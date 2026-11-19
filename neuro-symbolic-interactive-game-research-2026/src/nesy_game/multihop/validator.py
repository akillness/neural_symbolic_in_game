"""Core multi-hop ontology closure gate, bounded repair wrapper, and external baselines.

Kept inside the ``nesy_game.multihop`` subpackage so the frozen top-level
``src/nesy_game/*.py`` source-hash inventory remains byte-identical while
consolidating multi-hop closure into the core ``nesy_game`` package.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from ..contracts import (
    CandidateAction,
    ValidationError,
    ValidationResult,
    WorldState,
)
from ..repair import counterexample_guided_repair
from ..validator import VALIDATOR_CHECKS, validate_candidate


@dataclass(frozen=True)
class MultihopOntologySpec:
    """Read-only declarative ontology rules over role inheritance and fact implications."""

    role_parents: Mapping[str, frozenset[str]] = field(default_factory=dict)
    fact_implications: Mapping[str, frozenset[str]] = field(default_factory=dict)
    forbidden_by_role: Mapping[str, frozenset[str]] = field(default_factory=dict)
    min_stage_by_fact: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "role_parents",
            MappingProxyType({k: frozenset(v) for k, v in self.role_parents.items()}),
        )
        object.__setattr__(
            self,
            "fact_implications",
            MappingProxyType({k: frozenset(v) for k, v in self.fact_implications.items()}),
        )
        object.__setattr__(
            self,
            "forbidden_by_role",
            MappingProxyType({k: frozenset(v) for k, v in self.forbidden_by_role.items()}),
        )
        object.__setattr__(
            self,
            "min_stage_by_fact",
            MappingProxyType({k: int(v) for k, v in self.min_stage_by_fact.items()}),
        )


@dataclass(frozen=True)
class DatalogClosureResult:
    """Bottom-up semi-naive fixpoint result for one actor and fact seed set."""

    actor_id: str
    role_closure: frozenset[str]
    derived_facts: frozenset[str]
    effective_forbidden: frozenset[str]
    leaked_roots: frozenset[str]
    required_min_stage: int


def _transitive_fixpoint(
    seeds: Sequence[str], adjacency: Mapping[str, frozenset[str]]
) -> frozenset[str]:
    """Compute semi-naive transitive closure over directed string edges."""
    visited: set[str] = set(seeds)
    frontier: set[str] = set(seeds)
    while frontier:
        next_frontier: set[str] = set()
        for node in frontier:
            for nxt in adjacency.get(node, frozenset()):
                if nxt not in visited:
                    visited.add(nxt)
                    next_frontier.add(nxt)
        frontier = next_frontier
    return frozenset(visited)


def compute_datalog_closure(
    spec: MultihopOntologySpec,
    actor_id: str,
    seed_facts: Sequence[str],
    state_forbidden: Mapping[str, frozenset[str]] | None = None,
) -> DatalogClosureResult:
    """Evaluate bottom-up transitive role inheritance and fact derivation closure."""
    roles = _transitive_fixpoint([actor_id], spec.role_parents)
    derived = _transitive_fixpoint(list(seed_facts), spec.fact_implications)
    forbidden: set[str] = set()
    for role in roles:
        forbidden |= spec.forbidden_by_role.get(role, frozenset())
        if state_forbidden is not None:
            forbidden |= state_forbidden.get(role, frozenset())
    leaked = frozenset(derived & forbidden)
    req_stage = max((spec.min_stage_by_fact.get(item, 0) for item in derived), default=0)
    return DatalogClosureResult(
        actor_id=actor_id,
        role_closure=roles,
        derived_facts=derived,
        effective_forbidden=frozenset(forbidden),
        leaked_roots=leaked,
        required_min_stage=req_stage,
    )


def validate_candidate_multihop(
    state: WorldState,
    action: CandidateAction,
    spec: MultihopOntologySpec,
) -> ValidationResult:
    """Enforce the canonical 7-predicate gate plus transitive multi-hop ontology closure."""
    base = validate_candidate(state, action)
    extra_errors: list[ValidationError] = []
    roles = _transitive_fixpoint([action.actor_id], spec.role_parents)
    forbidden: set[str] = set(state.forbidden_disclosures.get(action.actor_id, frozenset()))
    for role in roles:
        forbidden |= state.forbidden_disclosures.get(role, frozenset())
        forbidden |= spec.forbidden_by_role.get(role, frozenset())

    for fact in sorted(set(action.used_facts) | set(action.disclosed_facts)):
        derived = _transitive_fixpoint([fact], spec.fact_implications)
        hits = sorted(derived & forbidden)
        if hits:
            extra_errors.append(
                ValidationError(
                    code="FORBIDDEN_DISCLOSURE",
                    entity=fact,
                    reason=(
                        f"Fact '{fact}' transitively entails forbidden secret(s) {hits} "
                        f"under role closure {sorted(roles)}."
                    ),
                    repair_hint="Withhold derived or role-inherited forbidden disclosures.",
                )
            )
        min_stage = max((spec.min_stage_by_fact.get(item, 0) for item in derived), default=0)
        if state.quest_stage < min_stage:
            extra_errors.append(
                ValidationError(
                    code="QUEST_STAGE_VIOLATION",
                    entity=fact,
                    reason=(
                        f"Fact '{fact}' closure {sorted(derived)} requires stage {min_stage}, "
                        f"current stage is {state.quest_stage}."
                    ),
                    repair_hint="Advance quest_stage before referencing derived staged facts.",
                )
            )

    if not extra_errors:
        return base
    merged: dict[tuple[str, str, str], ValidationError] = {}
    for err in (*base.errors, *extra_errors):
        merged.setdefault((err.code, err.entity, err.reason), err)
    checks = (*VALIDATOR_CHECKS, "multihop_ontology_closure")
    errors_tuple = tuple(merged.values())
    return ValidationResult(
        valid=len(errors_tuple) == 0,
        errors=errors_tuple,
        checks_run=checks,
    )


def execute_with_multihop_repair(
    state: WorldState,
    candidate: CandidateAction,
    spec: MultihopOntologySpec,
    *,
    max_repairs: int = 2,
) -> tuple[CandidateAction, ValidationResult, int]:
    """Apply bounded state-blind rho(a, E) against the multi-hop validator (Theorems 1-4)."""
    if max_repairs < 0:
        raise ValueError("max_repairs must be non-negative")
    current = candidate
    repairs_used = 0
    val = validate_candidate_multihop(state, current, spec)
    while not val.valid and repairs_used < max_repairs:
        repaired = counterexample_guided_repair(state, current, val, repairs_used + 1)
        if repaired == current:
            break
        current = repaired
        repairs_used += 1
        val = validate_candidate_multihop(state, current, spec)
    final_val = validate_candidate_multihop(state, current, spec)
    return current, final_val, repairs_used


def evaluate_action_mask_shield(state: WorldState, action: CandidateAction) -> ValidationResult:
    """Safe-RL Action Masking baseline (Alshiekh et al. 2018) without epistemic closure or rho.

    Enforces action existence, world-fact preconditions, object reachability, and
    monotonic stage constraints, but does not audit NPC knowledge gaps or
    multi-hop transitive disclosure leaks.
    """
    errors: list[ValidationError] = []
    policy = state.action_policies.get(action.action_type)
    if policy is None:
        errors.append(
            ValidationError(
                "UNKNOWN_ACTION_TYPE",
                action.action_type,
                "Action type has no registered policy.",
                "Select an allowed masked action.",
            )
        )
    else:
        for pre in sorted(policy.required_preconditions - action.preconditions):
            errors.append(
                ValidationError(
                    "POLICY_PRECONDITION_OMISSION",
                    pre,
                    f"Action mask requires precondition '{pre}'.",
                    "Use valid masked transition.",
                )
            )
        if (
            action.quest_stage_effect is not None
            and action.quest_stage_effect not in policy.allowed_quest_stage_effects
        ):
            errors.append(
                ValidationError(
                    "POLICY_QUEST_STAGE_EFFECT_VIOLATION",
                    str(action.quest_stage_effect),
                    "Stage transition disallowed by action mask.",
                    "Reselect action within current stage mask.",
                )
            )
    for pre in sorted(action.preconditions - state.facts):
        errors.append(
            ValidationError(
                "UNSATISFIED_PRECONDITION",
                pre,
                f"Precondition '{pre}' is absent from state.facts.",
                "Wait until precondition holds.",
            )
        )
    for obj in sorted(action.required_objects - state.inventory):
        loc = state.object_locations.get(obj)
        if loc is None or loc not in state.reachable_locations:
            errors.append(
                ValidationError(
                    "UNREACHABLE_REQUIRED_OBJECT",
                    obj,
                    f"Object '{obj}' is outside inventory and reachable locations.",
                    "Move to object location first.",
                )
            )
    if action.required_quest_stage > state.quest_stage:
        errors.append(
            ValidationError(
                "QUEST_STAGE_VIOLATION",
                str(action.required_quest_stage),
                "Action masked at current quest stage.",
                "Wait for prerequisite stage.",
            )
        )
    if action.quest_stage_effect is not None and action.quest_stage_effect < state.quest_stage:
        errors.append(
            ValidationError(
                "QUEST_STAGE_REGRESSION",
                str(action.quest_stage_effect),
                "Action mask forbids quest stage regression.",
                "Select non-regressing stage transition.",
            )
        )
    return ValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        checks_run=("action_policy_mask", "precondition", "reachability", "quest_stage_mask"),
    )


def evaluate_dialog_rail_filter(
    state: WorldState,
    action: CandidateAction,
    *,
    forbidden_tokens: Sequence[str] = (),
) -> ValidationResult:
    """NeMo-Guardrails-style Colang output-rail baseline without multi-hop closure or rho.

    Enforces schema/policy alignment, explicit 1-hop ``state.forbidden_disclosures[actor]``,
    and direct substring output rails on ``disclosed_facts`` / ``narrative_text``, while
    missing transitive multi-hop derivations (d >= 2), ancestor-role inheritance, and ``rho``.
    """
    errors: list[ValidationError] = []
    policy = state.action_policies.get(action.action_type)
    if policy is None:
        errors.append(
            ValidationError(
                "UNKNOWN_ACTION_TYPE",
                action.action_type,
                "Action type rejected by dialog rail.",
                "Regenerate response.",
            )
        )
    else:
        for eff in sorted(policy.required_effects - action.effects):
            errors.append(
                ValidationError(
                    "POLICY_EFFECT_OMISSION",
                    eff,
                    f"Dialog rail requires policy effect '{eff}'.",
                    "Regenerate response.",
                )
            )
        if (
            action.quest_stage_effect is not None
            and action.quest_stage_effect not in policy.allowed_quest_stage_effects
        ):
            errors.append(
                ValidationError(
                    "POLICY_QUEST_STAGE_EFFECT_VIOLATION",
                    str(action.quest_stage_effect),
                    "Dialog rail disallowed quest stage transition.",
                    "Regenerate response.",
                )
            )

    direct_forbidden = set(state.forbidden_disclosures.get(action.actor_id, frozenset()))
    for item in sorted(set(action.disclosed_facts) & direct_forbidden):
        errors.append(
            ValidationError(
                "FORBIDDEN_DISCLOSURE",
                item,
                f"Direct forbidden secret '{item}' blocked by dialog rail.",
                "Refuse forbidden topic.",
            )
        )

    lowered_text = action.narrative_text.lower()
    rail_terms = set(direct_forbidden) | {tok for tok in forbidden_tokens if tok}
    for term in sorted(rail_terms):
        readable = term.replace("_", " ").lower()
        if term.lower() in lowered_text or readable in lowered_text:
            errors.append(
                ValidationError(
                    "OUTPUT_RAIL_BLOCKED_TERM",
                    term,
                    f"Narrative output matched blocked 1-hop token '{term}'.",
                    "Rephrase without blocked term.",
                )
            )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=tuple(errors),
        checks_run=("action_policy_rail", "direct_1hop_forbidden", "lexical_output_rail"),
    )


def spec_to_dict(spec: MultihopOntologySpec) -> dict[str, Any]:
    """Serialize ``MultihopOntologySpec`` deterministically for JSON contracts."""
    return {
        "role_parents": {k: sorted(v) for k, v in sorted(spec.role_parents.items())},
        "fact_implications": {k: sorted(v) for k, v in sorted(spec.fact_implications.items())},
        "forbidden_by_role": {k: sorted(v) for k, v in sorted(spec.forbidden_by_role.items())},
        "min_stage_by_fact": dict(sorted(spec.min_stage_by_fact.items())),
    }
