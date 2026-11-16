# Latency & Scaling Benchmark Summary (0-LLM-Call)

- **Timestamp (UTC)**: 2026-11-16T13:38:45Z
- **Platform**: macOS-26.6.2-arm64-arm-64bit-Mach-O (arm64)
- **Python**: 3.14.6
- **CPU count**: 12
- **LLM calls**: 0 (purely deterministic symbolic runtime)

## (a) Validator `V(c_t, a_t)` Latency Across Fact/Rule Scales

| Case | Facts/Rules (`N`) | Errors | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---:|---:|---:|---:|---:|---:|
| valid_pass | 10 | 0 | 0.0017 | 0.0019 | 0.0022 | 200 |
| multi_error_fail | 10 | 10 | 0.0063 | 0.0065 | 0.0071 | 200 |
| valid_pass | 100 | 0 | 0.0021 | 0.0022 | 0.0024 | 200 |
| multi_error_fail | 100 | 36 | 0.0180 | 0.0185 | 0.0211 | 200 |
| valid_pass | 500 | 0 | 0.0041 | 0.0043 | 0.0200 | 200 |
| multi_error_fail | 500 | 156 | 0.0729 | 0.0837 | 0.1170 | 200 |
| valid_pass | 1000 | 0 | 0.0040 | 0.0049 | 0.0114 | 200 |
| multi_error_fail | 1000 | 156 | 0.0742 | 0.0831 | 0.1351 | 200 |
| valid_pass | 2000 | 0 | 0.0040 | 0.0055 | 0.0403 | 200 |
| multi_error_fail | 2000 | 156 | 0.0723 | 0.0797 | 0.1290 | 200 |

## (b) Counterexample-Guided Repair `rho` Latency Across Fact/Rule Scales

| Case | Facts/Rules (`N`) | Errors | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---:|---:|---:|---:|---:|---:|
| repairable_converges | 10 | 5 | 0.0073 | 0.0091 | 0.0096 | 200 |
| mixed_repairable_irreparable | 10 | 10 | 0.0078 | 0.0097 | 0.0583 | 200 |
| repairable_converges | 100 | 23 | 0.0108 | 0.0113 | 0.0312 | 200 |
| mixed_repairable_irreparable | 100 | 36 | 0.0121 | 0.0128 | 0.0155 | 200 |
| repairable_converges | 500 | 103 | 0.0257 | 0.0278 | 0.0800 | 200 |
| mixed_repairable_irreparable | 500 | 156 | 0.0307 | 0.0406 | 0.1613 | 200 |
| repairable_converges | 1000 | 103 | 0.0260 | 0.0265 | 0.0299 | 200 |
| mixed_repairable_irreparable | 1000 | 156 | 0.0309 | 0.0323 | 0.0801 | 200 |
| repairable_converges | 2000 | 103 | 0.0250 | 0.0277 | 0.0308 | 200 |
| mixed_repairable_irreparable | 2000 | 156 | 0.0303 | 0.0328 | 0.0886 | 200 |

## (c) Reachability (Closure vs State-Space BFS) Across Room Scales

| Algorithm | Topology | Rooms | Edges | Reachable | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `production_reachable_locations` | locked_chain | 4 | 3 | 3 | 0.0066 | 0.0067 | 0.0070 | 200 |
| `reference_reachable_locations` | locked_chain | 4 | 3 | 3 | 0.0068 | 0.0075 | 0.0089 | 200 |
| `production_reachable_locations` | bypass_branch | 4 | 4 | 3 | 0.0077 | 0.0079 | 0.0082 | 200 |
| `reference_reachable_locations` | bypass_branch | 4 | 4 | 3 | 0.0082 | 0.0085 | 0.0114 | 200 |
| `production_reachable_locations` | locked_chain | 16 | 15 | 15 | 0.0198 | 0.0241 | 0.0678 | 200 |
| `reference_reachable_locations` | locked_chain | 16 | 15 | 15 | 0.0252 | 0.0279 | 0.0712 | 200 |
| `production_reachable_locations` | bypass_branch | 16 | 16 | 15 | 0.0211 | 0.0244 | 0.0630 | 200 |
| `reference_reachable_locations` | bypass_branch | 16 | 16 | 15 | 0.0266 | 0.0294 | 0.0751 | 200 |
| `production_reachable_locations` | locked_chain | 64 | 63 | 63 | 0.0737 | 0.0784 | 0.1523 | 200 |
| `reference_reachable_locations` | locked_chain | 64 | 63 | 63 | 0.1032 | 0.1757 | 0.6130 | 200 |
| `production_reachable_locations` | bypass_branch | 64 | 64 | 63 | 0.0751 | 0.0804 | 0.1093 | 200 |
| `reference_reachable_locations` | bypass_branch | 64 | 64 | 63 | 0.1036 | 0.1130 | 0.4179 | 200 |
| `production_reachable_locations` | locked_chain | 256 | 255 | 255 | 0.2945 | 0.3708 | 0.6654 | 100 |
| `reference_reachable_locations` | locked_chain | 256 | 255 | 255 | 0.5380 | 1.5124 | 2.1596 | 100 |
| `production_reachable_locations` | bypass_branch | 256 | 256 | 255 | 0.2958 | 0.4533 | 1.7457 | 100 |
| `reference_reachable_locations` | bypass_branch | 256 | 256 | 255 | 0.4168 | 0.4764 | 0.5292 | 100 |

## (d) SHA-256 Verification & JSONL Replay Across Scales

| Component | Scale (`N` or `L`) | Payload/File Bytes | p50 (ms) | p95 (ms) | max (ms) | Iterations |
|---|---|---:|---:|---:|---:|---:|
| `sha256_verify_record` | N=10 | 6769 | 0.0540 | 0.0583 | 0.0675 | 200 |
| `replay_trace_record` | N=10 | 6769 | 0.6243 | 0.7326 | 0.8438 | 200 |
| `sha256_verify_record` | N=100 | 47629 | 0.3616 | 0.4190 | 0.8669 | 200 |
| `replay_trace_record` | N=100 | 47629 | 4.9370 | 5.3115 | 12.0628 | 200 |
| `sha256_verify_record` | N=500 | 231695 | 1.6651 | 1.8147 | 2.7538 | 200 |
| `replay_trace_record` | N=500 | 231695 | 24.2245 | 28.1614 | 56.0030 | 200 |
| `sha256_verify_record` | N=1000 | 436661 | 3.3403 | 3.7553 | 9.7346 | 100 |
| `replay_trace_record` | N=1000 | 436661 | 45.8534 | 57.8320 | 63.2439 | 100 |
| `sha256_verify_record` | N=2000 | 860981 | 6.4743 | 7.0760 | 14.9712 | 100 |
| `replay_trace_record` | N=2000 | 860981 | 86.7584 | 98.4529 | 111.7940 | 100 |
| `replay_trace_jsonl` | L=1 steps (N=100) | 50527 | 7.3035 | 7.5498 | 13.5388 | 50 |
| `replay_trace_jsonl` | L=10 steps (N=100) | 508294 | 72.3633 | 82.2943 | 86.8739 | 50 |
| `replay_trace_jsonl` | L=50 steps (N=100) | 2572214 | 365.9220 | 379.7224 | 382.4888 | 20 |
| `replay_trace_jsonl` | L=100 steps (N=100) | 5219614 | 757.0580 | 822.0731 | 853.3910 | 20 |
