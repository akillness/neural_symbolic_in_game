"""Run the deterministic TRACE-RPG conformance pilot from designed fixtures.

This pilot is an implementation-verification artifact. It intentionally emits raw
counts only and cannot support model-quality, player-experience, or causal claims.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game import (
    ActionPolicy,
    AdapterFailure,
    CandidateAction,
    ExperimentCase,
    ProposalResponse,
    RecordedProposalAdapter,
    WorldState,
    candidate_from_mapping,
    execute_with_repair,
    parse_candidate_record,
    replay_trace_jsonl,
    replay_trace_record,
    run_experiment_case,
    summarize_experiment,
    to_jsonable,
    validate_candidate,
    verify_trace_record,
    write_experiment_jsonl,
    write_trace_jsonl,
)

DEFAULT_MANIFEST = ROOT / "configs/pilot-manifest.json"
DEFAULT_OUTPUT = ROOT / "runs/conformance-pilot"
DEFAULT_RELEASE = ROOT / "research/academic-pipeline/stage-04-pilot"
# Every provenance section must declare whether its rows are executed fixture rows or
# aggregate summaries derived from them. The mapping is exhaustive by construction: `add`
# raises on an unregistered section, so a new aggregate section cannot silently be counted
# as executed and inflate the executed-case total.
ROW_CLASS_BY_SECTION: dict[str, str] = {
    "gate_conformance": "executed",
    "boundary_sentinels": "executed",
    "closed_boundary_regressions": "executed",
    "repair_arms": "executed",
    "integrity_faults": "executed",
    "integrity_boundaries": "executed",
    "adapter_accounting": "executed",
    "accounting_guards": "executed",
    "pilot_summary": "aggregate",
    "repair_arm_summary": "aggregate",
}
ROW_CLASSES = frozenset(ROW_CLASS_BY_SECTION.values())
PROVENANCE_COLUMNS = (
    "arm_id",
    "config_hash",
    "input_hash",
    "state_hash",
    "prior_state_hash",
)
NONE_REPAIRER_CODE_HASH = hashlib.sha256(b"none").hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_hash(payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _provenance(
    arm_id: str,
    config_payload: Any,
    input_payload: Any,
    state_payload: Any,
) -> dict[str, str]:
    """Return explicit deterministic provenance for one pilot result row."""

    state_hash = _canonical_hash(state_payload)
    return {
        "arm_id": arm_id,
        "config_hash": _canonical_hash(config_payload),
        "input_hash": _canonical_hash(input_payload),
        "state_hash": state_hash,
        "prior_state_hash": state_hash,
    }


def _clone(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _state_hash(state: WorldState) -> str:
    return _canonical_hash(to_jsonable(state))


def _rehash_trace(record: dict[str, Any]) -> None:
    payload = {key: value for key, value in record.items() if key != "trace_hash"}
    record["trace_hash"] = _canonical_hash(payload)


def _world_state(data: Mapping[str, Any]) -> WorldState:
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


def _unique_ids(items: Sequence[Mapping[str, Any]], section: str) -> None:
    identifiers = [item["id"] for item in items]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{section} contains duplicate fixture identifiers")


def _require_keys(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    missing = sorted(expected - value.keys())
    extra = sorted(value.keys() - expected)
    if missing or extra:
        raise ValueError(f"{field} fields mismatch: missing={missing}, extra={extra}")


def _validate_candidate_fixture(candidate: Mapping[str, Any], field: str) -> None:
    required = {"action_id", "actor_id", "action_type", "preconditions", "effects"}
    allowed = required | {
        "required_objects",
        "used_facts",
        "disclosed_facts",
        "required_quest_stage",
        "quest_stage_effect",
        "narrative_text",
        "metadata",
        "unexpected_top_level_metadata",
    }
    missing = sorted(required - candidate.keys())
    extra = sorted(candidate.keys() - allowed)
    if missing or extra:
        raise ValueError(f"{field} fields mismatch: missing={missing}, extra={extra}")


def _validate_manifest_structure(data: Mapping[str, Any]) -> None:
    _require_keys(
        data,
        {
            "schema_version",
            "pilot_id",
            "evidence_scope",
            "amendment",
            "implemented_validator_codes",
            "base_state",
            "gate_fixtures",
            "boundary_sentinels",
            "closed_boundary_regressions",
            "repair",
            "integrity_faults",
            "integrity_boundaries",
            "adapter_cases",
            "accounting_guards",
        },
        "pilot manifest",
    )
    _require_keys(
        data["amendment"],
        {"id", "artifact_status", "source_stage", "change"},
        "pilot manifest amendment",
    )
    if (
        data["amendment"]["id"] != "stage-08-candidate-contract-strictness"
        or data["amendment"]["artifact_status"] != "post-stage-08-rerun"
        or data["amendment"]["source_stage"] != "stage-04-pilot"
        or not data["amendment"]["change"]
    ):
        raise ValueError("pilot amendment provenance differs from the frozen Stage-8 rerun")
    _require_keys(
        data["base_state"],
        {
            "state_id",
            "locations",
            "reachable_locations",
            "object_locations",
            "inventory",
            "facts",
            "action_policies",
            "npc_knowledge",
            "forbidden_disclosures",
            "quest_stage",
        },
        "base_state",
    )
    for action_type, policy in data["base_state"]["action_policies"].items():
        _require_keys(
            policy,
            {
                "required_preconditions",
                "allowed_effects",
                "required_effects",
                "allowed_quest_stage_effects",
            },
            f"action_policies.{action_type}",
        )
    for fixture in data["gate_fixtures"]:
        _require_keys(fixture, {"id", "expected_codes", "candidate"}, fixture["id"])
        _validate_candidate_fixture(fixture["candidate"], f"{fixture['id']}.candidate")
    for fixture in data["boundary_sentinels"]:
        _require_keys(
            fixture,
            {"id", "boundary_type", "expected_valid", "interpretation", "candidate"},
            fixture["id"],
        )
        _validate_candidate_fixture(fixture["candidate"], f"{fixture['id']}.candidate")
    for fixture in data["closed_boundary_regressions"]:
        _require_keys(
            fixture,
            {
                "id",
                "boundary_type",
                "closed_in",
                "expected_rejected",
                "expected_failure_code",
                "interpretation",
                "candidate",
            },
            fixture["id"],
        )
        _validate_candidate_fixture(fixture["candidate"], f"{fixture['id']}.candidate")
        if fixture["expected_failure_code"] not in {"parse_error"}:
            raise ValueError(
                f"{fixture['id']} declares an unsupported expected_failure_code: "
                f"{fixture['expected_failure_code']}"
            )
    boundary_ids = [item["id"] for item in data["boundary_sentinels"]] + [
        item["id"] for item in data["closed_boundary_regressions"]
    ]
    if len(boundary_ids) != len(set(boundary_ids)):
        raise ValueError("boundary sentinel and regression IDs must be unique")
    _require_keys(data["repair"], {"arms", "cases"}, "repair")
    arm_ids = {arm["id"] for arm in data["repair"]["arms"]}
    for arm in data["repair"]["arms"]:
        _require_keys(arm, {"id", "repair_budget", "strategy"}, f"repair arm {arm['id']}")
    for case in data["repair"]["cases"]:
        _require_keys(
            case,
            {"id", "repairable", "expected_status", "candidate"},
            f"repair case {case['id']}",
        )
        _require_keys(case["expected_status"], arm_ids, f"{case['id']}.expected_status")
        _validate_candidate_fixture(case["candidate"], f"{case['id']}.candidate")
    for boundary in data["integrity_boundaries"]:
        _require_keys(
            boundary,
            {"id", "expected_detected", "interpretation"},
            f"integrity boundary {boundary['id']}",
        )
    adapter_base = {
        "id",
        "kind",
        "seed",
        "expected_status",
        "expected_failure_type",
    }
    recorded_extra = {
        "provider_latency_ms",
        "input_tokens",
        "output_tokens",
        "candidate",
    }
    for fixture in data["adapter_cases"]:
        expected = adapter_base | (recorded_extra if fixture["kind"] == "recorded" else set())
        _require_keys(fixture, expected, f"adapter case {fixture['id']}")
        if "candidate" in fixture:
            _validate_candidate_fixture(fixture["candidate"], f"{fixture['id']}.candidate")


def load_manifest(path: Path) -> dict[str, Any]:
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value
        return result

    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
    _validate_manifest_structure(data)
    if data.get("schema_version") != "1.0.0":
        raise ValueError("unsupported pilot manifest schema version")
    for section in (
        "gate_fixtures",
        "boundary_sentinels",
        "integrity_boundaries",
        "adapter_cases",
    ):
        _unique_ids(data[section], section)
    _unique_ids(data["repair"]["arms"], "repair arms")
    _unique_ids(data["repair"]["cases"], "repair cases")
    for name in ("integrity_faults", "accounting_guards"):
        values = data[name]
        if len(values) != len(set(values)):
            raise ValueError(f"{name} contains duplicate identifiers")
    if (
        len(data["integrity_boundaries"]) != 1
        or data["integrity_boundaries"][0]["id"] != "repair_transition_substitution"
        or data["integrity_boundaries"][0]["expected_detected"] is not False
        or not data["integrity_boundaries"][0]["interpretation"]
    ):
        raise ValueError("integrity boundary set differs from the frozen pilot design")

    implemented = set(data["implemented_validator_codes"])
    negative_codes = [
        code for fixture in data["gate_fixtures"] for code in fixture["expected_codes"]
    ]
    if set(negative_codes) != implemented or len(negative_codes) != len(implemented):
        raise ValueError("gate fixtures must isolate every implemented validator code exactly once")
    if sum(not fixture["expected_codes"] for fixture in data["gate_fixtures"]) != 1:
        raise ValueError("gate fixtures require exactly one valid control")
    # The candidate_contract_strictness boundary was closed in Stage 8: the proposal parser
    # now rejects unknown top-level fields, matching the replay parser. Only the two
    # genuinely open encoding boundaries remain documented as sentinels.
    if len(data["boundary_sentinels"]) != 2:
        raise ValueError("pilot requires exactly two explicit boundary sentinels")
    boundary_types = {item["boundary_type"] for item in data["boundary_sentinels"]}
    if boundary_types != {
        "semantic_extraction",
        "policy_completeness",
    }:
        raise ValueError("boundary sentinel coverage differs from the frozen manifest")
    if not all(item["expected_valid"] for item in data["boundary_sentinels"]):
        raise ValueError("boundary sentinels document encoded-gate acceptance")
    if len(data["closed_boundary_regressions"]) != 1:
        raise ValueError("pilot requires exactly one closed-boundary regression fixture")
    if not all(item["expected_rejected"] for item in data["closed_boundary_regressions"]):
        raise ValueError("closed-boundary regressions must expect rejection")
    return data


def run_gate_conformance(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    observed_negative_codes: list[str] = []
    for fixture in manifest["gate_fixtures"]:
        candidate = candidate_from_mapping(fixture["candidate"])
        validation = validate_candidate(state, candidate)
        outcome = execute_with_repair(
            state,
            candidate,
            repair_budget=0,
            trace_context={
                "pilot_id": manifest["pilot_id"],
                "fixture_id": fixture["id"],
                "arm_id": "gate_validation_k0",
            },
        )
        replayed_state = replay_trace_record(to_jsonable(outcome))
        observed_codes = sorted(error.code for error in validation.errors)
        expected_codes = sorted(fixture["expected_codes"])
        expected_status = "fallback" if expected_codes else "commit"
        replay_passed = to_jsonable(replayed_state) == to_jsonable(outcome.state)
        state_changed = to_jsonable(outcome.state) != to_jsonable(state)
        atomic_state_passed = state_changed == (expected_status == "commit")
        passed = (
            observed_codes == expected_codes
            and validation.valid == (not expected_codes)
            and outcome.status == expected_status
            and replay_passed
            and atomic_state_passed
        )
        rows.append(
            {
                **_provenance(
                    "gate_validation_k0",
                    {
                        "implemented_validator_codes": manifest["implemented_validator_codes"],
                        "repair_budget": 0,
                        "repair_strategy": "none",
                    },
                    fixture,
                    to_jsonable(state),
                ),
                "fixture_id": fixture["id"],
                "repair_budget": 0,
                "repair_strategy": "none",
                "expected_code_count": len(expected_codes),
                "expected_codes": expected_codes,
                "observed_error_count": len(observed_codes),
                "observed_codes": observed_codes,
                "valid": validation.valid,
                "expected_status": expected_status,
                "final_status": outcome.status,
                "replay_passed": replay_passed,
                "state_changed": state_changed,
                "atomic_state_passed": atomic_state_passed,
                "final_state_hash": _state_hash(outcome.state),
                "passed": passed,
                "outcome_record": to_jsonable(outcome),
            }
        )
        observed_negative_codes.extend(observed_codes)
    raw = {
        "fixture_count": len(rows),
        "passed_fixture_count": sum(row["passed"] for row in rows),
        "negative_fixture_count": sum(bool(row["expected_code_count"]) for row in rows),
        "valid_control_count": sum(not row["expected_code_count"] for row in rows),
        "implemented_code_count": len(manifest["implemented_validator_codes"]),
        "observed_unique_code_count": len(set(observed_negative_codes)),
    }
    return rows, raw


def run_boundary_sentinels(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Exercise known encoded-gate boundaries without calling them safety passes."""

    rows: list[dict[str, Any]] = []
    for fixture in manifest["boundary_sentinels"]:
        candidate = candidate_from_mapping(fixture["candidate"])
        validation = validate_candidate(state, candidate)
        outcome = execute_with_repair(
            state,
            candidate,
            repair_budget=0,
            trace_context={
                "pilot_id": manifest["pilot_id"],
                "sentinel_id": fixture["id"],
                "arm_id": "boundary_sentinel_k0",
            },
        )
        replayed_state = replay_trace_record(to_jsonable(outcome))
        observed_codes = sorted(error.code for error in validation.errors)
        replay_passed = to_jsonable(replayed_state) == to_jsonable(outcome.state)
        state_changed = to_jsonable(outcome.state) != to_jsonable(state)
        atomic_state_passed = state_changed
        passed = (
            validation.valid == fixture["expected_valid"]
            and not observed_codes
            and outcome.status == "commit"
            and replay_passed
            and atomic_state_passed
        )
        rows.append(
            {
                **_provenance(
                    "boundary_sentinel_k0",
                    {
                        "boundary_type": fixture["boundary_type"],
                        "expected_valid": fixture["expected_valid"],
                        "repair_budget": 0,
                        "repair_strategy": "none",
                    },
                    fixture["candidate"],
                    to_jsonable(state),
                ),
                "sentinel_id": fixture["id"],
                "boundary_type": fixture["boundary_type"],
                "expected_valid": fixture["expected_valid"],
                "observed_valid": validation.valid,
                "observed_codes": observed_codes,
                "final_status": outcome.status,
                "replay_passed": replay_passed,
                "state_changed": state_changed,
                "atomic_state_passed": atomic_state_passed,
                "final_state_hash": _state_hash(outcome.state),
                "passed": passed,
                "safety_pass": False,
                "interpretation": fixture["interpretation"],
                "outcome_record": to_jsonable(outcome),
            }
        )
    raw = {
        "sentinel_count": len(rows),
        "encoded_acceptance_count": sum(row["observed_valid"] for row in rows),
        "passed_sentinel_count": sum(row["passed"] for row in rows),
        "safety_pass_count": sum(row["safety_pass"] for row in rows),
    }
    return rows, raw


