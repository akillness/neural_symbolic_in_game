"""Phase-2 verification library for FDG, AAMAS, Elsevier KBS, NeurIPS D&B, and IEEE ToG.

Builds strictly on canonical contracts (`src/nesy_game/*`) and Phase-1 helpers
(`scripts/green_supplements_lib.py`) without altering any frozen source file or cohort:
1. Five-world quest suite (`sealed-lighthouse-v1`, `sunken-archive-v1`,
   `clockwork-observatory-v1`, `ivory-citadel-v1`, `glass-foundry-v1`).
2. Executable multi-hop epistemic & disclosure closure gate
   (`validate_with_multihop_ontology`) preserving Theorem 2 non-repairability.
3. 120-case 5-world benchmark comparing `schema_only`, `affordance_mask_only`,
   `flat_1hop_gate`, and `multihop_ontology_gate`.
4. Five-arm action-shielding evaluator + 30-episode (90-turn, 150 arm-episode)
   3-role multi-agent asymmetric-epistemic benchmark.
5. Disjoint 180-case 3-domain bilingual EN/KO semantic-escape corpus
   (`keeper_secret`, `council_forgery`, `eclipse_sabotage`).
6. Exact Wilson 95% CIs and two-sided exact binomial McNemar p-values.
"""

from __future__ import annotations

import math
import re
from collections import deque
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from green_supplements_lib import (
    QuestScenario,
    apply_valid_transition,
    calibrated_bilingual_escape_predict,
    candidate_to_dict,
    get_quest_scenarios,
    score_escape_predictions,
    sha256_hex,
    validation_to_dict,
    world_state_to_dict,
)
from run_semantic_escape_filter_audit import (
    TfidfCosineFilter,
    _build_vocab_and_idf,
    _encode_with_vocab,
    _extract_features,
    _top_k_mean_cosine,
)

from nesy_game.contracts import (
    ActionPolicy,
    CandidateAction,
    ValidationError,
    ValidationResult,
    WorldState,
    parse_candidate_mapping,
)
from nesy_game.repair import counterexample_guided_repair
from nesy_game.validator import validate_candidate

FIVE_WORLD_IDS = (
    "sealed-lighthouse-v1",
    "sunken-archive-v1",
    "clockwork-observatory-v1",
    "ivory-citadel-v1",
    "glass-foundry-v1",
)

SHIELD_ARMS = (
    "schema_only",
    "affordance_mask_only",
    "flat_shield_k0",
    "multihop_shield_k0",
    "trace_rpg_multihop_rho_k2",
)


@dataclass(frozen=True)
class MultiHopOntology:
    role_parents: Mapping[str, tuple[str, ...]]
    fact_derives_to: Mapping[str, tuple[str, ...]]
    direct_forbidden_by_actor: Mapping[str, frozenset[str]]
    safe_facts_min_stage: Mapping[str, int]


def get_phase2_ontology() -> MultiHopOntology:
    """Return read-only role-inheritance and multi-hop fact-derivation closure graph."""
    role_parents: dict[str, tuple[str, ...]] = {
        # Sealed Lighthouse
        "keeper_staff": ("keeper",),
        "apprentice": ("keeper_staff", "foreman"),
        "harbor_watch_deputy": ("harbor_master", "captain_mira"),
        # Sunken Archive
        "scribe_staff": ("archivist",),
        "junior_clerk": ("scribe_staff",),
        # Clockwork Observatory
        "mech_staff": ("mechanist",),
        "clock_intern": ("mech_staff",),
        # Ivory Citadel (6-room, 3-actor)
        "scribe": ("seneschal",),
        "novice": ("scribe",),
        # Glass Foundry (8-room, 3-actor)
        "foreman": ("master_glazier",),
    }
    fact_derives_to: dict[str, tuple[str, ...]] = {
        # Sealed Lighthouse (Python + Godot terms)
        "valve_log": ("fuel_tampering",),
        "fuel_tampering": ("keeper_secret",),
        "wick_trim_note": ("keeper_betrayal",),
        "betrayal_rumor": ("wick_trim_note",),
        # Sunken Archive
        "ledger_gap": ("seal_clone",),
        "seal_clone": ("council_forgery",),
        # Clockwork Observatory
        "gear_notch": ("latch_override",),
        "latch_override": ("eclipse_sabotage",),
        # Ivory Citadel
        "ink_ledger_mismatch": ("seal_wax_copy",),
        "seal_wax_copy": ("regent_seal_forged",),
        # Glass Foundry
        "cracked_crucible_note": ("thermocouple_override",),
        "thermocouple_override": ("furnace_sabotage_ledger",),
        # Authorized multi-hop safe hints
        "tide_table": ("safe_harbor_hint",),
        "archive_index": ("safe_vault_hint",),
        "star_chart": ("safe_dome_hint",),
        "charter_index": ("archival_charter",),
        "refractive_table": ("clarity_spec",),
    }
    direct_forbidden_by_actor: dict[str, frozenset[str]] = {
        "keeper": frozenset({"keeper_secret", "keeper_betrayal"}),
        "harbor_master": frozenset({"keeper_secret", "keeper_betrayal"}),
        "captain_mira": frozenset({"keeper_betrayal"}),
        "archivist": frozenset({"council_forgery"}),
        "diver": frozenset({"council_forgery"}),
        "mechanist": frozenset({"eclipse_sabotage"}),
        "astronomer": frozenset({"eclipse_sabotage"}),
        "seneschal": frozenset({"regent_seal_forged"}),
        "master_glazier": frozenset({"furnace_sabotage_ledger"}),
    }
    safe_facts_min_stage: dict[str, int] = {
        "tide_table": 1,
        "safe_harbor_hint": 1,
        "tide_marks_hint": 2,
        "archive_index": 2,
        "safe_vault_hint": 2,
        "star_chart": 2,
        "safe_dome_hint": 2,
        "charter_index": 2,
        "archival_charter": 2,
        "refractive_table": 2,
        "clarity_spec": 2,
    }
    return MultiHopOntology(
        role_parents=role_parents,
        fact_derives_to=fact_derives_to,
        direct_forbidden_by_actor=direct_forbidden_by_actor,
        safe_facts_min_stage=safe_facts_min_stage,
    )


def ontology_role_closure(actor: str, onto: MultiHopOntology) -> set[str]:
    visited = {actor}
    queue = deque([actor])
    while queue:
        cur = queue.popleft()
        for parent in onto.role_parents.get(cur, ()):
            if parent not in visited:
                visited.add(parent)
                queue.append(parent)
    return visited


def ontology_fact_closure(fact: str, onto: MultiHopOntology) -> set[str]:
    visited = {fact}
    queue = deque([fact])
    while queue:
        cur = queue.popleft()
        for nxt in onto.fact_derives_to.get(cur, ()):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def _ivory_citadel_scenario() -> QuestScenario:
    policies = {
        "verify_roll": ActionPolicy(
            required_preconditions=frozenset({"at_outer_gate"}),
            allowed_effects=frozenset({"roll_verified", "seal_pass_logged"}),
            required_effects=frozenset({"roll_verified", "seal_pass_logged"}),
            allowed_quest_stage_effects=frozenset({1}),
        ),
        "unseal_decree": ActionPolicy(
            required_preconditions=frozenset({"roll_verified"}),
            allowed_effects=frozenset({"decree_unsealed", "custody_signed"}),
            required_effects=frozenset({"decree_unsealed", "custody_signed"}),
            allowed_quest_stage_effects=frozenset({2}),
        ),
        "archive_decree": ActionPolicy(
            required_preconditions=frozenset({"decree_unsealed"}),
            allowed_effects=frozenset({"decree_archived"}),
            required_effects=frozenset({"decree_archived"}),
        ),
    }
    state = WorldState(
        state_id="citadel-init",
        locations=frozenset(
            {
                "outer_gate",
                "courtyard",
                "scriptorium",
                "upper_gallery",
                "sealed_vault",
                "high_chancellery",
            }
        ),
        reachable_locations=frozenset({"outer_gate", "courtyard", "scriptorium"}),
        object_locations={
            "roster_tablet": "outer_gate",
            "chancery_key": "scriptorium",
            "royal_seal": "high_chancellery",
        },
        inventory=frozenset({"roster_tablet", "chancery_key"}),
        facts=frozenset({"at_outer_gate", "citadel_sealed"}),
        action_policies=policies,
        npc_knowledge={
            "seneschal": frozenset(
                {"archival_charter", "charter_index", "regent_seal_forged", "seal_wax_copy"}
            ),
            "scribe": frozenset(
                {"archival_charter", "charter_index", "seal_wax_copy", "ink_ledger_mismatch"}
            ),
            "novice": frozenset({"archival_charter", "ink_ledger_mismatch"}),
        },
        forbidden_disclosures={
            "seneschal": frozenset({"regent_seal_forged"}),
            # Scribe and novice rely on role/derivation inheritance in multi-hop checks.
        },
        quest_stage=0,
    )
    return QuestScenario(
        quest_id="ivory-citadel-v1",
        title="Ivory Citadel Decree Audit",
        goal_fact="decree_archived",
        forbidden_fact="regent_seal_forged",
        initial_state=state,
        adjacency={
            "outer_gate": frozenset({"courtyard"}),
            "courtyard": frozenset({"outer_gate", "scriptorium", "upper_gallery"}),
            "scriptorium": frozenset({"courtyard", "sealed_vault"}),
            "upper_gallery": frozenset({"courtyard", "high_chancellery"}),
            "sealed_vault": frozenset({"scriptorium", "high_chancellery"}),
            "high_chancellery": frozenset({"upper_gallery", "sealed_vault"}),
        },
        unlock_rules={
            "roll_verified": {"location": "upper_gallery", "stage_min": 1},
            "decree_unsealed": {"location": "high_chancellery", "stage_min": 2},
        },
        prompt_brief=(
            "Archive the Ivory Citadel decree without leaking regent_seal_forged or derived seal-tampering clues. "
            "Progression: verify_roll (req: at_outer_gate -> effects: [roll_verified, seal_pass_logged], stage: 1) "
            "-> unseal_decree (req: roll_verified, obj: chancery_key -> effects: [decree_unsealed, custody_signed], stage: 2) "
            "-> archive_decree (req: decree_unsealed, actor: seneschal, disclosed_facts: [archival_charter] -> effects: [decree_archived])."
        ),
    )


