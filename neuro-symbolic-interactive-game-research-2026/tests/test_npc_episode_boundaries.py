from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))

from nesy_game.npc_goal import (
    BudgetExceeded,
    ControllerFailure,
    GoalController,
    IntentInterpreter,
    Interpretation,
    ProtocolError,
    ReplayValidator,
    canonical_config_hash,
    content_hash,
    default_envelope,
)

POLICY_HASH = "2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd"
OBS_KEYS = {
    "lens_reachable",
    "lens_carried",
    "signal_restored",
    "tide_lead_authorized",
    "goal_reached",
    "in_dialogue",
}


def observation(**overrides: bool) -> dict[str, bool]:
    result = {key: False for key in OBS_KEYS}
    result.update(overrides)
    return result


def request(
    *,
    request_id: str = "episode-request",
    session_id: str = "episode-session",
    epoch: int = 0,
    episode_id: str = "episode-1",
    revision: int = 0,
    obs: dict[str, bool] | None = None,
    event_kind: str = "utterance",
    utterance: str | None = "Where is the lens?",
    budget: dict | None = None,
) -> dict:
    payload = default_envelope(
        message_type="request",
        request_id=request_id,
        session_id=session_id,
        session_epoch=epoch,
        sequence=-1,
        delivery_index=-1,
        state_ref={
            "revision": revision,
            "sha256": hashlib.sha256(f"state-{revision}".encode()).hexdigest(),
        },
        body={
            "event_kind": event_kind,
            "utterance": None if event_kind == "observation" else utterance,
            "observation": obs or observation(lens_reachable=True),
        },
        arm="R",
        backend="rule",
        policy_hash=POLICY_HASH,
    )
    payload["episode_id"] = episode_id
    if budget is not None:
        payload["budget"] = copy.deepcopy(budget)
    payload["content_sha256"] = content_hash(payload)
    return payload


def result_for(
    source: dict,
    step: dict,
    *,
    status: str = "APPLIED",
    revision: int | None = None,
    state_hash: str | None = None,
) -> dict:
    world_operation = step["operation"] in {"acquire_object", "install_lens", "reveal_hint"}
    result_revision = (
        source["state_ref"]["revision"] + 1
        if revision is None and world_operation and status == "APPLIED"
        else source["state_ref"]["revision"]
        if revision is None
        else revision
    )
    result_state = {
        "revision": result_revision,
        "sha256": state_hash or hashlib.sha256(f"state-{result_revision}".encode()).hexdigest(),
    }
    payload = default_envelope(
        message_type="result",
        request_id=source["request_id"],
        session_id=source["session_id"],
        session_epoch=source["session_epoch"],
        sequence=1,
        delivery_index=1,
        state_ref=result_state,
        body={
            "action_id": step["action_id"],
            "operation": step["operation"],
            "status": status,
            "engine_revision": result_revision,
            "state_ref": result_state,
            "feedback": "applied",
            "observation": observation(lens_reachable=True),
        },
        arm="R",
        backend="rule",
        policy_hash=source["policy_hash"],
    )
    payload["episode_id"] = source["episode_id"]
    payload["config_hash"] = source["config_hash"]
    payload["content_sha256"] = content_hash(payload)
    return payload


class CountingInterpreter:
    arm = "R"

    def __init__(self) -> None:
        self.calls = 0

    def interpret(
        self, *, request_id: str, utterance: str, timeout_ms: int | None = None
    ) -> Interpretation:
        self.calls += 1
        return Interpretation(
            request_id + ".intent",
            {"label": "ASK_INFORMATION", "claims": [], "target": None},
            "rule",
            "R",
        )


