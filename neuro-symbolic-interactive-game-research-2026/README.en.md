# TRACE-RPG Research Package 2026

> Status: the user accepted the revision direction produced by the simulated Stage 6 Major Revision review. The expanded claim-faithfulness audit and guided-repair clean tagged input recapture have passed; this closes F6's reproducibility gate, not the separate G4/G6 game gates. This is not a journal decision, paper acceptance, reviewer archive, or DOI deposit. No confirmatory efficacy result has been produced; `C-RESULT-001`--`005` remain `TODO-RESULT`. A separate single-model RQ2 screening packet is reported only as `pilot-only`, apart from the deterministic authored-fixture counts.

TRACE-RPG never writes an LLM proposal directly into canonical game state. Each successfully parsed proposal becomes a typed candidate event and is committed only after an externally supplied action policy and deterministic checks over preconditions, reachability, NPC knowledge, disclosure, and quest stage. An invalid candidate yields structured validation errors and may receive a bounded repair opportunity; adapter and controller failures remain classified terminal rows. Knowledge-graph retrieval and game-engine integration remain separate confirmatory tracks connected through the versioned event contract; neither is represented as completed pilot evidence.

## Evidence map

| Lane | Current evidence | Honest boundary |
|---|---|---|
| Deterministic offline pilot | Parser, validator, repair, replay, integrity, and accounting fixtures over one authored world | Encoded-field mechanism conformance only |
| Live RQ2 screening | One hosted proposer; guided `5/5` versus blind `0/5` only in the deliberately repairable policy-blind cell | `C-PILOT-007/008` only; no population, model-ranking, or `C-RESULT-003` promotion |
| KG/ontology simulation | 43 OKF nodes, 106 reference edges, 24 curated typed edges, 6/6 authored holdouts | Closed-world `simulation-only`; not runtime retrieval or semantic completeness |
| Godot/Web engineering | 4/4 fixtures, 49/49 combined checks, tracked player, desktop production smoke | Authored-fixture and presentation conformance; not usability, fun, G4, or final G6 |
| Confirmatory study | Not executed | `C-RESULT-001`–`005` remain `TODO-RESULT` |

The evidence ceilings for contributions C1–C5, all 45 references across nine topics, the three
experiment lanes, and the engineering lane are cross-checked together in
[`contribution-reference-crosscheck.md`](research/academic-pipeline/contribution-reference-crosscheck.md).

## Visuals

All six SVGs are produced by `scripts/generate_readme_visuals.py`. The V2 footer, V3, and V4 are read directly from the frozen pilot CSVs and the claim ledger, so their numbers cannot drift from their sources. Solid elements are implemented and exercised by the pilot; dashed elements are specified, unimplemented, and carry no evidence.

### V1 · Trust boundary

![Trust boundary: learned proposal, symbolic authority](visuals/system-architecture.svg)

The proposer may observe the affect estimate `z_t`, graph retrieval, and temporal memory, yet none of them holds commit authority. Canonical state changes only through `T(c_t, a_t)` after the gate passes. Encoded validity is validity for encoded predicates only, and the shared candidate-key contract rejects unknown top-level fields at both proposal and replay boundaries.

### V2 · One transaction

![Parse, validate, bounded repair, defensive check, commit](visuals/commit-transaction.svg)

If no candidate within budget validates, canonical state remains unchanged; a failed initial candidate may still be repaired and committed. Every completed candidate attempt is recorded before the terminal outcome. The repair-arm figures in the footer are read from `repair-arm-summary.csv`.

### V3 · Every Stage 4 offline-pilot observation

![Every Stage 4 offline-pilot number, generated from the frozen artifact](visuals/pilot-evidence.svg)

Each denominator counts designed cases for that row alone, so rows are not comparable to one another. `0/2` and `5/7` are designed outcomes, not regressions. No confidence interval, significance test, or causal comparison is claimed.

### V4 · Claim ledger status

![Claim ledger status](visuals/claim-status.svg)

Designed-fixture evidence never promotes itself into an efficacy claim, and a verified status is revoked if an upstream trace or analysis hash changes.

### V5 · Academic pipeline status

![Academic pipeline status](visuals/research-workflow.svg)

