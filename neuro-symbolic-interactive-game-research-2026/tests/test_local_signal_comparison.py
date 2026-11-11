"""Behavioral contracts for the offline signal comparison."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_local_signal_comparison as comparison

from nesy_game.contracts import ActionPolicy
from nesy_game.runtime import to_jsonable
from nesy_game.validator import validate_candidate


class LocalSignalComparisonTests(unittest.TestCase):
    def test_signals_are_derived_from_each_original_proposal(self):
        expected = {
            "missing_precondition": ("POLICY_PRECONDITION_OMISSION", "authorized"),
            "missing_effect": ("POLICY_EFFECT_OMISSION", "signal_restored"),
            "unauthorized_objective": ("POLICY_EFFECT_VIOLATION", "signal_restored"),
            "forbidden_disclosure": ("FORBIDDEN_DISCLOSURE", "secret"),
            "unsatisfied_dependency": ("UNSATISFIED_PRECONDITION", "permission"),
        }
        cases = comparison.fixtures()
        self.assertEqual({state.state_id for state, _ in cases}, set(expected))
        for state, candidate in cases:
            with self.subTest(case=state.state_id):
                row = comparison.run_case(state, candidate)
                actual = validate_candidate(state, candidate)
                self.assertFalse(actual.valid)
                self.assertEqual(row["detailed_signal"], to_jsonable(actual))
                self.assertEqual(
                    [
                        (error["code"], error["entity"])
                        for error in row["detailed_signal"]["errors"]
                    ],
                    [expected[state.state_id]],
                )
                self.assertEqual(row["shared_proposal"], to_jsonable(candidate))
                self.assertEqual(
                    row["generic_signal"], {"valid": False, "message": "Action rejected."}
                )
                for condition in row["conditions"].values():
                    self.assertEqual(condition["input_proposal"], to_jsonable(candidate))
                self.assertEqual(
                    row["conditions"]["deterministic_detailed"]["input_signal"], to_jsonable(actual)
                )
                self.assertEqual(
                    row["conditions"]["llm_detailed"]["input_signal"], to_jsonable(actual)
                )
                self.assertEqual(
                    row["conditions"]["llm_generic"]["input_signal"], row["generic_signal"]
                )

    def test_deterministic_repair_revalidates_and_commits_corrected_proposals(self):
        cases = {state.state_id: (state, candidate) for state, candidate in comparison.fixtures()}
        for case_id, field, value in (
            ("missing_precondition", "preconditions", ["authorized"]),
            ("missing_effect", "effects", ["signal_restored"]),
            ("unsatisfied_dependency", "preconditions", []),
        ):
            with self.subTest(case=case_id):
                state, candidate = cases[case_id]
                before = to_jsonable(state)
                first = comparison.run_case(state, candidate)
                self.assertEqual(first, comparison.run_case(state, candidate))
                result = first["conditions"]["deterministic_detailed"]
                self.assertEqual(result["final_candidate"][field], value)
                self.assertEqual(result["outcome"], "commit")
                self.assertIs(result["final_gate_accepted"], True)
                self.assertIs(result["objective_reached"], True)
                self.assertIn("signal_restored", result["final_facts"])
                self.assertEqual(to_jsonable(state), before)

    def test_gate_acceptance_does_not_imply_independent_objective(self):
        state, candidate = next(
            pair for pair in comparison.fixtures() if pair[0].state_id == "unauthorized_objective"
        )
        result = comparison.run_case(state, candidate)["conditions"]["deterministic_detailed"]
        self.assertEqual(result["outcome"], "commit")
        self.assertIs(result["final_gate_accepted"], True)
        self.assertIs(result["objective_reached"], False)
        self.assertNotIn("signal_restored", result["final_candidate"]["effects"])
        self.assertNotIn("signal_restored", result["final_facts"])

    def test_irreparable_disclosure_is_rejected_without_changing_state(self):
        state, candidate = next(
            pair for pair in comparison.fixtures() if pair[0].state_id == "forbidden_disclosure"
        )
        before = to_jsonable(state)
        result = comparison.run_case(state, candidate)["conditions"]["deterministic_detailed"]
        self.assertEqual(result["outcome"], "fallback")
        self.assertIs(result["final_gate_accepted"], False)
        self.assertIs(result["objective_reached"], False)
        self.assertEqual(result["final_facts"], sorted(state.facts))
        self.assertEqual(to_jsonable(state), before)

    def test_repair_is_rejected_when_restored_precondition_is_false(self):
        state, candidate = comparison.case(
            "new_invalid_after_repair",
            ActionPolicy(frozenset({"authorized"}), frozenset({"signal_restored"})),
            {"preconditions": frozenset(), "effects": frozenset({"signal_restored"})},
            facts={"existing"},
        )
        before = to_jsonable(state)
        row = comparison.run_case(state, candidate)
        result = row["conditions"]["deterministic_detailed"]
        self.assertEqual(
            row["detailed_signal"]["errors"][0]["code"], "POLICY_PRECONDITION_OMISSION"
        )
        self.assertEqual(result["final_candidate"]["preconditions"], ["authorized"])
        self.assertEqual(result["outcome"], "fallback")
        self.assertIs(result["final_gate_accepted"], False)
        self.assertIs(result["objective_reached"], False)
        self.assertEqual(result["final_facts"], ["existing"])
        self.assertEqual(to_jsonable(state), before)

    def test_trace_records_initial_failure_and_revalidation_after_repair(self):
        success = next(
            pair for pair in comparison.fixtures() if pair[0].state_id == "missing_precondition"
        )
        failure = comparison.case(
            "new_invalid_after_repair",
            ActionPolicy(frozenset({"authorized"}), frozenset({"signal_restored"})),
            {"preconditions": frozenset(), "effects": frozenset({"signal_restored"})},
            facts={"existing"},
        )
        for (state, candidate), final_valid, final_codes in (
            (success, True, []),
            (failure, False, ["UNSATISFIED_PRECONDITION"]),
        ):
            with self.subTest(case=state.state_id):
                row = comparison.run_case(state, candidate)
                result = row["conditions"]["deterministic_detailed"]
                self.assertEqual(result["repair_attempts"], 1)
                trace = result["trace"]
                self.assertEqual([step["attempt"] for step in trace], [0, 1])
                self.assertEqual(trace[0]["candidate"], to_jsonable(candidate))
                self.assertEqual(trace[0]["validation"], row["detailed_signal"])
                self.assertEqual(
                    [error["code"] for error in trace[0]["validation"]["errors"]],
                    ["POLICY_PRECONDITION_OMISSION"],
                )
                self.assertEqual(trace[1]["candidate"], result["final_candidate"])
                self.assertEqual(trace[1]["candidate"]["preconditions"], ["authorized"])
                self.assertEqual(trace[1]["validation"], result["final_validation"])
                self.assertIs(result["final_validation"]["valid"], final_valid)
                self.assertEqual(
                    [error["code"] for error in result["final_validation"]["errors"]], final_codes
                )
                self.assertIs(result["final_gate_accepted"], final_valid)

    def test_unrun_llm_conditions_have_no_observed_outcome(self):
        for state, candidate in comparison.fixtures():
            row = comparison.run_case(state, candidate)
            for name in ("llm_detailed", "llm_generic"):
                with self.subTest(case=state.state_id, condition=name):
                    result = row["conditions"][name]
                    self.assertEqual(result["status"], "NOT_RUN")
                    self.assertIsNone(result["outcome"])
                    self.assertIsNone(result["final_gate_accepted"])
                    self.assertIsNone(result["objective_reached"])

    def test_initially_valid_proposal_is_not_misreported_as_repair(self):
        state, candidate = comparison.case(
            "already_valid",
            ActionPolicy(frozenset(), frozenset({"signal_restored"})),
            {"preconditions": frozenset(), "effects": frozenset({"signal_restored"})},
        )
        with self.assertRaisesRegex(ValueError, "must begin with a rejected proposal"):
            comparison.run_case(state, candidate)
