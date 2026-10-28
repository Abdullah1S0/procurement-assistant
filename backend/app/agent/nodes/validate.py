"""`validate` node: safety + sanity checks before anything touches MongoDB."""
from __future__ import annotations

import re
from typing import Any

from app.agent.nodes.common import traced
from app.agent.state import AgentState
from app.agent.validator import PipelineValidationError, validate_pipeline
from app.config import get_settings

# A recurring mistake on "most frequently/commonly ordered items" questions: counting distinct
# ORDERS per item instead of LINES per item. Prompt wording and a contrastive few-shot both call
# this out, but the served MoE model isn't perfectly deterministic even at temperature 0, so it
# still slips through on some runs - and it keeps finding different pipeline SHAPES to express the
# same mistake (a {item, po_key} group followed by counting those groups; a single $group with
# {"$addToSet": "$po_key"} + $project {"$size": ...}; etc.). Rather than chase each shape, this
# checks the question's INTENT directly: a correct answer to this question never needs to
# reference po_key or purchase_order_number anywhere, since it is purely a count of
# item_name_normalized groups. Any reference to an order-identifying field means the model is
# computing an order count. Caught here and sent back to `reflect` with a pinpoint hint, using the
# existing self-correction loop to guarantee the right answer instead of relying on one sample.
_ITEM_FREQUENCY_QUESTION = re.compile(
    r"(most (frequently |commonly )?ordered|most common|most ordered).{0,30}(item|line)", re.IGNORECASE)
_ORDER_IDENTIFYING_FIELD = re.compile(r"po_key|purchase_order_number")


def _references_order_identifying_field(node: Any) -> bool:
    if isinstance(node, dict):
        return any(_references_order_identifying_field(v) for v in node.values())
    if isinstance(node, list):
        return any(_references_order_identifying_field(v) for v in node)
    if isinstance(node, str):
        return bool(_ORDER_IDENTIFYING_FIELD.search(node))
    return False


def _is_order_count_for_item_frequency_mistake(question: str, pipeline: list[dict[str, Any]]) -> bool:
    """True if `pipeline` answers an item-frequency question by counting distinct orders per item
    (in any shape) instead of counting lines per item."""
    if not _ITEM_FREQUENCY_QUESTION.search(question or ""):
        return False
    return _references_order_identifying_field(pipeline)


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
                '{"$group": {"_id": "$item_name_normalized", "lines": {"$sum": 1}}}. Your pipeline references '
                "po_key or purchase_order_number, which means it is counting distinct ORDERS per item, not LINES - "
                "that is wrong for this question, no matter how it is computed (two $group stages, "
                '$addToSet+$size, etc.). Remove every reference to po_key/purchase_order_number and count lines.')
    except PipelineValidationError as exc:
        return {"pipeline": None, "error": f"Validation error: {exc}", "_event": {"ok": False, "error": str(exc)}}
    return {"pipeline": pipeline, "error": None, "_event": {"ok": True}}


def route_after_validate(state: AgentState) -> str:
    """Valid -> execute; invalid -> reflect (which retries or gives up)."""
    return "execute" if state.get("pipeline") is not None else "reflect"
