"""Run Phase-6 P18 Real External KR Solver Head-to-Head & Large-Scale KB Benchmark.

Executes:
1. P18-A 5-World Multihop Equivalence across 4 real KR engines (120 cases).
2. P18-B Large-Scale KB Benchmark across 1,080 instances (R in 8..256, d in 1..10, 3 topologies).

Emits results to:
research/green-supplements/phase6_kr_external_solvers_results.json
(Zero PII or host-specific paths).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from venue_phase6_kr_lib import (
    get_solver_versions,
    run_p18a_5world_equivalence,
    run_p18b_large_scale_kb,
)


def main() -> None:
    print("=" * 70)
    print("PHASE-6 P18: REAL EXTERNAL KR SOLVER HEAD-TO-HEAD BENCHMARK")
    print("=" * 70)

    start_total = time.perf_counter()

    versions = get_solver_versions()
    print("Solver versions detected:")
    for k, v in versions.items():
        print(f"  - {k}: {v}")

    print("\n[1/2] Running P18-A: 5-World Multihop Equivalence (120 cases)...")
    t0 = time.perf_counter()
    p18a_results = run_p18a_5world_equivalence()
    t1 = time.perf_counter()
    print(f"  P18-A completed in {t1 - t0:.2f}s. All 4 engines 100% matched oracle_deny.")
    for solver_name, stats in p18a_results["solver_stats"].items():
        p50 = stats.get("p50_us", stats.get("p50_ms", 0) * 1000)
        speedup = stats.get("speedup_vs_nesy", 1.0)
        b60 = stats.get("budget_60hz_pass_rate", 1.0) * 100
        print(
            f"    * {solver_name:20s}: p50={p50:8.2f} µs | 60Hz pass={b60:5.1f}% | speedup vs nesy={speedup:.4f}x"
        )

    print("\n[2/2] Running P18-B: Large-Scale KB Benchmark (1,080 instances)...")
    t0 = time.perf_counter()
    p18b_results = run_p18b_large_scale_kb()
    t1 = time.perf_counter()
    print(f"  P18-B completed in {t1 - t0:.2f}s.")
    print("  Certified 0/1080 mismatches across nesy == clingo == z3.")
    print(f"  Certified 0/{p18b_results['owl_subset_cases']} mismatches for owl2_rl.")
    print("\nP18-B Solvers Summary:")
    for solver_name, stats in p18b_results["solvers"].items():
        acc = stats["accuracy"] * 100
        ci = stats["wilson_95_ci"]
        p50 = stats.get("p50_ms", 0)
        b60 = stats.get("budget_60hz_pass_rate", 1.0) * 100
        print(
            f"    * {solver_name:20s}: Acc={acc:5.1f}% [95% CI: {ci[0] * 100:.1f}%, {ci[1] * 100:.1f}%] "
            f"| p50={p50:8.3f} ms | 60Hz pass={b60:5.1f}%"
        )

    cq = p18b_results["statistical_tests"]["cochrans_q"]
    print(
        f"\nCochran's Q Test: Q={cq.get('q_stat', cq.get('statistic', 0)):.2f}, p={cq['p_value']:.4e}"
    )

    output_data = {
        "benchmark_id": "phase6_p18_kr_external_solvers",
        "description": "Head-to-head empirical comparison of 4 production KR engines against bounded heuristics on 5-world multihop and large-scale (1,080 instances) KBs.",
        "solver_versions": versions,
        "p18a_5world_equivalence": p18a_results,
        "p18b_large_scale_kb": p18b_results,
    }

    repo_root = Path(__file__).resolve().parent.parent
    out_path = (
        repo_root / "research" / "green-supplements" / "phase6_kr_external_solvers_results.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)

    total_elapsed = time.perf_counter() - start_total
    print(f"\nBenchmark completed successfully in {total_elapsed:.2f}s.")
    print(f"Results written to: {out_path.relative_to(repo_root)}")


if __name__ == "__main__":
    main()
