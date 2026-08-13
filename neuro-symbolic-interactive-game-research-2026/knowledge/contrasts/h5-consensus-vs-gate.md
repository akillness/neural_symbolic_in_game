---
type: Contrast Family
title: H5 — 컨센서스 대 기호 게이트 [PROPOSED]
description: 동일 예산 계정에서 컨센서스 검증(C1/C2)과 기호 게이트(A5), 하이브리드(C3)의 비용-유효성 Pareto 위치를 비교하는 제안 대조.
tags: [h5, consensus, proposed, not-registered]
timestamp: 2026-08-14T12:00:00Z
---

# Schema

H5a: A5 vs C1·C2 — 유효성 비열등(2pp 재사용) + 비용 우월. H5b: 의미 오류율에서 C1 vs A5.
H5c: C3 vs A5 — 의미 오류율 우월 + 하드 유효성 유지 + 비용 증가 보고.
분석은 H1 혼합효과 구조 재사용, Holm 보정. 상태: PROPOSED — experiment-matrix.yaml 미등록,
사전등록 전 결과 주장 금지.

# Relations

- arm: [컨센서스 arm C1–C3](/experiments/consensus-arms.md) · 기준: [A0–A5](/experiments/controller-arms.md)
- 지표: [cost-of-valid-episode](/metrics/cost-of-valid-episode.md) ·
  [valid episode rate](/metrics/valid-episode-rate.md) · 의미 판정: [의미 오라클](/oracles/semantic-oracle.md)
- 논거: [KG–validator 동형성](/concepts/kg-validator-isomorphism.md) ·
  근거 문헌: [컨센서스·비용 문헌](/citations/consensus-cost-literature.md)
