#!/usr/bin/env python3
"""Generate TRACE-RPG paper's reproducible SVG figures.

The drawings use only SVG primitives and Python's standard library. Their
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
ORANGE = "#A05A00"
GREEN = "#007A59"
GRAY = "#666A6D"
PALE_BLUE = "#EAF4FA"
PALE_ORANGE = "#FFF2DD"
PALE_GREEN = "#E8F5EF"
PALE_GRAY = "#EEF0F2"

# Only these authored mathematical labels use SVG typography; DTO strings stay literal.
MATH_LABELS = {
    "external q_t": 'external <tspan font-style="italic">q<tspan baseline-shift="sub" font-size="70%">t</tspan></tspan>',
    "6 families -> E": '6 families → <tspan font-style="italic">E</tspan>',
    "invalid: rho": 'invalid: <tspan font-style="italic">ρ</tspan>',
    "invalid: rho(a,E)": 'invalid: <tspan font-style="italic">ρ(a,E)</tspan>',
    "reads a and E": 'reads <tspan font-style="italic">a</tspan> and <tspan font-style="italic">E</tspan>',
    "all v_i hold:": 'all <tspan font-style="italic">v<tspan baseline-shift="sub" font-size="70%">i</tspan></tspan> hold:',
    "recheck, T(c_t, a)": 'recheck, <tspan font-style="italic">T(c<tspan baseline-shift="sub" font-size="70%">t</tspan>, a)</tspan>',
    "recompute T,": 'recompute <tspan font-style="italic">T</tspan>,',
}


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
        f"{fill_attr}{transform}>{MATH_LABELS.get(value, escape(value))}</text>"
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
        tspans.append(f'<tspan x="{x}" dy="{dy}">{MATH_LABELS.get(value, escape(value))}</tspan>')
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
            f'    <rect class="label-shield" x="{x - width // 2}" y="{y - 44}" '
            f'width="{width}" height="68" rx="2" fill="#FFFFFF" stroke="#FFFFFF"/>'
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
            f'    <rect class="label-shield" x="{x - 40}" y="{y - height // 2}" '
            f'width="80" height="{height}" rx="3" fill="#FFFFFF" stroke="#FFFFFF"/>'
        ),
        (
            f'    <text x="{x}" y="{y}" class="section" text-anchor="middle" dominant-baseline="central" '
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
    """Render the full-width transaction pipeline with padded stages and scope tags."""
    width, height = 1280, 1070
    items = svg_header(
        width,
        height,
        "TRACE-RPG transaction pipeline overview",
        "One generated event read left to right: an untrusted proposal crosses the trust boundary as a typed candidate, and seven deterministic checks grouped into six state-relative families decide it from external policy and state. Evidence tags are scope labels only: DESIGN structure, E1 offline conformance, and ENG1 engineering-only. No figure element supports population efficacy or player-experience claims. The lower strip shows the playable ledger grammar derived from committed snapshots.",
    )
    items.insert(
        len(items) - 1, "<style>.tag,.ledger,.legend {font-size:28px;font-weight:700}</style>"
    )
    tag_colors = {"DESIGN": GRAY, "E1": BLUE, "ENG1": GREEN}

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
        parts = [
            rect(x, y, box_width, 200, fill=fill, stroke=accent, dash="8 6" if dashed else None),
            text(x + box_width // 2, y + 50, title_value, css_class="box-title", anchor="middle"),
            multiline(x + box_width // 2, y + 98, body_lines, css_class="small", line_height=38),
        ]
        # Text-only scope tags avoid miniature chips with near-zero internal padding.
        span = 80 * (len(tags) - 1)
        for index, tag in enumerate(tags):
            parts.append(
                text(
                    x + box_width // 2 - span // 2 + 80 * index,
                    y + 178,
                    tag,
                    css_class="tag",
                    anchor="middle",
                    fill=tag_colors[tag],
                )
            )
        return parts

    items += [
        rect(10, 15, 1260, 800, fill=LIGHT_GRAY),
        text(35, 65, "ONE GENERATED EVENT AS A TRANSACTION", css_class="section"),
        text(35, 110, "DESIGN structure", css_class="legend", fill=GRAY),
        text(365, 110, "E1 offline", css_class="legend", fill=BLUE),
        text(700, 110, "ENG1 engineering-only", css_class="legend", fill=GREEN),
    ]
    row1, row2, row3 = 140, 365, 590
    for x, accent, title_value, body_lines, fill, tags, dashed in (
        (20, GRAY, "PROPOSAL", ("untrusted", "model output"), PALE_GRAY, ("DESIGN",), True),
        (362, BLUE, "PARSER", ("type-strict", "known keys"), PALE_BLUE, ("E1",), False),
        (674, BLUE, "POLICY", ("external q_t", "who may act"), PALE_BLUE, ("E1", "ENG1"), False),
        (
            986,
            BLUE,
            "VALIDATE",
            ("7 checks", "6 families -> E"),
            PALE_BLUE,
            ("E1", "ENG1"),
            False,
        ),
    ):
        items += stage(
            x,
            row1,
            270,
            accent=accent,
            title_value=title_value,
            body_lines=body_lines,
            fill=fill,
            tags=tags,
            dashed=dashed,
        )
    items += stage(
        664,
        row2,
        270,
        accent=GRAY,
        title_value="FALLBACK",
        body_lines=("j = K:", "no mutation"),
        fill=PALE_GRAY,
        tags=("E1",),
        dashed=True,
    )
    items += stage(
        986,
        row2,
        270,
        accent=ORANGE,
        title_value="REPAIR",
        body_lines=("invalid: rho(a,E)", "reads a and E"),
        fill=PALE_ORANGE,
        tags=("E1",),
    )
    for x, title_value, body_lines in (
        (20, "COMMIT", ("all v_i hold:", "recheck, T(c_t, a)")),
        (450, "RECORD", ("SHA-256 linked", "terminal row")),
        (880, "REPLAY", ("recompute T,", "compare state")),
    ):
        items += stage(
            x,
            row3,
            380,
            accent=GREEN,
            title_value=title_value,
            body_lines=body_lines,
            fill=PALE_GREEN,
            tags=("E1", "ENG1"),
        )
    for x1, x2, color, marker in ((638, 668, BLUE, "blue"), (950, 980, BLUE, "blue")):
        items.append(line(x1, 240, x2, 240, color=color, marker=marker))
    items.append(line(326, 132, 326, 355, color=ORANGE, width=3, dash="11 7"))
    items += vertical_label_chip(312, 164, "TRUST", color=ORANGE, height=192)
    items.append(line(296, 240, 356, 240, color=GRAY, marker="gray"))
    items.append(line(1080, 346, 1080, 359, color=ORANGE, marker="orange"))
    items.append(path("M1220 359 V346", color=ORANGE, marker="orange", dash="9 6"))
    items.append(line(980, 465, 940, 465, color=GRAY, marker="gray"))
    items.append(path("M800 575 V578 H640 V584", color=GRAY, marker="gray"))
    items.append(path("M980 240 H960 V355 H210 V584", color=GREEN, marker="green"))
    items += arrow_label(210, 470, "valid", color=GREEN, width=112)
    items.append(line(406, 690, 444, 690, color=GREEN, marker="green"))
    items.append(line(836, 690, 874, 690, color=GREEN, marker="green"))

    items += [
        rect(10, 830, 1260, 225, fill=LIGHT_GRAY),
        text(35, 875, "PLAYABLE LEDGER GRAMMAR (ENG1)", css_class="section"),
    ]
    for x, accent, fill, dashed, lines in (
        (24, GREEN, PALE_GREEN, False, ("ENTRY #N", "COMMITTED", "7 checks hold")),
        (336, GREEN, PALE_GREEN, False, ("CONTRIB. #N", "STAGE a>b", "CHAIN k/3")),
        (648, ORANGE, PALE_ORANGE, True, ("HELD", "reason code", "NEXT VALID")),
        (960, BLUE, PALE_BLUE, False, ("RULE", "GATE family", "recalled later")),
    ):
        items.append(
            rect(x, 890, 292, 160, fill=fill, stroke=accent, dash="8 6" if dashed else None)
        )
        items.append(text(x + 146, 934, lines[0], css_class="ledger", anchor="middle"))
        items.append(multiline(x + 146, 980, lines[1:], css_class="small", line_height=32))

    items.append("</svg>")
    return "\n".join(items) + "\n"


FIGURES = {
    "fig_architecture.svg": compact_architecture_svg,
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