def run_closed_boundary_regressions(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Assert that boundaries closed in earlier stages stay closed, in both parsers.

    Each fixture was once accepted by the permissive proposal parser while the replay
    parser rejected it, so replay could refuse a candidate that had already committed.
    Stage 8 closed that asymmetry. This check feeds the same mapping through both the
    proposal-side parser and the replay-side parser and requires that they agree, so
    drift in either one fails the pilot rather than silently reopening the gap.
    """

    rows: list[dict[str, Any]] = []
    for fixture in manifest["closed_boundary_regressions"]:
        payload = fixture["candidate"]

        proposal_code: str | None = None
        proposal_error: str | None = None
        try:
            candidate_from_mapping(payload)
        except AdapterFailure as failure:
            proposal_code = failure.code
            proposal_error = str(failure)
        proposal_rejected = proposal_code is not None

        # Call the replay-side parser directly. A fabricated whole record would fail for
        # unrelated hash/trace reasons and would report parity spuriously.
        replay_error: str | None = None
        try:
            parse_candidate_record(payload)
        except ValueError as failure:
            # ValueError is the replay parser's declared refusal; any other exception is
            # a bug and must surface rather than be counted as agreement.
            replay_error = str(failure)
        replay_rejected = replay_error is not None

        parity = proposal_rejected == replay_rejected
        unknown_key_rejected = (
            proposal_error is not None
            and "unknown candidate fields" in proposal_error
            and replay_error is not None
            and "unknown candidate fields" in replay_error
        )
        rows.append(
            {
                **_provenance(
                    "closed_boundary_regression",
                    {
                        "boundary_type": fixture["boundary_type"],
                        "closed_in": fixture["closed_in"],
                        "expected_rejected": fixture["expected_rejected"],
                    },
                    payload,
                    to_jsonable(state),
                ),
                "regression_id": fixture["id"],
                "boundary_type": fixture["boundary_type"],
                "closed_in": fixture["closed_in"],
                "expected_rejected": fixture["expected_rejected"],
                "proposal_rejected": proposal_rejected,
                "replay_rejected": replay_rejected,
                "parsers_agree": parity,
                "expected_failure_code": fixture["expected_failure_code"],
                "observed_failure_code": proposal_code,
                "proposal_error": proposal_error,
                "replay_error": replay_error,
                "unknown_key_rejected": unknown_key_rejected,
                "final_state_hash": _state_hash(state),
                "passed": (
                    proposal_rejected == fixture["expected_rejected"]
                    and proposal_code == fixture["expected_failure_code"]
                    and parity
                    and unknown_key_rejected
                ),
                "interpretation": fixture["interpretation"],
            }
        )
    raw = {
        "regression_count": len(rows),
        "proposal_rejected_count": sum(row["proposal_rejected"] for row in rows),
        "replay_rejected_count": sum(row["replay_rejected"] for row in rows),
        "parser_parity_count": sum(row["parsers_agree"] for row in rows),
        "unknown_key_rejection_count": sum(row["unknown_key_rejected"] for row in rows),
        "passed_regression_count": sum(row["passed"] for row in rows),
    }
    return rows, raw


def _unchanged_repair(
    state: WorldState,
    candidate: CandidateAction,
    validation: Any,
    attempt: int,
) -> CandidateAction:
    del state, validation, attempt
    return candidate


def _structured_repair(
    state: WorldState,
    candidate: CandidateAction,
    validation: Any,
    attempt: int,
) -> CandidateAction:
    del validation, attempt
    policy = state.action_policies.get(candidate.action_type)
    if policy is None:
        return candidate
    repaired_effects = (candidate.effects & policy.allowed_effects) | policy.required_effects
    return replace(
        candidate,
        preconditions=policy.required_preconditions,
        effects=repaired_effects,
    )


def run_repair_arms(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    strategies: dict[str, Callable[..., CandidateAction] | None] = {
        "none": None,
        "unchanged": _unchanged_repair,
        "policy_restore": _structured_repair,
    }
    rows: list[dict[str, Any]] = []
    for case in manifest["repair"]["cases"]:
        candidate = candidate_from_mapping(case["candidate"])
        initial_validation = validate_candidate(state, candidate)
        if initial_validation.valid:
            raise ValueError(f"repair fixture must start invalid: {case['id']}")
        for arm in manifest["repair"]["arms"]:
            outcome = execute_with_repair(
                state,
                candidate,
                repairer=strategies[arm["strategy"]],
                repair_budget=arm["repair_budget"],
                trace_context={
                    "pilot_id": manifest["pilot_id"],
                    "case_id": case["id"],
                    "arm": arm["id"],
                },
            )
            expected_status = case["expected_status"][arm["id"]]
            replayed_state = replay_trace_record(to_jsonable(outcome))
            replay_passed = to_jsonable(replayed_state) == to_jsonable(outcome.state)
            state_changed = to_jsonable(outcome.state) != to_jsonable(state)
            atomic_state_passed = state_changed == (expected_status == "commit")
            rows.append(
                {
                    **_provenance(
                        arm["id"],
                        arm,
                        case,
                        to_jsonable(state),
                    ),
                    "case_id": case["id"],
                    "repairable": case["repairable"],
                    "repair_budget": arm["repair_budget"],
                    "repair_strategy": arm["strategy"],
                    "initial_error_count": len(initial_validation.errors),
                    "repair_attempt_count": outcome.attempts,
                    "trace_attempt_count": len(outcome.trace),
                    "final_status": outcome.status,
                    "final_error_count": len(outcome.validation.errors),
                    "state_changed": state_changed,
                    "final_state_hash": _state_hash(outcome.state),
                    "replay_passed": replay_passed,
                    "atomic_state_passed": atomic_state_passed,
                    "expected_status": expected_status,
                    "passed": (
                        outcome.status == expected_status and replay_passed and atomic_state_passed
                    ),
                    "trace_hash": outcome.trace_hash,
                    "outcome_record": to_jsonable(outcome),
                }
            )

    summary: list[dict[str, Any]] = []
    for arm in manifest["repair"]["arms"]:
        arm_rows = [row for row in rows if row["arm_id"] == arm["id"]]
        summary.append(
            {
                **_provenance(
                    arm["id"],
                    arm,
                    {"case_ids": [case["id"] for case in manifest["repair"]["cases"]]},
                    to_jsonable(state),
                ),
                "final_state_hash": _canonical_hash([row["final_state_hash"] for row in arm_rows]),
                "case_count": len(arm_rows),
                "repair_budget": arm["repair_budget"],
                "repair_strategy": arm["strategy"],
                "initially_invalid_case_count": sum(
                    row["initial_error_count"] > 0 for row in arm_rows
                ),
                "commit_count": sum(row["final_status"] == "commit" for row in arm_rows),
                "fallback_count": sum(row["final_status"] == "fallback" for row in arm_rows),
                "repair_success_count": sum(
                    row["repair_attempt_count"] > 0 and row["final_status"] == "commit"
                    for row in arm_rows
                ),
                "executed_repair_count": sum(row["repair_attempt_count"] for row in arm_rows),
                "passed_case_count": sum(row["passed"] for row in arm_rows),
            }
        )
    return rows, summary


def _exception_detected(operation: Callable[[], Any]) -> tuple[bool, str]:
    try:
        operation()
    except (OSError, RuntimeError, ValueError) as exc:
        return True, type(exc).__name__
    return False, "none"


def _valid_recorded_adapter(case_id: str = "integrity-case") -> RecordedProposalAdapter:
    record = {
        "scenario_id": case_id,
        "seed": 1,
        "provider_latency_ms": 1.0,
        "input_tokens": 1,
        "output_tokens": 1,
        "candidate": {
            "action_id": f"{case_id}-action",
            "actor_id": "guard",
            "action_type": "OPEN_DOOR",
            "preconditions": ["met_guard"],
            "effects": ["door_open"],
        },
    }
    return RecordedProposalAdapter(f"pilot/{case_id}", "v1", [record])


def _integrity_fault_input_specs(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze operation inputs independently of execution and observed detector outcomes."""

    valid_candidate = manifest["gate_fixtures"][0]["candidate"]
    repair_candidate = manifest["repair"]["cases"][0]["candidate"]
    recorded_adapter = {
        "case_id": "integrity-case",
        "model_id": "pilot/integrity-case",
        "model_revision": "v1",
        "scenario_id": "integrity-case",
        "seed": 1,
        "provider_latency_ms": 1.0,
        "input_tokens": 1,
        "output_tokens": 1,
        "candidate": {
            "action_id": "integrity-case-action",
            "actor_id": "guard",
            "action_type": "OPEN_DOOR",
            "preconditions": ["met_guard"],
            "effects": ["door_open"],
        },
    }
    base = {
        "source_kind": "valid_gate_candidate_k0",
        "source_candidate": valid_candidate,
        "trace_context": {
            "pilot_id": manifest["pilot_id"],
            "fixture": "integrity-base",
        },
    }
    repair = {
        "source_kind": "repairable_candidate_k1",
        "source_candidate": repair_candidate,
        "repair_strategy": "policy_restore",
        "repair_budget": 1,
        "trace_context": {
            "pilot_id": manifest["pilot_id"],
            "fixture": "integrity-repair-base",
        },
    }
    return {
        "checksum_drift": {
            **base,
            "mutation": {"path": "state.facts", "operation": "append", "value": "forged_fact"},
            "rehash": False,
        },
        "rehashed_impossible_state": {
            **base,
            "mutation": {"path": "state.facts", "operation": "append", "value": "forged_fact"},
            "rehash": True,
        },
        "attempts_mutation": {
            **base,
            "mutation": {"path": "attempts", "operation": "replace", "value": 99},
            "rehash": True,
        },
        "type_coercion": {
            **base,
            "mutation": {"path": "attempts", "operation": "integer_to_string"},
            "rehash": True,
        },
        "intermediate_validation_mutation": {
            **repair,
            "mutation": {
                "path": "trace[0].validation.valid",
                "operation": "replace",
                "value": True,
            },
            "rehash": True,
        },
        "early_valid_attempt_followed_by_repair": {
            **repair,
            "mutation": {"path": "trace[0]", "operation": "replace_with_trace[1]"},
            "rehash": True,
        },
        "top_level_candidate_mutation": {
            **base,
            "mutation": {
                "path": "candidate.action_id",
                "operation": "replace",
                "value": "mutated-top-level-action",
            },
            "rehash": True,
        },
        "disconnected_episode": {
            "source_kind": "two_valid_gate_candidates_k0",
            "source_candidate": valid_candidate,
            "episode_records": [
                {
                    "action_id": "integrity-first",
                    "trace_context": {
                        "pilot_id": manifest["pilot_id"],
                        "fixture": "first",
                    },
                },
                {
                    "action_id": "integrity-disconnected",
                    "trace_context": {
                        "pilot_id": manifest["pilot_id"],
                        "fixture": "disconnected",
                    },
                },
            ],
            "operation": "append_two_traces_with_noncontinuous_prior_state",
        },
        "record_outcome_mismatch": {
            "source_kind": "recorded_adapter_pair",
            "recorded_adapter": recorded_adapter,
            "run_ids": ["integrity-record-a", "integrity-record-b"],
            "repair_budget": 0,
            "clock": "frozen_zero",
            "operation": "pair_first_record_with_second_outcome",
        },
        "partial_write_rollback": {
            "source_kind": "recorded_adapter_pair_write",
            "recorded_adapter": recorded_adapter,
            "run_id": "integrity-record-a",
            "repair_budget": 0,
            "clock": "frozen_zero",
            "operation": "inject_oserror_on_result_append_after_trace_append",
        },
    }


def run_integrity_faults(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    fault_specifications = _integrity_fault_input_specs(manifest)
    valid_candidate = candidate_from_mapping(manifest["gate_fixtures"][0]["candidate"])
    base_outcome = execute_with_repair(
        state,
        valid_candidate,
        trace_context={"pilot_id": manifest["pilot_id"], "fixture": "integrity-base"},
    )
    base_record = to_jsonable(base_outcome)
    results: dict[str, dict[str, Any]] = {}

    checksum_drift = _clone(base_record)
    checksum_drift["state"]["facts"].append("forged_fact")
    results["checksum_drift"] = {
        "detected": not verify_trace_record(checksum_drift),
        "detector": "checksum",
        "checksum_valid_after_fault": verify_trace_record(checksum_drift),
    }

    rehashed = _clone(base_record)
    rehashed["state"]["facts"].append("forged_fact")
    _rehash_trace(rehashed)
    detected, exception_type = _exception_detected(lambda: replay_trace_record(rehashed))
    results["rehashed_impossible_state"] = {
        "detected": detected,
        "detector": "semantic_replay",
        "checksum_valid_after_fault": verify_trace_record(rehashed),
        "exception_type": exception_type,
    }

    attempts = _clone(base_record)
    attempts["attempts"] = 99
    _rehash_trace(attempts)
    detected, exception_type = _exception_detected(lambda: replay_trace_record(attempts))
    results["attempts_mutation"] = {
        "detected": detected,
        "detector": "semantic_replay",
        "checksum_valid_after_fault": verify_trace_record(attempts),
        "exception_type": exception_type,
    }

    coerced = _clone(base_record)
    coerced["attempts"] = str(coerced["attempts"])
    _rehash_trace(coerced)
    detected, exception_type = _exception_detected(lambda: replay_trace_record(coerced))
    results["type_coercion"] = {
        "detected": detected,
        "detector": "strict_type_replay",
        "checksum_valid_after_fault": verify_trace_record(coerced),
        "exception_type": exception_type,
    }

    repair_candidate = candidate_from_mapping(manifest["repair"]["cases"][0]["candidate"])
    repair_outcome = execute_with_repair(
        state,
        repair_candidate,
        repairer=_structured_repair,
        repair_budget=1,
        trace_context={
            "pilot_id": manifest["pilot_id"],
            "fixture": "integrity-repair-base",
        },
    )
    if repair_outcome.status != "commit" or len(repair_outcome.trace) != 2:
        raise RuntimeError("integrity repair base must commit after exactly one repair")
    intermediate_validation = _clone(to_jsonable(repair_outcome))
    intermediate_validation["trace"][0]["validation"]["valid"] = True
    _rehash_trace(intermediate_validation)
    detected, exception_type = _exception_detected(
        lambda: replay_trace_record(intermediate_validation)
    )
    results["intermediate_validation_mutation"] = {
        "detected": detected,
        "detector": "deterministic_validation_replay",
        "checksum_valid_after_fault": verify_trace_record(intermediate_validation),
        "exception_type": exception_type,
        "mutated_attempt_index": 0,
        "source_trace_attempt_count": len(repair_outcome.trace),
        "source_attempt_was_nonfinal": True,
    }

    early_valid = _clone(to_jsonable(repair_outcome))
    early_valid["trace"][0]["candidate"] = _clone(early_valid["trace"][1]["candidate"])
    early_valid["trace"][0]["validation"] = _clone(early_valid["trace"][1]["validation"])
    _rehash_trace(early_valid)
    detected, exception_type = _exception_detected(lambda: replay_trace_record(early_valid))
    results["early_valid_attempt_followed_by_repair"] = {
        "detected": detected,
        "detector": "control_flow_replay",
        "checksum_valid_after_fault": verify_trace_record(early_valid),
        "exception_type": exception_type,
    }

    top_level = _clone(base_record)
    top_level["candidate"]["action_id"] = "mutated-top-level-action"
    _rehash_trace(top_level)
    detected, exception_type = _exception_detected(lambda: replay_trace_record(top_level))
    results["top_level_candidate_mutation"] = {
        "detected": detected,
        "detector": "semantic_replay",
        "checksum_valid_after_fault": verify_trace_record(top_level),
        "exception_type": exception_type,
    }

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        trace_path = root / "disconnected.jsonl"
        first = execute_with_repair(
            state,
            replace(valid_candidate, action_id="integrity-first"),
            trace_context={"pilot_id": manifest["pilot_id"], "fixture": "first"},
        )
        disconnected = execute_with_repair(
            state,
            replace(valid_candidate, action_id="integrity-disconnected"),
            trace_context={"pilot_id": manifest["pilot_id"], "fixture": "disconnected"},
        )
        write_trace_jsonl(trace_path, first)
        write_trace_jsonl(trace_path, disconnected)
        detected, exception_type = _exception_detected(
            lambda: replay_trace_jsonl(trace_path, state)
        )
    results["disconnected_episode"] = {
        "detected": detected,
        "detector": "episode_continuity",
        "checksum_valid_after_fault": True,
        "exception_type": exception_type,
    }

    adapter = _valid_recorded_adapter()
    first_case = run_experiment_case(
        adapter,
        state,
        run_id="integrity-record-a",
        scenario_id="integrity-case",
        seed=1,
        clock=lambda: 0.0,
    )
    second_case = run_experiment_case(
        adapter,
        state,
        run_id="integrity-record-b",
        scenario_id="integrity-case",
        seed=1,
        clock=lambda: 0.0,
    )
    mismatched = ExperimentCase(first_case.record, second_case.outcome, second_case.state)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        detected, exception_type = _exception_detected(
            lambda: write_experiment_jsonl(
                root / "results.jsonl", root / "traces.jsonl", mismatched
            )
        )
        no_orphan = not (root / "results.jsonl").exists() and not (root / "traces.jsonl").exists()
    results["record_outcome_mismatch"] = {
        "detected": detected and no_orphan,
        "detector": "record_trace_link",
        "checksum_valid_after_fault": True,
        "exception_type": exception_type,
    }

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        result_path = root / "results.jsonl"
        trace_path = root / "traces.jsonl"
        original_open = Path.open

        def fail_result_open(path: Path, mode: str = "r", *args: Any, **kwargs: Any):
            if path == result_path and mode == "ab":
                raise OSError("injected deterministic result-write failure")
            return original_open(path, mode, *args, **kwargs)

        with patch.object(Path, "open", fail_result_open):
            detected, exception_type = _exception_detected(
                lambda: write_experiment_jsonl(result_path, trace_path, first_case)
            )
        rolled_back = not result_path.exists() and not trace_path.exists()
    results["partial_write_rollback"] = {
        "detected": detected and rolled_back,
        "detector": "pair_write_rollback",
        "checksum_valid_after_fault": True,
        "exception_type": exception_type,
    }

    for fault_id, specification in fault_specifications.items():
        results[fault_id]["fault_specification"] = specification

    expected_faults = manifest["integrity_faults"]
    if set(results) != set(expected_faults):
        raise ValueError("integrity implementation and manifest fault sets differ")
    provenance_input_by_fault = {
        fault_id: {
            "fault_id": fault_id,
            "fault_specification": results[fault_id]["fault_specification"],
        }
        for fault_id in expected_faults
    }
    rows = [
        {
            **_provenance(
                "integrity_fault",
                {
                    "fault_id": fault_id,
                    "detector": results[fault_id]["detector"],
                },
                provenance_input_by_fault[fault_id],
                to_jsonable(state),
            ),
            "fault_id": fault_id,
            "final_state_hash": _state_hash(state),
            **results[fault_id],
        }
        for fault_id in expected_faults
    ]
    raw = {
        "fault_count": len(rows),
        "detected_fault_count": sum(row["detected"] for row in rows),
    }
    return rows, raw


def run_integrity_boundaries(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Document integrity limits that deterministic semantic replay cannot authenticate."""

    repair_candidate = candidate_from_mapping(manifest["repair"]["cases"][0]["candidate"])
    repair_outcome = execute_with_repair(
        state,
        repair_candidate,
        repairer=_structured_repair,
        repair_budget=1,
        trace_context={
            "pilot_id": manifest["pilot_id"],
            "fixture": "integrity-boundary-repair-base",
        },
    )
    if repair_outcome.status != "commit" or len(repair_outcome.trace) != 2:
        raise RuntimeError("integrity boundary base must commit after exactly one repair")

    substituted = _clone(to_jsonable(repair_outcome))
    substitute_candidate = candidate_from_mapping(
        next(
            fixture["candidate"]
            for fixture in manifest["gate_fixtures"]
            if fixture["id"] == "gate-policy-precondition-omission"
        )
    )
    substitute_validation = validate_candidate(state, substitute_candidate)
    if substitute_validation.valid:
        raise RuntimeError("repair-transition substitute must remain initially invalid")
    substituted["trace"][0]["candidate"] = to_jsonable(substitute_candidate)
    substituted["trace"][0]["validation"] = to_jsonable(substitute_validation)
    _rehash_trace(substituted)
    detected, exception_type = _exception_detected(lambda: replay_trace_record(substituted))

    boundary = manifest["integrity_boundaries"][0]
    if boundary["id"] != "repair_transition_substitution":
        raise ValueError("unsupported integrity boundary")
    row = {
        **_provenance(
            "integrity_boundary",
            {
                "boundary_id": boundary["id"],
                "repair_budget": 1,
                "repair_strategy": "policy_restore",
                "expected_detected": boundary["expected_detected"],
            },
            {
                "original_candidate": manifest["repair"]["cases"][0]["candidate"],
                "substitute_candidate": to_jsonable(substitute_candidate),
            },
            to_jsonable(state),
        ),
        "boundary_id": boundary["id"],
        "repair_budget": 1,
        "repair_strategy": "policy_restore",
        "expected_detected": boundary["expected_detected"],
        "observed_detected": detected,
        "replay_accepted": not detected,
        "checksum_valid_after_substitution": verify_trace_record(substituted),
        "exception_type": exception_type,
        "passed": detected == boundary["expected_detected"],
        "final_state_hash": _canonical_hash(substituted["state"]),
        "interpretation": boundary["interpretation"],
        "substituted_outcome_record": substituted,
    }
    raw = {
        "boundary_count": 1,
        "expected_undetected_count": int(not boundary["expected_detected"]),
        "observed_undetected_count": int(not detected),
        "passed_boundary_count": int(row["passed"]),
    }
    return [row], raw


class _TimeoutAdapter:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.model_revision = "v1"

    def propose(self, state: WorldState, scenario_id: str, seed: int) -> ProposalResponse:
        del state, scenario_id, seed
        raise TimeoutError


class _NonJsonAdapter:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.model_revision = "v1"

    def propose(self, state: WorldState, scenario_id: str, seed: int) -> ProposalResponse:
        del state, scenario_id, seed
        candidate = CandidateAction(
            action_id="adapter-non-json",
            actor_id="guard",
            action_type="OPEN_DOOR",
            preconditions=frozenset({"met_guard"}),
            effects=frozenset({"door_open"}),
            metadata={"unsupported": object()},
        )
        return ProposalResponse(candidate, 13.0, 120, 24)


class _ContractNoneAdapter:
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.model_revision = "v1"

    def propose(self, state: WorldState, scenario_id: str, seed: int) -> Any:
        del state, scenario_id, seed
        return None


def _adapter_from_fixture(case: Mapping[str, Any]) -> Any:
    model_id = f"pilot/{case['id']}"
    kind = case["kind"]
    if kind == "simulated_timeout":
        return _TimeoutAdapter(model_id)
    if kind == "non_json_live":
        return _NonJsonAdapter(model_id)
    if kind == "contract_none":
        return _ContractNoneAdapter(model_id)
    if kind == "missing_record":
        return RecordedProposalAdapter(model_id, "v1", [])
    if kind == "malformed_record":
        record = {
            "scenario_id": case["id"],
            "seed": case["seed"],
            "provider_latency_ms": 14.0,
            "input_tokens": 130,
            "output_tokens": 26,
            "candidate": {
                "action_id": case["id"],
                "actor_id": "guard",
                "action_type": "OPEN_DOOR",
                "preconditions": "met_guard",
                "effects": ["door_open"],
            },
        }
        return RecordedProposalAdapter(model_id, "v1", [record])
    if kind == "recorded":
        record = {
            "scenario_id": case["id"],
            "seed": case["seed"],
            "provider_latency_ms": case["provider_latency_ms"],
            "input_tokens": case["input_tokens"],
            "output_tokens": case["output_tokens"],
            "candidate": case["candidate"],
        }
        return RecordedProposalAdapter(model_id, "v1", [record])
    raise ValueError(f"unsupported adapter fixture kind: {kind}")


def _adapter_controller_config(fixture: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "repair_budget": 0,
        "repair_strategy": "none",
        "adapter_kind": fixture["kind"],
        "repairer_strategy_id": "none",
        "repairer_code_hash": NONE_REPAIRER_CODE_HASH,
    }


def _adapter_assignment_input(fixture: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": fixture["id"],
        "scenario_id": fixture["id"],
        "seed": fixture["seed"],
        "candidate": fixture.get("candidate"),
    }


def _expected_adapter_assignments(manifest: Mapping[str, Any]) -> list[tuple[Any, ...]]:
    prior_state_hash = _canonical_hash(to_jsonable(_world_state(manifest["base_state"])))
    return [
        (
            "conformance-adapter",
            "adapter_execution",
            fixture["id"],
            fixture["seed"],
            f"pilot/{fixture['id']}",
            "v1",
            _canonical_hash(_adapter_controller_config(fixture)),
            _canonical_hash(_adapter_assignment_input(fixture)),
            prior_state_hash,
        )
        for fixture in manifest["adapter_cases"]
    ]


def run_adapter_accounting(
    manifest: Mapping[str, Any], state: WorldState
) -> tuple[list[dict[str, Any]], dict[str, int], list[Any]]:
    rows: list[dict[str, Any]] = []
    records = []
    for fixture in manifest["adapter_cases"]:
        adapter = _adapter_from_fixture(fixture)
        controller_config = _adapter_controller_config(fixture)
        assignment_input = _adapter_assignment_input(fixture)
        case = run_experiment_case(
            adapter,
            state,
            run_id="conformance-adapter",
            arm_id="adapter_execution",
            scenario_id=fixture["id"],
            seed=fixture["seed"],
            repair_budget=0,
            controller_config=controller_config,
            assignment_input=assignment_input,
            clock=lambda: 0.0,
        )
        record = case.record
        passed = (
            record.status == fixture["expected_status"]
            and record.failure_type == fixture["expected_failure_type"]
        )
        rows.append(
            {
                "arm_id": record.arm_id,
                "config_hash": record.controller_config_hash,
                "input_hash": record.assignment_input_hash,
                "state_hash": record.prior_state_hash,
                "prior_state_hash": record.prior_state_hash,
                "case_id": fixture["id"],
                "repair_budget": controller_config["repair_budget"],
                "repair_strategy": controller_config["repair_strategy"],
                "kind": fixture["kind"],
                "status": record.status,
                "failure_type": record.failure_type,
                "provider_latency_observed": record.provider_latency_ms is not None,
                "input_tokens": record.input_tokens,
                "output_tokens": record.output_tokens,
                "state_changed": to_jsonable(case.state) != to_jsonable(state),
                "final_state_hash": _state_hash(case.state),
                "passed": passed,
            }
        )
        records.append(record)

    expected_assignments = _expected_adapter_assignments(manifest)
    summarize_experiment(records, expected_assignments)
    statuses = Counter(record.status for record in records)
    raw = {
        "assigned_case_count": len(records),
        "commit_count": statuses["commit"],
        "fallback_count": statuses["fallback"],
        "adapter_failure_count": statuses["adapter_failure"],
        "provider_latency_observed_count": sum(
            record.provider_latency_ms is not None for record in records
        ),
        "input_token_count": sum(record.input_tokens for record in records),
        "output_token_count": sum(record.output_tokens for record in records),
        "proposal_trace_count": sum(record.trace_hash is not None for record in records),
        "state_change_count": sum(row["state_changed"] for row in rows),
        "passed_case_count": sum(row["passed"] for row in rows),
    }
    return rows, raw, records


def run_accounting_guards(
    manifest: Mapping[str, Any], records: Sequence[Any]
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    expected = _expected_adapter_assignments(manifest)
    operations: dict[str, Callable[[], Any]] = {
        "duplicate_observed_record": lambda: summarize_experiment([*records, records[0]], expected),
        "duplicate_expected_assignment": lambda: summarize_experiment(
            records, [*expected, expected[0]]
        ),
        "missing_expected_assignment": lambda: summarize_experiment(records[:-1], expected),
    }
    if set(operations) != set(manifest["accounting_guards"]):
        raise ValueError("accounting guard implementation and manifest differ")
    rows = []
    for guard_id in manifest["accounting_guards"]:
        detected, exception_type = _exception_detected(operations[guard_id])
        rows.append(
            {
                **_provenance(
                    "accounting_guard",
                    {
                        "expected_assignment_count": len(expected),
                        "guard_id": guard_id,
                    },
                    {
                        "guard_id": guard_id,
                        "assignment_keys": expected,
                    },
                    to_jsonable(_world_state(manifest["base_state"])),
                ),
                "guard_id": guard_id,
                "final_state_hash": _state_hash(_world_state(manifest["base_state"])),
                "detected": detected,
                "exception_type": exception_type,
            }
        )
    raw = {
        "guard_count": len(rows),
        "detected_guard_count": sum(row["detected"] for row in rows),
    }
    return rows, raw


def _table_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ";".join(_table_value(item) for item in value)
    return str(value)


def _markdown_value(value: Any) -> str:
    return _table_value(value).replace("|", "\\|").replace("\n", " ")


def _latex_value(value: Any) -> str:
    text = _table_value(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in text)


def _strict_instance_schema(value: Any) -> dict[str, Any]:
    """Create a draft-2020-12 schema that freezes keys, lengths, types, and values."""

    if isinstance(value, Mapping):
        properties = {key: _strict_instance_schema(child) for key, child in value.items()}
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(value),
            "properties": properties,
        }
    if isinstance(value, list):
        schema: dict[str, Any] = {
            "type": "array",
            "minItems": len(value),
            "maxItems": len(value),
            "items": False,
        }
        if value:
            schema["prefixItems"] = [_strict_instance_schema(child) for child in value]
        return schema
    return {"const": value}


def _validate_strict_instance(value: Any, schema: Mapping[str, Any], field: str = "root") -> None:
    if "const" in schema:
        if value != schema["const"] or type(value) is not type(schema["const"]):
            raise ValueError(f"{field} differs from frozen schema constant")
        return
    if schema.get("type") == "object":
        if not isinstance(value, Mapping):
            raise ValueError(f"{field} must be an object")
        expected = set(schema["required"])
        if set(value) != expected:
            raise ValueError(f"{field} object keys differ from strict schema")
        for key in schema["required"]:
            _validate_strict_instance(value[key], schema["properties"][key], f"{field}.{key}")
        return
    if schema.get("type") == "array":
        if not isinstance(value, list) or len(value) != schema["minItems"]:
            raise ValueError(f"{field} array length differs from strict schema")
        if not value:
            return
        for index, (child, child_schema) in enumerate(
            zip(value, schema["prefixItems"], strict=True)
        ):
            _validate_strict_instance(child, child_schema, f"{field}[{index}]")
        return
    raise ValueError(f"unsupported strict schema node at {field}")


def _released_schema(title: str, schema_id: str, value: Any) -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": schema_id,
        "title": title,
        **_strict_instance_schema(value),
    }


def write_table_bundle(
    output_dir: Path,
    stem: str,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
) -> list[Path]:
    if not rows:
        raise ValueError(f"cannot emit an empty table: {stem}")
    paths = [
        output_dir / f"{stem}.csv",
        output_dir / f"{stem}.md",
        output_dir / f"{stem}.tex",
    ]
    with paths[0].open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _table_value(row.get(column)) for column in columns})

    markdown = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    markdown.extend(
        "| " + " | ".join(_markdown_value(row.get(column)) for column in columns) + " |"
        for row in rows
    )
    paths[1].write_text("\n".join(markdown) + "\n", encoding="utf-8")

    alignment = "l" * len(columns)
    latex = [
        f"\\begin{{tabular}}{{{alignment}}}",
        r"\hline",
        " & ".join(_latex_value(column) for column in columns) + r" \\",
        r"\hline",
    ]
    latex.extend(
        " & ".join(_latex_value(row.get(column)) for column in columns) + r" \\" for row in rows
    )
    latex.extend([r"\hline", r"\end{tabular}"])
    paths[2].write_text("\n".join(latex) + "\n", encoding="utf-8")
    return paths


def _summary_rows(
    gate: Mapping[str, int],
    boundaries: Mapping[str, int],
    closed_boundaries: Mapping[str, int],
    repair: Sequence[Mapping[str, Any]],
    integrity: Mapping[str, int],
    integrity_boundaries: Mapping[str, int],
    adapter: Mapping[str, int],
    guards: Mapping[str, int],
) -> list[dict[str, Any]]:
    rows = [
        {
            "section": "gate_conformance",
            "measure": "fixtures_matching_expected_result",
            "numerator": gate["passed_fixture_count"],
            "denominator": gate["fixture_count"],
            "notes": "one valid control and one isolated fixture per implemented code",
        },
        {
            "section": "gate_conformance",
            "measure": "implemented_codes_observed",
            "numerator": gate["observed_unique_code_count"],
            "denominator": gate["implemented_code_count"],
            "notes": "designed fixtures, not independent human labels",
        },
        {
            "section": "boundary_sentinels",
            "measure": "encoded_acceptances_documented",
            "numerator": boundaries["encoded_acceptance_count"],
            "denominator": boundaries["sentinel_count"],
            "notes": (
                "known semantic-extraction and policy-completeness boundaries; not safety passes"
            ),
        },
        {
            "section": "closed_boundary_regressions",
            "measure": "closed_boundaries_still_rejected",
            "numerator": closed_boundaries["passed_regression_count"],
            "denominator": closed_boundaries["regression_count"],
            "notes": "both parsers reject the complete candidate specifically for its unknown key",
        },
        {
            "section": "closed_boundary_regressions",
            "measure": "parser_parity_on_unknown_keys",
            "numerator": closed_boundaries["parser_parity_count"],
            "denominator": closed_boundaries["regression_count"],
            "notes": "proposal and replay parsers agree on unknown-key rejection",
        },
    ]
    for row in repair:
        rows.extend(
            [
                {
                    "section": "repair_arms",
                    "measure": f"{row['arm_id']}:commits",
                    "numerator": row["commit_count"],
                    "denominator": row["case_count"],
                    "notes": "two initially invalid designed cases",
                },
                {
                    "section": "repair_arms",
                    "measure": f"{row['arm_id']}:repair_successes",
                    "numerator": row["repair_success_count"],
                    "denominator": row["initially_invalid_case_count"],
                    "notes": "commit after one or more repair attempts",
                },
            ]
        )
    rows.extend(
        [
            {
                "section": "integrity_faults",
                "measure": "named_detectable_faults_detected",
                "numerator": integrity["detected_fault_count"],
                "denominator": integrity["fault_count"],
                "notes": "checksums are unkeyed integrity checks, not signatures",
            },
            {
                "section": "integrity_boundaries",
                "measure": "known_undetectable_boundaries_observed",
                "numerator": integrity_boundaries["observed_undetected_count"],
                "denominator": integrity_boundaries["expected_undetected_count"],
                "notes": "repair generation is not authenticated or re-executed by semantic replay",
            },
            {
                "section": "adapter_accounting",
                "measure": "commits",
                "numerator": adapter["commit_count"],
                "denominator": adapter["assigned_case_count"],
                "notes": "raw assigned-case count",
            },
            {
                "section": "adapter_accounting",
                "measure": "symbolic_fallbacks",
                "numerator": adapter["fallback_count"],
                "denominator": adapter["assigned_case_count"],
                "notes": "raw assigned-case count",
            },
            {
                "section": "adapter_accounting",
                "measure": "adapter_failures",
                "numerator": adapter["adapter_failure_count"],
                "denominator": adapter["assigned_case_count"],
                "notes": "raw assigned-case count",
            },
            {
                "section": "adapter_accounting",
                "measure": "provider_latency_observed",
                "numerator": adapter["provider_latency_observed_count"],
                "denominator": adapter["assigned_case_count"],
                "notes": "response-observed cases only; no percentile reported",
            },
            {
                "section": "accounting_guards",
                "measure": "manifest_faults_detected",
                "numerator": guards["detected_guard_count"],
                "denominator": guards["guard_count"],
                "notes": "duplicate observed, duplicate expected, and missing assignment",
            },
        ]
    )
    return rows


def _actual_published_provenance(result: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    row_groups = (
        ("gate_conformance", result["gate_conformance"]["rows"], "fixture_id"),
        ("boundary_sentinels", result["boundary_sentinels"]["rows"], "sentinel_id"),
        (
            "closed_boundary_regressions",
            result["closed_boundary_regressions"]["rows"],
            "regression_id",
        ),
        ("repair_arms", result["repair_arms"]["rows"], "case_id"),
        (
            "repair_arm_summary",
            result["repair_arms"]["raw_counts_by_arm"],
            "arm_id",
        ),
        ("integrity_faults", result["integrity_faults"]["rows"], "fault_id"),
        (
            "integrity_boundaries",
            result["integrity_boundaries"]["rows"],
            "boundary_id",
        ),
        ("adapter_accounting", result["adapter_accounting"]["rows"], "case_id"),
        ("accounting_guards", result["accounting_guards"]["rows"], "guard_id"),
        ("pilot_summary", result["summary_rows"], "measure"),
    )
    actual: dict[str, dict[str, str]] = {}
    for section, rows, identifier_field in row_groups:
        for row in rows:
            row_id = str(row[identifier_field])
            if section == "pilot_summary":
                row_id = f"{row['section']}:{row_id}"
            key = f"{section}/{row_id}/{row['arm_id']}"
            if key in actual:
                raise ValueError(f"duplicate pilot assignment key: {key}")
            try:
                row_class = ROW_CLASS_BY_SECTION[section]
            except KeyError as failure:
                raise ValueError(
                    f"section {section!r} has no declared row class; register it in "
                    "ROW_CLASS_BY_SECTION"
                ) from failure
            entry = {
                "section": section,
                "row_id": row_id,
                "row_class": row_class,
                **{column: row[column] for column in PROVENANCE_COLUMNS},
            }
            for hash_field in (
                "config_hash",
                "input_hash",
                "state_hash",
                "prior_state_hash",
            ):
                value = entry[hash_field]
                if len(value) != 64 or any(
                    character not in "0123456789abcdef" for character in value
                ):
                    raise ValueError(f"invalid {hash_field} in pilot row {key}")
            actual[key] = entry
    return actual


def _expected_published_provenance(
    manifest: Mapping[str, Any], state: WorldState
) -> dict[str, dict[str, str]]:
    """Freeze expected row provenance exclusively from the pre-run input manifest."""

    expected: dict[str, dict[str, str]] = {}

    def add(
        section: str,
        row_id: str,
        arm_id: str,
        config_payload: Any,
        input_payload: Any,
    ) -> None:
        key = f"{section}/{row_id}/{arm_id}"
        if key in expected:
            raise ValueError(f"duplicate expected pilot assignment key: {key}")
        try:
            row_class = ROW_CLASS_BY_SECTION[section]
        except KeyError as failure:
            raise ValueError(
                f"section {section!r} has no declared row class; register it in "
                "ROW_CLASS_BY_SECTION so aggregate rows are never counted as executed"
            ) from failure
        expected[key] = {
            "section": section,
            "row_id": row_id,
            "row_class": row_class,
            **_provenance(
                arm_id,
                config_payload,
                input_payload,
                to_jsonable(state),
            ),
        }

    gate_config = {
        "implemented_validator_codes": manifest["implemented_validator_codes"],
        "repair_budget": 0,
        "repair_strategy": "none",
    }
    for fixture in manifest["gate_fixtures"]:
        add("gate_conformance", fixture["id"], "gate_validation_k0", gate_config, fixture)
    for fixture in manifest["boundary_sentinels"]:
        add(
            "boundary_sentinels",
            fixture["id"],
            "boundary_sentinel_k0",
            {
                "boundary_type": fixture["boundary_type"],
                "expected_valid": fixture["expected_valid"],
                "repair_budget": 0,
                "repair_strategy": "none",
            },
            fixture["candidate"],
        )
    for fixture in manifest["closed_boundary_regressions"]:
        add(
            "closed_boundary_regressions",
            fixture["id"],
            "closed_boundary_regression",
            {
                "boundary_type": fixture["boundary_type"],
                "closed_in": fixture["closed_in"],
                "expected_rejected": fixture["expected_rejected"],
            },
            fixture["candidate"],
        )
    repair_case_ids = [case["id"] for case in manifest["repair"]["cases"]]
    for arm in manifest["repair"]["arms"]:
        for case in manifest["repair"]["cases"]:
            add("repair_arms", case["id"], arm["id"], arm, case)
        add(
            "repair_arm_summary",
            arm["id"],
            arm["id"],
            arm,
            {"case_ids": repair_case_ids},
        )
    integrity_fault_specs = _integrity_fault_input_specs(manifest)
    for fault_id in manifest["integrity_faults"]:
        detector_by_fault = {
            "checksum_drift": "checksum",
            "rehashed_impossible_state": "semantic_replay",
            "attempts_mutation": "semantic_replay",
            "type_coercion": "strict_type_replay",
            "intermediate_validation_mutation": "deterministic_validation_replay",
            "early_valid_attempt_followed_by_repair": "control_flow_replay",
            "top_level_candidate_mutation": "semantic_replay",
            "disconnected_episode": "episode_continuity",
            "record_outcome_mismatch": "record_trace_link",
            "partial_write_rollback": "pair_write_rollback",
        }
        add(
            "integrity_faults",
            fault_id,
            "integrity_fault",
            {"fault_id": fault_id, "detector": detector_by_fault[fault_id]},
            {
                "fault_id": fault_id,
                "fault_specification": integrity_fault_specs[fault_id],
            },
        )
    for boundary in manifest["integrity_boundaries"]:
        add(
            "integrity_boundaries",
            boundary["id"],
            "integrity_boundary",
            {
                "boundary_id": boundary["id"],
                "repair_budget": 1,
                "repair_strategy": "policy_restore",
                "expected_detected": boundary["expected_detected"],
            },
            {
                "original_candidate": manifest["repair"]["cases"][0]["candidate"],
                "substitute_candidate": to_jsonable(
                    candidate_from_mapping(
                        next(
                            fixture["candidate"]
                            for fixture in manifest["gate_fixtures"]
                            if fixture["id"] == "gate-policy-precondition-omission"
                        )
                    )
                ),
            },
        )
    for fixture in manifest["adapter_cases"]:
        controller_config = _adapter_controller_config(fixture)
        assignment_input = _adapter_assignment_input(fixture)
        add(
            "adapter_accounting",
            fixture["id"],
            "adapter_execution",
            controller_config,
            assignment_input,
        )
    expected_adapter_keys = _expected_adapter_assignments(manifest)
    for guard_id in manifest["accounting_guards"]:
        add(
            "accounting_guards",
            guard_id,
            "accounting_guard",
            {
                "expected_assignment_count": len(expected_adapter_keys),
                "guard_id": guard_id,
            },
            {"guard_id": guard_id, "assignment_keys": expected_adapter_keys},
        )
    summary_ids = [
        ("gate_conformance", "fixtures_matching_expected_result"),
        ("gate_conformance", "implemented_codes_observed"),
        ("boundary_sentinels", "encoded_acceptances_documented"),
        ("closed_boundary_regressions", "closed_boundaries_still_rejected"),
        ("closed_boundary_regressions", "parser_parity_on_unknown_keys"),
        *[
            ("repair_arms", f"{arm['id']}:{measure}")
            for arm in manifest["repair"]["arms"]
            for measure in ("commits", "repair_successes")
        ],
        ("integrity_faults", "named_detectable_faults_detected"),
        ("integrity_boundaries", "known_undetectable_boundaries_observed"),
        ("adapter_accounting", "commits"),
        ("adapter_accounting", "symbolic_fallbacks"),
        ("adapter_accounting", "adapter_failures"),
        ("adapter_accounting", "provider_latency_observed"),
        ("accounting_guards", "manifest_faults_detected"),
    ]
    for section, measure in summary_ids:
        row_id = f"{section}:{measure}"
        add(
            "pilot_summary",
            row_id,
            "pilot_summary",
            {"pilot_id": manifest["pilot_id"]},
            {"section": section, "measure": measure},
        )
    return expected


def _build_assignment_manifest(
    manifest: Mapping[str, Any], state: WorldState, result: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind published rows to provenance frozen independently before execution."""

    expected = _expected_published_provenance(manifest, state)
    actual = _actual_published_provenance(result)
    if actual != expected:
        missing = sorted(expected.keys() - actual.keys())
        unexpected = sorted(actual.keys() - expected.keys())
        mismatched = sorted(
            key for key in expected.keys() & actual.keys() if expected[key] != actual[key]
        )
        raise ValueError(
            "pilot provenance binding mismatch: "
            f"missing={missing}, unexpected={unexpected}, mismatched={mismatched}"
        )

    executed = sum(1 for row in expected.values() if row["row_class"] == "executed")
    aggregate = sum(1 for row in expected.values() if row["row_class"] == "aggregate")
    if executed + aggregate != len(expected):
        raise ValueError(
            "row-class partition is incomplete: "
            f"{executed} executed + {aggregate} aggregate != {len(expected)} rows"
        )

    assignment_manifest = {
        "schema_version": "1.0.0",
        "executed_row_count": executed,
        "aggregate_row_count": aggregate,
        "pilot_id": manifest["pilot_id"],
        "assignment_count": len(expected),
        "assignment_set_hash": _canonical_hash(expected),
        "expected_provenance_by_key": expected,
    }
    entry_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["section", "row_id", "row_class", *PROVENANCE_COLUMNS],
        "properties": {
            "section": {"type": "string", "minLength": 1},
            "row_id": {"type": "string", "minLength": 1},
            "row_class": {"enum": sorted(ROW_CLASSES)},
            "arm_id": {"type": "string", "minLength": 1},
            "config_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "input_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "state_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "prior_state_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
        },
    }
    assignment_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://example.org/schemas/trace-rpg-pilot-assignment-manifest.schema.json",
        "title": "TRACE-RPG deterministic conformance pilot assignment manifest",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "pilot_id",
            "assignment_count",
            "executed_row_count",
            "aggregate_row_count",
            "assignment_set_hash",
            "expected_provenance_by_key",
        ],
        "properties": {
            "schema_version": {"const": "1.0.0"},
            "pilot_id": {"const": manifest["pilot_id"]},
            "assignment_count": {"const": len(expected)},
            # Pinned as consts so a drifting executed/aggregate split fails schema
            # validation rather than quietly changing what the total means.
            "executed_row_count": {"const": executed},
            "aggregate_row_count": {"const": aggregate},
            "assignment_set_hash": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "expected_provenance_by_key": {
                "type": "object",
                "additionalProperties": False,
                "required": list(expected),
                "properties": {key: entry_schema for key in expected},
            },
        },
    }
    return assignment_manifest, assignment_schema


