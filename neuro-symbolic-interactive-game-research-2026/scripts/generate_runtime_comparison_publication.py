#!/usr/bin/env python3
"""Render the fixed-game native runtime comparison from public-safe results.

Separate strict modes accept the frozen eight-row comparison or the stopped
identity-admission packet, never a pooled cohort. Invalid or absent evidence
produces no output. The renderer uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = (
    ROOT / "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json"
)
INPUT_PATH = RESULTS_PATH
OUTPUT_DIR = ROOT / "paper/latex/generated"
FIGURES_DIR = ROOT / "paper/latex/figures"

SCHEMA_VERSION = "codex-runtime-public-results/1"
STUDY_ID = "codex-paired-public-20261026"
QUEST_ID = "sealed-lighthouse-v1"
SELECTORS = ("gpt-6.1-sol", "gpt-5.6-sol")
REPRESENTATIONS = ("general_rule", "ontology")
REPEATS = (1, 2)
SEED = 20261024
REQUIRED_STATUS = "complete"
PUBLIC_RESULTS_SHA256 = "ba369ab2f4e02afaeac643490e13fe6785ac7f8cbd04a5b88507c2cc4691c26e"
IDENTITY_RESULTS_PATH = (
    ROOT
    / "research/runtime-model-swap-20261024/codex-identity-20261026/public-results-v1/results.json"
)
IDENTITY_RESULTS_SHA256 = "12fee3535d99930311b71ffa7e56b9aaa8b220353a14533cc25194211bf5554c"
IDENTITY_SELECTORS = ("gpt-6-luna", "gpt-6-sol", "gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.6-terra")

_IDENTITY_FIXED_METADATA = {
    "prior_cohort": {
        "results_sha256": PUBLIC_RESULTS_SHA256,
        "pooled": False,
        "unchanged": True,
        "assigned": 8,
        "system_goal_successes": 5,
    },
    "failure": {
        "primary": "provider_identity_missing",
        "secondary": "outgoing_request_tuple_not_bound",
        "record_hash_valid": True,
        "semantic_record_links_valid": True,
        "engineering_record_accepted": False,
        "raw_bootstrap_stop_reason": "episode_record_integrity_invalid",
        "raw_terminal_failure_reason": "repair_source_error",
        "safety": "NO_COMMIT_OBSERVED",
        "fresh_engine_replay": "NOT_RUN",
        "proposal_constraint_validity": None,
        "model_incapability_inferred": False,
    },
    "unsupported_request": {
        "requested_selector": "gpt-6-terra",
        "catalog_status": "NOT_ADVERTISED_IN_PINNED_CATALOG",
        "assigned": 0,
        "substituted": False,
    },
    "diagnosis": {
        "bounded_source_fallback_review": "PASS_UNATTESTED",
        "dedicated_tracer_status": "UNAVAILABLE_HTTP_429",
        "identity_state": "MISSING_NOT_MISMATCHED",
        "logging_target_level_correct": True,
        "missing_or_nonstring_header_unresolved": True,
        "provider_model_header": "openai-model",
        "source_urls": [
            "https://github.com/openai/codex/blob/rust-v0.164.0/codex-rs/codex-api/src/sse/responses.rs#L38-L76",
            "https://github.com/openai/codex/blob/rust-v0.164.0/codex-rs/core/src/session/turn.rs#L3121-L3135",
            "https://github.com/openai/codex/blob/rust-v0.164.0/codex-rs/core/src/session/mod.rs#L4209-L4230",
        ],
    },
    "claims": {
        "new_verified_model_comparison": False,
        "ontology_effect_demonstrated": False,
        "confirmatory_A_C_established": False,
        "zero_cost_or_zero_credit_claimed": False,
        "no_rerun": True,
    },
}

ROW_FIELDS = (
    "row_id",
    "planned_id",
    "requested_selector",
    "representation",
    "repeat",
    "assigned",
    "executed",
    "status",
    "failure_reason",
    "primary_success",
    "goal_reached",
    "host_invocations_observed",
    "provider_request_count",
    "repair_calls",
    "initial_proposal_failures",
    "timeout_calls",
    "committed_transitions",
    "unsafe_committed_transitions",
    "safety_status",
    "replay_valid",
    "engine_reexecution_valid",
    "engine_reexecution_status",
    "elapsed_seconds",
    "preparation_seconds",
    "outgoing_requests_bound",
    "provider_identity",
    "provider_revision",
    "cost_usd",
    "source_manifest_sha256",
    "episode_sha256",
    "result_sha256",
)

_SCOPE = {
    "quest_id": QUEST_ID,
    "selectors": list(SELECTORS),
    "representations": list(REPRESENTATIONS),
    "repeats": 2,
    "seed": SEED,
    "concurrency": 1,
    "episode_wall_seconds": 180,
    "response_seconds": 60,
    "maximum_host_invocations": 12,
    "maximum_repairs_per_decision": 2,
}

_STATUS = ("success", "failure", "technical_failure")
_SAFETY = ("PASS", "FAIL", "NO_COMMIT_OBSERVED", "NOT_OBSERVED")
_ENGINE_REEXECUTION_STATUS = ("VALID", "INVALID", "NOT_RUN", "NOT_OBSERVED")
_SHA256 = set("0123456789abcdef")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_number(value: Any) -> bool:
    return type(value) in (int, float) and not isinstance(value, bool)


def _optional_nonnegative_int(value: Any, label: str) -> None:
    _require(
        value is None or (_is_int(value) and value >= 0),
        f"{label} must be a nonnegative integer or null",
    )


def _optional_nonnegative_number(value: Any, label: str) -> None:
    _require(
        value is None or (_is_number(value) and math.isfinite(float(value)) and value >= 0),
        f"{label} must be finite and nonnegative or null",
    )


def _sha256(value: Any, label: str, *, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    _require(
        isinstance(value, str) and len(value) == 64 and all(char in _SHA256 for char in value),
        f"{label} must be a lowercase SHA-256 digest",
    )


def expected_planned_ids() -> tuple[str, ...]:
    """Return the frozen row order used by the public packet."""

    return tuple(
        f"{QUEST_ID}:{selector}:{representation}:repeat-{repeat}"
        for selector in SELECTORS
        for representation in REPRESENTATIONS
        for repeat in REPEATS
    )


def _parse_planned_id(value: str) -> tuple[str, str, str, int]:
    parts = value.split(":")
    _require(len(parts) == 4, f"invalid planned_id: {value!r}")
    quest, selector, representation, repeat_token = parts
    _require(repeat_token.startswith("repeat-"), f"invalid planned_id repeat: {value!r}")
    try:
        repeat = int(repeat_token.removeprefix("repeat-"))
    except ValueError as exc:
        raise ValueError(f"invalid planned_id repeat: {value!r}") from exc
    return quest, selector, representation, repeat


def _validate_row(row: Mapping[str, Any], index: int) -> None:
    _require(set(row) == set(ROW_FIELDS), f"row {index + 1} fields drifted")
    row_id = row["row_id"]
    _require(
        _is_int(row_id) and 1 <= row_id <= 8, f"row {index + 1} row_id must be an integer 1..8"
    )
    planned_id = row["planned_id"]
    _require(isinstance(planned_id, str), f"row {row_id} planned_id must be a string")
    quest, selector, representation, repeat = _parse_planned_id(planned_id)
    _require(quest == QUEST_ID, f"row {row_id} quest drift")
    _require(selector in SELECTORS, f"row {row_id} selector drift")
    _require(representation in REPRESENTATIONS, f"row {row_id} representation drift")
    _require(repeat in REPEATS, f"row {row_id} repeat drift")
    _require(
        row["requested_selector"] == selector,
        f"row {row_id} requested selector disagrees with planned_id",
    )
    _require(
        row["representation"] == representation,
        f"row {row_id} representation disagrees with planned_id",
    )
    _require(row["repeat"] == repeat, f"row {row_id} repeat disagrees with planned_id")
    _require(row["assigned"] is True, f"row {row_id} is not assigned")

    _require(
        row["executed"] is None or type(row["executed"]) is bool,
        f"row {row_id} executed must be boolean or null",
    )
    _require(row["status"] in _STATUS, f"row {row_id} status is invalid")
    _require(type(row["primary_success"]) is bool, f"row {row_id} primary_success must be boolean")
    _require(
        row["primary_success"] is (row["status"] == "success"),
        f"row {row_id} status/success disagreement",
    )
    _require(
        row["goal_reached"] is None or type(row["goal_reached"]) is bool,
        f"row {row_id} goal_reached must be boolean or null",
    )
    _require(
        row["engine_reexecution_status"] in _ENGINE_REEXECUTION_STATUS,
        f"row {row_id} engine_reexecution_status invalid",
    )
    if row["engine_reexecution_status"] in ("VALID", "INVALID"):
        _require(
            row["engine_reexecution_valid"] is (row["engine_reexecution_status"] == "VALID"),
            f"row {row_id} engine reexecution status/valid disagreement",
        )
    else:
        _require(
            row["engine_reexecution_valid"] is None,
            f"row {row_id} non-terminal engine reexecution must have null validity",
        )

    reason = row["failure_reason"]
    _require(
        reason is None or (isinstance(reason, str) and bool(reason.strip())),
        f"row {row_id} failure_reason invalid",
    )
    if row["status"] == "success":
        _require(reason is None, f"row {row_id} success cannot have failure_reason")
    else:
        _require(reason is not None, f"row {row_id} failure requires failure_reason")

    _require(
        _is_int(row["host_invocations_observed"])
        and 0 <= row["host_invocations_observed"] <= _SCOPE["maximum_host_invocations"],
        f"row {row_id} host_invocations_observed must be an integer in 0..{_SCOPE['maximum_host_invocations']}",
    )
    _require(
        row["provider_request_count"] is None,
        f"row {row_id} provider_request_count must remain null",
    )
    for field in (
        "repair_calls",
        "initial_proposal_failures",
        "timeout_calls",
        "committed_transitions",
        "unsafe_committed_transitions",
    ):
        _optional_nonnegative_int(row[field], f"row {row_id} {field}")
    _require(row["safety_status"] in _SAFETY, f"row {row_id} safety_status invalid")
    for field in ("replay_valid", "engine_reexecution_valid", "outgoing_requests_bound"):
        _require(
            row[field] is None or type(row[field]) is bool,
            f"row {row_id} {field} must be boolean or null",
        )
    for field in ("elapsed_seconds", "preparation_seconds"):
        _optional_nonnegative_number(row[field], f"row {row_id} {field}")
    if row["primary_success"]:
        _require(row["executed"] is True, f"row {row_id} primary_success requires executed=true")
        _require(
            row["goal_reached"] is True, f"row {row_id} primary_success requires goal_reached=true"
        )
        _require(
            row["elapsed_seconds"] is not None
            and row["elapsed_seconds"] <= _SCOPE["episode_wall_seconds"],
            f"row {row_id} primary_success exceeds frozen episode wall bound",
        )

    # Provider identity, revision, and cost are outside the public observation boundary.
    _require(row["provider_identity"] is None, f"row {row_id} provider_identity must remain null")
    _require(row["provider_revision"] is None, f"row {row_id} provider_revision must remain null")
    _require(row["cost_usd"] is None, f"row {row_id} cost_usd must remain null")
    _sha256(row["source_manifest_sha256"], f"row {row_id} source_manifest_sha256")
    _sha256(row["episode_sha256"], f"row {row_id} episode_sha256", nullable=True)
    _sha256(row["result_sha256"], f"row {row_id} result_sha256")

    executed = row["executed"] is True
    if not executed:
        # A no-episode row may retain the zero receipt count, but no unobserved
        # endpoint metric may be represented as a fabricated zero.
        _require(
            row["host_invocations_observed"] == 0, f"row {row_id} non-executed row has host calls"
        )
        for field in (
            "repair_calls",
            "initial_proposal_failures",
            "timeout_calls",
            "committed_transitions",
            "unsafe_committed_transitions",
            "goal_reached",
            "replay_valid",
            "engine_reexecution_valid",
            "elapsed_seconds",
        ):
            _require(row[field] is None, f"row {row_id} non-executed {field} must be null")
        _require(
            row["safety_status"] == "NOT_OBSERVED",
            f"row {row_id} non-executed safety must be NOT_OBSERVED",
        )
    else:
        _require(
            row["host_invocations_observed"] > 0, f"row {row_id} executed row has no host receipt"
        )

    # A committed unsafe transition cannot exceed the observed committed count.
    if row["unsafe_committed_transitions"] is not None and row["committed_transitions"] is not None:
        _require(
            row["unsafe_committed_transitions"] <= row["committed_transitions"],
            f"row {row_id} unsafe transitions exceed committed transitions",
        )


def validate_public_results(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize a complete public packet independent of its source path."""

    _require(isinstance(payload, Mapping), "public runtime results must be an object")
    expected_top = {"schema_version", "study_id", "status", "scope", "rows"}
    _require(set(payload) == expected_top, "public runtime result top-level fields drifted")
    _require(payload["schema_version"] == SCHEMA_VERSION, "public runtime result schema mismatch")
    _require(payload["study_id"] == STUDY_ID, "public runtime result study mismatch")
    _require(payload["status"] == REQUIRED_STATUS, "public runtime result status is not complete")
    _require(payload["scope"] == _SCOPE, "public runtime result scope drifted")
    rows = payload["rows"]
    _require(
        isinstance(rows, list) and len(rows) == 8,
        "public runtime result must contain exactly eight rows",
    )
    for index, row in enumerate(rows):
        _require(isinstance(row, Mapping), f"row {index + 1} must be an object")
        _validate_row(row, index)
    by_id = {row["row_id"]: row for row in rows}
    _require(
        len(by_id) == 8 and set(by_id) == set(range(1, 9)),
        "row_id values are duplicated or incomplete",
    )
    expected_ids = expected_planned_ids()
    ordered = [by_id[index] for index in range(1, 9)]
    _require(
        tuple(row["planned_id"] for row in ordered) == expected_ids, "planned_id set/order drifted"
    )
    _require(all(row["assigned"] is True for row in ordered), "assigned denominator is incomplete")

    first = ordered[0]
    _require(first["status"] == "technical_failure", "retained first row is not technical_failure")
    _require(
        first["executed"] is None and first["host_invocations_observed"] == 0,
        "retained first row execution accounting drifted",
    )
    _require(
        first["failure_reason"] and "serial" in first["failure_reason"].casefold(),
        "retained first row is not a serialization failure",
    )
    _require(first["episode_sha256"] is None, "retained first row must not claim an episode hash")
    _require(
        first["preparation_seconds"] is None and first["outgoing_requests_bound"] is None,
        "retained first row must not claim timing/request observations",
    )
    timeout_rows = [
        row
        for row in ordered
        if row["requested_selector"] == "gpt-6.1-sol"
        and row["representation"] == "ontology"
        and row["status"] != "success"
        and (row["failure_reason"] == "response_timeout" or (row["timeout_calls"] or 0) > 0)
    ]
    _require(timeout_rows, "at least one GPT-6.1 ontology response_timeout row is required")
    return {
        "schema_version": payload["schema_version"],
        "study_id": payload["study_id"],
        "status": payload["status"],
        "scope": payload["scope"],
        "rows": ordered,
    }


