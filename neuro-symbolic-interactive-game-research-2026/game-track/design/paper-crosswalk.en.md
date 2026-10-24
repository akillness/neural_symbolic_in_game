# The Sealed Lighthouse — Paper and Stage 6 Crosswalk

```yaml
pair_id: SL-XWALK-001
language: en
version: 0.2.0
run_id: 20260813-sealed-lighthouse-cycle-2
paper_target: SCI-or-SCIE-game-journal
status: DESIGN-CROSSWALK-NO-EFFICACY-RESULT
```

## 1. Scope

This document maps game mechanics to planned paper evidence. It does not promote any `TODO-RESULT`
claim. The submission manuscript remains authoritative in `../../paper/latex/en/main.tex` and
`../../paper/latex/ko/main.tex`; the Markdown files are superseded protocol blueprints. [OBSERVED]

## Verified current production (2026-10-23)

Observed `READY`: `dpl_75HRZ3UGnVtADdvZnFUJaG9espYY`, [production alias](https://sealed-lighthouse-trace-rpg.vercel.app)
and [generated deployment](https://sealed-lighthouse-trace-fflmsgady-akillness-projects.vercel.app).
[HTTP receipt](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-http-assets.json):
18/18 staged game/dashboard/PDF assets HTTP 200 and byte-count/SHA-256 identical; root 307 → `/dashboard/`.
[Native keyboard/mouse production QA](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-browser/actual-game-acceptance.json)
passes stage-zero denial, lens, mount/stage 2, fresh disclosure, authorized redisplay, map 1440,
map 390 and continuous diagnostics (8/8); console/page/request/HTTP errors are all 0. One headed desktop
Chromium session at DPR 2 exercised 390 px reflow/keyboard inspection, not physical-mobile gameplay.

The [presentation release receipt](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-final-verification.json)
records 171 tests + 23 subtests passing: 62 frozen-case + 43 publication-source + 44 presentation
and 22 visual-validator tests ([focused receipt 049](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/049-frozen-affected-regressions.json),
[paired-paper receipt 050](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/050-frozen-paired-papers.json)). [Source-identity
negative cases and the approved EN/KO clause oracle](../../tests/test_ontology_publication_sources.py)
verify frozen publication declarations separately from runtime authorization, independent human gold
and efficacy. Four SVGs and tables have more breathing room; tables retain 4 pt padding,
`arraystretch=1.20` and standard IEEE 10 pt type, with properly typeset LaTeX math.
Current [English](../../paper/latex/en/main.pdf) / [Korean](../../paper/latex/ko/main.pdf) PDFs are each
10 pages, 675846 / 631282 bytes, with 0 Type3 fonts each. Final selected-source CI status is recorded
in the presentation receipt; Git delivery requires separate repository commit/remote-history evidence, not deployment.
The [sealed case](../../research/development-cases/ontology-map-20261023-01/result.json) remains `n=1`,
6 native CLI calls, 0 repeats, runtime-selected `gpt-6.1-sol`, provider identity/revision/cost `null`.
Jev remains negative, unvalidated `proposal_only` advice with no approval authority. [Source map](../web/dashboard/ontology-map.json),
Godot writer authority, canonical R5 capture, fixture60 and NPC88 are unchanged. **G4/full G6 remain
`FIX`; no efficacy, superiority or human benefit follows.** R3/D-087 history is superseded only for
current-production status; original private/raw evidence and historical metrics remain preserved.

## 2. RQ1–RQ5 mapping

| Table SL-XWALK-T1 | Paper claim | Game manipulation | Independent unit | Planned endpoint | Evidence required before promotion | Current state |
|---|---|---|---|---|---|---|
| RQ1 / H1 | `C-RESULT-001` | unreachable-object holdout, premature Mira disclosure, causal-stage skip; A5 vs A0 and registered baselines | held-out world/quest template; seeds nested | valid episode rate, hard dialogue violation rate, forbidden disclosure | live promoted-model runs + independent encoded/semantic oracle + mixed-effects analysis | `TODO-RESULT` [OBSERVED] |
| RQ2 / H2 | `C-RESULT-003` | identical rejected candidate receives generic blind retry (A3) or typed counterexample (A4), `K=3` | held-out scenario/template | repair@K, tokens, cost, latency, failure class | matched call/token budget and complete treatment-policy accounting | `TODO-RESULT` [OBSERVED] |
| RQ3 / H3 | `C-RESULT-004` | relationship/fact event queried at `5/10/20` turns with and without graph + temporal provenance | NPC/relation motif template | contradiction rate, matched-validity diversity | disjoint NPC/motif holdout + independent semantic labels + provenance trace | `TODO-RESULT` [OBSERVED] |
| RQ4 / H4 | `C-RESULT-002` | A5 `trace_rpg_full` crossed with affect `off` vs `uncertainty_calibrated_soft_adaptation`; high uncertainty disables adaptation | affect template | validity non-inferiority then target tension RMSE | `2 pp` one-sided `α=.025` validity gate, then two-sided `α=.05` RMSE test | `TODO-RESULT` [OBSERVED] |
| RQ5 / H5 | `C-RESULT-005` | same frozen scenarios and arms across promoted models; ten-model screen precedes confirmation | scenario/template across model stratum | system-by-model interaction and direction | exact model revisions, access/scale strata, sensitivity analysis | `TODO-RESULT` [OBSERVED]; secondary estimand |

## 3. Metric definitions

| Table SL-XWALK-T2 metric | Formula | Authority boundary |
|---|---|---|
| Valid episode rate | `valid_completed_episodes / attempted_episodes` | independent oracle, not controller self-score |
| Hard violation per commit | `hard_violations_on_committed_actions / committed_actions` | encoded + semantic audit |
| Forbidden disclosure rate | `forbidden_facts_disclosed / disclosure_opportunities` | hidden disclosure oracle |
| Repair@K | `invalid_candidates_repaired_within_K / invalid_candidates` | matched A3/A4 assignment, `K=3` |
| Memory contradiction rate | `semantic_memory_contradictions / scored_memory_queries` | independent `5/10/20`-turn labels |
| Target tension RMSE | `sqrt(mean((predicted_tension - target_tension)^2))` | tested only after hard-validity non-inferiority |
| Replay equality | `I(engine_terminal_hash = research_terminal_hash)` | engine correctness only, not RQ efficacy |
| Rejection immutability | `I(pre_state_hash = post_state_hash)` for reject/timeout/failure | engine/controller boundary correctness |
| Authored typed-link proposal precision/recall | `P=TP/(TP+FP)`, `R=TP/(TP+FN)` | `SL-KG-ONTOLOGY-SIM-001` closed-world method links only; never RQ3 efficacy |
| Ontology fit at K | `Sem@K = conforming_top_K / (K × queries)` | encoded domain/range construction check, not semantic completeness |

## 4. Stage 6 C1 closure map

Stage 6 C1 states that full-paper efficacy and external validity are absent. [OBSERVED] The game
track can close only specific prerequisites; it cannot close the finding by design alone.

| Table SL-XWALK-T3 C1 requirement | Design/implementation surface | Completion evidence | State |
|---|---|---|---|
| Live model/controller comparison | A0–A5 plus configured grounding/affect variants in `SL-ORACLE-T3` | assignment-complete experiment records | [PLANNED] |
| Independent semantic oracle | encoded + semantic layers in `SL-ORACLE-001` | frozen hidden labels, agreement/adjudication, manifest hash | [PLANNED]; no labels collected |
| Held-out worlds/quests | joint template/motif split | split manifest + duplicate audit | [PLANNED] |
| Genuine blind retry | A3 generic retry, no typed feedback | prompt/call/token audit vs A4 | [PLANNED] |
| Direct, constraint, reject, blind, repair, full arms | A0–A5 | exact six-arm config exists; preregistration and execution records required | [OBSERVED config] + [PLANNED execution] |
| Failures retained | treatment-policy estimand | timeout/parse/exhaustion rows and denominators | [TARGET] |
| Correct independent unit | template cluster, seed nested | raw N, cluster count, variance components | [TARGET] |
| Tokens, latency, cost | trace contract | per-assignment accounting + summaries | [TARGET] |

The current `configs/experiment-matrix.yaml` names all six C1 arms explicitly and sets maximum
matched calls to `1+K=4`. [OBSERVED config] This closes the naming/design gap, not the execution,
oracle, holdout, or analysis requirements.

## 5. Stage 6 M6 closure map

| Table SL-XWALK-T4 M6 requirement | Fixture | Required artifact | Interpretive limit | State |
|---|---|---|---|---|
| Multi-step engine scenario | `SL-M6-LOAD`–`SL-M6-FAULTS` | Godot JSONL trace + command/build metadata | engine-local policy mirror, not cross-runtime/external validity | [OBSERVED authored fixture] |
| Quest progression | Q0→Q2 plus authorized hint | acquire/install commits and stage snapshots | engine-local correctness; later lighthouse entry is out of slice | [OBSERVED authored fixture] |
| NPC knowledge/disclosure | premature reject then authorized hint | `evt-002-validation-secret`, fallback, `evt-005-commit-hint` | no model-quality claim without live arms/oracle | [OBSERVED authored fixture] |
| Save/load or replay | valid save/load, corrupt-save rejection, operation replay | `evt-006-save`, `evt-007-load`, `evt-008-replay-check` | persistence/reproducibility only | [OBSERVED authored fixture] |
| Frame/request budget | frame and request latency only | raw telemetry + p95 with sample counts | frame target failed; local input/provider latency absent | [OBSERVED incomplete, FIX] |
| Non-headless engine render | canonical arrival, rejected secret, authorized hint | `SL-CAPTURE-001` paper bundle with manifest IDs `sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, `sl-rc-003-authorized-hint` | authored fixture render/state correspondence only | [OBSERVED immutable promotion] |

These observed rows are engine-local policy-mirror evidence. Live Python authorization transport
remains required for a cross-runtime M6 integration claim. No row changes a `C-RESULT-*` state.
The selected current machine-bound render packet is
`godot-4.7.1-20261023-publication-r5`, selected by
[`current.json`](../../_workspace/current/engineering/tech-verification/current.json). Its
[manifest](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20261023-publication-r5/evidence-manifest.json)
records four real Godot runs and three non-headless macOS scripted fixture-trace replay panels at `2026-10-23 11:00:42` UTC, with no live
Python authorization transport or neural inference. It records source/toolchain hashes and tool
versions; it is authored render/state correspondence, not actual player interaction. R4 (`godot-4.7.1-20261023-publication-r4`) and the prior
`godot-4.7.1-20261023-signal-explainer-r1`, `godot-4.7.1-20261015t083849z-sealed-lighthouse-current-v3` and earlier immutable packets remain
retained as dated history, not current-runtime certification.

The historical [R3 production receipt](../../_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-final-verification.json)
records `PASS_FOR_APPROVED_BOUNDED_RELEASE` for `dpl_BvpyBPiSouiyoyzN3wG9WQN16YNM`, with
7 canonical Godot cases, 8 public-safe checks and 9 deployed-asset byte matches. Its fixed 60-case
general-rule and ontology-gate arms agree (16 allowed, 44 denied, 0 expectation mismatches each);
this is bounded declaration-derived engineering conformance, not ontology superiority or efficacy.
**G4 and full G6 remain `FIX`.** This documentation update asserts no new deployment or push.

The [paper producer manifest](../../paper/latex/generated/disclosure_producer_manifest.json) separately
records publication-only materialization from current `results-signal-explainer-20261023-r5` deterministic Python/Godot artifacts, with no new model observation.
Its public interview derivative is not byte-equivalent to the private historical source; original
frozen packets and runtime receipts remain unchanged. Neither materialization nor that derivative
replaces the selected render. The [actual browser-input gameplay receipt](../../_workspace/current/qa/releases/2026-10-23-signal-explainer/receipt.json)
records 3 commits and 1 hold through Mira's authorized hint, with tide-mark deduction not attempted.
Scripted replay, publication provenance, and actual gameplay are distinct evidence classes. A later
disclosure-only observation cannot change render selection without an owner update to `current.json`.

Historical trace/receipt repair checkpoint: Main reported 53 tests and 48 subtests in the targeted
eight-file run. The current production section records later evidence and separate CI/Git attestation.

### 5.1. Ontology structure-to-evidence development case

Updated 2026-10-23. The read-only bilingual **Ontology structure → evidence** view lives inside
**Engineering detail** in the [dashboard](../web/dashboard/index.html); `Tab`/`Enter` opens the
details control and the table wraps at mobile width. Its eight authored roles are **World, Actor,
Knowledge, Fact, Policy, Quest, Action, Trace**. [Source map JSON](../web/dashboard/ontology-map.json)
retains canonical identifiers, frozen source references and rule IDs; only public aliases reach
the UI. Declared structure and the latest observed public event are distinct columns, not access
to full canonical state. Missing/unreported/skipped evidence never becomes pass. Eight roles,
seven Python predicates, six Godot display families and seven disclosure rules are not one-to-one.

The sealed [result](../../research/development-cases/ontology-map-20261023-01/result.json) is
`ACCEPTED`: one actual Codex development case (`n=1`, zero independent repeats), native runtime-selected
`gpt-6.1-sol`, six CLI invocations (five editing turns and one read-only/no-edit resume).
Provider-returned model identity, immutable revision and cost remain unknown (`null`); runtime
selection is not provider-weight attestation. Historical `gpt-5.6-sol` and NPC88 are not relabelled.
The receipt records 62 checks passed, Godot Web build exit 0, real-input stage-zero denial, fresh
disclosure and authorized redisplay; read-only inspection preserves state and the frozen comparison.
Both 1440×900 and 390×900 views show eight roles with keyboard Enter verified; continuous diagnostics
from before navigation record zero console/page/request/HTTP errors and zero warnings.

- [Public evidence manifest](../../research/development-cases/ontology-map-20261023-01/public-evidence-manifest.json) retains original/public hashes separately; failed attempts and same-case repairs remain preserved, not new samples.
- Actual browser PNGs: [denial](../../research/development-cases/ontology-map-20261023-01/browser/010-stage_zero_denial.png), [fresh disclosure](../../research/development-cases/ontology-map-20261023-01/browser/036-fresh_disclosure.png), [authorized redisplay](../../research/development-cases/ontology-map-20261023-01/browser/038-authorized_redisplay.png), [1440 px map](../../research/development-cases/ontology-map-20261023-01/browser/map-1440-action.png), [390 px map](../../research/development-cases/ontology-map-20261023-01/browser/map-390-action.png).
- The [mechanism figure](../../paper/latex/figures/fig_signal_mechanism.pdf), `fig:signal-mechanism`, is an authored diagram, not a browser capture; see the current ten-page [English](../../paper/latex/en/main.pdf) and [Korean](../../paper/latex/ko/main.pdf) manuscripts, `sec:development-case`.

This additional development-engineering case does not enlarge the frozen 60-case disclosure cohort
or NPC88 and establishes no human benefit, fun, efficacy, productivity or ontology superiority.
Godot source/writer authority and canonical R5 engine capture remain unchanged. **G4/full G6 remain
`FIX`.** Current production and separate CI/Git attestation are described above.
The retired hosted-model cohort (including historical labels, fixture60, and NPC88) is provenance-only and excluded from active paper tables, counts, and runtime-model claims; no label or outcome is transferred to the runtime-reported `gpt-6.1-sol` development case. The source-derived traceability instrument is a proposal, not a measured score: [`codebook.en.md`](../../research/traceability-scoring-20261023/codebook.en.md) and [`sources.json`](../../research/traceability-scoring-20261023/sources.json). Whole-game matched-information and repeated-cross-model comparison remain `PROPOSED_NOT_EXECUTED`: [`plan.en.md`](../../research/development-comparison-20261023/plan.en.md).

## 6. Game artifact → paper use

| Table SL-XWALK-T5 artifact | Stable ID | Permitted paper use now | Forbidden use now |
|---|---|---|---|
| GDD pair | `SL-GDD-001` | describe the experimental game and authority boundary | claim fun, validity, portability, or performance |
| Scenario/oracle pair | `SL-ORACLE-001` | describe planned holdout, arms, and independent labels | report completed N, agreement, or effects |
| Concept and worldview | `SL-CONCEPT-001`, `SL-WORLD-001` | define public fixture semantics | use production lore QA as gold oracle |
| Numeric/core-loop plans | `SL-BALANCE-001`, `SL-LOOP-001` | report design targets with `[TARGET]` | report target as observed measurement |
| Novelty survey | `SL-SURVEY-001`, `SL-NOVELTY-001` | bounded official-description comparison with limitations | universal novelty or player impression claim |
| Frozen concept pack | `SL-C01`–`SL-C04` | disclose AI-assisted concept authoring and visual condition | infer game quality or RQ result from image quality |
| Non-headless render bundle | `SL-CAPTURE-001` (paper label; not a manifest field), `C-GAME-DESIGN-003` | show three deterministic structured-state Godot render surfaces with exact manifest capture IDs and source binding | claim live Python integration, model/visual efficacy, usability, immersion, human outcomes, G4, or G6 |
| Typed methods-graph simulation | `SL-KG-ONTOLOGY-SIM-001` | report the authored six-query link-holdout method, exact formulas, and construction checks under a simulation-only label | infer runtime retrieval, temporal-memory benefit, semantic completeness, player usefulness, or any `C-RESULT-*` promotion |
| Contribution readout (`CONTRIBUTION #N`, `RULE LEARNED`, `CASE CHAIN`, two-part end-card receipt) | `SL-GDD-T4`, `SL-HYP-001`, `SL-PLAY-EVAL-001` checks `contribution_delta_is_pure_and_names_facts`, `hold_teaches_rule_for_its_gate`, `case_chain_mirrors_committed_snapshot` | describe how the playable ledger mirrors the manuscript's predicate families (Table II) and links every commit to its snapshot delta as engineering conformance (ENG1, C2/C3 surfaces) | claim fun, perceived agency, competence, reduced frustration, G4, or any player outcome; the `[TARGET]` questions in `SL-GDD-T4` have no data |

## 7. Paper-ready wording controls

Permitted now:

> [TARGET] The Sealed Lighthouse protocol operationalizes quest reachability, gated NPC disclosure,
> bounded repair, and temporal memory; its authored Godot fixture has executed only the bounded
> quest/disclosure/save-load/operation-replay subset. Model, player, and visual efficacy remain
> untested.

Permitted only after a live Python-authorized, executed, independently reviewed M6 trace:

> [OBSERVED] The frozen development episode completed the preregistered engine path and reproduced
> the terminal state hash; this establishes cross-runtime integration-path evidence, not model efficacy.

Current engine-local evidence may instead be described as an authored Godot policy-mirror run with
stable-envelope schema projection. It does not establish a live Python authorization round-trip.

After immutable promotion and fresh validation, `C-GAME-DESIGN-003` may state only:

> [OBSERVED] A separate non-headless Godot pass rendered the canonical authored arrival, rejected
> disclosure, and authorized-hint states as `sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, and
> `sl-rc-003-authorized-hint`, with source and file digests recorded in the selected evidence set.
> This is render/state correspondence, not an efficacy or cross-runtime result.

Forbidden until C1 is executed and independently reviewed:

- “TRACE-RPG reduces hard violations,” “structured repair is more efficient,” “memory improves
  consistency,” “affect improves tension,” or “the effect generalizes across models.”
- Any promotion of `C-RESULT-001`–`C-RESULT-005`.
- Any suggestion that generated images, production QA, deterministic fixtures, or one M6 run are an
  independent semantic or player-quality result.

## 8. Release gates

Before paper citation, validate bilingual IDs/numbers, link targets, source identity, scenario split,
oracle independence, protocol completeness, leakage guards, schema conformance, deterministic
replay, and claim-ledger state. A missing artifact remains `FIX`; it is not evidence to delete or a
reason to weaken the claim boundary.
