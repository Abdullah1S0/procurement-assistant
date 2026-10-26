"""Helpers shared by graph nodes."""
from __future__ import annotations

import functools
import json
import logging
import re
import time
from typing import Any, Callable

from app.agent.state import AgentState
from app.db.schema import looks_like_meta_question, meta_reply

log = logging.getLogger("agent")
# Never shown to the user as-is - the model's own text on a forced-tool-call failure can contain
# hallucinated sample data (see `safe_tool_failure_reply`).
_REPHRASE_REPLY = {
    "en": "I couldn't turn that into an answer - could you rephrase the question?",
    "ar": "لم أستطع تحويل هذا إلى إجابة، هل يمكنك إعادة صياغة السؤال؟",
}
ARABIC = re.compile(r"[؀-ۿ]")
# Unicode space separators the model sometimes emits (e.g. U+202F around numbers) that render
# oddly or break copy-paste; normalised to a plain space.
UNUSUAL_SPACES = re.compile("[   -     　]")


def detect_language(text: str) -> str:
    """Return 'ar' if the text contains Arabic script, else 'en'."""
    return "ar" if ARABIC.search(text or "") else "en"


def clean_text(text: str) -> str:
    """Replace non-breaking/unusual Unicode space characters with a normal space."""
    return UNUSUAL_SPACES.sub(" ", text or "")


def safe_tool_failure_reply(question: str, language: str, raw_text: str) -> str:
    """Decide what to show the user when a forced tool call fails even after the auto-tool_choice
    retry. The model's own `raw_text` is NEVER returned directly - tested in production, it can
    contain hallucinated sample rows/values. Only used for logging. If the question looks like a
    meta-question, answer with the canned `meta_reply`; otherwise ask the user to rephrase."""
    log.warning("tool_call_fallback_text question=%r raw_text=%r", question, raw_text[:500])
    if looks_like_meta_question(question):
        return meta_reply("ar" if language == "ar" else "en")
    return _REPHRASE_REPLY.get(language, _REPHRASE_REPLY["en"])


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
