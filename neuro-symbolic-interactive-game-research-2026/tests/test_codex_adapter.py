from __future__ import annotations

import json
from pathlib import Path

import pytest

from nesy_game import AdapterFailure, validate_candidate
from nesy_game.codex_adapter import (
    CANDIDATE_KEYS,
    LIVE_CANDIDATE_SCHEMA,
    CodexProposalAdapter,
    build_instruction,
    validate_live_candidate,
    visible_state_projection,
)
from scripts.run_live_pilot_rq2 import (
    ARMS,
    REPAIR_BUDGET,
    load_base_state,
    run_seed,
    summarize,
    world_state_from_manifest,
)

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "configs/pilot-manifest.json").read_text(encoding="utf-8"))
SCENARIO = json.loads(
    (ROOT / "game-track/godot/data/sealed_lighthouse.json").read_text(encoding="utf-8")
)


def _state():
    return world_state_from_manifest(MANIFEST["base_state"])


def _valid_envelope(request_id: str, candidate: dict) -> dict:
    return {
        "schema_version": "1.0.0",
        "request_id": request_id,
        "status": "candidate",
        "claim_boundary": "candidate_soft_proposal_only",
        "authorization_effect": "none",
        "canonical_state_mutated": False,
        "hard_validation_required": True,
        "candidate": candidate,
        "assumptions": [],
        "uncertainties": [],
    }


def _candidate(**overrides) -> dict:
    base = {
        "action_id": "a1",
        "actor_id": "player",
        "action_type": "SAY",
        "preconditions": ["met_guard"],
        "effects": [],
        "required_objects": [],
        "used_facts": [],
        "disclosed_facts": [],
        "required_quest_stage": 0,
        "quest_stage_effect": None,
        "narrative_text": "",
    }
    base.update(overrides)
    return base


class _StubCodex:
    def __init__(self, payload=None, code=0, error_code="stub_error"):
        self.payload = payload
        self.code = code
        self.error_code = error_code
        self.seen: list[dict] = []

    def run_prompt(self, **kwargs):
        self.seen.append(kwargs)
        request_id = kwargs["request_id"]
        if self.code != 0:
            return self.code, {"error_code": self.error_code}
        payload = self.payload or _valid_envelope(request_id, _candidate())
        payload = dict(payload)
        payload["request_id"] = request_id
        return 0, payload


def test_live_candidate_schema_pairs_type_with_every_const() -> None:
    """Structured-output rejects a bare const, so every property needs a type."""
    schema = json.loads(LIVE_CANDIDATE_SCHEMA.read_text(encoding="utf-8"))
    for name, spec in schema["properties"].items():
        if "const" in spec:
            assert "type" in spec, f"{name} declares const without type"
    assert set(schema["properties"]["candidate"]["properties"]) == CANDIDATE_KEYS
    assert schema["properties"]["canonical_state_mutated"]["const"] is False
    assert schema["properties"]["hard_validation_required"]["const"] is True


def test_projection_withholds_permanently_forbidden_facts() -> None:
    projection = visible_state_projection(_state(), SCENARIO)
    blob = json.dumps(projection, ensure_ascii=False)
    for forbidden in SCENARIO["disclosure_policy"]["permanently_forbidden"]:
        assert forbidden not in blob
    assert projection["withheld_fact_count"] >= 1
    assert "action_policies" in projection["state"]


def test_policy_blind_condition_hides_the_constraint_table() -> None:
    blind = visible_state_projection(
        _state(), SCENARIO, include_action_policies=False, condition_label="policy_blind"
    )
    assert "action_policies" not in blind["state"]
    assert blind["state"]["action_types"] == sorted(MANIFEST["base_state"]["action_policies"])
    assert blind["condition"] == "policy_blind"


