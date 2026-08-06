#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

exec "${WORKSPACE_ROOT}/rag-benchmark-system/.venv/bin/python" \
  "${SCRIPT_DIR}/run_three_project_closure.py" "$@"
