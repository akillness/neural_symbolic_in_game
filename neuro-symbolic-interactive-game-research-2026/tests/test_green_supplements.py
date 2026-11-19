"""Unit tests for GREEN-readiness supplements (multi-quest, multi-hop ontology, Audit B, TR alpha, replay, Croissant)."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from compute_tr_alpha import (
    build_blinded_tr_packet,
    evaluate_packet_alpha,
    krippendorff_alpha_nominal,
)
from green_supplements_lib import (
    build_multihop_ontology_benchmark,
    calibrated_bilingual_escape_predict,
    check_invariants_i1_to_i4,
    execute_bounded_step,
    get_quest_scenarios,
    replay_episode_trace,
    score_escape_predictions,
)
from run_green_supplements import run_single_episode, write_croissant_metadata
from run_semantic_escape_filter_audit import build_corpus

AGENTS_TRACE_FIELDS = (
    "proposal",
    "evidence",
    "validation",
    "repair",
    "commit",
    "model_revision",
    "seed",
    "cost",
    "latency",
)


def test_multi_quest_progression_and_invariants() -> None:
    assert check_invariants_i1_to_i4()["i1_to_i4_pass"] is True
    scenarios = get_quest_scenarios()
    assert set(scenarios.keys()) == {
        "sealed-lighthouse-v1",
        "sunken-archive-v1",
        "clockwork-observatory-v1",
    }

    # Verify sunken-archive-v1 repairs an omitted required_effect and reaches goal safely
    sc = scenarios["sunken-archive-v1"]
    step1 = execute_bounded_step(
        sc.initial_state,
        {
            "action_id": "a1",
            "actor_id": "archivist",
            "action_type": "survey_atrium",
            "preconditions": ["at_atrium"],
            "effects": [],  # omitted drain_mapped -> repairable by rho
            "required_objects": [],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 0,
            "quest_stage_effect": 1,
        },
        sc,
        step_index=1,
        repair_budget=2,
    )
    assert step1["committed"] is True
    assert step1["repaired"] is True
    assert step1["unsafe_committed"] is False
    assert step1["would_commit_k0"] is False
    assert step1["would_commit_k1"] is True
    assert step1["would_commit_k2"] is True
    assert "flooded_vault" in step1["next_state"].reachable_locations


def test_multihop_ontology_breaks_flat_rule_parity() -> None:
    res = build_multihop_ontology_benchmark()
    assert res["total_cases"] == 48
    assert res["ontology_multihop_gate"]["accuracy"] == 1.0
    assert res["ontology_multihop_gate"]["unsafe_leaks_fn"] == 0
    assert res["flat_1hop_rule"]["unsafe_leaks_fn"] > 0
    assert res["unsafe_leak_reduction"] == res["flat_1hop_rule"]["unsafe_leaks_fn"]


def test_calibrated_bilingual_escape_filter_improves_frr() -> None:
    corpus = build_corpus()
    assert len(corpus) == 88
    preds = [calibrated_bilingual_escape_predict(c) for c in corpus]
    metrics = score_escape_predictions(corpus, preds)
    assert metrics["explicit_detected"].endswith("/16")
    assert metrics["paraphrase_detected"].endswith("/36")
    assert metrics["benign_false_rejections"].endswith("/36")
    assert metrics["explicit_recall"] == 1.0
    assert metrics["paraphrase_recall"] >= 0.50
    assert metrics["benign_frr"] <= 0.10


def test_krippendorff_alpha_exact_and_pending_gate() -> None:
    assert krippendorff_alpha_nominal([["PASS", "PASS"], ["FAIL", "FAIL"]]) == 1.0
    a_partial = krippendorff_alpha_nominal([["PASS", "PASS"], ["PASS", "FAIL"], ["FAIL", "FAIL"]])
    assert a_partial is not None and 0.0 < a_partial < 1.0

    pkt = build_blinded_tr_packet()
    assert len(pkt["items"]) == 36
    assert sum(i["committed"] and not i["repaired"] for i in pkt["items"]) == 12
    assert sum(i["committed"] and i["repaired"] for i in pkt["items"]) == 12
    assert sum(not i["committed"] and not i["repaired"] for i in pkt["items"]) == 12
    for item in pkt["items"]:
        assert "world_state_excerpt" in item
        assert "candidate_payload" in item
        assert "validation_errors" in item
        assert isinstance(item["committed"], bool)
        assert len(item["prior_hash"]) == 64
        assert len(item["final_hash"]) == 64
    res = evaluate_packet_alpha(pkt)
    assert res["status"] == "AWAITING_HUMAN_RATERS"
    assert res["krippendorff_alpha"] is None

    # Refuses single human rater
    pkt["items"][0]["rater_labels"] = {"rater_a": "PASS"}
    assert evaluate_packet_alpha(pkt)["status"] == "AWAITING_HUMAN_RATERS"


def test_episode_trace_provenance_counterfactual_k_and_strict_replay(tmp_path: Path) -> None:
    sc = get_quest_scenarios()["sealed-lighthouse-v1"]
    scripted = [
        {
            "action_id": "s1",
            "actor_id": "keeper",
            "action_type": "unlock_room",
            "preconditions": ["at_pier"],
            "effects": [],  # omitted beacon_unlocked -> repaired at attempt 1 (k0=False, k1=True)
            "required_objects": ["beacon_key"],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 0,
            "quest_stage_effect": 1,
            "narrative_text": "Unlocking beacon room.",
        },
        {
            "action_id": "s2",
            "actor_id": "keeper",
            "action_type": "restore_signal",
            "preconditions": ["beacon_unlocked"],
            "effects": ["signal_restored"],
            "required_objects": ["signal_lens"],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 1,
            "quest_stage_effect": 2,
            "narrative_text": "Restoring harbor signal.",
        },
        {
            "action_id": "s3",
            "actor_id": "keeper",
            "action_type": "reveal_hint",
            "preconditions": ["signal_restored"],
            "effects": ["hint_delivered"],
            "required_objects": [],
            "used_facts": ["tide_schedule"],
            "disclosed_facts": ["tide_schedule"],
            "required_quest_stage": 2,
            "quest_stage_effect": None,
            "narrative_text": "Sharing tide schedule.",
        },
    ]
    idx = [0]

    def fake_caller(_model: str, _prompt: str) -> dict:
        payload = scripted[idx[0]]
        idx[0] += 1
        return {
            "ok": True,
            "payload": payload,
            "raw_response": json.dumps(payload),
            "conversation_id": f"conv-{idx[0]}",
            "served_model_revision": "UNATTESTED_BY_CLI",
            "duration_seconds": 0.1,
            "wall_seconds": 0.12,
            "cost_usd": None,
            "cost_source": "cli_unreported",
            "usage": {"total_tokens": 100},
        }

    ep = run_single_episode(
        model="gemini-3.8-flash-medium",
        scenario=sc,
        representation="ontology_gate",
        repeat=1,
        repair_budget=2,
        turn_cache={},
        turn_cache_path=tmp_path / "turn_cache.jsonl",
        cli_version="1.5.11",
        caller=fake_caller,
    )
    assert ep["goal_reached"] is True
    assert ep["replay"]["replay_valid"] is True
    assert ep["k0_step_commits"] <= ep["k1_step_commits"] <= ep["k2_step_commits"]
    assert ep["k0_step_commits"] == 2
    assert ep["k1_step_commits"] == 3
    for turn in ep["turns"]:
        for key in AGENTS_TRACE_FIELDS:
            assert key in turn, f"missing AGENTS trace field {key}"

    # Tampered hash must fail replay
    tampered_hash = json.loads(json.dumps(ep))
    tampered_hash["turns"][0]["commit"]["final_hash"] = "0" * 64
    assert replay_episode_trace(tampered_hash)["replay_valid"] is False

    # Omitted candidate field or unknown key must fail allow_defaults=False replay
    tampered_key = json.loads(json.dumps(ep))
    tampered_key["turns"][0]["commit"]["committed_candidate"]["unexpected_key"] = True
    res_bad = replay_episode_trace(tampered_key)
    assert res_bad["replay_valid"] is False
    assert any("strict parse failed" in m for m in res_bad["mismatches"])


def test_croissant_metadata_generation_and_digests(tmp_path: Path) -> None:
    sample_a = tmp_path / "multihop_ontology_results.json"
    sample_a.write_text('{"ok":true}\n', encoding="utf-8")
    croissant = write_croissant_metadata(tmp_path)
    out_file = tmp_path / "croissant_trace_rpg_benchmark.json"
    assert out_file.is_file()
    assert croissant["@context"] == "http://mlcommons.org/croissant/1.0"
    assert croissant["@type"] == "sc:Dataset"
    assert croissant["version"] == "1.0.0"
    assert len(croissant["recordSet"]) == 4
    entry = croissant["distribution"][0]
    assert entry["name"] == "multihop_ontology_results.json"
    assert entry["sha256"] == hashlib.sha256(sample_a.read_bytes()).hexdigest()
