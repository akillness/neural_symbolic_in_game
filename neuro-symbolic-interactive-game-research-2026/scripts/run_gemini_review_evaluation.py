"""Execute the frozen, designer-authored offline review-boundary audit.

This is not a model or human efficacy study. The schema-only intervention is an
isolated simulator; the other arms use the unchanged native commit controller.
No outcomes are produced merely by importing this module.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from itertools import product
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from nesy_game.contracts import ActionPolicy, CandidateAction, WorldState, parse_candidate_mapping
from nesy_game.repair import counterexample_guided_repair
from nesy_game.runtime import execute_with_repair, replay_trace_record, to_jsonable
from scripts.review_reference import generic_accepts, reference_reachable_locations

PROTOCOL_PATH = ROOT / "research/academic-pipeline/gemini-review-20261113/protocol-v2.json"
ARMS = ("schema_only", "semantic_rejection", "unchanged_retry", "guided_repair")
REPAIR_BUDGETS = dict(zip(ARMS, (0, 0, 1, 1)))
SET_SIGNATURE_FIELDS = (
    "preconditions",
    "effects",
    "required_objects",
    "used_facts",
    "disclosed_facts",
)
SIGNATURE_FIELDS = (
    "action_type",
    *SET_SIGNATURE_FIELDS,
    "required_quest_stage",
    "quest_stage_effect",
)


def _protocol() -> dict[str, Any]:
    return json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))


def _json(value: Any) -> str:
    return json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def production_reachable_locations(graph: Mapping[str, Any]) -> frozenset[str]:
    """Monotone room/key closure, distinct from the location/inventory BFS.

    Correctness is scoped to finite bidirectional edges and persistent reusable
    keys. Consumable keys or irreversible transitions need another state model.
    """
    if not isinstance(graph, Mapping) or set(graph) != {"rooms", "start", "edges", "placements"}:
        raise ValueError("graph must contain exactly rooms, start, edges, placements")
    rooms, start, edges, placements = (
        graph[field] for field in ("rooms", "start", "edges", "placements")
    )
    if (
        not isinstance(rooms, list)
        or not rooms
        or any(not isinstance(room, str) or not room for room in rooms)
        or len(set(rooms)) != len(rooms)
    ):
        raise ValueError("rooms must be a nonempty list of unique nonempty strings")
    room_set = set(rooms)
    if not isinstance(start, str) or start not in room_set:
        raise ValueError("start must be a declared room")
    if not isinstance(placements, Mapping) or any(
        not isinstance(item, str) or not item or not isinstance(room, str) or room not in room_set
        for item, room in placements.items()
    ):
        raise ValueError("placements must map nonempty item ids to declared rooms")
    if not isinstance(edges, list):
        raise TypeError("edges must be a list")
    key_ids: set[str] = set()
    checked_edges: list[tuple[str, str, set[str]]] = []
    for edge in edges:
        if not isinstance(edge, Mapping) or set(edge) != {"source", "target", "requires_keys"}:
            raise ValueError("edge must contain exactly source, target, requires_keys")
        source, target, required = edge["source"], edge["target"], edge["requires_keys"]
        if any(not isinstance(room, str) or room not in room_set for room in (source, target)):
            raise ValueError("edge endpoints must be declared rooms")
        if (
            not isinstance(required, list)
            or any(not isinstance(key, str) or not key or key not in placements for key in required)
            or len(set(required)) != len(required)
        ):
            raise ValueError("requires_keys must list unique placed key ids")
        key_ids.update(required)
        checked_edges.append((source, target, set(required)))
    reached = {start}
    collected: set[str] = set()
    while True:
        previous = (frozenset(reached), frozenset(collected))
        collected.update(key for key in key_ids if placements[key] in reached)
        for source, target, required in checked_edges:
            if required <= collected and (source in reached or target in reached):
                reached.update((source, target))
        if previous == (frozenset(reached), frozenset(collected)):
            return frozenset(reached)


def _graph(room_count: int, topology: str, placement: Sequence[str]) -> dict[str, Any]:
    rooms = [f"r{index}" for index in range(room_count)]
    edges = []
    for index in range(1, room_count):
        required = ["key0"] if index == room_count // 2 else []
        if index == room_count - 1:
            required = ["key1"]
        edges.append(
            {"source": rooms[index - 1], "target": rooms[index], "requires_keys": required}
        )
    if topology == "bypass_branch":
        edges.append({"source": rooms[0], "target": rooms[room_count // 2], "requires_keys": []})
    elif topology != "locked_chain":
        raise ValueError(f"unsupported frozen topology: {topology}")
    positions = {"start": rooms[0], "goal": rooms[-1]}
    return {
        "rooms": rooms,
        "start": rooms[0],
        "edges": edges,
        "placements": {
            "key0": positions[placement[0]],
            "key1": positions[placement[1]],
            "map": rooms[0],
            "relic": rooms[-1],
        },
    }


def _state(graph: Mapping[str, Any], stage: int, state_id: str) -> dict[str, Any]:
    policy = _protocol()["state_and_policy"]
    return {
        "state_id": state_id,
        "locations": sorted(graph["rooms"]),
        "reachable_locations": sorted(production_reachable_locations(graph)),
        "object_locations": dict(graph["placements"]),
        "inventory": [],
        "facts": sorted(policy["facts"]),
        "action_policies": {
            "SIGNAL": {
                "required_preconditions": ["ready"],
                "allowed_effects": ["beacon_lit", "signal_restored"],
                "required_effects": ["signal_restored"],
                "allowed_quest_stage_effects": [stage, stage + 1],
            },
            "OBSERVE": {
                "required_preconditions": [],
                "allowed_effects": ["observed"],
                "required_effects": [],
                "allowed_quest_stage_effects": [],
            },
        },
        "npc_knowledge": {policy["actor"]: sorted(policy["known_facts"])},
        "forbidden_disclosures": {policy["actor"]: ["keeper_secret"] if stage == 0 else []},
        "quest_stage": stage,
    }


def _world_state(data: Mapping[str, Any]) -> WorldState:
    return WorldState(
        state_id=data["state_id"],
        locations=frozenset(data["locations"]),
        reachable_locations=frozenset(data["reachable_locations"]),
        object_locations=data["object_locations"],
        inventory=frozenset(data["inventory"]),
        facts=frozenset(data["facts"]),
        quest_stage=data["quest_stage"],
        action_policies={
            name: ActionPolicy(
                required_preconditions=frozenset(policy["required_preconditions"]),
                allowed_effects=frozenset(policy["allowed_effects"]),
                required_effects=frozenset(policy["required_effects"]),
                allowed_quest_stage_effects=frozenset(policy["allowed_quest_stage_effects"]),
            )
            for name, policy in data["action_policies"].items()
        },
        npc_knowledge={actor: frozenset(facts) for actor, facts in data["npc_knowledge"].items()},
        forbidden_disclosures={
            actor: frozenset(facts) for actor, facts in data["forbidden_disclosures"].items()
        },
    )


def _candidate(case_id: str, variant: str, stage: int) -> dict[str, Any]:
    candidate = {
        "action_id": case_id,
        "actor_id": "keeper",
        "action_type": "SIGNAL",
        "preconditions": ["ready"],
        "effects": ["signal_restored"],
        "required_objects": [],
        "used_facts": [],
        "disclosed_facts": [],
        "required_quest_stage": stage,
        "quest_stage_effect": stage + 1,
        "narrative_text": "Restore the signal.",
        "metadata": {},
    }
    changes = {
        "valid_signal": {},
        "valid_observe": {
            "action_type": "OBSERVE",
            "preconditions": [],
            "effects": ["observed"],
            "quest_stage_effect": None,
            "narrative_text": "Observe the harbor.",
        },
        "valid_public_fact": {"used_facts": ["harbor_open"], "disclosed_facts": ["harbor_open"]},
        "valid_start_object": {"required_objects": ["map"]},
        "required_relic": {"required_objects": ["relic"]},
        "omit_policy_precondition": {"preconditions": []},
        "omit_policy_effect": {"effects": []},
        "unauthorized_effect": {"effects": ["signal_restored", "treasure_spawned"]},
        "declared_secret": {"disclosed_facts": ["keeper_secret"]},
        "unknown_knowledge": {"used_facts": ["unknown_fact"]},
        "future_stage": {"required_quest_stage": stage + 1},
        "unknown_object": {"required_objects": ["unknown_relic"]},
        "extra_unsatisfied_precondition": {"preconditions": ["ready", "absent_fact"]},
    }
    if variant not in changes:
        raise ValueError(f"unsupported frozen candidate variant: {variant}")
    candidate.update(changes[variant])
    return candidate


def build_cases() -> list[dict[str, Any]]:
    protocol = _protocol()
    design = protocol["graph_design"]
    cases = []
    for room_count, topology, placement, stage in product(
        design["room_counts"],
        design["topologies"],
        design["key_placement_patterns"],
        design["quest_stages"],
    ):
        state_id = f"n{room_count}-{topology}-{'-'.join(placement)}-q{stage}"
        graph = _graph(room_count, topology, placement)
        state = _state(graph, stage, state_id)
        for variant in protocol["candidate_variants"]:
            case_id = f"{state_id}--{variant}"
            cases.append(
                {
                    "case_id": case_id,
                    "variant": variant,
                    "graph": deepcopy(graph),
                    "state": deepcopy(state),
                    "candidate": _candidate(case_id, variant, stage),
                }
            )
    if len(cases) != protocol["assignment_count_per_arm"]:
        raise ValueError("constructed cases disagree with frozen assignment count")
    return cases


def build_surface_sentinels() -> list[dict[str, Any]]:
    texts = (
        ("en", "The keeper secretly extinguished the beacon."),
        ("en", "It was the lighthouse guardian who quietly put out its light."),
        ("en", "Behind the darkness was the keeper's hidden act of sabotage."),
        ("ko", "등대지기가 몰래 신호등을 껐다."),
        ("ko", "불빛을 남몰래 없앤 사람은 등대의 수호자였다."),
        ("ko", "등대가 어두워진 뒤에는 지기의 숨겨진 방해가 있었다."),
    )
    graph = _graph(4, "locked_chain", ("start", "start"))
    state = _state(graph, 0, "surface-canonical-q0")
    cases = []
    for index, (language, text) in enumerate(texts):
        for declared in (False, True):
            variant = "surface_declared" if declared else "surface_undeclared"
            case_id = f"surface-{index + 1}-{language}-{variant}"
            candidate = _candidate(case_id, "valid_observe", 0)
            candidate.update(
                narrative_text=text, disclosed_facts=["keeper_secret"] if declared else []
            )
            cases.append(
                {
                    "case_id": case_id,
                    "variant": variant,
                    "language": language,
                    "pair_id": f"surface-{index + 1}",
                    "graph": deepcopy(graph),
                    "state": deepcopy(state),
                    "candidate": candidate,
                }
            )
    return cases


def structural_signature(candidate_mapping: Mapping[str, Any]) -> str:
    """Exact encoded structure, not identity, prose, graph labels, or creativity."""
    fields = {name: candidate_mapping[name] for name in SIGNATURE_FIELDS}
    for name in SET_SIGNATURE_FIELDS:
        fields[name] = sorted(set(fields[name]))
    return _json(fields)


def _unchanged_repair(
    state: WorldState, candidate: CandidateAction, validation: Any, attempt: int
) -> CandidateAction:
    del state, validation, attempt
    return candidate


def _empty_row(case: Mapping[str, Any], arm_id: str) -> dict[str, Any]:
    proposal = deepcopy(case.get("candidate"))
    initial_state = deepcopy(case.get("state"))
    return {
        "case_id": case["case_id"],
        "variant": case.get("variant"),
        "arm": arm_id,
        "status": "FAILED",
        "reference_initial_valid": None,
        "reference_final_valid": None,
        "goal_reached": None,
        "initial_candidate": proposal,
        "final_candidate": None,
        "initial_state": initial_state,
        "reference_state": None,
        "final_state": None,
        "before_state_hash": _hash(initial_state),
        "after_state_hash": None,
        "initial_signature": None,
        "final_signature": None,
        "schema_validation": {
            "valid": None,
            "parser": "parse_candidate_mapping(allow_defaults=False)",
        },
        "validation": None,
        "initial_validation": None,
        "attempts": [],
        "repair_attempt_count": 0,
        "repair_budget": REPAIR_BUDGETS[arm_id],
        "semantic_gate_executed": False,
        "native_outcome": None,
        "native_replay_equal": None,
        "error": None,
        "latency_ms": None,
        "model_called": False,
        "model_id": None,
        "model_revision": None,
        "seed": None,
        "cost_usd": None,
    }


def _reference_inputs(
    case: Mapping[str, Any], row: dict[str, Any], candidate: CandidateAction
) -> WorldState:
    reference_data = deepcopy(case["state"])
    reference_data["reachable_locations"] = sorted(reference_reachable_locations(case["graph"]))
    reference_state = _world_state(reference_data)
    row["reference_state"] = reference_data
    row["reference_state_hash"] = _hash(reference_data)
    row["reference_initial_valid"] = generic_accepts(reference_state, candidate)
    row["initial_signature"] = structural_signature(to_jsonable(candidate))
    row["production_reachable_locations"] = sorted(production_reachable_locations(case["graph"]))
    row["reference_reachable_locations"] = reference_data["reachable_locations"]
    row["graph_agreement"] = (
        row["production_reachable_locations"] == reference_data["reachable_locations"]
    )
    return reference_state


def _record_error(row: dict[str, Any], exc: Exception) -> None:
    row["status"] = "FAILED"
    row["error"] = {"type": type(exc).__name__, "message": str(exc)}


def run_case(case: Mapping[str, Any], arm_id: str) -> dict[str, Any]:
    if arm_id not in ARMS:
        raise ValueError(f"unknown audit arm: {arm_id}")
    started = time.perf_counter()
    row = _empty_row(case, arm_id)
    try:
        # The same strict parser is the first decision boundary for every arm.
        candidate = parse_candidate_mapping(case["candidate"], allow_defaults=False)
        row["schema_validation"]["valid"] = True
        row["parsed_candidate"] = to_jsonable(candidate)
        reference_state = _reference_inputs(case, row, candidate)
        state = _world_state(case["state"])
        row["before_state_hash"] = _hash(state)
        if arm_id == "schema_only":
            # Deliberate ablation: neither validate_candidate nor native commit is
            # called. Only encoded effects/stage, never prose, enter this simulator.
            final_candidate = candidate
            final_state = replace(
                state,
                facts=state.facts | candidate.effects,
                quest_stage=state.quest_stage
                if candidate.quest_stage_effect is None
                else candidate.quest_stage_effect,
            )
            row["status"] = "COMMITTED"
            row["validation"] = {
                "valid": True,
                "errors": [],
                "checks_run": ["strict_schema_only"],
                "semantic_validation": "NOT_EXECUTED",
            }
            row["initial_validation"] = row["validation"]
            row["attempts"] = [
                {"attempt": 0, "candidate": to_jsonable(candidate), "validation": row["validation"]}
            ]
        else:
            row["semantic_gate_executed"] = True
            repairer = {
                "semantic_rejection": None,
                "unchanged_retry": _unchanged_repair,
                "guided_repair": counterexample_guided_repair,
            }[arm_id]
            outcome = execute_with_repair(
                state,
                candidate,
                repairer=repairer,
                repair_budget=REPAIR_BUDGETS[arm_id],
                trace_context={
                    "study_id": _protocol()["study_id"],
                    "case_id": case["case_id"],
                    "arm": arm_id,
                },
            )
            row["native_outcome"] = to_jsonable(outcome)
            row["attempts"] = to_jsonable(outcome.trace)
            row["repair_attempt_count"] = outcome.attempts
            row["initial_validation"] = to_jsonable(outcome.trace[0].validation)
            row["validation"] = to_jsonable(outcome.validation)
            if outcome.status not in ("commit", "fallback"):
                raise ValueError(f"unexpected native outcome: {outcome.status}")
            row["status"] = "COMMITTED" if outcome.status == "commit" else "HOLD"
            final_candidate, final_state = outcome.candidate, outcome.state
        row["final_candidate"] = to_jsonable(final_candidate)
        row["final_state"] = to_jsonable(final_state)
        row["after_state_hash"] = _hash(final_state)
        row["goal_reached"] = (
            row["status"] == "COMMITTED" and "signal_restored" in final_state.facts
        )
        row["final_signature"] = structural_signature(row["final_candidate"])
        # Never evaluate against outcome.state: an action cannot satisfy its own
        # preconditions or stage requirement retroactively through its effects.
        row["reference_final_valid"] = generic_accepts(reference_state, final_candidate)
        if row["native_outcome"] is not None:
            replayed = replay_trace_record(row["native_outcome"])
            row["native_replay_equal"] = to_jsonable(replayed) == row["final_state"]
            if not row["native_replay_equal"]:
                raise ValueError("native replay disagrees with emitted final state")
    except Exception as exc:  # noqa: BLE001 - Keep every execution failure in the assigned denominator.
        if row["schema_validation"]["valid"] is None:
            row["schema_validation"].update(valid=False, error=str(exc))
        _record_error(row, exc)
    finally:
        row["latency_ms"] = (time.perf_counter() - started) * 1000.0
    return row


def _failed_assignment(
    case: Mapping[str, Any], arm_id: str, exc: Exception, started: float
) -> dict[str, Any]:
    """Retain escaped execution failures without inventing a final state."""
    row = _empty_row(case, arm_id)
    try:
        candidate = parse_candidate_mapping(case["candidate"], allow_defaults=False)
        row["schema_validation"]["valid"] = True
        row["parsed_candidate"] = to_jsonable(candidate)
        _reference_inputs(case, row, candidate)
    except Exception as reference_error:  # noqa: BLE001 - Retain failed assignments even when reference evaluation fails.
        row["initial_evaluation_error"] = {
            "type": type(reference_error).__name__,
            "message": str(reference_error),
        }
    _record_error(row, exc)
    row["latency_ms"] = (time.perf_counter() - started) * 1000.0
    return row


def summarize_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    summaries = {}
    for arm in ARMS:
        assigned = [row for row in rows if row["arm"] == arm]
        if not assigned:
            continue
        valid = [row for row in assigned if row["reference_initial_valid"] is True]
        invalid = [row for row in assigned if row["reference_initial_valid"] is False]
        committed = [row for row in assigned if row["status"] == "COMMITTED"]
        held = [row for row in assigned if row["status"] == "HOLD"]
        failed = [row for row in assigned if row["status"] == "FAILED"]
        safe = [row for row in committed if row["reference_final_valid"] is True]
        repaired = [row for row in safe if row["reference_initial_valid"] is False]
        preserved = [
            row
            for row in safe
            if row["reference_initial_valid"] is True
            and row.get("initial_signature") is not None
            and row["initial_signature"] == row.get("final_signature")
        ]
        initial_signatures = {
            row["initial_signature"] for row in valid if row.get("initial_signature") is not None
        }
        retained_signatures = {row["initial_signature"] for row in preserved}
        invalid_signatures = {
            row["initial_signature"] for row in invalid if row.get("initial_signature") is not None
        }
        repaired_signatures = {
            row["final_signature"] for row in repaired if row.get("final_signature") is not None
        }
        unsafe = sum(row["reference_final_valid"] is False for row in committed)
        false_rejections = sum(row["reference_initial_valid"] is True for row in held)
        goals = sum(row["goal_reached"] is True for row in committed)
        metrics = {
            "assigned": len(assigned),
            "initial_valid": len(valid),
            "initial_invalid": len(invalid),
            "initial_reference_evaluated": len(valid) + len(invalid),
            "initial_reference_unknown": len(assigned) - len(valid) - len(invalid),
            "committed": len(committed),
            "held": len(held),
            "failed": len(failed),
            "safe_commits": len(safe),
            "unsafe_commits": unsafe,
            "commit_reference_unknown": sum(
                row["reference_final_valid"] is None for row in committed
            ),
            "repair_successes": len(repaired),
            "false_rejections": false_rejections,
            "goals": goals,
            "pre_gate_invalid_denominator": len(assigned),
            "repair_success_denominator": len(invalid),
            "terminal_hold_denominator": len(assigned),
            "unsafe_commit_denominator": len(assigned),
            "unsafe_commit_among_commits_denominator": len(committed),
            "false_rejection_denominator": len(valid),
            "goal_denominator": len(assigned),
            "valid_initial_signature_count": len(initial_signatures),
            "valid_retained_signature_count": len(retained_signatures),
            "valid_signature_preserved": len(preserved),
            "valid_signature_case_denominator": len(valid),
            "valid_signature_denominator": len(initial_signatures),
            "invalid_initial_signature_count": len(invalid_signatures),
            "repaired_signature_count": len(repaired_signatures),
            "repair_attempts_executed": sum(row.get("repair_attempt_count", 0) for row in assigned),
            "native_replay_emitted": sum(
                row.get("native_replay_equal") is not None for row in assigned
            ),
            "native_replay_equal": sum(row.get("native_replay_equal") is True for row in assigned),
            "latency_ms_total": sum(row["latency_ms"] for row in assigned),
        }
        if len(committed) + len(held) + len(failed) != len(assigned):
            raise ValueError(f"unknown outcome status in {arm}")
        for name, numerator, denominator in (
            ("pre_gate_invalid_rate", len(invalid), len(assigned)),
            ("repair_success_rate", len(repaired), len(invalid)),
            ("terminal_hold_rate", len(held), len(assigned)),
            ("unsafe_commit_rate", unsafe, len(assigned)),
            ("unsafe_commit_among_commits_rate", unsafe, len(committed)),
            ("false_rejection_rate", false_rejections, len(valid)),
            ("goal_rate", goals, len(assigned)),
            ("valid_signature_retention_rate", len(retained_signatures), len(initial_signatures)),
        ):
            metrics[name] = numerator / denominator if denominator else None
        metrics["latency_ms_mean"] = metrics["latency_ms_total"] / len(assigned)
        summaries[arm] = metrics
    return summaries


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        )


def _write_rows(output: Path, stem: str, rows: Sequence[Mapping[str, Any]]) -> None:
    with (output / f"{stem}.jsonl").open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(_json(row) + "\n")
    fields = sorted({field for row in rows for field in row})
    with (output / f"{stem}.csv").open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: _json(value) if isinstance(value, (dict, list)) else value
                    for field, value in row.items()
                }
            )


def _graph_agreement(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    seen = set()
    rows = []
    for case in cases:
        key = (_hash(case["graph"]), case["state"]["quest_stage"])
        if key in seen:
            continue
        seen.add(key)
        closure = sorted(production_reachable_locations(case["graph"]))
        bfs = sorted(reference_reachable_locations(case["graph"]))
        rows.append(
            {
                "state_id": case["state"]["state_id"],
                "graph_hash": key[0],
                "quest_stage": key[1],
                "closure": closure,
                "bfs": bfs,
                "agrees": closure == bfs,
            }
        )
    mismatches = [row for row in rows if not row["agrees"]]
    return {
        "assigned": len(rows),
        "agreements": len(rows) - len(mismatches),
        "mismatches": mismatches,
        "states": rows,
    }


def _table_fragment(summary: Mapping[str, Any], language: str) -> str:
    korean = language == "ko"
    title = "결정론적 오프라인 경계 감사" if korean else "Deterministic offline boundary audit"
    heading = (
        "실행군 & 배정 & 초기 무효 & 수리 복구 & 보류 & 비안전 반영 & 과잉 차단 & 목표 & 실패"
        if korean
        else "Arm & Assigned & Initial invalid & Recovered & Hold & Unsafe commit & False rejection & Goal & Failed"
    )
    lines = [
        "% Generated exclusively from this directory's observed audit rows.",
        "\\begin{table*}[t]",
        "\\centering",
        "\\scriptsize",
        "\\begin{tabular}{lrrrrrrrr}",
        "\\hline",
        heading + r" \\",
        "\\hline",
    ]
    for arm, row in summary["core"].items():
        values = (
            arm.replace("_", r"\_"),
            str(row["assigned"]),
            f"{row['initial_invalid']}/{row['pre_gate_invalid_denominator']}",
            f"{row['repair_successes']}/{row['repair_success_denominator']}",
            f"{row['held']}/{row['terminal_hold_denominator']}",
            f"{row['unsafe_commits']}/{row['unsafe_commit_denominator']}",
            f"{row['false_rejections']}/{row['false_rejection_denominator']}",
            f"{row['goals']}/{row['goal_denominator']}",
            str(row["failed"]),
        )
        lines.append(" & ".join(values) + r" \\")
    lines.extend(["\\hline", "\\end{tabular}"])
    note = (
        "수리는 초기 무효, 과잉 차단은 초기 유효를 분모로 사용한다. 목표 달성은 규칙 적합성과 별개이다."
        if korean
        else "Recovery uses initially invalid cases; false rejection uses initially valid cases. Goal attainment is separate from rule validity."
    )
    lines.extend([f"\\caption{{{title}. {note}}}", "\\end{table*}", ""])
    lines.extend(
        [
            "\\begin{table*}[t]",
            "\\centering",
            "\\scriptsize",
            "\\begin{tabular}{lrrrrr}",
            "\\hline",
            (
                "실행군 & 유효 구조 보존 & 사례 보존 & 초기 무효 구조 & 수리 후 구조 & 비안전/반영"
                if korean
                else "Arm & Valid signatures retained & Cases retained & Invalid signatures & Repaired signatures & Unsafe/commits"
            )
            + r" \\",
            "\\hline",
        ]
    )
    for arm, row in summary["core"].items():
        values = (
            arm.replace("_", r"\_"),
            f"{row['valid_retained_signature_count']}/{row['valid_signature_denominator']}",
            f"{row['valid_signature_preserved']}/{row['valid_signature_case_denominator']}",
            str(row["invalid_initial_signature_count"]),
            str(row["repaired_signature_count"]),
            f"{row['unsafe_commits']}/{row['unsafe_commit_among_commits_denominator']}",
        )
        lines.append(" & ".join(values) + r" \\")
    boundary = (
        "정확한 구조 서명만 비교하며 창의성이나 언어 다양성은 측정하지 않는다."
        if korean
        else "Exact encoded signatures only; neither creativity nor linguistic diversity is measured."
    )
    lines.extend(["\\hline", "\\end{tabular}", f"\\caption{{{boundary}}}", "\\end{table*}", ""])
    graph = summary["graph_agreement"]
    lines.append(
        f"도달성 구현 교차검사: {graph['agreements']}/{graph['assigned']}. "
        if korean
        else f"Reachability implementation crosscheck: {graph['agreements']}/{graph['assigned']}. "
    )
    lines.append("\\begin{tabular}{lrrrr}")
    lines.append(
        (
            "실행군 & 별도 표면 배정 & 무선언 반영 & 선언 보류 & 실패"
            if korean
            else "Arm & Separate surface assignments & Undeclared commits & Declared holds & Failed"
        )
        + r" \\"
    )
    for arm, row in summary["surface"].items():
        boundary_row = summary["surface_pairs"][arm]
        values = (
            arm.replace("_", r"\_"),
            str(row["assigned"]),
            f"{boundary_row['undeclared_committed']}/{boundary_row['undeclared_assigned']}",
            f"{boundary_row['declared_held']}/{boundary_row['declared_assigned']}",
            str(row["failed"]),
        )
        lines.append(" & ".join(values) + r" \\")
    lines.extend(
        [
            "\\end{tabular}",
            (
                "표면 문장은 설계자가 작성한 센티널이며 자연어 누출 빈도나 렌더러 안전성의 증거가 아니다. 모델·인간 효능은 측정하지 않았다."
                if korean
                else "Surface sentences are designer-authored sentinels, not natural-language leakage prevalence or renderer safety evidence. Model and human efficacy remain unmeasured."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_study(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir)
    if output.is_symlink() or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        raise FileExistsError(
            "audit output directory must be new or empty and must not be a symlink"
        )
    output.mkdir(parents=True, exist_ok=True)
    protocol_bytes = PROTOCOL_PATH.read_bytes()
    protocol = json.loads(protocol_bytes)
    if tuple(arm["id"] for arm in protocol["arms"]) != ARMS or any(
        arm["repair_budget"] != REPAIR_BUDGETS[arm["id"]] for arm in protocol["arms"]
    ):
        raise ValueError("frozen protocol arms disagree with implemented interventions")
    cases, surface = build_cases(), build_surface_sentinels()
    inventory = [
        {"case_id": case["case_id"], "arm": arm, "cohort": cohort}
        for cohort, inputs in (("core", cases), ("surface", surface))
        for case in inputs
        for arm in ARMS
    ]
    if len({(unit["case_id"], unit["arm"], unit["cohort"]) for unit in inventory}) != len(
        inventory
    ):
        raise ValueError("duplicate frozen assignments")
    source_paths = {
        Path(__file__).resolve(),
        ROOT / "scripts/review_reference.py",
        PROTOCOL_PATH,
        PROTOCOL_PATH.with_name("reviewer-source.json"),
        PROTOCOL_PATH.with_name("review-response.json"),
        *sorted((ROOT / "src/nesy_game").glob("*.py")),
    }
    source_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(source_paths)
    }
    # Every exact input, assignment and source digest precedes the first outcome.
    with (output / "protocol.json").open("xb") as handle:
        handle.write(protocol_bytes)
    _write_json(output / "cases.json", cases)
    _write_json(output / "surface_sentinels.json", surface)
    _write_json(output / "assignment_inventory.json", inventory)
    _write_json(output / "source_hashes.json", source_hashes)
    for name in ("reviewer-source.json", "review-response.json"):
        with (output / name).open("xb") as handle:
            handle.write(PROTOCOL_PATH.with_name(name).read_bytes())
    input_files = (
        "protocol.json",
        "cases.json",
        "surface_sentinels.json",
        "assignment_inventory.json",
        "source_hashes.json",
        "reviewer-source.json",
        "review-response.json",
    )
    input_hashes = {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in input_files
    }
    _write_json(output / "input_hashes.json", input_hashes)
    results: dict[str, list[dict[str, Any]]] = {"core": [], "surface": []}
    for cohort, inputs in (("core", cases), ("surface", surface)):
        for case in inputs:
            for arm in ARMS:
                started = time.perf_counter()
                try:
                    row = run_case(case, arm)
                except Exception as exc:  # noqa: BLE001 - Keep every escaped failure in the assigned denominator.
                    row = _failed_assignment(case, arm, exc, started)
                row["cohort"] = cohort
                row["input_hash"] = _hash(case)
                row["source_hashes"] = source_hashes
                results[cohort].append(row)
    _write_rows(output, "rows", results["core"])
    _write_rows(output, "surface_rows", results["surface"])
    summary = {
        "schema_version": protocol["schema_version"],
        "study_id": protocol["study_id"],
        "scope": protocol["scope"],
        "model_called": False,
        "model_id": None,
        "model_revision": None,
        "seed": None,
        "cost_usd": None,
        "source_hashes": source_hashes,
        "input_hashes": input_hashes,
        "core": summarize_rows(results["core"]),
        "surface": summarize_rows(results["surface"]),
        "graph_agreement": _graph_agreement(cases),
        "surface_pairs": {},
    }
    for arm in ARMS:
        arm_rows = [row for row in results["surface"] if row["arm"] == arm]
        undeclared = [row for row in arm_rows if row["variant"] == "surface_undeclared"]
        declared = [row for row in arm_rows if row["variant"] == "surface_declared"]
        summary["surface_pairs"][arm] = {
            "undeclared_assigned": len(undeclared),
            "declared_assigned": len(declared),
            "undeclared_committed": sum(row["status"] == "COMMITTED" for row in undeclared),
            "declared_held": sum(row["status"] == "HOLD" for row in declared),
            "narrative_state_mutation_checks": sum(
                row["final_state"] is not None for row in arm_rows
            ),
            "narrative_state_mutation_mismatches": [
                row["case_id"]
                for row in arm_rows
                if row["final_state"] is not None
                and (
                    set(row["final_state"]["facts"])
                    != (
                        set(row["initial_state"]["facts"])
                        | (
                            set(row["final_candidate"]["effects"])
                            if row["status"] == "COMMITTED"
                            else set()
                        )
                    )
                    or row["final_state"]["quest_stage"] != row["initial_state"]["quest_stage"]
                )
            ],
        }
    _write_json(output / "summary.json", summary)
    for language in ("en", "ko"):
        with (output / f"review_boundary_audit_{language}.tex").open(
            "x", encoding="utf-8"
        ) as handle:
            handle.write(_table_fragment(summary, language))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="New or empty directory; prior cohorts are never overwritten",
    )
    arguments = parser.parse_args()
    summary = run_study(arguments.output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(arguments.output_dir),
                "study_id": summary["study_id"],
                "core": summary["core"],
                "surface": summary["surface"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
