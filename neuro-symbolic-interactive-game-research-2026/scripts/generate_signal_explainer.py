#!/usr/bin/env python3
"""Generate the public-safe TRACE-RPG signal explainer contract and figures.

This producer is additive: it reads the frozen declaration and current result/receipt
artifacts, derives categorical counts, and never rewrites an input or emits raw game
state.  The live lane is a receipt projection; engine sequence/time are unreported
unless the engine envelope supplies them at runtime.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nesy_game.disclosure import verify_publication_sources

PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"
PACKET_SIDECAR = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.sha256"
RESULTS = ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5"
TRACE = RESULTS / "disclosure-trace.jsonl"
COMPARISON = RESULTS / "comparison-summary.json"
FACTUAL = RESULTS / "factual-summary.json"
METADATA = RESULTS / "metadata.json"
SCENARIO = ROOT / "game-track/godot/data/sealed_lighthouse.json"
REFERENCE = ROOT / "game-track/web/dashboard/disclosure-reference.json"
ONTOLOGY_MAP = ROOT / "game-track/web/dashboard/ontology-map.json"
FIGURES = ROOT / "paper/latex/figures"
EXPECTED_PACKET_SHA = "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"
ARMS = ("unchecked_isolated", "general_rule", "ontology_gate")
STRATA = (("N", "normal"), ("B", "boundary"), ("M", "malformed"))

PYTHON7 = (
    ("action_policy", "Action policy"),
    ("precondition", "Precondition"),
    ("object_reachability", "Object reachability"),
    ("npc_knowledge", "NPC knowledge"),
    ("forbidden_disclosure", "Forbidden disclosure"),
    ("quest_stage", "Quest stage"),
    ("quest_stage_monotonicity", "Quest-stage monotonicity"),
)
GODOT6 = (
    ("POLICY", "Policy"),
    ("PRECONDITION", "Precondition"),
    ("REACHABILITY", "Reachability"),
    ("KNOWLEDGE", "Knowledge"),
    ("DISCLOSURE", "Disclosure"),
    ("QUEST STAGE", "Quest stage"),
)
DISCLOSURE7 = (
    ("DISC-001", "Permanent prohibition"),
    ("DISC-002", "Stage-gated denial"),
    ("DISC-003", "Eligible actor"),
    ("DISC-004", "Actor knowledge"),
    ("DISC-005", "Fresh authorized disclosure"),
    ("DISC-006", "Authorized redisplay"),
    ("DISC-007", "Denial preserves state"),
)


def _reject_constant(token: str) -> None:
    raise ValueError(f"non-finite JSON number: {token}")


def _ensure_finite(value: Any, path: str = "$") -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"non-finite JSON number at {path}")
    if isinstance(value, dict):
        for key, nested in value.items():
            _ensure_finite(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _ensure_finite(nested, f"{path}[{index}]")
    return value


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> Any:
    try:
        return _ensure_finite(
            json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant)
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"invalid JSON input: {path}: {exc}") from exc


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = _ensure_finite(json.loads(line, parse_constant=_reject_constant))
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid JSONL input {path}:{line_number}: {exc}") from exc
        require(isinstance(row, dict), f"JSONL row is not an object: {path}:{line_number}")
        rows.append(row)
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_inputs() -> dict[str, Any]:
    packet_bytes = PACKET.read_bytes()
    packet_sha = hashlib.sha256(packet_bytes).hexdigest()
    require(packet_sha == EXPECTED_PACKET_SHA, "frozen packet digest drift")
    sidecar = PACKET_SIDECAR.read_text(encoding="utf-8").split()[0]
    require(sidecar == packet_sha, "frozen packet sidecar drift")
    packet = json.loads(packet_bytes, parse_constant=_reject_constant)
    require(
        packet.get("status") == "FROZEN_EXPECTATIONS_NOT_RUNTIME_RESULTS", "packet is not frozen"
    )
    require(packet.get("scope", {}).get("operation") == "reveal_hint", "unexpected operation")
    rows = read_jsonl(TRACE)
    comparison = read_json(COMPARISON)
    factual = read_json(FACTUAL)
    metadata = read_json(METADATA)
    scenario = read_json(SCENARIO)
    cases = [*packet["normal_cases"], *packet["boundary_cases"], *packet["malformed_cases"]]
    case_ids = [case.get("case_id") for case in cases]
    require(
        all(isinstance(case_id, str) and case_id for case_id in case_ids), "frozen case id missing"
    )
    require(len(case_ids) == len(set(case_ids)) == 60, "frozen case ids duplicate or missing")
    for (prefix, name), count in zip(STRATA, (48, 4, 8)):
        group = packet[f"{name}_cases"]
        require(len(group) == count, f"frozen {name} denominator drift")
        for case in group:
            require(
                case["case_id"].startswith(f"{prefix}-"),
                "frozen case stratum does not match packet bucket",
            )
            require(type(case.get("stage")) is int, "frozen case stage must be an integer")
            require(
                isinstance(case.get("knows"), bool)
                and isinstance(case.get("prior_disclosed"), bool),
                "frozen case knowledge/disclosed axes must be boolean",
            )
            require(
                isinstance(case.get("expected"), dict)
                and isinstance(case["expected"].get("allowed"), bool),
                "frozen case expected.allowed must be boolean",
            )
            require(
                isinstance(case["expected"].get("codes"), list)
                and all(isinstance(code, str) for code in case["expected"]["codes"]),
                "frozen case expected codes must be strings",
            )
            if prefix != "M":
                for field in ("actor_id", "fact_id"):
                    require(
                        isinstance(case.get(field), str) and bool(case[field]),
                        f"frozen case {field} missing",
                    )
    by_case = {case["case_id"]: case for case in cases}
    require(len(rows) == 180, "immutable trace must contain 180 rows")
    expected_pairs = {(case_id, arm) for case_id in case_ids for arm in ARMS}
    observed_pairs = {(row.get("case_id"), row.get("arm")) for row in rows}
    require(len(observed_pairs) == len(rows), "trace case/arm pairs duplicate")
    require(observed_pairs == expected_pairs, "trace case/arm pair missing")
    known_rule_ids = {rule_id for rule_id, _ in DISCLOSURE7}
    for row in rows:
        require(row.get("stratum") == row["case_id"][0], f"trace stratum drift: {row['case_id']}")
        require(
            isinstance(row.get("mismatch"), bool),
            f"trace mismatch must be boolean: {row.get('case_id')}",
        )
        require(
            isinstance(row.get("mutated"), bool),
            f"trace mutated must be boolean: {row.get('case_id')}",
        )
        require(
            isinstance(row.get("replay_equal"), bool),
            f"trace replay_equal must be boolean: {row.get('case_id')}",
        )
        require(
            isinstance((row.get("expected") or {}).get("allowed"), bool),
            f"trace expected.allowed must be boolean: {row.get('case_id')}",
        )
        require(
            isinstance((row.get("observed") or {}).get("allowed"), bool),
            f"trace observed.allowed must be boolean: {row.get('case_id')}",
        )
        expected = by_case[row["case_id"]]["expected"]
        expected_view = {
            "allowed": expected["allowed"],
            "codes": sorted(set(expected["codes"])),
            "template_id": expected.get("template_id"),
            "state_effect": expected.get("state_effect", "denied_no_mutation"),
        }
        require(row["expected"] == expected_view, f"trace expected view drift: {row['case_id']}")
        checks = row.get("checks")
        require(isinstance(checks, list), "trace checks must be a list")
        for check in checks:
            require(
                isinstance(check, dict) and set(check) == {"rule_id", "outcome"},
                "trace check fields are invalid",
            )
            require(
                isinstance(check["rule_id"], str)
                and check["rule_id"] in known_rule_ids
                and isinstance(check["outcome"], str)
                and check["outcome"] in {"pass", "fail"},
                "trace check identifier or outcome is invalid",
            )
    require(
        comparison.get("case_counts") == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
        "comparison denominators drift",
    )
    require(
        factual.get("status") == "PASS" and factual.get("general_ontology_equal") is True,
        "factual summary is not PASS",
    )
    require(metadata.get("packet_sha256") == packet_sha, "metadata packet binding drift")
    require(
        metadata.get("contract_version") == packet.get("packet_version"),
        "metadata contract version drift",
    )
    require(
        metadata.get("arms") == list(ARMS) and metadata.get("case_ids") == case_ids,
        "metadata arms or case IDs drift",
    )
    require(
        metadata.get("current_source_bindings_observed") is True,
        "current source bindings were not observed",
    )
    source_hashes = metadata.get("source_hashes")
    require(
        isinstance(source_hashes, dict) and set(source_hashes) == set(packet["source_hashes"]),
        "metadata source binding set drift",
    )
    require(
        isinstance(metadata.get("public_source_bindings"), dict)
        and bool(metadata["public_source_bindings"])
        and metadata.get("observation_scope")
        == "new deterministic Python evaluation; no new Godot or model observation",
        "current public-source evaluation metadata missing",
    )
    verify_publication_sources(
        ROOT,
        source_hashes,
        packet,
        public_source_bindings=metadata.get("public_source_bindings"),
    )
    for row in rows:
        binding = row.get("contract_binding", {})
        require(
            binding.get("packet_sha256") == packet_sha
            and binding.get("source_hashes") == source_hashes,
            "trace source or packet binding drift",
        )
    return {
        "packet": packet,
        "packet_sha": packet_sha,
        "rows": rows,
        "comparison": comparison,
        "factual": factual,
        "metadata": metadata,
        "scenario": scenario,
        "by_case": by_case,
    }


def _unsafe(row: dict[str, Any]) -> bool:
    return bool(row.get("unsafe_violations")) or bool(row.get("violations"))


def derive_arm(rows: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    selected = [row for row in rows if row.get("arm") == arm]
    require(len(selected) == 60, f"{arm}: case count drift")
    unique_unsafe = {row["case_id"] for row in selected if _unsafe(row)}
    # The frozen contract defines unsafe as unauthorized allow or redisplay mutation;
    # permitted fresh representation mismatches are not unsafe.
    unauthorized = {
        row["case_id"]
        for row in selected
        if not row["expected"]["allowed"] and row["observed"].get("allowed")
    }
    redisplay = {
        row["case_id"]
        for row in selected
        if row["expected"].get("state_effect") == "redisplay_no_mutation" and row.get("mutated")
    }
    unique_unsafe = unauthorized | redisplay
    strata: dict[str, dict[str, Any]] = {}
    for prefix, name in STRATA:
        cell_rows = [row for row in selected if row.get("stratum") == prefix]
        require(
            len(cell_rows) == {"normal": 48, "boundary": 4, "malformed": 8}[name],
            f"{arm}/{name}: denominator drift",
        )
        checks = [check for row in cell_rows for check in row.get("checks", [])]
        strata[name] = {
            "n": len(cell_rows),
            "outcome": {
                "allowed": sum(bool(r["observed"].get("allowed")) for r in cell_rows),
                "denied": sum(not bool(r["observed"].get("allowed")) for r in cell_rows),
            },
            "unsafe": len({r["case_id"] for r in cell_rows if r["case_id"] in unique_unsafe}),
            "mismatch": sum(bool(r.get("mismatch")) for r in cell_rows),
            "replay": {
                "equal": sum(bool(r.get("replay_equal")) for r in cell_rows),
                "unequal": sum(not bool(r.get("replay_equal")) for r in cell_rows),
            },
            "checks": {
                "pass": sum(check.get("outcome") == "pass" for check in checks),
                "fail": sum(check.get("outcome") == "fail" for check in checks),
                "report_status": "reported" if checks else "unreported",
            },
            "report_status": "reported",
        }
    return {
        "case_count": len(selected),
        "outcome": {
            "allowed": sum(bool(r["observed"].get("allowed")) for r in selected),
            "denied": sum(not bool(r["observed"].get("allowed")) for r in selected),
        },
        "unsafe": len(unique_unsafe),
        "mismatch": sum(bool(r.get("mismatch")) for r in selected),
        "replay": {
            "equal": sum(bool(r.get("replay_equal")) for r in selected),
            "unequal": sum(not bool(r.get("replay_equal")) for r in selected),
        },
        "strata": strata,
        "report_status": "reported",
    }


def semantic_rules(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "python7": [{"id": key, "label": label} for key, label in PYTHON7],
        "godot6": [{"id": key, "label": label} for key, label in GODOT6],
        "disclosure7": [{"id": key, "label": label} for key, label in DISCLOSURE7],
        "boundary": "Python validator checks, Godot display families, and frozen disclosure rules are distinct non-isomorphic label sets.",
    }


def live_projection(data: dict[str, Any]) -> dict[str, Any]:
    """Describe the live lane without preloading independent fixture evidence."""
    return {
        "status": "awaiting_runtime",
        "timeline_source": "runtime_embedded_events",
        "events": [],
        "counts": {"runtime_events": 0},
        "clock": {"seq": "unreported", "t_ms": "unreported", "provider_latency": "out_of_scope"},
        "note": "The live timeline starts empty and is populated only by new sequential engine events; independent fixture evidence remains in its own checker and paper lanes.",
    }


def build_reference(data: dict[str, Any]) -> dict[str, Any]:
    arms = {arm: derive_arm(data["rows"], arm) for arm in ARMS}
    general_rows = {row["case_id"]: row for row in data["rows"] if row.get("arm") == "general_rule"}
    ontology_rows = {
        row["case_id"]: row for row in data["rows"] if row.get("arm") == "ontology_gate"
    }
    equality = sum(
        json.dumps(
            {
                "observed": general_rows[case_id]["observed"],
                "mutated": general_rows[case_id]["mutated"],
                "replay_equal": general_rows[case_id]["replay_equal"],
                "mismatch": general_rows[case_id]["mismatch"],
            },
            sort_keys=True,
        )
        == json.dumps(
            {
                "observed": ontology_rows[case_id]["observed"],
                "mutated": ontology_rows[case_id]["mutated"],
                "replay_equal": ontology_rows[case_id]["replay_equal"],
                "mismatch": ontology_rows[case_id]["mismatch"],
            },
            sort_keys=True,
        )
        for case_id in general_rows
    )
    require(
        equality == 60 and data["factual"].get("general_ontology_equal") is True,
        "general/ontology equality drift",
    )
    reported_equality = data["comparison"].get("general_vs_ontology", {})
    require(
        reported_equality.get("case_count") == 60
        and reported_equality.get("equal_case_count") == equality
        and reported_equality.get("outcome_equal") is True
        and reported_equality.get("mismatch_case_ids") == [],
        "comparison equality summary drift",
    )
    for arm, observed in arms.items():
        reported = data["comparison"].get("arms", {}).get(arm, {})
        metrics = {
            "case_count": observed["case_count"],
            "allowed_count": observed["outcome"]["allowed"],
            "denied_count": observed["outcome"]["denied"],
            "unique_unsafe_case_count": observed["unsafe"],
            "expected_mismatch_count": observed["mismatch"],
            "replay_mismatch_count": observed["replay"]["unequal"],
        }
        require(
            all(
                type(reported.get(key)) is int and reported[key] == value
                for key, value in metrics.items()
            ),
            f"comparison aggregate drift: {arm}",
        )
        for key, metric in (
            ("unsafe_by_stratum", "unsafe"),
            ("semantic_mismatch_by_stratum", "mismatch"),
        ):
            expected_counts = {prefix: observed["strata"][name][metric] for prefix, name in STRATA}
            require(
                reported.get(key) == expected_counts
                and all(type(value) is int for value in reported[key].values()),
                f"comparison stratum aggregate drift: {arm}",
            )
        require(
            data["factual"].get("arm_observations", {}).get(arm) == reported,
            f"factual arm summary drift: {arm}",
        )
    require(
        (
            arms["general_rule"]["unsafe"],
            arms["ontology_gate"]["unsafe"],
            arms["unchecked_isolated"]["unsafe"],
        )
        == (0, 0, 51),
        "unsafe count drift",
    )
    require(
        (
            arms["general_rule"]["mismatch"],
            arms["ontology_gate"]["mismatch"],
            arms["unchecked_isolated"]["mismatch"],
        )
        == (0, 0, 60),
        "mismatch count drift",
    )
    graph = {
        "nodes": [
            {"id": "typed_input", "label": "Typed input"},
            {"id": "ontology", "label": "Entities, relations, rules"},
            {"id": "checks", "label": "Actual checks"},
            {"id": "decision", "label": "Allowed or denied"},
            {"id": "state_effect", "label": "Canonical state effect"},
        ],
        "edges": [
            ["typed_input", "ontology"],
            ["ontology", "checks"],
            ["checks", "decision"],
            ["decision", "state_effect"],
        ],
        "boundary": "Methods ontology simulation is separate from runtime policy; no live capture or superiority claim.",
    }
    cells = {arm: details["strata"] for arm, details in arms.items()}
    input_hashes = {
        name: sha(path)
        for name, path in (
            ("packet", PACKET),
            ("packet_sidecar", PACKET_SIDECAR),
            ("trace", TRACE),
            ("comparison", COMPARISON),
            ("factual", FACTUAL),
            ("metadata", METADATA),
            ("scenario", SCENARIO),
        )
    }
    return {
        "schema_version": "trace-rpg-signal-explainer/v1",
        "semantic_labels": {
            "typed_input": "operation, actor role, subject type, integer quest stage, knowledge/disclosed boolean axes",
            "entities": "actor and fact references are typed; unsafe raw identifiers are omitted from public projections",
            "relations": "knowledge and prior-disclosure relations connect typed input to policy checks",
            "rules": "minimum stage, forbidden membership, eligible actor, and knowledge predicates",
            "checks": "only checks actually recorded are shown; absent coverage is unreported",
            "decision": "authorized fresh, authorized redisplay, or denied",
            "state_effect": "fresh disclosure, redisplay without mutation, or denied without mutation",
            "missingness": "unreported is evidence absence, never pass, skipped, or out_of_scope",
        },
        "live": live_projection(data),
        "frozen_comparison": {
            "independent_inputs": 60,
            "arms": list(ARMS),
            "case_counts": {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
            "counts": {
                "general_ontology_equal": equality,
                "unsafe_by_arm": {arm: arms[arm]["unsafe"] for arm in ARMS},
                "mismatch_by_arm": {arm: arms[arm]["mismatch"] for arm in ARMS},
            },
            "cells": cells,
            "graph": graph,
            "claim_boundary": data["comparison"].get("claim_boundary", {}),
        },
        "disclosure_rules": semantic_rules(data),
        "provenance": {
            "packet_sha256": data["packet_sha"],
            "input_hashes": input_hashes,
            "source_mismatches": data["metadata"].get("source_hash_mismatches", {}),
        },
    }


def svg_text(x: int, y: int, value: str, cls: str = "body", anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}">{escape(value)}</text>'


def svg_box(
    x: int,
    y: int,
    w: int,
    h: int,
    fill: str,
    stroke: str = "#C9CDD1",
    dash: str = "",
    class_name: str = "",
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    class_attr = f' class="{class_name}"' if class_name else ""
    return f'<rect{class_attr} x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash_attr}/>'


def svg_header(width: int, height: int, title: str, desc: str, label: str) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="svg-title svg-desc" data-paper-label="{label}">',
        f'<title id="svg-title">{escape(title)}</title>',
        f'<desc id="svg-desc">{escape(desc)}</desc>',
        "<style>text{font-family:Helvetica,Arial,sans-serif;fill:#202124}.title{font-size:34px;font-weight:700}.subtitle{font-size:28px;fill:#5F6368}.head{font-size:32px;font-weight:700}.body{font-size:30px}.small{font-size:28px;fill:#5F6368}.label{font-size:30px;font-weight:700}.cell{font-size:30px}.note{font-size:28px;font-style:italic;fill:#5F6368}</style>",
        '<defs><marker id="arrow-blue" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" fill="#0072B2"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="#FFFFFF"/>',
    ]


def mechanism_svg() -> str:
    ontology = read_json(ONTOLOGY_MAP)
    require(
        isinstance(ontology, dict) and ontology.get("schema_version") == "ontology-evidence-map/v1",
        "mechanism ontology schema drift",
    )
    role_ids = ("world", "actor", "knowledge", "fact", "policy", "quest", "action", "trace")
    roles = {role["id"]: role["labels"]["en"] for role in ontology["roles"]}
    require(
        len(ontology["roles"]) == len(role_ids) and set(roles) == set(role_ids),
        "mechanism ontology role vocabulary drift",
    )
    packet = read_json(PACKET)
    source_packet = ontology.get("source_packet")
    scenario = ontology.get("scenario")
    scenario_path = SCENARIO.relative_to(ROOT).as_posix()
    require(
        isinstance(source_packet, dict)
        and source_packet.get("path") == PACKET.relative_to(ROOT).as_posix()
        and all(
            source_packet.get(field) == packet[field]
            for field in ("packet_id", "packet_version", "status")
        )
        and source_packet.get("sha256") == sha(PACKET) == EXPECTED_PACKET_SHA
        and isinstance(scenario, dict)
        and scenario.get("path") == scenario_path
        and scenario.get("sha256") == sha(SCENARIO) == packet["source_hashes"][scenario_path],
        "mechanism ontology source binding drift",
    )
    width, height = 1280, 1060
    parts = svg_header(
        width,
        height,
        "TRACE-RPG source-bound ontology mechanism",
        "Eight roles from ontology-map.json connect scenario and frozen expectation sources to relations and constraints, actual recorded checks, a bounded decision and canonical state effect. This is an explicit authored ontology, not hidden model state or a seven-dimensional embedding. Python Boolean checks, Godot display families and disclosure rules remain separate vocabularies. Missing checks are unreported, never passed.",
        "fig:signal-mechanism",
    )
    stages = [
        (
            "#EAF4FA",
            "#0072B2",
            "SOURCE + TYPED REQUEST",
            ("scenario + frozen expectations", "reveal_hint(actor_id, fact_id)"),
        ),
        (
            "#E8F5EF",
            "#007A59",
            "EIGHT ONTOLOGY ROLES",
            (
                f"{roles['world']} declares {roles['actor']} / {roles['fact']} / {roles['quest']}",
                f"{roles['knowledge']} links {roles['actor']} to {roles['fact']}",
                f"{roles['policy']} constrains {roles['action']}",
                f"{roles['trace']} records checks and effects",
            ),
        ),
        (
            "#E8F5EF",
            "#007A59",
            "RELATIONS / CONSTRAINTS",
            (
                "actor knows fact; fact disclosed",
                "forbidden / minimum quest stage",
                "knowledge or history ≠ permission",
            ),
        ),
        (
            "#FFF2DD",
            "#A05A00",
            "ACTUAL RECORDED CHECKS",
            (
                "policy / actor / knowledge",
                "stage gate + state-effect rules",
                "only emitted checks shown",
            ),
        ),
        (
            "#FBECEC",
            "#B54747",
            "DECISION",
            ("authorized fresh /", "authorized redisplay / denied"),
        ),
        (
            "#EEF0F2",
            "#666A6D",
            "CANONICAL STATE EFFECT",
            (
                "fresh: add fact + disclosed ID",
                "tide_marks_hint only: relationship memory",
                "redisplay / denial: no mutation",
                "quest stage preserved",
            ),
        ),
    ]
    # Snake order leaves dedicated connector channels outside padded cards.
    positions = ((20, 16), (660, 16), (660, 316), (20, 316), (20, 616), (660, 616))
    for (x, y), (fill, stroke, title, detail) in zip(positions, stages):
        parts += [
            svg_box(x, y, 600, 252, fill, stroke),
            svg_text(x + 300, y + 54, title, "head", "middle"),
        ]
        parts.extend(
            svg_text(x + 300, y + 104 + line * 38, value, "body", "middle")
            for line, value in enumerate(detail)
        )
    for route in (
        "M626,142 H654",
        "M960,274 V310",
        "M654,442 H626",
        "M320,574 V610",
        "M626,742 H654",
    ):
        parts.append(
            f'<path class="connector" d="{route}" fill="none" stroke="#0072B2" '
            'stroke-width="2" marker-end="url(#arrow-blue)"/>'
        )
    for line, value in enumerate(
        (
            "Roles: ontology-map.json",
            f"{len(PYTHON7)} Python checks | {len(GODOT6)} Godot families | {len(DISCLOSURE7)} DISC rules",
            "Missing checks: unreported, not pass",
            "Authored structure, not model state",
        )
    ):
        parts.append(svg_text(640, 922 + line * 38, value, "small", "middle"))
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def comparison_svg(data: dict[str, Any]) -> str:
    width, height = 1280, 1362
    parts = svg_header(
        width,
        height,
        "TRACE-RPG frozen comparison",
        "Independent 60-case by 3-arm comparison with normal, boundary and malformed strata. Unsafe and semantic mismatch are separate categorical counts; sparse check cells remain unreported.",
        "fig:signal-comparison",
    )
    parts += [
        svg_text(24, 48, "FROZEN INDEPENDENT", "title"),
        svg_text(24, 92, "COMPARISON | 60 INPUTS × 3 ARMS", "title"),
        svg_text(24, 136, "Unsafe ≠ semantic mismatch | no time trend", "subtitle"),
        svg_text(24, 178, "A/D: allow / deny", "small"),
        svg_text(600, 178, "Checks P/F: recorded pass / fail only", "small"),
    ]
    labels = {
        "unchecked_isolated": ("UNCHECKED", "#FBECEC"),
        "general_rule": ("GENERAL", "#E8F5EF"),
        "ontology_gate": ("ONTOLOGY", "#EAF4FA"),
    }
    # One row per arm/stratum gives every value a real padded table cell.
    x0, table_y, header_h, row_h = 24, 208, 76, 68
    widths = (220, 244, 164, 160, 176, 268)
    headings = ("Arm", "Input cases", "A/D", "Unsafe", "Mismatch", "Checks P/F")
    cursor = x0
    for cell_w, heading in zip(widths, headings):
        parts.append(svg_box(cursor, table_y, cell_w, header_h, "#F4F5F6"))
        parts.append(svg_text(cursor + cell_w / 2, table_y + 48, heading, "label", "middle"))
        cursor += cell_w
    for arm_index, arm in enumerate(ARMS):
        for stratum_index, (_, name) in enumerate(STRATA):
            cell = data["frozen_comparison"]["cells"][arm][name]
            check_label = (
                f"{cell['checks']['pass']} / {cell['checks']['fail']}"
                if cell["checks"]["report_status"] == "reported"
                else "unreported"
            )
            values = (
                labels[arm][0],
                f"{name.capitalize()}  n={cell['n']}",
                f"{cell['outcome']['allowed']} / {cell['outcome']['denied']}",
                str(cell["unsafe"]),
                str(cell["mismatch"]),
                check_label,
            )
            y = table_y + header_h + (arm_index * 3 + stratum_index) * row_h
            cursor = x0
            for cell_w, value in zip(widths, values):
                parts.append(svg_box(cursor, y, cell_w, row_h, labels[arm][1]))
                parts.append(svg_text(cursor + cell_w / 2, y + 44, value, "cell", "middle"))
                cursor += cell_w
    chart_y = 928
    parts += [
        svg_box(24, chart_y, 1232, 288, "#F7F7F5"),
        svg_text(52, chart_y + 50, "UNSAFE VS SEMANTIC MISMATCH", "head"),
        svg_text(52, chart_y + 94, "Case counts; horizontal scale 0 to 60", "small"),
        svg_text(764, chart_y + 94, "Red = unsafe   Blue = mismatch", "small"),
    ]
    for index, arm in enumerate(ARMS):
        group_x, track_w = 52 + index * 400, 306
        parts.append(svg_text(group_x, chart_y + 140, labels[arm][0].capitalize(), "label"))
        for series, (metric, color) in enumerate((("unsafe", "#B54747"), ("mismatch", "#0072B2"))):
            value = sum(data["frozen_comparison"]["cells"][arm][name][metric] for _, name in STRATA)
            bar_y = chart_y + 166 + series * 40
            bar_w = int(track_w * value / 60)
            parts.append(svg_box(group_x, bar_y, track_w, 20, "#FFFFFF"))
            if value:
                parts.append(
                    svg_box(group_x, bar_y, bar_w, 20, color, color, class_name="data-mark")
                )
            parts.append(svg_text(group_x + track_w + 12, bar_y + 20, str(value), "small"))
        for tick in (0, 30, 60):
            tx = group_x + track_w * tick / 60
            parts.append(svg_text(int(tx), chart_y + 266, str(tick), "small", "middle"))
    parts += [
        svg_text(24, 1258, "General = ontology: 60 equal cases", "note"),
        svg_text(24, 1298, "General / ontology / unchecked:", "note"),
        svg_text(24, 1338, "unsafe = 0 / 0 / 51; mismatch = 0 / 0 / 60", "note"),
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def convert(svg_path: Path, stem: str) -> None:
    rsvg = shutil.which("rsvg-convert")
    ps2pdf = shutil.which("ps2pdf")
    require(rsvg and ps2pdf, "required converters unavailable: rsvg-convert and ps2pdf")
    with tempfile.TemporaryDirectory(prefix="signal-figure-") as temp_dir:
        temp = Path(temp_dir)
        png = temp / "figure.png"
        eps = temp / "figure.eps"
        pdf = temp / "figure.pdf"
        subprocess.run(
            [rsvg, "-f", "png", "-o", str(png), str(svg_path)], check=True, capture_output=True
        )
        subprocess.run(
            [rsvg, "-f", "eps", "-o", str(eps), str(svg_path)], check=True, capture_output=True
        )
        with eps.open("a", encoding="utf-8") as handle:
            handle.write(f"\n[ /Title (source-sha256:{sha(svg_path)}) /DOCINFO pdfmark\n")
        subprocess.run(
            [
                ps2pdf,
                "-dEPSCrop",
                "-dOmitInfoDate=true",
                "-dOmitID=true",
                "-dOmitXMP=true",
                str(eps),
                str(pdf),
            ],
            check=True,
            capture_output=True,
        )
        (FIGURES / f"{stem}.png").write_bytes(png.read_bytes())
        (FIGURES / f"{stem}.pdf").write_bytes(pdf.read_bytes())


def outputs(data: dict[str, Any]) -> dict[Path, str]:
    return {
        REFERENCE: json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        FIGURES / "fig_signal_mechanism.svg": mechanism_svg(),
        FIGURES / "fig_signal_comparison.svg": comparison_svg(data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify derived JSON/SVG outputs without rewriting them",
    )
    args = parser.parse_args()
    data = build_reference(load_inputs())
    expected = outputs(data)
    if args.check:
        for path, content in expected.items():
            require(path.is_file(), f"missing generated output: {path}")
            require(path.read_text(encoding="utf-8") == content, f"generated output drift: {path}")
            if path.suffix == ".svg":
                ET.parse(path)
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "mode": "check",
                    "normal_boundary_malformed_per_arm": [48, 4, 8],
                    "general_ontology_equal": 60,
                    "unsafe": [0, 0, 51],
                    "mismatch": [0, 0, 60],
                },
                sort_keys=True,
            )
        )
        return 0
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    for path, content in expected.items():
        path.write_text(content, encoding="utf-8", newline="\n")
        if path.suffix == ".svg":
            ET.parse(path)
    convert(FIGURES / "fig_signal_mechanism.svg", "fig_signal_mechanism")
    convert(FIGURES / "fig_signal_comparison.svg", "fig_signal_comparison")
    print(
        json.dumps(
            {
                "status": "PASS",
                "normal_boundary_malformed_per_arm": [48, 4, 8],
                "general_ontology_equal": 60,
                "unsafe": [0, 0, 51],
                "mismatch": [0, 0, 60],
                "outputs": [
                    str(path.relative_to(ROOT))
                    for path in (
                        *expected,
                        FIGURES / "fig_signal_mechanism.png",
                        FIGURES / "fig_signal_mechanism.pdf",
                        FIGURES / "fig_signal_comparison.png",
                        FIGURES / "fig_signal_comparison.pdf",
                    )
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
