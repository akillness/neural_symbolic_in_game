"""Cross-artifact publication gates for the 2026-10-23 current research lane.

These tests exercise generated artifacts and validators through their public file/function
surfaces. Historical E2/NPC receipts remain testable, but cannot silently become current
publication evidence.
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_npc_paper_results as npc_generator
import generate_paper_results as result_generator
import validate_contribution_crosswalk as crosswalk_validator
import validate_npc_goal_evidence as npc_validator
import validate_visual_assets as visual_validator

ACTIVE_OUTPUTS = {
    "pilot_results_en.tex",
    "pilot_results_ko.tex",
    "pilot_tables_en.tex",
    "pilot_tables_ko.tex",
    "contribution_map_en.tex",
    "contribution_map_ko.tex",
    "evidence_lanes_en.tex",
    "evidence_lanes_ko.tex",
}
RETIRED_MARKERS = (
    "live_pilot",
    "rq2-live-pilot",
    "C-PILOT-007",
    "C-PILOT-008",
    "C-RESULT-003",
    "signal-repair",
)


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def test_active_generation_does_not_read_retired_live_inputs(tmp_path: Path) -> None:
    """The current bilingual closure is reproducible when the retired E2 loader is unavailable."""
    output = tmp_path / "generated"
    with (
        patch.object(result_generator, "OUT", output),
        patch.object(
            result_generator,
            "_load_live_packet",
            side_effect=AssertionError("retired live packet must not be loaded"),
        ),
        patch.object(sys, "argv", ["generate_paper_results.py"]),
    ):
        result_generator.main()

    assert {path.name for path in output.iterdir()} == ACTIVE_OUTPUTS
    rendered = "\n".join(path.read_text(encoding="utf-8") for path in output.iterdir())
    assert not any(marker in rendered for marker in RETIRED_MARKERS)
    assert "E1" in rendered and "E3" in rendered and "ENG1" in rendered
    assert "E2" in rendered  # historical exclusion is disclosed, not relabeled as active


def test_active_manuscript_closure_rejects_hidden_historical_live_include() -> None:
    """A retired E2 fragment cannot re-enter active publication through a relative include."""
    original_read_text = Path.read_text

    def read_text(path: Path, *args: object, **kwargs: object) -> str:
        text = original_read_text(path, *args, **kwargs)
        if path == ROOT / "paper/latex/en/main.tex":
            return text + r"\input{../generated/historical-live/live_pilot_results_en.tex}" + "\n"
        return text

    with patch.object(Path, "read_text", new=read_text), pytest.raises(ValueError):
        crosswalk_validator.main()


@pytest.mark.parametrize("language", ("en", "ko"))
@pytest.mark.parametrize("mode", ("commented-out", "unused-macro"))
def test_required_pilot_results_input_must_be_in_effective_closure(
    language: str, mode: str
) -> None:
    """A required pilot-results prose fragment cannot hide in comments or unused macros."""
    crosswalk_validator._validate_generated_input_closure(language)
    main_path = (ROOT / f"paper/latex/{language}/main.tex").resolve()
    target = rf"\input{{../generated/pilot_results_{language}.tex}}"
    replacement = (
        f"%{target}"
        if mode == "commented-out"
        else rf"\newcommand{{\unusedPilotResults}}{{{target}}}"
    )
    original_read_text = Path.read_text

    def read_text(path: Path, *args: object, **kwargs: object) -> str:
        text = original_read_text(path, *args, **kwargs)
        if path == main_path:
            assert text.count(target) == 1
            return text.replace(target, replacement, 1)
        return text

    with (
        patch.object(Path, "read_text", new=read_text),
        pytest.raises(ValueError, match="active publication closure omits generated fragments"),
    ):
        crosswalk_validator._validate_generated_input_closure(language)


@pytest.mark.parametrize("language", ("en", "ko"))
def test_invoked_zero_arg_macro_keeps_pilot_results_in_effective_closure(language: str) -> None:
    """An invoked zero-argument macro still contributes its generated input to closure."""
    crosswalk_validator._validate_generated_input_closure(language)
    main_path = (ROOT / f"paper/latex/{language}/main.tex").resolve()
    target = rf"\input{{../generated/pilot_results_{language}.tex}}"
    replacement = (
        rf"\newcommand{{\activePilotResults}}{{{target}}}"
        "\n"
        r"\activePilotResults"
    )
    original_read_text = Path.read_text

    def read_text(path: Path, *args: object, **kwargs: object) -> str:
        text = original_read_text(path, *args, **kwargs)
        if path == main_path:
            assert text.count(target) == 1
            return text.replace(target, replacement, 1)
        return text

    with patch.object(Path, "read_text", new=read_text):
        closure = crosswalk_validator._tex_input_closure(main_path)
    assert (ROOT / f"paper/latex/generated/pilot_results_{language}.tex").resolve() in closure


@pytest.mark.parametrize("relative", ["../outside.txt", "absolute.txt", "link.txt", "directory"])
def test_crosswalk_evidence_paths_reject_escape_and_nonregular_files(
    tmp_path: Path, relative: str
) -> None:
    """Evidence paths must stay under the project root and resolve to regular files."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    (project_root / "absolute.txt").write_text("inside", encoding="utf-8")
    (project_root / "directory").mkdir()
    (project_root / "link.txt").symlink_to(outside)
    candidate = str(outside) if relative == "absolute.txt" else relative
    rows = [{"contribution_id": "C1", "evidence_paths": candidate}]
    with patch.object(crosswalk_validator, "ROOT", project_root), pytest.raises(ValueError):
        crosswalk_validator._assert_paths(rows, "evidence_paths")


