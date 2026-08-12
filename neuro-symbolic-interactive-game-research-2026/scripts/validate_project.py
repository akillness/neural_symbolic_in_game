#!/usr/bin/env python3
"""Dependency-light structural, parity, and integrity checks for the scaffold."""

from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

REQUIRED = [
    "README.ko.md",
    "README.en.md",
    "paper/ko/manuscript.md",
    "paper/en/manuscript.md",
    "configs/model-matrix.yaml",
    "configs/experiment-matrix.yaml",
    "configs/metric-catalog.yaml",
    "configs/scenario-catalog.yaml",
    "research/source-ledger.yaml",
    "research/claim-ledger.yaml",
    "research/original-link-audit.yaml",
    "research/journal-targets.md",
    "research/journal-targets.ko.md",
    "research/deep-research/report.md",
    "game-track/schemas/game-bridge.schema.json",
    "data/fixtures/game-bridge-event.json",
    "harness/ownership.yaml",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def check_required() -> None:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    if missing:
        fail(f"missing required files: {missing}")


def check_model_matrix() -> None:
    text = (ROOT / "configs/model-matrix.yaml").read_text(encoding="utf-8")
    ids = re.findall(r"^  - id: (.+)$", text, flags=re.MULTILINE)
    if not 5 <= len(ids) <= 10:
        fail(f"model matrix must contain 5-10 models, found {len(ids)}")
    if len(ids) != len(set(ids)):
        fail("model IDs are not unique")


def check_bilingual_claims() -> None:
    ko = (ROOT / "paper/ko/manuscript.md").read_text(encoding="utf-8")
    en = (ROOT / "paper/en/manuscript.md").read_text(encoding="utf-8")
    pattern = r"C-(?:METHOD|DATA|AFFECT|SYSTEM|RESULT)-\d{3}"
    ko_claims, en_claims = set(re.findall(pattern, ko)), set(re.findall(pattern, en))
    if ko_claims != en_claims:
        fail(
            f"bilingual claim mismatch: KO-only={ko_claims - en_claims}, EN-only={en_claims - ko_claims}"
        )
    if ko.count("TODO-RESULT") != en.count("TODO-RESULT"):
        fail("bilingual TODO-RESULT counts differ")
    if "TODO-RESULT" not in ko or "TODO-RESULT" not in en:
        fail("result lock marker missing")


def check_json_and_bridge() -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads((ROOT / "game-track/schemas/game-bridge.schema.json").read_text())
    event = json.loads((ROOT / "data/fixtures/game-bridge-event.json").read_text())
    Draft202012Validator.check_schema(schema)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(event), key=lambda item: list(item.path)
    )
    if errors:
        rendered = [
            f"{'.'.join(map(str, error.path)) or '<root>'}: {error.message}" for error in errors
        ]
        fail(f"bridge fixture violates Draft 2020-12 schema: {rendered}")
    for result in (ROOT / "research/deep-research/results").glob("*.json"):
        json.loads(result.read_text(encoding="utf-8"))


def check_svg() -> None:
    svgs = sorted((ROOT / "visuals").glob("*.svg"))
    if len(svgs) < 2:
        fail("at least two SVG visualizations are required")
    for svg in svgs:
        ET.parse(svg)


def check_scraped_sources() -> None:
    captures = sorted((ROOT / "research/sources/scraped").glob("*.md"))
    if len(captures) < 8:
        fail(f"expected at least 8 scraped captures, found {len(captures)}")
    expected_thin_probes = {
        "kaggle-multipeng-probe.md",
        "uist-generative-agents.md",
        "www-dynamic-difficulty-adjustment.md",
    }
    too_small = [
        path.name
        for path in captures
        if path.stat().st_size < 100 and path.name not in expected_thin_probes
    ]
    if too_small:
        fail(f"empty/thin scraped captures: {too_small}")
    audit = (ROOT / "research/original-link-audit.yaml").read_text(encoding="utf-8")
    for probe in expected_thin_probes:
        if probe not in audit:
            fail(f"thin/blocked probe lacks an explicit audit status: {probe}")


def check_raw_manifest() -> None:
    manifest = ROOT / "research/sources/raw/SHA256SUMS"
    if not manifest.exists():
        fail("raw source checksum manifest missing")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        path = manifest.parent / name
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            fail(f"raw source checksum mismatch: {name}")


def check_evidence_and_analysis_contracts() -> None:
    ledger = yaml.safe_load((ROOT / "research/source-ledger.yaml").read_text(encoding="utf-8"))
    missing_captures = []
    for source in ledger.get("sources", []):
        relative = source.get("local_capture")
        if relative and not (ROOT / "research" / relative).is_file():
            missing_captures.append(f"{source['id']}:{relative}")
    if missing_captures:
        fail(f"source ledger references missing captures: {missing_captures}")

    matrix = yaml.safe_load((ROOT / "configs/experiment-matrix.yaml").read_text(encoding="utf-8"))
    statistics = matrix.get("statistics", {})
    required_statistics = {
        "observational_unit",
        "paired_block",
        "seed_treatment",
        "confirmatory_contrasts",
        "multiple_comparisons",
        "noninferiority",
        "failures_and_missingness",
    }
    missing_statistics = required_statistics - statistics.keys()
    if missing_statistics:
        fail(f"confirmatory analysis contract is incomplete: {sorted(missing_statistics)}")


def check_graphify_layers() -> None:
    authoritative = REPO / "llm-wiki/graphify-out/graph.json"
    prompt_graph = REPO / "llm-wiki/graphify-out/prompts/graph.json"
    if not authoritative.is_file() or not prompt_graph.is_file():
        fail("both authoritative and prompt/output Graphify layers must exist")
    authoritative_data = json.loads(authoritative.read_text(encoding="utf-8"))
    prompt_data = json.loads(prompt_graph.read_text(encoding="utf-8"))
    if authoritative.resolve() == prompt_graph.resolve() or authoritative_data == prompt_data:
        fail("Graphify layers are mixed or identical")
    if not authoritative_data.get("nodes") or not prompt_data.get("nodes"):
        fail("Graphify graph layer has no nodes")


def main() -> None:
    check_required()
    check_model_matrix()
    check_bilingual_claims()
    check_json_and_bridge()
    check_svg()
    check_scraped_sources()
    check_raw_manifest()
    check_evidence_and_analysis_contracts()
    check_graphify_layers()
    print(
        "PASS: structure, bilingual claims, bridge, SVG, captures, raw hashes, and Graphify layers"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError, ET.ParseError) as exc:
        print(f"FAIL: {exc}")
        sys.exit(1)