class NpcEpisodeBoundaryTests(unittest.TestCase):
    def test_observation_epoch_resume_reuses_one_intent_and_replays_each_snapshot(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        initial = request(request_id="resume-intent", obs=observation(lens_reachable=True))
        decision = controller.handle_request(initial)
        self.assertEqual(decision["body"]["steps"][0]["operation"], "acquire_object")
        self.assertEqual(
            controller.handle_result(result_for(initial, decision["body"]["steps"][0]))["body"][
                "status"
            ],
            "ACCEPTED",
        )

        snapshots = [controller.export_trace(initial["session_id"], session_epoch=0)]
        installed_observation = request(
            request_id="resume-installed",
            epoch=1,
            revision=1,
            event_kind="observation",
            obs=observation(lens_carried=True),
            utterance=None,
        )
        installed_decision = controller.handle_request(installed_observation)
        self.assertEqual(installed_decision["body"]["steps"][0]["operation"], "install_lens")
        self.assertEqual(
            controller.handle_result(
                result_for(installed_observation, installed_decision["body"]["steps"][0])
            )["body"]["status"],
            "ACCEPTED",
        )
        snapshots.append(controller.export_trace(initial["session_id"], session_epoch=1))

        reveal_observation = request(
            request_id="resume-reveal",
            epoch=2,
            revision=2,
            event_kind="observation",
            obs=observation(
                lens_carried=True, signal_restored=True, tide_lead_authorized=True, in_dialogue=True
            ),
            utterance=None,
        )
        reveal_decision = controller.handle_request(reveal_observation)
        self.assertEqual(reveal_decision["body"]["steps"][0]["operation"], "reveal_hint")
        self.assertEqual(
            controller.handle_result(
                result_for(reveal_observation, reveal_decision["body"]["steps"][0])
            )["body"]["status"],
            "ACCEPTED",
        )
        snapshots.append(controller.export_trace(initial["session_id"], session_epoch=2))

        self.assertEqual(interpreter.calls, 1)
        for epoch, snapshot in enumerate(snapshots):
            with self.subTest(epoch=epoch):
                self.assertEqual(snapshot["session_epoch"], epoch)
                self.assertTrue(
                    ReplayValidator.validate(snapshot, expected_session_id=initial["session_id"])[
                        "valid"
                    ]
                )

    def test_operation_conditioned_result_transitions_are_enforced(self) -> None:
        cases = (
            ("acquire", observation(lens_reachable=True), "acquire_object", "WAITING_PLAYER"),
            ("install", observation(lens_carried=True), "install_lens", "WAITING_PLAYER"),
            (
                "reveal",
                observation(
                    lens_carried=True,
                    signal_restored=True,
                    tide_lead_authorized=True,
                    in_dialogue=True,
                ),
                "reveal_hint",
                "READY",
            ),
            (
                "negotiate",
                observation(lens_carried=True, signal_restored=True, tide_lead_authorized=True),
                "negotiate",
                "WAITING_DIALOGUE",
            ),
            (
                "clarify",
                observation(
                    lens_carried=True,
                    signal_restored=True,
                    tide_lead_authorized=True,
                    in_dialogue=True,
                ),
                "clarify",
                "WAITING_DIALOGUE",
            ),
        )
        for name, obs, operation, _status in cases:
            with self.subTest(operation=name):
                controller = GoalController(interpreter=IntentInterpreter(arm="R"))
                source = request(
                    request_id=f"transition-{name}",
                    obs=obs,
                    utterance="Please help." if name == "clarify" else "Where is the lens?",
                )
                self.assertEqual(source["config_hash"], canonical_config_hash())
                decision = controller.handle_request(source)
                self.assertEqual(decision["body"]["steps"][0]["operation"], operation)
                result = result_for(source, decision["body"]["steps"][0])
                if operation in {"negotiate", "clarify"}:
                    result["body"]["engine_revision"] = source["state_ref"]["revision"]
                    result["body"]["state_ref"] = source["state_ref"]
                    result["state_ref"] = source["state_ref"]
                    result["content_sha256"] = content_hash(result)
                accepted = controller.handle_result(result)
                self.assertEqual(accepted["body"]["status"], "ACCEPTED")

    def test_non_applied_and_stale_results_preserve_state_and_quota(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="non-applied", obs=observation(lens_reachable=True))
        decision = controller.handle_request(source)
        step = decision["body"]["steps"][0]
        non_applied = result_for(
            source,
            step,
            status="ERROR",
            revision=source["state_ref"]["revision"],
            state_hash=source["state_ref"]["sha256"],
        )
        self.assertEqual(controller.handle_result(non_applied)["body"]["status"], "ACCEPTED")

        stale_source = request(request_id="stale", obs=observation(lens_reachable=True))
        stale_decision = controller.handle_request(stale_source)
        stale = result_for(
            stale_source,
            stale_decision["body"]["steps"][0],
            status="STALE",
            revision=stale_source["state_ref"]["revision"],
            state_hash=stale_source["state_ref"]["sha256"],
        )
        rejected = controller.handle_result(stale)
        self.assertEqual(rejected["body"]["status"], "REJECTED")
        self.assertEqual(rejected["body"]["error"], "stale_result")
        self.assertEqual(controller.handle_result(stale)["body"]["status"], "REJECTED")
        valid_retry = result_for(stale_source, stale_decision["body"]["steps"][0])
        self.assertEqual(controller.handle_result(valid_retry)["body"]["status"], "ACCEPTED")

    def test_invalid_result_state_transitions_are_rejected(self) -> None:
        cases = (
            (
                "acquire_object",
                observation(lens_reachable=True),
                "APPLIED",
                0,
                "state-0",
                "applied_revision_mismatch",
            ),
            (
                "install_lens",
                observation(lens_carried=True),
                "APPLIED",
                0,
                "state-0",
                "applied_revision_mismatch",
            ),
            (
                "reveal_hint",
                observation(
                    lens_carried=True,
                    signal_restored=True,
                    tide_lead_authorized=True,
                    in_dialogue=True,
                ),
                "APPLIED",
                0,
                "state-0",
                "applied_revision_mismatch",
            ),
            (
                "negotiate",
                observation(lens_carried=True, signal_restored=True, tide_lead_authorized=True),
                "APPLIED",
                1,
                None,
                "dialogue_state_changed",
            ),
            (
                "acquire_object",
                observation(lens_reachable=True),
                "ERROR",
                1,
                None,
                "non_applied_state_changed",
            ),
        )
        for index, (operation, obs, status, revision, state_hash, error) in enumerate(cases):
            with self.subTest(operation=operation, status=status):
                controller = GoalController(interpreter=IntentInterpreter(arm="R"))
                source = request(request_id=f"invalid-transition-{index}", obs=obs)
                decision = controller.handle_request(source)
                self.assertEqual(decision["body"]["steps"][0]["operation"], operation)
                result = result_for(
                    source,
                    decision["body"]["steps"][0],
                    status=status,
                    revision=revision,
                    state_hash=hashlib.sha256((state_hash or "changed").encode()).hexdigest(),
                )
                rejected = controller.handle_result(result)
                self.assertEqual(rejected["body"]["status"], "REJECTED")
                self.assertEqual(rejected["body"]["error"], error)

    def test_rehashed_replay_rejects_operation_transition_violation(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="replay-transition", obs=observation(lens_reachable=True))
        decision = controller.handle_request(source)
        invalid = result_for(
            source,
            decision["body"]["steps"][0],
            revision=source["state_ref"]["revision"],
            state_hash=source["state_ref"]["sha256"],
        )
        invalid["content_sha256"] = content_hash(invalid)
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate(
                [source, decision, invalid], expected_session_id=source["session_id"]
            )
        self.assertEqual(str(raised.exception), "replay_result_transition_mismatch")

    def test_higher_epoch_inherits_calls_actions_replans_and_search_budget(self) -> None:
        base = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 1,
            "max_action_attempts": 1,
            "max_replans": 1,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=base)
        first = request(request_id="budget-first", budget=base)
        first_decision = controller.handle_request(first)
        first_result = result_for(first, first_decision["body"]["steps"][0])
        self.assertEqual(controller.handle_result(first_result)["body"]["status"], "ACCEPTED")
        replacement = request(
            request_id="budget-epoch",
            epoch=1,
            revision=1,
            obs=observation(lens_carried=True),
            budget=base,
        )
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_request(replacement)
        self.assertEqual(str(raised.exception), "max_intent_calls")

    def test_higher_epoch_preserves_action_attempt_quota(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 1,
            "max_replans": 8,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        old = request(request_id="action-old", budget=budget)
        old_decision = controller.handle_request(old)
        self.assertEqual(
            controller.handle_result(result_for(old, old_decision["body"]["steps"][0]))["body"][
                "status"
            ],
            "ACCEPTED",
        )
        new = request(
            request_id="action-new",
            epoch=1,
            revision=1,
            obs=observation(lens_carried=True),
            budget=budget,
        )
        new_decision = controller.handle_request(new)
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_result(result_for(new, new_decision["body"]["steps"][0], revision=2))
        self.assertEqual(str(raised.exception), "max_action_attempts")

    def test_higher_epoch_preserves_replan_quota(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 8,
            "max_replans": 1,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        old = request(request_id="replan-old", budget=budget)
        old_decision = controller.handle_request(old)
        self.assertEqual(
            controller.handle_result(result_for(old, old_decision["body"]["steps"][0]))["body"][
                "status"
            ],
            "ACCEPTED",
        )
        new = request(
            request_id="replan-new",
            epoch=1,
            revision=1,
            obs=observation(lens_carried=True),
            budget=budget,
        )
        new_decision = controller.handle_request(new)
        self.assertEqual(controller.handle_request(new), new_decision)
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_result(result_for(new, new_decision["body"]["steps"][0], revision=2))
        self.assertEqual(str(raised.exception), "max_replans")

    def test_higher_epoch_preserves_plan_search_budget(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 8,
            "max_replans": 8,
            "max_plan_expansions": 4,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        old = request(request_id="search-old", budget=budget)
        controller.handle_request(old)
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_request(request(request_id="search-new", epoch=1, budget=budget))
        self.assertEqual(str(raised.exception), "max_plan_expansions")

    def test_expired_same_episode_cannot_be_resurrected_by_higher_epoch(self) -> None:
        clock = [100.0]
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 100,
            "max_intent_calls": 8,
            "max_action_attempts": 8,
            "max_replans": 8,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        with patch("nesy_game.npc_goal.time.monotonic", side_effect=lambda: clock[0]):
            controller = GoalController(
                interpreter=IntentInterpreter(arm="R"), budget=budget, session_ttl_seconds=10
            )
            controller.handle_request(request(request_id="expires", budget=budget))
            clock[0] += 0.101
            with self.assertRaises(ControllerFailure) as raised:
                controller.handle_request(request(request_id="resurrect", epoch=1, budget=budget))
        self.assertEqual(str(raised.exception), "session_expired")

    def test_epoch_replacement_preserves_old_snapshot_for_replay(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        old = request(request_id="old-commit")
        old_decision = controller.handle_request(old)
        old_result = result_for(old, old_decision["body"]["steps"][0])
        self.assertEqual(controller.handle_result(old_result)["body"]["status"], "ACCEPTED")
        new = request(
            request_id="new-epoch", epoch=1, revision=1, obs=observation(lens_carried=True)
        )
        controller.handle_request(new)
        old_snapshot = controller.export_trace(old["session_id"], session_epoch=0)
        current_snapshot = controller.export_trace(old["session_id"])
        self.assertEqual(old_snapshot["session_epoch"], 0)
        self.assertEqual(current_snapshot["session_epoch"], 1)
        self.assertGreaterEqual(old_snapshot["cursor"]["row_count"], 3)
        self.assertEqual(old_snapshot["cursor"]["row_count"], len(old_snapshot["rows"]))
        self.assertTrue(
            ReplayValidator.validate(old_snapshot, expected_session_id=old["session_id"])["valid"]
        )
        self.assertNotEqual(old_snapshot["snapshot_id"], current_snapshot["snapshot_id"])


if __name__ == "__main__":
    unittest.main()
