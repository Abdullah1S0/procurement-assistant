"""Groq tool_use_failed detection, Unicode space cleanup, and the dataset meta-reply."""
import pytest
from langchain_core.messages import AIMessage

from app.agent.nodes.common import clean_text, safe_tool_failure_reply, strip_empty_assumptions_line
from app.db.schema import asks_about_revenue, looks_like_meta_question, meta_reply, revenue_clarification, wants_sample_rows
from app.llm import ForcedToolCallFailed, _retry_after_from_message, invoke_forced_tool, tool_use_failed_text


class _FakeGroqError(Exception):
    def __init__(self, body: object) -> None:
        super().__init__("Error code: 400")
        self.body = body


_TOOL_USE_FAILED = _FakeGroqError({"error": {"code": "tool_use_failed", "failed_generation": "first attempt text"}})
_OUTPUT_PARSE_FAILED = _FakeGroqError({"error": {"code": "output_parse_failed",
                                                  "failed_generation": "retry also malformed"}})


class _FakeLLM:
    """A scripted stand-in: `script` has one entry per bind_tools().invoke() call, in order -
    either an exception to raise or an AIMessage to return."""

    def __init__(self, script: list) -> None:
        self.script = list(script)

    def bind_tools(self, *_a, **_kw) -> "_FakeLLM":
        return self

    def invoke(self, _inputs):
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_tool_use_failed_text_extracts_failed_generation() -> None:
    exc = _FakeGroqError({"error": {"code": "tool_use_failed", "message": "...",
                                     "failed_generation": "The data covers 2012-2015."}})
    assert tool_use_failed_text(exc) == "The data covers 2012-2015."


def test_tool_use_failed_text_also_handles_output_parse_failed() -> None:
    # a sibling error code Groq uses when it emits unparsable text (e.g. stray reasoning) instead
    # of a valid tool call - same forced-tool_choice situation, same fallback handling.
    exc = _FakeGroqError({"error": {"code": "output_parse_failed",
                                     "message": "Parsing failed. The model generated output that could not be "
                                                "parsed. Please adjust your prompt.",
                                     "failed_generation": "We need total spend for department ... Submit pipeline."}})
    assert tool_use_failed_text(exc) == "We need total spend for department ... Submit pipeline."


def test_tool_use_failed_text_ignores_other_errors() -> None:
    assert tool_use_failed_text(_FakeGroqError({"error": {"code": "rate_limit_exceeded"}})) is None
    assert tool_use_failed_text(ValueError("boom")) is None
    assert tool_use_failed_text(_FakeGroqError("not a dict body")) is None


def test_tool_use_failed_text_detects_empty_failed_generation() -> None:
    # regression: an EMPTY failed_generation ("") must still be recognised as tool_use_failed -
    # `"" or None` previously collapsed it to None, which every caller reads as "not this error
    # at all" and re-raises uncaught instead of retrying.
    exc = _FakeGroqError({"error": {"code": "tool_use_failed", "failed_generation": ""}})
    assert tool_use_failed_text(exc) == ""
    assert tool_use_failed_text(exc) is not None
    exc2 = _FakeGroqError({"error": {"code": "output_parse_failed"}})  # field missing entirely
    assert tool_use_failed_text(exc2) == ""
    assert tool_use_failed_text(exc2) is not None


def test_strip_empty_assumptions_line_removes_placeholder_variants() -> None:
    cases = [
        "**$28.80B**\n\n*Assumptions: None*",
        "**$28.80B**\n\n*Assumptions: None.*",
        "**$28.80B**\n\nAssumptions: N/A",
        "**$28.80B**\n\n_الافتراضات: لا يوجد_",
    ]
    for text in cases:
        cleaned = strip_empty_assumptions_line(text)
        assert "ssumption" not in cleaned.lower()
        assert "افتراض" not in cleaned
        assert cleaned.startswith("**$28.80B**")


def test_strip_empty_assumptions_line_keeps_a_real_assumption() -> None:
    text = "**$28.80B**\n\n*Assumptions: quarter read as fiscal quarter (FY Q4 = Apr-Jun).*"
    assert strip_empty_assumptions_line(text) == text


def test_clean_text_normalises_unusual_spaces() -> None:
    assert clean_text("28.80 B") == "28.80 B"
    assert clean_text("a b　c") == "a b c"
    assert clean_text("") == ""


def test_meta_reply_mentions_date_range_in_both_languages() -> None:
    en = meta_reply("en")
    ar = meta_reply("ar")
    assert "2012-07-02" in en and "2015-06-30" in en
    assert "2012-07-02" in ar and "2015-06-30" in ar
    assert en != ar


def test_asks_about_revenue_detects_en_and_ar_variants() -> None:
    assert asks_about_revenue("What was the state's total revenue in fiscal year 2014-2015?")
    assert asks_about_revenue("How much profit did the state make?")
    assert asks_about_revenue("ما هي الإيرادات في السنة المالية 2014-2015؟")
    assert asks_about_revenue("كم بلغت الأرباح؟")
    assert not asks_about_revenue("What was the total spend in fiscal year 2014-2015?")
    assert not asks_about_revenue("كم بلغ الإنفاق في السنة المالية 2014-2015؟")


