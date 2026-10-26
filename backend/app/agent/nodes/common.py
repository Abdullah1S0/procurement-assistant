"""Helpers shared by graph nodes."""
from __future__ import annotations

import functools
import json
import logging
import re
import time
from typing import Any, Callable

from app.agent.state import AgentState

log = logging.getLogger("agent")
ARABIC = re.compile(r"[؀-ۿ]")


def detect_language(text: str) -> str:
    """Return 'ar' if the text contains Arabic script, else 'en'."""
    return "ar" if ARABIC.search(text or "") else "en"


def compact_json(obj: Any, limit: int | None = None) -> str:
    """Minified JSON (non-ASCII kept), optionally truncated."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    return s if limit is None or len(s) <= limit else s[:limit] + "…"


def traced(name: str) -> Callable[[Callable[[AgentState], dict]], Callable[[AgentState], dict]]:
    """Decorator: time a node and attach an `event` ({node, detail, ms}) used for progress streaming + logs."""

    def deco(fn: Callable[[AgentState], dict]) -> Callable[[AgentState], dict]:
        @functools.wraps(fn)
        def wrapper(state: AgentState) -> dict:
            t0 = time.perf_counter()
            update = fn(state) or {}
            ms = int((time.perf_counter() - t0) * 1000)
            event = {"node": name, "ms": ms, **update.pop("_event", {})}
            log.info("node=%s ms=%d %s", name, ms, compact_json({k: v for k, v in event.items() if k not in ("node", "ms")}, 500))
            update["event"] = event
            return update

        return wrapper

    return deco
