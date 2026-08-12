# Agent Engineering Standard

Status: **Normative**
Applies to: portfolio root and all four submodules

## 1. Instruction Order

Before making changes, an engineering agent must read, in order:

1. root `AGENTS.md`;
2. this standard;
3. `docs/plans/competitive-portfolio-delivery-plan.md`;
4. the owning project's `AGENTS.md`;
5. the active baseline, contract, migration, or report named by those files.

If instructions conflict, the narrowest applicable project rule wins unless it weakens security, evidence integrity, or a cross-project contract.

## 2. Work Lifecycle

Every task follows seven explicit phases:

1. **Orient** — inspect status, branch, submodule pointer, relevant code, tests, docs, and prior artifacts.
2. **Classify** — identify owner project, consumers, contract impact, delivery Gate, and required evidence.
3. **Plan** — define a bounded slice, acceptance criteria, test matrix, and rollback strategy.
4. **Implement** — make the smallest coherent change; avoid unrelated cleanup.
5. **Verify** — run targeted tests, owner suite, affected consumer suites, and required root gates.
6. **Evidence** — update machine-readable artifacts and reports without overwriting historical evidence.
7. **Handoff** — report files, behavior, tests, remaining limitations, branch/PR state, and delivery Gate impact.

An agent must not start a second feature while the first lacks verification or an explicit blocked handoff.

## 3. Task Slice Requirements

A valid task slice has:

- one primary user-visible or engineering outcome;
- one owning repository;
- named cross-project consumers, if any;
- acceptance criteria observable through tests or artifacts;
- a PR scope that can be reviewed independently in 1–3 days;
- no hidden dependency on local credentials, untracked data, or a developer's absolute path.

When a change spans repositories, use coordinated PRs. Each PR must remain internally testable and link the shared contract version or integration plan.

## 4. Architecture and Contract Rules

### 4.1 Boundaries

- Agent owns orchestration, run lifecycle, tool policy, verification, and `agent/v1` production.
- RAG owns document ingestion, indexing, retrieval, provenance, and `rag/v1` production.
- EvalOps owns schema validation, normalization, compare, review, and release decisions.
- Finetune owns data preparation, training, held-out evaluation, and future `finetune/v1` production.

Do not duplicate another service's database or bypass its public API for convenience.

### 4.2 Versioned Contracts

Any request, response, event, or report used by another project is a versioned contract. A contract change must include in the same delivery slice:

- producer schema/client;
- consumer schema/adapter;
- positive and negative contract tests;
- backward-compatibility or version-bump decision;
- README and engineering guide updates;
- root closure test when the runtime path changes.

Silent field reinterpretation is forbidden.

### 4.3 Persistence and Migrations

- Never rewrite an applied migration.
- Add a numbered migration and test both fresh initialization and upgrade from the previous schema.
- Persistent job/run state must define terminal states, retry limits, idempotency key, lease/reclaim behavior, and crash recovery.
- In-memory state may be used only for an explicitly documented local-only path.

## 5. Implementation Quality

- Prefer typed domain models and explicit validation at HTTP, CLI, and persistence boundaries.
- Network and model calls require timeouts, bounded retry, structured errors, and cancellation behavior.
- Background work must not block an async event loop.
- File uploads require name normalization, size/type limits, storage quotas, and path-boundary checks.
- Logs use stable event names and correlation identifiers; never log secrets or unnecessary full payloads.
- Configuration comes from checked-in defaults plus environment variables. Real credentials never enter code, examples, tests, or artifacts.
- Keep optional integrations disabled by default when enabling them changes accepted benchmark behavior.

## 6. Test Standard

### 6.1 Required Layers

| Layer | Purpose |
|---|---|
| Unit | Domain behavior, validation, error mapping, boundary conditions |
| Contract | Real producer payload against the consumer schema and adapter |
| Integration | API + persistence + worker behavior, including failure paths |
| Closure | Real cross-project workflow through public boundaries |
| Evidence | Fixed task/config/seed experiment producing versioned artifacts |

