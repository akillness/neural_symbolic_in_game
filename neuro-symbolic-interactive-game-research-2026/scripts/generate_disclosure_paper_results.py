#!/usr/bin/env python3
"""Generate bilingual, source-bound evidence for the frozen ``reveal_hint`` packet.

This producer is deliberately additive.  It reads the frozen expectation packet and
only the four files emitted by ``run_disclosure_evaluation.py``; it never reads or
rewrites the historical NPC producers or their evidence.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nesy_game.disclosure import verify_publication_sources

PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"
PACKET_SIDECAR = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.sha256"
RESULTS = ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5"
OUT = ROOT / "paper/latex/generated"
FIGURES = ROOT / "paper/latex/figures"
EXPECTED_PACKET_SHA256 = "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"
ARMS = ("unchecked_isolated", "general_rule", "ontology_gate")
STRATA = (("N", "normal"), ("B", "boundary"), ("M", "malformed"))
TRACE_NAME = "disclosure-trace.jsonl"
SUMMARY_NAME = "comparison-summary.json"
FACTUAL_NAME = "factual-summary.json"
METADATA_NAME = "metadata.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing input: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON input {path}: {exc}") from exc


def _read_rows(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ValueError(f"missing input: {path}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL input {path}:{line_number}: {exc}") from exc
        _require(isinstance(value, dict), f"JSONL row is not an object: {path}:{line_number}")
        rows.append(value)
    return rows


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _latex(value: Any) -> str:
    text = str(value)
    for old, new in (
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
    ):
        text = text.replace(old, new)
    return text


def _latex_code(value: Any) -> str:
    """Escape code-like values and add legal line-break points for long tokens."""
    text = _latex(value)
    return r"\allowbreak{}".join(text[index : index + 16] for index in range(0, len(text), 16))


def _expected_view(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    return {
        "allowed": bool(expected["allowed"]),
        "codes": sorted(set(expected.get("codes", []))),
        "template_id": expected.get("template_id"),
        "state_effect": expected.get("state_effect", "denied_no_mutation"),
    }


def _cases(packet: dict[str, Any]) -> dict[str, dict[str, Any]]:
    cases: list[dict[str, Any]] = [
        *packet["normal_cases"],
        *packet["boundary_cases"],
        *packet["malformed_cases"],
    ]
    by_id = {case["case_id"]: case for case in cases}
    _require(len(by_id) == len(cases), "frozen packet has duplicate case IDs")
    return by_id


def _load() -> dict[str, Any]:
    packet_bytes = PACKET.read_bytes() if PACKET.is_file() else b""
    _require(bool(packet_bytes), f"missing frozen expectation packet: {PACKET}")
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()
    _require(packet_sha == EXPECTED_PACKET_SHA256, "frozen expectation packet digest mismatch")
    sidecar = PACKET_SIDECAR.read_text(encoding="utf-8").strip().split()
    _require(
        len(sidecar) >= 1 and sidecar[0] == EXPECTED_PACKET_SHA256,
        "expectation sidecar digest mismatch",
    )
    packet = _read_json(PACKET)
    _require(
        packet.get("status") == "FROZEN_EXPECTATIONS_NOT_RUNTIME_RESULTS",
        "expectations packet is not frozen",
    )
    _require(
        packet.get("scope", {}).get("operation") == "reveal_hint",
        "producer only supports reveal_hint",
    )
    case_by_id = _cases(packet)
    _require(len(packet["normal_cases"]) == 48, "frozen normal denominator drift")
    _require(len(packet["boundary_cases"]) == 4, "frozen boundary denominator drift")
    _require(len(packet["malformed_cases"]) == 8, "frozen malformed denominator drift")
    _require(len(packet["rule_change_fixtures"]) == 2, "frozen rule-change fixture drift")

    trace_path = RESULTS / TRACE_NAME
    comparison_path = RESULTS / SUMMARY_NAME
    factual_path = RESULTS / FACTUAL_NAME
    metadata_path = RESULTS / METADATA_NAME
    rows = _read_rows(trace_path)
    comparison = _read_json(comparison_path)
    factual = _read_json(factual_path)
    metadata = _read_json(metadata_path)
    _require(len(rows) == len(case_by_id) * len(ARMS), "trace cardinality is not cases x arms")
    keys = [(row.get("case_id"), row.get("arm")) for row in rows]
    _require(len(set(keys)) == len(keys), "trace has duplicate case/arm records")
    expected_keys = {(case_id, arm) for case_id in case_by_id for arm in ARMS}
    _require(set(keys) == expected_keys, "trace case/arm set differs from frozen packet")
    for row in rows:
        case_id = row["case_id"]
        arm = row["arm"]
        case = case_by_id[case_id]
        _require(row.get("stratum") == case_id[0], f"{case_id}/{arm}: stratum is not case prefix")
        _require(
            row.get("expected") == _expected_view(case), f"{case_id}/{arm}: trace expectation drift"
        )
        observed = row.get("observed")
        _require(isinstance(observed, dict), f"{case_id}/{arm}: observed semantic view missing")
        _require(isinstance(row.get("checks"), list), f"{case_id}/{arm}: checks missing")
        for check in row["checks"]:
            _require(
                isinstance(check, dict) and check.get("outcome") in {"pass", "fail"},
                f"{case_id}/{arm}: check outcome must be pass/fail",
            )
        _require(
            isinstance(row.get("replay_equal"), bool), f"{case_id}/{arm}: replay_equal missing"
        )
        _require(isinstance(row.get("mismatch"), bool), f"{case_id}/{arm}: mismatch missing")
        _require(isinstance(row.get("mutated"), bool), f"{case_id}/{arm}: mutated missing")

    _require(
        metadata.get("packet_sha256") == packet_sha, "results metadata does not bind packet digest"
    )
    _require(
        metadata.get("contract_version") == packet.get("packet_version"),
        "results contract version drift",
    )
    _require(metadata.get("arms") == list(ARMS), "results arm order drift")
    _require(set(metadata.get("case_ids", [])) == set(case_by_id), "results case IDs drift")
    source_mismatches = metadata.get("source_hash_mismatches") or {}
    _require(isinstance(source_mismatches, dict), "results source-hash mismatch field is malformed")
    for source_path, detail in source_mismatches.items():
        _require(
            isinstance(source_path, str) and isinstance(detail, dict),
            "source-hash mismatch record is malformed",
        )
        _require(
            isinstance(detail.get("expected"), str) and isinstance(detail.get("observed"), str),
            "source-hash mismatch lacks expected/observed digests",
        )
    observed_source_hashes = metadata.get("source_hashes") or {}
    _require(
        isinstance(observed_source_hashes, dict) and observed_source_hashes,
        "results source hashes are missing",
    )
    _require(
        isinstance(metadata.get("public_source_bindings"), dict)
        and bool(metadata["public_source_bindings"])
        and metadata.get("observation_scope")
        == "new deterministic Python evaluation; no new Godot or model observation",
        "current public-source evaluation metadata missing",
    )
    verify_publication_sources(
        ROOT,
        observed_source_hashes,
        packet,
        public_source_bindings=metadata.get("public_source_bindings"),
    )
    _require(factual.get("status") == "PASS", "general/ontology disclosure results are not PASS")
    _require(
        factual.get("general_ontology_equal") is True, "general and ontology outcomes are not equal"
    )
    _require(
        factual.get("rule_change_fixtures_match") is True, "rule-change fixtures did not match"
    )

    computed_arms = _arm_metrics(rows)
    _require(
        comparison.get("arms") == computed_arms, "comparison arm metrics do not match raw traces"
    )
    _require(
        comparison.get("case_counts") == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
        "comparison denominators drift",
    )
    _require(
        comparison.get("general_vs_ontology", {}).get("outcome_equal") is True,
        "summary equality is not true",
    )
    _validate_fixtures(packet, comparison)
    return {
        "packet": packet,
        "packet_sha": packet_sha,
        "rows": rows,
        "comparison": comparison,
        "factual": factual,
        "metadata": metadata,
        "inputs": {
            "packet": PACKET,
            "packet_sidecar": PACKET_SIDECAR,
            "trace": trace_path,
            "comparison": comparison_path,
            "factual": factual_path,
            "metadata": metadata_path,
        },
    }


def _arm_metrics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        arm_rows = [row for row in rows if row.get("arm") == arm]
        unauthorized = [
            row for row in arm_rows if not row["expected"]["allowed"] and row["observed"]["allowed"]
        ]
        redisplay = [
            row
            for row in arm_rows
            if row["expected"]["state_effect"] == "redisplay_no_mutation" and row["mutated"]
        ]
        unsafe = {row["case_id"]: row for row in (*unauthorized, *redisplay)}
        fresh_mismatches = [
            row
            for row in arm_rows
            if row["mismatch"]
            and row["expected"]["allowed"]
            and row["expected"]["state_effect"] == "fresh_disclosure"
        ]

        def by_stratum(selected: Iterable[dict[str, Any]]) -> dict[str, int]:
            counts = Counter(row["stratum"] for row in selected)
            return {stratum: counts[stratum] for stratum in ("N", "B", "M")}

        metrics[arm] = {
            "case_count": len(arm_rows),
            "normal_case_count": sum(row.get("stratum") == "N" for row in arm_rows),
            "allowed_count": sum(bool(row["observed"].get("allowed")) for row in arm_rows),
            "denied_count": sum(not bool(row["observed"].get("allowed")) for row in arm_rows),
            "expected_mismatch_count": sum(bool(row.get("mismatch")) for row in arm_rows),
            "semantic_mismatch_by_stratum": by_stratum(row for row in arm_rows if row["mismatch"]),
            "state_assertion_failure_count": sum(
                bool(row.get("state_assertion_failures")) for row in arm_rows
            ),
            "display_assertion_failure_count": sum(
                bool(row.get("display_assertion_failures")) for row in arm_rows
            ),
            "replay_mismatch_count": sum(not bool(row.get("replay_equal")) for row in arm_rows),
            "unsafe_violation_count": len(unsafe),
            "unique_unsafe_case_count": len(unsafe),
            "unsafe_by_stratum": by_stratum(unsafe.values()),
            "unauthorized_allow_count": len({row["case_id"] for row in unauthorized}),
            "unauthorized_allow_by_stratum": by_stratum(unauthorized),
            "redisplay_mutation_count": len({row["case_id"] for row in redisplay}),
            "redisplay_mutation_by_stratum": by_stratum(redisplay),
            "permitted_fresh_representation_mismatch_count": len(
                {row["case_id"] for row in fresh_mismatches}
            ),
            "permitted_fresh_representation_mismatch_by_stratum": by_stratum(fresh_mismatches),
        }
    return metrics


def _validate_fixtures(packet: dict[str, Any], comparison: dict[str, Any]) -> None:
    expected = packet["rule_change_fixtures"]
    observed = comparison.get("rule_change_comparison", {}).get("fixtures")
    _require(
        isinstance(observed, list) and len(observed) == len(expected),
        "rule-change fixture rows drift",
    )
    for frozen, actual in zip(expected, observed):
        _require(actual.get("fixture_id") == frozen["fixture_id"], "rule-change fixture ID drift")
        _require(
            actual.get("paired_case_ids") == frozen["paired_case_ids"],
            f"{frozen['fixture_id']}: pair drift",
        )
        _require(
            actual.get("mutation") == frozen["mutation"], f"{frozen['fixture_id']}: mutation drift"
        )
        _require(
            actual.get("expected_general_code_edit") == frozen["expected_general_code_edit"],
            f"{frozen['fixture_id']}: general edit drift",
        )
        _require(
            actual.get("expected_ontology_declaration_edit")
            == frozen["expected_ontology_declaration_edit"],
            f"{frozen['fixture_id']}: ontology edit drift",
        )
        _require(
            actual.get("mutation_scope_preserved") is True,
            f"{frozen['fixture_id']}: mutation scope not preserved",
        )
        _require(actual.get("all_pairs_match") is True, f"{frozen['fixture_id']}: pair mismatch")


def _status_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    records = list(rows)
    return {
        "pass": sum(not row["mismatch"] for row in records),
        "fail": sum(bool(row["mismatch"]) for row in records),
    }


def _check_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    records = list(rows)
    counts = Counter()
    for row in records:
        checks = row.get("checks", [])
        if not checks:
            counts["unreported_cases"] += 1
        for check in checks:
            counts[str(check["outcome"])] += 1
    return {key: counts.get(key, 0) for key in ("pass", "fail", "unreported_cases")}


def _signal_cells(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    cells: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for arm in ARMS:
        for prefix, name in STRATA:
            selected = [row for row in rows if row["arm"] == arm and row["stratum"] == prefix]
            cells[arm][name] = {
                "n": len(selected),
                "expected": _status_counts(selected),
                "replay": {
                    "pass": sum(bool(row["replay_equal"]) for row in selected),
                    "fail": sum(not bool(row["replay_equal"]) for row in selected),
                },
                "checks": _check_counts(selected),
            }
    return cells


def _ontology_label(data: dict[str, Any]) -> str:
    ontology = data["metadata"].get("runtime_ontology") or {}
    return str(ontology.get("ontology_id") or f"{data['packet']['packet_id']}:runtime-disclosure")


def _narrative(data: dict[str, Any], korean: bool) -> str:
    packet = data["packet"]
    comparison = data["comparison"]
    metadata = data["metadata"]
    digest = _latex_code(data["packet_sha"])
    counts = comparison["case_counts"]
    ontology = metadata.get("runtime_ontology") or {}
    rules = packet["rule_ids"]
    source_mismatches = metadata.get("source_hash_mismatches") or {}
    mismatch_paths = ", ".join(_latex(path) for path in sorted(source_mismatches)) or "none"
    arm_comparison = comparison["general_vs_ontology"]
    fixture_comparison = comparison["rule_change_comparison"]
    equal_case_count = arm_comparison["equal_case_count"]
    equality_case_count = arm_comparison["case_count"]
    fixtures = fixture_comparison.get("fixtures", [])
    fixture_count = len(fixtures)
    paired_case_count = sum(len(fixture.get("paired_case_ids", [])) for fixture in fixtures)
    arms_equal = (
        arm_comparison.get("outcome_equal") is True and equal_case_count == equality_case_count
    )
    fixtures_equal = fixture_comparison.get("all_fixtures_match") is True and all(
        fixture.get("all_pairs_match") is True for fixture in fixtures
    )
    arm_equality_en = (
        f"The checked general-rule and ontology-gate arms have identical outcomes on all {equal_case_count} of {equality_case_count} authored cases."
        if arms_equal
        else f"The checked general-rule and ontology-gate arms are not identical across {equal_case_count} of {equality_case_count} authored cases."
    )
    fixture_limit_en = (
        f"The rule-change fixture set contains no discriminating case between these arms: all {fixture_count} fixtures and their {paired_case_count} paired cases match."
        if fixtures_equal
        else f"The rule-change fixture set does not establish the absence of a discriminating case between these arms ({fixture_count} fixtures; {paired_case_count} paired cases)."
    )
    arm_equality_ko = (
        f"검증된 general-rule과 ontology-gate arm은 저작된 사례 전체에서 결과가 동일하다({equal_case_count}/{equality_case_count})."
        if arms_equal
        else f"검증된 general-rule과 ontology-gate arm은 저작된 사례 전체에서 결과가 동일하지 않다({equal_case_count}/{equality_case_count})."
    )
    fixture_limit_ko = (
        f"rule-change fixture 집합에는 두 arm을 가르는 discriminating case가 없으며, {fixture_count}개 fixture의 {paired_case_count}개 paired case가 모두 일치한다."
        if fixtures_equal
        else f"rule-change fixture 집합은 두 arm 사이에 discriminating case가 없음을 확립하지 않는다({fixture_count}개 fixture; {paired_case_count}개 paired case)."
    )
    if korean:
        mismatch_note = (
            f"실행 시점 관측 hash는 현재 source와 일치한다. 동결 패킷 baseline과 다른 source는 "
            f"{len(source_mismatches)}개({mismatch_paths})이며, 패킷 hash는 수정하지 않고 이 차이를 공개한다."
        )
        return (
            rf"""\subsection{{동결된 \texttt{{reveal\_hint}} 계약과 공개 증거}}
