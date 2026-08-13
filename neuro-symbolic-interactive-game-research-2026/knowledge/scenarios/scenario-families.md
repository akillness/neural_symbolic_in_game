---
type: Scenario Family Set
title: 확증 시나리오 패밀리 7종
description: 세계 접근성·인과, NPC 공개, 시간 기억, 인물 기만, 감정 상승·불확실 — 각 패밀리는 등록 앵커와 1차 종점을 가진다.
tags: [scenarios, families]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

| 패밀리 | 앵커 | 1차 종점 |
|---|---|---|
| 세계 접근성 | IF-LOCK-001 | valid episode rate |
| 세계 인과 | IF-CAUSAL-001 | valid episode rate |
| NPC 공개 | NPC-SECRET-001 | hard dialogue violation rate |
| 시간 기억 | NPC-MEMORY-020 | 회상 모순율 (5/10/20턴) |
| 인물 기만 | NPC-DECEPTION-001 | 의미 하드 위반 |
| 감정 상승 | AFF-RISE-001 | 게이트 후 긴장 RMSE |
| 감정 불확실 | AFF-UNCERTAIN-001 | 폴백 정확성 |

확증 항목은 개발 발화의 의역이 아닌 템플릿 인스턴스화.

# Relations

- 개발 전용: [Sealed Lighthouse 개발 fixture](/scenarios/sealed-lighthouse-dev.md)
