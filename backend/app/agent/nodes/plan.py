"""`plan` node: decompose multi-step questions into ordered sub-questions."""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.agent.nodes.common import traced
from app.agent.prompts import PLAN_SYSTEM
from app.agent.state import AgentState
from app.llm import get_llm, invoke_with_backoff


class Plan(BaseModel):
    """Ordered sub-questions."""

    steps: list[str] = Field(description="2-3 ordered sub-questions", min_length=1, max_length=3)


@traced("plan")
def plan(state: AgentState) -> dict:
    """Simple questions pass through as a 1-step plan; complex ones are decomposed by the LLM."""
    question = state["standalone_question"]
    if not state.get("needs_plan"):
        return {"plan": [question], "step_index": 0, "_event": {"steps": [question]}}
    llm = get_llm().with_structured_output(Plan, method="function_calling")
    p: Plan = invoke_with_backoff(llm, [SystemMessage(PLAN_SYSTEM), HumanMessage(question)])
    steps = [s.strip() for s in p.steps if s.strip()][:3] or [question]
    return {"plan": steps, "step_index": 0, "_event": {"steps": steps}}
