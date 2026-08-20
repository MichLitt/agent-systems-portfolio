#!/usr/bin/env python3
"""Submit recomputed G3 arm summaries to EvalOps and create a release gate.

Run only after ``build_g3_evidence.py`` has produced a complete artifact.  The
script never fabricates a promoted decision: the returned EvalOps decision is
written back into the evidence JSON and controls its ``passed`` field.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "evidence" / "agent-rag-ablation-latest.json"
MANIFEST = ROOT / "experiments" / "g3-agent-rag-ablation" / "task-manifest.json"


def request(url: str, payload: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("EVALOPS_API_KEY", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
        raise SystemExit(f"EvalOps request failed: {exc}") from exc


def main() -> int:
    endpoint = os.environ.get("EVALOPS_ENDPOINT", "").rstrip("/")
    if not endpoint:
        raise SystemExit("EVALOPS_ENDPOINT must point to the EvalOps /v1 base URL")
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if evidence.get("passed") or evidence.get("gate_decision") is not None:
        raise SystemExit("evidence already has a gate decision; do not overwrite historical result")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    task_ids = manifest["task_ids"]
    run_ids: dict[str, str] = {}
    for arm in ("baseline", "candidate"):
        metric = evidence["metrics"][arm]
        run_id = f"g3-agent-rag-ablation-{arm}-aggregate-v1"
        run_ids[arm] = run_id
        payload = {
            "schema_version": "agent/v1", "run_id": run_id, "run_type": "eval",
            "status": "completed", "benchmark_name": "g3_agent_rag_ablation_v1",
            "task_ids": task_ids, "preset": "C3", "llm_profile": evidence["llm_profile"],
            "git_commit": evidence["agent_runtime_commit"],
            "total_steps": metric["total_steps"], "total_tool_calls": metric["total_tool_calls"],
            "tool_success_rate": metric["tool_success_rate"], "total_tokens": metric["token_usage"],
            # EvalOps agent/v1 owns this field as an integer millisecond count.
            # The evidence aggregator retains fractional milliseconds so it can
            # compute percentiles without premature rounding.
            "wall_duration_ms": int(round(metric["wall_duration_total_ms"])),
            "verification_pass_rate": metric["verification_pass_rate"],
            "tool_retry_rate": metric["tool_retry_rate"], "retrieval_hit_rate": metric["retrieval_hit_rate"],
            "citation_correctness_rate": metric["citation_correctness_rate"],
            "wall_latency_p50_ms": metric["wall_latency_p50_ms"],
            "wall_latency_p95_ms": metric["wall_latency_p95_ms"],
            "estimated_cost_usd": metric["estimated_cost_usd"],
        }
        request(f"{endpoint}/ingest/agent/v1", payload)

    # Let a separately-run local normalizer claim and normalize both reports.
    deadline = time.monotonic() + 20
    compare: dict | None = None
    while time.monotonic() < deadline:
        try:
            compare = request(f"{endpoint}/compare", {
                "app_type": "agent", "baseline_run_id": run_ids["baseline"],
                "candidate_run_id": run_ids["candidate"],
            })
            break
        except SystemExit:
            time.sleep(1)
    if compare is None:
        raise SystemExit("EvalOps did not normalize G3 aggregate reports before timeout")

    # Promotion must prove no quality regression while documenting non-quality
    # metrics.  A neutral/rejected outcome is persisted honestly by this script.
    gate = request(f"{endpoint}/gate", {
        "compare_session_id": compare["compare_session_id"],
        "rules": [
            {"metric": "verification_pass_rate", "op": "delta_abs_gte", "threshold": 0.0, "required": True},
            {"metric": "tool_success_rate", "op": "delta_abs_gte", "threshold": -0.05, "required": True},
            {"metric": "wall_latency_p95_ms", "op": "delta_pct_lte", "threshold": 1.0, "required": False},
        ],
    })
    evidence["baseline_run_ids"] = evidence["baseline_run_ids"] + [run_ids["baseline"]]
    evidence["candidate_run_ids"] = evidence["candidate_run_ids"] + [run_ids["candidate"]]
    evidence["evalops_compare_session_id"] = compare["compare_session_id"]
    evidence["evalops_gate"] = gate
    evidence["gate_decision"] = gate["decision"]
    evidence["passed"] = gate["decision"] == "promoted"
    EVIDENCE.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"EvalOps gate: {gate['decision']}")
    return 0 if evidence["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
