#!/usr/bin/env python3
"""Generate bilingual IEEE result prose and compact tables from frozen pilot JSON."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
RESULTS_PATH = ROOT / "research/academic-pipeline/stage-04-pilot/pilot-results.json"
LIVE_ROOT = ROOT / "research/academic-pipeline/rq2-live-pilot"
LIVE_MANIFEST_PATH = LIVE_ROOT / "promotion-manifest.json"
LIVE_CURRENT_CELLS = (
    ("frozen_visible", "frozen-pilot-base/policy_visible/summary.json"),
    ("frozen_blind", "frozen-pilot-base/policy_blind/summary.json"),
    ("frozen_goal_blind", "frozen-pilot-base/goal_directed_blind/summary.json"),
    ("signal_v2_visible", "signal-repair-v2/policy_visible/summary.json"),
    ("signal_v2_blind", "signal-repair-v2/policy_blind/summary.json"),
)
LIVE_DIAGNOSTIC_SUMMARY = "signal-repair/policy_blind/summary.json"
LIVE_DIAGNOSTIC_RESULTS = "signal-repair/policy_blind/results.jsonl"
LIVE_SUPPORTED_CLAIMS = ["C-PILOT-007", "C-PILOT-008"]
LIVE_EXCLUDED_CLAIMS = ["C-RESULT-003"]
LIVE_RECEIPT_CLAIM_BOUNDARY = (
    "Live-proposer screening pilot on a single frozen base state with a tiny seed grid. "
    "Supports C-RESULT-003 only at pilot-only. Not a population effect, not a promoted-model "
    "result, and not statistical evidence."
)
OUT = ROOT / "paper/latex/generated"


def _escape(value: Any) -> str:
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


def _class_counts(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (row["arm_id"], row["repairability"]): row
        for row in data["repair_arms"]["raw_counts_by_class"]
    }


def _fmt_mean(value: Any) -> str:
    return "---" if value is None else f"{value:.1f}"


def _load_live_packet() -> dict[str, Any]:
    manifest = json.loads(LIVE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("pilot_id") != "SL-RQ2-LIVE-001":
        raise ValueError("unexpected live-pilot identity")
    if manifest.get("evidence_tier") != "screening-pilot-only":
        raise ValueError("live packet exceeds the screening-only claim boundary")
    if manifest.get("supported_claim_ids") != LIVE_SUPPORTED_CLAIMS:
        raise ValueError("live-pilot supported claim drift")
    if manifest.get("excluded_claim_ids") != LIVE_EXCLUDED_CLAIMS:
        raise ValueError("live-pilot excluded claim drift")
    if "C-RESULT-003 remains TODO-RESULT" not in manifest.get("claim_boundary", ""):
        raise ValueError("live-pilot current claim boundary drift")

    files = manifest.get("files", {})
    if not files:
        raise ValueError("live-pilot promotion manifest has no files")
    for relative_path, receipt in sorted(files.items()):
        payload = (LIVE_ROOT / relative_path).read_bytes()
        if len(payload) != receipt["bytes"]:
            raise ValueError(f"live-pilot byte count drift: {relative_path}")
        if hashlib.sha256(payload).hexdigest() != receipt["sha256"]:
            raise ValueError(f"live-pilot checksum drift: {relative_path}")

    current: dict[str, dict[str, Any]] = {}
    for key, relative_path in LIVE_CURRENT_CELLS:
        summary = json.loads((LIVE_ROOT / relative_path).read_text(encoding="utf-8"))
        if summary.get("pilot_id") != manifest["pilot_id"]:
            raise ValueError(f"live-pilot id drift: {relative_path}")
        if summary.get("evidence_tier") != "screening-pilot-only":
            raise ValueError(f"live-pilot evidence tier drift: {relative_path}")
        if summary.get("claim_boundary") != LIVE_RECEIPT_CLAIM_BOUNDARY:
            raise ValueError(f"live-pilot receipt boundary drift: {relative_path}")
        if summary.get("repair_budget") != 1:
            raise ValueError(f"live-pilot repair budget drift: {relative_path}")
        if summary.get("matched_candidate_per_seed") is not True:
            raise ValueError(f"live-pilot candidate matching drift: {relative_path}")
        if summary.get("token_accounting_available") is not False:
            raise ValueError(f"live-pilot token-accounting boundary drift: {relative_path}")
        if summary.get("counts", {}).get("seeds") != 5:
            raise ValueError(f"live-pilot seed count drift: {relative_path}")
        if set(summary.get("per_arm", {})) != {"guided_repair", "unchanged_retry"}:
            raise ValueError(f"live-pilot arm set drift: {relative_path}")
        current[key] = summary

    expected_signatures = {
        "frozen_visible": (5, 5, 5, ()),
        "frozen_blind": (5, 5, 5, ()),
        "frozen_goal_blind": (0, 0, 0, ("QUEST_STAGE_REGRESSION",)),
        "signal_v2_visible": (5, 5, 5, ()),
        "signal_v2_blind": (
            0,
            5,
            0,
            (
                "POLICY_EFFECT_OMISSION",
                "POLICY_EFFECT_VIOLATION",
                "POLICY_PRECONDITION_OMISSION",
            ),
        ),
    }
    for key, expected in expected_signatures.items():
        summary = current[key]
        observed = (
            summary["counts"]["initially_valid"],
            summary["per_arm"]["guided_repair"]["commits"],
            summary["per_arm"]["unchanged_retry"]["commits"],
            tuple(summary["observed_initial_error_codes"]),
        )
        if observed != expected:
            raise ValueError(f"live-pilot promoted cell drift: {key}: {observed!r}")

    diagnostic_summary = json.loads(
        (LIVE_ROOT / LIVE_DIAGNOSTIC_SUMMARY).read_text(encoding="utf-8")
    )
    diagnostic_rows = [
        json.loads(line)
        for line in (LIVE_ROOT / LIVE_DIAGNOSTIC_RESULTS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if diagnostic_summary.get("base_state_id") != "live-pilot-signal-repair-v1":
        raise ValueError("superseded diagnostic identity drift")
    if diagnostic_summary.get("claim_boundary") != LIVE_RECEIPT_CLAIM_BOUNDARY:
        raise ValueError("superseded diagnostic receipt boundary drift")
    if len(diagnostic_rows) != 5:
        raise ValueError("superseded diagnostic row-count drift")
    for row in diagnostic_rows:
        guided = row["arms"]["guided_repair"]
        if guided["status"] != "fallback":
            raise ValueError("superseded diagnostic unexpectedly committed")
        if guided["final_error_codes"] != ["NPC_KNOWLEDGE_VIOLATION"]:
            raise ValueError("superseded diagnostic residual-error drift")

    return {
        "manifest": manifest,
        "current": current,
        "diagnostic_summary": diagnostic_summary,
        "diagnostic_rows": diagnostic_rows,
    }


def _result_text(data: dict[str, Any], korean: bool) -> str:
    gate = data["gate_conformance"]["raw_counts"]
    boundary = data["boundary_sentinels"]["raw_counts"]
    closed_boundary = data["closed_boundary_regressions"]["raw_counts"]
    integrity = data["integrity_faults"]["raw_counts"]
    integrity_boundary = data["integrity_boundaries"]["raw_counts"]
    adapter = data["adapter_accounting"]["raw_counts"]
    guards = data["accounting_guards"]["raw_counts"]
    by_class = _class_counts(data)
    case_total = sum(
        row["case_count"]
        for row in data["repair_arms"]["raw_counts_by_class"]
        if row["arm_id"] == "guided_repair"
    )
    g_cases = by_class[("guided_repair", "guided_repairable")]["case_count"]
    o_cases = by_class[("guided_repair", "oracle_only")]["case_count"]
    i_cases = by_class[("guided_repair", "irreparable")]["case_count"]
    guided_commits = by_class[("guided_repair", "guided_repairable")]["commit_count"]
    guided_oracle_only = by_class[("guided_repair", "oracle_only")]["commit_count"]
    guided_irreparable = by_class[("guided_repair", "irreparable")]["commit_count"]
    oracle_guided = by_class[("structured_repair", "guided_repairable")]["commit_count"]
    oracle_only = by_class[("structured_repair", "oracle_only")]["commit_count"]
    oracle_irreparable = by_class[("structured_repair", "irreparable")]["commit_count"]
    guided_mean_edit = _fmt_mean(
        by_class[("guided_repair", "guided_repairable")]["mean_commit_edit_field_count"]
    )
    if korean:
        return (
            rf"""
