# Stage 6 Peer-Review Simulation / 6단계 동료심사 시뮬레이션

Date: 2026-08-13

Panel: EIC + R1 (methods) + R2 (related work) + R3 (clarity/reproducibility) + Devil's Advocate,
run in parallel against `paper/latex/en/main.tex` and the frozen Stage 4 artifacts.

> **Post-review resolution note (2026-08-13):** F12 and F14 below are preserved as the panel's
> historical findings. The Stage-8 implementation now derives both parsers from one candidate-key
> contract and rejects unknown top-level keys at both boundaries. The rerun packet reports 43
> executed fixture rows plus 21 aggregate rows, bound as 64 provenance records, with the former
> unknown-key sentinel retained as a 1/1 closed negative regression.

## Meta-review / 종합 판정

**Recommendation: MAJOR REVISION, with three integrity findings that must be fixed before any
resubmission.**

| Reviewer | Recommendation | Score |
| --- | --- | --- |
| EIC | Major Revision | overall merit 4.5/10 |
| R1 methodology | Major Revision | methodology 4/10 |
| R2 related work | Major Revision | 4.5/10 |
| R3 clarity/reproducibility | Major Revision | writing 6/10 |
| Devil's Advocate | Reject (integrity) | overall 2/10 |

The panel agreed on Major Revision except the Devil's Advocate, who argued for rejection on
integrity rather than on missing experiments. The integrity findings were independently reproduced
by the maintainer and are upheld, so the Devil's Advocate position governs the revision even though
the modal recommendation is Major Revision.

### Acceptance gate — every item is must-fix / 재제출 전 필수 수정 항목

"Major Revision" here does **not** license resubmission with the scope findings outstanding. The
gate has two classes and both block:

**Class A — verified integrity failures.** A published claim contradicts the executed code or
artifact. Each was reproduced independently by the maintainer.

| ID | Must-fix |
| --- | --- |
| I1 | Remove "counterexample-guided" wherever the reference repairer is the evidence, or implement a repairer that consumes `validation.errors` |
| I2 | Remove 13/13 as a reported result, or relabel it explicitly as a construction invariant |
| I3 | Reclassify the six adapter telemetry values as synthetic fixture constants; delete recording vocabulary |
| F6 | Regenerate the release packet from a clean committed tree so every declared input resolves at the recorded commit |

**Class B — critical scope and positioning failures.** The paper asserts more than its evidence or
its literature review supports. These block equally.

| ID | Must-fix |
| --- | --- |
| F4 | State that the pilot executes one world state, with its exact size; drop plural "Game Worlds" from the title unless a second world is added |
| F5 | Remove "neuro-symbolic" from title, abstract, and keywords, or evaluate a neural proposer |
| F7 | Add a data/code availability statement |
| F8 | Delete the "approved 36-source pool" framing and restate the gap against named literature |
| F9 | Retitle away from "event-sourced" or implement log-derived state; reconcile `m_t` with the implementation |
| F10 | Add the mediation / Versu / STRIPS / runtime-enforcement lineage |

**Class C — major defects that block acceptance but not resubmission.** These must be fixed before
the paper can be accepted; a resubmission that addresses Class A and B while carrying a documented
plan for Class C may be reviewed.

| ID | Must-fix |
| --- | --- |
| F11 | Re-render all three figures so no glyph falls below ~6 pt at IEEE column width |
| F12 | Close the proposal/replay parser asymmetry, or prove the two cannot disagree on admissible input |
| F13 | Prove P1–P4 or demote them to asserted design invariants, and remove P2's vacuous antecedent |
| F14 | Report executed cases (43) and distinct inputs separately from the 19 aggregate rows |
| F15 | Replace the repair-arm table with a per-case listing that makes the oracle nature visible |

**Minor items (F16–F18)** — editorial leakage, `\IfFileExists` scaffolding, and uncited floats — are
copy-edit fixes required before camera-ready, not resubmission blockers.

A resubmission that fixes Class A but leaves Class B open is still a reject: the integrity fixes
alone would leave a paper whose title and framing overclaim.

Class A와 B는 재제출 차단 항목이고, Class C는 게재 승인 차단 항목이다. Class A만 수정한
재제출은 제목과 프레이밍이 여전히 과장돼 있으므로 여전히 reject다.

## Integrity findings — independently reproduced / 무결성 지적

These three were confirmed by direct inspection, not accepted on the reviewer's word. Each one
passed the Stage 4.5 claim-faithfulness gate, so the gate verdict is corrected in
`stage-04.5-claim-faithfulness-gate.md`.

### I1. The abstract names a repair mechanism the executed code does not implement

`scripts/run_conformance_pilot.py:461` — `_structured_repair` begins with `del validation, attempt`.
The counterexample set is discarded on the first line. The function then reads
`state.action_policies` and assigns `policy.required_preconditions` and `policy.required_effects`
directly into the candidate.

The abstract and contribution list say "structured counterexamples for bounded repair" and
"bounded counterexample-guided repair". The reference repairer is not counterexample-guided. It is
policy reconstruction from the authoritative state — an oracle upper bound, not a deployable repair
method. Its 1/2 result is analytic: it overwrites `preconditions`, so the precondition case commits;
it never touches `required_objects`, so the reachability case cannot.

