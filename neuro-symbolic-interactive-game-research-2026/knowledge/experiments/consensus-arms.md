---
type: Controller Arm Set
title: 컨센서스 arm C1–C3 [PROPOSED]
description: consensus_vote_n(N=5 다수결), multiagent_debate_r(2×2 토론), consensus_then_gate(랭킹→게이트 최종 권한) 제안 arm 3종.
tags: [arms, consensus, proposed]
timestamp: 2026-08-14T12:00:00Z
---

# Schema

| arm | 검증 신호 | 예산 계정 | 하드 보장 |
|---|---|---|---|
| C1 consensus_vote_n | 구조 동치류 다수결 (소프트) | N 호출·전체 토큰 | 없음 |
| C2 multiagent_debate_r | 토론 수렴 (소프트) | 2R+1 호출 | 없음 |
| C3 consensus_then_gate | 소프트 랭킹 + 하드 게이트 | N+(1+K) 호출 | I1–I4 유지 |

기존 호출 수 매칭에 총 토큰 예산 매칭 축 추가 — Pareto 보고로 확장.
신규 종단 클래스 제안: consensus_deadlock(과반 미달, 상태 불변 보존).

# Relations

- 기준 arm: [A0–A5](/experiments/controller-arms.md) · 대조: [H5](/contrasts/h5-consensus-vs-gate.md)
- 게임 배선 증거(엔지니어링): [LLM 채널 데모](/engine/llm-channel-demo.md)
