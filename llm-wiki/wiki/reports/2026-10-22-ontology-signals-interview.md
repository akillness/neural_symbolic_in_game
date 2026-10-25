# TRACE-RPG 온톨로지·7개 검사: 인터뷰 근거 지도

- 날짜: 2026-10-22 인터뷰; 현재 상태 갱신 2026-10-23.
- 현재 구현: **승인된 `reveal_hint` 한정 구현과 관측된 focused 검증 결과가 존재한다.** §11은 최종 재생성 직전 동결한 증거 지도이며, 이후 최종 gate/PDF 상태는 별도 `research/npc-disclosure/final-verification-20261023.json` receipt를 따른다. §1–10의 미구현·승인 대기·당시 소스 줄번호는 인터뷰 시점 기록으로 보존한다.
- 범위: 한·영 원고, 온톨로지 레지스트리, Python 연구 실행계, Godot 게임 및 표시 계층, 저장된 실험 패킷.
- 자료 판정: 현재 소스와 선택된 패킷을 우선한다. 외부 리뷰·Jev 판정은 보조 의견이며 구현이나 실험의 증거가 아니다. 기존 원시 패킷은 수정하지 않는다.

## 1. 먼저 바로잡을 해석

현재 연구는 **모델 내부 상태를 온톨로지로 읽어 7개 수치로 변환하는 연구가 아니다.** 비권위 모델이 구조화한 행동 후보를 명시적 상태·정책과 비교해 7개 Boolean 검사를 수행하는 방식이다.

- 원고의 표현: `V(c,a)=(v_policy,v_pre,v_reach,v_know,v_disc,v_elig,v_stage,E)`.
- 7개 검사 / 6개 의미군 / 별도 오류집합 `E`를 구별한다. 퀘스트 의미군에 자격·단조성 검사가 각각 있다. 파서는 선행 단계이며 일곱 번째 검사가 아니다.
- 실제 Python 반환형: `ValidationResult(valid, errors, checks_run)`. 7개 숫자 배열을 직접 반환하지 않는다. `checks_run`은 검사 이름이며 모두 통과했다는 뜻이 아니다.
- 서술문 `narrative_text`의 의미를 추출하거나 선언되지 않은 함의를 검사하지 않는다. 구조화 후보의 선언 충실성은 별도 검증 과제다.

출처: `paper/latex/en/main.tex:73–82`, `paper/latex/ko/main.tex:123–144`, `src/nesy_game/contracts.py:175–207`, `src/nesy_game/validator.py:7–146` (아래 경로는 모두 연구 루트 `neuro-symbolic-interactive-game-research-2026/` 기준).

## 2. Codex와 모델 출처는 세 갈래다

| 역할 | 관찰된 근거 | 주장할 수 없는 것 |
|---|---|---|
| 논문·게임 제작 보조 | 원고는 LLM 보조 작성 사실을 공개한다. | 특정 작성 모델이 gpt-5.6-sol이었다는 사실은 조사한 근거로 확정할 수 없다. |
| 과거 E2 제안 생성 | `rq2-live-pilot/signal-repair-v2/policy_blind/summary.json`은 `gpt-5.6-sol`, `gpt-5.6-sol@codex-cli-unpinned-2026-08-28`을 기록한다. | 불변 provider revision 증명이나 최신 NPC 모델 식별 근거가 아니다. |
| NPC run-006 P 조건 | 인증된 Codex CLI/OAuth 경로의 24개 행은 requested/returned model이 null, available=false다. | 최신 NPC가 gpt-5.6-sol이라는 주장, 24 CLI 시도=원격 과금 호출 24회라는 주장. |

출처: `research/academic-pipeline/rq2-live-pilot/signal-repair-v2/policy_blind/summary.json:19–21`, `research/academic-pipeline/npc-goal-recovery/verified-run-006/screening-results.jsonl:1–72`, `paper/latex/generated/npc_results_en.tex:1–6`, `paper/latex/en/main.tex:263–264`.

## 3. 실제 온톨로지 문서 구조와 내용

레지스트리는 `TRACE-RPG-ONTOLOGY-001`, schema `1.0.0`이다. OWL/SHACL, 독립 의미 정답, 런타임 검색 시스템이 아니라고 파일 자체가 한정한다.

| 구성 | 실제 내용 | 실행상 지위 |
|---|---|---|
| `knowledge/ontology/trace-rpg-ontology.json` | ID·버전·범위·claim boundary, node_types, relation_types, 구조 제약, 한·영 competency questions | 어휘·문서 그래프의 규약; 게임 런타임이 읽는 권한 엔진 아님 |
| node_types | ActionType, Actor, Fact, Item, Location, Policy, Quest Stage 등과 연구 방법 문서 타입 | 게임 상태 어휘와 methods 문서 타입을 함께 선언 |
| relation_types | `layer`, `domain`, `range`, `validator_predicate` | 검사 의미군과 문서상 연결; 검증기를 자동 생성하지 않음 |
| constraints | 타입·관계 선언, 끝점 존재, domain/range 정합, 중복·자기 연결 금지 | 그래프 구조 적합성; 게임 의미의 완전성 보장 아님 |
| competency_questions | ID, question_en/ko, source_type, relation, target_type, required_sources, minimum_answers | 문서 그래프가 필요한 방법론 연결을 제공하는지 점검 |
| `curated-relations.json` | 사람이 작성한 typed edge와 근거 문서; 예: H2 repair-vs-retry → evaluated_by → repair-at-K | 저작된 연결; 독립 gold가 아님 |
| `knowledge-graph-schema.sql` | metadata, node_type, relation_type, node, edge, competency_question, benchmark_query, benchmark_candidate, strategy_run | SQLite 미러 및 비교실험 구조 |

실제 관계 예시:

```json
"authorized_by": {
  "layer": "game-state",
  "domain": ["ActionType"],
  "range": ["Policy"],
  "validator_predicate": "v_policy"
}
```

전체 game-state 매핑은 `authorized_by→v_policy`, `requires_precondition→v_pre`, `requires_reachable_item→v_reach`, `knows→v_know`, `forbids_disclosure→v_disc`, `advances_stage→v_quest`다. 마지막 항목은 두 퀘스트 검사의 **의미군**이다.

