"""generate_query node: the fallback message when a forced tool call fails for good."""
import pytest

from app.agent.nodes.generate import generate_query
from app.llm import ForcedToolCallFailed


def _state(step_index: int, plan: list[str], language: str = "en") -> dict:
    return {"plan": plan, "step_index": step_index, "gen_messages": [], "lookups": 0,
            "language": language, "standalone_question": plan[0], "question": plan[0], "steps": []}


def test_first_step_failure_has_no_part_prefix(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.agent.nodes.generate as g
    monkeypatch.setattr(g, "invoke_forced_tool", lambda *a, **kw: (_ for _ in ()).throw(ForcedToolCallFailed("")))
    out = generate_query(_state(0, ["How many orders in March 2014?"]))
    assert out["fallback_answer"]
    assert "part of your question" not in out["fallback_answer"]


def test_later_step_failure_names_the_failed_part(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.agent.nodes.generate as g
    monkeypatch.setattr(g, "invoke_forced_tool", lambda *a, **kw: (_ for _ in ()).throw(ForcedToolCallFailed("")))
    plan = ["Highest-spending UNSPSC segment?", "Top supplier in that segment?"]
    out = generate_query(_state(1, plan))
    assert "I could not answer this part of your question" in out["fallback_answer"]
    assert plan[1] in out["fallback_answer"]


def test_later_step_failure_in_arabic(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.agent.nodes.generate as g
    monkeypatch.setattr(g, "invoke_forced_tool", lambda *a, **kw: (_ for _ in ()).throw(ForcedToolCallFailed("")))
    plan = ["ما هي الفترة الأعلى إنفاقاً؟", "ما هو أعلى صرف فيها؟"]
    out = generate_query(_state(1, plan, language="ar"))
    assert "لم أستطع الإجابة عن هذا الجزء من سؤالك" in out["fallback_answer"]
    assert plan[1] in out["fallback_answer"]