def load_public_results(path: Path | str = INPUT_PATH) -> dict[str, Any]:
    """Load the fixed public packet once, pinning its exact bytes before validation."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"public runtime results are absent: {source}")
    try:
        raw = source.read_bytes()
    except OSError as exc:
        raise ValueError(f"cannot read public runtime results: {source}") from exc
    digest = hashlib.sha256(raw).hexdigest()
    _require(
        digest == PUBLIC_RESULTS_SHA256,
        f"public runtime results hash mismatch: expected {PUBLIC_RESULTS_SHA256}, got {digest}",
    )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot parse public runtime results: {source}") from exc
    return validate_public_results(payload)


def _optional_sum(rows: Iterable[Mapping[str, Any]], field: str) -> int | None:
    values = [row[field] for row in rows if row[field] is not None]
    return sum(values) if values else None


def _counts(rows: Iterable[Mapping[str, Any]], field: str) -> dict[str, int]:
    values = [row[field] for row in rows]
    return {
        "true": sum(value is True for value in values),
        "false": sum(value is False for value in values),
        "unknown": sum(value is None for value in values),
    }


def _duration(values: Iterable[Any]) -> dict[str, Any]:
    observed = [float(value) for value in values if value is not None]
    if not observed:
        return {"n": 0, "mean": None, "median": None, "min": None, "max": None}
    return {
        "n": len(observed),
        "mean": statistics.fmean(observed),
        "median": statistics.median(observed),
        "min": min(observed),
        "max": max(observed),
    }


def _summary(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "assigned": len(rows),
        "system_successes": sum(row["primary_success"] is True for row in rows),
        "observed_executions": sum(row["executed"] is True for row in rows),
        "host_invocations": sum(int(row["host_invocations_observed"]) for row in rows),
        "repairs": {
            "sum": _optional_sum(rows, "repair_calls"),
            "observed_rows": sum(row["repair_calls"] is not None for row in rows),
        },
        "initial_proposal_failures": {
            "sum": _optional_sum(rows, "initial_proposal_failures"),
            "observed_rows": sum(row["initial_proposal_failures"] is not None for row in rows),
        },
        "timeout_calls": {
            "sum": _optional_sum(rows, "timeout_calls"),
            "observed_rows": sum(row["timeout_calls"] is not None for row in rows),
        },
        "transitions": {
            "committed": _optional_sum(rows, "committed_transitions"),
            "unsafe_committed": _optional_sum(rows, "unsafe_committed_transitions"),
            "observed_rows": sum(row["committed_transitions"] is not None for row in rows),
        },
        "replay_valid": _counts(rows, "replay_valid"),
        "engine_reexecution_status": {
            status: sum(row["engine_reexecution_status"] == status for row in rows)
            for status in _ENGINE_REEXECUTION_STATUS
        },
        "durations": {
            "elapsed_seconds": _duration(row["elapsed_seconds"] for row in rows),
            "preparation_seconds": _duration(row["preparation_seconds"] for row in rows),
        },
        "status_counts": {
            status: sum(row["status"] == status for row in rows) for status in _STATUS
        },
    }


def compute_aggregates(data: Mapping[str, Any]) -> dict[str, Any]:
    """Derive overall and four-cell summaries exclusively from validated rows."""

    rows = list(data["rows"])
    cells = []
    for selector in SELECTORS:
        for representation in REPRESENTATIONS:
            cell_rows = [
                row
                for row in rows
                if row["requested_selector"] == selector and row["representation"] == representation
            ]
            _require(len(cell_rows) == 2, f"cell is not n=2: {selector}/{representation}")
            cell = _summary(cell_rows)
            cell.update({"selector": selector, "representation": representation, "rows": cell_rows})
            cells.append(cell)
    overall = _summary(rows)
    return {"overall": overall, "cells": cells}


def _latex(value: Any) -> str:
    text = str(value)
    for old, new in (
        ("\\", r"\textbackslash{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("&", r"\&"),
        ("#", r"\#"),
        ("{", r"\{"),
        ("}", r"\}"),
    ):
        text = text.replace(old, new)
    return text


def _fmt(value: Any, *, digits: int = 2) -> str:
    if value is None:
        return "NR"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _duration_text(summary: Mapping[str, Any]) -> str:
    return (
        "NR"
        if summary["n"] == 0
        else f"n={summary['n']}; {_fmt(summary['mean'])}/{_fmt(summary['median'])}"
    )


def _engine_status_text(counts: Mapping[str, int]) -> str:
    return "; ".join(f"{name}={counts[name]}" for name in _ENGINE_REEXECUTION_STATUS)


def render_results_fragment(data: Mapping[str, Any], korean: bool = False) -> str:
    agg = compute_aggregates(data)
    overall = agg["overall"]
    timeout_n = sum(
        row["requested_selector"] == "gpt-6.1-sol"
        and row["representation"] == "ontology"
        and row["failure_reason"] == "response_timeout"
        for row in data["rows"]
    )
    elapsed = overall["durations"]["elapsed_seconds"]
    preparation = overall["durations"]["preparation_seconds"]
    repairs = overall["repairs"]["sum"]
    unsafe = overall["transitions"]["unsafe_committed"]
    committed = overall["transitions"]["committed"]
    replay = overall["replay_valid"]
    engine_status = _latex(_engine_status_text(overall["engine_reexecution_status"]))
    if korean:
        return (
            rf"""\subsection{{고정 게임 native runtime 비교}}
