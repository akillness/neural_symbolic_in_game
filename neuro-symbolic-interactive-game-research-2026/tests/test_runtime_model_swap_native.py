from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from collections.abc import Iterator, Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_runtime_model_swap as offline_cli
import run_runtime_model_swap_native as native_cli
from codex_oauth_llm import TOOL_POLICY_FEATURES

from nesy_game import runtime_model_swap_native as native_runtime
from nesy_game.runtime_model_swap import (
    EpisodeLimits,
    GodotEpisodeEngine,
    ModelSpec,
    run_episode,
)
from nesy_game.runtime_model_swap_native import (
    ACTIVATION_SCHEMA,
    ASSIGNMENT_PLAN_SCHEMA,
    EXTENSION_ACTIVATION_SCHEMA,
    EXTENSION_ASSIGNMENT_PLAN_SCHEMA,
    EXTENSION_CODEX_CATALOG_SHA256,
    EXTENSION_CODEX_CLI_VERSION,
    EXTENSION_CODEX_IDENTITY_SOURCE,
    EXTENSION_CODEX_TARGETS,
    EXTENSION_IDENTITY_POLICY,
    MAX_BOUND_FILE_BYTES,
    NativeActivationTrust,
    NativePromptResult,
    NativePromptRunner,
    PromptTransportError,
    build_assignment_plan,
    build_extension_assignment_plan,
    load_pinned_native_activation,
    parse_codex_provider_identity,
    run_host_process,
    validate_native_context,
)

PROPOSAL_SHA = "a" * 64
SOURCE_SHA = "b" * 64
INPUT_SHA = "c" * 64
PROMPT_SHA = "d" * 64
GAME_SHA = "e" * 64
ONTOLOGY_SHA = "f" * 64
ORACLE_SHA = "1" * 64

_CODEX_ORIGINAL_EXTRACT_PATH = (
    ROOT
    / "research/runtime-model-swap-20261024/codex-live-20261026/public-packet-v1"
    / "codex-sol-models-original-extract.json"
)
_CODEX_PROVENANCE_PATH = (
    ROOT
    / "research/runtime-model-swap-20261024/codex-live-20261026/public-packet-v1"
    / "codex-no-tools-catalog-provenance.json"
)
_CODEX_DERIVED_CATALOG_PATH = ROOT / "src/nesy_game/codex_no_tools_models.json"
_CODEX_DERIVED_CATALOG_SHA256 = "5293550d74b5ceea7e3c528799fe8a992cbcd215ea326516c4a1bc011c035d36"
_CODEX_ALLOWED_TOOL_FIELD_REPLACEMENTS = {
    "apply_patch_tool_type": None,
    "experimental_supported_tools": [],
    "tool_mode": "direct",
    "multi_agent_version": None,
}
_CODEX_REQUIRED_ADDITIONAL_DISABLES = {
    "code_mode",
    "code_mode_only",
    "code_mode_tool_search",
    "multi_agent",
    "multi_agent_v2",
    "sleep_tool",
    "token_budget",
    "current_time_reminder",
    "request_permissions_tool",
    "deferred_executor",
    "send_message_to_user_async",
    "standalone_web_search",
    "plugins",
    "goals",
    "hooks",
}


_ORIGINAL_NATIVE_NOW_VALUE = native_runtime._now_value


def setUpModule() -> None:
    def stable_now(value: Any = None) -> Any:
        if value is None:
            value = "2026-10-25T12:00:00Z"
        return _ORIGINAL_NATIVE_NOW_VALUE(value)

    clock_patcher = patch.object(native_runtime, "_now_value", side_effect=stable_now)
    clock_patcher.start()
    unittest.addModuleCleanup(clock_patcher.stop)


class _CountingTransport:
    def __init__(
        self, *, stdout: str = "", returncode: int = 0, error: BaseException | None = None
    ) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"command": list(command), **kwargs})
        if self.error is not None:
            raise self.error
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, "fixture stderr")


class _HostFixtureTransport:
    def __init__(self, host: str, payload: dict[str, Any]) -> None:
        self.host = host
        self.payload = payload
        self.calls: list[dict[str, Any]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"command": list(command), **kwargs})
        command = list(command)
        if self.host == "codex":
            output_flag = command.index("--output-last-message")
            Path(command[output_flag + 1]).write_text(
                json.dumps(self.payload, ensure_ascii=False), encoding="utf-8"
            )
            stdout = "\n".join(
                [
                    json.dumps({"type": "thread.started", "thread_id": "fixture-thread"}),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps(self.payload, ensure_ascii=False),
                            },
                        }
                    ),
                ]
            )
        elif self.host == "claude_code":
            stdout = json.dumps(
                {
                    "type": "result",
                    "structured_output": self.payload,
                    "modelUsage": {"inputTokens": 11, "outputTokens": 7},
                }
            )
        else:
            stdout = json.dumps(
                {
                    "status": "completed",
                    "response": self.payload,
                    "usage": {"input_tokens": 11, "output_tokens": 7},
                }
            )
        return subprocess.CompletedProcess(command, 0, stdout, "")


class _SimpleEngine:
    def __init__(self) -> None:
        self.value = 0
        self.commits: list[dict[str, Any]] = []

    def state(self) -> dict[str, Any]:
        return {"value": self.value}

    def legal_actions(self) -> list[str]:
        return ["finish"] if self.value == 0 else []

    def preconditions(self) -> dict[str, Any]:
        return {"finish": ["value=0"]}

    def constraints(self) -> list[str]:
        return ["value_monotonic"]

    def objective(self) -> str:
        return "value_is_one"

    def validate(self, proposal: dict[str, Any]) -> dict[str, Any]:
        return {"valid": proposal.get("action") == "finish", "code": None}

    def commit(self, proposal: dict[str, Any]) -> dict[str, Any]:
        self.commits.append(dict(proposal))
        self.value = 1
        return self.state()

    def objective_reached(self) -> bool:
        return self.value == 1


def _native_context(
    *,
    host: str = "codex",
    selector: str = "gpt-6.1-sol",
    representation: str = "general_rule",
    now: str = "2026-10-25T12:00:00Z",
    expires_at: str = "2026-10-26T00:00:00Z",
    mode: str = "engineering_fixture",
) -> dict[str, Any]:
    return {
        "schema_version": "runtime-native-context/1",
        "study_id": "runtime-model-swap-20261024",
        "assignment_id": "prep-quest-001",
        "execution_mode": mode,
        "model": {
            "host": host,
            "selector": selector,
            "representation": representation,
            "effort": "medium",
            "revision": "fixture-revision-001",
        },
        "hashes": {
            "approved_proposal_sha256": PROPOSAL_SHA,
            "source_manifest_sha256": SOURCE_SHA,
            "input_manifest_sha256": INPUT_SHA,
            "prompt_sha256": PROMPT_SHA,
            "game_sha256": GAME_SHA,
            "ontology_sha256": ONTOLOGY_SHA,
            "oracle_sha256": ORACLE_SHA,
        },
        "bound_files": {
            "approved_proposal": {
                "path": "research/pilot-native-preparation-proposal-v1.json",
                "sha256": PROPOSAL_SHA,
            },
            "source_manifest": {
                "path": "research/native-source-manifest.json",
                "sha256": SOURCE_SHA,
            },
            "input_manifest": {
                "path": "research/public-minimal-input-manifest.json",
                "sha256": INPUT_SHA,
            },
            "prompt": {"path": "research/prompt.txt", "sha256": PROMPT_SHA},
            "game": {"path": "game-track/godot/project.godot", "sha256": GAME_SHA},
            "ontology": {"path": "research/ontology.json", "sha256": ONTOLOGY_SHA},
            "oracle": {"path": "research/oracle.json", "sha256": ORACLE_SHA},
        },
        "expires_at": expires_at,
        "authority": {
            "native_activation": True,
            "public_input_egress": True,
            "identity_setting_verified": True,
            "context_isolation_verified": True,
            "subscription_no_additional_charge_verified": True,
            "research_context_transmission": False,
            "scientific_launch": False,
        },
        "evidence": {
            "public_input": {"status": "verified", "receipt": "public-input-receipt-001"},
            "identity_setting": {
                "status": "verified",
                "host": host,
                "selector": selector,
                "effort": "medium",
                "revision": "fixture-revision-001",
            },
            "context_isolation": {
                "status": "verified",
                "tools": "none",
                "workspace": "temporary",
            },
            "subscription": {
                "status": "verified",
                "no_additional_charge": True,
                "billing_source": "existing-subscription-receipt",
            },
        },
        # This field is deliberately non-authoritative.  A caller cannot self-certify readiness.
        "ready": True,
    }


def _native_source_bound_context(
    tmp_path: Path, *, host: str = "codex", selector: str = "gpt-6.1-sol"
) -> dict[str, Any]:
    context = _native_context(host=host, selector=selector, mode="native")
    if host == "antigravity":
        context["model"]["approved_agent"] = "fixture-agent"
        context["evidence"]["identity_setting"]["approved_agent"] = "fixture-agent"
    context["authority"].update(research_context_transmission=True, scientific_launch=True)
    allowed_requests = [
        {
            "instruction_sha256": hashlib.sha256(b"fixture prompt").hexdigest(),
            "user_prompt_sha256": hashlib.sha256(b"fixture prompt").hexdigest(),
            "output_schema_sha256": "0" * 64,
        }
    ]
    allowed_requests_sha256 = hashlib.sha256(_canonical_bytes(allowed_requests)).hexdigest()
    context["evidence"]["public_input"]["allowed_requests_sha256"] = allowed_requests_sha256

    bound_root = tmp_path / "bound"
    receipt_root = tmp_path / "receipts"
    bound_root.mkdir()
    receipt_root.mkdir()

    def write_bytes(relative: Path, payload: bytes) -> str:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return hashlib.sha256(payload).hexdigest()

    def write_json(relative: Path, payload: Mapping[str, Any]) -> str:
        return write_bytes(
            relative, json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )

    source_fixture = Path("bound") / "source-fixture.gd"
    source_fixture_sha = write_bytes(source_fixture, b"source-bound synthetic controller\n")
    input_fixture = Path("bound") / "public-input.txt"
    input_fixture_sha = write_bytes(input_fixture, b"source-bound synthetic public input\n")
    source_manifest = Path("bound") / "source_manifest.json"
    input_manifest = Path("bound") / "input_manifest.json"
    approved_proposal = Path("bound") / "approved_proposal.json"
    prompt = Path("bound") / "prompt.txt"
    game = Path("bound") / "game.godot"
    ontology = Path("bound") / "ontology.json"
    oracle = Path("bound") / "oracle.json"

    source_manifest_sha = write_json(
        source_manifest,
        {
            "schema_version": "runtime-native-source-manifest/1",
            "files": [
                {
                    "path": source_fixture.as_posix(),
                    "sha256": source_fixture_sha,
                    "role": "controller",
                }
            ],
        },
    )
    input_manifest_sha = write_json(
        input_manifest,
        {
            "schema_version": "runtime-native-input-manifest/1",
            "files": [
                {
                    "path": input_fixture.as_posix(),
                    "sha256": input_fixture_sha,
                    "role": "public_prompt",
                }
            ],
        },
    )
    bound_payloads = {
        "approved_proposal": (
            approved_proposal,
            {
                "kind": "source-bound synthetic approved proposal",
                "assignment_id": context["assignment_id"],
            },
        ),
        "prompt": (prompt, b"source-bound synthetic prompt\n"),
        "game": (game, b"source-bound synthetic game\n"),
        "ontology": (ontology, {"kind": "source-bound synthetic ontology"}),
        "oracle": (oracle, {"kind": "source-bound synthetic oracle"}),
    }
    bound_digests = {
        "source_manifest": (source_manifest, source_manifest_sha),
        "input_manifest": (input_manifest, input_manifest_sha),
    }
    for name, (relative, payload) in bound_payloads.items():
        digest = write_bytes(
            relative,
            payload
            if isinstance(payload, bytes)
            else json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )
        bound_digests[name] = (relative, digest)

    fields = {
        "approved_proposal_sha256": "approved_proposal",
        "source_manifest_sha256": "source_manifest",
        "input_manifest_sha256": "input_manifest",
        "prompt_sha256": "prompt",
        "game_sha256": "game",
        "ontology_sha256": "ontology",
        "oracle_sha256": "oracle",
    }
    for hash_field, bound_name in fields.items():
        relative, digest = bound_digests[bound_name]
        context["hashes"][hash_field] = digest
        context["bound_files"][bound_name] = {"path": relative.as_posix(), "sha256": digest}

    def artifact(name: str, **extra: Any) -> dict[str, str]:
        relative = Path("receipts") / f"{name}.json"
        body: dict[str, Any] = {
            "kind": "runtime-native-evidence/1",
            "evidence": name,
            "label": f"source-bound synthetic {name}",
            "status": "verified",
            "source_bound": True,
            "study_id": context["study_id"],
            "assignment_id": context["assignment_id"],
            "host": context["model"]["host"],
            "model_selector": context["model"]["selector"],
            "representation": context["model"]["representation"],
            "model_revision": context["model"]["revision"],
            "effort": context["model"]["effort"],
            "source_manifest_sha256": context["hashes"]["source_manifest_sha256"],
            "input_manifest_sha256": context["hashes"]["input_manifest_sha256"],
            "authority": dict(context["authority"]),
            "permissions": {
                "read": True,
                "write": False,
                "network": False,
                "generation": True,
                "egress": True,
            },
        }
        if host == "antigravity":
            body["approved_agent"] = "fixture-agent"
        body.update(extra)
        payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        digest = write_bytes(relative, payload)
        return {"path": relative.as_posix(), "sha256": digest}

    evidence = context["evidence"]
    evidence["public_input"].update(
        source_bound=True,
        allowed_requests_sha256=allowed_requests_sha256,
        receipt_artifact=artifact("public_input", allowed_requests_sha256=allowed_requests_sha256),
    )
    evidence["identity_setting"].update(
        source_bound=True,
        receipt_artifact=artifact(
            "identity_setting", host=host, selector=selector, effort="medium"
        ),
    )
    evidence["context_isolation"].update(
        source_bound=True,
        receipt_artifact=artifact("context_isolation", tools="none", workspace="temporary"),
    )
    evidence["subscription"].update(
        source_bound=True,
        receipt_artifact=artifact(
            "subscription",
            no_additional_charge=True,
            billing_source="existing-subscription-receipt",
        ),
    )
    evidence["activation"] = {
        "status": "verified",
        "source_bound": True,
        "receipt_artifact": artifact("activation"),
    }
    if host == "antigravity":
        evidence["effective_tool_context"] = {
            "status": "verified",
            "source_bound": True,
            "tools": "none",
            "workspace": "temporary",
            "receipt_artifact": artifact(
                "effective-isolation", tools="none", workspace="temporary"
            ),
        }
    return context


def _rebind_native_evidence(
    root: Path,
    context: dict[str, Any],
    *,
    source_manifest_sha256: str | None = None,
    input_manifest_sha256: str | None = None,
    evidence_name: str | None = None,
) -> None:
    evidence = context["evidence"]
    for name, receipt in evidence.items():
        if evidence_name is not None and name != evidence_name:
            continue
        if not isinstance(receipt, dict):
            continue
        descriptor = receipt.get("receipt_artifact")
        if not isinstance(descriptor, dict):
            continue
        path = root / descriptor["path"]
        body = json.loads(path.read_text(encoding="utf-8"))
        if source_manifest_sha256 is not None:
            body["source_manifest_sha256"] = source_manifest_sha256
        if input_manifest_sha256 is not None:
            body["input_manifest_sha256"] = input_manifest_sha256
        payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        path.write_bytes(payload)
        descriptor["sha256"] = hashlib.sha256(payload).hexdigest()


def _project_root_native_context(tmp_path: Path) -> dict[str, Any]:
    context = _native_source_bound_context(tmp_path)
    prefix = tmp_path.name
    for binding in context["bound_files"].values():
        binding["path"] = f"{prefix}/{binding['path']}"
    for receipt in context["evidence"].values():
        if isinstance(receipt, dict) and isinstance(receipt.get("receipt_artifact"), dict):
            receipt["receipt_artifact"]["path"] = f"{prefix}/{receipt['receipt_artifact']['path']}"
    return context


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _simulation_bundle(
    root: Path,
    *,
    manifest_mutation: str | None = None,
    extension: bool = False,
) -> dict[str, Any]:
    """Create separate source/trust roots with a bounded exact-request capability."""

    root.mkdir(parents=True, exist_ok=True)
    source_root = root / "source"
    trust_root = root / "trust"
    source_root.mkdir()
    trust_root.mkdir()
    written: dict[str, tuple[Path, str]] = {}

    def write(relative: str, value: Any, *, raw: bool = False, base: Path = source_root) -> str:
        path = base / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = value if raw else _canonical_bytes(value)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        path.write_bytes(payload)
        digest = hashlib.sha256(payload).hexdigest()
        written[f"{base.name}/{relative}"] = (path, digest)
        return digest

    source_leaf = write("bound/public-controller.gd", b"controller fixture\n", raw=True)
    input_leaf = write("bound/public-prompt.txt", b"fixture prompt", raw=True)
    source_manifest_payload: dict[str, Any] = {
        "schema_version": "runtime-native-source-manifest/1",
        "synthetic": False,
        "engineering_only": False,
        "publicity": {"status": "verified", "actual_publicity": "verified_public"},
        "files": [
            {"path": "bound/public-controller.gd", "sha256": source_leaf, "role": "controller"}
        ],
    }
    input_manifest_payload: dict[str, Any] = {
        "schema_version": "runtime-native-input-manifest/1",
        "synthetic": False,
        "engineering_only": False,
        "publicity": {"status": "verified", "actual_publicity": "verified_public"},
        "files": [
            {"path": "bound/public-prompt.txt", "sha256": input_leaf, "role": "public_prompt"}
        ],
    }
    if manifest_mutation == "synthetic":
        source_manifest_payload["synthetic"] = True
    elif manifest_mutation == "engineering_only":
        source_manifest_payload["engineering_only"] = True
    elif manifest_mutation == "unresolved_publicity":
        source_manifest_payload["publicity"]["actual_publicity"] = "UNRESOLVED"
    elif manifest_mutation == "private_role":
        source_manifest_payload["files"][0]["role"] = "private_input"
    elif manifest_mutation == "private_path":
        source_manifest_payload["files"][0]["path"] = "private/controller.gd"
    elif manifest_mutation == "nested_manifest":
        nested = {"schema_version": "runtime-native-source-manifest/1", "files": []}
        nested_sha = write("bound/nested.json", nested)
        source_manifest_payload["files"].append(
            {"path": "bound/nested.json", "sha256": nested_sha, "role": "manifest"}
        )

    source_manifest_sha = write("bound/source_manifest.json", source_manifest_payload)
    input_manifest_sha = write("bound/input_manifest.json", input_manifest_payload)
    bound_payloads = {
        "approved_proposal": ("bound/approved-proposal.json", {"kind": "approved-proposal"}),
        "prompt": ("bound/prompt.txt", "fixture prompt", True),
        "game": ("bound/game.godot", "fixture game", True),
        "ontology": ("bound/ontology.json", {"kind": "ontology"}),
        "oracle": ("bound/oracle.json", {"kind": "oracle"}),
        "output_schema": ("bound/output-schema.json", {"type": "object"}),
        "fixture": ("bound/fixture.json", {"fixture": "sealed-lighthouse"}),
    }
    for values in bound_payloads.values():
        relative, value, *raw = values
        write(relative, value, raw=bool(raw and raw[0]))

    context = _native_context(
        host="codex",
        selector="gpt-6-luna" if extension else "gpt-6.1-sol",
        mode="native",
    )
    context["study_id"] = "runtime-model-swap-20261024"
    context["authority"].update(research_context_transmission=True, scientific_launch=True)
    context["model"]["revision"] = "fixture-revision-001"
    plan_builder = build_extension_assignment_plan if extension else build_assignment_plan
    plan = plan_builder(
        quest_id="sealed-lighthouse-v1",
        seed=20261024,
        source_manifest_sha256=source_manifest_sha,
        input_manifest_sha256=input_manifest_sha,
    )
    fixture_sha = written["source/bound/fixture.json"][1]
    oracle_sha = written["source/bound/oracle.json"][1]
    for row in plan["rows"]:
        row.update(
            fixture_id="fixture:sealed-lighthouse",
            fixture_sha256=fixture_sha,
            oracle_sha256=oracle_sha,
        )
    plan_bytes = _canonical_bytes(plan)
    plan_path = trust_root / "assignment-plan.json"
    plan_path.write_bytes(plan_bytes)
    plan_sha = hashlib.sha256(plan_bytes).hexdigest()
    selected = plan["rows"][0]
    context["assignment_id"] = selected["assignment_id"]
    context["model"].update(
        host=selected["target"]["host"],
        selector=selected["target"]["selector"],
        effort=selected["target"]["effort"],
        representation=selected["representation"],
    )
    fields = {
        "approved_proposal_sha256": "approved_proposal",
        "source_manifest_sha256": "source_manifest",
        "input_manifest_sha256": "input_manifest",
        "prompt_sha256": "prompt",
        "game_sha256": "game",
        "ontology_sha256": "ontology",
        "oracle_sha256": "oracle",
    }
    source_names = {
        "approved_proposal": "approved-proposal.json",
        "prompt": "prompt.txt",
        "game": "game.godot",
        "ontology": "ontology.json",
        "oracle": "oracle.json",
    }
    for hash_field, name in fields.items():
        if name == "source_manifest":
            digest = source_manifest_sha
        elif name == "input_manifest":
            digest = input_manifest_sha
        else:
            digest = written[f"source/bound/{source_names[name]}"][1]
        context["hashes"][hash_field] = digest
        context["bound_files"][name] = {
            "path": f"bound/{source_names.get(name, name + '.json')}",
            "sha256": digest,
        }

    def evidence_artifact(name: str, **extra: Any) -> dict[str, str]:
        body = {
            "kind": "runtime-native-evidence/1",
            "evidence": name,
            "status": "verified",
            "source_bound": True,
            "study_id": context["study_id"],
            "assignment_id": context["assignment_id"],
            "host": context["model"]["host"],
            "model_selector": context["model"]["selector"],
            "representation": context["model"]["representation"],
            "model_revision": context["model"]["revision"],
            "effort": context["model"]["effort"],
            "source_manifest_sha256": source_manifest_sha,
            "input_manifest_sha256": input_manifest_sha,
            "authority": dict(context["authority"]),
            "permissions": {"generation": True, "egress": True},
        }
        body.update(extra)
        relative = f"receipts/{name}.json"
        digest = write(relative, body)
        return {"path": relative, "sha256": digest}

    allowed_requests = [
        {
            "instruction_sha256": hashlib.sha256(b"fixture prompt").hexdigest(),
            "user_prompt_sha256": hashlib.sha256(b"fixture prompt").hexdigest(),
            "output_schema_sha256": written["source/bound/output-schema.json"][1],
        },
        {
            "instruction_sha256": hashlib.sha256(b"fixture prompt second").hexdigest(),
            "user_prompt_sha256": hashlib.sha256(b"fixture prompt second").hexdigest(),
            "output_schema_sha256": written["source/bound/output-schema.json"][1],
        },
    ]
    allowed_requests.sort(
        key=lambda item: (
            item["instruction_sha256"],
            item["user_prompt_sha256"],
            item["output_schema_sha256"],
        )
    )
    allowed_requests_sha = hashlib.sha256(_canonical_bytes(allowed_requests)).hexdigest()
    context["evidence"]["public_input"].update(
        source_bound=True,
        allowed_requests_sha256=allowed_requests_sha,
        receipt_artifact=evidence_artifact(
            "public_input", allowed_requests_sha256=allowed_requests_sha
        ),
    )
    context["evidence"]["identity_setting"].update(
        source_bound=True, receipt_artifact=evidence_artifact("identity_setting")
    )
    context["evidence"]["context_isolation"].update(
        source_bound=True,
        receipt_artifact=evidence_artifact(
            "context_isolation", tools="none", workspace="temporary"
        ),
    )
    context["evidence"]["subscription"].update(
        source_bound=True,
        receipt_artifact=evidence_artifact("subscription", no_additional_charge=True),
    )
    context["evidence"]["activation"] = {
        "status": "verified",
        "source_bound": True,
        "receipt_artifact": evidence_artifact("activation"),
    }
    artifact_bindings = dict(context["hashes"])
    artifact_bindings.update(
        output_schema_sha256=written["source/bound/output-schema.json"][1],
        allowed_requests=allowed_requests,
        allowed_requests_sha256=allowed_requests_sha,
    )
    if extension:
        artifact_bindings["extension_catalog_sha256"] = EXTENSION_CODEX_CATALOG_SHA256
    evidence_digests = {
        f"{name}_receipt_sha256": context["evidence"][name]["receipt_artifact"]["sha256"]
        for name in ("public_input", "identity_setting", "context_isolation", "subscription")
    }
    activation = {
        "schema_version": EXTENSION_ACTIVATION_SCHEMA if extension else ACTIVATION_SCHEMA,
        **({"identity_policy": EXTENSION_IDENTITY_POLICY} if extension else {}),
        "kind": "human_approved_native_launch",
        "activation_id": "activation-fixture-001",
        "study_id": context["study_id"],
        "expires_at": "2026-10-26T00:00:00Z",
        "permissions": {
            "native_launch": True,
            "research_context_transmission": True,
            "scientific_assignment": True,
            "generation": True,
            "egress": True,
            "no_additional_charge_verified": True,
        },
        "plan": {
            "schema_version": EXTENSION_ASSIGNMENT_PLAN_SCHEMA
            if extension
            else ASSIGNMENT_PLAN_SCHEMA,
            "sha256": plan_sha,
            "row_id": selected["planned_id"],
            "row_sha256": hashlib.sha256(_canonical_bytes(selected)).hexdigest(),
        },
        "row_binding": {
            "assignment_id": selected["assignment_id"],
            "quest_id": selected["quest_id"],
            "host": selected["target"]["host"],
            "selector": selected["target"]["selector"],
            "effort": selected["target"]["effort"],
            "representation": selected["representation"],
            "repeat": selected["repeat"],
            "seed": selected["seed"],
            "reset": selected["reset"],
            "fixture_id": selected["fixture_id"],
            "fixture_sha256": selected["fixture_sha256"],
            "oracle_sha256": context["hashes"]["oracle_sha256"],
        },
        "artifact_bindings": artifact_bindings,
        "evidence_digests": evidence_digests,
    }
    activation_path = trust_root / "activation.json"
    activation_bytes = _canonical_bytes(activation)
    activation_path.write_bytes(activation_bytes)
    activation_sha = hashlib.sha256(activation_bytes).hexdigest()
    capability = load_pinned_native_activation(
        activation_path=activation_path,
        activation_sha256=activation_sha,
        plan_path=plan_path,
        plan_sha256=plan_sha,
        row_id=selected["planned_id"],
        purpose="test_simulation",
        trust_root=trust_root,
        source_root=source_root,
    )
    return {
        "root": root,
        "source_root": source_root,
        "trust_root": trust_root,
        "context": context,
        "plan": plan,
        "row": selected,
        "activation": activation,
        "activation_path": activation_path,
        "activation_sha256": activation_sha,
        "plan_path": plan_path,
        "plan_sha256": plan_sha,
        "capability": capability,
        "allowed_requests": allowed_requests,
        "allowed_requests_sha256": allowed_requests_sha,
    }


def _model(context: dict[str, Any]) -> dict[str, str]:
    model = context["model"]
    return {
        "host": model["host"],
        "selector": model["selector"],
        "representation": model["representation"],
        "effort": model["effort"],
    }


def _simulation_config(bundle: dict[str, Any]) -> dict[str, Any]:
    context = bundle["context"]
    hashes = context["hashes"]
    return {
        "assignment_id": context["assignment_id"],
        "study_id": context["study_id"],
        "quest_id": bundle["row"]["quest_id"],
        "model_selector": context["model"]["selector"],
        "representation": context["model"]["representation"],
        "effort": context["model"]["effort"],
        **{
            field: hashes[field]
            for field in (
                "approved_proposal_sha256",
                "source_manifest_sha256",
                "input_manifest_sha256",
                "prompt_sha256",
                "game_sha256",
                "ontology_sha256",
                "oracle_sha256",
            )
        },
        "output_schema_sha256": bundle["activation"]["artifact_bindings"]["output_schema_sha256"],
        "allowed_requests_sha256": bundle["activation"]["artifact_bindings"][
            "allowed_requests_sha256"
        ],
    }


_EXISTING_CREDIT_POLICY = "existing_credits_no_new_purchase"
_CREDIT_POLICY_FIELDS = {
    "existing_credit_consumption_authorized": True,
    "automatic_reload_off_verified": True,
    "native_account_match_verified": True,
    "new_credit_purchase_authorized": False,
    "api_key_fallback_authorized": False,
}


