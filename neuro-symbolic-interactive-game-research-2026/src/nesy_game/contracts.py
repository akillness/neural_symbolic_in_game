"""Dependency-free contracts shared by research and headless game tracks."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


def _string_set(value: Any, field_name: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise TypeError(f"{field_name} must be an explicit collection of strings")
    frozen = frozenset(value)
    if len(frozen) != len(value):
        raise ValueError(f"{field_name} must not contain duplicates")
    if any(not isinstance(item, str) or not item for item in frozen):
        raise ValueError(f"{field_name} must contain non-empty strings")
    return frozen


def _string_set_mapping(value: Mapping[Any, Any], field_name: str) -> Mapping[str, frozenset[str]]:
    parsed: dict[str, frozenset[str]] = {}
    for key, children in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{field_name} keys must be non-empty strings")
        parsed[key] = _string_set(children, f"{field_name}.{key}")
    return MappingProxyType(parsed)


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(child) for key, child in value.items()})
    if isinstance(value, (set, frozenset)):
        return frozenset(_deep_freeze(child) for child in value)
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(child) for child in value)
    return value


@dataclass(frozen=True)
class ActionPolicy:
    """Authoritative encoded constraints for one action type."""

    required_preconditions: frozenset[str]
    allowed_effects: frozenset[str]
    required_effects: frozenset[str] = field(default_factory=frozenset)
    allowed_quest_stage_effects: frozenset[int] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_preconditions",
            _string_set(self.required_preconditions, "required_preconditions"),
        )
        object.__setattr__(
            self, "allowed_effects", _string_set(self.allowed_effects, "allowed_effects")
        )
        object.__setattr__(
            self, "required_effects", _string_set(self.required_effects, "required_effects")
        )
        stage_effects = frozenset(self.allowed_quest_stage_effects)
        if any(
            not isinstance(stage, int) or isinstance(stage, bool) or stage < 0
            for stage in stage_effects
        ):
            raise ValueError("allowed_quest_stage_effects must contain non-negative exact integers")
        object.__setattr__(self, "allowed_quest_stage_effects", stage_effects)
        if not self.required_effects <= self.allowed_effects:
            raise ValueError("required effects must be a subset of allowed effects")


@dataclass(frozen=True)
class WorldState:
    state_id: str
    locations: frozenset[str]
    reachable_locations: frozenset[str]
    object_locations: Mapping[str, str]
    inventory: frozenset[str]
    facts: frozenset[str]
    action_policies: Mapping[str, ActionPolicy] = field(default_factory=dict)
    npc_knowledge: Mapping[str, frozenset[str]] = field(default_factory=dict)
    forbidden_disclosures: Mapping[str, frozenset[str]] = field(default_factory=dict)
    quest_stage: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.state_id, str) or not self.state_id:
            raise ValueError("state_id must be a non-empty string")
        if not isinstance(self.quest_stage, int) or isinstance(self.quest_stage, bool):
            raise TypeError("quest_stage must be a non-negative exact integer")
        if self.quest_stage < 0:
            raise ValueError("quest_stage must be a non-negative exact integer")
        locations = _string_set(self.locations, "locations")
        reachable_locations = _string_set(self.reachable_locations, "reachable_locations")
        if not reachable_locations <= locations:
            raise ValueError("reachable locations must be a subset of locations")
        object_locations = dict(self.object_locations)
        if any(
            not isinstance(key, str) or not key or not isinstance(location, str) or not location
            for key, location in object_locations.items()
        ):
            raise ValueError("object locations must map non-empty strings to non-empty strings")
        if not set(object_locations.values()) <= locations:
            raise ValueError("object locations must refer to declared locations")
        action_policies = dict(self.action_policies)
        if any(
            not isinstance(key, str) or not key or not isinstance(policy, ActionPolicy)
            for key, policy in action_policies.items()
        ):
            raise ValueError("action policies must map non-empty strings to ActionPolicy values")
        object.__setattr__(self, "locations", locations)
        object.__setattr__(self, "reachable_locations", reachable_locations)
        object.__setattr__(self, "inventory", _string_set(self.inventory, "inventory"))
        object.__setattr__(self, "facts", _string_set(self.facts, "facts"))
        object.__setattr__(self, "object_locations", MappingProxyType(object_locations))
        object.__setattr__(self, "action_policies", MappingProxyType(action_policies))
        object.__setattr__(
            self,
            "npc_knowledge",
            _string_set_mapping(self.npc_knowledge, "npc_knowledge"),
        )
        object.__setattr__(
            self,
            "forbidden_disclosures",
            _string_set_mapping(self.forbidden_disclosures, "forbidden_disclosures"),
        )


@dataclass(frozen=True)
class CandidateAction:
    action_id: str
    actor_id: str
    action_type: str
    preconditions: frozenset[str]
    effects: frozenset[str]
    required_objects: frozenset[str] = field(default_factory=frozenset)
    used_facts: frozenset[str] = field(default_factory=frozenset)
    disclosed_facts: frozenset[str] = field(default_factory=frozenset)
    required_quest_stage: int = 0
    quest_stage_effect: int | None = None
    narrative_text: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("action_id", "actor_id", "action_type"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.required_quest_stage, int) or isinstance(
            self.required_quest_stage, bool
        ):
            raise TypeError("required_quest_stage must be a non-negative exact integer")
        if self.required_quest_stage < 0:
            raise ValueError("required_quest_stage must be a non-negative exact integer")
        if self.quest_stage_effect is not None and (
            not isinstance(self.quest_stage_effect, int)
            or isinstance(self.quest_stage_effect, bool)
        ):
            raise TypeError("quest_stage_effect must be null or a non-negative exact integer")
        if self.quest_stage_effect is not None and self.quest_stage_effect < 0:
            raise ValueError("quest_stage_effect must be null or a non-negative exact integer")
        if not isinstance(self.narrative_text, str):
            raise TypeError("narrative_text must be a string")
        for name in (
            "preconditions",
            "effects",
            "required_objects",
            "used_facts",
            "disclosed_facts",
        ):
            object.__setattr__(self, name, _string_set(getattr(self, name), name))
        object.__setattr__(self, "metadata", _deep_freeze(self.metadata))


@dataclass(frozen=True)
class ValidationError:
    code: str
    entity: str
    reason: str
    repair_hint: str


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: tuple[ValidationError, ...]
    checks_run: tuple[str, ...]


@dataclass(frozen=True)
class TraceAttempt:
    attempt: int
    candidate: CandidateAction
    validation: ValidationResult


@dataclass(frozen=True)
class CommitOutcome:
    status: str
    state: WorldState
    candidate: CandidateAction
    validation: ValidationResult
    attempts: int
    trace_hash: str
    prior_state: WorldState
    trace: tuple[TraceAttempt, ...]
    trace_context: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "trace", tuple(self.trace))
        object.__setattr__(self, "trace_context", _deep_freeze(self.trace_context))


# Single source of truth for the candidate event's top-level key NAMES.
#
# Both parsers derive their accepted key set from this constant: the proposal-side
# parser in `nesy_game.experiment` and the replay-side parser in `nesy_game.runtime`.
# Before Stage 8 the two maintained separate lists and disagreed on unknown keys — the
# proposal parser silently ignored them while replay rejected them, so replay could
# refuse a candidate that had already committed. Deriving both from one constant makes
# that specific divergence unrepresentable.
#
# The two parsers remain deliberately different in other respects and this constant does
# not unify them: the proposal parser supplies defaults for omitted optional fields,
# whereas the replay parser requires all twelve keys to be present because it reads
# records that were serialized from a committed CandidateAction. Value-level validation
# also differs. Only unknown-key handling is guaranteed identical.
CANDIDATE_FIELDS = frozenset(
    {
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
    }
)

REQUIRED_CANDIDATE_FIELDS = frozenset(
    {"action_id", "actor_id", "action_type", "preconditions", "effects"}
)


class CandidateParseError(ValueError):
    """Raised when a candidate mapping violates the shared candidate contract."""


def _as_string_set(value: Any, field: str) -> frozenset[str]:
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise CandidateParseError(f"{field} must be an explicit collection of strings")
    frozen = frozenset(value)
    # Mirrors _string_set: a duplicate entry must be rejected, not silently collapsed,
    # so a candidate cannot smuggle repeated facts past the contract.
    if len(frozen) != len(value):
        raise CandidateParseError(f"{field} must not contain duplicates")
    if any(not isinstance(item, str) or not item for item in frozen):
        raise CandidateParseError(f"{field} must contain non-empty strings")
    return frozen


def _as_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CandidateParseError(f"{field} must be a non-empty string")
    return value


def _as_exact_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CandidateParseError(f"{field} must be a non-negative exact integer")
    return value


def _as_json_value(value: Any, field: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CandidateParseError(f"{field} must be a finite number")
        return
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise CandidateParseError(f"{field} keys must be strings")
            _as_json_value(child, f"{field}.{key}")
        return
    if isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _as_json_value(child, f"{field}[{index}]")
        return
    raise CandidateParseError(f"{field} must be JSON-representable")


def parse_candidate_mapping(data: Any, *, allow_defaults: bool) -> CandidateAction:
    """Parse a candidate mapping under the one shared candidate contract.

    Both the proposal-side parser and the replay-side parser call this function, so
    unknown-key handling, required-key handling, and value-level validation cannot drift
    apart between them.

    Args:
        data: the candidate mapping.
        allow_defaults: when True, omitted optional keys take their documented defaults,
            which is the proposal boundary where a generator need not emit every field.
            When False, every key must be present, which is the replay boundary where the
            record was serialized from a committed :class:`CandidateAction`.

    Raises:
        CandidateParseError: on any contract violation. It subclasses ``ValueError`` so
            existing replay callers that catch ``ValueError`` keep working.
    """

    if not isinstance(data, Mapping):
        raise CandidateParseError("candidate must be an object")
    if any(not isinstance(key, str) for key in data):
        raise CandidateParseError("candidate keys must be strings")

    unknown = sorted(set(data.keys()) - CANDIDATE_FIELDS)
    if unknown:
        raise CandidateParseError(f"unknown candidate fields: {unknown}")

    expected = REQUIRED_CANDIDATE_FIELDS if allow_defaults else CANDIDATE_FIELDS
    missing = sorted(expected - data.keys())
    if missing:
        raise CandidateParseError(f"candidate fields missing: {missing}")

    quest_stage_effect = data.get("quest_stage_effect")
    if quest_stage_effect is not None:
        quest_stage_effect = _as_exact_int(quest_stage_effect, "quest_stage_effect")
    narrative_text = data.get("narrative_text", "")
    if not isinstance(narrative_text, str):
        raise CandidateParseError("narrative_text must be a string")
    metadata = data.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise CandidateParseError("metadata must be an object")
    _as_json_value(metadata, "metadata")

    return CandidateAction(
        action_id=_as_nonempty_string(data["action_id"], "action_id"),
        actor_id=_as_nonempty_string(data["actor_id"], "actor_id"),
        action_type=_as_nonempty_string(data["action_type"], "action_type"),
        preconditions=_as_string_set(data["preconditions"], "preconditions"),
        effects=_as_string_set(data["effects"], "effects"),
        required_objects=_as_string_set(data.get("required_objects", []), "required_objects"),
        used_facts=_as_string_set(data.get("used_facts", []), "used_facts"),
        disclosed_facts=_as_string_set(data.get("disclosed_facts", []), "disclosed_facts"),
        required_quest_stage=_as_exact_int(
            data.get("required_quest_stage", 0), "required_quest_stage"
        ),
        quest_stage_effect=quest_stage_effect,
        narrative_text=narrative_text,
        metadata=dict(metadata),
    )
