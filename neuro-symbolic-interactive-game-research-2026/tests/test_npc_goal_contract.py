from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

P = Path(
    "/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026"
)
sys.path.insert(0, str(P / "src"))

from nesy_game.npc_goal import (
    BudgetExceeded,
    ControllerFailure,
    GoalController,
    IntentInterpreter,
    ProtocolError,
    ReplayValidator,
    content_hash,
    default_envelope,
    sha256_json,
    validate_envelope,
    verify_claims,
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
    value = {key: False for key in OBS_KEYS}
    value.update(overrides)
    return value


def request(
    *,
    utterance: str = "Where is the lens?",
    obs: dict[str, bool] | None = None,
    request_id: str = "request-1",
    epoch: int = 0,
    revision: int = 0,
) -> dict:
    return default_envelope(
        message_type="request",
        request_id=request_id,
        session_id="contract-session",
        session_epoch=epoch,
        state_ref={
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
        sequence=-1,
        delivery_index=-1,
    )


class NpcGoalContractTests(unittest.TestCase):
    def test_fixed_goal_and_observation_driven_plan_table(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        cases = (
            (
                "reachable_not_carried",
                observation(lens_reachable=True),
                "WAITING_PLAYER",
                "acquire_object",
            ),
            (
                "carried_requires_install",
                observation(lens_carried=True),
                "WAITING_PLAYER",
                "install_lens",
            ),
            (
                "restored_unauthorized_no_route",
                observation(lens_carried=True, signal_restored=True),
                "NO_ROUTE",
                None,
            ),
            (
                "restored_authorized_needs_dialogue",
                observation(lens_carried=True, signal_restored=True, tide_lead_authorized=True),
                "WAITING_DIALOGUE",
                "negotiate",
            ),
            (
                "restored_authorized_dialogue_reveals",
                observation(
                    lens_carried=True,
                    signal_restored=True,
                    tide_lead_authorized=True,
                    in_dialogue=True,
                ),
                "READY",
                "reveal_hint",
            ),
            (
                "unreachable_not_carried_no_route",
                observation(lens_reachable=False),
                "NO_ROUTE",
                None,
            ),
            (
                "goal_precedes_intent",
                observation(goal_reached=True, in_dialogue=True),
                "GOAL_REACHED",
                None,
            ),
        )
        for index, (name, obs, status, operation) in enumerate(cases):
            with self.subTest(case=name):
                response = controller.handle_request(
                    request(request_id=f"request-{index}", obs=obs)
                )
                body = response["body"]
                self.assertEqual(body["status"], status)
                self.assertEqual(
                    body["steps"][0]["operation"] if body["steps"] else None, operation
                )
                self.assertEqual(
                    response["goal_id"], "harbor-signal-restored-authorized-tide-lead-v1"
                )
                self.assertEqual(response["goal_version"], "1")
                self.assertEqual(response["policy_hash"], POLICY_HASH)

    def test_refusal_and_ambiguity_are_legal_clarify_without_goal_change(self) -> None:
        cases = ("No, leave me alone.", "Please help.")
        for index, utterance in enumerate(cases):
            with self.subTest(utterance=utterance):
                response = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(
                    request(
                        utterance=utterance,
                        obs=observation(
                            lens_carried=True,
                            signal_restored=True,
                            tide_lead_authorized=True,
                            in_dialogue=True,
                        ),
                        request_id=f"clarify-{index}",
                    )
                )
                self.assertEqual(response["body"]["status"], "WAITING_DIALOGUE")
                self.assertEqual(response["body"]["steps"][0]["operation"], "clarify")
                self.assertEqual(response["body"]["steps"][0]["execution_mode"], "dialogue")
                self.assertEqual(
                    response["goal_id"], "harbor-signal-restored-authorized-tide-lead-v1"
                )
                self.assertEqual(response["goal_version"], "1")

    def test_plan_expansion_budget_counts_public_search_nodes(self) -> None:
        budget = {
            "intent_deadline_ms": 30_000,
            "episode_deadline_ms": 900_000,
            "max_intent_calls": 1,
            "max_action_attempts": 32,
            "max_replans": 16,
            "max_plan_expansions": 2,
            "max_inflight_per_session": 1,
            "input_tokens": None,
            "output_tokens": None,
            "cost": None,
        }
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), budget=budget)
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_request(
                request(
                    request_id="expansion-budget", obs=observation(lens_reachable=True), epoch=0
                )
            )
        self.assertEqual(str(raised.exception), "max_plan_expansions")

    def test_replay_accepts_enabled_reveal_and_rejects_unsafe_reveal(self) -> None:
        authorized = observation(
            lens_carried=True, signal_restored=True, tide_lead_authorized=True, in_dialogue=True
        )
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(
            utterance="Tell me the clue.", obs=authorized, request_id="authorized-replay"
        )
        decision = controller.handle_request(source)
        records = [source, decision]
        before_structure = copy.deepcopy(records)
        before_bytes = json.dumps(
            records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        first = ReplayValidator.validate(records, expected_session_id=source["session_id"])
        self.assertTrue(first["valid"])
        self.assertEqual(records, before_structure)
        self.assertEqual(
            json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
            before_bytes,
        )
        second = ReplayValidator.validate(records, expected_session_id=source["session_id"])
        self.assertTrue(second["valid"])
        self.assertEqual(records, before_structure)
        self.assertEqual(
            json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            ),
            before_bytes,
        )
        self.assertEqual(decision["body"]["steps"][0]["operation"], "reveal_hint")

        unsafe_source = request(
            utterance="Tell me the clue.",
            obs=observation(
                lens_carried=True,
                signal_restored=True,
                tide_lead_authorized=False,
                in_dialogue=True,
            ),
            request_id="unsafe-replay",
        )
        unsafe_decision = controller.handle_request(unsafe_source)
        self.assertEqual(unsafe_decision["body"]["status"], "NO_ROUTE")
        unsafe_decision["body"]["status"] = "READY"
        unsafe_decision["body"]["steps"] = [
            {
                "action_id": "unsafe-reveal",
                "operation": "reveal_hint",
                "execution_mode": "commit_world",
                "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
            }
        ]
        unsafe_decision["content_sha256"] = content_hash(unsafe_decision)
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate(
                [unsafe_source, unsafe_decision], expected_session_id=unsafe_source["session_id"]
            )
        self.assertEqual(str(raised.exception), "replay_plan_semantics_mismatch")

    def test_claims_are_verified_against_public_observation_not_treated_as_facts(self) -> None:
        intent = {
            "label": "REPORT_FACT",
            "claims": [{"code": "SIGNAL_RESTORED", "state": "UNVERIFIED"}],
            "target": None,
        }
        checked = verify_claims(intent, observation(lens_carried=False, signal_restored=False))
        self.assertEqual(checked["claims"][0]["state"], "CONTRADICTED")
        self.assertEqual(checked["claims"][0]["code"], "SIGNAL_RESTORED")

    def test_codex_instruction_contains_public_utterance_only(self) -> None:
        seen: dict[str, str] = {}

        def runner(**kwargs):
            seen["instruction"] = kwargs["instruction"]
            return 0, {
                "request_id": kwargs["request_id"],
                "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
            }

        interpreter = IntentInterpreter(arm="P", prompt_runner=runner)
        result = interpreter.interpret(request_id="public-request", utterance="Can you help me?")
        self.assertEqual(result.typed_intent["label"], "ASK_INFORMATION")
        for forbidden in ("tide_marks_hint", "sealed_lighthouse", "canonical_state", "worldstate"):
            self.assertNotIn(forbidden, seen["instruction"])
        self.assertIn('"utterance":"Can you help me?"', seen["instruction"])

    def test_refusal_or_ambiguity_must_change_legal_plan_not_only_trace(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        base = observation(lens_reachable=True)
        ask = controller.handle_request(
            request(utterance="Where is the lens?", obs=base, request_id="ask")
        )
        refusal = controller.handle_request(
            request(utterance="No, leave me alone.", obs=base, request_id="refusal")
        )
        self.assertNotEqual(ask["body"]["steps"], refusal["body"]["steps"])
        self.assertEqual(refusal["body"]["status"], "WAITING_DIALOGUE")
        self.assertEqual(refusal["body"]["steps"][0]["operation"], "clarify")

    def test_same_request_is_deduplicated_without_new_action(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"), cache_ttl_seconds=60)
        first_request = request(request_id="same")
        first = controller.handle_request(first_request)
        second = controller.handle_request(first_request)
        self.assertEqual(first, second)
        self.assertEqual(first["body"]["steps"][0]["operation"], "acquire_object")

    def test_request_id_conflict_is_rejected(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        controller.handle_request(request(request_id="conflict", utterance="Where is the lens?"))
        with self.assertRaises(ProtocolError) as raised:
            controller.handle_request(request(request_id="conflict", utterance="Tell me the clue."))
        self.assertEqual(str(raised.exception), "request_id_conflict")

    def test_result_duplicate_has_no_second_action_attempt(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        decision = controller.handle_request(request(request_id="plan"))
        step = decision["body"]["steps"][0]
        returned_state_ref = {"revision": 1, "sha256": "1" * 64}
        result = default_envelope(
            message_type="result",
            session_id="contract-session",
            request_id="plan",
            state_ref=returned_state_ref,
            body={
                "action_id": step["action_id"],
                "operation": step["operation"],
                "status": "APPLIED",
                "engine_revision": returned_state_ref["revision"],
                "state_ref": returned_state_ref,
                "feedback": "applied",
                "observation": observation(lens_reachable=True),
            },
            policy_hash=POLICY_HASH,
        )
        accepted = controller.handle_result(result)
        duplicate = controller.handle_result(result)
        self.assertEqual(accepted["body"]["status"], "ACCEPTED")
        self.assertEqual(duplicate["body"]["status"], "DUPLICATE")

    def test_result_engine_revision_must_equal_returned_state_revision(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="revision-equality")
        decision = controller.handle_request(source)
        step = decision["body"]["steps"][0]
        result = default_envelope(
            message_type="result",
            session_id="contract-session",
            request_id="revision-equality",
            state_ref=source["state_ref"],
            body={
                "action_id": step["action_id"],
                "operation": step["operation"],
                "status": "APPLIED",
                "engine_revision": source["state_ref"]["revision"] + 1,
                "state_ref": source["state_ref"],
                "feedback": "applied",
                "observation": observation(lens_reachable=True),
            },
            policy_hash=POLICY_HASH,
        )
        rejected = controller.handle_result(result)
        self.assertEqual(rejected["body"]["status"], "REJECTED")
        self.assertEqual(rejected["body"]["error"], "contradictory_result")

    def test_call_budget_is_terminal_and_explicit(self) -> None:
        controller = GoalController(
            interpreter=IntentInterpreter(arm="R"),
            budget={
                "intent_deadline_ms": 30_000,
                "episode_deadline_ms": 900_000,
                "max_intent_calls": 1,
                "max_action_attempts": 32,
                "max_replans": 16,
                "max_plan_expansions": 32,
                "max_inflight_per_session": 1,
                "input_tokens": None,
                "output_tokens": None,
                "cost": None,
            },
        )
        controller.handle_request(request(request_id="budget-1"))
        with self.assertRaises(BudgetExceeded) as raised:
            controller.handle_request(request(request_id="budget-2"))
        self.assertEqual(str(raised.exception), "max_intent_calls")

    def test_trace_is_redacted_and_replay_tampering_is_rejected(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        controller.handle_request(
            request(utterance="Please tell me the next clue.", request_id="trace")
        )
        trace = controller.export_trace("contract-session")
        rows = trace["rows"]
        self.assertEqual(trace["session_id"], "contract-session")
        self.assertEqual(trace["session_epoch"], 0)
        self.assertEqual(trace["cursor"]["session_id"], "contract-session")
        self.assertEqual(trace["cursor"]["row_count"], len(rows))
        self.assertEqual(trace["cursor"]["head_hash"], rows[-1]["hash"])
        encoded = str(trace)
        self.assertNotIn("Please tell me the next clue.", encoded)
        self.assertNotIn("tide_marks_hint", encoded)
        self.assertTrue(all(len(row["hash"]) == 64 for row in rows))

        record = request(request_id="replay")
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate([record, record], expected_session_id="contract-session")
        self.assertEqual(str(raised.exception), "replay_order_violation")
        tampered = dict(record, content_sha256="0" * 64)
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate([tampered], expected_session_id="contract-session")
        self.assertEqual(str(raised.exception), "content_hash_mismatch")

    def test_p_arm_adapter_failure_is_explicit_not_rule_fallback(self) -> None:
        def failed_runner(**_kwargs):
            return 7, {"error": "timeout"}

        interpreter = IntentInterpreter(arm="P", prompt_runner=failed_runner)
        with self.assertRaises(ControllerFailure) as raised:
            interpreter.interpret(request_id="adapter-failure", utterance="Where is the lens?")
        self.assertEqual(str(raised.exception), "codex_interpretation_failed:timeout")

    def test_observation_event_accepts_null_transient_utterance(self) -> None:
        envelope = default_envelope(
            message_type="request",
            body={
                "event_kind": "observation",
                "utterance": None,
                "observation": observation(lens_reachable=True),
            },
            request_id="observation-event",
            arm="R",
            backend="rule",
        )
        validated = validate_envelope(envelope, expected_message_type="request")
        self.assertEqual(validated["body"]["event_kind"], "observation")
        self.assertIsNone(validated["body"]["utterance"])
        self.assertEqual(sha256_json({"b": 2, "a": 1}), sha256_json({"a": 1, "b": 2}))


if __name__ == "__main__":
    unittest.main()
