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
        "      .section { font-size: 25px; font-weight: 700; }",
        "      .box-title { font-size: 24px; font-weight: 700; }",
        "      .body { font-size: 21px; font-weight: 400; }",
        "      .small { font-size: 19px; font-weight: 400; }",
        "      .note { font-size: 19px; font-style: italic; fill: #5F6368; }",
        "      .arrow-label { font-size: 19px; font-weight: 700; }",
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
        f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
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
        f'  <path d="{d}" stroke="{color}" stroke-width="{width}" '
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
    return [
        rect(x - width // 2, y - 21, width, 29, fill="#FFFFFF", stroke="#FFFFFF", radius=2),
        text(x, y, value, css_class="arrow-label", anchor="middle", fill=color),
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
        85,
        285,
        60,
        accent=GRAY,
        title_value="Retrieval / memory",
    )
    items += component_box(
        375,
        85,
        285,
        60,
        accent=GRAY,
        title_value="Soft narrative scores",
    )
    items += component_box(
        695,
        85,
        285,
        60,
        accent=GRAY,
        title_value="Model rationale",
    )
    items += component_box(
        1015,
        85,
        355,
        60,
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
        905,
        375,
        190,
        100,
        accent=ORANGE,
        title_value="REPAIR",
        body_lines=("structured E_j", "only while j < K"),
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
    items.append(path("M805 340 H850 V425 H905", color=ORANGE, marker="orange"))
    items += arrow_label(850, 395, "invalid, j < K", color=ORANGE, width=150)
    items.append(path("M805 352 H825 V498 H1125 V425 H1170", color=GRAY, marker="gray"))
    items += arrow_label(1030, 493, "invalid, j = K", color=GRAY, width=150)
    items.append(
        path(
            "M905 442 H875 V482 H150 V370",
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
        title_value="CANONICAL AUTHORITY  c_t = (G_t, q_t, m_t)",
        subtitle="Canonical owner supplies typed world state, action/quest/disclosure policy, and committed prefix",
    )
    items += component_box(
        55,
        600,
        365,
        55,
        accent=GREEN,
        title_value="Prior canonical state  c_t",
        fill=PALE_GREEN,
    )
    items += component_box(
        495,
        600,
        380,
        55,
        accent=BLUE,
        title_value="Externally supplied policy  q_t",
        fill=PALE_BLUE,
    )
    items += component_box(
        970,
        600,
        405,
        55,
        accent=GREEN,
        title_value="Final canonical state  c_(t+1)",
        fill=PALE_GREEN,
    )
    items.append(path("M1000 325 V560 H1170 V600", color=GREEN, marker="green"))
    items.append(path("M1270 475 V600", color=GRAY, marker="gray"))

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
            "K plus one recorded attempts. A successful application performs an additional "
            "defensive validation before canonical mutation."
        ),
    )

    items += band(
        25,
        20,
        1390,
        92,
        accent=BLUE,
        title_value="BOUNDED ATTEMPT CONTRACT",
        subtitle="≤ K + 1 recorded candidate attempts: j = 0, …, K",
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
        735,
        485,
        240,
        110,
        accent=ORANGE,
        title_value="Structured repair",
        body_lines=("consume E_j", "set j ← j + 1"),
        fill=PALE_ORANGE,
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
    items.append(path("M980 432 V458 H855 V485", color=ORANGE, marker="orange"))
    items += arrow_label(904, 456, "yes", color=ORANGE, width=55)
    items.append(path("M1090 380 H1140 V540 H1185", color=GRAY, marker="gray"))
    items += arrow_label(1135, 370, "no", color=GRAY, width=48)
    items.append(
        path(
            "M735 540 H665 V625 H140 V305",
            color=ORANGE,
            marker="orange",
            dash="10 7",
        )
    )
    items += arrow_label(430, 619, "next recorded candidate attempt", color=ORANGE, width=280)
    items.append(path("M1338 240 V630 H1180 V650", color=GREEN, marker="green"))
    items.append(path("M1292 595 V625 H1245 V650", color=GRAY, marker="gray"))

    items += band(
        25,
        655,
        850,
        95,
        accent=GRAY,
        title_value="TERMINATION ASSUMPTION",
        subtitle="Each proposal/repair callback returns within its separately enforced deadline",
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
            "mechanism-conformance statements. Live-model efficacy, player benefit, affect, and "
            "commercial-engine performance remain unmeasured future questions."
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
        (220, "Repair arms", ("K = 0 / retry / repair", "repairable strata"), ORANGE),
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
    items.append(
        text(
            831,
            325,
            "INFERENCE BOUNDARY",
            css_class="section",
            anchor="middle",
            fill=ORANGE,
            rotate=-90,
        )
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
            "Live ten-model superiority",
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


FIGURES = {
    "fig_architecture.svg": architecture_svg,
    "fig_repair_state_machine.svg": repair_state_machine_svg,
    "fig_evidence_boundary.svg": evidence_boundary_svg,
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
