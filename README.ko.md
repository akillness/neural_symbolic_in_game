# TRACE-RPG — The Sealed Lighthouse

[English](README.md) | **한국어**

*언어 모델은 게임 세계에서 다음에 무슨 일이 일어날지 제안할 수 있다. 하지만 결정론적 symbolic commit gate가 허락하기 전까지 그 무엇도 정식 상태가 되지 않으며, 모든 결과는 hash로 연결된 영수증을 남긴다.*

[![validate](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml/badge.svg)](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml)
[![Paper · EN PDF](https://img.shields.io/badge/Paper-EN%20PDF-b31b1b)](neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.pdf)
[![Paper · KO PDF](https://img.shields.io/badge/Paper-KO%20PDF-b31b1b)](neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.pdf)
[![Live dashboard](https://img.shields.io/badge/Live-dashboard%20%2B%20game-2ea44f)](https://sealed-lighthouse-trace-rpg.vercel.app)
[![Play in browser](https://img.shields.io/badge/Play-game%20only-1f6feb)](https://sealed-lighthouse-trace-rpg.vercel.app/public/)
[![Godot 4.7.1](https://img.shields.io/badge/Godot-4.7.1-478cbf)](neuro-symbolic-interactive-game-research-2026/game-track/godot/README.ko.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab)](neuro-symbolic-interactive-game-research-2026/pyproject.toml)
[![Evidence 52/52 + 4/4 · 8/8 · 5/5](https://img.shields.io/badge/Evidence-52%2F52%20%2B%204%2F4%20%C2%B7%208%2F8%20%C2%B7%205%2F5-blue)](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/evaluation-matrix.md)
[![last commit](https://img.shields.io/github/last-commit/akillness/neural_symbolic_in_game)](https://github.com/akillness/neural_symbolic_in_game/commits/main)
[![Slides (KO)](https://img.shields.io/badge/Slides-KO-orange)](neuro-symbolic-interactive-game-research-2026/docs/slides/trace-rpg-overview.ko.html)

![2026-11-03 현재 source에서 캡처한 ending: 수사관의 기여와 validator 영수증. 모델 결과가 아닌 엔지니어링 화면 근거](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-ending.png)

- **Gate.** 생성된 모든 이벤트는 신뢰할 수 없는 transaction proposal로 취급한다. type-strict parser, 외부 action policy, 그리고 여섯 상태 상대 계열에 속한 일곱 개의 결정론적 검사가 commit 여부를 결정한다. 거부된 candidate는 한도 내에서 반례 유도 repair를 받고, 그 밖의 모든 경우는 변경 없는 이전 상태로 되돌아간다.
- **게임.** *The Sealed Lighthouse*는 Godot 4.7.1로 만든 턴제 수사 micro-RPG다. 게임 안의 ledger가 gate를 서사 속에서 그대로 보여 준다. hold는 자신을 막은 계열을 명시하고 규칙을 가르치며, commit은 기여를 게시하고 다음 단서를 열고 SHA-256 영수증 체인을 잇는다.
- **근거, 그리고 그 한계.** 네 개의 레인(E1 오프라인 fixture, E2 라이브 스크리닝, E3 KG 시뮬레이션, ENG1 엔진 적합성)은 정확한 count만 보고한다. gate 일치 13/13, guided-repairable class에서 ρ 5/5, 플레이어블 core 검사 52/52 + D-073 확장 검사 4/4, 하나로 일치하는 종단 state hash. 작성된 세계 하나, hosted proposer 하나, 참가자 없음, 효능 주장 없음.

<!-- prospective-pilot:start -->
## 사전 지정 비교 실험 — 2026-11-03

Study: `prospective-pilot-20261103`. Status: **NOT_RUN/BLOCKED**; conclusion: `NOT_MET`.

| Track | Planned | Blocked | Assigned | Attempted | Executed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Runtime | 60 | 60 | 0 | 0 | 0 |
| Development | 120 | 120 | 0 | 0 | 0 |

요청 패널은 Codex `gpt-5.6-sol`, Codex `gpt-6.1-sol`, Antigravity `gemini-3.8-flash-medium`이며 medium은 명목 설정이다. Runtime은 같은 정보의 일반 규칙/온톨로지를 10회 fresh reset으로 비교한다. 제한된 개발은 두 표현과 최소 입력/공개 저장소 탐색, 5개 과제, 2회 fresh run을 교차한다. 이는 완료된 모델 실행이 아닌 계획된 배정이다. 실제 응답 신원, credit 사용 방지, 격리, 새 activation이 입증되지 않아 추론을 시작하지 않았다. 성공률·효과·비용·구간은 미측정이며 0이 아니다.
<!-- prospective-pilot:end -->

[동결 protocol](neuro-symbolic-interactive-game-research-2026/research/prospective-pilot-20261103/protocol-v1.json) · [보존한 집계](neuro-symbolic-interactive-game-research-2026/research/prospective-pilot-20261103/results-v1/summary.json) · [독립 offline 과제 control](neuro-symbolic-interactive-game-research-2026/research/prospective-pilot-20261103/task-freeze-v1.json). 5개 과제 오라클은 각각 정답 변형 2개를 통과시키고 결함·오답 변형 2개를 거부했으며 9,303개 파일의 누출 검사를 통과했다. 이는 모델 효능이 아닌 fixture 근거다. 과거 8행 5/8 pilot, 중단된 신원 확장, 로컬 Ollama 관측, 단일 개발 사례와 합산하지 않는다. 최신 agent의 전수 탐색 능력은 가정된 사실이 아닌 미검증 가설이다.

## 논문 한눈에 보기

![그림 1: transaction 파이프라인 — propose, parse, policy, 여섯 계열의 일곱 검사, 한도 내 repair 또는 변경 없는 fallback, commit, record, replay — 그리고 플레이어가 읽는 ledger 문법 띠](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_architecture.png)

**TRACE-RPG: 출처 결속 온톨로지 근거와 대화형 게임의 단일 Codex 통합 사례.** 리뷰·개정한 로컬 PDF의 실측 분량은 **영문 17쪽·국문 17쪽**(2026-11-11)이며 기존 원고 구조와 글자 크기를 유지했다. 두 언어의 claim·수식·표·그림 ID는 같고 페이지 배치는 다르다. 익명 심사용 작업 초안이지 10쪽 venue 제한 충족, 학술지 제출 또는 게재 승인을 주장하지 않는다. 참고문헌 58건의 citation identity·인용 맥락·preprint 상태 검증은 별도로 기록한다.

**논지.** 유창하거나 schema에 맞는 생성 텍스트는 제안된 게임 이벤트가 실행 가능하고, 승인되었으며, 정식 상태와 일관된다는 것을 보장하지 않는다. 그래서 TRACE-RPG는 생성된 모든 이벤트를 신뢰할 수 없는 transaction proposal로 취급하고, 결정론적 symbolic commit gate를 통해서만 받아들인다.

| | 기여 | 무엇을 보장하는가 |
|---|---|---|
| **C1** | 신뢰 경계 contract와 type-strict parser | 알 수 없는 key와 모호한 type을 proposal 경계와 replay 경계 양쪽에서 거부한다 |
| **C2** | validate–repair–commit controller | 여섯 상태 상대 계열의 일곱 개의 결정론적 검사, 한도 내 repair(기록되는 시도는 최대 K+1회), 변경 없는 fallback, commit 전 재검증 |
| **C3** | 감사 연결 근거 계층 | SHA-256으로 연결된 record, 상태 의미 replay, assignment-complete 회계 |
| **C4** | assignment-complete harness | 설계된 사례를 하나도 빠짐없이 관찰하고 분류하는 정확한 회계 |
| **C5** | 반례 유도 repair 연산자 ρ | 직전 candidate와 validator의 typed error set만 읽으며, 권위 있는 상태는 절대 읽지 않는다 |

일곱 검사는 여섯 상태 상대 계열로 묶인다. 어떤 실패도 상태를 바꾸지 않는다.

| 계열 | 검사 | 거부하는 것 |
|---|---|---|
| Action policy | 1 | 알 수 없는 action 또는 type |
| Precondition | 2 | 없거나 거짓인 요구 조건 |
| Reachability | 3 | 접근 불가능한 object |
| NPC knowledge | 4 | 선언되지 않은 known fact |
| Disclosure | 5 | 금지된 fact |
| Quest | 6, 7 | 자격 없는 stage; stage 후퇴 |

[![2026-11-11 리뷰·개정 PDF에서 렌더한 한국어 원고 17쪽 전체 contact sheet](neuro-symbolic-interactive-game-research-2026/docs/readme/review-20261111/paper-ko-pages.png)](neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.pdf)

## 근거

아래 네 과거 레인은 원래 count와 상한을 유지하며 별도 v5 개발 수집과 합산하지 않는다. 모든 숫자는 결정론적 runner 또는 hash로 묶인 영수증에서 나온 raw count이며, 추론 통계는 보고하지 않는다.

| 레인 | 설계 | 단위 | 대표 count | 상한 |
|---|---|---|---|---|
| **E1** 오프라인 적합성 | 작성된 frozen fixture, 세계 하나: gate fixture 13개, repair fixture 12개 × 4 arm, fault injection 10개, adapter/회계 assignment 7개, guard 3개 | Fixture | gate 일치 13/13; guided-repairable class에서 ρ 5/5 | 인코딩된 술어에 대한 mechanism 적합성 — 효능 아님 |
| **E2** 라이브 스크리닝 | hosted proposer 하나(`gpt-5.6-sol`), 5 cell × 5 call, K = 1, 두 arm에 동일 candidate | Call | Signal-v2 cell: ρ 5/5 대 blind retry 0/5 | pilot-only; 모집단·모델 순위 주장 없음 |
| **E3** KG/온톨로지 시뮬레이션 | closed-world typed-link 시뮬레이션: node 43개, reference edge 106개, 검토된 typed edge 24개, 채점된 proposal 210개; degree baseline 대 고정 전략 6개 | Proposal | 작성된 holdout 6/6 회수 | simulation-only; 런타임 검색이나 의미적 진리 아님 |
| **ENG1** Godot/Web 엔지니어링 | fixture 4개, core 검사 52개 + D-073 확장 검사 4개, 8항목 3D 스모크, archetype 회전 5회 | Check | 52/52 (+4/4 확장) · 8/8 · 5/5; 종단 hash가 오프라인 runner와 일치 | 성능이 아닌 적합성; 참가자 없음 |

**결과 전문.**

- **E1.** gate 일치 13/13, 구현된 error code 12개 모두 관찰. 처음에 invalid였던 repair 사례 12건(guided-repairable 5 / oracle-only 1 / irreparable 6)에 대해 rejection-only 0/12, blind retry 0/12, ρ 5/5 + 0/1 + 0/6, 상태를 읽는 oracle callback 5/5 + 1/1 + 0/6. 실패한 모든 arm은 상태를 그대로 두었다. 사전 지정된 fault 10/10이 지정된 검사에서 거부되었다. provenance 경계 fixture 1/1은 설계상 replay를 통과한다 — key 없는 hash는 무결성을 주지 인증을 주지 않는다.
- **E2.** guided의 우위는 policy-blind Signal-v2 cell에서만 나타났다(ρ 5/5 대 blind 0/5, +5). 나머지 네 cell은 +0이었다. 세 건은 candidate가 이미 valid였고, 한 건은 되돌릴 수 없는 quest-stage 후퇴였다. 비-commit 결과 15/15 모두 이전 상태 hash를 보존했다.
- **E3.** typed-lexical 전략이 작성된 holdout 6/6을 회수했다(P = R = F1 = 1.000, MRR 0.944, Brier 0.131, Sem@3 1.000). degree baseline은 하나도 회수하지 못했다.
- **ENG1.** Godot slice가 작성된 trace를 replay하며 종단 state hash가 오프라인 runner와 동일하다: `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`. 플레이어블 평가 core 52/52(fixture 검사 40 + presentation invariant 12)와 별도로 집계한 D-073 수사·안내·trace 확장 4/4(전체 56/56), 3D 스모크 8/8, balance probe 5/5.

![Balance probe: 스크립트로 작성된 archetype 다섯 가지가 같은 commit 체인을 각각 완주한다](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/balance-archetypes.svg)

![KG/온톨로지 시뮬레이션 평가 matrix: 작성된 holdout에 대한 degree baseline 대 고정 typed-link 전략 여섯 가지](neuro-symbolic-interactive-game-research-2026/research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg)

**이 근거가 보여 주지 않는 것.**

- 어떤 모델이 다른 모델보다 낫다는 것 — E2는 revision이 고정되지 않은 hosted proposer 하나로 cell당 다섯 번 호출했다.
- 플레이어 경험, 재미, usability, 정서 — 참가자를 모집한 적이 없다.
- 작성된 세계 하나를 넘어서는 일반화 — 모든 fixture는 frozen world state 하나 안에 있다.
- 작성자 인증 — hash 체인은 key가 없으므로 무결성만 증명한다.
- 엔진 성능 — ENG1은 적합성 근거이지 지연이나 처리량 근거가 아니다.

### 별도 v5 paired-selector 개발 수집 — 2026-11-10

합성 개발 fixture 5개 × feedback 조건 2개 × 요청 selector 2개에서 **응답 20개를 수신했다. schema 실패 10개, strict parsing 통과 candidate 10개, gate 승인 8개, 독립적으로 지정한 목표 달성 7개**다. 아래 각 행의 분모는 schema 실패를 포함한 배정 5개 전체다. 응답 수신은 과제 성공이 아니며 승인된 commit도 목표를 놓칠 수 있다.

| 요청 selector | Feedback | 응답 수신 | Schema 실패 | Strict parsing 통과 | Gate 승인 | 목표 달성 |
|---|---|---:|---:|---:|---:|---:|
| `gpt-5.6-luna` | Detailed | 5/5 | 1/5 | 4/5 | 4/5 | 3/5 |
| `gpt-5.6-luna` | Generic | 5/5 | 0/5 | 5/5 | 3/5 | 3/5 |
| `gpt-5.6-terra` | Detailed | 5/5 | 5/5 | 0/5 | 0/5 | 0/5 |
| `gpt-5.6-terra` | Generic | 5/5 | 4/5 | 1/5 | 1/5 | 1/5 |

관측된 목표 달성은 Luna 6/10, Terra 1/10이다. 이는 검증된 실제 응답 신원이 아닌 요청 selector이며, 실제 신원·provider 요청 횟수·비용은 알 수 없다. 작은 합성 집합은 holdout이 아니고 feedback 정보량이 다르며 명목 직렬 순서는 Luna 다음 Terra였다. 사람 대상 연구나 인과 연구가 아니며 모델 우월성·온톨로지 효능·사용자 편익을 주장하지 않는다. 앞선 미완료·diagnostic cohort, 단일 탐색 사례, 사전 지정 pilot, NPC validated-v5는 각각 별도로 유지한다.

`unauthorized_objective` fixture는 정책·목표 충돌을 그대로 유지한다. 고정 정책은 어떤 효과도 허용하지 않지만 공통 목표에는 `signal_restored`가 필요하다. Luna의 상세 응답은 금지된 효과를 제거해 승인되었으나 목표에는 도달하지 못했다. 이 사례도 모든 배정 분모에 남는다. CLI stdout/stderr 원문은 보존하지 않았고 바이트 수·해시·이벤트 요약은 남아 있으며 parsing 실패 10개의 내용 수준 원인은 미상이다. 보존된 v5 이벤트 배열에서는 각 응답이 terminal completion보다 먼저 나타났다(20/20). 이 사후 순서 검사는 새 모델 실행이나 제공자 신원 검증이 아니다.

[19개 코호트의 과거 이력 목록](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-history-20261111/cohort-inventory.json)은 이전 준비·실패·미완료 및 v3·v4 파일도 공개한다. 코호트별 계수와 원본 파일 해시는 가림 처리한 기록 집계이지 합산한 독립 관측이나 제공자 요청 횟수가 아니다. 원시 운영 기록은 로컬에 보존하며 해시만으로 비공개 원본의 공개 재현이 가능해지는 것은 아니다.

공개 입력: [Luna 결과](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-v5/paired-model-comparison-20261110-v5-gpt-5.6-luna/results.json) · [Terra 결과](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-v5/paired-model-comparison-20261110-v5-gpt-5.6-terra/results.json) · [복사한 prompt 20개](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-v5/). projection은 `metadata.codex_executable`만 null로 바꾸고 raw 파일 SHA-256과 생략 영수증을 추가한다. 결과·prompt hash·실행 파일 hash/version은 유지한다. raw cohort와 승인은 로컬에 변경 없이 남는다. 공통 7파일 source ZIP은 상위 출처만 입증하며 독립 실행 가능한 재현본이 아니다.

![그림 5: 상세 typed error와 일반 거부를 대비하고 strict parsing, candidate ID 검사, 일곱 술어 재검증, commit 또는 변경 없는 fallback, 별도 목표 검사를 잇는 출처 기반 v5 state-signal 도식](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_state_signal.png)

signal은 거부 이유를 설명할 뿐 상태 변경 권한을 주거나 정서를 추정하지 않는다. 이 작성된 도식은 동결 collector와 기록된 signal 필드를 사용한다. 단일 응답 뒤 v5 collector는 추가 repair 호출을 허용하지 않으며 재검증만 commit을 승인할 수 있다.

![그림 6: 배정·응답 20개에서 parsing 통과 10개, 승인된 commit 8개, 목표 달성 7개로 이어지는 동결 v5 수집 흐름과 전체 20개 fixture별 결과 및 schema 실패를 포함한 dispatch-to-terminal 초](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_paired_feedback_flow.png)

흐름과 matrix는 schema 실패 10개와 목표를 놓친 승인 commit 1개를 모두 유지한다. 초 단위 시간은 실패 응답을 포함한 dispatch부터 terminal까지이며 모델만의 지연이 아니다.

## 게임

*The Sealed Lighthouse*는 3D 항구 장면 안의 턴제 서사 수사 micro-RPG다(Godot 4.7.1, 영어 UI). 보상은 항구 쪽 신호를 복구하고 저조 항로를 얻는 것이며, 바다 건너 등대 자체는 봉인된 채 어둡게 남는다. 브라우저에서 바로 플레이할 수 있다: [sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app)은 게임이 임베드된 라이브 대시보드를 열고, [`/public/`](https://sealed-lighthouse-trace-rpg.vercel.app/public/)은 게임만 연다.

**골든 패스** — commit 세 번, 선택적으로 hold 한 번:

1. 램프 창고에서 신호 렌즈를 회수 → **commit**, stage 0 > 1.
2. 항구 신호 mount에 렌즈를 설치 → **commit**, stage 1 > 2, 단서가 승인된다.
3. Mira 선장에게 조석 표식 단서를 요청 → **commit**; 이어서 서쪽 방파제의 조석 표식을 조사 → 에피소드 완료.
4. (선택) Mira에게 봉인된 등대지기의 비밀을 요청 → DISCLOSURE 계열이 **HELD**, 상태 변경 없음, 규칙 학습.

**플레이어가 읽는 ledger** — commit된 snapshot의 presentation 전용 readout이며, oracle label이나 봉인된 fact는 절대 담지 않는다:

```text
[P] PROPOSAL …
[C] ENTRY #N | COMMITTED
[C] CONTRIBUTION #N | <facts> | STAGE a>b | CHAIN k/3
[N] UNLOCKED | <next affordance>

[H] HELD | [V] GATE <family> | state unchanged
[N] NEXT VALID ENTRY
[V] RULE LEARNED | <family>: <rule>

HUD      CASE CHAIN | LENS [x] > MOUNT [x] > LEAD [x] | RULES LEARNED n
End card INVESTIGATOR'S CONTRIBUTION #1–#3 · RULES LEARNED · ENTRIES/HOLDS/FINAL STAGE
         VALIDATOR RECEIPT <state hash> · HOLDS BY GATE
```

| 키 | 동작 | | 키 | 동작 |
|---|---|---|---|---|
| `W A S D` | 이동 | | `F5` / `F9` | 저장 / 불러오기(checksum 검증; 손상된 save는 거부) |
| 마우스 | 시점 | | `M` | 모션 줄이기 |
| `E` | 상호작용 / 조사 | | `V` | 오디오 토글 |
| `Esc` | 커서 해제 | | `T` | 필드 가이드 |

<table>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-arrival.png" alt="2026-11-03 현재 source의 arrival: proposal 이전 상태"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-refusal.png" alt="현재 source의 HOLD: gate 계열을 명시하고 이전 상태를 보존한다"></td>
  </tr>
  <tr>
    <td align="center"><sub>Arrival — 임시 복사본의 새 engine 캡처</sub></td>
    <td align="center"><sub>HOLD — 이전 상태 보존</sub></td>
  </tr>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-authorized_hint.png" alt="현재 source의 승인된 COMMIT: 기여와 다음 affordance"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-ending.png" alt="현재 source의 ending과 validator 영수증"></td>
  </tr>
  <tr>
    <td align="center"><sub>COMMIT — 승인된 진행</sub></td>
    <td align="center"><sub>Ending — validator 영수증</sub></td>
  </tr>
</table>

**아래는 과거 production 캡처다.** 날짜가 있는 배포 근거로 보존하며, 새로 캡처한 현재 source나 새 배포의 바이트가 아니다.

<p align="center">
  <img width="32%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-start.png" alt="모바일 viewport의 프로덕션 배포: 시작 화면">
  <img width="32%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-in-game.png" alt="모바일 viewport의 프로덕션 배포: 게임 내 ledger">
</p>

위의 새 still sequence로 기존 활성 gameplay GIF를 교체했다. 1280×720 캡처 4개는 현재 source의 임시 Godot build에서 얻었다(fixture 4/4, core 검사 52/52, 화면 4/4). 사용성이나 모델 효능 근거가 아니다. [캡처 manifest](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/manifest.json)는 source, UTC, 크기, bytes, SHA-256과 관측 가능한 state/event 결속을 기록한다. 과거 원본과 hash-bound 영수증은 보존한다. UI 아트는 파일별 provenance·절차적 fallback을 갖춘 Higgsfield 이미지이며 player rig는 큐레이션된 Higgsfield GLB(Idle / Casual_Walk)다. Mixamo raw 파일은 추적하지 않는다. 이동·카메라·VFX·오디오·UI는 정식 상태를 바꾸지 않고 proposal router와 validator만 바꾸며 engine slice에는 live Python 왕복이 없다.

## 라이브 commit-gate 대시보드

**2026-11-03 현재 source의 로컬 캡처:** 실제 브라우저 입력으로 arrival → HOLD → COMMIT 3회 → ending을 완료했고 hold 1회와 상태에 결속된 dashboard readout을 기록했다. 모델 assignment가 아닌 operator-driven 화면 경로다. Capture attempt 1은 완료됐지만 **pointer-lock page error 5개**가 있었고 두 번의 bounded yaw/lock 재시도 진단도 보존했다. Clean-browser gate는 **NOT_PASS**이며 화면을 읽을 수 있다는 이유로 통과 처리하지 않는다. 배포·사용성·몰입·모델 편익을 주장하지 않는다.

아래의 현재 still sequence로 예전 dashboard GIF와 이전 renderer의 표시용 사본을 교체했다. 불변 과거 캡처와 실패 영수증은 보존한다.

![2026-11-03 현재 source의 dashboard arrival: stage 0, commit 0, hold 0](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-arrival.png)

<table>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-hold.png" alt="현재 로컬의 stage-gated disclosure HOLD: 초기 상태 hash 보존"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-commit.png" alt="현재 로컬의 렌즈 회수: stage 0에서 1, commit 1회와 hold 1회"></td>
  </tr>
  <tr>
    <td align="center"><sub>Hold</sub></td>
    <td align="center"><sub>Commit</sub></td>
  </tr>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-complete.png" alt="현재 로컬 ending: commit 3회와 hold 1회"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-last-action.png" alt="현재 로컬의 마지막 판정과 verdict history readout"></td>
  </tr>
  <tr>
    <td align="center"><sub>현재 source의 ending · commit 3회 / hold 1회</sub></td>
    <td align="center"><sub>현재 source의 읽기 전용 판정 이력</sub></td>
  </tr>
</table>

**과거 production endpoint:** [sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app). 2026-09-03 배포 기록은 root를 `/dashboard/`로 연결하고 내장 게임을 `/public/`에서 서빙했다. 당시 desktop/390×844 검사는 과거 기록이다. 이번 갱신은 재배포하지 않았고 production 바이트가 새 로컬 캡처와 같다는 것을 입증하지 않는다.

<p align="center"><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-signals.png" alt="2026-11-03 현재 source의 로컬 읽기 전용 disclosure signals"></p>

로컬에서 실행하려면, 대시보드가 로컬 Web 빌드를 내장하므로 로컬에서 서빙한다:

```bash
cd neuro-symbolic-interactive-game-research-2026
./scripts/build_godot_web.sh                                   # disposable-copy Web export -> game-track/web/public/ (ignored)
python3 -m http.server 4173 --bind 127.0.0.1 --directory game-track/web
open http://127.0.0.1:4173/dashboard/                          # game at /public/, dashboard at /dashboard/
```

경계는 한 방향이다. 내장된 게임은 `window.parent.postMessage`로 typed event를 미러링하며 페이지에는 게임 명령 채널이 없고 봉인된 fact ID도 전달받지 않는다. 새 경로는 commit 3회와 hold 1회를 기록했다. `STAGE_GATED_DISCLOSURE` hold는 초기 상태 hash를 보존했고 실제 state/event 결속은 캡처 manifest에 남겼다. 이는 현재 로컬 경로의 관측이지 새 배포 서비스나 모델 성능의 근거가 아니다.

## 슬라이드

16장짜리 한국어 개요 덱을 단일 HTML 파일로 제공한다: [`trace-rpg-overview.ko.html`](neuro-symbolic-interactive-game-research-2026/docs/slides/trace-rpg-overview.ko.html)(화살표나 스페이스로 이동, `?`로 도움말). 덱은 이 README와 같은 흐름을 따른다.

<table>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-01.jpg" alt="슬라이드 1"><br><sub>01 · 제목</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-02.jpg" alt="슬라이드 2"><br><sub>02 · 문제: 유창한 텍스트 ≠ valid한 이벤트(여섯 가지 실패 유형)</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-03.jpg" alt="슬라이드 3"><br><sub>03 · 은행 창구 비유</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-04.jpg" alt="슬라이드 4"><br><sub>04 · 파이프라인: propose → parse → policy → 7 검사 / 6 계열 → repair 또는 fallback → commit → record → replay</sub></td>
  </tr>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-05.jpg" alt="슬라이드 5"><br><sub>05 · 여섯 상태 상대 계열, 일곱 검사, 게임 예시</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-06.jpg" alt="슬라이드 6"><br><sub>06 · Guided repair: ρ 루프와 네 개의 arm</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-07.jpg" alt="슬라이드 7"><br><sub>07 · SHA-256 영수증 체인과 의미 replay</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-08.jpg" alt="슬라이드 8"><br><sub>08 · 기여 C1–C5</sub></td>
  </tr>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-09.jpg" alt="슬라이드 9"><br><sub>09 · 근거 레인 E1 / E2 / E3 / ENG1과 상한</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-10.jpg" alt="슬라이드 10"><br><sub>10 · 오프라인 repair-arm 막대 그래프</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-11.jpg" alt="슬라이드 11"><br><sub>11 · 라이브 스크리닝 표와 KG 숫자</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-12.jpg" alt="슬라이드 12"><br><sub>12 · 게임 에피소드 루프와 권위 경계</sub></td>
  </tr>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-13.jpg" alt="슬라이드 13"><br><sub>13 · 규칙 학습으로서의 HELD 화면</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-14.jpg" alt="슬라이드 14"><br><sub>14 · 기여 readout: CONTRIBUTION / UNLOCKED / CASE CHAIN과 두 부분 영수증</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-15.jpg" alt="슬라이드 15"><br><sub>15 · 근거가 말하는 것과 말하지 않는 것</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-16.jpg" alt="슬라이드 16"><br><sub>16 · 다음 단계와 세 줄 요약</sub></td>
  </tr>
</table>

## 재현

```bash
cd neuro-symbolic-interactive-game-research-2026
uv sync --extra research --extra dev                 # Python 3.11+ and test/validation dependencies
uv run python -m pytest -q                           # unit + contract tests
uv run python scripts/validate_project.py            # structure, schemas/bridge, SVG, evidence contracts
uv run python scripts/validate_contribution_crosswalk.py
uv run python scripts/validate_visual_assets.py --require-pdf-tools
./scripts/validate_game_track.sh                     # Godot 4.7.1 on PATH: fixtures, smoke, balance probe
uv run python scripts/run_playable_evaluation.py     # SL-PLAY-EVAL-001 on a disposable project copy
./scripts/verify_like_ci.sh                          # the CI-equivalent gate
uv run python scripts/generate_paired_feedback_figures.py --check  # frozen public inputs -> SVG drift check; no model call
ARCHIVED_NPC_SOURCE="$(mktemp -d)"                    # explicit empty directory for historical source
git archive --format=tar fa9fb8a2c2249e35eddc7d4e0951c15a7b4bea09:neuro-symbolic-interactive-game-research-2026 | tar -xf - -C "$ARCHIVED_NPC_SOURCE"
make -C paper/latex check NPC_PAPER_EVIDENCE_ROOT="$ARCHIVED_NPC_SOURCE"
```

- `uv sync --extra research --extra dev` — CI와 같은 lock된 Python 3.11+ 연구·테스트·검증 환경을 설치한다.
- `pytest` — parser, validator, repair, replay, 무결성, 회계 contract.
- `validate_project.py` — 저장소 구조, JSON 스키마와 game bridge, SVG 원본, 소스 매니페스트, 증거·분석 계약.
- `validate_contribution_crosswalk.py` — C1–C5, 참고문헌 58건, 근거 레인 네 개가 두 원고에서 서로 일관되는지.
- `validate_visual_assets.py` — 논문의 모든 그림과 표가 편집 가능한 원본과 데이터로 이어지는지.
- `validate_game_track.sh` — Godot fixture, 3D 스모크, archetype balance probe.
- `run_playable_evaluation.py` — 프로젝트의 일회용 복사본 위에서 SL-PLAY-EVAL-001(검사 52개).
- `verify_like_ci.sh` — `validate` workflow가 실행하는 것과 같은 gate.
- `generate_paired_feedback_figures.py --check` — 동결 공개 v5 projection에 대해 생성된 SVG 원본 두 개의 drift를 확인하며 파일을 다시 쓰거나 모델을 호출하지 않는다. PNG/PDF 파생본은 논문 pipeline이 빌드한다.
- `make -C paper/latex check NPC_PAPER_EVIDENCE_ROOT="$ARCHIVED_NPC_SOURCE"` — 두 PDF를 다시 빌드하고 출처 결속 근거·양의 정수 쪽수·Type 3 font를 검사한다. 명시한 revision의 archived project는 과거 NPC006 source를 제공할 뿐 현재 runtime의 권위가 아니다. 이 archived-source 검사는 통과했지만 archive 없는 기본 검사는 NPC006과 현재 source가 달라 **FIX**로 유지된다. 현재 source의 전체 CI 통과를 주장하지 않는다.

### Aside 전용 브라우저 검사

기존 Aside CLI와 승인된 연결 profile이 있는 환경에서 연구 프로젝트 디렉터리 기준으로 원래 브라우저 contract 53개와 추가 fixture 대조군을 실행한다:

```bash
export NSG_BROWSER_BACKEND=aside
export NSG_ASIDE_PROFILE='your-approved-profile-id'
uv run pytest tests/test_publication_presentation.py tests/test_ontology_evidence_map.py tests/test_signal_explainer.py -q
```

profile 자리표시는 명시적으로 바꾸고 profile ID나 원시 브라우저 로그는 공개하지 않는다. 같은 환경값으로 `./scripts/verify_like_ci.sh`도 Aside를 선택한다. 선택한 backend의 누락·실패는 다른 브라우저를 사용할 허가가 아니다. bridge는 작업 전용 탭과 loopback fixture만 연다. native request/pageerror callback은 여전히 사용할 수 없다. 실제 HTTP 영수증과 초기 main-world error/CSP/message observer를 유한한 fixture 관측 구간 안에서 검사할 뿐, 일반 native 브라우저 감시와 동등하다고 인증하지 않는다. component·그림 검사이며 gameplay·모델 효능·프로덕션 배포의 근거가 아니다. 이 명령은 Aside 설치·계정 변경·연구 실행을 하지 않는다.

패킷: 오프라인 파일럿(frozen, hash로 묶임)은 [`research/academic-pipeline/stage-04-pilot/`](neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/stage-04-pilot/), 라이브 스크리닝은 [`research/academic-pipeline/rq2-live-pilot/`](neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/rq2-live-pilot/), KG 시뮬레이션은 [`research/simulation/kg-ontology/`](neuro-symbolic-interactive-game-research-2026/research/simulation/kg-ontology/), 플레이어블 평가는 [`game-track/godot/docs/latest/`](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/).

## 고정 목표 NPC 운영 레인 (프로토콜 1.1)

현재 NPC 통합은 `sealed-lighthouse-v1`을 향하는 고정 목표 controller다. 정식 상태의 유일한 writer는 Godot이며, Python은 typed intent를 해석하고 여섯 필드 public observation만 대상으로 bounded BFS를 수행한다. hidden world state를 읽거나 새롭고 전지적인 planning을 하지 않는다. `acquire_object`와 `install_lens`는 player의 명시적 요청이고, signal 복구·tide lead 승인·dialogue open 뒤 `reveal_hint`를 낼 수 있는 주체는 Captain Mira뿐이다.

wire contract는 `npc-goal-recovery/1.1.0`이다. P는 공식 인증 Codex OAuth CLI adapter를 호출하며 rule fallback은 없다. R은 작성된 rule/grammar control이고, O는 같은 model family의 public-input-only auxiliary arm이며 independent gold가 아니다. loopback service는 `127.0.0.1:8768`에 bind하고 `http://127.0.0.1:8877`, `http://localhost:8877`만 정확히 허용한다. `TRACE_RPG_NPC_CAPABILITY`는 일시적 환경값이며 capability는 `X-NPC-Capability`에만 보낸다. episode budget은 utterance epoch을 넘어 누적된다: intent 30,000 ms, episode 900,000 ms, intent call 8회, action attempt 32회, replan 16회, plan expansion 32회, in-flight 1개. 배정은 engineering R 16개 observation과 screening 72개(P/R/O × 2, 각 24개)로 총 88개이며, arm별 합계는 R=40, P=24, O=24다. input/output token, cost, 반환된 model revision은 사용할 수 없어 `null`로 유지한다.

**validated-v5 근거.** corpus는 28개 case(engineering 16개 + screening 12개)다. 불변 canonical packet `research/academic-pipeline/npc-goal-recovery/verified-run-006/`에는 배정된 88행이 기록됐으며 strict validation을 통과했다. 인증 CLI 실행 24회: 요청·반환된 모든 24개 model ID는 null이며, provider revision, provider seed, token 회계, cost도 모두 null이다. screening 각 arm의 실행 완료 20개와 stale-control ACK 거부에 따른 assigned failure 4개를 모두 유지한다. 관측된 goal 4/24는 recovery rate나 efficacy 추정치가 아니다. O의 same-family 표기는 protocol source label이며 P와의 실제 일치를 검증한 것이 아니다. 모델 미식별 `verified-run-001/`, 실패한 diagnostic, source-bound native `verified-run-002/`, `verified-run-003/`은 별도의 불변 근거이며 이 cohort와 합산하지 않는다. efficacy·superiority·generalization·human benefit·independent label을 주장하지 않는다.

프로젝트 루트에서 OAuth를 확인하고 rule fallback 없는 Codex service arm을 명시해 실행한다:

```bash
codex login status
uv run python scripts/run_npc_service.py \
  --backend codex --model gpt-5.6-sol --host 127.0.0.1 --port 8768 \
  --allow-origin http://127.0.0.1:8877 \
  --allow-origin http://localhost:8877
```

canonical packet은 immutable하다. 새 model-pinned cohort를 실행하려면 아래 `NEW-ID`를 사용하지 않은 식별자로 바꾸며, 과거 두 cohort를 덮어쓰거나 합산하지 않는다. preflight/dry-run도 새 noncanonical directory를 사용한다. 저장된 canonical packet을 다시 검증할 때는 `research/academic-pipeline/npc-goal-recovery/verified-run-006`를 validator에만 전달한다.

```bash
uv run python scripts/run_npc_goal_experiment.py \
  --packet all --model gpt-5.6-sol \
  --engineering-fixtures data/fixtures/npc-goal-recovery/validated-v5/engineering.json \
  --screening-fixtures data/fixtures/npc-goal-recovery/validated-v5/screening.json \
  --output-dir _workspace/current/qa/npc-rerun-NEW-ID \
  --godot-project game-track/godot

uv run python scripts/validate_npc_goal_evidence.py \
  --packet all \
  --root "$PWD" \
  --packet-dir _workspace/current/qa/npc-rerun-NEW-ID
```

validator가 통과한 뒤에만 final packet 결과와 bilingual paper fragment를 갱신하며, preflight와 과거 packet은 diagnostic으로 남긴다.

## 경계와 공개

논문이 명시하는 경계이며, 이 README도 같은 경계를 지킨다:

- 작성된 세계 하나. 모든 fixture와 플레이어블은 frozen world state 하나를 공유한다.
- revision이 고정되지 않은 hosted proposer 하나. 라이브 스크리닝은 pilot-only다.
- 참가자 없음, 정서·usability 데이터 없음, 효능 주장 없음.
- 키 없는 hash는 무결성 확인에 쓰이며, 인증을 제공하지 않는다.
- 엔진 근거는 성능이 아닌 적합성이다.
- 사람이 판단하는 gate — G4(presentation), G6(production) — 는 아직 열려 있다.

**출처 이력의 예외.** 과거 QA presentation 사본 세 개는 비공개 rig/cache payload를 의도적으로 제외하므로, 그 사본의 과거 whole-tree manifest는 바이트까지 완전한 공개 재현본이 아니다. 과거 단위 테스트 RED 영수증 두 개는 덮어써져 원본 바이트 동일성이 복구되지 않았으며, reconstruction으로 표시한 파일은 원본 근거가 아니다. [날짜가 명시된 출처 이력](llm-wiki/wiki/reports/2026-10-15-npc-goal-operation-implementation.md#historical-unit-test-receipt-losses-and-explicit-corrections)에 해당 영수증과 공개 사본의 제외 항목을 각각 기록했다. 이 QA 이력의 예외와 별도로 보존·해시 검증된 canonical 실험 packet을 혼동하지 않는다.

**AI 공개.** 대규모 언어 모델이 산문·코드·테스트 초안 작성과 인용 확인을 도왔고, hosted 모델이 라벨이 붙은 라이브 스크리닝 candidate를 생성했다. 보고된 모든 count는 결정론적 runner 또는 hash로 묶인 영수증에서 나온다. 플레이어블의 UI 아트는 파일별 provenance와 절차적 fallback을 갖춘 큐레이션된 AI 생성 이미지(Higgsfield)이고, 플레이어 rig는 큐레이션된 Higgsfield GLB이며, Mixamo 원본 파일은 절대 추적하지 않는다.

License: to be announced.

## 인용

```bibtex
@misc{tracerpg2026,
  title = {TRACE-RPG: Auditable Neuro-Symbolic Commit Gates for Interactive Game Worlds},
  year  = {2026},
  note  = {Draft prepared for anonymous review; no submission or acceptance claimed},
  url   = {https://github.com/akillness/neural_symbolic_in_game}
}
```

