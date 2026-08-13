---
type: Bundle Guide
title: TRACE-RPG Methods Knowledge Bundle
description: OKF v0.1 번들 — TRACE-RPG 실험 방법론의 지식 원자를 상호 링크로 연결한 방법 그래프.
tags: [okf, methods, trace-rpg]
timestamp: 2026-08-14T00:00:00Z
---

# Overview

이 번들은 논문(`paper/latex/*/main.tex`), 오라클 계획(SL-ORACLE-001), 동결 설정
(`configs/experiment-matrix.yaml`), 게임 기획(SL-GDD-001)에 흩어진 실험 방법을
OKF 지식 원자로 정규화한다. 링크는 관계의 존재를 주장하고, 관계의 의미는 주변 산문이 명명한다.

타입 규약: Concept · Experiment Stage · Controller Arm Set · Contrast Family ·
Oracle · Protocol · Metric Definition · Scenario Family Set · Engine Evidence ·
Claim Boundary · Runbook.

# Relations

- 검증: [OKF 구조 린트](/protocols/bundle-validation.md)와
  [설정 드리프트 검사](/protocols/config-drift-check.md)를 배포 전 실행한다.
