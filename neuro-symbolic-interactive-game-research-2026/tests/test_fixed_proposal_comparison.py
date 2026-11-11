"""Behavioral contracts for the offline fixed-proposal comparison."""

import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_fixed_proposal_comparison as comparison
from run_local_signal_comparison import case, fixtures

from nesy_game.contracts import ActionPolicy
from nesy_game.runtime import to_jsonable


class FixedProposalComparisonTests(unittest.TestCase):
    def test_same_rejected_proposal_is_observed_without_repair_or_commit(self):
        for state, candidate in fixtures():
            with self.subTest(case=state.state_id):
                before = to_jsonable(state)
                proposal = to_jsonable(candidate)
                row = comparison.run_case(state, candidate)
                control = row["conditions"]["proposal_only"]
                gate = row["conditions"]["trace_gate"]
                self.assertEqual(row["shared_proposal"], proposal)
                self.assertEqual(gate["trace"][0]["candidate"], proposal)
                self.assertEqual(len(gate["trace"]), 1)
                self.assertEqual(control["outcome"], "not_executed")
                self.assertEqual(control["final_state"], before)
                self.assertEqual(gate["outcome"], "fallback")
                self.assertFalse(gate["validation"]["valid"])
                self.assertEqual(gate["final_state"], before)
                self.assertEqual(to_jsonable(state), before)

    def test_valid_proposal_commits_only_in_gate_without_claiming_objective(self):
        state, candidate = case(
            "valid",
            ActionPolicy(frozenset(), frozenset({"signal_restored"})),
            {"preconditions": frozenset(), "effects": frozenset({"signal_restored"})},
        )
        before = to_jsonable(state)
        row = comparison.run_case(state, candidate)
        gate = row["conditions"]["trace_gate"]
        self.assertEqual(row["conditions"]["proposal_only"]["final_state"], before)
        self.assertEqual(gate["trace"][0]["candidate"], row["shared_proposal"])
        self.assertEqual(gate["outcome"], "commit")
        self.assertTrue(gate["validation"]["valid"])
        self.assertIn("signal_restored", gate["final_state"]["facts"])
        self.assertEqual(to_jsonable(state), before)
        self.assertEqual(row["oracle_status"], "NOT_AVAILABLE")
        for result in row["conditions"].values():
            self.assertIsNone(result["objective_reached"])

    def test_unimplemented_condition_and_real_gate_failure_remain_in_denominator(self):
        state, candidate = fixtures()[0]
        valid_state, valid_candidate = case(
            "encoding_failure",
            ActionPolicy(frozenset(), frozenset({"signal_restored"})),
            {"preconditions": frozenset(), "effects": frozenset({"signal_restored"})},
        )
        malformed = replace(valid_candidate, action_id="\ud800")
        failed = comparison.run_case(valid_state, malformed)
        gate = failed["conditions"]["trace_gate"]
        self.assertEqual(gate["status"], "FAILED")
        self.assertEqual(gate["error"]["type"], "UnicodeEncodeError")
        self.assertIn("surrogates not allowed", gate["error"]["message"])
        self.assertIsNone(gate["outcome"])
        self.assertIsNone(gate["final_state"])
        rules = failed["conditions"]["generic_rules"]
        self.assertEqual(rules["status"], "NOT_IMPLEMENTED")
        self.assertIsNone(rules["outcome"])
        self.assertIsNone(rules["final_state"])
        summary = comparison.summarize([comparison.run_case(state, candidate), failed])
        self.assertEqual(
            summary["conditions"]["trace_gate"],
            {
                "assigned": 2,
                "completed": 1,
                "failed": 1,
                "not_implemented": 0,
                "missing": 0,
            },
        )
        self.assertEqual(
            summary["conditions"]["generic_rules"],
            {
                "assigned": 2,
                "completed": 0,
                "failed": 0,
                "not_implemented": 2,
                "missing": 0,
            },
        )
        self.assertEqual(summary["oracle"], {"assigned": 2, "adjudicated": 0, "missing": 2})
