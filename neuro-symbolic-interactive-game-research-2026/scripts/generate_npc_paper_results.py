#!/usr/bin/env python3
"""Generate additive bilingual NPC evidence fragments and an editable SVG figure.

This generator consumes only the new NPC-GOAL-RECOVERY packet. Legacy E1/E2/E3/ENG1
fragments are deliberately not read or rewritten here.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "research/academic-pipeline/npc-goal-recovery/verified-run-003"
CONFIG = ROOT / "configs/npc-goal-recovery.json"
GAME_CONFIG = ROOT / "game-track/godot/project.godot"
SCHEMA = ROOT / "game-track/schemas/npc-goal-recovery.schema.json"
OUT = ROOT / "paper/latex/generated"
FIGURES = ROOT / "paper/latex/figures"
PROJECT_CONFIG_SHA256 = "2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd"
NPC_CONFIG_SHA256 = "d63f5679f360d3fd8d1a424422f5cae4a7096ba46441f746cdd97de56044e098"
ARMS = ("P", "R", "O")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: JSONL row is not an object")
            rows.append(value)
    return rows


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _portable_validation_report(report: dict[str, Any]) -> dict[str, Any]:
    """Copy a validation report and make an exact packet path portable."""
    portable = dict(report)
    recorded_dir = portable.get("packet_dir")
    if not isinstance(recorded_dir, str):
        return portable
    recorded_path = Path(recorded_dir)
    if not recorded_path.is_absolute():
        recorded_path = ROOT / recorded_path
    if recorded_path.resolve() == PACKET.resolve():
        portable["packet_dir"] = PACKET.relative_to(ROOT).as_posix()
    return portable


def _load_packet() -> dict[str, Any]:
    _require(PACKET.is_dir(), f"missing NPC packet: {PACKET}")
    from validate_npc_goal_evidence import validate_packet

    validation_reports: dict[str, Any] = {}
    for packet_id in ("NPC-ENG1", "NPC-SCR1"):
        report, errors = validate_packet(packet_id, ROOT, packet_dir=PACKET)
        _require(not errors and report.get("valid") is True, f"{packet_id}: " + "; ".join(errors))
        validation_reports[packet_id] = _portable_validation_report(report)
    config = _read_json(CONFIG)
    _require(_sha(GAME_CONFIG) == PROJECT_CONFIG_SHA256, "NPC game config SHA file drift")
    _require(_sha(CONFIG) == NPC_CONFIG_SHA256, "NPC protocol config SHA file drift")
    _require(
        config.get("goal", {}).get("id") == "harbor-signal-restored-authorized-tide-lead-v1",
        "NPC goal identity drift",
    )
    success = str(config.get("goal", {}).get("success", ""))
    for predicate in ("signal_lens_installed", "lighthouse_hint_authorized", "tide_marks_hint"):
        _require(predicate in success, f"NPC final predicate omits {predicate}")
    _require(
        config.get("evaluation", {}).get("independent_source_fraction") == 0,
        "NPC O independence drift",
    )
    _require(
        config.get("evaluation", {}).get("utterance_source_kind") == "same_model_family_auxiliary",
        "NPC O source-kind drift",
    )
    aggregate = _read_json(PACKET / "aggregate.json")
    manifest = _read_json(PACKET / "screening-assignment-manifest.json")
    engineering = _rows(PACKET / "engineering-results.jsonl")
    screening = _rows(PACKET / "screening-results.jsonl")
    replay = _read_json(PACKET / "replay-results.json")
    receipts = _read_json(PACKET / "sha256-manifest.json")
    _require(
        aggregate.get("schema_version") == "npc-goal-recovery/evidence-1",
        "NPC aggregate schema drift",
    )
    _require(aggregate.get("packet_id") == "NPC-SCR1", "NPC packet identity drift")
    _require(
        aggregate.get("source_project_config_sha256") == PROJECT_CONFIG_SHA256,
        "NPC project config SHA drift",
    )
    _require(
        aggregate.get("npc_protocol_config_sha256") == NPC_CONFIG_SHA256,
        "NPC protocol config SHA drift",
    )
    _require(aggregate.get("source_schema_sha256") == _sha(SCHEMA), "NPC schema SHA drift")
    _require(len(engineering) == 16, "NPC-ENG1 JSONL cardinality drift")
    _require(len(screening) == 72, "NPC-SCR1 JSONL cardinality drift")
    _require(aggregate.get("run_mode") == "publish", "NPC preflight is not publishable")
    p_rows = [row for row in screening if row.get("arm") == "P"]
    _require(len(p_rows) == 24, "NPC actual P denominator drift")
    model_rows: list[dict[str, Any]] = []
    for index, row in enumerate(p_rows, start=1):
        model = row.get("model")
        _require(
            isinstance(model, dict),
            f"NPC P model metadata missing/malformed at row {index}",
        )
        _require(
            "requested" in model and "returned" in model,
            f"NPC P model metadata fields missing at row {index}",
        )
        if "available" in model:
            _require(
                isinstance(model["available"], bool),
                f"NPC P model availability malformed at row {index}",
            )
        for field in ("requested", "returned"):
            value = model[field]
            _require(
                value is None
                or (isinstance(value, str) and bool(value.strip()) and value == value.strip()),
                f"NPC P model {field} malformed at row {index}",
            )
        model_rows.append({"requested": model["requested"], "returned": model["returned"]})
    requested_models = {model["requested"] for model in model_rows}
    returned_models = {model["returned"] for model in model_rows}
    returned_named_models = {model for model in returned_models if model is not None}
    _require(len(requested_models) == 1, "NPC P requested model cohort is mixed")
    _require(
        len(returned_named_models) <= 1,
        "NPC P returned model cohort has multiple named revisions",
    )
    model_metadata = {
        "requested": next(iter(requested_models)),
        "returned": next(iter(returned_named_models), None),
        "returned_unknown_count": sum(model["returned"] is None for model in model_rows),
        "cohort_size": len(model_rows),
    }
    stale_control_counts: Counter[str] = Counter()
    stale_case_controls: dict[str, set[str]] = {}
    stale_arm_counts: Counter[str] = Counter()
    stale_verified_rows = 0
    assigned_failure_rows = 0
    for row in screening:
        if row.get("status") != "assigned_failure":
            continue
        assigned_failure_rows += 1
        failure_codes = {
            failure.get("code") for failure in row.get("failure", []) if isinstance(failure, dict)
        }
        acks = row.get("acks")
        ack_body = acks[0].get("body") if isinstance(acks, list) and acks else None
        trace = row.get("engine", {}).get("experiment", {}).get("trace", {})
        gates = trace.get("expected_negative_gates", []) if isinstance(trace, dict) else []
        controls = {
            gate.get("control")
            for gate in gates
            if isinstance(gate, dict)
            and gate.get("control") in {"stale_revision", "stale_policy"}
            and gate.get("expected_status") == "STALE"
            and gate.get("observed_status") == "STALE"
            and gate.get("state_ref_before") == gate.get("state_ref_after")
            and gate.get("passed") is True
        }
        case_id = row.get("case_id")
        fixture_ref = row.get("fixture_ref")
        verified_stale = (
            "result_ack_not_accepted" in failure_codes
            and isinstance(ack_body, dict)
            and ack_body.get("status") == "REJECTED"
            and ack_body.get("error") == "stale_result"
            and row.get("regime") == "stale"
            and isinstance(case_id, str)
            and isinstance(fixture_ref, str)
            and isinstance(trace, dict)
            and trace.get("status") == "STALE"
            and fixture_ref.endswith(f"#{case_id}")
            and bool(controls)
        )
        if verified_stale:
            stale_verified_rows += 1
            stale_arm_counts[str(row.get("arm"))] += 1
            stale_control_counts.update(controls)
            stale_case_controls.setdefault(case_id, set()).update(controls)
    stale_disclosure = {
        "verified_rows": stale_verified_rows,
        "assigned_failure_rows": assigned_failure_rows,
        "by_arm": dict(stale_arm_counts),
        "by_control": dict(stale_control_counts),
        "by_case": {case_id: sorted(controls) for case_id, controls in stale_case_controls.items()},
        "unclassified_rows": assigned_failure_rows - stale_verified_rows,
    }
    for row in p_rows:
        attempts = row.get("cli_exec_attempts")
        _require(
            isinstance(attempts, list) and len(attempts) == 1,
            "NPC P requires one observed CLI exec attempt per assignment",
        )
        attempt = attempts[0]
        _require(
            isinstance(attempt, dict)
            and attempt.get("schema_version") == "codex-exec-attempt/1"
            and attempt.get("operation") == "exec"
            and attempt.get("runner_injected") is False
            and attempt.get("tool_policy_enforced") is True
            and attempt.get("request_id") == row.get("request", {}).get("request_id")
            and isinstance(attempt.get("disabled_feature_count"), int)
            and not isinstance(attempt.get("disabled_feature_count"), bool)
            and attempt["disabled_feature_count"] > 0,
            "NPC P CLI attempt provenance mismatch",
        )
        _require(row.get("model_calls") == len(attempts), "NPC P observed attempt counter mismatch")
        _require(
            not any(failure.get("code") == "model_skipped" for failure in row.get("failure", [])),
            "NPC skipped P is not publishable",
        )
    assignments = manifest.get("assignments")
    _require(
        isinstance(assignments, list) and len(assignments) == 72,
        "NPC assignment manifest cardinality drift",
    )
    _require(isinstance(aggregate.get("arms"), dict), "NPC aggregate arms missing")
    for arm in ARMS:
        summary = aggregate["arms"].get(arm)
        _require(isinstance(summary, dict), f"NPC arm summary missing: {arm}")
        _require(summary.get("n") == 24, f"NPC arm denominator drift: {arm}")
        _require(
            summary.get("source_independent_n") == 0, f"NPC source-independent count drift: {arm}"
        )
    usage = aggregate.get("usage", {})
    _require(
        usage.get("token_accounting_available") is False, "NPC token availability boundary drift"
    )
    _require(
        usage.get("input_tokens") is None and usage.get("output_tokens") is None,
        "NPC token NA drift",
    )
    _require(usage.get("cost") is None, "NPC cost NA drift")
    _require(
        usage.get("model_revision_available") is False, "NPC model revision availability drift"
    )
    _require(usage.get("model_revision") is None, "NPC model revision NA drift")
    claims = aggregate.get("claims", {})
    for key, expected in {
        "independent_labels": False,
        "efficacy_pending": True,
        "superiority": False,
        "generalization": False,
        "human_benefit": False,
        "c_result_promotion": False,
    }.items():
        _require(claims.get(key) is expected, f"NPC claim boundary drift: {key}")
    _require(isinstance(replay, dict), "NPC replay result must be an object")
    _require(replay.get("model_calls") == 0, "NPC replay unexpectedly invoked a model")
    return {
        "aggregate": aggregate,
        "manifest": manifest,
        "engineering": engineering,
        "screening": screening,
        "replay": replay,
        "model_metadata": model_metadata,
        "stale_disclosure": stale_disclosure,
        "validation_reports": validation_reports,
        "receipts": receipts,
    }


def _latex(value: Any) -> str:
    text = str(value)
    for old, new in (
        ("\\", r"\textbackslash{}"),
        ("_", r"\_"),
        ("%", r"\%"),
        ("&", r"\&"),
        ("#", r"\#"),
    ):
        text = text.replace(old, new)
    return text


def _status_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    values: Counter[str] = Counter()
    for row in rows:
        status = row.get("status") or row.get("result", {}).get("status") or row.get("outcome")
        values[str(status or "UNSPECIFIED")] += 1
    return values


def _failure_counts(summary: dict[str, Any]) -> Counter[str]:
    values = summary.get("failures_by_code", {})
    _require(isinstance(values, dict), "NPC failures_by_code must be an object")
    return Counter({str(key): int(value) for key, value in values.items()})


def _results(packet: dict[str, Any], korean: bool) -> str:
    aggregate = packet["aggregate"]
    eng_n = len(packet["engineering"])
    eng_status = ", ".join(
        f"{_latex(key)}={value}"
        for key, value in sorted(_status_counts(packet["engineering"]).items())
    )
    model_metadata = packet["model_metadata"]
    requested_model = model_metadata["requested"]
    returned_revision = model_metadata["returned"]
    unknown_returned_count = int(model_metadata.get("returned_unknown_count", 0))
    cohort_size = int(model_metadata.get("cohort_size", 24))
    unknown_label = "알 수 없음 (null)" if korean else "unknown (null)"
    requested_label = unknown_label if requested_model is None else _latex(requested_model)
    returned_label = unknown_label if returned_revision is None else _latex(returned_revision)
    if returned_revision is not None and unknown_returned_count:
        partial_word = "부분" if korean else "partial"
        unknown_word = "알 수 없음" if korean else "unknown"
        returned_label = (
            f"{returned_label} ({partial_word}; {unknown_word} "
            f"{unknown_returned_count}/{cohort_size})"
        )
    scr_status = ", ".join(
        f"{_latex(key)}={value}"
        for key, value in sorted(_status_counts(packet["screening"]).items())
    )
    p_rows = [row for row in packet["screening"] if row["arm"] == "P"]
    p_attempts = sum(row["model_calls"] for row in p_rows)
    p_decisions = sum(isinstance(row.get("decision"), dict) for row in p_rows)
    p_failures = sum(row["status"] == "assigned_failure" for row in p_rows)
    stale_disclosure = packet["stale_disclosure"]
    stale_arm_label = ", ".join(
        f"{arm}={int(stale_disclosure.get('by_arm', {}).get(arm, 0))}" for arm in ARMS
    )
    stale_case_label = (
        ", ".join(
            f"{_latex(case_id)} ({', '.join(_latex(control) for control in controls)})"
            for case_id, controls in sorted(stale_disclosure.get("by_case", {}).items())
        )
        or "none"
    )
    stale_verified_rows = int(stale_disclosure.get("verified_rows", 0))
    unclassified_failure_rows = int(stale_disclosure.get("unclassified_rows", 0))
    if korean:
        stale_failure_disclosure = (
            f"검증된 사전 작성 stale-control ACK 거부는 arm별 {stale_arm_label}건"
            f"({stale_case_label})이며, {stale_verified_rows}개 인스턴스 모두 "
            f"대응하는 음성 대조 gate가 모두 통과했다. 따라서 이 행들은 assigned failure로 "
            f"분모에 남기되 method-performance 결과로 해석하지 않으며, 기타 assigned failure "
            f"{unclassified_failure_rows}개는 미분류로 남긴다."
        )
    else:
        stale_failure_disclosure = (
            f"Verified pre-authored stale-control ACK rejections are {stale_arm_label} per arm"
            f" ({stale_case_label}); {stale_verified_rows} instances had all "
            f"corresponding negative-control gates passed. These rows remain assigned failures in the "
            f"denominator, not method-performance outcomes; other assigned failures "
            f"({unclassified_failure_rows}) remain unclassified."
        )
    if korean:
        return (
            rf"""
