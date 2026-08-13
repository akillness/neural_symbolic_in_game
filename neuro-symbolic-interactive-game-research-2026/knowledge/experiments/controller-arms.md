---
type: Controller Arm Set
title: 컨트롤러 arm A0–A5와 예산 계약
description: direct_commit부터 trace_rpg_full까지 6개 arm — A3/A4/A5는 최대 호출 4(1+K), K=3으로 예산 매칭.
tags: [arms, budget]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

| arm | 구조 제약 | 검증기 | 수리 | 최대 호출 |
|---|---|---|---|---|
| A0 direct_commit | 없음 | 사후 채점만(격리 빌드) | 없음 | 1 |
| A1 structural_constraint_only | 스키마/문법 | 사후 채점만 | 없음 | 1 |
| A2 validator_rejection_only | 없음 | 거절 | 없음 | 1 |
| A3 matched_budget_blind_retry | 없음 | 거절 | 일반 재시도 ≤K | 4 |
| A4 structured_repair | 없음 | 거절 | 타입 반례 ≤K | 4 |
| A5 trace_rpg_full | 인코딩 정책+KG provenance | 거절/커밋+재검증 | 타입 반례 ≤K | 4 |

시도별 계정: tokens · provider_latency_ms · total_request_latency_ms · cost · failure_class.

# Relations

- 게임 내 A4 미러: [LLM 채널 데모](/engine/llm-channel-demo.md)
- 공통 통제: [실행 통제](/protocols/execution-controls.md)
