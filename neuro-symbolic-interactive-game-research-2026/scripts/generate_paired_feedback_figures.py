#!/usr/bin/env python3
"""Generate the v5 paired-selector development figures from frozen results.

Two SVGs are derived from the privacy-safe ``results.json`` projections under
``research/codex_feedback_pilot/public-v5/``:

* ``fig_state_signal.svg`` (diagram): the state signal that one assignment shows
  the requested selector before repair (detailed structured error set versus the
  generic rejection message) and the deterministic path after the response.
* ``fig_paired_feedback_flow.svg`` (chart): the aggregate collection flow and the
  per-fixture outcome matrix with per-cell counts.

Counts, signal fields, error codes and elapsed values come from the results;
stage names and boundary notes are authored. ``--check`` detects SVG drift without
writing. ``--export-public`` derives public inputs from local immutable raw cohorts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_paper_figures as gpf

RAW_COHORT_ROOT = ROOT / "research" / "codex_feedback_pilot"
COHORT_ROOT = RAW_COHORT_ROOT / "public-v5"
COHORT_PREFIX = "paired-model-comparison-20261110-v5-"
SELECTORS = ("gpt-5.6-luna", "gpt-5.6-terra")
CONDITIONS = ("detailed", "generic")
FIGURES = ROOT / "paper" / "latex" / "figures"
STATE_SIGNAL_SVG = FIGURES / "fig_state_signal.svg"
FLOW_SVG = FIGURES / "fig_paired_feedback_flow.svg"
GENERIC_MESSAGE = "Action rejected."
OBJECTIVE_FACT = "signal_restored"
SCHEMA_FAILURE = "CandidateParseError"
AUTHORIZED_FIXTURES = (
    "missing_precondition",
    "missing_effect",
    "forbidden_disclosure",
    "unsatisfied_dependency",
)
CONFLICT_FIXTURE = "unauthorized_objective"

# Outcome classes: letter, long label, fill, stroke.
OUTCOMES = {
    "goal": ("G", "goal reached: committed, fact present", gpf.PALE_GREEN, gpf.GREEN),
    "gate": ("A", "gate accepted, goal missed", gpf.PALE_BLUE, gpf.BLUE),
    "fallback": ("F", "rejected, state unchanged", gpf.PALE_ORANGE, gpf.ORANGE),
    "schema": ("S", "schema failure, no candidate", gpf.PALE_GRAY, gpf.GRAY),
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


EXPECTED_CHECKS = (
    "action_policy",
    "precondition",
    "object_reachability",
    "npc_knowledge",
    "forbidden_disclosure",
    "quest_stage",
    "quest_stage_monotonicity",
)
ERROR_KEYS = frozenset({"code", "entity", "reason", "repair_hint"})
SUMMARY_KEYS = frozenset(
    {"assigned", "completed", "failed", "pending", "gate_accepted", "objective_reached"}
)


def mapping(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label}: expected an object")
    return value


def read_json(path: Path) -> tuple[Any, str]:
    """Read once so the parsed document and its recorded digest are the same bytes."""
    try:
        raw = path.read_bytes()
        return json.loads(raw.decode("utf-8")), hashlib.sha256(raw).hexdigest()
    except (OSError, ValueError) as exc:
        raise ValueError(f"unreadable results input: {path}: {exc}") from exc


def classify(row: dict[str, Any]) -> str:
    case_id = row["case_id"]
    failure = row.get("failure")
    evaluation = row.get("evaluation")
    if row.get("status") == "FAILED":
        require(evaluation is None, f"{case_id}: failed row carries an evaluation")
        require(
            mapping(failure, f"{case_id}: failure").get("type") == SCHEMA_FAILURE,
            f"{case_id}: unexpected failure type",
        )
        return "schema"
    require(row.get("status") == "COMPLETED", f"{case_id}: unexpected status")
    require(failure is None, f"{case_id}: completed row carries a failure")
    evaluation = mapping(evaluation, f"{case_id}: evaluation")
    require(
        evaluation.get("identity_preserved") is True
        and evaluation.get("initial_state_unchanged") is True,
        f"{case_id}: identity or initial state not preserved",
    )
    trace = evaluation.get("trace")
    require(
        isinstance(trace, list) and len(trace) == 1 and bool(evaluation.get("trace_hash")),
        f"{case_id}: repair budget 0 requires exactly one trace attempt",
    )
    committed = evaluation.get("outcome") == "commit"
    accepted = evaluation.get("final_gate_accepted")
    reached = evaluation.get("objective_reached")
    require(
        isinstance(accepted, bool) and isinstance(reached, bool), f"{case_id}: flags not boolean"
    )
    if committed:
        require(accepted is True, f"{case_id}: commit without gate acceptance")
        facts = mapping(evaluation.get("final_state"), f"{case_id}: final_state").get("facts")
        require(isinstance(facts, list), f"{case_id}: final facts missing")
        require(
            reached == (OBJECTIVE_FACT in facts), f"{case_id}: objective flag disagrees with facts"
        )
        return "goal" if reached else "gate"
    require(
        evaluation.get("outcome") == "fallback"
        and accepted is False
        and reached is False
        and evaluation.get("fallback_state_unchanged") is True,
        f"{case_id}: unexpected outcome",
    )
    return "fallback"


def _check_detailed_signal(case_id: str, signal: dict[str, Any]) -> tuple[str, tuple[str, ...]]:
    require(set(signal) == {"valid", "checks_run", "errors"}, f"{case_id}: detailed signal fields")
    require(signal["valid"] is False, f"{case_id}: detailed signal must be invalid")
    checks = signal["checks_run"]
    require(
        isinstance(checks, list) and tuple(checks) == EXPECTED_CHECKS,
        f"{case_id}: checks_run must be the seven expected checks in order",
    )
    errors = signal["errors"]
    require(isinstance(errors, list) and len(errors) == 1, f"{case_id}: expected one error")
    error = mapping(errors[0], f"{case_id}: error")
    require(
        set(error) == ERROR_KEYS, f"{case_id}: error must carry code, entity, reason, repair_hint"
    )
    require(
        all(isinstance(error[key], str) and error[key] for key in ERROR_KEYS),
        f"{case_id}: error fields must be non-empty strings",
    )
    return error["code"], tuple(checks)


def _row_digest(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_cohorts(cohort_root: Path) -> dict[str, Any]:
    cells: dict[tuple[str, str], dict[str, Any]] = {}
    fixtures: list[str] | None = None
    codes: dict[str, str] = {}
    detailed_signals: dict[str, dict[str, Any]] = {}
    pair_inputs: dict[str, str] = {}
    prompts: dict[tuple[str, str], str] = {}
    sources: dict[str, str] = {}
    retained_rows: list[dict[str, Any]] = []
    retained_metadata: dict[str, Any] = {}
    row_receipts: dict[str, Any] = {}
    for selector in SELECTORS:
        results_path = cohort_root / f"{COHORT_PREFIX}{selector}" / "results.json"
        doc, digest = read_json(results_path)
        sources[str(results_path.relative_to(ROOT))] = digest
        doc = mapping(doc, str(results_path))
        metadata = mapping(doc.get("metadata"), f"{selector}: metadata")
        require(metadata.get("model_selector") == selector, f"{selector}: selector mismatch")
        require(
            metadata.get("actual_model_identity") is None and metadata.get("cost_usd") is None,
            f"{selector}: served identity or cost must be unreported",
        )
        rows = doc.get("cases")
        require(isinstance(rows, list), f"{selector}: cases must be a list")
        require(len(rows) == 10, f"{selector}: expected 10 assignments, found {len(rows)}")
        for row in rows:
            mapping(row, f"{selector}: row")
            require(
                isinstance(row.get("case_id"), str) and row.get("condition") in CONDITIONS,
                f"{selector}: row without case_id or known condition",
            )
        require(
            len({(row["case_id"], row["condition"]) for row in rows}) == 10,
            f"{selector}: duplicate case/condition assignment",
        )
        summaries = mapping(doc.get("summary"), f"{selector}: summary")
        for condition in CONDITIONS:
            subset = [row for row in rows if row["condition"] == condition]
            ids = [row["case_id"] for row in subset]
            require(
                len(subset) == 5 and len(set(ids)) == 5,
                f"{selector}/{condition}: expected 5 unique cases",
            )
            if fixtures is None:
                fixtures = list(ids)
            require(
                set(ids) == set(fixtures),
                f"{selector}/{condition}: fixture set differs from paired set",
            )
            outcomes = {}
            for row in subset:
                case_id = row["case_id"]
                evidence = mapping(row.get("evidence"), f"{case_id}: evidence")
                stdout = mapping(evidence.get("stdout"), f"{case_id}: stdout")
                require(
                    type(evidence.get("returncode")) is int
                    and evidence["returncode"] == 0
                    and stdout.get("complete") is True,
                    f"{selector}/{condition}/{case_id}: response receipt incomplete",
                )
                events = evidence.get("events")
                require(
                    isinstance(events, list) and bool(events), f"{case_id}: terminal events missing"
                )
                event_types = [mapping(event, f"{case_id}: event").get("type") for event in events]
                require(
                    event_types[-1] == "turn.completed"
                    and event_types.count("turn.started")
                    == event_types.count("turn.completed")
                    == 1,
                    f"{case_id}: incomplete or duplicate terminal envelope",
                )
                if row.get("status") == "COMPLETED":
                    require(
                        isinstance(row.get("response_text"), str)
                        and bool(row["response_text"].strip()),
                        f"{case_id}: completed response text missing",
                    )
                elapsed = evidence.get("elapsed_seconds")
                require(
                    type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0,
                    f"{case_id}: elapsed_seconds must be finite and non-negative",
                )
                # Paired inputs: one state and proposal per fixture across conditions and selectors.
                for key in ("initial_state", "shared_proposal"):
                    require(
                        bool(mapping(row.get(key), f"{case_id}: {key}")), f"{case_id}: {key} empty"
                    )
                pair = json.dumps(
                    [row.get("initial_state"), row.get("shared_proposal")], sort_keys=True
                )
                require(
                    pair_inputs.setdefault(case_id, pair) == pair,
                    f"{case_id}: initial_state/shared_proposal differ across the paired assignments",
                )
                require(
                    isinstance(row.get("prompt_sha256"), str)
                    and row["prompt_sha256"]
                    and row.get("prompt_file") == f"{case_id}-{condition}.prompt.txt",
                    f"{case_id}/{condition}: prompt receipt malformed",
                )
                require(
                    prompts.setdefault((case_id, condition), row["prompt_sha256"])
                    == row["prompt_sha256"],
                    f"{case_id}/{condition}: prompt differs across selectors",
                )
                signal = mapping(row.get("input_signal"), f"{case_id}: input_signal")
                if condition == "detailed":
                    code, _checks = _check_detailed_signal(case_id, signal)
                    require(
                        detailed_signals.setdefault(case_id, signal) == signal,
                        f"{case_id}: detailed signal differs across selectors",
                    )
                    codes[case_id] = code
                else:
                    require(
                        signal.get("valid") is False
                        and signal == {"valid": False, "message": GENERIC_MESSAGE},
                        f"{case_id}: generic signal drift",
                    )
                outcomes[case_id] = {
                    "class": classify(row),
                    "elapsed_seconds": round(float(elapsed), 1),
                }
            require(len(outcomes) == 5, f"{selector}/{condition}: collapsed outcomes")
            summary = mapping(summaries.get(condition), f"{selector}/{condition}: summary")
            require(set(summary) == SUMMARY_KEYS, f"{selector}/{condition}: summary fields")
            require(
                all(type(value) is int and value >= 0 for value in summary.values()),
                f"{selector}/{condition}: summary counts must be non-negative integers",
            )
            counts = {
                "assigned": len(subset),
                "received": len(subset),
                "parsed": sum(1 for item in outcomes.values() if item["class"] != "schema"),
                "gate": sum(1 for item in outcomes.values() if item["class"] in {"goal", "gate"}),
                "goal": sum(1 for item in outcomes.values() if item["class"] == "goal"),
                "schema": sum(1 for item in outcomes.values() if item["class"] == "schema"),
            }
            require(summary["assigned"] == counts["assigned"], "summary assigned drift")
            require(summary["completed"] == counts["parsed"], "summary completed drift")
            require(summary["failed"] == counts["schema"], "summary failed drift")
            require(summary["gate_accepted"] == counts["gate"], "summary gate drift")
            require(summary["objective_reached"] == counts["goal"], "summary objective drift")
            require(summary["pending"] == 0, "pending assignments remain")
            cells[(selector, condition)] = {"counts": counts, "outcomes": outcomes}
        retained_metadata[selector] = metadata
        row_receipts[str(results_path.relative_to(ROOT))] = {
            "sha256": digest,
            "rows": {f"/cases/{i}": _row_digest(row) for i, row in enumerate(rows)},
        }
        retained_rows.extend(
            {
                **row,
                "selector": selector,
                "source": str(results_path.relative_to(ROOT)),
                "pointer": f"/cases/{index}",
            }
            for index, row in enumerate(rows)
        )
    require(
        fixtures is not None and len(fixtures) == 5, f"expected five fixtures, found {fixtures}"
    )
    totals = {
        key: sum(cell["counts"][key] for cell in cells.values())
        for key in ("assigned", "received", "parsed", "gate", "goal", "schema")
    }
    return {
        "cells": cells,
        "fixtures": fixtures,
        "codes": codes,
        "checks": list(EXPECTED_CHECKS),
        "totals": totals,
        "sources": sources,
        "rows": retained_rows,
        "metadata": retained_metadata,
        "row_receipts": row_receipts,
    }


def load_cohorts(cohort_root: Path | None = None) -> dict[str, Any]:
    """Load the frozen cohorts; any malformed shape is a ValueError, never a partial render."""
    try:
        return _load_cohorts(COHORT_ROOT if cohort_root is None else cohort_root)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError(f"malformed results input: {type(exc).__name__}: {exc}") from exc


def describe_v5_strata(cohorts: dict[str, Any]) -> dict[str, Any]:
    """Describe retained assignments without IO, replay, or changing frozen endpoints."""
    try:
        return _describe_v5_strata(cohorts)
    except (KeyError, TypeError, AttributeError, IndexError) as exc:
        raise ValueError(f"malformed v5 strata evidence: {type(exc).__name__}: {exc}") from exc


def _describe_v5_strata(cohorts: dict[str, Any]) -> dict[str, Any]:
    raw_rows = cohorts["rows"]
    require(isinstance(raw_rows, list) and len(raw_rows) == 20, "expected 20 retained rows")
    fixture_ids = {*AUTHORIZED_FIXTURES, CONFLICT_FIXTURE}
    expected = {(s, c, f) for s in SELECTORS for c in CONDITIONS for f in fixture_ids}
    keys = [(r["selector"], r["condition"], r["case_id"]) for r in raw_rows]
    require(
        len(set(keys)) == 20 and set(keys) == expected, "missing, duplicate or unknown assignment"
    )
    sources = mapping(cohorts["sources"], "strata sources")
    require(len(sources) == 2, "expected two source receipts")
    require(
        all(
            isinstance(d, str) and len(d) == 64 and set(d) <= set("0123456789abcdef")
            for d in sources.values()
        ),
        "malformed source digest",
    )
    pairs: dict[str, Any] = {}
    rows = []
    for raw in raw_rows:
        selector, condition, case_id = raw["selector"], raw["condition"], raw["case_id"]
        source = raw["source"]
        require(
            source in sources and source.endswith(f"{COHORT_PREFIX}{selector}/results.json"),
            f"{case_id}: missing source receipt",
        )
        pointer = raw["pointer"]
        require(pointer in {f"/cases/{i}" for i in range(10)}, f"{case_id}: bad source pointer")
        receipt = cohorts["row_receipts"][source]
        require(receipt["sha256"] == sources[source], f"{case_id}: source digest mismatch")
        retained = {k: v for k, v in raw.items() if k not in {"selector", "source", "pointer"}}
        require(
            _row_digest(retained) == receipt["rows"][pointer],
            f"{case_id}: retained row/source pointer mismatch",
        )
        state = mapping(raw["initial_state"], f"{case_id}: initial state")
        proposal = mapping(raw["shared_proposal"], f"{case_id}: proposal")
        pair = [state, proposal]
        require(pairs.setdefault(case_id, pair) == pair, f"{case_id}: paired input drift")
        allowed = state["action_policies"]["signal"]["allowed_effects"]
        conflict = case_id == CONFLICT_FIXTURE
        require(
            isinstance(allowed, list)
            and (allowed == [] if conflict else OBJECTIVE_FACT in allowed),
            f"{case_id}: stratum policy contradiction",
        )
        require(
            isinstance(state["facts"], list) and OBJECTIVE_FACT not in state["facts"],
            f"{case_id}: initial goal already present",
        )
        # Reconstruct the archived prompt bytes, not live collector code; no prompt-file IO.
        payload = {
            "state": state,
            "candidate": proposal,
            "validator_feedback": raw["input_signal"],
            "objective": "commit with signal_restored in final facts",
        }
        prompt = (
            "Repair this fictional game action. Return only one JSON object with exactly the same candidate fields, no markdown. "
            "Keep action_id, actor_id and action_type unchanged. Do not use tools or network.\n"
            + json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        )
        require(
            hashlib.sha256(prompt.encode("utf-8")).hexdigest() == raw["prompt_sha256"],
            f"{case_id}: prompt digest/payload mismatch",
        )
        evidence = raw["evidence"]
        events = [event["type"] for event in evidence["events"]]
        require(
            type(evidence["returncode"]) is int
            and evidence["returncode"] == 0
            and evidence["stdout"]["complete"] is True
            and events[-1] == "turn.completed"
            and events.count("turn.started") == events.count("turn.completed") == 1,
            f"{case_id}: unsuccessful response receipt",
        )
        outcome = classify(raw)
        require(
            outcome == cohorts["cells"][(selector, condition)]["outcomes"][case_id]["class"],
            f"{case_id}: retained outcome/cell mismatch",
        )
        evaluation = raw["evaluation"]
        final_facts = final_effects = errors = unchanged = None
        if evaluation is not None:
            final_state = mapping(evaluation["final_state"], f"{case_id}: final state")
            final_facts = final_state["facts"]
            final_effects = evaluation["final_candidate"]["effects"]
            require(
                isinstance(final_facts, list) and isinstance(final_effects, list),
                f"{case_id}: malformed final facts/effects",
            )
            unchanged = state == final_state
            require(outcome != "fallback" or unchanged, f"{case_id}: fallback state changed")
            require(
                outcome == "fallback" or set(final_effects) <= set(allowed),
                f"{case_id}: commit violates effect policy",
            )
            validation = evaluation["validation"]
            require(
                validation["valid"] is evaluation["final_gate_accepted"],
                f"{case_id}: validation/acceptance contradiction",
            )
            errors = [error["code"] for error in validation["errors"]]
        rows.append(
            {
                "selector": selector,
                "condition": condition,
                "case_id": case_id,
                "stratum": "negative_control_conflict" if conflict else "authorized_progress",
                "source": source,
                "pointer": pointer,
                "prompt_sha256": raw["prompt_sha256"],
                "collection_status": raw["status"],
                "failure_type": raw["failure"]["type"] if raw["failure"] else None,
                "runtime_outcome": evaluation["outcome"] if evaluation else None,
                "observation": {
                    "goal": "COMMITTED_GOAL",
                    "gate": "COMMITTED_NO_GOAL",
                    "fallback": "HOLD_FALLBACK",
                    "schema": "UNKNOWN_SCHEMA_FAILURE",
                }[outcome],
                "gate_accepted_observed": evaluation["final_gate_accepted"] if evaluation else None,
                "goal_reached_observed": evaluation["objective_reached"] if evaluation else None,
                "assigned_gate_success": outcome in {"goal", "gate"},
                "assigned_goal_success": outcome == "goal",
                "fallback_state_unchanged": evaluation["fallback_state_unchanged"]
                if evaluation
                else None,
                "full_final_state_unchanged": unchanged,
                "state_id_changed": state["state_id"] != final_state["state_id"]
                if evaluation
                else None,
                "forbidden_goal_suppressed_observed": OBJECTIVE_FACT not in final_facts
                if conflict and evaluation
                else None,
                "final_effects": list(final_effects) if final_effects is not None else None,
                "final_facts": list(final_facts) if final_facts is not None else None,
                "error_codes": errors,
            }
        )
    groups = []
    for selector in SELECTORS:
        assigned = sorted(
            (r for r in raw_rows if r["selector"] == selector), key=lambda r: r["pointer"]
        )
        require(
            len({r["source"] for r in assigned}) == 1
            and len({r["pointer"] for r in assigned}) == 10,
            "duplicate source pointer",
        )
        metadata = cohorts["metadata"][selector]
        require(
            metadata["objective"] == "gate commits and final facts contain signal_restored",
            "frozen objective drift",
        )
        fixtures = [
            {"state": r["initial_state"], "proposal": r["shared_proposal"]}
            for r in assigned
            if r["condition"] == "detailed"
        ]
        digest = hashlib.sha256(
            json.dumps(fixtures, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        require(digest == metadata["fixture_sha256"], "fixture digest mismatch")
        for condition in CONDITIONS:
            subset = [r for r in rows if r["selector"] == selector and r["condition"] == condition]
            counts = _strata_outcome_counts(subset)
            original = {
                "assigned": 5,
                "received": 5,
                "parsed": 5 - counts["schema_unknown"],
                "gate_accepted": counts["committed_goal"] + counts["committed_no_goal"],
                "goal_reached": counts["committed_goal"],
                "schema_failures": counts["schema_unknown"],
                **counts,
            }
            frozen = cohorts["cells"][(selector, condition)]["counts"]
            for new, old in (
                ("assigned", "assigned"),
                ("received", "received"),
                ("parsed", "parsed"),
                ("gate_accepted", "gate"),
                ("goal_reached", "goal"),
                ("schema_failures", "schema"),
            ):
                require(
                    original[new] == frozen[old], f"{selector}/{condition}: original count drift"
                )
            authorized = [r for r in subset if r["stratum"] == "authorized_progress"]
            controls = [r for r in subset if r["stratum"] == "negative_control_conflict"]
            observed = sum(r["runtime_outcome"] is not None for r in controls)
            confirmed = sum(r["forbidden_goal_suppressed_observed"] is True for r in controls)
            groups.append(
                {
                    "selector": selector,
                    "condition": condition,
                    "original_all_five": original,
                    "authorized_progress": {
                        "assigned_denominator": len(authorized),
                        "goal_numerator": sum(r["assigned_goal_success"] for r in authorized),
                        **_strata_outcome_counts(authorized),
                    },
                    "negative_control_conflict": {
                        "assigned_denominator": len(controls),
                        "confirmed_suppression_count": confirmed,
                        "observed_outcome_count": observed,
                        "unassessed_count": len(controls) - observed,
                        "observed_only_fraction": {"numerator": confirmed, "denominator": observed}
                        if observed
                        else None,
                        "forbidden_goal_reached_observed_count": sum(
                            r["goal_reached_observed"] is True for r in controls
                        ),
                        **{
                            k: v
                            for k, v in _strata_outcome_counts(controls).items()
                            if k != "committed_goal"
                        },
                    },
                }
            )
    for new, old in (
        ("assigned", "assigned"),
        ("received", "received"),
        ("parsed", "parsed"),
        ("gate_accepted", "gate"),
        ("goal_reached", "goal"),
        ("schema_failures", "schema"),
    ):
        require(
            sum(g["original_all_five"][new] for g in groups) == cohorts["totals"][old],
            f"original total drift: {old}",
        )
    return {
        "scope": {
            "stratification": "POST_HOC_DESCRIPTIVE_ONLY",
            "preregistered_endpoint": False,
            "frozen_denominators_modified": False,
        },
        "rows": rows,
        "groups": groups,
        "sources": dict(sources),
    }


def _strata_outcome_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        name: sum(row["observation"] == observation for row in rows)
        for name, observation in (
            ("committed_goal", "COMMITTED_GOAL"),
            ("committed_no_goal", "COMMITTED_NO_GOAL"),
            ("hold_fallback", "HOLD_FALLBACK"),
            ("schema_unknown", "UNKNOWN_SCHEMA_FAILURE"),
        )
    }


def render_v5_strata_tex(description: dict[str, Any], language: str = "en") -> str:
    """Render both language tables from the same computed descriptive record."""
    require(language in {"en", "ko"}, "unsupported strata table language")
    ko = language == "ko"
    caption = (
        "변경하지 않은 v5 배정 5개를 사후 기술적으로 분할한 표. 사전등록 분석이나 독립 코호트가 아니며 대체 평가변수가 아니다. Terra 대조군은 파싱 실패 후 미평가이다."
        if ko
        else "Post-hoc descriptive partition of the unchanged five-fixture v5 assignments; not preregistered, not an independent cohort, and not a replacement endpoint. Terra controls are unassessed after parser failure."
    )
    headings = (
        "요청 selector & 신호 & 원래 목표 /5 & 허가된 목표 /4 & 대조군 처리 /1"
        if ko
        else "Requested selector & Signal & Original goal /5 & Authorized goal /4 & Control handling /1"
    )
    lines = [
        r"\begin{table*}[t]",
        r"\caption{" + caption + "}",
        r"\label{tab:paired-feedback-strata}",
        r"\centering\footnotesize",
        r"\setlength{\tabcolsep}{4pt}",
        r"\renewcommand{\arraystretch}{1.15}",
        r"\begin{tabularx}{\textwidth}{@{}llcc>{\raggedright\arraybackslash}X@{}}",
        r"\toprule",
        headings + r" \\",
        r"\midrule",
    ]
    for group in description["groups"]:
        original = group["original_all_five"]
        authorized = group["authorized_progress"]
        control = group["negative_control_conflict"]
        if control["unassessed_count"]:
            handling = (
                "미평가" if ko else "unassessed"
            ) + f" {control['unassessed_count']}/1 (schema unknown)"
        else:
            (row,) = (
                r
                for r in description["rows"]
                if r["selector"] == group["selector"]
                and r["condition"] == group["condition"]
                and r["stratum"] == "negative_control_conflict"
            )
            if control["committed_no_goal"]:
                effects = "no effects" if row["final_effects"] == [] else "effects retained"
                state_id = "changed" if row["state_id_changed"] else "unchanged"
                outcome = f"COMMIT ({effects}; state ID {state_id})"
            else:
                require(
                    row["observation"] == "HOLD_FALLBACK"
                    and row["full_final_state_unchanged"] is True,
                    "control is neither an observed no-goal commit nor unchanged fallback",
                )
                outcome = "HOLD (fallback; state unchanged)"
            suppression = "금지 목표 억제" if ko else "forbidden goal suppressed"
            handling = f"{suppression} {control['confirmed_suppression_count']}/1; {outcome}"
        signal = (
            {"detailed": "상세", "generic": "일반"}[group["condition"]]
            if ko
            else group["condition"]
        )
        lines.append(
            f"{group['selector']} & {signal} & {original['goal_reached']}/5 & "
            f"{authorized['goal_numerator']}/4 & {handling}" + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabularx}", r"\end{table*}"])
    return "\n".join(lines) + "\n"


def export_public(raw_root: Path | None = None, public_root: Path | None = None) -> None:
    """Project local raw receipts without changing their bytes or case outcomes."""
    raw_root = RAW_COHORT_ROOT if raw_root is None else raw_root
    public_root = COHORT_ROOT if public_root is None else public_root
    require(raw_root.resolve() != public_root.resolve(), "public root must differ from raw root")
    load_cohorts(raw_root)
    pending: list[tuple[Path, bytes]] = []
    protected_inputs: set[Path] = set()
    for selector in SELECTORS:
        directory = f"{COHORT_PREFIX}{selector}"
        source = raw_root / directory / "results.json"
        doc, digest = read_json(source)
        protected_inputs.add(source)
        protected_inputs.add(source.parent / "approved_results.json")
        doc["metadata"]["codex_executable"] = None
        doc["public_projection"] = {
            "schema": "paired-feedback-public-projection/1",
            "raw_source_sha256": digest,
            "omitted_fields": ["metadata.codex_executable"],
            "reason": "Local executable path omitted; outcomes and executable hash/version retained.",
        }
        destination = public_root / directory
        pending.append(
            (
                destination / "results.json",
                (json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
                    "utf-8"
                ),
            )
        )
        for row in doc["cases"]:
            name = row["prompt_file"]
            require(Path(name).name == name, "prompt path must be a plain filename")
            payload = (source.parent / name).read_bytes()
            protected_inputs.add(source.parent / name)
            require(
                hashlib.sha256(payload).hexdigest() == row["prompt_sha256"],
                f"{name}: prompt hash mismatch",
            )
            pending.append((destination / name, payload))
    protected_paths = {path.resolve() for path in protected_inputs}
    protected_inodes = {
        (path.stat().st_dev, path.stat().st_ino) for path in protected_inputs if path.exists()
    }
    for path, _payload in pending:
        require(
            not path.is_symlink()
            and path.resolve().is_relative_to(public_root.resolve())
            and path.resolve() not in protected_paths,
            f"unsafe public destination: {path.name}",
        )
        if path.exists():
            require(
                (path.stat().st_dev, path.stat().st_ino) not in protected_inodes,
                f"public destination aliases raw input: {path.name}",
            )
    for path, payload in pending:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def _box(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    accent: str,
    title: str,
    lines: tuple[str, ...] = (),
    fill: str = "#FFFFFF",
    dashed: bool = False,
) -> list[str]:
    return gpf.component_box(
        x,
        y,
        width,
        height,
        accent=accent,
        title_value=title,
        body_lines=lines,
        fill=fill,
        dashed=dashed,
    )


def state_signal_svg(data: dict[str, Any]) -> str:
    items = gpf.svg_header(
        1440,
        1120,
        "State signal before repair and the deterministic path after the response",
        "A fixed state and shared invalid proposal are checked, not accepted. The requested "
        "selector receives structured detailed feedback or a generic rejection, then returns "
        "one candidate. Strict parsing and an identity check precede deterministic validation "
        "with repair budget zero. Only a valid candidate can commit; the separate objective "
        "requires signal_restored in committed facts. Source-derived schematic, not live capture.",
    )
    items += gpf.band(
        20,
        20,
        1400,
        80,
        accent=gpf.BLUE,
        title_value="STATE SIGNAL | FROM REJECTION TO A CHECKED RESPONSE",
        subtitle="One v5 assignment: the signal explains a failed check; it never authorizes a commit.",
    )
    items += _box(
        40,
        140,
        400,
        160,
        accent=gpf.GRAY,
        title="FIXED INPUT",
        lines=("same WorldState", "same invalid proposal", "same independent objective"),
        fill=gpf.PALE_GRAY,
    )
    items.append(gpf.line(440, 220, 514, 220, color=gpf.BLUE, marker="blue"))
    checks = data["checks"]
    items += _box(
        520,
        140,
        880,
        160,
        accent=gpf.BLUE,
        title="SEVEN DETERMINISTIC CHECKS",
        lines=(", ".join(checks[:3]), ", ".join(checks[3:6]), checks[6]),
        fill=gpf.PALE_BLUE,
    )
    for x, color, marker in ((360, gpf.ORANGE, "orange"), (1080, gpf.GRAY, "gray")):
        items.append(gpf.path(f"M960 300 L960 325 L{x} 325 L{x} 354", color=color, marker=marker))
    items += _box(
        40,
        360,
        640,
        160,
        accent=gpf.ORANGE,
        title="DETAILED SIGNAL",
        lines=(
            "valid: false; len(checks_run): 7",
            "errors: code, entity, reason, repair_hint",
            "structured counterexample, not permission",
        ),
        fill=gpf.PALE_ORANGE,
    )
    items += _box(
        760,
        360,
        640,
        160,
        accent=gpf.GRAY,
        title="GENERIC SIGNAL",
        lines=("valid: false", f"message: {GENERIC_MESSAGE}", "no error code or repair hint"),
        fill=gpf.PALE_GRAY,
    )
    for x, color, marker in ((360, gpf.ORANGE, "orange"), (1080, gpf.GRAY, "gray")):
        items.append(gpf.path(f"M{x} 520 L{x} 540 L720 540 L720 554", color=color, marker=marker))
    items += _box(
        40,
        560,
        1360,
        110,
        accent=gpf.BLUE,
        title="REQUESTED SELECTOR RETURNS ONE RESPONSE",
        lines=(
            "one fresh ephemeral Codex session; prompt says no tools or network; no further model call",
        ),
    )
    items.append(gpf.path("M720 670 L720 695 L230 695 L230 714", color=gpf.BLUE, marker="blue"))
    items += _box(
        40,
        720,
        380,
        140,
        accent=gpf.BLUE,
        title="PARSE + ID CHECK",
        lines=("exact candidate fields", "preserve IDs and type", "reject unknown keys"),
        fill=gpf.PALE_BLUE,
    )
    items.append(gpf.line(420, 790, 524, 790, color=gpf.BLUE, marker="blue"))
    items += _box(
        530,
        720,
        380,
        140,
        accent=gpf.BLUE,
        title="REVALIDATE",
        lines=("same seven checks", "repair budget 0", "all must pass to commit"),
        fill=gpf.PALE_BLUE,
    )
    items.append(gpf.line(910, 790, 1014, 790, color=gpf.GREEN, marker="green"))
    items += _box(
        1020,
        720,
        380,
        140,
        accent=gpf.GREEN,
        title="COMMIT",
        lines=("apply validated transition", "record trace hash", "then check the objective"),
        fill=gpf.PALE_GREEN,
    )
    items.append(gpf.line(230, 860, 230, 904, color=gpf.GRAY, marker="gray"))
    items += _box(
        40,
        910,
        380,
        140,
        accent=gpf.GRAY,
        title="INVALID RESPONSE",
        lines=(
            "schema failure or ID change",
            "no authorized transition",
            "zero gate and goal success",
        ),
        fill=gpf.PALE_GRAY,
        dashed=True,
    )
    items.append(gpf.line(720, 860, 720, 904, color=gpf.ORANGE, marker="orange"))
    items += _box(
        530,
        910,
        380,
        140,
        accent=gpf.ORANGE,
        title="REJECT / FALLBACK",
        lines=("prior state unchanged", "goal missed", "failure stays in denominator"),
        fill=gpf.PALE_ORANGE,
        dashed=True,
    )
    items.append(gpf.line(1210, 860, 1210, 904, color=gpf.GREEN, marker="green"))
    items += _box(
        1020,
        910,
        380,
        140,
        accent=gpf.GREEN,
        title="INDEPENDENT GOAL",
        lines=(
            f"{OBJECTIVE_FACT} in facts",
            "a valid commit can miss it",
            "gate is not goal success",
        ),
    )
    items.append(
        gpf.text(
            40,
            1095,
            "Authored flow from the frozen collector; signal fields from results. No hidden-state or efficacy claim.",
            css_class="note",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


def flow_svg(data: dict[str, Any]) -> str:
    totals = data["totals"]
    fixtures = data["fixtures"]
    items = gpf.svg_header(
        1440,
        1120,
        "v5 paired-selector collection flow and per-fixture outcomes",
        "Assigned, received, strictly parsed, gate-accepted and objective-reached counts "
        "include all twenty assignments. Matrix letters identify goal, accepted but goal "
        "missed, fallback or schema failure. Seconds include every terminal response, "
        "including schema failures, and measure dispatch to terminal, not model latency. "
        "The four rows report parsed/gate/goal counts out of five assigned cases each. "
        "Served identity, provider request count and cost are not reported. Error codes: "
        + "; ".join(f"{fixture}: {data['codes'][fixture]}" for fixture in fixtures),
    )
    items += gpf.band(
        20,
        20,
        1400,
        80,
        accent=gpf.GREEN,
        title_value=f"V5 DEVELOPMENT COLLECTION | {totals['assigned']} ASSIGNMENTS",
        subtitle="Five synthetic fixtures x two signal conditions x two requested selectors; no pooled prior cohort.",
    )
    stages = (
        (("ASSIGNED",), "assigned", gpf.GRAY, gpf.PALE_GRAY),
        (("RECEIVED",), "received", gpf.GRAY, gpf.PALE_GRAY),
        (("STRICTLY", "PARSED"), "parsed", gpf.BLUE, gpf.PALE_BLUE),
        (("GATE", "ACCEPTED"), "gate", gpf.BLUE, gpf.PALE_BLUE),
        (("GOAL", "REACHED"), "goal", gpf.GREEN, gpf.PALE_GREEN),
    )
    for index, (label, key, accent, fill) in enumerate(stages):
        x = 40 + index * 280
        items += _box(
            x, 130, 240, 135, accent=accent, title=str(totals[key]), lines=label, fill=fill
        )
        if index:
            items.append(gpf.line(x - 38, 195, x - 6, 195, color=accent, marker=_marker(accent)))
    items.append(
        gpf.text(
            40,
            305,
            f"{totals['schema']} schema failures; {totals['gate'] - totals['goal']} accepted commit missed the goal. Response receipt is not task success.",
            css_class="small",
        )
    )
    items.append(gpf.rect(20, 335, 1400, 580, fill=gpf.LIGHT_GRAY, radius=5))
    items.append(gpf.text(40, 375, "OUTCOME AND DISPATCH-TO-TERMINAL SECONDS", css_class="section"))
    col_x = [400 + index * 220 for index in range(len(fixtures))]
    for x, fixture in zip(col_x, fixtures):
        items.append(gpf.multiline(x, 425, fixture.split("_"), css_class="small", line_height=30))
    row_y = 485
    for selector in SELECTORS:
        for condition in CONDITIONS:
            cell = data["cells"][(selector, condition)]
            counts = cell["counts"]
            items.append(
                gpf.multiline(
                    40,
                    row_y + 25,
                    (
                        selector,
                        f"{condition} signal",
                        f"P{counts['parsed']} / A{counts['gate']} / G{counts['goal']} of {counts['assigned']}",
                    ),
                    css_class="small",
                    anchor="start",
                    line_height=30,
                )
            )
            for x, fixture in zip(col_x, fixtures):
                outcome = cell["outcomes"][fixture]
                letter, _label, fill, stroke = OUTCOMES[outcome["class"]]
                items.append(
                    f'  <rect class="data-mark outcome-mark" x="{x - 80}" y="{row_y}" width="160" height="82" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
                )
                items.append(
                    gpf.text(x, row_y + 35, letter, css_class="box-title", anchor="middle")
                )
                items.append(
                    gpf.text(
                        x,
                        row_y + 69,
                        f"{outcome['elapsed_seconds']:.1f} s",
                        css_class="small",
                        anchor="middle",
                    )
                )
            row_y += 105
    legend_positions = ((40, 960), (760, 960), (40, 1005), (760, 1005))
    for (x, y), key in zip(legend_positions, ("goal", "gate", "fallback", "schema")):
        letter, label, fill, stroke = OUTCOMES[key]
        items.append(
            f'  <rect class="data-mark legend-mark" x="{x}" y="{y - 26}" width="34" height="34" rx="5" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        )
        items.append(gpf.text(x + 46, y, f"{letter}: {label}", css_class="small"))
    items.append(
        gpf.text(
            40,
            1055,
            "Row counts: P parsed / A gate accepted / G goal reached, each out of five assigned cases.",
            css_class="note",
        )
    )
    items.append(
        gpf.text(
            40,
            1095,
            "NR: served identity, provider request count, cost. Small development-only sample; no superiority claim.",
            css_class="note",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


def _marker(color: str) -> str:
    return {gpf.BLUE: "blue", gpf.ORANGE: "orange", gpf.GREEN: "green"}.get(color, "gray")


def outputs(data: dict[str, Any]) -> dict[Path, str]:
    return {STATE_SIGNAL_SVG: state_signal_svg(data), FLOW_SVG: flow_svg(data)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check", action="store_true", help="verify generated figures and strata without rewriting"
    )
    mode.add_argument(
        "--export-public",
        action="store_true",
        help="derive privacy-safe inputs from local raw receipts, then render",
    )
    args = parser.parse_args()
    if args.export_public:
        export_public()
    data = load_cohorts()
    expected = outputs(data)
    description = describe_v5_strata(data)
    generated = ROOT / "paper" / "latex" / "generated"
    expected[generated / "paired_feedback_strata.json"] = (
        json.dumps(description, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    for language in ("en", "ko"):
        expected[generated / f"paired_feedback_strata_{language}.tex"] = render_v5_strata_tex(
            description, language=language
        )
    for path, content in expected.items():
        if path.suffix == ".svg":
            ET.fromstring(content)
        if args.check:
            require(path.is_file(), f"missing generated figure: {path}")
            require(path.read_text(encoding="utf-8") == content, f"generated figure drift: {path}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": "PASS",
                "mode": "check" if args.check else "write",
                "totals": data["totals"],
                "fixtures": data["fixtures"],
                "sources": data["sources"],
                "outputs": [str(path.relative_to(ROOT)) for path in expected],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
