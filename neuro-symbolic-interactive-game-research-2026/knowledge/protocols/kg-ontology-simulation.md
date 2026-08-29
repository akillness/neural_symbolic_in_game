---
type: Protocol
title: KG 온톨로지 제안 시뮬레이션

description: 동결된 링크 holdout과 후보 풀에서 제안 전략을 기준선부터 순차 평가하고 제약 충족 개선만 keep하는 재현 절차.
tags: [kg, ontology, autoresearch, simulation-only]
timestamp: 2026-08-25T00:00:00Z
---

# Protocol

1. OKF 문서 그래프, 타입 온톨로지, curated relation, benchmark config의 해시를 동결한다.
2. config holdout ID 목록이 질의별 holdout ID와 순서까지 정확히 같은지 확인한다.
3. holdout relation을 학습 그래프와 직접 reference edge에서 함께 제거한다.
4. 모든 전략을 같은 질의·후보·예산에서 순서대로 평가하고 기준선을 먼저 기록한다.
5. aggregate·source별 competency question 최소치와 온톨로지 무위반을 먼저 확인한다.
6. recall·coverage·`Sem@K` floor를 통과한 전략만 비교한다.
7. config가 선언한 precision, realistic-tie MRR, nDCG, Brier score, 복잡도 순으로 엄격히
   개선할 때만 keep한다.
8. 동률과 회귀는 discard한다. 이 keep/discard는 오프라인 전략 선택이며 Git을 reset하지 않는다.
9. SQLite는 sibling 임시 파일에 완성·검사한 뒤 원자적으로 교체하고 symlink·비-SQLite target은 거부한다.

# Authority boundary

출력은 `engineering_only: true`, `simulation_only: true`다. 합성 closed-world negative는
"현재 엣지로 등록되지 않음"을 뜻할 뿐 실제로 거짓이라는 독립 의미 판정이 아니다.
Graphify 권위 그래프, 게임 상태, validator, repair, save schema, Godot 파일은 입력도
쓰기 대상도 아니다. `C-RESULT-001`부터 `C-RESULT-005`까지 자동 승격할 수 없다.

# Relations

- 온톨로지: [TRACE-RPG application ontology](/concepts/trace-rpg-application-ontology.md)
- 지표: [KG 링크 제안 품질](/metrics/kg-proposal-quality.md)
- 실행 통제: [execution controls](/protocols/execution-controls.md)
- 평가 근거: [KG·온톨로지 제안 평가 1차 출처](/citations/kg-ontology-evaluation-literature.md)
- 클레임 경계: [claim boundary](/concepts/claim-boundary.md)
