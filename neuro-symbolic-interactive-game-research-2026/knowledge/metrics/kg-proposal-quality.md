---
type: Metric Definition
title: KG 링크 제안 품질

description: 동결된 타입 관계 holdout에서 링크 제안 전략의 정밀도·재현율·순위·캘리브레이션·온톨로지 적합성을 계산한다.
tags: [metric, kg, ontology, simulation-only]
timestamp: 2026-08-25T00:00:00Z
---

# Definitions

질의 집합 $Q$, 선택된 링크 집합 $S_q$, 동결된 관련 링크 집합 $G_q$에 대해
$TP=\sum_q|S_q\cap G_q|$, $FP=\sum_q|S_q\setminus G_q|$,
$FN=\sum_q|G_q\setminus S_q|$로 둔다.

$$
P=\frac{TP}{TP+FP},\qquad R=\frac{TP}{TP+FN},\qquad
F_1=\frac{2PR}{P+R}.
$$

분모가 0이면 해당 비율은 이 도구에서 `0.0`으로 고정한다. 현실적 동률 순위는
$r_q=(r_q^{\mathrm{opt}}+r_q^{\mathrm{pess}})/2$이고,
$\mathrm{MRR}=|Q|^{-1}\sum_q r_q^{-1}$이다. 이진 관련성의
$\mathrm{nDCG}@K$와 $\mathrm{Hits}@K$도 함께 보고한다.

후보 신뢰도 $s_i\in[0,1]$와 관련성 라벨 $y_i\in\{0,1\}$에 대해

$$
\mathrm{BS}=N^{-1}\sum_{i=1}^{N}(s_i-y_i)^2.
$$

상위 $K$ 링크의 domain/range 제약 적합 비율은

$$
\mathrm{Sem}@K=\frac{\sum_{q\in Q}\sum_{i=1}^{K}I[\mathrm{valid}_{qi}]}{K|Q|}.
$$

이 수치는 설계된 closed-world holdout에서 링크 복원을 측정한다. 실제 사용자 유용성,
런타임 검색 효능, 의미 완전성 또는 `C-RESULT-004`의 근거가 아니다.

# Relations

- 프로토콜: [KG 온톨로지 제안 시뮬레이션](/protocols/kg-ontology-simulation.md)
- 온톨로지: [TRACE-RPG application ontology](/concepts/trace-rpg-application-ontology.md)
- 근거: [KG·온톨로지 제안 평가 1차 출처](/citations/kg-ontology-evaluation-literature.md)
- 경계: [claim boundary](/concepts/claim-boundary.md)
