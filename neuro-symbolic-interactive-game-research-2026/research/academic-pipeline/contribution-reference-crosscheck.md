# 논문 기여도·레퍼런스·실험 교차검증 / Contribution–Reference–Experiment Crosscheck

상태: **VERIFIED-SCOPE-LIMITED**

점검일: **2026-09-03** (최초 2026-08-30; 2026-09-02 top-venue 보강 S47--S51; 2026-09-03 1차 소스 + Aside 브라우저 교차검증)

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
| C5 | typed 반례 유도 연산자 $\rho$ | symbolic validation, self-feedback, runtime feedback | E1의 동결 repairability class 비교만 | 작성 fixture + bounded offline mechanism; live-model evidence와 효능 해석 금지 |

핵심 novelty는 개별 아이디어의 발명이 아니라 **C1–C5가 하나의 권위 경계와 추적 계약으로
결합되고, 그 결합의 성공·실패·미생성 trace까지 같은 분모에서 감사되는 구현**이다.
`C-RESULT-001`–`005`는 모두 `TODO-RESULT`이며, 위 기여도를 효능·우월성 주장으로 승격하지
않는다.

## 3. 레퍼런스 ↔ 주제 교차검증

`reference-topic-crosswalk.csv`는 BibTeX의 58개 논문 레코드를 다음 9개 주제로 전수 매핑한다.
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

Stage-5 기계 기록 기준 집계는 **58개 = VERIFIED 48 + PREPRINT 10** (2026-10-14 bounded primary refresh에서 S57 JSONSchemaBench, S58 NCP-Bench, S59 benchmark-contamination study를 arXiv API와 OpenAlex DOI identity records로 독립 확인; 세 항목 모두 archival proceedings record를 확인하지 못해 PREPRINT 유지), unmatched 0, hallucinated 0이다. Semantic Scholar가 429를 반환한 기존 22개 레코드는 `rate_limited`로 명시했고, 새 항목은 arXiv·OpenAlex identity만으로 범위를 제한했다.
각 정체성은 Crossref, OpenAlex, PMLR, arXiv 또는 공식 학회 프로그램에서 별도로 확인했으며, 새 항목의 fetched arXiv/OpenAlex metadata에는 명시적 paper license가 노출되지 않았다. 이 수치는 **미일치 22건**이 아니라 **세 번째 색인 coverage gap 22건**이다.

## 4. 활성 근거 레인과 은퇴한 역사 레인 / Active and retired evidence lanes

활성 publication matrix는 E1, E3, ENG1만 포함한다. E2 행은 원본 receipt와 해시를 잃지 않기 위한
`publication_scope=historical` ledger이며 활성 생성·활성 lane count·C5 근거에 참여하지 않는다.

| 레인 | 공개 범위 | 설계 단위 | 핵심 관찰/역할 | 금지되는 해석 |
|---|---|---|---|---|
| E1 오프라인 conformance | active | 작성 fixture와 동결 repairability class | gate 13/13; commit 0/12 rejection, 0/12 blind, 5/12 $\rho$, 6/12 oracle; detectable fault 10/10; guard 3/3 | 모집단 효능, 모델 품질, safety rate |
| E3 KG/ontology simulation | active | 7 strategy × 6 query × 5 candidate = 210 score | retained strategy P=R=F1=1.000, MRR 0.944, Brier 0.131, Sem@3 1.000; baseline 0/6 | runtime retrieval, long-horizon memory, `C-RESULT-004` |
| ENG1 Godot/Web engineering | active | authored fixture 4개, combined 52 checks, smoke 8, balance archetype 5 | 4/4, 52/52, 8/8, 5/5; engine-local conformance | usability, fun, G4, 최종 G6, live Python transport |
| E2 live RQ2 screening | historical-only | 원래 live receipt/hash 묶음 | old model-specific cohort의 재현·무결성 확인만; 활성 산출물과 C5에서 제외 | active model result, model ranking, efficacy, 일반 sample efficiency |

E1은 확률 표본이 아니므로 $p$-value나 모집단 신뢰구간을 붙이지 않는다. E2 receipt는
validator의 명시적 historical check와 generator의 `--historical-live` 모드에서만 읽으며,
원본 파일을 덮어쓰지 않고 `paper/latex/generated/historical-live/`에 별도 재현한다. E2의
hosted revision, seed, token accounting은 활성 주장에 사용하지 않는다. E3는 실제 검색
runtime이 아니다. ENG1의 남은 사람 측정은 `_workspace/current/qa/human-measurement-packet.md`가 소유한다.

별도의 실제 개발 사례는 `research/development-cases/ontology-map-20261023-01/`의
`contract.json`, `result.json`, `runtime-identity.public.json`, `public-evidence-manifest.json`에
결속된다. 이 사례는 runtime-reported `gpt-6.1-sol` 선택, 1개 development run, independent
repeat 0개를 기록하며 provider-returned model/revision/seed/cost는 null이다. 관찰 wall
5942.665초는 orchestration을 포함하고, outer CLI 263.32초는 inference latency가 아니다.
날짜가 고정된 62 tests/QA10 PASS receipt와 별도의 새 additive QA overall NOT_PASS는 서로 다른
acceptance set으로 유지한다. 이 사례는 E2가 아니며 C1--C5의 model-specific empirical outcome도 아니다.


## 5. 메서드–결과 일치 판정

