"""Unit and artifact-regression tests for the 5 deterministic 0-LLM engineering audits.

Covers:
1. Cross-artifact provenance, strict 0-LLM-call contract, coarse sanitized host
   metadata, and on-disk SHA-256 ``source_hashes`` verification (including clean-CI
   public-source projection when private ``reviewer-source.json`` is absent).
2. A1 (``run_multi_error_repair_audit.py``): family denominator partition
   (``96 + 160 + 96 == 352``), fixed-point vs period-2 oscillation classification,
   and simultaneous conflict-guard fixed-point behavior.
3. A2 (``run_latency_scaling_benchmark.py``): deterministic subset selection across
   set/hash orderings, ``active_constraint_arity_cap == 100`` saturation, and
   fail-closed ``ValueError`` guards that survive ``python -O``.
4. A3 (``run_traceability_seeded_audit.py``): seeded-corruption sensitivity across
   all 5 operators (with recomputed ``trace_hash``), zero false alarms across all 3
   invariance controls, ``--public-source-projection`` parity, and fail-closed
   ``ValueError`` rejection on tampered commitments.
5. A4 (``run_soak_and_refusal_probe.py``): ``validate_probe_report`` acceptance on
   valid payload, fail-closed ``ValueError`` rejection on missing refusal codes,
   memory-leak/probe failures, and state-hash drift, plus graceful ``"NR"``
   formatting in ``render_summary_markdown`` when ``soak_delta_mib`` is ``None``.
6. B (``run_semantic_escape_filter_audit.py``): out-of-fold LOO IDF isolation in
   ``TfidfCosineFilter.fit()``, zero exact text overlap between calibration
   prototypes and the 88-case evaluation corpus, and Stage-1 vs Stage-2 gating.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from nesy_game.contracts import (
    CandidateAction,
    ValidationError,
    ValidationResult,
    WorldState,
    parse_candidate_mapping,
)
from nesy_game.runtime import verify_trace_record
from scripts import run_latency_scaling_benchmark as a2_latency
from scripts import run_multi_error_repair_audit as a1_repair
from scripts import run_semantic_escape_filter_audit as b_escape
from scripts import run_soak_and_refusal_probe as a4_soak
from scripts import run_traceability_seeded_audit as a3_trace
from scripts.run_gemini_review_evaluation import _world_state

ROOT = Path(__file__).resolve().parents[1]

AUDIT_ARTIFACTS: tuple[tuple[str, str, str], ...] = (
    (
        "A1_multi_error_repair",
        "research/academic-pipeline/multi-error-repair-audit/results.json",
        "scripts/run_multi_error_repair_audit.py",
    ),
    (
        "A2_latency_scaling",
        "research/academic-pipeline/latency-scaling-benchmark/results.json",
        "scripts/run_latency_scaling_benchmark.py",
    ),
    (
        "A3_traceability_seeded",
        "research/traceability-scoring-20261023/seeded-control-audit-v1/results.json",
        "scripts/run_traceability_seeded_audit.py",
    ),
    (
        "A4_soak_and_refusal",
        "game-track/godot/docs/soak-and-refusal-probe-v1/results.json",
        "scripts/run_soak_and_refusal_probe.py",
    ),
    (
        "B_semantic_escape",
        "research/academic-pipeline/semantic-escape-filter-audit/results.json",
        "scripts/run_semantic_escape_filter_audit.py",
    ),
)

ALLOWED_ENV_KEYS = frozenset({"os", "arch", "python_major_minor"})
ALLOWED_OS_FAMILIES = frozenset({"Darwin", "Linux", "Windows", "FreeBSD", "OpenBSD", "NetBSD"})
ALLOWED_ARCH_FAMILIES = frozenset({"arm64", "aarch64", "x86_64", "amd64"})
FORBIDDEN_HOST_SUBSTRINGS = (
    "/Users/",
    "/home/",
    "C:\\Users\\",
    "Darwin Kernel Version",
    '"hostname"',
    '"fqdn"',
)
PROJECTED_PRIVATE_REVIEWER_REL_PATHS = frozenset(
    {
        "research/academic-pipeline/gemini-review-20261113/reviewer-source.json",
        "research/academic-pipeline/gemini-review-20261113/results-v2/reviewer-source.json",
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=16)
def _load_json_cached(rel_path: str) -> dict[str, Any]:
    return json.loads((ROOT / rel_path).read_text(encoding="utf-8"))


def _verify_source_hashes_on_disk(
    source_hashes: Mapping[str, str],
    *,
    root: Path = ROOT,
    base_dir: Path | None = None,
) -> None:
    """Verify every SHA-256 entry in ``source_hashes`` against disk or public projection."""
    assert source_hashes, "source_hashes must not be empty"
    v2_inputs: dict[str, str] | None = None
    v2_sources: dict[str, str] | None = None

    for rel_str, expected_digest in source_hashes.items():
        assert re.fullmatch(r"[0-9a-f]{64}", expected_digest), (
            f"Malformed SHA-256 digest for {rel_str}: {expected_digest!r}"
        )
        disk_path = (base_dir / rel_str) if base_dir is not None else (root / rel_str)
        norm_rel = str(disk_path.relative_to(root))

        if norm_rel in PROJECTED_PRIVATE_REVIEWER_REL_PATHS and not disk_path.is_file():
            if v2_inputs is None or v2_sources is None:
                v2_inputs = _load_json_cached(
                    "research/academic-pipeline/gemini-review-20261113/results-v2/input_hashes.json"
                )
                v2_sources = _load_json_cached(
                    "research/academic-pipeline/gemini-review-20261113/results-v2/source_hashes.json"
                )
            receipt = a3_trace.verify_public_review_source(v2_inputs, v2_sources)
            if expected_digest != receipt["original_commitment_sha256"]:
                raise ValueError(
                    f"Projected private source digest mismatch for {norm_rel}: {expected_digest}"
                )
            continue

        if not disk_path.is_file():
            raise ValueError(f"Missing hashed source artifact on disk: {norm_rel}")
        actual_digest = _sha256(disk_path)
        if actual_digest != expected_digest:
            raise ValueError(
                f"SHA-256 drift for {norm_rel}: expected {expected_digest}, got {actual_digest}"
            )


# ---------------------------------------------------------------------------
# 1. Cross-Artifact Provenance, 0-LLM Contract & Sanitized Host Metadata
# ---------------------------------------------------------------------------


class TestCrossArtifactProvenanceAndZeroLlmContract:
    @pytest.mark.parametrize(
        ("audit_id", "results_rel", "runner_rel"),
        AUDIT_ARTIFACTS,
        ids=[item[0] for item in AUDIT_ARTIFACTS],
    )
    def test_committed_results_enforce_zero_llm_calls_and_coarse_host_metadata(
        self,
        audit_id: str,
        results_rel: str,
        runner_rel: str,
    ) -> None:
        del audit_id, runner_rel
        raw_text = (ROOT / results_rel).read_text(encoding="utf-8")
        payload = _load_json_cached(results_rel)

        # Strict 0-LLM contract: boolean False and integer 0 (never bool/None).
        assert payload["model_called"] is False
        assert type(payload["llm_calls"]) is int
        assert payload["llm_calls"] == 0

        # Coarse sanitized host metadata only (no usernames, paths, hostnames, or kernel builds).
        env = payload["environment"]
        assert isinstance(env, dict) and env
        assert {"os", "arch"}.issubset(env.keys())
        assert set(env.keys()).issubset(ALLOWED_ENV_KEYS)
        assert env["os"] in ALLOWED_OS_FAMILIES
        assert env["arch"] in ALLOWED_ARCH_FAMILIES
        if "python_major_minor" in env:
            assert re.fullmatch(r"\d+\.\d+", env["python_major_minor"])

        for forbidden in FORBIDDEN_HOST_SUBSTRINGS:
            assert forbidden not in raw_text, f"Host leak {forbidden!r} in {results_rel}"

        if results_rel.endswith("soak-and-refusal-probe-v1/results.json"):
            assert payload["engine"]["os"] in a4_soak.ALLOWED_COARSE_OS
            assert payload["engine"]["headless"] is True

    @pytest.mark.parametrize(
        ("audit_id", "results_rel", "runner_rel"),
        AUDIT_ARTIFACTS,
        ids=[item[0] for item in AUDIT_ARTIFACTS],
    )
    def test_committed_source_hashes_match_on_disk_sha256(
        self,
        audit_id: str,
        results_rel: str,
        runner_rel: str,
    ) -> None:
        del audit_id
        payload = _load_json_cached(results_rel)
        source_hashes = payload["source_hashes"]
        assert isinstance(source_hashes, dict)
        assert runner_rel in source_hashes
        _verify_source_hashes_on_disk(source_hashes, root=ROOT)

    def test_transitive_v2_manifests_verify_under_simulated_clean_ci_without_private_source(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        v2_inputs = _load_json_cached(
            "research/academic-pipeline/gemini-review-20261113/results-v2/input_hashes.json"
        )
        v2_sources = _load_json_cached(
            "research/academic-pipeline/gemini-review-20261113/results-v2/source_hashes.json"
        )
        real_is_file = Path.is_file
        hidden = {ROOT / rel for rel in PROJECTED_PRIVATE_REVIEWER_REL_PATHS}

        def fake_is_file(path: Path) -> bool:
            if path.resolve() in hidden:
                return False
            return real_is_file(path)

        monkeypatch.setattr(Path, "is_file", fake_is_file)

        _verify_source_hashes_on_disk(v2_sources, root=ROOT)
        _verify_source_hashes_on_disk(
            v2_inputs,
            root=ROOT,
            base_dir=ROOT / "research/academic-pipeline/gemini-review-20261113/results-v2",
        )

        # Any non-projected file missing or drifted must still fail closed.
        tampered = dict(v2_sources)
        tampered["src/nesy_game/validator.py"] = "0" * 64
        with pytest.raises(ValueError, match="SHA-256 drift"):
            _verify_source_hashes_on_disk(tampered, root=ROOT)


# ---------------------------------------------------------------------------
# 2. A1: Multi-Error & Conflict-Pair Repair Convergence Audit
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _a1_cases_by_id() -> dict[str, dict[str, Any]]:
    return {case["case_id"]: case for case in a1_repair.build_cases()}


class TestMultiErrorRepairAuditA1:
    def test_family_denominators_partition_352_cases_and_keep_128_guard_battery_separate(
        self,
    ) -> None:
        cases = list(_a1_cases_by_id().values())
        assert len(cases) == 352

        by_family = {
            fam: {c["case_id"] for c in cases if c["family"] == fam}
            for fam in ("repairable_multi", "mixed_partial_clear", "conflict_pair")
        }
        assert len(by_family["repairable_multi"]) == 96
        assert len(by_family["mixed_partial_clear"]) == 160
        assert len(by_family["conflict_pair"]) == 96
        assert 96 + 160 + 96 == 352
        assert not (by_family["repairable_multi"] & by_family["mixed_partial_clear"])
        assert not (by_family["repairable_multi"] & by_family["conflict_pair"])
        assert not (by_family["mixed_partial_clear"] & by_family["conflict_pair"])
        assert set().union(*by_family.values()) == {c["case_id"] for c in cases}

        committed = _load_json_cached(
            "research/academic-pipeline/multi-error-repair-audit/results.json"
        )
        assert committed["base_state_count"] == 32
        assert committed["cases_per_budget"] == 352
        assert committed["budgets"] == [0, 1, 2, 3]
        assert committed["total_end_to_end_runs"] == 352 * 4 == 1408
        assert committed["unsafe_commits_total"] == 0
        assert committed["false_rejections_total"] == 0
        assert committed["native_replay_equal_total"] == 1408
        assert committed["family_breakdown"]["repairable_multi"]["assigned"] == 96
        assert committed["family_breakdown"]["mixed_partial_clear"]["assigned"] == 160
        assert committed["family_breakdown"]["conflict_pair"]["assigned"] == 96
        assert committed["simultaneous_conflict_guard"]["assigned"] == 128

    @pytest.mark.parametrize(
        ("case_id", "budget", "expected"),
        [
            (
                "n4-locked_chain-start-start-q0--multi_all_5_repairable",
                0,
                {
                    "status": "HOLD",
                    "observed_trajectory_fixed_point": False,
                    "fixed_point_attempt": None,
                    "terminal_is_fixed_point": False,
                    "observed_period_2": False,
                    "terminal_in_period_2": False,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--multi_all_5_repairable",
                1,
                {
                    "status": "COMMITTED",
                    "observed_trajectory_fixed_point": True,
                    "fixed_point_attempt": 1,
                    "terminal_is_fixed_point": True,
                    "observed_period_2": False,
                    "terminal_in_period_2": False,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--mixed_pre_eff_knowledge",
                1,
                {
                    "status": "HOLD",
                    "partial_clear_hold": True,
                    "observed_trajectory_fixed_point": False,
                    "fixed_point_attempt": None,
                    "terminal_is_fixed_point": True,
                    "observed_period_2": False,
                    "terminal_in_period_2": False,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--mixed_pre_eff_knowledge",
                2,
                {
                    "status": "HOLD",
                    "partial_clear_hold": True,
                    "observed_trajectory_fixed_point": True,
                    "fixed_point_attempt": 2,
                    "terminal_is_fixed_point": True,
                    "observed_period_2": False,
                    "terminal_in_period_2": False,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--conflict_cross_attempt_omitted",
                1,
                {
                    "status": "HOLD",
                    "observed_trajectory_fixed_point": False,
                    "terminal_is_fixed_point": False,
                    "observed_period_2": False,
                    "terminal_in_period_2": True,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--conflict_cross_attempt_omitted",
                2,
                {
                    "status": "HOLD",
                    "observed_trajectory_fixed_point": False,
                    "terminal_is_fixed_point": False,
                    "observed_period_2": True,
                    "terminal_in_period_2": True,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--conflict_cross_attempt_plus_effect",
                2,
                {
                    "status": "HOLD",
                    "partial_clear_hold": True,
                    "observed_trajectory_fixed_point": False,
                    "terminal_is_fixed_point": False,
                    "observed_period_2": False,
                    "terminal_in_period_2": True,
                },
            ),
            (
                "n4-locked_chain-start-start-q0--conflict_cross_attempt_plus_effect",
                3,
                {
                    "status": "HOLD",
                    "partial_clear_hold": True,
                    "observed_trajectory_fixed_point": False,
                    "terminal_is_fixed_point": False,
                    "observed_period_2": True,
                    "terminal_in_period_2": True,
                },
            ),
        ],
    )
    def test_classify_trace_convergence_distinguishes_fixed_points_and_period_2_cycles(
        self,
        case_id: str,
        budget: int,
        expected: Mapping[str, Any],
    ) -> None:
        case = _a1_cases_by_id()[case_id]
        row = a1_repair.run_case_at_budget(case, budget)
        for key, exp_val in expected.items():
            assert row[key] == exp_val, f"{case_id} K={budget}: {key}={row[key]!r} != {exp_val!r}"

    def test_simultaneous_conflict_guard_preserves_conflicting_entity_and_hits_step1_fixed_point(
        self,
    ) -> None:
        base_states = a1_repair._load_base_states()
        guard = a1_repair.run_simultaneous_conflict_guard_audit(base_states)

        assert guard["assigned"] == 128
        assert guard["ready_preserved_count"] == 128
        assert guard["fixed_point_by_step_1_count"] == 128

        for variant in ("guard_conflict_only_present", "guard_conflict_only_omitted"):
            v = guard["by_variant"][variant]
            assert v["assigned"] == 32
            assert v["c0_eq_c1_count"] == 32
            assert v["fixed_point_by_step_1_count"] == 32

        for variant in (
            "guard_conflict_plus_effect_present",
            "guard_conflict_plus_effect_omitted",
        ):
            v = guard["by_variant"][variant]
            assert v["assigned"] == 32
            assert v["c0_eq_c1_count"] == 0
            assert v["effects_repaired_step_1_count"] == 32
            assert v["fixed_point_by_step_1_count"] == 32
            assert v["ready_preserved_count"] == 32

    def test_run_case_at_budget_fails_closed_on_native_replay_mismatch(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        case = _a1_cases_by_id()["n4-locked_chain-start-start-q0--multi_all_5_repairable"]
        drifted = replace(_world_state(case["state"]), quest_stage=99)
        monkeypatch.setattr(a1_repair, "replay_trace_record", lambda _rec: drifted)
        with pytest.raises(ValueError, match="Native replay mismatch"):
            a1_repair.run_case_at_budget(case, 1)


# ---------------------------------------------------------------------------
# 3. A2: Latency & Scaling Benchmark
# ---------------------------------------------------------------------------


class TestLatencyScalingBenchmarkA2:
    def test_build_scaled_state_and_candidates_is_deterministic_across_hash_seeds_and_set_order(
        self,
    ) -> None:
        for scale_n in a2_latency.FACT_RULE_SCALES:
            state, valid_cand, invalid_cand = a2_latency._build_scaled_state_and_candidates(scale_n)
            k_req = max(2, min(scale_n // 5, a2_latency.ACTIVE_CONSTRAINT_ARITY_CAP))
            expected_omitted_pre = frozenset(sorted(valid_cand.preconditions)[: k_req // 2])
            expected_omitted_eff = frozenset(sorted(valid_cand.effects)[: k_req // 2])
            assert expected_omitted_pre.issubset(invalid_cand.preconditions)
            assert expected_omitted_eff.issubset(invalid_cand.effects)
            assert len(state.facts) == scale_n

        # Subprocess verification under distinct PYTHONHASHSEED values proves frozenset
        # hash randomization cannot alter candidate subset selection.
        snippet = (
            "import hashlib, json, sys; "
            "sys.path.insert(0, 'src'); sys.path.insert(0, '.'); "
            "from nesy_game.runtime import to_jsonable; "
            "from scripts.run_latency_scaling_benchmark import _build_scaled_state_and_candidates; "
            "payload = json.dumps(to_jsonable(_build_scaled_state_and_candidates(500)), sort_keys=True); "
            "print(hashlib.sha256(payload.encode('utf-8')).hexdigest())"
        )
        digests: list[str] = []
        for seed in ("1", "999983"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            proc = subprocess.run(
                [sys.executable, "-c", snippet],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            digests.append(proc.stdout.strip())
        assert digests[0] == digests[1] and len(digests[0]) == 64

        # Also verify reversed frozenset insertion order on ActionPolicy produces identical subsets.
        forward_pre = frozenset(f"fact_{i}" for i in range(40))
        reverse_pre = frozenset(f"fact_{i}" for i in reversed(range(40)))
        assert sorted(forward_pre)[:20] == sorted(reverse_pre)[:20]

    def test_active_constraint_arity_caps_at_100_while_ambient_store_scales_to_2000(self) -> None:
        assert a2_latency.ACTIVE_CONSTRAINT_ARITY_CAP == 100
        committed = _load_json_cached(
            "research/academic-pipeline/latency-scaling-benchmark/results.json"
        )
        assert committed["config"]["active_constraint_arity_cap"] == 100

        observed_arities = {}
        for scale_n in a2_latency.FACT_RULE_SCALES:
            state, valid_cand, _ = a2_latency._build_scaled_state_and_candidates(scale_n)
            observed_arities[scale_n] = len(valid_cand.preconditions)
            assert len(valid_cand.effects) == observed_arities[scale_n]
            assert len(state.facts) == scale_n
            assert len(state.action_policies) == scale_n + 2

        assert observed_arities == {10: 2, 100: 20, 500: 100, 1000: 100, 2000: 100}

        val_fail_errors = {
            row["facts_rules_count"]: row["error_count"]
            for row in committed["benchmarks"]["validator"]
            if row["case"] == "multi_error_fail"
        }
        assert val_fail_errors[500] == val_fail_errors[1000] == val_fail_errors[2000] == 156

    def test_fail_closed_value_error_guards_fire_and_survive_python_optimize_flag(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        with pytest.raises(ValueError, match="empty sequence"):
            a2_latency._percentile([], 0.95)

        # Validator guard: valid candidate unexpectedly rejected.
        monkeypatch.setattr(
            a2_latency,
            "validate_candidate",
            lambda _s, _c: ValidationResult(
                valid=False,
                errors=(ValidationError("FORBIDDEN_DISCLOSURE", "x", "msg", "hint"),),
                checks_run=("disclosure",),
            ),
        )
        with pytest.raises(ValueError, match="Expected valid candidate"):
            a2_latency.benchmark_validator(warmup=0, iterations=1)
        monkeypatch.undo()

        # Validator guard: invalid candidate unexpectedly accepted.
        with monkeypatch.context() as mp:
            mp.setattr(
                a2_latency,
                "validate_candidate",
                lambda _s, _c: ValidationResult(valid=True, errors=(), checks_run=()),
            )
            with pytest.raises(ValueError, match="Expected invalid candidate"):
                a2_latency.benchmark_validator(warmup=0, iterations=1)

        # Repair guard: repairable candidate fails to converge.
        with monkeypatch.context() as mp:
            mp.setattr(
                a2_latency,
                "counterexample_guided_repair",
                lambda _s, cand, _v, _a: cand,
            )
            with pytest.raises(ValueError, match="Expected repairable candidate to converge"):
                a2_latency.benchmark_repair(warmup=0, iterations=1)

        # Reachability guard: closure diverges from reference state-space BFS.
        with monkeypatch.context() as mp:
            mp.setattr(
                a2_latency,
                "production_reachable_locations",
                lambda _g: frozenset({"bogus_unreachable_room"}),
            )
            with pytest.raises(ValueError, match="Reachability mismatch"):
                a2_latency.benchmark_reachability(warmup=0, iterations=1)

        # Verification guard: SHA-256 receipt check fails.
        with monkeypatch.context() as mp:
            mp.setattr(a2_latency, "verify_trace_record", lambda _r: False)
            with pytest.raises(ValueError, match="SHA-256 verification failed"):
                a2_latency.benchmark_verification_and_replay(warmup=0, iterations=1)

        # Replay guards: single-record and episode JSONL state drift fail closed.
        drifted_state, _, _ = a2_latency._build_scaled_state_and_candidates(10)
        drifted_state = replace(drifted_state, quest_stage=999)
        with monkeypatch.context() as mp:
            mp.setattr(a2_latency, "replay_trace_record", lambda _r: drifted_state)
            with pytest.raises(ValueError, match="Replay state mismatch"):
                a2_latency.benchmark_verification_and_replay(warmup=0, iterations=1)
        with monkeypatch.context() as mp:
            mp.setattr(
                a2_latency, "replay_trace_jsonl", lambda _p, initial_state=None: drifted_state
            )
            with pytest.raises(ValueError, match="Episode JSONL replay mismatch"):
                a2_latency.benchmark_verification_and_replay(warmup=0, iterations=1)

        # Prove guards are real ValueError raises, NOT assert statements stripped under python -O.
        opt_snippet = (
            "import sys; "
            "sys.path.insert(0, 'src'); sys.path.insert(0, '.'); "
            "import scripts.run_latency_scaling_benchmark as m; "
            "assert False, 'must be stripped under -O'; "
            "m.production_reachable_locations = lambda _g: frozenset({'corrupted'}); "
            "ok = False\n"
            "try:\n"
            "    m.benchmark_reachability(warmup=0, iterations=1)\n"
            "except ValueError:\n"
            "    ok = True\n"
            "if not ok or __debug__:\n"
            "    raise SystemExit(1)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-O", "-c", opt_snippet],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, f"Guard failed under python -O: {proc.stderr}"


# ---------------------------------------------------------------------------
# 4. A3: Traceability Seeded-Control Audit
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _a3_frozen_fixture() -> dict[str, Any]:
    v2_dir = a3_trace.V2_DIR
    protocol = json.loads((v2_dir / "protocol.json").read_text(encoding="utf-8"))
    summary_v2 = json.loads((v2_dir / "summary.json").read_text(encoding="utf-8"))
    cases = json.loads((v2_dir / "cases.json").read_text(encoding="utf-8"))
    surface_cases = json.loads((v2_dir / "surface_sentinels.json").read_text(encoding="utf-8"))
    inventory = json.loads((v2_dir / "assignment_inventory.json").read_text(encoding="utf-8"))
    source_hashes = json.loads((v2_dir / "source_hashes.json").read_text(encoding="utf-8"))
    input_hashes = json.loads((v2_dir / "input_hashes.json").read_text(encoding="utf-8"))
    core_rows = [
        json.loads(line)
        for line in (v2_dir / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    surface_rows = [
        json.loads(line)
        for line in (v2_dir / "surface_rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    frozen_cases_by_id = {c["case_id"]: c for c in cases + surface_cases}
    frozen_case_hashes = {cid: a3_trace._sha256_json(c) for cid, c in frozen_cases_by_id.items()}
    frozen_inventory_keys = frozenset((x["case_id"], x["arm"], x["cohort"]) for x in inventory)

    single_attempt_row = next(r for r in core_rows if r["arm"] == "semantic_rejection")
    repaired_commit_row = next(
        r
        for r in core_rows
        if r["arm"] == "guided_repair"
        and r["status"] == "COMMITTED"
        and r["repair_attempt_count"] == 1
    )
    failed_repair_hold_row = next(
        r
        for r in core_rows
        if r["arm"] == "guided_repair" and r["status"] == "HOLD" and r["repair_attempt_count"] == 1
    )
    return {
        "protocol": protocol,
        "summary_v2": summary_v2,
        "source_hashes": source_hashes,
        "input_hashes": input_hashes,
        "core_rows": core_rows,
        "surface_rows": surface_rows,
        "frozen_cases_by_id": frozen_cases_by_id,
        "frozen_case_hashes": frozen_case_hashes,
        "frozen_inventory_keys": frozen_inventory_keys,
        "representative_rows": {
            "single_attempt": single_attempt_row,
            "repaired_commit": repaired_commit_row,
            "failed_repair_hold": failed_repair_hold_row,
        },
    }


def _score_a3_row(row: Mapping[str, Any], locator: str = "test-row:1") -> dict[str, Any]:
    ctx = _a3_frozen_fixture()
    return a3_trace.score_v2_row(
        row,
        row_locator=locator,
        frozen_cases_by_id=ctx["frozen_cases_by_id"],
        frozen_case_hashes=ctx["frozen_case_hashes"],
        frozen_inventory_keys=ctx["frozen_inventory_keys"],
        frozen_source_hashes=ctx["source_hashes"],
        protocol=ctx["protocol"],
    )


class TestTraceabilitySeededAuditA3:
    def test_committed_seeded_audit_sensitivity_and_zero_false_alarm_denominators(self) -> None:
        committed = _load_json_cached(
            "research/traceability-scoring-20261023/seeded-control-audit-v1/results.json"
        )
        sc = committed["seeded_control_summary"]
        assert sc["clean_native_pool_size"] == 1248
        assert sc["clean_baseline_failures"] == 0
        assert sc["candidate_corruption_controls_total"] == 6240
        assert sc["seeded_valid_corruptions"] == 4656
        assert sc["detected_valid_corruptions"] == 4656
        assert sc["overall_detector_sensitivity"] == 1.0
        assert sc["inapplicable_controls_retained_separately"] == 1584
        assert sc["malformed_controls_retained_separately"] == 0
        assert sc["clean_control_units"] == 3744
        assert sc["false_alarms"] == 0
        assert sc["overall_false_alarm_rate"] == 0.0
        assert committed["reliability"]["krippendorff_alpha"] == "UNDEFINED"

        tr05 = committed["baseline_frozen_trace_scores"]["cohort_1_gemini_review_v2"]["TR05"]
        assert tr05["TR05_forward"]["complete_chain_numerator"] == 12
        assert tr05["TR05_forward"]["complete_chain_denominator"] == 12
        assert tr05["TR05_reverse"]["complete_chain_numerator"] == 10
        assert tr05["TR05_reverse"]["complete_chain_denominator"] == 10
        assert tr05["co_hashed_sibling_modules_disclosed_separately"]["count"] == 10

    @pytest.mark.parametrize(
        ("row_key", "corruption_kind", "expected_status", "expected_degraded_dims"),
        [
            ("failed_repair_hold", "remove_receipt", "valid", {"TR01", "TR02", "TR03", "TR04"}),
            ("repaired_commit", "swap_attempt_id", "valid", {"TR01", "TR03", "TR04"}),
            ("single_attempt", "swap_attempt_id", "inapplicable", set()),
            ("repaired_commit", "bind_old_artifact_revision", "valid", {"TR01", "TR02"}),
            (
                "repaired_commit",
                "reverse_decision_or_status",
                "valid",
                {"TR02", "TR03", "TR04"},
            ),
            ("failed_repair_hold", "omit_failed_repair", "valid", {"TR04"}),
            ("repaired_commit", "omit_failed_repair", "inapplicable", set()),
            ("single_attempt", "omit_failed_repair", "inapplicable", set()),
        ],
    )
    def test_seeded_corruptions_are_detected_even_when_trace_hash_is_recomputed(
        self,
        row_key: str,
        corruption_kind: str,
        expected_status: str,
        expected_degraded_dims: set[str],
    ) -> None:
        row = _a3_frozen_fixture()["representative_rows"][row_key]
        baseline = _score_a3_row(row)
        for dim in ("TR01", "TR02", "TR03"):
            assert baseline[dim]["complete_chain"] == 1
        if baseline["TR04"]["applicable"]:
            assert baseline["TR04"]["complete_chain"] == 1

        app_status, mutated, _ = a3_trace._apply_seeded_corruption(row, corruption_kind)
        assert app_status == expected_status
        if expected_status == "inapplicable":
            assert mutated is None
            return

        assert mutated is not None
        if corruption_kind in {
            "swap_attempt_id",
            "reverse_decision_or_status",
            "omit_failed_repair",
        }:
            # Recomputed trace_hash passes naive checksum check; semantic links must still catch it.
            assert verify_trace_record(mutated["native_outcome"]) is True

        scored = _score_a3_row(mutated)
        degraded = {
            dim
            for dim in ("TR01", "TR02", "TR03", "TR04")
            if baseline[dim]["applicable"]
            and baseline[dim]["complete_chain"] == 1
            and (not scored[dim]["applicable"] or scored[dim]["complete_chain"] == 0)
        }
        assert degraded == expected_degraded_dims

    @pytest.mark.parametrize(
        "control_kind",
        (
            "clean_duplicate",
            "irrelevant_decorative_addition",
            "semantics_preserving_format_change",
        ),
    )
    def test_invariance_controls_preserve_exact_tr01_tr04_score_signatures(
        self,
        control_kind: str,
    ) -> None:
        reps = _a3_frozen_fixture()["representative_rows"]
        for row_key, row in reps.items():
            baseline = _score_a3_row(row, locator=f"clean:{row_key}")
            transformed = a3_trace._apply_invariance_control(row, control_kind)
            scored = _score_a3_row(transformed, locator=f"control:{control_kind}:{row_key}")
            assert a3_trace._score_signature(scored) == a3_trace._score_signature(baseline)

    def test_public_source_projection_parity_when_private_reviewer_source_absent(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ctx = _a3_frozen_fixture()
        receipt = a3_trace.verify_public_review_source(ctx["input_hashes"], ctx["source_hashes"])
        assert receipt["receipt_sha256"] == a3_trace.PUBLIC_RECEIPT_SHA256
        assert receipt["public_derivative_sha256"] == a3_trace.PUBLIC_DERIVATIVE_SHA256
        assert receipt["original_commitment_sha256"] == a3_trace.REVIEWER_SOURCE_ORIGINAL_SHA256

        real_is_file = Path.is_file
        hidden = {ROOT / rel for rel in PROJECTED_PRIVATE_REVIEWER_REL_PATHS}
        monkeypatch.setattr(
            Path,
            "is_file",
            lambda p: False if p.resolve() in hidden else real_is_file(p),
        )

        # Without public projection, missing private reviewer-source.json fails TR05_reverse.
        without_proj = a3_trace.score_tr05_v2(
            ctx["protocol"],
            ctx["summary_v2"],
            ctx["source_hashes"],
            ctx["input_hashes"],
            ctx["core_rows"],
            ctx["surface_rows"],
            use_public_projection=False,
        )
        assert without_proj["TR05_forward"]["complete_chain_numerator"] == 11
        assert without_proj["TR05_reverse"]["complete_chain_numerator"] == 9

        # With public projection enabled, both forward (12/12) and reverse (10/10) match committed.
        with_proj = a3_trace.score_tr05_v2(
            ctx["protocol"],
            ctx["summary_v2"],
            ctx["source_hashes"],
            ctx["input_hashes"],
            ctx["core_rows"],
            ctx["surface_rows"],
            use_public_projection=True,
        )
        assert with_proj["TR05_forward"]["complete_chain_numerator"] == 12
        assert with_proj["TR05_forward"]["complete_chain_denominator"] == 12
        assert with_proj["TR05_reverse"]["complete_chain_numerator"] == 10
        assert with_proj["TR05_reverse"]["complete_chain_denominator"] == 10

        # Committed preflight records verified public projection parity on all 7 inputs & 20 sources.
        committed = _load_json_cached(
            "research/traceability-scoring-20261023/seeded-control-audit-v1/results.json"
        )
        pre = committed["frozen_integrity_preflight"]
        assert pre["public_source_projection_verified"] is True
        assert pre["public_source_projection"] == receipt
        assert pre["v2_input_hashes_matched"] == pre["v2_input_hashes_total"] == 7
        assert pre["v2_source_hashes_matched"] == pre["v2_source_hashes_total"] == 20

    def test_verify_public_review_source_fails_closed_on_tampered_commitments_or_derivative(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ctx = _a3_frozen_fixture()
        inputs = dict(ctx["input_hashes"])
        sources = dict(ctx["source_hashes"])

        bad_inputs = dict(inputs, **{"reviewer-source.json": "f" * 64})
        with pytest.raises(ValueError, match="original reviewer/executed-runner commitments"):
            a3_trace.verify_public_review_source(bad_inputs, sources)

        bad_sources = dict(sources, **{"scripts/run_gemini_review_evaluation.py": "e" * 64})
        with pytest.raises(ValueError, match="original reviewer/executed-runner commitments"):
            a3_trace.verify_public_review_source(inputs, bad_sources)

        # Stage isolated REVIEW_DIR inside fake project root to test tampered derivative bytes.
        fake_root = tmp_path / "repo"
        fake_review = fake_root / "research/academic-pipeline/gemini-review-20261113"
        (fake_review / "results-v2").mkdir(parents=True)
        for rel in (
            "public-source-projection-v1.json",
            "reviewer-source.public.json",
            "results-v2/input_hashes.json",
            "results-v2/source_hashes.json",
        ):
            shutil.copy2(a3_trace.REVIEW_DIR / rel, fake_review / rel)

        monkeypatch.setattr(a3_trace, "ROOT", fake_root)
        monkeypatch.setattr(a3_trace, "REVIEW_DIR", fake_review)
        assert a3_trace.verify_public_review_source(inputs, sources)["receipt_sha256"] == (
            a3_trace.PUBLIC_RECEIPT_SHA256
        )

        # Corrupting reviewer-source.public.json fails closed immediately.
        (fake_review / "reviewer-source.public.json").write_bytes(b'{"tampered": true}\n')
        with pytest.raises(ValueError, match="public reviewer-source bytes drift"):
            a3_trace.verify_public_review_source(inputs, sources)

        # Corrupting public-source-projection-v1.json receipt bytes also fails closed.
        shutil.copy2(
            ROOT / "research/academic-pipeline/gemini-review-20261113/reviewer-source.public.json",
            fake_review / "reviewer-source.public.json",
        )
        (fake_review / "public-source-projection-v1.json").write_bytes(b'{"tampered": true}\n')
        with pytest.raises(
            ValueError, match="approved public reviewer-source projection receipt digest drift"
        ):
            a3_trace.verify_public_review_source(inputs, sources)

        # run_audit itself invokes verify_public_review_source before scoring and fails closed.
        with pytest.raises(
            ValueError, match="approved public reviewer-source projection receipt digest drift"
        ):
            a3_trace.run_audit(
                tmp_path / "audit-out",
                public_source_projection=True,
                write_outputs=False,
            )

        # Unknown corruption/invariance operator names fail closed with ValueError.
        sample_row = ctx["representative_rows"]["repaired_commit"]
        with pytest.raises(ValueError, match="unknown corruption_kind"):
            a3_trace._apply_seeded_corruption(sample_row, "nonexistent_operator")
        with pytest.raises(ValueError, match="unknown invariance control_kind"):
            a3_trace._apply_invariance_control(sample_row, "nonexistent_control")


# ---------------------------------------------------------------------------
# 5. A4: Godot Headless Refusal-Coverage & Soak Probe
# ---------------------------------------------------------------------------


def _valid_a4_report() -> dict[str, Any]:
    return deepcopy(
        _load_json_cached("game-track/godot/docs/soak-and-refusal-probe-v1/results.json")
    )


class TestSoakAndRefusalProbeA4:
    def test_validate_probe_report_accepts_committed_payload_and_checks_memory_stability(
        self,
    ) -> None:
        report = _valid_a4_report()
        a4_soak.validate_probe_report(report, expected_ticks=1600)

        monitors = report["soak"]["memory"]["godot_monitors"]
        assert monitors["orphan_node_count"]["max"] == 0
        assert monitors["orphan_node_count"]["final"] == 0
        assert monitors["object_count_steady_state_delta"] == 0
        assert monitors["node_count"]["min"] == monitors["node_count"]["max"]

    @pytest.mark.parametrize(
        ("label", "mutator", "expected_match"),
        [
            (
                "missing_exercised_refusal_code",
                lambda r: r["refusal_code_coverage"]["exercised_codes"].remove(
                    "OBJECT_NOT_REACHABLE"
                ),
                "exercised refusal codes mismatch",
            ),
            (
                "non_empty_missing_codes_list",
                lambda r: r["refusal_code_coverage"]["missing_codes"].append(
                    "QUEST_STAGE_PRECONDITION"
                ),
                "missing refusal codes",
            ),
            (
                "newly_targeted_code_absent_from_cases",
                lambda r: [
                    row.__setitem__("observed_codes", ["UNKNOWN_OPERATION"])
                    for row in r["refusal_code_coverage"]["cases"]
                    if "OBJECT_NOT_REACHABLE" in row["observed_codes"]
                ],
                "newly targeted code not exercised: OBJECT_NOT_REACHABLE",
            ),
            (
                "newly_targeted_code_absent_from_soak",
                lambda r: r["soak"]["counts"]["exercised_refusal_codes"].remove(
                    "QUEST_STAGE_PRECONDITION"
                ),
                "soak did not exercise QUEST_STAGE_PRECONDITION",
            ),
            (
                "memory_leak_orphan_node_failure_reported",
                lambda r: r["failures"].append(
                    {
                        "section": "memory",
                        "step": "steady_state",
                        "message": "orphan_node_count leaked 4 nodes during soak",
                    }
                ),
                "probe reported failures",
            ),
            (
                "canonical_terminal_hash_drift",
                lambda r: r.__setitem__("canonical_terminal_sha256", "0" * 64),
                "canonical terminal hash drifted",
            ),
            (
                "refusal_battery_state_hash_drift",
                lambda r: r["refusal_code_coverage"].__setitem__("all_cases_state_isolated", False),
                "refusal battery had non-isolated state",
            ),
            (
                "soak_refusal_state_hash_drift",
                lambda r: r["soak"]["counts"].__setitem__(
                    "refusals_state_isolated", r["soak"]["counts"]["refusals"] - 1
                ),
                "soak refusal state isolation mismatch",
            ),
            (
                "soak_terminal_state_hash_drift",
                lambda r: r["soak"]["counts"].__setitem__(
                    "terminal_hash_matches", r["soak"]["episodes_completed"] - 1
                ),
                "soak terminal hash invariance mismatch",
            ),
            (
                "passed_flag_false_without_failures_entry",
                lambda r: r.__setitem__("passed", False),
                "probe reported failures",
            ),
            (
                "refusal_trace_mirror_mismatch",
                lambda r: r["refusal_code_coverage"].__setitem__(
                    "all_cases_trace_consistent", False
                ),
                "refusal battery had EvaluationTrace mismatch",
            ),
            (
                "soak_tick_budget_mismatch",
                lambda r: r["soak"].__setitem__("ticks_executed", 1200),
                "unexpected soak tick count",
            ),
        ],
        ids=lambda item: item if isinstance(item, str) else "",
    )
    def test_validate_probe_report_fails_closed_on_missing_code_memory_leak_or_hash_drift(
        self,
        label: str,
        mutator: Any,
        expected_match: str,
    ) -> None:
        del label
        report = _valid_a4_report()
        mutator(report)
        with pytest.raises(ValueError, match=expected_match):
            a4_soak.validate_probe_report(report, expected_ticks=1600)

    def test_cli_rejects_sub_1000_soak_tick_budget_fail_closed(self) -> None:
        with pytest.raises(ValueError, match="--ticks must be at least 1000"):
            a4_soak.main(["--ticks", "999"])

    def test_render_summary_markdown_formats_nr_gracefully_when_soak_delta_mib_is_none(
        self,
    ) -> None:
        # Case 1: Only soak_delta_mib is None while KiB samples exist.
        partial_none = _valid_a4_report()
        partial_none["soak"]["memory"]["resident_rss_kib"]["soak_delta_mib"] = None
        md_partial = a4_soak.render_summary_markdown(partial_none)
        assert "(`soak_delta=-43184 KiB` / `NR`)" in md_partial
        assert "None" not in md_partial

        # Case 2: Sandboxed host where `ps -o rss=` is unavailable (-1 samples, None deltas).
        all_unrecorded = _valid_a4_report()
        all_unrecorded["soak"]["memory"]["resident_rss_kib"] = {
            "pre_refusal_battery": -1,
            "pre_soak": -1,
            "post_soak": -1,
            "soak_delta_kib": None,
            "soak_delta_mib": None,
        }
        md_unrecorded = a4_soak.render_summary_markdown(all_unrecorded)
        assert (
            "pre-refusal `NR` -> pre-soak `NR` -> post-soak `NR` (`soak_delta=NR` / `NR`)"
            in md_unrecorded
        )
        assert "-1 KiB" not in md_unrecorded
        assert "None" not in md_unrecorded


# ---------------------------------------------------------------------------
# 6. B: Semantic Escape Filter Audit
# ---------------------------------------------------------------------------


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


class TestSemanticEscapeFilterAuditB:
    def test_tfidf_fit_enforces_strict_out_of_fold_loo_idf_isolation(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # 1. Black-box behavioral proof:
        # Held-out positive prototype 0 carries unique OOV digit tokens ("77777" vs 8 unique
        # OOV tokens) that never appear in the remaining 6 in-fold prototypes.
        # Under true 6-doc out-of-fold LOO vocabulary/IDF construction, fold 0 drops all OOV
        # features of prototype 0, keeping its L2-normalized vector, LOO margin, and calibrated
        # threshold bit-for-bit identical. Under transductive full-corpus IDF leakage, flooding
        # prototype 0 with unique high-IDF tokens crushes its shared L2 weight and margin.
        peer_pos = "alpha beta gamma deltay"
        peer_neg = "omega sigma theta kappax"
        positives_short = ("alpha | 77777", peer_pos, peer_pos, peer_pos)
        positives_flooded = (
            "alpha | 888801 888802 888803 888804 888805 888806 888807 888808",
            peer_pos,
            peer_pos,
            peer_pos,
        )
        negatives = (peer_neg, peer_neg, peer_neg)

        fit_short = b_escape.TfidfCosineFilter.fit(positives_short, negatives, top_k=2)
        fit_flooded = b_escape.TfidfCosineFilter.fit(positives_flooded, negatives, top_k=2)

        assert fit_short.loo_min_pos_margin == fit_flooded.loo_min_pos_margin
        assert fit_short.loo_max_neg_margin == fit_flooded.loo_max_neg_margin
        assert fit_short.threshold == fit_flooded.threshold
        assert fit_short.loo_youden_j == fit_flooded.loo_youden_j

        # Prove non-vacuity: transductive full-corpus IDF WOULD leak and shrink fold 0's margin.
        leaky_feats_short = [b_escape._extract_features(d) for d in positives_short + negatives]
        leaky_feats_flooded = [b_escape._extract_features(d) for d in positives_flooded + negatives]
        v_s, idf_s = b_escape._build_vocab_and_idf(leaky_feats_short)
        v_f, idf_f = b_escape._build_vocab_and_idf(leaky_feats_flooded)
        leaky_sim_short = b_escape._sparse_dot(
            b_escape._encode_with_vocab(leaky_feats_short[0], v_s, idf_s),
            b_escape._encode_with_vocab(leaky_feats_short[1], v_s, idf_s),
        )
        leaky_sim_flooded = b_escape._sparse_dot(
            b_escape._encode_with_vocab(leaky_feats_flooded[0], v_f, idf_f),
            b_escape._encode_with_vocab(leaky_feats_flooded[1], v_f, idf_f),
        )
        assert leaky_sim_flooded < leaky_sim_short * 0.6

        # 2. Direct 28-prototype calibration fold check: every held-out prototype's unique
        # canary token is excluded from its own 27-prototype fold_vocab/fold_idf.
        pos_canaries = [
            f"{doc} canarypos{i:02d}" for i, doc in enumerate(b_escape.CALIBRATION_POSITIVES)
        ]
        neg_canaries = [
            f"{doc} canaryneg{j:02d}" for j, doc in enumerate(b_escape.CALIBRATION_NEGATIVES)
        ]
        recorded_vocabs: list[tuple[int, set[str]]] = []
        real_builder = b_escape._build_vocab_and_idf

        def spy_builder(train_feats: Any) -> tuple[dict[str, int], tuple[float, ...]]:
            vocab, idf = real_builder(train_feats)
            recorded_vocabs.append((len(train_feats), set(vocab.keys())))
            return vocab, idf

        monkeypatch.setattr(b_escape, "_build_vocab_and_idf", spy_builder)
        fitted = b_escape.TfidfCosineFilter.fit(pos_canaries, neg_canaries, top_k=3)

        # 14 positive LOO folds + 14 negative LOO folds (27 docs each) + 1 deployment refit (28).
        assert len(recorded_vocabs) == 29
        for i in range(14):
            n_docs, vocab_terms = recorded_vocabs[i]
            assert n_docs == 27
            assert f"w1:canarypos{i:02d}" not in vocab_terms
            assert not any(f"canarypos{i:02d}" in term for term in vocab_terms)
        for j in range(14):
            n_docs, vocab_terms = recorded_vocabs[14 + j]
            assert n_docs == 27
            assert f"w1:canaryneg{j:02d}" not in vocab_terms
            assert not any(f"canaryneg{j:02d}" in term for term in vocab_terms)

        deploy_n_docs, deploy_terms = recorded_vocabs[28]
        assert deploy_n_docs == 28
        assert len(deploy_terms) == len(fitted.vocab)
        assert all(f"w1:canarypos{i:02d}" in deploy_terms for i in range(14))
        assert all(f"w1:canaryneg{j:02d}" in deploy_terms for j in range(14))

    def test_zero_text_overlap_between_calibration_prototypes_and_evaluation_corpus(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        corpus = b_escape.build_corpus()
        assert len(corpus) == 88

        pos_norm = {_norm_text(t) for t in b_escape.CALIBRATION_POSITIVES}
        neg_norm = {_norm_text(t) for t in b_escape.CALIBRATION_NEGATIVES}
        eval_norm = {_norm_text(c["candidate"]["narrative_text"]) for c in corpus}

        assert len(pos_norm) == 14
        assert len(neg_norm) == 14
        assert not (pos_norm & neg_norm)
        assert not (eval_norm & pos_norm)
        assert not (eval_norm & neg_norm)

        committed = _load_json_cached(
            "research/academic-pipeline/semantic-escape-filter-audit/results.json"
        )
        assert committed["tfidf_calibration"]["eval_text_overlap_count"] == 0
        assert committed["tfidf_calibration"]["loo_idf_isolation"] is True
        assert committed["tfidf_calibration"]["loo_in_fold_prototypes"] == 27

        # Fail-closed guard: injecting any evaluation sentence into calibration raises ValueError.
        leaked_sentence = f"  {corpus[0]['candidate']['narrative_text'].upper()}  "
        monkeypatch.setattr(
            b_escape,
            "CALIBRATION_POSITIVES",
            (*b_escape.CALIBRATION_POSITIVES[:-1], leaked_sentence),
        )
        with pytest.raises(ValueError, match="calibration/evaluation leakage detected"):
            b_escape.run_audit(tmp_path / "leaked-out")

    def test_stage1_short_circuits_explicit_violations_while_stage2_gates_undeclared_escapes(
        self,
    ) -> None:
        corpus = b_escape.build_corpus()
        explicit_case = next(c for c in corpus if c["stratum"] == "explicit_violation")
        undeclared_direct = next(
            c
            for c in corpus
            if c["stratum"] == "undeclared_paraphrase" and c["subcategory"] == "direct_alias"
        )
        benign_standard = next(
            c
            for c in corpus
            if c["stratum"] == "benign_in_policy" and c["subcategory"] == "standard_benign"
        )

        # 1. Explicit violation rejects at Stage 1 without ever invoking Stage 2.
        def forbidden_stage2(_state: WorldState, _cand: CandidateAction) -> tuple[bool, Any]:
            raise AssertionError("Stage 2 must not execute when Stage 1 rejects")

        row_exp, _, s2_ms_exp = b_escape._eval_gate_single(explicit_case, forbidden_stage2)
        assert row_exp["stage1_rejected"] is True
        assert row_exp["stage2_executed"] is False
        assert row_exp["rejected"] is True
        assert row_exp["decision"] == "HOLD"
        assert s2_ms_exp is None

        # 2. Baseline (stage2=None) commits undeclared paraphrases; Stage-2 filters hold them.
        row_base, _, s2_ms_base = b_escape._eval_gate_single(undeclared_direct, None)
        assert row_base["stage1_rejected"] is False
        assert row_base["stage2_executed"] is False
        assert row_base["decision"] == "COMMIT"
        assert s2_ms_base is None

        tfidf_filter = b_escape.TfidfCosineFilter.fit(
            b_escape.CALIBRATION_POSITIVES, b_escape.CALIBRATION_NEGATIVES, top_k=3
        )
        for stage2_fn in (b_escape.deterministic_alias_pattern_filter, tfidf_filter.predict):
            row_und, _, s2_ms_und = b_escape._eval_gate_single(undeclared_direct, stage2_fn)
            assert row_und["stage1_rejected"] is False
            assert row_und["stage2_executed"] is True
            assert row_und["stage2_flagged"] is True
            assert row_und["decision"] == "HOLD"
            assert s2_ms_und is not None and s2_ms_und >= 0.0

        # 3. Standard benign passes both Stage 1 and deterministic Stage-2 alias/pattern filter.
        row_ben, _, s2_ms_ben = b_escape._eval_gate_single(
            benign_standard, b_escape.deterministic_alias_pattern_filter
        )
        assert row_ben["stage1_rejected"] is False
        assert row_ben["stage2_executed"] is True
        assert row_ben["stage2_flagged"] is False
        assert row_ben["decision"] == "COMMIT"
        assert s2_ms_ben is not None

        # 4. Policy scoping: when keeper_secret is no longer forbidden in WorldState, Stage-2
        # filters must not block sabotage prose.
        unlocked_state = replace(
            _world_state(undeclared_direct["state"]),
            forbidden_disclosures={"keeper": frozenset()},
        )
        cand = parse_candidate_mapping(undeclared_direct["candidate"], allow_defaults=False)
        alias_flagged, alias_reasons = b_escape.deterministic_alias_pattern_filter(
            unlocked_state, cand
        )
        tfidf_flagged, _ = tfidf_filter.predict(unlocked_state, cand)
        assert alias_flagged is False and alias_reasons == []
        assert tfidf_flagged is False

        committed = _load_json_cached(
            "research/academic-pipeline/semantic-escape-filter-audit/results.json"
        )
        base_gate = committed["gates"]["baseline_structured_id"]
        alias_gate = committed["gates"]["structured_id_plus_alias_pattern"]
        tfidf_gate = committed["gates"]["structured_id_plus_tfidf_cosine"]
        assert base_gate["counts"]["tp_explicit"] == 16
        assert base_gate["counts"]["tp_undeclared"] == 0
        assert base_gate["latency_ms"]["stage2_only_warm_n"] == 0
        assert base_gate["latency_ms"]["stage2_only_warm_p95_ms"] is None
        assert alias_gate["latency_ms"]["stage2_only_warm_n"] == 1800
        assert tfidf_gate["latency_ms"]["stage2_only_warm_n"] == 1800
        assert alias_gate["counts"]["tp_undeclared"] == 22
        assert alias_gate["frozen_12_sentinel_check"]["undeclared_caught"] == 6
        assert alias_gate["by_subcategory"]["standard_benign"]["rejected"] == 0
        assert tfidf_gate["counts"]["tp_undeclared"] == 35
