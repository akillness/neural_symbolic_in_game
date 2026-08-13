"""Hard constraints. Narrative quality and affect never override these gates."""

from __future__ import annotations

from .contracts import CandidateAction, ValidationError, ValidationResult, WorldState


def validate_candidate(state: WorldState, action: CandidateAction) -> ValidationResult:
    errors: list[ValidationError] = []
    checks = (
        "action_policy",
        "precondition",
        "object_reachability",
        "npc_knowledge",
        "forbidden_disclosure",
        "quest_stage",
        "quest_stage_monotonicity",
    )

    policy = state.action_policies.get(action.action_type)
    if policy is None:
        errors.append(
            ValidationError(
                "UNKNOWN_ACTION_TYPE",
                action.action_type,
                f"Action type '{action.action_type}' has no authoritative policy.",
                "Reject the candidate or register an independently reviewed action policy.",
            )
        )
    else:
        for predicate in sorted(policy.required_preconditions - action.preconditions):
            errors.append(
                ValidationError(
                    "POLICY_PRECONDITION_OMISSION",
                    predicate,
                    f"Candidate omitted policy precondition '{predicate}'.",
                    "Restore the precondition from the authoritative action policy.",
                )
            )
        for effect in sorted(policy.required_effects - action.effects):
            errors.append(
                ValidationError(
                    "POLICY_EFFECT_OMISSION",
                    effect,
                    f"Candidate omitted required policy effect '{effect}'.",
                    "Restore the effect from the authoritative action policy.",
                )
            )
        for effect in sorted(action.effects - policy.allowed_effects):
            errors.append(
                ValidationError(
                    "POLICY_EFFECT_VIOLATION",
                    effect,
                    f"Candidate declared non-allowed effect '{effect}'.",
                    "Remove the effect or revise the policy through an audited authoring workflow.",
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
                    "Candidate declared a quest-stage mutation not authorized by its action policy.",
                    "Remove the stage mutation or authorize the exact target through audited policy.",
                )
            )

    for predicate in sorted(action.preconditions - state.facts):
        errors.append(
            ValidationError(
                "UNSATISFIED_PRECONDITION",
                predicate,
                f"Required predicate '{predicate}' is false in state {state.state_id}.",
                "Remove the dependency or establish the predicate in an earlier valid action.",
            )
        )

    for object_id in sorted(action.required_objects - state.inventory):
        location = state.object_locations.get(object_id)
        if location is None or location not in state.reachable_locations:
            errors.append(
                ValidationError(
                    "UNREACHABLE_REQUIRED_OBJECT",
                    object_id,
                    f"Required object '{object_id}' is not reachable before use.",
                    "Move the object to a reachable location or add a validated alternate route.",
                )
            )

    known = state.npc_knowledge.get(action.actor_id, frozenset())
    for fact in sorted(action.used_facts - known):
        errors.append(
            ValidationError(
                "NPC_KNOWLEDGE_VIOLATION",
                fact,
                f"Actor '{action.actor_id}' used a fact outside its knowledge set.",
                "Retrieve actor-visible evidence or remove the unsupported fact.",
            )
        )

    for fact in sorted(action.disclosed_facts - known):
        errors.append(
            ValidationError(
                "NPC_DISCLOSURE_KNOWLEDGE_VIOLATION",
                fact,
                f"Actor '{action.actor_id}' disclosed a fact outside its knowledge set.",
                "Remove the disclosure or establish an actor-visible evidence event first.",
            )
        )

    forbidden = state.forbidden_disclosures.get(action.actor_id, frozenset())
    for fact in sorted(action.disclosed_facts & forbidden):
        errors.append(
            ValidationError(
                "FORBIDDEN_DISCLOSURE",
                fact,
                f"Actor '{action.actor_id}' disclosed a locked fact.",
                "Withhold the fact until its symbolic release condition is satisfied.",
            )
        )

    if action.required_quest_stage > state.quest_stage:
        errors.append(
            ValidationError(
                "QUEST_STAGE_VIOLATION",
                str(action.required_quest_stage),
                f"Action requires stage {action.required_quest_stage}, current stage is {state.quest_stage}.",
                "Delay the action or validate the missing quest transition.",
            )
        )

    if action.quest_stage_effect is not None and action.quest_stage_effect < state.quest_stage:
        errors.append(
            ValidationError(
                "QUEST_STAGE_REGRESSION",
                str(action.quest_stage_effect),
                f"Action would regress quest stage from {state.quest_stage} to {action.quest_stage_effect}.",
                "Keep the stage monotonic or encode an explicit rollback event and policy.",
            )
        )

    return ValidationResult(not errors, tuple(errors), checks)
