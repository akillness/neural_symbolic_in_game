# Signal notation review / 시그널 표기 재검토 — 2026-10-23

## Status / 상태

`AUDIT_COMPLETE_CLARIFICATIONS_OPEN`; additional live QA is `NOT_PASS`. No paper, figure, validator, game source, frozen result, deployment or experimental sample changed. This is a notation/evidence audit, not a human-comprehension or efficacy study. Only this knowledge note and its navigation records are updated.

검토한 도표·수식에서 잘림/겹침은 관찰되지 않았다. 그러나 검사 명칭의 코드 연결과 시그널 단위 설명에는 보완점이 남는다. 과거 배포 PASS와 아래 새 QA 실패를 별개의 날짜·실행 근거로 보존한다.

## Fresh verification / 새 검증

- Command: `uv run --extra dev python -m pytest tests/test_publication_presentation.py tests/test_ontology_publication_sources.py tests/test_signal_explainer.py -q`, from the research project root. Exit 0: **104 passed in 77.80s**. This is the selected related suite, not a new full-CI result.
- Two independent source/semantics reviewers and one rendered-PDF reviewer completed read-only reviews. Actual EN p2/p3/p9 and KO p2/p4/p9 were viewed at 150 dpi with 300 dpi diagnostic crops; inspected figure outputs were also viewed. No objective clipping or unintended ink overlap was observed in those regions. This is not exhaustive proofreading, print certification or measured human readability.
- EN PDF: 675846 bytes, 10 pages, SHA-256 `a643d01cd1c6e2172d6bff470ab23c1fda051176625cec262b21303009f65186`.
- KO PDF: 631282 bytes, 10 pages, SHA-256 `efd6e0a4b036463d49c1fd6ba458d076444bbc4e84dfb3fba15dcf482db7007a`.
- One fresh Jev API request returned `jev-1.14.0` for requested alias `jev-latest`. Tier `unvalidated`, verdict `proposal_only`; `evidence_supports=yes, p_yes=0.74`; `needs_clarification=yes, p_yes=0.67`. These are advisory outputs, not calibrated correctness probabilities, approval, independent gold or game authority. Historical negative Jev advice remains unchanged.

## Signal units / 시그널의 단위

| Label | Exact meaning / 정확한 의미 | Non-meaning / 뜻하지 않는 것 |
|---|---|---|
| E | Expected-match / expected-mismatch **case counts** / 기대 일치·불일치 사례 수 | A probability or safety rate |
| R | Replay-equal / replay-unequal **case counts** / 재생 동일·상이 사례 수 | Safety or expected correctness |
| C | PASS / FAIL **check-record counts** / 검사 기록의 통과·실패 수 | Case counts; totals need not equal n |
| NR | Cases with no reported checks / 검사 기록이 없는 사례 수 | PASS, skipped, or live out_of_scope |

Slash pairs are **two counts, not fractions**. For the 48 normal cases, `C 14/68` means 14 passing and 68 failing check records, not 14 of 68 cases. Unchecked `C 0/0, NR 48` means no check records were reported for those cases; it does not mean all checks passed. Unchecked `E 0/48` together with `R 48/0` directly demonstrates that replay equality alone does not establish expected correctness.

[INFERENCE] A standalone reader may mistake the slash pairs for ratios or replay PASS for safety. This risk was identified from visible labels and semantics, not measured on human readers. Expand the visible legend and retain case-versus-record units in both languages if a revision is agreed.

## Exact Python binding / Python 검사와 명칭 연결

[Validator source](../../../neuro-symbolic-interactive-game-research-2026/src/nesy_game/validator.py) declares exactly these seven IDs. The paper's aliases are not evidence of an eighth predicate.

| Equation component | Exact check ID | Condition / 조건 |
|---|---|---|
| v_policy | action_policy | Missing policy, required-precondition/effect omissions, extra effects, or unauthorized quest-stage target |
| v_pre | precondition | Candidate preconditions absent from current facts |
| v_reach | object_reachability | Required object absent from inventory and missing/unreachable location |
| v_know | npc_knowledge | Used or disclosed facts outside actor knowledge |
| v_disc | forbidden_disclosure | Disclosed facts intersect forbidden set |
| v_elig | quest_stage | required_quest_stage > current quest_stage; minimum-stage eligibility |
| v_stage | quest_stage_monotonicity | quest_stage_effect < current quest_stage; regression |