def _assert_complete(result: Mapping[str, Any]) -> None:
    checks = (
        result["gate_conformance"]["raw_counts"]["passed_fixture_count"]
        == result["gate_conformance"]["raw_counts"]["fixture_count"],
        result["boundary_sentinels"]["raw_counts"]["passed_sentinel_count"]
        == result["boundary_sentinels"]["raw_counts"]["sentinel_count"],
        result["boundary_sentinels"]["raw_counts"]["safety_pass_count"] == 0,
        result["closed_boundary_regressions"]["raw_counts"]["passed_regression_count"]
        == result["closed_boundary_regressions"]["raw_counts"]["regression_count"],
        result["closed_boundary_regressions"]["raw_counts"]["parser_parity_count"]
        == result["closed_boundary_regressions"]["raw_counts"]["regression_count"],
        result["closed_boundary_regressions"]["raw_counts"]["unknown_key_rejection_count"]
        == result["closed_boundary_regressions"]["raw_counts"]["regression_count"],
        all(row["passed"] for row in result["repair_arms"]["rows"]),
        result["integrity_faults"]["raw_counts"]["detected_fault_count"]
        == result["integrity_faults"]["raw_counts"]["fault_count"],
        result["integrity_boundaries"]["raw_counts"]["passed_boundary_count"]
        == result["integrity_boundaries"]["raw_counts"]["boundary_count"],
        result["integrity_boundaries"]["raw_counts"]["observed_undetected_count"]
        == result["integrity_boundaries"]["raw_counts"]["expected_undetected_count"],
        result["adapter_accounting"]["raw_counts"]["passed_case_count"]
        == result["adapter_accounting"]["raw_counts"]["assigned_case_count"],
        result["accounting_guards"]["raw_counts"]["detected_guard_count"]
        == result["accounting_guards"]["raw_counts"]["guard_count"],
    )
    if not all(checks):
        raise RuntimeError("conformance pilot failed one or more designed fixtures")


