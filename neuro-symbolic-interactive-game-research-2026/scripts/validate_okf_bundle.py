#!/usr/bin/env python3
"""OKF v0.1 structural lint for the methods knowledge bundle.

Checks every .md atom for closed YAML frontmatter, the required type/title/
description fields, and that absolute bundle links resolve to existing atoms.
"""

import os
import pathlib
import re
import sys


def main() -> int:
    bundle = sys.argv[1] if len(sys.argv) > 1 else "knowledge"
    errors = []
    atom_paths = set()
    for root, dirs, files in os.walk(bundle):
        dirs[:] = [d for d in dirs if d != "graphify-out"]
        for name in files:
            if name.endswith(".md"):
                atom_paths.add(
                    "/" + os.path.relpath(os.path.join(root, name), bundle).replace(os.sep, "/")
                )
    for root, dirs, files in os.walk(bundle):
        dirs[:] = [d for d in dirs if d != "graphify-out"]
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            text = pathlib.Path(path).read_text()
            if not text.startswith("---"):
                errors.append(f"{path}: missing frontmatter")
                continue
            fm_end = text.find("---", 3)
            if fm_end == -1:
                errors.append(f"{path}: unclosed frontmatter")
                continue
            frontmatter = text[3:fm_end]
            for field in ("type:", "title:", "description:"):
                if field not in frontmatter:
                    errors.append(f"{path}: missing required field {field!r}")
            for link in re.findall(r"\]\((/[^)]+\.md)\)", text):
                if link not in atom_paths:
                    errors.append(f"{path}: broken bundle link {link}")
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"OK — {len(atom_paths)} OKF atoms valid, all bundle links resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
