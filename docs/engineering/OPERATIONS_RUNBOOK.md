# Operations Runbook

## Start the demo

Install Docker Desktop, then from the portfolio root run:

```bash
docker compose --profile demo up --build
```

This starts Agent (`http://localhost:8765/health`), RAG (`http://localhost:8080/v1/health`), EvalOps (`http://localhost:8000/ui/`), two independent workers, and a deterministic demo seed. The seed uploads a local PDF, waits for the durable RAG job, creates baseline/candidate EvalOps runs, evaluates a release gate, and adds a review tag. It requires no LLM credential or paid API.

## Daily use

- Open `http://localhost:8000/ui/` to review runs, compare/gate evidence and bad cases.
- Submit a PDF to `POST http://localhost:8080/v1/ingest`; poll `GET /v1/ingest/{job_id}`. The RAG worker owns execution, so the job survives an API restart.
- Use `http://localhost:8765/docs` for the Agent runtime API. Supply LLM credentials only when submitting a real Agent task; they are not needed for the seeded demo.

## Stop, reset and recover

```bash
docker compose down                 # stop, preserve volumes
docker compose up -d                # restart; RAG/EvalOps state persists
docker compose down -v              # destructive: remove all demo state
```

If an ingestion is stuck in `processing`, restart `rag-worker`; its expired lease becomes claimable. Check `docker compose logs rag-worker rag evalops-worker` before resetting volumes.

## Security boundaries

- Keep API keys in local environment files or your deployment secret store; never commit them.
- The demo workspace is mounted read-only. Use a disposable, explicitly mounted workspace for real Agent code changes.
- The RAG API accepts PDFs only and enforces upload, chunking and storage-quota limits.
