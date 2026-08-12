#!/usr/bin/env python3
"""Validate TRACE-RPG model evidence records against its field registry."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fields", type=Path, required=True)
    parser.add_argument("--dir", dest="results", type=Path, required=True)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    registry = yaml.safe_load(args.fields.read_text(encoding="utf-8"))
    definitions = [
        field
        for category in registry.get("field_categories", [])
        for field in category.get("fields", [])
    ]
    known = {field["name"] for field in definitions}
    required = {field["name"] for field in definitions if field.get("required")}
    records = sorted(args.results.glob("*.json"))
    if not records:
        print("FAIL: no deep-research JSON records")
        return 1

    failed = False
    for path in records:
        record = json.loads(path.read_text(encoding="utf-8"))
        missing = sorted(required - record.keys())
        unknown = sorted(record.keys() - known)
        empty = sorted(name for name in required if record.get(name) in (None, "", []))
        valid = not missing and not empty
        failed |= not valid
        if not args.quiet or not valid:
            print(
                f"{'PASS' if valid else 'FAIL'} {path.name}: "
                f"missing={missing}, empty={empty}, extra={unknown}"
            )

    passed = len(records) if not failed else "not-all"
    print(f"Deep-research contract: {passed}/{len(records)} records valid")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
