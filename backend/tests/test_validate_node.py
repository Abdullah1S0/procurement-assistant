"""validate node: the item-frequency order-count mistake detector, and the follow-up
fiscal-year-scope-continuity detector."""
from app.agent.nodes.validate import _dropped_fiscal_year_follow_up_scope as dropped_year
from app.agent.nodes.validate import _is_order_count_for_item_frequency_mistake as mistake

# Two different pipeline shapes the model has produced for the same underlying mistake (counting
# distinct orders per item instead of lines per item) - the detector must catch both by intent,
# not by matching one specific shape.
WRONG_TWO_GROUP = [{"$group": {"_id": {"item": "$item_name_normalized", "po": "$po_key"}}},
                    {"$group": {"_id": "$_id.item", "order_count": {"$sum": 1}}}]
WRONG_ADD_TO_SET = [{"$group": {"_id": "$item_name_normalized", "orderCount": {"$addToSet": "$po_key"}}},
                     {"$project": {"orderCount": {"$size": "$orderCount"}}}]
RIGHT = [{"$group": {"_id": "$item_name_normalized", "lines": {"$sum": 1}}}]


def test_flags_order_count_pattern_on_item_frequency_question() -> None:
    assert mistake("What are the 5 most frequently ordered line items?", WRONG_TWO_GROUP)
    assert mistake("What are the most commonly ordered items?", WRONG_TWO_GROUP)


def test_flags_add_to_set_variant_of_the_same_mistake() -> None:
    assert mistake("What are the 5 most frequently ordered line items?", WRONG_ADD_TO_SET)


def test_does_not_flag_the_correct_single_group_pipeline() -> None:
    assert not mistake("What are the 5 most frequently ordered line items?", RIGHT)


def test_does_not_flag_unrelated_questions() -> None:
    # referencing po_key is legitimate for other questions (e.g. average order value groups by
    # po_key on purpose) - only flag it for item-frequency questions.
    assert not mistake("Average order value in fiscal year 2012-2013?", WRONG_TWO_GROUP)
    assert not mistake("Who are the top 3 suppliers by spend?", WRONG_TWO_GROUP)


def _prior_turn(pipeline_json: str) -> dict:
    return {"turns": [{"pipeline": pipeline_json}]}


ALL_YEARS_PIPELINE = [{"$match": {"fiscal_year": {"$in": ["2012-2013", "2013-2014", "2014-2015"]}}},
                      {"$group": {"_id": "$acquisition_type", "spend": {"$sum": "$total_price"}}}]
NO_FY_PIPELINE = [{"$match": {}}, {"$group": {"_id": "$acquisition_type", "spend": {"$sum": "$total_price"}}}]
KEPT_FY_PIPELINE = [{"$match": {"fiscal_year": "2014-2015"}},
                    {"$group": {"_id": "$acquisition_type", "spend": {"$sum": "$total_price"}}}]


def test_flags_all_years_in_filter_on_a_follow_up() -> None:
    state = {"intent": "follow_up", "standalone_question": "break that down by acquisition type",
             **_prior_turn('[{"$match":{"fiscal_year":"2014-2015"}}]')}
    assert dropped_year(state, ALL_YEARS_PIPELINE) == "2014-2015"


def test_flags_fiscal_year_omitted_entirely_on_a_follow_up() -> None:
    state = {"intent": "follow_up", "standalone_question": "break that down by acquisition type",
             **_prior_turn('[{"$match":{"fiscal_year":"2014-2015"}}]')}
    assert dropped_year(state, NO_FY_PIPELINE) == "2014-2015"


def test_does_not_flag_when_the_year_is_kept() -> None:
    state = {"intent": "follow_up", "standalone_question": "break that down by acquisition type",
             **_prior_turn('[{"$match":{"fiscal_year":"2014-2015"}}]')}
    assert dropped_year(state, KEPT_FY_PIPELINE) is None


def test_does_not_flag_a_fresh_question_or_one_with_no_prior_scope() -> None:
    state = {"intent": "data_question", "standalone_question": "break that down by acquisition type",
             **_prior_turn('[{"$match":{"fiscal_year":"2014-2015"}}]')}
    assert dropped_year(state, ALL_YEARS_PIPELINE) is None  # not a follow-up
    state2 = {"intent": "follow_up", "standalone_question": "break that down by acquisition type", "turns": []}
    assert dropped_year(state2, ALL_YEARS_PIPELINE) is None  # no prior turn to inherit from


def test_does_not_flag_a_deliberate_broadening_or_year_change() -> None:
    prior = _prior_turn('[{"$match":{"fiscal_year":"2014-2015"}}]')
    assert dropped_year({"intent": "follow_up", "standalone_question": "and across all fiscal years?",
                         **prior}, ALL_YEARS_PIPELINE) is None
    assert dropped_year({"intent": "follow_up", "standalone_question": "what about fiscal year 2013-2014?",
                         **prior}, NO_FY_PIPELINE) is None
