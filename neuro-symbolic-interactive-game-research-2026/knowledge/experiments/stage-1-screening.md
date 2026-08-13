---
type: Experiment Stage
title: Stage 1 스크리닝
description: 등록 모델 10개 전체를 트랙당 시나리오 30 × 반복 3으로 Pareto 선별한다 — 논문 수준 인과 결론 없음.
tags: [screening, planned]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

models: all-10 · scenarios_per_track: 30 · repetitions: 3 ·
arms: [A0–A5 전체](/experiments/controller-arms.md) ·
grounding: none | rag | kg_temporal_memory. 상태: PLANNED.

# Relations

- 승격 → [Stage 2 확증](/experiments/stage-2-confirmatory.md)
