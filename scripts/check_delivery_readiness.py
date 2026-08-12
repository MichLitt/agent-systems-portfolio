#!/usr/bin/env python3
"""Assess machine-verifiable portfolio delivery Gates.

The default command is informational and exits successfully. ``--require``
turns a Gate into a strict CI/release check. Manual criteria remain defined in
the competitive delivery plan.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = (
    "llm-coding-agent-system",
    "rag-benchmark-system",
    "llm-evalops-platform",
    "coding-llm-finetune",
)


@dataclass
class GateResult:
    name: str
    failures: list[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.failures


def _run_git(args: list[str], cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _load_json(path: Path, failures: list[str]) -> dict:
    if not path.is_file():
        failures.append(f"missing {path.relative_to(ROOT)}")
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(data, dict):
        failures.append(f"{path.relative_to(ROOT)} must contain a JSON object")
        return {}
    return data


def _require_truthy(data: dict, keys: tuple[str, ...], label: str, failures: list[str]) -> None:
    if not data:
        return
    for key in keys:
        if not data.get(key):
            failures.append(f"{label} field {key!r} is missing or false")


def check_engineering() -> GateResult:
    result = GateResult("engineering")
    required = (
        ROOT / "README.md",
        ROOT / "AGENTS.md",
        ROOT / ".gitmodules",
        ROOT / "docs" / "engineering" / "AGENT_ENGINEERING_STANDARD.md",
        ROOT / "docs" / "engineering" / "ENGINEERING_GUIDE.md",
        ROOT / "docs" / "plans" / "competitive-portfolio-delivery-plan.md",
    )
    for path in required:
        if not path.is_file():
            result.failures.append(f"missing {path.relative_to(ROOT)}")

    for project in PROJECTS:
        project_root = ROOT / project
        if not project_root.is_dir() or not (project_root / ".git").exists():
            result.failures.append(f"Submodule not initialized: {project}")
        if not (project_root / "AGENTS.md").is_file():
            result.failures.append(f"missing {project}/AGENTS.md")

    closure_path = ROOT / "artifacts" / "closure" / "three-project-closure-latest.json"
    closure = _load_json(closure_path, result.failures)
    _require_truthy(
        closure,
        ("rag_ingest", "agent_retrieval", "three_project_closure"),
        closure_path.relative_to(ROOT).as_posix(),
        result.failures,
    )
    if closure and closure.get("rag_evalops_gate") != "promoted":
        result.failures.append("RAG EvalOps gate is not promoted")
    if closure and closure.get("agent_evalops_gate") != "promoted":
        result.failures.append("Agent EvalOps gate is not promoted")
    return result


def _workflow_exists(root: Path) -> bool:
    workflows = root / ".github" / "workflows"
    return workflows.is_dir() and any(
        path.suffix in {".yml", ".yaml"} for path in workflows.iterdir() if path.is_file()
    )


def check_release() -> GateResult:
    result = GateResult("release")
    engineering = check_engineering()
    if not engineering.ready:
        result.failures.append("dependency engineering is not ready")

    for repo_root, label in ((ROOT, "portfolio"), *[(ROOT / p, p) for p in PROJECTS]):
        if not _workflow_exists(repo_root):
            result.failures.append(f"missing CI workflow: {label}")

    for project in PROJECTS:
        project_root = ROOT / project
        head = _run_git(["rev-parse", "HEAD"], project_root)
        remote_main = _run_git(["rev-parse", "refs/remotes/origin/main"], project_root)
        if not head or not remote_main:
            result.failures.append(f"cannot resolve HEAD/origin/main: {project}")
        elif head != remote_main:
            result.failures.append(f"Submodule HEAD is not origin/main: {project}")

    tags = (_run_git(["tag", "--points-at", "HEAD"], ROOT) or "").splitlines()
    if not any(re.fullmatch(r"v\d+\.\d+\.\d+", tag) for tag in tags):
        result.failures.append("portfolio HEAD has no semantic release tag")
    if not (ROOT / "docs" / "releases" / "v0.1.0.md").is_file():
        result.failures.append("missing docs/releases/v0.1.0.md")
    return result


def check_demo() -> GateResult:
    result = GateResult("demo")
    release = check_release()
    if not release.ready:
        result.failures.append("dependency release is not ready")

    if not any((ROOT / name).is_file() for name in ("compose.yaml", "compose.yml", "docker-compose.yml")):
        result.failures.append("missing root Compose file")
    runbook = ROOT / "docs" / "engineering" / "OPERATIONS_RUNBOOK.md"
    if not runbook.is_file():
        result.failures.append("missing docs/engineering/OPERATIONS_RUNBOOK.md")
    demo_path = ROOT / "artifacts" / "delivery" / "demo-readiness.json"
    demo = _load_json(demo_path, result.failures)
    _require_truthy(
        demo,
        (
            "one_command_start",
            "seeded_workflow",
            "restart_recovery",
            "review_loop",
            "security_smoke",
            "passed",
        ),
        demo_path.relative_to(ROOT).as_posix(),
        result.failures,
    )
    return result


def check_evidence() -> GateResult:
    result = GateResult("evidence")
    demo = check_demo()
    if not demo.ready:
        result.failures.append("dependency demo is not ready")

    evidence_path = ROOT / "artifacts" / "evidence" / "agent-rag-ablation-latest.json"
    evidence = _load_json(evidence_path, result.failures)
    _require_truthy(
        evidence,
        (
            "task_count",
            "seed_count",
            "baseline_run_ids",
            "candidate_run_ids",
            "metrics",
            "passed",
        ),
        evidence_path.relative_to(ROOT).as_posix(),
        result.failures,
    )
    if evidence and evidence.get("gate_decision") != "promoted":
        result.failures.append("agent/RAG evidence gate is not promoted")
    if not (ROOT / "docs" / "reports" / "agent-rag-ablation-v1.md").is_file():
        result.failures.append("missing docs/reports/agent-rag-ablation-v1.md")
    return result


CHECKS: dict[str, Callable[[], GateResult]] = {
    "engineering": check_engineering,
    "release": check_release,
    "demo": check_demo,
    "evidence": check_evidence,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require",
        choices=tuple(CHECKS),
        help="Exit non-zero unless this Gate's machine-verifiable checks pass.",
    )
    args = parser.parse_args()

    results = [check() for check in CHECKS.values()]
    for result in results:
        status = "READY" if result.ready else "BLOCKED"
        print(f"{result.name.upper()}_READINESS={status}")
        for failure in result.failures:
            print(f"  - {failure}")

    if args.require:
        selected = next(result for result in results if result.name == args.require)
        return 0 if selected.ready else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
