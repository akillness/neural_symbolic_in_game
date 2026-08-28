from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.run_balance_archetypes import (
    EXPECTED_ARCHETYPE_IDS,
    PROBE_ID,
    render_chart,
    render_markdown,
    validate_probe,
)
from scripts.run_playable_evaluation import EXACT_TERMINAL_HASH, GODOT_PROJECT, LATEST_DOCS

LATEST_PROBE = LATEST_DOCS / "balance-archetypes.json"


def _latest_probe() -> dict:
    assert LATEST_PROBE.is_file(), "run scripts/run_balance_archetypes.py to regenerate"
    return json.loads(LATEST_PROBE.read_text(encoding="utf-8"))


def test_latest_probe_artifact_passes_full_revalidation() -> None:
    report = _latest_probe()
    validate_probe(report)
    assert report["probe_id"] == PROBE_ID
    assert report["canonical_terminal_sha256"] == EXACT_TERMINAL_HASH
    assert tuple(row["archetype_id"] for row in report["archetypes"]) == EXPECTED_ARCHETYPE_IDS


def test_probe_validation_fails_closed_on_isolation_and_forbidden_drift() -> None:
    report = _latest_probe()

    broken = deepcopy(report)
    broken["archetypes"][1]["counts"]["refusals_state_isolated"] -= 1
    with pytest.raises(ValueError, match="revalidation failed"):
        validate_probe(broken)

    forbidden = deepcopy(report)
    forbidden["archetypes"][4]["counts"]["forbidden_commits"] += 1
    with pytest.raises(ValueError, match="revalidation failed"):
        validate_probe(forbidden)

    drifted = deepcopy(report)
    drifted["canonical_terminal_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="canonical terminal hash"):
        validate_probe(drifted)

    failed = deepcopy(report)
    failed["failures"] = [{"archetype_id": "A-01", "step_index": 0, "message": "boom"}]
    failed["passed"] = False
    with pytest.raises(ValueError, match="probe reported failures"):
        validate_probe(failed)


def test_markdown_and_chart_are_claim_bounded_and_deterministic() -> None:
    report = _latest_probe()
    markdown = render_markdown(report)
    assert "사람 플레이어의 밸런스 체감" in markdown
    assert "Not evidence for human balance perception" in markdown
    for archetype_id in EXPECTED_ARCHETYPE_IDS:
        assert archetype_id in markdown
    assert "OBJECT_NOT_REACHABLE" in markdown
    assert "QUEST_STAGE_PRECONDITION" in markdown
    assert "duplicate_install_recommits_revision_only" in markdown

    chart_first = render_chart(report)
    chart_second = render_chart(report)
    assert chart_first == chart_second
    assert chart_first.startswith("<svg ")
    assert "SL-BALANCE-PROBE-001" in chart_first
    assert "scripted engineering conformance" in chart_first


def test_probe_runner_contract_names_every_archetype_and_shared_layout() -> None:
    runner = (GODOT_PROJECT / "scripts/balance_probe_runner.gd").read_text(encoding="utf-8")
    for archetype_id in EXPECTED_ARCHETYPE_IDS:
        assert f'"{archetype_id}"' in runner
    assert 'preload("res://scripts/game3d/golden_path_layout.gd")' in runner
    assert 'preload("res://scripts/sealed_lighthouse_machine.gd")' in runner
    assert "designed-fixture" in runner
    assert "QUEST_STAGE_PRECONDITION" in runner

    scene = (GODOT_PROJECT / "scenes/balance_probe.tscn").read_text(encoding="utf-8")
    assert "res://scripts/balance_probe_runner.gd" in scene

    game_3d = (GODOT_PROJECT / "scripts/game3d/game_3d.gd").read_text(encoding="utf-8")
    assert "GoldenPathLayout.interactable_specs()" in game_3d
    assert "GoldenPathLayout.next_affordance(" in game_3d

    layout = Path(GODOT_PROJECT / "scripts/game3d/golden_path_layout.gd").read_text(
        encoding="utf-8"
    )
    assert "class_name GoldenPathLayout" in layout
    assert "next_affordance" in layout


def test_probe_artifact_records_machine_properties_with_ui_guards() -> None:
    report = _latest_probe()
    properties = report["aggregates"]["machine_properties"]
    names = {item["property"] for item in properties}
    assert "duplicate_install_recommits_revision_only" in names
    assert "duplicate_hint_recommits_revision_only" in names
    assert all(item["semantic_state_changed"] is False for item in properties)
    assert all(item["ui_guard"] for item in properties)
