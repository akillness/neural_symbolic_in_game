#!/usr/bin/env python3
"""Run the frozen three-arm NPC disclosure evaluator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.disclosure import (
    DisclosureContractError,
    evaluate_contract,
    load_frozen_contract,
    write_evaluation,
)

DEFAULT_PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate the frozen reveal_hint disclosure packet through isolated unchecked, "
            "general-rule, and ontology-gate arms."
        )
    )
    parser.add_argument(
        "--packet", type=Path, default=DEFAULT_PACKET, help="frozen expectation packet"
    )
    parser.add_argument(
        "--public-sources",
        action="store_true",
        help="use the pinned, explicitly non-equivalent reviewer-account-redacted source derivative",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="new empty result directory; recorded evidence is never overwritten",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=ROOT,
        help="nested project root containing game-track and research",
    )
    parser.add_argument("--json", action="store_true", help="print factual summary JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet = args.packet if args.packet.is_absolute() else ROOT / args.packet
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    project_root = (
        args.project_root if args.project_root.is_absolute() else ROOT / args.project_root
    )
    try:
        if output_dir.exists() and (not output_dir.is_dir() or any(output_dir.iterdir())):
            raise ValueError(f"refusing to overwrite recorded evidence: {output_dir}")
        contract = load_frozen_contract(packet, project_root, public_sources=args.public_sources)
        bundle = evaluate_contract(contract)
        paths = write_evaluation(bundle, output_dir)
    except (DisclosureContractError, OSError, ValueError) as exc:
        print(f"FAIL disclosure evaluation: {exc}", file=sys.stderr)
        return 1
    factual = bundle.factual_summary
    status = factual["status"]
    if args.json:
        print(json.dumps(factual, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"{status} {bundle.metadata['contract_version']}: "
            f"normal={factual['case_counts']['normal']}, "
            f"boundary={factual['case_counts']['boundary']}, "
            f"malformed={factual['case_counts']['malformed']}, "
            f"general_ontology_equal={factual['general_ontology_equal']}, "
            f"rule_changes={factual['rule_change_fixtures_match']}"
        )
        for path in paths.values():
            print(path)
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
