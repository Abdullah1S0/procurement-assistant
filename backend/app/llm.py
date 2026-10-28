"""LLM provider factory + rate-limit aware invocation.

Switching provider is an env change: LLM_PROVIDER=groq|openai|anthropic and LLM_MODEL=<model id>.
(OpenAI/Anthropic need `pip install langchain-openai` / `langchain-anthropic`.)
"""
from __future__ import annotations

import logging
import random
import re
import time
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.config import get_settings

log = logging.getLogger(__name__)


def get_llm(fast: bool = False) -> BaseChatModel:
    """Build the chat model configured in the environment.

    Args:
        fast: use `LLM_FAST_MODEL` (if set) for light nodes such as `understand` and `answer`.
    """
    s = get_settings()
    model = (s.llm_fast_model if fast and s.llm_fast_model else s.llm_model)
    provider = s.llm_provider.lower()
    if provider == "groq":
        from langchain_groq import ChatGroq

        if not s.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Add it to .env (see .env.example) and restart the backend.")

        kwargs: dict[str, Any] = {}
        if model.startswith("openai/gpt-oss") and s.llm_reasoning_effort:
            kwargs["reasoning_effort"] = s.llm_reasoning_effort
        # SDK retries disabled: we do our own explicit, logged exponential backoff in `invoke_with_backoff`.
        return ChatGroq(model=model, temperature=s.llm_temperature, api_key=s.groq_api_key or None,
                        max_retries=0, **kwargs)
    if provider == "openai":
        from langchain_openai import ChatOpenAI  # type: ignore[import-not-found]

        return ChatOpenAI(model=model, temperature=s.llm_temperature, api_key=s.openai_api_key or None, max_retries=0)
    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic  # type: ignore[import-not-found]

        return ChatAnthropic(model=model, temperature=s.llm_temperature, api_key=s.anthropic_api_key or None,
                             max_retries=0)
    raise ValueError(f"Unsupported LLM_PROVIDER={s.llm_provider!r}")


# Groq (and most OpenAI-compatible APIs) spell out the wait in the error message itself, e.g.
# "...Please try again in 1.63s.", "...try again in 163ms.", or, for daily-quota limits,
# "...try again in 11m33.792s." - more precise than any Retry-After header.
_RETRY_AFTER_IN_MESSAGE = re.compile(
    r"try again in"
    r"(?:\s*(?P<h>[\d.]+)\s*h)?"
    r"(?:\s*(?P<m>[\d.]+)\s*m(?!s))?"
    r"(?:\s*(?P<s>[\d.]+)\s*s\b)?"
    r"(?:\s*(?P<ms>[\d.]+)\s*ms\b)?",
    re.IGNORECASE,
)


def _retry_after_from_message(exc: Exception) -> float | None:
    """Parse "try again in [Xh][Xm][Xs][Xms]" out of the error message/body, in seconds."""
    text = str(exc)
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            text = error["message"]
    m = _RETRY_AFTER_IN_MESSAGE.search(text)
    if not m or not any(m.groups()):
        return None
    total = 0.0
    if m.group("h"):
        total += float(m.group("h")) * 3600
    if m.group("m"):
        total += float(m.group("m")) * 60
    if m.group("s"):
        total += float(m.group("s"))
    if m.group("ms"):
        total += float(m.group("ms")) / 1000.0
    return total or None