이 산출물은 동결 기대값 패킷 \texttt{{{_latex(packet["packet_id"])}}} (v{_latex(packet["packet_version"])})과 네 개 실제 결과 파일만 읽는다. 패킷 SHA-256 \texttt{{{digest}}}는 sidecar와 대조했다. 선언식 \texttt{{{_latex(packet["scope"]["normal_denominator_formula"])}}}의 정상 분모는 {counts["normal"]}개이며, 경계 {counts["boundary"]}개와 잘못된 입력 {counts["malformed"]}개는 제외한다. Trace 기대값은 gate 출력이 아닌 packet case ID로 대조한다.

내용 우선 설명은 typed input(연산·행위자·fact·stage·knowledge·prior-disclosed)을 ontology entities/relations와 authored rules에 통과시켜 check, allowed/denied 결정, canonical state effect를 기록한다. 허용된 최초 표시는 요청 fact만(조석 단서의 선언된 relationship-memory 항목도) 추가하고 stage를 보존하며 revision을 한 번 증가시킨다. 거부·기공개 재표시는 canonical state를 보존한다. 설명용일 뿐 hidden fact·자연어 함의·live capture를 주장하지 않는다.

온톨로지 선언은 \texttt{{{_latex_code(ontology.get("ontology_id", f"{packet['packet_id']}:runtime-disclosure"))}}} / v{_latex(ontology.get("ontology_version", packet["packet_version"]))}, provenance는 \texttt{{frozen\_expectation\_packet}}이다. 범위는 네 canonical fact ID({", ".join(_latex(value) for value in packet["scope"]["canonical_fact_ids"])})와 행위자 \texttt{{{_latex(packet["scope"]["eligible_actor_ids"][0])}}}뿐이다. 규칙 ID: {", ".join(_latex(key) for key in sorted(rules))}; 승인 template은 \texttt{{mira-safe-deflection-v1}} 및 \texttt{{sl-rc-003-authorized-hint}}뿐이다.