출처: `knowledge/ontology/trace-rpg-ontology.json:1–198`, `knowledge/concepts/trace-rpg-application-ontology.md:12–22`, `knowledge/ontology/curated-relations.json:1–19`, `knowledge/ontology/knowledge-graph-schema.sql:3–85`.

## 4. 7개 검사의 의미와 Python 구성

모든 검사 결과는 단위 없는 참/거짓이다. 확률·감정·품질 점수가 아니다.

| 형식 기호 | Python 이름 | 참이 되는 조건 | 검증기 줄 |
|---|---|---|---|
| `v_policy` | action_policy | 정책 존재, 필수 조건·효과 포함, 효과·단계 변경이 정책상 허용됨 | 21–70 |
| `v_pre` | precondition | 후보의 모든 전제조건이 현재 facts에 존재 | 72–80 |
| `v_reach` | object_reachability | 요구 물체가 inventory 또는 reachable_locations 안에 있음 | 82–92 |
| `v_know` | npc_knowledge | 사용·공개한 사실을 해당 NPC가 알고 있음 | 94–113 |
| `v_disc` | forbidden_disclosure | 공개 사실과 해당 NPC의 금지 사실이 겹치지 않음 | 115–124 |
| `v_elig` | quest_stage | 요구 단계 ≤ 현재 단계 | 126–134 |
| `v_stage` | quest_stage_monotonicity | 새 단계가 없거나 현재 단계 이상; 정책 허용 검사는 별도 | 136–144 |

`src/nesy_game/`의 역할은 다음과 같다.

- `contracts.py`: WorldState, ActionPolicy, CandidateAction, ValidationError, ValidationResult 및 공통 타입 파서.
- `codex_adapter.py`: 공개 가능 상태 projection → Codex 요청 → 비권위 후보 반환. 모델 이름은 호출자가 선택한다.
- `validator.py`: 현재 상태와 후보를 비교하고 오류 `code/entity/reason/repair_hint`를 생성한다. 오류 개수는 고정 7개가 아니다.
- `repair.py`: 해당 guided repair 구현은 후보와 오류만 사용하며 WorldState를 읽지 않는다. 다른 reference repair는 상태를 읽을 수 있다.
- `runtime.py`: 검증 → 제한된 후보 수리 → 재검증 → 커밋 직전 방어적 재검증 → 상태 변경. 소진 시 기존 상태를 보존한다.
- `kg_ontology_simulation.py`: 별도 methods 문서 그래프 추출·온톨로지 검사·연결 복원 비교. 게임 커밋 경로의 컴파일러가 아니다.

별도 시뮬레이션의 **7**은 알고리즘 7종이다. 점수 입력은 degree, lexical overlap, reciprocal path distance, type_fit의 **4개 특징**이며 진단 점수는 보정된 확률이 아니다.

## 5. 구체적 예: 기존 OPEN_DOOR 저장 기록

**저작된 적합성 fixture이며 이번 세션의 새 실행이나 라이브 모델 샘플이 아니다.**

| 단계 | 저장 기록의 내용 |
|---|---|
| 상태 | facts=`{met_guard, public_fact}`, quest_stage=1 |
| 정책 | OPEN_DOOR는 met_guard를 요구하고 door_open 효과를 요구·허용; 단계 변경은 허용하지 않음 |
| 제안 | preconditions=`{stale_guard_fact}`, effects=`{door_open}` |
| 첫 판정 | POLICY_PRECONDITION_OMISSION(met_guard), UNSATISFIED_PRECONDITION(stale_guard_fact); valid=false |
| 수리 | 전제조건 필드에서 stale_guard_fact를 제거하고 met_guard를 삽입; 효과는 보존 |
| 재판정 | errors=[]; valid=true |
| 커밋 | facts=`{door_open, met_guard, public_fact}`, 단계=1; state_id=`f7daa379a182212e` |

[INFERENCE — 저장 오류로부터 설명용 재구성] 7개 검사 순서로 쓰면 `(0,0,1,1,1,1,1) → (1,1,1,1,1,1,1)`이다. 이 벡터가 원시 기록에 직접 저장되어 있었다고 주장하지 않는다.

출처: `configs/pilot-manifest.json:25–86,365–385`, `research/academic-pipeline/stage-04-pilot/pilot-results.json:5649–5662,5777–5897`, `research/academic-pipeline/stage-04-pilot/repair-arms.md:3–6`.

## 6. 비교표: 의미 있는 관찰과 통계적 유의성을 구별

| 근거층 | 분모와 저장 결과 | 허용되는 해석 / 한계 |
|---|---|---|
| E1 저작된 오프라인 사례 | 조건별 12개: reject 0/12, unchanged retry 0/12, guided 5/12, state-reading reference 6/12 커밋 | 수리 가능·불가능 사례에서 설계한 메커니즘이 작동함. 독립 재생성 baseline 또는 일반적 효능 입증 아님 |
| E2 signal-v2/policy-blind | 동일 제안 5건: guided 5/5, unchanged retry 0/5 | 의도적으로 수리 가능한 조건의 서술적 결과 |
| E2 나머지 4개 cell | 각 5건; 3개 cell은 양쪽 5/5, goal-blind는 양쪽 0/5 | 유리한 cell만 선택하지 않는다. 총 25건; E1과 합산하지 않는다 |
| E3 온톨로지 문서 연결 | 저작된 target 6개: 선택된 S2 6/6, degree baseline 0/6; 7×6×5=210 scores | 동일 target으로 전략 선택·요약; 독립 test set, 런타임 이득, 의미 완전성 입증 아님 |
| NPC-SCR1 run-006 | 12사례×2반복×3조건=72행. 각 조건 24배정, 20완료, 4실패, 4 goal-reached | 고정 사례 계수. 실패는 저작된 stale-control 거부이며 O도 독립 의미 gold가 아님 |

현재 조사한 표에는 통계적 유의성, 모델 순위, 회복 효능, 플레이어 이득을 확정하는 근거가 없다. 'publishable' 패킷 상태는 그러한 주장을 허용한다는 뜻이 아니다.

