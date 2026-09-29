"""Drive the live site like a shopper and save screenshots for output/app_check.html.

Needs the backend on :8000 and the front end on :5173. Run with any Python that has Playwright, e.g.
  ../../HW2/.venv/bin/python scripts/capture_app_check.py
Writes output/app_check_images/*.png and output/app_check_images/results.json (replies + database values).
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

HW4 = Path(__file__).resolve().parents[1]
OUT = HW4 / "output" / "app_check_images"
DB = HW4 / "data" / "campus_customs.db"  # local data pack
SITE = "http://localhost:5173"


def db_stock(product_id: str) -> dict:
    con = sqlite3.connect(DB)
    name, price = con.execute("SELECT name, price FROM catalogue WHERE product_id = ?", (product_id,)).fetchone()
    order = ["XS", "S", "M", "L", "XL", "XXL"]
    rows = dict(con.execute("SELECT size, quantity FROM inventory WHERE product_id = ?", (product_id,)).fetchall())
    return {"product_id": product_id, "name": name, "price": price, "inventory": {s: rows.get(s) for s in order}}


def ask(page: Page, text: str, timeout: float = 120) -> dict:
    """Type into the chat and wait until Boola's answer (not the 'sniffing' placeholder) arrives."""
    if not page.locator(".chat").count():
        page.click(".chat-launcher")
    before = page.locator(".msg-assistant .bubble:not(.typing)").count()
    page.fill(".chat-input textarea", text)
    page.keyboard.press("Enter")
    start = time.time()
    page.wait_for_function(
        f"document.querySelectorAll('.msg-assistant .bubble:not(.typing)').length > {before} && !document.querySelector('.typing')",
        timeout=timeout * 1000,
    )
    page.wait_for_timeout(1200)  # let the cards finish their entrance animation
    last = page.locator(".msg-assistant").last
    return {
        "question": text,
        "seconds": round(time.time() - start, 1),
        "reply": last.locator(".bubble").inner_text(),
        "checks": last.locator(".checks").inner_text() if last.locator(".checks").count() else None,
        "chat_cards": last.locator(".msg-products .tile-name").all_inner_texts(),
    }


def show_answer(page: Page) -> None:
    """Scroll the chat so the latest question and Boola's written answer are at the top of the panel."""
    page.evaluate("""() => {
        const list = document.querySelector('.chat-list'); const msgs = list.querySelectorAll('.msg-user');
        const q = msgs[msgs.length - 1]; list.scrollTop = q.offsetTop - list.offsetTop - 8 }""")
    page.mouse.move(5, 400)  # keep the pointer off product photos (they zoom on hover)
    page.wait_for_timeout(300)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict = {"site": SITE, "captured_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)

        # 1. Inventory: a guest on the Saybrook College Crewneck page asks about sizes.
        page.goto(f"{SITE}/products/saybrook-college-crewneck")
        page.wait_for_selector(".product-page h1")
        chat = ask(page, "How much is this? Is it in stock in XXL, and how many are left in L?")
        show_answer(page)
        page.locator(".chat").screenshot(path=OUT / "inventory_chat.png")
        page.click(".chat-close")  # then the product page itself, whose price and size chips come straight from the database
        page.evaluate("window.scrollTo(0, 0)")
        page.mouse.move(5, 400)
        page.wait_for_timeout(600)
        page.screenshot(path=OUT / "inventory_page.png", clip={"x": 0, "y": 0, "width": 1440, "height": 820})
        results["inventory"] = {**chat, "page_sizes": page.locator(".product-page .size").all_inner_texts(),
                                "database": db_stock("saybrook-college-crewneck")}

        # 2. Dynamic cards: a fresh visitor on the Home page asks a category question.
        page.goto(SITE)
        page.evaluate("sessionStorage.clear(); localStorage.clear()")
        page.goto(SITE)
        page.wait_for_selector(".storefront")
        chat = ask(page, "What hoodies do you have?")
        show_answer(page)
        page.screenshot(path=OUT / "hoodie_cards.png")
        showcase = page.locator("#chat-showcase")
        results["cards"] = {**chat, "page": page.url, "title": showcase.locator("h2").inner_text(),
                            "meta": showcase.locator(".showcase-head .muted").inner_text(),
                            "cards": showcase.locator(".tile-name").all_inner_texts(),
                            "prices": showcase.locator(".tag-price").all_inner_texts(),
                            "see_all": showcase.locator(".showcase-actions .btn").get_attribute("href")}
        page.click(".chat-close")
        page.wait_for_timeout(400)
        page.screenshot(path=OUT / "hoodie_cards_page.png")
        first = showcase.locator(".tile").first
        clicked = first.locator(".tile-name").inner_text()
        first.click()
        page.wait_for_selector(".product-page h1")
        page.mouse.move(5, 400)
        page.wait_for_timeout(900)
        page.screenshot(path=OUT / "card_opens_product.png")
        results["cards"]["clicked_card"] = clicked
        results["cards"]["opened"] = {"url": page.url, "h1": page.locator(".product-page h1").inner_text(),
                                      "price": page.locator(".detail-price").inner_text()}
        con = sqlite3.connect(DB)
        results["cards"]["database_hoodie_count"] = sum(
            1 for (g,) in con.execute("SELECT garment_type FROM catalogue") if any(k in g.lower() for k in ("hoodie", "hooded"))
            and not any(k in g.lower() for k in ("quarter-zip", "jacket", "fleece", "bomber")))

        # 3. Problem 9 usability feature: instant search suggestions in the header.
        page.evaluate("sessionStorage.clear()")
        page.goto(SITE)
        page.wait_for_selector(".storefront")
        page.click(".search-wrap input")
        page.keyboard.type("dad", delay=90)
        page.wait_for_selector(".suggest-item")
        page.wait_for_timeout(500)
        page.keyboard.press("ArrowDown")
        page.keyboard.press("ArrowDown")
        page.wait_for_timeout(250)
        page.screenshot(path=OUT / "instant_search.png", clip={"x": 0, "y": 0, "width": 1440, "height": 560})
        results["search"] = {"typed": "dad", "suggestions": page.locator(".suggest-item").all_inner_texts(),
                             "actions": page.locator(".suggest-action").all_inner_texts(),
                             "highlighted": page.locator(".suggest-item.active .suggest-name").inner_text(),
                             "database": [db_stock(p) for p in ("yale-dad-crewneck", "yale-dad-hoodie", "yale-dad-t-shirt")]}
        page.keyboard.press("Enter")
        page.wait_for_selector(".product-page h1")
        results["search"]["enter_opened"] = {"url": page.url, "h1": page.locator(".product-page h1").inner_text()}

        # Bonus (Problem 9): find_alternatives when a size is sold out, from the Yale Dad T-Shirt page.
        page.evaluate("sessionStorage.clear()")
        page.goto(f"{SITE}/products/yale-dad-t-shirt")
        page.wait_for_selector(".product-page h1")
        chat = ask(page, "Do you have this in XL?")
        show_answer(page)
        page.screenshot(path=OUT / "alternatives.png")
        results["alternatives"] = {**chat, "inline_cards": page.locator(".product-page #chat-showcase .tile-name").all_inner_texts(),
                                   "database": db_stock("yale-dad-t-shirt"),
                                   "alternatives_xl_stock": {n: db_stock(pid)["inventory"]["XL"] for pid, n in con.execute(
                                       "SELECT product_id, name FROM catalogue").fetchall()
                                       if n in page.locator(".product-page #chat-showcase .tile-name").all_inner_texts()}}
        browser.close()
    (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
