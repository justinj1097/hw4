"""Tools the shopping agent can call. Each one reads campus_customs.db; the agent may only state prices and
stock that these return. Results are typed (models.py) so the agent always gets the same fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pydantic_ai import RunContext

import db
from models import (SIZE_ORDER, Alternative, AlternativesResult, CatalogueOverview, CurrentPage, PageContext, SearchResults, ShopperProfile, PriceQuote, ProductCard, ProductDescription, ProductDetail, ProductMatch,
                    ProductNotFound, PublicUser, SizeAvailability, StockReport)
from config import LOW_STOCK_THRESHOLD


@dataclass
class ChatDeps:
    """Per-turn state. The honesty validator in agent.py checks the reply against what the tools actually returned."""

    user: PublicUser | None  # the signed-in shopper from the users table (name, email), or None for a guest
    page: CurrentPage | None = None  # where they are on the site, verified against the database
    seen_ids: set[str] = field(default_factory=set)  # every product any tool returned this turn
    prices: dict[str, float] = field(default_factory=dict)  # product_id -> price, only from price-bearing results
    quantities: set[int] = field(default_factory=set)  # every stock number a tool returned (per size and totals)
    user_amounts: set[float] = field(default_factory=set)  # dollar amounts the shopper typed ("under $50")
    tool_calls: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)  # plain-English lookups for the "✓ Checked the store database" note


def _checked(ctx: RunContext[ChatDeps], text: str) -> None:
    if text not in ctx.deps.checks:
        ctx.deps.checks.append(text)


# ---------- helpers ----------

def _status(quantity: int) -> str:
    return "sold_out" if quantity == 0 else "low_stock" if quantity <= LOW_STOCK_THRESHOLD else "in_stock"


def _match(card: ProductCard) -> ProductMatch:
    return ProductMatch(product_id=card.product_id, name=card.name, category=card.category, colors=card.colors,
                        price=card.price, stock_status=card.stock_status, sizes_in_stock=card.sizes_in_stock)


def _remember(ctx: RunContext[ChatDeps], card: ProductCard, price: bool = True, stock: bool = True) -> None:
    ctx.deps.seen_ids.add(card.product_id)
    if price:
        ctx.deps.prices[card.product_id] = card.price
    if stock:
        ctx.deps.quantities.add(card.total_stock)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _join(sizes: list[str]) -> str:
    return sizes[0] if len(sizes) == 1 else ", ".join(sizes[:-1]) + f", and {sizes[-1]}"


def resolve(product: str) -> ProductDetail | ProductNotFound:
    """Find one product by id or exact name. Anything fuzzier returns suggestions instead of a guess."""
    text = product.strip()
    if detail := db.get_product(text):
        return detail
    wanted = _norm(text)
    for card in db.all_products():
        if _norm(card.name) == wanted or _norm(card.product_id) == wanted:
            return db.get_product(card.product_id)  # type: ignore[return-value]
    suggestions = [_match(c) for c in db.search_products(text, limit=3)]
    hint = "Did you mean one of the suggestions? Use its product_id." if suggestions else "Try search_products with other words."
    return ProductNotFound(query=text, message=f"No product with id or name '{text}'. {hint}", suggestions=suggestions)


def _log(ctx: RunContext[ChatDeps], call: str) -> None:
    ctx.deps.tool_calls.append(call)


# ---------- tools ----------

def search_products(ctx: RunContext[ChatDeps], query: str = "", category: str | None = None, color: str | None = None,
                    max_price: float | None = None, min_price: float | None = None, size: str | None = None,
                    in_stock_only: bool = False, limit: int = 12) -> SearchResults:
    """Find products from the shopper's words. Returns ids, names, prices, which sizes are in stock, and the total match count.

    Args:
        query: keywords such as "baseball crewneck", "mom hoodie", "Saybrook", "vintage bulldog". Empty to browse by filters.
        category: one of Hoodies, Crewnecks, T-Shirts, Long Sleeves, Quarter-Zips, Jackets & Fleece.
        color: a color word, e.g. "navy", "gray", "white".
        max_price: highest price in US dollars.
        min_price: lowest price in US dollars.
        size: only products in stock in this size (XS, S, M, L, XL, XXL). This HIDES products sold out in that size, so
            do NOT use it to answer "is X in stock in size Y?" - find X without a size, then call check_stock.
        in_stock_only: skip products that are sold out in every size.
        limit: how many results, 1-12.
    """
    every, mode = db.search_with_mode(query, category, color, max_price, min_price, size, in_stock_only, limit=500)
    cards = every[:max(1, min(limit, 12))]
    for c in cards:
        _remember(ctx, c)
    if mode != "any_word":
        ctx.deps.quantities.add(len(every))  # a real total may be quoted ("we have 27 hoodies"); a loose one may not
    _log(ctx, f"search_products({query!r}, category={category!r}) -> {len(cards)} of {len(every)}")
    what = " ".join(x for x in [color, category, f'"{query}"' if query else None] if x) or "the catalogue"
    _checked(ctx, f"searched {what} ({len(every)} match{'es' if len(every) != 1 else ''})" if mode != "any_word" else f"searched {what} (closest matches)")
    return SearchResults(total_matches=len(every), showing=len(cards), match=mode, results=[_match(c) for c in cards])


def get_product_description(ctx: RunContext[ChatDeps], product: str) -> ProductDescription | ProductNotFound:
    """What a product is: type, colors, design, and tags. Use get_price or check_stock for price and stock.

    Args:
        product: a product_id from search_products (preferred) or the product's exact name.
    """
    found = resolve(product)
    _log(ctx, f"get_product_description({product!r})")
    if isinstance(found, ProductNotFound):
        return found
    _remember(ctx, found, price=False, stock=False)
    _checked(ctx, f"product details for {found.name}")
    return ProductDescription(product_id=found.product_id, name=found.name, category=found.category, garment_type=found.garment_type,
                              description=found.description, colors=found.colors, tags=found.search_tags,
                              product_page=f"/products/{found.product_id}")


def get_price(ctx: RunContext[ChatDeps], products: list[str]) -> list[PriceQuote | ProductNotFound]:
    """Current list price for one or more products (up to 10), straight from the database.

    Args:
        products: product_ids from search_products (preferred) or exact product names.
    """
    out: list[PriceQuote | ProductNotFound] = []
    for product in products[:10]:
        found = resolve(product)
        if isinstance(found, ProductNotFound):
            out.append(found)
            continue
        _remember(ctx, found, stock=False)
        out.append(PriceQuote(product_id=found.product_id, name=found.name, price=found.price))
    _log(ctx, f"get_price({products!r})")
    quoted = [q.name for q in out if isinstance(q, PriceQuote)]
    if quoted:
        _checked(ctx, f"price of {quoted[0]}" if len(quoted) == 1 else f"prices of {len(quoted)} products")
    return out


def check_stock(ctx: RunContext[ChatDeps], product: str, size: str | None = None) -> StockReport | ProductNotFound:
    """How many are in stock, size by size. Pass `size` when the shopper asks about one size.

    Args:
        product: a product_id from search_products (preferred) or the product's exact name.
        size: optional, one of XS, S, M, L, XL, XXL (also accepts "small", "medium", "large", "extra large").
    """
    found = resolve(product)
    _log(ctx, f"check_stock({product!r}, {size!r})")
    if isinstance(found, ProductNotFound):
        return found
    _remember(ctx, found)
    _checked(ctx, f"live stock for {found.name}")
    sizes = [SizeAvailability(size=s.size, quantity=s.quantity, status=_status(s.quantity)) for s in found.inventory]
    ctx.deps.quantities.update(s.quantity for s in sizes)
    in_stock = [s.size for s in sizes if s.quantity > 0]
    sold_out = [s.size for s in sizes if s.quantity == 0]

    requested = _size(size) if size else None
    row = next((s for s in sizes if s.size == requested), None)
    if size and not row:
        summary = f"'{size}' isn't a size this product comes in (sizes: {', '.join(s.size for s in sizes)}). "
    elif row and row.quantity == 0:
        summary = f"Sold out in {row.size}. "
    elif row:
        summary = f"In stock in {row.size}: {'only ' if row.status == 'low_stock' else ''}{row.quantity} left. "
    else:
        summary = ""
    if not in_stock:
        summary += "Sold out in every size."
    else:
        summary += f"In stock in {_join(in_stock)}." + (f" Sold out in {_join(sold_out)}." if sold_out else "")

    return StockReport(
        product_id=found.product_id, name=found.name, price=found.price, sizes=sizes, sizes_in_stock=in_stock, sizes_sold_out=sold_out,
        total_in_stock=sum(s.quantity for s in sizes), requested_size=row.size if row else (size or None),
        requested_size_status=row.status if row else None, requested_size_quantity=row.quantity if row else None,
        summary=summary.strip(), checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def list_categories(ctx: RunContext[ChatDeps]) -> CatalogueOverview:
    """What the store carries overall: categories with product counts, colors, sizes, and the price range."""
    products = db.all_products()
    _log(ctx, "list_categories()")
    _checked(ctx, "the full catalogue overview")
    counts: dict[str, int] = {}
    for p in products:
        counts[p.category] = counts.get(p.category, 0) + 1
    low, high = min(p.price for p in products), max(p.price for p in products)
    ctx.deps.user_amounts.update({low, high})  # the range itself may be quoted
    return CatalogueOverview(product_count=len(products), categories=counts, colors=sorted({c for p in products for c in p.colors}),
                             sizes=SIZE_ORDER, price_range_usd=(low, high))


# ---------- substitutes ----------

COLOR_FAMILIES = {
    "pink": ["pink", "rose", "coral", "magenta", "salmon", "fuchsia"], "red": ["red", "crimson", "maroon", "coral"],
    "blue": ["blue", "navy", "royal", "light blue"], "navy": ["navy", "blue"], "gray": ["gray", "grey", "heather", "charcoal", "silver"],
    "grey": ["gray", "grey", "heather", "charcoal"], "white": ["white", "cream", "ivory"], "black": ["black", "charcoal"],
    "green": ["green", "forest", "olive"], "yellow": ["yellow", "gold"], "gold": ["gold", "yellow"],
    "purple": ["purple", "violet", "lavender"], "orange": ["orange", "coral"], "cream": ["cream", "ivory", "white"],
}


def _color_match(wanted: str, colors: list[str]) -> str:
    """'exact' if the color is named, 'close' if a shade from the same family is, else ''."""
    w = _norm(wanted)
    lowered = [c.lower() for c in colors]
    if any(w in c for c in lowered):
        return "exact"
    return "close" if any(shade in c for shade in COLOR_FAMILIES.get(w, []) for c in lowered) else ""


NAME_STOPWORDS = {"yale", "university", "the", "t", "shirt", "tee", "crewneck", "hoodie", "1", "4", "zip", "left", "chest", "logo",
                  "tri", "blend", "sports", "college", "fleece", "jacket", "sweater", "long", "sleeve"}


def _name_words(name: str) -> set[str]:
    return set(_norm(name).split()) - NAME_STOPWORDS


def find_alternatives(ctx: RunContext[ChatDeps], product: str | None = None, size: str | None = None, color: str | None = None,
                      category: str | None = None, limit: int = 6) -> AlternativesResult | ProductNotFound:
    """Real in-stock substitutes when a product is sold out in a size, or doesn't come in a color.

    Every result is in stock in `size` (if given) and comes in `color` or a close shade (if given), checked in code.
    Show them as cards (picks) and say why each fits.

    Args:
        product: the product being replaced (product_id or exact name). Optional if you pass a category.
        size: the size the shopper needs, e.g. XXL or "medium".
        color: the color the shopper wants, e.g. "pink".
        category: shop category to search when there's no product (e.g. Hoodies).
        limit: how many substitutes, 1-8.
    """
    original = resolve(product) if product else None
    if isinstance(original, ProductNotFound):
        return original
    want_size = _size(size) if size else None
    base_category = original.category if original else category
    _log(ctx, f"find_alternatives({product!r}, size={want_size!r}, color={color!r})")

    problems = []
    if original and want_size:
        row = next((s for s in original.inventory if s.size == want_size), None)
        problems.append(f"Sold out in {want_size}" if row and row.quantity == 0 else f"In stock in {want_size}" if row else f"Doesn't come in {want_size}")
    if original and color:
        match = _color_match(color, original.colors)
        problems.append(f"Comes in {', '.join(original.colors)}" + ("" if match == "exact" else f", not {color}"))
    status = "; ".join(problems) or "Looking for similar items"

    base_tags = {t.lower() for t in original.search_tags} if original else set()
    scored: list[tuple[float, Alternative]] = []
    for card in db.all_products():
        if original and card.product_id == original.product_id:
            continue
        if want_size and want_size not in card.sizes_in_stock:
            continue
        if not want_size and card.stock_status == "sold_out":
            continue
        color_hit = _color_match(color, card.colors) if color else "not_requested"
        if color and not color_hit:
            continue
        detail = db.get_product(card.product_id)
        shared = base_tags & {t.lower() for t in detail.search_tags} - {"yale", "yale university", "college merch", "campus customs"}
        # Shared name words ("Dad", "Saybrook", "Baseball") matter most: they're who or what the item is for.
        theme_words = (_name_words(original.name) & _name_words(card.name)) if original else set()
        score = (8 * len(theme_words) + (4 if base_category and card.category == base_category else 0) + len(shared)
                 + (3 if color_hit == "exact" else 1 if color_hit == "close" else 0))
        if original:
            score += len(set(original.colors) & set(card.colors)) * 0.5 + (1 if original.garment_type == card.garment_type else 0)
        reasons = []
        if base_category and card.category == base_category:
            reasons.append(f"also a {card.category[:-1] if card.category.endswith('s') else card.category}")
        if want_size:
            reasons.append(f"in stock in {want_size}")
        if color:
            reasons.append(f"comes in {color}" if color_hit == "exact" else f"close shade: {', '.join(c for c in card.colors if _color_match(color, [c]))}")
        garment_words = ("crewneck", "hoodie", "sweatshirt", "shirt", "tee", "zip", "jacket", "fleece", "sleeve")
        themes = sorted((t for t in shared if not any(g in t for g in garment_words)), key=lambda t: (-len(t.split()), t))
        if theme_words:
            reasons.append("also " + " ".join(w.capitalize() for w in sorted(theme_words)))
        elif themes:
            reasons.append(f"also {themes[0]}")
        why = " · ".join(reasons)
        scored.append((score, Alternative(**_match(card).model_dump(), why=why[:1].upper() + why[1:], color_match=color_hit)))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    alternatives = [a for _, a in scored[:max(1, min(limit, 8))]]
    for a in alternatives:
        _remember(ctx, db.get_products([a.product_id])[0])
    if original:
        _remember(ctx, original)
    _checked(ctx, f"in-stock alternatives{f' in {want_size}' if want_size else ''}{f' in {color}' if color else ''} ({len(alternatives)} found)")
    note = "" if alternatives else "No product in the catalogue meets all of these; say so and suggest relaxing the color or size."
    if color and alternatives and all(a.color_match == "close" for a in alternatives):
        note = f"Nothing comes in exactly {color}; these are the closest shades. Say that clearly."
    return AlternativesResult(original=_match(original) if original else None, original_status=status, requested_size=want_size,
                              requested_color=color, alternatives=alternatives, note=note)


SIZE_WORDS = {"xs": "XS", "extra small": "XS", "x small": "XS", "s": "S", "small": "S", "m": "M", "medium": "M", "med": "M",
              "l": "L", "large": "L", "xl": "XL", "extra large": "XL", "x large": "XL", "xxl": "XXL", "2xl": "XXL", "xx large": "XXL"}


def _size(text: str) -> str:
    return SIZE_WORDS.get(_norm(text).replace("-", " "), text.strip().upper())


# ---------- who is chatting, and where ----------

PAGE_KINDS = {"/": "home", "/products": "products", "/about": "about", "/login": "login", "/signup": "signup"}


def resolve_page(page: PageContext | None) -> CurrentPage | None:
    """Turn the browser's page report into facts the agent can trust: the product must exist, the category must be real."""
    if page is None:
        return None
    by_id = {p.product_id: p for p in db.all_products()}
    saved = [{"product_id": i, "name": by_id[i].name} for i in dict.fromkeys(page.saved_ids) if i in by_id][:30]
    path = page.path.split("?", 1)[0].rstrip("/") or "/"
    if path.startswith("/products/"):
        product = db.get_product(page.product_id or path.removeprefix("/products/"))
        if product:
            return CurrentPage(path=path, kind="product", product_id=product.product_id, product_name=product.name, category=product.category, saved=saved)
        return CurrentPage(path=path, kind="other", saved=saved)
    categories = {p.category for p in db.all_products()}
    category = page.category if page.category in categories else None
    search = (page.search or "").strip()[:100] or None
    kind = "saved" if path == "/saved" else PAGE_KINDS.get(path, "other")
    return CurrentPage(path=path, kind=kind, category=category, search=search, saved=saved)  # type: ignore[arg-type]


def get_my_account(ctx: RunContext[ChatDeps]) -> ShopperProfile:
    """The signed-in shopper's own account: name, email, member-since date, and how many chat messages are saved."""
    _log(ctx, "get_my_account()")
    _checked(ctx, "your account details")
    u = ctx.deps.user
    if not u:
        return ShopperProfile(signed_in=False)
    return ShopperProfile(signed_in=True, first_name=u.first_name, last_name=u.last_name, email=u.email,
                          member_since=u.created_at[:10], saved_messages=db.count_chat(u.id))


def get_current_page(ctx: RunContext[ChatDeps]) -> CurrentPage | ProductNotFound:
    """Which page the shopper is looking at right now. On a product page this is the item 'this' or 'it' refers to."""
    _log(ctx, "get_current_page()")
    page = ctx.deps.page
    if page is None:
        return ProductNotFound(query="current page", message="The site didn't say which page the shopper is on.")
    if page.product_id:
        ctx.deps.seen_ids.add(page.product_id)
    return page


TOOLS = [search_products, get_product_description, get_price, check_stock, find_alternatives, list_categories, get_my_account, get_current_page]
