#!/usr/bin/env python3
"""Recompute the G3 Agent–RAG evidence summary from retained task checkpoints.

This command refuses incomplete or mismatched suites.  It is deliberately a
reader: raw per-task outputs and the Agent run-state database remain the source
of truth, while the resulting JSON is the compact committed evidence artifact.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import statistics
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "g3-agent-rag-ablation"
RUNS = ROOT / "artifacts" / "g3-agent-rag-ablation" / "runs"
RUN_STATE = ROOT / "llm-coding-agent-system" / "memory" / "run_state.db"
OUTPUT = ROOT / "artifacts" / "evidence" / "agent-rag-ablation-latest.json"


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected object in {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    lower, upper = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def finite_ratio(numerator: int | float, denominator: int | float) -> float | None:
    return float(numerator / denominator) if denominator else None


def run_state_rows(run_ids: set[str]) -> tuple[dict[str, sqlite3.Row], list[sqlite3.Row]]:
    if not RUN_STATE.is_file():
        return {}, []
    connection = sqlite3.connect(RUN_STATE)
    connection.row_factory = sqlite3.Row
    try:
        placeholders = ",".join("?" for _ in run_ids)
        if not placeholders:
            return {}, []
        rows = connection.execute(
            f"SELECT * FROM runs WHERE run_id IN ({placeholders})", tuple(run_ids)
        ).fetchall()
        calls = connection.execute(
            f"SELECT * FROM tool_calls WHERE run_id IN ({placeholders})", tuple(run_ids)
        ).fetchall()
        return {row["run_id"]: row for row in rows}, calls
    finally:
        connection.close()


_TOOL_CALL_LINE = re.compile(r"^\s{2}>\s+([a-z_][a-z0-9_]*)\(")


def raw_log_tool_calls(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recover tool evidence from retained task logs when runner state is absent.

    GitHub workflow artifacts contain every task's stdout but intentionally do
    not contain the runner-local SQLite database.  The log format records each
    tool invocation and its result, so it remains an auditable source for
    aggregate tool and retrieval metrics.
    """
    calls: list[dict[str, Any]] = []
    for entry in entries:
        stdout_path = entry.get("stdout_path")
        if not isinstance(stdout_path, str):
            continue
        path = ROOT / stdout_path
        if not path.is_file():
            continue
        active: dict[str, Any] | None = None
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = _TOOL_CALL_LINE.match(line)
            if match:
                if active is not None:
                    calls.append(active)
                active = {"tool_name": match.group(1), "is_error": None, "result_text": ""}
                continue
            if active is None:
                continue
            stripped = line.strip()
            if stripped.startswith("ok:"):
                active["is_error"] = False
                active["result_text"] += stripped[3:].strip() + "\n"
            elif stripped.startswith(("error:", "failed:")):
                active["is_error"] = True
                active["result_text"] += stripped + "\n"
            elif active["result_text"]:
                active["result_text"] += stripped + "\n"
        if active is not None:
            calls.append(active)
    return calls


def suite(trial: str, arm: str, seed: int, task_ids: list[str]) -> dict[str, Any]:
    path = RUNS / f"g3_{trial}_{arm}_seed{seed}" / "suite.json"
    if not path.is_file():
        raise ValueError(f"missing suite: {path.relative_to(ROOT)}")
    value = load(path)
    results = value.get("task_results")
    actual = [entry.get("task_id") for entry in results] if isinstance(results, list) else []
    if actual != task_ids:
        raise ValueError(f"suite task order/content mismatch: {path.relative_to(ROOT)}")
    return {"path": path, "sha256": sha256(path), "value": value}


