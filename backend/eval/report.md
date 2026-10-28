# Evaluation report

- Run: 2026-10-28 17:12 · mode: **live agent**
- Model: `groq:openai/gpt-oss-120b`
- Scoring: numeric tolerance 0.5%, order-insensitive for sets, ordered top-k for rankings; field names may differ.

| Set | Accuracy |
|---|---|
| Given (`data/eval_questions.json`) | **15/16 (94%)** |
| Given, excluding the 7 few-shot questions (held-out) | 9/9 (100%) |
| Extra (follow-ups, Arabic, ambiguity, out-of-scope) | 14/16 (88%) |
| **All** | **29/32 (91%)** |

Latency: median 4.2s, max 55.4s · self-corrections used: 0

| # | Set | Lang | Question | Result | Retries | Latency | Notes |
|---|---|---|---|---|---|---|---|
| 1 | given | en | How many purchase orders were created in fiscal year 2013-2014? | ✅ | 0 | 4.27s | scalar |
| 2 | given (few-shot) | ar | كم عدد الطلبات اللي انعملت في مارس 2014؟ | ✅ | 0 | 2.8s | scalar |
| 3 | given | en | How many orders were created in Q2 of calendar year 2014? | ✅ | 0 | 55.35s | scalar |
| 4 | given (few-shot) | en | Which fiscal quarter had the highest total spending? | ✅ | 0 | 3.57s | top-1 ordered |
| 5 | given (few-shot) | en | Which calendar quarter had the highest spending? | ✅ | 0 | 3.04s | top-1 ordered |
| 6 | given (few-shot) | en | What are the 5 most frequently ordered line items? | ❌ | 0 | 5.78s | ranking: got [{'_id': 'medical supplies', 'orderCount': 3690}, {'_id': 'contract', 'orderCount': 3100}, {'_id': 'toner', |
| 7 | given | en | Total spend per fiscal year? | ✅ | 0 | 6.28s | set (order-insensitive) |
| 8 | given | en | Top 5 departments by spending | ✅ | 0 | 5.1s | top-5 ordered |
| 9 | given (few-shot) | en | Who are the top 3 suppliers by spend in fiscal year 2014-2015? | ✅ | 0 | 4.97s | top-3 ordered |
| 10 | given | en | How is spending split across acquisition types? | ✅ | 0 | 5.39s | set (order-insensitive) |
| 11 | given | en | How much was spent using CalCard, and how many line items? | ✅ | 0 | 4.75s | scalar |
| 12 | given | en | What share of spending was contract spend (has an LPA number)? | ✅ | 0 | 3.68s | set (order-insensitive) |
| 13 | given (few-shot) | en | How much did the Department of Corrections and Rehabilitation spend on IT Goods per fiscal year? | ✅ | 0 | 2.66s | set (order-insensitive) |
| 14 | given | en (multi-step) | Which UNSPSC segment had the highest spend, and what was its top supplier? | ✅ | 0 | 13.63s | step1 top-1 ordered; step2 ok |
| 15 | given (few-shot) | en | Average order value (sum of line totals per order) in fiscal year 2012-2013? | ✅ | 0 | 4.9s | scalar |
| 16 | given | en | How much was spent with small businesses in each fiscal year? | ✅ | 0 | 6.01s | set (order-insensitive) |
| 101 | extra | ar | ما هي أكثر 3 جهات حكومية إنفاقاً في السنة المالية 2013-2014؟ | ✅ | 0 | 4.11s | top-3 ordered |
| 102 | extra | en (ambiguous quarter) | Which quarter had the highest spending? | ✅ | 0 | 4.5s | top-1 ordered |
| 103 | extra | en (partial department name) | How much did the Department of Corrections spend in fiscal year 2014-2015? | ❌ | 0 | 10.78s | BadRequestError: Error code: 400 - {'error': {'message': "Parsing failed. The model generated output that could not be p |
| 104 | extra | en (out of scope) | What's the weather in Sacramento today? | ✅ | 0 | 0.86s | intent=out_of_scope (expected out_of_scope) |
| 105 | extra | en (chit-chat) | Hi! What can you help me with? | ✅ | 0 | 0.74s | intent=chit_chat (expected chit_chat) |
| 106 | extra | en | How many orders were created in March 2014? | ✅ | 0 | 3.03s | scalar |
| 107 | extra | en (follow-up of 106) | and in March 2015? | ✅ | 0 | 2.55s | scalar |
| 108 | extra | en | What was the total spend in fiscal year 2014-2015? | ✅ | 0 | 5.49s | scalar |
| 109 | extra | en (follow-up of 108) | break that down by acquisition type | ❌ | 0 | 4.48s | set: got [{'_id': 'NON-IT Services', 'lines': 68193, 'spend': 140589259405.73}, {'_id': 'NON-IT Goods', 'lines': 213934, |
| 110 | extra | ar | كم صرفت الولاية باستخدام بطاقة CalCard في كل سنة مالية؟ | ✅ | 0 | 2.87s | set (order-insensitive) |
| 111 | extra | en (multi-step) | Which department placed the most orders, and what was its most frequently ordered item? | ✅ | 0 | 6.39s | step1 top-1 ordered; step2 ok |
| 112 | extra | en (time series) | Show the number of orders per month in calendar year 2013 | ✅ | 0 | 2.82s | set (order-insensitive) |
| 113 | extra | en | How much was spent with disabled veteran business enterprises (DVBE) in fiscal year 2014-2015? | ✅ | 0 | 2.5s | scalar |
| 114 | extra | ar (meta: date range) | البيانات الموجوده عندك, من تاريخ كم الى كم؟ | ✅ | 0 | 1.68s | intent=meta_question (expected meta_question) |
| 115 | extra | en (meta: date range) | What date range does this dataset cover? | ✅ | 0 | 0.64s | intent=meta_question (expected meta_question) |
| 116 | extra | en (meta: fields) | What kind of fields or information does this data include? | ✅ | 0 | 0.86s | intent=meta_question (expected meta_question) |

## Failures

### #6 What are the 5 most frequently ordered line items?
- ranking: got [{'_id': 'medical supplies', 'orderCount': 3690}, {'_id': 'contract', 'orderCount': 3100}, {'_id': 'toner', 'orderCount': 1551}]
- pipelines: `[[{"$match": {"fiscal_year": {"$in": ["2012-2013", "2013-2014", "2014-2015"]}, "is_duplicate_row": false, "item_name_normalized": {"$ne": null}}}, {"$group": {"_id": "$item_name_normalized", "orderCount": {"$addToSet": "$po_key"}}}, {"$project": {"orderCount": {"$size": "$orderCount"}}}, {"$sort": {"orderCount": -1}}, {"$limit": 5}]]`
- answer: **Top 5 line items by purchase‑order count (FY 2012‑13 – FY 2014‑15)**  

| Rank | Line item | Purchase orders |
|------|-----------|-----------------|
| 1 | medical supplies | 3,690 |
| 2 | contract | 3,100 |
| 3 | toner | 1,551 |
| 4 | office supplies | 1,494 |
| 5 | ew (expert witness) | 1,379 |


### #103 How much did the Department of Corrections spend in fiscal year 2014-2015?
- BadRequestError: Error code: 400 - {'error': {'message': "Parsing failed. The model generated output that could not be parsed. Please adjust your prompt. See 'failed_generation' for more details.", 'type': 'invalid_request_error', 'code': 'output_parse_failed', 'failed_generation': 'We need total spend for department Corrections and Rehabilitation, Department of in FY 2014-2015. Use match is_duplicate_row false, department_name exact, fiscal_year "2014-2015". Then group sum total_price. Submit pipeline.'}}
- pipelines: `[]`
- answer: 

### #109 break that down by acquisition type
- set: got [{'_id': 'NON-IT Services', 'lines': 68193, 'spend': 140589259405.73}, {'_id': 'NON-IT Goods', 'lines': 213934, 'spend': 4558575479.66}, {'_id': 'IT Services', 'lines': 11157, 'spend': 4449069898.3}]
- pipelines: `[[{"$match": {"fiscal_year": {"$in": ["2012-2013", "2013-2014", "2014-2015"]}, "is_duplicate_row": false}}, {"$group": {"_id": "$acquisition_type", "lines": {"$sum": 1}, "spend": {"$sum": "$total_price"}}}, {"$sort": {"spend": -1}}, {"$limit": 200}]]`
- answer: **Acquisition‑type spend and order count**

| Acquisition Type | Orders (lines) | Spend |
|------------------|----------------|-------|
| NON‑IT Services | 68,193 | $140.59B |
| NON‑IT Goods | 213,934 | $4.56B |
| IT Services | 11,157 | $4.45B |
| IT Goods | 50,486 | $1.57B |
| IT Telecommunications