\subsection{{구조 필드 게이트 적합성}}
파일럿 loader는 구현된 validator code를 정확히 한 번씩 고립시키는 fixture 집합과 유효 control 1개만을 허용한다. 따라서 {gate["passed_fixture_count"]}/{gate["fixture_count"]} 일치와 구현된 오류 코드 {gate["implemented_code_count"]}종의 관찰은 측정된 성공률이 아니라 \emph{{하니스의 구성 불변량}}이다. 이 실행이 보여주는 것은 loader가 강제하지 않는 부분, 즉 고립된 음성 fixture {gate["negative_fixture_count"]}개가 각각 다른 코드가 아니라 작성된 기대 코드와 일치했고 비commit 경로가 전체 정준 상태를 유지했다는 관찰이다. 이는 단일 world state에서 저자가 설계한 구조 필드 oracle에 대한 구현 적합성이며 독립 의미 판정의 정확도가 아니다.

\subsection{{설계 픽스처에서의 수리 arm 비교}}
처음부터 유효하지 않은 설계 case {case_total}개는 guided-repairable {g_cases}개, oracle-only {o_cases}개, irreparable {i_cases}개의 동결된 repairability class로 분할된다. Rejection-only와 블라인드 동일 후보 retry는 각각 0/{case_total} commit이었다. 반례 유도 연산자 $\rho$는 guided-repairable case {guided_commits}/{g_cases}를 commit했고, 설계상 oracle-only {guided_oracle_only}/{o_cases}, irreparable {guided_irreparable}/{i_cases}였다. 모든 $\rho$ commit은 candidate field를 평균 {guided_mean_edit}개 수정했으며, 실패한 모든 arm 실행은 정준 상태를 변경 없이 유지했다. 상태를 읽는 참조 callback은 guided-repairable {oracle_guided}/{g_cases}와 oracle-only {oracle_only}/{o_cases}를 commit했고 irreparable은 {oracle_irreparable}/{i_cases}였다. 이 정확한 count는 세 메커니즘을 설계 픽스처 위에서 분리한다. 블라인드 retry는 반례를 commit으로 전환하지 못하고, $\rho$는 오류 payload에 충분한 정보가 담긴 case만 전환하며, oracle은 상태 지식이 필요한 case를 추가로 전환한다. 이는 동결 픽스처에 대한 연산자 적합성이며, 어떤 live model의 수리 품질도 아니다.

