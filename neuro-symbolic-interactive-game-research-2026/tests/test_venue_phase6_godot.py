"""Tests for Phase-6 P19 Authentic Multi-World & Large-Scale Godot 4.7.1 Runtime Benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from venue_phase6_godot_lib import (
    DEFAULT_OUTPUT_PATH,
    P19B_TIER_CONFIGS,
    build_godot_benchmark_payload,
)

FORBIDDEN_LEAK_SUBSTRINGS = (
    "/Users/",
    "/home/",
    "/opt/homebrew/",
    "Jangyoung",
    "Hongik",
    "akillness",
    "127.0.0.1",
)


def test_payload_structure_and_determinism() -> None:
    p1, cases1 = build_godot_benchmark_payload()
    p2, cases2 = build_godot_benchmark_payload()
    assert len(cases1) == 120
    assert len(p1["p19a_cases"]) == 120
    assert len(p1["p19a_world_episodes"]) == 5
    assert len(p1["p19b_tiers"]) == len(P19B_TIER_CONFIGS) == 5
    assert json.dumps(p1, sort_keys=True) == json.dumps(p2, sort_keys=True)
    assert len(cases1) == len(cases2)


def test_saved_p19_results_integrity() -> None:
    assert DEFAULT_OUTPUT_PATH.exists(), f"Missing P19 artifact: {DEFAULT_OUTPUT_PATH}"
    raw_text = DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8")
    for forbidden in FORBIDDEN_LEAK_SUBSTRINGS:
        assert forbidden not in raw_text, f"Leak substring found in P19 JSON: {forbidden}"

    data = json.loads(raw_text)
    assert data["benchmark_id"] == "phase6_p19_godot_large_scale_runtime"
    assert data["engine"]["binary_name"] == "godot"
    assert data["engine"]["game_track_godot_modified"] is False
    assert data["human_evaluation_status"] == "AWAITING_HUMAN_RATERS"
    assert data["human_raters_completed"] == 0

    p19a = data["p19a_5world_cross_runtime_parity"]
    assert p19a["cases_total"] == 120
    assert p19a["python_godot_divergences"] == 0
    assert p19a["godot_oracle_divergences"] == 0
    assert p19a["fresh_process_case_divergences"] == 0
    assert p19a["parity_rate"] == 1.0
    assert p19a["world_episodes_total"] == 5
    assert p19a["world_episodes_fresh_process_hash_matches"] == 5
    for world_id, ep in p19a["world_episodes"].items():
        assert ep["unsafe_commits"] == 0, world_id
        assert ep["leaks_committed"] == 0, world_id
        assert ep["fresh_process_hash_match"] is True, world_id
        assert ep["rho_repairs"] >= 1, world_id
        assert ep["blocked_leaks"] >= 1, world_id

    p19b = data["p19b_large_scale_soak"]
    assert p19b["tiers_total"] == 5
    assert p19b["tiers_fresh_process_hash_matches"] == 5
    assert p19b["total_ticks"] == 5000
    assert p19b["total_unsafe_commits"] == 0
    assert p19b["total_leaks_committed"] == 0
    assert p19b["total_rho_repairs"] > 0
    assert p19b["total_blocked_leaks"] > 0
    for tier_name, t in p19b["tiers"].items():
        assert t["ticks"] == 1000, tier_name
        assert t["unsafe_commits"] == 0, tier_name
        assert t["leaks_committed"] == 0, tier_name
        assert t["fresh_process_hash_match"] is True, tier_name
        assert t["p95_ms"] < 16.667, f"{tier_name} exceeded 60Hz budget: {t['p95_ms']}ms"
        assert t["budget_60hz_pass_rate"] >= 0.99, tier_name
