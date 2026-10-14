# 설계·실험 명세: 변화에 견디는 하이브리드 NPC 운영 시스템

## 상태와 검토 목적

- 상태: **설계 초안 / 사용자 검토 대기 / 프로토콜 미동결 / 구현 미승인**.
- 작성일: 2026-10-14. 인터뷰 ID: `trace-rpg-game-bound-agent-impact-20261014`.
- 대상 독자: 연구 책임자, 게임·에이전트 시스템 설계자, 후속 구현 담당자.
- 승인된 작업: 인터뷰를 설계·실험 명세로 정리하고 검토한다. 코드·한영 원고 변경, 실험 실행, 배포, 커밋·푸시는 포함하지 않는다.
- 명확성 기준: 20%, 출처 `default` (사용자 설정에 `ambiguityThreshold` 없음; 프로젝트 설정 파일 없음).
- 인터뷰 후 개념 미정 정도: 약 14%. 아래 점수는 설계 명확성 휴리스틱이며 성능·통계적 신뢰도·구현 준비도 점수가 아니다.
- 불변 연구·게임 운영 규칙은 저장소의 `AGENTS.md`와 `neuro-symbolic-interactive-game-research-2026/CLAUDE.md`가 우선한다.

## 1. 사용자 결정과 범위

| 항목 | 확정한 결정 |
|---|---|
| 설계 축 | 시스템 구조와 논문 주장·증거를 함께 결정 |
| 중심 판단 주체 | NPC 에이전트 |
| 핵심 성과 | 실패·플레이어/세계 변화 이후에도 원래 목표를 회복·추진 |
| 목표 권한 | 게임이 고정 목표와 성공 조건을 부여; NPC는 계획만 자율적으로 변경 |
| LLM 필요 역할 | 자연어·비정형 플레이어 상호작용 해석 |
| 계획 책임 | LLM은 의도 해석; 기호 계획기는 행동 선택·재계획 |
| 기여 중심 | 변화에 견디는 NPC 운영 시스템; 게이트 피드백 우월성을 선결론으로 두지 않음 |
| 첫 증거 환경 | 실제 Godot 게임의 턴·이벤트 기반 NPC; 같은 계약으로 자동 실험·리플레이 |
| 다음 산출물 | 설계·실험 명세 작성 후 검토; 구현은 별도 승인 |

두 개의 확정된 최상위 축은 모두 활성이다. `게임 에이전트 시스템`은 §§3–6, `논문 주장과 증거`는 §§7–9에서 다룬다. 뒤로 미룬 축은 없다.

### 목표

플레이어의 자유로운 표현과 게임의 상황 변화에 대응해, 고정된 게임 목표를 유지하면서 허용된 행동을 재계획하는 하이브리드 NPC를 설계한다. 의도 해석·계획·실행·상태 변경의 책임과 실패 원인을 분리해 검증한다.

### 비목표

다중 에이전트 협업, 자율 목표 생성, 새 기호 계획 알고리즘의 발명, LLM에 정식 상태 변경 권한 부여, 플레이어 경험·서사 품질의 효능 주장, 상용 실시간 성능 보장, 기존 파일럿을 새 NPC 성능으로 재명명하는 것은 이번 초안의 범위 밖이다.

## 2. 현재 구현과 새 설계의 차이

현재 근거의 소유 문서는 `neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/submission-optimization-2026-10-14.md`이다.

- `src/nesy_game/experiment.py`의 `run_experiment_case`는 제안 한 번 뒤 같은 prior state에서 `execute_with_repair`를 수행한다. 다음 게임 관측으로 목표 계획을 바꾸는 NPC 에피소드 루프가 아니다.
- `src/nesy_game/repair.py`의 `rho(a,E)`는 후보와 typed 오류만 읽는 국소 수리다. 변경된 세계를 읽는 재계획기나 NPC 기억으로 취급하지 않는다.
- `game-track/godot/scripts/game3d/game_3d.gd`는 제안을 로컬 `SealedLighthouseMachine.apply_operation`에 전달한다. 작성된 autoplay는 플레이어 입력을 대신하는 경로 실행이다.
- `scripts/project_experimental_bridge.py`는 JSONL을 stdout으로 투영하는 경로이며 라이브 양방향 연결이 아니다.
- 현재 상태 해시(`src/nesy_game/experiment.py:576–579`)와 의미적 리플레이(`src/nesy_game/runtime.py:402–403`) 근거는 존재한다. 새 설계에 필요한 것은 요청이 관측한 상태 식별자와 실제 승인 시점 상태의 비교·실패 분류이지, 기존 해시가 없다는 주장이 아니다.
- `src/nesy_game/metrics.py:35–40`에는 `valid_commit_rate`, `hard_violations_per_candidate`, `repair_at_k`가 이미 있다. `hard_violations_per_candidate`는 후보당 위반 **개수의 평균**이며 무효 후보의 비율이 아니다. 새 이름으로 중복 지표를 만들거나 0–1 확률로 해석하지 않는다.
- 두 `_safe_rate` 기반 지표도 빈 분모에서 구현상 0.0을 반환한다. 분석 표에는 후보 수와 `repair_successes` 집계 항목 수·실제 수리 시도 수를 함께 보고한다. 후보가 없는 `hard_violations_per_candidate` 또는 집계 항목이 없는 `repair_at_k`는 **undefined (`n=0`)**로 표시하며, 원래 함수의 0.0을 깨끗한 제안/수리 실패의 증거로 해석하지 않는다. 수리 미시도와 수리 실패도 구분한다. 기존 집계 항목 수를 실제 수리 시도 수로 간주하지 않으며, episode 계측의 수리 기회/시도 단위는 D-06에 동결한다.
- `src/nesy_game/experiment.py`의 `ProposalResponse`는 `provider_latency_ms`, `input_tokens`, `output_tokens`를 가진다. `AdapterFailure`와 `planned_experiment_assignment`/`summarize_experiment`에는 호출 전 배정·분류된 실패 보존의 근거가 있다. 이는 완성된 NPC episode 계측이 아니다. 새 회복·intent 정확도·freshness·deadline endpoint는 아직 없으며 구현 후 별도 검증해야 한다. 기존 adapter-failure의 zero proposal counters를 실제 소비량 0의 증거로 전용하지 않는다.

