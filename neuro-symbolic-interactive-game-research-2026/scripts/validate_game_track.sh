#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

uv run python scripts/validate_game_studio.py
uv run python scripts/validate_concept_assets.py
uv run python -m pytest -q tests/test_godot_experimental_game.py
uv run ruff check \
  scripts/capture_godot_evidence.py \
  scripts/png_contract.py \
  scripts/project_experimental_bridge.py \
  scripts/validate_game_studio.py \
  scripts/validate_concept_assets.py \
  tests/test_godot_experimental_game.py
uv run ruff format --check \
  scripts/capture_godot_evidence.py \
  scripts/png_contract.py \
  scripts/project_experimental_bridge.py \
  scripts/validate_game_studio.py \
  scripts/validate_concept_assets.py \
  tests/test_godot_experimental_game.py
