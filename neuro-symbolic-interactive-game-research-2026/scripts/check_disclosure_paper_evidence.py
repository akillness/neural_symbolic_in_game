#!/usr/bin/env python3
"""Strict six-deliverable gate for NPC disclosure paper evidence.

This checker is intentionally separate from the additive paper producer.  It never
infers Godot execution from Python results or from declared manifest paths: an
explicit captured ``NPC_DISCLOSURE_RESULT`` receipt is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nesy_game.disclosure import verify_publication_sources

PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"
SIDECAR = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.sha256"
RESULTS = ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5"
MANIFEST = ROOT / "paper/latex/generated/disclosure_producer_manifest.json"
EXPECTED_PACKET_SHA256 = "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"
CHANGED_SCRIPTS = (
    "game-track/godot/scripts/game3d/game_3d.gd",
    "game-track/godot/scripts/sealed_lighthouse_machine.gd",
)
EXECUTION_SOURCES = (
    *CHANGED_SCRIPTS,
    "game-track/godot/data/sealed_lighthouse.json",
    "game-track/godot/scripts/evidence_capture_runner.gd",
    "game-track/godot/scripts/canonical_state.gd",
    "tests/npc_disclosure_harness.gd",
)
ARMS = ("unchecked_isolated", "general_rule", "ontology_gate")
LABELS = ("", "tab:disclosure-contract", "tab:disclosure-arms", "tab:disclosure-fixtures")
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing JSON artifact: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON artifact {path}: {exc}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else ROOT / candidate


def _numeric_tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", text))


def _check_packet() -> None:
    _require(PACKET.is_file(), f"frozen packet missing: {PACKET}")
    _require(_sha(PACKET) == EXPECTED_PACKET_SHA256, "frozen packet SHA-256 mismatch")
    sidecar = SIDECAR.read_text(encoding="utf-8").split()
    _require(sidecar and sidecar[0] == EXPECTED_PACKET_SHA256, "frozen packet sidecar mismatch")


def _check_current_results(manifest: dict[str, Any]) -> dict[str, Any]:
    required = {
        "disclosure-trace.jsonl": RESULTS / "disclosure-trace.jsonl",
        "comparison-summary.json": RESULTS / "comparison-summary.json",
        "factual-summary.json": RESULTS / "factual-summary.json",
        "metadata.json": RESULTS / "metadata.json",
    }
    input_hashes = manifest.get("input_sha256", {})
    expected_inputs = {
        "packet": str(PACKET.relative_to(ROOT)),
        "packet_sidecar": str(SIDECAR.relative_to(ROOT)),
        "trace": str((RESULTS / "disclosure-trace.jsonl").relative_to(ROOT)),
        "comparison": str((RESULTS / "comparison-summary.json").relative_to(ROOT)),
        "factual": str((RESULTS / "factual-summary.json").relative_to(ROOT)),
        "metadata": str((RESULTS / "metadata.json").relative_to(ROOT)),
    }
    _require(manifest.get("inputs") == expected_inputs, "manifest selected input path drift")
    for name, path in required.items():
        _require(path.is_file(), f"current result missing: {path}")
        key = {
            "disclosure-trace.jsonl": "trace",
            "comparison-summary.json": "comparison",
            "factual-summary.json": "factual",
            "metadata.json": "metadata",
        }[name]
        _require(input_hashes.get(key) == _sha(path), f"manifest input hash drift: {name}")
    metadata = _read_json(required["metadata.json"])
    _require(
        metadata.get("packet_sha256") == EXPECTED_PACKET_SHA256,
        "current metadata packet binding mismatch",
    )
    _require(
        metadata.get("current_source_bindings_observed") is True,
        "current source bindings were not observed",
    )
    observed = metadata.get("source_hashes")
    _require(isinstance(observed, dict) and observed, "current source hashes missing")
    _require(
        isinstance(metadata.get("public_source_bindings"), dict)
        and bool(metadata["public_source_bindings"])
        and metadata.get("observation_scope")
        == "new deterministic Python evaluation; no new Godot or model observation",
        "current public-source evaluation metadata missing",
    )
    public_binding = verify_publication_sources(
        ROOT,
        observed,
        _read_json(PACKET),
        public_source_bindings=metadata.get("public_source_bindings"),
    )
    _require(
        manifest.get("public_source_substitution") == public_binding,
        "manifest public substitution binding drift",
    )
    _require(
        manifest.get("observation_scope")
        == "publication materialization from current r5 deterministic Python and Godot artifacts; no new model observation",
        "publication observation scope drift",
    )
    comparison = _read_json(required["comparison-summary.json"])
    _require(
        comparison.get("arms") and set(comparison["arms"]) == set(ARMS),
        "three-arm comparison is incomplete",
    )
    _require(
        comparison.get("case_counts") == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
        "current denominators drift",
    )
    factual = _read_json(required["factual-summary.json"])
    _require(factual.get("status") == "PASS", "current factual summary is not PASS")
    _require(factual.get("general_ontology_equal") is True, "general/ontology parity is not PASS")
    return metadata


def _frozen_cases() -> dict[str, dict[str, Any]]:
    packet = _read_json(PACKET)
    cases = [*packet["normal_cases"], *packet["boundary_cases"], *packet["malformed_cases"]]
    return {case["case_id"]: case for case in cases}


def _expected_view(case: dict[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    return {
        "allowed": bool(expected["allowed"]),
        "codes": sorted(set(expected.get("codes", []))),
        "template_id": expected.get("template_id"),
        "state_effect": expected.get("state_effect", "denied_no_mutation"),
    }


def _expected_trace_check_ids(case: dict[str, Any]) -> list[str]:
    """Return the runtime predicate checks for a disclosure outcome."""
    codes = set(case.get("codes", []))
    if "DISCLOSURE_TEMPLATE_UNAVAILABLE" in codes:
        return ["DISC-CHECK-005-TEMPLATE"]
    if codes & {"FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE"}:
        return ["DISC-CHECK-001-POLICY"]
    if "UNKNOWN_ACTOR" in codes:
        return ["DISC-CHECK-001-POLICY", "DISC-CHECK-002-ACTOR"]
    if "NPC_DOES_NOT_KNOW_FACT" in codes:
        return [
            "DISC-CHECK-001-POLICY",
            "DISC-CHECK-002-ACTOR",
            "DISC-CHECK-003-KNOWLEDGE",
        ]
    state_effect = case.get("state_effect")
    if state_effect == "redisplay_no_mutation":
        return [
            "DISC-CHECK-001-POLICY",
            "DISC-CHECK-002-ACTOR",
            "DISC-CHECK-003-KNOWLEDGE",
            "DISC-CHECK-004-REDISPLAY",
        ]
    if state_effect == "fresh_disclosure":
        return [
            "DISC-CHECK-001-POLICY",
            "DISC-CHECK-002-ACTOR",
            "DISC-CHECK-003-KNOWLEDGE",
            "DISC-CHECK-005-FRESH",
        ]
    return []


def _check_godot_receipt(path: Path, metadata: dict[str, Any]) -> None:
    receipt = _read_json(path)
    _require(
        receipt.get("marker") == "NPC_DISCLOSURE_RESULT",
        "Godot receipt lacks NPC_DISCLOSURE_RESULT marker",
    )
    _require(receipt.get("passed") is True, "Godot receipt did not pass")
    _require(receipt.get("failures") == [], "Godot receipt contains failures")
    _require(
        receipt.get("packet_sha256") == EXPECTED_PACKET_SHA256,
        "Godot receipt packet binding mismatch",
    )
    _require(
        receipt.get("scenario_source") == "game-track/godot/data/sealed_lighthouse.json",
        "Godot receipt scenario binding mismatch",
    )
    receipt_hashes = receipt.get("source_hashes")
    _require(isinstance(receipt_hashes, dict), "Godot receipt source hashes missing")
    for relative in EXECUTION_SOURCES:
        source = ROOT / relative
        _require(source.is_file(), f"Godot receipt source missing: {relative}")
        _require(
            HASH_RE.fullmatch(str(receipt_hashes.get(relative, ""))) is not None,
            f"Godot receipt source hash malformed: {relative}",
        )
        _require(
            receipt_hashes[relative] == _sha(source),
            f"Godot receipt source hash mismatch: {relative}",
        )
        if relative in metadata.get("source_hashes", {}):
            _require(
                receipt_hashes[relative] == metadata["source_hashes"][relative],
                f"Godot receipt metadata hash mismatch: {relative}",
            )
    cases = receipt.get("cases")
    _require(
        isinstance(cases, list) and bool(cases),
        "Godot receipt requires nonempty real cases; marker-only proof is rejected",
    )
    frozen_cases = _frozen_cases()
    packet = _read_json(PACKET)
    packet_operation = packet["scope"]["operation"]
    approved_templates = {
        template["template_id"]: template for template in packet["approved_templates"]
    }
    seen: set[str] = set()
    required_case_keys = {
        "case_id",
        "operation",
        "actor_id",
        "fact_id",
        "stage",
        "prior_disclosed",
        "expected",
        "observed",
        "accepted",
        "codes",
        "template_id",
        "rule_ids",
        "state_effect",
        "prior_state_hash",
        "next_state_hash",
        "display",
        "disclosure_trace",
    }
    for index, case in enumerate(cases):
        _require(
            isinstance(case, dict) and required_case_keys.issubset(case),
            f"Godot receipt case[{index}] lacks semantic/hash/display/trace fields",
        )
        case_id = case["case_id"]
        _require(
            isinstance(case_id, str) and case_id in frozen_cases,
            f"Godot receipt case[{index}] is not a frozen case ID",
        )
        _require(case_id not in seen, f"Godot receipt duplicate case ID: {case_id}")
        seen.add(case_id)
        frozen = frozen_cases[case_id]
        _require(
            case["operation"] == packet_operation == "reveal_hint",
            f"Godot receipt case[{index}] operation drift",
        )
        for field in ("actor_id", "fact_id", "stage", "prior_disclosed"):
            if field in frozen:
                _require(case[field] == frozen[field], f"Godot receipt case[{index}] {field} drift")
        _require(
            case["expected"] == frozen["expected"],
            f"Godot receipt case[{index}] expected value is not frozen-packet bound",
        )
        _require(
            isinstance(case["observed"], dict), f"Godot receipt case[{index}] observed malformed"
        )
        observed = case["observed"]
        _require(
            observed.get("accepted") == case["accepted"],
            f"Godot receipt case[{index}] observed accepted mismatch",
        )
        _require(
            sorted(observed.get("codes", [])) == sorted(case["codes"]),
            f"Godot receipt case[{index}] observed codes mismatch",
        )
        _require(
            observed.get("template_id") == case["template_id"],
            f"Godot receipt case[{index}] observed template mismatch",
        )
        _require(
            observed.get("state_effect") == case["state_effect"],
            f"Godot receipt case[{index}] observed state effect mismatch",
        )
        _require(
            case["accepted"] == bool(frozen["expected"]["allowed"]),
            f"Godot receipt case[{index}] accepted/expectation mismatch",
        )
        _require(
            sorted(case["codes"]) == sorted(frozen["expected"].get("codes", [])),
            f"Godot receipt case[{index}] codes/expectation mismatch",
        )
        _require(
            case["template_id"] == frozen["expected"].get("template_id"),
            f"Godot receipt case[{index}] template/expectation mismatch",
        )
        _require(
            case["state_effect"] == frozen["expected"].get("state_effect", "denied_no_mutation"),
            f"Godot receipt case[{index}] state/expectation mismatch",
        )
        _require(
            isinstance(case["rule_ids"], list)
            and all(isinstance(rule, str) for rule in case["rule_ids"])
            and sorted(case["rule_ids"]) == sorted(frozen["expected"].get("rule_ids", [])),
            f"Godot receipt case[{index}] rule IDs are not frozen-packet bound",
        )
        _require(
            HASH_RE.fullmatch(str(case["prior_state_hash"])) is not None
            and HASH_RE.fullmatch(str(case["next_state_hash"])) is not None,
            f"Godot receipt case[{index}] state hashes malformed",
        )
        _require(
            isinstance(case["display"], dict)
            and isinstance(case["disclosure_trace"], dict)
            and bool(case["disclosure_trace"]),
            f"Godot receipt case[{index}] display/trace malformed",
        )
        trace = case["disclosure_trace"]
        _require(
            trace.get("contract_id") == packet["packet_id"]
            and trace.get("contract_version") == packet["packet_version"],
            f"Godot receipt case[{index}] disclosure contract binding mismatch",
        )
        _require(
            isinstance(trace.get("check_ids"), list)
            and all(isinstance(check_id, str) for check_id in trace["check_ids"])
            and sorted(trace["check_ids"]) == sorted(_expected_trace_check_ids(case)),
            f"Godot receipt case[{index}] disclosure trace check IDs mismatch",
        )
        _require(
            isinstance(trace.get("error_ids"), list)
            and sorted(trace["error_ids"]) == sorted(case["codes"]),
            f"Godot receipt case[{index}] disclosure trace error IDs mismatch",
        )
        _require(
            trace.get("prior_state_hash") == case["prior_state_hash"]
            and trace.get("next_state_hash") == case["next_state_hash"],
            f"Godot receipt case[{index}] disclosure trace hash mismatch",
        )
        template_id = case["template_id"]
        if template_id is None:
            _require(
                case["display"] == {},
                f"Godot receipt case[{index}] display/template binding mismatch",
            )
        else:
            template = approved_templates.get(template_id)
            _require(
                isinstance(template, dict)
                and case["display"].get("template_id") == template_id
                and case["display"].get("source") == template["source"],
                f"Godot receipt case[{index}] display/template binding mismatch",
            )


def _check_outputs(manifest: dict[str, Any], godot_receipt: Path) -> dict[str, Any]:
    six = manifest.get("six_deliverables")
    _require(
        isinstance(six, dict)
        and set(six)
        == {
            "ontology_contract",
            "python_godot_boundary",
            "raw_backed_signals",
            "three_arm_comparison",
            "paired_manuscripts",
            "game_fixture_mapping",
        },
        "six-deliverable mapping is incomplete",
    )
    outputs = manifest.get("outputs", {})
    required_outputs = [
        "results_en",
        "results_ko",
        "tables_en",
        "tables_ko",
        "figure_svg",
        "figure_png",
        "figure_pdf",
    ]
    for key in required_outputs:
        relative = outputs.get(key)
        _require(
            isinstance(relative, str) and _resolve(relative).is_file(),
            f"generated output missing: {key}",
        )
    en_text = "\n".join(
        _resolve(outputs[key]).read_text(encoding="utf-8") for key in ("results_en", "tables_en")
    )
    ko_text = "\n".join(
        _resolve(outputs[key]).read_text(encoding="utf-8") for key in ("results_ko", "tables_ko")
    )
    for label in LABELS[1:]:
        _require(label in en_text and label in ko_text, f"bilingual label missing: {label}")
    _require(_numeric_tokens(en_text) == _numeric_tokens(ko_text), "EN/KO numeric parity mismatch")
    svg = _resolve(outputs["figure_svg"]).read_text(encoding="utf-8")
    for token in (
        'data-paper-label="fig:disclosure-signals"',
        "disclosure-trace.jsonl",
        "PASS",
        "FAIL",
        "NR",
        "unreported_cases",
        "not model latent state",
    ):
        _require(token in svg, f"figure provenance/legend token missing: {token}")
    en_pdf = ROOT / "paper/latex/en/main.pdf"
    ko_pdf = ROOT / "paper/latex/ko/main.pdf"
    en_log = ROOT / "paper/latex/en/main.log"
    ko_log = ROOT / "paper/latex/ko/main.log"
    for pdf, log in ((en_pdf, en_log), (ko_pdf, ko_log)):
        _require(pdf.is_file() and pdf.stat().st_size > 0, f"paper PDF missing: {pdf}")
        _require(log.is_file(), f"paper build log missing: {log}")
        log_text = log.read_text(encoding="utf-8", errors="replace")
        _require(
            "Output written on" in log_text and "Fatal error" not in log_text,
            f"paper build receipt failed: {log}",
        )
    return {
        "godot_receipt": str(godot_receipt.relative_to(ROOT)),
        "pdfs": [str(en_pdf.relative_to(ROOT)), str(ko_pdf.relative_to(ROOT))],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify six disclosure paper evidence deliverables"
    )
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--godot-receipt", type=Path, default=RESULTS / "godot-receipt.json")
    parser.add_argument(
        "--public-receipt",
        type=Path,
        help="write a NEW publication-materialization receipt; never a new gameplay observation",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        manifest_path = _resolve(args.manifest)
        godot_receipt = _resolve(args.godot_receipt)
        manifest = _read_json(manifest_path)
        _check_packet()
        metadata = _check_current_results(manifest)
        _require(godot_receipt.is_file(), f"explicit Godot receipt missing: {godot_receipt}")
        _check_godot_receipt(godot_receipt, metadata)
        outputs = _check_outputs(manifest, godot_receipt)
        if args.public_receipt:
            receipt_path = _resolve(args.public_receipt)
            receipt = {
                "schema_version": "disclosure-public-materialization/v1",
                "status": "PASS",
                "observation_scope": "publication materialization from current r5 deterministic Python and Godot artifacts; no new model observation",
                "frozen_packet_sha256": EXPECTED_PACKET_SHA256,
                "case_counts": {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
                "public_source_substitution": manifest["public_source_substitution"],
                "current_inputs_sha256": manifest["input_sha256"],
                "current_godot_receipt": str(godot_receipt.relative_to(ROOT)),
                "current_godot_receipt_sha256": _sha(godot_receipt),
                "producer_manifest_sha256": _sha(manifest_path),
                "materialization_sources_sha256": {
                    path: _sha(ROOT / path)
                    for path in (
                        "src/nesy_game/disclosure.py",
                        "scripts/check_disclosure_paper_evidence.py",
                        "scripts/generate_disclosure_paper_results.py",
                        "scripts/generate_signal_explainer.py",
                    )
                },
                "outputs_sha256": {
                    path: _sha(_resolve(path)) for path in manifest["outputs"].values()
                },
            }
            receipt_path.parent.mkdir(parents=True, exist_ok=True)
            with receipt_path.open("x", encoding="utf-8") as stream:
                stream.write(
                    json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
                )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 1
    print(
        json.dumps(
            {"status": "PASS", "manifest": str(manifest_path.relative_to(ROOT)), **outputs},
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
