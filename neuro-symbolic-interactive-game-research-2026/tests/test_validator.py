import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from nesy_game import ActionPolicy, CandidateAction, WorldState, validate_candidate


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = WorldState(
            state_id="s0",
            locations=frozenset({"dock", "lighthouse"}),
            reachable_locations=frozenset({"dock"}),
            object_locations={"rusted_key": "lighthouse"},
            inventory=frozenset(),
            facts=frozenset({"player_saved_dock"}),
            action_policies={
                "NPC_REPLY": ActionPolicy(frozenset({"player_saved_dock"}), frozenset()),
                "UNLOCK_AND_REVEAL": ActionPolicy(
                    frozenset({"player_has_map"}),
                    frozenset({"lighthouse_unlocked"}),
                    frozenset({"lighthouse_unlocked"}),
                ),
            },
            npc_knowledge={"captain_mira": frozenset({"player_saved_dock"})},
            forbidden_disclosures={"captain_mira": frozenset({"prince_is_traitor"})},
            quest_stage=1,
        )

    def test_valid_dialogue_passes(self) -> None:
        action = CandidateAction(
            action_id="a-valid",
            actor_id="captain_mira",
            action_type="NPC_REPLY",
            preconditions=frozenset({"player_saved_dock"}),
            effects=frozenset(),
            used_facts=frozenset({"player_saved_dock"}),
            disclosed_facts=frozenset({"player_saved_dock"}),
            required_quest_stage=1,
        )
        self.assertTrue(validate_candidate(self.state, action).valid)

    def test_counterexample_exposes_all_hard_failures(self) -> None:
        action = CandidateAction(
            action_id="a-invalid",
            actor_id="captain_mira",
            action_type="UNLOCK_AND_REVEAL",
            preconditions=frozenset({"player_has_map"}),
            effects=frozenset({"lighthouse_unlocked"}),
            required_objects=frozenset({"rusted_key"}),
            used_facts=frozenset({"prince_is_traitor"}),
            disclosed_facts=frozenset({"prince_is_traitor"}),
            required_quest_stage=2,
        )
        codes = {error.code for error in validate_candidate(self.state, action).errors}
        self.assertEqual(
            codes,
            {
                "UNSATISFIED_PRECONDITION",
                "UNREACHABLE_REQUIRED_OBJECT",
                "NPC_KNOWLEDGE_VIOLATION",
                "NPC_DISCLOSURE_KNOWLEDGE_VIOLATION",
                "FORBIDDEN_DISCLOSURE",
                "QUEST_STAGE_VIOLATION",
            },
        )

    def test_unknown_disclosure_is_rejected_even_when_not_forbidden(self) -> None:
        action = CandidateAction(
            action_id="a-unknown-disclosure",
            actor_id="captain_mira",
            action_type="NPC_REPLY",
            preconditions=frozenset({"player_saved_dock"}),
            effects=frozenset(),
            disclosed_facts=frozenset({"unknown_secret"}),
        )
        codes = {error.code for error in validate_candidate(self.state, action).errors}
        self.assertIn("NPC_DISCLOSURE_KNOWLEDGE_VIOLATION", codes)

    def test_candidate_cannot_omit_authoritative_precondition(self) -> None:
        action = CandidateAction(
            action_id="a-policy-bypass",
            actor_id="captain_mira",
            action_type="NPC_REPLY",
            preconditions=frozenset(),
            effects=frozenset(),
        )
        codes = {error.code for error in validate_candidate(self.state, action).errors}
        self.assertIn("POLICY_PRECONDITION_OMISSION", codes)

    def test_world_mapping_is_defensively_immutable(self) -> None:
        source = {"key": "dock"}
        state = WorldState(
            state_id="immutable",
            locations=frozenset({"dock"}),
            reachable_locations=frozenset({"dock"}),
            object_locations=source,
            inventory=frozenset(),
            facts=frozenset(),
        )
        source["key"] = "elsewhere"
        self.assertEqual(state.object_locations["key"], "dock")
        with self.assertRaises(TypeError):
            state.object_locations["key"] = "elsewhere"


if __name__ == "__main__":
    unittest.main()
