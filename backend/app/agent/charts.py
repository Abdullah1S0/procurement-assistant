"""Pick a chart spec for a result set (LLM hint first, heuristic fallback)."""
from __future__ import annotations

import re
from typing import Any

from app.db.serialize import flatten_row

TIME_KEYS = re.compile(r"(year|month|quarter|date|^q$|fiscal|period)", re.I)
TIME_VALUES = re.compile(r"^(\d{4}(-\d{2}|-\d{4})?|FY\d\d-\d\d( Q\d)?|\d{4}-Q?\d)$")


def _numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def table_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten results and merge a compound _id (e.g. year + q) into a single `label` column for charting."""
    rows = []
    for r in results:
        flat = flatten_row(r)
        if isinstance(r.get("_id"), dict):
            flat = {"label": "-".join(str(v) for v in r["_id"].values()), **flat}
        rows.append(flat)
    return rows


def suggest_chart(results: list[dict[str, Any]], hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Return {"type": "bar"|"line", "x": key, "y": key} for breakdowns/time series, else None."""
    if len(results) < 2:
        return None
    rows = table_rows(results)
    keys = list(rows[0].keys())
    numeric = [k for k in keys if all(_numeric(r.get(k)) or r.get(k) is None for r in rows) and k != "label"]
    labels = [k for k in keys if k not in numeric]
    if hint and hint.get("chart_type") == "none":
        return None
    x = hint.get("x_field") if hint else None
    y = hint.get("y_field") if hint else None
    if x not in keys:
        x = "label" if "label" in keys else ("_id" if "_id" in keys else (labels[0] if labels else None))
    if y not in numeric:
        y = next((k for k in numeric if k != x), None)
    if not x or not y:
        return None
    ctype = hint.get("chart_type") if hint and hint.get("chart_type") in ("bar", "line") else None
    if ctype is None:
        is_time = bool(TIME_KEYS.search(x)) or all(TIME_VALUES.match(str(r.get(x, ""))) for r in rows)
        ctype = "line" if is_time and len(rows) >= 3 else "bar"
    return {"type": ctype, "x": x, "y": y}