Python evaluator는 같은 사례·기대 객체를 세 격리 arm에 materialize하고 semantic outcome, check trace, error, 전후 state SHA-256, template ID, replay equality를 기록한다. Godot은 별도 game-execution 경계에서 기존 \texttt{{reveal\_hint}} writer와 canonical mutation을 소유하며, 이 producer는 state를 재구성하거나 대체하지 않는다. 연결은 operation \texttt{{reveal\_hint}}, scenario \texttt{{{_latex(packet["scope"]["scenario_id"])}}}, actor \texttt{{{_latex(packet["scope"]["eligible_actor_ids"][0])}}}, bound source hash로 추적한다.
{mismatch_note}

표~\ref{{tab:disclosure-arms}}는 같은 {counts["total"]}개 사례의 세 arm을 정상/경계/잘못된 입력 분모로 보고하며, unchecked 위반은 의도된 격리 관측이다. {arm_equality_ko} {fixture_limit_ko} 이는 공유 동결 규칙 아래 authorization-conformance limit이며 일반적 ontology equivalence 또는 ontology superiority의 증거가 아니다. 그림~\ref{{fig:disclosure-signals}}는 E/R(기대 일치·재생 사례), C(check-record PASS/FAIL), NR(보고된 check가 없는 사례)를 구별한다. NR은 skipped/pass/out-of-scope가 아니다. 표~\ref{{tab:disclosure-fixtures}}는 rule-change fixture와 paired case를 disposable clone에 매핑하며 shipped scenario는 바꾸지 않는다.

