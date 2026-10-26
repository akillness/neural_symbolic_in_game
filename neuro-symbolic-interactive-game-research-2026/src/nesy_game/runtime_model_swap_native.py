from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any

NATIVE_CONTEXT_SCHEMA = "runtime-native-context/1"
ASSIGNMENT_PLAN_SCHEMA = "runtime-model-swap/assignment-plan/1"
SUPPORTED_HOSTS = {"codex", "claude_code", "antigravity"}
HASH_FIELDS = (
    "approved_proposal_sha256",
    "source_manifest_sha256",
    "input_manifest_sha256",
    "prompt_sha256",
    "game_sha256",
    "ontology_sha256",
    "oracle_sha256",
)
BOUND_FILE_FIELDS = {
    "approved_proposal_sha256": "approved_proposal",
    "source_manifest_sha256": "source_manifest",
    "input_manifest_sha256": "input_manifest",
    "prompt_sha256": "prompt",
    "game_sha256": "game",
    "ontology_sha256": "ontology",
    "oracle_sha256": "oracle",
}

ACTIVATION_SCHEMA = "runtime-native-activation/2"
ACTIVATION_KIND = "human_approved_native_launch"
TRUSTED_PURPOSES = {"production_native", "test_simulation"}
SOURCE_ROLES = {"controller", "game", "schema", "oracle", "representation", "goal_oracle"}
INPUT_ROLES = {
    "public_prompt",
    "public_quest",
    "public_game_state",
    "action_schema",
    "output_schema",
    "representation",
}
_ACTIVATION_HASH_FIELDS = (
    *HASH_FIELDS,
    "output_schema_sha256",
    "allowed_requests_sha256",
)
_ACTIVATION_EVIDENCE_FIELDS = (
    "public_input_receipt_sha256",
    "identity_setting_receipt_sha256",
    "context_isolation_receipt_sha256",
    "subscription_receipt_sha256",
)

_CODEX_TOOL_CATALOG_PATH = Path(__file__).with_name("codex_no_tools_models.json")
_CODEX_TOOL_CATALOG_SHA256 = "5293550d74b5ceea7e3c528799fe8a992cbcd215ea326516c4a1bc011c035d36"
_CODEX_NO_TOOLS_FEATURES = (
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
)


def _billing_authorized(data: Any, policy: Any, strict_field: str) -> bool:
    if not isinstance(data, Mapping):
        return False
    if policy == "included_only":
        return data.get(strict_field) is True
    if policy != "existing_credits_no_new_purchase":
        return False
    # Credit permission is not evidence of zero cost or included-only usage.
    return (
        data.get(strict_field) is False
        and data.get("existing_credit_consumption_authorized") is True
        and data.get("automatic_reload_off_verified") is True
        and data.get("native_account_match_verified") is True
        and data.get("new_credit_purchase_authorized") is False
        and data.get("api_key_fallback_authorized") is False
    )


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    return value


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


@dataclass(frozen=True)
class NativeActivationTrust:
    activation_sha256: str
    plan_sha256: str
    row_id: str
    row_sha256: str
    activation: Mapping[str, Any]
    row: Mapping[str, Any]
    purpose: str = "production_native"
    origin: str = "trusted_bootstrap"
    source_root: str | None = None


class PromptTransportError(RuntimeError):
    """A genuine local transport or process-launch failure."""


def _canonical_bytes(value: Any) -> bytes:
    return _json(value).encode("utf-8")


def _bound_json_object(
    path: str | Path, *, trust_root: Path, label: str
) -> tuple[bytes, dict[str, Any]]:
    candidate = Path(path)
    try:
        resolved_root = trust_root.resolve()
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (resolved_root / candidate).resolve()
        )
        resolved.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label}_path_escape") from exc
    if _private_path(resolved.relative_to(resolved_root)):
        raise ValueError(f"{label}_private_path_rejected")
    raw = _read_bound_bytes(resolved)
    if raw is None:
        raise ValueError(f"{label}_unreadable_or_oversized")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"json_invalid:{path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")  # noqa: TRY004 -- JSON validation contract.
    return raw, value


