---
type: Metric Definition
title: Cost-of-Valid-Episode [PROPOSED]
description: 유효 에피소드 1건당 기대 비용 E[cost]/P(valid) — 비용과 정확도를 접는 결정 지표(문헌의 cost-of-pass 형식).
tags: [metric, cost, proposed]
timestamp: 2026-08-14T12:00:00Z
---

# Overview

cost는 토큰·호출·지연·$의 벡터로 병행 보고하고, 스칼라 접기는 $ 기준.
Pareto 전선은 추정치·95% CI와 함께 기술 보고(전선 자체에 검정 없음).

# Relations

- 사용: [H5](/contrasts/h5-consensus-vs-gate.md) · 병행: [repair@K](/metrics/repair-at-k.md)
