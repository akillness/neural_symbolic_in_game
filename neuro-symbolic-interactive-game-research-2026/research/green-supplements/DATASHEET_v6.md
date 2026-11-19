# TRACE-RPG Benchmark Datasheet (v6 — Complete Phase 1–6 External KR Solvers, Large-Scale Godot 4.7.1, & 1,200-Case Bilingual Escape Release)

Structured following Gebru et al. (2021), *Datasheets for Datasets*. Consolidates all 30 Croissant 1.0 v6 FileObjects across deterministic benchmarks (`1,664` authorization checks, `48` & `120` multi-hop cases, `480` Datalog scaling cases), open/closed-weight CLI studies (`P6`–`P14`), attested direct HTTPS Anthropic Messages API experiments (`P15`–`P17`), and Phase-6 industrial external KR solver benchmarks (`P18`), authentic multi-world & large-scale Godot 4.7.1 engine benchmarks (`P19`), and the 1,200-case 6-domain bilingual EN/KO adversarial escape benchmark (`P20`), alongside anonymized executable Godot 4.7.1 scripts inside `godot/`.

## 1. Motivation
- **Purpose:** Provide an auditable neuro-symbolic runtime verification benchmark separating candidate proposal from canonical engine commit, featuring `nesy_game.multihop`, industrial KR reasoner equivalence and frame-budget cliff profiling (`Clingo 5.8.3` ASP, `Z3 5.4.1.0` SMT, `RDFLib 7.6.0 + OWLRL 7.6.2` OWL 2 RL), Safe-RL action masking, NeMo-style Colang output rails, authentic multi-world and 5,000-tick Godot 4.7.1 engine verification, independent 7-arm closed-loop multi-agent episodes (`P15`), attested commercial API prospective factorial + Godot 4.7.1 execution (`P16`), and large-scale 6-domain bilingual EN/KO adversarial semantic-escape evaluation (`P20`).
- **Creators:** TRACE-RPG Benchmark Contributors (double-anonymous submission).

