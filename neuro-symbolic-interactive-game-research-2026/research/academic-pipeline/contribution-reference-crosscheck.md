# 논문 기여도·레퍼런스·실험 교차검증 / Contribution–Reference–Experiment Crosscheck

상태: **VERIFIED-SCOPE-LIMITED**

점검일: **2026-09-02** (최초 2026-08-30; 2026-09-02 top-venue 보강 S47--S51)

대상 원고: `paper/latex/{en,ko}/main.tex`

구조화 정본:

- `contribution-evidence-matrix.csv`
- `reference-topic-crosswalk.csv`
- `experiment-evidence-matrix.csv`

## 1. 적용한 검증 원칙

K-Dense-AI `scientific-agent-skills`의 고정 커밋
`f6fcafeb1cc8c82eca0160a18bc41c38427b8e0f`에서 다음 원칙을 선택적으로 적용했다.

1. 주장과 근거를 ID로 결합한다.
2. 근거가 없는 결과는 만들지 않고 `TODO-RESULT`로 남긴다.
3. 기여도–근거 매트릭스와 메서드–결과 일치 검사를 별도 산출물로 둔다.
4. 인용은 단일 색인에 의존하지 않고 BibTeX, 원고, Stage-5 다중 색인 기록을 대조한다.
5. 보고 완결성과 연구 품질을 구분한다.
6. 확증 결과와 탐색적·파일럿 결과를 분리한다.
7. 단위, 불확실성, 표본 단위, 추론 상한을 명시한다.
8. 구조화 reviewer 코멘트처럼 `근거 있음 / 경계 / 다음 필요 단계`를 함께 기록한다.

반대로, 논문마다 AI 생성 그림을 의무화하는 규칙은 채택하지 않았다. 이 저장소의 그림은
동결 데이터나 실제 엔진 캡처가 요구할 때만 생성하며, 장식적 그림을 근거로 취급하지 않는다.

## 2. 기여도 중심 결론

| ID | 기여 | 가장 가까운 선행 주제 | 현재 직접 근거 | 정직한 상한 |
|---|---|---|---|---|
| C1 | 버전된 신뢰경계 계약 | 게임 특화 기호 검증, 구조 제약, 검색·메모리 | 계약·parser 코드, proposal/replay parity fixture, Godot bridge schema | 인코딩된 필드와 작성 fixture의 계약 적합성 |
| C2 | validate–repair–commit controller | planning precondition/effect, narrative interposition, runtime enforcement | 6개 술어, 불변 fallback, 방어적 재검증, 엔진 policy mirror | 동결 정책·사례에서의 메커니즘 동작 |
| C3 | 감사 연결 근거 계층 | process metrics, reproducibility, integrity reporting | checksum, state-semantic replay, continuity, render/state receipt | 지정 변이에 대한 무결성·재생 적합성; 작성자 인증 아님 |
| C4 | 할당 완전 conformance harness | explicit-state environments, agent benchmarks, 평가·통계 지침 | 동결 assignment, terminal failure 분류, manifest guard | 설계 사례의 정확 집계; 모집단 추정 아님 |
| C5 | typed 반례 유도 연산자 $\rho$ | symbolic validation, self-feedback, runtime feedback | E1의 repairability class 비교와 E2의 단일모델 regime screen | 작성 fixture + 특정 repairable regime의 pilot-only 전이 |

핵심 novelty는 개별 아이디어의 발명이 아니라 **C1–C5가 하나의 권위 경계와 추적 계약으로
결합되고, 그 결합의 성공·실패·미생성 trace까지 같은 분모에서 감사되는 구현**이다.
`C-RESULT-001`–`005`는 모두 `TODO-RESULT`이며, 위 기여도를 효능·우월성 주장으로 승격하지
않는다.

## 3. 레퍼런스 ↔ 주제 교차검증

`reference-topic-crosswalk.csv`는 BibTeX의 55개 논문 레코드를 다음 9개 주제로 전수 매핑한다.
`S43`은 의도적 결번이며 가짜 레코드를 만들지 않는다.

| 주제 | 범위 | 원고에서의 역할 | 대표 기여 연결 |
|---|---|---|---|
| T1 | interactive narrative / grounded game worlds | 직접·인접 게임 비교와 권위 배치 | C1, C2, C5 |
| T2 | retrieval / memory / role agents | proposal context와 commit authority 분리 | C1 |
| T3 | structured generation | 구조 적합성과 상태 상대 유효성 분리 | C1 |
| T4 | environments / benchmarks | 명시 상태, multitrack, process 평가 선례 | C3, C4 |
| T5 | player experience / affect | 현재 미실행인 인간·적응 레인의 경계 | `BOUNDARY-FUTURE` |
| T6 | human and LLM evaluation | 향후 blinded evaluation·bias control | C4 |
| T7 | statistics / reproducibility | 추론 상한, 재현성, 향후 분석 설계 | C3, C4 |
| T8 | planning / runtime / interposition | novelty의 역사적 계보와 비발명 경계 | C2, C3 |
| T9 | feedback repair | $\rho$의 feedback channel·authority 차이 | C5 |

