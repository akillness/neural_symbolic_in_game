# TRACE-RPG Research Package 2026

> Status: the Stage 6 revise-and-resubmit direction has been accepted and the evidence-generating game-track revision is in progress. No confirmatory efficacy result has been produced; `C-RESULT-001`--`005` remain `TODO-RESULT`. Existing numbers remain deterministic authored-fixture conformance counts.

TRACE-RPG never writes an LLM proposal directly into canonical game state. Each successfully parsed proposal becomes a typed candidate event and is committed only after an externally supplied action policy and deterministic checks over preconditions, reachability, NPC knowledge, disclosure, and quest stage. An invalid candidate yields structured validation errors and may receive a bounded repair opportunity; adapter and controller failures remain classified terminal rows. Knowledge-graph retrieval and game-engine integration remain separate confirmatory tracks connected through the versioned event contract; neither is represented as completed pilot evidence.

## Visuals

All six SVGs are produced by `scripts/generate_readme_visuals.py`. The V2 footer, V3, and V4 are read directly from the frozen pilot CSVs and the claim ledger, so their numbers cannot drift from their sources. Solid elements are implemented and exercised by the pilot; dashed elements are specified, unimplemented, and carry no evidence.

### V1 · Trust boundary

![Trust boundary: learned proposal, symbolic authority](visuals/system-architecture.svg)

The proposer may observe the affect estimate `z_t`, graph retrieval, and temporal memory, yet none of them holds commit authority. Canonical state changes only through `T(c_t, a_t)` after the gate passes. Encoded validity is validity for encoded predicates only, and the shared candidate-key contract rejects unknown top-level fields at both proposal and replay boundaries.

### V2 · One transaction

![Parse, validate, bounded repair, defensive check, commit](visuals/commit-transaction.svg)

If no candidate within budget validates, canonical state remains unchanged; a failed initial candidate may still be repaired and committed. Every completed candidate attempt is recorded before the terminal outcome. The repair-arm figures in the footer are read from `repair-arm-summary.csv`.

### V3 · Every pilot observation

![Every pilot number, generated from the frozen artifact](visuals/pilot-evidence.svg)

Each denominator counts designed cases for that row alone, so rows are not comparable to one another. `0/2` and `5/7` are designed outcomes, not regressions. No confidence interval, significance test, or causal comparison is claimed.

### V4 · Claim ledger status

![Claim ledger status](visuals/claim-status.svg)

Designed-fixture evidence never promotes itself into an efficacy claim, and a verified status is revoked if an upstream trace or analysis hash changes.

### V5 · Academic pipeline status

![Academic pipeline status](visuals/research-workflow.svg)

The original Stage 4.5 `22/22` pass is retained only as a superseded audit record: Stage 6 later
reproduced three claim defects and one unaudited body-level telemetry defect. Stage 8 corrected the
manuscript and parser contract, and Stage 9 completed the short-paper formatting and AI-use
disclosure. Stage 5 still verifies all 36 bibliography identities without an unmatched or
hallucinated entry. A clean-commit Stage 10 reproducibility lock and any independent efficacy study
remain pending. See [`research/academic-pipeline/stage-04.5-claim-faithfulness-gate.md`](research/academic-pipeline/stage-04.5-claim-faithfulness-gate.md)
and [`research/academic-pipeline/stage-08-revision.md`](research/academic-pipeline/stage-08-revision.md).

### V6 · Planned confirmatory design (not executed)

![Planned confirmatory experiment design](visuals/confirmatory-design.svg)

## Journal target and evidence bar

The primary candidate is **IEEE Transactions on Games**, whose scope directly covers game AI, player modelling, and game evaluation. **Knowledge-Based Systems** is the method-first alternative; **IEEE Transactions on Affective Computing** becomes relevant only if affect inference is an independently strong contribution; **Entertainment Computing** is an application and user-study alternative. Indexing changes, so SCIE coverage must be rechecked in the Clarivate Master Journal List immediately before submission.

Journal-level claims require a preregistered primary endpoint, pilot-informed prospective power analysis, world- and quest-template holdouts, mixed-effects models, effect sizes with 95% confidence intervals, multiplicity correction, independent human evaluation, failure analysis, assignment-complete outcome records, and complete proposal traces when a proposal outcome exists.

Detailed venue gate: [`research/journal-targets.md`](research/journal-targets.md)

## Research questions

- RQ1: Does a symbolic commit gate reduce impossible world states and forbidden disclosures across model scales?
- RQ2: Is counterexample/unsat-core repair more sample-efficient than blind retry?
- RQ3: Do graph retrieval and temporal memory improve long-horizon consistency without collapsing narrative diversity?
- RQ4: Can uncertainty-calibrated affect adaptation improve target-curve tracking without regressing hard validity?
- RQ5: Do controller gains replicate across a ten-model screen and a three-model confirmatory stage?