\subsection{{무결성, 경계, 배정 회계}}
현재 명세가 검출 가능하다고 지정한 {integrity["fault_count"]}개 fault fixture는 모두 지정된 검사 연산에서 거부됐다({integrity["detected_fault_count"]}/{integrity["fault_count"]}). 이 파일럿은 안정적인 typed detector code까지 대조하지 않으므로 detector layer 귀속을 입증하지 않는다. 별도로, 동일하게 기록된 유효 수리 앞의 무효 선행 후보를 다른 무효 후보로 치환하고 체크섬을 재계산한 알려진 provenance 경계는 예상대로 재생을 통과했다({integrity_boundary["observed_undetected_count"]}/{integrity_boundary["boundary_count"]} 미검출). 따라서 키 없는 체크섬을 재계산할 수 있는 작성자를 방어하지 않으며, 재생은 repair 생성 연산의 출처를 인증하지 않는다. 열린 경계 sentinel 두 건---자연어 disclosure 미추출과 required object의 후보·정책 동시 누락---은 {boundary["encoded_acceptance_count"]}/{boundary["sentinel_count"]}가 의도대로 인코딩상 허용됐고 safety pass는 {boundary["safety_pass_count"]}건이었다. 과거 unknown top-level field 허용 경계는 Stage 8 이후 닫힌 음성 회귀로 재분류되었으며, 완전한 12-field candidate에 unknown key 하나를 추가한 fixture를 proposal·replay parser 모두 구체적으로 거부했다({closed_boundary["passed_regression_count"]}/{closed_boundary["regression_count"]}). 이는 parser rejection parity이지 의미 안전성의 증거가 아니다. Adapter/accounting 7개 배정에서는 commit {adapter["commit_count"]}, 기호 fallback {adapter["fallback_count"]}, adapter failure {adapter["adapter_failure_count"]}였다. 합성 telemetry 필드는 {adapter["provider_latency_observed_count"]}/7 배정에서 채워져 전파됐으며, 이는 측정값이 아니라 회계 필드 전파 확인이다. 배정 guard {guards["detected_guard_count"]}/{guards["guard_count"]}가 중복·누락을 거부했다. 이 수치는 모두 합성 offline fixture의 raw count다.
""".strip()
            + "\n"
        )
    return (
        rf"""
