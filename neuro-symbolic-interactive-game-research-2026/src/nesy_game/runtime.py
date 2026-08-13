"""Bounded validate/repair/commit loop; models never mutate state directly."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any

from .contracts import (
    ActionPolicy,
    CandidateAction,
    CommitOutcome,
    TraceAttempt,
    ValidationResult,
    WorldState,
)
from .validator import validate_candidate

Repairer = Callable[[WorldState, CandidateAction, ValidationResult, int], CandidateAction]


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {key: to_jsonable(child) for key, child in sorted(value.items())}
    if isinstance(value, (set, frozenset)):
        converted = [to_jsonable(child) for child in value]
        return sorted(converted, key=lambda child: json.dumps(child, sort_keys=True))
    if isinstance(value, (list, tuple)):
        return [to_jsonable(child) for child in value]
    return value


def _require_mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")  # noqa: TRY004
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{field} keys must be strings")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    missing = sorted(expected - value.keys())
    extra = sorted(value.keys() - expected)
    if missing or extra:
        raise ValueError(f"{field} fields mismatch: missing={missing}, extra={extra}")


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _require_exact_int(value: Any, field: str, *, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        raise ValueError(f"{field} must be a non-negative exact integer")
    return value


def _require_string_list(value: Any, field: str) -> frozenset[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array of strings")  # noqa: TRY004
    parsed = [_require_nonempty_string(item, f"{field} item") for item in value]
    if len(parsed) != len(set(parsed)):
        raise ValueError(f"{field} must not contain duplicates")
    return frozenset(parsed)


def _validate_json_value(value: Any, field: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise ValueError(f"{field} contains a non-finite number")
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{field}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _require_nonempty_string(key, f"{field} key")
            _validate_json_value(child, f"{field}.{key}")
        return
    raise ValueError(f"{field} contains a non-JSON value")


def _trace_hash(
    state: WorldState,
    trace: tuple[TraceAttempt, ...],
    context: Mapping[str, Any],
    status: str,
    outcome_state: WorldState,
    final_candidate: CandidateAction,
    final_validation: ValidationResult,
    attempts: int,
) -> str:
    record = _trace_hash_record(
        state,
        trace,
        context,
        status,
        outcome_state,
        final_candidate,
        final_validation,
        attempts,
    )
    payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _trace_hash_record(
    state: WorldState,
    trace: tuple[TraceAttempt, ...] | list[dict[str, Any]],
    context: Mapping[str, Any],
    status: str,
    outcome_state: WorldState | Mapping[str, Any],
    final_candidate: CandidateAction | Mapping[str, Any],
    final_validation: ValidationResult | Mapping[str, Any],
    attempts: int,
) -> dict[str, Any]:
    return {
        "status": status,
        "state": to_jsonable(outcome_state),
        "candidate": to_jsonable(final_candidate),
        "validation": to_jsonable(final_validation),
        "attempts": attempts,
        "prior_state": to_jsonable(state),
        "trace": to_jsonable(trace),
        "trace_context": to_jsonable(context),
    }


def _apply_valid(state: WorldState, action: CandidateAction) -> WorldState:
    result = validate_candidate(state, action)
    if not result.valid:
        raise ValueError("cannot apply an invalid candidate")
    next_stage = (
        state.quest_stage if action.quest_stage_effect is None else action.quest_stage_effect
    )
    next_id = hashlib.sha256(f"{state.state_id}:{action.action_id}".encode()).hexdigest()[:16]
    return replace(
        state,
        state_id=next_id,
        facts=state.facts | action.effects,
        quest_stage=next_stage,
    )


def execute_with_repair(
    state: WorldState,
    initial: CandidateAction,
    repairer: Repairer | None = None,
    repair_budget: int = 0,
    trace_context: Mapping[str, Any] | None = None,
) -> CommitOutcome:
    """Validate, optionally repair, and atomically commit or fall back unchanged."""

    if repair_budget < 0:
        raise ValueError("repair_budget must be non-negative")
    context = dict(trace_context or {})
    candidate = initial
    trace: list[TraceAttempt] = []
    for attempt in range(repair_budget + 1):
        result = validate_candidate(state, candidate)
        trace.append(TraceAttempt(attempt, candidate, result))
        frozen_trace = tuple(trace)
        if result.valid:
            committed_state = _apply_valid(state, candidate)
            digest = _trace_hash(
                state,
                frozen_trace,
                context,
                "commit",
                committed_state,
                candidate,
                result,
                attempt,
            )
            return CommitOutcome(
                status="commit",
                state=committed_state,
                candidate=candidate,
                validation=result,
                attempts=attempt,
                trace_hash=digest,
                prior_state=state,
                trace=frozen_trace,
                trace_context=context,
            )
        if repairer is None or attempt == repair_budget:
            digest = _trace_hash(
                state,
                frozen_trace,
                context,
                "fallback",
                state,
                candidate,
                result,
                attempt,
            )
            return CommitOutcome(
                status="fallback",
                state=state,
                candidate=candidate,
                validation=result,
                attempts=attempt,
                trace_hash=digest,
                prior_state=state,
                trace=frozen_trace,
                trace_context=context,
            )
        candidate = repairer(state, candidate, result, attempt + 1)
    raise AssertionError("bounded loop must return")


def write_trace_jsonl(path: str | Path, outcome: CommitOutcome) -> None:
    """Append one content-checksummed outcome; callers own retention and locking."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_jsonable(outcome), ensure_ascii=False, sort_keys=True) + "\n")


