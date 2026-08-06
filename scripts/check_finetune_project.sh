#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_ROOT="${WORKSPACE_ROOT}/coding-llm-finetune"
PYTHON="${PROJECT_ROOT}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
  echo "ERROR: coding-llm-finetune environment is missing; run 'make refresh'." >&2
  exit 1
fi

scripts=(
  "scripts/prepare_sft_data.py"
  "scripts/check_contamination.py"
  "scripts/sft_train.py"
  "scripts/generate_dpo_pairs.py"
  "scripts/dpo_train.py"
)

for script in "${scripts[@]}"; do
  echo "==> coding-llm-finetune/${script} --help"
  (
    cd "${PROJECT_ROOT}"
    PYTHONDONTWRITEBYTECODE=1 "${PYTHON}" "${script}" --help >/dev/null
  )
done

echo "FINETUNE_CLI_SMOKE=passed"