- **PASS:** C1–C5는 모두 코드·계약·fixture 또는 receipt 경로를 가지며 C5의 active evidence lane은 E1뿐이다.
- **PASS:** 활성 E1, E3, ENG1의 단위와 분모는 서로 섞이지 않는다.
- **PASS:** E2는 historical receipt/hash 재현과 fail-closed 검증에만 사용되고 기본 생성·활성 matrix count에서 제외된다.
- **PASS:** E3는 모든 `C-RESULT-*`에 비지원으로 표시되고, E2 old live-model 결과는 어떤 C1–C5 active outcome에도 귀속되지 않는다.
- **PASS:** 영문·국문 원고가 같은 58개 BibTeX key와 안정적인 C1–C5/활성 lane ID를 사용한다.

## 6. 제안 traceability scoring instrument / Proposed traceability instrument

다음은 PROV-DM의 entity/activity/usage/generation/agent, NASA SWE-052 bidirectional
traceability, ACM Artifact Review의 completeness·consistency·exercisability, Hayes--Krippendorff
독립 코딩, JCGM VIM의 verification/validation 구분에서 **동기를 얻은 project-authored
제안**이다. 이 출처들은 아래 rubric을 인증하지 않으며, 현재 사례는 점수를 측정하지 않았다.

각 차원 $d$에 대해 사전에 opportunity 집합 $U_d$와 필수 link 집합 $L_d(u)$를 고정한다.
정확한 source/version과 locator로 관계를 독립 확인한 link만 1이며, 나머지는
`missing`, `inaccessible`, `stale`, `contradicted`, `unverified` 중 하나로 기록한다.
완전한 단위 수 $n_d$와 전체 단위 수 $N_d=|U_d|$를 $n_d/N_d$로 보고하고 여섯 비율·시간·
결과를 하나의 가중 composite로 평균하지 않는다.

1. **Identity/activity binding:** task/run/attempt, artifact revision/digest, producing/using activity, actor.
2. **Decision evidence chain:** request/input → rule/requirement version → actually evaluated check/result → emitted decision.
3. **Decision-to-effect:** decision → observed state/artifact outcome, including denied/no-op and before/after evidence.
4. **Repair chain:** triggering failure → corrective change package → exact revalidation → result/unresolved state; failed repairs remain scorable.
5. **Bidirectional requirement coverage:** requirement → artifact → verification and in-scope change → requirement, reported separately.
6. **Independent exercisability:** non-author assessor exercises each predeclared replay/audit target with documented inputs and receipt.

Observer-neutral raw inventories must include retries, failures, no-ops and stage-not-reached events.
Missing links are 0 when the unit is in the reconciled denominator; incomplete inventory is
`indeterminate`, not an apparently complete percentage. Outcome status (`PASS`, `FAIL`,
`NOT_RUN`, `STAGE_NOT_REACHED`, `OUT_OF_SCOPE`, `MISSING`) remains separate from trace grade.
At least two non-author assessors, pre-adjudication ratings, disagreement matrices, raw agreement
and a nominal reliability estimate are prospective requirements; Jev/Gemini agreement is advisory,
not independent ground truth. The full source-bound rubric is staged under
`research/traceability-scoring-20261023/`.

## 7. Prospective whole-game and repeated cross-model plan

`research/development-comparison-20261023/` is the prospective plan, not an executed result.
It must freeze matched whole-game task information, starting checkout, semantic rules, tool/resource
limits, operator intervention, and acceptance checks before collection; vary representation only.
Use independently initiated task-runs across repeated held-out whole-game changes and multiple model
conditions, with arm-neutral observer reconciliation and blinded/adjudicated traceability coding.
The primary endpoint remains time-to-first-all-predeclared-validation-pass, with waiting, edits,
tools and repairs on the clock; failed, unfinished and timed-out assignments do not receive successful
completion times. Report decision and repair traceability separately with explicit denominators and
missingness. No sample-size, efficacy, superiority, ontology-benefit or traceability score is
established by this repository state.

## 2026-10-14 bounded refresh: literature and pilot-packet precedence

- S57 (2025 JSONSchemaBench), S58 (2026 NCP-Bench), and S59 (2025 benchmark-contamination study) were added only after direct arXiv API identity records were matched independently to OpenAlex DOI records. They remain `PREPRINT`; S58's arXiv acceptance comment for ICML 2026 is preserved, but no proceedings record was established. The fetched records expose no explicit paper license, so no reuse permission is inferred.
- The authoritative current C-PILOT-005 packet remains `stage-04-pilot/pilot-assignment-manifest.json` plus `sha256-manifest.json`: **121 = 85 executed + 36 aggregate**, with the frozen bytes and hashes unchanged. The later **64 = 43 + 21** prose/material-passport count is retained as a historical recapture claim only and must not replace the Stage-04 denominator. A parent-controlled replication receipt on 2026-10-14 reported byte-identical pilot results, manifest, and 11 CSVs in a separate release lane.
- The repair operator $[?25l\rho$ is implemented and remains state-blind in the precise sense of no direct `WorldState` access: it reads the prior candidate and typed validator errors, and those errors are its sole state-derived input. `policy_restore` is the separate state-reading oracle; frozen arm IDs are unchanged.
- **OPEN:** 확증 다중모델·독립 semantic oracle·인간 참가자·affect·runtime retrieval/memory·live transport 실험.
- **OPEN:** G4와 사람 제스처·latency·soak·rollback이 필요한 G6.

## English summary

The three CSVs bind all five manuscript contributions to prior-work topics, repository evidence,
and explicit inference ceilings. Active generation contains only E1 offline conformance, E3
engineering-only simulation, and ENG1 engineering verification; the E2 old live-model cohort is
retained only as an explicitly historical receipt/hash ledger. The separate development case records
runtime-reported `gpt-6.1-sol` selection without provider attestation, and the traceability rubric and
whole-game repeated cross-model comparison remain proposed future work. The contribution is the
audited integration, not invention of planning, interposition, constrained decoding, retrieval, or
feedback repair; no `C-RESULT-*` claim is promoted.
