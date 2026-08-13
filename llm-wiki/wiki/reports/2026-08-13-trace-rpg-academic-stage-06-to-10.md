# TRACE-RPG Academic Pipeline — Stages 6 to 10

Status: **EXPANDED FINAL RE-AUDIT AND CLEAN TAGGED RECAPTURE PASSED**

The ten-stage academic pipeline ran to completion on 2026-08-13. The headline result is not that
the manuscript improved, though it did. It is that a purpose-built claim-faithfulness gate passed
three false claims, and adversarial review caught them.

## What Stage 6 found that Stage 4.5 missed

Five reviewers ran in parallel against the manuscript and the frozen artifacts. Four recommended
Major Revision; the Devil's Advocate recommended rejection on integrity rather than on missing
experiments. Each integrity finding was reproduced by direct inspection before being accepted.

1. **The abstract named a repair mechanism the code does not implement.** The reference repair
   callback opens with `del validation, attempt` — it discards the counterexample set — then copies
   the policy-required preconditions and effects straight out of the authoritative state. The paper
   called this "counterexample-guided repair". Its 1/2 commit result was analytic: the callback
   assigns `preconditions`, so the precondition case commits; it never touches `required_objects`,
   so the reachability case cannot.
2. **13/13 conflated a construction invariant with an observation.** `load_manifest` refuses to run
   unless the fixture set isolates every implemented validator code exactly once, so the denominator
   13, the coverage of all 12 codes, and the single valid control are the harness's own precondition.
   The loader does not check outcome equality, so the run does show something — each negative fixture
   reached its declared code rather than a different one — but that is conformance to a self-authored
   oracle, not an independent success rate. One number was reported as if it were the latter.
3. **Synthetic constants were described with recording vocabulary.** The adapter latency and token
   values are pinned as JSON-Schema `const`. The paper called them "historical fixture metadata".
4. **The artifact manifest's provenance commit did not contain the pilot runner.** At the recorded
   commit only 5 of 14 declared inputs resolved.

All three claim defects had passed the Stage 4.5 gate. The gate verified consistency between
artifacts; the artifacts were consistently wrong together. Its verdict is now marked superseded
rather than deleted, and three mandatory checks were added: read the body of the function the
evaluation actually invokes, test whether a reported ratio is enforced by its own loader, and trace
every provider-attributed number to its origin.

## Stage 7

Not activated. `ARS_CROSS_MODEL` was unset. A local Ollama endpoint was reachable but a 7B instance
is not a credible independent verifier for findings that required reading a 2,298-line harness, so
treating reachability as activation would have misreported an optional stage as executed.

## What Stage 8 changed

Class A (integrity) and Class B (scope and positioning) are closed.

The title lost "Neuro-Symbolic", "Event-Sourced", and the plural "Game Worlds": the evaluated pilot
has no neural proposer, persists snapshots rather than deriving state from a log, and runs against
exactly one authored world state. The related-work section now credits action interposition as long
established, citing narrative mediation, classical planning applicability, runtime enforcement,
authored-logic interactive drama in this journal's own predecessor title, and belief-aware narrative
planning — five works verified through the same three-index process as Stage 5. A data and code
availability statement was added, including the provenance caveat rather than hiding it.

Two code-level fixes went beyond wording:

- **Parser asymmetry closed.** The proposal parser ignored unknown top-level fields while the replay
  parser rejected them, so replay could refuse a candidate that had already committed. Both now
  delegate to one shared `parse_candidate_mapping`. Replay stays strict deliberately, because that
  strictness is what detects record corruption; only unknown-key handling is claimed identical. The
  retired boundary sentinel was kept as a parser-parity regression fixture, so drift fails the pilot.
- **Figure legibility.** All three mechanism figures rendered between 3.30 and 4.36 pt, below the
  legibility floor. As two-column floats the smallest glyph class is now 6.75 pt, measured from the
  built PDF's image geometry.

An independently written test suite for the unified parser caught a regression the refactor had
introduced: the shared helper used `not value` where the original used `not value.strip()`, so
whitespace-only identifiers could reach commit. Unified toward the strict side.

## What the expanded Stage 4.5 re-audit found

