#!/usr/bin/env python3
"""Export the OKF bundle's cross-links as an explicit knowledge graph.

Nodes are atoms (typed via frontmatter); edges are the bundle-absolute markdown
links between them. Output: knowledge/graphify-out/okf-links.json plus a
degree/orphan summary, and an optional --path A B shortest-path query.
"""

import json
import os
import pathlib
import re
import sys
from collections import deque

BUNDLE = "knowledge"
OUT = os.path.join(BUNDLE, "graphify-out", "okf-links.json")


def load_graph():
    nodes = {}
    edges = []
    for root, _, files in os.walk(BUNDLE):
        if "graphify-out" in root:
            continue
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            rel = "/" + os.path.relpath(path, BUNDLE).replace(os.sep, "/")
            text = pathlib.Path(path).read_text()
            fm_end = text.find("---", 3)
            frontmatter = text[3:fm_end] if text.startswith("---") and fm_end != -1 else ""
            type_match = re.search(r"^type:\s*(.+)$", frontmatter, re.MULTILINE)
            title_match = re.search(r"^title:\s*(.+)$", frontmatter, re.MULTILINE)
            nodes[rel] = {
                "id": rel,
                "type": type_match.group(1).strip() if type_match else "Unknown",
                "title": title_match.group(1).strip() if title_match else rel,
            }
            for target in re.findall(r"\]\((/[^)]+\.md)\)", text):
                edges.append({"source": rel, "target": target})
    edges = [e for e in edges if e["target"] in nodes]
    return nodes, edges


def shortest_path(nodes, edges, start_hint, goal_hint):
    def resolve(hint):
        for node_id in nodes:
            if hint in node_id:
                return node_id
        return None

    start, goal = resolve(start_hint), resolve(goal_hint)
    if not start or not goal:
        return None
    adjacency = {}
    for edge in edges:
        adjacency.setdefault(edge["source"], set()).add(edge["target"])
        adjacency.setdefault(edge["target"], set()).add(edge["source"])
    queue = deque([[start]])
    seen = {start}
    while queue:
        trail = queue.popleft()
        if trail[-1] == goal:
            return trail
        for neighbor in adjacency.get(trail[-1], ()):  # undirected walk
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(trail + [neighbor])
    return None


def main() -> int:
    nodes, edges = load_graph()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as handle:
        json.dump(
            {"nodes": list(nodes.values()), "edges": edges},
            handle,
            indent=2,
            ensure_ascii=False,
        )
    degree = {node_id: 0 for node_id in nodes}
    for edge in edges:
        degree[edge["source"]] += 1
        degree[edge["target"]] += 1
    orphans = sorted(node_id for node_id, count in degree.items() if count == 0)
    print(f"okf-links.json — {len(nodes)} atoms, {len(edges)} typed-prose links")
    hubs = sorted(degree.items(), key=lambda item: -item[1])[:5]
    for node_id, count in hubs:
        print(f"  hub {count:2d}  {node_id}")
    if orphans:
        print("  orphan atoms (no links in/out):", ", ".join(orphans))
    if len(sys.argv) == 4 and sys.argv[1] == "--path":
        trail = shortest_path(nodes, edges, sys.argv[2], sys.argv[3])
        if trail:
            print("path:", "  →  ".join(trail))
        else:
            print(f"no path between {sys.argv[2]!r} and {sys.argv[3]!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
