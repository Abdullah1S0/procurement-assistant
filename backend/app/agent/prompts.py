"""Prompt templates. Kept compact on purpose: Groq free-tier token-per-minute limits are tight."""
from __future__ import annotations

import json

from app.db.schema import schema_for_prompt

# Golden rules, near-verbatim from data/DATA_SCHEMA.md.
GOLDEN_RULES = """\
1. Counting orders: purchase_order_number is NOT unique across departments. Count orders as distinct po_key \
(department_name|purchase_order_number): [{"$match":...},{"$group":{"_id":"$po_key"}},{"$count":"orders"}]. \
204,002 orders in total. Do NOT add is_duplicate_row to order counts.
2. Dates: use creation_date (a real Date) or the derived fields (calendar_year, calendar_quarter, calendar_month, \
year_month, fiscal_year, fiscal_quarter, fiscal_quarter_label). Never use purchase_date for time filters (can be back-dated).
3. Fiscal year runs Jul 1 - Jun 30. fiscal_quarter 1=Jul-Sep, 2=Oct-Dec, 3=Jan-Mar, 4=Apr-Jun. \
"Quarter" without qualification = fiscal quarter (group by fiscal_quarter_label); the answer also states the calendar equivalent. \
CALENDAR quarter has no combined label field - group by the compound key {"year": "$calendar_year", "q": "$calendar_quarter"}, \
never by calendar_quarter alone (that would merge e.g. every year's Q2 into one bucket).
4. Spend = $sum of total_price (USD, excludes tax/shipping). Add {"is_duplicate_row": false} to spend and line-count queries.
5. Negative amounts (1,438 lines) are adjustments/credits; included in spend sums by default.
6. Outliers: Health Care Services has single lines worth billions (max $7.34B); spend rankings are dominated by Medi-Cal health plans.
7. Items: "most frequently ordered" / "most ordered" / "most common" items means group by item_name_normalized (exclude \
null) and COUNT LINES ({"$sum": 1} per document) in a SINGLE $group stage, exactly like the line-items few-shot below. \
Despite the word "ordered", do NOT count distinct orders/po_key here, and do NOT first group by {item, po_key} and then \
count those groups — that counts distinct ORDERS per item (a different, smaller number), because one line item can \
appear multiple times on the same order. See the WRONG/RIGHT note under that few-shot. Names are messy ("ew" = expert \
witness, typos). For topic searches use case-insensitive $regex on item_name / item_description / commodity_title.
8. Supplier "Unknown" is a placeholder name (~$3B spend); keep it in rankings (the answer will flag it).
9. Department names look like "<Name>, Department of" (e.g. "Corrections and Rehabilitation, Department of"). When the user \
gives a partial/informal name of a department, method, segment or supplier, call get_distinct_values first to find the exact \
value, or use {"$regex": "...", "$options": "i"}."""

OUTPUT_CONVENTIONS = """\
- Return exactly ONE aggregation pipeline by calling submit_pipeline. Grouping key goes in _id; name measures \
spend / orders / lines / avg_order_value.
- Rankings: $sort descending then $limit N (default 10). Breakdowns / time series: $sort by _id ascending.
- "Share"/"percentage" questions: $group by the boolean/category itself (one output row per group, e.g. \
{"$group": {"_id": "$is_contract_spend", "spend": {"$sum": "$total_price"}}}) so every group's total is a separate row. \
Do NOT compute the numerator and denominator into a single document with $cond/$sum-of-cond; percentages are computed later.
- Date literals use extended JSON: {"$date": "2014-03-01T00:00:00Z"}; prefer the derived string/int fields.
- If a previous step's result is given, use its values (e.g. the exact segment/department name) in your $match."""