def test_historical_e2_cannot_be_relabelled_as_active_in_lane_matrix(tmp_path: Path) -> None:
    """Changing E2's scope to active must fail instead of promoting its old cohort."""
    rows = _rows(result_generator.EXPERIMENT_MATRIX)
    for row in rows:
        if row["evidence_lane_id"] == "E2":
            row["publication_scope"] = "active"
    mutated = tmp_path / "experiment-evidence-matrix.csv"
    _write_rows(mutated, rows)

    with (
        patch.object(result_generator, "EXPERIMENT_MATRIX", mutated),
        pytest.raises(ValueError, match="historical"),
    ):
        result_generator._lane_table(False)


def test_current_lane_csv_maps_each_contribution_to_bounded_active_claims(tmp_path: Path) -> None:
    """C1-C5 map to active lanes and retain a non-efficacy ceiling in generated output."""
    contributions = _rows(result_generator.CONTRIBUTION_MATRIX)
    assert [row["contribution_id"] for row in contributions] == ["C1", "C2", "C3", "C4", "C5"]
    active = set(result_generator.ACTIVE_LANE_IDS)
    assert all(set(row["evidence_lane_ids"].split("|")) <= active for row in contributions)

    output = result_generator._contribution_map(False)
    for contribution_id in ("C1", "C2", "C3", "C4", "C5"):
        assert f"{contribution_id} & " in output
    assert "none supports an efficacy claim" in output
    assert "E2" not in output.split(r"\midrule", 1)[1]

    mutated = tmp_path / "contribution-evidence-matrix.csv"
    bad_rows = [dict(row) for row in contributions]
    bad_rows[-1]["evidence_lane_ids"] = "E2"
    _write_rows(mutated, bad_rows)
    with (
        patch.object(result_generator, "CONTRIBUTION_MATRIX", mutated),
        pytest.raises(ValueError, match="historical E2"),
    ):
        result_generator._contribution_map(False)


def test_historical_packet_receipts_reject_hash_and_identity_mutations(tmp_path: Path) -> None:
    """Historical validation remains fail-closed for both receipt bytes and packet identity."""
    packet_copy = tmp_path / "verified-run-006"
    shutil.copytree(npc_generator.PACKET, packet_copy)

    receipt_path = packet_copy / "sha256-manifest.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["files"][0]["sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    _, errors = npc_validator.validate_packet("NPC-SCR1", ROOT, packet_dir=packet_copy)
    assert any("sha256 receipt mismatch" in error for error in errors)

    shutil.rmtree(packet_copy)
    shutil.copytree(npc_generator.PACKET, packet_copy)
    assignment_path = packet_copy / "screening-assignment-manifest.json"
    assignment = json.loads(assignment_path.read_text(encoding="utf-8"))
    assignment["assignments"][0]["packet_id"] = "NPC-ENG1"
    assignment_path.write_text(json.dumps(assignment, indent=2) + "\n", encoding="utf-8")
    _, errors = npc_validator.validate_packet("NPC-SCR1", ROOT, packet_dir=packet_copy)
    assert any("identity/arm mismatch" in error for error in errors)


def test_active_manifest_rejects_unknown_table_surface_and_missing_owner() -> None:
    """Active table declarations must name real surfaces and owners; historical fragments are not enough."""
    manifest = json.loads(visual_validator.MANIFEST_PATH.read_text(encoding="utf-8"))
    validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)

    unknown_surface = json.loads(json.dumps(manifest))
    unknown_surface["table_sources"][0]["rendered_in"] = ["paper-en", "paper-ko", "retired-paper"]
    validator._validate_tables(unknown_surface)
    assert any("unknown rendered surfaces" in error for error in validator.errors)

    missing_owner = json.loads(json.dumps(manifest))
    missing_owner["visual_assets"][0]["used_by"] = ["paper/latex/en/not-a-real-owner.tex"]
    validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
    validator._validate_visual_assets(missing_owner)
    assert any("missing owner" in error for error in validator.errors)


def test_historical_uncompiled_table_fragment_is_not_current_closure() -> None:
    """A retired generated fragment on disk is harmless unless an active paper closure reaches it."""
    manifest = json.loads(visual_validator.MANIFEST_PATH.read_text(encoding="utf-8"))
    validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
    validator._validate_tables(manifest)
    assert not any("historical-live" in error for error in validator.errors)


