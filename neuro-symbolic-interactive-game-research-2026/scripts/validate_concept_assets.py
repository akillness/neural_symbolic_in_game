#!/usr/bin/env python3
"""Validate the frozen Sealed Lighthouse concept pack without image dependencies."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "game-track" / "assets" / "concepts"
MANIFEST_PATH = ASSET_ROOT / "asset-manifest.json"


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError(f"not a canonical PNG header: {path}")
    return struct.unpack(">II", header[16:24])


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest.get("runtime_generation") is not False:
        raise ValueError("concept pack must prohibit runtime generation")
    if manifest.get("primary_experiment_eligible") is not False:
        raise ValueError("concept pack must be excluded from the primary experiment")

    ids: set[str] = set()
    for row in manifest.get("assets", []):
        asset_id = row["asset_id"]
        if asset_id in ids:
            raise ValueError(f"duplicate asset id: {asset_id}")
        ids.add(asset_id)
        image_path = ASSET_ROOT / row["file"]
        provenance_path = ASSET_ROOT / row["provenance"]
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        width, height = png_dimensions(image_path)
        expected = {
            "asset_id": asset_id,
            "file": row["file"],
            "observed_width": width,
            "observed_height": height,
            "bytes": image_path.stat().st_size,
            "sha256": sha256(image_path),
            "runtime_eligible": False,
            "primary_experiment_eligible": False,
            "ai_generated_content": True,
        }
        for key, value in expected.items():
            if provenance.get(key) != value:
                raise ValueError(
                    f"{asset_id} {key}: expected {value!r}, got {provenance.get(key)!r}"
                )
        prompt_path = ASSET_ROOT / provenance["prompt_file"]
        if not prompt_path.read_text(encoding="utf-8").strip():
            raise ValueError(f"empty prompt: {prompt_path}")
        if provenance.get("prompt_sha256") != sha256(prompt_path):
            raise ValueError(f"prompt hash mismatch: {asset_id}")
        if provenance.get("tool") != "god-tibo-imagen" or provenance.get("tool_version") != "0.3.0":
            raise ValueError(f"unexpected generator identity: {asset_id}")
        if (
            provenance.get("provider") != "private-codex"
            or provenance.get("model_requested") != "gpt-5.4"
        ):
            raise ValueError(f"unexpected provider/model: {asset_id}")
        if not provenance.get("response_id") or not provenance.get("generation_session_id"):
            raise ValueError(f"missing response/session provenance: {asset_id}")
        if provenance.get("intended_track") != ["design", "secondary-vlm-ui"]:
            raise ValueError(f"unexpected intended track: {asset_id}")
        if not str(provenance.get("curation_state", "")).startswith("accepted-concept-"):
            raise ValueError(f"asset not curated as a concept: {asset_id}")
        if not provenance.get("limitations"):
            raise ValueError(f"missing limitations: {asset_id}")
        for reference in provenance.get("reference_inputs", []):
            reference_path = ASSET_ROOT / reference["file"]
            if sha256(reference_path) != reference["sha256"]:
                raise ValueError(f"reference hash mismatch: {asset_id} -> {reference_path}")
        if provenance.get("rights_review") != "pending-human-publication-review":
            raise ValueError(f"unexpected rights state: {asset_id}")
        print(f"PASS {asset_id} {width}x{height} {expected['sha256'][:12]}")

    if ids != {"SL-C01", "SL-C02", "SL-C03", "SL-C04"}:
        raise ValueError(f"unexpected concept asset set: {sorted(ids)}")
    print(f"Concept asset pack valid: {len(ids)} assets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
