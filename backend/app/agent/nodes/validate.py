"""`validate` node: safety + sanity checks before anything touches MongoDB."""
from __future__ import annotations

from app.agent.nodes.common import traced
from app.agent.state import AgentState
from app.agent.validator import PipelineValidationError, validate_pipeline
from app.config import get_settings


@traced("validate")
def validate(state: AgentState) -> dict:
    """Parse the candidate JSON, allow only read-only stages on `purchases`, enforce a row limit."""
    s = get_settings()
    try:
        pipeline = validate_pipeline(state["candidate"]["raw"], s.mongo_collection, s.query_row_limit)
    except PipelineValidationError as exc:
        return {"pipeline": None, "error": f"Validation error: {exc}", "_event": {"ok": False, "error": str(exc)}}
    return {"pipeline": pipeline, "error": None, "_event": {"ok": True}}


def route_after_validate(state: AgentState) -> str:
    """Valid -> execute; invalid -> reflect (which retries or gives up)."""
    return "execute" if state.get("pipeline") is not None else "reflect"
