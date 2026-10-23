from __future__ import annotations

import hashlib
import json
import re
import subprocess

import pytest

from scripts.run_playable_evaluation import (
    EXACT_TERMINAL_HASH,
    EXPECTED_PRESENTATION_CHECKS,
    GODOT_PROJECT,
    find_godot_4,
    stage_project,
)

SHA256 = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_RECEIPT_FIELDS = {
    "receipt_schema_version",
    "receipt_seq",
    "monotonic_us",
    "telemetry_session_id",
    "scenario_id",
    "build_id",
    "build_fingerprint",
    "engine_version",
    "scene_id",
    "receipt_kind",
    "phase_code",
    "prior_state_sha256",
    "next_state_sha256",
    "canonical_state_unchanged",
    "payload",
}
FORBIDDEN_RECEIPT_TOKENS = (
    "fact_id",
    "fact_ids",
    "keeper_betrayal",
    "tide_marks_hint",
    "hidden_fact",
    "oracle",
    "save_path",
    "user_text",
)


@pytest.fixture(scope="module")
def evaluation_report(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict, str]:
    try:
        godot_info = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    if godot_info is None:
        pytest.skip("Godot 4.x is not installed; no engine execution is claimed")
    godot, _version = godot_info
    root = tmp_path_factory.mktemp("godot-observation")
    staged_project = root / "project"
    stage_project(GODOT_PROJECT, staged_project)
    source_project_hash = hashlib.sha256((GODOT_PROJECT / "project.godot").read_bytes()).hexdigest()

    imported = subprocess.run(
        [godot, "--headless", "--path", str(staged_project), "--import"],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr

    output_path = root / "evaluation.json"
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(staged_project),
            "res://scenes/main_3d.tscn",
            "--quit-after",
            "120",
            "--",
            "--evaluate",
            str(output_path),
            "--public-safe",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output_path.is_file(), result.stdout + result.stderr
    return json.loads(output_path.read_text(encoding="utf-8")), source_project_hash


@pytest.fixture(scope="module")
def autoplay_receipt_export(tmp_path_factory: pytest.TempPathFactory) -> dict:
    try:
        godot_info = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    if godot_info is None:
        pytest.skip("Godot 4.x is not installed; no engine execution is claimed")
    godot, _version = godot_info
    root = tmp_path_factory.mktemp("godot-autoplay-receipts")
    staged_project = root / "project"
    stage_project(GODOT_PROJECT, staged_project)
    imported = subprocess.run(
        [godot, "--headless", "--path", str(staged_project), "--import"],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr

    output_path = root / "receipts.json"
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(staged_project),
            "res://scenes/main_3d.tscn",
            "--",
            "--autoplay",
            "--receipt-output",
            str(output_path),
            "--public-safe",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output_path.is_file(), result.stdout + result.stderr
    return json.loads(output_path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def receipt_guard_probe(tmp_path_factory: pytest.TempPathFactory) -> dict:
    try:
        godot_info = find_godot_4()
    except RuntimeError as error:
        pytest.skip(str(error))
    if godot_info is None:
        pytest.skip("Godot 4.x is not installed; no engine execution is claimed")
    godot, _version = godot_info
    root = tmp_path_factory.mktemp("godot-receipt-guards")
    staged_project = root / "project"
    stage_project(GODOT_PROJECT, staged_project)
    probe_script = staged_project / "receipt_guard_probe.gd"
    probe_script.write_text(
        """extends SceneTree

func _init() -> void:
    call_deferred("_run_probe")

func _run_probe() -> void:
    var game = preload("res://scenes/main_3d.tscn").instantiate()
    root.add_child(game)
    await process_frame
    var args := OS.get_cmdline_user_args()
    var output_index := args.find("--probe-output")
    var output_path := str(args[output_index + 1]) if output_index + 1 < args.size() else ""
    var canonical_before: String = str(game.machine.state_hash())
    var recording_enabled_by_default := bool(game._receipt_recording_enabled)
    game._record_observation_receipt(
        "objective_rendered",
        "ARRIVAL",
        canonical_before,
        canonical_before,
        {"objective_code": "MIRA_AUTHORIZATION", "next_affordance_target": "mira"},
    )
    var default_rows: int = game._observation_receipts.size()
    game._receipt_recording_enabled = true
    var empty_commit_rejected := not bool(game._receipt_payload_safe({
        "receipt_kind": "commit_emitted",
        "payload": {},
    }))
    game._receipt_output_path = output_path + ".export"
    for _index in range(4097):
        game._record_observation_receipt(
            "objective_rendered",
            "ARRIVAL",
            canonical_before,
            canonical_before,
            {"objective_code": "MIRA_AUTHORIZATION", "next_affordance_target": "mira"},
        )
    var export_result := bool(game._export_receipts_if_requested())
    var canonical_after: String = str(game.machine.state_hash())
    var result := {
        "recording_enabled_by_default": recording_enabled_by_default,
        "default_rows": default_rows,
        "empty_commit_rejected": empty_commit_rejected,
        "overflowed": bool(game._receipt_overflowed),
        "export_failed": bool(game._receipt_export_failed),
        "export_result": export_result,
        "receipt_count": game._observation_receipts.size(),
        "canonical_before": canonical_before,
        "canonical_after": canonical_after,
        "export_exists": FileAccess.file_exists(game._receipt_output_path),
    }
    var file := FileAccess.open(output_path, FileAccess.WRITE)
    file.store_string(JSON.stringify(result))
    file.close()
    quit(0)
""",
        encoding="utf-8",
    )
    imported = subprocess.run(
        [godot, "--headless", "--path", str(staged_project), "--import"],
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert imported.returncode == 0, imported.stdout + imported.stderr
    output_path = root / "probe.json"
    result = subprocess.run(
        [
            godot,
            "--headless",
            "--path",
            str(staged_project),
            "--script",
            "res://receipt_guard_probe.gd",
            "--",
            "--probe-output",
            str(output_path),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert output_path.is_file(), result.stdout + result.stderr
    return json.loads(output_path.read_text(encoding="utf-8"))


def test_observation_receipts_are_ordered_timed_and_privacy_safe(
    evaluation_report: tuple[dict, str],
) -> None:
    report, _source_project_hash = evaluation_report
    telemetry = report["telemetry"]
    receipts = telemetry["receipts"]

    assert telemetry["passed"] is True
    assert [row["receipt_kind"] for row in receipts] == [
        "objective_rendered",
        "disclosure_outcome",
        "hold_emitted",
    ]
    assert [row["receipt_seq"] for row in receipts] == [1, 2, 3]
    assert receipts[0]["phase_code"] == "ARRIVAL"
    assert receipts[1]["phase_code"] == "DISCLOSURE"
    assert receipts[2]["phase_code"] == "HOLD"
    assert receipts[0]["payload"] == {
        "objective_code": "MIRA_AUTHORIZATION",
        "next_affordance_target": "mira",
    }

    previous_clock = -1
    for receipt in receipts:
        assert set(receipt) == REQUIRED_RECEIPT_FIELDS
        assert receipt["receipt_schema_version"] == "1.0.0"
        assert receipt["receipt_seq"] > 0
        assert receipt["monotonic_us"] >= previous_clock
        previous_clock = receipt["monotonic_us"]
        assert SHA256.fullmatch(receipt["prior_state_sha256"])
        assert SHA256.fullmatch(receipt["next_state_sha256"])
        assert receipt["canonical_state_unchanged"] is (
            receipt["prior_state_sha256"] == receipt["next_state_sha256"]
        )
        assert receipt["scenario_id"] == "sealed-lighthouse-v1"
        assert receipt["scene_id"] == "main_3d"
        assert isinstance(receipt["payload"], dict)

    hold = receipts[2]
    assert hold["canonical_state_unchanged"] is True
    assert hold["prior_state_sha256"] == hold["next_state_sha256"]
    assert hold["payload"] == {
        "reason_codes": ["STAGE_GATED_DISCLOSURE"],
        "gate_codes": ["DISCLOSURE/QUEST STAGE"],
        "correction_code": "ASK_AUTHORIZED_LEAD",
        "next_affordance_target": "mira",
    }

    disclosure = receipts[1]
    assert disclosure["canonical_state_unchanged"] is True
    assert disclosure["prior_state_sha256"] == disclosure["next_state_sha256"]
    assert disclosure["payload"]["operation_code"] == "reveal_hint"
    assert disclosure["payload"]["state_effect"] == "denied_no_mutation"
    assert disclosure["payload"]["mutated"] is False

    serialized_receipts = json.dumps(receipts, ensure_ascii=False, sort_keys=True).lower()
    for token in FORBIDDEN_RECEIPT_TOKENS:
        assert token not in serialized_receipts


def test_receipt_telemetry_preserves_core_denominator_and_canonical_hash(
    evaluation_report: tuple[dict, str],
) -> None:
    report, source_project_hash = evaluation_report
    telemetry = report["telemetry"]

    assert report["passed"] is True
    assert report["state_sha256_before"] == report["state_sha256_after"]
    assert SHA256.fullmatch(report["state_sha256_before"])
    assert report["checks"]
    assert len(report["checks"]) == len(EXPECTED_PRESENTATION_CHECKS) == 16
    assert {check["check"] for check in report["checks"]} == EXPECTED_PRESENTATION_CHECKS
    assert all(check["pass"] is True for check in report["checks"])

    assert [check["check"] for check in telemetry["checks"]] == [
        "receipts_present",
        "receipt_shape_complete",
        "receipt_sequence_and_clock_ordered",
        "receipt_state_hashes_valid",
        "receipt_payloads_code_only",
        "receipt_state_flags_consistent",
        "hold_receipts_preserve_state",
        "build_fingerprint_is_grounded",
        "build_fingerprint_recomputed",
        "telemetry_does_not_change_canonical_state",
        "receipt_capacity_not_exceeded",
    ]
    assert all(check["pass"] is True for check in telemetry["checks"])
    assert telemetry["engineering_only"] is True
    assert "participant" in telemetry["claim_boundary"]
    fingerprint = telemetry["build_fingerprint"]
    assert fingerprint["complete"] is True
    assert SHA256.fullmatch(fingerprint["combined_sha256"])
    for relative_path in (
        "project.godot",
        "scripts/game3d/game_3d.gd",
        "scripts/game3d/golden_path_layout.gd",
    ):
        source_digest = hashlib.sha256((GODOT_PROJECT / relative_path).read_bytes()).hexdigest()
        assert fingerprint["source_hashes"][f"res://{relative_path}"] == source_digest
    assert (
        source_project_hash
        == hashlib.sha256((GODOT_PROJECT / "project.godot").read_bytes()).hexdigest()
    )


def test_autoplay_receipt_export_covers_commits_case_revisits_and_session_end(
    autoplay_receipt_export: dict,
) -> None:
    export = autoplay_receipt_export
    receipts = export["receipts"]
    kinds = [receipt["receipt_kind"] for receipt in receipts]

    assert export["engineering_only"] is True
    assert "participant" in export["claim_boundary"]
    assert export["receipt_count"] == len(receipts)
    assert kinds[0] == "objective_rendered"
    assert kinds[-1] == "session_end_emitted"
    assert kinds.count("commit_emitted") == 3
    assert kinds.count("case_chain_opened") >= 1
    assert kinds.count("case_chain_closed") >= 1
    assert kinds.count("hold_emitted") >= 1

    assert [
        receipt["payload"]["operation_code"]
        for receipt in receipts
        if receipt["receipt_kind"] == "commit_emitted"
    ] == ["acquire_object", "install_lens", "reveal_hint"]
    case_actions = [
        receipt["payload"]["action_code"]
        for receipt in receipts
        if receipt["receipt_kind"] in {"case_chain_opened", "case_chain_closed"}
    ]
    assert set(case_actions) == {"OPEN_CASE_FILE", "CLOSE_CASE_FILE"}
    assert receipts[-1]["payload"] == {
        "commit_count": 3,
        "refusal_count": 1,
        "chain_filled": 3,
        "chain_total": 3,
    }

    previous_seq = 0
    previous_clock = -1
    previous_hash = None
    for receipt in receipts:
        assert receipt["receipt_seq"] == previous_seq + 1
        assert receipt["monotonic_us"] >= previous_clock
        assert SHA256.fullmatch(receipt["prior_state_sha256"])
        assert SHA256.fullmatch(receipt["next_state_sha256"])
        if previous_hash is not None:
            assert receipt["prior_state_sha256"] == previous_hash
        if receipt["receipt_kind"] in {
            "objective_rendered",
            "hold_emitted",
            "case_chain_opened",
            "case_chain_closed",
            "session_end_emitted",
        }:
            assert receipt["canonical_state_unchanged"] is True
            assert receipt["prior_state_sha256"] == receipt["next_state_sha256"]
        previous_seq = receipt["receipt_seq"]
        previous_clock = receipt["monotonic_us"]
        previous_hash = receipt["next_state_sha256"]

    assert export["initial_state_sha256"] == receipts[0]["prior_state_sha256"]
    assert export["final_state_sha256"] == receipts[-1]["next_state_sha256"]
    assert export["final_state_sha256"] == EXACT_TERMINAL_HASH
    serialized_receipts = json.dumps(receipts, ensure_ascii=False, sort_keys=True).lower()
    for token in FORBIDDEN_RECEIPT_TOKENS:
        assert token not in serialized_receipts


def test_receipt_recording_is_opt_in_and_overflow_refuses_export_without_state_mutation(
    receipt_guard_probe: dict,
) -> None:
    probe = receipt_guard_probe

    assert probe["recording_enabled_by_default"] is False
    assert probe["default_rows"] == 0
    assert probe["empty_commit_rejected"] is True
    assert probe["overflowed"] is True
    assert probe["export_failed"] is True
    assert probe["export_result"] is False
    assert probe["receipt_count"] == 4096
    assert probe["export_exists"] is False
    assert SHA256.fullmatch(probe["canonical_before"])
    assert probe["canonical_after"] == probe["canonical_before"]
