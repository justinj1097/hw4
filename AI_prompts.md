# AI prompts

## Problem 1 — Campus Customs website with a chatbot

### Prompt

Campus Customs needs a real customer website with a helpful chatpot. you will build a React + Vite TypeScript front end and a Python FastAPI backend whose brain is a PydanticAI agent. Shoppers should be able to browse products, create an account, chat about merch, see matching items appear on the page, and get honest answers about price and stock from a local database.

you are given campus_customs.db with tables for the product catalogue, inventory by size, and users (with hashed passwords). Product image file paths are in the catalogue table. Research yalebulldogblue.com to learn the style of Campus Customs page and information for your agent prompt.

Use your PORTKEY_API_KEY, or whatever API key you have for your agent's AI calls. If using OpenAI through Portkey use any models in the 5.6 or 6 series. You may want a smarter model for harder agent steps.

create AI_prompts.md

put one section for each prompt. each section must include:

1. the problem number and title
2. at least one prompt you typed in your own words as much as possible
3. one follow-up prompt if you needed it (and one sentence on what was lacking after the first)

### Follow-up prompt

None needed.

## Problem 2 — Understanding the database

### Prompt

look at the database data/campus_customs.db and understand the fields of each table

at a minimum you should understand catalogue, inventory, and users

start the file output/harness.md - write down each table and its fields, and one short line on why each field matters for the shop or the chatbot

you will keep growing this harness file in later problems (models, tools, safety, specs)

### Follow-up prompt

None needed.

## Problem 3 — Front end pages, product pages, and chat panel

### Prompt

scaffold a React + Vite + TypeScript front end for Campus Customs. Put a nav bar at the top that links to the main pages:

1. Home
2. Products
3. About Us
4. Log in
5. Create Account

Pull Campus Customs-style wording from yalebulldogblue.com for Home and About Us, but write these pages in your own voice (do not copy the original site text)

On the Products page, show product images from the catalogue (use the image paths in the database) with basic product info (name, price, short description)

Make each product open a single-item page (large image on one side, full product text on the other - description, price, sizes/stock when you have them). clicking a card on Products should take the shopper there.

Add a chat interface in the bottom right of the site (a floating chat panel is fine). It does not need to talk to an agent yet - a stub that will call your backend later is enough for this problem.

You will need a small API soon to read the database. It is fine to start a simple FastAPI app in backend/main.py just to serve products and images, then grow it into the agent backend in Problem 5

### Follow-up prompt

None needed.

## Problem 4 — Create account and log in

### Prompt

Build a normal create-account / login flow

1. create account: first name, last name, email, password (confirm password is a nice touch)
2. Log in: email and password

New accounts go in the users table. Make sure to store passwords securely so hackers (human or AI) cannot access them.

The seed database already has a test user you can use while building:

1. email: test@campuscustoms.yale.edu
2. Password: password

Confirm you can log in as that user, and that a brand-new account you create also works

Update output/harness.md with how auth works (what you store for a user and how passwords are protected)

### Follow-up prompt

None needed.

## Problem 5 — Chatbot agent behind FastAPI

### Prompt

Build the shop chatbot as a PydanticAI agent behind FastAPI, plugged into your front-end chat widget. Put the API app in backend/main.py - that is the file you run with Uvicorn. Keep the agent as these four files next to it (same idea as Homework 3):

1. backend/prompts/prompt/md - system prompt (grow this same file later)
2. backend/agent.py - agent entry / wiring
3. backend/tools.py - tools the agent can call
4. backend/models.py - Pydantic / PydanticAI structured types

In main.py, expose a chat route so a message from the website returns a reply from the agent (and whatever else you need for products/auth). You will need your AI model API key for the agent

Put Campus Customs voice and safety basics into prompts/prompt.md (you will expand tools and safety later). Start or update types in models.py for chat replies / product cards as needed.

In output/harness.md, note how the front end talks to FastAPI and how the agent is loaded (prompt file + model)

Make sure the backend runs from the backend/ folder like this:

