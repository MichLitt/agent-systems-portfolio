#!/usr/bin/env python3
"""Validate the immutable inputs for the G3 Agent–RAG comparison."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "g3-agent-rag-ablation"

def fail(message: str) -> None:
    print(f"G3 protocol: BLOCKED — {message}")
    raise SystemExit(1)


def git_head(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=path,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None

def read_json(name: str) -> tuple[Path, dict]:
    path = EXPERIMENT / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")
    if not isinstance(value, dict):
        fail(f"{path.relative_to(ROOT)} must contain a JSON object")
    return path, value

def main() -> None:
    manifest_path, manifest = read_json("task-manifest.json")
    corpus_path, corpus = read_json("rag-corpus-manifest.json")
    _, config = read_json("run-config.json")
    task_ids = manifest.get("task_ids")
    if not isinstance(task_ids, list) or not 20 <= len(task_ids) <= 30:
        fail("task manifest must contain 20–30 task IDs")
    if any(not isinstance(task_id, str) or not task_id for task_id in task_ids) or len(task_ids) != len(set(task_ids)):
        fail("task IDs must be unique, non-empty strings")
    source = manifest.get("source", {})
    commit = source.get("commit") if isinstance(source, dict) else None
    if not isinstance(commit, str) or len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
        fail("task source commit must be a 40-character lowercase SHA")
    expected_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    if config.get("task_manifest_sha256") != expected_hash:
        fail("run config task manifest hash does not match the frozen manifest")
    expected_corpus_hash = hashlib.sha256(corpus_path.read_bytes()).hexdigest()
    if config.get("rag_corpus_manifest_sha256") != expected_corpus_hash:
        fail("run config corpus manifest hash does not match the frozen corpus")
    runtime_commit = config.get("agent_runtime_commit")
    if (
        not isinstance(runtime_commit, str)
        or len(runtime_commit) != 40
        or any(c not in "0123456789abcdef" for c in runtime_commit)
    ):
        fail("Agent runtime commit must be a 40-character lowercase SHA")
    agent_root = ROOT / "llm-coding-agent-system"
    resolved = git_head(agent_root)
    if resolved is None:
        fail("cannot resolve the Agent runtime commit")
    if resolved != runtime_commit:
        fail("Agent checkout does not match the frozen runtime commit")
    trial_id = config.get("trial_id")
    if not isinstance(trial_id, str) or not trial_id.strip():
        fail("a non-empty formal trial_id is required")
    external_timeout = config.get("external_task_timeout_seconds")
    if not isinstance(external_timeout, int) or not 1 <= external_timeout <= 240:
        fail("external task timeout must be an integer between 1 and 240 seconds")
    seeds = config.get("seeds")
    if not isinstance(seeds, list) or len(seeds) != 3 or len(set(seeds)) != 3:
        fail("exactly three distinct seeds are required")
    baseline, candidate = config.get("baseline"), config.get("candidate")
    if not isinstance(baseline, dict) or baseline.get("knowledge_retrieval") is not False:
        fail("baseline must explicitly disable knowledge retrieval")
    if not isinstance(candidate, dict) or candidate.get("knowledge_retrieval") is not True:
        fail("candidate must explicitly enable knowledge retrieval")
    if candidate.get("index_name") != corpus.get("index_name"):
        fail("candidate index must match the frozen corpus manifest")
    if candidate.get("rag_index_id") != corpus.get("index_name"):
        fail("candidate fixed RAG index must match the frozen corpus manifest")
    documents = corpus.get("documents")
    if not isinstance(documents, list) or not documents:
        fail("RAG corpus must name at least one document")
    prohibited = ("task", "test", "trajectory", "result", "artifact", "patch")
    if any(any(token in str(doc).lower() for token in prohibited) for doc in documents):
        fail("RAG corpus manifest contains a potentially task-leaking document")
    for document in documents:
        path = (ROOT / str(document)).resolve()
        if ROOT not in path.parents or not path.is_file():
            fail(f"RAG corpus document is missing or outside the workspace: {document}")
    builder = corpus.get("builder")
    if not isinstance(builder, dict):
        fail("RAG corpus builder metadata is required")
    if builder.get("repository") != "rag-benchmark-system":
        fail("RAG corpus builder must name rag-benchmark-system")
    if builder.get("commit") != git_head(ROOT / "rag-benchmark-system"):
        fail("RAG checkout does not match the frozen corpus builder commit")
    print(f"G3 protocol: READY — {len(task_ids)} tasks, {len(seeds)} seeds, manifest sha256={expected_hash}")

if __name__ == "__main__":
    main()
