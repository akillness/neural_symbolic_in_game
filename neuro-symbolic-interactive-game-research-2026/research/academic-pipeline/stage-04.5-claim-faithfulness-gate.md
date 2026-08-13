# Stage 4.5 Claim-Faithfulness Integrity Gate (L3) / 4.5단계 주장 충실성 무결성 게이트

Status: **PASS — expanded post-revision re-audit executed; clean release lock remains blocked**

> **Current packet note (2026-08-13):** the expanded audit below supersedes the corrected BLOCK
> while preserving both the deficient original audit and its Stage-6 correction as history. The
> L3 gate now passes because the current EN/KO claims match the implementation and disclosed
> evidence boundary. This is not an archival-release pass: the frozen packet still records a dirty
> tree and only 19/20 exact input digests match at its recorded commit.

## Final expanded re-audit (2026-08-13) / 최종 확장 재감사

Audited sources:

- EN source SHA-256: `6ca9954206fdfde056de92729ecc7f0871b1a55ffc7f1b683ad02f0768737863`
- KO source SHA-256: `308eadc1f2cfce82e4826bf7c698114ead13590f2030579317bf8a9dc088a675`
- EN PDF SHA-256: `553da2f886d72cc9cbdb79ffc333ee72647080b7a2d3ff490c37ee077d7a7504`
- KO PDF SHA-256: `da62f77305bae7fecfb6fdf0ea836430974a0f9fa04a3b38cdae4888abf51ec8`
- bibliography SHA-256: `5ca42d5d172ef72028f2c33e33d1f90dab18223c05021d2a77920e6f1ef0ef4e`
- pilot result SHA-256: `f6c76abba4c728849912e90382e8df9079738f128706c13a5a649e45d37f7bfd`
- pilot SHA manifest SHA-256: `a2c208f7e852e85e057c4737f7c91b9ac177659c0a1ec0584a21b79e461e875c`

The first expanded pass did not pass. It found six claim defects and one remaining camera-ready
reference defect that the earlier remediation record had missed. Each was corrected in matched
English and Korean text, both PDFs were rebuilt, and the entire audit was restarted before this
verdict was recorded.

| ID | Initial class | Finding in the pre-correction revision | Final repair |
| --- | --- | --- | --- |
| E45-01 | `OVERSTATED` | “an order of magnitude slower” was not supported by all four five-sample Godot traces | report the exact first-sample range, 98.760--116.667 ms, and label it startup-sensitive rather than a stable benchmark |
| E45-02 | `SCOPE_MISMATCH` | $c_t=(G_t,q_t,m_t)$ placed an event prefix inside canonical state even though `WorldState` is snapshot-based and no validator reads a log prefix | use $c_t=(G_t,q_t)$ and state that terminal history is separate and not used for log-derived state |
| E45-03 | `UNSUPPORTED` | the bridge was said to export only after commit although its schema carries observation, proposal, validation, reject, fallback, and commit events | describe the bridge as a versioned event interface and reserve canonical mutation for a valid commit |
| E45-04 | `UNSUPPORTED` | 20/20 exact input hashes were said to match the packet's recorded commit | disclose the observed 19/20 digest match, the earlier runner present at the commit, and the frozen runner revision's dirty-tree-only provenance |
| E45-05 | `SCOPE_MISMATCH` | the AI disclosure denied result interpretation despite AI-assisted evidence auditing and interpretation | disclose prose/code/test assistance, command orchestration, auditing, and interpretation while retaining deterministic runners as the value source |
| E45-06 | `UNSUPPORTED` | an anonymized reviewer archive was described as already available without an evidenced archive | describe present repository contents and make clean tagged recapture a prerequisite for any archive/DOI claim |
| E45-07 | camera-ready | `alg:commit` and three result/validator tables still lacked explicit text references | cite all five figure/algorithm floats and all three tables in both languages |

### Final claim inventory and classification

Compound sentences were split when they depended on different evidence anchors. Forty-two claim
families were re-audited across the complete manuscript rather than only the abstract and
introduction.

