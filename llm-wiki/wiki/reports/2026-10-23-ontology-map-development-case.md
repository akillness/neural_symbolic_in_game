# Ontology evidence map and actual Codex development case — 2026-10-23

## Conclusion / 결론

This is not a measurement of a language model's hidden state or a seven-dimensional embedding. Eight authored ontology roles organize scenario declarations and evidence. Seven Python checks, six Godot display families and seven disclosure rules are distinct vocabularies. A read-only view shows which checks were actually evaluated and what happened to canonical state.

모델 내부 상태를 7차원 신호로 읽어 낸 연구가 아니다. 저자 작성 온톨로지 8역할로 시나리오 선언과 근거를 정리하고, Python 검사 7개·Godot 표시 6계열·공개 규칙 7개를 구분한다. 읽기 전용 뷰는 실제 평가된 검사와 정규 상태 전이를 보여 준다. 누락·미보고·미실행은 통과가 아니다.

The bounded production deployment is verified at [the dashboard](https://sealed-lighthouse-trace-rpg.vercel.app/dashboard/), with [English](https://sealed-lighthouse-trace-rpg.vercel.app/paper/en.pdf) and [Korean](https://sealed-lighthouse-trace-rpg.vercel.app/paper/ko.pdf) ten-page papers. Final selected-source CI status is recorded in the [presentation final receipt](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-final-verification.json). Git completion must be checked in repository/remote history, not inferred from deployment.

## Concrete ontology structure / 구체적 온톨로지 구조

[Canonical source map](../../../neuro-symbolic-interactive-game-research-2026/game-track/web/dashboard/ontology-map.json) / [deployed JSON](https://sealed-lighthouse-trace-rpg.vercel.app/dashboard/ontology-map.json). Exact identifiers remain in the research source; the game-facing view uses neutral aliases. No secret fact payload is reproduced here.

| Role / 역할 | Source-grounded content / 원본에 근거한 내용 | Frozen expectation references |
|---|---|---|
| World / 세계 | `sealed-lighthouse-v1`; initial reachable locations `harbor_dock`, `lamp_store`; `signal_lens` initially at `lamp_store`. These are declarations, not an observed current player position. | `scope.scenario_id`, `declaration_derivation.stage_axis` |
| Actor / 행위자 | `captain_mira` is the only eligible disclosure actor; policy is checked before actor eligibility. | `scope.eligible_actor_ids`, `M-001`, `M-007` |
| Knowledge / 지식 | Mira knows four canonical fact IDs. Knowledge and prior disclosure history do not themselves authorize disclosure. | `declaration_derivation.knowledge_axis`, `declaration_derivation.prior_disclosure_axis` |
| Fact / 사실 | Initial facts are `dock_saved`, `lighthouse_dark`; four canonical IDs are the union of initial facts and Mira's knowledge. An identifier is not its secret payload. | `scope.canonical_fact_ids`, `declaration_derivation.fact_axis` |
| Policy / 정책 | `keeper_betrayal` is permanently forbidden; `tide_marks_hint` requires `quest.stage ≥ 2`. Policy denial uses the safe deflection and preserves canonical state. | `rule_ids`, `M-007`, `M-008` |
| Quest / 퀘스트 | Initial stage 0 and `dock_saved` flag; disclosure preserves stage. Boundary fixtures test stages 1 and 2, not observed progress. | `declaration_derivation.stage_axis`, `B-003`, `B-004` |
| Action / 행동 | `reveal_hint(actor_id, fact_id)`: fresh authorization adds the requested fact/disclosed ID and increments revision once; the hint additionally adds its declared memory entry. Redisplay rechecks authorization without mutation. | `declaration_derivation.first_disclosure_effect`, `declaration_derivation.redisplay_effect`, `integration_contract.display_assertions` |
| Trace / 추적 | Packet/version, rule IDs, hashes, template and case references connect declarations to evidence. Frozen fixtures are not live events; missing fields cannot establish full state or a pass. | `strata_denominators`, `integration_contract.evidence` |

The map binds frozen packet `sl-npc-disclosure-expectations-v1`, version `1.0.0`, status `FROZEN_EXPECTATIONS_NOT_RUNTIME_RESULTS`, SHA-256 `9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028`, and the declared scenario bytes. These are display/source bindings, not server authentication or model-weight attestations.

## Checks, signals and mutation / 검사·시그널·상태 변경

Python's seven checks are `action_policy`, `precondition`, `object_reachability`, `npc_knowledge`, `forbidden_disclosure`, `quest_stage`, `quest_stage_monotonicity`. Godot's six display families are `POLICY`, `PRECONDITION`, `REACHABILITY`, `KNOWLEDGE`, `DISCLOSURE`, `QUEST STAGE`. The separate disclosure rules are `DISC-001`–`DISC-007`: permanent prohibition, stage denial, actor eligibility, actor knowledge, fresh disclosure, authorized redisplay and denial-preserves-state. They are not a one-to-one mapping or evidence that every check runs for every operation.

| Observed transition / 관측 전이 | Meaning / 의미 | Canonical effect / 정규 상태 영향 |
|---|---|---|
| Stage-zero denial / 단계 0 거부 | The minimum-stage rule rejects the requested hint. Later short-circuited checks are not passes. | Prior and next hashes equal; no mutation. |
| Fresh authorized disclosure / 최초 승인 공개 | Current policy, stage, actor and knowledge checks authorize the hint. | Requested declared effects commit; prior and next hashes differ. |
| Authorized redisplay / 승인 재표시 | Current authorization is checked again; history alone does not authorize it. | Prior and next hashes equal; no duplicate canonical mutation. |

The [mechanism figure](../../../neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_signal_mechanism.svg) and the dashboard follow typed input → ontology relation/rules → actually evaluated checks → decision → canonical state effect. The ontology view has no channel for proposing or committing game actions.

## Fixed-case comparison / 고정 사례 비교

Each arm uses 60 fixed authored cases: 48 normal, 4 boundary and 8 malformed cases. Two rule-change fixtures remain a separate paired comparison. Expectations are declaration-derived, not independent human labels or a random sample.

| Arm / 비교군 | Unsafe outcomes / 안전 위반 결과 | Expectation mismatches / 기대 불일치 |
|---|---:|---:|
| General rule / 일반 규칙 | 0/60 | 0/60 |
| Ontology gate / 온톨로지 게이트 | 0/60 | 0/60 |
| Unchecked isolated / 검증 없는 격리군 | 51/60 | 60/60 |

Unchecked unsafe outcomes decompose into 44 unauthorized disclosures and 7 redisplay mutations. They must not be confused with the 60 expectation mismatches. General-rule and ontology-gate outputs agree on all 60 inputs; this does **not** demonstrate ontology superiority or statistical significance. [Source packet and result entry point](../../../neuro-symbolic-interactive-game-research-2026/research/npc-disclosure/reveal-hint-expectations-v1.json).

## Actual coding evidence / 실제 코딩 증거

[Contract](../../../neuro-symbolic-interactive-game-research-2026/research/development-cases/ontology-map-20261023-01/contract.json), [sealed result](../../../neuro-symbolic-interactive-game-research-2026/research/development-cases/ontology-map-20261023-01/result.json), and [public evidence manifest](../../../neuro-symbolic-interactive-game-research-2026/research/development-cases/ontology-map-20261023-01/public-evidence-manifest.json) describe **one** prospective development task: add the read-only bilingual ontology evidence view to the existing game. This is not a claim that the entire game was newly built in this case.

- Native Codex runtime reports `gpt-6.1-sol` in one linked thread. Six CLI invocations comprise five editing turns and one read-only/no-edit resume; they are not six independent development runs. Independent repeats: zero.
- The initial privacy defect, source-binding defects, read-only no-edit attempt and internal mobile clipping defect were retained with their repairs. QA attempts 01–08 are `NOT_PASS`; 09 passed the older acceptance checks; 10 passed after the additional mobile-content geometry repair. Do not rewrite all earlier attempts as failures or discard their receipts.
- The frozen case recorded 62 passing checks, an actual Web build, real-input denial/fresh-disclosure/redisplay, keyboard opening and non-mutating inspection at 1440×900 and 390×900. Later release validation adds 43 publication-source, 44 presentation and22 visual-validator tests: [focused receipt049](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/049-frozen-affected-regressions.json) records 171 tests = 62 + 43 + 44 + 22, plus23 passing subtests separately; [paired-paper receipt050](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/050-frozen-paired-papers.json) retains ten-page EN/KO publication checks. Neither enlarges the development sample.
- Provider-returned model identity, revision and price/cost are unavailable (`null`). Runtime selection is not independent provider-weight attestation. Cumulative token counters are not summed across resumes; engine event time, outer CLI elapsed time and whole-task elapsed time are different measurements.
- Jev's retained advisory was negative (`evidence_supports=no`, `p_yes=0.27`, selected-answer confidence 0.73), unvalidated and `proposal_only`. It is not approval or gameplay authority. Historical `gpt-5.6-sol`, the fixed 60-case comparison and NPC88 are not relabelled or pooled with this case.

Publication-source checks reject wrong map schema, packet path/id/version/status, scenario path and digests. An independent frozen bilingual-clause oracle catches specified polarity reversals; it deliberately rejects unreviewed paraphrases and is **not** a general natural-language semantic validator or human gold.

## Production verification / 프로덕션 검증

Deployment `dpl_75HRZ3UGnVtADdvZnFUJaG9espYY` is observed `READY` at the [production alias](https://sealed-lighthouse-trace-rpg.vercel.app) and [generated deployment](https://sealed-lighthouse-trace-fflmsgady-akillness-projects.vercel.app). All 18 staged dashboard, game and paper assets returned HTTP 200 with matching byte counts and SHA-256 hashes; `/` returned 307 to `/dashboard/`. One headed desktop Chromium session with native keyboard/mouse input and DPR 2 passed all eight gates: stage-zero denial, lens pickup, mount/stage 2, fresh disclosure, authorized redisplay, map 1440, map 390 and continuous diagnostics. Console/page/request/HTTP errors were each 0. This is not a second coding run or efficacy experiment; 390 px is desktop reflow/keyboard inspection, not physical-mobile gameplay.

[Presentation production acceptance](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-browser/actual-game-acceptance.json) and [presentation asset checks](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-http-assets.json) retain the observations. Current [EN](../../../neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.pdf) / [KO](../../../neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.pdf) PDFs are 675846 / 631282 bytes, each 10 pages with 0 Type3 fonts. Four SVGs and tables are roomier; tables retain 4 pt padding, `arraystretch=1.20` and standard IEEE 10 pt type, with properly typeset LaTeX math. The selected R5 engine render remains separate scripted replay/capture evidence. **G4/full G6 remain `FIX`; human benefit, fun, productivity, efficacy and ontology superiority remain unestablished.**

## Provenance / 출처

Evidence date: 2026-10-23. Evidence level: authored frozen declarations plus primary execution/build/browser receipts. Raw original receipts and historical inputs were not rewritten; public derivatives separately retain raw/public SHA values. Publication security review approved 110 case file bindings, 48 command-stream bindings and ten QA receipt bindings after masking 55 local-account ownership entries. The repository's existing license/provenance boundaries remain in force; no new provider-model license or third-party rights claim is made here.

The [2026-10-23 pre-refinement final receipt](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/final-verification.json) and [pre-presentation source snapshot](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/pre-presentation-source-snapshot.zip) remain historical and untouched. Their CI status does not establish the presentation revision's final CI or Git completion; consult the current presentation receipt and repository/remote history separately.

Related: [[wiki/concepts/trace-rpg-controller]], [[wiki/concepts/hard-validity-soft-adaptation]], [[wiki/concepts/evidence-and-claim-status]], [[wiki/projects/trace-rpg-paper-2026]]. Historical source-bound interview reports remain unchanged.
