# TRACE-RPG Benchmark Datasheet (v5 — Complete Phase 1–5 & Attested Anthropic API Release)

Structured following Gebru et al. (2021), *Datasheets for Datasets*. Consolidates all 26 Croissant 1.0 v5 FileObjects across deterministic benchmarks (`1,664` authorization checks, `48` & `120` multi-hop cases, `480` Datalog scaling cases), open/closed-weight CLI studies (`P6`–`P14`), and attested direct HTTPS Anthropic Messages API experiments (`P15`–`P17`).

## 1. Motivation
- **Purpose:** Provide an auditable neuro-symbolic runtime verification benchmark separating candidate proposal from canonical engine commit, featuring `nesy_game.multihop`, Safe-RL action masking, NeMo-style Colang output rails, independent 7-arm closed-loop multi-agent episodes (`P15`), attested commercial API prospective factorial + Godot 4.7.1 execution (`P16`), and unified-prompt bilingual EN/KO semantic escape (`P17`).
- **Creators:** TRACE-RPG Benchmark Contributors (double-anonymous submission).

## 2. Composition (26 Croissant 1.0 v5 FileObjects)
- **v1–v4 Foundation (`22` files):** `multihop_ontology_results.json`, `multiquest_live_results.json`, `audit_b_{calibrated,live,jev}_results.json`, `tr_human_eval_packet.json` (`N=0` human template), `DATASHEET.md`, `phase2_*` (`5` files), `phase3_*` (`5` files + `DATASHEET_v3.md`), `phase4_{unguided_multiagent_3family,stateful_repair_90,unguided_godot_closed_loop,3family_multisecret_escape}_results.json`, `DATASHEET_v4.md`.
- **Phase-5 Attested Direct Anthropic API Suites (`P15`–`P17` + `DATASHEET_v5.md`):**
  1. `phase5_attested_closed_loop_mas_results.json` (**P15**): `105` independent closed-loop 5-turn episodes across `3` attested models (`claude-haiku-5-5, claude-sonnet-5-5, claude-opus-5-5`) $\times$ `5` quest worlds $\times$ `7` independent trajectory arms (`schema_only`, `safe_rl_action_mask`, `nemo_colang_rail`, `flat_1hop_shield`, `multihop_shield_k0`, `trace_rpg_multihop_rho_k2`, `trace_rpg_hybrid_rho_llm_k1`), with zero-LLM trace replay verification and exact Cochran/McNemar statistics.
  2. `phase5_attested_claude_api_prospective_results.json` (**P16**, non-pooled with frozen `0/180` `prospective-pilot-20261103`): `60` factorial runtime episodes (`general_rule` vs. `ontology_multihop` $\times$ 5 worlds $\times$ 2 epistemic regimes) + `21` live API $\rightarrow$ Godot 4.7.1 closed-loop episodes (`21/21` fresh 0-LLM replays, `0` leaks).
  3. `phase5_attested_unified_escape_results.json` (**P17**): `540` fresh unified-prompt live API evaluations (`180` EN/KO cases $\times$ `3` attested tiers, zero deterministic short-circuits; Fleiss' $\kappa=0.8813$, $\alpha=0.8815$) with full per-language (`EN`/`KO`) and per-domain (`keeper_secret`, `council_forgery`, `eclipse_sabotage`) breakdowns.

## 3. Collection Process
- Synthetic quest state machines (`<=8` rooms, `<=3` actors), procedural Datalog graphs ($R{\le}64, d{\le}5$), and bilingual EN/KO utterances contain zero web-scraped text, zero user PII, and zero secrets.
- Phase-5 direct HTTPS calls to `https://api.anthropic.com/v1/messages` record attested `served_model` snapshots (temperature omitted where deprecated on Claude 5.5), SHA-256-hashed `message_id`/`request_id`, input/output tokens, and HTTP latency, while strictly redacting keys/headers/workspaces.

## 4. Preprocessing, Cleaning, and Labeling
- Zero data omission or cherry-picking: all HTTP/parse failures remain inside reported denominators.
- `tr_human_eval_packet.json` (`TR01--TR06`, `N=0` human raters) remains `AWAITING_HUMAN_RATERS` and is strictly excluded from machine leaderboard scores; frozen `prospective-pilot-20261103/results-v1` remains `0/180` `NOT_RUN/BLOCKED`.

## 5. Uses
- Benchmark for proposal-to-commit neuro-symbolic safety gating, multi-hop Datalog epistemic closure, deterministic repair $\rho(a,E)$, and bilingual semantic-escape verification. Does not measure human player enjoyment or free-form 3D rendering.

## 6. Distribution
- Packaged cleanly in `neurips-db-supplemental-benchmark.zip` with `CHECKSUMS.sha256`, Croissant 1.0 v2/v3/v4/v5 metadata, dual **MIT** (verification code) + **CC BY 4.0** (data/traces) license, and standalone `python3 reproduce_benchmark.py` verifier.

## 7. Maintenance
- Maintained by the TRACE-RPG Contributors with frozen `src/nesy_game/*.py` (`20/20` SHA-256) and immutable raw archives. Additive versioned releases never alter prior Croissant v1–v4 or `source_hashes.json` digests.
