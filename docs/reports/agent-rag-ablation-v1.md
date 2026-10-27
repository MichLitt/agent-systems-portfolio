# G3 Agent–RAG controlled ablation

## Decision

**EvalOps decision: `promoted`.** The candidate met the predeclared non-regression gate.

> **Erratum (2026-10-27):** the token-usage figures are not provider usage, and the
> pass-rate difference cannot be attributed to retrieved content. See the
> [erratum](agent-rag-ablation-v1-erratum.md) before citing any number from this report.

## Frozen design

- Task observations: 20 tasks × 3 seeds per arm.
- Model profile: `glm_5`; Agent runtime: `5887204e5692dde68c528727170460691269947c`.
- Baseline disables `knowledge_retrieval`; candidate uses the fixed, task-independent RAG index.
- The task manifest and corpus manifest hashes are recorded in the companion evidence JSON.

## Results

| Metric | Baseline | Candidate | Candidate − baseline |
| --- | ---: | ---: | ---: |
| Verification pass rate | 76.7% | 83.3% | +6.7 pp |
| Tool success rate | 70.6% | 70.1% | — |
| Tool retry rate | 14.8% | 7.9% | — |
| p50 wall latency | 71,543.9 ms | 61,878.6 ms | — |
| p95 wall latency | 180,011.1 ms | 180,011.2 ms | — |
| Token usage | invalid (see erratum) | invalid (see erratum) | — |

## Failure observations and limitations

- Baseline failure taxonomy: `{"external_task_timeout": 9, "max_steps": 1, "retry_exhausted": 4, "verification_passed": 46}`.
- Candidate failure taxonomy: `{"external_task_timeout": 8, "max_steps": 1, "retry_exhausted": 1, "verification_passed": 50}`.
- Retrieval hit and citation correctness are reported only when retrieval calls and citation annotations are observed; absent measurements are not imputed.
- All figures are regenerated from retained suite checkpoints and task logs (using Agent run-state records when available) by `scripts/build_g3_evidence.py`; the EvalOps comparison and gate are recorded in `artifacts/evidence/agent-rag-ablation-latest.json`.
