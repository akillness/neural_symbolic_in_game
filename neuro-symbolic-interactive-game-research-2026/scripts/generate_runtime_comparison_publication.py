#!/usr/bin/env python3
"""Render the fixed-game native runtime comparison from public-safe results.

The renderer is intentionally strict: it accepts only the frozen eight-row public
packet, derives every aggregate from row observations, and emits no output when
the packet is absent or invalid.  It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections.abc import Iterable, Mapping
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
            "요청 selector & 표현 & 목표/배정 & 관측 실행 & Host 호출 & Unsafe/Commit & Elapsed 중앙값(n) & Fresh engine"
            + r" \\"
        )
        note = f"Fresh engine은 {engine_order} 순서의 건수이다. NR은 미보고이지 0이 아니다. 전체 계수와 semantic replay의 구분은 본문에 보고한다."
    else:
        caption = "Fixed-game native runtime comparison (n=2 per cell). All eight assignments, including the harness failure and timeouts, remain in denominators."
        headers = (
            "Requested selector & Form & Goal/assigned & Observed exec. & Host calls & Unsafe/committed & Elapsed median (n) & Fresh engine"
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=INPUT_PATH, help="explicit public results JSON path"
    )
    main(parser.parse_args().input)
