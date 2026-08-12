import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from nesy_game import (
    ActionPolicy,
    CandidateAction,
    WorldState,
    execute_with_repair,
    to_jsonable,
    verify_trace_record,
    write_trace_jsonl,
)


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = WorldState(
            state_id="s0",
            locations=frozenset({"gate"}),
            reachable_locations=frozenset({"gate"}),
            object_locations={},
            inventory=frozenset(),
            facts=frozenset({"met_guard"}),
            action_policies={
                "REPLY": ActionPolicy(
                    frozenset({"met_guard"}),
                    frozenset({"door_open"}),
                    frozenset({"door_open"}),
                ),
                "ROLLBACK": ActionPolicy(frozenset({"met_guard"}), frozenset()),
            },
            npc_knowledge={"guard": frozenset({"met_guard"})},
            forbidden_disclosures={"guard": frozenset({"vault_code"})},
            quest_stage=1,
        )

    def test_invalid_candidate_never_mutates_state(self) -> None:
        action = CandidateAction(
            action_id="bad",
            actor_id="guard",
            action_type="REPLY",
            preconditions=frozenset({"unknown"}),
            effects=frozenset({"door_open"}),
        )
        outcome = execute_with_repair(self.state, action)
        self.assertEqual(outcome.status, "fallback")
        self.assertIs(outcome.state, self.state)
        self.assertNotIn("door_open", outcome.state.facts)

    def test_structured_repair_can_commit_within_budget(self) -> None:
        action = CandidateAction(
            action_id="repair-me",
            actor_id="guard",
            action_type="REPLY",
            preconditions=frozenset({"unknown"}),
            effects=frozenset({"door_open"}),
            quest_stage_effect=2,
        )

        def repair(state, candidate, validation, attempt):
            self.assertEqual(attempt, 1)
            self.assertIn("UNSATISFIED_PRECONDITION", {error.code for error in validation.errors})
            return replace(candidate, preconditions=frozenset({"met_guard"}))

        outcome = execute_with_repair(self.state, action, repair, repair_budget=1)
        self.assertEqual(outcome.status, "commit")
        self.assertEqual(outcome.attempts, 1)
        self.assertIn("door_open", outcome.state.facts)
        self.assertEqual(outcome.state.quest_stage, 2)
        self.assertEqual(len(outcome.trace_hash), 64)
        self.assertEqual(len(outcome.trace), 2)
        self.assertTrue(verify_trace_record(to_jsonable(outcome)))

    def test_repair_history_changes_trace_hash(self) -> None:
        final = CandidateAction(
            action_id="same-final",
            actor_id="guard",
            action_type="REPLY",
            preconditions=frozenset({"met_guard"}),
            effects=frozenset({"door_open"}),
        )
        initial = replace(final, preconditions=frozenset({"unknown"}))

        def repair(state, candidate, validation, attempt):
            return final

        repaired = execute_with_repair(self.state, initial, repair, repair_budget=1)
        direct = execute_with_repair(self.state, final)
        self.assertNotEqual(repaired.trace_hash, direct.trace_hash)

    def test_jsonl_trace_round_trip_verifies(self) -> None:
        action = CandidateAction(
            action_id="trace-round-trip",
            actor_id="guard",
            action_type="REPLY",
            preconditions=frozenset({"met_guard"}),
            effects=frozenset({"door_open"}),
        )
        outcome = execute_with_repair(
            self.state,
            action,
            trace_context={"seed": 47, "evidence_ids": ["met_guard"]},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trace.jsonl"
            write_trace_jsonl(path, outcome)
            record = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(verify_trace_record(record))

    def test_nested_trace_context_is_defensively_immutable(self) -> None:
        evidence_ids = ["met_guard"]
        action = CandidateAction(
            action_id="immutable-trace",
            actor_id="guard",
            action_type="REPLY",
            preconditions=frozenset({"met_guard"}),
            effects=frozenset({"door_open"}),
            metadata={"nested": {"tags": ["initial"]}},
        )
        outcome = execute_with_repair(
            self.state,
            action,
            trace_context={"evidence_ids": evidence_ids},
        )
        evidence_ids.append("late-mutation")
        self.assertEqual(outcome.trace_context["evidence_ids"], ("met_guard",))
        self.assertTrue(verify_trace_record(to_jsonable(outcome)))
        with self.assertRaises(AttributeError):
            outcome.candidate.metadata["nested"]["tags"].append("late-mutation")

    def test_trace_verifier_rejects_top_level_outcome_tampering(self) -> None:
        action = CandidateAction(
            action_id="tamper-check",
            actor_id="guard",
            action_type="REPLY",
            preconditions=frozenset({"met_guard"}),
            effects=frozenset({"door_open"}),
        )
        record = to_jsonable(execute_with_repair(self.state, action))
        record["state"]["facts"] = ["tampered"]
        record["attempts"] = 999
        self.assertFalse(verify_trace_record(record))

    def test_quest_stage_cannot_regress(self) -> None:
        action = CandidateAction(
            action_id="regress",
            actor_id="guard",
            action_type="ROLLBACK",
            preconditions=frozenset({"met_guard"}),
            effects=frozenset(),
            quest_stage_effect=0,
        )
        outcome = execute_with_repair(self.state, action)
        self.assertEqual(outcome.status, "fallback")
        self.assertEqual(outcome.validation.errors[0].code, "QUEST_STAGE_REGRESSION")


if __name__ == "__main__":
    unittest.main()
