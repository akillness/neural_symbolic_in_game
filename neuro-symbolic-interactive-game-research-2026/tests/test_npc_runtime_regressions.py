from __future__ import annotations

import copy
import hashlib
import json
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

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
    content_hash,
    default_envelope,
    sha256_json,
    validate_envelope,
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
    request_id: str = "request-1",
    session_id: str = "runtime-session",
    epoch: int = 0,
    episode_id: str = "episode-1",
    revision: int = 0,
    obs: dict[str, bool] | None = None,
    utterance: str = "Where is the lens?",
    budget: dict | None = None,
    state_ref: dict[str, object] | None = None,
) -> dict:
    payload = default_envelope(
        message_type="request",
        request_id=request_id,
        session_id=session_id,
        session_epoch=epoch,
        sequence=-1,
        delivery_index=-1,
        state_ref=state_ref
        if state_ref is not None
        else {
            "revision": revision,
            "sha256": hashlib.sha256(f"state-{revision}".encode()).hexdigest(),
        },
        body={
            "event_kind": "utterance",
            "utterance": utterance,
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
    source: dict, step: dict, *, action_id: str | None = None, operation: str | None = None
) -> dict:
    result_operation = operation or step["operation"]
    source_revision = source["state_ref"]["revision"]
    mutates_world = result_operation in {"acquire_object", "install_lens", "reveal_hint"}
    result_revision = source_revision + 1 if mutates_world else source_revision
    result_state = {
        "revision": result_revision,
        "sha256": hashlib.sha256(f"state-{result_revision}".encode()).hexdigest(),
    }
    payload = default_envelope(
        message_type="result",
        request_id=source["request_id"],
        session_id=source["session_id"],
        session_epoch=source["session_epoch"],
        state_ref=result_state,
        body={
            "action_id": action_id or step["action_id"],
            "operation": result_operation,
            "status": "APPLIED",
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
    if source.get("config_hash") is not None:
        payload["config_hash"] = source["config_hash"]
    payload["budget"] = copy.deepcopy(source["budget"])
    payload["content_sha256"] = content_hash(payload)
    return payload


def rehash(payload: dict) -> dict:
    payload = copy.deepcopy(payload)
    payload["content_sha256"] = content_hash(payload)
    return payload


def assert_rejected(
    test: unittest.TestCase, controller: GoalController, payload: dict, *, error: str
) -> None:
    try:
        response = controller.handle_result(payload)
    except (ProtocolError, ControllerFailure) as exc:
        test.assertEqual(str(exc), error)
        return
    test.assertEqual(response["body"]["status"], "REJECTED")
    test.assertEqual(response["body"]["error"], error)


def gate_first_commit(
    controller: GoalController, method_name: str
) -> tuple[threading.Event, threading.Event]:
    original = getattr(controller, method_name)
    reached = threading.Event()
    release = threading.Event()
    calls = [0]

    def gated(*args, **kwargs):
        calls[0] += 1
        if calls[0] == 1:
            reached.set()
            if not release.wait(2):
                raise AssertionError("commit barrier was not released")
        return original(*args, **kwargs)

    setattr(controller, method_name, gated)
    return reached, release


class BarrierInterpreter:
    arm = "R"

    def __init__(self) -> None:
        self.started = threading.Event()
        self.release = threading.Event()
        self.calls = 0

    def interpret(
        self, *, request_id: str, utterance: str, timeout_ms: int | None = None
    ) -> Interpretation:
        self.calls += 1
        self.started.set()
        if not self.release.wait(2):
            raise AssertionError("barrier was not released")
        return Interpretation(
            request_id + ".intent",
            {"label": "ASK_INFORMATION", "claims": [], "target": None},
            "rule",
            "R",
        )


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


class NpcRuntimeRegressionTests(unittest.TestCase):
    def test_raw_utterance_digest_mismatch_rejects_before_session_or_interpreter(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        payload = request(request_id="raw-digest-mismatch", utterance="Where is the lens?")
        payload["provenance"] = {
            **payload["provenance"],
            "raw_utterance_sha256": hashlib.sha256(b"different utterance").hexdigest(),
        }
        payload["content_sha256"] = content_hash(payload)

        with self.assertRaises(ProtocolError) as raised:
            controller.handle_request(payload)

        self.assertEqual(str(raised.exception), "raw_utterance_hash_mismatch")
        self.assertEqual(interpreter.calls, 0)
        self.assertEqual(controller._sessions, {})
        self.assertEqual(controller._inflight_sessions, set())

    def test_utterance_requires_matching_raw_utf8_digest(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        utterance = "Where is the lens? 灯台"
        payload = request(request_id="raw-digest-valid", utterance=utterance)
        payload["provenance"] = {
            **payload["provenance"],
            "raw_utterance_sha256": hashlib.sha256(utterance.encode("utf-8")).hexdigest(),
        }
        payload["content_sha256"] = content_hash(payload)
        decision = controller.handle_request(payload)
        self.assertEqual(interpreter.calls, 1)
        self.assertEqual(
            decision["provenance"]["raw_utterance_sha256"],
            payload["provenance"]["raw_utterance_sha256"],
        )

        missing = request(request_id="raw-digest-missing", utterance=utterance)
        missing["provenance"] = {**missing["provenance"], "raw_utterance_sha256": None}
        missing["content_sha256"] = content_hash(missing)
        with self.assertRaises(ProtocolError) as raised:
            controller.handle_request(missing)
        self.assertEqual(str(raised.exception), "raw_utterance_hash_required")
        self.assertEqual(interpreter.calls, 1)

    def test_observation_raw_digest_is_null_only(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        controller.handle_request(request(request_id="observation-prior"))
        observation_request = request(request_id="observation-raw-null")
        observation_request["body"] = {
            **observation_request["body"],
            "event_kind": "observation",
            "utterance": None,
        }
        observation_request["provenance"] = {
            **observation_request["provenance"],
            "raw_utterance_sha256": None,
        }
        observation_request["content_sha256"] = content_hash(observation_request)
        decision = controller.handle_request(observation_request)
        self.assertEqual(decision["body"]["status"], "WAITING_PLAYER")
        self.assertEqual(interpreter.calls, 1)

        forbidden = copy.deepcopy(observation_request)
        forbidden["request_id"] = "observation-raw-present"
        forbidden["provenance"] = {
            **forbidden["provenance"],
            "raw_utterance_sha256": hashlib.sha256(b"not-an-observation-utterance").hexdigest(),
        }
        forbidden["content_sha256"] = content_hash(forbidden)
        with self.assertRaises(ProtocolError) as raised:
            controller.handle_request(forbidden)
        self.assertEqual(str(raised.exception), "observation_raw_utterance_hash_forbidden")
        self.assertEqual(interpreter.calls, 1)

    def test_canonical_schema_accepts_generated_typed_intent_and_decision(self) -> None:
        seen_schema = {}

        def runner(**kwargs):
            seen_schema.update(kwargs)
            output = {
                "request_id": kwargs["request_id"],
                "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
            }
            schema = json.loads(Path(kwargs["output_schema"]).read_text(encoding="utf-8"))
            self.assertEqual(list(Draft202012Validator(schema).iter_errors(output)), [])
            return 0, output

        controller = GoalController(interpreter=IntentInterpreter(arm="P", prompt_runner=runner))
        payload = request(request_id="schema", budget=None)
        payload["provenance"] = {**payload["provenance"], "arm": "P", "backend": "codex"}
        payload["content_sha256"] = content_hash(payload)
        decision = controller.handle_request(payload)
        schema = json.loads(
            (P / "game-track/schemas/npc-goal-recovery.schema.json").read_text(encoding="utf-8")
        )
        self.assertEqual(list(Draft202012Validator(schema).iter_errors(decision)), [])
        self.assertIn("output_schema", seen_schema)

    def test_adapter_timeout_is_minimum_of_intent_and_episode_remainders(self) -> None:
        seen: dict[str, float] = {}

        def runner(**kwargs):
            seen["timeout"] = kwargs["timeout"]
            return 0, {
                "request_id": kwargs["request_id"],
                "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
            }

        budget = {
            "intent_deadline_ms": 1_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 32,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="P", prompt_runner=runner))
        payload = request(request_id="adapter-budget", budget=budget)
        payload["provenance"] = {**payload["provenance"], "arm": "P", "backend": "codex"}
        payload["content_sha256"] = content_hash(payload)
        controller.handle_request(payload)
        self.assertEqual(seen["timeout"], 1.0)

    def test_adapter_timeout_is_capped_by_episode_remainder(self) -> None:
        seen: dict[str, float] = {}

        def runner(**kwargs):
            seen["timeout"] = kwargs["timeout"]
            return 0, {
                "request_id": kwargs["request_id"],
                "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
            }

        calls = [0]

        def monotonic() -> float:
            calls[0] += 1
            return 0.0 if calls[0] <= 2 else 0.8

        budget = {
            "intent_deadline_ms": 1_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 32,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        with patch("nesy_game.npc_goal.time.monotonic", side_effect=monotonic):
            controller = GoalController(
                interpreter=IntentInterpreter(arm="P", prompt_runner=runner),
                session_ttl_seconds=1,
            )
            payload = request(request_id="episode-budget", budget=budget)
            payload["provenance"] = {**payload["provenance"], "arm": "P", "backend": "codex"}
            payload["content_sha256"] = content_hash(payload)
            controller.handle_request(payload)
        self.assertEqual(seen["timeout"], 0.2)

    def test_malformed_enum_containers_and_boolean_revisions_are_protocol_errors(self) -> None:
        cases = []
        payload = request(request_id="bad-message")
        payload["message_type"] = []
        cases.append(payload)
        payload = request(request_id="bad-arm")
        payload["provenance"]["arm"] = {}
        cases.append(payload)
        payload = request(request_id="bad-revision")
        payload["state_ref"]["revision"] = True
        cases.append(payload)
        payload = request(request_id="bad-budget")
        payload["budget"]["max_intent_calls"] = True
        cases.append(payload)
        payload = result_for(
            request(request_id="bad-operation"),
            {"action_id": "action-x", "operation": "acquire_object"},
        )
        payload["body"]["operation"] = []
        cases.append(payload)
        for index, candidate in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ProtocolError):
                validate_envelope(rehash(candidate))

    def test_result_must_bind_to_issued_request_episode_operation_and_state(self) -> None:
        mutations = (
            (
                "wrong-request",
                lambda result: result.update(request_id="other-request"),
                "result_binding_mismatch",
            ),
            (
                "wrong-episode",
                lambda result: result.update(episode_id="other-episode"),
                "episode_id_changed",
            ),
            (
                "wrong-operation",
                lambda result: result["body"].update(operation="reveal_hint"),
                "result_binding_mismatch",
            ),
            (
                "wrong-state",
                lambda result: (
                    result.update(state_ref={"revision": 7, "sha256": "7" * 64}),
                    result["body"].update(
                        state_ref={"revision": 7, "sha256": "7" * 64}, engine_revision=7
                    ),
                ),
                "applied_revision_mismatch",
            ),
        )
        for name, mutate, error in mutations:
            with self.subTest(binding=name):
                controller = GoalController(interpreter=IntentInterpreter(arm="R"))
                source = request(request_id=name)
                decision = controller.handle_request(source)
                result = result_for(source, decision["body"]["steps"][0])
                mutate(result)
                assert_rejected(self, controller, rehash(result), error=error)

    def test_unsolicited_result_is_rejected_without_state_adoption(self) -> None:
        source = request(request_id="unissued")
        result = result_for(source, {"action_id": "invented-action", "operation": "acquire_object"})

        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        controller.handle_request(source)
        assert_rejected(self, controller, result, error="unknown_action")

    def test_stale_and_regressing_results_are_rejected_without_state_adoption(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="stale-result")
        decision = controller.handle_request(source)
        stale = result_for(source, decision["body"]["steps"][0])
        stale["body"]["status"] = "STALE"
        stale["body"]["engine_revision"] = 1
        assert_rejected(self, controller, rehash(stale), error="stale_result")

        accepted = result_for(source, decision["body"]["steps"][0])
        accepted["body"]["engine_revision"] = 1
        accepted["body"]["state_ref"] = {"revision": 1, "sha256": "1" * 64}
        accepted["state_ref"] = {"revision": 1, "sha256": "1" * 64}
        self.assertEqual(controller.handle_result(rehash(accepted))["body"]["status"], "ACCEPTED")
        follow_up = request(
            request_id="follow-up",
            revision=1,
            obs=observation(lens_carried=True),
            state_ref=accepted["state_ref"],
        )
        next_decision = controller.handle_request(follow_up)
        regressing = result_for(follow_up, next_decision["body"]["steps"][0])
        regressing["body"]["engine_revision"] = 0
        regressing["state_ref"] = {"revision": 0, "sha256": "0" * 64}
        regressing["body"]["state_ref"] = {"revision": 0, "sha256": "0" * 64}
        assert_rejected(self, controller, rehash(regressing), error="applied_revision_mismatch")

    def test_identical_result_retry_is_duplicate_but_conflicting_duplicate_is_rejected(
        self,
    ) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 1,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        source = request(request_id="duplicate", budget=budget)
        decision = controller.handle_request(source)
        result = result_for(source, decision["body"]["steps"][0])
        self.assertEqual(controller.handle_result(result)["body"]["status"], "ACCEPTED")
        self.assertEqual(controller.handle_result(result)["body"]["status"], "DUPLICATE")
        conflicting = copy.deepcopy(result)
        conflicting["body"]["status"] = "ERROR"
        conflicting["body"]["observation"] = observation(goal_reached=True)
        assert_rejected(self, controller, rehash(conflicting), error="conflicting_duplicate")

    def test_action_attempt_budget_rejects_second_distinct_accepted_result(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 1,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        first_source = request(request_id="attempt-one", budget=budget)
        first_decision = controller.handle_request(first_source)
        first_result = result_for(first_source, first_decision["body"]["steps"][0])
        first_state = {"revision": 1, "sha256": "1" * 64}
        first_result["state_ref"] = first_state
        first_result["body"]["state_ref"] = first_state
        first_result["body"]["engine_revision"] = first_state["revision"]
        first_result["body"]["observation"] = observation(lens_carried=True)
        self.assertEqual(
            controller.handle_result(rehash(first_result))["body"]["status"], "ACCEPTED"
        )

        second_source = request(
            request_id="attempt-two",
            revision=1,
            obs=observation(lens_carried=True),
            budget=budget,
            state_ref=first_state,
        )
        second_decision = controller.handle_request(second_source)
        second_step = second_decision["body"]["steps"][0]
        self.assertNotEqual(
            first_decision["body"]["steps"][0]["action_id"], second_step["action_id"]
        )
        second_result = result_for(second_source, second_step)
        second_state = {"revision": 2, "sha256": "2" * 64}
        second_result["state_ref"] = second_state
        second_result["body"]["state_ref"] = second_state
        second_result["body"]["engine_revision"] = second_state["revision"]
        second_result["body"]["observation"] = observation(lens_carried=True)
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_result(rehash(second_result))
        self.assertEqual(str(raised.exception), "max_action_attempts")

    def test_decision_trace_capacity_rejects_before_inference_without_partial_mutation(
        self,
    ) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter, max_trace_rows=3)
        first = request(request_id="trace-capacity-first")
        controller.handle_request(first)
        state = controller._sessions[first["session_id"]]
        before = {
            "trace": copy.deepcopy(state.trace),
            "replay_records": copy.deepcopy(state.replay_records),
            "plan": copy.deepcopy(state.plan),
            "issued_actions": copy.deepcopy(state.issued_actions),
            "request_digests": copy.deepcopy(state.request_digests),
            "last_interpretation": copy.deepcopy(state.last_interpretation),
            "last_observation": copy.deepcopy(state.last_observation),
            "last_state_ref": copy.deepcopy(state.last_state_ref),
            "last_raw_utterance_sha256": state.last_raw_utterance_sha256,
            "calls": state.calls,
            "replans": state.replans,
            "expansions": state.expansions,
        }
        cache_before = copy.deepcopy(controller._cache)

        second = request(
            request_id="trace-capacity-second",
            obs=observation(lens_carried=True),
            utterance="I found the lens.",
        )
        with self.assertRaises(ControllerFailure) as raised:
            controller.handle_request(second)

        self.assertEqual(str(raised.exception), "trace_overflow")
        self.assertEqual(interpreter.calls, 1)
        self.assertEqual(state.trace, before["trace"])
        self.assertEqual(state.replay_records, before["replay_records"])
        self.assertEqual(state.plan, before["plan"])
        self.assertEqual(state.issued_actions, before["issued_actions"])
        self.assertEqual(state.request_digests, before["request_digests"])
        self.assertEqual(state.last_interpretation, before["last_interpretation"])
        self.assertEqual(state.last_observation, before["last_observation"])
        self.assertEqual(state.last_state_ref, before["last_state_ref"])
        self.assertEqual(state.last_raw_utterance_sha256, before["last_raw_utterance_sha256"])
        self.assertEqual(state.calls, before["calls"])
        self.assertEqual(state.replans, before["replans"])
        self.assertEqual(state.expansions, before["expansions"])
        self.assertEqual(controller._cache, cache_before)

    def test_result_trace_capacity_rejects_before_state_and_acceptance_mutation(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), max_trace_rows=2)
        source = request(request_id="result-trace-capacity")
        decision = controller.handle_request(source)
        result = result_for(source, decision["body"]["steps"][0])
        state = controller._sessions[source["session_id"]]
        before = {
            "trace": copy.deepcopy(state.trace),
            "replay_records": copy.deepcopy(state.replay_records),
            "plan": copy.deepcopy(state.plan),
            "action_attempts": state.action_attempts,
            "replans": state.replans,
            "last_state_ref": copy.deepcopy(state.last_state_ref),
            "last_observation": copy.deepcopy(state.last_observation),
            "accepted_results": copy.deepcopy(state.accepted_results),
            "last_result_ids": copy.deepcopy(state.last_result_ids),
        }

        with self.assertRaises(ControllerFailure) as raised:
            controller.handle_result(result)

        self.assertEqual(str(raised.exception), "trace_overflow")
        self.assertEqual(state.trace, before["trace"])
        self.assertEqual(state.replay_records, before["replay_records"])
        self.assertEqual(state.plan, before["plan"])
        self.assertEqual(state.action_attempts, before["action_attempts"])
        self.assertEqual(state.replans, before["replans"])
        self.assertEqual(state.last_state_ref, before["last_state_ref"])
        self.assertEqual(state.last_observation, before["last_observation"])
        self.assertEqual(state.accepted_results, before["accepted_results"])
        self.assertEqual(state.last_result_ids, before["last_result_ids"])

    def test_rejected_trace_admission_releases_capacity_for_retry(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter, max_trace_rows=3)
        first = request(request_id="trace-retry-first")
        controller.handle_request(first)
        second = request(request_id="trace-retry-second", utterance="I found the lens.")
        with self.assertRaises(ControllerFailure) as raised:
            controller.handle_request(second)
        self.assertEqual(str(raised.exception), "trace_overflow")
        self.assertEqual(interpreter.calls, 1)

        controller.max_trace_rows = 4
        retried = controller.handle_request(second)
        self.assertEqual(retried["request_id"], second["request_id"])
        self.assertEqual(interpreter.calls, 2)

    def test_utterance_only_epoch_supersession_counts_replans_and_preserves_world(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 8,
            "max_action_attempts": 32,
            "max_replans": 1,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter, budget=budget)
        first = request(request_id="supersede-0", epoch=0, budget=budget)
        controller.handle_request(first)
        second = request(
            request_id="supersede-1",
            epoch=1,
            budget=budget,
            utterance="Please reconsider the same clue.",
        )
        controller.handle_request(second)
        state = controller._sessions[first["session_id"]]
        self.assertEqual(state.replans, 1)
        self.assertEqual(state.action_attempts, 0)
        self.assertEqual(state.last_state_ref["revision"], 0)
        self.assertEqual(state.accepted_results, {})
        self.assertEqual(state.last_result_ids, set())
        causes = [
            row["data"].get("replan_cause")
            for row in state.trace
            if row.get("event_type") in {"decision", "result"}
        ]
        self.assertIn("utterance_supersede", causes)

        third = request(
            request_id="supersede-2",
            epoch=2,
            budget=budget,
            utterance="One more wording for the same clue.",
        )
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_request(third)
        self.assertEqual(str(raised.exception), "max_replans")
        self.assertEqual(interpreter.calls, 2)

    def test_same_epoch_state_reference_guard_rejects_stale_and_forked_without_mutation(
        self,
    ) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        source = request(request_id="state-guard-source", revision=0)
        decision = controller.handle_request(source)
        result = result_for(source, decision["body"]["steps"][0])
        self.assertEqual(controller.handle_result(result)["body"]["status"], "ACCEPTED")
        state = controller._sessions[source["session_id"]]
        self.assertEqual(state.last_state_ref["revision"], 1)

        before = {
            "trace": copy.deepcopy(state.trace),
            "replay_records": copy.deepcopy(state.replay_records),
            "plan": copy.deepcopy(state.plan),
            "calls": state.calls,
            "last_state_ref": copy.deepcopy(state.last_state_ref),
            "request_digests": copy.deepcopy(state.request_digests),
        }
        stale = request(request_id="state-guard-stale", revision=0)
        with self.assertRaisesRegex(ControllerFailure, "^stale_state_ref$"):
            controller.handle_request(stale)
        self.assertEqual(interpreter.calls, 1)
        self.assertEqual(state.trace, before["trace"])
        self.assertEqual(state.replay_records, before["replay_records"])
        self.assertEqual(state.plan, before["plan"])
        self.assertEqual(state.calls, before["calls"])
        self.assertEqual(state.last_state_ref, before["last_state_ref"])
        self.assertEqual(state.request_digests, before["request_digests"])

        forked = request(request_id="state-guard-forked", revision=1)
        forked["state_ref"]["sha256"] = "f" * 64
        forked["body"]["observation"] = observation(lens_carried=True)
        forked["content_sha256"] = content_hash(forked)
        with self.assertRaisesRegex(ControllerFailure, "^forked_state_ref$"):
            controller.handle_request(forked)
        self.assertEqual(interpreter.calls, 1)
        self.assertEqual(state.trace, before["trace"])
        self.assertEqual(state.replay_records, before["replay_records"])
        self.assertEqual(state.plan, before["plan"])
        self.assertEqual(state.calls, before["calls"])
        self.assertEqual(state.last_state_ref, before["last_state_ref"])
        self.assertEqual(state.request_digests, before["request_digests"])

        higher = request(
            request_id="state-guard-gap",
            revision=3,
            obs=observation(lens_carried=True),
        )
        higher["body"] = {**higher["body"], "event_kind": "observation", "utterance": None}
        higher["provenance"] = {**higher["provenance"], "raw_utterance_sha256": None}
        higher["content_sha256"] = content_hash(higher)
        accepted = controller.handle_request(higher)
        self.assertEqual(accepted["body"]["status"], "WAITING_PLAYER")
        self.assertEqual(interpreter.calls, 1)
        self.assertEqual(state.last_state_ref["revision"], 3)

    def test_cancel_winning_decision_commit_has_no_publication_side_effects(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        payload = request(request_id="cancel-before-decision-commit")
        reached, release = gate_first_commit(controller, "_commit_decision")
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_request(payload)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(reached.wait(1))
        controller.cancel(payload["session_id"], payload["session_epoch"])
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcome.get("error"), ControllerFailure)
        self.assertEqual(str(outcome["error"]), "session_closed_or_cancelled")
        self.assertNotIn("value", outcome)
        trace = controller.export_trace(payload["session_id"])
        self.assertFalse(
            any(
                row.get("message_type") == "decision" or row.get("event_type") == "decision"
                for row in trace["rows"]
            )
        )

    def test_decision_publication_winning_cancel_is_ordered_after_cached_publication(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        payload = request(request_id="decision-before-cancel")
        reached, release = gate_first_commit(controller, "_commit_decision")
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_request(payload)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(reached.wait(1))
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertNotIn("error", outcome)
        self.assertEqual(controller.handle_request(payload), outcome["value"])
        controller.cancel(payload["session_id"], payload["session_epoch"])

    def test_epoch_replacement_at_decision_commit_is_busy_then_retries_after_old_call_ends(
        self,
    ) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        old = request(request_id="epoch-old-commit", epoch=0)
        replacement = request(request_id="epoch-new-commit", epoch=1)
        reached, release = gate_first_commit(controller, "_commit_decision")
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_request(old)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(reached.wait(1))
        with self.assertRaises(ControllerFailure) as raised:
            controller.handle_request(replacement)
        self.assertEqual(str(raised.exception), "inflight_limit")
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcome.get("error"), ControllerFailure)
        self.assertEqual(str(outcome["error"]), "stale_session_epoch")
        self.assertNotIn("value", outcome)

        retried = controller.handle_request(replacement)
        self.assertEqual(retried["request_id"], replacement["request_id"])

    def test_cancel_winning_result_commit_does_not_adopt_state(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="cancel-before-result-commit")
        decision = controller.handle_request(source)
        result = result_for(source, decision["body"]["steps"][0])
        reached, release = gate_first_commit(controller, "_commit_result")
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_result(result)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(reached.wait(1))
        controller.cancel(source["session_id"], source["session_epoch"])
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcome.get("error"), ControllerFailure)
        self.assertEqual(str(outcome["error"]), "session_closed_or_cancelled")
        self.assertNotIn("value", outcome)
        trace = controller.export_trace(source["session_id"])
        self.assertFalse(
            any(
                row.get("message_type") == "result" or row.get("event_type") == "result"
                for row in trace["rows"]
            )
        )

    def test_result_publication_winning_cancel_preserves_duplicate_adoption(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="result-before-cancel")
        decision = controller.handle_request(source)
        result = result_for(source, decision["body"]["steps"][0])
        reached, release = gate_first_commit(controller, "_commit_result")
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_result(result)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(reached.wait(1))
        release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertNotIn("error", outcome)
        self.assertEqual(outcome["value"]["body"]["status"], "ACCEPTED")
        self.assertEqual(controller.handle_result(result)["body"]["status"], "DUPLICATE")
        controller.cancel(source["session_id"], source["session_epoch"])

    def test_cancelled_barrier_inference_cannot_publish(self) -> None:
        interpreter = BarrierInterpreter()
        controller = GoalController(interpreter=interpreter)
        payload = request(request_id="cancelled")
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_request(payload)
            except (
                ControllerFailure,
                BudgetExceeded,
            ) as exc:  # thread handoff for the assertion below
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(interpreter.started.wait(1))
        controller.cancel(payload["session_id"], payload["session_epoch"])
        interpreter.release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcome.get("error"), ControllerFailure)
        self.assertNotIn("value", outcome)

    def test_epoch_replacement_during_inference_is_busy_then_retries_after_old_call_ends(
        self,
    ) -> None:
        interpreter = BarrierInterpreter()
        controller = GoalController(interpreter=interpreter)
        old = request(request_id="epoch-old-during-inference", epoch=0)
        replacement = request(request_id="epoch-new-during-inference", epoch=1)
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_request(old)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(interpreter.started.wait(1))
        with self.assertRaises(ControllerFailure) as raised:
            controller.handle_request(replacement)
        self.assertEqual(str(raised.exception), "inflight_limit")
        self.assertEqual(interpreter.calls, 1)
        interpreter.release.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertIsInstance(outcome.get("error"), ControllerFailure)
        self.assertEqual(str(outcome["error"]), "stale_session_epoch")
        self.assertNotIn("value", outcome)

        retried = controller.handle_request(replacement)
        self.assertEqual(retried["request_id"], replacement["request_id"])
        self.assertEqual(interpreter.calls, 2)

    def test_episode_deadline_is_checked_after_inference(self) -> None:
        interpreter = BarrierInterpreter()
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 100,
            "max_intent_calls": 8,
            "max_action_attempts": 32,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=interpreter, budget=budget)
        payload = request(request_id="expired", budget=budget)
        outcome: dict[str, object] = {}

        def invoke() -> None:
            try:
                outcome["value"] = controller.handle_request(payload)
            except (ControllerFailure, BudgetExceeded) as exc:
                outcome["error"] = exc

        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(interpreter.started.wait(1))
        threading.Event().wait(0.15)
        interpreter.release.set()
        thread.join(2)
        self.assertIsInstance(outcome.get("error"), BudgetExceeded)
        self.assertEqual(str(outcome["error"]), "episode_deadline")

    def test_episode_expiry_rejects_result_without_state_adoption(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 100,
            "max_intent_calls": 8,
            "max_action_attempts": 32,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        source = request(request_id="result-after-expiry", budget=budget)
        decision = controller.handle_request(source)
        result = result_for(source, decision["body"]["steps"][0])
        threading.Event().wait(0.15)
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_result(result)
        self.assertEqual(str(raised.exception), "episode_deadline")

    def test_lower_incoming_budget_is_enforced_or_rejected_and_accounting_stays_null(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 1,
            "max_action_attempts": 32,
            "max_replans": 16,
            "max_plan_expansions": 32,
            "max_inflight_per_session": 1,
            "input_tokens": 123,
            "output_tokens": 456,
            "cost": 7.89,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        first = request(request_id="budget-one", budget=budget)
        response = controller.handle_request(first)
        self.assertEqual(response["budget"]["max_intent_calls"], 1)
        self.assertIsNone(response["budget"]["input_tokens"])
        self.assertIsNone(response["budget"]["output_tokens"])
        self.assertIsNone(response["budget"]["cost"])
        with self.assertRaises(BudgetExceeded):
            controller.handle_request(request(request_id="budget-two", budget=budget))

    def test_expired_cache_does_not_rerun_and_sessions_and_cache_stay_bounded(self) -> None:
        interpreter = IntentInterpreter(arm="R")
        retry_controller = GoalController(
            interpreter=interpreter, cache_ttl_seconds=0, session_ttl_seconds=60
        )
        first = request(request_id="expired-cache", session_id="bounded-0")
        retry_controller.handle_request(first)
        with self.assertRaises(ControllerFailure) as raised:
            retry_controller.handle_request(first)
        self.assertEqual(str(raised.exception), "duplicate_request_without_cached_response")

        controller = GoalController(
            interpreter=IntentInterpreter(arm="R"),
            cache_ttl_seconds=0,
            max_sessions=2,
            max_cache_entries=2,
            session_ttl_seconds=0,
        )
        for index in range(8):
            try:
                controller.handle_request(
                    request(request_id=f"bounded-{index}", session_id=f"bounded-{index}")
                )
            except (ProtocolError, ControllerFailure, BudgetExceeded):
                pass
        self.assertLessEqual(len(controller._sessions), 2)
        self.assertLessEqual(len(controller._cache), 2)

    def test_expired_session_reclaims_capacity_but_old_identity_cannot_reinfer(self) -> None:
        clock = [100.0]

        def monotonic() -> float:
            return clock[0]

        interpreter = CountingInterpreter()
        with patch("nesy_game.npc_goal.time.monotonic", side_effect=monotonic):
            controller = GoalController(
                interpreter=interpreter,
                cache_ttl_seconds=0,
                session_ttl_seconds=10,
                max_sessions=1,
            )
            old = request(request_id="old-expiring", session_id="old-session")
            controller.handle_request(old)
            self.assertEqual(interpreter.calls, 1)
            clock[0] += 11

            replacement = request(request_id="replacement", session_id="new-session")
            controller.handle_request(replacement)
            self.assertEqual(interpreter.calls, 2)

            retry = request(request_id="old-retry", session_id="old-session")
            with self.assertRaises(ControllerFailure) as raised:
                controller.handle_request(retry)
            self.assertEqual(str(raised.exception), "session_expired")
            self.assertEqual(interpreter.calls, 2)

    def test_replay_rejects_rehashed_plan_observation_and_sequence_semantic_tampering(self) -> None:
        source = request(request_id="replay-semantics")
        decision = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(source)
        cases = {}
        altered_plan = copy.deepcopy(decision)
        altered_plan["body"]["steps"][0]["operation"] = "install_lens"
        altered_plan["content_sha256"] = content_hash(altered_plan)
        cases["plan"] = [source, altered_plan]
        altered_observation = copy.deepcopy(source)
        altered_observation["body"]["observation"] = observation(goal_reached=True)
        altered_observation["content_sha256"] = content_hash(altered_observation)
        cases["observation"] = [altered_observation, decision]
        altered_sequence = copy.deepcopy(decision)
        altered_sequence["sequence"] = source["sequence"] + 2
        altered_sequence["delivery_index"] = source["delivery_index"] + 2
        altered_sequence["content_sha256"] = content_hash(altered_sequence)
        cases["sequence"] = [source, altered_sequence]
        for name, records in cases.items():
            with self.subTest(tamper=name):
                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(records, expected_session_id=source["session_id"])
                self.assertIn("replay", str(raised.exception))

    def test_replay_rejects_unmatched_request_wrong_operation_and_appended_step(self) -> None:
        source = request(request_id="replay-binding")
        decision = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(source)

        unmatched = copy.deepcopy(decision)
        unmatched["request_id"] = "unmatched-request"
        unmatched["body"]["steps"][0]["operation"] = "install_lens"
        unmatched["body"]["steps"][0]["arguments"] = {"object_id": "signal_lens"}
        unmatched["content_sha256"] = content_hash(unmatched)
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate([source, unmatched], expected_session_id=source["session_id"])
        self.assertEqual(str(raised.exception), "replay_decision_without_request")

        appended = copy.deepcopy(decision)
        appended["body"]["steps"].append(
            {
                "action_id": "action-appended",
                "operation": "reveal_hint",
                "execution_mode": "commit_world",
                "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
            }
        )
        appended["content_sha256"] = content_hash(appended)
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate([source, appended], expected_session_id=source["session_id"])
        self.assertEqual(str(raised.exception), "replay_plan_semantics_mismatch")

    def test_exported_redacted_trace_replays_semantically_and_tampering_fails(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="trace-replay", utterance="Please tell me the next clue.")
        controller.handle_request(source)
        trace = controller.export_trace(source["session_id"])
        self.assertIsInstance(trace, dict)
        self.assertNotIn(source["body"]["utterance"], json.dumps(trace, ensure_ascii=False))
        self.assertGreaterEqual(len(trace["rows"]), 2)
        self.assertEqual(
            ReplayValidator.validate(trace, expected_session_id=source["session_id"])["valid"], True
        )

        tampered_rows = copy.deepcopy(trace["rows"])
        decision_index, decision = next(
            (index, row)
            for index, row in enumerate(tampered_rows)
            if row.get("message_type") == "decision"
        )
        canonical = dict(decision)
        previous_hash = canonical.pop("previous_hash")
        canonical.pop("hash")
        canonical["body"]["steps"][0]["operation"] = "install_lens"
        canonical["body"]["steps"][0]["arguments"] = {"object_id": "signal_lens"}
        canonical["content_sha256"] = content_hash(canonical)
        canonical["previous_hash"] = previous_hash
        canonical["hash"] = sha256_json(
            {
                "record": {
                    key: value
                    for key, value in canonical.items()
                    if key not in {"previous_hash", "hash"}
                },
                "previous_hash": previous_hash,
            }
        )
        tampered_rows[decision_index] = canonical
        with self.assertRaises(ProtocolError):
            ReplayValidator.validate(tampered_rows, expected_session_id=source["session_id"])

    def test_ordinary_know_another_and_noise_are_not_refusals(self) -> None:
        interpreter = IntentInterpreter(arm="R")
        for utterance in ("What do you know?", "Tell me another clue.", "The noise is loud."):
            with self.subTest(utterance=utterance):
                result = interpreter.interpret(request_id="ordinary", utterance=utterance)
                self.assertNotEqual(result.typed_intent["label"], "REFUSE_HELP")


if __name__ == "__main__":
    unittest.main()