uvicorn main:app --reload --port 8000

### Follow-up prompt

None needed.

## Problem 6 — Database lookup tools

### Prompt

Give the agent tools that look up real information from campus_customs.db

1. Product Description
2. Price
3. How many are in stock (by size when the customer asks)

The agent must use the database - it should not invent prices or quantities. If a size is out of stock, say so clearly

Expand prompts/prompt.md so the agent knows to call these tools for price and stock questions. Add or update return types in models.py

In output/harness.md, list each tool and explain which model fields you chose for lookup results and why

### Follow-up prompt

None needed.

## Problem 7 — Chat results as product cards on the page

### Prompt

Now we will add a neat feature to the site. When a customer asks about a type of item - for example "what hoodies do you have?" - the agent should search the catalogue and the website should dynamically show those matching items as product cards (image, name, price, short info).

This is an API contract: the agent returns structured product matches and then the front end renders them on the website. It looks really cool

After the dynamic product cards are loaded by your new feature, make sure the same single-item page behavior you built in Problem 3 still works: each product card - including the ones the chat just put on the page - should still open that detail view (large image + full info) when clicked

Update prompts/prompt.md and output/harness.md so it is clear how search results reach the page

### Follow-up prompt

None needed.

## Problem 8 — Saved chat history, who is chatting, and page context

### Prompt

When a shopper is logged in, save their chat history in the database in an appropriate table and reload it when they return. The agent should know who is chatting (name, email) - put that in agent deps (or an equivalent clear pattern) and/or tools the agent can call

Also pass enough page context that if someone is on a product page and asks "do you have this in pink?", the agent knows which item they mean. Hint: you can put code into the agent context

Guests can still chat, but history only needs to persist for logged-in users.

Document in output/harness.md: how user chat history is stored, what customer fields the agent sees, and how page context is passed

### Follow-up prompt

None needed.

## Problem 9 — Usability improvements

### Prompt

Now that the core shop works, improve it. Choose and implement:

1. 2 front-end usability improvements
2. 2 agent / backend usability improvements

Front-end improvements are things that make the site look better and make it easier to use

Agent / backend improvements are things that make the agent output better, more accurate, or safer. These could be new agent tools or things that make the agent run faster or cheaper

Write output/usability.md before or as you build. For each of the improvements, say:

1. what you added
2. why it helps a Campus Customs shopper or the business

Then make sure all improvements actually show up in the running app. Graders will read the write-up and look for the features

### Follow-up prompt

None needed.

## Problem 10 — Storefront design

### Prompt

Add creative design so the site feels like a real Campus Customs storefront - fonts, color, hierarchy, motion, product presentation, chat feel.

You will get more points for imaginative and innovative design

Write output/design.md: what you changed and why it should help customers stick around and buy. Keep it concrete and short

### Follow-up prompt

None needed.

## Problem 11 — Live app check

### Prompt

Test the live site and document it in output/app_check.html (a page you can double-click open). Include clear screenshots and shorts captions for :

1. Chat checking the inventory level of an item (honest stock/price from the DB)
2. The dynamic search-result cards appearing after a category question (e.g. hoodies)
3. One of the usability features you added in Problem 9

Make the HTML easy to grade: heading for each check, screenshot, one or two sentences on what the screenshot proves.

Put the screenshot image files in output/app_check_images/ and link them from app_check.html with relative paths (for example app_check_images/inventory.png)

### Follow-up prompt

None needed.

## Problem 12 — Audit trail, safety rules, and the finished harness

### Prompt

Keep an append-only output/audit_trail.json of agent-loop activity (time, tool name, short args/result, stop reason). Do not wipe it between runs.

Also, think of some safety rules to give the agent and put them in prompts/prompt.md

Finish output/harness.md so it is clear how the system works.

1. Model fields in models.py and why you chose them
2. Tools and abilities
3. Safety rules
4. Specs (loop limits, result caps, models, how to run front + back)

### Follow-up prompt

None needed.
