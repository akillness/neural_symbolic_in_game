"""Offline protocol, admission and reporting boundary of the 2026-11-03 prospective pilot.

This module freezes and validates the 180-unit design, decides admission, keeps the
accounting honest, and audits task freezes. It never starts a native host process for
inference and never calls a model: the only subprocess it can create is one of four
metadata argv (version/help), and only through an injected process factory. The live
runtime runner and the development broker loop are NOT implemented, so every unit stays
blocked. Standard library only; the generic ``_render`` of the runtime-model-swap module is
imported lazily so the metadata path never touches prompt/render code.
"""

from __future__ import annotations

import copy
import difflib
import hashlib
import itertools
import json
import math
import os
import re
import subprocess
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

STUDY_ID = "prospective-pilot-20261103"
SOURCE_COMMIT = "13b5c77401aefc0cb8ff3f10534d8944564e957b"
SCHEMA = "prospective-pilot-protocol/v1"
CODEX_CATALOG_SHA256 = "5293550d74b5ceea7e3c528799fe8a992cbcd215ea326516c4a1bc011c035d36"

TARGETS: dict[str, dict[str, Any]] = {
    "c56sol": {
        "host": "codex",
        "selector": "gpt-5.6-sol",
        "effort": "medium",
        "catalog": "src/nesy_game/codex_no_tools_models.json",
        "catalog_line": 177,
        "catalog_sha256": CODEX_CATALOG_SHA256,
        "catalog_minimal_client_version": "0.144.0",
    },
    "c61sol": {
        "host": "codex",
        "selector": "gpt-6.1-sol",
        "effort": "medium",
        "catalog": "src/nesy_game/codex_no_tools_models.json",
        "catalog_line": 4,
        "catalog_sha256": CODEX_CATALOG_SHA256,
        "catalog_minimal_client_version": "0.153.0",
    },
    "agy38f": {
        "host": "antigravity",
        "selector": "gemini-3.8-flash-medium",
        "effort": "medium",
        "catalog": None,
        "catalog_line": None,
        "catalog_sha256": None,
        "catalog_minimal_client_version": None,
    },
}
RUNTIME_LIMITS = {
    "wall_seconds": 180,
    "response_seconds": 60,
    "host_dispatches": 12,
    "repairs_per_decision": 2,
}
DEVELOPMENT_LIMITS = {
    "wall_seconds": 900,
    "tool_executions": 64,
    "submissions": 3,
    "host_dispatches": 72,
    "non_yielding_dispatches": 5,
}
BROKER: dict[str, Any] = {
    "schema": "prospective-pilot-broker/v1",
    "live_loop": "NOT_IMPLEMENTED",
    "operations": {
        "min": ["read_task_file", "write_file", "run_public_check", "submit"],
        "exp": [
            "read_task_file",
            "write_file",
            "run_public_check",
            "submit",
            "list_corpus",
            "read_corpus",
            "search_corpus",
        ],
    },
    "limits": {
        "write_file_bytes": 65536,
        "public_check_output_bytes": 16384,
        "list_corpus_entries": 500,
        "search_hits": 50,
        "search_excerpt_bytes": 200,
        "observation_bytes": 16384,
        "prompt_bytes": 196608,
    },
}
_ENDPOINTS = {
    "runtime": "independent engine goal within 180 s with the commit-safety gate PASS and "
    "provider identity qualified",
    "development": "hidden task verification passes within 900 s and 3 submissions with "
    "provider identity qualified",
}
_MISSINGNESS = {
    "admitted_without_terminal_record": "missing",
    "failed_and_timeout_stay_in_denominator": True,
    "blocked_is_not_zero": True,
    "unknown_cost_is_null": True,
}
TRUST_FAULTS = ("identity", "authorization", "credit", "isolation", "schema")
ORDINARY_FAILURES = ("invalid_proposal", "timeout", "repairs_exhausted")
_STOP_RULE = {
    "trust_faults": list(TRUST_FAULTS),
    "scope": "entire_serial_queue_both_tracks",
    "ordinary_failures_halt": False,
    "resume": "new_recorded_admission_decision",
    "replacement": False,
}
_ANALYSIS = {
    "tracks_pooled": False,
    "historical_lanes_pooled": False,
    "success_denominator": "all_admitted_units",
    "effect_estimate": None,
    "cost": "null_unless_every_admitted_unit_has_an_observed_cost",
}

REPRESENTATIONS = ("general_rule", "ontology")
TASK_IDS = ("t1", "t2", "t3", "t4", "t5")
SEMANTIC_KEYS = (
    "requirement_ids",
    "public_facts",
    "preconditions",
    "allowed_effects",
    "rejection_semantics",
    "unchanged_invariants",
)
_PROTOCOL_KEYS = frozenset(
    {
        "schema",
        "study_id",
        "source_commit",
        "targets",
        "units",
        "runtime_limits",
        "development_limits",
        "broker",
        "tasks",
        "endpoints",
        "missingness",
        "stop_rule",
        "analysis",
    }
)
_TASK_ROW_KEYS = frozenset({"task_id", "semantic", "contexts", "context_hashes"})

REASONS = (
    "BLOCKED_NO_CREDIT_ENFORCEMENT",
    "BLOCKED_IDENTITY_FORMAT_UNOBSERVED",
    "BLOCKED_ACTIVATION_ABSENT",
    "BLOCKED_PUBLIC_DERIVED_UNAPPROVED",
    "BLOCKED_SOURCE_COMMIT_UNAVAILABLE",
    "BLOCKED_TARGET_UNVERIFIED",
    "BLOCKED_ISOLATION_UNPROVEN",
    "BLOCKED_SCHEMA_ACCEPTANCE_UNOBSERVED",
    "BLOCKED_LIVE_PATH_NOT_IMPLEMENTED",
    "BLOCKED_TASK_FREEZE_INCOMPLETE",
    "BLOCKED_QUEUE_HALTED",
)
METADATA_ARGV = (
    ("codex", "--version"),
    ("codex", "exec", "--help"),
    ("agy", "--version"),
    ("agy", "--help"),
)
_PROVIDERS = ("codex", "antigravity")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Positive provider-identity and credit-enforcement formats are registered only from a
# retained real receipt of a future approved run. They are empty today, so no booleans,
# configuration, metadata, catalog entry, echoed JSON or model field can pass either gate.
_OBSERVED_IDENTITY_FORMATS: dict[str, Any] = {}
_AUTHORITATIVE_CREDIT_SOURCES: dict[str, Any] = {}
# Receipt gates accept a receipt only from a registered issuer. None is registered today.
_TRUSTED_RECEIPT_ISSUERS: dict[str, frozenset[str]] = {}
_RECEIPT_SCHEMAS = {
    "activation": "prospective-pilot-activation/v1",
    "public_derived": "prospective-pilot-public-approval/v1",
    "isolation": "prospective-pilot-isolation-receipt/v1",
    "schema_acceptance": "prospective-pilot-schema-acceptance/v1",
    "task_freeze": "prospective-pilot-task-freeze/v1",
}

