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


def _result_text(data: dict[str, Any], korean: bool) -> str:
    gate = data["gate_conformance"]["raw_counts"]
    boundary = data["boundary_sentinels"]["raw_counts"]
    integrity = data["integrity_faults"]["raw_counts"]
    integrity_boundary = data["integrity_boundaries"]["raw_counts"]
    adapter = data["adapter_accounting"]["raw_counts"]
    guards = data["accounting_guards"]["raw_counts"]
    if korean:
        return (
            rf"""
\subsection{{구조 필드 게이트 적합성}}
동결된 {gate["fixture_count"]}개 게이트 fixture(유효 control 1개와 고립된 음성 fixture {gate["negative_fixture_count"]}개)는 모두 사전 명세 결과와 일치했다({gate["passed_fixture_count"]}/{gate["fixture_count"]}). 구현된 오류 코드 {gate["implemented_code_count"]}종이 각각 관찰됐고, 비commit 경로는 전체 정준 상태를 유지했다. 이 일치는 저자가 설계한 구조 필드 oracle에 대한 구현 적합성이며 독립 의미 판정의 정확도가 아니다.

\subsection{{수리 메커니즘}}
처음부터 유효하지 않은 두 case에서 rejection-only와 동일 후보 retry는 각각 0/2 commit이었다. 구조화 수리는 수리 가능 precondition case를 1회 수리 후 commit했고 수리 불가능 reachability case는 fallback하여 1/2 commit이었다. 이는 결정론적 callback의 제어 흐름 sanity check이며 LLM 수리 품질이나 sample efficiency 비교가 아니다.

\subsection{{무결성, 경계, 배정 회계}}
현재 명세가 검출 가능하다고 지정한 {integrity["fault_count"]}개 fault fixture는 모두 지정된 검사 연산에서 거부됐다({integrity["detected_fault_count"]}/{integrity["fault_count"]}). 이 파일럿은 안정적인 typed detector code까지 대조하지 않으므로 detector layer 귀속을 입증하지 않는다. 별도로, 동일하게 기록된 유효 수리 앞의 무효 선행 후보를 다른 무효 후보로 치환하고 체크섬을 재계산한 알려진 provenance 경계는 예상대로 재생을 통과했다({integrity_boundary["observed_undetected_count"]}/{integrity_boundary["boundary_count"]} 미검출). 따라서 키 없는 체크섬을 재계산할 수 있는 작성자를 방어하지 않으며, 재생은 repair 생성 연산의 출처를 인증하지 않는다. 세 경계 sentinel---자연어 disclosure 미추출, required object의 후보·정책 동시 누락, 알 수 없는 candidate top-level field 무시---은 {boundary["encoded_acceptance_count"]}/{boundary["sentinel_count"]}가 의도대로 인코딩상 허용됐고 safety pass는 {boundary["safety_pass_count"]}건이었다. Adapter/accounting 7개 배정에서는 commit {adapter["commit_count"]}, 기호 fallback {adapter["fallback_count"]}, adapter failure {adapter["adapter_failure_count"]}였으며, provider 응답 관측은 {adapter["provider_latency_observed_count"]}/7이었다. 배정 guard {guards["detected_guard_count"]}/{guards["guard_count"]}가 중복·누락을 거부했다. 이 수치는 모두 합성 offline fixture의 raw count다.
""".strip()
            + "\n"
        )
    return (
        rf"""
\subsection{{Declared-Field Gate Conformance}}
All {gate["fixture_count"]} frozen gate fixtures---one valid control and {gate["negative_fixture_count"]} isolated negative fixtures---matched their prespecified outcomes ({gate["passed_fixture_count"]}/{gate["fixture_count"]}). Each of the {gate["implemented_code_count"]} implemented error codes was observed once, and every noncommit path preserved the complete canonical state. This agreement is implementation conformance to an authored structured-field oracle, not accuracy against independent semantic labels.

\subsection{{Repair Mechanism}}
Across two initially invalid cases, rejection-only and unchanged-candidate retry each committed 0/2. Structured repair committed the repairable precondition case after one repair and left the deliberately nonrepairable reachability case at fallback, for 1/2 commits. This is a deterministic callback control-flow sanity check, not an estimate of LLM repair quality or sample efficiency.

\subsection{{Integrity, Boundaries, and Assignment Accounting}}
All {integrity["fault_count"]} faults prespecified as detectable were rejected by their designated check operations ({integrity["detected_fault_count"]}/{integrity["fault_count"]}). Because this pilot does not compare stable typed detector codes, it does not establish detector-layer attribution. Separately, the known provenance-boundary fixture substituted a different invalid precursor before the same recorded valid repair, recomputed the checksum, and passed replay as expected ({integrity_boundary["observed_undetected_count"]}/{integrity_boundary["boundary_count"]} undetected). Thus, the mechanism does not protect against a writer who can recompute unkeyed checksums, and replay does not authenticate the repair-generation operation. Three boundary sentinels---unextracted narrative disclosure, simultaneous omission of a required object from candidate and policy, and an ignored unknown top-level candidate field---were intentionally accepted at the encoded layer ({boundary["encoded_acceptance_count"]}/{boundary["sentinel_count"]}), with {boundary["safety_pass_count"]} labelled as safety passes. Among seven adapter/accounting assignments, outcomes were {adapter["commit_count"]} commit, {adapter["fallback_count"]} symbolic fallback, and {adapter["adapter_failure_count"]} adapter failures; provider-response latency was observed for {adapter["provider_latency_observed_count"]}/7 only. All {guards["detected_guard_count"]}/{guards["guard_count"]} injected duplicate or missing-assignment guards failed closed. These are raw counts from synthetic offline fixtures.
""".strip()
        + "\n"
    )


