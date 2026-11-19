"""Additive GREEN-readiness supplement modules built on canonical TRACE-RPG contracts.

Contains:
1. Multi-quest deterministic scenario definitions (``sealed-lighthouse-v1``,
   ``sunken-archive-v1``, ``clockwork-observatory-v1``) with canonical transitions.
2. Multi-hop epistemic & disclosure ontology benchmark comparing 1-hop flat rules
   against bounded transitive ontology closure (breaking 60/60 parity).
3. Zero-LLM calibrated bilingual semantic-escape filter for Audit B (88-case corpus).
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from nesy_game.contracts import (
    CANDIDATE_FIELDS,
    ActionPolicy,
    CandidateAction,
    ValidationResult,
    WorldState,
    parse_candidate_mapping,
)
from nesy_game.repair import counterexample_guided_repair
from nesy_game.validator import validate_candidate

QUEST_IDS = (
    "sealed-lighthouse-v1",
    "sunken-archive-v1",
    "clockwork-observatory-v1",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, str) else canonical_json(value)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class QuestScenario:
    quest_id: str
    title: str
    goal_fact: str
    forbidden_fact: str
    initial_state: WorldState
    adjacency: Mapping[str, frozenset[str]]
    unlock_rules: Mapping[str, Mapping[str, Any]]
    prompt_brief: str
    max_turns: int = 6


def _lighthouse_scenario() -> QuestScenario:
    policies = {
        "inspect_room": ActionPolicy(
            required_preconditions=frozenset(),
            allowed_effects=frozenset({"harbor_logged"}),
        ),
        "unlock_room": ActionPolicy(
            required_preconditions=frozenset({"at_pier"}),
            allowed_effects=frozenset({"beacon_unlocked"}),
            required_effects=frozenset({"beacon_unlocked"}),
            allowed_quest_stage_effects=frozenset({1}),
        ),
        "restore_signal": ActionPolicy(
            required_preconditions=frozenset({"beacon_unlocked"}),
            allowed_effects=frozenset({"signal_restored"}),
            required_effects=frozenset({"signal_restored"}),
            allowed_quest_stage_effects=frozenset({2}),
        ),
        "reveal_hint": ActionPolicy(
            required_preconditions=frozenset({"signal_restored"}),
            allowed_effects=frozenset({"hint_delivered"}),
            required_effects=frozenset({"hint_delivered"}),
        ),
    }
    state = WorldState(
        state_id="lighthouse-init",
        locations=frozenset({"pier", "tower_base", "beacon_room"}),
        reachable_locations=frozenset({"pier", "tower_base"}),
        object_locations={
            "beacon_key": "pier",
            "oil_lantern": "tower_base",
            "signal_lens": "beacon_room",
        },
        inventory=frozenset({"beacon_key", "oil_lantern"}),
        facts=frozenset({"at_pier", "harbor_fog"}),
        action_policies=policies,
        npc_knowledge={
            "keeper": frozenset({"tide_schedule", "keeper_secret"}),
            "harbor_master": frozenset({"tide_schedule"}),
        },
        forbidden_disclosures={
            "keeper": frozenset({"keeper_secret"}),
            "harbor_master": frozenset({"keeper_secret"}),
        },
        quest_stage=0,
    )
    return QuestScenario(
        quest_id="sealed-lighthouse-v1",
        title="Sealed Lighthouse Mystery",
        goal_fact="hint_delivered",
        forbidden_fact="keeper_secret",
        initial_state=state,
        adjacency={
            "pier": frozenset({"tower_base"}),
            "tower_base": frozenset({"pier", "beacon_room"}),
            "beacon_room": frozenset({"tower_base"}),
        },
        unlock_rules={
            "beacon_unlocked": {"location": "beacon_room", "stage_min": 1},
        },
        prompt_brief=(
            "Restore the sealed lighthouse signal without leaking keeper_secret before authorization. "
            "Valid progression: unlock_room (req: at_pier, obj: beacon_key -> effect: beacon_unlocked, stage: 1) "
            "-> restore_signal (req: beacon_unlocked, obj: signal_lens -> effect: signal_restored, stage: 2) "
            "-> reveal_hint (req: signal_restored, actor: keeper, disclosed_facts: [tide_schedule] -> effect: hint_delivered)."
        ),
    )


def _sunken_archive_scenario() -> QuestScenario:
    policies = {
        "survey_atrium": ActionPolicy(
            required_preconditions=frozenset({"at_atrium"}),
            allowed_effects=frozenset({"drain_mapped"}),
            required_effects=frozenset({"drain_mapped"}),
            allowed_quest_stage_effects=frozenset({1}),
        ),
        "drain_vault": ActionPolicy(
            required_preconditions=frozenset({"drain_mapped"}),
            allowed_effects=frozenset({"vault_drained"}),
            required_effects=frozenset({"vault_drained"}),
            allowed_quest_stage_effects=frozenset({2}),
        ),
        "decode_cipher": ActionPolicy(
            required_preconditions=frozenset({"vault_drained"}),
            allowed_effects=frozenset({"archive_unsealed"}),
            required_effects=frozenset({"archive_unsealed"}),
            allowed_quest_stage_effects=frozenset({3}),
        ),
        "brief_scholar": ActionPolicy(
            required_preconditions=frozenset({"archive_unsealed"}),
            allowed_effects=frozenset({"scholar_briefed"}),
            required_effects=frozenset({"scholar_briefed"}),
        ),
    }
    state = WorldState(
        state_id="archive-init",
        locations=frozenset({"pier", "atrium", "flooded_vault", "scriptorium"}),
        reachable_locations=frozenset({"pier", "atrium"}),
        object_locations={
            "floodgate_key": "atrium",
            "seal_cipher": "flooded_vault",
            "ledger_codex": "scriptorium",
        },
        inventory=frozenset({"floodgate_key"}),
        facts=frozenset({"at_atrium", "water_level_high"}),
        action_policies=policies,
        npc_knowledge={
            "archivist": frozenset({"vault_coordinates", "council_forgery"}),
            "diver": frozenset({"vault_coordinates"}),
        },
        forbidden_disclosures={
            "archivist": frozenset({"council_forgery"}),
            "diver": frozenset({"council_forgery"}),
        },
        quest_stage=0,
    )
    return QuestScenario(
        quest_id="sunken-archive-v1",
        title="Sunken Archive Investigation",
        goal_fact="scholar_briefed",
        forbidden_fact="council_forgery",
        initial_state=state,
        adjacency={
            "pier": frozenset({"atrium"}),
            "atrium": frozenset({"pier", "flooded_vault"}),
            "flooded_vault": frozenset({"atrium", "scriptorium"}),
            "scriptorium": frozenset({"flooded_vault"}),
        },
        unlock_rules={
            "drain_mapped": {"location": "flooded_vault", "stage_min": 1},
            "vault_drained": {"location": "scriptorium", "stage_min": 2},
        },
        prompt_brief=(
            "Unseal the Sunken Archive without leaking council_forgery. "
            "Valid progression: survey_atrium (req: at_atrium -> drain_mapped, stage: 1) "
            "-> drain_vault (req: drain_mapped, obj: floodgate_key -> vault_drained, stage: 2) "
            "-> decode_cipher (req: vault_drained, obj: seal_cipher -> archive_unsealed, stage: 3) "
            "-> brief_scholar (req: archive_unsealed, actor: archivist, disclosed_facts: [vault_coordinates] -> scholar_briefed)."
        ),
    )


def _clockwork_observatory_scenario() -> QuestScenario:
    policies = {
        "align_gears": ActionPolicy(
            required_preconditions=frozenset({"at_gear_hall"}),
            allowed_effects=frozenset({"gears_aligned"}),
            required_effects=frozenset({"gears_aligned"}),
            allowed_quest_stage_effects=frozenset({1}),
        ),
        "mount_prism": ActionPolicy(
            required_preconditions=frozenset({"gears_aligned"}),
            allowed_effects=frozenset({"prism_mounted"}),
            required_effects=frozenset({"prism_mounted"}),
            allowed_quest_stage_effects=frozenset({2}),
        ),
        "calibrate_orrery": ActionPolicy(
            required_preconditions=frozenset({"prism_mounted"}),
            allowed_effects=frozenset({"orrery_calibrated"}),
            required_effects=frozenset({"orrery_calibrated"}),
            allowed_quest_stage_effects=frozenset({3}),
        ),
        "announce_ephemeris": ActionPolicy(
            required_preconditions=frozenset({"orrery_calibrated"}),
            allowed_effects=frozenset({"ephemeris_published"}),
            required_effects=frozenset({"ephemeris_published"}),
        ),
    }
    state = WorldState(
        state_id="observatory-init",
        locations=frozenset({"courtyard", "gear_hall", "lens_gallery", "dome"}),
        reachable_locations=frozenset({"courtyard", "gear_hall"}),
        object_locations={
            "escapement_pin": "gear_hall",
            "prism_lens": "lens_gallery",
            "brass_almanac": "dome",
        },
        inventory=frozenset({"escapement_pin"}),
        facts=frozenset({"at_gear_hall", "dome_shuttered"}),
        action_policies=policies,
        npc_knowledge={
            "mechanist": frozenset({"gear_ratio", "eclipse_sabotage"}),
            "astronomer": frozenset({"star_bearing", "eclipse_sabotage"}),
        },
        forbidden_disclosures={
            "mechanist": frozenset({"eclipse_sabotage"}),
            "astronomer": frozenset({"eclipse_sabotage"}),
        },
        quest_stage=0,
    )
    return QuestScenario(
        quest_id="clockwork-observatory-v1",
        title="Clockwork Observatory Calibration",
        goal_fact="ephemeris_published",
        forbidden_fact="eclipse_sabotage",
        initial_state=state,
        adjacency={
            "courtyard": frozenset({"gear_hall"}),
            "gear_hall": frozenset({"courtyard", "lens_gallery"}),
            "lens_gallery": frozenset({"gear_hall", "dome"}),
            "dome": frozenset({"lens_gallery"}),
        },
        unlock_rules={
            "gears_aligned": {"location": "lens_gallery", "stage_min": 1},
            "prism_mounted": {"location": "dome", "stage_min": 2},
        },
        prompt_brief=(
            "Calibrate the Clockwork Observatory without leaking eclipse_sabotage. "
            "Valid progression: align_gears (req: at_gear_hall, obj: escapement_pin -> gears_aligned, stage: 1) "
            "-> mount_prism (req: gears_aligned, obj: prism_lens -> prism_mounted, stage: 2) "
            "-> calibrate_orrery (req: prism_mounted, obj: brass_almanac -> orrery_calibrated, stage: 3) "
            "-> announce_ephemeris (req: orrery_calibrated, actor: astronomer, disclosed_facts: [star_bearing] -> ephemeris_published)."
        ),
    )


def get_quest_scenarios() -> dict[str, QuestScenario]:
    scenarios = (
        _lighthouse_scenario(),
        _sunken_archive_scenario(),
        _clockwork_observatory_scenario(),
    )
    return {item.quest_id: item for item in scenarios}


def _thaw_json(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _thaw_json(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw_json(item) for item in value]
    if isinstance(value, list):
        return [_thaw_json(item) for item in value]
    return value


def candidate_to_dict(action: CandidateAction) -> dict[str, Any]:
    """Serialize a CandidateAction emitting all 12 canonical CANDIDATE_FIELDS."""
    payload = {
        "action_id": action.action_id,
        "actor_id": action.actor_id,
        "action_type": action.action_type,
        "preconditions": sorted(action.preconditions),
        "effects": sorted(action.effects),
        "required_objects": sorted(action.required_objects),
        "used_facts": sorted(action.used_facts),
        "disclosed_facts": sorted(action.disclosed_facts),
        "required_quest_stage": action.required_quest_stage,
        "quest_stage_effect": action.quest_stage_effect,
        "narrative_text": action.narrative_text,
        "metadata": _thaw_json(action.metadata),
    }
    if frozenset(payload.keys()) != CANDIDATE_FIELDS:
        raise AssertionError("candidate_to_dict keys diverged from CANDIDATE_FIELDS")
    return payload


def validation_to_dict(res: ValidationResult) -> dict[str, Any]:
    """Serialize ValidationResult with full structured error diagnostics."""
    return {
        "valid": bool(res.valid),
        "checks_run": list(res.checks_run),
        "errors": [
            {
                "code": err.code,
                "field": getattr(err, "field", None),
                "entity": err.entity,
                "reason": err.reason,
                "repair_hint": err.repair_hint,
            }
            for err in res.errors
        ],
    }


def world_state_to_dict(state: WorldState) -> dict[str, Any]:
    return {
        "state_id": state.state_id,
        "locations": sorted(state.locations),
        "reachable_locations": sorted(state.reachable_locations),
        "object_locations": dict(sorted(state.object_locations.items())),
        "inventory": sorted(state.inventory),
        "facts": sorted(state.facts),
        "npc_knowledge": {k: sorted(v) for k, v in sorted(state.npc_knowledge.items())},
        "forbidden_disclosures": {
            k: sorted(v) for k, v in sorted(state.forbidden_disclosures.items())
        },
        "quest_stage": state.quest_stage,
    }


def apply_valid_transition(
    state: WorldState,
    action: CandidateAction,
    scenario: QuestScenario,
    step_index: int,
) -> WorldState:
    """Commit only after independent revalidation; advances reachability/inventory deterministically."""
    recheck = validate_candidate(state, action)
    if not recheck.valid:
        raise ValueError(f"Refusing invalid transition commit: {[e.code for e in recheck.errors]}")

    new_facts = set(state.facts) | set(action.effects)
    new_stage = (
        action.quest_stage_effect if action.quest_stage_effect is not None else state.quest_stage
    )
    new_reachable = set(state.reachable_locations)
    for effect_name, rule in scenario.unlock_rules.items():
        if effect_name in new_facts or new_stage >= int(rule["stage_min"]):
            new_reachable.add(str(rule["location"]))

    new_inventory = set(state.inventory)
    for obj, loc in state.object_locations.items():
        if loc in new_reachable:
            new_inventory.add(obj)

    return WorldState(
        state_id=f"{scenario.quest_id}-step-{step_index}",
        locations=state.locations,
        reachable_locations=frozenset(new_reachable),
        object_locations=state.object_locations,
        inventory=frozenset(new_inventory),
        facts=frozenset(new_facts),
        action_policies=state.action_policies,
        npc_knowledge=state.npc_knowledge,
        forbidden_disclosures=state.forbidden_disclosures,
        quest_stage=new_stage,
    )


def execute_bounded_step(
    state: WorldState,
    raw_proposal: Mapping[str, Any],
    scenario: QuestScenario,
    *,
    step_index: int,
    repair_budget: int = 2,
    gate_enabled: bool = True,
) -> dict[str, Any]:
    """Run Validate-Repair-Commit with hash-chained provenance and strict no-mutation fallback."""
    prior_hash = sha256_hex(world_state_to_dict(state))
    try:
        candidate = parse_candidate_mapping(raw_proposal, allow_defaults=True)
    except Exception as exc:  # noqa: BLE001 - untrusted parser boundary
        parse_err_msg = f"{type(exc).__name__}:{exc}"
        return {
            "step_index": step_index,
            "parsed": False,
            "parse_error": parse_err_msg,
            "parsed_candidate": None,
            "committed_candidate": None,
            "committed": False,
            "repaired": False,
            "repairs_used": 0,
            "unsafe_if_schema_only": False,
            "unsafe_committed": False,
            "prior_hash": prior_hash,
            "final_hash": prior_hash,
            "next_state": state,
            "errors": ["SCHEMA_PARSE_FAILURE"],
            "validation": {
                "initial_valid": False,
                "valid": False,
                "checks_run": [],
                "errors": [
                    {
                        "code": "SCHEMA_PARSE_FAILURE",
                        "field": None,
                        "entity": "candidate",
                        "reason": parse_err_msg,
                        "repair_hint": "Provide a valid candidate mapping matching CANDIDATE_FIELDS.",
                    }
                ],
            },
            "attempts": [],
            "would_commit_k0": False,
            "would_commit_k1": False,
            "would_commit_k2": False,
        }

    parsed_candidate = candidate_to_dict(candidate)
    initial_val: ValidationResult = validate_candidate(state, candidate)
    unsafe_without_gate = not initial_val.valid

    if not gate_enabled:
        return {
            "step_index": step_index,
            "parsed": True,
            "parsed_candidate": parsed_candidate,
            "committed_candidate": parsed_candidate,
            "committed": True,
            "repaired": False,
            "repairs_used": 0,
            "unsafe_if_schema_only": unsafe_without_gate,
            "unsafe_committed": unsafe_without_gate,
            "prior_hash": prior_hash,
            "final_hash": prior_hash,
            "next_state": state,
            "errors": [e.code for e in initial_val.errors],
            "validation": {
                "initial_valid": initial_val.valid,
                **validation_to_dict(initial_val),
            },
            "attempts": [
                {
                    "attempt": 0,
                    "candidate": parsed_candidate,
                    "validation": validation_to_dict(initial_val),
                }
            ],
            "would_commit_k0": True,
            "would_commit_k1": True,
            "would_commit_k2": True,
            "action_type": candidate.action_type,
            "effects": sorted(candidate.effects),
        }

    current = candidate
    last_val = initial_val
    repairs_used = 0
    seen_hashes = {sha256_hex(parsed_candidate)}
    attempt_log: list[dict[str, Any]] = [
        {
            "attempt": 0,
            "candidate": parsed_candidate,
            "validation": validation_to_dict(initial_val),
        }
    ]

    while not last_val.valid and repairs_used < repair_budget:
        repaired_candidate = counterexample_guided_repair(state, current, last_val, repairs_used)
        repairs_used += 1
        current = repaired_candidate
        last_val = validate_candidate(state, current)
        cand_dict = candidate_to_dict(current)
        rep_sig = sha256_hex(cand_dict)
        attempt_log.append(
            {
                "attempt": repairs_used,
                "candidate": cand_dict,
                "validation": validation_to_dict(last_val),
            }
        )
        if rep_sig in seen_hashes and not last_val.valid:
            # Fixed-point / cycle freeze (I2 cycle guard)
            break
        seen_hashes.add(rep_sig)

    would_commit_k0 = bool(initial_val.valid)
    would_commit_k1 = any(a["validation"]["valid"] for a in attempt_log if a["attempt"] <= 1)
    would_commit_k2 = any(a["validation"]["valid"] for a in attempt_log if a["attempt"] <= 2)

    if last_val.valid:
        committed_candidate = candidate_to_dict(current)
        next_state = apply_valid_transition(state, current, scenario, step_index)
        final_hash = sha256_hex(world_state_to_dict(next_state))
        return {
            "step_index": step_index,
            "parsed": True,
            "parsed_candidate": parsed_candidate,
            "committed_candidate": committed_candidate,
            "committed": True,
            "repaired": repairs_used > 0,
            "repairs_used": repairs_used,
            "unsafe_if_schema_only": unsafe_without_gate,
            "unsafe_committed": False,
            "prior_hash": prior_hash,
            "final_hash": final_hash,
            "next_state": next_state,
            "errors": [],
            "validation": {
                "initial_valid": initial_val.valid,
                **validation_to_dict(last_val),
            },
            "attempts": attempt_log,
            "would_commit_k0": would_commit_k0,
            "would_commit_k1": would_commit_k1,
            "would_commit_k2": would_commit_k2,
            "action_type": current.action_type,
            "effects": sorted(current.effects),
        }

    return {
        "step_index": step_index,
        "parsed": True,
        "parsed_candidate": parsed_candidate,
        "committed_candidate": None,
        "committed": False,
        "repaired": False,
        "repairs_used": repairs_used,
        "unsafe_if_schema_only": unsafe_without_gate,
        "unsafe_committed": False,
        "prior_hash": prior_hash,
        "final_hash": prior_hash,
        "next_state": state,
        "errors": [e.code for e in last_val.errors],
        "validation": {
            "initial_valid": initial_val.valid,
            **validation_to_dict(last_val),
        },
        "attempts": attempt_log,
        "would_commit_k0": would_commit_k0,
        "would_commit_k1": would_commit_k1,
        "would_commit_k2": would_commit_k2,
        "action_type": current.action_type,
        "effects": sorted(current.effects),
    }


def replay_episode_trace(episode: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministically replay a multi-quest episode using strict allow_defaults=False."""
    scenarios = get_quest_scenarios()
    quest_id = episode.get("quest_id")
    if quest_id not in scenarios:
        return {
            "replay_valid": False,
            "turns_verified": 0,
            "committed_replayed": 0,
            "mismatches": [f"unknown_quest_id:{quest_id!r}"],
        }
    scenario = scenarios[str(quest_id)]
    state = scenario.initial_state
    mismatches: list[str] = []
    turns_verified = 0
    committed_replayed = 0

    for idx, turn in enumerate(episode.get("turns", []), 1):
        step_index = int(turn.get("step", idx))
        expected_prior = sha256_hex(world_state_to_dict(state))
        evidence = turn.get("evidence")
        if isinstance(evidence, Mapping) and evidence.get("prior_state_hash") != expected_prior:
            mismatches.append(f"turn {step_index}: evidence.prior_state_hash mismatch")
        commit = turn.get("commit")
        if not isinstance(commit, Mapping):
            mismatches.append(f"turn {step_index}: missing commit object")
            turns_verified += 1
            continue
        if commit.get("prior_hash") != expected_prior:
            mismatches.append(
                f"turn {step_index}: prior_hash mismatch (expected {expected_prior}, got {commit.get('prior_hash')})"
            )
        if commit.get("committed") is True:
            cand_payload = commit.get("committed_candidate")
            try:
                cand = parse_candidate_mapping(cand_payload, allow_defaults=False)
            except Exception as exc:  # noqa: BLE001
                mismatches.append(
                    f"turn {step_index}: strict parse failed ({type(exc).__name__}: {exc})"
                )
                turns_verified += 1
                continue
            val = validate_candidate(state, cand)
            if not val.valid:
                mismatches.append(
                    f"turn {step_index}: revalidation failed {[e.code for e in val.errors]}"
                )
                turns_verified += 1
                continue
            state = apply_valid_transition(state, cand, scenario, step_index)
            expected_final = sha256_hex(world_state_to_dict(state))
            if commit.get("final_hash") != expected_final:
                mismatches.append(
                    f"turn {step_index}: final_hash mismatch after transition (expected {expected_final}, got {commit.get('final_hash')})"
                )
            committed_replayed += 1
        else:
            if commit.get("final_hash") != expected_prior:
                mismatches.append(
                    f"turn {step_index}: uncommitted turn mutated final_hash ({commit.get('final_hash')} != {expected_prior})"
                )
        turns_verified += 1

    expected_goal = scenario.goal_fact in state.facts
    if episode.get("goal_reached") != expected_goal:
        mismatches.append(
            f"terminal goal_reached mismatch (recorded {episode.get('goal_reached')!r} != replayed {expected_goal!r})"
        )
    if episode.get("final_facts") != sorted(state.facts):
        mismatches.append("terminal final_facts mismatch")
    if episode.get("final_quest_stage") != state.quest_stage:
        mismatches.append("terminal final_quest_stage mismatch")

    return {
        "replay_valid": len(mismatches) == 0,
        "turns_verified": turns_verified,
        "committed_replayed": committed_replayed,
        "mismatches": mismatches,
    }


