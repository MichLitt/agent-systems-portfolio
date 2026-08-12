# Agent Runtime Threat Model

Scope: the G2 local/container deployment of the Agent runtime, RAG service and
EvalOps. This is a boundary document, not a claim that arbitrary untrusted code
is safe to execute.

## Assets and trust boundaries

| Asset | Boundary | Current control |
|---|---|---|
| API tokens | Browser/client → service | Business APIs require a Bearer token when their environment token is set; only health endpoints are public. Tokens are environment variables, not repository files. |
| Agent run state and memory | Agent process → mounted volume | Persistent SQLite state is mounted separately from the demo workspace. |
| Repository task workspace | Agent shell → mounted workspace | The Compose demo workspace is mounted read-only. Real tasks must use an explicit disposable workspace. |
| RAG documents and indexes | RAG API → RAG volume | PDF-only admission, upload/chunk/storage limits, hash-based idempotency, and a dedicated worker protect the ingestion path. |
| EvalOps evidence | Producers → EvalOps database | Versioned ingest contracts, idempotent reports and token-protected business endpoints. |

## Threats and mitigations

| Threat | Mitigation present | Residual risk / operator rule |
|---|---|---|
| Unauthenticated network caller reads or mutates service data | `RAG_API_TOKEN`, `EVALOPS_API_TOKEN`, and `AGENT_API_TOKEN` protect business APIs. The closure test proves anonymous requests are rejected. | TLS, network policy and secret rotation are deployment responsibilities; do not expose local demo ports publicly. |
| Prompt instructs the Agent to run destructive host commands | The shell tool blocks a small denylist, uses timeout/process-group termination and executes from its configured workspace. | A denylist is not a sandbox. Do not mount host-sensitive paths, Docker sockets or credentials into Agent containers. |
| Agent writes outside the intended codebase | Commands use the configured workspace as `cwd`; Compose demo workspace is read-only. | Shell commands can still reference absolute paths available inside the container. Use a dedicated container/user and only mount an explicit task workspace. |
| Dependency-install loops or unbounded process execution | Task-scoped ad-hoc install budgets, command timeout and process-tree termination. | Resource limits are not yet configured in Compose; apply CPU/memory quotas in production. |
| Malicious/oversized document upload | RAG accepts PDF content types and validates upload size, chunk settings, index IDs and data-directory quota. | OCR/parser libraries process untrusted bytes. Run RAG in an isolated container and keep images patched. |
| Worker crash loses or duplicates ingestion | SQLite-backed job queue, lease reclaim, retries and content/config idempotency. | SQLite is suitable for the demo single-host deployment; use a managed queue/database for multi-host scale. |
| Token or prompt leakage through logs/artifacts | Clients send tokens only in Authorization headers; API logging records structural metadata rather than headers or raw prompts. | Treat generated trajectory/artifact volumes as sensitive; review before sharing. |

## Required operator practices

1. Copy `.env.example` to `.env`, replace `PORTFOLIO_API_TOKEN`, and never commit `.env`.
2. Keep demo ports bound to trusted local/private networks. Use TLS and a secret manager for remote deployment.
3. Run Agent tasks only against disposable repositories or a reviewed copy; never mount home directories, cloud credentials, SSH keys or Docker sockets.
4. Investigate a stuck ingestion job via worker logs before deleting volumes; lease recovery is the normal recovery path.

## Explicit non-goals

The current system does not provide tenant isolation, malware analysis, command
allowlisting, full egress control, production secret rotation, or a guarantee
that LLM-produced shell commands are safe. Those are prerequisites for a
multi-user or internet-exposed deployment, not claims made by G2.
