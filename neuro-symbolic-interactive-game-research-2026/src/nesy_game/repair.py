"""Counterexample-guided candidate repair: rho(a, E) reads no authoritative state.

The operator consumes exactly two inputs: the prior candidate ``a`` and the
validator's structured error set ``E`` (codes + entity payloads). It never reads
the authoritative ``WorldState``; the ``state`` parameter exists only to satisfy
the shared ``Repairer`` callback signature and is discarded before any use. This
is the load-bearing contract separating rho from the state-reading reference
repairer (the oracle upper bound) used by the conformance pilot.

Per-error-class rule table (frozen; mirrored in the paper's method section):

| Validator code                       | Edit delta(e) on the candidate         | Rationale                                                        |
|--------------------------------------|----------------------------------------|------------------------------------------------------------------|
| POLICY_PRECONDITION_OMISSION         | insert entity into ``preconditions``   | payload names the exact declared policy requirement               |
| POLICY_EFFECT_OMISSION               | insert entity into ``effects``         | payload names the exact declared policy requirement               |
| POLICY_EFFECT_VIOLATION              | drop entity from ``effects``           | drops exactly the unauthorized declared mutation                  |
| UNSATISFIED_PRECONDITION             | drop entity from ``preconditions``     | removes a candidate-declared dependency; candidate-local edit     |
| POLICY_QUEST_STAGE_EFFECT_VIOLATION  | set ``quest_stage_effect`` to ``None`` | drops exactly the unauthorized stage mutation                     |
| UNKNOWN_ACTION_TYPE                  | no-op                                  | payload names no registered alternative; any rewrite would guess  |
| UNREACHABLE_REQUIRED_OBJECT          | no-op                                  | undeclaring a genuine dependency would launder the violation      |
| NPC_KNOWLEDGE_VIOLATION              | no-op                                  | undeclaring a used fact would launder the violation               |
| NPC_DISCLOSURE_KNOWLEDGE_VIOLATION   | no-op                                  | undeclaring a disclosure would launder the violation              |
| FORBIDDEN_DISCLOSURE                 | no-op                                  | withholding requires knowing the release condition (state)        |
| QUEST_STAGE_VIOLATION                | no-op                                  | the correct requirement needs current-stage knowledge (state)     |
| QUEST_STAGE_REGRESSION               | no-op                                  | the mutation is policy-authorized; direction needs stage (state)  |

Properties (unit-tested in ``tests/test_guided_repair.py``):
- state-blind: no ``WorldState`` attribute is ever read (poisoned-state sentinel);
- deterministic: output depends only on ``(a, E)``;
- bounded: at most one field edit per distinct error entity, so the number of
  changed candidate fields per attempt is at most ``len(E)``;
- idempotent per error class: applying the same error set twice is a fixed point;
- conflict-safe: an entity named by both an insert rule and a drop rule on the
  same field is declared irreparable and left untouched (no oscillation within
  one attempt).
"""

from __future__ import annotations

from dataclasses import replace

from .contracts import CandidateAction, ValidationResult, WorldState

_PRECONDITION_INSERT = "POLICY_PRECONDITION_OMISSION"
_PRECONDITION_DROP = "UNSATISFIED_PRECONDITION"
_EFFECT_INSERT = "POLICY_EFFECT_OMISSION"
_EFFECT_DROP = "POLICY_EFFECT_VIOLATION"
_STAGE_EFFECT_DROP = "POLICY_QUEST_STAGE_EFFECT_VIOLATION"

GUIDED_REPAIRABLE_CODES = frozenset(
    {
        _PRECONDITION_INSERT,
        _PRECONDITION_DROP,
        _EFFECT_INSERT,
        _EFFECT_DROP,
        _STAGE_EFFECT_DROP,
    }
)

GUIDED_IRREPARABLE_CODES = frozenset(
    {
        "UNKNOWN_ACTION_TYPE",
        "UNREACHABLE_REQUIRED_OBJECT",
        "NPC_KNOWLEDGE_VIOLATION",
        "NPC_DISCLOSURE_KNOWLEDGE_VIOLATION",
        "FORBIDDEN_DISCLOSURE",
        "QUEST_STAGE_VIOLATION",
        "QUEST_STAGE_REGRESSION",
    }
)


def counterexample_guided_repair(
    state: WorldState,
    candidate: CandidateAction,
    validation: ValidationResult,
    attempt: int,
) -> CandidateAction:
    """Return rho(candidate, validation.errors); the state argument is never read."""

    del state, attempt  # rho consumes only the prior candidate and the error set.

    precondition_inserts = {
        error.entity for error in validation.errors if error.code == _PRECONDITION_INSERT
    }
    precondition_drops = {
        error.entity for error in validation.errors if error.code == _PRECONDITION_DROP
    }
    effect_inserts = {error.entity for error in validation.errors if error.code == _EFFECT_INSERT}
    effect_drops = {error.entity for error in validation.errors if error.code == _EFFECT_DROP}

    # An entity simultaneously demanded and rejected on the same field is declared
    # guided-irreparable: editing it either way re-triggers the opposite error, so
    # rho leaves it untouched instead of oscillating.
    precondition_conflicts = precondition_inserts & precondition_drops
    precondition_inserts -= precondition_conflicts
    precondition_drops -= precondition_conflicts
    effect_conflicts = effect_inserts & effect_drops
    effect_inserts -= effect_conflicts
    effect_drops -= effect_conflicts

    drop_stage_effect = any(error.code == _STAGE_EFFECT_DROP for error in validation.errors)

    repaired_preconditions = (candidate.preconditions - frozenset(precondition_drops)) | frozenset(
        precondition_inserts
    )
    repaired_effects = (candidate.effects - frozenset(effect_drops)) | frozenset(effect_inserts)
    repaired_stage_effect = None if drop_stage_effect else candidate.quest_stage_effect

    if (
        repaired_preconditions == candidate.preconditions
        and repaired_effects == candidate.effects
        and repaired_stage_effect == candidate.quest_stage_effect
    ):
        return candidate
    return replace(
        candidate,
        preconditions=repaired_preconditions,
        effects=repaired_effects,
        quest_stage_effect=repaired_stage_effect,
    )
