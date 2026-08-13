# Response to Reviewers / 심사 의견에 대한 답변

Manuscript: TRACE-RPG: A Trace-Linked Symbolic Commit Gate for Generated Events in an Interactive
Game World

Date: 2026-08-13 · Decision under response: Major Revision (Devil's Advocate: Reject on integrity)

Every comment is tagged `RESOLVED`, `PARTIALLY_ADDRESSED`, or `REBUTTED`. Nothing is left untagged.
Where a comment is rebutted, the rebuttal is argued rather than asserted, and where a comment is
only partially addressed we say so instead of claiming completion.

Three of the reviewers' findings were defects in claims that had already passed our own
claim-faithfulness gate. We reproduced each one by direct inspection before accepting it, corrected
the gate's verdict rather than defending it, and added three mandatory checks derived from what it
missed. We are grateful for findings that our own process should have caught.

---

## Editor-in-Chief

| # | Comment | Status |
| --- | --- | --- |
| EIC-1 | Observed Godot engine evidence exists in the project but the manuscript disclaims engine-loop measurement; the disclaimer is stale | `RESOLVED` |
| EIC-2 | The trust boundary has a hole the paper documents but does not close | `RESOLVED` |
| EIC-3 | Missing prior-work families inflate apparent novelty | `RESOLVED` |
| EIC-4 | The repair-arm table stages a comparison its data cannot support | `RESOLVED` |
| EIC-5 | "Auditable" in the title overclaims relative to the mechanism | `RESOLVED` |
| EIC-6 | P1–P3 are called propositions but are neither proved nor machine-checked | `RESOLVED` |
| EIC-7 | No data-availability statement in a paper whose thesis is reproducibility | `RESOLVED` |
| EIC-8 | Internal editorial housekeeping has leaked into the body text | `RESOLVED` |
| EIC-9 | Conditional-compilation scaffolding must not reach submission | `RESOLVED` |
| EIC-10 | Tiny denominators should be presented as cases, not ratios | `PARTIALLY_ADDRESSED` |
| EIC-11 | Give the reader the adoption cost per commit | `REBUTTED` |

**EIC-1.** The disclaimer was false, not merely stale, and we have corrected it rather than softened
it. The introduction now reports the headless engine timing explicitly and bounds it precisely: one
scripted canonical fixture at a fixed seed, a per-request figure that measures local fixture handling
rather than model or network inference, and a 16.7 ms frame budget that **was not met** in a
five-sample capture whose first sample was an order of magnitude slower than the rest. We report the
failed budget rather than omitting it. We do not attribute the outlier to startup, because the trace
does not establish that cause.

**EIC-2.** Closed in code, not in prose. Both parsers now delegate to a single
`parse_candidate_mapping` in `contracts.py`. The retired boundary sentinel was **kept** as a
closed-boundary regression fixture that feeds one payload through both parsers and requires
agreement; the pilot reports `parser_parity_on_unknown_keys` and fails if either parser drifts. Both
now reject with the identical message. We preserved the replay parser's strictness about omitted
optional fields deliberately — that strictness is what detects record corruption — so we claim
parity only for unknown-key handling and say exactly that in the docstrings.

**EIC-3.** Added, with citations verified through the same three-index process we use for the rest of
the bibliography: narrative mediation (Riedl, Saretto & Young, AAMAS 2003), classical planning
applicability (Fikes & Nilsson 1971), runtime enforcement (Schneider 2000), authored-logic
interactive drama in this journal's predecessor title (Evans & Short, IEEE TCIAIG), and belief-aware
narrative planning (Ware & Siler, AIIDE 2021). We state plainly that we did not invent interposition
and restate the contribution as the evidence layer bound to the gate under an untrusted generative
proposer. The "approved 36-source pool" framing is deleted; the reviewer was right that it made the
gap true by construction.

**EIC-4.** The table is now one row per callback-and-case pair, read from the frozen per-case
records. The tautology is visible in the table itself: the policy-restore callback commits exactly
the case whose defect class it assigns fields for. Its caption says "Not a Comparison".

**EIC-5.** "Auditable" is out of the title, along with "Neuro-Symbolic", "Event-Sourced", and the
plural "Game Worlds".

**EIC-6.** We did not manufacture proofs under revision pressure; we removed the claim to have
them. The four statements are relabelled I1–I4 as implementation invariants under the encoded
contracts, the text says explicitly that the pilot tests their mechanisms with deterministic fixtures
"rather than presenting general theorems", and no proof language remains in either language. The
formerly vacuous antecedent is now disclosed in place: I2 holds "provided every proposal and repair
callback returns", and the manuscript adds that the runtime does not enforce callback deadlines, so
I2 is not a wall-clock termination guarantee.

**EIC-7.** Added in both languages, including the caveat that the earlier packet's provenance commit
did not resolve every declared input. A reviewer should learn that from us, not discover it.

**EIC-8.** Both leaks removed from the body text.

**EIC-9.** Resolved in the final copy-edit. Both manuscripts directly include the three required
figures and directly input the language-matched generated results and tables. The conditional
fallback machinery was removed, so an absent required artifact now stops the LaTeX build.

**EIC-10 — partial.** The repair table is now per-case, so the smallest denominators are gone from
it. The accounting table still uses ratios. We judged the footnote naming the construction invariant
to be the more important fix and did not want to churn the accounting table in the same revision.

**EIC-11 — rebutted.** We decline to add a per-commit cost figure. The only timing we have is from
one scripted fixture at one seed on one machine; publishing it as "adoption cost" would create
exactly the kind of number this revision spent its effort removing. The reviewer's underlying point
is correct and it belongs in the confirmatory study with a real workload.

---

## Reviewer 1 — methodology

| # | Comment | Status |
| --- | --- | --- |
| R1-1 | One fixture per error code is too thin to claim the gate works; no coverage argument | `PARTIALLY_ADDRESSED` |
| R1-2 | Repair arms at n=2 invite a causal reading the text disclaims | `RESOLVED` |
| R1-3 | Absence of p-values is correct, but three arms side by side still imply comparison | `RESOLVED` |
| R1-4 | 62 assignments is an inflated-looking denominator | `RESOLVED` |
| R1-5 | The oracle is circular: same authors wrote validator, fixtures, and expectations | `PARTIALLY_ADDRESSED` |
| R1-6 | Check whether a fixture could pass vacuously | `RESOLVED` |

**R1-1 — partial.** We now state what the fixture set does and does not establish rather than
claiming coverage. The loader enforces the design — denominator, code coverage, one valid control —
so those are construction invariants; the run adds that each negative fixture reached its declared
code rather than a different one. A genuine coverage argument needs held-out fixtures authored by
someone who has not read the validator, which is future work.

**R1-2 and R1-3.** Both addressed by the per-case table plus prose stating that the reference
callback is not counterexample-guided and that the three arms are a control-flow trace rather than a
strategy comparison.

**R1-4.** The reviewer is right that a single total invites the wrong reading. Every manifest row now
carries a schema-enforced `row_class` of `executed` or `aggregate`, the manifest declares
`executed_row_count` and `aggregate_row_count` alongside the total, both are pinned as schema
consts so a drifting split fails validation, and the builder asserts the partition. The current
release binds 64 rows: 43 executed fixture rows and 21 aggregate summaries. The availability
statement reports the split in both languages, so the total never appears unqualified.

**R1-5 — partial.** We cannot break the circularity within this paper's scope, so we name it
instead: the results section says the agreement is "conformance to an authored structured-field
oracle, not accuracy against independent semantic labels". Breaking it requires independently
labelled cases.

**R1-6.** Checked. The closed-boundary regression is the concrete answer: a fixture that once passed
vacuously now fails the pilot if either parser regresses.

---

## Reviewer 2 — related work and positioning

| # | Comment | Status |
| --- | --- | --- |
| R2-1 | Gap claim is circular, asserted against a self-selected pool | `RESOLVED` |
| R2-2 | "Event-sourced" is uncited, undefined, and architecturally inaccurate | `RESOLVED` |
| R2-3 | Missing runtime-enforcement and shielding literature | `RESOLVED` |
| R2-4 | The comparison table grades competitors on axes they never targeted | `RESOLVED` |
| R2-5 | Preprints are load-bearing for positioning claims | `REBUTTED` |

**R2-1 and R2-3.** Both are addressed by the same revision described under EIC-3: the "approved 36-source pool" framing is deleted, and runtime enforcement is now cited directly (Schneider 2000) as one of the prior lines TRACE-RPG does not claim to have invented.

**R2-2.** The reviewer's architectural point is correct: `WorldState` is a snapshot dataclass, every
record embeds complete prior and post snapshots, and no predicate reads the event prefix. The term
is out of the title and keywords. We did not attempt to retrofit log-derived state.

**R2-4.** The coverage table is gone from the positioning argument, replaced by prose that credits
each prior line for what it targeted.

**R2-5 — rebutted.** No conclusion depends on treating a preprint as archival. S01 is described as a
preprint comparator, S26 as a preprint reporting VLM engagement limitations, and the affect claim
that leaned on S26 was independently downgraded to `verified-scope-limited-preprint` in our claim
ledger before this review. We keep all three, labelled.

---

## Reviewer 3 — clarity and reproducibility

| # | Comment | Status |
| --- | --- | --- |
| R3-1 | The manifest's provenance commit does not contain the code that produced the artifacts | `RESOLVED` |
| R3-2 | No artifact availability statement anywhere in the paper | `RESOLVED` |
| R3-3 | All three figures are illegible at IEEE column width | `RESOLVED` |
| R3-4 | Three of five floats are never cited in either language | `RESOLVED` |

**R3-1.** The reviewer's verification was correct: at the recorded commit the pilot runner did not
exist and only 5 of 14 declared inputs resolved. We committed the runner, manifest, schemas, and
configuration first, then regenerated. The final 2026-08-14 packet records **21 declared inputs,
all of which resolve at tagged commit `c4752df` with matching hashes**, verified by reading each
input out of that commit and recomputing its digest. A `--no-local` pristine clone reproduced all
35 manifest-listed release artifacts byte-identically from that tagged source.

**R3-2.** Addressed as described under EIC-7: a Data and Code Availability section was added to both manuscripts, carrying the provenance caveat rather than omitting it.

**R3-3.** Measured and fixed. The figures placed at scale 0.174, putting the smallest glyph class at
3.30 pt. As two-column floats the scale is 0.355 and the smallest class is **6.75 pt**, clearing the
legibility floor. Verified from the built PDF's embedded image geometry and by rendering the page,
not by inferring from environment width.

**R3-4 — resolved in the final copy-edit.** The evidence-boundary figure is now cited explicitly
in both language versions at the point where generated result-table admission is explained.

---

## Devil's Advocate

| # | Comment | Status |
| --- | --- | --- |
| DA-1 | "Structured repair" is not the mechanism the abstract names; its headline number is analytic | `RESOLVED` |
| DA-2 | 13/13 mixes loader-enforced coverage with observed authored-oracle agreement | `RESOLVED` |
| DA-3 | The entire empirical corpus runs against exactly one world state | `PARTIALLY_ADDRESSED` |
| DA-4 | "Neuro-symbolic" describes a system with zero neural components in the loop | `RESOLVED` |
| DA-5 | Authored constants published as recorded provider telemetry | `RESOLVED` |
| DA-6 | Position against planning operator semantics and mediation | `RESOLVED` |
| DA-7 | Four propositions, zero proofs, no falsifying test | `RESOLVED` |
| DA-8 | No reader changes behaviour; the one decisive number is disclaimed | `REBUTTED` |
| DA-9 | The 62-row denominator counts the pilot's own summary statistics as cases | `RESOLVED` |
| DA-10 | Measurement apparatus larger than the system it measures | `REBUTTED` |
| DA-11 | Submitted with a conditional build harness in place of finished figures | `RESOLVED` |
| DA-12 | Length and undeclared article type | `RESOLVED` |

**DA-1, DA-2, DA-5.** All three verified against the repository and all three corrected. These were
the findings our own gate passed, and the reviewer is right that a gate which cannot catch them is
not yet doing scientific work. The gate has been amended accordingly. On DA-2 specifically we accept
the substance while sharpening the statement: the loader fixes the fixture-set design, so the
denominator and code coverage are invariants, but it does not check outcome equality, so the observed
agreement is real — it is authored-oracle conformance, not an independent rate. The manuscript now
separates the two.

**DA-3 — partial.** The overclaim is removed but the limitation is not remedied. The abstract,
introduction, and conclusion now say "a single authored world state" and the title's plural is gone.
Adding a second world would not answer the reviewer's real point, which is about scale.

**DA-4.** The title, abstract, and keywords no longer claim "neuro-symbolic". We scope the statement
to what we verified: the evaluated pilot executes deterministic symbolic fixtures and does not
evaluate a neural proposal generator.

**DA-8 — rebutted, narrowly.** We accept that no studio engineer can decide to ship from this paper,
and we have stopped implying otherwise. We do not accept that nothing is actionable. The
closed-boundary regression is a concrete, transferable result: a permissive proposal parser paired
with a strict replay parser lets replay reject what commit accepted, and that asymmetry is invisible
to artifact-consistency checking. Any team building a validate-then-commit boundary around a
generative proposer can act on that today. It is a smaller claim than the paper originally made, and
it is the one we now make.

**DA-10 — rebutted.** The reviewer's own analysis concedes the checksums, manifests, replay, and
continuity checks are "real and well-built". A harness larger than the system under test is a normal
property of conformance testing, not a category error. We accept the sharper form of the criticism —
process rigour was deployed where empirical content was required — and that is precisely what the
integrity findings exposed and this revision addresses.

**DA-6.** Addressed as described under EIC-3, which added the planning and mediation lineage the reviewer identified.

**DA-12.** The article type is now declared: this is submitted as a Short Paper. The IEEE ToG short-paper band is 6--8 pages with overlength charges above 6 and references counted, verified at transactions.games on 2026-08-13. The manuscript is 7 pages in English and 6 in Korean. We removed the Confirmatory Extensions section rather than padding toward a full paper, and the page it recovered is what the two-column figures needed.

**DA-7 and DA-9.** Addressed as described under EIC-6 and R1-4 respectively.

**DA-11.** Resolved with F17: the EN/KO sources now use direct required figure includes and direct
generated-fragment inputs, with no placeholder fallback path.

---

## Summary of disposition / 처리 요약

| Status | Count |
| --- | --- |
| `RESOLVED` | 30 |
| `PARTIALLY_ADDRESSED` | 4 |
| `REBUTTED` | 4 |
| Total comments | 38 |

Closed by ID at the Stage-8 checkpoint: I1, I2, I3, F4, F5, F6, F7, F8, F9, F10, F11, F12, F13, F14, F15, F16, F17, F18. F13 and F14 were the two acceptance blockers carried out of Stage 8's first pass and were closed there: the propositions are relabelled as asserted invariants with the vacuous antecedent disclosed, and every manifest row carries a schema-enforced executed-or-aggregate class with the split declared and asserted. The expanded re-audit completed F18 by adding matched EN/KO references to all five figure/algorithm floats and all three tables. It also found that the later F14 runner revision reopened F6 as a release-only provenance item: all 20 input paths existed at `e4c2c77`, but only 19 exact digests matched because that commit contained an earlier runner revision. The 2026-08-14 clean recapture closes F6 with 21/21 exact input digest matches at tagged commit `c4752df` and `dirty=false`.

Open by ID: none among the recorded Stage 8 findings.

Partially addressed comments: DA-3, EIC-10, R1-1, R1-5. Rebutted: DA-8, DA-10, EIC-11, R2-5. Each is argued in place above.

We state closure by finding ID rather than by class, because the Stage 6 classes and the reviewer comment set do not partition the same way: a comment can remain partial while the finding it maps to is closed. No manuscript, camera-ready copy-edit, or F6 clean-recapture item remains open. The expanded Stage-4.5 re-audit and clean tagged input binding pass. No reviewer archive/DOI deposit is claimed. This is the user-accepted simulated Major Revision direction, not a journal acceptance decision.

Class A/B 원고 지적과 F13/F14는 종결됐고, F17은 필수 산출물 직접 입력으로, F18은 5개
figure/algorithm float와 3개 table의 영문·국문 참조로 종결했다. 확장된 Stage-4.5 재감사는
통과했다. 과거 `e4c2c77` packet의 runner digest 불일치로 재개됐던 F6는 2026-08-14 clean
recapture에서 tagged commit `c4752df`에 대한 정확한 입력 digest 21/21 일치와 `dirty=false`로
종결됐다. 심사 archive/DOI deposit은 주장하지 않는다. 이는 사용자가 수용한 모의 Major
Revision 방향이며 저널의 게재 승인 결정이 아니다.
