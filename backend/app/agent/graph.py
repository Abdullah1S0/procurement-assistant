"""LangGraph wiring for the procurement agent.

understand ─┬─> plan ─> generate_query ⇄ schema_lookup
            │               │
            │            validate ──(invalid)──> reflect ──> generate_query (retry) | next step | answer
            │               │
            │            execute ──(error/empty)─> reflect
            │               │
            │      (next sub-question) ─> generate_query
            └─(chit-chat / out-of-scope)─────────────> answer ─> END
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.nodes.answer import answer
from app.agent.nodes.execute import execute, route_after_execute
from app.agent.nodes.generate import generate_query, route_after_generate
from app.agent.nodes.lookup import schema_lookup
from app.agent.nodes.plan import plan
from app.agent.nodes.reflect import reflect, route_after_reflect
from app.agent.nodes.understand import understand
from app.agent.nodes.validate import route_after_validate, validate
from app.agent.state import AgentState

NODE_LABELS = {
    "understand": "Understanding the question",
    "plan": "Planning",
    "generate_query": "Generating query",
    "schema_lookup": "Looking up exact values",
    "validate": "Validating query",
    "execute": "Executing on MongoDB",
    "reflect": "Self-correcting",
    "answer": "Writing the answer",
}


def route_after_understand(state: AgentState) -> str:
    """Data questions go to planning; chit-chat and out-of-scope go straight to the answer."""
    return "plan" if state.get("intent") in ("data_question", "follow_up") else "answer"


def build_graph(checkpointer: Any | None = None) -> CompiledStateGraph:
    """Build and compile the agent graph."""
    g = StateGraph(AgentState)
    g.add_node("understand", understand)
    g.add_node("plan", plan)
    g.add_node("generate_query", generate_query)
    g.add_node("schema_lookup", schema_lookup)
    g.add_node("validate", validate)
    g.add_node("execute", execute)
    g.add_node("reflect", reflect)
    g.add_node("answer", answer)

    g.add_edge(START, "understand")
    g.add_conditional_edges("understand", route_after_understand, ["plan", "answer"])
    g.add_edge("plan", "generate_query")
    g.add_conditional_edges("generate_query", route_after_generate, ["schema_lookup", "validate"])
    g.add_edge("schema_lookup", "generate_query")
    g.add_conditional_edges("validate", route_after_validate, ["execute", "reflect"])
    g.add_conditional_edges("execute", route_after_execute, ["reflect", "generate_query", "answer"])
    g.add_conditional_edges("reflect", route_after_reflect, ["generate_query", "answer"])
    g.add_edge("answer", END)
    return g.compile(checkpointer=checkpointer)


@lru_cache
def get_agent() -> CompiledStateGraph:
    """Process-wide agent with in-memory conversation memory (keyed by thread_id = session_id)."""
    return build_graph(InMemorySaver())


def turn_input(message: str) -> dict[str, Any]:
    """Initial state for a new user turn: resets every per-turn field (memory in `turns` is kept)."""
    return {
        "question": message, "intent": "data_question", "standalone_question": message, "direct_reply": "",
        "needs_plan": False, "plan": [message], "step_index": 0, "gen_messages": [], "candidate": None,
        "pipeline": None, "error": None, "retries": 0, "lookups": 0, "empty_retry_done": False, "steps": [],
        "answer": "", "chart": None, "event": {},
    }
