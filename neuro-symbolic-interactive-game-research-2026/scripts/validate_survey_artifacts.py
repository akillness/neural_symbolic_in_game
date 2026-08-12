#!/usr/bin/env python3
"""Validate the project-local browser survey deliverables."""

from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED = {
    "triage.md": ("# Triage", "- Problem:", "- Audience:", "- Why now:"),
    "context.md": (
        "## Workflow Context",
        "## Affected Users",
        "## Current Workarounds",
        "## Adjacent Problems",
        "## User Voices",
    ),
    "solutions.md": (
        "## Solution List",
        "## Categories",
        "## What People Actually Use",
        "## Frequency Ranking",
        "## Key Gaps",
        "## Contradictions",
        "## Key Insight",
    ),
}
PROVENANCE = ("direct page retrieval", "indexed snippet", "thin evidence")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-provenance", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    contents: list[str] = []
    for filename, markers in REQUIRED.items():
        path = args.path / filename
        if not path.is_file():
            errors.append(f"missing {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        contents.append(text)
        errors.extend(f"{filename} lacks {marker}" for marker in markers if marker not in text)

    combined = "\n".join(contents).lower()
    if args.require_provenance and not any(label in combined for label in PROVENANCE):
        errors.append("no recognized provenance label")

    if errors:
        print("FAIL: survey contract: " + "; ".join(errors))
        return 1
    print(f"PASS: survey contract ({len(REQUIRED)} artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
