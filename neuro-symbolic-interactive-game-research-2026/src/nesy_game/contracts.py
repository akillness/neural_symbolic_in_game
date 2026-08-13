"""Dependency-free contracts shared by research and headless game tracks."""

from __future__ import annotations

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
