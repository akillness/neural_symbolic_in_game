---
type: Metric Definition
title: 장기 모순율

description: 동일 유효성 조건에서 5·10·20턴 창마다 독립 오라클이 확인한 모순 에피소드 비율.
tags: [metric, memory, contradiction, proposed]
timestamp: 2026-08-25T00:00:00Z
---

# Definition

평가 창 길이를 $L\in\{5,10,20\}$, 완결된 평가 에피소드 집합을 $D_L$, 독립 오라클이
장기 모순을 확인한 지시함수를 $I_{\mathrm{contra}}(e,L)$라 하면

$$
\mathrm{LCR}_L=\frac{\sum_{e\in D_L} I_{\mathrm{contra}}(e,L)}{|D_L|}.
$$

$|D_L|=0$이면 값은 0이 아니라 `NA`다. 유효 에피소드율이 사전등록된 비열등 마진을
통과한 조건끼리만 비교한다. 이 항목은 정의일 뿐 실행 결과가 아니다.

# Relations

- 대조: [H3 KG 시간 메모리](/contrasts/h3-memory.md)
- 채점: [의미 오라클](/oracles/semantic-oracle.md)
- 누출 통제: [leakage guards](/protocols/leakage-guards.md)
- 클레임 경계: [claim boundary](/concepts/claim-boundary.md)