위 경로는 모두 프로젝트 디렉터리 `neuro-symbolic-interactive-game-research-2026/` 기준이다. 새 라이브 연결, NPC 목표 제어기, 의도 계약과 재계획은 **아직 구현·측정하지 않은 제안**이다. 현재 E1은 작성형 적합성, E2는 구성된 screening pilot, ENG1은 엔진 로컬 적합성이다. 기존 숫자와 `TODO-RESULT` 상태는 그대로 보존한다.

## 3. 권한과 Module 설계

물리적으로 엔진 프로세스 안에 LLM을 넣는 것이 목표가 아니다. 게임 이벤트·NPC 지식·허용된 도구·목표·실행 결과에 결합하는 것이 목표이며, 게임과 연구/에이전트 런타임은 분리한다.

```text
Godot: 게임 이벤트 + NPC에게 허용된 ObservationSnapshot + GoalContract
    ↓ 버전형 JSON
에이전트 런타임: LlmIntentInterpreter → TypedIntent
    ↓ 형식·근거·권한 검토
SymbolicPlanner: 고정 목표 + 검토된 PlanningContext + 허용된 관측에서 계획/재계획
    ↓ 버전형 행동 Proposal
Godot: freshness 검사 + 결정론적 hard 검사 → commit 또는 HOLD
    ↓ ActionResult + 새 관측/상태 식별자
에이전트 런타임: 다음 판단, 종료 또는 기록된 안전한 실패
```

| Module | 책임 | 갖지 않는 권한 |
|---|---|---|
| 게임의 목표 소유자 | `GoalContract`와 성공 predicate·목표 버전을 정의 | LLM 응답으로 목표를 바꾸지 않음 |
| ObservationProjection | NPC에게 허용된 현재 관측·공개된 근거만 제공 | 비공개 세계·다른 NPC 기억의 우회 공개 |
| ClaimMemory | 발언·추정과 검증된 근거를 출처별 보관 | 플레이어 발언을 정식 fact로 직접 승격 |
| LlmIntentInterpreter | 비정형 표현을 불확실성·근거를 포함한 `TypedIntent`로 제안 | 정식 상태·목표·policy를 변경 |
| SymbolicPlanner | 게임 목표 아래 허용된 행동을 선택·재계획 | NPC가 모르는 사실을 참으로 가정 |
| GoalController | 의미 있는 이벤트의 순서·예산·취소·재관측·종료를 관리 | 유효성 승인 또는 렌더 루프를 대체 |
| 정식 게임 commit gate | 승인 시점의 상태와 hard constraints를 검사하고 원자적으로 승인 | LLM 판단을 승인 근거로 대체 |
| Trace/Replay | 원인·결과와 상태 연결을 기록·검증 | 기록이나 에이전트 기억을 별도 상태 권위로 사용 |

계획기와 게이트가 같은 최신 상태와 완전한 제약을 공유하면 gate-HOLD가 드물 수 있다. 이를 보이기 위해 계획기를 일부러 약화하거나 잘못된 행동을 만든다고 가정하지 않는다. 부분 관측·계획 후 상태 변화·잘못된 의도 해석·실행 실패를 서로 다른 원인으로 기록한다.

## 4. 제안하는 Interface 계약

아래는 필요한 의미 계약이다. 스키마 번호·필드 타입·직렬화와 실제 저장 위치는 프로토콜 동결 시 정한다. 기존 동결 스키마를 덮어쓰지 않는다.

