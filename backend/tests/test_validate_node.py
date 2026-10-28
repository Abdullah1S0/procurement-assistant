"""validate node: the item-frequency order-count mistake detector."""
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
