"""Unit tests for Phase-3 library (`scripts/venue_phase3_lib.py`)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from venue_phase2_lib import FIVE_WORLD_IDS
from venue_phase3_lib import (
    PHASE3_MODELS,
    build_5world_godot_specs,
    build_procedural_multihop_scaling_benchmark,
    chi2_sf,
    cochrans_q,
    extract_last_schema_dict,
    fleiss_kappa,
    krippendorff_alpha_nominal,
)

from nesy_game.contracts import ActionPolicy, CandidateAction, WorldState


def test_extract_last_schema_dict_handles_concatenated_outputs() -> None:
    env1 = {"response": '{"ok": false}\n{"ok": true, "reason": "final"}\n'}
    got1 = extract_last_schema_dict(env1, ("ok", "reason"))
    assert got1 == {"ok": True, "reason": "final"}

    env2 = {
        "response": 'Preface\n```json\n{"leak": true, "reason": "draft"}\n```\n'
        'Final:\n```json\n{"leak": false, "reason": "verified"}\n```'
    }
    got2 = extract_last_schema_dict(env2, ("leak", "reason"))
    assert got2 == {"leak": False, "reason": "verified"}

    env3 = {"structured_output": {"leak": True, "reason": "native"}}
    assert extract_last_schema_dict(env3, ("leak", "reason")) == {
        "leak": True,
        "reason": "native",
    }
    assert extract_last_schema_dict({"response": "not json"}, ("leak",)) is None


def test_statistical_helpers_cochran_fleiss_krippendorff() -> None:
    # Exact analytical checks: df=2 chi2_sf(x, 2) == exp(-x/2); df=1 == erfc(sqrt(x/2))
    assert math.isclose(chi2_sf(4.0, 2), math.exp(-2.0), rel_tol=1e-9)
    assert math.isclose(chi2_sf(3.84145882, 1), 0.05, abs_tol=1e-6)
    assert math.isclose(chi2_sf(9.21034037, 2), 0.01, abs_tol=1e-6)
    assert chi2_sf(20.0, 4) < 0.001

    # Tied matrix gives Q=0, p=1
    q_tied = cochrans_q([[1, 1, 1], [0, 0, 0], [1, 1, 1]])
    assert q_tied["q_stat"] == 0.0 and q_tied["p_value"] == 1.0

    # Differing arms yield significant Cochran Q
    q_diff = cochrans_q([[1, 0, 0]] * 12 + [[1, 1, 0]] * 6)
    assert q_diff["q_stat"] > 10.0 and q_diff["p_value"] < 0.01

    # Perfect inter-rater agreement gives kappa=1.0 and alpha=1.0
    assert fleiss_kappa([[3, 0], [0, 3], [3, 0], [0, 3]]) == 1.0
    assert krippendorff_alpha_nominal([[1, 1, 1], [0, 0, 0], [1, 1, None], [0, 0, 0]]) == 1.0
    # Slight disagreement reduces alpha below 1.0
    alpha_partial = krippendorff_alpha_nominal([[1, 1, 0], [0, 0, 0], [1, 1, 1], [0, 0, 0]])
    assert 0.3 < alpha_partial < 0.9


def test_p9_procedural_multihop_480_cases_and_datalog_oracle() -> None:
    res = build_procedural_multihop_scaling_benchmark()
    assert res["total_cases"] == 480
    assert res["oracle_mismatches"] == 0
    assert res["oracle_agreement_rate"] == 1.0

    gates = res["overall_gates"]
    assert gates["multihop_ontology_gate"]["accuracy"] == 1.0
    assert gates["multihop_ontology_gate"]["unsafe_leaks"] == 0
    assert gates["bounded_2hop_gate"]["unsafe_leaks"] > 0
    assert gates["flat_1hop_gate"]["unsafe_leaks"] > gates["bounded_2hop_gate"]["unsafe_leaks"]
    assert res["by_depth"]["2"]["flat_1hop_gate"]["unsafe_leaks"] > 0
    assert res["by_depth"]["2"]["bounded_2hop_gate"]["unsafe_leaks"] == 0
    assert res["by_depth"]["3"]["bounded_2hop_gate"]["unsafe_leaks"] > 0
    assert res["by_depth"]["5"]["multihop_ontology_gate"]["unsafe_leaks"] == 0
    assert res["cochrans_q"]["p_value"] < 1e-10


def test_5world_godot_specs_and_model_panel() -> None:
    assert len(PHASE3_MODELS) == 3
    specs = build_5world_godot_specs()
    worlds = specs["worlds"]
    assert tuple(worlds.keys()) == FIVE_WORLD_IDS
    for qid, spec in worlds.items():
        assert spec["quest_id"] == qid
        assert spec["goal_fact"]
        assert spec["forbidden_fact"]
        assert len(spec["policies"]) >= 2
        assert len(spec["canonical_world_state_sha256"]) == 64

    # Smoke check WorldState construction compatibility with CandidateAction
    _ = (ActionPolicy, CandidateAction, WorldState)


def test_phase3_archived_receipts_croissant_v3_and_anonymization() -> None:
    import hashlib
    import json
    import re

    supp_dir = ROOT / "research/green-supplements"
    v1 = json.loads((supp_dir / "croissant_trace_rpg_benchmark.json").read_text(encoding="utf-8"))
    v2 = json.loads(
        (supp_dir / "croissant_trace_rpg_benchmark_v2.json").read_text(encoding="utf-8")
    )
    v3 = json.loads(
        (supp_dir / "croissant_trace_rpg_benchmark_v3.json").read_text(encoding="utf-8")
    )
    assert len(v1["distribution"]) == 6
    assert len(v2["distribution"]) == 12
    assert len(v3["distribution"]) == 17
    for manifest in (v1, v2, v3):
        for item in manifest["distribution"]:
            target = supp_dir / item["name"]
            assert target.is_file(), f"Missing manifest artifact: {target}"
            assert hashlib.sha256(target.read_bytes()).hexdigest() == item["sha256"]

    p9 = json.loads(
        (supp_dir / "phase3_procedural_multihop_scaling_results.json").read_text(encoding="utf-8")
    )
    assert p9["total_cases"] == 480
    assert p9["oracle_mismatches"] == 0
    assert p9["overall_gates"]["multihop_ontology_gate"]["accuracy"] == 1.0

    p6 = json.loads(
        (supp_dir / "phase3_live_multiagent_3family_results.json").read_text(encoding="utf-8")
    )
    assert p6["total_episodes"] == 30
    assert p6["arms"]["trace_rpg_multihop_rho_k2"]["zero_leak_episodes"] == 30
    assert p6["arms"]["trace_rpg_multihop_rho_k2"]["safe_milestone_episodes"] == 16

    p7 = json.loads(
        (supp_dir / "phase3_crossfamily_shield_90_results.json").read_text(encoding="utf-8")
    )
    assert p7["total_tasks"] == 90
    assert p7["tasks_parsed"] == 87
    assert p7["arms"]["trace_rpg_multihop_rho_k2"]["noisy_policy_safe_commits"] == 30
    assert p7["arms"]["trace_rpg_multihop_rho_k2"]["unsafe_commits"] == 0

    p8 = json.loads(
        (supp_dir / "phase3_crossfamily_multisecret_escape_results.json").read_text(
            encoding="utf-8"
        )
    )
    assert p8["total_cases"] == 180
    assert len(p8["inter_verifier_agreement"]["families"]) == 3
    assert p8["inter_verifier_agreement"]["fleiss_kappa"] > 0.9
    assert "gpt-oss-120b-medium" in p8["quota_notes"]

    p10 = json.loads(
        (supp_dir / "phase3_multiworld_godot_closed_loop_results.json").read_text(encoding="utf-8")
    )
    assert p10["combined_episodes"] == 50
    assert p10["combined_replay_valid"] == 50
    assert p10["combined_unsafe_commits"] == 0
    assert p10["informed_cohort_20ep"]["total_godot_goals"] == 20
    assert p10["epistemic_blindspot_cohort_30ep"]["total_episodes"] == 30

    forbidden = re.compile(
        r"Jangyoung|Jeong|Shinjin|Kang|Hongik|akillness|정장영|강신진|홍익|127\.0\.0\.1",
        re.IGNORECASE,
    )
    for fpath in [*sorted(supp_dir.glob("phase3_*.json")), supp_dir / "DATASHEET_v3.md"]:
        assert not forbidden.search(fpath.read_text(encoding="utf-8")), f"PII/IP leak in {fpath}"


def test_build_neurips_supplement_v3_archive_and_reproduce(tmp_path: Path) -> None:
    import json
    import subprocess
    import zipfile

    from build_neurips_supplement import build_neurips_supplement

    zip_path = tmp_path / "neurips-db-supplemental-benchmark.zip"
    summary = build_neurips_supplement(zip_path)
    assert summary["croissant_v2_verified"] == "12/12"
    assert summary["croissant_v3_verified"] == "17/17"
    assert summary["anon_pii_leaks"] == 0

    extract_dir = tmp_path / "extracted"
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)
    cro_v3 = json.loads(
        (extract_dir / "data/croissant_trace_rpg_benchmark_v3.json").read_text(encoding="utf-8")
    )
    assert len(cro_v3["distribution"]) == 17
    assert all(item["contentUrl"].startswith("data/") for item in cro_v3["distribution"])

    proc = subprocess.run(
        [sys.executable, "reproduce_benchmark.py"],
        cwd=str(extract_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    rep = json.loads(proc.stdout)
    assert rep["status"] == "PASS"
    assert rep["croissant_v2_sha256_verified"] == "12/12"
    assert rep["croissant_v3_sha256_verified"] == "17/17"
    assert rep["phase3_p10_godot_50ep"]["combined_replays_valid"] == "50/50"
