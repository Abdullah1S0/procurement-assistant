"""Groq tool_use_failed detection, Unicode space cleanup, and the dataset meta-reply."""
from app.agent.nodes.common import clean_text, safe_tool_failure_reply
from app.db.schema import looks_like_meta_question, meta_reply, wants_sample_rows
from app.llm import _retry_after_from_message, tool_use_failed_text


class _FakeGroqError(Exception):
    def __init__(self, body: object) -> None:
        super().__init__("Error code: 400")
        self.body = body


def test_tool_use_failed_text_extracts_failed_generation() -> None:
    exc = _FakeGroqError({"error": {"code": "tool_use_failed", "message": "...",
                                     "failed_generation": "The data covers 2012-2015."}})
    assert tool_use_failed_text(exc) == "The data covers 2012-2015."


def test_tool_use_failed_text_ignores_other_errors() -> None:
    assert tool_use_failed_text(_FakeGroqError({"error": {"code": "rate_limit_exceeded"}})) is None
    assert tool_use_failed_text(ValueError("boom")) is None
    assert tool_use_failed_text(_FakeGroqError("not a dict body")) is None


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


def test_safe_tool_failure_reply_never_returns_raw_model_text() -> None:
    hallucinated = "Sure! Row 1: supplier=Acme Medical Supplies, amount=$42.00"
    meta_text = safe_tool_failure_reply("What date range does this dataset cover?", "en", hallucinated)
    other_text = safe_tool_failure_reply("Who is the president of France?", "en", hallucinated)
    assert hallucinated not in meta_text
    assert hallucinated not in other_text
    assert meta_text == meta_reply("en")
    assert "rephrase" in other_text.lower()
