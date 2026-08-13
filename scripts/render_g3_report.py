#!/usr/bin/env python3
"""Render the versioned G3 report strictly from a gated evidence artifact."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "artifacts" / "evidence" / "agent-rag-ablation-latest.json"
REPORT = ROOT / "docs" / "reports" / "agent-rag-ablation-v1.md"


def pct(value: float | None) -> str:
    return "not measured" if value is None else f"{value * 100:.1f}%"


def number(value: float | None, digits: int = 1) -> str:
    return "not measured" if value is None else f"{value:,.{digits}f}"


def main() -> int:
    if not EVIDENCE.is_file():
        print("G3 report: BLOCKED — missing gated evidence artifact")
        return 1
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    decision = evidence.get("gate_decision")
    if decision not in {"promoted", "rejected"}:
        print("G3 report: BLOCKED — evidence has no EvalOps gate decision")
        return 1
    baseline = evidence["metrics"]["baseline"]
    candidate = evidence["metrics"]["candidate"]
    delta = (candidate["verification_pass_rate"] or 0) - (baseline["verification_pass_rate"] or 0)
    conclusion = (
        "The candidate met the predeclared non-regression gate."
        if decision == "promoted"
        else "The candidate did not meet the predeclared release gate; no quality-improvement claim is warranted."
    )
    content = f"""# G3 Agent–RAG controlled ablation

## Decision

**EvalOps decision: `{decision}`.** {conclusion}

## Frozen design

- Task observations: {evidence['task_count']} tasks × {evidence['seed_count']} seeds per arm.
- Model profile: `{evidence['llm_profile']}`; Agent runtime: `{evidence['agent_runtime_commit']}`.
- Baseline disables `knowledge_retrieval`; candidate uses the fixed, task-independent RAG index.
- The task manifest and corpus manifest hashes are recorded in the companion evidence JSON.

## Results

| Metric | Baseline | Candidate | Candidate − baseline |
| --- | ---: | ---: | ---: |
| Verification pass rate | {pct(baseline['verification_pass_rate'])} | {pct(candidate['verification_pass_rate'])} | {delta * 100:+.1f} pp |
| Tool success rate | {pct(baseline['tool_success_rate'])} | {pct(candidate['tool_success_rate'])} | — |
| Tool retry rate | {pct(baseline['tool_retry_rate'])} | {pct(candidate['tool_retry_rate'])} | — |
| p50 wall latency | {number(baseline['wall_latency_p50_ms'])} ms | {number(candidate['wall_latency_p50_ms'])} ms | — |
| p95 wall latency | {number(baseline['wall_latency_p95_ms'])} ms | {number(candidate['wall_latency_p95_ms'])} ms | — |
| Token usage | {number(baseline['token_usage'], 0)} | {number(candidate['token_usage'], 0)} | — |

## Failure observations and limitations

- Baseline failure taxonomy: `{json.dumps(baseline['failure_taxonomy'], sort_keys=True)}`.
- Candidate failure taxonomy: `{json.dumps(candidate['failure_taxonomy'], sort_keys=True)}`.
- Retrieval hit and citation correctness are reported only when retrieval calls and citation annotations are observed; absent measurements are not imputed.
- All figures are regenerated from retained suite checkpoints and Agent run-state records by `scripts/build_g3_evidence.py`; the EvalOps comparison and gate are recorded in `artifacts/evidence/agent-rag-ablation-latest.json`.
"""
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(content, encoding="utf-8")
    print(f"Wrote {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
