from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.runtime_model_swap import (
    EpisodeLimits,
    ModelSpec,
    aggregate_episode_records,
    run_episode,
    verify_episode_record,
)
from nesy_game.runtime_model_swap_native import PromptTransportError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SequenceSource:
    def __init__(self, values: list[object], *, clock: FakeClock | None = None) -> None:
        self.values = list(values)
        self.clock = clock
        self.calls = 0
        self.contexts: list[dict[str, Any]] = []

    def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        self.contexts.append(copy.deepcopy(context))
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        if self.clock is not None and isinstance(value, tuple):
            value, elapsed = value
            self.clock.advance(float(elapsed))
        return copy.deepcopy(value)


class LighthouseEngine:
    """Small deterministic engine exposing the runtime harness's public seam."""

    def __init__(self, *, initial: dict[str, Any] | None = None) -> None:
        self._state = copy.deepcopy(
            initial
            or {
                "location": "dock",
                "inventory": [],
                "facts": {"lens_reachable": True},
                "signal_restored": False,
            }
        )
        self.validate_calls: list[dict[str, Any]] = []
        self.commit_calls: list[dict[str, Any]] = []

    def state(self) -> dict[str, Any]:
        return copy.deepcopy(self._state)

    def legal_actions(self) -> list[str]:
        if self._state["location"] == "dock" and "lens" not in self._state["inventory"]:
            return ["collect_lens"]
        if self._state["location"] == "dock" and "lens" in self._state["inventory"]:
            return ["move_to_lighthouse"]
        if self._state["location"] == "lighthouse" and "lens" in self._state["inventory"]:
            return ["install_lens"]
        return []

    def preconditions(self) -> dict[str, list[str]]:
        return {
            "collect_lens": ["location=dock", "lens_not_in_inventory"],
            "move_to_lighthouse": ["lens_in_inventory", "location=dock"],
            "install_lens": ["lens_in_inventory", "location=lighthouse"],
        }

    def constraints(self) -> list[str]:
        return ["canonical_state_only", "goal_observed_by_engine"]

    def objective(self) -> str:
        return "engine_observed_signal_restored"

    def validate(self, proposal: dict[str, Any]) -> dict[str, Any]:
        self.validate_calls.append(copy.deepcopy(proposal))
        action = proposal.get("action")
        if action not in self.legal_actions():
            return {
                "valid": False,
                "code": "ILLEGAL_ACTION",
                "message": f"action {action!r} is not legal in the canonical state",
            }
        return {"valid": True, "code": None, "message": None}

    def commit(self, proposal: dict[str, Any]) -> dict[str, Any]:
        self.commit_calls.append(copy.deepcopy(proposal))
        action = proposal["action"]
        if action == "collect_lens":
            self._state["inventory"].append("lens")
        elif action == "move_to_lighthouse":
            self._state["location"] = "lighthouse"
        elif action == "install_lens":
            self._state["signal_restored"] = True
        else:  # pragma: no cover - validation must prevent this path.
            raise AssertionError(f"unvalidated action: {action}")
        return self.state()

    def objective_reached(self) -> bool:
        return bool(self._state["signal_restored"])


MODEL = ModelSpec(
    model_id="offline-synthetic-model",
    representation="general_rule",
    provider=None,
    revision=None,
    offline=True,
)
LIMITS = EpisodeLimits(
    wall_seconds=30.0,
    response_seconds=5.0,
    max_host_calls=12,
    max_repairs_per_decision=2,
)


def proposal(action: str, **extra: Any) -> dict[str, Any]:
    return {"action": action, **extra}