출처: `paper/latex/generated/pilot_tables_en.tex`, `live_pilot_tables_en.tex`, `npc_tables_en.tex`, `npc_results_en.tex`, `npc_validation_reports.json`, `paper/latex/en/main.tex:193–206`.

## 7. 시각자료와 게임 연결의 현재 경계

- [기존 구조도](../../../neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_architecture.png): 7 checks / 6 families와 commit·repair·fallback 구조. 설명도이며 실행 캡처가 아니다.
- 기존 결과 대비도 (capture unavailable in checkout: `../../../neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_evidence_regimes.png`): E1·E2 분모와 null regime 분리. 통계 추론 그래프가 아니다. 이 과거 그림의 원본은 현재 미확보이며 다른 그림으로 대체하지 않는다.
- Godot 대시보드는 POLICY/PRECONDITION/REACHABILITY/KNOWLEDGE/DISCLOSURE/QUEST STAGE의 **6개 군**을 표시한다. `pass/fail/skipped/out_of_scope`는 서로 다르며 missing을 pass로 바꾸지 않는다.
- 현재 표시 trace는 Godot hard writer 판정을 별도 EvaluationTrace가 재구성한 미러다. 온톨로지 추론 또는 Python의 7개 결과를 그대로 전달하는 계측이 아니다.
- E1/E2 핵심 Python hard-policy 승인 왕복은 현재 게임에 구현되어 있지 않다. 기존 ENG1은 Godot 지역 정책 미러다. 별도 NPC 경로는 Codex 의도 → Python claim 검증·공개상태 계획 → Godot 권한 검사·상태 기록이다.
- 기존 2026-10-14-r2 캡처는 저장 해시와 일치하는 역사적 그림이다. 현재 소스 캡처로 재표기할 수 없다.
- 이번 세션에서 기존 `fig_architecture.png`와 `fig_evidence_regimes.png`를 직접 열어 확인했다. 결과 대비도는 일부 막대가 `Guided rho`·`State oracle` 라벨을 덮는다. 최종 그림은 가독성을 고치고, 설명도·저장 결과·실행 캡처의 지위를 각각 캡션에 명시해야 한다. 새 게임 실행을 확인한 것은 아니다.

출처: `game-track/web/dashboard/dashboard.js:38–67,126–142,539–576`, `game-track/godot/scripts/game3d/evaluation_trace.gd:4–120`, `game-track/godot/scripts/sealed_lighthouse_machine.gd:46–90,149–206`, `game-track/design/paper-crosswalk.en.md:18–94` 및 studio 계약.

### 새 근거 그림 후보 — 아직 실행하지 않음

동일한 `reveal_hint(captain_mira,tide_marks_hint)` 요청을 렌즈 장착 전후에 비교한다. 이 단서는 단계 2부터 허용되지만 keeper secret은 영구 금지이므로 두 사실을 바꿔치기하지 않는다. 후보 그림은 다음 사슬을 한 trace ID로 연결해야 한다.

`온톨로지 관계/버전 → 상태·정책 필드 → 후보 → 실제 검사 → 오류/보류 → 합법적 중간 행동 → 동일 후보 재검사 → 커밋 → 상태 hash/revision 변화 → UI 표시`

이 그림을 현재 구현의 증거로 삼으려면 실제 실행·소스 바인딩이 필요하다. 관계가 문서상 설명에 그친다면 그림에도 그렇게 표기한다.

## 8. 확인된 불일치와 미해결 항목

1. `knowledge/concepts/commit-gate.md:11–13`은 6개 의미군+E를 7-튜플로 설명한다. 현재 원고의 7개 검사+E와 숫자 의미가 다르다. 관련 개념 문서도 함께 정합화할 필요가 있다.
2. 소스 감사에서 hard writer SHA-256=`48da35d485473abfa9805e0dddb80d6aa6bad5c0bd183c57541886e768f839c1`, 미러에 고정된 SHA-256=`cc531b6b93c066807eb628c0616d060a275a71d7f65c118983d2e8a90cc6b962`로 불일치했다. 바인딩 결함이며 그 자체로 게임 동작 오류를 증명하지는 않는다. 해시만 바꿔 해결되었다고 할 수 없다.
3. shared vault의 Proof012 현재성 표현은 원고의 run-006 선택/native012 historical과 충돌한다. 저장된 과거 PASS를 현재 검증으로 상속하지 않는다.
4. 선언되지 않은 자연어 함의, 독립 의미 라벨, 예산을 맞춘 새 제안 재생성 baseline, 통계 검정·인간 평가, 현재 모델 revision은 미확보다.

## 9. 보조 리뷰와 인터뷰 결정

- 로컬 3개 독립 감사: 원고·모델 출처 / 온톨로지·Python / 게임·시각자료. 소스·저장 패킷·이미지·해시를 조사했으며 새 게임 실행이나 전체 테스트는 수행하지 않았다.
- Jev API 호출은 `jev-1.14.0` 응답을 받았다. `proposal_only`; evidence_supports=0.72가 설정 threshold=0.80 미만이다. 연구 근거를 승인한 결과가 아니며 논문 실험에 포함하지 않는다.
- Aside 및 Argon 리뷰는 별도 intake로 관리한다. 외부 리뷰가 E1/E2 Python 게이트와 Godot 경로를 하나로 묶으면 현재 소스와 충돌하므로 **미구현 제안**으로만 취급한다.
- 원고·게임 실행 코드는 아직 변경하지 않았다. 한·영 동시 개정과 영향받는 게임 개선은 인터뷰 합의 후 수행할 범위다.

**첫 질문:** 이번 논문 심화와 게임 수정의 주된 관찰·검증 대상은 ① 게임 속 NPC·세계 상태·행동과 검증·수리 과정, ② 게임을 개발하는 코딩 에이전트의 작업 과정, ③ 모델 내부 잠재 상태 중 무엇인가?

현재 구현에 직접 대응하는 대상은 ①이다. ②는 보조적인 제작 출처 정보만 있으며, ③의 내부 상태 계측은 없다. 향후 연구 대상을 고르는 일은 현재 자료가 대신 결정할 수 없는 사용자의 선택이다.

