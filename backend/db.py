"""SQLite access for the catalogue, inventory, users, and chat history. All SQL is parameterised."""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from config import DB_PATH, LOW_STOCK_THRESHOLD
from models import SIZE_ORDER, BrowseLink, ChatMessageOut, Checks, CurrentPage, ProductCard, ProductDetail, PublicUser, Showcase, ShowcaseCard, SizeStock

# Shop categories, checked in order against the free-text garment_type column.
CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("Quarter-Zips", ("quarter-zip",)),
    ("Jackets & Fleece", ("jacket", "fleece", "bomber")),
    ("Hoodies", ("hoodie", "hooded")),
    ("Long Sleeves", ("long-sleeve",)),
    ("Crewnecks", ("crewneck", "mockneck", "raglan")),
    ("T-Shirts", ("t-shirt",)),
]
SYNONYMS = {
    "tee": "t-shirt", "tees": "t-shirt", "tshirt": "t-shirt", "shirt": "t-shirt",
    "hoody": "hoodie", "hoodies": "hoodie", "sweatshirts": "sweatshirt", "crew": "crewneck", "crewnecks": "crewneck",
    "quarterzip": "quarter-zip", "1/4": "quarter-zip", "zip": "zip", "grey": "gray", "jackets": "jacket",
    "mom": "mom", "mother": "mom", "dad": "dad", "father": "dad", "grandmother": "grandma", "grandfather": "grandpa",
}
STOPWORDS = {"a", "an", "the", "and", "or", "for", "with", "in", "of", "to", "do", "you", "have", "any", "i", "me", "my",
             "want", "need", "looking", "some", "something", "show", "yale", "is", "are", "it", "that", "this", "please"}


def migrate() -> None:
    """Additive schema changes, safe to run on every start: chat_messages.page_json records where each message was sent from."""
    with connect() as conn:
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(chat_messages)")}
        if "page_json" not in columns:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN page_json TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages (user_id, id)")


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def category_of(garment_type: str) -> str:
    g = garment_type.lower()
    for name, keys in CATEGORY_RULES:
        if any(k in g for k in keys):
            return name
    return "Other"


def _inventory(conn: sqlite3.Connection) -> dict[str, list[SizeStock]]:
    rows = conn.execute("SELECT product_id, size, quantity FROM inventory").fetchall()
    stock: dict[str, list[SizeStock]] = {}
    for r in rows:
        stock.setdefault(r["product_id"], []).append(SizeStock(size=r["size"], quantity=r["quantity"]))
    for sizes in stock.values():
        sizes.sort(key=lambda s: SIZE_ORDER.index(s.size) if s.size in SIZE_ORDER else 99)
    return stock


def _card(row: sqlite3.Row, sizes: list[SizeStock]) -> ProductCard:
    total = sum(s.quantity for s in sizes)
    status = "sold_out" if total == 0 else "low_stock" if total <= LOW_STOCK_THRESHOLD else "in_stock"
    return ProductCard(
        product_id=row["product_id"],
        name=row["name"],
        category=category_of(row["garment_type"]),
        garment_type=row["garment_type"],
        description=row["description"],
        colors=json.loads(row["colors"]),
        price=row["price"],
        image_url=f"/images/{row['image_file_path'].removeprefix('products/')}",
        total_stock=total,
        sizes_in_stock=[s.size for s in sizes if s.quantity > 0],
        stock_status=status,
    )


def all_products() -> list[ProductCard]:
    with connect() as conn:
        stock = _inventory(conn)
        rows = conn.execute("SELECT * FROM catalogue ORDER BY name").fetchall()
    return [_card(r, stock.get(r["product_id"], [])) for r in rows]


def get_product(product_id: str) -> ProductDetail | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
        if not row:
            return None
        sizes = _inventory(conn).get(product_id, [])
    card = _card(row, sizes)
    return ProductDetail(**card.model_dump(), search_tags=json.loads(row["search_tags"]), inventory=sizes)


def get_products(product_ids: list[str]) -> list[ProductCard]:
    """Cards for the given ids, in the given order; unknown ids are skipped."""
    by_id = {p.product_id: p for p in all_products()}
    return [by_id[i] for i in dict.fromkeys(product_ids) if i in by_id]


def _terms(query: str) -> list[str]:
    words = re.findall(r"[a-z0-9/'-]+", query.lower())
    return [SYNONYMS.get(w, w) for w in words if w not in STOPWORDS]


def search_products(query: str = "", category: str | None = None, color: str | None = None, max_price: float | None = None,
                    min_price: float | None = None, size: str | None = None, in_stock_only: bool = False, limit: int = 12) -> list[ProductCard]:
    """Keyword search over name, tags, garment type, colors, and description, plus exact filters. Best matches first."""
    return search_with_mode(query, category, color, max_price, min_price, size, in_stock_only, limit)[0]


