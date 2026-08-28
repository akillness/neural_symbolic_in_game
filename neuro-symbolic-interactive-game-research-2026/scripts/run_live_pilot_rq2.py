#!/usr/bin/env python3
"""RQ2 live pilot: guided repair rho vs blind unchanged retry on live proposals (D-040).

Design (frozen in `research/directions/rq2-live-pilot-plan.md`):

* One live proposal per seed. Both repair arms then consume the **same** candidate,
  so the arms differ by repair strategy only and not by model sampling noise.
* Matched budget `K=1` for both arms, mirroring the frozen offline battery.
* The deterministic validator remains the sole authority; a fallback leaves the
  prior state hash unchanged.

Claim boundary: screening-tier evidence. Hosted model revisions drift, token
accounting is unavailable through the CLI wrapper, and the sample is tiny. Results
may support `C-RESULT-003` at `pilot-only` and never at `verified-empirical`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game import (
    ActionPolicy,
    AdapterFailure,
    WorldState,
    counterexample_guided_repair,
    execute_with_repair,
    to_jsonable,
    validate_candidate,
)
from nesy_game.codex_adapter import CodexProposalAdapter

PILOT_ID = "SL-RQ2-LIVE-001"
DEFAULT_MANIFEST = ROOT / "configs/pilot-manifest.json"
DEFAULT_STATES = ROOT / "configs/live-pilot-states.json"
DEFAULT_OUTPUT = ROOT / "runs/live-pilot-rq2"
DEFAULT_SCENARIO = ROOT / "game-track/godot/data/sealed_lighthouse.json"
DEFAULT_SEEDS = (11, 23, 47, 83, 131)
REPAIR_BUDGET = 1
ARMS = ("unchanged_retry", "guided_repair")


def _unchanged_repair(state: WorldState, candidate: Any, validation: Any, attempt: int) -> Any:
    """Blind retry: resubmit the identical candidate, reading nothing."""

    del state, validation, attempt
    return candidate


REPAIRERS = {
    "unchanged_retry": _unchanged_repair,
    "guided_repair": counterexample_guided_repair,
}


def _canonical_hash(payload: Any) -> str:
    canonical = json.dumps(
        to_jsonable(payload), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_base_state(
    state_key: str, *, manifest_path: Path, states_path: Path
) -> tuple[WorldState, str]:
    """Resolve one pre-registered base state and return it with its state id.

    ``frozen-pilot-base`` always reads the immutable offline packet, so the frozen
    manifest stays the single source for that state and cannot drift into a copy.
    """

    if state_key == "frozen-pilot-base":
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return world_state_from_manifest(manifest["base_state"]), "frozen-pilot-base"
    catalog = json.loads(states_path.read_text(encoding="utf-8"))
    entry = catalog["states"].get(state_key)
    if entry is None or "action_policies" not in entry:
        raise SystemExit(f"unknown or non-executable base state: {state_key}")
    return world_state_from_manifest(entry), str(entry["state_id"])


def world_state_from_manifest(data: Mapping[str, Any]) -> WorldState:
    policies = {
        action_type: ActionPolicy(
            frozenset(policy["required_preconditions"]),
            frozenset(policy["allowed_effects"]),
            frozenset(policy.get("required_effects", [])),
            frozenset(policy.get("allowed_quest_stage_effects", [])),
        )
        for action_type, policy in data["action_policies"].items()
    }
    return WorldState(
        state_id=data["state_id"],
        locations=frozenset(data["locations"]),
        reachable_locations=frozenset(data["reachable_locations"]),
        object_locations=data["object_locations"],
        inventory=frozenset(data["inventory"]),
        facts=frozenset(data["facts"]),
        action_policies=policies,
        npc_knowledge={key: frozenset(value) for key, value in data["npc_knowledge"].items()},
        forbidden_disclosures={
            key: frozenset(value) for key, value in data["forbidden_disclosures"].items()
        },
        quest_stage=data["quest_stage"],
    )


def _error_codes(validation: Any) -> list[str]:
    return sorted({error.code for error in validation.errors})


def run_seed(
    adapter: Any,
    state: WorldState,
    *,
    scenario_id: str,
    seed: int,
) -> dict[str, Any]:
    """One live proposal, then both repair arms over that identical candidate."""

    prior_hash = _canonical_hash(state)
    row: dict[str, Any] = {
        "seed": seed,
        "scenario_id": scenario_id,
        "prior_state_sha256": prior_hash,
        "model_id": adapter.model_id,
        "model_revision": adapter.model_revision,
        "condition": getattr(adapter, "condition", "policy_visible"),
    }
    try:
        response = adapter.propose(state, scenario_id, seed)
    except AdapterFailure as failure:
        row["status"] = "adapter_failure"
        row["failure_code"] = failure.code
        row["arms"] = {}
        return row

    candidate = response.candidate
    initial = validate_candidate(state, candidate)
    row["status"] = "proposed"
    row["provider_latency_ms"] = round(response.provider_latency_ms, 3)
    row["proposal_sha256"] = _canonical_hash(candidate)
    row["initial_valid"] = bool(initial.valid)
    row["initial_error_codes"] = _error_codes(initial)
    row["candidate_action_type"] = candidate.action_type

    arms: dict[str, Any] = {}
    for arm_id in ARMS:
        outcome = execute_with_repair(
            state,
            candidate,
            REPAIRERS[arm_id],
            REPAIR_BUDGET,
            {"arm_id": arm_id, "scenario_id": scenario_id, "seed": seed},
        )
        final_hash = _canonical_hash(outcome.state)
        arms[arm_id] = {
            "status": outcome.status,
            "attempts": outcome.attempts,
            "final_state_sha256": final_hash,
            "state_unchanged": final_hash == prior_hash,
            "final_error_codes": _error_codes(outcome.trace[-1].validation),
        }
        if outcome.status == "fallback" and final_hash != prior_hash:
            raise AssertionError(f"fallback mutated state for arm {arm_id} at seed {seed}")
    row["arms"] = arms
    return row


def summarize(
    rows: Sequence[Mapping[str, Any]],
    *,
    model_id: str,
    revision: str,
    condition: str = "policy_visible",
) -> dict[str, Any]:
    proposed = [row for row in rows if row["status"] == "proposed"]
    invalid = [row for row in proposed if not row["initial_valid"]]
    per_arm: dict[str, Any] = {}
    for arm_id in ARMS:
        commits = sum(1 for row in proposed if row["arms"][arm_id]["status"] == "commit")
        invalid_commits = sum(1 for row in invalid if row["arms"][arm_id]["status"] == "commit")
        isolated = sum(
            1
            for row in proposed
            if row["arms"][arm_id]["status"] != "commit" and row["arms"][arm_id]["state_unchanged"]
        )
        non_commits = sum(1 for row in proposed if row["arms"][arm_id]["status"] != "commit")
        per_arm[arm_id] = {
            "commits": commits,
            "cases": len(proposed),
            "commits_among_initially_invalid": invalid_commits,
            "initially_invalid_cases": len(invalid),
            "non_commit_state_isolated": isolated,
            "non_commits": non_commits,
        }
    observed_codes = sorted({code for row in invalid for code in row["initial_error_codes"]})
    return {
        "schema_version": "1.0.0",
        "pilot_id": PILOT_ID,
        "evidence_tier": "screening-pilot-only",
        "claim_boundary": (
            "Live-proposer screening pilot on a single frozen base state with a tiny seed "
            "grid. Supports C-RESULT-003 only at pilot-only. Not a population effect, not a "
            "promoted-model result, and not statistical evidence."
        ),
        "not_evidence_for": [
            "verified-empirical promotion",
            "population efficacy",
            "model ranking",
            "human experience",
        ],
        "model_id": model_id,
        "model_revision": revision,
        "condition": condition,
        "condition_note": (
            "policy_visible hands the model the full precondition/effect table; "
            "policy_blind withholds it and lists action-type names only."
        ),
        "repair_budget": REPAIR_BUDGET,
        "arms": list(ARMS),
        "matched_candidate_per_seed": True,
        "token_accounting_available": False,
        "counts": {
            "seeds": len(rows),
            "proposals_returned": len(proposed),
            "adapter_failures": len(rows) - len(proposed),
            "initially_valid": len(proposed) - len(invalid),
            "initially_invalid": len(invalid),
        },
        "per_arm": per_arm,
        "observed_initial_error_codes": observed_codes,
    }


def write_outputs(
    output_dir: Path, rows: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.jsonl"
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    results_path.write_text(body, encoding="utf-8")
    summary_path = output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "pilot_id": PILOT_ID,
        "files": {
            path.name: {
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in (results_path, summary_path)
        },
    }
    (output_dir / "sha256-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, help="Hosted model id passed to the Codex CLI")
    parser.add_argument(
        "--model-revision",
        required=True,
        help="Exact hosted revision string recorded in every row (no inference)",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--states", type=Path, default=DEFAULT_STATES)
    parser.add_argument(
        "--state",
        default="frozen-pilot-base",
        help="Pre-registered base state key from configs/live-pilot-states.json",
    )
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--condition",
        choices=("policy_visible", "policy_blind", "goal_directed_blind"),
        default="policy_visible",
        help="Difficulty condition; policy_blind withholds the constraint table.",
    )
    parser.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        default=list(DEFAULT_SEEDS),
        help="Frozen seed grid; changing it changes the design and must be recorded",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    state, state_label = load_base_state(
        args.state, manifest_path=args.manifest, states_path=args.states
    )
    scenario_id = str(scenario.get("scenario_id", "sealed-lighthouse-v1"))

    adapter = CodexProposalAdapter(
        model_id=args.model,
        model_revision=args.model_revision,
        scenario=scenario,
        run_label=f"rq2-{args.condition}",
        timeout=args.timeout,
        condition=args.condition,
    )
    output_dir = args.output or (DEFAULT_OUTPUT / args.state / args.condition)
    rows = [
        run_seed(adapter, state, scenario_id=scenario_id, seed=seed) for seed in sorted(args.seeds)
    ]
    summary = summarize(
        rows, model_id=args.model, revision=args.model_revision, condition=args.condition
    )
    summary["base_state"] = args.state
    summary["base_state_id"] = state_label
    write_outputs(output_dir, rows, summary)
    counts = summary["counts"]
    guided = summary["per_arm"]["guided_repair"]
    blind = summary["per_arm"]["unchanged_retry"]
    print(
        f"{PILOT_ID} [{args.state}/{args.condition}]: seeds {counts['seeds']}, "
        f"proposals {counts['proposals_returned']}, "
        f"initially valid {counts['initially_valid']}, initially invalid {counts['initially_invalid']}; "
        f"guided commits {guided['commits']}/{guided['cases']} "
        f"(invalid-only {guided['commits_among_initially_invalid']}/{guided['initially_invalid_cases']}), "
        f"blind commits {blind['commits']}/{blind['cases']}; output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
