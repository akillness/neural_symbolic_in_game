from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from nesy_game.npc_goal import GoalController, Interpretation, ReplayValidator
from scripts.run_npc_service import (
    DEFAULT_ALLOWED_ORIGINS,
    NpcServer,
    ServiceState,
)
from scripts.run_playable_evaluation import (
    SANDBOXED_MACOS_HOST_ERROR,
    _run_godot,
    find_godot_4,
    stage_project,
)

ROOT = Path(__file__).parents[1]
GODOT_PROJECT = ROOT / "game-track" / "godot"
HARNESS = ROOT / "game-track" / "godot" / "tests" / "npc_play_loop_harness.gd"
TRANSPORT = ROOT / "game-track" / "godot" / "tests" / "npc_play_loop_transport.gd"
RESULT_PREFIX = "NPC_PLAY_LOOP_RESULT "
CAPABILITY = "npc-play-loop-test-capability"


class FakePInterpreter:
    """Explicit no-model P-arm interpreter; GoalController/planner/schema stay real."""

    arm = "P"
    model = None

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def interpret(
        self, *, request_id: str, utterance: str, timeout_ms: int | None = None
    ) -> Interpretation:
        del timeout_ms
        self.calls.append((request_id, utterance))
        return Interpretation(
            intent_id=f"{request_id}.intent",
            typed_intent={
                "label": "ASK_INFORMATION",
                "claims": [{"code": "NONE", "state": "UNVERIFIED"}],
                "target": "signal",
            },
            backend="codex",
            arm="P",
        )


@contextmanager
def running_fake_p_service() -> Iterator[tuple[str, ServiceState, FakePInterpreter]]:
    interpreter = FakePInterpreter()
    controller = GoalController(interpreter=interpreter)
    state = ServiceState(
        controller,
        allowed_origins=DEFAULT_ALLOWED_ORIGINS,
        max_workers=1,
        trace_output=None,
        capability=CAPABILITY,
        max_inference_calls=8,
        header_timeout=0.25,
        body_timeout=0.25,
    )
    server = NpcServer("127.0.0.1", 0, state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state, interpreter
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def _ensure_project_imported(godot: str, staged: Path) -> None:
    _run_godot(
        [
            godot,
            "--headless",
            "--path",
            str(staged),
            "--import",
            "--log-file",
            str(staged.parent / "npc-play-loop-import.log"),
        ],
        label="npc play-loop project import",
        timeout=300,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )


def _run_harness(
    godot: str,
    staged: Path,
    report_path: Path,
    *,
    real_service: bool = False,
    contract_regression: bool = False,
) -> dict[str, Any]:
    command = [
        godot,
        "--headless",
        "--path",
        str(staged),
        "--script",
        "res://tests/npc_play_loop_harness.gd",
        "--quit-after",
        "12000" if real_service else "1200",
        "--log-file",
        str(staged.parent / "npc-play-loop-execution.log"),
        "--",
    ]
    if real_service:
        command.extend(["--real-service", "--report-path", str(report_path)])
    else:
        command.extend(["--report-path", str(report_path)])
    if contract_regression:
        command.append("--contract-regression")
    print("NPC_PLAY_LOOP_COMMAND " + json.dumps(command))
    result = _run_godot(
        command,
        label="npc ordinary play-loop harness",
        timeout=120,
        allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
    )
    output = result.stdout + result.stderr
    lines = [line for line in output.splitlines() if line.startswith(RESULT_PREFIX)]
    assert len(lines) == 1, f"play-loop harness must emit exactly one result marker:\n{output}"
    report = json.loads(lines[0][len(RESULT_PREFIX) :])
    assert report["passed"] is True, report["errors"]
    assert report["errors"] == []
    assert report_path.is_file(), report
    return report


@pytest.fixture(scope="module")
def godot() -> str:
    try:
        executable, _version = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    return executable


@pytest.fixture
def staged_project(godot: str, tmp_path: Path) -> Path:
    staged = tmp_path / "project"
    stage_project(GODOT_PROJECT, staged)
    tests_dir = staged / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HARNESS, tests_dir / HARNESS.name)
    shutil.copy2(TRANSPORT, tests_dir / TRANSPORT.name)
    _ensure_project_imported(godot, staged)
    return staged