def test_goal_directed_instruction_forbids_the_do_nothing_escape() -> None:
    projection = visible_state_projection(
        _state(),
        SCENARIO,
        include_action_policies=False,
        condition_label="goal_directed_blind",
    )
    text = build_instruction("req-1", projection, 11)
    assert "MUST change the world" in text
    assert "do-nothing action" in text
    plain = build_instruction("req-1", visible_state_projection(_state(), SCENARIO), 11)
    assert "MUST change the world" not in plain


def test_envelope_validator_rejects_authority_drift() -> None:
    good = _valid_envelope("req-1", _candidate())
    assert validate_live_candidate(good, "req-1") is True
    assert validate_live_candidate(good, "other") is False

    for field, value in (
        ("canonical_state_mutated", True),
        ("hard_validation_required", False),
        ("authorization_effect", "commit"),
        ("claim_boundary", "authoritative"),
        ("status", "committed"),
    ):
        broken = dict(good)
        broken[field] = value
        assert validate_live_candidate(broken, "req-1") is False, field

    missing_field = dict(good)
    missing_field["candidate"] = {k: v for k, v in _candidate().items() if k != "effects"}
    assert validate_live_candidate(missing_field, "req-1") is False


def test_adapter_returns_response_and_maps_transport_failure() -> None:
    adapter = CodexProposalAdapter(
        model_id="stub-model",
        model_revision="stub-rev",
        scenario=SCENARIO,
        codex_module=_StubCodex(),
    )
    response = adapter.propose(_state(), "sealed-lighthouse-v1", 11)
    assert response.candidate.action_type == "SAY"
    assert response.provider_latency_ms >= 0.0
    assert adapter.calls[0]["seed"] == 11

    failing = CodexProposalAdapter(
        model_id="stub-model",
        model_revision="stub-rev",
        scenario=SCENARIO,
        codex_module=_StubCodex(code=4, error_code="codex_exec_failed"),
    )
    with pytest.raises(AdapterFailure) as failure:
        failing.propose(_state(), "sealed-lighthouse-v1", 11)
    assert failure.value.code == "live_transport:codex_exec_failed"


def test_adapter_rejects_unknown_condition() -> None:
    with pytest.raises(ValueError, match="condition must be"):
        CodexProposalAdapter(
            model_id="m", model_revision="r", scenario=SCENARIO, condition="anything"
        )


def test_run_seed_shares_one_candidate_across_both_arms() -> None:
    """Matched comparison: both arms must consume the identical proposal."""
    invalid = _candidate(action_type="ROLLBACK_STAGE", quest_stage_effect=0)
    adapter = CodexProposalAdapter(
        model_id="stub-model",
        model_revision="stub-rev",
        scenario=SCENARIO,
        codex_module=_StubCodex(payload=_valid_envelope("x", invalid)),
    )
    state = _state()
    row = run_seed(adapter, state, scenario_id="sealed-lighthouse-v1", seed=11)

    assert row["status"] == "proposed"
    assert row["initial_valid"] is False
    assert "QUEST_STAGE_REGRESSION" in row["initial_error_codes"]
    assert set(row["arms"]) == set(ARMS)
    assert len(adapter.calls) == 1, "one live call must serve both arms"
    for arm in ARMS:
        assert row["arms"][arm]["status"] == "fallback"
        assert row["arms"][arm]["state_unchanged"] is True
        assert row["arms"][arm]["attempts"] == REPAIR_BUDGET


def test_summary_separates_invalid_only_denominator() -> None:
    adapter = CodexProposalAdapter(
        model_id="stub-model",
        model_revision="stub-rev",
        scenario=SCENARIO,
        codex_module=_StubCodex(),
    )
    state = _state()
    rows = [run_seed(adapter, state, scenario_id="sealed-lighthouse-v1", seed=s) for s in (11, 23)]
    summary = summarize(rows, model_id="stub-model", revision="stub-rev", condition="policy_blind")

    assert summary["evidence_tier"] == "screening-pilot-only"
    assert summary["token_accounting_available"] is False
    assert summary["matched_candidate_per_seed"] is True
    assert summary["counts"]["initially_valid"] == 2
    for arm in ARMS:
        assert summary["per_arm"][arm]["initially_invalid_cases"] == 0
        assert summary["per_arm"][arm]["commits_among_initially_invalid"] == 0