**사용자 확정 답변 (2026-10-22 세션, 질문 도구): ① 게임 속 NPC·상태·행동.** 코딩 에이전트는 제작 출처로 구분하고, 모델 내부 잠재 상태 측정은 이번 주 연구 대상에서 제외한다. 이 선택은 온톨로지 런타임 연결·새 효능 주장·구현 착수의 승인이 아니다.

**① 선택 후의 다음 결정:** 온톨로지를 현 구현을 설명하는 문서로 유지할 것인가, 아니면 버전 있는 관계·정책 규약을 실제 게임의 허용 행동과 상태 전이에 연결하고 그 실행 추적을 핵심 기여로 삼을 것인가? ① 선택만으로 런타임 확장까지 승인된 것은 아니다.

**두 번째 사용자 확정 답변 (질문 도구): ② 한정된 실행 계약.** 선정한 행동 범위의 온톨로지 관계·정책을 실제 게임 검증에 연결하고, 계약→검사→오류·수리→상태 전이의 근거를 한·영 논문에 함께 반영하는 방향을 선택했다. 현 레지스트리가 이미 실행 권위를 가진다는 뜻이 아니다. 행동 범위·중심 연구 주장·비교 조건·성공 기준은 인터뷰에서 추가 결정하며, 아직 코드·원고 구현에 착수하지 않았다.

검토 제안: 추적 가능한 실행 연결을 우선 비교하되, 생성·수리 효능 및 플레이어 이득은 독립 비교실험 전까지 미검증 주장으로 남긴다. 일반적 runtime assurance 원리 자체를 새 기여라고 주장하지 않는다.

**세 번째 사용자 확정 답변 (질문 도구): 선언된 규칙의 집행·추적.** 핵심 검증 대상은 금지된 상태 변경 차단과 온톨로지 계약→검사→오류·수리→실제 게임 상태 변경의 재현이다. 구조화 오류의 수리 효능이나 행동 간 일반화는 이번 선택으로 입증된 것이 아니며, 핵심 주장으로 선택되지 않았다. 첫 대상 행동과 성공 기준은 아직 정하지 않았고, 한·영 원고 및 게임 코드 구현은 아직 시작하지 않았다.

### 첫 행동 범위: NPC 정보 공개 확정

- **네 번째 사용자 확정 답변 (질문 도구): ② NPC 정보 공개.** 첫 검증 행동은 `reveal_hint` 정보 공개로 한정한다. 아이템 거래·퀘스트 단계 변경으로의 일반화는 이 선택에 포함하지 않는다.
- 검토 권고는 ②다. Godot `sealed_lighthouse_machine.gd:46–90,184–206`의 `reveal_hint`는 금지 정보·단계·행위자·지식 보유를 검사하고, 허용 시 `facts`와 NPC `disclosed`를 갱신한다. 일부 보조 의견의 “정보 공개는 로그만 남긴다”는 전제는 이 소스와 맞지 않아 채택하지 않는다.
- 재사용 범위 정정: 현재는 `captain_mira`와 `tide_marks_hint` 한 쌍에 고정된 fixture 경로다. 행위자 적격성(`sealed_lighthouse_machine.gd:190`, `evaluation_trace.gd:86`), 공개 인자 바인딩(`game_3d.gd:3148,3186,3709`), 기억 항목(`sealed_lighthouse_machine.gd:200–201`)이 코드 리터럴이므로 온톨로지 실행 계약으로 옮겨야 한다. 기존 정책 검사 논리는 출발점이지만 완성된 선언형 계약을 재사용하는 것은 아니며, ①·③보다 구현 변경이 작다고 확정할 근거는 없다.
- ①은 명시적 소유권·양측 이전 계약을 새로 정의해야 한다. ③은 기존 획득·설치의 단계 변경을 활용할 수 있지만, 사용자 연구 우선순위는 소스만으로 결정할 수 없다.
- 이 권고는 실행 시험이나 온톨로지 런타임 연결의 증거가 아니다. 선택 후 실험 단위, 반증 조건, 비교군, 실제 커밋 권위와 재현 기준을 확정해야 한다.

### 다섯 번째 확정: 허가된 사실만 대사로 표시

- 사용자 확정 답변(질문 도구): **허가된 사실만 대사로 표시**. 공개 기록 변경만 통제하는 방식이나 자유 생성 대사에 의미 판정기를 붙이는 방식은 이번 첫 연결의 선택이 아니다.
- 선택한 범위는 canonical fact ID와 검증된 정형 템플릿으로 플레이어 대사를 구성하고, 허가되지 않은 사실이 공개 상태나 표시 대사에 들어가지 않는지 함께 검증하는 것이다. 표현 자유도는 제한한다.
- 이 보장 범위는 선언된 사실·허가 규칙·승인된 템플릿의 폐쇄된 표시 경로에 한정한다. 자연어 전체의 암묵적 함의, 우회적 추론, 모든 UI 채널의 정보 유출 방지를 증명한 것으로 확대하지 않는다.
- 아직 구현·새 실행 검증·원고 개정은 수행하지 않았다. 비교군은 아래 여섯 번째 결정으로 확정됐으며, 평가 독립성과 정량적 성공 기준은 미결정이다.

### 여섯 번째 확정: 일반 규칙 구현을 포함한 세 비교군

- 사용자 확정 답변(질문 도구): **일반 규칙 구현까지 비교**. 동일 상태·후보 사실·표시 템플릿을 제공하는 무검사, 일반 타입/명시적 정책 코드, 온톨로지 기반 게이트의 세 비교군을 포함한다. 무검사 비교군은 격리된 평가에서만 실행한다.
- 같은 규칙을 정확히 구현한 두 게이트는 같은 판정을 해야 한다. 위반률만으로 온톨로지의 추가 기여를 주장하지 않는다. 동일 규칙 판정 일치와 규칙 변경 시 수정 범위·누락·추적성을 함께 측정한다.
- 구조화된 오류 제공에 따른 수리 효과의 별도 인과 실험은 선택하지 않았다. 온톨로지 우월성, 사람의 개발 시간 단축, 일반화는 이 선택으로 확정되는 결과가 아니다.
- 독립 기대값/held-out 규칙 변경 구성과 정량 수용 기준은 다음 결정이다. 새 실험·원고·게임 개정은 아직 수행하지 않았다.
- 기존 Ouroboros 세션에 누적 선택과 이번 답변을 제출했으나 호출이 30초 시간 초과됐다. 서버 저장 여부는 별도 확인 전까지 미확인이다. 이 로컬 기록은 질문 도구에서 관측한 사용자 선택을 보존한다.