Confirmed documentation gap: EN validator table lines 117–123 and KO lines 191–197 omit exact IDs. “Quest eligibility” is a vague alias for the minimum-stage check. The “Quest stage” row mixes regression from `quest_stage_monotonicity` with unauthorized targets enforced by `action_policy`. A correction should expose the IDs/conditions and separate their attribution, not change results or invent checks.

Python7, Godot6 display families and DISC-001–007 remain separate vocabularies, not a one-to-one mapping. The live public projection exposes operation/actorRole/subjectType, but not complete actor/fact/stage/knowledge values. It therefore does not by itself supply a fully reproducible concrete typed-action instance. Any worked example must label declaration-derived values separately from observed values and mark non-applicable/missing fields explicitly.

## Additional live QA / 추가 실제 게임 QA

The unchanged `research/development-cases/ontology-map-20261023-01/actual-game-driver.cjs` was run against the production dashboard with the installed Playwright and explicit Chromium executable, DPR 2, separate fresh output directories.

- Headed attempt: `NOT_PASS`. The route's unchanged yaw guard stopped movement; snapshots show yaw 0 before movement and −1.49 at final capture. Root cause is not established by these observations; no silent camera correction or assertion weakening was applied.
- Headless attempt: stage-zero denial, lens pickup, mount/stage 2, fresh disclosure, authorized redisplay, map1440 and map390 all passed. **Overall `NOT_PASS`**: four page errors, each `WrongDocumentError: The root document of this element is not valid for pointer lock.`, failed continuous diagnostics. Console-error, request-failure and HTTP-error lists were empty. Do not equate seven passing component gates with full acceptance.
- Fresh disclosure was allowed with different prior/next hashes and `fresh_disclosure`. Authorized redisplay was allowed with equal hashes and `redisplay_no_mutation`. PRECONDITION and REACHABILITY were out_of_scope in these disclosure explanations, not PASS.
- The 390 px inspection is desktop reflow/keyboard inspection, not a physical-mobile gameplay test. Headless results do not establish headed-native acceptance.

Local, non-publication receipts and snapshots: `/private/tmp/trace-rpg-signal-audit-1792794307824/`. `summary.json`, `001-fresh-signal-regressions.json`, `002-jev-advisory.json`, `003-production-native-input.json`, `004-production-headless-input.json`, and both browser subdirectories retain the exact commands and observations. These temporary local paths are not promised permanent publication artifacts.

## Interview boundary / 다음 인터뷰의 경계

The prior choice to show **mechanism and comparison together** remains settled; do not ask the same question again. The frozen comparison still has 60 authored cases per arm (48/4/8), general-rule and ontology unsafe/mismatch 0, unchecked unsafe 51 = unauthorized44 + redisplay-mutation7, and mismatch60. It does not show ontology superiority. The coding case remains n=1, CLI6 and zero independent repeats; this audit adds no independent development sample.

A useful next decision is the **primary outcome for a prospective matched-information rule-change development comparison**: completion time, residual defects, or evidence/repair traceability. Existing data does not establish a winner. A chosen endpoint must later freeze its start/end, unit, safety gates and independent-run design; bilingual paper and affected game changes follow that agreed contract, not this audit alone.

Withdrawn review claims: “invented eligibility predicate” was too strong; the issue is alias/attribution. Fig.2's Table III reference correctly targets the ontology-role table; adjacent Table II is a different float, not a wrong reference.

Related: [[wiki/reports/2026-10-23-ontology-map-development-case]], [[wiki/queries/2026-10-23-signal-data-types-interview]], [[wiki/concepts/trace-rpg-controller]], [[wiki/concepts/evidence-and-claim-status]].
## Interview decision / 인터뷰 결정 — 2026-10-23

The user selected **검증 통과까지 걸린 시간 / time to pass validation** as the primary endpoint. The selected option explicitly keeps defect checks as mandatory quality gates. This resolves the primary-endpoint question; it does not authorize a new experiment, implementation, paper revision or deployment.