# Offline engineering default used only by ``build_protocol()`` without arguments. The CLI
# ``prepare`` replaces it with the bound public task specs of the external task bundle.
_OFFLINE_SPECS: list[dict[str, Any]] = [
    {
        "task_id": "t1",
        "title": "Actor rule binding in the ontology mapping",
        "requirement": "Restore the ontology-map binding so the eligible actor is bound to the "
        "stated rule while denials for unrelated roles are preserved; the three "
        "label sets stay non-isomorphic and unrelated entries stay unchanged.",
        "target_file": "game-track/web/dashboard/ontology-map.json",
        "interface_files": [],
        "public_check": "public_check.py",
        "max_changed_lines": 30,
        "endpoint": "bounded_repair",
        "baseline_sha256": None,
    },
    {
        "task_id": "t2",
        "title": "Quest stage regression gate in the validator",
        "requirement": "A proposal whose quest stage is lower than the recorded stage must be "
        "rejected with QUEST_STAGE_REGRESSION naming the entity; absent, equal and "
        "higher stages stay accepted and the prior state is never mutated.",
        "target_file": "src/nesy_game/validator.py",
        "interface_files": ["src/nesy_game/contracts.py"],
        "public_check": "public_check.py",
        "max_changed_lines": 30,
        "endpoint": "bounded_repair",
        "baseline_sha256": None,
    },
    {
        "task_id": "t3",
        "title": "Bounded repair of omitted required effects",
        "requirement": "Repair inserts a required effect that a proposal omitted, never edits "
        "authoritative state, leaves irreparable knowledge errors unrepaired, stays "
        "within the stated edit bound and is idempotent.",
        "target_file": "src/nesy_game/repair.py",
        "interface_files": ["src/nesy_game/contracts.py", "src/nesy_game/validator.py"],
        "public_check": "public_check.py",
        "max_changed_lines": 30,
        "endpoint": "bounded_repair",
        "baseline_sha256": None,
    },
    {
        "task_id": "t4",
        "title": "Semantic replay rejection in the runtime trace",
        "requirement": "Replay must reject a history whose final replayed state differs from the "
        "recorded state even when every checksum is recomputed, while a valid "
        "history is accepted; reorder, duplicate and fallback mutations are rejected.",
        "target_file": "src/nesy_game/runtime.py",
        "interface_files": ["src/nesy_game/contracts.py"],
        "public_check": "public_check.py",
        "max_changed_lines": 30,
        "endpoint": "bounded_repair",
        "baseline_sha256": None,
    },
    {
        "task_id": "t5",
        "title": "Read-only dashboard unknown rendering",
        "requirement": "The dashboard renders a missing, null or malformed value as the unknown "
        "string, never as zero, while real false and zero values render as such; the "
        "target stays visible without horizontal overflow at desktop and narrow "
        "viewports and the page remains read-only.",
        "target_file": "game-track/web/dashboard/dashboard.js",
        "interface_files": [],
        "public_check": "public_check.cjs",
        "max_changed_lines": 30,
        "endpoint": "bounded_repair",
        "baseline_sha256": None,
    },
]


# ---------------------------------------------------------------- hashing and strict JSON
def canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def sha256_hex(data: bytes | str) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


def git_blob_id(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def protocol_sha256(protocol: dict) -> str:
    return sha256_hex(canonical_json(protocol))


def _reject_constant(name: str) -> Any:
    raise ValueError(f"non-finite JSON constant {name!r}")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def strict_json_loads(text: str, *, allow_whitespace: bool = False) -> Any:
    if not allow_whitespace and text != text.strip():
        raise ValueError("JSON text has surrounding whitespace")
    return json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)


def load_json_file(path: Path | str) -> Any:
    return strict_json_loads(Path(path).read_text(encoding="utf-8"), allow_whitespace=True)


def _utc(timestamp: float | None = None) -> str:
    return datetime.fromtimestamp(time.time() if timestamp is None else timestamp, UTC).isoformat()


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _ordered(reasons: list[str]) -> list[str]:
    return sorted(set(reasons), key=REASONS.index)


# ---------------------------------------------------------------- context codec
def _render_context(semantic: dict[str, Any], representation: str) -> str:
    # Lazy: only protocol construction renders contexts; the metadata path never imports this.
    from nesy_game.runtime_model_swap import _render

    return _render(semantic, representation)


def decode_context(text: str, representation: str) -> dict[str, Any]:
    """Strictly invert the existing generic ``_render``; reject any ambiguity."""
    if not isinstance(text, str):
        raise TypeError("context must be text")
    if representation == "ontology":
        if not text.startswith("ontology:"):
            raise ValueError("ontology context lacks its prefix")
        value = strict_json_loads(text[len("ontology:") :])
        if not isinstance(value, dict):
            raise ValueError("ontology context must be a JSON object")
        return value
    if representation == "general_rule":
        if not text.startswith("rules:"):
            raise ValueError("general-rule context lacks its prefix")
        return _decode_rules(text[len("rules:") :])
    raise ValueError(f"unknown representation {representation!r}")


def _decode_rules(body: str) -> dict[str, Any]:
    decoder = json.JSONDecoder(object_pairs_hook=_no_duplicates, parse_constant=_reject_constant)
    facts: dict[str, Any] = {}
    position = 0
    while position < len(body):
        equals = body.find("=", position)
        if equals < 0:
            raise ValueError("rule without '='")
        key = body[position:equals]
        if not _KEY.fullmatch(key):
            raise ValueError(f"invalid rule key {key!r}")
        if key in facts:
            raise ValueError(f"duplicate rule key {key!r}")
        value, end = decoder.raw_decode(body, equals + 1)
        facts[key] = value
        if end == len(body):
            return facts
        if body[end] != ";":
            raise ValueError("trailing text after a rule value")
        position = end + 1
        if position == len(body):
            raise ValueError("trailing rule separator")
    return facts


# ---------------------------------------------------------------- task specs and protocol
def interface_paths(spec: dict[str, Any]) -> list[str]:
    paths = []
    for item in spec.get("interface_files", []):
        path = item.get("path") if isinstance(item, dict) else item
        if not isinstance(path, str) or not path:
            raise ValueError("interface_files entries must be paths")
        paths.append(path)
    return paths


