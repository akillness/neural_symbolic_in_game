"""Unit tests for the counterexample-guided repair operator rho(a, E).

The load-bearing contract: rho consumes ONLY the prior candidate and the
validator's structured error set. It never reads the authoritative WorldState —
every test below calls rho with a poisoned sentinel whose attribute access
raises, so any state read fails loudly.
"""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game import (
    GUIDED_IRREPARABLE_CODES,
    GUIDED_REPAIRABLE_CODES,
    CandidateAction,
    ValidationError,
    ValidationResult,
    counterexample_guided_repair,
)


class _PoisonedState:
    """Sentinel standing in for WorldState: any WorldState-field access raises.

    Interpreter-internal dunder lookups (``__class__`` during unittest collection)
    pass through; every domain attribute rho could conceivably read (``facts``,
    ``action_policies``, ``quest_stage``, ...) raises immediately.
    """

    def __getattribute__(self, name: str):
        if name.startswith("__") and name.endswith("__"):
            return object.__getattribute__(self, name)
        raise AssertionError(f"rho must not read WorldState (accessed {name!r})")


def _errors(*pairs: tuple[str, str]) -> ValidationResult:
    return ValidationResult(
        valid=False,
        errors=tuple(
            ValidationError(code, entity, f"designed test error {code}", "test hint")
            for code, entity in pairs
        ),
        checks_run=(),
    )


def _candidate(**overrides) -> CandidateAction:
    fields = {
        "action_id": "rho-test",
        "actor_id": "guard",
        "action_type": "SAY",
        "preconditions": frozenset({"met_guard"}),
        "effects": frozenset(),
    }
    fields.update(overrides)
    return CandidateAction(**fields)


_POISON = _PoisonedState()


class GuidedRepairPerErrorClassTests(unittest.TestCase):
    def test_policy_precondition_omission_inserts_exactly_the_named_predicate(self) -> None:
        candidate = _candidate(preconditions=frozenset())
        repaired = counterexample_guided_repair(
            _POISON, candidate, _errors(("POLICY_PRECONDITION_OMISSION", "met_guard")), 1
        )
        self.assertEqual(repaired.preconditions, frozenset({"met_guard"}))
        self.assertEqual(repaired.effects, candidate.effects)
        self.assertEqual(repaired.quest_stage_effect, candidate.quest_stage_effect)

    def test_unsatisfied_precondition_drops_exactly_the_named_predicate(self) -> None:
        candidate = _candidate(preconditions=frozenset({"met_guard", "stale_fact"}))
        repaired = counterexample_guided_repair(
            _POISON, candidate, _errors(("UNSATISFIED_PRECONDITION", "stale_fact")), 1
        )
        self.assertEqual(repaired.preconditions, frozenset({"met_guard"}))

    def test_policy_effect_omission_inserts_exactly_the_named_effect(self) -> None:
        candidate = _candidate(action_type="OPEN_DOOR")
        repaired = counterexample_guided_repair(
            _POISON, candidate, _errors(("POLICY_EFFECT_OMISSION", "door_open")), 1
        )
        self.assertEqual(repaired.effects, frozenset({"door_open"}))

    def test_policy_effect_violation_drops_exactly_the_named_effect(self) -> None:
        candidate = _candidate(effects=frozenset({"unauthorized_effect", "door_open"}))
        repaired = counterexample_guided_repair(
            _POISON, candidate, _errors(("POLICY_EFFECT_VIOLATION", "unauthorized_effect")), 1
        )
        self.assertEqual(repaired.effects, frozenset({"door_open"}))

    def test_stage_effect_violation_clears_only_the_stage_mutation(self) -> None:
        candidate = _candidate(quest_stage_effect=2)
        repaired = counterexample_guided_repair(
            _POISON, candidate, _errors(("POLICY_QUEST_STAGE_EFFECT_VIOLATION", "2")), 1
        )
        self.assertIsNone(repaired.quest_stage_effect)
        self.assertEqual(repaired.preconditions, candidate.preconditions)
        self.assertEqual(repaired.effects, candidate.effects)

    def test_every_declared_irreparable_code_is_a_strict_noop(self) -> None:
        candidate = _candidate(
            action_type="UNREGISTERED",
            required_objects=frozenset({"remote_key"}),
            used_facts=frozenset({"unknown_fact"}),
            disclosed_facts=frozenset({"sealed_secret"}),
            required_quest_stage=2,
            quest_stage_effect=0,
        )
        for code in sorted(GUIDED_IRREPARABLE_CODES):
            with self.subTest(code=code):
                repaired = counterexample_guided_repair(
                    _POISON, candidate, _errors((code, "some_entity")), 1
                )
                self.assertIs(repaired, candidate)

    def test_taxonomy_partitions_all_twelve_validator_codes(self) -> None:
        self.assertEqual(len(GUIDED_REPAIRABLE_CODES), 5)
        self.assertEqual(len(GUIDED_IRREPARABLE_CODES), 7)
        self.assertFalse(GUIDED_REPAIRABLE_CODES & GUIDED_IRREPARABLE_CODES)


