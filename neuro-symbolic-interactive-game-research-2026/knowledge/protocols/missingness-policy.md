---
type: Protocol
title: 결측·실패 treatment-policy
description: timeout/파싱 실패는 adapter failure로, 수리 소진은 symbolic fallback으로 유지 — 추정량에서 제거하지 않는다.
tags: [missingness, estimand]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

응답 전 인프라 실패만 같은 seed 1회 재실행(감사 사유 기록) 후 실패로 채점.
인간 평가 결측: 단일 대치 금지, 비율 보고 + MAR·delta-MNAR 민감도.
에너지 텔레메트리 결측: 대치 없이 해당 추정량에서만 제외하고 count 보고.
보고 항목: effect size · 95% CI · raw n · cluster 수 · 제외 · 실패 count.
