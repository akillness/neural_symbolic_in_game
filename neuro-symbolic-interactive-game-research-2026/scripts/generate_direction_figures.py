#!/usr/bin/env python3
"""Generate SVG figures for the consensus-vs-symbolic-gate research direction.

Repository rule: paper/research diagrams come from SVG/Python generators, not
image models. Output: research/directions/figures/*.svg. The Pareto panel is a
conceptual target sketch and is labeled as such — it plots no measured data.
"""

from html import escape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_ROOT / "research" / "directions" / "figures"

INK = "#1B2830"
SOFT = "#4A5A64"
MUTED = "#75838C"
PANEL = "#F7F3E9"
CARD = "#FFFDF6"
BRASS = "#8A6228"
AMBER = "#B97F1E"
CORAL = "#B84A41"
MONO = "Noto Sans KR, Apple SD Gothic Neo, Helvetica, Arial, sans-serif"


def svg_header(width, height, title, description):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="svg-title svg-desc" '
        f'font-family="{MONO}">'
        f'<title id="svg-title">{escape(title)}</title>'
        f'<desc id="svg-desc">{escape(description)}</desc>'
    )


def box(x, y, w, h, stroke, label_lines, fill=CARD, size=12.5, color=INK):
    text = ""
    line_height = 15
    start = y + h / 2 - (len(label_lines) - 1) * line_height / 2 + 4
    for index, line in enumerate(label_lines):
        text += (
            f'<text x="{x + w / 2}" y="{start + index * line_height}" text-anchor="middle" '
            f'font-family="{MONO}" font-size="{size}" fill="{color}">{escape(line)}</text>'
        )
    rect = (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="1.3"/>'
    )
    return rect + text


def arrow(x1, y1, x2, y2, color=SOFT, dash=""):
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line class="connector" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{color}" stroke-width="1.4" marker-end="url(#arr)"{dash_attr}/>'
    )


def label(x, y, value, color=MUTED, size=11, anchor="middle", halo=False):
    halo_attrs = (
        f' paint-order="stroke" stroke="{PANEL}" stroke-width="5" stroke-linejoin="round"'
        if halo
        else ""
    )
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-family="{MONO}" '
        f'font-size="{size}" fill="{color}"{halo_attrs}>{escape(value)}</text>'
    )


def lanes_figure() -> str:
    parts = [
        svg_header(
            900,
            430,
            "세 가지 검증 체제 비교",
            "동일 시나리오, 모델, 예산 계정 아래 기호 게이트, 컨센서스, 하이브리드를 비교한다.",
        ),
        (
            f'<defs><marker id="arr" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" '
            f'markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8z" fill="{SOFT}"/></marker></defs>'
        ),
        f'<rect x="0" y="0" width="900" height="430" fill="{PANEL}"/>',
        label(450, 28, "세 가지 검증 체제 — 동일 시나리오·모델·예산 계정 아래 비교", INK, 14),
    ]
    lanes = [
        (
            55,
            "(a) 기호 게이트 A5",
            BRASS,
            ["Proposer", "1회 + 수리 ≤K"],
            ["KG/정책 Validator", "결정론·모델비용 0"],
            ["Commit / Refuse", "하드 보장 I1–I4"],
        ),
        (
            185,
            "(b) 컨센서스 C1/C2",
            CORAL,
            ["Proposer ×N", "독립 표본 N=5"],
            ["일치 투표/토론", "소프트 신호·보장 없음"],
            ["Accept / Reject", "확률적 판정"],
        ),
        (
            315,
            "(c) 하이브리드 C3",
            AMBER,
            ["Proposer ×N", "표본 N"],
            ["컨센서스 랭킹", "→ 게이트 최종 권한"],
            ["Gate Commit", "하드 보장 유지"],
        ),
    ]
    for y, title, color, first, second, third in lanes:
        parts.append(label(60, y - 12, title, color, 13, "start"))
        parts.append(box(60, y, 200, 62, color, first))
        parts.append(arrow(260, y + 31, 330, y + 31, color))
        parts.append(box(330, y + 0, 240, 62, color, second))
        parts.append(arrow(570, y + 31, 640, y + 31, color))
        parts.append(box(640, y, 200, 62, color, third))
    parts.append(
        label(
            450,
            412,
            "비용 축: 호출 수·토큰·지연·$ | 정확도 축: valid episode rate · hard violation rate · semantic hazard",
            MUTED,
            11.5,
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def pareto_figure() -> str:
    # Conceptual target sketch only — axes carry no measured values.
    left, top, width, height = 90, 60, 700, 280
    parts = [
        svg_header(
            860,
            420,
            "비용-유효성 Pareto 개념 스케치",
            "측정 데이터가 아닌 목표 스케치로, 기호 게이트와 컨센서스 후보의 예상 위치를 비교한다.",
        ),
        f'<rect x="0" y="0" width="860" height="420" fill="{PANEL}"/>',
        label(430, 30, "개념적 목표 스케치 — 측정 데이터 아님 [TARGET]", CORAL, 13),
        (
            f'<line x1="{left}" y1="{top + height}" x2="{left + width}" y2="{top + height}" '
            f'stroke="{INK}" stroke-width="1.2"/>'
        ),
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + height}" '
            f'stroke="{INK}" stroke-width="1.2"/>'
        ),
        label(
            left + width / 2, top + height + 35, "에피소드당 기대 비용 (토큰·호출·$) →", INK, 12.5
        ),
        (
            f'<text x="40" y="{top + height / 2}" text-anchor="middle" font-family="{MONO}" '
            f'font-size="12.5" fill="{INK}" transform="rotate(-90 40 {top + height / 2})">'
            "하드 유효성 →</text>"
        ),
    ]
    # Draw the conceptual frontier before its point labels. Haloed labels then
    # interrupt the stroke instead of letting it print across glyphs.
    parts.append(
        f'<path class="connector" d="M130 300 C 250 160, 330 110, 340 95 L 470 78" '
        f'fill="none" stroke="{AMBER}" stroke-width="1.2" stroke-dasharray="5 4"/>'
    )
    points = [
        ("A0 direct", 130, 300, MUTED),
        ("A3 blind retry", 300, 205, MUTED),
        ("C1 vote-5", 500, 175, CORAL),
        ("C2 debate", 640, 160, CORAL),
        ("A4 repair", 320, 150, SOFT),
        ("A5 gate", 340, 95, BRASS),
        ("C3 hybrid?", 470, 78, AMBER),
    ]
    for name, x, y, color in points:
        parts.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}"/>')
        parts.append(label(x, y - 14, name, color, 11.5, halo=True))
    parts.append(
        label(
            430,
            410,
            "H5 질문: 컨센서스 arm이 게이트의 Pareto 전선을 개선하는가, 흡수되는가?",
            INK,
            12,
        )
    )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    figures = {
        "fig_consensus_gate_lanes.svg": lanes_figure(),
        "fig_cost_validity_pareto_concept.svg": pareto_figure(),
    }
    for name, svg in figures.items():
        target = OUT_DIR / name
        target.write_text(svg, encoding="utf-8", newline="\n")
        print("wrote", target.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