def _apply_existing_credit_policy(bundle: dict[str, Any]) -> dict[str, Any]:
    context = bundle["context"]
    activation = bundle["activation"]
    context["billing_policy"] = _EXISTING_CREDIT_POLICY
    activation["billing_policy"] = _EXISTING_CREDIT_POLICY
    activation["permissions"].update(
        no_additional_charge_verified=False,
        **_CREDIT_POLICY_FIELDS,
    )
    context["authority"].update(
        subscription_no_additional_charge_verified=False,
        **_CREDIT_POLICY_FIELDS,
    )
    subscription = context["evidence"]["subscription"]
    subscription.update(
        billing_policy=_EXISTING_CREDIT_POLICY,
        no_additional_charge=False,
        **_CREDIT_POLICY_FIELDS,
    )
    receipt = subscription["receipt_artifact"]
    receipt_path = bundle["source_root"] / receipt["path"]
    body = json.loads(receipt_path.read_text(encoding="utf-8"))
    body.update(
        billing_policy=_EXISTING_CREDIT_POLICY,
        no_additional_charge=False,
        **_CREDIT_POLICY_FIELDS,
    )
    body["authority"] = dict(context["authority"])
    body["permissions"] = {**body.get("permissions", {}), **_CREDIT_POLICY_FIELDS}
    for evidence in context["evidence"].values():
        descriptor = evidence.get("receipt_artifact") if isinstance(evidence, Mapping) else None
        if not isinstance(descriptor, Mapping):
            continue
        evidence_path = bundle["source_root"] / descriptor["path"]
        evidence_body = json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence is subscription:
            evidence_body = body
        evidence_body["authority"] = dict(context["authority"])
        if evidence is subscription:
            evidence_body["permissions"] = {
                **evidence_body.get("permissions", {}),
                **_CREDIT_POLICY_FIELDS,
            }
        evidence_path.write_bytes(_canonical_bytes(evidence_body))
    _rebind_native_evidence(bundle["source_root"], context)
    for evidence_name in ("public_input", "identity_setting", "context_isolation", "subscription"):
        activation["evidence_digests"][f"{evidence_name}_receipt_sha256"] = context["evidence"][
            evidence_name
        ]["receipt_artifact"]["sha256"]
    return bundle


def _reload_pinned_activation(bundle: dict[str, Any]) -> dict[str, Any]:
    activation_bytes = _canonical_bytes(bundle["activation"])
    bundle["activation_path"].write_bytes(activation_bytes)
    bundle["activation_sha256"] = hashlib.sha256(activation_bytes).hexdigest()
    bundle["capability"] = load_pinned_native_activation(
        activation_path=bundle["activation_path"],
        activation_sha256=bundle["activation_sha256"],
        plan_path=bundle["plan_path"],
        plan_sha256=bundle["plan_sha256"],
        row_id=bundle["row"]["planned_id"],
        purpose="test_simulation",
        trust_root=bundle["trust_root"],
        source_root=bundle["source_root"],
        now="2026-10-25T12:00:00Z",
    )
    return bundle


def _existing_credit_policy_bundle(root: Path) -> dict[str, Any]:
    return _reload_pinned_activation(_apply_existing_credit_policy(_simulation_bundle(root)))


def _mutate_subscription_body(
    bundle: dict[str, Any],
    *,
    updates: Mapping[str, Any],
    remove: tuple[str, ...] = (),
) -> dict[str, Any]:
    context = bundle["context"]
    receipt = context["evidence"]["subscription"]["receipt_artifact"]
    path = bundle["source_root"] / receipt["path"]
    body = json.loads(path.read_text(encoding="utf-8"))
    for key in remove:
        body.pop(key, None)
    body.update(updates)
    path.write_bytes(_canonical_bytes(body))
    _rebind_native_evidence(bundle["source_root"], context, evidence_name="subscription")
    bundle["activation"]["evidence_digests"]["subscription_receipt_sha256"] = receipt["sha256"]
    return _reload_pinned_activation(bundle)


def _production_bundle(root: Path, *, extension: bool = False) -> dict[str, Any]:
    """Create a test-only externally pinned production-shaped capability."""
    bundle = _simulation_bundle(root, extension=extension)
    context_path = bundle["source_root"] / "context.json"
    context_path.write_bytes(_canonical_bytes(bundle["context"]))
    capability = load_pinned_native_activation(
        activation_path=bundle["activation_path"],
        activation_sha256=bundle["activation_sha256"],
        plan_path=bundle["plan_path"],
        plan_sha256=bundle["plan_sha256"],
        row_id=bundle["row"]["planned_id"],
        purpose="production_native",
        origin="trusted_bootstrap",
        trust_root=bundle["trust_root"],
        source_root=bundle["source_root"],
        now="2026-10-25T12:00:00Z",
    )
    bundle["capability"] = capability
    bundle["context_path"] = context_path
    return bundle


def _production_config(bundle: dict[str, Any]) -> dict[str, Any]:
    row = bundle["row"]
    target = row["target"]
    bindings = bundle["activation"]["artifact_bindings"]
    return {
        "assignment_id": row["assignment_id"],
        "study_id": bundle["context"]["study_id"],
        "quest_id": row["quest_id"],
        "model_host": target["host"],
        "model_selector": target["selector"],
        "representation": row["representation"],
        "effort": target["effort"],
        "seed": row["seed"],
        "repeat": row["repeat"],
        "reset": row["reset"],
        "fixture_id": row["fixture_id"],
        "fixture_sha256": row["fixture_sha256"],
        "oracle_sha256": row["oracle_sha256"],
        "output_schema_sha256": bindings["output_schema_sha256"],
        "allowed_requests_sha256": bindings["allowed_requests_sha256"],
        **{
            field: bundle["context"]["hashes"][field]
            for field in (
                "approved_proposal_sha256",
                "source_manifest_sha256",
                "input_manifest_sha256",
                "prompt_sha256",
                "game_sha256",
                "ontology_sha256",
            )
        },
    }


def _production_args(
    bundle: dict[str, Any],
    root: Path,
    *,
    context_path: Path | None = None,
    source_manifest: Path | None = None,
    input_manifest: Path | None = None,
    output_root: Path | None = None,
    project: Path | None = None,
) -> Any:
    row = bundle["row"]
    argv = [
        "--native",
        "--native-context",
        str(context_path or bundle["context_path"]),
        "--source-root",
        str(bundle["source_root"]),
        "--source-manifest",
        str(source_manifest or bundle["source_root"] / "bound" / "source_manifest.json"),
        "--input-manifest",
        str(input_manifest or bundle["source_root"] / "bound" / "input_manifest.json"),
        "--output-root",
        str(output_root or root / "outputs"),
        "--quest-id",
        row["quest_id"],
        "--seed",
        str(row["seed"]),
        "--fixture-ref",
        row["fixture_id"],
        "--prompt",
        "fixture prompt",
        "--godot-binary",
        "fixture-godot",
    ]
    if project is not None:
        argv.extend(["--project", str(project)])
    return native_cli.parse_args(argv)


@contextlib.contextmanager
def _production_executable_root(bundle: dict[str, Any]) -> Iterator[None]:
    """TEST-ONLY: simulate loading the executable from the approved source root.

    This patches only the CLI's executable-root observation; it does not mint,
    alter, or bypass the capability authority under test.
    """
    with patch.object(native_cli, "ROOT", bundle["source_root"]):
        yield


def _run_production_native(bundle: dict[str, Any], args: Any) -> dict[str, Any]:
    """Run the real native CLI under the test-only executable-root simulation."""
    with _production_executable_root(bundle):
        return native_cli._run_native(args, trusted_activation=bundle["capability"])


def _run_trusted_native_episode(
    bundle: dict[str, Any],
    *,
    output_path: Path | None = None,
    transport: _HostFixtureTransport | None = None,
) -> tuple[dict[str, Any], _HostFixtureTransport]:
    transport = transport or _HostFixtureTransport("codex", {"action": "finish"})

    def local_process(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        on_started = kwargs.get("on_started")
        if callable(on_started):
            on_started()
        return transport(command, **kwargs)

    runner = NativePromptRunner(
        host=bundle["row"]["target"]["host"],
        selector=bundle["row"]["target"]["selector"],
        effort=bundle["row"]["target"]["effort"],
        native_context=bundle["context"],
        trusted_activation=bundle["capability"],
    )

    engine = _SimpleEngine()
    engine.prompt_receipts = []

    def proposal(_context: dict[str, Any]) -> dict[str, Any]:
        response = runner(
            request_id="decision-0",
            instruction="fixture prompt",
            user_prompt="fixture prompt",
            output_schema=bundle["source_root"] / "bound" / "output-schema.json",
            model=bundle["row"]["target"]["selector"],
            timeout=1,
            representation=bundle["row"]["representation"],
        )
        engine.prompt_receipts.append(response.receipt)
        if response.returncode != 0:
            raise RuntimeError(response.receipt.get("error", "fixture transport failed"))
        return response.payload

    def repair(
        _context: dict[str, Any],
        _error: dict[str, Any],
        _reason: str,
        _attempt: int,
    ) -> dict[str, str]:
        return {"action": "finish"}

    engine.propose = proposal  # type: ignore[attr-defined]
    engine.repair = repair  # type: ignore[attr-defined]

    home = bundle["root"] / "home"
    (home / ".codex").mkdir(parents=True, exist_ok=True)
    (home / ".codex" / "auth.json").write_text("{}", encoding="utf-8")

    with (
        patch.dict(os.environ, {"HOME": str(home)}),
        patch("nesy_game.runtime_model_swap_native.run_host_process", side_effect=local_process),
    ):
        record = run_episode(
            engine=engine,
            proposal_source=engine.propose,  # type: ignore[attr-defined]
            repair_source=engine.repair,  # type: ignore[attr-defined]
            model=ModelSpec(
                bundle["row"]["target"]["selector"],
                bundle["row"]["representation"],
                provider=bundle["row"]["target"]["host"],
                offline=False,
            ),
            limits=EpisodeLimits(180, 60, 1, 0),
            seed=bundle["row"]["seed"],
            clock=lambda: 0.0,
            config=_production_config(bundle),
            prompt="fixture prompt",
            native_context=bundle["context"],
            trusted_activation=bundle["capability"],
            output_path=output_path,
        )
    return record, transport


def _cli_engine_double() -> SimpleNamespace:
    return SimpleNamespace(
        propose=lambda _context: {"action": "finish"},
        repair=lambda _context, _error, _reason, _attempt: {"action": "finish"},
        prompt_receipts=[],
    )


def _assert_not_ready(result: dict[str, Any]) -> None:
    self = unittest.TestCase()
    self.assertIs(result.get("ready"), False)
    self.assertTrue(result.get("reasons"))
    self.assertIn("bindings", result)


class NativeActivationCapabilityTests(unittest.TestCase):
    def test_self_consistent_context_without_capability_is_rejected_before_setup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = _native_source_bound_context(root)
            result = validate_native_context(
                context,
                model=_model(context),
                config={"assignment_id": context["assignment_id"]},
                prompt="fixture prompt",
                source_root=root,
                now="2026-10-25T12:00:00Z",
            )
        self.assertFalse(result["ready"])
        self.assertFalse(result.get("launch_authorized", False))
        self.assertFalse(result.get("scientific_eligible", False))
        self.assertIn("trusted_activation_missing", result["reasons"])

    def test_simulation_capability_validates_structure_without_authorizing_launch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            result = validate_native_context(
                bundle["context"],
                model=_model(bundle["context"]),
                config={"assignment_id": bundle["row"]["assignment_id"]},
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertTrue(result["ready"])
        self.assertEqual(result["trust_state"], "test_simulation")
        self.assertFalse(result["launch_authorized"])
        self.assertFalse(result["scientific_eligible"])

    def test_loader_accepts_exact_external_artifact_and_selected_plan_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            capability = bundle["capability"]
        self.assertIsInstance(capability, NativeActivationTrust)
        self.assertEqual(capability.purpose, "test_simulation")
        self.assertEqual(capability.row["planned_id"], bundle["row"]["planned_id"])
        self.assertEqual(capability.row["target"]["host"], "codex")
        self.assertEqual(capability.row["target"]["selector"], "gpt-6.1-sol")
        self.assertEqual(capability.row["representation"], "general_rule")
        self.assertEqual(capability.row["repeat"], 1)
        self.assertEqual(capability.row["seed"], 20261024)
        self.assertTrue(capability.row["reset"])
        self.assertEqual(len(bundle["plan"]["rows"]), 20)
        self.assertEqual(
            bundle["plan"]["counts"],
            {"quests": 1, "targets": 5, "representations": 2, "repeats": 2},
        )

    def test_loader_rejects_digest_expiry_plan_row_and_binding_mismatches(self) -> None:
        cases = (
            ("activation-digest", {"activation_sha256": "0" * 64}),
            ("plan-digest", {"plan_sha256": "0" * 64}),
            ("row-selector", {"row_binding": {"selector": "unapproved-selector"}}),
            ("row-host", {"row_binding": {"host": "claude_code"}}),
            ("row-view", {"row_binding": {"representation": "ontology"}}),
            ("row-repeat", {"row_binding": {"repeat": 2}}),
            ("row-seed", {"row_binding": {"seed": 7}}),
            ("row-reset", {"row_binding": {"reset": False}}),
            ("row-fixture", {"row_binding": {"fixture_id": "fixture:other"}}),
            ("row-oracle", {"row_binding": {"oracle_sha256": "0" * 64}}),
            ("schema", {"schema_version": "runtime-native-activation/1"}),
        )
        for name, mutation in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory))
                activation_sha = bundle["activation_sha256"]
                plan_sha = bundle["plan_sha256"]
                if name == "activation-digest":
                    activation_sha = mutation["activation_sha256"]
                elif name == "plan-digest":
                    plan_sha = mutation["plan_sha256"]
                else:
                    activation = json.loads(bundle["activation_path"].read_text(encoding="utf-8"))
                    for field, value in mutation.items():
                        if isinstance(value, dict):
                            activation[field] = {**activation[field], **value}
                        else:
                            activation[field] = value
                    bundle["activation_path"].write_bytes(_canonical_bytes(activation))
                    activation_sha = hashlib.sha256(
                        bundle["activation_path"].read_bytes()
                    ).hexdigest()
                with self.assertRaises(ValueError):
                    load_pinned_native_activation(
                        activation_path=bundle["activation_path"],
                        activation_sha256=activation_sha,
                        plan_path=bundle["plan_path"],
                        plan_sha256=plan_sha,
                        row_id=bundle["row"]["planned_id"],
                        purpose="test_simulation",
                        trust_root=bundle["trust_root"],
                        source_root=bundle["source_root"],
                    )

    def test_runner_rejects_unlisted_outgoing_request_before_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            schema = bundle["source_root"] / "bound" / "output-schema.json"
            transport = _CountingTransport(stdout="{}")
            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6.1-sol",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
                process_runner=transport,
            )
            response = runner(
                request_id="fixture:unlisted-outgoing-request",
                instruction="unlisted instruction bytes",
                user_prompt="unlisted user prompt bytes",
                output_schema=schema,
                model="gpt-6.1-sol",
                timeout=2,
            )
        self.assertTrue(response.receipt["admission"]["ready"])
        self.assertEqual(response.receipt["error"], "outgoing_request_tuple_not_bound")
        self.assertFalse(response.receipt.get("attempted", False))
        self.assertFalse(response.receipt.get("dispatch_started", False))
        self.assertEqual(transport.calls, [])

    def test_exact_tuple_allowlist_accepts_two_requests_and_rejects_component_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            transport = _CountingTransport(stdout="{}")
            schema = bundle["source_root"] / "bound" / "output-schema.json"
            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6.1-sol",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
                process_runner=transport,
            )
            first = runner(
                request_id="fixture:first",
                instruction="fixture prompt",
                user_prompt="fixture prompt",
                output_schema=schema,
                model="gpt-6.1-sol",
                timeout=2,
            )
            second = runner(
                request_id="fixture:second",
                instruction="fixture prompt second",
                user_prompt="fixture prompt second",
                output_schema=schema,
                model="gpt-6.1-sol",
                timeout=2,
            )
            rejected = runner(
                request_id="fixture:third",
                instruction="fixture prompt third",
                user_prompt="fixture prompt third",
                output_schema=schema,
                model="gpt-6.1-sol",
                timeout=2,
            )
            self.assertEqual(first.returncode, 0)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(rejected.receipt["error"], "outgoing_request_tuple_not_bound")
            self.assertEqual(len(transport.calls), 2)

            changed_schema = bundle["source_root"] / "bound" / "changed-schema.json"
            changed_schema.write_text('{"type":"array"}', encoding="utf-8")
            schema_rejected = runner(
                request_id="fixture:schema",
                instruction="fixture prompt",
                user_prompt="fixture prompt",
                output_schema=changed_schema,
                model="gpt-6.1-sol",
                timeout=2,
            )
        self.assertEqual(schema_rejected.receipt["error"], "output_schema_bytes_not_bound")
        self.assertEqual(len(transport.calls), 2)

    def test_allowlist_shape_order_duplicates_size_and_digest_are_rejected(self) -> None:
        mutations: list[tuple[str, Any]] = [
            ("empty", []),
            ("duplicate", lambda rows: [rows[0], rows[0]]),
            ("noncanonical", lambda rows: list(reversed(rows))),
            (
                "oversized",
                lambda rows: (
                    rows
                    + [
                        {
                            "instruction_sha256": f"{index:064x}",
                            "user_prompt_sha256": f"{index + 1:064x}",
                            "output_schema_sha256": f"{index + 2:064x}",
                        }
                        for index in range(11)
                    ]
                ),
            ),
            ("wrong-keys", lambda rows: [{"instruction_sha256": rows[0]["instruction_sha256"]}]),
            (
                "bad-hash",
                lambda rows: [{**rows[0], "user_prompt_sha256": "not-a-sha256"}, rows[1]],
            ),
            ("digest-mismatch", "digest-mismatch"),
        ]
        for name, mutation in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory))
                activation = json.loads(bundle["activation_path"].read_text(encoding="utf-8"))
                rows = activation["artifact_bindings"]["allowed_requests"]
                if mutation == "digest-mismatch":
                    activation["artifact_bindings"]["allowed_requests_sha256"] = "0" * 64
                else:
                    activation["artifact_bindings"]["allowed_requests"] = (
                        mutation(rows) if callable(mutation) else mutation
                    )
                    activation["artifact_bindings"]["allowed_requests_sha256"] = hashlib.sha256(
                        _canonical_bytes(activation["artifact_bindings"]["allowed_requests"])
                    ).hexdigest()
                path = bundle["trust_root"] / f"mutated-{name}.json"
                path.write_bytes(_canonical_bytes(activation))
                with self.assertRaises(ValueError):
                    load_pinned_native_activation(
                        activation_path=path,
                        activation_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        plan_path=bundle["plan_path"],
                        plan_sha256=bundle["plan_sha256"],
                        row_id=bundle["row"]["planned_id"],
                        purpose="test_simulation",
                        trust_root=bundle["trust_root"],
                        source_root=bundle["source_root"],
                    )

    def test_public_input_receipt_digest_cannot_be_replaced_by_context_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            context = bundle["context"]
            context["evidence"]["public_input"]["allowed_requests_sha256"] = "0" * 64
            result = validate_native_context(
                context,
                model=_model(context),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertFalse(result["ready"])
        self.assertTrue(any("public_input" in reason for reason in result["reasons"]))

    def test_loader_rejects_external_private_symlink_and_oversized_trust_artifacts_before_reads(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            outside = Path(directory).parent / f"{Path(directory).name}-outside"
            outside.mkdir()
            external = outside / "activation.json"
            external.write_bytes(bundle["activation_path"].read_bytes())
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=external,
                    activation_sha256=hashlib.sha256(external.read_bytes()).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                )
            private_path = bundle["trust_root"] / "private" / "activation.json"
            private_path.parent.mkdir()
            private_path.write_bytes(bundle["activation_path"].read_bytes())
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=private_path,
                    activation_sha256=hashlib.sha256(private_path.read_bytes()).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                )

            link = bundle["trust_root"] / "activation-link.json"
            os.symlink(external, link)
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=link,
                    activation_sha256=hashlib.sha256(link.read_bytes()).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                )

            oversized = bundle["trust_root"] / "oversized.json"
            oversized.write_bytes(b"{" + b"x" * (8 * 1024 * 1024) + b"}")
            digest = hashlib.sha256(oversized.read_bytes()).hexdigest()
            with (
                patch.object(Path, "read_bytes", side_effect=AssertionError("oversized read")),
                self.assertRaises(ValueError),
            ):
                load_pinned_native_activation(
                    activation_path=oversized,
                    activation_sha256=digest,
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                )

    def test_loader_rejects_expired_and_current_preparation_approval_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            expired = dict(bundle["activation"])
            expired["expires_at"] = "2026-10-24T00:00:00Z"
            expired_path = bundle["trust_root"] / "expired-activation.json"
            expired_path.write_bytes(_canonical_bytes(expired))
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=expired_path,
                    activation_sha256=hashlib.sha256(expired_path.read_bytes()).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                )
            preparation_path = bundle["trust_root"] / "preparation-approval.json"
            preparation_path.write_bytes(
                _canonical_bytes(
                    {
                        "schema_version": "runtime-native-preparation-approval/1",
                        "kind": "human_approved_native_preparation",
                        "status": "approved",
                    }
                )
            )
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=preparation_path,
                    activation_sha256=hashlib.sha256(preparation_path.read_bytes()).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="production_native",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                )

    def test_native_manifests_reject_synthetic_unresolved_private_and_nested_entries(self) -> None:
        for mutation in (
            "synthetic",
            "engineering_only",
            "unresolved_publicity",
            "private_role",
            "nested_manifest",
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory), manifest_mutation=mutation)
                result = validate_native_context(
                    bundle["context"],
                    model=_model(bundle["context"]),
                    config={"assignment_id": bundle["row"]["assignment_id"]},
                    prompt="fixture prompt",
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                    trusted_activation=bundle["capability"],
                )
            self.assertFalse(result["ready"])
            self.assertTrue(
                any("manifest" in reason or "private" in reason for reason in result["reasons"])
            )


