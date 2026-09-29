"""Paths and settings. Secrets come from the environment or the workspace .env; nothing secret is hard-coded."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
# The data pack (campus_customs.db + products/) is local-only and not in git: place it in hw4/data/ (see README).
DATA_DIR = Path(os.getenv("CAMPUS_CUSTOMS_DATA", BACKEND_DIR.parent / "data"))
DB_PATH = Path(os.getenv("CAMPUS_CUSTOMS_DB", DATA_DIR / "campus_customs.db"))
if not DB_PATH.is_file() or not (DATA_DIR / "products").is_dir():
    raise SystemExit(f"Data pack not found. Put campus_customs.db and products/ in {DATA_DIR} (or set CAMPUS_CUSTOMS_DATA). See README.md.")
PROMPT_PATH = BACKEND_DIR / "prompts" / "prompt.md"


def load_env() -> None:
    """Read KEY=VALUE lines from the nearest .env (backend/, HW4/, or the workspace root) without overriding real env vars."""
    for folder in (BACKEND_DIR, BACKEND_DIR.parent, *BACKEND_DIR.parents):
        path = folder / ".env"
        if path.is_file():
            for line in path.read_text().splitlines():
                key, sep, value = line.partition("=")
                if sep and key.strip() and not key.strip().startswith("#") and key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
            return


load_env()

PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY", "")
PORTKEY_BASE_URL = os.getenv("PORTKEY_BASE_URL", "https://api.portkey.ai/v1")
PORTKEY_PROVIDER = os.getenv("PORTKEY_PROVIDER", "openai")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5.6-luna")

def _session_secret() -> str:
    """Signs login tokens. Uses SESSION_SECRET if set; otherwise a random one saved in backend/.session_secret (git-ignored),
    so shoppers stay signed in when the server restarts."""
    if os.getenv("SESSION_SECRET"):
        return os.environ["SESSION_SECRET"]
    path = BACKEND_DIR / ".session_secret"
    if not path.exists():
        path.write_text(secrets.token_hex(32))
        path.chmod(0o600)
    return path.read_text().strip()


SESSION_SECRET = _session_secret()
SESSION_TTL_SECONDS = 7 * 24 * 3600

LOW_STOCK_THRESHOLD = 5
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]

AUDIT_PATH = Path(os.getenv("CAMPUS_CUSTOMS_AUDIT", BACKEND_DIR.parent / "output" / "audit_trail.json"))
CHAT_RATE_LIMIT = (20, 5 * 60)  # at most 20 chat messages per shopper (or IP) per 5 minutes