이 공개 결과는 하나의 authored quest(\texttt{{{_latex(QUEST_ID)}}})에 대해 seed {SEED}, selector당 representation별 반복 2회의 {overall["assigned"]}개 배정 행을 보존한다. 시스템 endpoint 성공은 {overall["system_successes"]}/{overall["assigned"]}이고, 관측된 native 실행은 {overall["observed_executions"]}개이다. 실제 receipt에서 집계한 host 호출은 {overall["host_invocations"]}회이며, 관측된 repair 합은 {_fmt(repairs)}이다. committed transition은 {_fmt(committed)}, 그중 unsafe는 {_fmt(unsafe)}이며, semantic replay valid/invalid/NR은 {replay["true"]}/{replay["false"]}/{replay["unknown"]}이다. fresh-engine reexecution 처분은 {engine_status}이다. elapsed 관측은 {_duration_text(elapsed)}초(평균/중앙값), preparation 관측은 {_duration_text(preparation)}초이다. 보고되지 않은 값은 0이 아니라 NR이다.

첫 행은 harness JSON serialization 기술 실패로 유지되어 GPT-6.1 능력에 귀속하지 않는다. GPT-6.1 ontology에서 response-timeout 행 {timeout_n}개 이상을 frozen 60초 경계 안의 실패로 보존한다. 모델은 typed-intent proposal만 담당하고 deterministic Python planner/checker와 Godot commit이 권한을 유지한다. 따라서 이 표는 한 quest의 기술적 관측이며 efficacy, superiority, noninferiority, 일반 ontology 일관성 또는 player benefit을 주장하지 않는다. semantic record-link replay만으로 fresh-engine reexecution을 주장하지 않는다. provider identity/revision/cost와 provider request 수는 공개 관측 경계를 넘어 NR이다.
""".strip()
            + "\n"
        )
    return (
        rf"""\subsection{{Fixed-game native runtime comparison}}
