from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from nesy_game.disclosure import (
    ARM_NAMES,
    evaluate_case,
    evaluate_contract,
    load_frozen_contract,
    write_evaluation,
)

ROOT = Path(__file__).parents[1]
PACKET = ROOT / "research" / "npc-disclosure" / "reveal-hint-expectations-v1.json"
EXPECTED_PACKET_SHA256 = "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"


def _contract():
    return load_frozen_contract(PACKET, ROOT, public_sources=True)


def _cases(contract):
    packet = contract.packet
    return [*packet["normal_cases"], *packet["boundary_cases"], *packet["malformed_cases"]]


def _semantic(payload: dict) -> dict:
    return {
        "allowed": payload["allowed"],
        "codes": sorted(set(payload["codes"])),
        "template_id": payload["template_id"],
        "state_effect": payload["state_effect"],
    }


def _mutated_policy(contract, fixture: dict) -> dict:
    policy = copy.deepcopy(contract.scenario["disclosure_policy"])
    mutation = fixture["mutation"]
    if mutation["path"] == "disclosure_policy.stage_gates[0].minimum_stage":
        policy["stage_gates"][0]["minimum_stage"] = mutation["to"]
    elif mutation["path"] == "disclosure_policy.permanently_forbidden":
        policy["permanently_forbidden"] = copy.deepcopy(mutation["to"])
    else:  # frozen packet itself should reject any new mutation path
        raise AssertionError(f"unexpected frozen mutation path: {mutation['path']}")
    return policy


def test_frozen_packet_identity_and_separate_strata() -> None:
    assert hashlib.sha256(PACKET.read_bytes()).hexdigest() == EXPECTED_PACKET_SHA256
    contract = _contract()
    assert len(contract.packet["normal_cases"]) == 48
    assert len(contract.packet["boundary_cases"]) == 4
    assert len(contract.packet["malformed_cases"]) == 8
    assert len(contract.packet["rule_change_fixtures"]) == 2
    assert tuple(contract.packet["authorship"]["arms"]) == ARM_NAMES


def test_general_and_ontology_arms_match_independent_frozen_expectations() -> None:
    """The frozen expected object is the oracle; neither arm may manufacture labels."""
    contract = _contract()
    for case in _cases(contract):
        general = evaluate_case(contract, case, "general_rule").payload
        ontology = evaluate_case(contract, case, "ontology_gate").payload
        expected = case["expected"]
        expected_view = {
            "allowed": bool(expected["allowed"]),
            "codes": sorted(set(expected.get("codes", []))),
            "template_id": expected.get("template_id"),
            "state_effect": expected.get("state_effect", "denied_no_mutation"),
        }
        assert _semantic(general) == expected_view, case["case_id"]
        assert _semantic(ontology) == expected_view, case["case_id"]
        assert _semantic(general) == _semantic(ontology), case["case_id"]


def test_denial_preserves_complete_state_and_emits_only_safe_fallback() -> None:
    contract = _contract()
    denied = [case for case in _cases(contract) if not case["expected"]["allowed"]]
    assert denied
    for case in denied:
        for arm in ("general_rule", "ontology_gate"):
            payload = evaluate_case(contract, case, arm).payload
            assert payload["allowed"] is False, case["case_id"]
            assert payload["state_effect"] == "denied_no_mutation", case["case_id"]
            assert payload["prior_state"] == payload["state"], case["case_id"]
            assert payload["prior_state_hash"] == payload["next_state_hash"], case["case_id"]
            assert payload["mutated"] is False, case["case_id"]
            assert payload["template_id"] == "mira-safe-deflection-v1", case["case_id"]
            assert payload["display"]["template_id"] == "mira-safe-deflection-v1", case["case_id"]
            if case.get("fact_id"):
                assert case["fact_id"] not in payload["display"].get("text_en", "")


def test_fresh_and_redisplay_effects_preserve_the_frozen_state_contract() -> None:
    contract = _contract()
    fresh = [
        case
        for case in _cases(contract)
        if case["expected"].get("state_effect") == "fresh_disclosure"
    ]
    redisplay = [
        case
        for case in _cases(contract)
        if case["expected"].get("state_effect") == "redisplay_no_mutation"
    ]
    assert fresh and redisplay
    for case in fresh:
        payload = evaluate_case(contract, case, "general_rule").payload
        before = payload["prior_state"]
        after = payload["state"]
        actor = case["actor_id"]
        fact = case["fact_id"]
        assert fact in after["facts"], case["case_id"]
        assert fact in after["npcs"][actor]["disclosed"], case["case_id"]
        assert after["quest"]["stage"] == before["quest"]["stage"], case["case_id"]
        assert after["revision"] == before["revision"] + 1, case["case_id"]
        assert payload["prior_state_hash"] != payload["next_state_hash"], case["case_id"]
        if fact == "tide_marks_hint":
            assert after["npcs"][actor]["relationship_memory"] == [
                "turn-05:mira-shared-tide-marks-hint"
            ], case["case_id"]
        else:
            assert (
                after["npcs"][actor]["relationship_memory"]
                == before["npcs"][actor]["relationship_memory"]
            ), case["case_id"]
    for case in redisplay:
        payload = evaluate_case(contract, case, "general_rule").payload
        assert payload["state"] == payload["prior_state"], case["case_id"]
        assert payload["next_state_hash"] == payload["prior_state_hash"], case["case_id"]
        assert payload["mutated"] is False, case["case_id"]
        assert payload["state"]["revision"] == payload["prior_state"]["revision"], case["case_id"]


