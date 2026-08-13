---
type: Concept
title: 구현 불변량 I1–I4
description: 소진 실패 불변성, 제한된 기록 시도(K+1), 효과 권한, 상태 의미적 리플레이 — 파일럿이 fixture로 시험하는 네 약속.
tags: [invariants, pilot]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

| ID | 불변량 | 한계 |
|---|---|---|
| I1 | K 소진/커밋 전 실패 시 반환 상태 = prior state | 정리가 아닌 fixture 시험 |
| I2 | 최대 K+1 candidate attempt + 방어적 재검증 1회 | wall-clock 종료 보장 아님 |
| I3 | 효과·stage target은 ActionPolicy 허용 범위 내 | 정책 작성 정확성 가정 |
| I4 | 수락 trace는 terminal state 재구성 | 중간 수리 provenance 미재현 |

# Relations

- 게이트: [기호 커밋 게이트](/concepts/commit-gate.md)
- 엔진 대응: [M6 엔진 fixture](/engine/m6-engine-fixture.md)
