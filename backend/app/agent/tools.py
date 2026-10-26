"""Tools exposed to the query-generation LLM."""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field
from pymongo.collection import Collection

from app.db.schema import LOOKUP_FIELDS


class get_distinct_values(BaseModel):  # noqa: N801 - tool name as seen by the LLM
    """Look up exact stored values of a field (e.g. department_name) to match the user's wording. Returns up to 25 values
    with their line counts, most frequent first."""

    field: Literal[LOOKUP_FIELDS] = Field(description="Field to inspect")  # type: ignore[valid-type]
    search: str | None = Field(default=None, description="Optional case-insensitive substring, e.g. 'correction'")


class submit_pipeline(BaseModel):  # noqa: N801
    """Submit the final MongoDB aggregation pipeline for the question."""

    pipeline: list[dict[str, Any]] = Field(
        description="Aggregation pipeline stages as a native JSON array, e.g. "
        '[{"$match": {...}}, {"$group": {...}}]. Do NOT encode it as a string.')
    chart_type: Literal["bar", "line", "none"] = Field(default="none", description="Suggested chart for the result")
    x_field: str | None = Field(default=None, description="Result field for the chart x-axis / category (often _id)")
    y_field: str | None = Field(default=None, description="Numeric result field for the chart y-axis")


TOOLS = [get_distinct_values, submit_pipeline]


def run_distinct_values(collection: Collection, field: str, search: str | None = None, limit: int = 25) -> dict[str, Any]:
    """Execute the `get_distinct_values` tool: top values of `field` (optionally filtered by a substring)."""
    if field not in LOOKUP_FIELDS:
        return {"error": f"field must be one of {list(LOOKUP_FIELDS)}"}
    match: dict[str, Any] = {field: {"$ne": None}}
    if search:
        match[field] = {"$regex": re.escape(search.strip()), "$options": "i"}
    pipeline = [{"$match": match}, {"$group": {"_id": f"${field}", "lines": {"$sum": 1}}},
                {"$sort": {"lines": -1}}, {"$limit": limit}]
    rows = list(collection.aggregate(pipeline, maxTimeMS=10000))
    values = [{"value": r["_id"], "lines": r["lines"]} for r in rows]
    if not values and search:
        # fall back to word-level matching ("dept of corrections" -> any word)
        words = [re.escape(w) for w in re.findall(r"\w{4,}", search)]
        if words:
            pipeline[0] = {"$match": {field: {"$regex": "|".join(words), "$options": "i"}}}
            values = [{"value": r["_id"], "lines": r["lines"]} for r in collection.aggregate(pipeline, maxTimeMS=10000)]
    return {"field": field, "search": search, "values": values}
