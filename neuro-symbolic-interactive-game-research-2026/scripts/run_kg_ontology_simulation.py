"""Generate or verify the claim-bounded KG/ontology simulation packet."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.kg_ontology_simulation import (
    DEFAULT_DATABASE,
    build_artifact_payloads,
    build_sqlite,
    check_artifacts,
    write_artifacts,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate typed OKF link proposals without touching game authority."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if tracked JSON/Markdown/TSV/SVG/TeX artifacts are stale",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=DEFAULT_DATABASE,
        help=(
            "generated SQLite graph-store path; replacement is atomic and rejects symlinks or "
            "non-SQLite files"
        ),
    )
    parser.add_argument(
        "--no-database",
        action="store_true",
        help="skip the local SQLite runtime artifact",
    )
    parser.add_argument("--json", action="store_true", help="print the compact result as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payloads, matrix, context = build_artifact_payloads(ROOT)
    if args.check:
        mismatches = check_artifacts(ROOT, payloads)
        with tempfile.TemporaryDirectory(prefix="trace-rpg-kg-check-") as directory:
            counts = build_sqlite(ROOT, Path(directory) / "knowledge.sqlite", matrix, context)
        if mismatches:
            for mismatch in mismatches:
                print(f"FAIL: {mismatch}")
            return 1
    else:
        write_artifacts(ROOT, payloads)
        counts = {}
        if not args.no_database:
            database = args.database if args.database.is_absolute() else ROOT / args.database
            counts = build_sqlite(ROOT, database, matrix, context)

    summary = {
        "simulation_id": matrix["simulation_id"],
        "status": matrix["status"],
        "graph": {
            "nodes": matrix["graph"]["nodes"],
            "reference_edges": matrix["graph"]["reference_edges"],
            "curated_typed_edges": matrix["graph"]["curated_typed_edges"],
            "ontology_violations": matrix["ontology_violations"],
        },
        "winner": matrix["winner"],
        "sqlite_rows": counts,
        "mode": "check" if args.check else "write",
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        metrics = matrix["winner"]["metrics"]
        print(
            f"PASS {matrix['simulation_id']}: {matrix['graph']['nodes']} nodes, "
            f"{matrix['graph']['curated_typed_edges']} typed edges, "
            f"winner={matrix['winner']['strategy_id']}, "
            f"precision={metrics['precision']:.3f}, recall={metrics['recall']:.3f}, "
            f"Sem@3={metrics['semantic_at_k']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
