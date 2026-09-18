# Aside 근거 리뷰 — 게임 적용 논문과 플레이어 증거 경계 (2026-09-18)

Status: **REVIEW COMPLETE / ENGINEERING EVIDENCE RETAINED / PLAYER·효능 결과 미확립**

이 보고서는 TRACE-RPG 논문과 *The Sealed Lighthouse*에 이미 적용된 근거를 재검토하고, 2026-09-18 Aside 브라우저 조사 intake 두 건을 연구 근거가 아니라 **설계 권고**로 사용해 다음 개선 사이클을 동결하기 위한 기록이다. Aside 보고서 자체가 명시하듯 해당 자료는 `[INFERENCE]`이며, 아래의 게임·논문 결과를 승격하지 않는다.

- 게임/논문 기준선: [[2026-09-03-paper-game-readout-figure-readme-and-reference-recheck]]
- 게임 UI·탐정 튜토리얼 Aside intake: `neuro-symbolic-interactive-game-research-2026/_workspace/current/intake/aside-research-2026-09-18-detective-tutorial-hud.md`
- 커밋 게이트 trace·평가 상태 Aside intake: `neuro-symbolic-interactive-game-research-2026/_workspace/current/intake/aside-research-2026-09-18-commit-gate-trace-encoding.md`
- 직접 대조한 원고: `neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.tex`
- 현재 claim ledger: `neuro-symbolic-interactive-game-research-2026/research/claim-ledger.yaml`
- 현재 플레이테스트 상태: `neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/playtest-report.md`

## 1. Executive verdict

현재 패킷은 **상징적 커밋 게이트의 설계·구현 conformance**에는 강하지만, 게임이 플레이어에게 더 재미있거나 이해하기 쉽거나 주체성을 높인다는 근거에는 도달하지 않았다. 원고의 현 경계는 대체로 정직하다.

| 근거 | 현재 관찰 | 허용되는 해석 | 허용되지 않는 해석 |
|---|---|---|---|
| E1 offline | 13/13 authored validator expectations, 12/12 repairability-class checks, fault/replay/accounting fixtures | 동결된 한 세계에서 구현된 계약·불변식의 conformance | 실제 모델의 오류율, 일반화, 플레이어 효능 |
| E2 live screening | `signal-repair-v2`, 5/5 guided 대 0/5 blind, 동일 proposal, K=1; 다른 regime은 null | 의도적으로 만든 guided-repairable regime에서의 pilot-only mechanism transfer | 일반적인 sample efficiency, 모델 우위, 인구집단 효과 |
| ENG1 Godot/Web | 52/52 evaluation, 8/8 smoke, authored trace와 terminal hash 일치 | 한 authored fixture의 엔진 로컬 재생·표시 conformance | usability, immersion, fun, agency, commercial performance |
| Human study | 참가자 0, 독립 playtest 0, G4/G6 human gate 미종결 | 측정 프로토콜이 준비되어 있음 | 플레이어 경험·가독성·이해도·재방문 의도 결과 |

따라서 `C-RESULT-001`–`005`와 G4/G6를 그대로 `TODO-RESULT`/`FIX`로 유지해야 한다. 8쪽 PDF의 캡처, dashboard, `contribution` readout은 **presentation-only engineering evidence**이다.

## 2. 무엇이 잘 뒷받침되는가

1. **hard validity와 soft adaptation의 분리**가 원고, claim ledger, 게임 readout에 일관되게 반영되어 있다. 커밋은 canonical snapshot과 deterministic checks를 거친 뒤에만 발생하고, affect·narrative·retrieval·memory는 authority가 아니다.
2. **repair의 범위가 정직하게 제한**되어 있다. `ρ(a,E)`는 구조화된 error와 이전 candidate만 읽으며, live pilot의 5/5 대 0/5는 특정 constructed error regime에만 귀속된다.
3. **negative/failure accounting**이 보존된다. fallback, adapter/controller failure, no-trace terminal row를 분모에서 삭제하지 않는다.
4. **게임 표시와 canonical state가 분리**되어 있다. contribution/case-chain/rule 줄은 committed snapshot의 순수 파생물이고 state를 바꾸지 않는다.
5. **현재 paper의 과장 방지 장치**가 실제로 작동한다. claim ledger는 C-RESULT를 TODO-RESULT로 유지하고, `playtest-report.md`도 0 participants를 명시한다.

## 3. 근거가 부족하거나 아직 비어 있는 부분

### 3.1 플레이어 경험은 측정되지 않았다

현재 자동화는 입력·렌더·해시·replay를 검증하지만, 다음을 관찰하지 않는다.

