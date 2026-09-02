#!/usr/bin/env python3
"""Generate the TRACE-RPG paper's three reproducible SVG diagrams.

The drawings use only SVG primitives and Python's standard library.  Their
labels intentionally distinguish mechanism conformance in designed fixtures
from future, unmeasured efficacy claims.
"""

from __future__ import annotations

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
ORANGE = "#E69F00"
GREEN = "#009E73"
GRAY = "#7A7A7A"
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
        "      .section { font-size: 28px; font-weight: 700; }",
        "      .box-title { font-size: 26px; font-weight: 700; }",
        "      .body { font-size: 25px; font-weight: 400; }",
        "      .small { font-size: 24px; font-weight: 400; }",
        "      .note { font-size: 24px; font-style: italic; fill: #5F6368; }",
        "      .arrow-label { font-size: 24px; font-weight: 700; }",
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
                y + 62,
                body_lines,
                css_class="small",
                line_height=25,
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
            f'    <rect class="label-shield" x="{x - width // 2}" y="{y - 21}" '
            f'width="{width}" height="29" rx="2" fill="#FFFFFF" stroke="#FFFFFF"/>'
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


def repair_state_machine_svg() -> str:
    width, height = 1440, 780
    items = svg_header(
        width,
        height,
        "TRACE-RPG bounded validate-repair-commit state machine",
        (
            "Each candidate attempt is validated and recorded. A repair budget K permits at most "
            "K plus one recorded attempts. On an invalid attempt with budget remaining, the "
            "arm-selected repair callback runs: the guided operator rho consumes only the prior "
            "candidate and the structured error set, while the state-reading oracle callback is "
            "an upper bound only. A successful application performs an additional defensive "
            "validation before canonical mutation."
        ),
    )

    items += band(
        25,
        20,
        830,
        92,
        accent=BLUE,
        title_value="BOUNDED ATTEMPT CONTRACT",
        subtitle="≤ K + 1 recorded candidate attempts: j = 0, …, K",
    )
    items += band(
        880,
        20,
        535,
        92,
        accent=ORANGE,
        title_value="FROZEN REPAIRABILITY CLASSES",
        subtitle="guided-repairable · oracle-only · irreparable",
    )

    items += component_box(
        45,
        205,
        190,
        100,
        accent=GRAY,
        title_value="Candidate a_j",
        body_lines=("initial j = 0", "or repaired"),
        fill=PALE_GRAY,
    )
    items += component_box(
        285,
        205,
        205,
        100,
        accent=BLUE,
        title_value="Validate",
        body_lines=("V(c_t,a_j)", "same prior c_t"),
        fill=PALE_BLUE,
    )
    items += component_box(
        540,
        195,
        245,
        120,
        accent=BLUE,
        title_value="Record attempt j",
        body_lines=("candidate + V", "errors E_j + hashes"),
        fill=PALE_BLUE,
    )

    items.append(
        polygon(
            "885,185 965,255 885,325 805,255",
            fill="#FFFFFF",
            stroke=BLUE,
            stroke_width=3,
        )
    )
    items.append(multiline(885, 249, ("valid?",), css_class="box-title"))

    items += component_box(
        995,
        125,
        245,
        115,
        accent=GREEN,
        title_value="Defensive validation",
        body_lines=("one extra check", "before mutation"),
        fill=PALE_GREEN,
    )
    items += component_box(
        1275,
        125,
        125,
        115,
        accent=GREEN,
        title_value="COMMIT",
        body_lines=("atomic", "T(c_t,a_j)"),
        fill=PALE_GREEN,
    )

    items.append(
        polygon(
            "1010,310 1090,380 1010,450 930,380",
            fill="#FFFFFF",
            stroke=ORANGE,
            stroke_width=3,
        )
    )
    items.append(multiline(1010, 374, ("j < K?",), css_class="box-title"))
    items += component_box(
        620,
        485,
        240,
        110,
        accent=ORANGE,
        title_value="Guided repair",
        body_lines=("rho(a_j, E_j) edit from E_j", "never reads state; j ← j+1"),
        fill=PALE_ORANGE,
    )
    items += component_box(
        885,
        485,
        250,
        110,
        accent=SKY,
        title_value="Oracle repair",
        body_lines=("reads authoritative state", "upper bound; j ← j+1"),
        fill=PALE_BLUE,
    )
    items += component_box(
        1185,
        485,
        215,
        110,
        accent=GRAY,
        title_value="FALLBACK",
        body_lines=("no mutation", "c_(t+1) = c_t"),
        fill=PALE_GRAY,
    )

    items += component_box(
        955,
        650,
        445,
        85,
        accent=BLUE,
        title_value="Finalize trace + semantic replay",
        body_lines=("recorded outcome must reconstruct deterministically",),
        fill=PALE_BLUE,
    )

    items.append(line(235, 255, 285, 255, color=GRAY, marker="gray"))
    items.append(line(490, 255, 540, 255, color=BLUE, marker="blue"))
    items.append(line(785, 255, 805, 255, color=BLUE, marker="blue"))
    items.append(path("M965 235 H980 V182 H995", color=GREEN, marker="green"))
    items += arrow_label(980, 218, "yes", color=GREEN, width=55)
    items.append(line(1240, 182, 1275, 182, color=GREEN, marker="green"))
    items.append(path("M885 325 V355 H930", color=ORANGE, marker="orange"))
    items += arrow_label(905, 350, "no", color=ORANGE, width=50)
    items.append(path("M1010 450 V465 H740 V485", color=ORANGE, marker="orange"))
    items.append(path("M1010 450 V485", color=ORANGE, marker="orange"))
    items += arrow_label(900, 460, "yes", color=ORANGE, width=50)
    items.append(path("M1090 380 H1140 V540 H1185", color=GRAY, marker="gray"))
    items += arrow_label(1135, 370, "no", color=GRAY, width=48)
    items.append(
        path(
            "M1010 595 V625 H140 V305",
            color=ORANGE,
            marker="orange",
            dash="10 7",
        )
    )
    items.append(path("M740 595 V625", color=ORANGE, dash="10 7"))
    items += arrow_label(430, 619, "next recorded candidate attempt", color=ORANGE, width=280)
    items.append(path("M1338 240 V440 H1420 V632 H1390 V650", color=GREEN, marker="green"))
    items.append(path("M1292 595 V615 H1260 V650", color=GRAY, marker="gray"))

    items += band(
        25,
        655,
        850,
        95,
        accent=GRAY,
        title_value="TERMINATION ASSUMPTION",
        subtitle="Callbacks are assumed to return; the runtime enforces no wall-clock deadline",
    )
    items.append(
        text(
            1400,
            765,
            "The extra defensive validation is not an additional candidate attempt.",
            css_class="note",
            anchor="end",
        )
    )

    items.append("</svg>")
    return "\n".join(items) + "\n"


