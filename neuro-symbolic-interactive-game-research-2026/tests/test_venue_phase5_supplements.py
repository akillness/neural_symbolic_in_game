#!/usr/bin/env python3
"""Offline and artifact tests for Phase-5 attested Anthropic API suite and v5 archive."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from venue_phase2_lib import get_expanded_5world_scenarios
from venue_phase4_lib import build_world_candidate_schema, phase2_ontology_to_spec
from venue_phase5_lib import (
    SECRET_OR_PII_RE,
    LiveApiBudget,
    assert_clean_text,
    call_anthropic_messages_structured,
    execute_arm_step,
    sanitize_json_schema_for_anthropic,
)


def test_sanitize_schema_and_secret_scrubber() -> None:
    schema = build_world_candidate_schema(["unlock_room"], ["keeper"])
    sanitized = sanitize_json_schema_for_anthropic(schema)
    raw = json.dumps(sanitized)
    assert '"minimum"' not in raw
    assert '"minLength"' not in raw
    assert sanitized["properties"]["action_type"]["enum"] == ["unlock_room"]

    with pytest.raises(ValueError, match="forbidden secret"):
        assert_clean_text("debug token sk-ant-usr-secret", context="unit")
    with pytest.raises(ValueError, match="forbidden secret"):
        assert_clean_text("wrkspc_01TestOrg", context="unit")


def test_budget_breaker_and_cached_mock_transport(tmp_path: Path) -> None:
    cache: dict[str, dict] = {}
    cache_path = tmp_path / "cache.jsonl"
    budget = LiveApiBudget(max_requests=2, max_tokens=1000)

    def _mock_transport(url, headers, body, timeout):
        assert url.endswith("/v1/messages")
        assert "temperature" not in json.loads(body.decode("utf-8"))
        resp = {
            "id": "msg_test_mock_01",
            "model": "claude-haiku-5-5",
            "stop_reason": "end_turn",
            "usage": {
                "input_tokens": 50,
                "output_tokens": 20,
                "output_tokens_details": {"thinking_tokens": 0},
                "service_tier": "standard",
            },
            "content": [{"type": "text", "text": json.dumps({"leak": False, "reason": "ok"})}],
        }
        return 200, {"request-id": "req_mock_01"}, json.dumps(resp).encode("utf-8")

    schema = {
        "type": "object",
        "properties": {"leak": {"type": "boolean"}, "reason": {"type": "string"}},
        "required": ["leak", "reason"],
    }
    r1 = call_anthropic_messages_structured(
        cache=cache,
        cache_path=cache_path,
        budget=budget,
        cache_key="k1",
        model="claude-haiku-5-5",
        system_prompt="sys",
        user_prompt="user",
        schema=schema,
        required_keys=("leak", "reason"),
        transport=_mock_transport,
        api_key="dummy-test-placeholder-only",
    )
    assert r1["parse_ok"] is True
    assert r1["served_model"] == "claude-haiku-5-5"
    assert r1["message_id_sha256"] == hashlib.sha256(b"msg_test_mock_01").hexdigest()
    assert budget.requests_used == 1

    # Second call with identical key hits cache without bumping requests_used
    r2 = call_anthropic_messages_structured(
        cache=cache,
        cache_path=cache_path,
        budget=budget,
        cache_key="k1",
        model="claude-haiku-5-5",
        system_prompt="sys",
        user_prompt="user",
        schema=schema,
        required_keys=("leak", "reason"),
        transport=_mock_transport,
        api_key="dummy-test-placeholder-only",
    )
    assert r2["parsed_output"] == {"leak": False, "reason": "ok"}
    assert budget.requests_used == 1

    budget.reserve_call()
    with pytest.raises(RuntimeError, match="request budget exhausted"):
        budget.reserve_call()


def test_phase5_7arm_step_evaluator_and_hybrid_repropose() -> None:
    sc = get_expanded_5world_scenarios()["sealed-lighthouse-v1"]
    state = sc.initial_state
    spec = phase2_ontology_to_spec()

    leaky_prop = {
        "action_id": "a-leak",
        "actor_id": "keeper_staff",
        "action_type": "unlock_room",
        "preconditions": ["at_pier"],
        "effects": ["beacon_unlocked"],
        "required_objects": [],
        "used_facts": ["valve_log"],
        "disclosed_facts": [],
        "required_quest_stage": 0,
        "quest_stage_effect": 1,
        "narrative_text": "Unlocking after reading valve log.",
    }
    safe_rl = execute_arm_step(
        arm="safe_rl_action_mask",
        state=state,
        raw_proposal=leaky_prop,
        scenario=sc,
        step_index=1,
        spec=spec,
    )
    assert safe_rl["committed"] is True
    assert safe_rl["unsafe_committed"] is True

    rho = execute_arm_step(
        arm="trace_rpg_multihop_rho_k2",
        state=state,
        raw_proposal=leaky_prop,
        scenario=sc,
        step_index=1,
        spec=spec,
    )
    assert rho["committed"] is False
    assert rho["unsafe_committed"] is False

    hybrid = execute_arm_step(
        arm="trace_rpg_hybrid_rho_llm_k1",
        state=state,
        raw_proposal=leaky_prop,
        scenario=sc,
        step_index=1,
        spec=spec,
        repropose_callback=lambda _c, _e: {
            "action_id": "a-safe",
            "actor_id": "keeper",
            "action_type": "unlock_room",
            "preconditions": ["at_pier"],
            "effects": ["beacon_unlocked"],
            "required_objects": [],
            "used_facts": [],
            "disclosed_facts": [],
            "required_quest_stage": 0,
            "quest_stage_effect": 1,
            "narrative_text": "Unlock beacon safely.",
        },
    )
    assert hybrid["committed"] is True
    assert hybrid["llm_retargeted"] is True
    assert hybrid["unsafe_committed"] is False


def test_phase5_artifacts_croissant_v5_and_zip_repro(tmp_path: Path) -> None:
    from build_neurips_supplement import FORBIDDEN_ANON_RE, build_neurips_supplement

    supp_dir = ROOT / "research/green-supplements"
    cro_v5 = json.loads(
        (supp_dir / "croissant_trace_rpg_benchmark_v5.json").read_text(encoding="utf-8")
    )
    assert len(cro_v5["distribution"]) == 26
    for item in cro_v5["distribution"]:
        fpath = supp_dir / item["name"]
        assert fpath.is_file()
        assert hashlib.sha256(fpath.read_bytes()).hexdigest() == item["sha256"]

    for fpath in [*sorted(supp_dir.glob("phase5_*")), supp_dir / "DATASHEET_v5.md"]:
        assert not SECRET_OR_PII_RE.search(fpath.read_text(encoding="utf-8")), f"leak in {fpath}"

    zip_path = tmp_path / "neurips-db-supplemental-benchmark.zip"
    summary = build_neurips_supplement(zip_path)
    assert summary["croissant_v5_verified"] == "26/26"
    assert summary["anon_pii_leaks"] == 0

    extract_dir = tmp_path / "unzipped"
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)
    for extracted in sorted(extract_dir.rglob("*")):
        if not extracted.is_file():
            continue
        raw_text = extracted.read_text(encoding="utf-8", errors="ignore")
        assert not FORBIDDEN_ANON_RE.search(raw_text), f"identity leak in {extracted}"
        collapsed = re.sub(r"""(['"])\s*\+\s*\1""", "", raw_text)
        assert not FORBIDDEN_ANON_RE.search(collapsed), f"split identity leak in {extracted}"
    proc = subprocess.run(
        [sys.executable, str(extract_dir / "reproduce_benchmark.py")],
        capture_output=True,
        text=True,
        check=True,
    )
    out = json.loads(proc.stdout)
    assert out["status"] == "PASS"
    assert out["croissant_v5_sha256_verified"] == "26/26"
