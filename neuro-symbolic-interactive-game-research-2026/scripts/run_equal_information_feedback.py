#!/usr/bin/env python3
"""Compare two lossless feedback encodings with a fixed offline repair operator.

The generic headline alone has less information than detailed feedback. This
control therefore includes the entire detailed payload in a JSON text field.
The study exercises format transport, not generic-only feedback or model behavior.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_fixed_oracle_comparison import fixtures
from run_local_signal_comparison import NoState
from run_representation_consumers import checked_jsonable

from nesy_game.contracts import ValidationError, ValidationResult
from nesy_game.repair import counterexample_guided_repair
from nesy_game.runtime import execute_with_repair, to_jsonable
from nesy_game.validator import validate_candidate


def encode_feedback(validation):
    detailed = to_jsonable(validation)
    return {
        "detailed": detailed,
        "generic_with_details": {
            "message": "Action accepted." if validation.valid else "Action rejected.",
            "details_json": json.dumps(
                detailed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ),
        },
    }


def decode_feedback(name, signal):
    data = signal if name == "detailed" else json.loads(signal["details_json"])
    return ValidationResult(
        data["valid"],
        tuple(ValidationError(**error) for error in data["errors"]),
        tuple(data["checks_run"]),
    )


def run_case(split, state, candidate, expected_valid=None, expected_objective=None):
    """Run the same state-blind repair and fail-closed gate for both encodings."""
    setup_error = None
    signals = {"detailed": None, "generic_with_details": None}
    input_state = input_proposal = case_id = None
    try:
        case_id = checked_jsonable(state.state_id)
    except Exception as exc:  # noqa: BLE001 - Preserve setup failures for sanitized per-condition accounting.
        setup_error = exc
    try:
        input_state = checked_jsonable(state)
    except Exception as exc:  # noqa: BLE001 - Preserve setup failures for sanitized per-condition accounting.
        if setup_error is None:
            setup_error = exc
    try:
        input_proposal = checked_jsonable(candidate)
    except Exception as exc:  # noqa: BLE001 - Preserve setup failures for sanitized per-condition accounting.
        if setup_error is None:
            setup_error = exc
    try:
        if setup_error is not None:
            raise setup_error
        validation = validate_candidate(state, candidate)
        signals = encode_feedback(validation)
        if not isinstance(signals, dict) or set(signals) != {"detailed", "generic_with_details"}:
            raise ValueError("feedback encodings missing or unexpected")
        signals = checked_jsonable(signals)
    except Exception as exc:  # noqa: BLE001 - Preserve setup failures for sanitized per-condition accounting.
        setup_error = exc
        signals = {"detailed": None, "generic_with_details": None}
    conditions = {}
    for name in ("detailed", "generic_with_details"):
        signal = signals[name]
        try:
            if setup_error is not None:
                raise setup_error
            decoded = decode_feedback(name, signal)
            if decoded != validation:
                raise ValueError("feedback encoding lost or changed information")

            def repair(_state, proposal, actual, attempt, *, decoded=decoded):
                if actual != validation:
                    raise ValueError("runtime feedback differs from the fixed feedback")
                return counterexample_guided_repair(NoState(), proposal, decoded, attempt)

            outcome = execute_with_repair(state, candidate, repairer=repair, repair_budget=1)
            if outcome.status not in ("commit", "fallback"):
                raise ValueError(f"unexpected outcome: {outcome.status}")
            conditions[name] = {
                "status": "COMPLETED",
                "input_state": input_state,
                "input_proposal": input_proposal,
                "signal": signal,
                "decoded_signal": checked_jsonable(decoded),
                "outcome": outcome.status,
                "final_candidate": checked_jsonable(outcome.candidate),
                "final_state": checked_jsonable(outcome.state),
                "trace": checked_jsonable(outcome.trace),
                "objective_reached": outcome.status == "commit"
                and "signal_restored" in outcome.state.facts,
                # Original-proposal labels do not adjudicate a repaired proposal.
                "safety_violation": None,
                "false_refusal": None,
            }
        except Exception as exc:  # noqa: BLE001 - Keep every condition failure in the assigned denominator.
            conditions[name] = {
                "status": "FAILED",
                "input_state": input_state,
                "input_proposal": input_proposal,
                "signal": signal,
                "decoded_signal": None,
                "outcome": None,
                "final_candidate": None,
                "final_state": None,
                "trace": None,
                "objective_reached": None,
                "safety_violation": None,
                "false_refusal": None,
                "error": {"type": type(exc).__name__, "message": "condition failed"},
            }
    return {"split": split, "case_id": case_id, "conditions": conditions}


def summarize(rows):
    summary = {}
    for split in ("development", "held_out"):
        group = [row for row in rows if row["split"] == split]
        summary[split] = {}
        for name in ("detailed", "generic_with_details"):
            results = [row["conditions"][name] for row in group]
            summary[split][name] = {
                "assigned": len(results),
                "completed": sum(r["status"] == "COMPLETED" for r in results),
                "failed": sum(r["status"] == "FAILED" for r in results),
                "committed": sum(r["outcome"] == "commit" for r in results),
                "fallback": sum(r["outcome"] == "fallback" for r in results),
                "objective_reached": sum(r["objective_reached"] is True for r in results),
                "objective_unknown": sum(r["objective_reached"] is None for r in results),
                "safety_unknown": sum(r["safety_violation"] is None for r in results),
                "false_refusal_unknown": sum(r["false_refusal"] is None for r in results),
            }
    return summary


def main():
    rows = [run_case(*case) for case in fixtures()]
    paths = [
        Path(__file__),
        ROOT / "scripts/run_fixed_oracle_comparison.py",
        ROOT / "scripts/run_local_signal_comparison.py",
        ROOT / "src/nesy_game/repair.py",
        ROOT / "src/nesy_game/runtime.py",
        ROOT / "src/nesy_game/validator.py",
        ROOT / "src/nesy_game/contracts.py",
    ]
    print(
        json.dumps(
            {
                "scope": "Fixed-input offline feedback encoding control, no model or human participant.",
                "comparison": "Structured validation vs generic headline plus the full structured validation serialized as JSON; both decode to exactly the same information before the same deterministic state-blind repair.",
                "limitations": "This does not test a generic-only message, model response, human interpretation, causal effects, or generalization. Held-out cases were authored alongside the comparator, not independently sourced or blinded. Gate acceptance is not independent safety adjudication of repaired proposals.",
                "reproducibility": {
                    "python": platform.python_version(),
                    "model_calls": 0,
                    "repair_budget": 1,
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