def test_every_promoted_live_cell_keeps_its_claim_boundary_and_state_isolation() -> None:
    root = ROOT / "research/academic-pipeline/rq2-live-pilot"
    if not root.is_dir():
        pytest.skip("promoted live-pilot artifacts are not present in this checkout")
    cells = sorted(root.glob("*/*/summary.json"))
    assert cells, "no promoted live-pilot cells found"
    for summary_path in cells:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        assert summary["condition"] == summary_path.parent.name
        assert summary["evidence_tier"] == "screening-pilot-only"
        assert summary["repair_budget"] == REPAIR_BUDGET
        assert summary["matched_candidate_per_seed"] is True
        rows = [
            json.loads(line)
            for line in (summary_path.parent / "results.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        ]
        assert len(rows) == summary["counts"]["seeds"]
        for row in rows:
            if row["status"] != "proposed":
                continue
            for arm in ARMS:
                if row["arms"][arm]["status"] == "fallback":
                    assert row["arms"][arm]["state_unchanged"] is True


def test_promoted_headline_cell_reproduces_the_guided_advantage() -> None:
    cell = (
        ROOT
        / "research/academic-pipeline/rq2-live-pilot/signal-repair-v2/policy_blind/summary.json"
    )
    if not cell.is_file():
        pytest.skip("headline live-pilot cell is not present in this checkout")
    summary = json.loads(cell.read_text(encoding="utf-8"))
    assert summary["counts"]["initially_invalid"] == summary["counts"]["proposals_returned"]
    guided = summary["per_arm"]["guided_repair"]
    blind = summary["per_arm"]["unchanged_retry"]
    assert guided["commits"] > blind["commits"], "headline separation must remain recorded"
    assert blind["commits"] == 0
    assert blind["non_commit_state_isolated"] == blind["non_commits"]


def test_variant_states_are_preregistered_and_v1_is_marked_superseded() -> None:
    catalog = json.loads((ROOT / "configs/live-pilot-states.json").read_text(encoding="utf-8"))
    assert "preregistration_note" in catalog
    assert catalog["states"]["signal-repair"]["status"] == "superseded-2026-08-28"
    assert "defect" in catalog["states"]["signal-repair"]
    v2 = catalog["states"]["signal-repair-v2"]
    assert "player" in v2["npc_knowledge"]
    for policy in v2["action_policies"].values():
        assert policy["required_effects"], "no zero-effect escape may exist in the variant"
        assert policy["allowed_quest_stage_effects"] == []


def test_frozen_base_state_is_read_from_the_immutable_packet() -> None:
    """The frozen base state must never be served from a drifting copy."""
    state, label = load_base_state(
        "frozen-pilot-base",
        manifest_path=ROOT / "configs/pilot-manifest.json",
        states_path=ROOT / "configs/live-pilot-states.json",
    )
    assert label == "frozen-pilot-base"
    assert state.state_id == MANIFEST["base_state"]["state_id"]

    with pytest.raises(SystemExit, match="unknown or non-executable base state"):
        load_base_state(
            "no-such-state",
            manifest_path=ROOT / "configs/pilot-manifest.json",
            states_path=ROOT / "configs/live-pilot-states.json",
        )


def test_hard_validator_still_rejects_a_forbidden_disclosure_candidate() -> None:
    """The prompt withholds the ID, but the gate must reject it if it appears anyway."""
    forbidden = SCENARIO["disclosure_policy"]["permanently_forbidden"][0]
    candidate_map = _candidate(disclosed_facts=[forbidden])
    from nesy_game import candidate_from_mapping

    result = validate_candidate(_state(), candidate_from_mapping(candidate_map))
    assert not result.valid
