"""Append-only audit trail of agent-loop activity: output/audit_trail.json (a JSON list of AuditEntry records).

Every chat turn appends its entries once, when the turn ends (success or failure). Writes are serialised with a lock
and done by writing a temp file then atomically replacing the old one, so a crash mid-write can't lose earlier runs.
The file is never cleared by the app.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from config import AUDIT_PATH
from models import AuditEntry, CurrentPage, PublicUser
from safety import redact

_LOCK = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def summarize(result: Any) -> str:
    """A short, readable, redacted description of a tool result."""
    if isinstance(result, list):
        names = [getattr(r, "name", None) or getattr(r, "query", None) for r in result]
        return redact(f"{len(result)} result(s): " + ", ".join(n for n in names if n))
    if isinstance(result, BaseModel):
        data = result.model_dump()
        if "total_matches" in data:
            return redact(f"{data['total_matches']} match(es), {data['match']}; showing {data['showing']}: "
                          + ", ".join(r["name"] for r in data["results"][:6]))
        if "summary" in data and "sizes" in data:
            return redact(f"{data['name']}: {data['summary']} (${data['price']:g})")
        if "alternatives" in data:
            return redact(f"{data['original_status']}; {len(data['alternatives'])} alternative(s): "
                          + ", ".join(a["name"] for a in data["alternatives"][:5]))
        if "suggestions" in data:
            return redact(f"not found: {data['message']}")
        return redact(json.dumps(data, default=str))
    return redact(result)


class TurnAudit:
    """Collects one turn's entries in memory, then appends them in one locked write."""

    def __init__(self, user: PublicUser | None, page: CurrentPage | None, effort: str) -> None:
        self.run_id = uuid.uuid4().hex[:12]
        self.shopper = f"user:{user.id}" if user else "guest"
        self.page = page.path if page else None
        self.effort = effort
        self.entries: list[AuditEntry] = []

    def add(self, event: str, **fields: Any) -> None:
        args = fields.pop("tool_args", None)
        self.entries.append(AuditEntry(
            run_id=self.run_id, timestamp=_now(), step=len(self.entries) + 1, event=event, shopper=self.shopper, page=self.page,
            effort=self.effort, tool_args={k: redact(v, 120) for k, v in args.items()} if args else None, **fields))

    def flush(self) -> None:
        if self.entries:
            append(self.entries)


def append(entries: list[AuditEntry]) -> None:
    with _LOCK:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing: list = []
        if AUDIT_PATH.exists():
            try:
                existing = json.loads(AUDIT_PATH.read_text() or "[]")
            except json.JSONDecodeError:  # never throw away a damaged log: keep it aside and start a new one
                AUDIT_PATH.rename(AUDIT_PATH.with_suffix(f".corrupt-{int(datetime.now().timestamp())}.json"))
        tmp = AUDIT_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing + [e.model_dump(exclude_none=True) for e in entries], indent=1))
        os.replace(tmp, AUDIT_PATH)


def record_safety_turn(user: PublicUser | None, page: CurrentPage | None, note: str) -> None:
    """Log a turn that code answered without running the agent (e.g. a crisis reply)."""
    trail = TurnAudit(user, page, "low")
    trail.add("final_answer", result_summary=redact(note))
    trail.add("run_stopped", stop_reason="completed", duration_ms=0, model_requests=0)
    trail.flush()
