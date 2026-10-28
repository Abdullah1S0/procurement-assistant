"""HTTP routes."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from sse_starlette.sse import EventSourceResponse

from app.agent.nodes.common import detect_language
from app.api.models import ChatRequest, ChatResponse
from app.api.service import aiter_chat, run_chat
from app.config import get_settings
from app.db.client import get_client, get_collection
from app.db.schema import FIELDS

log = logging.getLogger("api")
router = APIRouter(prefix="/api")

# The UI must never show a raw exception (stack text, BadRequestError, etc.) - the full exception
# is always logged server-side via log.exception(); only this friendly, localized message (plus
# the existing frontend Retry button) reaches the client.
_FRIENDLY_ERROR = {
    "en": "Something went wrong while answering that - please try again.",
    "ar": "حدث خطأ أثناء محاولة الإجابة - يرجى المحاولة مرة أخرى.",
}


def _friendly_error_detail(message: str) -> str:
    return _FRIENDLY_ERROR[detect_language(message)]

EXAMPLES = [
    {"lang": "en", "text": "How many orders were created in March 2014?"},
    {"lang": "en", "text": "Which quarter had the highest spending?"},
    {"lang": "en", "text": "What are the 5 most frequently ordered line items?"},
    {"lang": "en", "text": "Top 5 departments by spending"},
    {"lang": "en", "text": "Which UNSPSC segment had the highest spend, and what was its top supplier?"},
    {"lang": "en", "text": "How much did Corrections spend on IT Goods per fiscal year?"},
    {"lang": "en", "text": "Show monthly order counts for calendar year 2013"},
    {"lang": "ar", "text": "كم عدد الطلبات اللي انعملت في مارس 2014؟"},
    {"lang": "ar", "text": "ما هي أكثر 3 جهات حكومية إنفاقاً في السنة المالية 2013-2014؟"},
    {"lang": "ar", "text": "كم صرفت الولاية باستخدام بطاقة CalCard في كل سنة مالية؟"},
]


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness + MongoDB connectivity."""
    s = get_settings()
    try:
        get_client().admin.command("ping")
        docs = get_collection().estimated_document_count()
        mongo = "ok"
    except Exception as exc:  # noqa: BLE001
        docs, mongo = 0, f"error: {exc}"
    return {"status": "ok" if mongo == "ok" else "degraded", "mongo": mongo, "documents": docs,
            "llm_provider": s.llm_provider, "llm_model": s.llm_model, "llm_key_configured": bool(s.groq_api_key)
            or s.llm_provider != "groq"}


@router.get("/schema")
def schema() -> dict[str, Any]:
    """Field list for the UI sidebar."""
    return {"collection": get_settings().mongo_collection, "fields": FIELDS}


@router.get("/examples")
def examples() -> list[dict[str, str]]:
    """Suggested questions (English + Arabic)."""
    return EXAMPLES


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Answer one message (non-streaming)."""
    try:
        return await run_in_threadpool(run_chat, req.session_id, req.message)
    except Exception as exc:
        log.exception("chat failed")
        raise HTTPException(status_code=502, detail=_friendly_error_detail(req.message)) from exc


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> EventSourceResponse:
    """Server-Sent Events: `step` events node-by-node, then a `final` event (or `error`)."""

    async def events() -> AsyncIterator[dict[str, str]]:
        try:
            async for kind, payload in aiter_chat(req.session_id, req.message):
                yield {"event": kind, "data": payload.model_dump_json()}
        except Exception as exc:  # noqa: BLE001
            log.exception("chat stream failed")
            yield {"event": "error", "data": json.dumps({"detail": _friendly_error_detail(req.message)})}

    return EventSourceResponse(events())
