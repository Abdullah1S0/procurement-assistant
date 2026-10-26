"""`plan` node: decompose multi-step questions into ordered sub-questions."""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.nodes.common import safe_tool_failure_reply, traced
from app.agent.prompts import PLAN_SYSTEM
from app.agent.state import AgentState
from app.llm import get_llm, invoke_with_backoff, tool_use_failed_text


class Plan(BaseModel):
    """Ordered sub-questions."""

    steps: list[str] = Field(description="2-3 ordered sub-questions", min_length=1, max_length=3)


@traced("plan")
def plan(state: AgentState) -> dict:
    """Simple questions pass through as a 1-step plan; complex ones are decomposed by the LLM."""
    question = state["standalone_question"]
    if not state.get("needs_plan"):
        return {"plan": [question], "step_index": 0, "_event": {"steps": [question]}}
    msgs = [SystemMessage(PLAN_SYSTEM), HumanMessage(question)]
    try:
        llm = get_llm().with_structured_output(Plan, method="function_calling")
        p: Plan = invoke_with_backoff(llm, msgs)
    except Exception as exc:  # noqa: BLE001
        failed_text = tool_use_failed_text(exc)
        if failed_text is None:
            raise
        ai = invoke_with_backoff(get_llm().bind_tools([Plan], tool_choice="auto"), msgs)
        call = next((c for c in ai.tool_calls if c["name"] == "Plan"), None)
        if call is None:
            text = ai.content if isinstance(ai.content, str) and ai.content.strip() else failed_text
            safe_text = safe_tool_failure_reply(question, state.get("language", "en"), text or "")
            return {"plan": [question], "step_index": 0, "fallback_answer": safe_text,
                    "_event": {"steps": [], "fallback_text": True}}
        p = Plan(**call["args"])
    steps = [s.strip() for s in p.steps if s.strip()][:3] or [question]
    return {"plan": steps, "step_index": 0, "_event": {"steps": steps}}


def route_after_plan(state: AgentState) -> str:
    """Fallback text (forced tool call refused twice) -> answer; otherwise -> generate_query."""
    return "answer" if state.get("fallback_answer") else "generate_query"
