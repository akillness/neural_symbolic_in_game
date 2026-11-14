from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_gemini_review_evaluation as evaluation
from scripts.review_reference import generic_accepts, reference_reachable_locations

ARMS = ("schema_only", "semantic_rejection", "unchanged_retry", "guided_repair")
VARIANTS = {
    "valid_signal",
    "valid_observe",
    "valid_public_fact",
    "valid_start_object",
    "required_relic",
    "omit_policy_precondition",
    "omit_policy_effect",
    "unauthorized_effect",
    "declared_secret",
    "unknown_knowledge",
    "future_stage",
    "unknown_object",
    "extra_unsatisfied_precondition",
}


def _case(variant="valid_signal", stage=0):
    return deepcopy(
        next(
            case
            for case in evaluation.build_cases()
            if case["variant"] == variant and case["state"]["quest_stage"] == stage
        )
    )


def _reference_valid(state, candidate):
    # Duck-typed contract values keep this check independent of production parsers.
    state = deepcopy(state)
    for key in ("facts", "locations", "reachable_locations", "inventory"):
        state[key] = frozenset(state[key])
    for key in ("npc_knowledge", "forbidden_disclosures"):
        state[key] = {actor: frozenset(facts) for actor, facts in state[key].items()}
    state["action_policies"] = {
        name: SimpleNamespace(**{key: frozenset(value) for key, value in policy.items()})
        for name, policy in state["action_policies"].items()
    }
    candidate = deepcopy(candidate)
    for key in ("preconditions", "effects", "required_objects", "used_facts", "disclosed_facts"):
        candidate[key] = frozenset(candidate[key])
    return generic_accepts(SimpleNamespace(**state), SimpleNamespace(**candidate))


def test_complete_factorial_has_every_variant_once_per_graph_state():
    cases = evaluation.build_cases()
    assert len(cases) == 416
    assert len({case["case_id"] for case in cases}) == 416
    assert Counter(case["variant"] for case in cases) == Counter({v: 32 for v in VARIANTS})
    groups = {}
    for case in cases:
        key = (json.dumps(case["graph"], sort_keys=True), case["state"]["quest_stage"])
        groups.setdefault(key, []).append(case["variant"])
    assert len(groups) == 32
    assert all(Counter(variants) == Counter(VARIANTS) for variants in groups.values())
    assert {len(case["graph"]["rooms"]) for case in cases} == {4, 8}
    assert {case["state"]["quest_stage"] for case in cases} == {0, 1}
    assert cases == evaluation.build_cases()
    json.dumps(cases, allow_nan=False)


def test_closure_and_inventory_bfs_agree_for_every_frozen_graph_state():
    for case in evaluation.build_cases():
        expected = reference_reachable_locations(case["graph"])
        assert evaluation.production_reachable_locations(case["graph"]) == expected, case["case_id"]
        assert frozenset(case["state"]["reachable_locations"]) == expected, case["case_id"]


@pytest.mark.parametrize(
    "edges", [None, {}, "r0 -> r1"], ids=["null-edges", "mapping-edges", "string-edges"]
)
def test_production_closure_rejects_wrong_edges_container_type_with_type_error(edges):
    graph = _case()["graph"]
    graph["edges"] = edges
    with pytest.raises(TypeError):
        evaluation.production_reachable_locations(graph)


@pytest.mark.parametrize(
    "variant",
    [
        "unauthorized_effect",
        "omit_policy_precondition",
        "omit_policy_effect",
        "declared_secret",
        "future_stage",
        "unknown_object",
    ],
)
def test_schema_only_really_commits_unsafe_proposals_semantic_gate_holds(variant):
    case = _case(variant)
    unsafe = evaluation.run_case(case, "schema_only")
    rejected = evaluation.run_case(case, "semantic_rejection")
    assert unsafe["reference_initial_valid"] is False
    assert unsafe["status"] == "COMMITTED"
    assert unsafe["reference_final_valid"] is False
    assert unsafe["final_candidate"] == unsafe["initial_candidate"]
    assert set(unsafe["final_state"]["facts"]) == (
        set(case["state"]["facts"]) | set(case["candidate"]["effects"])
    )
    assert rejected["status"] == "HOLD"
    assert rejected["before_state_hash"] == rejected["after_state_hash"]