- 플레이어가 `HOLD`의 이유와 다음 행동을 이해하는가
- 기여도 readout이 player agency/유능감에 영향을 주는가
- case-chain이 추론을 돕는가, 아니면 HUD 부담을 늘리는가
- 재미, 몰입, frustration, perceived control, repeat intent가 달라지는가
- 튜토리얼을 실제로 읽고 목표를 재진술할 수 있는가

`human-measurement-packet.md`는 소유자 1인 gesture/성능 확인용이며 독립 참가자 연구가 아니다. 그러므로 그 패킷을 실행하더라도 G4 효능 결과로 승격하면 안 된다.

### 3.2 현재 design advice와 empirical claim이 섞일 위험

Aside의 탐정 게임 조사는 다음을 권고하지만, TRACE-RPG의 효과를 입증하지 않는다.

- Golden Idol 개발자 인터뷰는 전체 정답 판정이 복잡한 장면에서 좌절을 만들 수 있어 partial-progress와 bounded closeness signal을 도입했다고 설명한다. 이는 3-node tutorial chain에는 설계 precedent지만, 이 게임의 만족도 효과가 아니다.
- Obra Dinn 개발자 devlog는 초기 popup hint가 읽히지 않았고, 이후 contextual mode와 diegetic pointer로 바꿨다고 기록한다. 이는 upfront folio를 reference card + just-in-time coaching으로 분해할 근거이지, TRACE-RPG의 tutorial success 결과가 아니다.
- CHI PLAY 연구는 mystery에서 interpretation tool/information map을 권고하면서도 unknown을 전부 수치화하지 말라고 한다. 따라서 `CHAIN 2/3`은 tutorial spine으로 제한하고, 수집률형 전역 progress metric은 추가하지 않는 편이 안전하다.

### 3.3 live repair 비교는 confirmatory evidence가 아니다

5개 seed/cell과 unpinned hosted revision은 계획된 모델 모집단에 대한 추론을 허용하지 않는다. 특히 다음이 남아 있다.

- 독립 semantic oracle와 templated multi-scenario battery
- 사전 고정된 model/revision/provider scope와 실제 seed control
- 동일 proposal을 공유하는 matched-arm 외에, proposal variation을 포함한 분석
- guided-repairable / oracle-only / irreparable 각 regime의 사전 비율과 외적 타당도
- primary endpoint, 최소 효과/정밀도 기준, 반복측정 단위와 multiplicity 계획

이 공백은 결과 파일 이름이나 status를 바꿔 해결할 수 없다.

### 3.4 trace 시각화는 `pass`와 `not evaluated`를 혼동해서는 안 된다

Aside의 trace 조사에서 JSON Schema 2020-12는 successful evaluation만 evaluated로 기여한다고 명시하고, verbose output에서는 각 node에 명시적 `valid`를 둘 것을 권고한다. 따라서 고정 topology dashboard가 모든 가족을 그릴 때 누락된 state를 회색 또는 pass처럼 렌더링하면 시각적 과장이 된다. `PASS`, `FAIL`, `SKIPPED`, `OUT_OF_SCOPE`, `ERROR`를 분리하고 각 non-evaluated state에 reason을 요구하는 것은 **trace honesty 개선**이지 player efficacy 근거가 아니다.

### 3.5 접근성과 성능은 별도 gate다

WCAG 2.2의 1.4.3(텍스트 contrast 4.5:1/large text 3:1), 1.4.11(non-text state 3:1), 2.5.8(target 24×24 CSS px)와 reduced-motion 지침은 UI 품질 gate를 정할 수 있게 한다. 이것을 만족해도 readability/immersion 결과가 자동으로 생기지는 않는다. 마찬가지로 input-to-visible 100 ms 목표와 soak/frame 측정은 runtime performance evidence이지 fun evidence가 아니다.

## 4. Aside 원자료에서 추출한 고신뢰 설계 근거

