#!/usr/bin/env python3
"""Validate frozen NPC 1.1 manifests and causal execution evidence.

The validator is a read-only, no-model gate.  It verifies source-bound assignment
sets, byte-level provenance, immutable inputs and receipts, canonical controller
snapshots, native Godot execution, and operation-conditioned state transitions.
Assigned failures remain visible; they are never converted to unavailable success.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.npc_goal import ProtocolError, ReplayValidator, validate_envelope

PACKET_SCHEMA_VERSION = "npc-goal-recovery/evidence-1"
RECORD_SCHEMA_VERSION = "npc-goal-recovery/record-1"
CORE_SCHEMA_VERSION = "npc-goal-recovery/1.1.0"
SCHEMA_VERSION = CORE_SCHEMA_VERSION
ARMS = {"P", "R", "O"}
EXPECTED_COUNTS = {"NPC-ENG1": 16, "NPC-SCR1": 72}
OBSERVATION_KEYS = {
    "lens_reachable",
    "lens_carried",
    "signal_restored",
    "tide_lead_authorized",
    "goal_reached",
    "in_dialogue",
}
PROTOCOL_BUDGET_KEYS = {
    "intent_deadline_ms",
    "episode_deadline_ms",
    "max_intent_calls",
    "max_action_attempts",
    "max_replans",
    "max_plan_expansions",
    "max_inflight_per_session",
    "input_tokens",
    "output_tokens",
    "cost",
}
EXPECTED_CLAIMS = {
    "engineering": "synthetic closed-world deterministic protocol/gate checks",
    "screening": "bounded descriptive screening only",
    "independent_labels": False,
    "efficacy_pending": True,
    "superiority": False,
    "generalization": False,
    "human_benefit": False,
    "c_result_promotion": False,
}
REQUIRED_ASSIGNMENT_KEYS = {
    "assignment_id",
    "packet_id",
    "case_id",
    "fixture_ref",
    "arm",
    "repetition",
    "seed",
    "fixture_input_sha256",
    "config_hash",
    "source_project_config_sha256",
    "npc_protocol_config_sha256",
    "policy_hash",
    "budget",
    "source_kind",
    "utterance_source_kind",
    "independent_source",
    "assignment_key",
}
WORLD_OPERATIONS = {"acquire_object", "install_lens", "reveal_hint"}
DIALOGUE_OPERATIONS = {"clarify", "negotiate", "dialogue", "ask_information"}
NON_APPLIED = {
    "REJECTED",
    "STALE",
    "CANCELLED",
    "ERROR",
    "DUPLICATE",
    "NO_ROUTE",
    "NO_CANONICAL_ROUTE",
}
TAMPER_REJECTION_STATUSES = {"REJECTED", "STALE", "ERROR"}
CANONICAL_TAMPER_CODES = {
    "CONTENT_HASH_MISMATCH",
    "STATE_HASH_MISMATCH",
    "STEP_ARGUMENTS_INVALID",
    "STEP_BINDING_INVALID",
    "PLAYER_ACTION_BINDING_MISMATCH",
    "PLAYER_ACTION_PRECONDITION_MISMATCH",
    "DECISION_CONTEXT_MISMATCH",
    "POLICY_HASH_MISMATCH",
}
REPLAY_ROW_KEYS = {"assignment_id", "status", "assigned_failure", "python", "godot", "model_calls"}
REPLAY_DENOMINATOR_KEYS = {
    "python_eligible",
    "python_failed",
    "python_unavailable",
    "godot_eligible",
    "godot_failed",
    "godot_unavailable",
}
REPLAY_REPORT_KEYS = {"schema_version", "packet_id", "model_calls", "denominators", "rows"}
RUNTIME_SOURCE_PATHS = (
    "src/nesy_game/npc_goal.py",
    "scripts/codex_oauth_llm.py",
    "scripts/run_npc_goal_experiment.py",
    "game-track/godot/scripts/game3d/game_3d.gd",
    "game-track/godot/scripts/game3d/npc_agent_client.gd",
    "game-track/godot/scripts/sealed_lighthouse_machine.gd",
    "game-track/godot/scripts/canonical_state.gd",
    "game-track/godot/data/npc-goal-recovery.json",
    "game-track/godot/data/sealed_lighthouse.json",
    "game-track/godot/scenes/main_3d.tscn",
)


def canonical(value: Any) -> bytes:
    """Return the protocol's canonical JSON bytes (for value digests only)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def runtime_source_hashes(root: Path) -> dict[str, str]:
    """Return hashes for every runtime source frozen by the experiment protocol."""
    return {path: sha256_file(root / path) for path in RUNTIME_SOURCE_PATHS}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ProtocolError(f"{path}:{line_number}: row must be an object")
        rows.append(value)
    return rows


