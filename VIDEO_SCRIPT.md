# Demo video script (target 7:00, hard limit 8:00)

**Prep:** stack running (`docker compose up -d`, data seeded), browser at http://localhost:5173 with a fresh chat,
editor open on `backend/app/agent/`, `backend/eval/report.md` open. Send each demo question once beforehand so
Groq is warm and you know the timings. Keep the browser zoom at about 110%.

| Time | Section | On screen | Say (short) |
|---|---|---|---|
| 0:00–0:35 | **Problem** | README title | "Procurement analysts ask questions like 'which quarter had the highest spending?' but the data is 346k line items in MongoDB. This assistant turns natural language (English or Arabic) into safe MongoDB aggregations, runs them, and explains the result." |
| 0:35–1:30 | **Architecture** | README Mermaid diagrams | React UI → FastAPI (SSE) → LangGraph agent → Groq LLM + MongoDB. Walk the graph: understand → plan → generate_query ⇄ schema_lookup → validate → execute → reflect → answer. "Each node is a small Python module." |
| 1:30–4:15 | **Live demo** (≈25 s per question) | Chat UI | Point at the step chips streaming live each time. |
| | Q1 time period | "How many orders were created in March 2014?" | 5,673. Open *Show query*: distinct `po_key`, because PO numbers repeat across departments. |
| | Q2 ambiguous quarter + chart | "Which quarter had the highest spending?" | FY14-15 Q4 = Apr–Jun 2015, $28.80B. It states fiscal vs calendar. |
| | Q3 items | "What are the 5 most frequently ordered line items?" | Bar chart; "ew" = expert witness caveat. |
| | Q4 multi-step | "Which UNSPSC segment had the highest spend, and what was its top supplier?" | `plan` creates 2 steps; step 2 uses step 1's result. Show both pipelines. |
| | Q5 follow-up | "Top 5 departments by spending" → "break that down by fiscal year for the top one" | "Interpreted as …" line shows memory resolving the follow-up. Mention the Medi-Cal outlier caveat. |
| | Q6 Arabic | "كم صرفت الولاية باستخدام بطاقة CalCard في كل سنة مالية؟" | RTL answer in Arabic, line chart. |
| | (optional) out-of-scope | "What's the weather in Sacramento?" | Polite refusal, no query run. |
| 4:15–5:45 | **Code walkthrough** | `graph.py` → `prompts.py` → `validator.py` → `reflect.py` | `graph.py`: conditional edges and retry loop. `prompts.py`: golden rules + 6 few-shots, ≈2k tokens because of Groq limits. `validator.py`: allowlist, blocks `$out/$merge/$where/$function/$accumulator` recursively, forces `$limit 200`, `maxTimeMS`. `reflect.py`: errors and empty results go back to the LLM with hints (`$regex` + `i`), max 2 retries. `llm.py`: `get_llm()` factory, one env line to switch provider; 429 backoff. |
| 5:45–6:30 | **Evaluation** | terminal `python -m eval.run_eval` (pre-recorded) + `eval/report.md` | 16 given + 13 extra. Tolerant comparator: 0.5%, order-insensitive sets, top-k rankings. Read the score; mention held-out accuracy and one failure plus how it was fixed. `pytest`: 35 tests. |
| 6:30–7:00 | **Design choices & next steps** | README "Limitations" | Explicit graph over a free-form ReAct agent (predictable and debuggable), tool-based structured output, read-only safety layer, compact prompts. Next: persistent checkpointer, read-only DB user, embeddings for messy item names. |

**Backup plan:** if Groq rate-limits during recording, cut to the pre-recorded run of the same question.
Don't wait on camera.