\subsection{{Declared-Field Gate Conformance}}
The pilot loader admits a fixture set only when it isolates every implemented validator code exactly once alongside one valid control, so the {gate["passed_fixture_count"]}/{gate["fixture_count"]} agreement and the observation of all {gate["implemented_code_count"]} implemented error codes are \emph{{construction invariants of the harness}}, not measured success rates. What the run adds is the part the loader does not enforce: each of the {gate["negative_fixture_count"]} isolated negative fixtures showed observed agreement with its authored expected code rather than reaching a different one, and every noncommit path preserved the complete canonical state. This is implementation conformance to an authored structured-field oracle over a single world state, not accuracy against independent semantic labels.

\subsection{{Repair-Arm Comparison on Designed Fixtures}}
The {case_total} initially invalid designed cases are partitioned into frozen repairability classes: {g_cases} guided-repairable, {o_cases} oracle-only, and {i_cases} irreparable. Rejection-only and blind unchanged-candidate retry each committed 0/{case_total}. The counterexample-guided operator $\rho$ committed {guided_commits}/{g_cases} guided-repairable cases and, by design, {guided_oracle_only}/{o_cases} oracle-only and {guided_irreparable}/{i_cases} irreparable cases; every $\rho$ commit edited a mean of {guided_mean_edit} candidate fields, and every failed arm execution left the canonical state unchanged. The state-reading reference callback committed {oracle_guided}/{g_cases} guided-repairable and {oracle_only}/{o_cases} oracle-only cases, with {oracle_irreparable}/{i_cases} irreparable. These exact counts separate the three mechanisms on the designed fixtures: blind retry never converts a counterexample into a commit, $\rho$ converts exactly the cases whose error payload carries sufficient information, and the oracle additionally converts the case requiring state knowledge. This is operator conformance on frozen fixtures, not repair quality of any live model.