| 출처 | 확인된 사실/권고 | TRACE-RPG에 적용할 때의 정확한 범위 |
|---|---|---|
| W3C, *PROV-DM*, 2013, https://www.w3.org/TR/prov-dm/ | plan과 activity record를 별도 개념으로 둔다 | pipeline diagram과 실제 proposal trace를 별도 레이어로 라벨링; provenance 의미론의 적용이지 플레이어 효과가 아님 |
| JSON Schema team, *JSON Schema Core 2020-12*, 2020, https://json-schema.org/draft/2020-12/json-schema-core | failed evaluation은 evaluated에 기여하지 않으며 verbose output은 명시적 per-node valid를 요구 | `PASS`/`FAIL`/`SKIPPED`/`OUT_OF_SCOPE`/`ERROR`를 payload에 명시; conformance reporting을 개선 |
| OpenTelemetry, *Trace API*, official specification, https://opentelemetry.io/docs/specs/otel/trace/api/ | `Unset`, `Ok`, `Error`를 구분하며 default를 success로 읽지 않도록 주의 | state missing을 pass/neutral로 fallback하지 않음; dashboard 오독 방지 |
| Kärnä, Väkevä, Rautalahti & Lindqvist, *Questions without Answers: Enjoyment of Irresolution in Mystery Player Experience*, PACM HCI 8, CHI PLAY 2024, DOI 10.1145/3677100, https://aaltodoc.aalto.fi/server/api/core/bitstreams/5516f1a8-c521-4663-bdb0-0dfd69d860fe/content | thinking tool/information map을 제공하되 unknown을 모두 quantify하지 말라는 design guideline | case chain은 제한된 추론 도구로 유지; 전역 clue counter는 추가하지 않음 |
| Marques, Parreiras, Kritz & Xexéo, *A Conceptual Model for the Analysis of Investigation Elements in Games*, 2024, arXiv:2403.10272, https://arxiv.org/html/2403.10272v1 | investigation을 exploration–elicitation–experimentation–evaluation cycle로 분석하고 clue storage/evaluation feedback을 별도 축으로 둔다 | telemetry에서 탐색·제안·hold·commit·revisit를 별도 event로 보존; cycle 모델 자체를 결과로 주장하지 않음 |
| El Montaser, Lallé & Muratet, *Evaluating the Impact of Automated Hints in a 3D Educational Escape Game*, IUI 2025, pp. 685–694, DOI 10.1145/3708359.3712132, https://dl.acm.org/doi/full/10.1145/3708359.3712132 | optional incremental hints의 효과가 난이도/학습자에 따라 달라질 수 있음 | hint를 optional·runged로 설계하고, completion/time/independent solution을 조건별 측정; 이 논문의 수치를 TRACE-RPG에 전이하지 않음 |
| Microsoft, *Xbox Accessibility Guidelines 115: Errors and warnings*, official guideline, https://learn.microsoft.com/en-us/gaming/accessibility/xbox-accessibility-guidelines/115 | 오류와 교정 방법을 여러 방식으로 설명하고 발생 지점을 시각적으로 강조 | HOLD row에 gate reason + correction/next valid entry를 텍스트와 비색상 channel로 제공; 이해도는 별도 사용자 측정 |
| W3C WAI, *WCAG 2.2 Understanding: Use of Color / Non-text Contrast / Target Size*, 2023, https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html | 색상만으로 상태를 전달하지 않고, 그래픽/state에 contrast와 target-size 기준을 적용 | glyph+label+color, 3:1 state contrast, 24×24 CSS px target을 QA gate로 검사; WCAG PASS를 usability claim으로 바꾸지 않음 |
| Pope, *Return of the Obra Dinn* development logs, developer primary sources, https://dukope.com/devlogs/obra-dinn/tig-30 | 초반 popup hint의 실패와 contextual/diegetic guidance의 설계 trade-off를 직접 기록 | folio를 reopenable reference로 두고 first hold/commit 시점에 contextual card를 제시; preference/learning 효과는 측정 전까지 미확정 |

## 5. 우선순위 개선안 — 두 사이클

### Cycle A: evidence-safe instrumentation and design lock

1. **상태 의미론을 payload에서 먼저 고정한다.** 각 check에 `state`, `code`, `reason`, `ord`; 전체 trace에 `short_circuit_at`; 누락 state는 fail-closed `ERROR`로 처리한다. `OUT_OF_SCOPE`와 `SKIPPED`를 count에서 `PASS`와 합치지 않는다.
2. **플레이어 관찰 event를 canonical mutation과 분리한다.** 최소 event는 `session_start`, `objective_seen`, `folio_open/page`, `proposal_shown`, `hold_seen`, `correction_seen`, `next_valid_entry_seen`, `commit_seen`, `case_chain_revisited`, `session_end`다. 이벤트에는 build/content hash, scenario ID, locale, viewport/device class, monotonic timestamp, prior/next canonical state hash를 넣되 원문 입력과 개인정보는 수집하지 않는다.
3. **현재 게임의 저위험 UI 개선만 적용한다.** folio page 1만 시작 시 보여 주고 page 2/3은 첫 commit/hold 뒤에 contextual하게 열 수 있게 하며, 언제든 다시 열 수 있게 한다. timer auto-advance는 쓰지 않는다. 이 변경은 presentation/view-local 상태로 제한하고 golden-path canonical hash를 재검증한다.
4. **HOLD copy를 error + correction + inference로 분리한다.** `왜 보류됐는가`, `다음에 무엇을 할 수 있는가`, `이 규칙이 세계에 대해 무엇을 말해 주는가`를 별도 텍스트로 표시한다. hidden oracle label이나 미등록 raw ID는 계속 fail-closed한다.
5. **QA gate와 human outcome을 분리한 matrix를 고정한다.** WCAG/viewport/render/performance는 engineering columns, comprehension/agency/fun/frustration은 human columns로 둔다. 자동화 52/52는 human column을 채우지 못한다.
6. **Cycle A의 종료 조건:** trace schema/validator regression PASS, missing-state negative fixture PASS, EN/KO parity PASS, 1280×720 및 390×844 screenshot/contrast/target-size checks PASS, 기존 terminal hash 또는 의도적으로 변경된 새 baseline receipt가 명시됨, 그리고 아직 `C-RESULT` 승격 없음.

