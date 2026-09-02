#!/usr/bin/env bash
# Deploy the live commit-gate dashboard as the production site (D-068).
#
# Site layout (identical to the local run guide, so every relative path is unchanged):
#   dist/dashboard/   game-track/web/dashboard/   (root "/" redirects here)
#   dist/public/      the public-safe Godot Web export from scripts/build_godot_web.sh
#   vercel.json       game-track/web/vercel.dashboard.json (outputDirectory = dist, so Vercel's
#                     "public/ if it exists" default cannot swallow the dashboard)
#
# Presentation-only: the dashboard consumes the game's one-directional postMessage mirror and
# has no channel back into the game. Deploying it promotes no research, G4, or G6 status.
#
# Usage: scripts/deploy_vercel_dashboard.sh [--dry-run]
#   Requires a logged-in Vercel CLI (`vercel whoami`) with access to the project below.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB="$PROJECT_ROOT/game-track/web"
VERCEL_PROJECT="${VERCEL_PROJECT:-sealed-lighthouse-trace-rpg}"
VERCEL_SCOPE="${VERCEL_SCOPE:-akillness-projects}"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

if [[ ! -f "$WEB/public/index.pck" || ! -f "$WEB/public/index.wasm" ]]; then
  echo "== Web export missing; building it on a disposable copy" >&2
  "$PROJECT_ROOT/scripts/build_godot_web.sh"
fi

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/sealed-lighthouse-dashboard-site.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/site/dist"
rsync -a --exclude vercel.json "$WEB/public/" "$STAGE/site/dist/public/"
rsync -a --exclude screenshots --exclude 'README*' "$WEB/dashboard/" "$STAGE/site/dist/dashboard/"
cp "$WEB/vercel.dashboard.json" "$STAGE/site/vercel.json"

echo "== Staged site receipts"
(cd "$STAGE/site" && find . -type f | sort | while read -r f; do
  printf '%s  %s  %s\n' "$(shasum -a 256 "$f" | cut -c1-64)" "$(stat -f '%z' "$f")" "$f"
done)

if [[ "$DRY_RUN" == 1 ]]; then
  echo "== Dry run: not deploying"
  exit 0
fi

echo "== Linking $VERCEL_PROJECT ($VERCEL_SCOPE) and deploying to production"
vercel link --yes --project "$VERCEL_PROJECT" --scope "$VERCEL_SCOPE" --cwd "$STAGE/site" >/dev/null
vercel deploy --prod --yes --scope "$VERCEL_SCOPE" --cwd "$STAGE/site"
