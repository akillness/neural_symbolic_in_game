#!/usr/bin/env python3
"""Run the fixed-goal NPC protocol experiments with auditable evidence.

The runner freezes every assignment before invoking an interpreter.  P uses the
authenticated Codex adapter through :class:`IntentInterpreter`; R and O use
only their explicitly declared deterministic inputs.  Godot is invoked only
when an actual binary/entrypoint is supplied.  Missing services, parse errors,
timeouts, and unavailable engine gates stay as assigned failures; no fallback
or fabricated success is emitted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from run_playable_evaluation import stage_project

from nesy_game.npc_goal import (
    DEFAULT_BUDGET,
    ControllerFailure,
    GoalController,
    IntentInterpreter,
    ProtocolError,
    ReplayValidator,
    validate_envelope,
)

SCHEMA_VERSION = "npc-goal-recovery/1.1.0"
PACKET_SCHEMA_VERSION = "npc-goal-recovery/evidence-1"
SCENARIO_ID = "sealed-lighthouse-v1"
NPC_ID = "captain_mira"
GOAL_ID = "harbor-signal-restored-authorized-tide-lead-v1"
GOAL_VERSION = "1"
ARMS = ("P", "R", "O")
OBSERVATION_KEYS = (
    "lens_reachable",
    "lens_carried",
    "signal_restored",
    "tide_lead_authorized",
    "goal_reached",
    "in_dialogue",
)
PROTOCOL_BUDGET_KEYS = (
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
)
CLAIM_BOUNDARY = {
    "engineering": "synthetic closed-world deterministic protocol/gate checks",
    "screening": "bounded descriptive screening only",
    "independent_labels": False,
    "efficacy_pending": True,
    "superiority": False,
    "generalization": False,
    "human_benefit": False,
    "c_result_promotion": False,
}


class AdmissionShortCircuit(Exception):
    """Stop one assignment before any engine/model call after global admission failure."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(canonical(value) + b"\n")
    os.replace(temporary, path)