This public packet retains {overall["assigned"]} assigned rows for one authored quest (\texttt{{{_latex(QUEST_ID)}}}), with seed {SEED} and two repeats per selector/representation cell. System-endpoint successes are {overall["system_successes"]}/{overall["assigned"]}; observed native executions are {overall["observed_executions"]}. Host invocations are summed from actual receipts ({overall["host_invocations"]}), and observed repairs sum to {_fmt(repairs)}. Committed transitions total {_fmt(committed)}, of which unsafe are {_fmt(unsafe)}; semantic replay valid/invalid/NR is {replay["true"]}/{replay["false"]}/{replay["unknown"]}. Fresh-engine reexecution disposition counts are {engine_status}. Observed elapsed time is {_duration_text(elapsed)} seconds (mean/median), and preparation time is {_duration_text(preparation)} seconds. Unreported values are NR, not zero.

The first row is retained as a harness JSON-serialization technical failure and is not attributed to GPT-6.1 capability. At least {timeout_n} GPT-6.1 ontology row(s) retain a response-timeout failure under the frozen 60-second bound. Models provide typed-intent proposals; the deterministic Python planner/checker and Godot commit retain authority. The table is therefore a technical observation for one quest, not an efficacy, superiority, noninferiority, general ontology-consistency, or player-benefit claim. Semantic record-link replay is not fresh-engine reexecution. Provider identity/revision/cost and provider-request counts remain NR outside the public observation boundary.
""".strip()
        + "\n"
    )


def render_tables_fragment(data: Mapping[str, Any], korean: bool = False) -> str:
    agg = compute_aggregates(data)
    cells = agg["cells"]
    engine_order = _latex("/".join(_ENGINE_REEXECUTION_STATUS))
    if korean:
        caption = "고정 게임 native runtime 비교(n=2/셀). 기술 실패와 timeout을 포함한 원래 8개 배정 행을 분모에 보존한다."
        headers = (
            "요청 selector & 표현 & 목표/배정 & 관측 실행 & Host 호출 & Unsafe/Commit & Elapsed 중앙값(s; n) & Fresh engine"
            + r" \\"
        )
        note = f"Fresh engine은 {engine_order} 순서의 건수이다. NR은 미보고이지 0이 아니다. 전체 계수와 semantic replay의 구분은 본문에 보고한다."
    else:
        caption = "Fixed-game native runtime comparison (n=2 per cell). All eight assignments, including the harness failure and timeouts, remain in denominators."
        headers = (
            "Requested selector & Form & Goal/assigned & Observed exec. & Host calls & Unsafe/committed & Elapsed median (s; n) & Fresh engine"
            + r" \\"
        )
        note = f"Fresh engine counts follow {engine_order} order. NR is unreported, not zero. Overall counts and the separate semantic replay are reported in the text."
    rows = []
    for cell in cells:
        summary = cell
        goal_values = [row["goal_reached"] for row in summary["rows"]]
        goal_count = (
            sum(value is True for value in goal_values)
            if any(value is not None for value in goal_values)
            else None
        )
        elapsed_summary = summary["durations"]["elapsed_seconds"]
        elapsed_label = (
            "NR"
            if elapsed_summary["n"] == 0
            else f"{_fmt(elapsed_summary['median'])} ({elapsed_summary['n']})"
        )
        engine_status = summary["engine_reexecution_status"]
        engine_counts = "/".join(str(engine_status[name]) for name in _ENGINE_REEXECUTION_STATUS)
        rows.append(
            " & ".join(
                (
                    _latex(summary["selector"]),
                    _latex(summary["representation"]),
                    f"{_fmt(goal_count)}/{summary['assigned']}",
                    str(summary["observed_executions"]),
                    str(summary["host_invocations"]),
                    f"{_fmt(summary['transitions']['unsafe_committed'])}/{_fmt(summary['transitions']['committed'])}",
                    _latex(elapsed_label),
                    engine_counts,
                )
            )
            + r" \\"
        )
    return (
        rf"""\begin{{table*}}[t]
