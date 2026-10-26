"""Safety + sanity checks for LLM-generated aggregation pipelines.

The agent may only run read-only `aggregate` calls on the `purchases` collection.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

ALLOWED_STAGES: frozenset[str] = frozenset({
    "$match", "$group", "$sort", "$limit", "$skip", "$project", "$addFields", "$set", "$unset",
    "$unwind", "$count", "$facet", "$bucket", "$bucketAuto", "$sortByCount", "$replaceRoot",
    "$replaceWith", "$sample", "$lookup", "$unionWith",
})
# Operators that write data or execute arbitrary JavaScript; rejected anywhere in the pipeline.
FORBIDDEN_OPERATORS: frozenset[str] = frozenset({
    "$out", "$merge", "$function", "$where", "$accumulator",
})
SUB_PIPELINE_STAGES = ("$lookup", "$unionWith")


class PipelineValidationError(ValueError):
    """Raised when a pipeline is unsafe or malformed. The message is fed back to the LLM."""


def _convert_dates(node: Any) -> Any:
    """Turn extended-JSON dates ({"$date": "2014-03-01T00:00:00Z"}) into datetimes; everything else stays plain JSON."""
    if isinstance(node, dict):
        if len(node) == 1 and "$date" in node and isinstance(node["$date"], (str, int)):
            val = node["$date"]
            if isinstance(val, int):
                return datetime.fromtimestamp(val / 1000, tz=timezone.utc).replace(tzinfo=None)
            try:
                dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            except ValueError as exc:
                raise PipelineValidationError(f"Invalid $date value {val!r}; use ISO format 2014-03-01T00:00:00Z") from exc
            return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
        return {k: _convert_dates(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_convert_dates(v) for v in node]
    return node


def parse_pipeline(raw: str | list[Any]) -> list[dict[str, Any]]:
    """Parse a pipeline from a JSON string (extended-JSON $date allowed, code fences tolerated)."""
    if isinstance(raw, list):
        raw = json.dumps(raw)
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PipelineValidationError(f"Pipeline is not valid JSON: {exc}") from exc
    if isinstance(parsed, dict) and "pipeline" in parsed:
        parsed = parsed["pipeline"]
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list) or not parsed:
        raise PipelineValidationError("Pipeline must be a non-empty JSON array of stages.")
    return _convert_dates(parsed)


def _check_no_forbidden(node: Any, path: str = "pipeline") -> None:
    """Recursively reject forbidden operators anywhere in the document tree."""
    if isinstance(node, dict):
        for key, val in node.items():
            if key in FORBIDDEN_OPERATORS:
                raise PipelineValidationError(f"Operator {key} is not allowed (read-only access) at {path}.")
            _check_no_forbidden(val, f"{path}.{key}")
    elif isinstance(node, list):
        for i, val in enumerate(node):
            _check_no_forbidden(val, f"{path}[{i}]")


def _check_stages(stages: list[Any], collection: str, path: str = "pipeline") -> None:
    """Check each stage is a single allowed `$stage` and that sub-pipelines stay on `collection`."""
    for i, stage in enumerate(stages):
        where = f"{path}[{i}]"
        if not isinstance(stage, dict) or len(stage) != 1:
            raise PipelineValidationError(f"{where} must be an object with exactly one stage operator.")
        (name, body), = stage.items()
        if name not in ALLOWED_STAGES:
            raise PipelineValidationError(f"Stage {name} at {where} is not allowed.")
        if name in SUB_PIPELINE_STAGES:
            target = body.get("from") if name == "$lookup" else (body if isinstance(body, str) else body.get("coll"))
            if target not in (None, collection):
                raise PipelineValidationError(f"{name} may only reference the '{collection}' collection.")
            if isinstance(body, dict) and isinstance(body.get("pipeline"), list):
                _check_stages(body["pipeline"], collection, f"{where}.pipeline")
        if name == "$facet":
            if not isinstance(body, dict):
                raise PipelineValidationError(f"$facet at {where} must be an object.")
            for facet_name, sub in body.items():
                if not isinstance(sub, list):
                    raise PipelineValidationError(f"$facet.{facet_name} must be an array of stages.")
                _check_stages(sub, collection, f"{where}.$facet.{facet_name}")


def enforce_limit(stages: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    """Cap the final `$limit` at `max_rows`, appending one if the pipeline does not end with a limit."""
    stages = list(stages)
    last = stages[-1]
    if "$limit" in last and isinstance(last["$limit"], int) and last["$limit"] > 0:
        stages[-1] = {"$limit": min(last["$limit"], max_rows)}
    else:
        stages.append({"$limit": max_rows})
    return stages


def validate_pipeline(raw: str | list[Any], collection: str = "purchases", max_rows: int = 200) -> list[dict[str, Any]]:
    """Parse, safety-check and normalise a pipeline. Raises PipelineValidationError on failure."""
    stages = parse_pipeline(raw)
    _check_no_forbidden(stages)
    _check_stages(stages, collection)
    return enforce_limit(stages, max_rows)
