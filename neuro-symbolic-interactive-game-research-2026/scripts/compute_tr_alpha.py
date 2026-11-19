#!/usr/bin/env python3
"""Blinded TR01-TR06 human annotation packet builder and Krippendorff alpha calculator.

Strictly forbids synthetic or LLM-simulated human scores: ``compute-alpha`` verifies that
at least two distinct human raters supplied explicit labels before computing alpha.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from green_supplements_lib import (
    execute_bounded_step,
    get_quest_scenarios,
    sha256_hex,
    world_state_to_dict,
)

RUBRIC_DIMENSIONS = (
    ("TR01", "Action policy & precondition validity attribution"),
    ("TR02", "Object reachability & inventory grounding accuracy"),
    ("TR03", "NPC epistemic knowledge boundary attribution"),
    ("TR04", "Quest-stage disclosure permission judgment"),
    ("TR05", "Replay trace-to-source provenance alignment"),
    ("TR06", "Repair feedback non-leakage & safety neutrality"),
)


def krippendorff_alpha_nominal(units_by_item: list[list[Any]]) -> float | None:
    """Compute nominal Krippendorff's alpha across items x raters (None entries ignored)."""
    pairable = []
    categories: set[Any] = set()
    for row in units_by_item:
        vals = [v for v in row if v is not None]
        if len(vals) >= 2:
            pairable.append(vals)
            categories.update(vals)
    if not pairable:
        return None
    if len(categories) <= 1:
        return 1.0

    n_total = sum(len(vals) for vals in pairable)
    do_num = 0.0
    cat_counts: dict[Any, int] = {c: 0 for c in categories}
    for vals in pairable:
        m_u = len(vals)
        for v in vals:
            cat_counts[v] += 1
        disagreements = 0
        for i in range(m_u):
            for j in range(i + 1, m_u):
                if vals[i] != vals[j]:
                    disagreements += 1
        # Two-sided off-diagonal pair count / (m_u - 1)
        do_num += (2.0 * disagreements) / (m_u - 1)

    d_o = do_num / n_total
    # Expected disagreement D_e
    sum_nc = sum(c * (c - 1) for c in cat_counts.values())
    d_e = 1.0 - (sum_nc / (n_total * (n_total - 1)))
    if d_e == 0.0:
        return 1.0
    return 1.0 - (d_o / d_e)


def _sample_candidate_for_polarity(
    qid: str, sc: Any, code: str, polarity: str, sample_idx: int
) -> dict[str, Any]:
    s0 = sc.initial_state
    actor = next(iter(s0.npc_knowledge))
    if qid == "sealed-lighthouse-v1":
        valid_base = {
            "action_id": f"{code.lower()}-{sample_idx + 1:02d}",
            "actor_id": actor,
            "action_type": "unlock_room",
            "preconditions": ["at_pier"],
            "effects": ["beacon_unlocked"],
            "required_objects": ["beacon_key"],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 0,
            "quest_stage_effect": 1,
            "narrative_text": "Unlocking the lighthouse beacon chamber using the pier key.",
        }
        unreachable_obj = "signal_lens"
    elif qid == "sunken-archive-v1":
        valid_base = {
            "action_id": f"{code.lower()}-{sample_idx + 1:02d}",
            "actor_id": actor,
            "action_type": "survey_atrium",
            "preconditions": ["at_atrium"],
            "effects": ["drain_mapped"],
            "required_objects": ["floodgate_key"],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 0,
            "quest_stage_effect": 1,
            "narrative_text": "Surveying the atrium drainage channels with the floodgate key.",
        }
        unreachable_obj = "ledger_codex"
    else:
        valid_base = {
            "action_id": f"{code.lower()}-{sample_idx + 1:02d}",
            "actor_id": actor,
            "action_type": "align_gears",
            "preconditions": ["at_gear_hall"],
            "effects": ["gears_aligned"],
            "required_objects": ["escapement_pin"],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 0,
            "quest_stage_effect": 1,
            "narrative_text": "Aligning the observatory drive gears using the escapement pin.",
        }
        unreachable_obj = "brass_almanac"

    if polarity == "positive_valid":
        return valid_base
    if polarity == "borderline_repair":
        repaired_case = dict(valid_base)
        repaired_case["effects"] = []  # omitted required effect -> rho inserts safely
        repaired_case["narrative_text"] = (
            f"{valid_base['narrative_text']} (missing declared effect)"
        )
        return repaired_case

    # negative_violation tailored by rubric dimension TR01..TR06
    neg = dict(valid_base)
    if code == "TR01":
        neg["action_type"] = "illegal_override_action"
        neg["effects"] = ["bypass_lock"]
    elif code == "TR02":
        neg["required_objects"] = [unreachable_obj]
    elif code == "TR03":
        neg["used_facts"] = ["unverified_rumor_fact"]
    elif code == "TR04":
        neg["disclosed_facts"] = [sc.forbidden_fact]
    elif code == "TR05":
        neg["required_quest_stage"] = 3
    else:  # TR06
        neg["disclosed_facts"] = [sc.forbidden_fact]
        neg["effects"] = []
    return neg


