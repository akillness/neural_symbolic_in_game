from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.run_playable_evaluation import (
    SANDBOXED_MACOS_HOST_ERROR,
    _run_godot,
    find_godot_4,
    stage_project,
)

ROOT = Path(__file__).parents[1]
GODOT_PROJECT = ROOT / "game-track" / "godot"
HARNESS = ROOT / "tests" / "godot_panel_lifecycle_harness.gd"
RESULT_PREFIX = "PANEL_LIFECYCLE_RESULT "
PREFIX_SNAPSHOT = (
    ROOT
    / "_workspace"
    / "current"
    / "qa"
    / "mobile-mira-choice-fix-pre"
    / "harbor_ledger_ui.gd.RED.52e4f8c9b0.pre"
)


def _ensure_project_imported(godot: str, staged_project: Path) -> None:
    command = [
        godot,
        "--headless",
        "--path",
        str(staged_project),
        "--import",
        "--log-file",
        str(staged_project.parent / "regression-import.log"),
    ]
    print("PANEL_REGRESSION_COMMAND " + json.dumps(command))
    _run_godot(
        command,
        label="panel project import",
        timeout=300,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )


def _run_panel_harness(godot: str, staged_project: Path) -> dict:
    command = [
        godot,
        "--headless",
        "--path",
        str(staged_project),
        "--script",
        f"res://tests/{HARNESS.name}",
        "--quit-after",
        "120",
        "--log-file",
        str(staged_project.parent / "regression-execution.log"),
    ]
    print("PANEL_REGRESSION_COMMAND " + json.dumps(command))
    result = _run_godot(
        command,
        label="panel lifecycle harness",
        timeout=60,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )
    output = result.stdout + result.stderr
    print(output)
    lines = [line for line in output.splitlines() if line.startswith(RESULT_PREFIX)]
    assert len(lines) == 1, f"panel harness must emit exactly one result marker:\n{output}"
    harness_result = json.loads(lines[0][len(RESULT_PREFIX) :])
    assert harness_result["passed"] is True, harness_result["failures"]
    assert harness_result["failures"] == []
    return harness_result


@pytest.fixture(scope="module")
def godot() -> str:
    try:
        executable, _version = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    return executable


@pytest.fixture
def staged_project(godot: str, tmp_path: Path) -> Path:
    project = tmp_path / "project"
    stage_project(GODOT_PROJECT, project)
    harness_target = project / "tests" / HARNESS.name
    harness_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HARNESS, harness_target)
    _ensure_project_imported(godot, project)
    return project


def test_contextual_ledger_dock_lifecycle_preserves_active_choices_and_overlays(
    godot: str,
    staged_project: Path,
) -> None:
    """Exercise the real presentation lifecycle without loading the source project."""
    _run_panel_harness(godot, staged_project)


def test_mobile_mira_choice_regression_is_red_against_immutable_pre_fix_snapshot(
    godot: str,
    staged_project: Path,
) -> None:
    """The preserved pre-fix UI bytes fail only in the disposable staged copy."""
    pre_fix_bytes = PREFIX_SNAPSHOT.read_bytes()
    staged_ui = staged_project / "scripts" / "game3d" / "harbor_ledger_ui.gd"
    source_before = staged_ui.read_bytes()
    staged_ui.write_bytes(pre_fix_bytes)
    assert staged_ui.read_bytes() == pre_fix_bytes
    with pytest.raises(RuntimeError, match=r"panel lifecycle harness failed \(exit=1\)") as caught:
        _run_panel_harness(godot, staged_project)
    assert "scroll-to-view authored Mira choice" in str(caught.value)
    assert staged_ui.read_bytes() == pre_fix_bytes
    assert (
        source_before == (GODOT_PROJECT / "scripts" / "game3d" / "harbor_ledger_ui.gd").read_bytes()
    )


@pytest.mark.parametrize(
    ("fault", "diagnostic"),
    [
        (
            'push_error("panel regression injected push_error")',
            "ERROR: panel regression injected push_error",
        ),
        (
            'assert(false, "panel regression injected script error")',
            "SCRIPT ERROR: Assertion failed: panel regression injected script error",
        ),
    ],
    ids=["push-error-with-zero-exit", "script-error-with-zero-exit"],
)
def test_panel_wrapper_rejects_zero_exit_errors_despite_passing_marker(
    godot: str,
    staged_project: Path,
    fault: str,
    diagnostic: str,
) -> None:
    """Engine errors must invalidate success even when a real script prints PASS."""
    (staged_project / "tests" / HARNESS.name).write_text(
        "extends SceneTree\n\n"
        "func _init() -> void:\n"
        "\t_inject_error()\n"
        f"\tprint('{RESULT_PREFIX}" + '{"passed":true,"failures":[]}' + "')\n"
        "\tquit(0)\n\n"
        "func _inject_error() -> void:\n"
        f"\t{fault}\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match=r"panel lifecycle harness failed \(exit=0\)") as caught:
        _run_panel_harness(godot, staged_project)
    output = str(caught.value)
    assert diagnostic in output
    assert RESULT_PREFIX + '{"passed":true,"failures":[]}' in output
    print("PANEL_REGRESSION_EXPECTED_REJECTION " + output)
