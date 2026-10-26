"""`reflect` node: feed validation/DB errors or empty results back to the LLM (max N retries)."""
from __future__ import annotations

from langchain_core.messages import HumanMessage, ToolMessage

from app.agent.nodes.common import traced
from app.agent.nodes.execute import finish_step
from app.agent.state import AgentState, StepResult
from app.config import get_settings
from app.db.serialize import to_jsonable

EMPTY_HINT = (
    "The pipeline ran but returned 0 documents. Common causes: an exact string that does not match the stored value "
    "(casing, department names look like '<Name>, Department of'), wrong types (calendar_year/fiscal_quarter are ints, "
    "fiscal_year is a string like '2013-2014', year_month like '2014-03'), or a wrong date literal. Call "
    "get_distinct_values to find exact values, or use {\"$regex\": \"...\", \"$options\": \"i\"}. If the data truly has no "
    "matches, resubmit the same pipeline."
)


@traced("reflect")
def reflect(state: AgentState) -> dict:
    """Retry with error feedback, or give up on this sub-query after `agent_max_retries` attempts."""
    error = state.get("error") or "unknown error"
    retries = state.get("retries", 0)
    candidate = state.get("candidate") or {}
    if retries >= get_settings().agent_max_retries:
        step: StepResult = {"question": state["plan"][state.get("step_index", 0)],
                            "pipeline": to_jsonable(state.get("pipeline") or []), "results": [], "row_count": 0,
                            "retries": retries, "error": None if error == "EMPTY_RESULT" else error, "chart_hint": None}
        return {**finish_step(state, step), "_event": {"gave_up": True, "error": error[:300]}}

    feedback = EMPTY_HINT if error == "EMPTY_RESULT" else f"{error}\nFix the pipeline and call submit_pipeline again."
    messages = list(state["gen_messages"])
    if candidate.get("tool_call_id"):
        messages.append(ToolMessage(content=f"ERROR: {feedback}", tool_call_id=candidate["tool_call_id"]))
    else:
        messages.append(HumanMessage(f"ERROR: {feedback}"))
    return {"gen_messages": messages, "retries": retries + 1, "candidate": None, "pipeline": None, "error": None,
            "_event": {"retry": retries + 1, "reason": error[:300]}}


def route_after_reflect(state: AgentState) -> str:
    """Retrying -> generate_query; gave up -> next sub-question or answer."""
    if state.get("retries", 0) > 0 and state.get("gen_messages"):
        return "generate_query"
    return "generate_query" if state.get("step_index", 0) < len(state.get("plan", [])) else "answer"