\subsection{{Integrity, Boundaries, and Assignment Accounting}}
All {integrity["fault_count"]} faults prespecified as detectable were rejected by their designated check operations ({integrity["detected_fault_count"]}/{integrity["fault_count"]}). Because this pilot does not compare stable typed detector codes, it does not establish detector-layer attribution. Separately, the known provenance-boundary fixture substituted a different invalid precursor before the same recorded valid repair, recomputed the checksum, and passed replay as expected ({integrity_boundary["observed_undetected_count"]}/{integrity_boundary["boundary_count"]} undetected). Thus, the mechanism does not protect against a writer who can recompute unkeyed checksums, and replay does not authenticate the repair-generation operation. Two open boundary sentinels---unextracted narrative disclosure and simultaneous omission of a required object from candidate and policy---were intentionally accepted at the encoded layer ({boundary["encoded_acceptance_count"]}/{boundary["sentinel_count"]}), with {boundary["safety_pass_count"]} labelled as safety passes. The former unknown-top-level-field acceptance boundary was reclassified after Stage 8 as a closed negative regression: both proposal and replay parsers specifically rejected a complete 12-field candidate carrying one unknown key ({closed_boundary["passed_regression_count"]}/{closed_boundary["regression_count"]}). This establishes parser rejection parity, not semantic safety. Among seven adapter/accounting assignments, outcomes were {adapter["commit_count"]} commit, {adapter["fallback_count"]} symbolic fallback, and {adapter["adapter_failure_count"]} adapter failures. Synthetic telemetry fields were populated and propagated for {adapter["provider_latency_observed_count"]}/7 assignments; these are schema-pinned constants verifying accounting-field propagation, not measurements. All {guards["detected_guard_count"]}/{guards["guard_count"]} injected duplicate or missing-assignment guards failed closed. These are raw counts from synthetic offline fixtures.
""".strip()
        + "\n"
    )


def _tables(data: dict[str, Any], korean: bool) -> str:
    integrity = data["integrity_faults"]["raw_counts"]
    integrity_boundary = data["integrity_boundaries"]["raw_counts"]
    adapter = data["adapter_accounting"]["raw_counts"]
    guards = data["accounting_guards"]["raw_counts"]
    gate = data["gate_conformance"]["raw_counts"]
    boundary = data["boundary_sentinels"]["raw_counts"]
    closed_boundary = data["closed_boundary_regressions"]["raw_counts"]
    by_class = _class_counts(data)
    caption1 = (
        "수리 arm $\\times$ repairability class 정확 집계 (설계 픽스처)"
        if korean
        else "Repair Arm $\\times$ Repairability Class, Exact Counts (Designed Fixtures)"
    )
    caption2 = "동결 파일럿 원시 집계" if korean else "Frozen-Pilot Raw Accounting"
    if korean:
        arm_header = "Arm & 정보원 & G-rep.$^{f}$ & O-only$^{f}$ & Irrep.$^{f}$ & 수정$^{e}$"
        arm_labels = (
            "Rejection-only ($K{=}0$)",
            "블라인드 retry",
            "반례 유도 $\\rho$",
            "상태 판독 oracle",
        )
        arm_sources = ("없음", "없음", "오류 집합 $E$", "권위 상태+정책")
        count_header = "검사 & 분자 & 분모"
        count_labels = (
            "게이트 fixture 일치$^{c}$",
            "알려진 경계 허용$^{a}$",
            "닫힌 unknown-key 경계 거부$^{d}$",
            "탐지 가능 무결성 결함 거부",
            "알려진 무결성 경계 replay 허용$^{b}$",
            "Adapter 커밋",
            "기호 fallback",
            "Adapter 실패",
            "Manifest guard 거부",
        )
        footnote = (
            "$^{a}$경계 허용은 의미 추출과 정책 완결성 한계를 "
            "문서화하며 safety pass가 아니다. "
            "$^{b}$Replay는 repair 생성을 인증하거나 다시 실행하지 않는다. "
            "$^{c}$Loader가 이 일치를 강제하므로 측정값이 아니라 구성 불변량이다. "
            "$^{d}$Stage 8 이후의 parser 거부 parity이며 의미 안전성 증거가 아니다."
        )
        footnote_e = (
            " $^{e}$commit된 수리의 변경 candidate field 평균 개수(최소성 proxy); "
            "실패한 arm 실행은 상태를 변경하지 않았다. "
            "$^{f}$commit/사례 수. G-rep. = guided-repairable, O-only = oracle-only, "
            "Irrep. = irreparable(동결된 repairability class)."
        )
    else:
        arm_header = "Arm & Info source & G-rep.$^{f}$ & O-only$^{f}$ & Irrep.$^{f}$ & Edits$^{e}$"
        arm_labels = (
            "Rejection-only ($K{=}0$)",
            "Blind unchanged retry",
            "Counterexample-guided $\\rho$",
            "State-reading oracle",
        )
        arm_sources = ("none", "none", "error set $E$", "state+policy")
        count_header = "Check & Numerator & Denominator"
        count_labels = (
            "Gate fixture agreement$^{c}$",
            "Known-boundary acceptances$^{a}$",
            "Closed unknown-key boundary rejected$^{d}$",
            "Detectable integrity faults rejected",
            "Known integrity boundary replay-accepted$^{b}$",
            "Adapter commits",
            "Symbolic fallbacks",
            "Adapter failures",
            "Manifest guards rejected",
        )
        footnote = (
            "$^{a}$Boundary acceptances document semantic-extraction and policy-completeness "
            "limits; they are not safety passes. $^{b}$Replay does not "
            "authenticate or re-execute repair generation. $^{c}$The loader enforces this "
            "agreement, so it is a construction invariant rather than a measurement. "
            "$^{d}$This is post-Stage-8 parser rejection parity, not semantic-safety evidence."
        )
        footnote_e = (
            " $^{e}$Mean changed candidate fields over committed repairs (minimality proxy); "
            "failed arm executions left the state unchanged. "
            "$^{f}$Commits/cases. G-rep. = guided-repairable, O-only = oracle-only, "
            "Irrep. = irreparable (frozen repairability classes)."
        )
    # One row per repair arm, read from the frozen per-class aggregate records. Cell
    # values are exact commit/case counts per frozen repairability class, so the table
    # is a designed-fixture comparison, never a population estimate.
    arm_ids = ("rejection_only", "unchanged_retry", "guided_repair", "structured_repair")
    label_by_arm = dict(zip(arm_ids, arm_labels, strict=True))
    source_by_arm = dict(zip(arm_ids, arm_sources, strict=True))

    def _cell(arm: str, repairability: str) -> str:
        row = by_class[(arm, repairability)]
        return f"{row['commit_count']}/{row['case_count']}"

    def _mean_edit(arm: str) -> str:
        commits = [
            row
            for row in data["repair_arms"]["raw_counts_by_class"]
            if row["arm_id"] == arm and row["repaired_commit_count"] > 0
        ]
        total_commits = sum(row["repaired_commit_count"] for row in commits)
        if total_commits == 0:
            return "---"
        weighted = sum(
            row["mean_commit_edit_field_count"] * row["repaired_commit_count"] for row in commits
        )
        return f"{weighted / total_commits:.1f}"

    arm_rows = [
        rf"{label_by_arm[arm]} & {source_by_arm[arm]} & "
        rf"{_cell(arm, 'guided_repairable')} & {_cell(arm, 'oracle_only')} & "
        rf"{_cell(arm, 'irreparable')} & {_mean_edit(arm)} \\"
        for arm in arm_ids
    ]
    return (
        rf"""