### 평가 기준 제안과 계정 재시도 요청의 구분

- 현재 사용자 요청은 사용자가 지정한 별도 인증 계정으로 Argon 리뷰를 다시 시도하는 것이다. 평가 독립성, 표본 수, seed, 수용 임계값 또는 새 실험 실행에 대한 승인은 아니다.
- 보조 검토의 평가 설계는 아직 제안이다. 세 비교군에는 동일한 기대 판정과 분모를 적용하지만, 의도적으로 검사를 제거한 무검사군에는 무위반 통과를 요구하지 않는다. 그 군의 위반·오차는 관측값으로 보고한다. 생산용 두 게이트에 적용할 통과 기준도 사용자 결정 전에는 확정하지 않는다.
- 별도 평가 에이전트를 배정하는 것만으로 독립 인간 정답이나 접근이 분리된 holdout이 성립하지 않는다. 기대표의 작성 근거·동결 시점·접근 경계와 replay 동일성 기준이 남은 결정이다.

### 일곱 번째 확정: 규칙 기반 검증부터 완성

- 사용자 확정 답변(질문 도구): **규칙 기반 검증부터 완성**. 별도 검증 subagent가 선언된 규칙에서 사례별 기대 판정표를 작성하고 구현 전에 동결하는 방식을 선택했다.
- 기대값은 온톨로지 게이트의 출력에서 복사하지 않는다. 세 비교군에 동일한 사례와 기대값을 적용하고, 무검사군의 위반은 관측값으로 보고한다.
- 이 단계의 근거는 규칙 준수·추적성·규칙 변경 누락에 대한 제한된 공학 검증이다. 별도 에이전트의 작성만으로 독립 인간 정답, 접근이 분리된 holdout 또는 사람의 이득이 성립하지 않는다. Jev는 보조 검토이며 정답·커밋 권한을 갖지 않는다.
- 정량 수용 기준과 동결할 사례 범위는 아직 확정 전이다. 이 답변을 새 실험 결과나 원고·게임 개정 완료로 해석하지 않는다.

### 구현 전 도메인·규칙변경 검토안 — 아직 사용자 승인 아님

- `DisclosureDesignCheck`의 소스 검토안은 `captain_mira` 1명 × 선언된 사실 ID 4개 × 기준 단계 `{0,1,2}` × 지식 보유/부재로 **24건의 부분 조합**을 제안했다. 이 수에는 사용자 여덟 번째 결정의 행위자 적격성·기공개 여부 축이 반영되지 않았으므로 전체 전수 사례 수로 사용할 수 없다. 최종 분모는 모든 합의 축과 별도 잘못된 입력 층을 반영해 구현 전에 동결한다.
- 격리된 평가 fixture에서만 `tide_marks_hint.minimum_stage: 2→3`을 바꾸는 단일 규칙 변경을 제안한다. 실제 게임의 진행 규칙 변경을 뜻하지 않는다. 기준/변경 계약에 같은 사례를 짝비교하고 새 허용 경계 `stage=3`도 검사한다. 위 부분 조합에 단계 3만 추가한 수는 32건이나, 이것도 전체 분모는 아니다. 두 유효 게이트는 동결된 모든 동일 사례를 실행하며 무검사 arm은 위반 건수를 보고한다.
- 기대 판정은 별도 검증 subagent가 구현 전 선언 규칙에서 작성·동결한다. 게이트 산출물 복사나 독립 인간 gold라는 명칭은 허용하지 않는다. 규칙 변경 때 일반 코드 arm의 조건 수정과 온톨로지 arm의 선언 수정 범위·누락을 각각 기록하며 온톨로지 우월성을 사전 가정하지 않는다.
- 기공개 사실의 재요청 동작은 아래 아홉 번째 사용자 선택으로 확정됐다. 현재 `_reveal_hint`와 `apply_operation`은 그 선택을 아직 구현하지 않는다. 현재 성공 경로는 `revision`을 먼저 증가시키므로 `mutated=true`를 재공개 탐지나 멱등성 근거로 사용하지 않는다.
- 근거: `game-track/godot/data/sealed_lighthouse.json:24-59`, `game-track/godot/scripts/sealed_lighthouse_machine.gd:58-86,184-206`. 새 실험·기대표 동결·원고 또는 게임 구현 완료를 뜻하지 않는다.

### 여덟 번째 확정: 현 시나리오의 선언 조건 전수

- 사용자 확정 답변(질문 도구): **현 시나리오 조건 전수**. 새 NPC나 스토리를 추가하지 않고 현재 선언된 사실·공개 정책·퀘스트 단계와 행위자 적격성·지식 보유·기공개 여부의 유한 조건표를 검증한다. 경계·잘못된 입력 사례는 별도 층으로 구분한다.
- 사례 수와 분모는 선언에서 산출하여 구현 전에 동결한다. ‘전수’는 이 선언 조건표에만 적용하며 모든 도달 가능한 게임 상태, 자유 자연어, 다른 행동이나 게임의 일반화로 확대하지 않는다.
- 질문에 제시한 수용 기준: 두 게이트는 동결된 모든 사례의 기대 허용·거부 판정과 일치한다. 거부 시 공개 상태와 플레이어 대사에 금지 사실을 추가하지 않는다. 계약 버전·규칙 ID·검사·오류·상태 변경을 연결한다. 같은 초기 상태·계약·후보의 재생은 판정·공개 상태·표시 대사가 동일해야 한다.
- 세 비교군은 같은 사례·기대값을 사용한다. 의도적인 무검사군에는 무위반 통과를 요구하지 않고 실제 위반 수를 기록한다. 일반 코드와 온톨로지 게이트에는 같은 규칙 변경을 적용하고 수정 범위·누락을 보고한다.
- 별도 검증 subagent의 기대표 동결, Jev의 보조 의견 경계, 독립 인간 정답·접근 분리 holdout·인간 이득을 주장하지 않는 조건은 유지한다. 구체적 규칙 변경 fixture와 개수는 선언을 근거로 정해 같은 동결 패킷에 포함해야 한다.
- 위 내용은 합의된 설계이며 시험 통과 결과가 아니다. 최종 목표 재진술·Seed 승인 및 원고·게임 구현은 아직 수행하지 않았다. 최신 Ouroboros 답변 제출도 30초 시간 초과로 끝나 서버 저장 여부는 미확인이다. 이 로컬 기록의 여덟 결정을 누락한 Seed를 승인하지 않는다.

