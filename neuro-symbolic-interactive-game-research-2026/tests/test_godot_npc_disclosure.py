from __future__ import annotations

import json
import os
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
HARNESS = ROOT / "tests" / "npc_disclosure_harness.gd"
RESULT_PREFIX = "NPC_DISCLOSURE_RESULT "


@pytest.fixture(scope="module")
def godot() -> str:
    try:
        executable, _version = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    return executable


def test_staged_canonical_writer_reveal_hint_contract(
    godot: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Run the disclosure writer only from a disposable staged project copy."""
    staged = tmp_path / "project"
    stage_project(GODOT_PROJECT, staged)
    shutil.copy2(HARNESS, staged / "tests" / HARNESS.name)
    receipt_path = Path(
        os.environ.get("NPC_DISCLOSURE_RECEIPT_PATH", str(tmp_path / "godot-receipt.json"))
    )
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    preflight = [godot, "--headless", "--editor", "--path", str(staged), "--quit"]
    _run_godot(
        preflight,
        label="staged Godot editor preflight",
        timeout=60,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )
    monkeypatch.setenv("NPC_DISCLOSURE_RECEIPT_PATH", str(receipt_path))
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
        str(tmp_path / "npc-disclosure.log"),
    ]
    result = _run_godot(
        command,
        label="staged NPC disclosure harness",
        timeout=60,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )
    output = result.stdout + result.stderr
    lines = [line for line in output.splitlines() if line.startswith(RESULT_PREFIX)]
    assert len(lines) == 1, output
    payload = json.loads(lines[0][len(RESULT_PREFIX) :])
    assert payload["passed"] is True, payload["failures"]
    assert payload["failures"] == []
    assert staged != GODOT_PROJECT
    assert receipt_path.is_file(), f"missing staged disclosure receipt: {receipt_path}"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["marker"] == "NPC_DISCLOSURE_RESULT"
    assert receipt["passed"] is True, receipt["failures"]
    assert receipt["failures"] == []
    assert (
        receipt["packet_sha256"]
        == "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"
    )
    assert receipt["scenario_source"] == "game-track/godot/data/sealed_lighthouse.json"
    assert set(receipt["source_hashes"]) == {
        "game-track/godot/scripts/game3d/game_3d.gd",
        "game-track/godot/scripts/sealed_lighthouse_machine.gd",
        "game-track/godot/data/sealed_lighthouse.json",
        "game-track/godot/scripts/evidence_capture_runner.gd",
        "game-track/godot/scripts/canonical_state.gd",
        "tests/npc_disclosure_harness.gd",
    }
    assert receipt["cases"], "receipt has no actual runtime cases"
    assert receipt["semantic_assertions"] == {
        "semantic_outcomes": True,
        "state_hash_binding": True,
        "display_safety": True,
        "canonical_recomputation": True,
    }
