"""Offline tests (no AI calls) on a temporary copy of the database.

  cd backend && .venv/bin/python -m pytest -q
"""

from __future__ import annotations

import os
import shutil
import tempfile
from types import SimpleNamespace
from pathlib import Path

DB_COPY = Path(tempfile.mkdtemp()) / "campus_customs.db"
shutil.copy(Path(__file__).resolve().parents[2] / "data" / "campus_customs.db", DB_COPY)  # hw4/data/ (local data pack)
os.environ["CAMPUS_CUSTOMS_DB"] = str(DB_COPY)
os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ["CAMPUS_CUSTOMS_AUDIT"] = str(DB_COPY.parent / "audit_trail.json")  # tests never touch the real audit file

from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import db  # noqa: E402
from agent import allowed_amounts, choose_effort, honesty_problems  # noqa: E402
from main import app  # noqa: E402
from models import BrowseLink, ChatReply, ProductNotFound, ProductPick, StockReport  # noqa: E402
from tools import ChatDeps, check_stock, get_price, get_product_description  # noqa: E402

client = TestClient(app)


def test_catalogue_and_images():
    products = client.get("/api/products").json()
    assert products["total"] == 102
    detail = client.get("/api/products/yale-dad-t-shirt").json()
    assert detail["price"] == 32.0 and len(detail["inventory"]) == 6
    assert "XL" not in detail["sizes_in_stock"]  # XL quantity is 0 in the given data
    assert client.get(detail["image_url"]).headers["content-type"] == "image/jpeg"
    assert client.get("/api/products/not-a-product").status_code == 404


def test_search_and_filters():
    names = [p["name"] for p in client.get("/api/products", params={"q": "dad shirt"}).json()["products"]]
    assert names[0] == "Yale Dad T Shirt"
    xl = client.get("/api/products", params={"q": "dad", "size": "XL"}).json()["products"]
    assert all("XL" in p["sizes_in_stock"] for p in xl)
    cheap = client.get("/api/products", params={"category": "T-Shirts", "sort": "price_asc"}).json()["products"]
    assert [p["price"] for p in cheap] == sorted(p["price"] for p in cheap)


def test_seed_test_user_can_log_in():
    r = client.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "password"})
    assert r.status_code == 200 and r.json()["user"]["first_name"] == "Test"
    assert client.post("/api/auth/login", json={"email": "test@campuscustoms.yale.edu", "password": "Password"}).status_code == 401


def test_signup_login_and_no_password_leak():
    body = {"first_name": "Test", "last_name": "Shopper", "email": "shopper@example.com", "password": "blue-crewneck-weather", "confirm_password": "blue-crewneck-weather"}
    created = client.post("/api/auth/signup", json=body)
    assert created.status_code == 201 and "password" not in created.text
    assert client.post("/api/auth/signup", json=body).status_code == 409
    token = client.post("/api/auth/login", json={"email": "SHOPPER@example.com", "password": body["password"]}).json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["first_name"] == "Test" and "password_hash" not in me
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}x"}).status_code == 401
    assert client.get("/api/chat/history").status_code == 401
    stored = db.find_user_by_email("shopper@example.com")[1]
    assert body["password"] not in stored and stored.startswith("pbkdf2_sha256$600000$")


def test_weak_or_mismatched_passwords_are_rejected():
    base = {"first_name": "Weak", "last_name": "Pass", "email": "weak@example.com"}
    for pw, confirm in [("password", "password"), ("12345678", "12345678"), ("aaaaaaaa", "aaaaaaaa"), ("weakpass-long", "different-one")]:
        assert client.post("/api/auth/signup", json={**base, "password": pw, "confirm_password": confirm}).status_code == 422
    assert db.find_user_by_email("weak@example.com") is None