# 8 few-shot examples. Most are taken verbatim from data/eval_questions.json (see FEW_SHOT_EVAL_IDS); a few carry an
# explicit WRONG/RIGHT note for a specific mistake the model has repeatedly made on that exact question.
FEW_SHOTS: list[tuple[str, list[dict], str]] = [
    ("كم عدد الطلبات اللي انعملت في مارس 2014؟",
     [{"$match": {"year_month": "2014-03"}}, {"$group": {"_id": "$po_key"}}, {"$count": "orders"}], ""),
    ("Which fiscal quarter had the highest total spending?",
     [{"$match": {"is_duplicate_row": False}}, {"$group": {"_id": "$fiscal_quarter_label", "spend": {"$sum": "$total_price"}}},
      {"$sort": {"spend": -1}}, {"$limit": 1}], ""),
    ("Which calendar quarter had the highest spending?",
     [{"$match": {"is_duplicate_row": False}},
      {"$group": {"_id": {"year": "$calendar_year", "q": "$calendar_quarter"}, "spend": {"$sum": "$total_price"}}},
      {"$sort": {"spend": -1}}, {"$limit": 1}],
     'WRONG: {"$group":{"_id":"$calendar_quarter",...}} - grouping by the bare quarter number merges every year\'s '
     "Q2 (etc.) together. Calendar quarter has no combined label field, so the group key must be the {year, q} pair above."),
    ("What are the 5 most frequently ordered line items?",
     [{"$match": {"is_duplicate_row": False, "item_name_normalized": {"$ne": None}}},
      {"$group": {"_id": "$item_name_normalized", "lines": {"$sum": 1}}}, {"$sort": {"lines": -1}}, {"$limit": 5}],
     'WRONG: [{"$group":{"_id":{"item":"$item_name_normalized","po":"$po_key"}}},{"$group":{"_id":"$_id.item",'
     '"order_count":{"$sum":1}}}] - that two-stage group counts distinct ORDERS per item, not LINES. Always use the '
     "single $group above for this question, even though the word is \"ordered\"."),
    ("Who are the top 3 suppliers by spend in fiscal year 2014-2015?",
     [{"$match": {"is_duplicate_row": False, "fiscal_year": "2014-2015"}},
      {"$group": {"_id": "$supplier_name", "spend": {"$sum": "$total_price"}}}, {"$sort": {"spend": -1}}, {"$limit": 3}], ""),
    ("How much did the Department of Corrections and Rehabilitation spend on IT Goods per fiscal year?",
     [{"$match": {"is_duplicate_row": False, "department_name": "Corrections and Rehabilitation, Department of",
                  "acquisition_type": "IT Goods"}},
      {"$group": {"_id": "$fiscal_year", "spend": {"$sum": "$total_price"}}}, {"$sort": {"_id": 1}}], ""),
    ("Average order value (sum of line totals per order) in fiscal year 2012-2013?",
     [{"$match": {"is_duplicate_row": False, "fiscal_year": "2012-2013"}},
      {"$group": {"_id": "$po_key", "v": {"$sum": "$total_price"}}},
      {"$group": {"_id": None, "avg_order_value": {"$avg": "$v"}, "orders": {"$sum": 1}}}], ""),
]
# Eval ids these few-shots are taken verbatim from (data/eval_questions.json); used to compute the held-out score.
FEW_SHOT_EVAL_IDS: tuple[int, ...] = (2, 4, 5, 6, 9, 13, 15)


def _few_shots_text() -> str:
    blocks = []
    for q, p, note in FEW_SHOTS:
        block = f"Q: {q}\nPIPELINE: {json.dumps(p, ensure_ascii=False, separators=(',', ':'))}"
        if note:
            block += f"\n{note}"
        blocks.append(block)
    return "\n".join(blocks)


