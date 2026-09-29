"""Campus Customs web API: catalogue, product images, accounts, and the chat agent.

Run from the backend/ folder:
  uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic_ai.exceptions import ModelHTTPError, UnexpectedModelBehavior, UsageLimitExceeded

import auth
import db
from agent import chat, history_for_user
from tools import resolve_page
from config import BACKEND_DIR, CORS_ORIGINS, DATA_DIR
from images import ensure_web_images
from audit import record_safety_turn
from safety import CRISIS_REPLY, chat_limit, crisis_signal, mask_sensitive
from models import (AuthResponse, ChatMessageOut, ChatRequest, ChatResponse, Facets, LoginRequest, ProductDetail, ProductList,
                     PublicUser, SignupRequest)

log = logging.getLogger("campus_customs")
BLOCKED_REPLY = ("Sorry, I can't help with that request. I'm happy to help you find Yale merch, check prices and sizes, "
                 "or answer questions about the store.")
TOO_COMPLEX_REPLY = ("That one needed more lookups than I can do in one go. Could you ask about one or two products at a time? "
                     "The store can also help at (475) 301-4205.")
UNVERIFIED_REPLY = ("Sorry, I couldn't confirm that from our product data just now. Could you ask again, maybe naming the product? "
                    "You can also call the store at (475) 301-4205.")
app = FastAPI(title="Campus Customs API")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
db.migrate()
app.mount("/images", StaticFiles(directory=ensure_web_images(DATA_DIR / "products", DATA_DIR / "products_web")), name="images")


def current_user(authorization: str | None = Header(default=None)) -> PublicUser | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    user_id = auth.read_token(authorization[7:].strip())
    return db.get_user(user_id) if user_id else None


def require_user(user: PublicUser | None = Depends(current_user)) -> PublicUser:
    if not user:
        raise HTTPException(401, "Please sign in.")
    return user


# ---------- catalogue ----------

@app.get("/api/products", response_model=ProductList)
def list_products(q: str = "", category: str | None = None, color: str | None = None, max_price: float | None = None,
                  min_price: float | None = None, size: str | None = None, in_stock: bool = False,
                  sort: str = Query("featured", pattern="^(featured|price_asc|price_desc|name)$"),
                  ids: str | None = Query(None, max_length=4000, description="Comma-separated product ids (the Saved page)")):
    if ids is not None:
        products = db.get_products([i.strip() for i in ids.split(",") if i.strip()][:60])
        return ProductList(products=products, total=len(products))
    if q or category or color or max_price is not None or min_price is not None or size or in_stock:
        products = db.search_products(q, category, color, max_price, min_price, size, in_stock, limit=200)
    else:
        products = db.all_products()
    if sort == "price_asc":
        products.sort(key=lambda p: (p.price, p.name))
    elif sort == "price_desc":
        products.sort(key=lambda p: (-p.price, p.name))
    elif sort == "name":
        products.sort(key=lambda p: p.name)
    return ProductList(products=products, total=len(products))


@app.get("/api/products/{product_id}", response_model=ProductDetail)
def product_detail(product_id: str):
    product = db.get_product(product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product


@app.get("/api/facets", response_model=Facets)
def facets():
    products = db.all_products()
    counts: dict[str, int] = {}
    for p in products:
        counts[p.category] = counts.get(p.category, 0) + 1
    order = [name for name, _ in db.CATEGORY_RULES] + ["Other"]
    categories = [{"name": c, "count": counts[c]} for c in sorted(counts, key=lambda c: order.index(c) if c in order else 99)]
    main_colors = ["navy", "blue", "gray", "white", "black", "red", "green", "cream", "gold"]
    colors = [c for c in main_colors if any(c in col.lower() for p in products for col in p.colors)]
    return Facets(categories=categories, colors=colors, min_price=min(p.price for p in products), max_price=max(p.price for p in products))


# ---------- accounts ----------

@app.post("/api/auth/signup", response_model=AuthResponse, status_code=201)
def signup(body: SignupRequest):
    if body.confirm_password is not None and body.confirm_password != body.password:
        raise HTTPException(422, "Passwords don't match.")
    if problem := auth.password_problem(body.password, body.email, body.first_name, body.last_name):
        raise HTTPException(422, problem)
    if db.find_user_by_email(body.email):
        raise HTTPException(409, "An account with this email already exists. Try logging in.")
    try:
        user = db.create_user(body.first_name.strip(), body.last_name.strip(), body.email, auth.hash_password(body.password))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "An account with this email already exists. Try logging in.")
    return AuthResponse(token=auth.create_token(user.id), user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
def login(body: LoginRequest, request: Request):
    email_key, ip_key = f"email:{body.email.lower()}", f"ip:{request.client.host if request.client else 'unknown'}"
    if wait := auth.throttle.retry_after(email_key, ip_key):
        raise HTTPException(429, f"Too many failed attempts. Try again in {max(1, wait // 60)} minute(s).", headers={"Retry-After": str(wait)})
    found = db.find_user_by_email(body.email)
    if found is None:
        auth.burn_time(body.password)  # same cost as a wrong password, so nobody can probe which emails have accounts
    if found is None or not auth.verify_password(body.password, found[1]):
        auth.throttle.fail(email_key, ip_key)
        raise HTTPException(401, "Email or password is incorrect.")
    auth.throttle.reset(email_key)
    return AuthResponse(token=auth.create_token(found[0].id), user=found[0])


@app.get("/api/auth/me", response_model=PublicUser)
def me(user: PublicUser = Depends(require_user)):
    return user


# ---------- chat ----------

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request, user: PublicUser | None = Depends(current_user)):
    key = f"user:{user.id}" if user else f"ip:{request.client.host if request.client else 'unknown'}"
    if wait := chat_limit.hit(key):
        raise HTTPException(429, f"You're sending messages very quickly. Please wait {wait} seconds and try again.", headers={"Retry-After": str(wait)})
    # Card numbers, SSNs, and passwords are masked here, before the model, the database, or the audit trail ever see them.
    message, masked = mask_sensitive(body.message)
    if masked:
        log.info("masked %s in a chat message", ", ".join(masked))
    # Signed-in shoppers: history comes from the database (anything the browser sends is ignored). Guests: from the browser.
    history = history_for_user(user.id) if user else [t.model_copy(update={"content": mask_sensitive(t.content)[0]}) for t in body.history]
    page = resolve_page(body.page)  # checked against the database before the agent sees it
    try:
        if crisis_signal(message, strong_only=True):
            response = ChatResponse(reply=CRISIS_REPLY, showcase=None, effort="low")  # care first, no model needed
            record_safety_turn(user, page, "crisis reply sent without calling the model")
        else:
            response = await chat(message, user, history, page)
    except ModelHTTPError as error:
        if "content_filter" not in str(error.body):
            log.exception("chat failed")
            raise HTTPException(502, "The assistant is having trouble right now. Please try again in a moment.")
        # The provider's safety filter blocked the message: answer kindly instead of erroring. If it sounded like distress,
        # reply with support resources, never a flat "can't help".
        response = ChatResponse(reply=CRISIS_REPLY if crisis_signal(message) else BLOCKED_REPLY, showcase=None, effort="low")
    except UsageLimitExceeded:
        log.warning("chat turn hit the model request limit for %r", message[:80])
        response = ChatResponse(reply=TOO_COMPLEX_REPLY, showcase=None, effort="high")
    except UnexpectedModelBehavior:
        # The honesty checks rejected every draft; say so rather than show an unverified price or stock claim.
        log.warning("chat reply failed validation twice for %r", message[:80])
        response = ChatResponse(reply=UNVERIFIED_REPLY, showcase=None, effort="high")
    except Exception:
        log.exception("chat failed")
        raise HTTPException(502, "The assistant is having trouble right now. Please try again in a moment.")
    if user:
        db.save_chat(user.id, "user", message, page=page)
        db.save_chat(user.id, "assistant", response.reply, response.showcase, checks=response.checks)
    return response


@app.get("/api/chat/history", response_model=list[ChatMessageOut])
def get_history(user: PublicUser = Depends(require_user)):
    return db.chat_history(user.id)


@app.delete("/api/chat/history", status_code=204)
def delete_history(user: PublicUser = Depends(require_user)):
    db.clear_chat(user.id)


@app.get("/api/health")
def health():
    return {"ok": True, "products": len(db.all_products())}


# ---------- built front end (optional single-server mode) ----------

DIST = BACKEND_DIR.parent / "frontend" / "dist"
if DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        target = DIST / path
        return FileResponse(target if path and target.is_file() else DIST / "index.html")