@pytest.mark.parametrize("variant", ["omit_policy_precondition", "omit_policy_effect"])
def test_guided_repair_recovers_required_policy_fields_and_rechecks_final_candidate(variant):
    case = _case(variant)
    before = deepcopy(case)
    row = evaluation.run_case(case, "guided_repair")
    assert case == before
    assert row["status"] == "COMMITTED"
    assert row["reference_initial_valid"] is False
    assert row["reference_final_valid"] is True
    assert row["goal_reached"] is True
    assert "ready" in row["final_candidate"]["preconditions"]
    assert "signal_restored" in row["final_candidate"]["effects"]
    assert row["initial_candidate"] == before["candidate"]
    assert row["initial_signature"] != row["final_signature"]
    reference_state = deepcopy(before["state"])
    reference_state["reachable_locations"] = sorted(reference_reachable_locations(before["graph"]))
    assert _reference_valid(reference_state, row["final_candidate"]) is True
    assert row["reference_state"] == reference_state


@pytest.mark.parametrize("arm", ARMS)
def test_schema_failure_is_retained_as_failed_assignment_not_a_commit(arm):
    case = _case()
    case["candidate"]["undeclared_field"] = "not admitted by strict schema"
    before = deepcopy(case)
    row = evaluation.run_case(case, arm)
    assert row["status"] == "FAILED"
    assert row["case_id"] == case["case_id"]
    assert row["after_state_hash"] is None
    assert row["goal_reached"] is None
    assert row["error"] is not None
    assert case == before


def test_replay_failure_preserves_observed_final_state_and_goal_but_not_committed_credit(
    monkeypatch,
):
    case = _case()
    before = deepcopy(case)
    observed = evaluation.run_case(case, "semantic_rejection")
    assert observed["status"] == "COMMITTED"
    assert observed["goal_reached"] is True

    def fail_native_replay(record):
        raise RuntimeError("injected-native-replay-failure")

    monkeypatch.setattr(evaluation, "replay_trace_record", fail_native_replay)
    failed = evaluation.run_case(case, "semantic_rejection")

    assert failed["status"] == "FAILED"
    assert failed["error"] == {
        "type": "RuntimeError",
        "message": "injected-native-replay-failure",
    }
    assert failed["final_state"] == observed["final_state"]
    assert failed["after_state_hash"] == observed["after_state_hash"]
    assert failed["after_state_hash"] != failed["before_state_hash"]
    assert failed["goal_reached"] is True
    assert "signal_restored" in failed["final_state"]["facts"]
    assert case == before
    summary = evaluation.summarize_rows([failed])["semantic_rejection"]
    assert summary["assigned"] == 1
    assert summary["failed"] == 1
    assert summary["committed"] == 0
    assert summary["goals"] == 0


def test_unchanged_retry_does_not_relabel_invalid_candidate_as_repaired():
    row = evaluation.run_case(_case("omit_policy_effect"), "unchanged_retry")
    assert row["status"] == "HOLD"
    assert row["reference_initial_valid"] is False
    assert row["before_state_hash"] == row["after_state_hash"]
    assert len(row["attempts"]) == 2
    assert row["initial_candidate"]["effects"] == row["final_candidate"]["effects"]


def test_post_state_cannot_retroactively_satisfy_its_own_precondition_or_stage():
    case = _case()
    case["candidate"]["preconditions"].append("signal_restored")
    case["candidate"]["required_quest_stage"] = 1
    case["candidate"]["quest_stage_effect"] = 1
    before = deepcopy(case)
    row = evaluation.run_case(case, "schema_only")
    assert row["status"] == "COMMITTED"
    assert _reference_valid(row["final_state"], row["final_candidate"]) is True
    assert _reference_valid(row["reference_state"], row["final_candidate"]) is False
    assert row["reference_initial_valid"] is False
    assert row["reference_final_valid"] is False
    assert row["goal_reached"] is True
    assert row["reference_state"]["quest_stage"] == 0
    assert "signal_restored" not in row["reference_state"]["facts"]
    assert case == before


def test_valid_observation_is_not_miscounted_as_goal_success():
    row = evaluation.run_case(_case("valid_observe"), "semantic_rejection")
    assert row["status"] == "COMMITTED"
    assert row["reference_final_valid"] is True
    assert row["goal_reached"] is False
    assert "observed" in row["final_state"]["facts"]
    assert "signal_restored" not in row["final_state"]["facts"]


def test_false_rejection_denominator_excludes_invalid_and_retains_failed_assignments():
    valid = evaluation.run_case(_case(), "semantic_rejection")
    invalid = evaluation.run_case(_case("declared_secret"), "semantic_rejection")
    valid_hold = {
        **deepcopy(valid),
        "case_id": "valid-hold",
        "status": "HOLD",
        "goal_reached": False,
        "after_state_hash": valid["before_state_hash"],
    }
    failed = {
        **deepcopy(valid),
        "case_id": "valid-failed",
        "status": "FAILED",
        "goal_reached": False,
        "error": "deliberate execution failure",
    }
    summary = evaluation.summarize_rows([valid, valid_hold, invalid, failed])["semantic_rejection"]
    assert summary["assigned"] == 4
    assert summary["initial_valid"] == 3
    assert summary["initial_invalid"] == 1
    assert summary["false_rejections"] == 1
    assert summary["false_rejection_denominator"] == 3
    assert (summary["committed"], summary["held"], summary["failed"]) == (1, 2, 1)
    assert summary["repair_successes"] == 0
    assert summary["unsafe_commits"] == 0