주장은 bounded engineering conformance에 한정된다. human gold, access-separated holdout, efficacy, superiority, generalization, player benefit, model latent state, cost는 주장하지 않는다. 정확한 입력 경로·hash·재생성 명령은 \path{{paper/latex/generated/disclosure_producer_manifest.json}}에 결속된다."""
        ).strip() + "\n"
    mismatch_note = (
        f"Execution-observed hashes match the current source. {len(source_mismatches)} source hash(es) differ from the frozen baseline "
        f"({mismatch_paths}); the packet hash is preserved and the difference is disclosed."
    )
    return (
        rf"""\subsection{{Frozen \texttt{{reveal\_hint}} contract and disclosure evidence}}
Only the frozen expectation packet \texttt{{{_latex(packet["packet_id"])}}} (v{_latex(packet["packet_version"])}) and four result files are consumed. Packet SHA-256 \texttt{{{digest}}} was checked against its sidecar. The declared normal stratum has {counts["normal"]} cases under \texttt{{{_latex(packet["scope"]["normal_denominator_formula"])}}}; boundary {counts["boundary"]} and malformed {counts["malformed"]} are excluded. Trace expectations match packet case IDs, not gate output.

Content-first explanation maps typed input (operation, actor, fact, stage, knowledge, prior disclosure) through ontology entities/relations and authored rules to checks, an allowed/denied decision, and canonical state effect. A permitted first display adds only the requested fact (plus the declared relationship-memory entry for the tide hint), preserves stage, and increments revision once; denial/redisplay preserves canonical state. Explanatory only: no hidden facts, natural-language implications, or live capture.

Runtime declaration: \texttt{{{_latex_code(ontology.get("ontology_id", f"{packet['packet_id']}:runtime-disclosure"))}}} / v{_latex(ontology.get("ontology_version", packet["packet_version"]))}, provenance \texttt{{frozen\_expectation\_packet}}. Scope contains only four canonical fact IDs ({", ".join(_latex(value) for value in packet["scope"]["canonical_fact_ids"])}) and eligible actor \texttt{{{_latex(packet["scope"]["eligible_actor_ids"][0])}}}. Rule IDs: {", ".join(_latex(key) for key in sorted(rules))}; approved templates only \texttt{{mira-safe-deflection-v1}} and \texttt{{sl-rc-003-authorized-hint}}.

Python evaluator materializes the same cases/expectation object in three isolated arms, recording semantic outcomes, check traces, errors, before/after state SHA-256, rendered template IDs, and replay equality. Godot separately owns the existing \texttt{{reveal\_hint}} writer and canonical mutation at the game-execution boundary; this producer neither reconstructs nor replaces Godot state. Traceability binds operation \texttt{{reveal\_hint}}, scenario \texttt{{{_latex(packet["scope"]["scenario_id"])}}}, actor \texttt{{{_latex(packet["scope"]["eligible_actor_ids"][0])}}}, and bound source hashes.
{mismatch_note}