Operational definition for the subsequent protocol: one task-run, measured in seconds, from receipt of the same complete rule-change request and evidence to the first observed pass of every task-specific mandatory check frozen before the run. Keep a continuous task clock across planning, edits, tools, provider waiting and repairs/resumes; do not sum cumulative counters across invocations. Retain start/end provenance and the exact acceptance receipt. A faster incomplete or unsafe patch is not a successful completion.

Failure, timeout and unfinished runs remain in the assigned-run accounting and are reported as not completed; do not report their stop time as successful completion time or silently remove them from the comparison. Independent-run count, task matching, resource/intervention rules, stopping budget and acceptance-set details still require a frozen prospective protocol. No new measurements or ontology-superiority result follows from this selection. The previous n=1 case, fixed60 comparisons and fresh live-QA NOT_PASS remain unchanged.

사용자 선택은 1차 지표를 고정한 것이다. 정확한 대조 실험 프로토콜 전체가 확정됐다는 뜻은 아니며, 한영 논문과 게임의 후속 변경은 그 프로토콜과 별도의 합의 범위에 따른다.

## 추적 가능성 추가 / Adding traceability — 2026-10-23

User addition: **판단,수정의 추적가능성도 넣고싶어**. Include **decision and repair traceability** alongside the selected time endpoint. Working hierarchy: time-to-pass-validation remains primary; traceability is a key secondary endpoint; hard-validity and defect checks remain mandatory quality gates. Inclusion is recorded; the operational definitions below are proposals for the prospective protocol, not measured results or a claim that the full protocol is frozen.

추적 가능성은 모델의 숨은 사고 과정이나 사후 설명의 그럴듯함이 아니다. 외부에서 관찰 가능한 **요구·입력 → 근거·적용 규칙 → 실제 검사·결정 → 수정 → 재검증·상태 영향**의 연결을 검증한다. Coding-agent repair traces and game-action/state traces remain distinct but may be linked through task, attempt, artifact and replay references.

| Endpoint / 지표 | Proposed observation / 측정 제안 | Boundary / 경계 |
|---|---|---|
| Primary: time / 1차: 시간 | Seconds from the same complete request to first pass of all pre-frozen required checks | Fast incomplete/unsafe work is not successful completion |
| Decision traceability / 판단 추적 | Independently verified evidence/rule/check/decision/state-effect links, with applicable required fields defined before collection; report verified and observed attempt counts together | Actual check statuses, not every possible check assumed PASS; links do not prove hidden internal reasoning |
| Repair traceability / 수정 추적 | Verified triggering error or requirement → attempted code/configuration change → revalidation result, for each actual repair attempt | Failed repairs can be fully traceable; traceability is not repair success |
| Supporting audit / 보조 검증 | Independently resolve artifact references, relevant conditions and reported transitions; replay checks deterministic correspondence where applicable | Field presence, plausible rationale or replay equality alone does not establish correctness/safety |

Use an arm-neutral observer inventory to reconcile **all** decision/repair attempts, including retries and failed attempts; agent-authored trace lists alone do not establish the denominator. Missing trace records count as missing coverage, not exclusions or passes. If the observer inventory itself is incomplete, coverage is indeterminate rather than an apparently complete percentage. Repair traceability is N/A only when zero repair attempts are independently established, not merely when the repair log is empty. An explicitly recorded and verifiable stage-not-reached is different from an unexplained missing artifact.

두 비교군에 동일한 원시 기록·관찰 조건과 공통 감사 기준을 적용한다. 일반 규칙군에 없는 온톨로지 전용 문서 양식을 점수 조건으로 강요하거나, 측정 중 한쪽에만 추가 수정 힌트를 주지 않는다. 외부 원시 근거에서 동일한 기준으로 연결을 검증하며 판단·수정 추적 비율은 따로 보고한다. 시간과 추적 비율을 임의 가중합으로 합치지 않는다.

The independent methods reviewer accepted this as an interview proposal and identified the denominator-completeness and traceability-versus-repair-success corrections incorporated above. Assessor independence, audit sampling/adjudication, attempt boundaries, retries, required links and thresholds still need prospective freezing. No new measured percentages, human benefit, ontology superiority, paper/game source changes or deployment are established.