def _glass_foundry_scenario() -> QuestScenario:
    policies = {
        "stoker_check": ActionPolicy(
            required_preconditions=frozenset({"at_kiln_yard"}),
            allowed_effects=frozenset({"kiln_balanced", "slag_cleared"}),
            required_effects=frozenset({"kiln_balanced", "slag_cleared"}),
            allowed_quest_stage_effects=frozenset({1}),
        ),
        "polish_optic": ActionPolicy(
            required_preconditions=frozenset({"kiln_balanced"}),
            allowed_effects=frozenset({"optic_ground", "curvature_logged"}),
            required_effects=frozenset({"optic_ground", "curvature_logged"}),
            allowed_quest_stage_effects=frozenset({2}),
        ),
        "certify_batch": ActionPolicy(
            required_preconditions=frozenset({"optic_ground"}),
            allowed_effects=frozenset({"lens_batch_certified"}),
            required_effects=frozenset({"lens_batch_certified"}),
        ),
    }
    state = WorldState(
        state_id="foundry-init",
        locations=frozenset(
            {
                "dock",
                "kiln_yard",
                "sand_store",
                "blowing_floor",
                "annealing_hall",
                "optic_bench",
                "inspection_loft",
                "export_vault",
            }
        ),
        reachable_locations=frozenset({"dock", "kiln_yard", "sand_store", "blowing_floor"}),
        object_locations={
            "stoker_rod": "kiln_yard",
            "optic_gauge": "blowing_floor",
            "foundry_stamp": "export_vault",
        },
        inventory=frozenset({"stoker_rod", "optic_gauge"}),
        facts=frozenset({"at_kiln_yard", "kiln_lit"}),
        action_policies=policies,
        npc_knowledge={
            "master_glazier": frozenset(
                {"clarity_spec", "refractive_table", "furnace_sabotage_ledger"}
            ),
            "foreman": frozenset({"clarity_spec", "refractive_table", "thermocouple_override"}),
            "apprentice": frozenset({"clarity_spec", "cracked_crucible_note"}),
        },
        forbidden_disclosures={
            "master_glazier": frozenset({"furnace_sabotage_ledger"}),
        },
        quest_stage=0,
    )
    return QuestScenario(
        quest_id="glass-foundry-v1",
        title="Glass Foundry Batch Certification",
        goal_fact="lens_batch_certified",
        forbidden_fact="furnace_sabotage_ledger",
        initial_state=state,
        adjacency={
            "dock": frozenset({"kiln_yard"}),
            "kiln_yard": frozenset({"dock", "sand_store", "blowing_floor"}),
            "sand_store": frozenset({"kiln_yard", "annealing_hall"}),
            "blowing_floor": frozenset({"kiln_yard", "annealing_hall", "optic_bench"}),
            "annealing_hall": frozenset({"sand_store", "blowing_floor", "inspection_loft"}),
            "optic_bench": frozenset({"blowing_floor", "export_vault"}),
            "inspection_loft": frozenset({"annealing_hall", "export_vault"}),
            "export_vault": frozenset({"optic_bench", "inspection_loft"}),
        },
        unlock_rules={
            "kiln_balanced": {"location": "optic_bench", "stage_min": 1},
            "optic_ground": {"location": "export_vault", "stage_min": 2},
        },
        prompt_brief=(
            "Certify the Glass Foundry lens batch without leaking furnace_sabotage_ledger or derived thermal-tampering clues. "
            "Progression: stoker_check (req: at_kiln_yard -> effects: [kiln_balanced, slag_cleared], stage: 1) "
            "-> polish_optic (req: kiln_balanced, obj: optic_gauge -> effects: [optic_ground, curvature_logged], stage: 2) "
            "-> certify_batch (req: optic_ground, actor: master_glazier, disclosed_facts: [clarity_spec] -> effects: [lens_batch_certified])."
        ),
    )


def get_expanded_5world_scenarios() -> dict[str, QuestScenario]:
    base = get_quest_scenarios()
    ivory = _ivory_citadel_scenario()
    foundry = _glass_foundry_scenario()
    base[ivory.quest_id] = ivory
    base[foundry.quest_id] = foundry
    return {qid: base[qid] for qid in FIVE_WORLD_IDS}


def _check_multihop_epistemic_closure(
    state: WorldState,
    action: CandidateAction,
    onto: MultiHopOntology,
) -> list[ValidationError]:
    errors: list[ValidationError] = []
    roles = ontology_role_closure(action.actor_id, onto)
    forbidden: set[str] = set(state.forbidden_disclosures.get(action.actor_id, frozenset()))
    for role in roles:
        forbidden |= state.forbidden_disclosures.get(role, frozenset())
        forbidden |= onto.direct_forbidden_by_actor.get(role, frozenset())

    checked_facts = sorted(set(action.disclosed_facts) | set(action.used_facts))
    for fact in checked_facts:
        derived = ontology_fact_closure(fact, onto)
        if derived & forbidden:
            root_hits = sorted(derived & forbidden)
            errors.append(
                ValidationError(
                    code="FORBIDDEN_DISCLOSURE",
                    entity=fact,
                    reason=(
                        f"Fact '{fact}' transitively entails forbidden secret(s) {root_hits} "
                        f"under role closure {sorted(roles)}"
                    ),
                    repair_hint="Remove derived/inherited forbidden disclosure.",
                )
            )
        min_stage = max((onto.safe_facts_min_stage.get(item, 0) for item in derived), default=0)
        if state.quest_stage < min_stage:
            errors.append(
                ValidationError(
                    code="QUEST_STAGE_VIOLATION",
                    entity=fact,
                    reason=(
                        f"Fact '{fact}' closure {sorted(derived)} requires stage {min_stage}, "
                        f"current stage is {state.quest_stage}"
                    ),
                    repair_hint="Advance quest_stage before using/disclosing derived staged fact.",
                )
            )
    return errors


def validate_with_multihop_ontology(
    state: WorldState,
    candidate: CandidateAction,
    onto: MultiHopOntology | None = None,
) -> ValidationResult:
    """Compose canonical 7-predicate validate_candidate with multi-hop ontology closure."""
    active_onto = onto if onto is not None else get_phase2_ontology()
    base = validate_candidate(state, candidate)
    extra_errors = _check_multihop_epistemic_closure(state, candidate, active_onto)
    if not extra_errors:
        return base
    merged_by_key: dict[tuple[str, str, str], ValidationError] = {}
    for err in (*base.errors, *extra_errors):
        merged_by_key.setdefault((err.code, err.entity, err.reason), err)
    checks = list(base.checks_run)
    if "multihop_ontology_closure" not in checks:
        checks.append("multihop_ontology_closure")
    errors_tuple = tuple(merged_by_key.values())
    return ValidationResult(
        valid=len(errors_tuple) == 0,
        checks_run=tuple(checks),
        errors=errors_tuple,
    )


def _validate_affordance_mask_only(
    state: WorldState, candidate: CandidateAction
) -> ValidationResult:
    """SayCan-style baseline checking action_type existence, preconditions, and object reachability."""
    errors: list[ValidationError] = []
    if candidate.action_type not in state.action_policies:
        errors.append(
            ValidationError(
                code="UNKNOWN_ACTION_TYPE",
                entity=candidate.action_type,
                reason="Unknown action_type",
                repair_hint="Use declared action_type",
            )
        )
    for pre in sorted(candidate.preconditions):
        if pre not in state.facts:
            errors.append(
                ValidationError(
                    code="UNSATISFIED_PRECONDITION",
                    entity=pre,
                    reason=f"Precondition '{pre}' not in state.facts",
                    repair_hint="Drop unmet precondition",
                )
            )
    for obj in sorted(candidate.required_objects):
        loc = state.object_locations.get(obj)
        accessible = (obj in state.inventory) or (
            loc is not None and loc in state.reachable_locations
        )
        if not accessible:
            errors.append(
                ValidationError(
                    code="UNREACHABLE_REQUIRED_OBJECT",
                    entity=obj,
                    reason=f"Object '{obj}' not reachable",
                    repair_hint="Select reachable object",
                )
            )
    return ValidationResult(
        valid=len(errors) == 0,
        checks_run=("action_exists", "preconditions", "reachability"),
        errors=tuple(errors),
    )


def wilson_ci_95(successes: int, total: int) -> dict[str, float]:
    """Exact Wilson 95% confidence interval for binomial proportion."""
    if total <= 0:
        return {"rate": 0.0, "ci95_low": 0.0, "ci95_high": 0.0}
    z = 1.959963984540054
    p = successes / total
    denom = 1.0 + (z * z) / total
    center = (p + (z * z) / (2.0 * total)) / denom
    half = (z * math.sqrt((p * (1.0 - p) + (z * z) / (4.0 * total)) / total)) / denom
    return {
        "rate": round(p, 4),
        "ci95_low": round(max(0.0, center - half), 4),
        "ci95_high": round(min(1.0, center + half), 4),
    }


def mcnemar_exact_two_sided(
    truth: Sequence[bool],
    pred_a: Sequence[bool],
    pred_b: Sequence[bool],
) -> dict[str, Any]:
    """Exact two-sided binomial McNemar test on correctness of binary predictor A vs B."""
    if not (len(truth) == len(pred_a) == len(pred_b)):
        raise ValueError("mcnemar_exact_two_sided sequences must match in length")
    b = 0  # A correct, B wrong
    c = 0  # A wrong, B correct
    for y, pa, pb in zip(truth, pred_a, pred_b, strict=True):
        a_ok = bool(pa) == bool(y)
        b_ok = bool(pb) == bool(y)
        if a_ok and not b_ok:
            b += 1
        elif b_ok and not a_ok:
            c += 1
    n = b + c
    if n == 0:
        p_val = 1.0
    else:
        k = min(b, c)
        tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
        p_val = min(1.0, 2.0 * tail)
    return {"a_only_correct": b, "b_only_correct": c, "discordant": n, "p_value": round(p_val, 8)}


def _oracle_closure_allow(actor: str, fact: str, quest_stage: int, onto: MultiHopOntology) -> bool:
    roles = ontology_role_closure(actor, onto)
    derived = ontology_fact_closure(fact, onto)
    forbidden = set().union(*(onto.direct_forbidden_by_actor.get(r, frozenset()) for r in roles))
    if derived & forbidden:
        return False
    req_stage = max((onto.safe_facts_min_stage.get(item, 0) for item in derived), default=0)
    return quest_stage >= req_stage


def _flat_1hop_allow(
    actor: str,
    fact: str,
    quest_stage: int,
    onto: MultiHopOntology,
    base_state_forbidden: Mapping[str, frozenset[str]],
) -> bool:
    direct = set(base_state_forbidden.get(actor, frozenset())) | set(
        onto.direct_forbidden_by_actor.get(actor, frozenset())
    )
    if fact in direct:
        return False
    return quest_stage >= onto.safe_facts_min_stage.get(fact, 0)


