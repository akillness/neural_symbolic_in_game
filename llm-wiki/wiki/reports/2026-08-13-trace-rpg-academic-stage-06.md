# TRACE-RPG Academic Pipeline — Stage 6

Status: **REVISE AND RESUBMIT — USER DECISION REQUIRED**

The Stage 6 IEEE Transactions on Games peer-review simulation combined EIC, methodology, related
work, clarity/reproducibility, and adversarial-review perspectives. It retained the approved Full
Paper target and did not reinterpret the deterministic Stage 4 pilot as efficacy evidence.

## Meta-review

The topic and staged authorization mechanism fit game-AI and game-software research, but the current
six-page packet is not mature Full Paper evidence. The central finding is a revise-and-resubmit
decision: TRACE-RPG has a coherent proposal/commit trust boundary and strong evidence discipline,
yet lacks independent semantic labels, live model/controller comparisons, held-out game-world
templates, an executed engine path, and participant evidence.

The strongest accept case is a substantially revised reproducibility-first Short Paper. The active
project contract nevertheless remains a Full Paper, so evidence-generating confirmatory work is a
publication gate rather than an optional embellishment.

## Critical revisions

1. Run assignment-complete confirmatory comparisons with an independent semantic oracle, held-out
   worlds/quests, genuine blind retry, live model instances, and uncertainty-aware reporting.
2. Replace the Stage 4 dirty-snapshot bundle with a clean tagged-commit reproduction lock after the
   source revision is final; remove user-specific paths and add availability metadata.
3. Add IEEE-required AI-use disclosure while preserving double-anonymous review constraints.

## Major revisions

- Compare the system against the direct interactive-narrative, shielding/guardrail,
  neuro-symbolic-design, and event-log/replay lineages; weaken the unsupported "closest comparator"
  rank claim.
- Define neuro-symbolic, event-sourced, transactional, and auditable within the narrower implemented
  boundary, or rename them.
- Treat P1--P4 as implementation invariants unless formal proof/model-check/property evidence is
  added.
- Expand the central algorithm to include adapter/controller failures, deadlines, terminal record
  emission, paired persistence, and rollback.
- Resolve the repository license and add code/data availability text through an author decision.
- Execute a headless or real-engine multi-step path before claiming engine relevance.

## Stable evidence boundary

Stage 4.5 remains 22 faithful claims out of 22 audited, with no overstated or unsupported claim.
Stage 5 remains 33 verified citation identities and 3 declared preprints out of 36, with no unmatched
or hallucinated record. These integrity results do not answer the Stage 6 efficacy and novelty
questions. `C-RESULT-001` through `C-RESULT-005` remain `TODO-RESULT`.

Canonical review:
`neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/stage-06-peer-review-simulation.md`.

Next gate: the user must accept, partially accept, or rebut the Stage 6 findings before optional
Stage 7 cross-model review or Stage 8 author revision.

Related: [[wiki/reports/2026-08-13-trace-rpg-academic-stage-04.5-and-05]],
[[wiki/projects/trace-rpg-paper-2026]], [[wiki/concepts/journal-grade-experimental-design]].