class GuidedRepairPropertyTests(unittest.TestCase):
    def test_never_reads_state_poisoned_sentinel(self) -> None:
        # The sentinel raises on ANY attribute access; reaching an assertion on the
        # result proves rho completed without touching the state argument.
        candidate = _candidate(preconditions=frozenset())
        repaired = counterexample_guided_repair(
            _POISON,
            candidate,
            _errors(
                ("POLICY_PRECONDITION_OMISSION", "met_guard"),
                ("POLICY_EFFECT_VIOLATION", "bad_effect"),
                ("UNKNOWN_ACTION_TYPE", "SAY"),
            ),
            1,
        )
        self.assertEqual(repaired.preconditions, frozenset({"met_guard"}))

    def test_poisoned_sentinel_actually_poisons(self) -> None:
        with self.assertRaisesRegex(AssertionError, "must not read WorldState"):
            _ = _POISON.facts

    def test_idempotent_per_error_set(self) -> None:
        candidate = _candidate(
            preconditions=frozenset({"stale_fact"}),
            effects=frozenset({"unauthorized_effect"}),
            quest_stage_effect=2,
        )
        errors = _errors(
            ("POLICY_PRECONDITION_OMISSION", "met_guard"),
            ("UNSATISFIED_PRECONDITION", "stale_fact"),
            ("POLICY_EFFECT_VIOLATION", "unauthorized_effect"),
            ("POLICY_QUEST_STAGE_EFFECT_VIOLATION", "2"),
        )
        once = counterexample_guided_repair(_POISON, candidate, errors, 1)
        twice = counterexample_guided_repair(_POISON, once, errors, 2)
        self.assertEqual(once, twice)

    def test_edits_are_bounded_by_the_error_set(self) -> None:
        candidate = _candidate(
            preconditions=frozenset({"stale_fact"}),
            effects=frozenset({"unauthorized_effect"}),
            quest_stage_effect=2,
        )
        errors = _errors(
            ("POLICY_PRECONDITION_OMISSION", "met_guard"),
            ("UNSATISFIED_PRECONDITION", "stale_fact"),
            ("POLICY_EFFECT_VIOLATION", "unauthorized_effect"),
            ("POLICY_QUEST_STAGE_EFFECT_VIOLATION", "2"),
        )
        repaired = counterexample_guided_repair(_POISON, candidate, errors, 1)
        changed_fields = sum(
            getattr(repaired, field) != getattr(candidate, field)
            for field in (
                "action_id",
                "actor_id",
                "action_type",
                "preconditions",
                "effects",
                "required_objects",
                "used_facts",
                "disclosed_facts",
                "required_quest_stage",
                "quest_stage_effect",
                "narrative_text",
                "metadata",
            )
        )
        self.assertLessEqual(changed_fields, len(errors.errors))
        # Identity/declaration fields are never edited.
        self.assertEqual(repaired.action_id, candidate.action_id)
        self.assertEqual(repaired.actor_id, candidate.actor_id)
        self.assertEqual(repaired.action_type, candidate.action_type)
        self.assertEqual(repaired.required_objects, candidate.required_objects)
        self.assertEqual(repaired.used_facts, candidate.used_facts)
        self.assertEqual(repaired.disclosed_facts, candidate.disclosed_facts)

    def test_insert_drop_conflict_on_same_entity_is_declared_irreparable(self) -> None:
        # A predicate simultaneously required by policy and false in state cannot be
        # fixed candidate-locally; rho must leave it untouched rather than oscillate.
        candidate = _candidate(preconditions=frozenset({"contested_fact"}))
        errors = _errors(
            ("POLICY_PRECONDITION_OMISSION", "contested_fact"),
            ("UNSATISFIED_PRECONDITION", "contested_fact"),
        )
        repaired = counterexample_guided_repair(_POISON, candidate, errors, 1)
        self.assertIs(repaired, candidate)

    def test_noop_returns_the_identical_candidate_object(self) -> None:
        candidate = _candidate()
        repaired = counterexample_guided_repair(
            _POISON, candidate, _errors(("QUEST_STAGE_VIOLATION", "2")), 1
        )
        self.assertIs(repaired, candidate)

    def test_deterministic_for_equal_inputs(self) -> None:
        candidate = _candidate(effects=frozenset({"a", "b"}))
        errors = _errors(
            ("POLICY_EFFECT_VIOLATION", "a"),
            ("POLICY_EFFECT_VIOLATION", "b"),
            ("POLICY_EFFECT_OMISSION", "c"),
        )
        first = counterexample_guided_repair(_POISON, candidate, errors, 1)
        second = counterexample_guided_repair(_POISON, candidate, errors, 1)
        self.assertEqual(first, second)
        self.assertEqual(first.effects, frozenset({"c"}))


if __name__ == "__main__":
    unittest.main()