\subsection{{고정 목표 NPC 운영 (NPC-ENG1/NPC-SCR1)}}
Mira의 고정 목표는 항구 신호 복구 후 허가된 조석 단서를 제공하는 것이다. Python은 typed intent와 공개 관측으로 bounded BFS 계획을 계산한다. 획득·설치는 플레이어가, 허가된 \texttt{{reveal\_hint}}는 NPC가 수행한다. Godot은 session/epoch/request/goal/policy/revision/hash를 동기 검사한 뒤 기존 writer를 await 없이 호출한다. 결과와 새 관측이 다음 계획을 결정하므로 단일 후보의 validator-error repair와 구별된다.

NPC-ENG1은 실제 엔진 snapshot에서 시작한 R arm의 결정론적 engineering 사례 {eng_n}개({eng_status})다. NPC-SCR1은 P/R/O 각 24개, 전체 {aggregate["assignment_count"]}개 배정과 실패를 모두 보존한다({scr_status}). P는 인증된 Codex CLI 실행 시도 {p_attempts}회, 반환 decision {p_decisions}개, 배정 실패 {p_failures}개를 기록했다. 이는 원격 과금 호출 횟수가 아니다. 요청 모델: {requested_label}; decision에 기록된 모델 식별자: {returned_label}. 후자는 설정된 selector이며 provider revision이 아니다. provider revision은 사용할 수 없고 null 식별자는 미상으로 남긴다. 전역 설정은 모델 식별 근거가 아니다. R은 작성된 규칙을 사용한다. O는 \texttt{{same\_model\_family\_auxiliary}}로 선언된 protocol auxiliary일 뿐이며 실제 모델 계열 일치는 unverified(검증되지 않음)이다. 독립 원본은 0개이고 O는 oracle이나 semantic gold가 아니다. 표~\ref{{tab:npc-screening}}과 그림~\ref{{fig:npc-screening}}은 bounded protocol-conformance 고정 사례의 기술적 계수이지 회복 효능·우월성·일반화 추정이 아니다. efficacy는 pending이며 토큰·비용은 미측정이다. 읽기 전용 CLI와 격리 작업 디렉터리를 사용했지만 tool-free 추론이나 적대적 기밀성은 검증하지 않았다.
{stale_failure_disclosure}

