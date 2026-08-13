#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

uv run python -m pytest -q tests/test_codex_oauth_llm.py
uv run ruff check scripts/codex_oauth_llm.py tests/test_codex_oauth_llm.py
uv run ruff format --check scripts/codex_oauth_llm.py tests/test_codex_oauth_llm.py