### 아홉 번째 확정: 현재 권한을 재검사하고 대사만 다시 표시

- 사용자 확정 답변(질문 도구): **대사만 다시 표시**. 이미 공개한 사실을 다시 요청받으면 현재 공개 조건을 재검사한다. 여전히 허용되는 경우 정형 대사는 다시 표시하되 `facts`, NPC `disclosed`, 관계 기억, `revision`과 canonical state hash는 바꾸지 않는다. 요청과 판정은 canonical 게임 상태 밖의 추적에 남긴다.
- 기공개 이력은 권한 우회가 아니다. 현재 영구 금지·단계·행위자·지식 조건을 통과하지 못하면 재표시도 거부한다. 이 선택은 앞으로 구현할 계약이며 현재 런타임이 멱등하다는 관측 결과가 아니다.
- 검증 subagent의 추가 도메인안은 적격 NPC 1명 × 사실 4개 × 단계 3개 × 지식 보유/부재 × 기공개 여부의 48개 조합이다. 이는 **적격 행위자 층의 제안 수**이지 전체 분모나 실험 결과가 아니다. 합의된 행위자 적격성 축과 잘못된 입력·경계 층을 모두 명시해 별도 검증 subagent가 전체 기대표·층별 분모를 구현 전에 동결해야 한다. 도달 가능 상태의 전수라고 부르지 않는다.
- 규칙 변경 검토안은 격리 fixture의 `tide_marks_hint.minimum_stage: 2→1` 및 별도 fixture의 영구 금지 목록에 `tide_marks_hint` 추가다. 두 변경을 각각 기준과 짝비교하며, 실제 게임의 이야기·진행 규칙은 바꾸지 않는다. 이 안은 위 2→3 초안의 대체 제안으로 최종 목표 재진술에 포함할 사항이며 아직 사용자 승인된 실험 결과가 아니다.
- 현재까지 아홉 사용자 선택을 확보했다. 최종 목표 재진술·Seed 승인과 원고·게임 구현은 아직 미완료다.

### 당시 기록: Seed 문서 검토 완료·구현 승인 대기 (2026-10-23, §11로 상태 갱신)

- 아홉 인터뷰 결정과 기존 여덟 동작 기준을 유지한 Seed v1.1.0을 준비했다: `.ouroboros/seeds/seed-20261023-npc-disclosure-37ffdf78a47d.yaml`.
- 사용자가 채택한 A/B 보완에 따라 아홉 번째 수용 기준 `ac_5ec891277d116f3c`를 추가했다. 온톨로지 구조·내용, Python/Godot 역할·경계, 시그널 그림·의미, 세 비교군 근거표, 한·영 원고, 게임 변경·검증 대응표의 여섯 산출물을 모두 요구하며 소스·원자료·실행 근거와 연결한다. 미지원 주장을 제외하는 것으로 산출물 누락을 면제하지 않는다.
- Ouroboros QA 호출의 시간 초과 후 읽기 전용 `SeedLocalQA` subagent가 문서만 재검토했다. iteration 1은 0.84로 수정 필요, iteration 2는 0.95로 문서 기준 0.90을 통과했다. 근거: `.ouroboros/artifacts/seed-37ffdf78a47d-qa-iteration-2.json`.
- `shasum -a 256 .ouroboros/seeds/seed-20261023-npc-disclosure-37ffdf78a47d.yaml` 결과는 `3e601c02f44f64c90715254a9376e7c97c638f92dd27479ecb1e3df7592b81e2`이며 QA 기록과 일치한다. YAML 파싱 및 기존 기준 보존 검증은 해당 QA 기록의 구조 검증 항목에 남아 있다.
- 문서 QA 통과는 구현 승인이나 실험 통과가 아니다. 최종 실행 승인은 아직 없고, 기대표·층별 분모·규칙 변경 fixture의 구현 전 동결 및 새 원고·게임 구현·검증은 미완료다. 이전 절의 미확정 상태는 결정 당시 기록으로 보존한다.

## 10. 외부 검토와 투고지 조사 상태

- Aside 외부 리뷰는 수집 완료된 **미검증 intake**다. 실제 사용 모델을 확인하지 못했으며, 최초 요청한 `openai/gpt-5.6-sol`은 해당 계정에서 이용 불가였다. 외부 리뷰의 통합 Python→Godot 경로 해석은 현재 소스 감사보다 우선하지 않는다.
- 최초 계정의 Argon Deep Research는 시작 확인 후 **사용량 한도로 미완료**다. 최종 보고서와 완료 응답의 모델 식별자는 확보하지 못했다. “117개 웹사이트 조사 중”은 진행 UI일 뿐 검증된 인용·종합 결과가 아니다. 비활성 Flash-Lite 표시도 대체 모델 실행의 증거가 아니다.
- 원문/상태 근거: `neuro-symbolic-interactive-game-research-2026/research/deep-research/reviewer-intake/2026-10-22/aside-review.json`, `aside-review.txt`, `argon-review.txt`. Argon 담당자의 방법론 우려는 로컬 검토 의견이며 미완료 Argon 보고서의 결론으로 인용하지 않는다.
- 인터뷰에 반영할 근거 경계: 온톨로지의 추가 가치는 typed-state+explicit-policy 비교군 없이 입증되지 않는다. 7개 검사는 6개 의미군에 대응하며 충분성·비중복성 자체는 별도 검증 대상이다. 현재 근거는 제한된 규칙 집행·추적 주장만 지원하며, 효능·독립 의미 정답·사람의 이득을 입증하지 않는다.
- 5개 투고지 문서는 `neuro-symbolic-interactive-game-research-2026/research/deep-research/journal-targets/2026-10-22/`에 작성됐다: IEEE Transactions on Games, Knowledge-Based Systems, IEEE Transactions on Affective Computing, Information Sciences, Expert Systems with Applications. 문서의 실험 제안은 계획이며 관측 결과가 아니다. 미확인 JCR 지표와 현재 투고 준비도는 확인된 것으로 취급하지 않는다.
- 사용자가 지정한 별도 인증 계정의 재시도는 접수됐다. 2026-10-22T23:14:35.891Z 브라우저 관측에서 계정 표시, Argon 선택, Deep Research 선택과 “웹사이트 48개 조사 중”을 확인했다. 최종 보고서는 아직 관측되지 않았다. 48은 검증된 인용 수가 아니며, 실제 반환 모델 revision도 미확인이다. 최초 계정의 사용량 제한을 이 재시도의 실패로 해석하지 않는다.
- 재시도의 상태·진행 캡처는 reviewer-intake의 비공개 로컬 자료로 보존한다. 계정 식별자, 식별자를 포함한 파일명, 개인 대화 URL은 공개 기록에서 제외했다. 새 중복 조사는 제출하지 않았다.

