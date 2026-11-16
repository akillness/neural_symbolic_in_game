"""Isolated 0-LLM-call latency scaling benchmark for TRACE-RPG symbolic components.

Benchmarks median (p50), p95, max, min, and mean latency in milliseconds across
scaling graph and rule/fact sizes for:
  (a) validator: ``validate_candidate(state, action)`` (``V(c_t, a_t)``)
  (b) repair: ``counterexample_guided_repair(state, candidate, validation, attempt)`` (``rho``)
  (c) reachability: ``production_reachable_locations`` (closure) and
      ``reference_reachable_locations`` (state-space BFS)
  (d) verification & replay: ``verify_trace_record`` (SHA-256),
      ``replay_trace_record``, and ``replay_trace_jsonl``

Zero LLM calls are made. No frozen artifacts are modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import statistics
import sys
import tempfile
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nesy_game.contracts import ActionPolicy, CandidateAction, WorldState
from nesy_game.repair import counterexample_guided_repair
from nesy_game.runtime import (
    execute_with_repair,
    replay_trace_jsonl,
    replay_trace_record,
    to_jsonable,
    verify_trace_record,
    write_trace_jsonl,
)
from nesy_game.validator import validate_candidate
from scripts.review_reference import reference_reachable_locations
from scripts.run_gemini_review_evaluation import _graph, production_reachable_locations

DEFAULT_OUTPUT_DIR = ROOT / "research/academic-pipeline/latency-scaling-benchmark"
ROOM_SCALES = (4, 16, 64, 256)
TOPOLOGIES = ("locked_chain", "bypass_branch")
FACT_RULE_SCALES = (10, 100, 500, 1000, 2000)
ACTIVE_CONSTRAINT_ARITY_CAP = 100
EPISODE_LENGTHS = (1, 10, 50, 100)


def _percentile(sorted_values: Sequence[float], q: float) -> float:
    """Linear-interpolation percentile (R-7 / NumPy default) for q in [0, 1]."""
    if not sorted_values:
        raise ValueError("cannot compute percentile of empty sequence")
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = pos - lo
    return sorted_values[lo] + frac * (sorted_values[hi] - sorted_values[lo])


def _benchmark(
    fn: Callable[[], Any],
    *,
    warmup: int,
    iterations: int,
) -> dict[str, float | int]:
    for _ in range(warmup):
        fn()
    samples_ms: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter_ns()
        fn()
        t1 = time.perf_counter_ns()
        samples_ms.append((t1 - t0) / 1_000_000.0)
    samples_ms.sort()
    return {
        "iterations": iterations,
        "warmup": warmup,
        "min_ms": round(samples_ms[0], 6),
        "p50_ms": round(statistics.median(samples_ms), 6),
        "p95_ms": round(_percentile(samples_ms, 0.95), 6),
        "max_ms": round(samples_ms[-1], 6),
        "mean_ms": round(statistics.fmean(samples_ms), 6),
    }


def _build_scaled_state_and_candidates(
    scale_n: int,
) -> tuple[WorldState, CandidateAction, CandidateAction]:
    """Build a deterministic WorldState with `scale_n` facts, policies, objects, and knowledge."""
    room_count = max(4, min(scale_n, 256))
    locations = frozenset(f"r{i}" for i in range(room_count))
    reachable = frozenset(f"r{i}" for i in range(room_count // 2))
    facts = frozenset(f"fact_{i}" for i in range(scale_n))
    inventory = frozenset(f"item_{i}" for i in range(max(2, scale_n // 10)))
    object_locations = {f"obj_{i}": f"r{i % room_count}" for i in range(scale_n)}
    # Place target_unreachable_obj in an unreachable room
    object_locations["unreachable_obj"] = f"r{room_count - 1}"

    k_req = max(2, min(scale_n // 5, ACTIVE_CONSTRAINT_ARITY_CAP))
    req_pre = frozenset(f"fact_{i}" for i in range(k_req))
    req_eff = frozenset(f"eff_{i}" for i in range(k_req))
    allow_eff = req_eff | frozenset(f"opt_eff_{i}" for i in range(k_req))

    action_policies: dict[str, ActionPolicy] = {
        f"policy_{i}": ActionPolicy(
            required_preconditions=frozenset({f"fact_{i % scale_n}"}),
            allowed_effects=frozenset({f"eff_{i % scale_n}"}),
            required_effects=frozenset({f"eff_{i % scale_n}"}),
            allowed_quest_stage_effects=frozenset({2, 3}),
        )
        for i in range(scale_n)
    }
    action_policies["target_action"] = ActionPolicy(
        required_preconditions=req_pre,
        allowed_effects=allow_eff,
        required_effects=req_eff,
        allowed_quest_stage_effects=frozenset({2, 3}),
    )
    action_policies["restricted_action"] = ActionPolicy(
        required_preconditions=req_pre,
        allowed_effects=req_eff,
        required_effects=req_eff,
        allowed_quest_stage_effects=frozenset(),
    )

    known_facts = frozenset(f"fact_{i}" for i in range(scale_n))
    forbidden = frozenset(f"secret_{i}" for i in range(max(2, scale_n // 10)))
    npc_knowledge = {"npc_0": known_facts}
    forbidden_disclosures = {"npc_0": forbidden}

    state = WorldState(
        state_id=f"state_n{scale_n}",
        locations=locations,
        reachable_locations=reachable,
        object_locations=object_locations,
        inventory=inventory,
        facts=facts,
        action_policies=action_policies,
        npc_knowledge=npc_knowledge,
        forbidden_disclosures=forbidden_disclosures,
        quest_stage=2,
    )

    valid_candidate = CandidateAction(
        action_id=f"act_valid_n{scale_n}",
        actor_id="npc_0",
        action_type="target_action",
        preconditions=req_pre,
        effects=req_eff,
        required_objects=frozenset({"item_0"}),
        used_facts=frozenset({"fact_0", "fact_1"}),
        disclosed_facts=frozenset({"fact_0"}),
        required_quest_stage=1,
        quest_stage_effect=3,
        narrative_text="Valid action under symbolic constraints.",
        metadata={"scale": scale_n},
    )

    # Multi-error candidate that exercises repairable + irreparable error paths
    omitted_pre = frozenset(sorted(req_pre)[: k_req // 2])
    unsatisfied_pre = frozenset(f"missing_fact_{i}" for i in range(max(1, k_req // 4)))
    unauthorized_eff = frozenset(f"illegal_eff_{i}" for i in range(max(1, k_req // 4)))
    omitted_eff = frozenset(sorted(req_eff)[: k_req // 2])

    invalid_candidate = CandidateAction(
        action_id=f"act_invalid_n{scale_n}",
        actor_id="npc_0",
        action_type="restricted_action",
        preconditions=omitted_pre | unsatisfied_pre,
        effects=omitted_eff | unauthorized_eff,
        required_objects=frozenset({"unreachable_obj"}),
        used_facts=frozenset({"unknown_npc_fact_0"}),
        disclosed_facts=frozenset({"secret_0"}),
        required_quest_stage=5,
        quest_stage_effect=3,
        narrative_text="Invalid candidate exercising multi-error validation and repair.",
        metadata={"scale": scale_n},
    )
    return state, valid_candidate, invalid_candidate


def benchmark_validator(warmup: int, iterations: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scale_n in FACT_RULE_SCALES:
        state, valid_cand, invalid_cand = _build_scaled_state_and_candidates(scale_n)

        res_valid = validate_candidate(state, valid_cand)
        if not res_valid.valid:
            raise ValueError(f"Expected valid candidate at N={scale_n}, got {res_valid.errors}")
        stats_valid = _benchmark(
            lambda s=state, c=valid_cand: validate_candidate(s, c),
            warmup=warmup,
            iterations=iterations,
        )
        rows.append(
            {
                "component": "validator",
                "case": "valid_pass",
                "facts_rules_count": scale_n,
                "error_count": 0,
                **stats_valid,
            }
        )

        res_invalid = validate_candidate(state, invalid_cand)
        if res_invalid.valid:
            raise ValueError(f"Expected invalid candidate at N={scale_n}")
        stats_invalid = _benchmark(
            lambda s=state, c=invalid_cand: validate_candidate(s, c),
            warmup=warmup,
            iterations=iterations,
        )
        rows.append(
            {
                "component": "validator",
                "case": "multi_error_fail",
                "facts_rules_count": scale_n,
                "error_count": len(res_invalid.errors),
                **stats_invalid,
            }
        )
    return rows


def benchmark_repair(warmup: int, iterations: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scale_n in FACT_RULE_SCALES:
        state, _, invalid_cand = _build_scaled_state_and_candidates(scale_n)
        # Also build a purely repairable candidate of matching scale
        policy = state.action_policies["restricted_action"]
        req_pre = sorted(policy.required_preconditions)
        req_eff = sorted(policy.required_effects)
        half = max(1, len(req_pre) // 2)
        repairable_cand = CandidateAction(
            action_id=f"act_repairable_n{scale_n}",
            actor_id="npc_0",
            action_type="restricted_action",
            preconditions=frozenset(req_pre[:half]) | frozenset({"missing_pre_0"}),
            effects=frozenset(req_eff[:half]) | frozenset({"illegal_eff_0"}),
            required_objects=frozenset({"item_0"}),
            used_facts=frozenset({"fact_0"}),
            disclosed_facts=frozenset({"fact_0"}),
            required_quest_stage=1,
            quest_stage_effect=3,
            narrative_text="Purely repairable candidate.",
            metadata={"scale": scale_n},
        )
        val_repairable = validate_candidate(state, repairable_cand)
        if val_repairable.valid:
            raise ValueError(f"Expected repairable candidate to start invalid at N={scale_n}")
        stats_rep = _benchmark(
            lambda s=state, c=repairable_cand, v=val_repairable: counterexample_guided_repair(
                s, c, v, 1
            ),
            warmup=warmup,
            iterations=iterations,
        )
        repaired = counterexample_guided_repair(state, repairable_cand, val_repairable, 1)
        repaired_val = validate_candidate(state, repaired)
        if not repaired_val.valid:
            raise ValueError(
                f"Expected repairable candidate to converge at N={scale_n}, got {repaired_val.errors}"
            )
        rows.append(
            {
                "component": "counterexample_guided_repair",
                "case": "repairable_converges",
                "facts_rules_count": scale_n,
                "error_count": len(val_repairable.errors),
                "candidate_preconditions": len(repairable_cand.preconditions),
                "candidate_effects": len(repairable_cand.effects),
                **stats_rep,
            }
        )

        val_multi = validate_candidate(state, invalid_cand)
        stats_multi = _benchmark(
            lambda s=state, c=invalid_cand, v=val_multi: counterexample_guided_repair(s, c, v, 1),
            warmup=warmup,
            iterations=iterations,
        )
        rows.append(
            {
                "component": "counterexample_guided_repair",
                "case": "mixed_repairable_irreparable",
                "facts_rules_count": scale_n,
                "error_count": len(val_multi.errors),
                "candidate_preconditions": len(invalid_cand.preconditions),
                "candidate_effects": len(invalid_cand.effects),
                **stats_multi,
            }
        )
    return rows


def benchmark_reachability(warmup: int, iterations: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for room_count in ROOM_SCALES:
        for topology in TOPOLOGIES:
            graph = _graph(room_count, topology, ("start", "goal"))
            prod_set = production_reachable_locations(graph)
            ref_set = reference_reachable_locations(graph)
            if prod_set != ref_set:
                raise ValueError(f"Reachability mismatch at {room_count} {topology}")

            # Fewer iterations only if 256-room BFS is slow; otherwise keep consistent
            iters = iterations if room_count <= 64 else min(iterations, 100)
            wup = min(warmup, iters // 2)

            stats_closure = _benchmark(
                lambda g=graph: production_reachable_locations(g),
                warmup=wup,
                iterations=iters,
            )
            rows.append(
                {
                    "component": "reachability_closure",
                    "algorithm": "production_reachable_locations",
                    "room_count": room_count,
                    "edge_count": len(graph["edges"]),
                    "topology": topology,
                    "reachable_count": len(prod_set),
                    **stats_closure,
                }
            )

            stats_bfs = _benchmark(
                lambda g=graph: reference_reachable_locations(g),
                warmup=wup,
                iterations=iters,
            )
            rows.append(
                {
                    "component": "reachability_bfs",
                    "algorithm": "reference_reachable_locations",
                    "room_count": room_count,
                    "edge_count": len(graph["edges"]),
                    "topology": topology,
                    "reachable_count": len(ref_set),
                    **stats_bfs,
                }
            )
    return rows


def benchmark_verification_and_replay(warmup: int, iterations: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    # 1. Single-record SHA-256 verification and semantic replay across fact/rule scales
    for scale_n in FACT_RULE_SCALES:
        state, valid_cand, _ = _build_scaled_state_and_candidates(scale_n)
        outcome = execute_with_repair(
            state,
            valid_cand,
            repairer=counterexample_guided_repair,
            repair_budget=1,
            trace_context={"benchmark": "latency_scaling", "scale": scale_n},
        )
        if outcome.status != "commit":
            raise ValueError(f"Expected commit at N={scale_n}, got {outcome.status}")
        record = to_jsonable(outcome)
        payload_bytes = len(json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8"))

        if not verify_trace_record(record):
            raise ValueError(f"SHA-256 verification failed at N={scale_n}")
        iters = iterations if scale_n <= 500 else min(iterations, 100)
        wup = min(warmup, iters // 2)

        stats_sha = _benchmark(
            lambda r=record: verify_trace_record(r),
            warmup=wup,
            iterations=iters,
        )
        rows.append(
            {
                "component": "sha256_verify_record",
                "facts_rules_count": scale_n,
                "record_bytes": payload_bytes,
                **stats_sha,
            }
        )

        replayed_state = replay_trace_record(record)
        if replayed_state != outcome.state:
            raise ValueError(f"Replay state mismatch at N={scale_n}")
        stats_replay = _benchmark(
            lambda r=record: replay_trace_record(r),
            warmup=wup,
            iterations=iters,
        )
        rows.append(
            {
                "component": "replay_trace_record",
                "facts_rules_count": scale_n,
                "record_bytes": payload_bytes,
                **stats_replay,
            }
        )

    # 2. Full JSONL episode replay across episode lengths (at N=100 facts/rules)
    raw_base_state, base_cand, _ = _build_scaled_state_and_candidates(100)
    max_ep_len = max(EPISODE_LENGTHS)
    base_policy = raw_base_state.action_policies[base_cand.action_type]
    ep_policies = dict(raw_base_state.action_policies)
    ep_policies[base_cand.action_type] = ActionPolicy(
        required_preconditions=base_policy.required_preconditions,
        allowed_effects=base_policy.allowed_effects
        | frozenset(f"step_eff_{s}" for s in range(max_ep_len)),
        required_effects=base_policy.required_effects,
        allowed_quest_stage_effects=base_policy.allowed_quest_stage_effects,
    )
    base_state = WorldState(
        state_id=raw_base_state.state_id,
        locations=raw_base_state.locations,
        reachable_locations=raw_base_state.reachable_locations,
        object_locations=raw_base_state.object_locations,
        inventory=raw_base_state.inventory,
        facts=raw_base_state.facts,
        action_policies=ep_policies,
        npc_knowledge=raw_base_state.npc_knowledge,
        forbidden_disclosures=raw_base_state.forbidden_disclosures,
        quest_stage=raw_base_state.quest_stage,
    )
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        for ep_len in EPISODE_LENGTHS:
            jsonl_path = tmp_path / f"episode_{ep_len}.jsonl"
            cur_state = base_state
            for step in range(ep_len):
                step_cand = CandidateAction(
                    action_id=f"step_{step}",
                    actor_id=base_cand.actor_id,
                    action_type=base_cand.action_type,
                    preconditions=base_cand.preconditions,
                    effects=base_cand.effects | frozenset({f"step_eff_{step}"}),
                    required_objects=base_cand.required_objects,
                    used_facts=base_cand.used_facts,
                    disclosed_facts=base_cand.disclosed_facts,
                    required_quest_stage=base_cand.required_quest_stage,
                    quest_stage_effect=base_cand.quest_stage_effect,
                    narrative_text=f"Step {step}",
                    metadata={"step": step},
                )
                outcome = execute_with_repair(
                    cur_state,
                    step_cand,
                    repairer=counterexample_guided_repair,
                    repair_budget=1,
                    trace_context={"step": step},
                )
                if outcome.status != "commit":
                    raise ValueError(f"Expected commit at step={step}, got {outcome.status}")
                write_trace_jsonl(jsonl_path, outcome)
                cur_state = outcome.state

            file_bytes = jsonl_path.stat().st_size
            ep_iters = 50 if ep_len <= 10 else 20
            ep_warmup = 5
            final_state = replay_trace_jsonl(jsonl_path, initial_state=base_state)
            if final_state != cur_state:
                raise ValueError(f"Episode JSONL replay mismatch at ep_len={ep_len}")

            stats_ep = _benchmark(
                lambda p=jsonl_path, init=base_state: replay_trace_jsonl(p, initial_state=init),
                warmup=ep_warmup,
                iterations=ep_iters,
            )
            rows.append(
                {
                    "component": "replay_trace_jsonl",
                    "episode_length": ep_len,
                    "facts_rules_count": 100,
                    "file_bytes": file_bytes,
                    **stats_ep,
                }
            )

    return rows


def render_summary_md(results: dict[str, Any]) -> str:
    env = results["environment"]
    cfg = results["config"]
    lines: list[str] = [
        "# Latency & Scaling Benchmark Summary (0-LLM-Call)",
        "",
        f"- **Host (coarse)**: `{env['os']}` (`{env['arch']}`)",
        "- **LLM calls**: `0` (`model_called = false`; purely deterministic symbolic runtime)",
        (
            f"- **Active constraint arity cap (`active_constraint_arity_cap`)**: `{cfg['active_constraint_arity_cap']}` "
            "(per-action `k_req = max(2, min(N // 5, 100))` saturates at `100` for `N >= 500`, so `N in {500, 1000, 2000}` "
            "measures ambient store-size scaling at fixed active constraint arity `100`)"
        ),
        "",
        "## (a) Validator `V(c_t, a_t)` Latency Across Fact/Rule Scales",
        "",
        "> Note: Active per-action constraint arity caps at `active_constraint_arity_cap = 100` (`N >= 500` isolates store-size scaling across `N` facts, policies, objects, and NPC knowledge entries).",
        "",
        "| Case | Facts/Rules (`N`) | Active Arity (`k_req`) | Errors | p50 (ms) | p95 (ms) | max (ms) | Iterations |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in results["benchmarks"]["validator"]:
        k_req = max(2, min(r["facts_rules_count"] // 5, cfg["active_constraint_arity_cap"]))
        lines.append(
            f"| {r['case']} | {r['facts_rules_count']} | {k_req} | {r['error_count']} | "
            f"{r['p50_ms']:.4f} | {r['p95_ms']:.4f} | {r['max_ms']:.4f} | {r['iterations']} |"
        )

    lines.extend(
        [
            "",
            "## (b) Counterexample-Guided Repair `rho` Latency Across Fact/Rule Scales",
            "",
            "> Note: For `N >= 500`, active per-action constraint arity stays fixed at `100` (`103` repairable errors / `156` mixed errors), measuring store-size scaling.",
            "",
            "| Case | Facts/Rules (`N`) | Active Arity (`k_req`) | Errors | p50 (ms) | p95 (ms) | max (ms) | Iterations |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for r in results["benchmarks"]["repair"]:
        k_req = max(2, min(r["facts_rules_count"] // 5, cfg["active_constraint_arity_cap"]))
        lines.append(
            f"| {r['case']} | {r['facts_rules_count']} | {k_req} | {r['error_count']} | "
            f"{r['p50_ms']:.4f} | {r['p95_ms']:.4f} | {r['max_ms']:.4f} | {r['iterations']} |"
        )

    lines.extend(
        [
            "",
            "## (c) Reachability (Closure vs State-Space BFS) Across Room Scales",
            "",
            "| Algorithm | Topology | Rooms | Edges | Reachable | p50 (ms) | p95 (ms) | max (ms) | Iterations |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for r in results["benchmarks"]["reachability"]:
        lines.append(
            f"| `{r['algorithm']}` | {r['topology']} | {r['room_count']} | {r['edge_count']} | "
            f"{r['reachable_count']} | {r['p50_ms']:.4f} | {r['p95_ms']:.4f} | {r['max_ms']:.4f} | {r['iterations']} |"
        )
    r256_rows = {
        (r["topology"], r["algorithm"]): r
        for r in results["benchmarks"]["reachability"]
        if r["room_count"] == 256
    }
    lc_prod = r256_rows[("locked_chain", "production_reachable_locations")]
    lc_bfs = r256_rows[("locked_chain", "reference_reachable_locations")]
    bb_prod = r256_rows[("bypass_branch", "production_reachable_locations")]
    bb_bfs = r256_rows[("bypass_branch", "reference_reachable_locations")]
    lines.extend(
        [
            "",
            "### `R = 256` Topology Pair Summary (Both Topologies Explicitly Reported)",
            "",
            (
                f"- **`locked_chain` (`R=256`, `{lc_prod['edge_count']}` edges, `{lc_prod['reachable_count']}` reachable)**: "
                f"closure `p50={lc_prod['p50_ms']:.4f} ms`, `p95={lc_prod['p95_ms']:.4f} ms`, `max={lc_prod['max_ms']:.4f} ms` "
                f"vs. state-space BFS `p50={lc_bfs['p50_ms']:.4f} ms`, `p95={lc_bfs['p95_ms']:.4f} ms`, `max={lc_bfs['max_ms']:.4f} ms`."
            ),
            (
                f"- **`bypass_branch` (`R=256`, `{bb_prod['edge_count']}` edges, `{bb_prod['reachable_count']}` reachable)**: "
                f"closure `p50={bb_prod['p50_ms']:.4f} ms`, `p95={bb_prod['p95_ms']:.4f} ms`, `max={bb_prod['max_ms']:.4f} ms` "
                f"vs. state-space BFS `p50={bb_bfs['p50_ms']:.4f} ms`, `p95={bb_bfs['p95_ms']:.4f} ms`, `max={bb_bfs['max_ms']:.4f} ms`."
            ),
        ]
    )

    lines.extend(
        [
            "",
            "## (d) SHA-256 Verification & JSONL Replay Across Scales",
            "",
            "| Component | Scale (`N` or `L`) | Payload/File Bytes | p50 (ms) | p95 (ms) | max (ms) | Iterations |",
            "|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for r in results["benchmarks"]["verification_and_replay"]:
        if "episode_length" in r:
            scale_label = f"L={r['episode_length']} steps (N=100)"
            size_bytes = r["file_bytes"]
        else:
            scale_label = f"N={r['facts_rules_count']}"
            size_bytes = r["record_bytes"]
        lines.append(
            f"| `{r['component']}` | {scale_label} | {size_bytes} | "
            f"{r['p50_ms']:.4f} | {r['p95_ms']:.4f} | {r['max_ms']:.4f} | {r['iterations']} |"
        )

    lines.append("")
    return "\n".join(lines)


def run_all(output_dir: Path, warmup: int, iterations: int) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.perf_counter()

    source_paths = sorted(
        {
            Path(__file__).resolve(),
            ROOT / "src/nesy_game/contracts.py",
            ROOT / "src/nesy_game/validator.py",
            ROOT / "src/nesy_game/repair.py",
            ROOT / "src/nesy_game/runtime.py",
            ROOT / "scripts/review_reference.py",
            ROOT / "scripts/run_gemini_review_evaluation.py",
        }
    )
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }

    results: dict[str, Any] = {
        "benchmark_id": "latency-scaling-benchmark",
        "model_called": False,
        "llm_calls": 0,
        "environment": {
            "os": platform.system(),
            "arch": platform.machine(),
        },
        "config": {
            "room_scales": list(ROOM_SCALES),
            "topologies": list(TOPOLOGIES),
            "fact_rule_scales": list(FACT_RULE_SCALES),
            "active_constraint_arity_cap": ACTIVE_CONSTRAINT_ARITY_CAP,
            "scaling_regime_note": (
                "Active per-action constraint arity k_req = max(2, min(N // 5, 100)) caps at 100 "
                "for N >= 500; N in {500, 1000, 2000} measures ambient store-size scaling "
                "(facts, policies, objects, NPC knowledge) at fixed active constraint arity 100."
            ),
            "episode_lengths": list(EPISODE_LENGTHS),
            "default_warmup": warmup,
            "default_iterations": iterations,
            "percentile_method": "linear_interpolation_r7",
        },
        "source_hashes": source_hashes,
        "benchmarks": {
            "validator": benchmark_validator(warmup, iterations),
            "repair": benchmark_repair(warmup, iterations),
            "reachability": benchmark_reachability(warmup, iterations),
            "verification_and_replay": benchmark_verification_and_replay(warmup, iterations),
        },
    }
    results["total_benchmark_wall_seconds"] = round(time.perf_counter() - t_start, 4)

    results_path = output_dir / "results.json"
    summary_path = output_dir / "summary.md"
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    summary_path.write_text(render_summary_md(results), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--iterations", type=int, default=200)
    args = parser.parse_args()

    results = run_all(args.output_dir, args.warmup, args.iterations)
    print(f"Wrote {args.output_dir / 'results.json'}")
    print(f"Wrote {args.output_dir / 'summary.md'}")
    print(f"Total wall time: {results['total_benchmark_wall_seconds']}s")


if __name__ == "__main__":
    main()
