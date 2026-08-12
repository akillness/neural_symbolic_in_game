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

![System architecture](./neuro-symbolic-interactive-game-research-2026/visuals/system-architecture.svg)

## Quick validation

```bash
cd neuro-symbolic-interactive-game-research-2026
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
```

The current package is a research scaffold, not a claim that model experiments have already run. Empirical values remain explicitly marked `TODO-RESULT` until trace-backed runs pass the release gates.
