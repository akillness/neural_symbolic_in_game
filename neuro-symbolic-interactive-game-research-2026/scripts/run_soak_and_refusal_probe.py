#!/usr/bin/env python3
"""Run the separate Sealed Lighthouse refusal-coverage and headless soak probe.

This runner stages a disposable copy of `game-track/godot/`, imports assets in
headless Godot 4.x, executes `scenes/soak_and_refusal_probe.tscn`, revalidates
all refusal-coverage, state-isolation, timing, and memory-stability invariants in
Python, and writes artifacts to:
`game-track/godot/docs/soak-and-refusal-probe-v1/{results.json,summary.md}`.

It does not modify `SL-PLAY-EVAL-001`, `SL-BALANCE-PROBE-001`, or any frozen
evidence directory.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from scripts.run_playable_evaluation import (
        EXACT_TERMINAL_HASH,
        GODOT_PROJECT,
        SANDBOXED_MACOS_HOST_ERROR,
        _run_godot,
        atomic_write,
        find_godot_4,
        stage_project,
    )
except ModuleNotFoundError:  # Direct `python scripts/...` execution.
    from run_playable_evaluation import (
        EXACT_TERMINAL_HASH,
        GODOT_PROJECT,
        SANDBOXED_MACOS_HOST_ERROR,
        _run_godot,
        atomic_write,
        find_godot_4,
        stage_project,
    )

PROBE_ID = "SL-SOAK-REFUSAL-PROBE-001"
DEFAULT_OUTPUT_DIR = GODOT_PROJECT / "docs" / "soak-and-refusal-probe-v1"
EXPECTED_CODES = (
    "FORBIDDEN_DISCLOSURE",
    "MISSING_REQUIRED_OBJECT",
    "NPC_DOES_NOT_KNOW_FACT",
    "OBJECT_NOT_PRESENT",
    "OBJECT_NOT_REACHABLE",
    "QUEST_STAGE_PRECONDITION",
    "STAGE_GATED_DISCLOSURE",
    "UNKNOWN_ACTOR",
    "UNKNOWN_OPERATION",
)
NEWLY_EXERCISED_CODES = ("OBJECT_NOT_REACHABLE", "QUEST_STAGE_PRECONDITION")


def validate_probe_report(report: Mapping[str, Any], *, expected_ticks: int) -> None:
    """Fail closed if any refusal-coverage or soak invariant is violated."""
    if report.get("probe_id") != PROBE_ID or report.get("engineering_only") is not True:
        raise ValueError("probe identity or engineering_only flag drifted")
    if report.get("execution_status") != "OBSERVED_ENGINE_RUN":
        raise ValueError("probe did not report OBSERVED_ENGINE_RUN")
    engine = report.get("engine", {})
    if engine.get("name") != "Godot" or engine.get("headless") is not True:
        raise ValueError(f"probe did not run headlessly in Godot: {engine!r}")
    if report.get("canonical_terminal_sha256") != EXACT_TERMINAL_HASH:
        raise ValueError("canonical terminal hash drifted")
    if report.get("passed") is not True or report.get("failures"):
        raise ValueError(f"probe reported failures: {report.get('failures')!r}")

    refusal = report["refusal_code_coverage"]
    if tuple(sorted(str(c) for c in refusal["exercised_codes"])) != EXPECTED_CODES:
        raise ValueError(f"exercised refusal codes mismatch: {refusal['exercised_codes']!r}")
    if (
        int(refusal["exercised_count"]) != int(refusal["implemented_count"])
        or int(refusal["exercised_count"]) != 9
    ):
        raise ValueError(f"refusal code coverage not 9/9: {refusal!r}")
    if refusal.get("missing_codes"):
        raise ValueError(f"missing refusal codes: {refusal['missing_codes']!r}")
    if refusal.get("all_cases_state_isolated") is not True:
        raise ValueError("refusal battery had non-isolated state")
    if refusal.get("all_cases_trace_consistent") is not True:
        raise ValueError("refusal battery had EvaluationTrace mismatch")

    observed_by_code: dict[str, list[dict[str, Any]]] = {}
    for row in refusal["cases"]:
        if row.get("passed") is not True:
            raise ValueError(f"refusal case failed: {row!r}")
        for code in row["observed_codes"]:
            observed_by_code.setdefault(str(code), []).append(row)
    for code in NEWLY_EXERCISED_CODES:
        if code not in observed_by_code:
            raise ValueError(f"newly targeted code not exercised: {code}")

    soak = report["soak"]
    if int(soak["ticks_executed"]) != expected_ticks or int(soak["ticks_executed"]) < 1000:
        raise ValueError(f"unexpected soak tick count: {soak['ticks_executed']}")
    counts = soak["counts"]
    if int(counts["refusals_state_isolated"]) != int(counts["refusals"]):
        raise ValueError("soak refusal state isolation mismatch")
    if int(counts["trace_consistent"]) != int(counts["trace_checks"]):
        raise ValueError("soak EvaluationTrace consistency mismatch")
    if int(counts["terminal_hash_matches"]) != int(soak["episodes_completed"]):
        raise ValueError("soak terminal hash invariance mismatch")
    for code in NEWLY_EXERCISED_CODES:
        if code not in counts["exercised_refusal_codes"]:
            raise ValueError(f"soak did not exercise {code}")


def render_summary_markdown(report: Mapping[str, Any]) -> str:
    refusal = report["refusal_code_coverage"]
    soak = report["soak"]
    counts = soak["counts"]
    timing = soak["timing_ms"]
    mem = soak["memory"]
    rss = mem["resident_rss_kib"]
    static_mem = mem["godot_static_memory_bytes"]
    monitors = mem["godot_monitors"]

    lines = [
        "# Sealed Lighthouse — Refusal Coverage & Headless Soak Probe",
        "",
        f"- **Probe ID**: `{report['probe_id']}`",
        f"- **Status**: **{'PASS' if report['passed'] else 'FAIL'}** (`{report['execution_status']}`)",
        f"- **Engine**: Godot `{report['engine']['version']}` (`display_server={report['engine']['display_server']}`, `os={report['engine']['os']}`)",
        f"- **Canonical Terminal SHA-256**: `{report['canonical_terminal_sha256']}`",
        "",
        "> Claim boundary: Headless Godot engine conformance, refusal-code coverage, and deterministic step/commit timing + memory stability soak only. Not evidence for human gameplay, G3/G4/G7, usability, immersion, or LLM efficacy.",
        "",
        "## 1. Refusal-Code Coverage (Previously Unexercised + Full Matrix)",
        "",
        f"- **Implemented / Exercised**: `{refusal['exercised_count']}/{refusal['implemented_count']}` (`100%` of `IMPLEMENTED_CODES`)",
        "- **Newly Exercised Codes**: `OBJECT_NOT_REACHABLE`, `QUEST_STAGE_PRECONDITION`",
        f"- **State-Hash Isolation**: `{refusal['isolated_cases']}/{refusal['total_cases']}` (`all_cases_state_isolated={refusal['all_cases_state_isolated']}`)",
        f"- **EvaluationTrace Mirror Consistency**: `{refusal['trace_consistent_cases']}/{refusal['total_cases']}` (`all_cases_trace_consistent={refusal['all_cases_trace_consistent']}`)",
        "",
        "| Case ID | Expected Code | Observed Codes | Mechanism | Isolated | Trace Consistent | Latency (ms) |",
        "| --- | --- | --- | --- | --- | --- | ---: |",
    ]
    for row in refusal["cases"]:
        lines.append(
            f"| `{row['case_id']}` | `{row['expected_code']}` | "
            f"`{','.join(row['observed_codes'])}` | {row['mechanism']} | "
            f"{'PASS' if row['state_isolated'] else 'FAIL'} | "
            f"{'PASS' if row['trace_consistent'] else 'FAIL'} | "
            f"{row['latency_ms']:.3f} |"
        )

    lines.extend(
        [
            "",
            "Supplementary note: `DISCLOSURE_TEMPLATE_UNAVAILABLE` is a defensive guard in `_reveal_hint` triggered only if `EvidenceCaptureRunner.CAPTURE_SPECS` lacks `sl-rc-003-authorized-hint`; it remains structurally unreachable under intact source assets.",
            "",
            "## 2. Deterministic Headless Soak Loop",
            "",
            f"- **Ticks Executed**: `{soak['ticks_executed']}` (`warmup_ticks={soak['warmup_ticks']}`, `steady_state_ticks={soak['steady_state_ticks']}`, `cycle_length={soak['cycle_length']}`)",
            f"- **Episodes Completed**: `{soak['episodes_completed']}` (`terminal_hash_matches={counts['terminal_hash_matches']}/{soak['episodes_completed']}`)",
            f"- **Commits / Refusals / World Events / Save-Loads**: `{counts['commits']}` / `{counts['refusals']}` (`{counts['refusals_state_isolated']}` isolated) / `{counts['world_events']}` / `{counts['save_loads']}`",
            f"- **EvaluationTrace Checks Consistent**: `{counts['trace_consistent']}/{counts['trace_checks']}`",
            f"- **Total Soak Wall Time**: `{soak['total_soak_elapsed_ms']:.3f} ms`",
            "",
            "### Step/Commit & Headless Frame Timing (ms, `Time.get_ticks_usec`)",
            "",
            "| Metric | Count | Min | Mean | p50 | p95 | p99 | Max |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for label, key in (
        ("`step_commit_all_ticks`", "step_commit_all_ticks"),
        ("`step_commit_steady_state` (post-warmup)", "step_commit_steady_state"),
        ("`commit_only_operations`", "commit_only_operations"),
        ("`frame_wall_all_ticks` (incl. tick-1 startup)", "frame_wall_all_ticks"),
        ("`frame_wall_steady_state` (post-warmup)", "frame_wall_steady_state"),
        ("`headless_frame_delta_all_ticks`", "headless_frame_delta_all_ticks"),
        ("`headless_frame_delta_steady_state`", "headless_frame_delta_steady_state"),
    ):
        stat = timing[key]
        lines.append(
            f"| {label} | {stat['count']} | {stat['min']:.3f} | {stat['mean']:.3f} | "
            f"{stat['p50']:.3f} | {stat['p95']:.3f} | {stat['p99']:.3f} | {stat['max']:.3f} |"
        )

    lines.extend(
        [
            "",
            "### Memory & Object Stability",
            "",
            f"- **OS Resident Set Size (`ps -o rss=`)**: pre-refusal `{rss['pre_refusal_battery']} KiB` -> pre-soak `{rss['pre_soak']} KiB` -> post-soak `{rss['post_soak']} KiB` (`soak_delta={rss['soak_delta_kib']} KiB` / `{rss['soak_delta_mib']:.3f} MiB`)",
            f"- **Godot Static Memory (all ticks)**: initial `{static_mem['all_ticks']['initial']:,} B`, min `{static_mem['all_ticks']['min']:,} B`, max `{static_mem['all_ticks']['max']:,} B`, final `{static_mem['all_ticks']['final']:,} B`, peak `{static_mem['peak_reported_bytes']:,} B`",
            f"- **Godot Static Memory (steady-state post-warmup)**: initial `{static_mem['steady_state']['initial']:,} B` -> final `{static_mem['steady_state']['final']:,} B` (`delta={static_mem['steady_state_delta_bytes']:+,} B`)",
            f"- **Godot Object / Node / Orphan Monitors**: objects steady-state `{monitors['object_count_steady_state']['initial']}` -> `{monitors['object_count_steady_state']['final']}` (`delta={monitors['object_count_steady_state_delta']:+d}`), nodes `{monitors['node_count']['min']}..{monitors['node_count']['max']}`, orphan nodes `{monitors['orphan_node_count']['min']}..{monitors['orphan_node_count']['max']}`",
            "",
            "| Tick | Static Memory (B) | Object Count | Node Count | Orphan Nodes |",
            "| ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for cp in mem["checkpoints"]:
        lines.append(
            f"| {cp['tick']} | {cp['static_memory_bytes']:,} | {cp['object_count']} | "
            f"{cp['node_count']} | {cp['orphan_node_count']} |"
        )
    lines.extend(
        [
            "",
            "Generated by `scripts/run_soak_and_refusal_probe.py` against `game-track/godot/scenes/soak_and_refusal_probe.tscn` on a disposable staged project copy.",
            "",
        ]
    )
    return "\n".join(lines)


def run_probe(*, godot: str, output_dir: Path, ticks: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="sealed-lighthouse-soak-refusal-") as directory:
        working = Path(directory)
        project = working / "project"
        logs = working / "logs"
        probe_path = working / "soak-and-refusal-probe.json"
        logs.mkdir()
        stage_project(GODOT_PROJECT, project)
        _run_godot(
            [
                godot,
                "--headless",
                "--editor",
                "--path",
                str(project),
                "--import",
                "--quit-after",
                "120",
                "--log-file",
                str(logs / "import.log"),
            ],
            label="fresh Godot project import",
            timeout=120,
            allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
        )
        _run_godot(
            [
                godot,
                "--headless",
                "--path",
                str(project),
                "--scene",
                "res://scenes/soak_and_refusal_probe.tscn",
                "--quit-after",
                str(max(ticks + 500, 3000)),
                "--log-file",
                str(logs / "soak-and-refusal-probe.log"),
                "--",
                "--output",
                str(probe_path),
                "--ticks",
                str(ticks),
            ],
            label="headless soak and refusal probe",
            timeout=120,
            allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
        )
        report = json.loads(probe_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise TypeError("probe output must be a JSON object")
    validate_probe_report(report, expected_ticks=ticks)
    json_bytes = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    md_bytes = render_summary_markdown(report).encode("utf-8")
    atomic_write(output_dir / "results.json", json_bytes)
    atomic_write(output_dir / "summary.md", md_bytes)
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", help="Explicit Godot 4 editor executable")
    parser.add_argument(
        "--ticks", type=int, default=1600, help="Deterministic soak tick count (default: 1600)"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for results.json and summary.md",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.ticks < 1000:
        raise ValueError("--ticks must be at least 1000")
    godot, version = find_godot_4(args.godot)
    output_dir = args.output_dir.expanduser().resolve()
    report = run_probe(godot=godot, output_dir=output_dir, ticks=args.ticks)
    refusal = report["refusal_code_coverage"]
    timing = report["soak"]["timing_ms"]
    rss = report["soak"]["memory"]["resident_rss_kib"]
    print(
        f"{PROBE_ID} PASS: refusal={refusal['exercised_count']}/{refusal['implemented_count']}, "
        f"ticks={report['soak']['ticks_executed']}, "
        f"step_commit_p95={timing['step_commit_steady_state']['p95']:.3f}ms, "
        f"frame_wall_p95={timing['frame_wall_steady_state']['p95']:.3f}ms, "
        f"rss_delta={rss['soak_delta_kib']}KiB, Godot {version}; output={output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
