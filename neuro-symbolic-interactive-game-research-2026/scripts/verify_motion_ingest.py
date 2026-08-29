#!/usr/bin/env python3
"""Verify that a locally held rig/motion source imports into Godot (D-039/D-045).

Why this exists: the motion lane deliberately does not track character or
animation bytes (Adobe's Mixamo terms forbid redistributing raw character and
animation files, and this is a public repository). So the *asset* cannot be
committed, but the *ingestion recipe* can be, and this script is that recipe in
runnable form. Point it at a file you downloaded yourself and it reports what
Godot actually built from it.

It also records the measured shape of that import so the motion lane can carry
provenance metadata without carrying the bytes.

Boundary: this is engineering conformance for the asset pipeline. It is not
research evidence, it does not touch canonical game state, and it never copies
the source into a tracked path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW = ROOT / "game-track/assets/motion/raw"
SUPPORTED_SUFFIXES = {".fbx", ".dae", ".glb", ".gltf"}

PROBE_GD = """extends SceneTree

func _init() -> void:
\tvar res := load("res://source__SUFFIX__")
\tif res == null:
\t\tprint("PROBE " + JSON.stringify({"imported": false}))
\t\tquit(1)
\t\treturn
\tvar scene: Node = res.instantiate()
\tvar skeletons: Array = []
\tvar players: Array = []
\tvar meshes := 0
\tvar stack: Array = [scene]
\twhile not stack.is_empty():
\t\tvar n: Node = stack.pop_back()
\t\tif n is Skeleton3D:
\t\t\tskeletons.append({"name": n.name, "bones": n.get_bone_count()})
\t\tif n is AnimationPlayer:
\t\t\tplayers.append({"name": n.name, "animations": n.get_animation_list()})
\t\tif n is MeshInstance3D:
\t\t\tmeshes += 1
\t\tfor c in n.get_children():
\t\t\tstack.append(c)
\tprint("PROBE " + JSON.stringify({
\t\t"imported": true,
\t\t"root_class": scene.get_class(),
\t\t"skeletons": skeletons,
\t\t"animation_players": players,
\t\t"mesh_instances": meshes,
\t}))
\tquit(0)
"""

PROJECT_GODOT = """config_version=5

[application]
config/name="motion-ingest-probe"

[rendering]
renderer/rendering_method="gl_compatibility"
"""


def find_godot(explicit: str | None) -> str:
    candidates = [explicit] if explicit else []
    for command in ("godot4", "godot"):
        found = shutil.which(command)
        if found:
            candidates.append(found)
    candidates.append("/Applications/Godot.app/Contents/MacOS/Godot")
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise SystemExit("Godot 4 executable not found; pass --godot")


def probe(source: Path, godot: str, timeout: int = 300) -> dict[str, Any]:
    """Import one source in a disposable project and report the built scene."""
    with tempfile.TemporaryDirectory(prefix="motion-ingest-") as directory:
        project = Path(directory)
        (project / "project.godot").write_text(PROJECT_GODOT, encoding="utf-8")
        staged = project / f"source{source.suffix.lower()}"
        shutil.copy2(source, staged)
        (project / "probe.gd").write_text(
            PROBE_GD.replace("__SUFFIX__", source.suffix.lower()), encoding="utf-8"
        )
        subprocess.run(
            [godot, "--headless", "--path", str(project), "--import", "--quit-after", "300"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        result = subprocess.run(
            [godot, "--headless", "--path", str(project), "--script", "res://probe.gd"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    for line in (result.stdout + result.stderr).splitlines():
        if line.startswith("PROBE "):
            return json.loads(line[len("PROBE ") :])
    raise SystemExit(f"probe produced no verdict; Godot output:\n{result.stdout[-2000:]}")


def describe(source: Path, report: dict[str, Any]) -> dict[str, Any]:
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    skeletons = report.get("skeletons", [])
    players = report.get("animation_players", [])
    return {
        "schema_version": "1.0.0",
        "source_file_name": source.name,
        "source_bytes": source.stat().st_size,
        "source_sha256": digest,
        "bytes_tracked_in_git": False,
        "why_not_tracked": (
            "Mixamo terms forbid redistributing raw character and animation files; this "
            "repository is public, so the lane records provenance and the ingestion recipe "
            "instead of the asset bytes."
        ),
        "godot_import": {
            "native_importer": True,
            "blender_required": False,
            "imported": bool(report.get("imported")),
            "root_class": report.get("root_class"),
            "skeleton_count": len(skeletons),
            "bone_counts": [item.get("bones") for item in skeletons],
            "animation_players": [item.get("animations") for item in players],
            "mesh_instances": report.get("mesh_instances"),
        },
        "claim_boundary": (
            "Asset-pipeline engineering conformance only. Not research evidence, not a "
            "runtime promotion, and not a rights clearance."
        ),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        help="Rig/motion file to probe; defaults to the first supported file in raw/",
    )
    parser.add_argument("--godot", help="Explicit Godot 4 executable")
    parser.add_argument("--write", type=Path, help="Write the description JSON to this path")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    source = args.source
    if source is None:
        candidates = sorted(
            path
            for path in DEFAULT_RAW.glob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        )
        if not candidates:
            print(
                "No rig/motion source found. Download one yourself into "
                f"{DEFAULT_RAW.relative_to(ROOT)} (kept out of git) and re-run.",
                file=sys.stderr,
            )
            return 2
        source = candidates[0]
    if not source.is_file():
        print(f"source not found: {source}", file=sys.stderr)
        return 2

    report = probe(source, find_godot(args.godot))
    description = describe(source, report)
    payload = json.dumps(description, ensure_ascii=False, indent=2, sort_keys=True)
    if args.write:
        args.write.parent.mkdir(parents=True, exist_ok=True)
        args.write.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    godot_import = description["godot_import"]
    ok = (
        godot_import["imported"]
        and godot_import["skeleton_count"] >= 1
        and any(godot_import["animation_players"])
    )
    print(
        f"\nVERDICT: {'PASS' if ok else 'FAIL'} — skeletons={godot_import['skeleton_count']}, "
        f"bones={godot_import['bone_counts']}, meshes={godot_import['mesh_instances']}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
