"""Validator: blocks dangerous stages/operators and enforces a row limit."""
import pytest

from app.agent.validator import PipelineValidationError, validate_pipeline


@pytest.mark.parametrize("pipeline", [
    '[{"$match": {}}, {"$out": "hacked"}]',
    '[{"$merge": {"into": "x"}}]',
    '[{"$match": {"$where": "sleep(1000)"}}]',
    '[{"$group": {"_id": null, "x": {"$accumulator": {"init": "function(){}"}}}}]',
    '[{"$addFields": {"x": {"$function": {"body": "function(){}", "args": [], "lang": "js"}}}}]',
    '[{"$facet": {"a": [{"$out": "x"}]}}]',
    '[{"$lookup": {"from": "users", "localField": "a", "foreignField": "b", "as": "c"}}]',
    '[{"$unionWith": "secrets"}]',
    '[{"$collStats": {}}]',
    '[{"$match": {}, "$limit": 5}]',
    'not json',
    '[]',
    '"just a string"',
])
def test_rejects_unsafe_or_malformed(pipeline: str) -> None:
    with pytest.raises(PipelineValidationError):
        validate_pipeline(pipeline)


def test_appends_limit_when_missing() -> None:
    out = validate_pipeline('[{"$match": {"fiscal_year": "2013-2014"}}, {"$group": {"_id": "$po_key"}}]')
    assert out[-1] == {"$limit": 200}


def test_caps_existing_limit() -> None:
    assert validate_pipeline('[{"$sort": {"x": -1}}, {"$limit": 5000}]', max_rows=200)[-1] == {"$limit": 200}
    assert validate_pipeline('[{"$sort": {"x": -1}}, {"$limit": 5}]')[-1] == {"$limit": 5}


def test_accepts_code_fence_and_extended_json_dates() -> None:
    raw = '```json\n[{"$match": {"creation_date": {"$gte": {"$date": "2014-03-01T00:00:00Z"}}}}, {"$count": "n"}]\n```'
    out = validate_pipeline(raw)
    assert out[0]["$match"]["creation_date"]["$gte"].year == 2014
    assert out[-1] == {"$limit": 200}


def test_allows_self_lookup_and_facet() -> None:
    out = validate_pipeline('[{"$facet": {"a": [{"$count": "n"}], "b": [{"$lookup": {"from": "purchases", '
                            '"pipeline": [{"$limit": 1}], "as": "x"}}]}}]')
    assert "$facet" in out[0]


def test_accepts_list_input() -> None:
    assert validate_pipeline([{"$match": {}}])[-1] == {"$limit": 200}