class NativeContextAdmissionTests(unittest.TestCase):
    def test_missing_false_expired_hash_model_and_representation_gates_reject_before_dispatch(
        self,
    ) -> None:
        cases: list[tuple[str, Any]] = []
        missing = _native_context()
        del missing["evidence"]["public_input"]
        cases.append(("missing-publicity", missing))
        missing_identity = _native_context()
        del missing_identity["evidence"]["identity_setting"]
        cases.append(("missing-identity", missing_identity))
        false_activation = _native_context()
        false_activation["authority"]["native_activation"] = False
        cases.append(("false-activation", false_activation))
        false_publicity = _native_context()
        false_publicity["authority"]["public_input_egress"] = False
        cases.append(("false-publicity", false_publicity))

        false_authority = _native_context()
        false_authority["authority"]["context_isolation_verified"] = False
        cases.append(("false-isolation", false_authority))
        false_subscription = _native_context()
        false_subscription["authority"]["subscription_no_additional_charge_verified"] = False
        cases.append(("false-subscription", false_subscription))

        expired = _native_context(expires_at="2026-10-24T00:00:00Z")
        cases.append(("expired", expired))

        wrong_hash = _native_context()
        wrong_hash["hashes"]["source_manifest_sha256"] = "9" * 64
        cases.append(("source-mismatch", wrong_hash))

        wrong_model = _native_context(selector="gpt-5.6-sol")
        cases.append(("model-mismatch", wrong_model))

        wrong_representation = _native_context(representation="ontology")
        cases.append(("representation-mismatch", wrong_representation))

        for name, context in cases:
            with self.subTest(name=name):
                result = validate_native_context(
                    context,
                    model=_model(_native_context()),
                    config={"assignment_id": "prep-quest-001"},
                    prompt="fixture prompt",
                    now="2026-10-25T12:00:00Z",
                )
                _assert_not_ready(result)

                transport = _CountingTransport(stdout="{}")
                runner = NativePromptRunner(
                    host="codex",
                    selector="gpt-6.1-sol",
                    effort="medium",
                    native_context=context,
                    process_runner=transport,
                    clock=lambda: 0.0,
                )
                response = runner(
                    request_id="prep-quest-001:0",
                    user_prompt="fixture prompt",
                    model="gpt-6.1-sol",
                    timeout=5.0,
                    representation="general_rule",
                )
                self.assertIsInstance(response, NativePromptResult)
                self.assertNotEqual(response.returncode, 0)
                self.assertEqual(transport.calls, [])

    def test_ready_true_is_not_evidence_and_unresolved_context_blocks_process(self) -> None:
        context = _native_context()
        context["evidence"]["context_isolation"]["status"] = "unknown"
        context["evidence"]["context_isolation"]["sandbox"] = "plan"
        context["evidence"]["context_isolation"]["mode"] = "plan"
        context["authority"]["context_isolation_verified"] = False
        context["ready"] = True
        result = validate_native_context(
            context,
            model=_model(context),
            config={"assignment_id": context["assignment_id"]},
            prompt="fixture prompt",
            now="2026-10-25T12:00:00Z",
        )
        _assert_not_ready(result)

        transport = _CountingTransport(stdout="{}")
        runner = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=context,
            process_runner=transport,
        )
        response = runner(request_id="r1", user_prompt="fixture", model="gpt-6.1-sol", timeout=2)
        self.assertEqual(transport.calls, [])
        self.assertFalse(response.receipt.get("dispatch_started", False))

    def test_complete_source_bound_native_context_still_requires_independent_capability(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = _native_source_bound_context(root)
            result = validate_native_context(
                context,
                model=_model(context),
                config={"assignment_id": context["assignment_id"]},
                prompt="fixture prompt",
                source_root=root,
                now="2026-10-25T12:00:00Z",
            )
        self.assertFalse(result["ready"])
        self.assertFalse(result.get("launch_authorized", False))
        self.assertFalse(result.get("scientific_eligible", False))
        self.assertIn("trusted_activation_missing", result["reasons"])

    def test_native_context_cannot_authorize_project_root_paths_without_source_root(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            context = _project_root_native_context(Path(directory))
            result = validate_native_context(
                context,
                model=_model(context),
                config={"assignment_id": context["assignment_id"]},
                prompt="fixture prompt",
                now="2026-10-25T12:00:00Z",
            )
        self.assertFalse(result["ready"])
        self.assertFalse(result.get("launch_authorized", False))
        self.assertIn("trusted_activation_missing", result["reasons"])

    def test_native_receipt_artifacts_missing_false_tampered_or_denied_reject(self) -> None:
        mutations = ("missing", "false", "tampered", "denied-permissions")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context = _native_source_bound_context(root)
                activation = context["evidence"]["activation"]
                if mutation == "missing":
                    del context["evidence"]["activation"]
                elif mutation == "false":
                    activation["source_bound"] = False
                elif mutation == "tampered":
                    (root / activation["receipt_artifact"]["path"]).write_text(
                        "tampered receipt\n", encoding="utf-8"
                    )
                else:
                    activation_path = root / activation["receipt_artifact"]["path"]
                    activation_body = json.loads(activation_path.read_text(encoding="utf-8"))
                    activation_body["permissions"]["generation"] = False
                    activation_body["permissions"]["egress"] = False
                    activation_path.write_text(
                        json.dumps(activation_body, sort_keys=True), encoding="utf-8"
                    )
                    _rebind_native_evidence(root, context, evidence_name="activation")
                result = validate_native_context(
                    context,
                    model=_model(context),
                    config={"assignment_id": context["assignment_id"]},
                    prompt="fixture prompt",
                    source_root=root,
                    now="2026-10-25T12:00:00Z",
                )
                self.assertFalse(result["ready"])
                self.assertTrue(result["reasons"])

    def test_native_receipt_body_schema_and_descriptor_disagreement_reject(self) -> None:
        mutations = ("descriptor-body-disagreement", "raw-string", "self-certified")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context = _native_source_bound_context(root)
                activation = context["evidence"]["activation"]
                activation_path = root / activation["receipt_artifact"]["path"]
                if mutation == "descriptor-body-disagreement":
                    body = json.loads(activation_path.read_text(encoding="utf-8"))
                    body["assignment_id"] = "different-assignment"
                    activation_path.write_text(json.dumps(body, sort_keys=True), encoding="utf-8")
                elif mutation == "raw-string":
                    activation_path.write_text(
                        json.dumps("source-bound synthetic activation"), encoding="utf-8"
                    )
                else:
                    activation_path.write_text(
                        json.dumps({"status": "verified", "source_bound": True}), encoding="utf-8"
                    )
                _rebind_native_evidence(root, context, evidence_name="activation")
                result = validate_native_context(
                    context,
                    model=_model(context),
                    config={"assignment_id": context["assignment_id"]},
                    prompt="fixture prompt",
                    source_root=root,
                    now="2026-10-25T12:00:00Z",
                )
                self.assertFalse(result["ready"])
                self.assertTrue(result["reasons"])

    def test_antigravity_effective_isolation_receipt_is_required_and_bound(self) -> None:
        mutations = ("missing", "false", "tampered")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context = _native_source_bound_context(
                    root, host="antigravity", selector="gemini-3.8-flash-medium"
                )
                effective = context["evidence"]["effective_tool_context"]
                if mutation == "missing":
                    del context["evidence"]["effective_tool_context"]
                elif mutation == "false":
                    effective["source_bound"] = False
                else:
                    (root / effective["receipt_artifact"]["path"]).write_text(
                        "tampered isolation receipt\n", encoding="utf-8"
                    )
                result = validate_native_context(
                    context,
                    model=_model(context),
                    config={"assignment_id": context["assignment_id"]},
                    prompt="fixture prompt",
                    source_root=root,
                    now="2026-10-25T12:00:00Z",
                )
                self.assertFalse(result["ready"])

    def test_denied_private_auth_wiki_and_raw_paths_are_rejected_before_read(self) -> None:
        for segment in ("private", "auth", "wiki", "raw"):
            with self.subTest(segment=segment), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = _simulation_bundle(root)
                baseline = validate_native_context(
                    bundle["context"],
                    model=_model(bundle["context"]),
                    config=_simulation_config(bundle),
                    prompt="fixture prompt",
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                    trusted_activation=bundle["capability"],
                )
                self.assertTrue(baseline["ready"])
                self.assertFalse(baseline["launch_authorized"])
                self.assertFalse(baseline["scientific_eligible"])

                context = bundle["context"]
                denied = bundle["source_root"] / segment / "never-read.json"
                context["bound_files"]["source_manifest"]["path"] = f"{segment}/never-read.json"
                original_read_bytes = Path.read_bytes

                def guarded_read_bytes(
                    path: Path,
                    denied_path: Path = denied,
                    original_reader: Any = original_read_bytes,
                ) -> bytes:
                    if path.resolve() == denied_path.resolve():
                        raise AssertionError("denied receipt path was read")
                    return original_reader(path)

                with patch.object(Path, "read_bytes", guarded_read_bytes):
                    result = validate_native_context(
                        context,
                        model=_model(context),
                        config=_simulation_config(bundle),
                        prompt="fixture prompt",
                        source_root=bundle["source_root"],
                        now="2026-10-25T12:00:00Z",
                        trusted_activation=bundle["capability"],
                    )
                self.assertFalse(result["ready"])
                self.assertIn("source_manifest_private_path_rejected", result["reasons"])

    def test_native_context_cannot_authorize_project_root_paths_with_source_root_alone(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            context = _project_root_native_context(Path(directory))
            result = validate_native_context(
                context,
                model=_model(context),
                config={"assignment_id": context["assignment_id"]},
                prompt="fixture prompt",
                now="2026-10-25T12:00:00Z",
            )
        self.assertFalse(result["ready"])
        self.assertFalse(result.get("launch_authorized", False))
        self.assertIn("trusted_activation_missing", result["reasons"])

    def test_native_ready_flag_cannot_self_certify_without_activation_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            context = _native_source_bound_context(Path(directory))
            del context["evidence"]["activation"]
            context["ready"] = True
            result = validate_native_context(
                context,
                model=_model(context),
                config={"assignment_id": context["assignment_id"]},
                prompt="fixture prompt",
                source_root=directory,
                now="2026-10-25T12:00:00Z",
            )
        self.assertFalse(result["ready"])

    def test_native_admission_rejects_drift_in_file_listed_by_bound_source_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _simulation_bundle(root)
            context = bundle["context"]
            listed = bundle["source_root"] / "bound" / "public-controller.gd"
            baseline = validate_native_context(
                context,
                model=_model(context),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertTrue(baseline["ready"])
            self.assertFalse(baseline["launch_authorized"])
            self.assertFalse(baseline["scientific_eligible"])

            listed.write_text("controller tampered\n", encoding="utf-8")
            drifted = validate_native_context(
                context,
                model=_model(context),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertFalse(drifted["ready"])
            self.assertIn("source_manifest_file_content_mismatch", drifted["reasons"])

    def test_native_admission_rejects_drift_in_file_listed_by_bound_input_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _simulation_bundle(root)
            context = bundle["context"]
            listed = bundle["source_root"] / "bound" / "public-prompt.txt"
            baseline = validate_native_context(
                context,
                model=_model(context),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertTrue(baseline["ready"])
            self.assertFalse(baseline["launch_authorized"])
            self.assertFalse(baseline["scientific_eligible"])

            listed.write_text("public input tampered\n", encoding="utf-8")
            drifted = validate_native_context(
                context,
                model=_model(context),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertFalse(drifted["ready"])
            self.assertIn("input_manifest_file_content_mismatch", drifted["reasons"])

    def test_native_admission_rejects_private_path_listed_by_source_manifest_before_read(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _simulation_bundle(root, manifest_mutation="private_path")
            denied = bundle["source_root"] / "private" / "controller.gd"
            original_read_bytes = Path.read_bytes

            def guarded_read_bytes(
                path: Path,
                denied_path: Path = denied,
                original_reader: Any = original_read_bytes,
            ) -> bytes:
                if path.resolve() == denied_path.resolve():
                    raise AssertionError("denied manifest leaf path was read")
                return original_reader(path)

            with patch.object(Path, "read_bytes", guarded_read_bytes):
                result = validate_native_context(
                    bundle["context"],
                    model=_model(bundle["context"]),
                    config=_simulation_config(bundle),
                    prompt="fixture prompt",
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                    trusted_activation=bundle["capability"],
                )
        self.assertFalse(result["ready"])
        self.assertIn("source_manifest_private_path_rejected", result["reasons"])

    def test_engineering_fixture_requires_injected_transport_and_is_never_scientific(self) -> None:
        context = _native_context(mode="engineering_fixture")
        missing_transport = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=context,
        )
        response = missing_transport(
            request_id="fixture:missing-transport",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=1,
        )
        self.assertNotEqual(response.returncode, 0)
        self.assertFalse(response.receipt.get("scientific_eligible", True))
        self.assertEqual(response.receipt.get("mode"), "engineering_fixture")

        transport = _HostFixtureTransport("codex", {"action": "observe"})
        runner = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=context,
            process_runner=transport,
        )
        response = runner(
            request_id="fixture:injected",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=1,
        )
        self.assertIsInstance(response, NativePromptResult)
        self.assertFalse(response.receipt["scientific_eligible"])
        self.assertEqual(response.receipt["mode"], "engineering_fixture")


class NativeBillingPolicyAdmissionTests(unittest.TestCase):
    def test_loader_accepts_existing_credit_policy_for_codex_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _existing_credit_policy_bundle(Path(directory))
            result = validate_native_context(
                bundle["context"],
                model=_model(bundle["context"]),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertTrue(result["ready"], result["reasons"])
        self.assertEqual(bundle["capability"].activation["billing_policy"], _EXISTING_CREDIT_POLICY)
        self.assertIs(
            bundle["capability"].activation["permissions"]["no_additional_charge_verified"],
            False,
        )

    def test_included_only_source_bound_fixture_remains_admissible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            result = validate_native_context(
                bundle["context"],
                model=_model(bundle["context"]),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertTrue(result["ready"])
        self.assertEqual(result["trust_state"], "test_simulation")

    def test_included_only_false_zero_cost_labels_reject_before_dispatch(self) -> None:
        for mutation in ("wrapper", "body"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory))
                if mutation == "wrapper":
                    bundle["context"]["evidence"]["subscription"]["no_additional_charge"] = False
                else:
                    receipt = bundle["context"]["evidence"]["subscription"]["receipt_artifact"]
                    path = bundle["source_root"] / receipt["path"]
                    body = json.loads(path.read_text(encoding="utf-8"))
                    body["no_additional_charge"] = False
                    path.write_bytes(_canonical_bytes(body))
                    _rebind_native_evidence(
                        bundle["source_root"], bundle["context"], evidence_name="subscription"
                    )
                    bundle["activation"]["evidence_digests"]["subscription_receipt_sha256"] = (
                        receipt["sha256"]
                    )
                    _reload_pinned_activation(bundle)
                result = validate_native_context(
                    bundle["context"],
                    model=_model(bundle["context"]),
                    config=_simulation_config(bundle),
                    prompt="fixture prompt",
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                    trusted_activation=bundle["capability"],
                )
                self.assertFalse(result["ready"])
                transport = _CountingTransport(stdout="{}")
                response = NativePromptRunner(
                    host="codex",
                    selector="gpt-6.1-sol",
                    effort="medium",
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                    process_runner=transport,
                )(
                    request_id="fixture:included-only-charge",
                    user_prompt="fixture prompt",
                    model="gpt-6.1-sol",
                    timeout=2,
                )
                self.assertNotEqual(response.returncode, 0)
                self.assertEqual(transport.calls, [])

    def test_loader_requires_explicit_credit_permissions_to_be_exact_booleans(self) -> None:
        missing = object()
        for key, expected in _CREDIT_POLICY_FIELDS.items():
            invalid = not expected
            invalid_string = "true" if expected is True else "false"
            for label, value in (
                ("missing", missing),
                ("invalid", invalid),
                ("string", invalid_string),
            ):
                with self.subTest(key=key, value=label), tempfile.TemporaryDirectory() as directory:
                    bundle = _apply_existing_credit_policy(_simulation_bundle(Path(directory)))
                    if value is missing:
                        bundle["activation"]["permissions"].pop(key)
                    else:
                        bundle["activation"]["permissions"][key] = value
                    activation_bytes = _canonical_bytes(bundle["activation"])
                    bundle["activation_path"].write_bytes(activation_bytes)
                    with self.assertRaises(ValueError):
                        load_pinned_native_activation(
                            activation_path=bundle["activation_path"],
                            activation_sha256=hashlib.sha256(activation_bytes).hexdigest(),
                            plan_path=bundle["plan_path"],
                            plan_sha256=bundle["plan_sha256"],
                            row_id=bundle["row"]["planned_id"],
                            purpose="test_simulation",
                            trust_root=bundle["trust_root"],
                            source_root=bundle["source_root"],
                            now="2026-10-25T12:00:00Z",
                        )

    def test_allowed_request_allowlist_supports_48_sorted_tuples_and_rejects_invalid_shapes(
        self,
    ) -> None:
        def bindings(rows: list[dict[str, str]]) -> dict[str, Any]:
            return {
                "allowed_requests": rows,
                "allowed_requests_sha256": hashlib.sha256(_canonical_bytes(rows)).hexdigest(),
            }

        rows = [
            {
                "instruction_sha256": f"{index:064x}",
                "user_prompt_sha256": f"{index + 100:064x}",
                "output_schema_sha256": f"{index + 200:064x}",
            }
            for index in range(48)
        ]
        accepted = native_runtime._validate_allowed_requests(bindings(rows))
        self.assertEqual(len(accepted), 48)
        self.assertEqual(accepted[0]["instruction_sha256"], "0" * 64)
        self.assertEqual(accepted[-1]["instruction_sha256"], f"{47:064x}")

        for name, invalid_rows in (
            (
                "49-rows",
                [
                    {
                        "instruction_sha256": f"{index:064x}",
                        "user_prompt_sha256": f"{index + 100:064x}",
                        "output_schema_sha256": f"{index + 200:064x}",
                    }
                    for index in range(49)
                ],
            ),
            ("duplicate", rows[:-1] + [rows[-2]]),
            ("unordered", list(reversed(rows))),
        ):
            with self.subTest(name=name), self.assertRaises(ValueError):
                native_runtime._validate_allowed_requests(bindings(invalid_rows))

    def test_context_and_subscription_wrapper_require_credit_permissions_before_dispatch(
        self,
    ) -> None:
        for mapping_name in ("authority", "subscription"):
            for key, expected in _CREDIT_POLICY_FIELDS.items():
                invalid = not expected
                invalid_string = "true" if expected is True else "false"
                for label, value in (
                    ("missing", None),
                    ("invalid", invalid),
                    ("string", invalid_string),
                ):
                    with (
                        self.subTest(mapping=mapping_name, key=key, value=label),
                        tempfile.TemporaryDirectory() as directory,
                    ):
                        bundle = _existing_credit_policy_bundle(Path(directory))
                        mapping = (
                            bundle["context"]["authority"]
                            if mapping_name == "authority"
                            else bundle["context"]["evidence"]["subscription"]
                        )
                        if label == "missing":
                            mapping.pop(key)
                        else:
                            mapping[key] = value
                        result = validate_native_context(
                            bundle["context"],
                            model=_model(bundle["context"]),
                            config=_simulation_config(bundle),
                            prompt="fixture prompt",
                            source_root=bundle["source_root"],
                            now="2026-10-25T12:00:00Z",
                            trusted_activation=bundle["capability"],
                        )
                        self.assertFalse(result["ready"])
                        transport = _CountingTransport(stdout="{}")
                        response = NativePromptRunner(
                            host="codex",
                            selector="gpt-6.1-sol",
                            effort="medium",
                            native_context=bundle["context"],
                            trusted_activation=bundle["capability"],
                            process_runner=transport,
                        )(
                            request_id="fixture:credit-permission",
                            user_prompt="fixture prompt",
                            model="gpt-6.1-sol",
                            timeout=2,
                        )
                        self.assertNotEqual(response.returncode, 0)
                        self.assertEqual(transport.calls, [])

    def test_subscription_body_policy_or_permission_tampering_rejects_after_rebinding(self) -> None:
        cases: list[tuple[str, dict[str, Any], tuple[str, ...]]] = [
            ("policy-mismatch", {"billing_policy": "included_only"}, ()),
        ]
        for key, expected in _CREDIT_POLICY_FIELDS.items():
            invalid = not expected
            invalid_string = "true" if expected is True else "false"
            cases.extend(
                (
                    (f"{key}-missing", {}, (key,)),
                    (f"{key}-false-or-true", {key: invalid}, ()),
                    (f"{key}-string", {key: invalid_string}, ()),
                )
            )
        for name, updates, remove in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = _existing_credit_policy_bundle(Path(directory))
                _mutate_subscription_body(bundle, updates=updates, remove=remove)
                result = validate_native_context(
                    bundle["context"],
                    model=_model(bundle["context"]),
                    config=_simulation_config(bundle),
                    prompt="fixture prompt",
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                    trusted_activation=bundle["capability"],
                )
                self.assertFalse(result["ready"])
                transport = _CountingTransport(stdout="{}")
                response = NativePromptRunner(
                    host="codex",
                    selector="gpt-6.1-sol",
                    effort="medium",
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                    process_runner=transport,
                )(
                    request_id="fixture:subscription-body",
                    user_prompt="fixture prompt",
                    model="gpt-6.1-sol",
                    timeout=2,
                )
                self.assertNotEqual(response.returncode, 0)
                self.assertEqual(transport.calls, [])

    def test_unknown_or_mismatched_billing_policy_rejects(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _apply_existing_credit_policy(_simulation_bundle(Path(directory)))
            bundle["activation"]["billing_policy"] = "unknown-policy"
            activation_bytes = _canonical_bytes(bundle["activation"])
            bundle["activation_path"].write_bytes(activation_bytes)
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=bundle["activation_path"],
                    activation_sha256=hashlib.sha256(activation_bytes).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=bundle["row"]["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                )

        with tempfile.TemporaryDirectory() as directory:
            bundle = _existing_credit_policy_bundle(Path(directory))
            bundle["context"]["billing_policy"] = "included_only"
            result = validate_native_context(
                bundle["context"],
                model=_model(bundle["context"]),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertFalse(result["ready"])

    def test_codex_only_credit_policy_cannot_be_loaded_for_another_host_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _apply_existing_credit_policy(_simulation_bundle(Path(directory)))
            other_host = bundle["plan"]["rows"][8]
            bundle["activation"]["plan"].update(
                row_id=other_host["planned_id"],
                row_sha256=hashlib.sha256(_canonical_bytes(other_host)).hexdigest(),
            )
            bundle["activation"]["row_binding"].update(
                assignment_id=other_host["assignment_id"],
                quest_id=other_host["quest_id"],
                host=other_host["target"]["host"],
                selector=other_host["target"]["selector"],
                effort=other_host["target"]["effort"],
                representation=other_host["representation"],
                repeat=other_host["repeat"],
                seed=other_host["seed"],
                reset=other_host["reset"],
                fixture_id=other_host["fixture_id"],
                fixture_sha256=other_host["fixture_sha256"],
                oracle_sha256=other_host["oracle_sha256"],
            )
            activation_bytes = _canonical_bytes(bundle["activation"])
            bundle["activation_path"].write_bytes(activation_bytes)
            with self.assertRaises(ValueError):
                load_pinned_native_activation(
                    activation_path=bundle["activation_path"],
                    activation_sha256=hashlib.sha256(activation_bytes).hexdigest(),
                    plan_path=bundle["plan_path"],
                    plan_sha256=bundle["plan_sha256"],
                    row_id=other_host["planned_id"],
                    purpose="test_simulation",
                    trust_root=bundle["trust_root"],
                    source_root=bundle["source_root"],
                    now="2026-10-25T12:00:00Z",
                )

    def test_validate_native_context_rejects_codex_only_policy_for_claude_before_dispatch(
        self,
    ) -> None:
        context = _native_context(host="claude_code", selector="opus")
        context["billing_policy"] = _EXISTING_CREDIT_POLICY
        context["authority"].update(
            subscription_no_additional_charge_verified=False,
            **_CREDIT_POLICY_FIELDS,
        )
        context["evidence"]["subscription"].update(
            billing_policy=_EXISTING_CREDIT_POLICY,
            no_additional_charge=False,
            **_CREDIT_POLICY_FIELDS,
        )
        result = validate_native_context(
            context,
            model=_model(context),
            config={"assignment_id": context["assignment_id"]},
            prompt="fixture prompt",
            now="2026-10-25T12:00:00Z",
        )
        self.assertFalse(result["ready"])
        transport = _CountingTransport(stdout="{}")
        response = NativePromptRunner(
            host="claude_code",
            selector="opus",
            effort="medium",
            native_context=context,
            process_runner=transport,
        )(
            request_id="fixture:non-codex-credit-policy",
            user_prompt="fixture prompt",
            model="opus",
            timeout=2,
        )
        self.assertNotEqual(response.returncode, 0)
        self.assertEqual(transport.calls, [])


class NativeCodexCatalogTests(unittest.TestCase):
    def test_static_catalog_derivation_preserves_canonical_models_except_tool_fields(self) -> None:
        original = json.loads(_CODEX_ORIGINAL_EXTRACT_PATH.read_text(encoding="utf-8"))
        derived_bytes = _CODEX_DERIVED_CATALOG_PATH.read_bytes()
        derived = json.loads(derived_bytes.decode("utf-8"))
        provenance = json.loads(_CODEX_PROVENANCE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(
            provenance["original_extract_kind"],
            "Canonical JSON extraction of two unmodified model records, not a full byte-identical source snapshot",
        )
        self.assertEqual(hashlib.sha256(derived_bytes).hexdigest(), _CODEX_DERIVED_CATALOG_SHA256)
        self.assertEqual(provenance["derived_sha256"], _CODEX_DERIVED_CATALOG_SHA256)
        self.assertEqual(provenance["selected_slugs"], ["gpt-6.1-sol", "gpt-5.6-sol"])
        self.assertEqual(
            provenance["only_allowed_field_replacements"],
            _CODEX_ALLOWED_TOOL_FIELD_REPLACEMENTS,
        )
        self.assertIs(
            provenance[
                "model_ids_base_instructions_reasoning_settings_and_all_other_fields_preserved"
            ],
            True,
        )

        self.assertEqual(
            {key: value for key, value in derived.items() if key != "models"},
            {key: value for key, value in original.items() if key != "models"},
        )
        original_models = {model["slug"]: model for model in original["models"]}
        derived_models = {model["slug"]: model for model in derived["models"]}
        self.assertEqual(len(original["models"]), 2)
        self.assertEqual(len(derived["models"]), 2)
        self.assertEqual(set(original_models), {"gpt-6.1-sol", "gpt-5.6-sol"})
        self.assertEqual(set(derived_models), set(original_models))
        for slug in ("gpt-6.1-sol", "gpt-5.6-sol"):
            original_model = original_models[slug]
            derived_model = derived_models[slug]
            self.assertEqual(
                {
                    key: value
                    for key, value in derived_model.items()
                    if key not in _CODEX_ALLOWED_TOOL_FIELD_REPLACEMENTS
                },
                {
                    key: value
                    for key, value in original_model.items()
                    if key not in _CODEX_ALLOWED_TOOL_FIELD_REPLACEMENTS
                },
                slug,
            )
            self.assertEqual(
                {key: derived_model.get(key) for key in _CODEX_ALLOWED_TOOL_FIELD_REPLACEMENTS},
                _CODEX_ALLOWED_TOOL_FIELD_REPLACEMENTS,
                slug,
            )


class NativeHostContractTests(unittest.TestCase):
    def test_supported_codex_claude_and_antigravity_requests_parse_distinct_envelopes(self) -> None:
        payload = {"action": "observe", "request_id": "fixture:1"}
        cases = [
            ("codex", "gpt-6.1-sol"),
            ("claude_code", "opus"),
            ("antigravity", "gemini-3.8-flash-medium"),
        ]
        for host, selector in cases:
            with self.subTest(host=host):
                context = _native_context(host=host, selector=selector)
                transport = _HostFixtureTransport(host, payload)
                runner = NativePromptRunner(
                    host=host,
                    selector=selector,
                    effort="medium",
                    native_context=context,
                    process_runner=transport,
                )
                response = runner(
                    request_id="fixture:1",
                    user_prompt="fixture prompt",
                    model=selector,
                    timeout=7.0,
                    output_schema="schema.json",
                    instruction="instruction",
                )
                self.assertEqual(response.returncode, 0)
                self.assertEqual(response.payload, payload)
                self.assertEqual(response.receipt["host"], host)
                self.assertEqual(response.receipt["selector"], selector)
                self.assertEqual(response.receipt["effort"], "medium")
                if host in {"claude_code", "antigravity"}:
                    self.assertEqual(
                        response.receipt["usage"], {"input_tokens": 11, "output_tokens": 7}
                    )
                self.assertEqual(len(transport.calls), 1)

                command = transport.calls[0]["command"]
                if host == "codex":
                    self.assertIn("exec", command)
                    self.assertIn("--output-last-message", command)
                    self.assertIn("--model", command)
                    self.assertIn("--skip-git-repo-check", command)
                elif host == "claude_code":
                    self.assertIn("--output-format", command)
                    self.assertIn("json", command)
                    self.assertIn("--safe-mode", command)
                    self.assertIn("--tools", command)
                    self.assertIn("--strict-mcp-config", command)
                    self.assertIn("--model", command)
                else:
                    self.assertIn("--print", command)
                    self.assertIn("--output-format", command)
                    self.assertIn("--json-schema", command)
                    self.assertIn("--model", command)
                    self.assertIn("--effort", command)
                    for forbidden in ("--safe-mode", "--tools", "--strict-mcp-config", "--bare"):
                        self.assertNotIn(forbidden, command)

    def test_antigravity_uppercase_success_and_refusal_envelopes_are_distinguished(self) -> None:
        payload = {"action": "observe"}
        cases = (
            ("SUCCESS", 0),
            ("refused", 5),
        )
        for status, expected_code in cases:
            with self.subTest(status=status):
                transport = _CountingTransport(
                    stdout=json.dumps({"status": status, "response": payload})
                )
                runner = NativePromptRunner(
                    host="antigravity",
                    selector="gemini-3.8-flash-medium",
                    effort="medium",
                    native_context=_native_context(
                        host="antigravity", selector="gemini-3.8-flash-medium"
                    ),
                    process_runner=transport,
                )
                response = runner(
                    request_id=f"fixture:{status}",
                    user_prompt="fixture",
                    model="gemini-3.8-flash-medium",
                    timeout=2,
                )
                self.assertEqual(response.returncode, expected_code)
                if status == "refused":
                    self.assertEqual(response.receipt["error"], "provider_refused")

    def test_claude_explicit_error_or_refusal_cannot_become_valid_structured_output(self) -> None:
        payload = {"action": "observe"}
        envelopes = (
            {"type": "result", "is_error": True, "structured_output": payload},
            {
                "type": "result",
                "subtype": "error_during_execution",
                "is_error": True,
                "structured_output": payload,
            },
        )
        for envelope in envelopes:
            with self.subTest(envelope=envelope):
                runner = NativePromptRunner(
                    host="claude_code",
                    selector="opus",
                    effort="medium",
                    native_context=_native_context(host="claude_code", selector="opus"),
                    process_runner=_CountingTransport(stdout=json.dumps(envelope)),
                )
                response = runner(
                    request_id="fixture:claude-error",
                    user_prompt="fixture",
                    model="opus",
                    timeout=2,
                )
                self.assertNotEqual(response.returncode, 0)

    def test_request_id_and_validator_rejections_cannot_be_returned_as_valid(self) -> None:
        wrong_id = {"request_id": "fixture:wrong", "action": "observe"}
        transport = _CountingTransport(stdout=json.dumps({"structured_output": wrong_id}))
        runner = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=transport,
        )
        response = runner(
            request_id="fixture:expected",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
            validator=lambda payload, request_id: payload.get("request_id") == request_id,
        )
        self.assertNotEqual(response.returncode, 0)

        rejected = _CountingTransport(
            stdout=json.dumps({"structured_output": {"action": "observe"}})
        )
        runner = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=rejected,
        )
        response = runner(
            request_id="fixture:validator",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
            validator=lambda _payload, _request_id: False,
        )
        self.assertNotEqual(response.returncode, 0)

    def test_codex_policy_features_are_imported_and_cwd_is_confined(self) -> None:
        transport = _CountingTransport(
            stdout=json.dumps({"structured_output": {"action": "observe"}})
        )
        runner = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=transport,
        )
        response = runner(
            request_id="fixture:policy",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
        )
        self.assertEqual(response.returncode, 0)
        command = transport.calls[0]["command"]
        for feature in TOOL_POLICY_FEATURES:
            self.assertIn(
                ["--disable", feature],
                [command[index : index + 2] for index in range(len(command) - 1)],
            )
        cwd = Path(transport.calls[0]["cwd"]).resolve()
        self.assertNotEqual(cwd, ROOT)
        self.assertNotIn(ROOT, cwd.parents)

    def test_codex_turn_completed_usage_survives_output_last_message_payload(self) -> None:
        payload = {"action": "observe"}

        def transport(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            output = Path(command[command.index("--output-last-message") + 1])
            output.write_text(json.dumps(payload), encoding="utf-8")
            stdout = "\n".join(
                (
                    json.dumps(
                        {
                            "type": "turn.completed",
                            "usage": {"input_tokens": 31, "output_tokens": 9},
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": json.dumps(payload)},
                        }
                    ),
                )
            )
            return subprocess.CompletedProcess(command, 0, stdout, "")

        runner = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=transport,
        )
        response = runner(
            request_id="fixture:usage",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
        )
        self.assertEqual(response.returncode, 0)
        self.assertEqual(response.receipt["usage"], {"input_tokens": 31, "output_tokens": 9})

    def test_claude_cost_is_an_estimate_not_a_subscription_invoice(self) -> None:
        envelope = {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "structured_output": {"action": "observe"},
            "modelUsage": {"inputTokens": 11, "outputTokens": 7},
            "total_cost_usd": 0.0123,
        }
        runner = NativePromptRunner(
            host="claude_code",
            selector="opus",
            effort="medium",
            native_context=_native_context(host="claude_code", selector="opus"),
            process_runner=_CountingTransport(stdout=json.dumps(envelope)),
        )
        response = runner(
            request_id="fixture:cost",
            user_prompt="fixture",
            model="opus",
            timeout=2,
        )
        self.assertEqual(response.returncode, 0)
        self.assertEqual(response.receipt["usage"], {"input_tokens": 11, "output_tokens": 7})
        self.assertEqual(response.receipt["cost_estimate_usd"], 0.0123)
        self.assertIsNone(response.receipt["cost_usd"])
        self.assertNotEqual(response.receipt["cost_source"], "subscription_invoice")

    def test_unknown_identity_revision_effort_usage_and_cost_are_not_inferred(self) -> None:
        context = _native_context(host="antigravity", selector="gemini-3.8-flash-medium")
        transport = _CountingTransport(
            stdout=json.dumps({"status": "completed", "response": {"action": "observe"}})
        )
        runner = NativePromptRunner(
            host="antigravity",
            selector="gemini-3.8-flash-medium",
            effort="medium",
            native_context=context,
            process_runner=transport,
        )
        response = runner(
            request_id="fixture:unknowns",
            user_prompt="fixture",
            model="gemini-3.8-flash-medium",
            timeout=2,
        )
        self.assertEqual(response.returncode, 0)
        for key in (
            "provider_identity",
            "provider_revision",
            "effective_effort",
            "usage",
            "cost_usd",
        ):
            self.assertIn(key, response.receipt)
            self.assertIsNone(response.receipt[key])
        self.assertNotEqual(response.receipt.get("cost_source"), "subscription_invoice")

    def test_malformed_refused_nonzero_and_timeout_attempts_keep_receipts_without_dispatch_fallback(
        self,
    ) -> None:
        failures = [
            ("malformed", _CountingTransport(stdout="not-json")),
            ("refused", _CountingTransport(stdout=json.dumps({"status": "refused"}))),
            ("nonzero", _CountingTransport(stdout="{}", returncode=17)),
            (
                "timeout",
                _CountingTransport(error=subprocess.TimeoutExpired(["fixture-host"], timeout=0.25)),
            ),
        ]
        for name, transport in failures:
            with self.subTest(name=name):
                runner = NativePromptRunner(
                    host="antigravity",
                    selector="gemini-3.8-flash-medium",
                    effort="medium",
                    native_context=_native_context(
                        host="antigravity", selector="gemini-3.8-flash-medium"
                    ),
                    process_runner=transport,
                )
                response = runner(
                    request_id=f"fixture:{name}",
                    user_prompt="fixture",
                    model="gemini-3.8-flash-medium",
                    timeout=0.25,
                )
                self.assertNotEqual(response.returncode, 0)
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(response.receipt["attempted"], True)
                self.assertIn("error", response.receipt)
                self.assertNotIn("fallback_host", response.receipt)

    def test_timeout_is_clamped_to_remaining_episode_and_rejects_unrestricted_context(self) -> None:
        observed: list[float] = []

        def transport(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            observed.append(float(kwargs["timeout"]))
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps({"status": "completed", "response": {"action": "observe"}}),
                "",
            )

        context = _native_context(host="claude_code", selector="opus")
        runner = NativePromptRunner(
            host="claude_code",
            selector="opus",
            effort="medium",
            native_context=context,
            process_runner=transport,
        )
        runner(
            request_id="r1",
            user_prompt="fixture",
            model="opus",
            timeout=60,
            remaining_wall_seconds=180,
        )
        runner(
            request_id="r2",
            user_prompt="fixture",
            model="opus",
            timeout=60,
            remaining_wall_seconds=13,
        )
        self.assertEqual(observed, [60.0, 13.0])

        unsafe = _native_context(host="claude_code", selector="opus")
        unsafe["authority"]["context_isolation_verified"] = False
        isolated = NativePromptRunner(
            host="claude_code",
            selector="opus",
            effort="medium",
            native_context=unsafe,
            process_runner=transport,
        )
        before = len(observed)
        result = isolated(
            request_id="r3",
            user_prompt="fixture",
            model="opus",
            timeout=60,
            remaining_wall_seconds=60,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(observed), before)

    def test_invalid_timeout_values_reject_before_transport(self) -> None:
        for timeout in (True, 0, -1.0, float("nan"), float("inf")):
            with self.subTest(timeout=timeout):
                transport = _CountingTransport(stdout=json.dumps({"action": "observe"}))
                runner = NativePromptRunner(
                    host="codex",
                    selector="gpt-6.1-sol",
                    effort="medium",
                    native_context=_native_context(),
                    process_runner=transport,
                )
                result = runner(
                    request_id="fixture:invalid-timeout",
                    user_prompt="fixture",
                    model="gpt-6.1-sol",
                    timeout=timeout,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(result.receipt.get("attempted", False))
                self.assertEqual(transport.calls, [])

    def test_launch_encoding_and_output_bound_failures_retain_attempt_receipts_without_payload(
        self,
    ) -> None:
        launch = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=_CountingTransport(error=OSError("fixture launch failure")),
        )
        launched = launch(
            request_id="fixture:launch",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
        )
        self.assertEqual(launched.returncode, 127)
        self.assertTrue(launched.receipt["attempted"])
        self.assertTrue(launched.receipt["dispatch_started"])
        self.assertIn("host_launch_failed:OSError", launched.receipt["error"])
        self.assertEqual(launched.payload, {})

        oversized = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=_CountingTransport(stdout="x" * (64 * 1024 + 1)),
        )
        bounded = oversized(
            request_id="fixture:output-bound",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
        )
        self.assertEqual(bounded.returncode, 4)
        self.assertEqual(bounded.receipt["error"], "host_output_limit")
        self.assertTrue(bounded.receipt["attempted"])
        self.assertEqual(bounded.payload, {})

        encoded = NativePromptRunner(
            host="codex",
            selector="gpt-6.1-sol",
            effort="medium",
            native_context=_native_context(),
            process_runner=_CountingTransport(stdout=b"\xff\xfe"),
        )
        malformed = encoded(
            request_id="fixture:encoding",
            user_prompt="fixture",
            model="gpt-6.1-sol",
            timeout=2,
        )
        self.assertEqual(malformed.returncode, 5)
        self.assertEqual(malformed.receipt["error"], "malformed_response")
        self.assertTrue(malformed.receipt["attempted"])
        self.assertEqual(malformed.payload, {})

    def test_requested_model_and_representation_mismatches_reject_before_transport(self) -> None:
        cases = (
            {"model": "gpt-5.6-sol"},
            {"representation": "ontology"},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                transport = _CountingTransport(stdout=json.dumps({"action": "observe"}))
                runner = NativePromptRunner(
                    host="codex",
                    selector="gpt-6.1-sol",
                    effort="medium",
                    native_context=_native_context(),
                    process_runner=transport,
                )
                result = runner(
                    request_id="fixture:request-validation",
                    user_prompt="fixture",
                    model=overrides.get("model", "gpt-6.1-sol"),
                    representation=overrides.get("representation", "general_rule"),
                    timeout=2,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(result.receipt.get("attempted", False))
                self.assertEqual(transport.calls, [])

    def test_child_environment_is_scratch_only_and_fixture_mode_never_links_auth(self) -> None:
        observed: dict[str, Any] = {}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_home = root / "original-home"
            original_codex = original_home / ".codex"
            original_codex.mkdir(parents=True)
            original_auth = original_codex / "auth.json"
            original_auth_bytes = (
                b'{"access_token":"fixture-token","refresh_token":"fixture-refresh"}'
            )
            original_auth.write_bytes(original_auth_bytes)
            (original_home / "AGENTS.md").write_text("global sentinel", encoding="utf-8")
            (original_codex / "AGENTS.md").write_text("codex sentinel", encoding="utf-8")
            (original_codex / "config.toml").write_text("fixture_config = true", encoding="utf-8")
            (original_codex / "memories.md").write_text(
                "personal memory sentinel", encoding="utf-8"
            )
            (original_codex / "skills" / "fixture-skill").mkdir(parents=True)
            (original_codex / "skills" / "fixture-skill" / "SKILL.md").write_text(
                "personal skill sentinel", encoding="utf-8"
            )
            project_root = root / "project"
            project_root.mkdir()
            (project_root / "AGENTS.md").write_text("project sentinel", encoding="utf-8")

            def transport(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                observed.update(kwargs)
                child_env = kwargs["env"]
                scratch = Path(kwargs["cwd"]).resolve()
                observed["scratch"] = scratch
                for key in (
                    "HOME",
                    "CODEX_HOME",
                    "TMPDIR",
                    "TMP",
                    "TEMP",
                    "XDG_CONFIG_HOME",
                    "XDG_CACHE_HOME",
                    "XDG_DATA_HOME",
                ):
                    self.assertIn(key, child_env)
                    path = Path(child_env[key]).resolve()
                    self.assertTrue(
                        path == scratch or scratch in path.parents, (key, path, scratch)
                    )
                    self.assertNotEqual(path, original_home.resolve())
                self.assertEqual(Path(child_env["CODEX_HOME"]).name, ".codex")
                self.assertNotIn(str(original_home.resolve()), " ".join(child_env.values()))
                self.assertFalse((Path(child_env["HOME"]) / "AGENTS.md").exists())
                self.assertFalse((Path(child_env["CODEX_HOME"]) / "AGENTS.md").exists())
                self.assertFalse((Path(child_env["CODEX_HOME"]) / "config.toml").exists())
                self.assertFalse((Path(child_env["CODEX_HOME"]) / "memories.md").exists())
                self.assertFalse((Path(child_env["CODEX_HOME"]) / "skills").exists())
                self.assertFalse((Path(child_env["CODEX_HOME"]) / "auth.json").exists())
                self.assertFalse((scratch / "AGENTS.md").exists())
                self.assertNotIn(project_root, scratch.parents)
                self.assertNotIn("OPENAI_API_KEY", child_env)
                self.assertNotIn("ANTHROPIC_API_KEY", child_env)
                return subprocess.CompletedProcess(
                    command, 0, json.dumps({"action": "observe"}), ""
                )

            injected = {
                "OPENAI_API_KEY": "fixture-openai-key",
                "ANTHROPIC_API_KEY": "fixture-anthropic-key",
                "OPENAI_BASE_URL": "https://fixture.invalid/v1",
                "ANTHROPIC_BASE_URL": "https://fixture.invalid/anthropic",
                "CODEX_MODEL": "fixture-model",
                "OPENAI_REASONING_EFFORT": "fixture-effort",
            }
            synthetic_environment = {
                "HOME": str(original_home),
                "PATH": "/fixture/bin",
                **injected,
            }
            with patch.dict(os.environ, synthetic_environment, clear=True):
                runner = NativePromptRunner(
                    host="codex",
                    selector="gpt-6.1-sol",
                    effort="medium",
                    native_context=_native_context(),
                    process_runner=transport,
                )
                result = runner(
                    request_id="fixture:environment",
                    user_prompt="fixture",
                    model="gpt-6.1-sol",
                    timeout=2,
                )
            self.assertEqual(original_auth.read_bytes(), original_auth_bytes)
            self.assertFalse(observed["scratch"].exists())

        self.assertEqual(result.returncode, 0)
        self.assertEqual(observed["env"]["PATH"], synthetic_environment["PATH"])
        for key in injected:
            self.assertNotIn(key, observed["env"], f"forbidden environment key survived: {key}")

    def test_source_bound_real_transport_links_dummy_auth_persists_refresh_and_uses_codex_overrides(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root / "bundle")
            original_home = root / "original-home"
            original_codex = original_home / ".codex"
            original_codex.mkdir(parents=True)
            original_auth = original_codex / "auth.json"
            original_auth_bytes = (
                b'{"access_token":"fixture-token","refresh_token":"fixture-refresh"}'
            )
            refreshed_auth_bytes = b'{"access_token":"fixture-token-rotated","refresh_token":"fixture-refresh-rotated"}'
            original_auth.write_bytes(original_auth_bytes)
            observed: dict[str, Any] = {}

            def run_host_spy(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                observed.update(kwargs)
                observed["command"] = list(command)
                scratch = Path(kwargs["cwd"]).resolve()
                observed["scratch"] = scratch
                child_env = kwargs["env"]
                for key in (
                    "HOME",
                    "CODEX_HOME",
                    "TMPDIR",
                    "TMP",
                    "TEMP",
                    "XDG_CONFIG_HOME",
                    "XDG_CACHE_HOME",
                    "XDG_DATA_HOME",
                ):
                    path = Path(child_env[key]).resolve()
                    self.assertTrue(
                        path == scratch or scratch in path.parents, (key, path, scratch)
                    )
                self.assertEqual(Path(child_env["CODEX_HOME"]).name, ".codex")
                auth_link = Path(child_env["CODEX_HOME"]) / "auth.json"
                self.assertTrue(auth_link.is_symlink())
                self.assertEqual(auth_link.resolve(), original_auth.resolve())
                self.assertEqual(auth_link.read_bytes(), original_auth_bytes)
                auth_link.write_bytes(refreshed_auth_bytes)
                expected_overrides = {
                    "project_doc_max_bytes=0",
                    "memories.use_memories=false",
                    "memories.generate_memories=false",
                    "cloud.skills.enabled=false",
                    'cli_auth_credentials_store="file"',
                }
                config_values = {
                    command[index + 1] for index, value in enumerate(command[:-1]) if value == "-c"
                }
                self.assertTrue(
                    expected_overrides <= config_values, (expected_overrides, config_values)
                )
                disable_values = {
                    command[index + 1]
                    for index, value in enumerate(command[:-1])
                    if value == "--disable"
                }
                self.assertTrue(
                    _CODEX_REQUIRED_ADDITIONAL_DISABLES <= disable_values,
                    (_CODEX_REQUIRED_ADDITIONAL_DISABLES, disable_values),
                )
                expected_additional_configs = {
                    "agents.enabled=false",
                    "tools.experimental_request_user_input.enabled=false",
                    "tools.update_plan.enabled=false",
                    'web_search="disabled"',
                }
                self.assertTrue(
                    expected_additional_configs <= config_values,
                    (expected_additional_configs, config_values),
                )
                catalog_setting = next(
                    value for value in config_values if value.startswith("model_catalog_json=")
                )
                catalog_path = Path(json.loads(catalog_setting.split("=", 1)[1]))
                observed["catalog_path"] = catalog_path
                self.assertEqual(catalog_path, scratch / "codex-models.json")
                admitted_bytes = catalog_path.read_bytes()
                self.assertEqual(admitted_bytes, _CODEX_DERIVED_CATALOG_PATH.read_bytes())
                self.assertEqual(
                    hashlib.sha256(admitted_bytes).hexdigest(), _CODEX_DERIVED_CATALOG_SHA256
                )
                output_last = Path(command[command.index("--output-last-message") + 1])
                payload = {"action": "observe", "request_id": "fixture:source-bound"}
                output_last.write_text(json.dumps(payload), encoding="utf-8")
                on_started = kwargs.get("on_started")
                if callable(on_started):
                    on_started()
                stdout = json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": json.dumps(payload)},
                    }
                )
                return subprocess.CompletedProcess(command, 0, stdout, "")

            runner = NativePromptRunner(
                host=bundle["row"]["target"]["host"],
                selector=bundle["row"]["target"]["selector"],
                effort=bundle["row"]["target"]["effort"],
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            with (
                patch.dict(
                    os.environ,
                    {"HOME": str(original_home), "PATH": "/fixture/bin"},
                    clear=False,
                ),
                patch.object(native_runtime, "run_host_process", side_effect=run_host_spy),
            ):
                response = runner(
                    request_id="fixture:source-bound",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model=bundle["row"]["target"]["selector"],
                    timeout=2,
                    representation=bundle["row"]["representation"],
                )
            self.assertEqual(response.returncode, 0)
            self.assertEqual(response.payload["action"], "observe")
            self.assertEqual(response.receipt["transport_kind"], "local_process")
            self.assertEqual(original_auth.read_bytes(), refreshed_auth_bytes)
            for key in (
                "HOME",
                "CODEX_HOME",
                "TMPDIR",
                "TMP",
                "TEMP",
                "XDG_CONFIG_HOME",
                "XDG_CACHE_HOME",
                "XDG_DATA_HOME",
            ):
                self.assertFalse(Path(observed["env"][key]).exists())
            self.assertFalse(observed["catalog_path"].exists())
            self.assertFalse(observed["scratch"].exists())

    def test_source_bound_real_transport_missing_auth_fails_before_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root / "bundle")
            original_home = root / "missing-auth-home"
            original_home.mkdir()
            calls: list[dict[str, Any]] = []

            def run_host_spy(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                calls.append({"command": list(command), **kwargs})
                return subprocess.CompletedProcess(command, 0, "{}", "")

            runner = NativePromptRunner(
                host=bundle["row"]["target"]["host"],
                selector=bundle["row"]["target"]["selector"],
                effort=bundle["row"]["target"]["effort"],
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            with (
                patch.dict(
                    os.environ,
                    {"HOME": str(original_home), "PATH": "/fixture/bin"},
                    clear=False,
                ),
                patch.object(native_runtime, "run_host_process", side_effect=run_host_spy),
            ):
                response = runner(
                    request_id="fixture:missing-auth",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model=bundle["row"]["target"]["selector"],
                    timeout=2,
                    representation=bundle["row"]["representation"],
                )
        self.assertNotEqual(response.returncode, 0)
        self.assertEqual(response.receipt.get("error"), "codex_auth_unavailable")
        self.assertFalse(response.receipt.get("dispatch_started", False))
        self.assertFalse(response.receipt.get("local_process_started", False))
        self.assertFalse(response.receipt.get("attempted", False))
        self.assertEqual(calls, [])

    def test_missing_or_tampered_static_catalog_fails_before_auth_or_dispatch(self) -> None:
        cases = ("missing", "tampered")
        for mutation in cases:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = _production_bundle(root / "bundle")
                original_home = root / "original-home"
                original_codex = original_home / ".codex"
                original_codex.mkdir(parents=True)
                original_auth = original_codex / "auth.json"
                auth_bytes = b'{"access_token":"fixture-token","refresh_token":"fixture-refresh"}'
                original_auth.write_bytes(auth_bytes)
                if mutation == "missing":
                    catalog_path = root / "missing-codex-models.json"
                    expected_error = "codex_tool_catalog_unavailable"
                else:
                    catalog_path = root / "tampered-codex-models.json"
                    catalog_path.write_bytes(b'{"models":[]}')
                    expected_error = "codex_tool_catalog_mismatch"
                symlink_calls: list[Path] = []
                original_symlink_to = Path.symlink_to

                def symlink_spy(
                    path: Path,
                    target: str | Path,
                    *args: Any,
                    symlink_calls: list[Path] = symlink_calls,
                    original_symlink_to: Any = original_symlink_to,
                    **kwargs: Any,
                ) -> None:
                    symlink_calls.append(path)
                    original_symlink_to(path, target, *args, **kwargs)

                calls: list[dict[str, Any]] = []

                def run_host_spy(
                    command: list[str],
                    *,
                    calls: list[dict[str, Any]] = calls,
                    **kwargs: Any,
                ) -> subprocess.CompletedProcess[str]:
                    calls.append({"command": list(command), **kwargs})
                    return subprocess.CompletedProcess(command, 0, "{}", "")

                runner = NativePromptRunner(
                    host=bundle["row"]["target"]["host"],
                    selector=bundle["row"]["target"]["selector"],
                    effort=bundle["row"]["target"]["effort"],
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                )
                with (
                    patch.dict(
                        os.environ,
                        {"HOME": str(original_home), "PATH": "/fixture/bin"},
                        clear=False,
                    ),
                    patch.object(native_runtime, "_CODEX_TOOL_CATALOG_PATH", catalog_path),
                    patch.object(Path, "symlink_to", autospec=True, side_effect=symlink_spy),
                    patch.object(native_runtime, "run_host_process", side_effect=run_host_spy),
                ):
                    response = runner(
                        request_id=f"fixture:catalog-{mutation}",
                        instruction="fixture prompt",
                        user_prompt="fixture prompt",
                        output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                        model=bundle["row"]["target"]["selector"],
                        timeout=2,
                        representation=bundle["row"]["representation"],
                    )
                self.assertNotEqual(response.returncode, 0)
                self.assertEqual(response.receipt.get("error"), expected_error)
                self.assertFalse(response.receipt.get("started", False))
                self.assertFalse(response.receipt.get("dispatch_started", False))
                self.assertFalse(response.receipt.get("local_process_started", False))
                self.assertFalse(response.receipt.get("attempted", False))
                self.assertEqual(calls, [])
                self.assertEqual(symlink_calls, [])
                self.assertEqual(original_auth.read_bytes(), auth_bytes)
                self.assertNotIn("env", response.receipt)


class RuntimeAccountingTests(unittest.TestCase):
    def test_twelve_observable_transport_attempts_are_counted_and_two_repairs_are_bounded(
        self,
    ) -> None:
        engine = _SimpleEngine()
        calls = 0

        def source(_context: dict[str, Any]) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            raise PromptTransportError("fixture transport failure")

        record = run_episode(
            engine=engine,
            proposal_source=source,
            model=ModelSpec("fixture-native", "general_rule"),
            limits=EpisodeLimits(180, 60, 12, 2),
            seed=20261024,
            clock=lambda: 0.0,
            config={"assignment_id": "fixture"},
            prompt="fixture",
        )
        self.assertFalse(record["success"])
        self.assertEqual(calls, 12)
        self.assertEqual(record["accounting"]["host_calls"], 12)
        self.assertEqual(record["accounting"]["transport_retries"], 11)
        self.assertEqual(len(record["evidence"]["calls"]), 12)
        self.assertEqual(len(engine.commits), 0)

        repair_calls = 0

        def bad_source(_context: dict[str, Any]) -> dict[str, Any]:
            return {"action": "not-legal"}

        def bad_repair(
            _context: dict[str, Any], _error: dict[str, Any], _attempt: int
        ) -> dict[str, Any]:
            nonlocal repair_calls
            repair_calls += 1
            return {"action": "still-not-legal"}

        repaired = run_episode(
            engine=_SimpleEngine(),
            proposal_source=bad_source,
            repair_source=bad_repair,
            model=ModelSpec("fixture-native", "general_rule"),
            limits=EpisodeLimits(180, 60, 12, 2),
            seed=20261024,
            clock=lambda: 0.0,
            config={"assignment_id": "fixture"},
            prompt="fixture",
        )
        self.assertFalse(repaired["success"])
        self.assertEqual(repair_calls, 2)
        self.assertEqual(repaired["accounting"]["repair_calls"], 2)
        self.assertEqual(repaired["accounting"]["host_calls"], 3)
        self.assertEqual(repaired["decisions"][0]["commit"], None)

    def test_invalid_or_late_output_never_commits(self) -> None:
        engine = _SimpleEngine()
        late = {"action": "finish"}
        clock_values = iter([0.0, 0.0, 0.0, 61.0])
        record = run_episode(
            engine=engine,
            proposal_source=lambda _context: late,
            model=ModelSpec("fixture-native", "general_rule"),
            limits=EpisodeLimits(180, 60, 12, 0),
            seed=20261024,
            clock=lambda: next(clock_values, 61.0),
            config={"assignment_id": "fixture"},
            prompt="fixture",
        )
        self.assertFalse(record["success"])
        self.assertEqual(engine.commits, [])
        self.assertIsNone(record["decisions"][0]["commit"])
        self.assertIn(record["failure_reason"], {"response_timeout", "wall_budget_exhausted"})

    def test_run_episode_native_context_rejection_happens_before_provider_or_commit(self) -> None:
        engine = _SimpleEngine()
        context = _native_context()
        context["hashes"]["input_manifest_sha256"] = "9" * 64

        def must_not_dispatch(_context: dict[str, Any]) -> dict[str, Any]:
            raise AssertionError("native admission must precede proposal dispatch")

        record = run_episode(
            engine=engine,
            proposal_source=must_not_dispatch,
            model=ModelSpec("fixture-native", "general_rule"),
            limits=EpisodeLimits(180, 60, 12, 2),
            seed=20261024,
            clock=lambda: 0.0,
            config={"assignment_id": "prep-quest-001"},
            prompt="fixture",
            native_context=context,
        )
        self.assertFalse(record["success"])
        self.assertEqual(record["accounting"]["host_calls"], 0)
        self.assertEqual(engine.commits, [])
        self.assertEqual(record["evidence"]["provenance"]["mode"], "rejected")


class GodotNormalizationTests(unittest.TestCase):
    def test_native_shaped_result_is_normalized_with_receipt_before_record_hash(self) -> None:
        from test_runtime_model_swap_godot import FakeEngineTransport

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)

            def prompt_runner(**kwargs: Any) -> NativePromptResult:
                request_id = kwargs["request_id"]
                return NativePromptResult(
                    0,
                    {
                        "request_id": request_id,
                        "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
                    },
                    {
                        "schema_version": "runtime-native-receipt/1",
                        "request_id": request_id,
                        "mode": "engineering_fixture",
                        "attempted": True,
                        "dispatch_started": True,
                    },
                )

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=prompt_runner,
                engine_runner=transport,
                godot_binary="fixture-godot",
                fixture_ref="fixture:godot",
                assignment_id="fixture-godot",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("fixture-native", "general_rule"),
                limits=EpisodeLimits(180, 60, 1, 0),
                seed=20261024,
                clock=lambda: 0.0,
                config={"assignment_id": "fixture-godot"},
                prompt="fixture prompt",
            )

        self.assertTrue(engine.prompt_receipts)
        self.assertEqual(record["evidence"]["prompt_receipts"], engine.prompt_receipts)
        self.assertTrue(all("request_id" in receipt for receipt in engine.prompt_receipts))
        expected_hash = hashlib.sha256(
            json.dumps(
                {key: value for key, value in record.items() if key != "record_hash"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(record["record_hash"], expected_hash)

    def test_godot_repeated_native_failures_finalize_twelve_rows_without_timeout_claims(
        self,
    ) -> None:
        from test_runtime_model_swap_godot import FakeEngineTransport

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            engine_transport = FakeEngineTransport(root)
            prompt_dispatches: list[dict[str, Any]] = []

            def failing_prompt(**kwargs: Any) -> NativePromptResult:
                prompt_dispatches.append(dict(kwargs))
                request_id = kwargs["request_id"]
                return NativePromptResult(
                    127,
                    {},
                    {
                        "schema_version": "runtime-native-receipt/1",
                        "request_id": request_id,
                        "mode": "engineering_fixture",
                        "attempted": True,
                        "dispatch_started": True,
                        "timed_out": False,
                        "error": "host_launch_failed",
                        "failure_kind": "transport",
                    },
                )

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=failing_prompt,
                engine_runner=engine_transport,
                godot_binary="fixture-godot",
                fixture_ref="fixture:godot",
                assignment_id="fixture-godot-failures",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("fixture-native", "general_rule"),
                limits=EpisodeLimits(180, 60, 12, 2),
                seed=20261024,
                clock=lambda: 0.0,
                config={"assignment_id": "fixture-godot-failures"},
                prompt="fixture prompt",
            )

        self.assertFalse(record["success"])
        self.assertEqual(len(prompt_dispatches), 12)
        self.assertEqual(len(engine.prompt_calls), 12)
        self.assertEqual(len(engine.prompt_receipts), 12)
        self.assertEqual(record["accounting"]["timeout_calls"], 0)
        self.assertEqual(len(record["evidence"]["prompt_invocations"]), 12)
        self.assertEqual(len(record["evidence"]["prompt_receipts"]), 12)
        self.assertEqual(
            [call for call in engine_transport.calls if call["mode"] == "experiment"], []
        )

    def test_nested_timeout_stops_after_one_dispatch_without_commit(self) -> None:
        from test_runtime_model_swap_godot import FakeEngineTransport

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt_dispatches: list[dict[str, Any]] = []

            def timeout_prompt(**kwargs: Any) -> NativePromptResult:
                prompt_dispatches.append(dict(kwargs))
                return NativePromptResult(
                    124,
                    {},
                    {
                        "schema_version": "runtime-native-receipt/1",
                        "request_id": kwargs["request_id"],
                        "mode": "engineering_fixture",
                        "attempted": True,
                        "dispatch_started": True,
                        "timed_out": True,
                        "error": "response_timeout",
                        "failure_kind": "timeout",
                    },
                )

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=timeout_prompt,
                engine_runner=FakeEngineTransport(root),
                godot_binary="fixture-godot",
                fixture_ref="fixture:godot",
                assignment_id="fixture-godot-timeout",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("fixture-native", "general_rule"),
                limits=EpisodeLimits(180, 60, 12, 2),
                seed=20261024,
                clock=lambda: 0.0,
                config={"assignment_id": "fixture-godot-timeout"},
                prompt="fixture prompt",
            )

        self.assertFalse(record["success"])
        self.assertEqual(len(prompt_dispatches), 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["accounting"]["timeout_calls"], 1)
        self.assertEqual(record["safety"]["committed_transitions"], 0)
        self.assertIsNone(record["decisions"][0]["commit"])

    def test_four_injected_tuple_prompts_are_not_native_processes_and_hash_completed_accounting(
        self,
    ) -> None:
        from test_runtime_model_swap_godot import POLICY_HASH, FakeEngineTransport

        class FourPromptGoalTransport(FakeEngineTransport):
            def __init__(self, root: Path) -> None:
                super().__init__(root)
                self.experiment_count = 0
                self.current_observation: dict[str, Any] | None = None
                self.current_state_ref: dict[str, Any] | None = None

            def __call__(self, **kwargs: Any) -> dict[str, Any]:
                payload = json.loads(Path(kwargs["input_path"]).read_text(encoding="utf-8"))
                setup = payload.get("setup_operations", [])
                if (
                    kwargs["mode"] == "bootstrap"
                    and setup
                    and setup[-1].get("operation") == "open_dialogue"
                ):
                    if self.current_observation is None or self.current_state_ref is None:
                        raise AssertionError("dialogue bootstrap had no canonical state")
                    observation = dict(self.current_observation)
                    observation["in_dialogue"] = True
                    state_ref = dict(self.current_state_ref)
                    trace = {
                        "passed": True,
                        "observation": observation,
                        "observations": [observation],
                        "state_ref": state_ref,
                        "final_state_ref": state_ref,
                        "policy_hash": POLICY_HASH,
                        "source_hashes": {"policy_hash": POLICY_HASH},
                        "actions": [],
                    }
                    self.current_observation = observation
                    self.current_state_ref = state_ref
                    return {
                        "status": "completed",
                        "trace": trace,
                        "latency_ms": 3.5,
                        "input_sha256_before": "a" * 64,
                        "input_sha256_after": "a" * 64,
                        "sidecar_path": str(kwargs["input_path"]) + ".bootstrap.json",
                    }

                if kwargs["mode"] == "experiment" and payload.get("mutations") == []:
                    steps = payload["decision"]["body"]["steps"]
                    operation = steps[0]["operation"]
                    if operation not in {"negotiate", "reveal_hint"}:
                        raise AssertionError(f"unexpected empty-mutation operation: {operation}")
                    initial = payload["initial_public_snapshot"]
                    before_observation = dict(initial["observation"])
                    before_ref = dict(initial["state_ref"])
                    self.experiment_count += 1
                    if operation == "negotiate":
                        after_observation = dict(before_observation)
                        after_ref = dict(before_ref)
                    else:
                        after_observation = dict(before_observation)
                        after_observation["goal_reached"] = True
                        after_revision = int(before_ref["revision"]) + 1
                        after_ref = {
                            "revision": after_revision,
                            "sha256": f"{after_revision:064x}",
                        }
                    action = {
                        "action_id": f"fake-action-{self.experiment_count}",
                        "operation": operation,
                        "status": "APPLIED",
                        "engine_revision": int(after_ref["revision"]),
                        "state_ref_before": before_ref,
                        "state_ref_after": after_ref,
                        "observation_before": before_observation,
                        "observation_after": after_observation,
                        "feedback": "applied",
                        "arguments": dict(steps[0].get("arguments", {})),
                    }
                    trace = {
                        "passed": True,
                        "observations": [after_observation],
                        "final_state_ref": after_ref,
                        "actions": [action],
                    }
                    if operation == "reveal_hint":
                        trace["goal_reached"] = True
                    self.next_revision = int(after_ref["revision"])
                    self.current_observation = after_observation
                    self.current_state_ref = dict(after_ref)
                    return {
                        "status": "completed",
                        "trace": trace,
                        "latency_ms": 3.5,
                        "input_sha256_before": "a" * 64,
                        "input_sha256_after": "a" * 64,
                        "sidecar_path": str(kwargs["input_path"]) + ".result.json",
                    }

                result = super().__call__(**kwargs)
                trace = result["trace"]
                if kwargs["mode"] == "bootstrap":
                    self.current_observation = dict(trace["observation"])
                    self.current_state_ref = dict(trace["state_ref"])
                    return result

                self.experiment_count += 1
                action = trace["actions"][0]
                observation = dict(trace["observations"][-1])
                if action["operation"] == "install_lens":
                    observation["tide_lead_authorized"] = True
                action["observation_after"] = observation
                trace["observations"] = [observation]
                self.current_observation = observation
                self.current_state_ref = dict(trace["final_state_ref"])
                return result

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            engine_transport = FourPromptGoalTransport(root)
            prompt_dispatches: list[dict[str, Any]] = []

            def tuple_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                prompt_dispatches.append(dict(kwargs))
                return 0, {
                    "request_id": kwargs["request_id"],
                    "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
                }

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=tuple_prompt,
                engine_runner=engine_transport,
                godot_binary="fixture-godot",
                fixture_ref="fixture:godot",
                assignment_id="fixture-godot-success",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("fixture-native", "general_rule"),
                limits=EpisodeLimits(180, 60, 12, 2),
                seed=20261024,
                clock=lambda: 0.0,
                config={"assignment_id": "fixture-godot-success"},
                prompt="fixture prompt",
            )

        self.assertTrue(record["success"])
        self.assertEqual(len(prompt_dispatches), 4)
        self.assertEqual(record["accounting"]["host_calls"], 4)
        self.assertEqual(len(record["evidence"]["prompt_invocations"]), 4)
        self.assertEqual(record["evidence"]["provider_process_launch_count"], 0)
        self.assertIsNone(record["evidence"]["provider_request_count"])
        self.assertEqual(record["safety"]["committed_transitions"], 3)
        self.assertEqual(
            record["final_state"]["observation"],
            {
                "lens_reachable": True,
                "lens_carried": True,
                "signal_restored": True,
                "tide_lead_authorized": True,
                "goal_reached": True,
                "in_dialogue": True,
            },
        )
        expected_hash = hashlib.sha256(
            json.dumps(
                {key: value for key, value in record.items() if key != "record_hash"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(record["record_hash"], expected_hash)


class AssignmentPlanTests(unittest.TestCase):
    def test_plan_is_deterministic_twenty_rows_one_quest_five_targets_two_views_two_repeats_and_zero_science(
        self,
    ) -> None:
        kwargs = {
            "quest_id": "sealed-lighthouse-v1",
            "seed": 20261024,
            "source_manifest_sha256": SOURCE_SHA,
            "input_manifest_sha256": INPUT_SHA,
            "panel": [
                {
                    "family_label": "GPT-6.1-SOL",
                    "host": "codex",
                    "selector": "gpt-6.1-sol",
                    "effort": "medium",
                },
                {
                    "family_label": "GPT-5.6-SOL",
                    "host": "codex",
                    "selector": "gpt-5.6-sol",
                    "effort": "medium",
                },
                {
                    "family_label": "Claude Opus 5.5",
                    "host": "claude_code",
                    "selector": "opus",
                    "effort": "medium",
                },
                {
                    "family_label": "Claude Sonnet 5.5",
                    "host": "claude_code",
                    "selector": "sonnet",
                    "effort": "medium",
                },
                {
                    "family_label": "Gemini 3.8 Flash",
                    "host": "antigravity",
                    "selector": "gemini-3.8-flash-medium",
                    "effort": "medium",
                },
            ],
        }
        first = build_assignment_plan(**kwargs)
        second = build_assignment_plan(**kwargs)
        self.assertEqual(first, second)
        self.assertEqual(first["schema_version"], "runtime-model-swap/assignment-plan/1")
        self.assertEqual(first["status"], "planned")
        self.assertEqual(first["quest_id"], "sealed-lighthouse-v1")
        self.assertEqual(first["seed"], 20261024)
        self.assertEqual(len(first["rows"]), 20)
        self.assertEqual(
            first["counts"], {"quests": 1, "targets": 5, "representations": 2, "repeats": 2}
        )
        self.assertEqual(first["scientific"]["assigned"], 0)
        self.assertEqual(first["scientific"]["executed"], 0)
        self.assertFalse(first["scientific"]["eligible"])
        self.assertEqual({row["quest_id"] for row in first["rows"]}, {"sealed-lighthouse-v1"})
        self.assertEqual(
            {row["representation"] for row in first["rows"]}, {"general_rule", "ontology"}
        )
        self.assertEqual({row["repeat"] for row in first["rows"]}, {1, 2})
        self.assertEqual(
            {row["target"]["family_label"] for row in first["rows"]},
            {item["family_label"] for item in kwargs["panel"]},
        )
        self.assertTrue(all(row["reset"] is True for row in first["rows"]))

    def test_plan_rejects_wrong_panel_cardinality_identity_and_manifest_hashes(self) -> None:
        panel = [
            {
                "family_label": "GPT-6.1-SOL",
                "host": "codex",
                "selector": "gpt-6.1-sol",
                "effort": "medium",
            },
            {
                "family_label": "GPT-5.6-SOL",
                "host": "codex",
                "selector": "gpt-5.6-sol",
                "effort": "medium",
            },
            {
                "family_label": "Claude Opus 5.5",
                "host": "claude_code",
                "selector": "opus",
                "effort": "medium",
            },
            {
                "family_label": "Claude Sonnet 5.5",
                "host": "claude_code",
                "selector": "sonnet",
                "effort": "medium",
            },
            {
                "family_label": "Gemini 3.8 Flash",
                "host": "antigravity",
                "selector": "gemini-3.8-flash-medium",
                "effort": "medium",
            },
        ]
        cases = [
            ("empty", [], SOURCE_SHA, INPUT_SHA),
            ("four-target", panel[:4], SOURCE_SHA, INPUT_SHA),
            ("duplicate-target", [panel[0]] * 5, SOURCE_SHA, INPUT_SHA),
            (
                "mismatched-host-selector",
                [*panel[:1], {**panel[1], "host": "claude_code"}, *panel[2:]],
                SOURCE_SHA,
                INPUT_SHA,
            ),
            ("invalid-source-hash", panel, "not-a-sha256", INPUT_SHA),
            ("invalid-input-hash", panel, SOURCE_SHA, "d" * 63),
        ]
        for name, candidate, source_hash, input_hash in cases:
            with self.subTest(name=name), self.assertRaises(ValueError):
                build_assignment_plan(
                    quest_id="sealed-lighthouse-v1",
                    seed=20261024,
                    source_manifest_sha256=source_hash,
                    input_manifest_sha256=input_hash,
                    panel=candidate,
                )


class LocalProcessBoundaryTests(unittest.TestCase):
    def test_local_python_timeout_terminates_process_and_descendant_without_native_binary(
        self,
    ) -> None:
        child_script = (
            "import os,signal,sys,time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(30)"
        )
        parent_script = (
            "import os,signal,subprocess,sys,time; "
            "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "open(sys.argv[2], 'w').write(str(os.getpid())); "
            "subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[3]], "
            "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
            "time.sleep(30)"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            parent_pid = root / "parent.pid"
            child_pid = root / "child.pid"
            try:
                with self.assertRaises(subprocess.TimeoutExpired) as raised:
                    run_host_process(
                        [
                            sys.executable,
                            "-c",
                            parent_script,
                            child_script,
                            str(parent_pid),
                            str(child_pid),
                        ],
                        input="fixture",
                        cwd=directory,
                        timeout=0.1,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                self.assertIs(type(raised.exception), subprocess.TimeoutExpired)
                pids = [int(parent_pid.read_text()), int(child_pid.read_text())]
                probes = [("pid", pid, os.kill) for pid in pids]
                probes.append(("group", pids[0], os.killpg))
                # communicate() reaps the leader, not its adopted descendants.
                # Observe init's reaping within the existing 1s cleanup grace;
                # zombies still count as present until both PID and group ESRCH.
                deadline = time.monotonic() + 1.0
                while True:
                    remaining = []
                    for kind, pid, probe in probes:
                        try:
                            probe(pid, 0)
                        except ProcessLookupError:
                            continue
                        remaining.append((kind, pid))
                    if not remaining:
                        self.assertLessEqual(time.monotonic(), deadline)
                        break
                    remaining_seconds = deadline - time.monotonic()
                    if remaining_seconds <= 0:
                        self.fail(f"timed-out processes or group remain present: {remaining}")
                    time.sleep(min(0.005, remaining_seconds))
            finally:
                if parent_pid.exists():
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(int(parent_pid.read_text()), signal.SIGKILL)

    def test_local_python_success_returns_stdout_stderr_and_exit_code(self) -> None:
        script = "import sys; print('stdout fixture'); print('stderr fixture', file=sys.stderr); sys.exit(3)"
        with tempfile.TemporaryDirectory() as directory:
            result = run_host_process(
                [sys.executable, "-c", script],
                input="fixture",
                cwd=directory,
                timeout=2.0,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, "stdout fixture\n")
        self.assertEqual(result.stderr, "stderr fixture\n")


class NativeCliContractTests(unittest.TestCase):
    def test_cli_success_uses_success_and_engineering_status_not_record_status(self) -> None:
        result = {
            "status": "failure",
            "success": True,
            "engineering_status": "PASS",
            "scientific": {"assigned": 0, "executed": 0, "eligible": False},
        }
        output = io.StringIO()
        with (
            patch.object(native_cli, "_fixture", return_value=result),
            contextlib.redirect_stdout(output),
        ):
            code = native_cli.main(
                [
                    "--engineering-fixture",
                    "--native-context",
                    "context.json",
                    "--fixture-transcript",
                    "transcript.json",
                    "--output-root",
                    "outputs",
                ]
            )
        self.assertEqual(code, 0)

    def test_native_without_trusted_activation_exits_before_context_or_engine_reads(self) -> None:
        output = io.StringIO()
        with (
            patch.object(native_cli, "_load_json", side_effect=AssertionError("context read")),
            patch.object(
                native_cli, "_manifest_receipt", side_effect=AssertionError("manifest read")
            ),
            patch.object(native_cli, "run_episode", side_effect=AssertionError("engine run")),
            contextlib.redirect_stdout(output),
        ):
            code = native_cli.main(
                ["--native", "--native-context", "/definitely/missing/trap-context.json"],
                trusted_activation=None,
            )
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(code, 2)
        self.assertIn("trusted_activation_missing", payload["failure_reason"])

    def test_manifest_receipt_exclusions_are_not_evidence_of_included_private_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "publicity": {"status": "verified"},
                        "excluded_categories": ["private", "account", "credential"],
                    }
                ),
                encoding="utf-8",
            )
            receipt = native_cli._manifest_receipt(path, kind="input", source_root=root)
        self.assertEqual(receipt["status"], "verified")

    def test_manifest_receipt_rejects_explicitly_included_forbidden_categories(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "publicity": {"status": "verified"},
                        "included_categories": ["public_prompt", "private"],
                    }
                ),
                encoding="utf-8",
            )
            receipt = native_cli._manifest_receipt(path, kind="input", source_root=root)
        self.assertEqual(receipt["status"], "unresolved")

    def test_check_requires_manifest_bindings_to_match_admission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context_path = root / "context.json"
            source_path = root / "source.json"
            input_path = root / "input.json"
            context_path.write_text(json.dumps(_native_context()), encoding="utf-8")
            source_path.write_text(
                json.dumps({"publicity": {"status": "verified"}}), encoding="utf-8"
            )
            input_path.write_text(
                json.dumps({"publicity": {"status": "verified"}}), encoding="utf-8"
            )
            args = native_cli.parse_args(
                [
                    "--check-only",
                    "--native-context",
                    str(context_path),
                    "--source-root",
                    str(root),
                    "--source-manifest",
                    str(source_path),
                    "--input-manifest",
                    str(input_path),
                    "--prompt",
                    "fixture prompt",
                ]
            )
            result = native_cli._check(args)
        self.assertEqual(result["status"], "blocked")

    def test_fixture_rejects_transcript_host_mismatch_before_engine_setup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context_path = root / "context.json"
            transcript_path = root / "transcript.json"
            project = root / "project"
            project.mkdir()
            context_path.write_text(
                json.dumps(_native_context(mode="engineering_fixture")), encoding="utf-8"
            )
            transcript_path.write_text(
                json.dumps(
                    {
                        "schema_version": "runtime-native-fixture-transcript/1",
                        "host": "claude_code",
                        "responses": [{"payload": {"action": "observe"}}],
                    }
                ),
                encoding="utf-8",
            )
            args = native_cli.parse_args(
                [
                    "--engineering-fixture",
                    "--native-context",
                    str(context_path),
                    "--source-root",
                    str(root),
                    "--fixture-transcript",
                    str(transcript_path),
                    "--output-root",
                    str(root / "outputs"),
                    "--project",
                    str(project),
                ]
            )
            with (
                patch.object(
                    native_cli,
                    "run_episode",
                    return_value={
                        "status": "failure",
                        "success": False,
                        "engineering_status": "FIX",
                    },
                ),
                self.assertRaisesRegex(ValueError, "transcript host"),
            ):
                native_cli._fixture(args, native=False)

    def test_cli_malformed_or_non_object_context_fails_closed_without_output_or_provider_activity(
        self,
    ) -> None:
        for name, raw in (("malformed", "{not-json"), ("non-object", "[]")):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context_path = root / "context.json"
                context_path.write_text(raw, encoding="utf-8")
                output_root = root / "outputs"
                output = io.StringIO()
                with (
                    patch.object(native_cli, "run_episode") as run_episode,
                    contextlib.redirect_stdout(output),
                ):
                    code = native_cli.main(
                        [
                            "--engineering-fixture",
                            "--native-context",
                            str(context_path),
                            "--fixture-transcript",
                            str(root / "transcript.json"),
                            "--output-root",
                            str(output_root),
                        ]
                    )
                payload = json.loads(output.getvalue())
                self.assertEqual(code, 2)
                self.assertEqual(payload["status"], "blocked")
                self.assertEqual(
                    payload["scientific"], {"assigned": 0, "executed": 0, "eligible": False}
                )
                self.assertFalse(output_root.exists())
                run_episode.assert_not_called()

    def test_cli_malformed_or_non_object_manifest_fails_closed_with_structured_exit2(self) -> None:
        cases = (("source", "{not-json"), ("input", "[]"))
        for kind, raw in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                context_path = root / "context.json"
                context_path.write_text(json.dumps(_native_context()), encoding="utf-8")
                source_path = root / "source.json"
                input_path = root / "input.json"
                source_path.write_text(
                    raw if kind == "source" else json.dumps({"publicity": {"status": "verified"}}),
                    encoding="utf-8",
                )
                input_path.write_text(
                    raw if kind == "input" else json.dumps({"publicity": {"status": "verified"}}),
                    encoding="utf-8",
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = native_cli.main(
                        [
                            "--check-only",
                            "--native-context",
                            str(context_path),
                            "--source-manifest",
                            str(source_path),
                            "--input-manifest",
                            str(input_path),
                        ]
                    )
                payload = json.loads(output.getvalue())
                self.assertEqual(code, 2)
                self.assertEqual(payload["status"], "blocked")
                self.assertEqual(payload["scientific"]["assigned"], 0)
                self.assertFalse(payload["scientific"]["eligible"])

    def test_cli_modes_require_explicit_inputs_and_never_fall_through_to_execution(self) -> None:
        cases = (
            (["--plan"], "plan_requires_source_and_input_manifest_hashes"),
            (["--check-only"], "check_only_requires_native_context"),
            (["--engineering-fixture"], "execution_requires_native_context"),
        )
        for argv, reason in cases:
            with self.subTest(reason=reason):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = native_cli.main(argv)
                payload = json.loads(output.getvalue())
                self.assertEqual(code, 2)
                self.assertEqual(payload["status"], "blocked")
                self.assertIn(reason, payload["failure_reason"])
                self.assertEqual(payload["scientific"]["assigned"], 0)
                self.assertFalse(payload["scientific"]["eligible"])

    def test_native_authority_rejection_precedes_output_project_and_provider_activity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = _native_context(mode="native")
            context["authority"]["native_activation"] = False
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            source_path = root / "source.json"
            input_path = root / "input.json"
            source_payload = {"publicity": {"status": "verified"}}
            input_payload = {"publicity": {"status": "verified"}}
            source_path.write_text(json.dumps(source_payload), encoding="utf-8")
            input_path.write_text(json.dumps(input_payload), encoding="utf-8")
            source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            input_digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
            context["hashes"].update(
                source_manifest_sha256=source_digest,
                input_manifest_sha256=input_digest,
            )
            context["bound_files"]["source_manifest"]["sha256"] = source_digest
            context["bound_files"]["input_manifest"]["sha256"] = input_digest
            context_path.write_text(json.dumps(context), encoding="utf-8")
            output_root = root / "outputs"
            project = root / "project"
            project.mkdir()
            output = io.StringIO()
            with (
                patch.object(
                    native_cli,
                    "run_episode",
                    return_value={"status": "failure", "success": False},
                ) as run_episode,
                contextlib.redirect_stdout(output),
            ):
                code = native_cli.main(
                    [
                        "--native",
                        "--native-context",
                        str(context_path),
                        "--source-manifest",
                        str(source_path),
                        "--input-manifest",
                        str(input_path),
                        "--output-root",
                        str(output_root),
                        "--project",
                        str(project),
                    ]
                )
            payload = json.loads(output.getvalue())
            self.assertFalse(output_root.exists())
            project_entries = list(project.iterdir())
        self.assertEqual(code, 2)
        self.assertEqual(payload["status"], "blocked")
        run_episode.assert_not_called()
        self.assertEqual(project_entries, [])

    def test_check_reports_future_native_denominator_unassigned_and_ineligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            context = _native_context()
            source_path = root / "source.json"
            input_path = root / "input.json"
            source_path.write_text(
                json.dumps({"publicity": {"status": "verified"}}), encoding="utf-8"
            )
            input_path.write_text(
                json.dumps({"publicity": {"status": "verified"}}), encoding="utf-8"
            )
            source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            input_digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
            context["hashes"].update(
                source_manifest_sha256=source_digest,
                input_manifest_sha256=input_digest,
            )
            context["bound_files"]["source_manifest"]["sha256"] = source_digest
            context["bound_files"]["input_manifest"]["sha256"] = input_digest
            context_path = root / "context.json"
            context_path.write_text(json.dumps(context), encoding="utf-8")
            args = native_cli.parse_args(
                [
                    "--check-only",
                    "--native-context",
                    str(context_path),
                    "--source-root",
                    str(root),
                    "--source-manifest",
                    str(source_path),
                    "--input-manifest",
                    str(input_path),
                    "--prompt",
                    "fixture prompt",
                ]
            )
            result = native_cli._check(args)
        self.assertEqual(result["scientific"], {"assigned": 0, "executed": 0, "eligible": False})


class NativePlanAndUseTimeTests(unittest.TestCase):
    def test_loader_rejects_duplicate_missing_crossproduct_and_row_plan_drift(self) -> None:
        mutations = (
            "duplicate",
            "missing",
            "crossproduct-hole",
            "wrong-target",
            "quest",
            "seed",
            "reset",
            "order",
            "status",
            "scientific",
            "wrong-id",
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory))
                plan = json.loads(bundle["plan_path"].read_text(encoding="utf-8"))
                rows = [dict(row) for row in plan["rows"]]
                if mutation == "duplicate":
                    rows[-1] = dict(rows[0])
                elif mutation == "missing":
                    rows.pop()
                elif mutation == "crossproduct-hole":
                    different_index = next(
                        index
                        for index, row in enumerate(rows)
                        if row["representation"] != rows[0]["representation"]
                    )
                    rows[different_index]["representation"] = rows[0]["representation"]
                elif mutation == "wrong-target":
                    rows[0]["target"] = {**rows[0]["target"], "selector": "wrong-selector"}
                elif mutation == "quest":
                    plan["quest_id"] = "wrong-quest"
                    rows = [{**row, "quest_id": "wrong-quest"} for row in rows]
                elif mutation == "seed":
                    plan["seed"] = 7
                    rows = [{**row, "seed": 7} for row in rows]
                elif mutation == "reset":
                    rows[0]["reset"] = False
                elif mutation == "order":
                    rows.reverse()
                elif mutation == "status":
                    plan["status"] = "executed"
                elif mutation == "scientific":
                    plan["scientific"] = {"assigned": 1, "executed": 0, "eligible": True}
                elif mutation == "wrong-id":
                    rows[1]["planned_id"] = "wrong-planned-id"
                plan["rows"] = rows
                plan_bytes = _canonical_bytes(plan)
                bundle["plan_path"].write_bytes(plan_bytes)
                plan_sha = hashlib.sha256(plan_bytes).hexdigest()
                activation = json.loads(bundle["activation_path"].read_text(encoding="utf-8"))
                activation["plan"] = {**activation["plan"], "sha256": plan_sha}
                activation_bytes = _canonical_bytes(activation)
                bundle["activation_path"].write_bytes(activation_bytes)
                with self.assertRaises(ValueError):
                    load_pinned_native_activation(
                        activation_path=bundle["activation_path"],
                        activation_sha256=hashlib.sha256(activation_bytes).hexdigest(),
                        plan_path=bundle["plan_path"],
                        plan_sha256=plan_sha,
                        row_id=bundle["row"]["planned_id"],
                        purpose="test_simulation",
                        trust_root=bundle["trust_root"],
                        source_root=bundle["source_root"],
                    )

    def test_context_row_override_and_pinned_evidence_digest_mismatch_reject_at_admission(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _production_bundle(Path(directory))
            context = json.loads(json.dumps(bundle["context"]))
            context["model"]["selector"] = "wrong-selector"
            result = validate_native_context(
                context,
                model=_model(bundle["context"]),
                config=_production_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertFalse(result["ready"])
            self.assertTrue(
                any(
                    "trusted_row" in reason or "model_selector" in reason
                    for reason in result["reasons"]
                )
            )

            activation = json.loads(bundle["activation_path"].read_text(encoding="utf-8"))
            activation["evidence_digests"]["public_input_receipt_sha256"] = "9" * 64
            path = bundle["trust_root"] / "evidence-mismatch.json"
            payload = _canonical_bytes(activation)
            path.write_bytes(payload)
            capability = load_pinned_native_activation(
                activation_path=path,
                activation_sha256=hashlib.sha256(payload).hexdigest(),
                plan_path=bundle["plan_path"],
                plan_sha256=bundle["plan_sha256"],
                row_id=bundle["row"]["planned_id"],
                purpose="production_native",
                origin="trusted_bootstrap",
                trust_root=bundle["trust_root"],
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
            )
            result = validate_native_context(
                bundle["context"],
                model=_model(bundle["context"]),
                config=_production_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=capability,
            )
        self.assertFalse(result["ready"])
        self.assertTrue(
            any("artifact" in reason or "evidence" in reason for reason in result["reasons"])
        )

    def test_activation_expiry_is_rechecked_at_invocation_and_blocks_transport(self) -> None:
        from datetime import UTC, datetime

        from nesy_game import runtime_model_swap_native as native_runtime

        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            current = datetime(2026, 10, 25, 12, tzinfo=UTC)

            def actual_admission_clock(_value: Any = None) -> datetime:
                return current

            transport = _HostFixtureTransport("codex", {"action": "observe"})
            runner = NativePromptRunner(
                host=bundle["row"]["target"]["host"],
                selector=bundle["row"]["target"]["selector"],
                effort=bundle["row"]["target"]["effort"],
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
                process_runner=transport,
                clock=lambda: 0.0,
            )
            with patch.object(native_runtime, "_now_value", side_effect=actual_admission_clock):
                admission = validate_native_context(
                    bundle["context"],
                    model=_model(bundle["context"]),
                    config=_simulation_config(bundle),
                    prompt="fixture prompt",
                    source_root=bundle["source_root"],
                    trusted_activation=bundle["capability"],
                )
                self.assertTrue(admission["ready"])
                accepted = runner(
                    request_id="fixture:unexpired",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model=bundle["row"]["target"]["selector"],
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )
                current = datetime(2026, 10, 27, tzinfo=UTC)
                rejected = runner(
                    request_id="fixture:expired",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model=bundle["row"]["target"]["selector"],
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )

        self.assertEqual(accepted.returncode, 0)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("trusted_activation_expired", rejected.receipt["admission"]["reasons"])
        self.assertFalse(rejected.receipt["attempted"])
        self.assertFalse(rejected.receipt["dispatch_started"])
        self.assertEqual(len(transport.calls), 1)


class NativeAccountingContractTests(unittest.TestCase):
    @staticmethod
    def _assert_record_hash(record: dict[str, Any]) -> None:
        expected = hashlib.sha256(
            json.dumps(
                {key: value for key, value in record.items() if key != "record_hash"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self = unittest.TestCase()
        self.assertEqual(record["record_hash"], expected)

    def test_admitted_production_engine_bootstrap_failure_is_assigned_not_executed(self) -> None:
        class BootstrapFailureEngine(_SimpleEngine):
            engine_error = "fixture bootstrap failure"

        with tempfile.TemporaryDirectory() as directory:
            bundle = _production_bundle(Path(directory))
            record = run_episode(
                engine=BootstrapFailureEngine(),
                proposal_source=lambda _context: {"action": "finish"},
                model=ModelSpec(
                    bundle["row"]["target"]["selector"],
                    bundle["row"]["representation"],
                    provider=bundle["row"]["target"]["host"],
                    offline=False,
                ),
                limits=EpisodeLimits(180, 60, 12, 2),
                seed=bundle["row"]["seed"],
                clock=lambda: 0.0,
                config=_production_config(bundle),
                prompt="fixture prompt",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
        self.assertEqual(record["scientific"], {"assigned": 1, "executed": 0, "eligible": True})
        self.assertEqual(record["evidence"]["provider_process_launch_count"], 0)
        self.assertTrue(record["accounting"]["denominator_eligible"])
        self._assert_record_hash(record)

    def test_file_not_found_local_start_is_not_an_actual_process_or_execution(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _production_bundle(Path(directory))
            runner = NativePromptRunner(
                host=bundle["row"]["target"]["host"],
                selector=bundle["row"]["target"]["selector"],
                effort=bundle["row"]["target"]["effort"],
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )

            class ReceiptEngine(_SimpleEngine):
                def __init__(self) -> None:
                    super().__init__()
                    self.prompt_receipts: list[dict[str, Any]] = []

                def propose(self, _context: dict[str, Any]) -> dict[str, str]:
                    response = runner(
                        request_id="fixture:file-not-found",
                        instruction="fixture prompt",
                        user_prompt="fixture prompt",
                        output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                        model=bundle["row"]["target"]["selector"],
                        timeout=1,
                    )
                    self.prompt_receipts.append(response.receipt)
                    return {"action": "not-legal"}

            with (
                patch(
                    "nesy_game.runtime_model_swap_native.validate_native_context",
                    return_value={
                        "ready": True,
                        "mode": "native",
                        "scientific_eligible": True,
                        "reasons": [],
                    },
                ),
                patch(
                    "nesy_game.runtime_model_swap_native.run_host_process",
                    side_effect=FileNotFoundError("fixture missing host"),
                ),
            ):
                engine = ReceiptEngine()
                record = run_episode(
                    engine=engine,
                    proposal_source=engine.propose,
                    model=ModelSpec(
                        bundle["row"]["target"]["selector"],
                        bundle["row"]["representation"],
                        provider=bundle["row"]["target"]["host"],
                        offline=False,
                    ),
                    limits=EpisodeLimits(180, 60, 1, 0),
                    seed=bundle["row"]["seed"],
                    clock=lambda: 0.0,
                    config=_production_config(bundle),
                    prompt="fixture prompt",
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                )
        self.assertEqual(engine.prompt_receipts[0]["local_process_started"], False)
        self.assertEqual(record["evidence"]["provider_process_launch_count"], 0)
        self.assertEqual(record["scientific"]["executed"], 0)
        self._assert_record_hash(record)

    def test_injected_dispatch_metadata_cannot_create_native_scientific_accounting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))

            class InjectedEngine(_SimpleEngine):
                def __init__(self) -> None:
                    super().__init__()
                    self.prompt_receipts = [
                        {
                            "schema_version": "runtime-native-receipt/1",
                            "mode": "engineering_fixture",
                            "transport_kind": "injected_fixture",
                            "runner_injected": True,
                            "dispatch_started": True,
                            "local_process_started": True,
                            "activation_sha256": bundle["capability"].activation_sha256,
                            "plan_sha256": bundle["capability"].plan_sha256,
                            "row_id": bundle["capability"].row_id,
                        }
                    ]

            engine = InjectedEngine()
            record = run_episode(
                engine=engine,
                proposal_source=lambda _context: {"action": "finish"},
                model=ModelSpec("fixture-native", "general_rule", provider="codex", offline=False),
                limits=EpisodeLimits(180, 60, 1, 0),
                seed=20261024,
                clock=lambda: 0.0,
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
        self.assertEqual(record["scientific"], {"assigned": 0, "executed": 0, "eligible": False})
        self.assertEqual(record["evidence"]["provider_process_launch_count"], 0)
        self.assertIsNone(record["evidence"]["provider_request_count"])
        self._assert_record_hash(record)
        self.assertFalse(record["accounting"]["denominator_eligible"])

    def test_native_prompt_result_malformed_or_refused_uses_two_repairs_not_transport_retries(
        self,
    ) -> None:
        result = NativePromptResult(
            6,
            {},
            {
                "mode": "engineering_fixture",
                "error": "provider_refused",
                "attempted": True,
                "dispatch_started": True,
            },
        )
        repairs = 0

        def repair(
            _context: dict[str, Any], _error: dict[str, Any], _attempt: int
        ) -> NativePromptResult:
            nonlocal repairs
            repairs += 1
            return result

        record = run_episode(
            engine=_SimpleEngine(),
            proposal_source=lambda _context: result,
            repair_source=repair,
            model=ModelSpec("fixture-native", "general_rule"),
            limits=EpisodeLimits(180, 60, 12, 2),
            seed=20261024,
            clock=lambda: 0.0,
            config={"assignment_id": "fixture"},
            prompt="fixture",
        )
        self.assertFalse(record["success"])
        self.assertEqual(repairs, 2)
        self.assertEqual(record["accounting"]["host_calls"], 3)
        self.assertEqual(record["accounting"]["transport_retries"], 0)
        self.assertIsNone(record["decisions"][0]["commit"])


class NativeProductionBootstrapTests(unittest.TestCase):
    def test_native_project_override_rejected_before_payload_read_or_runtime_effects(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            alternate_project = root / "alternate-godot-project"
            (alternate_project / "scripts").mkdir(parents=True)
            (alternate_project / "project.godot").write_text(
                '[application]\nconfig/name="changed-alternate"\n', encoding="utf-8"
            )
            (alternate_project / "scripts" / "changed.gd").write_text(
                "extends Node\n", encoding="utf-8"
            )
            args = _production_args(bundle, root, project=alternate_project)
            protected_payloads = {
                bundle["context_path"].resolve(),
                (bundle["source_root"] / "bound" / "prompt.txt").resolve(),
                (bundle["source_root"] / "bound" / "source_manifest.json").resolve(),
                (bundle["source_root"] / "bound" / "input_manifest.json").resolve(),
            }
            read_attempts: list[str] = []
            original_read_bytes = Path.read_bytes
            original_read_text = Path.read_text

            def guarded_read_bytes(
                path: Path,
                *read_args: Any,
                **read_kwargs: Any,
            ) -> bytes:
                if path.resolve() in protected_payloads:
                    read_attempts.append(f"bytes:{path}")
                    raise AssertionError("native payload was read")
                return original_read_bytes(path, *read_args, **read_kwargs)

            def guarded_read_text(
                path: Path,
                *read_args: Any,
                **read_kwargs: Any,
            ) -> str:
                if path.resolve() in protected_payloads:
                    read_attempts.append(f"text:{path}")
                    raise AssertionError("native payload was read")
                return original_read_text(path, *read_args, **read_kwargs)

            effects: list[str] = []
            with (
                patch.object(Path, "read_bytes", guarded_read_bytes),
                patch.object(Path, "read_text", guarded_read_text),
                patch.object(
                    native_cli,
                    "NativePromptRunner",
                    side_effect=lambda effects=effects, **_: effects.append("runner"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "GodotEpisodeEngine",
                    side_effect=lambda effects=effects, **_: effects.append("engine"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "stage_project",
                    side_effect=lambda *_, effects=effects: effects.append("stage"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_host_process",
                    side_effect=lambda *_, effects=effects, **__: effects.append("process"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_episode",
                    side_effect=lambda *_, effects=effects, **__: effects.append("episode"),
                    create=True,
                ),
                self.assertRaises(ValueError) as raised,
            ):
                _run_production_native(bundle, args)

        self.assertEqual(str(raised.exception), "native_project_override_rejected")
        self.assertEqual(read_attempts, [])
        self.assertEqual(effects, [])
        self.assertFalse((root / "outputs").exists())

    def test_native_runtime_source_root_mismatch_rejected_before_payload_read_or_runtime_effects(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            self.assertNotEqual(Path(native_cli.ROOT).resolve(), bundle["source_root"].resolve())
            args = _production_args(bundle, root)
            protected_payloads = {
                bundle["context_path"].resolve(),
                (bundle["source_root"] / "bound" / "prompt.txt").resolve(),
                (bundle["source_root"] / "bound" / "source_manifest.json").resolve(),
                (bundle["source_root"] / "bound" / "input_manifest.json").resolve(),
            }
            read_attempts: list[str] = []
            original_read_bytes = Path.read_bytes
            original_read_text = Path.read_text

            def guarded_read_bytes(
                path: Path,
                *read_args: Any,
                **read_kwargs: Any,
            ) -> bytes:
                if path.resolve() in protected_payloads:
                    read_attempts.append(f"bytes:{path}")
                    raise AssertionError("native payload was read")
                return original_read_bytes(path, *read_args, **read_kwargs)

            def guarded_read_text(
                path: Path,
                *read_args: Any,
                **read_kwargs: Any,
            ) -> str:
                if path.resolve() in protected_payloads:
                    read_attempts.append(f"text:{path}")
                    raise AssertionError("native payload was read")
                return original_read_text(path, *read_args, **read_kwargs)

            effects: list[str] = []
            with (
                patch.object(Path, "read_bytes", guarded_read_bytes),
                patch.object(Path, "read_text", guarded_read_text),
                patch.object(
                    native_cli,
                    "NativePromptRunner",
                    side_effect=lambda effects=effects, **_: effects.append("runner"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "GodotEpisodeEngine",
                    side_effect=lambda effects=effects, **_: effects.append("engine"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "stage_project",
                    side_effect=lambda *_, effects=effects: effects.append("stage"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_host_process",
                    side_effect=lambda *_, effects=effects, **__: effects.append("process"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_episode",
                    side_effect=lambda *_, effects=effects, **__: effects.append("episode"),
                    create=True,
                ),
                self.assertRaises(ValueError) as raised,
            ):
                native_cli._run_native(args, trusted_activation=bundle["capability"])

        self.assertEqual(str(raised.exception), "runtime_source_root_mismatch")
        self.assertEqual(read_attempts, [])
        self.assertEqual(effects, [])
        self.assertFalse((root / "outputs").exists())

    def test_trusted_production_bootstrap_derives_every_runtime_field_from_selected_row(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            row = bundle["row"]
            target = row["target"]
            args = native_cli.parse_args(
                [
                    "--native",
                    "--native-context",
                    str(bundle["context_path"]),
                    "--source-root",
                    str(bundle["source_root"]),
                    "--source-manifest",
                    str(bundle["source_root"] / "bound" / "source_manifest.json"),
                    "--input-manifest",
                    str(bundle["source_root"] / "bound" / "input_manifest.json"),
                    "--output-root",
                    str(root / "outputs"),
                    "--quest-id",
                    row["quest_id"],
                    "--seed",
                    str(row["seed"]),
                    "--fixture-ref",
                    row["fixture_id"],
                    "--prompt",
                    "fixture prompt",
                    "--godot-binary",
                    "fixture-godot",
                ]
            )
            runner_kwargs: dict[str, Any] = {}
            engine_kwargs: dict[str, Any] = {}
            episode_kwargs: dict[str, Any] = {}
            effects: list[str] = []
            stage_args: dict[str, Path] = {}
            engine_instances: list[Any] = []

            class FakeEngine:
                def propose(self, _context: dict[str, Any]) -> dict[str, str]:
                    return {"action": "finish"}

                def repair(
                    self, _context: dict[str, Any], _error: dict[str, Any], _attempt: int
                ) -> dict[str, str]:
                    return {"action": "finish"}

            def runner_factory(**kwargs: Any) -> object:
                runner_kwargs.update(kwargs)
                effects.append("runner")
                return object()

            def engine_factory(**kwargs: Any) -> FakeEngine:
                engine_kwargs.update(kwargs)
                effects.append("engine")
                engine = FakeEngine()
                engine_instances.append(engine)
                return engine

            def fake_stage(source: Path, destination: Path) -> None:
                stage_args.update(source=source, destination=destination)
                effects.append("stage")

            def fake_episode(**kwargs: Any) -> dict[str, Any]:
                episode_kwargs.update(kwargs)
                effects.append("episode")
                return {
                    "status": "failure",
                    "success": False,
                    "engineering_status": "NOT_PASS",
                    "scientific": {"assigned": 1, "executed": 0, "eligible": True},
                }

            with (
                patch.object(
                    native_cli, "NativePromptRunner", side_effect=runner_factory, create=True
                ),
                patch.object(
                    native_cli, "GodotEpisodeEngine", side_effect=engine_factory, create=True
                ),
                patch.object(native_cli, "stage_project", side_effect=fake_stage, create=True),
                patch.object(
                    native_cli,
                    "run_godot",
                    side_effect=AssertionError("native engine"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_host_process",
                    side_effect=AssertionError("native process"),
                    create=True,
                ),
                patch.object(native_cli, "run_episode", side_effect=fake_episode, create=True),
            ):
                result = _run_production_native(bundle, args)

        self.assertEqual(result["status"], "failure")
        self.assertEqual(effects, ["stage", "runner", "engine", "episode"])
        approved_source = (bundle["source_root"] / "game-track" / "godot").resolve()
        self.assertEqual(stage_args["source"], approved_source)
        self.assertEqual(stage_args["destination"], engine_kwargs["project"])
        self.assertEqual(stage_args["destination"].name, "project")
        self.assertTrue(stage_args["destination"].parent.name.startswith("runtime-native-project-"))
        self.assertNotEqual(stage_args["destination"], approved_source)
        self.assertEqual(len(engine_instances), 1)
        self.assertIs(episode_kwargs["engine"], engine_instances[0])
        self.assertIs(runner_kwargs["trusted_activation"], bundle["capability"])
        self.assertEqual(runner_kwargs["host"], target["host"])
        self.assertEqual(runner_kwargs["selector"], target["selector"])
        self.assertEqual(runner_kwargs["effort"], target["effort"])
        self.assertEqual(runner_kwargs["native_context"], bundle["context"])
        self.assertEqual(engine_kwargs["seed"], row["seed"])
        self.assertEqual(engine_kwargs["assignment_id"], row["assignment_id"])
        self.assertEqual(engine_kwargs["fixture_ref"], row["fixture_id"])
        model = episode_kwargs["model"]
        self.assertEqual(model.provider, target["host"])
        self.assertEqual(model.model_id, target["selector"])
        self.assertEqual(model.representation, row["representation"])
        self.assertFalse(model.offline)
        self.assertIs(episode_kwargs["trusted_activation"], bundle["capability"])
        self.assertIs(runner_kwargs["native_context"], episode_kwargs["native_context"])
        self.assertEqual(episode_kwargs["native_context"], bundle["context"])
        self.assertEqual(episode_kwargs["seed"], row["seed"])
        config = episode_kwargs["config"]
        expected = _production_config(bundle)
        for key, value in expected.items():
            self.assertEqual(config[key], value, key)
        self.assertEqual(config["quest_id"], row["quest_id"])
        self.assertEqual(config["repeat"], row["repeat"])
        self.assertTrue(config["reset"])
        self.assertEqual(config["fixture_id"], row["fixture_id"])
        self.assertEqual(config["oracle_sha256"], row["oracle_sha256"])
        self.assertEqual(
            config["output_schema_sha256"],
            bundle["activation"]["artifact_bindings"]["output_schema_sha256"],
        )

    def test_conflicting_cli_or_context_row_overrides_reject_before_runtime_effects(self) -> None:
        mutations = ("quest", "seed", "fixture", "context-selector")
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = _production_bundle(root)
                argv = [
                    "--native",
                    "--native-context",
                    str(bundle["context_path"]),
                    "--source-root",
                    str(bundle["source_root"]),
                    "--source-manifest",
                    str(bundle["source_root"] / "bound" / "source_manifest.json"),
                    "--input-manifest",
                    str(bundle["source_root"] / "bound" / "input_manifest.json"),
                    "--output-root",
                    str(root / "outputs"),
                    "--prompt",
                    "fixture prompt",
                ]
                context = bundle["context"]
                if mutation == "quest":
                    argv.extend(["--quest-id", "different-quest"])
                elif mutation == "seed":
                    argv.extend(["--seed", "7"])
                elif mutation == "fixture":
                    argv.extend(["--fixture-ref", "fixture:other"])
                else:
                    context = json.loads(json.dumps(context))
                    context["model"]["selector"] = "conflicting-selector"
                    bundle["context_path"].write_bytes(_canonical_bytes(context))
                args = native_cli.parse_args(argv)
                effects: list[str] = []
                with (
                    patch.object(
                        native_cli,
                        "NativePromptRunner",
                        side_effect=lambda effects=effects, **_: effects.append("runner"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "GodotEpisodeEngine",
                        side_effect=lambda effects=effects, **_: effects.append("engine"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "stage_project",
                        side_effect=lambda *_, effects=effects: effects.append("stage"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "run_episode",
                        side_effect=lambda effects=effects, **_: effects.append("episode"),
                        create=True,
                    ),
                    self.assertRaises(ValueError),
                ):
                    _run_production_native(bundle, args)
                self.assertEqual(effects, [])

    def test_cli_native_pre_read_guards_reject_private_context_prompt_and_manifest_paths(
        self,
    ) -> None:
        protected_segments = (
            "auth/manifest.json",
            "private/manifest.json",
            "raw/manifest.json",
            "wiki/manifest.json",
            ".env.json",
            "credential.key",
            "secret.crt",
            ".aws/credentials",
            ".config/private.json",
            ".gnupg/private.gpg",
            ".secrets/token.json",
            "llm-wiki/private.md",
            ".claude/settings.json",
            ".agents/agent.json",
            ".codex/auth.json",
            "account/private.json",
            "accounts/private.json",
        )
        cases = [
            (kind, relative)
            for kind in ("native-context", "bound-prompt", "source-manifest", "input-manifest")
            for relative in protected_segments
        ]
        for kind, relative in cases:
            with (
                self.subTest(kind=kind, relative=relative),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                bundle = _production_bundle(root)
                context = json.loads(json.dumps(bundle["context"]))
                denied = bundle["source_root"] / relative
                denied.parent.mkdir(parents=True, exist_ok=True)
                if kind == "native-context":
                    denied.write_bytes(bundle["context_path"].read_bytes())
                    args = _production_args(bundle, root, context_path=denied)
                elif kind == "bound-prompt":
                    denied.write_bytes(
                        (bundle["source_root"] / "bound" / "prompt.txt").read_bytes()
                    )
                    context["bound_files"]["prompt"]["path"] = relative
                    bundle["context_path"].write_bytes(_canonical_bytes(context))
                    args = _production_args(bundle, root)
                else:
                    manifest_name = (
                        "source_manifest" if kind == "source-manifest" else "input_manifest"
                    )
                    original = bundle["source_root"] / "bound" / f"{manifest_name}.json"
                    denied.write_bytes(original.read_bytes())
                    context["bound_files"][manifest_name]["path"] = relative
                    bundle["context_path"].write_bytes(_canonical_bytes(context))
                    args = _production_args(
                        bundle,
                        root,
                        source_manifest=denied if kind == "source-manifest" else None,
                        input_manifest=denied if kind == "input-manifest" else None,
                    )

                denied_resolved = denied.resolve()
                read_attempts: list[str] = []
                original_read_bytes = Path.read_bytes
                original_read_text = Path.read_text

                def guarded_read_bytes(
                    path: Path,
                    *read_args: Any,
                    denied_path: Path = denied_resolved,
                    attempts: list[str] = read_attempts,
                    original_reader: Any = original_read_bytes,
                    **read_kwargs: Any,
                ) -> bytes:
                    if path.resolve() == denied_path:
                        attempts.append("bytes")
                        raise AssertionError("forbidden CLI path was read")
                    return original_reader(path, *read_args, **read_kwargs)

                def guarded_read_text(
                    path: Path,
                    *read_args: Any,
                    denied_path: Path = denied_resolved,
                    attempts: list[str] = read_attempts,
                    original_reader: Any = original_read_text,
                    **read_kwargs: Any,
                ) -> str:
                    if path.resolve() == denied_path:
                        attempts.append("text")
                        raise AssertionError("forbidden CLI path was read")
                    return original_reader(path, *read_args, **read_kwargs)

                effects: list[str] = []
                with (
                    patch.object(Path, "read_bytes", guarded_read_bytes),
                    patch.object(Path, "read_text", guarded_read_text),
                    patch.object(
                        native_cli,
                        "NativePromptRunner",
                        side_effect=lambda effects=effects, **_: effects.append("runner"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "GodotEpisodeEngine",
                        side_effect=lambda effects=effects, **_: effects.append("engine"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "stage_project",
                        side_effect=lambda *_, effects=effects: effects.append("stage"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "run_host_process",
                        side_effect=lambda *_, effects=effects, **__: effects.append("process"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "run_episode",
                        side_effect=lambda *_, effects=effects, **__: effects.append("episode"),
                        create=True,
                    ),
                    self.assertRaises(ValueError),
                ):
                    _run_production_native(bundle, args)

                self.assertEqual(read_attempts, [])
                self.assertEqual(effects, [])
                self.assertFalse((root / "outputs").exists())

    def test_cli_native_pre_read_guard_rejects_outside_and_private_symlink_targets(self) -> None:
        for target_kind in ("outside", "private"):
            with self.subTest(target_kind=target_kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = _production_bundle(root)
                if target_kind == "outside":
                    target = root / "outside-context.json"
                else:
                    target = bundle["source_root"] / "private" / "private-context.json"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(bundle["context_path"].read_bytes())
                link = bundle["source_root"] / "bound" / "context-link.json"
                link.symlink_to(target)
                read_attempts: list[str] = []
                original_read_bytes = Path.read_bytes
                original_read_text = Path.read_text
                target_resolved = target.resolve()

                def guarded_read_bytes(
                    path: Path,
                    *read_args: Any,
                    target_path: Path = target_resolved,
                    attempts: list[str] = read_attempts,
                    original_reader: Any = original_read_bytes,
                    **read_kwargs: Any,
                ) -> bytes:
                    if path.resolve() == target_path:
                        attempts.append("bytes")
                        raise AssertionError("symlink target was read")
                    return original_reader(path, *read_args, **read_kwargs)

                def guarded_read_text(
                    path: Path,
                    *read_args: Any,
                    target_path: Path = target_resolved,
                    attempts: list[str] = read_attempts,
                    original_reader: Any = original_read_text,
                    **read_kwargs: Any,
                ) -> str:
                    if path.resolve() == target_path:
                        attempts.append("text")
                        raise AssertionError("symlink target was read")
                    return original_reader(path, *read_args, **read_kwargs)

                args = _production_args(bundle, root, context_path=link)
                effects: list[str] = []
                with (
                    patch.object(Path, "read_bytes", guarded_read_bytes),
                    patch.object(Path, "read_text", guarded_read_text),
                    patch.object(
                        native_cli,
                        "NativePromptRunner",
                        side_effect=lambda effects=effects, **_: effects.append("runner"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "GodotEpisodeEngine",
                        side_effect=lambda effects=effects, **_: effects.append("engine"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "stage_project",
                        side_effect=lambda *_, effects=effects: effects.append("stage"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "run_host_process",
                        side_effect=lambda *_, effects=effects, **__: effects.append("process"),
                        create=True,
                    ),
                    patch.object(
                        native_cli,
                        "run_episode",
                        side_effect=lambda *_, effects=effects, **__: effects.append("episode"),
                        create=True,
                    ),
                    self.assertRaisesRegex(ValueError, "path_escape|private_path_rejected"),
                ):
                    _run_production_native(bundle, args)
                self.assertEqual(read_attempts, [])
                self.assertEqual(effects, [])
                self.assertFalse((root / "outputs").exists())

    def test_cli_native_oversized_manifest_is_rejected_before_payload_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            oversized = bundle["source_root"] / "bound" / "oversized-source.json"
            with oversized.open("wb") as handle:
                handle.seek(MAX_BOUND_FILE_BYTES)
                handle.write(b"\0")
            self.assertEqual(oversized.stat().st_size, MAX_BOUND_FILE_BYTES + 1)
            context = json.loads(json.dumps(bundle["context"]))
            context["bound_files"]["source_manifest"]["path"] = "bound/oversized-source.json"
            bundle["context_path"].write_bytes(_canonical_bytes(context))
            args = _production_args(bundle, root, source_manifest=oversized)
            read_attempts: list[str] = []
            original_read_bytes = Path.read_bytes
            original_read_text = Path.read_text
            oversized_resolved = oversized.resolve()

            def guarded_read_bytes(
                path: Path,
                *read_args: Any,
                denied_path: Path = oversized_resolved,
                attempts: list[str] = read_attempts,
                original_reader: Any = original_read_bytes,
                **read_kwargs: Any,
            ) -> bytes:
                if path.resolve() == denied_path:
                    attempts.append("bytes")
                    raise AssertionError("oversized manifest payload was read")
                return original_reader(path, *read_args, **read_kwargs)

            def guarded_read_text(
                path: Path,
                *read_args: Any,
                denied_path: Path = oversized_resolved,
                attempts: list[str] = read_attempts,
                original_reader: Any = original_read_text,
                **read_kwargs: Any,
            ) -> str:
                if path.resolve() == denied_path:
                    attempts.append("text")
                    raise AssertionError("oversized manifest payload was read")
                return original_reader(path, *read_args, **read_kwargs)

            effects: list[str] = []
            with (
                patch.object(Path, "read_bytes", guarded_read_bytes),
                patch.object(Path, "read_text", guarded_read_text),
                patch.object(
                    native_cli,
                    "NativePromptRunner",
                    side_effect=lambda effects=effects, **_: effects.append("runner"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "GodotEpisodeEngine",
                    side_effect=lambda effects=effects, **_: effects.append("engine"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "stage_project",
                    side_effect=lambda *_, effects=effects: effects.append("stage"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_host_process",
                    side_effect=lambda *_, effects=effects, **__: effects.append("process"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_episode",
                    side_effect=lambda *_, effects=effects, **__: effects.append("episode"),
                    create=True,
                ),
                self.assertRaisesRegex(ValueError, "oversized|unreadable"),
            ):
                _run_production_native(bundle, args)
        self.assertEqual(read_attempts, [])
        self.assertEqual(effects, [])
        self.assertFalse((root / "outputs").exists())

    def test_cli_native_public_bound_paths_reach_injected_runtime_as_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            args = _production_args(bundle, root)
            runner_double = SimpleNamespace()
            engine_double = SimpleNamespace(
                propose=lambda _context: {"action": "finish"},
                repair=lambda _context, _error, _reason, _attempt: {"action": "finish"},
                prompt_receipts=[],
            )
            effects: list[str] = []
            stage_args: dict[str, Path] = {}
            engine_kwargs: dict[str, Any] = {}
            episode_kwargs: dict[str, Any] = {}

            def engine_factory(**kwargs: Any) -> object:
                engine_kwargs.update(kwargs)
                effects.append("engine")
                return engine_double

            def fake_stage(source: Path, destination: Path) -> None:
                stage_args.update(source=source, destination=destination)
                effects.append("stage")

            def fake_episode(**kwargs: Any) -> dict[str, Any]:
                episode_kwargs.update(kwargs)
                effects.append("episode")
                return {
                    "status": "failure",
                    "success": False,
                    "engineering_status": "NOT_PASS",
                    "scientific": {"assigned": 1, "executed": 0, "eligible": True},
                }

            with (
                patch.object(
                    native_cli,
                    "NativePromptRunner",
                    side_effect=lambda effects=effects, runner_double=runner_double, **_: (
                        effects.append("runner") or runner_double
                    ),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "GodotEpisodeEngine",
                    side_effect=engine_factory,
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "stage_project",
                    side_effect=fake_stage,
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_godot",
                    side_effect=AssertionError("native engine"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_host_process",
                    side_effect=AssertionError("provider process"),
                    create=True,
                ),
                patch.object(
                    native_cli,
                    "run_episode",
                    side_effect=fake_episode,
                    create=True,
                ),
            ):
                result = _run_production_native(bundle, args)
        self.assertEqual(effects, ["stage", "runner", "engine", "episode"])
        self.assertEqual(result["status"], "failure")
        approved_source = (bundle["source_root"] / "game-track" / "godot").resolve()
        self.assertEqual(stage_args["source"], approved_source)
        self.assertEqual(stage_args["destination"], engine_kwargs["project"])
        self.assertEqual(stage_args["destination"].name, "project")
        self.assertTrue(stage_args["destination"].parent.name.startswith("runtime-native-project-"))
        self.assertEqual(engine_kwargs["output_root"], (root / "outputs").resolve())
        self.assertIs(episode_kwargs["engine"], engine_double)
        self.assertIs(episode_kwargs["proposal_source"], engine_double.propose)
        self.assertIs(episode_kwargs["repair_source"], engine_double.repair)

    def test_cli_native_materializes_frozen_allowed_requests_before_episode_hashing(
        self,
    ) -> None:
        class ProposalEngine(_SimpleEngine):
            def __init__(self, **_kwargs: Any) -> None:
                super().__init__()
                self.proposal_contexts: list[dict[str, Any]] = []

            def propose(self, context: dict[str, Any]) -> dict[str, str]:
                self.proposal_contexts.append(context)
                return {"action": "finish"}

            def repair(
                self,
                _context: dict[str, Any],
                _error: dict[str, Any],
                _reason: str,
                _attempt: int,
            ) -> dict[str, str]:
                return {"action": "finish"}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            args = _production_args(bundle, root)
            engine_instances: list[ProposalEngine] = []

            def engine_factory(**kwargs: Any) -> ProposalEngine:
                engine = ProposalEngine(**kwargs)
                engine_instances.append(engine)
                return engine

            with (
                patch.object(native_cli, "stage_project", return_value=None, create=True),
                patch.object(
                    native_cli,
                    "GodotEpisodeEngine",
                    side_effect=engine_factory,
                    create=True,
                ),
            ):
                result = _run_production_native(bundle, args)

            episode_path = Path(result["output_root"]) / "episode.json"
            episode = json.loads(episode_path.read_text(encoding="utf-8"))

        frozen_requests = bundle["capability"].activation["artifact_bindings"]["allowed_requests"]
        expected_requests = [dict(row) for row in frozen_requests]
        expected_requests_sha256 = hashlib.sha256(_canonical_bytes(expected_requests)).hexdigest()
        self.assertEqual(expected_requests_sha256, bundle["allowed_requests_sha256"])
        self.assertEqual(episode["config"]["allowed_requests"], expected_requests)
        self.assertEqual(episode["config"]["allowed_requests_sha256"], expected_requests_sha256)
        expected_config_hash = hashlib.sha256(_canonical_bytes(episode["config"])).hexdigest()
        self.assertEqual(episode["evidence"]["config_hash"], expected_config_hash)

        self.assertEqual(result["status"], "success")
        self.assertTrue(result["success"])
        self.assertEqual(len(engine_instances), 1)
        self.assertEqual(len(engine_instances[0].proposal_contexts), 1)
        self.assertEqual(
            engine_instances[0].proposal_contexts[0]["logical_request_id"], "decision-0"
        )
        self.assertEqual(episode["decisions"][0]["validation"]["valid"], True)
        self.assertEqual(engine_instances[0].commits, [{"action": "finish"}])
        self.assertEqual(episode["evidence"]["native_context"]["ready"], True)
        self.assertEqual(episode["scientific"], {"assigned": 1, "executed": 0, "eligible": True})
        self.assertTrue(episode["accounting"]["denominator_eligible"])

    def test_run_episode_late_output_write_failure_raises_with_finalized_native_record(
        self,
    ) -> None:
        from nesy_game.runtime_model_swap import EpisodePersistenceError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            output_path = root / "episode.json"
            original_open = Path.open
            transport = _HostFixtureTransport("codex", {"action": "finish"})

            def fail_final_write(path: Path, *open_args: Any, **open_kwargs: Any) -> Any:
                mode = open_args[0] if open_args else open_kwargs.get("mode", "r")
                if path.resolve() == output_path.resolve() and mode == "x":
                    raise OSError("fixture final output write failed")
                return original_open(path, *open_args, **open_kwargs)

            with (
                patch.object(Path, "open", fail_final_write),
                self.assertRaises(EpisodePersistenceError) as raised,
            ):
                _record, _ = _run_trusted_native_episode(
                    bundle, output_path=output_path, transport=transport
                )

        record = raised.exception.record
        self.assertEqual(record["scientific"], {"assigned": 1, "executed": 1, "eligible": True})
        self.assertEqual(record["evidence"]["provider_process_launch_count"], 1)
        self.assertTrue(record["evidence"]["prompt_receipts"])
        self.assertTrue(record["evidence"]["raw_proposals"])
        self.assertTrue(record["evidence"]["validation"])
        self.assertTrue(record["evidence"]["commit"])
        self.assertEqual(record["safety"]["status"], "PASS")
        self.assertTrue(record["semantic_replay"]["valid"])
        expected_hash = hashlib.sha256(
            json.dumps(
                {key: value for key, value in record.items() if key != "record_hash"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        self.assertEqual(record["record_hash"], expected_hash)
        self.assertEqual(len(transport.calls), 1)

    def test_cli_persistence_failure_preserves_full_record_and_known_execution_summary(
        self,
    ) -> None:
        from nesy_game.runtime_model_swap import EpisodePersistenceError

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            episode_record, _transport = _run_trusted_native_episode(bundle)
            persistence_error = EpisodePersistenceError(
                "fixture final output write failed", record=episode_record
            )
            args = _production_args(bundle, root)
            with (
                patch.object(native_cli, "stage_project", return_value=None, create=True),
                patch.object(
                    native_cli, "NativePromptRunner", return_value=SimpleNamespace(), create=True
                ),
                patch.object(
                    native_cli, "GodotEpisodeEngine", return_value=_cli_engine_double(), create=True
                ),
                patch.object(native_cli, "run_episode", side_effect=persistence_error, create=True),
            ):
                result = _run_production_native(bundle, args)

        self.assertFalse(result["success"])
        self.assertEqual(result["episode_record"], episode_record)
        self.assertEqual(result["scientific"], episode_record["scientific"])
        self.assertEqual(result["failure_artifact"]["denominator"], result["scientific"])

    def test_cli_cleanup_failure_preserves_returned_record_and_known_execution_summary(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            episode_record, _transport = _run_trusted_native_episode(bundle)
            args = _production_args(bundle, root)
            with (
                patch.object(native_cli, "stage_project", return_value=None, create=True),
                patch.object(
                    native_cli, "NativePromptRunner", return_value=SimpleNamespace(), create=True
                ),
                patch.object(
                    native_cli, "GodotEpisodeEngine", return_value=_cli_engine_double(), create=True
                ),
                patch.object(native_cli, "run_episode", return_value=episode_record, create=True),
                patch.object(
                    native_cli.tempfile.TemporaryDirectory,
                    "__exit__",
                    side_effect=OSError("fixture cleanup failed"),
                ),
            ):
                result = _run_production_native(bundle, args)

        self.assertFalse(result["success"])
        self.assertEqual(result["episode_record"], episode_record)
        self.assertEqual(result["scientific"], episode_record["scientific"])
        self.assertEqual(result["failure_artifact"]["denominator"], result["scientific"])
        self.assertEqual(result["failure_artifact"]["phase"], "cleanup")

    def test_cli_episode_exception_without_record_reports_unknown_execution_not_zero(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            args = _production_args(bundle, root)
            with (
                patch.object(native_cli, "stage_project", return_value=None, create=True),
                patch.object(
                    native_cli, "NativePromptRunner", return_value=SimpleNamespace(), create=True
                ),
                patch.object(
                    native_cli, "GodotEpisodeEngine", return_value=_cli_engine_double(), create=True
                ),
                patch.object(
                    native_cli,
                    "run_episode",
                    side_effect=RuntimeError("fixture opaque episode failure"),
                    create=True,
                ),
            ):
                result = _run_production_native(bundle, args)

        self.assertFalse(result["success"])
        self.assertIsNone(result.get("episode_record"))
        self.assertEqual(result["scientific"], {"assigned": 1, "executed": None, "eligible": True})
        self.assertEqual(result["failure_artifact"]["denominator"], result["scientific"])
        self.assertEqual(
            result["failure_artifact"]["error"],
            "RuntimeError:fixture opaque episode failure",
        )

    def test_cli_episode_exception_without_record_uses_observed_trust_bound_start(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root)
            episode_record, _transport = _run_trusted_native_episode(bundle)
            observed_receipts = episode_record["evidence"]["prompt_receipts"]
            args = _production_args(bundle, root)
            engine_double = _cli_engine_double()
            engine_double.prompt_receipts = observed_receipts
            with (
                patch.object(native_cli, "stage_project", return_value=None, create=True),
                patch.object(
                    native_cli, "NativePromptRunner", return_value=SimpleNamespace(), create=True
                ),
                patch.object(
                    native_cli, "GodotEpisodeEngine", return_value=engine_double, create=True
                ),
                patch.object(
                    native_cli,
                    "run_episode",
                    side_effect=RuntimeError("fixture opaque episode failure"),
                    create=True,
                ),
            ):
                result = _run_production_native(bundle, args)

        self.assertFalse(result["success"])
        self.assertIsNone(result.get("episode_record"))
        self.assertEqual(result["observed_prompt_receipts"], observed_receipts)
        self.assertEqual(result["scientific"], {"assigned": 1, "executed": 1, "eligible": True})
        self.assertEqual(
            result["failure_artifact"]["execution_evidence"],
            "observed_trust_bound_start",
        )
        self.assertEqual(
            result["failure_artifact"]["error"],
            "RuntimeError:fixture opaque episode failure",
        )
        self.assertEqual(result["failure_artifact"]["denominator"], result["scientific"])


class ExtensionAssignmentPlanTests(unittest.TestCase):
    def test_extension_plan_is_exact_five_target_twenty_row_crossproduct(self) -> None:
        plan = build_extension_assignment_plan(
            quest_id="sealed-lighthouse-v1",
            seed=20261024,
            source_manifest_sha256=SOURCE_SHA,
            input_manifest_sha256=INPUT_SHA,
        )
        self.assertEqual(plan["schema_version"], EXTENSION_ASSIGNMENT_PLAN_SCHEMA)
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(EXTENSION_ACTIVATION_SCHEMA, "runtime-native-activation/3")
        self.assertEqual(len(plan["rows"]), 20)
        self.assertEqual(
            plan["counts"], {"quests": 1, "targets": 5, "representations": 2, "repeats": 2}
        )
        self.assertEqual(
            [row["target"]["selector"] for row in plan["rows"][::4]],
            list(EXTENSION_CODEX_TARGETS),
        )
        self.assertEqual(
            {row["target"]["selector"] for row in plan["rows"]},
            {
                "gpt-6-luna",
                "gpt-6-sol",
                "gpt-5.6-luna",
                "gpt-5.6-sol",
                "gpt-5.6-terra",
            },
        )
        self.assertNotIn("gpt-6-terra", {row["target"]["selector"] for row in plan["rows"]})
        self.assertTrue(all(row["target"]["host"] == "codex" for row in plan["rows"]))
        self.assertTrue(all(row["target"]["effort"] == "medium" for row in plan["rows"]))
        self.assertEqual(
            {row["representation"] for row in plan["rows"]}, {"general_rule", "ontology"}
        )
        self.assertEqual({row["repeat"] for row in plan["rows"]}, {1, 2})
        self.assertTrue(all(row["reset"] is True for row in plan["rows"]))
        self.assertEqual(plan["scientific"], {"assigned": 0, "executed": 0, "eligible": False})

    def test_extension_builder_is_not_a_legacy_or_mixed_schema_alias(self) -> None:
        legacy = build_assignment_plan(
            quest_id="sealed-lighthouse-v1",
            seed=20261024,
            source_manifest_sha256=SOURCE_SHA,
            input_manifest_sha256=INPUT_SHA,
        )
        extension = build_extension_assignment_plan(
            quest_id="sealed-lighthouse-v1",
            seed=20261024,
            source_manifest_sha256=SOURCE_SHA,
            input_manifest_sha256=INPUT_SHA,
        )
        self.assertEqual(legacy["schema_version"], ASSIGNMENT_PLAN_SCHEMA)
        self.assertEqual(extension["schema_version"], EXTENSION_ASSIGNMENT_PLAN_SCHEMA)
        self.assertNotEqual(
            [row["target"]["selector"] for row in legacy["rows"]],
            [row["target"]["selector"] for row in extension["rows"]],
        )
        self.assertNotEqual(extension["schema_version"], ASSIGNMENT_PLAN_SCHEMA)

    def test_extension_activation_rejects_missing_or_wrong_catalog_digest(self) -> None:
        for mutation in ("missing", "wrong"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory), extension=True)
                plan = dict(bundle["plan"])
                if mutation == "missing":
                    plan.pop("catalog_sha256", None)
                else:
                    plan["catalog_sha256"] = "0" * 64
                plan_bytes = _canonical_bytes(plan)
                bundle["plan_path"].write_bytes(plan_bytes)
                bundle["plan_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
                bundle["activation"]["plan"]["sha256"] = bundle["plan_sha256"]
                activation_bytes = _canonical_bytes(bundle["activation"])
                bundle["activation_path"].write_bytes(activation_bytes)
                activation_sha = hashlib.sha256(activation_bytes).hexdigest()
                with self.assertRaisesRegex(ValueError, "native_activation_plan_catalog_mismatch"):
                    load_pinned_native_activation(
                        activation_path=bundle["activation_path"],
                        activation_sha256=activation_sha,
                        plan_path=bundle["plan_path"],
                        plan_sha256=bundle["plan_sha256"],
                        row_id=bundle["row"]["planned_id"],
                        purpose="test_simulation",
                        trust_root=bundle["trust_root"],
                        source_root=bundle["source_root"],
                    )


class ProviderIdentityAdmissionTests(unittest.TestCase):
    _SELECTOR = "gpt-6-luna"
    _MATCH = (
        "2026-10-26T12:00:00Z INFO codex_core::session: "
        "server reported model gpt-6-luna (matches requested model)"
    )

    def test_parser_accepts_only_narrow_provider_header_match(self) -> None:
        result = parse_codex_provider_identity(
            self._MATCH + "\n", requested_selector=self._SELECTOR
        )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["provider_identity"], self._SELECTOR)
        self.assertEqual(result["identity_source"], "codex_core::session")
        self.assertEqual(
            result["identity_message"],
            "server reported model gpt-6-luna (matches requested model)",
        )
        self.assertEqual(EXTENSION_CODEX_IDENTITY_SOURCE, "codex_core::session")
        self.assertEqual(EXTENSION_CODEX_CLI_VERSION, "0.164.0")

    def test_parser_rejects_missing_mismatch_reroute_ambiguous_and_malformed_identity(self) -> None:
        cases = (
            ("missing", "ordinary stderr\n", "provider_identity_missing"),
            (
                "mismatch",
                "INFO codex_core::session: server reported model gpt-6-sol (matches requested model)\n",
                "provider_identity_mismatch",
            ),
            (
                "match-then-reroute",
                f"{self._MATCH}\nINFO codex_core::session: server reported model gpt-6-sol while requested model was gpt-6-luna\n",
                "provider_identity_reroute",
            ),
            (
                "reroute",
                "INFO codex_core::session: server reported model gpt-6-sol while requested model was gpt-6-luna\n",
                "provider_identity_reroute",
            ),
            ("ambiguous", f"{self._MATCH}\n{self._MATCH}\n", "provider_identity_ambiguous"),
            (
                "malformed",
                "INFO codex_core::session: server reported model gpt-6-luna\n",
                "provider_identity_malformed",
            ),
        )
        for name, stderr, expected_error in cases:
            with self.subTest(name=name):
                result = parse_codex_provider_identity(stderr, requested_selector=self._SELECTOR)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["provider_identity"])
                self.assertEqual(result["error"], expected_error)

    def test_parser_does_not_accept_body_config_echo_or_retry_origin_as_identity(self) -> None:
        spoofed_body = {
            "model": self._SELECTOR,
            "requested_model": self._SELECTOR,
            "config": {"model": self._SELECTOR},
        }
        cases = (
            json.dumps(spoofed_body),
            (
                "INFO codex_core::session: server reported model gpt-6-luna (matches requested model)\n"
                "INFO codex_core::session: server reported model gpt-6-sol while requested model was gpt-6-luna\n"
            ),
        )
        for stderr in cases:
            result = parse_codex_provider_identity(stderr, requested_selector=self._SELECTOR)
            self.assertEqual(result["status"], "rejected")
            self.assertIsNone(result["provider_identity"])

    def test_extension_runner_admits_only_current_provider_identity(self) -> None:
        cases = (
            ("matched", self._MATCH + "\n", 0, None),
            ("missing", "ordinary stderr\n", 5, "provider_identity_missing"),
            (
                "mismatched",
                "INFO codex_core::session: server reported model gpt-6-sol (matches requested model)\n",
                5,
                "provider_identity_mismatch",
            ),
            ("duplicate", f"{self._MATCH}\n{self._MATCH}\n", 5, "provider_identity_ambiguous"),
            (
                "match-then-reroute",
                f"{self._MATCH}\nINFO codex_core::session: server reported model gpt-6-sol while requested model was gpt-6-luna\n",
                5,
                "provider_identity_reroute",
            ),
            (
                "retry-origin",
                "INFO codex_core::session: retrying request after transport failure\n"
                + self._MATCH
                + "\n",
                5,
                "provider_identity_reroute",
            ),
        )
        for name, stderr, expected_returncode, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory), extension=True)

                class IdentityTransport(_CountingTransport):
                    def __call__(
                        self,
                        command: list[str],
                        *,
                        _stderr: str = stderr,
                        **kwargs: Any,
                    ) -> subprocess.CompletedProcess[str]:
                        self.calls.append({"command": list(command), **kwargs})
                        return subprocess.CompletedProcess(
                            command,
                            0,
                            json.dumps(
                                {
                                    "type": "item.completed",
                                    "item": {
                                        "type": "agent_message",
                                        "text": json.dumps(
                                            {
                                                "request_id": "fixture:identity-matrix",
                                                "action": "finish",
                                            }
                                        ),
                                    },
                                }
                            ),
                            _stderr,
                        )

                transport = IdentityTransport()
                runner = NativePromptRunner(
                    host="codex",
                    selector="gpt-6-luna",
                    effort="medium",
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                    process_runner=transport,
                )
                response = runner(
                    request_id="fixture:identity-matrix",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model="gpt-6-luna",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )
                self.assertEqual(response.returncode, expected_returncode)
                if expected_error is None:
                    self.assertEqual(response.payload["action"], "finish")
                    self.assertEqual(response.receipt["provider_identity"], "gpt-6-luna")
                    self.assertEqual(response.receipt["identity_transport"], "http")
                    self.assertEqual(
                        response.receipt["identity_request_hash"],
                        response.receipt["outgoing_request_sha256"],
                    )
                    config_values = {
                        transport.calls[0]["command"][index + 1]
                        for index, value in enumerate(transport.calls[0]["command"][:-1])
                        if value == "-c"
                    }
                    self.assertIn('model_provider="codex_extension_http"', config_values)
                    self.assertIn(
                        'model_providers.codex_extension_http.name="OpenAI"', config_values
                    )
                    self.assertIn(
                        'model_providers.codex_extension_http.wire_api="responses"', config_values
                    )
                    self.assertIn(
                        "model_providers.codex_extension_http.requires_openai_auth=true",
                        config_values,
                    )
                    self.assertIn(
                        "model_providers.codex_extension_http.supports_websockets=false",
                        config_values,
                    )
                    self.assertIn(
                        "model_providers.codex_extension_http.request_max_retries=0",
                        config_values,
                    )
                    self.assertIn(
                        "model_providers.codex_extension_http.stream_max_retries=0",
                        config_values,
                    )
                else:
                    self.assertEqual(response.receipt["error"], expected_error)
                    self.assertEqual(response.payload, {})

    def test_injected_fixture_identity_remains_synthetic_even_with_positive_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))

            class IdentityFixtureTransport(_CountingTransport):
                def __call__(
                    self, command: list[str], **kwargs: Any
                ) -> subprocess.CompletedProcess[str]:
                    self.calls.append({"command": list(command), **kwargs})
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {
                                    "type": "agent_message",
                                    "text": json.dumps(
                                        {"request_id": "fixture:identity", "action": "finish"}
                                    ),
                                },
                            }
                        ),
                        self._stderr,
                    )

                _stderr = ProviderIdentityAdmissionTests._MATCH + "\n"

            transport = IdentityFixtureTransport()
            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6.1-sol",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
                process_runner=transport,
            )
            response = runner(
                request_id="fixture:identity",
                instruction="fixture prompt",
                user_prompt="fixture prompt",
                output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                model="gpt-6.1-sol",
                timeout=1,
                representation=bundle["row"]["representation"],
            )
        self.assertIsNone(response.receipt.get("identity_request_hash"))
        self.assertIsNone(response.receipt.get("identity_transport"))
        self.assertIsNone(response.receipt.get("identity_cli_version"))
        self.assertEqual(response.returncode, 0)
        self.assertEqual(response.payload["action"], "finish")
        self.assertTrue(response.receipt["synthetic"])
        self.assertIsNone(response.receipt["provider_identity"])

    def test_parser_rejects_non_text_transport_without_coercion(self) -> None:
        result = parse_codex_provider_identity(None, requested_selector=self._SELECTOR)  # type: ignore[arg-type]
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "provider_identity_transport_invalid")

    def test_codex_extension_transport_is_http_zero_retry_narrow_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))

            class Transport(_CountingTransport):
                def __call__(
                    self, command: list[str], **kwargs: Any
                ) -> subprocess.CompletedProcess[str]:
                    self.calls.append({"command": list(command), **kwargs})
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        json.dumps(
                            {
                                "type": "item.completed",
                                "item": {
                                    "type": "agent_message",
                                    "text": json.dumps(
                                        {"request_id": "fixture:transport", "action": "observe"}
                                    ),
                                },
                            }
                        ),
                        "",
                    )

            transport = Transport()
            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6.1-sol",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
                process_runner=transport,
            )
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "inherited-secret",
                    "ANTHROPIC_API_KEY": "alternate-secret",
                    "OPENAI_BASE_URL": "https://alternate.invalid",
                    "CODEX_API_KEY": "alternate-secret",
                },
                clear=False,
            ):
                response = runner(
                    request_id="fixture:transport",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model="gpt-6.1-sol",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )
        self.assertEqual(response.returncode, 0)
        observed = transport.calls[0]
        command = observed["command"]
        config_values = {
            command[index + 1] for index, value in enumerate(command[:-1]) if value == "-c"
        }
        for extension_override in (
            'model_provider="codex_extension_http"',
            'model_providers.codex_extension_http.name="OpenAI"',
            'model_providers.codex_extension_http.wire_api="responses"',
            "model_providers.codex_extension_http.requires_openai_auth=true",
            "model_providers.codex_extension_http.supports_websockets=false",
            "model_providers.codex_extension_http.request_max_retries=0",
            "model_providers.codex_extension_http.stream_max_retries=0",
        ):
            self.assertNotIn(extension_override, config_values)
        self.assertNotIn("RUST_LOG", observed["env"])
        for key in (
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "OPENAI_BASE_URL",
            "CODEX_API_KEY",
        ):
            self.assertNotIn(key, observed["env"])


class ExtensionActivationClaimTests(unittest.TestCase):
    def test_production_extension_row_claim_is_atomic_and_once_per_runner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root / "fixture", extension=True)
            schema_bytes = (bundle["source_root"] / "bound" / "output-schema.json").read_bytes()
            output_roots = [root / name for name in ("output-a", "output-b", "output-c")]
            schemas: list[Path] = []
            for output_root in output_roots:
                output_root.mkdir()
                schema = output_root / "schema.json"
                schema.write_bytes(schema_bytes)
                schemas.append(schema)
            dispatches: list[dict[str, Any]] = []
            home = root / "home"
            (home / ".codex").mkdir(parents=True)
            (home / ".codex" / "auth.json").write_text("{}", encoding="utf-8")

            def host_process(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                dispatches.append({"command": list(command), **kwargs})
                request_id = "fixture:claim-1" if len(dispatches) == 1 else "fixture:claim-2"
                return subprocess.CompletedProcess(
                    command,
                    0,
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps({"request_id": request_id, "action": "finish"}),
                            },
                        }
                    ),
                    ProviderIdentityAdmissionTests._MATCH + "\n",
                )

            def invoke(
                runner: NativePromptRunner,
                request_id: str,
                schema: Path,
                *,
                prompt: str = "fixture prompt",
            ) -> NativePromptResult:
                return runner(
                    request_id=request_id,
                    instruction=prompt,
                    user_prompt=prompt,
                    output_schema=schema,
                    output_schema_sha256=bundle["activation"]["artifact_bindings"][
                        "output_schema_sha256"
                    ],
                    allowed_requests_sha256=bundle["activation"]["artifact_bindings"][
                        "allowed_requests_sha256"
                    ],
                    quest_id=bundle["row"]["quest_id"],
                    seed=bundle["row"]["seed"],
                    repeat=bundle["row"]["repeat"],
                    reset=bundle["row"]["reset"],
                    fixture_id=bundle["row"]["fixture_id"],
                    fixture_sha256=bundle["row"]["fixture_sha256"],
                    oracle_sha256=bundle["row"]["oracle_sha256"],
                    model="gpt-6-luna",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )

            runner_one = NativePromptRunner(
                host="codex",
                selector="gpt-6-luna",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            runner_two = NativePromptRunner(
                host="codex",
                selector="gpt-6-luna",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            with (
                patch.object(
                    native_runtime,
                    "_sanitized_environment",
                    side_effect=lambda: {"HOME": str(home)},
                ),
                patch.object(native_runtime, "run_host_process", side_effect=host_process),
            ):
                first = invoke(runner_one, "fixture:claim-1", schemas[0])
                second = invoke(
                    runner_one, "fixture:claim-2", schemas[1], prompt="fixture prompt second"
                )
                denied = invoke(runner_two, "fixture:claim-3", schemas[2])
        self.assertEqual(first.returncode, 0)
        self.assertEqual(second.returncode, 0, second.receipt)
        self.assertEqual(denied.returncode, 2)
        self.assertEqual(denied.receipt["error"], "native_activation_row_already_claimed")
        self.assertEqual(len(dispatches), 2)


class ProductionExtensionReceiptTests(unittest.TestCase):
    _MATCH = (
        "2026-10-26T12:00:00Z INFO codex_core::session: "
        "server reported model gpt-6-luna (matches requested model)"
    )

    def _run_episode_with_stderr(
        self, stderr: str
    ) -> tuple[dict[str, Any], dict[str, Any], NativeActivationTrust]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root / "fixture", extension=True)
            home = root / "home"
            (home / ".codex").mkdir(parents=True)
            (home / ".codex" / "auth.json").write_text("{}", encoding="utf-8")
            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6-luna",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            engine = _SimpleEngine()
            engine.prompt_receipts = []

            def host_process(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                on_started = kwargs.get("on_started")
                if callable(on_started):
                    on_started()
                return subprocess.CompletedProcess(
                    command,
                    0,
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps(
                                    {"request_id": "decision-0", "action": "finish"}
                                ),
                            },
                        }
                    ),
                    stderr,
                )

            def proposal(_context: dict[str, Any]) -> dict[str, Any]:
                response = runner(
                    request_id="decision-0",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    output_schema_sha256=bundle["activation"]["artifact_bindings"][
                        "output_schema_sha256"
                    ],
                    allowed_requests_sha256=bundle["activation"]["artifact_bindings"][
                        "allowed_requests_sha256"
                    ],
                    quest_id=bundle["row"]["quest_id"],
                    seed=bundle["row"]["seed"],
                    repeat=bundle["row"]["repeat"],
                    reset=bundle["row"]["reset"],
                    fixture_id=bundle["row"]["fixture_id"],
                    fixture_sha256=bundle["row"]["fixture_sha256"],
                    oracle_sha256=bundle["row"]["oracle_sha256"],
                    model="gpt-6-luna",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )
                engine.prompt_receipts.append(response.receipt)
                if response.returncode != 0:
                    raise PromptTransportError(response.receipt.get("error", "fixture failure"))
                return response.payload

            with (
                patch.object(
                    native_runtime, "_sanitized_environment", return_value={"HOME": str(home)}
                ),
                patch.object(native_runtime, "run_host_process", side_effect=host_process),
            ):
                record = run_episode(
                    engine=engine,
                    proposal_source=proposal,
                    model=ModelSpec(
                        "gpt-6-luna",
                        bundle["row"]["representation"],
                        provider="codex",
                        offline=False,
                    ),
                    limits=EpisodeLimits(180, 60, 1, 0),
                    seed=bundle["row"]["seed"],
                    clock=lambda: 0.0,
                    config=_production_config(bundle),
                    prompt="fixture prompt",
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                )
            return record, engine.prompt_receipts[0], bundle["capability"]

    def test_production_receipt_qualification_controls_scientific_eligibility(self) -> None:
        cases = (
            ("verified", self._MATCH, True),
            ("missing", "", False),
            (
                "wrong",
                "2026-10-26T12:00:00Z INFO codex_core::session: server reported model gpt-6-sol (matches requested model)",
                False,
            ),
            (
                "reroute",
                "2026-10-26T12:00:00Z INFO codex_core::session: server reported model gpt-6-sol while requested model was gpt-6-luna",
                False,
            ),
        )
        for name, stderr, qualified in cases:
            with self.subTest(name=name):
                record, receipt, capability = self._run_episode_with_stderr(stderr)
                self.assertEqual(record["accounting"]["assigned"], 1)
                self.assertEqual(record["scientific"]["assigned"], 1)
                self.assertEqual(record["accounting"]["denominator_eligible"], True)
                self.assertEqual(record["scientific"]["executed"], 1)
                self.assertEqual(record["scientific"]["eligible"], qualified)
                self.assertEqual(
                    record["evidence"]["response_qualification"]["qualified"], qualified
                )
                self.assertEqual(
                    native_cli._native_scientific_summary(record, capability),
                    {"assigned": 1, "executed": 1, "eligible": qualified},
                )
                finalized_failure = native_cli._post_admission_failure(
                    phase="record",
                    exc=RuntimeError("fixture finalized failure"),
                    source={"source": "fixture"},
                    inputs={"input": "fixture"},
                    output_root=Path("fixture-output"),
                    record=record,
                    trusted_activation=capability,
                )
                self.assertEqual(
                    finalized_failure["scientific"],
                    native_cli._native_scientific_summary(record, capability),
                )
                if qualified:
                    mutations = (
                        (
                            "missing",
                            lambda candidate: candidate["evidence"].pop("response_qualification"),
                        ),
                        (
                            "malformed",
                            lambda candidate: candidate["evidence"].update(
                                response_qualification=[]
                            ),
                        ),
                        (
                            "boolean-like-required",
                            lambda candidate: candidate["evidence"][
                                "response_qualification"
                            ].update(required=1),
                        ),
                        (
                            "boolean-like-qualified",
                            lambda candidate: candidate["evidence"][
                                "response_qualification"
                            ].update(qualified=1),
                        ),
                        (
                            "boolean-like-eligible",
                            lambda candidate: candidate["scientific"].update(eligible=1),
                        ),
                    )
                    for mutation, mutate in mutations:
                        candidate = json.loads(json.dumps(record))
                        mutate(candidate)
                        summary = native_cli._native_scientific_summary(candidate, capability)
                        self.assertFalse(summary["eligible"], mutation)
                if not qualified:
                    self.assertEqual(len(record["decisions"]), 1)
                    decision = record["decisions"][0]
                    self.assertEqual(decision["raw_proposals"], [])
                    self.assertIsNone(decision["validation"])
                    self.assertIsNone(decision["repair"])
                    self.assertIsNone(decision["commit"])
                    self.assertEqual(record["evidence"]["commit"], [])
                    self.assertFalse(record["success"])
                    self.assertFalse(record["scientific"]["eligible"])
                if qualified:
                    self.assertTrue(record["success"])
                    self.assertTrue(receipt["provider_identity_verified"])
                    self.assertEqual(receipt["provider_identity"], "gpt-6-luna")
                    self.assertEqual(receipt["identity_source"], EXTENSION_CODEX_IDENTITY_SOURCE)
                    self.assertIsNone(receipt["provider_revision"])
                    self.assertEqual(receipt["identity_transport"], "http")
                    self.assertEqual(receipt["identity_cli_version"], EXTENSION_CODEX_CLI_VERSION)
                    self.assertEqual(
                        receipt["identity_request_hash"], receipt["outgoing_request_sha256"]
                    )
                else:
                    self.assertFalse(record["success"])
                    self.assertNotEqual(receipt.get("provider_identity_verified"), True)
                    self.assertNotEqual(receipt.get("response_qualified"), True)

    def test_extension_post_admission_failures_never_promote_without_finalized_qualification(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            _record, receipt, capability = self._run_episode_with_stderr(self._MATCH)
            no_record = native_cli._post_admission_failure(
                phase="episode",
                exc=RuntimeError("fixture opaque episode failure"),
                source={},
                inputs={},
                output_root=root / "no-record",
                engine=SimpleNamespace(prompt_receipts=[]),
                trusted_activation=capability,
            )
            receipts_only = native_cli._post_admission_failure(
                phase="episode",
                exc=RuntimeError("fixture receipts-only failure"),
                source={},
                inputs={},
                output_root=root / "receipts-only",
                engine=SimpleNamespace(prompt_receipts=[receipt]),
                trusted_activation=capability,
            )
            pre_dispatch = native_cli._post_admission_failure(
                phase="admission",
                exc=RuntimeError("fixture pre-dispatch failure"),
                source={},
                inputs={},
                output_root=root / "pre-dispatch",
                trusted_activation=capability,
            )
            legacy_bundle = _production_bundle(root / "legacy")
            legacy = native_cli._post_admission_failure(
                phase="episode",
                exc=RuntimeError("fixture legacy failure"),
                source={},
                inputs={},
                output_root=root / "legacy-output",
                trusted_activation=legacy_bundle["capability"],
            )
        self.assertEqual(
            no_record["scientific"],
            {"assigned": 1, "executed": None, "eligible": False},
        )
        self.assertEqual(no_record["failure_artifact"]["execution_evidence"], "unknown")
        self.assertEqual(
            receipts_only["scientific"],
            {"assigned": 1, "executed": 1, "eligible": False},
        )
        self.assertEqual(
            receipts_only["failure_artifact"]["execution_evidence"],
            "observed_trust_bound_start",
        )
        self.assertEqual(
            pre_dispatch["scientific"], {"assigned": 1, "executed": 0, "eligible": False}
        )
        self.assertEqual(pre_dispatch["failure_artifact"]["execution_evidence"], "pre_dispatch")
        self.assertEqual(legacy["scientific"], {"assigned": 1, "executed": None, "eligible": True})
        self.assertEqual(
            native_cli._native_scientific_summary({"evidence": {}}, legacy_bundle["capability"]),
            {"assigned": 1, "executed": 0, "eligible": True},
        )


class ExtensionDispatchCapTests(unittest.TestCase):
    def test_twelve_dispatches_are_cumulative_and_thirteenth_or_new_runner_is_denied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root / "fixture", extension=True)
            schema = bundle["source_root"] / "bound" / "output-schema.json"
            home = root / "home"
            (home / ".codex").mkdir(parents=True)
            (home / ".codex" / "auth.json").write_text("{}", encoding="utf-8")
            request_ids: list[str] = []
            process_calls: list[str] = []
            active_request_id = ""

            def host_process(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                process_calls.append(active_request_id)
                on_started = kwargs.get("on_started")
                if callable(on_started):
                    on_started()
                return subprocess.CompletedProcess(
                    command,
                    0,
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps(
                                    {"request_id": active_request_id, "action": "finish"}
                                ),
                            },
                        }
                    ),
                    ProductionExtensionReceiptTests._MATCH,
                )

            def invoke(runner: NativePromptRunner, request_id: str) -> NativePromptResult:
                nonlocal active_request_id
                active_request_id = request_id
                request_ids.append(request_id)
                return runner(
                    request_id=request_id,
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=schema,
                    output_schema_sha256=bundle["activation"]["artifact_bindings"][
                        "output_schema_sha256"
                    ],
                    allowed_requests_sha256=bundle["activation"]["artifact_bindings"][
                        "allowed_requests_sha256"
                    ],
                    quest_id=bundle["row"]["quest_id"],
                    seed=bundle["row"]["seed"],
                    repeat=bundle["row"]["repeat"],
                    reset=bundle["row"]["reset"],
                    fixture_id=bundle["row"]["fixture_id"],
                    fixture_sha256=bundle["row"]["fixture_sha256"],
                    oracle_sha256=bundle["row"]["oracle_sha256"],
                    model="gpt-6-luna",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )

            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6-luna",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            new_runner = NativePromptRunner(
                host="codex",
                selector="gpt-6-luna",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
            with (
                patch.object(
                    native_runtime,
                    "_sanitized_environment",
                    side_effect=lambda: {"HOME": str(home)},
                ),
                patch.object(native_runtime, "run_host_process", side_effect=host_process),
            ):
                results = [invoke(runner, f"fixture:episode-{index}") for index in range(1, 13)]
                denied = invoke(runner, "fixture:episode-13")
                claimed = invoke(new_runner, "fixture:new-runner")
        self.assertEqual(len(request_ids), 14)
        self.assertEqual(process_calls, request_ids[:12])
        for result in results:
            self.assertEqual(result.returncode, 0, result.receipt.get("error"))
        self.assertEqual(denied.returncode, 2, denied.receipt.get("error"))
        self.assertEqual(denied.receipt["error"], "native_extension_dispatch_limit")
        self.assertEqual(denied.receipt["dispatch_started"], False)
        self.assertEqual(claimed.returncode, 2, claimed.receipt.get("error"))
        self.assertEqual(claimed.receipt["error"], "native_activation_row_already_claimed")
        self.assertEqual(len(process_calls), 12)

    def test_reusing_runner_across_episodes_cannot_reset_extension_dispatch_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = _production_bundle(root / "fixture", extension=True)
            schema = bundle["source_root"] / "bound" / "output-schema.json"
            home = root / "home"
            (home / ".codex").mkdir(parents=True)
            (home / ".codex" / "auth.json").write_text("{}", encoding="utf-8")
            request_ids: list[str] = []
            process_calls: list[str] = []
            active_request_id = ""
            active_engine: _SimpleEngine | None = None

            def host_process(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
                process_calls.append(active_request_id)
                on_started = kwargs.get("on_started")
                if callable(on_started):
                    on_started()
                return subprocess.CompletedProcess(
                    command,
                    0,
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "type": "agent_message",
                                "text": json.dumps(
                                    {"request_id": active_request_id, "action": "finish"}
                                ),
                            },
                        }
                    ),
                    ProductionExtensionReceiptTests._MATCH,
                )

            runner = NativePromptRunner(
                host="codex",
                selector="gpt-6-luna",
                effort="medium",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )

            def invoke(request_id: str) -> NativePromptResult:
                nonlocal active_request_id
                active_request_id = request_id
                request_ids.append(request_id)
                return runner(
                    request_id=request_id,
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=schema,
                    output_schema_sha256=bundle["activation"]["artifact_bindings"][
                        "output_schema_sha256"
                    ],
                    allowed_requests_sha256=bundle["activation"]["artifact_bindings"][
                        "allowed_requests_sha256"
                    ],
                    quest_id=bundle["row"]["quest_id"],
                    seed=bundle["row"]["seed"],
                    repeat=bundle["row"]["repeat"],
                    reset=bundle["row"]["reset"],
                    fixture_id=bundle["row"]["fixture_id"],
                    fixture_sha256=bundle["row"]["fixture_sha256"],
                    oracle_sha256=bundle["row"]["oracle_sha256"],
                    model="gpt-6-luna",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )

            def proposal(_context: dict[str, Any]) -> dict[str, Any]:
                response = invoke(f"fixture:episode-{len(request_ids) + 1}")
                if active_engine is None:
                    raise AssertionError("fixture engine was not initialized")
                active_engine.prompt_receipts.append(response.receipt)
                if response.returncode != 0:
                    raise PromptTransportError(response.receipt.get("error", "fixture failure"))
                return response.payload

            def run_one(output_path: Path) -> dict[str, Any]:
                nonlocal active_engine
                engine = _SimpleEngine()
                engine.prompt_receipts = []
                active_engine = engine
                with (
                    patch.object(
                        native_runtime,
                        "_sanitized_environment",
                        side_effect=lambda: {"HOME": str(home)},
                    ),
                    patch.object(native_runtime, "run_host_process", side_effect=host_process),
                ):
                    return run_episode(
                        engine=engine,
                        proposal_source=proposal,
                        model=ModelSpec(
                            "gpt-6-luna",
                            bundle["row"]["representation"],
                            provider="codex",
                            offline=False,
                        ),
                        limits=EpisodeLimits(180, 60, 1, 0),
                        seed=bundle["row"]["seed"],
                        clock=lambda: 0.0,
                        config=_production_config(bundle),
                        prompt="fixture prompt",
                        output_path=output_path,
                        native_context=bundle["context"],
                        trusted_activation=bundle["capability"],
                    )

            with (
                patch.object(
                    native_runtime,
                    "_sanitized_environment",
                    side_effect=lambda: {"HOME": str(home)},
                ),
                patch.object(native_runtime, "run_host_process", side_effect=host_process),
            ):
                for index in range(1, 12):
                    preconsumed = invoke(f"fixture:preconsume-{index}")
                    self.assertEqual(preconsumed.returncode, 0, preconsumed.receipt.get("error"))
                first = run_one(root / "episode-first.json")
                second = run_one(root / "episode-second.json")
        self.assertEqual(process_calls, request_ids[:12])
        self.assertEqual(len(process_calls), 12)
        self.assertTrue(first["success"])
        self.assertEqual(first["scientific"], {"assigned": 1, "executed": 1, "eligible": True})
        self.assertEqual(len(first["evidence"]["commit"]), 1)
        self.assertFalse(second["success"])
        self.assertFalse(second["scientific"]["eligible"])
        self.assertEqual(second["scientific"]["assigned"], 1)
        self.assertEqual(second["scientific"]["executed"], 0)
        self.assertTrue(second["accounting"]["denominator_eligible"])
        self.assertEqual(second["decisions"][0]["raw_proposals"], [])
        self.assertIsNone(second["decisions"][0]["validation"])
        self.assertIsNone(second["decisions"][0]["repair"])
        self.assertIsNone(second["decisions"][0]["commit"])
        self.assertEqual(second["evidence"]["commit"], [])
        self.assertEqual(
            second["evidence"]["prompt_receipts"][0]["error"], "native_extension_dispatch_limit"
        )


class RejectedIdentityRuntimeBoundaryTests(unittest.TestCase):
    def test_rejected_identity_cannot_commit_action_or_report_goal_success(self) -> None:
        engine = _SimpleEngine()
        calls: list[dict[str, Any]] = []

        def rejected_identity(context: dict[str, Any]) -> dict[str, Any]:
            calls.append(dict(context))
            raise PromptTransportError("provider_identity_missing")

        with tempfile.TemporaryDirectory() as directory:
            bundle = _simulation_bundle(Path(directory))
            record = run_episode(
                engine=engine,
                proposal_source=rejected_identity,
                model=ModelSpec("gpt-6.1-sol", "general_rule", provider="codex", offline=False),
                limits=EpisodeLimits(180, 60, 1, 0),
                seed=20261024,
                clock=lambda: 0.0,
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                output_path=Path(directory) / "record.json",
                native_context=bundle["context"],
                trusted_activation=bundle["capability"],
            )
        self.assertEqual(len(calls), 1)
        self.assertEqual(record["accounting"]["source_attempts"], 1)
        self.assertFalse(record["success"])
        self.assertFalse(record["goal_reached"])
        self.assertEqual(engine.commits, [])
        self.assertEqual(record["decisions"][0]["commit"], None)
        self.assertIn("provider_identity_missing", record["last_error"])


class ExtensionAdmissionPrerequisiteTests(unittest.TestCase):
    def test_disabled_identity_gate_blocks_before_any_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _production_bundle(Path(directory))
            context = json.loads(json.dumps(bundle["context"]))
            context["authority"]["identity_setting_verified"] = False
            result = validate_native_context(
                context,
                model=_model(bundle["context"]),
                config=_production_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertFalse(result["ready"])
        self.assertIn("authority_identity_setting_verified_missing", result["reasons"])

    def test_stale_source_receipt_and_authority_mutation_block_admission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _production_bundle(Path(directory))
            source_manifest = bundle["source_root"] / "bound" / "source_manifest.json"
            source_manifest.write_bytes(source_manifest.read_bytes() + b"\nstale\n")
            result = validate_native_context(
                bundle["context"],
                model=_model(bundle["context"]),
                config=_production_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
            self.assertFalse(result["ready"])
            self.assertTrue(any("source_manifest" in reason for reason in result["reasons"]))

            context = json.loads(json.dumps(bundle["context"]))
            context["authority"]["context_isolation_verified"] = False
            authority_result = validate_native_context(
                context,
                model=_model(bundle["context"]),
                config=_production_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertFalse(authority_result["ready"])
        self.assertIn("authority_context_isolation_verified_missing", authority_result["reasons"])

    def test_removed_existing_credit_prerequisite_blocks_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle = _existing_credit_policy_bundle(Path(directory))
            context = json.loads(json.dumps(bundle["context"]))
            context["authority"].pop("automatic_reload_off_verified")
            result = validate_native_context(
                context,
                model=_model(bundle["context"]),
                config=_simulation_config(bundle),
                prompt="fixture prompt",
                source_root=bundle["source_root"],
                now="2026-10-25T12:00:00Z",
                trusted_activation=bundle["capability"],
            )
        self.assertFalse(result["ready"])
        self.assertTrue(
            any(
                reason in result["reasons"]
                for reason in (
                    "authority_subscription_no_additional_charge_verified_missing",
                    "subscription_charge_unknown",
                )
            )
        )


class OfflineBoundaryTests(unittest.TestCase):
    def test_existing_offline_cli_rejects_live_without_provider_activity(self) -> None:
        output = io.StringIO()
        with (
            patch.object(
                sys, "argv", ["run_runtime_model_swap.py", "--live", "--output-root", "/tmp/unused"]
            ),
            contextlib.redirect_stdout(output),
        ):
            code = offline_cli.main()
        self.assertEqual(code, 2)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["failure_reason"], "provider_not_allowed_offline")
        self.assertEqual(payload["provider_process_launch_count"], 0)


class ResponseModelIdentityObservationTests(unittest.TestCase):
    _SELECTOR = "gpt-6-luna"
    _SOURCE = "codex::response_model"
    _OLD_MATCH = (
        "2026-10-26T12:00:00Z INFO codex_core::session: "
        "server reported model gpt-6-luna (matches requested model)"
    )
    _FIELDS = (
        ("transport", "Http"),
        ("response_sequence", "1"),
        ("request_correlation_id", "req-7f3a"),
        ("phase", "SseTerminal(Completed)"),
        ("identity", "Exact"),
        ("created_model", "Exact"),
        ("completed_model", "Exact"),
        ("id_binding", "Match"),
        ("id_bound", "true"),
    )
    # Synthetic handoff/finish records for loopback-free unit cases (same shape as real records).
    _SYNTH_HANDOFF = (
        "2026-10-29T12:00:00.100000Z  INFO codex::responses_binding: "
        "responses request transport handoff correlation_id=req-7f3a attempt=0"
    )
    _SYNTH_FINISH = (
        "2026-10-29T12:00:00.200000Z  INFO codex::responses_binding: "
        "responses request attempt finished correlation_id=req-7f3a attempt=0 "
        "transport_handoff=true status=200 success=true"
    )
    # Real records from the rebuilt-CLI run on the loopback fixture (scratch capture, no provider call).
    # The span prefix before "codex::responses_binding:" is elided; parsing uses the message tail.
    _CAPTURED_HANDOFF = (
        "2026-10-29T05:35:19.134142Z  INFO ...span elided... codex::responses_binding: "
        "responses request transport handoff correlation_id=9ab8cab9-cc96-4e0f-99e8-c73fb0e19344 attempt=0"
    )
    _CAPTURED_FINISHED = (
        "2026-10-29T05:35:19.144868Z  INFO ...span elided... codex::responses_binding: "
        "responses request attempt finished correlation_id=9ab8cab9-cc96-4e0f-99e8-c73fb0e19344 "
        "attempt=0 transport_handoff=true status=200 success=true"
    )
    _CAPTURED_SELECTOR = "fixture-model"
    _CAPTURED_HEADER = (
        "2026-10-29T05:35:19.153266Z  INFO codex::response_model: response model header observation "
        "transport=Http response_sequence=1 request_correlation_id=9ab8cab9-cc96-4e0f-99e8-c73fb0e19344 "
        "phase=SseTerminal(Completed) header=Absent comparison=NotCompared parse_error=false"
    )
    _CAPTURED_IDENTITY = (
        "2026-10-29T05:35:19.153281Z  INFO codex::response_model: response model identity observation "
        "transport=Http response_sequence=1 request_correlation_id=9ab8cab9-cc96-4e0f-99e8-c73fb0e19344 "
        "phase=SseTerminal(Completed) identity=Exact created_model=Missing completed_model=Exact "
        "id_binding=Match id_bound=true"
    )
    # Identity pair from the separately saved observations file (different run: id 0c581f0c..., no records).
    _OBSERVATION_FILE_HEADER = (
        "2026-10-29T05:35:27.702017Z  INFO codex::response_model: response model header observation "
        "transport=Http response_sequence=1 request_correlation_id=0c581f0c-42b6-497e-8d82-3880dedb394b "
        "phase=SseTerminal(Completed) header=Absent comparison=NotCompared parse_error=false"
    )
    _OBSERVATION_FILE_IDENTITY = (
        "2026-10-29T05:35:27.702026Z  INFO codex::response_model: response model identity observation "
        "transport=Http response_sequence=1 request_correlation_id=0c581f0c-42b6-497e-8d82-3880dedb394b "
        "phase=SseTerminal(Completed) identity=Exact created_model=Missing completed_model=Exact "
        "id_binding=Match id_bound=true"
    )
    # Normal (non-retry) reqwest trace lines from the same captured run.
    _CAPTURED_NORMAL_TRACE_LINES = (
        "2026-10-29T05:35:18.894438Z TRACE reqwest::retry: shouldn't retry!",
        "2026-10-29T05:35:18.978403Z TRACE reqwest::retry: shouldn't retry!",
        "2026-10-29T05:35:18.979733Z TRACE reqwest::retry: shouldn't retry!",
    )
    _OTHER_CID = "11111111-2222-3333-4444-555555555555"

    @classmethod
    def _observation(cls, **overrides: str | None) -> str:
        values = dict(cls._FIELDS)
        for key, value in overrides.items():
            if value is None:
                values.pop(key)
            else:
                values[key] = value
        body = " ".join(f"{key}={value}" for key, value in values.items())
        return (
            f"2026-10-29T12:00:00.123456Z  INFO {cls._SOURCE}: "
            f"response model identity observation {body}"
        )

    @staticmethod
    def _with_field(line: str, key: str, value: str | None) -> str:
        tokens: list[str] = []
        replaced = False
        for token in line.split():
            if token.startswith(f"{key}="):
                replaced = True
                if value is not None:
                    tokens.append(f"{key}={value}")
                continue
            tokens.append(token)
        assert replaced, key
        return " ".join(tokens)

    @classmethod
    def _captured_run(
        cls, *, handoff=None, finished=None, header=None, identity=None
    ) -> tuple[str, ...]:
        return (
            handoff or cls._CAPTURED_HANDOFF,
            finished or cls._CAPTURED_FINISHED,
            header or cls._CAPTURED_HEADER,
            identity or cls._CAPTURED_IDENTITY,
        )

    def _parse(self, stderr: str) -> dict[str, Any]:
        return parse_codex_provider_identity(stderr, requested_selector=self._SELECTOR)

    def _parse_captured(self, *lines: str) -> dict[str, Any]:
        return parse_codex_provider_identity(
            "\n".join(lines) + "\n", requested_selector=self._CAPTURED_SELECTOR
        )

    def test_exact_completed_bound_single_attempt_observation_is_verified(self) -> None:
        result = self._parse(
            self._observation() + "\n" + self._SYNTH_HANDOFF + "\n" + self._SYNTH_FINISH + "\n"
        )
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["provider_identity"], self._SELECTOR)
        self.assertEqual(result["identity_source"], self._SOURCE)
        self.assertEqual(result["request_correlation_id"], "req-7f3a")

    def test_captured_positive_run_verifies_against_requested_selector(self) -> None:
        result = self._parse_captured(*self._captured_run())
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["provider_identity"], "fixture-model")
        self.assertEqual(result["identity_source"], "codex::response_model")
        self.assertEqual(result["request_correlation_id"], "9ab8cab9-cc96-4e0f-99e8-c73fb0e19344")

    def test_captured_positive_with_normal_trace_lines_still_verifies(self) -> None:
        result = self._parse_captured(*self._CAPTURED_NORMAL_TRACE_LINES, *self._captured_run())
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["provider_identity"], "fixture-model")

    def test_observation_file_pair_without_handoff_records_is_rejected(self) -> None:
        result = self._parse_captured(
            self._OBSERVATION_FILE_HEADER, self._OBSERVATION_FILE_IDENTITY
        )
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "provider_identity_handoff_missing")

    def test_created_model_omitted_is_accepted_but_other_created_values_reject(self) -> None:
        for value in ("Conflict", "Mismatch", "Duplicate", "Invalid", "Null"):
            with self.subTest(created_model=value):
                line = self._with_field(self._CAPTURED_IDENTITY, "created_model", value)
                result = self._parse_captured(*self._captured_run(identity=line))
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["error"], f"provider_identity_observation_{value.lower()}")
        result = self._parse_captured(*self._captured_run())
        self.assertEqual(result["status"], "verified")

    def test_captured_positive_mutations_reject_with_specific_codes(self) -> None:
        h, f, hd, i = (
            self._CAPTURED_HANDOFF,
            self._CAPTURED_FINISHED,
            self._CAPTURED_HEADER,
            self._CAPTURED_IDENTITY,
        )
        wf = self._with_field
        other = self._OTHER_CID
        cases = (
            ("duplicate-identity-line", (h, f, hd, i, i), "provider_identity_ambiguous"),
            (
                "two-correlation-ids",
                (h, f, hd, wf(i, "request_correlation_id", other)),
                "provider_identity_correlation_ambiguous",
            ),
            (
                "identity-conflict",
                (h, f, hd, wf(i, "identity", "Conflict")),
                "provider_identity_observation_conflict",
            ),
            (
                "identity-mismatch",
                (h, f, hd, wf(i, "identity", "Mismatch")),
                "provider_identity_observation_mismatch",
            ),
            (
                "completed-missing",
                (h, f, hd, wf(i, "completed_model", "Missing")),
                "provider_identity_observation_missing",
            ),
            (
                "completed-null",
                (h, f, hd, wf(i, "completed_model", "Null")),
                "provider_identity_observation_null",
            ),
            (
                "completed-invalid",
                (h, f, hd, wf(i, "completed_model", "Invalid")),
                "provider_identity_observation_invalid",
            ),
            (
                "completed-duplicate",
                (h, f, hd, wf(i, "completed_model", "Duplicate")),
                "provider_identity_observation_duplicate",
            ),
            (
                "binding-mismatch",
                (h, f, hd, wf(i, "id_binding", "Mismatch")),
                "provider_identity_observation_mismatch",
            ),
            (
                "binding-missing",
                (h, f, hd, wf(i, "id_binding", "Missing")),
                "provider_identity_observation_missing",
            ),
            (
                "unbound",
                (h, f, hd, wf(i, "id_bound", "false")),
                "provider_identity_observation_unbound",
            ),
            (
                "phase-legacy-completed",
                (h, f, hd, wf(i, "phase", "Completed")),
                "provider_identity_phase_not_completed",
            ),
            (
                "phase-created",
                (h, f, hd, wf(i, "phase", "SseTerminal(Created)")),
                "provider_identity_phase_not_completed",
            ),
            ("header-only", (h, f, hd), "provider_identity_missing"),
            ("handoff-missing", (f, hd, i), "provider_identity_handoff_missing"),
            ("handoff-duplicate-same-id", (h, h, f, hd, i), "provider_identity_handoff_ambiguous"),
            (
                "handoff-two-distinct-ids",
                (h, wf(h, "correlation_id", other), f, hd, i),
                "provider_identity_handoff_ambiguous",
            ),
            ("finish-missing", (h, hd, i), "provider_identity_finish_missing"),
            ("finish-duplicate", (h, f, f, hd, i), "provider_identity_finish_ambiguous"),
            (
                "finish-attempt-nonzero",
                (h, wf(f, "attempt", "1"), hd, i),
                "provider_identity_reroute",
            ),
            (
                "finish-success-false",
                (h, wf(f, "success", "false"), hd, i),
                "provider_identity_finish_unsuccessful",
            ),
            (
                "finish-status-500",
                (h, wf(f, "status", "500"), hd, i),
                "provider_identity_finish_status",
            ),
            (
                "finish-status-199",
                (h, wf(f, "status", "199"), hd, i),
                "provider_identity_finish_status",
            ),
            (
                "handoff-vs-finish-id",
                (h, wf(f, "correlation_id", other), hd, i),
                "provider_identity_handoff_mismatch",
            ),
            (
                "identity-vs-handoff-id",
                (
                    h,
                    f,
                    wf(hd, "request_correlation_id", other),
                    wf(i, "request_correlation_id", other),
                ),
                "provider_identity_correlation_mismatch",
            ),
        )
        for name, lines, expected_error in cases:
            with self.subTest(name=name):
                result = self._parse_captured(*lines)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["provider_identity"])
                self.assertEqual(result["error"], expected_error)

    def test_two_correlation_ids_across_attempt_logs_are_rejected(self) -> None:
        cases = (
            (
                "two-observations",
                self._observation(request_correlation_id="req-a")
                + "\n"
                + self._observation(request_correlation_id="req-b")
                + "\n",
            ),
            (
                "observation-plus-other-line",
                self._observation()
                + "\n2026-10-29T12:00:01Z INFO codex_core::session: request_correlation_id=req-b\n",
            ),
        )
        for name, stderr in cases:
            with self.subTest(name=name):
                result = self._parse(stderr)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["provider_identity"])
                self.assertEqual(result["error"], "provider_identity_correlation_ambiguous")

    def test_identity_fields_reject_each_bad_enum_with_specific_code(self) -> None:
        for field in ("identity", "created_model", "completed_model", "id_binding"):
            values = ("Duplicate", "Conflict", "Mismatch", "Missing", "Null", "Invalid")
            if field == "created_model":
                values = tuple(value for value in values if value != "Missing")
            for value in values:
                with self.subTest(field=field, value=value):
                    result = self._parse(self._observation(**{field: value}) + "\n")
                    self.assertEqual(result["status"], "rejected")
                    self.assertIsNone(result["provider_identity"])
                    self.assertEqual(
                        result["error"], f"provider_identity_observation_{value.lower()}"
                    )

    def test_unexpected_identity_enum_is_unqualified_not_verified(self) -> None:
        result = self._parse(self._observation(identity="Pending") + "\n")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "provider_identity_observation_unqualified")

    def test_non_completed_phase_is_rejected(self) -> None:
        result = self._parse(self._observation(phase="Created") + "\n")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "provider_identity_phase_not_completed")

    def test_unbound_or_uncorrelated_observation_is_rejected(self) -> None:
        cases = (
            (
                "unbound",
                self._observation(id_bound="false") + "\n",
                "provider_identity_observation_unbound",
            ),
            (
                "correlation-missing-token",
                self._observation(request_correlation_id="missing") + "\n",
                "provider_identity_correlation_missing",
            ),
        )
        for name, stderr, expected_error in cases:
            with self.subTest(name=name):
                result = self._parse(stderr)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["provider_identity"])
                self.assertEqual(result["error"], expected_error)

    def test_malformed_observation_fields_are_rejected(self) -> None:
        cases = (
            ("missing-field", self._observation(id_bound=None) + "\n"),
            ("duplicate-field", self._observation() + " identity=Exact\n"),
            ("extra-field", self._observation() + " model=gpt-6-luna\n"),
            (
                "wrong-message",
                "INFO codex::response_model: response model identity changed\n",
            ),
        )
        for name, stderr in cases:
            with self.subTest(name=name):
                result = self._parse(stderr)
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["provider_identity"])
                self.assertEqual(result["error"], "provider_identity_observation_malformed")

    def test_absent_observation_keeps_missing_error(self) -> None:
        result = self._parse("ordinary stderr\n")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "provider_identity_missing")

    def test_duplicate_identical_observation_is_ambiguous(self) -> None:
        result = self._parse(self._observation() + "\n" + self._observation() + "\n")
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["error"], "provider_identity_ambiguous")

    def test_reroute_or_retry_evidence_beside_observation_is_rejected(self) -> None:
        cases = (
            (
                "reroute",
                self._observation() + "\nINFO codex_core::session: server reported model gpt-6-sol "
                "while requested model was gpt-6-luna\n",
            ),
            (
                "retry-origin",
                "INFO codex_core::session: retrying request after transport failure\n"
                + self._observation()
                + "\n",
            ),
            (
                "nonzero-attempt",
                "INFO codex_core::session: handoff correlation_id=req-7f3a attempt=1\n"
                + self._observation()
                + "\n",
            ),
        )
        for name, stderr in cases:
            with self.subTest(name=name):
                result = self._parse(stderr)
                self.assertEqual(result["status"], "rejected")
                self.assertEqual(result["error"], "provider_identity_reroute")

    def test_old_format_match_remains_verified_with_old_source_and_no_correlation(self) -> None:
        result = self._parse(self._OLD_MATCH + "\n")
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["identity_source"], "codex_core::session")
        self.assertNotIn("request_correlation_id", result)

    def test_extension_runner_admits_only_exact_bound_single_attempt_observation(self) -> None:
        cases = (
            (
                "exact",
                self._observation() + "\n" + self._SYNTH_HANDOFF + "\n" + self._SYNTH_FINISH + "\n",
                0,
                None,
            ),
            (
                "two-correlation-ids",
                self._observation(request_correlation_id="req-a")
                + "\n"
                + self._observation(request_correlation_id="req-b")
                + "\n",
                5,
                "provider_identity_correlation_ambiguous",
            ),
            (
                "created-phase",
                self._observation(phase="Created") + "\n",
                5,
                "provider_identity_phase_not_completed",
            ),
            (
                "unbound",
                self._observation(id_bound="false") + "\n",
                5,
                "provider_identity_observation_unbound",
            ),
        )
        for name, stderr, expected_returncode, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                bundle = _simulation_bundle(Path(directory), extension=True)
                stdout = json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": json.dumps(
                                {"request_id": "fixture:identity-observation", "action": "finish"}
                            ),
                        },
                    }
                )

                class IdentityTransport(_CountingTransport):
                    def __call__(
                        self,
                        command: list[str],
                        *,
                        _stdout: str = stdout,
                        _stderr: str = stderr,
                        **kwargs: Any,
                    ) -> subprocess.CompletedProcess[str]:
                        self.calls.append({"command": list(command), **kwargs})
                        return subprocess.CompletedProcess(command, 0, _stdout, _stderr)

                transport = IdentityTransport()
                runner = NativePromptRunner(
                    host="codex",
                    selector="gpt-6-luna",
                    effort="medium",
                    native_context=bundle["context"],
                    trusted_activation=bundle["capability"],
                    process_runner=transport,
                )
                response = runner(
                    request_id="fixture:identity-observation",
                    instruction="fixture prompt",
                    user_prompt="fixture prompt",
                    output_schema=bundle["source_root"] / "bound" / "output-schema.json",
                    model="gpt-6-luna",
                    timeout=1,
                    representation=bundle["row"]["representation"],
                )
                self.assertEqual(response.returncode, expected_returncode)
                if expected_error is None:
                    self.assertEqual(response.payload["action"], "finish")
                    self.assertTrue(response.receipt["provider_identity_verified"])
                    self.assertEqual(response.receipt["provider_identity"], "gpt-6-luna")
                    self.assertEqual(response.receipt["identity_source"], self._SOURCE)
                    self.assertEqual(response.receipt["identity_transport"], "http")
                else:
                    self.assertEqual(response.receipt["error"], expected_error)
                    self.assertEqual(response.payload, {})


# Contract map:
# AC1 admission/publicity/identity/context/subscription/hash/expiry/model gates; no self-certified ready.
# AC2 three supported host envelopes, exact flags, no Antigravity Claude-only flags, no substitution.
# AC3 attempts/corrections/deadlines, malformed/refusal/nonzero/timeout, no late/invalid commit, local cleanup.
# AC4 deterministic 20-row plan, reset/repeat/view/target dimensions, zero scientific assignment/execution.
# AC5 concrete source/input/prompt/game/ontology/oracle hashes and publicity/context evidence.
# AC6 unknown provider identity/revision/effective effort/usage/cost remain unknown; estimates are not invoices.
# AC7 existing run_episode seam, offline safety, assigned failure and no-commit evidence.
# AC8 local-only engineering fixture and old --live refusal; no provider command/account/billing action.
