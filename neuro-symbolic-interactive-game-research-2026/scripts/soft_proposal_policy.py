#!/usr/bin/env python3
"""Disclosure-policy gate for Codex OAuth soft proposals.

`codex_oauth_llm.validate_proposal` checks the envelope contract — that a reply
declares itself a candidate with no authorization effect. It does not look at
what the reply *says*. This module adds the missing half for the Sealed
Lighthouse scenario family:

* `model_visible_projection` builds the fact set a prompt may expose, so a
  permanently forbidden fact ID is never named in the request at all.
* `screen_response` flags a reply that names a sealed or stage-gated fact.

Boundary: the screen is lexical, so it is a cheap pre-filter, not a semantic
oracle. It cannot detect a paraphrase that leaks a secret without naming it;
that judgment belongs to the blind semantic annotation described in
SL-ORACLE-001. A clean screen therefore means "no forbidden identifier
surfaced", never "the reply is semantically safe".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCENARIO = PROJECT_ROOT / "game-track" / "godot" / "data" / "sealed_lighthouse.json"

FORBIDDEN_DISCLOSURE = "FORBIDDEN_DISCLOSURE"
STAGE_GATED_DISCLOSURE = "STAGE_GATED_DISCLOSURE"


def load_scenario(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def initial_state(scenario: dict[str, Any]) -> dict[str, Any]:
    return scenario["initial_state"]


def _surface_terms(scenario: dict[str, Any], fact_id: str) -> list[str]:
    """Identifier plus any scenario-declared player-facing terms for a fact."""

    declared = scenario.get("disclosure_surface_terms", {}).get(fact_id, [])
    terms = [fact_id, *declared]
    return [term for term in terms if term]


def model_visible_projection(
    state: dict[str, Any], scenario: dict[str, Any], actor_id: str = "captain_mira"
) -> dict[str, Any]:
    """Facts a prompt may expose, and the IDs disclosable at the current stage."""

    actor = state["npcs"][actor_id]
    stage = int(state["quest"]["stage"])
    known = sorted({*actor["disclosed"], *state["facts"]})
    disclosable = sorted(
        gate["fact_id"]
        for gate in scenario["disclosure_policy"]["stage_gates"]
        if stage >= int(gate["minimum_stage"])
        and gate["fact_id"] in actor["knowledge"]
        and gate["fact_id"] not in state["facts"]
    )
    return {"known_facts": known, "disclosable_now": disclosable, "quest_stage": stage}


def screen_response(
    text: str, state: dict[str, Any], scenario: dict[str, Any], actor_id: str = "captain_mira"
) -> dict[str, Any]:
    """Flag sealed or stage-gated identifiers that surfaced in a reply."""

    policy = scenario["disclosure_policy"]
    stage = int(state["quest"]["stage"])
    already_public = set(state["facts"]) | set(state["npcs"][actor_id]["disclosed"])
    codes: set[str] = set()
    matched: set[str] = set()

    def hits(fact_id: str) -> bool:
        return any(
            re.search(re.escape(term), text, re.IGNORECASE)
            for term in _surface_terms(scenario, fact_id)
        )

    for fact_id in policy["permanently_forbidden"]:
        if hits(fact_id):
            codes.add(FORBIDDEN_DISCLOSURE)
            matched.add(fact_id)
    for gate in policy["stage_gates"]:
        fact_id = gate["fact_id"]
        if fact_id in already_public or stage >= int(gate["minimum_stage"]):
            continue
        if hits(fact_id):
            codes.add(STAGE_GATED_DISCLOSURE)
            matched.add(fact_id)

    return {
        "clean": not codes,
        "violation_codes": sorted(codes),
        "matched_facts": sorted(matched),
        "screen": "lexical-identifier-screen",
        "semantic_oracle_required": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, default=DEFAULT_SCENARIO)
    parser.add_argument(
        "--projection",
        action="store_true",
        help="Print the model-visible projection instead of screening a reply.",
    )
    parser.add_argument(
        "--proposal",
        type=Path,
        help="Soft-proposal JSON file; omit to read the reply text from stdin.",
    )
    args = parser.parse_args(argv)

    scenario = load_scenario(args.scenario)
    state = initial_state(scenario)

    if args.projection:
        json.dump(model_visible_projection(state, scenario), sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if args.proposal is not None:
        payload = json.loads(args.proposal.read_text(encoding="utf-8"))
        text = payload.get("response", "") if isinstance(payload, dict) else ""
    else:
        text = sys.stdin.read()

    verdict = screen_response(text, state, scenario)
    json.dump(verdict, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if verdict["clean"] else 1


if __name__ == "__main__":
    sys.exit(main())