def _source_input_entries(manifest_path: Path) -> list[dict[str, Any]]:
    paths = {
        manifest_path,
        Path(__file__).resolve(),
        ROOT / "pyproject.toml",
        ROOT / "uv.lock",
        ROOT / "tests/test_conformance_pilot.py",
        *(ROOT / "src/nesy_game").glob("*.py"),
        *(ROOT / "game-track/schemas").glob("*.json"),
    }
    entries = []
    for path in sorted((item for item in paths if item.is_file()), key=lambda item: str(item)):
        try:
            label = str(path.relative_to(ROOT))
        except ValueError:
            label = path.name
        entries.append({"path": label, "sha256": _sha256(path), "bytes": path.stat().st_size})
    return entries


def _command_text(arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _reproducibility_provenance(input_entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    git_root = Path(_command_text(("git", "-C", str(ROOT), "rev-parse", "--show-toplevel")))
    project_prefix = ROOT.relative_to(git_root).as_posix()
    excluded = (
        f":(exclude){project_prefix}/runs/**",
        f":(exclude){project_prefix}/research/academic-pipeline/stage-04-pilot/**",
    )
    status = _command_text(
        (
            "git",
            "-C",
            str(git_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            ".",
            *excluded,
        )
    )
    diff = _command_text(
        (
            "git",
            "-C",
            str(git_root),
            "diff",
            "--binary",
            "HEAD",
            "--",
            ".",
            *excluded,
        )
    )
    untracked_output = subprocess.run(
        (
            "git",
            "-C",
            str(git_root),
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            ".",
            *excluded,
        ),
        check=True,
        capture_output=True,
    ).stdout
    untracked_entries = []
    for raw_path in sorted(filter(None, untracked_output.split(b"\0"))):
        relative_path = raw_path.decode("utf-8")
        path = git_root / relative_path
        if path.is_file():
            untracked_entries.append(
                {
                    "path": relative_path,
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
            )
    dirty_payload = {
        "status": status.splitlines(),
        "tracked_diff": diff,
        "untracked_files": untracked_entries,
    }
    return {
        "git": {
            "commit": _command_text(("git", "-C", str(git_root), "rev-parse", "HEAD")),
            "dirty": bool(status),
            "dirty_diff_hash": _canonical_hash(dirty_payload),
            "release_paths_excluded_from_dirty_hash": [
                f"{project_prefix}/runs/",
                f"{project_prefix}/research/academic-pipeline/stage-04-pilot/",
            ],
        },
        "environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "python_executable": sys.executable,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "uv_version": _command_text(("uv", "--version")),
        },
        "runner_hash": _sha256(Path(__file__).resolve()),
        "source_tree_hash": _canonical_hash(list(input_entries)),
    }


def _mirror_release(source_dir: Path, release_dir: Path) -> None:
    release_dir.mkdir(parents=True, exist_ok=True)
    source_names = {path.name for path in source_dir.iterdir() if path.is_file()}
    release_names = {path.name for path in release_dir.iterdir() if path.is_file()}
    unexpected = sorted(release_names - source_names)
    if unexpected:
        raise ValueError(f"release mirror contains unexpected stale files: {unexpected}")
    for source in sorted(source_dir.iterdir(), key=lambda path: path.name):
        if source.is_file():
            destination = release_dir / source.name
            shutil.copy2(source, destination)
            if _sha256(destination) != _sha256(source):
                raise RuntimeError(f"release mirror checksum mismatch: {source.name}")


def run_pilot(
    manifest_path: Path,
    output_dir: Path,
    release_dir: Path | None = None,
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    output_dir = output_dir.resolve()
    manifest = load_manifest(manifest_path)
    state = _world_state(manifest["base_state"])

    gate_rows, gate_raw = run_gate_conformance(manifest, state)
    boundary_rows, boundary_raw = run_boundary_sentinels(manifest, state)
    closed_rows, closed_raw = run_closed_boundary_regressions(manifest, state)
    repair_rows, repair_summary = run_repair_arms(manifest, state)
    integrity_rows, integrity_raw = run_integrity_faults(manifest, state)
    integrity_boundary_rows, integrity_boundary_raw = run_integrity_boundaries(manifest, state)
    adapter_rows, adapter_raw, adapter_records = run_adapter_accounting(manifest, state)
    guard_rows, guard_raw = run_accounting_guards(manifest, adapter_records)
    summary_rows = [
        {
            **_provenance(
                "pilot_summary",
                {"pilot_id": manifest["pilot_id"]},
                {"section": row["section"], "measure": row["measure"]},
                to_jsonable(state),
            ),
            "final_state_hash": _state_hash(state),
            **row,
        }
        for row in _summary_rows(
            gate_raw,
            boundary_raw,
            closed_raw,
            repair_summary,
            integrity_raw,
            integrity_boundary_raw,
            adapter_raw,
            guard_raw,
        )
    ]

    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "pilot_id": manifest["pilot_id"],
        "evidence_scope": manifest["evidence_scope"],
        "amendment": manifest["amendment"],
        "inference": "none; raw designed-fixture counts only",
        "gate_conformance": {"rows": gate_rows, "raw_counts": gate_raw},
        "boundary_sentinels": {"rows": boundary_rows, "raw_counts": boundary_raw},
        "closed_boundary_regressions": {"rows": closed_rows, "raw_counts": closed_raw},
        "repair_arms": {"rows": repair_rows, "raw_counts_by_arm": repair_summary},
        "integrity_faults": {"rows": integrity_rows, "raw_counts": integrity_raw},
        "integrity_boundaries": {
            "rows": integrity_boundary_rows,
            "raw_counts": integrity_boundary_raw,
        },
        "adapter_accounting": {
            "rows": adapter_rows,
            "raw_counts": adapter_raw,
            "records": [
                {
                    "arm_id": record.arm_id,
                    "config_hash": record.controller_config_hash,
                    "input_hash": record.assignment_input_hash,
                    "state_hash": record.prior_state_hash,
                    "prior_state_hash": record.prior_state_hash,
                    "final_state_hash": record.final_state_hash,
                    "experiment_record": to_jsonable(record),
                }
                for record in adapter_records
            ],
        },
        "accounting_guards": {"rows": guard_rows, "raw_counts": guard_raw},
        "summary_rows": summary_rows,
        "claim_boundary": [
            "supports implementation conformance on designed fixtures",
            "does not support model superiority, player-experience, affect, or causal claims",
            "does not estimate validator false-positive or false-negative rates",
            "boundary sentinel acceptance is not evidence of semantic safety or policy completeness",
            "the closed candidate-contract regression establishes parser rejection parity only; it is not semantic-safety evidence",
            "semantic replay does not authenticate or re-execute the repair generator",
        ],
    }
    assignment_manifest, assignment_schema = _build_assignment_manifest(manifest, state, result)
    result["assignment_manifest"] = {
        "path": "pilot-assignment-manifest.json",
        "schema_path": "pilot-assignment-manifest.schema.json",
        "assignment_count": assignment_manifest["assignment_count"],
        "assignment_set_hash": assignment_manifest["assignment_set_hash"],
    }
    _assert_complete(result)

    output_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []
    generated.extend(
        write_table_bundle(
            output_dir,
            "gate-conformance",
            gate_rows,
            (
                *PROVENANCE_COLUMNS,
                "fixture_id",
                "repair_budget",
                "repair_strategy",
                "expected_code_count",
                "expected_codes",
                "observed_error_count",
                "observed_codes",
                "valid",
                "expected_status",
                "final_status",
                "replay_passed",
                "state_changed",
                "atomic_state_passed",
                "final_state_hash",
                "passed",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "integrity-boundaries",
            integrity_boundary_rows,
            (
                *PROVENANCE_COLUMNS,
                "boundary_id",
                "repair_budget",
                "repair_strategy",
                "expected_detected",
                "observed_detected",
                "replay_accepted",
                "checksum_valid_after_substitution",
                "exception_type",
                "passed",
                "final_state_hash",
                "interpretation",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "repair-arm-summary",
            repair_summary,
            (
                *PROVENANCE_COLUMNS,
                "final_state_hash",
                "repair_budget",
                "repair_strategy",
                "case_count",
                "initially_invalid_case_count",
                "commit_count",
                "fallback_count",
                "repair_success_count",
                "executed_repair_count",
                "passed_case_count",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "boundary-sentinels",
            boundary_rows,
            (
                *PROVENANCE_COLUMNS,
                "sentinel_id",
                "boundary_type",
                "expected_valid",
                "observed_valid",
                "observed_codes",
                "final_status",
                "replay_passed",
                "state_changed",
                "atomic_state_passed",
                "final_state_hash",
                "passed",
                "safety_pass",
                "interpretation",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "closed-boundary-regressions",
            closed_rows,
            (
                *PROVENANCE_COLUMNS,
                "regression_id",
                "boundary_type",
                "closed_in",
                "expected_rejected",
                "proposal_rejected",
                "replay_rejected",
                "parsers_agree",
                "expected_failure_code",
                "observed_failure_code",
                "proposal_error",
                "replay_error",
                "unknown_key_rejected",
                "final_state_hash",
                "passed",
                "interpretation",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "repair-arms",
            repair_rows,
            (
                *PROVENANCE_COLUMNS,
                "case_id",
                "repairable",
                "repair_budget",
                "repair_strategy",
                "initial_error_count",
                "repair_attempt_count",
                "trace_attempt_count",
                "final_status",
                "final_error_count",
                "state_changed",
                "final_state_hash",
                "replay_passed",
                "atomic_state_passed",
                "passed",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "integrity-faults",
            integrity_rows,
            (
                *PROVENANCE_COLUMNS,
                "fault_id",
                "final_state_hash",
                "fault_specification",
                "detector",
                "checksum_valid_after_fault",
                "detected",
                "exception_type",
                "mutated_attempt_index",
                "source_trace_attempt_count",
                "source_attempt_was_nonfinal",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "adapter-accounting",
            adapter_rows,
            (
                *PROVENANCE_COLUMNS,
                "case_id",
                "kind",
                "repair_budget",
                "repair_strategy",
                "status",
                "failure_type",
                "provider_latency_observed",
                "input_tokens",
                "output_tokens",
                "state_changed",
                "final_state_hash",
                "passed",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "accounting-guards",
            guard_rows,
            (
                *PROVENANCE_COLUMNS,
                "guard_id",
                "final_state_hash",
                "detected",
                "exception_type",
            ),
        )
    )
    generated.extend(
        write_table_bundle(
            output_dir,
            "pilot-summary",
            summary_rows,
            (
                *PROVENANCE_COLUMNS,
                "section",
                "measure",
                "numerator",
                "denominator",
                "notes",
                "final_state_hash",
            ),
        )
    )

    assignment_path = output_dir / "pilot-assignment-manifest.json"
    assignment_path.write_text(
        json.dumps(assignment_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(assignment_path)
    assignment_schema_path = output_dir / "pilot-assignment-manifest.schema.json"
    assignment_schema_path.write_text(
        json.dumps(assignment_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(assignment_schema_path)

    input_schema = _released_schema(
        "TRACE-RPG frozen conformance pilot input manifest",
        "https://example.org/schemas/trace-rpg-pilot-input-manifest.schema.json",
        manifest,
    )
    _validate_strict_instance(manifest, input_schema)
    input_schema_path = output_dir / "pilot-input-manifest.schema.json"
    input_schema_path.write_text(
        json.dumps(input_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(input_schema_path)

    results_schema = _released_schema(
        "TRACE-RPG deterministic conformance pilot results",
        "https://example.org/schemas/trace-rpg-pilot-results.schema.json",
        result,
    )
    _validate_strict_instance(result, results_schema)
    results_schema_path = output_dir / "pilot-results.schema.json"
    results_schema_path.write_text(
        json.dumps(results_schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(results_schema_path)

    result_path = output_dir / "pilot-results.json"
    result_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    generated.append(result_path)

    input_entries = _source_input_entries(manifest_path)
    artifact_entries = [
        {
            "path": path.name,
            "sha256": _sha256(path),
            "bytes": path.stat().st_size,
        }
        for path in sorted(generated, key=lambda item: item.name)
    ]
    sha_manifest = {
        "schema_version": "1.0.0",
        "hash_algorithm": "sha256",
        "inputs": input_entries,
        "artifacts": artifact_entries,
        "reproducibility": _reproducibility_provenance(input_entries),
        "self_hash_excluded": True,
    }
    sha_path = output_dir / "sha256-manifest.json"
    sha_path.write_text(
        json.dumps(sha_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if release_dir is not None and release_dir.resolve() != output_dir:
        _mirror_release(output_dir, release_dir.resolve())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--release-dir", type=Path, default=DEFAULT_RELEASE)
    args = parser.parse_args()
    result = run_pilot(args.manifest, args.output_dir, args.release_dir)
    print(
        json.dumps(
            {
                "pilot_id": result["pilot_id"],
                "output_dir": str(args.output_dir.resolve()),
                "release_dir": str(args.release_dir.resolve()),
                "gate_fixture_count": result["gate_conformance"]["raw_counts"]["fixture_count"],
                "integrity_fault_count": result["integrity_faults"]["raw_counts"]["fault_count"],
                "adapter_case_count": result["adapter_accounting"]["raw_counts"][
                    "assigned_case_count"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
