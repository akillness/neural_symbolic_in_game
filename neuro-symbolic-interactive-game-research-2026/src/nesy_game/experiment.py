"""Deterministic offline experiment runner and recorded-response adapter."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .contracts import CandidateAction, CommitOutcome, WorldState
from .runtime import execute_with_repair, replay_trace_jsonl, replay_trace_record, to_jsonable


def _is_exact_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class AdapterFailure(RuntimeError):
    """A classified proposal failure retained in the treatment-policy estimand."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = (
            code if isinstance(code, str) and code.strip() else "adapter_failure:unclassified"
        )


@dataclass(frozen=True)
class ProposalResponse:
    candidate: CandidateAction
    provider_latency_ms: float
    input_tokens: int
    output_tokens: int

    def __post_init__(self) -> None:
        if not _is_finite_number(self.provider_latency_ms) or self.provider_latency_ms < 0:
            raise ValueError("provider latency must be finite and non-negative")
        if not _is_exact_int(self.input_tokens) or not _is_exact_int(self.output_tokens):
            raise ValueError("token counts must be exact integers")
        if self.input_tokens < 0 or self.output_tokens < 0:
            raise ValueError("token counts must be non-negative")


class ProposalAdapter(Protocol):
    model_id: str
    model_revision: str

    def propose(self, state: WorldState, scenario_id: str, seed: int) -> ProposalResponse: ...


AssignmentKey = tuple[str, str, int, str, str]


def _adapter_identity(adapter: Any) -> tuple[str, str, str | None]:
    try:
        model_id = adapter.model_id
        model_revision = adapter.model_revision
    except Exception as exc:  # noqa: BLE001 - untrusted adapter boundary
        return "unknown-adapter", "unknown-revision", f"adapter_contract:{type(exc).__name__}"
    if not isinstance(model_id, str) or not model_id:
        revision = model_revision if isinstance(model_revision, str) and model_revision else None
        return "unknown-adapter", revision or "unknown-revision", "adapter_contract:model_id"
    if not isinstance(model_revision, str) or not model_revision:
        return model_id, "unknown-revision", "adapter_contract:model_revision"
    return model_id, model_revision, None


def _normalize_proposal_response(value: Any) -> ProposalResponse:
    if not isinstance(value, ProposalResponse):
        raise AdapterFailure(
            "adapter_contract:response_type",
            f"adapter returned {type(value).__name__}, expected ProposalResponse",
        )
    if not isinstance(value.candidate, CandidateAction):
        raise AdapterFailure("adapter_contract:candidate_type", "candidate is not CandidateAction")
    try:
        candidate = candidate_from_mapping(to_jsonable(value.candidate))
    except AdapterFailure:
        raise
    except (TypeError, ValueError) as exc:
        raise AdapterFailure(
            "adapter_contract:candidate_serialization",
            f"candidate cannot be represented as strict JSON: {exc}",
        ) from exc
    return ProposalResponse(
        candidate=candidate,
        provider_latency_ms=value.provider_latency_ms,
        input_tokens=value.input_tokens,
        output_tokens=value.output_tokens,
    )


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AdapterFailure("parse_error", f"{field} must be a non-empty string")
    return value