def test_revenue_clarification_never_calls_spend_revenue() -> None:
    en = revenue_clarification("en")
    ar = revenue_clarification("ar")
    assert "spend" in en.lower() and "revenue" in en.lower()
    assert "إنفاق" in ar and "إيرادات" in ar
    assert en != ar


def test_retry_after_parses_seconds_and_milliseconds_from_message() -> None:
    e1 = _FakeGroqError({"error": {"message": "Rate limit reached. Please try again in 1.63s."}})
    e2 = _FakeGroqError({"error": {"message": "Rate limit reached. Please try again in 163ms."}})
    # real daily-quota (TPD) message captured from Groq: minutes + seconds combined
    e4 = _FakeGroqError({"error": {"message": "...on tokens per day (TPD): Limit 200000, Used 198163, "
                                               "Requested 3443. Please try again in 11m33.792s. "
                                               "Need more tokens? Upgrade to Dev Tier today..."}})
    e3 = _FakeGroqError({"error": {"message": "no timing info here"}})
    assert _retry_after_from_message(e1) == 1.63
    assert _retry_after_from_message(e2) == 0.163
    assert abs(_retry_after_from_message(e4) - 693.792) < 1e-6
    assert _retry_after_from_message(e3) is None


def test_looks_like_meta_question_handles_typos_and_arabic() -> None:
    assert looks_like_meta_question("البيانات الموجوده عندك, من تاريخ كم الى كم؟")
    assert looks_like_meta_question("وش الصفوف والاعمده الموخوده؟")  # typo: الموخوده -> الموجودة
    assert looks_like_meta_question("What date range does this dataset cover?")
    assert not looks_like_meta_question("كم عدد الطلبات فب مارس ٢٠١٤")  # a normal data question
    assert not looks_like_meta_question("top suplier by spnd")  # a normal data question


def test_wants_sample_rows_detects_row_column_requests() -> None:
    assert wants_sample_rows("وش الصفوف والاعمده الموخوده؟")
    assert wants_sample_rows("Can you show me a few sample rows?")
    assert not wants_sample_rows("What date range does this dataset cover?")


def test_invoke_forced_tool_succeeds_on_first_try() -> None:
    call = AIMessage(content="", tool_calls=[{"name": "submit_pipeline", "id": "c1", "args": {}}])
    llm = _FakeLLM([call])
    assert invoke_forced_tool(llm, [], "required", []) is call


def test_invoke_forced_tool_recovers_via_auto_retry() -> None:
    call = AIMessage(content="", tool_calls=[{"name": "submit_pipeline", "id": "c1", "args": {}}])
    llm = _FakeLLM([_TOOL_USE_FAILED, call])
    assert invoke_forced_tool(llm, [], "required", []) is call


def test_invoke_forced_tool_raises_when_the_retry_fails_the_same_way() -> None:
    # the auto-tool_choice retry can hit the exact same error (e.g. malformed JSON again) - this
    # must not propagate as a raw, uncaught exception; it becomes a ForcedToolCallFailed instead.
    llm = _FakeLLM([_TOOL_USE_FAILED, _OUTPUT_PARSE_FAILED])
    with pytest.raises(ForcedToolCallFailed) as exc_info:
        invoke_forced_tool(llm, [], "required", [])
    assert exc_info.value.text == "retry also malformed"


def test_invoke_forced_tool_raises_when_retry_calls_no_tool_at_all() -> None:
    llm = _FakeLLM([_TOOL_USE_FAILED, AIMessage(content="I think the answer is 42.", tool_calls=[])])
    with pytest.raises(ForcedToolCallFailed) as exc_info:
        invoke_forced_tool(llm, [], "required", [])
    assert "42" in exc_info.value.text


def test_invoke_forced_tool_recovers_from_empty_failed_generation() -> None:
    # the exact live bug: tool_use_failed with failed_generation == "" must still retry (and
    # succeed here), not re-raise the original exception as if it weren't this error at all.
    empty = _FakeGroqError({"error": {"code": "tool_use_failed", "failed_generation": ""}})
    call = AIMessage(content="", tool_calls=[{"name": "submit_pipeline", "id": "c1", "args": {}}])
    llm = _FakeLLM([empty, call])
    assert invoke_forced_tool(llm, [], "required", []) is call


def test_invoke_forced_tool_falls_back_safely_on_empty_failed_generation_both_times() -> None:
    empty = _FakeGroqError({"error": {"code": "tool_use_failed", "failed_generation": ""}})
    llm = _FakeLLM([empty, empty])
    with pytest.raises(ForcedToolCallFailed) as exc_info:
        invoke_forced_tool(llm, [], "required", [])
    assert exc_info.value.text == ""


def test_safe_tool_failure_reply_never_returns_raw_model_text() -> None:
    hallucinated = "Sure! Row 1: supplier=Acme Medical Supplies, amount=$42.00"
    meta_text = safe_tool_failure_reply("What date range does this dataset cover?", "en", hallucinated)
    other_text = safe_tool_failure_reply("Who is the president of France?", "en", hallucinated)
    assert hallucinated not in meta_text
    assert hallucinated not in other_text
    assert meta_text == meta_reply("en")
    assert "rephrase" in other_text.lower()
