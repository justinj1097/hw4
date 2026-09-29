"""Pydantic types shared by the API, the database layer, and the PydanticAI agent."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Size = Literal["XS", "S", "M", "L", "XL", "XXL"]
SIZE_ORDER: list[str] = ["XS", "S", "M", "L", "XL", "XXL"]


# ---------- catalogue ----------

class SizeStock(BaseModel):
    size: str
    quantity: int = Field(ge=0)


class ProductCard(BaseModel):
    """What a product grid tile (and a chat product card) needs."""

    product_id: str
    name: str
    category: str = Field(description="Shop category derived from garment_type, e.g. 'Hoodies'")
    garment_type: str
    description: str
    colors: list[str]
    price: float
    image_url: str
    total_stock: int
    sizes_in_stock: list[str]
    stock_status: Literal["in_stock", "low_stock", "sold_out"]


class ProductDetail(ProductCard):
    search_tags: list[str]
    inventory: list[SizeStock]


class ProductList(BaseModel):
    products: list[ProductCard]
    total: int


class Facets(BaseModel):
    categories: list[dict]  # {"name": "Hoodies", "count": 25}
    colors: list[str]
    min_price: float
    max_price: float


# ---------- agent tool results (tools.py) ----------
# What the agent sees when it looks something up. Every figure comes straight from campus_customs.db.

StockStatus = Literal["in_stock", "low_stock", "sold_out"]


class ProductMatch(BaseModel):
    """One search hit: enough to pick the right product and quote its price and sizes."""

    product_id: str
    name: str
    category: str
    colors: list[str]
    price: float = Field(description="US dollars, from catalogue.price")
    stock_status: StockStatus
    sizes_in_stock: list[str]


class SearchResults(BaseModel):
    """search_products result: the best matches plus the true total, so the agent never mistakes one page of results for everything."""

    total_matches: int = Field(description="How many products in the whole catalogue match these words and filters")
    showing: int = Field(description="How many are listed in results (at most the limit)")
    match: Literal["all_words", "any_word", "filters_only"] = Field(
        description="all_words: every result matches every search word, so total_matches is a real count. any_word: nothing matched all "
                    "the words, so these are loose matches ranked by relevance; don't quote total_matches as how many the store has.")
    results: list[ProductMatch]


class ProductDescription(BaseModel):
    """What the item is (no price or stock: use get_price / check_stock for those)."""

    product_id: str
    name: str
    category: str
    garment_type: str
    description: str
    colors: list[str]
    tags: list[str] = Field(description="Search tags from the catalogue, e.g. 'dad shirt', 'Saybrook'")
    product_page: str = Field(description="Site path the shopper can open, e.g. /products/yale-dad-t-shirt")


class PriceQuote(BaseModel):
    product_id: str
    name: str
    price: float = Field(description="US dollars, from catalogue.price")
    currency: Literal["USD"] = "USD"
    note: str = "List price from the store database. There are no discounts or promo codes."


class SizeAvailability(BaseModel):
    size: str
    quantity: int = Field(ge=0, description="Units on hand, from inventory.quantity")
    status: StockStatus = Field(description="sold_out = 0, low_stock = 1–5, in_stock = 6+")


class StockReport(BaseModel):
    """Stock for one product, size by size, plus a ready-made plain-English summary."""

    product_id: str
    name: str
    price: float
    sizes: list[SizeAvailability] = Field(description="Every size the product is made in, XS→XXL")
    sizes_in_stock: list[str]
    sizes_sold_out: list[str]
    total_in_stock: int
    requested_size: str | None = Field(default=None, description="The size the shopper asked about, if any")
    requested_size_status: StockStatus | None = Field(default=None, description="Status of requested_size; null if not asked or not a size this product comes in")
    requested_size_quantity: int | None = None
    summary: str = Field(description="One true sentence to build the answer from, e.g. 'Sold out in XL. In stock in XS, S, M, L, and XXL.'")
    checked_at: str = Field(description="UTC time the database was read; stock can change")


class ProductNotFound(BaseModel):
    """Returned instead of a result when the product can't be identified. Never guess: use a suggestion's id or ask."""

    query: str
    message: str
    suggestions: list[ProductMatch] = Field(default_factory=list, description="Closest real products, if any")


class Alternative(ProductMatch):
    why: str = Field(description="Why it's a good substitute, e.g. 'Also a Crewneck · in stock in XXL · also Saybrook'")
    color_match: Literal["exact", "close", "not_requested"] = "not_requested"


class AlternativesResult(BaseModel):
    """find_alternatives result: what's wrong with the original, and real in-stock substitutes that fix it."""

    original: ProductMatch | None = Field(default=None, description="The product being replaced, if one was given")
    original_status: str = Field(description="Plain statement of the problem, e.g. 'Sold out in XXL' or 'Comes in navy blue and white, not pink'")
    requested_size: str | None = None
    requested_color: str | None = None
    alternatives: list[Alternative] = Field(description="Best first. Every one is in stock in requested_size and comes in requested_color (or a close shade).")
    note: str = ""


