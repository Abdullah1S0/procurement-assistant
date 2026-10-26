"""LLM provider factory + rate-limit aware invocation.

Switching provider is an env change: LLM_PROVIDER=groq|openai|anthropic and LLM_MODEL=<model id>.
(OpenAI/Anthropic need `pip install langchain-openai` / `langchain-anthropic`.)
"""
from __future__ import annotations

import logging
import random
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


def _is_retryable(exc: Exception) -> tuple[bool, float | None]:
    """Return (retryable, retry_after_seconds) for rate-limit (429) and transient 5xx/connection errors."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    name = type(exc).__name__
    retry_after = None
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
            delay = min(delay, 60.0) + random.uniform(0, 0.5)
            log.warning("LLM call failed (%s); retry %d/%d in %.1fs", type(exc).__name__, attempt + 1,
                        s.llm_max_retries, delay)
            time.sleep(delay)
            attempt += 1
