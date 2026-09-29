"""Password hashing, login throttling, and signed login tokens.

Two stored formats are accepted:
  * ``pbkdf2_sha256$<salt>$<hex digest>``: the seed database's format. It doesn't record the iteration count; the seed
    accounts use 120,000 (confirmed against the known test account).
  * ``pbkdf2_sha256$<iterations>$<salt>$<hex digest>``: what new accounts get. It is self-describing, so the work
    factor can be raised later without breaking older accounts.
Only the salted hash is ever stored. The password itself is never saved, logged, or returned.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict, deque

from config import SESSION_SECRET, SESSION_TTL_SECONDS

ALGORITHM = "pbkdf2_sha256"
SEED_ITERATIONS = 120_000  # work factor used by the seed database's 3-part hashes
NEW_ITERATIONS = 600_000  # OWASP's current recommendation for PBKDF2-HMAC-SHA256
SALT_BYTES = 16  # 128-bit random salt per password
MIN_PASSWORD, MAX_PASSWORD = 8, 200  # the cap stops huge inputs being used to tie up the CPU

# A short blocklist of the passwords attackers try first.
COMMON_PASSWORDS = {
    "password", "password1", "password123", "passw0rd", "12345678", "123456789", "1234567890", "qwerty123", "qwertyuiop",
    "iloveyou", "letmein1", "welcome1", "admin123", "abc12345", "11111111", "00000000", "yale1701", "bulldogs", "boolaboola",
}


def _digest(password: str, salt: str, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_BYTES)
    return f"{ALGORITHM}${NEW_ITERATIONS}${salt}${_digest(password, salt, NEW_ITERATIONS)}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check against either stored format. Unknown formats never match."""
    if len(password) > MAX_PASSWORD:
        return False
    parts = stored.split("$")
    if len(parts) == 4 and parts[0] == ALGORITHM and parts[1].isdigit():
        _, iterations, salt, expected = parts
        return hmac.compare_digest(_digest(password, salt, int(iterations)), expected)
    if len(parts) == 3 and parts[0] == ALGORITHM:
        _, salt, expected = parts
        return hmac.compare_digest(_digest(password, salt, SEED_ITERATIONS), expected)
    return False


_DUMMY_HASH = hash_password(secrets.token_hex(16))


def burn_time(password: str) -> None:
    """Do the same work as a real check, so an unknown email takes as long as a wrong password (no account probing)."""
    verify_password(password, _DUMMY_HASH)


def password_problem(password: str, email: str, first_name: str = "", last_name: str = "") -> str | None:
    """Why a new password is too weak, or None if it's acceptable."""
    lowered = password.lower()
    if len(password) < MIN_PASSWORD:
        return f"Use at least {MIN_PASSWORD} characters."
    if len(password) > MAX_PASSWORD:
        return f"Use at most {MAX_PASSWORD} characters."
    if lowered in COMMON_PASSWORDS or len(set(password)) < 4:
        return "That password is too easy to guess. Try a longer phrase."
    local = email.split("@", 1)[0].lower()
    if (len(local) >= 4 and local in lowered) or any(len(n) >= 3 and n.lower() == lowered for n in (first_name, last_name)):
        return "Don't use your name or email in your password."
    return None


# ---------- login throttling ----------

class LoginThrottle:
    """At most MAX_FAILURES failed logins per email (and per client IP) in WINDOW seconds. In memory, per process."""

    MAX_FAILURES = 5
    WINDOW = 15 * 60

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        q = self._failures[key]
        while q and now - q[0] > self.WINDOW:
            q.popleft()
        return q

    def retry_after(self, *keys: str) -> int:
        """Seconds until another attempt is allowed (0 if allowed now)."""
        now = time.time()
        with self._lock:
            waits = [int(self.WINDOW - (now - q[0])) + 1 for k in keys if len(q := self._recent(k, now)) >= self.MAX_FAILURES]
        return max(waits, default=0)

    def fail(self, *keys: str) -> None:
        with self._lock:
            for k in keys:
                self._failures[k].append(time.time())

    def reset(self, *keys: str) -> None:
        with self._lock:
            for k in keys:
                self._failures.pop(k, None)


throttle = LoginThrottle()


# ---------- login tokens: base64(payload).HMAC-SHA256 ----------

def _sign(data: bytes) -> str:
    return base64.urlsafe_b64encode(hmac.new(SESSION_SECRET.encode(), data, hashlib.sha256).digest()).decode().rstrip("=")


def create_token(user_id: int) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"uid": user_id, "exp": int(time.time()) + SESSION_TTL_SECONDS}).encode()).decode().rstrip("=")
    return f"{payload}.{_sign(payload.encode())}"


def read_token(token: str) -> int | None:
    """Return the user id for a valid, unexpired token, else None."""
    try:
        payload, signature = token.split(".", 1)
        if not hmac.compare_digest(signature, _sign(payload.encode())):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return int(data["uid"]) if data.get("exp", 0) > time.time() else None
    except (ValueError, KeyError, json.JSONDecodeError):
        return None
