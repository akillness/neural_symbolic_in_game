"""Offline failure accounting for the equal-information feedback control."""

import copy
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_equal_information_feedback as comparison
import run_representation_consumers as serialization

from nesy_game.contracts import CandidateAction, TraceAttempt, ValidationResult, WorldState
from nesy_game.runtime import to_jsonable
from nesy_game.validator import validate_candidate

ARMS = ("detailed", "generic_with_details")
SECRET = "private-fault-marker"


class EqualInformationFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.split, self.state, self.candidate, _, _ = next(
            case for case in comparison.fixtures() if case[1].state_id == "missing_precondition"
        )
        self.validation = validate_candidate(self.state, self.candidate)

    def assert_failure_and_recovery(self, failed, error_type=None):
        """A failed assignment remains unknown and cannot abort the next case."""
        later_case = next(
            case for case in comparison.fixtures() if case[1].state_id == "missing_effect"
        )
        completed = comparison.run_case(*later_case)
        self.assertEqual(completed["case_id"], "missing_effect")
        summary = comparison.summarize([failed, completed])[self.split]
        encoded = json.dumps(
            {"cases": [failed, completed], "summary": summary},
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8", errors="strict")
        self.assertNotIn(SECRET.encode(), encoded)
        self.assertEqual(set(failed["conditions"]), set(ARMS))
        for name in ARMS:
            with self.subTest(arm=name):
                condition = failed["conditions"][name]
                self.assertEqual(condition["status"], "FAILED")
                self.assertEqual(condition["error"]["message"], "condition failed")
                if error_type is not None:
                    self.assertEqual(condition["error"]["type"], error_type)
                for field in (
                    "outcome",
                    "final_candidate",
                    "final_state",
                    "trace",
                    "objective_reached",
                    "safety_violation",
                    "false_refusal",
                ):
                    self.assertIsNone(condition[field])
                good = completed["conditions"][name]
                self.assertEqual(good["status"], "COMPLETED")
                self.assertEqual(good["outcome"], "commit")
                self.assertIs(good["objective_reached"], True)
                self.assertEqual(good["final_candidate"]["effects"], ["signal_restored"])
                self.assertEqual(
                    summary[name],
                    {
                        "assigned": 2,
                        "completed": 1,
                        "failed": 1,
                        "committed": 1,
                        "fallback": 0,
                        "objective_reached": 1,
                        "objective_unknown": 1,
                        "safety_unknown": 2,
                        "false_refusal_unknown": 2,
                    },
                )

    def test_validation_and_encoding_failures_keep_both_assignments(self):
        for source in ("validate_candidate", "encode_feedback"):
            with self.subTest(source=source):
                with patch.object(comparison, source, side_effect=RuntimeError(SECRET)):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed, "RuntimeError")

    def test_setup_serialization_failure_is_not_repeated_in_error_reporting(self):
        for field, owner, target in (
            ("state", serialization, self.state),
            ("proposal", serialization, self.candidate),
            ("feedback", comparison, self.validation),
        ):
            with self.subTest(field=field):
                original = owner.to_jsonable

                def failing(value, *, target=target, original=original):
                    if value is target:
                        raise RuntimeError(SECRET)
                    return original(value)

                with (
                    patch.object(comparison, "validate_candidate", return_value=self.validation),
                    patch.object(owner, "to_jsonable", side_effect=failing),
                ):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed, "RuntimeError")

    def test_condition_serialization_failures_are_sanitized_and_counted(self):
        original = serialization.to_jsonable
        targets = {
            "decoded_feedback": lambda value: (
                isinstance(value, ValidationResult) and value is not self.validation
            ),
            "final_candidate": lambda value: (
                isinstance(value, CandidateAction) and value is not self.candidate
            ),
            "final_state": lambda value: isinstance(value, WorldState) and value is not self.state,
            "trace": lambda value: (
                isinstance(value, tuple) and bool(value) and isinstance(value[0], TraceAttempt)
            ),
        }
        for field, matches in targets.items():
            with self.subTest(field=field):

                def failing(value, *, matches=matches):
                    if matches(value):
                        raise RuntimeError(SECRET)
                    return original(value)

                with (
                    patch.object(comparison, "validate_candidate", return_value=self.validation),
                    patch.object(serialization, "to_jsonable", side_effect=failing),
                ):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed, "RuntimeError")

    def test_non_json_condition_output_is_failed_before_report_serialization(self):
        original = serialization.to_jsonable
        for label, bad_value in (
            ("nan", float("nan")),
            ("positive_infinity", float("inf")),
            ("negative_infinity", float("-inf")),
            ("unsupported_object", object()),
            ("surrogate", "\ud800"),
        ):
            with self.subTest(value=label):

                def poisoned(value, *, bad_value=bad_value):
                    if isinstance(value, WorldState) and value is not self.state:
                        return {SECRET: bad_value}
                    return original(value)

                with patch.object(serialization, "to_jsonable", side_effect=poisoned):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed)

    def test_non_json_input_values_cannot_escape_as_completed_results(self):
        for label, value in (
            ("nan", float("nan")),
            ("positive_infinity", float("inf")),
            ("negative_infinity", float("-inf")),
            ("unsupported_object", object()),
        ):
            with self.subTest(value=label):
                candidate = replace(self.candidate, metadata={SECRET: [value]})
                failed = comparison.run_case(self.split, self.state, candidate)
                self.assert_failure_and_recovery(failed)

    def test_surrogate_inputs_do_not_poison_strict_utf8_report(self):
        for field in ("metadata_value", "metadata_key", "state_id"):
            with self.subTest(field=field):
                state, candidate = self.state, self.candidate
                if field == "metadata_value":
                    candidate = replace(candidate, metadata={SECRET: ["\ud800"]})
                elif field == "metadata_key":
                    candidate = replace(candidate, metadata={SECRET + "\udfff": "value"})
                else:
                    state = replace(state, state_id=SECRET + "\ud800")
                failed = comparison.run_case(self.split, state, candidate)
                self.assert_failure_and_recovery(failed, "UnicodeEncodeError")

    def test_unserializable_encoded_signals_fail_both_arms_before_consumption(self):
        for label, value in (
            ("nan", float("nan")),
            ("infinity", float("inf")),
            ("object", object()),
            ("surrogate", "\udfff"),
        ):
            with self.subTest(value=label):
                signals = comparison.encode_feedback(self.validation)
                signals["generic_with_details"][SECRET] = value
                with patch.object(comparison, "encode_feedback", return_value=signals):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed)

    def test_missing_arm_keys_cannot_shrink_the_assigned_denominator(self):
        for missing in ARMS:
            with self.subTest(missing=missing):
                signals = comparison.encode_feedback(self.validation)
                del signals[missing]
                with patch.object(comparison, "encode_feedback", return_value=signals):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed, "ValueError")

    def test_malformed_arm_containers_cannot_create_or_remove_assignments(self):
        extra_arm = comparison.encode_feedback(self.validation)
        extra_arm[SECRET] = {}
        for label, signals in (
            ("list_of_arm_names", list(ARMS)),
            ("tuple_of_arm_names", ARMS),
            ("null", None),
            ("unexpected_arm", extra_arm),
        ):
            with self.subTest(container=label):
                with patch.object(comparison, "encode_feedback", return_value=signals):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                self.assert_failure_and_recovery(failed, "ValueError")

    def test_condition_decode_failure_does_not_discard_healthy_sibling(self):
        signals = copy.deepcopy(comparison.encode_feedback(self.validation))
        signals["generic_with_details"]["details_json"] = SECRET
        with patch.object(comparison, "encode_feedback", return_value=signals):
            row = comparison.run_case(self.split, self.state, self.candidate)
        failed = row["conditions"]["generic_with_details"]
        self.assertEqual(failed["status"], "FAILED")
        self.assertEqual(
            failed["error"], {"type": "JSONDecodeError", "message": "condition failed"}
        )
        for field in ("objective_reached", "safety_violation", "false_refusal"):
            self.assertIsNone(failed[field])
        healthy = row["conditions"]["detailed"]
        self.assertEqual(healthy["outcome"], "commit")
        self.assertIs(healthy["objective_reached"], True)
        summary = comparison.summarize([row])[self.split]
        self.assertEqual(summary["detailed"]["completed"], 1)
        self.assertEqual(summary["generic_with_details"]["assigned"], 1)
        self.assertEqual(summary["generic_with_details"]["failed"], 1)
        self.assertEqual(summary["generic_with_details"]["objective_unknown"], 1)

    def test_healthy_equal_information_control_preserves_repair_and_rejection(self):
        expected = {
            "missing_precondition": ("commit", True),
            "forbidden_disclosure": ("fallback", False),
            "held_valid_goal": ("commit", True),
        }
        for case in comparison.fixtures():
            if case[1].state_id not in expected:
                continue
            with self.subTest(case=case[1].state_id):
                row = comparison.run_case(*case)
                detailed, generic = (row["conditions"][name] for name in ARMS)
                validation = validate_candidate(case[1], case[2])
                self.assertEqual(detailed["signal"], to_jsonable(validation))
                self.assertEqual(json.loads(generic["signal"]["details_json"]), detailed["signal"])
                for condition in (detailed, generic):
                    self.assertEqual(condition["status"], "COMPLETED")
                    self.assertEqual(condition["outcome"], expected[case[1].state_id][0])
                    self.assertIs(condition["objective_reached"], expected[case[1].state_id][1])
                    self.assertIsNone(condition["safety_violation"])
                    self.assertIsNone(condition["false_refusal"])
                    self.assertEqual(condition["decoded_signal"], to_jsonable(validation))
                for field in ("outcome", "final_candidate", "final_state", "trace"):
                    self.assertEqual(detailed[field], generic[field])
                if case[1].state_id == "missing_precondition":
                    self.assertEqual(detailed["final_candidate"]["preconditions"], ["authorized"])
                    self.assertIn("signal_restored", detailed["final_state"]["facts"])
                elif case[1].state_id == "forbidden_disclosure":
                    self.assertEqual(detailed["final_state"], to_jsonable(case[1]))
                    self.assertEqual(detailed["final_candidate"]["disclosed_facts"], ["secret"])
