"""Validate the curated public-runtime player GLB and its provenance.

The validator is deliberately stdlib-only and fail-closed. It verifies bytes,
rights/curation gates, mesh and skin structure, required locomotion clips, the
measured triangle count, opaque double-sided material settings, and the
post-processed root-bone scale channels.
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAYER_ROOT = ROOT / "game-track/godot/assets/player"
GLB_PATH = PLAYER_ROOT / "higgsfield-player.glb"
TEXTURE_PATH = PLAYER_ROOT / "higgsfield-player_texture_0.png"
PROVENANCE_PATH = PLAYER_ROOT / "higgsfield-player.glb.provenance.json"
CURATION_PATH = PLAYER_ROOT / "curation.json"
REQUIRED_CLIPS = {"Idle", "Casual_Walk"}
EXPECTED_RIGHTS_REVIEW = "accepted-public-runtime-higgsfield-workspace-commercial-use"
REQUIRED_RIGHTS_SOURCE = "https://higgsfield.ai/terms-of-use-agreement"
GLB_MAGIC = 0x46546C67
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
FLOAT_COMPONENT = 5126
ROOT_SCALE_TOLERANCE = 0.02
REQUIRED_PROVENANCE_FIELDS = {
    "schema_version",
    "asset_id",
    "asset_class",
    "file",
    "prompt_file",
    "prompt_sha256",
    "reference_inputs",
    "runtime_dependencies",
    "tool",
    "tool_version",
    "provider",
    "job_ids",
    "generated_at_utc",
    "observed",
    "bytes",
    "sha256",
    "curation_state",
    "intended_track",
    "runtime_eligible",
    "primary_experiment_eligible",
    "rights_review",
    "rights_sources",
    "ai_generated_content",
    "limitations",
    "post_processing",
}
REQUIRED_CURATION_FIELDS = {
    "schema_version",
    "asset_id",
    "status",
    "approved_at_utc",
    "scope",
    "technical_review",
    "visual_review",
    "rights_basis",
}


def _read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB is truncated")
    magic, version, declared_length = struct.unpack_from("<III", data, 0)
    if magic != GLB_MAGIC or version != 2:
        raise ValueError("file is not GLB v2")
    if declared_length != len(data):
        raise ValueError("GLB declared length does not match file bytes")
    document: dict[str, Any] | None = None
    binary = b""
    offset = 12
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        payload = data[offset + 8 : offset + 8 + chunk_length]
        if len(payload) != chunk_length:
            raise ValueError("GLB chunk is truncated")
        if chunk_type == JSON_CHUNK:
            document = json.loads(payload.decode("utf-8"))
        elif chunk_type == BIN_CHUNK:
            binary = payload
        offset += 8 + chunk_length
    if document is None:
        raise ValueError("GLB JSON chunk is missing")
    return document, binary


def _triangle_count(document: dict[str, Any]) -> int:
    total = 0
    accessors = document.get("accessors", [])
    for mesh in document.get("meshes", []):
        for primitive in mesh.get("primitives", []):
            if primitive.get("mode", 4) != 4:
                raise ValueError("player mesh contains a non-triangle primitive")
            accessor_index = primitive.get("indices")
            if accessor_index is None:
                accessor_index = primitive["attributes"]["POSITION"]
            total += int(accessors[accessor_index]["count"]) // 3
    return total


def _root_joint_indices(document: dict[str, Any]) -> set[int]:
    joints: set[int] = set()
    for skin in document.get("skins", []):
        joints.update(int(index) for index in skin.get("joints", []))
    parents: dict[int, int] = {}
    for parent_index, node in enumerate(document.get("nodes", [])):
        for child_index in node.get("children", []):
            parents[int(child_index)] = parent_index
    return {joint for joint in joints if parents.get(joint) not in joints}


def _accessor_floats(document: dict[str, Any], binary: bytes, accessor_index: int) -> list[float]:
    accessor = document["accessors"][accessor_index]
    if accessor.get("componentType") != FLOAT_COMPONENT or accessor.get("type") != "VEC3":
        raise ValueError("root scale accessor must be float VEC3")
    view = document["bufferViews"][accessor["bufferView"]]
    start = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    count = int(accessor["count"]) * 3
    end = start + count * 4
    if end > len(binary):
        raise ValueError("root scale accessor exceeds GLB binary chunk")
    return list(struct.unpack_from(f"<{count}f", binary, start))


def _root_scales_are_unit(document: dict[str, Any], binary: bytes) -> bool:
    roots = _root_joint_indices(document)
    for animation in document.get("animations", []):
        for channel in animation.get("channels", []):
            target = channel.get("target", {})
            if target.get("path") != "scale" or target.get("node") not in roots:
                continue
            sampler = animation["samplers"][channel["sampler"]]
            values = _accessor_floats(document, binary, sampler["output"])
            if any(abs(value - 1.0) > ROOT_SCALE_TOLERANCE for value in values):
                return False
    return True


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path.name} must contain a JSON object")
    return value


def main() -> int:
    failures: list[str] = []
    for required_path in (GLB_PATH, TEXTURE_PATH, PROVENANCE_PATH, CURATION_PATH):
        if not required_path.is_file():
            failures.append(f"missing required player asset file: {required_path}")
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    try:
        provenance = _load_json(PROVENANCE_PATH)
        curation = _load_json(CURATION_PATH)
        document, binary = _read_glb(GLB_PATH)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        print(f"FAIL: unable to parse player asset contract: {error}")
        return 1

    missing_provenance = sorted(REQUIRED_PROVENANCE_FIELDS - set(provenance))
    missing_curation = sorted(REQUIRED_CURATION_FIELDS - set(curation))
    if missing_provenance:
        failures.append(f"provenance fields missing: {missing_provenance}")
    if missing_curation:
        failures.append(f"curation fields missing: {missing_curation}")

    digest = hashlib.sha256(GLB_PATH.read_bytes()).hexdigest()
    if provenance.get("sha256") != digest:
        failures.append("player GLB sha256 drifted from provenance")
    if provenance.get("bytes") != GLB_PATH.stat().st_size:
        failures.append("player GLB byte count drifted from provenance")
    if provenance.get("file") != GLB_PATH.name:
        failures.append("provenance file does not name the runtime GLB")
    if provenance.get("runtime_eligible") is not True:
        failures.append("runtime_eligible must be true after curation")
    if provenance.get("primary_experiment_eligible") is not False:
        failures.append("AI player asset must remain ineligible for primary experiments")
    if provenance.get("ai_generated_content") is not True:
        failures.append("AI-generated-content disclosure must be true")
    if provenance.get("rights_review") != EXPECTED_RIGHTS_REVIEW:
        failures.append("rights review does not match the approved Higgsfield runtime basis")
    rights_sources = provenance.get("rights_sources")
    if not isinstance(rights_sources, list) or not any(
        isinstance(source, dict)
        and source.get("url") == REQUIRED_RIGHTS_SOURCE
        and source.get("section") == "4.4"
        and bool(source.get("verified_at_utc"))
        for source in rights_sources
    ):
        failures.append("rights review lacks a dated Higgsfield Terms section 4.4 receipt")
    if provenance.get("curation_state") != "curated-runtime":
        failures.append("curation_state must be curated-runtime")
    if provenance.get("intended_track") != "game-track-runtime":
        failures.append("intended_track must be game-track-runtime")

    texture_bytes = TEXTURE_PATH.read_bytes()
    texture_digest = hashlib.sha256(texture_bytes).hexdigest()
    runtime_dependencies = provenance.get("runtime_dependencies")
    if (
        not isinstance(runtime_dependencies, list)
        or len(runtime_dependencies) != 1
        or not isinstance(runtime_dependencies[0], dict)
    ):
        failures.append("runtime_dependencies must name exactly one texture receipt")
    else:
        texture_receipt = runtime_dependencies[0]
        if texture_receipt.get("file") != TEXTURE_PATH.name:
            failures.append("runtime dependency does not name the extracted texture")
        if texture_receipt.get("bytes") != len(texture_bytes):
            failures.append("player texture byte count drifted from provenance")
        if texture_receipt.get("sha256") != texture_digest:
            failures.append("player texture sha256 drifted from provenance")

    prompt_path = (PROVENANCE_PATH.parent / str(provenance.get("prompt_file", ""))).resolve()
    if not prompt_path.is_file():
        failures.append("referenced player prompt file is missing")
    elif hashlib.sha256(prompt_path.read_bytes()).hexdigest() != provenance.get("prompt_sha256"):
        failures.append("player prompt sha256 drifted from provenance")

    if curation.get("asset_id") != provenance.get("asset_id"):
        failures.append("curation asset_id does not match provenance")
    if curation.get("status") != "accepted-runtime":
        failures.append("curation status must be accepted-runtime")
    if curation.get("scope") != "game-track-public-runtime-only":
        failures.append("curation scope must remain public runtime only")
    if curation.get("technical_review") is not True or curation.get("visual_review") is not True:
        failures.append("technical and visual curation reviews must both be true")
    if curation.get("rights_basis") != EXPECTED_RIGHTS_REVIEW:
        failures.append("curation rights basis does not match provenance")

    clip_names = {str(animation.get("name", "")) for animation in document.get("animations", [])}
    if not REQUIRED_CLIPS.issubset(clip_names):
        failures.append(f"required locomotion clips missing: {sorted(REQUIRED_CLIPS - clip_names)}")
    if len(document.get("meshes", [])) < 1:
        failures.append("player GLB has no mesh")
    if len(document.get("skins", [])) < 1:
        failures.append("player GLB has no skin")
    try:
        triangles = _triangle_count(document)
        if provenance.get("observed", {}).get("triangles") != triangles:
            failures.append("measured triangle count drifted from provenance")
        if not _root_scales_are_unit(document, binary):
            failures.append("root-bone animation scale is not unit after post-processing")

        embedded_images = [image for image in document.get("images", []) if "bufferView" in image]
        if len(embedded_images) != 1:
            failures.append("player GLB must contain exactly one embedded image")
        else:
            texture_view = document["bufferViews"][embedded_images[0]["bufferView"]]
            texture_start = int(texture_view.get("byteOffset", 0))
            texture_end = texture_start + int(texture_view["byteLength"])
            if binary[texture_start:texture_end] != texture_bytes:
                failures.append("extracted player texture drifted from GLB-embedded image")
    except (KeyError, IndexError, TypeError, ValueError, struct.error) as error:
        failures.append(f"invalid player GLB structure: {error}")

    for material in document.get("materials", []):
        if material.get("alphaMode", "OPAQUE") != "OPAQUE":
            failures.append("player material must remain OPAQUE")
        if material.get("doubleSided") is not True:
            failures.append("player material must remain double-sided")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print(
        "PASS curated player asset: "
        f"{GLB_PATH.stat().st_size} bytes, {_triangle_count(document)} triangles, "
        f"clips={','.join(sorted(REQUIRED_CLIPS))}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
