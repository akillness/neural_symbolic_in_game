from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from typing import Any

import run_npc_goal_experiment as npc_experiment
import run_playable_evaluation as playable_evaluation
import run_runtime_model_swap as runtime_cli

from nesy_game.runtime_model_swap import (
    EpisodeLimits,
    GodotEpisodeEngine,
    ModelSpec,
    run_episode,
    verify_episode_record,
)
from scripts.run_npc_goal_experiment import run_godot
from scripts.run_playable_evaluation import stage_project

ROOT = Path(__file__).resolve().parents[1]
GODOT_PROJECT = ROOT / "game-track" / "godot"
FIXTURE_REF = "data/fixtures/npc-goal-recovery/validated-v2/engineering.json#ENG-S01"
POLICY_HASH = "b" * 64
GODOT_BINARY = shutil.which("godot4") or shutil.which("godot") or "/opt/homebrew/bin/godot"

OBSERVATION = {
    "lens_reachable": True,
    "lens_carried": False,
    "signal_restored": False,
    "tide_lead_authorized": False,
    "goal_reached": False,
    "in_dialogue": False,
}


def _valid_typed_intent(request_id: str) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
    }


def _public_context(engine: GodotEpisodeEngine) -> dict[str, Any]:
    state = engine.state()
    semantic = {
        "state": state,
        "legal_actions": engine.legal_actions(),
        "preconditions": engine.preconditions(),
        "constraints": engine.constraints(),
        "objective": engine.objective(),
    }
    rendering = "rules:" + ";".join(
        f"{key}={json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"
        for key, value in semantic.items()
    )
    return {
        "state": state,
        "model_input": {**semantic, "representation": "general_rule", "rendering": rendering},
        "logical_request_id": "decision-0",
        "remaining_wall_seconds": 180.0,
    }


