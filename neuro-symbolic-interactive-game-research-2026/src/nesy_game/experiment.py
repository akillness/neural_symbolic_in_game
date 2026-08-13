"""Deterministic offline experiment runner and recorded-response adapter."""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import os
import time
from collections.abc import Callable, Iterable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .contracts import (
    CandidateAction,
    CandidateParseError,
    CommitOutcome,
    WorldState,
    parse_candidate_mapping,
)
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


AssignmentKey = tuple[str, str, str, int, str, str, str, str, str]


def _content_hash(value: Any) -> str:
    canonical = json.dumps(
        to_jsonable(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _repairer_provenance(repairer: Any) -> tuple[str, str]:
    if repairer is None:
        return "none", hashlib.sha256(b"none").hexdigest()
    module = getattr(repairer, "__module__", type(repairer).__module__)
    qualname = getattr(repairer, "__qualname__", type(repairer).__qualname__)
    strategy_id = f"{module}.{qualname}"
    code = getattr(repairer, "__code__", None)
    try:
        source = inspect.getsource(repairer)
    except (OSError, TypeError):
        source = None

    def portable_value(value: Any) -> Any:
        try:
            _content_hash(value)
        except (TypeError, ValueError):
            value_type = type(value)
            return {"unsupported_type": f"{value_type.__module__}.{value_type.__qualname__}"}
        return to_jsonable(value)

    closure = getattr(repairer, "__closure__", None) or ()
    function_globals = getattr(repairer, "__globals__", {})
    referenced_globals = {
        name: portable_value(function_globals[name])
        for name in getattr(code, "co_names", ())
        if name in function_globals and name != "__builtins__"
    }
    payload = {
        "strategy_id": strategy_id,
        "source": source,
        "bytecode": getattr(code, "co_code", b"").hex(),
        "constants": portable_value(getattr(code, "co_consts", ())),
        "defaults": portable_value(getattr(repairer, "__defaults__", None)),
        "keyword_defaults": portable_value(getattr(repairer, "__kwdefaults__", None)),
        "closure": [portable_value(cell.cell_contents) for cell in closure],
        "referenced_globals": referenced_globals,
        "callable_state": portable_value(getattr(repairer, "__dict__", {})),
    }
    return strategy_id, _content_hash(payload)


def _merge_provenance(
    supplied: Mapping[str, Any] | None,
    authoritative: Mapping[str, Any],
    *,
    kind: str,
) -> dict[str, Any]:
    if supplied is None:
        return dict(authoritative)
    if not isinstance(supplied, Mapping):
        raise TypeError(f"{kind} provenance must be an object")
    merged = dict(supplied)
    for key, value in authoritative.items():
        if key in merged and merged[key] != value:
            raise ValueError(f"reserved {kind} field {key!r} contradicts execution")
        merged[key] = value
    return merged


class _ControllerExecutionFailure(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _validate_assignment_coordinates(
    run_id: Any,
    arm_id: Any,
    scenario_id: Any,
    seed: Any,
) -> None:
    for name, value in (("run_id", run_id), ("arm_id", arm_id), ("scenario_id", scenario_id)):
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string")
    if not _is_exact_int(seed) or seed < 0:
        raise ValueError("seed must be a non-negative exact integer")


def _resolve_provenance_hashes(
    state: WorldState,
    *,
    scenario_id: str,
    seed: int,
    repairer: Any,
    repair_budget: int,
    controller_config: Mapping[str, Any] | None,
    assignment_input: Mapping[str, Any] | None,
) -> tuple[str, str, str]:
    if not _is_exact_int(repair_budget) or repair_budget < 0:
        raise ValueError("repair_budget must be a non-negative exact integer")
    if repairer is not None and not callable(repairer):
        raise TypeError("repairer must be callable or null")
    repairer_strategy_id, repairer_code_hash = _repairer_provenance(repairer)
    resolved_config = _merge_provenance(
        controller_config,
        {
            "repair_budget": repair_budget,
            "repairer_strategy_id": repairer_strategy_id,
            "repairer_code_hash": repairer_code_hash,
        },
        kind="controller",
    )
    resolved_input = _merge_provenance(
        assignment_input,
        {"scenario_id": scenario_id, "seed": seed},
        kind="assignment",
    )
    try:
        return (
            _content_hash(resolved_config),
            _content_hash(resolved_input),
            _content_hash(state),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"experiment provenance must be strict JSON: {exc}") from exc


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


def planned_experiment_assignment(
    adapter: ProposalAdapter,
    state: WorldState,
    *,
    run_id: str,
    arm_id: str = "default",
    scenario_id: str,
    seed: int,
    repairer=None,
    repair_budget: int = 0,
    controller_config: Mapping[str, Any] | None = None,
    assignment_input: Mapping[str, Any] | None = None,
) -> AssignmentKey:
    """Freeze an assignment key independently before invoking the proposal adapter."""

    _validate_assignment_coordinates(run_id, arm_id, scenario_id, seed)
    model_id, model_revision, _failure_code = _adapter_identity(adapter)
    controller_hash, input_hash, state_hash = _resolve_provenance_hashes(
        state,
        scenario_id=scenario_id,
        seed=seed,
        repairer=repairer,
        repair_budget=repair_budget,
        controller_config=controller_config,
        assignment_input=assignment_input,
    )
    return (
        run_id,
        arm_id,
        scenario_id,
        seed,
        model_id,
        model_revision,
        controller_hash,
        input_hash,
        state_hash,
    )


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


def candidate_from_mapping(data: Mapping[str, Any]) -> CandidateAction:
    """Parse a proposal candidate under the shared candidate contract.

    Delegates to :func:`nesy_game.contracts.parse_candidate_mapping` with
    ``allow_defaults=True``: a generator need not emit every optional field at the
    proposal boundary. The replay-side parser calls the same function with
    ``allow_defaults=False`` because it reads records serialized from a committed
    candidate, so persisted-record strictness is preserved while unknown-key handling,
    required-key handling, and value validation stay identical between the two.

    Contract violations surface as :class:`AdapterFailure` with code ``parse_error`` so
    the offline runner classifies them as adapter failures rather than crashes.
    """

    try:
        return parse_candidate_mapping(data, allow_defaults=True)
    except CandidateParseError as failure:
        raise AdapterFailure("parse_error", str(failure)) from failure


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
    arm_id: str
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
    controller_config_hash: str
    assignment_input_hash: str
    prior_state_hash: str
    final_state_hash: str
    proposal_hash: str | None
    record_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or self.schema_version != "1.2.0":
            raise ValueError("unsupported experiment record schema version")
        for name in (
            "run_id",
            "arm_id",
            "scenario_id",
            "model_id",
            "model_revision",
            "prior_state_id",
            "final_state_id",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        for name in (
            "controller_config_hash",
            "assignment_input_hash",
            "prior_state_hash",
            "final_state_hash",
        ):
            value = getattr(self, name)
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest")
        if self.proposal_hash is not None and (
            not isinstance(self.proposal_hash, str)
            or len(self.proposal_hash) != 64
            or any(character not in "0123456789abcdef" for character in self.proposal_hash)
        ):
            raise ValueError("proposal_hash must be null or a lowercase SHA-256 digest")
        if self.status not in {
            "commit",
            "fallback",
            "adapter_failure",
            "controller_failure",
        }:
            raise ValueError(f"unsupported experiment status: {self.status}")
        if not _is_finite_number(self.runner_latency_ms) or self.runner_latency_ms < 0:
            raise ValueError("runner latency must be finite and non-negative")
        for name in ("input_tokens", "output_tokens", "repair_attempts", "seed"):
            if not _is_exact_int(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a non-negative exact integer")
        if self.status == "adapter_failure":
            if not isinstance(self.failure_type, str) or not self.failure_type:
                raise ValueError("adapter failures require a non-empty failure_type")
            if (
                self.provider_latency_ms is not None
                or self.trace_hash is not None
                or self.proposal_hash is not None
            ):
                raise ValueError(
                    "adapter failures cannot claim provider latency, proposal, or trace"
                )
            if self.input_tokens or self.output_tokens or self.repair_attempts:
                raise ValueError("adapter failures must use zero proposal counters")
            if (
                self.prior_state_id != self.final_state_id
                or self.prior_state_hash != self.final_state_hash
            ):
                raise ValueError("adapter failures must leave state unchanged")
        elif self.status == "controller_failure":
            if not isinstance(self.failure_type, str) or not self.failure_type:
                raise ValueError("controller failures require a non-empty failure_type")
            if not _is_finite_number(self.provider_latency_ms) or self.provider_latency_ms < 0:
                raise ValueError("controller failures require finite provider latency")
            if self.proposal_hash is None or self.trace_hash is not None:
                raise ValueError("controller failures require a proposal but no completed trace")
            if (
                self.prior_state_id != self.final_state_id
                or self.prior_state_hash != self.final_state_hash
            ):
                raise ValueError("controller failures must leave state unchanged")
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
            if self.proposal_hash is None:
                raise ValueError("proposal outcomes require a proposal hash")
            if self.status == "commit" and self.failure_type is not None:
                raise ValueError("commits cannot have a failure_type")
            if self.status == "fallback" and (
                not isinstance(self.failure_type, str) or not self.failure_type
            ):
                raise ValueError("fallbacks require a non-empty failure_type")
            if self.status == "fallback" and (
                self.prior_state_id != self.final_state_id
                or self.prior_state_hash != self.final_state_hash
            ):
                raise ValueError("fallbacks must leave state unchanged")
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
    if _content_hash(case.state) != record.final_state_hash:
        raise ValueError("experiment case final-state hash does not match its state")
    if outcome is None:
        if record.status not in {"adapter_failure", "controller_failure"}:
            raise ValueError("only classified boundary failures may omit a proposal outcome")
        if record.trace_hash is not None:
            raise ValueError("a case without an outcome cannot claim a completed trace")
        if case.state.state_id != record.final_state_id:
            raise ValueError("boundary-failure case state does not match its record")
        return
    replayed_state = replay_trace_record(to_jsonable(outcome))
    if to_jsonable(replayed_state) != to_jsonable(outcome.state):
        raise ValueError("proposal outcome does not semantically replay to its final state")
    expected = {
        "run_id": record.run_id,
        "arm_id": record.arm_id,
        "scenario_id": record.scenario_id,
        "seed": record.seed,
        "model_id": record.model_id,
        "model_revision": record.model_revision,
        "provider_latency_ms": record.provider_latency_ms,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "controller_config_hash": record.controller_config_hash,
        "assignment_input_hash": record.assignment_input_hash,
        "prior_state_hash": record.prior_state_hash,
        "proposal_hash": record.proposal_hash,
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
    if record.prior_state_hash != _content_hash(outcome.prior_state):
        raise ValueError("experiment record prior-state hash does not match outcome")
    if record.proposal_hash != _content_hash(outcome.trace[0].candidate):
        raise ValueError("experiment record proposal hash does not match initial candidate")
    if to_jsonable(case.state) != to_jsonable(outcome.state):
        raise ValueError("experiment case state does not match outcome")


def run_experiment_case(
    adapter: ProposalAdapter,
    state: WorldState,
    *,
    run_id: str,
    arm_id: str = "default",
    scenario_id: str,
    seed: int,
    repairer=None,
    repair_budget: int = 0,
    controller_config: Mapping[str, Any] | None = None,
    assignment_input: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> ExperimentCase:
    """Run one attributed assigned case; failures leave canonical state unchanged."""

    _validate_assignment_coordinates(run_id, arm_id, scenario_id, seed)
    controller_config_hash, assignment_input_hash, prior_state_hash = _resolve_provenance_hashes(
        state,
        scenario_id=scenario_id,
        seed=seed,
        repairer=repairer,
        repair_budget=repair_budget,
        controller_config=controller_config,
        assignment_input=assignment_input,
    )
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
            schema_version="1.2.0",
            run_id=run_id,
            arm_id=arm_id,
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
            controller_config_hash=controller_config_hash,
            assignment_input_hash=assignment_input_hash,
            prior_state_hash=prior_state_hash,
            final_state_hash=prior_state_hash,
            proposal_hash=None,
        )
        return ExperimentCase(record, None, state)

    proposal_hash = _content_hash(response.candidate)
    context = {
        "run_id": run_id,
        "arm_id": arm_id,
        "scenario_id": scenario_id,
        "seed": seed,
        "model_id": model_id,
        "model_revision": model_revision,
        "provider_latency_ms": response.provider_latency_ms,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "controller_config_hash": controller_config_hash,
        "assignment_input_hash": assignment_input_hash,
        "prior_state_hash": prior_state_hash,
        "proposal_hash": proposal_hash,
    }
    repair_calls = 0

    def tracked_repairer(*args):
        nonlocal repair_calls
        repair_calls += 1
        try:
            repaired = repairer(*args)
        except TimeoutError as exc:
            raise _ControllerExecutionFailure("controller_timeout", str(exc)) from exc
        except Exception as exc:
            raise _ControllerExecutionFailure(
                f"controller_exception:{type(exc).__name__}", str(exc)
            ) from exc
        try:
            return candidate_from_mapping(to_jsonable(repaired))
        except (AdapterFailure, TypeError, ValueError) as exc:
            raise _ControllerExecutionFailure(
                "controller_contract:repair_candidate", str(exc)
            ) from exc

    try:
        outcome = execute_with_repair(
            state,
            response.candidate,
            repairer=None if repairer is None else tracked_repairer,
            repair_budget=repair_budget,
            trace_context=context,
        )
    except _ControllerExecutionFailure as exc:
        elapsed = max(0.0, (clock() - started) * 1000)
        record = ExperimentRecord(
            schema_version="1.2.0",
            run_id=run_id,
            arm_id=arm_id,
            scenario_id=scenario_id,
            seed=seed,
            model_id=model_id,
            model_revision=model_revision,
            status="controller_failure",
            failure_type=exc.code,
            provider_latency_ms=response.provider_latency_ms,
            runner_latency_ms=elapsed,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            repair_attempts=repair_calls,
            trace_hash=None,
            prior_state_id=state.state_id,
            final_state_id=state.state_id,
            controller_config_hash=controller_config_hash,
            assignment_input_hash=assignment_input_hash,
            prior_state_hash=prior_state_hash,
            final_state_hash=prior_state_hash,
            proposal_hash=proposal_hash,
        )
        return ExperimentCase(record, None, state)
    elapsed = max(0.0, (clock() - started) * 1000)
    record = ExperimentRecord(
        schema_version="1.2.0",
        run_id=run_id,
        arm_id=arm_id,
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
        controller_config_hash=controller_config_hash,
        assignment_input_hash=assignment_input_hash,
        prior_state_hash=prior_state_hash,
        final_state_hash=_content_hash(outcome.state),
        proposal_hash=proposal_hash,
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
        record.arm_id,
        record.scenario_id,
        record.seed,
        record.model_id,
        record.model_revision,
        record.controller_config_hash,
        record.assignment_input_hash,
        record.prior_state_hash,
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
    controller_failures = sum(row.status == "controller_failure" for row in rows)
    return {
        "assigned_cases": len(rows),
        "commit_rate": commits / len(rows),
        "overall_failure_rate": 1 - commits / len(rows),
        "hard_validation_failure_rate": hard_validation_failures / len(rows),
        "adapter_failure_rate": adapter_failures / len(rows),
        "controller_failure_rate": controller_failures / len(rows),
        "latency_observed_cases": len(latencies),
        "provider_response_latency_p50_ms": _percentile(latencies, 0.50),
        "provider_response_latency_p95_ms": _percentile(latencies, 0.95),
        "total_input_tokens": sum(row.input_tokens for row in rows),
        "total_output_tokens": sum(row.output_tokens for row in rows),
    }