| 계약 | 필수 의미 |
|---|---|
| `GoalContract` | NPC/goal ID, 목표 버전, 게임 소유 성공 predicate, 종료·포기 권한 |
| `ObservationSnapshot` | episode/NPC/event ID, 논리 상태 revision, canonical hash, 허용 관측, policy/visibility 버전 |
| `UntrustedClaim` | 발언/주장 ID, speaker·출처, 원문 또는 hash/reference, verification 상태, 근거·반박 연결 |
| `TypedIntent` | 발언 reference, 의도·대상 reference, 요청/선호, 근거 reference, 불확실성/해석 보류; goal 변경 필드 없음 |
| `Plan` | plan ID, intent ID, PlanningContext digest, 목표·관측 버전, 단계·전제, 기호 계획기 버전, 남은 예산 |
| `Proposal` | actor·goal·plan/action ID, 의도·근거 reference, `expected_revision`, `expected_state_hash`, 허용된 행동 payload |
| `ActionResult` | executed/held/stale/cancelled/timeout/no-route 등 구분, 안전한 typed 이유, prior/next revision·hash, 실행 근거 |

### 상태 신선도와 원자적 승인

게임이 상태 식별자를 발급한다. hash가 같은 값으로 되돌아오는 경우에도 이벤트 순서가 구별되도록 revision 의미를 정한다. 표현상 변화와 정식 상태 변화를 구분하고, no-op/HOLD의 revision 처리도 동결한다.

`expected_revision`과 `expected_state_hash`를 승인 시점에 검사한다. 신선도 검사·hard 검사·commit은 같은 원자적 승인 절차에 속해야 한다. 하나라도 실패하면 정식 상태를 바꾸지 않고 이유를 기록한다. 오래된 요청과 plan은 폐기/취소한 후 새로 허용된 관측에서 재계획한다. 이를 위해 도메인 `WorldState` 자체에 새 필드를 넣을지, 별도의 episode envelope를 사용할지는 호환성 검토에서 결정한다.

### 발언·믿음·사실의 구분

플레이어의 “렌즈를 가져왔다”는 **출처가 있는 주장**이지 inventory fact가 아니다. 확인 전에는 모순 없이 명확화 질문이나 허용된 조회/검증 행동을 선택할 수 있지만, 해당 사실을 전제하는 행동을 정당화할 수 없다. 정식 지식 갱신은 게임이 승인한 검증 근거와 경로를 통해서만 가능하다. 단순 confidence 수치로 fact로 승격하지 않는다.

LLM과 계획기가 읽는 관측·기억 투영에는 같은 NPC 지식/노출 한계를 적용한다. 오류 payload도 그 한계 아래 제공한다. 기호 계획기가 비공개 canonical state를 읽는 oracle로 바뀌는 것을 허용하지 않는다.

### 의도 해석이 계획과 회복에 영향을 주는 인과 경로

`utterance → TypedIntent/Claim → 검토된 PlanningContext → 행동 선택 → 게임/플레이어 결과 → goal progress`를 기록한다. `PlanningContext`는 근거 있는 요청·행동 선호, NPC가 추가로 확인할 항목, 허용된 정보 요청/협상 분기 등을 담는 계획 입력이다. 최종 world fact·hard policy·고정 goal predicate를 바꾸는 별도 권위가 아니다. Plan은 intent ID와 PlanningContext digest를 참조해야 한다.

설계 예시는 같은 목표를 가진 NPC에게 플레이어가 도움을 거절하거나 다른 접근을 요청했을 때, 허용된 정보 확인·명확화·협상·대체 행동 중 무엇을 먼저 선택할지를 달리하는 것이다. 검증된 세계 관측이 있어야 물리적 전제를 바꿀 수 있고, 의도만으로 금지된 행동을 허용할 수 없다. 실제 지원 분기는 D-01/D-03에, 환경·player-response 정책과 관측 기회 정렬은 D-06에 동결한다.

동결 평가에는 같은 고정 목표/초기 상태에서 서로 다른 독립 intent label이 서로 다른 합법적 PlanningContext 또는 후속 상호작용을 요구하는 사례를 포함한다. P/R/O가 동일 계획기를 사용해도 그 입력 차이가 목표 진척에 영향을 주는지 trace로 확인한다. 의미를 다르게 해석해도 계획 입력·행동·환경 반응이 같다면, 그 regime에서 회복 차이를 LLM 해석 기여로 주장하지 않는다. 순수 세계 변화 재계획 효과는 별도 regime로 보고한다.

## 5. 이벤트·예산·실패 동작

