#!/usr/bin/env python3
"""Report reproducibility-critical tool surfaces without mutating the workspace."""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def output(command: list[str]) -> str:
    try:
        return subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=20
        ).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def main() -> None:
    graphify_help = output(["graphify", "--help"]) if shutil.which("graphify") else ""
    report = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "graphify_path": shutil.which("graphify"),
        "graphify_surface": {
            name: name in graphify_help
            for name in [
                "extract",
                "update",
                "cluster-only",
                "query",
                "scope",
                "summary",
                "export",
                "portable-check",
            ]
        },
        "scrapling_path": shutil.which("scrapling"),
        "git_commit": output(["git", "rev-parse", "HEAD"]),
        "research_root": str(ROOT),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
