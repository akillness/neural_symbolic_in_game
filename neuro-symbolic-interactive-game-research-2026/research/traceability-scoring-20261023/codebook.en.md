# Traceability-scoring codebook (proposal)

**Status:** `PROPOSED_NOT_VALIDATED`; this is a project-authored measurement protocol, not a certified standard and not a measured result.

## 1. Construct and unit of analysis

The construct is **recoverable correspondence among observable requirements, artifacts, activities, decisions, repairs, and outcomes**. It is not hidden chain-of-thought, developer skill, task success, correctness, safety, human comprehension, or ontology superiority.

Before prospective collection, freeze:

1. the stage schema and event taxonomy;
2. the arm-neutral observer inventory `U_d` for each dimension;
3. required-link lists `L_d(u)`, applicability rules, source/version rules, and outcome-status vocabulary;
4. the clock and acceptance-set versions; and
5. assessor access, blinding, and adjudication order.

A unit is an observer-inventoried attempt, decision, repair, requirement, change, or audit/replay target as specified below. A CLI invocation, decision, repair, check record, and task-run are **different unit types**. Six invocations in one thread are not six independent runs.

## 2. Binary link anchor

For every required link, assign `1` only if an assessor can resolve the exact source/version, verify the claimed relationship against raw or frozen evidence, and record a supporting locator. Field presence, a plausible graph, a test name, a hash alone, or a later explanation is insufficient.

Assign `0` and exactly one primary reason when the link is not verified:

| reason | operational meaning |
|---|---|
| `missing` | the required record or locator is absent; no empty log may prove zero activity |
| `stale` | the record exists but points to an older or otherwise inapplicable revision/version |
| `contradicted` | accessible evidence conflicts with the claimed relationship or status |
| `inaccessible` | the required evidence cannot be accessed under the frozen assessor procedure |
| `unverified` | evidence is present but the relationship, chronology, or actual execution cannot be established |

Do not convert any of these reasons into `PASS`. Record actual outcome separately as `PASS`, `FAIL`, `NOT_RUN`, `STAGE_NOT_REACHED`, `OUT_OF_SCOPE`, or `MISSING`. A traceable failure remains a failure. `STAGE_NOT_REACHED` can explain a guarded predecessor but never counts a later check as executed or passed.

## 3. Six dimensions

| ID | Dimension and binary unit | Required links / positive anchor | Complete-chain numerator and denominator | Source basis |
|---|---|---|---|---|
| **TR01** | **Identity and activity binding.** Unit: each required artifact-reference slot in an observer-inventoried activity. | Bind task/run/attempt, exact artifact revision or digest, producing or using activity, and responsible actor. `1` only when every required identity/activity field is resolved to the frozen source/version and locator. | `n_01 =` slots with every required identity/activity link verified; `N_01 =` all applicable slots required by the frozen stage schema for the neutral activity inventory. | `SRC01`, `SRC03` |
| **TR02** | **Decision evidence chain.** Unit: each observable decision (including coding and game-action decisions, reported separately). | Verify request/input → applicable rule/requirement version → actual evaluated check/result → emitted decision; verify what ran, not what could have run. | `n_02 =` decisions with every applicable chain link verified; `N_02 =` all decisions in the neutral observer inventory that require a chain. | `SRC01`, `SRC02`, `SRC03` |
| **TR03** | **Decision-to-effect correspondence.** Unit: each decision that requires an observable effect record. | Connect decision to observed state/artifact outcome, including committed diff or transition, denied/no-op result where applicable, and before/after evidence. A hash equality alone is not semantic correctness or safety. | `n_03 =` decisions with all required effect links verified; `N_03 =` all inventoried decisions requiring an outcome record under the frozen schema. | `SRC01`, `SRC03`, `SRC05` |
| **TR04** | **Repair chain.** Unit: each actual repair attempt reconciled from independent change/event records. | Triggering failure or unmet requirement → attempted corrective change package → exact revalidation execution → observed result or unresolved state. Reruns without new edits remain attached to the same change package; a new repair boundary is declared before a new edit. | `n_04 =` repair attempts with every chain link verified; `N_04 =` all actual repair attempts in the reconciled neutral inventory. If independently verified that zero repairs occurred, report `N_04=0` and `N/A`; an empty repair log is not evidence of zero. | `SRC01`, `SRC02`, `SRC03` |
| **TR05** | **Bidirectional requirement coverage.** Unit: each predeclared requirement and each inventoried in-scope change, reported as two separate views. | Forward: requirement → implementing artifact → relevant verification evidence. Reverse: in-scope change → justified requirement. Code presence or a test name is not semantic linkage. | Forward: `n_05F/N_05F =` fully linked requirements / all predeclared requirements. Reverse: `n_05R/N_05R =` justified changes / all inventoried in-scope changes. Never average the two. | `SRC02`, `SRC03` |
| **TR06** | **Independent evidence exercisability.** Unit: each predeclared artifact-audit or replay target. | A non-author assessor exercises the target with documented inputs, dependencies, commands, tolerances, and retained receipt; record agreement/disagreement. This is not automatically reproduction of the scientific result or another development run. | `n_06 =` successfully independently exercised targets; `N_06 =` all predeclared audit/replay targets. Report attempted and not-attempted targets separately. | `SRC03`, `SRC05` |