def test_traceability_rubric_is_proposed_and_source_bound_without_scores() -> None:
    """The six-dimensional rubric binds sources while refusing to manufacture achieved rates."""
    rubric_path = ROOT / "research/traceability-scoring-20261023/rubric.json"
    rubric = json.loads(rubric_path.read_text(encoding="utf-8"))
    assert rubric["status"] == "PROPOSED_NOT_VALIDATED"
    assert rubric["measurement_status"]["proposal_not_measured"] is True
    dimensions = rubric["dimensions"]
    assert [item["id"] for item in dimensions] == [f"TR0{index}" for index in range(1, 7)]
    source_ids = set(rubric["source_refs"])
    assert source_ids == {f"SRC0{index}" for index in range(1, 6)}
    for dimension in dimensions:
        assert set(dimension["source_refs"]) <= source_ids
        assert "achieved_score" not in dimension
        assert "measured_rate" not in dimension
    assert "No traceability percentage" in " ".join(rubric["nonclaims"])

    mutated = json.loads(json.dumps(rubric))
    mutated["dimensions"][0]["source_refs"] = ["SRC-UNKNOWN"]
    with pytest.raises(AssertionError):
        assert set(mutated["dimensions"][0]["source_refs"]) <= source_ids


def test_prospective_comparison_plan_is_nonexecuted_independent_and_fail_closed() -> None:
    """The future plan preserves blocked cells, fresh repeats and null caps without implying results."""
    protocol = json.loads(
        (ROOT / "research/development-comparison-20261023/protocol.json").read_text(
            encoding="utf-8"
        )
    )
    current = protocol["current_evidence_boundary"]
    assert current["development_runs"] == 1
    assert current["native_cli_invocations"] == 6
    assert current["independent_repeats"] == 0
    assert current["whole_game_creation_evidence"] is False
    assert "not provider revision" in current["identity_boundary"]
    assert "fresh workspace" in protocol["microgame_task_contract"]["freshness"]
    assert "fresh thread" in protocol["microgame_task_contract"]["freshness"]
    assert protocol["candidate_pilot_matrix"]["independent_repeats_per_cell"] == 2
    assert protocol["candidate_pilot_matrix"]["status"] == "PROPOSED_NOT_EXECUTED"

    approval = protocol["approval_revision"]
    assert approval["status"] == "APPROVED_FOR_PLANNING_ONLY"
    assert approval["aggregate_additional_api_spend_cap_usd"] == 100
    assert set(approval["aggregate_scope"]) == {"whole_game_coding", "ontology_content_generation"}

    caps = protocol["caps_and_approval"]
    assert caps["status"] == "PARTIALLY_APPROVED_AGGREGATE_ONLY"
    assert caps["aggregate_additional_api_spend_cap_usd"] == 100
    assert caps["aggregate_spend_approval_status"] == "APPROVED_VIA_USER_ASK_2026-10-23"
    assert set(caps["aggregate_spend_scope"]) == {"whole_game_coding", "ontology_content_generation"}
    for field in ("budget_usd", "input_token_cap", "output_token_cap", "wall_time_cap_seconds",
                  "repair_attempt_cap", "tool_call_cap", "operator_intervention_cap", "price_guard"):
        assert caps[field] is None
    assert caps["operational_caps_status"] == "REQUIRED_UNAPPROVED_PARAMETERS"
    assert caps["approval_receipt"] is None
    assert "fails the launch gate" in caps["rule"]

    boundary = protocol["execution_boundary"]
    assert all(value == 0 for key, value in boundary.items() if key.endswith("_started"))
    assert protocol["status"] == "PROPOSED_NOT_EXECUTED"
    assert all(stage["status"] == "PROPOSED_NOT_EXECUTED" for stage in protocol["staged_plan"])
    schedule = protocol["minimal_feasibility_schedule"]
    assert schedule["status"] == "PROPOSED_NOT_EXECUTED"
    assert schedule["aggregate_budget_ceiling_usd"] == 100
    assert schedule["maximum_planned_assignments_if_all_gates_pass"] == 36
    assert schedule["no_execution_statement"].startswith("No F0, F1 or F2")
    expanded = protocol["expanded_candidate_matrix"]
    assert expanded["status"] == "PROPOSED_NOT_EXECUTED"
    assert expanded["planned_runs_per_track"] == 72
    assert expanded["planned_runs_if_both_tracks_are_declared"] == 144
    cohort = protocol["expanded_candidate_cohort"]
    assert cohort["status"] == "PROPOSED_NOT_EXECUTED"
    assert all(candidate["canonical_id"] is None for candidate in cohort["candidates"])
    assert all(candidate["coding_tool_capable"] is None for candidate in cohort["candidates"])
    assert all(candidate["content_generation_capable"] is None for candidate in cohort["candidates"])
    assert "No candidate in this expanded cohort has been called" in cohort["no_execution_statement"]
    assert "no resume-as-repeat" in protocol["microgame_task_contract"]["freshness"]
    assert "old" not in current["source_case_scope"].casefold()

    mutated = json.loads(json.dumps(protocol))
    mutated["candidate_pilot_matrix"]["cells"][0]["assigned_runs"] = 1
    with pytest.raises(AssertionError):
        assert (
            mutated["candidate_pilot_matrix"]["cells"][0]["assigned_runs"]
            == protocol["candidate_pilot_matrix"]["independent_repeats_per_cell"]
        )
