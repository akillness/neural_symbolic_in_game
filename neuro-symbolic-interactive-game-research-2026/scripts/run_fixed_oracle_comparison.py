#!/usr/bin/env python3
"""Fixed-input, offline controller comparison with designer-authored expectations.

The two controllers receive the same complete state and proposal. The generic
checker is a separate implementation, not a model or a safety authority. The
expectations were authored for these synthetic cases by the implementation
designer, not independently annotated or validated by a human observer.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from review_reference import generic_accepts
from run_local_signal_comparison import fixtures as development_fixtures

from nesy_game.contracts import ActionPolicy, CandidateAction, WorldState
from nesy_game.runtime import execute_with_repair, to_jsonable


def fixtures():
    """Case-level judgments specified separately from either controller.

    Goal means a committed action leaves signal_restored in the state. Expected
    validity is whether the fixed proposal satisfies the encoded game rules.
    Held-out cases were not in the existing development fixture set; they are
    designer-authored, not independently collected or blinded.
    """
    dev = [
        ("development", state, candidate, False, False)
        for state, candidate in development_fixtures()
    ]
    policy = ActionPolicy(
        frozenset(), frozenset({"signal_restored"}), allowed_quest_stage_effects=frozenset({1})
    )

    def held(case_id, candidate_kwargs, **state_kwargs):
        state = WorldState(
            state_id=case_id,
            locations=frozenset({"harbor", "tower"}),
            reachable_locations=frozenset({"harbor"}),
            object_locations={},
            inventory=frozenset(),
            facts=frozenset(),
            action_policies={"signal": policy},
            npc_knowledge={"captain": frozenset({"secret"})},
            **state_kwargs,
        )
        candidate = CandidateAction(
            action_id=case_id, actor_id="captain", action_type="signal", **candidate_kwargs
        )
        return state, candidate

    base = {"preconditions": frozenset(), "effects": frozenset({"signal_restored"})}
    scenarios = [
        (held("held_valid_goal", base), True, True),
        (
            held("held_valid_no_goal", {"preconditions": frozenset(), "effects": frozenset()}),
            True,
            False,
        ),
        (
            held("held_unknown_knowledge", {**base, "used_facts": frozenset({"unknown"})}),
            False,
            False,
        ),
        (
            held("held_unreachable_object", {**base, "required_objects": frozenset({"key"})}),
            False,
            False,
        ),
        (held("held_future_stage", {**base, "required_quest_stage": 1}), False, False),
        (held("held_allowed_stage", {**base, "quest_stage_effect": 1}), True, True),
    ]
    return dev + [
        ("held_out", state, candidate, valid, goal) for (state, candidate), valid, goal in scenarios
    ]


def run_case(split, state, candidate, expected_valid=None, expected_objective=None):
    """Compare controllers; missing expectations remain unknown, never inferred."""
    initial = to_jsonable(state)
    proposal = to_jsonable(candidate)
    conditions = {}
    for name in ("generic_rules", "trace_gate"):
        try:
            if name == "generic_rules":
                accepted = generic_accepts(state, candidate)
                # Simulation only: no external game engine or model is invoked.
                final = (
                    replace(
                        state,
                        facts=state.facts | candidate.effects,
                        quest_stage=state.quest_stage
                        if candidate.quest_stage_effect is None
                        else candidate.quest_stage_effect,
                    )
                    if accepted
                    else state
                )
                trace = None
            else:
                outcome = execute_with_repair(state, candidate, repair_budget=0)
                if outcome.status not in ("commit", "fallback"):
                    raise ValueError(f"unexpected outcome: {outcome.status}")
                accepted = outcome.status == "commit"
                final = outcome.state
                trace = {"trace": to_jsonable(outcome.trace), "trace_hash": outcome.trace_hash}
            objective = accepted and "signal_restored" in final.facts
            conditions[name] = {
                "status": "COMPLETED",
                "input_state": initial,
                "input_proposal": proposal,
                "accepted": accepted,
                "objective_reached": objective,
                "safety_violation": None
                if expected_valid is None
                else accepted and not expected_valid,
                "false_refusal": None
                if expected_valid is None
                else not accepted and expected_valid,
                "objective_matches_expectation": None
                if expected_objective is None
                else objective == expected_objective,
                "final_facts": sorted(final.facts),
                "final_quest_stage": final.quest_stage,
                "trace_evidence": trace,
            }
        except Exception as exc:  # noqa: BLE001 - Keep every condition failure in the assigned denominator.
            conditions[name] = {
                "status": "FAILED",
                "input_state": initial,
                "input_proposal": proposal,
                "accepted": None,
                "objective_reached": None,
                "safety_violation": None,
                "false_refusal": None,
                "objective_matches_expectation": None,
                "error": {"type": type(exc).__name__, "message": str(exc)},
            }
    return {
        "split": split,
        "case_id": state.state_id,
        "expectation": {
            "valid": expected_valid,
            "objective": expected_objective,
            "source": "caller-supplied; built-in case judgments authored by scenario designer, not independently validated"
            if expected_valid is not None or expected_objective is not None
            else None,
        },
        "conditions": conditions,
    }


def summarize(rows):
    summary = {}
    for split in ("development", "held_out"):
        group = [row for row in rows if row["split"] == split]
        summary[split] = {}
        for name in ("generic_rules", "trace_gate"):
            results = [row["conditions"][name] for row in group]
            summary[split][name] = {
                "assigned": len(results),
                "completed": sum(r["status"] == "COMPLETED" for r in results),
                "failed": sum(r["status"] == "FAILED" for r in results),
                "safety_violations": sum(r["safety_violation"] is True for r in results),
                "safety_unknown": sum(r["safety_violation"] is None for r in results),
                "false_refusals": sum(r["false_refusal"] is True for r in results),
                "false_refusal_unknown": sum(r["false_refusal"] is None for r in results),
                "objective_reached": sum(r["objective_reached"] is True for r in results),
                "objective_unknown": sum(r["objective_reached"] is None for r in results),
                "objective_mismatches": sum(
                    r["objective_matches_expectation"] is False for r in results
                ),
                "objective_expectation_unknown": sum(
                    r["objective_matches_expectation"] is None for r in results
                ),
            }
    return summary


def main():
    rows = [run_case(*case) for case in fixtures()]
    paths = [
        Path(__file__),
        ROOT / "scripts/run_local_signal_comparison.py",
        ROOT / "scripts/review_reference.py",
        ROOT / "src/nesy_game/runtime.py",
        ROOT / "src/nesy_game/validator.py",
        ROOT / "src/nesy_game/contracts.py",
    ]
    print(
        json.dumps(
            {
                "scope": "Synthetic fixed-input offline comparison; not model, player, or real-world performance.",
                "oracle": "Scenario designer authored case-specific expected decisions from the encoded game rules; no independent human annotation or verification. Objective is committed final state containing signal_restored.",
                "comparison": "Both controllers receive identical complete state and proposal, with zero repairs; generic_rules separately implements the encoded constraints and simulates the state transition.",
                "limitations": "Held-out means separate from existing development fixtures, not independently sourced or blinded; the same designer authored cases, judgments, and comparator. Cases are too few for generalization or causal claims.",
                "reproducibility": {
                    "python": platform.python_version(),
                    "model_calls": 0,
                    "repair_budget": 0,
                    "source_sha256": {
                        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in paths
                    },
                },
                "cases": rows,
                "summary": summarize(rows),
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
