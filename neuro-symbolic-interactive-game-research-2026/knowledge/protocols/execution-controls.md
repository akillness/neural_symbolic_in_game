---
type: Protocol
title: 실행 통제 (decoding·seed·timeout)
description: temperature 0.7 · top_p 0.95 · max_output_tokens 1024 · seeds [11,23,47,83,131] · K=3 · timeout 60s · cold-cache 1차.
tags: [controls, frozen-config]
timestamp: 2026-08-14T00:00:00Z
---

# Overview

정확한 모델 revision 필수(version_policy). 이 수치의 단일 진실 원천은
`configs/experiment-matrix.yaml`이며, 본 원자와의 불일치는
[드리프트 검사](/protocols/config-drift-check.md)가 탐지한다.
