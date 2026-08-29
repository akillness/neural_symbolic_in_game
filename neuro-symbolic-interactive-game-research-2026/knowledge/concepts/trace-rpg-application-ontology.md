---
type: Application Ontology
title: TRACE-RPG application ontology

description: OKF 방법론 관계와 인코딩된 게임 상태 술어를 분리해 등록하는 폐쇄형 애플리케이션 온톨로지.
tags: [kg, ontology, typed-relations, simulation-only]
timestamp: 2026-08-25T00:00:00Z
---

# Scope

`knowledge/ontology/trace-rpg-ontology.json`은 두 레이어를 한 레지스트리에서 분리한다.
`methods` 레이어는 OKF 문서의 타입 관계를, `game-state` 레이어는 기존 검증기 술어에
대응하는 관계 어휘만 등록한다. SQLite 미러와 시뮬레이터는 `methods` 레이어를 사용한다.
게임 런타임은 이 파일을 읽지 않으며 기존 `WorldState`와 validator가 계속 권위 경계다.

# Invariants

모든 노드는 선언된 타입을 갖고, 모든 엣지는 선언된 relation과 존재하는 양 끝점을 가지며,
domain/range를 만족하고, 중복·self-edge가 없어야 한다. 각 competency question은 aggregate 최소치와 source별 최소치를 모두 만족해야 한다. 여섯 개 game-state 관계는
$v_{policy}$, $v_{pre}$, $v_{reach}$, $v_{know}$, $v_{disc}$, $v_{quest}$에 명시적으로
매핑된다. 이는 인코딩 커버리지의 구성 불변량이지 의미 완전성 증거가 아니다.

# Relations

- 설계 근거: [KG–validator 동형성](/concepts/kg-validator-isomorphism.md)
- 실행 절차: [KG 온톨로지 제안 시뮬레이션](/protocols/kg-ontology-simulation.md)
- 측정: [KG 링크 제안 품질](/metrics/kg-proposal-quality.md)
- 경계: [claim boundary](/concepts/claim-boundary.md)
