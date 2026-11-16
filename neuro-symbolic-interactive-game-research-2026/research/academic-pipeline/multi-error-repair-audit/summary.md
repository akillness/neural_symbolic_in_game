# Multi-Error & Conflict-Pair Repair Convergence Audit

- **Study ID**: `multi-error-repair-audit-20261116`
- **Host (coarse)**: `Darwin` (`arm64`)
- **Model calls**: `False` (`llm_calls = 0`; deterministic offline audit)
- **Base graph/state combinations**: `32` (from `run_gemini_review_evaluation.py`)
- **End-to-end variants**: `11` across 3 families -> `352` assigned cases per budget `K in {0, 1, 2, 3}` (`96 + 160 + 96 = 352`; `1408` total runs)
- **Separate same-pass conflict-guard unit battery**: `128` assigned (`4` variants x `32` states; `128/128` preserve `ready` and reach fixed point at step 1)
- **Graph closure vs BFS agreement**: `32/32`
- **Native trace replay equality**: `1408/1408`
- **Unsafe commits across all runs**: `0/1408`

## 1. Overall Convergence & Recovery Across Budgets (K = 0 -> 1 -> 2 -> 3)

| Budget K | Assigned | Committed (Safe) | Recovery Rate | Held | Partial-Clear Holds (of Held) | Obs. Traj Fixed-Pt | Terminal Fixed-Pt | Obs. Period-2 Osc. | Terminal Period-2 Osc. | Incr. Recovered (Prev->K) | Error Reduction |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 352 | 0 (0) | 0.00% | 352 | 0/352 (0.00%) | 0/352 (0.00%) | 0/352 (0.00%) | 0/352 (0.00%) | 0/352 (0.00%) | — | 0/916 (0.00%) |
| 1 | 352 | 124 (124) | 35.23% | 228 | 164/228 (71.93%) | 124/352 (35.23%) | 256/352 (72.73%) | 0/352 (0.00%) | 96/352 (27.27%) | 124/352 (35.23%) | 672/916 (73.36%) |
| 2 | 352 | 124 (124) | 35.23% | 228 | 164/228 (71.93%) | 256/352 (72.73%) | 256/352 (72.73%) | 64/352 (18.18%) | 96/352 (27.27%) | 0/228 (0.00%) | 672/916 (73.36%) |
| 3 | 352 | 124 (124) | 35.23% | 228 | 164/228 (71.93%) | 256/352 (72.73%) | 256/352 (72.73%) | 96/352 (27.27%) | 96/352 (27.27%) | 0/228 (0.00%) | 672/916 (73.36%) |

## 2. Breakdown by Fixture Family Across K in {0, 1, 2, 3}

### Explicit Assigned Denominators by Family & Battery

- **`repairable_multi`** (`96` assigned = `3` variants x `32` states): `0/96` safe commits at `K=0`, `96/96` safe commits at `K>=1` (`0/96` held at `K>=1`).
- **`mixed_partial_clear`** (`160` assigned = `5` variants x `32` states): `28/160` safe commits at `K>=1`, `132/160` held, and `132/132` (`100.00%`) of holds are partial-clear holds.
- **`conflict_pair`** (`96` assigned = `3` variants x `32` states): `0/96` safe commits across all `K`, `96/96` held; trajectory period-2 oscillation `0/96` at `K=1`, `64/96` at `K=2`, `96/96` at `K=3`; terminal lookahead period-2 oscillation `96/96` at `K>=1`.
- **Separate `simultaneous_conflict_guard` unit battery** (`128` assigned = `4` variants x `32` states, distinct from the `352` end-to-end denominator): `128/128` preserve conflicting entity `ready` and reach fixed point at step 1.