Table~\ref{{tab:disclosure-arms}} reports the three arms over the same {counts["total"]} cases with separate normal/boundary/malformed denominators; unchecked violations are intentional isolated observations. {arm_equality_en} {fixture_limit_en} This bounds authorization conformance under the shared frozen rules, not general ontology equivalence or ontology superiority. Figure~\ref{{fig:disclosure-signals}} distinguishes E/R (expected-match/replay cases), C (check-record PASS/FAIL), and NR (cases with no reported checks); NR is not skipped, pass, or out-of-scope. Table~\ref{{tab:disclosure-fixtures}} maps rule-change fixtures and paired cases to disposable policy clones; the shipped scenario is unchanged.

Claims are limited to bounded engineering conformance: no human gold labels, access-separated holdout, efficacy, superiority, generalization, player benefit, model latent state, or cost. Exact input paths, hashes, and reproduction commands are bound by \path{{paper/latex/generated/disclosure_producer_manifest.json}}."""
    ).strip() + "\n"


def _contract_table(data: dict[str, Any], korean: bool) -> str:
    packet = data["packet"]
    ontology = data["metadata"].get("runtime_ontology") or {}
    labels = (
        [
            "Operation / 연산",
            "Scenario / 시나리오",
            "Normal denominator / 정상 분모",
            "Boundary / 경계",
            "Malformed / 잘못된 입력",
            "Canonical facts / 정형 사실",
            "Eligible actor / 적격 행위자",
            "Ontology / 온톨로지",
            "Rule IDs / 규칙 ID",
            "Templates / 템플릿",
        ]
        if korean
        else [
            "Operation",
            "Scenario",
            "Normal denominator",
            "Boundary",
            "Malformed",
            "Canonical facts",
            "Eligible actor",
            "Ontology",
            "Rule IDs",
            "Templates",
        ]
    )
    values = [
        packet["scope"]["operation"],
        packet["scope"]["scenario_id"],
        packet["scope"]["normal_denominator"],
        len(packet["boundary_cases"]),
        len(packet["malformed_cases"]),
        ", ".join(packet["scope"]["canonical_fact_ids"]),
        ", ".join(packet["scope"]["eligible_actor_ids"]),
        ontology.get("ontology_id", _ontology_label(data)),
        ", ".join(sorted(packet["rule_ids"])),
        "mira-safe-deflection-v1; sl-rc-003-authorized-hint",
    ]
    rows = list(zip(labels, values))
    caption = (
        r"동결된 reveal\_hint 계약의 구조·내용·규칙 ID와 실제 결과 provenance."
        if korean
        else r"Frozen reveal\_hint contract structure, content, rule IDs, and result provenance."
    )
    header = (
        r"\textbf{Field / 항목} & \textbf{Value / 값}"
        if korean
        else r"\textbf{Field} & \textbf{Value}"
    )
    body = "\n".join(
        _latex(key) + " & " + _latex(value).replace(r"\_", r"\_\allowbreak{}") + r" \\"
        for key, value in rows
    )
    note = (
        "기대값은 gate 출력에서 유도하지 않았고, 표의 분모는 동결 선언에서 읽었다."
        if korean
        else "Expectations are not derived from gate output; denominators are read from the frozen declaration."
    )
    return rf"""\begin{{table}}[t]
\caption{{{caption}}}
\label{{tab:disclosure-contract}}
\centering\scriptsize
\setlength{{\tabcolsep}}{{4pt}}
\renewcommand{{\arraystretch}}{{1.20}}
\begin{{tabularx}}{{\columnwidth}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.32\columnwidth}} >{{\raggedright\arraybackslash}}X@{{}}}}
\toprule
{header} \\
\midrule
{body}
\bottomrule
\end{{tabularx}}
\par\vspace{{3pt}}\noindent\parbox{{0.97\columnwidth}}{{\scriptsize {_latex(note)}}}
\end{{table}}
"""


def _arms_table(data: dict[str, Any], korean: bool) -> str:
    counts = data["comparison"]["case_counts"]
    metrics = data["comparison"]["arms"]
    caption = (
        "세 disclosure arm의 raw trace 관측 계수; 정상/경계/잘못된 입력 분모를 분리한다."
        if korean
        else "Raw-trace observations for the three disclosure arms with separate normal, boundary, and malformed denominators."
    )
    header = (
        r"\textbf{Arm} & $\boldsymbol{n}$ \textbf{(N/B/M)} & \textbf{Allow/Deny} & \textbf{Semantic mismatch} & \textbf{State/Display fail} & \textbf{Replay fail} & \textbf{Unique unsafe} "
        + r"\\"
    )
    rows = []
    for arm in ARMS:
        values = metrics[arm]
        rows.append(
            f"{_latex(arm)} & {values['normal_case_count']}/{counts['boundary']}/{counts['malformed']} & "
            f"{values['allowed_count']}/{values['denied_count']} & {values['expected_mismatch_count']} & "
            f"{values['state_assertion_failure_count']}/{values['display_assertion_failure_count']} & "
            f"{values['replay_mismatch_count']} & {values['unsafe_violation_count']} " + r"\\"
        )
    note = (
        "N/B/M = normal/boundary/malformed. 의미 불일치는 전체 기대 결과와의 차이이고, 고유 위험 사례는 무허가 허용 또는 재표시 상태 변경의 합집합이다. 허용된 최초 공개의 표현 불일치만으로 위험 사례에 포함하지 않는다. 무검사군은 격리된 관측이며 효능·우월성·일반화 결과가 아니다."
        if korean
        else "N/B/M = normal/boundary/malformed. Semantic mismatch compares the complete expected outcome; unique unsafe cases are the union of unauthorized allows and redisplay mutations. Permitted fresh-disclosure representation mismatches alone are not unsafe. Unchecked observations do not establish efficacy, superiority, or generalization."
    )
    return rf"""\begin{{table*}}[t]
