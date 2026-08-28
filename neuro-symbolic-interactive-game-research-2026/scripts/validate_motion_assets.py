#!/usr/bin/env python3
"""Validate the motion/rig intake lane contract (D-039).

Fail-closed checks:
- no raw motion source files (.fbx/.dae/.bvh) are git-tracked anywhere under
  the motion lane (Adobe's Mixamo FAQ forbids redistributing raw files);
- every staged .glb carries an adjacent provenance JSON with the required
  fields and `runtime_eligible: false` unless a curation.json exists;
- provenance records an explicit license note and retrieval/creation date.

An empty lane (contract only, zero assets) passes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOTION_ROOT = ROOT / "game-track/assets/motion"
FORBIDDEN_TRACKED_SUFFIXES = {".fbx", ".dae", ".bvh"}
REQUIRED_PROVENANCE_FIELDS = {
    "asset_id",
    "source",
    "source_kind",
    "license_note",
    "no_redistribution_of_raw_source",
    "retrieved_or_created_utc",
    "processing",
    "blender_version",
    "sha256",
    "bytes",
    "runtime_eligible",
    "intended_track",
}


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", str(MOTION_ROOT.relative_to(ROOT.parent))],
        check=True,
        capture_output=True,
        text=True,
        cwd=ROOT.parent,
    )
    return [ROOT.parent / line for line in result.stdout.splitlines() if line]


def main() -> int:
    failures: list[str] = []
    if not (MOTION_ROOT / "README.md").is_file():
        failures.append("motion lane README.md is missing")

    tracked = _tracked_files()
    for path in tracked:
        if path.suffix.lower() in FORBIDDEN_TRACKED_SUFFIXES:
            failures.append(f"raw motion source must never be git-tracked: {path}")

    glb_files = sorted(MOTION_ROOT.rglob("*.glb"))
    for glb in glb_files:
        provenance_path = glb.with_suffix(".glb.provenance.json")
        if not provenance_path.is_file():
            failures.append(f"missing provenance for {glb}")
            continue
        try:
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            failures.append(f"invalid provenance JSON {provenance_path}: {error}")
            continue
        missing = sorted(REQUIRED_PROVENANCE_FIELDS - set(provenance))
        if missing:
            failures.append(f"provenance fields missing for {glb}: {missing}")
            continue
        digest = hashlib.sha256(glb.read_bytes()).hexdigest()
        if provenance["sha256"] != digest:
            failures.append(f"provenance sha256 drifted for {glb}")
        if provenance["bytes"] != glb.stat().st_size:
            failures.append(f"provenance byte count drifted for {glb}")
        if provenance["no_redistribution_of_raw_source"] is not True:
            failures.append(f"raw-source redistribution guard unacknowledged for {glb}")
        curated = (glb.parent / "curation.json").is_file()
        if provenance["runtime_eligible"] is True and not curated:
            failures.append(f"runtime_eligible without curation.json: {glb}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(f"PASS motion intake lane: {len(glb_files)} staged GLB assets, raw-source guard clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