The original Stage 4.5 `22/22` pass is retained only as a superseded audit record: Stage 6 later
reproduced three claim defects and one unaudited body-level telemetry defect. Stage 8 corrected the
manuscript and parser contract, and the expanded audit passed 42/42 claim families. Stage 5 now
contains 45 identity-verified references with 0 unmatched or hallucinated entries. Stage 10 binds
22/22 declared inputs, 38/38 artifacts, and 121 provenance rows to the clean guided-repair release
tag. The final Stage 9 bilingual PDFs now include the live-screening and KG-simulation addenda;
both are 8 pages and pass the page-band, Type 3 font, and LaTeX log gates. Independent efficacy
studies and journal submission remain pending. See [`research/academic-pipeline/stage-04.5-claim-faithfulness-gate.md`](research/academic-pipeline/stage-04.5-claim-faithfulness-gate.md)
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

Each question maps to one `C-RESULT-*` claim, and all five are still `TODO-RESULT`. The tables below
separate what the repository has built from what it has measured.

## At a glance

| Question | What exists today | What is still missing |
|---|---|---|
| Does the code run? | Yes — full pytest: 172 passed, 2 skipped; unittest discovery: 131 passed, 2 skipped; deterministic pilot, Godot slice, live public-safe Web build | — |
| Is the pipeline complete? | Yes for the staged repository deliverables through Stage 10, including the final bilingual PDF rebuild and format checks | Independent efficacy studies, journal submission, and a decision remain |
| Is the paper written? | Yes — current bilingual IEEE sources and 8-page PDFs, 45 paper references, ρ(a,E) guided repair, and separate live-screening/KG-simulation addenda | Journal submission, review, and any resulting revision remain |
| **Are the research claims proven?** | **No** | Only a five-call-per-cell RQ2 screening pilot exists; confirmatory multi-model, human, affect, retrieval, memory, and engine-performance studies are missing |

The implementation needed for the current conformance claims is complete. The **confirmatory
experiments are not**: 5 of 21 tracked claims are efficacy claims with no promotion-qualifying
evidence, and they are the ones the research questions ask.

## Experiment design (planned, not executed)

SSOT: [`configs/experiment-matrix.yaml`](configs/experiment-matrix.yaml). This confirmatory matrix has
not been run; the separate RQ2 screening pilot is not a substitute for it. The matrix is recorded so
the scope is auditable.

| Dimension | Stage 1 screening | Stage 2 confirmatory |
|---|---|---|
| Models | 10 (all) | 3 (promoted by frozen Pareto rule) |
| Scenarios per track | 30 | 120 |
| Repetitions | 3 | 5 |
| Controller arms | 6 | 6 |
| Grounding variants | 3 (`none`, `rag`, `kg_temporal_memory`) | 3 |
| Affect variants | — | 2 (`off`, uncertainty-calibrated) |
| Ablations | — | 6 |
| Purpose | Pareto screening; **no causal conclusion** | Preregistered full factorial |

The six controller arms are ordered by how much of the stack they enable, so each comparison isolates
one mechanism:

| Arm | Gate | Repair | Grounding stack |
|---|---|---|---|
| `direct_commit` | none (unsafe baseline, isolated build) | — | — |
| `structural_constraint_only` | schema/grammar only | — | — |
| `validator_rejection_only` | state-relative | none | — |
| `matched_budget_blind_retry` | state-relative | K new proposals, no error feedback | — |
| `structured_repair` | state-relative | K repairs with structured errors | partial |
| `trace_rpg_full` | state-relative + external policy | K repairs + defensive revalidation | full |

| Track | Primary endpoint |
|---|---|
| `world-generation` | `valid_episode_rate` |
| `npc-dialogue` | `hard_dialogue_violation_rate` |
| `affect-adaptation` | `target_curve_rmse` without hard-validity regression |

Controls: seeds `11, 23, 47, 83, 131`; repair budget `K=3`; 60 s timeout; at most 4 proposal-or-repair
calls, matched across the three comparable arms; per-attempt tokens, latency, cost, and failure class
recorded. 28 metrics are catalogued in [`configs/metric-catalog.yaml`](configs/metric-catalog.yaml).

## KG/ontology graph store and proposal simulation

The project now keeps three meanings separate: the sibling Graphify artifact is a document-navigation
index, Python `WorldState` remains the hard runtime authority, and the new SQLite file is only a
repository-local **methods-graph mirror**. The closed application ontology declares 21 node types,
13 relation types, domain/range rules, six validator-predicate mappings, and six executable,
source-scoped competency questions. It is not OWL/SHACL and does not implement runtime graph retrieval.