def test_replay_is_equal_and_inputs_are_sensitive() -> None:
    contract = _contract()
    case = next(item for item in contract.packet["normal_cases"] if item["case_id"] == "N-047")
    first = evaluate_case(contract, case, "general_rule").payload
    second = evaluate_case(contract, case, "general_rule").payload
    replay_fields = (
        "allowed",
        "codes",
        "checks",
        "errors",
        "rule_ids",
        "state_effect",
        "template_id",
        "prior_state_hash",
        "next_state_hash",
        "mutated",
        "prior_state",
        "state",
    )
    assert {key: first[key] for key in replay_fields} == {key: second[key] for key in replay_fields}
    changed = dict(case)
    changed["knows"] = False
    denied = evaluate_case(contract, changed, "general_rule").payload
    assert denied["allowed"] is False
    assert denied["codes"] == ["NPC_DOES_NOT_KNOW_FACT"]
    assert denied["next_state_hash"] == denied["prior_state_hash"]


def test_rule_change_fixtures_change_only_declared_pairs_and_keep_arms_in_parity() -> None:
    contract = _contract()
    baseline_policy = copy.deepcopy(contract.scenario["disclosure_policy"])
    by_id = {case["case_id"]: case for case in contract.packet["normal_cases"]}
    for fixture in contract.packet["rule_change_fixtures"]:
        mutated_policy = _mutated_policy(contract, fixture)
        assert contract.scenario["disclosure_policy"] == baseline_policy
        for delta in fixture["expected_deltas"]:
            case = by_id[delta["case_id"]]
            for arm in ("general_rule", "ontology_gate"):
                baseline = evaluate_case(contract, case, arm).payload
                mutated = evaluate_case(contract, case, arm, policy_override=mutated_policy).payload
                for expected_view, observed in (
                    (delta["baseline"], baseline),
                    (delta["mutated"], mutated),
                ):
                    for key, expected_value in expected_view.items():
                        actual_value = observed[key]
                        if key == "codes":
                            actual_value = sorted(set(actual_value))
                        assert actual_value == expected_value, (
                            fixture["fixture_id"],
                            delta["case_id"],
                            arm,
                            key,
                        )
            general_mutated = evaluate_case(
                contract, case, "general_rule", policy_override=mutated_policy
            ).payload
            ontology_mutated = evaluate_case(
                contract, case, "ontology_gate", policy_override=mutated_policy
            ).payload
            assert _semantic(general_mutated) == _semantic(ontology_mutated)
        assert contract.scenario["disclosure_policy"] == baseline_policy


@pytest.mark.parametrize(
    "case_id", ["M-001", "M-002", "M-003", "M-004", "M-005", "M-006", "M-007", "M-008"]
)
def test_malformed_cases_preserve_request_omission_and_policy_precedence(case_id: str) -> None:
    contract = _contract()
    case = next(item for item in contract.packet["malformed_cases"] if item["case_id"] == case_id)
    payload = evaluate_case(contract, case, "general_rule").payload
    expected = case["expected"]
    assert _semantic(payload) == {
        "allowed": expected["allowed"],
        "codes": sorted(set(expected.get("codes", []))),
        "template_id": expected["template_id"],
        "state_effect": "denied_no_mutation",
    }
    for key in ("actor_id", "fact_id"):
        if key in case:
            assert payload["request"][key] == case[key]
        else:
            assert key not in payload["request"]
    if case_id in {"M-007", "M-008"}:
        assert payload["codes"] in (["FORBIDDEN_DISCLOSURE"], ["STAGE_GATED_DISCLOSURE"])
        assert payload["codes"] != ["UNKNOWN_ACTOR"]
    assert payload["prior_state"] == payload["state"]


def test_runner_writes_only_agreed_result_surfaces(tmp_path: Path) -> None:
    write_evaluation(evaluate_contract(_contract()), tmp_path)
    expected_files = {
        "disclosure-trace.jsonl",
        "comparison-summary.json",
        "factual-summary.json",
        "metadata.json",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected_files
    comparison = json.loads((tmp_path / "comparison-summary.json").read_text(encoding="utf-8"))
    factual = json.loads((tmp_path / "factual-summary.json").read_text(encoding="utf-8"))
    assert comparison["case_counts"] == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60}
    assert comparison["general_vs_ontology"]["outcome_equal"] is True
    assert factual["status"] == "PASS"
