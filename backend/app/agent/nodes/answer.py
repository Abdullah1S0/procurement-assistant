"""`answer` node: natural-language answer + chart suggestion; also writes conversation memory."""
from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.charts import suggest_chart
from app.agent.nodes.common import compact_json, traced
from app.agent.prompts import ANSWER_SYSTEM
from app.agent.state import AgentState, Turn
from app.db.serialize import humanize_number, round_floats
from app.llm import get_llm, invoke_with_backoff

FALLBACK_REPLY = {
    "en": "I can answer questions about California state purchases (FY2012-13 to FY2014-15), e.g. "
          "\"Which quarter had the highest spending?\"",
    "ar": "أستطيع الإجابة عن أسئلة حول مشتريات ولاية كاليفورنيا (السنوات المالية 2012-2015)، مثل: "
          "\"ما هو الربع الأعلى إنفاقاً؟\"",
}


def _annotate(value: Any) -> Any:
    """Round floats and add human-readable forms for large numbers, so the LLM does not mis-scale them."""
    if isinstance(value, dict):
        return {k: _annotate(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_annotate(v) for v in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value) >= 10_000:
        return f"{round_floats(float(value))} ({humanize_number(value)})"
    return round_floats(value)


def _results_context(state: AgentState) -> str:
    lines = []
    for i, step in enumerate(state.get("steps", []), 1):
        lines.append(f"Step {i}: {step['question']}")
        if step.get("error"):
            lines.append(f"  ERROR: {step['error'][:300]}")
        else:
            lines.append(f"  rows: {step['row_count']}; results: {compact_json(_annotate(step['results'][:20]), 2500)}")
    return "\n".join(lines) or "(no results)"


@traced("answer")
def answer(state: AgentState) -> dict:
    """Write the final answer in the user's language and pick a chart for the last breakdown/time series."""
    language = state.get("language", "en")
    if state.get("intent") in ("chit_chat", "out_of_scope"):
        text = state.get("direct_reply") or FALLBACK_REPLY[language]
        chart = None
    else:
        sys = ANSWER_SYSTEM.format(language_name="Arabic" if language == "ar" else "English")
        human = (f"User question: {state['question']}\nResolved question: {state['standalone_question']}\n"
                 f"Query results:\n{_results_context(state)}")
        msg = invoke_with_backoff(get_llm(fast=True), [SystemMessage(sys), HumanMessage(human)])
        text = msg.content if isinstance(msg.content, str) else str(msg.content)
        chart = None
        for step in reversed(state.get("steps", [])):
            chart = suggest_chart(step.get("results", []), step.get("chart_hint"))
            if chart:
                chart["step"] = state["steps"].index(step)
                break
    last_pipe = next((s["pipeline"] for s in reversed(state.get("steps", [])) if s.get("pipeline")), None)
    turn: Turn = {"user": state["question"], "standalone": state.get("standalone_question", state["question"]),
                  "answer": text, "pipeline": compact_json(last_pipe, 400) if last_pipe else ""}
    return {"answer": text, "chart": chart, "turns": [turn], "_event": {"chars": len(text), "chart": chart}}