## 4. Denominators and missingness

The denominator is built from an arm-neutral observer's raw process, tool, change, and event records, not from an agent's self-selected trace list. Include retries, failures, no-op decisions, deferred decisions, and guarded stages within the frozen taxonomy.

- **Complete-chain denominator:** for dimension `d`, `N_d = |{u ∈ U_d : applicable(u)=true}|`; `n_d` counts units for which every required link in `L_d(u)` is verified. Report `n_d/N_d` only when `inventory_complete=true` and `N_d>0`.
- **Per-link denominator (optional and never interchangeable):** `l_d / m_d`, where `l_d = Σ verified links` and `m_d = Σ applicable required links` across the same frozen units. State the link list and units. A per-link rate must not be called complete-chain coverage.
- **Incomplete inventory:** report `coverage=INDETERMINATE`, observed counts, and the inventory gap. Do not publish a seemingly complete percentage.
- **Verified zero:** `N/A` is permitted only when independent evidence establishes non-applicability. For TR04 this means independently verified zero actual repair attempts; an empty log is not enough.
- **Stage guard:** record `STAGE_NOT_REACHED` with the verified predecessor/guard and reason. It may satisfy a status-explanation link, but does not make a downstream validation `PASS`. A mandatory audit/replay target simply not attempted is not `N/A`.
- **Polarity:** missing, inaccessible, stale, contradicted, and unverified are non-passing link states. They never become a success through denominator removal.

## 5. Reliability, blinding, and nested units (prospective protocol)

Use at least two assessors who did not generate the traces or implement the artifact. Freeze training, authorship, organisational ties, access, and blinding failures. Blind arm/model labels where feasible. Preserve each assessor's pre-adjudication binary/status ratings and locators; adjudicate only after ratings are locked. Do not calculate reliability on consensus labels.

Report per dimension: unit counts, category frequencies, missing/applicability counts, disagreement matrices, raw agreement, and nominal Krippendorff's alpha for binary/status labels **where estimable**. Report uncertainty where estimable. If there is no variation or support is inadequate, report `UNDEFINED` or `NOT_ESTIMABLE`, never perfect reliability. Links are nested within decisions, repairs, requirements, targets, and runs; do not treat every edge as an independent study sample. No pilot or alpha estimate was executed for this proposal.

## 6. Fault controls and invariance

Freeze controls before seeing scores. On isolated copies seed: remove a receipt, swap an attempt ID, bind an old artifact revision, reverse a decision/status, or omit a failed repair. Report `detected_valid_corruptions / seeded_valid_corruptions` and `false_alarms / clean_control_units`; retain malformed or inapplicable controls separately. The control author must not disclose mutation keys to blinded assessors.

