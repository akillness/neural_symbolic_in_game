---
type: Runbook
title: 방법 원자 ↔ 동결 설정 드리프트 검사
description: OKF 원자에 인용된 수치가 experiment-matrix.yaml의 동결값과 일치하는지 기계 검증한다.
tags: [drift, preregistration]
timestamp: 2026-08-14T00:00:00Z
---

# Overview

방법 문서가 여러 곳(논문·계획서·설정)에 흩어질 때 생기는 조용한 불일치를
사전등록 전에 탐지한다 — 이것이 OKF 그래프가 실험 방법을 실제로 개선하는 지점.

# Steps

`python3 scripts/check_methods_drift.py` 실행 — 검사 항목: K, seeds, 규모(30×3/120×5),
decoding, timeout, 비열등 한계, arm 명단.
