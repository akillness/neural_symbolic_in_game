#!/usr/bin/env bash
# Run the exact .github/workflows/validate.yml sequence locally.
#
# The CI job lints and tests a wider surface than any single project script:
# ruff covers src, tests, scripts, and examples, and nine other gates run after
# it. Running only ./scripts/validate_game_track.sh before a push therefore
# passes locally and still fails CI. Use this script instead, or install it as a
# pre-push hook with --install-hook.
#
# Usage:
#   ./scripts/verify_like_ci.sh                 # run every CI step in order
#   ./scripts/verify_like_ci.sh --install-hook  # install as .git/hooks/pre-push
set -uo pipefail

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ "${1:-}" = "--install-hook" ]; then
  HOOK="$REPO_ROOT/.git/hooks/pre-push"
  RELATIVE="${PROJECT_DIR#"$REPO_ROOT"/}"
  cat > "$HOOK" <<HOOK_BODY
#!/usr/bin/env bash
# Installed by scripts/verify_like_ci.sh --install-hook
exec "\$(git rev-parse --show-toplevel)/$RELATIVE/scripts/verify_like_ci.sh"
HOOK_BODY
  chmod +x "$HOOK"
  echo "installed pre-push hook: $HOOK"
  exit 0
fi

FAILED=()

step() {
  local label="$1"
  shift
  printf '\n=== %s ===\n' "$label"
  if "$@"; then
    printf 'PASS %s\n' "$label"
  else
    printf 'FAIL %s\n' "$label"
    FAILED+=("$label")
  fi
}

visuals_are_current() {
  uv run python scripts/generate_readme_visuals.py || return 1
  if [ -n "$(git status --porcelain -- visuals)" ]; then
    echo "README visuals are stale; commit the regenerated visuals/."
    git status --porcelain -- visuals
    return 1
  fi
}

ruff_gate() {
  uv run ruff check src tests scripts examples || return 1
  uv run ruff format --check src tests scripts examples || return 1
}

step "Install locked environment" uv sync --extra research --extra dev
step "Unit tests" uv run python -m unittest discover -s tests
step "Ruff lint and format" ruff_gate
step "Project integrity" uv run python scripts/validate_project.py
step "README visuals match their sources" visuals_are_current
step "Offline experiment smoke" uv run python examples/recorded_experiment.py
step "Harness structure" uv run python scripts/validate_harness.py
step "Experimental game-track contracts" ./scripts/validate_game_track.sh
step "Deep-research result contracts" uv run python scripts/validate_deep_research.py \
  --fields research/deep-research/fields.yaml --dir research/deep-research/results --quiet
step "Survey artifact contract" uv run python scripts/validate_survey_artifacts.py \
  ../.survey/neuro-symbolic-interactive-game-2026 --require-provenance
step "Wiki lint" uv run python scripts/lint_wiki.py ../llm-wiki

printf '\n'
if [ ${#FAILED[@]} -eq 0 ]; then
  echo "All CI steps passed locally; this tree should push clean."
  exit 0
fi
printf 'CI-equivalent failures (%d):\n' "${#FAILED[@]}"
printf '  - %s\n' "${FAILED[@]}"
exit 1
