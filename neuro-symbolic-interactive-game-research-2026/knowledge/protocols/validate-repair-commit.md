---
type: Protocol
title: Validate–Repair–Commit 루프
description: 구조화 오류를 수리 callback에 노출하고, 예산 K 소진 시 무변경 fallback, 성공 시 커밋 직전 방어적 재검증.
tags: [loop, repair]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

최대 기록 시도 K+1. repair는 상태를 직접 변경하지 않는다. 파일럿 참조 callback은
반례 유도가 아닌 oracle 상한(권위 상태에서 정책 필드 재구성).

# Relations

- [invariants](/concepts/invariants.md) · [controller arms](/experiments/controller-arms.md)