def _normalize_policy(value: Any) -> Any:
    """Mirror Godot's disclosure-policy integer normalization before hashing."""
    if isinstance(value, Mapping):
        return {key: _normalize_policy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_policy(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def policy_hash(root: Path) -> str:
    """Hash the canonical disclosure policy, never project.godot."""
    scenario_path = root / "game-track/godot/data/sealed_lighthouse.json"
    scenario = read_json(scenario_path)
    if not isinstance(scenario, Mapping) or not isinstance(
        scenario.get("disclosure_policy"), Mapping
    ):
        raise ProtocolError(f"disclosure_policy missing: {scenario_path}")
    return digest(_normalize_policy(scenario["disclosure_policy"]))


def config_hash(root: Path) -> str:
    """Hash the exact canonical config file bytes required by protocol 1.1."""
    return sha256_file(root / "configs/npc-goal-recovery.json")


def source_project_config_hash(root: Path) -> str:
    return sha256_file(root / "game-track/godot/project.godot")


def _is_sha(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _project_relative(root: Path, value: Any) -> str | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    candidate = Path(value)
    if any(part == ".." for part in candidate.parts):
        return None
    try:
        resolved = (root / candidate).resolve()
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate.as_posix()


def _path(root: Path, packet_dir: Path | None, name: str) -> Path:
    return (
        packet_dir or root / "research/academic-pipeline/npc-goal-recovery/verified-run-006"
    ) / name


def _fixture_path(root: Path, fixture_ref: Any) -> tuple[Path, str] | None:
    if not isinstance(fixture_ref, str) or "#" not in fixture_ref:
        return None
    path_text, case_id = fixture_ref.split("#", 1)
    relative = _project_relative(root, path_text)
    if relative is None:
        return None
    if not relative.startswith("data/fixtures/npc-goal-recovery/validated-v5/"):
        return None
    fixture_path = root / relative
    if not case_id:
        return None
    return fixture_path, case_id


def fixture_case(assignment: Mapping[str, Any], root: Path | None = None) -> dict[str, Any]:
    """Load and normalize one source fixture case without retaining raw text."""
    root = root or ROOT
    resolved = _fixture_path(root, assignment.get("fixture_ref"))
    if resolved is None:
        raise ValueError("fixture_ref must be a project-relative path plus #case id")
    fixture_path, case_id = resolved
    if not fixture_path.is_file():
        raise ValueError(f"fixture missing: {fixture_path}")
    payload = read_json(fixture_path)
    if not isinstance(payload, Mapping) or not isinstance(payload.get("cases"), list):
        raise ProtocolError(f"invalid fixture packet: {fixture_path}")
    source = next(
        (
            case
            for case in payload["cases"]
            if isinstance(case, Mapping) and str(case.get("id")) == case_id
        ),
        None,
    )
    if not isinstance(source, Mapping):
        raise ProtocolError(f"fixture case missing: {assignment.get('fixture_ref')}")
    if str(source.get("id")) != str(assignment.get("case_id")):
        raise ValueError("assignment case_id does not match loaded fixture case id")
    case = copy.deepcopy(dict(source))
    utterance = case.pop("utterance", None)
    if not isinstance(utterance, str) or len(utterance) > 1000:
        raise ValueError(f"invalid fixture utterance: {assignment.get('fixture_ref')}")
    utterance_hash = hashlib.sha256(utterance.encode("utf-8")).hexdigest()
    if case.get("raw_utterance_sha256", utterance_hash) != utterance_hash:
        raise ValueError(f"fixture utterance hash mismatch: {assignment.get('fixture_ref')}")
    case["raw_utterance_sha256"] = utterance_hash
    source_kind = case.get("source_kind")
    if not isinstance(source_kind, str) or not source_kind:
        raise ValueError(f"fixture source_kind missing: {assignment.get('fixture_ref')}")
    observation = case.get("observation")
    if (
        not isinstance(observation, Mapping)
        or set(observation) != OBSERVATION_KEYS
        or any(type(v) is not bool for v in observation.values())
    ):
        raise ValueError(f"invalid fixture observation: {assignment.get('fixture_ref')}")
    stable_ref = f"{fixture_path.relative_to(root).as_posix()}#{case_id}"
    original_ref = str(assignment.get("fixture_ref"))
    if original_ref != stable_ref:
        raise ValueError(f"fixture_ref is not canonical project-relative path: {original_ref}")
    case["fixture_ref"] = stable_ref
    case["fixture_ref_sha256"] = hashlib.sha256(stable_ref.encode("utf-8")).hexdigest()
    return case


def assignment_key(row: Mapping[str, Any]) -> str:
    return digest({key: value for key, value in row.items() if key != "assignment_key"})


def persisted_has_raw_utterance(value: Any) -> bool:
    """Return true only when persisted data contains actual utterance text.

    Replay envelopes retain the literal ``[REDACTED]`` sentinel (and may retain
    ``null`` for non-request rows); neither is raw input.  Any other value under
    an ``utterance`` key is a provenance violation.
    """
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "utterance":
                if item is not None and item != "[REDACTED]":
                    return True
            elif persisted_has_raw_utterance(item):
                return True
        return False
    if isinstance(value, list):
        return any(persisted_has_raw_utterance(item) for item in value)
    return False


def _normalize_numbers(value: Any) -> Any:
    """Normalize Godot's JSON numeric floats for semantic record comparisons."""
    if isinstance(value, Mapping):
        return {key: _normalize_numbers(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_numbers(item) for item in value]
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _semantic_equal(left: Any, right: Any) -> bool:
    return _normalize_numbers(left) == _normalize_numbers(right)


def _engine_action_signature(action: Mapping[str, Any]) -> dict[str, Any]:
    after = action.get("state_ref_after")
    before = action.get("state_ref_before")
    observation = action.get("observation_after", action.get("observation"))
    return {
        "action_id": str(action.get("action_id", "")),
        "operation": str(action.get("operation", "")),
        "execution_mode": str(action.get("execution_mode", "")),
        "arguments": copy.deepcopy(action.get("arguments", {})),
        "status": str(action.get("status", "")),
        "observation": copy.deepcopy(observation),
        "state_ref_before": copy.deepcopy(before),
        "state_ref_after": copy.deepcopy(after),
        "engine_revision": after.get("revision") if isinstance(after, Mapping) else None,
        "state_hash_after": after.get("sha256") if isinstance(after, Mapping) else None,
    }


def _engine_reexecution_comparison(
    original: Mapping[str, Any], replayed: Mapping[str, Any]
) -> dict[str, Any]:
    def actions(report: Mapping[str, Any]) -> list[dict[str, Any]]:
        if "actions" in report and not isinstance(report["actions"], list):
            raise TypeError("engine_reexecution_actions_must_be_list")
        if "rows" in report and not isinstance(report["rows"], list):
            raise TypeError("engine_reexecution_actions_must_be_list")
        if "actions" in report:
            rows = report["actions"]
        elif "rows" in report:
            rows = report["rows"]
        else:
            rows = []
        return [_engine_action_signature(row) for row in rows]

    comparison = {
        "terminal_status": original.get("status", original.get("terminal_status"))
        == replayed.get("status", replayed.get("terminal_status")),
        "initial_state_ref": original.get("initial_state_ref") == replayed.get("initial_state_ref"),
        "final_state_ref": original.get("final_state_ref") == replayed.get("final_state_ref"),
        "decision_sha256": original.get("decision_sha256") == replayed.get("decision_sha256"),
        "actions": actions(original) == actions(replayed),
        "expected_negative_gates": original.get("expected_negative_gates", [])
        == replayed.get("expected_negative_gates", []),
    }
    comparison["passed"] = all(comparison.values())
    return comparison


def check_budget(actual: Any, expected: Mapping[str, Any], where: str, errors: list[str]) -> None:
    if not isinstance(actual, Mapping) or set(actual) != PROTOCOL_BUDGET_KEYS:
        errors.append(f"{where}: budget keys/shape mismatch")
        return
    if dict(actual) != dict(expected):
        errors.append(f"{where}: budget differs from frozen config")
    for key in ("input_tokens", "output_tokens", "cost"):
        if actual[key] is not None and (
            not isinstance(actual[key], (int, float)) or actual[key] < 0
        ):
            errors.append(f"{where}: invalid {key}")


def _state_ref(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == {"revision", "sha256"}
        and type(value["revision"]) is int
        and value["revision"] >= 0
        and _is_sha(value["sha256"])
    )


def _observation(value: Any) -> bool:
    return (
        isinstance(value, Mapping)
        and set(value) == OBSERVATION_KEYS
        and all(type(value[key]) is bool for key in OBSERVATION_KEYS)
    )


def _snapshot_ref(report: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for key in ("actual_state_ref", "initial_state_ref", "state_ref", "state_ref_before"):
        value = report.get(key)
        if isinstance(value, Mapping):
            return value
    snapshot = report.get("initial_public_snapshot")
    if isinstance(snapshot, Mapping) and isinstance(snapshot.get("state_ref"), Mapping):
        return snapshot["state_ref"]
    return None


def _engine_action_rows(report: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = report.get("actions", report.get("rows", []))
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def _native_final_observation(report: Mapping[str, Any]) -> Any:
    """Return the native terminal observation, never an editable record field."""
    final_snapshot = report.get("final_public_snapshot")
    if isinstance(final_snapshot, Mapping) and "observation" in final_snapshot:
        return final_snapshot.get("observation")
    rows = _engine_action_rows(report)
    if rows:
        terminal = rows[-1]
        if "observation_after" in terminal:
            return terminal.get("observation_after")
        if "observation" in terminal:
            return terminal.get("observation")
    observations = report.get("observations")
    if isinstance(observations, list) and observations:
        return observations[-1]
    return None


def _validate_action_transition(action: Mapping[str, Any], where: str, errors: list[str]) -> None:
    before = action.get("state_ref_before")
    after = action.get("state_ref_after")
    before_obs = action.get("observation_before")
    after_obs = action.get("observation_after", action.get("observation"))
    operation = str(action.get("operation", ""))
    status = str(action.get("status", ""))
    if not _state_ref(before) or not _state_ref(after):
        errors.append(f"{where}: action state_ref_before/state_ref_after missing or malformed")
        return
    if not _observation(before_obs) or not _observation(after_obs):
        errors.append(f"{where}: action observations missing or malformed")
        return
    # Native action rows do not carry engine_revision; result envelopes do.
    if "engine_revision" in action and action.get("engine_revision") != after["revision"]:
        errors.append(f"{where}: engine revision mismatch")
    same_state = dict(before) == dict(after)
    same_observation = dict(before_obs) == dict(after_obs)
    accepted = (
        action.get("result", {}).get("accepted")
        if isinstance(action.get("result"), Mapping)
        else None
    )
    if status == "APPLIED":
        if accepted is not True:
            errors.append(f"{where}: APPLIED action is not accepted")
        if operation in WORLD_OPERATIONS:
            if after["revision"] != before["revision"] + 1 or after["sha256"] == before["sha256"]:
                errors.append(
                    f"{where}: world APPLIED transition must increment revision and change hash"
                )
        elif (
            operation in DIALOGUE_OPERATIONS
            or action.get("execution_mode") == "dialogue"
            or operation in {"no_route", "no-route"}
        ):
            if not same_state or not same_observation:
                errors.append(f"{where}: dialogue/no-route APPLIED transition must be unchanged")
        elif not same_state or not same_observation:
            errors.append(f"{where}: unknown APPLIED operation changed canonical state")
    elif status in NON_APPLIED or status:
        if accepted is True:
            errors.append(f"{where}: non-applied action marked accepted")
        if not same_state or not same_observation:
            errors.append(f"{where}: non-applied transition changed state or observation")
    else:
        errors.append(f"{where}: action status missing")


def _validate_negative_gates(
    report: Mapping[str, Any],
    where: str,
    errors: list[str],
    required_controls: list[str] | None = None,
) -> None:
    gates = report.get("expected_negative_gates")
    required = list(required_controls or [])
    if gates is None:
        gates = []
    if not isinstance(gates, list):
        errors.append(f"{where}: negative gate list malformed")
        return
    if not required and gates:
        errors.append(f"{where}: negative gates declared without canonical controls")
    controls = [gate.get("control") if isinstance(gate, Mapping) else None for gate in gates]
    if required and controls != required:
        errors.append(f"{where}: negative gate coverage mismatch")
    for index, gate in enumerate(gates):
        if not isinstance(gate, Mapping) or gate.get("passed") is not True:
            errors.append(f"{where}: negative gate[{index}] failed")
            continue
        before, after = gate.get("state_ref_before"), gate.get("state_ref_after")
        if not _state_ref(before) or not _state_ref(after) or dict(before) != dict(after):
            errors.append(f"{where}: negative gate[{index}] changed canonical state")
        expected = str(gate.get("expected_status", ""))
        observed = str(gate.get("observed_status", ""))
        control = str(gate.get("control", ""))
        status_ok = observed == expected
        if control == "stale_revision" and expected == "STALE" and observed == "REJECTED":
            status_ok = True
        if control == "no_route":
            proof = (
                gate.get("physical_route_unreachable") is True and gate.get("no_world_step") is True
            )
            status_ok = status_ok or (
                expected == "NO_CANONICAL_ROUTE" and observed in {"NO_CANONICAL_ROUTE", "NO_ROUTE"}
            )
            if observed == "APPLIED":
                status_ok = expected == "NO_CANONICAL_ROUTE" and proof
            if not proof:
                errors.append(f"{where}: negative gate[{index}] no-route proof missing")
        if control == "cancelled" and expected == "CANCELLED" and observed == "ERROR":
            codes = gate.get("codes")
            status_ok = isinstance(codes, list) and {str(code) for code in codes} >= {
                "EPOCH_MISMATCH",
                "GENERATION_MISMATCH",
            }
        if expected and not status_ok:
            errors.append(f"{where}: negative gate[{index}] status mismatch")


def _artifact_path(
    root: Path, packet_dir: Path, value: Any, artifact_root: Path | None = None
) -> Path | None:
    """Resolve a recorded artifact reference to one member of the current packet.

    Relative references are packet-local.  Native commands may retain an absolute
    path from the recorded ``artifact_root``; that path is admitted only when it
    names a member below that declared root, then is rebased to the current packet
    directory.  Both forms pass through the same resolved containment check so
    relocation cannot turn a basename or outsider path into a valid artifact.
    """
    if not isinstance(value, str) or not value:
        return None
    packet = packet_dir.resolve()
    candidate = Path(value)
    try:
        if candidate.is_absolute():
            if artifact_root is None:
                return None
            recorded_root = artifact_root.resolve()
            recorded_path = candidate.resolve()
            relative = recorded_path.relative_to(recorded_root)
            path = (packet / relative).resolve()
        else:
            path = (packet / candidate).resolve()
        path.relative_to(packet)
    except (OSError, ValueError):
        return None
    return path if path.is_file() else None


def _artifact_exists(
    root: Path, value: Any, packet_dir: Path | None = None, artifact_root: Path | None = None
) -> bool:
    if packet_dir is None:
        if not isinstance(value, str) or not value:
            return False
        candidate = Path(value)
        return (candidate if candidate.is_absolute() else root / candidate).is_file()
    return _artifact_path(root, packet_dir, value, artifact_root) is not None


def _sidecar_json(
    root: Path, packet_dir: Path, value: Any, artifact_root: Path | None = None
) -> Mapping[str, Any] | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        return None
    path = _artifact_path(root, packet_dir, value, artifact_root)
    if path is None:
        return None
    try:
        payload = read_json(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, Mapping) else None


def _validate_input_file_hash(
    root: Path,
    packet_dir: Path,
    metadata: Mapping[str, Any],
    where: str,
    errors: list[str],
    artifact_root: Path | None = None,
) -> None:
    input_value = metadata.get("input_path")
    if not isinstance(input_value, str) or not input_value or Path(input_value).is_absolute():
        errors.append(f"{where}: native input_path must be packet-relative")
        return
    input_path = _artifact_path(root, packet_dir, input_value, artifact_root)
    if input_path is None:
        errors.append(f"{where}: native input artifact missing or outside packet")
        return
    actual = sha256_file(input_path)
    if (
        metadata.get("input_sha256_before") != actual
        or metadata.get("input_sha256_after") != actual
    ):
        errors.append(f"{where}: native input SHA does not match actual immutable file")
    if metadata.get("input_bytes_preserved") is not True:
        errors.append(f"{where}: native input bytes were not preserved")


def _command_input_path(
    root: Path, packet_dir: Path, command: Any, artifact_root: Path | None
) -> Path | None:
    if not isinstance(command, list):
        return None
    for index, token in enumerate(command[:-1]):
        if isinstance(token, str) and (
            token == "--npc-bootstrap" or token == "--npc-experiment" or token == "--npc-mode"
        ):
            return _artifact_path(root, packet_dir, command[index + 1], artifact_root)
    return None


def _stage_files(
    root: Path,
    packet_dir: Path,
    metadata: Mapping[str, Any],
    stage: str,
    where: str,
    errors: list[str],
    artifact_root: Path | None,
) -> tuple[Path | None, Path | None, Mapping[str, Any] | None, Any]:
    _validate_input_file_hash(root, packet_dir, metadata, where, errors, artifact_root)
    input_value = metadata.get("input_path")
    input_path = (
        _artifact_path(root, packet_dir, input_value, artifact_root)
        if isinstance(input_value, str) and not Path(input_value).is_absolute()
        else None
    )
    command_path = _command_input_path(root, packet_dir, metadata.get("command"), artifact_root)
    if input_path is None:
        errors.append(f"{where}: input artifact missing or outside packet")
    if command_path is None or input_path is None or command_path != input_path:
        errors.append(f"{where}: command input does not match metadata.input_path")
    sidecar_value = metadata.get("sidecar_path")
    sidecar_path = (
        _artifact_path(root, packet_dir, sidecar_value, artifact_root)
        if isinstance(sidecar_value, str) and not Path(sidecar_value).is_absolute()
        else None
    )
    if sidecar_path is None:
        errors.append(f"{where}: sidecar artifact missing or outside packet")
    elif input_path is not None:
        expected_suffix = ".bootstrap.json" if stage == "bootstrap" else ".result.json"
        if sidecar_path.name != input_path.name + expected_suffix:
            errors.append(f"{where}: sidecar_path has wrong suffix")
    sidecar = _sidecar_json(root, packet_dir, sidecar_value, artifact_root)
    if sidecar is None:
        errors.append(f"{where}: sidecar artifact missing or unreadable")
    embedded = metadata.get("trace")
    if not isinstance(embedded, Mapping):
        errors.append(f"{where}: embedded trace missing")
    elif sidecar is not None and sidecar != embedded:
        errors.append(f"{where}: sidecar does not match embedded trace")
    payload: Any = None
    if input_path is not None:
        try:
            payload = read_json(input_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{where}: input JSON unreadable: {exc}")
    return input_path, sidecar_path, sidecar, payload


def _required_negative_controls(case: Mapping[str, Any]) -> list[str]:
    mutations = case.get("mutations", [])
    return [str(item) for item in mutations] if isinstance(mutations, list) else []


def _validate_native_input(
    payload: Any,
    assignment: Mapping[str, Any],
    record: Mapping[str, Any],
    case: Mapping[str, Any],
    stage: str,
    where: str,
    errors: list[str],
    expected_hashes: Mapping[str, Any],
    check_decision: bool = True,
) -> None:
    if not isinstance(payload, Mapping):
        errors.append(f"{where}: native input must be an object")
        return
    for key in ("assignment_id", "fixture_ref", "fixture_input_sha256", "config_hash"):
        if payload.get(key) != assignment.get(key):
            errors.append(f"{where}: input {key} does not bind assignment")
    if payload.get("source_hashes") != dict(expected_hashes):
        errors.append(f"{where}: input source hashes mismatch")
    if payload.get("setup_operations") != case.get("setup_operations", []):
        errors.append(f"{where}: input setup recipe mismatch")
    if payload.get("seed_world_events") != case.get("seed_world_events", []):
        errors.append(f"{where}: input seed recipe mismatch")
    if stage == "bootstrap":
        if payload.get("mutations") != case.get("mutations", []):
            errors.append(f"{where}: bootstrap mutations mismatch fixture")
        return
    if check_decision:
        expected_controls = list(case.get("mutations", []))
        actual_mutations = payload.get("mutations")
        if (
            not isinstance(actual_mutations, list)
            or actual_mutations[: len(expected_controls)] != expected_controls
        ):
            errors.append(f"{where}: experiment mutations mismatch fixture")
        else:
            extras = actual_mutations[len(expected_controls) :]
            if len(extras) > 1 or any(
                not isinstance(item, Mapping)
                or item.get("code") != "fixture-playeraction"
                or not isinstance(item.get("operation"), str)
                for item in extras
            ):
                errors.append(f"{where}: experiment mutations contain unbound extras")
    expected_initial = {"state_ref": case.get("state_ref"), "observation": case.get("observation")}
    if not _semantic_equal(payload.get("initial_public_snapshot"), expected_initial):
        errors.append(f"{where}: input initial snapshot mismatch fixture")
    if not _semantic_equal(
        payload.get("initial_public_snapshot"),
        {
            "state_ref": record.get("state_ref_before"),
            "observation": record.get("observation_before", record.get("observation")),
        },
    ):
        errors.append(f"{where}: input initial snapshot mismatch record")
    if not _semantic_equal(payload.get("request"), record.get("request")):
        errors.append(f"{where}: input request mismatch record")
    if check_decision and not _semantic_equal(payload.get("decision"), record.get("decision")):
        errors.append(f"{where}: input decision mismatch record")


def _normalized_state_ref(value: Any) -> dict[str, Any] | None:
    if not _state_ref(value):
        return None
    return {"revision": int(value["revision"]), "sha256": str(value["sha256"])}


def _tamper_rejected_from_evidence(
    tamper_engine: Mapping[str, Any] | None,
    tamper_report: Mapping[str, Any] | None,
    tamper_rows: list[Mapping[str, Any]],
    canonical_ref: Mapping[str, Any] | None,
) -> bool:
    """Mirror the producer's strict process/sidecar negative-gate predicate."""
    if not isinstance(tamper_engine, Mapping) or not isinstance(tamper_report, Mapping):
        return False
    expected_ref = _normalized_state_ref(canonical_ref)
    if expected_ref is None or not tamper_rows:
        return False
    if not all(
        tamper_engine.get(key) is True
        for key in ("input_exists", "input_nonempty", "input_bytes_preserved")
    ):
        return False
    before_hash = tamper_engine.get("input_sha256_before")
    after_hash = tamper_engine.get("input_sha256_after")
    if not _is_sha(before_hash) or before_hash != after_hash:
        return False
    returncode = tamper_engine.get("returncode")
    if returncode not in (0, 1):
        return False
    process_status = str(tamper_engine.get("status", "")).lower()
    if (returncode == 0 and process_status != "completed") or (
        returncode == 1 and process_status != "failed"
    ):
        return False
    observed_statuses: set[str] = set()
    observed_codes: set[str] = set()
    for row in tamper_rows:
        if not isinstance(row, Mapping):
            return False
        status = str(row.get("status", "")).upper()
        observed_statuses.add(status)
        if status == "APPLIED" or status not in NON_APPLIED:
            return False
        result = row.get("result") if isinstance(row.get("result"), Mapping) else {}
        row_mutated = row.get("mutated")
        result_mutated = result.get("mutated")
        if (
            row_mutated is True
            or result_mutated is True
            or result.get("accepted") is True
            or (row_mutated is not False and result_mutated is not False)
        ):
            return False
        before = _normalized_state_ref(row.get("state_ref_before"))
        after = _normalized_state_ref(row.get("state_ref_after"))
        if before != expected_ref or after != expected_ref:
            return False
        for container in (row, result):
            codes = container.get("codes", []) if isinstance(container, Mapping) else []
            if not isinstance(codes, list):
                return False
            observed_codes.update(str(code) for code in codes)
    trace_codes = tamper_report.get("errors", [])
    if not isinstance(trace_codes, list):
        return False
    observed_codes.update(str(code) for code in trace_codes)
    trace_status = str(
        tamper_report.get("status", tamper_report.get("terminal_status", ""))
    ).upper()
    if trace_status:
        observed_statuses.add(trace_status)
    try:
        initial_ref = _normalized_state_ref(tamper_report.get("initial_state_ref"))
        final_ref = _normalized_state_ref(tamper_report.get("final_state_ref"))
    except (TypeError, ValueError):
        return False
    if initial_ref != expected_ref or final_ref != expected_ref:
        return False
    if "APPLIED" in observed_statuses or not (observed_statuses & TAMPER_REJECTION_STATUSES):
        return False
    if not (observed_codes & CANONICAL_TAMPER_CODES):
        return False
    return observed_codes <= CANONICAL_TAMPER_CODES | {"ACTION_NOT_APPLIED"}


def _core_rebased_replay_envelope(
    source: Mapping[str, Any], replay_row: Mapping[str, Any]
) -> dict[str, Any]:
    """Reproduce Core replay indexing/hash metadata without relaxing payload identity."""
    expected = copy.deepcopy(dict(source))
    expected.pop("hash", None)
    expected.pop("previous_hash", None)
    expected.pop("content_sha256", None)
    expected["sequence"] = replay_row.get("sequence")
    expected["delivery_index"] = replay_row.get("delivery_index")
    expected["content_sha256"] = digest(expected)
    expected["previous_hash"] = replay_row.get("previous_hash")
    expected["hash"] = digest(
        {
            "record": {
                key: value
                for key, value in expected.items()
                if key not in {"hash", "previous_hash"}
            },
            "previous_hash": expected["previous_hash"],
        }
    )
    return expected


def _record_has_native_action(record: Mapping[str, Any]) -> bool:
    """Return whether a completed record contains a native executed action."""
    engine = record.get("engine")
    if not isinstance(engine, Mapping):
        return False
    experiment = engine.get("experiment")
    if not isinstance(experiment, Mapping):
        return False
    trace = experiment.get("trace")
    if not isinstance(trace, Mapping):
        return False
    actions = trace.get("actions")
    return isinstance(actions, list) and bool(actions)


def _validate_result_ack_contract(record: Mapping[str, Any], where: str, errors: list[str]) -> None:
    if record.get("status") != "completed":
        return
    if not _record_has_native_action(record):
        return
    results = record.get("results")
    acks = record.get("acks")
    if not isinstance(results, list) or not isinstance(acks, list) or not results or not acks:
        errors.append(f"{where}: completed action result/ACK completion chain missing")
        return
    if len(acks) != len(results):
        errors.append(f"{where}: completed results/ACK count mismatch")
        return
    seen_result_keys: set[tuple[Any, Any]] = set()
    identity_keys = (
        "session_id",
        "session_epoch",
        "episode_id",
        "request_id",
        "scenario_id",
        "npc_id",
        "goal_id",
        "goal_version",
        "config_hash",
        "policy_hash",
    )
    for index, (result, ack) in enumerate(zip(results, acks)):
        if not isinstance(result, Mapping) or not isinstance(ack, Mapping):
            errors.append(f"{where}: result/ACK[{index}] must be objects")
            continue
        result_body = result.get("body") if isinstance(result.get("body"), Mapping) else {}
        ack_body = ack.get("body") if isinstance(ack.get("body"), Mapping) else {}
        result_key = (result_body.get("action_id"), result.get("content_sha256", digest(result)))
        repeated = result_key in seen_result_keys
        seen_result_keys.add(result_key)
        if ack_body.get("ack_for") != "result":
            errors.append(f"{where}: ACK[{index}] is not for a result")
        if index == 0 and ack_body.get("status") != "ACCEPTED":
            errors.append(f"{where}: first result ACK must be ACCEPTED")
        elif ack_body.get("status") == "DUPLICATE" and not repeated:
            errors.append(f"{where}: duplicate ACK without repeated result")
        elif ack_body.get("status") not in {"ACCEPTED", "DUPLICATE"}:
            errors.append(f"{where}: result ACK[{index}] status is not accepted")
        for key in identity_keys:
            if ack.get(key) != result.get(key):
                errors.append(f"{where}: ACK[{index}] identity mismatch for {key}")
        if ack.get("state_ref") != result.get("body", {}).get("state_ref"):
            errors.append(f"{where}: ACK[{index}] state identity mismatch")
        if (
            not isinstance(result.get("sequence"), int)
            or not isinstance(ack.get("sequence"), int)
            or ack["sequence"] <= result["sequence"]
        ):
            errors.append(f"{where}: ACK[{index}] ordering does not follow result")
        if (
            not isinstance(result.get("delivery_index"), int)
            or not isinstance(ack.get("delivery_index"), int)
            or ack["delivery_index"] <= result["delivery_index"]
        ):
            errors.append(f"{where}: ACK[{index}] delivery ordering does not follow result")


def _validate_engine(
    record: Mapping[str, Any],
    assignment: Mapping[str, Any],
    errors: list[str],
    where: str,
    expected_policy: str,
    root: Path,
    packet_dir: Path,
    artifact_root: Path | None = None,
) -> None:
    engine = record.get("engine")
    if not isinstance(engine, Mapping):
        if record.get("status") == "completed":
            errors.append(f"{where}: engine report missing")
        return
    case: Mapping[str, Any] = {}
    try:
        case = fixture_case(assignment, root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"{where}: fixture binding unavailable: {exc}")
    expected_hashes = {
        "config_hash": config_hash(root),
        "npc_protocol_config_sha256": config_hash(root),
        "source_project_config_sha256": source_project_config_hash(root),
        "source_schema_sha256": sha256_file(
            root / "game-track/schemas/npc-goal-recovery.schema.json"
        ),
        "policy_hash": expected_policy,
    }
    bootstrap = engine.get("bootstrap")
    experiment = engine.get("experiment")
    if not isinstance(bootstrap, Mapping):
        errors.append(f"{where}: bootstrap metadata missing")
        return
    _, _, bootstrap_sidecar, bootstrap_input = _stage_files(
        root, packet_dir, bootstrap, "bootstrap", f"{where}: bootstrap", errors, artifact_root
    )
    _validate_native_input(
        bootstrap_input,
        assignment,
        record,
        case,
        "bootstrap",
        f"{where}: bootstrap",
        errors,
        expected_hashes,
    )
    bootstrap_report = bootstrap.get("trace")
    if bootstrap.get("status") != "completed" or bootstrap.get("input_bytes_preserved") is not True:
        errors.append(f"{where}: completed record lacks completed bootstrap gate")
    if record.get("status") == "completed" and (
        type(bootstrap.get("returncode")) is not int or bootstrap.get("returncode") != 0
    ):
        errors.append(f"{where}: bootstrap returncode must be zero")
    if not isinstance(bootstrap_report, Mapping) or bootstrap_report.get("passed") is not True:
        errors.append(f"{where}: bootstrap sidecar gate failed")
    elif bootstrap_sidecar is not None and bootstrap_sidecar != bootstrap_report:
        errors.append(f"{where}: bootstrap sidecar does not match embedded trace")
    if isinstance(bootstrap_report, Mapping):
        if (
            bootstrap_report.get("policy_hash") != expected_policy
            or bootstrap_report.get("source_hashes") != expected_hashes
        ):
            errors.append(f"{where}: bootstrap policy/source binding failed")
        if not _semantic_equal(bootstrap_report.get("state_ref"), case.get("state_ref")):
            errors.append(f"{where}: bootstrap final state does not bind fixture")
    if engine.get("status") == "not_run" and record.get("status") == "assigned_failure":
        return
    if not isinstance(experiment, Mapping):
        errors.append(f"{where}: experiment metadata missing")
        return
    experiment_input_path, _, experiment_sidecar, experiment_input = _stage_files(
        root, packet_dir, experiment, "experiment", f"{where}: experiment", errors, artifact_root
    )
    _validate_native_input(
        experiment_input,
        assignment,
        record,
        case,
        "experiment",
        f"{where}: experiment",
        errors,
        expected_hashes,
    )
    if (
        experiment.get("status") != "completed"
        or experiment.get("input_bytes_preserved") is not True
    ):
        errors.append(f"{where}: completed record lacks completed Godot experiment")
    if record.get("status") == "completed" and (
        type(experiment.get("returncode")) is not int or experiment.get("returncode") != 0
    ):
        errors.append(f"{where}: experiment returncode must be zero")
    report = experiment.get("trace")
    if not isinstance(report, Mapping) or report.get("passed") is not True:
        errors.append(f"{where}: experiment sidecar stage/hash gate failed")
        return
    if experiment_sidecar is not None and experiment_sidecar != report:
        errors.append(f"{where}: experiment sidecar does not match embedded trace")
    if report.get("assignment_id") != assignment.get("assignment_id") or report.get(
        "fixture_ref"
    ) != assignment.get("fixture_ref"):
        errors.append(f"{where}: experiment assignment/fixture binding mismatch")
    if (
        report.get("policy_hash") != expected_policy
        or report.get("source_hashes") != expected_hashes
    ):
        errors.append(f"{where}: experiment policy/source binding failed")
    expected_snapshot = {
        "state_ref": record.get("state_ref_before"),
        "observation": record.get("observation_before", record.get("observation")),
    }
    if not _semantic_equal(report.get("initial_public_snapshot"), expected_snapshot):
        errors.append(f"{where}: native initial snapshot does not bind record")
    if not _semantic_equal(
        report.get("initial_public_snapshot"),
        {"state_ref": case.get("state_ref"), "observation": case.get("observation")},
    ):
        errors.append(f"{where}: native initial snapshot does not bind fixture")
    if not _semantic_equal(report.get("decision"), record.get("decision")):
        errors.append(f"{where}: native decision does not match record")
    if not _is_sha(report.get("decision_sha256")) or report.get("decision_sha256") != digest(
        report.get("decision")
    ):
        errors.append(f"{where}: native decision SHA does not match native decision")
    request_context = (
        experiment_input.get("request_context") if isinstance(experiment_input, Mapping) else None
    )
    if not isinstance(request_context, Mapping) or not _semantic_equal(
        report.get("request_context"), request_context
    ):
        errors.append(f"{where}: native request context does not match input")
    trace_request = report.get("request")
    identity_keys = (
        "request_id",
        "session_id",
        "session_epoch",
        "episode_id",
        "goal_id",
        "goal_version",
    )
    if (
        not isinstance(trace_request, Mapping)
        or not isinstance(request_context, Mapping)
        or any(trace_request.get(key) != request_context.get(key) for key in identity_keys)
    ):
        errors.append(f"{where}: native request identity does not match input")
    if _snapshot_ref(report) != record.get("state_ref_before"):
        errors.append(f"{where}: experiment initial state binding failed")
    if report.get("final_state_ref") != record.get("state_ref_after"):
        errors.append(f"{where}: experiment final state binding failed")
    rows = _engine_action_rows(report)
    for index, action in enumerate(rows):
        if not action.get("action_id") or not action.get("operation"):
            errors.append(f"{where}: action[{index}] missing identity")
        _validate_action_transition(action, f"{where}: action[{index}]", errors)
    _validate_negative_gates(report, where, errors, _required_negative_controls(case))
    replay = engine.get("replay")
    comparison = engine.get("replay_comparison")
    if (
        not isinstance(replay, Mapping)
        or replay.get("replay_kind") != "engine_fixture_reexecution"
        or replay.get("mode") != "experiment"
    ):
        errors.append(f"{where}: native replay is not truthful engine_fixture_reexecution")
    replay_input_path = None
    replay_report: Mapping[str, Any] | None = None
    replay_input: Any = None
    if isinstance(replay, Mapping):
        replay_input_path, _, replay_sidecar, replay_input = _stage_files(
            root, packet_dir, replay, "replay", f"{where}: replay", errors, artifact_root
        )
        _validate_native_input(
            replay_input,
            assignment,
            record,
            case,
            "experiment",
            f"{where}: replay",
            errors,
            expected_hashes,
        )
        replay_report = replay.get("trace") if isinstance(replay.get("trace"), Mapping) else None
        if isinstance(replay_report, Mapping):
            if replay_report.get("assignment_id") != assignment.get(
                "assignment_id"
            ) or replay_report.get("fixture_ref") != assignment.get("fixture_ref"):
                errors.append(f"{where}: replay assignment/fixture binding mismatch")
            if not _semantic_equal(
                replay_report.get("decision"), report.get("decision")
            ) or replay_report.get("decision_sha256") != report.get("decision_sha256"):
                errors.append(f"{where}: replay decision binding mismatch")
        if experiment_input_path is not None and replay_input_path is not None:
            try:
                if experiment_input_path.read_bytes() != replay_input_path.read_bytes():
                    errors.append(
                        f"{where}: native replay input bytes differ from experiment input"
                    )
            except OSError as exc:
                errors.append(f"{where}: native replay input bytes unreadable: {exc}")
        if (
            isinstance(replay_report, Mapping)
            and replay_sidecar is not None
            and replay_sidecar != replay_report
        ):
            errors.append(f"{where}: native replay sidecar does not match embedded trace")
    if record.get("status") == "completed" and isinstance(replay, Mapping):
        if replay.get("status") != "completed":
            errors.append(
                f"{where}: native replay completion signals incomplete: status must be completed"
            )
        returncode = replay.get("returncode")
        if type(returncode) is not int or returncode != 0:
            errors.append(
                f"{where}: native replay completion signals incomplete: "
                "native replay completion returncode must be 0"
            )
        if not isinstance(replay_report, Mapping) or replay_report.get("passed") is not True:
            errors.append(
                f"{where}: native replay completion signals incomplete: "
                "native replay trace.passed must be true"
            )
        if replay.get("input_bytes_preserved") is not True:
            errors.append(
                f"{where}: native replay completion signals incomplete: "
                "input_bytes_preserved must be true"
            )
    if not isinstance(replay_report, Mapping):
        errors.append(f"{where}: native replay sidecar report missing")
    else:
        try:
            actual_comparison = _engine_reexecution_comparison(report, replay_report)
        except (AttributeError, TypeError, ValueError) as exc:
            errors.append(f"{where}: invalid reexecution comparison: {exc}")
        else:
            if comparison != actual_comparison:
                errors.append(f"{where}: embedded replay comparison does not match actual sidecars")
            if actual_comparison.get("passed") is not True:
                errors.append(f"{where}: immutable engine fixture reexecution comparison failed")
    tamper = engine.get("tamper_reexecution", engine.get("tamper_replay"))
    decision_steps = (
        report.get("decision", {}).get("body", {}).get("steps", [])
        if isinstance(report.get("decision"), Mapping)
        else []
    )
    tamper_applicable = bool(rows or decision_steps)
    if tamper_applicable:
        if not isinstance(tamper, Mapping):
            errors.append(f"{where}: tamper replay missing for action/decision evidence")
        else:
            _, _, tamper_sidecar, tamper_input = _stage_files(
                root, packet_dir, tamper, "tamper", f"{where}: tamper", errors, artifact_root
            )
            _validate_native_input(
                tamper_input,
                assignment,
                record,
                case,
                "tamper",
                f"{where}: tamper",
                errors,
                expected_hashes,
                check_decision=False,
            )
            if isinstance(tamper_input, Mapping) and tamper_input.get("mutations") != []:
                errors.append(f"{where}: tamper probe must omit inherited fixture mutations")
            if isinstance(experiment_input, Mapping) and isinstance(tamper_input, Mapping):
                original_steps = (
                    experiment_input.get("decision", {}).get("body", {}).get("steps", [])
                    if isinstance(experiment_input.get("decision"), Mapping)
                    else []
                )
                altered_steps = (
                    tamper_input.get("decision", {}).get("body", {}).get("steps", [])
                    if isinstance(tamper_input.get("decision"), Mapping)
                    else []
                )
                if (
                    len(original_steps) != len(altered_steps)
                    or not original_steps
                    or not isinstance(original_steps[0], Mapping)
                    or not isinstance(altered_steps[0], Mapping)
                ):
                    errors.append(f"{where}: tamper decision steps malformed")
                else:
                    expected_tamper = copy.deepcopy(experiment_input)
                    expected_tamper["mutations"] = []
                    expected_tamper["decision"]["body"]["steps"][0]["operation"] = altered_steps[
                        0
                    ].get("operation")
                    if not _semantic_equal(expected_tamper, tamper_input) or _semantic_equal(
                        expected_tamper, experiment_input
                    ):
                        errors.append(
                            f"{where}: tamper input did not isolate one decision operation change"
                        )
            tamper_report = (
                tamper.get("trace") if isinstance(tamper.get("trace"), Mapping) else None
            )
            if (
                tamper_sidecar is not None
                and tamper_report is not None
                and tamper_sidecar != tamper_report
            ):
                errors.append(f"{where}: tamper sidecar does not match embedded trace")
            tamper_rows = (
                _engine_action_rows(tamper_report) if isinstance(tamper_report, Mapping) else []
            )
            if not isinstance(tamper_report, Mapping) or tamper.get("status") not in {
                "completed",
                "failed",
            }:
                errors.append(f"{where}: semantic tamper replay report missing")
            if not tamper_rows:
                errors.append(f"{where}: semantic tamper replay has no action rejection")
            actual_tamper_rejected = _tamper_rejected_from_evidence(
                tamper,
                tamper_report,
                tamper_rows,
                record.get("state_ref_before")
                if isinstance(record.get("state_ref_before"), Mapping)
                else None,
            )
            stored_tamper_rejected = (
                record.get("replay", {}).get("godot_tamper_rejected")
                if isinstance(record.get("replay"), Mapping)
                else None
            )
            if record.get("status") == "completed" and actual_tamper_rejected is not True:
                errors.append(f"{where}: completed tamper replay did not prove canonical rejection")
            if stored_tamper_rejected is not actual_tamper_rejected:
                errors.append(
                    f"{where}: godot_tamper_rejected does not match actual tamper evidence"
                )
            for index, action in enumerate(tamper_rows):
                _validate_action_transition(action, f"{where}: tamper action[{index}]", errors)
                if (
                    str(action.get("status")) not in NON_APPLIED
                    or action.get("result", {}).get("accepted") is True
                    or action.get("result", {}).get("mutated") is True
                ):
                    errors.append(
                        f"{where}: tamper action[{index}] was not rejected without world write"
                    )
    elif tamper is not None:
        errors.append(f"{where}: tamper replay supplied without original action/decision step")


def _replay_classes(record: Mapping[str, Any]) -> tuple[str, str]:
    replay = record.get("replay") if isinstance(record.get("replay"), Mapping) else {}
    python = replay.get("python") if isinstance(replay.get("python"), Mapping) else {}
    if not python:
        python_class = "python_unavailable"
    elif python.get("valid") is True:
        python_class = "python_eligible"
    else:
        python_class = "python_failed"
    engine = record.get("engine") if isinstance(record.get("engine"), Mapping) else {}
    godot = engine.get("replay") if isinstance(engine.get("replay"), Mapping) else {}
    comparison = (
        engine.get("replay_comparison")
        if isinstance(engine.get("replay_comparison"), Mapping)
        else None
    )
    native_trace = godot.get("trace")
    godot_completion = (
        godot.get("status") == "completed"
        and type(godot.get("returncode")) is int
        and godot.get("returncode") == 0
        and isinstance(native_trace, Mapping)
        and native_trace.get("passed") is True
        and godot.get("input_bytes_preserved") is True
    )
    godot_eligible = (
        godot_completion and isinstance(comparison, Mapping) and comparison.get("passed") is True
    )
    godot_evidence = bool(godot) or isinstance(comparison, Mapping)
    if godot_eligible:
        godot_class = "godot_eligible"
    elif godot_evidence and (
        godot.get("available") is not False or isinstance(comparison, Mapping)
    ):
        godot_class = "godot_failed"
    else:
        godot_class = "godot_unavailable"
    return python_class, godot_class


def _validate_replay_report(
    replay_report: Any,
    packet: str,
    packet_dir: Path,
    assignment_map: Mapping[str, Mapping[str, Any]],
    records: list[Mapping[str, Any]],
    errors: list[str],
) -> None:
    if not isinstance(replay_report, Mapping):
        errors.append("replay report must be an object")
        return
    if set(replay_report) != REPLAY_REPORT_KEYS:
        errors.append("replay report schema keys mismatch")
        return
    if replay_report.get("schema_version") != "npc-goal-recovery/replay-1":
        errors.append("replay report schema version mismatch")
    scope = replay_report.get("packet_id")
    if scope not in {packet, "NPC-ALL"}:
        errors.append("replay report packet scope mismatch")
        return
    if type(replay_report.get("model_calls")) is not int or replay_report.get("model_calls") != 0:
        errors.append("replay report model_calls must be zero")
    rows = replay_report.get("rows")
    denominators = replay_report.get("denominators")
    if (
        not isinstance(rows, list)
        or not isinstance(denominators, Mapping)
        or set(denominators) != REPLAY_DENOMINATOR_KEYS
    ):
        errors.append("replay report row/denominator schema mismatch")
        return
    scope_records: dict[str, Mapping[str, Any]] = {
        str(row.get("assignment_id")): row for row in records
    }
    expected_ids = set(scope_records)
    if scope == "NPC-ALL":
        other_packet = "NPC-ENG1" if packet == "NPC-SCR1" else "NPC-SCR1"
        other_manifest_path = packet_dir / (
            "engineering-assignment-manifest.json"
            if other_packet == "NPC-ENG1"
            else "screening-assignment-manifest.json"
        )
        other_result_path = packet_dir / (
            "engineering-results.jsonl" if other_packet == "NPC-ENG1" else "screening-results.jsonl"
        )
        try:
            other_manifest = read_json(other_manifest_path)
            other_assignments = other_manifest.get("assignments", [])
            if not isinstance(other_assignments, list):
                raise TypeError("assignments missing")
            other_ids = [
                str(item.get("assignment_id"))
                for item in other_assignments
                if isinstance(item, Mapping)
            ]
            expected_ids.update(other_ids)
            if other_result_path.is_file():
                for row in load_jsonl(other_result_path):
                    scope_records[str(row.get("assignment_id"))] = row
            else:
                errors.append("global replay scope requires the other packet results")
        except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"global replay scope unavailable: {exc}")
    row_map: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows):
        where = f"replay-results row[{index}]"
        if not isinstance(row, Mapping) or set(row) != REPLAY_ROW_KEYS:
            errors.append(f"{where}: exact row schema mismatch")
            continue
        aid = row.get("assignment_id")
        if not isinstance(aid, str) or aid in row_map:
            errors.append(f"{where}: duplicate or invalid assignment id")
            continue
        row_map[aid] = row
        record = scope_records.get(aid)
        if record is None:
            errors.append(f"{where}: assignment outside replay scope")
            continue
        if row.get("status") != record.get("status") or row.get("assigned_failure") is not (
            record.get("status") == "assigned_failure"
        ):
            errors.append(f"{where}: status does not match persisted record")
        expected_python = (
            record.get("replay", {}).get("python", {})
            if isinstance(record.get("replay"), Mapping)
            else {}
        )
        expected_godot = (
            record.get("engine", {}).get("replay", {})
            if isinstance(record.get("engine"), Mapping)
            else {}
        )
        if row.get("python") != expected_python:
            errors.append(f"{where}: python replay payload mismatch")
        if row.get("godot") != expected_godot:
            errors.append(f"{where}: godot replay payload mismatch")
        if type(row.get("model_calls")) is not int or row.get("model_calls") != 0:
            errors.append(f"{where}: model_calls must be zero")
    if set(row_map) != expected_ids:
        errors.append("replay-results assignment rowset is incomplete, duplicated, or out of scope")
    computed = {key: 0 for key in REPLAY_DENOMINATOR_KEYS}
    for aid, record in scope_records.items():
        if aid not in expected_ids:
            continue
        python_class, godot_class = _replay_classes(record)
        computed[python_class] += 1
        computed[godot_class] += 1
    if dict(denominators) != computed:
        errors.append("replay-results denominators do not match independently recomputed records")


def _validate_publish_records(
    records: list[Mapping[str, Any]], packet: str, run_mode: Any, errors: list[str]
) -> None:
    if run_mode != "publish" or packet != "NPC-SCR1":
        return
    for index, record in enumerate(records):
        where = f"record[{index}]"
        attempts = record.get("cli_exec_attempts")
        if not isinstance(attempts, list):
            errors.append(f"{where}: cli_exec_attempts must be a list")
            continue
        model_calls = record.get("model_calls")
        if type(model_calls) is not int or model_calls != len(attempts):
            errors.append(f"{where}: model_calls does not equal actual CLI attempts")
        if record.get("arm") == "P":
            if len(attempts) != 1:
                errors.append(
                    f"{where}: publish P assignment must have exactly one codex exec attempt"
                )
            else:
                attempt = attempts[0]
                request = (
                    record.get("request") if isinstance(record.get("request"), Mapping) else {}
                )
                if (
                    not isinstance(attempt, Mapping)
                    or attempt.get("schema_version") != "codex-exec-attempt/1"
                    or attempt.get("operation") != "exec"
                    or attempt.get("runner_injected") is not False
                    or attempt.get("tool_policy_enforced") is not True
                    or type(attempt.get("disabled_feature_count")) is not int
                    or attempt.get("disabled_feature_count") <= 0
                    or attempt.get("request_id") != request.get("request_id")
                ):
                    errors.append(f"{where}: publish codex execution evidence is not policy-bound")
        elif record.get("arm") in {"R", "O"} and (model_calls != 0 or attempts):
            errors.append(f"{where}: rule/reference publish assignment must have zero model calls")
        failures = record.get("failure")
        if isinstance(failures, list) and any(
            isinstance(failure, Mapping) and failure.get("code") == "model_skipped"
            for failure in failures
        ):
            errors.append(f"{where}: model skip is forbidden in publish mode")


def _expected_assignments(
    root: Path, packet: str
) -> tuple[set[tuple[str, str, int]], list[dict[str, Any]]]:
    fixture = (
        root
        / "data/fixtures/npc-goal-recovery/validated-v5"
        / ("engineering.json" if packet == "NPC-ENG1" else "screening.json")
    )
    payload = read_json(fixture)
    cases = payload.get("cases", []) if isinstance(payload, Mapping) else []
    expected: set[tuple[str, str, int]] = set()
    for case in cases:
        if not isinstance(case, Mapping):
            continue
        arms = tuple(case.get("arms", ("R",))) if packet == "NPC-ENG1" else tuple(ARMS)
        repetitions = int(case.get("repetitions", 1)) if packet == "NPC-ENG1" else 2
        for arm in arms:
            for repetition in range(1, repetitions + 1):
                expected.add((str(case.get("id")), str(arm), repetition))
    return expected, [dict(case) for case in cases if isinstance(case, Mapping)]


def _validate_fixture_packet(root: Path, packet: str, errors: list[str]) -> None:
    fixture = (
        root
        / "data/fixtures/npc-goal-recovery/validated-v5"
        / ("engineering.json" if packet == "NPC-ENG1" else "screening.json")
    )
    try:
        payload = read_json(fixture)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"fixture packet unreadable: {fixture}: {exc}")
        return
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version") != "npc-goal-recovery/validated-v5"
        or payload.get("packet_id") != packet
    ):
        errors.append(f"fixture schema or packet mismatch: {fixture}")
        return
    cases = payload.get("cases")
    expected_count = 16 if packet == "NPC-ENG1" else 12
    if not isinstance(cases, list) or len(cases) != expected_count:
        errors.append(f"fixture case count must be {expected_count}: {fixture}")
        return
    expected_prefix = "ENG-" if packet == "NPC-ENG1" else "SCR-"
    for case in cases:
        if not isinstance(case, Mapping) or not str(case.get("id", "")).startswith(expected_prefix):
            errors.append(f"fixture case identity prefix mismatch: {fixture}")
            break


def validate_packet(
    packet: str, root: Path, packet_dir: Path | None = None
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    packet_dir = (
        packet_dir or root / "research/academic-pipeline/npc-goal-recovery/verified-run-006"
    )
    artifact_root: Path | None = None
    config_path = root / "configs/npc-goal-recovery.json"
    schema_path = root / "game-track/schemas/npc-goal-recovery.schema.json"
    config_digest = config_hash(root)
    schema_digest = sha256_file(schema_path)
    _validate_fixture_packet(root, packet, errors)
    project_digest = source_project_config_hash(root)
    expected_policy = policy_hash(root)
    config = read_json(config_path)
    expected_budget = {key: config.get("budget", {}).get(key) for key in PROTOCOL_BUDGET_KEYS}
    manifest_path = _path(
        root,
        packet_dir,
        "engineering-assignment-manifest.json"
        if packet == "NPC-ENG1"
        else "screening-assignment-manifest.json",
    )
    result_path = _path(
        root,
        packet_dir,
        "engineering-results.jsonl" if packet == "NPC-ENG1" else "screening-results.jsonl",
    )
    aggregate_path = _path(
        root, packet_dir, "engineering-aggregate.json" if packet == "NPC-ENG1" else "aggregate.json"
    )
    source_manifest_path = _path(root, packet_dir, "source-manifest.json")
    expected_count = EXPECTED_COUNTS[packet]
    if source_manifest_path.is_file():
        source_manifest_probe = read_json(source_manifest_path)
        if isinstance(source_manifest_probe, Mapping) and isinstance(
            source_manifest_probe.get("artifact_root"), str
        ):
            artifact_root = Path(source_manifest_probe["artifact_root"]).resolve()
    if not manifest_path.is_file():
        error = f"missing manifest: {manifest_path}"
        return {
            "packet_id": packet,
            "valid": False,
            "publishable": False,
            "run_mode": None,
            "errors": [error],
        }, [error]
    manifest = read_json(manifest_path)
    source_manifest = read_json(source_manifest_path) if source_manifest_path.is_file() else {}
    raw_test_only = (
        source_manifest.get("test_only", False) if isinstance(source_manifest, Mapping) else False
    )
    test_only = raw_test_only if type(raw_test_only) is bool else False
    if type(raw_test_only) is not bool:
        errors.append("source manifest test_only must be a boolean")
    run_mode = source_manifest.get("run_mode") if isinstance(source_manifest, Mapping) else None
    if run_mode not in {"dry_run", "preflight", "publish"}:
        errors.append("source manifest run_mode must be dry_run, preflight, or publish")

    if not isinstance(manifest, Mapping):
        errors.append("manifest must be an object")
        manifest = {}
    if (
        manifest.get("schema_version") != PACKET_SCHEMA_VERSION
        or manifest.get("packet_id") != packet
    ):
        errors.append("manifest schema or packet id mismatch")
    for key, expected in (
        ("config_hash", config_digest),
        ("npc_protocol_config_sha256", config_digest),
        ("source_project_config_sha256", project_digest),
        ("source_schema_sha256", schema_digest),
        ("policy_hash", expected_policy),
    ):
        if manifest.get(key) != expected:
            errors.append(f"manifest {key} mismatch")
    check_budget(manifest.get("budget"), expected_budget, "manifest", errors)
    claims = manifest.get("claim_boundary", manifest.get("claims"))
    if claims != EXPECTED_CLAIMS:
        errors.append("manifest claim boundary mismatch")
    assignments = (
        manifest.get("assignments") if isinstance(manifest.get("assignments"), list) else []
    )
    if len(assignments) != expected_count or manifest.get("assignment_count") != expected_count:
        errors.append(f"manifest assignment count must be {expected_count}")
    expected_ids, _cases = _expected_assignments(root, packet)
    assignment_map: dict[str, Mapping[str, Any]] = {}
    seen_tuples: set[tuple[str, str, int]] = set()
    for index, assignment in enumerate(assignments):
        where = f"assignment[{index}]"
        if not isinstance(assignment, Mapping):
            errors.append(f"{where}: not an object")
            continue
        if not REQUIRED_ASSIGNMENT_KEYS.issubset(set(assignment)):
            errors.append(f"{where}: required key set mismatch")
        aid = str(assignment.get("assignment_id", ""))
        if aid in assignment_map:
            errors.append(f"{where}: duplicate assignment id")
        assignment_map[aid] = assignment
        fixture_ref_path = str(assignment.get("fixture_ref", "")).split("#", 1)[0]
        if _project_relative(root, fixture_ref_path) is None:
            errors.append(f"{where}: fixture_ref must be project-relative")
        canonical_fixture_path = (
            "data/fixtures/npc-goal-recovery/validated-v5/engineering.json"
            if packet == "NPC-ENG1"
            else "data/fixtures/npc-goal-recovery/validated-v5/screening.json"
        )
        if fixture_ref_path != canonical_fixture_path:
            errors.append(f"{where}: fixture_ref does not bind packet canonical fixture")
        case_id = str(assignment.get("case_id", ""))
        arm = str(assignment.get("arm", ""))
        repetition = assignment.get("repetition")
        tuple_key = (case_id, arm, repetition) if type(repetition) is int else (case_id, arm, -1)
        seen_tuples.add(tuple_key)
        if tuple_key not in expected_ids:
            errors.append(f"{where}: omitted/swapped assignment identity")
        if assignment.get("packet_id") != packet or arm not in ARMS:
            errors.append(f"{where}: identity/arm mismatch")
        if assignment.get("assignment_key") != assignment_key(assignment):
            errors.append(f"{where}: assignment key mismatch")
        for key, expected in (
            ("config_hash", config_digest),
            ("npc_protocol_config_sha256", config_digest),
            ("source_project_config_sha256", project_digest),
            ("source_schema_sha256", schema_digest),
            ("policy_hash", expected_policy),
        ):
            if assignment.get(key) != expected:
                errors.append(f"{where}: {key} mismatch")
        check_budget(assignment.get("budget"), expected_budget, where, errors)
        if assignment.get("independent_source") is not False:
            errors.append(f"{where}: independent source must be false")
        try:
            case = fixture_case(assignment, root)
            if (
                assignment.get("seed") != case.get("seed")
                or assignment.get("source_kind") != case.get("source_kind")
                or assignment.get("utterance_source_kind") != case.get("source_kind")
            ):
                errors.append(f"{where}: source/seed does not bind fixture case")
            if assignment.get("fixture_input_sha256") != digest(case):
                errors.append(f"{where}: fixture input hash mismatch")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{where}: {exc}")
    if seen_tuples != expected_ids:
        errors.append("manifest assignment set is incomplete or contains swapped rows")
    if isinstance(source_manifest, Mapping):
        for key, expected in (
            ("config_hash", config_digest),
            ("npc_protocol_config_sha256", config_digest),
            ("source_project_config_sha256", project_digest),
            ("source_schema_sha256", schema_digest),
            ("policy_hash", expected_policy),
        ):
            if source_manifest.get(key) != expected:
                errors.append(f"source manifest {key} mismatch")
        before_hashes = source_manifest.get("runtime_source_hashes_before")
        after_hashes = source_manifest.get("runtime_source_hashes_after")
        expected_runtime = runtime_source_hashes(root)
        if before_hashes != expected_runtime:
            errors.append(
                f"source manifest runtime_source_hashes_before mismatch: {source_manifest_path} (FIX)"
            )
        if after_hashes != expected_runtime:
            errors.append(
                f"source manifest runtime_source_hashes_after mismatch: {source_manifest_path} (FIX)"
            )
        if source_manifest.get("runtime_sources_unchanged") is not True:
            errors.append("source manifest runtime_sources_unchanged must be true")
        if source_manifest.get("source_project_config_sha256_after") != project_digest:
            errors.append("source manifest source_project_config_sha256_after mismatch")
        if source_manifest.get("source_project_unchanged") is not True:
            errors.append("source manifest source_project_unchanged must be true")
    else:
        errors.append("source manifest missing")

    records: list[dict[str, Any]] = []
    if not result_path.is_file():
        errors.append(f"missing results: {result_path}")
    else:
        try:
            records = load_jsonl(result_path)
        except ValueError as exc:
            errors.append(str(exc))
    record_map: dict[str, Mapping[str, Any]] = {}
    for index, record in enumerate(records):
        where = f"record[{index}]"
        aid = str(record.get("assignment_id", ""))
        if aid in record_map:
            errors.append(f"{where}: duplicate assignment result")
        record_map[aid] = record
        assignment = assignment_map.get(aid)
        if assignment is None:
            errors.append(f"{where}: result has no assignment")
            continue
        for identity_key in (
            "packet_id",
            "case_id",
            "arm",
            "repetition",
            "fixture_ref",
            "fixture_input_sha256",
            "seed",
        ):
            if record.get(identity_key) != assignment.get(identity_key):
                errors.append(f"{where}: assignment identity mismatch for {identity_key}")
        if record.get("arm") not in ARMS:
            errors.append(f"{where}: invalid record arm")
        if record.get("record_schema_version") != RECORD_SCHEMA_VERSION or record.get(
            "record_sha256"
        ) != digest({key: value for key, value in record.items() if key != "record_sha256"}):
            errors.append(f"{where}: record schema/hash mismatch")
        if record.get("fixture_ref") != assignment.get("fixture_ref") or record.get(
            "fixture_input_sha256"
        ) != assignment.get("fixture_input_sha256"):
            errors.append(f"{where}: fixture binding mismatch")
        if persisted_has_raw_utterance(record):
            errors.append(f"{where}: raw utterance persisted")
        check_budget(record.get("budget"), expected_budget, where, errors)
        if record.get("claim_boundary") != EXPECTED_CLAIMS:
            errors.append(f"{where}: claim boundary mismatch")
        provenance = record.get("provenance")
        if not isinstance(provenance, Mapping) or provenance.get("independent_source") is not False:
            errors.append(f"{where}: provenance independent_source must be false")
        if isinstance(provenance, Mapping):
            for key, expected in (
                ("config_hash", config_digest),
                ("npc_protocol_config_sha256", config_digest),
                ("source_project_config_sha256", project_digest),
                ("source_schema_sha256", schema_digest),
                ("policy_hash", expected_policy),
            ):
                if provenance.get(key) != expected:
                    errors.append(f"{where}: provenance {key} mismatch")
        hashes = record.get("hashes")
        if not isinstance(hashes, Mapping) or hashes.get("config_hash") != config_digest:
            errors.append(f"{where}: record config hash missing/mismatch")
            hashes = {}
        before = record.get("state_ref_before")
        after = record.get("state_ref_after")
        trace = (
            record.get("engine", {}).get("experiment", {}).get("trace")
            if isinstance(record.get("engine"), Mapping)
            else None
        )
        if not isinstance(trace, Mapping):
            trace = {}
        before_obs = record.get("observation_before", record.get("observation"))
        after_obs = record.get("observation_after")
        native_final_obs = _native_final_observation(trace)
        if record.get("status") == "completed":
            if native_final_obs is None:
                errors.append(f"{where}: completed record requires native final observation")
            else:
                if not _observation(native_final_obs):
                    errors.append(f"{where}: native final observation is malformed")
                if record.get("observation_after") is not None and not _semantic_equal(
                    record.get("observation_after"), native_final_obs
                ):
                    errors.append(
                        f"{where}: observation_after does not bind native final observation"
                    )
                after_obs = native_final_obs
        if record.get("status") != "completed" and after_obs is None:
            final_snapshot = (
                trace.get("final_public_snapshot")
                if isinstance(trace.get("final_public_snapshot"), Mapping)
                else None
            )
            after_obs = (
                final_snapshot.get("observation") if isinstance(final_snapshot, Mapping) else None
            )
            if (
                after_obs is None
                and isinstance(trace.get("observations"), list)
                and trace["observations"]
            ):
                after_obs = trace["observations"][-1]
        if record.get("status") == "completed":
            if not _state_ref(before) or not _state_ref(after):
                errors.append(f"{where}: completed record lacks canonical before/after state refs")
            if not _observation(before_obs) or not _observation(after_obs):
                errors.append(
                    f"{where}: completed record lacks canonical before/after observations"
                )
            if (
                isinstance(after_obs, Mapping)
                and record.get("goal_reached") is not None
                and record.get("goal_reached") != after_obs.get("goal_reached")
            ):
                if native_final_obs is not None:
                    errors.append(f"{where}: goal_reached does not bind native final observation")
                else:
                    errors.append(f"{where}: fabricated goal counter")
            for field in (
                "bootstrap_input_sha256_before",
                "bootstrap_input_sha256_after",
                "experiment_input_sha256_before",
                "experiment_input_sha256_after",
            ):
                if not _is_sha(hashes.get(field)) or hashes.get(field) != hashes.get(
                    field.replace("_before", "_after")
                ):
                    errors.append(f"{where}: immutable input hash missing/mismatch for {field}")
        if not isinstance(record.get("failure", []), list) or any(
            not isinstance(failure, Mapping) or not isinstance(failure.get("code"), str)
            for failure in record.get("failure", [])
        ):
            errors.append(f"{where}: failure list/code shape mismatch")
        elif record.get("status") == "assigned_failure" and not record.get("failure"):
            errors.append(f"{where}: assigned failure has no retained failure code")
        for field in ("goal_reached", "recovery_eligible", "recovery_unreachable"):
            if record.get(field) is not None and type(record.get(field)) is not bool:
                errors.append(f"{where}: {field} must be boolean or null")
        decision = record.get("decision")
        envelopes: list[Mapping[str, Any]] = []
        if decision is not None:
            try:
                validate_envelope(decision, expected_message_type="decision")
                envelopes.append(decision)
                backend = {"P": "codex", "R": "rule", "O": "reference"}.get(str(record.get("arm")))
                if (
                    decision.get("config_hash") != config_digest
                    or decision.get("policy_hash") != expected_policy
                    or decision.get("provenance", {}).get("arm") != record.get("arm")
                    or decision.get("provenance", {}).get("backend") != backend
                ):
                    errors.append(f"{where}: decision provenance/hash mismatch")
            except ProtocolError as exc:
                errors.append(f"{where}: invalid decision envelope: {exc}")
        for key, message_type in (("results", "result"), ("acks", "ack")):
            values = record.get(key, [])
            if not isinstance(values, list):
                errors.append(f"{where}: {key} must be a list")
                continue
            for envelope in values:
                try:
                    validate_envelope(envelope, expected_message_type=message_type)
                    envelopes.append(envelope)
                except ProtocolError as exc:
                    errors.append(f"{where}: invalid {message_type} envelope: {exc}")
        _validate_result_ack_contract(record, where, errors)
        replay = record.get("replay") if isinstance(record.get("replay"), Mapping) else {}
        snapshot = replay.get("snapshot") if isinstance(replay.get("snapshot"), Mapping) else None
        if snapshot is None and isinstance(replay.get("records"), list):
            snapshot = {"rows": replay.get("records")}
        replay_rows = snapshot.get("rows") if isinstance(snapshot, Mapping) else None
        if record.get("status") == "completed":
            if (
                not isinstance(snapshot, Mapping)
                or not isinstance(replay_rows, list)
                or not replay_rows
                or not isinstance(replay_rows[0], Mapping)
                or replay_rows[0].get("message_type") != "request"
            ):
                errors.append(f"{where}: completed record lacks canonical replay snapshot rows")
            else:
                request = record.get("request")
                request_identity_keys = (
                    "request_id",
                    "session_id",
                    "session_epoch",
                    "episode_id",
                    "scenario_id",
                    "npc_id",
                    "goal_id",
                    "goal_version",
                )
                if not isinstance(request, Mapping) or any(
                    request.get(key) != replay_rows[0].get(key) for key in request_identity_keys
                ):
                    errors.append(f"{where}: completed request identity does not bind replay")
                for envelope in [
                    *(
                        [record.get("decision")]
                        if isinstance(record.get("decision"), Mapping)
                        else []
                    ),
                    *(record.get("results", []) if isinstance(record.get("results"), list) else []),
                ]:
                    if isinstance(envelope, Mapping) and any(
                        request.get(key) != envelope.get(key) for key in request_identity_keys
                    ):
                        errors.append(
                            f"{where}: completed request identity does not bind envelopes"
                        )
                        break
                try:
                    checked = ReplayValidator.validate(
                        snapshot,
                        expected_session_id=str(record.get("request", {}).get("session_id"))
                        if isinstance(record.get("request"), Mapping)
                        else None,
                    )
                    python = replay.get("python", {}) if isinstance(replay, Mapping) else {}
                    if python.get("valid") is not True or python.get("rows") != checked["rows"]:
                        errors.append(f"{where}: canonical replay summary mismatch")
                    replay_result_rows = [
                        row
                        for row in replay_rows
                        if isinstance(row, Mapping) and row.get("message_type") == "result"
                    ]
                    persisted_results = record.get("results", [])
                    if (
                        not isinstance(persisted_results, list)
                        or len(replay_result_rows) != len(persisted_results)
                        or any(
                            not isinstance(source, Mapping)
                            or not isinstance(row, Mapping)
                            or _core_rebased_replay_envelope(source, row) != row
                            for source, row in zip(persisted_results, replay_result_rows)
                        )
                    ):
                        errors.append(f"{where}: replay result rows do not match persisted results")
                except (ProtocolError, ValueError, KeyError, TypeError) as exc:
                    errors.append(f"{where}: canonical replay invalid in {result_path}: {exc}")
        _validate_engine(
            record,
            assignment,
            errors,
            where,
            expected_policy,
            root,
            packet_dir or root / "research/academic-pipeline/npc-goal-recovery/verified-run-006",
            artifact_root,
        )
    _validate_publish_records(records, packet, run_mode, errors)
    missing = sorted(set(assignment_map) - set(record_map))
    if missing:
        errors.append(
            f"missing assignment results: {missing[:8]}" + ("..." if len(missing) > 8 else "")
        )

    if not aggregate_path.is_file():
        errors.append(f"missing aggregate: {aggregate_path}")
    else:
        aggregate = read_json(aggregate_path)
        if (
            not isinstance(aggregate, Mapping)
            or aggregate.get("schema_version") != PACKET_SCHEMA_VERSION
            or aggregate.get("packet_id") != packet
        ):
            errors.append("aggregate schema or packet id mismatch")
        if isinstance(aggregate, Mapping) and aggregate.get("run_mode") != run_mode:
            errors.append("aggregate run_mode does not match source manifest")
        if isinstance(aggregate, Mapping):
            for key, expected in (
                ("config_hash", config_digest),
                ("npc_protocol_config_sha256", config_digest),
                ("source_project_config_sha256", project_digest),
                ("source_schema_sha256", schema_digest),
                ("policy_hash", expected_policy),
            ):
                if aggregate.get(key) != expected:
                    errors.append(f"aggregate {key} mismatch")
            if (
                aggregate.get("assignment_count") != expected_count
                or aggregate.get("claims") != EXPECTED_CLAIMS
            ):
                errors.append("aggregate count/claim boundary mismatch")
            arms = aggregate.get("arms", {}) if isinstance(aggregate.get("arms"), Mapping) else {}
            expected_summaries: dict[str, dict[str, Any]] = {}
            for arm in ARMS:
                rows = [row for row in records if row.get("arm") == arm]
                failures: dict[str, int] = {}
                statuses: dict[str, int] = {}
                for row in rows:
                    status = str(row.get("status", "unknown"))
                    statuses[status] = statuses.get(status, 0) + 1
                    values = row.get("failure", [])
                    if isinstance(values, list):
                        for failure in values:
                            if isinstance(failure, Mapping):
                                code = str(failure.get("code", "unknown"))
                                failures[code] = failures.get(code, 0) + 1
                observed: dict[str, tuple[int | None, bool]] = {}
                for field in ("goal_reached", "recovery_eligible", "recovery_unreachable"):
                    values = [row.get(field) for row in rows]
                    available = bool(values) and all(type(value) is bool for value in values)
                    observed[field] = (
                        (sum(1 for value in values if value), available)
                        if available
                        else (None, False)
                    )
                expected_summaries[arm] = {
                    "n": len(rows),
                    "source_independent_n": sum(
                        1
                        for row in rows
                        if isinstance(row.get("provenance"), Mapping)
                        and row["provenance"].get("independent_source")
                    ),
                    "completed_n": sum(1 for row in rows if row.get("status") == "completed"),
                    "assigned_failure_n": sum(
                        1 for row in rows if row.get("status") == "assigned_failure"
                    ),
                    "failures_by_code": failures,
                    "terminal_status_counts": statuses,
                    "goal_reached_n": observed["goal_reached"][0],
                    "goal_reached_available": observed["goal_reached"][1],
                    "recovery_eligible_n": observed["recovery_eligible"][0],
                    "recovery_eligible_available": observed["recovery_eligible"][1],
                    "recovery_unreachable_n": observed["recovery_unreachable"][0],
                    "recovery_unreachable_available": observed["recovery_unreachable"][1],
                    "success": None,
                }
                summary = arms.get(arm, {}) if isinstance(arms.get(arm), Mapping) else {}
                if summary != expected_summaries[arm]:
                    errors.append(f"aggregate arm {arm} counts/statuses mismatch validated records")
            expected_denominators = {
                "all_preassigned": len(assignments),
                "recovery_eligible": sum(
                    summary["recovery_eligible_n"] or 0 for summary in expected_summaries.values()
                )
                if all(
                    summary["recovery_eligible_available"]
                    for summary in expected_summaries.values()
                )
                else None,
                "recovery_unreachable": sum(
                    summary["recovery_unreachable_n"] or 0
                    for summary in expected_summaries.values()
                )
                if all(
                    summary["recovery_unreachable_available"]
                    for summary in expected_summaries.values()
                )
                else None,
            }
            if aggregate.get("denominators") != expected_denominators:
                errors.append("aggregate denominators mismatch validated records")

    replay_path = _path(root, packet_dir, "replay-results.json")
    if not replay_path.is_file():
        errors.append(f"missing replay report: {replay_path}")
    else:
        _validate_replay_report(
            read_json(replay_path), packet, packet_dir, assignment_map, records, errors
        )

    sha_path = _path(root, packet_dir, "sha256-manifest.json")
    if not sha_path.is_file():
        errors.append(f"missing sha256 manifest: {sha_path}")
    else:
        receipt = read_json(sha_path)
        entries = receipt.get("files") if isinstance(receipt, Mapping) else None
        if (
            not isinstance(receipt, Mapping)
            or receipt.get("schema_version") != "npc-goal-recovery/receipts-1"
            or not isinstance(entries, list)
        ):
            errors.append("sha256 manifest schema mismatch")
        else:
            packet_root = packet_dir.resolve()
            seen_receipts: set[str] = set()
            for index, item in enumerate(entries):
                if not isinstance(item, Mapping) or set(item) != {"path", "sha256"}:
                    errors.append(f"sha256 manifest entry[{index}] malformed")
                    continue
                path_text = item.get("path")
                candidate = Path(path_text) if isinstance(path_text, str) else Path("")
                if (
                    not isinstance(path_text, str)
                    or not path_text
                    or candidate.is_absolute()
                    or ".." in candidate.parts
                ):
                    errors.append(f"sha256 manifest entry[{index}] path must be packet-relative")
                    continue
                local = (packet_root / candidate).resolve()
                try:
                    relative = local.relative_to(packet_root)
                except ValueError:
                    errors.append(f"sha256 manifest entry[{index}] path escapes packet")
                    continue
                normalized = relative.as_posix()
                if normalized != path_text:
                    errors.append(f"sha256 manifest entry[{index}] path is not normalized")
                if path_text in seen_receipts:
                    errors.append(f"sha256 manifest duplicate path: {path_text}")
                seen_receipts.add(path_text)
                if not _is_sha(item.get("sha256")):
                    errors.append(f"sha256 manifest entry malformed: {path_text}")
                elif not local.is_file() or sha256_file(local) != item["sha256"]:
                    errors.append(f"sha256 receipt mismatch: {path_text}")
            expected_receipts = {
                path.relative_to(packet_root).as_posix()
                for path in packet_root.rglob("*")
                if path.is_file()
                and path.name not in {"sha256-manifest.json", "validation-report.json"}
                and "godot-project" not in path.relative_to(packet_root).parts
            }
            missing_receipts = expected_receipts - seen_receipts
            extra_receipts = seen_receipts - expected_receipts
            if missing_receipts:
                errors.append(f"sha256 receipt missing files: {sorted(missing_receipts)[:8]}")
            if extra_receipts:
                errors.append(f"sha256 receipt unexpected files: {sorted(extra_receipts)[:8]}")
    publishable = run_mode == "publish" and packet == "NPC-SCR1" and not test_only and not errors
    report = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "core_schema_version": CORE_SCHEMA_VERSION,
        "packet_id": packet,
        "run_mode": run_mode,
        "publishable": publishable,
        "valid": not errors,
        "errors": errors,
        "counts": {
            "assignments": len(assignments),
            "records": len(records),
            "missing_records": len(missing),
        },
        "claim_boundary": dict(EXPECTED_CLAIMS),
        "replay_model_calls": 0,
        "source": {
            "config_hash": config_digest,
            "npc_protocol_config_sha256": config_digest,
            "source_project_config_sha256": project_digest,
            "source_schema_sha256": schema_digest,
            "policy_hash": expected_policy,
            "test_only": test_only,
        },
        "packet_dir": str(packet_dir),
    }
    return report, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", choices=("engineering", "screening", "all"), default="all")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--packet-dir", type=Path, default=None)
    args = parser.parse_args()
    packets = (
        ["NPC-ENG1", "NPC-SCR1"]
        if args.packet == "all"
        else ["NPC-ENG1" if args.packet == "engineering" else "NPC-SCR1"]
    )
    packet_dir = (
        args.packet_dir
        or args.root / "research/academic-pipeline/npc-goal-recovery/verified-run-006"
    )
    reports: list[dict[str, Any]] = []
    for packet in packets:
        report, _ = validate_packet(packet, args.root, packet_dir=packet_dir)
        reports.append(report)
    output = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "core_schema_version": CORE_SCHEMA_VERSION,
        "valid": all(item.get("valid") for item in reports),
        "packets": reports,
        "packet_dir": str(packet_dir),
    }
    packet_dir.mkdir(parents=True, exist_ok=True)
    (packet_dir / "validation-report.json").write_bytes(canonical(output) + b"\n")
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if output["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
