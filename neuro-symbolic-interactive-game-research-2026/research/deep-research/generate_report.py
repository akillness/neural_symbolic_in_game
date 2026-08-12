#!/usr/bin/env python3
"""Render validated deep-research JSON records as a complete Markdown report."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
FIELDS = ROOT / "fields.yaml"
OUTPUT = ROOT / "report.md"

CATEGORY_MAPPING = {
    "Basic Info": ["basic_info", "Basic Info"],
    "Technical Features": ["technical_features", "technical_characteristics", "Technical Features"],
    "Performance Metrics": ["performance_metrics", "performance", "Performance Metrics"],
    "Milestone Significance": ["milestone_significance", "milestones", "Milestone Significance"],
    "Business Info": ["business_info", "commercial_info", "Business Info"],
    "Competition & Ecosystem": ["competition_ecosystem", "competition", "Competition & Ecosystem"],
    "History": ["history", "History"],
    "Market Positioning": ["market_positioning", "market", "Market Positioning"],
    "Experimental Fit": ["experimental_fit", "Experimental Fit"],
    "Uncertainty": ["uncertainty", "Uncertainty"],
}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def nested_values(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from nested_values(child)
    else:
        yield value


def lookup(record: dict[str, Any], category: str, field: str) -> Any:
    if field in record:
        return record[field]
    for key in CATEGORY_MAPPING.get(category, [category]):
        nested = record.get(key)
        if isinstance(nested, dict) and field in nested:
            return nested[field]
    for value in record.values():
        if isinstance(value, dict) and field in value:
            return value[field]
    return None


def format_value(value: Any) -> str:
    if isinstance(value, list):
        if value and all(isinstance(item, dict) for item in value):
            return "<br>".join(
                " | ".join(f"{k}: {format_value(v)}" for k, v in item.items()) for item in value
            )
        rendered = [format_value(item) for item in value]
        return ", ".join(rendered) if len(rendered) <= 5 else "<br>".join(rendered)
    if isinstance(value, dict):
        return "; ".join(f"{key}: {format_value(child)}" for key, child in value.items())
    text = str(value)
    return text if len(text) <= 100 else text.replace(". ", ".<br>")


def is_uncertain(field: str, value: Any, uncertain: set[str]) -> bool:
    if field in uncertain or value in (None, ""):
        return True
    return any("[uncertain]" in str(item) for item in nested_values(value))


def main() -> None:
    schema = yaml.safe_load(FIELDS.read_text(encoding="utf-8"))
    categories = schema["field_categories"]
    records = [
        json.loads(path.read_text(encoding="utf-8")) for path in sorted(RESULTS.glob("*.json"))
    ]
    defined = {field["name"] for category in categories for field in category["fields"]}
    internal = {"_source_file", "uncertain"}
    category_keys = {key for aliases in CATEGORY_MAPPING.values() for key in aliases}

    lines = [
        "# Deep Research Report: 2026 Model Panel",
        "",
        "> Evidence snapshot: 2026-08-12. Exact revisions and service availability must be rechecked at experiment time.",
        "",
        "## Table of contents",
        "",
    ]
    for index, record in enumerate(records, 1):
        name = str(record.get("name", f"Item {index}"))
        lines.append(
            f"{index}. [{name}](#{slug(name)}) — Access: {record.get('access', 'n/a')} | "
            f"Context: {record.get('context_tokens', 'n/a')} | License: {record.get('license', 'n/a')}"
        )

    for record in records:
        name = str(record.get("name", "Unnamed item"))
        uncertain = set(record.get("uncertain", []))
        lines.extend(["", f"## {name}", ""])
        for category in categories:
            rows: list[tuple[str, str]] = []
            for field in category["fields"]:
                field_name = field["name"]
                value = lookup(record, category["name"], field_name)
                if not is_uncertain(field_name, value, uncertain):
                    rows.append((field_name, format_value(value)))
            if rows:
                lines.extend([f"### {category['name']}", "", "| Field | Value |", "|---|---|"])
                lines.extend(f"| {field} | {value} |" for field, value in rows)
                lines.append("")

        extras = {
            key: value
            for key, value in record.items()
            if key not in defined and key not in internal and key not in category_keys
        }
        if extras:
            lines.extend(["### Other Info", "", "| Field | Value |", "|---|---|"])
            lines.extend(f"| {key} | {format_value(value)} |" for key, value in extras.items())
            lines.append("")
        if uncertain:
            lines.extend(
                ["### Uncertain fields", ""] + [f"- {field}" for field in sorted(uncertain)] + [""]
            )

    OUTPUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