Add clean duplicates, irrelevant decorative additions, and semantics-preserving format changes. These invariance controls should not change a grade. A text log, table, ordinary rule file, or ontology can satisfy the same semantic link; no score requires RDF, ontology triples, a particular layout, or decorative fields.

Record audit burden and instrumentation overhead symmetrically: assessor minutes per unit, evidence objects inspected, access failures, and any logging or intervention cost. Audit burden is a reporting quantity, not a traceability score.

## 7. Primary time endpoint remains separate

For a future matched comparison, predeclare **time-to-first-all-predeclared-validation-pass** as continuous task-clock seconds from receipt of the matched complete request/evidence to the first exact receipt passing every mandatory check. Waiting, edits, tools, provider waits, and repairs remain on the clock. Every assigned run receives a completion status; failed, unfinished, and timed-out runs do not receive successful-completion times.

The current **5942.665 s** is a descriptive wall-clock value from an older case, not a newly predeclared prospective metric. It must not be combined with TR01–TR06 or treated as a model-inference latency estimate. The future whole-game comparison is planned in `research/development-comparison-20261023/plan.en.md`, `plan.ko.md`, and `protocol.json` with `study_label=development-comparison-20261023`, `task_id=GODOT-MICROGAME-FULL-001`, and `status=PROPOSED_NOT_EXECUTED`; this codebook does not execute that plan.

## 8. Illustrative examples (not collected trials)

1. **Beautiful ontology, wrong receipt (negative):** the ontology contains every expected edge but points to an older revision. The affected link is `0/stale`, and the complete-chain unit is `0`; an ordinary text log binding the correct execution may earn `1`. Formatting contributes nothing.
2. **Excellent trace, failed repair (positive traceability, failed outcome):** trigger, actual diff, rerun, and failing result are all resolved. TR04 can be `1` while outcome is `FAIL` and completion is unachieved. A second observed repair omitted from the log remains in the denominator with missing links; zero log entries cannot yield `N/A`.
3. **Early denial and partial QA:** a guard stops execution and evidence shows no state commit. Decision/status/effect links can be complete; downstream checks are `STAGE_NOT_REACHED`, not `PASS`. Seven passing component gates do not overturn a newer additive overall `NOT_PASS` when pointer-lock errors or the yaw guard remain.

These examples are didactic constructions, not collected trials or measured scores.

## 9. Current-case evidence boundary

Known descriptive facts are: one operator-assisted Codex task in one linked thread; six native turn contexts and six CLI invocations; five editing turns, four code-repair rounds, and one read-only/no-edit resume; a 62-pass receipt; a dated QA10 `PASS` under its then-current acceptance set; later overall additive QA `NOT_PASS`; and 107/107 released file/hash bindings matching (102 manifest entries plus five actual images). The 107/107 result is byte-integrity evidence, not an independent study, publisher approval, authenticity proof, or efficacy result.

Unknown or unestablished are: provider-returned immutable model identity/revision, seed, monetary cost, model-only latency, comparator arm, independent repeats (current `n=1`, independent repeats `0`), independently scored TR01–TR06 values, causal superiority, ontology necessity, human/player benefit, and publisher approval. Do not relabel legacy cohorts or old E2 outcomes as this case. The latest overall `NOT_PASS` and the dated QA10 `PASS` are distinct records under distinct acceptance contexts.

## 10. Source note

The five primary sources are enumerated in `sources.json` as `SRC01`–`SRC05`. They provide conceptual support for provenance, bidirectional traceability, artifact review, coding reliability, and verification/validation distinctions; none certifies this project-authored rubric. JCGM metrological traceability is a calibration-chain concept and is not a synonym for software evidence traceability. Cite direct URLs without adding new bibliography identifiers or redistributing full text.

**Next action:** freeze a prospective task's inventory, link lists, status vocabulary, and assessor procedure before collecting any TR01–TR06 score.
