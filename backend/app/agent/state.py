"""LangGraph state for the procurement agent."""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import BaseMessage

Intent = Literal["data_question", "follow_up", "chit_chat", "out_of_scope", "meta_question"]


class StepResult(TypedDict, total=False):
    """Outcome of one executed sub-query."""

    question: str
    pipeline: list[dict[str, Any]]
    results: list[dict[str, Any]]
    row_count: int
    retries: int
    error: str | None
    chart_hint: dict[str, Any] | None


class Turn(TypedDict):
    """Compact memory of a finished turn (used to resolve follow-ups)."""

    user: str
    standalone: str
    answer: str
    pipeline: str


class AgentState(TypedDict, total=False):
    """Graph state. Everything except `turns` is reset at the start of each user turn."""

    # conversation memory (persisted per session by the checkpointer)
    turns: Annotated[list[Turn], operator.add]
    # current turn
    question: str
    language: Literal["en", "ar"]
    intent: Intent
    standalone_question: str
    direct_reply: str
    needs_plan: bool
    plan: list[str]
    step_index: int
    gen_messages: list[BaseMessage]
    candidate: dict[str, Any] | None  # {"raw": str, "chart": {...}}
    pipeline: list[dict[str, Any]] | None  # validated pipeline for the current step
    # Set when the model refuses a forced tool call even after an auto-tool_choice retry; its
    # text becomes the final answer directly, skipping validate/execute/answer's own LLM call.
    fallback_answer: str | None
    error: str | None
    retries: int
    lookups: int
    empty_retry_done: bool
    steps: list[StepResult]
    answer: str
    chart: dict[str, Any] | None
    event: dict[str, Any]  # last node event, consumed by the API for progress streaming
