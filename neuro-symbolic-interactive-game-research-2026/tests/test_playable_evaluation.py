from __future__ import annotations

import json
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.run_playable_evaluation import (
    EXACT_TERMINAL_HASH,
    EXPECTED_FIXTURE_CHECKS,
    EXPECTED_FIXTURE_IDS,
    EXPECTED_PRESENTATION_CHECKS,
    FIXTURE_FILES,
    GODOT_PROJECT,
    LATEST_DOCS,
    NOT_EVIDENCE_FOR,
    SANDBOXED_MACOS_HOST_ERROR,
    SCREENSHOT_STAGES,
    _run_godot,
    atomic_write,
    build_matrix,
    render_markdown,
    screenshot_receipts,
    stage_project,
    summarize_fixture_run,
    summarize_presentation,
    write_outputs,
)


def _fixture_document(index: int) -> dict:
    modes = ("none", "duplicate_event", "timeout", "corrupt_save")
    duplicate = int(index == 1)
    timeout = int(index == 2)
    fallback_codes = ["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE"]
    if timeout:
        fallback_codes.insert(0, "ADAPTER_TIMEOUT")
    return {
        "fixture_id": EXPECTED_FIXTURE_IDS[index],
        "fault_mode": modes[index],
        "expected": {
            "terminal_state_hash": EXACT_TERMINAL_HASH,
            "research_oracle_state_hash": EXACT_TERMINAL_HASH,
            "committed_operations": ["acquire_object", "install_lens", "reveal_hint"],
            "duplicate_event_count": duplicate,
            "timeout_count": timeout,
            "fallback_codes": fallback_codes,
        },
    }


def _fixture_events(index: int) -> list[dict]:
    events = [
        {
            "event_id": "fallback-secret",
            "event_type": "fallback",
            "validation": {"codes": ["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE"]},
            "commit": {"applied": False, "operation": None},
        }
    ]
    for number, operation in enumerate(("acquire_object", "install_lens", "reveal_hint")):
        events.append(
            {
                "event_id": f"commit-{number}",
                "event_type": "commit",
                "validation": {"codes": []},
                "commit": {"applied": True, "operation": operation},
            }
        )
    if index == 1:
        events.append(deepcopy(events[2]))
    if index == 2:
        events.extend(
            [
                {
                    "event_id": "timeout",
                    "event_type": "timeout",
                    "validation": {"codes": ["ADAPTER_TIMEOUT"]},
                    "commit": {"applied": False, "operation": None},
                },
                {
                    "event_id": "fallback-timeout",
                    "event_type": "fallback",
                    "validation": {"codes": ["ADAPTER_TIMEOUT"]},
                    "commit": {"applied": False, "operation": None},
                },
            ]
        )
    return events


def _fixture_summary(index: int, events: list[dict]) -> dict:
    return {
        "execution_status": "OBSERVED_ENGINE_RUN",
        "fixture_id": EXPECTED_FIXTURE_IDS[index],
        "engine": {
            "name": "Godot",
            "headless": True,
            "version": "4.7.1.stable.official.test",
        },
        "terminal_state_hash": EXACT_TERMINAL_HASH,
        "checks": {name: True for name in EXPECTED_FIXTURE_CHECKS},
        "counts": {
            "events": len(events),
            "commits": 3,
            "fallbacks": 2 if index == 2 else 1,
            "duplicate_events": int(index == 1),
            "timeouts": int(index == 2),
        },
    }


def _fixture_rows() -> list[dict]:
    rows = []
    for index in range(4):
        events = _fixture_events(index)
        rows.append(
            summarize_fixture_run(
                _fixture_document(index),
                _fixture_summary(index, events),
                events,
            )
        )
    return rows


def _presentation() -> dict:
    report = {
        "evaluation": "sealed-lighthouse-3d-presentation-engineering",
        "engineering_only": True,
        "passed": True,
        "state_sha256_before": "f" * 64,
        "state_sha256_after": "f" * 64,
        "supported_screenshot_stages": list(SCREENSHOT_STAGES),
        "checks": [{"check": name, "pass": True} for name in sorted(EXPECTED_PRESENTATION_CHECKS)],
    }
    return summarize_presentation(report)


def _screenshots() -> list[dict]:
    return [
        {
            "stage": stage,
            "file": f"{stage}.png",
            "bytes": 100 + index,
            "sha256": str(index) * 64,
            "width": 1280,
            "height": 720,
            "engineering_working_capture_only": True,
        }
        for index, stage in enumerate(SCREENSHOT_STAGES, start=1)
    ]


def test_matrix_is_exactly_claim_bounded_and_counts_52_of_52() -> None:
    matrix = build_matrix(
        godot_version="4.7.1.stable.official.test",
        fixtures=_fixture_rows(),
        presentation=_presentation(),
        screenshots=_screenshots(),
    )

    assert matrix["all_pass"] is True
    assert matrix["status"] == "PASS"
    assert matrix["scope"]["engineering_only"] is True
    assert matrix["scope"]["g4_status"] == "UNASSESSED"
    assert tuple(matrix["scope"]["not_evidence_for"]) == NOT_EVIDENCE_FOR
    assert matrix["terminal_state"]["exact_sha256"] == EXACT_TERMINAL_HASH
    assert matrix["totals"] == {
        "fixtures_passed": 4,
        "fixtures_total": 4,
        "fixture_checks_passed": 40,
        "fixture_checks_total": 40,
        "presentation_checks_passed": 12,
        "presentation_checks_total": 12,
        "combined_checks_passed": 52,
        "combined_checks_total": 52,
        "screenshots_valid": 4,
        "screenshots_total": 4,
    }
    assert [row["counts"]["fallbacks"] for row in matrix["authored_fixtures"]] == [
        1,
        1,
        2,
        1,
    ]


