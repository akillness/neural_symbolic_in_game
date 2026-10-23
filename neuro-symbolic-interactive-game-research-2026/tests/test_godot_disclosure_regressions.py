from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from scripts.run_playable_evaluation import GODOT_PROJECT, find_godot_4, stage_project

ROOT = Path(__file__).parents[1]
TRACE_RESULT_MARKER = "DISCLOSURE_RECEIPT_PROBE "


@pytest.fixture(scope="module")
def godot() -> str:
    try:
        executable, _version = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    return executable


def _import_project(godot: str, project: Path, log_path: Path) -> None:
    imported = subprocess.run(
        [godot, "--headless", "--path", str(project), "--import", "--log-file", str(log_path)],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr


def _evaluate_report(godot: str, project: Path, output_path: Path) -> tuple[dict[str, Any], str]:
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(project),
            "res://scenes/main_3d.tscn",
            "--quit-after",
            "120",
            "--",
            "--evaluate",
            str(output_path),
            "--public-safe",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert output_path.is_file(), result.stdout + result.stderr
    return json.loads(output_path.read_text(encoding="utf-8")), result.stdout + result.stderr


def test_evaluation_trace_names_only_checks_the_engine_evaluated(
    godot: str, tmp_path: Path
) -> None:
    """The public evaluation trace must not mislabel a conditional check as skipped."""
    project = tmp_path / "project"
    stage_project(GODOT_PROJECT, project)
    _import_project(godot, project, tmp_path / "import.log")
    report, _output = _evaluate_report(godot, project, tmp_path / "evaluation.json")

    trace = report["dashboard_trace"]
    assert trace["checks"] == [
        {"code": "FORBIDDEN_DISCLOSURE", "gate": "DISCLOSURE", "outcome": "pass"},
        {
            "code": "STAGE_GATED_DISCLOSURE",
            "gate": "DISCLOSURE/QUEST STAGE",
            "outcome": "fail",
        },
    ]
    assert trace["skipped"] == [
        {"code": "UNKNOWN_ACTOR", "gate": "POLICY"},
        {"code": "NPC_DOES_NOT_KNOW_FACT", "gate": "KNOWLEDGE"},
    ]
    named_checks = [entry["code"] for entry in trace["checks"]]
    named_skips = [entry["code"] for entry in trace["skipped"]]
    assert set(named_checks + named_skips) == {
        "FORBIDDEN_DISCLOSURE",
        "STAGE_GATED_DISCLOSURE",
        "UNKNOWN_ACTOR",
        "NPC_DOES_NOT_KNOW_FACT",
    }
    assert "DISCLOSURE_TEMPLATE_UNAVAILABLE" not in named_checks + named_skips
    assert trace["held_at"] == "STAGE_GATED_DISCLOSURE"
    assert trace["short_circuit"] is True
    assert trace["consistent"] is True


DISCLOSURE_RECEIPT_PROBE = r"""extends SceneTree

const RESULT_MARKER := "DISCLOSURE_RECEIPT_PROBE "

func _init() -> void:
    call_deferred("_run")

func _rows(game: Object, start: int, end: int) -> Array:
    var rows: Array = []
    for index in range(start, end):
        rows.append(game._observation_receipts[index].duplicate(true))
    return rows

func _authorized_state(game: Object) -> Dictionary:
    var state: Dictionary = game.machine.state.duplicate(true)
    state["quest"]["stage"] = 2
    state["npcs"]["captain_mira"]["disclosed"].erase("tide_marks_hint")
    state["facts"].erase("tide_marks_hint")
    return state

func _run() -> void:
    var scene_resource: PackedScene = load("res://scenes/main_3d.tscn")
    var game: Object = scene_resource.instantiate()
    root.add_child(game)
    await process_frame
    game._smoke_mode = false
    game._evaluate_mode = false
    game._play_started = true
    game._dialogue_open = true
    game._receipt_recording_enabled = true
    game._observation_receipts.clear()
    game._receipt_sequence = 0
    game._telemetry_started_us = Time.get_ticks_usec()
    game._telemetry_session_id = "disclosure-receipt-probe"
    game._telemetry_initial_state_hash = game.machine.state_hash()

    var denied_before: String = str(game.machine.state_hash())
    var denied_start: int = game._observation_receipts.size()
    var denied: Dictionary = game.call("_propose_tide_hint")
    var denied_after: String = str(game.machine.state_hash())

    game.machine.load_state(_authorized_state(game))
    game._dialogue_open = true
    var fresh_before: String = str(game.machine.state_hash())
    var fresh_start: int = game._observation_receipts.size()
    var fresh: Dictionary = game.call("_propose_tide_hint")
    var fresh_after: String = str(game.machine.state_hash())

    game._dialogue_open = true
    var redisplay_before: String = str(game.machine.state_hash())
    var redisplay_start: int = game._observation_receipts.size()
    var redisplay: Dictionary = game.call("_propose_tide_hint")
    var redisplay_after: String = str(game.machine.state_hash())

    print(RESULT_MARKER + JSON.stringify({
        "denied": {"result": denied, "before": denied_before, "after": denied_after, "receipts": _rows(game, denied_start, fresh_start)},
        "fresh": {"result": fresh, "before": fresh_before, "after": fresh_after, "receipts": _rows(game, fresh_start, redisplay_start)},
        "redisplay": {"result": redisplay, "before": redisplay_before, "after": redisplay_after, "receipts": _rows(game, redisplay_start, game._observation_receipts.size())},
    }))
    quit(0)
"""


def _run_receipt_probe(godot: str, project: Path, tmp_path: Path) -> dict[str, Any]:
    script = project / "tests" / "disclosure_receipt_probe.gd"
    script.write_text(DISCLOSURE_RECEIPT_PROBE, encoding="utf-8")
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(project),
            "--script",
            "res://tests/disclosure_receipt_probe.gd",
            "--quit-after",
            "120",
            "--log-file",
            str(tmp_path / "probe.log"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = result.stdout + result.stderr
    lines = [line for line in output.splitlines() if line.startswith(TRACE_RESULT_MARKER)]
    assert len(lines) == 1, output
    return json.loads(lines[0][len(TRACE_RESULT_MARKER) :])


def test_disclosure_receipts_preserve_denial_fresh_and_redisplay_state_boundaries(
    godot: str, tmp_path: Path
) -> None:
    """Each disclosure route links receipt hashes without inventing a mutation."""
    project = tmp_path / "project"
    stage_project(GODOT_PROJECT, project)
    _import_project(godot, project, tmp_path / "import.log")
    probe = _run_receipt_probe(godot, project, tmp_path)

    denied = probe["denied"]
    assert denied["result"]["accepted"] is False
    assert denied["result"]["state_effect"] == "denied_no_mutation"
    assert denied["before"] == denied["after"]
    assert [row["receipt_kind"] for row in denied["receipts"]][:2] == [
        "disclosure_outcome",
        "hold_emitted",
    ]
    assert all(
        row["prior_state_sha256"] == row["next_state_sha256"] == denied["before"]
        for row in denied["receipts"]
    )

    fresh = probe["fresh"]
    assert fresh["result"]["accepted"] is True
    assert fresh["result"]["state_effect"] == "fresh_disclosure"
    assert fresh["result"]["mutated"] is True
    assert fresh["before"] != fresh["after"]
    assert [row["receipt_kind"] for row in fresh["receipts"]][:2] == [
        "disclosure_outcome",
        "commit_emitted",
    ]
    assert fresh["receipts"][0]["prior_state_sha256"] == fresh["before"]
    assert fresh["receipts"][0]["next_state_sha256"] == fresh["after"]
    assert fresh["receipts"][1]["prior_state_sha256"] == fresh["after"]
    assert fresh["receipts"][1]["next_state_sha256"] == fresh["after"]

    redisplay = probe["redisplay"]
    assert redisplay["result"]["accepted"] is True
    assert redisplay["result"]["state_effect"] == "redisplay_no_mutation"
    assert redisplay["result"]["mutated"] is False
    assert redisplay["before"] == redisplay["after"] == fresh["after"]
    assert [row["receipt_kind"] for row in redisplay["receipts"]] == ["disclosure_outcome"]
    assert (
        redisplay["receipts"][0]["prior_state_sha256"]
        == redisplay["receipts"][0]["next_state_sha256"]
    )
    assert redisplay["receipts"][0]["prior_state_sha256"] == redisplay["before"]


def test_autoplay_receipt_links_disclosure_mutation_to_commit(godot: str, tmp_path: Path) -> None:
    """Autoplay must link the disclosure mutation to its emitted commit receipt."""
    project = tmp_path / "project"
    stage_project(GODOT_PROJECT, project)
    _import_project(godot, project, tmp_path / "import.log")
    output_path = tmp_path / "autoplay-receipts.json"
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(project),
            "res://scenes/main_3d.tscn",
            "--",
            "--autoplay",
            "--receipt-output",
            str(output_path),
            "--public-safe",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output_path.is_file(), result.stdout + result.stderr
    export = json.loads(output_path.read_text(encoding="utf-8"))
    receipts = export["receipts"]
    disclosure_index = next(
        index for index, row in enumerate(receipts) if row["receipt_kind"] == "disclosure_outcome"
    )
    disclosure = receipts[disclosure_index]
    assert disclosure["payload"]["operation_code"] == "reveal_hint"
    assert disclosure["payload"]["state_effect"] == "fresh_disclosure"
    assert disclosure["prior_state_sha256"] != disclosure["next_state_sha256"]
    assert receipts[disclosure_index + 1]["receipt_kind"] == "commit_emitted"
    commit = receipts[disclosure_index + 1]
    assert commit["payload"]["operation_code"] == "reveal_hint"
    assert commit["prior_state_sha256"] == disclosure["next_state_sha256"]
    assert commit["next_state_sha256"] == disclosure["next_state_sha256"]