Stage-5 기계 기록 기준 집계는 **55개 = VERIFIED 46 + PREPRINT 9**, unmatched 0,
hallucinated 0이다. Semantic Scholar가 429를 반환한 22개 레코드는 `rate_limited`로 명시했고,
각 정체성은 Crossref, OpenAlex, PMLR, arXiv 또는 공식 학회 프로그램에서 별도로 확인했다.
2026-08-30 spot-check에서 S02, S44, S45, S46의 제목 레코드를 관찰했지만 이는 재현 가능한
전수 재감사를 대체하지 않는다. 따라서 이 수치는 **미일치 22건**이 아니라 **세 번째 색인
coverage gap 22건**이다.

## 4. 실험을 네 레인으로 정리

| 레인 | 설계 단위 | 핵심 관찰 | 지원 범위 | 금지되는 해석 |
|---|---|---|---|---|
| E1 오프라인 conformance | 작성 fixture와 동결 repairability class | gate 13/13; commit 0/12 rejection, 0/12 blind, 5/12 $\rho$, 6/12 oracle; detectable fault 10/10; guard 3/3 | C1–C5의 구현·메커니즘 적합성 | 모집단 효능, 모델 품질, safety rate |
| E2 live RQ2 screening | 5개 cell × seed-indexed call 5회, matched $K=1$ | `signal-repair-v2/policy_blind`에서만 initial invalid 5/5, $\rho$ 5/5, blind 0/5; 다른 4 cell은 guided advantage 없음; noncommit 15/15 state-isolated | C5의 regime-specific mechanism transfer, `pilot-only` | `C-RESULT-003`, 모델 순위, 일반 sample efficiency |
| E3 KG/ontology simulation | 7 strategy × 6 query × 5 candidate = 210 score | retained strategy P=R=F1=1.000, MRR 0.944, Brier 0.131, Sem@3 1.000; baseline 0/6 | closed-world construction result | runtime retrieval, long-horizon memory, `C-RESULT-004` |
| ENG1 Godot/Web engineering | authored fixture 4개, combined 52 checks, smoke 8, balance archetype 5 | 4/4, 52/52, 8/8, 5/5 통과 | 엔진 로컬 정책 mirror·presentation conformance | usability, fun, G4, 최종 G6, live Python transport |

E1은 확률 표본이 아니므로 $p$-value나 모집단 신뢰구간을 붙이지 않는다. E2의 실행 receipt는
모두 `K=1`(아암당 최대 `1+K=2`)이며 초기 계획의 `K=3`은 실행되지 않았다. E2의 seed는 hosted
sampler를 통제하지 않고 revision과 token accounting이 고정되지 않았다. 해시로 동결된 내부
summary의 과거 `C-RESULT-003 pilot-only` 문구는 외곽 promotion manifest가 명시적으로
supersede하며, 현재 승격 범위는 `C-PILOT-007/008`뿐이다. E3는 실제 검색 런타임이 아니다.
ENG1의 남은 사람 측정은 `_workspace/current/qa/human-measurement-packet.md`가 소유한다.

## 5. 메서드–결과 일치 판정

- **PASS:** C1–C5는 모두 코드·계약·fixture 또는 receipt 경로를 가진다.
- **PASS:** E1, E2, E3, ENG1의 단위와 분모가 서로 섞이지 않는다.
- **PASS:** E2는 `C-PILOT-007/008`만 지원하고 `C-RESULT-003`은 승격하지 않는다.
- **PASS:** E3는 모든 `C-RESULT-*`에 비지원으로 표시된다.
- **PASS:** 영문·국문 원고가 같은 55개 BibTeX key를 인용하고 같은 기여 ID와 레인 ID를 쓴다.
- **OPEN:** 확증 다중모델·독립 semantic oracle·인간 참가자·affect·runtime retrieval/memory·live transport 실험.
- **OPEN:** G4와 사람 제스처·latency·soak·rollback이 필요한 G6.

## English summary

The three CSVs bind all five manuscript contributions to prior-work topics, repository evidence,
experiment lanes, claim IDs, and explicit inference ceilings; map all 55 bibliography records to nine
topics; and keep offline conformance, live screening, KG simulation, and engine engineering as
non-interchangeable units. The contribution is the audited integration, not invention of planning,
interposition, constrained decoding, retrieval, or feedback repair. No `C-RESULT-*` claim is promoted.
