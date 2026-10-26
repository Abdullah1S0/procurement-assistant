"""Shared fixtures: a mongomock `purchases` collection and a scripted fake LLM."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import mongomock
import pytest
from langchain_core.messages import AIMessage


def _doc(i: int, dept: str, po: str, ym: str, fy: str, price: float, item: str, dup: bool = False) -> dict[str, Any]:
    y, m = map(int, ym.split("-"))
    return {"row_id": i, "creation_date": datetime(y, m, 15), "year_month": ym, "calendar_year": y,
            "calendar_month": m, "calendar_quarter": (m - 1) // 3 + 1, "fiscal_year": fy,
            "fiscal_quarter": ((m - 7) % 12) // 3 + 1, "department_name": dept, "purchase_order_number": po,
            "po_key": f"{dept}|{po}", "total_price": price, "item_name_normalized": item, "is_duplicate_row": dup,
            "acquisition_type": "IT Goods", "segment_title": "Healthcare Services", "supplier_name": "Acme"}


@pytest.fixture
def collection(monkeypatch: pytest.MonkeyPatch) -> mongomock.Collection:
    """Small in-memory dataset; the agent's DB accessors are patched to use it."""
    col = mongomock.MongoClient()["procurement"]["purchases"]
    corr = "Corrections and Rehabilitation, Department of"
    col.insert_many([
        _doc(1, corr, "A1", "2014-03", "2013-2014", 100.0, "toner"),
        _doc(2, corr, "A1", "2014-03", "2013-2014", 50.0, "paper"),
        _doc(3, "Public Health, Department of", "A1", "2014-03", "2013-2014", 10.0, "toner"),  # same PO no., other dept
        _doc(4, corr, "B2", "2014-04", "2013-2014", 1000.0, "toner"),
        _doc(5, corr, "B2", "2014-04", "2013-2014", 1000.0, "toner", dup=True),
    ])
    import app.agent.nodes.execute as ex
    import app.agent.nodes.lookup as lk
    import app.db.client as db_client
    monkeypatch.setattr(ex, "get_collection", lambda: col)
    monkeypatch.setattr(lk, "get_collection", lambda: col)
    monkeypatch.setattr(db_client, "get_collection", lambda: col)  # used by sample_documents()
    return col


class FakeLLM:
    """Duck-typed stand-in for a chat model: returns scripted outputs in order."""

    def __init__(self, script: list[Any]) -> None:
        self.script = script
        self.calls: list[Any] = []

    def bind_tools(self, *_: Any, **__: Any) -> "FakeLLM":
        return self

    def with_structured_output(self, *_: Any, **__: Any) -> "FakeLLM":
        return self

    def invoke(self, inputs: Any) -> Any:
        self.calls.append(inputs)
        return self.script.pop(0)


def submit(pipeline: list[dict], call_id: str = "c1", **chart: Any) -> AIMessage:
    """AIMessage calling submit_pipeline."""
    return AIMessage(content="", tool_calls=[{"name": "submit_pipeline", "id": call_id,
                                              "args": {"pipeline": json.dumps(pipeline), **chart}}])


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch):
    """Install a FakeLLM (built from a script) into every node module that calls `get_llm`."""
    import app.agent.nodes.answer as an
    import app.agent.nodes.generate as ge
    import app.agent.nodes.plan as pl
    import app.agent.nodes.understand as un

    def install(script: list[Any]) -> FakeLLM:
        llm = FakeLLM(script)
        for mod in (an, ge, pl, un):
            monkeypatch.setattr(mod, "get_llm", lambda fast=False: llm)
        return llm

    return install