\begin{{table}}[t]
\caption{{{caption1}}}
\label{{tab:pilot-repair}}
\centering\scriptsize
\begin{{tabularx}}{{\columnwidth}}{{@{{}}>{{\raggedright\arraybackslash}}X
 >{{\raggedright\arraybackslash}}X rrrr@{{}}}}
\toprule
{arm_header} \\
\midrule
{chr(10).join(arm_rows)}
\bottomrule
\end{{tabularx}}
\end{{table}}

\begin{{table}}[t]
\caption{{{caption2}}}
\label{{tab:pilot-accounting}}
\centering\footnotesize
\begin{{tabularx}}{{\columnwidth}}{{@{{}}Xrr@{{}}}}
\toprule
{count_header} \\
\midrule
{count_labels[0]} & {gate["passed_fixture_count"]} & {gate["fixture_count"]} \\
{count_labels[1]} & {boundary["encoded_acceptance_count"]} & {boundary["sentinel_count"]} \\
{count_labels[2]} & {closed_boundary["passed_regression_count"]} & {closed_boundary["regression_count"]} \\
{count_labels[3]} & {integrity["detected_fault_count"]} & {integrity["fault_count"]} \\
{count_labels[4]} & {integrity_boundary["observed_undetected_count"]} & {integrity_boundary["boundary_count"]} \\
{count_labels[5]} & {adapter["commit_count"]} & {adapter["assigned_case_count"]} \\
{count_labels[6]} & {adapter["fallback_count"]} & {adapter["assigned_case_count"]} \\
{count_labels[7]} & {adapter["adapter_failure_count"]} & {adapter["assigned_case_count"]} \\
{count_labels[8]} & {guards["detected_guard_count"]} & {guards["guard_count"]} \\
\bottomrule
\end{{tabularx}}
\vspace{{1pt}}\parbox{{0.96\columnwidth}}{{\scriptsize {footnote}{footnote_e}}}
\end{{table}}
""".strip()
        + "\n"
    )


def _live_result_text(packet: dict[str, Any], korean: bool) -> str:
    cells = packet["current"]
    headline = cells["signal_v2_blind"]
    model_id = _escape(headline["model_id"])
    call_count = headline["counts"]["seeds"]
    repair_budget = headline["repair_budget"]
    guided_commits = headline["per_arm"]["guided_repair"]["commits"]
    blind_commits = headline["per_arm"]["unchanged_retry"]["commits"]
    noncommits = sum(
        arm["non_commits"] for summary in cells.values() for arm in summary["per_arm"].values()
    )
    isolated = sum(
        arm["non_commit_state_isolated"]
        for summary in cells.values()
        for arm in summary["per_arm"].values()
    )
    max_initial_errors = max(len(row["initial_error_codes"]) for row in packet["diagnostic_rows"])

    if korean:
        return (
            rf"""
