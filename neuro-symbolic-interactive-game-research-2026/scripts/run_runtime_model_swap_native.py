#!/usr/bin/env python3
"""Source-bound local preparation CLI for the native proposal harness.

No mode is implicit: ``--plan`` and ``--check-only`` inspect local artifacts,
``--engineering-fixture`` uses an injected versioned transcript, and ``--native``
requires a separately source-bound activation context.  This command never
performs account, billing, credential, or provider-readiness probes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_npc_goal_experiment import run_godot
from run_playable_evaluation import stage_project

from nesy_game.runtime_model_swap import (
    EpisodeLimits,
    EpisodePersistenceError,
    GodotEpisodeEngine,
    ModelSpec,
    run_episode,
)
from nesy_game.runtime_model_swap_native import (
    NativeActivationTrust,
    NativePromptRunner,
    _bound_json_object,
    _read_bound_bytes,
    _resolve_bound_path,
    build_assignment_plan,
    validate_native_context,
)


class TranscriptTransport:
    """An explicit local fixture transport; it cannot execute transcript commands."""

    synthetic_request_id_rebinding = True

    def __init__(self, host: str, transcript: Mapping[str, Any]) -> None:
        self.host = host
        self.transcript = transcript
        self.index = 0
        self.calls: list[dict[str, Any]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> Any:
        import subprocess

        self.calls.append({"command": list(command), **kwargs})
        responses = self.transcript.get("responses")
        if not isinstance(responses, list) or self.index >= len(responses):
            return subprocess.CompletedProcess(command, 2, "", "fixture transcript exhausted")
        entry = responses[self.index]
        self.index += 1
        if not isinstance(entry, Mapping) or not isinstance(entry.get("payload"), Mapping):
            return subprocess.CompletedProcess(command, 2, "", "fixture response malformed")
        payload = dict(entry["payload"])
        requested_id = _request_id_from_input(kwargs.get("input"))
        if requested_id and entry.get("request_id_rebinding", "synthetic") == "synthetic":
            payload["request_id"] = requested_id
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        if self.host == "codex":
            command_list = list(command)
            if "--output-last-message" in command_list:
                output = Path(command_list[command_list.index("--output-last-message") + 1])
                output.write_text(encoded, encoding="utf-8")
            stdout = json.dumps(
                {"type": "item.completed", "item": {"type": "agent_message", "text": encoded}}
            )
        elif self.host == "claude_code":
            stdout = json.dumps({"type": "result", "structured_output": payload})
        else:
            stdout = json.dumps({"status": "completed", "response": payload})
        return subprocess.CompletedProcess(command, 0, stdout, "")


def _request_id_from_input(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    marker = '"request_id":'
    position = value.find(marker)
    if position < 0:
        return None
    tail = value[position + len(marker) :].lstrip()
    if not tail.startswith('"'):
        return None
    end = tail.find('"', 1)
    return tail[1:end] if end > 1 else None


def _load_json(path: Path, *, source_root: Path = ROOT) -> dict[str, Any]:
    return _load_bounded_json(path, source_root, label="json")


def _manifest_receipt(path: Path | None, *, kind: str, source_root: Path = ROOT) -> dict[str, Any]:
    if path is None:
        return {"kind": kind, "status": "missing", "sha256": None, "path": None}
    resolved = _bound_path(source_root, str(path), label=f"{kind}_manifest")
    raw, payload = _bound_json_object(resolved, trust_root=source_root, label=f"{kind}_manifest")
    publicity = payload.get("publicity") or payload.get("public_input")
    receipt = {
        "kind": kind,
        "status": "verified"
        if isinstance(publicity, Mapping) and publicity.get("status") == "verified"
        else "unresolved",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "path": str(path),
        "engineering_only": payload.get("engineering_only") is True,
    }
    included = payload.get("included_categories")
    if isinstance(included, list):
        forbidden_tokens = (
            "account",
            "auth",
            "credential",
            "private",
            "raw",
            "repository",
            "wiki",
            "secret",
            "confidential",
            "unverified",
        )
        known_tokens = (
            "public",
            "verified",
            "prompt",
            "quest",
            "game",
            "state",
            "schema",
            "action",
            "rule",
            "ontology",
            "condition",
            "input",
            "output",
        )
        for category in included:
            normalized = str(category).casefold().replace("-", " ").replace("_", " ")
            if any(token in normalized for token in forbidden_tokens):
                receipt["status"] = "unresolved"
                receipt["reason"] = "included_forbidden_category"
                break
            if not any(token in normalized for token in known_tokens):
                receipt["status"] = "unresolved"
                receipt["reason"] = "included_category_unknown"
                break
    return receipt


def _load_transcript(path: Path, *, source_root: Path = ROOT) -> dict[str, Any]:
    transcript = _load_json(path, source_root=source_root)
    if transcript.get("schema_version") != "runtime-native-fixture-transcript/1":
        raise ValueError("fixture transcript schema mismatch")
    if transcript.get("host") not in {"codex", "claude_code", "antigravity"}:
        raise ValueError("fixture transcript host unsupported")
    if not isinstance(transcript.get("responses"), list) or not transcript["responses"]:
        raise ValueError("fixture transcript responses missing")
    return transcript


def _manifest_binding_reasons(
    context: Mapping[str, Any], source: Mapping[str, Any], inputs: Mapping[str, Any]
) -> list[str]:
    hashes = context.get("hashes") if isinstance(context.get("hashes"), Mapping) else {}
    bound_files = (
        context.get("bound_files") if isinstance(context.get("bound_files"), Mapping) else {}
    )
    reasons: list[str] = []
    for name, receipt, hash_key in (
        ("source_manifest", source, "source_manifest_sha256"),
        ("input_manifest", inputs, "input_manifest_sha256"),
    ):
        if receipt.get("status") != "verified":
            reasons.append(f"{name}_receipt_unverified")
        digest = receipt.get("sha256")
        if digest is None or digest != hashes.get(hash_key):
            reasons.append(f"{name}_receipt_hash_mismatch")
        binding = bound_files.get(name)
        if not isinstance(binding, Mapping) or binding.get("sha256") != digest:
            reasons.append(f"{name}_binding_mismatch")
    return reasons


def _plan(args: argparse.Namespace) -> dict[str, Any]:
    panel = _load_json(args.panel, source_root=args.source_root)["panel"] if args.panel else None
    return build_assignment_plan(
        quest_id=args.quest_id,
        seed=args.seed,
        source_manifest_sha256=args.source_manifest_sha256,
        input_manifest_sha256=args.input_manifest_sha256,
        panel=panel,
    )


_PRIVATE_PATH_SEGMENTS = {
    ".git",
    ".ssh",
    ".aws",
    ".config",
    ".gnupg",
    ".secrets",
    "credentials",
    "credential",
    "secrets",
    "secret",
}


def _bound_path(root: Path, value: Any, *, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label}_path_invalid")
    root = root.resolve()
    candidate = Path(value)
    try:
        if candidate.is_absolute():
            try:
                relative = candidate.relative_to(root)
            except ValueError:
                relative = candidate.resolve().relative_to(root)
        else:
            relative = candidate
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label}_path_escape") from exc
    resolved, error = _resolve_bound_path(root, str(relative))
    if error is not None or resolved is None:
        raise ValueError(f"{label}_{error or 'path_invalid'}")
    return resolved


def _bound_bytes(root: Path, binding: Any, *, label: str) -> bytes:
    if not isinstance(binding, Mapping):
        raise ValueError(f"{label}_binding_missing")  # noqa: TRY004 -- JSON validation contract.
    path = _bound_path(root, binding.get("path"), label=label)
    raw = _read_bound_bytes(path)
    if raw is None:
        raise ValueError(f"{label}_unreadable_or_oversized")
    if hashlib.sha256(raw).hexdigest() != binding.get("sha256"):
        raise ValueError(f"{label}_content_mismatch")
    return raw


def _load_bounded_json(path: Path, root: Path, *, label: str) -> dict[str, Any]:
    resolved = _bound_path(root, str(path), label=label)
    _raw, value = _bound_json_object(resolved, trust_root=root, label=label)
    return value


def _new_output_root(path: Path | None) -> Path:
    if path is None:
        raise ValueError("execution_requires_output_root")
    resolved = path.expanduser().resolve()
    if resolved.exists():
        raise ValueError("output_root_must_be_new")
    if any(part.casefold() in _PRIVATE_PATH_SEGMENTS for part in resolved.parts):
        raise ValueError("output_root_private_path_rejected")
    return resolved


def _native_scientific_summary(
    record: Mapping[str, Any], trust: NativeActivationTrust
) -> dict[str, Any]:
    summary = {"assigned": 1, "executed": 0, "eligible": True}
    supplied = record.get("scientific")
    if isinstance(supplied, Mapping):
        executed = supplied.get("executed")
        if type(executed) is int and executed in {0, 1}:
            summary["executed"] = executed
    evidence = record.get("evidence")
    receipts = evidence.get("prompt_receipts") if isinstance(evidence, Mapping) else None
    if isinstance(receipts, list):
        actual = 0
        for receipt in receipts:
            if not isinstance(receipt, Mapping):
                continue
            if (
                receipt.get("transport_kind") == "local_process"
                and receipt.get("local_process_started") is True
                and receipt.get("dispatch_started") is True
                and receipt.get("mode") in {"native", "production_native"}
                and receipt.get("activation_sha256") == trust.activation_sha256
                and receipt.get("plan_sha256") == trust.plan_sha256
                and receipt.get("row_id") == trust.row_id
            ):
                actual += 1
        summary["executed"] = 1 if actual else 0
    return summary


def _post_admission_failure(
    *,
    phase: str,
    exc: Exception,
    source: Mapping[str, Any],
    inputs: Mapping[str, Any],
    output_root: Path,
    record: Mapping[str, Any] | None = None,
    engine: Any = None,
    trusted_activation: NativeActivationTrust | None = None,
) -> dict[str, Any]:
    scientific: dict[str, Any] = {"assigned": 1, "executed": 0, "eligible": True}
    execution_evidence = "pre_dispatch"
    receipts = getattr(engine, "prompt_receipts", None)
    if isinstance(record, Mapping) and isinstance(trusted_activation, NativeActivationTrust):
        scientific = _native_scientific_summary(record, trusted_activation)
        execution_evidence = "finalized_record"
    elif phase in {"episode", "cleanup", "record"}:
        scientific["executed"] = None
        execution_evidence = "unknown"
        if isinstance(receipts, list) and isinstance(trusted_activation, NativeActivationTrust):
            observed = _native_scientific_summary(
                {"evidence": {"prompt_receipts": receipts}}, trusted_activation
            )
            if observed["executed"] == 1:
                scientific = observed
                execution_evidence = "observed_trust_bound_start"
    failure = {
        "kind": "native_post_admission_failure",
        "phase": phase,
        "error": f"{type(exc).__name__}:{exc}",
        "denominator": scientific,
        "execution_evidence": execution_evidence,
    }
    return {
        "status": "failure",
        "success": False,
        "failure_reason": f"native_{phase}_failed",
        "failure_artifact": failure,
        "scientific": scientific,
        "source": dict(source),
        "input": dict(inputs),
        "output_root": str(output_root),
        "episode_record": record,
        "observed_prompt_receipts": receipts if isinstance(receipts, list) else None,
    }


def _check(
    args: argparse.Namespace,
    *,
    trusted_activation: NativeActivationTrust | None = None,
) -> dict[str, Any]:
    context = _load_json(args.native_context, source_root=args.source_root)
    source = _manifest_receipt(args.source_manifest, kind="source", source_root=args.source_root)
    inputs = _manifest_receipt(args.input_manifest, kind="input", source_root=args.source_root)
    model = context.get("model") if isinstance(context.get("model"), Mapping) else {}
    config = {
        "assignment_id": context.get("assignment_id"),
        "study_id": context.get("study_id"),
        "model_selector": model.get("selector"),
        "representation": model.get("representation"),
        "effort": model.get("effort"),
    }
    admission = validate_native_context(
        context,
        model={
            "host": model.get("host"),
            "selector": model.get("selector"),
            "representation": model.get("representation"),
            "effort": model.get("effort"),
        },
        config=config,
        prompt=args.prompt,
        source_root=(
            trusted_activation.source_root
            if isinstance(trusted_activation, NativeActivationTrust)
            and context.get("execution_mode") == "native"
            else (args.source_root if context.get("execution_mode") == "native" else None)
        ),
        now=args.now,
        trusted_activation=trusted_activation,
    )
    manifest_reasons = _manifest_binding_reasons(context, source, inputs)
    if manifest_reasons:
        admission["reasons"] = list(
            dict.fromkeys([*admission.get("reasons", []), *manifest_reasons])
        )
        admission["ready"] = False
        admission["scientific_eligible"] = False
    return {
        "status": "ready" if admission.get("ready") else "blocked",
        "admission": admission,
        "source": source,
        "input": inputs,
        "scientific": {"assigned": 0, "executed": 0, "eligible": False},
    }


def _run_native(
    args: argparse.Namespace,
    *,
    trusted_activation: NativeActivationTrust,
) -> dict[str, Any]:
    if not isinstance(trusted_activation, NativeActivationTrust):
        raise ValueError("trusted_activation_invalid")  # noqa: TRY004 -- Canonical admission rejection.
    if trusted_activation.purpose != "production_native":
        raise ValueError("trusted_activation_invalid")
    if args.project is not None:
        raise ValueError("native_project_override_rejected")
    cap_root = Path(trusted_activation.source_root or "").resolve()
    if not cap_root.is_dir():
        raise ValueError("trusted_source_root_invalid")
    if ROOT.resolve() != cap_root:
        raise ValueError("runtime_source_root_mismatch")
    if args.source_root is None or Path(args.source_root).resolve() != cap_root:
        raise ValueError("source_root_mismatch")
    if args.native_context is None:
        raise ValueError("execution_requires_native_context")
    context = _load_bounded_json(args.native_context, cap_root, label="native_context")
    bindings = context.get("bound_files")
    if not isinstance(bindings, Mapping):
        raise ValueError("bindings_missing")  # noqa: TRY004 -- JSON validation contract.
    row = trusted_activation.row
    target = row.get("target") if isinstance(row, Mapping) else None
    activation = trusted_activation.activation
    artifact_bindings = (
        activation.get("artifact_bindings") if isinstance(activation, Mapping) else None
    )
    if not isinstance(target, Mapping) or not isinstance(artifact_bindings, Mapping):
        raise ValueError("trusted_activation_binding_invalid")  # noqa: TRY004 -- Canonical admission rejection.
    host = str(target["host"])
    selector = str(target["selector"])
    effort = str(target["effort"])
    representation = str(row["representation"])
    row_values = {
        "quest_id": row["quest_id"],
        "seed": row["seed"],
        "fixture_id": row["fixture_id"],
        "repeat": row["repeat"],
        "reset": row["reset"],
    }
    for name, supplied, expected in (
        ("quest", args.quest_id, row_values["quest_id"]),
        ("seed", args.seed, row_values["seed"]),
        ("fixture", args.fixture_ref, row_values["fixture_id"]),
    ):
        if supplied != expected:
            raise ValueError(f"trusted_row_{name}_mismatch")
    if args.fixture_transcript is not None or args.panel is not None:
        raise ValueError("native_fixture_override_rejected")
    prompt_bytes = _bound_bytes(cap_root, bindings.get("prompt"), label="prompt")
    try:
        prompt = prompt_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("prompt_not_utf8") from exc
    if args.prompt != prompt:
        raise ValueError("trusted_prompt_mismatch")
    hashes = {
        field: artifact_bindings.get(field)
        for field in (
            "approved_proposal_sha256",
            "source_manifest_sha256",
            "input_manifest_sha256",
            "prompt_sha256",
            "game_sha256",
            "ontology_sha256",
            "oracle_sha256",
            "output_schema_sha256",
            "allowed_requests_sha256",
        )
    }
    for field, supplied in (
        ("source_manifest_sha256", args.source_manifest_sha256),
        ("input_manifest_sha256", args.input_manifest_sha256),
    ):
        if supplied and supplied != hashes[field]:
            raise ValueError(f"trusted_{field}_mismatch")
    source_binding = bindings.get("source_manifest")
    input_binding = bindings.get("input_manifest")
    source_path = _bound_path(
        cap_root,
        source_binding.get("path") if isinstance(source_binding, Mapping) else None,
        label="source_manifest",
    )
    input_path = _bound_path(
        cap_root,
        input_binding.get("path") if isinstance(input_binding, Mapping) else None,
        label="input_manifest",
    )
    for label, supplied, expected in (
        ("source_manifest", args.source_manifest, source_path),
        ("input_manifest", args.input_manifest, input_path),
    ):
        if supplied is not None and Path(supplied).resolve() != expected:
            raise ValueError(f"{label}_override_rejected")
    source = _manifest_receipt(source_path, kind="source", source_root=cap_root)
    inputs = _manifest_receipt(input_path, kind="input", source_root=cap_root)
    manifest_reasons = _manifest_binding_reasons(context, source, inputs)
    if manifest_reasons:
        raise ValueError("manifest_binding_rejected:" + ",".join(manifest_reasons))
    config = {
        "assignment_id": row["assignment_id"],
        "study_id": activation.get("study_id"),
        "quest_id": row_values["quest_id"],
        "model_host": host,
        "model_selector": selector,
        "representation": representation,
        "effort": effort,
        "seed": row_values["seed"],
        "repeat": row_values["repeat"],
        "reset": row_values["reset"],
        "fixture_id": row_values["fixture_id"],
        "fixture_sha256": row["fixture_sha256"],
        **hashes,
        "allowed_requests": [
            dict(request) for request in artifact_bindings.get("allowed_requests", ())
        ],
        "scenario": row_values["quest_id"],
    }
    admission = validate_native_context(
        context,
        model={
            "host": host,
            "selector": selector,
            "representation": representation,
            "effort": effort,
            "offline": False,
        },
        config=config,
        prompt=prompt,
        source_root=cap_root,
        now=args.now,
        trusted_activation=trusted_activation,
    )
    if admission.get("ready") is not True or admission.get("scientific_eligible") is not True:
        reasons = ",".join(str(reason) for reason in admission.get("reasons", []))
        raise ValueError("native_context_rejected" + (f":{reasons}" if reasons else ""))
    output_root = _new_output_root(args.output_root)
    phase = "output"
    record: Mapping[str, Any] | None = None
    engine: GodotEpisodeEngine | None = None
    try:
        output_root.mkdir(parents=True, exist_ok=False)
        with tempfile.TemporaryDirectory(prefix="runtime-native-project-") as working:
            project = Path(working) / "project"
            phase = "stage"
            stage_project(cap_root / "game-track" / "godot", project)
            phase = "runner"
            runner = NativePromptRunner(
                host=host,
                selector=selector,
                effort=effort,
                native_context=context,
                trusted_activation=trusted_activation,
            )
            phase = "engine"
            engine = GodotEpisodeEngine(
                project=project,
                output_root=output_root,
                seed=row_values["seed"],
                assignment_id=str(row["assignment_id"]),
                prompt_runner=runner,
                engine_runner=run_godot,
                godot_binary=args.godot_binary
                or shutil.which("godot4")
                or shutil.which("godot")
                or "godot",
                fixture_ref=str(row_values["fixture_id"]),
            )
            phase = "episode"
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                repair_source=engine.repair,
                model=ModelSpec(
                    selector,
                    representation,
                    provider=host,
                    offline=False,
                ),
                limits=EpisodeLimits(),
                seed=row_values["seed"],
                clock=__import__("time").monotonic,
                config=config,
                prompt=prompt,
                native_context=context,
                trusted_activation=trusted_activation,
                output_path=output_root / "episode.json",
            )
            phase = "cleanup"
        phase = "record"
        if not isinstance(record, Mapping):
            raise TypeError("episode_record_object_required")
    except Exception as exc:  # noqa: BLE001 -- Preserve assigned failures from arbitrary engine transports.
        if isinstance(exc, EpisodePersistenceError):
            record = exc.record
        return _post_admission_failure(
            phase=phase,
            exc=exc,
            source=source,
            inputs=inputs,
            output_root=output_root,
            record=record,
            engine=engine,
            trusted_activation=trusted_activation,
        )
    scientific = _native_scientific_summary(record, trusted_activation)
    return {
        "status": record.get("status"),
        "success": record.get("success"),
        "engineering_status": record.get("engineering_status"),
        "failure_reason": record.get("failure_reason"),
        "scientific": scientific,
        "source": source,
        "input": inputs,
        "output_root": str(output_root),
        "record_hash": record.get("record_hash"),
        "accounting": {
            "assigned": scientific["assigned"],
            "executed": scientific["executed"],
            "eligible": scientific["eligible"],
            "provider_request_count": None,
        },
    }


def _fixture(
    args: argparse.Namespace,
    *,
    native: bool = False,
    trusted_activation: NativeActivationTrust | None = None,
) -> dict[str, Any]:
    context = _load_json(args.native_context, source_root=args.source_root)
    model_data = context.get("model")
    if args.output_root is None:
        raise ValueError("execution_requires_output_root")
    source_receipt = _manifest_receipt(
        args.source_manifest, kind="source", source_root=args.source_root
    )
    input_receipt = _manifest_receipt(
        args.input_manifest, kind="input", source_root=args.source_root
    )
    if not isinstance(model_data, Mapping):
        return {
            "status": "blocked",
            "reason": "model_missing",
            "scientific": {"assigned": 0, "executed": 0},
        }
    if context.get("execution_mode") != "engineering_fixture":
        return {
            "status": "blocked",
            "reason": "fixture_mode_requires_engineering_context",
            "scientific": {"assigned": 0, "executed": 0},
        }
    transcript = _load_transcript(args.fixture_transcript, source_root=args.source_root)
    if transcript.get("host") != str(model_data.get("host")):
        raise ValueError("fixture transcript host mismatch")
    manifest_reasons = _manifest_binding_reasons(context, source_receipt, input_receipt)
    if manifest_reasons:
        return {
            "status": "blocked",
            "reason": "manifest_binding_rejected",
            "reasons": manifest_reasons,
            "scientific": {"assigned": 0, "executed": 0, "eligible": False},
            "source": source_receipt,
            "input": input_receipt,
        }
    transport = TranscriptTransport(str(model_data["host"]), transcript)
    runner = NativePromptRunner(
        host=str(model_data["host"]),
        selector=str(model_data["selector"]),
        effort=str(model_data["effort"]),
        native_context=context,
        process_runner=transport,
    )
    config = {
        "scenario": args.quest_id,
        "goal": "harbor-signal-restored-authorized-tide-lead-v1",
        "assignment_id": str(context.get("assignment_id")),
        "study_id": context.get("study_id"),
        "model_selector": model_data.get("selector"),
        "representation": model_data.get("representation"),
        "effort": model_data.get("effort"),
    }
    args.output_root.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="runtime-native-project-") as working:
        project = Path(args.project).resolve() if args.project else Path(working) / "project"
        if args.project is None:
            stage_project(ROOT / "game-track" / "godot", project)
        engine = GodotEpisodeEngine(
            project=project,
            output_root=args.output_root,
            seed=args.seed,
            assignment_id=str(context.get("assignment_id")),
            prompt_runner=runner,
            engine_runner=run_godot,
            godot_binary=args.godot_binary
            or shutil.which("godot4")
            or shutil.which("godot")
            or "godot",
            fixture_ref=args.fixture_ref,
        )
        record = run_episode(
            engine=engine,
            proposal_source=engine.propose,
            repair_source=engine.repair,
            model=ModelSpec(
                str(model_data["selector"]),
                str(model_data["representation"]),
                provider=str(model_data["host"]),
                offline=False,
            ),
            limits=EpisodeLimits(),
            seed=args.seed,
            clock=__import__("time").monotonic,
            config=config,
            prompt=args.prompt,
            native_context=context,
            output_path=args.output_root / "episode.json",
        )
    return {
        "status": record.get("status"),
        "success": record.get("success"),
        "engineering_status": record.get("engineering_status"),
        "failure_reason": record.get("failure_reason"),
        "scientific": {"assigned": 0, "executed": 0, "eligible": False},
        "source": source_receipt,
        "input": input_receipt,
        "output_root": str(args.output_root),
        "transcript_calls": len(transport.calls),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--plan", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--engineering-fixture", action="store_true")
    modes.add_argument("--native", action="store_true")
    parser.add_argument("--native-context", type=Path)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--input-manifest", type=Path)
    parser.add_argument("--fixture-transcript", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--panel", type=Path)
    parser.add_argument("--quest-id", default="sealed-lighthouse-v1")
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--source-manifest-sha256", default="")
    parser.add_argument("--input-manifest-sha256", default="")
    parser.add_argument(
        "--prompt", default="Restore the lighthouse signal and reveal the authorized tide lead."
    )
    parser.add_argument("--now")
    parser.add_argument("--project", type=Path)
    parser.add_argument("--godot-binary")
    parser.add_argument(
        "--fixture-ref",
        default="data/fixtures/npc-goal-recovery/validated-v2/engineering.json#ENG-S01",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    *,
    trusted_activation: NativeActivationTrust | None = None,
) -> int:
    args = parse_args(argv)
    try:
        if args.native:
            if not isinstance(trusted_activation, NativeActivationTrust):
                raise ValueError("trusted_activation_missing")
            if trusted_activation.purpose != "production_native":
                raise ValueError("trusted_activation_invalid")
            if args.native_context is None:
                raise ValueError("execution_requires_native_context")
            result = _run_native(args, trusted_activation=trusted_activation)
        elif args.plan:
            if not args.source_manifest_sha256 or not args.input_manifest_sha256:
                raise ValueError("plan_requires_source_and_input_manifest_hashes")
            result = _plan(args)
        elif args.check_only:
            if args.native_context is None:
                raise ValueError("check_only_requires_native_context")
            result = _check(args, trusted_activation=trusted_activation)
        elif args.engineering_fixture:
            if args.native_context is None:
                raise ValueError("execution_requires_native_context")
            if args.fixture_transcript is None:
                raise ValueError("engineering_fixture_requires_transcript")
            result = _fixture(args)
        else:
            raise ValueError("explicit_execution_mode_required")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        engineering_pass = (
            result.get("success") is True
            and str(result.get("engineering_status", "")).upper() == "PASS"
        )
        planned_or_ready = result.get("status") in {"planned", "ready"}
        scientific_success = (
            result.get("scientific", {}).get("executed") == 1
            and result.get("scientific", {}).get("eligible") is True
            and result.get("success") is True
        )
        return 0 if planned_or_ready or engineering_pass or scientific_success else 2
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "status": "blocked",
                    "failure_reason": f"{type(exc).__name__}:{exc}",
                    "scientific": {"assigned": 0, "executed": 0, "eligible": False},
                },
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
