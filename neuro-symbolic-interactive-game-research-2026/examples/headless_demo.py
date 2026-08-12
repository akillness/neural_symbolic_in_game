#!/usr/bin/env python3
"""Run the commit boundary without a model or game engine."""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from nesy_game import ActionPolicy, CandidateAction, WorldState, execute_with_repair, to_jsonable


def main() -> None:
    state = WorldState(
        state_id="harbor-0",
        locations=frozenset({"harbor", "lighthouse"}),
        reachable_locations=frozenset({"harbor"}),
        object_locations={},
        inventory=frozenset(),
        facts=frozenset({"player_saved_dock"}),
        action_policies={
            "NPC_REPLY": ActionPolicy(
                required_preconditions=frozenset({"player_saved_dock"}),
                allowed_effects=frozenset({"lighthouse_hint_given"}),
                required_effects=frozenset({"lighthouse_hint_given"}),
            )
        },
        npc_knowledge={"captain_mira": frozenset({"player_saved_dock"})},
        forbidden_disclosures={"captain_mira": frozenset({"prince_is_traitor"})},
        quest_stage=1,
    )
    proposal = CandidateAction(
        action_id="demo-1",
        actor_id="captain_mira",
        action_type="NPC_REPLY",
        preconditions=frozenset({"player_has_map"}),
        effects=frozenset({"lighthouse_hint_given"}),
        used_facts=frozenset({"player_saved_dock"}),
        narrative_text="The old light answers only to those who saved the dock.",
    )

    def counterexample_repair(world, action, validation, attempt):
        policy = world.action_policies[action.action_type]
        return replace(action, preconditions=policy.required_preconditions)

    outcome = execute_with_repair(
        state,
        proposal,
        counterexample_repair,
        repair_budget=1,
        trace_context={"seed": 23, "evidence_ids": ["fact-player-saved-dock"]},
    )
    print(json.dumps(to_jsonable(outcome), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