- 판단은 플레이어 발언, 허용된 세계 변화, 자기 행동의 결과·HOLD, 또는 지정된 timeout/cancellation 같은 의미 있는 이벤트에서 시작한다. 렌더 프레임마다 LLM을 호출하지 않는다.
- 비동기 판단 중 새 이벤트가 오면 요청/계획의 episode·revision을 비교해 재사용 가능성 또는 취소를 결정한다. 순서 결정·중복 제거·늦은 응답 폐기 규칙을 로그와 리플레이에서 재현한다.
- 예산은 wall-clock deadline, 총 LLM calls/tokens, 도구 calls, 기호 계획기의 탐색 한도로 이루어진 **벡터**다. 수치는 실험 전에 동결한다. 서로 다른 계산을 임의의 단일 “agent step”으로 같다고 하지 않는다.
- 늦거나 예산을 넘긴 응답은 실행하지 않는다. 등록된 상태 보존 대기/안전한 실패로 마무리하고, 남은 예산이 있을 때만 새 관측에서 재시도한다. partial plan의 첫 단계라도 새로 검사·승인하지 않고 실행하지 않는다.
- 목표 도달 불가능, intent 미해결, 요청 취소, 모델/도구 실패와 timeout은 별도 terminal outcome이다. 실패한 episode도 분모와 trace에서 남긴다.
- 토큰 회계가 불가능한 backend는 availability=false와 미관측 값을 명시한다. 비용/토큰 동등성을 증명할 수 없으면 해당 효율 비교는 미충족으로 보고한다.

Trace는 proposal·근거·검증·수리·commit·model revision·seed·cost·latency에 더해 intent/plan ID, 관측/승인 상태 식별자, 변화 이벤트, 재계획 원인과 stage별 실패를 연결한다. `rho`의 국소 수리와 새 관측에 따른 goal replanning을 서로 다른 항목으로 남긴다.

## 6. 설계 수용 기준

모든 항목은 **Pending**이다. 문서에 있다는 이유로 구현 PASS가 아니다.

| ID | 시작 조건·트리거 | 기대 결과 / 금지 부작용 | 검증 방법 |
|---|---|---|---|
| AC-NPC-01 | 게임 소유 목표 아래 플레이어 발언을 받음 | goal/success predicate는 유지되고 intent·plan만 변경 | 목표 버전 보존 및 언어 입력 긍정/부정 fixture |
| AC-NPC-02 | 확인되지 않은 사실 주장·모호한 대상·금지 요청 | claim/uncertainty가 남고 근거 없는 fact·비공개 지식 승격 없음 | 독립 intent label·정보 노출 음성 fixture·trace 점검 |
| AC-NPC-03 | 관측 후 commit 전에 정식 상태 변화 | stale로 분류, 정식 상태 불변, 새 관측에서 재계획 | 순서 고정 변화 주입 + revision/hash 연결 검증 |
| AC-NPC-04 | 최신·허용된 NPC 행동 제안 | hard 검사 뒤에만 commit하고 후속 관측이 같은 결과를 참조 | 실제 Godot 라이브 episode + 동일 계약 자동 replay |
| AC-NPC-05 | 목표를 유지한 채 회복 가능한 변화 발생 | 사전 동결 예산 내 성공 predicate 도달 여부를 기록 | paired 변화 시나리오·작성형 player 정책·목표 oracle |
| AC-NPC-06 | deadline 초과·늦은 응답·중복·취소·no-route | 승인되지 않은/중복 실행 없음; 명명된 안전한 terminal outcome | 각 실패 주입·원자적 승인 fixture·전체 trace 보존 |
| AC-NPC-07 | 같은 입력·승인 이벤트·정책/소프트웨어 버전 replay | 같은 정식 상태 연결과 승인 결과; live LLM 응답을 재생성할 필요 없음 | 기록된 제안/결과 기반 deterministic replay·hash 대조 |
| AC-NPC-08 | LLM 판단이 진행 중인 게임 | 렌더/입력 처리가 판단을 기다리지 않으며 stage별 지연 관측 가능 | 실제 게임의 event→의도→계획→승인 구간과 렌더 진행 기록 |

## 7. 논문 계약: 주장과 새 증거

**제안하는 연구 질문:** 자유로운 플레이어 표현과 중간 게임 변화 아래에서, 근거 기반 언어 해석과 기호 재계획을 결합한 NPC 운영 구조는 강한 대조 구조와 비교해 고정 목표 회복·비용·실패 추적에서 어떤 차이를 보이는가?

조건부 가설 H-NPC-01: 같은 목표·관측 권한·행동·총예산에서 하이브리드 구조가 강한 규칙 기반 해석기와 동일 계획기를 사용하는 구조보다, 사전에 보지 못한 표현/상황에서 더 나은 의도 해석과 목표 회복을 보일 수 있다. 향상 없음·비용 증가·oracle과의 큰 격차도 허용되는 반증 결과다.

기여 후보는 실제 게임에 연결된 역할/권한 계약, claim–intent–plan–commit의 추적 가능한 실패 분리, 언어 해석과 재계획의 효과를 분리하는 실험이다. agent 명명, 폐루프 자체, 기호 계획이나 검증 게이트의 발명은 기여로 주장하지 않는다. “더 생생한 NPC”나 플레이어 만족은 별도 인간 연구 없이 주장하지 않는다.

