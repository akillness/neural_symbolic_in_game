---
type: Experiment Stage
title: 결정론적 오프라인 파일럿 (PQ1–PQ5)
description: 설계 fixture에 대한 정확한 count만 보고하는 적합성 파일럿 — p-value·모집단 CI 부여 금지.
tags: [pilot, conformance]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

PQ1 유효 commit/invalid 불변 · PQ2 rejection/retry/repair 경로 · PQ3 변조·주입 거부 ·
PQ4 adapter/manifest fail-closed · PQ5 unknown-key 파서 parity.
도메인 4개: validator/state isolation · repair control flow · fault injection ·
adapter/accounting. 배정 키: (run, arm, scenario, seed, model, revision,
h_controller, h_input, h_prior). 종단 클래스 4: commit · symbolic fallback ·
adapter failure · controller failure.

# Relations

- 경계: [claim boundary](/concepts/claim-boundary.md)
- 다음 단계: [Stage 1 스크리닝](/experiments/stage-1-screening.md)
