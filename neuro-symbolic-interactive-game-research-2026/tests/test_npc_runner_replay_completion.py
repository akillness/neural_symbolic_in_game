from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "scripts"))

import run_npc_goal_experiment as runner
from run_npc_goal_experiment import DEFAULT_BUDGET, execute_assignment, load_cases, make_assignments
from validate_npc_goal_evidence import fixture_case

V5 = PROJECT / "data/fixtures/npc-goal-recovery/validated-v5"


class ReplayCompletionRegressionTests(unittest.TestCase):
    def _assignment(self) -> tuple[dict, dict]:
        packet = json.loads((V5 / "engineering.json").read_text(encoding="utf-8"))
        case = next(
            item
            for item in load_cases(V5 / "engineering.json", "NPC-ENG1", 16)
            if item["id"] == "ENG-S01"
        )
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
        return fixture_case(assignment, PROJECT), assignment

    @staticmethod
    def _tamper_trace(payload: dict) -> dict:
        initial = payload["initial_public_snapshot"]
        step = dict(payload["decision"]["body"]["steps"][0])
        step["operation"] = "tampered_operation"
        state_ref = copy.deepcopy(initial["state_ref"])
        action = {
            "action_id": step["action_id"],
            "arguments": copy.deepcopy(step["arguments"]),
            "codes": ["CONTENT_HASH_MISMATCH", "STEP_ARGUMENTS_INVALID", "STEP_BINDING_INVALID"],
            "execution_mode": step["execution_mode"],
            "index": 0,
            "observation_after": copy.deepcopy(initial["observation"]),
            "observation_before": copy.deepcopy(initial["observation"]),
            "operation": step["operation"],
            "result": {
                "accepted": False,
                "codes": [
                    "CONTENT_HASH_MISMATCH",
                    "STEP_ARGUMENTS_INVALID",
                    "STEP_BINDING_INVALID",
                ],
                "mutated": False,
            },
            "state_ref_after": copy.deepcopy(state_ref),
            "state_ref_before": copy.deepcopy(state_ref),
            "status": "REJECTED",
            "step": step,
        }
        return {
            "actions": [action],
            "errors": ["ACTION_NOT_APPLIED"],
            "final_state_ref": copy.deepcopy(state_ref),
            "initial_public_snapshot": copy.deepcopy(initial),
            "initial_state_ref": copy.deepcopy(state_ref),
            "passed": False,
            "status": "REJECTED",
            "terminal_status": "REJECTED",
        }

    def _run(self, replay_mutation: str | None = None) -> tuple[dict, dict[str, object]]:
        case, assignment = self._assignment()
        calls: dict[str, object] = {
            "bootstrap": 0,
            "experiment": 0,
            "replay": 0,
            "tamper": 0,
            "replay_content_comparison_inputs_match": False,
        }

        def fake_run_godot(*, mode: str, input_path: Path, **_: object) -> dict:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            if mode == "bootstrap":
                calls["bootstrap"] = int(calls["bootstrap"]) + 1
                snapshot = {
                    "observation": copy.deepcopy(case["observation"]),
                    "state_ref": copy.deepcopy(case["state_ref"]),
                }
                return {
                    "status": "completed",
                    "returncode": 0,
                    "input_bytes_preserved": True,
                    "trace": {
                        **snapshot,
                        "passed": True,
                        "policy_hash": assignment["policy_hash"],
                        "source_hashes": {"policy_hash": assignment["policy_hash"]},
                    },
                }

            if ".tamper." in input_path.name:
                calls["tamper"] = int(calls["tamper"]) + 1
                return {
                    "status": "failed",
                    "returncode": 1,
                    "input_exists": True,
                    "input_nonempty": True,
                    "input_bytes_preserved": True,
                    "trace": self._tamper_trace(payload),
                }

            initial = payload["initial_public_snapshot"]
            step = dict(payload["decision"]["body"]["steps"][0])
            after_observation = copy.deepcopy(initial["observation"])
            after_observation["lens_carried"] = True
            after_observation["lens_reachable"] = False
            after_state = {
                "revision": 1,
                "sha256": "19b474dcc12a962d8a43b0a33ceaa1d845f047dfa8c772e08095dcbfa463c498",
            }
            action = {
                "action_id": step["action_id"],
                "arguments": copy.deepcopy(step["arguments"]),
                "codes": [],
                "execution_mode": step["execution_mode"],
                "index": 0,
                "observation_after": after_observation,
                "observation_before": copy.deepcopy(initial["observation"]),
                "operation": step["operation"],
                "result": {"accepted": True, "codes": [], "mutated": True},
                "state_ref_after": after_state,
                "state_ref_before": copy.deepcopy(initial["state_ref"]),
                "status": "APPLIED",
                "step": copy.deepcopy(step),
            }
            trace = {
                "actions": [action],
                "decision": copy.deepcopy(payload["decision"]),
                "decision_sha256": payload["decision"].get("content_sha256"),
                "errors": [],
                "expected_negative_gates": [],
                "final_state_ref": copy.deepcopy(after_state),
                "initial_public_snapshot": copy.deepcopy(initial),
                "initial_state_ref": copy.deepcopy(initial["state_ref"]),
                "passed": True,
                "status": "APPLIED",
            }
            is_replay = ".engine_fixture_reexecution." in input_path.name
            if is_replay:
                calls["replay"] = int(calls["replay"]) + 1
                # The replay content is deliberately unchanged; only one completion signal is mutated.
                replay_trace = copy.deepcopy(trace)
                replay_result = {
                    "status": "completed",
                    "returncode": 0,
                    "input_bytes_preserved": True,
                    "trace": replay_trace,
                }
                if replay_mutation == "status_failed":
                    replay_result["status"] = "failed"
                elif replay_mutation == "returncode_nonzero":
                    replay_result["returncode"] = 7
                elif replay_mutation == "trace_not_passed":
                    replay_result["trace"]["passed"] = False
                elif replay_mutation == "input_not_preserved":
                    replay_result["input_bytes_preserved"] = False
                elif replay_mutation == "canonical_after_omitted":
                    replay_action = replay_result["trace"]["actions"][0]
                    replay_action["state_ref"] = replay_action.pop("state_ref_after")
                elif replay_mutation == "malformed_action":
                    replay_result["trace"]["actions"] = ["malformed-action-row"]
                    calls["replay_content_comparison_inputs_match"] = False
                if replay_mutation != "malformed_action":
                    calls["replay_content_comparison_inputs_match"] = True
                return replay_result
            calls["experiment"] = int(calls["experiment"]) + 1
            return {
                "status": "completed",
                "returncode": 0,
                "input_bytes_preserved": True,
                "trace": trace,
            }

        with (
            tempfile.TemporaryDirectory(prefix="npc-runner-replay-completion-") as directory,
            patch.object(runner, "run_godot", side_effect=fake_run_godot),
        ):
            record = execute_assignment(
                case,
                assignment,
                budget=DEFAULT_BUDGET,
                model=None,
                service_url=None,
                godot_binary="fake-godot",
                godot_project=PROJECT / "game-track" / "godot",
                output_dir=Path(directory),
                godot_timeout=1,
                skip_model=False,
            )
        return record, calls

    def _assert_native_prerequisites(self, record: dict, calls: dict[str, object]) -> None:
        self.assertEqual(calls["bootstrap"], 1)
        self.assertEqual(calls["experiment"], 1)
        self.assertEqual(calls["replay"], 1)
        self.assertEqual(calls["tamper"], 1)
        self.assertTrue(calls["replay_content_comparison_inputs_match"])
        self.assertEqual(record["model_calls"], 0)
        self.assertEqual(record["acks"][0]["body"]["status"], "ACCEPTED")
        self.assertTrue(record["replay"]["godot_tamper_rejected"])
        self.assertTrue(record["engine"]["replay_comparison"]["passed"])

    def test_native_replay_completion_positive_control_is_valid(self) -> None:
        record, calls = self._run()

        self._assert_native_prerequisites(record, calls)
        self.assertEqual(record["status"], "completed")
        self.assertTrue(record["replay"]["valid"])
        self.assertTrue(record["replay"]["engine_fixture_reexecution"]["valid"])

    def test_native_replay_completion_signals_each_fail_closed(self) -> None:
        for mutation in (
            "status_failed",
            "returncode_nonzero",
            "trace_not_passed",
            "input_not_preserved",
        ):
            with self.subTest(mutation=mutation):
                record, calls = self._run(mutation)
                self._assert_native_prerequisites(record, calls)
                self.assertFalse(record["replay"]["valid"])
                self.assertEqual(record["status"], "assigned_failure")
                self.assertIn(
                    "engine_fixture_reexecution_incomplete",
                    {failure["code"] for failure in record["failure"]},
                )

    def test_malformed_replay_action_is_assigned_failure_without_abort(self) -> None:
        record, calls = self._run("malformed_action")

        self.assertEqual(calls["bootstrap"], 1)
        self.assertEqual(calls["experiment"], 1)
        self.assertEqual(calls["replay"], 1)
        self.assertEqual(calls["tamper"], 1)
        self.assertEqual(record["model_calls"], 0)
        self.assertEqual(record["acks"][0]["body"]["status"], "ACCEPTED")
        self.assertTrue(record["replay"]["godot_tamper_rejected"])
        self.assertFalse(record["engine"]["replay_comparison"]["passed"])
        self.assertFalse(record["replay"]["valid"])
        self.assertEqual(record["status"], "assigned_failure")
        self.assertTrue(
            any(
                failure["category"] == "replay_failure"
                and failure["code"] == "engine_fixture_reexecution_mismatch"
                for failure in record["failure"]
            )
        )

    def test_replay_without_canonical_after_fails_closed(self) -> None:
        record, calls = self._run("canonical_after_omitted")

        self.assertEqual(calls["bootstrap"], 1)
        self.assertEqual(calls["experiment"], 1)
        self.assertEqual(calls["replay"], 1)
        self.assertEqual(calls["tamper"], 1)
        self.assertTrue(calls["replay_content_comparison_inputs_match"])
        self.assertEqual(record["model_calls"], 0)
        self.assertEqual(record["acks"][0]["body"]["status"], "ACCEPTED")
        self.assertTrue(record["replay"]["godot_tamper_rejected"])
        self.assertFalse(record["engine"]["replay_comparison"]["passed"])
        self.assertFalse(record["replay"]["valid"])
        self.assertEqual(record["status"], "assigned_failure")
        self.assertIn(
            "engine_fixture_reexecution_mismatch",
            {failure["code"] for failure in record["failure"]},
        )

    def test_non_list_empty_action_container_cannot_match_empty_trace(self) -> None:
        baseline = {
            "status": "APPLIED",
            "initial_state_ref": {"revision": 1, "sha256": "a" * 64},
            "final_state_ref": {"revision": 2, "sha256": "b" * 64},
            "decision_sha256": "d" * 64,
            "actions": [],
            "expected_negative_gates": [],
        }

        self.assertTrue(runner._engine_reexecution_comparison(baseline, baseline)["passed"])

        legacy_rows = dict(baseline)
        legacy_rows.pop("actions")
        legacy_rows["rows"] = []
        self.assertTrue(runner._engine_reexecution_comparison(baseline, legacy_rows)["passed"])

        for mutation in ("actions_mapping", "rows_string"):
            with self.subTest(mutation=mutation):
                malformed = dict(baseline)
                if mutation == "actions_mapping":
                    malformed["actions"] = {}
                else:
                    malformed.pop("actions")
                    malformed["rows"] = "bad"
                with self.assertRaisesRegex(TypeError, "engine_reexecution_actions_must_be_list"):
                    runner._engine_reexecution_comparison(baseline, malformed)

    def test_replay_report_excludes_incomplete_native_replays(self) -> None:
        positive, positive_calls = self._run()
        self._assert_native_prerequisites(positive, positive_calls)
        positive_report = runner.replay_report(
            [positive], packet_id="runner-replay-report-positive"
        )
        self.assertEqual(positive_report["denominators"]["godot_eligible"], 1)
        self.assertEqual(positive_report["denominators"]["godot_failed"], 0)
        self.assertEqual(len(positive_report["rows"]), 1)
        self.assertFalse(positive_report["rows"][0]["assigned_failure"])

        for mutation in (
            "status_failed",
            "returncode_nonzero",
            "trace_not_passed",
            "input_not_preserved",
        ):
            with self.subTest(mutation=mutation):
                record, calls = self._run(mutation)
                self._assert_native_prerequisites(record, calls)
                report = runner.replay_report(
                    [record], packet_id=f"runner-replay-report-{mutation}"
                )
                self.assertEqual(report["denominators"]["godot_eligible"], 0)
                self.assertEqual(report["denominators"]["godot_failed"], 1)
                self.assertEqual(len(report["rows"]), 1)
                self.assertTrue(report["rows"][0]["assigned_failure"])
                self.assertEqual(report["rows"][0]["status"], "assigned_failure")


if __name__ == "__main__":
    unittest.main()
