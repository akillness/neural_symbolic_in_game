#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

uv run python scripts/validate_game_studio.py
uv run python scripts/validate_concept_assets.py
uv run python scripts/validate_motion_assets.py
uv run python scripts/validate_player_asset.py
uv run python -m pytest -q \
  tests/test_godot_experimental_game.py \
  tests/test_godot_web_release.py \
  tests/test_playable_evaluation.py \
  tests/test_balance_archetypes.py \
  tests/test_codex_oauth_llm.py
uv run ruff check \
  scripts/codex_oauth_llm.py \
  scripts/capture_godot_evidence.py \
  scripts/png_contract.py \
  scripts/project_experimental_bridge.py \
  scripts/run_playable_evaluation.py \
  scripts/run_balance_archetypes.py \
  scripts/validate_game_studio.py \
  scripts/validate_concept_assets.py \
  scripts/validate_motion_assets.py \
  scripts/validate_player_asset.py \
  scripts/verify_motion_ingest.py \
  tests/test_codex_oauth_llm.py \
  tests/test_godot_experimental_game.py \
  tests/test_godot_web_release.py \
  tests/test_playable_evaluation.py \
  tests/test_balance_archetypes.py
uv run ruff format --check \
  scripts/codex_oauth_llm.py \
  scripts/capture_godot_evidence.py \
  scripts/png_contract.py \
  scripts/project_experimental_bridge.py \
  scripts/run_playable_evaluation.py \
  scripts/run_balance_archetypes.py \
  scripts/validate_game_studio.py \
  scripts/validate_concept_assets.py \
  scripts/validate_motion_assets.py \
  scripts/validate_player_asset.py \
  scripts/verify_motion_ingest.py \
  tests/test_codex_oauth_llm.py \
  tests/test_godot_experimental_game.py \
  tests/test_godot_web_release.py \
  tests/test_playable_evaluation.py \
  tests/test_balance_archetypes.py