![Simulation-only KG/ontology evaluation matrix](research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg)

`SL-KG-ONTOLOGY-SIM-001` runs seven fixed strategies over six authored queries × five candidates: 30 candidate scores per strategy and 210 total.
For selected links $S_q$ and one frozen relevant link $G_q$ per query,
$P=TP/(TP+FP)$, $R=TP/(TP+FN)$, $F_1=2PR/(P+R)$,
$MRR=|Q|^{-1}\sum_q r_q^{-1}$ with realistic tie ranks,
$BS=N^{-1}\sum_i(s_i-y_i)^2$, and
$Sem@K=(K|Q|)^{-1}\sum_{q,i}I[domain/range\ valid]$.
The ratchet keeps a strategy only after recall ≥0.80, coverage ≥0.95, `Sem@3=1`, and strict
lexicographic improvement.

Current deterministic packet: **43 OKF nodes, 106 reference edges, 24 curated typed edges, 0 ontology
violations, 6/6 competency questions**. The retained `S2-typed-lexical-loose` strategy recovered
6/6 authored holdouts (`P=R=F1=1.000`, realistic-tie `MRR=0.944`, `BS=0.131`, `Sem@3=1.000`).
These are closed-world construction results, not independent semantic truth, user usefulness,
runtime KG efficacy, long-horizon memory evidence, or support for any `C-RESULT-*` claim.

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_kg_ontology_simulation.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_kg_ontology_simulation.py --check
sqlite3 research/simulation/kg-ontology/latest/trace-rpg-knowledge.sqlite \
  'SELECT relation, COUNT(*) FROM edge GROUP BY relation ORDER BY relation;'
