#!/usr/bin/env python3
"""Start a G3 suite detached from the invoking terminal session.

The suite runner owns its own process group, writes stdout/stderr to the
ignored suite directory, and can therefore survive an interactive terminal or
tool-call lifecycle ending.  It refuses to start if the suite is already live.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / "experiments/g3-agent-rag-ablation/run-config.json").read_text())
    trial = config["trial_id"]
    suite_dir = ROOT / "artifacts/g3-agent-rag-ablation/runs" / f"g3_{trial}_{args.arm}_seed{args.seed}"
    suite_dir.mkdir(parents=True, exist_ok=True)
    pid_path = suite_dir / "runner.pid"
    if pid_path.exists():
        try:
            pid = int(pid_path.read_text().strip())
            os.kill(pid, 0)
        except (OSError, ValueError):
            pid_path.unlink(missing_ok=True)
        else:
            raise SystemExit(f"suite runner is already live (pid={pid})")
    command = [
        sys.executable, str(ROOT / "scripts/run_g3_ablation.py"),
        "--arm", args.arm, "--seed", str(args.seed), "--resume",
    ]
    log = (suite_dir / "runner.log").open("a", encoding="utf-8")
    process = subprocess.Popen(
        command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    pid_path.write_text(f"{process.pid}\n", encoding="utf-8")
    (suite_dir / "runner-start.json").write_text(json.dumps({
        "pid": process.pid, "trial_id": trial, "arm": args.arm,
        "seed": args.seed, "started_at": time.time(), "command": command,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Started detached G3 runner pid={process.pid} suite={suite_dir.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
