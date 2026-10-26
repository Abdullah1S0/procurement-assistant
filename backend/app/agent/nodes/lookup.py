"""`schema_lookup` node: executes `get_distinct_values` tool calls."""
from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from app.agent.nodes.common import compact_json, traced
from app.agent.state import AgentState
from app.agent.tools import run_distinct_values
from app.db.client import get_collection


@traced("schema_lookup")
def schema_lookup(state: AgentState) -> dict:
    """Answer every pending tool call of the last AI message with a ToolMessage."""
    messages = list(state["gen_messages"])
    ai: AIMessage = messages[-1]
    found = []
    for call in ai.tool_calls:
        if call["name"] == "get_distinct_values":
            out = run_distinct_values(get_collection(), call["args"].get("field", ""), call["args"].get("search"))
            found.append({"field": out.get("field"), "search": out.get("search"),
                          "top": [v["value"] for v in out.get("values", [])[:5]]})
        else:
            out = {"note": "Ignored: call submit_pipeline again after reading the lookup results."}
        messages.append(ToolMessage(content=compact_json(out, 3000), tool_call_id=call["id"]))
    return {"gen_messages": messages, "lookups": state.get("lookups", 0) + 1, "_event": {"lookups": found}}
