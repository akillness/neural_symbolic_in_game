---
type: Experiment Stage
title: Stage 2 확증
description: 승격 3개 모델을 트랙당 시나리오 120 × seed 5(11·23·47·83·131)로 사전등록 full factorial + ablation 분석한다.
tags: [confirmatory, planned]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

models: promoted-3 · scenarios_per_track: 120 · repetitions: 5 ·
affect_variants: off | uncertainty_calibrated_soft_adaptation (A5 위 교차, 7번째 arm 아님) ·
ablations: no_retrieval · no_memory · no_policy · no_validator · rejection_only · no_affect.
상태: PLANNED — 동결·사전등록 후에만 확증.

# Relations

- 검정: [H1](/contrasts/h1-gate-vs-direct.md) · [H2](/contrasts/h2-repair-vs-retry.md) ·
  [H3](/contrasts/h3-memory.md) · [H4](/contrasts/h4-affect.md)
- 채점: [인코딩 오라클](/oracles/encoding-oracle.md) · [의미 오라클](/oracles/semantic-oracle.md)
- 누출 방지: [leakage guards](/protocols/leakage-guards.md)