""".strip()
            + "\n"
        )
    return (
        rf"""
\subsection{{Fixed-Goal NPC Operation (NPC-ENG1/NPC-SCR1)}}
Mira's fixed goal is to deliver the authorized tide lead after harbor-signal restoration. Python computes bounded BFS plans from typed intent and public observations. Acquire/install remain player actions; the NPC may only commit the authorized \texttt{{reveal\_hint}}. Godot synchronously checks session/epoch/request/goal/policy/revision/hash before calling the existing writer without an await. Results and new observations determine the next plan, unlike single-candidate validator-error repair.

NPC-ENG1 comprises {eng_n} deterministic R-arm engineering cases initialized from actual engine snapshots ({eng_status}). NPC-SCR1 retains all {aggregate["assignment_count"]} assignments and failures, 24 per P/R/O arm ({scr_status}). P records {p_attempts} authenticated Codex CLI exec attempts, {p_decisions} returned decisions, and {p_failures} assigned failures; these are not remote billing-call counts. Requested model: {requested_label}; recorded decision-model identifier: {returned_label}. The latter propagates the configured selector, not a provider revision; the provider revision is unavailable. Null identifiers remain unknown; global defaults are not evidence. R uses authored rules. O is a protocol-declared auxiliary under \texttt{{same\_model\_family\_auxiliary}}. Actual model-family matching is unverified. No source is independent; O is neither an oracle nor semantic gold. Table~\ref{{tab:npc-screening}} and Fig.~\ref{{fig:npc-screening}} report bounded protocol-conformance fixed-case counts, not recovery-efficacy, superiority, or generalization estimates. Efficacy remains pending; tokens and cost are unmeasured. A read-only CLI and isolated working directory were used, but tool-free inference and adversarial confidentiality were not established.
{stale_failure_disclosure}
""".strip()
        + "\n"
    )


def _tables(packet: dict[str, Any], korean: bool) -> str:
    aggregate = packet["aggregate"]
    caption = (
        "NPC-SCR1 고정 사례 실행 계수. NPC-ENG1의 16개 사례와 분리하며 모든 실패를 분모에 보존한다."
        if korean
        else "NPC-SCR1 fixed-case execution counts, separate from the 16 NPC-ENG1 cases; all assigned failures remain in the denominator."
    )
    headers = (
        r"Arm & 배정 & 완료/실패 & 목표 도달 & 회복 E/U \\"
        if korean
        else r"Arm & Assigned & Complete/fail & Goal reached & Recovery E/U \\"
    )
    rows = []
    for arm in ARMS:
        summary = aggregate["arms"][arm]
        observed = []
        for key in ("goal_reached_n", "recovery_eligible_n", "recovery_unreachable_n"):
            value = summary.get(key)
            _require(
                value is None or (type(value) is int and 0 <= value <= summary["n"]),
                f"invalid observed count: {arm}/{key}",
            )
            observed.append(str(value) if value is not None else "NA")
        goal, eligible, unreachable = observed
        rows.append(
            f"{arm} & {summary['n']} & {summary['completed_n']}/{summary['assigned_failure_n']} & {goal} & {eligible}/{unreachable} "
            + r"\\"
        )
    note = (
        "E: 회복 평가 가능, U: 도달 불가; NA: 미측정. 목표 관측 계수는 회복률이 아니다. Replay 적합성은 실패 행을 완료로 바꾸지 않는다. O의 독립 원본은 0개다."
        if korean
        else "E: recovery eligible; U: unreachable; NA: unmeasured. Observed goal counts are not recovery rates. Valid replay does not turn a failed assignment into a completed one. O has zero independent sources."
    )
    return (
        rf"""
