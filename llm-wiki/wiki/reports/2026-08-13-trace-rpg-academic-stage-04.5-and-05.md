# TRACE-RPG Academic Pipeline — Stages 4.5 and 5

Status: **STAGE 4.5 ORIGINAL PASS SUPERSEDED; STAGE 5 CITATION-IDENTITY GATE REMAINS PASSED**

Current correction: Stage 6 later reproduced three claim defects and one body-level telemetry defect
outside the original audit scope. The fail-closed Stage 4.5 verdict is therefore not a current pass;
its `22/22` result below is retained as historical evidence of the deficient audit. Stage 8 corrected
the manuscript/parser issues and regenerated the pilot as 2 open sentinels plus 1 closed unknown-key
regression, but a final comprehensive claim-faithfulness re-audit belongs to Stage 10. Stage 5's
36-entry citation-identity result is unaffected.

The Stage 4 packet was approved on 2026-08-13, and the two fail-closed integrity gates that guard
peer review were then executed. Neither gate produced a blocking finding, and neither promoted any
designed-fixture observation into an efficacy result.

## Original Stage 4.5 verdict — claim faithfulness (superseded)

Twenty-two claims were audited: nine abstract sentences and thirteen introduction sentences. All
twenty-two classified `FAITHFUL`, with zero `OVERSTATED`, `UNSUPPORTED`, or `SCOPE_MISMATCH`.

The audit was mechanical wherever a mechanical check was possible:

- Every fraction asserted in the manuscripts appears in `pilot-summary.csv`; zero unbacked numbers.
- English and Korean generated result prose carry an identical fraction multiset.
- Labels, equations, tables, figures, sections, and the 36-key citation set are identical across the
  two manuscripts, and the bibliography is closed in both directions.
- The five `TODO-RESULT` efficacy claims were searched for as positive assertions and none appears.
- `C-PILOT-001` through `C-PILOT-005` were recomputed against the pilot CSVs and the assignment
  manifest; all five are consistent.
- The superseding Stage 8 packet records 35 artifacts and 20 declared inputs; its SHA-256 entries were recomputed and intact after migration.

Mechanism claims were traced to implementing symbols rather than to matching prose. The audit
historically confirmed that the proposal parser `candidate_from_mapping` ignored unknown top-level candidate
fields while the replay parser `_candidate_from_json` rejected them through `_require_exact_keys`.
The Stage 4 manuscripts described that permissive proposal boundary and disclosed it as boundary sentinel
`boundary-extra-candidate-field`. Stage 8 closed the asymmetry: both parsers now reject an unknown key,
and the former sentinel is retained as a negative regression rather than an open limitation.

A risk-vocabulary sweep found twenty-one superiority, efficacy, generality, proof, and security
tokens in the English manuscript. Every occurrence is a negation, an explicitly scoped statement, or
an attributed claim about prior work. The Korean manuscript's two tokens are both negations.

## Stage 5 — citation verification

Thirty-six bibliography entries were verified through metadata APIs only, with no publisher-page
scraping: Semantic Scholar as primary, OpenAlex and Crossref as advisory, and arXiv for preprint
confirmation. A title match counted only at normalized similarity of at least 0.85.

| Status | Count |
| --- | --- |
| `VERIFIED` | 33 |
| `PREPRINT` | 3 |
| `UNMATCHED` | 0 |
| `HALLUCINATED` | 0 |

Every entry was matched by at least one independent index. The three preprints are S01, S02, and
S26, all already described as preprints in the manuscripts.

Seven entries showed a year difference against a matched index. Each was inspected and all seven are
the same benign archival-versus-preprint pattern; for S15, S17, S18, and S33 the differing OpenAlex
record was confirmed to be an arXiv `submittedVersion`, so the bibliography's archival year is
correct and no edit was required.

`S23_yin2026contextualized` was re-checked because Stage 2 had flagged a future-dated issue. Its DOI
resolves in all three indices at similarity 1.0 with volume 58 and article 101194, but the issued
date 2026-09 remains in the future and no issue number is assigned. The citation is verified by
identity and the existing recheck-at-submission note stays in force.

Semantic Scholar returned HTTP 429 for nine entries after three backoff rounds, repeating the
rate-limit condition recorded at Stage 2. This is an index access limitation, not evidence about the
citations; each of the nine is matched by another index, and no entry is reported as verified on the
strength of an index that did not answer.

## What these gates did not do

Stage 4.5 verified that the manuscripts' claims match their own body evidence. Stage 5 verified
citation identity. Neither gate assessed whether each cited work supports the sentence citing it,
which belongs to Stage 6, and neither changed the standing evidence boundary. `C-RESULT-001` through
`C-RESULT-005` remain `TODO-RESULT`, and the pilot remains deterministic offline conformance
evidence with no live model, participant, affect, retrieval, memory, or engine result.

## Canonical artifacts

- `research/academic-pipeline/stage-04.5-claim-faithfulness-gate.md`
- `research/academic-pipeline/stage-05-citation-verification.md`
- `research/academic-pipeline/stage-05-citation-verification.json`
- `research/academic-pipeline/material-passport.json`

Current pipeline: Stage 6 revise-and-resubmit was accepted and actioned; optional Stage 7 was not
activated; Stages 8 and 9 executed; Stage 10 clean-commit reproducibility lock and final re-audit are
pending.

Related: [[wiki/reports/2026-08-12-trace-rpg-academic-stage-04]],
[[wiki/projects/trace-rpg-paper-2026]], [[wiki/concepts/evidence-and-claim-status]].