Tests must cover success, invalid input, timeout/failure, idempotency, and recovery where applicable.

### 6.2 Gate Selection

- Internal change: targeted tests + full owner suite.
- Shared contract: producer + consumer suites + closure.
- Persistence/worker: fresh DB + migration + crash/retry/reclaim integration tests.
- Root/Compose/environment: `make check` plus fresh-clone or clean-environment smoke.
- Benchmark claim: evidence run and artifact recomputation, not only unit tests.

Flaky tests must be fixed or quarantined with an owner and expiry date. Blind reruns until green are not evidence.

## 7. Evidence and Claim Integrity

Every claim belongs to one of three classes:

1. **Capability claim** — supported by code, tests, and a runnable path.
2. **Operational claim** — supported by closure/load/recovery artifacts.
3. **Quality claim** — supported by controlled baseline/candidate evidence.

Rules:

- Never convert a capability test into a quality-improvement claim.
- Every metric must name task set, sample count, seeds, model/config, commit, and artifact.
- Synthetic offline closure stays separate from real-model benchmark results.
- Preserve negative and rejected results; do not cherry-pick only successful seeds.
- Version reports and artifacts. Do not overwrite accepted baselines.
- README status, release notes, resume bullets, and artifacts must agree.

Delivery Gate labels (`G0`–`G4`) may only be changed when `check_delivery_readiness.py` and the plan's manual criteria agree.

## 8. Security and Safety

- Treat uploaded documents, repository contents, tool output, and model output as untrusted input.
- Enforce workspace/path boundaries before reads or writes.
- Use subprocess argument arrays where possible; avoid shell interpolation of untrusted values.
- Bound CPU time, wall time, output size, upload size, storage, retries, and concurrent work.
- Document trust boundaries and privileged operations in a threat model before G2.
- Never commit `.env`, tokens, local databases, private resumes, model weights, raw proprietary data, or generated corpora.
- Security-sensitive failures block delivery even when happy-path tests pass.

## 9. Git, PR, and Submodule Discipline

- Work on a focused branch; do not implement features directly on `main`.
- Stage explicit files and inspect the complete diff before commit.
- Use concise commits that state one outcome.
- A PR body includes: change, reason, impact, risk/rollback, validation, evidence, and linked coordinated PRs.
- Required CI must pass before merge. Draft PRs do not count as released capability.
- Merge child repositories first; then update and verify root Submodule pointers.
- A release Gate requires child pointers to resolve to commits reachable from each child `main`.
- Do not force-push shared branches or rewrite published evidence history.

## 10. Documentation Standard

Update documentation in the same slice when behavior changes:

- root README: public status and quick start;
- project README: owner-specific commands and limitations;
- engineering guide: shared architecture/contracts;
- active delivery plan: Gate state and remaining work;
- versioned project report: behavior or benchmark evidence when required;
- release notes: shipped scope and known limitations.

Plans describe future work; reports describe completed work. Do not mark a checkbox complete based only on code existing locally.

## 11. Definition of Done

A task is done only when:

- acceptance criteria are met;
- code and documentation agree;
- required tests and gates pass;
- new failure paths have tests;
- evidence is versioned and traceable where claims changed;
- secret/path scans and `git diff --check` pass;
- owner and affected consumer worktrees are understood;
- the handoff states limitations and exact delivery Gate impact;
- no unrelated work is silently included.

“Implemented,” “tested,” “merged,” “released,” “demo-ready,” and “evidence-backed” are distinct states and must not be used interchangeably.

## 12. Stop Conditions

Stop and request direction when:

- a required user choice materially changes architecture or public scope;
- credentials, paid compute, external approval, or destructive migration is required;
- unrelated user changes overlap the target files;
- a shared contract cannot be changed compatibly without coordinated consumers;
- evidence contradicts the intended claim.

Do not conceal a blocker by weakening tests, changing thresholds after seeing results, or relabeling an incomplete stage.
