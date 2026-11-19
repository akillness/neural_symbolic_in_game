# Phase-6 External KR Solvers (P18), Authentic Large-Scale Godot 4.7.1 (P19), 1,200-Case Bilingual Escape (P20), and Overleaf Release (2026-11-19)

Status: `verified-primary` (deterministic/solver/engine benchmarks); Jev check recorded as `NON_SCIENTIFIC_ADVISORY_ONLY`; human ratings (`TR01–TR06`) remain `N=0` (`AWAITING_HUMAN_RATERS`) and `prospective-pilot-20261103` remains `0/180` (`NOT_RUN/BLOCKED`).

## Summary of Phase-6 Technical Upgrades

Targeting the three venues held at `YELLOW` after Phase 5 (`elsevier-kbs-ec`, `ieee-tog`, `neurips-db`) without modifying `src/nesy_game/*.py`, `game-track/godot/`, `pyproject.toml`, `uv.lock`, `paper/latex/references.bib`, or frozen hashes:

1. **P18 — External KR Solvers & Multi-Scale KB Benchmark (`research/green-supplements/phase6_kr_external_solvers_results.json`):**
   - Live industrial solvers (`clingo 5.8.3`, `z3-solver 5.4.1.0`, `rdflib 7.6.0 + owlrl 7.6.2`) via ephemeral `uv run --with ...`.
   - **P18A (120 5-world cases):** `0/120` mismatches across all 4 exact engines (`nesy_game` p50 `2.46 us`, Clingo `397.12 us`, Z3 `2.634 ms`, OWL 2 RL `19.223 ms`).
   - **P18B (1,080 instances, $R \in \{8,16,32,64,128,256\}, d \in \{1,2,3,5,8,10\}$, 3 topologies):** `1,080/1,080` exact equivalence for `nesy_game` (`0.032 ms` p50, `100%` 60/120 Hz), Clingo (`1.268 ms` p50, `100%` 60/120 Hz), and Z3 (`7.885 ms` p50, `68.43%` 60 Hz with empirical real-time cliff `11.67%` at $R{=}128$ and `0.0%` at $R{=}256$); `45/45` stratified P18B + `120` P18A = `165/165` certified for OWL 2 RL (`114.5 ms` at $R{=}8 \to 19,696.2 ms$ at $R{=}64$, `budget_exceeded_gt_20s_per_case` at $R \in \{128,256\}$); vs. `flat_1hop` `50.00%` and `bounded_2hop` `58.33%` (Cochran's $Q = 1948.24, p < 10^{-300}$).
2. **P19 — Authentic Multi-World & Large-Scale Godot 4.7.1 Runtime Benchmark (`research/green-supplements/phase6_godot_large_scale_runtime_results.json`):**
   - Headless `Godot 4.7.1.stable.official.a13da4feb` in ephemeral temp project (`game-track/godot/` untouched).
   - **P19A (120 5-world cases + 5 world episodes):** `120/120` exact parity (`0` Python-Godot / Godot-Oracle / fresh-process divergences, GDScript p50 `5.0 us` / p95 `8.0 us`, `5/5` terminal SHA-256 matches, `0` unsafe/leaks).
   - **P19B (5,000-tick 5-tier soak up to $R=128, A=16, d=8$):** `3,750` commits, `1,250` $\rho$-repairs, `1,875` blocked leaks, `0` unsafe commits, `0` leaks committed, `5/5` fresh-process SHA-256 matches, max tick `0.074 ms` (`0.44%` of 60 Hz budget, `100%` 60/120 Hz pass).
3. **P20 — 1,200-Case 6-Domain Bilingual Adversarial Escape Benchmark (`research/green-supplements/phase6_large_bilingual_escape_results.json`):**
   - `1,200` cases (`6` domains $\times$ `5` strata `S1`–`S5` $\times$ `600` EN + `600` KO, `corpus_sha256` `1af8be38...`, mean domain vocab Jaccard `0.0630`).
   - 5 deterministic LODO baselines: `stage1_id_only` `60.00%` (`0%` FRR), `keyword_rule_naive` `62.67%` (`98.33%` S4 FRR / `75.21%` FRR), `stage1_plus_negation_rule_hybrid` `73.67%` (`0%` FRR), `bm25_lexical_lodo` `96.75%` (`2.08%` S4 FRR / `3.12%` FRR), `tfidf_char_word_lodo` `97.17%` (`1.25%` S4 FRR / `4.79%` FRR); Cochran's $Q = 871.39$ ($p = 2.63 \times 10^{-187}$).
4. **NeurIPS Supplement v6 (`_workspace/current/qa/neurips-db-supplemental-benchmark.zip`):**
   - `368,528` B (`64` files, `63/63 CHECKSUMS.sha256`, `DATASHEET_v6.md`, Croissant v6 `30/30`, `0` PII leaks), bundling 4 anonymized executable Godot 4.7.1 scripts (`godot/project.godot`, `sealed_lighthouse_machine.gd`, `godot_phase6_multiworld_bench.gd`, `phase6_benchmark_payload.json`), verified live in `/tmp` via both `python3 reproduce_benchmark.py` and `python3 reproduce_benchmark.py --with-godot`.

## Phase-6 Overleaf Bundles & Readiness Status

Release directory: `neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-11-19-phase6-venue-bundles/` (`MANIFEST.json`). Every Overleaf `.zip` compiled from scratch in clean `/tmp` with `errs=0`, `type3=0`, `overfull=0`, `anon_leaks=0`:

| Venue | Phase 5 | Phase 6 Status | Overleaf Bundle | Verified `/tmp` Pages (EN / Anon / KO) |
|---|---|---|---|---|
| `elsevier-kbs-ec` | `YELLOW` | `GREEN` (Systems & Formal-KR scope) | `elsevier-kbs-ec-overleaf.zip` (`1,422,697` B) | `12 / 12 / 11` |
| `ieee-tog` | `YELLOW` | `GREEN` (Game-Engine Systems scope) | `ieee-tog-overleaf.zip` (`1,415,624` B) | `9 / 9 / 8` |
| `neurips-db` | `YELLOW` | `YELLOW_TECHNICAL_READY_HUMAN_GOLD_OPEN` | `neurips-db-overleaf.zip` (`1,419,709` B) + Supplement v6 | `14 (7p body) / 14 (7p body) / 12` |

Previously released Phase-5 `GREEN` venues (`aiide`, `ieee-cog`, `fdg`, `aamas`) remain untouched under `_workspace/current/qa/releases/2026-11-19-green-venue-bundles/`.

## Jev Advisory Check

- Profile `jeo` (`backend: local`, `model: qev-0.8b-text-Q8_0`, `tier: local_calibrated`): `quality_grade: excellent` (confidence `0.9581`), `failure_category: none` (confidence `0.8509`). Recorded strictly as `NON_SCIENTIFIC_ADVISORY_ONLY`.
