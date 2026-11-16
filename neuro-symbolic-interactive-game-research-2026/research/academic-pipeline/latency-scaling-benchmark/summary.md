# Latency & Scaling Benchmark Summary (0-LLM-Call)

- **Host (coarse)**: `Darwin` (`arm64`)
- **LLM calls**: `0` (`model_called = false`; purely deterministic symbolic runtime)
- **Active constraint arity cap (`active_constraint_arity_cap`)**: `100` (per-action `k_req = max(2, min(N // 5, 100))` saturates at `100` for `N >= 500`, so `N in {500, 1000, 2000}` measures ambient store-size scaling at fixed active constraint arity `100`)

## (a) Validator `V(c_t, a_t)` Latency Across Fact/Rule Scales

> Note: Active per-action constraint arity caps at `active_constraint_arity_cap = 100` (`N >= 500` isolates store-size scaling across `N` facts, policies, objects, and NPC knowledge entries).

| Case | Facts/Rules (`N`) | Active Arity (`k_req`) | Errors | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---:|---:|---:|---:|---:|---:|---:|
| valid_pass | 10 | 2 | 0 | 0.0016 | 0.0017 | 0.0045 | 200 |
| multi_error_fail | 10 | 2 | 10 | 0.0056 | 0.0058 | 0.0073 | 200 |
| valid_pass | 100 | 20 | 0 | 0.0020 | 0.0021 | 0.0024 | 200 |
| multi_error_fail | 100 | 20 | 36 | 0.0170 | 0.0175 | 0.0398 | 200 |
| valid_pass | 500 | 100 | 0 | 0.0037 | 0.0043 | 0.0048 | 200 |
| multi_error_fail | 500 | 100 | 156 | 0.0680 | 0.0732 | 0.0990 | 200 |
| valid_pass | 1000 | 100 | 0 | 0.0038 | 0.0039 | 0.0040 | 200 |
| multi_error_fail | 1000 | 100 | 156 | 0.0662 | 0.0715 | 0.1221 | 200 |
| valid_pass | 2000 | 100 | 0 | 0.0039 | 0.0042 | 0.0062 | 200 |
| multi_error_fail | 2000 | 100 | 156 | 0.0671 | 0.0751 | 0.1068 | 200 |

## (b) Counterexample-Guided Repair `rho` Latency Across Fact/Rule Scales

> Note: For `N >= 500`, active per-action constraint arity stays fixed at `100` (`103` repairable errors / `156` mixed errors), measuring store-size scaling.

| Case | Facts/Rules (`N`) | Active Arity (`k_req`) | Errors | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---:|---:|---:|---:|---:|---:|---:|
| repairable_converges | 10 | 2 | 5 | 0.0068 | 0.0082 | 0.0232 | 200 |
| mixed_repairable_irreparable | 10 | 2 | 10 | 0.0070 | 0.0088 | 0.0248 | 200 |
| repairable_converges | 100 | 20 | 23 | 0.0109 | 0.0125 | 0.0395 | 200 |
| mixed_repairable_irreparable | 100 | 20 | 36 | 0.0123 | 0.0140 | 0.0158 | 200 |
| repairable_converges | 500 | 100 | 103 | 0.0282 | 0.0284 | 0.0305 | 200 |
| mixed_repairable_irreparable | 500 | 100 | 156 | 0.0345 | 0.0395 | 0.0903 | 200 |
| repairable_converges | 1000 | 100 | 103 | 0.0295 | 0.0337 | 0.0524 | 200 |
| mixed_repairable_irreparable | 1000 | 100 | 156 | 0.0351 | 0.0377 | 0.0448 | 200 |
| repairable_converges | 2000 | 100 | 103 | 0.0285 | 0.0317 | 0.0611 | 200 |
| mixed_repairable_irreparable | 2000 | 100 | 156 | 0.0352 | 0.0389 | 0.0685 | 200 |

## (c) Reachability (Closure vs State-Space BFS) Across Room Scales

