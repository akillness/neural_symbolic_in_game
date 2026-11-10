"""Offline accounting and fail-closed contracts for the frozen v5 figures."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import re
import socket
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "research" / "codex_feedback_pilot" / "public-v5"
PREFIX = "paired-model-comparison-20261110-v5-"
SELECTORS = ("gpt-5.6-luna", "gpt-5.6-terra")
CONDITIONS = ("detailed", "generic")
METRICS = ("assigned", "received", "parsed", "gate", "goal", "schema")
EXPECTED_COUNTS = {
    (SELECTORS[0], "detailed"): (5, 5, 4, 4, 3, 1),
    (SELECTORS[0], "generic"): (5, 5, 5, 3, 3, 0),
    (SELECTORS[1], "detailed"): (5, 5, 0, 0, 0, 5),
    (SELECTORS[1], "generic"): (5, 5, 1, 1, 1, 4),
}
EXPECTED_TOTALS = dict(zip(METRICS, (20, 20, 10, 8, 7, 10)))
EXPECTED_CODES = {
    "missing_precondition": "POLICY_PRECONDITION_OMISSION",
    "missing_effect": "POLICY_EFFECT_OMISSION",
    "unauthorized_objective": "POLICY_EFFECT_VIOLATION",
    "forbidden_disclosure": "FORBIDDEN_DISCLOSURE",
    "unsatisfied_dependency": "UNSATISFIED_PRECONDITION",
}
EXPECTED_CHECKS = [
    "action_policy",
    "precondition",
    "object_reachability",
    "npc_knowledge",
    "forbidden_disclosure",
    "quest_stage",
    "quest_stage_monotonicity",
]
SVG = "{http://www.w3.org/2000/svg}"


def _forbid_external_effect(*args, **kwargs):
    pytest.fail("Frozen figure generation must not launch inference/processes or use the network")


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    # Trap the real external boundaries rather than mocking the generator's accounting.
    monkeypatch.setattr(subprocess, "Popen", _forbid_external_effect)
    monkeypatch.setattr(os, "system", _forbid_external_effect)
    monkeypatch.setattr(socket, "create_connection", _forbid_external_effect)
    monkeypatch.setattr(socket.socket, "connect", _forbid_external_effect)
    monkeypatch.setattr(socket.socket, "connect_ex", _forbid_external_effect)


@pytest.fixture
def generator(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("generate_paired_feedback_figures")


@pytest.fixture(scope="module")
def cohorts():
    return {
        selector: json.loads((PILOT / f"{PREFIX}{selector}" / "results.json").read_text())
        for selector in SELECTORS
    }


@pytest.fixture
def workspace(tmp_path, monkeypatch, generator):
    cohort_root = tmp_path / "research" / "codex_feedback_pilot"
    paths = {}
    for selector in SELECTORS:
        source = PILOT / f"{PREFIX}{selector}" / "results.json"
        target = cohort_root / source.parent.name / source.name
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
        paths[selector] = target
    figures = tmp_path / "paper" / "latex" / "figures"
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    monkeypatch.setattr(generator, "COHORT_ROOT", cohort_root)
    monkeypatch.setattr(generator, "FIGURES", figures)
    monkeypatch.setattr(generator, "STATE_SIGNAL_SVG", figures / "fig_state_signal.svg")
    monkeypatch.setattr(generator, "FLOW_SVG", figures / "fig_paired_feedback_flow.svg")
    return paths


def _mutate(path, change):
    doc = json.loads(path.read_text())
    change(doc)
    path.write_text(json.dumps(doc), encoding="utf-8")


def _visible_text(svg):
    root = ET.fromstring(svg)
    assert root.tag == SVG + "svg"
    return [" ".join(" ".join(node.itertext()).split()) for node in root.iter(SVG + "text")]


def _tree_bytes(root):
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_frozen_counts_preserve_all_receipts_and_schema_failure_denominators(generator, cohorts):
    data = generator.load_cohorts()
    assert data["totals"] == EXPECTED_TOTALS
    assert set(data["cells"]) == set(EXPECTED_COUNTS)
    assert set(data["fixtures"]) == set(EXPECTED_CODES)
    assert data["codes"] == EXPECTED_CODES
    assert data["checks"] == EXPECTED_CHECKS
    for key, expected in EXPECTED_COUNTS.items():
        selector, condition = key
        cell = data["cells"][key]
        counts = cell["counts"]
        assert counts == dict(zip(METRICS, expected)), key
        assert set(cell["outcomes"]) == set(EXPECTED_CODES), key
        classes = Counter(outcome["class"] for outcome in cell["outcomes"].values())
        assert classes["schema"] + counts["parsed"] == counts["received"] == counts["assigned"]
        assert classes["goal"] + classes["gate"] == counts["gate"]
        assert classes["fallback"] + counts["gate"] == counts["parsed"]
        assert classes["goal"] == counts["goal"]
        for row in cohorts[selector]["cases"]:
            if row["condition"] != condition:
                continue
            outcome = cell["outcomes"][row["case_id"]]
            assert outcome["elapsed_seconds"] == round(row["evidence"]["elapsed_seconds"], 1)
            if row["status"] == "FAILED":
                assert outcome["class"] == "schema"
            elif row["evaluation"]["objective_reached"]:
                assert outcome["class"] == "goal"
            elif row["evaluation"]["final_gate_accepted"]:
                assert outcome["class"] == "gate"
            else:
                assert outcome["class"] == "fallback"
    # An accepted commit that misses the goal must not silently become task success.
    assert (
        data["cells"][(SELECTORS[0], "detailed")]["outcomes"]["unauthorized_objective"]["class"]
        == "gate"
    )


def test_flow_render_publishes_per_cell_denominators_and_separate_failure_outcomes(generator):
    labels = _visible_text(generator.flow_svg(generator.load_cohorts()))
    text = " ".join(labels)
    rows = re.findall(
        r"(gpt-[\w.-]+) (detailed|generic) signal P(\d+) / A(\d+) / G(\d+) of (\d+)",
        text,
    )
    assert rows == [
        (selector, condition, str(values[2]), str(values[3]), str(values[4]), str(values[0]))
        for (selector, condition), values in EXPECTED_COUNTS.items()
    ]
    for words, count in (
        (["ASSIGNED"], 20),
        (["RECEIVED"], 20),
        (["STRICTLY", "PARSED"], 10),
        (["GATE", "ACCEPTED"], 8),
        (["GOAL", "REACHED"], 7),
    ):
        index = labels.index(" ".join(words))
        assert labels[index - 1] == str(count)
    marks = Counter(label for label in labels if label in {"G", "A", "F", "S"})
    assert marks == {"G": 7, "A": 1, "F": 2, "S": 10}
    assert "10 schema failures" in text
    assert "1 accepted commit missed" in text


def test_state_signal_render_distinguishes_exact_generic_and_structured_feedback(generator):
    text = " ".join(_visible_text(generator.state_signal_svg(generator.load_cohorts())))
    for label in (
        "DETAILED SIGNAL",
        "GENERIC SIGNAL",
        "valid: false",
        "len(checks_run): 7",
        "errors: code, entity,",
        "reason, repair_hint",
        "message: Action rejected.",
        "no error code or repair hint",
        "repair budget 0",
        "no further model call",
        "signal_restored",
    ):
        assert label in text
    for check in EXPECTED_CHECKS:
        assert check in text


def test_rendered_labels_keep_development_identity_cost_and_efficacy_boundaries(generator):
    labels = _visible_text(generator.flow_svg(generator.load_cohorts()))
    text = " ".join(labels).lower()
    assert "synthetic fixtures" in text and "development" in text
    assert "response receipt is not task success" in text
    assert "no superiority claim" in text
    state_text = " ".join(
        _visible_text(generator.state_signal_svg(generator.load_cohorts()))
    ).lower()
    assert "no hidden-state or efficacy claim" in state_text
    assert re.search(
        r"(?:nr|not reported|unknown|unverified).*served identity.*request count.*cost", text
    )
    for selector in SELECTORS:
        assert selector in text
    combined_text = text + " " + state_text
    assert "dispatch-to-terminal" in text
    assert not re.search(r"\$\s*\d|\b\d+(?:\.\d+)?\s*(?:usd|dollars)\b", combined_text)
    assert not re.search(
        r"(?:served|actual|verified) model(?: identity)?\s*[:=]\s*gpt", combined_text
    )
    assert not re.search(r"(?:proves?|demonstrates?)\s+(?:efficacy|superiority)", combined_text)


@pytest.mark.parametrize(
    "case",
    [
        "invalid_json",
        "not_an_object",
        "missing_cases",
        "pending_row",
        "pending_summary",
        "missing_assignment",
        "duplicate_fixture",
        "nonmatching_fixture",
        "selector_mismatch",
        "incomplete_receipt",
        "failed_transport",
        "unexpected_failure",
        "objective_without_gate",
        "summary_assigned",
        "summary_completed",
        "summary_failed",
        "summary_gate",
        "summary_goal",
    ],
)
def test_invalid_or_unpaired_evidence_is_rejected_before_render(generator, workspace, case):
    path = workspace[SELECTORS[0]]
    if case == "invalid_json":
        path.write_text("{not-json", encoding="utf-8")
    elif case == "not_an_object":
        path.write_text("[]", encoding="utf-8")
    else:

        def change(doc):
            row = doc["cases"][0]
            if case == "missing_cases":
                del doc["cases"]
            elif case == "pending_row":
                row["status"] = "PENDING"
            elif case == "pending_summary":
                doc["summary"]["detailed"]["pending"] = 1
            elif case == "missing_assignment":
                doc["cases"].pop()
            elif case == "duplicate_fixture":
                # Hide the collapsed outcome in a self-consistent summary: uniqueness
                # must be checked independently, not accidentally via count mismatch.
                doc["cases"][0] = deepcopy(doc["cases"][2])
                for field in ("completed", "gate_accepted", "objective_reached"):
                    doc["summary"]["detailed"][field] -= 1
            elif case == "nonmatching_fixture":
                row["case_id"] = "not_in_paired_fixture_set"
            elif case == "selector_mismatch":
                doc["metadata"]["model_selector"] = SELECTORS[1]
            elif case == "incomplete_receipt":
                row["evidence"]["stdout"]["complete"] = False
            elif case == "failed_transport":
                row["evidence"]["returncode"] = 1
            elif case == "unexpected_failure":
                failed = next(item for item in doc["cases"] if item["status"] == "FAILED")
                failed["failure"]["type"] = "TimeoutError"
            elif case == "objective_without_gate":
                row["evaluation"]["final_gate_accepted"] = False
            else:
                field = {
                    "summary_assigned": "assigned",
                    "summary_completed": "completed",
                    "summary_failed": "failed",
                    "summary_gate": "gate_accepted",
                    "summary_goal": "objective_reached",
                }[case]
                doc["summary"]["detailed"][field] += 1

        _mutate(path, change)
    with pytest.raises(ValueError):
        generator.load_cohorts()
    assert not generator.FIGURES.exists()


@pytest.mark.parametrize("field", ["initial_state", "shared_proposal"])
@pytest.mark.parametrize("pair", ["signal_conditions", "selectors"])
def test_pairing_requires_identical_state_and_proposal(generator, workspace, field, pair):
    selector = SELECTORS[0] if pair == "signal_conditions" else SELECTORS[1]

    def change(doc):
        rows = [
            item
            for item in doc["cases"]
            if item["case_id"] == "missing_precondition"
            and (pair == "selectors" or item["condition"] == "generic")
        ]
        for row in rows:
            row[field]["facts" if field == "initial_state" else "effects"] = ["changed_pair_input"]

    _mutate(workspace[selector], change)
    with pytest.raises(ValueError):
        generator.load_cohorts()


@pytest.mark.parametrize(
    "signal",
    [
        {"valid": False, "message": "Action rejected.", "repair_hint": "leaked hint"},
        {"valid": False, "message": "Different rejection."},
        {"valid": True, "message": "Action rejected."},
        {"valid": 0, "message": "Action rejected."},
        {"valid": False},
    ],
    ids=[
        "hint-leak",
        "changed-message",
        "accepted-invalid-proposal",
        "nonboolean-valid",
        "missing-message",
    ],
)
def test_generic_condition_rejects_any_change_to_minimal_signal(generator, workspace, signal):
    def change(doc):
        row = next(item for item in doc["cases"] if item["condition"] == "generic")
        row["input_signal"] = signal

    _mutate(workspace[SELECTORS[0]], change)
    with pytest.raises(ValueError):
        generator.load_cohorts()


@pytest.mark.parametrize(
    "case",
    [
        "valid_signal",
        "missing_entity",
        "missing_reason",
        "missing_repair_hint",
        "empty_errors",
        "additional_error",
        "error_code_drift",
        "checks_drift",
        "duplicate_check",
    ],
)
def test_detailed_condition_requires_complete_structured_error_set(generator, workspace, case):
    def change(doc):
        signal = doc["cases"][0]["input_signal"]
        if case == "valid_signal":
            signal["valid"] = True
        elif case.startswith("missing_"):
            del signal["errors"][0][case.removeprefix("missing_")]
        elif case == "empty_errors":
            signal["errors"] = []
        elif case == "additional_error":
            signal["errors"].append(dict(signal["errors"][0]))
        elif case == "error_code_drift":
            signal["errors"][0]["code"] = "OTHER_ERROR"
        elif case == "checks_drift":
            signal["checks_run"].pop()
        else:
            signal["checks_run"][-1] = signal["checks_run"][0]

    _mutate(workspace[SELECTORS[0]], change)
    with pytest.raises(ValueError):
        generator.load_cohorts()


def test_write_then_check_is_deterministic_offline_and_preserves_frozen_sources(
    generator, workspace, monkeypatch, capsys
):
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in workspace.values()}
    monkeypatch.setattr(sys, "argv", ["generate_paired_feedback_figures.py"])
    assert generator.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "write"
    assert report["totals"] == EXPECTED_TOTALS
    receipts = {
        str(path.relative_to(generator.ROOT)): hashlib.sha256(raw).hexdigest()
        for path, (raw, _) in before.items()
    }
    assert report["sources"] == receipts
    expected = generator.outputs(generator.load_cohorts())
    assert {path.name for path in generator.FIGURES.iterdir()} == {
        "fig_state_signal.svg",
        "fig_paired_feedback_flow.svg",
    }
    for path, rendered in expected.items():
        assert path.read_text() == rendered
        _visible_text(rendered)
    written = _tree_bytes(generator.FIGURES)
    monkeypatch.setattr(sys, "argv", ["generate_paired_feedback_figures.py", "--check"])
    monkeypatch.setattr(Path, "write_text", _forbid_external_effect)
    monkeypatch.setattr(Path, "write_bytes", _forbid_external_effect)
    assert generator.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["mode"] == "check"
    assert report["totals"] == EXPECTED_TOTALS
    assert report["sources"] == receipts
    assert _tree_bytes(generator.FIGURES) == written
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in workspace.values()
    } == before


@pytest.mark.parametrize("figure", ["STATE_SIGNAL_SVG", "FLOW_SVG"])
@pytest.mark.parametrize("problem", ["missing", "drift"])
def test_check_detects_missing_or_drift_without_rewriting_any_artifact(
    generator, workspace, monkeypatch, figure, problem
):
    expected = generator.outputs(generator.load_cohorts())
    generator.FIGURES.mkdir(parents=True)
    for path, rendered in expected.items():
        path.write_text(rendered, encoding="utf-8")
    target = getattr(generator, figure)
    if problem == "missing":
        target.unlink()
    else:
        # Keep valid SVG but corrupt a published outcome: XML validity alone is insufficient.
        root = ET.fromstring(target.read_text())
        node = next(root.iter(SVG + "text"))
        node.text = "UNTRUSTED PUBLISHED COUNT 999/5"
        target.write_text(ET.tostring(root, encoding="unicode"), encoding="utf-8")
    before = _tree_bytes(generator.ROOT)
    monkeypatch.setattr(sys, "argv", ["generate_paired_feedback_figures.py", "--check"])
    monkeypatch.setattr(Path, "write_text", _forbid_external_effect)
    monkeypatch.setattr(Path, "write_bytes", _forbid_external_effect)
    with pytest.raises(
        ValueError,
        match="missing generated figure" if problem == "missing" else "generated figure drift",
    ):
        generator.main()
    assert _tree_bytes(generator.ROOT) == before


def test_check_never_creates_a_missing_output_directory(generator, workspace, monkeypatch):
    before = _tree_bytes(generator.ROOT)
    monkeypatch.setattr(sys, "argv", ["generate_paired_feedback_figures.py", "--check"])
    monkeypatch.setattr(Path, "write_text", _forbid_external_effect)
    monkeypatch.setattr(Path, "write_bytes", _forbid_external_effect)
    monkeypatch.setattr(Path, "mkdir", _forbid_external_effect)
    with pytest.raises(ValueError, match="missing generated figure"):
        generator.main()
    assert not generator.FIGURES.exists()
    assert _tree_bytes(generator.ROOT) == before


def test_source_receipts_hash_exact_bytes_not_normalized_json(generator, workspace):
    before = generator.load_cohorts()
    path = workspace[SELECTORS[0]]
    raw = path.read_bytes() + b"\n"
    path.write_bytes(raw)
    after = generator.load_cohorts()
    source = str(path.relative_to(generator.ROOT))
    assert after["totals"] == before["totals"] == EXPECTED_TOTALS
    assert after["sources"][source] == hashlib.sha256(raw).hexdigest()
    assert after["sources"][source] != before["sources"][source]
    other = str(workspace[SELECTORS[1]].relative_to(generator.ROOT))
    assert after["sources"][other] == before["sources"][other]


@pytest.fixture
def raw_workspace(workspace):
    for selector, path in workspace.items():
        source = PILOT / f"{PREFIX}{selector}"
        # Reconstruct a safe raw fixture; private collection directories are not published.
        doc = json.loads(path.read_text())
        doc.pop("public_projection")
        doc["metadata"]["codex_executable"] = "fictional/local/codex"
        path.write_text(json.dumps(doc), encoding="utf-8")
        for row in json.loads(path.read_text())["cases"]:
            name = row["prompt_file"]
            (path.parent / name).write_bytes((source / name).read_bytes())
    return workspace


def test_public_export_preserves_raw_and_every_scientific_value(
    generator, raw_workspace, monkeypatch, capsys
):
    raw_root = raw_workspace[SELECTORS[0]].parent.parent
    public_root = raw_root / "public-v5"
    before = _tree_bytes(raw_root)
    monkeypatch.setattr(generator, "RAW_COHORT_ROOT", raw_root)
    monkeypatch.setattr(generator, "COHORT_ROOT", public_root)
    monkeypatch.setattr(sys, "argv", ["generate_paired_feedback_figures.py", "--export-public"])
    assert generator.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report["totals"] == EXPECTED_TOTALS
    assert set(report["sources"]) == {
        str((public_root / path.parent.name / "results.json").relative_to(generator.ROOT))
        for path in raw_workspace.values()
    }
    expected_public_files = set()
    for path in raw_workspace.values():
        raw = json.loads(path.read_text())
        projected_path = public_root / path.parent.name / "results.json"
        projected = json.loads(projected_path.read_text())
        projection = projected.pop("public_projection")
        assert projection == {
            "schema": "paired-feedback-public-projection/1",
            "raw_source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "omitted_fields": ["metadata.codex_executable"],
            "reason": "Local executable path omitted; outcomes and executable hash/version retained.",
        }
        assert projected["metadata"]["codex_executable"] is None
        expected = deepcopy(raw)
        expected["metadata"]["codex_executable"] = None
        assert projected == expected
        expected_public_files.add(str(projected_path.relative_to(public_root)))
        for row in raw["cases"]:
            prompt = projected_path.parent / row["prompt_file"]
            assert prompt.read_bytes() == (path.parent / row["prompt_file"]).read_bytes()
            assert hashlib.sha256(prompt.read_bytes()).hexdigest() == row["prompt_sha256"]
            expected_public_files.add(str(prompt.relative_to(public_root)))
    assert set(_tree_bytes(public_root)) == expected_public_files
    assert {
        name: ((raw_root / name).read_bytes(), (raw_root / name).stat().st_mtime_ns)
        for name in before
    } == before
    assert generator.load_cohorts(raw_root)["totals"] == generator.load_cohorts()["totals"]
    # Once exported, checking figures must not need the private raw archive.
    monkeypatch.setattr(generator, "RAW_COHORT_ROOT", generator.ROOT / "unavailable-private-input")
    monkeypatch.setattr(sys, "argv", ["generate_paired_feedback_figures.py", "--check"])
    monkeypatch.setattr(Path, "write_text", _forbid_external_effect)
    monkeypatch.setattr(Path, "write_bytes", _forbid_external_effect)
    assert generator.main() == 0
    assert json.loads(capsys.readouterr().out)["totals"] == EXPECTED_TOTALS


def test_public_export_cannot_overwrite_the_raw_archive(generator, raw_workspace):
    raw_root = raw_workspace[SELECTORS[0]].parent.parent
    before = _tree_bytes(raw_root)
    with pytest.raises(ValueError, match="public root must differ from raw root"):
        generator.export_public(raw_root, raw_root)
    assert _tree_bytes(raw_root) == before


def test_export_rejects_corrupt_last_prompt_before_writing_any_public_file(
    generator, raw_workspace
):
    raw_root = raw_workspace[SELECTORS[0]].parent.parent
    public_root = raw_root / "public-v5"
    path = raw_workspace[SELECTORS[1]]
    final_row = json.loads(path.read_text())["cases"][-1]
    prompt = path.parent / final_row["prompt_file"]
    prompt.write_bytes(prompt.read_bytes() + b"\nchanged after collection")
    before = _tree_bytes(raw_root)
    with pytest.raises(ValueError, match="prompt hash mismatch"):
        generator.export_public(raw_root, public_root)
    assert not public_root.exists()
    assert _tree_bytes(raw_root) == before


@pytest.mark.parametrize("field", ["initial_state", "shared_proposal"])
@pytest.mark.parametrize("problem", ["missing", "null", "empty"])
def test_equal_but_absent_pair_inputs_are_not_a_valid_pair(generator, workspace, field, problem):
    def change(doc):
        for row in doc["cases"]:
            if problem == "missing":
                row.pop(field)
            else:
                row[field] = None if problem == "null" else {}

    # Removing the input everywhere must not pass merely because all pairs agree on null.
    for path in workspace.values():
        _mutate(path, change)
    with pytest.raises(ValueError):
        generator.load_cohorts()


@pytest.mark.parametrize(
    "field",
    [
        "assigned",
        "completed",
        "failed",
        "pending",
        "gate_accepted",
        "objective_reached",
    ],
)
def test_summary_counts_require_integers_not_equal_valued_floats(generator, workspace, field):
    def change(doc):
        summary = doc["summary"]["detailed"]
        summary[field] = float(summary[field])

    _mutate(workspace[SELECTORS[0]], change)
    with pytest.raises(ValueError):
        generator.load_cohorts()


@pytest.mark.parametrize(
    "problem",
    [
        "boolean_returncode",
        "boolean_pending",
        "empty_response",
        "null_response",
        "empty_events",
        "missing_start",
        "duplicate_start",
        "duplicate_terminal",
        "nonterminal_last_event",
    ],
)
def test_received_requires_an_actual_single_terminal_adapter_response(
    generator, workspace, problem
):
    def change(doc):
        row = doc["cases"][0]
        evidence = row["evidence"]
        if problem == "boolean_returncode":
            evidence["returncode"] = False
        elif problem == "boolean_pending":
            doc["summary"]["detailed"]["pending"] = False
        elif problem in {"empty_response", "null_response"}:
            row["response_text"] = "" if problem == "empty_response" else None
        elif problem == "empty_events":
            evidence["events"] = []
        elif problem == "missing_start":
            evidence["events"] = [
                event for event in evidence["events"] if event["type"] != "turn.started"
            ]
        elif problem == "duplicate_start":
            event = next(event for event in evidence["events"] if event["type"] == "turn.started")
            evidence["events"].insert(0, deepcopy(event))
        elif problem == "duplicate_terminal":
            evidence["events"].append(deepcopy(evidence["events"][-1]))
        else:
            evidence["events"].append({"type": "item.completed", "item_type": "agent_message"})

    _mutate(workspace[SELECTORS[0]], change)
    with pytest.raises(ValueError):
        generator.load_cohorts()


@pytest.mark.parametrize("kind", ["results", "prompt", "approved"])
@pytest.mark.parametrize("alias", ["symlink", "hardlink"])
def test_public_export_rejects_destination_aliases_to_any_protected_raw_file(
    generator, raw_workspace, kind, alias
):
    raw_root = raw_workspace[SELECTORS[0]].parent.parent
    public_root = raw_root / "public-v5"
    raw_result = raw_workspace[SELECTORS[1]]
    if kind == "results":
        protected = raw_result
    elif kind == "prompt":
        protected = (
            raw_result.parent / json.loads(raw_result.read_text())["cases"][-1]["prompt_file"]
        )
    else:
        protected = raw_result.parent / "approved_results.json"
        protected.write_bytes(b'{"frozen_approval": "must remain unchanged"}\n')
    target = public_root / raw_result.parent.name / "results.json"
    target.parent.mkdir(parents=True)
    if alias == "symlink":
        target.symlink_to(protected)
    else:
        os.link(protected, target)
    before = _tree_bytes(raw_root)
    with pytest.raises(ValueError):
        generator.export_public(raw_root, public_root)
    assert _tree_bytes(raw_root) == before


def test_public_export_rejects_a_cohort_directory_symlink_into_raw(generator, raw_workspace):
    raw_root = raw_workspace[SELECTORS[0]].parent.parent
    public_root = raw_root / "public-v5"
    public_root.mkdir()
    raw_directory = raw_workspace[SELECTORS[1]].parent
    (public_root / raw_directory.name).symlink_to(raw_directory, target_is_directory=True)
    before = _tree_bytes(raw_root)
    with pytest.raises(ValueError):
        generator.export_public(raw_root, public_root)
    assert _tree_bytes(raw_root) == before