\subsection{{라이브 스크리닝 파일럿 (pilot-only)}}
별도 스크리닝 파일럿은 Codex CLI를 통해 {model_id}을 호출했다. 셀마다 seed로 구분한 제안 호출 {call_count}회와 수리 예산 $K={repair_budget}$을 사용했고, 각 호출의 최초 후보 하나를 블라인드 동일 후보 retry와 $\rho$가 공유했다. Hosted revision은 고정되지 않았고 token 회계는 제공되지 않았으며 seed는 hosted sampler를 제어하지 않으므로 이 호출들은 독립 무작위 표본이 아니라 준반복이다. 따라서 추론 통계나 모델 순위를 보고하지 않는다.

표~\ref{{tab:live-screening}}에서 유도 우위는 의도적으로 guided-repairable 오류가 나오도록 구성한 \texttt{{signal-repair-v2}}의 policy-blind 셀에서만 나타났다. 최초 후보 {call_count}/{call_count}가 모두 무효였고 $\rho$는 {guided_commits}/{call_count}, 블라인드는 {blind_commits}/{call_count}를 commit했다. 나머지 현재 셀 4개는 유도 우위를 보이지 않았다. 세 셀은 최초 후보가 이미 유효했고, 동결 기저의 goal-directed 셀은 수리 불가 quest-stage regression이었다. 현재 셀의 모든 noncommit arm 결과 {isolated}/{noncommits}가 prior-state hash를 보존했다. 이 결과는 해당 오류 regime에서의 mechanism transfer만 지지하며 모집단 효능, 모델 승격, 표본 효율 일반화는 지지하지 않는다. 따라서 \texttt{{C-PILOT-007}}과 \texttt{{C-PILOT-008}}은 pilot-only이고 \texttt{{C-RESULT-003}}은 \texttt{{TODO-RESULT}}로 남는다. 폐기된 v1 진단에서는 동반 오류가 최대 {max_initial_errors}개에서 수리 불가 knowledge 오류 1개로 줄었지만 commit되지 않아, 오류 하나라도 수리 불가이면 부분 수리가 합성되지 않음을 보여 주었다.
""".strip()
            + "\n"
        )
    return (
        rf"""
\subsection{{Live Screening Pilot (Pilot-Only)}}
A separate screening pilot called {model_id} through the Codex CLI. It used {call_count} seed-indexed proposal calls per cell and repair budget $K={repair_budget}$; within each call, blind unchanged retry and $\rho$ received the same initial candidate. The hosted revision was unpinned, token accounting was unavailable, and the seeds did not control the hosted sampler, so the calls are quasi-replicates rather than independent randomized samples. We report neither inferential statistics nor a model ranking.