def evidence_boundary_svg() -> str:
    width, height = 1440, 650
    items = svg_header(
        width,
        height,
        "TRACE-RPG evidence and inference boundary",
        (
            "Frozen designed fixtures feed a deterministic observation pipeline and support only "
            "mechanism-conformance statements, including the guided-versus-oracle repair "
            "separation. Live-model efficacy, player benefit, affect, and commercial-engine "
            "performance remain unmeasured future questions."
        ),
    )

    items += band(
        20,
        20,
        325,
        605,
        accent=GRAY,
        title_value="DESIGNED FIXTURES",
        subtitle="Purposive, frozen inputs",
    )
    for y, title_value, body_lines, accent in (
        (100, "Gate conformance", ("valid control", "named failure codes"), BLUE),
        (
            220,
            "Repair arms",
            ("K=0 · retry · rho · oracle", "frozen repairability classes"),
            ORANGE,
        ),
        (340, "Integrity mutations", ("checksum / replay", "linkage / continuity"), GREEN),
        (460, "Adapter + accounting", ("strict response classes", "assignment guards"), GRAY),
    ):
        items += component_box(
            45,
            y,
            275,
            95,
            accent=accent,
            title_value=title_value,
            body_lines=body_lines,
        )

    items += band(
        375,
        20,
        430,
        605,
        accent=BLUE,
        title_value="DETERMINISTIC OBSERVATION",
        subtitle="Versioned artifacts and exact counts",
    )
    for y, title_value, body_lines, accent, fill in (
        (
            100,
            "Frozen manifest + hashes",
            ("case IDs / arm IDs", "config / input / state"),
            BLUE,
            PALE_BLUE,
        ),
        (
            220,
            "Offline runner",
            ("proposal → gate → outcome", "one classified row / case"),
            BLUE,
            PALE_BLUE,
        ),
        (
            340,
            "Designated check operations",
            ("schema + checksum", "semantic replay + continuity"),
            GREEN,
            PALE_GREEN,
        ),
        (
            460,
            "Generated evidence tables",
            ("raw counts + exact ratios", "no population p-values"),
            GREEN,
            PALE_GREEN,
        ),
    ):
        items += component_box(
            400,
            y,
            380,
            95,
            accent=accent,
            title_value=title_value,
            body_lines=body_lines,
            fill=fill,
        )

    items.append(line(320, 147, 400, 147, color=BLUE, marker="blue"))
    items.append(line(320, 267, 400, 267, color=ORANGE, marker="orange"))
    items.append(line(320, 387, 400, 387, color=GREEN, marker="green"))
    items.append(line(320, 507, 400, 507, color=GRAY, marker="gray"))
    items.append(line(590, 195, 590, 220, color=BLUE, marker="blue"))
    items.append(line(590, 315, 590, 340, color=BLUE, marker="blue"))
    items.append(line(590, 435, 590, 460, color=GREEN, marker="green"))

    items.append(
        line(
            840,
            35,
            840,
            615,
            color=ORANGE,
            width=4,
            dash="12 8",
        )
    )
    items += vertical_label_chip(
        840,
        325,
        "INFERENCE BOUNDARY",
        color=ORANGE,
        height=320,
    )

    items += component_box(
        885,
        45,
        510,
        245,
        accent=GREEN,
        title_value="OBSERVED IN THIS PAPER",
        body_lines=(
            "Designed-fixture agreement",
            "Rejected-state immutability",
            "Bounded attempt accounting",
            "Guided-vs-oracle repair separation",
            "Implemented fault-fixture detection",
            "Mechanism conformance for frozen cases",
        ),
        fill=PALE_GREEN,
    )
    items += component_box(
        885,
        330,
        510,
        270,
        accent=ORANGE,
        title_value="NOT MEASURED — FUTURE WORK",
        body_lines=(
            "Live-model repair quality or superiority",
            "Player benefit or narrative quality",
            "Affect-adaptation efficacy",
            "Commercial-engine performance",
            "Semantic / policy completeness",
            "Cryptographic authentication",
        ),
        fill=PALE_ORANGE,
        dashed=True,
    )
    items.append(path("M780 507 H835 V170 H885", color=GREEN, marker="green"))
    items += arrow_label(875, 162, "supported", color=GREEN, width=105)
    items.append(
        text(
            1140,
            625,
            "No result arrow crosses into the future-work panel.",
            css_class="note",
            anchor="middle",
        )
    )

    items.append("</svg>")
    return "\n".join(items) + "\n"