def _validate_allowed_requests(bindings: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    rows = bindings.get("allowed_requests")
    # Four public states may recur under twelve request IDs; dispatch remains capped at twelve.
    if not isinstance(rows, (list, tuple)) or not 1 <= len(rows) <= 48:
        raise ValueError("native_activation_allowed_requests_cardinality_invalid")
    keys = ("instruction_sha256", "user_prompt_sha256", "output_schema_sha256")
    normalized: list[dict[str, str]] = []
    for row in rows:
        if not isinstance(row, Mapping) or set(row) != set(keys):
            raise ValueError("native_activation_allowed_request_shape_invalid")
        if any(not _is_sha256(row.get(key)) for key in keys):
            raise ValueError("native_activation_allowed_request_digest_invalid")
        normalized.append({key: str(row[key]) for key in keys})
    sort_key = lambda row: tuple(row[key] for key in keys)
    if normalized != sorted(normalized, key=sort_key):
        raise ValueError("native_activation_allowed_requests_order_invalid")
    if len({sort_key(row) for row in normalized}) != len(normalized):
        raise ValueError("native_activation_allowed_requests_duplicate")
    digest = bindings.get("allowed_requests_sha256")
    if not _is_sha256(digest) or _sha256(_canonical_bytes(normalized)) != digest:
        raise ValueError("native_activation_allowed_requests_digest_mismatch")
    return tuple(normalized)


def load_pinned_native_activation(
    *,
    activation_path: str | Path,
    activation_sha256: str,
    plan_path: str | Path,
    plan_sha256: str,
    row_id: str,
    purpose: str = "production_native",
    origin: str | None = None,
    trust_root: str | Path | None = None,
    source_root: str | Path | None = None,
    now: Any = None,
) -> NativeActivationTrust:
    """Load one externally pinned launch decision and one exact frozen plan row."""
    if purpose not in TRUSTED_PURPOSES:
        raise ValueError("native_activation_purpose_invalid")
    expected_origin = "test_only" if purpose == "test_simulation" else "trusted_bootstrap"
    if origin is not None and origin != expected_origin:
        raise ValueError("native_activation_origin_invalid")
    if trust_root is None or source_root is None:
        raise ValueError("native_activation_roots_required")
    try:
        trusted_root = Path(trust_root).resolve()
        trusted_source = Path(source_root).resolve()
        if not trusted_root.is_dir() or not trusted_source.is_dir():
            raise ValueError("native_activation_roots_invalid")
        try:
            trusted_root.relative_to(trusted_source)
            raise ValueError("native_activation_trust_root_must_be_external")
        except ValueError as first:
            if str(first) == "native_activation_trust_root_must_be_external":
                raise
        try:
            trusted_source.relative_to(trusted_root)
            raise ValueError("native_activation_trust_root_must_be_external")
        except ValueError as second:
            if str(second) == "native_activation_trust_root_must_be_external":
                raise
    except OSError as exc:
        raise ValueError("native_activation_roots_invalid") from exc
    if not _is_sha256(activation_sha256) or not _is_sha256(plan_sha256):
        raise ValueError("native_activation_digest_invalid")
    activation_raw, activation = _bound_json_object(
        activation_path, trust_root=trusted_root, label="native_activation"
    )
    plan_raw, plan = _bound_json_object(plan_path, trust_root=trusted_root, label="native_plan")
    if _sha256(activation_raw) != activation_sha256:
        raise ValueError("native_activation_digest_mismatch")
    if _sha256(plan_raw) != plan_sha256:
        raise ValueError("native_activation_plan_digest_mismatch")
    if activation.get("schema_version") != ACTIVATION_SCHEMA:
        raise ValueError("native_activation_schema_mismatch")
    if activation.get("kind") != ACTIVATION_KIND:
        raise ValueError("native_activation_kind_mismatch")
    if plan.get("schema_version") != ASSIGNMENT_PLAN_SCHEMA:
        raise ValueError("native_activation_plan_schema_mismatch")
    if not isinstance(row_id, str) or not row_id:
        raise ValueError("native_activation_row_id_invalid")
    expires = _parse_time(activation.get("expires_at"))
    if expires is None or _now_value(now) >= expires:
        raise ValueError("native_activation_expired_or_invalid")
    permissions = activation.get("permissions")
    if not isinstance(permissions, Mapping) or any(
        permissions.get(key) is not True
        for key in (
            "native_launch",
            "research_context_transmission",
            "scientific_assignment",
            "generation",
            "egress",
        )
    ):
        raise ValueError("native_activation_permissions_invalid")
    billing_policy = activation.get("billing_policy", "included_only")
    if not _billing_authorized(permissions, billing_policy, "no_additional_charge_verified"):
        raise ValueError("native_activation_billing_policy_invalid")
    rows = plan.get("rows")
    if not isinstance(rows, list) or len(rows) != 20:
        raise ValueError("native_activation_plan_requires_exactly_twenty_rows")
    expected_targets = (
        ("GPT-6.1-SOL", "codex", "gpt-6.1-sol", "medium"),
        ("GPT-5.6-SOL", "codex", "gpt-5.6-sol", "medium"),
        ("Claude Opus 5.5", "claude_code", "opus", "medium"),
        ("Claude Sonnet 5.5", "claude_code", "sonnet", "medium"),
        ("Gemini 3.8 Flash", "antigravity", "gemini-3.8-flash-medium", "medium"),
    )
    if plan.get("status") != "planned" or not isinstance(plan.get("quest_id"), str):
        raise ValueError("native_activation_plan_header_invalid")
    if plan.get("counts") != {"quests": 1, "targets": 5, "representations": 2, "repeats": 2}:
        raise ValueError("native_activation_plan_counts_invalid")
    if plan.get("assigned_ids") != [] or plan.get("scientific") != {
        "assigned": 0,
        "executed": 0,
        "eligible": False,
    }:
        raise ValueError("native_activation_plan_scientific_state_invalid")
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise ValueError("native_activation_row_invalid")  # noqa: TRY004 -- JSON validation contract.
        target_index, remainder = divmod(index, 4)
        representation_index, repeat_index = divmod(remainder, 2)
        family, host, selector, effort = expected_targets[target_index]
        representation = ("general_rule", "ontology")[representation_index]
        expected_id = f"{plan['quest_id']}:{selector}:{representation}:repeat-{repeat_index + 1}"
        expected = {
            "planned_id": expected_id,
            "assignment_id": expected_id,
            "quest_id": plan["quest_id"],
            "target": {
                "family_label": family,
                "host": host,
                "selector": selector,
                "effort": effort,
            },
            "representation": representation,
            "repeat": repeat_index + 1,
            "seed": plan.get("seed"),
            "order": index,
            "reset": True,
            "status": "planned",
            "scientific_assignment": False,
            "executed": False,
        }
        if any(row.get(key) != value for key, value in expected.items()):
            raise ValueError("native_activation_plan_row_drift")
        if not _is_sha256(row.get("source_manifest_sha256")) or not _is_sha256(
            row.get("input_manifest_sha256")
        ):
            raise ValueError("native_activation_plan_manifest_hash_invalid")
        if not isinstance(row.get("fixture_id"), str) or not _is_sha256(row.get("fixture_sha256")):
            raise ValueError("native_activation_plan_fixture_binding_invalid")
    rows_by_id = {row["planned_id"]: row for row in rows}
    selected = rows_by_id.get(row_id)
    if selected is None:
        raise ValueError("native_activation_plan_row_missing_or_duplicate")
    plan_binding = activation.get("plan")
    if (
        not isinstance(plan_binding, Mapping)
        or plan_binding.get("schema_version") != ASSIGNMENT_PLAN_SCHEMA
        or plan_binding.get("sha256") != plan_sha256
        or plan_binding.get("row_id") != row_id
        or not _is_sha256(plan_binding.get("row_sha256"))
        or _sha256(_canonical_bytes(selected)) != plan_binding.get("row_sha256")
    ):
        raise ValueError("native_activation_plan_row_binding_invalid")
    binding = activation.get("row_binding")
    target = selected.get("target")
    if not isinstance(binding, Mapping) or not isinstance(target, Mapping):
        raise ValueError("native_activation_row_binding_missing")  # noqa: TRY004 -- JSON validation contract.
    if billing_policy == "existing_credits_no_new_purchase" and target.get("host") != "codex":
        raise ValueError("native_activation_credit_policy_host_invalid")
    expected_binding = {
        "assignment_id": selected.get("assignment_id"),
        "quest_id": selected.get("quest_id"),
        "host": target.get("host"),
        "selector": target.get("selector"),
        "effort": target.get("effort"),
        "representation": selected.get("representation"),
        "repeat": selected.get("repeat"),
        "seed": selected.get("seed"),
        "reset": selected.get("reset"),
        "fixture_id": selected.get("fixture_id"),
        "fixture_sha256": selected.get("fixture_sha256"),
        "oracle_sha256": activation.get("artifact_bindings", {}).get("oracle_sha256")
        if isinstance(activation.get("artifact_bindings"), Mapping)
        else None,
    }
    if any(binding.get(key) != value for key, value in expected_binding.items()):
        raise ValueError("native_activation_row_binding_mismatch")
    artifact_bindings = activation.get("artifact_bindings")
    if not isinstance(artifact_bindings, Mapping) or any(
        not _is_sha256(artifact_bindings.get(field)) for field in _ACTIVATION_HASH_FIELDS
    ):
        raise ValueError("native_activation_artifact_bindings_invalid")
    if selected.get("source_manifest_sha256") != artifact_bindings.get(
        "source_manifest_sha256"
    ) or selected.get("input_manifest_sha256") != artifact_bindings.get("input_manifest_sha256"):
        raise ValueError("native_activation_row_manifest_binding_mismatch")
    evidence_digests = activation.get("evidence_digests")
    required_evidence = list(_ACTIVATION_EVIDENCE_FIELDS)
    _validate_allowed_requests(artifact_bindings)
    if not isinstance(evidence_digests, Mapping) or any(
        not _is_sha256(evidence_digests.get(field)) for field in required_evidence
    ):
        raise ValueError("native_activation_evidence_bindings_invalid")
    frozen_activation = _freeze(dict(activation))
    frozen_row = _freeze(dict(selected))
    return NativeActivationTrust(
        activation_sha256=activation_sha256,
        plan_sha256=plan_sha256,
        row_id=row_id,
        row_sha256=str(plan_binding["row_sha256"]),
        activation=frozen_activation,
        row=frozen_row,
        purpose=purpose,
        origin=origin or expected_origin,
        source_root=str(trusted_source),
    )


def _sanitized_environment() -> dict[str, str]:
    # Native OAuth stays in HOME; no ambient credentials, endpoints, or model overrides.
    allowed = {"HOME", "PATH", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL", "LC_CTYPE", "TERM"}
    return {key: value for key, value in os.environ.items() if key in allowed}


def _json(value: Any) -> str:
    return json.dumps(
        _plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _sha256(value: Any) -> str:
    if isinstance(value, bytes):
        payload = value
    elif isinstance(value, str):
        payload = value.encode("utf-8")
    else:
        payload = _json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _safe_text(value: Any, limit: int = 64 * 1024) -> str:
    text = value if isinstance(value, str) else str(value or "")
    return text.encode("utf-8", errors="backslashreplace").decode("utf-8")[:limit]


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _now_value(value: Any) -> datetime:
    parsed = _parse_time(value)
    if parsed is not None:
        return parsed
    return datetime.now(UTC)


def _verified(receipt: Any, *, engineering_fixture: bool = False) -> bool:
    if not isinstance(receipt, Mapping) or receipt.get("status") != "verified":
        return False
    if engineering_fixture:
        return True
    return receipt.get("source_bound") is True


MAX_BOUND_FILE_BYTES = 8 * 1024 * 1024
_DENIED_PATH_SEGMENTS = {
    ".git",
    ".ssh",
    ".aws",
    ".config",
    ".gnupg",
    ".secrets",
    ".claude",
    ".agents",
    ".codex",
    "account",
    "accounts",
    "llm-wiki",
    "auth",
    "credentials",
    "credential",
    "private",
    "raw",
    "wiki",
    "secret",
    "secrets",
    "password",
    "token",
}
_DENIED_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".crt", ".cer")
_DENIED_NAMES = {"id_rsa", "id_ed25519", "authorized_keys"}


def _private_path(path: Path) -> bool:
    for part in path.parts:
        name = part.casefold()
        if name in _DENIED_PATH_SEGMENTS or name in _DENIED_NAMES:
            return True
        if name.startswith(".env") or name.endswith(_DENIED_SUFFIXES):
            return True
        if name.startswith(("auth.", "credential.", "credentials.", "secret.", "secrets.")):
            return True
        if any(token in name for token in ("credential", "password", "private_key", "secret_key")):
            return True
    return False


def _resolve_bound_path(root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str):
        return None, "path_invalid"
    relative = Path(value)
    if relative.is_absolute():
        return None, "path_escape"
    if _private_path(relative):
        return None, "private_path_rejected"
    try:
        path = (root / relative).resolve()
        path.relative_to(root)
    except (OSError, ValueError):
        return None, "path_escape"
    if _private_path(path.relative_to(root)):
        return None, "private_path_rejected"
    return path, None


def _read_bound_bytes(path: Path, limit: int = MAX_BOUND_FILE_BYTES) -> bytes | None:
    try:
        if not path.is_file() or path.stat().st_size > limit:
            return None
        raw = path.read_bytes()
        return raw if len(raw) <= limit else None
    except OSError:
        return None


def validate_manifest(
    path: str | Path | None,
    *,
    kind: str,
    mode: str = "engineering_fixture",
    source_root: str | Path | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate a manifest and its declared leaves without recursive manifest loading."""
    if path is None:
        return {"kind": kind, "status": "missing", "sha256": None, "path": None}
    manifest_path = Path(path)
    if source_root is not None:
        root = Path(source_root).resolve()
        resolved, error = _resolve_bound_path(
            root, str(path) if not manifest_path.is_absolute() else ""
        )
        if manifest_path.is_absolute():
            try:
                resolved = manifest_path.resolve()
                resolved.relative_to(root)
                error = (
                    None
                    if not _private_path(resolved.relative_to(root))
                    else "private_path_rejected"
                )
            except (OSError, ValueError):
                resolved, error = None, "path_escape"
        if resolved is None or error is not None:
            return {
                "kind": kind,
                "status": "unresolved",
                "sha256": None,
                "path": str(path),
                "reason": error,
            }
        manifest_path = resolved
    raw = _read_bound_bytes(manifest_path)
    if raw is None:
        return {
            "kind": kind,
            "status": "unresolved",
            "sha256": None,
            "path": str(manifest_path),
            "reason": "manifest_unreadable",
        }
    digest = _sha256(raw)
    receipt: dict[str, Any] = {
        "kind": kind,
        "status": "verified",
        "sha256": digest,
        "path": str(manifest_path),
        "engineering_only": False,
    }
    if expected_sha256 is not None and digest != expected_sha256:
        receipt.update(status="unresolved", reason="manifest_digest_mismatch")
        return receipt
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(f"{kind}_manifest_invalid")
    if not isinstance(payload, Mapping):
        raise ValueError(f"{kind}_manifest_invalid")  # noqa: TRY004 -- JSON validation contract.
    publicity = payload.get("publicity") or payload.get("public_input")
    receipt["engineering_only"] = payload.get("engineering_only") is True
    included = payload.get("included_categories")
    if isinstance(included, list):
        forbidden = {
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
        }
        if any(
            any(
                token in str(category).casefold().replace("-", " ").replace("_", " ")
                for token in forbidden
            )
            for category in included
        ):
            receipt.update(status="unresolved", reason="included_forbidden_category")
    if mode != "native":
        if not isinstance(publicity, Mapping) or publicity.get("status") != "verified":
            receipt.update(status="unresolved", reason="publicity_unverified")
        return receipt
    schema = f"runtime-native-{kind}-manifest/1"
    entries = payload.get("files")
    if payload.get("schema_version") != schema or not isinstance(entries, list):
        receipt.update(status="unresolved", reason="manifest_schema_mismatch")
        return receipt
    if payload.get("synthetic") is not False:
        receipt.update(status="unresolved", reason="manifest_synthetic_forbidden")
    if payload.get("engineering_only") is not False:
        receipt.update(status="unresolved", reason="manifest_engineering_only")
    if (
        not isinstance(publicity, Mapping)
        or publicity.get("status") != "verified"
        or publicity.get("actual_publicity") != "verified_public"
    ):
        receipt.update(status="unresolved", reason="manifest_publicity_unresolved")
    root = (
        Path(source_root).resolve() if source_root is not None else manifest_path.parent.resolve()
    )
    allowed = SOURCE_ROLES if kind == "source" else INPUT_ROLES
    for entry in entries:
        if (
            not isinstance(entry, Mapping)
            or not isinstance(entry.get("path"), str)
            or not _is_sha256(entry.get("sha256"))
        ):
            receipt.update(status="unresolved", reason="manifest_entry_invalid")
            continue
        role = str(entry.get("role", ""))
        if role not in allowed or role.casefold() in {
            "manifest",
            "receipt",
            "archive",
            "raw",
            "private",
            "account",
            "auth",
            "credential",
            "secret",
            "repository",
            "wiki",
            "unverified",
        }:
            receipt.update(status="unresolved", reason="manifest_role_forbidden")
            continue
        listed, path_error = _resolve_bound_path(root, entry["path"])
        if listed is None or path_error is not None:
            receipt.update(status="unresolved", reason=f"manifest_{path_error or 'path_invalid'}")
            continue
        listed_raw = _read_bound_bytes(listed)
        if listed_raw is None or _sha256(listed_raw) != entry["sha256"]:
            receipt.update(status="unresolved", reason="manifest_file_content_mismatch")
    return receipt


def _receipt_artifact_bound(
    receipt: Mapping[str, Any],
    *,
    context: Mapping[str, Any],
    context_model: Mapping[str, Any],
    hashes: Mapping[str, Any],
    source_root: str | Path | None,
    evidence_name: str | None = None,
    trusted_activation: NativeActivationTrust | None = None,
) -> bool:
    if source_root is None or not isinstance(receipt, Mapping):
        return False
    artifact = receipt.get("receipt_artifact")
    if (
        not isinstance(artifact, Mapping)
        or set(artifact) != {"path", "sha256"}
        or not _is_sha256(artifact.get("sha256"))
    ):
        return False
    root = Path(source_root).resolve()
    path, path_error = _resolve_bound_path(root, artifact.get("path"))
    if path is None or path_error is not None:
        return False
    raw = _read_bound_bytes(path)
    if raw is None or _sha256(raw) != artifact.get("sha256"):
        return False
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(body, Mapping):
        return False
    if (
        body.get("kind") != "runtime-native-evidence/1"
        or not isinstance(body.get("evidence"), str)
        or (evidence_name is not None and body.get("evidence") != evidence_name)
        or body.get("status") != "verified"
        or body.get("source_bound") is not True
    ):
        return False
    if body.get("study_id") != context.get("study_id") or body.get("assignment_id") != context.get(
        "assignment_id"
    ):
        return False
    if (
        body.get("host") != context_model.get("host")
        or body.get("model_selector") != context_model.get("selector")
        or body.get("representation") != context_model.get("representation")
        or body.get("model_revision") != context_model.get("revision")
        or body.get("effort") != context_model.get("effort")
    ):
        return False
    if body.get("source_manifest_sha256") != hashes.get("source_manifest_sha256") or body.get(
        "input_manifest_sha256"
    ) != hashes.get("input_manifest_sha256"):
        return False
    authority = context.get("authority")
    if not isinstance(authority, Mapping) or body.get("authority") != dict(authority):
        return False
    permissions = body.get("permissions")
    if (
        not isinstance(permissions, Mapping)
        or permissions.get("generation") is not True
        or permissions.get("egress") is not True
    ):
        return False
    if isinstance(trusted_activation, NativeActivationTrust):
        evidence_digests = trusted_activation.activation.get("evidence_digests")
        digest_key = {
            "public_input": "public_input_receipt_sha256",
            "identity_setting": "identity_setting_receipt_sha256",
            "context_isolation": "context_isolation_receipt_sha256",
            "subscription": "subscription_receipt_sha256",
            "activation": "activation_receipt_sha256",
            "effective-isolation": "effective_tool_context_receipt_sha256",
        }.get(evidence_name)
        if (
            not isinstance(evidence_digests, Mapping)
            or digest_key is None
            or artifact.get("sha256") != evidence_digests.get(digest_key)
        ):
            return False
    if evidence_name == "public_input":
        expected = receipt.get("allowed_requests_sha256")
        if expected != body.get("allowed_requests_sha256"):
            return False
        if isinstance(trusted_activation, NativeActivationTrust):
            bindings = trusted_activation.activation.get("artifact_bindings")
            if not isinstance(bindings, Mapping) or expected != bindings.get(
                "allowed_requests_sha256"
            ):
                return False
    if evidence_name == "identity_setting":
        if (
            body.get("host") != receipt.get("host", context_model.get("host"))
            or body.get("model_selector", body.get("selector"))
            != receipt.get("selector", context_model.get("selector"))
            or body.get("effort") != receipt.get("effort", context_model.get("effort"))
        ):
            return False
        if context_model.get("host") == "antigravity":
            approved = (
                context_model.get("approved_agent")
                or context_model.get("agent")
                or context_model.get("profile")
            )
            if body.get("approved_agent") != approved:
                return False
    if evidence_name == "context_isolation" and (
        body.get("tools") != "none" or body.get("workspace") not in {"temporary", "isolated"}
    ):
        return False
    if evidence_name == "subscription":
        policy = context.get("billing_policy", "included_only")
        return body.get("billing_policy", "included_only") == policy and _billing_authorized(
            body, policy, "no_additional_charge"
        )
    return True


def _base_bindings(context: Mapping[str, Any]) -> dict[str, Any]:
    hashes = context.get("hashes")
    files = context.get("bound_files")
    return {
        "hashes": dict(hashes) if isinstance(hashes, Mapping) else {},
        "bound_files": dict(files) if isinstance(files, Mapping) else {},
        "study_id": context.get("study_id"),
        "assignment_id": context.get("assignment_id"),
    }


def validate_native_context(
    context: Mapping[str, Any] | None,
    *,
    model: Mapping[str, Any],
    config: Mapping[str, Any],
    prompt: str,
    source_root: str | Path | None = None,
    now: Any = None,
    trusted_activation: NativeActivationTrust | None = None,
) -> dict[str, Any]:
    """Validate a source-bound activation context before any process is created.

    ``ready`` is derived from bound files and receipts.  The caller supplied
    ``ready`` member is intentionally ignored.  Engineering fixtures can be
    admitted only as synthetic, non-scientific runs; real native mode requires a
    separate source-bound activation receipt in addition to preparation evidence.
    """

    if not isinstance(context, Mapping):
        return {
            "schema_version": NATIVE_CONTEXT_SCHEMA,
            "ready": False,
            "mode": None,
            "trust_state": "missing",
            "launch_authorized": False,
            "scientific_eligible": False,
            "reasons": ["context_missing"],
            "bindings": {},
        }
    mode = context.get("execution_mode")
    trust_state = (
        trusted_activation.purpose
        if isinstance(trusted_activation, NativeActivationTrust)
        else "missing"
    )
    result: dict[str, Any] = {
        "schema_version": NATIVE_CONTEXT_SCHEMA,
        "ready": False,
        "mode": mode,
        "trust_state": trust_state,
        "launch_authorized": False,
        "scientific_eligible": False,
        "reasons": [],
        "bindings": _base_bindings(context),
    }
    reasons: list[str] = result["reasons"]
    if mode == "native" and trusted_activation is None:
        reasons.append("trusted_activation_missing")
        result["reasons"] = reasons
        return result
    if mode == "native" and not isinstance(trusted_activation, NativeActivationTrust):
        reasons.append("trusted_activation_invalid")
        result["reasons"] = reasons
        return result
    if mode != "native" and trusted_activation is not None:
        reasons.append("trusted_activation_mode_mismatch")
    if mode == "native" and isinstance(trusted_activation, NativeActivationTrust):
        expected_origin = (
            "test_only" if trusted_activation.purpose == "test_simulation" else "trusted_bootstrap"
        )
        if (
            trusted_activation.purpose not in TRUSTED_PURPOSES
            or trusted_activation.origin != expected_origin
        ):
            reasons.append("trusted_activation_origin_invalid")
        if _sha256(_canonical_bytes(trusted_activation.row)) != trusted_activation.row_sha256:
            reasons.append("trusted_row_digest_mismatch")
        if (
            source_root is not None
            and Path(source_root).resolve() != Path(trusted_activation.source_root or "").resolve()
        ):
            reasons.append("trusted_source_root_mismatch")
        source_root = trusted_activation.source_root
    elif mode == "native" and source_root is None:
        reasons.append("trusted_source_root_missing")
    reasons: list[str] = result["reasons"]
    if context.get("schema_version") != NATIVE_CONTEXT_SCHEMA:
        reasons.append("schema_mismatch")
    if mode not in {"engineering_fixture", "native"}:
        reasons.append("unsupported_execution_mode")
    if mode == "native" and model.get("offline") is True:
        reasons.append("native_mode_marked_offline")

    assignment_id = config.get("assignment_id")
    if assignment_id is not None and context.get("assignment_id") != assignment_id:
        reasons.append("assignment_mismatch")
    if config.get("study_id") is not None and context.get("study_id") != config.get("study_id"):
        reasons.append("study_mismatch")

    context_model = context.get("model")
    if not isinstance(context_model, Mapping):
        reasons.append("model_missing")
        context_model = {}
    host = context_model.get("host")
    selector = context_model.get("selector")
    representation = context_model.get("representation")
    effort = context_model.get("effort")
    billing_policy = context.get("billing_policy", "included_only")
    result["billing_policy"] = billing_policy
    if billing_policy == "existing_credits_no_new_purchase" and host != "codex":
        reasons.append("credit_policy_host_invalid")
    if mode == "native" and (model.get("offline") is True or context_model.get("offline") is True):
        reasons.append("native_mode_marked_offline")
    if host not in SUPPORTED_HOSTS:
        reasons.append("unsupported_host")
    if not isinstance(selector, str) or not selector:
        reasons.append("selector_missing")
    if representation not in {"general_rule", "ontology"}:
        reasons.append("representation_invalid")
    if effort != "medium":
        reasons.append("effort_mismatch")
    approved_agent = (
        context_model.get("approved_agent")
        or context_model.get("agent")
        or context_model.get("profile")
    )
    if mode == "native" and host == "antigravity" and not isinstance(approved_agent, str):
        reasons.append("antigravity_approved_agent_missing")
    for key in ("host", "selector", "representation", "effort"):
        requested = model.get(key)
        if requested is not None and requested != context_model.get(key):
            reasons.append(f"model_{key}_mismatch")
    if config.get("model_selector") is not None and config.get("model_selector") != selector:
        reasons.append("selector_config_mismatch")
    if config.get("representation") is not None and config.get("representation") != representation:
        reasons.append("representation_config_mismatch")
    if config.get("effort") is not None and config.get("effort") != effort:
        reasons.append("effort_config_mismatch")

    hashes = context.get("hashes")
    bound_files = context.get("bound_files")
    if not isinstance(hashes, Mapping):
        reasons.append("hashes_missing")
        hashes = {}
    if not isinstance(bound_files, Mapping):
        reasons.append("bindings_missing")
        bound_files = {}
    for field in HASH_FIELDS:
        value = hashes.get(field)
        if not _is_sha256(value):
            reasons.append(f"{field}_invalid")
            continue
        bound_name = BOUND_FILE_FIELDS[field]
        binding = bound_files.get(bound_name)
        if not isinstance(binding, Mapping) or binding.get("sha256") != value:
            reasons.append(f"{field}_binding_mismatch")
        expected = config.get(field)
        if expected is not None and expected != value:
            reasons.append(f"{field}_config_mismatch")
    if config.get("prompt_sha256") is not None and config.get("prompt_sha256") != _sha256(prompt):
        reasons.append("prompt_content_mismatch")
    if mode == "native" and isinstance(trusted_activation, NativeActivationTrust):
        selected = trusted_activation.row
        target = selected.get("target") if isinstance(selected, Mapping) else None
        activation = trusted_activation.activation
        if activation.get("billing_policy", "included_only") != billing_policy:
            reasons.append("trusted_billing_policy_mismatch")
        if not _billing_authorized(
            activation.get("permissions"), billing_policy, "no_additional_charge_verified"
        ):
            reasons.append("trusted_billing_authority_invalid")
        artifact_bindings = (
            activation.get("artifact_bindings") if isinstance(activation, Mapping) else None
        )
        if not isinstance(target, Mapping) or not isinstance(artifact_bindings, Mapping):
            reasons.append("trusted_activation_binding_invalid")
        else:
            expected_model = {
                "host": target.get("host"),
                "selector": target.get("selector"),
                "representation": selected.get("representation"),
                "effort": target.get("effort"),
            }
            for key, expected in expected_model.items():
                if context_model.get(key) != expected or model.get(key) not in {None, expected}:
                    reasons.append(f"trusted_row_{key}_mismatch")
            if context.get("assignment_id") != selected.get("assignment_id"):
                reasons.append("trusted_row_assignment_mismatch")
            if context.get("study_id") != activation.get("study_id"):
                reasons.append("trusted_activation_study_mismatch")
            if config.get("quest_id") is not None and config.get("quest_id") != selected.get(
                "quest_id"
            ):
                reasons.append("trusted_row_quest_mismatch")
            for field in HASH_FIELDS:
                if hashes.get(field) != artifact_bindings.get(field):
                    reasons.append(f"trusted_{field}_mismatch")
            for field in (
                "output_schema_sha256",
                "allowed_requests_sha256",
                "source_manifest_sha256",
                "input_manifest_sha256",
                "oracle_sha256",
            ):
                supplied = config.get(field) or hashes.get(field) or context.get(field)
                if supplied is not None and supplied != artifact_bindings.get(field):
                    reasons.append(f"trusted_{field}_mismatch")
            row_bindings = {
                "quest_id": selected.get("quest_id"),
                "seed": selected.get("seed"),
                "repeat": selected.get("repeat"),
                "reset": selected.get("reset"),
                "fixture_id": selected.get("fixture_id"),
                "fixture_sha256": selected.get("fixture_sha256"),
                "oracle_sha256": artifact_bindings.get("oracle_sha256"),
            }
            for field, expected in row_bindings.items():
                supplied = config.get(field)
                if supplied is not None and supplied != expected:
                    reasons.append(f"trusted_row_{field}_mismatch")
            activation_expires = _parse_time(activation.get("expires_at"))
            if activation_expires is None or _now_value(now) >= activation_expires:
                reasons.append("trusted_activation_expired")

    bound_bytes: dict[str, bytes] = {}
    if source_root is not None:
        root = Path(source_root).resolve()
        for bound_name, binding in bound_files.items():
            if not isinstance(binding, Mapping):
                reasons.append(f"{bound_name}_path_invalid")
                continue
            path, path_error = _resolve_bound_path(root, binding.get("path"))
            if path is None:
                reasons.append(f"{bound_name}_{path_error or 'path_invalid'}")
                continue
            raw = _read_bound_bytes(path)
            if raw is None or _sha256(raw) != binding.get("sha256"):
                reasons.append(f"{bound_name}_content_mismatch")
                continue
            bound_bytes[bound_name] = raw

        manifest_specs = ("source_manifest", "source"), ("input_manifest", "input")
        for bound_name, kind in manifest_specs:
            binding = bound_files.get(bound_name)
            if not isinstance(binding, Mapping):
                continue
            manifest_path, path_error = _resolve_bound_path(root, binding.get("path"))
            if manifest_path is None or path_error is not None:
                reasons.append(f"{bound_name}_{path_error or 'path_invalid'}")
                continue
            if mode == "native":
                receipt = validate_manifest(
                    manifest_path,
                    kind=kind,
                    mode="native",
                    source_root=root,
                    expected_sha256=binding.get("sha256"),
                )
                if receipt.get("status") != "verified":
                    reasons.append(
                        f"{bound_name}_{receipt.get('reason', 'manifest_rejected').removeprefix('manifest_')}"
                    )

    expires = _parse_time(context.get("expires_at"))
    if expires is None:
        reasons.append("expiry_missing_or_invalid")
    elif _now_value(now) >= expires:
        reasons.append("expired")

    authority = context.get("authority")
    if not isinstance(authority, Mapping):
        reasons.append("authority_missing")
        authority = {}
    required_booleans = (
        "native_activation",
        "public_input_egress",
        "identity_setting_verified",
        "context_isolation_verified",
    )
    for key in required_booleans:
        if authority.get(key) is not True:
            reasons.append(f"authority_{key}_missing")
    if not _billing_authorized(
        authority, billing_policy, "subscription_no_additional_charge_verified"
    ):
        reasons.append("authority_subscription_no_additional_charge_verified_missing")
    if (
        mode == "engineering_fixture"
        and authority.get("research_context_transmission") is not False
    ):
        reasons.append("research_context_transmission_not_denied")
    if authority.get("scientific_launch") is True and mode == "engineering_fixture":
        reasons.append("fixture_scientific_launch_forbidden")

    evidence = context.get("evidence")
    if not isinstance(evidence, Mapping):
        reasons.append("evidence_missing")
        evidence = {}
    for name in ("public_input", "identity_setting", "context_isolation", "subscription"):
        receipt = evidence.get(name)
        if not _verified(receipt, engineering_fixture=mode == "engineering_fixture"):
            reasons.append(f"{name}_evidence_unverified")
        elif mode == "native" and not _receipt_artifact_bound(
            receipt,
            context=context,
            context_model=context_model,
            hashes=hashes,
            source_root=source_root,
            evidence_name=name,
            trusted_activation=trusted_activation,
        ):
            reasons.append(f"{name}_artifact_unbound")
    identity = evidence.get("identity_setting")
    if isinstance(identity, Mapping):
        for key in ("host", "selector", "effort"):
            if identity.get(key) != context_model.get(key):
                reasons.append(f"identity_{key}_mismatch")
        if (
            host == "antigravity"
            and isinstance(approved_agent, str)
            and identity.get("approved_agent", identity.get("agent", identity.get("profile")))
            != approved_agent
        ):
            reasons.append("identity_agent_mismatch")
    isolation = evidence.get("context_isolation")
    if isinstance(isolation, Mapping) and (
        isolation.get("tools") != "none"
        or isolation.get("workspace") not in {"temporary", "isolated"}
    ):
        reasons.append("context_isolation_not_restricted")
    subscription = evidence.get("subscription")
    if isinstance(subscription, Mapping) and (
        subscription.get("billing_policy", "included_only") != billing_policy
        or not _billing_authorized(subscription, billing_policy, "no_additional_charge")
    ):
        reasons.append("subscription_charge_unknown")
    publicity = evidence.get("public_input")
    if isinstance(publicity, Mapping) and publicity.get("status") != "verified":
        reasons.append("publicity_unverified")
    if mode == "native":
        request_binding = (
            publicity.get("allowed_requests_sha256") if isinstance(publicity, Mapping) else None
        )
        if not _is_sha256(request_binding):
            reasons.append("public_input_bytes_unbound")
        if host == "antigravity":
            effective = evidence.get("effective_tool_context")
            if (
                not isinstance(effective, Mapping)
                or effective.get("status") != "verified"
                or effective.get("source_bound") is not True
                or effective.get("tools") != "none"
                or effective.get("workspace") not in {"temporary", "isolated"}
                or not _receipt_artifact_bound(
                    effective,
                    context=context,
                    context_model=context_model,
                    hashes=hashes,
                    source_root=source_root,
                    trusted_activation=trusted_activation,
                    evidence_name="effective-isolation",
                )
            ):
                reasons.append("antigravity_effective_isolation_unverified")

        if authority.get("research_context_transmission") is not True:
            reasons.append("native_egress_not_authorized")
        if authority.get("scientific_launch") is not True:
            reasons.append("scientific_launch_not_authorized")
    elif mode == "engineering_fixture":
        result["scientific_eligible"] = False

    result["reasons"] = list(dict.fromkeys(reasons))
    result["ready"] = not result["reasons"]
    production = (
        result["ready"]
        and mode == "native"
        and isinstance(trusted_activation, NativeActivationTrust)
        and trusted_activation.purpose == "production_native"
    )
    result["launch_authorized"] = production
    result["scientific_eligible"] = production
    if (
        isinstance(trusted_activation, NativeActivationTrust)
        and trusted_activation.purpose == "test_simulation"
    ):
        result["mode"] = "test_simulation"
    if isinstance(trusted_activation, NativeActivationTrust):
        result["bindings"].update(
            activation_sha256=trusted_activation.activation_sha256,
            plan_sha256=trusted_activation.plan_sha256,
            row_id=trusted_activation.row_id,
            row_sha256=trusted_activation.row_sha256,
        )
    result["bindings"]["validated_at"] = _now_value(now).isoformat().replace("+00:00", "Z")
    return result


@dataclass(frozen=True)
class NativePromptResult:
    returncode: int
    payload: dict[str, Any]
    receipt: dict[str, Any]


def run_host_process(
    command: Sequence[str],
    *,
    input: str | bytes | None,
    cwd: str | Path,
    timeout: float,
    env: Mapping[str, str] | None = None,
    on_started: Callable[[], None] | None = None,
    **subprocess_compat: Any,
) -> subprocess.CompletedProcess[Any]:
    """Run a local process in its own group and clean the group on timeout."""

    if not command or any(not isinstance(part, str) or not part for part in command):
        raise ValueError("command_must_be_nonempty_argv")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout_must_be_positive")
    options = dict(subprocess_compat)
    options.pop("check", None)
    capture_output = bool(options.pop("capture_output", False))
    text_mode = bool(options.get("text", False))
    if capture_output:
        options.setdefault("stdout", subprocess.PIPE)
        options.setdefault("stderr", subprocess.PIPE)
    process = subprocess.Popen(
        list(command),
        shell=False,
        cwd=str(cwd),
        env=None if env is None else dict(env),
        stdin=subprocess.PIPE,
        start_new_session=True,
        **options,
    )
    if on_started is not None:
        on_started()
    try:
        stdout, stderr = process.communicate(input=input, timeout=float(timeout))
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, stderr = process.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
        if exc.output is None:
            exc.output = stdout
        if exc.stderr is None:
            exc.stderr = stderr
        raise
    if text_mode:
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _usage(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    aliases = {
        "inputTokens": "input_tokens",
        "outputTokens": "output_tokens",
        "input_tokens": "input_tokens",
        "output_tokens": "output_tokens",
    }
    normalized = {aliases.get(key, key): item for key, item in value.items()}
    return normalized or None


def _json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return dict(parsed) if isinstance(parsed, Mapping) else None
    return None


class NativePromptRunner:
    """Build and parse one bounded request for a selected native host."""

    def __init__(
        self,
        *,
        host: str,
        selector: str,
        effort: str,
        native_context: Mapping[str, Any],
        trusted_activation: NativeActivationTrust | None = None,
        process_runner: Callable[..., subprocess.CompletedProcess[Any]] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.native_context = native_context
        self.trusted_activation = trusted_activation
        self._requested_identity = (host, selector, effort)
        if isinstance(trusted_activation, NativeActivationTrust):
            target = trusted_activation.row.get("target")
            self.host = str(target.get("host")) if isinstance(target, Mapping) else host
            self.selector = str(target.get("selector")) if isinstance(target, Mapping) else selector
            self.effort = str(target.get("effort")) if isinstance(target, Mapping) else effort
            self._identity_mismatch = (host, selector, effort) != (
                self.host,
                self.selector,
                self.effort,
            )
        else:
            self.host, self.selector, self.effort = host, selector, effort
            self._identity_mismatch = False
        self.process_runner = process_runner
        self.clock = clock

    def _receipt(self, request_id: str, *, mode: str, **fields: Any) -> dict[str, Any]:
        receipt = {
            "schema_version": "runtime-native-receipt/1",
            "request_id": request_id,
            "request_id_rebinding": "synthetic"
            if getattr(self.process_runner, "synthetic_request_id_rebinding", False)
            else None,
            "host": self.host,
            "selector": self.selector,
            "effort": self.effort,
            "provider_identity": None,
            "provider_revision": None,
            "effective_effort": None,
            "usage": None,
            "cost_usd": None,
            "cost_estimate_usd": None,
            "cost_source": "unknown",
            "billing_policy": self.native_context.get("billing_policy", "included_only"),
            "mode": mode,
            "transport_kind": "injected_fixture"
            if self.process_runner is not None
            else "local_process",
            "local_process_started": False,
            "scientific_eligible": False if mode == "engineering_fixture" else None,
            "attempted": False,
            "dispatch_started": False,
            "runner_injected": self.process_runner is not None,
        }
        if isinstance(self.trusted_activation, NativeActivationTrust):
            receipt.update(
                activation_sha256=self.trusted_activation.activation_sha256,
                plan_sha256=self.trusted_activation.plan_sha256,
                row_id=self.trusted_activation.row_id,
                mode=mode,
            )
        receipt.update(fields)
        return receipt

    def _command(self, scratch: Path, output_schema: Any, output_last: Path) -> list[str]:
        schema = str(output_schema) if output_schema is not None else str(scratch / "schema.json")
        if self.host == "codex":
            try:
                import codex_oauth_llm as helper
            except ImportError:
                import importlib.util

                helper_path = Path(__file__).resolve().parents[2] / "scripts" / "codex_oauth_llm.py"
                spec = importlib.util.spec_from_file_location("native_codex_oauth_llm", helper_path)
                if spec is None or spec.loader is None:
                    raise RuntimeError("codex_feature_contract_unavailable")
                helper = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(helper)
            features = getattr(helper, "TOOL_POLICY_FEATURES", None)
            if not features:
                raise RuntimeError("codex_feature_contract_unavailable")
            catalog_bytes = _read_bound_bytes(_CODEX_TOOL_CATALOG_PATH)
            if catalog_bytes is None:
                raise ValueError("codex_tool_catalog_unavailable")
            if _sha256(catalog_bytes) != _CODEX_TOOL_CATALOG_SHA256:
                raise ValueError("codex_tool_catalog_mismatch")
            catalog_path = scratch / "codex-models.json"
            catalog_path.write_bytes(catalog_bytes)

            command = ["codex", "exec", "--json", "--strict-config"]
            for feature in features:
                command.extend(("--disable", feature))
            for feature in _CODEX_NO_TOOLS_FEATURES:
                command.extend(("--disable", feature))

            command.extend(
                [
                    "--output-schema",
                    schema,
                    "--output-last-message",
                    str(output_last),
                    "--ephemeral",
                    "--skip-git-repo-check",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "-c",
                    f"model_catalog_json={json.dumps(str(catalog_path))}",
                    "-c",
                    "agents.enabled=false",
                    "-c",
                    "tools.experimental_request_user_input.enabled=false",
                    "-c",
                    "tools.update_plan.enabled=false",
                    "-c",
                    'web_search="disabled"',
                    "-c",
                    "project_doc_max_bytes=0",
                    "-c",
                    "memories.use_memories=false",
                    "-c",
                    "memories.generate_memories=false",
                    "-c",
                    "cloud.skills.enabled=false",
                    "-c",
                    'cli_auth_credentials_store="file"',
                    "-c",
                    'model_reasoning_effort="medium"',
                    "--model",
                    self.selector,
                    "-",
                ]
            )
            return command
        if self.host == "claude_code":
            empty_mcp = scratch / "empty-mcp.json"
            try:
                claude_schema = Path(schema).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                claude_schema = schema
            empty_mcp.write_text("{}", encoding="utf-8")
            return [
                "claude",
                "--print",
                "--output-format",
                "json",
                "--json-schema",
                claude_schema,
                "--model",
                self.selector,
                "--effort",
                "medium",
                "--safe-mode",
                "--tools",
                "",
                "--strict-mcp-config",
                "--mcp-config",
                str(empty_mcp),
                "--no-session-persistence",
                "--disable-slash-commands",
            ]
        command = [
            "agy",
            "--print",
            "--input-format",
            "text",
            "--output-format",
            "json",
            "--json-schema",
            schema,
            "--model",
            self.selector,
            "--effort",
            "medium",
            "--disable-slash-commands",
        ]
        model = self.native_context.get("model")
        approved_agent = (
            model.get("approved_agent") or model.get("agent") or model.get("profile")
            if isinstance(model, Mapping)
            else None
        )
        if isinstance(approved_agent, str) and approved_agent:
            command.extend(("--agent", approved_agent))
        return command

    def _parse(
        self, completed: subprocess.CompletedProcess[Any], output_last: Path
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        usage: dict[str, Any] | None = None
        cost_estimate: float | None = None
        envelope: dict[str, Any] | None = None
        stdout = (
            completed.stdout.decode("utf-8", errors="replace")
            if isinstance(completed.stdout, bytes)
            else str(completed.stdout or "")
        )
        if self.host == "codex":
            for line in stdout.splitlines():
                item = _json_object(line)
                if not item:
                    continue
                if item.get("type") == "turn.completed":
                    usage = _usage(item.get("usage")) or usage
                nested = item.get("item")
                if (
                    envelope is None
                    and item.get("type") == "item.completed"
                    and isinstance(nested, Mapping)
                ):
                    envelope = _json_object(nested.get("text")) or _json_object(
                        nested.get("output")
                    )
            if output_last.is_file():
                try:
                    envelope = _json_object(output_last.read_text(encoding="utf-8")) or envelope
                except (OSError, UnicodeError):
                    pass
            if envelope is None:
                envelope = _json_object(stdout)
        else:
            envelope = _json_object(stdout)
        if envelope is None:
            return None, {"error": "malformed_response", "usage": usage}
        if self.host == "claude_code":
            if envelope.get("type") != "result":
                return None, {"error": "unexpected_claude_envelope", "usage": usage}
            usage = _usage(envelope.get("modelUsage"))
            subtype = str(envelope.get("subtype", "")).casefold()
            if (
                envelope.get("is_error") is True
                or subtype.startswith("error")
                or "refus" in subtype
            ):
                return None, {
                    "error": "provider_refused" if "refus" in subtype else "provider_error",
                    "usage": usage,
                }
            payload = _json_object(envelope.get("structured_output"))
            if payload is None:
                return None, {"error": "malformed_structured_output", "usage": usage}
            raw_cost = envelope.get("total_cost_usd")
            if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool):
                cost_estimate = float(raw_cost)
            return payload, {
                "usage": usage,
                "cost_estimate_usd": cost_estimate,
                "cost_source": "provider_estimate" if cost_estimate is not None else "unknown",
            }
        if self.host == "antigravity":
            status = str(envelope.get("status", "")).casefold()
            parsed_usage = _usage(envelope.get("usage"))
            if status not in {"completed", "success"}:
                return None, {
                    "error": "provider_refused"
                    if status == "refused"
                    else "unexpected_antigravity_status",
                    "usage": parsed_usage,
                }
            payload = _json_object(envelope.get("response")) or _json_object(
                envelope.get("structured_output")
            )
            if payload is None:
                return None, {"error": "malformed_response", "usage": parsed_usage}
            return payload, {"usage": parsed_usage}
        payload = (
            _json_object(envelope.get("structured_output"))
            or _json_object(envelope.get("response"))
            or envelope
        )
        return payload, {"usage": usage or _usage(envelope.get("usage"))}

    def __call__(self, **kwargs: Any) -> NativePromptResult:
        request_id = str(kwargs.get("request_id") or "")
        mode = str(self.native_context.get("execution_mode") or "native")
        base = self._receipt(request_id, mode=mode)
        if not request_id:
            base["error"] = "request_id_missing"
            return NativePromptResult(2, {}, base)
        context_model = (
            self.native_context.get("model")
            if isinstance(self.native_context.get("model"), Mapping)
            else {}
        )
        requested_model = kwargs.get("model")
        requested_representation = kwargs.get("representation")
        if self._identity_mismatch:
            base["error"] = "trusted_identity_override_rejected"
            base["reasons"] = ["trusted_identity_override_rejected"]
            return NativePromptResult(2, {}, base)
        validation = validate_native_context(
            self.native_context,
            model={
                "host": self.host,
                "selector": self.selector,
                "effort": self.effort,
                "representation": requested_representation
                if requested_representation is not None
                else context_model.get("representation"),
            },
            config={
                "assignment_id": self.native_context.get("assignment_id"),
                "model_selector": self.selector,
                "representation": requested_representation,
                "quest_id": kwargs.get("quest_id"),
                "seed": kwargs.get("seed"),
                "repeat": kwargs.get("repeat"),
                "reset": kwargs.get("reset"),
                "fixture_id": kwargs.get("fixture_id"),
                "fixture_sha256": kwargs.get("fixture_sha256"),
                "output_schema_sha256": kwargs.get("output_schema_sha256"),
                "allowed_requests_sha256": kwargs.get("allowed_requests_sha256"),
                "oracle_sha256": kwargs.get("oracle_sha256"),
            },
            prompt=str(kwargs.get("user_prompt", "")),
            source_root=(
                self.trusted_activation.source_root
                if isinstance(self.trusted_activation, NativeActivationTrust)
                else None
            ),
            trusted_activation=self.trusted_activation,
        )
        if requested_model is not None and requested_model != self.selector:
            validation.setdefault("reasons", []).append("requested_model_mismatch")
            validation["ready"] = False
        base["admission"] = {
            "ready": validation.get("ready"),
            "reasons": validation.get("reasons", []),
        }
        if validation.get("ready") is not True:
            base.update(error="native_context_rejected", failure_kind="authorization")
            return NativePromptResult(2, {}, base)
        effective_mode = validation.get("mode", mode)
        if (
            isinstance(self.trusted_activation, NativeActivationTrust)
            and self.trusted_activation.purpose == "test_simulation"
        ):
            effective_mode = "test_simulation"
        base["mode"] = effective_mode
        base["synthetic"] = effective_mode in {"engineering_fixture", "test_simulation"}
        outgoing_value = kwargs.get("instruction") or kwargs.get("user_prompt", "")
        try:
            outgoing_bytes = (
                outgoing_value
                if isinstance(outgoing_value, bytes)
                else str(outgoing_value).encode("utf-8")
            )
        except UnicodeError:
            base.update(error="outgoing_request_not_utf8", failure_kind="logical")
            return NativePromptResult(2, {}, base)
        try:
            transport_input = outgoing_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            base["error"] = "outgoing_request_not_utf8"
            return NativePromptResult(2, {}, base)
        instruction_sha256 = _sha256(outgoing_bytes)
        user_prompt = kwargs.get("user_prompt", "")
        user_prompt_bytes = (
            user_prompt if isinstance(user_prompt, bytes) else str(user_prompt).encode("utf-8")
        )
        user_prompt_sha256 = _sha256(user_prompt_bytes)
        base["outgoing_request_sha256"] = instruction_sha256
        base["request_tuple"] = {
            "instruction_sha256": instruction_sha256,
            "user_prompt_sha256": user_prompt_sha256,
        }
        if mode == "native" and isinstance(self.trusted_activation, NativeActivationTrust):
            bindings = self.trusted_activation.activation.get("artifact_bindings")
            if not isinstance(bindings, Mapping):
                base["error"] = "request_set_binding_missing"
                return NativePromptResult(2, {}, base)
            expected_schema = bindings.get("output_schema_sha256")
            schema_value = kwargs.get("output_schema")
            schema_bytes: bytes | None = None
            if isinstance(schema_value, (str, Path)):
                schema_path = Path(schema_value)
                root = Path(self.trusted_activation.source_root or "").resolve()
                try:
                    schema_path = (
                        schema_path.resolve()
                        if schema_path.is_absolute()
                        else (root / schema_path).resolve()
                    )
                    try:
                        schema_relative = schema_path.relative_to(root)
                    except ValueError:
                        schema_relative = schema_path.relative_to(
                            Path(tempfile.gettempdir()).resolve()
                        )
                    if _private_path(schema_relative):
                        raise ValueError("schema_private_path_rejected")
                    schema_bytes = _read_bound_bytes(schema_path)
                except (OSError, ValueError):
                    schema_bytes = None
            elif isinstance(schema_value, bytes):
                schema_bytes = schema_value
            if schema_bytes is None or _sha256(schema_bytes) != expected_schema:
                base["error"] = "output_schema_bytes_not_bound"
                return NativePromptResult(2, {}, base)
            request_tuple = (
                instruction_sha256,
                user_prompt_sha256,
                _sha256(schema_bytes),
            )
            allowed = bindings.get("allowed_requests")
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
            if request_tuple not in allowed_tuples:
                base["error"] = "outgoing_request_tuple_not_bound"
                return NativePromptResult(2, {}, base)
        if (
            effective_mode in {"engineering_fixture", "test_simulation"}
            and self.process_runner is None
        ):
            base["error"] = "engineering_fixture_transport_required"
            return NativePromptResult(2, {}, base)
        if (
            effective_mode not in {"engineering_fixture", "test_simulation"}
            and self.process_runner is not None
        ):
            base["error"] = "injected_transport_only_allowed_for_fixture"
            return NativePromptResult(2, {}, base)
        timeout = kwargs.get("timeout", 60.0)
        remaining = kwargs.get("remaining_wall_seconds")
        bounds = (timeout,) if remaining is None else (timeout, remaining)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in bounds
        ):
            base["error"] = "invalid_response_timeout"
            return NativePromptResult(2, {}, base)
        if remaining is not None:
            timeout = min(float(timeout), float(remaining))
        timeout = min(float(timeout), 60.0)
        if timeout <= 0:
            base.update(error="response_deadline_exhausted", timed_out=True)
            return NativePromptResult(124, {}, base)
        try:
            with tempfile.TemporaryDirectory(prefix="runtime-native-") as directory:
                scratch = Path(directory).resolve()
                output_last = scratch / "last-message.json"
                try:
                    command = self._command(scratch, kwargs.get("output_schema"), output_last)
                except ValueError as exc:
                    base.update(error=str(exc), failure_kind="authorization")
                    return NativePromptResult(2, {}, base)
                environment = _sanitized_environment()
                if self.host == "codex":
                    codex_home = scratch / ".codex"
                    codex_home.mkdir()
                    if self.process_runner is None:
                        auth_file = (
                            Path(environment.get("HOME") or Path.home()) / ".codex/auth.json"
                        )
                        if not auth_file.is_file() or not os.access(auth_file, os.R_OK):
                            base.update(
                                error="codex_auth_unavailable", failure_kind="authorization"
                            )
                            return NativePromptResult(2, {}, base)
                        # Share native refresh state without copying credentials or loading user context.
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
                        isolated_path = scratch / leaf
                        isolated_path.mkdir(parents=True, exist_ok=True)
                        environment[key] = str(isolated_path)
                base.update(
                    command=list(command),
                    attempted=True,
                    dispatch_started=True,
                    timeout_seconds=timeout,
                )
                started = self.clock()
                transport = self.process_runner or run_host_process
                on_started = (
                    (lambda: base.update(local_process_started=True))
                    if self.process_runner is None
                    else None
                )
                completed = transport(
                    command,
                    cwd=str(scratch),
                    input=transport_input,
                    check=False,
                    capture_output=True,
                    env=environment,
                    text=True,
                    timeout=timeout,
                    on_started=on_started,
                )
                elapsed = self.clock() - started
                base["duration_seconds"] = elapsed
                if (
                    len(str(completed.stdout or "")) > 64 * 1024
                    or len(str(completed.stderr or "")) > 64 * 1024
                ):
                    base["error"] = "host_output_limit"
                    return NativePromptResult(4, {}, base)
                base["stdout"] = _safe_text(completed.stdout)
                base["stderr"] = _safe_text(completed.stderr)
                if elapsed >= timeout:
                    base.update(error="response_timeout", timed_out=True, failure_kind="timeout")
                    return NativePromptResult(124, {}, base)
                if completed.returncode != 0:
                    base.update(
                        error="host_process_failed",
                        returncode=completed.returncode,
                        failure_kind="logical",
                    )
                    return NativePromptResult(int(completed.returncode), {}, base)
                payload, parsed = self._parse(completed, output_last)
                base.update(parsed, returncode=0)
                if payload is None:
                    return NativePromptResult(5, {}, base)
                payload_request_id = payload.get("request_id")
                if payload_request_id is not None and payload_request_id != request_id:
                    base["error"] = "request_id_mismatch"
                    return NativePromptResult(6, {}, base)
                validator = kwargs.get("validator")
                if validator is not None:
                    try:
                        accepted = validator(payload, request_id)
                    except Exception as exc:  # noqa: BLE001 -- Validator failures are response failures.
                        base["error"] = f"validator_failed:{type(exc).__name__}:{exc}"
                        return NativePromptResult(6, {}, base)
                    if not accepted:
                        base["error"] = "validator_rejected"
                        return NativePromptResult(6, {}, base)
                return NativePromptResult(0, payload, base)
        except subprocess.TimeoutExpired as exc:
            base.update(
                attempted=True,
                dispatch_started=True,
                timed_out=True,
                failure_kind="timeout",
                error="response_timeout",
                stdout=_safe_text(exc.output),
                stderr=_safe_text(exc.stderr),
            )
            return NativePromptResult(124, {}, base)
        except (FileNotFoundError, OSError) as exc:
            base.update(
                attempted=True,
                dispatch_started=True,
                failure_kind="transport",
                error=f"host_launch_failed:{type(exc).__name__}:{exc}",
            )
            return NativePromptResult(127, {}, base)
        except (ValueError, TypeError) as exc:
            base.update(
                attempted=True,
                dispatch_started=True,
                failure_kind="logical",
                error=f"host_request_invalid:{type(exc).__name__}:{exc}",
            )
            return NativePromptResult(127, {}, base)


def build_assignment_plan(
    *,
    quest_id: str,
    seed: int = 20261024,
    source_manifest_sha256: str,
    input_manifest_sha256: str,
    panel: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    approved_targets = (
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
    )
    targets = list(approved_targets if panel is None else panel)
    if not _is_sha256(source_manifest_sha256) or not _is_sha256(input_manifest_sha256):
        raise ValueError("assignment_plan_manifest_hash_invalid")
    if not isinstance(quest_id, str) or not quest_id.strip():
        raise ValueError("assignment_plan_quest_invalid")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("assignment_plan_seed_invalid")  # noqa: TRY004 -- Canonical rejection contract.
    if len(targets) != 5:
        raise ValueError("assignment_plan_requires_five_targets")
    identity_fields = ("host", "selector", "effort", "family_label")
    if any(
        not isinstance(target, Mapping)
        or any(not isinstance(target.get(field), str) for field in identity_fields)
        for target in targets
    ):
        raise ValueError("assignment_plan_target_invalid")
    expected = {tuple(target[field] for field in identity_fields) for target in approved_targets}
    actual = {tuple(target[field] for field in identity_fields) for target in targets}
    if actual != expected:
        raise ValueError("assignment_plan_target_identity_mismatch")
    rows: list[dict[str, Any]] = []
    index = 0
    for target in targets:
        for representation in ("general_rule", "ontology"):
            for repeat in (1, 2):
                planned_id = f"{quest_id}:{target['selector']}:{representation}:repeat-{repeat}"
                rows.append(
                    {
                        "planned_id": planned_id,
                        "assignment_id": planned_id,
                        "quest_id": quest_id,
                        "target": dict(target),
                        "representation": representation,
                        "repeat": repeat,
                        "seed": seed,
                        "order": index,
                        "reset": True,
                        "source_manifest_sha256": source_manifest_sha256,
                        "input_manifest_sha256": input_manifest_sha256,
                        "status": "planned",
                        "scientific_assignment": False,
                        "executed": False,
                    }
                )
                index += 1
    return {
        "schema_version": ASSIGNMENT_PLAN_SCHEMA,
        "status": "planned",
        "quest_id": quest_id,
        "seed": seed,
        "rows": rows,
        "counts": {"quests": 1, "targets": 5, "representations": 2, "repeats": 2},
        "assigned_ids": [],
        "scientific": {"assigned": 0, "executed": 0, "eligible": False},
        "independence": {
            "provider_rng": "not_assumed",
            "compute_or_cost": "not_equal_or_measured",
            "concurrency": 1,
        },
    }


__all__ = [
    "ACTIVATION_KIND",
    "ACTIVATION_SCHEMA",
    "ASSIGNMENT_PLAN_SCHEMA",
    "NATIVE_CONTEXT_SCHEMA",
    "NativeActivationTrust",
    "NativePromptResult",
    "NativePromptRunner",
    "PromptTransportError",
    "build_assignment_plan",
    "load_pinned_native_activation",
    "run_host_process",
    "validate_manifest",
    "validate_native_context",
]