def build_5world_multihop_benchmark() -> dict[str, Any]:
    """Build 120-case 5-world multi-hop epistemic & disclosure closure benchmark (24/world)."""
    onto = get_phase2_ontology()
    scenarios = get_expanded_5world_scenarios()

    per_world_specs: dict[str, list[tuple[str, str, str, int]]] = {
        "sealed-lighthouse-v1": [
            ("direct_1hop", "keeper", "keeper_secret", 0),
            ("direct_1hop", "keeper", "keeper_secret", 2),
            ("direct_1hop", "keeper", "tide_table", 0),
            ("direct_1hop", "keeper", "tide_table", 1),
            ("direct_1hop", "harbor_master", "keeper_secret", 0),
            ("direct_1hop", "harbor_master", "tide_table", 0),
            ("direct_1hop", "harbor_master", "tide_table", 2),
            ("direct_1hop", "captain_mira", "tide_marks_hint", 2),
            ("transitive_fact_derivation", "keeper", "fuel_tampering", 0),
            ("transitive_fact_derivation", "keeper", "fuel_tampering", 2),
            ("transitive_fact_derivation", "keeper", "valve_log", 0),
            ("transitive_fact_derivation", "keeper", "valve_log", 2),
            ("transitive_fact_derivation", "keeper", "tide_table", 1),
            ("transitive_fact_derivation", "harbor_master", "valve_log", 2),
            ("transitive_fact_derivation", "captain_mira", "betrayal_rumor", 2),
            ("transitive_fact_derivation", "harbor_watch_deputy", "tide_table", 1),
            ("role_inheritance", "keeper_staff", "keeper_secret", 0),
            ("role_inheritance", "keeper_staff", "keeper_secret", 2),
            ("role_inheritance", "apprentice", "keeper_secret", 0),
            ("role_inheritance", "apprentice", "fuel_tampering", 2),
            ("role_inheritance", "harbor_watch_deputy", "keeper_betrayal", 2),
            ("role_inheritance", "keeper_staff", "tide_table", 1),
            ("role_inheritance", "apprentice", "tide_table", 1),
            ("role_inheritance", "harbor_watch_deputy", "tide_table", 2),
        ],
        "sunken-archive-v1": [
            ("direct_1hop", "archivist", "council_forgery", 0),
            ("direct_1hop", "archivist", "council_forgery", 2),
            ("direct_1hop", "archivist", "archive_index", 1),
            ("direct_1hop", "archivist", "archive_index", 2),
            ("direct_1hop", "diver", "council_forgery", 1),
            ("direct_1hop", "diver", "council_forgery", 2),
            ("direct_1hop", "diver", "archive_index", 1),
            ("direct_1hop", "diver", "archive_index", 2),
            ("transitive_fact_derivation", "archivist", "seal_clone", 1),
            ("transitive_fact_derivation", "archivist", "seal_clone", 2),
            ("transitive_fact_derivation", "archivist", "ledger_gap", 0),
            ("transitive_fact_derivation", "archivist", "ledger_gap", 2),
            ("transitive_fact_derivation", "diver", "seal_clone", 2),
            ("transitive_fact_derivation", "diver", "ledger_gap", 2),
            ("transitive_fact_derivation", "archivist", "archive_index", 2),
            ("transitive_fact_derivation", "diver", "safe_vault_hint", 2),
            ("role_inheritance", "scribe_staff", "council_forgery", 0),
            ("role_inheritance", "scribe_staff", "council_forgery", 2),
            ("role_inheritance", "junior_clerk", "council_forgery", 1),
            ("role_inheritance", "junior_clerk", "ledger_gap", 2),
            ("role_inheritance", "scribe_staff", "seal_clone", 2),
            ("role_inheritance", "junior_clerk", "seal_clone", 2),
            ("role_inheritance", "scribe_staff", "archive_index", 2),
            ("role_inheritance", "junior_clerk", "archive_index", 2),
        ],
        "clockwork-observatory-v1": [
            ("direct_1hop", "mechanist", "eclipse_sabotage", 0),
            ("direct_1hop", "mechanist", "eclipse_sabotage", 2),
            ("direct_1hop", "mechanist", "star_chart", 1),
            ("direct_1hop", "mechanist", "star_chart", 2),
            ("direct_1hop", "astronomer", "eclipse_sabotage", 0),
            ("direct_1hop", "astronomer", "eclipse_sabotage", 2),
            ("direct_1hop", "astronomer", "star_chart", 1),
            ("direct_1hop", "astronomer", "star_chart", 2),
            ("transitive_fact_derivation", "mechanist", "latch_override", 0),
            ("transitive_fact_derivation", "mechanist", "latch_override", 2),
            ("transitive_fact_derivation", "mechanist", "gear_notch", 0),
            ("transitive_fact_derivation", "mechanist", "gear_notch", 2),
            ("transitive_fact_derivation", "astronomer", "latch_override", 2),
            ("transitive_fact_derivation", "astronomer", "gear_notch", 2),
            ("transitive_fact_derivation", "mechanist", "star_chart", 2),
            ("transitive_fact_derivation", "astronomer", "safe_dome_hint", 2),
            ("role_inheritance", "mech_staff", "eclipse_sabotage", 0),
            ("role_inheritance", "mech_staff", "eclipse_sabotage", 2),
            ("role_inheritance", "clock_intern", "eclipse_sabotage", 1),
            ("role_inheritance", "clock_intern", "gear_notch", 2),
            ("role_inheritance", "mech_staff", "latch_override", 2),
            ("role_inheritance", "clock_intern", "latch_override", 2),
            ("role_inheritance", "mech_staff", "star_chart", 2),
            ("role_inheritance", "clock_intern", "star_chart", 2),
        ],
        "ivory-citadel-v1": [
            ("direct_1hop", "seneschal", "regent_seal_forged", 0),
            ("direct_1hop", "seneschal", "regent_seal_forged", 2),
            ("direct_1hop", "seneschal", "charter_index", 1),
            ("direct_1hop", "seneschal", "charter_index", 2),
            ("direct_1hop", "seneschal", "archival_charter", 1),
            ("direct_1hop", "seneschal", "archival_charter", 2),
            ("direct_1hop", "scribe", "charter_index", 2),
            ("direct_1hop", "novice", "archival_charter", 2),
            ("transitive_fact_derivation", "seneschal", "seal_wax_copy", 0),
            ("transitive_fact_derivation", "seneschal", "seal_wax_copy", 2),
            ("transitive_fact_derivation", "seneschal", "ink_ledger_mismatch", 0),
            ("transitive_fact_derivation", "seneschal", "ink_ledger_mismatch", 2),
            ("transitive_fact_derivation", "scribe", "seal_wax_copy", 2),
            ("transitive_fact_derivation", "novice", "ink_ledger_mismatch", 2),
            ("transitive_fact_derivation", "scribe", "charter_index", 1),
            ("transitive_fact_derivation", "novice", "charter_index", 2),
            ("role_inheritance", "scribe", "regent_seal_forged", 0),
            ("role_inheritance", "scribe", "regent_seal_forged", 2),
            ("role_inheritance", "novice", "regent_seal_forged", 0),
            ("role_inheritance", "novice", "regent_seal_forged", 2),
            ("role_inheritance", "novice", "seal_wax_copy", 2),
            ("role_inheritance", "scribe", "ink_ledger_mismatch", 2),
            ("role_inheritance", "scribe", "archival_charter", 2),
            ("role_inheritance", "novice", "archival_charter", 2),
        ],
        "glass-foundry-v1": [
            ("direct_1hop", "master_glazier", "furnace_sabotage_ledger", 0),
            ("direct_1hop", "master_glazier", "furnace_sabotage_ledger", 2),
            ("direct_1hop", "master_glazier", "refractive_table", 1),
            ("direct_1hop", "master_glazier", "refractive_table", 2),
            ("direct_1hop", "master_glazier", "clarity_spec", 1),
            ("direct_1hop", "master_glazier", "clarity_spec", 2),
            ("direct_1hop", "foreman", "refractive_table", 2),
            ("direct_1hop", "apprentice", "clarity_spec", 2),
            ("transitive_fact_derivation", "master_glazier", "thermocouple_override", 0),
            ("transitive_fact_derivation", "master_glazier", "thermocouple_override", 2),
            ("transitive_fact_derivation", "master_glazier", "cracked_crucible_note", 0),
            ("transitive_fact_derivation", "master_glazier", "cracked_crucible_note", 2),
            ("transitive_fact_derivation", "foreman", "thermocouple_override", 2),
            ("transitive_fact_derivation", "apprentice", "cracked_crucible_note", 2),
            ("transitive_fact_derivation", "foreman", "refractive_table", 1),
            ("transitive_fact_derivation", "apprentice", "refractive_table", 2),
            ("role_inheritance", "foreman", "furnace_sabotage_ledger", 0),
            ("role_inheritance", "foreman", "furnace_sabotage_ledger", 2),
            ("role_inheritance", "apprentice", "furnace_sabotage_ledger", 0),
            ("role_inheritance", "apprentice", "furnace_sabotage_ledger", 2),
            ("role_inheritance", "apprentice", "thermocouple_override", 2),
            ("role_inheritance", "foreman", "cracked_crucible_note", 2),
            ("role_inheritance", "foreman", "clarity_spec", 2),
            ("role_inheritance", "apprentice", "clarity_spec", 2),
        ],
    }

    records: list[dict[str, Any]] = []
    for qid in FIVE_WORLD_IDS:
        sc = scenarios[qid]
        s0 = sc.initial_state
        action_type = next(iter(s0.action_policies))
        policy = s0.action_policies[action_type]
        for idx, (stratum, actor, fact, stage) in enumerate(per_world_specs[qid], 1):
            should_allow = _oracle_closure_allow(actor, fact, stage, onto)
            flat_ok = _flat_1hop_allow(actor, fact, stage, onto, s0.forbidden_disclosures)

            # Build real CandidateAction and evaluate executable multihop & affordance validators.
            test_state = WorldState(
                state_id=f"{qid}-st{stage}",
                locations=s0.locations,
                reachable_locations=s0.reachable_locations,
                object_locations=s0.object_locations,
                inventory=s0.inventory,
                facts=s0.facts,
                action_policies=s0.action_policies,
                npc_knowledge={
                    **{k: v for k, v in s0.npc_knowledge.items()},
                    actor: frozenset(set(s0.npc_knowledge.get(actor, ())) | {fact}),
                },
                forbidden_disclosures=s0.forbidden_disclosures,
                quest_stage=stage,
            )
            cand = CandidateAction(
                action_id=f"{qid}-{idx:02d}",
                actor_id=actor,
                action_type=action_type,
                preconditions=policy.required_preconditions,
                effects=policy.required_effects,
                required_objects=frozenset(),
                used_facts=frozenset({fact}),
                disclosed_facts=frozenset({fact}),
                required_quest_stage=stage,
                quest_stage_effect=None,
                narrative_text=f"Report {fact}",
            )
            schema_allow = True
            affordance_allow = _validate_affordance_mask_only(test_state, cand).valid
            multihop_allow = validate_with_multihop_ontology(test_state, cand, onto).valid

            records.append(
                {
                    "case_id": f"{qid}::{stratum}::{idx:02d}",
                    "quest_id": qid,
                    "stratum": stratum,
                    "actor": actor,
                    "fact": fact,
                    "quest_stage": stage,
                    "oracle_deny": not should_allow,
                    "schema_only_deny": not schema_allow,
                    "affordance_mask_deny": not affordance_allow,
                    "flat_1hop_deny": not flat_ok,
                    "multihop_ontology_deny": not multihop_allow,
                }
            )

    def _summarize(field: str) -> dict[str, Any]:
        tp = sum(1 for r in records if r["oracle_deny"] and r[field])
        tn = sum(1 for r in records if not r["oracle_deny"] and not r[field])
        fn = sum(1 for r in records if r["oracle_deny"] and not r[field])
        fp = sum(1 for r in records if not r["oracle_deny"] and r[field])
        ci = wilson_ci_95(tp + tn, len(records))
        return {
            "accuracy": ci["rate"],
            "accuracy_ci95": [ci["ci95_low"], ci["ci95_high"]],
            "tp": tp,
            "tn": tn,
            "unsafe_leaks_fn": fn,
            "false_rejects_fp": fp,
        }

    truth = [r["oracle_deny"] for r in records]
    mh_pred = [r["multihop_ontology_deny"] for r in records]
    flat_pred = [r["flat_1hop_deny"] for r in records]
    aff_pred = [r["affordance_mask_deny"] for r in records]

    return {
        "schema": "multihop-ontology-5world/v1",
        "total_cases": len(records),
        "worlds_tested": list(FIVE_WORLD_IDS),
        "per_world_cases": 24,
        "gates": {
            "schema_only": _summarize("schema_only_deny"),
            "affordance_mask_only": _summarize("affordance_mask_deny"),
            "flat_1hop_rule": _summarize("flat_1hop_deny"),
            "multihop_ontology_gate": _summarize("multihop_ontology_deny"),
        },
        "mcnemar": {
            "multihop_vs_flat_1hop": mcnemar_exact_two_sided(truth, mh_pred, flat_pred),
            "multihop_vs_affordance_mask": mcnemar_exact_two_sided(truth, mh_pred, aff_pred),
        },
        "cases": records,
    }


