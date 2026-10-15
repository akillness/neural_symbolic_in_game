from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from scripts.run_playable_evaluation import stage_project
from src.nesy_game.npc_goal import (
    GoalController,
    IntentInterpreter,
    canonical_config_hash,
    content_hash,
    default_envelope,
    sha256_json,
)

ROOT = Path(__file__).parents[1]
GODOT = ROOT / "game-track" / "godot"
V2 = ROOT / "data/fixtures/npc-goal-recovery/validated-v2"
V5 = ROOT / "data/fixtures/npc-goal-recovery/validated-v5"
POLICY = "6cffab0197ac17ffc94b36b525cc6fd75d577e8b50d5dbabf5991b858b72283d"
PROJECT_HASH = hashlib.sha256((GODOT / "project.godot").read_bytes()).hexdigest()
CONFIG_HASH = canonical_config_hash()
LIVE_POLICY = sha256_json(
    json.loads((GODOT / "data/sealed_lighthouse.json").read_text())["disclosure_policy"]
)
OBS_KEYS = {
    "lens_reachable",
    "lens_carried",
    "signal_restored",
    "tide_lead_authorized",
    "goal_reached",
    "in_dialogue",
}


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def find_godot() -> str:
    path = shutil.which("godot4") or shutil.which("godot")
    if path is None:
        raise unittest.SkipTest("Godot 4.x is not installed")
    probe = subprocess.run(
        [path, "--version"], capture_output=True, text=True, check=False, timeout=30
    )
    if probe.returncode != 0 or not probe.stdout.startswith("4."):
        raise unittest.SkipTest("Godot 4.x is not available")
    return path


