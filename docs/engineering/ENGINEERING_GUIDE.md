# Engineering Guide

## 1. Purpose

This workspace demonstrates an end-to-end Agent engineering system rather
than four unrelated demos. The core production loop is:

```text
document ingestion -> retrieval service -> Agent tool use
                   -> versioned run reporting -> comparison -> release gate
```

The projects deliberately remain separate deployable units with independent
Git histories, lockfiles, environments, tests, and failure domains. The parent
portfolio repository pins their released commits through Git submodules.

## 2. Runtime Architecture

| Service | Default address | Process model | Persistence |
|---|---|---|---|
| RAG API | `127.0.0.1:8080` | FastAPI; ingestion background tasks | Index directory + in-memory jobs |
| Agent Runtime API | `127.0.0.1:8765` | FastAPI; background Agent runs | SQLite run state + audit trail |
| EvalOps API | `127.0.0.1:8000` | FastAPI ingest/query/compare/gate | SQLite WAL |
| EvalOps Worker | no port | Separate polling process | Same EvalOps SQLite file |

The closure script allocates temporary ports and storage, starts the real RAG
and EvalOps processes, and calls the real Agent tool and producer clients.

## 3. Contract Reference

### 3.1 RAG Retrieval

Request:

```json
{
  "query": "When is a candidate promoted?",
  "index_id": "release-manual",
  "top_k": 5
}
```

Response fields relied on by the Agent:

```json
{
  "results": [
    {
      "doc_id": "manual-c0001",
      "text": "...",
      "score": 1.0,
      "metadata": {
        "source": "manual.pdf",
        "page_start": 2,
        "page_end": 3,
        "section": "Release Gate"
      }
    }
  ],
  "latency_ms": 4.2,
  "retrieval_profile": "auto",
  "index_id": "release-manual"
}
```

`index_id` is restricted to a safe portable identifier. Runtime ingestion and
registry discovery must use the same `--data-dir` root.

### 3.2 EvalOps Producer Schemas

`agent/v1` carries run type/status, steps, tool calls, tool success, tokens,
wall duration, preset/profile, and eval task metadata. Eval task set identity
is a stable hash of benchmark name and sorted task IDs. Service runs have no
task set and cannot be compared.

`rag/v1` carries dataset, retrieval/generator configuration, QA metrics,
faithfulness/hallucination, latency, cost, and retrieval trace extras. Dataset
is the comparison task set.

The URL schema key and payload `schema_version` must match. Invalid payloads
return HTTP 422 before entering the worker queue.

### 3.3 Compare and Gate

1. Both runs must exist.
2. Both runs must have the same `app_type`.
3. Both runs must have the same non-null `task_set_id`.
4. Compare persists absolute and percentage deltas.
5. Gate evaluates rules against the persisted compare session.
6. Required-rule failure rejects the release; otherwise it is promoted.

## 4. Development Workflow

All work follows
[`AGENT_ENGINEERING_STANDARD.md`](./AGENT_ENGINEERING_STANDARD.md). The active
delivery scope and Gate criteria live in
[`competitive-portfolio-delivery-plan.md`](../plans/competitive-portfolio-delivery-plan.md).

1. Read root/project instructions, the engineering standard, and the active Gate.
2. Inspect the target project's Git status, Submodule state, current baseline, and evidence.
3. Define a bounded slice with acceptance criteria, consumers, tests, and rollback.
4. Make the smallest coherent change that preserves the shared contracts.
5. Run targeted tests, then the full owner-project suite.
6. Run every consumer/producer suite affected by a contract change.
7. Run `./scripts/run_three_project_closure.sh` for integration changes.
8. Update README, project reports, plans, and this guide if behavior or contracts changed.
9. Run readiness, `git diff --check`, and review all affected worktrees before handoff.

## 5. Test and Release Gates

```bash
# Core project suites
./scripts/check_core_projects.sh

# Post-training pipeline CLI smoke
./scripts/check_finetune_project.sh

# True cross-project workflow
./scripts/run_three_project_closure.sh

# Delivery Gate status (informational unless --require is used)
./scripts/check_delivery_readiness.py

# All local gates
make check
```

Current verified local gates:

- Agent: 275 passed.
- EvalOps: 45 passed.
- RAG: 415 passed, 1 optional-model skip.
- Closure: RAG ingestion and Agent retrieval passed; Agent and RAG gates promoted.

These counts are orientation, not permanent assertions. Test command exit
status and the current closure artifact are authoritative.

### Delivery Gates

- **G0 Engineering Closure** — capability tests and real local closure.
- **G1 Release Baseline** — merged main commits, full CI, aligned Submodules, release notes/tag.
- **G2 Demo-Ready Product** — reproducible stack, recoverable ingestion, review loop, operations/security evidence.
- **G3 Evidence-Backed Flagship** — controlled baseline/candidate experiment and reproducible quantified evidence.

For the formal G3 executor, secrets, raw-artifact retention, and gate sequence,
see [G3 formal-run guide](G3_FORMAL_RUN_GUIDE.md).

G2 is the minimum competitive resume threshold. G3 is mandatory for quality
uplift claims. The readiness script checks machine-verifiable criteria; manual
criteria remain authoritative in the delivery plan.

## 6. Baselines and Evidence

- Agent benchmark claims must use its accepted versioned baseline reports and matching artifacts.
- RAG benchmark claims must be backed by run JSON/JSONL and the owning report.
- EvalOps decisions are operational evidence, not evidence that a model benchmark is statistically significant.
- Never mix offline synthetic closure results with paid/real-model benchmark claims.
- Do not overwrite versioned baselines; add a new report when project rules require one.

## 7. Data and Secrets

- `.env` is local only.
- API keys, SQLite databases, indexes, checkpoints, and model weights stay out of source control.
- Small machine-readable acceptance artifacts may live under `artifacts/`.
- Large experiment output stays inside the owning project's ignored results directory or external storage.

## 8. Workspace Moves

The recommended directory name is `agent-systems-portfolio`. After renaming,
refresh all environments with:

```bash
make refresh
```

This refreshes editable-install paths and console-script shebangs that may
still contain the previous absolute workspace path. Then rerun `make check`.
