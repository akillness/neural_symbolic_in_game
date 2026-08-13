#!/usr/bin/env python3
"""Validate the persistent game-studio workspace and paper-boundary contract."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

try:
    from scripts.png_contract import validate_render_png
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from png_contract import validate_render_png

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
CURRENT = ROOT / "_workspace" / "current"

REQUIRED_CURRENT = {
    "intake/production-brief.md",
    "intake/game-survey.md",
    "design/concept.md",
    "design/worldview.md",
    "design/balance-sheet.md",
    "design/core-loop.md",
    "design/novelty-scorecard.md",
    "design/presentation-spec.md",
    "design/trend-survey/triage.md",
    "design/trend-survey/context.md",
    "design/trend-survey/solutions.md",
    "pm/revenue-map.md",
    "pm/reward-bands.md",
    "pm/negotiation-record.md",
    "pm/revenue-forecast.md",
    "engineering/architecture-contract.md",
    "engineering/perf-budget.md",
    "engineering/movement-optimization.md",
    "engineering/resource-manifest.md",
    "ops/telemetry-contract.md",
    "ops/rollback-runbook.md",
    "ops/release-readiness.md",
    "ui/visual-direction.md",
    "ui/blinded-evaluation-ui.md",
    "ui/human-study-data-protocol.md",
    "qa/test-plan.md",
    "qa/benchmark-notes.md",
    "qa/playtest-report.md",
    "qa/exploit-register.md",
    "qa/defect-register.md",
    "qa/regression-matrix.md",
    "qa/discovery-notes.md",
    "qa/gate-measurements.md",
    "qa/content-worldview-audit.md",
    "production/task-manifest.md",
    "production/decision-log.md",
    "production/generator-ownership.md",
    "production/gate-reviews/stage-1-baseline.md",
    "conflicts.md",
}

REQUIRED_DESIGN_PAIRS = {
    "gdd.en.md": "gdd.ko.md",
    "paper-crosswalk.en.md": "paper-crosswalk.ko.md",
    "scenario-oracle-plan.en.md": "scenario-oracle-plan.ko.md",
}


def fail(message: str) -> None:
    raise ValueError(message)


def check_single_workspace() -> None:
    if not CURRENT.is_dir():
        fail("missing _workspace/current")
    missing = sorted(path for path in REQUIRED_CURRENT if not (CURRENT / path).is_file())
    if missing:
        fail(f"missing studio artifacts: {missing}")
    siblings = {
        path.name
        for path in CURRENT.parent.iterdir()
        if path.is_dir() and path.name not in {"current", "archive", "editor"}
    }
    if siblings:
        fail(f"dated or unknown workspace siblings are prohibited: {sorted(siblings)}")
    root_ignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    if re.search(r"(?m)^_workspace/$", root_ignore):
        fail("unanchored _workspace ignore hides the project studio")


def check_rule_contract() -> None:
    rules = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    pointer = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    if "../AGENTS.md" not in pointer or "CLAUDE.md" not in pointer:
        fail("project AGENTS.md must point to both research and studio contracts")
    forbidden = re.findall(r"\{[A-Z][A-Z0-9_]*\}", rules)
    if forbidden:
        fail(f"unresolved rule placeholders: {forbidden}")
    required_fragments = {
        "_workspace/current/": "single live workspace",
        "Godot 4.x headless-first": "engine selection",
        "Re-derive this file": "workspace/rule freshness",
        "god-tibo-imagen": "asset generator ownership",
        "structured text/state": "dual-track primary boundary",
        "./scripts/validate_game_track.sh": "exact regression command",
    }
    for fragment, purpose in required_fragments.items():
        if fragment not in rules:
            fail(f"studio rule missing {purpose}: {fragment}")


def check_design_pairs() -> None:
    design_root = ROOT / "game-track" / "design"
    for en_name, ko_name in REQUIRED_DESIGN_PAIRS.items():
        en = (design_root / en_name).read_text(encoding="utf-8")
        ko = (design_root / ko_name).read_text(encoding="utf-8")
        en_pair = re.search(r"pair_id:\s*([^\n]+)", en)
        ko_pair = re.search(r"pair_id:\s*([^\n]+)", ko)
        if not en_pair or not ko_pair or en_pair.group(1).strip() != ko_pair.group(1).strip():
            fail(f"pair_id mismatch: {en_name}, {ko_name}")
        for token in (
            "C-RESULT-001",
            "C-RESULT-002",
            "C-RESULT-003",
            "C-RESULT-004",
            "C-RESULT-005",
        ):
            if (token in en) != (token in ko):
                fail(f"claim token parity mismatch for {token}: {en_name}, {ko_name}")
        en_numbers = set(re.findall(r"\b(?:SL-[A-Z0-9-]+|RQ[1-5]|C-RESULT-00[1-5])\b", en))
        ko_numbers = set(re.findall(r"\b(?:SL-[A-Z0-9-]+|RQ[1-5]|C-RESULT-00[1-5])\b", ko))
        if en_numbers != ko_numbers:
            fail(
                f"stable ID parity mismatch in {en_name}/{ko_name}: "
                f"EN-only={sorted(en_numbers - ko_numbers)}, KO-only={sorted(ko_numbers - en_numbers)}"
            )


def check_experiment_config() -> None:
    game = yaml.safe_load((ROOT / "configs" / "experimental-game.yaml").read_text())
    matrix = yaml.safe_load((ROOT / "configs" / "experiment-matrix.yaml").read_text())
    expected = {
        "direct_commit",
        "structural_constraint_only",
        "validator_rejection_only",
        "matched_budget_blind_retry",
        "structured_repair",
        "trace_rpg_full",
    }
    for stage in ("stage_1_screening", "stage_2_confirmatory"):
        observed = set(matrix["design"][stage]["controller_arms"])
        if observed != expected:
            fail(f"{stage} controller arms differ: {sorted(observed)}")
    if set(game["controller_arms"]) != expected:
        fail("experimental-game arm set differs from experiment matrix")
    if game["tracks"]["primary"]["generated_images"] != "prohibited":
        fail("primary track must prohibit generated images")
    if game["authority"]["current_fixture_authority"] != "godot-authored-policy-mirror":
        fail("current fixture authority must remain the engine-local policy mirror")
    if game["authority"]["live_python_authorization_transport"] != "not-executed":
        fail("live Python authorization must not be promoted without execution evidence")
    if game["tracks"]["secondary"]["id"] != "secondary-vlm-ui":
        fail("secondary track identifier drifted")
    if matrix["controls"]["experimental_game"]["secondary_input_track"] != "secondary-vlm-ui":
        fail("experiment matrix secondary track identifier drifted")
    if game["human_study"]["recruitment"] != "prohibited":
        fail("Cycle 1 recruitment boundary changed")


def check_claim_boundary() -> None:
    ledger = yaml.safe_load((ROOT / "research" / "claim-ledger.yaml").read_text())
    statuses = {row["id"]: row["status"] for row in ledger["claims"]}
    for index in range(1, 6):
        claim_id = f"C-RESULT-{index:03d}"
        if statuses.get(claim_id) != "TODO-RESULT":
            fail(f"planned efficacy result was promoted: {claim_id}")
    expected_game_claims = {
        "C-GAME-DESIGN-001": "approved-design-protocol",
        "C-GAME-DESIGN-002": "verified-authored-engine-fixture",
        "C-GAME-DESIGN-003": "verified-authored-engine-render-fixture",
    }
    for claim_id, expected_status in expected_game_claims.items():
        if statuses.get(claim_id) != expected_status:
            fail(f"bounded game claim drifted: {claim_id}")


def check_asset_manifest() -> None:
    manifest = json.loads(
        (ROOT / "game-track/assets/concepts/asset-manifest.json").read_text(encoding="utf-8")
    )
    if len(manifest["assets"]) != 4:
        fail("expected four frozen concept assets")
    if manifest["primary_experiment_eligible"] is not False:
        fail("concept pack entered the primary track")
    if manifest["track"] != "secondary-vlm-ui":
        fail("asset pack secondary track identifier drifted")


def check_engine_evidence() -> None:
    tech_root = CURRENT / "engineering" / "tech-verification"
    staging_root = tech_root / "staging"
    if staging_root.exists() and any(staging_root.iterdir()):
        fail(f"incomplete Godot evidence captures remain in staging: {staging_root}")
    pointer_path = tech_root / "current.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    if set(pointer) != {"schema_version", "evidence_set_id", "manifest_sha256"}:
        fail("current Godot evidence pointer fields drifted")
    if pointer["schema_version"] != "1.0.0":
        fail("current Godot evidence pointer version drifted")
    evidence_set_id = pointer["evidence_set_id"]
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]{2,127}", evidence_set_id) is None:
        fail("unsafe current Godot evidence-set ID")
    evidence_parent = tech_root / "evidence"
    evidence_root = evidence_parent / evidence_set_id
    if evidence_root.resolve().parent != evidence_parent.resolve():
        fail("current Godot evidence pointer escaped retained root")
    manifest_path = evidence_root / "evidence-manifest.json"
    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != pointer["manifest_sha256"]:
        fail("current Godot evidence manifest hash drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("evidence_set_id") != evidence_set_id:
        fail("current pointer and Godot evidence manifest ID differ")
    current_facing_docs = (
        ROOT / "game-track/README.en.md",
        ROOT / "game-track/README.ko.md",
        ROOT / "game-track/godot/README.en.md",
        ROOT / "game-track/godot/README.ko.md",
        ROOT / "game-track/design/paper-crosswalk.en.md",
        ROOT / "game-track/design/paper-crosswalk.ko.md",
    )
    for doc_path in current_facing_docs:
        document = doc_path.read_text(encoding="utf-8")
        if evidence_set_id not in document:
            fail(f"current Godot evidence ID is missing from public doc: {doc_path}")
    expected_engine_version = "4.7.1.stable.official.a13da4feb"
    if manifest["engine_version"] != expected_engine_version:
        fail(f"unexpected retained Godot version: {manifest['engine_version']}")
    schemas = ROOT / "game-track" / "schemas"
    event_schema = json.loads((schemas / "experimental-game-event.schema.json").read_text())
    save_schema = json.loads((schemas / "experimental-game-save.schema.json").read_text())
    summary_schema = json.loads((schemas / "experimental-game-summary.schema.json").read_text())
    render_schema = json.loads(
        (schemas / "experimental-game-render-capture.schema.json").read_text()
    )
    event_validator = Draft202012Validator(event_schema)
    save_validator = Draft202012Validator(save_schema)
    summary_validator = Draft202012Validator(summary_schema)
    render_validator = Draft202012Validator(render_schema)
    expected_fixtures = {
        "sealed-lighthouse-canonical-v1",
        "sealed-lighthouse-corrupt-save-v1",
        "sealed-lighthouse-duplicate-event-v1",
        "sealed-lighthouse-timeout-v1",
    }
    observed = {row["fixture_id"] for row in manifest["runs"]}
    if observed != expected_fixtures:
        fail(f"unexpected engine evidence fixture set: {sorted(observed)}")
    expected_files = {"evidence-manifest.json"}
    for fixture_id in expected_fixtures:
        expected_files.update(
            {
                f"{fixture_id}/events.jsonl",
                f"{fixture_id}/save.json",
                f"{fixture_id}/summary.json",
            }
        )
    render_capture = manifest.get("render_capture")
    if not isinstance(render_capture, dict):
        fail("current Godot evidence set lacks non-headless render capture evidence")
    render_validator.validate(render_capture)
    if render_capture["evidence_set_id"] != evidence_set_id:
        fail("render capture evidence-set ID drifted")
    if render_capture["engine"]["headless"] is not False:
        fail("render capture was incorrectly recorded as headless")
    if render_capture["engine"]["display_server"] == "headless":
        fail("render capture used the headless display server")
    if manifest.get("render_command_template") is None:
        fail("render capture command template is missing")
    render_root = evidence_root / "rendered-canonical-v1"
    capture_manifest_path = render_root / "capture-manifest.json"
    if json.loads(capture_manifest_path.read_text(encoding="utf-8")) != render_capture:
        fail("top-level and retained render capture manifests differ")
    expected_files.add("rendered-canonical-v1/capture-manifest.json")
    canonical_events_path = evidence_root / "sealed-lighthouse-canonical-v1/events.jsonl"
    canonical_summary_path = evidence_root / "sealed-lighthouse-canonical-v1/summary.json"
    if (
        hashlib.sha256(canonical_events_path.read_bytes()).hexdigest()
        != render_capture["source"]["events_sha256"]
    ):
        fail("render source events hash drifted")
    if (
        hashlib.sha256(canonical_summary_path.read_bytes()).hexdigest()
        != render_capture["source"]["summary_sha256"]
    ):
        fail("render source summary hash drifted")
    canonical_summary = json.loads(canonical_summary_path.read_text(encoding="utf-8"))
    for field in ("fixture_id", "scenario_id", "run_id", "episode_id", "seed"):
        if render_capture[field] != canonical_summary[field]:
            fail(f"render capture summary identity drifted: {field}")
    render_software_paths = {
        "capture_scene_sha256": ROOT / "game-track/godot/scenes/evidence_capture.tscn",
        "capture_runner_sha256": ROOT / "game-track/godot/scripts/evidence_capture_runner.gd",
        "project_sha256": ROOT / "game-track/godot/project.godot",
        "capture_pipeline_sha256": ROOT / "scripts/capture_godot_evidence.py",
        "png_contract_sha256": ROOT / "scripts/png_contract.py",
        "capture_schema_sha256": (
            ROOT / "game-track/schemas/experimental-game-render-capture.schema.json"
        ),
        "retained_validator_sha256": ROOT / "scripts/validate_game_studio.py",
        "uv_lock_sha256": ROOT / "uv.lock",
    }
    for field, path in render_software_paths.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != render_capture["source"][field]:
            fail(f"retained render evidence is stale against current {field}: {path}")
    toolchain = render_capture["validation_toolchain"]
    if toolchain["json_schema_draft"] != "2020-12":
        fail("retained render JSON Schema draft drifted")
    if toolchain["png_decoder"] != "stdlib-zlib-filter-reconstruction-v1":
        fail("retained render PNG decoder identity drifted")
    canonical_events = {
        event["event_id"]: event
        for event in (
            json.loads(line)
            for line in canonical_events_path.read_text(encoding="utf-8").splitlines()
        )
    }
    expected_capture_rows = {
        "sl-rc-001-arrival": {
            "event_id": "evt-000-observe",
            "file": "sl-rc-001-arrival.png",
            "beat": "arrival_observation",
            "view_mode": "participant-primary",
            "participant_visible": True,
        },
        "sl-rc-002-rejected-secret": {
            "event_id": "evt-002-fallback-secret",
            "file": "sl-rc-002-rejected-secret.png",
            "beat": "forbidden_disclosure_rejected",
            "view_mode": "experiment-inspector",
            "participant_visible": False,
        },
        "sl-rc-003-authorized-hint": {
            "event_id": "evt-005-commit-hint",
            "file": "sl-rc-003-authorized-hint.png",
            "beat": "authorized_hint_committed",
            "view_mode": "experiment-inspector",
            "participant_visible": False,
        },
    }
    if {row["capture_id"] for row in render_capture["captures"]} != set(expected_capture_rows):
        fail("render capture ID set drifted")
    for capture in render_capture["captures"]:
        capture_id = capture["capture_id"]
        for field, value in expected_capture_rows[capture_id].items():
            if capture[field] != value:
                fail(f"render capture {field} mapping drifted: {capture_id}")
        event = canonical_events[capture["event_id"]]
        for field in (
            "sequence",
            "delivery_index",
            "turn",
            "world_state_hash_before",
            "world_state_hash",
        ):
            if capture[field] != event[field]:
                fail(f"render capture {field} drifted: {capture_id}")
        if capture["validation_status"] != event["validation"]["status"]:
            fail(f"render capture validation status drifted: {capture_id}")
        if capture["validation_codes"] != event["validation"]["codes"]:
            fail(f"render capture validation codes drifted: {capture_id}")
        if capture["generated_assets_in_frame"] is not False:
            fail(f"generated asset entered primary render capture: {capture_id}")
        image_path = render_root / capture["file"]
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != capture["sha256"]:
            fail(f"render capture hash drifted: {capture_id}")
        if image_path.stat().st_size != capture["bytes"]:
            fail(f"render capture byte count drifted: {capture_id}")
        if validate_render_png(image_path).to_jsonable() != capture["pixel_stats"]:
            fail(f"render capture pixel contract drifted: {capture_id}")
        expected_files.add(f"rendered-canonical-v1/{capture['file']}")
    rejected = next(
        row
        for row in render_capture["captures"]
        if row["capture_id"] == "sl-rc-002-rejected-secret"
    )
    if rejected["world_state_hash_before"] != rejected["world_state_hash"]:
        fail("rendered rejection did not preserve state")
    authorized = next(
        row
        for row in render_capture["captures"]
        if row["capture_id"] == "sl-rc-003-authorized-hint"
    )
    authorized_event = canonical_events[authorized["event_id"]]
    if not authorized_event["commit"]["applied"]:
        fail("authorized-hint render is not bound to an applied commit")
    actual_files = {
        path.relative_to(evidence_root).as_posix()
        for path in evidence_root.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        fail(
            "retained evidence file set drifted: "
            f"missing={sorted(expected_files - actual_files)}, "
            f"unexpected={sorted(actual_files - expected_files)}"
        )
    terminal_hashes: set[str] = set()
    for run in manifest["runs"]:
        summary = run["summary"]
        summary_validator.validate(summary)
        if summary["execution_status"] != "OBSERVED_ENGINE_RUN":
            fail(f"engine run is not observed: {run['fixture_id']}")
        if summary["engine"]["headless"] is not True:
            fail(f"engine run is not headless: {run['fixture_id']}")
        if not summary["engine"]["version"].startswith("4.7.1"):
            fail(f"summary Godot version drifted: {run['fixture_id']}")
        false_checks = [key for key, value in summary["checks"].items() if value is not True]
        if false_checks:
            fail(f"failed engine correctness checks in {run['fixture_id']}: {false_checks}")
        terminal_hashes.add(summary["terminal_state_hash"])
        run_root = evidence_root / run["fixture_id"]
        for filename, receipt in run["files"].items():
            path = run_root / filename
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != receipt["sha256"] or path.stat().st_size != receipt["bytes"]:
                fail(f"engine evidence hash/size mismatch: {path}")
        file_summary = json.loads((run_root / "summary.json").read_text(encoding="utf-8"))
        if file_summary != summary:
            fail(f"manifest summary differs from retained summary: {run['fixture_id']}")
        save_validator.validate(json.loads((run_root / "save.json").read_text(encoding="utf-8")))
        events = [
            json.loads(line)
            for line in (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        for delivery_index, event in enumerate(events):
            event_validator.validate(event)
            if event["delivery_index"] != delivery_index:
                fail(f"non-contiguous delivery order in {run['fixture_id']}")
        logical_sequences = sorted({event["sequence"] for event in events})
        if logical_sequences != list(range(len(logical_sequences))):
            fail(f"non-contiguous logical event order in {run['fixture_id']}")
        by_event_id: dict[str, list[dict]] = {}
        for event in events:
            by_event_id.setdefault(event["event_id"], []).append(event)
        for event_id, deliveries in by_event_id.items():
            if len(deliveries) == 1:
                continue
            if len({event["sequence"] for event in deliveries}) != 1:
                fail(f"duplicate logical event changed sequence: {event_id}")
            normalized = [dict(event, delivery_index=0) for event in deliveries]
            if any(event != normalized[0] for event in normalized[1:]):
                fail(f"duplicate delivery changed logical event content: {event_id}")
    if terminal_hashes != {"4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892"}:
        fail(f"engine terminal hashes diverge: {sorted(terminal_hashes)}")

    software_paths = {
        "runner_sha256": ROOT / "game-track/godot/scripts/experimental_game_runner.gd",
        "machine_sha256": ROOT / "game-track/godot/scripts/sealed_lighthouse_machine.gd",
        "canonicalizer_sha256": ROOT / "game-track/godot/scripts/canonical_state.gd",
        "scenario_sha256": ROOT / "game-track/godot/data/sealed_lighthouse.json",
    }
    for run in manifest["runs"]:
        software = run["summary"]["software"]
        for field, path in software_paths.items():
            if hashlib.sha256(path.read_bytes()).hexdigest() != software[field]:
                fail(f"retained engine evidence is stale against current {field}: {path}")
        fixture_path = (
            ROOT
            / "data/fixtures"
            / f"experimental-game-{run['fixture_id'].removeprefix('sealed-lighthouse-').removesuffix('-v1')}.json"
        )
        if run["fixture_id"] == "sealed-lighthouse-canonical-v1":
            fixture_path = ROOT / "data/fixtures/experimental-game-canonical.json"
        if hashlib.sha256(fixture_path.read_bytes()).hexdigest() != software["fixture_sha256"]:
            fail(f"retained fixture hash is stale: {fixture_path}")


def main() -> int:
    check_single_workspace()
    check_rule_contract()
    check_design_pairs()
    check_experiment_config()
    check_claim_boundary()
    check_asset_manifest()
    check_engine_evidence()
    print("PASS: game-studio workspace, rules, bilingual design, dual tracks, and claim boundary")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
