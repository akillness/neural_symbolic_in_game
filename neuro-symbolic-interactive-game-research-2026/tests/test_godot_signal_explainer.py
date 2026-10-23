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
HARNESS = ROOT / "tests" / "signal_explainer_harness.gd"
RESULT_PREFIX = "SIGNAL_EXPLAINER_RESULT "


@pytest.fixture(scope="module")
def godot() -> str:
    try:
        executable, _version = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    return executable


def _run_signal_harness(godot: str, staged: Path) -> dict:
    preflight = [godot, "--headless", "--editor", "--path", str(staged), "--quit"]
    _run_godot(
        preflight,
        label="staged signal explainer editor preflight",
        timeout=60,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )
    command = [
        godot,
        "--headless",
        "--path",
        str(staged),
        "--script",
        f"res://tests/{HARNESS.name}",
        "--quit-after",
        "120",
        "--log-file",
        str(staged.parent / "signal-explainer.log"),
    ]
    result = _run_godot(
        command,
        label="staged signal explainer harness",
        timeout=60,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )
    output = result.stdout + result.stderr
    lines = [line for line in output.splitlines() if line.startswith(RESULT_PREFIX)]
    assert len(lines) == 1, (
        f"signal explainer harness must emit exactly one result marker:\n{output}"
    )
    payload = json.loads(lines[0][len(RESULT_PREFIX) :])
    assert payload["passed"] is True, payload["failures"]
    assert payload["failures"] == []
    return payload


def _stage_signal_project(godot: str, tmp_path: Path, *, template_unavailable: bool) -> dict:
    staged = tmp_path / ("project-template-unavailable" if template_unavailable else "project")
    stage_project(GODOT_PROJECT, staged)
    harness_target = staged / "tests" / HARNESS.name
    harness_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HARNESS, harness_target)
    if template_unavailable:
        capture_runner = staged / "scripts" / "evidence_capture_runner.gd"
        source = capture_runner.read_text(encoding="utf-8")
        old = '"sl-rc-003-authorized-hint"'
        assert source.count(old) == 1
        capture_runner.write_text(source.replace(old, '"sl-rc-003-missing"'), encoding="utf-8")
    result = _run_signal_harness(godot, staged)
    assert staged != GODOT_PROJECT
    return result


def test_staged_signal_explainer_is_opt_in_read_only_and_matches_live_disclosure_outcomes(
    godot: str, tmp_path: Path
) -> None:
    """Exercise real denied/fresh/redisplay routes without importing the source project."""
    report = _stage_signal_project(godot, tmp_path, template_unavailable=False)
    assert report["cases"] == [
        "startup_and_waiting",
        "denied",
        "fresh",
        "redisplay",
        "panel_lifecycle",
    ]


def test_staged_signal_explainer_fails_closed_when_authorized_template_is_unavailable(
    godot: str, tmp_path: Path
) -> None:
    """A missing authorized display template is denied, not rendered as a fabricated check."""
    report = _stage_signal_project(godot, tmp_path, template_unavailable=True)
    assert report["cases"] == [
        "startup_and_waiting",
        "denied",
        "template_unavailable",
        "panel_lifecycle",
    ]