class FakeEngineTransport:
    """Only the Godot transport is faked; adapter/controller seams remain real."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[dict[str, Any]] = []
        self.next_revision = 0

    def __call__(
        self,
        *,
        binary: str,
        project: Path,
        mode: str,
        input_path: Path,
        log_dir: Path,
        timeout: float,
    ) -> dict[str, Any]:
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        self.calls.append({"binary": binary, "project": project, "mode": mode, "payload": payload})
        if mode == "bootstrap":
            state_ref = {"revision": self.next_revision, "sha256": f"{self.next_revision:064x}"}
            trace = {
                "passed": True,
                "observation": dict(OBSERVATION),
                "state_ref": state_ref,
                "policy_hash": POLICY_HASH,
                "source_hashes": {"policy_hash": POLICY_HASH},
                "actions": [],
            }
        else:
            initial = payload["initial_public_snapshot"]
            before_ref = dict(initial["state_ref"])
            before_observation = dict(initial["observation"])
            operation = payload.get("mutations", [{}])[0].get("operation")
            after_observation = dict(before_observation)
            if operation == "acquire_object":
                after_observation["lens_carried"] = True
            elif operation == "install_lens":
                after_observation["signal_restored"] = True
            after_revision = int(before_ref["revision"]) + 1
            after_ref = {"revision": after_revision, "sha256": f"{after_revision:064x}"}
            self.next_revision = after_revision
            action = {
                "action_id": f"fake-action-{after_revision}",
                "operation": operation,
                "status": "APPLIED",
                "engine_revision": after_revision,
                "state_ref_before": before_ref,
                "state_ref_after": after_ref,
                "observation_before": before_observation,
                "observation_after": after_observation,
                "feedback": "applied",
            }
            trace = {
                "passed": True,
                "observations": [after_observation],
                "final_state_ref": after_ref,
                "actions": [action],
            }
        return {
            "status": "completed",
            "trace": trace,
            "latency_ms": 3.5,
            "input_sha256_before": "a" * 64,
            "input_sha256_after": "a" * 64,
            "sidecar_path": str(input_path)
            + (".bootstrap.json" if mode == "bootstrap" else ".result.json"),
        }


class AdvancingClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class GoalReachedTransport(FakeEngineTransport):
    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        payload = json.loads(Path(kwargs["input_path"]).read_text(encoding="utf-8"))
        result = super().__call__(**kwargs)
        if (
            kwargs["mode"] == "experiment"
            and payload.get("mutations", [{}])[0].get("operation") == "install_lens"
        ):
            trace = result["trace"]
            observation = dict(trace["observations"][-1])
            observation["signal_restored"] = True
            observation["goal_reached"] = True
            trace["observations"] = [observation]
            trace["actions"][0]["observation_after"] = observation
            trace["goal_reached"] = True
        return result


class UnsafeGoalReachedTransport(GoalReachedTransport):
    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        payload = json.loads(Path(kwargs["input_path"]).read_text(encoding="utf-8"))
        result = super().__call__(**kwargs)
        if (
            kwargs["mode"] == "experiment"
            and payload.get("mutations", [{}])[0].get("operation") == "install_lens"
        ):
            result["trace"]["passed"] = False
            result["trace"]["errors"] = ["COMMITTED_INVARIANT_VIOLATION"]
            result["status"] = "failed"
        return result


class ReplayWitnessTransport(GoalReachedTransport):
    def __init__(self, root: Path, *, replay_goal: bool, top_level_witness: bool = False) -> None:
        super().__init__(root)
        self.replay_goal = replay_goal
        self.top_level_witness = top_level_witness

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        result = super().__call__(**kwargs)
        if kwargs["mode"] != "experiment":
            return result
        trace = result["trace"]
        is_replay = Path(kwargs["input_path"]).name.startswith("reexecution-")
        if not is_replay:
            if self.top_level_witness:
                trace["goal_reached"] = True
            else:
                trace.pop("goal_reached", None)
            return result
        observation = dict(trace["observations"][-1])
        observation["goal_reached"] = self.replay_goal
        trace["observations"] = [observation]
        trace["actions"][0]["observation_after"] = observation
        if self.top_level_witness:
            trace["goal_reached"] = True
        else:
            trace.pop("goal_reached", None)
        return result


class GodotEpisodeEngineSeamTests(unittest.TestCase):
    def test_adapter_uses_real_P_interpreter_and_traces_malformed_typed_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)
            prompt_calls: list[dict[str, Any]] = []

            def malformed_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                prompt_calls.append(kwargs)
                return 0, {
                    "request_id": kwargs["request_id"],
                    "typed_intent": {
                        "label": "NOT_A_CANONICAL_LABEL",
                        "claims": [],
                        "target": None,
                    },
                }

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=malformed_prompt,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="SEAM-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(30.0, 5.0, 4, 0),
                seed=20261024,
                clock=lambda: 0.0,
                config={"assignment_id": "SEAM-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertFalse(record["success"])
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertEqual(record["evidence"]["calls"][0]["kind"], "proposal")
        self.assertTrue(record["evidence"]["calls"][0]["failed"])
        self.assertEqual(
            record["evidence"]["raw_model_outputs"][0]["typed_intent"]["label"],
            "NOT_A_CANONICAL_LABEL",
        )
        self.assertEqual(len(prompt_calls), 1)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["binary"], "/injected/godot")
        self.assertEqual(record["decisions"][0]["commit"], None)
        self.assertEqual([item["mode"] for item in engine.engine_evidence], ["bootstrap"])
        self.assertEqual(
            [item["mode"] for item in record["evidence"]["engine_runs"]], ["bootstrap"]
        )
        self.assertFalse(
            any(
                item["mode"] in {"experiment", "commit"}
                for item in record["evidence"]["engine_runs"]
            )
        )
        self.assertEqual(record["evidence"]["calls"][0]["host_invocations"], 1)
        self.assertEqual(
            record["evidence"]["raw_model_outputs"][0]["typed_intent"]["label"],
            "NOT_A_CANONICAL_LABEL",
        )
        self.assertEqual(record["evidence"]["provider_identity"], None)

    def test_adapter_preserves_engine_receipt_fields(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)

            def scripted_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                return 0, _valid_typed_intent(kwargs["request_id"])

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=scripted_prompt,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="SEAM-002",
            )
            limits = EpisodeLimits(180.0, 60.0, 12, 2)
            engine.configure_runtime(
                limits=limits,
                clock=lambda: 0.0,
                started=0.0,
                model_id="requested-offline-model",
                prompt="Restore the signal.",
            )
            context = _public_context(engine)
            proposed = engine.propose(context)
            validation = engine.validate(proposed)
            self.assertEqual(proposed, {"action": "acquire_object"})
            self.assertTrue(validation["valid"])
            engine.commit(proposed)

        evidence = engine.engine_evidence
        self.assertEqual([item["mode"] for item in evidence], ["bootstrap", "experiment"])
        experiment = next(item for item in evidence if item["mode"] == "experiment")
        self.assertEqual(experiment["latency_ms"], 3.5)
        self.assertEqual(experiment["input_sha256_before"], "a" * 64)
        self.assertEqual(experiment["input_sha256_after"], "a" * 64)
        self.assertTrue(experiment["sidecar_path"].endswith(".result.json"))
        self.assertEqual(len(transport.calls), 2)

    def test_controller_decision_blocks_tampered_raw_operation_before_transport(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)
            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **kwargs: (0, _valid_typed_intent(kwargs["request_id"])),
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="SEAM-TAMPER-001",
            )
            engine.configure_runtime(
                limits=EpisodeLimits(180.0, 60.0, 12, 2),
                clock=lambda: 0.0,
                started=0.0,
                model_id="requested-offline-model",
                prompt="Restore the signal.",
            )
            proposed = engine.propose(_public_context(engine))
            self.assertEqual(proposed, {"action": "acquire_object"})
            invalid = engine.validate({"action": "install_lens"})
            self.assertFalse(invalid["valid"])
            self.assertEqual(invalid["code"], "CONTROLLER_DECISION_INVALID")
            with self.assertRaisesRegex(ValueError, "proposal_controller_step_mismatch"):
                engine.commit({"action": "install_lens"})

        self.assertEqual([call["mode"] for call in transport.calls], ["bootstrap"])

    def test_semantic_rendering_reaches_prompt_without_rewriting_utterance(self) -> None:
        seen: dict[str, Any] = {}

        def scripted_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
            seen.update(kwargs)
            return 0, _valid_typed_intent(kwargs["request_id"])

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=scripted_prompt,
                engine_runner=FakeEngineTransport(root),
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="SEAM-PROMPT-001",
            )
            utterance = "Please restore the lighthouse signal, exactly as spoken."
            engine.configure_runtime(
                limits=EpisodeLimits(180.0, 60.0, 12, 2),
                clock=lambda: 0.0,
                started=0.0,
                model_id="requested-offline-model",
                prompt=utterance,
            )
            context = _public_context(engine)
            self.assertEqual(engine.propose(context), {"action": "acquire_object"})

        self.assertEqual(seen["user_prompt"], utterance)
        self.assertEqual(seen["model"], "requested-offline-model")
        self.assertIn("PUBLIC_CONTEXT=" + context["model_input"]["rendering"], seen["instruction"])
        self.assertIn("rules:", seen["instruction"])

    def test_controller_request_budget_uses_runtime_limits(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)
            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **kwargs: (0, _valid_typed_intent(kwargs["request_id"])),
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="SEAM-BUDGET-001",
            )
            engine.configure_runtime(
                limits=EpisodeLimits(180.0, 60.0, 12, 2),
                clock=lambda: 0.0,
                started=0.0,
                model_id="requested-offline-model",
                prompt="Restore the signal.",
            )
            proposed = engine.propose(_public_context(engine))
            self.assertTrue(engine.validate(proposed)["valid"])
            engine.commit(proposed)

        experiment = next(call for call in transport.calls if call["mode"] == "experiment")
        budget = experiment["payload"]["request"]["budget"]
        self.assertEqual(budget["max_intent_calls"], 12)
        self.assertEqual(budget["intent_deadline_ms"], 60_000)
        self.assertEqual(budget["episode_deadline_ms"], 180_000)

    def test_engine_unavailable_is_an_assigned_failure_record(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport_calls: list[dict[str, Any]] = []

            def unavailable_runner(**kwargs: Any) -> dict[str, Any]:
                transport_calls.append(kwargs)
                return {
                    "status": "unavailable",
                    "error": "godot_binary_unavailable",
                    "mode": kwargs["mode"],
                }

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **_: (0, _valid_typed_intent("request")),
                engine_runner=unavailable_runner,
                godot_binary="/missing/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="GODOT-UNAVAILABLE-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(30.0, 5.0, 4, 0),
                seed=20261024,
                clock=lambda: 0.0,
                config={"assignment_id": "GODOT-UNAVAILABLE-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "engine_unavailable")
        self.assertEqual(record["config"]["assignment_id"], "GODOT-UNAVAILABLE-001")
        self.assertTrue(record["accounting"]["denominator_eligible"])
        self.assertEqual(len(transport_calls), 1)
        self.assertEqual(record["safety"]["status"], "NOT_PASS")

    def test_completed_unsafe_goal_retains_witness_and_fails_safety_without_more_dispatch(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = UnsafeGoalReachedTransport(root)
            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **kwargs: (0, _valid_typed_intent(kwargs["request_id"])),
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="UNSAFE-GOAL-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 0),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "UNSAFE-GOAL-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertTrue(record["success"])
        self.assertTrue(record["goal_reached"])
        self.assertTrue(record["primary_success"])
        self.assertTrue(record["final_state"]["observation"]["goal_reached"])
        self.assertEqual(record["safety"]["status"], "FAIL")
        self.assertIn("COMMITTED_INVARIANT_VIOLATION", record["safety"]["errors"])
        self.assertNotEqual(record["engineering_status"], "PASS")
        self.assertFalse(record["accepted_for_engineering_verification"])
        self.assertEqual(record["accounting"]["host_calls"], 2)
        experiment_runs = [
            run for run in record["evidence"]["engine_runs"] if run.get("mode") == "experiment"
        ]
        self.assertEqual(
            [run["purpose"] for run in experiment_runs],
            ["episode", "episode", "reexecution", "reexecution"],
        )
        self.assertEqual(
            [run["status"] for run in experiment_runs],
            ["completed", "failed", "completed", "failed"],
        )
        self.assertEqual(record["evidence"]["engine_reexecution"]["model_calls"], 0)
        self.assertEqual(len(record["decisions"]), 2)

    def test_unavailable_engine_is_not_pass_safety_evidence(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)

            def unavailable_runner(**kwargs: Any) -> dict[str, Any]:
                return {
                    "status": "unavailable",
                    "error": "godot_binary_unavailable",
                    "mode": kwargs["mode"],
                }

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **_: (0, _valid_typed_intent("request")),
                engine_runner=unavailable_runner,
                godot_binary="/missing/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="UNAVAILABLE-SAFETY-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(30.0, 5.0, 4, 0),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "UNAVAILABLE-SAFETY-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "engine_unavailable")
        self.assertEqual(record["safety"]["status"], "NOT_PASS")
        self.assertFalse(record["accepted_for_engineering_verification"])

    def test_non_json_prompt_callback_output_is_diagnostic_and_does_not_poison_record(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)
            output = root / "episode.json"

            def object_prompt(**kwargs: Any) -> tuple[int, object]:
                return 0, object()

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=object_prompt,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="NONJSON-CALLBACK-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(30.0, 5.0, 4, 0),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "NONJSON-CALLBACK-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
                output_path=output,
            )
            written_receipt = json.loads(output.read_text(encoding="utf-8"))

        self.assertFalse(record["success"])
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["decisions"][0]["commit"], None)
        encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
        self.assertIn("object", encoded.lower())
        self.assertIn("serialization", encoded.lower())
        self.assertEqual(written_receipt["record_hash"], record["record_hash"])

    def test_P_interpreter_surrogate_target_detail_is_assigned_without_commit(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = FakeEngineTransport(root)
            output = root / "episode.json"

            def surrogate_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                return 0, {
                    "request_id": kwargs["request_id"],
                    "typed_intent": {
                        "label": "ASK_INFORMATION",
                        "claims": [],
                        "target": "\ud800",
                    },
                    "detail": "target=\ud800",
                }

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=surrogate_prompt,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="SURROGATE-P-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(30.0, 5.0, 4, 0),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "SURROGATE-P-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
                output_path=output,
            )
            written_receipt = json.loads(output.read_text(encoding="utf-8"))
            strict = json.dumps(
                written_receipt, ensure_ascii=False, allow_nan=False, sort_keys=True
            )
            strict.encode("utf-8")
            canonical = {
                key: value for key, value in written_receipt.items() if key != "record_hash"
            }
            self.assertEqual(
                written_receipt["record_hash"],
                hashlib.sha256(
                    json.dumps(
                        canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                ).hexdigest(),
            )
            encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
            self.assertIn("serialization", encoded.lower())

        self.assertFalse(record["success"])
        self.assertFalse(record["primary_success"])
        self.assertEqual(record["assignment_id"], "SURROGATE-P-001")
        self.assertEqual(written_receipt["assignment_id"], record["assignment_id"])
        self.assertEqual(written_receipt["record_hash"], record["record_hash"])
        self.assertEqual(record["failure_reason"], "proposal_source_error")
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertIsNone(record["decisions"][0]["commit"])
        self.assertFalse(record["accepted_for_engineering_verification"])
        self.assertNotEqual(record["engineering_status"], "PASS")
        self.assertEqual([call["mode"] for call in transport.calls], ["bootstrap"])

    def test_late_native_prompt_callback_uses_assigned_timeout_without_commit(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            clock = AdvancingClock()
            transport = FakeEngineTransport(root)

            def late_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                clock.advance(61.0)
                return 0, _valid_typed_intent(kwargs["request_id"])

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=late_prompt,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="LATE-PROMPT-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 0),
                seed=20261024,
                clock=clock,
                config={"assignment_id": "LATE-PROMPT-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "response_timeout")
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["decisions"][0]["commit"], None)
        self.assertEqual(len([call for call in transport.calls if call["mode"] == "experiment"]), 0)

    def test_malformed_typed_adapter_output_repairs_through_engine_with_lineage(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = GoalReachedTransport(root)
            prompt_calls: list[dict[str, Any]] = []

            def malformed_then_valid(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                prompt_calls.append(kwargs)
                if len(prompt_calls) == 1:
                    return 0, {
                        "request_id": kwargs["request_id"],
                        "typed_intent": {
                            "label": "NOT_A_CANONICAL_LABEL",
                            "claims": [],
                            "target": None,
                        },
                    }
                return 0, _valid_typed_intent(kwargs["request_id"])

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=malformed_then_valid,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="REPAIR-ADAPTER-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                repair_source=engine.repair,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 2),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "REPAIR-ADAPTER-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertTrue(record["success"])
        self.assertTrue(record["goal_reached"])
        self.assertEqual(record["accounting"]["repair_calls"], 1)
        self.assertEqual(record["accounting"]["successful_repairs"], 1)
        self.assertEqual(record["accounting"]["host_calls"], len(prompt_calls))
        self.assertEqual(record["evidence"]["calls"][0]["logical_request_id"], "decision-0")
        self.assertEqual(record["evidence"]["calls"][1]["logical_request_id"], "decision-0")
        self.assertIn("VALIDATOR_ERROR=", prompt_calls[1]["instruction"])
        self.assertIn("invalid_intent_label", prompt_calls[1]["instruction"])
        self.assertEqual(len([call for call in transport.calls if call["mode"] == "bootstrap"]), 1)

    def test_replay_goal_witness_uses_final_boolean_when_top_level_witness_is_missing(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = ReplayWitnessTransport(root, replay_goal=False)
            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **kwargs: (0, _valid_typed_intent(kwargs["request_id"])),
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="REPLAY-WITNESS-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 0),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "REPLAY-WITNESS-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertTrue(record["primary_success"])
        self.assertFalse(record["semantic_replay"]["valid"])
        checks = record["evidence"]["engine_reexecution"]["checks"]
        self.assertTrue(checks[0]["goal_witness"])
        self.assertFalse(checks[-1]["goal_witness"])
        self.assertFalse(verify_episode_record(record))

    def test_replay_conflicting_top_level_and_final_goal_witness_does_not_pass(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            transport = ReplayWitnessTransport(root, replay_goal=False, top_level_witness=True)
            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **kwargs: (0, _valid_typed_intent(kwargs["request_id"])),
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="REPLAY-WITNESS-002",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 0),
                seed=20261024,
                clock=AdvancingClock(),
                config={"assignment_id": "REPLAY-WITNESS-002", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertTrue(record["primary_success"])
        self.assertFalse(record["semantic_replay"]["valid"])
        self.assertFalse(record["evidence"]["engine_reexecution"]["checks"][0]["goal_witness"])

    def test_engine_action_timeout_uses_remaining_episode_wall_not_provider_deadline(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            clock = AdvancingClock()
            transport = GoalReachedTransport(root)
            experiment_timeouts: list[float] = []

            def slow_transport(**kwargs: Any) -> dict[str, Any]:
                if kwargs["mode"] == "experiment" and not Path(
                    kwargs["input_path"]
                ).name.startswith("reexecution-"):
                    experiment_timeouts.append(kwargs["timeout"])
                    clock.advance(70.0)
                return transport(**kwargs)

            engine = GodotEpisodeEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=lambda **kwargs: (0, _valid_typed_intent(kwargs["request_id"])),
                engine_runner=slow_transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="ENGINE-TIMEOUT-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 0),
                seed=20261024,
                clock=clock,
                config={"assignment_id": "ENGINE-TIMEOUT-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertTrue(record["success"])
        self.assertTrue(experiment_timeouts)
        self.assertGreater(experiment_timeouts[0], 60.0)

    def test_symbolic_planning_time_is_charged_after_dispatch_not_provider_timeout(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            clock = AdvancingClock()
            transport = GoalReachedTransport(root)

            def prompt_runner(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                clock.advance(10.0)
                return 0, _valid_typed_intent(kwargs["request_id"])

            class PlanningAdvancingEngine(GodotEpisodeEngine):
                def propose(self, context: dict[str, Any]) -> dict[str, Any]:
                    proposed = super().propose(context)
                    clock.advance(65.0)
                    return proposed

            engine = PlanningAdvancingEngine(
                project=root / "project",
                output_root=root / "outputs",
                prompt_runner=prompt_runner,
                engine_runner=transport,
                godot_binary="/injected/godot",
                fixture_ref=FIXTURE_REF,
                assignment_id="PLANNING-TIME-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 0),
                seed=20261024,
                clock=clock,
                config={"assignment_id": "PLANNING-TIME-001", "fixture_ref": FIXTURE_REF},
                prompt="Restore the lighthouse signal.",
            )

        self.assertTrue(record["success"])
        self.assertTrue(record["goal_reached"])
        self.assertEqual(
            record["evidence"]["time"]["ended"] - record["evidence"]["time"]["started"], 150.0
        )
        self.assertFalse(record["accounting"]["wall_expired"])

    def test_cli_composition_wires_engine_repair_without_native_process(self) -> None:
        captured: dict[str, Any] = {}

        class CapturingEngine:
            def __init__(self, **kwargs: Any) -> None:
                captured["engine"] = self
                captured["engine_kwargs"] = kwargs

            def propose(self, context: dict[str, Any]) -> dict[str, Any]:
                raise AssertionError("CLI composition must not invoke propose in this fixture")

            def repair(
                self, context: dict[str, Any], error: dict[str, Any], attempt: int
            ) -> dict[str, Any]:
                raise AssertionError("CLI composition must not invoke repair in this fixture")

        def fake_stage(_source: Path, destination: Path) -> None:
            destination.mkdir(parents=True, exist_ok=True)

        def fake_run_episode(**kwargs: Any) -> dict[str, Any]:
            captured["run_episode_kwargs"] = kwargs
            return {
                "status": "success",
                "success": True,
                "primary_success": True,
                "engineering_status": "FIX",
                "accepted_for_engineering_verification": False,
                "failure_reason": None,
                "goal_reached": True,
                "semantic_replay": {"valid": False},
                "decisions": [],
            }

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output_root = Path(directory) / "outputs"
            with (
                patch.object(runtime_cli, "GodotEpisodeEngine", CapturingEngine),
                patch.object(runtime_cli, "run_episode", fake_run_episode),
                patch.object(
                    npc_experiment, "run_godot", side_effect=AssertionError("native process")
                ) as mocked_run_godot,
                patch.object(playable_evaluation, "stage_project", fake_stage),
                patch.object(
                    sys,
                    "argv",
                    ["run_runtime_model_swap.py", "--offline", "--output-root", str(output_root)],
                ),
            ):
                exit_code = runtime_cli.main()

        self.assertEqual(exit_code, 1)
        self.assertIs(captured["run_episode_kwargs"]["repair_source"].__self__, captured["engine"])
        self.assertEqual(captured["run_episode_kwargs"]["repair_source"].__name__, "repair")
        self.assertIs(captured["engine_kwargs"]["engine_runner"], mocked_run_godot)
        self.assertFalse(mocked_run_godot.called)


@unittest.skipUnless(shutil.which("godot4") or shutil.which("godot"), "Godot 4.x is not installed")
class GodotEpisodeEngineIntegrationTests(unittest.TestCase):
    def test_two_real_experiment_cycles_bind_setup_and_reject_tampered_state_ref(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            tracked_sources = (
                "scripts/game3d/game_3d.gd",
                "scripts/experimental_game_runner.gd",
            )
            original_source_hashes = {
                name: hashlib.sha256((GODOT_PROJECT / name).read_bytes()).hexdigest()
                for name in tracked_sources
            }
            project = root / "project"
            stage_project(GODOT_PROJECT, project)
            staged_before_hashes = {
                name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                for name in tracked_sources
            }
            self.assertEqual(staged_before_hashes, original_source_hashes)
            outputs = root / "outputs"
            receipts: list[dict[str, Any]] = []
            experiment_payloads: list[dict[str, Any]] = []
            prompt_calls: list[dict[str, Any]] = []
            engine_paths: list[Path] = []

            integration_clock = AdvancingClock()

            def stable_engine_runner(**kwargs: Any) -> dict[str, Any]:
                engine_paths.append(Path(kwargs["project"]).resolve())
                if kwargs["mode"] == "experiment":
                    experiment_payloads.append(
                        json.loads(Path(kwargs["input_path"]).read_text(encoding="utf-8"))
                    )
                receipt = run_godot(**kwargs)
                receipts.append(receipt)
                integration_clock.advance(0.001)
                return receipt

            def scripted_prompt(**kwargs: Any) -> tuple[int, dict[str, Any]]:
                prompt_calls.append(kwargs)
                return 0, _valid_typed_intent(kwargs["request_id"])

            engine = GodotEpisodeEngine(
                project=project,
                output_root=outputs,
                prompt_runner=scripted_prompt,
                engine_runner=stable_engine_runner,
                godot_binary=GODOT_BINARY,
                fixture_ref=FIXTURE_REF,
                assignment_id="GODOT-REAL-001",
            )
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                model=ModelSpec("offline-scripted", "general_rule", None, None, True),
                limits=EpisodeLimits(180.0, 60.0, 12, 2),
                seed=20261024,
                clock=integration_clock,
                config={"assignment_id": "GODOT-REAL-001", "fixture_ref": FIXTURE_REF},
                prompt="Complete acquire, install, dialogue, and reveal.",
            )

            experiment_calls = [item for item in receipts if item.get("mode") == "experiment"]
            self.assertGreaterEqual(len(experiment_calls), 2)
            self.assertGreaterEqual(len(experiment_payloads), 2)
            first_trace = experiment_calls[0]["trace"]
            first_applied = [
                action
                for action in first_trace.get("actions", [])
                if action.get("status") == "APPLIED"
            ]
            self.assertTrue(first_applied)
            second_payload = experiment_payloads[1]
            self.assertEqual(
                second_payload["setup_operations"],
                [
                    {
                        "operation": first_applied[0]["operation"],
                        "arguments": first_applied[0].get("arguments", {}),
                    }
                ],
            )
            self.assertEqual(
                second_payload["initial_public_snapshot"]["state_ref"],
                first_applied[0]["state_ref_after"],
            )
            self.assertGreaterEqual(len(prompt_calls), 2)
            self.assertTrue(record["success"])
            self.assertTrue(record["goal_reached"])
            final_trace = experiment_calls[-1]["trace"]
            final_observation = (final_trace.get("observations") or [{}])[-1]
            self.assertTrue(final_observation.get("goal_reached"))
            dialogue_payloads = [
                payload for payload in experiment_payloads if payload.get("in_dialogue")
            ]
            self.assertTrue(dialogue_payloads)
            self.assertTrue(
                any(
                    any(
                        operation.get("operation") == "open_dialogue"
                        for operation in payload["setup_operations"]
                    )
                    for payload in dialogue_payloads
                )
            )
            self.assertTrue(record["evidence"]["engine_runs"])
            self.assertTrue(
                all(
                    "latency_ms" in run and "sidecar_path" in run
                    for run in record["evidence"]["engine_runs"]
                )
            )
            self.assertTrue(record["evidence"]["preparation"])
            self.assertTrue(
                all(
                    str(project) in " ".join(run["command"])
                    for run in record["evidence"]["preparation"]
                )
            )
            self.assertTrue(
                all(
                    run["input_sha256_before"] == run["input_sha256_after"]
                    and run["input_bytes_preserved"]
                    for run in record["evidence"]["engine_runs"]
                )
            )
            self.assertTrue(
                all(run["mode"] == "import" for run in record["evidence"]["preparation"])
            )
            self.assertTrue(
                all(run["mode"] != "import" for run in record["evidence"]["engine_runs"])
            )
            self.assertTrue(engine_paths)
            self.assertTrue(all(path == project.resolve() for path in engine_paths))
            self.assertNotEqual(project.resolve(), GODOT_PROJECT.resolve())
            self.assertEqual(len(prompt_calls), record["accounting"]["host_calls"])
            self.assertEqual(
                len(record["evidence"]["prompt_invocations"]), record["accounting"]["host_calls"]
            )
            reexecution = record["evidence"]["engine_reexecution"]
            self.assertTrue(reexecution["valid"])
            self.assertEqual(reexecution["model_calls"], 0)
            self.assertTrue(reexecution["checks"])
            self.assertTrue(all(check["passed"] for check in reexecution["checks"]))
            self.assertEqual(
                reexecution["scope"], "fresh_godot_processes_exact_immutable_episode_inputs"
            )
            staged_after_hashes = {
                name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                for name in tracked_sources
            }
            self.assertEqual(staged_after_hashes, original_source_hashes)
            self.assertEqual(
                {
                    name: hashlib.sha256((GODOT_PROJECT / name).read_bytes()).hexdigest()
                    for name in tracked_sources
                },
                original_source_hashes,
            )

            tampered = json.loads(json.dumps(second_payload))
            tampered["initial_public_snapshot"]["state_ref"] = {"revision": 999, "sha256": "f" * 64}
            tampered_path = root / "tampered.json"
            tampered_path.write_text(json.dumps(tampered, sort_keys=True), encoding="utf-8")
            tampered_receipt = run_godot(
                binary=GODOT_BINARY,
                project=project,
                mode="experiment",
                input_path=tampered_path,
                log_dir=root / "tampered-logs",
                timeout=60,
            )
            tampered_trace = tampered_receipt.get("trace") or {}
            self.assertIn("INITIAL_STATE_REF_MISMATCH", tampered_trace.get("errors", []))
            self.assertFalse(tampered_trace.get("passed"))
            self.assertEqual(
                {
                    name: hashlib.sha256((project / name).read_bytes()).hexdigest()
                    for name in tracked_sources
                },
                original_source_hashes,
            )
            self.assertEqual(
                {
                    name: hashlib.sha256((GODOT_PROJECT / name).read_bytes()).hexdigest()
                    for name in tracked_sources
                },
                original_source_hashes,
            )


if __name__ == "__main__":
    unittest.main()