def verify_trace_record(record: Mapping[str, Any]) -> bool:
    """Verify the content hash of a JSON-decoded trace record."""

    required = {
        "status",
        "state",
        "candidate",
        "validation",
        "attempts",
        "prior_state",
        "trace",
        "trace_context",
        "trace_hash",
    }
    if set(record) != required:
        return False
    payload = {
        "status": record["status"],
        "state": record["state"],
        "candidate": record["candidate"],
        "validation": record["validation"],
        "attempts": record["attempts"],
        "prior_state": record["prior_state"],
        "trace": record["trace"],
        "trace_context": record["trace_context"],
    }
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest() == record["trace_hash"]


def _world_state_from_json(data: Mapping[str, Any]) -> WorldState:
    data = _require_mapping(data, "world state")
    _require_exact_keys(
        data,
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
        "world state",
    )
    raw_policies = _require_mapping(data["action_policies"], "action_policies")
    policies = {
        _require_nonempty_string(action_type, "action policy key"): _policy_from_json(
            policy, f"action_policies.{action_type}"
        )
        for action_type, policy in raw_policies.items()
    }
    object_locations = _require_mapping(data["object_locations"], "object_locations")
    parsed_object_locations = {
        _require_nonempty_string(key, "object_locations key"): _require_nonempty_string(
            value, f"object_locations.{key}"
        )
        for key, value in object_locations.items()
    }
    return WorldState(
        state_id=_require_nonempty_string(data["state_id"], "state_id"),
        locations=_require_string_list(data["locations"], "locations"),
        reachable_locations=_require_string_list(
            data["reachable_locations"], "reachable_locations"
        ),
        object_locations=parsed_object_locations,
        inventory=_require_string_list(data["inventory"], "inventory"),
        facts=_require_string_list(data["facts"], "facts"),
        action_policies=policies,
        npc_knowledge=_string_set_mapping(data["npc_knowledge"], "npc_knowledge"),
        forbidden_disclosures=_string_set_mapping(
            data["forbidden_disclosures"], "forbidden_disclosures"
        ),
        quest_stage=_require_exact_int(data["quest_stage"], "quest_stage"),
    )


