#!/usr/bin/env python3
"""Validate the managed workspace documentation layout and relative links."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = [
    "llm-coding-agent-system",
    "rag-benchmark-system",
    "llm-evalops-platform",
    "coding-llm-finetune",
]
LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def managed_markdown() -> list[Path]:
    paths = [ROOT / "README.md", ROOT / "AGENTS.md"]
    paths.extend(sorted((ROOT / "docs").rglob("*.md")))
    for project in PROJECTS:
        for name in ("README.md", "AGENTS.md", "CLAUDE.md"):
            paths.append(ROOT / project / name)
    return paths


def main() -> int:
    errors: list[str] = []
    required_engineering_docs = (
        ROOT / "docs" / "engineering" / "AGENT_ENGINEERING_STANDARD.md",
        ROOT / "docs" / "engineering" / "ENGINEERING_GUIDE.md",
        ROOT / "docs" / "plans" / "competitive-portfolio-delivery-plan.md",
    )
    for required in required_engineering_docs:
        if not required.is_file():
            errors.append(f"missing required engineering document: {required.relative_to(ROOT)}")

    root_markdown = {path.name for path in ROOT.glob("*.md")}
    expected_root = {"README.md", "AGENTS.md"}
    if root_markdown != expected_root:
        errors.append(
            f"root Markdown must be {sorted(expected_root)}, got {sorted(root_markdown)}"
        )

    for project in PROJECTS:
        agents = ROOT / project / "AGENTS.md"
        claude = ROOT / project / "CLAUDE.md"
        if not agents.is_file():
            errors.append(f"missing {agents.relative_to(ROOT)}")
        if not claude.is_file() or "AGENTS.md" not in claude.read_text(encoding="utf-8"):
            errors.append(f"{claude.relative_to(ROOT)} must point to AGENTS.md")

    obsolete = (
        "THREE_PROJECT_CLOSURE_PLAN.md",
        "AI_Intern_Project_Roadmap.md",
        "closure/three_project_closure_latest.json",
        "Projects/Toys",
    )

    for document in managed_markdown():
        if not document.is_file():
            errors.append(f"missing managed document: {document.relative_to(ROOT)}")
            continue
        text = document.read_text(encoding="utf-8")
        if text.count("```") % 2:
            errors.append(f"unbalanced code fences: {document.relative_to(ROOT)}")
        for token in obsolete:
            if token in text:
                errors.append(f"obsolete path {token!r}: {document.relative_to(ROOT)}")
        for raw_target in LINK_RE.findall(text):
            target = raw_target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path = unquote(target.split("#", 1)[0])
            if not target_path:
                continue
            resolved = (document.parent / target_path).resolve()
            if not resolved.exists():
                errors.append(
                    f"broken link {target!r}: {document.relative_to(ROOT)}"
                )

    if errors:
        print("Documentation check failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Documentation check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
