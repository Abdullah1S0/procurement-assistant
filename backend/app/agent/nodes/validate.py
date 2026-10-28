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


# A second recurring mistake, seen on both a fresh question and a follow-up: the model matches
# fiscal_year via $in against ALL THREE known fiscal years - a filter that is a complete no-op (it
# matches everything) - instead of either omitting the filter or keeping the one specific year the
# conversation was scoped to. For a follow-up specifically, this also means it silently drops the
# year the user was just talking about. Only 3 fiscal years exist in this dataset, so "matches all
# of them" is never a real filter a correct pipeline would write.
_ALL_FISCAL_YEARS = frozenset({"2012-2013", "2013-2014", "2014-2015"})
_FISCAL_YEAR_LITERAL = re.compile(r"\b20\d{2}-20\d{2}\b")
_BROADEN_SCOPE_WORDS = re.compile(
    r"all fiscal years|every fiscal year|across (all )?(fiscal )?years|all years|all three years|overall",
    re.IGNORECASE)


def _prior_fiscal_year_scope(state: AgentState) -> str | None:
    """The single fiscal_year value the previous turn's pipeline was scoped to, if any."""
    turns = state.get("turns") or []
    if not turns:
        return None
    m = re.search(r'"fiscal_year":\s*"(\d{4}-\d{4})"', turns[-1].get("pipeline") or "")
    return m.group(1) if m else None


def _dropped_fiscal_year_follow_up_scope(state: AgentState, pipeline: list[dict[str, Any]]) -> str | None:
    """For a follow-up, if the previous turn was scoped to one specific fiscal_year and the user's
    latest message doesn't ask to change or broaden that scope, the new pipeline must keep it -
    either as an equality match or as part of a narrower $in. Returns the year that should have
    been kept if it was dropped (via an all-years $in, or omitted outright); None if it's fine."""
    if state.get("intent") != "follow_up":
        return None
    prior_year = _prior_fiscal_year_scope(state)
    if prior_year is None:
        return None
    question = state.get("standalone_question") or state.get("question") or ""
    if _BROADEN_SCOPE_WORDS.search(question):
        return None
    if any(y != prior_year for y in _FISCAL_YEAR_LITERAL.findall(question)):
        return None  # the user asked about a different specific year - a deliberate change
    for stage in pipeline:
        match = stage.get("$match") if isinstance(stage, dict) else None
        if not isinstance(match, dict):
            continue
        fy = match.get("fiscal_year")
        if fy == prior_year:
            return None
        if isinstance(fy, dict) and prior_year in fy.get("$in", []) and set(fy["$in"]) < _ALL_FISCAL_YEARS:
            return None  # narrowed further but still includes the prior year - fine
    return prior_year


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
        dropped_year = _dropped_fiscal_year_follow_up_scope(state, pipeline)
        if dropped_year:
            raise PipelineValidationError(
                f'This is a follow-up to a question scoped to fiscal_year "{dropped_year}". Keep that scope - add '
                f'{{"fiscal_year": "{dropped_year}"}} to the $match stage - unless the user explicitly asked to '
                "change or broaden it. Do not match all fiscal years via $in; that is a no-op filter.")
    except PipelineValidationError as exc:
        return {"pipeline": None, "error": f"Validation error: {exc}", "_event": {"ok": False, "error": str(exc)}}
    return {"pipeline": pipeline, "error": None, "_event": {"ok": True}}


def route_after_validate(state: AgentState) -> str:
    """Valid -> execute; invalid -> reflect (which retries or gives up)."""
    return "execute" if state.get("pipeline") is not None else "reflect"
