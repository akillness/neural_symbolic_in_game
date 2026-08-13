# Neural-Symbolic Interactive Game Research 2026

[![validate](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml/badge.svg)](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Knowledge](https://img.shields.io/badge/knowledge-llm--wiki%20%2B%20Graphify-6f42c1)](./llm-wiki/index.md)
[![Research status](https://img.shields.io/badge/status-experimental-orange)](./neuro-symbolic-interactive-game-research-2026/README.en.md)

도전적인 뉴로-심볼릭 인터랙티브 게임 연구를 위한 이중언어 논문 초안, 10개 모델 평가 매트릭스, 결정론적 정책 검증 런타임, semantic trace replay, recorded-response 실험 runner, 게임 브리지, 지속 갱신 가능한 연구 하네스입니다. 실제 모델/엔진 어댑터와 인간 실험은 다음 구현 단계입니다.

This repository contains a bilingual paper draft, a ten-model evaluation matrix, deterministic policy validation, semantic trace replay, a recorded-response experiment runner, a game bridge, and a refreshable research harness. Real model and engine adapters plus the human study remain future work.

| Start here | Description |
|---|---|
| [한국어 안내](./neuro-symbolic-interactive-game-research-2026/README.ko.md) | 연구 질문, 구조, 실행 순서 |
| [English guide](./neuro-symbolic-interactive-game-research-2026/README.en.md) | Research questions, architecture, execution |
| [한국어 논문 초안](./neuro-symbolic-interactive-game-research-2026/paper/ko/manuscript.md) | TRACE-RPG manuscript draft |
| [English paper draft](./neuro-symbolic-interactive-game-research-2026/paper/en/manuscript.md) | TRACE-RPG manuscript draft |
| [Project knowledge index](./llm-wiki/index.md) | Persistent sources, concepts, reports, and graph |

## System at a glance

![Trust boundary: learned proposal, symbolic authority](./neuro-symbolic-interactive-game-research-2026/visuals/system-architecture.svg)

제안은 학습 모델이, 커밋 권한은 결정론적 게이트가 가집니다. 검색·메모리·감정 추정은 제안 컨텍스트일 뿐 정식 상태를 바꿀 수 없습니다.
A learned model proposes; only the deterministic gate commits. Retrieval, memory, and affect are proposal context and can never mutate canonical state.

![One transaction: parse, validate, bounded repair, defensive check, commit](./neuro-symbolic-interactive-game-research-2026/visuals/commit-transaction.svg)

## What the numbers actually say

아래 두 그림은 동결된 파일럿 CSV와 주장 원장에서 직접 생성되므로 원본 수치와 어긋날 수 없습니다. CI가 재생성 결과와 커밋된 SVG의 일치를 강제합니다.
Both figures below are generated directly from the frozen pilot CSVs and the claim ledger, so they cannot drift from their sources; CI enforces that the committed SVGs match a fresh regeneration.

![Every pilot number, generated from the frozen artifact](./neuro-symbolic-interactive-game-research-2026/visuals/pilot-evidence.svg)

![Claim ledger status](./neuro-symbolic-interactive-game-research-2026/visuals/claim-status.svg)

분모는 전부 저자가 설계한 결정론적 사례입니다. 효능 주장 `C-RESULT-001`–`005`는 근거가 없는 `TODO-RESULT`입니다.
Every denominator is an authored deterministic case. The efficacy claims `C-RESULT-001`–`005` are `TODO-RESULT` with no evidence.

![Academic pipeline status](./neuro-symbolic-interactive-game-research-2026/visuals/research-workflow.svg)

![Planned confirmatory design — no result in this repository comes from this matrix](./neuro-symbolic-interactive-game-research-2026/visuals/confirmatory-design.svg)

Regenerate all six visuals with `uv run python scripts/generate_readme_visuals.py`.

## Quick validation

```bash
cd neuro-symbolic-interactive-game-research-2026
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
uv run python scripts/generate_readme_visuals.py
```

The current package is a research scaffold, not a claim that model experiments have already run. Empirical values remain explicitly marked `TODO-RESULT` until trace-backed runs pass the release gates.