## 11. 승인된 한정 구현과 현재 증거 상태 (2026-10-23)

**보고서 동결 시점: 구현 present / 최종 checker·PDF closure pending.** 승인된 Seed `.ouroboros/seeds/seed-20261023-npc-disclosure-37ffdf78a47d.yaml`에 따라 Python 평가와 Godot `reveal_hint` 실행·정형 표시 경로의 구현이 존재한다. 앞 절의 ‘최종 구현 승인 대기’는 이전 시점 기록이다. Main이 보고한 초기 smoke는 Python 결정론 평가 PASS와 staged Godot 8/8이다. 아래 최신 focused 검증은 36 passed이며, 최종 재생성·checker·PDF 결과는 연구 루트의 `research/npc-disclosure/final-verification-20261023.json`에 Main이 기록한다. 이 보고서도 생성 입력의 소스 해시에 포함되므로 최종 receipt를 받기 위해 본문을 다시 고쳐 순환적인 stale binding을 만들지 않는다.

### 동결 입력과 해석 범위

- 별도 `DisclosureFreeze`가 선언에서 작성한 `research/npc-disclosure/reveal-hint-expectations-v1.json`은 `FROZEN_EXPECTATIONS_NOT_RUNTIME_RESULTS`다. 정상 48, 경계 4, malformed 8을 분리하며, 두 규칙변경 fixture의 네 짝비교 사례는 별도다. 이는 동결 조건표의 분모이지 모든 도달 가능한 게임 상태의 전수가 아니다.
- 문서 담당자가 실행한 `shasum -a 256 .ouroboros/seeds/seed-20261023-npc-disclosure-37ffdf78a47d.yaml neuro-symbolic-interactive-game-research-2026/research/npc-disclosure/reveal-hint-expectations-v1.json`은 exit 0이었다. Seed=`3e601c02f44f64c90715254a9376e7c97c638f92dd27479ecb1e3df7592b81e2`, 기대표=`9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028`; 기대표 sidecar와 일치한다. 원시 자료·동결 기대값·과거 실행 패킷은 수정하지 않는다.
- 기대표의 `source_hashes`는 구현 전 출처다. 수정된 실행 소스의 해시를 여기에 덮어쓰거나 이전 소스와 같다고 주장하지 않는다. 현재 실행 바인딩은 별도 결과 metadata와 Godot receipt에서 확인해야 한다.

### 여섯 산출물의 경로

아래 경로는 연구 루트 `neuro-symbolic-interactive-game-research-2026/` 기준이다. `paper/latex/generated/disclosure_producer_manifest.json`의 `six_deliverables`가 여섯 범주와 입력·출력·ID를 연결한다. 파일 존재, 양언어 input과 table/figure label은 직접 확인했다. 표의 pending은 이 보고서 동결 시점이며, 이후 최종 판정은 별도 final-verification receipt가 갱신한다.

| 필수 범주 | 현재 산출물과 근거 연결 | 현재 판정 |
|---|---|---|
| 온톨로지 구조·내용 | `research/npc-disclosure/reveal-hint-expectations-v1.json`의 scope/rule_ids/approved_templates/integration_contract → `paper/latex/generated/disclosure_tables_en.tex`, `disclosure_tables_ko.tex`의 `tab:disclosure-contract` | 동결 선언 근거 연결; 최종 gate pending |
| Python/Godot 역할·경계 | `src/nesy_game/disclosure.py`, `game-track/godot/scripts/sealed_lighthouse_machine.gd` → `paper/latex/generated/disclosure_results_en.tex`, `disclosure_results_ko.tex` | Python은 동결 계약 평가, Godot은 실제 실행·상태 변경 권한; 핵심 Python E1/E2 게이트의 실시간 왕복으로 표현하지 않음 |
| 원자료 기반 시그널·범례 | `research/npc-disclosure/results-current/disclosure-trace.jsonl` → `paper/latex/figures/fig_disclosure_signals.svg`, `.png`, `.pdf`, `fig:disclosure-signals` | expected-match·replay·policy-check의 PASS/FAIL/SKIPPED; 외부 Boolean 검사이며 모델 잠재 상태·확률·품질 점수 아님 |
| 세 비교군 근거표 | `research/npc-disclosure/results-current/comparison-summary.json` → 두 `disclosure_tables_*.tex`의 `tab:disclosure-arms` | 일반/온톨로지 60/60 일치; 각각 unsafe 0. 격리 무검사군의 실제 unsafe는 51/60이며 semantic mismatch 60/60과 구별 |
| 한·영 동시 개정 | `paper/latex/en/main.tex` → `paper/latex/en/main.pdf`; `paper/latex/ko/main.tex` → `paper/latex/ko/main.pdf`; 양언어 `disclosure_results_*.tex`, `disclosure_tables_*.tex` | 소스·PDF 경로 및 대응 label 확인; 수치 교정 전 빌드는 최종 증거가 아니며 동결 후 빌드·동등성·시각 검토 receipt pending |
| 게임–fixture 대응 | 기대표·comparison summary·`game-track/godot/data/sealed_lighthouse.json` → 두 `disclosure_tables_*.tex`의 `tab:disclosure-fixtures`; `research/npc-disclosure/results-current/godot-receipt.json` | 규칙변경 2개/짝비교 4개가 기대와 일치하고 누락 없음. 실제 Godot receipt는 passed=true/failures=[] 및 packet/source/state hash를 포함; 최종 checker pending |