\caption{{{caption}}}
\label{{tab:disclosure-arms}}
\centering\scriptsize
\setlength{{\tabcolsep}}{{4pt}}
\renewcommand{{\arraystretch}}{{1.20}}
\begin{{tabularx}}{{\textwidth}}{{@{{}}l r r >{{\raggedleft\arraybackslash}}X >{{\raggedleft\arraybackslash}}X r r@{{}}}}
\toprule
{header}
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabularx}}
\par\vspace{{3pt}}\noindent\parbox{{0.97\textwidth}}{{\scriptsize {_latex(note)}}}
\end{{table*}}
"""


def _fixtures_table(data: dict[str, Any], korean: bool) -> str:
    fixtures = data["comparison"]["rule_change_comparison"]["fixtures"]
    caption = (
        "규칙 변경 fixture의 paired-case traceability와 수정 범위; shipped scenario는 변경하지 않는다."
        if korean
        else "Rule-change fixture traceability and edit scope for paired cases; the shipped scenario is not modified."
    )
    header = (
        r"\textbf{Fixture} & \textbf{Mutation} & \textbf{Paired cases} & \textbf{Changed paths} & \textbf{Missed cases} & \textbf{Match} "
        + r"\\"
    )
    rows = []
    for fixture in fixtures:
        mutation = fixture["mutation"]
        mutation_label = (
            _latex(f"{mutation.get('path')} {mutation.get('from')}→{mutation.get('to')}")
            .replace(r"\_", r"\_\allowbreak{}")
            .replace("→", r"$\to$")
        )
        changed_paths = (
            _latex(", ".join(fixture.get("observed_changed_paths", [])))
            .replace(r"\_", r"\_\allowbreak{}")
            .replace(".", r".\allowbreak{}")
        )
        rows.append(
            f"{_latex(fixture['fixture_id'])} & {mutation_label} & "
            f"{_latex(', '.join(fixture['paired_case_ids']))} & "
            f"{changed_paths} & "
            f"{_latex(', '.join(fixture.get('missed_case_ids', [])) or 'none')} & "
            f"{_latex('PASS' if fixture.get('all_pairs_match') else 'FAIL')} " + r"\\"
        )
    note = (
        "두 fixture는 general_rule과 ontology_gate에 같은 변경을 적용한다. missed case가 없고 mutation_scope_preserved가 true인 경우만 PASS이다."
        if korean
        else "Each fixture applies the same mutation to general_rule and ontology_gate. PASS requires no missed case and mutation_scope_preserved=true."
    )
    return rf"""\begin{{table*}}[t]