| Surface | Claim families | Primary evidence |
| --- | ---: | --- |
| Abstract | 9 | implementation bodies, generated pilot fragments, explicit non-claims |
| Introduction and contributions | 13 | contracts, validator/runtime, engine packet, scope statements |
| Guarantee and architecture body | 7 | `contracts.py`, `validator.py`, `runtime.py`, bridge schema/projector |
| Pilot results and accounting | 6 | pilot JSON/CSVs, assignment manifest, generated fragments |
| Godot engine/render statements | 3 | retained v5 summaries, render manifest, PNG bindings |
| AI disclosure and availability | 2 | recorded workflow and current SHA manifest |
| Conclusion | 2 | bounded synthesis of the same evidence and non-claims |
| **Total** | **42** | |

| Class | Count |
| --- | ---: |
| `FAITHFUL` | 42 |
| `OVERSTATED` | 0 |
| `UNSUPPORTED` | 0 |
| `SCOPE_MISMATCH` | 0 |

### Expanded mandatory checks

| Check | Exact observation | Result |
| --- | --- | --- |
| Reference-implementation body | `_structured_repair` deletes `validation`/`attempt` and reads `state.action_policies`; the paper calls it a policy-restore oracle, not counterexample-guided repair | pass |
| Construction invariant | `load_manifest` enforces all 12 implemented codes exactly once plus one valid control; 13/13 is labelled a loader construction invariant | pass |
| Telemetry provenance | the two populated adapter cases pin 10.0/100/20 and 12.0/110/22 as JSON-Schema `const`; they are called synthetic accounting fields | pass |
| State/log boundary | `WorldState` has snapshot fields and no event-prefix member; current text keeps terminal history separate and denies log-derived state | pass |
| Bridge scope | the schema enumerates eight event types; current text no longer says bridge export occurs only after commit | pass |
| Parser and mutation boundary | both candidate parsers call `parse_candidate_mapping`; unknown keys reject, and `_apply_valid` revalidates before mutation | pass |
| Pilot numeric provenance | 13/13 construction invariant; repair 0/2, 0/2, 1/2; detectable faults 10/10; known boundary 1/1; sentinels 2/2 with 0 safety passes; parser regression 1/1; adapter 1+1+5/7; guards 3/3; provenance 43+21=64 | pass |
| Engine numeric provenance | four v5 fixture summaries contain five frame samples each; the first is largest in all four, range 98.760--116.667 ms; 0/4 pass the 16.7 ms budget | pass |
| Bundle integrity | all 35 artifact and 20 working-tree input hashes recompute (55/55) | pass |
| Recorded-commit provenance | manifest commit `e4c2c77`; all 20 paths exist, but only 19 exact digests match; the runner blob at that commit is an earlier revision, and both manuscripts disclose exactly that | pass for claim faithfulness; release remains blocked |
| Bilingual parity | three equations, five figure/algorithm floats, three tables, eight label/ref pairs, 76 citation instances, 42 unique citation keys, and identical experimental fraction multisets | pass |
| Citation identity | 42 entries: 39 `VERIFIED`, 3 `PREPRINT`, 0 `UNMATCHED`, 0 `HALLUCINATED` | pass |
| `TODO-RESULT` firewall | `C-RESULT-001` through `C-RESULT-005` remain `TODO-RESULT`; no positive efficacy phrasing appears | pass |
| PDF build | `make check`: EN 7 pp, KO 6 pp, zero Type-3 fonts, overfull boxes, undefined references/citations, or missing characters | pass |

### Final gate decision

The expanded L3 claim-faithfulness gate is **PASS_WITH_DISCLOSED_RELEASE_BLOCK**. Stage 5 remains
valid and all current manuscript claims are faithful to their cited source/code/artifact boundary.
No designed fixture, engine trace, screenshot, or generated presentation artifact is promoted into
a model, participant, usability, immersion, affect, retrieval, memory, or population-efficacy
result. `C-RESULT-001` through `C-RESULT-005` remain `TODO-RESULT`.

