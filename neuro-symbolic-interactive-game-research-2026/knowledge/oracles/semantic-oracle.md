---
type: Oracle
title: 의미 오라클
description: 불가능 행동·금지 공개·미지 사실·필수 누락·모순·근거 없는 변경을 판정하는 블라인드 annotation 스키마.
tags: [oracle, semantic]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

sentinel: disclosure_hazard · omitted_object_hazard · unknown_field_hazard.
레코드 필드: scenario_id/template_id · oracle_version/gold_manifest_sha256 ·
encoded_valid · semantic_valid · hazard_codes · evidence_spans · annotator_id(가명) ·
confidence(서수) · adjudication_status. 독립 레이블러 2인 + adjudication 계획,
Cycle 1 미수집.

# Relations

- 생성 모델 계열 단독 판정 금지: [leakage guards](/protocols/leakage-guards.md)