def run_godot(
    godot: str, project: Path, mode: str, input_path: Path
) -> tuple[subprocess.CompletedProcess[str], dict | None]:
    command = [
        godot,
        "--headless",
        "--audio-driver",
        "Dummy",
        "--path",
        str(project),
        "--scene",
        "scenes/main_3d.tscn",
        "--",
        f"--npc-{mode}",
        str(input_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False, timeout=60)
    sidecar = input_path.with_name(
        input_path.name + (".bootstrap.json" if mode == "bootstrap" else ".result.json")
    )
    return completed, json.loads(sidecar.read_text()) if sidecar.is_file() else None


def context_from_snapshot(case: dict, snapshot: dict) -> dict:
    return {
        "session_id": f"test-{case['id']}",
        "episode_id": f"episode-{case['id']}",
        "session_epoch": 0,
        "request_id": f"request-{case['id']}",
        "goal_id": "harbor-signal-restored-authorized-tide-lead-v1",
        "goal_version": "1",
        "config_hash": CONFIG_HASH,
    }


def make_request(case: dict, snapshot: dict) -> dict:
    context = context_from_snapshot(case, snapshot)
    request = default_envelope(
        message_type="request",
        request_id=context["request_id"],
        session_id=context["session_id"],
        session_epoch=0,
        state_ref=snapshot["state_ref"],
        body={
            "event_kind": "utterance",
            "utterance": case["utterance"],
            "observation": snapshot["observation"],
        },
        arm="R",
        backend="rule",
        policy_hash=snapshot["policy_hash"],
    )
    request.update(
        episode_id=context["episode_id"],
        goal_id=context["goal_id"],
        goal_version=context["goal_version"],
    )
    request["content_sha256"] = content_hash(request)
    return request


def make_decision(case: dict, snapshot: dict) -> tuple[dict, dict]:
    request = make_request(case, snapshot)
    digest = hashlib.sha256(case["utterance"].encode()).hexdigest()
    reference = case.get("reference_intent") or {
        "label": "ASK_INFORMATION",
        "claims": [],
        "target": None,
    }
    controller = GoalController(
        interpreter=IntentInterpreter(arm="R", reference_intents={digest: reference})
    )
    return request, controller.handle_request(request)


def make_reference_decision(case: dict, snapshot: dict) -> tuple[dict, dict]:
    context = context_from_snapshot(case, snapshot)
    request = default_envelope(
        message_type="request",
        request_id=context["request_id"],
        session_id=context["session_id"],
        session_epoch=0,
        state_ref=snapshot["state_ref"],
        body={
            "event_kind": "utterance",
            "utterance": case["utterance"],
            "observation": snapshot["observation"],
        },
        arm="O",
        backend="reference",
        policy_hash=snapshot["policy_hash"],
    )
    request.update(
        episode_id=context["episode_id"],
        goal_id=context["goal_id"],
        goal_version=context["goal_version"],
    )
    request["content_sha256"] = content_hash(request)
    digest = hashlib.sha256(case["utterance"].encode()).hexdigest()
    reference = case.get("reference_intent") or {
        "label": "ASK_INFORMATION",
        "claims": [],
        "target": None,
    }
    controller = GoalController(
        interpreter=IntentInterpreter(arm="O", reference_intents={digest: reference})
    )
    return request, controller.handle_request(request)


class NpcEngineExperimentTests(unittest.TestCase):
    def test_v2_cases_bind_actual_bootstrap_receipts_and_preserve_source_boundary(self) -> None:
        packets = [("engineering.json", 16), ("screening.json", 12)]
        for filename, expected_count in packets:
            packet = json.loads((V2 / filename).read_text())
            self.assertEqual(packet["schema_version"], "npc-goal-recovery/validated-v2")
            self.assertEqual(len(packet["cases"]), expected_count)
            self.assertEqual(packet["policy_hash"], POLICY)
            self.assertNotEqual(packet["policy_hash"], PROJECT_HASH)
            self.assertEqual(
                packet["provenance"]["source_family"], "same_model_family_auxiliary100%"
            )
            self.assertEqual(packet["provenance"]["independent_source_fraction"], 0)
            self.assertTrue(packet["provenance"]["public_input_only"])
            self.assertFalse(packet["provenance"]["reference_is_semantic_gold"])
            correction = packet["correction_metadata"]
            self.assertEqual(correction["status"], "corrected_preflight_expectations")
            self.assertEqual(
                correction["basis"], "actual_public_flags_plus_unchanged_reference_intent"
            )
            self.assertFalse(correction["outcomes_collected"])
            self.assertFalse(correction["model_dependent_curation"])
            self.assertFalse(correction["receipt_regenerated"])
            self.assertTrue(
                correction["preserved_original_v2"].endswith("preflight-v2-expectations/")
            )
            self.assertEqual(
                {case["regime"] for case in packet["cases"]},
                {
                    "static",
                    "language_claim",
                    "world_change",
                    "stale",
                    "deadline_cancel",
                    "duplicate_no_route",
                },
            )
            ids = set()
            for case in packet["cases"]:
                with self.subTest(packet=filename, case=case["id"]):
                    self.assertNotIn(case["id"], ids)
                    ids.add(case["id"])
                    self.assertEqual(set(case["observation"]), OBS_KEYS)
                    receipt_path = V2 / case["bootstrap_receipt_ref"]
                    input_path = V2 / case["bootstrap_input_ref"]
                    self.assertTrue(receipt_path.is_file())
                    self.assertTrue(input_path.is_file())
                    self.assertEqual(
                        sha256_bytes(receipt_path.read_bytes()), case["bootstrap_receipt_sha256"]
                    )
                    self.assertEqual(
                        sha256_bytes(input_path.read_bytes()), case["bootstrap_input_sha256"]
                    )
                    receipt = json.loads(receipt_path.read_text())
                    bootstrap_input = json.loads(input_path.read_text())
                    self.assertEqual(bootstrap_input["assignment_id"], case["id"])
                    self.assertEqual(bootstrap_input["fixture_ref"], case["fixture_ref"])
                    self.assertEqual(bootstrap_input["setup_operations"], case["setup_operations"])
                    self.assertEqual(
                        bootstrap_input["seed_world_events"], case["seed_world_events"]
                    )
                    self.assertEqual(bootstrap_input["in_dialogue"], case["in_dialogue"])
                    self.assertIsNone(bootstrap_input["decision"])
                    self.assertEqual(
                        set(bootstrap_input["request_context"]),
                        {
                            "session_id",
                            "episode_id",
                            "session_epoch",
                            "request_id",
                            "goal_id",
                            "goal_version",
                        },
                    )
                    self.assertTrue(receipt["passed"])
                    self.assertTrue(receipt["input_bytes_preserved"])
                    self.assertEqual(receipt["observation"], case["observation"])
                    self.assertEqual(receipt["state_ref"], case["state_ref"])
                    self.assertEqual(receipt["policy_hash"], packet["policy_hash"])
                    self.assertEqual(
                        case["raw_utterance_sha256"],
                        hashlib.sha256(case["utterance"].encode()).hexdigest(),
                    )
                    self.assertEqual(
                        case["fixture_ref_sha256"],
                        hashlib.sha256(case["fixture_ref"].encode()).hexdigest(),
                    )
                    self.assertNotIn(
                        "1111111111111111111111111111111111111111111111111111111111111111",
                        case["state_ref"]["sha256"],
                    )

    def test_preflight_archive_preserves_pre_correction_v2_bytes(self) -> None:
        archive = ROOT / "research/academic-pipeline/npc-goal-recovery/preflight-v2-expectations"
        for filename in ("engineering.json", "screening.json"):
            current = V2 / filename
            preserved = archive / filename
            self.assertTrue(preserved.is_file())
            self.assertNotEqual(preserved.read_bytes(), current.read_bytes())
        current_bootstrap = {path.name: path for path in (V2 / "bootstrap").glob("*.json")}
        preserved_bootstrap = {path.name: path for path in (archive / "bootstrap").glob("*.json")}
        self.assertEqual(set(preserved_bootstrap), set(current_bootstrap))
        for name, current in current_bootstrap.items():
            self.assertEqual(preserved_bootstrap[name].read_bytes(), current.read_bytes())

    def test_bootstrap_snapshots_drive_grounded_planner_expectations(self) -> None:
        for filename in ("engineering.json", "screening.json"):
            packet = json.loads((V2 / filename).read_text())
            for case in packet["cases"]:
                with self.subTest(packet=filename, case=case["id"]):
                    receipt = json.loads((V2 / case["bootstrap_receipt_ref"]).read_text())
                    snapshot = {
                        "observation": receipt["observation"],
                        "state_ref": receipt["state_ref"],
                        "policy_hash": receipt["policy_hash"],
                    }
                    _request, decision = make_reference_decision(case, snapshot)
                    body = decision["body"]
                    operation = body["steps"][0]["operation"] if body["steps"] else None
                    self.assertEqual(body["status"], case["expected_status"])
                    self.assertEqual(operation, case["expected_operation"])
                    if case["expected_operation"] == "reveal_hint":
                        self.assertTrue(snapshot["observation"]["signal_restored"])
                        self.assertTrue(snapshot["observation"]["tide_lead_authorized"])
                        self.assertTrue(snapshot["observation"]["in_dialogue"])
                    if case["expected_status"] == "NO_ROUTE":
                        self.assertFalse(body["steps"])

    def test_bootstrap_then_assigned_r_decision_applies_player_transition_and_replays(self) -> None:
        godot = find_godot()
        case = json.loads((V5 / "engineering.json").read_text())["cases"][0]
        snapshot = {
            "observation": case["observation"],
            "state_ref": case["state_ref"],
            "policy_hash": case["policy_hash"],
        }
        request, decision = make_decision(case, snapshot)
        self.assertEqual(decision["provenance"]["arm"], "R")
        self.assertEqual(decision["body"]["steps"][0]["operation"], "acquire_object")
        experiment = {
            "schema_version": "npc-engineering/input-1",
            "assignment_id": "TEST-ASSIGNED-R",
            "fixture_ref": case["fixture_ref"],
            "source_hashes": deepcopy(case["source_hashes"]),
            "setup_operations": [],
            "seed_world_events": [],
            "in_dialogue": False,
            "request_context": context_from_snapshot(case, snapshot),
            "request": request,
            "decision": decision,
            "initial_public_snapshot": snapshot,
            "mutations": [{"code": "fixture-playeraction", "operation": "acquire_object"}],
            "expected": {"goal_reached": False},
        }
        with tempfile.TemporaryDirectory(prefix="npc-v2-engine-test-") as directory:
            root = Path(directory)
            project = root / "project"
            stage_project(GODOT, project)
            imported = subprocess.run(
                [
                    godot,
                    "--headless",
                    "--audio-driver",
                    "Dummy",
                    "--path",
                    str(project),
                    "--import",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            input_path = root / "assigned-r.json"
            input_path.write_bytes(canonical(experiment) + b"\n")
            before = sha256_bytes(input_path.read_bytes())
            first_process, first = run_godot(godot, project, "experiment", input_path)
            self.assertEqual(first_process.returncode, 0, first_process.stderr)
            self.assertIsNotNone(first)
            assert first is not None
            self.assertTrue(first["passed"])
            self.assertTrue(first["input_bytes_preserved"])
            self.assertEqual(first["rows"][0]["status"], "APPLIED")
            self.assertTrue(first["rows"][0]["result"]["accepted"])
            self.assertTrue(first["rows"][0]["observation_after"]["lens_carried"])
            self.assertGreater(
                first["final_state_ref"]["revision"], first["initial_state_ref"]["revision"]
            )
            self.assertEqual(before, sha256_bytes(input_path.read_bytes()))

            replay_process, replay = run_godot(godot, project, "experiment", input_path)
            self.assertEqual(replay_process.returncode, 0, replay_process.stderr)
            self.assertEqual(replay["rows"], first["rows"])
            self.assertEqual(replay["final_state_ref"], first["final_state_ref"])

    def test_native_goal_reached_terminal_preserves_state_hash_without_mutation(self) -> None:
        godot = find_godot()
        packet = json.loads((V2 / "engineering.json").read_text())
        case = next(item for item in packet["cases"] if item["id"] == "ENG-X01")
        receipt = json.loads((V2 / case["bootstrap_receipt_ref"]).read_text())
        snapshot = {
            "observation": receipt["observation"],
            "state_ref": receipt["state_ref"],
            "policy_hash": LIVE_POLICY,
        }
        request, decision = make_reference_decision(case, snapshot)
        self.assertEqual(decision["body"]["status"], "GOAL_REACHED")
        self.assertEqual(decision["body"]["steps"], [])
        experiment = {
            "schema_version": "npc-engineering/input-1",
            "assignment_id": "TEST-GOAL-REACHED",
            "fixture_ref": case["fixture_ref"],
            "source_hashes": {
                "source_project_config_sha256": PROJECT_HASH,
                "npc_protocol_config_sha256": CONFIG_HASH,
                "policy_hash": LIVE_POLICY,
            },
            "setup_operations": case["setup_operations"],
            "seed_world_events": case["seed_world_events"],
            "in_dialogue": case["in_dialogue"],
            "request_context": context_from_snapshot(case, snapshot),
            "request": request,
            "decision": decision,
            "initial_public_snapshot": snapshot,
            "mutations": [],
            "expected": {"goal_reached": True},
        }
        with tempfile.TemporaryDirectory(prefix="npc-v2-goal-reached-test-") as directory:
            root = Path(directory)
            project = root / "project"
            stage_project(GODOT, project)
            imported = subprocess.run(
                [
                    godot,
                    "--headless",
                    "--audio-driver",
                    "Dummy",
                    "--path",
                    str(project),
                    "--import",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            input_path = root / "goal-reached.json"
            input_path.write_bytes(canonical(experiment) + b"\n")
            before = sha256_bytes(input_path.read_bytes())
            process, report = run_godot(godot, project, "experiment", input_path)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIsNotNone(report)
            assert report is not None
            self.assertTrue(report["passed"])
            self.assertEqual(report["status"], "GOAL_REACHED")
            self.assertTrue(report["events"][0]["result"]["accepted"])
            self.assertEqual(report["initial_state_ref"], snapshot["state_ref"])
            self.assertEqual(report["final_state_ref"], report["initial_state_ref"])
            self.assertEqual(before, sha256_bytes(input_path.read_bytes()))

    def test_native_goal_reached_forgery_is_rejected_without_state_change(self) -> None:
        godot = find_godot()
        packet = json.loads((V2 / "engineering.json").read_text())
        case = next(item for item in packet["cases"] if item["id"] == "ENG-S01")
        receipt = json.loads((V2 / case["bootstrap_receipt_ref"]).read_text())
        snapshot = {
            "observation": receipt["observation"],
            "state_ref": receipt["state_ref"],
            "policy_hash": LIVE_POLICY,
        }
        request, decision = make_reference_decision(case, snapshot)
        forged = deepcopy(decision)
        forged["body"]["status"] = "GOAL_REACHED"
        forged["body"]["steps"] = []
        forged["content_sha256"] = content_hash(forged)
        experiment = {
            "schema_version": "npc-engineering/input-1",
            "assignment_id": "TEST-GOAL-FORGERY",
            "fixture_ref": case["fixture_ref"],
            "source_hashes": {
                "source_project_config_sha256": PROJECT_HASH,
                "npc_protocol_config_sha256": CONFIG_HASH,
                "policy_hash": LIVE_POLICY,
            },
            "setup_operations": case["setup_operations"],
            "seed_world_events": case["seed_world_events"],
            "in_dialogue": case["in_dialogue"],
            "request_context": context_from_snapshot(case, snapshot),
            "request": request,
            "decision": forged,
            "initial_public_snapshot": snapshot,
            "mutations": [],
            "expected": {"goal_reached": False},
        }
        with tempfile.TemporaryDirectory(prefix="npc-v2-goal-forgery-test-") as directory:
            root = Path(directory)
            project = root / "project"
            stage_project(GODOT, project)
            imported = subprocess.run(
                [
                    godot,
                    "--headless",
                    "--audio-driver",
                    "Dummy",
                    "--path",
                    str(project),
                    "--import",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            input_path = root / "goal-forgery.json"
            input_path.write_bytes(canonical(experiment) + b"\n")
            before = sha256_bytes(input_path.read_bytes())
            process, report = run_godot(godot, project, "experiment", input_path)
            self.assertIsNotNone(report)
            assert report is not None
            self.assertEqual(
                process.returncode,
                0,
                json.dumps(
                    {
                        "stdout": process.stdout,
                        "stderr": process.stderr,
                        "status": report.get("status"),
                        "terminal_status": report.get("terminal_status"),
                        "errors": report.get("errors"),
                        "events": report.get("events"),
                        "expected_negative_gates": report.get("expected_negative_gates"),
                    },
                    sort_keys=True,
                ),
            )
            self.assertEqual(report["status"], "GOAL_NOT_REACHED", report)
            self.assertFalse(report["events"][0]["result"]["accepted"])
            self.assertEqual(report["events"][0]["result"]["codes"], ["GOAL_NOT_REACHED"])
            self.assertEqual(report["initial_state_ref"], snapshot["state_ref"])
            self.assertEqual(report["final_state_ref"], report["initial_state_ref"])
            self.assertEqual(before, sha256_bytes(input_path.read_bytes()))

    def test_native_stale_and_cancelled_directives_do_not_reach_writer(self) -> None:
        godot = find_godot()
        packet = json.loads((V2 / "engineering.json").read_text())
        cases = (
            ("stale_revision", "ENG-T01", "STALE", ("STATE_HASH_MISMATCH",)),
            ("cancelled", "ENG-S01", "CANCELLED", ("EPOCH_MISMATCH", "GENERATION_MISMATCH")),
        )
        for control, case_id, expected_status, expected_code in cases:
            case = next(item for item in packet["cases"] if item["id"] == case_id)
            receipt = json.loads((V2 / case["bootstrap_receipt_ref"]).read_text())
            snapshot = {
                "observation": receipt["observation"],
                "state_ref": receipt["state_ref"],
                "policy_hash": LIVE_POLICY,
            }
            request, decision = make_reference_decision(case, snapshot)
            experiment = {
                "schema_version": "npc-engineering/input-1",
                "assignment_id": f"TEST-{control.upper()}",
                "fixture_ref": case["fixture_ref"],
                "source_hashes": {
                    "source_project_config_sha256": PROJECT_HASH,
                    "npc_protocol_config_sha256": CONFIG_HASH,
                    "policy_hash": LIVE_POLICY,
                },
                "setup_operations": case["setup_operations"],
                "seed_world_events": case["seed_world_events"],
                "in_dialogue": case["in_dialogue"],
                "request_context": context_from_snapshot(case, snapshot),
                "request": request,
                "decision": decision,
                "initial_public_snapshot": snapshot,
                "mutations": [control],
                "expected": {"goal_reached": False},
            }
            with (
                self.subTest(control=control),
                tempfile.TemporaryDirectory(prefix=f"npc-v2-{control}-test-") as directory,
            ):
                root = Path(directory)
                project = root / "project"
                stage_project(GODOT, project)
                imported = subprocess.run(
                    [
                        godot,
                        "--headless",
                        "--audio-driver",
                        "Dummy",
                        "--path",
                        str(project),
                        "--import",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=90,
                )
                self.assertEqual(imported.returncode, 0, imported.stderr)
                input_path = root / f"{control}.json"
                input_path.write_bytes(canonical(experiment) + b"\n")
                before = sha256_bytes(input_path.read_bytes())
                process, report = run_godot(godot, project, "experiment", input_path)
                self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
                self.assertIsNotNone(report)
                assert report is not None
                self.assertTrue(report["passed"], report)
                self.assertEqual(report["status"], expected_status)
                self.assertEqual(len(report["rows"]), 1)
                row = report["rows"][0]
                self.assertEqual(row["status"], expected_status)
                self.assertFalse(row["result"]["accepted"])
                self.assertTrue(any(code in row["codes"] for code in expected_code))
                self.assertEqual(row["state_ref_before"], row["state_ref_after"])
                self.assertEqual(report["initial_state_ref"], report["final_state_ref"])
                self.assertEqual(before, sha256_bytes(input_path.read_bytes()))

    def test_invalid_args_policy_state_decision_and_json_fail_closed_with_diagnostics(self) -> None:
        godot = find_godot()
        case = json.loads((V5 / "engineering.json").read_text())["cases"][0]
        snapshot = {
            "observation": case["observation"],
            "state_ref": case["state_ref"],
            "policy_hash": case["policy_hash"],
        }
        request, decision = make_decision(case, snapshot)
        with tempfile.TemporaryDirectory(prefix="npc-v2-negative-test-") as directory:
            root = Path(directory)
            project = root / "project"
            stage_project(GODOT, project)
            subprocess.run(
                [
                    godot,
                    "--headless",
                    "--audio-driver",
                    "Dummy",
                    "--path",
                    str(project),
                    "--import",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
            bad_args = {
                "schema_version": "npc-engineering/input-1",
                "assignment_id": "BAD-ARGS",
                "fixture_ref": case["fixture_ref"],
                "setup_operations": [{"operation": "acquire_object", "arguments": {}}],
                "seed_world_events": [],
                "in_dialogue": False,
                "request_context": context_from_snapshot(case, snapshot),
                "decision": None,
                "mutations": [],
            }
            bad_path = root / "bad-args.json"
            bad_path.write_bytes(canonical(bad_args) + b"\n")
            process, report = run_godot(godot, project, "bootstrap", bad_path)
            self.assertNotEqual(process.returncode, 0)
            self.assertEqual(report["terminal_status"], "BOOTSTRAP_REJECTED")
            self.assertIn("SETUP_OPERATION_ARGUMENTS_INVALID", report["errors"])
            self.assertTrue(report["input_bytes_preserved"])

            base = {
                "schema_version": "npc-engineering/input-1",
                "assignment_id": "BAD-CONTEXT",
                "fixture_ref": case["fixture_ref"],
                "source_hashes": deepcopy(case["source_hashes"]),
                "setup_operations": [],
                "seed_world_events": [],
                "in_dialogue": False,
                "request_context": context_from_snapshot(case, snapshot),
                "request": request,
                "decision": decision,
                "initial_public_snapshot": snapshot,
                "mutations": [{"code": "fixture-playeraction", "operation": "acquire_object"}],
                "expected": {"goal_reached": False},
            }
            bad_policy = deepcopy(base)
            bad_policy["source_hashes"]["policy_hash"] = "0" * 64
            policy_path = root / "bad-policy.json"
            policy_path.write_bytes(canonical(bad_policy) + b"\n")
            policy_process, policy_report = run_godot(godot, project, "experiment", policy_path)
            self.assertNotEqual(policy_process.returncode, 0)
            self.assertIn("POLICY_HASH_MISMATCH", policy_report["errors"])

            stale = deepcopy(base)
            stale["initial_public_snapshot"] = {
                "observation": snapshot["observation"],
                "state_ref": {"revision": 99, "sha256": "9" * 64},
            }
            stale_path = root / "bad-state.json"
            stale_path.write_bytes(canonical(stale) + b"\n")
            stale_process, stale_report = run_godot(godot, project, "experiment", stale_path)
            self.assertNotEqual(stale_process.returncode, 0)
            self.assertIn("INITIAL_STATE_REF_MISMATCH", stale_report["errors"])

            malformed = deepcopy(base)
            malformed["decision"] = deepcopy(decision)
            malformed["decision"]["content_sha256"] = "0" * 64
            malformed_path = root / "malformed-decision.json"
            malformed_path.write_bytes(canonical(malformed) + b"\n")
            malformed_process, malformed_report = run_godot(
                godot, project, "experiment", malformed_path
            )
            self.assertNotEqual(malformed_process.returncode, 0)
            self.assertEqual(malformed_report["status"], "REJECTED")
            self.assertIn("ACTION_NOT_APPLIED", malformed_report["errors"])
            self.assertEqual(
                malformed_report["initial_state_ref"], malformed_report["final_state_ref"]
            )

            invalid_path = root / "invalid-json.json"
            invalid_path.write_bytes(b"{this is not json\n")
            invalid_process, invalid_report = run_godot(godot, project, "experiment", invalid_path)
            self.assertNotEqual(invalid_process.returncode, 0)
            self.assertIn("INPUT_MISSING", invalid_report["errors"])
            self.assertEqual(invalid_report["initial_state_ref"], invalid_report["final_state_ref"])
            self.assertIn("NPC-EXPERIMENT", invalid_process.stdout + invalid_process.stderr)

    def test_native_cancel_and_stale_callback_gates_preserve_writer_boundary(self) -> None:
        godot = find_godot()
        with tempfile.TemporaryDirectory(prefix="npc-native-lifecycle-test-") as directory:
            root = Path(directory)
            project = root / "project"
            stage_project(GODOT, project)
            imported = subprocess.run(
                [
                    godot,
                    "--headless",
                    "--audio-driver",
                    "Dummy",
                    "--path",
                    str(project),
                    "--import",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            harness = project / "tests" / "npc_lifecycle_harness.gd"
            process = subprocess.run(
                [
                    godot,
                    "--headless",
                    "--audio-driver",
                    "Dummy",
                    "--path",
                    str(project),
                    "--script",
                    "res://tests/npc_lifecycle_harness.gd",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=120,
            )
            self.assertTrue(harness.is_file())
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        result = next(
            json.loads(line)
            for line in reversed(process.stdout.splitlines())
            if line.startswith("{")
        )
        self.assertTrue(result["mutation_accepted"])
        self.assertTrue(result["stale_blocked"])
        self.assertTrue(result["ordinary_after_cancel_applied"])
        self.assertEqual(result["stale_state_ref"], result["ordinary_state_ref"])

    def test_changed_decision_hash_changes_engine_effect_not_only_input_bytes(self) -> None:
        godot = find_godot()
        case = json.loads((V5 / "engineering.json").read_text())["cases"][0]
        snapshot = {
            "observation": case["observation"],
            "state_ref": case["state_ref"],
            "policy_hash": case["policy_hash"],
        }
        request, decision = make_decision(case, snapshot)
        no_route = deepcopy(decision)
        no_route["body"]["steps"] = []
        no_route["body"]["status"] = "NO_ROUTE"
        no_route["content_sha256"] = content_hash(no_route)

        def payload(value: dict) -> dict:
            return {
                "schema_version": "npc-engineering/input-1",
                "assignment_id": "DECISION-DIFF",
                "fixture_ref": case["fixture_ref"],
                "source_hashes": deepcopy(case["source_hashes"]),
                "setup_operations": [],
                "seed_world_events": [],
                "in_dialogue": False,
                "request_context": context_from_snapshot(case, snapshot),
                "request": request,
                "decision": value,
                "initial_public_snapshot": snapshot,
                "mutations": [{"code": "fixture-playeraction", "operation": "acquire_object"}],
                "expected": {"goal_reached": False},
            }

        with tempfile.TemporaryDirectory(prefix="npc-v5-diff-test-") as directory:
            root = Path(directory)
            first_project = root / "first-project"
            second_project = root / "second-project"
            first_path = root / "first.json"
            second_path = root / "second.json"
            for project in (first_project, second_project):
                stage_project(GODOT, project)
                imported = subprocess.run(
                    [
                        godot,
                        "--headless",
                        "--audio-driver",
                        "Dummy",
                        "--path",
                        str(project),
                        "--import",
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=90,
                )
                self.assertEqual(imported.returncode, 0, imported.stderr)
            first_path.write_bytes(canonical(payload(decision)) + b"\n")
            second_path.write_bytes(canonical(payload(no_route)) + b"\n")
            first_process, first = run_godot(godot, first_project, "experiment", first_path)
            second_process, second = run_godot(godot, second_project, "experiment", second_path)
            self.assertEqual(first_process.returncode, 0, first_process.stderr)
            self.assertEqual(second_process.returncode, 0, second_process.stderr)
            self.assertIsNotNone(first)
            self.assertIsNotNone(second)
            assert first is not None and second is not None
            self.assertNotEqual(first["decision_sha256"], second["decision_sha256"])
            self.assertNotEqual(first["status"], second["status"])
            self.assertNotEqual(first["final_state_ref"], second["final_state_ref"])
            self.assertNotEqual(
                sha256_bytes(first_path.read_bytes()), sha256_bytes(second_path.read_bytes())
            )
            self.assertTrue(first["rows"][0]["result"]["accepted"])
            self.assertEqual(second["status"], "NO_ROUTE")
            self.assertTrue(second["events"][0]["result"]["accepted"])


if __name__ == "__main__":
    unittest.main()