def _tables(data: dict[str, Any], korean: bool) -> str:
    repair = {row["arm_id"]: row for row in data["repair_arms"]["raw_counts_by_arm"]}
    integrity = data["integrity_faults"]["raw_counts"]
    integrity_boundary = data["integrity_boundaries"]["raw_counts"]
    adapter = data["adapter_accounting"]["raw_counts"]
    guards = data["accounting_guards"]["raw_counts"]
    gate = data["gate_conformance"]["raw_counts"]
    boundary = data["boundary_sentinels"]["raw_counts"]
    caption1 = "결정론적 수리 arm 결과" if korean else "Deterministic Repair-Arm Outcomes"
    caption2 = "동결 파일럿 원시 집계" if korean else "Frozen-Pilot Raw Accounting"
    if korean:
        arm_header = "Arm & 사례 & 커밋 & 수리 호출"
        arm_labels = ("거부 전용", "동일 후보 재시도", "구조화 수리")
        count_header = "검사 & 분자 & 분모"
        count_labels = (
            "게이트 fixture 일치",
            "알려진 경계 허용$^{a}$",
            "탐지 가능 무결성 결함 거부",
            "알려진 무결성 경계 replay 허용$^{b}$",
            "Adapter 커밋",
            "기호 fallback",
            "Adapter 실패",
            "Manifest guard 거부",
        )
        footnote = (
            "$^{a}$경계 허용은 의미 추출, 정책 완결성, 알 수 없는 필드 처리의 한계를 "
            "문서화하며 safety pass가 아니다. "
            "$^{b}$Replay는 repair 생성을 인증하거나 다시 실행하지 않는다."
        )
    else:
        arm_header = "Arm & Cases & Commits & Repair calls"
        arm_labels = ("Rejection only", "Unchanged retry", "Structured repair")
        count_header = "Check & Numerator & Denominator"
        count_labels = (
            "Gate fixture agreement",
            "Known-boundary acceptances$^{a}$",
            "Detectable integrity faults rejected",
            "Known integrity boundary replay-accepted$^{b}$",
            "Adapter commits",
            "Symbolic fallbacks",
            "Adapter failures",
            "Manifest guards rejected",
        )
        footnote = (
            "$^{a}$Boundary acceptances document semantic-extraction, policy-completeness, and "
            "unknown-field handling limits; they are not safety passes. $^{b}$Replay does not "
            "authenticate or re-execute repair generation."
        )
    return (
        rf"""
\begin{{table}}[t]
\caption{{{caption1}}}
\label{{tab:pilot-repair}}
\centering\footnotesize
\begin{{tabular}}{{@{{}}lccc@{{}}}}
\toprule
{arm_header} \\
\midrule
{arm_labels[0]} & 2 & {repair["rejection_only"]["commit_count"]} & {repair["rejection_only"]["executed_repair_count"]} \\
{arm_labels[1]} & 2 & {repair["unchanged_retry"]["commit_count"]} & {repair["unchanged_retry"]["executed_repair_count"]} \\
{arm_labels[2]} & 2 & {repair["structured_repair"]["commit_count"]} & {repair["structured_repair"]["executed_repair_count"]} \\
\bottomrule
\end{{tabular}}
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
{count_labels[2]} & {integrity["detected_fault_count"]} & {integrity["fault_count"]} \\
{count_labels[3]} & {integrity_boundary["observed_undetected_count"]} & {integrity_boundary["boundary_count"]} \\
{count_labels[4]} & {adapter["commit_count"]} & {adapter["assigned_case_count"]} \\
{count_labels[5]} & {adapter["fallback_count"]} & {adapter["assigned_case_count"]} \\
{count_labels[6]} & {adapter["adapter_failure_count"]} & {adapter["assigned_case_count"]} \\
{count_labels[7]} & {guards["detected_guard_count"]} & {guards["guard_count"]} \\
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
    OUT.mkdir(parents=True, exist_ok=True)
    for language, korean in (("en", False), ("ko", True)):
        (OUT / f"pilot_results_{language}.tex").write_text(
            _result_text(data, korean), encoding="utf-8"
        )
        (OUT / f"pilot_tables_{language}.tex").write_text(_tables(data, korean), encoding="utf-8")
    print(f"generated bilingual result inputs from {RESULTS_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
