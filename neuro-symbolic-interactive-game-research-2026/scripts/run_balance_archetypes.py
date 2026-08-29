#!/usr/bin/env python3
"""Run the Sealed Lighthouse balance/archetype probe and publish latest artifacts.

This driver stages a disposable Godot project, executes the deterministic
headless archetype battery (`scenes/balance_probe.tscn`), revalidates the
emitted counts in Python, and writes claim-bounded working artifacts:
`balance-archetypes.json`, `balance-archetypes.md`, and a deterministic SVG
chart under `game-track/godot/docs/latest/`.

Everything produced here is scripted engineering conformance. It is not
evidence for human balance perception, archetype viability (G3), fun or repeat
behavior (G7), usability, immersion, affect, or model/player efficacy.
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
        LATEST_DOCS,
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
        LATEST_DOCS,
        SANDBOXED_MACOS_HOST_ERROR,
        _run_godot,
        atomic_write,
        find_godot_4,
        stage_project,
    )

PROBE_ID = "SL-BALANCE-PROBE-001"
EXPECTED_ARCHETYPE_IDS = ("A-01", "A-02", "A-03", "A-04", "A-05")
EXPECTED_OPERATIONS = ("acquire_object", "install_lens", "reveal_hint")
CHART_WIDTH = 980
CHART_HEIGHT = 430
BAR_COLORS = {"commits": "#F2B84B", "refusals": "#D9685F", "observes": "#8FA3B2"}


def validate_probe(report: Mapping[str, Any]) -> None:
    """Fail closed when the probe payload drifts from its frozen contract."""
    if report.get("probe_id") != PROBE_ID or report.get("engineering_only") is not True:
        raise ValueError("probe identity or engineering_only flag drifted")
    if report.get("passed") is not True or report.get("failures"):
        raise ValueError(f"probe reported failures: {report.get('failures')}")
    if report.get("canonical_terminal_sha256") != EXACT_TERMINAL_HASH:
        raise ValueError("canonical terminal hash drifted")
    rows = report.get("archetypes")
    if (
        not isinstance(rows, list)
        or tuple(str(row.get("archetype_id")) for row in rows) != EXPECTED_ARCHETYPE_IDS
    ):
        raise ValueError("archetype battery identity drifted")

    refusals = sum(int(row["counts"]["refusals"]) for row in rows)
    isolated = sum(int(row["counts"]["refusals_state_isolated"]) for row in rows)
    forbidden_commits = sum(int(row["counts"]["forbidden_commits"]) for row in rows)
    aggregates = report["aggregates"]
    g2 = aggregates["g2_replacement_measurements"]
    operation_coverage = aggregates["operation_coverage"]
    checks = (
        (g2["rejected_action_state_hash_equality"]["refusals"] == refusals, "refusal totals"),
        (g2["rejected_action_state_hash_equality"]["isolated"] == isolated, "isolation totals"),
        (isolated == refusals, "refusal state isolation must be complete"),
        (
            g2["forbidden_disclosure_per_opportunity"]["committed"] == forbidden_commits == 0,
            "forbidden disclosure commits must be zero",
        ),
        (
            g2["canonical_episode_reachability"]["reached"] == len(rows),
            "semantic reachability totals",
        ),
        (
            g2["replay_terminal_hash_equality"]["matched"] == len(rows),
            "replay totals",
        ),
        (
            all(row["terminal"]["matches_canonical_semantic"] is True for row in rows),
            "semantic convergence",
        ),
        (
            all(row["replay"]["terminal_hash_matches"] is True for row in rows),
            "per-archetype replay",
        ),
        (
            tuple(sorted(operation_coverage["exercised"])) == EXPECTED_OPERATIONS,
            "implemented operation coverage",
        ),
        (
            operation_coverage["exercised_count"]
            == operation_coverage["implemented_count"]
            == len(EXPECTED_OPERATIONS),
            "implemented operation totals",
        ),
    )
    failed = [label for ok, label in checks if not ok]
    if failed:
        raise ValueError(f"probe aggregate revalidation failed: {failed}")


def render_markdown(report: Mapping[str, Any]) -> str:
    rows = report["archetypes"]
    aggregates = report["aggregates"]
    g2 = aggregates["g2_replacement_measurements"]
    coverage = aggregates["refusal_code_coverage"]
    lines = [
        "# 봉인된 등대 — 아키타입 밸런스 프로브 / Archetype Balance Probe",
        "",
        f"Probe ID: `{report['probe_id']}` · Status: **PASS (engineering conformance)**",
        "",
        (
            "> 범위: 스크립트된 아키타입 5종의 결정론적 실행 적합성과 레이아웃 근사 페이싱만 측정한다. "
            "사람 플레이어의 밸런스 체감, G3 생존성, G7 재미/반복, 사용성·몰입·정서·효능의 근거가 아니다."
        ),
        (
            "> Scope: deterministic conformance of five scripted archetypes plus layout-proxy pacing. "
            "Not evidence for human balance perception, G3 viability, G7 fun/repeat, usability, "
            "immersion, affect, or efficacy."
        ),
        "",
        "## 아키타입 실행 결과 / Archetype runs",
        "",
        (
            "| ID | 아키타입 | 연산 | 기록 | 보류 | 관찰 | 이동 근사 (m / s) | 최종 revision | "
            "의미 상태 = 정식 경로 |"
        ),
        "| --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- |",
    ]
    for row in rows:
        counts = row["counts"]
        pacing = row["pacing_proxy"]
        terminal = row["terminal"]
        lines.append(
            f"| {row['archetype_id']} | {row['name_ko']} | {counts['operations']} | "
            f"{counts['commits']} | {counts['refusals']} | {counts['observes']} | "
            f"{pacing['walk_distance_m']} m / {pacing['walk_time_s_at_walk_speed']} s | "
            f"{terminal['revision']} | "
            f"{'예' if terminal['matches_canonical_semantic'] else '아니오'} |"
        )
    lines.extend(
        [
            "",
            (
                "이동 근사는 상호작용 지점 간 직선 거리(`GoldenPathLayout`)를 WALK_SPEED "
                f"{report['walk_speed_mps']} m/s로 나눈 값이며, 읽기·판단 시간이 빠진 하한 근사다."
            ),
            "",
            "## G2 대체 지표 측정 / G2 replacement measurements",
            "",
            "| 지표 | 관측 | 목표 | 판정 |",
            "| --- | --- | --- | --- |",
            (
                f"| 정식 에피소드 도달률 | {g2['canonical_episode_reachability']['reached']}/"
                f"{g2['canonical_episode_reachability']['attempted']} | 1.0 | PASS |"
            ),
            (
                f"| 금지 공개 커밋/기회 | {g2['forbidden_disclosure_per_opportunity']['committed']}/"
                f"{g2['forbidden_disclosure_per_opportunity']['opportunities']} | 0.0 | PASS |"
            ),
            (
                f"| 보류 시 상태 해시 불변 | {g2['rejected_action_state_hash_equality']['isolated']}/"
                f"{g2['rejected_action_state_hash_equality']['refusals']} | 1.0 | PASS |"
            ),
            (
                f"| 연산 로그 재생 해시 일치 | {g2['replay_terminal_hash_equality']['matched']}/"
                f"{g2['replay_terminal_hash_equality']['replayed']} | 1.0 | PASS |"
            ),
            (
                f"| 거절 코드 커버리지 | {coverage['exercised_count']}/{coverage['implemented_count']} "
                "| 문서화 | 2건 구조적 미도달(사유 기록) |"
            ),
            "",
            "구조적으로 미도달한 코드 / structurally unexercised codes:",
            "",
        ]
    )
    for item in coverage["unexercised"]:
        lines.append(f"- `{item['code']}` — {item['reason']}")
    lines.extend(
        [
            "",
            "## 기계 속성 발견 / Machine-property findings",
            "",
        ]
    )
    for finding in aggregates["machine_properties"]:
        lines.append(
            f"- `{finding['property']}` ({finding['archetype_id']} step {finding['step_index']}): "
            f"의미 상태 변화 없음(semantic unchanged), UI 가드 — {finding['ui_guard']}"
        )
    lines.extend(
        [
            "",
            (
                "중복 커밋은 기계 수준에서 revision만 증가시키고 의미 상태를 바꾸지 않는다. "
                "라이브 어댑터 승인 전 영속 이벤트 멱등성이 여전히 필요하다(EG-I05)."
            ),
            "",
            (
                "차트: [balance-archetypes.svg](balance-archetypes.svg) · 원자료: "
                "[balance-archetypes.json](balance-archetypes.json)"
            ),
            "",
            "Generated by `scripts/run_balance_archetypes.py` from a fresh disposable project copy.",
            "",
        ]
    )
    return "\n".join(lines)


def render_chart(report: Mapping[str, Any]) -> str:
    """Deterministic SVG: per-archetype counts plus the walk-time proxy."""
    rows = report["archetypes"]
    max_count = max(
        max(
            int(row["counts"]["commits"]),
            int(row["counts"]["refusals"]),
            int(row["counts"]["observes"]),
        )
        for row in rows
    )
    max_walk = max(float(row["pacing_proxy"]["walk_time_s_at_walk_speed"]) for row in rows)
    left, top = 70, 64
    panel_width, panel_height = 520, 300
    group_width = panel_width / len(rows)
    bar_width = 26
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_WIDTH}" '
            f'height="{CHART_HEIGHT}" viewBox="0 0 {CHART_WIDTH} {CHART_HEIGHT}" '
            'font-family="sans-serif">'
        ),
        f'<rect width="{CHART_WIDTH}" height="{CHART_HEIGHT}" fill="#141A21"/>',
        (
            '<text x="24" y="30" fill="#F2B84B" font-size="18">아키타입 밸런스 프로브 — '
            "기록/보류/관찰과 이동 근사 (SL-BALANCE-PROBE-001)</text>"
        ),
        (
            '<text x="24" y="50" fill="#8FA3B2" font-size="12">scripted engineering conformance '
            "only · not human balance, G3, G7, usability, or efficacy evidence</text>"
        ),
    ]
    for index, (label, color) in enumerate(BAR_COLORS.items()):
        legend_x = left + index * 150
        korean = {"commits": "기록", "refusals": "보류", "observes": "관찰"}[label]
        parts.append(f'<rect x="{legend_x}" y="{top - 6}" width="12" height="12" fill="{color}"/>')
        parts.append(
            f'<text x="{legend_x + 18}" y="{top + 5}" fill="#D9D3C4" font-size="12">'
            f"{korean} {label}</text>"
        )
    axis_bottom = top + 20 + panel_height
    for tick in range(max_count + 1):
        tick_y = axis_bottom - (tick / max_count) * panel_height
        parts.append(
            f'<line x1="{left - 8}" y1="{tick_y:.1f}" x2="{left + panel_width}" '
            f'y2="{tick_y:.1f}" stroke="#26303A" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{left - 14}" y="{tick_y + 4:.1f}" fill="#8FA3B2" font-size="11" '
            f'text-anchor="end">{tick}</text>'
        )
    for row_index, row in enumerate(rows):
        counts = row["counts"]
        group_x = left + row_index * group_width
        for bar_index, (key, color) in enumerate(BAR_COLORS.items()):
            value = int(counts[key])
            bar_height = (value / max_count) * panel_height
            bar_x = group_x + 8 + bar_index * (bar_width + 4)
            bar_y = axis_bottom - bar_height
            parts.append(
                f'<rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_width}" '
                f'height="{bar_height:.1f}" fill="{color}"/>'
            )
            parts.append(
                f'<text x="{bar_x + bar_width / 2:.1f}" y="{bar_y - 4:.1f}" fill="#D9D3C4" '
                f'font-size="11" text-anchor="middle">{value}</text>'
            )
        parts.append(
            f'<text x="{group_x + group_width / 2:.1f}" y="{axis_bottom + 18}" fill="#D9D3C4" '
            f'font-size="12" text-anchor="middle">{row["archetype_id"]}</text>'
        )
        parts.append(
            f'<text x="{group_x + group_width / 2:.1f}" y="{axis_bottom + 34}" fill="#8FA3B2" '
            f'font-size="10" text-anchor="middle">{row["name_ko"]}</text>'
        )
    walk_left = left + panel_width + 70
    walk_width = CHART_WIDTH - walk_left - 40
    parts.append(
        f'<text x="{walk_left}" y="{top + 4}" fill="#D9D3C4" font-size="13">이동 근사 시간 '
        "(직선 하한, 초)</text>"
    )
    parts.append(
        f'<text x="{walk_left}" y="{top + 20}" fill="#8FA3B2" font-size="10">B-002 루프 목표 '
        "60–120 s 대비 이동은 소수 비중 — 잔여는 읽기·판단 시간</text>"
    )
    walk_axis_top = top + 36
    walk_row_height = (axis_bottom - walk_axis_top) / len(rows)
    for row_index, row in enumerate(rows):
        seconds = float(row["pacing_proxy"]["walk_time_s_at_walk_speed"])
        bar_y = walk_axis_top + row_index * walk_row_height + 8
        bar_length = (seconds / max_walk) * (walk_width - 120)
        parts.append(
            f'<text x="{walk_left}" y="{bar_y + 12:.1f}" fill="#D9D3C4" font-size="11">'
            f"{row['archetype_id']}</text>"
        )
        parts.append(
            f'<rect x="{walk_left + 48}" y="{bar_y:.1f}" width="{bar_length:.1f}" height="16" '
            'fill="#4A7B96"/>'
        )
        parts.append(
            f'<text x="{walk_left + 54 + bar_length:.1f}" y="{bar_y + 12:.1f}" fill="#8FA3B2" '
            f'font-size="11">{seconds} s</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def run_probe(*, godot: str, output_dir: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="sealed-lighthouse-balance-") as directory:
        working = Path(directory)
        project = working / "project"
        logs = working / "logs"
        probe_path = working / "balance-probe.json"
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
                "res://scenes/balance_probe.tscn",
                "--quit-after",
                "120",
                "--log-file",
                str(logs / "balance-probe.log"),
                "--",
                "--output",
                str(probe_path),
            ],
            label="headless balance/archetype probe",
            timeout=60,
            allowed_errors=SANDBOXED_MACOS_HOST_ERROR,
        )
        report = json.loads(probe_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise TypeError("balance probe output must be a JSON object")
    validate_probe(report)
    payload = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    atomic_write(output_dir / "balance-archetypes.json", payload)
    atomic_write(output_dir / "balance-archetypes.md", render_markdown(report).encode("utf-8"))
    atomic_write(output_dir / "balance-archetypes.svg", render_chart(report).encode("utf-8"))
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--godot", help="Explicit Godot 4 editor executable")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    godot, version = find_godot_4(args.godot)
    report = run_probe(godot=godot, output_dir=LATEST_DOCS)
    rows = report["archetypes"]
    print(
        f"{PROBE_ID} PASS: archetypes {len(rows)}/5, refusal isolation "
        f"{report['aggregates']['g2_replacement_measurements']['rejected_action_state_hash_equality']['isolated']}"
        f"/{report['aggregates']['g2_replacement_measurements']['rejected_action_state_hash_equality']['refusals']}, "
        f"Godot {version}; output={LATEST_DOCS}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
