"""`generate_query` node: the LLM writes an aggregation pipeline (via tool calls)."""
from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.agent.nodes.common import compact_json, safe_tool_failure_reply, traced
from app.agent.prompts import GENERATE_SYSTEM
from app.agent.state import AgentState
from app.agent.tools import TOOLS
from app.llm import get_llm, invoke_with_backoff, tool_use_failed_text

MAX_LOOKUPS = 3


def _step_prompt(state: AgentState) -> str:
    """User message for the current sub-question, with results of earlier steps for multi-step plans."""
    plan = state["plan"]
    i = state.get("step_index", 0)
    parts = [f"Question: {plan[i]}"]
    if len(plan) > 1:
        parts.insert(0, f"Overall question: {state['standalone_question']}\nThis is step {i + 1} of {len(plan)}.")
        for j, prev in enumerate(state.get("steps", [])):
            parts.append(f"Result of step {j + 1} ({prev['question']}): {compact_json(prev.get('results', [])[:5], 800)}")
    return "\n".join(parts)


@traced("generate_query")
def generate_query(state: AgentState) -> dict:
    """Call the LLM with the schema prompt; it either looks up values or submits a pipeline."""
    messages = list(state.get("gen_messages") or [])
    if not messages:
        messages = [SystemMessage(GENERATE_SYSTEM), HumanMessage(_step_prompt(state))]
    lookups = state.get("lookups", 0)
    tool_choice = "submit_pipeline" if lookups >= MAX_LOOKUPS else "required"
    try:
        ai: AIMessage = invoke_with_backoff(get_llm().bind_tools(TOOLS, tool_choice=tool_choice), messages)
    except Exception as exc:  # noqa: BLE001
        failed_text = tool_use_failed_text(exc)
        if failed_text is None:
            raise
        # Groq rejected the forced tool call (model answered in plain text); retry once with
        # tool_choice="auto", and fall back to that text as the final answer if it still refuses.
        ai = invoke_with_backoff(get_llm().bind_tools(TOOLS, tool_choice="auto"), messages)
        if not ai.tool_calls:
            text = ai.content if isinstance(ai.content, str) and ai.content.strip() else failed_text
            question = state.get("standalone_question", state.get("question", ""))
            safe_text = safe_tool_failure_reply(question, state.get("language", "en"), text or "")
            return {"gen_messages": messages, "candidate": None, "fallback_answer": safe_text,
                    "_event": {"action": "fallback_text", "safe": True}}
    messages.append(ai)

    submit = next((c for c in ai.tool_calls if c["name"] == "submit_pipeline"), None)
    other = [c for c in ai.tool_calls if c["name"] != "submit_pipeline"]
    if other:
        return {"gen_messages": messages, "candidate": None,
                "_event": {"action": "lookup", "calls": [c["args"] for c in other]}}
    if submit:
        args = submit["args"]
        candidate = {"raw": args.get("pipeline", ""), "tool_call_id": submit["id"],
                     "chart": {k: args.get(k) for k in ("chart_type", "x_field", "y_field")}}
    else:  # model answered in plain text; try to use it as the pipeline
        candidate = {"raw": ai.content if isinstance(ai.content, str) else "", "tool_call_id": None, "chart": None}
    return {"gen_messages": messages, "candidate": candidate,
            "_event": {"action": "submit", "pipeline": compact_json(candidate["raw"], 2000)}}


def route_after_generate(state: AgentState) -> str:
    """Fallback text (forced tool call refused twice) -> answer; lookup call -> schema_lookup;
    submitted pipeline -> validate."""
    if state.get("fallback_answer"):
        return "answer"
    return "validate" if state.get("candidate") else "schema_lookup"
