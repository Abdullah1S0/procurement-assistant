"""Request/response models for the HTTP API."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """A user message within a conversation."""

    session_id: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class StepEvent(BaseModel):
    """One executed graph node (for the UI progress indicator / trace)."""

    node: str
    label: str
    ms: int
    detail: dict[str, Any] = {}


class QueryResult(BaseModel):
    """One executed sub-query."""

    question: str
    pipeline: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool
    retries: int
    error: str | None = None


class ChatResponse(BaseModel):
    """Final agent answer."""

    session_id: str
    answer: str
    language: str
    intent: str
    standalone_question: str
    pipelines: list[list[dict[str, Any]]]
    results: list[QueryResult]
    chart: dict[str, Any] | None
    steps: list[StepEvent]
    latency_ms: int
