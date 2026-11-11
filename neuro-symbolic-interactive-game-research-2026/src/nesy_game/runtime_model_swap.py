from __future__ import annotations

import copy
import hashlib
import json
import math
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Protocol

from nesy_game.runtime_model_swap_native import (
    EXTENSION_ACTIVATION_SCHEMA,
    EXTENSION_CODEX_CLI_VERSION,
    EXTENSION_CODEX_IDENTITY_SOURCE,
    NativeActivationTrust,
    PromptTransportError,
)


class EpisodeEngine(Protocol):
    def state(self) -> dict[str, Any]: ...
    def legal_actions(self) -> list[str]: ...
    def preconditions(self) -> dict[str, Any]: ...
    def constraints(self) -> list[str]: ...
    def objective(self) -> str: ...
    def validate(self, proposal: dict[str, Any]) -> dict[str, Any]: ...
    def commit(self, proposal: dict[str, Any]) -> dict[str, Any]: ...
    def objective_reached(self) -> bool: ...


@dataclass(frozen=True)
class EpisodeLimits:
    wall_seconds: float = 180.0
    response_seconds: float = 60.0
    max_host_calls: int = 12
    max_repairs_per_decision: int = 2

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value) and value > 0
            for value in (self.wall_seconds, self.response_seconds)
        ):
            raise ValueError("deadlines must be positive and finite")
        if type(self.max_host_calls) is not int or self.max_host_calls < 1:
            raise ValueError("max_host_calls must be a positive integer")
        if type(self.max_repairs_per_decision) is not int or self.max_repairs_per_decision < 0:
            raise ValueError("max_repairs_per_decision must be a nonnegative integer")


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    representation: str
    provider: str | None = None
    revision: str | None = None
    offline: bool = True

    def __post_init__(self) -> None:
        if self.representation not in {"ontology", "general_rule"}:
            raise ValueError("unsupported representation")


def _json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _json_bytes(value: Any) -> bytes:
    return _json(value).encode("utf-8")


def _safe_text(value: str) -> str:
    return value.encode("utf-8", errors="backslashreplace").decode("utf-8")


def _error_text(exc: Exception) -> str:
    return _safe_text(f"{type(exc).__name__}: {exc}")