def compact_architecture_svg() -> str:
    """Render a single-column, print-legible trust-boundary diagram."""

    width, height = 900, 600
    items = svg_header(
        width,
        height,
        "TRACE-RPG compact trust-boundary architecture",
        (
            "Non-authoritative context conditions an untrusted proposal. A strict adapter and "
            "state-relative validator select commit, bounded repair, or unchanged fallback."
        ),
    )
    items += band(
        20,
        15,
        860,
        95,
        accent=GRAY,
        title_value="NON-AUTHORITATIVE CONTEXT  z_t",
        subtitle="retrieval / memory / soft scores / rationale / future affect",
    )
    items += band(
        20,
        125,
        860,
        310,
        accent=BLUE,
        title_value="PROPOSAL TO VALIDATION TO TERMINAL OUTCOME",
        subtitle="solid = deterministic path / dashed = bounded retry",
    )
    items += component_box(
        40,
        210,
        125,
        92,
        accent=GRAY,
        title_value="Proposal",
        body_lines=("a_j", "untrusted"),
        fill=PALE_GRAY,
    )
    items += component_box(
        190,
        210,
        135,
        92,
        accent=BLUE,
        title_value="Adapter",
        body_lines=("schema", "known keys"),
        fill=PALE_BLUE,
    )
    items += component_box(
        355,
        200,
        165,
        112,
        accent=BLUE,
        title_value="Validator",
        body_lines=("V(c_t,a_j)", "hard gates"),
        fill=PALE_BLUE,
    )
    items += component_box(
        590,
        185,
        125,
        92,
        accent=GREEN,
        title_value="COMMIT",
        body_lines=("atomic T",),
        fill=PALE_GREEN,
    )
    items += component_box(
        745,
        185,
        120,
        92,
        accent=GREEN,
        title_value="Bridge",
        body_lines=("versioned", "event"),
        fill=PALE_GREEN,
    )
    items += component_box(
        575,
        330,
        150,
        82,
        accent=ORANGE,
        title_value="REPAIR",
        body_lines=("rho(a_j,E_j)",),
        fill=PALE_ORANGE,
    )
    items += component_box(
        725,
        330,
        140,
        82,
        accent=GRAY,
        title_value="FALLBACK",
        body_lines=("unchanged",),
        fill=PALE_GRAY,
    )

    items.append(line(165, 256, 190, 256, color=GRAY, marker="gray"))
    items.append(line(325, 256, 355, 256, color=BLUE, marker="blue"))
    items.append(path("M520 230 H590", color=GREEN, marker="green"))
    items += arrow_label(555, 218, "valid", color=GREEN, width=72)
    items.append(line(715, 230, 745, 230, color=GREEN, marker="green"))
    items.append(path("M520 278 H548 V371 H575", color=ORANGE, marker="orange"))
    items += arrow_label(550, 344, "invalid", color=ORANGE, width=86)
    items.append(path("M520 295 H535 V425 H795 V412", color=GRAY, marker="gray"))
    items += arrow_label(680, 421, "budget exhausted", color=GRAY, width=170)
    items.append(path("M575 386 H545 V302 H520", color=ORANGE, marker="orange", dash="9 6"))

    items += band(
        20,
        450,
        860,
        130,
        accent=GREEN,
        title_value="CANONICAL AUTHORITY",
    )
    items += component_box(
        40,
        515,
        235,
        48,
        accent=GREEN,
        title_value="Prior state  G_t",
        fill=PALE_GREEN,
    )
    items += component_box(
        330,
        515,
        235,
        48,
        accent=BLUE,
        title_value="Stored policy  q_t",
        fill=PALE_BLUE,
    )
    items += component_box(
        630,
        515,
        235,
        48,
        accent=GREEN,
        title_value="Final state  c_(t+1)",
        fill=PALE_GREEN,
    )
    items.append(path("M448 515 V312", color=BLUE, marker="blue"))
    items += arrow_label(540, 468, "validator reads", color=BLUE, width=156)
    items.append(path("M865 230 H875 V500 H748 V515", color=GREEN, marker="green"))
    items.append(path("M805 412 V515", color=GRAY, marker="gray"))
    items.append("</svg>")
    return "\n".join(items) + "\n"