def _string_set(value: Any, field: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise AdapterFailure("parse_error", f"{field} must be an array of strings")
    parsed = frozenset(_nonempty_string(item, f"{field} item") for item in value)
    if len(parsed) != len(value):
        raise AdapterFailure("parse_error", f"{field} must not contain duplicates")
    return parsed


def _validate_json_value(value: Any, field: str) -> None:
    if value is None or isinstance(value, (str, bool)) or _is_exact_int(value):
        return
    if isinstance(value, float):
        if math.isfinite(value):
            return
        raise AdapterFailure("parse_error", f"{field} contains a non-finite number")
    if isinstance(value, list):
        for index, child in enumerate(value):
            _validate_json_value(child, f"{field}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            _nonempty_string(key, f"{field} key")
            _validate_json_value(child, f"{field}.{key}")
        return
    raise AdapterFailure("parse_error", f"{field} contains a non-JSON value")


def candidate_from_mapping(data: Mapping[str, Any]) -> CandidateAction:
    """Parse a candidate without treating model-supplied fields as authoritative policy."""

    if not isinstance(data, Mapping):
        raise AdapterFailure("parse_error", "candidate must be an object")
    required = {"action_id", "actor_id", "action_type", "preconditions", "effects"}
    missing = sorted(required - data.keys())
    if missing:
        raise AdapterFailure("parse_error", f"candidate fields missing: {missing}")
    required_quest_stage = data.get("required_quest_stage", 0)
    quest_stage_effect = data.get("quest_stage_effect")
    narrative_text = data.get("narrative_text", "")
    metadata = data.get("metadata", {})
    if not _is_exact_int(required_quest_stage) or required_quest_stage < 0:
        raise AdapterFailure("parse_error", "required_quest_stage must be a non-negative integer")
    if quest_stage_effect is not None and (
        not _is_exact_int(quest_stage_effect) or quest_stage_effect < 0
    ):
        raise AdapterFailure(
            "parse_error", "quest_stage_effect must be null or a non-negative integer"
        )
    if not isinstance(narrative_text, str):
        raise AdapterFailure("parse_error", "narrative_text must be a string")
    if not isinstance(metadata, Mapping):
        raise AdapterFailure("parse_error", "metadata must be an object")
    _validate_json_value(metadata, "metadata")
    return CandidateAction(
        action_id=_nonempty_string(data["action_id"], "action_id"),
        actor_id=_nonempty_string(data["actor_id"], "actor_id"),
        action_type=_nonempty_string(data["action_type"], "action_type"),
        preconditions=_string_set(data["preconditions"], "preconditions"),
        effects=_string_set(data["effects"], "effects"),
        required_objects=_string_set(data.get("required_objects", []), "required_objects"),
        used_facts=_string_set(data.get("used_facts", []), "used_facts"),
        disclosed_facts=_string_set(data.get("disclosed_facts", []), "disclosed_facts"),
        required_quest_stage=required_quest_stage,
        quest_stage_effect=quest_stage_effect,
        narrative_text=narrative_text,
        metadata=deepcopy(dict(metadata)),
    )


class RecordedProposalAdapter:
    """Replay frozen proposal records without network access or model drift."""

    def __init__(self, model_id: str, model_revision: str, records: Iterable[Mapping[str, Any]]):
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must be a non-empty string")
        if not isinstance(model_revision, str) or not model_revision.strip():
            raise ValueError("model_revision must be a non-empty string")
        if isinstance(records, (str, bytes, Mapping)):
            raise TypeError("records must be an array of objects")
        self.model_id = model_id
        self.model_revision = model_revision
        self._records: dict[tuple[str, int], Mapping[str, Any]] = {}
        for record in records:
            if not isinstance(record, Mapping):
                raise TypeError("each recorded proposal must be an object")
            frozen_record = deepcopy(dict(record))
            scenario_id = frozen_record.get("scenario_id")
            seed = frozen_record.get("seed")
            if not isinstance(scenario_id, str) or not scenario_id.strip():
                raise ValueError("recorded scenario_id must be a non-empty string")
            if not _is_exact_int(seed) or seed < 0:
                raise ValueError("recorded seed must be a non-negative exact integer")
            key = (scenario_id, seed)
            if key in self._records:
                raise ValueError(f"duplicate recorded proposal: {key}")
            self._records[key] = frozen_record

    @classmethod
    def from_json(cls, path: str | Path) -> RecordedProposalAdapter:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(data, Mapping):
            raise TypeError("recorded proposal fixture must be an object")
        return cls(data["model_id"], data["model_revision"], data["records"])

    def propose(self, state: WorldState, scenario_id: str, seed: int) -> ProposalResponse:
        del state
        record = self._records.get((scenario_id, seed))
        if record is None:
            raise AdapterFailure(
                "missing_record",
                f"no frozen response for scenario={scenario_id!r}, seed={seed}",
            )
        if "failure" in record:
            failure = record["failure"]
            if not isinstance(failure, Mapping):
                raise AdapterFailure("parse_error", "failure must be an object")
            if "candidate" in record:
                raise AdapterFailure("parse_error", "record cannot contain failure and candidate")
            code = failure.get("code")
            message = failure.get("message", "")
            if not isinstance(code, str) or not code.strip():
                raise AdapterFailure("parse_error", "failure code must be a non-empty string")
            if not isinstance(message, str):
                raise AdapterFailure("parse_error", "failure message must be a string")
            raise AdapterFailure(code, message)
        try:
            return ProposalResponse(
                candidate=candidate_from_mapping(record["candidate"]),
                provider_latency_ms=record["provider_latency_ms"],
                input_tokens=record["input_tokens"],
                output_tokens=record["output_tokens"],
            )
        except AdapterFailure:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise AdapterFailure("parse_error", f"recorded response parse failed: {exc}") from exc


@dataclass(frozen=True)
class ExperimentRecord:
    schema_version: str
    run_id: str
    scenario_id: str
    seed: int
    model_id: str
    model_revision: str
    status: str
    failure_type: str | None
    provider_latency_ms: float | None
    runner_latency_ms: float
    input_tokens: int
    output_tokens: int
    repair_attempts: int
    trace_hash: str | None
    prior_state_id: str
    final_state_id: str
    record_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or self.schema_version != "1.0.0":
            raise ValueError("unsupported experiment record schema version")
        for name in (
            "run_id",
            "scenario_id",
            "model_id",
            "model_revision",
            "prior_state_id",
            "final_state_id",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if self.status not in {"commit", "fallback", "adapter_failure"}:
            raise ValueError(f"unsupported experiment status: {self.status}")
        if not _is_finite_number(self.runner_latency_ms) or self.runner_latency_ms < 0:
            raise ValueError("runner latency must be finite and non-negative")
        for name in ("input_tokens", "output_tokens", "repair_attempts", "seed"):
            if not _is_exact_int(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a non-negative exact integer")
        if self.status == "adapter_failure":
            if not isinstance(self.failure_type, str) or not self.failure_type:
                raise ValueError("adapter failures require a non-empty failure_type")
            if self.provider_latency_ms is not None or self.trace_hash is not None:
                raise ValueError(
                    "adapter failures cannot claim provider latency or a proposal trace"
                )
            if self.input_tokens or self.output_tokens or self.repair_attempts:
                raise ValueError("adapter failures must use zero proposal counters")
            if self.prior_state_id != self.final_state_id:
                raise ValueError("adapter failures must leave state unchanged")
        else:
            if not _is_finite_number(self.provider_latency_ms):
                raise ValueError("proposal outcomes require finite provider latency")
            if self.provider_latency_ms < 0:
                raise ValueError("provider latency must be non-negative")
            if (
                self.trace_hash is None
                or len(self.trace_hash) != 64
                or any(character not in "0123456789abcdef" for character in self.trace_hash)
            ):
                raise ValueError("proposal outcomes require a SHA-256 trace hash")
            if self.status == "commit" and self.failure_type is not None:
                raise ValueError("commits cannot have a failure_type")
            if self.status == "fallback" and (
                not isinstance(self.failure_type, str) or not self.failure_type
            ):
                raise ValueError("fallbacks require a non-empty failure_type")
        payload = to_jsonable(self)
        supplied_hash = payload.pop("record_hash")
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        expected_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if supplied_hash != "" and (
            not isinstance(supplied_hash, str) or supplied_hash != expected_hash
        ):
            raise ValueError("experiment record hash does not match its contents")
        object.__setattr__(self, "record_hash", expected_hash)


@dataclass(frozen=True)
class ExperimentCase:
    record: ExperimentRecord
    outcome: CommitOutcome | None
    state: WorldState


def _validate_experiment_case(case: ExperimentCase) -> None:
    record = case.record
    outcome = case.outcome
    if not verify_experiment_record(to_jsonable(record)):
        raise ValueError("experiment record checksum verification failed")
    if outcome is None:
        if record.status != "adapter_failure" or record.trace_hash is not None:
            raise ValueError("only adapter failures may omit a proposal outcome")
        if case.state.state_id != record.final_state_id:
            raise ValueError("adapter-failure case state does not match its record")
        return
    replayed_state = replay_trace_record(to_jsonable(outcome))
    if to_jsonable(replayed_state) != to_jsonable(outcome.state):
        raise ValueError("proposal outcome does not semantically replay to its final state")
    expected = {
        "run_id": record.run_id,
        "scenario_id": record.scenario_id,
        "seed": record.seed,
        "model_id": record.model_id,
        "model_revision": record.model_revision,
        "provider_latency_ms": record.provider_latency_ms,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
    }
    actual_context = to_jsonable(outcome.trace_context)
    if any(actual_context.get(key) != value for key, value in expected.items()):
        raise ValueError("experiment record does not match outcome trace context")
    if record.status != outcome.status:
        raise ValueError("experiment record status does not match outcome")
    if record.trace_hash != outcome.trace_hash:
        raise ValueError("experiment record trace_hash does not match outcome")
    if record.repair_attempts != outcome.attempts:
        raise ValueError("experiment record repair count does not match outcome")
    if record.prior_state_id != outcome.prior_state.state_id:
        raise ValueError("experiment record prior state does not match outcome")
    if record.final_state_id != outcome.state.state_id:
        raise ValueError("experiment record final state does not match outcome")
    if to_jsonable(case.state) != to_jsonable(outcome.state):
        raise ValueError("experiment case state does not match outcome")


def run_experiment_case(
    adapter: ProposalAdapter,
    state: WorldState,
    *,
    run_id: str,
    scenario_id: str,
    seed: int,
    repairer=None,
    repair_budget: int = 0,
    clock: Callable[[], float] = time.perf_counter,
) -> ExperimentCase:
    """Run one assigned case; adapter failures leave canonical state unchanged."""

    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")
    if not isinstance(scenario_id, str) or not scenario_id:
        raise ValueError("scenario_id must be a non-empty string")
    if not _is_exact_int(seed) or seed < 0:
        raise ValueError("seed must be a non-negative exact integer")
    started = clock()
    model_id, model_revision, failure_code = _adapter_identity(adapter)
    if failure_code is None:
        try:
            response = _normalize_proposal_response(adapter.propose(state, scenario_id, seed))
        except AdapterFailure as exc:
            failure_code = exc.code
        except TimeoutError:
            failure_code = "timeout"
        except Exception as exc:  # noqa: BLE001 - classify untrusted adapter failures
            failure_code = f"adapter_exception:{type(exc).__name__}"

    if failure_code is not None:
        elapsed = max(0.0, (clock() - started) * 1000)
        record = ExperimentRecord(
            schema_version="1.0.0",
            run_id=run_id,
            scenario_id=scenario_id,
            seed=seed,
            model_id=model_id,
            model_revision=model_revision,
            status="adapter_failure",
            failure_type=failure_code,
            provider_latency_ms=None,
            runner_latency_ms=elapsed,
            input_tokens=0,
            output_tokens=0,
            repair_attempts=0,
            trace_hash=None,
            prior_state_id=state.state_id,
            final_state_id=state.state_id,
        )
        return ExperimentCase(record, None, state)

    elapsed = max(0.0, (clock() - started) * 1000)
    context = {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "seed": seed,
        "model_id": model_id,
        "model_revision": model_revision,
        "provider_latency_ms": response.provider_latency_ms,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
    }
    outcome = execute_with_repair(
        state,
        response.candidate,
        repairer=repairer,
        repair_budget=repair_budget,
        trace_context=context,
    )
    record = ExperimentRecord(
        schema_version="1.0.0",
        run_id=run_id,
        scenario_id=scenario_id,
        seed=seed,
        model_id=model_id,
        model_revision=model_revision,
        status=outcome.status,
        failure_type=None if outcome.status == "commit" else "hard_validation_failure",
        provider_latency_ms=response.provider_latency_ms,
        runner_latency_ms=elapsed,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        repair_attempts=outcome.attempts,
        trace_hash=outcome.trace_hash,
        prior_state_id=state.state_id,
        final_state_id=outcome.state.state_id,
    )
    return ExperimentCase(record, outcome, outcome.state)


def write_experiment_jsonl(
    result_path: str | Path,
    trace_path: str | Path,
    case: ExperimentCase,
) -> None:
    """Append a linked result/trace pair with best-effort rollback on write failure."""

    destination = Path(result_path)
    trace_destination = Path(trace_path)
    if destination.resolve() == trace_destination.resolve():
        raise ValueError("result and trace destinations must be different files")
    _validate_experiment_case(case)
    for path in (destination, trace_destination):
        if path.exists() and not path.is_file():
            raise ValueError(f"experiment destination is not a regular file: {path}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    trace_destination.parent.mkdir(parents=True, exist_ok=True)
    if case.outcome is not None and trace_destination.is_file():
        preceding_state = replay_trace_jsonl(trace_destination)
        if to_jsonable(preceding_state) != to_jsonable(case.outcome.prior_state):
            raise ValueError("trace path already contains a disconnected episode")
    result_line = (
        json.dumps(to_jsonable(case.record), ensure_ascii=False, sort_keys=True) + "\n"
    ).encode()
    trace_line = (
        None
        if case.outcome is None
        else (
            json.dumps(to_jsonable(case.outcome), ensure_ascii=False, sort_keys=True) + "\n"
        ).encode()
    )
    paths = [destination] if trace_line is None else [destination, trace_destination]
    existed = {path: path.exists() for path in paths}
    sizes = {path: path.stat().st_size if path.exists() else 0 for path in paths}
    try:
        if trace_line is not None:
            with trace_destination.open("ab") as handle:
                handle.write(trace_line)
                handle.flush()
                os.fsync(handle.fileno())
        with destination.open("ab") as handle:
            handle.write(result_line)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception as write_error:
        rollback_errors: list[OSError] = []
        for path in paths:
            try:
                if path.exists():
                    if existed[path]:
                        with path.open("r+b") as handle:
                            handle.truncate(sizes[path])
                    else:
                        path.unlink()
            except OSError as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors:
            raise RuntimeError(
                f"experiment write failed and rollback was incomplete: {rollback_errors}"
            ) from write_error
        raise


def verify_experiment_record(record: Mapping[str, Any]) -> bool:
    """Verify the unkeyed content checksum of a decoded assigned-case record."""

    if not isinstance(record, Mapping):
        return False
    supplied_hash = record.get("record_hash")
    if (
        not isinstance(supplied_hash, str)
        or len(supplied_hash) != 64
        or any(character not in "0123456789abcdef" for character in supplied_hash)
    ):
        return False
    payload = dict(record)
    payload.pop("record_hash")
    try:
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    except (TypeError, ValueError):
        return False
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest() == supplied_hash


def experiment_record_from_mapping(record: Mapping[str, Any]) -> ExperimentRecord:
    """Apply semantic invariants and hash verification to a decoded record."""

    if not isinstance(record, Mapping) or not verify_experiment_record(record):
        raise ValueError("experiment record checksum verification failed")
    try:
        return ExperimentRecord(**dict(record))
    except TypeError as exc:
        raise ValueError(f"invalid experiment record fields: {exc}") from exc


def experiment_assignment_key(record: ExperimentRecord) -> AssignmentKey:
    return (
        record.run_id,
        record.scenario_id,
        record.seed,
        record.model_id,
        record.model_revision,
    )


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def summarize_experiment(
    records: Iterable[ExperimentRecord],
    expected_assignments: Iterable[AssignmentKey],
) -> dict[str, int | float | None]:
    """Treatment-policy summary gated by an exact frozen assignment manifest."""

    rows = list(records)
    if not rows:
        raise ValueError("at least one experiment record is required")
    row_keys = [experiment_assignment_key(row) for row in rows]
    if len(row_keys) != len(set(row_keys)):
        raise ValueError("duplicate assigned-case record")
    expected_keys = list(expected_assignments)
    if len(expected_keys) != len(set(expected_keys)):
        raise ValueError("duplicate assignment in expected manifest")
    missing = set(expected_keys) - set(row_keys)
    unexpected = set(row_keys) - set(expected_keys)
    if missing or unexpected:
        raise ValueError(
            f"assigned-case manifest mismatch: missing={sorted(missing)}, "
            f"unexpected={sorted(unexpected)}"
        )
    latencies = [row.provider_latency_ms for row in rows if row.provider_latency_ms is not None]
    commits = sum(row.status == "commit" for row in rows)
    hard_validation_failures = sum(row.status == "fallback" for row in rows)
    adapter_failures = sum(row.status == "adapter_failure" for row in rows)
    return {
        "assigned_cases": len(rows),
        "commit_rate": commits / len(rows),
        "overall_failure_rate": 1 - commits / len(rows),
        "hard_validation_failure_rate": hard_validation_failures / len(rows),
        "adapter_failure_rate": adapter_failures / len(rows),
        "latency_observed_cases": len(latencies),
        "provider_response_latency_p50_ms": _percentile(latencies, 0.50),
        "provider_response_latency_p95_ms": _percentile(latencies, 0.95),
        "total_input_tokens": sum(row.input_tokens for row in rows),
        "total_output_tokens": sum(row.output_tokens for row in rows),
    }
