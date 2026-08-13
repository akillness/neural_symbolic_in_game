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

    def test_quest_stage_mutation_requires_explicit_policy_authorization(self) -> None:
        action = CandidateAction(
            action_id="a-stage-bypass",
            actor_id="captain_mira",
            action_type="NPC_REPLY",
            preconditions=frozenset({"player_saved_dock"}),
            effects=frozenset(),
            quest_stage_effect=2,
        )
        codes = {error.code for error in validate_candidate(self.state, action).errors}
        self.assertIn("POLICY_QUEST_STAGE_EFFECT_VIOLATION", codes)

    def test_narrative_semantics_require_a_separate_extractor(self) -> None:
        action = CandidateAction(
            action_id="a-semantic-boundary",
            actor_id="captain_mira",
            action_type="NPC_REPLY",
            preconditions=frozenset({"player_saved_dock"}),
            effects=frozenset(),
            disclosed_facts=frozenset(),
            narrative_text="The prince is the traitor.",
        )
        self.assertTrue(validate_candidate(self.state, action).valid)

    def test_object_requirements_must_be_encoded_by_policy_or_candidate(self) -> None:
        action = CandidateAction(
            action_id="a-policy-completeness-boundary",
            actor_id="captain_mira",
            action_type="NPC_REPLY",
            preconditions=frozenset({"player_saved_dock"}),
            effects=frozenset(),
            required_objects=frozenset(),
        )
        self.assertTrue(validate_candidate(self.state, action).valid)

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

    def test_world_state_rejects_invalid_topology_and_stage_types(self) -> None:
        common = {
            "state_id": "invalid",
            "locations": frozenset({"dock"}),
            "object_locations": {},
            "inventory": frozenset(),
            "facts": frozenset(),
        }
        with self.assertRaisesRegex(ValueError, "reachable locations"):
            WorldState(reachable_locations=frozenset({"elsewhere"}), **common)
        with self.assertRaisesRegex(ValueError, "object locations"):
            WorldState(
                reachable_locations=frozenset({"dock"}),
                object_locations={"key": "elsewhere"},
                **{key: value for key, value in common.items() if key != "object_locations"},
            )
        with self.assertRaisesRegex(TypeError, "quest_stage"):
            WorldState(reachable_locations=frozenset({"dock"}), quest_stage=True, **common)

    def test_contract_string_sets_never_split_bare_strings(self) -> None:
        with self.assertRaisesRegex(TypeError, "preconditions"):
            CandidateAction(
                action_id="a",
                actor_id="captain_mira",
                action_type="NPC_REPLY",
                preconditions="player_saved_dock",
                effects=frozenset(),
            )
        with self.assertRaisesRegex(TypeError, "required_preconditions"):
            ActionPolicy("player_saved_dock", frozenset())
        with self.assertRaisesRegex(TypeError, "locations"):
            WorldState(
                state_id="s",
                locations="dock",
                reachable_locations=frozenset(),
                object_locations={},
                inventory=frozenset(),
                facts=frozenset(),
            )


if __name__ == "__main__":
    unittest.main()