| Family | K | Assigned | Safe Commits | Recovery | Held | Partial-Clear Holds (of Holds) | Obs. Traj Fixed-Pt | Terminal Fixed-Pt | Traj. Period-2 | Term. Lookahead Period-2 | Incr. Recovered | Error Reduction |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `repairable_multi` | 0 | 96 | 0/96 | 0.00% | 96/96 | 0/96 (0.00%) | 0/96 (0.00%) | 0/96 (0.00%) | 0/96 | 0/96 | — | 0/320 (0.00%) |
| `repairable_multi` | 1 | 96 | 96/96 | 100.00% | 0/96 | 0/0 (N/A) | 96/96 (100.00%) | 96/96 (100.00%) | 0/96 | 0/96 | 96/96 | 320/320 (100.00%) |
| `repairable_multi` | 2 | 96 | 96/96 | 100.00% | 0/96 | 0/0 (N/A) | 96/96 (100.00%) | 96/96 (100.00%) | 0/96 | 0/96 | 0/0 | 320/320 (100.00%) |
| `repairable_multi` | 3 | 96 | 96/96 | 100.00% | 0/96 | 0/0 (N/A) | 96/96 (100.00%) | 96/96 (100.00%) | 0/96 | 0/96 | 0/0 | 320/320 (100.00%) |
| `mixed_partial_clear` | 0 | 160 | 0/160 | 0.00% | 160/160 | 0/160 (0.00%) | 0/160 (0.00%) | 0/160 (0.00%) | 0/160 | 0/160 | — | 0/468 (0.00%) |
| `mixed_partial_clear` | 1 | 160 | 28/160 | 17.50% | 132/160 | 132/132 (100.00%) | 28/160 (17.50%) | 160/160 (100.00%) | 0/160 | 0/160 | 28/160 | 320/468 (68.38%) |
| `mixed_partial_clear` | 2 | 160 | 28/160 | 17.50% | 132/160 | 132/132 (100.00%) | 160/160 (100.00%) | 160/160 (100.00%) | 0/160 | 0/160 | 0/132 | 320/468 (68.38%) |
| `mixed_partial_clear` | 3 | 160 | 28/160 | 17.50% | 132/160 | 132/132 (100.00%) | 160/160 (100.00%) | 160/160 (100.00%) | 0/160 | 0/160 | 0/132 | 320/468 (68.38%) |
| `conflict_pair` | 0 | 96 | 0/96 | 0.00% | 96/96 | 0/96 (0.00%) | 0/96 (0.00%) | 0/96 (0.00%) | 0/96 | 0/96 | — | 0/128 (0.00%) |
| `conflict_pair` | 1 | 96 | 0/96 | 0.00% | 96/96 | 32/96 (33.33%) | 0/96 (0.00%) | 0/96 (0.00%) | 0/96 | 96/96 | 0/96 | 32/128 (25.00%) |
| `conflict_pair` | 2 | 96 | 0/96 | 0.00% | 96/96 | 32/96 (33.33%) | 0/96 (0.00%) | 0/96 (0.00%) | 64/96 | 96/96 | 0/96 | 32/128 (25.00%) |
| `conflict_pair` | 3 | 96 | 0/96 | 0.00% | 96/96 | 32/96 (33.33%) | 0/96 (0.00%) | 0/96 (0.00%) | 96/96 | 96/96 | 0/96 | 32/128 (25.00%) |

## 3. Per-Variant Results at K=1 and K=3 (Highlighting Incremental K=1->2->3 Stability)

| Variant | Family | Assigned | K=1 Commit | K=3 Commit | K=1->3 Incr. | K=1 Held (Partial-Clear) | K=1 Obs. Traj FP | K=2 Obs. Traj FP | K=3 Obs. Traj FP | K=3 Obs. Period-2 | Errors Cleared (K=3) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `multi_pre_eff_violation` | `repairable_multi` | 32 | 32 | 32 | 0 | 0 (0) | 32/32 | 32/32 | 32/32 | 0/32 | 64/64 |
| `multi_pre_eff_omission_violation` | `repairable_multi` | 32 | 32 | 32 | 0 | 0 (0) | 32/32 | 32/32 | 32/32 | 0/32 | 96/96 |
| `multi_all_5_repairable` | `repairable_multi` | 32 | 32 | 32 | 0 | 0 (0) | 32/32 | 32/32 | 32/32 | 0/32 | 160/160 |
| `mixed_pre_eff_forbidden` | `mixed_partial_clear` | 32 | 16 | 16 | 0 | 16 (16) | 16/32 | 32/32 | 32/32 | 0/32 | 64/80 |
| `mixed_pre_eff_knowledge` | `mixed_partial_clear` | 32 | 0 | 0 | 0 | 32 (32) | 0/32 | 32/32 | 32/32 | 0/32 | 64/96 |
| `mixed_pre_eff_forbidden_knowledge` | `mixed_partial_clear` | 32 | 0 | 0 | 0 | 32 (32) | 0/32 | 32/32 | 32/32 | 0/32 | 64/112 |
| `mixed_pre_eff_relic` | `mixed_partial_clear` | 32 | 12 | 12 | 0 | 20 (20) | 12/32 | 32/32 | 32/32 | 0/32 | 64/84 |
| `mixed_eff_future_stage` | `mixed_partial_clear` | 32 | 0 | 0 | 0 | 32 (32) | 0/32 | 32/32 | 32/32 | 0/32 | 64/96 |
| `conflict_cross_attempt_omitted` | `conflict_pair` | 32 | 0 | 0 | 0 | 32 (0) | 0/32 | 0/32 | 0/32 | 32/32 | 0/32 |
| `conflict_cross_attempt_present` | `conflict_pair` | 32 | 0 | 0 | 0 | 32 (0) | 0/32 | 0/32 | 0/32 | 32/32 | 0/32 |
| `conflict_cross_attempt_plus_effect` | `conflict_pair` | 32 | 0 | 0 | 0 | 32 (32) | 0/32 | 0/32 | 0/32 | 32/32 | 32/64 |

