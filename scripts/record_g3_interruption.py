#!/usr/bin/env python3
"""Record a host-interrupted G3 task before resuming its suite.

This is intentionally explicit rather than automatic: it is for a runner that
was terminated by its host before it could persist the normal timeout record.
The task is retained as an unsuccessful observation, never silently rerun.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--duration-seconds", type=float, required=True)
    args = parser.parse_args()
    suite_path = ROOT / "artifacts" / "g3-agent-rag-ablation" / "runs" / f"g3_{args.arm}_seed{args.seed}" / "suite.json"
    suite = json.loads(suite_path.read_text(encoding="utf-8"))
    results = suite["task_results"]
    if any(item.get("task_id") == args.task_id for item in results):
        raise SystemExit(f"task is already recorded: {args.task_id}")
    results.append({
        "task_id": args.task_id,
        "duration_seconds": args.duration_seconds,
        "process_returncode": None,
        "result_path": None,
        "stdout_path": None,
        "stderr_path": None,
        "agent_result": {
            "success": False,
            "benchmark_passed": False,
            "termination_reason": "external_host_timeout",
            "error_types": ["external_host_timeout"],
        },
        "note": "Host terminated the isolated runner before it could persist a normal task result.",
    })
    temporary = suite_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(suite_path)
    print(f"Recorded {args.task_id} as external_host_timeout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
