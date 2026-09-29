"""Code-level safety checks that run before a chat message reaches the model, the database, or the audit trail."""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict, deque

from config import CHAT_RATE_LIMIT

CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SECRET = re.compile(r"(?i)\b(sk-[a-z0-9_-]{10,}|pk-[a-z0-9_-]{10,}|bearer\s+[a-z0-9._-]{12,}|api[_ -]?key\s*[:=]\s*\S+|password\s*[:=]\s*\S+)")


def _luhn(digits: str) -> bool:
    total, parity = 0, len(digits) % 2
    for i, ch in enumerate(digits):
        d = int(ch)
        if i % 2 == parity:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def mask_sensitive(message: str) -> tuple[str, list[str]]:
    """Mask payment card numbers (Luhn-checked), SSNs, and things that look like keys or passwords. Returns (text, what was masked)."""
    found: list[str] = []

    def card(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if 13 <= len(digits) <= 19 and _luhn(digits):
            found.append("card number")
            return "[card number removed]"
        return m.group()

    text = CARD.sub(card, message)
    if SSN.search(text):
        found.append("social security number")
        text = SSN.sub("[SSN removed]", text)
    if SECRET.search(text):
        found.append("password or key")
        text = SECRET.sub("[secret removed]", text)
    return text, found


def redact(value: object, limit: int = 240) -> str:
    """For logs: no emails, card numbers, SSNs, or secrets, and never more than `limit` characters."""
    text = mask_sensitive(str(value))[0]
    text = EMAIL.sub("[email]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


class RateLimit:
    """Sliding-window limit on chat messages per key (user id or IP). In memory, per process."""

    def __init__(self, limit: int, window: int) -> None:
        self.limit, self.window = limit, window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> int:
        """Record one message; return 0 if allowed, else seconds until the next one is allowed."""
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return int(self.window - (now - q[0])) + 1
            q.append(now)
            return 0


chat_limit = RateLimit(*CHAT_RATE_LIMIT)


# Wellbeing: clear crisis statements get a caring reply without waiting on the model; softer distress signals are only
# used to choose that reply when the provider's content filter blocks the message (so nobody in distress gets "can't help").
CRISIS_STRONG = re.compile(r"\b(kill(ing)? myself|suicid\w*|end (it all|my life)|want(ed)? to die|don'?t want to (live|be alive)|self[- ]?harm|hurt(ing)? myself)\b", re.I)
CRISIS_SOFT = re.compile(r"\b(hopeless|no point|worthless|can'?t go on|can'?t do this anymore|give up on (life|everything)|depress\w*|in crisis)\b", re.I)

CRISIS_REPLY = ("I'm really sorry you're feeling this way. You don't have to handle it alone. If you're in the US, you can call or text "
                "**988** (Suicide & Crisis Lifeline) any time to talk with someone, and if you're in danger right now, please call **911**. "
                "Yale students can also reach Yale Mental Health & Counseling. I'm just a shopping assistant, but I'm here if you need anything else.")


def crisis_signal(message: str, strong_only: bool = False) -> bool:
    return bool(CRISIS_STRONG.search(message) or (not strong_only and CRISIS_SOFT.search(message)))
