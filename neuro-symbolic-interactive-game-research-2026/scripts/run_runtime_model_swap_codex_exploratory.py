#!/usr/bin/env python3
"""Prospective, non-confirmatory Codex selector exploratory runner.

The default and ``--prelaunch`` paths are offline. They write a fresh plan and
prelaunch receipt without reading credentials or starting ``codex``/Godot. A
live cell uses the existing Codex ``exec`` command and sanitized OAuth handoff,
then feeds the returned proposal through the unchanged fixed-game validator.
Provider identity remains explicitly unknown unless a provider receipt proves it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
import uuid
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_npc_goal_experiment import run_godot
from run_playable_evaluation import stage_project

from nesy_game.npc_goal import SCHEMA_PATH
from nesy_game.runtime_model_swap import (
    EpisodeLimits,
    GodotEpisodeEngine,
    ModelSpec,
    run_episode,
)
from nesy_game.runtime_model_swap_native import (
    EXTENSION_ACTIVATION_SCHEMA,
    NativeActivationTrust,
    NativePromptRunner,
    _bound_json_object,
    _claim_extension_activation,
    _sanitized_environment,
    load_pinned_native_activation,
    run_host_process,
    validate_native_context,
)

PROMPT = "Restore the lighthouse signal and reveal the authorized tide lead."
FIXTURE_REF = "data/fixtures/npc-goal-recovery/validated-v2/engineering.json#ENG-S01"
COHORT = "codex-selector-exploratory"
STUDY_ID = "codex-selector-exploratory-fixed-game-20261028"
FROZEN_PACKET_EXPECTED = {
    "assignment_plan": "2da3a4de5512ce79bb04be3f7b663fe8e4ea7aa51a52ac19e2dc7f7611d54629",
    "approved_scope": "3ef35166e2d1a6fa3de63b751f68a2ecba1e0a6e68eeb801495a666b6194749a",
}
REPRESENTATIONS = ("general_rule", "ontology")
FROZEN_PACKET = (
    ROOT
    / "research"
    / "runtime-model-swap-20261024"
    / "codex-identity-20261026"
    / "frozen-packet-v1"
)


class ExploratoryActivationRequired(RuntimeError):
    """Raised when a live cell is requested without explicit user admission."""


class CodexSelectorPromptRunner:
    """Codex exec transport bound to one fresh source-pinned activation row."""

    def __init__(
        self,
        *,
        selector: str,
        trusted_activation: NativeActivationTrust,
        expected_assignment_id: str,
        expected_config_hash: str,
        expected_representation: str,
        expected_seed: int,
        expected_fixture_ref: str,
        native_context: Mapping[str, Any] | None = None,
        process_runner: Any = None,
        max_dispatches: int = 12,
        clock: Any = time.monotonic,
    ) -> None:
        if selector != "gpt-6-luna":
            raise ValueError("requested_selector_must_be_gpt-6-luna")
        if not isinstance(trusted_activation, NativeActivationTrust):
            raise ValueError("fresh_source_bound_activation_required")  # noqa: TRY004
        if trusted_activation.activation.get("schema_version") != EXTENSION_ACTIVATION_SCHEMA:
            raise ValueError("fresh_extension_activation_required")
        if trusted_activation.row.get("assignment_id") != trusted_activation.row_id:
            raise ValueError("activation_row_id_mismatch")
        self.selector = selector
        self.trusted_activation = trusted_activation
        self.expected_assignment_id = expected_assignment_id
        self.expected_config_hash = expected_config_hash
        self.expected_representation = expected_representation
        self.expected_seed = expected_seed
        self.expected_fixture_ref = expected_fixture_ref
        _validate_limits(
            max_dispatches=max_dispatches, episode_timeout=180.0, response_timeout=60.0
        )
        self.native_context = native_context
        self.process_runner = process_runner
        self.max_dispatches = max_dispatches
        self._activation_claimed = False
        self._activation_pid: int | None = None
        self._dispatch_starts = 0
        self.clock = clock
        self.prompt_calls: list[dict[str, Any]] = []
        self.prompt_receipts: list[dict[str, Any]] = []
        self.raw_model_outputs: list[Any] = []

    def _admit(self, prompt: str) -> dict[str, Any]:
        row = self.trusted_activation.row
        required_source_files = {
            "scripts/run_runtime_model_swap_codex_exploratory.py": _sha256_file(Path(__file__))
        }
        validation = validate_native_context(
            self.native_context,
            model={
                "host": "codex",
                "selector": self.selector,
                "effort": "medium",
                "representation": self.expected_representation,
                "offline": False,
            },
            config={
                "assignment_id": self.trusted_activation.row_id,
                "study_id": self.trusted_activation.activation.get("study_id"),
                "model_selector": self.selector,
                "representation": self.expected_representation,
                "effort": "medium",
                "quest_id": row.get("quest_id"),
                "seed": self.expected_seed,
                "repeat": row.get("repeat"),
                "reset": row.get("reset"),
                "fixture_id": self.expected_fixture_ref,
            },
            prompt=prompt,
            source_root=self.trusted_activation.source_root,
            trusted_activation=self.trusted_activation,
            required_source_files=required_source_files,
        )
        reasons = list(validation.get("reasons", []))
        simulation = self.trusted_activation.purpose == "test_simulation"
        if simulation and self.process_runner is None:
            reasons.append("engineering_fixture_transport_required")
        elif not simulation and self.process_runner is not None:
            reasons.append("injected_transport_only_allowed_for_fixture")
        if not reasons:
            if self._activation_claimed:
                if self._activation_pid != os.getpid():
                    reasons.append("native_activation_row_already_claimed")
            else:
                claim_error = _claim_extension_activation(self.trusted_activation)
                if claim_error is not None:
                    reasons.append(claim_error)
                else:
                    self._activation_claimed = True
                    self._activation_pid = os.getpid()
        return {
            "ready": not reasons,
            "reasons": reasons,
            "required_source_files": required_source_files,
            "required_source_files_verified": validation.get("ready") is True,
        }

    def __call__(self, **kwargs: Any) -> Any:
        request_id = str(kwargs.get("request_id") or "")
        if not request_id:
            return self._result(2, {}, {"error": "request_id_missing", "failure_kind": "logical"})
        requested_model = kwargs.get("model")
        if requested_model is not None and requested_model != self.selector:
            return self._result(
                2, {}, {"error": "requested_model_mismatch", "failure_kind": "authorization"}
            )
        if kwargs.get("assignment_id") != self.expected_assignment_id:
            return self._result(
                2, {}, {"error": "assignment_binding_mismatch", "failure_kind": "authorization"}
            )
        if kwargs.get("row_id") != self.trusted_activation.row_id:
            return self._result(
                2, {}, {"error": "row_binding_mismatch", "failure_kind": "authorization"}
            )
        if kwargs.get("config_hash") != self.expected_config_hash:
            return self._result(
                2, {}, {"error": "config_binding_mismatch", "failure_kind": "authorization"}
            )
        timeout_value = kwargs.get("timeout", 60.0)
        if not isinstance(timeout_value, (int, float)) or isinstance(timeout_value, bool):
            return self._result(
                2, {}, {"error": "invalid_response_timeout", "failure_kind": "logical"}
            )
        timeout = min(float(timeout_value), 60.0)
        if timeout <= 0:
            return self._result(
                124,
                {},
                {
                    "error": "response_deadline_exhausted",
                    "timed_out": True,
                    "failure_kind": "timeout",
                },
            )
        instruction = kwargs.get("instruction") or kwargs.get("user_prompt") or ""
        try:
            instruction_text = (
                instruction.decode("utf-8") if isinstance(instruction, bytes) else str(instruction)
            )
        except UnicodeDecodeError:
            return self._result(
                2, {}, {"error": "outgoing_request_not_utf8", "failure_kind": "logical"}
            )
        user_prompt = kwargs.get("user_prompt", "")
        try:
            user_prompt_bytes = (
                user_prompt if isinstance(user_prompt, bytes) else str(user_prompt).encode("utf-8")
            )
            user_prompt_text = user_prompt_bytes.decode("utf-8")
        except UnicodeError:
            return self._result(
                2, {}, {"error": "outgoing_user_prompt_not_utf8", "failure_kind": "logical"}
            )
        schema_value = kwargs.get("output_schema")
        schema_bytes: bytes | None = None
        if isinstance(schema_value, bytes):
            schema_bytes = schema_value
        elif isinstance(schema_value, (str, Path)):
            try:
                schema_bytes = Path(schema_value).read_bytes()
            except OSError:
                schema_bytes = None
        activation_bindings = self.trusted_activation.activation.get("artifact_bindings")
        if isinstance(activation_bindings, Mapping):
            schema_digest = (
                hashlib.sha256(schema_bytes).hexdigest() if schema_bytes is not None else None
            )
            expected_schema = activation_bindings.get("output_schema_sha256")
            instruction_digest = hashlib.sha256(instruction_text.encode("utf-8")).hexdigest()
            prompt_digest = hashlib.sha256(user_prompt_bytes).hexdigest()
            allowed = activation_bindings.get("allowed_requests")
            allowed_tuples = (
                {
                    (
                        item.get("instruction_sha256"),
                        item.get("user_prompt_sha256"),
                        item.get("output_schema_sha256"),
                    )
                    for item in allowed
                    if isinstance(item, Mapping)
                }
                if isinstance(allowed, (list, tuple))
                else set()
            )
            if (
                schema_digest != expected_schema
                or (instruction_digest, prompt_digest, schema_digest) not in allowed_tuples
            ):
                return self._result(
                    2,
                    {},
                    {"error": "outgoing_request_tuple_not_bound", "failure_kind": "authorization"},
                )
        receipt: dict[str, Any] = {
            "schema_version": "runtime-codex-selector-receipt/1",
            "request_id": request_id,
            "assignment_id": self.expected_assignment_id,
            "row_id": self.trusted_activation.row_id,
            "config_hash": self.expected_config_hash,
            "activation_sha256": self.trusted_activation.activation_sha256,
            "plan_sha256": self.trusted_activation.plan_sha256,
            "host": "codex",
            "selector": self.selector,
            "effort": "medium",
            "provider_identity": None,
            "provider_identity_verified": False,
            "provider_revision": None,
            "identity_status": "unknown",
            "identity_source": None,
            "transport_kind": "local_process",
            "requested_selector": self.selector,
            "request_sha256": hashlib.sha256(instruction_text.encode("utf-8")).hexdigest(),
            "attempted": False,
            "dispatch_started": False,
            "local_process_started": False,
            "provider_request_count": None,
            "provider_request_count_authoritative": False,
            "cost_usd": None,
            "cost_status": "unknown",
            "provider_retries": 0,
            "synthetic": False,
            "scientific_eligible": False,
        }
        validation = self._admit(user_prompt_text)
        receipt["admission"] = validation
        if validation["ready"] is not True:
            receipt.update(error="native_context_rejected", failure_kind="authorization")
            return self._result(2, {}, receipt)
        if self._dispatch_starts >= self.max_dispatches:
            receipt.update(error="native_extension_dispatch_limit", failure_kind="authorization")
            return self._result(2, {}, receipt)
        started = self.clock()
        try:
            import tempfile

            with tempfile.TemporaryDirectory(prefix="runtime-codex-selector-") as directory:
                scratch = Path(directory).resolve()
                output_last = scratch / "last-message.json"
                schema_value = kwargs.get("output_schema")
                command = NativePromptRunner(
                    host="codex",
                    selector=self.selector,
                    effort="medium",
                    native_context={"billing_policy": "existing_credits_no_new_purchase"},
                    trusted_activation=self.trusted_activation,
                )._command(scratch, schema_value, output_last)
                environment = _sanitized_environment()
                codex_home = scratch / ".codex"
                codex_home.mkdir()
                auth_file = Path(environment.get("HOME") or Path.home()) / ".codex" / "auth.json"
                if self.process_runner is None:
                    if not auth_file.is_file() or not os.access(auth_file, os.R_OK):
                        receipt.update(error="codex_auth_unavailable", failure_kind="authorization")
                        return self._result(2, {}, receipt)
                    (codex_home / "auth.json").symlink_to(auth_file.resolve(strict=True))
                environment["HOME"] = str(scratch)
                environment["CODEX_HOME"] = str(codex_home)
                for key, leaf in (
                    ("TMPDIR", "tmp"),
                    ("TMP", "tmp"),
                    ("TEMP", "tmp"),
                    ("XDG_CONFIG_HOME", ".config"),
                    ("XDG_CACHE_HOME", ".cache"),
                    ("XDG_DATA_HOME", ".local/share"),
                ):
                    isolated = scratch / leaf
                    isolated.mkdir(parents=True, exist_ok=True)
                    environment[key] = str(isolated)
                receipt.update(
                    command=[_redact_path(str(part), scratch) for part in command],
                    attempted=True,
                    dispatch_started=True,
                    local_process_started=False,
                    timeout_seconds=timeout,
                )
                self._dispatch_starts += 1
                transport = self.process_runner or run_host_process
                completed = transport(
                    command,
                    cwd=str(scratch),
                    input=instruction_text,
                    check=False,
                    capture_output=True,
                    env=environment,
                    text=True,
                    timeout=timeout,
                    on_started=(lambda: receipt.update(local_process_started=True))
                    if self.process_runner is None
                    else None,
                )
                raw_stdout = str(completed.stdout or "")
                raw_stderr = str(completed.stderr or "")
                receipt.update(
                    returncode=completed.returncode,
                    stdout_sha256=hashlib.sha256(
                        raw_stdout.encode("utf-8", errors="replace")
                    ).hexdigest(),
                    stderr_sha256=hashlib.sha256(
                        raw_stderr.encode("utf-8", errors="replace")
                    ).hexdigest(),
                    stdout_bytes=len(raw_stdout.encode("utf-8", errors="replace")),
                    stderr_bytes=len(raw_stderr.encode("utf-8", errors="replace")),
                    provider_request_count=None,
                    provider_request_count_authoritative=False,
                    provider_request_count_ambiguous=True,
                    provider_request_count_basis="transport_process_only_no_authoritative_provider_evidence",
                    provider_retries=0,
                    duration_seconds=self.clock() - started,
                )
                parser = NativePromptRunner(
                    host="codex", selector=self.selector, effort="medium", native_context={}
                )
                payload, parsed = parser._parse(completed, output_last)
                receipt.update(parsed)
                if completed.returncode != 0:
                    receipt.update(error="host_process_failed", failure_kind="logical")
                    return self._result(int(completed.returncode), {}, receipt)
                if payload is None:
                    receipt.update(error="malformed_response", failure_kind="logical")
                    return self._result(5, {}, receipt)
                if payload.get("request_id") not in {None, request_id}:
                    receipt.update(error="request_id_mismatch", failure_kind="logical")
                    return self._result(6, {}, receipt)
                validator = kwargs.get("validator")
                if validator is not None and not validator(payload, request_id):
                    receipt.update(error="validator_rejected", failure_kind="logical")
                    return self._result(6, {}, receipt)
                self.raw_model_outputs.append(payload)
                return self._result(0, payload, receipt)
        except __import__("subprocess").TimeoutExpired as exc:
            raw_output = _safe_text(exc.output)
            raw_error = _safe_text(exc.stderr)
            receipt.update(
                error="response_timeout",
                timed_out=True,
                failure_kind="timeout",
                stdout_sha256=hashlib.sha256(raw_output.encode("utf-8")).hexdigest(),
                stderr_sha256=hashlib.sha256(raw_error.encode("utf-8")).hexdigest(),
            )
            return self._result(124, {}, receipt)
        except (FileNotFoundError, OSError) as exc:
            receipt.update(
                error=f"host_launch_failed:{type(exc).__name__}", failure_kind="transport"
            )
            return self._result(127, {}, receipt)

    def _result(self, returncode: int, payload: dict[str, Any], receipt: dict[str, Any]) -> Any:
        simulation = self.trusted_activation.purpose == "test_simulation"
        receipt.setdefault("request_id", None)
        receipt.setdefault("attempted", False)
        receipt.setdefault("dispatch_started", False)
        receipt.setdefault("local_process_started", False)
        receipt.setdefault("provider_retries", 0)
        receipt.setdefault("provider_identity", None)
        receipt.setdefault("provider_identity_verified", False)
        receipt.setdefault("identity_status", "unknown")
        receipt.setdefault("cost_usd", None)
        receipt["synthetic"] = simulation
        receipt["scientific_eligible"] = False
        receipt["mode"] = "test_simulation" if simulation else "configured_selector_exploratory"
        if self.process_runner is not None:
            receipt["transport_kind"] = "injected_fixture"
        receipt.setdefault("duration_seconds", 0.0)
        self.prompt_receipts.append(dict(receipt))
        self.prompt_calls.append(
            {
                "request_id": receipt.get("request_id"),
                "receipt": dict(receipt),
                "returncode": returncode,
            }
        )
        from nesy_game.runtime_model_swap_native import NativePromptResult

        return NativePromptResult(returncode, payload, receipt)


def _json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _safe_text(value: Any) -> str:
    return str(value).encode("utf-8", errors="backslashreplace").decode("utf-8")[:512]


def _redact_path(value: str, scratch: Path) -> str:
    """Keep receipts replayable without persisting host-specific paths."""
    text = _safe_text(value)
    replacements = {
        str(scratch): "<scratch>",
        str(ROOT.resolve()): "<project-root>",
        str(Path.home().resolve()): "<home>",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return "<external>"


def _write_json_once(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _validate_limits(
    *, max_dispatches: int, episode_timeout: float, response_timeout: float
) -> None:
    if type(max_dispatches) is not int or not 1 <= max_dispatches <= 12:
        raise ValueError("max_dispatches_must_be_between_1_and_12")
    if not isinstance(episode_timeout, (int, float)) or isinstance(episode_timeout, bool):
        raise ValueError("episode_timeout_invalid")  # noqa: TRY004
    if not 0 < float(episode_timeout) <= 180:
        raise ValueError("episode_timeout_must_be_between_0_and_180_seconds")
    if not isinstance(response_timeout, (int, float)) or isinstance(response_timeout, bool):
        raise ValueError("response_timeout_invalid")  # noqa: TRY004
    if not 0 < float(response_timeout) <= 60:
        raise ValueError("response_timeout_must_be_between_0_and_60_seconds")


def _validate_representations(representations: Sequence[str]) -> tuple[str, ...]:
    values = tuple(str(value) for value in representations)
    if values != REPRESENTATIONS:
        raise ValueError("representations_must_be_exactly_general_rule_then_ontology")
    return values


def _assignment_id(seed: int, representation: str) -> str:
    return f"{COHORT}-{seed}-{representation}"


def build_plan(
    *,
    model: str = "gpt-6-luna",
    seed: int = 20261028,
    representations: Sequence[str] = REPRESENTATIONS,
    max_dispatches: int = 12,
    episode_timeout: float = 180.0,
    response_timeout: float = 60.0,
) -> dict[str, Any]:
    """Build a fresh two-cell plan without touching the frozen cohort."""
    if model != "gpt-6-luna":
        raise ValueError("requested_selector_must_be_gpt-6-luna")
    if type(seed) is not int:
        raise ValueError("seed_must_be_integer")
    reps = _validate_representations(representations)
    _validate_limits(
        max_dispatches=max_dispatches,
        episode_timeout=episode_timeout,
        response_timeout=response_timeout,
    )
    cells = [
        {
            "assignment_id": _assignment_id(seed, representation),
            "representation": representation,
            "seed": seed,
            "repeat": 1,
            "reset": True,
            "status": "planned",
            "executed": False,
            "scientific_assignment": False,
        }
        for representation in reps
    ]
    plan = {
        "schema_version": "runtime-codex-selector-exploratory/1",
        "status": "plan_only",
        "cohort": COHORT,
        "study_id": STUDY_ID,
        "quest_id": "sealed-lighthouse-v1",
        "goal": "harbor-signal-restored-authorized-tide-lead-v1",
        "target": {
            "host": "codex",
            "requested_selector": model,
            "effort": "medium",
            "transport": "native_codex_exec",
        },
        "cells": cells,
        "representations": list(reps),
        "seed": seed,
        "limits": {
            "max_host_dispatches": max_dispatches,
            "episode_seconds": float(episode_timeout),
            "response_seconds": float(response_timeout),
            "max_repairs_per_decision": 2,
        },
        "provenance": {
            "requested_selector": model,
            "provider_identity": None,
            "provider_revision": None,
            "identity_status": "unknown_until_provider_response",
            "response_required_for_identity": True,
            "provider_request_count": None,
            "cost_usd": None,
            "cost_status": "unknown_until_authoritative_receipt",
        },
        "claim_boundary": [
            "configured-selector exploratory observation only",
            "not verified provider identity",
            "not a strict native identity cohort",
            "not causal evidence for representation or ontology efficacy",
            "assigned failures and unknown identity remain in denominator bookkeeping",
        ],
        "replay": {
            "prompt": PROMPT,
            "fixture_ref": FIXTURE_REF,
            "source_root": "project_root",
            "fresh_output_required": True,
            "raw_credentials_persisted": False,
        },
        "config_hash": None,
    }
    plan["config_hash"] = _hash({key: value for key, value in plan.items() if key != "config_hash"})
    return plan


def _source_checks() -> dict[str, Any]:
    required = {
        "exploratory_entrypoint": Path(__file__).resolve(),
        "runtime_model_swap": ROOT / "src" / "nesy_game" / "runtime_model_swap.py",
        "runtime_model_swap_native": ROOT / "src" / "nesy_game" / "runtime_model_swap_native.py",
        "godot_project": ROOT / "game-track" / "godot" / "project.godot",
        "output_schema": SCHEMA_PATH,
        "fixture": ROOT
        / "data"
        / "fixtures"
        / "npc-goal-recovery"
        / "validated-v2"
        / "engineering.json",
    }
    return {
        name: {"present": path.is_file(), "sha256": _sha256_file(path), "path": _relative(path)}
        for name, path in required.items()
    }


def _frozen_packet_checks() -> dict[str, Any]:
    files = {
        "assignment_plan": FROZEN_PACKET / "assignment-plan.json",
        "approved_scope": FROZEN_PACKET / "approved-scope.json",
    }
    return {
        name: {"present": path.is_file(), "sha256": _sha256_file(path), "path": _relative(path)}
        for name, path in files.items()
    }


def prelaunch_check(
    *,
    output_dir: str | Path,
    model: str = "gpt-6-luna",
    seed: int = 20261028,
    representations: Sequence[str] = REPRESENTATIONS,
    max_dispatches: int = 12,
    episode_timeout: float = 180.0,
    response_timeout: float = 60.0,
) -> dict[str, Any]:
    """Write fresh offline plan/check artifacts; never starts a process."""
    plan = build_plan(
        model=model,
        seed=seed,
        representations=representations,
        max_dispatches=max_dispatches,
        episode_timeout=episode_timeout,
        response_timeout=response_timeout,
    )
    output = Path(output_dir).expanduser().resolve()
    if output == ROOT.resolve() or output.exists():
        raise FileExistsError("output_dir_must_be_fresh_and_non_root")
    source = _source_checks()
    frozen = _frozen_packet_checks()
    missing = [name for name, row in source.items() if row["present"] is not True]
    frozen_drift = [
        name
        for name, expected in FROZEN_PACKET_EXPECTED.items()
        if frozen.get(name, {}).get("present") is not True
        or frozen.get(name, {}).get("sha256") != expected
    ]
    codex_available = shutil.which("codex") is not None
    offline_status = (
        "offline_checks_passed"
        if not missing and not frozen_drift and codex_available
        else "blocked"
    )
    check = {
        "schema_version": "runtime-codex-selector-prelaunch/1",
        "live_calls": 0,
        "status": offline_status,
        "subprocesses_started": 0,
        "credentials_read": False,
        "auth_status": "not_checked_no_credentials_access",
        "requested_selector": model,
        "provider_identity": None,
        "provider_revision": None,
        "identity_status": "unknown_until_provider_response",
        "codex_binary_available": codex_available,
        "native_validator": "required_before_any_dispatch",
        "native_transport": "codex_exec_model_selector",
        "source_checks": source,
        "frozen_packet_checks": frozen,
        "blockers": [
            "no_live_calls_in_prelaunch",
            "separate_external_source_bound_activation_required_for_live_dispatch",
        ],
        "frozen_packet_drift": frozen_drift,
        "missing_source_artifacts": missing,
        "exact_command": [
            "PYTHONDONTWRITEBYTECODE=1",
            "python",
            "scripts/run_runtime_model_swap_codex_exploratory.py",
            "--model",
            model,
            "--seed",
            str(seed),
            "--output-dir",
            "<fresh-output-dir>",
            "--max-dispatches",
            str(max_dispatches),
            "--episode-timeout",
            str(float(episode_timeout)),
            "--response-timeout",
            str(float(response_timeout)),
            "--prelaunch",
        ],
        "execute_command": [
            "PYTHONDONTWRITEBYTECODE=1",
            "python",
            "scripts/run_runtime_model_swap_codex_exploratory.py",
            "--execute",
            "--admit-exploratory",
            "--model",
            model,
            "--seed",
            str(seed),
            "--output-dir",
            "<fresh-output-dir>",
            "--activation-path",
            "<general-rule-activation.json>",
            "--activation-sha256",
            "<general-rule-activation-sha256>",
            "--activation-path",
            "<ontology-activation.json>",
            "--activation-sha256",
            "<ontology-activation-sha256>",
            "--plan-path",
            "<fresh-assignment-plan.json>",
            "--plan-sha256",
            "<plan-sha256>",
            "--row-id",
            "<general-rule-row-id>",
            "--row-id",
            "<ontology-row-id>",
            "--trust-root",
            "<trust-root>",
            "--source-root",
            "<source-root>",
            "--max-dispatches",
            str(max_dispatches),
            "--episode-timeout",
            str(float(episode_timeout)),
            "--response-timeout",
            str(float(response_timeout)),
        ],
        "plan_config_hash": plan["config_hash"],
        "claim_boundary": plan["claim_boundary"],
    }
    if missing:
        check["status"] = "blocked"
    output.mkdir(parents=True, exist_ok=False)
    _write_json_once(output / "admission-plan.json", plan)
    _write_json_once(output / "prelaunch-check.json", check)
    return {"plan": plan, "check": check}


def _identity_summary(record: Mapping[str, Any]) -> dict[str, Any]:
    evidence = record.get("evidence") if isinstance(record.get("evidence"), Mapping) else {}
    receipts = (
        evidence.get("prompt_receipts") if isinstance(evidence.get("prompt_receipts"), list) else []
    )
    identities = {
        receipt.get("provider_identity")
        for receipt in receipts
        if isinstance(receipt, Mapping) and isinstance(receipt.get("provider_identity"), str)
    }
    revisions = {
        receipt.get("provider_revision")
        for receipt in receipts
        if isinstance(receipt, Mapping) and isinstance(receipt.get("provider_revision"), str)
    }
    verified = all(
        isinstance(receipt, Mapping) and receipt.get("provider_identity_verified") is True
        for receipt in receipts
    ) and bool(receipts)
    return {
        "requested_selector": record.get("model", {}).get("model_id"),
        "provider_identity": min(identities) if len(identities) == 1 else None,
        "provider_revision": min(revisions) if len(revisions) == 1 else None,
        "identity_status": "verified" if verified else "unknown",
        "response_receipts": len(receipts),
    }


def _validate_exploratory_activation_pair(
    *,
    trusted_activation: NativeActivationTrust,
    authorization_row_id: str,
    representation: str,
    seed: int,
) -> None:
    """Validate one loaded row before either exploratory cell can dispatch."""
    if representation not in REPRESENTATIONS:
        raise ValueError("unsupported_representation")
    if not isinstance(trusted_activation, NativeActivationTrust):
        raise ExploratoryActivationRequired("fresh_source_bound_activation_required")
    row = trusted_activation.row
    if (
        trusted_activation.row_id != authorization_row_id
        or row.get("assignment_id") != authorization_row_id
    ):
        raise ExploratoryActivationRequired("fresh_activation_cell_mismatch")
    target = row.get("target")
    if not isinstance(target, Mapping) or any(
        target.get(key) != value
        for key, value in {"host": "codex", "selector": "gpt-6-luna", "effort": "medium"}.items()
    ):
        raise ExploratoryActivationRequired("fresh_activation_target_mismatch")
    if "family_label" in target and not isinstance(target.get("family_label"), str):
        raise ExploratoryActivationRequired("fresh_activation_family_label_invalid")
    if row.get("representation") != representation or row.get("seed") != seed:
        raise ExploratoryActivationRequired("fresh_activation_row_mismatch")
    if _assignment_id(seed, representation) == authorization_row_id:
        raise ExploratoryActivationRequired("exploratory_assignment_must_be_distinct")
    bindings = trusted_activation.activation.get("artifact_bindings")
    if not isinstance(bindings, Mapping) or not isinstance(
        bindings.get("allowed_requests"), (list, tuple)
    ):
        raise ExploratoryActivationRequired("fresh_request_binding_required")
    permissions = trusted_activation.activation.get("permissions")
    billing_policy = trusted_activation.activation.get("billing_policy")
    if not isinstance(permissions, Mapping) or billing_policy != "existing_credits_no_new_purchase":
        raise ExploratoryActivationRequired("fresh_billing_gate_required")


def run_exploratory_cell(
    *,
    output_dir: str | Path,
    representation: str,
    seed: int,
    trusted_activation: NativeActivationTrust,
    native_context: Mapping[str, Any] | None = None,
    process_runner: Any = None,
    authorization_row_id: str | None = None,
    max_dispatches: int = 12,
    episode_timeout: float = 180.0,
    response_timeout: float = 60.0,
    godot_binary: str | None = None,
    exploratory_plan_hash: str | None = None,
) -> dict[str, Any]:
    """Run one actual cell under a fresh source-pinned activation gate."""
    if representation not in REPRESENTATIONS:
        raise ValueError("unsupported_representation")
    if not isinstance(trusted_activation, NativeActivationTrust):
        raise ExploratoryActivationRequired("fresh_source_bound_activation_required")
    row = trusted_activation.row
    expected_row_id = (
        trusted_activation.row_id if authorization_row_id is None else authorization_row_id
    )
    if trusted_activation.row_id != expected_row_id or row.get("assignment_id") != expected_row_id:
        raise ExploratoryActivationRequired("fresh_activation_cell_mismatch")
    authorization_row_id = expected_row_id
    target = row.get("target")
    if isinstance(target, Mapping):
        if any(
            target.get(key) != value
            for key, value in {
                "host": "codex",
                "selector": "gpt-6-luna",
                "effort": "medium",
            }.items()
        ):
            raise ExploratoryActivationRequired("fresh_activation_target_mismatch")
        if "family_label" in target and not isinstance(target.get("family_label"), str):
            raise ExploratoryActivationRequired("fresh_activation_family_label_invalid")
    if row.get("representation") not in (None, representation) or row.get("seed") not in (
        None,
        seed,
    ):
        raise ExploratoryActivationRequired("fresh_activation_row_mismatch")
    assignment_id = _assignment_id(seed, representation)
    if assignment_id == authorization_row_id:
        raise ExploratoryActivationRequired("exploratory_assignment_must_be_distinct")
    bindings = trusted_activation.activation.get("artifact_bindings")
    if not isinstance(bindings, Mapping) or not isinstance(
        bindings.get("allowed_requests"), (list, tuple)
    ):
        raise ExploratoryActivationRequired("fresh_request_binding_required")
    _validate_limits(
        max_dispatches=max_dispatches,
        episode_timeout=episode_timeout,
        response_timeout=response_timeout,
    )
    if exploratory_plan_hash is None:
        exploratory_plan_hash = build_plan(
            model="gpt-6-luna",
            seed=seed,
            representations=REPRESENTATIONS,
            max_dispatches=max_dispatches,
            episode_timeout=episode_timeout,
            response_timeout=response_timeout,
        )["config_hash"]
    if not isinstance(exploratory_plan_hash, str) or len(exploratory_plan_hash) != 64:
        raise ExploratoryActivationRequired("fresh_exploratory_plan_hash_required")
    output = Path(output_dir).expanduser().resolve()
    if output.exists():
        if not output.is_dir() or any(output.iterdir()):
            raise FileExistsError("cell_output_dir_must_be_fresh")
    else:
        output.mkdir(parents=True, exist_ok=False)
    config = {
        "cohort": COHORT,
        "study_id": STUDY_ID,
        "assignment_id": assignment_id,
        "authorization_row_id": authorization_row_id,
        "exploratory_plan_hash": exploratory_plan_hash,
        "execution_mode": "configured_selector_exploratory",
        "model_host": "codex",
        "model_selector": "gpt-6-luna",
        "representation": representation,
        "effort": "medium",
        "seed": seed,
        "quest_id": "sealed-lighthouse-v1",
        "fixture_id": FIXTURE_REF,
        "claim_boundary": "configured-selector exploratory observation only",
    }
    limits = EpisodeLimits(
        wall_seconds=float(episode_timeout),
        response_seconds=float(response_timeout),
        max_host_calls=max_dispatches,
    )
    config_hash = _hash(config)
    permissions = trusted_activation.activation.get("permissions")
    billing_policy = trusted_activation.activation.get("billing_policy")
    if not isinstance(permissions, Mapping) or billing_policy != "existing_credits_no_new_purchase":
        raise ExploratoryActivationRequired("fresh_billing_gate_required")
    admission = {
        "mode": "configured_selector_exploratory",
        "ready": True,
        "requested_selector": "gpt-6-luna",
        "assignment_id": assignment_id,
        "authorization_row_id": authorization_row_id,
        "config_hash": config_hash,
        "exploratory_plan_hash": exploratory_plan_hash,
        "activation_study_id": trusted_activation.activation.get("study_id"),
        "prompt_hash": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "max_host_dispatches": max_dispatches,
        "episode_seconds": float(episode_timeout),
        "response_seconds": float(response_timeout),
        "provider_retries": 0,
        "raw_credentials_persisted": False,
        "activation_sha256": trusted_activation.activation_sha256,
        "plan_sha256": trusted_activation.plan_sha256,
        "row_sha256": trusted_activation.row_sha256,
        "row_id": trusted_activation.row_id,
        "account_gate": dict(permissions),
        "billing_policy": billing_policy,
    }
    runner = CodexSelectorPromptRunner(
        selector="gpt-6-luna",
        trusted_activation=trusted_activation,
        expected_assignment_id=assignment_id,
        expected_config_hash=config_hash,
        expected_representation=representation,
        expected_seed=seed,
        expected_fixture_ref=FIXTURE_REF,
        native_context=native_context,
        process_runner=process_runner,
        max_dispatches=max_dispatches,
    )
    native_admission = runner._admit(PROMPT)
    if native_admission["ready"] is not True:
        raise ExploratoryActivationRequired(
            "native_context_rejected:" + ",".join(native_admission["reasons"])
        )
    admission["native_admission"] = native_admission
    with __import__("tempfile").TemporaryDirectory(
        prefix="runtime-codex-selector-project-"
    ) as working:
        project = Path(working) / "project"
        stage_project(ROOT / "game-track" / "godot", project)
        engine = GodotEpisodeEngine(
            project=project,
            output_root=output,
            seed=seed,
            assignment_id=assignment_id,
            prompt_runner=runner,
            engine_runner=run_godot,
            godot_binary=godot_binary or shutil.which("godot4") or shutil.which("godot") or "godot",
            fixture_ref=FIXTURE_REF,
        )
        record = run_episode(
            engine=engine,
            proposal_source=engine.propose,
            repair_source=engine.repair,
            model=ModelSpec(
                "gpt-6-luna", representation, provider="codex", revision=None, offline=False
            ),
            limits=limits,
            seed=seed,
            clock=time.monotonic,
            config=config,
            prompt=PROMPT,
            output_path=None,
            trusted_activation=trusted_activation,
            exploratory_context=admission,
        )
    evidence = record.setdefault("evidence", {})
    if trusted_activation.purpose == "test_simulation":
        evidence.setdefault("provenance", {}).update(mode="test_simulation", synthetic=True)
    evidence["provider_identity"] = None
    evidence["provider_revision"] = None
    evidence["provider_identity_status"] = "unknown"
    evidence["cost_usd"] = None
    record["exploratory"] = {
        "cohort": COHORT,
        "claim_boundary": config["claim_boundary"],
        "identity": _identity_summary(record),
        "scientific_eligible": False,
    }
    record["scientific"] = {"assigned": 0, "executed": 0, "eligible": False}
    record["accepted_for_engineering_verification"] = False
    record["record_hash"] = _hash(
        {key: value for key, value in record.items() if key != "record_hash"}
    )
    _write_json_once(output / "episode.json", record)
    return record


def _default_output_dir() -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return (
        ROOT
        / "_workspace"
        / "current"
        / "qa"
        / "releases"
        / f"{COHORT}-{stamp}-{uuid.uuid4().hex[:8]}"
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="gpt-6-luna")
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--max-dispatches", type=int, default=12)
    parser.add_argument("--episode-timeout", type=float, default=180.0)
    parser.add_argument("--response-timeout", type=float, default=60.0)
    parser.add_argument("--prelaunch", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--admit-exploratory", action="store_true")
    parser.add_argument("--activation-path", type=Path, action="append", default=[])
    parser.add_argument("--activation-sha256", action="append", default=[])
    parser.add_argument("--plan-path", type=Path)
    parser.add_argument("--plan-sha256")
    parser.add_argument("--row-id", action="append", default=[])
    parser.add_argument("--trust-root", type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--native-context", type=Path, action="append", default=[])
    return parser.parse_args(argv)


def _failure_record(
    *,
    output: Path,
    representation: str,
    seed: int,
    reason: str,
    assignment_id: str | None = None,
    authorization_row_id: str | None = None,
) -> dict[str, Any]:
    record = {
        "schema_version": "runtime-model-swap/1",
        "assignment_id": assignment_id or _assignment_id(seed, representation),
        "authorization_row_id": authorization_row_id,
        "scope": "bookkeeping",
        "model": {
            "model_id": "gpt-6-luna",
            "representation": representation,
            "provider": "codex",
            "revision": None,
            "offline": False,
        },
        "seed": seed,
        "status": "failure",
        "success": False,
        "goal_reached": False,
        "failure_reason": reason,
        "scientific": {"assigned": 0, "executed": 0, "eligible": False},
        "accepted_for_engineering_verification": False,
        "evidence": {
            "provenance": {
                "mode": "configured_selector_exploratory",
                "synthetic": False,
                "scientific_eligible": False,
            },
            "provider_identity": None,
            "provider_revision": None,
            "cost_usd": None,
        },
    }
    record["record_hash"] = _hash(
        {key: value for key, value in record.items() if key != "record_hash"}
    )
    _write_json_once(output / "episode.json", record)
    return record


def _execute_cells(args: argparse.Namespace, output: Path) -> dict[str, Any]:
    if args.model != "gpt-6-luna":
        raise ExploratoryActivationRequired("requested_selector_must_be_gpt-6-luna")
    activation_paths = (
        tuple(args.activation_path) if isinstance(args.activation_path, (list, tuple)) else ()
    )
    activation_hashes = (
        tuple(args.activation_sha256) if isinstance(args.activation_sha256, (list, tuple)) else ()
    )
    row_ids = tuple(args.row_id) if isinstance(args.row_id, (list, tuple)) else ()
    native_contexts = getattr(args, "native_context", None)
    context_paths = tuple(native_contexts) if isinstance(native_contexts, (list, tuple)) else ()
    required = (args.plan_path, args.plan_sha256, args.trust_root, args.source_root)
    if (
        any(value in (None, "") for value in required)
        or len(activation_paths) != 2
        or len(activation_hashes) != 2
        or len(row_ids) != 2
        or len(context_paths) != 2
        or any(value in (None, "") for value in activation_paths)
        or any(value in (None, "") for value in activation_hashes)
        or any(value in (None, "") for value in row_ids)
        or any(value in (None, "") for value in context_paths)
    ):
        raise ExploratoryActivationRequired("fresh_activation_plan_account_gate_inputs_required")
    plan = build_plan(
        model=args.model,
        seed=args.seed,
        representations=REPRESENTATIONS,
        max_dispatches=args.max_dispatches,
        episode_timeout=args.episode_timeout,
        response_timeout=args.response_timeout,
    )
    output = Path(output).expanduser().resolve()
    if output.exists():
        raise FileExistsError("output_dir_must_be_fresh_and_non_root")
    output.mkdir(parents=True, exist_ok=False)
    total = args.max_dispatches
    first_cap = (total + 1) // 2
    caps = (first_cap, total - first_cap)
    records: list[dict[str, Any]] = []
    for index, (
        representation,
        authorization_row_id,
        activation_path,
        activation_sha256,
    ) in enumerate(zip(REPRESENTATIONS, row_ids, activation_paths, activation_hashes)):
        cell = plan["cells"][index]
        assignment_id = cell["assignment_id"]
        cell_output = output / representation
        cell_output.mkdir(parents=True, exist_ok=False)
        try:
            if caps[index] == 0:
                record = _failure_record(
                    output=cell_output,
                    representation=representation,
                    seed=args.seed,
                    reason="host_dispatch_budget_exhausted",
                    assignment_id=assignment_id,
                    authorization_row_id=authorization_row_id,
                )
            else:
                activation = load_pinned_native_activation(
                    activation_path=activation_path,
                    activation_sha256=activation_sha256,
                    plan_path=args.plan_path,
                    plan_sha256=args.plan_sha256,
                    row_id=authorization_row_id,
                    purpose="production_native",
                    origin="trusted_bootstrap",
                    trust_root=args.trust_root,
                    source_root=args.source_root,
                )
                try:
                    _raw, native_context = _bound_json_object(
                        context_paths[index],
                        trust_root=Path(activation.source_root or ""),
                        label="native_context",
                    )
                except (OSError, ValueError):
                    raise ExploratoryActivationRequired("native_context_invalid") from None
                record = run_exploratory_cell(
                    output_dir=cell_output,
                    representation=representation,
                    seed=args.seed,
                    trusted_activation=activation,
                    native_context=native_context,
                    authorization_row_id=authorization_row_id,
                    max_dispatches=caps[index],
                    episode_timeout=args.episode_timeout,
                    response_timeout=args.response_timeout,
                    exploratory_plan_hash=plan["config_hash"],
                )
        except Exception as exc:  # noqa: BLE001 -- preserve a failure row and continue the second cell
            episode_path = cell_output / "episode.json"
            if episode_path.exists():
                try:
                    record = json.loads(episode_path.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    record = _failure_record(
                        output=cell_output,
                        representation=representation,
                        seed=args.seed,
                        reason=f"{type(exc).__name__}: {_safe_text(exc)}",
                        assignment_id=assignment_id,
                        authorization_row_id=authorization_row_id,
                    )
            else:
                record = _failure_record(
                    output=cell_output,
                    representation=representation,
                    seed=args.seed,
                    reason=f"{type(exc).__name__}: {_safe_text(exc)}",
                    assignment_id=assignment_id,
                    authorization_row_id=authorization_row_id,
                )
        records.append(record)
    observed_counts = [
        row.get("evidence", {}).get("provider_request_count")
        for row in records
        if isinstance(row.get("evidence"), Mapping)
    ]
    summary = {
        "schema_version": "runtime-codex-selector-execution/1",
        "cohort": COHORT,
        "requested_selector": args.model,
        "seed": args.seed,
        "exploratory_plan_hash": plan["config_hash"],
        "max_dispatches_total": args.max_dispatches,
        "cell_dispatch_caps": list(caps),
        "records": [
            {
                "assignment_id": row.get("assignment_id"),
                "authorization_row_id": row.get("authorization_row_id"),
                "representation": row.get("model", {}).get("representation"),
                "status": row.get("status"),
                "failure_reason": row.get("failure_reason"),
                "identity_status": row.get("exploratory", {})
                .get("identity", {})
                .get("identity_status", "unknown"),
            }
            for row in records
        ],
        "live_calls": sum(observed_counts)
        if observed_counts and all(isinstance(value, int) for value in observed_counts)
        else None,
        "live_calls_ambiguous": not observed_counts
        or not all(isinstance(value, int) for value in observed_counts),
    }
    _write_json_once(output / "execution-summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output = args.output_dir or _default_output_dir()
    try:
        if args.execute:
            if not args.admit_exploratory:
                raise ExploratoryActivationRequired("explicit_admit_exploratory_required")
            summary = _execute_cells(args, output)
            print(
                _json(
                    {
                        "status": "completed",
                        "live_calls": summary["live_calls"],
                        "output_dir": _relative(output),
                    }
                )
            )
            return 0
        result = prelaunch_check(
            output_dir=output,
            model=args.model,
            seed=args.seed,
            max_dispatches=args.max_dispatches,
            episode_timeout=args.episode_timeout,
            response_timeout=args.response_timeout,
        )
        print(
            _json(
                {
                    "status": result["check"]["status"],
                    "live_calls": 0,
                    "config_hash": result["plan"]["config_hash"],
                }
            )
        )
        return 0 if result["check"]["status"] == "offline_checks_passed" else 2
    except (OSError, ValueError, TypeError, ExploratoryActivationRequired) as exc:
        print(_json({"status": "blocked", "live_calls": 0, "failure_reason": _safe_text(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
