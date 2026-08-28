#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
wiki_root="$(cd "${project_root}/../llm-wiki" && pwd)"

python3 "${project_root}/scripts/lint_wiki.py" "${wiki_root}"

# Some sandboxes deny os.sysconf("SC_SEM_NSEMS_MAX"), which Python's
# ProcessPoolExecutor probes before it will start. Graphify's AST extraction
# defaults to a process pool, so the rebuild dies with
# "[graphify watch] Rebuild failed: [Errno 1] Operation not permitted" even
# though the output directory is perfectly writable. GRAPHIFY_MAX_WORKERS=1 is
# graphify's own supported single-worker path (it returns before constructing
# the pool and extracts sequentially in-process), so probe once and set it only
# when the pool is genuinely unavailable. On a normal machine this changes
# nothing and parallel extraction is kept.
if ! python3 - <<'PROBE' >/dev/null 2>&1
import concurrent.futures.process as p
p._check_system_limits()
PROBE
then
  echo "Process pools are unavailable in this environment; using GRAPHIFY_MAX_WORKERS=1 (sequential extraction)." >&2
  export GRAPHIFY_MAX_WORKERS=1
fi

help_text="$(graphify --help 2>&1 || true)"
if [[ "${help_text}" != *"cluster-only"* || "${help_text}" != *"update"* ]]; then
  echo "Unsupported Graphify command surface; authoritative graph left unchanged." >&2
  exit 2
fi

(
  cd "${wiki_root}"
  graphify update .
  graphify cluster-only . --graph graphify-out/graph.json --no-viz
  # The generated report carries unresolved Obsidian community links that the
  # wiki linter correctly flags, so it must not stay as .md inside the vault.
  # `graphify cluster-only` also writes a dated backup of the previous curated
  # graph (graphify-out/YYYY-MM-DD/), which reintroduces a GRAPH_REPORT.md, so
  # apply the same rename to every copy rather than just the top-level one.
  while IFS= read -r report; do
    mv "${report}" "${report%.md}.generated.txt"
  done < <(find graphify-out -name 'GRAPH_REPORT.md' -type f)
  graphify query "TRACE-RPG symbolic commit game validity" \
    --graph graphify-out/graph.json --budget 700
)
