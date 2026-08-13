"""Contract tests for the one shared candidate parser and its two call sites.

``nesy_game.experiment.candidate_from_mapping`` (proposal boundary) and
``nesy_game.runtime.parse_candidate_record`` (replay boundary) both delegate to
``nesy_game.contracts.parse_candidate_mapping``. These tests pin the two guarantees that
the delegation exists to provide:

1. unknown-key handling is identical at both boundaries, and
2. the deliberate optional-field asymmetry stays safe, because a defaulted proposal
   candidate always serializes into a record that strict replay accepts.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from nesy_game import (
    AdapterFailure,
    CandidateAction,
    candidate_from_mapping,
    parse_candidate_record,
    to_jsonable,
)
from nesy_game.contracts import (
    CANDIDATE_FIELDS,
    REQUIRED_CANDIDATE_FIELDS,
    CandidateParseError,
)

# All twelve keys present: the shape replay reads back after a commit, and therefore the
# shape both boundaries accept. Value-level cases below mutate exactly one key of this
# record so a rejection cannot be blamed on an unrelated defect in the fixture.
FULL_RECORD: dict = {
    "action_id": "a1",
    "actor_id": "guard",
    "action_type": "REPLY",
    "preconditions": ["met_guard"],
    "effects": ["door_open"],
    "required_objects": ["key"],
    "used_facts": ["met_guard"],
    "disclosed_facts": [],
    "required_quest_stage": 1,
    "quest_stage_effect": 2,
    "narrative_text": "the guard steps aside",
    "metadata": {"confidence": 0.5, "nested": {"tags": ["a", "b"]}},
}

# Exactly the five required keys: what a generator may legitimately emit at the proposal
# boundary, where omitted optional keys take their documented defaults.
MINIMAL_PAYLOAD: dict = {
    "action_id": "a1",
    "actor_id": "guard",
    "action_type": "REPLY",
    "preconditions": ["met_guard"],
    "effects": ["door_open"],
}


def record(**overrides: object) -> dict:
    """A valid twelve-key record with the given keys replaced."""

    return {**FULL_RECORD, **overrides}


class CandidateContractTests(unittest.TestCase):
    # --- helpers -------------------------------------------------------------------

    def _reject_at_both_boundaries(self, payload: object) -> tuple[AdapterFailure, ValueError]:
        """Assert both call sites reject `payload`, and return both exceptions."""

        with self.assertRaises(AdapterFailure) as proposal:
            candidate_from_mapping(payload)
        self.assertEqual(proposal.exception.code, "parse_error")

        with self.assertRaises(CandidateParseError) as replay:
            parse_candidate_record(payload)

        return proposal.exception, replay.exception

    def _accepted_at_both_boundaries(self, payload: dict) -> CandidateAction:
        """Control for the value-level cases: the unmutated record still parses."""

        candidate = candidate_from_mapping(payload)
        self.assertEqual(parse_candidate_record(payload), candidate)
        return candidate

    # --- unknown-key parity: the defect that motivated the refactor ------------------

    def test_unknown_top_level_key_rejected_by_proposal_boundary(self) -> None:
        payload = record(unexpected_key="smuggled")

        with self.assertRaises(AdapterFailure) as caught:
            candidate_from_mapping(payload)

        self.assertEqual(caught.exception.code, "parse_error")
        self.assertIn("unexpected_key", str(caught.exception))

    def test_unknown_top_level_key_rejected_by_replay_boundary(self) -> None:
        payload = record(unexpected_key="smuggled")

        with self.assertRaises(CandidateParseError) as caught:
            parse_candidate_record(payload)

        # Replay callers catch ValueError, so the subclass relationship is contract.
        self.assertIsInstance(caught.exception, ValueError)
        self.assertIn("unexpected_key", str(caught.exception))

    def test_regression_unknown_key_rejected_by_both_boundaries_never_only_by_replay(
        self,
    ) -> None:
        # REGRESSION GUARD for the divergence this refactor removed. Proposal used to
        # silently ignore unknown top-level keys while replay rejected them, so replay
        # could refuse a candidate that had already committed. Parity means one verdict:
        # the identical payload must be rejected by BOTH boundaries, never by only one.
        payload = record(unexpected_key="smuggled")

        proposal_failure, replay_failure = self._reject_at_both_boundaries(payload)

        self.assertIn("unexpected_key", str(proposal_failure))
        self.assertIn("unexpected_key", str(replay_failure))
        self.assertEqual(str(proposal_failure), str(replay_failure))
        # The unmutated record is accepted by both, so the shared verdict above is
        # caused by the unknown key alone.
        self._accepted_at_both_boundaries(FULL_RECORD)

    # --- intentional defaults asymmetry: must NOT be "fixed" -------------------------

    def test_minimal_payload_parses_with_documented_defaults_at_proposal_boundary(self) -> None:
        candidate = candidate_from_mapping(MINIMAL_PAYLOAD)

        self.assertEqual(candidate.required_objects, frozenset())
        self.assertEqual(candidate.used_facts, frozenset())
        self.assertEqual(candidate.disclosed_facts, frozenset())
        self.assertEqual(candidate.required_quest_stage, 0)
        self.assertIsNone(candidate.quest_stage_effect)
        self.assertEqual(candidate.narrative_text, "")
        self.assertEqual(dict(candidate.metadata), {})
        # The supplied required keys survive untouched alongside the defaults.
        self.assertEqual(candidate.action_id, "a1")
        self.assertEqual(candidate.preconditions, frozenset({"met_guard"}))
        self.assertEqual(candidate.effects, frozenset({"door_open"}))
        # Stated as one contract: omitting an optional key is equivalent to spelling out
        # its documented default, never to some other value.
        self.assertEqual(
            candidate,
            CandidateAction(
                action_id="a1",
                actor_id="guard",
                action_type="REPLY",
                preconditions=frozenset({"met_guard"}),
                effects=frozenset({"door_open"}),
                required_objects=frozenset(),
                used_facts=frozenset(),
                disclosed_facts=frozenset(),
                required_quest_stage=0,
                quest_stage_effect=None,
                narrative_text="",
                metadata={},
            ),
        )

    def test_minimal_payload_rejected_by_replay_because_all_twelve_keys_required(self) -> None:
        # Replay strictness is deliberate, not an oversight: a persisted record was
        # serialized from a committed CandidateAction, so a missing optional key means
        # record corruption. Making replay lenient here would delete that detector.
        with self.assertRaises(CandidateParseError) as caught:
            parse_candidate_record(MINIMAL_PAYLOAD)

        message = str(caught.exception)
        omitted_keys = CANDIDATE_FIELDS - REQUIRED_CANDIDATE_FIELDS
        self.assertEqual(len(CANDIDATE_FIELDS), 12)
        self.assertEqual(len(REQUIRED_CANDIDATE_FIELDS), 5)
        for key in omitted_keys:
            with self.subTest(missing_key=key):
                self.assertIn(key, message)
        # Keys that were supplied are not reported as missing.
        for key in REQUIRED_CANDIDATE_FIELDS - omitted_keys:
            with self.subTest(supplied_key=key):
                self.assertNotIn(key, message)

    # --- round trip: the invariant that makes the asymmetry safe ---------------------

    def test_defaulted_proposal_candidate_round_trips_through_strict_replay(self) -> None:
        # Proposal may omit optional keys; replay may not accept an omission. That is
        # only safe because serializing a parsed candidate always materializes the
        # defaults into a complete twelve-key record.
        for label, payload in (
            ("defaults applied", MINIMAL_PAYLOAD),
            ("all keys supplied", FULL_RECORD),
        ):
            with self.subTest(payload=label):
                candidate = candidate_from_mapping(payload)

                serialized = to_jsonable(candidate)

                self.assertEqual(set(serialized), CANDIDATE_FIELDS)
                self.assertEqual(parse_candidate_record(serialized), candidate)

    # --- value-level validation, applied identically at both boundaries --------------

    def test_duplicate_collection_entry_rejected_at_both_boundaries(self) -> None:
        self._accepted_at_both_boundaries(record(preconditions=["x", "y"]))

        proposal_failure, replay_failure = self._reject_at_both_boundaries(
            record(preconditions=["x", "x"])
        )

        # Rejected, not silently deduplicated into frozenset({"x"}).
        self.assertIn("preconditions", str(proposal_failure))
        self.assertIn("preconditions", str(replay_failure))

    def test_missing_required_key_rejected_at_both_boundaries(self) -> None:
        payload = {key: value for key, value in FULL_RECORD.items() if key != "action_id"}

        proposal_failure, replay_failure = self._reject_at_both_boundaries(payload)

        self.assertIn("action_id", str(proposal_failure))
        self.assertIn("action_id", str(replay_failure))

    def test_bool_rejected_where_exact_integer_required_at_both_boundaries(self) -> None:
        # bool is an int subclass in Python; required_quest_stage=True must not slip
        # through as the integer 1.
        control = self._accepted_at_both_boundaries(record(required_quest_stage=1))
        self.assertEqual(control.required_quest_stage, 1)

        proposal_failure, replay_failure = self._reject_at_both_boundaries(
            record(required_quest_stage=True)
        )

        self.assertIn("required_quest_stage", str(proposal_failure))
        self.assertIn("required_quest_stage", str(replay_failure))

    def test_negative_required_quest_stage_rejected_at_both_boundaries(self) -> None:
        control = self._accepted_at_both_boundaries(record(required_quest_stage=0))
        self.assertEqual(control.required_quest_stage, 0)

        proposal_failure, replay_failure = self._reject_at_both_boundaries(
            record(required_quest_stage=-1)
        )

        self.assertIn("required_quest_stage", str(proposal_failure))
        self.assertIn("required_quest_stage", str(replay_failure))

    def test_non_finite_metadata_number_rejected_at_both_boundaries(self) -> None:
        control = self._accepted_at_both_boundaries(record(metadata={"score": 1.5}))
        self.assertEqual(dict(control.metadata), {"score": 1.5})

        for label, metadata in (
            ("nan", {"score": float("nan")}),
            ("inf", {"score": float("inf")}),
            ("-inf", {"score": float("-inf")}),
            ("nested inf", {"outer": {"scores": [float("inf")]}}),
        ):
            with self.subTest(metadata=label):
                proposal_failure, replay_failure = self._reject_at_both_boundaries(
                    record(metadata=metadata)
                )

                self.assertIn("metadata", str(proposal_failure))
                self.assertIn("metadata", str(replay_failure))

    def test_empty_string_in_collection_rejected_at_both_boundaries(self) -> None:
        control = self._accepted_at_both_boundaries(record(effects=["door_open"]))
        self.assertEqual(control.effects, frozenset({"door_open"}))

        proposal_failure, replay_failure = self._reject_at_both_boundaries(
            record(effects=["door_open", ""])
        )

        self.assertIn("effects", str(proposal_failure))
        self.assertIn("effects", str(replay_failure))

    def test_non_mapping_candidate_rejected_at_both_boundaries(self) -> None:
        for candidate in ([], "a1", None):
            with self.subTest(candidate=candidate):
                proposal_failure, replay_failure = self._reject_at_both_boundaries(candidate)

                self.assertEqual(str(proposal_failure), str(replay_failure))


if __name__ == "__main__":
    unittest.main()
