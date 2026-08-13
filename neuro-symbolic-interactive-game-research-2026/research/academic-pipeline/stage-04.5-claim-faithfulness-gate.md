# Stage 4.5 Claim-Faithfulness Integrity Gate (L3) / 4.5단계 주장 충실성 무결성 게이트

Status: **SUPERSEDED — original PASS verdict was wrong**

> **Current packet note (2026-08-13):** this document preserves the original pre-Stage-8 audit
> and its later correction. The current pilot packet is a post-Stage-8 rerun with 2 open
> sentinels, 1 closed unknown-key regression, 64 provenance rows (43 executed + 21 aggregate),
> and 35 artifact + 20 input hashes. Older counts and parser findings below are historical.

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
