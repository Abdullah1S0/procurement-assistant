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
"Quarter" without qualification = fiscal quarter (group by fiscal_quarter_label); the answer also states the calendar equivalent.
4. Spend = $sum of total_price (USD, excludes tax/shipping). Add {"is_duplicate_row": false} to spend and line-count queries.
5. Negative amounts (1,438 lines) are adjustments/credits; included in spend sums by default.
6. Outliers: Health Care Services has single lines worth billions (max $7.34B); spend rankings are dominated by Medi-Cal health plans.
7. Items: "most frequently ordered" / "most ordered" / "most common" items means group by item_name_normalized (exclude \
null) and COUNT LINES ({"$sum": 1} per document), exactly like the line-items few-shot below. Despite the word "ordered", \
do NOT count distinct orders/po_key here — one line item can appear multiple times on the same order. Names are messy \
("ew" = expert witness, typos). For topic searches use case-insensitive $regex on item_name / item_description / commodity_title.
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

# 6 few-shot examples taken from data/eval_questions.json (ids 2, 4, 6, 9, 13, 15).
FEW_SHOTS: list[tuple[str, list[dict]]] = [
    ("كم عدد الطلبات اللي انعملت في مارس 2014؟",
     [{"$match": {"year_month": "2014-03"}}, {"$group": {"_id": "$po_key"}}, {"$count": "orders"}]),
    ("Which fiscal quarter had the highest total spending?",
     [{"$match": {"is_duplicate_row": False}}, {"$group": {"_id": "$fiscal_quarter_label", "spend": {"$sum": "$total_price"}}},
      {"$sort": {"spend": -1}}, {"$limit": 1}]),
    ("What are the 5 most frequently ordered line items?",
     [{"$match": {"is_duplicate_row": False, "item_name_normalized": {"$ne": None}}},
      {"$group": {"_id": "$item_name_normalized", "lines": {"$sum": 1}}}, {"$sort": {"lines": -1}}, {"$limit": 5}]),
    ("Who are the top 3 suppliers by spend in fiscal year 2014-2015?",
     [{"$match": {"is_duplicate_row": False, "fiscal_year": "2014-2015"}},
      {"$group": {"_id": "$supplier_name", "spend": {"$sum": "$total_price"}}}, {"$sort": {"spend": -1}}, {"$limit": 3}]),
    ("How much did the Department of Corrections and Rehabilitation spend on IT Goods per fiscal year?",
     [{"$match": {"is_duplicate_row": False, "department_name": "Corrections and Rehabilitation, Department of",
                  "acquisition_type": "IT Goods"}},
      {"$group": {"_id": "$fiscal_year", "spend": {"$sum": "$total_price"}}}, {"$sort": {"_id": 1}}]),
    ("Average order value (sum of line totals per order) in fiscal year 2012-2013?",
     [{"$match": {"is_duplicate_row": False, "fiscal_year": "2012-2013"}},
      {"$group": {"_id": "$po_key", "v": {"$sum": "$total_price"}}},
      {"$group": {"_id": None, "avg_order_value": {"$avg": "$v"}, "orders": {"$sum": 1}}}]),
]
FEW_SHOT_EVAL_IDS: tuple[int, ...] = (2, 4, 6, 9, 13, 15)


def _few_shots_text() -> str:
    return "\n".join(f"Q: {q}\nPIPELINE: {json.dumps(p, ensure_ascii=False, separators=(',', ':'))}" for q, p in FEW_SHOTS)


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
- Add a short "Assumptions" line (italic) when relevant: fiscal vs calendar quarter (FY Q4 = Apr-Jun, Q1 = Jul-Sep; \
give the calendar equivalent), duplicate rows excluded from spend, orders = distinct department+PO number.
- Flag caveats when they apply: Health Care Services / Medi-Cal health plans dominate spend rankings; supplier "Unknown" \
is a placeholder; spend includes negative adjustment lines; item names are messy free text ("ew" = expert witness).
- Compute simple derived values (percent shares, differences) from the results when the question asks for them."""