def _policy_from_json(data: Any, field: str) -> ActionPolicy:
    data = _require_mapping(data, field)
    _require_exact_keys(
        data,
        {
            "required_preconditions",
            "allowed_effects",
            "required_effects",
            "allowed_quest_stage_effects",
        },
        field,
    )
    raw_stage_effects = data["allowed_quest_stage_effects"]
    if not isinstance(raw_stage_effects, list):
        raise TypeError(f"{field}.allowed_quest_stage_effects must be an array")
    parsed_stage_effects = [
        _require_exact_int(value, f"{field}.allowed_quest_stage_effects item")
        for value in raw_stage_effects
    ]
    if len(set(parsed_stage_effects)) != len(parsed_stage_effects):
        raise ValueError(f"{field}.allowed_quest_stage_effects must not contain duplicates")
    return ActionPolicy(
        required_preconditions=_require_string_list(
            data["required_preconditions"], f"{field}.required_preconditions"
        ),
        allowed_effects=_require_string_list(data["allowed_effects"], f"{field}.allowed_effects"),
        required_effects=_require_string_list(
            data["required_effects"], f"{field}.required_effects"
        ),
        allowed_quest_stage_effects=frozenset(parsed_stage_effects),
    )


def _string_set_mapping(data: Any, field: str) -> dict[str, frozenset[str]]:
    data = _require_mapping(data, field)
    return {
        _require_nonempty_string(key, f"{field} key"): _require_string_list(value, f"{field}.{key}")
        for key, value in data.items()
    }


def _candidate_from_json(data: Mapping[str, Any]) -> CandidateAction:
    data = _require_mapping(data, "candidate")
    _require_exact_keys(
        data,
        {
            "action_id",
            "actor_id",
            "action_type",
            "preconditions",
            "effects",
            "required_objects",
            "used_facts",
            "disclosed_facts",
            "required_quest_stage",
            "quest_stage_effect",
            "narrative_text",
            "metadata",
        },
        "candidate",
    )
    quest_stage_effect = data["quest_stage_effect"]
    if quest_stage_effect is not None:
        quest_stage_effect = _require_exact_int(quest_stage_effect, "quest_stage_effect")
    narrative_text = data["narrative_text"]
    if not isinstance(narrative_text, str):
        raise ValueError("narrative_text must be a string")  # noqa: TRY004
    metadata = _require_mapping(data["metadata"], "metadata")
    _validate_json_value(metadata, "metadata")
    return CandidateAction(
        action_id=_require_nonempty_string(data["action_id"], "action_id"),
        actor_id=_require_nonempty_string(data["actor_id"], "actor_id"),
        action_type=_require_nonempty_string(data["action_type"], "action_type"),
        preconditions=_require_string_list(data["preconditions"], "preconditions"),
        effects=_require_string_list(data["effects"], "effects"),
        required_objects=_require_string_list(data["required_objects"], "required_objects"),
        used_facts=_require_string_list(data["used_facts"], "used_facts"),
        disclosed_facts=_require_string_list(data["disclosed_facts"], "disclosed_facts"),
        required_quest_stage=_require_exact_int(
            data["required_quest_stage"], "required_quest_stage"
        ),
        quest_stage_effect=quest_stage_effect,
        narrative_text=narrative_text,
        metadata=dict(metadata),
    )


def _validate_validation_record(data: Any, field: str) -> Mapping[str, Any]:
    data = _require_mapping(data, field)
    _require_exact_keys(data, {"valid", "errors", "checks_run"}, field)
    if not isinstance(data["valid"], bool):
        raise ValueError(f"{field}.valid must be a boolean")  # noqa: TRY004
    if not isinstance(data["errors"], list):
        raise ValueError(f"{field}.errors must be an array")  # noqa: TRY004
    for index, error in enumerate(data["errors"]):
        error_field = f"{field}.errors[{index}]"
        error = _require_mapping(error, error_field)
        _require_exact_keys(error, {"code", "entity", "reason", "repair_hint"}, error_field)
        for key in ("code", "entity", "reason", "repair_hint"):
            if not isinstance(error[key], str):
                raise ValueError(f"{error_field}.{key} must be a string")  # noqa: TRY004
    checks = data["checks_run"]
    if not isinstance(checks, list) or any(
        not isinstance(item, str) or not item for item in checks
    ):
        raise ValueError(f"{field}.checks_run must be an array of non-empty strings")
    return data


