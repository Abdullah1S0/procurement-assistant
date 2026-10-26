"""Eval comparator: tolerant to field names, strict on values/order where it matters."""
from eval.compare import compare

TOP = [{"_id": "medical supplies", "lines": 3839}, {"_id": "contract", "lines": 3103}]


def test_ranking_accepts_renamed_fields_and_extra_columns() -> None:
    actual = [{"item": "Medical Supplies", "count": 3839, "pct": 1.1}, {"item": "contract", "count": 3103, "pct": 0.9}]
    assert compare(TOP, [actual], "ranking").ok


def test_ranking_rejects_wrong_order_and_values() -> None:
    assert not compare(TOP, [list(reversed(TOP))], "ranking").ok
    assert not compare(TOP, [[{"_id": "medical supplies", "lines": 3000}, TOP[1]]], "ranking").ok


def test_numeric_tolerance() -> None:
    exp = [{"_id": "FY14-15 Q4", "spend": 28801762780.47}]
    assert compare(exp, [[{"_id": "FY14-15 Q4", "spend": 28801762780.47 * 1.004}]], "ranking").ok
    assert not compare(exp, [[{"_id": "FY14-15 Q4", "spend": 28801762780.47 * 1.01}]], "ranking").ok


def test_set_is_order_insensitive() -> None:
    exp = [{"_id": False, "spend": 147193862345.97}, {"_id": True, "spend": 3989911878.51}]
    assert compare(exp, [list(reversed(exp))], "set").ok


def test_compound_id_and_any_step() -> None:
    exp = [{"_id": {"year": 2015, "q": 2}, "spend": 28801762780.47}]
    actual = [{"calendar_year": 2015, "calendar_quarter": 2, "total": 28801762780.47}]
    assert compare(exp, [[{"x": 1}], actual], "ranking").ok


def test_scalar_and_no_query() -> None:
    assert compare([{"orders": 5673}], [[{"n": 5673}]], "scalar").ok
    assert not compare([{"orders": 5673}], [], "scalar").ok