\begin{{table}}[t]
\caption{{{caption}}}
\label{{tab:npc-screening}}
\centering\scriptsize
\setlength{{\tabcolsep}}{{2.8pt}}
\renewcommand{{\arraystretch}}{{1.12}}
\begin{{tabularx}}{{\columnwidth}}{{@{{}}l r >{{\centering\arraybackslash}}X >{{\centering\arraybackslash}}X >{{\centering\arraybackslash}}X@{{}}}}
\toprule
{headers}
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabularx}}
\vspace{{1pt}}\parbox{{0.97\columnwidth}}{{\scriptsize {note}}}
\end{{table}}
""".strip()
        + "\n"
    )


def _svg(packet: dict[str, Any]) -> str:
    arms = packet["aggregate"]["arms"]
    # Keep the source aspect stable through the repository's rsvg-convert → EPS →
    # ps2pdf pipeline: 1100×468 SVG pixels become 825×351 PDF points without
    # independent rounding changing the aspect ratio.
    width, height = 1100, 468
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="svg-title svg-desc">',
        '<title id="svg-title">NPC-SCR1 fixed-case trace outcomes</title>',
        '<desc id="svg-desc">Observed completed traces and retained assigned failures for 24 rows per arm in authored fixed cases, including Codex-backed P. These descriptive counts are not estimates of recovery efficacy. O is a protocol-declared auxiliary; actual model-family matching is unverified.</desc>',
        "<style>text{font-family:Helvetica,Arial,sans-serif;fill:#202124}.title{font-size:32px;font-weight:700}.label{font-size:30px;font-weight:700}.body{font-size:28px}.note{font-size:28px;fill:#5F6368}.connector{fill:none}</style>",
        f'<rect width="{width}" height="{height}" fill="white"/>',
        '<text x="40" y="48" class="title">NPC-SCR1 | FIXED-CASE TRACE OUTCOMES</text>',
        '<text x="40" y="90" class="note">P: Codex intent | R: authored rules | O: protocol auxiliary (family unverified)</text>',
        '<rect x="145" y="115" width="25" height="22" fill="#0072B2"/>',
        '<text x="183" y="135" class="note">Completed trace</text>',
        '<rect x="470" y="115" width="25" height="22" fill="#D55E00"/>',
        '<text x="508" y="135" class="note">Assigned failure (retained)</text>',
    ]
    goal_counts = []
    for index, arm in enumerate(ARMS):
        summary = arms[arm]
        assigned = summary["n"]
        completed = summary["completed_n"]
        failed = summary["assigned_failure_n"]
        _require(type(assigned) is int and assigned == 24, f"invalid assigned count: {arm}")
        _require(type(completed) is int and type(failed) is int, f"unmeasured trace count: {arm}")
        _require(
            completed >= 0 and failed >= 0 and completed + failed == assigned,
            f"incomplete trace accounting: {arm}",
        )
        y = 165 + index * 65
        completed_width = 540 * completed / assigned
        failed_width = 540 * failed / assigned
        parts += [
            f'<text x="70" y="{y + 28}" class="label">{arm}</text>',
            f'<rect class="bar completed" x="145" y="{y}" width="{completed_width:g}" height="34" fill="#0072B2"/>',
            f'<rect class="bar assigned-failure" x="{145 + completed_width:g}" y="{y}" width="{failed_width:g}" height="34" fill="#D55E00"/>',
            f'<line class="connector" x1="685" y1="{y + 17}" x2="705" y2="{y + 17}" stroke="#C9CDD1" stroke-width="2"/>',
            f'<text x="715" y="{y + 28}" class="body">{completed} complete / {failed} failed</text>',
        ]
        reached = summary.get("goal_reached_n")
        goal_counts.append(f"{arm}: {reached}/{assigned}" if type(reached) is int else f"{arm}: NA")
    goal_text = escape("Goal reached, fixed cases only | " + " | ".join(goal_counts))
    parts += [
        f'<text x="40" y="389" class="note">{goal_text}</text>',
        '<text x="40" y="427" class="note">Independent-source rows: 0. No efficacy, superiority, or generalization claim.</text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def main() -> None:
    packet = _load_packet()
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    (OUT / "npc_validation_reports.json").write_text(
        json.dumps(packet["validation_reports"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for language, korean in (("en", False), ("ko", True)):
        (OUT / f"npc_results_{language}.tex").write_text(
            _results(packet, korean), encoding="utf-8", newline="\n"
        )
        (OUT / f"npc_tables_{language}.tex").write_text(
            _tables(packet, korean), encoding="utf-8", newline="\n"
        )
    target = FIGURES / "fig_npc_screening.svg"
    target.write_text(_svg(packet), encoding="utf-8", newline="\n")
    print(
        f"generated NPC paper fragments and {target.relative_to(ROOT)} from {PACKET.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
