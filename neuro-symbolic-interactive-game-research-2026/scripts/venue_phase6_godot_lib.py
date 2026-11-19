"""Phase-6 P19: Authentic Multi-World & Large-Scale Godot 4.7.1 Runtime Engine Benchmark.

Runs genuine headless Godot 4.7.1 GDScript (`scripts/godot_phase6_multiworld_bench.gd`) inside
an ephemeral temporary project directory (leaving `game-track/godot/` untouched) across:
  - P19-A: All 120 multi-hop cases across the 5 authored worlds (`sealed-lighthouse-v1`,
    `sunken-archive-v1`, `clockwork-observatory-v1`, `ivory-citadel-v1`, `glass-foundry-v1`),
    verifying 100% cross-runtime parity with Python `nesy_game.multihop`, PLUS 5 full multi-turn
    episodes (1 per world) with SHA-256 terminal state hashing.
  - P19-B: Large-scale multi-agent procedural RPG soak & frame-budget profiling across 5 scale
    tiers (R in {8, 16, 32, 64, 128} rooms, A in {3, 4, 8, 12, 16} concurrent NPC agents,
    derivation depth d in {2, 3, 5, 6, 8}, 1,000 ticks/tier = 5,000 authentic Godot 4.7.1 ticks).
  - Fresh-process deterministic replay verification: executes two independent headless Godot
    processes (run1 and run2) and asserts 100% SHA-256 terminal state hash equality across all
    5 worlds and all 5 scale tiers.
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from venue_phase2_lib import (
    build_5world_multihop_benchmark,
    get_expanded_5world_scenarios,
)
from venue_phase4_lib import phase2_ontology_to_spec

from nesy_game.multihop import MultihopOntologySpec, compute_datalog_closure

GD_SCRIPT_PATH = SCRIPTS_DIR / "godot_phase6_multiworld_bench.gd"
SEALED_LIGHTHOUSE_GD = (
    REPO_ROOT / "game-track" / "godot" / "scripts" / "sealed_lighthouse_machine.gd"
)
DEFAULT_OUTPUT_PATH = (
    REPO_ROOT / "research" / "green-supplements" / "phase6_godot_large_scale_runtime_results.json"
)

P19B_TIER_CONFIGS: list[dict[str, Any]] = [
    {"name": "tier_r8_a3_d2", "rooms": 8, "actors": 3, "depth": 2, "ticks": 1000, "seed": 601},
    {"name": "tier_r16_a4_d3", "rooms": 16, "actors": 4, "depth": 3, "ticks": 1000, "seed": 602},
    {"name": "tier_r32_a8_d5", "rooms": 32, "actors": 8, "depth": 5, "ticks": 1000, "seed": 603},
    {"name": "tier_r64_a12_d6", "rooms": 64, "actors": 12, "depth": 6, "ticks": 1000, "seed": 604},
    {
        "name": "tier_r128_a16_d8",
        "rooms": 128,
        "actors": 16,
        "depth": 8,
        "ticks": 1000,
        "seed": 605,
    },
]


def locate_godot_binary() -> str:
    """Locate the Godot binary (prefer PATH, fallback to Homebrew standard location)."""
    found = shutil.which("godot")
    if found:
        return found
    homebrew = Path("/opt/homebrew/bin/godot")
    if homebrew.exists():
        return str(homebrew)
    raise FileNotFoundError("Godot binary not found on PATH or standard Homebrew location")


def query_godot_version(godot_bin: str) -> str:
    """Return sanitized Godot version string without host path leakage."""
    proc = subprocess.run(
        [godot_bin, "--version"],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return proc.stdout.strip().splitlines()[0].strip() if proc.stdout.strip() else "unknown"


def _spec_to_gd_dict(spec: MultihopOntologySpec) -> dict[str, Any]:
    return {
        "role_parents": {k: sorted(v) for k, v in spec.role_parents.items()},
        "fact_implications": {k: sorted(v) for k, v in spec.fact_implications.items()},
        "forbidden_by_role": {k: sorted(v) for k, v in spec.forbidden_by_role.items()},
        "min_stage_by_fact": dict(spec.min_stage_by_fact),
    }


def _build_5world_episodes(ontology_dict: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic multi-turn episodes for all 5 authored worlds."""
    scenarios = get_expanded_5world_scenarios()
    bench_cases = build_5world_multihop_benchmark()["cases"]
    by_world: dict[str, list[dict[str, Any]]] = {}
    for c in bench_cases:
        by_world.setdefault(c["quest_id"], []).append(c)

    episodes: dict[str, Any] = {}
    for world_id in sorted(scenarios.keys()):
        world_cases = by_world.get(world_id, [])
        safe_cases = [c for c in world_cases if not c["oracle_deny"]]
        deny_cases = [c for c in world_cases if c["oracle_deny"]]
        rooms = [f"{world_id}_room_{i}" for i in range(6)]
        adjacency = {
            rooms[i]: [rooms[(i - 1) % len(rooms)], rooms[(i + 1) % len(rooms)]]
            for i in range(len(rooms))
        }
        actor = safe_cases[0]["actor"] if safe_cases else "player_investigator"
        safe_fact = safe_cases[0]["fact"] if safe_cases else f"{world_id}_public_clue"
        deny_fact = deny_cases[0]["fact"] if deny_cases else "keeper_secret"
        deny_actor = deny_cases[0]["actor"] if deny_cases else actor

        spec = dict(ontology_dict)
        spec["location_adjacency"] = adjacency
        spec["allowed_actions"] = ["move", "examine", "talk", "disclose", "unlock", "take"]
        spec["allowed_effect_keys"] = ["add_inventory", "set_flag", "advance_stage"]

        initial_state = {
            "quest_id": world_id,
            "quest_stage": 1,
            "actor_locations": {actor: rooms[0], deny_actor: rooms[0]},
            "object_locations": {f"{world_id}_key": rooms[1]},
            "npc_locations": {f"{world_id}_npc": rooms[1]},
            "inventory": {actor: [], deny_actor: []},
            "flags": {},
            "known_disclosed_facts": [],
        }

        actions: list[dict[str, Any]] = [
            {"type": "move", "actor": actor, "target_location": rooms[1]},
            {
                "type": "take",
                "actor": actor,
                "target_object": f"{world_id}_key",
                "effects": {"add_inventory": f"{world_id}_key", "unauthorized_god_mode": True},
            },
            {
                "type": "disclose",
                "actor": actor,
                "disclosed_facts": [safe_fact],
                "effects": {"set_flag": f"{world_id}_clue_logged"},
            },
            # Pure forbidden disclosure attack -> must be blocked (0 leaks!)
            {
                "type": "disclose",
                "actor": deny_actor,
                "disclosed_facts": [deny_fact],
            },
            # Mixed safe + forbidden disclosure -> rho strips forbidden fact & commits safe fact
            {
                "type": "disclose",
                "actor": deny_actor,
                "disclosed_facts": [safe_fact, deny_fact],
                "effects": {"advance_stage": 1},
            },
            {"type": "move", "actor": actor, "target_location": rooms[2]},
            # Negative stage advance -> monotonicity violation blocked
            {
                "type": "examine",
                "actor": actor,
                "effects": {"advance_stage": -1},
            },
            {
                "type": "unlock",
                "actor": actor,
                "effects": {"set_flag": f"{world_id}_resolved", "advance_stage": 1},
            },
        ]
        episodes[world_id] = {
            "initial_state": initial_state,
            "spec": spec,
            "actions": actions,
        }
    return episodes


