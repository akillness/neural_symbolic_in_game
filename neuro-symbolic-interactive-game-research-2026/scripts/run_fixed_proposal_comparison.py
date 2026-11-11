#!/usr/bin/env python3
"""Offline fixed-proposal controller demonstration; no model or oracle calls.

Run from the project root: python3 scripts/run_fixed_proposal_comparison.py
The existing synthetic fixtures are not held-out game cases. This is not a
player-performance study or an independently adjudicated safety evaluation.
"""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from run_local_signal_comparison import fixtures

from nesy_game.runtime import execute_with_repair, to_jsonable


def run_case(state, candidate):
    initial = to_jsonable(state)
    proposal = to_jsonable(candidate)
    conditions = {
        "proposal_only": {
            "status": "COMPLETED",
            "outcome": "not_executed",
            "final_state": initial,
            "objective_reached": None,
        },
        "generic_rules": {
            "status": "NOT_IMPLEMENTED",
            "outcome": None,
            "final_state": None,
            "objective_reached": None,
            "reason": "No independently implemented checker of the same rules is established.",
        },
    }
    try:
        outcome = execute_with_repair(state, candidate, repair_budget=0)
        conditions["trace_gate"] = {
            "status": "COMPLETED",
            "outcome": outcome.status,
            "final_state": to_jsonable(outcome.state),
            "validation": to_jsonable(outcome.validation),
            "trace": to_jsonable(outcome.trace),
            "trace_hash": outcome.trace_hash,
            "objective_reached": None,
        }
    except Exception as exc:  # noqa: BLE001 - Keep every condition failure in the assigned denominator.
        conditions["trace_gate"] = {
            "status": "FAILED",
            "outcome": None,
            "final_state": None,
            "objective_reached": None,
            "error": {"type": type(exc).__name__, "message": str(exc)},
        }
    return {
        "case_id": state.state_id,
        "initial_state": initial,
        "shared_proposal": proposal,
        "oracle_status": "NOT_AVAILABLE",
        "conditions": conditions,
    }


def summarize(rows):
    conditions = {}
    for name in ("proposal_only", "generic_rules", "trace_gate"):
        counts = {
            "assigned": len(rows),
            "completed": 0,
            "failed": 0,
            "not_implemented": 0,
            "missing": 0,
        }
        for row in rows:
            result = row.get("conditions", {}).get(name)
            status = result.get("status") if result else None
            key = {
                "COMPLETED": "completed",
                "FAILED": "failed",
                "NOT_IMPLEMENTED": "not_implemented",
            }.get(status, "missing")
            counts[key] += 1
        conditions[name] = counts
    return {
        "conditions": conditions,
        "oracle": {"assigned": len(rows), "adjudicated": 0, "missing": len(rows)},
    }


def main():
    rows = [run_case(state, candidate) for state, candidate in fixtures()]
    paths = [
        Path(__file__),
        ROOT / "scripts/run_local_signal_comparison.py",
        ROOT / "src/nesy_game/runtime.py",
        ROOT / "src/nesy_game/validator.py",
        ROOT / "src/nesy_game/contracts.py",
    ]
    print(
        json.dumps(
            {
                "scope": "synthetic offline controller demonstration, not held-out games or model performance",
                "oracle_note": "No independent human annotation or independent specification is established; same-scenario engineering oracle candidates are not ground truth.",
                "reproducibility": {
                    "python": platform.python_version(),
                    "repair_budget": 0,
                    "model_calls": 0,
                    "source_sha256": {
                        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in paths
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