### Cycle B: confirmatory player and model evidence

1. **별도 preregistration을 먼저 freeze한다.** human study와 live model study를 하나의 결과로 섞지 않는다. 조건, primary endpoint 하나/track, exclusion, stopping, missing-data, multiplicity, build hash, model revision, seed policy를 공개 hash로 묶는다.
2. **플레이어 연구는 최소 baseline-vs-variant within-subject 설계로 시작한다.** 같은 deterministic scenario battery를 counterbalance하고 order를 randomize한다. baseline은 기존 ledger, variant는 contribution/rule readout이며, 정보량과 playtime budget을 사전에 맞춘다.
3. **주요 human endpoint를 하나씩 동결한다.** 예: (a) chain-node objective comprehension의 정답률 또는 (b) 다음 유효 행동 선택까지 시간. fun/agency/immersion은 secondary로 두고 각 construct를 분리한다. Likert 한 문항을 여러 construct의 대리변수로 사용하지 않는다.
4. **표본수는 임의 숫자로 정하지 않는다.** pilot variance와 smallest effect of interest를 이용해 power/precision simulation을 하고, repeated observations는 participant와 scenario random effects를 포함한 mixed-effects model로 분석한다. 소표본이면 추정치와 interval을 보고하고 efficacy 결론을 보류한다.
5. **repair study는 independent semantic oracle와 템플릿 scenario를 추가한다.** guided-repairable만 고른 성공률을 주 endpoint로 삼지 말고, repairability strata를 사전 비율로 포함한다. model/provider/revision은 고정하거나 각 strata를 명시적으로 분석한다.
6. **Cycle B의 종료 조건:** prereg hash와 build hash 공개, counterbalance/randomization receipt 존재, independent oracle audit, planned denominator과 missing-data report, human consent/privacy packet, mixed-model/precision output, negative/null result 보존, 그리고 모든 승격 claim이 trace→analysis→ledger crosswalk를 갖춤.

## 6. 논문에 즉시 반영할 문장 수준의 경계

- `ENG1`과 Fig. 3에는 현재 문장처럼 “presentation-only readout; engineering conformance, not usability/efficacy evidence”를 유지한다.
- Discussion에 다음 의미를 명시한다: “The current game packet demonstrates engine-local conformance and a measurement-ready protocol; it contains no participant observation and therefore cannot support claims about comprehension, agency, enjoyment, immersion, or player benefit.”
- E2의 5/5 대 0/5는 “constructed guided-repairable regime에서의 pilot-only mechanism transfer”로만 부르고, `sample-efficient`, `better`, `improves` 같은 일반 비교 동사는 confirmatory protocol 전까지 사용하지 않는다.
- Aside의 설계 precedent는 Related Work/Design Rationale에 `[design precedent]`로 분리하고, 결과 표·claim ledger·abstract의 empirical evidence로 세지 않는다.
- 현재 `claim-ledger.yaml`의 `C-RESULT-001`–`005`와 `G4/G6` status를 변경하지 않는다.

## 7. 결론

가장 큰 부족함은 게임이 부족하게 만들어졌다는 증거가 아니라, **게임의 좋은 엔지니어링 증거를 플레이어 효능 증거로 잘못 읽을 수 있는 측정 공백**이다. 이번 패스의 안전한 개선은 더 많은 캡처나 더 강한 문구가 아니다. 먼저 trace semantics와 view-only instrumentation을 고정하고, 그 다음 preregistered human/model studies를 별도 lane으로 실행하는 것이다. 그 전까지 현재의 fail-closed 경계가 논문의 가장 강한 결과다.
