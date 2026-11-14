"""Post-hoc v5 descriptions must preserve the frozen assignments and observed outcomes."""

from __future__ import annotations

import builtins
import hashlib
import importlib
import io
import json
import re
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "research" / "codex_feedback_pilot" / "public-v5"
PREFIX = "paired-model-comparison-20261110-v5-"
SELECTORS = ("gpt-5.6-luna", "gpt-5.6-terra")
CONDITIONS = ("detailed", "generic")
AUTHORIZED = {
    "missing_precondition",
    "missing_effect",
    "forbidden_disclosure",
    "unsatisfied_dependency",
}
CONFLICT = "unauthorized_objective"
ORIGINAL_METRICS = (
    "assigned",
    "received",
    "parsed",
    "gate_accepted",
    "goal_reached",
    "schema_failures",
)
ORIGINAL = {
    (SELECTORS[0], "detailed"): (5, 5, 4, 4, 3, 1),
    (SELECTORS[0], "generic"): (5, 5, 5, 3, 3, 0),
    (SELECTORS[1], "detailed"): (5, 5, 0, 0, 0, 5),
    (SELECTORS[1], "generic"): (5, 5, 1, 1, 1, 4),
}
AUTHORIZED_COUNTS = {
    (SELECTORS[0], "detailed"): (3, 0, 0, 1),
    (SELECTORS[0], "generic"): (3, 0, 1, 0),
    (SELECTORS[1], "detailed"): (0, 0, 0, 4),
    (SELECTORS[1], "generic"): (1, 0, 0, 3),
}


