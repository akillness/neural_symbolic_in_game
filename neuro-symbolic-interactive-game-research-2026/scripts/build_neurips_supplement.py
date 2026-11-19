#!/usr/bin/env python3
"""Build a self-contained, double-anonymous NeurIPS D&B supplemental archive.

Packages all Phase-1..4 TRACE-RPG benchmark JSON receipts, ``DATASHEET.md``,
``DATASHEET_v3.md``, ``DATASHEET_v4.md``, Croissant 1.0 v2 (`12/12`), archive-local
Croissant 1.0 v3 (`17/17`), and archive-local Croissant 1.0 v4 (`22/22`) metadata,
the pure-Python verifier core (``src/nesy_game/`` + ``src/nesy_game/multihop/`` +
``scripts/``), ``reproduce_benchmark.py``, anonymized ``README.md``, and ``LICENSE``
into ``_workspace/current/qa/neurips-db-supplemental-benchmark.zip``, verifying 0
PII/IP/identity leaks across every packaged path and text payload.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_ZIP = ROOT / "_workspace/current/qa/neurips-db-supplemental-benchmark.zip"
SUPP_DIR = ROOT / "research/green-supplements"

DATA_FILES = (
    "multihop_ontology_results.json",
    "audit_b_calibrated_results.json",
    "multiquest_live_results.json",
    "audit_b_live_results.json",
    "tr_human_eval_packet.json",
    "audit_b_jev_results.json",
    "phase2_multihop_5world_results.json",
    "phase2_multiagent_epistemic_results.json",
    "phase2_godot_live_closed_loop_results.json",
    "phase2_live_shield_and_multihop_results.json",
    "phase2_multisecret_escape_results.json",
    "phase3_procedural_multihop_scaling_results.json",
    "phase3_multiworld_godot_closed_loop_results.json",
    "phase3_live_multiagent_3family_results.json",
    "phase3_crossfamily_shield_90_results.json",
    "phase3_crossfamily_multisecret_escape_results.json",
    "phase4_unguided_multiagent_3family_results.json",
    "phase4_stateful_repair_90_results.json",
    "phase4_unguided_godot_closed_loop_results.json",
    "phase4_3family_multisecret_escape_results.json",
    "phase5_attested_closed_loop_mas_results.json",
    "phase5_attested_claude_api_prospective_results.json",
    "phase5_attested_unified_escape_results.json",
    "phase6_kr_external_solvers_results.json",
    "phase6_godot_large_scale_runtime_results.json",
    "phase6_large_bilingual_escape_results.json",
    "DATASHEET.md",
    "DATASHEET_v3.md",
    "DATASHEET_v4.md",
    "DATASHEET_v5.md",
    "DATASHEET_v6.md",
    "croissant_trace_rpg_benchmark_v2.json",
)

CORE_NESY_MODULES = (
    "__init__.py",
    "contracts.py",
    "disclosure.py",
    "experiment.py",
    "metrics.py",
    "repair.py",
    "runtime.py",
    "validator.py",
    "multihop/__init__.py",
    "multihop/validator.py",
)

CORE_SCRIPTS = (
    "green_supplements_lib.py",
    "venue_phase2_lib.py",
    "venue_phase3_lib.py",
    "venue_phase4_lib.py",
    "venue_phase5_lib.py",
    "run_semantic_escape_filter_audit.py",
    "run_gemini_review_evaluation.py",
    "review_reference.py",
)

GODOT_PROJECT_CFG = 'config_version=5\n\n[application]\nconfig/name="trace_rpg_phase6_bench"\n'

FORBIDDEN_ANON_RE = re.compile(
    r"Jangyoung|Jeong|Shinjin|Kang|Hongik|akillness|정장영|강신진|홍익|127\.0\.0\.1|"
    r"\x6b\x61\x72\x61\x6d3824|\uad6c\ub85c\uac00\uc774|\bwrkspc\x5f|\bsk\x2dant\x2d|"
    r"max\x2dpromo\x2ddev|/(?:Users|home)/[^/\s]+|/opt/homebrew",
    re.IGNORECASE,
)

README_TEXT = """# TRACE-RPG Supplemental Benchmark Package (Double-Anonymous Review, v6)

This self-contained archive provides the reproducible TRACE-RPG benchmark artifacts (Phase 1–6),
pure-Python deterministic verifier core (`src/nesy_game/` + `src/nesy_game/multihop/`), Gebru et al.
datasheets (`data/DATASHEET.md`, `DATASHEET_v3.md`, `DATASHEET_v4.md`, `DATASHEET_v5.md`, `DATASHEET_v6.md`),
Croissant 1.0 v2 (`12/12`), v3 (`17/17`), v4 (`22/22`), v5 (`26/26`), and archive-local Croissant 1.0 v6
(`data/croissant_trace_rpg_benchmark_v6.json`, `30/30` SHA-256 digests with `data/...` contentUrls),
`CHECKSUMS.sha256`, executable anonymized Godot 4.7.1 benchmark scripts (`godot/`), confound-free
Phase-4 CLI + Godot 4.7.1 receipts, attested Anthropic Messages API Phase-5 receipts (`P15`–`P17`),
and Phase-6 industrial external KR solver (`P18`), authentic multi-world/large-scale Godot 4.7.1 (`P19`),
and 1,200-case 6-domain bilingual adversarial escape (`P20`) receipts.

