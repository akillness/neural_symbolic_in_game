#!/usr/bin/env python3
"""Run the latest Sealed Lighthouse playable engineering evaluation.

This runner deliberately produces engineering-conformance artifacts only. It
does not run participants or models, and its outputs are not evidence for G4,
usability, immersion, affect, or model/player efficacy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from scripts.png_contract import validate_render_png
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from png_contract import validate_render_png

ROOT = Path(__file__).resolve().parents[1]
GODOT_PROJECT = ROOT / "game-track/godot"
LATEST_DOCS = GODOT_PROJECT / "docs/latest"
FIXTURE_ROOT = ROOT / "data/fixtures"

MATRIX_ID = "SL-PLAY-EVAL-001"
EXACT_TERMINAL_HASH = "4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892"
FIXTURE_FILES = (
    "experimental-game-canonical.json",
    "experimental-game-duplicate-event.json",
    "experimental-game-timeout.json",
    "experimental-game-corrupt-save.json",
)
EXPECTED_FIXTURE_IDS = (
    "sealed-lighthouse-canonical-v1",
    "sealed-lighthouse-duplicate-event-v1",
    "sealed-lighthouse-timeout-v1",
    "sealed-lighthouse-corrupt-save-v1",
)
EXPECTED_FIXTURE_CHECKS = {
    "early_forbidden_state_isolation",
    "permitted_hint_after_authorization",
    "save_load_hash_match",
    "replay_hash_match",
    "expected_terminal_hash_match",
    "research_oracle_hash_match",
    "duplicate_idempotent",
    "timeout_state_isolation",
    "corrupt_save_state_isolation",
    "fixture_expectations_match",
}
EXPECTED_PRESENTATION_CHECKS = {
    "evaluation_does_not_mutate_canonical_state",
    "web_start_gate_is_visible_before_play",
    "audio_remains_locked_before_user_gesture",
    "procedural_audio_uses_no_external_assets",
    "semantic_feedback_has_non_color_redundancy",
    "responsive_layout_profiles_declared",
    "player_world_changes_route_through_proposals",
}
SCREENSHOT_STAGES = ("arrival", "refusal", "authorized_hint", "ending")
NOT_EVIDENCE_FOR = (
    "G4",
    "usability",
    "immersion",
    "affect",
    "model efficacy",
    "player efficacy",
)
ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
GODOT_ERROR = re.compile(r"(?:SCRIPT ERROR|ERROR):")
SHA256_HEX = re.compile(r"[0-9a-f]{64}")
SEMVER_PREFIX = re.compile(r"^(\d+\.\d+\.\d+)")


def _load_json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _godot_version_identity(version: str) -> tuple[str, bool, bool]:
    match = SEMVER_PREFIX.match(version)
    if match is None:
        raise ValueError(f"unrecognized Godot version string: {version}")
    lowered = version.lower()
    return match.group(1), "stable" in lowered, "official" in lowered


def find_godot_4(explicit: str | None = None) -> tuple[str, str]:
    """Find an executable Godot 4 editor and return its path and exact version."""
    candidates: list[str] = []
    if explicit:
        candidates.append(explicit)
    for command in ("godot4", "godot"):
        resolved = shutil.which(command)
        if resolved:
            candidates.append(resolved)
    candidates.extend(
        str(path)
        for path in (
            Path("/Applications/Godot.app/Contents/MacOS/Godot"),
            Path.home() / "Applications/Godot.app/Contents/MacOS/Godot",
        )
        if path.is_file()
    )
    attempted: list[str] = []
    for candidate in dict.fromkeys(candidates):
        attempted.append(candidate)
        try:
            probe = subprocess.run(
                [candidate, "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        version = probe.stdout.strip()
        if probe.returncode == 0 and version.startswith("4."):
            return candidate, version
    suffix = f"; attempted: {', '.join(attempted)}" if attempted else ""
    raise RuntimeError(f"Godot 4.x editor executable was not found{suffix}")


def _project_ignore(_directory: str, names: list[str]) -> set[str]:
    """Exclude caches and latest working docs from the disposable project copy."""
    ignored = {name for name in names if name in {".godot", ".omc", ".omx", "docs"}}
    ignored.update(name for name in names if name.endswith(".log"))
    return ignored


def stage_project(source: Path, destination: Path) -> None:
    """Create a cache-free disposable Godot project without mutating the source."""
    if destination.exists():
        raise FileExistsError(f"staged project already exists: {destination}")
    if not (source / "project.godot").is_file():
        raise FileNotFoundError(f"Godot project file is missing: {source / 'project.godot'}")
    shutil.copytree(source, destination, ignore=_project_ignore)


def _run_godot(
    command: list[str],
    *,
    label: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    log_output = ""
    if "--log-file" in command:
        log_index = command.index("--log-file")
        if log_index + 1 < len(command):
            log_path = Path(command[log_index + 1])
            if log_path.is_file():
                log_output = log_path.read_text(encoding="utf-8", errors="replace")
    output = ANSI_ESCAPE.sub("", result.stdout + result.stderr + log_output)
    if result.returncode != 0 or GODOT_ERROR.search(output):
        excerpt = output[-6000:]
        raise RuntimeError(f"{label} failed (exit={result.returncode}). Godot output:\n{excerpt}")
    return result


def _read_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {error}") from error
        if not isinstance(event, dict):
            raise TypeError(f"event must be an object at {path}:{line_number}")
        events.append(event)
    return events


def summarize_fixture_run(
    fixture: Mapping[str, Any],
    summary: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate one fresh authored run and retain only stable conformance facts."""
    fixture_id = str(fixture["fixture_id"])
    if summary.get("fixture_id") != fixture_id:
        raise ValueError(f"fixture/summary identity mismatch: {fixture_id}")
    if summary.get("execution_status") != "OBSERVED_ENGINE_RUN":
        raise ValueError(f"fixture did not report an observed engine run: {fixture_id}")

    engine = summary.get("engine")
    if (
        not isinstance(engine, Mapping)
        or engine.get("name") != "Godot"
        or not engine.get("headless")
    ):
        raise ValueError(f"fixture was not executed headlessly by Godot: {fixture_id}")

    checks = summary.get("checks")
    if not isinstance(checks, Mapping) or set(checks) != EXPECTED_FIXTURE_CHECKS:
        observed = sorted(checks) if isinstance(checks, Mapping) else []
        raise ValueError(f"unexpected fixture check set for {fixture_id}: {observed}")
    failed_checks = sorted(name for name, passed in checks.items() if passed is not True)
    if failed_checks:
        raise ValueError(f"failed fixture checks for {fixture_id}: {failed_checks}")

    expected = fixture.get("expected")
    counts = summary.get("counts")
    if not isinstance(expected, Mapping) or not isinstance(counts, Mapping):
        raise TypeError(f"fixture expected/count documents are missing: {fixture_id}")

    event_ids = [str(event.get("event_id")) for event in events]
    duplicate_deliveries = len(event_ids) - len(set(event_ids))
    committed_operations: list[str] = []
    seen_commit_ids: set[str] = set()
    for event in events:
        if event.get("event_type") != "commit" or not event.get("commit", {}).get("applied"):
            continue
        event_id = str(event["event_id"])
        if event_id in seen_commit_ids:
            continue
        seen_commit_ids.add(event_id)
        committed_operations.append(str(event["commit"]["operation"]))
    derived_counts = {
        "events": len(events),
        "commits": len(committed_operations),
        "fallbacks": sum(event.get("event_type") == "fallback" for event in events),
        "duplicate_events": duplicate_deliveries,
        "timeouts": sum(event.get("event_type") == "timeout" for event in events),
    }
    normalized_counts = {name: int(counts.get(name, -1)) for name in derived_counts}
    if normalized_counts != derived_counts:
        raise ValueError(
            f"summary/event count mismatch for {fixture_id}: "
            f"summary={normalized_counts}, derived={derived_counts}"
        )
    if committed_operations != list(expected["committed_operations"]):
        raise ValueError(f"committed operation mismatch for {fixture_id}")
    if derived_counts["duplicate_events"] != int(expected["duplicate_event_count"]):
        raise ValueError(f"duplicate count mismatch for {fixture_id}")
    if derived_counts["timeouts"] != int(expected["timeout_count"]):
        raise ValueError(f"timeout count mismatch for {fixture_id}")

    fallback_codes = sorted(
        {
            str(code)
            for event in events
            if event.get("event_type") == "fallback"
            for code in event.get("validation", {}).get("codes", [])
        }
    )
    if fallback_codes != sorted(str(code) for code in expected["fallback_codes"]):
        raise ValueError(f"fallback code mismatch for {fixture_id}: {fallback_codes}")

    terminal_hash = str(summary.get("terminal_state_hash"))
    if terminal_hash != str(expected["terminal_state_hash"]):
        raise ValueError(f"terminal hash mismatch for {fixture_id}: {terminal_hash}")
    if terminal_hash != str(expected["research_oracle_state_hash"]):
        raise ValueError(f"research-oracle hash mismatch for {fixture_id}: {terminal_hash}")
    if terminal_hash != EXACT_TERMINAL_HASH:
        raise ValueError(f"unexpected exact terminal hash for {fixture_id}: {terminal_hash}")

    isolation = {
        "early_forbidden": {
            "applicable": True,
            "passed": bool(checks["early_forbidden_state_isolation"]),
        },
        "timeout": {
            "applicable": fixture["fault_mode"] == "timeout",
            "passed": bool(checks["timeout_state_isolation"]),
        },
        "corrupt_save": {
            "applicable": fixture["fault_mode"] == "corrupt_save",
            "passed": bool(checks["corrupt_save_state_isolation"]),
        },
    }
    return {
        "fixture_id": fixture_id,
        "fault_mode": str(fixture["fault_mode"]),
        "engine_reported_version": str(engine["version"]),
        "passed": True,
        "terminal_state_sha256": terminal_hash,
        "committed_operations": committed_operations,
        "fallback_codes": fallback_codes,
        "counts": {
            "commits": derived_counts["commits"],
            "fallbacks": derived_counts["fallbacks"],
            "duplicate_events": derived_counts["duplicate_events"],
            "timeouts": derived_counts["timeouts"],
            "checks_passed": len(checks),
            "checks_total": len(checks),
        },
        "state_isolation": {
            **isolation,
            "all_required_passed": all(item["passed"] for item in isolation.values()),
        },
    }


