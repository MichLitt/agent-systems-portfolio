#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECTS=(
  "llm-coding-agent-system"
  "llm-evalops-platform"
  "rag-benchmark-system"
  "coding-llm-finetune"
)

if ! command -v uv >/dev/null 2>&1; then
  echo "ERROR: uv is required to refresh project environments." >&2
  exit 1
fi

for project in "${PROJECTS[@]}"; do
  echo "==> refreshing ${project}"
  (
    cd "${WORKSPACE_ROOT}/${project}"
    # A plain `uv sync` updates editable packages but leaves dependency console
    # scripts with shebangs pointing at the old absolute workspace path.
    UV_CACHE_DIR="${WORKSPACE_ROOT}/${project}/.uv-cache" uv venv --clear .venv
    UV_CACHE_DIR="${WORKSPACE_ROOT}/${project}/.uv-cache" uv sync
  )
done

# Repair Git's absolute paths for linked worktrees stored inside the Agent
# repository. External Codex worktrees are outside this workspace and do not
# move with it.
AGENT_REPO="${WORKSPACE_ROOT}/llm-coding-agent-system"
AGENT_WORKTREE_ROOT="${AGENT_REPO}/.claude/worktrees"
if [[ -d "${AGENT_WORKTREE_ROOT}" ]]; then
  AGENT_WORKTREES=()
  while IFS= read -r worktree; do
    AGENT_WORKTREES+=("${worktree}")
  done < <(find "${AGENT_WORKTREE_ROOT}" -mindepth 1 -maxdepth 1 -type d | sort)

  if (( ${#AGENT_WORKTREES[@]} > 0 )); then
    echo "==> repairing ${#AGENT_WORKTREES[@]} linked Agent worktrees"
    git -C "${AGENT_REPO}" worktree repair "${AGENT_WORKTREES[@]}"

    for worktree in "${AGENT_WORKTREES[@]}"; do
      if [[ -d "${worktree}/.venv" && -f "${worktree}/pyproject.toml" ]]; then
        echo "==> refreshing linked worktree $(basename "${worktree}")"
        (
          cd "${worktree}"
          UV_CACHE_DIR="${worktree}/.uv-cache" uv venv --clear .venv
          UV_CACHE_DIR="${worktree}/.uv-cache" uv sync
        )
      fi
    done
  fi
fi

echo "Workspace environments refreshed at ${WORKSPACE_ROOT}."