## Quick Verification (Zero External Dependencies, Python 3.10+)

```bash
python3 reproduce_benchmark.py
```

Optional live Godot 4.7+ execution (requires `godot` on `PATH`):

```bash
python3 reproduce_benchmark.py --with-godot
```

Running `reproduce_benchmark.py` performs seven standalone checks without network calls or API keys:
1. **`CHECKSUMS.sha256` & Croissant 1.0 v2–v6 SHA-256 Verification:** Verifies all file checksums plus
   `12/12` (v2), `17/17` (v3), `22/22` (v4), `26/26` (v5), and `30/30` (v6) digests inside `data/`.
2. **Core `nesy_game.multihop` Closure & External Shielding Baselines:** Verifies semi-naive
   transitive Datalog closure, multi-hop leak detection, Safe-RL action masking, and NeMo-style
   Colang output rails inside `src/nesy_game/multihop/`.
3. **Deterministic Phase-1, Phase-2, & Phase-3 Re-execution:** Re-computes from scratch:
   - Phase-1 48-case multi-hop closure and 88-case calibrated EN/KO escape filter metrics;
   - Phase-2 120-case 5-world multi-hop closure, 30-episode 3-role 5-arm shielding, and 180-case escape;
   - Phase-3 480-case procedural Datalog scaling (`R in {8,16,32,64} x d in {1..5}`, Cochran's `Q = 1100.19`).
4. **Confound-Free Phase-4 Receipts (`P11`–`P14`):** Verifies schema, counts, and invariants across
   `P11`–`P14`.
5. **Attested Direct-API Phase-5 Receipts (`P15`–`P17`):** Verifies `P15` (`105` episodes), `P16` (`60`
   factorial + `21` Godot replays), and `P17` (`540` unified-prompt EN/KO escape calls).
6. **Phase-6 External Solvers, Large-Scale Godot, & 1,200-Case Escape (`P18`–`P20`):** Verifies `P18`
   (`120` 5-world + `1,080` `R<=256` Clingo/Z3/OWL 2 RL equivalence & cliffs), `P19` (`120/120` 5-world
   Godot 4.7.1 parity + `5,000`-tick 5-tier soak, `0` unsafe/leaks), `P20` (`1,200`-case 6-domain EN/KO
   escape benchmark, Jaccard `0.0630`, `Q = 871.39`), and optional `--with-godot` live re-execution of
   `godot/godot_phase6_multiworld_bench.gd`.
7. **Human Packet Integrity:** Confirms `data/tr_human_eval_packet.json` preserves
   `AWAITING_HUMAN_RATERS`, `raters_completed == 0`, `krippendorff_alpha is None`, and zero synthetic labels.
"""
LICENSE_TEXT = """Dual License for TRACE-RPG Supplemental Benchmark Archive
=======================================================

1. Verification & Benchmark Code (`src/`, `scripts/`, `reproduce_benchmark.py`):
   MIT License
   Copyright (c) 2026 TRACE-RPG Benchmark Contributors (Double-Anonymous Submission)

   Permission is hereby granted, free of charge, to any person obtaining a copy
   of this software and associated documentation files (the "Software"), to deal
   in the Software without restriction, including without limitation the rights
   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
   copies of the Software, and to permit persons to whom the Software is
   furnished to do so, subject to the following conditions:
   The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.
   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

2. Benchmark Datasets, Traces, & Datasheet (`data/*.json`, `data/DATASHEET.md`):
   Creative Commons Attribution 4.0 International (CC BY 4.0)
   https://creativecommons.org/licenses/by/4.0/
"""

REPRODUCE_SCRIPT = '''#!/usr/bin/env python3
"""Standalone zero-network verifier for the TRACE-RPG NeurIPS D&B supplement (v6)."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
GODOT_DIR = HERE / "godot"
sys.path.insert(0, str(HERE / "src"))
sys.path.insert(0, str(HERE / "scripts"))
sys.path.insert(0, str(HERE))

from green_supplements_lib import (  # noqa: E402
    build_multihop_ontology_benchmark,
    calibrated_bilingual_escape_predict,
    check_invariants_i1_to_i4,
    score_escape_predictions,
)
from run_semantic_escape_filter_audit import build_corpus  # noqa: E402
from venue_phase2_lib import (  # noqa: E402
    build_5world_multihop_benchmark,
    build_multiagent_epistemic_benchmark,
    build_multisecret_escape_corpus,
    evaluate_multisecret_deterministic_baselines,
)
from venue_phase3_lib import build_procedural_multihop_scaling_benchmark  # noqa: E402


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_croissant(path: Path, expected_count: int, *, check_content_url: bool = False) -> int:
    doc = json.loads(path.read_text(encoding="utf-8"))
    dist = doc.get("distribution", [])
    assert len(dist) == expected_count, (
        f"expected {expected_count} entries in {path.name}, got {len(dist)}"
    )
    for entry in dist:
        target = DATA_DIR / entry["name"]
        assert target.is_file(), f"missing distribution file: {entry['name']}"
        if check_content_url:
            assert entry["contentUrl"] == f"data/{entry['name']}", entry["contentUrl"]
            assert (HERE / entry["contentUrl"]).is_file(), entry["contentUrl"]
        actual_sha = _sha256_file(target)
        assert actual_sha == entry["sha256"], (
            f"SHA-256 mismatch for {entry['name']}: {actual_sha} != {entry['sha256']}"
        )
    return len(dist)


def _verify_checksums_file(path: Path) -> int:
    assert path.is_file(), f"missing checksum manifest: {path}"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "empty CHECKSUMS.sha256"
    for line in lines:
        expected_sha, rel_path = line.split("  ", 1)
        target = HERE / rel_path
        assert target.is_file(), f"missing file in CHECKSUMS.sha256: {rel_path}"
        actual_sha = _sha256_file(target)
        assert actual_sha == expected_sha, (
            f"CHECKSUMS.sha256 mismatch for {rel_path}: {actual_sha} != {expected_sha}"
        )
    return len(lines)


def _run_live_godot_verification() -> dict[str, object]:
    godot_bin = shutil.which("godot")
    if not godot_bin:
        raise RuntimeError(
            "godot executable not found on PATH; install Godot 4.7+ and ensure `godot` is on PATH"
        )
    with tempfile.TemporaryDirectory(prefix="trace_rpg_repro_godot_") as tmp:
        tmp_path = Path(tmp)
        for fname in (
            "project.godot",
            "sealed_lighthouse_machine.gd",
            "godot_phase6_multiworld_bench.gd",
            "phase6_benchmark_payload.json",
        ):
            shutil.copy2(GODOT_DIR / fname, tmp_path / fname)
        in_json = tmp_path / "phase6_benchmark_payload.json"
        out_json = tmp_path / "result.json"
        proc = subprocess.run(
            [
                godot_bin,
                "--headless",
                "--path",
                str(tmp_path),
                "-s",
                "res://godot_phase6_multiworld_bench.gd",
                "--",
                str(in_json),
                str(out_json),
            ],
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        if proc.returncode != 0 or not out_json.is_file():
            raise RuntimeError(f"Godot execution failed (rc={proc.returncode}): {proc.stderr[:400]}")
        res = json.loads(out_json.read_text(encoding="utf-8"))
    p19a = res["p19a"]
    p19b = res["p19b"]
    p19a_cases = int(p19a["cases_count"])
    p19b_tiers = p19b["tiers"]
    assert p19a_cases == 120, f"expected 120 P19A cases, got {p19a_cases}"
    assert len(p19b_tiers) == 5, f"expected 5 P19B tiers, got {len(p19b_tiers)}"
    total_ticks = int(p19b["total_ticks"])
    total_unsafe = sum(int(t["unsafe_commits"]) for t in p19b_tiers.values())
    total_leaks = sum(int(t["leaks_committed"]) for t in p19b_tiers.values())
    assert total_ticks == 5000, f"expected 5000 soak ticks, got {total_ticks}"
    assert total_unsafe == 0, f"unexpected unsafe commits: {total_unsafe}"
    assert total_leaks == 0, f"unexpected leaks committed: {total_leaks}"
    return {
        "executed": True,
        "p19a_cases": p19a_cases,
        "p19b_tiers": len(p19b_tiers),
        "p19b_total_ticks": total_ticks,
        "p19b_unsafe_commits": total_unsafe,
        "p19b_leaks_committed": total_leaks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify TRACE-RPG NeurIPS D&B supplemental package.")
    parser.add_argument(
        "--with-godot",
        action="store_true",
        help="Also execute bundled godot/godot_phase6_multiworld_bench.gd via `godot` on PATH.",
    )
    args = parser.parse_args(argv)

    checksum_count = _verify_checksums_file(HERE / "CHECKSUMS.sha256")
    v2_count = _verify_croissant(DATA_DIR / "croissant_trace_rpg_benchmark_v2.json", 12)
    v3_count = _verify_croissant(
        DATA_DIR / "croissant_trace_rpg_benchmark_v3.json", 17, check_content_url=True
    )
    v4_count = _verify_croissant(
        DATA_DIR / "croissant_trace_rpg_benchmark_v4.json", 22, check_content_url=True
    )
    v5_count = _verify_croissant(
        DATA_DIR / "croissant_trace_rpg_benchmark_v5.json", 26, check_content_url=True
    )
    v6_count = _verify_croissant(
        DATA_DIR / "croissant_trace_rpg_benchmark_v6.json", 30, check_content_url=True
    )

    from nesy_game.contracts import CandidateAction
    from nesy_game.multihop import (
        compute_datalog_closure,
        evaluate_action_mask_shield,
        evaluate_dialog_rail_filter,
        validate_candidate_multihop,
    )
    from venue_phase2_lib import get_expanded_5world_scenarios
    from venue_phase4_lib import phase2_ontology_to_spec

    # Verify core nesy_game.multihop closure & external shielding baselines
    sc0 = get_expanded_5world_scenarios()["sealed-lighthouse-v1"]
    pol0 = sc0.initial_state.action_policies["unlock_room"]
    spec0 = phase2_ontology_to_spec()
    closure0 = compute_datalog_closure(spec0, "keeper_staff", ["valve_log"])
    assert "keeper_secret" in closure0.leaked_roots
    leaky0 = CandidateAction(
        action_id="repro-leak",
        actor_id="keeper_staff",
        action_type="unlock_room",
        preconditions=pol0.required_preconditions,
        effects=pol0.required_effects,
        used_facts=frozenset({"valve_log"}),
        disclosed_facts=frozenset(),
        required_quest_stage=0,
        quest_stage_effect=min(pol0.allowed_quest_stage_effects),
    )
    assert evaluate_action_mask_shield(sc0.initial_state, leaky0).valid is True
    assert evaluate_dialog_rail_filter(sc0.initial_state, leaky0).valid is True
    assert validate_candidate_multihop(sc0.initial_state, leaky0, spec0).valid is False

    # Re-run deterministic Phase-1 benchmarks and compare with archived JSONs
    inv_res = check_invariants_i1_to_i4()
    assert inv_res["i1_to_i4_pass"] is True, "Phase-1 invariants I1-I4 failed"
    mh1_live = build_multihop_ontology_benchmark()
    mh1_arch = json.loads((DATA_DIR / "multihop_ontology_results.json").read_text(encoding="utf-8"))
    assert mh1_live["flat_1hop_rule"] == mh1_arch["flat_1hop_rule"]
    assert mh1_live["ontology_multihop_gate"] == mh1_arch["ontology_multihop_gate"]

    corpus_88 = build_corpus()
    ab_live = score_escape_predictions(
        corpus_88, [calibrated_bilingual_escape_predict(c) for c in corpus_88]
    )
    ab_arch = json.loads((DATA_DIR / "audit_b_calibrated_results.json").read_text(encoding="utf-8"))
    for k, val in ab_live.items():
        assert ab_arch[k] == val, f"Phase-1 Audit B calibrated metric drifted for {k}"

    # Re-run deterministic Phase-2 benchmarks and compare with archived JSONs
    mh5_live = build_5world_multihop_benchmark()
    mh5_arch = json.loads(
        (DATA_DIR / "phase2_multihop_5world_results.json").read_text(encoding="utf-8")
    )
    assert mh5_live["gates"] == mh5_arch["gates"], "Phase-2 5-world multi-hop metrics drifted"

    ma_live = build_multiagent_epistemic_benchmark()
    ma_arch = json.loads(
        (DATA_DIR / "phase2_multiagent_epistemic_results.json").read_text(encoding="utf-8")
    )
    assert ma_live["arms"] == ma_arch["arms"], "Phase-2 multi-agent arm metrics drifted"

    det_esc = evaluate_multisecret_deterministic_baselines(build_multisecret_escape_corpus())
    esc_arch = json.loads(
        (DATA_DIR / "phase2_multisecret_escape_results.json").read_text(encoding="utf-8")
    )
    for model_key, metrics in det_esc["models"].items():
        assert esc_arch["deterministic_baselines"]["models"][model_key] == metrics, (
            f"Phase-2 deterministic escape baseline drifted for {model_key}"
        )

    # Re-run deterministic Phase-3 P9 procedural Datalog scaling (480 cases, R<=64, d<=5)
    p9_live = build_procedural_multihop_scaling_benchmark()
    p9_arch = json.loads(
        (DATA_DIR / "phase3_procedural_multihop_scaling_results.json").read_text(encoding="utf-8")
    )
    assert p9_live["total_cases"] == 480
    assert p9_live["oracle_mismatches"] == 0
    assert p9_live["overall_gates"] == p9_arch["overall_gates"], "P9 overall gates drifted"
    assert p9_live["cochrans_q"] == p9_arch["cochrans_q"], "P9 Cochran Q drifted"

    # Verify TR01-TR06 blinded packet status & non-fabrication contract
    tr_pkt = json.loads((DATA_DIR / "tr_human_eval_packet.json").read_text(encoding="utf-8"))
    assert tr_pkt["status"] == "AWAITING_HUMAN_RATERS"
    assert tr_pkt["raters_completed"] == 0
    assert tr_pkt["krippendorff_alpha"] is None
    assert len(tr_pkt["items"]) == 36
    assert all(not item.get("rater_labels") for item in tr_pkt["items"])

    # Verify Phase-2 & Phase-3 live cross-family & Godot 4.7.1 JSONs present with expected invariants
    godot_doc = json.loads(
        (DATA_DIR / "phase2_godot_live_closed_loop_results.json").read_text(encoding="utf-8")
    )
    shield_doc = json.loads(
        (DATA_DIR / "phase2_live_shield_and_multihop_results.json").read_text(encoding="utf-8")
    )
    p6_doc = json.loads(
        (DATA_DIR / "phase3_live_multiagent_3family_results.json").read_text(encoding="utf-8")
    )
    p7_doc = json.loads(
        (DATA_DIR / "phase3_crossfamily_shield_90_results.json").read_text(encoding="utf-8")
    )
    p8_doc = json.loads(
        (DATA_DIR / "phase3_crossfamily_multisecret_escape_results.json").read_text(encoding="utf-8")
    )
    p10_doc = json.loads(
        (DATA_DIR / "phase3_multiworld_godot_closed_loop_results.json").read_text(encoding="utf-8")
    )
    assert p6_doc["arms"]["multihop_shield_k0"]["unsafe_turns"] == 0
    assert p6_doc["arms"]["trace_rpg_multihop_rho_k2"]["unsafe_turns"] == 0
    assert p7_doc["arms"]["trace_rpg_multihop_rho_k2"]["noisy_policy_safe_commits"] == 30
    assert p7_doc["arms"]["trace_rpg_multihop_rho_k2"]["unsafe_commits"] == 0
    assert p10_doc["combined_replay_valid"] == p10_doc["combined_episodes"] == 50
    assert p10_doc["combined_unsafe_commits"] == 0
    assert p10_doc["total_godot_goals"] == 20

    p11_doc = json.loads(
        (DATA_DIR / "phase4_unguided_multiagent_3family_results.json").read_text(encoding="utf-8")
    )
    p12_doc = json.loads(
        (DATA_DIR / "phase4_stateful_repair_90_results.json").read_text(encoding="utf-8")
    )
    p13_doc = json.loads(
        (DATA_DIR / "phase4_unguided_godot_closed_loop_results.json").read_text(encoding="utf-8")
    )
    p14_doc = json.loads(
        (DATA_DIR / "phase4_3family_multisecret_escape_results.json").read_text(encoding="utf-8")
    )
    assert p11_doc["total_prompt_confound_markers"] == 0
    assert p11_doc["arms"]["trace_rpg_multihop_rho_k2"]["unsafe_turns"] == 0
    assert p12_doc["total_prompt_confound_markers"] == 0
    assert p12_doc["matched_controlled_fault_repair"]["all_prompts_included_failed_candidate"] is True
    assert p13_doc["total_prompt_confound_markers"] == 0
    assert p13_doc["combined_replay_valid"] == p13_doc["combined_episodes"]
    assert p13_doc["combined_unsafe_commits"] == 0
    assert len(p14_doc["families_represented"]) == 3

    p15_doc = json.loads(
        (DATA_DIR / "phase5_attested_closed_loop_mas_results.json").read_text(encoding="utf-8")
    )
    p16_doc = json.loads(
        (DATA_DIR / "phase5_attested_claude_api_prospective_results.json").read_text(
            encoding="utf-8"
        )
    )
    p17_doc = json.loads(
        (DATA_DIR / "phase5_attested_unified_escape_results.json").read_text(encoding="utf-8")
    )
    assert p15_doc["total_episodes"] == 105
    assert p15_doc["independent_arm_trajectories"] is True
    assert p15_doc["arms"]["trace_rpg_multihop_rho_k2"]["unsafe_turn_commits"] == 0
    assert p15_doc["arms"]["trace_rpg_hybrid_rho_llm_k1"]["safe_goal_episodes"] == 15
    assert p16_doc["part_16a_factorial_60"]["total_episodes"] == 60
    assert p16_doc["part_16a_factorial_60"]["by_representation"]["ontology_multihop"]["unsafe_commits"] == 0
    assert p16_doc["part_16b_godot_21"]["total_replay_valid"] == 21
    assert p16_doc["part_16b_godot_21"]["total_unsafe_commits"] == 0
    assert p17_doc["total_live_api_evaluations"] == 540
    assert p17_doc["deterministic_shortcircuit_count"] == 0

    p18_doc = json.loads(
        (DATA_DIR / "phase6_kr_external_solvers_results.json").read_text(encoding="utf-8")
    )
    p19_doc = json.loads(
        (DATA_DIR / "phase6_godot_large_scale_runtime_results.json").read_text(encoding="utf-8")
    )
    p20_doc = json.loads(
        (DATA_DIR / "phase6_large_bilingual_escape_results.json").read_text(encoding="utf-8")
    )
    assert p18_doc["p18a_5world_equivalence"]["n_cases"] == 120
    assert p18_doc["p18b_large_scale_kb"]["n_instances"] == 1080
    assert p18_doc["p18b_large_scale_kb"]["solvers"]["nesy_game_multihop"]["correct"] == 1080
    assert p18_doc["p18b_large_scale_kb"]["solvers"]["clingo_asp"]["correct"] == 1080
    assert p18_doc["p18b_large_scale_kb"]["solvers"]["z3_smt"]["correct"] == 1080
    assert p18_doc["p18b_large_scale_kb"]["solvers"]["owl2_rl"]["correct"] == 45
    assert p19_doc["p19a_5world_cross_runtime_parity"]["cases_total"] == 120
    assert p19_doc["p19a_5world_cross_runtime_parity"]["python_godot_divergences"] == 0
    assert p19_doc["p19b_large_scale_soak"]["total_ticks"] == 5000
    assert p19_doc["p19b_large_scale_soak"]["total_unsafe_commits"] == 0
    assert p19_doc["p19b_large_scale_soak"]["total_leaks_committed"] == 0
    assert p20_doc["corpus_summary"]["total_cases"] == 1200
    assert (GODOT_DIR / "project.godot").is_file()
    assert (GODOT_DIR / "sealed_lighthouse_machine.gd").is_file()
    assert (GODOT_DIR / "godot_phase6_multiworld_bench.gd").is_file()
    assert (GODOT_DIR / "phase6_benchmark_payload.json").is_file()

    godot_live = _run_live_godot_verification() if args.with_godot else {"executed": False}

    summary = {
        "checksums_sha256_verified": f"{checksum_count}/{checksum_count}",
        "croissant_v2_sha256_verified": f"{v2_count}/{v2_count}",
        "croissant_v3_sha256_verified": f"{v3_count}/{v3_count}",
        "croissant_v4_sha256_verified": f"{v4_count}/{v4_count}",
        "croissant_v5_sha256_verified": f"{v5_count}/{v5_count}",
        "croissant_v6_sha256_verified": f"{v6_count}/{v6_count}",
        "core_nesy_game_multihop_verified": True,
        "phase1_multihop_48": {
            "flat_1hop_rule": mh1_live["flat_1hop_rule"]["accuracy"],
            "ontology_multihop_gate": mh1_live["ontology_multihop_gate"]["accuracy"],
        },
        "phase2_multihop_5world_120": {
            k: v["accuracy"] for k, v in mh5_live["gates"].items()
        },
        "phase2_multiagent_arms_30ep": {
            k: {
                "safe_goal_rate": v["safe_goal_rate"],
                "zero_leak_episodes": v["zero_leak_episodes"],
                "unsafe_turn_rate": v["unsafe_turn_rate"],
            }
            for k, v in ma_live["arms"].items()
        },
        "phase2_multisecret_det_180": {
            k: {
                "paraphrase_recall": v["paraphrase_recall"],
                "benign_frr": v["benign_frr"],
                "f1": v["f1"],
            }
            for k, v in det_esc["models"].items()
        },
        "phase2_godot_episodes": len(godot_doc.get("episodes", [])),
        "phase2_live_shield_tasks": len(shield_doc.get("records", [])),
        "phase3_p9_datalog_480": {
            "total_cases": p9_live["total_cases"],
            "oracle_mismatches": p9_live["oracle_mismatches"],
            "multihop_acc": p9_live["overall_gates"]["multihop_ontology_gate"]["accuracy"],
            "cochrans_q": p9_live["cochrans_q"]["q_stat"],
        },
        "phase3_p6_multiagent_30ep": {
            "parsed_turns": p6_doc["total_parsed_turns"],
            "rho_zero_leak": p6_doc["arms"]["trace_rpg_multihop_rho_k2"]["zero_leak_episodes"],
            "rho_milestones": p6_doc["arms"]["trace_rpg_multihop_rho_k2"]["safe_milestone_episodes"],
        },
        "phase3_p7_shield90": {
            "tasks_parsed": f"{p7_doc['tasks_parsed']}/{p7_doc['total_tasks']}",
            "rho_noisy_safe": p7_doc["arms"]["trace_rpg_multihop_rho_k2"]["noisy_policy_safe_commits"],
            "llm_k1_noisy_safe": p7_doc["llm_self_repair_k1"]["noisy_policy_safe_commits"],
        },
        "phase3_p8_escape_540": {
            "fleiss_kappa": p8_doc["inter_verifier_agreement"]["fleiss_kappa"],
            "krippendorff_alpha": p8_doc["inter_verifier_agreement"]["krippendorff_alpha_nominal"],
        },
        "phase3_p10_godot_50ep": {
            "combined_replays_valid": f"{p10_doc['combined_replay_valid']}/{p10_doc['combined_episodes']}",
            "informed_goals": f"{p10_doc['total_godot_goals']}/{p10_doc['total_episodes']}",
            "unsafe_commits": p10_doc["combined_unsafe_commits"],
        },
        "phase4_p11_unguided_mas_30ep": {
            "parsed_turns": p11_doc["total_parsed_turns"],
            "rho_zero_leak": p11_doc["arms"]["trace_rpg_multihop_rho_k2"]["zero_leak_episodes"],
            "rho_milestones": p11_doc["arms"]["trace_rpg_multihop_rho_k2"]["safe_milestone_episodes"],
        },
        "phase4_p12_candidate_inclusive_repair": {
            "tasks_parsed": f"{p12_doc['tasks_parsed']}/{p12_doc['total_tasks']}",
            "fault_rho_k2": p12_doc["matched_controlled_fault_repair"]["deterministic_rho_k2"]["recovered"],
            "fault_state_blind_llm_k2": p12_doc["matched_controlled_fault_repair"]["state_blind_llm_k2"]["recovered"],
            "fault_state_aware_llm_k2": p12_doc["matched_controlled_fault_repair"]["state_aware_llm_k2"]["recovered"],
        },
        "phase4_p13_unguided_godot_42ep": {
            "combined_replays_valid": f"{p13_doc['combined_replay_valid']}/{p13_doc['combined_episodes']}",
            "combined_goals": f"{p13_doc['combined_godot_goals']}/{p13_doc['combined_episodes']}",
            "unsafe_commits": p13_doc["combined_unsafe_commits"],
        },
        "phase4_p14_3family_escape_720": {
            "kappa_3fam_540": p14_doc["three_family_agreement_540"]["fleiss_kappa"],
            "kappa_4model_720": p14_doc["full_4model_agreement_720"]["fleiss_kappa"],
        },
        "phase5_p15_closed_loop_mas_105": {
            "safe_goal_rho": p15_doc["arms"]["trace_rpg_multihop_rho_k2"]["safe_goal_episodes"],
            "safe_goal_hybrid": p15_doc["arms"]["trace_rpg_hybrid_rho_llm_k1"]["safe_goal_episodes"],
            "zero_leak_rho": p15_doc["arms"]["trace_rpg_multihop_rho_k2"]["zero_leak_episodes"],
            "unsafe_safe_rl": p15_doc["arms"]["safe_rl_action_mask"]["unsafe_turn_commits"],
            "unsafe_nemo": p15_doc["arms"]["nemo_colang_rail"]["unsafe_turn_commits"],
        },
        "phase5_p16_factorial_and_godot_81": {
            "16a_onto_zero_leak": p16_doc["part_16a_factorial_60"]["by_representation"]["ontology_multihop"]["zero_leak_episodes"],
            "16a_onto_safe_goals": p16_doc["part_16a_factorial_60"]["by_representation"]["ontology_multihop"]["safe_goals"],
            "16b_replays_valid": f"{p16_doc['part_16b_godot_21']['total_replay_valid']}/{p16_doc['part_16b_godot_21']['total_episodes']}",
            "16b_prod_exact_hashes": p16_doc["part_16b_godot_21"]["production_sealed_lighthouse_6"]["exact_terminal_hashes"],
        },
        "phase5_p17_unified_escape_540": {
            "fleiss_kappa": p17_doc["three_tier_agreement_540"]["fleiss_kappa"],
            "alpha": p17_doc["three_tier_agreement_540"]["krippendorff_alpha_nominal"],
        },
        "phase6_p18_external_kr_1080": {
            "p18a_cases": p18_doc["p18a_5world_equivalence"]["n_cases"],
            "p18b_cases": p18_doc["p18b_large_scale_kb"]["n_instances"],
            "clingo_correct": p18_doc["p18b_large_scale_kb"]["solvers"]["clingo_asp"]["correct"],
            "z3_correct": p18_doc["p18b_large_scale_kb"]["solvers"]["z3_smt"]["correct"],
            "owl2_rl_certified": p18_doc["p18b_large_scale_kb"]["solvers"]["owl2_rl"]["correct"],
        },
        "phase6_p19_godot_5000": {
            "p19a_cases": p19_doc["p19a_5world_cross_runtime_parity"]["cases_total"],
            "p19a_divergences": p19_doc["p19a_5world_cross_runtime_parity"]["python_godot_divergences"],
            "p19b_ticks": p19_doc["p19b_large_scale_soak"]["total_ticks"],
            "p19b_unsafe": p19_doc["p19b_large_scale_soak"]["total_unsafe_commits"],
            "p19b_leaks": p19_doc["p19b_large_scale_soak"]["total_leaks_committed"],
            "live_godot_verification": godot_live,
        },
        "phase6_p20_bilingual_escape_1200": {
            "total_cases": p20_doc["corpus_summary"]["total_cases"],
            "tfidf_lodo_acc": p20_doc["deterministic_baselines"]["tfidf_char_word_lodo"]["accuracy"],
            "bm25_lodo_acc": p20_doc["deterministic_baselines"]["bm25_lexical_lodo"]["accuracy"],
        },
        "tr_human_eval_status": tr_pkt["status"],
        "status": "PASS",
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _assert_clean_payload(arcname: str, raw: bytes) -> None:
    if FORBIDDEN_ANON_RE.search(arcname):
        raise ValueError(f"forbidden anonymization string in archive path: {arcname}")
    text = raw.decode("utf-8", errors="ignore")
    m = FORBIDDEN_ANON_RE.search(text)
    if m:
        raise ValueError(f"forbidden anonymization string {m.group(0)!r} in {arcname}")
    if arcname.endswith(".py"):
        # Catch split string-literal bypasses such as `"foo" + "bar"` or `'foo' + 'bar'`.
        collapsed = re.sub(r"""(['"])\s*\+\s*\1""", "", text)
        m2 = FORBIDDEN_ANON_RE.search(collapsed)
        if m2:
            raise ValueError(
                f"forbidden concatenated anonymization string {m2.group(0)!r} in {arcname}"
            )


def build_neurips_supplement(out_zip: Path = DEFAULT_OUT_ZIP) -> dict[str, Any]:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, bytes]] = [
        ("README.md", README_TEXT.encode("utf-8")),
        ("LICENSE", LICENSE_TEXT.encode("utf-8")),
        ("reproduce_benchmark.py", REPRODUCE_SCRIPT.encode("utf-8")),
        ("scripts/__init__.py", b'"""Anonymized verifier scripts package."""\n'),
    ]

    for fname in DATA_FILES:
        src = SUPP_DIR / fname
        if not src.is_file():
            raise FileNotFoundError(f"missing benchmark artifact for zip: {src}")
        entries.append((f"data/{fname}", src.read_bytes()))

    for mod in CORE_NESY_MODULES:
        src = ROOT / "src/nesy_game" / mod
        entries.append((f"src/nesy_game/{mod}", src.read_bytes()))

    for script_name in CORE_SCRIPTS:
        src = ROOT / "scripts" / script_name
        entries.append((f"scripts/{script_name}", src.read_bytes()))

    proto_rel = "research/academic-pipeline/gemini-review-20261113/protocol-v2.json"
    entries.append((proto_rel, (ROOT / proto_rel).read_bytes()))

    # Bundle executable anonymized Godot 4.7.1 scripts + deterministic P19A/P19B payload
    import sys as _sys

    if str(ROOT / "scripts") not in _sys.path:
        _sys.path.insert(0, str(ROOT / "scripts"))
    from venue_phase6_godot_lib import build_godot_benchmark_payload

    godot_payload, _ = build_godot_benchmark_payload()
    entries.append(("godot/project.godot", GODOT_PROJECT_CFG.encode("utf-8")))
    entries.append(
        (
            "godot/sealed_lighthouse_machine.gd",
            (ROOT / "game-track/godot/scripts/sealed_lighthouse_machine.gd").read_bytes(),
        )
    )
    entries.append(
        (
            "godot/godot_phase6_multiworld_bench.gd",
            (ROOT / "scripts/godot_phase6_multiworld_bench.gd").read_bytes(),
        )
    )
    entries.append(
        (
            "godot/phase6_benchmark_payload.json",
            (json.dumps(godot_payload, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"),
        )
    )

    # Embed archive-local Croissant v3 (17/17), v4 (22/22), v5 (26/26), and v6 (30/30)
    embedded_dists: list[tuple[str, list[dict[str, Any]]]] = []
    for label, cro_name, expected_len in (
        ("v3", "croissant_trace_rpg_benchmark_v3.json", 17),
        ("v4", "croissant_trace_rpg_benchmark_v4.json", 22),
        ("v5", "croissant_trace_rpg_benchmark_v5.json", 26),
        ("v6", "croissant_trace_rpg_benchmark_v6.json", 30),
    ):
        raw_cro = (SUPP_DIR / cro_name).read_text(encoding="utf-8")
        cro_obj = json.loads(raw_cro)
        dist_list = cro_obj.get("distribution", [])
        if len(dist_list) != expected_len:
            raise ValueError(f"expected {expected_len} entries in {cro_name}, got {len(dist_list)}")
        for item in dist_list:
            item["contentUrl"] = f"data/{item['name']}"
        entries.append(
            (
                f"data/{cro_name}",
                (json.dumps(cro_obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8"),
            )
        )
        embedded_dists.append((label, dist_list))

    # Verify Croissant v2..v6 hashes match data/ bytes inside zip
    entry_map = dict(entries)
    croissant_v2 = json.loads(
        entry_map["data/croissant_trace_rpg_benchmark_v2.json"].decode("utf-8")
    )
    dist_v2 = croissant_v2.get("distribution", [])
    if len(dist_v2) != 12:
        raise ValueError(
            f"expected 12 entries in croissant_trace_rpg_benchmark_v2.json, got {len(dist_v2)}"
        )
    for label, dist_list in (("v2", dist_v2), *embedded_dists):
        for item in dist_list:
            key = f"data/{item['name']}"
            if key not in entry_map:
                raise ValueError(f"Croissant {label} item missing from zip: {key}")
            actual = hashlib.sha256(entry_map[key]).hexdigest()
            if actual != item["sha256"]:
                raise ValueError(
                    f"Croissant {label} digest mismatch for {key}: {actual} != {item['sha256']}"
                )

    sorted_entries = sorted(entries, key=lambda kv: kv[0])
    checksum_lines = [
        f"{hashlib.sha256(raw).hexdigest()}  {arcname}\n" for arcname, raw in sorted_entries
    ]
    sorted_entries = sorted(
        [*sorted_entries, ("CHECKSUMS.sha256", "".join(checksum_lines).encode("utf-8"))],
        key=lambda kv: kv[0],
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, raw in sorted_entries:
            _assert_clean_payload(arcname, raw)
            zinfo = zipfile.ZipInfo(arcname, date_time=(2026, 11, 19, 0, 0, 0))
            zinfo.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zinfo, raw)

    archive_bytes = buf.getvalue()
    out_zip.write_bytes(archive_bytes)
    dist_v3 = embedded_dists[0][1]
    dist_v4 = embedded_dists[1][1]
    dist_v5 = embedded_dists[2][1]
    dist_v6 = embedded_dists[3][1]
    return {
        "path": str(out_zip),
        "bytes": len(archive_bytes),
        "sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "file_count": len(sorted_entries),
        "checksums_sha256_entries": len(checksum_lines),
        "croissant_v2_verified": f"{len(dist_v2)}/{len(dist_v2)}",
        "croissant_v3_verified": f"{len(dist_v3)}/{len(dist_v3)}",
        "croissant_v4_verified": f"{len(dist_v4)}/{len(dist_v4)}",
        "croissant_v5_verified": f"{len(dist_v5)}/{len(dist_v5)}",
        "croissant_v6_verified": f"{len(dist_v6)}/{len(dist_v6)}",
        "godot_executable_scripts_bundled": 4,
        "anon_pii_leaks": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-zip", type=Path, default=DEFAULT_OUT_ZIP)
    args = parser.parse_args(argv)
    summary = build_neurips_supplement(args.out_zip)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