def write_jsonl_preserving(
    path: Path, rows: list[Mapping[str, Any]], *, key: str = "assignment_id"
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        existing = [dict(row) for row in load_jsonl_local(path)]
    merged: dict[str, Mapping[str, Any]] = {
        str(row.get(key)): row for row in existing if row.get(key) is not None
    }
    for row in rows:
        row_key = row.get(key)
        if row_key is None or str(row_key) not in merged:
            merged[str(row_key)] = row
    ordered = [
        merged[str(row[key])]
        for row in rows
        if row.get(key) is not None and str(row[key]) in merged
    ]
    seen = {str(row[key]) for row in ordered if row.get(key) is not None}
    ordered.extend(
        row for row in existing if row.get(key) is not None and str(row[key]) not in seen
    )
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        for row in ordered:
            handle.write(canonical(row).decode("utf-8") + "\n")
    os.replace(temporary, path)


def load_jsonl_local(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: JSONL row must be an object")
            rows.append(value)
    return rows


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_budget(config: Mapping[str, Any]) -> dict[str, Any]:
    configured = dict(config.get("budget", {}))
    result = {key: configured.get(key, DEFAULT_BUDGET[key]) for key in PROTOCOL_BUDGET_KEYS}
    if result["max_inflight_per_session"] != 1:
        raise ValueError("frozen budget max_inflight_per_session must be 1")
    return result


def canonical_config_hash(path: Path) -> str:
    """Hash the exact config file bytes used by every runtime."""
    return sha256_file(path)


def source_project_config_hash(root: Path) -> str:
    return sha256_file(root / "game-track/godot/project.godot")


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def extract_policy_hash(report: Mapping[str, Any] | None) -> str | None:
    if not isinstance(report, Mapping):
        return None
    source_hashes = report.get("source_hashes")
    candidates = [report.get("policy_hash"), report.get("actual_policy_hash")]
    if isinstance(source_hashes, Mapping):
        candidates.extend(
            [source_hashes.get("policy_hash"), source_hashes.get("actual_policy_hash")]
        )
    for candidate in candidates:
        if is_sha256(candidate):
            return str(candidate)
    return None


def extract_snapshot(report: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(report, Mapping):
        return None
    snapshot = report.get("initial_public_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = report.get("public_snapshot")
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    observation = report.get(
        "public_observation", report.get("observation", snapshot.get("observation"))
    )
    state_ref = report.get(
        "actual_state_ref",
        report.get("initial_state_ref", report.get("state_ref", snapshot.get("state_ref"))),
    )
    if not isinstance(observation, Mapping) or not isinstance(state_ref, Mapping):
        return None
    try:
        return {
            "observation": normalize_observation(observation),
            "state_ref": normalize_state_ref(state_ref),
        }
    except ValueError:
        return None


def extract_final_snapshot(report: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(report, Mapping):
        return None
    actions = report.get("actions", report.get("rows", []))
    if isinstance(actions, list):
        for action in reversed(actions):
            if isinstance(action, Mapping):
                snapshot = extract_snapshot(
                    {
                        "observation": action.get("observation_after"),
                        "state_ref": action.get("state_ref_after"),
                    }
                )
                if snapshot is not None:
                    return snapshot
    final_ref = report.get("final_state_ref")
    observations = report.get("observations")
    if isinstance(final_ref, Mapping) and isinstance(observations, list) and observations:
        return extract_snapshot({"observation": observations[-1], "state_ref": final_ref})
    return None


def normalize_observation(value: Any) -> dict[str, bool]:
    if not isinstance(value, Mapping) or set(value) != set(OBSERVATION_KEYS):
        raise ValueError("fixture observation must contain exactly the six public fields")
    if any(type(value[key]) is not bool for key in OBSERVATION_KEYS):
        raise ValueError("fixture observation values must be booleans")
    return {key: bool(value[key]) for key in OBSERVATION_KEYS}


def normalize_state_ref(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"revision", "sha256"}:
        raise ValueError("fixture state_ref must contain revision and sha256")
    revision = value["revision"]
    state_hash = value["sha256"]
    if (
        type(revision) is not int
        or revision < 0
        or not isinstance(state_hash, str)
        or len(state_hash) != 64
    ):
        raise ValueError("fixture state_ref has invalid revision/hash")
    try:
        int(state_hash, 16)
    except ValueError as exc:
        raise ValueError("fixture state_ref hash is not hexadecimal") from exc
    return {"revision": revision, "sha256": state_hash}


def _fixture_path_from_ref(fixture_ref: str) -> Path:
    fixture_path = Path(str(fixture_ref).split("#", 1)[0])
    return fixture_path if fixture_path.is_absolute() else ROOT / fixture_path


def _project_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _case_digest(case: Mapping[str, Any]) -> str:
    return digest({key: value for key, value in case.items() if not str(key).startswith("_")})


def normalize_case(case: Any, fixture_path: Path) -> dict[str, Any]:
    if not isinstance(case, Mapping):
        raise ProtocolError(f"{fixture_path}: case must be an object")
    required = {
        "id",
        "regime",
        "utterance",
        "observation",
        "state_ref",
        "seed",
        "source_kind",
        "config_hash",
    }
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"{fixture_path}: case missing {missing}")
    case_copy = json.loads(json.dumps(case, ensure_ascii=False))
    case_copy["id"] = str(case_copy["id"])
    case_copy["regime"] = str(case_copy["regime"])
    case_copy["utterance"] = str(case_copy["utterance"])
    case_copy["config_hash"] = str(case_copy["config_hash"])
    if (
        not case_copy["id"]
        or len(case_copy["utterance"]) > 1000
        or not case_copy["source_kind"]
        or not is_sha256(case_copy["config_hash"])
    ):
        raise ValueError(
            f"{fixture_path}: invalid case id, config_hash, source_kind, or utterance length"
        )
    if type(case_copy["seed"]) is not int:
        raise ValueError(f"{fixture_path}: case seed must be an integer")
    case_copy["observation"] = normalize_observation(case_copy["observation"])
    case_copy["state_ref"] = normalize_state_ref(case_copy["state_ref"])
    utterance_hash = hashlib.sha256(case_copy["utterance"].encode("utf-8")).hexdigest()
    supplied_hash = case_copy.get("raw_utterance_sha256")
    if supplied_hash is not None and supplied_hash != utterance_hash:
        raise ValueError(f"{fixture_path}:{case_copy['id']}: raw utterance hash mismatch")
    case_copy["raw_utterance_sha256"] = utterance_hash
    reference = case_copy.get("reference_intent")
    if reference is not None and not isinstance(reference, Mapping):
        raise ValueError(f"{fixture_path}:{case_copy['id']}: reference_intent must be an object")
    for key in ("setup_operations", "seed_world_events", "mutations"):
        if key in case_copy and not isinstance(case_copy[key], list):
            raise ValueError(f"{fixture_path}:{case_copy['id']}: {key} must be a list")
    if "in_dialogue" in case_copy and type(case_copy["in_dialogue"]) is not bool:
        raise ValueError(f"{fixture_path}:{case_copy['id']}: in_dialogue must be boolean")
    case_copy.pop("utterance", None)
    stable_fixture_ref = f"{_project_relative(fixture_path)}#{case_copy['id']}"
    case_copy["fixture_ref"] = stable_fixture_ref
    case_copy["fixture_ref_sha256"] = hashlib.sha256(stable_fixture_ref.encode("utf-8")).hexdigest()
    return case_copy


def load_cases(path: Path, expected_packet: str, expected_count: int) -> list[dict[str, Any]]:
    payload = read_json(path)
    if (
        not isinstance(payload, Mapping)
        or payload.get("schema_version") != "npc-goal-recovery/validated-v5"
        or payload.get("packet_id") != expected_packet
    ):
        raise ValueError(
            f"{path}: schema_version must be npc-goal-recovery/validated-v5 and packet_id must be {expected_packet}"
        )
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != expected_count:
        raise ValueError(f"{path}: expected exactly {expected_count} cases")
    normalized = [normalize_case(case, path) for case in cases]
    ids = [case["id"] for case in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{path}: duplicate case ids")
    return normalized


def make_assignments(
    cases: list[dict[str, Any]],
    *,
    packet_id: str,
    config_hash: str,
    npc_protocol_config_sha256: str,
    source_schema_sha256: str,
    source_project_config_sha256: str,
    policy_hash: str | None,
    budget: Mapping[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in cases:
        if packet_id == "NPC-ENG1":
            arms = tuple(case.get("arms", ("R",)))
            repetitions = int(case.get("repetitions", 1))
        else:
            arms = ARMS
            repetitions = 2
        for arm in arms:
            if arm not in ARMS:
                raise ValueError(f"{case['id']}: invalid arm {arm}")
            for repetition in range(repetitions):
                assignment_id = f"{packet_id}:{case['id']}:{arm}:rep{repetition + 1}"
                source = {
                    "assignment_id": assignment_id,
                    "packet_id": packet_id,
                    "case_id": case["id"],
                    "fixture_ref": case["fixture_ref"],
                    "arm": arm,
                    "repetition": repetition + 1,
                    "seed": case["seed"],
                    "fixture_input_sha256": _case_digest(case),
                    "config_hash": config_hash,
                    "source_project_config_sha256": source_project_config_sha256,
                    "npc_protocol_config_sha256": npc_protocol_config_sha256,
                    "source_schema_sha256": source_schema_sha256,
                    "policy_hash": policy_hash,
                    "budget": dict(budget),
                    "source_kind": case["source_kind"],
                    "utterance_source_kind": case["source_kind"],
                    "independent_source": False,
                }
                row = dict(source)
                row["assignment_key"] = digest(source)
                rows.append(row)
    return rows


def freeze_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    """Create a manifest once; an existing file is immutable, including dry-runs."""
    if path.exists():
        existing = read_json(path)
        if existing != manifest:
            raise RuntimeError(f"frozen assignment manifest already exists and differs: {path}")
        return
    write_json(path, manifest)


def build_request(
    case: Mapping[str, Any],
    assignment: Mapping[str, Any],
    budget: Mapping[str, Any],
    *,
    observation: Mapping[str, Any],
    state_ref: Mapping[str, Any],
    event_kind: str = "utterance",
    sequence: int = 0,
    request_suffix: str = "",
) -> dict[str, Any]:
    policy = assignment.get("policy_hash")
    if not is_sha256(policy):
        raise ProtocolError("actual_policy_hash_unavailable")
    source = {
        "session_id": f"npc-exp-{assignment['assignment_key'][:20]}",
        "session_epoch": 0,
        "episode_id": f"episode-{assignment['assignment_key'][:20]}",
        "request_id": f"request-{assignment['assignment_key'][:20]}{request_suffix}",
        "sequence": sequence,
        "delivery_index": sequence,
        "config_hash": assignment["config_hash"],
        "policy_hash": policy,
        "state_ref": dict(state_ref),
        "budget": dict(budget),
        "provenance": {
            "arm": assignment["arm"],
            "backend": {"P": "codex", "R": "rule", "O": "reference"}[assignment["arm"]],
            "model": None,
            "trace_ref": assignment["assignment_id"],
            "recorded_response_ref": None,
            "raw_utterance_sha256": case["raw_utterance_sha256"]
            if event_kind == "utterance"
            else None,
        },
    }
    body = {
        "event_kind": event_kind,
        "utterance": case["_utterance"] if event_kind == "utterance" else None,
        "observation": normalize_observation(observation),
    }
    return GoalController.make_envelope(source, "request", body)


def redacted_request(request: Mapping[str, Any], case: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": request["schema_version"],
        "message_type": "request_redacted",
        "session_id": request["session_id"],
        "session_epoch": request["session_epoch"],
        "episode_id": request["episode_id"],
        "request_id": request["request_id"],
        "event_id": request["event_id"],
        "sequence": request["sequence"],
        "delivery_index": request["delivery_index"],
        "scenario_id": request["scenario_id"],
        "npc_id": request["npc_id"],
        "goal_id": request["goal_id"],
        "goal_version": request["goal_version"],
        "config_hash": request["config_hash"],
        "state_ref": dict(request["state_ref"]),
        "fixture_ref": case["fixture_ref"],
        "raw_utterance_sha256": case["raw_utterance_sha256"],
        "observation": dict(request["body"]["observation"]),
        "budget": dict(request["budget"]),
        "provenance": dict(request["provenance"]),
    }


def parse_json_output(text: str) -> Any:
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in reversed(text.splitlines()):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return None


def run_godot(
    *,
    binary: str | None,
    project: Path,
    mode: str,
    input_path: Path,
    log_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    project = project.resolve()
    input_path = input_path.resolve()
    log_dir = log_dir.resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    input_ref = input_path.relative_to(log_dir.parent).as_posix()
    if not input_path.is_file() or input_path.stat().st_size == 0:
        return {
            "available": False,
            "status": "invalid_input",
            "mode": mode,
            "command": [],
            "input_path": str(input_path),
            "input_exists": input_path.is_file(),
            "input_nonempty": input_path.is_file() and input_path.stat().st_size > 0,
            "input_sha256_before": None,
            "input_sha256_after": None,
            "input_bytes_preserved": False,
            "error": "godot_input_missing_or_empty",
        }
    command = [
        binary or "godot",
        "--headless",
        "--audio-driver",
        "Dummy",
        "--path",
        str(project),
        "--scene",
        "scenes/main_3d.tscn",
        "--",
        f"--npc-{mode}",
        str(input_path),
    ]
    started = time.perf_counter()
    input_before = sha256_file(input_path)
    result: dict[str, Any] = {
        "available": False,
        "status": "unavailable",
        "mode": mode,
        "project_path": str(project),
        "input_path": input_ref,
        "input_exists": True,
        "input_nonempty": True,
        "command": command,
        "latency_ms": None,
        "returncode": None,
        "trace": None,
        "sidecar_path": input_ref + (".bootstrap.json" if mode == "bootstrap" else ".result.json"),
        "input_sha256_before": input_before,
        "input_sha256_after": None,
        "input_bytes_preserved": False,
        "artifact_root": str(log_dir.parent),
    }
    resolved = shutil.which(binary or "godot") if not Path(binary or "godot").is_file() else binary
    if resolved is None:
        result["error"] = "godot_binary_unavailable"
        return result
    result["available"] = True
    stdout_path = log_dir / f"{input_path.stem}.{mode}.stdout.log"
    stderr_path = log_dir / f"{input_path.stem}.{mode}.stderr.log"
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        result.update(
            {
                "status": "deadline_timeout",
                "error": "godot_deadline",
                "latency_ms": (time.perf_counter() - started) * 1000,
            }
        )
        stdout = (
            exc.stdout.decode("utf-8", errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
        stderr = (
            exc.stderr.decode("utf-8", errors="replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "")
        )
        stdout_path.write_text(stdout, encoding="utf-8")
        stderr_path.write_text(stderr, encoding="utf-8")
        return result
    except OSError as exc:
        result.update(
            {
                "status": "launch_failed",
                "error": type(exc).__name__,
                "latency_ms": (time.perf_counter() - started) * 1000,
            }
        )
        return result
    stdout_path.write_text(completed.stdout or "", encoding="utf-8")
    stderr_path.write_text(completed.stderr or "", encoding="utf-8")
    input_after = sha256_file(input_path) if input_path.is_file() else None
    result["input_sha256_after"] = input_after
    result["input_bytes_preserved"] = input_before is not None and input_before == input_after
    sidecar_path = input_path.with_name(
        input_path.name + (".bootstrap.json" if mode == "bootstrap" else ".result.json")
    )
    report: Any = None
    if sidecar_path.is_file():
        try:
            report = read_json(sidecar_path)
        except (OSError, json.JSONDecodeError) as exc:
            result["error"] = f"invalid_result_sidecar:{type(exc).__name__}"
    else:
        result["error"] = "missing_result_sidecar"
    result["trace"] = report
    passed = isinstance(report, Mapping) and report.get("passed") is True
    result.update(
        {
            "status": "completed"
            if completed.returncode == 0 and passed and result["input_bytes_preserved"]
            else "failed",
            "returncode": completed.returncode,
            "latency_ms": (time.perf_counter() - started) * 1000,
        }
    )
    if not result["input_bytes_preserved"]:
        result["status"] = "input_mutated"
        result["error"] = "godot_input_bytes_changed"
    return result


def envelope_result_from_engine(
    source_envelope: Mapping[str, Any],
    request: Mapping[str, Any],
    engine_action: Mapping[str, Any],
    budget: Mapping[str, Any],
) -> dict[str, Any]:
    required = {"action_id", "operation", "status", "observation_after"}
    if set(engine_action) < required:
        raise ProtocolError("engine_action_missing_authoritative_fields")
    raw_state_ref = engine_action.get("state_ref_after")
    if not isinstance(raw_state_ref, Mapping):
        raise ProtocolError("engine_action_missing_after_state_ref")
    state_ref = normalize_state_ref(raw_state_ref)
    observation = normalize_observation(engine_action["observation_after"])
    raw_revision = engine_action.get("engine_revision", state_ref["revision"])
    if type(raw_revision) is not int or raw_revision != state_ref["revision"]:
        raise ProtocolError("engine_revision_state_ref_mismatch")
    body = {
        "action_id": str(engine_action["action_id"]),
        "operation": str(engine_action["operation"]),
        "status": str(engine_action["status"]),
        "engine_revision": raw_revision,
        "state_ref": state_ref,
        "feedback": str(engine_action.get("feedback", ""))[:512],
        "observation": observation,
    }
    source = dict(source_envelope)
    source["budget"] = dict(budget)
    source["state_ref"] = dict(body["state_ref"])
    return GoalController.make_envelope(source, "result", body)


def _engine_action_signature(action: Mapping[str, Any]) -> dict[str, Any]:
    after = action.get("state_ref_after")
    if not isinstance(after, Mapping):
        raise ProtocolError("engine action missing state_ref_after")
    state_ref_after = normalize_state_ref(after)
    before = action.get("state_ref_before")
    state_ref_before = normalize_state_ref(before) if isinstance(before, Mapping) else None
    observation = action.get("observation_after")
    if not isinstance(observation, Mapping):
        observation = action.get("observation")
    return {
        "action_id": str(action.get("action_id", "")),
        "operation": str(action.get("operation", "")),
        "execution_mode": str(action.get("execution_mode", "")),
        "arguments": json.loads(json.dumps(action.get("arguments", {}), ensure_ascii=False)),
        "status": str(action.get("status", "")),
        "observation": normalize_observation(observation),
        "state_ref_before": state_ref_before,
        "state_ref_after": state_ref_after,
        "engine_revision": state_ref_after["revision"],
        "state_hash_after": state_ref_after["sha256"],
    }


def _engine_reexecution_comparison(
    original: Mapping[str, Any], replayed: Mapping[str, Any]
) -> dict[str, Any]:
    def actions(report: Mapping[str, Any]) -> list[dict[str, Any]]:
        rows = report.get("actions", report.get("rows", []))
        if not isinstance(rows, list):
            raise TypeError("engine_reexecution_actions_must_be_list")
        return [_engine_action_signature(row) for row in rows]

    original_actions = actions(original)
    replay_actions = actions(replayed)
    original_gates = original.get("expected_negative_gates", [])
    replay_gates = replayed.get("expected_negative_gates", [])
    comparison = {
        "terminal_status": original.get("status", original.get("terminal_status"))
        == replayed.get("status", replayed.get("terminal_status")),
        "initial_state_ref": original.get("initial_state_ref") == replayed.get("initial_state_ref"),
        "final_state_ref": original.get("final_state_ref") == replayed.get("final_state_ref"),
        "decision_sha256": original.get("decision_sha256") == replayed.get("decision_sha256"),
        "actions": original_actions == replay_actions,
        "expected_negative_gates": original_gates == replay_gates,
    }
    comparison["passed"] = all(comparison.values())
    return comparison


def classify_exception(exc: BaseException) -> dict[str, Any]:
    text = str(exc) or type(exc).__name__
    code = text.split(":", 1)[0]
    if isinstance(exc, ProtocolError):
        category = "parse_failure"
    elif isinstance(exc, ControllerFailure):
        category = "controller_failure"
    elif isinstance(exc, TimeoutError):
        category = "deadline_failure"
    else:
        category = "runner_failure"
    return {"category": category, "code": code, "error": text}


def execute_assignment(
    case: Mapping[str, Any],
    assignment: Mapping[str, Any],
    *,
    budget: Mapping[str, Any],
    model: str | None,
    service_url: str | None,
    godot_binary: str | None,
    godot_project: Path,
    output_dir: Path,
    godot_timeout: float,
    skip_model: bool = False,
    admission_failure: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    fixture_path = _fixture_path_from_ref(str(case["fixture_ref"]))
    fixture_payload = read_json(fixture_path)
    fixture_source = next(
        item
        for item in fixture_payload["cases"]
        if str(item.get("id")) == str(case["case_id"] if "case_id" in case else case["id"])
    )
    working_case = dict(case)
    working_case["_utterance"] = str(fixture_source["utterance"])
    request: dict[str, Any] | None = None
    decision: dict[str, Any] | None = None
    result_envelopes: list[dict[str, Any]] = []
    ack_envelopes: list[dict[str, Any]] = []
    python_snapshot: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    cli_exec_attempts: list[dict[str, Any]] = []
    engine: dict[str, Any] = {"available": False, "status": "not_run"}
    replay: dict[str, Any] = {"valid": False, "rows": 0, "model_calls": 0}
    controller: GoalController | None = None
    actual_snapshot: dict[str, Any] | None = None
    assignment_runtime = dict(assignment)
    setup_operations = json.loads(json.dumps(case.get("setup_operations", []), ensure_ascii=False))
    seed_world_events = json.loads(
        json.dumps(case.get("seed_world_events", []), ensure_ascii=False)
    )
    mutations = json.loads(json.dumps(case.get("mutations", []), ensure_ascii=False))
    in_dialogue = bool(case.get("in_dialogue", False))
    source_hashes = {
        "config_hash": assignment["config_hash"],
        "source_project_config_sha256": assignment["source_project_config_sha256"],
        "npc_protocol_config_sha256": assignment["npc_protocol_config_sha256"],
        "source_schema_sha256": assignment["source_schema_sha256"],
    }
    if is_sha256(assignment.get("policy_hash")):
        source_hashes["policy_hash"] = assignment["policy_hash"]
    input_root = output_dir / "godot-input"
    input_root.mkdir(parents=True, exist_ok=True)
    stem = assignment["assignment_id"].replace(":", "_")
    try:
        if admission_failure is not None:
            errors.append(dict(admission_failure))
            engine = {
                "available": False,
                "status": "admission_failed",
                "admission_failure": dict(admission_failure),
            }
            raise AdmissionShortCircuit()
        context_ids = {
            "session_id": f"npc-exp-{assignment['assignment_key'][:20]}",
            "episode_id": f"episode-{assignment['assignment_key'][:20]}",
            "session_epoch": 0,
            "request_id": f"request-{assignment['assignment_key'][:20]}",
            "goal_id": GOAL_ID,
            "goal_version": GOAL_VERSION,
            "config_hash": assignment["config_hash"],
        }
        bootstrap_input = {
            "schema_version": "npc-engineering/input-1",
            "assignment_id": assignment["assignment_id"],
            "fixture_ref": case["fixture_ref"],
            "fixture_input_sha256": assignment["fixture_input_sha256"],
            "config_hash": assignment["config_hash"],
            "source_hashes": dict(source_hashes),
            "setup_operations": setup_operations,
            "seed_world_events": seed_world_events,
            "in_dialogue": in_dialogue,
            "request_context": context_ids,
            "decision": None,
            "mutations": mutations,
        }
        bootstrap_path = input_root / f"{stem}.bootstrap.json"
        write_json(bootstrap_path, bootstrap_input)
        bootstrap_engine = run_godot(
            binary=godot_binary,
            project=godot_project,
            mode="bootstrap",
            input_path=bootstrap_path,
            log_dir=output_dir / "logs",
            timeout=godot_timeout,
        )
        engine["bootstrap"] = bootstrap_engine
        bootstrap_report = (
            bootstrap_engine.get("trace") if isinstance(bootstrap_engine, Mapping) else None
        )
        actual_snapshot = extract_snapshot(
            bootstrap_report if isinstance(bootstrap_report, Mapping) else None
        )
        actual_policy = extract_policy_hash(
            bootstrap_report if isinstance(bootstrap_report, Mapping) else None
        )
        expected_snapshot = {"observation": case["observation"], "state_ref": case["state_ref"]}
        frozen_policy = assignment.get("policy_hash")
        if not is_sha256(frozen_policy):
            errors.append(
                {
                    "category": "engine_gate_failure",
                    "code": "policy_hash_unavailable",
                    "error": "frozen assignment policy hash is unavailable",
                }
            )
        elif actual_policy is None:
            errors.append(
                {
                    "category": "engine_gate_failure",
                    "code": "actual_policy_hash_unavailable",
                    "error": "bootstrap did not return canonical disclosure-policy hash",
                }
            )
        elif actual_policy != frozen_policy:
            errors.append(
                {
                    "category": "engine_gate_failure",
                    "code": "policy_hash_mismatch",
                    "error": "bootstrap policy hash differs from frozen assignment",
                }
            )
        if actual_snapshot is None:
            errors.append(
                {
                    "category": "engine_gate_failure",
                    "code": "public_snapshot_unavailable",
                    "error": "bootstrap did not return canonical public observation/state_ref",
                }
            )
        elif actual_snapshot != expected_snapshot:
            errors.append(
                {
                    "category": "engine_gate_failure",
                    "code": "bootstrap_fixture_snapshot_mismatch",
                    "error": "bootstrap snapshot differs from frozen validated-v5 case observation/state_ref",
                }
            )
        if bootstrap_engine.get("status") != "completed":
            errors.append(
                {
                    "category": "engine_gate_failure",
                    "code": "bootstrap_failed",
                    "error": str(bootstrap_engine.get("error", bootstrap_engine.get("status"))),
                }
            )
        if (
            actual_snapshot is not None
            and is_sha256(actual_policy)
            and actual_policy == frozen_policy
            and not errors
        ):
            if skip_model and assignment["arm"] == "P":
                errors.append(
                    {
                        "category": "model_unavailable",
                        "code": "model_skipped",
                        "error": "P arm skipped by --skip-model",
                    }
                )
            else:
                assignment_runtime["policy_hash"] = frozen_policy
                request = build_request(
                    working_case,
                    assignment_runtime,
                    budget,
                    observation=actual_snapshot["observation"],
                    state_ref=actual_snapshot["state_ref"],
                )
                if service_url:
                    capability = os.environ.get("TRACE_RPG_NPC_CAPABILITY")
                    if not capability:
                        raise ControllerFailure("capability_missing")
                    req = urllib.request.Request(
                        service_url.rstrip("/") + "/npc/step",
                        data=canonical(request),
                        headers={
                            "Content-Type": "application/json",
                            "X-NPC-Capability": f"Bearer {capability}",
                        },
                        method="POST",
                    )
                    try:
                        with urllib.request.urlopen(
                            req, timeout=budget["intent_deadline_ms"] / 1000
                        ) as response:
                            decision = json.loads(response.read().decode("utf-8"))
                    except (
                        urllib.error.URLError,
                        TimeoutError,
                        OSError,
                        json.JSONDecodeError,
                    ) as exc:
                        errors.append(classify_exception(exc))
                    if decision is not None:
                        errors.append(
                            {
                                "category": "replay_failure",
                                "code": "remote_python_replay_unavailable",
                                "error": "remote service did not provide a trustworthy controller.export_trace replay",
                            }
                        )
                else:
                    reference = (
                        {working_case["raw_utterance_sha256"]: working_case.get("reference_intent")}
                        if working_case.get("reference_intent")
                        else {}
                    )
                    controller = GoalController(
                        interpreter=IntentInterpreter(
                            arm=assignment["arm"],
                            model=model,
                            reference_intents=reference,
                            execution_observer=cli_exec_attempts.append,
                        ),
                        budget=budget,
                    )
                    decision = controller.handle_request(request)
            if decision is not None:
                validate_envelope(decision, expected_message_type="decision")
                intent = decision["body"]["typed_intent"]
                events.extend(
                    [
                        {
                            "type": "intent",
                            "version": 1,
                            "intent_id": decision["body"]["intent_id"],
                            "typed_intent": intent,
                            "model": decision["provenance"]["model"],
                            "claims": intent.get("claims", []),
                        },
                        {
                            "type": "planning_context",
                            "digest": decision["body"]["planning_context_digest"],
                            "state_ref": decision["state_ref"],
                            "observation": request["body"]["observation"],
                        },
                        {
                            "type": "plan",
                            "plan_id": decision["body"]["plan_id"],
                            "steps": decision["body"]["steps"],
                            "status": decision["body"]["status"],
                        },
                    ]
                )
                experiment_mutations = list(mutations)
                decision_steps = (
                    decision.get("body", {}).get("steps", [])
                    if isinstance(decision.get("body", {}).get("steps", []), list)
                    else []
                )
                for step in decision_steps:
                    if (
                        isinstance(step, Mapping)
                        and step.get("operation") in {"acquire_object", "install_lens"}
                        and step.get("execution_mode") == "player_request"
                    ):
                        experiment_mutations.append(
                            {"code": "fixture-playeraction", "operation": step["operation"]}
                        )
                experiment_input = {
                    "schema_version": "npc-engineering/input-1",
                    "assignment_id": assignment["assignment_id"],
                    "fixture_ref": case["fixture_ref"],
                    "fixture_input_sha256": assignment["fixture_input_sha256"],
                    "config_hash": assignment["config_hash"],
                    "source_hashes": {**source_hashes, "policy_hash": actual_policy},
                    "setup_operations": setup_operations,
                    "seed_world_events": seed_world_events,
                    "in_dialogue": in_dialogue,
                    "request_context": {
                        **{
                            key: request[key]
                            for key in (
                                "session_id",
                                "episode_id",
                                "session_epoch",
                                "request_id",
                                "goal_id",
                                "goal_version",
                            )
                        },
                        "config_hash": request["config_hash"],
                    },
                    "request": redacted_request(request, case),
                    "decision": decision,
                    "initial_public_snapshot": actual_snapshot,
                    "expected": {"goal_reached": case["expected_goal_reached"]}
                    if type(case.get("expected_goal_reached")) is bool
                    else {},
                    "mutations": experiment_mutations,
                }
                input_path = input_root / f"{stem}.experiment.json"
                write_json(input_path, experiment_input)
                experiment_engine = run_godot(
                    binary=godot_binary,
                    project=godot_project,
                    mode="experiment",
                    input_path=input_path,
                    log_dir=output_dir / "logs",
                    timeout=godot_timeout,
                )
                engine["experiment"] = experiment_engine
                trace = (
                    experiment_engine.get("trace")
                    if isinstance(experiment_engine, Mapping)
                    else None
                )
                if not isinstance(trace, Mapping):
                    errors.append(
                        {
                            "category": "engine_gate_failure",
                            "code": "missing_experiment_sidecar",
                            "error": "Godot experiment sidecar missing or invalid",
                        }
                    )
                else:
                    events.extend(
                        item for item in trace.get("events", []) if isinstance(item, Mapping)
                    )
                    actions = trace.get("actions", trace.get("rows", []))
                    if not isinstance(actions, list):
                        actions = []
                    first_result_seen = False
                    first_result_ack_status: str | None = None
                    for action in actions:
                        if not isinstance(action, Mapping):
                            errors.append(
                                {
                                    "category": "engine_trace_failure",
                                    "code": "invalid_action",
                                    "error": "engine action row is not an object",
                                }
                            )
                            continue
                        first_result_seen = True
                        try:
                            result_envelope = envelope_result_from_engine(
                                decision, request, action, budget
                            )
                            result_envelopes.append(result_envelope)
                            if controller is None:
                                if first_result_ack_status is None:
                                    first_result_ack_status = "UNAVAILABLE"
                                    errors.append(
                                        {
                                            "category": "engine_gate_failure",
                                            "code": "result_ack_unavailable",
                                            "error": "cross-runtime result has no local controller ACK",
                                        }
                                    )
                                continue
                            ack = controller.handle_result(result_envelope)
                            validate_envelope(ack, expected_message_type="ack")
                            ack_body = (
                                ack.get("body", {}) if isinstance(ack.get("body"), Mapping) else {}
                            )
                            ack_identity_keys = (
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
                            ack_binding_error = (
                                ack_body.get("ack_for") != "result"
                                or any(
                                    ack.get(key) != result_envelope.get(key)
                                    for key in ack_identity_keys
                                )
                                or ack.get("state_ref") != result_envelope.get("state_ref")
                                or not isinstance(ack.get("sequence"), int)
                                or not isinstance(result_envelope.get("sequence"), int)
                                or ack["sequence"] <= result_envelope["sequence"]
                                or not isinstance(ack.get("delivery_index"), int)
                                or not isinstance(result_envelope.get("delivery_index"), int)
                                or ack["delivery_index"] <= result_envelope["delivery_index"]
                            )
                            if ack_binding_error:
                                first_result_ack_status = "ERROR"
                                errors.append(
                                    {
                                        "category": "engine_gate_failure",
                                        "code": "result_ack_binding_mismatch",
                                        "error": "cross-runtime result ACK identity/order did not bind the actual result",
                                    }
                                )
                                continue
                            ack_envelopes.append(ack)
                            ack_body = (
                                ack.get("body", {}) if isinstance(ack.get("body"), Mapping) else {}
                            )
                            ack_status = ack_body.get("status")
                            if first_result_ack_status is None:
                                first_result_ack_status = (
                                    str(ack_status) if ack_status is not None else "INVALID"
                                )
                            if ack_status != "ACCEPTED":
                                errors.append(
                                    {
                                        "category": "engine_gate_failure",
                                        "code": "result_ack_not_accepted",
                                        "error": f"cross-runtime result ACK status was {ack_status!r}",
                                    }
                                )
                        except (ProtocolError, ControllerFailure, KeyError, ValueError) as exc:
                            if first_result_ack_status is None:
                                first_result_ack_status = "ERROR"
                                errors.append(
                                    {
                                        "category": "engine_gate_failure",
                                        "code": "result_ack_not_accepted",
                                        "error": "cross-runtime result did not produce an ACCEPTED ACK",
                                    }
                                )
                            errors.append(classify_exception(exc))
                    # At most one observation-only replan, and only after the first result ACK is ACCEPTED.
                    accepted_action = next(
                        (
                            action
                            for action in actions
                            if first_result_seen
                            and first_result_ack_status == "ACCEPTED"
                            and isinstance(action, Mapping)
                            and str(action.get("status")) == "APPLIED"
                            and isinstance(action.get("result"), Mapping)
                            and bool(action["result"].get("accepted", False))
                        ),
                        None,
                    )
                    if accepted_action is not None and controller is not None:
                        snapshot = extract_snapshot(
                            {
                                "observation": accepted_action.get("observation_after"),
                                "state_ref": accepted_action.get("state_ref_after"),
                            }
                        )
                        if snapshot is None:
                            errors.append(
                                {
                                    "category": "engine_trace_failure",
                                    "code": "invalid_replan_snapshot",
                                    "error": "accepted action lacks actual state_ref_after/observation_after",
                                }
                            )
                        else:
                            try:
                                replan_request = build_request(
                                    working_case,
                                    assignment_runtime,
                                    budget,
                                    observation=snapshot["observation"],
                                    state_ref=snapshot["state_ref"],
                                    event_kind="observation",
                                    sequence=1,
                                    request_suffix="-r1",
                                )
                                replan_decision = controller.handle_request(replan_request)
                                validate_envelope(replan_decision, expected_message_type="decision")
                                events.append(
                                    {
                                        "type": "observation_replan",
                                        "sequence": 1,
                                        "state_ref": snapshot["state_ref"],
                                        "decision": replan_decision["body"],
                                    }
                                )
                            except (ProtocolError, ControllerFailure, KeyError, ValueError) as exc:
                                errors.append(classify_exception(exc))
                    if experiment_engine.get("status") != "completed":
                        errors.append(
                            {
                                "category": "engine_gate_failure",
                                "code": "experiment_failed",
                                "error": str(
                                    experiment_engine.get("error", experiment_engine.get("status"))
                                ),
                            }
                        )
                    if trace.get("passed") is not True:
                        errors.append(
                            {
                                "category": "engine_gate_failure",
                                "code": "godot_gate_failed",
                                "error": "Godot report passed is not true",
                            }
                        )
                    # Re-execute the exact immutable experiment input. This is intentionally
                    # --npc-experiment, not --npc-replay: setup/world/dialogue are identical.
                    replay_path = input_root / f"{stem}.engine_fixture_reexecution.experiment.json"
                    shutil.copyfile(input_path, replay_path)
                    engine_reexecution = run_godot(
                        binary=godot_binary,
                        project=godot_project,
                        mode="experiment",
                        input_path=replay_path,
                        log_dir=output_dir / "logs",
                        timeout=godot_timeout,
                    )
                    engine_reexecution["replay_kind"] = "engine_fixture_reexecution"
                    engine["replay"] = engine_reexecution
                    replay_trace = (
                        engine_reexecution.get("trace")
                        if isinstance(engine_reexecution, Mapping)
                        else None
                    )
                    if isinstance(replay_trace, Mapping):
                        try:
                            comparison = _engine_reexecution_comparison(trace, replay_trace)
                        except (
                            AttributeError,
                            KeyError,
                            ProtocolError,
                            TypeError,
                            ValueError,
                        ) as exc:
                            comparison = {
                                "passed": False,
                                "error": f"invalid_reexecution_comparison:{type(exc).__name__}:{exc}",
                            }
                    else:
                        comparison = {"passed": False, "error": "missing_reexecution_sidecar"}
                    engine["replay_comparison"] = comparison
                    replay_status = engine_reexecution.get("status")
                    replay_returncode = engine_reexecution.get("returncode")
                    replay_trace_passed = (
                        isinstance(replay_trace, Mapping) and replay_trace.get("passed") is True
                    )
                    replay_input_preserved = engine_reexecution.get("input_bytes_preserved") is True
                    replay_completed = (
                        replay_status == "completed"
                        and replay_returncode == 0
                        and replay_trace_passed
                        and replay_input_preserved
                    )
                    replay_comparison_passed = comparison.get("passed") is True
                    replay["engine_fixture_reexecution"] = {
                        "valid": replay_completed and replay_comparison_passed,
                        "status": replay_status,
                        "returncode": replay_returncode,
                        "trace_passed": replay_trace_passed,
                        "input_bytes_preserved": replay_input_preserved,
                        "command": engine_reexecution.get("command"),
                        "comparison": comparison,
                    }
                    if not replay_comparison_passed:
                        errors.append(
                            {
                                "category": "replay_failure",
                                "code": "engine_fixture_reexecution_mismatch",
                                "error": "re-executed immutable experiment did not match terminal/state/action evidence",
                            }
                        )
                    if not replay_completed:
                        incomplete_signals = []
                        if replay_status != "completed":
                            incomplete_signals.append(f"status={replay_status!r}")
                        if replay_returncode != 0:
                            incomplete_signals.append(f"returncode={replay_returncode!r}")
                        if not replay_trace_passed:
                            incomplete_signals.append("trace.passed is not true")
                        if not replay_input_preserved:
                            incomplete_signals.append("input_bytes_preserved is not true")
                        errors.append(
                            {
                                "category": "replay_failure",
                                "code": "engine_fixture_reexecution_incomplete",
                                "error": "re-executed immutable experiment did not complete successfully: "
                                + ", ".join(incomplete_signals),
                            }
                        )
                    if decision_steps:
                        tampered = json.loads(json.dumps(experiment_input, ensure_ascii=False))
                        # Isolate content tampering from the original fixture's negative-control oracle.
                        tampered["mutations"] = []
                        tampered_decision = tampered.get("decision", {})
                        tampered_steps = (
                            tampered_decision.get("body", {}).get("steps", [])
                            if isinstance(tampered_decision, Mapping)
                            else []
                        )
                        replay["godot_tamper_rejected"] = False
                        if (
                            isinstance(tampered_steps, list)
                            and tampered_steps
                            and isinstance(tampered_steps[0], Mapping)
                        ):
                            tampered_steps[0] = dict(tampered_steps[0])
                            tampered_steps[0]["operation"] = "tampered_operation"
                            tampered_path = input_root / f"{stem}.tamper.experiment.json"
                            write_json(tampered_path, tampered)
                            tamper_engine = run_godot(
                                binary=godot_binary,
                                project=godot_project,
                                mode="experiment",
                                input_path=tampered_path,
                                log_dir=output_dir / "logs",
                                timeout=godot_timeout,
                            )
                            engine["tamper_reexecution"] = tamper_engine
                            tamper_trace = (
                                tamper_engine.get("trace")
                                if isinstance(tamper_engine, Mapping)
                                else None
                            )
                            tamper_rows = (
                                tamper_trace.get("actions", tamper_trace.get("rows", []))
                                if isinstance(tamper_trace, Mapping)
                                else []
                            )
                            if not isinstance(tamper_rows, list):
                                tamper_rows = []
                            canonical_ref = (
                                actual_snapshot.get("state_ref")
                                if isinstance(actual_snapshot, Mapping)
                                else None
                            )
                            rejection_statuses = {"REJECTED", "STALE", "ERROR"}
                            canonical_rejection_codes = {
                                "CONTENT_HASH_MISMATCH",
                                "STATE_HASH_MISMATCH",
                                "STEP_ARGUMENTS_INVALID",
                                "STEP_BINDING_INVALID",
                                "PLAYER_ACTION_BINDING_MISMATCH",
                                "PLAYER_ACTION_PRECONDITION_MISMATCH",
                                "DECISION_CONTEXT_MISMATCH",
                                "POLICY_HASH_MISMATCH",
                            }
                            observed_statuses: set[str] = set()
                            observed_codes: set[str] = set()
                            mutated_false = False
                            unchanged_canonical_ref = False
                            for row in tamper_rows:
                                if not isinstance(row, Mapping):
                                    continue
                                observed_statuses.add(str(row.get("status", "")).upper())
                                row_codes = row.get("codes", [])
                                if isinstance(row_codes, list):
                                    observed_codes.update(str(code) for code in row_codes)
                                row_result = row.get("result")
                                if isinstance(row_result, Mapping):
                                    result_codes = row_result.get("codes", [])
                                    if isinstance(result_codes, list):
                                        observed_codes.update(str(code) for code in result_codes)
                                mutated = row.get(
                                    "mutated",
                                    row_result.get("mutated")
                                    if isinstance(row_result, Mapping)
                                    else None,
                                )
                                mutated_false = (
                                    mutated_false or type(mutated) is bool and mutated is False
                                )
                                before = row.get("state_ref_before")
                                after = row.get("state_ref_after")
                                if (
                                    isinstance(before, Mapping)
                                    and isinstance(after, Mapping)
                                    and canonical_ref is not None
                                ):
                                    try:
                                        unchanged_canonical_ref = (
                                            unchanged_canonical_ref
                                            or normalize_state_ref(before)
                                            == canonical_ref
                                            == normalize_state_ref(after)
                                        )
                                    except ValueError:
                                        pass
                            if isinstance(tamper_trace, Mapping):
                                trace_codes = tamper_trace.get("errors", [])
                                if isinstance(trace_codes, list):
                                    observed_codes.update(str(code) for code in trace_codes)
                                trace_status = str(
                                    tamper_trace.get(
                                        "status", tamper_trace.get("terminal_status", "")
                                    )
                                ).upper()
                                if trace_status:
                                    observed_statuses.add(trace_status)
                                try:
                                    initial_ref = normalize_state_ref(
                                        tamper_trace.get("initial_state_ref")
                                    )
                                    final_ref = normalize_state_ref(
                                        tamper_trace.get("final_state_ref")
                                    )
                                    unchanged_canonical_ref = (
                                        unchanged_canonical_ref
                                        or canonical_ref is not None
                                        and initial_ref == canonical_ref == final_ref
                                    )
                                except (TypeError, ValueError):
                                    pass
                            process_evidence = bool(
                                isinstance(tamper_trace, Mapping)
                                and tamper_engine.get("returncode") in (0, 1)
                                and (
                                    tamper_engine.get("returncode") == 0
                                    or (
                                        str(tamper_trace.get("status", "")).upper()
                                        in rejection_statuses
                                        and isinstance(tamper_trace.get("errors"), list)
                                        and bool(tamper_trace["errors"])
                                        and {str(code) for code in tamper_trace["errors"]}
                                        <= {"ACTION_NOT_APPLIED"} | canonical_rejection_codes
                                    )
                                )
                                and tamper_engine.get("input_exists") is True
                                and tamper_engine.get("input_nonempty") is True
                                and tamper_engine.get("input_bytes_preserved") is True
                            )
                            explicit_rejection = bool(observed_statuses & rejection_statuses)
                            explicit_code_rejection = bool(
                                observed_codes & canonical_rejection_codes
                            )
                            replay["godot_tamper_rejected"] = (
                                process_evidence
                                and "APPLIED" not in observed_statuses
                                and (
                                    tamper_engine.get("returncode") == 0 or explicit_code_rejection
                                )
                                and unchanged_canonical_ref
                                and (
                                    (explicit_rejection and mutated_false)
                                    or explicit_code_rejection
                                )
                            )
                        if not replay["godot_tamper_rejected"]:
                            failure_code = (
                                "semantic_tamper_accepted"
                                if "APPLIED" in observed_statuses
                                else "tamper_replay_evidence_missing"
                            )
                            errors.append(
                                {
                                    "category": "replay_failure",
                                    "code": failure_code,
                                    "error": "tampered decision lacks valid sidecar/process rejection evidence with unchanged canonical state",
                                }
                            )
    except AdmissionShortCircuit:
        pass
    except (ProtocolError, ControllerFailure, KeyError, ValueError, OSError) as exc:
        errors.append(classify_exception(exc))
    finally:
        if request is not None and controller is not None:
            try:
                python_snapshot = controller.export_trace(
                    request["session_id"], session_epoch=request["session_epoch"]
                )
            except ControllerFailure as exc:
                errors.append(classify_exception(exc))
    if python_snapshot is not None:
        python_rows = python_snapshot.get("rows", [])
        try:
            python_replay = ReplayValidator.validate(
                python_snapshot, expected_session_id=request["session_id"] if request else None
            )
            python_replay["source"] = "controller.export_trace"
            python_replay["model_calls"] = 0
            replay["python"] = python_replay
            replay["snapshot"] = python_snapshot
            replay["records"] = python_rows
        except (ProtocolError, ControllerFailure) as exc:
            replay["python"] = {
                "valid": False,
                "rows": len(python_rows) if isinstance(python_rows, list) else 0,
                "model_calls": 0,
                "source": "controller.export_trace",
                "error": classify_exception(exc),
            }
            replay["snapshot"] = python_snapshot
            replay["records"] = python_rows if isinstance(python_rows, list) else []
    elif service_url and decision is not None:
        replay["python"] = {
            "valid": False,
            "rows": 0,
            "model_calls": 0,
            "source": "remote_service",
            "error": {
                "category": "replay_failure",
                "code": "remote_python_replay_unavailable",
                "error": "complete canonical replay was not supplied by remote service",
            },
        }
    python_valid = bool(replay.get("python", {}).get("valid") is True)
    engine_valid = bool(replay.get("engine_fixture_reexecution", {}).get("valid") is True)
    replay["valid"] = python_valid and engine_valid
    replay["model_calls"] = 0
    decision_body = decision.get("body", {}) if isinstance(decision, Mapping) else {}
    typed_intent = (
        decision_body.get("typed_intent", {}) if isinstance(decision_body, Mapping) else {}
    )
    experiment_trace = (
        engine.get("experiment", {}).get("trace")
        if isinstance(engine.get("experiment"), Mapping)
        else None
    )
    final_snapshot = extract_final_snapshot(
        experiment_trace if isinstance(experiment_trace, Mapping) else None
    )
    terminal_status = "UNAVAILABLE"
    if isinstance(experiment_trace, Mapping):
        terminal_status = str(
            experiment_trace.get("status", experiment_trace.get("terminal_status", "FAILED"))
        )
    elif errors:
        terminal_status = "FAILED"
    engine_completed = (
        isinstance(engine.get("experiment"), Mapping)
        and engine["experiment"].get("status") == "completed"
        and isinstance(experiment_trace, Mapping)
        and experiment_trace.get("passed") is True
    )
    status = (
        "completed" if engine_completed and replay["valid"] and not errors else "assigned_failure"
    )
    record: dict[str, Any] = {
        "record_schema_version": "npc-goal-recovery/record-1",
        "assignment_id": assignment["assignment_id"],
        "packet_id": assignment["packet_id"],
        "case_id": assignment["case_id"],
        "arm": assignment["arm"],
        "repetition": assignment["repetition"],
        "regime": case["regime"],
        "status": status,
        "terminal_status": terminal_status,
        "failure": errors,
        "fixture_ref": case["fixture_ref"],
        "fixture_input_sha256": assignment["fixture_input_sha256"],
        "raw_utterance_sha256": case["raw_utterance_sha256"],
        "goal": {
            "scenario_id": SCENARIO_ID,
            "npc_id": NPC_ID,
            "goal_id": GOAL_ID,
            "goal_version": GOAL_VERSION,
        },
        "observation": actual_snapshot["observation"] if actual_snapshot else None,
        "state_ref_before": actual_snapshot["state_ref"] if actual_snapshot else None,
        "state_ref_after": final_snapshot["state_ref"] if final_snapshot else None,
        "request": redacted_request(request, case) if request else None,
        "decision": decision,
        "claims": list(typed_intent.get("claims", [])) if isinstance(typed_intent, Mapping) else [],
        "planning_context": {
            "digest": decision_body.get("planning_context_digest"),
            "reviewed": decision is not None,
        },
        "plan": {
            "plan_id": decision_body.get("plan_id"),
            "steps": decision_body.get("steps", []),
            "status": decision_body.get("status"),
        }
        if decision is not None
        else None,
        "proposals": list(decision_body.get("steps", [])) if decision is not None else [],
        "results": result_envelopes,
        "acks": ack_envelopes,
        "world_events": list(experiment_trace.get("events", []))
        if isinstance(experiment_trace, Mapping)
        else [],
        "revisions": [
            item.get("body", {}).get("engine_revision")
            for item in result_envelopes
            if isinstance(item.get("body"), Mapping)
        ],
        "events": events,
        "engine": engine,
        "replay": replay,
        "goal_reached": experiment_trace.get("goal_reached")
        if isinstance(experiment_trace, Mapping)
        else None,
        "recovery_eligible": experiment_trace.get("recovery_eligible")
        if isinstance(experiment_trace, Mapping)
        else None,
        "recovery_unreachable": experiment_trace.get("recovery_unreachable")
        if isinstance(experiment_trace, Mapping)
        else None,
        "usage": {
            "available": False,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
            "model_revision_available": False,
            "model_revision": None,
        },
        "model": {
            "requested": model,
            "returned": decision.get("provenance", {}).get("model") if decision else None,
            "available": bool(decision and decision.get("provenance", {}).get("model")),
        },
        "cli_exec_attempts": cli_exec_attempts,
        "model_calls": len(cli_exec_attempts),
        "seed": case["seed"],
        "seed_scope": {"fixture": case["seed"], "model_sampling": None},
        "latency_ms": (time.perf_counter() - started) * 1000,
        "budget": dict(budget),
        "repair": {
            "attempts": 0,
            "replans": len([item for item in events if item.get("type") == "observation_replan"]),
            "fallback_used": False,
        },
        "hashes": {
            "config_hash": assignment["config_hash"],
            "fixture_input_sha256": assignment["fixture_input_sha256"],
            "execution_state_before_sha256": actual_snapshot["state_ref"]["sha256"]
            if actual_snapshot
            else None,
            "execution_state_after_sha256": final_snapshot["state_ref"]["sha256"]
            if final_snapshot
            else None,
            "decision_content_sha256": decision.get("content_sha256") if decision else None,
            "bootstrap_input_sha256_before": engine.get("bootstrap", {}).get("input_sha256_before"),
            "bootstrap_input_sha256_after": engine.get("bootstrap", {}).get("input_sha256_after"),
            "experiment_input_sha256_before": engine.get("experiment", {}).get(
                "input_sha256_before"
            ),
            "experiment_input_sha256_after": engine.get("experiment", {}).get("input_sha256_after"),
        },
        "claim_boundary": dict(CLAIM_BOUNDARY),
        "provenance": {
            "config_hash": assignment["config_hash"],
            "source_project_config_sha256": assignment["source_project_config_sha256"],
            "npc_protocol_config_sha256": assignment["npc_protocol_config_sha256"],
            "source_schema_sha256": assignment["source_schema_sha256"],
            "policy_hash": assignment.get("policy_hash"),
            "fixture_source_kind": case["source_kind"],
            "utterance_source_kind": assignment["utterance_source_kind"],
            "independent_source": False,
            "reference_is_semantic_gold": False,
        },
    }
    record["record_sha256"] = digest(record)
    return record


def _observed_count(rows: list[Mapping[str, Any]], key: str) -> tuple[int | None, bool]:
    values = [row.get(key) for row in rows]
    if not values or any(type(value) is not bool for value in values):
        return None, False
    return sum(1 for value in values if value), True


def aggregate(
    records: list[Mapping[str, Any]],
    assignments: list[Mapping[str, Any]],
    *,
    packet_id: str,
    npc_protocol_config_sha256: str,
    source_schema_sha256: str,
    source_project_config_sha256: str,
    policy_hash: str | None,
    config_hash: str,
) -> dict[str, Any]:
    by_arm: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        rows = [row for row in records if row.get("arm") == arm]
        failures: dict[str, int] = {}
        statuses: dict[str, int] = {}
        for row in rows:
            statuses[str(row.get("status", "unknown"))] = (
                statuses.get(str(row.get("status", "unknown")), 0) + 1
            )
            for failure in row.get("failure", []):
                code = str(failure.get("code", "unknown"))
                failures[code] = failures.get(code, 0) + 1
        goal_reached_n, goal_available = _observed_count(rows, "goal_reached")
        recovery_eligible_n, eligible_available = _observed_count(rows, "recovery_eligible")
        recovery_unreachable_n, unreachable_available = _observed_count(
            rows, "recovery_unreachable"
        )
        by_arm[arm] = {
            "n": len(rows),
            "source_independent_n": sum(
                1 for row in rows if row.get("provenance", {}).get("independent_source")
            ),
            "completed_n": sum(1 for row in rows if row.get("status") == "completed"),
            "assigned_failure_n": sum(1 for row in rows if row.get("status") == "assigned_failure"),
            "failures_by_code": failures,
            "terminal_status_counts": statuses,
            "goal_reached_n": goal_reached_n,
            "goal_reached_available": goal_available,
            "recovery_eligible_n": recovery_eligible_n,
            "recovery_eligible_available": eligible_available,
            "recovery_unreachable_n": recovery_unreachable_n,
            "recovery_unreachable_available": unreachable_available,
            "success": None,
        }
    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "packet_id": packet_id,
        "generated_at_unix": time.time(),
        "config_hash": config_hash,
        "source_project_config_sha256": source_project_config_sha256,
        "npc_protocol_config_sha256": npc_protocol_config_sha256,
        "source_schema_sha256": source_schema_sha256,
        "policy_hash": policy_hash,
        "assignment_count": len(assignments),
        "engineering_count": len(assignments) if packet_id == "NPC-ENG1" else None,
        "screening_assignment_count": len(assignments) if packet_id == "NPC-SCR1" else None,
        "arms": by_arm,
        "usage": {
            "token_accounting_available": False,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
            "model_revision_available": False,
            "model_revision": None,
        },
        "denominators": {
            "all_preassigned": len(assignments),
            "recovery_eligible": sum(v["recovery_eligible_n"] or 0 for v in by_arm.values())
            if all(v["recovery_eligible_available"] for v in by_arm.values())
            else None,
            "recovery_unreachable": sum(v["recovery_unreachable_n"] or 0 for v in by_arm.values())
            if all(v["recovery_unreachable_available"] for v in by_arm.values())
            else None,
        },
        "claims": dict(CLAIM_BOUNDARY),
        "validation": {
            "assignment_complete": False,
            "hashes_valid": False,
            "replay_valid": False,
            "provenance_valid": False,
            "claim_boundaries_valid": False,
        },
        "godot": {
            "experiment_available": any(
                row.get("engine", {}).get("experiment", {}).get("available") for row in records
            ),
            "replay_available": any(
                row.get("engine", {}).get("replay", {}).get("available") for row in records
            ),
        },
    }


def write_sha256_manifest(output_dir: Path) -> None:
    files: list[dict[str, str]] = []
    packet_dir = output_dir.resolve()
    for path in sorted(packet_dir.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(packet_dir)
        if relative_path.name in {"sha256-manifest.json", "validation-report.json"}:
            continue
        if "godot-project" in relative_path.parts:
            continue
        files.append(
            {
                "path": relative_path.as_posix(),
                "sha256": sha256_file(path),
            }
        )
    write_json(
        packet_dir / "sha256-manifest.json",
        {"schema_version": "npc-goal-recovery/receipts-1", "files": files},
    )


def replay_report(records: list[Mapping[str, Any]], packet_id: str) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    counts = {
        "python_eligible": 0,
        "python_failed": 0,
        "python_unavailable": 0,
        "godot_eligible": 0,
        "godot_failed": 0,
        "godot_unavailable": 0,
    }
    for record in records:
        replay = record.get("replay", {})
        py = replay.get("python", {}) if isinstance(replay, Mapping) else {}
        if isinstance(py, Mapping) and py:
            if py.get("valid") is True:
                counts["python_eligible"] += 1
            else:
                counts["python_failed"] += 1
        else:
            counts["python_unavailable"] += 1
        engine = record.get("engine", {})
        godot = (
            engine.get("replay", {})
            if isinstance(engine, Mapping) and isinstance(engine.get("replay"), Mapping)
            else {}
        )
        comparison = engine.get("replay_comparison") if isinstance(engine, Mapping) else None
        fixture_reexecution = (
            replay.get("engine_fixture_reexecution", {}) if isinstance(replay, Mapping) else {}
        )
        godot_eligible = (
            isinstance(fixture_reexecution, Mapping) and fixture_reexecution.get("valid") is True
        )
        godot_evidence = bool(godot) or isinstance(comparison, Mapping)
        if godot_eligible:
            counts["godot_eligible"] += 1
        elif godot_evidence and (
            godot.get("available") is not False or isinstance(comparison, Mapping)
        ):
            counts["godot_failed"] += 1
        else:
            counts["godot_unavailable"] += 1
        rows.append(
            {
                "assignment_id": record.get("assignment_id"),
                "status": record.get("status"),
                "assigned_failure": record.get("status") == "assigned_failure",
                "python": py,
                "godot": godot,
                "model_calls": 0,
            }
        )
    return {
        "schema_version": "npc-goal-recovery/replay-1",
        "packet_id": packet_id,
        "model_calls": 0,
        "denominators": counts,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", choices=("engineering", "screening", "all"), default="all")
    parser.add_argument(
        "--engineering-fixtures",
        type=Path,
        default=ROOT / "data/fixtures/npc-goal-recovery/validated-v5/engineering.json",
    )
    parser.add_argument(
        "--screening-fixtures",
        type=Path,
        default=ROOT / "data/fixtures/npc-goal-recovery/validated-v5/screening.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "research/academic-pipeline/npc-goal-recovery/verified-run-006",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--service-url", default=None)
    parser.add_argument("--godot-binary", default=None)
    parser.add_argument("--godot-project", type=Path, default=ROOT / "game-track/godot")
    parser.add_argument("--godot-timeout", type=float, default=120.0)
    parser.add_argument(
        "--skip-model",
        action="store_true",
        help="record P rows unavailable without invoking a model; still run deterministic R/O arms",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="freeze assignment manifests without invoking interpreters",
    )
    args = parser.parse_args()
    args.output_dir = args.output_dir.resolve()
    args.godot_project = args.godot_project.resolve()
    run_mode = "dry_run" if args.dry_run else "preflight" if args.skip_model else "publish"
    canonical_output = (
        ROOT / "research/academic-pipeline/npc-goal-recovery/verified-run-006"
    ).resolve()
    if run_mode != "publish" and args.output_dir == canonical_output:
        parser.error(
            "preflight/dry-run requires a separate output directory; canonical publish output is forbidden"
        )
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        parser.error("output directory must be fresh; existing experimental evidence is immutable")
    if run_mode == "publish" and args.service_url:
        parser.error("publish requires the locally observed official CLI execution path")
    if args.engineering_fixtures is not None:
        args.engineering_fixtures = args.engineering_fixtures.resolve()
    if args.screening_fixtures is not None:
        args.screening_fixtures = args.screening_fixtures.resolve()
    config_path = ROOT / "configs/npc-goal-recovery.json"
    schema_path = ROOT / "game-track/schemas/npc-goal-recovery.schema.json"
    config = read_json(config_path)
    config_hash = canonical_config_hash(config_path)
    npc_protocol_config_sha256 = sha256_file(config_path)
    source_schema_sha256 = sha256_file(schema_path)
    source_project_config_sha256 = source_project_config_hash(ROOT)
    budget = protocol_budget(config)
    runtime_source_hashes_before = {
        path: sha256_file(ROOT / path)
        for path in (
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
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / ".gitignore").write_text("godot-project/\n", encoding="utf-8")
    staged_godot_project: Path | None = None
    godot_import: dict[str, Any] = {
        "status": "not_run",
        "returncode": None,
        "project_path": None,
        "source_project_unchanged": None,
    }
    policy_engine: dict[str, Any] = {"status": "not_run"}
    admission_failure: dict[str, Any] | None = None
    if not args.dry_run:
        staged_godot_project = args.output_dir / "godot-project"
        if not staged_godot_project.exists():
            stage_project(args.godot_project, staged_godot_project)
        staged_godot_project = staged_godot_project.resolve()
        args.godot_project = staged_godot_project
        source_unchanged = source_project_config_hash(ROOT) == source_project_config_sha256
        godot_cmd = (
            shutil.which(args.godot_binary or "godot")
            if not args.godot_binary or not Path(args.godot_binary).is_file()
            else args.godot_binary
        )
        if godot_cmd:
            import_command = [
                godot_cmd,
                "--headless",
                "--audio-driver",
                "Dummy",
                "--path",
                str(staged_godot_project),
                "--import",
            ]
            try:
                import_run = subprocess.run(
                    import_command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=args.godot_timeout,
                )
                godot_import = {
                    "status": "completed" if import_run.returncode == 0 else "failed",
                    "returncode": import_run.returncode,
                    "command": import_command,
                    "project_path": str(staged_godot_project),
                    "source_project_unchanged": source_unchanged,
                }
                if import_run.returncode != 0:
                    godot_import["error"] = f"godot_import_returncode:{import_run.returncode}"
            except subprocess.TimeoutExpired as exc:
                godot_import = {
                    "status": "deadline_timeout",
                    "returncode": None,
                    "command": import_command,
                    "project_path": str(staged_godot_project),
                    "source_project_unchanged": source_unchanged,
                    "error": "godot_deadline",
                }
                if exc.stdout:
                    godot_import["stdout"] = (
                        exc.stdout.decode("utf-8", errors="replace")
                        if isinstance(exc.stdout, bytes)
                        else str(exc.stdout)
                    )
                if exc.stderr:
                    godot_import["stderr"] = (
                        exc.stderr.decode("utf-8", errors="replace")
                        if isinstance(exc.stderr, bytes)
                        else str(exc.stderr)
                    )
            except OSError as exc:
                godot_import = {
                    "status": "launch_failed",
                    "returncode": None,
                    "command": import_command,
                    "project_path": str(staged_godot_project),
                    "source_project_unchanged": source_unchanged,
                    "error": type(exc).__name__,
                }
        else:
            godot_import = {
                "status": "unavailable",
                "returncode": None,
                "project_path": str(staged_godot_project),
                "source_project_unchanged": source_unchanged,
                "error": "godot_binary_unavailable",
            }
    packets: list[tuple[str, list[dict[str, Any]], Path, int]] = []
    if args.packet in {"engineering", "all"}:
        packets.append(
            (
                "NPC-ENG1",
                load_cases(args.engineering_fixtures, "NPC-ENG1", 16),
                args.output_dir / "engineering-results.jsonl",
                16,
            )
        )
    if args.packet in {"screening", "all"}:
        packets.append(
            (
                "NPC-SCR1",
                load_cases(args.screening_fixtures, "NPC-SCR1", 12),
                args.output_dir / "screening-results.jsonl",
                72,
            )
        )
    frozen_policy_hash: str | None = None
    for _packet_id, packet_cases, _result_path, _expected_assignments in packets:
        for packet_case in packet_cases:
            case_policy = packet_case.get("policy_hash")
            source_policy = (
                packet_case.get("source_hashes", {}).get("policy_hash")
                if isinstance(packet_case.get("source_hashes"), Mapping)
                else None
            )
            if not is_sha256(case_policy) or case_policy != source_policy:
                raise ValueError(
                    f"{_packet_id}:{packet_case.get('id')}: frozen policy hash is missing or source-bound incorrectly"
                )
            if frozen_policy_hash is None:
                frozen_policy_hash = str(case_policy)
            elif frozen_policy_hash != case_policy:
                raise ValueError("validated-v5 packets disagree on frozen policy hash")
    policy_hash: str | None = frozen_policy_hash
    if not args.dry_run:
        import_status = str(godot_import.get("status"))
        if import_status != "completed":
            admission_failure = {
                "category": "engine_gate_failure",
                "code": f"godot_import_{import_status}",
                "error": str(godot_import.get("error", import_status)),
            }
        else:
            policy_path = args.output_dir / "godot-input" / "policy-bootstrap.json"
            policy_input = {
                "schema_version": "npc-engineering/input-1",
                "assignment_id": "NPC-POLICY-PREFLIGHT",
                "setup_operations": [],
                "seed_world_events": [],
                "in_dialogue": False,
                "request_context": {
                    "session_id": "npc-policy-preflight",
                    "episode_id": "npc-policy-preflight",
                    "session_epoch": 0,
                    "request_id": "npc-policy-preflight",
                    "goal_id": GOAL_ID,
                    "goal_version": GOAL_VERSION,
                },
                "decision": None,
                "mutations": [],
            }
            write_json(policy_path, policy_input)
            policy_engine = run_godot(
                binary=args.godot_binary,
                project=args.godot_project,
                mode="bootstrap",
                input_path=policy_path,
                log_dir=args.output_dir / "logs",
                timeout=args.godot_timeout,
            )
            actual_policy_hash = extract_policy_hash(
                policy_engine.get("trace") if isinstance(policy_engine, Mapping) else None
            )
            if policy_engine.get("status") != "completed" or not is_sha256(actual_policy_hash):
                admission_failure = {
                    "category": "engine_gate_failure",
                    "code": "policy_admission_unavailable",
                    "error": str(
                        policy_engine.get(
                            "error", policy_engine.get("status", "policy_hash_unavailable")
                        )
                    ),
                }
            elif actual_policy_hash != policy_hash:
                admission_failure = {
                    "category": "engine_gate_failure",
                    "code": "policy_hash_mismatch",
                    "error": "live policy hash differs from frozen validated-v5 assignment policy",
                }
    all_records: list[dict[str, Any]] = []
    for packet_id, cases, result_path, expected_assignments in packets:
        assignments = make_assignments(
            cases,
            packet_id=packet_id,
            config_hash=config_hash,
            npc_protocol_config_sha256=npc_protocol_config_sha256,
            source_schema_sha256=source_schema_sha256,
            source_project_config_sha256=source_project_config_sha256,
            policy_hash=policy_hash,
            budget=budget,
        )
        if len(assignments) != expected_assignments:
            raise ValueError(
                f"{packet_id}: expected {expected_assignments} assignments, got {len(assignments)}"
            )
        manifest = {
            "schema_version": PACKET_SCHEMA_VERSION,
            "packet_id": packet_id,
            "config_hash": config_hash,
            "source_project_config_sha256": source_project_config_sha256,
            "npc_protocol_config_sha256": npc_protocol_config_sha256,
            "source_schema_sha256": source_schema_sha256,
            "policy_hash": policy_hash,
            "budget": dict(budget),
            "claim_boundary": dict(CLAIM_BOUNDARY),
            "assignment_count": len(assignments),
            "assignments": assignments,
        }
        manifest_path = args.output_dir / (
            "engineering-assignment-manifest.json"
            if packet_id == "NPC-ENG1"
            else "screening-assignment-manifest.json"
        )
        freeze_manifest(manifest_path, manifest)
        if args.dry_run:
            continue
        existing = (
            {row.get("assignment_id"): row for row in load_jsonl_local(result_path)}
            if result_path.exists()
            else {}
        )
        case_map = {case["id"]: case for case in cases}
        records = list(existing.values())
        for assignment in assignments:
            if assignment["assignment_id"] in existing:
                continue
            record = execute_assignment(
                case_map[assignment["case_id"]],
                assignment,
                budget=budget,
                model=args.model,
                service_url=args.service_url,
                godot_binary=args.godot_binary,
                godot_project=args.godot_project,
                output_dir=args.output_dir,
                godot_timeout=args.godot_timeout,
                skip_model=args.skip_model,
                admission_failure=admission_failure,
            )
            records.append(record)
            existing[assignment["assignment_id"]] = record
        records = [
            existing[assignment["assignment_id"]]
            for assignment in assignments
            if assignment["assignment_id"] in existing
        ]
        write_jsonl_preserving(result_path, records)
        aggregate_path = args.output_dir / (
            "engineering-aggregate.json" if packet_id == "NPC-ENG1" else "aggregate.json"
        )
        packet_aggregate = aggregate(
            records,
            assignments,
            packet_id=packet_id,
            config_hash=config_hash,
            npc_protocol_config_sha256=npc_protocol_config_sha256,
            source_schema_sha256=source_schema_sha256,
            source_project_config_sha256=source_project_config_sha256,
            policy_hash=policy_hash,
        )
        packet_aggregate["run_mode"] = run_mode
        packet_aggregate["cli_exec_attempt_count"] = sum(row["model_calls"] for row in records)
        write_json(aggregate_path, packet_aggregate)
        all_records.extend(records)
    source_project_config_sha256_after = source_project_config_hash(ROOT)
    source_manifest = {
        "schema_version": PACKET_SCHEMA_VERSION,
        "config_hash": config_hash,
        "source_project_config_sha256": source_project_config_sha256,
        "source_project_config_sha256_after": source_project_config_sha256_after,
        "source_project_unchanged": source_project_config_sha256_after
        == source_project_config_sha256,
        "godot_import": godot_import,
        "staged_godot_project": str(staged_godot_project) if staged_godot_project else None,
        "npc_protocol_config_sha256": npc_protocol_config_sha256,
        "source_schema_sha256": source_schema_sha256,
        "policy_hash": policy_hash,
        "packets": [packet_id for packet_id, *_ in packets],
        "counts": {packet_id: expected for packet_id, _cases, _path, expected in packets},
        "redaction": "raw utterances are transient; persisted records retain fixture and utterance digests only",
    }
    source_manifest["policy_admission"] = policy_engine
    source_manifest["admission_failure"] = (
        dict(admission_failure) if admission_failure is not None else None
    )
    source_manifest["run_mode"] = run_mode
    source_manifest["cli_exec_attempt_count"] = sum(row["model_calls"] for row in all_records)
    source_manifest["artifact_root"] = str(args.output_dir)
    source_manifest["runtime_source_hashes_before"] = runtime_source_hashes_before
    source_manifest["runtime_source_hashes_after"] = {
        path: sha256_file(ROOT / path) for path in runtime_source_hashes_before
    }
    source_manifest["runtime_sources_unchanged"] = (
        source_manifest["runtime_source_hashes_after"] == runtime_source_hashes_before
    )
    write_json(args.output_dir / "source-manifest.json", source_manifest)
    if all_records and not args.dry_run:
        write_json(
            args.output_dir / "replay-results.json",
            replay_report(
                all_records,
                "NPC-SCR1"
                if args.packet == "screening"
                else "NPC-ENG1"
                if args.packet == "engineering"
                else "NPC-ALL",
            ),
        )
        write_sha256_manifest(args.output_dir)
    print(
        json.dumps(
            {
                "status": "ok",
                "packets": [packet_id for packet_id, *_ in packets],
                "records": len(all_records),
                "output_dir": str(args.output_dir),
                "files": sorted(path.name for path in args.output_dir.iterdir() if path.is_file()),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return (
        0
        if source_manifest["runtime_sources_unchanged"]
        and source_manifest["source_project_unchanged"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