def replay_trace_record(record: Mapping[str, Any]) -> WorldState:
    """Verify the unkeyed checksum and semantically replay one outcome record."""

    record = _require_mapping(record, "trace record")
    if not verify_trace_record(record):
        raise ValueError("trace record hash verification failed")
    trace = record["trace"]
    attempts = record["attempts"]
    if not isinstance(trace, list) or not trace:
        raise ValueError("trace must be a non-empty array")
    attempts = _require_exact_int(attempts, "attempts")
    if attempts != len(trace) - 1:
        raise ValueError("trace attempt count is inconsistent")
    context = _require_mapping(record["trace_context"], "trace_context")
    _validate_json_value(context, "trace_context")
    prior_state = _world_state_from_json(record["prior_state"])
    parsed_candidates: list[CandidateAction] = []
    for index, raw_entry in enumerate(trace):
        entry_field = f"trace[{index}]"
        entry = _require_mapping(raw_entry, entry_field)
        _require_exact_keys(entry, {"attempt", "candidate", "validation"}, entry_field)
        attempt = _require_exact_int(entry["attempt"], f"{entry_field}.attempt")
        if attempt != index:
            raise ValueError("trace attempt sequence is not contiguous")
        candidate = _candidate_from_json(entry["candidate"])
        _validate_validation_record(entry["validation"], f"{entry_field}.validation")
        validation = validate_candidate(prior_state, candidate)
        if to_jsonable(validation) != entry["validation"]:
            raise ValueError(f"attempt {index} validation does not match deterministic validation")
        if index < len(trace) - 1 and validation.valid:
            raise ValueError("trace contains an attempt after an early valid candidate")
        parsed_candidates.append(candidate)

    _candidate_from_json(record["candidate"])
    _validate_validation_record(record["validation"], "validation")
    if trace[-1].get("candidate") != record["candidate"]:
        raise ValueError("top-level candidate differs from final trace attempt")
    if trace[-1].get("validation") != record["validation"]:
        raise ValueError("top-level validation differs from final trace attempt")

    candidate = parsed_candidates[-1]
    validation = validate_candidate(prior_state, candidate)
    if to_jsonable(validation) != record["validation"]:
        raise ValueError("recorded validation does not match deterministic validation")

    if record["status"] == "commit":
        if not validation.valid:
            raise ValueError("invalid candidate cannot have commit status")
        expected_state = _apply_valid(prior_state, candidate)
    elif record["status"] == "fallback":
        if validation.valid:
            raise ValueError("valid candidate cannot have fallback status")
        expected_state = prior_state
    else:
        raise ValueError(f"unsupported trace status: {record['status']}")
    recorded_state = _world_state_from_json(record["state"])
    if to_jsonable(expected_state) != to_jsonable(recorded_state):
        raise ValueError("recorded outcome state does not match replayed state")
    return expected_state


def replay_trace_jsonl(path: str | Path, initial_state: WorldState | None = None) -> WorldState:
    """Replay a JSONL episode and enforce state continuity between records."""

    expected_prior = initial_state
    count = 0
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if expected_prior is not None and record.get("prior_state") != to_jsonable(
                    expected_prior
                ):
                    raise ValueError("prior state does not continue from the preceding record")
                expected_prior = replay_trace_record(record)
                count += 1
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"invalid trace at line {line_number}: {exc}") from exc
    if count == 0 or expected_prior is None:
        raise ValueError("trace file contains no records")
    return expected_prior
