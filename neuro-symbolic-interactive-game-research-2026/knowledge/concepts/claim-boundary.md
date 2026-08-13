---
type: Claim Boundary
title: 근거 경계 (Claim Boundary)
description: 파일럿 근거는 단일 작성 world의 선언된 구조화 필드에 대한 구현 적합성까지만이며, 효능·경험·성능 주장을 금지한다.
tags: [boundary, honesty]
timestamp: 2026-08-14T00:00:00Z
---

# Overview

허용: 인코딩된 검사의 상태 격리, bounded repair/fallback 경로, 변조 거부, 분류 유지.
금지: 라이브 모델 동작, cross-model 우월성, 플레이어 경험/몰입(G4), 감정·검색·메모리
효능, 상용 엔진 성능, C-RESULT-001–005. Godot 리플레이 성공은 Stage 6 M6까지만 지지.

정직성 장치: 참조 repair callback = oracle 상한(배포 수리 방법 아님),
adapter telemetry = JSON-Schema const 합성 상수(측정값 아님).

# Relations

- 모든 결과 원자는 이 원자를 링크해야 한다:
  [파일럿 측정](/experiments/pilot-measurement.md) ·
  [엔진 증거](/engine/render-capture-evidence.md) ·
  [LLM 채널 데모](/engine/llm-channel-demo.md)
