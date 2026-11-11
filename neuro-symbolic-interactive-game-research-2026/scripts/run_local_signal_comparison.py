#!/usr/bin/env python3
"""Local synthetic signal comparison; not evidence of LLM or player performance.

Run from the project root: python3 scripts/run_local_signal_comparison.py
No network, model, subscription, or historical result is accessed. The independent
objective is a predeclared final-state predicate, not validator acceptance. The
synthetic cases illustrate mechanisms, not estimates of real-world effectiveness.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.contracts import ActionPolicy, CandidateAction, WorldState
from nesy_game.repair import counterexample_guided_repair
from nesy_game.runtime import execute_with_repair, to_jsonable
from nesy_game.validator import validate_candidate


class NoState:
    """Fail if the deterministic repair operator tries to inspect world state."""

    def __getattribute__(self, name):
        raise AssertionError(f"repair tried to read world state: {name}")


def case(case_id, policy, candidate, facts=(), forbidden=()):
    state = WorldState(
        state_id=case_id,
        locations=frozenset({"harbor"}),
        reachable_locations=frozenset({"harbor"}),
        object_locations={},
        inventory=frozenset(),
        facts=frozenset(facts),
        action_policies={"signal": policy},
        npc_knowledge={"captain": frozenset({"secret"})},
        forbidden_disclosures={"captain": frozenset(forbidden)},
    )
    action = CandidateAction(
        action_id=case_id, actor_id="captain", action_type="signal", **candidate
    )
    return state, action


def fixtures():
    allowed = frozenset({"signal_restored"})
    return [
        case(
            "missing_precondition",
            ActionPolicy(frozenset({"authorized"}), allowed),
            {"preconditions": frozenset(), "effects": allowed},
            facts={"authorized"},
        ),
        case(
            "missing_effect",
            ActionPolicy(frozenset(), allowed, required_effects=allowed),
            {"preconditions": frozenset(), "effects": frozenset()},
        ),
        case(
            "unauthorized_objective",
            ActionPolicy(frozenset(), frozenset()),
            {"preconditions": frozenset(), "effects": allowed},
        ),
        case(
            "forbidden_disclosure",
            ActionPolicy(frozenset(), allowed),
            {
                "preconditions": frozenset(),
                "effects": allowed,
                "disclosed_facts": frozenset({"secret"}),
            },
            forbidden={"secret"},
        ),
        case(
            "unsatisfied_dependency",
            ActionPolicy(frozenset(), allowed),
            {"preconditions": frozenset({"permission"}), "effects": allowed},
        ),
    ]


def run_case(state, candidate):
    initial = validate_candidate(state, candidate)
    if initial.valid:
        raise ValueError(f"fixture {state.state_id} must begin with a rejected proposal")

    # The repair callback is deliberately never given the actual state. The runtime
    # independently owns state, validation and commit.
    def repair_without_state(_state, proposal, errors, attempt):
        return counterexample_guided_repair(NoState(), proposal, errors, attempt)

    outcome = execute_with_repair(state, candidate, repair_without_state, repair_budget=1)
    final_validation = validate_candidate(state, outcome.candidate)
    objective = outcome.status == "commit" and "signal_restored" in outcome.state.facts
    detailed = to_jsonable(initial)
    proposal = to_jsonable(candidate)
    return {
        "case_id": state.state_id,
        "shared_proposal": proposal,
        "detailed_signal": detailed,
        "generic_signal": {"valid": False, "message": "Action rejected."},
        "independent_objective": "committed final state contains signal_restored",
        "conditions": {
            "deterministic_detailed": {
                "status": "COMPLETED",
                "input_proposal": proposal,
                "input_signal": detailed,
                "outcome": outcome.status,
                "trace": to_jsonable(outcome.trace),
                "repair_attempts": outcome.attempts,
                "final_validation": to_jsonable(outcome.validation),
                "final_gate_accepted": final_validation.valid,
                "objective_reached": objective,
                "final_candidate": to_jsonable(outcome.candidate),
                "final_facts": sorted(outcome.state.facts),
            },
            "llm_detailed": {
                "status": "NOT_RUN",
                "input_proposal": proposal,
                "input_signal": detailed,
                "outcome": None,
                "final_gate_accepted": None,
                "objective_reached": None,
            },
            "llm_generic": {
                "status": "NOT_RUN",
                "input_proposal": proposal,
                "input_signal": {"valid": False, "message": "Action rejected."},
                "outcome": None,
                "final_gate_accepted": None,
                "objective_reached": None,
            },
        },
    }


def main():
    rows = [run_case(state, candidate) for state, candidate in fixtures()]
    results = [row["conditions"]["deterministic_detailed"] for row in rows]
    print(
        json.dumps(
            {
                "scope": "synthetic local demonstration only; no LLM comparison or population inference",
                "llm_blocker": "No provider-side credit blocking, response-bound model identity, isolation, public-input and per-row authorization evidence established; no calls made.",
                "cases": rows,
                "deterministic_summary": {
                    "n": len(rows),
                    "gate_accepted": sum(r["final_gate_accepted"] for r in results),
                    "objective_reached": sum(r["objective_reached"] for r in results),
                },
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