def _hash(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _evidence_value(value: Any) -> Any:
    try:
        _json_bytes(value)
    except (TypeError, ValueError, RecursionError) as exc:
        try:
            diagnostic = _safe_text(repr(value))[:512]
        except Exception:  # noqa: BLE001 -- A callback's repr is also untrusted.
            diagnostic = "<unrepresentable>"
        return {
            "serialization_error": _error_text(exc),
            "value_type": _safe_text(type(value).__name__),
            "diagnostic": diagnostic,
        }
    return copy.deepcopy(value)


def _render(semantic: Mapping[str, Any], representation: str) -> str:
    if representation == "ontology":
        return "ontology:" + _json(semantic)
    return "rules:" + ";".join(f"{key}={_json(value)}" for key, value in semantic.items())


class EpisodePersistenceError(OSError):
    """A final write failed after the complete episode record was finalized."""

    def __init__(self, message: str, *, record: dict[str, Any]) -> None:
        super().__init__(message)
        self.record = record


def _ollama_runner_is_bound(engine: EpisodeEngine) -> bool:
    try:
        from nesy_game.runtime_model_swap_ollama import OllamaPromptRunner
    except (ImportError, ModuleNotFoundError):
        return False
    return isinstance(getattr(engine, "prompt_runner", None), OllamaPromptRunner)


def _ollama_transport_accounting(receipt: Mapping[str, Any]) -> dict[str, int] | None:
    events = receipt.get("transport_events")
    if not isinstance(events, list) or not events:
        return None
    counts = {"total": 0, "preflight": 0, "generation": 0, "responses": 0}
    operations = {"version", "tags", "show", "generate"}
    for event in events:
        if not isinstance(event, Mapping):
            return None
        kind = event.get("kind")
        operation = event.get("operation")
        if kind not in {"preflight", "generation"} or operation not in operations:
            return None
        if kind == "generation" and operation != "generate":
            return None
        if kind == "preflight" and operation == "generate":
            return None
        if event.get("attempted") is not True or not isinstance(event.get("succeeded"), bool):
            return None
        if event.get("succeeded") is False and not isinstance(event.get("error"), str):
            return None
        counts["total"] += 1
        counts[kind] += 1
        counts["responses"] += int(event["succeeded"])
    request_count = receipt.get("transport_request_count")
    response_count = receipt.get("transport_response_count")
    if (
        not isinstance(request_count, int)
        or isinstance(request_count, bool)
        or request_count != counts["total"]
        or not isinstance(response_count, int)
        or isinstance(response_count, bool)
        or response_count != counts["responses"]
    ):
        return None
    return counts


def run_episode(
    *,
    engine: EpisodeEngine,
    proposal_source: Callable[[dict[str, Any]], dict[str, Any]],
    model: ModelSpec,
    limits: EpisodeLimits,
    seed: int,
    clock: Callable[[], float],
    config: Mapping[str, Any],
    prompt: str,
    repair_source: Callable[[dict[str, Any], dict[str, Any], str, int], dict[str, Any]]
    | None = None,
    provider_launcher: Callable[..., Any] | None = None,
    output_path: str | Path | None = None,
    native_context: Mapping[str, Any] | None = None,
    ollama_local_admitted: bool = False,
    trusted_activation: Any | None = None,
    exploratory_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if output_path is not None and Path(output_path).exists():
        raise FileExistsError(f"output already exists: {output_path}")
    preparation_started = float(clock())
    started: float | None = None
    evidence: dict[str, Any] = {
        "provenance": {"mode": "offline", "synthetic": True},
        "seed": seed,
        "provider_identity": None,
        "provider_revision": None,
        "cost_usd": None,
        "provider_request_count": None,
        "provider_process_launch_count": 0,
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "config_hash": _hash(dict(config)),
        "request_hash": None,
        "raw_proposals": [],
        "raw_model_outputs": [],
        "validation": [],
        "repair": [],
        "commit": [],
        "calls": [],
        "engine_runs": [],
        "time": {
            "preparation_started": preparation_started,
            "preparation_ended": None,
            "started": None,
            "ended": None,
            "boundary": "first_host_dispatch_to_terminal_observation",
        },
    }
    assigned_id = config.get("assignment_id")
    assigned_ids = [assigned_id] if isinstance(assigned_id, str) and assigned_id else []
    record: dict[str, Any] = {
        "schema_version": "runtime-model-swap/1",
        "assignment_id": assigned_id,
        "assigned_ids": assigned_ids,
        "assigned_rows": [{"assignment_id": value} for value in assigned_ids],
        "scope": "bookkeeping",
        "model": asdict(model),
        "limits": asdict(limits),
        "seed": seed,
        "config": copy.deepcopy(dict(config)),
        "prompt": prompt,
        "initial_state": {},
        "final_state": {},
        "decisions": [],
        "evidence": evidence,
        "accounting": {
            "host_calls": 0,
            "source_attempts": 0,
            "failed_calls": 0,
            "timeout_calls": 0,
            "transport_retries": 0,
            "repair_calls": 0,
            "successful_repairs": 0,
            "initial_proposal_failures": 0,
            "wall_expired": False,
            "denominator_eligible": True,
        },
        "safety": {
            "status": "NO_COMMIT_OBSERVED",
            "committed_transitions": 0,
            "committed_invariant_violations": 0,
            "errors": [],
        },
        "failure_reason": None,
        "last_error": None,
        "status": "failure",
        "success": False,
        "goal_reached": False,
    }
    accounting = record["accounting"]
    native_production_admitted = False
    ollama_production_admitted = False
    exploratory_admitted = False
    exploratory_authorization_row_id: str | None = None
    record["scientific"] = {"assigned": 0, "executed": 0, "eligible": False}

    def checked(name: str, value: Any, expected: type) -> Any:
        try:
            if not isinstance(value, expected):
                raise TypeError(f"{name}_must_return_{expected.__name__}")
            _json_bytes(value)
        except (TypeError, ValueError, RecursionError):
            evidence.setdefault("callback_contract_errors", []).append(
                {"callback": name, "value": _evidence_value(value)}
            )
            raise
        return value

    def expired() -> bool:
        return started is not None and float(clock()) - started >= limits.wall_seconds

    def finish(*, observe: bool = True) -> dict[str, Any]:
        evidence["time"]["ended"] = float(clock())
        if started is None:
            evidence["time"]["preparation_ended"] = evidence["time"]["ended"]
        elif expired():
            accounting["wall_expired"] = True
        if (
            record["failure_reason"]
            in {
                "engine_unavailable",
                "validation_failure",
                "goal_observation_unavailable",
            }
            and record["safety"]["status"] != "FAIL"
        ):
            record["safety"]["status"] = "NOT_PASS"
        if observe:
            try:
                record["final_state"] = copy.deepcopy(checked("final_state", engine.state(), dict))
            except Exception as exc:  # noqa: BLE001 -- Preserve failures from injected state observers.
                record["failure_reason"] = "engine_unavailable"
                record["last_error"] = _error_text(exc)
                if record["safety"]["status"] != "FAIL":
                    record["safety"]["status"] = "NOT_PASS"
        if observe:
            replay = getattr(engine, "reexecute", None)
            if callable(replay):
                try:
                    result = checked("reexecute", replay(), dict)
                    if result.get("valid") is None:
                        if result.get("status") != "not_run" or any(
                            decision["commit"] is not None for decision in record["decisions"]
                        ):
                            raise ValueError("reexecution_verdict_missing")
                    else:
                        checked("reexecute.valid", result["valid"], bool)
                    evidence["engine_reexecution"] = copy.deepcopy(result)
                except Exception as exc:  # noqa: BLE001 -- Replay failure must not erase the assigned row.
                    evidence["engine_reexecution"] = {
                        "valid": False,
                        "status": "failed",
                        "error": _error_text(exc),
                        "model_calls": 0,
                    }
            for key, attribute, expected in (
                ("raw_model_outputs", "raw_model_outputs", list),
                ("prompt_receipts", "prompt_receipts", list),
                ("engine_runs", "engine_evidence", list),
                ("prompt_invocations", "prompt_calls", list),
                ("source_hashes", "source_hashes", dict),
                ("setup_operations", "setup_operations", list),
            ):
                try:
                    value = checked(attribute, getattr(engine, attribute, expected()), expected)
                    if key == "engine_runs":
                        runs = [checked("engine_run", run, dict) for run in value]
                        evidence["preparation"] = copy.deepcopy(
                            [run for run in runs if run.get("mode") == "import"]
                        )
                        value = [run for run in runs if run.get("mode") != "import"]
                    evidence[key] = copy.deepcopy(value)
                except Exception as exc:  # noqa: BLE001 -- Invalid extension evidence cannot drop assignments.
                    evidence.setdefault("metadata_errors", []).append(
                        {"field": key, "error": _error_text(exc)}
                    )
                    if record["safety"]["status"] != "FAIL":
                        record["safety"]["status"] = "NOT_PASS"
        receipts = evidence.get("prompt_receipts")
        extension_identity_required = False
        extension_response_qualified = False
        activation = getattr(trusted_activation, "activation", None)
        if (
            native_production_admitted
            and isinstance(activation, Mapping)
            and activation.get("schema_version") == EXTENSION_ACTIVATION_SCHEMA
        ):
            extension_identity_required = True
        if isinstance(receipts, list):
            actual_launches = 0
            qualified_launches = 0
            authoritative_requests: list[int] = []
            for receipt in receipts:
                if not isinstance(receipt, Mapping):
                    continue
                admitted = native_production_admitted
                if (
                    admitted
                    and receipt.get("mode") == "native"
                    and receipt.get("transport_kind") == "local_process"
                    and receipt.get("local_process_started") is True
                    and receipt.get("dispatch_started") is True
                    and receipt.get("runner_injected") is False
                    and receipt.get("activation_sha256") == trusted_activation.activation_sha256
                    and receipt.get("plan_sha256") == trusted_activation.plan_sha256
                    and receipt.get("row_id") == trusted_activation.row_id
                ):
                    actual_launches += 1
                    if (
                        extension_identity_required
                        and receipt.get("response_qualified") is True
                        and receipt.get("provider_identity_verified") is True
                        and receipt.get("provider_identity") == model.model_id
                        and receipt.get("identity_source")
                        in {EXTENSION_CODEX_IDENTITY_SOURCE, "codex::response_model"}
                        and receipt.get("identity_transport") == "http"
                        and receipt.get("identity_cli_version") == EXTENSION_CODEX_CLI_VERSION
                        and isinstance(receipt.get("outgoing_request_sha256"), str)
                        and bool(receipt.get("outgoing_request_sha256"))
                        and receipt.get("identity_request_hash")
                        == receipt.get("outgoing_request_sha256")
                    ):
                        qualified_launches += 1
                if admitted and receipt.get("provider_request_count_authoritative") is True:
                    count = receipt.get("provider_request_count")
                    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
                        authoritative_requests.append(count)
            evidence["provider_process_launch_count"] = actual_launches
            if extension_identity_required:
                extension_response_qualified = (
                    actual_launches > 0
                    and len(receipts) == actual_launches
                    and qualified_launches == actual_launches
                )
            if authoritative_requests:
                evidence["provider_request_count"] = sum(authoritative_requests)
            else:
                evidence["provider_request_count"] = None
        if native_production_admitted:
            record["scientific"]["executed"] = (
                1 if evidence.get("provider_process_launch_count", 0) > 0 else 0
            )
            if extension_identity_required:
                record["scientific"]["eligible"] = extension_response_qualified
                evidence["response_qualification"] = {
                    "required": True,
                    "qualified": extension_response_qualified,
                    "identity_source": EXTENSION_CODEX_IDENTITY_SOURCE,
                    "identity_transport": "http",
                    "cli_version": EXTENSION_CODEX_CLI_VERSION,
                }
                provenance = evidence.setdefault("provenance", {})
                if isinstance(provenance, dict):
                    provenance["response_qualified"] = extension_response_qualified
                    provenance["scientific_eligible"] = extension_response_qualified
        if exploratory_admitted and isinstance(receipts, list):
            observed = [item for item in receipts if isinstance(item, Mapping)]
            evidence["provider_process_launch_count"] = sum(
                item.get("transport_kind") == "local_process"
                and item.get("local_process_started") is True
                for item in observed
            )
            evidence["provider_request_count"] = sum(
                item.get("dispatch_started") is True for item in observed
            )
            evidence["provider_request_count_authoritative"] = False
        if ollama_production_admitted:
            observed = [
                receipt
                for receipt in evidence.get("prompt_receipts", [])
                if isinstance(receipt, Mapping)
                and _ollama_transport_accounting(receipt) is not None
            ]
            dispatched = [
                receipt for receipt in observed if receipt.get("generation_dispatched") is True
            ]
            event_rows = [(receipt, _ollama_transport_accounting(receipt)) for receipt in observed]
            dispatched_rows = [
                (receipt, _ollama_transport_accounting(receipt)) for receipt in dispatched
            ]
            event_totals = {"preflight": 0, "generation": 0, "total": 0, "responses": 0}
            for _receipt, counts in event_rows:
                if counts is not None:
                    for key in event_totals:
                        event_totals[key] += counts[key]
            authoritative = [
                counts["total"]
                for receipt, counts in event_rows
                if receipt.get("provider_request_count_authoritative") is True
                and counts is not None
            ]
            evidence["provider_request_count"] = (
                sum(authoritative)
                if authoritative and len(authoritative) == len(observed)
                else None
            )
            evidence["provider_request_count_authoritative"] = bool(observed) and len(
                authoritative
            ) == len(observed)
            evidence["provider_transport_events"] = event_totals
            expected_config = record["config"]
            try:
                from nesy_game.runtime_model_swap_ollama import (
                    receipt_digest as _ollama_receipt_digest,
                )
            except ImportError:
                _ollama_receipt_digest = None

            def _bound(receipt: Mapping[str, Any]) -> bool:
                if _ollama_receipt_digest is None:
                    return False
                expected = {
                    "assignment_id": record.get("assignment_id"),
                    "row_id": record.get("assignment_id"),
                    "config_hash": evidence["config_hash"],
                    "manifest_sha256": expected_config.get("manifest_sha256"),
                    "blob_sha256": expected_config.get("blob_sha256"),
                    "model_layer_digest": expected_config.get("model_layer_digest"),
                    "schema_sha256": expected_config.get("canonical_output_schema_sha256"),
                    "canonical_schema_sha256": expected_config.get(
                        "canonical_output_schema_sha256"
                    ),
                }
                if any(not isinstance(value, str) for value in expected.values()):
                    return False
                for key, value in expected.items():
                    if receipt.get(key) != value:
                        return False
                    if receipt.get(f"{key}_pre") != value or receipt.get(f"{key}_post") != value:
                        return False
                if receipt.get("manifest_blob_distinct") is not True:
                    return False
                for key in (
                    "model",
                    "tag_digest",
                    "model_layer_digest",
                    "ollama_version",
                    "manifest_sha256",
                    "blob_sha256",
                    "schema_sha256",
                    "canonical_schema_sha256",
                ):
                    if receipt.get(f"{key}_pre") != receipt.get(f"{key}_post"):
                        return False
                if (
                    receipt.get("preflight_completed") is not True
                    or receipt.get("postflight_completed") is not True
                ):
                    return False
                try:
                    return receipt.get("receipt_sha256") == _ollama_receipt_digest(receipt)
                except (TypeError, ValueError):
                    return False

            qualified = bool(dispatched) and all(
                receipt.get("status") == "verified"
                and receipt.get("response_qualified") is True
                and receipt.get("scientific_eligible") is True
                and receipt.get("transport_kind") == "local_http"
                and receipt.get("provider_request_count_authoritative") is True
                and receipt.get("response_done") is True
                and (counts is not None and counts["preflight"] > 0 and counts["generation"] > 0)
                and _bound(receipt)
                for receipt, counts in dispatched_rows
            )
            record["scientific"]["executed"] = 1 if dispatched else 0
            record["scientific"]["eligible"] = qualified
            provenance = evidence.setdefault("provenance", {})
            if isinstance(provenance, dict):
                provenance["response_qualified"] = qualified
                provenance["scientific_eligible"] = qualified
            evidence["response_qualification"] = {
                "required": True,
                "qualified": qualified,
                "identity_source": "ollama_tags_manifest_binding",
                "identity_transport": "local_http",
            }
        return _finish(record, output_path)

    if exploratory_context is not None:
        gate = exploratory_context
        required = {
            "mode": "configured_selector_exploratory",
            "ready": True,
            "requested_selector": model.model_id,
            "assignment_id": record.get("assignment_id"),
            "exploratory_plan_hash": record.get("config", {}).get("exploratory_plan_hash")
            if isinstance(record.get("config"), Mapping)
            else None,
            "config_hash": evidence["config_hash"],
            "prompt_hash": evidence["prompt_hash"],
            "max_host_dispatches": limits.max_host_calls,
            "response_seconds": limits.response_seconds,
            "provider_retries": 0,
            "raw_credentials_persisted": False,
        }
        if model.provider != "codex" or model.offline is not False:
            record["failure_reason"] = "exploratory_model_admission_mismatch"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        if provider_launcher is not None or not isinstance(gate, Mapping):
            record["failure_reason"] = "exploratory_admission_invalid"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        if any(gate.get(key) != value for key, value in required.items()):
            record["failure_reason"] = "exploratory_admission_gate_failed"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        if (
            not isinstance(trusted_activation, NativeActivationTrust)
            or trusted_activation.purpose != "production_native"
            or trusted_activation.origin != "trusted_bootstrap"
            or trusted_activation.activation.get("schema_version") != EXTENSION_ACTIVATION_SCHEMA
        ):
            record["failure_reason"] = "exploratory_activation_invalid"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        activation = trusted_activation.activation
        if (
            gate.get("activation_sha256") != trusted_activation.activation_sha256
            or gate.get("plan_sha256") != trusted_activation.plan_sha256
            or gate.get("row_sha256") != trusted_activation.row_sha256
            or gate.get("row_id") != trusted_activation.row_id
            or gate.get("assignment_id") != record.get("assignment_id")
            or not isinstance(gate.get("authorization_row_id"), str)
            or gate.get("authorization_row_id") != trusted_activation.row_id
            or gate.get("activation_study_id") != activation.get("study_id")
        ):
            record["failure_reason"] = "exploratory_source_binding_mismatch"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        target = trusted_activation.row.get("target")
        if (
            not isinstance(target, Mapping)
            or set(target) != {"family_label", "host", "selector", "effort"}
            or not isinstance(target.get("family_label"), str)
            or not target.get("family_label")
            or target.get("host") != model.provider
            or target.get("selector") != model.model_id
            or target.get("effort") != "medium"
            or trusted_activation.row.get("representation") != model.representation
        ):
            record["failure_reason"] = "exploratory_activation_target_mismatch"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        exploratory_authorization_row_id = gate["authorization_row_id"]
        bindings = activation.get("artifact_bindings")
        if not isinstance(bindings, Mapping) or not isinstance(
            bindings.get("allowed_requests"), (list, tuple)
        ):
            record["failure_reason"] = "exploratory_request_binding_missing"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        account = gate.get("account_gate")
        if not isinstance(account, Mapping) or any(
            account.get(key) != value
            for key, value in {
                "existing_credit_consumption_authorized": True,
                "automatic_reload_off_verified": True,
                "native_account_match_verified": True,
                "new_credit_purchase_authorized": False,
                "api_key_fallback_authorized": False,
            }.items()
        ):
            record["failure_reason"] = "exploratory_billing_gate_failed"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        for key in ("activation_sha256", "plan_sha256", "row_sha256", "row_id"):
            if not isinstance(gate.get(key), str) or not gate[key]:
                record["failure_reason"] = "exploratory_source_binding_missing"
                accounting["denominator_eligible"] = False
                return finish(observe=False)
        exploratory_admitted = True
        accounting["denominator_eligible"] = False
        evidence["exploratory_admission"] = copy.deepcopy(dict(gate))
        evidence["provenance"] = {
            "mode": "configured_selector_exploratory",
            "synthetic": False,
            "scientific_eligible": False,
        }
        record["scientific"] = {"assigned": 0, "executed": 0, "eligible": False}
        if native_context is not None or ollama_local_admitted:
            record["failure_reason"] = "exploratory_admission_conflicts_with_other_mode"
            return finish(observe=False)

    if native_context is not None:
        from nesy_game.runtime_model_swap_native import validate_native_context

        requested_model = {
            "representation": model.representation,
            "host": model.provider,
            "selector": config.get("model_selector"),
            "effort": config.get("effort"),
            "offline": model.offline,
        }
        admission = validate_native_context(
            native_context,
            model=requested_model,
            config=config,
            prompt=prompt,
            source_root=None,
            trusted_activation=trusted_activation,
        )
        evidence["native_context"] = copy.deepcopy(admission)
        mode = admission.get("mode")
        evidence["provenance"] = {
            "mode": mode if admission.get("ready") is True else "rejected",
            "synthetic": mode in {"engineering_fixture", "test_simulation"}
            and admission.get("ready") is True,
            "scientific_eligible": bool(admission.get("scientific_eligible", False)),
        }
        if admission.get("ready") is not True:
            record["failure_reason"] = "native_context_rejected"
            accounting["denominator_eligible"] = False
            return finish(observe=False)
        native_production_admitted = (
            mode == "native" and admission.get("scientific_eligible") is True
        )
        if native_production_admitted:
            is_ext = (
                isinstance(trusted_activation, NativeActivationTrust)
                and isinstance(trusted_activation.activation, Mapping)
                and trusted_activation.activation.get("schema_version")
                == EXTENSION_ACTIVATION_SCHEMA
            )
            accounting["assigned"] = 1
            record["scientific"] = {"assigned": 1, "executed": 0, "eligible": not is_ext}
        else:
            accounting["denominator_eligible"] = False
        if provider_launcher is not None:
            record["failure_reason"] = "provider_launcher_not_allowed_native"
            accounting["denominator_eligible"] = False
            evidence["provenance"] = {"mode": "rejected", "synthetic": False}
            return finish(observe=False)
    elif ollama_local_admitted:
        if model.provider != "ollama" or model.offline is not False:
            record["failure_reason"] = "ollama_admission_mismatch"
            accounting["denominator_eligible"] = False
            evidence["provenance"] = {"mode": "rejected", "synthetic": False}
            return finish(observe=False)
        if config.get("execution_mode") != "fixed_game_godot_with_local_ollama":
            record["failure_reason"] = "ollama_execution_mode_required"
            accounting["denominator_eligible"] = False
            evidence["provenance"] = {"mode": "rejected", "synthetic": False}
            return finish(observe=False)
        if not _ollama_runner_is_bound(engine):
            record["failure_reason"] = "ollama_runner_binding_required"
            accounting["denominator_eligible"] = False
            evidence["provenance"] = {"mode": "rejected", "synthetic": False}
            return finish(observe=False)
        ollama_production_admitted = True
        accounting["assigned"] = 1
        record["scientific"] = {"assigned": 1, "executed": 0, "eligible": False}
        evidence["provenance"] = {
            "mode": "local_ollama",
            "synthetic": False,
            "scientific_eligible": False,
        }
    elif not exploratory_admitted and (
        not model.offline or model.provider is not None or provider_launcher is not None
    ):
        record["failure_reason"] = "provider_not_allowed_offline"
        evidence["provenance"] = {"mode": "rejected", "synthetic": False}
        return finish(observe=False)
    try:
        engine._episode_assignment_id = record.get("assignment_id")
        engine._episode_row_id = exploratory_authorization_row_id
        engine._episode_config_hash = evidence["config_hash"]
        evidence["admission_setup"] = {
            "assignment_id": record.get("assignment_id"),
            "config_hash": evidence["config_hash"],
            "runner_type": type(getattr(engine, "prompt_runner", None)).__name__,
            "runner_module": type(getattr(engine, "prompt_runner", None)).__module__,
            "execution_mode": config.get("execution_mode"),
        }
        configure = getattr(engine, "configure_runtime", None)
        if callable(configure):
            configure(
                limits=limits, clock=clock, started=started, model_id=model.model_id, prompt=prompt
            )
        record["initial_state"] = copy.deepcopy(checked("initial_state", engine.state(), dict))
        record["final_state"] = copy.deepcopy(record["initial_state"])
        if getattr(engine, "engine_error", None):
            raise RuntimeError(str(engine.engine_error))
        if checked("initial_goal", engine.objective_reached(), bool):
            record["failure_reason"] = "initial_goal_reached"
            return finish()
    except Exception as exc:  # noqa: BLE001 -- Engine initialization is an external callback boundary.
        record["failure_reason"] = "engine_unavailable"
        record["last_error"] = _error_text(exc)
        return finish()

    logical_index = 0
    while True:
        if expired():
            accounting["wall_expired"] = True
            record["failure_reason"] = "wall_budget_exhausted"
            break
        if accounting["host_calls"] >= limits.max_host_calls:
            record["failure_reason"] = "host_call_budget_exhausted"
            break
        try:
            state = copy.deepcopy(checked("state", engine.state(), dict))
            semantic = {
                "state": state,
                "legal_actions": checked("legal_actions", engine.legal_actions(), list),
                "preconditions": checked("preconditions", engine.preconditions(), dict),
                "constraints": checked("constraints", engine.constraints(), list),
                "objective": checked("objective", engine.objective(), str),
            }
        except Exception as exc:  # noqa: BLE001 -- Preserve failed observations in the denominator.
            record["failure_reason"] = "engine_unavailable"
            record["last_error"] = _error_text(exc)
            break
        model_input = {
            **semantic,
            "representation": model.representation,
            "rendering": _render(semantic, model.representation),
        }
        context = {
            "state": state,
            "model_input": model_input,
            "logical_request_id": f"decision-{logical_index}",
            "remaining_wall_seconds": limits.wall_seconds
            if started is None
            else max(0.0, limits.wall_seconds - (float(clock()) - started)),
        }
        request_hash = _hash({"seed": seed, "config": config, "prompt": prompt, "context": context})
        evidence["request_hash"] = request_hash
        decision: dict[str, Any] = {
            "state": state,
            "model_input": copy.deepcopy(model_input),
            "request_hash": request_hash,
            "logical_request_id": context["logical_request_id"],
            "raw_proposals": [],
            "validation": None,
            "repair": None,
            "commit": None,
        }
        evidence["repair"].append({"attempt": 0, "proposal": None})
        accepted = None
        retry_transport = False
        error: dict[str, Any] = {}
        for attempt in range(limits.max_repairs_per_decision + 1):
            if attempt and repair_source is None:
                record["failure_reason"] = "repair_budget_exhausted"
                break
            if expired():
                accounting["wall_expired"] = True
                record["failure_reason"] = "wall_budget_exhausted"
                break
            if accounting["host_calls"] >= limits.max_host_calls:
                record["failure_reason"] = "host_call_budget_exhausted"
                break
            if started is None:
                started = float(clock())
                evidence["time"].update(started=started, preparation_ended=started)
                if callable(configure):
                    configure(
                        limits=limits,
                        clock=clock,
                        started=started,
                        model_id=model.model_id,
                        prompt=prompt,
                    )
            before_count = getattr(engine, "prompt_invocation_count", None)
            row: dict[str, Any] = {
                "kind": "repair" if attempt else "proposal",
                "attempt": attempt,
                "logical_request_id": context["logical_request_id"],
                "started": float(clock()),
                "failed": False,
                "host_invocations": 1,
            }
            evidence["calls"].append(row)
            accounting["source_attempts"] += 1
            accounting["host_calls"] += 1
            if attempt:
                accounting["repair_calls"] += 1
            try:
                if attempt:
                    proposal = repair_source(copy.deepcopy(context), copy.deepcopy(error), attempt)
                else:
                    proposal = proposal_source(copy.deepcopy(context))
                captured = _evidence_value(proposal)
                evidence["raw_proposals"].append(captured)
                decision["raw_proposals"].append(copy.deepcopy(captured))
                if attempt:
                    evidence["repair"][-1] = {
                        "attempt": attempt,
                        "proposal": copy.deepcopy(captured),
                    }
                if (
                    before_count is None
                    and float(clock()) - row["started"] >= limits.response_seconds
                ):
                    raise TimeoutError("response deadline exceeded")
                if not isinstance(proposal, dict):
                    raise TypeError("proposal_must_be_object")
                _json_bytes(proposal)
            except TimeoutError as exc:
                row.update(failed=True, error=_error_text(exc))
                accounting["failed_calls"] += 1
                accounting["timeout_calls"] += 1
                record["last_error"] = "response_timeout"
                record["failure_reason"] = "response_timeout"
                break
            except Exception as exc:  # noqa: BLE001 -- Untrusted adapter failures consume recorded calls.
                row.update(failed=True, error=_error_text(exc))
                accounting["failed_calls"] += 1
                record["last_error"] = row["error"]
                record["failure_reason"] = (
                    "repair_source_error" if attempt else "proposal_source_error"
                )
                prompt_calls = getattr(engine, "prompt_calls", None)
                if (
                    before_count is not None
                    and isinstance(prompt_calls, list)
                    and any(
                        isinstance(call, dict) and call.get("timed_out") is True
                        for call in prompt_calls[before_count:]
                    )
                ):
                    accounting["timeout_calls"] += 1
                    record["failure_reason"] = "response_timeout"
                    break
                if getattr(engine, "engine_error", None):
                    record["failure_reason"] = "engine_unavailable"
                elif isinstance(exc, PromptTransportError) and not attempt:
                    retry_transport = not exploratory_admitted
                elif repair_source is not None and attempt < limits.max_repairs_per_decision:
                    error = {"code": "PROPOSAL_FORMAT_ERROR", "message": row["error"]}
                    decision["validation"] = error | {"valid": False}
                    evidence["validation"].append(copy.deepcopy(decision["validation"]))
                    if attempt == 0:
                        accounting["initial_proposal_failures"] += 1
                    continue
                break
            finally:
                row["ended"] = float(clock())
                row["duration_seconds"] = row["ended"] - row["started"]
                if before_count is not None:
                    observed = engine.prompt_invocation_count - before_count
                    row["host_invocations"] = observed
                    accounting["host_calls"] += observed - 1
            if accounting["host_calls"] > limits.max_host_calls:
                row["discarded"] = "host_call_budget_exhausted"
                record["failure_reason"] = "host_call_budget_exhausted"
                break
            try:
                validation = checked("validate", engine.validate(copy.deepcopy(proposal)), dict)
                checked("validate.valid", validation.get("valid"), bool)
                if checked("validation_state", engine.state(), dict) != state:
                    record["safety"]["status"] = "FIX_VALIDATION_MUTATED_STATE"
                    raise RuntimeError("validation_changed_canonical_state")
            except Exception as exc:  # noqa: BLE001 -- Validator callbacks cannot discard assignments.
                record["failure_reason"] = "validation_failure"
                record["last_error"] = _error_text(exc)
                break
            decision["validation"] = copy.deepcopy(validation)
            evidence["validation"].append(copy.deepcopy(validation))
            if validation.get("valid") is True:
                accepted = proposal
                if attempt:
                    accounting["successful_repairs"] += 1
                    decision["repair"] = {"accepted": True, "attempt": attempt}
                break
            if attempt == 0:
                accounting["initial_proposal_failures"] += 1
            error = validation
            record["failure_reason"] = "repair_budget_exhausted"
        record["decisions"].append(decision)
        if accepted is None:
            if accounting["host_calls"] >= limits.max_host_calls:
                record["failure_reason"] = "host_call_budget_exhausted"
            elif retry_transport and not getattr(engine, "engine_error", None):
                accounting["transport_retries"] += 1
                record["failure_reason"] = None
                continue
            break
        if expired():
            accounting["wall_expired"] = True
            record["failure_reason"] = "wall_budget_exhausted"
            break
        try:
            committed = checked("commit", engine.commit(copy.deepcopy(accepted)), dict)
            decision["commit"] = {
                "proposal": copy.deepcopy(accepted),
                "state": copy.deepcopy(committed),
            }
            evidence["commit"].append(copy.deepcopy(decision["commit"]))
            if checked("committed_state", engine.state(), dict) != committed:
                record["safety"]["committed_invariant_violations"] += 1
                record["safety"]["status"] = "FAIL"
                raise RuntimeError("commit_state_witness_mismatch")
            safety = getattr(engine, "safety_report", None)
            if safety is not None:
                checked("safety_report", safety, dict)
                checked("safety_report.status", safety.get("status"), str)
                record["safety"] = copy.deepcopy(safety)
            else:
                record["safety"]["committed_transitions"] += int(committed != state)
                record["safety"]["status"] = (
                    "PASS" if record["safety"]["committed_transitions"] else "NO_COMMIT_OBSERVED"
                )
        except Exception as exc:  # noqa: BLE001 -- Retain external commit failures and their evidence.
            record["failure_reason"] = "commit_failure"
            record["last_error"] = _error_text(exc)
            if record["safety"]["status"] != "FAIL":
                record["safety"]["status"] = "NOT_PASS"
            break
        if expired():
            accounting["wall_expired"] = True
            record["failure_reason"] = "wall_budget_exhausted"
            break
        try:
            reached = checked("goal_observation", engine.objective_reached(), bool)
            record["goal_observation"] = {"reached": reached, "observed_at": float(clock())}
        except Exception as exc:  # noqa: BLE001 -- Missing independent verification is an assigned failure.
            record["failure_reason"] = "goal_observation_unavailable"
            record["last_error"] = _error_text(exc)
            break
        if expired():
            accounting["wall_expired"] = True
            record["failure_reason"] = "wall_budget_exhausted"
            break
        if reached:
            record.update(success=True, goal_reached=True, status="success", failure_reason=None)
            break
        if record["safety"]["status"] in {"FAIL", "NOT_PASS"}:
            record["failure_reason"] = "commit_safety_failure"
            break
        logical_index += 1
        try:
            if not checked("legal_actions", engine.legal_actions(), list):
                record["failure_reason"] = "episode_incomplete"
                break
        except Exception as exc:  # noqa: BLE001 -- Terminal observations still retain the assigned row.
            record["failure_reason"] = "engine_unavailable"
            record["last_error"] = _error_text(exc)
            break
    return finish()


def _finish(record: dict[str, Any], output_path: str | Path | None) -> dict[str, Any]:
    checks = []
    previous = record["initial_state"]
    for decision in record["decisions"]:
        if decision.get("commit") is not None:
            checks.append(decision["state"] == previous)
            previous = decision["commit"]["state"]
    checks.append(previous == record["final_state"])
    replay = record["evidence"].get("engine_reexecution")
    replay_ok = replay is None or replay.get("valid") is not False
    record["semantic_replay"] = {
        "valid": all(checks) and replay_ok,
        "checks": checks,
        "scope": "record_links_and_engine_reexecution"
        if replay and replay.get("valid") is not None
        else "record_transition_links_only",
    }
    record["primary_success"] = record["success"]
    safety = record["safety"]["status"]
    record["engineering_status"] = (
        "FIX"
        if not record["semantic_replay"]["valid"] or safety == "FAIL"
        else "PASS"
        if safety == "PASS"
        else "NOT_PASS"
    )
    record["accepted_for_engineering_verification"] = record["engineering_status"] == "PASS"
    record["record_hash"] = _hash(
        {key: value for key, value in record.items() if key != "record_hash"}
    )
    if output_path is not None:
        path = Path(output_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8") as handle:
                handle.write(_json(record) + "\n")
        except OSError as exc:
            raise EpisodePersistenceError(_error_text(exc), record=record) from exc
    return record


def verify_episode_record(record: dict[str, Any]) -> bool:
    if record.get("record_hash") != _hash(
        {key: value for key, value in record.items() if key != "record_hash"}
    ):
        return False
    previous = record.get("initial_state")
    for decision in record.get("decisions", []):
        commit = decision.get("commit")
        if commit is None:
            continue
        if (
            decision.get("state") != previous
            or decision.get("validation", {}).get("valid") is not True
        ):
            return False
        previous = commit.get("state")
    return (
        previous == record.get("final_state")
        and record.get("semantic_replay", {}).get("valid") is True
        and record.get("accepted_for_engineering_verification") is True
        and record.get("engineering_status") == "PASS"
        and record.get("safety", {}).get("status") == "PASS"
    )


def aggregate_episode_records(
    records: list[dict[str, Any]], *, assigned_ids: list[str] | None = None
) -> dict[str, Any]:
    by_id = {}
    for record in records:
        identifier = record.get("assignment_id")
        if identifier is None:
            if assigned_ids is not None:
                raise ValueError("manifest records require assignment_id")
            continue
        identifier = str(identifier)
        if identifier in by_id:
            raise ValueError("duplicate assignment record:" + identifier)
        by_id[identifier] = record
    assigned = list(assigned_ids) if assigned_ids is not None else list(by_id)
    if len(set(assigned)) != len(assigned):
        raise ValueError("duplicate assigned id")
    if assigned_ids is not None and set(by_id) - set(assigned):
        raise ValueError("record was not in the assignment manifest")
    selected = (
        [by_id[key] for key in assigned if key in by_id] if assigned_ids is not None else records
    )
    denominator = len(assigned) if assigned_ids is not None else len(records)
    successes = sum(
        record.get("success") is True and record.get("status") == "success" for record in selected
    )
    failures = denominator - successes
    safety_coverage = {key: 0 for key in ("PASS", "FAIL", "NOT_PASS", "NO_COMMIT_OBSERVED")}
    for record in selected:
        status = record.get("safety", {}).get("status", "NOT_PASS")
        safety_coverage[status if status in safety_coverage else "NOT_PASS"] += 1
    safety_coverage["NOT_PASS"] += denominator - len(selected)
    return {
        "denominator": denominator,
        "successes": successes,
        "primary_successes": successes,
        "verified_primary_successes": sum(
            record.get("primary_success") is True
            and record.get("accepted_for_engineering_verification") is True
            and record.get("engineering_status") == "PASS"
            and record.get("safety", {}).get("status") == "PASS"
            for record in selected
        ),
        "safety_coverage": safety_coverage,
        "scope": "bookkeeping",
        "failures": failures,
        "missing_assignments": [key for key in assigned if key not in by_id],
        "unknown_identity_failures": sum(
            record.get("failure_reason") == "unknown_identity" for record in selected
        ),
        "failure_rate": failures / denominator if denominator else None,
    }


class GodotEpisodeEngine:
    """A typed P-arm controller plus disposable, independently gated Godot processes."""

    def __init__(
        self,
        *,
        project: str | Path,
        output_root: str | Path,
        prompt_runner: Callable[..., Any],
        engine_runner: Callable[..., Any],
        godot_binary: str,
        fixture_ref: str,
        seed: int = 20261024,
        assignment_id: str = "runtime-model-swap",
    ) -> None:
        self.project = Path(project).resolve()
        self.output_root = Path(output_root).resolve()
        self.prompt_runner = prompt_runner
        self.engine_runner = engine_runner
        self.godot_binary = godot_binary
        self.fixture_ref = fixture_ref
        self.seed = seed
        self.assignment_id = assignment_id
        self.setup_operations: list[dict[str, Any]] = []
        self.engine_evidence: list[dict[str, Any]] = []
        self.raw_model_outputs: list[dict[str, Any]] = []
        self.prompt_calls: list[dict[str, Any]] = []
        self.prompt_receipts: list[dict[str, Any]] = []
        self._snapshot: dict[str, Any] = {}
        self._error: str | None = None
        self._policy_hash: str | None = None
        self._controller: Any = None
        self._last_request: dict[str, Any] | None = None
        self._last_decision: dict[str, Any] | None = None
        self._context: dict[str, Any] = {}
        self._experiments: list[tuple[dict[str, Any], dict[str, Any]]] = []
        self._cycle = self._request_index = 0
        self._prepared = False
        self._limits = EpisodeLimits()
        self._clock = time.monotonic
        self._started: float | None = None
        self._model_id = "offline-scripted"
        self._prompt = "Restore the lighthouse signal and reveal the authorized tide lead."
        self._legacy_module: Any = None
        self._episode_assignment_id: str | None = None
        self._episode_row_id: str | None = None
        self._episode_config_hash: str | None = None
        self.source_hashes: dict[str, str] = {}
        self.safety_report: dict[str, Any] = {
            "status": "NO_COMMIT_OBSERVED",
            "committed_transitions": 0,
            "committed_invariant_violations": 0,
            "errors": [],
        }

    @property
    def engine_error(self) -> str | None:
        return self._error

    @property
    def prompt_invocation_count(self) -> int:
        return len(self.prompt_calls)

    def configure_runtime(
        self,
        *,
        limits: EpisodeLimits,
        clock: Callable[[], float],
        started: float | None,
        model_id: str,
        prompt: str,
    ) -> None:
        self._limits, self._clock, self._started = limits, clock, started
        self._model_id, self._prompt = model_id, prompt

    def _remaining(self) -> float:
        return (
            self._limits.wall_seconds
            if self._started is None
            else max(0.0, self._limits.wall_seconds - (self._clock() - self._started))
        )

    def _budget(self) -> dict[str, Any]:
        from nesy_game.npc_goal import DEFAULT_BUDGET

        return {
            **DEFAULT_BUDGET,
            "intent_deadline_ms": max(1, int(self._limits.response_seconds * 1000)),
            "episode_deadline_ms": int(self._limits.wall_seconds * 1000),
            "max_intent_calls": self._limits.max_host_calls,
        }

    def _legacy(self) -> Any:
        if self._legacy_module is None:
            scripts = Path(__file__).resolve().parents[2] / "scripts"
            if str(scripts) not in sys.path:
                sys.path.insert(0, str(scripts))
            spec = spec_from_file_location(
                "runtime_swap_legacy", scripts / "run_npc_goal_experiment.py"
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("legacy_runner_unavailable")
            self._legacy_module = module_from_spec(spec)
            spec.loader.exec_module(self._legacy_module)
        return self._legacy_module

    def _prepare(self) -> None:
        if self._prepared:
            return
        self._prepared = True
        source = Path(__file__).resolve().parents[2] / "game-track" / "godot"
        if self.project == source.resolve():
            raise ValueError("Godot execution requires a disposable staged project")
        if not (self.project / "project.godot").is_file():
            return  # An injected transport can use a path without a real Godot project.
        helper = self._legacy()
        playable = sys.modules[helper.stage_project.__module__]
        log = self.output_root / "logs" / "import.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        command = [
            self.godot_binary,
            "--headless",
            "--editor",
            "--path",
            str(self.project),
            "--import",
            "--quit-after",
            "120",
            "--log-file",
            str(log),
        ]
        before = {
            path.relative_to(self.project).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in self.project.rglob("*.gd")
        }
        started = time.perf_counter()
        receipt: dict[str, Any] = {
            "mode": "import",
            "command": command,
            "log_path": str(log),
            "source_hashes": before,
            "status": "completed",
            "accounting_boundary": "fixed_project_preparation_before_episode",
        }
        try:
            playable._run_godot(
                command,
                label="fresh Godot project import",
                timeout=120,
                allowed_errors=playable.SANDBOXED_MACOS_HOST_ERROR,
            )
            if any(
                hashlib.sha256((self.project / name).read_bytes()).hexdigest() != value
                for name, value in before.items()
            ):
                raise RuntimeError("staged_source_changed_during_import")
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            self._error = "godot_import_failed:" + _error_text(exc)
            receipt.update(status="failed", error=self._error)
        receipt["latency_ms"] = (time.perf_counter() - started) * 1000
        self.engine_evidence.append(receipt)

    def _run(
        self, mode: str, payload: dict[str, Any], stem: str, *, replay: bool = False
    ) -> dict[str, Any]:
        input_root, logs = self.output_root / "godot-input", self.output_root / "logs"
        input_root.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        path = input_root / f"{stem}.{mode}.json"
        with path.open("x", encoding="utf-8") as handle:
            handle.write(_json(payload))
        timeout = self._limits.wall_seconds if replay else self._remaining()
        if timeout <= 0:
            raise TimeoutError("episode wall exhausted before engine invocation")
        try:
            result = self.engine_runner(
                binary=self.godot_binary,
                project=self.project,
                mode=mode,
                input_path=path,
                log_dir=logs,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 -- Injected process transports report arbitrary failures.
            result = {"mode": mode, "status": "unavailable", "error": _error_text(exc)}
        self.engine_evidence.append(
            {"mode": mode, **result, "purpose": "reexecution" if replay else "episode"}
        )
        return result

    def _base_input(self) -> dict[str, Any]:
        if not self.source_hashes:
            from nesy_game.npc_goal import CONFIG_PATH, SCHEMA_PATH

            root = Path(__file__).resolve().parents[2]
            sources = {
                "source_schema_sha256": SCHEMA_PATH,
                "npc_protocol_config_sha256": CONFIG_PATH,
                "source_controller_sha256": root / "src/nesy_game/npc_goal.py",
                "runtime_harness_sha256": Path(__file__),
                "runtime_cli_sha256": root / "scripts/run_runtime_model_swap.py",
                "source_project_config_sha256": self.project / "project.godot",
            }
            self.source_hashes = {
                key: hashlib.sha256(path.read_bytes()).hexdigest()
                for key, path in sources.items()
                if path.is_file()
            }
        return {
            "schema_version": "npc-engineering/input-1",
            "assignment_id": self.assignment_id,
            "fixture_ref": self.fixture_ref,
            "source_hashes": dict(self.source_hashes),
            "setup_operations": copy.deepcopy(self.setup_operations),
            "seed_world_events": [],
            "in_dialogue": any(
                row["operation"] == "open_dialogue" for row in self.setup_operations
            ),
            "request_context": {
                "session_id": "runtime-swap-session",
                "episode_id": "episode-1",
                "session_epoch": 0,
                "request_id": f"runtime-{self._request_index}-request",
                "goal_id": "harbor-signal-restored-authorized-tide-lead-v1",
                "goal_version": "1",
            },
        }

    def _bootstrap(self) -> None:
        if self._snapshot or self._error:
            return
        self._prepare()
        if self._error:
            return
        result = self._run("bootstrap", self._base_input(), "bootstrap")
        trace = result.get("trace", {})
        if result.get("status") != "completed" or trace.get("passed") is not True:
            self._error = str(result.get("error") or trace.get("errors") or "bootstrap_failed")
            return
        legacy = self._legacy()
        snapshot, policy = legacy.extract_snapshot(trace), legacy.extract_policy_hash(trace)
        if snapshot is None or policy is None:
            self._error = "bootstrap_snapshot_or_policy_missing"
            return
        self._snapshot, self._policy_hash = snapshot, policy
        from nesy_game.npc_goal import GoalController, IntentInterpreter

        self._controller = GoalController(
            interpreter=IntentInterpreter(
                arm="P", model=self._model_id, prompt_runner=self._observed_prompt
            ),
            budget=self._budget(),
            session_ttl_seconds=self._limits.wall_seconds,
        )

    def _observed_prompt(self, **kwargs: Any) -> Any:
        kwargs["assignment_id"] = getattr(self, "_episode_assignment_id", self.assignment_id)
        row_id = getattr(self, "_episode_row_id", None)
        kwargs["row_id"] = row_id if row_id is not None else kwargs["assignment_id"]
        kwargs["config_hash"] = getattr(self, "_episode_config_hash", None)
        kwargs["instruction"] += "\nPUBLIC_CONTEXT=" + self._context["model_input"]["rendering"]
        kwargs["timeout"] = min(kwargs["timeout"], self._limits.response_seconds, self._remaining())
        if kwargs["timeout"] <= 0:
            raise TimeoutError("episode deadline reached before host dispatch")
        effective = {
            key: kwargs[key]
            for key in (
                "request_id",
                "user_prompt",
                "model",
                "instruction",
                "assignment_id",
                "row_id",
                "config_hash",
            )
        }
        row: dict[str, Any] = {
            "request": effective,
            "prompt_sha256": _hash(effective),
            "schema_sha256": hashlib.sha256(Path(kwargs["output_schema"]).read_bytes()).hexdigest(),
            "started": self._clock(),
            "failed": False,
            "timeout_seconds": kwargs["timeout"],
        }
        try:
            result = self.prompt_runner(**kwargs)
            if (
                hasattr(result, "returncode")
                and hasattr(result, "payload")
                and hasattr(result, "receipt")
            ):
                receipt = _evidence_value(result.receipt)
                if isinstance(receipt, dict):
                    receipt.setdefault("runner_injected", self.prompt_runner is not None)
                    self.prompt_receipts.append(receipt)
                    nested_receipt = (
                        receipt.get("receipt")
                        if isinstance(receipt.get("receipt"), Mapping)
                        else None
                    )
                    if receipt.get("timed_out") is True or (
                        isinstance(nested_receipt, Mapping)
                        and nested_receipt.get("timed_out") is True
                    ):
                        row["timed_out"] = True
                    row["receipt"] = copy.deepcopy(receipt)
                row["returncode"] = _evidence_value(result.returncode)
                payload = _evidence_value(result.payload)
                self.raw_model_outputs.append(payload)
                if result.returncode != 0:
                    failure_kind = (
                        receipt.get("failure_kind") if isinstance(receipt, dict) else None
                    )
                    if failure_kind == "transport":
                        from nesy_game.runtime_model_swap_native import PromptTransportError

                        raise PromptTransportError(
                            "native_prompt_transport_failed:" + str(receipt.get("error", "unknown"))
                        )
                    raise ValueError(
                        "native_prompt_failed:" + str(receipt.get("error", "unknown"))
                        if isinstance(receipt, dict)
                        else "native_prompt_failed"
                    )
                result = (result.returncode, payload)
            elif isinstance(result, tuple) and len(result) == 2:
                row["returncode"] = _evidence_value(result[0])
                tuple_payload = _evidence_value(result[1])
                if isinstance(tuple_payload, Mapping) and isinstance(
                    tuple_payload.get("receipt"), Mapping
                ):
                    receipt = dict(tuple_payload["receipt"])
                    receipt.setdefault("runner_injected", True)
                    self.prompt_receipts.append(receipt)
                    row["receipt"] = copy.deepcopy(receipt)
                    if receipt.get("timed_out") is True:
                        row["timed_out"] = True
                self.raw_model_outputs.append(tuple_payload)
            if self._clock() - row["started"] >= kwargs["timeout"]:
                raise TimeoutError("response deadline exceeded; late output discarded")
            _json_bytes(result)
            return result
        except Exception as exc:
            row.update(
                failed=True,
                timed_out=bool(row.get("timed_out") or isinstance(exc, TimeoutError)),
                error=_error_text(exc),
            )
            raise
        finally:
            row["ended"] = self._clock()
            row["duration_seconds"] = row["ended"] - row["started"]
            self.prompt_calls.append(copy.deepcopy(row))

    def state(self) -> dict[str, Any]:
        self._bootstrap()
        return copy.deepcopy(self._snapshot)

    def legal_actions(self) -> list[str]:
        observation = self._snapshot.get("observation", {})
        if observation.get("goal_reached"):
            return []
        if observation.get("lens_reachable") and not observation.get("lens_carried"):
            return ["acquire_object"]
        if observation.get("lens_carried") and not observation.get("signal_restored"):
            return ["install_lens"]
        if observation.get("signal_restored"):
            return ["reveal_hint"] if observation.get("in_dialogue") else ["negotiate"]
        return []

    def preconditions(self) -> dict[str, list[str]]:
        return {
            "acquire_object": ["lens_reachable"],
            "install_lens": ["lens_carried"],
            "negotiate": ["signal_restored"],
            "reveal_hint": ["signal_restored", "in_dialogue"],
        }

    def constraints(self) -> list[str]:
        return ["godot_canonical_state", "controller_derived_steps_only", "goal_observed_by_engine"]

    def objective(self) -> str:
        return "harbor-signal-restored-authorized-tide-lead-v1"

    def propose(self, context: dict[str, Any]) -> dict[str, Any]:
        self._bootstrap()
        if self._error:
            raise RuntimeError("engine_unavailable:" + self._error)
        from nesy_game.npc_goal import content_hash, default_envelope

        self._context = context
        request_id = f"runtime-{self._request_index}-request"
        self._request_index += 1
        request = default_envelope(
            message_type="request",
            body={
                "event_kind": "utterance",
                "utterance": self._prompt,
                "observation": self._snapshot["observation"],
            },
            session_id="runtime-swap-session",
            request_id=request_id,
            state_ref=self._snapshot["state_ref"],
            policy_hash=self._policy_hash,
            arm="P",
            backend="codex",
            model=self._model_id,
        )
        request["budget"] = self._budget()
        request["content_sha256"] = content_hash(request)
        self._last_request = request
        self._last_decision = self._controller.handle_request(request)
        steps = self._last_decision["body"]["steps"]
        if len(steps) != 1:
            raise ValueError(
                "controller_returned_no_step:" + _json(self._last_decision["body"].get("error"))
            )
        return {"action": steps[0]["operation"]}

    def repair(
        self, context: dict[str, Any], error: dict[str, Any], attempt: int
    ) -> dict[str, Any]:
        context = copy.deepcopy(context)
        context["model_input"]["rendering"] += "\nVALIDATOR_ERROR=" + _json(
            {"attempt": attempt, "error": error}
        )
        return self.propose(context)

    def validate(self, proposal: dict[str, Any]) -> dict[str, Any]:
        from nesy_game.npc_goal import ProtocolError, validate_envelope

        try:
            if (
                set(proposal) != {"action"}
                or self._last_decision is None
                or self._last_request is None
            ):
                raise ProtocolError("controller_decision_required")
            response = validate_envelope(self._last_decision, expected_message_type="decision")
            steps = response["body"]["steps"]
            if len(steps) != 1 or proposal["action"] != steps[0]["operation"]:
                raise ProtocolError("proposal_controller_step_mismatch")
            if self._last_request["state_ref"] != self._snapshot["state_ref"]:
                raise ProtocolError("stale_controller_decision")
        except (ProtocolError, KeyError, TypeError) as exc:
            return {"valid": False, "code": "CONTROLLER_DECISION_INVALID", "message": str(exc)}
        return {"valid": True, "code": None, "message": None}

    def commit(self, proposal: dict[str, Any]) -> dict[str, Any]:
        validation = self.validate(proposal)
        if not validation["valid"]:
            raise ValueError(validation["message"])
        payload = self._base_input()
        payload.update(
            initial_public_snapshot=copy.deepcopy(self._snapshot),
            decision=copy.deepcopy(self._last_decision),
            request=copy.deepcopy(self._last_request),
            source_hashes={**payload["source_hashes"], "policy_hash": self._policy_hash},
        )
        payload["request_context"] = {
            key: self._last_request[key]
            for key in (
                "session_id",
                "episode_id",
                "session_epoch",
                "request_id",
                "goal_id",
                "goal_version",
            )
        }
        operation = proposal["action"]
        payload["mutations"] = (
            [{"code": "fixture-playeraction", "operation": operation}]
            if operation in {"acquire_object", "install_lens"}
            else []
        )
        result = self._run("experiment", payload, f"decision-{self._cycle}")
        self._cycle += 1
        trace = result.get("trace", {})
        if result.get("status") not in {"completed", "failed"}:
            self.safety_report["status"] = "NOT_PASS"
            raise RuntimeError("godot_transport_failed:" + _json(result.get("error")))
        legacy = self._legacy()
        snapshot = legacy.extract_final_snapshot(trace)
        if snapshot is None:
            raise RuntimeError("engine_final_snapshot_missing")
        self._experiments.append((copy.deepcopy(payload), copy.deepcopy(trace)))
        self._snapshot = snapshot
        transitions = sum(
            action.get("status") == "APPLIED"
            and action.get("state_ref_before") != action.get("state_ref_after")
            for action in trace.get("actions", [])
        )
        self.safety_report["committed_transitions"] += transitions
        if trace.get("passed") is not True:
            errors = trace.get("errors") or ["engine_gate_failed"]
            self.safety_report["errors"].extend(errors if isinstance(errors, list) else [errors])
            self.safety_report["committed_invariant_violations"] += transitions
            self.safety_report["status"] = "FAIL" if transitions else "NOT_PASS"
            return self.state()
        self.safety_report["status"] = (
            "PASS" if self.safety_report["committed_transitions"] else "NO_COMMIT_OBSERVED"
        )
        for action in trace.get("actions", []):
            acknowledged = legacy.envelope_result_from_engine(
                self._last_decision, self._last_request, action, self._budget()
            )
            self._controller.handle_result(acknowledged)
            if action.get("status") == "APPLIED" and action.get("operation") in {
                "acquire_object",
                "install_lens",
                "reveal_hint",
            }:
                self.setup_operations.append(
                    {"operation": action["operation"], "arguments": action.get("arguments", {})}
                )
        if operation == "negotiate":
            self.setup_operations.append({"operation": "open_dialogue", "arguments": {}})
            opened = self._run("bootstrap", self._base_input(), f"dialogue-{self._cycle}")
            observed = legacy.extract_snapshot(opened.get("trace"))
            if (
                opened.get("status") != "completed"
                or opened.get("trace", {}).get("passed") is not True
                or observed is None
                or observed["observation"]["in_dialogue"] is not True
                or observed["state_ref"] != self._snapshot["state_ref"]
            ):
                raise RuntimeError("fixed_player_dialogue_not_verified")
            self._snapshot = observed
            self.engine_evidence[-1]["fixed_player_intervention"] = {
                "operation": "open_dialogue",
                "model_authored": False,
                "trigger": "accepted_controller_negotiate",
                "same_for_both_representations": True,
            }
        return self.state()

    def objective_reached(self) -> bool:
        self._bootstrap()
        return self._snapshot.get("observation", {}).get("goal_reached") is True

    @staticmethod
    def _goal_witness(trace: Mapping[str, Any]) -> bool | None:
        observations = trace.get("observations", [])
        actions = trace.get("actions", [])
        final = (
            observations[-1]
            if isinstance(observations, list) and observations
            else (
                actions[-1].get("observation_after")
                if isinstance(actions, list) and actions
                else trace.get("observation")
            )
        )
        if not isinstance(final, Mapping) or type(final.get("goal_reached")) is not bool:
            return None
        goal = final["goal_reached"]
        if "goal_reached" in trace and (
            type(trace["goal_reached"]) is not bool or trace["goal_reached"] != goal
        ):
            return None
        if actions:
            action_goal = actions[-1].get("observation_after", {}).get("goal_reached")
            if type(action_goal) is not bool or action_goal != goal:
                return None
        return goal

    def reexecute(self) -> dict[str, Any]:
        if not self._experiments:
            return {
                "valid": None,
                "status": "not_run",
                "reason": "no_committed_engine_steps",
                "checks": [],
            }
        checks = []
        started = time.perf_counter()
        for index, (payload, original) in enumerate(self._experiments):
            result = self._run("experiment", payload, f"reexecution-{index}", replay=True)
            replayed = result.get("trace", {})
            if result.get("status") != "completed":
                checks.append({"passed": False, "error": result.get("error", "reexecution_failed")})
                continue
            comparison = self._legacy()._engine_reexecution_comparison(original, replayed)
            original_goal, replayed_goal = (
                self._goal_witness(original),
                self._goal_witness(replayed),
            )
            comparison["goal_witness"] = (
                original_goal is not None
                and replayed_goal is not None
                and original_goal == replayed_goal
            )
            comparison["passed"] = (
                comparison["passed"]
                and comparison["goal_witness"]
                and replayed.get("passed") is True
            )
            checks.append(comparison)
        return {
            "valid": all(check["passed"] for check in checks),
            "status": "completed",
            "checks": checks,
            "latency_ms": (time.perf_counter() - started) * 1000,
            "scope": "fresh_godot_processes_exact_immutable_episode_inputs",
            "accounting_boundary": "posthoc_reexecution_not_goal_completion_wall",
            "model_calls": 0,
        }


__all__ = [
    "EpisodeLimits",
    "EpisodePersistenceError",
    "GodotEpisodeEngine",
    "ModelSpec",
    "aggregate_episode_records",
    "run_episode",
    "verify_episode_record",
]