| Algorithm | Topology | Rooms | Edges | Reachable | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `production_reachable_locations` | locked_chain | 4 | 3 | 3 | 0.0057 | 0.0060 | 0.0080 | 200 |
| `reference_reachable_locations` | locked_chain | 4 | 3 | 3 | 0.0060 | 0.0061 | 0.0078 | 200 |
| `production_reachable_locations` | bypass_branch | 4 | 4 | 3 | 0.0067 | 0.0073 | 0.0087 | 200 |
| `reference_reachable_locations` | bypass_branch | 4 | 4 | 3 | 0.0073 | 0.0075 | 0.0377 | 200 |
| `production_reachable_locations` | locked_chain | 16 | 15 | 15 | 0.0183 | 0.0187 | 0.0189 | 200 |
| `reference_reachable_locations` | locked_chain | 16 | 15 | 15 | 0.0220 | 0.0224 | 0.0259 | 200 |
| `production_reachable_locations` | bypass_branch | 16 | 16 | 15 | 0.0189 | 0.0225 | 0.0470 | 200 |
| `reference_reachable_locations` | bypass_branch | 16 | 16 | 15 | 0.0230 | 0.0288 | 0.0539 | 200 |
| `production_reachable_locations` | locked_chain | 64 | 63 | 63 | 0.0694 | 0.0786 | 0.8700 | 200 |
| `reference_reachable_locations` | locked_chain | 64 | 63 | 63 | 0.0882 | 0.0931 | 0.1407 | 200 |
| `production_reachable_locations` | bypass_branch | 64 | 64 | 63 | 0.0685 | 0.0725 | 0.1902 | 200 |
| `reference_reachable_locations` | bypass_branch | 64 | 64 | 63 | 0.0914 | 0.0982 | 0.1347 | 200 |
| `production_reachable_locations` | locked_chain | 256 | 255 | 255 | 0.2659 | 0.3121 | 0.3734 | 100 |
| `reference_reachable_locations` | locked_chain | 256 | 255 | 255 | 0.4005 | 0.4493 | 2.4238 | 100 |
| `production_reachable_locations` | bypass_branch | 256 | 256 | 255 | 0.2737 | 0.3153 | 0.3558 | 100 |
| `reference_reachable_locations` | bypass_branch | 256 | 256 | 255 | 0.3986 | 0.4775 | 1.8595 | 100 |

### `R = 256` Topology Pair Summary (Both Topologies Explicitly Reported)

- **`locked_chain` (`R=256`, `255` edges, `255` reachable)**: closure `p50=0.2659 ms`, `p95=0.3121 ms`, `max=0.3734 ms` vs. state-space BFS `p50=0.4005 ms`, `p95=0.4493 ms`, `max=2.4238 ms`.
- **`bypass_branch` (`R=256`, `256` edges, `255` reachable)**: closure `p50=0.2737 ms`, `p95=0.3153 ms`, `max=0.3558 ms` vs. state-space BFS `p50=0.3986 ms`, `p95=0.4775 ms`, `max=1.8595 ms`.

## (d) SHA-256 Verification & JSONL Replay Across Scales

| Component | Scale (`N` or `L`) | Payload/File Bytes | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---|---:|---:|---:|---:|---:|
| `sha256_verify_record` | N=10 | 6769 | 0.0592 | 0.0625 | 0.0675 | 200 |
| `replay_trace_record` | N=10 | 6769 | 0.6397 | 0.7206 | 0.7915 | 200 |
| `sha256_verify_record` | N=100 | 47629 | 0.3757 | 0.4542 | 0.4828 | 200 |
| `replay_trace_record` | N=100 | 47629 | 5.0170 | 5.4699 | 14.1451 | 200 |
| `sha256_verify_record` | N=500 | 231695 | 1.7193 | 1.9252 | 2.1285 | 200 |
| `replay_trace_record` | N=500 | 231695 | 24.3764 | 28.1398 | 34.2030 | 200 |
| `sha256_verify_record` | N=1000 | 436661 | 3.2973 | 3.6217 | 3.8163 | 100 |
| `replay_trace_record` | N=1000 | 436661 | 45.6001 | 51.9540 | 56.7184 | 100 |
| `sha256_verify_record` | N=2000 | 860981 | 6.4297 | 7.0108 | 7.9953 | 100 |
| `replay_trace_record` | N=2000 | 860981 | 87.1763 | 97.0171 | 117.7224 | 100 |
| `replay_trace_jsonl` | L=1 steps (N=100) | 50527 | 7.7487 | 9.2266 | 17.3907 | 50 |
| `replay_trace_jsonl` | L=10 steps (N=100) | 508294 | 79.9940 | 120.5777 | 148.0779 | 50 |
| `replay_trace_jsonl` | L=50 steps (N=100) | 2572214 | 396.5853 | 412.4689 | 424.9918 | 20 |
| `replay_trace_jsonl` | L=100 steps (N=100) | 5219614 | 817.2787 | 881.0375 | 896.9510 | 20 |
