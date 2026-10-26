"""JSON serialization of Mongo results."""
import json
import math
from datetime import datetime
from decimal import Decimal

from bson import ObjectId
from bson.decimal128 import Decimal128

from app.agent.charts import suggest_chart, table_rows
from app.db.serialize import flatten_row, humanize_number, to_jsonable


def test_to_jsonable_converts_bson_types() -> None:
    oid = ObjectId()
    doc = {"_id": oid, "d": datetime(2014, 3, 1), "dec": Decimal128("1.5"), "pyd": Decimal("2.5"),
           "nan": math.nan, "nested": [{"x": datetime(2015, 1, 2)}]}
    out = to_jsonable(doc)
    assert out == {"_id": str(oid), "d": "2014-03-01T00:00:00", "dec": 1.5, "pyd": 2.5, "nan": None,
                   "nested": [{"x": "2015-01-02T00:00:00"}]}
    json.dumps(out)  # must not raise


def test_flatten_compound_id() -> None:
    assert flatten_row({"_id": {"year": 2015, "q": 2}, "spend": 1.0}) == {"year": 2015, "q": 2, "spend": 1.0}
    assert table_rows([{"_id": {"year": 2015, "q": 2}, "spend": 1.0}])[0]["label"] == "2015-2"


def test_humanize() -> None:
    assert humanize_number(28801762780.47) == "28.80B"
    assert humanize_number(5619732914.21) == "5.62B"
    assert humanize_number(28559304.68) == "28.56M"
    assert humanize_number(5673) == "5,673"


def test_chart_suggestions() -> None:
    ts = [{"_id": "2012-2013", "spend": 1.0}, {"_id": "2013-2014", "spend": 2.0}, {"_id": "2014-2015", "spend": 3.0}]
    assert suggest_chart(ts) == {"type": "line", "x": "_id", "y": "spend"}
    cats = [{"_id": "Health", "spend": 3.0}, {"_id": "Public", "spend": 1.0}]
    assert suggest_chart(cats) == {"type": "bar", "x": "_id", "y": "spend"}
    assert suggest_chart([{"orders": 5}]) is None
    assert suggest_chart(cats, {"chart_type": "none"}) is None