def test_fixture_summary_fails_closed_on_event_count_drift() -> None:
    fixture = _fixture_document(0)
    events = _fixture_events(0)
    summary = _fixture_summary(0, events)
    summary["counts"]["fallbacks"] = 99

    with pytest.raises(ValueError, match="summary/event count mismatch"):
        summarize_fixture_run(fixture, summary, events)


def test_presentation_summary_requires_exact_twelve_check_contract_and_state_isolation() -> None:
    report = {
        "evaluation": "sealed-lighthouse-3d-presentation-engineering",
        "engineering_only": True,
        "passed": True,
        "state_sha256_before": "a" * 64,
        "state_sha256_after": "b" * 64,
        "supported_screenshot_stages": list(SCREENSHOT_STAGES),
        "checks": [{"check": name, "pass": True} for name in sorted(EXPECTED_PRESENTATION_CHECKS)],
    }
    with pytest.raises(ValueError, match="mutated canonical state"):
        summarize_presentation(report)

    report["state_sha256_after"] = report["state_sha256_before"]
    report["checks"] = report["checks"][:-1]
    with pytest.raises(ValueError, match="unexpected presentation check set"):
        summarize_presentation(report)


def test_stage_project_excludes_import_cache_and_latest_docs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        source = root / "source"
        destination = root / "destination"
        source.mkdir()
        (source / "project.godot").write_text("[application]\n", encoding="utf-8")
        (source / "keep.gd").write_text("extends Node\n", encoding="utf-8")
        (source / ".godot").mkdir()
        (source / ".godot/imported").write_text("stale\n", encoding="utf-8")
        (source / "docs").mkdir()
        (source / "docs/latest.png").write_bytes(b"not-runtime-input")

        stage_project(source, destination)

        assert (destination / "project.godot").is_file()
        assert (destination / "keep.gd").is_file()
        assert not (destination / ".godot").exists()
        assert not (destination / "docs").exists()
        assert (source / ".godot/imported").read_text(encoding="utf-8") == "stale\n"


def test_atomic_latest_outputs_are_byte_stable() -> None:
    matrix = build_matrix(
        godot_version="4.7.1.stable.official.test",
        fixtures=_fixture_rows(),
        presentation=_presentation(),
        screenshots=_screenshots(),
    )
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory)
        write_outputs(output, matrix)
        first_json = (output / "evaluation-matrix.json").read_bytes()
        first_markdown = (output / "evaluation-matrix.md").read_bytes()
        write_outputs(output, matrix)

        assert (output / "evaluation-matrix.json").read_bytes() == first_json
        assert (output / "evaluation-matrix.md").read_bytes() == first_markdown
        assert not list(output.glob("*.tmp"))
        assert json.loads(first_json)["all_pass"] is True
        markdown = render_markdown(matrix)
        assert "G4 remains `UNASSESSED`" in markdown
        assert "52/52" in markdown


def test_atomic_write_replaces_without_leaving_a_temporary_file() -> None:
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory) / "nested/result.txt"
        atomic_write(target, b"first")
        atomic_write(target, b"second")
        assert target.read_bytes() == b"second"
        assert not list(target.parent.glob("*.tmp"))


def test_godot_runner_fails_on_silent_script_error_in_log(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as directory:
        log_path = Path(directory) / "godot.log"
        log_path.write_text("SCRIPT ERROR: staged parse failure\n", encoding="utf-8")

        def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(["godot"], 0, "", "")

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(RuntimeError, match="staged parse failure"):
            _run_godot(
                ["godot", "--log-file", str(log_path)],
                label="silent-error-test",
                timeout=1,
            )


def test_godot_runner_allows_known_sandboxed_macos_import_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = (
        "ERROR: Can't open file from path '/System/Library/Fonts/Apple Color Emoji.ttc'.\n"
        "   at: get_file_as_bytes (core/io/file_access.cpp:907)\n"
        'ERROR: Condition "ret != noErr" is true. Returning: ""\n'
        "   at: get_system_ca_certificates (platform/macos/os_macos.mm:1035)"
    )

    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["godot"], 0, output, "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    _run_godot(
        ["godot"],
        label="sandboxed-import-test",
        timeout=1,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )


def test_latest_working_screenshots_pass_the_png_contract() -> None:
    receipts = screenshot_receipts(LATEST_DOCS)
    assert [row["stage"] for row in receipts] == list(SCREENSHOT_STAGES)
    assert {(row["width"], row["height"]) for row in receipts} == {(1280, 720)}
    assert all(len(row["sha256"]) == 64 for row in receipts)


def test_runner_contract_names_all_fixtures_and_public_safe_execution() -> None:
    root = Path(__file__).parents[1]
    source = root / "scripts/run_playable_evaluation.py"
    text = source.read_text(encoding="utf-8")
    assert len(FIXTURE_FILES) == 4
    assert "--import" in text
    assert "--evaluate" in text
    assert "--public-safe" in text
    assert (GODOT_PROJECT / "project.godot").is_file()
