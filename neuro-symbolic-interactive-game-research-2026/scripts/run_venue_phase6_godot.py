"""CLI entrypoint for Phase-6 P19 Authentic Godot 4.7.1 Multi-World & Large-Scale Benchmark."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from venue_phase6_godot_lib import DEFAULT_OUTPUT_PATH, run_p19_godot_benchmark


def main() -> int:
    result = run_p19_godot_benchmark(output_path=DEFAULT_OUTPUT_PATH)
    p19a = result["p19a_5world_cross_runtime_parity"]
    p19b = result["p19b_large_scale_soak"]
    print(f"Engine: {result['engine']['binary_name']} {result['engine']['version']}")
    print(
        f"P19A 5-world parity: {p19a['cases_total'] - p19a['python_godot_divergences']}/"
        f"{p19a['cases_total']} (divergences={p19a['python_godot_divergences']}, "
        f"world_hash_matches={p19a['world_episodes_fresh_process_hash_matches']}/"
        f"{p19a['world_episodes_total']}, p50={p19a['p50_us']} us)"
    )
    print(
        f"P19B large-scale soak: {p19b['total_ticks']} ticks, commits={p19b['total_commits']}, "
        f"rho_repairs={p19b['total_rho_repairs']}, blocked_leaks={p19b['total_blocked_leaks']}, "
        f"unsafe={p19b['total_unsafe_commits']}, leaks={p19b['total_leaks_committed']}, "
        f"tier_hash_matches={p19b['tiers_fresh_process_hash_matches']}/{p19b['tiers_total']}"
    )
    for name, t in p19b["tiers"].items():
        print(
            f"  {name}: R={t['rooms']} A={t['actors']} d={t['depth']} "
            f"p50={t['p50_ms']:.3f}ms p95={t['p95_ms']:.3f}ms max={t['max_ms']:.3f}ms "
            f"60Hz={t['budget_60hz_pass_rate'] * 100:.2f}% 120Hz={t['budget_120hz_pass_rate'] * 100:.2f}%"
        )
    print(f"Saved: {DEFAULT_OUTPUT_PATH.relative_to(SCRIPTS_DIR.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