**무효 commit 부재는 공통 hard invariant이지 arm 간 효능 지표가 아니다.** 미인코딩된 의미 위반까지 모두 잡는다는 soundness 주장도 하지 않는다. 승인 전 invalid/stale 제안의 빈도·종류는 비교 지표가 될 수 있다. 안전한 HOLD만 반복해 얻는 높은 생존율을 목표 회복으로 계산하지 않는다.

기존 `valid_commit_rate`는 commit이 하나 이상 있고 무효 commit이 없을 때 1.0이며, commit이 없으면 구현상 0.0이다. 따라서 commit 수·무효 commit 수를 함께 보고한다. 무진척 episode의 0.0을 무효 commit의 발생으로 해석하지 않고, 1.0을 arm 우월성으로 해석하지 않는다.

## 8. 실험 설계 초안

### 대조군

| Arm | 구조 | 분리할 질문 |
|---|---|---|
| P | LLM intent + 기호 계획/재계획 + 현재 상태 final gate | 제안하는 NPC 운영 구조 |
| R | 충분히 작성된 규칙/문법 해석기 + **같은** 기호 계획기/게이트 | LLM 해석 범위의 기여; 약한 keyword matcher만을 주 대조군으로 쓰지 않음 |
| O | 독립 label에서 제공한 올바른 intent + 같은 기호 계획기/게이트 | 언어 해석 상한 진단; 기존 `policy_restore` state-reading oracle와 다름 |
| G1 | 현재 guarded one-action proposer의 event별 운용 + 같은 final gate | 현재 구조와 전체 운영 구조 차이; 반드시 낮은 성능이라고 가정하지 않음 |
| LP | LLM이 계획/재계획도 제안 + 같은 final gate | 계획 책임 변경의 attribution 대조; 이 arm의 계획기는 의도적으로 다름 |

P/R/O를 기본 비교로 제안하며 G1/LP의 최종 필수 여부·정확한 controller/repair 구성은 프로토콜 동결에서 정한다. O의 label과 평가 규칙은 R/P의 개발·prompt·memory에 유출하지 않는다. 모든 deployed arm은 동일 final gate를 사용한다. gate 없이 unsafe 행동을 commit하는 대조군은 두지 않는다.

가능한 요소를 고정한다: 목표 predicate, NPC 지식/관측 projection, 행동 도구/스키마, 환경·player 정책, 시작 상태, 변화 주입, policy hash, 동일 LLM을 쓰는 arm의 model/revision, 전체 history 접근, budget vector와 종료 규칙. 계산이 다른 R/O/LP에는 적용 가능한 cap·실제 소비량·처리 시간을 각각 보고한다. 예산을 억지로 소모시켜 같은 비용이라고 하지 않는다.

### 시나리오·분리

세계/정책 구조·플레이어 표현을 개발/동결 평가로 분리한다. 초기 단일 NPC의 재사용 범위와 held-out 범위는 아직 승인되지 않았다. 같은 이야기 문장의 재표현만으로 cross-world 일반화를 주장하지 않는다.

발언 corpus의 출처·작성자/생성 model family·revision·작성 노력·개발 노출은 수집 전에 D-08에 동결한다. 주 평가를 P와 같은 LLM family가 생성·재표현한 문장만으로 구성하지 않는다. author-written 또는 독립 source/model family의 발언과 같은-family 보조 발언을 출처별로 분리 보고하고, 독립 intent label을 별도 평가자가 확인한다. O label과 held-out 표현은 R의 작성·P의 prompt tuning에 유출하지 않는다. 다른 model family라고 자동으로 독립성이 증명되는 것은 아니며, 중복·템플릿·발견된 contamination을 함께 점검한다.

실패 regime를 미리 선언한다: (L) 모호·기만·모순 발언에 의한 intent/claim 오류, (W) 허용된 관측 뒤의 세계/자원 변화, (E) 실행 실패·stale·timeout. 정적 환경도 control로 남긴다. 변화는 명시적 환경 이벤트/논리 step에 주입하고 paired arms의 발언·관측 기회를 정렬한다. 회복 가능/불가능 여부는 agent와 독립된 참조 절차로 사전 판정하며, 불가능 사례도 별도 분모·결과로 보존한다.

### 지표