The single remaining release gate is the clean committed/tagged recapture. The current packet's
19/20 exact recorded-commit digest match is honestly disclosed, so it does not block claim faithfulness;
it does block any claim that the package is a clean archival release.

> ## Correction notice / 정정 고지
>
> The original verdict below recorded 22/22 `FAITHFUL` and unblocked Stage 5. Stage 6 peer review
> then found three defects that this gate should have caught, and all three were independently
> reproduced. The original verdict is retained unedited for the audit trail; it is not the current
> finding.
>
> | Claim | Original class | Corrected class | Basis |
> | --- | --- | --- | --- |
> | A04 "structured counterexamples for bounded repair" | `FAITHFUL` | **`OVERSTATED`** | `_structured_repair` discards the counterexample (`del validation, attempt`) and reconstructs policy fields from authoritative state |
> | A07 "exact case counts" incl. 13/13 | `FAITHFUL` | **`SCOPE_MISMATCH`** | `load_manifest` enforces the fixture-set design (denominator 13, all 12 codes covered, one valid control), so those are construction invariants; it does not enforce outcome equality, so the observed expected-code agreement is real but is authored-oracle conformance, not an independent success rate. The claim conflated the two. |
> | A08 non-claim list incl. "no engine-loop measurements" | `FAITHFUL` | **`OUTDATED`** | observed Godot 4.7.1 headless runs exist in the project working tree |
> | B1 (body, `main.tex:161`) "provider-response latency ... is historical fixture metadata" | **not audited** | **`OVERSTATED`** | the six adapter telemetry values are pinned as JSON-Schema `const`; "historical" implies a provider interaction that never occurred |
>
> Corrected totals over the 22 audited abstract/introduction claims: 19 `FAITHFUL`,
> 1 `OVERSTATED` (A04), 1 `SCOPE_MISMATCH` (A07), 1 `OUTDATED` (A08).
>
> B1 is additional and was **outside the original audit scope**: the gate audited only abstract and
> introduction sentences, so a numeric-provenance claim in the body was never examined. That scope
> restriction is itself a gate defect, corrected by mandatory check 3 below.
>
> Under fail-closed semantics this is a **BLOCK**, not a pass.
>
> Why the gate missed them: the audit traced each mechanism claim to an implementing symbol and
> confirmed the symbol existed, but never read the reference repairer's body, never checked whether
> a reported ratio was enforced by its own loader, and never traced telemetry values to their schema
> declaration. Artifact-to-artifact consistency was verified while the artifacts were consistently
> wrong together.
>
> Remediation: Stage 8 revises both manuscripts; the three checks below are added as mandatory.
>
> ### Mandatory checks added to this gate
>
> 1. **Reference-implementation body read.** For every mechanism named in the abstract, read the body
>    of the function that the evaluation actually invokes — not merely the symbol the prose names.
> 2. **Construction-invariant test.** For every reported ratio, check whether the harness can execute
>    at all when the ratio fails. A ratio enforced by a loader precondition is an invariant, not a
>    result.
> 3. **Telemetry provenance trace.** For every numeric attributed to a provider, runtime, or device,
>    trace it to its origin. A value pinned as a schema `const` is synthetic fixture metadata and may
>    never be described with recording vocabulary.
>
> See `stage-06-peer-review.md` and `stage-08-revision.md`.

---

## Original verdict (2026-08-13, superseded) / 원래 판정 (대체됨)

Status as recorded at the time: **PASS_WITH_SCOPE_BOUNDARIES**

Snapshot date: 2026-08-13

Audited revision: `ea96f2e` (Stage 4 pilot frozen at `3958c09`; bundle re-verified at audit time)

Gate semantics: fail-closed. Any `OVERSTATED` or `UNSUPPORTED` abstract/introduction claim
blocks Stage 5. This audit found none, so Stage 5 is unblocked.