```

Outputs: exact [JSON matrix](research/simulation/kg-ontology/latest/evaluation-matrix.json),
[formula/strategy report](research/simulation/kg-ontology/latest/evaluation-matrix.md),
[TSV trials](research/simulation/kg-ontology/latest/strategy-trials.tsv),
[recommendations](research/simulation/kg-ontology/latest/recommendations.json), SVG, bilingual generated
TeX, hashes, and the ignored runtime SQLite mirror. The machine ontology is
[`knowledge/ontology/trace-rpg-ontology.json`](knowledge/ontology/trace-rpg-ontology.json).

## Paper at a glance

Authoritative sources: [`paper/latex/en/main.tex`](paper/latex/en/main.tex) ·
[`paper/latex/ko/main.tex`](paper/latex/ko/main.tex)

Current rebuilt PDFs: [`English`](paper/latex/en/main.pdf) ·
[`한국어`](paper/latex/ko/main.pdf)

| Item | Value |
|---|---|
| Title | TRACE-RPG: A Trace-Linked Symbolic Commit Gate for Generated Events in an Interactive Game World |
| Venue target | IEEE Transactions on Games, **Short Paper** (6–8 pp band) |
| Current PDF length | EN 8 pp · KO 8 pp; both include the live-screening and KG-simulation addenda and pass the repository paper checks |
| Sections | 11, identical in both languages |
| References | 45 — 42 identity-verified at Stage 5 + 3 verified 2026-08-21 adds, 0 hallucinated |
| Review model | double-anonymous |

What the paper claims, and what it explicitly does not:

| Claimed | Not claimed |
|---|---|
| A typed contract for state, policy, candidate, and record | That any model is better than another |
| A deterministic state-relative commit gate over 12 encoded codes | Player experience or narrative quality |
| Bounded repair with unchanged-state fallback | That the reference repairer is a deployable method |
| Content-linked records, semantic replay, episode continuity | Writer authentication (checksums are unkeyed) |
| Assignment-complete failure accounting | Retrieval, memory, or affect benefit |
| Conformance over **one** authored world state | Generalization to a real game at scale |

Claim ledger ([`research/claim-ledger.yaml`](research/claim-ledger.yaml)), 21 claims:

| Status | Count | Meaning |
|---|---:|---|
| `verified-designed-fixture` | 6 | Observed in frozen authored fixtures |
| `verified-primary` / `-scope-limited` / `-preprint` | 4 | Supported by cited literature |
| `verified-authored-engine-fixture` / `-render-fixture` | 2 | Godot slice conformance |
| `pilot-only` | 2 | Single-model live screening evidence with no population promotion |
| `approved-design-protocol` | 1 | Design approved, unexecuted |
| `proposed-contribution` | 1 | Architectural position |
| **`TODO-RESULT`** | **5** | **`C-RESULT-001`–`005`: no confirmatory efficacy result** |

## Quick start

```bash
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
uv run python scripts/validate_harness.py
./scripts/validate_game_track.sh
./scripts/validate_codex_oauth_llm.sh
uv run python examples/headless_demo.py
uv run python examples/recorded_experiment.py
uv run python scripts/generate_readme_visuals.py
```

Optional local LLM access is available through the official Codex device-code flow. The wrapper
never reads or prints credentials, runs each prompt ephemerally in a disposable read-only
workspace, and returns only a non-authoritative soft proposal with an explicit `request_id`.
It is not included in the public Web build and cannot commit canonical game state. See
[`docs/codex-oauth-llm.en.md`](docs/codex-oauth-llm.en.md).

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
| `game-track/` | Engine-neutral contracts, bilingual experimental GDD, Godot slice, and a fail-closed public asset-exclusion record |
| `_workspace/current/` | Single live game-studio production, design, engineering, QA, UI, and ops workspace |
| `research/` | Immutable sources, Scrapling captures, evidence and claim ledgers |
| `harness/` | Agent roles, workflows, and validation gates |
| `../llm-wiki/` | Project wiki and Graphify knowledge graph |
| `visuals/` | Source SVGs for the README and manuscript, generated by `scripts/generate_readme_visuals.py` |
| `scripts/` | Validators, pilot runner, and the paper-figure, table, and README-visual generators |

## Stage 4 paper and bounded pilot

The authoritative IEEE short-paper drafts are `paper/latex/en/main.pdf` and
`paper/latex/ko/main.pdf`. The offline tables are generated from
`research/academic-pipeline/stage-04-pilot/pilot-results.json`: gate agreement `13/13`
across 12 encoded error codes; 12 invalid repair cases partitioned as 5 guided-repairable,
1 oracle-only, and 6 irreparable; blind commits `0/12`, guided commits `5/5` in its reachable
class, and oracle commits `5/5` plus `1/1`; detectable integrity faults `10/10`; one declared
repair-provenance boundary replay-accepted `1/1`; adapter outcomes 1 commit, 1 symbolic fallback,
and 5 classified failures out of 7; assignment guards `3/3`. These are raw authored-fixture counts,
not live-model, player, or population efficacy estimates.

A separate generated live-screening table reads only the tracked
`research/academic-pipeline/rq2-live-pilot/` packet. In the constructed `signal-repair-v2` blind
cell at `K=1`, guided repair committed `5/5` and blind retry `0/5`; four other current cells showed
no guided advantage, and all `15/15` current noncommit arm outcomes preserved prior state. This is
`screening-pilot-only`; `C-RESULT-003` remains `TODO-RESULT`.

The guided-repair recapture records tag `trace-rpg-guided-repair-inputs-20260821-v1` and
`dirty=false`. All 22 declared inputs and 38 artifact hashes recompute, and the 121 provenance rows
remain partitioned as 85 executed fixture rows plus 36 aggregate rows. The manifest uses the portable
`uv run python` invocation without absolute user or clone paths. This closes F6; no reviewer archive
or DOI deposit is claimed.

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
canonical state. A separately labelled secondary VLM/UI research track may use reviewed,
checksum-locked derivatives in a future internal packet; its pending concept candidates remain
excluded here by ID/hash. Separately curated Higgsfield UI and player assets do ship in the
presentation lane, but never enter experiment inputs or canonical state. Image generation never
occurs during an experiment.
Start with `game-track/design/gdd.en.md`,
`game-track/design/paper-crosswalk.en.md`, and `configs/experimental-game.yaml`.

The human-study surface is protocol and tooling only. No participant has been recruited and no
personal telemetry or human outcome exists. Godot/headless measurements do not promote any
`C-RESULT-*` claim.

### Cycle 3 public-safe playable

The current Godot 4.7.1 playable adds third-person harbor exploration, proposal-gated interaction,
responsive ledger UI, reduced motion, pooled procedural VFX, and gesture-gated locally generated
audio. Its narrative payoff is restoration of the harbor-side signal and acquisition of the tide
route; the offshore lighthouse remains sealed.

| `SL-PLAY-EVAL-001` row | Checks | Result |
|---|---:|---|
| Canonical fixture | `10/10` | PASS |
| Duplicate-event fixture | `10/10` | PASS |
| Timeout fixture | `10/10` | PASS |
| Corrupt-save fixture | `10/10` | PASS |
| Presentation invariants | `9/9` | PASS |
| **Combined** | **`49/49`** | **PASS** |
| Archetype balance probe | `SL-BALANCE-PROBE-001` 5/5 | PASS |

All `4/4` fixtures reached
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`. See
[`SL-PLAY-EVAL-001`](game-track/godot/docs/latest/evaluation-matrix.md) and its
[JSON record](game-track/godot/docs/latest/evaluation-matrix.json).

