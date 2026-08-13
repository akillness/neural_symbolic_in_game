# Stage 8 Author Revision / 8단계 저자 개정

Date: 2026-08-13

Input: `stage-06-peer-review.md` (Major Revision; 3 integrity findings, 6 critical scope findings,
5 major defects, 3 minor items)

## Disposition summary / 처리 요약

| Class | Items | Resolved | Open |
| --- | --- | --- | --- |
| A — verified integrity failures | I1, I2, I3, F6 | 4 | 0 |
| B — critical scope and positioning | F4, F5, F7, F8, F9, F10 | 6 | 0 |
| C — major defects | F11, F12, F13, F14, F15 | 5 | 0 |
| Minor | F16, F17, F18 | 3 | 0 |

Every Class A, Class B, Class C, and minor item was closed by the Stage-8 manuscript revision. At
that point the separate release re-audit and reproducibility gates remained open.

> **Post-Stage-4.5 re-audit correction:** the expanded final audit passed only after correcting
> additional EN/KO claim and reference defects. It also found that the later F14 runner revision
> was recaptured against an earlier commit: all 20 input paths exist at `e4c2c77`, but only 19 exact
> digests match because its runner is an earlier revision. The current manuscripts disclose that
> historical gap. F6 was reopened only as a clean-release provenance gate, then closed on
> 2026-08-14 by a clean tagged recapture at `c4752df`; no reviewer archive or DOI deposit is claimed.

## Class A — integrity / 무결성

**I1. The abstract named a repair mechanism the code does not implement.** The reference callback
discards the counterexample set and reconstructs policy fields from the authoritative state. Every
occurrence of "counterexample-guided" that pointed at this callback has been removed from the
abstract, the contribution list, and the generated results prose in both languages. The mechanism
section now states plainly that the callback is *not* counterexample-guided, that it is an oracle
upper bound, and that its outcomes must not be read as evidence about any repair method that
consumes counterexamples. The results table was rebuilt as one row per callback-and-case pair read
from the frozen per-case records, so the tautology — the policy-restore callback commits exactly
the case whose defect it assigns fields for — is visible in the table rather than only in prose.

**I2. 13/13 was a loader precondition published as an observation.** The generated results now open
by stating that the loader admits a fixture set only when it isolates every implemented validator
code exactly once, so the 13/13 agreement and the observation of all 12 codes are construction
invariants of the harness rather than measured success rates. What the run adds is stated
separately and narrowly: each isolated negative fixture showed observed agreement with its authored
expected code rather than reaching a different one. The accounting table carries a footnote making
the same point.

**I3. Synthetic telemetry was described with recording vocabulary.** The six adapter latency and
token values are pinned as JSON-Schema `const` in the pilot input schema. The methods section now
says so explicitly and states that they exercise accounting-field propagation only and are not
measurements of any provider, runtime, or device. The results prose no longer reports
"provider-response latency was observed for 2/7"; it reports that synthetic telemetry fields were
populated and propagated for 2/7 assignments.

**F6. The manifest's provenance commit did not contain the pilot runner.** At the recorded commit
`3958c09`, `run_conformance_pilot.py` did not exist and only 5 of 14 declared inputs resolved. The
runner, manifest, schemas, and configuration were committed first, then the pilot was regenerated.
At the Stage-8 recapture, commit `26724a6` resolved **20 of 20 declared inputs**. A later F14 runner
revision changed that input after the recorded commit, so the current packet's separately verified
state is 19/20 exact digest matches at `e4c2c77`; all paths exist, but the commit contains an earlier
`scripts/run_conformance_pilot.py`, and the frozen runner revision is dirty-tree-only. This remained
the historical reason F6 was reopened. The final clean recapture binds 21/21 input paths and exact
digests to `c4752df43196761dcc64f02110f32bbaecfa235f`, tagged
`trace-rpg-stage10-inputs-20260814-v1`, with `dirty=false`; F6 is now closed.

## Class B — scope and positioning / 범위와 위치

**F4. One world state.** The pilot executes against exactly one authored state; the whole result set
carries a single distinct state hash. The abstract, introduction, and conclusion now say "a single
authored world state" and the title no longer says "Game Worlds" in the plural.

**F5. No neural proposer.** The evaluated pilot runs deterministic symbolic fixtures and does not
evaluate a neural proposal generator. "Neuro-symbolic" has been removed from the title, the
abstract, and the keywords in both languages.

**F7. No availability statement.** A Data and Code Availability section was added to both
manuscripts. The final re-audit revised it to state only what is currently evidenced: 35 artifact
and 21 input hashes recompute; all 21 paths and exact digests match clean tagged commit `c4752df`,
and all 35 artifact hashes recompute (56/56 total). The statement also says that no reviewer archive
or DOI deposit is currently claimed.

**F8. Novelty asserted against a self-selected pool.** The phrase "within the approved 36-source
pool" is removed. It was internal pipeline language and made the gap true by construction.

