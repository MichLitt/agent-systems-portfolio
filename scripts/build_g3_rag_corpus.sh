#!/usr/bin/env bash
set -euo pipefail

root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
manifest="$root_dir/experiments/g3-agent-rag-ablation/rag-corpus-manifest.json"
output_dir="${1:-$root_dir/artifacts/g3-agent-rag-ablation/indexes/g3-agent-rag-ablation-v1}"

python3 "$root_dir/scripts/validate_g3_ablation_protocol.py"
"$root_dir/rag-benchmark-system/.venv/bin/python" \
  "$root_dir/rag-benchmark-system/scripts/build_text_index.py" \
  --manifest "$manifest" \
  --workspace-root "$root_dir" \
  --output-dir "$output_dir" \
  --chunk-size 256 \
  --overlap 32
