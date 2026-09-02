#!/usr/bin/env python3
"""Validate contribution, reference-topic, and evidence-lane crosswalks."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from nesy_game.validator import VALIDATOR_CHECKS

ROOT = Path(__file__).parents[1]
PIPELINE = ROOT / "research/academic-pipeline"
CONTRIBUTIONS = PIPELINE / "contribution-evidence-matrix.csv"
REFERENCES = PIPELINE / "reference-topic-crosswalk.csv"
EXPERIMENTS = PIPELINE / "experiment-evidence-matrix.csv"
REPORT = PIPELINE / "contribution-reference-crosscheck.md"
BIBLIOGRAPHY = ROOT / "paper/latex/references.bib"
CITATION_AUDIT = PIPELINE / "stage-05-citation-verification.json"
CLAIM_LEDGER = ROOT / "research/claim-ledger.yaml"
LIVE_PILOT_PLAN = ROOT / "research/directions/rq2-live-pilot-plan.md"

CONTRIBUTION_IDS = {f"C{index}" for index in range(1, 6)}
LANE_IDS = {"E1", "E2", "E3", "ENG1"}
RESULT_CLAIMS = {f"C-RESULT-00{index}" for index in range(1, 6)}
TOPIC_IDS = {f"T{index}" for index in range(1, 10)}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _pipe(value: str) -> list[str]:
    return [item for item in value.split("|") if item]


def _bib_entries(text: str) -> dict[str, str]:
    starts = list(re.finditer(r"^@(\w+)\{([^,]+),", text, flags=re.MULTILINE))
    entries: dict[str, str] = {}
    for index, match in enumerate(starts):
        key = match.group(2)
        if key == "TRACE_RPG_BST_control":
            continue
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        body = text[match.start() : end]
        title_match = re.search(r"(?:^|\n)\s*title\s*=\s*\{", body, flags=re.IGNORECASE)
        if title_match is None:
            raise ValueError(f"missing braced title for {key}")
        cursor = title_match.end()
        depth = 1
        title_end = cursor
        while title_end < len(body) and depth:
            if body[title_end] == "{":
                depth += 1
            elif body[title_end] == "}":
                depth -= 1
            title_end += 1
        if depth:
            raise ValueError(f"unbalanced title for {key}")
        title = body[cursor : title_end - 1]
        title = re.sub(r"[{}]", "", title).replace(r"\&", "&")
        entries[key] = " ".join(title.split())
    return entries


def _citation_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(r"\\cite\{([^}]+)\}", tex):
        keys.update(key.strip() for key in match.group(1).split(","))
    return keys


def _assert_paths(rows: list[dict[str, str]], field: str) -> None:
    for row in rows:
        row_id = row.get("contribution_id") or row.get("evidence_lane_id") or "unknown"
        for relative in _pipe(row[field]):
            if not (ROOT / relative).exists():
                raise ValueError(f"{row_id} points to missing evidence: {relative}")


def _validate_headline_sources(experiment_rows: dict[str, dict[str, str]]) -> None:
    pilot = json.loads((PIPELINE / "stage-04-pilot/pilot-results.json").read_text(encoding="utf-8"))
    gate = pilot["gate_conformance"]["raw_counts"]
    if (gate["passed_fixture_count"], gate["fixture_count"]) != (13, 13):
        raise ValueError("E1 gate headline drift")
    arm_commits = {
        row["arm_id"]: row["commit_count"] for row in pilot["repair_arms"]["raw_counts_by_arm"]
    }
    if arm_commits != {
        "rejection_only": 0,
        "unchanged_retry": 0,
        "guided_repair": 5,
        "structured_repair": 6,
    }:
        raise ValueError(f"E1 repair headline drift: {arm_commits!r}")
    e1_headline = experiment_rows["E1"]["headline_observation"]
    for token in ("13/13", "0/12 rejection", "0/12 blind", "5/12 rho", "6/12 oracle"):
        if token not in e1_headline:
            raise ValueError(f"E1 matrix omits source-backed token: {token}")

    live_paths = (
        "frozen-pilot-base/policy_visible/summary.json",
        "frozen-pilot-base/policy_blind/summary.json",
        "frozen-pilot-base/goal_directed_blind/summary.json",
        "signal-repair-v2/policy_visible/summary.json",
        "signal-repair-v2/policy_blind/summary.json",
    )
    live_root = PIPELINE / "rq2-live-pilot"
    live = [json.loads((live_root / path).read_text(encoding="utf-8")) for path in live_paths]
    promotion = json.loads((live_root / "promotion-manifest.json").read_text(encoding="utf-8"))
    if promotion["supported_claim_ids"] != ["C-PILOT-007", "C-PILOT-008"]:
        raise ValueError("E2 supported-claim boundary drift")
    if promotion["excluded_claim_ids"] != ["C-RESULT-003"]:
        raise ValueError("E2 excluded-claim boundary drift")
    receipt_files = promotion["files"]
    if len(receipt_files) != 14:
        raise ValueError(f"E2 promotion manifest must bind 14 receipts, found {len(receipt_files)}")
    summary_paths = sorted(path for path in receipt_files if path.endswith("/summary.json"))
    result_paths = sorted(path for path in receipt_files if path.endswith("/results.jsonl"))
    if len(summary_paths) != 7 or len(result_paths) != 7:
        raise ValueError("E2 promotion manifest must bind seven summary/result pairs")
    for relative, receipt in receipt_files.items():
        payload = (live_root / relative).read_bytes()
        if len(payload) != receipt["bytes"]:
            raise ValueError(f"E2 receipt byte-count drift: {relative}")
        if hashlib.sha256(payload).hexdigest() != receipt["sha256"]:
            raise ValueError(f"E2 receipt SHA-256 drift: {relative}")
    for summary_path in summary_paths:
        result_path = summary_path.replace("/summary.json", "/results.jsonl")
        if result_path not in receipt_files:
            raise ValueError(f"E2 summary lacks a bound JSONL pair: {summary_path}")
        summary = json.loads((live_root / summary_path).read_text(encoding="utf-8"))
        rows = [
            json.loads(line)
            for line in (live_root / result_path).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if summary["repair_budget"] != 1:
            raise ValueError(f"E2 summary no longer uses K=1: {summary_path}")
        if (
            summary["counts"]["seeds"] != 5
            or summary["counts"]["proposals_returned"] != 5
            or summary["counts"]["adapter_failures"] != 0
            or len(rows) != 5
        ):
            raise ValueError(f"E2 summary/result cardinality drift: {summary_path}")
        if {row["seed"] for row in rows} != {11, 23, 47, 83, 131}:
            raise ValueError(f"E2 exact seed-set drift: {result_path}")
        if {row["status"] for row in rows} != {"proposed"}:
            raise ValueError(f"E2 row-status drift: {result_path}")
        if any(set(row["arms"]) != {"guided_repair", "unchanged_retry"} for row in rows):
            raise ValueError(f"E2 paired-arm contract drift: {result_path}")
        if not summary["matched_candidate_per_seed"]:
            raise ValueError(f"E2 matched-candidate contract drift: {summary_path}")
    plan = LIVE_PILOT_PLAN.read_text(encoding="utf-8")
    if "`1+K=4`" in plan or "`K=1`" not in plan or "`1+K=2`" not in plan:
        raise ValueError("E2 live plan disagrees with the frozen K=1 receipts")
    target = live[-1]
    signature = (
        target["counts"]["initially_invalid"],
        target["per_arm"]["guided_repair"]["commits"],
        target["per_arm"]["unchanged_retry"]["commits"],
    )
    if signature != (5, 5, 0):
        raise ValueError(f"E2 target-cell headline drift: {signature!r}")
    noncommits = sum(arm["non_commits"] for summary in live for arm in summary["per_arm"].values())
    isolated = sum(
        arm["non_commit_state_isolated"] for summary in live for arm in summary["per_arm"].values()
    )
    if (isolated, noncommits) != (15, 15):
        raise ValueError(f"E2 state-isolation headline drift: {(isolated, noncommits)!r}")
    e2_row = experiment_rows["E2"]
    if "K=1" not in e2_row["unit_or_budget"]:
        raise ValueError("E2 matrix omits the frozen K=1 budget")
    e2_headline = e2_row["headline_observation"]
    for token in ("5/5 initial", "rho committed 5/5", "blind 0/5", "15/15"):
        if token not in e2_headline:
            raise ValueError(f"E2 matrix omits source-backed token: {token}")

    kg = json.loads(
        (ROOT / "research/simulation/kg-ontology/latest/evaluation-matrix.json").read_text(
            encoding="utf-8"
        )
    )
    retained = next(row for row in kg["trials"] if row["decision"] == "keep")
    metrics = retained["metrics"]
    kg_signature = (
        metrics["precision"],
        metrics["recall"],
        metrics["f1"],
        round(metrics["mrr_realistic"], 3),
        round(metrics["brier_score"], 3),
        metrics["semantic_at_k"],
    )
    if kg_signature != (1, 1, 1, 0.944, 0.131, 1):
        raise ValueError(f"E3 metric headline drift: {kg_signature!r}")

    game = json.loads(
        (ROOT / "game-track/godot/docs/latest/evaluation-matrix.json").read_text(encoding="utf-8")
    )
    balance = json.loads(
        (ROOT / "game-track/godot/docs/latest/balance-archetypes.json").read_text(encoding="utf-8")
    )
    totals = game["totals"]
    game_signature = (
        totals["fixtures_passed"],
        totals["fixtures_total"],
        totals["combined_checks_passed"],
        totals["combined_checks_total"],
        balance["aggregates"]["archetype_count"],
        balance["passed"],
    )
    if game_signature != (4, 4, 52, 52, 5, True):
        raise ValueError(f"ENG1 headline drift: {game_signature!r}")


def main() -> None:
    bibliography = _bib_entries(BIBLIOGRAPHY.read_text(encoding="utf-8"))
    bib_keys = set(bibliography)
    if len(bib_keys) != 55:
        raise ValueError(f"expected 55 paper references, found {len(bib_keys)}")

    audit = json.loads(CITATION_AUDIT.read_text(encoding="utf-8"))
    audit_by_key = {entry["key"]: entry for entry in audit["entries"]}
    if set(audit_by_key) != bib_keys:
        raise ValueError("Stage-5 citation keys do not equal bibliography keys")
    status_counts = Counter(entry["status"] for entry in audit["entries"])
    rate_limited = sum(bool(entry["rate_limited_indices"]) for entry in audit["entries"])
    if status_counts != {"VERIFIED": 48, "PREPRINT": 7} or rate_limited != 22:
        raise ValueError(
            f"Stage-5 citation totals drift: status={status_counts!r}, rate_limited={rate_limited}"
        )

    reference_rows = _read_csv(REFERENCES)
    reference_by_key = {row["bib_key"]: row for row in reference_rows}
    if len(reference_rows) != 55 or set(reference_by_key) != bib_keys:
        raise ValueError("reference-topic crosswalk must cover each bibliography key exactly once")
    if {row["primary_topic_id"] for row in reference_rows} != TOPIC_IDS:
        raise ValueError("reference-topic crosswalk must exercise T1 through T9")
    for key, row in reference_by_key.items():
        if row["title"] != bibliography[key]:
            raise ValueError(f"title drift for {key}")
        if row["publication_status"] != audit_by_key[key]["status"]:
            raise ValueError(f"publication-status drift for {key}")
        if row["reference_id"] != key.split("_", maxsplit=1)[0]:
            raise ValueError(f"reference-id drift for {key}")
        tokens = set(_pipe(row["contribution_or_boundary"]))
        if not tokens or not tokens <= CONTRIBUTION_IDS | {"BOUNDARY-FUTURE"}:
            raise ValueError(f"invalid contribution mapping for {key}: {tokens!r}")

    manuscript_texts = {
        language: (ROOT / f"paper/latex/{language}/main.tex").read_text(encoding="utf-8")
        for language in ("en", "ko")
    }
    if len(VALIDATOR_CHECKS) != 7:
        raise ValueError(f"paper check-count contract drift: {VALIDATOR_CHECKS!r}")
    validator_count_markers = {
        "en": ("seven deterministic checks", "six state-relative families"),
        "ko": ("일곱 개의 결정론적 검사", "여섯 상태 상대 계열"),
    }
    for language, tex in manuscript_texts.items():
        for marker in validator_count_markers[language]:
            if marker not in tex:
                raise ValueError(f"{language} manuscript lacks validator-count marker: {marker}")
        cited = _citation_keys(tex)
        if cited != bib_keys:
            missing = sorted(bib_keys - cited)
            extra = sorted(cited - bib_keys)
            raise ValueError(
                f"{language} citation coverage drift: missing={missing}, extra={extra}"
            )
        for contribution_id in sorted(CONTRIBUTION_IDS):
            if rf"\textbf{{{contribution_id}---" not in tex:
                raise ValueError(f"{language} manuscript lacks marker {contribution_id}")
        for lane_id in ("E1", "E2", "E3"):
            if rf"\textbf{{{lane_id}}}" not in tex:
                raise ValueError(f"{language} manuscript lacks evidence-lane marker {lane_id}")
        if r"\textbf{ENG1.}" not in tex:
            raise ValueError(f"{language} manuscript lacks evidence-lane marker ENG1")
        availability_marker = {
            "en": "machine-checked contribution, reference-topic, and experiment matrices",
            "ko": "기계 검증 기여·참조 주제·실험 매트릭스",
        }[language]
        if availability_marker not in tex:
            raise ValueError(
                f"{language} data-availability text omits the machine-checked matrices"
            )

    claim_ids = set(
        re.findall(r"^\s*- id:\s*(\S+)\s*$", CLAIM_LEDGER.read_text(encoding="utf-8"), re.MULTILINE)
    )
    if not RESULT_CLAIMS <= claim_ids:
        raise ValueError("claim ledger no longer contains all C-RESULT claim IDs")

    contribution_rows = _read_csv(CONTRIBUTIONS)
    contribution_by_id = {row["contribution_id"]: row for row in contribution_rows}
    if len(contribution_rows) != 5 or set(contribution_by_id) != CONTRIBUTION_IDS:
        raise ValueError("contribution matrix must contain exactly C1 through C5")
    _assert_paths(contribution_rows, "evidence_paths")
    for contribution_id, row in contribution_by_id.items():
        forward_references = set(_pipe(row["reference_keys"]))
        if not forward_references <= bib_keys:
            raise ValueError(f"{contribution_id} contains an unknown reference key")
        reverse_references = {
            key
            for key, reference in reference_by_key.items()
            if contribution_id in _pipe(reference["contribution_or_boundary"])
        }
        if forward_references != reverse_references:
            raise ValueError(
                f"{contribution_id} forward/reverse reference drift: "
                f"forward_only={sorted(forward_references - reverse_references)}, "
                f"reverse_only={sorted(reverse_references - forward_references)}"
            )
        declared_topics = set(_pipe(row["prior_topic_ids"]))
        referenced_topics = {
            reference_by_key[key]["primary_topic_id"] for key in forward_references
        }
        if declared_topics != referenced_topics:
            raise ValueError(
                f"{contribution_id} topic/reference drift: "
                f"declared_only={sorted(declared_topics - referenced_topics)}, "
                f"referenced_only={sorted(referenced_topics - declared_topics)}"
            )
        if not set(_pipe(row["claim_ids"])) <= claim_ids:
            raise ValueError(f"{contribution_id} contains an unknown claim ID")
        if not set(_pipe(row["evidence_lane_ids"])) <= LANE_IDS:
            raise ValueError(f"{contribution_id} contains an unknown evidence lane")
        if "efficacy" in row["evidence_status"].lower():
            raise ValueError(f"{contribution_id} improperly claims efficacy")
    c2_mechanism = contribution_by_id["C2"]["manuscript_claim"]
    for marker in ("Seven deterministic checks", "six state-relative families"):
        if marker not in c2_mechanism:
            raise ValueError(f"C2 matrix lacks validator-count marker: {marker}")

    experiment_rows = _read_csv(EXPERIMENTS)
    experiment_by_id = {row["evidence_lane_id"]: row for row in experiment_rows}
    if len(experiment_rows) != 4 or set(experiment_by_id) != LANE_IDS:
        raise ValueError("experiment matrix must contain E1, E2, E3, and ENG1 exactly once")
    _assert_paths(experiment_rows, "evidence_paths")
    for lane_id, row in experiment_by_id.items():
        supporting = set(_pipe(row["supporting_claim_ids"]))
        prohibited = set(_pipe(row["prohibited_claim_ids"]))
        if not supporting <= claim_ids or not prohibited <= claim_ids:
            raise ValueError(f"{lane_id} contains an unknown claim ID")
        if supporting & RESULT_CLAIMS:
            raise ValueError(f"{lane_id} improperly promotes a C-RESULT claim")
        if prohibited != RESULT_CLAIMS:
            raise ValueError(f"{lane_id} must explicitly prohibit every C-RESULT claim")
    _validate_headline_sources(experiment_by_id)

    report = REPORT.read_text(encoding="utf-8")
    for identifier in sorted(CONTRIBUTION_IDS | LANE_IDS | TOPIC_IDS):
        if identifier not in report:
            raise ValueError(f"crosscheck report omits {identifier}")

    print(
        "contribution/reference crosswalk passed: "
        "5 contributions, 55 references, 9 topics, 3 experiment lanes + 1 engineering lane"
    )


if __name__ == "__main__":
    main()
