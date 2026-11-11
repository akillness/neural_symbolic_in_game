"""Offline behavioral checks for lossless feedback consumers."""

import copy
import io
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_representation_consumers as comparison

from nesy_game.runtime import to_jsonable
from nesy_game.validator import validate_candidate


class RepresentationConsumerTests(unittest.TestCase):
    def setUp(self):
        self.split, self.state, self.candidate, _, _ = comparison.fixtures()[0]
        self.validation = validate_candidate(self.state, self.candidate)
        self.signals = comparison.encode_signals(self.validation)

    def test_full_feedback_roundtrips_with_unicode_and_escaped_lines(self):
        feedback = {
            "valid": False,
            "checks_run": ["한글\ncheck"],
            "errors": [
                {
                    "code": "x",
                    "entity": "a\nb",
                    "reason": 'quote " and newline\n끝',
                    "repair_hint": "tab\tvalue",
                }
            ],
        }
        for name, signal in comparison.encode_signals(feedback).items():
            with self.subTest(name=name):
                self.assertEqual(comparison.information(name, signal), feedback)

    def test_unicode_line_separators_survive_roundtrip_and_consumption(self):
        feedback = to_jsonable(self.validation)
        feedback["errors"][0]["reason"] = "next\u0085line\u2028paragraph\u2029end"
        for name, signal in comparison.encode_signals(feedback).items():
            with self.subTest(name=name):
                self.assertEqual(comparison.information(name, signal), feedback)
                repaired = comparison.consume(name, signal, self.candidate)
                self.assertIn("authorized", repaired.preconditions)

    def test_each_consumer_reads_its_assigned_signal(self):
        feedback = to_jsonable(self.validation)
        self.assertEqual(feedback["errors"][0]["code"], "POLICY_PRECONDITION_OMISSION")
        changed = copy.deepcopy(feedback)
        changed["errors"][0]["entity"] = "different_requirement"
        changed_signals = comparison.encode_signals(changed)
        for name in ("structured", "text"):
            with self.subTest(name=name):
                original = comparison.consume(name, self.signals[name], self.candidate)
                altered = comparison.consume(name, changed_signals[name], self.candidate)
                self.assertIn("authorized", original.preconditions)
                self.assertIn("different_requirement", altered.preconditions)
                self.assertNotIn("authorized", altered.preconditions)
                self.assertEqual(self.candidate.preconditions, frozenset())

    def test_run_records_one_consumed_signal_and_revalidated_outcome(self):
        row = comparison.run_case(self.split, self.state, self.candidate)
        for name, condition in row["conditions"].items():
            with self.subTest(name=name):
                self.assertEqual(condition["status"], "COMPLETED")
                self.assertEqual(
                    comparison.information(name, condition["signal"]), row["original_feedback"]
                )
                self.assertEqual(len(condition["consumer_calls"]), 1)
                self.assertEqual(condition["consumer_calls"][0]["input"], condition["signal"])
                self.assertEqual(
                    condition["consumer_calls"][0]["candidate_before"], row["input_proposal"]
                )
                self.assertEqual(condition["outcome"], "commit")
                self.assertTrue(condition["objective_reached"])
                self.assertIsNone(condition["safety_violation"])
                self.assertIsNone(condition["false_refusal"])

    def test_tampering_is_rejected_before_consumer_and_counted(self):
        signals = copy.deepcopy(self.signals)
        signals["text"] = signals["text"].replace("authorized", "tampered")
        with patch.object(comparison, "encode_signals", return_value=signals):
            row = comparison.run_case(self.split, self.state, self.candidate)
        self.assertEqual(row["conditions"]["structured"]["status"], "COMPLETED")
        failed = row["conditions"]["text"]
        self.assertEqual(failed["status"], "FAILED")
        self.assertIs(failed["information_equal"], False)
        self.assertEqual(failed["consumer_calls"], [])
        self.assertIsNone(failed["objective_reached"])
        self.assertEqual(failed["error"], {"type": "ValueError", "message": "condition failed"})
        summary = comparison.summarize([row])[self.split]["text"]
        self.assertEqual((summary["assigned"], summary["completed"], summary["failed"]), (1, 0, 1))
        self.assertEqual((summary["objective_unknown"], summary["safety_unknown"]), (1, 1))

    def test_consumer_error_is_not_dropped_from_denominator(self):
        original = comparison.consume

        def failing(name, signal, candidate):
            if name == "text":
                raise RuntimeError("parser failure")
            return original(name, signal, candidate)

        with patch.object(comparison, "consume", side_effect=failing):
            row = comparison.run_case(self.split, self.state, self.candidate)
        self.assertEqual(row["conditions"]["text"]["error"]["type"], "RuntimeError")
        self.assertEqual(row["conditions"]["text"]["error"]["message"], "condition failed")
        self.assertNotIn("parser failure", str(row["conditions"]["text"]["error"]))
        failed = row["conditions"]["text"]
        self.assertEqual(failed["status"], "FAILED")
        self.assertIs(failed["information_equal"], True)
        self.assertEqual(len(failed["consumer_calls"]), 1)
        call = failed["consumer_calls"][0]
        self.assertEqual(call["attempt"], 1)
        self.assertEqual(call["input"], failed["signal"])
        self.assertEqual(call["candidate_before"], row["input_proposal"])
        self.assertIsNone(call["candidate_after"])
        summary = comparison.summarize([row])[self.split]
        self.assertEqual((summary["text"]["assigned"], summary["text"]["failed"]), (1, 1))
        self.assertEqual(summary["text"]["objective_unknown"], 1)
        self.assertEqual(summary["text"]["false_refusal_unknown"], 1)
        self.assertEqual(summary["structured"]["completed"], 1)

    def test_setup_failures_preserve_both_assignments_and_later_cases(self):
        for source in ("validate_candidate", "encode_signals"):
            with self.subTest(source=source):
                with patch.object(
                    comparison, source, side_effect=RuntimeError("secret setup marker")
                ):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                completed = comparison.run_case(self.split, self.state, self.candidate)
                summary = comparison.summarize([failed, completed])[self.split]
                for name in ("structured", "text"):
                    condition = failed["conditions"][name]
                    self.assertEqual(condition["status"], "FAILED")
                    self.assertEqual(
                        condition["error"], {"type": "RuntimeError", "message": "condition failed"}
                    )
                    self.assertNotIn("secret setup marker", str(condition["error"]))
                    self.assertEqual(condition["consumer_calls"], [])
                    self.assertIsNone(condition["objective_reached"])
                    self.assertEqual(completed["conditions"][name]["status"], "COMPLETED")
                    counts = summary[name]
                    self.assertEqual(
                        (counts["assigned"], counts["completed"], counts["failed"]), (2, 1, 1)
                    )
                    self.assertEqual(counts["objective_unknown"], 1)
                    self.assertEqual(counts["safety_unknown"], 2)
                    self.assertEqual(counts["false_refusal_unknown"], 2)

    def test_input_serialization_failure_preserves_assignments_and_later_case(self):
        original = comparison.to_jsonable
        for field, target in (("input_state", self.state), ("input_proposal", self.candidate)):
            with self.subTest(field=field):

                def failing(value, *, target=target):
                    if value is target:
                        raise RuntimeError("private serialization details")
                    return original(value)

                with patch.object(comparison, "to_jsonable", side_effect=failing):
                    failed = comparison.run_case(self.split, self.state, self.candidate)
                completed = comparison.run_case(self.split, self.state, self.candidate)
                self.assertIsNone(failed[field])
                self.assertIsNotNone(
                    failed["input_proposal" if field == "input_state" else "input_state"]
                )
                summary = comparison.summarize([failed, completed])[self.split]
                for name in ("structured", "text"):
                    condition = failed["conditions"][name]
                    self.assertEqual(condition["status"], "FAILED")
                    self.assertEqual(condition["error"]["type"], "RuntimeError")
                    self.assertNotIn("private serialization details", condition["error"]["message"])
                    self.assertEqual(condition["consumer_calls"], [])
                    self.assertIsNone(condition["objective_reached"])
                    self.assertIsNone(condition["safety_violation"])
                    self.assertIsNone(condition["false_refusal"])
                    self.assertEqual(completed["conditions"][name]["status"], "COMPLETED")
                    counts = summary[name]
                    self.assertEqual(
                        (counts["assigned"], counts["completed"], counts["failed"]), (2, 1, 1)
                    )
                    self.assertEqual(
                        (
                            counts["objective_unknown"],
                            counts["safety_unknown"],
                            counts["false_refusal_unknown"],
                        ),
                        (1, 2, 2),
                    )

    def test_non_json_candidate_preserves_assignments_and_strict_output(self):
        for bad_value in (float("nan"), float("inf"), float("-inf"), object()):
            with self.subTest(value=repr(bad_value)):
                candidate = replace(self.candidate, metadata={"private-marker": [bad_value]})
                failed = comparison.run_case(self.split, self.state, candidate)
                completed = comparison.run_case(self.split, self.state, self.candidate)
                summary = comparison.summarize([failed, completed])[self.split]
                self.assertIsNone(failed["input_proposal"])
                encoded = json.dumps([failed, completed, summary], allow_nan=False)
                self.assertNotIn("private-marker", encoded)
                for name in ("structured", "text"):
                    condition = failed["conditions"][name]
                    self.assertEqual(condition["status"], "FAILED")
                    self.assertIsNone(condition["information_equal"])
                    self.assertEqual(condition["consumer_calls"], [])
                    for metric in ("objective_reached", "safety_violation", "false_refusal"):
                        self.assertIsNone(condition[metric])
                    self.assertEqual(completed["conditions"][name]["status"], "COMPLETED")
                    counts = summary[name]
                    self.assertEqual(
                        (counts["assigned"], counts["completed"], counts["failed"]), (2, 1, 1)
                    )
                    self.assertEqual(
                        (
                            counts["objective_unknown"],
                            counts["safety_unknown"],
                            counts["false_refusal_unknown"],
                        ),
                        (1, 2, 2),
                    )

    def test_surrogate_inputs_fail_closed_in_strict_utf8_output(self):
        marker = "private-surrogate-marker"
        valid_candidate = replace(self.candidate, metadata={"unicode": "한글\u2028next\u2029end"})
        for field in ("metadata_value", "metadata_key", "state_id"):
            with self.subTest(field=field):
                bad_state = self.state
                bad_candidate = self.candidate
                if field == "metadata_value":
                    bad_candidate = replace(self.candidate, metadata={marker: ["\ud800"]})
                elif field == "metadata_key":
                    bad_candidate = replace(self.candidate, metadata={marker + "\udfff": "value"})
                else:
                    bad_state = replace(self.state, state_id=marker + "\ud800")
                cases = [
                    (self.split, bad_state, bad_candidate, None, None),
                    (self.split, self.state, valid_candidate, None, None),
                ]
                buffer = io.BytesIO()
                output = io.TextIOWrapper(buffer, encoding="utf-8", errors="strict")
                with (
                    patch.object(comparison, "fixtures", return_value=cases),
                    patch.object(sys, "stdout", output),
                ):
                    comparison.main()
                    output.flush()
                text = buffer.getvalue().decode("utf-8", errors="strict")
                self.assertNotIn(marker, text)
                self.assertNotIn("surrogates not allowed", text)
                report = json.loads(text)
                failed, completed = report["cases"]
                self.assertEqual(
                    completed["input_proposal"]["metadata"]["unicode"], "한글\u2028next\u2029end"
                )
                for name in ("structured", "text"):
                    condition = failed["conditions"][name]
                    self.assertEqual(condition["status"], "FAILED")
                    self.assertEqual(condition["error"]["message"], "condition failed")
                    self.assertEqual(condition["consumer_calls"], [])
                    for metric in ("objective_reached", "safety_violation", "false_refusal"):
                        self.assertIsNone(condition[metric])
                    self.assertEqual(completed["conditions"][name]["status"], "COMPLETED")
                    counts = report["summary"][self.split][name]
                    self.assertEqual(
                        (counts["assigned"], counts["completed"], counts["failed"]), (2, 1, 1)
                    )
                    self.assertEqual(
                        (
                            counts["objective_unknown"],
                            counts["safety_unknown"],
                            counts["false_refusal_unknown"],
                        ),
                        (1, 2, 2),
                    )

    def test_feedback_serialization_failure_preserves_assignments(self):
        original = comparison.to_jsonable

        def failing(value):
            if value is self.validation:
                raise RuntimeError("feedback serialization failed")
            return original(value)

        with (
            patch.object(comparison, "validate_candidate", return_value=self.validation),
            patch.object(comparison, "to_jsonable", side_effect=failing),
        ):
            failed = comparison.run_case(self.split, self.state, self.candidate)
        completed = comparison.run_case(self.split, self.state, self.candidate)
        summary = comparison.summarize([failed, completed])[self.split]
        for name in ("structured", "text"):
            condition = failed["conditions"][name]
            self.assertEqual(condition["status"], "FAILED")
            self.assertEqual(condition["error"]["type"], "RuntimeError")
            self.assertEqual(condition["consumer_calls"], [])
            self.assertIsNone(condition["objective_reached"])
            self.assertIsNone(condition["safety_violation"])
            self.assertIsNone(condition["false_refusal"])
            self.assertEqual(completed["conditions"][name]["status"], "COMPLETED")
            counts = summary[name]
            self.assertEqual((counts["assigned"], counts["completed"], counts["failed"]), (2, 1, 1))
            self.assertEqual(
                (
                    counts["objective_unknown"],
                    counts["safety_unknown"],
                    counts["false_refusal_unknown"],
                ),
                (1, 2, 2),
            )

    def test_malformed_representations_fail_validation(self):
        for name, signal in (
            ("text", "valid false\nchecks []\nerror {"),
            ("text", "checks []\nvalid false"),
            ("structured", {"valid": False, "checks_run": [], "errors": [{}]}),
        ):
            with self.subTest(name=name, signal=signal), self.assertRaises(ValueError):
                comparison.information(name, signal)

    def test_already_valid_candidate_does_not_consume_feedback(self):
        case = next(case for case in comparison.fixtures() if case[1].state_id == "held_valid_goal")
        row = comparison.run_case(*case)
        for condition in row["conditions"].values():
            self.assertEqual(condition["status"], "COMPLETED")
            self.assertEqual(condition["consumer_calls"], [])
            self.assertEqual(condition["outcome"], "commit")


if __name__ == "__main__":
    unittest.main()
