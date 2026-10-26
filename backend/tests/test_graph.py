"""End-to-end graph runs on mongomock with a scripted LLM (tests plumbing, not model quality)."""
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.graph import build_graph, turn_input
from app.agent.nodes.plan import Plan
from app.agent.nodes.understand import Understanding
from app.agent.tools import run_distinct_values
from tests.conftest import submit

ORDERS = [{"$match": {"year_month": "2014-03"}}, {"$group": {"_id": "$po_key"}}, {"$count": "orders"}]


def _run(graph, msg: str, thread: str = "t"):
    cfg = {"configurable": {"thread_id": thread}}
    nodes = [next(iter(c)) for c in graph.stream(turn_input(msg), cfg, stream_mode="updates")]
    return graph.get_state(cfg).values, nodes


def test_simple_question(collection, fake_llm) -> None:
    fake_llm([Understanding(intent="data_question", standalone_question="Orders in March 2014?"),
              submit(ORDERS), AIMessage(content="There were 3 orders.")])
    state, nodes = _run(build_graph(InMemorySaver()), "How many orders in March 2014?")
    assert nodes == ["understand", "plan", "generate_query", "validate", "execute", "answer"]
    assert state["steps"][0]["results"] == [{"orders": 2}]  # PO "A1" exists in two departments -> 2 distinct po_keys
    assert state["steps"][0]["pipeline"][-1] == {"$limit": 200}
    assert state["answer"] == "There were 3 orders."


def test_out_of_scope_skips_query(collection, fake_llm) -> None:
    fake_llm([Understanding(intent="out_of_scope", reply="I only know procurement data.")])
    state, nodes = _run(build_graph(InMemorySaver()), "What's the weather?")
    assert nodes == ["understand", "answer"]
    assert state["answer"] == "I only know procurement data." and state["steps"] == []


def test_unsafe_pipeline_then_self_correct(collection, fake_llm) -> None:
    fake_llm([Understanding(intent="data_question", standalone_question="q"),
              submit([{"$out": "x"}], "c1"), submit(ORDERS, "c2"), AIMessage(content="ok")])
    state, nodes = _run(build_graph(InMemorySaver()), "q")
    assert nodes.count("reflect") == 1 and nodes.count("generate_query") == 2
    assert state["steps"][0]["retries"] == 1 and state["steps"][0]["results"] == [{"orders": 2}]


def test_empty_result_triggers_reflect_and_lookup(collection, fake_llm) -> None:
    group = {"$group": {"_id": "$department_name", "lines": {"$sum": 1}}}  # (mongomock returns a row for _id: null on empty input)
    bad = [{"$match": {"department_name": "corrections"}}, group]
    good = [{"$match": {"department_name": {"$regex": "corrections", "$options": "i"}}}, group]
    lookup = AIMessage(content="", tool_calls=[{"name": "get_distinct_values", "id": "l1",
                                                "args": {"field": "department_name", "search": "correction"}}])
    llm = fake_llm([Understanding(intent="data_question", standalone_question="q"),
                    submit(bad, "c1"), lookup, submit(good, "c2"), AIMessage(content="4 lines")])
    state, nodes = _run(build_graph(InMemorySaver()), "q")
    assert "reflect" in nodes and "schema_lookup" in nodes
    assert state["steps"][0]["results"] == [{"_id": "Corrections and Rehabilitation, Department of", "lines": 4}]
    # the tool result was fed back to the LLM
    assert any("Corrections and Rehabilitation" in str(m.content) for m in llm.calls[3])


def test_multi_step_plan_passes_previous_results(collection, fake_llm) -> None:
    s1 = [{"$group": {"_id": "$department_name", "spend": {"$sum": "$total_price"}}}, {"$sort": {"spend": -1}}, {"$limit": 1}]
    s2 = [{"$match": {"department_name": "Corrections and Rehabilitation, Department of"}},
          {"$group": {"_id": "$item_name_normalized", "lines": {"$sum": 1}}}, {"$sort": {"lines": -1}}, {"$limit": 1}]
    llm = fake_llm([Understanding(intent="data_question", standalone_question="top dept and its top item",
                                  needs_plan=True),
                    Plan(steps=["top dept by spend", "top item in that dept"]),
                    submit(s1, "a"), submit(s2, "b"), AIMessage(content="done")])
    state, nodes = _run(build_graph(InMemorySaver()), "q")
    assert nodes.count("execute") == 2 and len(state["steps"]) == 2
    assert state["steps"][1]["results"] == [{"_id": "toner", "lines": 3}]
    assert "Result of step 1" in llm.calls[3][1].content


def test_follow_up_uses_memory(collection, fake_llm) -> None:
    graph = build_graph(InMemorySaver())
    fake_llm([Understanding(intent="data_question", standalone_question="Orders in March 2014?"),
              submit(ORDERS), AIMessage(content="3 orders")])
    _run(graph, "orders in March 2014?", "s")
    llm = fake_llm([Understanding(intent="follow_up", standalone_question="Orders in April 2014?"),
                    submit([{"$match": {"year_month": "2014-04"}}, {"$group": {"_id": "$po_key"}}, {"$count": "orders"}]),
                    AIMessage(content="1 order")])
    state, _ = _run(graph, "and in April?", "s")
    assert "orders in March 2014?" in llm.calls[0][1].content  # history reached the router
    assert len(state["turns"]) == 2 and state["steps"][0]["results"] == [{"orders": 1}]


def test_distinct_values_tool(collection) -> None:
    out = run_distinct_values(collection, "department_name", "correction")
    assert out["values"][0]["value"] == "Corrections and Rehabilitation, Department of"
    assert run_distinct_values(collection, "not_a_field")["error"]
