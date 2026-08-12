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

For a real run, an authorized operator must provide the selected LLM profile credential, start the RAG service with the built fixed corpus, and retain the raw results. Use the task IDs from the manifest as repeated `--task-id` arguments with `coder_agent.cli.eval`, once per condition and seed. The baseline must pass `--experiment-config '{"knowledge_retrieval": false, "model_seed": 101}'`; the candidate must pass `--experiment-config '{"knowledge_retrieval": true, "rag_index_id": "g3-agent-rag-ablation-v1", "model_seed": 101}'` with `RAG_API_URL` and `RAG_API_TOKEN` configured. The fixed-index policy overrides any index identifier supplied by the model. Repeat for all three frozen seed values.

Before publishing, export raw run identifiers and recomputed metrics to `artifacts/evidence/agent-rag-ablation-latest.json`, write `docs/reports/agent-rag-ablation-v1.md`, create the EvalOps comparison and gate, then run `make require-evidence`. A rejected or neutral result remains valid evidence and must be recorded as such; it cannot be presented as an improvement.
