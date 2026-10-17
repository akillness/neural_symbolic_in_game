from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))
sys.path.insert(0, str(PROJECT / "src"))

import run_npc_goal_experiment as runner
from run_npc_goal_experiment import DEFAULT_BUDGET, execute_assignment, load_cases, make_assignments
from run_npc_service import DEFAULT_ALLOWED_ORIGINS, NpcServer, ServiceState
from validate_npc_goal_evidence import fixture_case

from nesy_game.npc_goal import GoalController, IntentInterpreter

CAPABILITY = "runner-capability-test"
V5 = PROJECT / "data/fixtures/npc-goal-recovery/validated-v5"


class RecordingInterpreter:
    arm = "R"
    model = None

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self._delegate = IntentInterpreter(arm="R")

    def interpret(self, *, request_id: str, utterance: str, timeout_ms: int | None = None) -> dict:
        self.calls.append((request_id, utterance))
        return self._delegate.interpret(
            request_id=request_id, utterance=utterance, timeout_ms=timeout_ms
        )


def _assignment() -> tuple[dict, dict]:
    packet = json.loads((V5 / "engineering.json").read_text(encoding="utf-8"))
    source = next(case for case in packet["cases"] if case["id"] == "ENG-W01")
    normalized = load_cases(V5 / "engineering.json", "NPC-ENG1", 16)
    case = next(case for case in normalized if case["id"] == "ENG-W01")
    assignment = make_assignments(
        [case],
        packet_id="NPC-ENG1",
        config_hash=case["config_hash"],
        npc_protocol_config_sha256=case["config_hash"],
        source_schema_sha256="c" * 64,
        source_project_config_sha256="d" * 64,
        policy_hash=packet["policy_hash"],
        budget=DEFAULT_BUDGET,
    )[0]
    # Keep this assertion tied to the immutable fixture selected for the transport test.
    assert source["expected_operation"] is None
    return fixture_case(assignment), assignment


def _fake_godot(case: dict, assignment: dict):
    def run_godot(*, mode: str, input_path: Path, **_: object) -> dict:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        snapshot = {
            "observation": deepcopy(case["observation"]),
            "state_ref": deepcopy(case["state_ref"]),
        }
        if mode == "bootstrap":
            return {
                "status": "completed",
                "returncode": 0,
                "input_exists": True,
                "input_nonempty": True,
                "input_bytes_preserved": True,
                "trace": {
                    **snapshot,
                    "passed": True,
                    "policy_hash": assignment["policy_hash"],
                    "source_hashes": {"policy_hash": assignment["policy_hash"]},
                },
            }
        trace = {
            "status": "NO_ROUTE",
            "terminal_status": "NO_ROUTE",
            "passed": True,
            "initial_state_ref": snapshot["state_ref"],
            "final_state_ref": snapshot["state_ref"],
            "decision_sha256": payload["decision"]["content_sha256"],
            "actions": [],
            "expected_negative_gates": [],
        }
        return {
            "status": "completed",
            "returncode": 0,
            "input_exists": True,
            "input_nonempty": True,
            "input_bytes_preserved": True,
            "trace": trace,
        }

    return run_godot


class NpcRunnerCapabilityTests(unittest.TestCase):
    def _run_assignment(self, capability: str | None) -> tuple[dict, RecordingInterpreter]:
        case, assignment = _assignment()
        interpreter = RecordingInterpreter()
        state = ServiceState(
            GoalController(interpreter=interpreter),
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
            base = f"http://127.0.0.1:{server.server_port}"
            with (
                tempfile.TemporaryDirectory() as directory,
                patch.object(runner, "run_godot", side_effect=_fake_godot(case, assignment)),
                patch.dict(
                    os.environ,
                    {} if capability is None else {"TRACE_RPG_NPC_CAPABILITY": capability},
                    clear=False,
                ),
            ):
                if capability is None:
                    os.environ.pop("TRACE_RPG_NPC_CAPABILITY", None)
                record = execute_assignment(
                    case,
                    assignment,
                    budget=DEFAULT_BUDGET,
                    model=None,
                    service_url=base,
                    godot_binary="fake-godot",
                    godot_project=PROJECT / "game-track" / "godot",
                    output_dir=Path(directory),
                    godot_timeout=1,
                    skip_model=False,
                )
            return record, interpreter
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_remote_post_authenticates_with_bearer_and_separates_replay_limit(self) -> None:
        record, interpreter = self._run_assignment(CAPABILITY)

        self.assertEqual(len(interpreter.calls), 1)
        self.assertIsNotNone(record["decision"])
        self.assertEqual(record["decision"]["body"]["status"], "NO_ROUTE")
        self.assertEqual(record["status"], "assigned_failure")
        self.assertEqual(
            {failure["code"] for failure in record["failure"]},
            {"remote_python_replay_unavailable"},
        )

    def test_remote_post_rejects_missing_or_wrong_capability_before_interpretation(self) -> None:
        for label, capability, expected_code in (
            ("missing", None, "capability_missing"),
            ("wrong", "not-the-service-capability", "HTTP Error 401"),
        ):
            with self.subTest(capability=label):
                record, interpreter = self._run_assignment(capability)
                self.assertEqual(interpreter.calls, [])
                self.assertIsNone(record["decision"])
                self.assertEqual(record["status"], "assigned_failure")
                self.assertTrue(
                    any(failure["code"].startswith(expected_code) for failure in record["failure"]),
                    record["failure"],
                )


if __name__ == "__main__":
    unittest.main()
