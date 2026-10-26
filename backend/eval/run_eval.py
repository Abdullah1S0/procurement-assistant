"""Run the evaluation set through the agent and write `eval/report.md`.

Usage (from backend/):
    python -m eval.run_eval                  # given + extra questions, live LLM
    python -m eval.run_eval --only given     # just data/eval_questions.json
    python -m eval.run_eval --self-check     # run reference pipelines instead of the agent (harness sanity check)
    python -m eval.run_eval --delay 10       # seconds between questions (Groq free-tier rate limits)
"""
from __future__ import annotations

import argparse
import json
import logging
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from app.agent.graph import get_agent, turn_input
from app.agent.prompts import FEW_SHOT_EVAL_IDS
from app.config import get_settings
from app.db.client import get_collection
from app.db.serialize import to_jsonable
from eval.compare import compare, infer_kind

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent.parent / "data"
log = logging.getLogger("eval")


def load_questions(only: str | None) -> list[dict[str, Any]]:
    """Given questions (data/eval_questions.json) + extra hand-written ones (eval/extra_questions.json)."""
    given_path = DATA / "eval_questions.json"
    if not given_path.exists():
        given_path = ROOT / "eval_questions.json"  # docker image copy
    given = [{**q, "set": "given"} for q in json.loads(given_path.read_text(encoding="utf-8"))]
    extra = [{**q, "set": "extra"} for q in json.loads((ROOT / "extra_questions.json").read_text(encoding="utf-8"))]
    return {"given": given, "extra": extra}.get(only or "", given + extra)


def run_agent(q: dict[str, Any]) -> dict[str, Any]:
    """Run one question through the agent; follow-ups share a session via the `session` field."""
    session = q.get("session") or f"eval-{q['id']}-{int(time.time())}"
    q["_session"] = session
    cfg = {"configurable": {"thread_id": session}, "recursion_limit": 40}
    state = get_agent().invoke(turn_input(q["question"]), cfg)
    return state


def run_reference(q: dict[str, Any]) -> dict[str, Any]:
    """Self-check mode: execute the reference pipeline(s) as if the agent had produced them."""
    if "reference_pipeline" not in q:
        return {"intent": q.get("expected_intent", "out_of_scope"), "steps": [], "answer": "(self-check)"}
    rows = to_jsonable(list(get_collection().aggregate(q["reference_pipeline"], allowDiskUse=True)))
    steps = [{"question": q["question"], "pipeline": q["reference_pipeline"], "results": rows, "retries": 0}]
    if "expected_result_step2" in q:
        steps.append({"question": "step 2", "pipeline": [], "results": q["expected_result_step2"], "retries": 0})
    return {"intent": "data_question", "steps": steps, "answer": "(self-check)"}


