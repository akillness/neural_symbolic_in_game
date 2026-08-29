#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GODOT_PROJECT="$PROJECT_ROOT/game-track/godot"
WEB_CONFIG="$PROJECT_ROOT/game-track/web"
OUTPUT_DIR="$WEB_CONFIG/public"

if command -v godot4 >/dev/null 2>&1; then
  GODOT_BIN="${GODOT_BIN:-$(command -v godot4)}"
elif command -v godot >/dev/null 2>&1; then
  GODOT_BIN="${GODOT_BIN:-$(command -v godot)}"
else
  echo "Godot 4.x was not found on PATH." >&2
  exit 1
fi

VERSION="$($GODOT_BIN --version)"
if [[ "$VERSION" != 4.* ]]; then
  echo "Godot 4.x is required; found: $VERSION" >&2
  exit 1
fi

PYTHONDONTWRITEBYTECODE=1 python3 "$PROJECT_ROOT/scripts/validate_player_asset.py"

STAGE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/sealed-lighthouse-web.XXXXXX")"
cleanup() {
  rm -rf "$STAGE_DIR"
}
trap cleanup EXIT

STAGED_PROJECT="$STAGE_DIR/project"
STAGED_OUTPUT="$STAGE_DIR/output"
mkdir -p "$STAGED_PROJECT" "$STAGED_OUTPUT"

run_godot_checked() {
  local log_path="$1"
  shift
  if ! "$@" 2>&1 | tee "$log_path"; then
    echo "Godot command failed: $*" >&2
    exit 1
  fi
  # Godot can prefix diagnostics with ANSI/control text, so do not anchor the
  # error marker at the beginning of the captured line. This sandbox blocks a
  # small set of macOS system-font and certificate reads; remove only those
  # exact host diagnostics before applying the fail-closed game-error gate.
  local checked_log="$log_path.checked"
  awk '
    index($0, "/System/Library/Fonts/") && /ERROR: Can.t open file from path .*\.ttc/ { next }
    /ERROR: Condition "ret != noErr" is true\. Returning: ""/ { held = $0; next }
    held != "" {
      if ($0 ~ /at: get_system_ca_certificates/) { held = ""; next }
      print held
      held = ""
    }
    { print }
    END { if (held != "") print held }
  ' "$log_path" > "$checked_log"
  if grep -Eq '(SCRIPT ERROR|ERROR):' "$checked_log"; then
    echo "Godot reported an import or script error: $*" >&2
    exit 1
  fi
}

# The research project keeps headless.tscn as its canonical default because its
# exact project.godot hash is bound into immutable evidence. Web export happens
# from this disposable copy and changes only the copy's launch scene.
#
# `addons/` is excluded on purpose. The repository tracks no addon file, the game
# references none, and `project.godot` enables no editor plugin, so nothing in the
# playable depends on one. A developer with a local editor addon installed under
# `addons/` would otherwise have it staged into the export, where built-in addon
# scripts using `class_name` abort the Web build. Excluding it makes the bundle a
# function of the tracked tree rather than of the developer's editor state.
rsync -a \
  --exclude '.godot/' \
  --exclude '.omc/' \
  --exclude 'addons/' \
  --exclude 'scripts/game3d/llm/' \
  --exclude 'assets/rig/' \
  "$GODOT_PROJECT/" "$STAGED_PROJECT/"
cp "$WEB_CONFIG/export_presets.cfg" "$STAGED_PROJECT/export_presets.cfg"
sed 's@run/main_scene="res://scenes/headless\.tscn"@run/main_scene="res://scenes/main_3d.tscn"@' \
  "$STAGED_PROJECT/project.godot" > "$STAGED_PROJECT/project.godot.tmp"
mv "$STAGED_PROJECT/project.godot.tmp" "$STAGED_PROJECT/project.godot"

if ! grep -q 'run/main_scene="res://scenes/main_3d.tscn"' "$STAGED_PROJECT/project.godot"; then
  echo "The staged Web project did not select the playable scene." >&2
  exit 1
fi

run_godot_checked "$STAGE_DIR/import.log" \
  "$GODOT_BIN" --headless --path "$STAGED_PROJECT" --import
run_godot_checked "$STAGE_DIR/export.log" \
  "$GODOT_BIN" --headless --path "$STAGED_PROJECT" \
    --export-release "Web" "$STAGED_OUTPUT/index.html"
cp "$WEB_CONFIG/vercel.json" "$STAGED_OUTPUT/vercel.json"
cp "$GODOT_PROJECT/assets/fonts/OFL.txt" "$STAGED_OUTPUT/NanumGothic-OFL.txt"

mkdir -p "$OUTPUT_DIR"
rsync -a --delete "$STAGED_OUTPUT/" "$OUTPUT_DIR/"

echo "Web build ready: $OUTPUT_DIR"
find "$OUTPUT_DIR" -maxdepth 1 -type f -print0 | sort -z | xargs -0 ls -lh
