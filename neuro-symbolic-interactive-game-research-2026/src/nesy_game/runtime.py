"""Bounded validate/repair/commit loop; models never mutate state directly."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import fields, is_dataclass, replace
from pathlib import Path
from typing import Any

from .contracts import CandidateAction, CommitOutcome, TraceAttempt, ValidationResult, WorldState
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
    """Append one self-verifying outcome; callers own file retention and locking."""

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
