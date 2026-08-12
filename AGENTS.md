# AGENTS.md

This is the canonical workspace-level instruction file. It applies to all
projects unless a nested `AGENTS.md` adds stricter project-specific rules.
`CLAUDE.md` files are compatibility pointers; do not maintain a second copy of
the same instructions there.

## Read First

Before changing code, read:

1. `README.md` for the workspace map and current status.
2. `docs/engineering/AGENT_ENGINEERING_STANDARD.md` for the normative work lifecycle, evidence, security, Git, and completion rules.
3. `docs/plans/competitive-portfolio-delivery-plan.md` for the active delivery Gate and acceptance criteria.
4. `docs/engineering/ENGINEERING_GUIDE.md` for shared architecture and API contracts.
5. The target project's `AGENTS.md` for local commands, invariants, and report rules.
6. Any active baseline, migration, contract, or report named by those instructions.

## Project Map

| Directory | Responsibility | Primary boundary |
|---|---|---|
| `llm-coding-agent-system/` | Agent runtime and tools | `knowledge_retrieval`, `agent/v1` |
| `rag-benchmark-system/` | Document ingestion and retrieval | `/v1/ingest`, `/v1/retrieve`, `rag/v1` |
| `llm-evalops-platform/` | Observability and release decisions | ingest → normalize → compare → gate |
| `coding-llm-finetune/` | Targeted post-training | future `finetune/v1` producer |

The first three projects form the production closure. Finetune is an extension
and must not be represented as completed while its README results remain TBD.

## Shared Commands

- Core test gate: `./scripts/check_core_projects.sh`
- Finetune CLI smoke: `./scripts/check_finetune_project.sh`
- Cross-project HTTP closure: `./scripts/run_three_project_closure.sh`
- Documentation/layout gate: `python3 scripts/check_workspace_docs.py`
- Delivery readiness report: `python3 scripts/check_delivery_readiness.py`
- All workspace gates: `make check`
- Documentation index: `docs/README.md`

Run project-local commands from that project's directory. Do not assume one
project's virtual environment contains another project's dependencies.

## Delivery Gate Discipline

- G0 proves the integrated capability works locally.
- G1 requires merged child `main` commits, CI, aligned Submodule pointers, release notes, and a tag.
- G2 is the minimum competitive resume threshold and requires one-command demo, review loop, recoverable ingestion, operations documentation, and security smoke evidence.
- G3 is required before writing quantified quality-improvement claims; it requires a controlled baseline/candidate experiment and reproducible evidence artifact.
- G4 Finetune is optional and must not block the Agent platform from reaching G2/G3.

Run `make readiness` when planning and before handoff. Use the strict
`make require-release`, `make require-demo`, or `make require-evidence` targets
only when claiming that Gate. A local feature, Draft PR, or passing unit suite
does not by itself advance a delivery Gate.

## Cross-Project Contracts

### RAG → Agent

- Enable with `RAG_API_URL=http://<host>:8080` in the Agent process.
- Agent calls `POST /v1/retrieve` with `query`, `index_id`, and `top_k`.
- Results must retain `text`, `score`, and `metadata.source/page_start/page_end`.
- With `RAG_API_URL` unset, `knowledge_retrieval` must not be registered.

### Producers → EvalOps

- Agent endpoint: `/v1/ingest/agent/v1`; schema key `agent/v1`.
- RAG endpoint: `/v1/ingest/rag/v1`; schema key `rag/v1`.
- Ingest payloads are Pydantic-validated and idempotent by producer/schema/run ID.
- API and normalization worker are separate processes sharing one SQLite database.
- Compare requires matching non-null task sets. Gate consumes a persisted compare session.

When a shared contract changes, update producer schema/client, consumer
schema/adapter, integration tests, both affected READMEs, and the engineering
guide in the same task.

## Required Gates

| Change | Minimum verification |
|---|---|
| One project, internal only | Targeted tests + full project suite |
| RAG request/response or Agent knowledge tool | Agent + RAG suites + closure script |
| EvalOps ingest/adapter/compare/gate | EvalOps suite + both producer contract tests + closure script |
| Finetune pipeline/config/docs | Finetune CLI smoke; training claims require artifact-backed validation |
| Root scripts or shared environment | All core suites + closure script |
| Documentation only | Link/path scan and Markdown fence check |

Never claim closure from unit tests alone. The authoritative integration
artifact is `artifacts/closure/three-project-closure-latest.json`.

## File and Documentation Layout

- Keep only workspace entry points and engineering config at the root.
- Roadmaps belong in `docs/roadmap/`.
- Execution plans belong in `docs/plans/`.
- Shared engineering references belong in `docs/engineering/`.
- Resume/career material belongs in `docs/career/`.
- Generated verification evidence belongs in `artifacts/`.
- Project-specific plans and reports remain inside the owning project.

After moving a document, update every reference with `rg` before closing the task.

## Git and Safety

- The workspace root is a Git repository; each project is an independent Git
  repository pinned here as a submodule.
- Commit code inside the owning submodule first, then commit the updated
  submodule pointer in the workspace repository.
- Inspect `git status` in every affected project before editing.
- Preserve user changes and do not reset, clean, commit, push, or open PRs unless requested.
- Do not mix unrelated project changes into one claim of verification.
- Never commit `.env`, API keys, model tokens, local databases, large indexes, checkpoints, or model weights.

## Environment and Reproducibility

- Use `uv` and the project's checked-in lockfile.
- Copy `.env.example` locally; never edit real credentials into documentation.
- External model/API tests must be reported separately from offline tests.
- If the workspace directory moves, recreate or resync each `.venv` because
  console-script shebangs and editable-install paths may contain the old absolute path.

## Completion Checklist

- The task follows `AGENT_ENGINEERING_STANDARD.md` and names its owning project and delivery Gate impact.
- Code, schemas, docs, and examples agree.
- Required project suites pass.
- Cross-project closure passes when an integration boundary changed.
- Generated evidence points to the current layout.
- README/plan status is not ahead of the available artifact and merged branch state.
- `git diff --check` passes in each affected repository.
- Remaining external or paid validation is explicitly separated from completed local work.