### I2. The 13/13 headline is a loader precondition, not an observation

`scripts/run_conformance_pilot.py:286-293` — `load_manifest` raises
`"gate fixtures must isolate every implemented validator code exactly once"` unless the fixture set
is a bijection onto `implemented_validator_codes`, plus exactly one valid control. The pilot cannot
execute unless 13/13 already holds by construction. Reporting it as a result carries no information
about the validator.

### I3. Adapter telemetry is synthetic and was described with recording vocabulary

`configs/pilot-manifest.json` supplies `provider_latency_ms: 10.0`, `input_tokens: 100`,
`output_tokens: 20` and `12.0 / 110 / 22`. These are not merely authored: the pilot input schema
pins them as JSON-Schema `const`, so the six values verify accounting-field propagation and nothing
observational. The manuscript called them "historical fixture metadata", which implies a recorded
provider interaction that never occurred.

## Additional substantive findings / 추가 지적

| ID | Severity | Finding | Source |
| --- | --- | --- | --- |
| F4 | CRITICAL | Entire pilot executes against exactly one world state (1 distinct state hash across all rows); the title says "Game Worlds" | DA |
| F5 | CRITICAL | The evaluated pilot has no neural proposer in the loop, yet "neuro-symbolic" is in the title, abstract, and keywords | DA |
| F6 | CRITICAL | Manifest provenance commit `3958c09` does not contain `run_conformance_pilot.py`; only 5 of 14 declared inputs resolve at that commit, and the recorded dirty diff is not in the packet | R3 |
| F7 | CRITICAL | No data/code availability statement anywhere in a paper whose thesis is auditability | R3, EIC |
| F8 | CRITICAL | Gap claimed relative to the "approved 36-source pool" — novelty true by construction | R2, EIC |
| F9 | CRITICAL | "Event-sourced" is uncited, undefined, and architecturally inaccurate: `WorldState` persists full snapshots, no predicate reads `m_t` | R2 |
| F10 | MAJOR | Missing prior-work families: narrative mediation (Mimesis), Versu (this journal's predecessor), STRIPS-style applicability, runtime enforcement/shielding, belief-aware planning (Sabre) | EIC, R2 |
| F11 | MAJOR | All three figures render at 3.3–4.4 pt at IEEE column width; the two core mechanism figures are illegible | R3 |
| F12 | MAJOR | Trust-boundary hole: proposal parser ignores unknown top-level fields while the replay parser rejects them, so replay can reject what commit accepted | EIC |
| F13 | MAJOR | P1–P4 are stated in theorem register with no proof; P2's antecedent is vacuously satisfied by the pilot's callbacks | EIC, DA |
| F14 | MAJOR | The 62-key manifest enrols 19 aggregate summary rows as assignments; 43 rows actually executed | DA |
| F15 | MAJOR | Repair-arm table stages a three-way comparison its n=2 oracle data cannot support | EIC, DA |
| F16 | MINOR | Editorial leakage in body text ("must be rechecked at submission"; citation-provenance bookkeeping) | EIC |
| F17 | MINOR | `\IfFileExists` + `\pendingartifact` scaffolding must not reach submission | EIC, DA |
| F18 | MINOR | Three of five floats are never cited in either language | R3 |

## What the panel did not fault / 반증되지 않은 부분

The Devil's Advocate explicitly abandoned three attack lines after testing them:

- **Unfalsifiable disclaimers.** Rejected. The boundary sentinels publish three cases where the gate
  accepts what it arguably should not, marked `safety_pass=false`. Immunization does not publish its
  own failures.
- **Broken artifact.** Rejected. The full suite passes and the pilot reproduces byte-for-byte.
- **Fabricated citations.** Rejected. Stage 5 holds: 36/36 resolved, 0 hallucinated.

R3 independently confirmed byte-for-byte artifact reproduction, exact EN/KO structural parity, a
197-word abstract, and clean PDF builds with no Type-3 fonts or overfull boxes.

## Score trajectory / 점수 추이

| Gate | Result |
| --- | --- |
| Stage 2.5 pre-write integrity | pass with fail-closed scope boundaries |
| Stage 4.5 claim faithfulness (original verdict) | 22/22 FAITHFUL — **superseded** |
| Stage 4.5 (corrected after Stage 6) | 3 findings reclassified; gate reopened |
| Stage 5 citation verification | 36 entries, 0 hallucinated — upheld |
| Stage 6 peer review | Major Revision; 3 integrity findings |

## Why Stage 4.5 missed I1–I3 / 게이트가 놓친 이유

The Stage 4.5 audit traced each mechanism claim to an implementing symbol and confirmed the symbol
existed and was reachable. It did not read the reference repairer's body, did not check whether a
reported ratio was enforced by its loader, and did not trace telemetry values back to their schema
declaration. Consistency between artifacts was verified; the artifacts were consistently wrong
together.

The gate has been amended with three new mandatory checks so this class of defect fails closed in
future runs.

Stage 4.5 감사는 각 메커니즘 주장을 구현 심볼까지 추적했으나 참조 repairer의 본문, 보고된
비율이 loader에 의해 강제되는지 여부, telemetry 값의 스키마 선언까지는 확인하지 않았다.
아티팩트 간 일관성은 검증됐지만 아티팩트들이 함께 틀려 있었다.