def search_with_mode(query: str = "", category: str | None = None, color: str | None = None, max_price: float | None = None,
                     min_price: float | None = None, size: str | None = None, in_stock_only: bool = False,
                     limit: int = 12) -> tuple[list[ProductCard], str]:
    """Like search_products, plus how the words matched: 'all_words', 'any_word' (loose fallback), or 'filters_only'."""
    with connect() as conn:
        stock = _inventory(conn)
        rows = conn.execute("SELECT * FROM catalogue").fetchall()
    terms = _terms(query)
    scored: list[tuple[float, ProductCard]] = []
    for r in rows:
        card = _card(r, stock.get(r["product_id"], []))
        if category and card.category.lower() != category.lower():
            continue
        if color and not any(color.lower().replace("grey", "gray") in c.lower() for c in card.colors):
            continue
        if max_price is not None and card.price > max_price:
            continue
        if min_price is not None and card.price < min_price:
            continue
        if size and size.upper() not in card.sizes_in_stock:
            continue
        if in_stock_only and card.stock_status == "sold_out":
            continue
        fields = {
            "name": r["name"].lower(), "tags": r["search_tags"].lower(), "type": r["garment_type"].lower(),
            "colors": r["colors"].lower(), "desc": r["description"].lower(),
        }
        weights = {"name": 3.0, "tags": 2.0, "type": 2.0, "colors": 1.5, "desc": 1.0}
        score = sum(w for t in terms for f, w in weights.items() if t in fields[f])
        if terms and score == 0:
            continue
        hits = sum(1 for t in terms if any(t in v for v in fields.values()))
        scored.append((score, hits, card))
    # Several words ("Saybrook College") should mean all of them. Use any-word matches only when nothing matches every word.
    mode = "filters_only" if not terms else "all_words"
    if len(terms) > 1:
        if any(h == len(terms) for _, h, _ in scored):
            scored = [s for s in scored if s[1] == len(terms)]
        else:
            mode = "any_word"
    scored.sort(key=lambda s: (-s[0], s[2].stock_status == "sold_out", s[2].name))
    return [c for _, _, c in scored[:limit]], mode


# ---------- users ----------

def _public(row: sqlite3.Row) -> PublicUser:
    first = row["first_name"] or (row["name"].split(" ", 1)[0] if row["name"] else "")
    last = row["last_name"] or (row["name"].split(" ", 1)[1] if row["name"] and " " in row["name"] else "")
    return PublicUser(id=row["id"], first_name=first, last_name=last, name=row["name"], email=row["email"], created_at=row["created_at"])


def find_user_by_email(email: str) -> tuple[PublicUser, str] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()
    return (_public(row), row["password_hash"]) if row else None


def get_user(user_id: int) -> PublicUser | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public(row) if row else None


def create_user(first_name: str, last_name: str, email: str, password_hash: str) -> PublicUser:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash, first_name, last_name) VALUES (?, ?, ?, ?, ?)",
            (f"{first_name} {last_name}".strip(), email.strip().lower(), password_hash, first_name, last_name),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _public(row)


# ---------- chat history ----------

def build_showcase(title: str | None, picks: list[tuple[str, str]], browse: BrowseLink | None = None) -> Showcase | None:
    """Turn the agent's (product_id, highlight) picks into cards with live price, stock, and image. Unknown ids are dropped."""
    by_id = {p.product_id: p for p in all_products()}
    items = [ShowcaseCard(**by_id[pid].model_dump(), highlight=(highlight or by_id[pid].description)[:120])
             for pid, highlight in dict(picks).items() if pid in by_id]
    if not items:
        return None
    total = None
    if browse and (browse.category or browse.query or browse.color):
        total = len(search_products(browse.query or "", browse.category, browse.color, limit=500))
    return Showcase(title=title or "From your chat", items=items, browse=browse, total_matches=total)


def save_chat(user_id: int, role: str, content: str, showcase: Showcase | None = None, page: CurrentPage | None = None,
              checks: Checks | None = None) -> None:
    """Assistant rows store the showcase recipe (ids, highlights, title, link), not prices, so history always reloads live data."""
    products_json = None
    if role == "assistant":
        recipe: dict = {"title": showcase.title, "items": [{"product_id": c.product_id, "highlight": c.highlight} for c in showcase.items],
                        "browse": showcase.browse.model_dump() if showcase.browse else None} if showcase else {"items": []}
        if checks:
            recipe["checks"] = checks.model_dump()
        products_json = json.dumps(recipe)
    with connect() as conn:
        conn.execute("INSERT INTO chat_messages (user_id, role, content, products_json, page_json) VALUES (?, ?, ?, ?, ?)",
                     (user_id, role, content, products_json, page.model_dump_json() if page else None))


def _stored_showcase(raw: str | None) -> Showcase | None:
    data = json.loads(raw or "[]")
    if isinstance(data, list):  # rows from the seed data / Problem 1: a plain list of product dicts
        return build_showcase(None, [(p.get("product_id"), "") for p in data if isinstance(p, dict)])
    browse = BrowseLink(**data["browse"]) if data.get("browse") else None
    if not data.get("items"):
        return None
    return build_showcase(data.get("title"), [(i["product_id"], i.get("highlight", "")) for i in data.get("items", [])], browse)


def _stored_checks(raw: str | None) -> Checks | None:
    data = json.loads(raw or "[]")
    return Checks(**data["checks"]) if isinstance(data, dict) and data.get("checks") else None


def chat_history(user_id: int, limit: int = 40) -> list[ChatMessageOut]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM (SELECT * FROM chat_messages WHERE user_id = ? ORDER BY id DESC LIMIT ?) ORDER BY id",
                            (user_id, limit)).fetchall()
    return [ChatMessageOut(id=r["id"], role=r["role"], content=r["content"],
                           showcase=_stored_showcase(r["products_json"]) if r["role"] == "assistant" else None,
                           page=CurrentPage.model_validate_json(r["page_json"]) if r["page_json"] else None,
                           checks=_stored_checks(r["products_json"]) if r["role"] == "assistant" else None, created_at=r["created_at"])
            for r in rows]


def count_chat(user_id: int) -> int:
    with connect() as conn:
        return conn.execute("SELECT COUNT(*) FROM chat_messages WHERE user_id = ?", (user_id,)).fetchone()[0]


def clear_chat(user_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
