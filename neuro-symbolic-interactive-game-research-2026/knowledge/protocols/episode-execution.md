---
type: Runbook
title: 게임 에피소드 실험 실행 절차
description: 동결 시나리오부터 확증 분석까지 — 게임 에피소드가 실험 단위가 되는 6단계.
tags: [runbook, pipeline]
timestamp: 2026-08-14T00:00:00Z
---

# Steps

1. [시나리오 패밀리](/scenarios/scenario-families.md) 템플릿 인스턴스화·동결
2. 블록 무작위화(모델×시나리오×seed×arm×grounding×affect) → 실행 전 배정 키
3. 에피소드 실행 — 브리지 이벤트와 전/후 상태 해시, 시도별 계정 기록
4. 결정론적 리플레이 무결성·연속성 검증 ([M6 fixture](/engine/m6-engine-fixture.md) 원리)
5. 동결 오라클 채점 — [인코딩](/oracles/encoding-oracle.md) → [의미](/oracles/semantic-oracle.md)
6. 사전등록 분석 — H1–H4 게이트키핑 · [treatment-policy](/protocols/missingness-policy.md)