\caption{{{caption}}}
\label{{tab:runtime-comparison-aggregate}}
\centering\footnotesize
\setlength{{\tabcolsep}}{{4pt}}
\renewcommand{{\arraystretch}}{{1.20}}
\begin{{tabularx}}{{\textwidth}}{{@{{}}l l r r r r l r@{{}}}}
\toprule
{headers}
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabularx}}
\par\vspace{{3pt}}\noindent\parbox{{0.98\textwidth}}{{\footnotesize {note}}}
\end{{table*}}
""".strip()
        + "\n"
    )


def _svg_cell(value: Any) -> str:
    return escape(_fmt(value))


def render_comparison_svg(data: Mapping[str, Any]) -> str:
    """Render an editable, full-width eight-row comparison matrix SVG."""

    rows = data["rows"]
    width, height = 1800, 940
    cols = (
        (45, "Row", 100),
        (145, "Requested selector", 200),
        (345, "Representation / repeat", 245),
        (590, "Status", 210),
        (800, "Goal", 140),
        (940, "Observed host calls", 140),
        (1080, "Elapsed (s)", 160),
        (1240, "Safety / replay", 525),
    )
    header_lines = {
        "Requested selector": ("Requested", "selector"),
        "Representation / repeat": ("Representation", "/ repeat"),
        "Observed host calls": ("Host", "calls"),
        "Elapsed (s)": ("Elapsed", "(s)"),
        "Safety / replay": ("Safety", "R record-link / E engine"),
    }
    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="svg-title svg-desc">',
        '<title id="svg-title">Fixed-game native runtime comparison</title>',
        '<desc id="svg-desc">Eight assigned rows for one authored quest, showing requested selector, representation and repeat, status, goal, observed host calls, elapsed time, safety, semantic replay, and fresh-engine disposition. Fresh-engine labels are VALID, INVALID, NOT_RUN, or NOT_OBSERVED; NR means not reported; color is supplementary to explicit labels.</desc>',
        "<style>text{font-family:Helvetica,Arial,sans-serif;fill:#202124}.title{font-size:36px;font-weight:700}.subtitle{font-size:28px;fill:#5F6368}.head{font-size:30px;font-weight:700}.cell{font-size:28px}.small{font-size:28px;fill:#5F6368}.status{font-size:28px;font-weight:700}.rule{stroke:#C9CDD1;stroke-width:1}</style>",
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
        '<text x="35" y="38" class="title">FIXED-GAME NATIVE RUNTIME COMPARISON | 8 ASSIGNED ROWS</text>',
        '<text x="35" y="86" class="subtitle">One authored quest; n=2 per selector/representation cell; NR = not reported, not zero. Labels remain explicit; color is supplementary.</text>',
        '<rect x="35" y="105" width="1730" height="100" fill="#EEF0F2" stroke="#C9CDD1"/>',
    ]
    for x, label, _ in cols:
        lines = header_lines.get(label, (label,))
        tspans = "".join(
            f'<tspan x="{x}" dy="{0 if index == 0 else 42}">{escape(line)}</tspan>'
            for index, line in enumerate(lines)
        )
        out.append(
            f'<text x="{x}" y="130" class="head" aria-label="{escape(label)}">{tspans}</text>'
        )
    top = 205
    row_h = 72
    for index, row in enumerate(rows):
        y = top + index * row_h
        fill = "#FFFFFF" if index % 2 == 0 else "#F7F7F5"
        status = row["status"]
        failure_reason = row["failure_reason"] if row["failure_reason"] is not None else "null"
        status_label = (
            "HARNESS"
            if status == "technical_failure"
            else (
                "TIMEOUT"
                if failure_reason == "response_timeout"
                else ("SUCCESS" if status == "success" else "FAIL")
            )
        )
        status_fill = {"success": "#E8F5EF", "failure": "#FFF2DD", "technical_failure": "#EEF0F2"}[
            status
        ]
        goal_label = _fmt(row["goal_reached"])
        goal_fill = {"YES": "#E8F5EF", "NO": "#FFF2DD", "NR": "#EEF0F2"}[goal_label]
        row_key = f"row-{row['row_id']}"
        out += [
            f'<g id="{row_key}" aria-labelledby="{row_key}-title {row_key}-desc">',
            f'<title id="{row_key}-title">row {row["row_id"]} failure_reason={escape(str(failure_reason))}</title>',
            f'<desc id="{row_key}-desc">status={escape(str(status_label))}; goal={escape(goal_label)}; safety={escape(str(row["safety_status"]))}; replay={_svg_cell(row["replay_valid"])}; engine={escape(str(row["engine_reexecution_status"]))}; failure_reason={escape(str(failure_reason))}</desc>',
            f'<rect x="35" y="{y}" width="1730" height="{row_h}" fill="{fill}"/>',
            f'<line x1="35" y1="{y + row_h}" x2="1765" y2="{y + row_h}" class="rule"/>',
            f'<text x="45" y="{y + 44}" class="cell">{row["row_id"]}</text>',
            f'<text x="145" y="{y + 44}" class="cell">{escape(row["requested_selector"])}</text>',
            f'<text x="345" y="{y + 44}" class="cell">{escape(row["representation"])} / r{row["repeat"]}</text>',
            f'<rect class="data-mark status-mark" x="590" y="{y + 15}" width="200" height="36" rx="5" fill="{status_fill}" stroke="#C9CDD1"/>',
            f'<text x="602" y="{y + 41}" class="status">{escape(status_label)}</text>',
            f'<rect class="data-mark goal-mark" x="800" y="{y + 20}" width="32" height="32" rx="4" fill="{goal_fill}" stroke="#C9CDD1"/>',
            f'<text x="842" y="{y + 44}" class="cell">{escape(goal_label)}</text>',
            f'<text x="940" y="{y + 44}" class="cell">{_svg_cell(row["host_invocations_observed"])}</text>',
            f'<text x="1080" y="{y + 44}" class="cell">{_svg_cell(row["elapsed_seconds"])}</text>',
            f'<text x="1240" y="{y + 28}" class="cell">{escape(str(row["safety_status"]))}</text>',
            f'<text x="1240" y="{y + 60}" class="small">R {_svg_cell(row["replay_valid"])} / E {escape(str(row["engine_reexecution_status"]))}</text>',
            "</g>",
        ]
    out += [
        '<text x="35" y="820" class="small">Endpoint outcomes, receipt-derived host calls, and dispatch-to-terminal elapsed time.</text>',
        '<text x="35" y="860" class="small">Typed-intent proposal; deterministic planner/checker and Godot commit retain authority.</text>',
        '<text x="35" y="900" class="small">No efficacy/superiority/noninferiority/player-benefit claim; provider metadata and request counts remain NR.</text>',
        "</svg>",
    ]
    return "\n".join(out) + "\n"


def main(input_path: Path | str = INPUT_PATH) -> dict[str, Path]:
    """Validate the packet and write the four bilingual fragments plus SVG."""

    data = load_public_results(input_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "results_en": OUTPUT_DIR / "runtime_comparison_results_en.tex",
        "results_ko": OUTPUT_DIR / "runtime_comparison_results_ko.tex",
        "tables_en": OUTPUT_DIR / "runtime_comparison_tables_en.tex",
        "tables_ko": OUTPUT_DIR / "runtime_comparison_tables_ko.tex",
        "figure": FIGURES_DIR / "fig_runtime_comparison.svg",
    }
    outputs["results_en"].write_text(render_results_fragment(data), encoding="utf-8", newline="\n")
    outputs["results_ko"].write_text(
        render_results_fragment(data, korean=True), encoding="utf-8", newline="\n"
    )
    outputs["tables_en"].write_text(render_tables_fragment(data), encoding="utf-8", newline="\n")
    outputs["tables_ko"].write_text(
        render_tables_fragment(data, korean=True), encoding="utf-8", newline="\n"
    )
    outputs["figure"].write_text(render_comparison_svg(data), encoding="utf-8", newline="\n")
    print(f"generated runtime comparison publication fragments from {Path(input_path)}")
    return outputs


def _validate_identity_metadata(payload: Mapping[str, Any]) -> None:
    """Close all metadata objects; reject undeclared fields and misleading value coercions."""
    for name, expected in _IDENTITY_FIXED_METADATA.items():
        actual = payload[name]
        _require(
            isinstance(actual, Mapping) and set(actual) == set(expected),
            f"identity {name} fields drifted",
        )
        for field, expected_value in expected.items():
            _require(
                type(actual[field]) is type(expected_value) and actual[field] == expected_value,
                f"identity {name}.{field} value drifted",
            )

    digest_fields = (
        "episode_sha256",
        "operational_closure_sha256",
        "plan_sha256",
        "record_hash",
        "source_manifest_sha256",
        "source_snapshot_manifest_sha256",
    )
    provenance = payload["provenance"]
    _require(
        isinstance(provenance, Mapping)
        and set(provenance)
        == {
            *digest_fields,
            "execution_ended_at",
            "installed_cli_version",
            "source_snapshot_file_count",
            "source_snapshot_visibility",
        },
        "identity provenance fields drifted",
    )
    for field in digest_fields:
        _sha256(provenance[field], f"identity provenance {field}")
    _require(
        provenance["installed_cli_version"] == "0.164.0"
        and provenance["source_snapshot_visibility"] == "local_only"
        and _is_int(provenance["source_snapshot_file_count"])
        and provenance["source_snapshot_file_count"] == 23,
        "identity provenance source or CLI scope drifted",
    )
    ended_at = provenance["execution_ended_at"]
    _require(isinstance(ended_at, str), "identity execution timestamp must be a UTC string")
    try:
        timestamp = datetime.fromisoformat(ended_at)
    except ValueError:
        raise ValueError("identity execution timestamp must be canonical UTC ISO8601") from None
    _require(
        timestamp.tzinfo == UTC and timestamp.isoformat() == ended_at,
        "identity execution timestamp must be canonical UTC ISO8601",
    )
    timing = payload["timing"]
    _require(
        isinstance(timing, Mapping)
        and set(timing)
        == {
            "preparation_seconds",
            "episode_elapsed_seconds",
            "native_process_seconds",
            "orchestration_seconds",
            "successful_completion_seconds",
            "pure_inference_latency_claimed",
        },
        "identity timing fields drifted",
    )


def validate_identity_results(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Validate this stopped cohort without turning absent identity into model evidence."""
    fields = {
        "schema_version",
        "study_id",
        "status",
        "scope",
        "counters",
        "rows",
        "failure",
        "timing",
        "unknowns",
        "provenance",
        "prior_cohort",
        "unsupported_request",
        "diagnosis",
        "claims",
    }
    _require(
        isinstance(payload, Mapping) and set(payload) == fields, "identity packet fields drifted"
    )
    _require(
        payload["schema_version"] == "codex-native-identity-public-results/1",
        "identity schema drifted",
    )
    _require(
        payload["study_id"] == "runtime-model-swap-codex-identity-20261026-v1",
        "identity study drifted",
    )
    _require(payload["status"] == "STOPPED_IDENTITY_UNVERIFIED", "identity disposition drifted")
    _validate_identity_metadata(payload)
    expected_scope = {
        "quest_id": QUEST_ID,
        "seed": SEED,
        "requested_selectors": list(IDENTITY_SELECTORS),
        "representations": list(REPRESENTATIONS),
        "repeats": list(REPEATS),
        "effort": "medium",
        "serial_concurrency": 1,
        "episode_wall_seconds": 180,
        "response_seconds": 60,
        "actual_native_dispatch_cap_per_episode": 12,
        "logical_repair_budget_per_decision": 2,
    }
    scope = payload["scope"]
    _require(scope == expected_scope, "identity frozen scope drifted")
    for field in (
        "seed",
        "serial_concurrency",
        "episode_wall_seconds",
        "response_seconds",
        "actual_native_dispatch_cap_per_episode",
        "logical_repair_budget_per_decision",
    ):
        _require(_is_int(scope[field]), "identity scope count must be an integer")
    _require(all(_is_int(value) for value in scope["repeats"]), "identity repeats must be integers")
    expected_ids = tuple(
        f"{QUEST_ID}:{selector}:{representation}:repeat-{repeat}"
        for selector in IDENTITY_SELECTORS
        for representation in REPRESENTATIONS
        for repeat in REPEATS
    )
    rows = payload["rows"]
    _require(
        isinstance(rows, list) and len(rows) == len(expected_ids), "identity planned rows missing"
    )
    row_fields = {
        "planned_id",
        "requested_selector",
        "representation",
        "repeat",
        "assigned",
        "executed",
        "identity_qualified",
        "provider_identity",
        "provider_revision",
        "goal_reached",
        "status",
        "native_processes",
        "host_invocations",
        "blocked_repair_requests",
    }
    for index, (row, planned_id) in enumerate(zip(rows, expected_ids, strict=True)):
        _require(isinstance(row, Mapping) and set(row) == row_fields, "identity row fields drifted")
        _require(row["planned_id"] == planned_id, "identity planned row order drifted")
        _, selector, representation, repeat = _parse_planned_id(planned_id)
        _require(
            row["requested_selector"] == selector
            and row["representation"] == representation
            and row["repeat"] == repeat
            and _is_int(row["repeat"]),
            "identity row binding drifted",
        )
        for field in (
            "assigned",
            "executed",
            "native_processes",
            "host_invocations",
            "blocked_repair_requests",
        ):
            _require(
                _is_int(row[field]) and row[field] >= 0, "identity row count must be an integer"
            )
        assigned = int(index == 0)
        _require(
            row["assigned"] == assigned
            and row["executed"] == assigned
            and row["native_processes"] == assigned,
            "identity attempt disposition drifted",
        )
        _require(
            row["host_invocations"] == 3 * assigned
            and row["blocked_repair_requests"] == 2 * assigned,
            "identity native and blocked-request counts drifted",
        )
        _require(
            row["identity_qualified"] is False
            and row["provider_identity"] is None
            and row["provider_revision"] is None,
            "unqualified identity cannot be promoted",
        )
        expected_goal = False if assigned else None
        _require(row["goal_reached"] is expected_goal, "unobserved identity goal cannot be imputed")
        _require(
            row["status"] == ("IDENTITY_UNVERIFIED" if assigned else "NOT_RUN"),
            "identity row status drifted",
        )
    counters = payload["counters"]
    expected_counters = {
        "planned": len(rows),
        "assigned": sum(row["assigned"] for row in rows),
        "executed": sum(row["executed"] for row in rows),
        "identity_qualified": sum(row["identity_qualified"] for row in rows),
        "unattempted": sum(row["assigned"] == 0 for row in rows),
        "system_goal_successes": 0,
        "native_processes": sum(row["native_processes"] for row in rows),
        "host_invocations": sum(row["host_invocations"] for row in rows),
        "blocked_repair_requests": sum(row["blocked_repair_requests"] for row in rows),
        "committed_transitions": 0,
        "unsafe_committed_transitions": 0,
    }
    _require(
        isinstance(counters, Mapping)
        and counters == expected_counters
        and all(_is_int(value) for value in counters.values()),
        "identity counters do not reconcile",
    )
    unknowns = payload["unknowns"]
    _require(
        isinstance(unknowns, Mapping)
        and set(unknowns)
        == {
            "provider_identity",
            "provider_revision",
            "effective_effort",
            "provider_request_count",
            "provider_cost_usd",
            "actual_credit_consumption",
            "actual_cash_charge",
        }
        and all(value is None for value in unknowns.values()),
        "identity unknowns cannot be invented",
    )
    for field in (
        "preparation_seconds",
        "episode_elapsed_seconds",
        "native_process_seconds",
        "orchestration_seconds",
    ):
        value = payload["timing"][field]
        _optional_nonnegative_number(value, field)
        _require(value is not None and value > 0, "observed identity timing must be positive")
    _require(
        payload["timing"]["successful_completion_seconds"] is None
        and payload["timing"]["pure_inference_latency_claimed"] is False,
        "failed identity timing is not successful completion or pure inference",
    )
    return payload