The camera-ready EN/KO manuscripts were checked again after F17/F18 closure, this time against
function bodies, schemas, the generated PDFs, and both the current worktree and recorded provenance
commit. Seven preliminary defects were repaired before the verdict: the first-frame timing claim was
made exact; the formal context stopped treating event history as validated state; the bridge/event
wording was aligned with all eight supported message types; the clean-commit reproducibility claim
was reduced from a 20/20 digest match to the observed 19/20; the AI-use disclosure was made complete; the availability
statement stopped implying an already-created reviewer archive; and every algorithm, figure, and table
float received an explicit in-text reference in both languages.

After those repairs, all 42 audited claim families were classified `FAITHFUL`; none remained
`OVERSTATED`, `UNSUPPORTED`, or `SCOPE_MISMATCH`. This is a manuscript-faithfulness pass, not
a release-lock pass, and it does not convert any `C-RESULT-*` placeholder into a result.

## Stage-10 clean tagged recapture

The provenance mismatch found by the expanded audit is retained above as history. The 2026-08-14
recapture closes F6 against input commit `c4752df43196761dcc64f02110f32bbaecfa235f`, tagged
`trace-rpg-stage10-inputs-20260814-v1`. The manifest records `dirty=false`; all 21 input paths and
exact digests match the commit, all 35 artifact hashes recompute, and the packet closes at 56/56
hashes. The assignment partition remains 64 rows: 43 executed and 21 aggregate. Its Python
invocation is the portable `uv run python`, and no absolute user or clone path is present.

## Current release gate

| ID | Item | Class |
| --- | --- | --- |
| F13 | I1--I4 demoted to asserted encoded-contract implementation invariants; callback deadlines are not claimed | resolved in current manuscript |
| F14 | 64 provenance rows reported as 43 executed fixture rows plus 21 aggregate rows | resolved in current manuscript |
| F17 | Conditional build scaffolding removed; both languages directly include the final figures | resolved in current manuscript |
| F18 | All five figure/algorithm floats and all three table floats are explicitly referenced in both languages | resolved in current manuscript |
| Claim re-audit | Expanded post-F17/F18 audit: 42/42 claim families faithful | passed |
| F6 release lock | Clean tagged input commit `c4752df`; 21/21 exact input digest matches; 35/35 artifacts; 56/56 total; `dirty=false` | closed 2026-08-14 |
| Archive/deposit | No anonymized reviewer archive or DOI deposit exists in the evidence packet | not claimed; not an F6 failure |

## Standing evidence boundary

Unchanged by all of this. `C-RESULT-001` through `C-RESULT-005` remain `TODO-RESULT`. The pilot is
deterministic offline conformance over one authored world state. The Godot evidence comprises four
authored engine-local fixtures and three trace-bound non-headless render captures; the 16.7 ms frame
budget was not met and no live model, transport, participant, or efficacy result is implied. G4/G6
remain separate game gates.

## Verification

The historical clean-clone suite recorded 96 passing tests. The final re-audit freshly passed 14
targeted candidate-contract, conformance-pilot, and runtime tests; ruff and repository validators are
clean. `make check` exits 0 with no Type-3 fonts, overfull boxes, undefined references, or missing
characters; EN is 7 pp and KO is 6 pp inside the 6–8 short-paper band. Citation identity closes at
42/42 keys, all eight floats are referenced in both languages, and the exact provenance result is
35/35 artifact hashes, 21/21 input paths and exact digests at tagged commit `c4752df`, and 56/56
total hashes, with 64 provenance rows partitioned as 43 executed plus 21 aggregate.

## Canonical artifacts

- `research/academic-pipeline/stage-06-peer-review.md`
- `research/academic-pipeline/stage-07-cross-model-verification.md`
- `research/academic-pipeline/stage-08-revision.md`
- `research/academic-pipeline/stage-09-formatting-and-disclosure.md`
- `research/academic-pipeline/material-passport.json`
- `research/academic-pipeline/stage-04.5-claim-faithfulness-gate.md` (expanded pass; historical superseded verdict retained)

Related: [[wiki/reports/2026-08-13-trace-rpg-academic-stage-04.5-and-05]],
[[wiki/projects/trace-rpg-paper-2026]], [[wiki/concepts/evidence-and-claim-status]].