def compact_repair_state_machine_svg() -> str:
    """Render the bounded transaction as a single-column state machine."""

    width, height = 900, 620
    items = svg_header(
        width,
        height,
        "TRACE-RPG compact validate-repair-commit state machine",
        (
            "Every candidate is validated and recorded. Valid candidates receive a defensive "
            "check before commit; invalid candidates repair within K or fall back unchanged."
        ),
    )
    items += band(
        20,
        15,
        520,
        90,
        accent=BLUE,
        title_value="BOUNDED ATTEMPTS",
        subtitle="at most K + 1 recorded candidates",
    )
    items += band(
        560,
        15,
        320,
        90,
        accent=ORANGE,
        title_value="FROZEN CLASSES",
        subtitle="guided / oracle / none",
    )
    items += component_box(
        30,
        155,
        130,
        90,
        accent=GRAY,
        title_value="Candidate",
        body_lines=("a_j",),
        fill=PALE_GRAY,
    )
    items += component_box(
        190,
        155,
        130,
        90,
        accent=BLUE,
        title_value="Validate",
        body_lines=("V(c_t,a_j)",),
        fill=PALE_BLUE,
    )
    items += component_box(
        350,
        145,
        155,
        110,
        accent=BLUE,
        title_value="Record j",
        body_lines=("candidate", "errors+hash"),
        fill=PALE_BLUE,
    )
    items.append(
        polygon("575,135 645,200 575,265 505,200", fill="#FFFFFF", stroke=BLUE, stroke_width=3)
    )
    items.append(multiline(575, 194, ("valid?",), css_class="box-title"))
    items += component_box(
        675,
        125,
        190,
        95,
        accent=GREEN,
        title_value="Defense check",
        body_lines=("before mutation",),
        fill=PALE_GREEN,
    )
    items += component_box(
        700,
        250,
        150,
        82,
        accent=GREEN,
        title_value="COMMIT",
        body_lines=("atomic T",),
        fill=PALE_GREEN,
    )
    items.append(
        polygon(
            "575,285 645,345 575,405 505,345",
            fill="#FFFFFF",
            stroke=ORANGE,
            stroke_width=3,
        )
    )
    items.append(multiline(575, 339, ("j < K?",), css_class="box-title"))
    items += component_box(
        245,
        430,
        180,
        88,
        accent=ORANGE,
        title_value="Guided repair",
        body_lines=("rho(a_j,E_j)",),
        fill=PALE_ORANGE,
    )
    items += component_box(
        450,
        430,
        180,
        88,
        accent=SKY,
        title_value="Oracle repair",
        body_lines=("state upper bound",),
        fill=PALE_BLUE,
    )
    items += component_box(
        700,
        430,
        165,
        88,
        accent=GRAY,
        title_value="FALLBACK",
        body_lines=("no mutation",),
        fill=PALE_GRAY,
    )

    items.append(line(160, 200, 190, 200, color=GRAY, marker="gray"))
    items.append(line(320, 200, 350, 200, color=BLUE, marker="blue"))
    items.append(path("M645 180 H675", color=GREEN, marker="green"))
    items += arrow_label(655, 168, "yes", color=GREEN, width=46)
    items.append(path("M770 220 V250", color=GREEN, marker="green"))
    items.append(path("M575 265 V285", color=ORANGE, marker="orange"))
    items += arrow_label(605, 278, "no", color=ORANGE, width=50)
    items.append(path("M535 385 V410 H335 V430", color=ORANGE, marker="orange"))
    items.append(path("M615 385 V410 H540 V430", color=SKY, marker="blue"))
    items += arrow_label(470, 405, "selected arm", color=ORANGE, width=146)
    items.append(path("M645 345 H675 V474 H700", color=GRAY, marker="gray"))
    items += arrow_label(669, 336, "no", color=GRAY, width=50)
    items.append(path("M540 518 V538 H95 V245", color=ORANGE, marker="orange", dash="9 6"))
    items.append(path("M335 518 V538", color=ORANGE, dash="9 6"))
    items += arrow_label(310, 532, "next candidate attempt", color=ORANGE, width=225)

    items += band(
        20,
        548,
        500,
        58,
        accent=GRAY,
        title_value="Callback return assumed",
    )
    items += component_box(
        560,
        540,
        320,
        66,
        accent=BLUE,
        title_value="Finalize trace",
        body_lines=("semantic replay",),
        fill=PALE_BLUE,
    )
    items.append(path("M775 332 H885 V573 H880", color=GREEN, marker="green"))
    items.append(path("M782 518 V540", color=GRAY, marker="gray"))
    items.append("</svg>")
    return "\n".join(items) + "\n"


