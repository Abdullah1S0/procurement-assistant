"""answer node: a later-step failure in a multi-step plan must not discard earlier results."""
import pytest
from langchain_core.messages import AIMessage

import app.agent.nodes.answer as answer_mod
from app.agent.nodes.answer import answer


class _FakeLLM:
    def __init__(self, content: str) -> None:
        self.content = content

    def invoke(self, _messages):
        return AIMessage(content=self.content)


def test_partial_failure_keeps_successful_step_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(answer_mod, "get_llm", lambda fast=False: _FakeLLM("Healthcare Services spent $111.68B."))
    state = {
        "language": "en",
        "intent": "data_question",
        "question": "Which UNSPSC segment had the highest spend, and what was its top supplier?",
        "standalone_question": "Which UNSPSC segment had the highest spend, and what was its top supplier?",
        "plan": ["Highest-spending UNSPSC segment?", "Top supplier in that segment?"],
        "steps": [{"question": "Highest-spending UNSPSC segment?",
                   "pipeline": [{"$match": {}}], "results": [{"_id": "Healthcare Services", "spend": 111.68e9}],
                   "row_count": 1, "retries": 0, "error": None, "chart_hint": None}],
        "fallback_answer": 'I could not answer this part of your question: "Top supplier in that segment?". '
                           "I couldn't turn that into an answer - could you rephrase the question?",
        "turns": [],
    }
    out = answer(state)
    assert "Healthcare Services" in out["answer"]  # the successful step's answer survived
    assert "Top supplier in that segment?" in out["answer"]  # names which part failed
    assert "could not answer" in out["answer"].lower()


def test_total_failure_with_no_successful_steps_uses_fallback_only(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def _should_not_be_called(fast=False):
        nonlocal called
        called = True
        return _FakeLLM("should not be used")

    monkeypatch.setattr(answer_mod, "get_llm", _should_not_be_called)
    state = {
        "language": "en", "intent": "data_question", "question": "q", "standalone_question": "q",
        "plan": ["q"], "steps": [], "fallback_answer": "I couldn't turn that into an answer - please rephrase.",
        "turns": [],
    }
    out = answer(state)
    assert out["answer"] == "I couldn't turn that into an answer - please rephrase."
    assert called is False  # no LLM call needed when nothing succeeded
