---
type: Concept
title: 기호 커밋 게이트 (Symbolic Commit Gate)
description: 신뢰하지 않는 생성 제안을 정식 상태 변경으로부터 격리하는 TRACE-RPG의 핵심 트랜잭션 경계.
tags: [architecture, authority]
timestamp: 2026-08-14T00:00:00Z
---

# Overview

controller 입력 `c_t=(G_t,q_t)` 위에서 타입 엄격 파서(unknown top-level key 거부)와
7-튜플 validator `V(c,a)=(policy, pre, reach, know, disc, quest, E)`를 모두 통과한
후보만 전이 `T(c,a)`로 커밋된다. 실패 시 상태는 바이트 단위 보존.

# Relations

- 시험 대상 불변량: [구현 불변량 I1–I4](/concepts/invariants.md)
- 수리 경로: [validate–repair–commit 루프](/protocols/validate-repair-commit.md)
- 근거 한계: [claim boundary](/concepts/claim-boundary.md)
