# The Sealed Lighthouse — Scenario, Holdout, and Independent Oracle Plan

```yaml
pair_id: SL-ORACLE-001
language: en
version: 0.1.0
run_id: 20260813-sealed-lighthouse-cycle-1
confirmatory_status: PLANNED-NOT-EXECUTED
development_fixture_status: OBSERVED-AUTHORED-GODOT-POLICY-MIRROR
primary_track: structured-state-text
secondary_track: secondary-vlm-ui
```

## 1. Separation of purposes

`SL-DEV-001` (*The Sealed Lighthouse*) is the public development and Stage 6 M6 engine fixture. It
may be used to debug schemas, save/load, replay, telemetry, and presentation. Because its facts and
failures are public to developers, it is excluded from confirmatory efficacy estimates. [TARGET]

The confirmatory RQ1–RQ5 universe uses separately authored and frozen world/quest templates. Their
semantic gold labels remain hidden from generation systems, controller authors, production lore QA,
and visual-generation prompts until preregistered unblinding. [TARGET]

## 2. Scenario layers

| Table SL-ORACLE-T1 layer | Purpose | Templates and repetitions | Inference status |
|---|---|---|---|
| Development | Godot M6, schema and negative-fixture debugging | `SL-DEV-001`; deterministic seeds as needed | engineering only |
| Stage 1 screening | Pareto screen across all ten registered models | `30` scenarios/track × `3` repetitions; current config | no paper-level causal conclusion |
| Stage 2 confirmation | preregistered RQ1–RQ5 estimates across promoted three | `120` scenarios/track × `5` seeds (`11,23,47,83,131`); current config | confirmatory only after freeze and execution |
| Secondary visual | modality/UI sensitivity using frozen image packs | separately powered/preregistered block | exploratory until separate registration |

The `30/3`, `120/5`, model counts, and seeds are observed configuration values in
`../../configs/experiment-matrix.yaml`; they are not completed sample sizes. [OBSERVED config]

## 3. Scenario families

| Table SL-ORACLE-T2 family | Registered anchor | Required hazard | Primary endpoint |
|---|---|---|---|
| World reachability | `IF-LOCK-001` | required object unreachable or behind its own lock | valid episode rate |
| World causality | `IF-CAUSAL-001` | effect before precondition | valid episode rate |
| NPC disclosure | `NPC-SECRET-001` | future betrayal requested before authorization | hard dialogue violation rate |
| Temporal memory | `NPC-MEMORY-020` | relationship-changing event recalled at `5/10/20` turns | contradiction rate at matched validity |
| Character deception | `NPC-DECEPTION-001` | in-character lie must not contradict private canonical state | semantic hard violation |
| Affect rise | `AFF-RISE-001` | rising target with quest safety | tension RMSE after validity gate |
| Affect uncertainty | `AFF-UNCERTAIN-001` | high estimator uncertainty disables adaptation | fallback correctness |

Each confirmatory item is instantiated from a template, not by paraphrasing a development utterance.
[TARGET]

## 4. Holdout and leakage protocol

1. Freeze template family IDs before model assignment. Split at the joint
   `(world_template_id, quest_motif_id, npc_identity_id, relation_motif_id)` level, never at the
   utterance level. [TARGET]
2. `SL-DEV-001`, Brinewake, Captain Mira, the signal lens, and their close lexical paraphrases
   are development-only and excluded from Stage 2. [TARGET]
3. Fingerprint normalized graphs and quest automata; near-duplicate structures that cross a split
   are moved wholly to one side before unblinding. [TARGET]
4. Model prompts may contain encoded runtime-visible facts and policies, but never hidden semantic
   labels, adjudication notes, or oracle-only omitted fields. [TARGET]
5. Generation model family cannot be the sole judge. No generated concept image supplies ground
   truth. [TARGET]
6. Hash prompts, fixtures, oracle schema/version, model revisions, image-pack manifests, controller
   build, and game build. [TARGET]
7. Treat scenario/template as the independent unit; seeds are nested generations. Report cluster
   counts and variance components rather than counting rows as independent scenarios. [TARGET]

## 5. C1 controller arms and budget matching

Stage 6 C1 requires the following minimum diagnostic block. [OBSERVED requirement] The six exact
controller IDs and their budget contract are now materialized in
`../../configs/experiment-matrix.yaml`. [OBSERVED config] They remain unexecuted and must be frozen
in preregistration before any confirmatory run. [PLANNED]

| Table SL-ORACLE-T3 arm | Retrieval | Structural constraint | Deterministic validator | Retry/repair feedback | Calls |
|---|---:|---:|---:|---|---|
| A0 `direct_commit` | no | no | post hoc scoring only | none | `1` |
| A1 `structural_constraint_only` | no | schema/grammar only | post hoc scoring only | none | `1` |
| A2 `validator_rejection_only` | matched context | no | reject, no resubmission | none | `1` |
| A3 `matched_budget_blind_retry` | matched context | no | reject | generic retry, max `K=3` follow-ups | up to `4` total |
| A4 `structured_repair` | matched context | no | reject | typed counterexample, max `K=3` follow-ups | up to `4` total |
| A5 `trace_rpg_full` | KG + temporal provenance | encoded policy | reject/commit | typed counterexample, max `K=3` follow-ups | up to `4` total |