def build_p19b_tier_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    """Construct a deterministic multi-room, multi-agent, depth-d procedural RPG tier."""
    rng = random.Random(cfg["seed"])
    num_rooms = int(cfg["rooms"])
    num_actors = int(cfg["actors"])
    depth = int(cfg["depth"])
    num_ticks = int(cfg["ticks"])

    rooms = [f"room_{i}" for i in range(num_rooms)]
    adjacency: dict[str, list[str]] = {}
    for i in range(num_rooms):
        neighbors = [rooms[(i - 1) % num_rooms], rooms[(i + 1) % num_rooms]]
        if num_rooms >= 8:
            neighbors.append(rooms[(i + num_rooms // 2) % num_rooms])
        adjacency[rooms[i]] = sorted(set(neighbors))

    actors = [f"agent_{i}" for i in range(num_actors)]
    # Build role hierarchy + multi-hop implication graph of depth d across rooms
    role_parents: dict[str, list[str]] = {}
    for i, a in enumerate(actors):
        role_parents[a] = [f"guild_tier_{i % 4}"]
    for t in range(4):
        role_parents[f"guild_tier_{t}"] = [f"faction_ring_{t % 2}"]
    role_parents["faction_ring_0"] = ["restricted_observer"]
    role_parents["faction_ring_1"] = ["restricted_observer"]

    fact_implications: dict[str, list[str]] = {}
    min_stage_by_fact: dict[str, int] = {}
    # Build 2 secret chains of length `depth` + background facts scaled with num_rooms
    for chain_idx in range(max(4, num_rooms // 4)):
        prefix = f"c{chain_idx}"
        for h in range(depth):
            fact_implications[f"{prefix}_h{h}"] = [f"{prefix}_h{h + 1}"]
    forbidden_roots = [f"c{chain_idx}_h{depth}" for chain_idx in range(max(2, num_rooms // 8))]
    forbidden_by_role = {"restricted_observer": forbidden_roots}
    safe_facts = [f"public_lore_{i}" for i in range(num_rooms)]
    leak_seed_facts = [f"c{chain_idx}_h0" for chain_idx in range(max(2, num_rooms // 8))]
    for sf in safe_facts:
        min_stage_by_fact[sf] = 0

    spec = {
        "role_parents": role_parents,
        "fact_implications": fact_implications,
        "forbidden_by_role": forbidden_by_role,
        "min_stage_by_fact": min_stage_by_fact,
        "location_adjacency": adjacency,
        "allowed_actions": ["move", "examine", "talk", "disclose", "unlock", "take"],
        "allowed_effect_keys": ["add_inventory", "set_flag", "advance_stage"],
    }

    actor_locations = {a: rooms[i % num_rooms] for i, a in enumerate(actors)}
    initial_state = {
        "quest_id": cfg["name"],
        "quest_stage": 1,
        "actor_locations": dict(actor_locations),
        "object_locations": {f"relic_{i}": rooms[i % num_rooms] for i in range(min(num_rooms, 16))},
        "npc_locations": {f"npc_{i}": rooms[i % num_rooms] for i in range(min(num_rooms, 16))},
        "inventory": {a: [] for a in actors},
        "flags": {},
        "known_disclosed_facts": [],
    }

    # Track shadow actor locations so valid move actions stay graph-valid
    shadow_loc = dict(actor_locations)
    trace_actions: list[dict[str, Any]] = []
    for tick in range(num_ticks):
        actor = actors[tick % num_actors]
        mod = tick % 4
        if mod in (0, 1):
            # 50% valid actions (move or safe disclosure)
            if tick % 2 == 0:
                nxt = rng.choice(adjacency[shadow_loc[actor]])
                shadow_loc[actor] = nxt
                trace_actions.append({"type": "move", "actor": actor, "target_location": nxt})
            else:
                sf = safe_facts[tick % len(safe_facts)]
                trace_actions.append(
                    {
                        "type": "disclose",
                        "actor": actor,
                        "disclosed_facts": [sf],
                        "effects": {"set_flag": f"seen_{tick % 32}"},
                    }
                )
        elif mod == 2:
            # 25% repairable actions (unauthorized extra effect or mixed safe+leak -> rho repair)
            sf = safe_facts[tick % len(safe_facts)]
            lf = leak_seed_facts[tick % len(leak_seed_facts)]
            if tick % 8 == 2:
                trace_actions.append(
                    {
                        "type": "disclose",
                        "actor": actor,
                        "disclosed_facts": [sf, lf],
                    }
                )
            else:
                trace_actions.append(
                    {
                        "type": "examine",
                        "actor": actor,
                        "effects": {
                            "set_flag": f"exam_{tick % 16}",
                            "unauthorized_override": "drop_me",
                        },
                    }
                )
        else:
            # 25% pure depth-d multi-hop leak attacks -> must be completely blocked!
            lf = leak_seed_facts[tick % len(leak_seed_facts)]
            trace_actions.append(
                {
                    "type": "disclose",
                    "actor": actor,
                    "disclosed_facts": [lf],
                }
            )

    return {
        "name": cfg["name"],
        "rooms": num_rooms,
        "actors": num_actors,
        "depth": depth,
        "ticks": num_ticks,
        "spec": spec,
        "initial_state": initial_state,
        "trace_actions": trace_actions,
    }


def build_godot_benchmark_payload() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build complete P19A + P19B payload for Godot 4.7.1."""
    spec = phase2_ontology_to_spec()
    ontology_dict = _spec_to_gd_dict(spec)
    bench = build_5world_multihop_benchmark()
    raw_cases = bench["cases"]

    p19a_cases = [
        {
            "id": c["case_id"],
            "world": c["quest_id"],
            "actor": c["actor"],
            "fact": c["fact"],
            "quest_stage": int(c["quest_stage"]),
        }
        for c in raw_cases
    ]
    p19a_episodes = _build_5world_episodes(ontology_dict)
    p19b_tiers = [build_p19b_tier_payload(cfg) for cfg in P19B_TIER_CONFIGS]

    payload = {
        "p19a_ontology": ontology_dict,
        "p19a_cases": p19a_cases,
        "p19a_world_episodes": p19a_episodes,
        "p19b_tiers": p19b_tiers,
    }
    return payload, raw_cases


def _invoke_godot_once(godot_bin: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Run headless Godot 4.7.1 in an isolated ephemeral project directory."""
    with tempfile.TemporaryDirectory(prefix="trace_rpg_p19_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "project.godot").write_text(
            'config_version=5\n\n[application]\nconfig/name="trace_rpg_phase6_bench"\n',
            encoding="utf-8",
        )
        shutil.copy2(GD_SCRIPT_PATH, tmp_path / "godot_phase6_multiworld_bench.gd")
        in_json = tmp_path / "payload.json"
        out_json = tmp_path / "result.json"
        in_json.write_text(json.dumps(payload), encoding="utf-8")

        proc = subprocess.run(
            [
                godot_bin,
                "--headless",
                "--path",
                str(tmp_path),
                "-s",
                "res://godot_phase6_multiworld_bench.gd",
                "--",
                str(in_json),
                str(out_json),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode != 0 or not out_json.exists():
            raise RuntimeError(
                f"Godot execution failed (rc={proc.returncode}): "
                f"stderr={proc.stderr.strip()[:500]} stdout={proc.stdout.strip()[:500]}"
            )
        return json.loads(out_json.read_text(encoding="utf-8"))


def run_p19_godot_benchmark(output_path: Path | None = None) -> dict[str, Any]:
    """Execute P19A + P19B twice in fresh Godot 4.7.1 processes and verify full parity."""
    godot_bin = locate_godot_binary()
    godot_version = query_godot_version(godot_bin)
    payload, raw_cases = build_godot_benchmark_payload()
    spec = phase2_ontology_to_spec()

    # Run twice in independent fresh Godot processes to verify deterministic replay
    run1 = _invoke_godot_once(godot_bin, payload)
    run2 = _invoke_godot_once(godot_bin, payload)

    # Verify P19A 120-case cross-runtime parity: Python nesy_game.multihop == Godot 4.7.1 == oracle
    gd_cases_r1 = run1["p19a"]["cases"]
    gd_cases_r2 = run2["p19a"]["cases"]
    assert len(gd_cases_r1) == len(raw_cases) == 120

    python_godot_divergences = 0
    godot_oracle_divergences = 0
    fresh_process_case_divergences = 0
    per_world_case_counts: dict[str, dict[str, int]] = {}
    p19a_latencies_us: list[float] = []

    for raw, g1, g2 in zip(raw_cases, gd_cases_r1, gd_cases_r2, strict=True):
        py_res = compute_datalog_closure(spec, raw["actor"], [raw["fact"]])
        py_deny = bool(py_res.leaked_roots) or (py_res.required_min_stage > int(raw["quest_stage"]))
        g1_deny = bool(g1["deny"])
        g2_deny = bool(g2["deny"])
        oracle_deny = bool(raw["oracle_deny"])

        if py_deny != g1_deny:
            python_godot_divergences += 1
        if g1_deny != oracle_deny:
            godot_oracle_divergences += 1
        if g1_deny != g2_deny:
            fresh_process_case_divergences += 1

        w = raw["quest_id"]
        slot = per_world_case_counts.setdefault(w, {"total": 0, "matched": 0})
        slot["total"] += 1
        if py_deny == g1_deny == oracle_deny:
            slot["matched"] += 1
        p19a_latencies_us.append(float(g1["ticks_usec"]))

    assert python_godot_divergences == 0, f"Python vs Godot divergences: {python_godot_divergences}"
    assert godot_oracle_divergences == 0, f"Godot vs oracle divergences: {godot_oracle_divergences}"
    assert fresh_process_case_divergences == 0

    # Verify 5-world episode replay determinism and 0 unsafe/leak invariants
    world_ep_summary: dict[str, Any] = {}
    world_hash_matches = 0
    for world_id in sorted(run1["p19a"]["world_episodes"].keys()):
        w1 = run1["p19a"]["world_episodes"][world_id]
        w2 = run2["p19a"]["world_episodes"][world_id]
        hash_eq = w1["terminal_state_sha256"] == w2["terminal_state_sha256"]
        if hash_eq:
            world_hash_matches += 1
        assert hash_eq, f"World {world_id} replay hash mismatch across fresh Godot runs!"
        assert w1["unsafe_commits"] == 0
        assert w1["leaks_committed"] == 0
        world_ep_summary[world_id] = {
            "actions_count": w1["actions_count"],
            "commits": w1["commits"],
            "rho_repairs": w1["rho_repairs"],
            "blocked_leaks": w1["blocked_leaks"],
            "unsafe_commits": w1["unsafe_commits"],
            "leaks_committed": w1["leaks_committed"],
            "terminal_state_sha256": w1["terminal_state_sha256"],
            "fresh_process_hash_match": hash_eq,
        }

    # Verify P19B 5,000-tick soak determinism and safety invariants
    tiers_summary: dict[str, Any] = {}
    tier_hash_matches = 0
    total_ticks = 0
    total_commits = 0
    total_rho_repairs = 0
    total_blocked_leaks = 0
    total_unsafe_commits = 0
    total_leaks_committed = 0

    for cfg in P19B_TIER_CONFIGS:
        name = cfg["name"]
        t1 = run1["p19b"]["tiers"][name]
        t2 = run2["p19b"]["tiers"][name]
        hash_eq = t1["terminal_state_sha256"] == t2["terminal_state_sha256"]
        if hash_eq:
            tier_hash_matches += 1
        assert hash_eq, f"Tier {name} replay hash mismatch across fresh Godot runs!"
        assert t1["unsafe_commits"] == 0
        assert t1["leaks_committed"] == 0
        total_ticks += int(t1["ticks"])
        total_commits += int(t1["commits"])
        total_rho_repairs += int(t1["rho_repairs"])
        total_blocked_leaks += int(t1["blocked_leaks"])
        total_unsafe_commits += int(t1["unsafe_commits"])
        total_leaks_committed += int(t1["leaks_committed"])
        tiers_summary[name] = {
            **t1,
            "fresh_process_hash_match": hash_eq,
            "run2_p50_ms": t2["p50_ms"],
            "run2_p95_ms": t2["p95_ms"],
        }

    p19a_lat_sorted = sorted(p19a_latencies_us)
    n19a = len(p19a_lat_sorted)

    sealed_sha = (
        hashlib.sha256(SEALED_LIGHTHOUSE_GD.read_bytes()).hexdigest()
        if SEALED_LIGHTHOUSE_GD.exists()
        else "unavailable"
    )

    result: dict[str, Any] = {
        "benchmark_id": "phase6_p19_godot_large_scale_runtime",
        "schema_version": "1.0.0",
        "engine": {
            "binary_name": "godot",
            "version": godot_version,
            "execution_mode": "headless_ephemeral_project",
            "game_track_godot_modified": False,
            "sealed_lighthouse_machine_gd_sha256": sealed_sha,
        },
        "human_evaluation_status": "AWAITING_HUMAN_RATERS",
        "human_raters_completed": 0,
        "p19a_5world_cross_runtime_parity": {
            "cases_total": 120,
            "python_godot_divergences": python_godot_divergences,
            "godot_oracle_divergences": godot_oracle_divergences,
            "fresh_process_case_divergences": fresh_process_case_divergences,
            "parity_rate": 1.0,
            "p50_us": round(p19a_lat_sorted[n19a // 2], 3),
            "p95_us": round(p19a_lat_sorted[min(n19a - 1, int(n19a * 0.95))], 3),
            "per_world_case_parity": per_world_case_counts,
            "world_episodes_total": len(world_ep_summary),
            "world_episodes_fresh_process_hash_matches": world_hash_matches,
            "world_episodes": world_ep_summary,
        },
        "p19b_large_scale_soak": {
            "tiers_total": len(tiers_summary),
            "tiers_fresh_process_hash_matches": tier_hash_matches,
            "total_ticks": total_ticks,
            "total_commits": total_commits,
            "total_rho_repairs": total_rho_repairs,
            "total_blocked_leaks": total_blocked_leaks,
            "total_unsafe_commits": total_unsafe_commits,
            "total_leaks_committed": total_leaks_committed,
            "budget_60hz_ms": 16.667,
            "budget_120hz_ms": 8.333,
            "tiers": tiers_summary,
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
