#!/usr/bin/env python3
"""Submit the WP1 agent/v1 aggregate reports to EvalOps and compare the arms.

WP1 pre-registration §8. Run after the per-arm reports from
``coder_agent.eval.swebench_evalops`` are archived next to the summary:

    python3 scripts/ingest_wp1_evidence.py

With ``EVALOPS_ENDPOINT`` set to an EvalOps ``/v1`` base URL, the reports go to
that instance (with ``EVALOPS_API_KEY`` as the bearer token). Otherwise the
script starts a temporary EvalOps API and worker on a throwaway database, as
the closure script does.

It compares A-s101 with R (the pre-registered pair) and A-s101 with A-s202
(variation between seeds), and writes the normalized runs and metric deltas
to ``artifacts/evidence/wp1-evalops-compare.json``. It creates no gate: the
pre-registration defines no gate rules. EvalOps compare reports deltas only;
the significance tests are in ``summary.json``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
EVALOPS_ROOT = ROOT / "llm-evalops-platform"
EVIDENCE_DIR = ROOT / "llm-coding-agent-system" / "artifacts" / "wp1-formal"
OUTPUT = ROOT / "artifacts" / "evidence" / "wp1-evalops-compare.json"
ARMS = ("A-s101", "A-s202", "R")
PAIRS = (("A-s101", "R", "pre-registered: A seed 101 against R"), ("A-s101", "A-s202", "seed variation"))


def request(url: str, token: str, payload: dict | None = None) -> tuple[int, dict]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, {"detail": exc.read().decode()[:500]}


def _shown(path: Path) -> str:
    resolved = path.resolve()
    return str(resolved.relative_to(ROOT)) if resolved.is_relative_to(ROOT) else str(path)


def load_reports(evidence_dir: Path) -> dict[str, dict]:
    summary = json.loads((evidence_dir / "summary.json").read_text(encoding="utf-8"))
    task_ids = sorted(summary["per_instance"])
    resolved = {arm["arm"]: arm["resolved_rate"] for arm in summary["arms"]}
    reports = {}
    for arm in ARMS:
        path = evidence_dir / "evalops" / f"{arm}.agent-v1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["task_ids"] != task_ids or payload["resolved_rate"] != resolved[arm]:
            raise SystemExit(f"{path} disagrees with {evidence_dir / 'summary.json'}")
        reports[arm] = {"path": _shown(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "payload": payload}
    return reports


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait(check, what: str, timeout: float = 20) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = check()
        if result is not None:
            return result
        time.sleep(0.2)
    raise SystemExit(f"EvalOps: timed out waiting for {what}")


def submit_and_compare(base: str, token: str, reports: dict[str, dict]) -> dict:
    for arm, report in reports.items():
        status, body = request(f"{base}/ingest/agent/v1", token, report["payload"])
        if status not in (200, 201, 202):
            raise SystemExit(f"EvalOps rejected {arm}: {status} {body}")
        report["ingest"] = body
    runs = {}
    for arm, report in reports.items():
        url = f"{base}/runs/agent/{report['payload']['run_id']}"
        runs[arm] = _wait(lambda url=url: (lambda r: r[1] if r[0] == 200 else None)(request(url, token)),
                          f"normalized run {arm}")["run"]
    compares = []
    for baseline, candidate, purpose in PAIRS:
        status, body = request(f"{base}/compare", token, {
            "app_type": "agent", "baseline_run_id": reports[baseline]["payload"]["run_id"],
            "candidate_run_id": reports[candidate]["payload"]["run_id"],
        })
        if status != 201:
            raise SystemExit(f"EvalOps compare {baseline} vs {candidate} failed: {status} {body}")
        compares.append({"baseline": baseline, "candidate": candidate, "purpose": purpose, **body})
    return {"runs": runs, "compares": compares}


def with_temporary_evalops(reports: dict[str, dict]) -> dict:
    python = str(EVALOPS_ROOT / ".venv/bin/python")
    token = "wp1-ingest-token"
    port = _free_port()
    with tempfile.TemporaryDirectory(prefix="wp1-evalops-") as tmp:
        env = {**os.environ, "PYTHONPATH": str(EVALOPS_ROOT / "src"), "DATABASE_URL": str(Path(tmp) / "evalops.db"),
               "API_HOST": "127.0.0.1", "API_PORT": str(port), "WORKER_POLL_INTERVAL_SECS": "1",
               "EVALOPS_API_TOKEN": token}
        processes = [
            subprocess.Popen([python, str(EVALOPS_ROOT / f"scripts/start_{name}.py")], cwd=EVALOPS_ROOT, env=env,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for name in ("api", "worker")
        ]
        try:
            base = f"http://127.0.0.1:{port}"

            def healthy():
                if processes[0].poll() is not None:
                    raise SystemExit(f"EvalOps API exited with code {processes[0].returncode}")
                try:
                    status, body = request(f"{base}/health", token)
                except OSError:  # not listening yet
                    return None
                return body if status == 200 else None

            _wait(healthy, "the temporary EvalOps API")
            return submit_and_compare(f"{base}/v1", token, reports)
        finally:
            for process in processes:
                process.terminate()
            for process in processes:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--evidence-dir", type=Path, default=EVIDENCE_DIR)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    reports = load_reports(args.evidence_dir)
    endpoint = os.environ.get("EVALOPS_ENDPOINT", "").rstrip("/")
    if endpoint:
        result = submit_and_compare(endpoint, os.environ.get("EVALOPS_API_KEY", ""), reports)
    else:
        result = with_temporary_evalops(reports)
    commit = subprocess.run(["git", "-C", str(EVALOPS_ROOT), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    evidence = {
        "schema_version": "wp1-evalops/v1",
        "evalops_instance": "external" if endpoint else "temporary",
        "evalops_commit": commit,
        "gate": "none: the pre-registration defines no gate rules",
        "reports": {arm: {"path": r["path"], "sha256": r["sha256"], "run_id": r["payload"]["run_id"],
                          "ingest": r["ingest"]} for arm, r in reports.items()},
        **result,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for compare in result["compares"]:
        delta = next(d["absolute_delta"] for d in compare["deltas"] if d["metric_name"] == "resolved_rate")
        print(f"{compare['purpose']}: resolved_rate {compare['candidate']} - {compare['baseline']} = {delta:+.2f}")
    print(f"wrote {_shown(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