In Table~\ref{{tab:live-screening}}, a guided advantage appeared only in the policy-blind \texttt{{signal-repair-v2}} cell, a state deliberately constructed to elicit guided-repairable errors. All {call_count}/{call_count} initial candidates were invalid; $\rho$ committed {guided_commits}/{call_count}, whereas blind retry committed {blind_commits}/{call_count}. The other four current cells showed no guided advantage: three had already-valid initial candidates, and the frozen-base goal-directed cell produced irreparable quest-stage regressions. All {isolated}/{noncommits} noncommit arm outcomes in the current cells preserved the prior-state hash. This supports mechanism transfer only in that error regime, not population efficacy, model promotion, or a general sample-efficiency claim. Accordingly, \texttt{{C-PILOT-007}} and \texttt{{C-PILOT-008}} are pilot-only while \texttt{{C-RESULT-003}} remains \texttt{{TODO-RESULT}}. In the superseded v1 diagnostic, guided repair reduced up to {max_initial_errors} co-occurring errors to one irreparable knowledge error but still could not commit, showing that partial per-error repairs do not compose when any residual error is irreparable.
""".strip()
        + "\n"
    )


def _live_tables(packet: dict[str, Any], korean: bool) -> str:
    cells = packet["current"]
    ordered = (
        ("frozen_visible", "Frozen / visible", "동결 / 공개"),
        ("frozen_blind", "Frozen / blind", "동결 / 비공개"),
        ("frozen_goal_blind", "Frozen / goal-blind", "동결 / 목표-비공개"),
        ("signal_v2_visible", "Signal-v2 / visible", "Signal-v2 / 공개"),
        ("signal_v2_blind", "Signal-v2 / blind", "Signal-v2 / 비공개"),
    )
    code_labels = {
        "QUEST_STAGE_REGRESSION": "QSR",
        "POLICY_EFFECT_OMISSION": "PEO",
        "POLICY_EFFECT_VIOLATION": "PEV",
        "POLICY_PRECONDITION_OMISSION": "PPO",
    }
    rows = []
    for key, english_label, korean_label in ordered:
        summary = cells[key]
        error_label = "+".join(
            code_labels[code] for code in summary["observed_initial_error_codes"]
        )
        if not error_label:
            error_label = "---"
        rows.append(
            f"{korean_label if korean else english_label} & "
            f"{summary['counts']['initially_valid']}/{summary['counts']['seeds']} & "
            f"{summary['per_arm']['guided_repair']['commits']}/{summary['counts']['seeds']} & "
            f"{summary['per_arm']['unchanged_retry']['commits']}/{summary['counts']['seeds']} & "
            rf"{error_label} \\"
        )
    caption = (
        "라이브 스크리닝 파일럿 정확 집계 (셀당 제안 5회, $K{=}1$)"
        if korean
        else "Live Screening Pilot, Exact Counts (Five Proposals per Cell, $K{=}1$)"
    )
    header = (
        "기저 / 조건 & 최초 유효 & $\\rho$ commit & Blind commit & 최초 오류"
        if korean
        else "Base / condition & Initial valid & $\\rho$ commits & Blind commits & Initial errors"
    )
    footnote = (
        "QSR = quest-stage regression, PEO = policy-effect omission, "
        "PEV = policy-effect violation, PPO = policy-precondition omission. "
        "모든 수치는 screening-pilot-only이며 추론 통계가 아니다. 폐기된 v1 진단은 표에서 제외한다."
        if korean
        else "QSR = quest-stage regression, PEO = policy-effect omission, "
        "PEV = policy-effect violation, PPO = policy-precondition omission. "
        "All counts are screening-pilot-only, without inferential statistics; the superseded v1 "
        "diagnostic is excluded."
    )
    return (
        rf"""
\begin{{table}}[t]
\caption{{{caption}}}
\label{{tab:live-screening}}
\centering\scriptsize
\begin{{tabularx}}{{\columnwidth}}{{@{{}}>{{\raggedright\arraybackslash}}X rrr >{{\raggedright\arraybackslash}}X@{{}}}}
\toprule
{header} \\
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabularx}}
\vspace{{1pt}}\parbox{{0.96\columnwidth}}{{\scriptsize {footnote}}}
\end{{table}}
""".strip()
        + "\n"
    )


def main() -> None:
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    if data.get("inference") != "none; raw designed-fixture counts only":
        raise ValueError("pilot result scope is not the expected descriptive-only contract")
    live_packet = _load_live_packet()
    OUT.mkdir(parents=True, exist_ok=True)
    for language, korean in (("en", False), ("ko", True)):
        (OUT / f"pilot_results_{language}.tex").write_text(
            _result_text(data, korean), encoding="utf-8"
        )
        (OUT / f"pilot_tables_{language}.tex").write_text(_tables(data, korean), encoding="utf-8")
        (OUT / f"live_pilot_results_{language}.tex").write_text(
            _live_result_text(live_packet, korean), encoding="utf-8"
        )
        (OUT / f"live_pilot_tables_{language}.tex").write_text(
            _live_tables(live_packet, korean), encoding="utf-8"
        )
    print(
        "generated bilingual offline and live-screening inputs from "
        f"{RESULTS_PATH.relative_to(ROOT)} and {LIVE_MANIFEST_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