def test_structural_signatures_ignore_identity_prose_metadata_and_graph_labels():
    candidate = _case()["candidate"]
    candidate.update(preconditions=["ready", "harbor_open"], quest_stage_effect=None)
    renamed = deepcopy(candidate)
    renamed.update(
        action_id="different-id",
        actor_id="different-actor",
        narrative_text="전혀 다른 문장",
        metadata={"graph": "other", "location": "elsewhere"},
    )
    assert evaluation.structural_signature(candidate) == evaluation.structural_signature(renamed)
    renamed["preconditions"] = list(reversed(candidate["preconditions"]))
    assert evaluation.structural_signature(candidate) == evaluation.structural_signature(renamed)
    for field, value in {
        "action_type": "OBSERVE",
        "preconditions": ["ready", "other_fact"],
        "effects": ["signal_restored", "beacon_lit"],
        "required_objects": ["map"],
        "used_facts": ["harbor_open"],
        "disclosed_facts": ["harbor_open"],
        "required_quest_stage": 1,
        "quest_stage_effect": 1,
    }.items():
        changed = {**candidate, field: value}
        assert evaluation.structural_signature(candidate) != evaluation.structural_signature(
            changed
        ), field


def test_valid_signature_retention_and_repaired_signatures_have_separate_denominators():
    valid_case = _case()
    duplicate = deepcopy(valid_case)
    duplicate["case_id"] = "renamed-case"
    duplicate["candidate"].update(action_id="new-action", narrative_text="different prose")
    repair_case = _case("omit_policy_effect")
    repair_case["candidate"]["effects"] = ["beacon_lit"]
    rows = [
        evaluation.run_case(case, "guided_repair")
        for case in (
            valid_case,
            duplicate,
            _case("valid_observe"),
            repair_case,
        )
    ]
    summary = evaluation.summarize_rows(rows)["guided_repair"]
    assert summary["initial_valid"] == 3
    assert summary["valid_signature_preserved"] == 3
    assert summary["valid_initial_signature_count"] == 2
    assert summary["valid_retained_signature_count"] == 2
    assert summary["invalid_initial_signature_count"] == 1
    assert summary["repaired_signature_count"] == 1
    assert summary["repair_successes"] == 1


def test_surface_sentinels_are_six_paired_declarations_not_narrative_state_commands():
    cases = evaluation.build_surface_sentinels()
    assert len(cases) == 12
    pairs = {}
    for case in cases:
        pairs.setdefault(case["candidate"]["narrative_text"], []).append(case)
    assert len(pairs) == 6
    assert sum(any("가" <= char <= "힣" for char in text) for text in pairs) == 3
    for pair in pairs.values():
        assert len(pair) == 2
        undeclared = next(case for case in pair if not case["candidate"]["disclosed_facts"])
        declared = next(case for case in pair if case["candidate"]["disclosed_facts"])
        assert declared["candidate"]["disclosed_facts"] == ["keeper_secret"]
        assert declared["state"] == undeclared["state"]
        a = {**undeclared["candidate"], "action_id": "paired", "disclosed_facts": []}
        b = {**declared["candidate"], "action_id": "paired", "disclosed_facts": []}
        assert a == b
        accepted = evaluation.run_case(undeclared, "semantic_rejection")
        rejected = evaluation.run_case(declared, "semantic_rejection")
        assert accepted["status"] == "COMMITTED"
        assert accepted["reference_final_valid"] is True
        assert rejected["status"] == "HOLD"
        assert rejected["reference_initial_valid"] is False
        assert set(accepted["final_state"]["facts"]) == (
            set(undeclared["state"]["facts"]) | set(undeclared["candidate"]["effects"])
        )
        assert accepted["final_state"]["quest_stage"] == undeclared["state"]["quest_stage"]


