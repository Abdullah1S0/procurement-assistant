"""`validate` node: safety + sanity checks before anything touches MongoDB."""
from __future__ import annotations

import re
from typing import Any

from app.agent.nodes.common import traced
from app.agent.state import AgentState
from app.agent.validator import PipelineValidationError, validate_pipeline
from app.config import get_settings

# A recurring mistake on "most frequently/commonly ordered items" questions: grouping by
# {item, po_key} first and counting those groups (= distinct orders per item) instead of counting
# lines directly. Prompt wording and a contrastive few-shot both call this out, but the served
# MoE model isn't perfectly deterministic even at temperature 0, so it still slips through on some
# runs. Caught here and sent back to `reflect` with a pinpoint hint, using the existing
# self-correction loop to guarantee the right shape instead of relying on the first sample alone.
_ITEM_FREQUENCY_QUESTION = re.compile(
    r"(most (frequently |commonly )?ordered|most common|most ordered).{0,30}(item|line)", re.IGNORECASE)


def _is_order_count_for_item_frequency_mistake(question: str, pipeline: list[dict[str, Any]]) -> bool:
    """True if `pipeline` answers an item-frequency question by counting orders-per-item
    (via a {item, po_key} group) instead of lines-per-item."""
    if not _ITEM_FREQUENCY_QUESTION.search(question or ""):
        return False
    groups = [stage["$group"] for stage in pipeline if isinstance(stage, dict) and "$group" in stage]
    if len(groups) < 2:
        return False
    first_id = groups[0].get("_id")
    if not isinstance(first_id, dict):
        return False
    return any(isinstance(v, str) and "po_key" in v for v in first_id.values())


@traced("validate")
def validate(state: AgentState) -> dict:
    """Parse the candidate JSON, allow only read-only stages on `purchases`, enforce a row limit."""
    s = get_settings()
    try:
        pipeline = validate_pipeline(state["candidate"]["raw"], s.mongo_collection, s.query_row_limit)
        question = state["plan"][state.get("step_index", 0)]
        if _is_order_count_for_item_frequency_mistake(question, pipeline):
            raise PipelineValidationError(
                'For "most frequently/commonly ordered" items, count LINES directly with ONE $group stage: '
                '{"$group": {"_id": "$item_name_normalized", "lines": {"$sum": 1}}}. Do not group by {item, po_key} '
                "first and then count those groups - that counts distinct orders per item, not lines.")
    except PipelineValidationError as exc:
        return {"pipeline": None, "error": f"Validation error: {exc}", "_event": {"ok": False, "error": str(exc)}}
    return {"pipeline": pipeline, "error": None, "_event": {"ok": True}}


def route_after_validate(state: AgentState) -> str:
    """Valid -> execute; invalid -> reflect (which retries or gives up)."""
    return "execute" if state.get("pipeline") is not None else "reflect"
