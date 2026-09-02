#!/usr/bin/env python3
"""Write the deterministic editable-source manifest for tables and figures."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "visuals" / "source-manifest.json"

PAPER_FIGURE_GENERATOR = "scripts/generate_paper_figures.py"
DIRECTION_GENERATOR = "scripts/generate_direction_figures.py"
PAPER_TABLE_GENERATOR = "scripts/generate_paper_results.py"
KG_GENERATOR = "src/nesy_game/kg_ontology_simulation.py"
BALANCE_GENERATOR = "scripts/run_balance_archetypes.py"
CONFORMANCE_GENERATOR = "scripts/run_conformance_pilot.py"

CONFORMANCE_TABLE_STEMS = (
    "accounting-guards",
    "adapter-accounting",
    "boundary-sentinels",
    "closed-boundary-regressions",
    "gate-conformance",
    "integrity-boundaries",
    "integrity-faults",
    "pilot-summary",
    "repair-arm-summary",
    "repair-arms",
    "repair-class-summary",
)

LIVE_SUMMARIES = (
    "research/academic-pipeline/rq2-live-pilot/frozen-pilot-base/policy_visible/summary.json",
    "research/academic-pipeline/rq2-live-pilot/frozen-pilot-base/policy_blind/summary.json",
    "research/academic-pipeline/rq2-live-pilot/frozen-pilot-base/goal_directed_blind/summary.json",
    "research/academic-pipeline/rq2-live-pilot/signal-repair-v2/policy_visible/summary.json",
    "research/academic-pipeline/rq2-live-pilot/signal-repair-v2/policy_blind/summary.json",
)

EVIDENCE_ROOT = (
    "_workspace/current/engineering/tech-verification/evidence/"
    "godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5"
)


def receipt(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    payload = path.read_bytes()
    return {
        "path": relative_path,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def receipts(paths: Iterable[str]) -> list[dict[str, Any]]:
    return [receipt(path) for path in paths]


def visual_asset(
    asset_id: str,
    kind: str,
    *,
    rendered: tuple[str, ...],
    editable: tuple[str, ...],
    generator: str,
    data: tuple[str, ...] = (),
    used_by: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "id": asset_id,
        "kind": kind,
        "rendered": receipts(rendered),
        "editable_sources": receipts(editable),
        "generator": receipt(generator),
        "data_sources": receipts(data),
        "used_by": list(used_by),
    }


def table_source(
    source_id: str,
    *,
    layouts: tuple[str, ...],
    generator: str | None,
    data: tuple[str, ...] = (),
    readable: tuple[str, ...] = (),
    rendered_in: tuple[str, ...] = (),
    anchors: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "id": source_id,
        "kind": "table",
        "layout_sources": receipts(layouts),
        "generator": receipt(generator) if generator else None,
        "data_sources": receipts(data),
        "readable_sources": receipts(readable),
        "rendered_in": list(rendered_in),
        "anchors": list(anchors),
    }


def build_manifest() -> dict[str, Any]:
    paper_usage = ("paper/latex/en/main.tex", "paper/latex/ko/main.tex")
    direction_note = ("research/directions/consensus-vs-symbolic-gate.md",)

    paper_assets = []
    for stem, asset_id in (("fig_architecture", "paper-architecture"),):
        base = f"paper/latex/figures/{stem}"
        paper_assets.append(
            visual_asset(
                asset_id,
                "diagram",
                rendered=(f"{base}.pdf", f"{base}.png"),
                editable=(f"{base}.svg",),
                generator=PAPER_FIGURE_GENERATOR,
                used_by=paper_usage,
            )
        )

    adjacent_assets = [
        visual_asset(
            "direction-consensus-gate-lanes",
            "diagram",
            rendered=("research/directions/figures/fig_consensus_gate_lanes.svg",),
            editable=("research/directions/figures/fig_consensus_gate_lanes.svg",),
            generator=DIRECTION_GENERATOR,
            used_by=direction_note,
        ),
        visual_asset(
            "direction-cost-validity-pareto",
            "diagram",
            rendered=("research/directions/figures/fig_cost_validity_pareto_concept.svg",),
            editable=("research/directions/figures/fig_cost_validity_pareto_concept.svg",),
            generator=DIRECTION_GENERATOR,
            used_by=direction_note,
        ),
        visual_asset(
            "kg-ontology-evaluation-matrix",
            "table-chart",
            rendered=("research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg",),
            editable=("research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg",),
            generator=KG_GENERATOR,
            data=(
                "research/simulation/kg-ontology/latest/evaluation-matrix.json",
                "research/simulation/kg-ontology/latest/strategy-trials.tsv",
            ),
            used_by=(),
        ),
        visual_asset(
            "game-balance-archetypes",
            "chart",
            rendered=("game-track/godot/docs/latest/balance-archetypes.svg",),
            editable=("game-track/godot/docs/latest/balance-archetypes.svg",),
            generator=BALANCE_GENERATOR,
            data=("game-track/godot/docs/latest/balance-archetypes.json",),
            used_by=("game-track/godot/docs/latest/balance-archetypes.md",),
        ),
    ]

    pilot_dir = "research/academic-pipeline/stage-04-pilot"
    table_sources = [
        table_source(
            "current-paper-hand-authored-tables",
            layouts=("paper/latex/en/main.tex", "paper/latex/ko/main.tex"),
            generator=None,
            rendered_in=("paper-en", "paper-ko"),
            anchors=(
                "tab:validators",
                "alg:commit",
                "tab:rho-rules",
            ),
        ),
        table_source(
            "offline-pilot-paper-tables",
            layouts=(
                "paper/latex/generated/pilot_tables_en.tex",
                "paper/latex/generated/pilot_tables_ko.tex",
            ),
            generator=PAPER_TABLE_GENERATOR,
            data=(f"{pilot_dir}/pilot-results.json",),
            rendered_in=("paper-en", "paper-ko"),
            anchors=("tab:pilot-repair", "tab:pilot-accounting"),
        ),
        table_source(
            "live-screening-paper-table",
            layouts=(
                "paper/latex/generated/live_pilot_tables_en.tex",
                "paper/latex/generated/live_pilot_tables_ko.tex",
            ),
            generator=PAPER_TABLE_GENERATOR,
            data=(
                "research/academic-pipeline/rq2-live-pilot/promotion-manifest.json",
                *LIVE_SUMMARIES,
            ),
            rendered_in=("paper-en", "paper-ko"),
            anchors=("tab:live-screening",),
        ),
        table_source(
            "contribution-and-lane-paper-tables",
            layouts=(
                "paper/latex/generated/contribution_map_en.tex",
                "paper/latex/generated/contribution_map_ko.tex",
                "paper/latex/generated/evidence_lanes_en.tex",
                "paper/latex/generated/evidence_lanes_ko.tex",
            ),
            generator=PAPER_TABLE_GENERATOR,
            data=(
                "research/academic-pipeline/contribution-evidence-matrix.csv",
                "research/academic-pipeline/experiment-evidence-matrix.csv",
            ),
            rendered_in=("paper-en", "paper-ko"),
            anchors=("tab:contribution-map", "tab:evidence-lanes"),
        ),
        table_source(
            "kg-ontology-paper-fragments",
            layouts=(
                "paper/latex/generated/kg_ontology_simulation_en.tex",
                "paper/latex/generated/kg_ontology_simulation_ko.tex",
            ),
            generator=KG_GENERATOR,
            data=("research/simulation/kg-ontology/latest/evaluation-matrix.json",),
            rendered_in=(),
            anchors=("tab:kg-ontology-simulation",),
        ),
        table_source(
            "stage-04-conformance-table-bundle",
            layouts=tuple(f"{pilot_dir}/{stem}.tex" for stem in CONFORMANCE_TABLE_STEMS),
            generator=CONFORMANCE_GENERATOR,
            data=tuple(f"{pilot_dir}/{stem}.csv" for stem in CONFORMANCE_TABLE_STEMS),
            readable=tuple(f"{pilot_dir}/{stem}.md" for stem in CONFORMANCE_TABLE_STEMS),
        ),
    ]

    rendered_surfaces = [
        {
            "id": "paper-en",
            "artifact": receipt("paper/latex/en/main.pdf"),
            "editable_source": receipt("paper/latex/en/main.tex"),
        },
        {
            "id": "paper-ko",
            "artifact": receipt("paper/latex/ko/main.pdf"),
            "editable_source": receipt("paper/latex/ko/main.tex"),
        },
    ]

    render_dir = f"{EVIDENCE_ROOT}/rendered-canonical-v1"
    noneditable_evidence = [
        {
            "id": "sealed-lighthouse-render-panels",
            "kind": "engine-evidence",
            "editable": False,
            "rendered": receipts(
                (
                    f"{render_dir}/sl-rc-001-arrival.png",
                    f"{render_dir}/sl-rc-002-rejected-secret.png",
                    f"{render_dir}/sl-rc-003-authorized-hint.png",
                )
            ),
            "reproducible_sources": receipts(
                (
                    f"{render_dir}/capture-manifest.json",
                    f"{EVIDENCE_ROOT}/evidence-manifest.json",
                    "game-track/godot/scripts/evidence_capture_runner.gd",
                    "scripts/capture_godot_evidence.py",
                )
            ),
            "reason": (
                "The pixels are trace-bound engine evidence. Retouching is forbidden; "
                "regenerate from the bound scene, event/state packet, and capture runner."
            ),
        }
    ]

    return {
        "schema_version": 1,
        "generated_by": "scripts/update_visual_source_manifest.py",
        "rendered_surfaces": rendered_surfaces,
        "visual_assets": paper_assets + adjacent_assets,
        "table_sources": table_sources,
        "noneditable_evidence": noneditable_evidence,
    }


def main() -> None:
    payload = json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n"
    MANIFEST.write_text(payload, encoding="utf-8", newline="\n")
    print(f"wrote {MANIFEST.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
