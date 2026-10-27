# G3 Agent–RAG ablation — erratum

Date: 2026-10-27

Applies to: [`agent-rag-ablation-v1.md`](agent-rag-ablation-v1.md) and
[`agent-rag-ablation-latest.json`](../../artifacts/evidence/agent-rag-ablation-latest.json)
(Agent runtime `5887204e5692dde68c528727170460691269947c`, profile `glm_5`,
20 tasks × 3 seeds per arm).

This erratum corrects how three G3 results should be read. It does not change
the raw evidence or the EvalOps decision. The evidence JSON is kept as
recorded; the rendered report now links here.

## 1. Token usage was not measured

**Issue.** The reported token usage (50,999 baseline; 51,994 candidate) is
not provider usage. At this runtime commit, neither LLM backend read the
provider's `usage`. Every result's `total_tokens` was the initial context
estimate `len(system_prompt) // 4`, and the evidence builder summed those
estimates.

**Evidence.**

- The per-task averages (850 and 867) do not depend on work done. The
  candidate arm used fewer steps (203 vs 230) yet reports more "tokens".
- At the next runtime commit, all 18 v0.8 ComplexCodeBench runs record exactly
  968 tokens. Rebuilding the system prompt for that run's workspace gives
  `len(system_prompt) // 4 == 968`.

**Impact.**

- No token or cost figure from G3 may be cited.
- The figures cannot be recovered. Provider usage was never recorded, and the
  raw CI artifacts expired after their 30-day retention.
- The gate decision is unaffected; no gate rule used tokens.

**Fix.** Provider-reported usage accounting was added in Agent
`IMPROVEMENT_REPORT_v0.8.0-token-usage.md`.
`scripts/build_g3_evidence.py` now aggregates only result `usage` fields and
emits `token_usage_status`. Legacy results produce `null`, never an estimate.

## 2. The pass-rate difference cannot be attributed to retrieved content

**Issue.** The report presents verification pass rate rising from 46/60
(76.7%) to 50/60 (83.3%), +6.7 pp. That difference is not evidence that
retrieved document content improved the Agent.

**Evidence.**

- **Retrieval was rarely used.** Across all 60 candidate task observations,
  `knowledge_retrieval` was called 4 times. Only 2 calls returned results, and
  the citation provenance check validated 0 of those 2. At most two task runs
  received any retrieved content, while the arms differ by four successes.
- **The difference is within noise.** A two-sided Fisher exact test on
  50/60 vs 46/60 gives p ≈ 0.49. Detecting a 6.7 pp difference at this base
  rate with 80% power needs roughly 570 observations per arm.
- **The arms differ in more than content.** Registering the tool changes the
  tool schema presented to the model in every candidate step. Any real
  candidate effect could come from tool presence rather than from retrieved
  content, and this design cannot separate the two.

**Correct reading.** Under a frozen protocol, the candidate configuration met
the predeclared non-regression gate, and the observed difference is consistent
with chance. G3 demonstrates the evaluation pipeline: frozen manifests,
raw-suite hashes, failure taxonomy, recomputable metrics, and an EvalOps
compare/gate. It is not a measured quality improvement from RAG.

## 3. The external timeout dominated latency and part of the failures

**Issue.** 9/60 baseline and 8/60 candidate observations ended at the 180 s
external task timeout (`experiments/g3-agent-rag-ablation/run-config.json`).
Both arms' p95 wall latency equals that cap: 180,011.1 ms and 180,011.2 ms.

**Impact.**

- The `wall_latency_p95_ms` gate rule compared the cap with itself, so it
  carried no information.
- About 15% of observations measure the time budget, not Agent capability.
  The p50 latency difference is also affected, because truncated runs enter
  the distribution at the cap.

**Context for later protocols.** In the unaccepted v0.8 snapshots (5
completed SWE-12 tasks), single-attempt SWE task wall time has p50 ≈ 160 s
and max ≈ 356 s, so a 180 s cap would truncate most repository-repair tasks.
Future protocols must:

- set the external budget from a dev-split pilot distribution (above the p99);
- report budget timeouts as their own category;
- not gate on a latency percentile that saturates at the cap.

## What remains valid

- Pass/fail counts per arm (46/60 and 50/60) and the failure taxonomy.
- Tool success and retry rates, which are computed from run-state tool audits.
- The retrieval call, hit and provenance counts quoted above.
- Reproducibility: the task and corpus manifest hashes, raw-suite SHA256
  values, and the EvalOps compare/gate record.

## Claims boundary

Supported:

- A frozen baseline/candidate protocol with recomputable metrics and an
  automated EvalOps compare/gate was built and executed (20 tasks × 3 seeds
  per arm).
- The RAG-enabled configuration was non-inferior under the gate, at 50/60
  vs 46/60.

Not supported:

- Any statement that retrieval or document grounding *improved* pass rate.
- Any token, cost or cost-efficiency figure from G3.
- Any latency-percentile comparison from G3.