def summarize(arm: str, suites: list[dict[str, Any]], source_documents: set[str]) -> dict[str, Any]:
    entries = [entry for suite_data in suites for entry in suite_data["value"]["task_results"]]
    agent_results = [entry.get("agent_result", {}) for entry in entries]
    run_ids = {
        result.get("activation_counters", {}).get("run_id")
        for result in agent_results
        if isinstance(result, dict) and result.get("activation_counters", {}).get("run_id")
    }
    states, state_calls = run_state_rows(set(run_ids))
    calls: list[Any] = state_calls if state_calls else raw_log_tool_calls(entries)
    successes = sum(bool(result.get("benchmark_passed")) for result in agent_results if isinstance(result, dict))
    durations_ms = [float(entry["duration_seconds"]) * 1000 for entry in entries]
    steps = sum(int(result.get("steps_used", 0) or 0) for result in agent_results if isinstance(result, dict))
    retry_steps = sum(int(result.get("retry_steps", 0) or 0) for result in agent_results if isinstance(result, dict))
    tokens = sum(int(result.get("total_tokens", 0) or 0) for result in agent_results if isinstance(result, dict))
    total_calls = len(calls)
    successful_calls = sum(
        call["is_error"] is not None and not bool(call["is_error"])
        for call in calls
    )
    failure_taxonomy: dict[str, int] = {}
    for result in agent_results:
        reason = str(result.get("termination_reason") or "external_task_timeout")
        failure_taxonomy[reason] = failure_taxonomy.get(reason, 0) + 1

    retrieval_calls = [call for call in calls if call["tool_name"] == "knowledge_retrieval"]
    hits = [
        call for call in retrieval_calls
        if not call["is_error"] and str(call["result_text"] or "").startswith("Retrieved ")
    ]
    provenance_valid = []
    for call in hits:
        text = str(call["result_text"] or "")
        cited_sources = {
            line[4:].split(" [p.", 1)[0].strip()
            for line in text.splitlines()
            if line.startswith("[") and "] " in line and not line.startswith("[workspace")
            for line in [line.split("] ", 1)[1]]
        }
        provenance_valid.append(bool(cited_sources) and cited_sources <= source_documents)

    return {
        "suite_count": len(suites),
        "task_observations": len(entries),
        "run_ids": sorted(run_ids),
        "raw_suite_sha256": {data["path"].relative_to(ROOT).as_posix(): data["sha256"] for data in suites},
        "metrics": {
            "verification_pass_rate": finite_ratio(successes, len(entries)),
            "successful_tasks": successes,
            "total_tasks": len(entries),
            "total_steps": steps,
            "total_tool_calls": total_calls,
            "tool_success_rate": finite_ratio(successful_calls, total_calls),
            "tool_retry_rate": finite_ratio(retry_steps, steps),
            "wall_latency_p50_ms": percentile(durations_ms, 0.50),
            "wall_latency_p95_ms": percentile(durations_ms, 0.95),
            "wall_duration_total_ms": sum(durations_ms),
            "token_usage": tokens,
            "estimated_cost_usd": None,
            "retrieval_call_count": len(retrieval_calls),
            "retrieval_hit_rate": finite_ratio(len(hits), len(retrieval_calls)),
            "citation_correctness_rate": None,
            "citation_provenance_valid_rate": finite_ratio(sum(provenance_valid), len(provenance_valid)),
            "failure_taxonomy": failure_taxonomy,
        },
        "run_state_records_found": len(states),
    }


def main() -> int:
    try:
        config = load(EXPERIMENT / "run-config.json")
        manifest = load(EXPERIMENT / "task-manifest.json")
        corpus = load(EXPERIMENT / "rag-corpus-manifest.json")
        task_ids = manifest["task_ids"]
        seeds = config["seeds"]
        source_documents = {str(document) for document in corpus["documents"]}
        suites = {
            arm: [suite(config["trial_id"], arm, seed, task_ids) for seed in seeds]
            for arm in ("baseline", "candidate")
        }
        summary = {arm: summarize(arm, values, source_documents) for arm, values in suites.items()}
    except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"G3 evidence: BLOCKED — {exc}")
        return 1
    evidence = {
        "schema_version": "agent-rag-ablation/v1",
        "task_count": len(task_ids),
        "seed_count": len(seeds),
        "task_manifest_sha256": config["task_manifest_sha256"],
        "rag_corpus_manifest_sha256": config["rag_corpus_manifest_sha256"],
        "agent_runtime_commit": config["agent_runtime_commit"],
        "llm_profile": config["llm_profile"],
        "baseline_run_ids": summary["baseline"]["run_ids"],
        "candidate_run_ids": summary["candidate"]["run_ids"],
        "metrics": {arm: details["metrics"] for arm, details in summary.items()},
        "raw_evidence": {arm: {key: value for key, value in details.items() if key != "metrics"} for arm, details in summary.items()},
        "gate_decision": None,
        "passed": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
