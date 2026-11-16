"""Deterministic multi-error and conflict-pair repair convergence audit.

Extends the 32 frozen graph/state combinations from
``scripts/run_gemini_review_evaluation.py`` with:
1. Repairable multi-error co-occurrence fixtures (2 to 5 co-occurring
   errors across preconditions, effects, and quest_stage_effect).
2. Mixed repairable + irreparable co-occurrence fixtures (e.g.,
   POLICY_PRECONDITION_OMISSION + POLICY_EFFECT_VIOLATION +
   FORBIDDEN_DISCLOSURE / NPC_KNOWLEDGE_VIOLATION /
   UNREACHABLE_REQUIRED_OBJECT / QUEST_STAGE_VIOLATION).
3. Conflict-pair fixtures where the same entity ("ready") is involved in
   both POLICY_PRECONDITION_OMISSION and UNSATISFIED_PRECONDITION:
   - Cross-attempt state-backed conflict fixtures via ``execute_with_repair``
     (``"ready"`` required by SIGNAL policy but absent from ``state.facts``),
     testing period-2 oscillation vs convergence across K in {0, 1, 2, 3}.
   - Direct same-pass simultaneous conflict-guard fixtures calling
     ``counterexample_guided_repair`` with both error codes on the same
     entity in one ``ValidationResult`` (with and without co-occurring
     repairable errors).

Zero LLM calls are made. No frozen artifacts are modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nesy_game.contracts import (  # noqa: E402
    CandidateAction,
    ValidationError,
    ValidationResult,
    WorldState,
    parse_candidate_mapping,
)
from nesy_game.repair import (  # noqa: E402
    GUIDED_IRREPARABLE_CODES,
    GUIDED_REPAIRABLE_CODES,
    counterexample_guided_repair,
)
from nesy_game.runtime import execute_with_repair, replay_trace_record, to_jsonable  # noqa: E402
from nesy_game.validator import validate_candidate  # noqa: E402
from scripts.review_reference import generic_accepts, reference_reachable_locations  # noqa: E402
from scripts.run_gemini_review_evaluation import (  # noqa: E402
    PROTOCOL_PATH,
    _graph,
    _state,
    _world_state,
    production_reachable_locations,
    structural_signature,
)

DEFAULT_OUTPUT_DIR = ROOT / "research/academic-pipeline/multi-error-repair-audit"
BUDGETS: tuple[int, ...] = (0, 1, 2, 3)

VARIANT_SPECS: tuple[dict[str, str], ...] = (
    # Family 1: Purely repairable multi-error co-occurrence
    {
        "variant": "multi_pre_eff_violation",
        "family": "repairable_multi",
        "description": "POLICY_PRECONDITION_OMISSION(ready) + POLICY_EFFECT_VIOLATION(treasure_spawned)",
    },
    {
        "variant": "multi_pre_eff_omission_violation",
        "family": "repairable_multi",
        "description": "POLICY_PRECONDITION_OMISSION(ready) + POLICY_EFFECT_OMISSION(signal_restored) + POLICY_EFFECT_VIOLATION(treasure_spawned)",
    },
    {
        "variant": "multi_all_5_repairable",
        "family": "repairable_multi",
        "description": "All 5 GUIDED_REPAIRABLE_CODES co-occurring simultaneously",
    },
    # Family 2: Mixed repairable + irreparable co-occurrence (partial-clear holds)
    {
        "variant": "mixed_pre_eff_forbidden",
        "family": "mixed_partial_clear",
        "description": "POLICY_PRECONDITION_OMISSION + POLICY_EFFECT_VIOLATION + FORBIDDEN_DISCLOSURE(keeper_secret; irreparable at stage 0, permitted at stage 1)",
    },
    {
        "variant": "mixed_pre_eff_knowledge",
        "family": "mixed_partial_clear",
        "description": "POLICY_PRECONDITION_OMISSION + POLICY_EFFECT_VIOLATION + NPC_KNOWLEDGE_VIOLATION(unknown_fact)",
    },
    {
        "variant": "mixed_pre_eff_forbidden_knowledge",
        "family": "mixed_partial_clear",
        "description": "POLICY_PRECONDITION_OMISSION + POLICY_EFFECT_VIOLATION + FORBIDDEN_DISCLOSURE + NPC_KNOWLEDGE_VIOLATION",
    },
    {
        "variant": "mixed_pre_eff_relic",
        "family": "mixed_partial_clear",
        "description": "POLICY_PRECONDITION_OMISSION + POLICY_EFFECT_VIOLATION + UNREACHABLE_REQUIRED_OBJECT(relic; graph-dependent)",
    },
    {
        "variant": "mixed_eff_future_stage",
        "family": "mixed_partial_clear",
        "description": "POLICY_EFFECT_OMISSION + POLICY_EFFECT_VIOLATION + QUEST_STAGE_VIOLATION(stage+1)",
    },
    # Family 3: Cross-attempt conflict-pair fixtures (same entity in POLICY_PRECONDITION_OMISSION & UNSATISFIED_PRECONDITION)
    {
        "variant": "conflict_cross_attempt_omitted",
        "family": "conflict_pair",
        "description": "Policy requires 'ready' absent from state.facts; candidate starts omitting 'ready'",
    },
    {
        "variant": "conflict_cross_attempt_present",
        "family": "conflict_pair",
        "description": "Policy requires 'ready' absent from state.facts; candidate starts declaring 'ready'",
    },
    {
        "variant": "conflict_cross_attempt_plus_effect",
        "family": "conflict_pair",
        "description": "Conflict-pair entity 'ready' + co-occurring repairable POLICY_EFFECT_VIOLATION(treasure_spawned)",
    },
)

SIMULTANEOUS_GUARD_VARIANTS: tuple[dict[str, Any], ...] = (
    {
        "variant": "guard_conflict_only_present",
        "preconditions": ["ready"],
        "effects": ["signal_restored"],
        "extra_errors": [],
        "description": "Same-pass POLICY_PRECONDITION_OMISSION(ready) + UNSATISFIED_PRECONDITION(ready) with 'ready' present",
    },
    {
        "variant": "guard_conflict_only_omitted",
        "preconditions": [],
        "effects": ["signal_restored"],
        "extra_errors": [],
        "description": "Same-pass POLICY_PRECONDITION_OMISSION(ready) + UNSATISFIED_PRECONDITION(ready) with 'ready' omitted",
    },
    {
        "variant": "guard_conflict_plus_effect_present",
        "preconditions": ["ready"],
        "effects": ["signal_restored", "treasure_spawned"],
        "extra_errors": [("POLICY_EFFECT_VIOLATION", "treasure_spawned")],
        "description": "Same-pass conflict on 'ready' (present) + POLICY_EFFECT_VIOLATION(treasure_spawned)",
    },
    {
        "variant": "guard_conflict_plus_effect_omitted",
        "preconditions": [],
        "effects": ["signal_restored", "treasure_spawned"],
        "extra_errors": [("POLICY_EFFECT_VIOLATION", "treasure_spawned")],
        "description": "Same-pass conflict on 'ready' (omitted) + POLICY_EFFECT_VIOLATION(treasure_spawned)",
    },
)


def _json(value: Any) -> str:
    return json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _load_base_states() -> list[dict[str, Any]]:
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    design = protocol["graph_design"]
    states: list[dict[str, Any]] = []
    for room_count, topology, placement, stage in product(
        design["room_counts"],
        design["topologies"],
        design["key_placement_patterns"],
        design["quest_stages"],
    ):
        state_id = f"n{room_count}-{topology}-{'-'.join(placement)}-q{stage}"
        graph = _graph(room_count, topology, placement)
        state = _state(graph, stage, state_id)
        states.append(
            {
                "state_id": state_id,
                "stage": stage,
                "graph": graph,
                "state": state,
            }
        )
    if len(states) != design["state_count"]:
        raise ValueError(f"Expected {design['state_count']} base states, got {len(states)}")
    return states


def _candidate_for_variant(case_id: str, variant: str, stage: int) -> dict[str, Any]:
    base = {
        "action_id": case_id,
        "actor_id": "keeper",
        "action_type": "SIGNAL",
        "preconditions": ["ready"],
        "effects": ["signal_restored"],
        "required_objects": [],
        "used_facts": [],
        "disclosed_facts": [],
        "required_quest_stage": stage,
        "quest_stage_effect": stage + 1,
        "narrative_text": "Restore the signal.",
        "metadata": {"variant": variant},
    }
    overrides: dict[str, dict[str, Any]] = {
        "multi_pre_eff_violation": {
            "preconditions": [],
            "effects": ["signal_restored", "treasure_spawned"],
        },
        "multi_pre_eff_omission_violation": {
            "preconditions": [],
            "effects": ["treasure_spawned"],
        },
        "multi_all_5_repairable": {
            "preconditions": ["absent_fact"],
            "effects": ["treasure_spawned"],
            "quest_stage_effect": stage + 2,
        },
        "mixed_pre_eff_forbidden": {
            "preconditions": [],
            "effects": ["signal_restored", "treasure_spawned"],
            "disclosed_facts": ["keeper_secret"],
        },
        "mixed_pre_eff_knowledge": {
            "preconditions": [],
            "effects": ["signal_restored", "treasure_spawned"],
            "used_facts": ["unknown_fact"],
        },
        "mixed_pre_eff_forbidden_knowledge": {
            "preconditions": [],
            "effects": ["signal_restored", "treasure_spawned"],
            "disclosed_facts": ["keeper_secret"],
            "used_facts": ["unknown_fact"],
        },
        "mixed_pre_eff_relic": {
            "preconditions": [],
            "effects": ["signal_restored", "treasure_spawned"],
            "required_objects": ["relic"],
        },
        "mixed_eff_future_stage": {
            "effects": ["treasure_spawned"],
            "required_quest_stage": stage + 1,
        },
        "conflict_cross_attempt_omitted": {
            "preconditions": [],
        },
        "conflict_cross_attempt_present": {
            "preconditions": ["ready"],
        },
        "conflict_cross_attempt_plus_effect": {
            "preconditions": [],
            "effects": ["signal_restored", "treasure_spawned"],
        },
    }
    if variant not in overrides:
        raise ValueError(f"Unknown variant: {variant}")
    base.update(overrides[variant])
    return base


def build_cases() -> list[dict[str, Any]]:
    base_states = _load_base_states()
    cases: list[dict[str, Any]] = []
    for base in base_states:
        state_id = base["state_id"]
        stage = base["stage"]
        graph = base["graph"]
        for spec in VARIANT_SPECS:
            variant = spec["variant"]
            family = spec["family"]
            case_state = deepcopy(base["state"])
            if family == "conflict_pair":
                # Policy requires "ready", but "ready" is absent from state.facts.
                case_state["facts"] = [fact for fact in case_state["facts"] if fact != "ready"]
                case_state["state_id"] = f"{state_id}--unsatisfiable-ready"
            case_id = f"{state_id}--{variant}"
            cases.append(
                {
                    "case_id": case_id,
                    "base_state_id": state_id,
                    "stage": stage,
                    "variant": variant,
                    "family": family,
                    "graph": deepcopy(graph),
                    "state": case_state,
                    "candidate": _candidate_for_variant(case_id, variant, stage),
                }
            )
    return cases


def _error_pairs(validation_errors: Sequence[Any]) -> list[tuple[str, str]]:
    return [(err.code, err.entity) for err in validation_errors]


def _classify_trace_convergence(
    state: WorldState,
    outcome: Any,
    budget: int,
) -> dict[str, Any]:
    candidates = [attempt.candidate for attempt in outcome.trace]
    signatures = [structural_signature(to_jsonable(cand)) for cand in candidates]

    observed_trajectory_fixed_point = False
    fixed_point_attempt: int | None = None
    if outcome.status == "commit":
        observed_trajectory_fixed_point = True
        fixed_point_attempt = outcome.attempts
    else:
        for idx in range(1, len(candidates)):
            if candidates[idx] == candidates[idx - 1]:
                observed_trajectory_fixed_point = True
                fixed_point_attempt = idx
                break

    # Lookahead fixed-point check: would another call to rho change the terminal candidate?
    if outcome.status == "commit":
        terminal_is_fixed_point = True
    elif budget == 0:
        terminal_is_fixed_point = False
    else:
        next_candidate = counterexample_guided_repair(
            state, outcome.candidate, outcome.validation, budget + 1
        )
        terminal_is_fixed_point = next_candidate == outcome.candidate

    # Period-2 oscillation check on the observed trajectory: c_t == c_{t-2} while c_t != c_{t-1}
    observed_period_2 = False
    if outcome.status == "fallback" and len(candidates) >= 3:
        for idx in range(2, len(candidates)):
            if candidates[idx] == candidates[idx - 2] and candidates[idx] != candidates[idx - 1]:
                observed_period_2 = True
                break

    # Lookahead period-2 cycle check from the terminal candidate (for K >= 1).
    terminal_in_period_2 = observed_period_2
    if (
        outcome.status == "fallback"
        and budget >= 1
        and not terminal_is_fixed_point
        and not observed_period_2
    ):
        c_next1 = counterexample_guided_repair(
            state, outcome.candidate, outcome.validation, budget + 1
        )
        v_next1 = validate_candidate(state, c_next1)
        c_next2 = counterexample_guided_repair(state, c_next1, v_next1, budget + 2)
        if c_next2 == outcome.candidate and c_next1 != outcome.candidate:
            terminal_in_period_2 = True

    return {
        "candidate_signatures": signatures,
        "observed_trajectory_fixed_point": observed_trajectory_fixed_point,
        "fixed_point_attempt": fixed_point_attempt,
        "terminal_is_fixed_point": terminal_is_fixed_point,
        "observed_period_2": observed_period_2,
        "terminal_in_period_2": terminal_in_period_2,
    }


def run_case_at_budget(case: Mapping[str, Any], budget: int) -> dict[str, Any]:
    started = time.perf_counter()
    candidate = parse_candidate_mapping(case["candidate"], allow_defaults=False)
    state = _world_state(case["state"])

    reference_data = deepcopy(case["state"])
    reference_data["reachable_locations"] = sorted(reference_reachable_locations(case["graph"]))
    reference_state = _world_state(reference_data)
    reference_initial_valid = generic_accepts(reference_state, candidate)
    closure_locs = sorted(production_reachable_locations(case["graph"]))
    graph_agreement = closure_locs == reference_data["reachable_locations"]

    outcome = execute_with_repair(
        state,
        candidate,
        repairer=counterexample_guided_repair if budget > 0 else None,
        repair_budget=budget,
        trace_context={
            "study_id": "multi-error-repair-audit-20261116",
            "case_id": case["case_id"],
            "budget": budget,
        },
    )
    native_json = to_jsonable(outcome)
    replayed = replay_trace_record(native_json)
    native_replay_equal = to_jsonable(replayed) == to_jsonable(outcome.state)
    if not native_replay_equal:
        raise ValueError(f"Native replay mismatch on {case['case_id']} at K={budget}")

    status = "COMMITTED" if outcome.status == "commit" else "HOLD"
    reference_final_valid = generic_accepts(reference_state, outcome.candidate)

    initial_errors = outcome.trace[0].validation.errors
    final_errors = outcome.validation.errors
    initial_error_codes = [err.code for err in initial_errors]
    final_error_codes = [err.code for err in final_errors]
    initial_repairable_count = sum(err.code in GUIDED_REPAIRABLE_CODES for err in initial_errors)
    final_repairable_count = sum(err.code in GUIDED_REPAIRABLE_CODES for err in final_errors)
    initial_irreparable_count = sum(err.code in GUIDED_IRREPARABLE_CODES for err in initial_errors)
    final_irreparable_count = sum(err.code in GUIDED_IRREPARABLE_CODES for err in final_errors)

    partial_clear_hold = status == "HOLD" and len(final_errors) < len(initial_errors)
    convergence = _classify_trace_convergence(state, outcome, budget)
    latency_ms = (time.perf_counter() - started) * 1000.0

    return {
        "case_id": case["case_id"],
        "base_state_id": case["base_state_id"],
        "stage": case["stage"],
        "variant": case["variant"],
        "family": case["family"],
        "budget": budget,
        "status": status,
        "attempts_executed": outcome.attempts,
        "reference_initial_valid": reference_initial_valid,
        "reference_final_valid": reference_final_valid,
        "graph_agreement": graph_agreement,
        "native_replay_equal": native_replay_equal,
        "initial_error_count": len(initial_errors),
        "final_error_count": len(final_errors),
        "errors_cleared": len(initial_errors) - len(final_errors),
        "initial_error_codes": initial_error_codes,
        "final_error_codes": final_error_codes,
        "initial_repairable_count": initial_repairable_count,
        "final_repairable_count": final_repairable_count,
        "initial_irreparable_count": initial_irreparable_count,
        "final_irreparable_count": final_irreparable_count,
        "partial_clear_hold": partial_clear_hold,
        "per_attempt_error_counts": [len(step.validation.errors) for step in outcome.trace],
        "per_attempt_error_pairs": [_error_pairs(step.validation.errors) for step in outcome.trace],
        **convergence,
        "latency_ms": latency_ms,
    }


def summarize_slice(
    rows: Sequence[Mapping[str, Any]],
    prev_rows_by_case: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, Any]:
    assigned = len(rows)
    initial_valid = sum(row["reference_initial_valid"] is True for row in rows)
    initial_invalid = sum(row["reference_initial_valid"] is False for row in rows)
    committed = sum(row["status"] == "COMMITTED" for row in rows)
    held = sum(row["status"] == "HOLD" for row in rows)
    safe_commits = sum(
        row["status"] == "COMMITTED" and row["reference_final_valid"] is True for row in rows
    )
    unsafe_commits = sum(
        row["status"] == "COMMITTED" and row["reference_final_valid"] is False for row in rows
    )
    false_rejections = sum(
        row["status"] == "HOLD" and row["reference_initial_valid"] is True for row in rows
    )
    repaired = sum(
        row["status"] == "COMMITTED"
        and row["reference_final_valid"] is True
        and row["reference_initial_valid"] is False
        for row in rows
    )

    partial_clear_holds = sum(row["partial_clear_hold"] for row in rows)
    traj_fixed_points = sum(row["observed_trajectory_fixed_point"] for row in rows)
    terminal_fixed_points = sum(row["terminal_is_fixed_point"] for row in rows)
    observed_period_2 = sum(row["observed_period_2"] for row in rows)
    terminal_in_period_2 = sum(row["terminal_in_period_2"] for row in rows)

    total_initial_errors = sum(row["initial_error_count"] for row in rows)
    total_final_errors = sum(row["final_error_count"] for row in rows)
    total_errors_cleared = total_initial_errors - total_final_errors

    incremental_recovered = 0
    incremental_eligible = 0
    if prev_rows_by_case is not None:
        for row in rows:
            prev = prev_rows_by_case[row["case_id"]]
            if prev["status"] == "HOLD":
                incremental_eligible += 1
                if row["status"] == "COMMITTED" and row["reference_final_valid"] is True:
                    incremental_recovered += 1

    attempt_hist = Counter(
        row["attempts_executed"] for row in rows if row["status"] == "COMMITTED"
    )

    return {
        "assigned": assigned,
        "initial_valid": initial_valid,
        "initial_invalid": initial_invalid,
        "committed": committed,
        "held": held,
        "safe_commits": safe_commits,
        "unsafe_commits": unsafe_commits,
        "false_rejections": false_rejections,
        "repaired": repaired,
        "recovery_rate": repaired / initial_invalid if initial_invalid else None,
        "hold_rate": held / assigned if assigned else None,
        "partial_clear_hold_count": partial_clear_holds,
        "partial_clear_hold_rate_among_holds": partial_clear_holds / held if held else None,
        "partial_clear_hold_rate_among_assigned": partial_clear_holds / assigned if assigned else None,
        "observed_trajectory_fixed_point_count": traj_fixed_points,
        "observed_trajectory_fixed_point_rate": traj_fixed_points / assigned if assigned else None,
        "terminal_fixed_point_count": terminal_fixed_points,
        "terminal_fixed_point_rate": terminal_fixed_points / assigned if assigned else None,
        "observed_period_2_count": observed_period_2,
        "observed_period_2_rate": observed_period_2 / assigned if assigned else None,
        "terminal_in_period_2_count": terminal_in_period_2,
        "terminal_in_period_2_rate": terminal_in_period_2 / assigned if assigned else None,
        "total_initial_errors": total_initial_errors,
        "total_final_errors": total_final_errors,
        "total_errors_cleared": total_errors_cleared,
        "error_reduction_rate": total_errors_cleared / total_initial_errors if total_initial_errors else None,
        "incremental_recovered_from_prev_k": incremental_recovered if prev_rows_by_case is not None else None,
        "incremental_eligible_from_prev_k": incremental_eligible if prev_rows_by_case is not None else None,
        "incremental_recovery_rate_among_prev_holds": (
            incremental_recovered / incremental_eligible
            if prev_rows_by_case is not None and incremental_eligible
            else (0.0 if prev_rows_by_case is not None else None)
        ),
        "commit_attempt_histogram": {str(k): attempt_hist[k] for k in sorted(attempt_hist)},
        "native_replay_equal_count": sum(row["native_replay_equal"] for row in rows),
        "graph_agreement_count": sum(row["graph_agreement"] for row in rows),
    }


def run_simultaneous_conflict_guard_audit(base_states: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Audit counterexample_guided_repair when both POLICY_PRECONDITION_OMISSION
    and UNSATISFIED_PRECONDITION name 'ready' in the SAME ValidationResult.
    """
    rows: list[dict[str, Any]] = []
    for base in base_states:
        state_data = deepcopy(base["state"])
        state_data["facts"] = [fact for fact in state_data["facts"] if fact != "ready"]
        state = _world_state(state_data)
        for spec in SIMULTANEOUS_GUARD_VARIANTS:
            case_id = f"{base['state_id']}--{spec['variant']}"
            cand = CandidateAction(
                action_id=case_id,
                actor_id="keeper",
                action_type="SIGNAL",
                preconditions=frozenset(spec["preconditions"]),
                effects=frozenset(spec["effects"]),
                required_quest_stage=base["stage"],
                quest_stage_effect=base["stage"] + 1,
                narrative_text="Restore the signal.",
                metadata={"variant": spec["variant"]},
            )
            errors = [
                ValidationError(
                    "POLICY_PRECONDITION_OMISSION",
                    "ready",
                    "Simultaneous conflict test: omitted policy precondition 'ready'.",
                    "Restore 'ready'.",
                ),
                ValidationError(
                    "UNSATISFIED_PRECONDITION",
                    "ready",
                    "Simultaneous conflict test: 'ready' is false in state.",
                    "Drop 'ready'.",
                ),
            ]
            for code, entity in spec["extra_errors"]:
                errors.append(
                    ValidationError(
                        code,
                        entity,
                        f"Co-occurring repairable error {code}({entity}).",
                        "Repair non-conflicting field.",
                    )
                )
            synthetic_validation = ValidationResult(
                valid=False,
                errors=tuple(errors),
                checks_run=("action_policy", "precondition"),
            )

            trajectory = [cand]
            cur = cand
            for attempt in (1, 2, 3):
                cur = counterexample_guided_repair(state, cur, synthetic_validation, attempt)
                trajectory.append(cur)

            ready_preserved = all(
                ("ready" in step.preconditions) == ("ready" in cand.preconditions)
                for step in trajectory
            )
            effects_repaired_step_1 = trajectory[1].effects == frozenset({"signal_restored"})
            fixed_point_by_step_1 = trajectory[1] == trajectory[2] == trajectory[3]
            post_step1_real_val = validate_candidate(state, trajectory[1])
            post_step1_real_codes = [err.code for err in post_step1_real_val.errors]

            rows.append(
                {
                    "case_id": case_id,
                    "variant": spec["variant"],
                    "ready_preserved": ready_preserved,
                    "effects_repaired_step_1": effects_repaired_step_1,
                    "fixed_point_by_step_1": fixed_point_by_step_1,
                    "c0_eq_c1": trajectory[0] == trajectory[1],
                    "c1_eq_c2": trajectory[1] == trajectory[2],
                    "c2_eq_c3": trajectory[2] == trajectory[3],
                    "post_step1_real_error_codes": post_step1_real_codes,
                }
            )

    by_variant: dict[str, Any] = {}
    for spec in SIMULTANEOUS_GUARD_VARIANTS:
        v = spec["variant"]
        vrows = [r for r in rows if r["variant"] == v]
        n = len(vrows)
        by_variant[v] = {
            "description": spec["description"],
            "assigned": n,
            "ready_preserved_count": sum(r["ready_preserved"] for r in vrows),
            "ready_preserved_rate": sum(r["ready_preserved"] for r in vrows) / n,
            "effects_repaired_step_1_count": sum(r["effects_repaired_step_1"] for r in vrows),
            "fixed_point_by_step_1_count": sum(r["fixed_point_by_step_1"] for r in vrows),
            "fixed_point_by_step_1_rate": sum(r["fixed_point_by_step_1"] for r in vrows) / n,
            "c0_eq_c1_count": sum(r["c0_eq_c1"] for r in vrows),
            "post_step1_real_error_codes_distinct": [
                list(codes) for codes in sorted({tuple(r["post_step1_real_error_codes"]) for r in vrows})
            ],
        }

    return {
        "assigned": len(rows),
        "ready_preserved_count": sum(r["ready_preserved"] for r in rows),
        "ready_preserved_rate": sum(r["ready_preserved"] for r in rows) / len(rows),
        "fixed_point_by_step_1_count": sum(r["fixed_point_by_step_1"] for r in rows),
        "fixed_point_by_step_1_rate": sum(r["fixed_point_by_step_1"] for r in rows) / len(rows),
        "by_variant": by_variant,
    }


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def build_summary_markdown(results: Mapping[str, Any]) -> str:
    lines: list[str] = [
        "# Multi-Error & Conflict-Pair Repair Convergence Audit",
        "",
        f"- **Study ID**: `{results['study_id']}`",
        f"- **Model calls**: `{results['model_called']}` (0 LLM calls; deterministic offline audit)",
        f"- **Base graph/state combinations**: `{results['base_state_count']}` (from `run_gemini_review_evaluation.py`)",
        f"- **End-to-end variants**: `{len(VARIANT_SPECS)}` across 3 families -> `{results['cases_per_budget']}` cases per budget `K in {{0, 1, 2, 3}}` (`{results['total_end_to_end_runs']}` total runs)",
        f"- **Graph closure vs BFS agreement**: `{results['graph_agreement_count']}/{results['base_state_count']}`",
        f"- **Native trace replay equality**: `{results['native_replay_equal_total']}/{results['total_end_to_end_runs']}`",
        f"- **Unsafe commits across all runs**: `{results['unsafe_commits_total']}/{results['total_end_to_end_runs']}`",
        "",
        "## 1. Overall Convergence & Recovery Across Budgets (K = 0 -> 1 -> 2 -> 3)",
        "",
        "| Budget K | Assigned | Committed (Safe) | Recovery Rate | Held | Partial-Clear Holds (of Held) | Obs. Traj Fixed-Pt | Terminal Fixed-Pt | Obs. Period-2 Osc. | Terminal Period-2 Osc. | Incr. Recovered (Prev->K) | Error Reduction |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for k in BUDGETS:
        s = results["by_budget"][str(k)]["overall"]
        incr = (
            "—"
            if s["incremental_recovered_from_prev_k"] is None
            else f"{s['incremental_recovered_from_prev_k']}/{s['incremental_eligible_from_prev_k']} ({_fmt_pct(s['incremental_recovery_rate_among_prev_holds'])})"
        )
        pc_str = (
            f"{s['partial_clear_hold_count']}/{s['held']} ({_fmt_pct(s['partial_clear_hold_rate_among_holds'])})"
            if s["held"]
            else f"{s['partial_clear_hold_count']}/0"
        )
        lines.append(
            f"| {k} | {s['assigned']} | {s['committed']} ({s['safe_commits']}) | {_fmt_pct(s['recovery_rate'])} | "
            f"{s['held']} | {pc_str} | "
            f"{s['observed_trajectory_fixed_point_count']}/{s['assigned']} ({_fmt_pct(s['observed_trajectory_fixed_point_rate'])}) | "
            f"{s['terminal_fixed_point_count']}/{s['assigned']} ({_fmt_pct(s['terminal_fixed_point_rate'])}) | "
            f"{s['observed_period_2_count']}/{s['assigned']} ({_fmt_pct(s['observed_period_2_rate'])}) | "
            f"{s['terminal_in_period_2_count']}/{s['assigned']} ({_fmt_pct(s['terminal_in_period_2_rate'])}) | "
            f"{incr} | {s['total_errors_cleared']}/{s['total_initial_errors']} ({_fmt_pct(s['error_reduction_rate'])}) |"
        )

    lines.extend(
        [
            "",
            "## 2. Breakdown by Fixture Family Across K in {0, 1, 2, 3}",
            "",
            "| Family | K | Assigned | Committed | Recovery | Held | Partial-Clear Holds | Obs. Traj Fixed-Pt | Terminal Fixed-Pt | Obs. Period-2 | Term. Period-2 | Incr. Recovered | Error Reduction |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for family in ("repairable_multi", "mixed_partial_clear", "conflict_pair"):
        for k in BUDGETS:
            s = results["by_budget"][str(k)]["by_family"][family]
            incr = (
                "—"
                if s["incremental_recovered_from_prev_k"] is None
                else f"{s['incremental_recovered_from_prev_k']}/{s['incremental_eligible_from_prev_k']}"
            )
            lines.append(
                f"| `{family}` | {k} | {s['assigned']} | {s['committed']} | {_fmt_pct(s['recovery_rate'])} | "
                f"{s['held']} | {s['partial_clear_hold_count']}/{s['held']} ({_fmt_pct(s['partial_clear_hold_rate_among_holds'])}) | "
                f"{s['observed_trajectory_fixed_point_count']}/{s['assigned']} ({_fmt_pct(s['observed_trajectory_fixed_point_rate'])}) | "
                f"{s['terminal_fixed_point_count']}/{s['assigned']} ({_fmt_pct(s['terminal_fixed_point_rate'])}) | "
                f"{s['observed_period_2_count']}/{s['assigned']} | "
                f"{s['terminal_in_period_2_count']}/{s['assigned']} | {incr} | "
                f"{s['total_errors_cleared']}/{s['total_initial_errors']} ({_fmt_pct(s['error_reduction_rate'])}) |"
            )

    lines.extend(
        [
            "",
            "## 3. Per-Variant Results at K=1 and K=3 (Highlighting Incremental K=1->2->3 Stability)",
            "",
            "| Variant | Family | Assigned | K=1 Commit | K=3 Commit | K=1->3 Incr. | K=1 Held (Partial-Clear) | K=1 Obs. Traj FP | K=2 Obs. Traj FP | K=3 Obs. Traj FP | K=3 Obs. Period-2 | Errors Cleared (K=3) |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for spec in VARIANT_SPECS:
        v = spec["variant"]
        s1 = results["by_budget"]["1"]["by_variant"][v]
        s2 = results["by_budget"]["2"]["by_variant"][v]
        s3 = results["by_budget"]["3"]["by_variant"][v]
        incr_1_3 = s3["committed"] - s1["committed"]
        lines.append(
            f"| `{v}` | `{spec['family']}` | {s1['assigned']} | {s1['committed']} | {s3['committed']} | "
            f"{incr_1_3} | {s1['held']} ({s1['partial_clear_hold_count']}) | "
            f"{s1['observed_trajectory_fixed_point_count']}/{s1['assigned']} | "
            f"{s2['observed_trajectory_fixed_point_count']}/{s2['assigned']} | "
            f"{s3['observed_trajectory_fixed_point_count']}/{s3['assigned']} | "
            f"{s3['observed_period_2_count']}/{s3['assigned']} | "
            f"{s3['total_errors_cleared']}/{s3['total_initial_errors']} |"
        )

    guard = results["simultaneous_conflict_guard"]
    lines.extend(
        [
            "",
            "## 4. Direct Single-Pass Simultaneous Conflict-Guard Audit (`counterexample_guided_repair`)",
            "",
            "When `POLICY_PRECONDITION_OMISSION(ready)` and `UNSATISFIED_PRECONDITION(ready)` are supplied in the **same** `ValidationResult` (testing `repair.py`'s `precondition_conflicts` guard across all 32 states):",
            "",
            f"- **Total assigned**: `{guard['assigned']}` (`4` variants x `32` states)",
            f"- **Conflicting entity `ready` untouched across steps 1..3**: `{guard['ready_preserved_count']}/{guard['assigned']}` ({_fmt_pct(guard['ready_preserved_rate'])})",
            f"- **Fixed point reached by step 1 (`c_1 == c_2 == c_3`)**: `{guard['fixed_point_by_step_1_count']}/{guard['assigned']}` ({_fmt_pct(guard['fixed_point_by_step_1_rate'])})",
            "",
            "| Guard Variant | Assigned | `ready` Preserved | Co-occurring Effect Cleared (Step 1) | Fixed Point by Step 1 (`c_1==c_2==c_3`) | `c_0==c_1` |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for v, gv in guard["by_variant"].items():
        lines.append(
            f"| `{v}` | {gv['assigned']} | {gv['ready_preserved_count']}/{gv['assigned']} | "
            f"{gv['effects_repaired_step_1_count']}/{gv['assigned']} | "
            f"{gv['fixed_point_by_step_1_count']}/{gv['assigned']} | "
            f"{gv['c0_eq_c1_count']}/{gv['assigned']} |"
        )

    rep1 = results["by_budget"]["1"]["by_family"]["repairable_multi"]
    rep2 = results["by_budget"]["2"]["by_family"]["repairable_multi"]
    rep3 = results["by_budget"]["3"]["by_family"]["repairable_multi"]
    mix1 = results["by_budget"]["1"]["by_family"]["mixed_partial_clear"]
    mix2 = results["by_budget"]["2"]["by_family"]["mixed_partial_clear"]
    mix_forb1 = results["by_budget"]["1"]["by_variant"]["mixed_pre_eff_forbidden"]
    mix_rel1 = results["by_budget"]["1"]["by_variant"]["mixed_pre_eff_relic"]
    conf1 = results["by_budget"]["1"]["by_family"]["conflict_pair"]
    conf2 = results["by_budget"]["2"]["by_family"]["conflict_pair"]
    conf3 = results["by_budget"]["3"]["by_family"]["conflict_pair"]
    conf_eff3 = results["by_budget"]["3"]["by_variant"]["conflict_cross_attempt_plus_effect"]

    lines.extend(
        [
            "",
            "## 5. Key Empirical Takeaways (Derived Directly from Observed Counts)",
            "",
            (
                f"1. **Parallel multi-error convergence in 1 step (`K=1` suffices when repairable)**: "
                f"`repairable_multi` recovers `{rep1['committed']}/{rep1['assigned']}` ({_fmt_pct(rep1['recovery_rate'])}) at `K=1` (`attempts=1`), "
                f"with `{rep2['incremental_recovered_from_prev_k']}/{rep2['incremental_eligible_from_prev_k']}` incremental recovery at `K=2` "
                f"and `{rep3['incremental_recovered_from_prev_k']}/{rep3['incremental_eligible_from_prev_k']}` at `K=3`."
            ),
            (
                f"2. **Partial-clear holds & fixed-point convergence on mixed errors**: "
                f"On `mixed_partial_clear` (`{mix1['assigned']}` cases), `{mix1['committed']}/{mix1['assigned']}` ({_fmt_pct(mix1['recovery_rate'])}) recover at `K=1` "
                f"(`{mix_forb1['committed']}/{mix_forb1['assigned']}` stage-1 `mixed_pre_eff_forbidden` + `{mix_rel1['committed']}/{mix_rel1['assigned']}` reachable-relic `mixed_pre_eff_relic`), "
                f"and `{mix1['held']}/{mix1['assigned']}` hold with `{mix1['unsafe_commits']}` unsafe commits. "
                f"Among those holds, `{mix1['partial_clear_hold_count']}/{mix1['held']}` ({_fmt_pct(mix1['partial_clear_hold_rate_among_holds'])}) are **partial-clear holds** "
                f"(clearing `{mix1['total_errors_cleared']}/{mix1['total_initial_errors']}` initial errors at `K=1`), reaching a terminal fixed point at `K=1` "
                f"(`{mix1['terminal_fixed_point_count']}/{mix1['assigned']}`) that is observed on the trajectory at `K=2` "
                f"(`{mix2['observed_trajectory_fixed_point_count']}/{mix2['assigned']}`)."
            ),
            (
                f"3. **Cross-attempt conflict-pair oscillation vs. same-pass conflict guard**: "
                f"In `execute_with_repair`, `validate_candidate` cannot emit both `POLICY_PRECONDITION_OMISSION(e)` and `UNSATISFIED_PRECONDITION(e)` in a single pass. "
                f"When `ready` is required by policy but absent from `state.facts`, `conflict_pair` enters a **period-2 cycle** "
                f"(`{conf1['terminal_in_period_2_count']}/{conf1['assigned']}` terminal period-2 at `K=1`; "
                f"observed on trajectory: `{conf1['observed_period_2_count']}/{conf1['assigned']}` at `K=1`, "
                f"`{conf2['observed_period_2_count']}/{conf2['assigned']}` at `K=2`, and `{conf3['observed_period_2_count']}/{conf3['assigned']}` at `K=3` after step 1 clears the transient effect violation in `{conf_eff3['partial_clear_hold_count']}/{conf_eff3['assigned']}` `conflict_cross_attempt_plus_effect` cases). "
                f"By contrast, when both codes co-occur in the same `ValidationResult`, `repair.py`'s conflict guard freezes `ready` immediately "
                f"(`{guard['ready_preserved_count']}/{guard['assigned']}`) while clearing co-occurring effect violations at step 1 (`{guard['fixed_point_by_step_1_count']}/{guard['assigned']}` fixed point)."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_audit(output_dir: Path) -> dict[str, Any]:
    cases = build_cases()
    base_states = _load_base_states()

    rows_by_budget: dict[int, list[dict[str, Any]]] = {}
    by_budget_summary: dict[str, Any] = {}
    prev_rows_by_case: dict[str, dict[str, Any]] | None = None

    for budget in BUDGETS:
        budget_rows = [run_case_at_budget(case, budget) for case in cases]
        rows_by_budget[budget] = budget_rows

        by_family: dict[str, Any] = {}
        for family in ("repairable_multi", "mixed_partial_clear", "conflict_pair"):
            fam_rows = [r for r in budget_rows if r["family"] == family]
            by_family[family] = summarize_slice(fam_rows, prev_rows_by_case)

        by_variant: dict[str, Any] = {}
        for spec in VARIANT_SPECS:
            v = spec["variant"]
            vrows = [r for r in budget_rows if r["variant"] == v]
            by_variant[v] = {
                "family": spec["family"],
                "description": spec["description"],
                **summarize_slice(vrows, prev_rows_by_case),
            }

        by_budget_summary[str(budget)] = {
            "overall": summarize_slice(budget_rows, prev_rows_by_case),
            "by_family": by_family,
            "by_variant": by_variant,
        }
        prev_rows_by_case = {r["case_id"]: r for r in budget_rows}

    guard_summary = run_simultaneous_conflict_guard_audit(base_states)

    all_rows = [row for b in BUDGETS for row in rows_by_budget[b]]
    source_paths = sorted(
        {
            Path(__file__).resolve(),
            ROOT / "src/nesy_game/repair.py",
            ROOT / "src/nesy_game/validator.py",
            ROOT / "src/nesy_game/runtime.py",
            ROOT / "scripts/run_gemini_review_evaluation.py",
            ROOT / "scripts/review_reference.py",
            PROTOCOL_PATH,
        }
    )
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in source_paths
    }

    graph_agreement_count = sum(
        row["graph_agreement"]
        for row in rows_by_budget[0]
        if row["variant"] == VARIANT_SPECS[0]["variant"]
    )

    results: dict[str, Any] = {
        "schema_version": "trace-rpg-multi-error-repair-audit/v1",
        "study_id": "multi-error-repair-audit-20261116",
        "model_called": False,
        "base_state_count": len(base_states),
        "variant_count": len(VARIANT_SPECS),
        "cases_per_budget": len(cases),
        "budgets": list(BUDGETS),
        "total_end_to_end_runs": len(all_rows),
        "graph_agreement_count": graph_agreement_count,
        "native_replay_equal_total": sum(row["native_replay_equal"] for row in all_rows),
        "unsafe_commits_total": sum(
            row["status"] == "COMMITTED" and row["reference_final_valid"] is False
            for row in all_rows
        ),
        "false_rejections_total": sum(
            row["status"] == "HOLD" and row["reference_initial_valid"] is True
            for row in all_rows
        ),
        "source_hashes": source_hashes,
        "variant_specs": list(VARIANT_SPECS),
        "by_budget": by_budget_summary,
        "simultaneous_conflict_guard": guard_summary,
        "rows_by_budget": {str(b): rows_by_budget[b] for b in BUDGETS},
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.json"
    summary_path = output_dir / "summary.md"
    results_path.write_text(
        json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    summary_path.write_text(build_summary_markdown(results), encoding="utf-8")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory for results.json and summary.md",
    )
    args = parser.parse_args()
    results = run_audit(args.output_dir)
    compact = {
        "output_dir": str(args.output_dir),
        "study_id": results["study_id"],
        "cases_per_budget": results["cases_per_budget"],
        "total_end_to_end_runs": results["total_end_to_end_runs"],
        "unsafe_commits_total": results["unsafe_commits_total"],
        "native_replay_equal_total": results["native_replay_equal_total"],
        "by_budget_overall": {
            k: results["by_budget"][k]["overall"] for k in map(str, BUDGETS)
        },
        "simultaneous_conflict_guard": {
            key: results["simultaneous_conflict_guard"][key]
            for key in (
                "assigned",
                "ready_preserved_count",
                "ready_preserved_rate",
                "fixed_point_by_step_1_count",
                "fixed_point_by_step_1_rate",
            )
        },
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