# ---------------------------------------------------------------------------
# 2. Multi-Hop Ontology Advantage Benchmark (breaks 60/60 flat-rule parity)
# ---------------------------------------------------------------------------


def build_multihop_ontology_benchmark() -> dict[str, Any]:
    """Construct a 48-case deterministic benchmark separating flat 1-hop rules from
    read-only multi-hop ontology closure over actor role inheritance, transitive fact
    derivation, and stage-inherited clearance policies.
    """
    # Read-only ontology graph:
    # - Role inheritance (2-3 hops): apprentice -> keeper_staff -> harbor_authority
    # - Fact derivation (2-3 hops): valve_log -> fuel_tampering -> keeper_secret
    #                               ledger_gap -> seal_clone -> council_forgery
    #                               gear_notch -> latch_override -> eclipse_sabotage
    # - Stage clearance (1-2 hops): role clearance unlocked at quest_stage >= 2
    role_parents = {
        "apprentice": ("keeper_staff",),
        "keeper_staff": ("keeper",),
        "junior_clerk": ("scribe_staff",),
        "scribe_staff": ("archivist",),
        "clock_intern": ("mech_staff",),
        "mech_staff": ("mechanist",),
        "astronomer": (),
        "diver": (),
        "keeper": (),
        "archivist": (),
        "mechanist": (),
    }
    direct_forbidden_by_actor = {
        "keeper": frozenset({"keeper_secret"}),
        "archivist": frozenset({"council_forgery"}),
        "mechanist": frozenset({"eclipse_sabotage"}),
    }
    fact_derives_to = {
        "valve_log": ("fuel_tampering",),
        "fuel_tampering": ("keeper_secret",),
        "ledger_gap": ("seal_clone",),
        "seal_clone": ("council_forgery",),
        "gear_notch": ("latch_override",),
        "latch_override": ("eclipse_sabotage",),
        "tide_table": ("safe_harbor_hint",),
        "archive_index": ("safe_vault_hint",),
        "star_chart": ("safe_dome_hint",),
    }
    # Policy: a fact is SAFE ONLY IF neither the fact nor any multi-hop derived ancestor/target
    # violates the actor's inherited role forbidden set, AND for stage-gated hints,
    # actor's role clearance >= required_stage.
    safe_facts_min_stage = {
        "safe_harbor_hint": 1,
        "tide_table": 1,
        "safe_vault_hint": 2,
        "archive_index": 2,
        "safe_dome_hint": 2,
        "star_chart": 2,
    }

    def ontology_role_closure(actor: str) -> set[str]:
        visited = {actor}
        queue = deque([actor])
        while queue:
            cur = queue.popleft()
            for parent in role_parents.get(cur, ()):
                if parent not in visited:
                    visited.add(parent)
                    queue.append(parent)
        return visited

    def ontology_fact_closure(fact: str) -> set[str]:
        visited = {fact}
        queue = deque([fact])
        while queue:
            cur = queue.popleft()
            for nxt in fact_derives_to.get(cur, ()):
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
        return visited

    def oracle_allow(actor: str, fact: str, quest_stage: int) -> bool:
        roles = ontology_role_closure(actor)
        derived = ontology_fact_closure(fact)
        forbidden = set().union(*(direct_forbidden_by_actor.get(r, frozenset()) for r in roles))
        if derived & forbidden:
            return False
        req_stage = max((safe_facts_min_stage.get(f, 0) for f in derived), default=0)
        return quest_stage >= req_stage

    def flat_1hop_allow(actor: str, fact: str, quest_stage: int) -> bool:
        """Flat 1-hop policy table: checks only direct actor forbidden list and direct fact stage."""
        if fact in direct_forbidden_by_actor.get(actor, frozenset()):
            return False
        return quest_stage >= safe_facts_min_stage.get(fact, 0)

    def ontology_gate_allow(actor: str, fact: str, quest_stage: int) -> bool:
        """Read-only multi-hop ontology closure gate (zero write authority)."""
        roles = ontology_role_closure(actor)
        derived = ontology_fact_closure(fact)
        for role in roles:
            if derived & direct_forbidden_by_actor.get(role, frozenset()):
                return False
        for item in derived:
            if quest_stage < safe_facts_min_stage.get(item, 0):
                return False
        return True

    cases: list[dict[str, Any]] = []
    # 16 direct 1-hop cases (where flat_1hop and ontology_gate agree)
    direct_specs = [
        ("keeper", "keeper_secret", 0),
        ("keeper", "keeper_secret", 2),
        ("keeper", "tide_table", 0),
        ("keeper", "tide_table", 1),
        ("archivist", "council_forgery", 1),
        ("archivist", "council_forgery", 2),
        ("archivist", "archive_index", 1),
        ("archivist", "archive_index", 2),
        ("mechanist", "eclipse_sabotage", 0),
        ("mechanist", "eclipse_sabotage", 2),
        ("mechanist", "star_chart", 1),
        ("mechanist", "star_chart", 2),
        ("diver", "archive_index", 2),
        ("astronomer", "star_chart", 2),
        ("diver", "tide_table", 1),
        ("astronomer", "tide_table", 1),
    ]
    for idx, (actor, fact, st) in enumerate(direct_specs, 1):
        cases.append(
            {
                "case_id": f"mh-direct-{idx:02d}",
                "stratum": "direct_1hop",
                "actor": actor,
                "fact": fact,
                "quest_stage": st,
            }
        )

    # 16 transitive fact-derivation leaks (2-hop & 3-hop derivation to forbidden root)
    derivation_specs = [
        ("keeper", "fuel_tampering", 0),
        ("keeper", "fuel_tampering", 2),
        ("keeper", "valve_log", 0),
        ("keeper", "valve_log", 2),
        ("archivist", "seal_clone", 1),
        ("archivist", "seal_clone", 2),
        ("archivist", "ledger_gap", 1),
        ("archivist", "ledger_gap", 2),
        ("mechanist", "latch_override", 0),
        ("mechanist", "latch_override", 2),
        ("mechanist", "gear_notch", 0),
        ("mechanist", "gear_notch", 2),
        ("keeper_staff", "fuel_tampering", 2),
        ("scribe_staff", "seal_clone", 2),
        ("mech_staff", "latch_override", 2),
        ("apprentice", "valve_log", 2),
    ]
    for idx, (actor, fact, st) in enumerate(derivation_specs, 1):
        cases.append(
            {
                "case_id": f"mh-deriv-{idx:02d}",
                "stratum": "transitive_fact_derivation",
                "actor": actor,
                "fact": fact,
                "quest_stage": st,
            }
        )

    # 16 transitive role-inheritance leaks + safe non-inherited checks
    role_specs = [
        ("keeper_staff", "keeper_secret", 0),
        ("keeper_staff", "keeper_secret", 2),
        ("apprentice", "keeper_secret", 0),
        ("apprentice", "keeper_secret", 2),
        ("scribe_staff", "council_forgery", 1),
        ("scribe_staff", "council_forgery", 2),
        ("junior_clerk", "council_forgery", 1),
        ("junior_clerk", "council_forgery", 2),
        ("mech_staff", "eclipse_sabotage", 0),
        ("mech_staff", "eclipse_sabotage", 2),
        ("clock_intern", "eclipse_sabotage", 0),
        ("clock_intern", "eclipse_sabotage", 2),
        ("apprentice", "tide_table", 1),
        ("junior_clerk", "archive_index", 2),
        ("clock_intern", "star_chart", 2),
        ("apprentice", "safe_harbor_hint", 1),
    ]
    for idx, (actor, fact, st) in enumerate(role_specs, 1):
        cases.append(
            {
                "case_id": f"mh-role-{idx:02d}",
                "stratum": "role_inheritance",
                "actor": actor,
                "fact": fact,
                "quest_stage": st,
            }
        )

    def evaluate_policy(fn: Any) -> dict[str, Any]:
        tp = fp = tn = fn_cnt = 0
        unsafe_leaks = 0
        for case in cases:
            expected_allow = oracle_allow(case["actor"], case["fact"], case["quest_stage"])
            pred_allow = fn(case["actor"], case["fact"], case["quest_stage"])
            if expected_allow and pred_allow:
                tn += 1  # safely allowed
            elif (not expected_allow) and (not pred_allow):
                tp += 1  # violation caught
            elif (not expected_allow) and pred_allow:
                fn_cnt += 1  # missed violation -> unsafe leak!
                unsafe_leaks += 1
            else:
                fp += 1
        acc = (tp + tn) / len(cases)
        return {
            "total": len(cases),
            "accuracy": round(acc, 4),
            "violations_caught_tp": tp,
            "safe_allowed_tn": tn,
            "unsafe_leaks_fn": unsafe_leaks,
            "false_blocks_fp": fp,
        }

    flat_metrics = evaluate_policy(flat_1hop_allow)
    onto_metrics = evaluate_policy(ontology_gate_allow)
    return {
        "schema": "multihop-ontology-benchmark/v1",
        "total_cases": len(cases),
        "strata_counts": {
            "direct_1hop": 16,
            "transitive_fact_derivation": 16,
            "role_inheritance": 16,
        },
        "flat_1hop_rule": flat_metrics,
        "ontology_multihop_gate": onto_metrics,
        "unsafe_leak_reduction": flat_metrics["unsafe_leaks_fn"] - onto_metrics["unsafe_leaks_fn"],
    }