def canonical_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "record_hash"}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def run_offline(
    source: SequenceSource,
    engine: LighthouseEngine | None = None,
    *,
    model: ModelSpec = MODEL,
    limits: EpisodeLimits = LIMITS,
    clock: FakeClock | None = None,
    repair_source: Any = None,
    assignment_id: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    config: dict[str, Any] = {"goal": "signal_restored", "fixture": "offline-lighthouse-v1"}
    if assignment_id is not None:
        config["assignment_id"] = assignment_id
    return run_episode(
        engine=engine or LighthouseEngine(),
        proposal_source=source,
        model=model,
        limits=limits,
        seed=20261024,
        clock=clock or FakeClock(),
        config=config,
        prompt="Restore the lighthouse signal by carrying and installing the lens.",
        repair_source=repair_source,
        **kwargs,
    )


class RuntimeModelSwapTests(unittest.TestCase):
    def test_three_decisions_preserve_canonical_state_and_credit_engine_goal_only(self) -> None:
        engine = LighthouseEngine()
        source = SequenceSource(
            [
                proposal("collect_lens", goal_reached=True),
                proposal("move_to_lighthouse", goal_reached=True),
                proposal("install_lens", goal_reached=False),
            ]
        )

        record = run_offline(source, engine)

        self.assertTrue(record["success"])
        self.assertEqual(record["status"], "success")
        self.assertTrue(record["goal_reached"])
        self.assertEqual(record["initial_state"]["location"], "dock")
        self.assertEqual(record["final_state"]["location"], "lighthouse")
        self.assertEqual(record["final_state"]["inventory"], ["lens"])
        self.assertTrue(record["final_state"]["signal_restored"])
        self.assertEqual(len(engine.commit_calls), 3)
        self.assertEqual(
            [context["state"]["location"] for context in source.contexts],
            ["dock", "dock", "lighthouse"],
        )
        self.assertEqual(
            [context["state"]["inventory"] for context in source.contexts],
            [[], ["lens"], ["lens"]],
        )
        self.assertTrue(all("commit" in decision for decision in record["decisions"]))

    def test_initially_won_episode_is_not_a_success(self) -> None:
        engine = LighthouseEngine(
            initial={
                "location": "lighthouse",
                "inventory": ["lens"],
                "facts": {},
                "signal_restored": True,
            }
        )
        source = SequenceSource([proposal("install_lens")])

        record = run_offline(source, engine)

        self.assertFalse(record["success"])
        self.assertEqual(record["status"], "failure")
        self.assertEqual(record["failure_reason"], "initial_goal_reached")
        self.assertEqual(source.calls, 0)
        self.assertEqual(record["accounting"]["host_calls"], 0)

    def test_hard_invalid_proposal_cannot_mutate_canonical_state(self) -> None:
        engine = LighthouseEngine()
        before = engine.state()
        source = SequenceSource([proposal("install_lens", goal_reached=True)])

        record = run_offline(
            source,
            engine,
            limits=EpisodeLimits(30.0, 5.0, 12, 0),
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["status"], "failure")
        self.assertEqual(record["failure_reason"], "repair_budget_exhausted")
        self.assertEqual(engine.state(), before)
        self.assertEqual(engine.commit_calls, [])
        self.assertFalse(record["decisions"][0]["validation"]["valid"])
        self.assertIsNone(record["decisions"][0]["commit"])

    def test_authoritative_error_drives_bounded_repair_and_finishes_whole_goal(self) -> None:
        engine = LighthouseEngine()
        source = SequenceSource(
            [proposal("install_lens"), proposal("move_to_lighthouse"), proposal("install_lens")]
        )
        seen: list[tuple[dict[str, Any], dict[str, Any], int]] = []

        def repair(context: dict[str, Any], error: dict[str, Any], attempt: int) -> dict[str, Any]:
            seen.append((copy.deepcopy(context), copy.deepcopy(error), attempt))
            return proposal("collect_lens")

        record = run_offline(source, engine, repair_source=repair)

        self.assertTrue(record["success"])
        self.assertEqual(record["status"], "success")
        self.assertTrue(record["goal_reached"])
        self.assertEqual(seen[0][1]["code"], "ILLEGAL_ACTION")
        self.assertEqual(seen[0][2], 1)
        self.assertEqual(record["accounting"]["host_calls"], 4)
        self.assertEqual(record["accounting"]["initial_proposal_failures"], 1)
        self.assertEqual(record["accounting"]["successful_repairs"], 1)
        self.assertEqual(record["decisions"][0]["repair"]["accepted"], True)
        self.assertEqual(engine.state()["inventory"], ["lens"])
        self.assertEqual(engine.state()["location"], "lighthouse")
        self.assertEqual(len(engine.commit_calls), 3)
        self.assertEqual(
            [context["state"]["location"] for context in source.contexts],
            ["dock", "dock", "lighthouse"],
        )
        self.assertEqual(
            [context["state"]["inventory"] for context in source.contexts],
            [[], ["lens"], ["lens"]],
        )

    def test_model_self_report_does_not_substitute_for_engine_observed_goal(self) -> None:
        engine = LighthouseEngine()
        source = SequenceSource([proposal("collect_lens", goal_reached=True)])

        record = run_offline(
            source,
            engine,
            limits=EpisodeLimits(30.0, 5.0, 1, 0),
        )

        self.assertFalse(record["success"])
        self.assertFalse(record["goal_reached"])
        self.assertEqual(record["failure_reason"], "host_call_budget_exhausted")
        self.assertFalse(record["final_state"]["signal_restored"])
        self.assertEqual(source.calls, 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(len(record["evidence"]["calls"]), 1)
        self.assertEqual(len(engine.commit_calls), 1)
        self.assertFalse(engine.objective_reached())

    def test_host_budget_counts_failed_and_timeout_calls_in_original_denominator(self) -> None:
        clock = FakeClock()
        source = SequenceSource(
            [PromptTransportError("provider failed"), TimeoutError("response timed out")]
        )

        record = run_offline(
            source,
            limits=EpisodeLimits(30.0, 5.0, 2, 0),
            clock=clock,
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "host_call_budget_exhausted")
        self.assertEqual(source.calls, 2)
        self.assertEqual(record["accounting"]["host_calls"], 2)
        self.assertEqual(record["accounting"]["failed_calls"], 2)
        self.assertEqual(record["accounting"]["denominator_eligible"], True)
        self.assertEqual(len(record["evidence"]["calls"]), 2)
        self.assertEqual(
            [call["kind"] for call in record["evidence"]["calls"]], ["proposal", "proposal"]
        )
        self.assertTrue(all(call["failed"] for call in record["evidence"]["calls"]))

    def test_first_call_timeout_is_counted_and_traced_without_exception(self) -> None:
        clock = FakeClock()

        class FirstCallTimeout:
            def __init__(self) -> None:
                self.calls = 0

            def __call__(self, context: dict[str, Any]) -> dict[str, Any]:
                self.calls += 1
                clock.advance(6.0)
                raise TimeoutError("first response timed out")

        source = FirstCallTimeout()
        engine = LighthouseEngine()
        record = run_episode(
            engine=engine,
            proposal_source=source,
            model=MODEL,
            limits=EpisodeLimits(30.0, 5.0, 4, 0),
            seed=20261024,
            clock=clock,
            config={"goal": "signal_restored", "fixture": "offline-lighthouse-v1"},
            prompt="Restore the lighthouse signal by carrying and installing the lens.",
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "response_timeout")
        self.assertEqual(source.calls, 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["accounting"]["timeout_calls"], 1)
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertEqual(len(record["evidence"]["calls"]), 1)
        self.assertEqual(record["evidence"]["calls"][0]["kind"], "proposal")
        self.assertTrue(record["evidence"]["calls"][0]["failed"])
        self.assertEqual(record["evidence"]["time"]["ended"], clock.now)
        self.assertEqual(engine.commit_calls, [])

    def test_exhausted_source_is_explicit_failure_not_free_eof(self) -> None:
        source = SequenceSource([])
        record = run_offline(
            source,
            limits=EpisodeLimits(30.0, 5.0, 4, 0),
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "proposal_source_error")
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertEqual(len(record["evidence"]["calls"]), 1)
        self.assertTrue(record["evidence"]["calls"][0]["failed"])
        self.assertIn("IndexError", record["evidence"]["calls"][0]["error"])

    def test_response_timeout_is_classified_and_does_not_commit_proposal(self) -> None:
        clock = FakeClock()
        source = SequenceSource([(proposal("collect_lens"), 6.0)], clock=clock)
        engine = LighthouseEngine()

        record = run_offline(
            source,
            engine,
            limits=EpisodeLimits(30.0, 5.0, 12, 0),
            clock=clock,
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "response_timeout")
        self.assertEqual(engine.commit_calls, [])
        self.assertEqual(record["accounting"]["timeout_calls"], 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["evidence"]["time"]["ended"], clock.now)

    def test_goal_reached_after_wall_expiry_is_not_credited(self) -> None:
        clock = FakeClock()
        source = SequenceSource(
            [
                (proposal("collect_lens"), 1.0),
                (proposal("move_to_lighthouse"), 1.0),
                (proposal("install_lens"), 3.0),
            ],
            clock=clock,
        )
        engine = LighthouseEngine()

        record = run_offline(
            source,
            engine,
            limits=EpisodeLimits(4.0, 5.0, 12, 0),
            clock=clock,
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "wall_budget_exhausted")
        self.assertGreaterEqual(clock.now, 4.0)
        self.assertFalse(record["goal_reached"])
        self.assertEqual(record["accounting"]["wall_expired"], True)
        self.assertEqual(record["evidence"]["time"]["ended"], clock.now)
        self.assertEqual(len(engine.commit_calls), 2)
        self.assertEqual(
            [call["action"] for call in engine.commit_calls], ["collect_lens", "move_to_lighthouse"]
        )

    def test_aggregate_keeps_assigned_manifest_rows_in_denominator(self) -> None:
        records = [
            {"assignment_id": "A", "status": "success", "success": True},
            {
                "assignment_id": "B",
                "status": "failure",
                "success": False,
                "failure_reason": "unknown_identity",
            },
        ]

        summary = aggregate_episode_records(records, assigned_ids=["A", "B", "C"])

        self.assertEqual(summary["denominator"], 3)
        self.assertEqual(summary["successes"], 1)
        self.assertEqual(summary["failures"], 2)
        self.assertEqual(summary["missing_assignments"], ["C"])
        self.assertEqual(summary["unknown_identity_failures"], 1)
        self.assertEqual(summary["failure_rate"], 2 / 3)

    def test_aggregate_keeps_unknown_identity_and_failures_in_original_denominator(self) -> None:
        records = [
            {"assignment_id": "A", "status": "success", "success": True},
            {
                "assignment_id": "B",
                "status": "failure",
                "success": False,
                "failure_reason": "unknown_identity",
            },
            {
                "assignment_id": "C",
                "status": "failure",
                "success": False,
                "failure_reason": "provider_failure",
            },
        ]

        summary = aggregate_episode_records(records)

        self.assertEqual(summary["denominator"], 3)
        self.assertEqual(summary["successes"], 1)
        self.assertEqual(summary["failures"], 2)
        self.assertEqual(summary["unknown_identity_failures"], 1)
        self.assertEqual(summary["failure_rate"], 2 / 3)

    def test_representation_swap_is_lossless_except_rendering(self) -> None:
        semantic_fields = ("state", "legal_actions", "preconditions", "constraints", "objective")
        ontology_source = SequenceSource([proposal("collect_lens")])
        rule_source = SequenceSource([proposal("collect_lens")])
        ontology_model = ModelSpec("offline-synthetic-model", "ontology", None, None, True)
        rule_model = ModelSpec("offline-synthetic-model", "general_rule", None, None, True)

        run_offline(ontology_source, model=ontology_model)
        run_offline(rule_source, model=rule_model)

        ontology_input = ontology_source.contexts[0]["model_input"]
        rule_input = rule_source.contexts[0]["model_input"]
        for field in semantic_fields:
            self.assertEqual(ontology_input[field], rule_input[field], field)
        self.assertNotEqual(ontology_input["rendering"], rule_input["rendering"])
        self.assertEqual(ontology_input["representation"], "ontology")
        self.assertEqual(rule_input["representation"], "general_rule")

    def test_offline_evidence_retains_unknown_provider_fields_and_semantic_trace(self) -> None:
        source = SequenceSource(
            [proposal("collect_lens"), proposal("move_to_lighthouse"), proposal("install_lens")]
        )

        record = run_offline(source)
        evidence = record["evidence"]

        self.assertIsNone(evidence["provider_revision"])
        self.assertIsNone(evidence["cost_usd"])
        self.assertIsNone(evidence["provider_request_count"])
        self.assertEqual(evidence["provenance"], {"mode": "offline", "synthetic": True})
        self.assertEqual(evidence["seed"], 20261024)
        for field in ("prompt_hash", "config_hash", "request_hash"):
            self.assertRegex(evidence[field], r"^[0-9a-f]{64}$")
        self.assertEqual(len(evidence["raw_proposals"]), 3)
        self.assertEqual(len(evidence["validation"]), 3)
        self.assertEqual(len(evidence["repair"]), 3)
        self.assertEqual(len(evidence["commit"]), 3)
        self.assertIn("time", evidence)
        self.assertIn("calls", evidence)
        self.assertTrue(record["semantic_replay"]["valid"])

    def test_semantic_replay_rejects_rehashed_tampered_transition(self) -> None:
        source = SequenceSource(
            [proposal("collect_lens"), proposal("move_to_lighthouse"), proposal("install_lens")]
        )
        record = run_offline(source)
        self.assertTrue(verify_episode_record(record))

        tampered = copy.deepcopy(record)
        tampered["decisions"][0]["commit"]["state"]["inventory"] = []
        tampered["record_hash"] = canonical_hash(tampered)

        self.assertFalse(verify_episode_record(tampered))

    def test_live_provider_is_fail_closed_before_launcher_or_model_call(self) -> None:
        source = SequenceSource([AssertionError("model call must not happen")])
        launcher_calls: list[dict[str, Any]] = []

        def launcher(**kwargs: Any) -> object:
            launcher_calls.append(kwargs)
            raise AssertionError("provider launcher must not happen")

        live_model = ModelSpec("unavailable-live", "general_rule", "provider-x", None, True)
        record = run_offline(
            source,
            model=live_model,
            provider_launcher=launcher,
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "provider_not_allowed_offline")
        self.assertEqual(source.calls, 0)
        self.assertEqual(launcher_calls, [])
        self.assertIsNone(record["evidence"]["provider_identity"])
        self.assertIsNone(record["evidence"]["provider_request_count"])

    def test_existing_output_collision_fails_closed_without_overwrite(self) -> None:
        source = SequenceSource([proposal("collect_lens")])
        original = b"pre-existing immutable output\n"

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "runtime-model-swap-collision-fixture"
            output.write_bytes(original)

            with self.assertRaises(FileExistsError):
                run_offline(source, output_path=output)

            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(source.calls, 0)

    def test_goal_true_after_commit_deadline_is_not_credited(self) -> None:
        clock = FakeClock()

        class LateGoalEngine(LighthouseEngine):
            def commit(self, proposal: dict[str, Any]) -> dict[str, Any]:
                super().commit(proposal)
                self._state["signal_restored"] = True
                clock.advance(5.0)
                return self.state()

        engine = LateGoalEngine()
        source = SequenceSource([proposal("collect_lens")])
        record = run_offline(
            source,
            engine,
            limits=EpisodeLimits(4.0, 5.0, 12, 0),
            clock=clock,
        )

        self.assertFalse(record["success"])
        self.assertFalse(record["goal_reached"])
        self.assertEqual(record["failure_reason"], "wall_budget_exhausted")
        self.assertTrue(record["accounting"]["wall_expired"])
        self.assertTrue(engine.objective_reached())
        self.assertEqual(len(engine.commit_calls), 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)

    def test_offline_provider_rejection_precedes_engine_and_source_activity(self) -> None:
        activity: list[str] = []

        class ActivityEngine(LighthouseEngine):
            def state(self) -> dict[str, Any]:
                activity.append("engine.state")
                return super().state()

            def objective_reached(self) -> bool:
                activity.append("engine.objective_reached")
                return super().objective_reached()

        def forbidden_source(_context: dict[str, Any]) -> dict[str, Any]:
            activity.append("source")
            raise AssertionError("provider rejection must precede proposal activity")

        record = run_episode(
            engine=ActivityEngine(),
            proposal_source=forbidden_source,
            model=ModelSpec("hosted-model", "general_rule", "provider-x", None, True),
            limits=LIMITS,
            seed=20261024,
            clock=FakeClock(),
            config={"goal": "signal_restored", "fixture": "offline-lighthouse-v1"},
            prompt="Restore the lighthouse signal.",
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "provider_not_allowed_offline")
        self.assertEqual(activity, [])
        self.assertEqual(record["accounting"]["host_calls"], 0)
        self.assertIsNone(record["evidence"]["provider_identity"])

    def test_manifest_record_identity_and_empty_denominator_are_explicit(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate assignment record:A"):
            aggregate_episode_records(
                [
                    {"assignment_id": "A", "status": "failure", "success": False},
                    {"assignment_id": "A", "status": "success", "success": True},
                ]
            )
        with self.assertRaisesRegex(ValueError, "manifest records require assignment_id"):
            aggregate_episode_records([{"status": "failure", "success": False}], assigned_ids=["A"])

        summary = aggregate_episode_records([], assigned_ids=[])
        self.assertEqual(summary["denominator"], 0)
        self.assertEqual(summary["successes"], 0)
        self.assertEqual(summary["failures"], 0)
        self.assertIsNone(summary["failure_rate"])

    def test_goal_observer_failure_after_commit_is_retained_as_assigned_failure(self) -> None:
        class GoalObserverFailureEngine(LighthouseEngine):
            def objective_reached(self) -> bool:
                if self.commit_calls:
                    raise RuntimeError("goal observer unavailable")
                return super().objective_reached()

        engine = GoalObserverFailureEngine()
        source = SequenceSource([proposal("collect_lens")])
        record = run_offline(source, engine, limits=EpisodeLimits(30.0, 5.0, 12, 0))

        self.assertFalse(record["success"])
        self.assertFalse(record["goal_reached"])
        self.assertEqual(record["failure_reason"], "goal_observation_unavailable")
        self.assertTrue(record["accounting"]["denominator_eligible"])
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(source.calls, 1)
        self.assertEqual(len(engine.commit_calls), 1)
        self.assertEqual(record["final_state"]["inventory"], ["lens"])

    def test_replay_failure_preserves_primary_goal_but_rejects_engineering_credit(self) -> None:
        class ReplayFailureEngine(LighthouseEngine):
            def reexecute(self) -> dict[str, Any]:
                return {
                    "valid": False,
                    "status": "completed",
                    "checks": [{"passed": False, "error": "replay_trace_mismatch"}],
                    "model_calls": 0,
                }

        engine = ReplayFailureEngine()
        record = run_offline(
            SequenceSource(
                [proposal("collect_lens"), proposal("move_to_lighthouse"), proposal("install_lens")]
            ),
            engine,
        )

        self.assertTrue(record["success"])
        self.assertTrue(record["goal_reached"])
        self.assertTrue(record["primary_success"])
        self.assertNotEqual(record["engineering_status"], "PASS")
        self.assertFalse(record["accepted_for_engineering_verification"])
        self.assertFalse(verify_episode_record(record))
        summary = aggregate_episode_records([record])
        self.assertEqual(summary["primary_successes"], 1)
        self.assertEqual(summary["verified_primary_successes"], 0)

    def test_non_json_proposals_are_assigned_json_safe_failures(self) -> None:
        cases = (
            ("set_payload", {"action": "collect_lens", "metadata": {"unserializable"}}),
            ("nan_payload", {"action": "collect_lens", "score": float("nan")}),
            ("surrogate_payload", {"action": "collect_lens", "metadata": "\ud800"}),
        )
        for name, value in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "episode.json"
                record = run_episode(
                    engine=LighthouseEngine(),
                    proposal_source=SequenceSource([value]),
                    model=MODEL,
                    limits=LIMITS,
                    seed=20261024,
                    clock=FakeClock(),
                    config={"assignment_id": "NONJSON-" + name, "goal": "signal_restored"},
                    prompt="Restore the lighthouse signal.",
                    output_path=output,
                )

                self.assertEqual(record["assignment_id"], "NONJSON-" + name)
                self.assertFalse(record["success"])
                self.assertIsNone(record["decisions"][0]["commit"])
                self.assertEqual(record["accounting"]["host_calls"], 1)
                self.assertEqual(record["accounting"]["failed_calls"], 1)
                encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
                self.assertIn("serialization", encoded.lower())
                self.assertIn(name.split("_")[0], encoded.lower())
                persisted = json.loads(output.read_text(encoding="utf-8"))
                persisted_encoded = json.dumps(
                    persisted, ensure_ascii=False, allow_nan=False, sort_keys=True
                )
                persisted_encoded.encode("utf-8")
                self.assertEqual(persisted["assignment_id"], record["assignment_id"])
                self.assertEqual(persisted["record_hash"], record["record_hash"])

    def test_surrogate_proposal_exception_message_is_assigned_utf8_safe_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            assignment_id = "NONJSON-EXCEPTION-SURROGATE"
            output = Path(directory) / "episode.json"
            source = SequenceSource([ValueError("proposal callback failed: \ud800")])
            record = run_episode(
                engine=LighthouseEngine(),
                proposal_source=source,
                model=MODEL,
                limits=LIMITS,
                seed=20261024,
                clock=FakeClock(),
                config={"assignment_id": assignment_id, "goal": "signal_restored"},
                prompt="Restore the lighthouse signal.",
                output_path=output,
            )
            self._assert_strict_persisted_record(record, output, assignment_id)
            encoded = json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True)
            encoded.encode("utf-8")

        self.assertFalse(record["success"])
        self.assertFalse(record["primary_success"])
        self.assertEqual(record["failure_reason"], "proposal_source_error")
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertIsNone(record["decisions"][0]["commit"])
        self.assertEqual(source.calls, 1)

    def _assert_strict_persisted_record(
        self, record: dict[str, Any], output: Path, assignment_id: str
    ) -> dict[str, Any]:
        persisted = json.loads(output.read_text(encoding="utf-8"))
        encoded = json.dumps(persisted, ensure_ascii=False, allow_nan=False, sort_keys=True)
        encoded.encode("utf-8")
        self.assertEqual(json.loads(encoded), persisted)
        self.assertEqual(record["assignment_id"], assignment_id)
        self.assertEqual(persisted["assignment_id"], assignment_id)
        self.assertEqual(persisted["record_hash"], record["record_hash"])
        self.assertEqual(persisted["record_hash"], canonical_hash(persisted))
        self.assertTrue(record["accounting"]["denominator_eligible"])
        self.assertFalse(record["accepted_for_engineering_verification"])
        self.assertNotEqual(record["engineering_status"], "PASS")
        return persisted

    def test_malformed_initial_and_semantic_callbacks_are_assigned_output_rows(self) -> None:
        class MalformedPreconditionsEngine(LighthouseEngine):
            def __init__(self, value: object) -> None:
                super().__init__()
                self.preconditions_invocations = 0
                self._value = value

            def preconditions(self) -> dict[str, Any]:
                self.preconditions_invocations += 1
                return {"collect_lens": self._value}

        cases = (
            ("initial_object", {"bad": object()}),
            ("initial_set", {"bad": {"unserializable"}}),
            ("initial_nan", {"bad": float("nan")}),
            ("initial_surrogate", {"bad": "\ud800"}),
            ("semantic_object", MalformedPreconditionsEngine(object())),
            ("semantic_set", MalformedPreconditionsEngine({"unserializable"})),
            ("semantic_nan", MalformedPreconditionsEngine(float("nan"))),
            ("semantic_surrogate", MalformedPreconditionsEngine("\ud800")),
        )

        for name, malformed in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                assignment_id = "CALLBACK-STATE-" + name
                output = Path(directory) / "episode.json"
                if isinstance(malformed, LighthouseEngine):
                    engine = malformed
                else:
                    initial = {
                        "location": "dock",
                        "inventory": [],
                        "facts": malformed,
                        "signal_restored": False,
                    }
                    engine = LighthouseEngine(initial=initial)

                source = SequenceSource([proposal("collect_lens")])
                record = run_offline(
                    source, engine, assignment_id=assignment_id, output_path=output
                )
                self._assert_strict_persisted_record(record, output, assignment_id)

                self.assertFalse(record["success"])
                self.assertFalse(record["primary_success"])
                self.assertEqual(record["failure_reason"], "engine_unavailable")
                self.assertEqual(source.calls, 0)
                if isinstance(engine, MalformedPreconditionsEngine):
                    self.assertEqual(engine.preconditions_invocations, 1)

    def test_malformed_validation_commit_and_goal_callbacks_are_assigned_output_rows(self) -> None:
        class MalformedValidationEngine(LighthouseEngine):
            def __init__(self, value: object) -> None:
                super().__init__()
                self.validation_invocations = 0
                self._value = value

            def validate(self, proposal_value: dict[str, Any]) -> object:
                self.validation_invocations += 1
                super().validate(proposal_value)
                return copy.deepcopy(self._value)

        class MalformedCommitEngine(LighthouseEngine):
            def __init__(self, value: object) -> None:
                super().__init__()
                self.commit_invocations = 0
                self._value = value

            def commit(self, proposal_value: dict[str, Any]) -> object:
                self.commit_invocations += 1
                super().commit(proposal_value)
                return copy.deepcopy(self._value)

        class MalformedObjectiveEngine(LighthouseEngine):
            def __init__(self, value: object) -> None:
                super().__init__()
                self.objective_invocations = 0
                self._value = value

            def objective_reached(self) -> object:
                self.objective_invocations += 1
                if self.objective_invocations == 1:
                    return False
                return copy.deepcopy(self._value)

        validation_cases = (
            ("validation_list", []),
            ("validation_object", {"valid": False, "detail": object()}),
            ("validation_set", {"valid": False, "detail": {"unserializable"}}),
            ("validation_nan", {"valid": False, "detail": float("nan")}),
            ("validation_surrogate", {"valid": False, "detail": "\ud800"}),
        )
        commit_cases = (
            ("commit_object", {"bad": object()}),
            ("commit_set", {"bad": {"unserializable"}}),
            ("commit_nan", {"bad": float("nan")}),
            ("commit_surrogate", {"bad": "\ud800"}),
        )
        objective_cases = (
            ("objective_object", object()),
            ("objective_set", {"unserializable"}),
            ("objective_nan", float("nan")),
            ("objective_nonboolean", 1),
            ("objective_surrogate", "\ud800"),
        )

        for name, malformed in validation_cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                assignment_id = "CALLBACK-VALIDATION-" + name
                output = Path(directory) / "episode.json"
                engine = MalformedValidationEngine(malformed)
                source = SequenceSource([proposal("collect_lens")])
                record = run_offline(
                    source, engine, output_path=output, assignment_id=assignment_id
                )
                self._assert_strict_persisted_record(record, output, assignment_id)

                self.assertFalse(record["success"])
                self.assertFalse(record["primary_success"])
                self.assertEqual(record["failure_reason"], "validation_failure")
                self.assertEqual(engine.validation_invocations, 1)
                self.assertEqual(source.calls, 1)

        for name, malformed in commit_cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                assignment_id = "CALLBACK-COMMIT-" + name
                output = Path(directory) / "episode.json"
                valid_state = {
                    "location": "dock",
                    "inventory": ["lens"],
                    "facts": {"lens_reachable": True},
                    "signal_restored": False,
                }
                engine = MalformedCommitEngine({**valid_state, "facts": malformed})
                source = SequenceSource([proposal("collect_lens")])
                record = run_offline(
                    source, engine, output_path=output, assignment_id=assignment_id
                )
                self._assert_strict_persisted_record(record, output, assignment_id)

                self.assertFalse(record["success"])
                self.assertFalse(record["primary_success"])
                self.assertEqual(record["failure_reason"], "commit_failure")
                self.assertEqual(engine.commit_invocations, 1)
                self.assertEqual(record["final_state"]["inventory"], ["lens"])

        for name, malformed in objective_cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                assignment_id = "CALLBACK-GOAL-" + name
                output = Path(directory) / "episode.json"
                engine = MalformedObjectiveEngine(malformed)
                source = SequenceSource([proposal("collect_lens")])
                record = run_offline(
                    source, engine, output_path=output, assignment_id=assignment_id
                )
                self._assert_strict_persisted_record(record, output, assignment_id)

                self.assertFalse(record["success"])
                self.assertFalse(record["primary_success"])
                self.assertEqual(record["failure_reason"], "goal_observation_unavailable")
                self.assertEqual(engine.objective_invocations, 2)
                self.assertEqual(source.calls, 1)

    def test_malformed_posthoc_replay_retains_primary_goal_but_rejects_engineering_acceptance(
        self,
    ) -> None:
        class MalformedReplayEngine(LighthouseEngine):
            def __init__(self, value: object) -> None:
                super().__init__()
                self.reexecute_invocations = 0
                self._value = value

            def reexecute(self) -> object:
                self.reexecute_invocations += 1
                return copy.deepcopy(self._value)

        cases = (
            ("replay_list", []),
            ("replay_nonjson", {"valid": object()}),
            ("replay_missing_marker", {"status": "completed"}),
            ("replay_nonboolean_marker", {"valid": 1}),
            ("replay_surrogate", {"valid": "\ud800"}),
        )

        for name, malformed in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                assignment_id = "CALLBACK-REPLAY-" + name
                output = Path(directory) / "episode.json"
                engine = MalformedReplayEngine(malformed)
                source = SequenceSource(
                    [
                        proposal("collect_lens"),
                        proposal("move_to_lighthouse"),
                        proposal("install_lens"),
                    ]
                )
                record = run_offline(
                    source, engine, output_path=output, assignment_id=assignment_id
                )
                self._assert_strict_persisted_record(record, output, assignment_id)

                self.assertTrue(record["success"])
                self.assertTrue(record["goal_reached"])
                self.assertTrue(record["primary_success"])
                self.assertFalse(record["semantic_replay"]["valid"])
                self.assertFalse(record["accepted_for_engineering_verification"])
                self.assertNotEqual(record["engineering_status"], "PASS")
                self.assertFalse(verify_episode_record(record))
                self.assertEqual(engine.reexecute_invocations, 1)
                self.assertEqual(source.calls, 3)

    def test_malformed_final_state_after_timely_goal_preserves_primary_and_rejects_engineering(
        self,
    ) -> None:
        class MalformedFinalStateEngine(LighthouseEngine):
            def __init__(self) -> None:
                super().__init__()
                self.goal_witnessed = False
                self.state_invocations = 0
                self.post_terminal_state_observed = False

            def state(self) -> dict[str, Any]:
                self.state_invocations += 1
                state = super().state()
                if self.goal_witnessed:
                    self.post_terminal_state_observed = True
                    state["facts"] = {"post_terminal": object()}
                return state

            def objective_reached(self) -> bool:
                reached = super().objective_reached()
                if reached:
                    self.goal_witnessed = True
                return reached

        with tempfile.TemporaryDirectory() as directory:
            assignment_id = "CALLBACK-FINAL-STATE-001"
            output = Path(directory) / "episode.json"
            engine = MalformedFinalStateEngine()
            source = SequenceSource(
                [
                    proposal("collect_lens"),
                    proposal("move_to_lighthouse"),
                    proposal("install_lens"),
                ]
            )
            record = run_offline(source, engine, output_path=output, assignment_id=assignment_id)
            self._assert_strict_persisted_record(record, output, assignment_id)

        self.assertTrue(engine.goal_witnessed)
        self.assertTrue(engine.post_terminal_state_observed)
        self.assertTrue(record["success"])
        self.assertTrue(record["goal_reached"])
        self.assertTrue(record["primary_success"])
        self.assertEqual(record["failure_reason"], "engine_unavailable")
        self.assertNotEqual(record["safety"]["status"], "PASS")
        self.assertFalse(record["accepted_for_engineering_verification"])
        self.assertNotEqual(record["engineering_status"], "PASS")

    def test_observed_prompt_invocation_delta_is_charged_before_commit(self) -> None:
        class ObservedPromptEngine(LighthouseEngine):
            def __init__(self) -> None:
                super().__init__(
                    initial={
                        "location": "lighthouse",
                        "inventory": ["lens"],
                        "facts": {"lens_reachable": True},
                        "signal_restored": False,
                    }
                )
                self.prompt_invocation_count = 0
                self.commit_invocations = 0

            def commit(self, proposal_value: dict[str, Any]) -> dict[str, Any]:
                self.commit_invocations += 1
                return super().commit(proposal_value)

        class DoubleDispatchSource:
            def __init__(self, engine: ObservedPromptEngine) -> None:
                self.engine = engine
                self.calls = 0

            def __call__(self, _context: dict[str, Any]) -> dict[str, Any]:
                self.calls += 1
                self.engine.prompt_invocation_count += 2
                return proposal("install_lens")

        cases = (("over_budget", 1, False), ("exact_final_call", 2, True))
        for name, max_host_calls, expected_success in cases:
            with self.subTest(name=name):
                engine = ObservedPromptEngine()
                source = DoubleDispatchSource(engine)
                record = run_offline(
                    source,
                    engine,
                    limits=EpisodeLimits(30.0, 5.0, max_host_calls, 0),
                )

                self.assertEqual(record["accounting"]["host_calls"], 2)
                self.assertEqual(source.calls, 1)
                self.assertEqual(engine.commit_invocations, 1 if expected_success else 0)
                self.assertEqual(record["success"], expected_success)
                self.assertEqual(record["primary_success"], expected_success)
                if expected_success:
                    self.assertTrue(record["goal_reached"])
                    self.assertTrue(record["accepted_for_engineering_verification"])
                else:
                    self.assertEqual(record["failure_reason"], "host_call_budget_exhausted")
                    self.assertFalse(record["goal_reached"])
                    self.assertFalse(record["accepted_for_engineering_verification"])

    def test_counter_only_prompt_telemetry_preserves_initial_source_failure_row(self) -> None:
        class CounterOnlyEngine(LighthouseEngine):
            def __init__(self) -> None:
                super().__init__()
                self.prompt_invocation_count = 0

        class FailingSource:
            def __init__(self, engine: CounterOnlyEngine) -> None:
                self.engine = engine
                self.calls = 0

            def __call__(self, _context: dict[str, Any]) -> dict[str, Any]:
                self.calls += 1
                self.engine.prompt_invocation_count += 1
                raise ValueError("bad offline response")

        with tempfile.TemporaryDirectory() as directory:
            assignment_id = "COUNTER-ONLY-INITIAL-SOURCE"
            output = Path(directory) / "episode.json"
            engine = CounterOnlyEngine()
            source = FailingSource(engine)
            record = run_offline(
                source,
                engine,
                assignment_id=assignment_id,
                output_path=output,
            )
            persisted = self._assert_strict_persisted_record(record, output, assignment_id)
            json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")

        self.assertFalse(record["success"])
        self.assertFalse(record["primary_success"])
        self.assertEqual(record["failure_reason"], "proposal_source_error")
        self.assertEqual(record["last_error"], "ValueError: bad offline response")
        self.assertEqual(source.calls, 1)
        self.assertEqual(engine.prompt_invocation_count, 1)
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["accounting"]["source_attempts"], 1)
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertEqual(record["evidence"]["calls"][0]["host_invocations"], 1)
        self.assertEqual(
            record["evidence"]["calls"][0]["error"], "ValueError: bad offline response"
        )
        self.assertEqual(engine.commit_calls, [])
        self.assertIsNone(record["decisions"][0]["commit"])
        self.assertEqual(persisted["assignment_id"], assignment_id)
        self.assertTrue(record["accounting"]["denominator_eligible"])
        self.assertFalse(verify_episode_record(record))

    def test_counter_only_prompt_telemetry_preserves_repair_source_failure_row(self) -> None:
        class CounterOnlyEngine(LighthouseEngine):
            def __init__(self) -> None:
                super().__init__()
                self.prompt_invocation_count = 0

        class CountingInitialSource:
            def __init__(self, engine: CounterOnlyEngine) -> None:
                self.engine = engine
                self.calls = 0

            def __call__(self, _context: dict[str, Any]) -> dict[str, Any]:
                self.calls += 1
                self.engine.prompt_invocation_count += 1
                return proposal("install_lens")

        class FailingRepair:
            def __init__(self, engine: CounterOnlyEngine) -> None:
                self.engine = engine
                self.calls = 0
                self.contexts: list[dict[str, Any]] = []

            def __call__(
                self,
                context: dict[str, Any],
                _error: dict[str, Any],
                attempt: int,
            ) -> dict[str, Any]:
                self.calls += 1
                self.contexts.append(copy.deepcopy(context))
                self.engine.prompt_invocation_count += 1
                self.assert_attempt = attempt
                raise ValueError("bad offline response")

        with tempfile.TemporaryDirectory() as directory:
            assignment_id = "COUNTER-ONLY-REPAIR-SOURCE"
            output = Path(directory) / "episode.json"
            engine = CounterOnlyEngine()
            repair = FailingRepair(engine)
            source = CountingInitialSource(engine)
            record = run_offline(
                source,
                engine,
                limits=EpisodeLimits(30.0, 5.0, 12, 1),
                assignment_id=assignment_id,
                output_path=output,
                repair_source=repair,
            )
            persisted = self._assert_strict_persisted_record(record, output, assignment_id)
            json.dumps(record, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")

        self.assertFalse(record["success"])
        self.assertFalse(record["primary_success"])
        self.assertEqual(record["failure_reason"], "repair_source_error")
        self.assertEqual(record["last_error"], "ValueError: bad offline response")
        self.assertEqual(repair.calls, 1)
        self.assertEqual(repair.assert_attempt, 1)
        self.assertEqual(source.calls, 1)
        self.assertEqual(engine.prompt_invocation_count, 2)
        self.assertEqual(record["accounting"]["host_calls"], 2)
        self.assertEqual(record["accounting"]["source_attempts"], 2)
        self.assertEqual(record["accounting"]["failed_calls"], 1)
        self.assertEqual(record["accounting"]["repair_calls"], 1)
        self.assertEqual(record["accounting"]["initial_proposal_failures"], 1)
        self.assertEqual(
            [call["host_invocations"] for call in record["evidence"]["calls"]],
            [1, 1],
        )
        self.assertEqual(
            [call["logical_request_id"] for call in record["evidence"]["calls"]],
            ["decision-0", "decision-0"],
        )
        self.assertEqual(repair.contexts[0]["logical_request_id"], "decision-0")
        self.assertEqual(
            record["evidence"]["calls"][1]["error"], "ValueError: bad offline response"
        )
        self.assertEqual(engine.commit_calls, [])
        self.assertIsNone(record["decisions"][0]["commit"])
        self.assertEqual(persisted["assignment_id"], assignment_id)
        self.assertTrue(record["accounting"]["denominator_eligible"])
        self.assertFalse(verify_episode_record(record))

    def test_setup_time_is_outside_episode_wall_and_first_host_boundary_is_explicit(self) -> None:
        clock = FakeClock()

        class SlowSetupEngine(LighthouseEngine):
            def __init__(self) -> None:
                super().__init__()
                self._setup_observed = False

            def state(self) -> dict[str, Any]:
                if not self._setup_observed:
                    self._setup_observed = True
                    clock.advance(150.0)
                return super().state()

        record = run_offline(
            SequenceSource(
                [proposal("collect_lens"), proposal("move_to_lighthouse"), proposal("install_lens")]
            ),
            SlowSetupEngine(),
            limits=EpisodeLimits(30.0, 5.0, 12, 0),
            clock=clock,
        )

        self.assertTrue(record["success"])
        self.assertFalse(record["accounting"]["wall_expired"])
        self.assertEqual(record["evidence"]["time"]["started"], 150.0)
        self.assertLessEqual(record["evidence"]["time"]["ended"] - 150.0, 30.0)

    def test_elapsed_host_validation_repair_and_engine_time_is_charged_after_dispatch(self) -> None:
        clock = FakeClock()

        class SlowValidationEngine(LighthouseEngine):
            def validate(self, proposal: dict[str, Any]) -> dict[str, Any]:
                clock.advance(10.0)
                return super().validate(proposal)

            def commit(self, proposal: dict[str, Any]) -> dict[str, Any]:
                clock.advance(20.0)
                return super().commit(proposal)

        source = SequenceSource(
            [
                (proposal("move_to_lighthouse"), 10.0),
                (proposal("move_to_lighthouse"), 10.0),
                (proposal("install_lens"), 10.0),
            ],
            clock=clock,
        )

        def repair(
            _context: dict[str, Any], _error: dict[str, Any], _attempt: int
        ) -> dict[str, Any]:
            clock.advance(10.0)
            return proposal("collect_lens")

        record = run_offline(
            source,
            SlowValidationEngine(),
            limits=EpisodeLimits(180.0, 60.0, 12, 2),
            clock=clock,
            repair_source=repair,
        )

        self.assertTrue(record["success"])
        self.assertEqual(record["accounting"]["host_calls"], 4)
        self.assertEqual(record["accounting"]["initial_proposal_failures"], 1)
        self.assertEqual(record["accounting"]["successful_repairs"], 1)
        self.assertEqual(
            record["evidence"]["time"]["ended"] - record["evidence"]["time"]["started"], 140.0
        )
        self.assertFalse(record["accounting"]["wall_expired"])

    def test_late_host_result_is_discarded_without_commit(self) -> None:
        clock = FakeClock()
        source = SequenceSource([(proposal("collect_lens"), 61.0)], clock=clock)

        record = run_offline(
            source,
            limits=EpisodeLimits(180.0, 60.0, 12, 0),
            clock=clock,
        )

        self.assertFalse(record["success"])
        self.assertEqual(record["failure_reason"], "response_timeout")
        self.assertFalse(record["accounting"]["wall_expired"])
        self.assertEqual(record["accounting"]["host_calls"], 1)
        self.assertEqual(record["decisions"][0]["commit"], None)

    def test_aggregate_separates_primary_goal_from_safety_coverage_and_labels_bookkeeping(
        self,
    ) -> None:
        records = [
            {
                "assignment_id": "safe",
                "status": "success",
                "success": True,
                "primary_success": True,
                "engineering_status": "PASS",
                "accepted_for_engineering_verification": True,
                "safety": {"status": "PASS"},
                "scope": "bookkeeping",
            },
            {
                "assignment_id": "unsafe",
                "status": "success",
                "success": True,
                "primary_success": True,
                "engineering_status": "FIX",
                "accepted_for_engineering_verification": False,
                "safety": {"status": "FAIL"},
                "scope": "bookkeeping",
            },
            {
                "assignment_id": "unverified",
                "status": "failure",
                "success": False,
                "primary_success": False,
                "engineering_status": "NOT_PASS",
                "accepted_for_engineering_verification": False,
                "safety": {"status": "NOT_PASS"},
                "scope": "bookkeeping",
            },
            {
                "assignment_id": "no-commit",
                "status": "failure",
                "success": False,
                "primary_success": False,
                "engineering_status": "NOT_PASS",
                "accepted_for_engineering_verification": False,
                "safety": {"status": "NO_COMMIT_OBSERVED"},
                "scope": "bookkeeping",
            },
        ]

        summary = aggregate_episode_records(records)

        self.assertEqual(summary["primary_successes"], 2)
        self.assertEqual(summary["verified_primary_successes"], 1)
        self.assertEqual(
            summary["safety_coverage"],
            {"PASS": 1, "FAIL": 1, "NOT_PASS": 1, "NO_COMMIT_OBSERVED": 1},
        )
        self.assertEqual(summary["scope"], "bookkeeping")


if __name__ == "__main__":
    unittest.main()