\caption{{{caption}}}
\label{{tab:disclosure-fixtures}}
\centering\scriptsize
\setlength{{\tabcolsep}}{{4pt}}
\renewcommand{{\arraystretch}}{{1.20}}
\begin{{tabularx}}{{\textwidth}}{{@{{}}>{{\raggedright\arraybackslash}}p{{0.19\textwidth}} >{{\raggedright\arraybackslash}}X >{{\raggedright\arraybackslash}}p{{0.11\textwidth}} >{{\raggedright\arraybackslash}}X >{{\raggedright\arraybackslash}}p{{0.10\textwidth}} r@{{}}}}
\toprule
{header}
\midrule
{chr(10).join(rows)}
\bottomrule
\end{{tabularx}}
\par\vspace{{3pt}}\noindent\parbox{{0.97\textwidth}}{{\scriptsize {_latex(note)}}}
\end{{table*}}
"""


def _svg(data: dict[str, Any]) -> str:
    cells = _signal_cells(data["rows"])
    width, height = 600, 1220
    arm_labels = {"unchecked_isolated": "U", "general_rule": "G", "ontology_gate": "O"}
    strata_labels = {
        "normal": ("N", "normal"),
        "boundary": ("B", "boundary"),
        "malformed": ("M", "malformed"),
    }
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="svg-title svg-desc" data-paper-label="fig:disclosure-signals">',
        '<title id="svg-title">reveal_hint external disclosure signals / 외부 공개 신호</title>',
        '<desc id="svg-desc">Source: disclosure-trace.jsonl. Arms: U=unchecked_isolated, G=general_rule, O=ontology_gate. E/R count expected-match/replay cases. C counts PASS/FAIL check records; NR counts cases with no reported checks (unreported_cases), not skipped checks. Each cell retains its own case denominator. These are engineering observations, not model latent state or efficacy measures.</desc>',
        "<style>text{font-family:Helvetica,Arial,sans-serif;fill:#202124}.title{font-size:32px;font-weight:700}.arm{font-size:32px;font-weight:700}.head{font-size:28px}.cell{font-size:28px}.small{font-size:28px;fill:#45494E}.border{stroke:#AAB0B6;stroke-width:1;fill:none}</style>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="16" y="44" class="title">EXTERNAL TRACE COUNTS</text>',
    ]
    x0, y0 = 16, 72
    arm_w, cell_w, row_h, head_h = 64, 168, 216, 108
    inset, first_baseline, line_step = 16, 44, 36
    for index, (_, stratum_name) in enumerate(STRATA):
        x = x0 + arm_w + index * cell_w
        parts.append(f'<rect x="{x}" y="{y0}" width="{cell_w}" height="{head_h}" fill="#EAF4F8"/>')
        code, label = strata_labels[stratum_name]
        parts.append(
            f'<text x="{x + cell_w / 2:g}" y="{y0 + 40}" class="head" text-anchor="middle"><tspan>{escape(code)}</tspan><tspan x="{x + cell_w / 2:g}" dy="{line_step}">{escape(label)}</tspan></text>'
        )
    for row_index, arm in enumerate(ARMS):
        y = y0 + head_h + row_index * row_h
        parts.append(f'<rect x="{x0}" y="{y}" width="{arm_w}" height="{row_h}" fill="#EAF4F8"/>')
        parts.append(
            f'<text x="{x0 + arm_w / 2:g}" y="{y + row_h / 2 + 12:g}" class="arm" text-anchor="middle">{arm_labels[arm]}</text>'
        )
        for col_index, (_, stratum_name) in enumerate(STRATA):
            x = x0 + arm_w + col_index * cell_w
            cell = cells[arm][stratum_name]
            parts.append(f'<g data-arm="{arm}" data-stratum="{stratum_name}">')
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w}" height="{row_h}" fill="#F4F5F6" class="border"/>'
            )
            parts.append(
                f'<text x="{x + inset}" y="{y + first_baseline}" class="cell"><tspan>E {cell["expected"]["pass"]}/{cell["expected"]["fail"]}</tspan><tspan x="{x + inset}" dy="{line_step}">n={cell["n"]}</tspan></text>'
            )
            parts.append(
                f'<text x="{x + inset}" y="{y + first_baseline + 2 * line_step}" class="cell">R {cell["replay"]["pass"]}/{cell["replay"]["fail"]}</text>'
            )
            parts.append(
                f'<text x="{x + inset}" y="{y + first_baseline + 3 * line_step}" class="cell"><tspan>C {cell["checks"]["pass"]}/{cell["checks"]["fail"]}</tspan><tspan x="{x + inset}" dy="{line_step}">NR {cell["checks"]["unreported_cases"]}</tspan></text>'
            )
            parts.append("</g>")
    grid_bottom = y0 + head_h + len(ARMS) * row_h
    footer_y = grid_bottom + first_baseline
    footer_gap = 12
    parts += [
        f'<path d="M{x0} {y0} L{x0 + arm_w + 3 * cell_w} {y0} L{x0 + arm_w + 3 * cell_w} {grid_bottom} L{x0} {grid_bottom} L{x0} {y0}" class="border connector"/>',
        f'<text x="{x0}" y="{footer_y}" class="small"><tspan>U unchecked_isolated ·</tspan><tspan x="{x0}" dy="{line_step}">G general_rule ·</tspan><tspan x="{x0}" dy="{line_step}">O ontology_gate</tspan></text>',
        f'<text x="{x0}" y="{footer_y + 3 * line_step + footer_gap}" class="small"><tspan>E expected P/F (n cases) ·</tspan><tspan x="{x0}" dy="{line_step}">R replay P/F</tspan></text>',
        f'<text x="{x0}" y="{footer_y + 5 * line_step + 2 * footer_gap}" class="small"><tspan>C records P/F ·</tspan><tspan x="{x0}" dy="{line_step}">NR cases with no reported checks</tspan></text>',
        f'<text x="{x0}" y="{footer_y + 7 * line_step + 3 * footer_gap}" class="small"><tspan>P pass · F fail; NR unreported,</tspan><tspan x="{x0}" dy="{line_step}">not pass/skipped/out-of-scope.</tspan></text>',
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def _convert_figure(svg_path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="disclosure-figure-") as temp_dir:
        temp = Path(temp_dir)
        png_tmp = temp / "figure.png"
        eps_tmp = temp / "figure.eps"
        pdf_tmp = temp / "figure.pdf"
        try:
            subprocess.run(
                ["rsvg-convert", "-f", "png", "-o", str(png_tmp), str(svg_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["rsvg-convert", "-f", "eps", "-o", str(eps_tmp), str(svg_path)],
                check=True,
                capture_output=True,
                text=True,
            )
            with eps_tmp.open("a", encoding="utf-8") as handle:
                handle.write(f"\n[ /Title (source-sha256:{_sha(svg_path)}) /DOCINFO pdfmark\n")
            subprocess.run(
                [
                    "ps2pdf",
                    "-dEPSCrop",
                    "-dOmitInfoDate=true",
                    "-dOmitID=true",
                    "-dOmitXMP=true",
                    str(eps_tmp),
                    str(pdf_tmp),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise ValueError(f"required figure converter unavailable: {exc.filename}") from exc
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"figure conversion failed: {exc.stderr or exc.stdout}") from exc
        (FIGURES / "fig_disclosure_signals.png").write_bytes(png_tmp.read_bytes())
        (FIGURES / "fig_disclosure_signals.pdf").write_bytes(pdf_tmp.read_bytes())


def main() -> None:
    data = _load()
    OUT.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    outputs = {
        "results_en": OUT / "disclosure_results_en.tex",
        "results_ko": OUT / "disclosure_results_ko.tex",
        "tables_en": OUT / "disclosure_tables_en.tex",
        "tables_ko": OUT / "disclosure_tables_ko.tex",
        "figure_svg": FIGURES / "fig_disclosure_signals.svg",
    }
    outputs["results_en"].write_text(_narrative(data, korean=False), encoding="utf-8", newline="\n")
    outputs["results_ko"].write_text(_narrative(data, korean=True), encoding="utf-8", newline="\n")
    outputs["tables_en"].write_text(
        _contract_table(data, korean=False)
        + _arms_table(data, korean=False)
        + _fixtures_table(data, korean=False),
        encoding="utf-8",
        newline="\n",
    )
    outputs["tables_ko"].write_text(
        _contract_table(data, korean=True)
        + _arms_table(data, korean=True)
        + _fixtures_table(data, korean=True),
        encoding="utf-8",
        newline="\n",
    )
    outputs["figure_svg"].write_text(_svg(data), encoding="utf-8", newline="\n")
    _convert_figure(outputs["figure_svg"])
    manifest = OUT / "disclosure_producer_manifest.json"
    manifest_payload = {
        "producer": "scripts/generate_disclosure_paper_results.py",
        "contract": "disclosure-paper-producer/v1",
        "packet_id": data["packet"]["packet_id"],
        "packet_version": data["packet"]["packet_version"],
        "packet_sha256": data["packet_sha"],
        "inputs": {key: str(path.relative_to(ROOT)) for key, path in data["inputs"].items()},
        "input_sha256": {key: _sha(path) for key, path in data["inputs"].items()},
        "outputs": {key: str(path.relative_to(ROOT)) for key, path in outputs.items()}
        | {
            "figure_png": "paper/latex/figures/fig_disclosure_signals.png",
            "figure_pdf": "paper/latex/figures/fig_disclosure_signals.pdf",
        },
        "labels": [
            "tab:disclosure-contract",
            "tab:disclosure-arms",
            "tab:disclosure-fixtures",
            "fig:disclosure-signals",
        ],
        "case_counts": data["comparison"]["case_counts"],
        "arms": list(ARMS),
        "claim_boundary": data["comparison"].get("claim_boundary", {}),
        "source_hash_mismatches_from_frozen_baseline": data["metadata"].get(
            "source_hash_mismatches", {}
        ),
        "public_source_substitution": verify_publication_sources(
            ROOT,
            data["metadata"]["source_hashes"],
            data["packet"],
            public_source_bindings=data["metadata"].get("public_source_bindings"),
        ),
        "observation_scope": "publication materialization from current r5 deterministic Python and Godot artifacts; no new model observation",
        "six_deliverables": {
            "ontology_contract": {
                "source": "research/npc-disclosure/reveal-hint-expectations-v1.json",
                "source_fields": [
                    "scope",
                    "rule_ids",
                    "approved_templates",
                    "integration_contract",
                ],
                "outputs": [
                    "paper/latex/generated/disclosure_tables_en.tex#tab:disclosure-contract",
                    "paper/latex/generated/disclosure_tables_ko.tex#tab:disclosure-contract",
                ],
            },
            "python_godot_boundary": {
                "source": [
                    "src/nesy_game/disclosure.py",
                    "game-track/godot/scripts/sealed_lighthouse_machine.gd",
                ],
                "outputs": [
                    "paper/latex/generated/disclosure_results_en.tex",
                    "paper/latex/generated/disclosure_results_ko.tex",
                ],
                "boundary": "Python evaluates the frozen contract; Godot owns game execution and state mutation.",
            },
            "raw_backed_signals": {
                "source": str((RESULTS / TRACE_NAME).relative_to(ROOT)),
                "outputs": [
                    "paper/latex/figures/fig_disclosure_signals.svg",
                    "paper/latex/figures/fig_disclosure_signals.png",
                    "paper/latex/figures/fig_disclosure_signals.pdf",
                ],
                "label": "fig:disclosure-signals",
                "legend": ["PASS", "FAIL", "NR: cases with no reported checks"],
            },
            "three_arm_comparison": {
                "source": str((RESULTS / SUMMARY_NAME).relative_to(ROOT)),
                "outputs": [
                    "paper/latex/generated/disclosure_tables_en.tex#tab:disclosure-arms",
                    "paper/latex/generated/disclosure_tables_ko.tex#tab:disclosure-arms",
                ],
                "arms": list(ARMS),
            },
            "paired_manuscripts": {
                "outputs": [
                    "paper/latex/generated/disclosure_results_en.tex",
                    "paper/latex/generated/disclosure_results_ko.tex",
                    "paper/latex/generated/disclosure_tables_en.tex",
                    "paper/latex/generated/disclosure_tables_ko.tex",
                ],
                "labels": [
                    "tab:disclosure-contract",
                    "tab:disclosure-arms",
                    "tab:disclosure-fixtures",
                    "fig:disclosure-signals",
                ],
            },
            "game_fixture_mapping": {
                "source": [
                    str(PACKET.relative_to(ROOT)),
                    str((RESULTS / SUMMARY_NAME).relative_to(ROOT)),
                    "game-track/godot/data/sealed_lighthouse.json",
                ],
                "outputs": [
                    "paper/latex/generated/disclosure_tables_en.tex#tab:disclosure-fixtures",
                    "paper/latex/generated/disclosure_tables_ko.tex#tab:disclosure-fixtures",
                ],
                "operation": "reveal_hint",
                "fixture_count": len(data["packet"]["rule_change_fixtures"]),
                "paired_case_count": sum(
                    len(fixture["paired_case_ids"])
                    for fixture in data["packet"]["rule_change_fixtures"]
                ),
            },
        },
        "regenerate_command": "cd neuro-symbolic-interactive-game-research-2026 && uv run python scripts/generate_disclosure_paper_results.py",
        "check_command": "cd neuro-symbolic-interactive-game-research-2026 && sha256sum research/npc-disclosure/reveal-hint-expectations-v1.json && uv run python scripts/generate_disclosure_paper_results.py",
    }
    manifest.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "outputs": {key: str(path.relative_to(ROOT)) for key, path in outputs.items()},
                "manifest": str(manifest.relative_to(ROOT)),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