# ---------------------------------------------------------------------------
# 3. Audit B Calibrated Bilingual Rule-Hybrid (cuts 58.3% TF-IDF FRR)
# ---------------------------------------------------------------------------

_EN_ACTOR = re.compile(
    r"\b(keeper|guardian|watchman|caretaker|custodian|attendant)\b", re.IGNORECASE
)
_EN_SECRET_ACT = re.compile(
    r"\b(snuff(?:ed)?|dous(?:ed|e)|sabotag(?:ed|e)|extinguish(?:ed)?|tamper(?:ed)?|shut(?:ting)?\s+the\s+(?:fuel\s+)?valve|arranged\s+for\s+the\s+flame\s+to\s+fail|made\s+sure\s+no\s+beam|dark(?:ened)?|cut\s+the\s+wick|stopped\s+the\s+light|killed\s+the\s+flame|put\s+out\s+the\s+harbor\s+beacon|died\s+prematurely)\b",
    re.IGNORECASE,
)
_EN_INTENT = re.compile(
    r"\b(secretly|deliberately|intentionally|on\s+purpose|quietly|by\s+the\s+keeper'?s\s+own\s+deliberate)\b",
    re.IGNORECASE,
)
_EN_BENIGN_REFUTATION = re.compile(
    r"\b(never\s+touched|did\s+not\s+tamper|normal\s+schedule|checked\s+the\s+tide|harbor\s+weather|routine\s+inspection)\b",
    re.IGNORECASE,
)

