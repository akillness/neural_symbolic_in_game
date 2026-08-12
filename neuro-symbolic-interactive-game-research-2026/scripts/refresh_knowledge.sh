#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
wiki_root="$(cd "${project_root}/../llm-wiki" && pwd)"

python3 "${project_root}/scripts/lint_wiki.py" "${wiki_root}"

help_text="$(graphify --help 2>&1 || true)"
if [[ "${help_text}" != *"cluster-only"* || "${help_text}" != *"update"* ]]; then
  echo "Unsupported Graphify command surface; authoritative graph left unchanged." >&2
  exit 2
fi

(
  cd "${wiki_root}"
  graphify update .
  graphify cluster-only . --graph graphify-out/graph.json --no-viz
  if [[ -f graphify-out/GRAPH_REPORT.md ]]; then
    mv graphify-out/GRAPH_REPORT.md graphify-out/GRAPH_REPORT.generated.txt
  fi
  graphify query "TRACE-RPG symbolic commit game validity" \
    --graph graphify-out/graph.json --budget 700
)