def _synthetic_study_source_root(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source_root = tmp_path / "synthetic-study-source"
    audit_dir = Path("research/academic-pipeline/gemini-review-20261113")
    source_paths = [
        Path("scripts/run_gemini_review_evaluation.py"),
        Path("scripts/review_reference.py"),
        audit_dir / "protocol-v2.json",
        audit_dir / "review-response.json",
        *(path.relative_to(root) for path in sorted((root / "src/nesy_game").glob("*.py"))),
    ]
    for relative_path in source_paths:
        target = source_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((root / relative_path).read_bytes())
    # This metadata is a contract fixture, not a reconstruction of the withheld review.
    (source_root / audit_dir / "reviewer-source.json").write_text(
        json.dumps(
            {
                "schema_version": "synthetic-reviewer-source-fixture/v1",
                "name": "synthetic public runner contract reviewer",
                "status": "SYNTHETIC_TEST_FIXTURE",
                "purpose": "Exercise source freezing only; not original reviewer evidence.",
            }
        ),
        encoding="utf-8",
    )
    return source_root


def test_study_freezes_all_assignments_before_outcomes_and_keeps_escaped_failure(
    tmp_path, monkeypatch
):
    source_root = _synthetic_study_source_root(tmp_path)
    frozen_protocol = (
        source_root / "research/academic-pipeline/gemini-review-20261113/protocol-v2.json"
    )
    monkeypatch.setattr(evaluation, "ROOT", source_root)
    monkeypatch.setattr(evaluation, "PROTOCOL_PATH", frozen_protocol)
    monkeypatch.setattr(
        evaluation, "__file__", str(source_root / "scripts/run_gemini_review_evaluation.py")
    )
    output = tmp_path / "new-study"
    real_run_case = evaluation.run_case
    expected_cases = evaluation.build_cases()
    expected_surface = evaluation.build_surface_sentinels()
    expected_units = {
        (case["case_id"], arm, cohort)
        for cohort, cases in (("core", expected_cases), ("surface", expected_surface))
        for case in cases
        for arm in ARMS
    }
    observed = []

    def observe_frozen_inputs(case, arm_id):
        if not observed:
            assert json.loads((output / "cases.json").read_text()) == expected_cases
            assert json.loads((output / "surface_sentinels.json").read_text()) == expected_surface
            protocol = json.loads((output / "protocol.json").read_text())
            assert protocol["status"] == "FROZEN_BEFORE_EXECUTION"
            inventory = json.loads((output / "assignment_inventory.json").read_text())
            assert len(inventory) == len(expected_units) == 1712
            assert {
                (unit["case_id"], unit["arm"], unit["cohort"]) for unit in inventory
            } == expected_units
            assert protocol == json.loads(frozen_protocol.read_text())
            hashes = json.loads((output / "source_hashes.json").read_text())
            assert {
                "scripts/review_reference.py",
                "scripts/run_gemini_review_evaluation.py",
            } <= set(hashes)
            for relative_path, digest in hashes.items():
                assert (
                    digest == hashlib.sha256((source_root / relative_path).read_bytes()).hexdigest()
                )
            assert not (output / "rows.jsonl").exists()
            assert not (output / "summary.json").exists()
        observed.append((case["case_id"], arm_id))
        if len(observed) == 1:
            raise RuntimeError("assigned-test-failure")
        return real_run_case(case, arm_id)

    monkeypatch.setattr(evaluation, "run_case", observe_frozen_inputs)
    evaluation.run_study(output)
    core = [json.loads(line) for line in (output / "rows.jsonl").read_text().splitlines()]
    surface = [
        json.loads(line) for line in (output / "surface_rows.jsonl").read_text().splitlines()
    ]
    assert len(core) == 1664
    assert len(surface) == 48
    actual_units = {(row["case_id"], row["arm"], "core") for row in core}
    actual_units |= {(row["case_id"], row["arm"], "surface") for row in surface}
    assert actual_units == expected_units
    assert len(observed) == len(expected_units)
    failures = [row for row in core + surface if row["status"] == "FAILED"]
    assert len(failures) == 1
    assert "assigned-test-failure" in str(failures[0]["error"])
    core_summary = evaluation.summarize_rows(core)
    assert set(core_summary) == set(ARMS)
    assert all(metrics["assigned"] == 416 for metrics in core_summary.values())
    assert sum(metrics["failed"] for metrics in core_summary.values()) == 1


def test_study_refuses_nonempty_directory_without_changing_existing_evidence(tmp_path):
    existing = tmp_path / "previous-study"
    existing.mkdir()
    sentinel = existing / "raw.jsonl"
    original = b'{"immutable":"prior cohort"}\n'
    sentinel.write_bytes(original)
    with pytest.raises((ValueError, FileExistsError)):
        evaluation.run_study(existing)
    assert sentinel.read_bytes() == original
    assert sorted(path.name for path in existing.iterdir()) == ["raw.jsonl"]