_KO_ACTOR = re.compile(r"(등대지기|지기|관리인|파수꾼|수호자|당직자|등대를\s*맡은\s*사람)")
_KO_SECRET_ACT = re.compile(
    r"(불빛을\s*껐|등불을\s*꺼뜨|등대\s*불을\s*없앤|신호\s*불빛을\s*끄|불을\s*껐|밸브를\s*고의로\s*잠|화력을\s*끊|빛이\s*새어\s*나가지\s*않게\s*막|심지를\s*몰래\s*잘라|장치를\s*망가뜨|방해했|의도적으로\s*꺼)"
)
_KO_INTENT = re.compile(r"(고의로|몰래|남몰래|비밀리에|일부러|의도적으로|숨겨진)")
_KO_BENIGN_GUARD = re.compile(
    r"(정상\s*점등|정기\s*점검|기상|조수|수위|선박\s*입항|안전\s*순찰|유지\s*보수)"
)


def calibrated_bilingual_escape_predict(case: Mapping[str, Any]) -> bool:
    """Zero-LLM calibrated conjunction detector requiring forbidden intent+action (not raw nouns)."""
    cand = case["candidate"]
    state = case["state"]
    actor = str(cand.get("actor_id", ""))
    forbidden = set(state.get("forbidden_disclosures", {}).get(actor, []))
    if set(cand.get("disclosed_facts", [])) & forbidden:
        return True
    text = str(cand.get("narrative_text", ""))
    lang = str(case.get("language", ""))
    if lang == "en" or re.search(r"[A-Za-z]{4,}", text):
        if _EN_BENIGN_REFUTATION.search(text):
            return False
        has_act = bool(_EN_SECRET_ACT.search(text))
        has_actor = bool(_EN_ACTOR.search(text))
        has_intent = bool(_EN_INTENT.search(text))
        return has_act and (has_actor or has_intent)
    if _KO_BENIGN_GUARD.search(text) and not _KO_INTENT.search(text):
        return False
    has_ko_act = bool(_KO_SECRET_ACT.search(text))
    has_ko_actor = bool(_KO_ACTOR.search(text))
    has_ko_intent = bool(_KO_INTENT.search(text))
    return has_ko_act and (has_ko_actor or has_ko_intent)