@pytest.fixture
def generator(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("generate_paired_feedback_figures")


@pytest.fixture
def receipts():
    # These are the already collected scientific inputs, never synthetic new samples.
    return {
        selector: json.loads((PILOT / f"{PREFIX}{selector}" / "results.json").read_text())
        for selector in SELECTORS
    }


def _key(row):
    return row["selector"], row["condition"], row["case_id"]


def _groups(description):
    return {(row["selector"], row["condition"]): row for row in description["groups"]}


def test_strata_partition_all_twenty_without_replacing_original_five_case_metrics(generator):
    cohorts = generator.load_cohorts()
    original = deepcopy(cohorts)
    description = generator.describe_v5_strata(cohorts)
    rows = description["rows"]
    assert Counter(_key(row) for row in rows) == Counter(
        (selector, condition, case_id)
        for selector in SELECTORS
        for condition in CONDITIONS
        for case_id in AUTHORIZED | {CONFLICT}
    )
    groups = _groups(description)
    assert len(description["groups"]) == 4
    assert set(groups) == set(ORIGINAL)
    for key, expected in ORIGINAL.items():
        group = groups[key]
        assert tuple(group["original_all_five"][name] for name in ORIGINAL_METRICS) == expected
        authorized = group["authorized_progress"]
        conflict = group["negative_control_conflict"]
        assert authorized["assigned_denominator"] == 4
        assert conflict["assigned_denominator"] == 1
        assert (
            tuple(
                authorized[name]
                for name in (
                    "committed_goal",
                    "committed_no_goal",
                    "hold_fallback",
                    "schema_unknown",
                )
            )
            == AUTHORIZED_COUNTS[key]
        )
        assert authorized["goal_numerator"] == expected[4]
        for field in ("committed_goal", "committed_no_goal", "hold_fallback", "schema_unknown"):
            assert authorized[field] + conflict.get(field, 0) == group["original_all_five"][field]
        cell_rows = [row for row in rows if (row["selector"], row["condition"]) == key]
        assert Counter(row["stratum"] for row in cell_rows) == {
            "authorized_progress": 4,
            "negative_control_conflict": 1,
        }
    assert cohorts == original, "The descriptive helper must not mutate its validated input"


def test_each_described_assignment_is_traceable_to_its_actual_receipt(generator, receipts):
    description = generator.describe_v5_strata(generator.load_cohorts())
    sources = description["sources"]
    for selector in SELECTORS:
        path = PILOT / f"{PREFIX}{selector}" / "results.json"
        assert sources[str(path.relative_to(ROOT))] == hashlib.sha256(path.read_bytes()).hexdigest()
    for row in description["rows"]:
        source = receipts[row["selector"]]
        index = int(row["pointer"].removeprefix("/cases/"))
        actual = source["cases"][index]
        assert (actual["case_id"], actual["condition"]) == (row["case_id"], row["condition"])
        assert row["source"] == str(
            (PILOT / f"{PREFIX}{row['selector']}" / "results.json").relative_to(ROOT)
        )
        assert row["prompt_sha256"] == actual["prompt_sha256"]
        assert row["collection_status"] == actual["status"]
        evaluation = actual["evaluation"]
        if evaluation is None:
            assert row["observation"] == "UNKNOWN_SCHEMA_FAILURE"
            assert row["failure_type"] == "CandidateParseError"
            for field in (
                "runtime_outcome",
                "gate_accepted_observed",
                "goal_reached_observed",
                "fallback_state_unchanged",
                "full_final_state_unchanged",
                "forbidden_goal_suppressed_observed",
                "final_effects",
                "final_facts",
            ):
                assert row[field] is None, (_key(row), field)
            assert row["assigned_gate_success"] is False
            assert row["assigned_goal_success"] is False
        else:
            assert row["runtime_outcome"] == evaluation["outcome"]
            assert row["gate_accepted_observed"] is evaluation["final_gate_accepted"]
            assert row["goal_reached_observed"] is evaluation["objective_reached"]
            assert row["assigned_gate_success"] is evaluation["final_gate_accepted"]
            assert row["assigned_goal_success"] is evaluation["objective_reached"]
            assert row["final_effects"] == evaluation["final_candidate"]["effects"]
            assert row["final_facts"] == evaluation["final_state"]["facts"]
            assert row["full_final_state_unchanged"] is (
                actual["initial_state"] == evaluation["final_state"]
            )
            assert row["fallback_state_unchanged"] is evaluation["fallback_state_unchanged"]


def test_no_effect_accepted_commit_is_not_hold_or_full_state_invariance(generator, receipts):
    description = generator.describe_v5_strata(generator.load_cohorts())
    rows = {_key(row): row for row in description["rows"]}
    committed = rows[(SELECTORS[0], "detailed", CONFLICT)]
    held = rows[(SELECTORS[0], "generic", CONFLICT)]
    assert committed["observation"] == "COMMITTED_NO_GOAL"
    assert committed["runtime_outcome"] == "commit"
    assert committed["gate_accepted_observed"] is True
    assert committed["goal_reached_observed"] is False
    assert committed["final_effects"] == committed["final_facts"] == []
    assert committed["forbidden_goal_suppressed_observed"] is True
    assert committed["fallback_state_unchanged"] is None
    assert committed["full_final_state_unchanged"] is False
    assert held["observation"] == "HOLD_FALLBACK"
    assert held["runtime_outcome"] == "fallback"
    assert held["gate_accepted_observed"] is False
    assert held["forbidden_goal_suppressed_observed"] is True
    assert held["fallback_state_unchanged"] is held["full_final_state_unchanged"] is True
    actual = next(
        row
        for row in receipts[SELECTORS[0]]["cases"]
        if row["case_id"] == CONFLICT and row["condition"] == "detailed"
    )
    before = actual["initial_state"]
    after = actual["evaluation"]["final_state"]
    assert before["state_id"] != after["state_id"]
    assert {key: value for key, value in before.items() if key != "state_id"} == {
        key: value for key, value in after.items() if key != "state_id"
    }


def test_only_evaluated_conflicts_receive_suppression_credit(generator):
    description = generator.describe_v5_strata(generator.load_cohorts())
    groups = _groups(description)
    for condition in CONDITIONS:
        luna = groups[(SELECTORS[0], condition)]["negative_control_conflict"]
        assert luna["confirmed_suppression_count"] == luna["observed_outcome_count"] == 1
        assert luna["unassessed_count"] == luna["schema_unknown"] == 0
        assert luna["observed_only_fraction"] == {"numerator": 1, "denominator": 1}
        assert (luna["committed_no_goal"], luna["hold_fallback"]) == (
            (1, 0) if condition == "detailed" else (0, 1)
        )
        terra = groups[(SELECTORS[1], condition)]["negative_control_conflict"]
        assert terra["confirmed_suppression_count"] == terra["observed_outcome_count"] == 0
        assert terra["unassessed_count"] == terra["schema_unknown"] == 1
        assert terra["committed_no_goal"] == terra["hold_fallback"] == 0
        assert terra["observed_only_fraction"] is None
        assert terra["forbidden_goal_reached_observed_count"] == 0
    conflict_rows = [row for row in description["rows"] if row["case_id"] == CONFLICT]
    assert sum(row["forbidden_goal_suppressed_observed"] is True for row in conflict_rows) == 2
    assert sum(row["forbidden_goal_suppressed_observed"] is None for row in conflict_rows) == 2


@pytest.mark.parametrize(
    "language,signals,unassessed",
    [
        ("en", ("detailed", "generic"), "unassessed"),
        ("ko", ("상세", "일반"), "미평가"),
    ],
)
def test_bilingual_table_renders_same_record_and_exposes_unknowns(
    generator, language, signals, unassessed
):
    description = generator.describe_v5_strata(generator.load_cohorts())
    rendered = generator.render_v5_strata_tex(description, language=language)
    table_rows = [line for line in rendered.splitlines() if any(s in line for s in SELECTORS)]
    assert len(table_rows) == 4
    groups = _groups(description)
    for selector in SELECTORS:
        for condition, signal in zip(CONDITIONS, signals):
            (line,) = [line for line in table_rows if selector in line and signal in line.lower()]
            group = groups[(selector, condition)]
            goal = group["original_all_five"]["goal_reached"]
            authorized = group["authorized_progress"]["goal_numerator"]
            fractions = re.findall(r"(\d+)\s*/\s*(\d+)", line)
            assert fractions[:2] == [(str(goal), "5"), (str(authorized), "4")]
            if selector == SELECTORS[0]:
                assert ("1", "1") in fractions[2:]
                assert ("COMMIT" if condition == "detailed" else "HOLD") in line
                assert ("HOLD" if condition == "detailed" else "COMMIT") not in line
            else:
                assert unassessed in line.lower()
                assert "HOLD" not in line and "COMMIT" not in line
    assert "\\label{tab:paired-feedback-strata}" in rendered
    if language == "en":
        assert "post-hoc" in rendered.lower() and "descriptive" in rendered.lower()
        assert "not preregistered" in rendered.lower()
        assert "not a replacement endpoint" in rendered.lower()
    else:
        assert "사후" in rendered and "기술" in rendered
        assert "사전등록" in rendered and "대체" in rendered


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "unknown_fixture",
        "missing_evaluation",
        "unknown_failure",
        "conflict_policy",
        "authorized_policy",
        "false_fallback_equality",
        "missing_final_facts",
    ],
)
def test_malformed_retained_evidence_fails_closed_instead_of_dropping_assignments(
    generator, damage
):
    cohorts = deepcopy(generator.load_cohorts())
    rows = cohorts["rows"]
    if damage == "missing":
        rows.pop()
    elif damage == "duplicate":
        rows.append(deepcopy(rows[0]))
    elif damage == "unknown_fixture":
        for row in rows:
            if row["case_id"] == CONFLICT:
                row["case_id"] = "unregistered_fixture"
    elif damage == "missing_evaluation":
        rows[0]["evaluation"] = None
    elif damage == "unknown_failure":
        row = next(row for row in rows if row["status"] == "FAILED")
        row["failure"]["type"] = "TransportError"
    elif damage in {"conflict_policy", "authorized_policy"}:
        for row in rows:
            if row["case_id"] == (CONFLICT if damage == "conflict_policy" else "missing_effect"):
                row["initial_state"]["action_policies"]["signal"]["allowed_effects"] = (
                    ["signal_restored"] if damage == "conflict_policy" else []
                )
    elif damage == "false_fallback_equality":
        row = next(
            row for row in rows if (row.get("evaluation") or {}).get("outcome") == "fallback"
        )
        row["evaluation"]["final_state"]["facts"].append("unrecorded_world_mutation")
    elif damage == "missing_final_facts":
        del rows[0]["evaluation"]["final_state"]["facts"]
    with pytest.raises(ValueError):
        generator.describe_v5_strata(cohorts)