- **주 지표:** 사전 지정 변화 후 원래 goal predicate에 예산 내 도달한 episode 비율. 대상은 agent와 독립적으로 사전 판정한 회복 가능 배정 사례이며, 아래 treatment-policy 분모를 적용한다. 회복 불가능 사례도 전체 배정과 별도 결과/분모에 남긴다.
- **해석 지표:** 독립 label의 허용 intent·entity grounding·불확실성 판단과 일치하는지. 모호한 발언은 복수 admissible intent 또는 명확화/보류를 label로 허용한다. 목표 달성만으로 해석 정답을 추정하지 않는다.
- **회복·운영 지표:** 회복까지 logical steps/time, 첫 valid progress commit까지 시간, 반복 HOLD/무진척, `hard_violations_per_candidate`, stale·invalid 제안의 원인별 개수, 취소·fallback·no-route 및 stage별 실패. 서로 다른 단위인 평균 위반 개수와 무효 제안 비율을 혼용하지 않는다. 회복 시간에는 성공/실패·관측 중단을 함께 보고하며 성공 episode만의 시간을 별도 조건부 기술 통계로 표시한다.
- **효율 지표:** 실제 총 calls/tokens/tool calls/탐색량·비용, event 시작→intent→plan→승인/feedback의 지연 분포. CLI 시작 지연을 실제 게임 반응 지연으로 대신하지 않는다.
- **공통 필수 검증:** encoded hard 검사·정보 경계·상태 연결·replay. 이 invariant가 실패한 arm/run은 FIX이며 조용히 삭제하지 않는다.

**Treatment-policy 분모:** arm/controller 실행 전 `episode × scenario × seed × model/revision × arm/config` 배정을 동결한다. 주 회복률의 분모는 사전에 회복 가능하다고 판정된 **모든 배정 episode**다. adapter failure·parse 오류·해석 미해결·timeout·controller failure와 변화 trigger 전에 실패한 episode도 제외하지 않으며 목표에 도달하지 못한 실패로 계산한다. 누락된 배정은 completeness FIX이지 자동 제외가 아니다. 실제로 HOLD/변화를 받은 episode만 사후 선택해 주 지표를 산출하지 않는다. 그런 조건부 진단을 제시한다면 별도 분모와 선택 조건을 표시한다. 기존 단일-proposal assignment 계약은 재사용 근거이며 새 episode key/schema는 D-02/D-06에서 동결한다.

관측률과 raw 차이를 기본 보고한다. model/episode/시나리오 반복의 독립성·집계 단위·구간 추정·검정은 분석 계획에 동결한다. oracle-minus-baseline 차이가 0일 수 있으므로 그 차이를 필수 정규화 분모로 사용하지 않는다.

### Mechanism ablation

1. 정적/동적 환경 control: 동일 interpreter와 planner에서 변화의 영향을 분리한다.
2. 재관측·재계획 없음: initial plan 유지, 동일 final gate. 역할의 필요성 점검이지 그 자체로 새 계획 알고리즘의 우월성 근거는 아니다.
3. claim 근거 확인/intent 수정의 유무: 오해와 기만 처리 효과를 분리하되 모든 arm의 final gate와 NPC 지식 한계는 유지한다. 승인하지 않는 shadow scoring으로 위험한 예상 결과를 별도 평가할 수 있다.

## 9. 프로토콜 동결 전 미결 사항

| ID | 결정할 사항 | 동결/승인 주체 |
|---|---|---|
| D-01 | 실제 첫 NPC·고정 목표 predicate·actor별 허용 행동·NPC 관측/지식 범위 | 게임 설계자 + 연구 책임자 |
| D-02 | 상태 revision의 의미, no-op/HOLD 처리, envelope/schema 버전, 라이브 transport/배포 방식 | 시스템 설계자; 권한 검사 검토 |
| D-03 | TypedIntent label, claim 검증·지식 갱신 경로, 모호한 발언의 처리 | 연구 책임자 + 독립 평가자 |
| D-04 | 기호 planning domain·unknown 처리·planner 버전/탐색 한도 | 계획기 담당 + 연구 책임자 |
| D-05 | model/revision/backend, 토큰·금전 한도, deadline·모든 budget 수치와 측정 조건 | 연구 책임자 + 비용 승인자 |
| D-06 | world/policy/표현 split, 환경·player-response 정책·관측 기회 정렬, 변화/회복 가능성 주입, 배정·평가 규모·반복·분석 계획 | 게임 설계자 + 연구 책임자; 수집 전 동결 |
| D-07 | G1/LP 포함 여부, 각 arm의 repair/history/툴 접근, 규칙 대조군 작성 노력 공개 | 연구 책임자 + 리뷰어 |
| D-08 | 발언 source·작성자/model family·revision, 평가 출처 비율·분리, O label 작성자의 입력 정보 권한·독립성·누출/중복 검사 | 연구 책임자 + 독립 평가자; 수집 전 동결 |

O label 작성 입력은 발언과 P/R에 제공한 **동일 NPC 허용 관측 투영·공개 GoalContract**로 제한한다. 비공개 canonical state, 미래 player-response 결과나 사전 회복 가능성 판정은 제공하지 않는다. 이 정보 경계를 D-03/D-08에서 함께 동결하고 label 입력 packet으로 검증한다. 회복 가능성 판정용 참조 절차와 게임의 최종 hard gate는 별도 권위이며, 그 정식 상태 정보를 O의 의도 해석 label에 우회 전달하지 않는다.