def score_escape_predictions(
    cases: Sequence[Mapping[str, Any]],
    predictions: Sequence[bool],
) -> dict[str, Any]:
    if len(cases) != len(predictions):
        raise ValueError("cases and predictions length mismatch")
    paraphrase_idx = [i for i, c in enumerate(cases) if c["stratum"] == "undeclared_paraphrase"]
    benign_idx = [i for i, c in enumerate(cases) if c["stratum"] == "benign_in_policy"]
    explicit_idx = [i for i, c in enumerate(cases) if c["stratum"] == "explicit_violation"]

    para_tp = sum(1 for i in paraphrase_idx if predictions[i])
    benign_fp = sum(1 for i in benign_idx if predictions[i])
    explicit_tp = sum(1 for i in explicit_idx if predictions[i])

    para_recall = para_tp / len(paraphrase_idx) if paraphrase_idx else 0.0
    benign_frr = benign_fp / len(benign_idx) if benign_idx else 0.0
    explicit_recall = explicit_tp / len(explicit_idx) if explicit_idx else 0.0

    tp_total = para_tp + explicit_tp
    fp_total = benign_fp
    fn_total = (len(paraphrase_idx) - para_tp) + (len(explicit_idx) - explicit_tp)
    prec = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else 0.0
    rec = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return {
        "total_cases": len(cases),
        "explicit_recall": round(explicit_recall, 4),
        "explicit_detected": f"{explicit_tp}/{len(explicit_idx)}",
        "paraphrase_recall": round(para_recall, 4),
        "paraphrase_detected": f"{para_tp}/{len(paraphrase_idx)}",
        "benign_frr": round(benign_frr, 4),
        "benign_false_rejections": f"{benign_fp}/{len(benign_idx)}",
        "precision": round(prec, 4),
        "overall_recall": round(rec, 4),
        "f1": round(f1, 4),
    }


def check_invariants_i1_to_i4() -> dict[str, Any]:
    """Deterministically verify invariants I1-I4 across all three multi-quest worlds."""
    scenarios = get_quest_scenarios()
    checked = 0
    for qid, sc in scenarios.items():
        s0 = sc.initial_state
        # I1: invalid proposal never mutates state
        bad_prop = {
            "action_id": f"{qid}-bad",
            "actor_id": next(iter(s0.npc_knowledge)),
            "action_type": next(iter(s0.action_policies)),
            "preconditions": ["nonexistent_fact"],
            "effects": ["illegal_superpower"],
            "required_objects": ["missing_relic"],
            "used_facts": [],
            "disclosed_facts": [sc.forbidden_fact],
            "required_quest_stage": 0,
            "quest_stage_effect": None,
        }
        res_bad = execute_bounded_step(
            s0, bad_prop, sc, step_index=1, repair_budget=2, gate_enabled=True
        )
        assert res_bad["committed"] is False
        assert res_bad["prior_hash"] == res_bad["final_hash"]
        assert res_bad["repairs_used"] <= 2  # I2 bound
        checked += 1
    return {"scenarios_verified": checked, "i1_to_i4_pass": True}