def score(q: dict[str, Any], state: dict[str, Any]) -> tuple[bool, str]:
    """Return (passed, explanation)."""
    kind = infer_kind(q)
    steps = state.get("steps", [])
    if kind == "no_query":
        ok = not steps and state.get("intent") in ("chit_chat", "out_of_scope", "meta_question")
        return ok, f"intent={state.get('intent')} (expected {q.get('expected_intent')})"
    sets = [s.get("results", []) for s in steps]
    m = compare(q["expected_result"], sets, kind)
    if not m.ok:
        return False, f"{kind}: {m.detail}"
    if "expected_result_step2" in q:
        m2 = compare(q["expected_result_step2"], sets, "ranking")
        return m2.ok, f"step1 {m.method}; step2 {'ok' if m2.ok else m2.detail}"
    return True, m.method


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["given", "extra"])
    ap.add_argument("--ids", type=str, default="", help="comma-separated ids to run")
    ap.add_argument("--delay", type=float, default=15.0, help="seconds between questions (Groq free-tier TPM)")
    ap.add_argument("--self-check", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "report.md"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    questions = load_questions(a.only)
    if a.ids:
        wanted = {int(x) for x in a.ids.split(",")}
        questions = [q for q in questions if q["id"] in wanted]
    rows: list[dict[str, Any]] = []
    for i, q in enumerate(questions):
        t0 = time.perf_counter()
        try:
            state = run_reference(q) if a.self_check else run_agent(q)
            ok, why = score(q, state)
            err = None
        except Exception as exc:  # noqa: BLE001 - keep going, record the failure
            state, ok, why, err = {}, False, "exception", f"{type(exc).__name__}: {exc}"
        latency = time.perf_counter() - t0
        steps = state.get("steps", [])
        rows.append({
            "id": q["id"], "set": q["set"], "lang": q.get("lang", ""), "question": q["question"], "pass": ok,
            "why": why, "error": err, "latency_s": round(latency, 2), "retries": sum(s.get("retries", 0) for s in steps),
            "pipelines": [s.get("pipeline") for s in steps], "answer": state.get("answer", ""),
            "few_shot": q["set"] == "given" and q["id"] in FEW_SHOT_EVAL_IDS,
        })
        print(f"[{i + 1}/{len(questions)}] #{q['id']} {'PASS' if ok else 'FAIL'} {latency:.1f}s  {why if not err else err}")
        if not a.self_check and i < len(questions) - 1:
            time.sleep(a.delay)
    write_report(rows, Path(a.out), a.self_check)
    (Path(a.out).with_suffix(".json")).write_text(encoding="utf-8", data=json.dumps(rows, ensure_ascii=False, indent=2, default=str))


def _acc(rows: list[dict[str, Any]]) -> str:
    return f"{sum(r['pass'] for r in rows)}/{len(rows)} ({100 * sum(r['pass'] for r in rows) / len(rows):.0f}%)" if rows else "n/a"


def write_report(rows: list[dict[str, Any]], path: Path, self_check: bool) -> None:
    """Write a markdown report."""
    s = get_settings()
    given = [r for r in rows if r["set"] == "given"]
    held_out = [r for r in given if not r["few_shot"]]
    extra = [r for r in rows if r["set"] == "extra"]
    lat = [r["latency_s"] for r in rows]
    lines = [
        "# Evaluation report", "",
        f"- Run: {datetime.now():%Y-%m-%d %H:%M} · mode: **{'self-check (reference pipelines)' if self_check else 'live agent'}**",
        f"- Model: `{s.llm_provider}:{s.llm_model}`" + (f" (fast: `{s.llm_fast_model}`)" if s.llm_fast_model else ""),
        "- Scoring: numeric tolerance 0.5%, order-insensitive for sets, ordered top-k for rankings; field names may differ.",
        "",
        "| Set | Accuracy |", "|---|---|",
        f"| Given (`data/eval_questions.json`) | **{_acc(given)}** |",
        f"| Given, excluding the {len(FEW_SHOT_EVAL_IDS)} few-shot questions (held-out) | {_acc(held_out)} |",
        f"| Extra (follow-ups, Arabic, ambiguity, out-of-scope) | {_acc(extra)} |",
        f"| **All** | **{_acc(rows)}** |", "",
        f"Latency: median {statistics.median(lat):.1f}s, max {max(lat):.1f}s · self-corrections used: "
        f"{sum(r['retries'] for r in rows)}" if lat else "", "",
        "| # | Set | Lang | Question | Result | Retries | Latency | Notes |", "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        q = r["question"].replace("|", "\\|")
        note = (r["error"] or r["why"]).replace("|", "\\|")[:120]
        fs = " (few-shot)" if r["few_shot"] else ""
        lines.append(f"| {r['id']} | {r['set']}{fs} | {r['lang']} | {q} | {'✅' if r['pass'] else '❌'} | "
                     f"{r['retries']} | {r['latency_s']}s | {note} |")
    fails = [r for r in rows if not r["pass"]]
    if fails:
        lines += ["", "## Failures", ""]
        for r in fails:
            lines += [f"### #{r['id']} {r['question']}", f"- {r['error'] or r['why']}",
                      f"- pipelines: `{json.dumps(r['pipelines'], ensure_ascii=False, default=str)[:800]}`",
                      f"- answer: {r['answer'][:300]}", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nwrote {path} — given {_acc(given)}, extra {_acc(extra)}, all {_acc(rows)}")


if __name__ == "__main__":
    main()