## 2. Composition (30 Croissant 1.0 v6 FileObjects + Executable `godot/` Engine Suite)
- **v1–v5 Foundation (`26` files):** `multihop_ontology_results.json`, `multiquest_live_results.json`, `audit_b_{calibrated,live,jev}_results.json`, `tr_human_eval_packet.json` (`N=0` human template), `DATASHEET.md`, `phase2_*` (`5` files), `phase3_*` (`5` files + `DATASHEET_v3.md`), `phase4_*` (`4` files + `DATASHEET_v4.md`), `phase5_*` (`3` files + `DATASHEET_v5.md`).
- **Phase-6 Technical Scaling & External-Solver Suites (`P18`–`P20` + `DATASHEET_v6.md`):**
  1. `phase6_kr_external_solvers_results.json` (**P18**): Live external KR solver equivalence and large-scale KB scaling across `nesy_game 0.1.0`, `Clingo 5.8.3` (ASP), `Z3 5.4.1.0` (SMT), and `RDFLib 7.6.0 + OWLRL 7.6.2` (OWL 2 RL):
     - **P18A (5-World Equivalence, `120` cases):** `120/120` exact equivalence (`0` mismatches across all 4 engines; p50 `2.46 us` `nesy_game`, `397.12 us` Clingo, `2.634 ms` Z3, `19.223 ms` OWL 2 RL).
     - **P18B (Large-Scale KB Scaling, `1,080` instances across $R \in \{8,16,32,64,128,256\}$, $d \in \{1,2,3,5,8,10\}$, 3 topologies):** `1,080/1,080` (`100.0%`) exact equivalence for `nesy_game` (p50 `0.032 ms`, `100%` 60/120 Hz), `Clingo` (p50 `1.268 ms`, `100%` 60/120 Hz), and `Z3` (p50 `7.885 ms`, `68.43%` 60 Hz; empirical cliff `11.67%` at $R{=}128$ and `0.0%` at $R{=}256$); `45/45` stratified certification (`165/165` combined with P18A, `0` mismatches) for `OWL 2 RL` with empirical cubic materialization cliff (`114.5 ms` at $R{=}8 \to 19,696.2 ms$ at $R{=}64$, `budget_exceeded_gt_20s_per_case` at $R \in \{128, 256\}$); vs. `flat_1hop` (`50.00%`) and `bounded_2hop` (`58.33%`), Cochran's $Q = 1948.24$ ($\text{df}=4, p < 10^{-300}$).
  2. `phase6_godot_large_scale_runtime_results.json` (**P19**): Authentic headless `Godot 4.7.1.stable.official.a13da4feb` evaluation:
     - **P19A (`120` 5-world parity cases + `5` multi-world episodes):** `120/120` exact cross-runtime parity (`0` Python-Godot, Godot-Oracle, or fresh-process divergences; GDScript p50 `5.0 us` / p95 `8.0 us`; `5/5` terminal SHA-256 matches, `0` unsafe commits, `0` leaks).
     - **P19B (`5,000`-tick 5-tier large-scale soak across $R \in \{8..128\}, A \in \{3..16\}, d \in \{2..8\}$):** `3,750` commits, `1,250` $\rho$-repairs, `1,875` blocked leaks, `0` unsafe commits, `0` leaks committed, `5/5` fresh-process SHA-256 matches, `100%` pass rate at 60 Hz and 120 Hz (max tick `0.074 ms` at $R{=}128, A{=}16, d{=}8$).
  3. `phase6_large_bilingual_escape_results.json` (**P20**): `1,200`-case 6-domain $\times$ 5-stratum (`S1`–`S5`) $\times$ 2-language (`600` EN + `600` KO) adversarial escape corpus (`corpus_sha256` prefix `1af8be38`, mean cross-domain vocabulary Jaccard `0.0630`) with 5 Leave-One-Domain-Out (LODO) baselines (`stage1_id_only` `60.00%` / `0%` FRR, `keyword_rule_naive` `62.67%` / `98.33%` S4 FRR / `75.21%` FRR, `stage1_plus_negation_rule_hybrid` `73.67%` / `0%` FRR, `bm25_lexical_lodo` `96.75%` / `2.08%` S4 FRR / `3.12%` FRR, `tfidf_char_word_lodo` `97.17%` / `1.25%` S4 FRR / `4.79%` FRR; Cochran's $Q = 871.39, \text{df}=4, p = 2.63 \times 10^{-187}$).
- **Executable Anonymized Godot 4.7.1 Suite (`godot/`):** Bundles `godot/project.godot`, `godot/sealed_lighthouse_machine.gd`, `godot/godot_phase6_multiworld_bench.gd`, and `godot/phase6_sample_payload.json` so reviewers with Godot 4.7+ installed can execute live engine verification via `python3 reproduce_benchmark.py --with-godot`.

## 3. Collection Process
- Procedural KR scaling graphs ($R{\le}256, d{\le}10$), 5-world quest state machines, 5-tier Godot soak states ($R{\le}128, A{\le}16, d{\le}8$), and 1,200 bilingual EN/KO adversarial utterances are deterministically generated from fixed seeds with zero web-scraped text, zero user PII, and zero secrets.
- Phase-5 direct HTTPS calls (`P15`–`P17`) remain single-vendor Anthropic Messages API records and are explicitly distinguished from vendor-agnostic deterministic, multi-solver, multi-runtime, and cross-family evaluations (`P6`–`P14`, `P18`–`P20`).

## 4. Preprocessing, Cleaning, and Labeling
- Zero data omission or cherry-picking: all HTTP/parse failures and OWL 2 RL per-scale budget exceedances (`budget_exceeded_gt_20s_per_case` at $R \in \{128, 256\}$) remain explicitly reported.
- `tr_human_eval_packet.json` (`TR01--TR06`, `N=0` human raters) remains `AWAITING_HUMAN_RATERS` with zero fabricated human gold labels; frozen `prospective-pilot-20261103/results-v1` remains `0/180` `NOT_RUN/BLOCKED`.

## 5. Uses
- Benchmark for proposal-to-commit neuro-symbolic safety gating, multi-hop Datalog epistemic closure, external KR solver frame-budget profiling, deterministic repair $\rho(a,E)$, authentic game-engine parity verification, and bilingual semantic-escape detection. Does not measure human player enjoyment or free-form 3D rendering.

## 6. Distribution
- Packaged cleanly in `neurips-db-supplemental-benchmark.zip` with `CHECKSUMS.sha256`, Croissant 1.0 v2/v3/v4/v5/v6 metadata (`30/30` SHA-256 digests in v6), dual **MIT** (verification & Godot scripts) + **CC BY 4.0** (data/traces/datasheets) license, standalone offline `python3 reproduce_benchmark.py`, and optional live Godot execution via `python3 reproduce_benchmark.py --with-godot`.

## 7. Maintenance
- Maintained by the TRACE-RPG Contributors with frozen `src/nesy_game/*.py` (`20/20` SHA-256), untouched `game-track/godot/`, and immutable raw archives. Additive versioned releases never alter prior Croissant v1–v5 or `source_hashes.json` digests.
