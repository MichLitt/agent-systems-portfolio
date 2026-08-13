# G3 Agent–RAG controlled ablation

This directory freezes the design of the G3 evidence experiment. It intentionally contains **no outcome data**. A result is publishable only after all baseline and candidate runs have completed, been retained, and passed an EvalOps gate.

## Controlled comparison

- The fixed task set is the 20-task manifest in `task-manifest.json`.
- Each condition runs every task for the same three seeds, passing each value as
  `model_seed` to the `glm_5` OpenAI-compatible completion request.
- The model profile, temperature, terminal timeout, verification commands,
  `agent_runtime_commit`, and RAG corpus remain fixed. Each task's step budget
  is its `max_steps` from the pinned `tasks.yaml` source (at most 20 steps in
  this selected set), rather than a new uniform override.
- `baseline_no_retrieval` forces the Agent not to register `knowledge_retrieval`, even while the RAG service is available for the candidate.
- `candidate_rag` registers the same tool set plus `knowledge_retrieval` against the named, task-independent index.

The experiment is invalid if the candidate corpus includes task prompts, test fixtures, patches, previous trajectories, or result artifacts.

## Preflight and execution

Run the static preflight first:

```bash
make check-ablation-protocol
```

Then build the fixed corpus; this writes ignored runtime artifacts and a
machine-readable source/digest record under `artifacts/g3-agent-rag-ablation/`:

```bash
make build-g3-corpus
```

For a real run, an authorized operator must provide the selected LLM profile credential, start the RAG service with the built fixed corpus, and retain the raw results. Use the isolated runner once per condition and seed:

```bash
make run-g3-ablation ARM=baseline SEED=101
make run-g3-ablation ARM=candidate SEED=101
```

The runner creates one Agent process per task and records a suite checkpoint after every task. Its three-minute outer task limit is frozen in `run-config.json` and independent of SDK streaming behavior: a timeout is recorded as `external_task_timeout`, not retried or discarded. Start formal suites with `make start-g3-ablation ARM=baseline SEED=101`; it detaches the runner into its own process group and retains its local log/PID metadata so an interactive tool session ending cannot truncate a task before checkpointing. A formal trial ID is also frozen; it creates separate checkpoint paths and prevents an exploratory run with altered conditions from being mixed into publishable evidence. If the host itself terminates the runner before it can persist that record, use `scripts/record_g3_interruption.py` to retain an `external_host_timeout` observation before resuming; it must not be silently rerun. Candidate runs require `RAG_API_URL` and `RAG_API_TOKEN`; the runner verifies `RAG_API_URL/v1/health` before making a model call. The fixed-index policy overrides any index identifier supplied by the model. Repeat for all three frozen seed values.

Raw per-task trajectories, logs, and suite checkpoints are retained locally under `artifacts/g3-agent-rag-ablation/runs/` and intentionally ignored by Git. The final committed evidence artifact records their identifiers, source hashes, aggregate metrics, and gate result without publishing arbitrary model output.

## Formal-run environment requirement

The formal `trial_id` must execute on an environment that preserves the suite
process through every task checkpoint (for example, a self-hosted CI runner or
a dedicated machine/session manager). Interactive desktop tool sessions may
reap detached child processes; such an interruption invalidates the affected
trial rather than authorizing a selective rerun. Record the interruption, mint
a new frozen trial ID, and restart both arms for all three seeds on a stable
executor. The evidence builder intentionally refuses incomplete trials.

Before publishing, export raw run identifiers and recomputed metrics to `artifacts/evidence/agent-rag-ablation-latest.json`, write `docs/reports/agent-rag-ablation-v1.md`, create the EvalOps comparison and gate, then run `make require-evidence`. A rejected or neutral result remains valid evidence and must be recorded as such; it cannot be presented as an improvement.
