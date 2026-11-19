"""Tests for Phase-6 P18 Real External KR Solvers & Large-Scale KB Benchmark.

Verifies:
1. Instance generation invariants (1,080 cases, R=256 >= 1000 facts/edges).
2. Pure Python / nesy Datalog evaluation and heuristic baseline behaviors.
3. External KR solvers (clingo, z3, owl2_rl) using pytest.importorskip so tests
   pass cleanly both in default environments and with extra solvers installed.
4. Stratified OWL 2 RL case counts (45 P18B + 120 P18A = 165 total certified cases).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts directory is in path
scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))

from venue_phase6_kr_lib import (
    compute_latency_stats,
    eval_bounded_2hop,
    eval_clingo_asp,
    eval_flat_1hop,
    eval_nesy_multihop,
    eval_owl2_rl,
    eval_z3_smt,
    generate_p18b_cases,
    get_solver_versions,
)

from nesy_game.multihop import MultihopOntologySpec


def test_solver_versions_structure() -> None:
    versions = get_solver_versions()
    assert "python" in versions
    assert "nesy_game" in versions
    for pkg in ("clingo", "z3-solver", "rdflib", "owlrl"):
        assert pkg in versions


def test_latency_stats_computation() -> None:
    empty_stats = compute_latency_stats([])
    assert empty_stats == {}

    times = [1.0, 2.0, 3.0, 4.0, 5.0, 10.0, 20.0]
    stats = compute_latency_stats(times, baseline_p50_ms=2.0)
    assert stats["n_evals"] == 7
    assert stats["p50_ms"] == 4.0
    assert stats["p50_us"] == 4000.0
    assert stats["budget_60hz_pass_rate"] == pytest.approx(6 / 7, abs=1e-4)  # 6 out of 7 <= 16.667
    assert stats["budget_120hz_pass_rate"] == pytest.approx(5 / 7, abs=1e-4)  # 5 out of 7 <= 8.333
    assert stats["speedup_vs_nesy"] == 0.5


def test_p18b_instance_generation_and_invariants() -> None:
    cases = generate_p18b_cases()
    assert len(cases) == 1080

    r_vals = {c.R for c in cases}
    assert r_vals == {8, 16, 32, 64, 128, 256}

    d_vals = {c.d for c in cases}
    assert d_vals == {1, 2, 3, 5, 8, 10}

    topos = {c.topology for c in cases}
    assert topos == {"linear_chain", "diamond_dag", "cyclic_role_hierarchy"}

    leaks = sum(1 for c in cases if c.oracle_deny)
    safes = sum(1 for c in cases if not c.oracle_deny)
    assert leaks == 540
    assert safes == 540

    # Invariant: R=256 instances must have >= 1,000 facts and >= 1,000 implication edges
    r256_cases = [c for c in cases if c.R == 256]
    assert len(r256_cases) == 180
    for c in r256_cases:
        assert c.num_facts >= 1000, f"Case {c.instance_id} has {c.num_facts} < 1000 facts"
        assert c.num_implication_edges >= 1000, (
            f"Case {c.instance_id} has {c.num_implication_edges} < 1000 edges"
        )


def test_datalog_vs_heuristics_multihop_divergence() -> None:
    """Verifies that flat_1hop and bounded_2hop fail on multi-hop depth >= 3."""
    # 3-hop linear chain
    spec_3hop = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"], "r2": ["r_forbidden"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"], "f2": ["f_forbidden"]},
        forbidden_by_role={"r_forbidden": ["f_forbidden"]},
        min_stage_by_fact={"f_forbidden": 1},
    )

    # Datalog correctly detects the 3-hop leak
    assert eval_nesy_multihop(spec_3hop, "actor", "f0", quest_stage=5) is True

    # Flat 1-hop misses it completely
    assert eval_flat_1hop(spec_3hop, "actor", "f0", quest_stage=5) is False

    # Bounded 2-hop misses it because it reaches at most r1 and f1
    assert eval_bounded_2hop(spec_3hop, "actor", "f0", quest_stage=5) is False

    # 1-hop case: 1 parent + 1 implication -> passes bounded_2hop, fails flat_1hop
    spec_1hop = MultihopOntologySpec(
        role_parents={"actor": ["r_forbidden"]},
        fact_implications={"f0": ["f_forbidden"]},
        forbidden_by_role={"r_forbidden": ["f_forbidden"]},
        min_stage_by_fact={"f_forbidden": 1},
    )
    assert eval_nesy_multihop(spec_1hop, "actor", "f0", quest_stage=5) is True
    assert eval_flat_1hop(spec_1hop, "actor", "f0", quest_stage=5) is False
    assert eval_bounded_2hop(spec_1hop, "actor", "f0", quest_stage=5) is True

    # 0-hop case: direct actor forbidden f0 -> passes both flat_1hop and bounded_2hop
    spec_0hop = MultihopOntologySpec(
        role_parents={},
        fact_implications={},
        forbidden_by_role={"actor": ["f0"]},
        min_stage_by_fact={"f0": 1},
    )
    assert eval_nesy_multihop(spec_0hop, "actor", "f0", quest_stage=5) is True
    assert eval_flat_1hop(spec_0hop, "actor", "f0", quest_stage=5) is True
    assert eval_bounded_2hop(spec_0hop, "actor", "f0", quest_stage=5) is True


def test_clingo_asp_solver_live() -> None:
    pytest.importorskip("clingo")

    # Leak case: role inheritance + implication
    spec_leak = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"]},
        forbidden_by_role={"r2": ["f2"]},
        min_stage_by_fact={"f2": 2},
    )
    assert eval_clingo_asp(spec_leak, "actor", "f0", quest_stage=5) is True
    assert eval_nesy_multihop(spec_leak, "actor", "f0", quest_stage=5) is True

    # Safe case
    spec_safe = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"]},
        forbidden_by_role={"r2": ["f_unrelated"]},
        min_stage_by_fact={"f2": 2},
    )
    assert eval_clingo_asp(spec_safe, "actor", "f0", quest_stage=5) is False
    assert eval_nesy_multihop(spec_safe, "actor", "f0", quest_stage=5) is False


def test_z3_smt_solver_live() -> None:
    pytest.importorskip("z3")

    spec_leak = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"]},
        forbidden_by_role={"r2": ["f2"]},
        min_stage_by_fact={"f2": 2},
    )
    assert eval_z3_smt(spec_leak, "actor", "f0", quest_stage=5) is True
    assert eval_nesy_multihop(spec_leak, "actor", "f0", quest_stage=5) is True

    spec_safe = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"]},
        forbidden_by_role={"r2": ["f_unrelated"]},
        min_stage_by_fact={"f2": 2},
    )
    assert eval_z3_smt(spec_safe, "actor", "f0", quest_stage=5) is False
    assert eval_nesy_multihop(spec_safe, "actor", "f0", quest_stage=5) is False


def test_owl2_rl_solver_live() -> None:
    pytest.importorskip("rdflib")
    pytest.importorskip("owlrl")

    spec_leak = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"]},
        forbidden_by_role={"r2": ["f2"]},
        min_stage_by_fact={"f2": 2},
    )
    assert eval_owl2_rl(spec_leak, "actor", "f0", quest_stage=5) is True
    assert eval_nesy_multihop(spec_leak, "actor", "f0", quest_stage=5) is True

    spec_safe = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"]},
        fact_implications={"f0": ["f1"], "f1": ["f2"]},
        forbidden_by_role={"r2": ["f_unrelated"]},
        min_stage_by_fact={"f2": 2},
    )
    assert eval_owl2_rl(spec_safe, "actor", "f0", quest_stage=5) is False
    assert eval_nesy_multihop(spec_safe, "actor", "f0", quest_stage=5) is False


def test_cyclic_knowledge_base_termination() -> None:
    """Verifies that cyclic KBs terminate cleanly across all solvers."""
    spec_cyclic = MultihopOntologySpec(
        role_parents={"actor": ["r1"], "r1": ["r2"], "r2": ["r1"]},  # cycle r1 <-> r2
        fact_implications={"f0": ["f1"], "f1": ["f2"], "f2": ["f1"]},  # cycle f1 <-> f2
        forbidden_by_role={"r2": ["f2"]},
        min_stage_by_fact={"f2": 2},
    )
    # Should detect leak without infinite loop
    assert eval_nesy_multihop(spec_cyclic, "actor", "f0", quest_stage=5) is True

    try:
        import clingo  # noqa: F401

        assert eval_clingo_asp(spec_cyclic, "actor", "f0", quest_stage=5) is True
    except ImportError:
        pass

    try:
        import z3  # noqa: F401

        assert eval_z3_smt(spec_cyclic, "actor", "f0", quest_stage=5) is True
    except ImportError:
        pass

    try:
        import owlrl  # noqa: F401
        import rdflib  # noqa: F401

        assert eval_owl2_rl(spec_cyclic, "actor", "f0", quest_stage=5) is True
    except ImportError:
        pass


def test_owl2_rl_stratified_subset_count() -> None:
    cases = generate_p18b_cases()
    owl_cases = [
        c
        for c in cases
        if c.case_idx == 0
        and (c.R in (8, 16) or (c.R == 32 and c.d in (1, 5)) or (c.R == 64 and c.d == 5))
    ]
    assert len(owl_cases) == 45
    # Total certified OWL 2 RL cases across benchmark: 120 (P18A) + 45 (P18B) = 165
    assert len(owl_cases) + 120 == 165


def test_phase6_kr_results_file_if_present() -> None:
    results_path = (
        Path(__file__).resolve().parent.parent
        / "research"
        / "green-supplements"
        / "phase6_kr_external_solvers_results.json"
    )
    if not results_path.exists():
        pytest.skip("Benchmark results file not yet generated")

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)
    p18a = data["p18a_5world_equivalence"]
    p18b = data["p18b_large_scale_kb"]
    assert p18a["mismatches"]["owl2_rl"] == 0
    assert p18a["solver_stats"]["owl2_rl"]["n_evals"] == 120
    assert p18b["owl_subset_cases"] == 45
    assert p18b["solvers"]["owl2_rl"]["correct"] == 45
    assert p18b["solvers"]["owl2_rl"]["total"] == 45
    total_owl_certified = (
        p18a["solver_stats"]["owl2_rl"]["n_evals"] + p18b["solvers"]["owl2_rl"]["total"]
    )
    assert total_owl_certified == 165
