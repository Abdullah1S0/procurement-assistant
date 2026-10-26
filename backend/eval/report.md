# Evaluation report

- Run: 2026-10-26 14:47 · mode: **live agent**
- Model: `groq:openai/gpt-oss-120b`
- Scoring: numeric tolerance 0.5%, order-insensitive for sets, ordered top-k for rankings; field names may differ.

| Set | Accuracy |
|---|---|
| Given (`data/eval_questions.json`) | **16/16 (100%)** |
| Given, excluding the 6 few-shot questions (held-out) | 10/10 (100%) |
| Extra (follow-ups, Arabic, ambiguity, out-of-scope) | 13/13 (100%) |
| **All** | **29/29 (100%)** |

Latency: median 3.4s, max 28.9s · self-corrections used: 1

| # | Set | Lang | Question | Result | Retries | Latency | Notes |
|---|---|---|---|---|---|---|---|
| 1 | given | en | How many purchase orders were created in fiscal year 2013-2014? | ✅ | 0 | 2.28s | scalar |
| 2 | given (few-shot) | ar | كم عدد الطلبات اللي انعملت في مارس 2014؟ | ✅ | 0 | 2.3s | scalar |
| 3 | given | en | How many orders were created in Q2 of calendar year 2014? | ✅ | 0 | 1.96s | scalar |
| 4 | given (few-shot) | en | Which fiscal quarter had the highest total spending? | ✅ | 0 | 3.01s | top-1 ordered |
| 5 | given | en | Which calendar quarter had the highest spending? | ✅ | 0 | 3.34s | top-1 ordered |
| 6 | given (few-shot) | en | What are the 5 most frequently ordered line items? | ✅ | 0 | 3.55s | top-5 ordered |
| 7 | given | en | Total spend per fiscal year? | ✅ | 0 | 4.31s | set (order-insensitive) |
| 8 | given | en | Top 5 departments by spending | ✅ | 0 | 28.91s | top-5 ordered |
| 9 | given (few-shot) | en | Who are the top 3 suppliers by spend in fiscal year 2014-2015? | ✅ | 0 | 3.56s | top-3 ordered |
| 10 | given | en | How is spending split across acquisition types? | ✅ | 0 | 3.28s | set (order-insensitive) |
| 11 | given | en | How much was spent using CalCard, and how many line items? | ✅ | 0 | 3.37s | scalar |
| 12 | given | en | What share of spending was contract spend (has an LPA number)? | ✅ | 0 | 5.51s | set (order-insensitive) |
| 13 | given (few-shot) | en | How much did the Department of Corrections and Rehabilitation spend on IT Goods per fiscal year? | ✅ | 0 | 2.67s | set (order-insensitive) |
| 14 | given | en (multi-step) | Which UNSPSC segment had the highest spend, and what was its top supplier? | ✅ | 0 | 5.76s | step1 top-1 ordered; step2 ok |
| 15 | given (few-shot) | en | Average order value (sum of line totals per order) in fiscal year 2012-2013? | ✅ | 0 | 4.99s | scalar |
| 16 | given | en | How much was spent with small businesses in each fiscal year? | ✅ | 0 | 2.97s | set (order-insensitive) |
| 101 | extra | ar | ما هي أكثر 3 جهات حكومية إنفاقاً في السنة المالية 2013-2014؟ | ✅ | 0 | 3.0s | top-3 ordered |
| 102 | extra | en (ambiguous quarter) | Which quarter had the highest spending? | ✅ | 0 | 3.38s | top-1 ordered |
| 103 | extra | en (partial department name) | How much did the Department of Corrections spend in fiscal year 2014-2015? | ✅ | 0 | 21.48s | scalar |
| 104 | extra | en (out of scope) | What's the weather in Sacramento today? | ✅ | 0 | 0.83s | intent=out_of_scope (expected out_of_scope) |
| 105 | extra | en (chit-chat) | Hi! What can you help me with? | ✅ | 0 | 1.29s | intent=chit_chat (expected chit_chat) |
| 106 | extra | en | How many orders were created in March 2014? | ✅ | 0 | 2.4s | scalar |
| 107 | extra | en (follow-up of 106) | and in March 2015? | ✅ | 0 | 3.04s | scalar |
| 108 | extra | en | What was the total spend in fiscal year 2014-2015? | ✅ | 0 | 2.83s | scalar |
| 109 | extra | en (follow-up of 108) | break that down by acquisition type | ✅ | 0 | 4.11s | set (order-insensitive) |
| 110 | extra | ar | كم صرفت الولاية باستخدام بطاقة CalCard في كل سنة مالية؟ | ✅ | 0 | 5.68s | set (order-insensitive) |
| 111 | extra | en (multi-step) | Which department placed the most orders, and what was its most frequently ordered item? | ✅ | 0 | 8.14s | step1 top-1 ordered; step2 ok |
| 112 | extra | en (time series) | Show the number of orders per month in calendar year 2013 | ✅ | 1 | 6.32s | set (order-insensitive) |
| 113 | extra | en | How much was spent with disabled veteran business enterprises (DVBE) in fiscal year 2014-2015? | ✅ | 0 | 3.43s | scalar |