def summarize_presentation(report: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and summarize the engine-local seven-check presentation report."""
    checks = report.get("checks")
    if not isinstance(checks, list):
        raise TypeError("presentation checks must be a list")
    check_by_name: dict[str, bool] = {}
    for item in checks:
        if not isinstance(item, Mapping) or not isinstance(item.get("check"), str):
            raise TypeError("presentation check entry is malformed")
        name = str(item["check"])
        if name in check_by_name:
            raise ValueError(f"duplicate presentation check: {name}")
        check_by_name[name] = item.get("pass") is True
    if set(check_by_name) != EXPECTED_PRESENTATION_CHECKS:
        raise ValueError(f"unexpected presentation check set: {sorted(check_by_name)}")
    failed = sorted(name for name, passed in check_by_name.items() if not passed)
    if failed or report.get("passed") is not True or report.get("engineering_only") is not True:
        raise ValueError(f"presentation evaluation failed: {failed}")
    before = str(report.get("state_sha256_before"))
    after = str(report.get("state_sha256_after"))
    if before != after:
        raise ValueError("presentation evaluation mutated canonical state")
    if tuple(report.get("supported_screenshot_stages", ())) != SCREENSHOT_STAGES:
        raise ValueError("presentation screenshot-stage contract drifted")
    return {
        "evaluation": str(report["evaluation"]),
        "engineering_only": True,
        "public_safe": True,
        "passed": True,
        "counts": {"checks_passed": len(checks), "checks_total": len(checks)},
        "check_ids": sorted(check_by_name),
        "state_isolation": {
            "state_sha256_before": before,
            "state_sha256_after": after,
            "unchanged": True,
        },
    }


def screenshot_receipts(directory: Path) -> list[dict[str, Any]]:
    """Validate the four latest working captures and return stable receipts."""
    receipts: list[dict[str, Any]] = []
    for stage in SCREENSHOT_STAGES:
        path = directory / f"{stage}.png"
        if not path.is_file():
            raise FileNotFoundError(
                f"latest screenshot is missing: {path}; rerun with --capture to regenerate"
            )
        stats = validate_render_png(path)
        receipts.append(
            {
                "stage": stage,
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "width": stats.width,
                "height": stats.height,
                "engineering_working_capture_only": True,
            }
        )
    return receipts


def build_matrix(
    *,
    godot_version: str,
    fixtures: Sequence[Mapping[str, Any]],
    presentation: Mapping[str, Any],
    screenshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the deterministic, claim-bounded evaluation matrix document."""
    if tuple(row.get("fixture_id") for row in fixtures) != EXPECTED_FIXTURE_IDS:
        raise ValueError("authored fixture order or identity drifted")
    probe_identity = _godot_version_identity(godot_version)
    if not godot_version.startswith("4.") or any(
        _godot_version_identity(str(row.get("engine_reported_version"))) != probe_identity
        for row in fixtures
    ):
        raise ValueError("Godot 4 version probe and fixture reports do not agree")
    if tuple(row.get("stage") for row in screenshots) != SCREENSHOT_STAGES:
        raise ValueError("working screenshot order or identity drifted")
    for screenshot in screenshots:
        if (
            screenshot.get("width") != 1280
            or screenshot.get("height") != 720
            or int(screenshot.get("bytes", 0)) <= 0
            or SHA256_HEX.fullmatch(str(screenshot.get("sha256", ""))) is None
            or screenshot.get("engineering_working_capture_only") is not True
        ):
            raise ValueError(f"invalid latest screenshot receipt: {screenshot.get('stage')}")
    if presentation.get("counts") != {"checks_passed": 7, "checks_total": 7}:
        raise ValueError("presentation result must remain exactly 7/7 for this matrix version")

    fixture_checks_passed = sum(int(row["counts"]["checks_passed"]) for row in fixtures)
    fixture_checks_total = sum(int(row["counts"]["checks_total"]) for row in fixtures)
    presentation_checks_passed = int(presentation["counts"]["checks_passed"])
    presentation_checks_total = int(presentation["counts"]["checks_total"])
    all_pass = (
        len(fixtures) == 4
        and all(row.get("passed") is True for row in fixtures)
        and presentation.get("passed") is True
        and len(screenshots) == 4
        and fixture_checks_passed == fixture_checks_total == 40
        and presentation_checks_passed == presentation_checks_total == 7
    )
    return {
        "schema_version": "1.0.0",
        "matrix_id": MATRIX_ID,
        "status": "PASS" if all_pass else "FAIL",
        "all_pass": all_pass,
        "scope": {
            "engineering_only": True,
            "claim_boundary": (
                "Fresh authored-fixture and presentation-invariant conformance only; no "
                "participant, neural-model, live research transport, usability, immersion, "
                "affect, or efficacy measurement."
            ),
            "not_evidence_for": list(NOT_EVIDENCE_FOR),
            "g4_status": "UNASSESSED",
        },
        "execution": {
            "engine": "Godot",
            "godot_version": godot_version,
            "fresh_temporary_project_import": True,
            "authored_fixture_runs_headless": True,
            "presentation_evaluation_headless": True,
            "presentation_mode": "public-safe procedural fallback",
            "immutable_evidence_modified": False,
        },
        "terminal_state": {
            "hash_algorithm": "sha256-canonical-json-v1",
            "exact_sha256": EXACT_TERMINAL_HASH,
            "all_four_fixtures_match": all(
                row["terminal_state_sha256"] == EXACT_TERMINAL_HASH for row in fixtures
            ),
        },
        "authored_fixtures": list(fixtures),
        "presentation": dict(presentation),
        "screenshots": list(screenshots),
        "totals": {
            "fixtures_passed": sum(row.get("passed") is True for row in fixtures),
            "fixtures_total": len(fixtures),
            "fixture_checks_passed": fixture_checks_passed,
            "fixture_checks_total": fixture_checks_total,
            "presentation_checks_passed": presentation_checks_passed,
            "presentation_checks_total": presentation_checks_total,
            "combined_checks_passed": fixture_checks_passed + presentation_checks_passed,
            "combined_checks_total": fixture_checks_total + presentation_checks_total,
            "screenshots_valid": len(screenshots),
            "screenshots_total": len(SCREENSHOT_STAGES),
        },
    }


def render_markdown(matrix: Mapping[str, Any]) -> str:
    """Render a stable, repository-friendly Markdown view of the matrix."""
    totals = matrix["totals"]
    lines = [
        "# Sealed Lighthouse — Playable Engineering Evaluation Matrix",
        "",
        f"Table ID: `{matrix['matrix_id']}` · Status: **{matrix['status']}**",
        "",
        (
            "> Scope: fresh authored-fixture and presentation-invariant conformance only. "
            "This is **not** G4, usability, immersion, affect, model-efficacy, or "
            "player-efficacy evidence. G4 remains `UNASSESSED`."
        ),
        "",
        f"- Godot: `{matrix['execution']['godot_version']}`",
        (
            "- Execution: fresh temporary project import; headless fixtures; "
            "public-safe procedural presentation evaluation"
        ),
        f"- Exact terminal state SHA-256: `{matrix['terminal_state']['exact_sha256']}`",
        (
            f"- Authored fixture checks: `{totals['fixture_checks_passed']}/"
            f"{totals['fixture_checks_total']}`"
        ),
        (
            f"- Presentation checks: `{totals['presentation_checks_passed']}/"
            f"{totals['presentation_checks_total']}`"
        ),
        (
            f"- Combined checks: `{totals['combined_checks_passed']}/"
            f"{totals['combined_checks_total']}`"
        ),
        "- Immutable research evidence: not modified",
        "",
        "## Authored fixture matrix",
        "",
        (
            "| Fixture | Fault mode | Commits | Fallbacks | Duplicates | Timeouts | "
            "Checks | State isolation | Result |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in matrix["authored_fixtures"]:
        counts = row["counts"]
        lines.append(
            f"| `{row['fixture_id']}` | `{row['fault_mode']}` | {counts['commits']} | "
            f"{counts['fallbacks']} | {counts['duplicate_events']} | {counts['timeouts']} | "
            f"{counts['checks_passed']}/{counts['checks_total']} | "
            f"{'PASS' if row['state_isolation']['all_required_passed'] else 'FAIL'} | "
            f"{'PASS' if row['passed'] else 'FAIL'} |"
        )

    presentation = matrix["presentation"]
    lines.extend(
        [
            "",
            "## Presentation instrumentation",
            "",
            "| Surface | Mode | Checks | Canonical state | Result |",
            "| --- | --- | ---: | --- | --- |",
            (
                f"| `{presentation['evaluation']}` | public-safe procedural | "
                f"{presentation['counts']['checks_passed']}/"
                f"{presentation['counts']['checks_total']} | unchanged | "
                f"{'PASS' if presentation['passed'] else 'FAIL'} |"
            ),
            "",
            (
                "These seven checks cover start-gate visibility, gesture-gated procedural "
                "audio, non-color semantic redundancy, responsive profile declaration, "
                "proposal routing, and evaluation-state isolation. They do not measure "
                "player experience."
            ),
            "",
            "## Latest public-safe working captures",
            "",
            "| Stage | Image | Dimensions | SHA-256 | Classification |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for shot in matrix["screenshots"]:
        lines.append(
            f"| `{shot['stage']}` | [{shot['file']}]({shot['file']}) | "
            f"{shot['width']}×{shot['height']} | `{shot['sha256']}` | "
            "engineering working capture only |"
        )
    lines.extend(
        [
            "",
            (
                "Generated by `scripts/run_playable_evaluation.py` from a fresh disposable "
                "project copy. No retained immutable evidence packet is overwritten."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def atomic_write(path: Path, payload: bytes) -> None:
    """Replace one latest-facing artifact atomically on the same filesystem."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(payload)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_outputs(output_dir: Path, matrix: Mapping[str, Any]) -> None:
    json_payload = (json.dumps(matrix, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    atomic_write(output_dir / "evaluation-matrix.json", json_payload)
    atomic_write(output_dir / "evaluation-matrix.md", render_markdown(matrix).encode("utf-8"))


def _copy_capture_set(source: Path, output_dir: Path) -> None:
    for stage in SCREENSHOT_STAGES:
        source_path = source / f"{stage}.png"
        validate_render_png(source_path)
    for stage in SCREENSHOT_STAGES:
        source_path = source / f"{stage}.png"
        atomic_write(output_dir / source_path.name, source_path.read_bytes())


def _capture_screenshots(godot: str, project: Path, output: Path, logs: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for stage in SCREENSHOT_STAGES:
        shot_path = output / f"{stage}.png"
        _run_godot(
            [
                godot,
                "--path",
                str(project),
                "--scene",
                "res://scenes/main_3d.tscn",
                "--windowed",
                "--resolution",
                "1280x720",
                "--single-window",
                "--audio-driver",
                "Dummy",
                "--rendering-method",
                "gl_compatibility",
                "--rendering-driver",
                "opengl3",
                "--fixed-fps",
                "30",
                "--disable-vsync",
                "--quit-after",
                "300",
                "--log-file",
                str(logs / f"capture-{stage}.log"),
                "--",
                "--shot",
                str(shot_path),
                "--shot-stage",
                stage,
                "--public-safe",
            ],
            label=f"public-safe screenshot capture ({stage})",
            timeout=60,
        )
        validate_render_png(shot_path)


def run_evaluation(
    *,
    godot: str,
    godot_version: str,
    output_dir: Path,
    capture: bool,
) -> dict[str, Any]:
    """Execute a fresh disposable run and return the validated stable matrix."""
    with tempfile.TemporaryDirectory(prefix="sealed-lighthouse-play-eval-") as directory:
        working = Path(directory)
        project = working / "project"
        fixtures_dir = working / "fixtures"
        fixture_outputs = working / "fixture-outputs"
        logs = working / "logs"
        presentation_path = working / "presentation-evaluation.json"
        captures = working / "captures"
        fixtures_dir.mkdir()
        fixture_outputs.mkdir()
        logs.mkdir()
        stage_project(GODOT_PROJECT, project)
        for filename in FIXTURE_FILES:
            shutil.copy2(FIXTURE_ROOT / filename, fixtures_dir / filename)

        _run_godot(
            [
                godot,
                "--headless",
                "--editor",
                "--path",
                str(project),
                "--import",
                "--quit-after",
                "120",
                "--log-file",
                str(logs / "import.log"),
            ],
            label="fresh Godot project import",
            timeout=120,
        )

        fixture_rows: list[dict[str, Any]] = []
        for filename in FIXTURE_FILES:
            fixture_path = fixtures_dir / filename
            fixture = _load_json_object(fixture_path)
            output = fixture_outputs / str(fixture["fixture_id"])
            output.mkdir()
            _run_godot(
                [
                    godot,
                    "--headless",
                    "--path",
                    str(project),
                    "--quit-after",
                    "120",
                    "--log-file",
                    str(logs / f"{fixture['fixture_id']}.log"),
                    "--",
                    f"--fixture={fixture_path}",
                    f"--output={output}",
                ],
                label=f"authored fixture {fixture['fixture_id']}",
                timeout=60,
            )
            summary = _load_json_object(output / "summary.json")
            events = _read_events(output / "events.jsonl")
            fixture_rows.append(summarize_fixture_run(fixture, summary, events))

        _run_godot(
            [
                godot,
                "--headless",
                "--path",
                str(project),
                "--scene",
                "res://scenes/main_3d.tscn",
                "--rendering-method",
                "gl_compatibility",
                "--rendering-driver",
                "opengl3",
                "--quit-after",
                "120",
                "--log-file",
                str(logs / "presentation-evaluation.log"),
                "--",
                "--evaluate",
                str(presentation_path),
                "--public-safe",
            ],
            label="public-safe presentation engineering evaluation",
            timeout=60,
        )
        presentation_report = _load_json_object(presentation_path)
        presentation = summarize_presentation(presentation_report)

        if capture:
            _capture_screenshots(godot, project, captures, logs)
            _copy_capture_set(captures, output_dir)
        screenshots = screenshot_receipts(output_dir)
        matrix = build_matrix(
            godot_version=godot_version,
            fixtures=fixture_rows,
            presentation=presentation,
            screenshots=screenshots,
        )
        if not matrix["all_pass"]:
            raise RuntimeError("playable engineering evaluation did not pass")
        atomic_write(
            output_dir / "presentation-evaluation.json",
            (
                json.dumps(presentation_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            ).encode("utf-8"),
        )
        write_outputs(output_dir, matrix)
        return matrix


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run fresh authored Godot fixtures and the public-safe presentation "
            "engineering evaluation, then write the latest stable matrix."
        )
    )
    parser.add_argument("--godot", help="Explicit Godot 4 editor executable")
    parser.add_argument(
        "--capture",
        action="store_true",
        help="Regenerate all four non-headless 1280x720 public-safe working screenshots.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    godot, version = find_godot_4(args.godot)
    matrix = run_evaluation(
        godot=godot,
        godot_version=version,
        output_dir=LATEST_DOCS,
        capture=args.capture,
    )
    totals = matrix["totals"]
    print(
        f"{matrix['matrix_id']} PASS: fixtures "
        f"{totals['fixtures_passed']}/{totals['fixtures_total']}, checks "
        f"{totals['combined_checks_passed']}/{totals['combined_checks_total']}, "
        f"screenshots {totals['screenshots_valid']}/{totals['screenshots_total']}; "
        f"Godot {version}; output={LATEST_DOCS}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