**F9 and F10. Uncredited lineage.** "Event-sourced" is out of the title. The related-work section
now credits action interposition as long established and cites five works verified through the same
three-index process used at Stage 5: narrative mediation, classical planning applicability, runtime
enforcement, authored-logic interactive drama in this journal's own predecessor title, and
belief-aware narrative planning. The contribution is restated narrowly as the evidence layer bound
to the gate under an untrusted generative proposer.

## Class C — major defects / 주요 결함

**F11 resolved.** All three mechanism figures rendered at 3.30–4.36 pt at IEEE column width, below
the roughly 6 pt legibility floor, which made the two core mechanism figures unreadable. They are
now two-column floats. Measured from the built PDF's embedded image geometry, the placement scale
went from 0.174 to 0.355 and the smallest glyph class from 3.30 pt to **6.75 pt**; every class now
clears the floor. Verified by rendering the page, not by inferring from environment width.

**F12 resolved.** The proposal parser ignored unknown top-level fields while the replay parser
rejected them, so replay could refuse a candidate that had already committed. Both parsers now
delegate to one shared `parse_candidate_mapping` in `contracts.py`, which owns unknown-key
handling, required-key handling, and value-level validation. The proposal boundary calls it with
`allow_defaults=True` and the replay boundary with `allow_defaults=False`, preserving
persisted-record strictness deliberately: replay must stay strict to detect record corruption. Only
unknown-key handling is claimed identical, and the docstrings say exactly that rather than claiming
the parsers cannot disagree at all.

The retired boundary sentinel was **not deleted**. It is retained as a closed-boundary regression
fixture that feeds the same payload through both parsers and requires them to agree; the pilot now
reports `parser_parity_on_unknown_keys` and fails if either parser drifts back. Both parsers reject
with the identical message `unknown candidate fields: ['unexpected_top_level_metadata']`.

**F15 resolved** as described under I1.

**F13 resolved in the current manuscript.** Former P1--P4 are now I1--I4, explicitly described as
asserted implementation invariants under encoded contracts rather than general theorems. Their
mechanisms are tied to deterministic valid, invalid, repair, fallback, replay, and fault-injection
fixtures. I2 now conditions only on callbacks returning, explicitly states that the runtime does
not enforce callback deadlines, and makes no wall-clock termination guarantee.

**F14 resolved in the current manuscript.** The regenerated manifest binds 64 provenance rows,
reported explicitly as 43 executed fixture rows plus 21 aggregate rows. The manuscript no longer
calls all 64 rows assignments or leaves the executed/aggregate denominator split implicit.

## Minor / 사소 항목

**F16 resolved:** editorial leakage removed from the body text.
**F17 resolved in the final copy-edit:** both manuscripts now directly include the three required
figures and directly input their language-matched generated results and tables. The
`\IfFileExists` and `\pendingartifact` fallbacks were removed, so a missing required artifact is a
hard LaTeX build failure rather than a latent placeholder path.
**F18 resolved after the expanded re-audit:** every one of the five figure/algorithm floats and all
three tables now has an explicit matched reference in both languages.

## Verification / 검증

| Check | Result |
| --- | --- |
| Test suite | 96 tests and 70 subtests pass |
| Ruff lint and format | clean over `src`, `tests`, `scripts`, `examples` |
| Pilot regeneration | deterministic; release bundle refreshed |
| Manifest integrity | 35 artifact + 21 input hashes recompute (56/56) |
| Manifest recorded-commit provenance | `c4752df`, tagged `trace-rpg-stage10-inputs-20260814-v1`; `dirty=false`; 21/21 paths and exact digests match; portable invocation; no absolute user/clone paths |
| Parser parity | proposal and replay reject the same payload with the same message |
| Paper build | `make all` exits 0; no Type-3 fonts, no overfull boxes, no undefined references |
| Page count | EN 7 pp, KO 6 pp, inside the 6–8 short-paper band |
| Figure legibility | smallest glyph class 6.75 pt, measured from PDF image geometry |

## Article type / 논문 유형

The manuscript is submitted as a **Short Paper**. The IEEE ToG short-paper band is 6–8 pages with
overlength charges above 6, and the count includes references (verified at transactions.games,
retrieved 2026-08-13). The empirical core does not support a full paper and was not padded toward
one; the Confirmatory Extensions section was removed and its non-claims folded into the discussion,
which is also what recovered the space the two-column figures needed.

## Remaining gate status / 남은 게이트 상태

The expanded Stage-4.5 re-audit passes, F17/F18 are closed, and the clean committed/tagged recapture
has closed F6. No paper-packet release blocker remains in this disposition record. A reviewer
archive/DOI deposit is not yet claimed, `C-RESULT-001`--`005` remain `TODO-RESULT`, and G4/G6 are
separate game gates.

확장된 Stage-4.5 최종 재감사는 통과했고 F17/F18은 현재 원고에서 종결됐다. Clean
committed/tagged recapture도 F6를 종결했다. 심사 archive/DOI deposit은 아직 주장하지 않고,
`C-RESULT-001`--`005`는 `TODO-RESULT`이며 G4/G6는 별도 게임 gate다. 이 기록은 저널 게재
승인을 뜻하지 않는다.
