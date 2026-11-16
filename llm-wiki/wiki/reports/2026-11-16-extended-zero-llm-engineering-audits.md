# Extended Zero-LLM Engineering Audits (A1–A4, B) — 2026-11-16

- **Status:** Executed (`0` LLM calls, deterministic / headless Godot `4.7.1-stable`), independent denominators separate from frozen paper cohorts (`416/arm`, `12/arm`, `E1`, `Disclosure`, `v5`, `Native`, `SL-PLAY-EVAL-001` 52/52, `SL-BALANCE-PROBE-001` 5/5).
- **Paper integration:** `neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.tex` and `en/main.tex` (`\label{sec:extended-audits}`, `tab:extended-audits`).

## Summary of Observed Results

1. **A1 (`scripts/run_multi_error_repair_audit.py`)**: 352 cases/budget (`K in {0,1,2,3}`, 1,408 runs). Safe commits: `K=0` `0/352`, `K>=1` `124/352` (`35.23%`, unsafe `0/1408`); `repairable_multi` `96/96` converge at `K=1`; `mixed_partial_clear` `132/132` partial-clear holds; `conflict_pair` cross-attempt `96/96` period-2 oscillation vs. same-pass conflict guard `128/128` immediate freeze.
2. **A2 (`scripts/run_latency_scaling_benchmark.py`)**: At `N=2000` facts/rules, validator `V` p95 `0.0055 ms` (valid) / `0.0797 ms` (multi-error), `rho` p95 `0.0328 ms`; at `R=256` rooms, reachability p95 `0.3708 ms` (closure) / `1.5124 ms` (BFS); SHA-256 verify p95 `7.08 ms`, `L=100` JSONL replay p95 `822.07 ms`.
3. **A3 (`scripts/run_traceability_seeded_audit.py`)**: `TR01–TR05` seeded corruption sensitivity `4656/4656` (`100.00%`), invariance false-alarm rate `0/3744` (`0.00%`), `TR05` forward `12/12`, reverse `10/10`; human Krippendorff alpha remains `UNDEFINED`.
4. **A4 (`scripts/run_soak_and_refusal_probe.py`)**: Headless Godot `4.7.1-stable` exercised `9/9` (`100%`) implemented refusal codes (including `OBJECT_NOT_REACHABLE` and `QUEST_STAGE_PRECONDITION`), state isolation `11/11`, trace consistency `1600/1600`, `step_commit` p95 `1.108 ms`, static memory delta `-268 B`, `0` object/orphan leaks.
5. **B (`scripts/run_semantic_escape_filter_audit.py`)**: 88-case EN/KO corpus (incl. 12 frozen sentinels): undeclared escape recall / benign FRR / warm p95 — Baseline (ID-only) `0.0% (0/36)` / `0.0%` / `0.0338 ms`; Alias/Pattern `61.1% (22/36)` / `11.1% (4/36)` / `0.0728 ms`; Local TF-IDF/Cosine `80.6% (29/36)` / `5.6% (2/36)` / `0.2259 ms`.