권장 검토 순서: D-01의 목표·행동·지식 범위를 먼저 정한 뒤 D-02/D-03/D-04의 상태·의도·계획 계약을 정합적으로 확정한다. D-05의 model family/revision과 D-07의 arm 경계를 정하고 D-08의 발언 출처·독립 label을 동결한 뒤, 이 입력들에 맞춰 D-06의 배정·평가·분석 계획을 마감한다. 발언 corpus 수집은 **D-06과 D-08 모두 동결 후**에 시작한다. D-06의 world/policy/표현 split·환경/player 정책도 수집 전에 동결하며, 배정·분석을 뒤에 검토한다는 권장 순서가 이를 면제하지 않는다.

이 표가 닫히기 전에는 사전등록·불변 seed 완료나 구현 준비 완료로 표시하지 않는다. 현재 문서는 핵심 방향의 검토 가능한 초안이다. author label 작성과 player 참여 연구도 구분한다.

## 10. 위험·되돌림·증거 게이트

주요 위험은 interpreter 오류를 planner 성능으로 포장하는 것, 숨은 정보/label leakage, 상태 변경 경쟁, 반복 HOLD로 목표 회복 지표를 회피하는 것, 비동기 응답이 비용/시간 예산을 넘겨 뒤늦게 실행되는 것이다. 대응은 앞 절의 stage 분류, 동일 projection/예산, 원자적 freshness 승인, 목표 predicate와 명명된 terminal outcome이다.

향후 구현은 기본 비활성의 새 mode/계약으로 기존 game policy·save·frozen research packet과 격리하는 것을 제안한다. 해제 시 agent 판단을 중단하고 승인되지 않은 pending 요청을 버린다. 검증된 현재 플레이 경로를 유지하는 되돌림을 설계한다. 구체 rollout·migration은 구현 계획 승인 범위에서 정한다.

새 측정치를 원고에 반영하려면 데이터/프로토콜 동결, 정보 누출 검사, 긍정·부정 logic fixture, 실제 게임 live loop, deterministic replay, 비용/지연 계측과 한영 claim/숫자 정합성이 먼저 필요하다. 현재 PDF·claim ledger·E1/E2/ENG1 및 `C-RESULT-*`는 수정하지 않는다.

## 11. 인터뷰 기록과 명확성

| Round | 질문 | 사용자 답 | 당시 개념 미정 정도 |
|---|---|---|---|
| 0 | 두 축을 함께 결정할 것인가? | 두 축을 함께 결정 | topology 확인; 미평가 |
| 1 | 중심 판단 주체 | NPC 에이전트 | 약 55% |
| 2 | 첫 핵심 성과 | 실패·변화 이후 목표 회복 | 약 34% |
| 3 | 목표와 계획의 변경 권한 | 목표 고정, 계획은 자율 | 약 27% |
| 4 | LLM의 필요한 역할 | 자연어·비정형 상호작용 해석 | 약 23% |
| 5 | 계획 책임 | LLM 해석, 기호 계획기 계획 | 약 21% |
| 6 | 기여 가설 재정렬 | 변화에 견디는 NPC 운영 시스템 | 약 21% |
| 7 | 첫 증거의 런타임 | 실제 Godot 게임, 턴·이벤트 기반 | 약 14% |
| 산출물 | 다음 작업 | 설계·실험 명세 작성 후 검토 | 구현 승인 아님 |

최종 개념 점수(0–1): 시스템 `{goal: .95, constraints: .90, criteria: .85, context: .90}`, 논문 `{goal: .90, constraints: .85, criteria: .80, context: .90}`. 축별 최솟값에 brownfield 가중치 `.35/.25/.25/.15`를 적용한 명확성은 `.8625`, 미정 정도는 `.1375`이다. 별도 critic이 지적한 프로토콜 미결은 이 개념 점수로 해소됐다고 주장하지 않는다.

Ontology: NPC·Player·GameWorld·AgentMemory·ValidationGate·Proposal은 Round 1–4에 유지됐다. Round 5에 TypedIntent와 SymbolicPlanner의 책임이 확인됐으며 Round 6–7에도 유지된다. 안정성은 Round 1 미평가, Round 2–4 `6/6`, Round 5 `6/8`, Round 6–7 `8/8`이다. GoalContract·ObservationSnapshot·UntrustedClaim은 명세가 제안한 추가 Interface/데이터 개념이며 사용자에게 별도 구현 승인받은 항목이 아니다.

## 12. 읽은 근거와 검토 경계