RQ4 is not a seventh controller arm: it crosses A5 with the configured affect variants `off` and
`uncertainty_calibrated_soft_adaptation`. [OBSERVED config]

RQ2 compares A3 with A4 under the same model, scenario, seed, prompt-visible facts, maximum `4` calls,
maximum output tokens, temperature `0.7`, top-p `0.95`, timeout `60 s`, and cold-cache primary
policy. [TARGET] Actual calls, tokens, latency, timeout, parse failures, and exhausted retries remain
in the treatment-policy estimand. A2 is not mislabeled as blind retry.

## 6. Independent oracle contract

The controller validator and production G1 lore audit cannot be the sole outcome oracle. [OBSERVED
requirement] The frozen oracle has two non-collapsed layers:

### 6.1 Encoded oracle

- Independently authored transition graph, object reachability, quest preconditions, NPC knowledge,
  and disclosure allow-list. [TARGET]
- Produces `encoded_valid`, typed violation codes, and expected state deltas. [TARGET]
- Uses a separate implementation or declarative gold artifact; it must not call the treatment
  validator as its label function. [TARGET]

### 6.2 Semantic oracle

- Blinded annotation schema for whether narrative text asserts an impossible action, forbidden
  disclosure, unknown fact, omitted required object/effect, contradiction, or unsupported state
  mutation. [TARGET]
- Includes sentinels intentionally accepted by the encoded boundary:
  `disclosure_hazard`, `omitted_object_hazard`, and `unknown_field_hazard`. [TARGET]
- Two independent future labels plus adjudication are planned. Agreement, raw disagreement,
  missingness, and adjudication changes must be reported. No labels are collected in Cycle 1.
  [PLANNED]

### 6.3 Gold isolation

The repository may contain the oracle schema, label vocabulary, frozen IDs, and cryptographic
manifest. Item-level gold values remain in access-controlled storage until unblinding. The
generation/controller logs receive only item IDs. Production QA may test protocol wiring with
synthetic labels but cannot certify semantic efficacy. [TARGET]

## 7. Labels and adjudication record

| Table SL-ORACLE-T4 field | Type | Meaning |
|---|---|---|
| `scenario_id`, `template_id` | string | frozen assignment and independent cluster |
| `oracle_version`, `gold_manifest_sha256` | string | identity of hidden judgment set |
| `encoded_valid` | boolean | independent encoded-world validity |
| `semantic_valid` | boolean/undetermined | independent narrative validity |
| `hazard_codes` | set | disclosure, omitted object/effect, unknown field, contradiction, impossible transition |
| `evidence_spans` | offsets + hashes | minimum text supporting a semantic label |
| `annotator_id` | pseudonymous code | no direct personal identifier in repository |
| `confidence` | ordinal | annotation uncertainty, not model confidence |
| `adjudication_status` | enum | none, pending, resolved, excluded-with-reason |

## 8. Primary and secondary-track randomization

Primary structured assignments are blocked by model, scenario/template, seed, controller arm,
grounding variant, and (for RQ4) affect variant. [TARGET] Secondary visual assignments additionally
block by `image_pack_id` and presentation order.
All images are generated before randomization, reviewed, frozen, and hashed. [TARGET] The visual
track never changes action policy, gold labels, quest graph, or commit authority.

Misleading visual-affect cues are allowed only as preregistered secondary probes; high VLM or affect
uncertainty must disable adaptation. [TARGET] Visual results cannot be pooled with primary results
without a prespecified hierarchical model.

## 9. M6 engine protocol

The engine-local authored policy mirror has executed frozen load, harbor observation, reachable
acquisition, premature-secret rejection with unchanged hash, valid quest-stage commit, authorized
hint, save/load equality, JSONL operation-replay terminal equality, duplicate/timeout fallback, and
corrupt-save rejection. [OBSERVED authored fixture] Three canonical/duplicate/timeout runs are
retained with exact command form, Godot version, platform, source/fixture hashes, event logs, saves,
pre/post/terminal hashes, request latency, and five-sample frame timing. [OBSERVED incomplete]

Local input-feedback latency, a soak run, and a live Python authorization round-trip remain absent.
[TARGET] Headless success supports only authored engine-path correctness and cannot be counted as a
live-model, independent-oracle, player, or VLM result.

## 10. Analysis plan alignment

- RQ1: mixed-effects logistic model for hard validity, template random intercept, model fixed
  stratum; H1 world/dialogue contrasts Holm-adjusted. [TARGET]
- RQ2: A4 vs A3, repair@K plus tokens/cost/latency, single two-sided `α=.05`. [TARGET]
- RQ3: memory vs no-memory across `5/10/20` turns, contradiction outcome conditioned on matched
  hard-validity band. [TARGET]
- RQ4: A5 with affect `off` vs `uncertainty_calibrated_soft_adaptation`; one-sided validity
  non-inferiority margin `2 percentage points` at `α=.025`, then tension-RMSE superiority at
  two-sided `α=.05`. [TARGET]
- RQ5: system-by-model interaction is secondary, not confirmatory. [TARGET]

No efficacy result, effect size, confidence interval, agreement value, or completed N is available
from this plan. [OBSERVED]