class CatalogueOverview(BaseModel):
    product_count: int
    categories: dict[str, int] = Field(description="Shop category → number of products")
    colors: list[str]
    sizes: list[str]
    price_range_usd: tuple[float, float]


# ---------- accounts ----------

class SignupRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=60)
    last_name: str = Field(min_length=1, max_length=60)
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    confirm_password: str | None = Field(default=None, max_length=200, description="If sent, must equal password")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class PublicUser(BaseModel):
    """A user as the front end sees it. Never includes the password hash."""

    id: int
    first_name: str
    last_name: str
    name: str
    email: str
    created_at: str


class AuthResponse(BaseModel):
    token: str
    user: PublicUser


# ---------- chat ----------

class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class PageContext(BaseModel):
    """Where the shopper is on the site, sent by the front end with each message. Untrusted: the server checks it."""

    path: str = Field(default="/", max_length=200, description="e.g. /products/champion-full-zip-hood")
    product_id: str | None = Field(default=None, max_length=120, description="Set on a product page")
    category: str | None = Field(default=None, max_length=40, description="Products page category filter, if any")
    search: str | None = Field(default=None, max_length=100, description="Products page search words, if any")
    saved_ids: list[str] = Field(default_factory=list, max_length=30, description="Products the shopper saved (wishlist)")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20, description="Recent turns for signed-out shoppers; signed-in history comes from the database")
    page: PageContext | None = None


class CurrentPage(BaseModel):
    """The server-verified version of PageContext that the agent sees (and get_current_page returns)."""

    path: str
    kind: Literal["home", "products", "product", "about", "login", "signup", "saved", "other"]
    product_id: str | None = Field(default=None, description="The product on screen; 'this' / 'it' usually means this one")
    product_name: str | None = None
    category: str | None = None
    search: str | None = None
    saved: list[dict[str, str]] = Field(default_factory=list, description="The shopper's saved items: [{product_id, name}], verified")

    def describe(self) -> str:
        if self.kind == "product" and self.product_id:
            return f"product page for {self.product_name} (product_id {self.product_id})"
        if self.kind == "products":
            bits = [f"category {self.category}" if self.category else "", f"search '{self.search}'" if self.search else ""]
            return "Products page" + (f" filtered by {' and '.join(b for b in bits if b)}" if any(bits) else " (all products)")
        return {"home": "Home page", "about": "About Us page", "login": "Log in page", "signup": "Create Account page",
                "saved": "Saved items page"}.get(self.kind, f"page {self.path}")


class ShopperProfile(BaseModel):
    """Who is chatting, from the users table (get_my_account). Never includes the password hash."""

    signed_in: bool
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    member_since: str | None = Field(default=None, description="Account creation date (YYYY-MM-DD)")
    saved_messages: int = Field(default=0, description="How many messages are in their saved chat history")


