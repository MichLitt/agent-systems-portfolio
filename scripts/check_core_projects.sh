#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

run_suite() {
  local project="$1"
  local python="${WORKSPACE_ROOT}/${project}/.venv/bin/python"
  if [[ ! -x "${python}" ]]; then
    echo "ERROR: ${project} environment is missing; run 'uv sync' in that project." >&2
    return 1
  fi

  echo "==> ${project}"
  (
    cd "${WORKSPACE_ROOT}/${project}"
    PYTHONDONTWRITEBYTECODE=1 "${python}" -m pytest -q -p no:cacheprovider
  )
}

run_suite "llm-coding-agent-system"
run_suite "llm-evalops-platform"
run_suite "rag-benchmark-system"
