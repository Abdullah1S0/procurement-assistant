"""`understand` node: classify intent and rewrite follow-ups into standalone questions."""
from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage

from pydantic import BaseModel, Field

from app.agent.nodes.common import detect_language, safe_tool_failure_reply, traced
from app.agent.prompts import UNDERSTAND_SYSTEM
from app.agent.state import AgentState
from app.db.schema import looks_like_meta_question, meta_reply
from app.llm import get_llm, invoke_with_backoff, tool_use_failed_text


class Understanding(BaseModel):  # noqa: N801 - tool name as seen by the LLM
    """Router output."""

    intent: Literal["data_question", "follow_up", "chit_chat", "out_of_scope", "meta_question"]
    standalone_question: str = Field(default="", description="Self-contained English question (data intents only)")
    needs_plan: bool = Field(default=False, description="True if 2+ dependent queries are needed")
    reply: str = Field(default="", description="Short reply for chit_chat / out_of_scope, in the user's language")


def _history_text(state: AgentState, n: int = 3) -> str:
    turns = state.get("turns", [])[-n:]
    if not turns:
        return "(no previous turns)"
    return "\n".join(f"User: {t['user']}\nResolved question: {t['standalone']}\nPipeline: {t['pipeline']}\n"
                     f"Assistant: {t['answer'][:300]}" for t in turns)


@traced("understand")
def understand(state: AgentState) -> dict:
    """Classify the message; for data questions produce a standalone question (resolving follow-ups)."""
    question = state["question"]
    language = detect_language(question)
    msgs = [SystemMessage(UNDERSTAND_SYSTEM),
            HumanMessage(f"Previous turns:\n{_history_text(state)}\n\nLatest user message: {question}")]
    try:
        llm = get_llm(fast=True).with_structured_output(Understanding, method="function_calling")
        u: Understanding = invoke_with_backoff(llm, msgs)
    except Exception as exc:  # noqa: BLE001
        failed_text = tool_use_failed_text(exc)
        if failed_text is None:
            raise

        def _fallback(text: str) -> dict:
            intent = "meta_question" if looks_like_meta_question(question) else "chit_chat"
            safe_text = safe_tool_failure_reply(question, language, text)
            return {
                "language": language, "intent": intent, "standalone_question": question,
                "direct_reply": safe_text, "plan": [question], "needs_plan": False,
                "_event": {"intent": intent, "fallback_text": True},
            }

        # Groq rejected the forced tool call (model answered in plain text); retry once with
        # tool_choice="auto". That retry can hit the exact same failure again (e.g. malformed
        # JSON) - don't let it raise uncaught, fall back the same way.
        try:
            ai = invoke_with_backoff(get_llm(fast=True).bind_tools([Understanding], tool_choice="auto"), msgs)
        except Exception as exc2:  # noqa: BLE001
            retry_failed_text = tool_use_failed_text(exc2)
            if retry_failed_text is None:
                raise
            return _fallback(retry_failed_text)
        call = next((c for c in ai.tool_calls if c["name"] == "Understanding"), None)
        if call is None:
            text = ai.content if isinstance(ai.content, str) and ai.content.strip() else failed_text
            return _fallback(text or "")
        u = Understanding(**call["args"])

    standalone = u.standalone_question.strip() or question
    if u.intent == "meta_question":
        return {
            "language": language, "intent": "meta_question", "standalone_question": standalone,
            "direct_reply": meta_reply(language), "plan": [standalone], "needs_plan": False,
            "_event": {"intent": "meta_question", "standalone_question": standalone},
        }
    return {
        "language": language,
        "intent": u.intent,
        "standalone_question": standalone,
        "direct_reply": u.reply,
        "plan": [standalone],
        "_event": {"intent": u.intent, "standalone_question": standalone, "needs_plan": u.needs_plan},
        "needs_plan": u.needs_plan,
    }