게이트 판정 기준은 fail-closed다. 초록·서론의 주장 중 `OVERSTATED` 또는 `UNSUPPORTED`가
하나라도 남으면 Stage 5로 진행할 수 없다. 이번 감사에서는 해당 항목이 없으므로 Stage 5가
차단 해제된다.

## Audit method / 감사 방법

The audit is mechanical wherever a mechanical check is possible, and the checks are reported with
their observed counts rather than as a summary verdict.

1. Every abstract sentence and introduction sentence was extracted from `paper/latex/en/main.tex`
   and treated as a candidate claim (9 abstract, 13 introduction).
2. Each mechanism claim was traced to the implementing source symbol, not merely to prose.
3. Every numeric assertion in both manuscripts was matched against the frozen pilot summary.
4. Both manuscripts were compared for label, float, equation, citation, and numeric parity.
5. The manuscripts were swept for superiority, improvement, efficacy, generality, proof, and
   security vocabulary, and every hit was read in context.
6. The five `TODO-RESULT` efficacy claims were searched for as positive assertions.
7. The frozen Stage 4 bundle checksums were recomputed.

## Mechanical check results / 기계적 검사 결과

| Check | Observation | Result |
| --- | --- | --- |
| Numeric fidelity | every fraction asserted in `en/main.tex` and the generated fragments appears in `pilot-summary.csv` | 0 unbacked numbers |
| Bilingual numeric parity | EN and KO generated result prose carry the identical fraction multiset `{0/2, 1/1, 1/2, 10/10, 13/13, 2/7, 3/3×2}` | equal |
| Label parity | `alg:commit`, `fig:architecture`, `fig:evidence`, `fig:repair`, `tab:validators` | identical in both |
| Float and structure parity | 3 equations, 1 table, 4 figures, 10 sections per manuscript | identical |
| Citation parity | 81 cite instances, 36 unique keys, identical key set in both | identical |
| Bibliography closure | 36 bib entries; 0 cited-but-absent; 0 present-but-uncited | closed |
| `TODO-RESULT` firewall | `C-RESULT-001`--`005` searched as positive assertions in both manuscripts | 0 asserted |
| Ledger-to-artifact consistency | `C-PILOT-001`--`005` recomputed against the pilot CSVs and assignment manifest | 5/5 consistent |
| Frozen bundle integrity | 32 artifact and 14 input SHA-256 entries recomputed | 46/46 intact |

The assignment manifest declares `assignment_count = 62` and carries exactly 62
`expected_provenance_by_key` entries, so the frozen denominator is internally consistent.

## Claim classification / 주장 분류

Abstract claims, traced to the body section that carries their evidence:

| ID | Claim | Body anchor | Class |
| --- | --- | --- | --- |
| A01 | Fluent or schema-valid text does not establish executability, authorization, or consistency | Introduction | `FAITHFUL` (motivation, not result) |
| A02 | The controller isolates untrusted proposals from state mutation | Architecture; Problem Definition | `FAITHFUL` |
| A03 | Type-strict parser for known fields; unknown top-level fields ignored rather than rejected | Architecture, Trust Boundary | `FAITHFUL` |
| A04 | Rejected candidates receive counterexamples for bounded repair; successful candidates are defensively revalidated | Architecture, Validate--Repair--Commit | `FAITHFUL` |
| A05 | Assignment-complete records link outcomes to unkeyed SHA-256; semantic replay reconstructs encoded transitions; continuity checks reject disconnected histories | Architecture, Integrity and Replay | `FAITHFUL` |
| A06 | Evaluation uses purposive deterministic fixtures rather than population inference | Pilot Method | `FAITHFUL` |
| A07 | Generated artifacts report exact case counts and outcomes | Pilot Method; Pilot Results | `FAITHFUL` |
| A08 | The evidence verifies neither repair provenance nor live-model, player, affect, retrieval, or engine performance | Discussion; Threats | `FAITHFUL` (explicit non-claim) |
| A09 | The work provides an auditable transaction protocol and a reproducible basis for later studies | Conclusion | `FAITHFUL` (capability, not efficacy) |

