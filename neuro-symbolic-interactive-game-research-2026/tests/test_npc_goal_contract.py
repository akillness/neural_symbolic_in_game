from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

P = Path(__file__).resolve().parents[1]
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


def observation_request(
    *,
    request_id: str,
    obs: dict[str, bool] | None = None,
    revision: int = 0,
    epoch: int = 0,
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
            "event_kind": "observation",
            "utterance": None,
            "observation": obs or observation(lens_reachable=True),
        },
        arm="R",
        backend="rule",
        policy_hash=POLICY_HASH,
        sequence=-1,
        delivery_index=-1,
    )


def rehashed_records(records: list[dict], order: list[int]) -> list[dict]:
    """Re-sequence copied envelopes while preserving their semantic payloads."""
    resequenced: list[dict] = []
    for sequence, source_index in enumerate(order):
        candidate = copy.deepcopy(records[source_index])
        candidate["event_id"] = f"evt-replay-{sequence}-{source_index}"
        candidate["sequence"] = sequence
        candidate["delivery_index"] = sequence
        candidate["content_sha256"] = content_hash(candidate)
        resequenced.append(candidate)
    return resequenced


def applied_result(decision: dict, *, sequence: int = 1) -> dict:
    step = decision["body"]["steps"][0]
    state_ref = {"revision": 1, "sha256": hashlib.sha256(b"state-1").hexdigest()}
    return default_envelope(
        message_type="result",
        session_id=decision["session_id"],
        session_epoch=decision["session_epoch"],
        request_id=decision["request_id"],
        sequence=sequence,
        delivery_index=sequence,
        state_ref=state_ref,
        body={
            "action_id": step["action_id"],
            "operation": step["operation"],
            "status": "APPLIED",
            "engine_revision": state_ref["revision"],
            "state_ref": state_ref,
            "feedback": "applied",
            "observation": observation(lens_reachable=True),
        },
        policy_hash=decision["policy_hash"],
        arm="R",
        backend="rule",
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

    def test_replay_accepts_matching_request_and_decision_state_ref(self) -> None:
        source = request(
            utterance="Tell me the clue.",
            obs=observation(
                lens_carried=True,
                signal_restored=True,
                tide_lead_authorized=True,
                in_dialogue=True,
            ),
            request_id="matching-state-ref",
            revision=7,
        )
        decision = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(source)

        replay = ReplayValidator.validate(
            [source, decision], expected_session_id=source["session_id"]
        )

        self.assertTrue(replay["valid"])

    def test_replay_rejects_resigned_decision_state_ref_mismatch(self) -> None:
        source = request(
            utterance="Tell me the clue.",
            obs=observation(
                lens_carried=True,
                signal_restored=True,
                tide_lead_authorized=True,
                in_dialogue=True,
            ),
            request_id="mismatched-state-ref",
            revision=7,
        )
        decision = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(source)
        self.assertTrue(
            ReplayValidator.validate([source, decision], expected_session_id=source["session_id"])[
                "valid"
            ]
        )

        mismatches = (
            (
                "revision-differs",
                {
                    "revision": 8,
                    "sha256": hashlib.sha256(b"state-8").hexdigest(),
                },
            ),
            (
                "hash-differs",
                {
                    "revision": source["state_ref"]["revision"],
                    "sha256": "f" * 64,
                },
            ),
        )
        for case, state_ref in mismatches:
            with self.subTest(case=case):
                tampered = copy.deepcopy(decision)
                tampered["state_ref"] = state_ref
                tampered["content_sha256"] = content_hash(tampered)

                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(
                        [source, tampered], expected_session_id=source["session_id"]
                    )
                self.assertEqual(str(raised.exception), "replay_state_ref_mismatch")

    def test_replay_enforces_result_causality_and_single_application(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="replay-causality", obs=observation(lens_reachable=True))
        decision = controller.handle_request(source)
        result = applied_result(decision)

        valid = [source, decision, result]
        self.assertTrue(
            ReplayValidator.validate(valid, expected_session_id=source["session_id"])["valid"]
        )
        self.assertEqual([record["sequence"] for record in valid], [0, 1, 2])
        self.assertEqual([record["delivery_index"] for record in valid], [0, 1, 2])
        self.assertTrue(all(record["content_sha256"] == content_hash(record) for record in valid))
        self.assertEqual(result["body"]["status"], "APPLIED")

        invalid_histories = (
            (
                "duplicate-applied-result",
                rehashed_records([source, decision, result, result], [0, 1, 2, 3]),
                "replay_duplicate_result",
            ),
            (
                "result-before-decision",
                rehashed_records([source, decision, result], [0, 2, 1]),
                "replay_result_before_decision",
            ),
            (
                "decision-before-request",
                rehashed_records([source, decision, result], [1, 0, 2]),
                "replay_decision_before_request",
            ),
        )
        for case, records, expected_error in invalid_histories:
            with self.subTest(case=case):
                self.assertEqual(
                    [record["sequence"] for record in records], list(range(len(records)))
                )
                self.assertEqual(
                    [record["delivery_index"] for record in records], list(range(len(records)))
                )
                self.assertTrue(
                    all(record["content_sha256"] == content_hash(record) for record in records)
                )
                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(records, expected_session_id=source["session_id"])
                self.assertEqual(str(raised.exception), expected_error)

    def test_replay_mirrors_first_action_binding_across_shared_decisions(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source_a = request(request_id="binding-a", obs=observation(lens_reachable=True))
        decision_a = controller.handle_request(source_a)
        source_b = observation_request(request_id="binding-b")
        decision_b = controller.handle_request(source_b)
        self.assertEqual(
            decision_a["body"]["steps"][0]["action_id"],
            decision_b["body"]["steps"][0]["action_id"],
        )

        result_a = applied_result(decision_a)
        result_b = applied_result(decision_b)
        rejected_b = controller.handle_result(result_b)
        self.assertEqual(rejected_b["body"]["status"], "REJECTED")
        self.assertEqual(rejected_b["body"]["error"], "result_binding_mismatch")
        accepted_a = controller.handle_result(result_a)
        self.assertEqual(accepted_a["body"]["status"], "ACCEPTED")

        shared_records = rehashed_records(
            [source_a, decision_a, source_b, decision_b], [0, 1, 2, 3]
        )
        shared_result_a = rehashed_records(
            [source_a, decision_a, source_b, decision_b, result_a], [0, 1, 2, 3, 4]
        )
        shared_result_b = rehashed_records(
            [source_a, decision_a, source_b, decision_b, result_b], [0, 1, 2, 3, 4]
        )
        shared_duplicate_result_a = rehashed_records(
            [source_a, decision_a, source_b, decision_b, result_a, result_a],
            [0, 1, 2, 3, 4, 5],
        )
        for records in (
            shared_records,
            shared_result_a,
            shared_result_b,
            shared_duplicate_result_a,
        ):
            self.assertEqual([record["sequence"] for record in records], list(range(len(records))))
            self.assertEqual(
                [record["delivery_index"] for record in records], list(range(len(records)))
            )
            self.assertTrue(
                all(record["content_sha256"] == content_hash(record) for record in records)
            )

        self.assertTrue(
            ReplayValidator.validate(shared_records, expected_session_id=source_a["session_id"])[
                "valid"
            ]
        )
        self.assertTrue(
            ReplayValidator.validate(shared_result_a, expected_session_id=source_a["session_id"])[
                "valid"
            ]
        )
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate(shared_result_b, expected_session_id=source_a["session_id"])
        self.assertEqual(str(raised.exception), "replay_result_binding_mismatch")
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate(
                shared_duplicate_result_a, expected_session_id=source_a["session_id"]
            )
        self.assertEqual(str(raised.exception), "replay_duplicate_result")

        distinct_controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        distinct_source_a = request(request_id="distinct-a", obs=observation(lens_reachable=True))
        distinct_decision_a = distinct_controller.handle_request(distinct_source_a)
        distinct_source_b = request(request_id="distinct-b", obs=observation(lens_carried=True))
        distinct_decision_b = distinct_controller.handle_request(distinct_source_b)
        self.assertNotEqual(
            distinct_decision_a["body"]["steps"][0]["action_id"],
            distinct_decision_b["body"]["steps"][0]["action_id"],
        )
        distinct_result_b = applied_result(distinct_decision_b)
        distinct_records = rehashed_records(
            [
                distinct_source_a,
                distinct_decision_a,
                distinct_source_b,
                distinct_decision_b,
                distinct_result_b,
            ],
            [0, 1, 2, 3, 4],
        )
        self.assertTrue(
            ReplayValidator.validate(
                distinct_records, expected_session_id=distinct_source_a["session_id"]
            )["valid"]
        )

    def test_replay_rejects_result_after_state_lineage_advance(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source_a = request(request_id="lineage-a", revision=0)
        decision_a = controller.handle_request(source_a)
        source_b = request(request_id="lineage-b", revision=2)
        decision_b = controller.handle_request(source_b)
        result_a = applied_result(decision_a)

        live_rejected = controller.handle_result(result_a)
        self.assertEqual(live_rejected["body"]["status"], "REJECTED")
        self.assertEqual(live_rejected["body"]["error"], "state_revision_regression")

        records = rehashed_records(
            [source_a, decision_a, source_b, decision_b, result_a], [0, 1, 2, 3, 4]
        )
        self.assertEqual([record["sequence"] for record in records], [0, 1, 2, 3, 4])
        self.assertEqual([record["delivery_index"] for record in records], [0, 1, 2, 3, 4])
        self.assertTrue(all(record["content_sha256"] == content_hash(record) for record in records))
        with self.subTest(case="revision-advance"):
            with self.assertRaises(ProtocolError) as raised:
                ReplayValidator.validate(records, expected_session_id=source_a["session_id"])
            self.assertEqual(str(raised.exception), "replay_state_revision_regression")

        fork_controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        fork_source_a = request(request_id="fork-lineage-a", revision=0)
        fork_decision_a = fork_controller.handle_request(fork_source_a)
        fork_source_b = request(request_id="fork-lineage-b", revision=1)
        fork_source_b["state_ref"]["sha256"] = hashlib.sha256(b"fork-state-1").hexdigest()
        fork_source_b["content_sha256"] = content_hash(fork_source_b)
        fork_decision_b = fork_controller.handle_request(fork_source_b)
        fork_result_a = applied_result(fork_decision_a)

        fork_live_rejected = fork_controller.handle_result(fork_result_a)
        self.assertEqual(fork_live_rejected["body"]["status"], "REJECTED")
        self.assertEqual(fork_live_rejected["body"]["error"], "state_revision_regression")
        fork_records = rehashed_records(
            [
                fork_source_a,
                fork_decision_a,
                fork_source_b,
                fork_decision_b,
                fork_result_a,
            ],
            [0, 1, 2, 3, 4],
        )
        self.assertTrue(
            all(record["content_sha256"] == content_hash(record) for record in fork_records)
        )
        with self.subTest(case="same-revision-fork"):
            with self.assertRaises(ProtocolError) as raised:
                ReplayValidator.validate(
                    fork_records, expected_session_id=fork_source_a["session_id"]
                )
            self.assertEqual(str(raised.exception), "replay_state_revision_regression")

    def test_replay_rejects_regressing_or_forked_state_lineage_after_applied_result(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source_a = request(request_id="lineage-state-a", revision=0)
        decision_a = controller.handle_request(source_a)
        result_a = applied_result(decision_a)
        live_applied = controller.handle_result(result_a)
        self.assertEqual(result_a["body"]["status"], "APPLIED")
        self.assertEqual(live_applied["body"]["status"], "ACCEPTED")

        stale_source_b = request(request_id="lineage-state-b", revision=0)
        with self.assertRaises(ControllerFailure) as stale_live:
            controller.handle_request(stale_source_b)
        self.assertEqual(str(stale_live.exception), "stale_state_ref")
        stale_builder = GoalController(interpreter=IntentInterpreter(arm="R"))
        stale_decision_b = stale_builder.handle_request(stale_source_b)

        fork_source_b = request(request_id="lineage-fork-b", revision=1)
        fork_source_b["state_ref"]["sha256"] = hashlib.sha256(b"fork-state-1").hexdigest()
        fork_source_b["content_sha256"] = content_hash(fork_source_b)
        with self.assertRaises(ControllerFailure) as fork_live:
            controller.handle_request(fork_source_b)
        self.assertEqual(str(fork_live.exception), "forked_state_ref")
        fork_builder = GoalController(interpreter=IntentInterpreter(arm="R"))
        fork_decision_b = fork_builder.handle_request(fork_source_b)

        histories = {
            "request-only-stale": rehashed_records(
                [source_a, decision_a, result_a, stale_source_b], [0, 1, 2, 3]
            ),
            "stale-request-and-decision": rehashed_records(
                [source_a, decision_a, result_a, stale_source_b, stale_decision_b],
                [0, 1, 2, 3, 4],
            ),
            "same-revision-fork-request-and-decision": rehashed_records(
                [source_a, decision_a, result_a, fork_source_b, fork_decision_b],
                [0, 1, 2, 3, 4],
            ),
        }
        expected_sequences = {
            "request-only-stale": [0, 1, 2, 3],
            "stale-request-and-decision": [0, 1, 2, 3, 4],
            "same-revision-fork-request-and-decision": [0, 1, 2, 3, 4],
        }
        for case, records in histories.items():
            with self.subTest(case=case):
                self.assertEqual(
                    [record["sequence"] for record in records], expected_sequences[case]
                )
                self.assertEqual(
                    [record["delivery_index"] for record in records], expected_sequences[case]
                )
                self.assertTrue(
                    all(record["content_sha256"] == content_hash(record) for record in records)
                )
                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(records, expected_session_id=source_a["session_id"])
                self.assertEqual(str(raised.exception), "replay_state_revision_regression")

    def test_replay_preserves_observation_intent_and_snapshot_row_identity(self) -> None:
        base_observation = observation(lens_reachable=True)
        changed_observation = observation(lens_carried=True)
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="observation-seed", obs=base_observation)
        decision = controller.handle_request(source)
        observation_source = observation_request(
            request_id="observation-followup", obs=changed_observation
        )
        live_observation_decision = controller.handle_request(observation_source)
        prior_typed = decision["body"]["typed_intent"]
        live_typed = live_observation_decision["body"]["typed_intent"]
        self.assertEqual(
            live_observation_decision["body"]["intent_id"], decision["body"]["intent_id"]
        )
        self.assertEqual(live_typed["label"], prior_typed["label"])
        self.assertEqual(
            [claim["code"] for claim in live_typed["claims"]],
            [claim["code"] for claim in prior_typed["claims"]],
        )
        self.assertEqual(live_typed["target"], prior_typed["target"])
        positive_records = rehashed_records(
            [source, decision, observation_source, live_observation_decision], [0, 1, 2, 3]
        )
        self.assertTrue(
            ReplayValidator.validate(positive_records, expected_session_id=source["session_id"])[
                "valid"
            ]
        )

        orphan_seed = request(
            utterance="Where is the lens?", obs=base_observation, request_id="orphan-seed"
        )
        orphan_decision = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(
            orphan_seed
        )
        orphan_source = observation_request(request_id="orphan-observation", obs=base_observation)
        orphan_decision["request_id"] = orphan_source["request_id"]
        orphan_decision["event_id"] = "evt-orphan-observation"
        orphan_decision["provenance"]["raw_utterance_sha256"] = None
        orphan_decision["content_sha256"] = content_hash(orphan_decision)
        with self.assertRaises(ControllerFailure) as orphan_live:
            GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(orphan_source)
        self.assertEqual(str(orphan_live.exception), "observation_without_prior_intent")
        orphan_records = rehashed_records([orphan_source, orphan_decision], [0, 1])

        mismatch_seed = request(
            utterance="I have the lens.", obs=changed_observation, request_id="mismatch-seed"
        )
        mismatch_decision = GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(
            mismatch_seed
        )
        mismatch_decision["request_id"] = observation_source["request_id"]
        mismatch_decision["event_id"] = "evt-observation-mismatch"
        mismatch_decision["provenance"]["raw_utterance_sha256"] = None
        mismatch_decision["content_sha256"] = content_hash(mismatch_decision)
        self.assertNotEqual(
            mismatch_decision["body"]["intent_id"], live_observation_decision["body"]["intent_id"]
        )
        mismatch_records = rehashed_records(
            [source, decision, observation_source, mismatch_decision], [0, 1, 2, 3]
        )
        ordered_controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        ordered_source_a = request(request_id="ordered-seed", obs=base_observation)
        ordered_decision_a = ordered_controller.handle_request(ordered_source_a)
        ordered_source_b = observation_request(
            request_id="ordered-observation", obs=changed_observation
        )
        ordered_decision_b = ordered_controller.handle_request(ordered_source_b)
        with self.assertRaises(ControllerFailure) as ordered_live:
            GoalController(interpreter=IntentInterpreter(arm="R")).handle_request(ordered_source_b)
        self.assertEqual(str(ordered_live.exception), "observation_without_prior_intent")
        reordered_records = rehashed_records(
            [ordered_source_a, ordered_source_b, ordered_decision_a, ordered_decision_b],
            [0, 1, 2, 3],
        )

        for case, records, expected_error in (
            (
                "observation-before-prior-decision",
                reordered_records,
                "replay_observation_without_prior_intent",
            ),
            (
                "observation-without-prior-intent",
                orphan_records,
                "replay_observation_without_prior_intent",
            ),
            (
                "observation-intent-mismatch",
                mismatch_records,
                "replay_observation_intent_mismatch",
            ),
        ):
            with self.subTest(case=case):
                self.assertEqual(
                    [record["sequence"] for record in records], list(range(len(records)))
                )
                self.assertEqual(
                    [record["delivery_index"] for record in records], list(range(len(records)))
                )
                self.assertTrue(
                    all(record["content_sha256"] == content_hash(record) for record in records)
                )
                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(records, expected_session_id=source["session_id"])
                self.assertEqual(str(raised.exception), expected_error)

        snapshot_controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        snapshot_controller.handle_request(request(request_id="snapshot-positive"))
        snapshot = snapshot_controller.export_trace("contract-session")
        self.assertTrue(
            ReplayValidator.validate(snapshot, expected_session_id="contract-session")["valid"]
        )
        for case, wrapper_field, wrapper_value in (
            ("snapshot-session-id", "session_id", "other-session"),
            ("snapshot-session-epoch", "session_epoch", 1),
        ):
            with self.subTest(case=case):
                tampered_snapshot = copy.deepcopy(snapshot)
                tampered_snapshot[wrapper_field] = wrapper_value
                tampered_snapshot["cursor"] = {
                    "session_id": tampered_snapshot["session_id"],
                    "session_epoch": tampered_snapshot["session_epoch"],
                    "row_count": len(tampered_snapshot["rows"]),
                    "head_hash": tampered_snapshot["rows"][-1]["hash"],
                }
                tampered_snapshot["snapshot_id"] = sha256_json(
                    {
                        "session_id": tampered_snapshot["session_id"],
                        "session_epoch": tampered_snapshot["session_epoch"],
                        "rows": tampered_snapshot["rows"],
                    }
                )
                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(tampered_snapshot)
                self.assertEqual(str(raised.exception), "replay_snapshot_row_identity_mismatch")

    def test_replay_rejects_orphan_observation_and_request_records(self) -> None:
        orphan_observation = observation_request(
            request_id="orphan-epoch0-observation", obs=observation(lens_reachable=True)
        )
        orphan_epoch0 = rehashed_records([orphan_observation], [0])

        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="complete-utterance", obs=observation(lens_reachable=True))
        decision = controller.handle_request(source)
        valid_pair = rehashed_records([source, decision], [0, 1])
        self.assertTrue(
            ReplayValidator.validate(valid_pair, expected_session_id="contract-session")["valid"]
        )
        trailing_orphan_request = request(
            request_id="trailing-orphan-request", obs=observation(lens_carried=True)
        )
        orphan_request_history = rehashed_records(
            [source, decision, trailing_orphan_request], [0, 1, 2]
        )

        for case, records, expected_error in (
            (
                "request-only-epoch0-observation",
                orphan_epoch0,
                "replay_observation_without_prior_intent",
            ),
            (
                "trailing-request-without-decision",
                orphan_request_history,
                "replay_request_without_decision",
            ),
        ):
            with self.subTest(case=case):
                self.assertEqual(
                    [record["sequence"] for record in records], list(range(len(records)))
                )
                self.assertEqual(
                    [record["delivery_index"] for record in records], list(range(len(records)))
                )
                self.assertTrue(
                    all(record["content_sha256"] == content_hash(record) for record in records)
                )
                with self.assertRaises(ProtocolError) as raised:
                    ReplayValidator.validate(records, expected_session_id="contract-session")
                self.assertEqual(str(raised.exception), expected_error)

    def test_replay_accepts_epoch_local_observation_pair_as_opaque_continuation(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="epoch-seed", obs=observation(lens_reachable=True))
        decision = controller.handle_request(source)
        self.assertEqual(
            controller.handle_result(applied_result(decision))["body"]["status"], "ACCEPTED"
        )

        observation_source = observation_request(
            request_id="epoch-observation", obs=observation(lens_carried=True), revision=1, epoch=1
        )
        controller.handle_request(observation_source)
        snapshot = controller.export_trace(source["session_id"], session_epoch=1)
        self.assertEqual(snapshot["rows"][0]["body"]["event_kind"], "observation")
        self.assertEqual(snapshot["rows"][1]["message_type"], "decision")
        self.assertTrue(
            ReplayValidator.validate(snapshot, expected_session_id=source["session_id"])["valid"]
        )

    def test_replay_rejects_epoch_later_observation_intent_mismatch(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        source = request(request_id="epoch-seed-mismatch", obs=observation(lens_reachable=True))
        decision = controller.handle_request(source)
        self.assertEqual(
            controller.handle_result(applied_result(decision))["body"]["status"], "ACCEPTED"
        )
        observation_source = observation_request(
            request_id="epoch-observation-mismatch",
            obs=observation(lens_carried=True),
            revision=1,
            epoch=1,
        )
        controller.handle_request(observation_source)
        mismatch_source = observation_request(
            request_id="epoch-mismatch", obs=observation(signal_restored=True), revision=1, epoch=1
        )
        controller.handle_request(mismatch_source)
        mismatch_snapshot = controller.export_trace(source["session_id"], session_epoch=1)
        mismatch_snapshot["rows"][-1] = GoalController(
            interpreter=IntentInterpreter(arm="R")
        ).handle_request(
            request(
                utterance="Signal restored.",
                request_id="epoch-mismatch-seed",
                obs=observation(signal_restored=True),
                revision=1,
                epoch=1,
            )
        )
        mismatch_snapshot["rows"][-1]["request_id"] = mismatch_source["request_id"]
        mismatch_snapshot["rows"][-1]["event_id"] = "evt-epoch-observation-mismatch"
        mismatch_snapshot["rows"][-1]["provenance"]["raw_utterance_sha256"] = None
        mismatch_snapshot["rows"][-1]["sequence"] = 3
        mismatch_snapshot["rows"][-1]["delivery_index"] = 3
        mismatch_snapshot["rows"][-1]["content_sha256"] = content_hash(
            mismatch_snapshot["rows"][-1]
        )
        mismatch_snapshot["rows"][-1]["previous_hash"] = mismatch_snapshot["rows"][-2]["hash"]
        canonical_last = {
            key: value
            for key, value in mismatch_snapshot["rows"][-1].items()
            if key not in {"previous_hash", "hash"}
        }
        mismatch_snapshot["rows"][-1]["hash"] = sha256_json(
            {
                "record": canonical_last,
                "previous_hash": mismatch_snapshot["rows"][-1]["previous_hash"],
            }
        )
        mismatch_snapshot["snapshot_id"] = sha256_json(
            {
                "session_id": mismatch_snapshot["session_id"],
                "session_epoch": mismatch_snapshot["session_epoch"],
                "rows": mismatch_snapshot["rows"],
            }
        )
        mismatch_snapshot["cursor"] = {
            "session_id": mismatch_snapshot["session_id"],
            "session_epoch": mismatch_snapshot["session_epoch"],
            "row_count": len(mismatch_snapshot["rows"]),
            "head_hash": mismatch_snapshot["rows"][-1]["hash"],
        }
        mismatch_records = mismatch_snapshot
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate(mismatch_records, expected_session_id=source["session_id"])
        self.assertEqual(str(raised.exception), "replay_observation_intent_mismatch")

    def test_replay_rejects_epoch_observation_before_prior_intent(self) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        ordered_source = request(
            request_id="ordered-utterance", obs=observation(lens_reachable=True)
        )
        ordered_decision = controller.handle_request(ordered_source)
        ordered_observation = observation_request(
            request_id="ordered-observation", obs=observation(lens_carried=True)
        )
        ordered_observation_decision = controller.handle_request(ordered_observation)
        ordered_records = [
            ordered_source,
            ordered_observation,
            ordered_decision,
            ordered_observation_decision,
        ]
        for record in ordered_records:
            record["session_epoch"] = 1
        reordered_records = rehashed_records(ordered_records, [0, 1, 2, 3])
        with self.assertRaises(ProtocolError) as raised:
            ReplayValidator.validate(
                reordered_records, expected_session_id=ordered_source["session_id"]
            )
        self.assertEqual(str(raised.exception), "replay_observation_without_prior_intent")

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