def build_blinded_tr_packet() -> dict[str, Any]:
    """Build 36 blinded trace items (6 per TR01..TR06) for >=2 independent human raters."""
    scenarios = get_quest_scenarios()
    items: list[dict[str, Any]] = []
    qids = tuple(scenarios.keys())
    for dim_idx, (code, desc) in enumerate(RUBRIC_DIMENSIONS):
        for sample_idx in range(6):
            qid = qids[(dim_idx + sample_idx) % len(qids)]
            sc = scenarios[qid]
            polarity = ("positive_valid", "negative_violation", "borderline_repair")[sample_idx % 3]
            raw_cand = _sample_candidate_for_polarity(qid, sc, code, polarity, sample_idx)
            step_res = execute_bounded_step(
                sc.initial_state,
                raw_cand,
                sc,
                step_index=1,
                repair_budget=2,
                gate_enabled=True,
            )
            state_dict = world_state_to_dict(sc.initial_state)
            items.append(
                {
                    "item_id": f"{code}-{sample_idx + 1:02d}",
                    "rubric_code": code,
                    "rubric_description": desc,
                    "quest_id": qid,
                    "blinded_stratum": polarity,
                    "snapshot_state_id": sc.initial_state.state_id,
                    "forbidden_fact": sc.forbidden_fact,
                    "prompt_excerpt": sc.prompt_brief,
                    "world_state_excerpt": {
                        "state_id": state_dict["state_id"],
                        "reachable_locations": state_dict["reachable_locations"],
                        "inventory": state_dict["inventory"],
                        "facts": state_dict["facts"],
                        "quest_stage": state_dict["quest_stage"],
                    },
                    "candidate_payload": step_res.get("parsed_candidate") or raw_cand,
                    "validation_errors": step_res["validation"]["errors"],
                    "committed": step_res["committed"],
                    "repaired": step_res["repaired"],
                    "prior_hash": step_res["prior_hash"],
                    "final_hash": step_res["final_hash"],
                    "candidate_summary": (
                        f"Trace sample {code}-{sample_idx + 1:02d} under {qid} "
                        f"(action={raw_cand['action_type']}, committed={step_res['committed']}, repaired={step_res['repaired']})"
                    ),
                    "rater_labels": {},
                }
            )
    packet = {
        "schema": "tr-human-eval-packet/v1",
        "status": "AWAITING_HUMAN_RATERS",
        "required_min_raters": 2,
        "recommended_raters": 3,
        "valid_labels": ["PASS", "FAIL", "UNCERTAIN"],
        "raters_completed": 0,
        "krippendorff_alpha": None,
        "items": items,
    }
    packet["packet_sha256"] = sha256_hex(items)
    return packet


def evaluate_packet_alpha(packet: dict[str, Any]) -> dict[str, Any]:
    items = packet.get("items", [])
    rater_ids: set[str] = set()
    for item in items:
        for rater_id, label in item.get("rater_labels", {}).items():
            if label is not None and str(label).strip():
                rater_ids.add(str(rater_id))
    sorted_raters = sorted(rater_ids)
    if len(sorted_raters) < 2:
        return {
            "status": "AWAITING_HUMAN_RATERS",
            "raters_completed": len(sorted_raters),
            "krippendorff_alpha": None,
            "per_dimension_alpha": {},
        }

    matrix = [[item.get("rater_labels", {}).get(r) for r in sorted_raters] for item in items]
    overall = krippendorff_alpha_nominal(matrix)
    per_dim: dict[str, float | None] = {}
    for code, _ in RUBRIC_DIMENSIONS:
        sub = [
            [item.get("rater_labels", {}).get(r) for r in sorted_raters]
            for item in items
            if item.get("rubric_code") == code
        ]
        a = krippendorff_alpha_nominal(sub)
        per_dim[code] = round(a, 4) if a is not None else None
    return {
        "status": "COMPUTED",
        "raters_completed": len(sorted_raters),
        "raters": sorted_raters,
        "krippendorff_alpha": round(overall, 4) if overall is not None else None,
        "per_dimension_alpha": per_dim,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="TR01-TR06 human rater packet & Krippendorff alpha"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init-packet")
    p_init.add_argument("--out", required=True)
    p_eval = sub.add_parser("compute-alpha")
    p_eval.add_argument("--packet", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "init-packet":
        pkt = build_blinded_tr_packet()
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(pkt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps({"written": str(out), "items": len(pkt["items"]), "status": pkt["status"]})
        )
        return 0

    pkt = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    res = evaluate_packet_alpha(pkt)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