## 4. Direct Single-Pass Simultaneous Conflict-Guard Audit (`counterexample_guided_repair`)

When `POLICY_PRECONDITION_OMISSION(ready)` and `UNSATISFIED_PRECONDITION(ready)` are supplied in the **same** `ValidationResult` (testing `repair.py`'s `precondition_conflicts` guard across all 32 states):

- **Total assigned**: `128` (`4` variants x `32` states)
- **Conflicting entity `ready` untouched across steps 1..3**: `128/128` (100.00%)
- **Fixed point reached by step 1 (`c_1 == c_2 == c_3`)**: `128/128` (100.00%)

| Guard Variant | Assigned | `ready` Preserved | Co-occurring Effect Cleared (Step 1) | Fixed Point by Step 1 (`c_1==c_2==c_3`) | `c_0==c_1` |
|---|---:|---:|---:|---:|---:|
| `guard_conflict_only_present` | 32 | 32/32 | 32/32 | 32/32 | 32/32 |
| `guard_conflict_only_omitted` | 32 | 32/32 | 32/32 | 32/32 | 32/32 |
| `guard_conflict_plus_effect_present` | 32 | 32/32 | 32/32 | 32/32 | 0/32 |
| `guard_conflict_plus_effect_omitted` | 32 | 32/32 | 32/32 | 32/32 | 0/32 |

## 5. Key Empirical Takeaways (Derived Directly from Observed Counts)

1. **Parallel multi-error convergence in 1 step (`K=1` suffices when repairable)**: `repairable_multi` recovers `96/96` (100.00%) at `K=1` (`attempts=1`), with `0/0` incremental recovery at `K=2` and `0/0` at `K=3`.
2. **Partial-clear holds & fixed-point convergence on mixed errors**: On `mixed_partial_clear` (`160` cases), `28/160` (17.50%) recover at `K=1` (`16/32` stage-1 `mixed_pre_eff_forbidden` + `12/32` reachable-relic `mixed_pre_eff_relic`), and `132/160` hold with `0` unsafe commits. Among those holds, `132/132` (100.00%) are **partial-clear holds** (clearing `320/468` initial errors at `K=1`), reaching a terminal fixed point at `K=1` (`160/160`) that is observed on the trajectory at `K=2` (`160/160`).
3. **Cross-attempt conflict-pair oscillation vs. same-pass conflict guard**: In `execute_with_repair`, `validate_candidate` cannot emit both `POLICY_PRECONDITION_OMISSION(e)` and `UNSATISFIED_PRECONDITION(e)` in a single pass. When `ready` is required by policy but absent from `state.facts`, `conflict_pair` enters a **period-2 cycle** (`96/96` terminal period-2 at `K=1`; observed on trajectory: `0/96` at `K=1`, `64/96` at `K=2`, and `96/96` at `K=3` after step 1 clears the transient effect violation in `32/32` `conflict_cross_attempt_plus_effect` cases). By contrast, when both codes co-occur in the same `ValidationResult`, `repair.py`'s conflict guard freezes `ready` immediately (`128/128`) while clearing co-occurring effect violations at step 1 (`128/128` fixed point).
