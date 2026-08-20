# Agent Systems Portfolio

A cohesive AI engineering portfolio built around one production-style loop:
an Agent Runtime uses a document knowledge service, while a shared EvalOps
platform records runs, compares candidates, and makes release decisions.

The workspace contains three integrated core systems plus one post-training
extension. Each project remains an independent Git repository and Python
environment, pinned by this parent repository as a Git submodule. This root
provides the shared architecture, operating rules, and verification entry
points.

## System Overview

```mermaid
flowchart LR
    D["PDF / OCR documents"] --> R["RAG Knowledge Service"]
    R -->|"POST /v1/retrieve"| A["Coding Agent Runtime"]
    R -->|"rag/v1 run report"| E["EvalOps Platform"]
    A -->|"agent/v1 run report"| E
    E --> C["Compare session"]
    C --> G["Release gate"]
    F["Targeted Post-Training"] -. "future finetune/v1" .-> E
    F -. "failure-driven model improvement" .-> A
```

## Projects

| Project | Role | Current state |
|---|---|---|
| [`llm-coding-agent-system`](./llm-coding-agent-system/) | Persistent Agent Runtime, tool execution, verification, resume/retry, knowledge tool | Integrated; 275 tests passing |
| [`rag-benchmark-system`](./rag-benchmark-system/) | PDF/OCR ingestion, BM25/FAISS retrieval API, citation/NLI evaluation | Integrated; 415 tests passing, 1 optional skip |
| [`llm-evalops-platform`](./llm-evalops-platform/) | Versioned ingest, normalization worker, run comparison, release gate | Integrated; 45 tests passing |
| [`coding-llm-finetune`](./coding-llm-finetune/) | Failure-driven SFT/DPO pipeline and clean evaluation | Extension; pipeline prepared, training pending |

## Delivery Status

The integrated engineering baseline is complete, but the portfolio is not yet
declared demo-ready or evidence-backed. Delivery is governed by explicit Gates:

| Gate | Meaning | Status |
|---|---|---|
| G0 Engineering Closure | Tests and real local Agent/RAG/EvalOps closure | **Ready** |
| G1 Release Baseline | Child changes merged to `main`, full CI, release tag | **Ready — v0.1.0** |
| G2 Demo-Ready Product | One-command stack, review UI, recoverable ingestion | **Ready — v0.2.0** |
| G3 Evidence-Backed Flagship | Controlled Agent baseline/candidate evaluation | **Ready — formal evidence published; v0.3.0 release pending** |

## Demo Stack

With Docker Desktop installed, start the four-service demonstration and its
offline seed data with:

```bash
cp .env.example .env  # choose a unique PORTFOLIO_API_TOKEN
docker compose --profile demo up --build
```

Then open the EvalOps review page at `http://localhost:8000/ui/`. The complete
startup, recovery, security boundaries and reset procedure are in the
[operations runbook](docs/engineering/OPERATIONS_RUNBOOK.md).

See the
[`competitive portfolio delivery plan`](./docs/plans/competitive-portfolio-delivery-plan.md)
for the work breakdown, acceptance evidence, and allowed resume claims. Run the
local readiness assessor at any time:

```bash
make readiness
```

The G3 baseline/candidate evaluation covers 20 fixed repository tasks across
three seeds per arm. Its gated result, raw-suite hashes, failure taxonomy and
limitations are recorded in the [G3 report](docs/reports/agent-rag-ablation-v1.md)
and companion [evidence artifact](artifacts/evidence/agent-rag-ablation-latest.json).

## Quick Verification

Run all three integrated project test suites:

```bash
make test
```

Run the post-training extension's offline CLI smoke checks:

```bash
make finetune-smoke
```

Run the real local HTTP closure—generated PDF → RAG ingestion → Agent
retrieval → Agent/RAG reports → EvalOps compare/gate:

```bash
make closure
```

No LLM key, cloud service, external model, or production index is required for
the closure test. Its latest machine-readable result is stored at
[`artifacts/closure/three-project-closure-latest.json`](./artifacts/closure/three-project-closure-latest.json).

## Local Development

Clone the complete portfolio and its four pinned repositories with:

```bash
git clone --recurse-submodules https://github.com/MichLitt/agent-systems-portfolio.git
cd agent-systems-portfolio
make refresh
```

For an existing clone, initialize or update all project checkouts with
`git submodule update --init --recursive`.

Each project owns its dependencies:

```bash
cd llm-evalops-platform && uv sync
cd ../rag-benchmark-system && uv sync
cd ../llm-coding-agent-system && uv sync
```

To run the integrated services manually:

```bash
# Terminal 1: EvalOps API
cd llm-evalops-platform
uv run python scripts/start_api.py

# Terminal 2: EvalOps normalization worker
cd llm-evalops-platform
uv run python scripts/start_worker.py

# Terminal 3: RAG retrieval service
cd rag-benchmark-system
uv run python scripts/start_api.py --data-dir data/indexes --port 8080

# Terminal 4: Agent with both integrations
cd llm-coding-agent-system
export RAG_API_URL=http://localhost:8080
export EVALOPS_ENDPOINT=http://localhost:8000/v1/ingest/agent/v1
uv run python -m coder_agent
```

RAG evaluation processes use their own producer endpoint:

```bash
export EVALOPS_ENDPOINT=http://localhost:8000/v1/ingest/rag/v1
```

## Documentation

- [`AGENTS.md`](./AGENTS.md) — canonical instructions for coding agents working anywhere in this workspace.
- [`docs/engineering/AGENT_ENGINEERING_STANDARD.md`](./docs/engineering/AGENT_ENGINEERING_STANDARD.md) — normative lifecycle, contract, testing, evidence, security, and PR rules.
- [`docs/engineering/ENGINEERING_GUIDE.md`](./docs/engineering/ENGINEERING_GUIDE.md) — architecture, contracts, workflows, and release gates.
- [`docs/plans/competitive-portfolio-delivery-plan.md`](./docs/plans/competitive-portfolio-delivery-plan.md) — active plan from engineering closure to a resume-ready flagship.
- [`docs/roadmap/portfolio-roadmap.md`](./docs/roadmap/portfolio-roadmap.md) — portfolio strategy and longer-term roadmap.
- [`docs/plans/three-project-closure-plan.md`](./docs/plans/three-project-closure-plan.md) — implemented integration plan and acceptance evidence.
- [`docs/README.md`](./docs/README.md) — complete documentation index.

## Workspace Layout

```text
.
├── AGENTS.md
├── README.md
├── Makefile
├── docs/
│   ├── engineering/
│   ├── roadmap/
│   ├── plans/
│   └── career/
├── artifacts/closure/
├── scripts/
├── llm-coding-agent-system/
├── rag-benchmark-system/
├── llm-evalops-platform/
└── coding-llm-finetune/
```

The recommended workspace directory name is `agent-systems-portfolio`.
After moving the directory, run `make refresh` once to rebuild absolute paths
inside the four project environments.
