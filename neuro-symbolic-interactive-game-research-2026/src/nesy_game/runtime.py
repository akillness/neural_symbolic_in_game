"""Bounded validate/repair/commit loop; models never mutate state directly."""

from __future__ import annotations

import hashlib
import json
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
    if not required <= record.keys():
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
    policies = {
        action_type: ActionPolicy(
            required_preconditions=frozenset(policy["required_preconditions"]),
            allowed_effects=frozenset(policy["allowed_effects"]),
            required_effects=frozenset(policy.get("required_effects", [])),
        )
        for action_type, policy in data.get("action_policies", {}).items()
    }
    return WorldState(
        state_id=str(data["state_id"]),
        locations=frozenset(data["locations"]),
        reachable_locations=frozenset(data["reachable_locations"]),
        object_locations=data["object_locations"],
        inventory=frozenset(data["inventory"]),
        facts=frozenset(data["facts"]),
        action_policies=policies,
        npc_knowledge={
            key: frozenset(value) for key, value in data.get("npc_knowledge", {}).items()
        },
        forbidden_disclosures={
            key: frozenset(value) for key, value in data.get("forbidden_disclosures", {}).items()
        },
        quest_stage=int(data.get("quest_stage", 0)),
    )


def _candidate_from_json(data: Mapping[str, Any]) -> CandidateAction:
    return CandidateAction(
        action_id=str(data["action_id"]),
        actor_id=str(data["actor_id"]),
        action_type=str(data["action_type"]),
        preconditions=frozenset(data["preconditions"]),
        effects=frozenset(data["effects"]),
        required_objects=frozenset(data.get("required_objects", [])),
        used_facts=frozenset(data.get("used_facts", [])),
        disclosed_facts=frozenset(data.get("disclosed_facts", [])),
        required_quest_stage=int(data.get("required_quest_stage", 0)),
        quest_stage_effect=data.get("quest_stage_effect"),
        narrative_text=str(data.get("narrative_text", "")),
        metadata=data.get("metadata", {}),
    )


def replay_trace_record(record: Mapping[str, Any]) -> WorldState:
    """Verify the unkeyed checksum and semantically replay one outcome record."""

    if not verify_trace_record(record):
        raise ValueError("trace record hash verification failed")
    trace = record["trace"]
    attempts = record["attempts"]
    if not isinstance(trace, list) or not trace or attempts != len(trace) - 1:
        raise ValueError("trace attempt count is inconsistent")
    if [entry.get("attempt") for entry in trace] != list(range(len(trace))):
        raise ValueError("trace attempt sequence is not contiguous")
    if trace[-1].get("candidate") != record["candidate"]:
        raise ValueError("top-level candidate differs from final trace attempt")
    if trace[-1].get("validation") != record["validation"]:
        raise ValueError("top-level validation differs from final trace attempt")

    prior_state = _world_state_from_json(record["prior_state"])
    candidate = _candidate_from_json(record["candidate"])
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
    if to_jsonable(expected_state) != record["state"]:
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