class ProductPick(BaseModel):
    """One product the agent wants shown on the page, plus a short line on why it fits."""

    product_id: str = Field(description="A product_id returned by a tool this turn")
    highlight: str = Field(max_length=120, description="Short info for the card (up to ~90 characters) from the description or tags, e.g. 'Navy pullover with a big white YALE across the chest'. No prices or stock numbers; the card shows those live.")


class BrowseLink(BaseModel):
    """Filters for a 'See all' link to the full Products page when there are more matches than cards."""

    category: str | None = Field(default=None, description="Hoodies, Crewnecks, T-Shirts, Long Sleeves, Quarter-Zips, or Jackets & Fleece")
    query: str | None = Field(default=None, description="Search words, e.g. 'Saybrook' or 'mom'")
    color: str | None = None


class ChatReply(BaseModel):
    """The agent's structured output for one chat turn (the agent side of the product-card contract)."""

    reply: str = Field(description="Friendly answer in short markdown. Prices and stock must come from tool results this turn.")
    showcase_title: str | None = Field(default=None, max_length=60, description="Heading for the cards on the page, e.g. 'Hoodies we carry' or 'Gifts for a Yale parent'. Null when picks is empty.")
    picks: list[ProductPick] = Field(default_factory=list, max_length=12, description="Products to show as cards on the page, best first. Empty for policy questions or small talk.")
    browse: BrowseLink | None = Field(default=None, description="Set when the shopper asked about a whole type or search (e.g. all hoodies), so the page can link to every match")


class ShowcaseCard(ProductCard):
    """A product card the page renders: live catalogue and stock data plus the agent's highlight."""

    highlight: str


class Showcase(BaseModel):
    """The site side of the contract: what the front end renders as dynamic product cards."""

    title: str
    items: list[ShowcaseCard]
    browse: BrowseLink | None = None
    total_matches: int | None = Field(default=None, description="How many products the browse link would show, when set")


class Checks(BaseModel):
    """What the backend actually looked up this turn, written from the tool calls (not by the model)."""

    checked_at: str = Field(description="UTC ISO time of the lookups")
    items: list[str] = Field(description="e.g. 'live stock for Saybrook College Crewneck', 'searched \"hoodies\" (27 matches)'")


class ChatResponse(BaseModel):
    reply: str
    checks: Checks | None = Field(default=None, description="Database lookups behind this answer; null if none")
    showcase: Showcase | None = Field(default=None, description="Cards to render on the page; null when the reply isn't about products")
    effort: Literal["low", "high"] = Field(description="Reasoning effort used for this turn")


class ChatMessageOut(BaseModel):
    id: int
    role: Literal["user", "assistant"]
    content: str
    showcase: Showcase | None = None
    page: CurrentPage | None = Field(default=None, description="Where a user message was sent from")
    checks: Checks | None = None
    created_at: str


# ---------- audit trail (audit.py) ----------

class AuditEntry(BaseModel):
    """One step of one agent turn, appended to output/audit_trail.json. The file is never truncated or rewritten from scratch."""

    run_id: str = Field(description="Shared by every entry of one chat turn, so a turn can be read back in order")
    timestamp: str = Field(description="UTC ISO time of this step")
    step: int = Field(description="1-based order within the turn")
    event: Literal["turn_started", "tool_call", "validation_retry", "final_answer", "run_stopped"]
    shopper: str = Field(description="'user:<id>' or 'guest'. Never a name or email")
    page: str | None = Field(default=None, description="Verified page path the message came from")
    effort: Literal["low", "high"] | None = None
    tool_name: str | None = None
    tool_args: dict[str, str] | None = Field(default=None, description="Arguments, each cut to 120 characters and redacted")
    result_summary: str | None = Field(default=None, description="Short, redacted summary of the tool result or answer (at most 240 characters)")
    stop_reason: Literal["completed", "validation_failed", "usage_limit", "content_filter", "error"] | None = Field(
        default=None, description="Only on the run_stopped entry")
    duration_ms: int | None = Field(default=None, description="On run_stopped: how long the whole turn took")
    model_requests: int | None = Field(default=None, description="On run_stopped: model round trips used (limit 8)")
    tokens_in: int | None = None
    tokens_out: int | None = None
