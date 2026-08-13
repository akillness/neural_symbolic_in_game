#!/usr/bin/env python3
"""Run three Godot fixtures into a new, immutable evidence-set directory."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator

try:
    from scripts.png_contract import validate_render_png
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from png_contract import validate_render_png

ROOT = Path(__file__).resolve().parents[1]
GODOT_PROJECT = ROOT / "game-track/godot"
SCHEMA_ROOT = ROOT / "game-track/schemas"
TECH_VERIFICATION = ROOT / "_workspace/current/engineering/tech-verification"
EVIDENCE_PARENT = TECH_VERIFICATION / "evidence"
STAGING_PARENT = TECH_VERIFICATION / "staging"
CURRENT_POINTER = TECH_VERIFICATION / "current.json"
SAFE_COMPONENT_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{2,127}")
FIXTURES = (
    ROOT / "data/fixtures/experimental-game-canonical.json",
    ROOT / "data/fixtures/experimental-game-duplicate-event.json",
    ROOT / "data/fixtures/experimental-game-timeout.json",
    ROOT / "data/fixtures/experimental-game-corrupt-save.json",
)
CANONICAL_FIXTURE_ID = "sealed-lighthouse-canonical-v1"
RENDER_ROOT_NAME = "rendered-canonical-v1"
RENDER_FILES = (
    "sl-rc-001-arrival.png",
    "sl-rc-002-rejected-secret.png",
    "sl-rc-003-authorized-hint.png",
)


def digest(path: Path) -> dict[str, int | str]:
    return {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def prepare_capture_paths(
    evidence_set_id: str,
    *,
    evidence_parent: Path = EVIDENCE_PARENT,
    staging_parent: Path = STAGING_PARENT,
) -> tuple[Path, Path]:
    """Reserve a unique staging path without touching a retained evidence set."""
    if SAFE_COMPONENT_PATTERN.fullmatch(evidence_set_id) is None:
        raise ValueError(
            "evidence-set ID must be 3-128 lowercase letters, digits, dots, underscores, or hyphens"
        )
    evidence_parent.mkdir(parents=True, exist_ok=True)
    staging_parent.mkdir(parents=True, exist_ok=True)
    target = evidence_parent / evidence_set_id
    staging = staging_parent / evidence_set_id
    if target.resolve().parent != evidence_parent.resolve():
        raise ValueError(f"evidence target escaped retained root: {evidence_set_id!r}")
    if staging.resolve().parent != staging_parent.resolve():
        raise ValueError(f"staging target escaped staging root: {evidence_set_id!r}")
    if target.exists():
        raise FileExistsError(f"retained evidence set already exists and is immutable: {target}")
    staging.mkdir(exist_ok=False)
    return staging, target


def fixture_output_path(staging_root: Path, fixture_id: str, seen: set[str]) -> Path:
    """Resolve one safe, unique fixture directory directly below the staging root."""
    if SAFE_COMPONENT_PATTERN.fullmatch(fixture_id) is None:
        raise ValueError(f"unsafe fixture_id: {fixture_id!r}")
    if fixture_id in seen:
        raise ValueError(f"duplicate fixture_id: {fixture_id}")
    seen.add(fixture_id)
    output = staging_root / fixture_id
    if output.resolve().parent != staging_root.resolve():
        raise ValueError(f"fixture output escaped staging: {fixture_id!r}")
    output.mkdir(parents=False, exist_ok=False)
    return output


def load_validator(filename: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_ROOT / filename).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def enrich_and_validate_render_capture(staging_root: Path, evidence_set_id: str) -> dict:
    """Validate PNG bytes and bind computed pixel statistics before packet promotion."""
    render_root = staging_root / RENDER_ROOT_NAME
    manifest_path = render_root / "capture-manifest.json"
    render_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if render_manifest.get("evidence_set_id") != evidence_set_id:
        raise ValueError("render capture evidence-set ID mismatch")
    observed_files = {row["file"] for row in render_manifest.get("captures", [])}
    if observed_files != set(RENDER_FILES):
        raise ValueError(f"unexpected render capture file set: {sorted(observed_files)}")
    canonical_root = staging_root / CANONICAL_FIXTURE_ID
    events_path = canonical_root / "events.jsonl"
    summary_path = canonical_root / "summary.json"
    if render_manifest["source"]["events_sha256"] != digest(events_path)["sha256"]:
        raise ValueError("render capture source events hash mismatch")
    if render_manifest["source"]["summary_sha256"] != digest(summary_path)["sha256"]:
        raise ValueError("render capture source summary hash mismatch")
    canonical_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    for field in ("fixture_id", "scenario_id", "run_id", "episode_id", "seed"):
        if render_manifest[field] != canonical_summary[field]:
            raise ValueError(f"render capture summary identity mismatch: {field}")
    event_by_id = {
        event["event_id"]: event
        for event in (
            json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()
        )
    }
    expected_captures = {
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
    if {row["capture_id"] for row in render_manifest["captures"]} != set(expected_captures):
        raise ValueError("unexpected render capture IDs")
    for row in render_manifest["captures"]:
        for field, value in expected_captures[row["capture_id"]].items():
            if row[field] != value:
                raise ValueError(f"render capture {field} binding mismatch: {row['capture_id']}")
        event = event_by_id[row["event_id"]]
        for field in (
            "sequence",
            "delivery_index",
            "turn",
            "world_state_hash_before",
            "world_state_hash",
        ):
            if row[field] != event[field]:
                raise ValueError(f"render capture {field} mismatch: {row['capture_id']}")
        if row["validation_status"] != event["validation"]["status"]:
            raise ValueError(f"render validation status mismatch: {row['capture_id']}")
        if row["validation_codes"] != event["validation"]["codes"]:
            raise ValueError(f"render validation codes mismatch: {row['capture_id']}")
        if (
            row["capture_id"] == "sl-rc-002-rejected-secret"
            and row["world_state_hash_before"] != row["world_state_hash"]
        ):
            raise ValueError("rejected disclosure render does not bind an unchanged state")
        if row["capture_id"] == "sl-rc-003-authorized-hint" and (
            not event["commit"]["applied"] or event["commit"]["operation"] != "reveal_hint"
        ):
            raise ValueError("authorized-hint render does not bind a committed reveal_hint")
        image_path = render_root / row["file"]
        if digest(image_path) != {"bytes": row["bytes"], "sha256": row["sha256"]}:
            raise ValueError(f"render capture hash/size mismatch: {image_path}")
        row["pixel_stats"] = validate_render_png(image_path).to_jsonable()
    render_manifest["source"].update(
        {
            "capture_pipeline_sha256": digest(Path(__file__))["sha256"],
            "png_contract_sha256": digest(ROOT / "scripts/png_contract.py")["sha256"],
            "capture_schema_sha256": digest(
                SCHEMA_ROOT / "experimental-game-render-capture.schema.json"
            )["sha256"],
            "retained_validator_sha256": digest(ROOT / "scripts/validate_game_studio.py")["sha256"],
            "uv_lock_sha256": digest(ROOT / "uv.lock")["sha256"],
        }
    )
    render_manifest["validation_toolchain"] = {
        "python_version": platform.python_version(),
        "jsonschema_version": importlib.metadata.version("jsonschema"),
        "json_schema_draft": "2020-12",
        "png_decoder": "stdlib-zlib-filter-reconstruction-v1",
    }
    manifest_path.write_text(
        json.dumps(render_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    load_validator("experimental-game-render-capture.schema.json").validate(render_manifest)
    return render_manifest


def validate_staging_capture(
    staging_root: Path, runs: list[dict], render_capture: dict | None = None
) -> None:
    """Reject an incomplete or schema-invalid evidence set before promotion."""
    event_validator = load_validator("experimental-game-event.schema.json")
    save_validator = load_validator("experimental-game-save.schema.json")
    summary_validator = load_validator("experimental-game-summary.schema.json")
    expected_files = {"evidence-manifest.json"}
    for run in runs:
        fixture_id = run["fixture_id"]
        run_root = staging_root / fixture_id
        expected_files.update(
            {
                f"{fixture_id}/events.jsonl",
                f"{fixture_id}/save.json",
                f"{fixture_id}/summary.json",
            }
        )
        summary = json.loads((run_root / "summary.json").read_text(encoding="utf-8"))
        save = json.loads((run_root / "save.json").read_text(encoding="utf-8"))
        summary_validator.validate(summary)
        save_validator.validate(save)
        if summary != run["summary"]:
            raise ValueError(f"manifest summary mismatch: {fixture_id}")
        if not all(summary["checks"].values()):
            raise ValueError(f"failed Godot checks: {fixture_id}")
        for delivery_index, line in enumerate(
            (run_root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ):
            event = json.loads(line)
            event_validator.validate(event)
            if event["delivery_index"] != delivery_index:
                raise ValueError(f"non-contiguous delivery order: {fixture_id}")
        for filename, receipt in run["files"].items():
            if digest(run_root / filename) != receipt:
                raise ValueError(f"staging hash/size mismatch: {fixture_id}/{filename}")
    if render_capture is not None:
        load_validator("experimental-game-render-capture.schema.json").validate(render_capture)
        expected_files.add(f"{RENDER_ROOT_NAME}/capture-manifest.json")
        for capture in render_capture["captures"]:
            image_path = staging_root / RENDER_ROOT_NAME / capture["file"]
            if digest(image_path) != {
                "bytes": capture["bytes"],
                "sha256": capture["sha256"],
            }:
                raise ValueError(f"render capture receipt mismatch: {image_path}")
            validate_render_png(image_path)
            expected_files.add(f"{RENDER_ROOT_NAME}/{capture['file']}")
    actual_files = {
        path.relative_to(staging_root).as_posix()
        for path in staging_root.rglob("*")
        if path.is_file()
    }
    if actual_files != expected_files:
        raise ValueError(
            "staging evidence file set mismatch: "
            f"missing={sorted(expected_files - actual_files)}, "
            f"unexpected={sorted(actual_files - expected_files)}"
        )


def promote_capture(staging: Path, target: Path) -> None:
    """Reserve a target without replacement and move the completion manifest last."""
    manifest = staging / "evidence-manifest.json"
    if not manifest.is_file():
        raise FileNotFoundError(f"capture manifest is missing: {manifest}")
    target.mkdir(parents=False, exist_ok=False)
    children = sorted(path for path in staging.iterdir() if path.name != manifest.name)
    for child in children:
        child.rename(target / child.name)
    manifest.rename(target / manifest.name)
    staging.rmdir()


def write_current_pointer(evidence_set_id: str, manifest_path: Path) -> None:
    """Atomically select one already-promoted immutable set for project validation."""
    pointer = {
        "schema_version": "1.0.0",
        "evidence_set_id": evidence_set_id,
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    temporary = CURRENT_POINTER.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(CURRENT_POINTER)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture Godot evidence into a new fail-closed evidence set."
    )
    parser.add_argument(
        "--evidence-set-id",
        required=True,
        help=(
            "Unique immutable set ID, for example godot-4.7.1-20260813t210000z-sealed-lighthouse-v1"
        ),
    )
    parser.add_argument(
        "--with-render-captures",
        action="store_true",
        help="Replay the canonical trace in a non-headless 1280x720 capture scene.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    godot = shutil.which("godot4") or shutil.which("godot")
    if godot is None:
        raise SystemExit("Godot 4.x is required to capture engine evidence")
    version = subprocess.run(
        [godot, "--version"], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    staging_root, evidence_root = prepare_capture_paths(args.evidence_set_id)
    try:
        runs = []
        seen_fixture_ids: set[str] = set()
        fixture_validator = load_validator("experimental-game-fixture.schema.json")
        for fixture_path in FIXTURES:
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            fixture_validator.validate(fixture)
            output = fixture_output_path(staging_root, fixture["fixture_id"], seen_fixture_ids)
            subprocess.run(
                [
                    godot,
                    "--headless",
                    "--path",
                    str(GODOT_PROJECT),
                    "--quit-after",
                    "120",
                    "--",
                    f"--fixture={fixture_path}",
                    f"--output={output}",
                ],
                check=True,
                timeout=30,
            )
            files = {
                name: digest(output / name)
                for name in ("events.jsonl", "save.json", "summary.json")
            }
            runs.append(
                {
                    "fixture_id": fixture["fixture_id"],
                    "summary": json.loads((output / "summary.json").read_text(encoding="utf-8")),
                    "files": files,
                }
            )
        render_capture = None
        render_command_template = None
        if args.with_render_captures:
            canonical_root = staging_root / CANONICAL_FIXTURE_ID
            render_root = fixture_output_path(staging_root, RENDER_ROOT_NAME, seen_fixture_ids)
            render_command = [
                godot,
                "--path",
                str(GODOT_PROJECT),
                "--scene",
                "res://scenes/evidence_capture.tscn",
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
                "--",
                f"--events={canonical_root / 'events.jsonl'}",
                f"--summary={canonical_root / 'summary.json'}",
                f"--output={render_root}",
                f"--evidence-set-id={args.evidence_set_id}",
            ]
            subprocess.run(render_command, check=True, timeout=45)
            render_capture = enrich_and_validate_render_capture(staging_root, args.evidence_set_id)
            render_command_template = (
                "godot --path game-track/godot --scene res://scenes/evidence_capture.tscn "
                "--windowed --resolution 1280x720 --single-window --audio-driver Dummy "
                "--rendering-method gl_compatibility --rendering-driver opengl3 "
                "--fixed-fps 30 --disable-vsync --quit-after 300 -- "
                "--events=<canonical-events.jsonl> --summary=<canonical-summary.json> "
                "--output=<render-capture-path> --evidence-set-id=<evidence-set-id>"
            )
        manifest = {
            "schema_version": "1.0.0",
            "status": "OBSERVED_ENGINE_RUNS",
            "evidence_set_id": args.evidence_set_id,
            "engine_version": version,
            "platform": platform.platform(),
            "command_template": (
                "godot --headless --path game-track/godot --quit-after 120 -- "
                "--fixture=<absolute fixture path> --output=<evidence path>"
            ),
            "runs": runs,
            "render_capture": render_capture,
            "render_command_template": render_command_template,
        }
        (staging_root / "evidence-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        validate_staging_capture(staging_root, runs, render_capture)
        promote_capture(staging_root, evidence_root)
        write_current_pointer(args.evidence_set_id, evidence_root / "evidence-manifest.json")
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise
    print(
        f"Captured {len(runs)} Godot evidence runs and "
        f"{len(render_capture['captures']) if render_capture else 0} rendered views "
        f"with {version} at {evidence_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
