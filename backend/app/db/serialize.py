"""Convert MongoDB results into JSON-safe, UI-friendly structures."""
import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from bson import ObjectId
from bson.decimal128 import Decimal128


def to_jsonable(value: Any) -> Any:
    """Recursively convert BSON/py types (datetime, ObjectId, Decimal128, NaN) to JSON-safe values."""
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, Decimal128):
        return float(value.to_decimal())
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def flatten_row(row: dict[str, Any]) -> dict[str, Any]:
    """Flatten one result document for tables/charts.

    A compound `_id` such as `{"year": 2015, "q": 2}` becomes top-level `year` / `q` columns,
    and nested dicts become dotted keys. Lists are joined into a string.
    """
    out: dict[str, Any] = {}

    def walk(prefix: str, val: Any) -> None:
        if isinstance(val, dict):
            for k, v in val.items():
                walk(f"{prefix}.{k}" if prefix else k, v)
        elif isinstance(val, list):
            out[prefix] = ", ".join(str(v) for v in val[:20])
        else:
            out[prefix] = val

    for key, val in row.items():
        if key == "_id" and isinstance(val, dict):
            walk("", val)
        else:
            walk(key, val)
    return out


def round_floats(value: Any, ndigits: int = 2) -> Any:
    """Recursively round floats (used for comparisons and compact prompts)."""
    if isinstance(value, float):
        return round(value, ndigits)
    if isinstance(value, dict):
        return {k: round_floats(v, ndigits) for k, v in value.items()}
    if isinstance(value, list):
        return [round_floats(v, ndigits) for v in value]
    return value


def humanize_number(x: float) -> str:
    """Format a number compactly: 28801762780.47 -> '28.80B', 5673 -> '5,673'."""
    ax = abs(x)
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M")):
        if ax >= div:
            return f"{x / div:.2f}{suf}"
    if float(x).is_integer():
        return f"{int(x):,}"
    return f"{x:,.2f}"
