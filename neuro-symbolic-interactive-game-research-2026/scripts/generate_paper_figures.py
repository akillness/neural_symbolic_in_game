#!/usr/bin/env python3
"""Generate TRACE-RPG paper's reproducible SVG figures.

The drawings use only SVG primitives and Python's standard library. Their
labels intentionally distinguish mechanism conformance in designed fixtures
from future, unmeasured efficacy claims.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "paper" / "latex" / "figures"

INK = "#202124"
MUTED = "#5F6368"
LIGHT_GRAY = "#F7F7F5"
BORDER = "#C9CDD1"
BLUE = "#0072B2"
SKY = "#56B4E9"
ORANGE = "#A05A00"
GREEN = "#007A59"
GRAY = "#666A6D"
PALE_BLUE = "#EAF4FA"
PALE_ORANGE = "#FFF2DD"
PALE_GREEN = "#E8F5EF"
PALE_GRAY = "#EEF0F2"


def svg_header(width: int, height: int, title: str, description: str) -> list[str]:
    """Return a common Classic Academic SVG header and marker definitions."""

    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
            'aria-labelledby="svg-title svg-desc">'
        ),
        f'  <title id="svg-title">{escape(title)}</title>',
        f'  <desc id="svg-desc">{escape(description)}</desc>',
        "  <defs>",
        *[
            (
                f'    <marker id="arrow-{name}" markerWidth="10" markerHeight="10" '
                'refX="8" refY="3" orient="auto" markerUnits="strokeWidth">'
                f'<path d="M0,0 L0,6 L9,3 z" fill="{color}"/></marker>'
            )
            for name, color in (
                ("blue", BLUE),
                ("orange", ORANGE),
                ("green", GREEN),
                ("gray", GRAY),
            )
        ],
        "    <style>",
        "      text { font-family: Helvetica, Arial, sans-serif; fill: #202124; }",
        "      .section { font-size: 32px; font-weight: 700; }",
        "      .box-title { font-size: 30px; font-weight: 700; }",
        "      .body { font-size: 29px; font-weight: 400; }",
        "      .small { font-size: 28px; font-weight: 400; }",
        "      .note { font-size: 28px; font-style: italic; fill: #5F6368; }",
        "      .arrow-label { font-size: 28px; font-weight: 700; }",
        "    </style>",
        "  </defs>",
        f'  <rect x="0" y="0" width="{width}" height="{height}" fill="#FFFFFF"/>',
    ]


def rect(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    fill: str = "#FFFFFF",
    stroke: str = BORDER,
    stroke_width: int = 2,
    radius: int = 7,
    dash: str | None = None,
) -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'  <rect x="{x}" y="{y}" width="{width}" height="{height}" '
        f'rx="{radius}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{stroke_width}"{dash_attr}/>'
    )


def line(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    *,
    color: str,
    marker: str | None = None,
    width: int = 3,
    dash: str | None = None,
) -> str:
    marker_attr = f' marker-end="url(#arrow-{marker})"' if marker else ""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'  <line class="connector" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="{width}" fill="none"'
        f"{marker_attr}{dash_attr}/>"
    )


def path(
    d: str,
    *,
    color: str,
    marker: str | None = None,
    width: int = 3,
    dash: str | None = None,
) -> str:
    marker_attr = f' marker-end="url(#arrow-{marker})"' if marker else ""
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'  <path class="connector" d="{d}" stroke="{color}" stroke-width="{width}" '
        f'fill="none"{marker_attr}{dash_attr}/>'
    )


def polygon(points: str, *, fill: str, stroke: str, stroke_width: int = 2) -> str:
    return (
        f'  <polygon points="{points}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{stroke_width}"/>'
    )


def text(
    x: int,
    y: int,
    value: str,
    *,
    css_class: str = "body",
    anchor: str = "start",
    fill: str | None = None,
    rotate: int | None = None,
) -> str:
    fill_attr = f' fill="{fill}"' if fill else ""
    transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
    return (
        f'  <text x="{x}" y="{y}" class="{css_class}" text-anchor="{anchor}"'
        f"{fill_attr}{transform}>{escape(value)}</text>"
    )


def multiline(
    x: int,
    y: int,
    values: list[str] | tuple[str, ...],
    *,
    css_class: str = "body",
    anchor: str = "middle",
    line_height: int = 28,
    fill: str | None = None,
) -> str:
    fill_attr = f' fill="{fill}"' if fill else ""
    tspans = []
    for index, value in enumerate(values):
        dy = "0" if index == 0 else str(line_height)
        tspans.append(f'<tspan x="{x}" dy="{dy}">{escape(value)}</tspan>')
    return (
        f'  <text x="{x}" y="{y}" class="{css_class}" '
        f'text-anchor="{anchor}"{fill_attr}>' + "".join(tspans) + "</text>"
    )


def band(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    accent: str,
    title_value: str,
    subtitle: str | None = None,
) -> list[str]:
    items = [
        rect(x, y, width, height, fill=LIGHT_GRAY, stroke=BORDER, radius=5),
        f'  <rect x="{x}" y="{y}" width="9" height="{height}" fill="{accent}"/>',
        text(x + 25, y + 35, title_value, css_class="section"),
    ]
    if subtitle:
        items.append(text(x + 25, y + 64, subtitle, css_class="small", fill=MUTED))
    return items


def component_box(
    x: int,
    y: int,
    width: int,
    height: int,
    *,
    accent: str,
    title_value: str,
    body_lines: tuple[str, ...] = (),
    fill: str = "#FFFFFF",
    dashed: bool = False,
) -> list[str]:
    items = [
        rect(
            x,
            y,
            width,
            height,
            fill=fill,
            stroke=accent,
            radius=7,
            dash="8 6" if dashed else None,
        ),
        f'  <rect x="{x}" y="{y}" width="8" height="{height}" rx="4" fill="{accent}"/>',
        text(x + width // 2 + 4, y + 33, title_value, css_class="box-title", anchor="middle"),
    ]
    if body_lines:
        items.append(
            multiline(
                x + width // 2 + 4,
                y + 66,
                body_lines,
                css_class="small",
                line_height=29,
            )
        )
    return items


def arrow_label(
    x: int,
    y: int,
    value: str,
    *,
    color: str,
    width: int,
) -> list[str]:
    """Return a connector label with an opaque clearance shield."""

    return [
        '  <g class="connector-label" data-line-clearance="shielded">',
        (
            f'    <rect class="label-shield" x="{x - width // 2}" y="{y - 28}" '
            f'width="{width}" height="38" rx="2" fill="#FFFFFF" stroke="#FFFFFF"/>'
        ),
        (
            f'    <text x="{x}" y="{y}" class="arrow-label" text-anchor="middle" '
            f'fill="{color}">{escape(value)}</text>'
        ),
        "  </g>",
    ]


def vertical_label_chip(
    x: int,
    y: int,
    value: str,
    *,
    color: str,
    height: int,
) -> list[str]:
    """Return a vertical label that interrupts, rather than overlaps, a rule."""

    return [
        '  <g class="connector-label" data-line-clearance="shielded">',
        (
            f'    <rect class="label-shield" x="{x - 24}" y="{y - height // 2}" '
            f'width="48" height="{height}" rx="3" fill="#FFFFFF" stroke="#FFFFFF"/>'
        ),
        (
            f'    <text x="{x}" y="{y}" class="section" text-anchor="middle" '
            f'fill="{color}" transform="rotate(-90 {x} {y})">{escape(value)}</text>'
        ),
        "  </g>",
    ]


def architecture_svg() -> str:
    width, height = 1440, 700
    items = svg_header(
        width,
        height,
        "TRACE-RPG trust-boundary architecture",
        (
            "A stochastic proposal is parsed by a strict adapter and checked by an encoded "
            "state-relative validator before commit, bounded repair, or unchanged fallback. "
            "The validator reads canonical state and stored policy; the repair callback "
            "rho consumes only the prior candidate and the structured error set. "
            "Soft context z_t is separate from canonical authority c_t."
        ),
    )

    items += band(
        25,
        20,
        1390,
        145,
        accent=GRAY,
        title_value="NON-AUTHORITATIVE CONTEXT  z_t",
        subtitle="May condition a proposal; cannot directly mutate canonical state",
    )
    items += component_box(
        55,
        100,
        285,
        48,
        accent=GRAY,
        title_value="Retrieval / memory",
    )
    items += component_box(
        375,
        100,
        285,
        48,
        accent=GRAY,
        title_value="Soft narrative scores",
    )
    items += component_box(
        695,
        100,
        285,
        48,
        accent=GRAY,
        title_value="Model rationale",
    )
    items += component_box(
        1015,
        100,
        355,
        48,
        accent=GRAY,
        title_value="Future affect estimate",
        dashed=True,
    )

    items += band(
        25,
        185,
        1390,
        320,
        accent=BLUE,
        title_value="PROPOSAL–VALIDATION–COMMIT PATH",
        subtitle="Solid arrows are current deterministic data/control flow; dashed arrows are bounded retry",
    )
    items += component_box(
        55,
        265,
        190,
        105,
        accent=GRAY,
        title_value="Proposal",
        body_lines=("response a_j", "untrusted"),
        fill=PALE_GRAY,
    )
    items += component_box(
        290,
        265,
        220,
        105,
        accent=BLUE,
        title_value="Strict adapter",
        body_lines=("response schema", "exact JSON types"),
        fill=PALE_BLUE,
    )
    items += component_box(
        555,
        255,
        250,
        125,
        accent=BLUE,
        title_value="Encoded validator",
        body_lines=("V(c_t, a_j)", "hard predicates + E_j"),
        fill=PALE_BLUE,
    )
    items += component_box(
        905,
        225,
        190,
        100,
        accent=GREEN,
        title_value="COMMIT",
        body_lines=("atomic T(c_t,a_j)", "only if valid"),
        fill=PALE_GREEN,
    )
    items += component_box(
        1170,
        225,
        205,
        100,
        accent=GREEN,
        title_value="Game bridge",
        body_lines=("versioned JSON", "committed event"),
        fill=PALE_GREEN,
    )
    items += component_box(
        895,
        375,
        210,
        100,
        accent=ORANGE,
        title_value="REPAIR",
        body_lines=("rho(a_j, E_j), j < K", "never reads c_t"),
        fill=PALE_ORANGE,
    )
    items += component_box(
        1170,
        375,
        205,
        100,
        accent=GRAY,
        title_value="FALLBACK",
        body_lines=("c_(t+1) = c_t", "when budget ends"),
        fill=PALE_GRAY,
    )

    items.append(line(245, 318, 290, 318, color=GRAY, marker="gray"))
    items.append(line(510, 318, 555, 318, color=BLUE, marker="blue"))
    items.append(path("M805 292 H855 V275 H905", color=GREEN, marker="green"))
    items += arrow_label(855, 268, "valid", color=GREEN, width=76)
    items.append(line(1095, 275, 1170, 275, color=GREEN, marker="green"))
    items.append(path("M805 340 H850 V425 H895", color=ORANGE, marker="orange"))
    items += arrow_label(825, 405, "invalid, j < K", color=ORANGE, width=130)
    items.append(path("M805 352 H825 V498 H1125 V425 H1170", color=GRAY, marker="gray"))
    items += arrow_label(1030, 503, "invalid, j = K", color=GRAY, width=150)
    items.append(
        path(
            "M895 442 H860 V482 H150 V370",
            color=ORANGE,
            marker="orange",
            dash="10 7",
        )
    )
    items += arrow_label(525, 478, "repaired candidate  a_(j+1)", color=ORANGE, width=245)

    items += band(
        25,
        525,
        1390,
        150,
        accent=GREEN,
        title_value="CANONICAL AUTHORITY  c_t = (G_t, q_t)",
        subtitle="Canonical owner supplies typed world state and stored policy; record history h_(<t) is kept separately and is never read by validation",
    )
    items += component_box(
        55,
        608,
        365,
        48,
        accent=GREEN,
        title_value="Prior canonical state  c_t",
        fill=PALE_GREEN,
    )
    items += component_box(
        495,
        608,
        380,
        48,
        accent=BLUE,
        title_value="Externally supplied policy  q_t",
        fill=PALE_BLUE,
    )
    items += component_box(
        970,
        608,
        405,
        48,
        accent=GREEN,
        title_value="Final canonical state  c_(t+1)",
        fill=PALE_GREEN,
    )
    # Route the successful branch around the right edge of the authority band;
    # the prior path crossed the long band subtitle at x=1140.
    items.append(path("M1272 325 H1398 V632 H1375", color=GREEN, marker="green"))
    items.append(path("M1270 475 V608", color=GRAY, marker="gray"))
    items.append(line(685, 608, 685, 380, color=BLUE, marker="blue"))
    items += arrow_label(700, 445, "reads c_t = (G_t, q_t)", color=BLUE, width=205)

    items.append("</svg>")
    return "\n".join(items) + "\n"


def compact_architecture_svg() -> str:
    """Render the single-column transaction pipeline overview with lane tags."""

    width, height = 900, 860
    items = svg_header(
        width,
        height,
        "TRACE-RPG transaction pipeline overview",
        (
            "One generated event read left to right: an untrusted proposal crosses the "
            "trust boundary as a typed candidate, and seven deterministic checks grouped "
            "into six state-relative families decide it from external policy and state. "
            "A failing candidate may be repaired from its typed errors at most K times or "
            "falls back unchanged; a passing candidate is rechecked and committed. Evidence "
            "tags are scope labels only: E1 offline conformance, E2 screening-pilot-only, "
            "and ENG1 engineering-only. No figure element supports population efficacy or "
            "player-experience claims. The lower strip shows the playable ledger grammar "
            "derived from committed snapshots."
        ),
    )
    items.insert(
        len(items) - 1,
        "  <style>.tag { font-size: 28px; font-weight: 700; }"
        " .ledger { font-size: 28px; font-weight: 700; }"
        " .legend { font-size: 28px; font-weight: 700; }</style>",
    )
    tag_style = {
        "E1": (BLUE, PALE_BLUE, 44),
        "E2": (ORANGE, PALE_ORANGE, 44),
        "ENG1": (GREEN, PALE_GREEN, 78),
    }

    def stage(
        x: int,
        y: int,
        box_width: int,
        *,
        accent: str,
        title_value: str,
        body_lines: tuple[str, ...],
        fill: str,
        tags: tuple[str, ...],
        dashed: bool = False,
    ) -> list[str]:
        box_height = 142
        parts = component_box(
            x,
            y,
            box_width,
            box_height,
            accent=accent,
            title_value=title_value,
            body_lines=body_lines,
            fill=fill,
            dashed=dashed,
        )
        cursor = x + box_width - 6
        for tag in reversed(tags):
            color, pale, chip_width = tag_style[tag]
            cursor -= chip_width
            parts.append(rect(cursor, y + 103, chip_width, 32, fill=pale, stroke=color, radius=4))
            parts.append(
                text(cursor + chip_width // 2, y + 127, tag, css_class="tag", anchor="middle")
            )
            cursor -= 6
        return parts

    # Band A: the transaction pipeline, read left to right and then down.
    items += band(
        10,
        15,
        880,
        635,
        accent=BLUE,
        title_value="ONE GENERATED EVENT AS A TRANSACTION",
    )
    # Evidence tags are scope labels, not efficacy claims.
    items.append(text(25, 96, "E1 offline", css_class="legend", fill=BLUE))
    items.append(text(245, 96, "E2 screening-pilot-only", css_class="legend", fill=ORANGE))
    items.append(text(575, 96, "ENG1 engineering-only", css_class="legend", fill=GREEN))
    row1, row2, row3 = 130, 312, 494
    columns = (20, 243, 466, 689)
    items += stage(
        columns[0],
        row1,
        190,
        accent=GRAY,
        title_value="PROPOSAL",
        body_lines=("untrusted", "model output"),
        fill=PALE_GRAY,
        tags=("E2",),
        dashed=True,
    )
    items += stage(
        columns[1],
        row1,
        190,
        accent=BLUE,
        title_value="PARSER",
        body_lines=("type-strict", "known keys"),
        fill=PALE_BLUE,
        tags=("E1",),
    )
    items += stage(
        columns[2],
        row1,
        190,
        accent=BLUE,
        title_value="POLICY",
        body_lines=("external q_t", "who may act"),
        fill=PALE_BLUE,
        tags=("E1", "ENG1"),
    )
    items += stage(
        columns[3],
        row1,
        190,
        accent=BLUE,
        title_value="VALIDATE",
        body_lines=("7 checks", "6 families -> E"),
        fill=PALE_BLUE,
        tags=("E1", "E2", "ENG1"),
    )
    items += stage(
        columns[2],
        row2,
        190,
        accent=GRAY,
        title_value="FALLBACK",
        body_lines=("j = K:", "no mutation"),
        fill=PALE_GRAY,
        tags=("E1", "E2"),
        dashed=True,
    )
    items += stage(
        columns[3],
        row2,
        190,
        accent=ORANGE,
        title_value="REPAIR",
        body_lines=("invalid: rho", "reads a and E"),
        fill=PALE_ORANGE,
        tags=("E1", "E2"),
    )
    items += stage(
        20,
        row3,
        270,
        accent=GREEN,
        title_value="COMMIT",
        body_lines=("all v_i hold:", "recheck, T(c_t, a)"),
        fill=PALE_GREEN,
        tags=("E1", "ENG1"),
    )
    items += stage(
        315,
        row3,
        270,
        accent=GREEN,
        title_value="RECORD",
        body_lines=("SHA-256 linked", "terminal row"),
        fill=PALE_GREEN,
        tags=("E1", "ENG1"),
    )
    items += stage(
        610,
        row3,
        270,
        accent=GREEN,
        title_value="REPLAY",
        body_lines=("recompute T,", "compare state"),
        fill=PALE_GREEN,
        tags=("E1", "ENG1"),
    )

    mid1 = row1 + 71
    items.append(line(210, mid1, 243, mid1, color=GRAY, marker="gray"))
    items.append(line(433, mid1, 466, mid1, color=BLUE, marker="blue"))
    items.append(line(656, mid1, 689, mid1, color=BLUE, marker="blue"))
    # Trust boundary between the proposal and the parser.
    items.append(line(226, 122, 226, 280, color=ORANGE, width=4, dash="11 7"))
    items += vertical_label_chip(226, 201, "TRUST", color=ORANGE, height=102)
    # Failing candidate: typed errors E go to the repair callback.
    items.append(line(760, 272, 760, 312, color=ORANGE, marker="orange"))
    items += arrow_label(705, 299, "E", color=ORANGE, width=40)
    # Bounded retry returns the repaired candidate to the gate.
    items.append(path("M850 312 V272", color=ORANGE, marker="orange", dash="9 6"))
    items.append(line(689, 383, 656, 383, color=GRAY, marker="gray"))
    items.append(path("M561 454 V474 H450 V494", color=GRAY, marker="gray"))
    # Passing candidate: down to the commit row.
    items.append(path("M689 230 H672 V292 H155 V494", color=GREEN, marker="green"))
    items += arrow_label(155, 390, "valid", color=GREEN, width=90)
    mid3 = row3 + 71
    items.append(line(290, mid3, 315, mid3, color=GREEN, marker="green"))
    items.append(line(585, mid3, 610, mid3, color=GREEN, marker="green"))

    # Band B: one compact row preserves the playable ledger grammar without
    # shrinking any label below the 28 px paper-label floor.
    items += band(
        10,
        665,
        880,
        175,
        accent=GREEN,
        title_value="PLAYABLE LEDGER GRAMMAR (ENG1)",
    )
    for x, accent, fill, dashed, lines in (
        (20, GREEN, PALE_GREEN, False, ("ENTRY #N", "COMMITTED", "7 checks hold")),
        (235, GREEN, PALE_GREEN, False, ("CONTRIB. #N", "STAGE a>b", "CHAIN k/3")),
        (450, ORANGE, PALE_ORANGE, True, ("HELD", "reason code", "NEXT VALID")),
        (665, BLUE, PALE_BLUE, False, ("RULE", "GATE family", "recalled later")),
    ):
        y = 715
        items.append(rect(x, y, 205, 110, fill=fill, stroke=accent, dash="8 6" if dashed else None))
        items.append(f'  <rect x="{x}" y="{y}" width="8" height="110" rx="4" fill="{accent}"/>')
        items.append(text(x + 106, y + 34, lines[0], css_class="ledger", anchor="middle"))
        items.append(
            multiline(
                x + 106,
                y + 65,
                lines[1:],
                css_class="small",
                line_height=34,
            )
        )
    items.append("</svg>")
    return "\n".join(items) + "\n"


def evidence_regimes_svg() -> str:
    """Render a compact, descriptive contrast from the frozen E1 and E2 counts."""

    e1_path = (
        PROJECT_ROOT / "research" / "academic-pipeline" / "stage-04-pilot" / "pilot-results.json"
    )
    e2_signal_path = (
        PROJECT_ROOT
        / "research"
        / "academic-pipeline"
        / "rq2-live-pilot"
        / "signal-repair-v2"
        / "policy_blind"
        / "summary.json"
    )
    e2_null_path = (
        PROJECT_ROOT
        / "research"
        / "academic-pipeline"
        / "rq2-live-pilot"
        / "frozen-pilot-base"
        / "goal_directed_blind"
        / "summary.json"
    )

    def load(path_value: Path) -> dict:
        return json.loads(path_value.read_text(encoding="utf-8"))

    e1 = load(e1_path)
    e1_rows = {row["arm_id"]: row for row in e1["repair_arms"]["raw_counts_by_arm"]}
    e1_specs = (
        ("rejection_only", "Rejection-only", BLUE),
        ("unchanged_retry", "Blind retry", BLUE),
        ("guided_repair", "Guided ρ", ORANGE),
        ("structured_repair", "State oracle", GREEN),
    )
    if set(e1_rows) != {spec[0] for spec in e1_specs}:
        raise ValueError("E1 repair-arm set changed; refusing to draw a stale contrast")
    if any(row["case_count"] != 12 for row in e1_rows.values()):
        raise ValueError("E1 denominator is not the frozen 12-case arm count")
    e1_counts = [
        (label, int(e1_rows[arm_id]["commit_count"]), 12, color)
        for arm_id, label, color in e1_specs
    ]

    def e2_counts(path_value: Path, expected_condition: str) -> tuple[int, int, int]:
        data = load(path_value)
        if data.get("condition") != expected_condition:
            raise ValueError(f"{path_value}: expected condition {expected_condition!r}")
        if data.get("evidence_tier") != "screening-pilot-only":
            raise ValueError(f"{path_value}: evidence tier is not screening-pilot-only")
        if data.get("matched_candidate_per_seed") is not True:
            raise ValueError(f"{path_value}: matched-candidate contract changed")
        counts = data["counts"]
        if counts["seeds"] != 5 or counts["proposals_returned"] != 5:
            raise ValueError(f"{path_value}: expected five matched pilot seeds")
        if counts["initially_invalid"] != 5 or counts["initially_valid"] != 0:
            raise ValueError(f"{path_value}: expected five initially invalid proposals")
        per_arm = data["per_arm"]
        return (
            int(per_arm["guided_repair"]["commits"]),
            int(per_arm["unchanged_retry"]["commits"]),
            5,
        )

    e2_signal = e2_counts(e2_signal_path, "policy_blind")
    e2_null = e2_counts(e2_null_path, "goal_directed_blind")
    width, height = 900, 468
    items = svg_header(
        width,
        height,
        "TRACE-RPG evidence regime contrast",
        (
            "Descriptive raw counts only: E1 frozen offline repair arms use twelve cases per arm; "
            "E2 screening-pilot-only matched candidates show the Signal-v2 policy-blind contrast "
            "and a goal-directed null regime. Denominators are not pooled and the figure supports "
            "no population efficacy, model ranking, or player-experience inference."
        ),
    )
    items.insert(
        len(items) - 1,
        "  <style>"
        " .evidence-label { font-size: 28px; font-weight: 700; }"
        " .panel-title { font-size: 28px; font-weight: 700; }"
        " .evidence-value { font-size: 28px; font-weight: 700; }"
        " .evidence-tiny { font-size: 28px; font-weight: 400; }"
        " .evidence-note { font-size: 28px; font-style: italic; fill: #5F6368; }"
        "</style>",
    )
    items += band(
        10,
        10,
        880,
        450,
        accent=BLUE,
        title_value="EVIDENCE REGIME CONTRAST (RAW COUNTS ONLY)",
    )
    items.append(
        text(
            35,
            78,
            "E1 offline + E2 screening-pilot-only; no inference",
            css_class="evidence-note",
        )
    )

    # E1: preserve the four-arm denominator contrast without pooling strata.
    items.append(rect(25, 95, 420, 300, fill="#FFFFFF", stroke=BLUE, radius=5))
    items.append(text(42, 127, "E1  FROZEN OFFLINE", css_class="panel-title", fill=BLUE))
    items.append(text(42, 166, "initially invalid: n=12", css_class="evidence-tiny", fill=MUTED))
    track_x, track_width = 190, 165
    for index, (label, commits, denominator, color) in enumerate(e1_counts):
        y = 181 + index * 45
        items.append(
            text(
                193,
                y + 20,
                label.replace("Rejection-only", "Reject-only"),
                css_class="evidence-label",
                anchor="end",
            )
        )
        items.append(rect(track_x, y, track_width, 24, fill=PALE_GRAY, stroke=BORDER, radius=3))
        fill_width = round(track_width * commits / denominator)
        if fill_width:
            items.append(rect(track_x, y, fill_width, 24, fill=color, stroke=color, radius=3))
        items.append(
            text(
                track_x + track_width + 10,
                y + 21,
                f"{commits}/{denominator}",
                css_class="evidence-value",
            )
        )
    items.append(text(track_x, 380, "0", css_class="evidence-tiny", anchor="middle", fill=MUTED))
    items.append(
        text(
            track_x + track_width // 2,
            380,
            "6",
            css_class="evidence-tiny",
            anchor="middle",
            fill=MUTED,
        )
    )
    items.append(
        text(
            track_x + track_width, 380, "12", css_class="evidence-tiny", anchor="middle", fill=MUTED
        )
    )

    # E2: separate one contrast from its null regime; never aggregate them.
    items.append(rect(460, 95, 420, 300, fill="#FFFFFF", stroke=ORANGE, radius=5))
    items.append(text(477, 127, "E2  SCREENING-PILOT-ONLY", css_class="panel-title", fill=ORANGE))
    items.append(text(477, 166, "matched calls: 5/cell", css_class="evidence-tiny", fill=MUTED))

    def regime_card(
        y: int, title: str, values: tuple[int, int, int], *, null: bool = False
    ) -> None:
        guided, blind, denominator = values
        card_fill = PALE_GRAY if null else PALE_ORANGE
        card_stroke = GRAY if null else ORANGE
        items.append(
            rect(
                475,
                y,
                390,
                105,
                fill=card_fill,
                stroke=card_stroke,
                radius=4,
                dash="8 6" if null else None,
            )
        )
        items.append(text(489, y + 25, title, css_class="evidence-label"))
        for row_index, (label, count, color) in enumerate(
            (("rho", guided, ORANGE), ("blind", blind, BLUE))
        ):
            row_y = y + 43 + row_index * 33
            items.append(rect(570, row_y, 170, 19, fill="#FFFFFF", stroke=BORDER, radius=3))
            fill_width = round(170 * count / denominator)
            if fill_width:
                items.append(rect(570, row_y, fill_width, 19, fill=color, stroke=color, radius=3))
            items.append(
                text(752, row_y + 17, f"{count}/{denominator}", css_class="evidence-value")
            )

    regime_card(173, "Signal-v2 / policy-blind", e2_signal)
    regime_card(282, "goal-directed / null", e2_null, null=True)
    items.append(line(450, 95, 450, 395, color=BORDER, width=2))
    items.append(
        text(477, 417, "rho = guided; blind = unchanged", css_class="evidence-tiny", fill=MUTED)
    )
    items.append(text(477, 450, "Denominators separate.", css_class="evidence-note"))
    items.append("</svg>")
    return "\n".join(items) + "\n"


FIGURES = {
    "fig_architecture.svg": compact_architecture_svg,
    "fig_evidence_regimes.svg": evidence_regimes_svg,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, render in FIGURES.items():
        target = OUTPUT_DIR / filename
        target.write_text(render(), encoding="utf-8", newline="\n")
        ET.parse(target)
        root = ET.parse(target).getroot()
        print(f"{filename}: {root.attrib['width']} x {root.attrib['height']} (XML valid)")


if __name__ == "__main__":
    main()
