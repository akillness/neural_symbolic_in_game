#!/usr/bin/env python3
"""Export the typed repository-local OKF methods graph and answer exact path queries."""

from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.kg_ontology_simulation import (
    atomic_write,
    build_okf_graph,
    canonical_json,
)

KNOWLEDGE = ROOT / "knowledge"
OUT = KNOWLEDGE / "graphify-out" / "okf-links.json"


def _resolve_hint(graph: dict[str, object], hint: str) -> str:
    node_ids = sorted(node["id"] for node in graph["nodes"])
    if hint in node_ids:
        return hint
    matches = [node_id for node_id in node_ids if hint in node_id]
    if len(matches) != 1:
        raise ValueError(f"hint must resolve exactly once: {hint!r} -> {matches}")
    return matches[0]


def shortest_path(graph: dict[str, object], source_hint: str, target_hint: str) -> list[str]:
    nodes = {node["id"]: node for node in graph["nodes"]}
    source = _resolve_hint(graph, source_hint)
    target = _resolve_hint(graph, target_hint)
    adjacency = {node_id: set() for node_id in nodes}
    for edge in graph["edges"]:
        adjacency[edge["source"]].add(edge["target"])
        adjacency[edge["target"]].add(edge["source"])
    queue = deque([(source, [source])])
    visited = {source}
    while queue:
        current, route = queue.popleft()
        if current == target:
            return route
        for neighbor in sorted(adjacency[current]):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, route + [neighbor]))
    raise ValueError(f"no path found: {source} -> {target}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", nargs=2, metavar=("SOURCE_HINT", "TARGET_HINT"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    graph = build_okf_graph(KNOWLEDGE, ROOT)
    payload = canonical_json(graph).encode()
    if args.check:
        if not OUT.is_file() or OUT.read_bytes() != payload:
            raise SystemExit(f"stale OKF graph: {OUT}")
    else:
        atomic_write(OUT, payload)
    print(
        f"exported {graph['summary']['nodes']} nodes and "
        f"{graph['summary']['reference_edges']} edges to {OUT}"
    )
    if args.path:
        route = shortest_path(graph, *args.path)
        nodes = {item["id"]: item for item in graph["nodes"]}
        for node_id in route:
            print(f"- {nodes[node_id]['title']} ({node_id})")


if __name__ == "__main__":
    main()
