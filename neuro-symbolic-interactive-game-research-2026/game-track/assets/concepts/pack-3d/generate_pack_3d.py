"""Frozen-prompt generation run for the SL3D presentation resource pack.

Dry-run validates each prompt before quota is spent; provenance is written
beside each PNG. Safe to re-run: existing PNGs are skipped.
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CONCEPTS = os.path.join(ROOT, "..")
LOG = os.path.join(ROOT, "generation-run.log")

ASSETS = [
    {
        "id": "SL3D-A01",
        "base": "SL3D-A01-storm-sky-panorama",
        "cls": "environment-backdrop",
        "size": "1536x1024",
        "ref": os.path.join(CONCEPTS, "SL-C01-environment-key-art.png"),
    },
    {
        "id": "SL3D-T01",
        "base": "SL3D-T01-wet-slate-planks",
        "cls": "tileable-surface-texture",
        "size": "1024x1024",
        "ref": os.path.join(CONCEPTS, "SL-C01-environment-key-art.png"),
    },
    {
        "id": "SL3D-T02",
        "base": "SL3D-T02-oxidized-brass",
        "cls": "tileable-surface-texture",
        "size": "1024x1024",
        "ref": os.path.join(CONCEPTS, "SL-C01-environment-key-art.png"),
    },
    {
        "id": "SL3D-P01",
        "base": "SL3D-P01-mira-dialogue-portrait",
        "cls": "npc-dialogue-portrait",
        "size": "1024x1024",
        "ref": os.path.join(CONCEPTS, "SL-C02-captain-mira-sheet.png"),
    },
    {
        "id": "SL3D-U01",
        "base": "SL3D-U01-signal-lens-icon",
        "cls": "item-icon",
        "size": "1024x1024",
        "ref": os.path.join(CONCEPTS, "SL-C04-evidence-icons.png"),
    },
]


def log(message):
    line = f"{datetime.datetime.now(datetime.UTC).strftime('%H:%M:%SZ')} {message}"
    print(line, flush=True)
    with open(LOG, "a") as handle:
        handle.write(line + "\n")


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, check=False)
    if result.stdout.strip():
        log(result.stdout.strip()[-2000:])
    if result.stderr.strip():
        log(result.stderr.strip()[-2000:])
    return result.returncode == 0


def tool_version():
    result = subprocess.run(
        ["npm", "ls", "-g", "god-tibo-imagen", "--depth=0"],
        capture_output=True,
        text=True,
        check=False,
    )
    for token in result.stdout.split():
        if token.startswith("god-tibo-imagen@"):
            return token.split("@", 1)[1]
    return "unknown"


def sips_dimension(png, flag):
    out = subprocess.run(
        ["sips", "-g", flag, png], capture_output=True, text=True, check=False
    ).stdout
    return int(out.strip().split()[-1])


def write_provenance(asset, version):
    png = os.path.join(ROOT, asset["base"] + ".png")
    prompt_path = os.path.join(ROOT, "prompts", asset["base"] + ".txt")
    with open(png, "rb") as png_handle:
        data = png_handle.read()
    with open(prompt_path, "rb") as prompt_handle:
        prompt_sha256 = hashlib.sha256(prompt_handle.read()).hexdigest()
    doc = {
        "schema_version": "1.0.0",
        "asset_id": asset["id"],
        "asset_class": asset["cls"],
        "file": asset["base"] + ".png",
        "prompt_file": "prompts/" + asset["base"] + ".txt",
        "prompt_sha256": prompt_sha256,
        "reference_inputs": [os.path.basename(asset["ref"])],
        "tool": "god-tibo-imagen",
        "tool_version": version,
        "provider": "private-codex",
        "generated_at_utc": datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requested_size": asset["size"],
        "observed_width": sips_dimension(png, "pixelWidth"),
        "observed_height": sips_dimension(png, "pixelHeight"),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "curation_state": "candidate-pending-review",
        "intended_track": ["design", "secondary-vlm-ui", "3d-presentation-candidate"],
        "runtime_eligible": False,
        "primary_experiment_eligible": False,
        "rights_review": "pending-human-publication-review",
        "ai_generated_content": True,
        "limitations": [
            "Undocumented private backend has no production SLA.",
            "Presentation-candidate use in the 3D slice awaits human rights/style review.",
            "Visual inspection does not establish originality, rights clearance, or player benefit.",
        ],
    }
    with open(os.path.join(ROOT, asset["base"] + ".provenance.json"), "w") as handle:
        json.dump(doc, handle, indent=2, ensure_ascii=False)
    log(f"PROVENANCE-OK {asset['id']}")


def main():
    version = tool_version()
    failures = 0
    for asset in ASSETS:
        png = os.path.join(ROOT, asset["base"] + ".png")
        if os.path.exists(png) and os.path.getsize(png) > 0:
            log(f"SKIP-EXISTING {asset['id']}")
            continue
        prompt_path = os.path.join(ROOT, "prompts", asset["base"] + ".txt")
        with open(prompt_path, encoding="utf-8") as prompt_handle:
            prompt = prompt_handle.read().strip()
        log(f"DRY-RUN {asset['id']}")
        if not run(["gti", "--prompt", prompt, "--dry-run"]):
            log(f"DRY-RUN-FAILED {asset['id']}")
            failures += 1
            continue
        log(f"GENERATE {asset['id']}")
        ok = run(
            [
                "gti",
                "--prompt",
                prompt,
                "--image",
                asset["ref"],
                "--size",
                asset["size"],
                "--output",
                png,
            ]
        )
        if ok and os.path.exists(png) and os.path.getsize(png) > 0:
            write_provenance(asset, version)
            log(f"GENERATED {asset['id']}")
        else:
            log(f"GENERATION-FAILED {asset['id']}")
            failures += 1
    log(f"PACK-RUN-COMPLETE failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
