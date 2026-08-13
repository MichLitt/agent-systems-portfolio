#!/usr/bin/env python3
"""Run one G3 arm/seed with per-task process isolation and checkpoints.

The LLM provider can keep an otherwise healthy HTTP stream open indefinitely.
This runner therefore executes each fixed task in a separate Agent process and
enforces an outer wall-clock limit.  A timeout is retained as an ordinary
failure record rather than silently retried or discarded.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "g3-agent-rag-ablation"
AGENT_ROOT = ROOT / "llm-coding-agent-system"
AGENT_PYTHON = AGENT_ROOT / ".venv" / "bin" / "python"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--trial", default="formal-v1", help="Frozen trial identifier; different trials never share checkpoints.")
    parser.add_argument("--agent-preset", default="C3")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "g3-agent-rag-ablation" / "runs")
    parser.add_argument("--task-timeout-seconds", type=int, default=240)
    parser.add_argument("--resume", action="store_true", help="Skip task IDs already recorded in this suite checkpoint.")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def require_rag_service() -> None:
    """Fail candidate execution before any paid model call if RAG is unavailable."""
    base_url = os.environ.get("RAG_API_URL", "").rstrip("/")
    if not base_url:
        raise SystemExit("candidate runs require RAG_API_URL")
    try:
        with urllib.request.urlopen(f"{base_url}/v1/health", timeout=5) as response:
            if response.status != 200:
                raise OSError(f"unexpected status {response.status}")
    except (OSError, urllib.error.URLError) as exc:
        raise SystemExit(f"candidate RAG preflight failed for {base_url}: {exc}") from exc


def main() -> int:
    args = parse_args()
    if args.task_timeout_seconds < 1:
        raise SystemExit("--task-timeout-seconds must be positive")
    if not AGENT_PYTHON.is_file():
        raise SystemExit(f"Agent virtual environment is missing: {AGENT_PYTHON}")
    manifest = load_json(EXPERIMENT / "task-manifest.json")
    config = load_json(EXPERIMENT / "run-config.json")
    tasks = manifest.get("task_ids")
    if not isinstance(tasks, list) or not all(isinstance(task, str) for task in tasks):
        raise SystemExit("invalid frozen task manifest")
    if args.seed not in config.get("seeds", []):
        raise SystemExit(f"seed {args.seed} is not in the frozen run configuration")
    if args.trial != config.get("trial_id"):
        raise SystemExit(f"trial must equal frozen config trial_id: {config.get('trial_id')!r}")
    if args.task_timeout_seconds != config.get("external_task_timeout_seconds"):
        raise SystemExit(
            "task timeout must equal frozen config external_task_timeout_seconds: "
            f"{config.get('external_task_timeout_seconds')!r}"
        )
    if args.arm == "candidate":
        require_rag_service()

    arm_config = config[args.arm]
    run_label = f"g3_{args.trial}_{args.arm}_seed{args.seed}"
    suite_dir = args.output / run_label
    suite_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = suite_dir / "suite.json"
    checkpoint: dict[str, Any] = load_json(checkpoint_path) if checkpoint_path.exists() else {
        "schema_version": "g3-agent-rag-ablation-run/v1",
        "run_label": run_label,
        "arm": args.arm,
        "seed": args.seed,
        "agent_preset": args.agent_preset,
        "task_timeout_seconds": args.task_timeout_seconds,
        "experiment_config": {
            "knowledge_retrieval": arm_config["knowledge_retrieval"],
            "model_seed": args.seed,
            **({"rag_index_id": arm_config["rag_index_id"]} if args.arm == "candidate" else {}),
        },
        "task_results": [],
    }
    completed = {entry["task_id"] for entry in checkpoint["task_results"]}
    if completed and not args.resume:
        raise SystemExit(f"checkpoint exists at {checkpoint_path}; rerun with --resume")
    if checkpoint.get("task_timeout_seconds") != args.task_timeout_seconds:
        raise SystemExit("checkpoint timeout does not match frozen task timeout")
    if checkpoint.get("agent_preset") != args.agent_preset:
        raise SystemExit("checkpoint preset does not match current preset")

    for index, task_id in enumerate(tasks, start=1):
        if task_id in completed:
            print(f"[{index}/{len(tasks)}] {task_id}: already recorded")
            continue
        task_dir = suite_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        task_label = f"{run_label}__{task_id}"
        experiment_config = checkpoint["experiment_config"]
        command = [
            str(AGENT_PYTHON), "-m", "coder_agent", "eval", "--benchmark", "custom",
            "--preset", args.agent_preset, "--config-label", task_label,
            "--llm-profile", str(config["llm_profile"]), "--output", str(task_dir),
            "--task-id", task_id, "--experiment-config", json.dumps(experiment_config, separators=(",", ":")),
        ]
        started = time.monotonic()
        print(f"[{index}/{len(tasks)}] {task_id}: starting")
        try:
            completed_process = subprocess.run(
                command, cwd=AGENT_ROOT, text=True, capture_output=True,
                timeout=args.task_timeout_seconds, check=False,
            )
            duration = time.monotonic() - started
            result_path = task_dir / f"{task_label}.json"
            result: dict[str, Any] = {
                "task_id": task_id,
                "duration_seconds": duration,
                "process_returncode": completed_process.returncode,
                "result_path": str(result_path.relative_to(ROOT)),
                "stdout_path": str((task_dir / "stdout.log").relative_to(ROOT)),
                "stderr_path": str((task_dir / "stderr.log").relative_to(ROOT)),
            }
            (task_dir / "stdout.log").write_text(completed_process.stdout, encoding="utf-8")
            (task_dir / "stderr.log").write_text(completed_process.stderr, encoding="utf-8")
            if result_path.exists():
                raw = json.loads(result_path.read_text(encoding="utf-8"))
                result["agent_result"] = raw[0] if isinstance(raw, list) and raw else raw
            else:
                result["agent_result"] = {"success": False, "termination_reason": "agent_result_missing"}
        except subprocess.TimeoutExpired as exc:
            duration = time.monotonic() - started
            (task_dir / "stdout.log").write_text(exc.stdout or "", encoding="utf-8")
            (task_dir / "stderr.log").write_text(exc.stderr or "", encoding="utf-8")
            result = {
                "task_id": task_id,
                "duration_seconds": duration,
                "process_returncode": None,
                "result_path": None,
                "stdout_path": str((task_dir / "stdout.log").relative_to(ROOT)),
                "stderr_path": str((task_dir / "stderr.log").relative_to(ROOT)),
                "agent_result": {"success": False, "termination_reason": "external_task_timeout"},
            }
        checkpoint["task_results"].append(result)
        write_json(checkpoint_path, checkpoint)
        print(f"[{index}/{len(tasks)}] {task_id}: recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