def load_identity_results(path: Path | str = IDENTITY_RESULTS_PATH) -> Mapping[str, Any]:
    """Read only exact sanitized bytes; preserve the separate original pilot."""
    raw = Path(path).read_bytes()
    _require(
        hashlib.sha256(raw).hexdigest() == IDENTITY_RESULTS_SHA256,
        "identity results digest mismatch",
    )
    _require(
        hashlib.sha256(RESULTS_PATH.read_bytes()).hexdigest() == PUBLIC_RESULTS_SHA256,
        "original pilot results changed",
    )
    return validate_identity_results(json.loads(raw))


def render_identity_fragment(data: Mapping[str, Any], korean: bool = False) -> str:
    """Render an admission failure report, not a benchmark with zero-filled model scores."""
    data = validate_identity_results(data)
    counts = data["counters"]
    if korean:
        paragraphs = [
            (
                r"\textbf{신원 admission 중단: not a model comparison.} "
                f"별도 확장은 {counts['planned']}개 계획, {counts['assigned']}개 배정, "
                f"{counts['native_processes']}회 native 프로세스 실행, {counts['identity_qualified']}개 신원 검증, "
                f"{counts['unattempted']}개 미실행이다. "
                r"첫 요청 \texttt{gpt-6-luna}/\texttt{general\_rule}의 CLI turn은 끝났지만 "
                r"provider 모델 신원 증거가 없어 응답을 수용하지 않고 나머지 실행을 중단했다."
            ),
            (
                r"요청 selector와 catalog 노출은 실제 응답 신원이 아니다. "
                r"\texttt{openai-model}의 부재 또는 유효 문자열로 전달되지 않은 경우를 현재 증거로 구분하지 못한다. "
                r"이는 관측된 모델 불일치나 모델 능력 실패가 아니다. "
                r"\texttt{gpt-6-terra}는 고정 catalog에 없어서 배정하거나 다른 모델로 대체하지 않았다."
            ),
            (
                r"감사 구분: \texttt{record hash valid=true}; \texttt{engineering record accepted=false}. "
                r"원래 중단 label \texttt{episode\_record\_integrity\_invalid}는 보존한다. "
                r"해시 재계산은 일치하지만 compound 검증 함수가 engineering/safety PASS도 요구하므로 "
                r"이 label을 바이트 손상으로 해석하지 않는다. 커밋은 0개, safety는 "
                r"\texttt{NO\_COMMIT\_OBSERVED}, 새 엔진 재생은 \texttt{NOT\_RUN}이며 안전 통과가 아니다."
            ),
            (
                r"차단된 repair 요청 2회는 native 재실행이 아니다. 원래 8개 pilot은 바이트 불변으로 별도 보존하며 "
                r"새 분모와 합산하지 않는다. Provider 신원/revision/유효 effort/요청 수/비용/실제 credit 및 현금 청구는 "
                r"\texttt{unknown}이다. 계정 일치와 자동 충전 OFF를 전후 관측했고 설정 변경이나 구매는 하지 않았지만 "
                r"0원 또는 credit 무사용의 증명은 아니다. 검증된 새 모델 비교, 온톨로지 효과, 확인적 A/C 근거는 없다."
            ),
        ]
        caption = "신원 검증 중단 확장의 10개 셀. 계획과 실제 배정·신원 검증·미실행을 분리하며 모델 성능 표가 아니다."
        header = r"요청 selector & 표현 & 계획 & 배정 & 신원 검증 & 미실행 \\"
        total_label = "합계"
    else:
        paragraphs = [
            (
                r"\textbf{Identity-admission stop: not a model comparison.} "
                f"The separate extension has {counts['planned']} planned rows, {counts['assigned']} assigned row, "
                f"{counts['native_processes']} native process, {counts['identity_qualified']} identity-qualified rows "
                f"and {counts['unattempted']} unattempted rows. "
                r"The first requested \texttt{gpt-6-luna}/\texttt{general\_rule} CLI turn completed, "
                r"but its response lacked provider model-identity evidence; it was not accepted and the batch stopped."
            ),
            (
                r"A requested selector or catalog advertisement is not a served identity. The evidence cannot distinguish "
                r"an absent \texttt{openai-model} header from one not delivered as a valid string. "
                r"This is not an observed model mismatch or model-incapability result. "
                r"\texttt{gpt-6-terra} was not advertised by the pinned catalog, was not assigned and was not substituted."
            ),
            (
                r"Audit distinction: \texttt{record hash valid=true}; \texttt{engineering record accepted=false}. "
                r"The original bootstrap label \texttt{episode\_record\_integrity\_invalid} is retained. "
                r"The recomputed hash matches; the compound predicate also requires engineering/safety PASS, "
                r"so this label is not evidence of corrupted bytes. There were 0 commits, safety is "
                r"\texttt{NO\_COMMIT\_OBSERVED}, and fresh-engine replay is \texttt{NOT\_RUN}, not a safety pass."
            ),
            (
                r"Two blocked repair requests were not native reruns. The original eight-row pilot remains byte-identical "
                r"and unpooled. Provider identity, revision, effective effort, request count, cost, actual credit use "
                r"and cash charge remain \texttt{unknown}. Matching accounts and automatic reload OFF were observed "
                r"before and after, without a setting change or purchase; these are not zero-cost or zero-credit attestations. "
                r"No verified new model comparison, ontology effect or confirmatory A/C evidence follows."
            ),
        ]
        caption = "Ten identity-admission cells distinguish plans, assignments, qualified identity and unattempted rows; not model performance."
        header = (
            r"Requested selector & Representation & Planned & Assigned & ID-qualified & Not run \\"
        )
        total_label = "Total"
    timing = data["timing"]
    timing_text = (
        f"Preparation {timing['preparation_seconds']:.3f} s; episode elapsed "
        f"{timing['episode_elapsed_seconds']:.3f} s; native process {timing['native_process_seconds']:.3f} s; "
        f"orchestration {timing['orchestration_seconds']:.3f} s. "
        + (
            "실패 시도의 서로 다른 시간 경계이며 순수 추론 지연이나 성공 시간이 아니다."
            if korean
            else "These are distinct failed-attempt boundaries, not pure inference latency or time to success."
        )
    )
    paragraphs.append(timing_text)
    out = [
        "\n\n".join(paragraphs),
        r"\setcounter{table}{14}",
        r"\begin{table}[!ht]",
        r"\centering",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.20}",
        f"\\caption{{{caption}}}",
        r"\label{tab:runtime-identity-admission}",
        r"\begin{tabular}{llrrrr}",
        r"\toprule",
        header,
        r"\midrule",
    ]
    for selector in IDENTITY_SELECTORS:
        for representation in REPRESENTATIONS:
            planned = assigned = qualified = not_run = 0
            for row in data["rows"]:
                if (
                    row["requested_selector"] == selector
                    and row["representation"] == representation
                ):
                    planned += 1
                    assigned += row["assigned"]
                    qualified += row["identity_qualified"]
                    not_run += row["assigned"] == 0
            out.append(
                f"\\texttt{{{_latex(selector)}}} & \\texttt{{{_latex(representation)}}} & "
                f"{planned} & {assigned} & {qualified} & {not_run} " + r"\\"
            )
    out.extend(
        [
            r"\midrule",
            f"{total_label} & --- & {counts['planned']} & {counts['assigned']} & "
            f"{counts['identity_qualified']} & {counts['unattempted']} " + r"\\",
            r"\bottomrule",
            r"\end{tabular}",
            r"\end{table}",
        ]
    )
    return "\n".join(out) + "\n"


def write_identity_fragments(input_path: Path | str = IDENTITY_RESULTS_PATH) -> tuple[Path, Path]:
    """Write only the two new fragments; never rewrite the original eight outcomes."""
    data = load_identity_results(input_path)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    paths = (
        OUTPUT_DIR / "runtime_identity_extension_en.tex",
        OUTPUT_DIR / "runtime_identity_extension_ko.tex",
    )
    for path, korean in zip(paths, (False, True), strict=True):
        path.write_text(
            render_identity_fragment(data, korean=korean), encoding="utf-8", newline="\n"
        )
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--input", type=Path, default=INPUT_PATH, help="explicit original public results JSON path"
    )
    mode.add_argument(
        "--identity-extension",
        action="store_true",
        help="render the separate stopped identity-admission cohort",
    )
    args = parser.parse_args()
    if args.identity_extension:
        write_identity_fragments()
    else:
        main(args.input)
