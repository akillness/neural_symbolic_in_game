#!/usr/bin/env python3
"""Generate the repository's README-facing SVG visuals.

Two of the six visuals are data-driven: `pilot-evidence.svg` is rendered from the
frozen Stage 4 pilot summary and `claim-status.svg` from the claim ledger.  Their
numbers therefore cannot drift away from the artifacts they describe.  The four
diagram visuals restate the implemented boundary and mark every unexecuted stage,
so the README never implies live-model, human, affect, or cross-runtime evidence.

Style follows `generate_paper_figures.py` (Classic Academic, Okabe-Ito accents)
so that README and manuscript figures read as one family.
"""

from __future__ import annotations

import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generate_paper_figures import (
    BLUE,
    BORDER,
    GRAY,
    GREEN,
    LIGHT_GRAY,
    MUTED,
    ORANGE,
    PALE_BLUE,
    PALE_GRAY,
    PALE_GREEN,
    PALE_ORANGE,
    SKY,
    line,
    multiline,
    path,
    rect,
    svg_header,
    text,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "visuals"
PILOT_DIR = PROJECT_ROOT / "research" / "academic-pipeline" / "stage-04-pilot"
PILOT_SUMMARY = PILOT_DIR / "pilot-summary.csv"
REPAIR_ARMS = PILOT_DIR / "repair-arm-summary.csv"
CLAIM_LEDGER = PROJECT_ROOT / "research" / "claim-ledger.yaml"

PALE_RED = "#FBECEF"
RED = "#B4436C"


def read_csv_rows(source: Path) -> list[dict[str, str]]:
    """Return every row of a frozen pilot CSV, failing loudly when it is empty."""

    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise SystemExit(f"FAIL: no rows in {source}")
    return rows


def read_repair_arms() -> list[dict[str, str]]:
    return read_csv_rows(REPAIR_ARMS)


def title_band(width: int, heading: str, subtitle: str) -> list[str]:
    """Return a full-width caption band used by every README visual."""

    return [
        rect(0, 0, width, 96, fill=LIGHT_GRAY, stroke=BORDER, radius=0, stroke_width=0),
        f'  <rect x="0" y="0" width="10" height="96" fill="{BLUE}"/>',
        text(34, 42, heading, css_class="section"),
        text(34, 74, subtitle, css_class="small", fill=MUTED),
        line(0, 96, width, 96, color=BORDER, width=2),
    ]


def footnote(x: int, y: int, value: str) -> str:
    return text(x, y, value, css_class="note")


def card(
    x: int,
    y: int,
    width: int,
    height: int,
    heading: str,
    lines: tuple[str, ...],
    *,
    fill: str = "#FFFFFF",
    accent: str = BORDER,
    dash: str | None = None,
) -> list[str]:
    """Return an accented card with a bold heading and small body lines."""

    items = [
        rect(x, y, width, height, fill=fill, stroke=accent, radius=7, dash=dash),
        f'  <rect x="{x}" y="{y}" width="8" height="{height}" fill="{accent}"/>',
        text(x + 26, y + 40, heading, css_class="box-title"),
    ]
    for index, value in enumerate(lines):
        items.append(text(x + 26, y + 74 + index * 27, value, css_class="small"))
    return items


def status_pill(x: int, y: int, width: int, label: str, *, fill: str, stroke: str) -> list[str]:
    return [
        rect(x, y, width, 36, fill=fill, stroke=stroke, radius=18, stroke_width=2),
        text(x + width // 2, y + 25, label, css_class="small", anchor="middle"),
    ]


# --------------------------------------------------------------------------
# V1 · system architecture
# --------------------------------------------------------------------------
def system_architecture_svg() -> str:
    width, height = 1480, 860
    items = svg_header(
        width,
        height,
        "TRACE-RPG system architecture and trust boundary",
        (
            "Untrusted proposals and non-authoritative context reach a deterministic "
            "commit gate. Only the gate may mutate canonical state. Dashed elements "
            "are specified but unimplemented."
        ),
    )
    items += title_band(
        width,
        "V1 · Trust boundary: learned proposal, symbolic authority",
        "Solid = implemented and exercised by the offline pilot   ·   Dashed = specified, not implemented, no evidence",
    )

    # Column headers.
    items.append(text(40, 148, "UNTRUSTED PROPOSAL", css_class="arrow-label", fill=MUTED))
    items.append(text(560, 148, "DETERMINISTIC AUTHORITY", css_class="arrow-label", fill=RED))
    items.append(text(1080, 148, "CANONICAL RECORD", css_class="arrow-label", fill=MUTED))

    # Proposal column: context feeds the proposer, never the gate.
    items += card(
        40,
        170,
        450,
        150,
        "Non-authoritative context",
        (
            "graph retrieval · temporal memory",
            "affect estimate z_t · narrative scores",
            "never a commit authority",
        ),
        fill="#FFFFFF",
        accent=GRAY,
        dash="7 6",
    )
    items += card(
        40,
        390,
        450,
        150,
        "Recorded-response adapter",
        (
            "frozen JSONL candidates · seed · rev",
            "strict parse of known fields",
            "terminal: commit / fallback / failure",
        ),
        fill=PALE_BLUE,
        accent=BLUE,
    )
    items += card(
        40,
        574,
        450,
        98,
        "Live model providers",
        ("hosted API and local serving adapters",),
        fill="#FFFFFF",
        accent=GRAY,
        dash="7 6",
    )

    # Gate column.
    items.append(rect(560, 170, 440, 502, fill=PALE_RED, stroke=RED, radius=9, stroke_width=3))
    items.append(text(586, 212, "Hard commit gate", css_class="box-title"))
    items.append(
        text(586, 242, "state-relative, externally supplied policy", css_class="small", fill=MUTED)
    )
    items.append(line(586, 258, 974, 258, color=RED, width=2))

    gate_checks = (
        ("v_policy", "action + effects allowed"),
        ("v_pre", "preconditions hold in c_t"),
        ("v_reach", "objects reachable"),
        ("v_know", "speaker knows the fact"),
        ("v_disc", "disclosure permitted"),
        ("v_quest", "stage legal, no regression"),
    )
    for index, (code, meaning) in enumerate(gate_checks):
        items.append(text(586, 292 + index * 32, code, css_class="small"))
        items.append(text(704, 292 + index * 32, meaning, css_class="small", fill=MUTED))

    items.append(rect(586, 494, 388, 66, fill="#FFFFFF", stroke=RED, radius=6))
    items.append(text(606, 520, "12 implemented error codes", css_class="small"))
    items.append(text(606, 546, "structured counterexample set E_t", css_class="small", fill=MUTED))

    items.append(rect(586, 578, 388, 70, fill="#FFFFFF", stroke=ORANGE, radius=6))
    items.append(text(606, 604, "Bounded repair, budget K", css_class="small"))
    items.append(
        text(606, 630, "exhausted ⇒ unchanged-state fallback", css_class="small", fill=MUTED)
    )

    # Canonical column.
    items += card(
        1080,
        170,
        360,
        186,
        "Canonical state c_t",
        (
            "G_t  typed world graph",
            "q_t  action + disclosure policy",
            "m_t  committed event prefix",
            "mutated only by T(c_t, a_t)",
        ),
        fill=PALE_GREEN,
        accent=GREEN,
    )
    items += card(
        1080,
        380,
        360,
        186,
        "Terminal evidence record",
        (
            "every attempt + its error set",
            "SHA-256 checksum (unkeyed)",
            "semantic replay + continuity",
            "frozen assignment key",
        ),
        fill=PALE_GREEN,
        accent=GREEN,
    )
    items += card(
        1080,
        590,
        360,
        112,
        "Game bridge",
        ("versioned event contract", "engine transport unimplemented"),
        fill="#FFFFFF",
        accent=GRAY,
        dash="7 6",
    )

    # Flow arrows: context conditions the proposer; only the proposer reaches the gate.
    items.append(path("M265 320 V390", color=GRAY, marker="gray", dash="7 6"))
    items.append(text(285, 362, "conditions the prompt", css_class="note"))
    items.append(path("M265 574 V540", color=GRAY, marker="gray", dash="7 6"))
    items.append(path("M490 465 H560", color=BLUE, marker="blue"))
    items.append(text(525, 452, "candidate", css_class="note", anchor="middle"))
    items.append(path("M1000 245 H1080", color=GREEN, marker="green"))
    items.append(text(1006, 233, "commit", css_class="note", fill=GREEN))
    items.append(path("M1000 470 H1080", color=GREEN, marker="green"))
    items.append(text(1006, 458, "record", css_class="note", fill=GREEN))
    items.append(path("M700 672 V712 H525 V478", color=ORANGE, marker="orange"))
    items.append(text(612, 704, "repair attempt", css_class="note", anchor="middle", fill=ORANGE))

    items.append(rect(40, 720, 1400, 96, fill=PALE_GRAY, stroke=BORDER, radius=7))
    items.append(
        text(
            66,
            756,
            "Invariant: no model output, retrieved fact, memory summary, or affect score may change canonical state without passing the gate.",
            css_class="small",
        )
    )
    items.append(
        footnote(
            66,
            788,
            "Encoded validity is validity for encoded predicates only; the shared key contract rejects unknown top-level fields at both parser boundaries.",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


# --------------------------------------------------------------------------
# V2 · commit transaction
# --------------------------------------------------------------------------
def commit_transaction_svg() -> str:
    width, height = 1480, 700
    items = svg_header(
        width,
        height,
        "TRACE-RPG commit transaction and repair arms",
        (
            "A candidate is parsed, validated against the prior state, optionally "
            "repaired within a bounded budget, defensively revalidated, and only then "
            "committed. Three repair arms were exercised offline."
        ),
    )
    items += title_band(
        width,
        "V2 · One transaction: parse → validate → repair(K) → defensive check → commit",
        "A rejected candidate leaves canonical state byte-identical; every attempt is recorded before the terminal outcome",
    )

    stages = (
        (40, "Candidate a_j", ("from adapter", "or repair"), PALE_BLUE, BLUE),
        (300, "Strict parse", ("declared schema", "known fields"), PALE_BLUE, BLUE),
        (560, "Validate", ("V(c_t, a_j)", "same prior c_t"), PALE_RED, RED),
    )
    for x, heading, lines, fill, accent in stages:
        items += card(x, 150, 220, 132, heading, lines, fill=fill, accent=accent)
    for x in (260, 520):
        items.append(path(f"M{x} 216 H{x + 40}", color=BLUE, marker="blue"))

    items += card(
        880,
        150,
        260,
        132,
        "Defensive check",
        ("one extra validation", "immediately before T"),
        fill=PALE_GREEN,
        accent=GREEN,
    )
    items += card(
        1190,
        150,
        250,
        132,
        "Commit",
        ("c_(t+1) = T(c_t, a_j)", "typed event appended"),
        fill=PALE_GREEN,
        accent=GREEN,
    )
    items.append(path("M780 216 H880", color=GREEN, marker="green"))
    items.append(text(830, 200, "all v_i = 1", css_class="note", anchor="middle", fill=GREEN))
    items.append(path("M1140 216 H1190", color=GREEN, marker="green"))

    items += card(
        560,
        330,
        320,
        128,
        "Record attempt j",
        ("candidate + error set E_j", "attempt hash chain"),
        fill="#FFFFFF",
        accent=ORANGE,
    )
    items.append(path("M670 282 V330", color=ORANGE, marker="orange"))
    items.append(text(686, 312, "some v_i = 0", css_class="small", fill=ORANGE))

    items += card(
        940,
        330,
        250,
        128,
        "Repair, j < K",
        ("consume E_j", "emit revised a_(j+1)"),
        fill=PALE_ORANGE,
        accent=ORANGE,
    )
    items += card(
        1240,
        330,
        200,
        128,
        "Fallback",
        ("j = K", "c_(t+1) = c_t"),
        fill=PALE_GRAY,
        accent=GRAY,
    )
    items.append(path("M880 394 H940", color=ORANGE, marker="orange"))
    items.append(path("M1190 394 H1240", color=GRAY, marker="gray"))
    items.append(path("M1065 458 V496 H540 V252 H560", color=ORANGE, marker="orange", dash="7 6"))
    items.append(
        text(
            810,
            488,
            "revalidate against the same prior state",
            css_class="note",
            anchor="middle",
            fill=ORANGE,
        )
    )

    # Repair-arm strip, read from the frozen pilot bundle so the numbers cannot drift.
    items.append(rect(40, 530, 1400, 132, fill=LIGHT_GRAY, stroke=BORDER, radius=7))
    arm_rows = read_repair_arms()
    case_count = int(arm_rows[0]["initially_invalid_case_count"]) if arm_rows else 0
    items.append(
        text(
            66,
            566,
            f"Repair arms exercised on {case_count} authored initially-invalid cases",
            css_class="box-title",
        )
    )
    for index, arm in enumerate(arm_rows):
        x = 66 + index * 350
        commits = int(arm["commit_count"])
        cases = int(arm["initially_invalid_case_count"])
        budget = arm["repair_budget"]
        strategy = arm["repair_strategy"]
        accent = GREEN if commits else GRAY
        items.append(text(x, 606, arm["arm_id"], css_class="small"))
        items.append(text(x, 632, f"K = {budget}, {strategy}", css_class="note"))
        items.append(text(x, 656, f"{commits} / {cases} commits", css_class="small", fill=accent))
    items.append(
        footnote(
            66,
            690,
            f"{case_count} designed cases per arm across frozen repairability classes. "
            "This is pilot feasibility, not evidence that any repair strategy generally wins.",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


# --------------------------------------------------------------------------
# V3 · pilot evidence (data-driven)
# --------------------------------------------------------------------------
SECTION_ORDER = (
    "gate_conformance",
    "boundary_sentinels",
    "closed_boundary_regressions",
    "repair_arms",
    "integrity_faults",
    "integrity_boundaries",
    "adapter_accounting",
    "accounting_guards",
)

SECTION_META: dict[str, tuple[str, str, str]] = {
    "gate_conformance": (
        "Gate conformance",
        "designed fixtures, not exhaustive semantic validity",
        GREEN,
    ),
    "boundary_sentinels": (
        "Open boundary sentinels",
        "documented encoding limitations — accepted on purpose, not safety passes",
        ORANGE,
    ),
    "closed_boundary_regressions": (
        "Closed boundary regression",
        "post-Stage-8 parser rejection parity — not semantic-safety evidence",
        GREEN,
    ),
    "repair_arms": (
        "Repair arms",
        "feasibility observations per frozen repairability class",
        BLUE,
    ),
    "integrity_faults": (
        "Integrity faults",
        "named injected mutations detected by their declared checks",
        GREEN,
    ),
    "integrity_boundaries": (
        "Integrity boundary",
        "repair-generation provenance is deliberately out of replay scope",
        ORANGE,
    ),
    "adapter_accounting": (
        "Adapter accounting",
        "terminal class of each assigned offline case, not provider reliability",
        SKY,
    ),
    "accounting_guards": (
        "Accounting guards",
        "injected manifest faults rejected by authored guards",
        GREEN,
    ),
}


def read_pilot_rows() -> tuple[list[dict[str, str]], str]:
    rows = read_csv_rows(PILOT_SUMMARY)
    return rows, rows[0]["config_hash"]


def pilot_evidence_svg() -> str:
    rows, config_hash = read_pilot_rows()
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["section"], []).append(row)
    unknown = sorted(set(grouped) - set(SECTION_ORDER))
    if unknown:
        raise SystemExit(f"FAIL: unlabelled pilot sections: {unknown}")

    row_height = 34
    section_head = 56
    total_rows = sum(len(grouped.get(name, ())) for name in SECTION_ORDER)
    sections_present = [name for name in SECTION_ORDER if name in grouped]
    body_height = total_rows * row_height + len(sections_present) * (section_head + 8)
    width = 1480
    height = 96 + 40 + body_height + 140

    items = svg_header(
        width,
        height,
        "TRACE-RPG Stage 4 deterministic pilot observations",
        (
            "Exact numerator over denominator for every measure in the frozen pilot "
            "summary. All denominators are authored deterministic cases, not samples "
            "from a deployment population."
        ),
    )
    items += title_band(
        width,
        "V3 · Every Stage 4 offline-pilot number",
        f"Source: research/academic-pipeline/stage-04-pilot/pilot-summary.csv   ·   separate from live screening   ·   config_hash {config_hash[:16]}…",
    )

    bar_x = 720
    bar_w = 560
    y = 136

    for name in sections_present:
        label, caveat, accent = SECTION_META[name]
        items.append(rect(40, y, 1400, 44, fill=LIGHT_GRAY, stroke=BORDER, radius=5))
        items.append(f'  <rect x="40" y="{y}" width="8" height="44" fill="{accent}"/>')
        items.append(text(66, y + 30, label, css_class="small"))
        items.append(text(360, y + 30, caveat, css_class="note"))
        y += section_head

        for row in grouped[name]:
            numerator = int(row["numerator"])
            denominator = int(row["denominator"])
            fraction = numerator / denominator if denominator else 0.0
            filled = round(bar_w * fraction)

            items.append(text(66, y + 22, row["measure"], css_class="small"))
            items.append(
                f'  <rect x="{bar_x}" y="{y + 6}" width="{bar_w}" height="22" rx="4" '
                f'fill="#FFFFFF" stroke="{BORDER}" stroke-width="2"/>'
            )
            if filled > 0:
                items.append(
                    f'  <rect x="{bar_x}" y="{y + 6}" width="{filled}" height="22" rx="4" '
                    f'fill="{accent}" fill-opacity="0.85"/>'
                )
            items.append(
                text(
                    bar_x + bar_w + 20,
                    y + 24,
                    f"{numerator} / {denominator}",
                    css_class="small",
                )
            )
            y += row_height
        y += 8

    items.append(
        text(
            66,
            y + 34,
            "Bar length is numerator ÷ denominator for that row only; rows are not comparable to one another.",
            css_class="small",
        )
    )
    items.append(
        footnote(
            66,
            y + 64,
            "No confidence interval, significance test, or causal comparison is claimed. 0/2 and 5/7 are designed outcomes, not regressions.",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


# --------------------------------------------------------------------------
# V4 · claim status (data-driven)
# --------------------------------------------------------------------------
STATUS_STYLE: dict[str, tuple[str, str, str]] = {
    "verified-primary": ("Verified · primary", PALE_GREEN, GREEN),
    "verified-scope-limited": ("Verified · narrow scope", PALE_GREEN, GREEN),
    "verified-scope-limited-preprint": ("Preprint · narrow", PALE_ORANGE, ORANGE),
    "verified-designed-fixture": ("Verified · designed", PALE_BLUE, BLUE),
    "verified-authored-engine-fixture": ("Verified · engine", PALE_BLUE, BLUE),
    "verified-authored-engine-render-fixture": ("Verified · render", PALE_BLUE, BLUE),
    "approved-design-protocol": ("Approved · protocol", PALE_ORANGE, ORANGE),
    "proposed-contribution": ("Proposed contribution", PALE_ORANGE, ORANGE),
    "pilot-only": ("Pilot-only · screening", PALE_ORANGE, ORANGE),
    "TODO-RESULT": ("TODO · no result", PALE_GRAY, GRAY),
}

STATUS_ORDER = (
    "verified-primary",
    "verified-scope-limited",
    "verified-scope-limited-preprint",
    "verified-designed-fixture",
    "verified-authored-engine-fixture",
    "verified-authored-engine-render-fixture",
    "approved-design-protocol",
    "proposed-contribution",
    "pilot-only",
    "TODO-RESULT",
)


def read_claims() -> list[dict[str, object]]:
    import yaml

    ledger = yaml.safe_load(CLAIM_LEDGER.read_text(encoding="utf-8"))
    claims = ledger.get("claims") or []
    if not claims:
        raise SystemExit(f"FAIL: no claims in {CLAIM_LEDGER}")
    return claims


def wrap(value: str, limit: int) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > limit and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def claim_status_svg() -> str:
    claims = read_claims()
    unknown = sorted({str(claim["status"]) for claim in claims} - set(STATUS_STYLE))
    if unknown:
        raise SystemExit(f"FAIL: unstyled claim statuses: {unknown}")

    ordered: list[dict[str, object]] = []
    for status in STATUS_ORDER:
        ordered.extend(claim for claim in claims if claim["status"] == status)

    cards = []
    for claim in ordered:
        status = str(claim["status"])
        label, fill, accent = STATUS_STYLE[status]
        body = wrap(str(claim["claim"]), 64)
        evidence = claim.get("evidence") or []
        name_counts: dict[str, int] = {}
        for item in evidence:
            name = Path(str(item)).name
            name_counts[name] = name_counts.get(name, 0) + 1
        names = [f"{name} ×{count}" if count > 1 else name for name, count in name_counts.items()]
        evidence_text = f"evidence: {', '.join(names)}" if names else "evidence: none recorded"
        evidence_lines = wrap(evidence_text, 78)
        body_last = 34 + (len(body) - 1) * 27
        evidence_start = body_last + 32
        card_h = max(116, evidence_start + (len(evidence_lines) - 1) * 24 + 18)
        cards.append(
            {
                "claim": claim,
                "label": label,
                "fill": fill,
                "accent": accent,
                "body": body,
                "evidence_lines": evidence_lines,
                "evidence_start": evidence_start,
                "height": card_h,
            }
        )

    counts = {
        status: sum(1 for claim in claims if claim["status"] == status) for status in STATUS_ORDER
    }
    legend_items = [
        f"{STATUS_STYLE[status][0]}: {counts[status]}" for status in STATUS_ORDER if counts[status]
    ]
    legend_lines: list[str] = []
    for item in legend_items:
        candidate = " · ".join((*legend_lines[-1:], item)) if legend_lines else item
        if legend_lines and len(candidate) <= 100:
            legend_lines[-1] = candidate
        else:
            legend_lines.append(item)
    note_lines = wrap(
        "Pilot and screening data cannot transition directly to verified-empirical; a verified "
        "result is revoked if an upstream hash changes.",
        108,
    )
    cards_bottom = 136 + sum(int(card["height"]) + 12 for card in cards)
    legend_y = cards_bottom + 10
    legend_h = 34 + len(legend_lines) * 28 + len(note_lines) * 25 + 18
    width = 1480
    height = legend_y + legend_h + 20

    items = svg_header(
        width,
        height,
        "TRACE-RPG claim ledger status",
        (
            "Every tracked claim with its full current wording and epistemic state. "
            "C-RESULT-001 through C-RESULT-005 have no confirmatory result and remain "
            "TODO-RESULT; screening receipts appear only under their pilot claim IDs."
        ),
    )
    items += title_band(
        width,
        "V4 · What is actually claimed, and on what evidence",
        "Source: research/claim-ledger.yaml   ·   no claim or evidence list is visually truncated",
    )

    y = 136
    for card_data in cards:
        claim = card_data["claim"]
        card_h = int(card_data["height"])
        fill = str(card_data["fill"])
        accent = str(card_data["accent"])
        items.append(rect(40, y, 1400, card_h, fill=fill, stroke=accent, radius=7))
        items.append(f'  <rect x="40" y="{y}" width="8" height="{card_h}" fill="{accent}"/>')
        items.append(text(66, y + 34, str(claim["id"]), css_class="box-title"))
        items += status_pill(
            66,
            y + 48,
            300,
            str(card_data["label"]),
            fill="#FFFFFF",
            stroke=accent,
        )
        for index, value in enumerate(card_data["body"]):
            items.append(text(400, y + 34 + index * 27, value, css_class="small"))
        for index, value in enumerate(card_data["evidence_lines"]):
            items.append(
                text(
                    400,
                    y + int(card_data["evidence_start"]) + index * 24,
                    value,
                    css_class="note",
                )
            )
        y += card_h + 12

    items.append(rect(40, legend_y, 1400, legend_h, fill=LIGHT_GRAY, stroke=BORDER, radius=7))
    for index, value in enumerate(legend_lines):
        items.append(text(66, legend_y + 36 + index * 28, value, css_class="small"))
    note_start = legend_y + 36 + len(legend_lines) * 28 + 8
    for index, value in enumerate(note_lines):
        items.append(footnote(66, note_start + index * 25, value))
    items.append("</svg>")
    return "\n".join(items) + "\n"


# --------------------------------------------------------------------------
# V5 · research workflow
# --------------------------------------------------------------------------
def research_workflow_svg() -> str:
    width, height = 1480, 560
    items = svg_header(
        width,
        height,
        "TRACE-RPG academic pipeline status",
        (
            "Stages 1 through 10 have recorded repository deliverables, including current bilingual "
            "PDFs. Confirmatory efficacy studies and journal submission remain outside this completed lane."
        ),
    )
    items += title_band(
        width,
        "V5 · Academic pipeline: what has run, what has not",
        "A stage is complete only when its artifact exists in the repository; approval gates are not inferred",
    )

    stages = (
        ("Stage 1", "Research packet", "COMPLETE", PALE_GREEN, GREEN),
        ("Stage 2", "Source shortlist", "COMPLETE", PALE_GREEN, GREEN),
        ("Stage 2.5", "Integrity gate", "COMPLETE", PALE_GREEN, GREEN),
        ("Stage 3", "IEEE outline", "COMPLETE", PALE_GREEN, GREEN),
        ("Stage 4", "Offline pilot + sources", "COMPLETE", PALE_GREEN, GREEN),
        ("Stage 4.5", "Claim audit", "COMPLETE", PALE_GREEN, GREEN),
        ("Stage 5", "50 matched citations", "COMPLETE", PALE_GREEN, GREEN),
        ("Stages 6–10", "Review, live screen, PDFs, lock", "COMPLETE", PALE_GREEN, GREEN),
    )
    card_w = 165
    gap = 12
    x = 40
    for index, (name, artifact, status, fill, accent) in enumerate(stages):
        dash = "7 6" if status == "NOT EXECUTED" else None
        items.append(rect(x, 150, card_w, 196, fill=fill, stroke=accent, radius=7, dash=dash))
        items.append(f'  <rect x="{x}" y="150" width="{card_w}" height="8" fill="{accent}"/>')
        items.append(text(x + card_w // 2, 196, name, css_class="box-title", anchor="middle"))
        items.append(
            multiline(
                x + card_w // 2,
                232,
                wrap(artifact, 18),
                css_class="small",
                line_height=26,
            )
        )
        items.append(
            multiline(
                x + card_w // 2,
                308,
                wrap(status, 14),
                css_class="note",
                line_height=24,
                fill=accent,
            )
        )
        if index + 1 < len(stages):
            # The arrow inherits the status of the stage it points at.
            next_status = stages[index + 1][2]
            reached = next_status != "NOT EXECUTED"
            items.append(
                path(
                    f"M{x + card_w} 248 H{x + card_w + gap}",
                    color=GREEN if reached else GRAY,
                    marker="green" if reached else "gray",
                    width=3,
                    dash=None if reached else "5 4",
                )
            )
        x += card_w + gap

    items.append(rect(40, 380, 690, 130, fill="#FFFFFF", stroke=GREEN, radius=7))
    items.append(text(66, 416, "Produced by the executed stages", css_class="box-title"))
    items.append(
        text(66, 448, "bilingual IEEE sources · verified 50-entry bibliography", css_class="small")
    )
    items.append(
        text(
            66,
            476,
            "38 artifacts · 22 inputs · 121 provenance rows · single-model live screening",
            css_class="small",
        )
    )

    items.append(rect(750, 380, 690, 130, fill="#FFFFFF", stroke=GRAY, radius=7, dash="7 6"))
    items.append(text(776, 416, "Not produced by any stage so far", css_class="box-title"))
    items.append(
        text(
            776,
            448,
            "confirmatory multi-model study · human study · live Python↔Godot authorization",
            css_class="small",
        )
    )
    items.append(
        text(
            776,
            476,
            "runtime retrieval/memory efficacy · affect efficacy · stable performance study",
            css_class="small",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


# --------------------------------------------------------------------------
# V6 · confirmatory design
# --------------------------------------------------------------------------
def confirmatory_design_svg() -> str:
    width, height = 1480, 620
    items = svg_header(
        width,
        height,
        "TRACE-RPG planned confirmatory experiment",
        (
            "A future two-stage design crossing three promoted models with six "
            "controller systems over three tracks. No part of this design has been "
            "executed."
        ),
    )
    items += title_band(
        width,
        "V6 · Planned confirmatory design — NOT EXECUTED",
        "Shown so the scope is auditable; every element below is future work with no collected data",
    )

    items.append(rect(40, 122, 1400, 46, fill=PALE_GRAY, stroke=GRAY, radius=7, dash="7 6"))
    items.append(
        text(
            740,
            152,
            "No result in this repository comes from the design below.",
            css_class="small",
            anchor="middle",
            fill=MUTED,
        )
    )

    columns = (
        (
            40,
            "Promoted models (3)",
            (
                "hosted frontier control",
                "strong open-weight",
                "≤ 32 GB deployment profile",
                "promoted by a frozen Pareto rule",
                "from a ten-model screen",
            ),
        ),
        (
            520,
            "Controller systems (6)",
            (
                "direct commit",
                "structural constraint only",
                "validator rejection only",
                "matched-budget blind retry",
                "structured repair",
                "TRACE-RPG full",
            ),
        ),
        (
            1000,
            "Tracks (3)",
            (
                "world generation",
                "NPC dialogue",
                "affect adaptation",
                "held-out worlds, quest motifs,",
                "NPC identities, relation motifs",
            ),
        ),
    )
    for x, heading, lines in columns:
        items += card(x, 196, 440, 232, heading, lines, fill="#FFFFFF", accent=GRAY, dash="7 6")
    items.append(path("M480 312 H520", color=GRAY, marker="gray", dash="7 6"))
    items.append(path("M960 312 H1000", color=GRAY, marker="gray", dash="7 6"))

    items.append(rect(40, 444, 1400, 130, fill=LIGHT_GRAY, stroke=BORDER, radius=7))
    items.append(
        text(66, 482, "Required before any efficacy claim is admitted", css_class="box-title")
    )
    items.append(
        text(
            66,
            514,
            "preregistered primary endpoint · pilot-informed power analysis · mixed-effects model · effect size with 95% CI",
            css_class="small",
        )
    )
    items.append(
        text(
            66,
            542,
            "multiplicity correction · blinded human evaluation at matched validity · independent semantic audit · deterministic replay",
            css_class="small",
        )
    )
    items.append("</svg>")
    return "\n".join(items) + "\n"


VISUALS = {
    "system-architecture.svg": system_architecture_svg,
    "commit-transaction.svg": commit_transaction_svg,
    "pilot-evidence.svg": pilot_evidence_svg,
    "claim-status.svg": claim_status_svg,
    "research-workflow.svg": research_workflow_svg,
    "confirmatory-design.svg": confirmatory_design_svg,
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, render in VISUALS.items():
        target = OUTPUT_DIR / filename
        target.write_text(render(), encoding="utf-8", newline="\n")
        root = ET.parse(target).getroot()
        print(f"{filename}: {root.attrib['width']} x {root.attrib['height']} (XML valid)")

    stale = sorted(item.name for item in OUTPUT_DIR.glob("*.svg") if item.name not in VISUALS)
    if stale:
        print(f"WARNING: unmanaged SVGs remain in visuals/: {stale}")


if __name__ == "__main__":
    main()
