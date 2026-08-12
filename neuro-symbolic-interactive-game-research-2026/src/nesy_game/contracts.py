"""Dependency-free contracts shared by research and headless game tracks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "required_preconditions", frozenset(self.required_preconditions))
        object.__setattr__(self, "allowed_effects", frozenset(self.allowed_effects))
        object.__setattr__(self, "required_effects", frozenset(self.required_effects))
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
        object.__setattr__(self, "locations", frozenset(self.locations))
        object.__setattr__(self, "reachable_locations", frozenset(self.reachable_locations))
        object.__setattr__(self, "inventory", frozenset(self.inventory))
        object.__setattr__(self, "facts", frozenset(self.facts))
        object.__setattr__(self, "object_locations", MappingProxyType(dict(self.object_locations)))
        object.__setattr__(self, "action_policies", MappingProxyType(dict(self.action_policies)))
        object.__setattr__(
            self,
            "npc_knowledge",
            MappingProxyType({key: frozenset(value) for key, value in self.npc_knowledge.items()}),
        )
        object.__setattr__(
            self,
            "forbidden_disclosures",
            MappingProxyType(
                {key: frozenset(value) for key, value in self.forbidden_disclosures.items()}
            ),
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
        for name in (
            "preconditions",
            "effects",
            "required_objects",
            "used_facts",
            "disclosed_facts",
        ):
            object.__setattr__(self, name, frozenset(getattr(self, name)))
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
