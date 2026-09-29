# Usability improvements

Four improvements to the Campus Customs site, two on the front end and two in the agent and backend. Each section says what was added, why it helps a shopper or the business, and where to see it in the running app.

---

## Front end 1: Instant search suggestions

### What I added
- **A live dropdown** under the header search box that updates as you type, after about 0.2 seconds. It shows up to 6 matching products, each with photo, name, category, price, and a stock badge ("Only 4 left", "Sold out").
- **Two shortcuts at the bottom:** "See all N results for '…'", which opens the filtered Products page, and "Ask the assistant about '…'", which sends the search to the chat.
- **Keyboard support:** ↑ / ↓ move through the list, Enter opens the highlighted item (or all results), and Esc closes the dropdown. Clicking outside also closes it.
- **A clear message** when nothing matches ("No products match 'x'"), still with the option to ask the assistant.

### Why it helps
- **Shoppers** find a specific item ("dad", "saybrook", "hockey") in one or two keystrokes, and can see price and stock before clicking. Typos and vague searches have a way out through the assistant instead of a dead end.
- **The business:** fewer "no results" dead ends mean fewer lost shoppers. Seeing a thumbnail and price right away gets people to product pages faster.

### Where to see it
Type in the search box in the header on any page, for example "dad" or "saybrook".

---

## Front end 2: Saved items (wishlist)

### What I added
- **A heart button** on every product card (the Products grid, chat cards, search results, and related items) and a **♡ Save** button on each product page.
- **A "Saved" link in the nav** with a live count, which opens **`/saved`**: a grid of your saved products with **live** price and stock, a "Remove" option, and **"Ask the assistant to compare my saved items"**.
- **The assistant knows what you saved.** The saved product ids are sent with each chat message, checked by the server, and given to the agent. So "Which of my saved items is cheapest?" or "Are my saved items in stock in M?" works.
- **Storage:** saved items live in the browser, so they work for guests and survive reloads, and are kept separate for each signed-in account.

### Why it helps
- **Shoppers** often browse on their phone between classes, or are parents collecting gift ideas. A saved list lets them come back later, and compare prices and sizes side by side, without searching again.
- **The business:** a saved item is a strong sign someone intends to buy. Keeping those items one click away, with live stock and an assistant ready to help decide, turns browsing into purchases at 57 Broadway or online.

### Where to see it
Click ♡ on any product card or product page. The **Saved (n)** count in the nav goes up. Open **Saved** and click "Ask the assistant to compare my saved items".

---

## Agent / backend 1: `find_alternatives` tool (in-stock substitutes)

### What I added
- **A new agent tool, `find_alternatives(product, size, color)`**, which returns real products that could replace one that doesn't work for the shopper.
  - Candidates **must** be in stock in the requested size, and must come in the requested color if one is given.
  - They are ranked by similarity: same category first, then shared search tags, colors, and garment type.
  - The result says why each one was picked ("Also a Crewneck · in stock in XXL · also Saybrook"), plus the original product's actual status ("sold out in XXL", "doesn't come in pink").
- **Color words are matched sensibly**, so "pink" also finds close shades such as "dusty coral". The tool labels those as close shades, not exact matches.
- **The prompt tells the agent to use it** whenever a size is sold out or a color isn't offered, and to show the results as product cards.

### Why it helps
- **Shoppers:** "Sold out in XXL" used to be a dead end, and "Do you have this in pink?" only got "no". Now they get "No, but here are similar crewnecks that do come in XXL", with cards they can click.
- **The business:** a sale that would have been lost to a stock-out becomes a sale of something similar. Recommendations only include items that are really in stock in that size, so the store never promises something it can't sell.
- **Accuracy:** the stock and color checks are done in code, not by the model's judgment.

### Where to see it
Open the Saybrook College Crewneck page (sold out in XXL) and ask the chat "Is this in stock in XXL?". Or, on any navy hoodie page, ask "Do you have this in pink?".

---

## Agent / backend 2: "Checked with the store database" notes

### What I added
- **A short line under every assistant answer** that looked something up, for example:

  > ✓ Checked the store database at 3:04 PM: live stock for Saybrook College Crewneck · price of 2 products · searched "hoodies" (27 matches)

- **It's built by the backend from the tools the agent actually called this turn**, not written by the model, so it can't claim a check that didn't happen. Answers about store policy or small talk show no line.
- The notes are returned as structured `checks` on `ChatResponse` and saved with signed-in chat history, so they come back after a reload.

### Why it helps
- **Shoppers** can trust that "only 2 left in L" or "$58" came from the live store database a moment ago, not from a guess. That matters most for price and stock, the two things a chatbot must never make up.
- **The business:** it's cheap proof of honesty that builds trust in the assistant, and it helps staff check what the bot based an answer on when a customer says "the chat told me…".
- **Safety:** if the agent ever answered a stock question without looking, the missing note would make it obvious.

### Where to see it
Ask the chat any price or stock question, such as "How much is the Yale Mom Hoodie?". The ✓ line appears under the answer.

---

## Checked in the running app

All four were tried in the browser against the running backend (`uvicorn main:app --reload --port 8000`) and front end (`npm run dev`):

| Improvement | What I did | What happened |
| --- | --- | --- |
| Instant search | Typed "dad" in the header search | The dropdown showed Yale Dad Crewneck ($58), Yale Dad Hoodie ($68), and Yale Dad T Shirt ($32), each with "In stock", plus "See all 3 results for 'dad'" and "Ask the assistant about 'dad'". ↓ ↓ highlighted the hoodie, and Enter opened `/products/yale-dad-hoodie` and closed the dropdown |
| Saved items | Clicked **Save** on the product page, then ♡ on two cards on `/products?category=Crewnecks` | The hearts saved without leaving the page. The nav showed **♡ Saved 3**, and `/saved` listed the 3 items with live prices ("3 saved · $184 together") |
| Saved + assistant | Clicked "Ask the assistant to compare my saved items" | Compared price and in-stock sizes for all 3, matching the database (for example, "XL has only 2 left" for the Champion crew, where the database has XL = 2), and showed them as "Your saved items" cards |
| `find_alternatives` | On the Saybrook College Crewneck page, asked "Is this in stock in XXL?" | "…sold out in XXL. It's in stock in XS, S, M, L, and XL. Here are a few XXL alternatives…", with 6 "XXL alternatives" cards, all really in stock in XXL, the Saybrook Logo T Shirt first |
| `find_alternatives` (color) | Asked the API "Do you have this in pink?" from the Basic Hoodie Big Yale page | "…comes in navy blue and white, not pink. The closest shade I found is the **Big Yale Tri Blend T Shirt** in dusty coral…", with a "Closest shade to pink" card |
| Checked notes | Every price or stock answer above | A line under each answer, for example "✓ Checked the store database at 11:35 PM: live stock for Saybrook College Crewneck · in-stock alternatives in XXL (6 found)" |

The offline tests (`backend/tests/test_api.py`, now 20) also cover these:
- `find_alternatives` never returns an item that's sold out in the requested size.
- The "Dad" theme ranks the Yale Dad Hoodie first.
- "Pink" is labelled as close shades only.
- The notes match the tools that actually ran.
- `/api/products?ids=` returns saved items and drops unknown ids.
- Saved ids are checked before the agent sees them.