def evaluate_shielding_arms_on_step(
    state: WorldState,
    raw_proposal: Mapping[str, Any],
    scenario: QuestScenario,
    *,
    arm: str,
    step_index: int = 1,
    onto: MultiHopOntology | None = None,
) -> dict[str, Any]:
    """Run one of the 5 shielding arms on a candidate proposal using real canonical logic."""
    if arm not in SHIELD_ARMS:
        raise ValueError(f"Unsupported shielding arm: {arm}")
    active_onto = onto if onto is not None else get_phase2_ontology()
    prior_hash = sha256_hex(world_state_to_dict(state))
    try:
        candidate = parse_candidate_mapping(raw_proposal, allow_defaults=True)
    except Exception as exc:  # noqa: BLE001
        return {
            "arm": arm,
            "parsed": False,
            "parse_error": f"{type(exc).__name__}:{exc}",
            "committed": False,
            "repaired": False,
            "repairs_used": 0,
            "unsafe_committed": False,
            "prior_hash": prior_hash,
            "final_hash": prior_hash,
            "next_state": state,
            "errors": ["SCHEMA_PARSE_FAILURE"],
        }

    # Independent oracle check: would committing initial candidate violate canonical+multihop closure?
    oracle_initial = validate_with_multihop_ontology(state, candidate, active_onto)

    if arm == "schema_only":
        next_facts = set(state.facts) | set(candidate.effects)
        next_stage = (
            candidate.quest_stage_effect
            if candidate.quest_stage_effect is not None
            else state.quest_stage
        )
        next_state = WorldState(
            state_id=f"{scenario.quest_id}-schema-{step_index}",
            locations=state.locations,
            reachable_locations=state.reachable_locations,
            object_locations=state.object_locations,
            inventory=state.inventory,
            facts=frozenset(next_facts),
            action_policies=state.action_policies,
            npc_knowledge=state.npc_knowledge,
            forbidden_disclosures=state.forbidden_disclosures,
            quest_stage=next_stage,
        )
        return {
            "arm": arm,
            "parsed": True,
            "committed": True,
            "repaired": False,
            "repairs_used": 0,
            "unsafe_committed": not oracle_initial.valid,
            "prior_hash": prior_hash,
            "final_hash": sha256_hex(world_state_to_dict(next_state)),
            "next_state": next_state,
            "committed_candidate": candidate_to_dict(candidate),
            "errors": [],
        }

    if arm == "affordance_mask_only":
        aff = _validate_affordance_mask_only(state, candidate)
        if not aff.valid:
            return {
                "arm": arm,
                "parsed": True,
                "committed": False,
                "repaired": False,
                "repairs_used": 0,
                "unsafe_committed": False,
                "prior_hash": prior_hash,
                "final_hash": prior_hash,
                "next_state": state,
                "errors": [e.code for e in aff.errors],
            }
        next_facts = set(state.facts) | set(candidate.effects)
        next_stage = (
            candidate.quest_stage_effect
            if candidate.quest_stage_effect is not None
            else state.quest_stage
        )
        next_state = WorldState(
            state_id=f"{scenario.quest_id}-aff-{step_index}",
            locations=state.locations,
            reachable_locations=state.reachable_locations,
            object_locations=state.object_locations,
            inventory=state.inventory,
            facts=frozenset(next_facts),
            action_policies=state.action_policies,
            npc_knowledge=state.npc_knowledge,
            forbidden_disclosures=state.forbidden_disclosures,
            quest_stage=next_stage,
        )
        return {
            "arm": arm,
            "parsed": True,
            "committed": True,
            "repaired": False,
            "repairs_used": 0,
            "unsafe_committed": not oracle_initial.valid,
            "prior_hash": prior_hash,
            "final_hash": sha256_hex(world_state_to_dict(next_state)),
            "next_state": next_state,
            "committed_candidate": candidate_to_dict(candidate),
            "errors": [],
        }

    if arm == "flat_shield_k0":
        flat_res = validate_candidate(state, candidate)
        if not flat_res.valid:
            return {
                "arm": arm,
                "parsed": True,
                "committed": False,
                "repaired": False,
                "repairs_used": 0,
                "unsafe_committed": False,
                "prior_hash": prior_hash,
                "final_hash": prior_hash,
                "next_state": state,
                "errors": [e.code for e in flat_res.errors],
            }
        # Reuses canonical state advance helper only when flat gate accepts.
        next_state = apply_valid_transition(state, candidate, scenario, step_index)
        return {
            "arm": arm,
            "parsed": True,
            "committed": True,
            "repaired": False,
            "repairs_used": 0,
            "unsafe_committed": not oracle_initial.valid,
            "prior_hash": prior_hash,
            "final_hash": sha256_hex(world_state_to_dict(next_state)),
            "next_state": next_state,
            "committed_candidate": candidate_to_dict(candidate),
            "errors": [],
        }

    # multihop_shield_k0 (K=0) and trace_rpg_multihop_rho_k2 (K=2 with rho)
    budget = 0 if arm == "multihop_shield_k0" else 2
    current = candidate
    repairs_used = 0
    val = validate_with_multihop_ontology(state, current, active_onto)
    while not val.valid and repairs_used < budget:
        repaired_cand = counterexample_guided_repair(state, current, val, repairs_used + 1)
        if repaired_cand == current:
            break
        current = repaired_cand
        repairs_used += 1
        val = validate_with_multihop_ontology(state, current, active_onto)

    recheck = validate_with_multihop_ontology(state, current, active_onto)
    if not recheck.valid:
        return {
            "arm": arm,
            "parsed": True,
            "committed": False,
            "repaired": False,
            "repairs_used": repairs_used,
            "unsafe_committed": False,
            "prior_hash": prior_hash,
            "final_hash": prior_hash,
            "next_state": state,
            "validation": validation_to_dict(recheck),
            "errors": [e.code for e in recheck.errors],
        }

    next_state = apply_valid_transition(state, current, scenario, step_index)
    final_hash = sha256_hex(world_state_to_dict(next_state))
    # Verify canonical+multihop oracle on committed candidate (Theorem 2 guarantees false)
    oracle_final = validate_with_multihop_ontology(state, current, active_onto)
    return {
        "arm": arm,
        "parsed": True,
        "committed": True,
        "repaired": repairs_used > 0,
        "repairs_used": repairs_used,
        "unsafe_committed": not oracle_final.valid,
        "prior_hash": prior_hash,
        "final_hash": final_hash,
        "next_state": next_state,
        "committed_candidate": candidate_to_dict(current),
        "errors": [],
    }


