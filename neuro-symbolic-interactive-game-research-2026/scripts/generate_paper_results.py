#!/usr/bin/env python3
"""Generate bilingual IEEE result prose and compact tables from frozen pilot JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
RESULTS_PATH = ROOT / "research/academic-pipeline/stage-04-pilot/pilot-results.json"
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


def main() -> None:
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    if data.get("inference") != "none; raw designed-fixture counts only":
        raise ValueError("pilot result scope is not the expected descriptive-only contract")
    OUT.mkdir(parents=True, exist_ok=True)
    for language, korean in (("en", False), ("ko", True)):
        (OUT / f"pilot_results_{language}.tex").write_text(
            _result_text(data, korean), encoding="utf-8"
        )
        (OUT / f"pilot_tables_{language}.tex").write_text(_tables(data, korean), encoding="utf-8")
    print(f"generated bilingual result inputs from {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
