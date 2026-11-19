# TRACE-RPG Benchmark Datasheet (v4 — Confound-Free 3-Family & Core Multihop Release)

Structured following Gebru et al. (2021), *Datasheets for Datasets*. Extends `DATASHEET.md` (v1/v2) and `DATASHEET_v3.md` while keeping v1 (`6/6`), v2 (`12/12`), and v3 (`17/17`) artifacts intact.

## 1. Motivation
- **Purpose:** Provide an auditable neuro-symbolic verification benchmark measuring (a) multi-hop epistemic and disclosure gating inside `nesy_game.multihop`, (b) confound-free 3-family multi-agent negotiation vs. Safe-RL action masking and NeMo-style Colang rails, (c) fair candidate-inclusive `(a, E)` counterexample repair vs. state-blind/state-aware LLM self-repair, (d) unguided Godot 4.7.1 closed-loop determinism, and (e) cross-family EN/KO semantic escape consensus.
- **Creators & Funding:** TRACE-RPG Benchmark Contributors (anonymized for double-anonymous peer review; zero host PII/IP).

## 2. Composition (22 Croissant 1.0 v4 FileObjects)
- **v2 Base (`12/12`):** `multihop_ontology_results.json` (48 cases), `multiquest_live_results.json` (24 eps), `audit_b_{calibrated,live,jev}_results.json` (88 cases), `tr_human_eval_packet.json` (36 blinded `TR01-TR06` items, `N=0`), `phase2_multihop_5world_results.json` (120 cases), `phase2_multiagent_epistemic_results.json` (30 eps), `phase2_godot_live_closed_loop_results.json` (16 eps), `phase2_live_shield_and_multihop_results.json` (60 tasks), `phase2_multisecret_escape_results.json` (180 items), `DATASHEET.md`.
- **v3 Scaling & Phase-3 Provenance (`5` files):** `phase3_procedural_multihop_scaling_results.json` (480 Datalog cases, $R{\in}\{8,16,32,64\} \times d{\in}\{1..5\}$), `phase3_multiworld_godot_closed_loop_results.json` (50 eps), `phase3_live_multiagent_3family_results.json`, `phase3_crossfamily_shield_90_results.json`, `phase3_crossfamily_multisecret_escape_results.json`, plus `DATASHEET_v3.md` (`phase3` archive also ships v3 Croissant).
- **v4 Confound-Free Phase-4 Additions (`P11`–`P14` + `DATASHEET_v4.md`):**
  1. `phase4_unguided_multiagent_3family_results.json` (**P11**): `30` unguided 3-turn sequential multi-agent episodes (`79/90` parsed turns, `0` prompt confound markers) evaluated counterfactually across 7 arms over `rho`-stepped states (`0/30` full goals; milestones = `commits >= 2`).
  2. `phase4_stateful_repair_90_results.json` (**P12**): `84/90` parsed 7-arm tasks + `27` matched policy/stage faults comparing `state_blind_llm` ($K=1$: `26/27`, $K=2$: `26/27`), `state_aware_llm` ($K=1$: `25/27`, $K=2$: `26/27`), and `rho` ($K=2$: `27/27`, 0 tok).
  3. `phase4_unguided_godot_closed_loop_results.json` (**P13**): `42` unguided Godot 4.7.1 episodes (`42/42` fresh 0-LLM replays, `0` leaks; 30 5-world + 12 production `SealedLighthouseMachine`).
  4. `phase4_3family_multisecret_escape_results.json` (**P14**): `180` EN/KO utterances $\times$ `4` neural verifiers (`720` matrix evals; 3-family 540-eval $\kappa=0.9309$, 4-model 720-eval $\kappa=0.9367$).

## 3. Collection Process
- All worlds (up to 8 rooms, 3 actors), procedural Datalog graphs, and EN/KO escape utterances are synthetic, author-constructed artifacts; zero human user logs, scraped web corpora, or private host identifiers appear.
- Live evaluations invoked `agy` (`cli_version 1.5.12`) for GPT-OSS 120B and Gemini 4 Hydrogen / 3.8 Flash plus `claude-code-cli` (`sonnet` medium fallback) for Claude Sonnet 5.5, with CLI-side provider revisions (`UNATTESTED_BY_CLI`) and unseeded decoding logged.

## 4. Preprocessing, Cleaning, and Labeling
- All parse/timeout failures (e.g., `P11` `11/30` GPT-OSS, `P12` `6/30`, `P13A` `16/55` steps, `P13B` `2/21` steps, `P14` `2/144`) are preserved unmodified in full denominators without cherry-picking.
- Notice on **P14** provenance: GPT-OSS rows ran cleanly in Phase 4, Claude reused Phase-3 `p3_esc` responses, and Gemini Hydrogen/Flash reused Phase-2 `p2_auditb` cache (which included an affirmative-violation instruction); `36/180` explicit violations use deterministic Stage-1 labels.
- `tr_human_eval_packet.json` remains `AWAITING_HUMAN_RATERS` (`N=0`, zero synthetic human labels); `0/180` prospective API pilot remains `NOT_RUN/BLOCKED`.

## 5. Uses
- Intended for reproducible neuro-symbolic safety gating, multi-hop Datalog benchmarking, deterministic counterexample repair, and bilingual leakage audit research. Not intended as a substitute for human playtesting on full open-world 3D games.

## 6. Distribution
- Distributed as an anonymized self-contained archive (`neurips-db-supplemental-benchmark.zip`) with Croissant 1.0 metadata (`v2` 12/12, `v3` 17/17, `v4` 22/22 SHA-256 digests), `CHECKSUMS.sha256`, dual **MIT** (verification code) + **CC BY 4.0** (datasets/traces) licensing, and offline `python3 reproduce_benchmark.py` verification.

## 7. Maintenance
- Maintained by the TRACE-RPG Contributors under strict immutability of `src/nesy_game/*.py` (`20/20` `source_hashes.json`), `game-track/godot/`, and raw historical logs. Future errata or human `TR01-TR06` cohorts append versioned JSON/datasheet releases without overwriting prior digests.
