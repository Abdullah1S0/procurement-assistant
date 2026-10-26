"""Glue between the HTTP layer and the LangGraph agent."""
from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Iterator

from app.agent.charts import table_rows
from app.agent.graph import NODE_LABELS, get_agent, turn_input
from app.api.models import ChatResponse, QueryResult, StepEvent
from app.config import get_settings

log = logging.getLogger("api")


def _config(session_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": session_id}, "recursion_limit": 40}


def _step_event(update: dict[str, Any]) -> StepEvent | None:
    """Turn a LangGraph `updates` chunk into a StepEvent."""
    for node, values in update.items():
        if node not in NODE_LABELS or not isinstance(values, dict):
            continue
        ev = dict(values.get("event") or {})
        ms = int(ev.pop("ms", 0))
        ev.pop("node", None)
        return StepEvent(node=node, label=NODE_LABELS[node], ms=ms, detail=ev)
    return None


def build_response(session_id: str, state: dict[str, Any], steps: list[StepEvent], t0: float) -> ChatResponse:
    """Assemble the API response from the final graph state."""
    max_rows = get_settings().api_result_rows
    results = []
    for s in state.get("steps", []):
        rows = table_rows(s.get("results", []))
        results.append(QueryResult(question=s["question"], pipeline=s.get("pipeline") or [], rows=rows[:max_rows],
                                   row_count=s.get("row_count", 0), truncated=len(rows) > max_rows,
                                   retries=s.get("retries", 0), error=s.get("error")))
    latency = int((time.perf_counter() - t0) * 1000)
    log.info("chat session=%s intent=%s latency_ms=%d pipelines=%d", session_id, state.get("intent"), latency, len(results))
    return ChatResponse(session_id=session_id, answer=state.get("answer", ""), language=state.get("language", "en"),
                        intent=state.get("intent", ""), standalone_question=state.get("standalone_question", ""),
                        pipelines=[r.pipeline for r in results], results=results, chart=state.get("chart"),
                        steps=steps, latency_ms=latency)


def run_chat(session_id: str, message: str) -> ChatResponse:
    """Run one turn synchronously."""
    agent, cfg, t0 = get_agent(), _config(session_id), time.perf_counter()
    steps = [ev for chunk in agent.stream(turn_input(message), cfg, stream_mode="updates") if (ev := _step_event(chunk))]
    return build_response(session_id, agent.get_state(cfg).values, steps, t0)


def iter_chat(session_id: str, message: str) -> Iterator[tuple[str, Any]]:
    """Run one turn, yielding ("step", StepEvent) per node and finally ("final", ChatResponse)."""
    agent, cfg, t0 = get_agent(), _config(session_id), time.perf_counter()
    steps: list[StepEvent] = []
    for chunk in agent.stream(turn_input(message), cfg, stream_mode="updates"):
        ev = _step_event(chunk)
        if ev:
            steps.append(ev)
            yield "step", ev
    yield "final", build_response(session_id, agent.get_state(cfg).values, steps, t0)


async def aiter_chat(session_id: str, message: str) -> AsyncIterator[tuple[str, Any]]:
    """Async variant used by the SSE endpoint (sync nodes run in LangGraph's thread pool)."""
    agent, cfg, t0 = get_agent(), _config(session_id), time.perf_counter()
    steps: list[StepEvent] = []
    async for chunk in agent.astream(turn_input(message), cfg, stream_mode="updates"):
        ev = _step_event(chunk)
        if ev:
            steps.append(ev)
            yield "step", ev
    state = (await agent.aget_state(cfg)).values
    yield "final", build_response(session_id, state, steps, t0)