### 관측된 명령과 결과

Main이 실행하고 문서 담당자가 출력 또는 결과 파일을 읽어 확인한 기록이다. 실행 cwd는 연구 루트다. 초기 32 passed/7.12s 및 34 passed/10.54s는 수정 과정의 이전 receipt이며 최신 결과를 대신하지 않는다.

| 확인 명령/기록 | 관측 결과와 한계 |
|---|---|
| `NPC_DISCLOSURE_RECEIPT_PATH=research/npc-disclosure/results-current/godot-receipt.json uv run pytest -q tests/test_npc_disclosure.py tests/test_godot_npc_disclosure.py tests/test_check_disclosure_paper_evidence.py tests/test_generate_disclosure_paper_results.py` | **36 passed in 9.11s**, `artifact://902` / raw `artifact://901`. 공개 재현 명령은 연구 루트 상대 경로로 치환했으며 원래 실행 명령의 바이트 동일본이 아님. M-007/M-008을 포함한 최종 네 파일 focused suite; project-wide suite·formatter·linter 실행으로 확대하지 않음 |
| `uv run python scripts/run_disclosure_evaluation.py --json` | `results-current/factual-summary.json`: PASS; 일반 규칙과 온톨로지 게이트가 각각 16 allow/44 deny, 기대·상태·표시·replay 실패 0; 두 게이트 60/60 일치; 규칙변경 2개/네 짝비교 기대 일치 및 누락 0 |
| `uv run python scripts/generate_disclosure_paper_results.py` | `artifact://884`에서 producer PASS 확인. 이후 이 보고서 동결과 최신 receipt를 반영한 재생성·드리프트 검사는 아직 별도 closure 필요 |
| `research/npc-disclosure/results-current/godot-receipt.json` | 실제 harness 결과, 동결 packet SHA와 현재 실행 source hash, 사례별 기대/관측·정형 display·prior/next state hash를 포함한다. Python 60사례 전수와 같은 Godot 분모로 읽지 않음 |
| `scripts/check_disclosure_paper_evidence.py`, 양언어 최종 PDF 빌드·동등성·시각 검토 | **동결 시점 pending**. 최종 정확한 명령·결과·현재 바이트 바인딩은 `research/npc-disclosure/final-verification-20261023.json`에서 확인하며, 파일 또는 성공 receipt가 없으면 완료로 간주하지 않음 |

### 검토 교정과 남은 검증

- 인터뷰 감사에서 구분한 **7개 Boolean 검사 / 6개 의미군 / 별도 오류집합 E**를 유지한다. 새 disclosure trace는 선택 행동의 실행 계약이며 기존 온톨로지 문서 그래프 전체가 게임 권한 엔진이 되었다는 뜻이 아니다.
- **실제 위험 계수 교정:** 초기 구현은 `expected_mismatch_count=60`을 unsafe와 혼동했다. 수정된 관측은 unauthorized allow 44 + redisplay mutation 7 = **unique unsafe 51**, strata별 정상41/48·경계2/4·malformed8/8이다. 나머지 9건은 허가된 fresh disclosure의 표현 불일치이며 unsafe에 더하지 않는다. 기대 의미 불일치 60 자체를 지우지 않으며 과거 실패·잘못된 계수는 수정 경위로 보존한다.
- **실행·그림 검토 교정:** Main이 전달한 disclosure trace 소비 경로 유실과 fail-closed replay 문제는 수정 후 위 focused suite로 재검증됐다. 문서 담당자는 실제 SVG가 expected-match/replay/policy-check 범례인데 두 원고 캡션이 allow/deny·fallback·mutation으로 설명한 불일치를 발견해 원고 담당자에게 전달했고, 담당자는 양언어 캡션을 실제 그림에 맞췄다. 최종 PDF에서의 반영 여부는 별도 build/visual receipt가 필요하다.
- **남은 closure:** 이 보고서 동결 후 evaluator/producer 재생성, authentic Godot receipt checker 및 여섯 산출물 gate, 양언어 PDF 최종 빌드·주장/label/수치 정합·시각 확인. 최종 결과는 unbound `research/npc-disclosure/final-verification-20261023.json`에 둔다. 이 절의 pending은 동결 시점 기록이며 후속 receipt와 repo index/log/task-manifest가 최신 상태를 가리킨다.
- **주장 경계:** 규칙 준수·추적성·재생·변경 누락의 한정 공학 검증만 다룬다. 독립 인간 gold, 접근 분리 holdout, 수리/모델 효능, 온톨로지 우월성, 개발시간 절감, 플레이어 이득, 모델 내부 상태 측정, 다른 행동·게임으로의 일반화를 주장하지 않는다. Jev·Aside·Argon은 보조 의견/intake이며 실험 정답이나 커밋 권한이 아니다.
- **Argon 후속 확인:** 비공개 reviewer-intake의 상태 캡처는 승인된 별도 계정 화면의 ‘48개 사이트 조사 중’과 `completed: false`를 기록한다. 일부 링크 패널은 최종 보고서·검증된 문헌 목록이 아니다. 최종 보고서/반환 모델 revision은 여전히 미확보이며 기존 partial-only 원본 기록을 로컬에 보존한다.
- **릴리스 경계:** strict-admitted006의 `READY_FOR_SELECTED_COMMIT`과 당시 82개 바이트·333 단위/78 게임/48 subtest·10쪽 PDF 기록은 **2026-10-17의 dated selected-source baseline**이다. 이번 수정 소스의 릴리스 증거로 승계하지 않는다. 이번 작업의 commit/push, clean release build, production deploy/browser 검증, 인간 효능 평가는 별도 미완료다.