def test_real_scene_ordinary_play_loop_uses_one_interpretation_and_observation_recovery(
    godot: str,
    staged_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_project_hash = hashlib.sha256((GODOT_PROJECT / "project.godot").read_bytes()).hexdigest()
    report_path = tmp_path / "npc-play-loop.result.json"
    monkeypatch.setenv("TRACE_RPG_NPC_CAPABILITY", CAPABILITY)
    with running_fake_p_service() as (endpoint, service_state, interpreter):
        monkeypatch.setenv("NPC_PLAY_LOOP_ENDPOINT", endpoint)
        report = _run_harness(godot, staged_project, report_path)
        assert report["transport_mode"] == "injected_fake_http"
        assert report["real_wait_timeout_ms"] == 35000
        assert interpreter.calls and len(interpreter.calls) == 1
        assert (
            interpreter.calls[0][1]
            == "Please help me restore the harbor signal and then reveal the tide marks hint."
        )
        expected_raw_utterance_sha = hashlib.sha256(
            interpreter.calls[0][1].encode("utf-8")
        ).hexdigest()
        assert report["request_events"][0]["raw_utterance_sha256"] == expected_raw_utterance_sha
        assert (
            report["decision_provenance"][0]["raw_utterance_sha256"] == expected_raw_utterance_sha
        )
        assert (
            report["request_events"][0]["request_id"]
            == report["decision_provenance"][0]["request_id"]
        )
        assert report["events"]["event_kinds"] == [
            "utterance",
            "observation",
            "observation",
            "observation",
        ]
        assert report["events"]["request_count"] == 4
        assert report["events"]["decision_count"] == 4
        assert report["events"]["result_ack_count"] >= 1
        assert report["final_observation"]["goal_reached"] is True
        assert report["final_state_ref"]["revision"] == 3
        assert report["report_path_arg"] == "--report-path <path>"
        assert report["command_contract"].endswith("--quit-after 1200 -- --report-path <path>")
        assert report["session_id"]

        epochs = sorted(set(report["events"]["session_epochs"]))
        assert len(epochs) == 3, report["events"]
        replay_reports = []
        for epoch in epochs:
            snapshot = service_state.controller.export_trace(
                report["session_id"], session_epoch=epoch
            )
            replay = ReplayValidator.validate(snapshot, expected_session_id=report["session_id"])
            assert replay["valid"] is True
            assert replay["rows"] > 0
            replay_reports.append({"epoch": epoch, "rows": replay["rows"]})
        assert [row["epoch"] for row in replay_reports] == epochs
        assert service_state.inference_calls == 1

    assert (
        hashlib.sha256((GODOT_PROJECT / "project.godot").read_bytes()).hexdigest()
        == source_project_hash
    )


def test_godot_decision_contract_rejects_invalid_status_and_target(
    godot: str,
    staged_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Canonical decision validation rejects invalid status, target, and terminal shape."""
    report_path = tmp_path / "npc-contract.result.json"
    monkeypatch.setenv("TRACE_RPG_NPC_CAPABILITY", CAPABILITY)
    with running_fake_p_service() as (endpoint, _service_state, _interpreter):
        monkeypatch.setenv("NPC_PLAY_LOOP_ENDPOINT", endpoint)
        report = _run_harness(
            godot,
            staged_project,
            report_path,
            contract_regression=True,
        )

    controls = {str(control["name"]): control for control in report["contract_controls"]}
    expected_negative = {
        "status_cancelled_rejected",
        "status_failed_rejected",
        "status_unknown_rejected",
        "arbitrary_target_rejected",
        "empty_error_rejected",
    }
    assert expected_negative <= controls.keys()
    assert all(controls[name]["passed"] is True for name in expected_negative), controls
    assert all(controls[name]["accepted"] is False for name in expected_negative), controls
    assert all(controls[name]["directive_delta"] == 0 for name in expected_negative), controls
    assert all(controls[name]["state_unchanged"] is True for name in expected_negative), controls
    assert all(
        "state_ref_before" in controls[name] and "state_ref_after" in controls[name]
        for name in expected_negative
    ), controls
    assert controls["valid_player_action"]["passed"] is True, controls
    assert controls["valid_dialogue_action"]["passed"] is True, controls
    assert "goal" in report["phases"], report


@pytest.mark.skipif(
    os.environ.get("NPC_PLAY_LOOP_REAL_SERVICE") != "1",
    reason="optional paid real-service mode; set NPC_PLAY_LOOP_REAL_SERVICE=1 explicitly",
)
def test_optional_real_service_mode_uses_existing_endpoint_and_report_contract(
    godot: str,
    staged_project: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Opt-in only: parent supplies the existing endpoint and capability, never this test."""
    capability = os.environ.get("NPC_PLAY_LOOP_CAPABILITY", "").strip()
    if not capability:
        pytest.fail("NPC_PLAY_LOOP_CAPABILITY must be supplied for optional real-service mode")
    report_path = tmp_path / "npc-play-loop.real-service.result.json"
    monkeypatch.delenv("NPC_PLAY_LOOP_ENDPOINT", raising=False)
    monkeypatch.setenv("TRACE_RPG_NPC_CAPABILITY", capability)
    report = _run_harness(godot, staged_project, report_path, real_service=True)
    assert report["mode"] == "real_service"
    assert report["transport_mode"] == "production_super_send"
    assert report["phases"][-1] == "goal"
    assert report["report_path_arg"] == "--report-path <path>"
    assert report["command_contract"].endswith(
        "--quit-after 12000 -- --real-service --report-path <path>"
    )
    assert report["final_observation"]["goal_reached"] is True
    assert report["errors"] == []