## Quick start

```bash
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
uv run python scripts/validate_harness.py
./scripts/validate_game_track.sh
uv run python examples/headless_demo.py
uv run python examples/recorded_experiment.py
uv run python scripts/generate_readme_visuals.py
```

This repository runs the local policy validator, bounded repair/fallback, operation/state-hash JSONL
replay, a network-free recorded-response adapter, and the Godot 4.x headless *Sealed Lighthouse*
policy-mirror slice. The game slice is engine-local conformance evidence only: it exercises quest
progression, gated disclosure, failure nonmutation, save/load, replay, authored fault fixtures, and
stable-envelope schema projection. Real Python↔Godot authorization transport, ten-model inference,
persistent live transport, MLflow/energy telemetry, and human recruitment remain unexecuted.

## Layout

| Path | Purpose |
|---|---|
| `paper/latex/en`, `paper/latex/ko` | Authoritative English and Korean IEEE Stage 4 manuscripts and PDFs |
| `paper/en`, `paper/ko` | Superseded future confirmatory-protocol blueprints |
| `configs/` | SSOT for ten models, treatments, scenarios, and metrics |
| `src/nesy_game/` | Deterministic contracts and minimal validator |
| `game-track/` | Engine-neutral contracts, bilingual experimental GDD, Godot headless slice, and frozen concept pack |
| `_workspace/current/` | Single live game-studio production, design, engineering, QA, UI, and ops workspace |
| `research/` | Immutable sources, Scrapling captures, evidence and claim ledgers |
| `harness/` | Agent roles, workflows, and validation gates |
| `../llm-wiki/` | Project wiki and Graphify knowledge graph |
| `visuals/` | Source SVGs for the README and manuscript, generated by `scripts/generate_readme_visuals.py` |
| `scripts/` | Validators, pilot runner, and the paper-figure, table, and README-visual generators |

## Stage 4 paper and bounded pilot

The authoritative IEEE short-paper drafts are `paper/latex/en/main.pdf` and
`paper/latex/ko/main.pdf`. Their tables are generated from
`research/academic-pipeline/stage-04-pilot/pilot-results.json`: gate agreement `13/13`
across 12 encoded error codes; repair-arm commits `0/2`, `0/2`, and `1/2`; named
detectable integrity faults `10/10`; one separately declared repair-provenance boundary
replay-accepted `1/1`; adapter outcomes 1 commit, 1 symbolic fallback, and 5 classified
failures out of 7; assignment guards `3/3`. These are raw authored-fixture counts, not
live-model, player, or population efficacy estimates.

Rebuild and verify both PDFs with `make -C paper/latex all`. The build preserves SVG
sources, creates high-resolution PNG inclusions to avoid Type 3 fonts, and rejects page-count,
Type 3 font, missing-glyph, undefined-reference, citation, and overfull-box regressions.

## Reproducibility boundary

- LLMs/VLMs propose candidates or soft signals; they never constitute canonical world state.
- SMT/rule checking guarantees only encoded constraints. Semantic false negatives are measured separately.
- Synthetic players are stress-test instruments, not evidence of human experience.
- Raw sources and execution traces are immutable, and paper tables must be generated from trace IDs.
- “Open weight” is not treated as a synonym for “open source”; every model retains an explicit license and policy record.

## Experimental game track

*The Sealed Lighthouse* is an 8--12 minute target, turn-based narrative investigation micro-RPG
chosen through a five-round deep interview. Its primary planned experiment uses structured text and
canonical state. A separately labelled secondary VLM/UI track may use the four pre-generated,
checksum-locked concept images under `game-track/assets/concepts/`; image generation never occurs
during an experiment. Start with `game-track/design/gdd.en.md`,
`game-track/design/paper-crosswalk.en.md`, and `configs/experimental-game.yaml`.

The human-study surface is protocol and tooling only. No participant has been recruited and no
personal telemetry or human outcome exists. Godot/headless measurements do not promote any
`C-RESULT-*` claim.

## Execution order

1. Pilot scenario difficulty, validator omission rates, and human-rating variance.
2. Freeze the analysis plan and primary endpoints; determine sample size through power analysis.
3. Screen ten models cheaply and promote three through a preregistered Pareto rule.
4. Run the confirmatory 3-model × 6-system × 3-track experiment and ablations.
5. Admit only independently audited, assignment-complete and outcome-classified runs; require a complete trace when a proposal outcome exists, while retaining classified terminal failures for which no proposal trace can exist.