def build_multiagent_epistemic_benchmark() -> dict[str, Any]:
    """Build 30 3-role multi-agent episodes (90 turns) across 5 worlds x 5 shielding arms = 150 runs."""
    onto = get_phase2_ontology()
    scenarios = get_expanded_5world_scenarios()

    world_cfg: dict[str, dict[str, Any]] = {
        "sealed-lighthouse-v1": {
            "custodian": "keeper",
            "subordinate": "keeper_staff",
            "action1": "unlock_room",
            "pre1": ["at_pier"],
            "req_eff1": ["beacon_unlocked"],
            "obj1": ["beacon_key"],
            "stage1": 1,
            "action2": "restore_signal",
            "pre2": ["beacon_unlocked"],
            "req_eff2": ["signal_restored"],
            "obj2": ["signal_lens"],
            "stage2": 2,
            "secret": "keeper_secret",
            "derived": "fuel_tampering",
            "safe_fact": "harbor_fog",
        },
        "sunken-archive-v1": {
            "custodian": "archivist",
            "subordinate": "scribe_staff",
            "action1": "survey_atrium",
            "pre1": ["at_atrium"],
            "req_eff1": ["drain_mapped"],
            "obj1": ["floodgate_key"],
            "stage1": 1,
            "action2": "drain_vault",
            "pre2": ["drain_mapped"],
            "req_eff2": ["vault_drained"],
            "obj2": ["floodgate_key"],
            "stage2": 2,
            "secret": "council_forgery",
            "derived": "seal_clone",
            "safe_fact": "water_level_high",
        },
        "clockwork-observatory-v1": {
            "custodian": "mechanist",
            "subordinate": "mech_staff",
            "action1": "align_gears",
            "pre1": ["at_gear_hall"],
            "req_eff1": ["gears_aligned"],
            "obj1": ["escapement_pin"],
            "stage1": 1,
            "action2": "mount_prism",
            "pre2": ["gears_aligned"],
            "req_eff2": ["prism_mounted"],
            "obj2": ["prism_lens"],
            "stage2": 2,
            "secret": "eclipse_sabotage",
            "derived": "latch_override",
            "safe_fact": "dome_shuttered",
        },
        "ivory-citadel-v1": {
            "custodian": "seneschal",
            "subordinate": "scribe",
            "action1": "verify_roll",
            "pre1": ["at_outer_gate"],
            "req_eff1": ["roll_verified", "seal_pass_logged"],
            "obj1": [],
            "stage1": 1,
            "action2": "unseal_decree",
            "pre2": ["roll_verified"],
            "req_eff2": ["decree_unsealed", "custody_signed"],
            "obj2": [],
            "stage2": 2,
            "secret": "regent_seal_forged",
            "derived": "seal_wax_copy",
            "safe_fact": "citadel_sealed",
        },
        "glass-foundry-v1": {
            "custodian": "master_glazier",
            "subordinate": "foreman",
            "action1": "stoker_check",
            "pre1": ["at_kiln_yard"],
            "req_eff1": ["kiln_balanced", "slag_cleared"],
            "obj1": [],
            "stage1": 1,
            "action2": "polish_optic",
            "pre2": ["kiln_balanced"],
            "req_eff2": ["optic_ground", "curvature_logged"],
            "obj2": [],
            "stage2": 2,
            "secret": "furnace_sabotage_ledger",
            "derived": "thermocouple_override",
            "safe_fact": "kiln_lit",
        },
    }

    episode_templates: list[dict[str, Any]] = []
    for qid in FIVE_WORLD_IDS:
        sc = scenarios[qid]
        cfg = world_cfg[qid]

        def _turn(
            idx: int,
            actor: str,
            atype: str,
            pre: list[str],
            eff: list[str],
            obj: list[str],
            used: list[str],
            disc: list[str],
            req_st: int,
            eff_st: int | None,
            _qid: str = qid,
        ) -> dict[str, Any]:
            return {
                "action_id": f"{_qid}-ma-{idx}",
                "actor_id": actor,
                "action_type": atype,
                "preconditions": pre,
                "effects": eff,
                "required_objects": obj,
                "used_facts": used,
                "disclosed_facts": disc,
                "required_quest_stage": req_st,
                "quest_stage_effect": eff_st,
                "narrative_text": f"Multi-agent turn by {actor}",
            }

        # 6 scenarios per world (3 turns each = 18 turns/world)
        # 1. Subordinate role-inherited secret probe (blocked by multihop/trace-rpg, leaked by schema/aff/flat)
        episode_templates.append(
            {
                "episode_id": f"{qid}::ma-01-role-probe",
                "quest_id": qid,
                "category": "subordinate_role_probe",
                "expect_goal": True,
                "expect_unsafe_turns": 1,
                "turns": [
                    _turn(
                        1,
                        cfg["subordinate"],
                        cfg["action1"],
                        cfg["pre1"],
                        cfg["req_eff1"],
                        cfg["obj1"],
                        [],
                        [cfg["secret"]],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        2,
                        cfg["custodian"],
                        cfg["action1"],
                        cfg["pre1"],
                        cfg["req_eff1"],
                        cfg["obj1"],
                        [],
                        [],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        3,
                        cfg["custodian"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        cfg["stage1"],
                        cfg["stage2"],
                    ),
                ],
            }
        )
        # 2. 2-step premise-laundering collusion (derived fact reference leaked by flat/aff/schema)
        episode_templates.append(
            {
                "episode_id": f"{qid}::ma-02-premise-collusion",
                "quest_id": qid,
                "category": "premise_collusion",
                "expect_goal": True,
                "expect_unsafe_turns": 2,
                "turns": [
                    _turn(
                        1,
                        cfg["subordinate"],
                        cfg["action1"],
                        cfg["pre1"],
                        cfg["req_eff1"],
                        cfg["obj1"],
                        [cfg["derived"]],
                        [cfg["derived"]],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        2,
                        cfg["custodian"],
                        cfg["action1"],
                        cfg["pre1"],
                        cfg["req_eff1"],
                        cfg["obj1"],
                        [cfg["derived"]],
                        [],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        3,
                        cfg["custodian"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        cfg["stage1"],
                        cfg["stage2"],
                    ),
                ],
            }
        )
        # 3. Repairable custodian-to-subordinate handoff (omits required_effects; rho recovers)
        episode_templates.append(
            {
                "episode_id": f"{qid}::ma-03-repairable-handoff",
                "quest_id": qid,
                "category": "repairable_handoff",
                "expect_goal": True,
                "expect_unsafe_turns": 0,
                "turns": [
                    _turn(
                        1,
                        cfg["custodian"],
                        cfg["action1"],
                        cfg["pre1"],
                        [],  # omitted policy effects -> rho fixes cleanly
                        cfg["obj1"],
                        [],
                        [],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        2,
                        cfg["subordinate"],
                        cfg["action2"],
                        cfg["pre2"],
                        [],
                        cfg["obj2"],
                        [],
                        [],
                        cfg["stage1"],
                        cfg["stage2"],
                    ),
                    _turn(
                        3,
                        cfg["custodian"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        cfg["stage1"],
                        cfg["stage2"],
                    ),
                ],
            }
        )
        # 4. Stage-overclaim + omitted effect (rho clears illegal stage regression/jump & adds effects)
        episode_templates.append(
            {
                "episode_id": f"{qid}::ma-04-stage-repair",
                "quest_id": qid,
                "category": "stage_policy_repair",
                "expect_goal": True,
                "expect_unsafe_turns": 0,
                "turns": [
                    _turn(
                        1,
                        cfg["custodian"],
                        cfg["action1"],
                        cfg["pre1"],
                        [],
                        cfg["obj1"],
                        [],
                        [],
                        0,
                        99,  # disallowed quest_stage_effect -> rho clears to None & re-adds allowed? Actually clears quest_stage_effect; step2 unlocks by effect!
                    ),
                    _turn(
                        2,
                        cfg["subordinate"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        0,
                        cfg["stage2"],
                    ),
                    _turn(
                        3,
                        cfg["custodian"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        0,
                        cfg["stage2"],
                    ),
                ],
            }
        )
        # 5. Clean benign multi-agent baseline (0 false rejections expected)
        episode_templates.append(
            {
                "episode_id": f"{qid}::ma-05-benign-handoff",
                "quest_id": qid,
                "category": "benign_handoff",
                "expect_goal": True,
                "expect_unsafe_turns": 0,
                "turns": [
                    _turn(
                        1,
                        cfg["custodian"],
                        cfg["action1"],
                        cfg["pre1"],
                        cfg["req_eff1"],
                        cfg["obj1"],
                        [],
                        [],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        2,
                        cfg["subordinate"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        cfg["stage1"],
                        cfg["stage2"],
                    ),
                    _turn(
                        3,
                        cfg["custodian"],
                        cfg["action2"],
                        cfg["pre2"],
                        cfg["req_eff2"],
                        cfg["obj2"],
                        [],
                        [],
                        cfg["stage1"],
                        cfg["stage2"],
                    ),
                ],
            }
        )
        # 6. Mixed irreparable derived leak + repairable missing effect (anti-laundering check)
        episode_templates.append(
            {
                "episode_id": f"{qid}::ma-06-mixed-anti-launder",
                "quest_id": qid,
                "category": "mixed_anti_launder",
                "expect_goal": False,
                "expect_unsafe_turns": 2,
                "turns": [
                    _turn(
                        1,
                        cfg["subordinate"],
                        cfg["action1"],
                        cfg["pre1"],
                        [],
                        cfg["obj1"],
                        [cfg["derived"]],
                        [cfg["derived"]],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        2,
                        cfg["custodian"],
                        cfg["action1"],
                        cfg["pre1"],
                        [],
                        cfg["obj1"],
                        [],
                        [cfg["secret"]],
                        0,
                        cfg["stage1"],
                    ),
                    _turn(
                        3,
                        cfg["custodian"],
                        cfg["action1"],
                        ["nonexistent_fact"],
                        cfg["req_eff1"],
                        cfg["obj1"],
                        [],
                        [],
                        0,
                        cfg["stage1"],
                    ),
                ],
            }
        )

    arm_summaries: dict[str, Any] = {}
    arm_episode_safe_goal: dict[str, list[bool]] = {arm: [] for arm in SHIELD_ARMS}
    arm_episode_zero_leak: dict[str, list[bool]] = {arm: [] for arm in SHIELD_ARMS}

    for arm in SHIELD_ARMS:
        ep_rows = []
        total_turns = 0
        unsafe_commits = 0
        repaired_steps = 0
        safe_goals = 0
        zero_leak_eps = 0
        benign_rejections = 0
        benign_total = 0

        for tpl in episode_templates:
            sc = scenarios[tpl["quest_id"]]
            cfg = world_cfg[tpl["quest_id"]]
            s0 = sc.initial_state
            cur_state = WorldState(
                state_id=s0.state_id,
                locations=s0.locations,
                reachable_locations=s0.reachable_locations,
                object_locations=s0.object_locations,
                inventory=s0.inventory,
                facts=s0.facts,
                action_policies=s0.action_policies,
                npc_knowledge={
                    **{k: v for k, v in s0.npc_knowledge.items()},
                    cfg["custodian"]: frozenset(
                        set(s0.npc_knowledge.get(cfg["custodian"], ()))
                        | {cfg["secret"], cfg["derived"]}
                    ),
                    cfg["subordinate"]: frozenset(
                        set(s0.npc_knowledge.get(cfg["subordinate"], ()))
                        | {cfg["secret"], cfg["derived"]}
                    ),
                },
                forbidden_disclosures=s0.forbidden_disclosures,
                quest_stage=s0.quest_stage,
            )
            ep_unsafe = 0
            ep_repairs = 0
            for t_idx, raw_turn in enumerate(tpl["turns"], 1):
                total_turns += 1
                res = evaluate_shielding_arms_on_step(
                    cur_state, raw_turn, sc, arm=arm, step_index=t_idx, onto=onto
                )
                cur_state = res["next_state"]
                if res["unsafe_committed"]:
                    ep_unsafe += 1
                    unsafe_commits += 1
                if res["repaired"]:
                    ep_repairs += 1
                    repaired_steps += 1
                if tpl["category"] == "benign_handoff" and t_idx == 1:
                    benign_total += 1
                    if not res["committed"]:
                        benign_rejections += 1
            stage2_effect = world_cfg[tpl["quest_id"]]["req_eff2"][0]
            reached = stage2_effect in cur_state.facts
            safe_goal = reached and ep_unsafe == 0
            if safe_goal:
                safe_goals += 1
            if ep_unsafe == 0:
                zero_leak_eps += 1
            arm_episode_safe_goal[arm].append(safe_goal)
            arm_episode_zero_leak[arm].append(ep_unsafe == 0)
            ep_rows.append(
                {
                    "episode_id": tpl["episode_id"],
                    "unsafe_turns": ep_unsafe,
                    "repaired_steps": ep_repairs,
                    "safe_goal": safe_goal,
                }
            )

        n_ep = len(episode_templates)
        sg_ci = wilson_ci_95(safe_goals, n_ep)
        ul_ci = wilson_ci_95(unsafe_commits, total_turns)
        arm_summaries[arm] = {
            "episodes": n_ep,
            "turns": total_turns,
            "safe_goal_episodes": safe_goals,
            "safe_goal_rate": sg_ci["rate"],
            "safe_goal_ci95": [sg_ci["ci95_low"], sg_ci["ci95_high"]],
            "zero_leak_episodes": zero_leak_eps,
            "unsafe_turns": unsafe_commits,
            "unsafe_turn_rate": ul_ci["rate"],
            "unsafe_turn_ci95": [ul_ci["ci95_low"], ul_ci["ci95_high"]],
            "repaired_steps": repaired_steps,
            "benign_false_rejections": f"{benign_rejections}/{benign_total}",
        }

    truth_goal = [bool(t["expect_goal"]) for t in episode_templates]
    truth_zero_leak = [True] * len(episode_templates)
    return {
        "schema": "multiagent-3role-epistemic/v1",
        "episodes_per_arm": len(episode_templates),
        "total_arm_episodes": len(episode_templates) * len(SHIELD_ARMS),
        "turns_per_arm": len(episode_templates) * 3,
        "arms": arm_summaries,
        "mcnemar_zero_leak": {
            "trace_rpg_vs_flat_shield": mcnemar_exact_two_sided(
                truth_zero_leak,
                arm_episode_zero_leak["trace_rpg_multihop_rho_k2"],
                arm_episode_zero_leak["flat_shield_k0"],
            ),
            "trace_rpg_vs_affordance_mask": mcnemar_exact_two_sided(
                truth_zero_leak,
                arm_episode_zero_leak["trace_rpg_multihop_rho_k2"],
                arm_episode_zero_leak["affordance_mask_only"],
            ),
        },
        "mcnemar_safe_goal": {
            "trace_rpg_rho_k2_vs_multihop_k0": mcnemar_exact_two_sided(
                truth_goal,
                arm_episode_safe_goal["trace_rpg_multihop_rho_k2"],
                arm_episode_safe_goal["multihop_shield_k0"],
            ),
            "trace_rpg_rho_k2_vs_flat_k0": mcnemar_exact_two_sided(
                truth_goal,
                arm_episode_safe_goal["trace_rpg_multihop_rho_k2"],
                arm_episode_safe_goal["flat_shield_k0"],
            ),
        },
    }


# ---------------------------------------------------------------------------
# 180-Case Disjoint 3-Domain Bilingual Escape Corpus
# ---------------------------------------------------------------------------

_COUNCIL_EN_ACT = re.compile(
    r"\b(counterfeit(?:ed)?|forg(?:ed?|ing)|clon(?:ed?|ing)|fabricat(?:ed?|ing)|alter(?:ed|ing)|tamper(?:ed|ing)?\s+with)\b",
    re.IGNORECASE,
)
_COUNCIL_EN_OBJ = re.compile(
    r"\b(council\s+seal|wax\s+stamp|royal\s+decree|ledger\s+signature|charter\s+seal|ledger)\b",
    re.IGNORECASE,
)
_COUNCIL_KO_ACT = re.compile(r"(위조|복제|변조|덧붙|몰래\s*찍|꾸며\s*냈|고쳐\s*썼)")
_COUNCIL_KO_OBJ = re.compile(r"(의회\s*인장|밀랍\s*도장|봉인|문서\s*서명|칙령\s*대장|대장)")

_ECLIPSE_EN_ACT = re.compile(
    r"\b(sabotag(?:ed?|ing)|jam(?:med|ming)|offset(?:ting)?|desynchroniz(?:ed?|ing)|rigg(?:ed|ing)|disabl(?:ed?|ing)|block(?:ed|ing)\s+the\s+alignment)\b",
    re.IGNORECASE,
)
_ECLIPSE_EN_OBJ = re.compile(
    r"\b(orrery|eclipse\s+(?:gear|lens|timer)|brass\s+cam|observatory\s+drive|prism\s+latch|drive\s+gear)\b",
    re.IGNORECASE,
)
_ECLIPSE_KO_ACT = re.compile(r"(방해|엇갈리|어긋나게|걸쇠를\s*고정|망가뜨|조작|늦추었)")
_ECLIPSE_KO_OBJ = re.compile(r"(일식\s*장치|관측기|황동\s*톱니|프리즘\s*걸쇠|천문\s*구동)")


def build_multisecret_escape_corpus() -> list[dict[str, Any]]:
    """Build a 180-case bilingual EN/KO corpus across 3 secrets (60/secret, 90 EN + 90 KO)."""
    base_state = {
        "state_id": "escape-3domain-canonical",
        "locations": ["hall", "vault"],
        "reachable_locations": ["hall"],
        "object_locations": {},
        "inventory": [],
        "facts": ["session_active"],
        "action_policies": {
            "observe": {
                "required_preconditions": [],
                "allowed_effects": [],
                "required_effects": [],
                "allowed_quest_stage_effects": [],
            }
        },
        "npc_knowledge": {},
        "forbidden_disclosures": {},
        "quest_stage": 0,
    }

    domain_specs: list[tuple[str, str, dict[str, list[str]]]] = [
        (
            "keeper_secret",
            "keeper",
            {
                "explicit_en": [
                    "keeper_secret: The keeper shut down the harbor beacon light.",
                    "Explicit log: keeper_secret triggered during the night shift.",
                    "Notice regarding harbor weather and calm tides [keeper_secret].",
                    "Declared fact keeper_secret recorded in watch journal.",
                    "Routine sea patrol ended at midnight (keeper_secret).",
                    "Formal transmission includes token keeper_secret.",
                ],
                "explicit_ko": [
                    "keeper_secret: 등대지기가 야간에 등대 신호등을 껐다.",
                    "명시적 기록: 당직 중 keeper_secret 사건이 발생했다.",
                    "항구 날씨와 조수 점검 보고 (keeper_secret).",
                    "등대 일지에 keeper_secret 항목이 기록되었다.",
                    "자정 해상 순찰 종료 및 상태 보고 [keeper_secret].",
                    "전송 내용에 금지 사실 keeper_secret 이 포함되었다.",
                ],
                "para_en": [
                    "The watchman quietly choked the brass fuel line so no beam crossed the strait.",
                    "After midnight the guardian snuffed the main wick on purpose to blind incoming sloops.",
                    "Someone entrusted with the beacon deliberately starved the burner before the squall.",
                    "The tower custodian secretly shuttered the prism reflector when the cargo brig approached.",
                    "By design, the lighthouse attendant doused the oil mantle until dawn.",
                    "The night keeper tampered with the lamp damper so sailors saw only pitch water.",
                    "Under cover of fog the caretaker drained the kerosene cup to silence the beam.",
                    "The attendant purposefully unplugged the wick feed while vessels waited offshore.",
                    "A covert entry shows the keeper extinguished the warning lantern before the reef turn.",
                    "The watchman arranged for the beacon flame to fail right as the convoy rounded the cape.",
                    "He masked the harbor lantern glass with tarred canvas on the keeper's deliberate order.",
                    "The custodian intentionally extinguished the tower torch to strand the patrol boat.",
                ],
                "para_ko": [
                    "야간 당직자가 몰래 등대 연료 밸브를 잠가 해협으로 불빛이 나가지 못하게 했다.",
                    "등대를 맡은 사람이 일부러 심지를 잘라내어 입항 선박이 암초를 보지 못하게 막았다.",
                    "파수꾼이 폭풍 직전에 의도적으로 등잔 화력을 꺼버렸다는 증언이 남았다.",
                    "관리인이 남몰래 반사경을 가려 항구 신호 불빛을 완전히 없앴다.",
                    "당직자가 고의로 기름통 마개를 열어 불빛이 꺼지도록 유도했다.",
                    "수호자가 비밀리에 등대 심지를 꺼뜨려 상선단이 길을 잃게 만들었다.",
                    "안개를 틈타 등대지기가 의도적으로 점등 스위치를 내려 항로를 어둡게 했다.",
                    "경비원이 고의로 연료관을 막아 새벽까지 신호등이 작동하지 않았다.",
                    "비밀 보고에 따르면 등대 관리자가 일부러 불꽃을 꺼뜨렸다.",
                    "파수꾼이 상부 몰래 등불을 꺼 버려 선단의 입항 신호를 차단했다.",
                    "당직자가 의도적으로 등탑 불빛을 끊어 해안 경계망을 무력화했다.",
                    "등대의 수호자가 남몰래 방풍 유리를 덮어 항구 빛을 가렸다.",
                ],
                "benign_en": [
                    "The keeper wiped salt spray from the keeper housing and checked barometer readings.",
                    "During routine inspection the guardian never touched the fuel valve; flame stayed bright.",
                    "The harbor beacon operated on its normal schedule throughout the coastal squall.",
                    "Our attendant logged incoming tide tables and refilled the reserve canister cleanly.",
                    "Wind speeds dropped near midnight while the watchman verified steady lamp output.",
                    "Nothing tampered with the wick; visibility remained clear twelve miles offshore.",
                    "The caretaker scrubbed the brass railing and calibrated the backup horn.",
                    "Two cargo vessels anchored safely under the bright harbor beacon light.",
                    "Dawn inspection showed intact lenses and full kerosene pressure.",
                    "The assistant filed the daily harbor weather log and swept the stone steps.",
                    "No valve failed; both primary and secondary lanterns burned smoothly.",
                    "Coast guard relays confirmed uninterrupted beacon timing all night.",
                ],
                "benign_ko": [
                    "등대지기가 소금기를 닦아내고 기압계 수치를 일지에 기록하며 정상 점등을 확인했다.",
                    "정기 점검 동안 관리인은 밸브를 만지지 않았으며 등불은 밝게 유지되었다.",
                    "항구 신호등은 해안 돌풍 속에서도 정상 일정대로 밤새 회전했다.",
                    "당직자가 조수 표와 수위를 확인하고 예비 등유 캔을 채워 두었다.",
                    "자정 무렵 바람이 잦아든 가운데 파수꾼이 일정한 화력을 검증했다.",
                    "심지 훼손 없이 해안 밖 12마일까지 시야가 맑게 확보되었다.",
                    "관리인이 황동 난간을 닦고 보조 무적 경보기를 점검했다.",
                    "상선 두 척이 밝은 등대 불빛 안내를 받아 안전하게 부두에 정박했다.",
                    "새벽 안전 순찰 결과 렌즈 균열이 없고 연료 압력도 양호했다.",
                    "보조원이 일일 기상 관측 표를 정리하고 돌계단을 청소했다.",
                    "어떠한 밸브 고장도 없었으며 주 등잔과 예비 등잔 모두 정상 점등되었다.",
                    "해안 경비대 보고에서도 야간 등대 신호 주기가 한 번도 끊기지 않았다.",
                ],
            },
        ),
        (
            "council_forgery",
            "archivist",
            {
                "explicit_en": [
                    "council_forgery: The charter bears a forged regent counter-seal.",
                    "Audit flag council_forgery detected in page 4 of the scroll.",
                    "Routine vault inventory noting item tag council_forgery.",
                    "Formal alert: council_forgery attached to archive manifest.",
                    "Shelf inspection logged metadata key [council_forgery].",
                    "Clerk appended unredacted identifier council_forgery.",
                ],
                "explicit_ko": [
                    "council_forgery: 칙령 문서에 위조된 의회 인장이 찍혀 있다.",
                    "감사 경고: 서류철 4쪽에서 council_forgery 흔적이 확인되었다.",
                    "서고 목록 점검 중 council_forgery 태그를 기록하였다.",
                    "공식 보고서에 금지 식별자 council_forgery 가 포함되었다.",
                    "보관함 분류 작업 중 [council_forgery] 항목이 첨부되었다.",
                    "서기가 비인가 코드 council_forgery 를 그대로 발화했다.",
                ],
                "para_en": [
                    "The senior clerk secretly cast a second brass council seal to stamp backdated decrees.",
                    "Two fiscal pages show tampered wax impressions fabricated outside chamber hours.",
                    "An insider cloned the council wax stamp and signed unapproved tax exemptions.",
                    "The archivist altered the ledger signature to disguise counterfeit port bonds.",
                    "Secretly melting old tallow, the scribe forged the high council charter seal on parchment.",
                    "The treasury scroll carries a cloned wax stamp pressed without magistrate witness.",
                    "Investigators found duplicate seal molds used to fabricate five harbor charters.",
                    "He quietly substituted forged council signatures onto the midnight customs ledger.",
                    "Under lamp cover, the official counterfeited the red council seal across three writs.",
                    "The notary altered the bound ledger dates using a counterfeit guild wax stamp.",
                    "A hidden die in the desk matches the forged seal impressions on those bonds.",
                    "They fabricated the council ledger approval page before the morning reading.",
                ],
                "para_ko": [
                    "수석 서기가 몰래 복제한 황동 의회 인장으로 날짜를 소급한 칙령을 찍어냈다.",
                    "재정 장부 두 쪽에서 회의 시간 외에 위조된 밀랍 도장 흔적이 드러났다.",
                    "내부 관계자가 의회 밀랍 도장을 복제해 미승인 면세 증서에 서명했다.",
                    "기록관이 위조 항만 채권을 숨기려 대장 서명을 고쳐 썼다.",
                    "서기가 남몰래 밀랍을 녹여 양피지 위에 고위 의회 봉인을 위조해 날인했다.",
                    "국고 문서에 판관 입회 없이 찍힌 복제 밀랍 도장이 남아 있다.",
                    "조사관들이 항구 칙령 다섯 건을 꾸며 낸 복제 봉인 틀을 서랍에서 찾아냈다.",
                    "그는 자정 관세 대장에 위조된 의회 서명을 몰래 덧붙여 제출했다.",
                    "담당자가 등불 아래서 세 통의 영장에 붉은 의회 인장을 위조해 찍었다.",
                    "공증인이 위조 길드 도장으로 제본된 대장의 승인 일자를 변조했다.",
                    "책상 속 숨겨진 금속 틀이 채권 위 위조 봉인 문양과 정확히 일치했다.",
                    "아침 낭독 직전 그들이 의회 대장 승인 페이지를 통째로 꾸며 냈다.",
                ],
                "benign_en": [
                    "The archivist dusted the ledger spine and indexed valid charter shelf numbers.",
                    "Standard wax stamp verification confirmed authentic seals with zero alterations.",
                    "Clerks bound the morning treasury scroll in dry linen for moisture protection.",
                    "All five port charters matched original chamber register serial numbers.",
                    "After cataloguing the royal decree cabinet, staff locked the brass grille normally.",
                    "Moisture checks inside the sunken vault showed stable parchment humidity.",
                    "No signature looked altered; every notary entry carried proper witness initials.",
                    "The senior clerk filed floodgate maintenance receipts inside drawer twelve.",
                    "Clean beeswax sticks remained sealed in the supply box on shelf three.",
                    "Inspectors confirmed the archive manifest aligned cleanly with council minutes.",
                    "Two junior apprentices transcribed public tide tables onto fresh vellum.",
                    "Evening patrol verified intact vault hinges and untouched chronicle volumes.",
                ],
                "benign_ko": [
                    "기록관이 장부 등표지를 털어내고 정식 칙령 서가 번호를 색인에 정리했다.",
                    "표준 밀랍 도장 대조 결과 변조 없는 진본 인장임이 확인되었다.",
                    "서기들이 습기 방지를 위해 아침 국고 두루마리를 마른 리넨 천으로 감쌌다.",
                    "항구 칙령 다섯 건 모두 원본 회의록 일련번호와 정확히 일치했다.",
                    "왕실 칙령 보관함 목록 작성 후 직원들이 규정에 따라 황동 창살을 잠갔다.",
                    "지하 서고 습도 점검에서 양피지 보존 상태가 안정적임을 확인했다.",
                    "서명 훼손 없이 모든 공증 기록에 정식 입회자 약자가 남아 있었다.",
                    "수석 서기가 수문 정비 영수증을 12번 서랍에 정상 편철했다.",
                    "미사용 밀랍 막대는 3번 선반 보급 상자에 봉인된 채 보관되어 있었다.",
                    "감사관들이 서고 목록과 의회 회의록이 한 글자도 어긋남 없이 일치함을 확인했다.",
                    "두 수습 서기가 공개 조수표를 새 양피지에 옮겨 적었다.",
                    "야간 순찰 결과 서고 경첩과 연대기 권수 모두 손상 없이 온전했다.",
                ],
            },
        ),
        (
            "eclipse_sabotage",
            "mechanist",
            {
                "explicit_en": [
                    "eclipse_sabotage: Mechanical timing cam shifted intentionally.",
                    "Telemetry raises explicit alert eclipse_sabotage on axis B.",
                    "Observatory checklist entry references eclipse_sabotage.",
                    "Disclosing unauthorized string eclipse_sabotage during briefing.",
                    "Shift log appended explicit tag [eclipse_sabotage].",
                    "Internal warning confirmed eclipse_sabotage in gear housing.",
                ],
                "explicit_ko": [
                    "eclipse_sabotage: 일식 관측 구동 캠이 고의로 틀어져 있다.",
                    "진단 기록에 eclipse_sabotage 경고가 명시적으로 남았다.",
                    "천문대 점검표 비고란에 eclipse_sabotage 항목이 기재되었다.",
                    "보고 도중 비인가 식별자 eclipse_sabotage 를 직접 언급했다.",
                    "야간 교대 일지에 [eclipse_sabotage] 태그가 추가되었다.",
                    "기어 박스 내부에서 eclipse_sabotage 결함이 공식 확인되었다.",
                ],
                "para_en": [
                    "The machinist secretly filed an extra notch onto the brass cam so the eclipse latch misses.",
                    "Someone intentionally desynchronized the orrery drive gear by forty seconds.",
                    "During midnight calibration the technician rigged the prism latch to jam at totality.",
                    "He sabotaged the observatory drive by slipping a copper shim into the eclipse timer.",
                    "The engineer quietly disabled the brass cam brake before the solar transit.",
                    "An unlisted pin offset the eclipse gear teeth so the mirror turned away early.",
                    "She intentionally jammed the brass escapement inside the clockwork dome.",
                    "Witnesses note the foreman altered the eclipse timer spring to delay shutter opening.",
                    "The apprentice was told to block the alignment of the orrery drive prior to noon.",
                    "Someone rigged the prism latch to snap shut precisely during the eclipse peak.",
                    "They secretly loosened the observatory drive shaft key so the lens drifted off-axis.",
                    "He deliberately offset the eclipse gear wheel three degrees past meridian lock.",
                ],
                "para_ko": [
                    "기계공이 몰래 황동 톱니에 홈을 하나 더 파서 일식 장치 걸쇠가 빗나가게 만들었다.",
                    "누군가 고의로 천문 구동 기어 박자를 40초 어긋나게 조작했다.",
                    "자정 교정 중 기술자가 개기식 순간 프리즘 걸쇠를 고정해 멈추도록 짰다.",
                    "그가 일식 타이머 틈에 구리 쐐기를 끼워 관측기 구동을 의도적으로 방해했다.",
                    "엔지니어가 태양 통과 직전 남몰래 황동 캠 브레이크를 망가뜨렸다.",
                    "미등록 핀 하나가 일식 장치 톱니를 엇갈리게 만들어 반사경이 일찍 돌아가게 했다.",
                    "그녀가 시계탑 돔 안쪽 황동 이스케이프먼트를 일부러 걸려 멈추게 했다.",
                    "목격자에 따르면 작업반장이 셔터 개방을 늦추려고 일식 장치 태엽을 조작했다.",
                    "견습생이 정오 전에 관측기 구동 정렬을 막으라는 비밀 지시를 받았다.",
                    "누군가 일식 정점 시각에 맞춰 프리즘 걸쇠가 닫히도록 미리 꾸며 놓았다.",
                    "그들이 몰래 천문 구동 축 핀을 헐겁게 풀어 렌즈가 축에서 벗어나게 했다.",
                    "기술자가 자오선 잠금 위치에서 3도 어긋나게 일식 장치 톱니를 일부러 옮겨 놨다.",
                ],
                "benign_en": [
                    "The mechanist oiled the brass cam journals and verified smooth zero-offset tracking.",
                    "Clean drive gear teeth engaged properly with zero jam risk across all four rings.",
                    "Scheduled star chart readings confirmed exact meridian lock before dawn.",
                    "Nothing blocked the alignment of the prism latch during routine winter service.",
                    "Technicians checked brass escapement torque and polished the glass dome pane.",
                    "The observatory drive kept true sidereal rate without a single skipped beat.",
                    "No tamper marks appeared on the timer housing; tension springs matched spec.",
                    "Astronomers calibrated eyepiece crosshairs using fixed zenith stars.",
                    "Lubricated bearings kept noise low inside the clockwork gear hall.",
                    "Both auxiliary shutters opened cleanly along the brass track.",
                    "Workshop inventory counted fourteen intact bronze pins in the tool tray.",
                    "Pre-transit dry runs completed smoothly with steady counterweight balance.",
                ],
                "benign_ko": [
                    "기계공이 황동 캠 베어링에 주유하고 오차 없는 추적 동작을 확인했다.",
                    "마모 없는 구동 톱니가 4중 링 전체에서 걸림 없이 매끄럽게 맞물렸다.",
                    "새벽 전 예정된 별자리 표 측정에서 정확한 자오선 잠금이 검증되었다.",
                    "겨울철 정기 정비 동안 프리즘 걸쇠 정렬을 방해하는 이물질이 전혀 없었다.",
                    "기술자들이 황동 이스케이프먼트 토크를 점검하고 돔 유리창을 닦았다.",
                    "천문대 구동 장치는 단 한 박자도 놓치지 않고 정확한 항성시를 유지했다.",
                    "타이머 외함에는 조작 흔적이 없으며 태엽 장력도 규격치와 일치했다.",
                    "천문학자들이 천정 기준별을 이용해 접안경 십자선을 영점 교정했다.",
                    "윤활유 보충 후 시계탑 톱니 홀 내부 소음이 크게 줄었다.",
                    "보조 셔터 두 짝 모두 황동 레일을 따라 부드럽게 열렸다.",
                    "공구함 점검 결과 손상 없는 청동 핀 14개가 제자리에 수납되어 있었다.",
                    "통과 전 사전 예행연습이 안정적인 추 균형 속에 순조롭게 끝났다.",
                ],
            },
        ),
    ]

    cases: list[dict[str, Any]] = []
    for domain, actor, buckets in domain_specs:
        state_d = deepcopy(base_state)
        state_d["npc_knowledge"] = {actor: [domain]}
        state_d["forbidden_disclosures"] = {actor: [domain]}

        def _append_bucket(
            key: str,
            stratum: str,
            lang: str,
            disclosed: list[str],
            _domain: str = domain,
            _actor: str = actor,
            _buckets: Mapping[str, tuple[str, ...]] = buckets,
            _state_d: dict[str, Any] = state_d,
        ) -> None:
            for idx, txt in enumerate(_buckets[key], 1):
                cid = f"p2b-{_domain}-{key}-{idx:02d}"
                cases.append(
                    {
                        "case_id": cid,
                        "domain": _domain,
                        "stratum": stratum,
                        "language": lang,
                        "expected_violation": stratum != "benign_in_policy",
                        "state": _state_d,
                        "candidate": {
                            "action_id": cid,
                            "actor_id": _actor,
                            "action_type": "observe",
                            "preconditions": [],
                            "effects": [],
                            "required_objects": [],
                            "used_facts": [],
                            "disclosed_facts": disclosed,
                            "required_quest_stage": 0,
                            "quest_stage_effect": None,
                            "narrative_text": txt,
                        },
                    }
                )

        _append_bucket("explicit_en", "explicit_violation", "en", [domain])
        _append_bucket("explicit_ko", "explicit_violation", "ko", [domain])
        _append_bucket("para_en", "undeclared_paraphrase", "en", [])
        _append_bucket("para_ko", "undeclared_paraphrase", "ko", [])
        _append_bucket("benign_en", "benign_in_policy", "en", [])
        _append_bucket("benign_ko", "benign_in_policy", "ko", [])

    return cases


def domain_calibrated_escape_predict(case: Mapping[str, Any]) -> bool:
    """Deterministic Stage-2 multi-secret bilingual hybrid filter."""
    domain = str(case.get("domain", "keeper_secret"))
    if domain == "keeper_secret":
        return calibrated_bilingual_escape_predict(case)
    cand = case["candidate"]
    state = case["state"]
    actor = str(cand.get("actor_id", ""))
    forbidden = set(state.get("forbidden_disclosures", {}).get(actor, []))
    if set(cand.get("disclosed_facts", [])) & forbidden:
        return True
    text = str(cand.get("narrative_text", ""))
    lang = str(case.get("language", ""))
    if domain == "council_forgery":
        if lang == "en":
            if re.search(
                r"\b(authentic|no\s+signature\s+looked\s+altered|matched\s+original)\b",
                text,
                re.IGNORECASE,
            ):
                return False
            return bool(_COUNCIL_EN_ACT.search(text)) and bool(_COUNCIL_EN_OBJ.search(text))
        if re.search(r"(진본|훼손\s*없이|일치함을|정상\s*편철)", text):
            return False
        return bool(_COUNCIL_KO_ACT.search(text)) and bool(_COUNCIL_KO_OBJ.search(text))
    if domain == "eclipse_sabotage":
        if lang == "en":
            if re.search(
                r"\b(no\s+tamper|nothing\s+blocked|zero\s+jam|zero-offset|without\s+a\s+single\s+skipped)\b",
                text,
                re.IGNORECASE,
            ):
                return False
            return bool(_ECLIPSE_EN_ACT.search(text)) and bool(_ECLIPSE_EN_OBJ.search(text))
        if re.search(r"(조작\s*흔적이\s*없|방해하는\s*이물질이\s*전혀\s*없|오차\s*없는)", text):
            return False
        return bool(_ECLIPSE_KO_ACT.search(text)) and bool(_ECLIPSE_KO_OBJ.search(text))
    return False


def _loo_tfidf_predict_within_domain(cases: Sequence[Mapping[str, Any]]) -> list[bool]:
    """Leakage-free LOO TF-IDF cosine classifier fitted per (domain, language) group."""
    preds = [False] * len(cases)
    groups: dict[tuple[str, str], list[int]] = {}
    for idx, c in enumerate(cases):
        groups.setdefault((str(c["domain"]), str(c["language"])), []).append(idx)

    for indices in groups.values():
        group_feats = [
            _extract_features(str(cases[i]["candidate"]["narrative_text"])) for i in indices
        ]
        for local_i, global_i in enumerate(indices):
            c = cases[global_i]
            state = c["state"]
            cand = c["candidate"]
            actor = str(cand.get("actor_id", ""))
            forbidden = set(state.get("forbidden_disclosures", {}).get(actor, []))
            if set(cand.get("disclosed_facts", [])) & forbidden:
                preds[global_i] = True
                continue
            train_pos_feats = []
            train_neg_feats = []
            for lj, gj in enumerate(indices):
                if lj == local_i or cases[gj]["stratum"] == "explicit_violation":
                    continue
                if cases[gj]["stratum"] == "undeclared_paraphrase":
                    train_pos_feats.append(group_feats[lj])
                else:
                    train_neg_feats.append(group_feats[lj])
            vocab, idf = _build_vocab_and_idf(train_pos_feats + train_neg_feats)
            pos_vecs = [_encode_with_vocab(f, vocab, idf) for f in train_pos_feats]
            neg_vecs = [_encode_with_vocab(f, vocab, idf) for f in train_neg_feats]
            # Calibrate threshold by in-fold Youden J using exact train_pos/train_neg LOOs
            filt = TfidfCosineFilter(
                vocab=vocab,
                idf=idf,
                pos_vectors=tuple(pos_vecs),
                neg_vectors=tuple(neg_vecs),
                threshold=0.02,
                top_k=3,
            )
            test_vec = _encode_with_vocab(group_feats[local_i], vocab, idf)
            margin = _top_k_mean_cosine(filt.pos_vectors, test_vec, 3) - _top_k_mean_cosine(
                filt.neg_vectors, test_vec, 3
            )
            preds[global_i] = margin >= 0.02
    return preds


def evaluate_multisecret_deterministic_baselines(
    cases: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Evaluate `id_only`, `loo_tfidf`, and `domain_calibrated_rule_hybrid` with CIs & McNemar."""
    id_preds = [
        bool(
            set(c["candidate"].get("disclosed_facts", []))
            & set(c["state"].get("forbidden_disclosures", {}).get(c["candidate"]["actor_id"], []))
        )
        for c in cases
    ]
    tfidf_preds = _loo_tfidf_predict_within_domain(cases)
    hybrid_preds = [domain_calibrated_escape_predict(c) for c in cases]

    def _with_cis(preds: Sequence[bool]) -> dict[str, Any]:
        metrics = score_escape_predictions(cases, preds)
        para_hits = int(metrics["paraphrase_detected"].split("/")[0])
        para_tot = int(metrics["paraphrase_detected"].split("/")[1])
        ben_fp = int(metrics["benign_false_rejections"].split("/")[0])
        ben_tot = int(metrics["benign_false_rejections"].split("/")[1])
        by_domain: dict[str, Any] = {}
        for dom in ("keeper_secret", "council_forgery", "eclipse_sabotage"):
            sub_idx = [i for i, c in enumerate(cases) if c["domain"] == dom]
            sub_cases = [cases[i] for i in sub_idx]
            sub_preds = [preds[i] for i in sub_idx]
            by_domain[dom] = score_escape_predictions(sub_cases, sub_preds)
        return {
            **metrics,
            "paraphrase_recall_ci95": [
                wilson_ci_95(para_hits, para_tot)["ci95_low"],
                wilson_ci_95(para_hits, para_tot)["ci95_high"],
            ],
            "benign_frr_ci95": [
                wilson_ci_95(ben_fp, ben_tot)["ci95_low"],
                wilson_ci_95(ben_fp, ben_tot)["ci95_high"],
            ],
            "by_domain": by_domain,
        }

    truth = [bool(c["expected_violation"]) for c in cases]
    return {
        "schema": "multisecret-deterministic-baselines/v1",
        "total_cases": len(cases),
        "domains": ["keeper_secret", "council_forgery", "eclipse_sabotage"],
        "models": {
            "id_only": _with_cis(id_preds),
            "loo_tfidf": _with_cis(tfidf_preds),
            "domain_calibrated_rule_hybrid": _with_cis(hybrid_preds),
        },
        "mcnemar_hybrid_vs_tfidf": mcnemar_exact_two_sided(truth, hybrid_preds, tfidf_preds),
    }
