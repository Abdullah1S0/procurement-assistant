"""`execute` node: run the validated pipeline with pymongo."""
from __future__ import annotations

import logging
import time

from pymongo.errors import PyMongoError

from app.agent.nodes.common import compact_json, traced
from app.agent.state import AgentState, StepResult
from app.config import get_settings
from app.db.client import get_collection
from app.db.serialize import to_jsonable

log = logging.getLogger("agent.pipeline")

# Per-step scratch fields reset when moving on to the next sub-question.
STEP_RESET = {"gen_messages": [], "candidate": None, "pipeline": None, "error": None, "retries": 0, "lookups": 0,
              "empty_retry_done": False}


def finish_step(state: AgentState, step: StepResult) -> dict:
    """Record a finished sub-query and advance to the next one."""
    return {**STEP_RESET, "steps": [*state.get("steps", []), step], "step_index": state.get("step_index", 0) + 1}


@traced("execute")
def execute(state: AgentState) -> dict:
    """Run the aggregation (maxTimeMS, allowDiskUse). Errors and suspicious empty results go to `reflect`."""
    s = get_settings()
    pipeline = state["pipeline"]
    t0 = time.perf_counter()
    try:
        rows = list(get_collection().aggregate(pipeline, maxTimeMS=s.query_max_time_ms, allowDiskUse=True))
    except PyMongoError as exc:
        ms = int((time.perf_counter() - t0) * 1000)
        log.warning("pipeline_error ms=%d pipeline=%s error=%s", ms, compact_json(pipeline), exc)
        return {"error": f"MongoDB error: {exc}", "_event": {"ok": False, "error": str(exc)[:300]}}
    ms = int((time.perf_counter() - t0) * 1000)
    log.info("pipeline_ok ms=%d rows=%d pipeline=%s", ms, len(rows), compact_json(pipeline))
    results = to_jsonable(rows)

    if not results and not state.get("empty_retry_done") and state.get("retries", 0) < s.agent_max_retries:
        return {"error": "EMPTY_RESULT", "empty_retry_done": True,
                "_event": {"ok": True, "rows": 0, "db_ms": ms, "note": "empty result, will self-correct"}}

    step: StepResult = {
        "question": state["plan"][state.get("step_index", 0)], "pipeline": to_jsonable(pipeline),
        "results": results, "row_count": len(results), "retries": state.get("retries", 0), "error": None,
        "chart_hint": (state.get("candidate") or {}).get("chart"),
    }
    return {**finish_step(state, step), "_event": {"ok": True, "rows": len(results), "db_ms": ms}}


def route_after_execute(state: AgentState) -> str:
    """Error/empty -> reflect; otherwise next sub-question or answer."""
    if state.get("error"):
        return "reflect"
    return "generate_query" if state.get("step_index", 0) < len(state.get("plan", [])) else "answer"
