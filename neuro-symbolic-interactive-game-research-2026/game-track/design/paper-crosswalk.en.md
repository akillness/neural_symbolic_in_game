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
The selected render packet is
`godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`; immutable v1--v4 are retained but
superseded through visual QA, validation-toolchain provenance binding, and CI-portability repair.
The v5 evidence chain records capture/decoder/schema/validator/lock hashes and tool versions without
requiring a verifier host to impersonate the capture host.

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
