#!/usr/bin/env python3
"""Validate file-based agents, skills, ownership, and workflow contracts."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
AGENTS = ROOT / ".claude/agents"
SKILLS = ROOT / ".claude/skills"
SECTIONS = [
    "## Core Responsibilities",
    "## Operational Principles",
    "## Input Protocol",
    "## Output Protocol",
    "## Error Handling",
    "## Team Communication",
]


def main() -> None:
    errors: list[str] = []
    agents = sorted(AGENTS.glob("*.md"))
    if len(agents) < 6:
        errors.append(f"need at least six specialist agents; found {len(agents)}")
    names: set[str] = set()
    for path in agents:
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^name:\s*(\S+)", text, re.MULTILINE)
        if not match:
            errors.append(f"{path}: missing frontmatter name")
        else:
            if match.group(1) in names:
                errors.append(f"duplicate agent name {match.group(1)}")
            names.add(match.group(1))
        for section in SECTIONS:
            if section not in text:
                errors.append(f"{path}: missing {section}")
        if "allowed-tools:" not in text:
            errors.append(f"{path}: missing allowed-tools")

    skill_files = sorted(SKILLS.glob("*/SKILL.md"))
    if len(skill_files) < 3:
        errors.append(f"need at least three reusable skills; found {len(skill_files)}")
    for path in skill_files:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "description:" not in text:
            errors.append(f"{path}: invalid skill frontmatter")

    ownership_path = ROOT / "harness/ownership.yaml"
    ownership_text = ownership_path.read_text(encoding="utf-8")
    ownership = yaml.safe_load(ownership_text)
    artifacts = ownership.get("artifacts", {})
    if not isinstance(artifacts, dict):
        errors.append("ownership artifacts must be a mapping")
        artifacts = {}
    for artifact, assignment in artifacts.items():
        artifact_path = (ROOT / artifact).resolve()
        if not artifact_path.exists():
            errors.append(f"ownership artifact does not exist: {artifact}")
        if not isinstance(assignment, dict):
            errors.append(f"ownership assignment must be a mapping: {artifact}")
            continue
        writer = assignment.get("writer")
        reviewer = assignment.get("reviewer")
        for role in (writer, reviewer):
            if role not in names:
                errors.append(f"ownership references unknown role {role}")
        if writer == reviewer:
            errors.append(f"ownership writer/reviewer collision: {artifact}")
    if "writer and reviewer must be different roles" not in ownership_text:
        errors.append("writer/reviewer separation rule missing")

    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors))
        raise SystemExit(1)
    print(f"PASS: {len(agents)} agents, {len(skill_files)} skills, ownership and workflows")


if __name__ == "__main__":
    main()
