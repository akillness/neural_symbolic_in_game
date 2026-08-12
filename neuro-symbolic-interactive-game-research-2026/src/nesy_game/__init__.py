"""TRACE-RPG research primitives."""

from .contracts import (
    ActionPolicy,
    CandidateAction,
    CommitOutcome,
    TraceAttempt,
    ValidationError,
    ValidationResult,
    WorldState,
)
from .metrics import evaluate_trace
from .runtime import (
    execute_with_repair,
    replay_trace_jsonl,
    replay_trace_record,
    to_jsonable,
    verify_trace_record,
    write_trace_jsonl,
)
from .validator import validate_candidate

__all__ = [
    "ActionPolicy",
    "CandidateAction",
    "CommitOutcome",
    "TraceAttempt",
    "ValidationError",
    "ValidationResult",
    "WorldState",
    "evaluate_trace",
    "execute_with_repair",
    "replay_trace_jsonl",
    "replay_trace_record",
    "to_jsonable",
    "validate_candidate",
    "verify_trace_record",
    "write_trace_jsonl",
]
