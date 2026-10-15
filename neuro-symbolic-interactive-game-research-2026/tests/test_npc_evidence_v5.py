from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

P = Path(
    "/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026"
)
sys.path.insert(0, str(P / "scripts"))

import run_npc_goal_experiment as experiment_runner
import validate_npc_goal_evidence as evidence_validator
from run_npc_goal_experiment import (
    DEFAULT_BUDGET,
    execute_assignment,
    load_cases,
    make_assignments,
    replay_report,
    run_godot,
    write_jsonl_preserving,
)
from validate_npc_goal_evidence import (
    _core_rebased_replay_envelope,
    _validate_result_ack_contract,
    digest,
    fixture_case,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
V5 = P / "data/fixtures/npc-goal-recovery/validated-v5"


class NpcValidatedV5EvidenceTests(unittest.TestCase):
    def _packet(self, name: str) -> dict:
        return json.loads((V5 / name).read_text(encoding="utf-8"))

    def test_v5_packets_have_frozen_counts_and_portable_case_refs(self) -> None:
        expected = {"engineering.json": 16, "screening.json": 12}
        for filename, count in expected.items():
            with self.subTest(packet=filename):
                packet = self._packet(filename)
                self.assertEqual(len(packet["cases"]), count)
                for case in packet["cases"]:
                    ref = case["fixture_ref"]
                    self.assertTrue(ref.startswith("data/fixtures/npc-goal-recovery/validated-v5/"))
                    self.assertFalse(Path(ref).is_absolute())
                    self.assertNotIn("..", Path(ref).parts)
                    self.assertTrue(SHA256.fullmatch(case["raw_utterance_sha256"]))
                    self.assertTrue(SHA256.fullmatch(case["fixture_ref_sha256"]))
                    self.assertTrue(SHA256.fullmatch(case["bootstrap_receipt_sha256"]))

    def test_true_goal_case_does_not_fabricate_expected_goal_field(self) -> None:
        packet = self._packet("screening.json")
        case = next(case for case in packet["cases"] if case["id"] == "SCR-D02")
        self.assertTrue(case["observation"]["goal_reached"])
        self.assertNotIn("expected_goal_reached", case)
        self.assertIsNone(case["expected_operation"])
        # The v5 packet is intentionally checked before the validator's v5 path cutover;
        # no derived expected-goal field may be introduced during normalization.

    def test_correction_metadata_proves_pre_model_actual_bootstrap_skip_gate(self) -> None:
        metadata = json.loads((V5 / "correction-manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(metadata["pre_model"])
        self.assertEqual(metadata["model_calls"], 0)
        self.assertEqual(metadata["integrity"]["receipt_status_required"], "passed")
        self.assertEqual(
            metadata["integrity"]["bootstrap_receipts"],
            "actual_disposable_godot_headless_bootstrap",
        )
        self.assertEqual(
            metadata["counts"],
            {"engineering_cases": 16, "screening_cases": 12, "source_independent_fraction": 0},
        )
        self.assertFalse(metadata["claims"]["efficacy"])
        self.assertFalse(metadata["claims"]["human_authored_labels"])

    def test_each_v5_case_binds_actual_bootstrap_receipt_and_source_hashes(self) -> None:
        for filename in ("engineering.json", "screening.json"):
            packet = self._packet(filename)
            for case in packet["cases"]:
                with self.subTest(case=case["id"]):
                    self.assertTrue(case["bootstrap_receipt_ref"].startswith("bootstrap/"))
                    self.assertEqual(case["bootstrap_receipt_ref"].count("/"), 1)
                    self.assertIsInstance(case["source_hashes"], dict)
                    self.assertTrue(
                        all(SHA256.fullmatch(value) for value in case["source_hashes"].values())
                    )
                    self.assertEqual(case["source_kind"], "same_model_family_auxiliary")

    def test_load_cases_admits_only_validated_v5_packets(self) -> None:
        cases = load_cases(V5 / "engineering.json", "NPC-ENG1", 16)
        self.assertEqual(len(cases), 16)
        with tempfile.TemporaryDirectory() as directory:
            legacy = Path(directory) / "legacy.json"
            payload = self._packet("engineering.json")
            payload["schema_version"] = "npc-goal-recovery/validated-v4"
            legacy.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "validated-v5"):
                load_cases(legacy, "NPC-ENG1", 16)

    def test_cli_dry_run_freezes_v5_manifest_without_staging_or_model_calls(self) -> None:
        script = P / "scripts/run_npc_goal_experiment.py"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dry-run"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(script),
                    "--packet",
                    "screening",
                    "--dry-run",
                    "--output-dir",
                    str(output),
                ],
                cwd=P,
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            manifest = json.loads(
                (output / "screening-assignment-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["schema_version"], "npc-goal-recovery/evidence-1")
            self.assertEqual(manifest["assignment_count"], 72)
            self.assertEqual(manifest["packet_id"], "NPC-SCR1")
            assignments = manifest["assignments"]
            self.assertEqual(len({row["assignment_key"] for row in assignments}), 72)
            self.assertTrue(all(SHA256.fullmatch(row["assignment_key"]) for row in assignments))
            self.assertTrue(
                all(
                    row["fixture_ref"].startswith("data/fixtures/npc-goal-recovery/validated-v5/")
                    for row in assignments
                )
            )
            self.assertTrue(
                all(
                    row["source_kind"] == "same_model_family_auxiliary"
                    and not row["independent_source"]
                    for row in assignments
                )
            )
            self.assertFalse((output / "screening-results.jsonl").exists())
            self.assertFalse((output / "godot-project").exists())
            self.assertEqual(
                json.loads((output / "source-manifest.json").read_text(encoding="utf-8"))[
                    "cli_exec_attempt_count"
                ],
                0,
            )

    def test_cli_preflight_and_dry_run_reject_canonical_publish_directory(self) -> None:
        script = P / "scripts/run_npc_goal_experiment.py"
        canonical = P / "research/academic-pipeline/npc-goal-recovery/verified-run-002"
        for flag in ("--dry-run", "--skip-model"):
            with self.subTest(flag=flag):
                completed = subprocess.run(
                    [
                        sys.executable,
                        str(script),
                        "--packet",
                        "screening",
                        flag,
                        "--output-dir",
                        str(canonical),
                    ],
                    cwd=P,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=120,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("canonical publish output is forbidden", completed.stderr)

    def test_godot_timeout_and_launch_failures_are_assigned_failure_signals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "input.json"
            input_path.write_text("{}", encoding="utf-8")
            log_dir = root / "logs"
            sleeper = root / "sleep-godot"
            sleeper.write_text("#!/bin/sh\nsleep 2\n", encoding="utf-8")
            sleeper.chmod(0o755)
            timed_out = run_godot(
                binary=str(sleeper),
                project=P,
                mode="bootstrap",
                input_path=input_path,
                log_dir=log_dir,
                timeout=0.01,
            )
            self.assertEqual(timed_out["status"], "deadline_timeout")
            self.assertEqual(timed_out["error"], "godot_deadline")
            broken = root / "broken-godot"
            broken.write_text("#!/no/such/interpreter\n", encoding="utf-8")
            broken.chmod(0o755)
            launch_failed = run_godot(
                binary=str(broken),
                project=P,
                mode="bootstrap",
                input_path=input_path,
                log_dir=log_dir,
                timeout=1,
            )
            self.assertEqual(launch_failed["status"], "launch_failed")
            self.assertEqual(launch_failed["error"], "FileNotFoundError")

    def test_existing_assignment_result_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "results.jsonl"
            write_jsonl_preserving(path, [{"assignment_id": "A", "status": "assigned_failure"}])
            write_jsonl_preserving(
                path,
                [
                    {"assignment_id": "A", "status": "completed"},
                    {"assignment_id": "B", "status": "assigned_failure"},
                ],
            )
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(
                rows,
                [
                    {"assignment_id": "A", "status": "assigned_failure"},
                    {"assignment_id": "B", "status": "assigned_failure"},
                ],
            )

    def test_null_policy_and_snapshot_admission_never_invokes_model(self) -> None:
        cases = load_cases(V5 / "engineering.json", "NPC-ENG1", 16)
        case = cases[0]
        assignment = make_assignments(
            [case],
            packet_id="NPC-ENG1",
            config_hash="a" * 64,
            npc_protocol_config_sha256="b" * 64,
            source_schema_sha256="c" * 64,
            source_project_config_sha256="d" * 64,
            policy_hash=None,
            budget=DEFAULT_BUDGET,
        )[0]
        with tempfile.TemporaryDirectory() as directory:
            record = execute_assignment(
                case,
                assignment,
                budget=DEFAULT_BUDGET,
                model=None,
                service_url=None,
                godot_binary="/definitely/missing-godot",
                godot_project=P / "game-track" / "godot",
                output_dir=Path(directory),
                godot_timeout=1,
                skip_model=False,
            )
        codes = {failure["code"] for failure in record["failure"]}
        self.assertEqual(record["status"], "assigned_failure")
        self.assertEqual(record["model_calls"], 0)
        self.assertIn("policy_hash_unavailable", codes)
        self.assertIn("public_snapshot_unavailable", codes)

    def _s01_assignment(self) -> tuple[dict, dict]:
        normalized = next(
            case
            for case in load_cases(V5 / "engineering.json", "NPC-ENG1", 16)
            if case["id"] == "ENG-S01"
        )
        assignment = make_assignments(
            [normalized],
            packet_id="NPC-ENG1",
            config_hash=normalized["config_hash"],
            npc_protocol_config_sha256=normalized["config_hash"],
            source_schema_sha256="c" * 64,
            source_project_config_sha256="d" * 64,
            policy_hash=self._packet("engineering.json")["policy_hash"],
            budget=DEFAULT_BUDGET,
        )[0]
        return fixture_case(assignment), assignment

    def _tamper_trace(self, payload: dict, variant: str) -> dict | None:
        initial = payload["initial_public_snapshot"]
        step = dict(payload["decision"]["body"]["steps"][0])
        step["operation"] = "tampered_operation"
        state_ref = deepcopy(initial["state_ref"])
        row = {
            "action_id": step["action_id"],
            "arguments": deepcopy(step["arguments"]),
            "codes": ["CONTENT_HASH_MISMATCH", "STEP_ARGUMENTS_INVALID", "STEP_BINDING_INVALID"],
            "execution_mode": step["execution_mode"],
            "index": 0,
            "observation_after": deepcopy(initial["observation"]),
            "observation_before": deepcopy(initial["observation"]),
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
            "state_ref_after": deepcopy(state_ref),
            "state_ref_before": deepcopy(state_ref),
            "status": "REJECTED",
            "step": deepcopy(step),
        }
        trace = {
            "actions": [row],
            "errors": ["ACTION_NOT_APPLIED"],
            "final_state_ref": deepcopy(state_ref),
            "initial_public_snapshot": deepcopy(initial),
            "initial_state_ref": deepcopy(state_ref),
            "passed": False,
            "status": "REJECTED",
            "terminal_status": "REJECTED",
        }
        if variant == "missing-sidecar":
            return None
        if variant == "no-rows":
            trace["actions"] = []
        elif variant == "no-rejection":
            trace["actions"] = []
            trace["errors"] = []
            trace["status"] = "FAILED"
            trace["terminal_status"] = "FAILED"
        elif variant == "unexpected-runtime-error":
            trace["errors"] = ["SCRIPT_ERROR"]
            trace["status"] = "FAILED"
            trace["terminal_status"] = "FAILED"
        elif variant == "weak-rejection":
            trace["actions"][0]["codes"] = []
            trace["actions"][0]["result"]["codes"] = []
        elif variant == "applied-row":
            applied = deepcopy(row)
            applied["status"] = "APPLIED"
            applied["result"] = {"accepted": True, "codes": [], "mutated": True}
            applied["codes"] = []
            trace["actions"].append(applied)
        elif variant == "changed-state":
            changed = {"revision": state_ref["revision"] + 1, "sha256": "e" * 64}
            trace["actions"][0]["state_ref_after"] = changed
            trace["final_state_ref"] = deepcopy(changed)
        return trace

    def _execute_s01_tamper(
        self, variant: str, *, returncode: int = 1, ack_variant: str | None = None
    ) -> dict:
        case, assignment = self._s01_assignment()

        def fake_run_godot(*, mode: str, input_path: Path, **_: object) -> dict:
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            input_flags = {
                "input_exists": True,
                "input_nonempty": True,
                "input_bytes_preserved": True,
            }
            if mode == "bootstrap":
                initial = {
                    "observation": deepcopy(case["observation"]),
                    "state_ref": deepcopy(case["state_ref"]),
                }
                trace = {
                    "actual_state_ref": deepcopy(case["state_ref"]),
                    "initial_public_snapshot": initial,
                    "initial_state_ref": deepcopy(case["state_ref"]),
                    "observation": deepcopy(case["observation"]),
                    "passed": True,
                    "policy_hash": assignment["policy_hash"],
                    "source_hashes": {"policy_hash": assignment["policy_hash"]},
                }
                return {"status": "completed", "returncode": 0, "trace": trace, **input_flags}
            if ".tamper." in input_path.name:
                trace = self._tamper_trace(payload, variant)
                return {
                    "status": "failed" if returncode else "completed",
                    "returncode": returncode,
                    "trace": trace,
                    **input_flags,
                }
            initial = payload["initial_public_snapshot"]
            step = dict(payload["decision"]["body"]["steps"][0])
            after_observation = deepcopy(initial["observation"])
            after_observation["lens_carried"] = True
            after_observation["lens_reachable"] = False
            after_state = {
                "revision": 1,
                "sha256": "19b474dcc12a962d8a43b0a33ceaa1d845f047dfa8c772e08095dcbfa463c498",
            }
            action = {
                "action_id": step["action_id"],
                "arguments": deepcopy(step["arguments"]),
                "codes": [],
                "execution_mode": step["execution_mode"],
                "index": 0,
                "observation_after": after_observation,
                "observation_before": deepcopy(initial["observation"]),
                "operation": step["operation"],
                "result": {"accepted": True, "codes": [], "mutated": True},
                "state_ref_after": after_state,
                "state_ref_before": deepcopy(initial["state_ref"]),
                "status": "APPLIED",
                "step": deepcopy(step),
            }
            trace = {
                "actions": [action],
                "decision": deepcopy(payload["decision"]),
                "decision_sha256": payload["decision"].get("content_sha256"),
                "errors": [],
                "expected_negative_gates": [],
                "final_state_ref": deepcopy(after_state),
                "initial_public_snapshot": deepcopy(initial),
                "initial_state_ref": deepcopy(initial["state_ref"]),
                "passed": True,
                "status": "APPLIED",
            }
            return {"status": "completed", "returncode": 0, "trace": trace, **input_flags}

        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(
                patch.object(experiment_runner, "run_godot", side_effect=fake_run_godot)
            )
            if ack_variant is not None:
                original_handle_result = experiment_runner.GoalController.handle_result

                def fake_handle_result(controller: object, envelope: dict) -> dict | None:
                    if ack_variant == "missing":
                        return None
                    ack = original_handle_result(controller, envelope)
                    if ack_variant == "nonaccepted":
                        mutated = deepcopy(ack)
                        mutated["body"] = {
                            **mutated["body"],
                            "status": "REJECTED",
                            "error": "synthetic_rejection",
                        }
                        mutated["content_sha256"] = experiment_runner.digest(
                            {
                                key: value
                                for key, value in mutated.items()
                                if key != "content_sha256"
                            }
                        )
                        return mutated
                    if ack_variant == "mismatched-request-id":
                        mutated = deepcopy(ack)
                        mutated["request_id"] = "request-mismatch"
                        mutated["content_sha256"] = experiment_runner.digest(
                            {
                                key: value
                                for key, value in mutated.items()
                                if key != "content_sha256"
                            }
                        )
                        return mutated
                    return ack

                stack.enter_context(
                    patch.object(
                        experiment_runner.GoalController,
                        "handle_result",
                        fake_handle_result,
                    )
                )
            return execute_assignment(
                case,
                assignment,
                budget=DEFAULT_BUDGET,
                model=None,
                service_url=None,
                godot_binary="fake-godot",
                godot_project=P / "game-track" / "godot",
                output_dir=Path(directory),
                godot_timeout=1,
                skip_model=False,
            )

    def test_validator_requires_tamper_clone_to_clear_controls_and_preserve_setup(self) -> None:
        state_ref = {"revision": 0, "sha256": "a" * 64}
        observation = {
            "lens_reachable": True,
            "lens_carried": False,
            "signal_restored": False,
            "tide_lead_authorized": False,
            "goal_reached": False,
            "in_dialogue": True,
        }
        snapshot = {"state_ref": state_ref, "observation": observation}
        context = {
            "session_id": "session-test",
            "episode_id": "episode-test",
            "session_epoch": 0,
            "request_id": "request-test",
            "goal_id": experiment_runner.GOAL_ID,
            "goal_version": experiment_runner.GOAL_VERSION,
            "config_hash": "c" * 64,
        }
        decision = {
            "body": {
                "steps": [
                    {
                        "operation": "acquire_object",
                        "action_id": "action-test",
                        "arguments": {},
                        "execution_mode": "npc",
                    }
                ]
            }
        }
        experiment_input = {
            "request_context": context,
            "request": context,
            "decision": decision,
            "initial_public_snapshot": snapshot,
            "setup_operations": [{"operation": "setup"}],
            "seed_world_events": [{"event": "seed"}],
            "mutations": [
                {"code": "no_route"},
                {"code": "fixture-playeraction", "operation": "acquire_object"},
            ],
        }
        expected_hashes = {
            "config_hash": "c" * 64,
            "source_project_config_sha256": "s" * 64,
            "npc_protocol_config_sha256": "c" * 64,
            "source_schema_sha256": "h" * 64,
            "policy_hash": "p" * 64,
        }
        action = {
            "action_id": "action-test",
            "operation": "acquire_object",
            "status": "APPLIED",
            "result": {"accepted": True, "mutated": True},
            "state_ref_before": state_ref,
            "state_ref_after": state_ref,
            "observation_before": observation,
            "observation_after": observation,
        }
        experiment_report = {
            "passed": True,
            "assignment_id": "A",
            "fixture_ref": "fixture#CASE",
            "policy_hash": expected_hashes["policy_hash"],
            "source_hashes": expected_hashes,
            "initial_public_snapshot": snapshot,
            "final_state_ref": state_ref,
            "decision": decision,
            "decision_sha256": evidence_validator.digest(decision),
            "request_context": context,
            "request": context,
            "actions": [action],
            "expected_negative_gates": [],
        }
        tamper_report = {
            "initial_state_ref": state_ref,
            "final_state_ref": state_ref,
            "actions": [
                {**action, "status": "REJECTED", "result": {"accepted": False, "mutated": False}}
            ],
        }

        replay_input = deepcopy(experiment_input)

        def run_variant(variant: str) -> list[str]:
            temporary_paths: list[Path] = []

            tamper_input = deepcopy(experiment_input)
            tamper_input["mutations"] = []
            tamper_input["decision"]["body"]["steps"][0]["operation"] = "tampered_operation"
            if variant == "inherited-controls":
                tamper_input["mutations"] = deepcopy(experiment_input["mutations"])
            elif variant == "changed-setup":
                tamper_input["setup_operations"] = [{"operation": "different-setup"}]
            metadata = {
                "bootstrap": {
                    "status": "completed",
                    "input_bytes_preserved": True,
                    "trace": {
                        "passed": True,
                        "policy_hash": expected_hashes["policy_hash"],
                        "source_hashes": expected_hashes,
                        "state_ref": state_ref,
                    },
                },
                "experiment": {
                    "status": "completed",
                    "input_bytes_preserved": True,
                    "trace": experiment_report,
                },
                "replay": {
                    "replay_kind": "engine_fixture_reexecution",
                    "mode": "experiment",
                    "status": "completed",
                    "trace": experiment_report,
                },
                "tamper_reexecution": {"status": "failed", "returncode": 1, "trace": tamper_report},
                "replay_comparison": {"passed": True},
            }
            payloads = {
                "bootstrap": ({}, metadata["bootstrap"]["trace"]),
                "experiment": (experiment_input, experiment_report),
                "replay": (replay_input, experiment_report),
                "tamper": (tamper_input, tamper_report),
            }

            def stage(_root, _packet, _metadata, stage_name, _where, _errors, _artifact_root):
                payload, sidecar = payloads[stage_name]
                if stage_name in {"experiment", "replay"}:
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".json", delete=False
                    ) as handle:
                        handle.write(json.dumps(payload, sort_keys=True))
                        path = Path(handle.name)
                    temporary_paths.append(path)
                    return path, None, sidecar, payload
                return None, None, sidecar, payload

            record = {
                "status": "completed",
                "assignment_id": "A",
                "state_ref_before": state_ref,
                "state_ref_after": state_ref,
                "observation_before": observation,
                "decision": decision,
                "engine": metadata,
            }
            assignment = {"assignment_id": "A", "fixture_ref": "fixture#CASE"}
            errors: list[str] = []
            with (
                patch.object(
                    evidence_validator,
                    "fixture_case",
                    return_value={
                        "state_ref": state_ref,
                        "observation": observation,
                        "mutations": [],
                    },
                ),
                patch.object(evidence_validator, "config_hash", return_value="c" * 64),
                patch.object(
                    evidence_validator, "source_project_config_hash", return_value="s" * 64
                ),
                patch.object(evidence_validator, "sha256_file", return_value="h" * 64),
                patch.object(evidence_validator, "_stage_files", side_effect=stage),
                patch.object(evidence_validator, "_validate_native_input"),
                patch.object(evidence_validator, "_validate_action_transition"),
                patch.object(
                    evidence_validator,
                    "_engine_reexecution_comparison",
                    return_value={"passed": True},
                ),
                patch.object(
                    evidence_validator, "_tamper_rejected_from_evidence", return_value=True
                ),
            ):
                evidence_validator._validate_engine(
                    record, assignment, errors, "record[0]", expected_hashes["policy_hash"], P, P
                )
            for path in temporary_paths:
                path.unlink(missing_ok=True)
            return errors

        valid_errors = run_variant("valid")
        self.assertFalse(
            any(
                "tamper input did not isolate" in error or "tamper probe must omit" in error
                for error in valid_errors
            )
        )
        self.assertFalse(any("native replay input bytes differ" in error for error in valid_errors))
        inherited_errors = run_variant("inherited-controls")
        self.assertTrue(
            any(
                "tamper probe must omit inherited fixture mutations" in error
                for error in inherited_errors
            )
        )
        changed_setup_errors = run_variant("changed-setup")
        self.assertTrue(
            any(
                "tamper input did not isolate one decision operation change" in error
                for error in changed_setup_errors
            )
        )

    def test_core_replay_rebases_result_metadata_without_relaxing_identity(self) -> None:
        source = {
            "message_type": "result",
            "session_id": "session-1",
            "request_id": "request-1",
            "event_id": "event-1",
            "body": {
                "action_id": "action-1",
                "operation": "acquire_object",
                "status": "APPLIED",
            },
            "sequence": 3,
            "delivery_index": 3,
            "content_sha256": "stale-content-hash",
            "previous_hash": "stale-previous-hash",
            "hash": "stale-record-hash",
        }
        replay_row = deepcopy(source)
        replay_row["sequence"] = 2
        replay_row["delivery_index"] = 2
        replay_row["previous_hash"] = "0" * 64

        rebased = _core_rebased_replay_envelope(source, replay_row)
        content = deepcopy(source)
        for key in ("hash", "previous_hash", "content_sha256"):
            content.pop(key, None)
        content["sequence"] = 2
        content["delivery_index"] = 2
        content_sha256 = digest(content)
        self.assertEqual(rebased["content_sha256"], content_sha256)
        content["content_sha256"] = content_sha256
        self.assertEqual(
            rebased["hash"],
            digest(
                {
                    "record": {
                        key: value
                        for key, value in content.items()
                        if key not in {"hash", "previous_hash"}
                    },
                    "previous_hash": "0" * 64,
                }
            ),
        )
        self.assertEqual(rebased["body"], source["body"])
        self.assertEqual(rebased["request_id"], source["request_id"])
        changed_source = deepcopy(source)
        changed_source["body"]["operation"] = "tampered_operation"
        self.assertNotEqual(
            _core_rebased_replay_envelope(changed_source, replay_row),
            rebased,
        )

    def test_exit_one_canonical_rejection_is_successful_negative_gate(self) -> None:
        record = self._execute_s01_tamper("valid")
        self.assertEqual(record["status"], "completed")
        self.assertTrue(record["replay"]["godot_tamper_rejected"])
        self.assertNotIn(
            "tamper_replay_evidence_missing", {item["code"] for item in record["failure"]}
        )
        self.assertEqual(record["engine"]["tamper_reexecution"]["returncode"], 1)

    def test_exit_one_missing_or_invalid_negative_evidence_remains_assigned_failure(self) -> None:
        for variant in ("missing-sidecar", "no-rows", "no-rejection", "unexpected-runtime-error"):
            with self.subTest(variant=variant):
                record = self._execute_s01_tamper(variant)
                self.assertEqual(record["status"], "assigned_failure")
                self.assertFalse(record["replay"].get("godot_tamper_rejected", False))

    def test_missing_first_result_ack_is_assigned_failure(self) -> None:
        record = self._execute_s01_tamper("valid", ack_variant="missing")
        self.assertEqual(record["status"], "assigned_failure")
        self.assertIn("result_ack_not_accepted", {item["code"] for item in record["failure"]})

    def test_nonaccepted_first_result_ack_is_assigned_failure(self) -> None:
        record = self._execute_s01_tamper("valid", ack_variant="nonaccepted")
        self.assertEqual(record["status"], "assigned_failure")
        self.assertIn("result_ack_not_accepted", {item["code"] for item in record["failure"]})

    def test_validator_rejects_missing_or_nonaccepted_first_ack(self) -> None:
        for variant in ("missing", "nonaccepted"):
            with self.subTest(variant=variant):
                record = self._execute_s01_tamper("valid")
                if variant == "missing":
                    record["acks"] = []
                else:
                    record["acks"][0]["body"]["status"] = "REJECTED"
                errors: list[str] = []
                _validate_result_ack_contract(record, "record[0]", errors)
                self.assertTrue(
                    any(
                        "ACK" in error
                        and ("count mismatch" in error or "first result ACK" in error)
                        for error in errors
                    )
                )

    def test_validator_rejects_mismatched_ack_request_id(self) -> None:
        record = self._execute_s01_tamper("valid")
        self.assertTrue(record["acks"])
        record["acks"][0]["request_id"] = "request-mismatch"
        errors: list[str] = []
        _validate_result_ack_contract(record, "record[0]", errors)
        self.assertTrue(any("ACK[0] identity mismatch for request_id" in error for error in errors))

    def test_crashed_tamper_with_rejected_row_is_not_canonical_rejection(self) -> None:
        record = self._execute_s01_tamper("unexpected-runtime-error", returncode=1)
        self.assertEqual(record["status"], "assigned_failure")
        self.assertFalse(record["replay"].get("godot_tamper_rejected", False))

    def test_exit_one_rejection_without_canonical_codes_is_not_evidence(self) -> None:
        record = self._execute_s01_tamper("weak-rejection")
        self.assertEqual(record["status"], "assigned_failure")
        self.assertFalse(record["replay"]["godot_tamper_rejected"])
        self.assertIn(
            "tamper_replay_evidence_missing", {item["code"] for item in record["failure"]}
        )

    def test_any_applied_tamper_row_fails_even_with_rejected_row(self) -> None:
        record = self._execute_s01_tamper("applied-row")
        self.assertEqual(record["status"], "assigned_failure")
        self.assertFalse(record["replay"]["godot_tamper_rejected"])
        self.assertIn("semantic_tamper_accepted", {item["code"] for item in record["failure"]})

    def test_changed_canonical_state_fails_negative_gate(self) -> None:
        record = self._execute_s01_tamper("changed-state")
        self.assertEqual(record["status"], "assigned_failure")
        self.assertFalse(record["replay"]["godot_tamper_rejected"])
        self.assertIn(
            "tamper_replay_evidence_missing", {item["code"] for item in record["failure"]}
        )

    def test_python_and_godot_replay_denominators_remain_independent(self) -> None:
        report = replay_report(
            [
                {
                    "assignment_id": "P",
                    "status": "assigned_failure",
                    "replay": {"python": {"valid": True, "rows": 2}},
                    "engine": {
                        "replay": {"available": True, "status": "completed"},
                        "replay_comparison": {"passed": True},
                    },
                },
                {
                    "assignment_id": "G",
                    "status": "assigned_failure",
                    "replay": {"python": {"valid": False}},
                    "results": [{"x": 1}],
                    "engine": {
                        "replay": {"available": True, "status": "failed"},
                        "replay_comparison": {"passed": False},
                    },
                },
                {
                    "assignment_id": "U",
                    "status": "assigned_failure",
                    "replay": {},
                    "engine": {"replay": {"available": False}},
                },
            ],
            "NPC-ENG1",
        )
        self.assertEqual(
            report["denominators"],
            {
                "python_eligible": 1,
                "python_failed": 1,
                "python_unavailable": 1,
                "godot_eligible": 1,
                "godot_failed": 1,
                "godot_unavailable": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