def _is_retryable(exc: Exception) -> tuple[bool, float | None]:
    """Return (retryable, retry_after_seconds) for rate-limit (429) and transient 5xx/connection errors."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    name = type(exc).__name__
    retry_after = _retry_after_from_message(exc)
    if retry_after is None:
        resp = getattr(exc, "response", None)
        if resp is not None:
            try:
                retry_after = float(resp.headers.get("retry-after"))
            except (TypeError, ValueError, AttributeError):
                retry_after = None
    if status == 429 or name == "RateLimitError":
        return True, retry_after
    if (isinstance(status, int) and status >= 500) or name in ("APIConnectionError", "APITimeoutError", "InternalServerError"):
        return True, retry_after
    return False, None


_FORCED_TOOL_CALL_ERROR_CODES = frozenset({"tool_use_failed", "output_parse_failed"})


def tool_use_failed_text(exc: Exception) -> str | None:
    """Return the model's `failed_generation` text if `exc` is a Groq 400 error from a forced
    `tool_choice` where the model didn't produce a valid tool call: "tool_use_failed" (answered in
    plain text) or "output_parse_failed" (emitted something that couldn't be parsed as the tool
    call, e.g. stray reasoning text). Returns None for any other exception."""
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None
    error = body.get("error")
    if not isinstance(error, dict) or error.get("code") not in _FORCED_TOOL_CALL_ERROR_CODES:
        return None
    return error.get("failed_generation") or None


def invoke_with_backoff(runnable: Runnable, inputs: Any) -> Any:
    """Invoke a runnable, retrying 429/5xx with exponential backoff (+jitter, honours Retry-After)."""
    s = get_settings()
    attempt = 0
    while True:
        try:
            return runnable.invoke(inputs)
        except Exception as exc:  # noqa: BLE001
            retryable, retry_after = _is_retryable(exc)
            if not retryable or attempt >= s.llm_max_retries:
                raise
            delay = retry_after if retry_after else s.llm_backoff_base_s * (2 ** attempt)
            # Trust an explicit server-told wait (even a long one, e.g. a daily-quota reset) much
            # further than a pure exponential guess, which stays capped at 60s.
            delay = min(delay, 300.0 if retry_after else 60.0) + random.uniform(0, 0.5)
            log.warning("LLM call failed (%s); retry %d/%d in %.1fs", type(exc).__name__, attempt + 1,
                        s.llm_max_retries, delay)
            time.sleep(delay)
            attempt += 1


class ForcedToolCallFailed(Exception):
    """Raised by `invoke_forced_tool` when the model never produces a valid tool call, even after
    retrying once with `tool_choice="auto"`. Carries the model's own text in `.text` for logging
    only - callers must never show it to the user as-is (it can contain hallucinated content)."""

    def __init__(self, text: str) -> None:
        super().__init__(text)
        self.text = text


def invoke_forced_tool(llm: BaseChatModel, tools: list[Any], tool_choice: str, messages: list[Any]) -> Any:
    """Invoke `llm` bound to `tools` with a forced `tool_choice` (a tool name, or "required").

    Groq's gpt-oss models occasionally fail to produce a valid tool call under a forced
    `tool_choice` - answering in plain text ("tool_use_failed") or emitting something that doesn't
    parse as the call, e.g. stray reasoning text ("output_parse_failed"). On either, retry once
    with `tool_choice="auto"`. That retry can hit the exact same failure (e.g. malformed JSON
    again), so it is guarded the same way, not left to raise uncaught. Returns an AIMessage with at
    least one tool call on success; raises `ForcedToolCallFailed` if no attempt produced one.
    """
    try:
        ai = invoke_with_backoff(llm.bind_tools(tools, tool_choice=tool_choice), messages)
    except Exception as exc:  # noqa: BLE001
        failed_text = tool_use_failed_text(exc)
        if failed_text is None:
            raise
        try:
            ai = invoke_with_backoff(llm.bind_tools(tools, tool_choice="auto"), messages)
        except Exception as exc2:  # noqa: BLE001
            retry_failed_text = tool_use_failed_text(exc2)
            if retry_failed_text is None:
                raise
            raise ForcedToolCallFailed(retry_failed_text) from exc2
        if not ai.tool_calls:
            text = ai.content if isinstance(ai.content, str) and ai.content.strip() else failed_text
            raise ForcedToolCallFailed(text or "")
        return ai
    if not ai.tool_calls:
        text = ai.content if isinstance(ai.content, str) and ai.content.strip() else ""
        raise ForcedToolCallFailed(text)
    return ai