def test_repeated_failed_logins_are_throttled():
    auth.throttle.reset("email:ada.1789818990@yale.edu", "ip:testclient")
    codes = [client.post("/api/auth/login", json={"email": "ada.1789818990@yale.edu", "password": f"guess-{i}"}).status_code for i in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    auth.throttle.reset("email:ada.1789818990@yale.edu", "ip:testclient")


def test_password_hash_formats():
    new = auth.hash_password("correct horse")
    algo, iterations, salt, digest = new.split("$")
    assert algo == "pbkdf2_sha256" and iterations == "600000" and len(salt) == 32 and len(digest) == 64
    assert auth.verify_password("correct horse", new) and not auth.verify_password("wrong", new)
    assert new != auth.hash_password("correct horse")  # a fresh random salt every time
    seed = db.find_user_by_email("test@campuscustoms.yale.edu")[1]
    assert len(seed.split("$")) == 3 and auth.verify_password("password", seed)


def _ctx():
    return SimpleNamespace(deps=ChatDeps(user=None))


def test_check_stock_reports_sold_out_sizes_clearly():
    ctx = _ctx()
    xl = check_stock(ctx, "yale-dad-t-shirt", "XL")  # XL quantity is 0 in the given data
    assert isinstance(xl, StockReport)
    assert xl.requested_size_status == "sold_out" and xl.requested_size_quantity == 0
    assert xl.summary.startswith("Sold out in XL.") and "XL" in xl.sizes_sold_out and "XL" not in xl.sizes_in_stock
    medium = check_stock(ctx, "Yale Dad T Shirt", "medium")  # exact name and a size word both work
    assert medium.requested_size == "M" and medium.requested_size_quantity == db.get_product("yale-dad-t-shirt").inventory[2].quantity
    assert check_stock(ctx, "yale-dad-t-shirt", "XXXL").requested_size_status is None
    assert [s.quantity for s in xl.sizes] == [s.quantity for s in db.get_product("yale-dad-t-shirt").inventory]


def test_unknown_products_return_suggestions_not_guesses():
    result = check_stock(_ctx(), "dad tee")
    assert isinstance(result, ProductNotFound) and result.suggestions
    assert any(s.product_id == "yale-dad-t-shirt" for s in result.suggestions)


def test_price_and_description_come_from_the_database():
    ctx = _ctx()
    quotes = get_price(ctx, ["yale-dad-t-shirt", "yale-mom-hoodie", "not-a-thing"])
    assert [q.price for q in quotes[:2]] == [32.0, 68.0] and isinstance(quotes[2], ProductNotFound)
    desc = get_product_description(ctx, "saybrook-college-crewneck")
    assert "Saybrook" in desc.description and not hasattr(desc, "price")
    assert ctx.deps.prices == {"yale-dad-t-shirt": 32.0, "yale-mom-hoodie": 68.0}  # a description alone never unlocks a price


def test_honesty_check_rejects_invented_prices_and_counts():
    ctx = _ctx()
    get_price(ctx, ["yale-dad-t-shirt", "yale-mom-hoodie"])
    check_stock(ctx, "yale-dad-t-shirt", "M")
    pick = ProductPick(product_id="yale-dad-t-shirt", highlight="Heather gray tee with navy YALE DAD lettering")
    ok = ChatReply(reply="The **Yale Dad T Shirt** is $32 and the hoodie is $68, $100 together.", showcase_title="Yale Dad gear", picks=[pick])
    assert honesty_problems(ctx.deps, ok) == []
    assert honesty_problems(ctx.deps, ChatReply(reply="It's only $5 today!"))
    assert honesty_problems(ctx.deps, ChatReply(reply="Only 3 left in M."))
    assert honesty_problems(ctx.deps, ChatReply(reply="Great pick.", showcase_title="Hoodies", picks=[ProductPick(product_id="basic-hoodie-big-yale", highlight="Big YALE")]))
    sneaky = ProductPick(product_id="yale-dad-t-shirt", highlight="Now just $5!")  # highlights are checked like the reply
    assert honesty_problems(ctx.deps, ChatReply(reply="Here you go.", showcase_title="Deals", picks=[sneaky]))
    assert honesty_problems(ctx.deps, ChatReply(reply="Here you go.", picks=[pick]))  # cards need a title


def test_price_honesty_rules():
    deps = ChatDeps(user=None)
    deps.prices.update({"yale-dad-t-shirt": 32.0, "yale-mom-hoodie": 68.0})
    ok = allowed_amounts(deps)
    assert {32.0, 68.0, 100.0, 136.0, 64.0} <= ok  # prices, a pair total, two of one item
    assert 5.0 not in ok and 55.0 not in ok  # invented prices are rejected
    assert choose_effort("gift ideas under $80 for my family") == "high"
    assert choose_effort("do you have hoodies?") == "low"


def test_showcase_contract_uses_live_data():
    show = db.build_showcase("Hoodies we carry", [("yale-mom-hoodie", "Navy hoodie with YALE MOM"), ("not-real", "x")],
                             BrowseLink(category="Hoodies"))
    assert show.title == "Hoodies we carry" and [c.product_id for c in show.items] == ["yale-mom-hoodie"]  # unknown ids dropped
    card = show.items[0]
    live = db.get_product("yale-mom-hoodie")
    assert card.price == live.price and card.image_url == live.image_url and card.highlight == "Navy hoodie with YALE MOM"
    assert show.total_matches == len([p for p in db.all_products() if p.category == "Hoodies"])


def test_saved_chats_reload_showcase_old_and_new_formats():
    user = db.find_user_by_email("test@campuscustoms.yale.edu")[0]
    db.save_chat(user.id, "assistant", "Here are some hoodies.", db.build_showcase("Hoodies", [("yale-dad-hoodie", "Navy YALE DAD hoodie")]))
    history = db.chat_history(user.id)
    newest = history[-1]
    assert newest.showcase.title == "Hoodies" and newest.showcase.items[0].highlight == "Navy YALE DAD hoodie"
    assert any(m.showcase for m in history[:-1])  # seed rows (a plain list of products) still load as cards


def test_page_context_is_verified_before_the_agent_sees_it():
    from models import PageContext
    from tools import resolve_page
    page = resolve_page(PageContext(path="/products/saybrook-college-crewneck", product_id="saybrook-college-crewneck"))
    assert page.kind == "product" and page.product_name == "Saybrook College Crewneck"
    assert resolve_page(PageContext(path="/products/fake", product_id="fake")).product_id is None  # unknown ids never reach the agent
    browsing = resolve_page(PageContext(path="/products", category="Not A Category", search="mom"))
    assert browsing.kind == "products" and browsing.category is None and browsing.search == "mom"


def test_account_tool_knows_the_signed_in_shopper_only():
    from tools import get_my_account
    user = db.find_user_by_email("test@campuscustoms.yale.edu")[0]
    me = get_my_account(SimpleNamespace(deps=ChatDeps(user=user)))
    assert me.signed_in and me.email == "test@campuscustoms.yale.edu" and me.first_name == "Test" and me.member_since
    assert "password" not in me.model_dump_json()
    assert get_my_account(_ctx()) .signed_in is False


def test_history_records_the_page_each_message_came_from():
    from agent import history_for_user
    from models import CurrentPage
    db.migrate()  # idempotent: safe to run again
    user = db.find_user_by_email("test@campuscustoms.yale.edu")[0]
    page = CurrentPage(path="/products/yale-dad-hoodie", kind="product", product_id="yale-dad-hoodie", product_name="Yale Dad Hoodie")
    db.save_chat(user.id, "user", "Do you have this in pink?", page=page)
    turns = history_for_user(user.id)
    assert turns[-1].content.startswith("[Sent from the product page for Yale Dad Hoodie (product_id yale-dad-hoodie)]")


def test_find_alternatives_only_returns_real_in_stock_substitutes():
    from tools import find_alternatives
    ctx = _ctx()
    result = find_alternatives(ctx, "yale-dad-t-shirt", size="XL")  # XL is sold out for the tee
    assert result.original_status == "Sold out in XL" and result.alternatives
    assert all("XL" in db.get_product(a.product_id).sizes_in_stock for a in result.alternatives)  # checked in code, not trusted
    assert result.alternatives[0].product_id == "yale-dad-hoodie"  # same "Dad" theme ranks first
    pink = find_alternatives(ctx, "basic-hoodie-big-yale", color="pink")
    assert "not pink" in pink.original_status and all(a.color_match in ("exact", "close") for a in pink.alternatives)
    assert "closest shades" in pink.note  # nothing is exactly pink, and the tool says so
    assert any(c.startswith("in-stock alternatives") for c in ctx.deps.checks)


def test_checks_are_written_from_real_tool_calls():
    ctx = _ctx()
    get_price(ctx, ["yale-dad-t-shirt"])
    check_stock(ctx, "saybrook-college-crewneck", "XXL")
    assert ctx.deps.checks == ["price of Yale Dad T Shirt", "live stock for Saybrook College Crewneck"]


def test_saved_items_endpoint_and_page_context():
    from models import PageContext
    from tools import resolve_page
    r = client.get("/api/products", params={"ids": "yale-mom-hoodie,not-real,yale-dad-t-shirt"}).json()
    assert [p["product_id"] for p in r["products"]] == ["yale-mom-hoodie", "yale-dad-t-shirt"]
    page = resolve_page(PageContext(path="/saved", saved_ids=["yale-mom-hoodie", "fake-id"]))
    assert page.kind == "saved" and page.saved == [{"product_id": "yale-mom-hoodie", "name": "Yale Mom Hoodie"}]


def test_multi_word_search_means_all_words():
    cards, mode = db.search_with_mode("Saybrook College", limit=500)
    assert mode == "all_words" and {c.product_id for c in cards} == {"saybrook-college-crewneck", "saybrook-logo-t-shirt", "saybrook-sweater-fleece-jacket"}
    loose, mode = db.search_with_mode("navy hoodie bulldog", limit=500)
    assert mode == "any_word" and loose  # nothing matches every word: loose matches, flagged so the agent won't quote a total



def test_audit_trail_is_append_only_and_redacted():
    import json as _json
    import audit
    from config import AUDIT_PATH
    user = db.find_user_by_email("test@campuscustoms.yale.edu")[0]
    for n in range(2):  # two separate "runs"
        trail = audit.TurnAudit(user, None, "low")
        trail.add("turn_started", result_summary=audit.redact(f"run {n}: email test@campuscustoms.yale.edu card 4242 4242 4242 4242"))
        trail.add("run_stopped", stop_reason="completed", duration_ms=1, model_requests=1)
        trail.flush()
    rows = _json.loads(AUDIT_PATH.read_text())
    assert len(rows) >= 4 and len({r["run_id"] for r in rows}) >= 2  # the second run appended; nothing was wiped
    text = AUDIT_PATH.read_text()
    assert "test@campuscustoms" not in text and "4242 4242" not in text and rows[0]["shopper"] == f"user:{user.id}"


def test_sensitive_numbers_are_masked_and_order_numbers_are_not():
    from safety import mask_sensitive
    text, found = mask_sensitive("card 4242 4242 4242 4242, order 1234567890123, ssn 123-45-6789")
    assert "4242" not in text and "1234567890123" in text and "123-45-6789" not in text
    assert found == ["card number", "social security number"]


def test_chat_rate_limit_and_crisis_signal():
    from safety import RateLimit, crisis_signal
    limit = RateLimit(3, 60)
    assert [limit.hit("ip:1") for _ in range(4)][:3] == [0, 0, 0] and limit.hit("ip:1") > 0 and limit.hit("ip:2") == 0
    assert crisis_signal("I want to end my life", strong_only=True)
    assert not crisis_signal("I'm hopeless at picking sizes lol", strong_only=True) and crisis_signal("feeling hopeless")
