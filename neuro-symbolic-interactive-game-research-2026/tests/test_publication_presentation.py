"""Rendered publication contracts; these are not gameplay or scientific efficacy tests."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "paper/latex/figures"
# IEEEtran journal textwidth = 7.16in; 96 CSS px/in, not the SVG's authoring units.
FULL_WIDTH = 7.16 * 96
SINGLE_COLUMN = FULL_WIDTH / 2


def _browser(figures):
    playwright = os.environ.get("PLAYWRIGHT_BIN") or shutil.which("playwright")
    if not playwright:
        pytest.skip("Publication geometry requires installed Playwright/Chromium")
    env = os.environ.copy()
    env["NODE_PATH"] = os.pathsep.join(
        filter(
            None, [env.get("NODE_PATH"), str(Path(playwright).parent.parent / "lib/node_modules")]
        )
    )
    candidates = sorted(
        Path.home().glob(
            "Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/"
            "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        )
    )
    if candidates and not env.get("PLAYWRIGHT_EXECUTABLE_PATH"):
        env["PLAYWRIGHT_EXECUTABLE_PATH"] = str(candidates[-1])
    result = subprocess.run(
        ["node", str(ROOT / "tests/publication_presentation_driver.cjs")],
        input=json.dumps({"figures": figures}),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def rendered_signals():
    names = ("fig_signal_mechanism", "fig_signal_comparison")
    results = _browser(
        [{"svg": (FIGURES / f"{name}.svg").read_text(), "width": FULL_WIDTH} for name in names]
    )
    return dict(zip(names, results, strict=True))


@pytest.fixture(scope="module")
def rendered_architecture():
    return _browser(
        [
            {
                "svg": (FIGURES / "fig_architecture.svg").read_text(),
                "width": FULL_WIDTH,
            }
        ]
    )[0]


@pytest.fixture(scope="module")
def rendered_disclosure():
    return _browser(
        [{"svg": (FIGURES / "fig_disclosure_signals.svg").read_text(), "width": SINGLE_COLUMN}]
    )[0]


def test_disclosure_matrix_has_single_column_readability_and_cell_clearance(rendered_disclosure):
    """At 343.68 CSSpx, header, arm, and body labels retain >=12px type and >=8px insets."""
    problems = _disclosure_geometry_violations(rendered_disclosure)
    assert not problems, problems


def _geometry_violations(figure, *, padding_tolerance=0.5, font_tolerance=0.1):
    problems = []
    for text in figure["texts"]:
        bounds = text["card"] or figure["canvas"]
        # A visible 9pt/12CSSpx font is the floor; margins remain actual paper pixels.
        if text["fontSize"] < 12 - font_tolerance:
            problems.append((text["text"], "font", text["fontSize"]))
        gaps = (
            text["left"] - bounds["left"],
            bounds["right"] - text["right"],
            text["top"] - bounds["top"],
            bounds["bottom"] - text["bottom"],
        )
        if min(gaps) < 8 - padding_tolerance:
            problems.append((text["text"], "padding", gaps))
        if text.get("insets") is not None and min(text["insets"]) < 8 - padding_tolerance:
            problems.append((text["text"], "padding", text["insets"]))
    for labels in [figure["texts"], *(text["lines"] for text in figure["texts"])]:
        for index, first in enumerate(labels):
            for second in labels[index + 1 :]:
                overlap_x = min(first["right"], second["right"]) - max(
                    first["left"], second["left"]
                )
                overlap_y = min(first["bottom"], second["bottom"]) - max(
                    first["top"], second["top"]
                )
                if overlap_x > 0.5 and overlap_y > 0.5:
                    problems.append((first["text"], "overlap", second["text"]))
    return problems


def _disclosure_geometry_violations(figure):
    problems = _geometry_violations(figure, padding_tolerance=0, font_tolerance=0)
    for text in figure["texts"]:
        if text["role"] in {"head", "arm", "cell"} and text["card"] is None:
            problems.append((text["text"], "missing cell bounds", None))
        bounds = text["card"] or figure["canvas"]
        for line in text["inkLines"]:
            if line["fontSize"] < 12:
                problems.append((line["text"], "font", line["fontSize"]))
            gaps = (
                line["left"] - bounds["left"],
                bounds["right"] - line["right"],
                line["top"] - bounds["top"],
                bounds["bottom"] - line["bottom"],
            )
            if min(gaps) < 8:
                problems.append((line["text"], "padding", gaps))
        for index, first in enumerate(text["inkLines"]):
            for second in text["inkLines"][index + 1 :]:
                if (
                    min(first["right"], second["right"]) > max(first["left"], second["left"]) + 0.5
                    and min(first["bottom"], second["bottom"])
                    > max(first["top"], second["top"]) + 0.5
                ):
                    problems.append((first["text"], "overlap", second["text"]))
    return problems


@pytest.mark.parametrize(
    "mutation,violation",
    (
        ("undersized-font", "font"),
        ("disclosure-small-line", "font"),
        ("disclosure-header-padding", "padding"),
        ("disclosure-body-padding", "padding"),
        ("disclosure-arm-padding", "padding"),
        ("disclosure-header-overlap", "overlap"),
        ("disclosure-body-overlap", "overlap"),
    ),
)
def test_disclosure_single_column_geometry_rejects_tight_or_overlapping_cells(mutation, violation):
    """Actual header/body/arm labels cannot pass by fitting only inside the outer canvas."""
    figure = _browser(
        [
            {
                "svg": (FIGURES / "fig_disclosure_signals.svg").read_text(),
                "width": SINGLE_COLUMN,
                "mutation": mutation,
            }
        ]
    )[0]
    assert violation in {problem[1] for problem in _disclosure_geometry_violations(figure)}


def _disclosure_value_violations(figure):
    trace = (
        ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5/disclosure-trace.jsonl"
    )
    rows = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    expected = {}
    for arm in ("unchecked_isolated", "general_rule", "ontology_gate"):
        for prefix, stratum in (("N", "normal"), ("B", "boundary"), ("M", "malformed")):
            selected = [row for row in rows if row["arm"] == arm and row["stratum"] == prefix]
            outcomes = [check["outcome"] for row in selected for check in row.get("checks", [])]
            expected[arm, stratum] = [
                (
                    "E",
                    sum(not row["mismatch"] for row in selected),
                    sum(bool(row["mismatch"]) for row in selected),
                ),
                ("n", len(selected)),
                (
                    "R",
                    sum(bool(row["replay_equal"]) for row in selected),
                    sum(not row["replay_equal"] for row in selected),
                ),
                ("C", outcomes.count("pass"), outcomes.count("fail")),
                ("NR", sum(not row.get("checks") for row in selected)),
            ]
    actual = {}
    for text in figure["texts"]:
        if text["cell"] is not None:
            key = text["cell"]["arm"], text["cell"]["stratum"]
            actual.setdefault(key, []).extend(text["inkLines"])
    parsed = {}
    for key, lines in actual.items():
        parsed[key] = []
        for line in sorted(lines, key=lambda line: (line["top"], line["left"])):
            pair = re.fullmatch(r"(E|R|C)\s+(\d+)\s*/\s*(\d+)", line["text"])
            count = re.fullmatch(r"(n|NR)\s*(?:=|\s)\s*(\d+)", line["text"])
            if pair:
                parsed[key].append((pair[1], int(pair[2]), int(pair[3])))
            elif count:
                parsed[key].append((count[1], int(count[2])))
            else:
                parsed[key].append(("unrecognized visible value", line["text"]))
    return [] if parsed == expected else [("matrix values", parsed, expected)]


def test_disclosure_nine_cells_preserve_trace_pairs_denominators_and_missingness(
    rendered_disclosure,
):
    """E/R count case P/F, C counts sparse check records, and NR counts unreported cases."""
    assert not (problems := _disclosure_value_violations(rendered_disclosure)), problems
    visible = " ".join(
        line["text"] for text in rendered_disclosure["texts"] for line in text["inkLines"]
    )
    for meaning in (
        "E expected P/F (n cases)",
        "R replay P/F",
        "C records P/F",
        "NR cases with no reported checks",
        "NR unreported",
        "not pass/skipped/out-of-scope.",
    ):
        assert meaning in visible, (meaning, visible)


@pytest.mark.parametrize("field", ("E", "R", "C", "n", "NR"))
def test_disclosure_numeric_oracle_rejects_swapped_pairs_and_erased_missingness(field):
    """Reverse real asymmetric P/F pairs or erase n/NR; recomputed trace evidence must reject it."""
    figure = _browser(
        [
            {
                "svg": (FIGURES / "fig_disclosure_signals.svg").read_text(),
                "width": SINGLE_COLUMN,
                "mutation": f"disclosure-value-{field}",
            }
        ]
    )[0]
    assert _disclosure_value_violations(figure)


@pytest.mark.parametrize("name", ("fig_signal_mechanism", "fig_signal_comparison"))
def test_signal_figures_have_paper_scale_padding_and_no_text_collisions(rendered_signals, name):
    """Every visible label fits its card/canvas and remains >=9pt at final placement."""
    assert not (problems := _geometry_violations(rendered_signals[name])), problems


@pytest.mark.parametrize(
    "mutation,violation",
    (
        ("undersized-font", "font"),
        ("clipped-label", "padding"),
        ("colliding-labels", "overlap"),
    ),
)
def test_rendered_geometry_detects_physical_presentation_regressions(mutation, violation):
    """Shrink, clip, and collide real labels in memory; no approved asset is rewritten."""
    figure = _browser(
        [
            {
                "svg": (FIGURES / "fig_signal_mechanism.svg").read_text(),
                "width": FULL_WIDTH,
                "mutation": mutation,
            }
        ]
    )[0]
    assert violation in {problem[1] for problem in _geometry_violations(figure)}


def test_architecture_has_paper_scale_card_and_rotated_shield_clearance(rendered_architecture):
    """At 687.36px placement, cards and shields retain readable, collision-free labels."""
    problems = _geometry_violations(rendered_architecture, padding_tolerance=0, font_tolerance=0)
    assert not problems, problems
    trust = next(text for text in rendered_architecture["texts"] if text["text"] == "TRUST")
    assert trust["card"]["shield"], "The rotated trust label must be checked against its shield"
    assert min(trust["insets"]) >= 8, trust


@pytest.mark.parametrize(
    "mutation,violation",
    (
        ("undersized-font", "font"),
        ("clipped-label", "padding"),
        ("colliding-labels", "overlap"),
        ("rotated-shield-padding", "padding"),
        ("colliding-lines", "overlap"),
    ),
)
def test_architecture_geometry_rejects_visible_regressions(mutation, violation):
    """A moved rotated label must fail clearance even while it still fits the outer canvas."""
    figure = _browser(
        [
            {
                "svg": (FIGURES / "fig_architecture.svg").read_text(),
                "width": FULL_WIDTH,
                "mutation": mutation,
            }
        ]
    )[0]
    problems = _geometry_violations(figure, padding_tolerance=0, font_tolerance=0)
    if mutation == "rotated-shield-padding":
        assert any(text == "TRUST" and kind == violation for text, kind, _ in problems), problems
    else:
        assert violation in {problem[1] for problem in problems}, problems


def _architecture_notation_violations(figure):
    problems = []
    rendered = " ".join(text["text"] for text in figure["texts"])
    if not any(
        line["text"] == "STAGE a>b" and line["right"] > line["left"]
        for text in figure["texts"]
        for line in text["lines"]
    ):
        problems.append("ledger literal")
    if (
        "ρ" not in rendered
        or "→" not in rendered
        or re.search(r"\\[A-Za-z]+|\$|[qvc]_[tic]", rendered)
    ):
        problems.append("math glyphs")
    for base, suffix in (("q", "t"), ("v", "i"), ("c", "t")):
        candidates = [
            (first, second)
            for text in figure["texts"]
            for first, second in pairwise(text["glyphs"])
            if first["char"] == base and second["char"] == suffix
        ]
        if not any(
            second["top"] > first["top"]
            and second["bottom"] > first["bottom"]
            and second["bottom"] - second["top"] < first["bottom"] - first["top"]
            and second["left"] >= first["left"]
            for first, second in candidates
        ):
            problems.append(f"{base}_{suffix} subscript")
    return problems


def test_architecture_renders_math_subscripts_without_rewriting_ledger_grammar(
    rendered_architecture,
):
    """Math has smaller/lowered SVG glyphs, while STAGE a>b stays literal gameplay grammar."""
    assert not (problems := _architecture_notation_violations(rendered_architecture)), problems


@pytest.mark.parametrize(
    "mutation,violations",
    (
        ("flattened-subscripts", ("q_t subscript", "v_i subscript", "c_t subscript")),
        ("raw-math-escape", ("math glyphs",)),
        ("ledger-arrow", ("ledger literal",)),
    ),
)
def test_architecture_notation_rejects_flattened_or_rewritten_labels(mutation, violations):
    """A printable but wrong mathematical or ledger label cannot satisfy the visual oracle."""
    figure = _browser(
        [
            {
                "svg": (FIGURES / "fig_architecture.svg").read_text(),
                "width": FULL_WIDTH,
                "mutation": mutation,
            }
        ]
    )[0]
    assert set(violations) <= set(_architecture_notation_violations(figure))


def test_comparison_visible_rows_preserve_frozen_trace_counts(rendered_signals):
    """Reflow must not transpose arms/strata or turn absent checks into passing zeroes."""
    trace = (
        ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5/disclosure-trace.jsonl"
    )
    rows = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    figure = rendered_signals["fig_signal_comparison"]
    expected = []
    for arm, label in (
        ("unchecked_isolated", "UNCHECKED"),
        ("general_rule", "GENERAL"),
        ("ontology_gate", "ONTOLOGY"),
    ):
        for prefix, name in (("N", "Normal"), ("B", "Boundary"), ("M", "Malformed")):
            selected = [row for row in rows if row["arm"] == arm and row["stratum"] == prefix]
            allows = sum(row["observed"]["allowed"] for row in selected)
            unsafe = sum(
                (not row["expected"]["allowed"] and row["observed"]["allowed"])
                or (row["expected"]["state_effect"] == "redisplay_no_mutation" and row["mutated"])
                for row in selected
            )
            checks = [check["outcome"] for row in selected for check in row.get("checks", [])]
            expected.append(
                (
                    label,
                    f"{name}  n={len(selected)}",
                    f"{allows} / {len(selected) - allows}",
                    str(unsafe),
                    str(sum(bool(row["mismatch"]) for row in selected)),
                    f"{checks.count('pass')} / {checks.count('fail')}" if checks else "unreported",
                )
            )
    actual = []
    for label in figure["texts"]:
        if label["text"] not in {"UNCHECKED", "GENERAL", "ONTOLOGY"}:
            continue
        baseline = label["bottom"]
        same_row = [text for text in figure["texts"] if abs(text["bottom"] - baseline) < 1]
        actual.append(
            tuple(text["text"] for text in sorted(same_row, key=lambda text: text["left"]))
        )
    assert actual == expected


def _compile_excerpt(tmp_path, language, content):
    # XeLaTeX preserves operator Unicode mappings; pdfLaTeX's CM big operators
    # may extract as V/[ despite looking correct, so it is not a glyph oracle.
    compiler = "xelatex"
    if not shutil.which(compiler) or not shutil.which("pdftotext"):
        pytest.skip(f"Publication excerpt requires {compiler} and pdftotext")
    main = (ROOT / f"paper/latex/{language}/main.tex").read_text()
    preamble = main.split(r"\begin{document}", 1)[0].split(r"\title{", 1)[0]
    source = tmp_path / "excerpt.tex"
    source.write_text(preamble + "\n\\begin{document}\n" + content + "\n\\end{document}\n")
    result = subprocess.run(
        [compiler, "-interaction=nonstopmode", "-halt-on-error", source.name],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    assert result.returncode == 0, result.stdout[-6000:] + result.stderr
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", str(tmp_path / "excerpt.pdf"), "-"],
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    root = ET.fromstring(result.stdout)
    words = [
        {
            "text": node.text or "",
            "page": page_index,
            **{key: float(value) for key, value in node.attrib.items()},
        }
        for page_index, page in enumerate(root.iter("{http://www.w3.org/1999/xhtml}page"))
        for node in page.iter()
        if node.tag.endswith("}word")
    ]
    assert words, "PDF text geometry must be observable before checking collisions"
    return words


@pytest.mark.parametrize("language", ("en", "ko"))
def test_equations_render_real_operators_and_not_escaped_latex(tmp_path, language):
    """Validator, transition, and repair equations retain math glyphs/subscript layout."""
    source = (ROOT / f"paper/latex/{language}/main.tex").read_text()
    equations = re.findall(r"\\begin\{equation\}.*?\\end\{equation\}", source, re.DOTALL)
    assert len(equations) == 3, "Review the independent math oracle when equations change"
    words = _compile_excerpt(tmp_path, language, "\n".join(equations))
    rendered = " ".join(word["text"] for word in words)
    for operator in ("∈", "∧", "⊕", "∪", "ρ", "δ"):
        assert operator in rendered, (operator, rendered)
    assert not re.search(r"\\(?:rho|delta|bigcup|bigwedge|mathrm|text|in|oplus)|\$", rendered), (
        rendered
    )
    # A subscript must be smaller and lower, not printed as raw c_t/a_t source.
    c = next(word for word in words if word["text"].strip("(),") == "c")
    assert any(
        word["text"] == "t"
        and word["xMin"] >= c["xMin"]
        and -0.5 <= word["xMin"] - c["xMax"] < 3
        and 0 < word["yMin"] - c["yMin"] < 6
        and word["page"] == c["page"]
        and word["yMax"] - word["yMin"] < c["yMax"] - c["yMin"]
        for word in words
    ), (c, words)


def _assert_no_word_collisions(words):
    for index, first in enumerate(words):
        for second in words[index + 1 :]:
            if first["page"] != second["page"]:
                continue
            width = min(first["xMax"], second["xMax"]) - max(first["xMin"], second["xMin"])
            height = min(first["yMax"], second["yMax"]) - max(first["yMin"], second["yMin"])
            assert width <= 0.25 or height <= 0.25, (first, second)


@pytest.mark.parametrize("language", ("en", "ko"))
@pytest.mark.parametrize(
    "family",
    (
        "contribution_map",
        "evidence_lanes",
        "pilot_tables",
        "npc_tables",
    ),
)
def test_generated_tables_wrap_without_visible_word_collisions(tmp_path, language, family):
    """Narrow paragraph columns may wrap identifiers, never paint over other cells."""
    source = (ROOT / f"paper/latex/generated/{family}_{language}.tex").read_text()
    tables = re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", source, re.DOTALL)
    assert tables, f"No publication table to exercise in {family}"
    words = _compile_excerpt(tmp_path, language, "\n\\clearpage\n".join(tables))
    _assert_no_word_collisions(words)


@pytest.mark.parametrize("language", ("en", "ko"))
def test_disclosure_table_preserves_observed_rows_with_intercell_space(tmp_path, language):
    """Actual TeX rows keep packet counts, ordered pairs, and an >=8pt column gutter."""
    source = (ROOT / f"paper/latex/generated/disclosure_tables_{language}.tex").read_text()
    tables = re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", source, re.DOTALL)
    table = next(table for table in tables if r"\label{tab:disclosure-arms}" in table)
    words = _compile_excerpt(tmp_path, language, table)
    observed = json.loads(
        (
            ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5/"
            "comparison-summary.json"
        ).read_text()
    )
    for arm in ("unchecked_isolated", "general_rule", "ontology_gate"):
        metric = observed["arms"][arm]
        label = next(word for word in words if word["text"] == arm)
        row = sorted(
            (word for word in words if abs(word["yMax"] - label["yMax"]) < 0.5),
            key=lambda word: word["xMin"],
        )
        expected = [
            arm,
            "48/4/8",
            f"{metric['allowed_count']}/{metric['denied_count']}",
            str(metric["expected_mismatch_count"]),
            f"{metric['state_assertion_failure_count']}/{metric['display_assertion_failure_count']}",
            str(metric["replay_mismatch_count"]),
            str(metric["unsafe_violation_count"]),
        ]
        assert [word["text"] for word in row] == expected, row
        gaps = [right["xMin"] - left["xMax"] for left, right in pairwise(row)]
        assert min(gaps) >= 8 * 72 / 72.27 - 0.15, (arm, gaps)
    # Header wrapping and body rows may grow, but visible words must never collide.
    _assert_no_word_collisions(words)
