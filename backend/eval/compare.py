"""Shape-tolerant comparison of agent results against expected results.

The agent may name fields differently (`total_spend` vs `spend`) or add extra columns, so rows are compared by
their *values*: labels (strings / ints inside `_id`) must match exactly (case-insensitive), measures (numbers outside
`_id`) must match within a relative tolerance (default 0.5%).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Kind = Literal["scalar", "set", "ranking", "no_query"]
TOL = 0.005


@dataclass
class Match:
    """Comparison outcome."""

    ok: bool
    method: str
    detail: str = ""


def _walk(value: Any, out: list[Any]) -> None:
    if isinstance(value, dict):
        for v in value.values():
            _walk(v, out)
    elif isinstance(value, list):
        for v in value:
            _walk(v, out)
    else:
        out.append(value)


def split_row(row: dict[str, Any]) -> tuple[list[Any], list[float]]:
    """Return (labels, measures). Labels: values inside `_id` plus any strings; measures: numbers outside `_id`."""
    labels: list[Any] = []
    measures: list[float] = []
    for k, v in row.items():
        vals: list[Any] = []
        _walk(v, vals)
        for x in vals:
            if k == "_id" or isinstance(x, str):
                labels.append(x)
            elif isinstance(x, (int, float)) and not isinstance(x, bool):
                measures.append(float(x))
    return labels, measures


def _num_close(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= max(tol * abs(b), 0.01)


def _all_values(row: dict[str, Any]) -> list[Any]:
    vals: list[Any] = []
    _walk(row, vals)
    return vals


def row_matches(expected: dict[str, Any], actual: dict[str, Any], tol: float = TOL) -> bool:
    """True if every expected label and measure is present in the actual row."""
    labels, measures = split_row(expected)
    actual_vals = _all_values(actual)
    a_strs = [str(v).strip().lower() for v in actual_vals if isinstance(v, str)]
    a_nums = [float(v) for v in actual_vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
    for lab in labels:
        if lab is None or isinstance(lab, bool):
            continue  # null/boolean group keys carry no label information
        if isinstance(lab, str):
            if lab.strip().lower() not in a_strs:
                return False
        elif isinstance(lab, (int, float)):
            if not any(n == lab for n in a_nums) and not any(str(lab) in s for s in a_strs):
                return False
    return all(any(_num_close(n, m, tol) for n in a_nums) for m in measures)


def _bag_of_numbers(expected: list[dict[str, Any]], actual_sets: list[list[dict[str, Any]]], tol: float) -> bool:
    nums = [float(v) for r in actual_sets for row in r for v in _all_values(row)
            if isinstance(v, (int, float)) and not isinstance(v, bool)]
    want = [m for row in expected for m in split_row(row)[1]]
    return bool(want) and all(any(_num_close(n, m, tol) for n in nums) for m in want)


def compare(expected: list[dict[str, Any]], actual_sets: list[list[dict[str, Any]]], kind: Kind,
            tol: float = TOL) -> Match:
    """Compare expected rows with the result sets of every pipeline the agent executed (any one may match)."""
    if not actual_sets:
        return Match(False, "none", "agent executed no query")
    for actual in actual_sets:
        if kind == "ranking":
            k = len(expected)
            if len(actual) >= k and all(row_matches(e, a, tol) for e, a in zip(expected, actual[:k])):
                return Match(True, f"top-{k} ordered")
        elif kind == "scalar":
            if any(row_matches(expected[0], a, tol) for a in actual):
                return Match(True, "scalar")
        else:  # set: order-insensitive one-to-one matching
            remaining = list(actual)
            ok = True
            for e in expected:
                hit = next((i for i, a in enumerate(remaining) if row_matches(e, a, tol)), None)
                if hit is None:
                    ok = False
                    break
                remaining.pop(hit)
            if ok:
                return Match(True, "set (order-insensitive)")
    if kind != "ranking" and _bag_of_numbers(expected, actual_sets, tol):
        return Match(True, "values (different shape)")
    first = actual_sets[0][:3]
    return Match(False, "mismatch", f"got {first}")


def infer_kind(question: dict[str, Any]) -> Kind:
    """Kind from the explicit `kind` field, else from the reference pipeline."""
    if question.get("kind"):
        return question["kind"]
    stages = [next(iter(s)) for s in question.get("reference_pipeline", [])]
    if "$limit" in stages:
        return "ranking"
    if len(question.get("expected_result", [])) == 1:
        return "scalar"
    return "set"
