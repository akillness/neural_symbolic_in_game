#!/usr/bin/env bash
# Run the exact .github/workflows/validate.yml sequence locally.
#
# The CI job lints and tests a wider surface than any single project script:
# ruff covers src, tests, scripts, and examples, and the remaining repository
# gates run after it. Running only ./scripts/validate_game_track.sh before a push therefore
# passes locally and still fails CI. Use this script instead, or install it as a
# pre-push hook with --install-hook.
#
# Usage:
#   ./scripts/verify_like_ci.sh                 # run every CI step in order
#   ./scripts/verify_like_ci.sh --install-hook  # install as .git/hooks/pre-push
# Explicit hosted SDK contract mode (native Aside stays the default):
#   NSG_BROWSER_BACKEND=aside NSG_ASIDE_TEST_TRANSPORT=playwright ./scripts/verify_like_ci.sh
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

ruff_gate() {
  uv run ruff check src tests scripts examples || return 1
  uv run ruff format --check src tests scripts examples || return 1
}

verify_contract_browser_runtime() {
  if ! command -v node >/dev/null 2>&1; then
    echo "Node is required for the explicit Playwright contract transport" >&2
    return 1
  fi
  if [ -z "${NODE_PATH:-}" ] || [ -z "${PLAYWRIGHT_BROWSERS_PATH:-}" ]; then
    echo "Set NODE_PATH and PLAYWRIGHT_BROWSERS_PATH to the preprovisioned pinned runtime" >&2
    return 1
  fi
  node <<'NODE'
const fs = require('node:fs');
const path = require('node:path');

async function verify() {
  const locations = process.env.NODE_PATH.split(path.delimiter);
  if (!locations.every(location => location && fs.statSync(location).isDirectory()) ||
      !fs.statSync(process.env.PLAYWRIGHT_BROWSERS_PATH).isDirectory())
    throw new Error('Configured runtime locations must be directories');
  const packagePath = require.resolve('playwright/package.json');
  if (!locations.some(location => {
    const candidate = path.join(location, 'playwright/package.json');
    return fs.existsSync(candidate) && fs.realpathSync(candidate) === packagePath;
  }))
    throw new Error('Playwright must resolve from the configured NODE_PATH');
  if (require('playwright/package.json').version !== '1.65.0')
    throw new Error('Playwright 1.65.0 is required');
  const { chromium } = require('playwright');
  if (process.env.PLAYWRIGHT_EXECUTABLE_PATH &&
      path.resolve(process.env.PLAYWRIGHT_EXECUTABLE_PATH) !== path.resolve(chromium.executablePath()))
    throw new Error('A browser override cannot replace pinned Chromium');
  const browser = await chromium.launch({ headless: true });
  await browser.close();
  console.log('Pinned Playwright 1.65.0 Chromium launch/close verified');
}
verify().catch(() => {
  console.error('Pinned contract runtime unavailable or incompatible; provision Playwright 1.65.0 and its Chromium before verification');
  process.exitCode = 1;
});
NODE
}

step "Install locked environment" uv sync --extra research --extra dev
if [ "${NSG_ASIDE_TEST_TRANSPORT:-}" = "playwright" ]; then
  if [ "${NSG_BROWSER_BACKEND:-}" != "aside" ]; then
    echo "Contract transport requires explicit NSG_BROWSER_BACKEND=aside" >&2
    exit 1
  fi
  step "Verify pinned contract browser runtime" verify_contract_browser_runtime
fi
step "Unit and publication regression tests" uv run pytest tests -q
step "Ruff lint and format" ruff_gate
step "Project integrity" uv run python scripts/validate_project.py
step "Contribution and reference crosswalk" uv run python scripts/validate_contribution_crosswalk.py
step "Editable visual and table sources" uv run python scripts/validate_visual_assets.py \
  --require-pdf-tools --check-regeneration
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
  echo "All CI steps passed locally; hosted CI remains a separate required result."
  exit 0
fi
printf 'CI-equivalent failures (%d):\n' "${#FAILED[@]}"
printf '  - %s\n' "${FAILED[@]}"
exit 1