def test_describing_and_rendering_preserve_source_bytes_hashes_and_posthoc_scope(
    generator, monkeypatch
):
    paths = sorted(PILOT.rglob("*"))
    paths.append(PILOT.parent / "paired-model-comparison-20261110-v5-source.zip")
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths if path.is_file()
    }
    real_open = io.open

    def readonly_open(file, mode="r", *args, **kwargs):
        if not isinstance(file, int):
            path = Path(file).resolve()
            if path.is_relative_to(PILOT.resolve()) or path in before:
                assert not any(flag in mode for flag in "wax+"), "Frozen inputs are read-only"
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(io, "open", readonly_open)
    monkeypatch.setattr(builtins, "open", readonly_open)
    cohorts = generator.load_cohorts()
    original = deepcopy(cohorts)
    description = generator.describe_v5_strata(cohorts)
    scope = description["scope"]
    assert scope["stratification"] == "POST_HOC_DESCRIPTIVE_ONLY"
    assert scope["preregistered_endpoint"] is False
    assert scope["frozen_denominators_modified"] is False
    assert description["sources"] == cohorts["sources"]
    record = deepcopy(description)
    for language in ("en", "ko"):
        generator.render_v5_strata_tex(description, language=language)
    assert description == record
    assert cohorts == original
    assert {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before} == before