| Arrival | Refusal |
|---|---|
| ![Public-safe arrival](game-track/godot/docs/latest/arrival.png) | ![Public-safe refusal](game-track/godot/docs/latest/refusal.png) |
| Authorized hint | Ending |
| ![Public-safe authorized hint](game-track/godot/docs/latest/authorized_hint.png) | ![Public-safe ending](game-track/godot/docs/latest/ending.png) |

These four 1280×720 files are latest engineering working captures, not immutable research evidence.
Pending-review concept candidates are excluded from Web/`--public-safe`; the current local build
uses curated Higgsfield UI assets and a validated tracked Higgsfield player GLB with
`Idle`/`Casual_Walk` over the procedural world/VFX/audio surface. Animation remains
presentation-only and cannot change canonical state or saves. The evaluation establishes authored-fixture and presentation-
invariant conformance only. G4, usability, immersion, affect, player efficacy, and confirmatory
model efficacy are **UNASSESSED**. On 2026-08-29/30, the current English Web build completed the
ending, refresh-persistent save/reload, state-isolated fall recovery, tracked-player load, and
ASCII-safe three-page tutorial with zero console/page errors. Production deployment
`dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y` then passed desktop start → in-game → Field Guide smoke with zero
console/page errors. G6 remains `FIX` pending production save/reload, current mobile verification,
human-gesture pointer/audio checks, warmed frame/input, 30-minute soak, and rollback evidence.

```bash
./scripts/build_godot_web.sh
python3 -m http.server 4173 --directory game-track/web/public
```

The current English/curated-player artifact is deployed: 11 manifest files / 50,745,187 bytes; PCK
10,892,412 bytes, SHA-256
`29e3d8b6b898482fb1a7979966cf1acec88caf7578a26398e889fc7af10f8f76`.
Deployment status: **[`dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y` READY on Vercel](https://sealed-lighthouse-trace-rpg.vercel.app)**.
Current full-route gameplay recording: **[Compresso-compressed H.264 MP4](game-track/godot/docs/latest/trace-rpg-gameplay.mp4)**
(`1280×720`, 30 fps, 69.067 s, 5,662,128 bytes, SHA-256
`aa374c5aa9d03e0ab2822b83638e4c6645c7c9fda6c07e858051254c244b7044`). It was captured from the
exact local build source deployed above and remains engineering demonstration, not usability or performance evidence.
All 10 public runtime files returned `200` and matched the local bytes; `vercel.json` was consumed as
deployment configuration and is not a public asset.
A headless-browser smoke on 2026-08-17 against `dpl_7DN4fLqmGa8DfKeiQamVrkXgpEoe` verified clean
loading, Korean glyphs, responsive 1280×720 and 390×844 layouts, and zero console/page errors.
Playwriter was used that day only for the Vercel device-approval login and one pointer-lock
retest that produced no lock, so pointer lock is **not verified**; automation denial is not
itself a defect, and the open item remains a human-gesture check. See
[`game-track/web/README.md`](game-track/web/README.md).

## Execution order

1. Pilot scenario difficulty, validator omission rates, and human-rating variance.
2. Freeze the analysis plan and primary endpoints; determine sample size through power analysis.
3. Screen ten models cheaply and promote three through a preregistered Pareto rule.
4. Run the confirmatory 3-model × 6-system × 3-track experiment and ablations.
5. Admit only independently audited, assignment-complete and outcome-classified runs; require a complete trace when a proposal outcome exists, while retaining classified terminal failures for which no proposal trace can exist.
