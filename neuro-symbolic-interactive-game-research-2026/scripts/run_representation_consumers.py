#!/usr/bin/env python3
"""Offline mechanical comparison of two lossless feedback representations.

These deterministic, state-blind consumers are synthetic programs, not models or
people. Their parser and repair rules are co-designed with the cases; this is not
an estimate of representation effects on an independent population.
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

from run_fixed_oracle_comparison import fixtures

from nesy_game.runtime import execute_with_repair, to_jsonable
from nesy_game.validator import validate_candidate


def checked_jsonable(value):
    data = to_jsonable(value)
    json.dumps(data, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    return data


def encode_signals(validation):
    data = checked_jsonable(validation)
    # Each text line is independently parseable; JSON quoting preserves arbitrary
    # field values, including newlines and delimiters within error messages.
    lines = [
        "valid " + json.dumps(data["valid"]),
        "checks " + json.dumps(data["checks_run"], ensure_ascii=False),
    ]
    lines.extend(
        "error " + json.dumps(error, ensure_ascii=False, sort_keys=True) for error in data["errors"]
    )
    return {"structured": data, "text": "\n".join(lines)}


def _text_records(signal):
    if not isinstance(signal, str):
        raise ValueError("text signal must be a string")  # noqa: TRY004 - Preserve malformed-signal ValueError contract.
    records = []
    for line in signal.split("\n"):
        tag, separator, value = line.partition(" ")
        if not separator or tag not in ("valid", "checks", "error"):
            raise ValueError("invalid text record")
        records.append((tag, json.loads(value)))
    return records


def information(name, signal):
    """Recover the full payload for an independent equality check, not repair."""
    if name == "structured":
        data = signal
    elif name == "text":
        records = _text_records(signal)
        if (
            len(records) < 2
            or records[0][0] != "valid"
            or records[1][0] != "checks"
            or any(tag != "error" for tag, _ in records[2:])
        ):
            raise ValueError("invalid text record order")
        data = {
            "valid": records[0][1],
            "checks_run": records[1][1],
            "errors": [value for _, value in records[2:]],
        }
    else:
        raise ValueError("unknown representation")
    if not isinstance(data, dict) or set(data) != {"valid", "checks_run", "errors"}:
        raise ValueError("invalid feedback fields")
    if (
        type(data["valid"]) is not bool
        or not isinstance(data["checks_run"], list)
        or not all(isinstance(x, str) for x in data["checks_run"])
    ):
        raise ValueError("invalid feedback metadata")
    if not isinstance(data["errors"], list) or any(
        not isinstance(e, dict)
        or set(e) != {"code", "reason", "entity", "repair_hint"}
        or not all(isinstance(v, str) for v in e.values())
        for e in data["errors"]
    ):
        raise ValueError("invalid feedback errors")
    return data


def consume(name, signal, candidate):
    """Read each representation directly and apply a bounded synthetic rule set."""
    if name == "structured":
        errors = signal["errors"]
    elif name == "text":
        errors = (record for tag, record in _text_records(signal) if tag == "error")
    else:
        raise ValueError("unknown representation")
    pre_add, pre_drop, effect_add, effect_drop = set(), set(), set(), set()
    stage_drop = False
    for error in errors:
        code, entity = error["code"], error["entity"]
        if code == "POLICY_PRECONDITION_OMISSION":
            pre_add.add(entity)
        elif code == "UNSATISFIED_PRECONDITION":
            pre_drop.add(entity)
        elif code == "POLICY_EFFECT_OMISSION":
            effect_add.add(entity)
        elif code == "POLICY_EFFECT_VIOLATION":
            effect_drop.add(entity)
        elif code == "POLICY_QUEST_STAGE_EFFECT_VIOLATION":
            stage_drop = True
    pre_conflict, effect_conflict = pre_add & pre_drop, effect_add & effect_drop
    return replace(
        candidate,
        preconditions=(candidate.preconditions - (pre_drop - pre_conflict))
        | (pre_add - pre_conflict),
        effects=(candidate.effects - (effect_drop - effect_conflict))
        | (effect_add - effect_conflict),
        quest_stage_effect=None if stage_drop else candidate.quest_stage_effect,
    )


def run_case(split, state, candidate, expected_valid=None, expected_objective=None):
    setup_error = None
    signals = {"structured": None, "text": None}
    expected = None
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
        signals = encode_signals(validation)
        expected = checked_jsonable(validation)
        if set(signals) != {"structured", "text"}:
            raise ValueError("feedback representations missing or unexpected")
        checked_jsonable(signals)
    except Exception as exc:  # noqa: BLE001 - Preserve setup failures for sanitized per-condition accounting.
        setup_error = exc
        signals = {"structured": None, "text": None}
    conditions = {}
    for name in ("structured", "text"):
        signal = signals.get(name)
        calls = []
        information_equal = None
        try:
            if setup_error is not None:
                raise setup_error
            information_equal = information(name, signal) == expected
            if not information_equal:
                raise ValueError("representation does not preserve complete feedback")

            def repair(_state, proposal, actual, attempt, *, name=name, signal=signal, calls=calls):
                if actual != validation or attempt != 1:
                    raise ValueError("unexpected feedback or repair attempt")
                call = {
                    "attempt": attempt,
                    "input": signal,
                    "candidate_before": checked_jsonable(proposal),
                    "candidate_after": None,
                }
                calls.append(call)
                result = consume(name, signal, proposal)
                call["candidate_after"] = checked_jsonable(result)
                return result

            outcome = execute_with_repair(state, candidate, repairer=repair, repair_budget=1)
            if outcome.status not in ("commit", "fallback"):
                raise ValueError("unexpected runtime outcome")
            conditions[name] = {
                "status": "COMPLETED",
                "signal": signal,
                "information_equal": True,
                "consumer_calls": calls,
                "outcome": outcome.status,
                "final_candidate": checked_jsonable(outcome.candidate),
                "final_state": checked_jsonable(outcome.state),
                "trace": checked_jsonable(outcome.trace),
                "objective_reached": outcome.status == "commit"
                and "signal_restored" in outcome.state.facts,
                "safety_violation": None,
                "false_refusal": None,
            }
        except Exception as exc:  # noqa: BLE001 - Keep sanitized failures in the assigned denominator.
            conditions[name] = {
                "status": "FAILED",
                "signal": signal,
                "information_equal": information_equal,
                "consumer_calls": calls,
                "outcome": None,
                "final_candidate": None,
                "final_state": None,
                "trace": None,
                "objective_reached": None,
                "safety_violation": None,
                "false_refusal": None,
                "error": {"type": type(exc).__name__, "message": "condition failed"},
            }
    return {
        "split": split,
        "case_id": case_id,
        "input_state": input_state,
        "input_proposal": input_proposal,
        "original_feedback": expected,
        "conditions": conditions,
    }


def summarize(rows):
    result = {}
    for split in ("development", "held_out"):
        result[split] = {}
        for name in ("structured", "text"):
            items = [row["conditions"][name] for row in rows if row["split"] == split]
            result[split][name] = {
                "assigned": len(items),
                "completed": sum(x["status"] == "COMPLETED" for x in items),
                "failed": sum(x["status"] == "FAILED" for x in items),
                "consumer_called": sum(bool(x["consumer_calls"]) for x in items),
                "committed": sum(x["outcome"] == "commit" for x in items),
                "fallback": sum(x["outcome"] == "fallback" for x in items),
                "objective_reached": sum(x["objective_reached"] is True for x in items),
                "objective_unknown": sum(x["objective_reached"] is None for x in items),
                "safety_unknown": sum(x["safety_violation"] is None for x in items),
                "false_refusal_unknown": sum(x["false_refusal"] is None for x in items),
            }
    return result


def main():
    rows = [run_case(*case) for case in fixtures()]
    paths = [
        Path(__file__),
        ROOT / "scripts/run_fixed_oracle_comparison.py",
        ROOT / "scripts/run_local_signal_comparison.py",
        ROOT / "src/nesy_game/runtime.py",
        ROOT / "src/nesy_game/validator.py",
        ROOT / "src/nesy_game/contracts.py",
    ]
    print(
        json.dumps(
            {
                "scope": "Synthetic deterministic state-blind consumers; offline mechanical diagnostic, not model performance.",
                "comparison": "Structured mapping versus tagged JSON text records; complete decoded feedback is checked equal before each condition. The repair callback directly parses the assigned signal. Both receive the same candidate and at most one repair; valid initial candidates require no consumer call. Semantic information and repair budget are equal, not bytes or token cost.",
                "limitations": "No independent participants, model calls, causal or generalization claims. Consumers, fixtures, and held-out cases are co-designed and cases are not independent. Gate acceptance is not independent safety adjudication of the final candidate; safety and false refusal remain unknown. This mechanical diagnostic cannot establish representation effects on models or humans.",
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
