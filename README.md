# Homework 4 — Campus Customs storefront with an AI shopping assistant

A customer website for **Campus Customs**, the official Yale merchandise store at 57 Broadway, New Haven. Shoppers can:
- browse all 102 products;
- create an account and log in;
- chat with **Boola**, a bulldog shopping assistant;
- see the products the chat recommends appear on the page as cards;
- get honest price and stock answers straight from the store database.

| Part | Stack |
| --- | --- |
| Front end | React + Vite + TypeScript (`frontend/`) |
| Back end | Python FastAPI (`backend/main.py`) |
| Agent | PydanticAI, `gpt-5.6-luna` through Portkey. Four files: `backend/prompts/prompt.md`, `backend/agent.py`, `backend/tools.py`, `backend/models.py` |
| Data | Local-only data pack in `data/`: `campus_customs.db` and `products/`. **Not in git** |

How everything works (models, tools, safety rules, limits) is in [`output/harness.md`](output/harness.md). The design and usability write-ups are in `output/design.md` and `output/usability.md`. The live test with screenshots is `output/app_check.html`.

## Layout

```
hw4/
├── AI_prompts.md            prompts used for each problem
├── requirements.txt         Python dependencies (backend)
├── .env.example             placeholders only; copy to .env
├── .gitignore               keeps .env, data/, and build output out of git
├── README.md
├── frontend/                Vite React TypeScript app
├── backend/
│   ├── main.py              FastAPI app, run with: uvicorn main:app --reload --port 8000
│   ├── agent.py             agent wiring: prompt + model + tools + honesty checks + audit
│   ├── tools.py             tools the agent calls (search, description, price, stock, alternatives, …)
│   ├── models.py            Pydantic types for the API, tools, and agent
│   ├── prompts/prompt.md    system prompt: voice, honesty and safety rules, store policies
│   ├── db.py auth.py config.py images.py safety.py audit.py   support modules
│   └── tests/               offline tests (no AI calls)
├── scripts/capture_app_check.py   drives the live site and takes the app-check screenshots
├── output/                  harness.md, design.md, usability.md, app_check.html, app_check_images/, audit_trail.json
└── data/                    ← local-only data pack (git-ignored), you add this
    ├── campus_customs.db
    └── products/            images referenced by the catalogue
```

## Run it

You need **Python 3.11+**, **Node 20+**, and a **Portkey API key**.

### 1. Get the data pack

The database and product photos aren't in this repository. Put the course data pack in `hw4/data/` so that these exist:

```
hw4/data/campus_customs.db
hw4/data/products/2025-yale-vs-harvard-t-shirt.jpg   (…and the other product images)
```

The backend checks for them on start and exits with a clear message if they're missing. It also creates `data/products_web/` (white-background display copies of the photos) the first time it runs. The originals are never changed.

### 2. Add your API key

```bash
cp .env.example .env
```

Then edit `.env` and set `PORTKEY_API_KEY`. `.env` is git-ignored.

### 3. Start the backend (FastAPI, port 8000)

From `hw4/`:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
```bash
cd backend && ../.venv/bin/uvicorn main:app --reload --port 8000
```

Or, with the virtual environment activated (`source .venv/bin/activate`), run `uvicorn main:app --reload --port 8000` from `backend/`. Check it at http://localhost:8000/api/health.

### 4. Start the front end (Vite, port 5173)

In a second terminal, from `hw4/`:

```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:5173**. The Vite dev server forwards `/api` and `/images` to the backend on port 8000, so both must be running.

Try it:
- log in as the seed account `test@campuscustoms.yale.edu` / `password`, or create your own account;
- open the chat (**Ask Boola**, bottom right) and ask "What hoodies do you have?";
- on a product page, ask "Is this in stock in XL?".

### 5. Tests (optional)

These make no AI calls, and they use temporary copies of the database and the audit file:

```bash
cd backend && ../.venv/bin/python -m pytest -q
```

## Notes

- **Honest answers:** every price and stock figure comes from the database through the agent's tools, and code rejects any reply whose numbers don't match what the tools returned. See "Safety rules" in `output/harness.md`.
- **Accounts:** passwords are stored only as salted PBKDF2-SHA256 hashes. Signed-in chats are saved in the database's `chat_messages` table.
- **Audit trail:** every chat turn appends its steps (tools, short arguments and results, stop reason) to `output/audit_trail.json`, which is never wiped.
- **Checking the screenshots:** `python scripts/capture_app_check.py` retakes the `output/app_check.html` screenshots. It needs both servers running and `pip install playwright && playwright install chromium`.
