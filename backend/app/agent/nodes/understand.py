"""`understand` node: classify intent and rewrite follow-ups into standalone questions."""
from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.nodes.common import detect_language, traced
from app.agent.prompts import UNDERSTAND_SYSTEM
from app.agent.state import AgentState
from app.llm import get_llm, invoke_with_backoff


class Understanding(BaseModel):
    """Router output."""

    intent: Literal["data_question", "follow_up", "chit_chat", "out_of_scope"]
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
    llm = get_llm(fast=True).with_structured_output(Understanding, method="function_calling")
    msgs = [SystemMessage(UNDERSTAND_SYSTEM),
            HumanMessage(f"Previous turns:\n{_history_text(state)}\n\nLatest user message: {question}")]
    u: Understanding = invoke_with_backoff(llm, msgs)
    standalone = u.standalone_question.strip() or question
    return {
        "language": language,
        "intent": u.intent,
        "standalone_question": standalone,
        "direct_reply": u.reply,
        "plan": [standalone],
        "_event": {"intent": u.intent, "standalone_question": standalone, "needs_plan": u.needs_plan},
        "needs_plan": u.needs_plan,
    }