def compact_evidence_boundary_svg() -> str:
    """Render designed inputs, checks, and claim ceiling at column width."""

    width, height = 900, 560
    items = svg_header(
        width,
        height,
        "TRACE-RPG compact evidence boundary",
        (
            "Designed fixtures flow through deterministic checks to mechanism-conformance "
            "statements only. Efficacy, player benefit, affect, and performance remain future work."
        ),
    )
    items += band(
        15,
        15,
        245,
        525,
        accent=GRAY,
        title_value="FROZEN FIXTURES",
        subtitle="frozen inputs",
    )
    for y, title_value, body, accent in (
        (90, "Gate cases", "valid + named errors", BLUE),
        (190, "Repair arms", "K=0 / blind / rho / oracle", ORANGE),
        (290, "Faults", "checksum / replay", GREEN),
        (390, "Accounting", "adapter + assignment", GRAY),
    ):
        items += component_box(
            35,
            y,
            205,
            78,
            accent=accent,
            title_value=title_value,
            body_lines=(body,),
        )

    items += band(
        280,
        15,
        280,
        525,
        accent=BLUE,
        title_value="DETERMINISTIC",
        subtitle="versioned exact counts",
    )
    for y, title_value, body, accent, fill in (
        (90, "Manifest + hashes", "IDs / config / state", BLUE, PALE_BLUE),
        (190, "Offline runner", "proposal to outcome", BLUE, PALE_BLUE),
        (290, "Check operations", "schema / continuity", GREEN, PALE_GREEN),
        (390, "Generated tables", "raw count / exact ratio", GREEN, PALE_GREEN),
    ):
        items += component_box(
            300,
            y,
            240,
            78,
            accent=accent,
            title_value=title_value,
            body_lines=(body,),
            fill=fill,
        )

    for y, color in ((129, BLUE), (229, ORANGE), (329, GREEN), (429, GRAY)):
        items.append(line(240, y, 300, y, color=color, marker="blue" if color == BLUE else "gray"))
    items.append(line(585, 25, 585, 535, color=ORANGE, width=4, dash="11 7"))
    items += vertical_label_chip(585, 280, "INFERENCE BOUNDARY", color=ORANGE, height=300)

    items += component_box(
        615,
        35,
        270,
        235,
        accent=GREEN,
        title_value="OBSERVED",
        body_lines=(
            "fixture agreement",
            "state immutability",
            "attempt accounting",
            "guided/oracle split",
            "named fault detection",
            "mechanism conformance",
        ),
        fill=PALE_GREEN,
    )
    items += component_box(
        615,
        295,
        270,
        235,
        accent=ORANGE,
        title_value="NOT MEASURED",
        body_lines=(
            "live repair superiority",
            "player or narrative benefit",
            "affect efficacy",
            "commercial performance",
            "semantic completeness",
            "authentication",
        ),
        fill=PALE_ORANGE,
        dashed=True,
    )
    items.append(path("M540 429 H570 V270 H750", color=GREEN, marker="green"))
    items += arrow_label(665, 286, "supports", color=GREEN, width=98)
    items.append("</svg>")
    return "\n".join(items) + "\n"


FIGURES = {
    "fig_architecture.svg": compact_architecture_svg,
    "fig_repair_state_machine.svg": compact_repair_state_machine_svg,
    "fig_evidence_boundary.svg": compact_evidence_boundary_svg,
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