- 현행 계약: `neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/submission-optimization-2026-10-14.md`.
- 현행 코드 흐름과 구현 여부의 근거는 §2 참조; 초기 실행 경로 조사에서 확인한 `src/nesy_game/codex_adapter.py`도 읽은 근거로 보존한다. 새 설계를 현재 구현으로 전용하지 않음.
- 지식 근거: `llm-wiki/wiki/concepts/trace-rpg-controller.md`, 현재 프로젝트 graph의 제어기/원래 연구 계획 관계. 그래프는 조회만 했으며 새 설계를 반영해 재생성하지 않았다.
- [LLM-Modulo (2024)](https://proceedings.mlr.press/v235/kambhampati24a.html): 외부 verifier와 모델의 역할 분리 선례.
- [AgentSpec (2025)](https://arxiv.org/abs/2503.18666): 외부 runtime enforcement 선례; 게임 효과로 전용하지 않음.
- [NCP-Bench (2026)](https://arxiv.org/abs/2608.08160): 장기 narrative commitment 문제 동기; 본 시스템 측정치 아님.
- [Symbolically Scaffolded Play (2025)](https://arxiv.org/abs/2510.25820): symbolic scaffolding과 경험 측정의 경계 참고; NPC 운영 효과를 대신 증명하지 않음.

문헌은 subagent의 제한된 primary-source 검토에 근거한다. 새 exhaustive survey·출판 상태 승격·최초 기여 선언을 하지 않는다. 현재 변경은 인터뷰 상태와 이 명세뿐이며 코드·원고·실험 결과의 변경이 아니다.

## 13. 문서 검토·검증 기록

2026-10-14 `NpcSpecEvaluator`의 독립 문서 품질 평가는 **4.4/5**, substantive blocker 없음이었다. 평가는 코드·외부 인용의 새 감사가 아닌 사용자 계약의 범위 충족과 문서 내부 정합성 검토다. 아래 점수는 선택적 보완 전 초안에 대한 판정이며 NPC 성능 점수가 아니다.

| 축 | 점수 | 평가 근거·보완 |
|---|---:|---|
| 정확성 | 4/5 | §2의 현재/제안 분리, 지표·빈 분모, §11 명확성 산술이 정합적; 해시/리플레이 코드 앵커 보완 요청을 반영 |
| 완결성 | 5/5 | 사용자 결정 두 축과 고정 목표·권한·인과 경로·대조군·실패 포함 분모·미구현 계측·미결 동결 사항 모두 포함 |
| 명확성 | 5/5 | 역할·계약·AC-NPC·arm·D-ID 표와 가설의 반증 조건이 일관됨 |
| 실행 가능성 | 4/5 | 승인 주체와 수용 기준 명시; D-ID 검토 순서 보완 요청을 §9에 반영 |
| 간결성 | 4/5 | 각 절의 역할은 명확함; §12의 중복 코드 목록을 §2 참조로 축소 |

- 문서 구조 검증: 프로젝트 디렉터리에서 `uv run python scripts/lint_wiki.py ../llm-wiki --format json` 실행, exit 0. 74 pages; `missing_paths`, `broken_links`, `orphan_pages` 모두 빈 목록.
- 최초 `NpcDesignCritic`의 REVISE는 과거 초안에 대한 판정이며 통과로 간주하지 않는다. 후속 `NpcSpecCritic`의 최종 **PASS_FOR_USER_REVIEW**를 IRC로 수신했다. 판정은 사용자가 검토할 수 있는 설계·실험 명세의 정합성에 한정하며 구현 준비도·NPC 효능 인증이 아니다.
- critic은 수정한 조항을 직접 읽고 경미 지적 5건의 CLOSED를 확인했다: ① 계획 입력/`Plan` 표의 intent ID·PlanningContext digest 정합성(§§3–4), ② O label 작성자의 NPC 정보 권한·우회 누출 차단(§9), ③ 환경/player-response 정책의 D-06 소유권(§§4·9), ④ `codex_adapter.py` 읽은 근거 복원(§12), ⑤ D-06+D-08 모두 동결 후 corpus 수집(§9). 실제 schema·label packet·데이터/분석 동결은 여전히 D-02/D-03/D-06/D-08의 후속 프로토콜 작업이며 완료로 승격하지 않는다.
- 검토 전달 이력: 최초 후속 task는 판정 텍스트를 남겼지만 null yield로 전달 실패했고, 재개 결과의 lifecycle 조회도 실패했다. 이를 PASS인 task 실행으로 재명명하지 않는다. 위 최종 조항 검증 판정은 별도로 수신한 직접 IRC 응답에 근거한다. critic의 코드 점검은 metrics/experiment 및 새 runtime 앵커에 한정되며, 다른 게임 경로와 외부 인용의 새 전수 감사는 아니다.
- AC-NPC-01..08은 후속 구현/실험의 수용 기준이지 실행된 테스트 결과가 아니다. D-01..D-08은 미동결이다. 문서 검증으로 새 NPC의 성능·게임 동작·논문 효과를 입증했다고 하지 않는다.