All 13 introduction sentences resolve to the same anchors; I10 (contribution list), I11
(deterministic pilot centre), I12 (absence list), and I13 (future confirmatory studies) are
`FAITHFUL` and are the claims that bound the rest.

No claim was classified `OVERSTATED`, `UNSUPPORTED`, or `SCOPE_MISMATCH`.

## Verified mechanism traces / 검증된 메커니즘 추적

Each mechanism claim was confirmed against the implementing symbol so that the audit does not rest
on prose agreeing with prose.

| Claim | Implementing symbol | Observed behaviour |
| --- | --- | --- |
| A03 known-field strictness | `experiment.candidate_from_mapping` | requires 5 fields, type-checks known fields, and silently ignores unrecognized top-level keys |
| A03 replay strictness | `runtime._candidate_from_json` via `_require_exact_keys` | rejects both missing and extra top-level keys |
| A04 defensive revalidation | `runtime._apply_valid` | revalidates immediately before mutation and refuses to apply an invalid candidate |
| A05 continuity | `runtime.replay_trace_jsonl` | enforces prior-state continuity between adjacent records |
| A05 disconnection refusal | `experiment` trace-path guard | raises on a disconnected episode before appending |
| A05 unchanged-state invariants | `ExperimentRecord.__post_init__` | adapter failures, controller failures, and fallbacks must leave `prior_state_hash == final_state_hash` |

The two parsers are intentionally different: the proposal boundary is permissive about unknown
keys while the replay boundary is exact. A03 describes the proposal parser, and the manuscript
states that limitation in the abstract, in the Trust Boundary subsection, and as boundary sentinel
`boundary-extra-candidate-field`. This is a documented contract-strictness limitation, not a
safety property.

두 파서는 의도적으로 다르다. 제안 경계는 알 수 없는 키에 관대하고 재생 경계는 정확 일치를
요구한다. A03은 제안 파서를 서술하며, 원고는 이 한계를 초록, Trust Boundary 절, boundary
sentinel `boundary-extra-candidate-field`에서 각각 명시한다.

## Risk-vocabulary sweep / 위험 표현 점검

Twenty-one risk tokens were found in the English manuscript and read in context. Every occurrence
is one of three admissible forms, and none asserts an unsupported result:

- negation of an efficacy claim, for example "not evidence that TRACE-RPG outperforms that or any
  other system" and "does not yet demonstrate portability to a commercial engine";
- an explicitly scoped statement, for example "can establish mechanism behavior only for its frozen
  cases";
- an attributed statement about prior work, for example "constrained decoders improve output
  structure".

The Korean manuscript's two risk tokens are both negations with the same meaning as their English
counterparts.

## Residual boundaries carried forward / 이월되는 경계

These are limitations, not gate failures. They were already disclosed in the manuscripts and remain
disclosed after this audit.

1. Encoded validity covers encoded predicates only; semantic omissions are not measured.
2. Unkeyed SHA-256 detects accidental or tested mutation, not an actor who recomputes checksums.
3. Semantic replay reconstructs the recorded transition and continuity; it does not authenticate or
   re-execute repair generation.
4. The proposal parser ignores unknown top-level candidate fields.
5. Single-process writer ownership is assumed; concurrent-writer safety is untested.
6. `C-RESULT-001`--`005` remain `TODO-RESULT` with no evidence.

## Gate decision / 게이트 판정

| Field | Value |
| --- | --- |
| Claims audited | 22 (9 abstract, 13 introduction) |
| `FAITHFUL` | 22 |
| `OVERSTATED` | 0 |
| `UNSUPPORTED` | 0 |
| `SCOPE_MISMATCH` | 0 |
| Blocking findings | 0 |
| Stage 5 | unblocked |

Stage 5 may proceed to citation verification. This gate does not approve the manuscript for
submission and does not convert any designed-fixture observation into an efficacy result.

이 게이트는 Stage 5 진행만 허용한다. 원고의 투고 승인이나 설계 fixture 관찰의 효능 결과
승격을 의미하지 않는다.