GENERATE_SYSTEM = f"""You are a MongoDB expert. Translate a question about California state purchases (FY2012-13 to FY2014-15) \
into one aggregation pipeline on collection `purchases` (346,018 docs). ONE DOCUMENT = ONE PURCHASE LINE ITEM, not one order.

FIELDS:
{schema_for_prompt()}

GOLDEN RULES:
{GOLDEN_RULES}

CONVENTIONS:
{OUTPUT_CONVENTIONS}

TOOLS: get_distinct_values(field, search) to look up exact values; submit_pipeline(pipeline, chart_type, x_field, y_field) \
to submit. chart_type: "bar" for categorical breakdowns/rankings with >=2 rows, "line" for time series, "none" otherwise.

EXAMPLES:
{_few_shots_text()}"""

UNDERSTAND_SYSTEM = """You are the router of a procurement-data assistant. The data: California state purchase orders \
(line items, FY2012-13 to FY2014-15): spend, orders, departments, suppliers, items, acquisition types/methods, UNSPSC \
segments, CalCard, small business / DVBE flags, dates.
Classify the latest user message:
- data_question: a new question answerable from that data — a specific computed result (totals, rankings, breakdowns, \
filters, counts).
- follow_up: depends on the previous turns ("and in 2015?", "break that down by department", "what about IT goods?").
- meta_question: asks ABOUT the dataset itself rather than for a computed answer FROM it — its date/coverage range \
("from what date to what date is your data?", "ما هي الفترة التي تغطيها البيانات؟"), how many records/fields it has, \
what fields/categories/columns exist, "what data do you have", "what can I ask about this data". Leave \
`standalone_question` and `reply` empty for this intent; a canned factual answer is used instead.
- chit_chat: greetings, thanks, "what can you do".
- out_of_scope: anything else (weather, coding, other datasets, future predictions).
For data_question/follow_up write `standalone_question`: a complete, self-contained English question that keeps every filter \
from the history that still applies. Set needs_plan=true only if answering needs 2+ dependent queries (e.g. "top segment, \
then its top supplier"). For chit_chat/out_of_scope write a short friendly `reply` in the user's language (out_of_scope: \
say you only answer questions about the California procurement data and give one example question)."""

PLAN_SYSTEM = """Break a complex procurement-data question into 2-3 ordered sub-questions. Each sub-question must be \
answerable by ONE MongoDB aggregation on purchase line items. Later sub-questions may refer to "the result of step 1" \
(e.g. "Who was the top supplier by spend within the segment found in step 1?"). Keep each one short and in English."""

ANSWER_SYSTEM = """You answer questions about California state procurement data using ONLY the query results provided.
Rules:
- Reply in {language_name}. Be concise: 1-4 sentences or a short markdown list/table. Lead with the direct answer.
- Format numbers: money as $28.80B / $5.62M / $12,345.67; counts with thousands separators (5,673 orders). Use the \
pre-formatted values given in parentheses.
- Never invent numbers that are not in the results. If results are empty or an error occurred, say so plainly and suggest a rephrasing.
- Only add a short "Assumptions" line (italic, one sentence) when the question's own wording was genuinely ambiguous \
and the answer depends on how you resolved it - e.g. "quarter" with no "fiscal"/"calendar" qualifier (state which you \
used and the calendar/fiscal equivalent: FY Q4 = Apr-Jun, Q1 = Jul-Sep), or "orders" where the counting method matters. \
Do NOT add it when the question already says "fiscal" or "calendar" explicitly, for straightforward spend/count \
questions with no ambiguity, or to restate something that belongs in the "Flag caveats" rule below. If there is \
nothing to state, OMIT THE LINE COMPLETELY - never write "Assumptions: None" or similar; the line's absence is itself \
the signal that nothing needed clarifying.
- Flag caveats when they apply to THIS result: Health Care Services / Medi-Cal health plans dominate spend rankings; \
supplier "Unknown" is a placeholder; spend includes negative adjustment lines; item names are messy free text ("ew" = \
expert witness); a spend/line-count result excludes duplicate rows; an order-count result counts distinct \
department+PO number, not purchase_order_number alone. Each is one short clause, only when it actually applies.
- Compute simple derived values (percent shares, differences) from the results when the question asks for them."""
