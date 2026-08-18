"""Contract tests for the soft-proposal disclosure gate."""

import copy
import json
import unittest
from pathlib import Path

from scripts import soft_proposal_policy as policy

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SoftProposalPolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scenario = policy.load_scenario(policy.DEFAULT_SCENARIO)
        self.state = copy.deepcopy(policy.initial_state(self.scenario))

    def test_projection_never_exposes_a_permanently_forbidden_fact(self) -> None:
        projection = policy.model_visible_projection(self.state, self.scenario)
        for fact_id in self.scenario["disclosure_policy"]["permanently_forbidden"]:
            self.assertNotIn(fact_id, projection["known_facts"])
            self.assertNotIn(fact_id, projection["disclosable_now"])

    def test_projection_withholds_a_stage_gated_fact_until_its_stage(self) -> None:
        gate = self.scenario["disclosure_policy"]["stage_gates"][0]
        self.assertLess(int(self.state["quest"]["stage"]), int(gate["minimum_stage"]))
        self.assertNotIn(
            gate["fact_id"],
            policy.model_visible_projection(self.state, self.scenario)["disclosable_now"],
        )
        self.state["quest"]["stage"] = int(gate["minimum_stage"])
        self.assertIn(
            gate["fact_id"],
            policy.model_visible_projection(self.state, self.scenario)["disclosable_now"],
        )

    def test_screen_flags_a_sealed_fact(self) -> None:
        sealed = self.scenario["disclosure_policy"]["permanently_forbidden"][0]
        verdict = policy.screen_response(
            f"미라가 {sealed} 이야기를 꺼낸다.", self.state, self.scenario
        )
        self.assertFalse(verdict["clean"])
        self.assertIn(policy.FORBIDDEN_DISCLOSURE, verdict["violation_codes"])
        self.assertIn(sealed, verdict["matched_facts"])

    def test_screen_flags_a_stage_gated_fact_before_its_stage(self) -> None:
        gate = self.scenario["disclosure_policy"]["stage_gates"][0]
        verdict = policy.screen_response(
            f"{gate['fact_id']} 를 알려주지.", self.state, self.scenario
        )
        self.assertFalse(verdict["clean"])
        self.assertIn(policy.STAGE_GATED_DISCLOSURE, verdict["violation_codes"])

    def test_screen_allows_a_stage_gated_fact_once_the_stage_is_reached(self) -> None:
        gate = self.scenario["disclosure_policy"]["stage_gates"][0]
        self.state["quest"]["stage"] = int(gate["minimum_stage"])
        verdict = policy.screen_response(
            f"{gate['fact_id']} 를 알려주지.", self.state, self.scenario
        )
        self.assertTrue(verdict["clean"])

    def test_screen_allows_an_already_public_fact(self) -> None:
        public = self.state["facts"][0]
        self.assertTrue(
            policy.screen_response(f"{public} 는 모두 아는 일이다.", self.state, self.scenario)[
                "clean"
            ]
        )

    def test_screen_declares_that_a_semantic_oracle_is_still_required(self) -> None:
        verdict = policy.screen_response("바람이 심하군.", self.state, self.scenario)
        self.assertTrue(verdict["clean"])
        self.assertTrue(verdict["semantic_oracle_required"])
        self.assertEqual(verdict["screen"], "lexical-identifier-screen")

    def test_declared_surface_terms_extend_the_screen(self) -> None:
        scenario = copy.deepcopy(self.scenario)
        sealed = scenario["disclosure_policy"]["permanently_forbidden"][0]
        scenario["disclosure_surface_terms"] = {sealed: ["등대지기가 배신했다"]}
        verdict = policy.screen_response("등대지기가 배신했다는 소문이 돈다.", self.state, scenario)
        self.assertFalse(verdict["clean"])
        self.assertIn(sealed, verdict["matched_facts"])

    def test_cli_screens_a_proposal_file(self) -> None:
        sealed = self.scenario["disclosure_policy"]["permanently_forbidden"][0]
        proposal = PROJECT_ROOT / "tests" / "_tmp_soft_proposal.json"
        proposal.write_text(json.dumps({"response": f"{sealed}"}), encoding="utf-8")
        try:
            self.assertEqual(policy.main(["--proposal", str(proposal)]), 1)
        finally:
            proposal.unlink()


if __name__ == "__main__":
    unittest.main()