def _check_spec(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise TypeError("task spec must be an object")
    for key in ("task_id", "title", "requirement", "target_file", "endpoint"):
        if not isinstance(spec.get(key), str) or not spec[key]:
            raise ValueError(f"task spec field {key} must be non-empty text")
    if not isinstance(spec.get("interface_files"), list):
        raise TypeError("task spec interface_files must be a list")
    interface_paths(spec)
    if spec.get("public_check") is None:
        raise ValueError("task spec lacks a public check")
    if type(spec.get("max_changed_lines")) is not int or spec["max_changed_lines"] < 1:
        raise ValueError("task spec max_changed_lines must be a positive integer")
    digest = spec.get("baseline_sha256")
    if digest is not None and not (isinstance(digest, str) and _HEX64.fullmatch(digest)):
        raise ValueError("task spec baseline_sha256 must be a sha256 hex digest or null")
    return spec


def semantic_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """The single semantic mapping both representations must carry, from public spec fields."""
    spec = _check_spec(spec)
    tid, target = spec["task_id"], spec["target_file"]
    facts = {
        "title": spec["title"],
        "requirement": spec["requirement"],
        "target_file": target,
        "interface_files": interface_paths(spec),
        "public_check": spec["public_check"],
        "max_changed_lines": spec["max_changed_lines"],
        "endpoint": spec["endpoint"],
        "baseline_sha256": spec.get("baseline_sha256"),
    }
    for optional in ("disclosed_mirrors", "disclosed_public_tests"):
        if optional in spec:
            facts[optional] = spec[optional]
    semantic = {
        "requirement_ids": [f"{tid}:requirement"],
        "public_facts": facts,
        "preconditions": f"{target} is the only file that may change; interface files are read-only",
        "allowed_effects": [
            (f"replace the contents of {target} within {spec['max_changed_lines']} changed lines")
        ],
        "rejection_semantics": {
            "public_check": spec["public_check"],
            "hidden_verification": "aggregate pass/fail and a count only",
        },
        "unchanged_invariants": [
            "every other file stays byte-identical",
            "no history, answer or candidate retrieval",
        ],
    }
    # Key order is canonical (sorted): general-rule rendering is insertion-ordered, and a
    # protocol reloaded from sorted-key JSON must re-render to byte-identical contexts.
    return dict(sorted(semantic.items()))


def _task_row(spec: dict[str, Any]) -> dict[str, Any]:
    semantic = semantic_from_spec(spec)
    contexts = {rep: _render_context(semantic, rep) for rep in REPRESENTATIONS}
    return {
        "task_id": spec["task_id"],
        "semantic": semantic,
        "contexts": contexts,
        "context_hashes": {
            rep: {"sha256": sha256_hex(text), "bytes": len(text.encode("utf-8"))}
            for rep, text in contexts.items()
        },
    }


def _canonical_units() -> list[dict[str, Any]]:
    keys = list(TARGETS)
    plan: list[dict[str, Any]] = []
    for block in range(1, 11):
        rotated = keys[block % 3 :] + keys[: block % 3]
        reps = ("gr", "onto") if block % 2 else ("onto", "gr")
        for key in rotated:
            for rep in reps:
                plan.append(
                    {
                        "track": "runtime",
                        "unit_id": f"pp1103:rt:{key}:{rep}:r{block:02d}",
                        "target": key,
                        "representation": rep,
                        "exploration": None,
                        "task": None,
                        "repeat": block,
                        "seed": 2026110300 + block,
                    }
                )
    cells = [("min", "gr"), ("min", "onto"), ("exp", "gr"), ("exp", "onto")]
    for block, (task, repeat) in enumerate(itertools.product(range(1, 6), (1, 2)), 1):
        rotated = keys[block % 3 :] + keys[: block % 3]
        order = cells[block % 4 :] + cells[: block % 4]
        for key in rotated:
            for exploration, rep in order:
                plan.append(
                    {
                        "track": "development",
                        "unit_id": f"pp1103:dev:{key}:{exploration}:{rep}:t{task}:r{repeat}",
                        "target": key,
                        "representation": rep,
                        "exploration": exploration,
                        "task": task,
                        "repeat": repeat,
                        "seed": 2026111000 + 10 * task + repeat,
                    }
                )
    for position, unit in enumerate(plan, 1):
        unit["order"] = position
        unit["reset_id"] = "pp1103:reset:" + sha256_hex(unit["unit_id"])[:16]
    return plan


def build_protocol(task_specs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    specs = _OFFLINE_SPECS if task_specs is None else task_specs
    if not isinstance(specs, list) or [
        s.get("task_id") if isinstance(s, dict) else None for s in specs
    ] != list(TASK_IDS):
        raise ValueError("exactly the five task specs t1..t5, in order, are required")
    return {
        "schema": SCHEMA,
        "study_id": STUDY_ID,
        "source_commit": SOURCE_COMMIT,
        "targets": copy.deepcopy(TARGETS),
        "units": _canonical_units(),
        "runtime_limits": dict(RUNTIME_LIMITS),
        "development_limits": dict(DEVELOPMENT_LIMITS),
        "broker": copy.deepcopy(BROKER),
        "tasks": [_task_row(spec) for spec in specs],
        "endpoints": dict(_ENDPOINTS),
        "missingness": dict(_MISSINGNESS),
        "stop_rule": copy.deepcopy(_STOP_RULE),
        "analysis": copy.deepcopy(_ANALYSIS),
    }


def _validate_units(units: Any) -> None:
    if not isinstance(units, list):
        raise TypeError("units must be a list")
    ids = [unit.get("unit_id") if isinstance(unit, dict) else None for unit in units]
    if len(set(map(str, ids))) != len(ids):
        raise ValueError("duplicate unit_id")
    canonical = _canonical_units()
    expected = {unit["unit_id"] for unit in canonical}
    if set(ids) != expected:
        raise ValueError(
            f"unit membership drift: missing {sorted(expected - set(ids))[:3]}, "
            f"unknown {sorted(set(ids) - expected)[:3]}"
        )
    resets = [unit.get("reset_id") for unit in units]
    if len(set(map(str, resets))) != len(resets):
        raise ValueError("reset_id is shared between units")
    for index, (got, want) in enumerate(zip(units, canonical, strict=True)):
        if set(got) != set(want):
            raise ValueError(f"unit {index + 1} has unknown or missing fields")
        for key in want:
            if got[key] != want[key] or type(got[key]) is not type(want[key]):
                raise ValueError(f"unit {index + 1} drifts from the frozen plan at {key!r}")


def _validate_tasks(tasks: Any) -> None:
    if not isinstance(tasks, list) or len(tasks) != len(TASK_IDS):
        raise ValueError("exactly five tasks are required")
    for task_id, task in zip(TASK_IDS, tasks, strict=True):
        if not isinstance(task, dict) or set(task) != _TASK_ROW_KEYS:
            raise ValueError(f"{task_id}: task row has unknown or missing fields")
        if task["task_id"] != task_id:
            raise ValueError(f"{task_id}: task order or identity drift")
        semantic = task["semantic"]
        if not isinstance(semantic, dict) or set(semantic) != set(SEMANTIC_KEYS):
            raise ValueError(f"{task_id}: semantic mapping must have exactly the six frozen keys")
        contexts, hashes = task["contexts"], task["context_hashes"]
        if not isinstance(contexts, dict) or set(contexts) != set(REPRESENTATIONS):
            raise ValueError(f"{task_id}: contexts must be exactly general_rule and ontology")
        for rep in REPRESENTATIONS:
            if decode_context(contexts[rep], rep) != semantic:
                raise ValueError(
                    f"{task_id}: {rep} context differs from the shared semantic mapping"
                )
            if contexts[rep] != _render_context(semantic, rep):
                raise ValueError(f"{task_id}: {rep} context is not the existing generic rendering")
        expected = {
            rep: {"sha256": sha256_hex(contexts[rep]), "bytes": len(contexts[rep].encode("utf-8"))}
            for rep in REPRESENTATIONS
        }
        if hashes != expected:
            raise ValueError(f"{task_id}: context hashes do not match the rendered bytes")


def validate_protocol(protocol: dict) -> dict:
    if not isinstance(protocol, dict):
        raise TypeError("protocol must be an object")
    unknown, missing = set(protocol) - _PROTOCOL_KEYS, _PROTOCOL_KEYS - set(protocol)
    if unknown or missing:
        raise ValueError(
            f"protocol fields drift: unknown {sorted(unknown)}, missing {sorted(missing)}"
        )
    for key, want in (("schema", SCHEMA), ("study_id", STUDY_ID), ("source_commit", SOURCE_COMMIT)):
        if protocol[key] != want:
            raise ValueError(f"protocol {key} drift")
    if canonical_json(protocol["targets"]) != canonical_json(TARGETS):
        raise ValueError("requested targets drift from the frozen strings")
    _validate_units(protocol["units"])
    for key, want in (
        ("runtime_limits", RUNTIME_LIMITS),
        ("development_limits", DEVELOPMENT_LIMITS),
        ("broker", BROKER),
        ("endpoints", _ENDPOINTS),
        ("missingness", _MISSINGNESS),
        ("stop_rule", _STOP_RULE),
        ("analysis", _ANALYSIS),
    ):
        if canonical_json(protocol[key]) != canonical_json(want):
            raise ValueError(f"frozen {key} drift (budgets and rules cannot be relaxed)")
    _validate_tasks(protocol["tasks"])
    return {
        "status": "PASS",
        "units": len(protocol["units"]),
        "tracks": dict(Counter(unit["track"] for unit in protocol["units"])),
        "tasks": len(protocol["tasks"]),
        "protocol_sha256": protocol_sha256(protocol),
    }


# ---------------------------------------------------------------- admission and collection
def _row(unit: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "unit_id": unit["unit_id"],
        "track": unit["track"],
        "planned": True,
        "blocked_reasons": reasons,
        "admitted": not reasons,
        "dispatch_attempts": 0,
        "native_process_starts": 0,
        "executed": False,
        "identity_qualified": False,
        "terminal_outcome": None,
        "successful": None,
        "safety_gate": None,
        "replayed": False,
        "actual_engine": None,
        "actual_model": None,
        "cost": None,
    }


def _parse_version(text: Any) -> tuple[int, ...] | None:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text) if isinstance(text, str) else None
    return tuple(int(part) for part in match.groups()) if match else None


def _source_gate(evidence: dict[str, Any]) -> bool:
    source = evidence.get("source")
    return (
        isinstance(source, dict)
        and source.get("source_commit") == SOURCE_COMMIT
        and source.get("checkpoint_status") == "SOURCE_DELIVERED_REMOTE_CONFIRMED"
        and source.get("commit_object_present") is True
        and isinstance(source.get("checkpoint_receipt_sha256"), str)
        and bool(_HEX64.fullmatch(source["checkpoint_receipt_sha256"]))
    )


def _target_gate(target: dict[str, Any], evidence: dict[str, Any]) -> bool:
    # No repository catalog lists the Antigravity slug, so that target stays unverified.
    if target["host"] != "codex":
        return False
    metadata = evidence.get("metadata")
    observed = metadata.get("codex") if isinstance(metadata, dict) else None
    if not isinstance(observed, dict) or observed.get("exec_help_status") != "OBSERVED":
        return False
    version = _parse_version(observed.get("version"))
    minimal = _parse_version(target["catalog_minimal_client_version"])
    return version is not None and minimal is not None and version >= minimal


def _receipt_gate(evidence: dict[str, Any], kind: str, protocol_hash: str) -> bool:
    receipt = evidence.get(kind)
    if not isinstance(receipt, dict) or receipt.get("schema") != _RECEIPT_SCHEMAS[kind]:
        return False
    if receipt.get("issuer") not in _TRUSTED_RECEIPT_ISSUERS.get(kind, frozenset()):
        return False
    body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    try:
        intact = receipt.get("receipt_sha256") == sha256_hex(canonical_json(body))
    except (TypeError, ValueError):
        return False
    return (
        intact
        and receipt.get("protocol_sha256") == protocol_hash
        and receipt.get("status") == "PASS"
    )


def _gate_reasons(
    unit: dict[str, Any], target: dict[str, Any], evidence: dict[str, Any], protocol_hash: str
) -> list[str]:
    reasons = []
    if not _source_gate(evidence):
        reasons.append("BLOCKED_SOURCE_COMMIT_UNAVAILABLE")
    if not _target_gate(target, evidence):
        reasons.append("BLOCKED_TARGET_UNVERIFIED")
    if target["host"] not in _AUTHORITATIVE_CREDIT_SOURCES:
        reasons.append("BLOCKED_NO_CREDIT_ENFORCEMENT")
    if target["host"] not in _OBSERVED_IDENTITY_FORMATS:
        reasons.append("BLOCKED_IDENTITY_FORMAT_UNOBSERVED")
    if not _receipt_gate(evidence, "activation", protocol_hash):
        reasons.append("BLOCKED_ACTIVATION_ABSENT")
    if not _receipt_gate(evidence, "public_derived", protocol_hash):
        reasons.append("BLOCKED_PUBLIC_DERIVED_UNAPPROVED")
    # Antigravity has no restriction flag; the development broker is not implemented; a Codex
    # runtime row additionally needs a live isolation receipt from a registered issuer.
    if (
        target["host"] != "codex"
        or unit["track"] == "development"
        or not _receipt_gate(evidence, "isolation", protocol_hash)
    ):
        reasons.append("BLOCKED_ISOLATION_UNPROVEN")
    if not _receipt_gate(evidence, "schema_acceptance", protocol_hash):
        reasons.append("BLOCKED_SCHEMA_ACCEPTANCE_UNOBSERVED")
    if not _receipt_gate(evidence, "task_freeze", protocol_hash):
        reasons.append("BLOCKED_TASK_FREEZE_INCOMPLETE")
    reasons.append("BLOCKED_LIVE_PATH_NOT_IMPLEMENTED")
    return _ordered(reasons)


def evaluate_admission(protocol: dict, evidence: dict) -> dict:
    validate_protocol(protocol)
    if not isinstance(evidence, dict):
        raise TypeError("evidence must be an object")
    try:
        evidence_hash = sha256_hex(canonical_json(evidence))
    except (TypeError, ValueError) as error:
        raise ValueError("evidence is not canonical JSON") from error
    protocol_hash = protocol_sha256(protocol)
    rows = [
        _row(
            unit, _gate_reasons(unit, protocol["targets"][unit["target"]], evidence, protocol_hash)
        )
        for unit in protocol["units"]
    ]
    reason_counts = Counter(reason for row in rows for reason in row["blocked_reasons"])
    return {
        "schema": "prospective-pilot-admission/v1",
        "study_id": STUDY_ID,
        "protocol_sha256": protocol_hash,
        "evidence_sha256": evidence_hash,
        "rows": rows,
        "admitted": sum(row["admitted"] for row in rows),
        "blocked_reason_counts": dict(sorted(reason_counts.items())),
    }


_COUNT_KEYS = (
    "planned",
    "blocked",
    "assigned",
    "attempted",
    "executed",
    "failed",
    "missing",
    "successful",
    "identity_qualified",
    "replayed",
)
_ROW_KEYS = (
    "unit_id",
    "track",
    "planned",
    "blocked_reasons",
    "admitted",
    "dispatch_attempts",
    "native_process_starts",
    "executed",
    "identity_qualified",
    "terminal_outcome",
    "successful",
    "safety_gate",
    "replayed",
    "actual_engine",
    "actual_model",
    "cost",
)


def _counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    admitted = [row for row in rows if row["admitted"]]
    return {
        "planned": len(rows),
        "blocked": len(rows) - len(admitted),
        "assigned": len(admitted),
        "attempted": sum(row["dispatch_attempts"] > 0 for row in rows),
        "executed": sum(row["executed"] for row in rows),
        "failed": sum(
            row["terminal_outcome"] is not None and row["successful"] is False for row in admitted
        ),
        "missing": sum(row["terminal_outcome"] is None for row in admitted),
        "successful": sum(row["successful"] is True for row in rows),
        "identity_qualified": sum(row["identity_qualified"] for row in rows),
        "replayed": sum(row["replayed"] for row in rows),
    }


def collect(protocol: dict, admission: dict, *, process_factory: Any) -> dict:
    """The only implemented collection path: a blocked manifest and zero native processes.

    There is no ``launch_native``: the live runner is NOT_IMPLEMENTED, so the injected factory
    is validated but never called and no input, however adversarial, starts a process. A row
    an admission claims as admitted is listed in ``unexpected_admissions``, forced blocked,
    and the CLI turns that into a failing command rather than a quiet success.
    """
    validate_protocol(protocol)
    if not callable(process_factory):
        raise TypeError("process_factory must be callable")
    given = admission.get("rows") if isinstance(admission, dict) else None
    if not isinstance(given, list):
        raise TypeError("admission must carry a rows list")
    by_id: dict[str, dict[str, Any]] = {}
    for row in given:
        unit_id = row.get("unit_id") if isinstance(row, dict) else None
        if not isinstance(unit_id, str) or unit_id in by_id:
            raise ValueError("admission rows must have unique string unit_id values")
        by_id[unit_id] = row
    if set(by_id) != {unit["unit_id"] for unit in protocol["units"]}:
        raise ValueError("admission rows do not match the frozen units")
    protocol_hash = protocol_sha256(protocol)
    if admission.get("protocol_sha256") not in (None, protocol_hash):
        raise ValueError("admission was computed for a different protocol")
    rows, unexpected = [], []
    for unit in protocol["units"]:
        source = by_id[unit["unit_id"]]
        reasons = source.get("blocked_reasons", [])
        if not isinstance(reasons, list) or any(reason not in REASONS for reason in reasons):
            raise ValueError(f"{unit['unit_id']}: invalid blocked_reasons")
        if source.get("admitted") is True:
            unexpected.append(unit["unit_id"])
        rows.append(_row(unit, _ordered([*reasons, "BLOCKED_LIVE_PATH_NOT_IMPLEMENTED"])))
    counts = _counts(rows)
    return {
        "schema": "prospective-pilot-collection/v1",
        "study_id": STUDY_ID,
        "protocol_sha256": protocol_hash,
        "native_process_starts": 0,
        "unexpected_admissions": unexpected,
        "counts": {
            key: counts[key] for key in ("planned", "blocked", "assigned", "attempted", "executed")
        },
        "rows": rows,
    }


def apply_stop_rule(ledger: dict, event: dict) -> dict:
    """Halt the entire serial queue (both tracks) on a trust fault; ordinary failures do not."""
    rows = ledger.get("rows") if isinstance(ledger, dict) else None
    if (
        not isinstance(rows, list)
        or not isinstance(event, dict)
        or set(event) != {"unit_id", "fault"}
    ):
        raise ValueError("stop rule needs a ledger with rows and an event {unit_id, fault}")
    out = copy.deepcopy(ledger)
    faulted = next((row for row in out["rows"] if row.get("unit_id") == event["unit_id"]), None)
    if faulted is None:
        raise ValueError("event names a unit outside the ledger")
    fault = event["fault"]
    if fault in ORDINARY_FAILURES:
        return out
    if fault not in TRUST_FAULTS:
        raise ValueError(f"unknown fault {fault!r}")
    if faulted.get("terminal_outcome") is None:
        raise ValueError("the faulted unit's terminal record must be written before halting")
    if out.get("halt") is not None:
        return out  # The first halt stands: no replacement and no activation reset.
    out["halt"] = {"unit_id": faulted["unit_id"], "fault": fault, "order": faulted.get("order")}
    for row in out["rows"]:
        if row is faulted or row.get("terminal_outcome") is not None:
            continue
        row["admitted"] = False
        row["blocked_reasons"] = _ordered([*row.get("blocked_reasons", []), "BLOCKED_QUEUE_HALTED"])
    return out


# ---------------------------------------------------------------- publicity, preflight, identity
def validate_turn(
    turn: dict, static_manifest: dict, derivation_ledger: dict, trust_root: Path
) -> dict:
    """Dynamic publicity predicate: a turn may contain only approved, ledgered, public inputs."""
    if not isinstance(turn, dict) or set(turn) != {
        "program_id",
        "program_sha256",
        "provider",
        "inputs",
    }:
        raise ValueError("turn must have exactly program_id, program_sha256, provider and inputs")
    provider = turn["provider"]
    if provider not in _PROVIDERS or not isinstance(turn["inputs"], list):
        raise ValueError("turn provider or inputs invalid")
    if not isinstance(derivation_ledger, dict) or derivation_ledger.get("approved") is not True:
        raise ValueError("derivation ledger is not approved")
    programs = derivation_ledger.get("programs")
    digest = turn["program_sha256"]
    if (
        not isinstance(programs, dict)
        or not isinstance(digest, str)
        or not _HEX64.fullmatch(digest)
        or programs.get(turn["program_id"]) != digest
    ):
        raise ValueError("controller program is not ledgered at this hash")
    base = Path(static_manifest["root"]) if static_manifest.get("root") else None

    def resolved(path: str) -> Path:
        return ((base / path) if base is not None else Path(path)).resolve()

    entries = {resolved(entry["path"]): entry for entry in static_manifest.get("files", [])}
    trust = Path(trust_root).resolve()
    for item in turn["inputs"]:
        kind = item.get("kind") if isinstance(item, dict) else None
        if kind == "static":
            if set(item) != {"kind", "path"} or not isinstance(item["path"], str):
                raise ValueError("static input must be exactly {kind, path}")
            path = resolved(item["path"])
            if path == trust or path.is_relative_to(trust):
                raise ValueError("static input lies inside the evaluator-only trust root")
            entry = entries.get(path)
            if entry is None or entry.get("classification") not in (
                "PUBLIC_BLOB",
                "PUBLIC_DERIVED",
                "NEW_AUTHORED",
            ):
                raise ValueError(f"static input {item['path']!r} is unclassified")
            try:
                actual = sha256_hex(path.read_bytes())
            except OSError as error:
                raise ValueError(f"static input {item['path']!r} is unreadable") from error
            if actual != entry.get("sha256"):
                raise ValueError(f"static input {item['path']!r} changed after approval")
        elif kind in ("public_engine_observation", "remaining_budget", "own_prior_output"):
            allowed = {"kind", "value"} | ({"provider"} if kind == "own_prior_output" else set())
            if set(item) != allowed:
                raise ValueError(f"{kind} input has unexpected fields")
            if kind == "own_prior_output" and item["provider"] != provider:
                raise ValueError("a turn may carry only the same provider's own prior output")
            try:
                text = canonical_json(item["value"])
            except (TypeError, ValueError) as error:
                raise ValueError(f"{kind} value is not canonical JSON") from error
            if str(trust) in text:
                raise ValueError(f"{kind} value names the evaluator-only trust root")
        else:
            raise ValueError(f"input kind {kind!r} is not an approved dynamic input")
    return {
        "status": "PASS",
        "program_id": turn["program_id"],
        "inputs": len(turn["inputs"]),
        "turn_sha256": sha256_hex(canonical_json(turn)),
    }


def metadata_preflight(argv: list[str], *, process_factory: Any) -> dict:
    """Run one of exactly four version/help argv with stdin closed, a sanitized env and 10 s."""
    if not isinstance(argv, (list, tuple)) or tuple(argv) not in METADATA_ARGV:
        raise ValueError(f"argv is not one of the four metadata-only commands: {list(argv)!r}")
    command = list(argv)
    env = {"PATH": os.environ.get("PATH", ""), "LC_ALL": "C", "LANG": "C"}
    started = time.time()
    record: dict[str, Any] = {
        "argv": command,
        "status": "UNVERIFIED",
        "reason": None,
        "exit_code": None,
        "timed_out": False,
        "stdout_sha256": None,
        "stderr_sha256": None,
        "stdout_bytes": 0,
        "stderr_bytes": 0,
        "version": None,
        "flags": [],
        "started_utc": _utc(started),
        "ended_utc": None,
        "raw": {"stdout": "", "stderr": ""},
    }
    try:
        done = process_factory(
            command,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=env,
            timeout=10,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        record.update(reason="timeout", timed_out=True)
    except OSError as error:
        record.update(reason=f"os_error:{type(error).__name__}")
    else:
        streams = [
            value if isinstance(value, bytes) else (value or "").encode("utf-8")
            for value in (done.stdout, done.stderr)
        ]
        text = [data.decode("utf-8", errors="replace") for data in streams]
        record.update(
            exit_code=done.returncode,
            stdout_sha256=sha256_hex(streams[0]),
            stderr_sha256=sha256_hex(streams[1]),
            stdout_bytes=len(streams[0]),
            stderr_bytes=len(streams[1]),
            raw={"stdout": text[0], "stderr": text[1]},
            flags=sorted(set(re.findall(r"(?<![\w-])--[a-z][a-z0-9-]*", text[0] + "\n" + text[1]))),
            status="OBSERVED" if done.returncode == 0 else "UNVERIFIED",
            reason=None if done.returncode == 0 else "nonzero_exit",
        )
        if command[-1] == "--version":
            match = re.search(r"\d+\.\d+\.\d+\S*", text[0] + "\n" + text[1])
            record["version"] = match.group(0) if match else None
    record["ended_utc"] = _utc()
    return record


def summarize_metadata(observations: list[dict[str, Any]]) -> dict[str, Any]:
    """Observed support only; served identity, credit and isolation are never inferred here."""
    summary: dict[str, Any] = {}
    for obs in observations:
        host = "codex" if obs["argv"][0] == "codex" else "agy"
        entry = summary.setdefault(
            host,
            {
                "version": None,
                "version_status": None,
                "exec_help_status": None,
                "help_status": None,
                "flags": [],
            },
        )
        if obs["argv"][-1] == "--version":
            entry["version"], entry["version_status"] = obs["version"], obs["status"]
        else:
            entry["exec_help_status" if host == "codex" else "help_status"] = obs["status"]
            entry["flags"] = obs["flags"]
    return summary


def bind_identity(observation: dict, attempt: dict) -> bool:
    """Engineering-only: provider channel of this exact attempt, one identity equal to the selector.

    It is NOT a host adapter positive: the observed-format registry is empty, so the evaluator
    gate stays blocked regardless of this predicate.
    """
    if not isinstance(observation, dict) or not isinstance(attempt, dict):
        return False
    if observation.get("channel") != "provider":
        return False
    for key in ("attempt_id", "pid", "started", "ended", "stream_sha256"):
        if key not in observation or key not in attempt:
            return False
        if observation[key] != attempt[key] or type(observation[key]) is not type(attempt[key]):
            return False
    if not isinstance(attempt["attempt_id"], str) or not attempt["attempt_id"]:
        return False
    if type(attempt["pid"]) is not int or attempt["pid"] <= 0:
        return False
    if not (
        isinstance(attempt["stream_sha256"], str) and _HEX64.fullmatch(attempt["stream_sha256"])
    ):
        return False
    if not (
        _is_number(attempt["started"])
        and _is_number(attempt["ended"])
        and attempt["ended"] >= attempt["started"]
    ):
        return False
    selector = attempt.get("selector")
    if not isinstance(selector, str) or not selector:
        return False
    identities, markers = observation.get("identities"), observation.get("markers")
    if not isinstance(identities, list) or len(identities) != 1 or identities[0] != selector:
        return False
    return isinstance(identities[0], str) and isinstance(markers, list) and not markers


# ---------------------------------------------------------------- independent analysis
def _check_row(row: dict[str, Any], unit: dict[str, Any]) -> None:
    def fail(message: str) -> None:
        raise ValueError(f"{unit['unit_id']}: {message}")

    if not isinstance(row, dict) or set(row) != set(_ROW_KEYS):
        fail("row keys differ from the frozen schema")
    if row["track"] != unit["track"]:
        fail("track drift")
    if row["planned"] is not True:
        fail("unit is not planned")
    reasons = row["blocked_reasons"]
    if not isinstance(reasons, list) or any(reason not in REASONS for reason in reasons):
        fail("invalid blocked_reasons")
    for key in ("admitted", "executed", "identity_qualified", "replayed"):
        if not isinstance(row[key], bool):
            fail(f"{key} must be a boolean")
    for key in ("dispatch_attempts", "native_process_starts"):
        if type(row[key]) is not int or row[key] < 0:
            fail(f"{key} must be a nonnegative integer")
    if row["successful"] is not None and not isinstance(row["successful"], bool):
        fail("successful must be true, false or null")
    cost = row["cost"]
    if cost is not None and (not _is_number(cost) or cost < 0):
        fail("cost must be null or a finite nonnegative number")
    for key in ("terminal_outcome", "safety_gate", "actual_engine", "actual_model"):
        if row[key] is not None and not isinstance(row[key], str):
            fail(f"{key} must be text or null")
    if not row["admitted"]:
        if (
            not reasons
            or row["dispatch_attempts"]
            or row["native_process_starts"]
            or row["executed"]
            or row["identity_qualified"]
            or row["replayed"]
            or any(
                row[key] is not None
                for key in (
                    "terminal_outcome",
                    "successful",
                    "safety_gate",
                    "actual_engine",
                    "actual_model",
                    "cost",
                )
            )
        ):
            fail("a blocked unit cannot carry execution, outcome or measurement values")
        return
    if reasons:
        fail("an admitted unit cannot carry blocked reasons")
    if row["native_process_starts"] > row["dispatch_attempts"]:
        fail("native process starts exceed dispatch attempts")
    if row["executed"] and (row["terminal_outcome"] is None or not row["native_process_starts"]):
        fail("an executed unit needs a terminal record and a native process start")
    if row["terminal_outcome"] is None and (
        row["successful"] is not None or row["replayed"] or row["identity_qualified"]
    ):
        fail("a unit without a terminal record cannot carry an outcome")
    if row["identity_qualified"] and not row["executed"]:
        fail("identity qualification requires execution")
    if row["replayed"] and not row["executed"]:
        fail("replay requires execution")
    if row["terminal_outcome"] is not None:
        expected = (
            row["executed"]
            and row["identity_qualified"]
            and row["terminal_outcome"] == "success"
            and row["safety_gate"] == "PASS"
        )
        if row["successful"] is not expected:
            fail("success flag contradicts terminal outcome, identity or safety gate")


def _checked_rows(protocol: dict, raw_rows: Any) -> list[dict[str, Any]]:
    validate_protocol(protocol)
    if not isinstance(raw_rows, list):
        raise TypeError("rows must be a list")
    ids = [row.get("unit_id") if isinstance(row, dict) else None for row in raw_rows]
    if len(set(map(str, ids))) != len(ids):
        raise ValueError("duplicate unit rows")
    units = {unit["unit_id"]: unit for unit in protocol["units"]}
    if set(ids) != set(units):
        raise ValueError(
            f"row membership drift: {len(set(units) - set(ids))} missing, "
            f"{len(set(ids) - set(units))} unknown"
        )
    for row in raw_rows:
        _check_row(row, units[row["unit_id"]])
    return raw_rows


def reconcile_results(protocol: dict, raw_rows: list[dict]) -> dict:
    rows = _checked_rows(protocol, raw_rows)
    counts = _counts(rows)
    admitted = [row for row in rows if row["admitted"]]
    known = [row["cost"] for row in admitted if row["cost"] is not None]
    unknown_cost = len(admitted) - len(known)
    tracks = {
        name: _counts([row for row in rows if row["track"] == name])
        for name in ("runtime", "development")
    }
    if not admitted:
        status = "NOT_RUN/BLOCKED"
    elif counts["assigned"] < counts["planned"] or counts["missing"]:
        status = "PARTIAL"
    else:
        status = "COMPLETE_ANALYSIS_NOT_IMPLEMENTED"
    return {
        "schema": "prospective-pilot-summary/v1",
        "study_id": STUDY_ID,
        "counts": {key: counts[key] for key in _COUNT_KEYS},
        "tracks": tracks,
        "success_rate": counts["successful"] / len(admitted) if admitted else None,
        "observed_cost": math.fsum(known) if admitted and unknown_cost == 0 else None,
        "known_cost_subtotal": math.fsum(known) if known else None,
        "unknown_cost_units": unknown_cost,
        # No estimator is implemented: an effect is never reported, even from complete data.
        "effect_estimate": None,
        "status": status,
        # The pre-registered comparison is not implemented here, so the conclusion is never MET.
        "conclusion": "NOT_MET",
    }


def validate_analysis(protocol: dict, raw_rows: list[dict], summary: dict) -> dict:
    expected = reconcile_results(protocol, raw_rows)
    if not isinstance(summary, dict):
        raise TypeError("summary must be an object")
    for key in sorted(set(expected) | set(summary)):
        if canonical_json(summary.get(key, "<absent>")) != canonical_json(
            expected.get(key, "<absent>")
        ):
            raise ValueError(f"summary field {key!r} does not match the raw rows")
    return {
        "status": "PASS",
        "rows": len(raw_rows),
        "summary_sha256": sha256_hex(canonical_json(summary)),
    }


# ---------------------------------------------------------------- task freeze, leakage, binding
VARIANT_RESULTS_NAME = "variant-results-v1.json"
HIDDEN_LITERALS_NAME = "hidden-literals-v1.json"
_BLOCKED_FREEZE = "BLOCKED_TASK_FREEZE_INCOMPLETE"
_VARIANTS = ("known_good", "alternative_correct", "baseline", "plausible_wrong")
_VARIANT_EXPECTED = (True, True, False, False)
_LEAK_KEYS = frozenset(
    {"known_good_files", "added_lines", "hidden_literals", "hidden_case_ids", "disclosures"}
)
_FORBIDDEN_PREFIXES = ("source-snapshot", "frozen-packet", "candidate-final")
_TOKEN = re.compile(
    r"""(?P<comment>/\*.*?\*/|//[^\n]*|\#[^\n]*)"""
    r"""|(?P<string>\"\"\".*?\"\"\"|'''.*?'''|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'"""
    r"""|`(?:\\.|[^`\\])*`)"""
    r"""|(?P<word>[A-Za-z_$][A-Za-z0-9_$]*|\d+(?:\.\d+)?)"""
    r"""|(?P<op>==|!=|<=|>=|=>|->|&&|\|\||\S)""",
    re.DOTALL,
)
_TOKEN_WINDOW = 12
_LINE_MIN = 20


def _tokens(text: str) -> list[str]:
    return [m.group() for m in _TOKEN.finditer(text) if m.lastgroup != "comment"]


def _windows(tokens: list[str]) -> set[str]:
    return {
        "\x1f".join(tokens[i : i + _TOKEN_WINDOW]) for i in range(len(tokens) - _TOKEN_WINDOW + 1)
    }


def _forbidden_path(relative: str) -> bool:
    parts = relative.split("/")
    return (
        ".git" in parts
        or "_workspace" in parts
        or relative.startswith("research/development-cases/")
        or any(part.startswith(_FORBIDDEN_PREFIXES) for part in parts)
        or parts[-1].endswith((".patch", ".diff"))
    )


def _non_space(text: str) -> int:
    return sum(not char.isspace() for char in text)


def validate_task_source_binding(baseline: Path, corpus_overlay: Path, manifest: dict) -> dict:
    """Baseline and exploration-corpus copy must be byte-identical and bound to the pinned source."""
    if not isinstance(manifest, dict) or manifest.get("source_commit") != SOURCE_COMMIT:
        raise ValueError("task is not bound to the pinned source commit")
    base, overlay = Path(baseline).read_bytes(), Path(corpus_overlay).read_bytes()
    digest = sha256_hex(base)
    if manifest.get("baseline_sha256") != digest:
        raise ValueError("baseline bytes do not match the committed baseline hash")
    if sha256_hex(overlay) != digest:
        raise ValueError("the exploration corpus copy does not carry the baseline's defect")
    if manifest.get("source_sha256") == digest:
        raise ValueError("the baseline equals the pinned known-good source: no defect was injected")
    return {"status": "PASS", "source_commit": SOURCE_COMMIT, "baseline_sha256": digest}


def audit_task_leakage(
    public_root: Path,
    trust_root: Path,
    oracle_manifest: dict,
    *,
    baseline_texts: tuple[str, ...] = (),
) -> dict:
    """Real byte/line/token-window search of a readable tree for known-good or hidden material."""
    if any(path.is_symlink() for path in (Path(public_root), *Path(public_root).parents)):
        raise ValueError("public root contains a symlink")
    public, trust = Path(public_root).resolve(), Path(trust_root).resolve()
    if not public.is_dir() or not trust.is_dir():
        raise ValueError("public and trust roots must be directories")
    if public == trust or public.is_relative_to(trust) or trust.is_relative_to(public):
        raise ValueError("public and evaluator-only roots must be disjoint")
    if not isinstance(oracle_manifest, dict) or set(oracle_manifest) != _LEAK_KEYS:
        raise ValueError("oracle manifest must have exactly the five leakage keys")
    texts = {
        key: oracle_manifest[key]
        for key in ("added_lines", "hidden_literals", "hidden_case_ids", "known_good_files")
    }
    if any(
        not isinstance(v, list) or any(not isinstance(i, str) or not i for i in v)
        for v in texts.values()
    ):
        raise ValueError("manifest lists must hold non-empty strings")
    known_hashes = {sha256_hex(Path(path).read_bytes()) for path in texts["known_good_files"]}
    lines = [
        line.strip()
        for hunk in texts["added_lines"]
        for line in hunk.splitlines()
        if _non_space(line) >= _LINE_MIN
    ]
    windows = set().union(*(_windows(_tokens(hunk)) for hunk in texts["added_lines"]))
    if not isinstance(baseline_texts, tuple) or any(
        not isinstance(text, str) for text in baseline_texts
    ):
        raise ValueError("baseline_texts must be a tuple of frozen defective source texts")
    for baseline in baseline_texts:
        windows.difference_update(_windows(_tokens(baseline)))
    hidden = [
        item.encode("utf-8") for item in (*texts["hidden_literals"], *texts["hidden_case_ids"])
    ]
    disclosed: dict[str, str] = {}
    for item in oracle_manifest["disclosures"]:
        path = item.get("path") if isinstance(item, dict) else None
        digest = item.get("sha256") if isinstance(item, dict) else None
        if (
            not isinstance(path, str)
            or not path
            or path.startswith("/")
            or ".." in path.split("/")
            or not isinstance(digest, str)
            or not _HEX64.fullmatch(digest)
            or item.get("kind") not in ("public-test", "semantic-mirror")
            or path in disclosed
        ):
            raise ValueError("invalid or duplicate mirror disclosure")
        disclosed[path] = digest
    violations, matched, scanned = [], {}, 0
    for directory, dirs, files in os.walk(public):
        dirs.sort()
        for name in dirs:
            path = Path(directory) / name
            if path.is_symlink():
                violations.append(f"{path.relative_to(public).as_posix()}: symlink")
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(public).as_posix()
            scanned += 1
            if path.is_symlink():
                violations.append(f"{relative}: symlink")
                continue
            if _forbidden_path(relative):
                violations.append(f"{relative}: forbidden history/answer surface")
            try:
                data = path.read_bytes()
            except OSError as error:
                raise ValueError(f"{relative}: unreadable ({error.__class__.__name__})") from error
            if any(item in data for item in hidden):
                violations.append(f"{relative}: hidden literal or case id")
                continue
            digest, kinds = sha256_hex(data), []
            if digest in known_hashes:
                kinds.append("whole_file")
            if b"\0" not in data:
                text = data.decode("utf-8", errors="replace")
                if any(line in text for line in lines):
                    kinds.append("added_line")
                if windows:
                    tokens = _tokens(text)
                    if any(
                        "\x1f".join(tokens[i : i + _TOKEN_WINDOW]) in windows
                        for i in range(len(tokens) - _TOKEN_WINDOW + 1)
                    ):
                        kinds.append("token_window")
            if kinds and disclosed.get(relative) == digest:
                matched[relative] = kinds
            elif kinds:
                violations.append(f"{relative}: undisclosed known-good match ({','.join(kinds)})")
    if violations:
        raise ValueError(
            f"task leakage: {len(violations)} violation(s): " + "; ".join(violations[:8])
        )
    return {
        "status": "PASS",
        "files_scanned": scanned,
        "disclosed_matches": [{"path": p, "kinds": k} for p, k in sorted(matched.items())],
        "unused_disclosures": sorted(set(disclosed) - set(matched)),
    }


def oracle_commitments(trust_root: Path) -> dict:
    """Hash every evaluator-only file (except the results file that embeds this commitment)."""
    root = Path(trust_root).resolve()
    files = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if (
            not path.is_file()
            or path.is_symlink()
            or relative == VARIANT_RESULTS_NAME
            or "__pycache__" in path.parts
            or path.suffix == ".pyc"
        ):
            continue
        files[relative] = sha256_hex(path.read_bytes())
    return {"files": len(files), "oracle_sha256": sha256_hex(canonical_json(files))}


def _read_json(path: Path) -> Any:
    return strict_json_loads(path.read_text(encoding="utf-8"), allow_whitespace=True)


def _task_row_status(
    task_id: str, bundle: Path, trust: Path, entry: Any, result: Any, spec_path: Path
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "task_id": task_id,
        "status": _BLOCKED_FREEZE,
        "known_good": None,
        "alternative_correct": None,
        "baseline": None,
        "plausible_wrong": None,
        "reasons": [],
    }
    incomplete, failed = row["reasons"], []
    if not isinstance(entry, dict):
        incomplete.append("task-manifest entry absent")
    if not spec_path.is_file():
        incomplete.append("task-spec.json absent")
    if not isinstance(result, dict):
        incomplete.append("no trusted variant-result row")
    if incomplete:
        return row
    spec = _read_json(spec_path)
    for variant in _VARIANTS:
        value = result.get(variant)
        if value is None:
            incomplete.append(f"{variant} observation missing")
        elif not isinstance(value, bool):
            failed.append(f"{variant} observation is not a boolean")
        else:
            row[variant] = value
    observed = tuple(row[v] for v in _VARIANTS)
    if None not in observed and observed != _VARIANT_EXPECTED:
        failed.append(f"oracle controls observed {observed}, expected {_VARIANT_EXPECTED}")
    if sha256_hex(spec_path.read_bytes()) != result.get("task_spec_sha256"):
        failed.append("task-spec.json bytes do not match the committed task_spec_sha256")
    if entry.get("source_commit") != SOURCE_COMMIT or spec.get("source_commit") != SOURCE_COMMIT:
        failed.append("task is not bound to the pinned source commit")
    target = spec.get("target_file")
    if not isinstance(target, str) or target.startswith("/") or ".." in target.split("/"):
        failed.append("unsafe target_file")
    else:
        try:
            validate_task_source_binding(
                bundle / task_id / "baseline" / target,
                bundle / task_id / "corpus-overlay" / target,
                {
                    "source_commit": entry.get("source_commit"),
                    "baseline_sha256": spec.get("baseline_sha256"),
                    "source_sha256": entry.get("source_sha256"),
                },
            )
            if entry.get("baseline_sha256") != spec.get("baseline_sha256"):
                failed.append("manifest and spec baseline hashes differ")
        except (OSError, ValueError) as error:
            failed.append(f"source binding: {error}")
    determinacy = trust / "tasks" / task_id / "determinacy.md"
    if not determinacy.is_file():
        incomplete.append("determinacy.md absent")
    else:
        digest = sha256_hex(determinacy.read_bytes())
        if digest != result.get("determinacy_sha256") or digest != entry.get("determinacy_sha256"):
            failed.append("determinacy.md bytes do not match the committed hashes")
    auditor = result.get("logic_auditor")
    if not isinstance(auditor, str) or not auditor:
        incomplete.append("independent logic auditor not recorded")
    elif entry.get("logic_auditor") not in (None, auditor):
        failed.append("auditor differs from the public record")
    if auditor and result.get("logic_verdict") != "PASS":
        (failed if result.get("logic_verdict") else incomplete).append(
            "logic auditor verdict is not PASS"
        )
    body = {key: value for key, value in result.items() if key != "receipt_sha256"}
    if result.get("receipt_sha256") is None:
        incomplete.append("row receipt hash missing")
    elif result["receipt_sha256"] != sha256_hex(canonical_json(body)):
        failed.append("row receipt hash does not match its content")
    row["reasons"] = [*incomplete, *failed]
    row["status"] = "FAIL" if failed else (_BLOCKED_FREEZE if incomplete else "PASS")
    return row


def _leak_manifest(bundle: Path, trust: Path, literals: dict[str, Any]) -> dict[str, Any]:
    known, added, disclosures = [], [], []
    for task_id in TASK_IDS:
        spec = _read_json(bundle / task_id / "task-spec.json")
        base = (bundle / task_id / "baseline" / spec["target_file"]).read_text(encoding="utf-8")
        baseline_lines = base.splitlines()
        for variant in ("known_good", "alternative_correct"):
            path = trust / "tasks" / task_id / "variants" / variant / spec["target_file"]
            known.append(str(path))
            variant_lines = path.read_text(encoding="utf-8").splitlines()
            # Each diff insertion/replacement is one contiguous added hunk. Never join
            # across unchanged context, other files, or the other correct variant.
            for tag, _, _, start, end in difflib.SequenceMatcher(
                None, baseline_lines, variant_lines, autojunk=False
            ).get_opcodes():
                if tag in ("insert", "replace"):
                    hunk = "\n".join(variant_lines[start:end])
                    if hunk.strip():
                        added.append(hunk)
        mirrors = bundle / task_id / "mirror-disclosures.json"
        if mirrors.is_file():
            disclosures += _read_json(mirrors)
    unique = {item["path"]: item for item in disclosures}.values()
    return {
        "known_good_files": known,
        "added_lines": added,
        "hidden_literals": literals["hidden_literals"],
        "hidden_case_ids": literals["hidden_case_ids"],
        "disclosures": list(unique),
    }


def verify_task_oracles(
    bundle_root: Path, trust_root: Path, *, corpus_roots: tuple[Path, ...] = ()
) -> dict:
    """Accept only trusted, hash-committed observations of the independent oracle; else BLOCKED.

    This never runs an oracle and never reads a ``verified`` flag as execution: the four
    variant booleans must come from the evaluator-only results file whose per-task spec,
    determinacy and row commitments, and whose whole-trust-root hash, are recomputed here.
    """
    bundle, trust = Path(bundle_root), Path(trust_root)
    reasons, failures = [], []
    manifest = results = None
    manifest_path, results_path = bundle / "task-manifest.json", trust / VARIANT_RESULTS_NAME
    try:
        manifest = _read_json(manifest_path) if manifest_path.is_file() else None
        results = _read_json(results_path) if results_path.is_file() else None
    except (OSError, ValueError) as error:
        failures.append(f"malformed input: {error}")
    if manifest is None:
        reasons.append("public task-manifest.json absent")
    if results is None:
        reasons.append(f"trusted {VARIANT_RESULTS_NAME} absent: no oracle observation supplied")
    oracle_hash = None
    entries = (
        {e.get("task_id"): e for e in manifest.get("tasks", []) if isinstance(e, dict)}
        if isinstance(manifest, dict) and isinstance(manifest.get("tasks"), list)
        else {}
    )
    rows_by_id = (
        {r.get("task_id"): r for r in results.get("tasks", []) if isinstance(r, dict)}
        if isinstance(results, dict) and isinstance(results.get("tasks"), list)
        else {}
    )
    if isinstance(results, dict):
        oracle_hash = oracle_commitments(trust)["oracle_sha256"]
        if results.get("source_commit") != SOURCE_COMMIT:
            failures.append("results are not bound to the pinned source commit")
        if results.get("oracle_sha256") != oracle_hash:
            failures.append("oracle bytes differ from the committed oracle_sha256")
    rows = []
    for task_id in TASK_IDS:
        try:
            rows.append(
                _task_row_status(
                    task_id,
                    bundle,
                    trust,
                    entries.get(task_id),
                    rows_by_id.get(task_id),
                    bundle / task_id / "task-spec.json",
                )
            )
        except (OSError, ValueError) as error:
            rows.append(
                {
                    "task_id": task_id,
                    "status": "FAIL",
                    "known_good": None,
                    "alternative_correct": None,
                    "baseline": None,
                    "plausible_wrong": None,
                    "reasons": [f"unreadable task input: {error}"],
                }
            )
    leakage = None
    literals_path = trust / HIDDEN_LITERALS_NAME
    if isinstance(results, dict) and manifest is not None:
        if not literals_path.is_file():
            reasons.append(f"{HIDDEN_LITERALS_NAME} absent: hidden-literal leakage unchecked")
        else:
            try:
                literals = _read_json(literals_path)
                leak_manifest = _leak_manifest(bundle, trust, literals)
                baseline_texts = tuple(
                    (
                        bundle
                        / row["task_id"]
                        / "baseline"
                        / _read_json(bundle / row["task_id"] / "task-spec.json")["target_file"]
                    ).read_text(encoding="utf-8")
                    for row in rows
                    if row["status"] == "PASS"
                )
                parts = [
                    audit_task_leakage(root, trust, leak_manifest, baseline_texts=baseline_texts)
                    for root in (bundle, *map(Path, corpus_roots))
                ]
                leakage = {
                    "status": "PASS",
                    "roots": len(parts),
                    "files_scanned": sum(p["files_scanned"] for p in parts),
                }
            except (OSError, ValueError, KeyError, TypeError) as error:
                leakage = {"status": "FAIL", "error": str(error)}
                failures.append(f"leakage: {error}")
    if failures or any(row["status"] == "FAIL" for row in rows):
        status = "FAIL"
    elif all(row["status"] == "PASS" for row in rows) and leakage and leakage["status"] == "PASS":
        status = "PASS"
    else:
        status = _BLOCKED_FREEZE
    return {
        "status": status,
        "source_commit": SOURCE_COMMIT,
        "oracle_sha256": oracle_hash,
        "leakage": leakage,
        "reasons": [*reasons, *failures],
        "tasks": rows,
    }
