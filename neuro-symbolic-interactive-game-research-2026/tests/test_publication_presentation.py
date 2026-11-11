"""Rendered publication contracts; these are not gameplay or scientific efficacy tests."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "paper/latex/figures"
# IEEEtran journal textwidth = 7.16in; 96 CSS px/in, not the SVG's authoring units.
FULL_WIDTH = 7.16 * 96
SINGLE_COLUMN = FULL_WIDTH / 2


def _browser(figures, *, bridge_control=False):
    env = os.environ.copy()
    if env.get("NSG_BROWSER_BACKEND") == "aside":
        assert shutil.which(env.get("ASIDE_BIN", "aside")), "Aside CLI is required"
    else:
        playwright = os.environ.get("PLAYWRIGHT_BIN") or shutil.which("playwright")
        if not playwright:
            pytest.skip("Publication geometry requires installed Playwright/Chromium")
        env["NODE_PATH"] = os.pathsep.join(
            filter(
                None,
                [env.get("NODE_PATH"), str(Path(playwright).parent.parent / "lib/node_modules")],
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
        input=json.dumps({"figures": figures, "bridgeControl": bridge_control}),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=140 if env.get("NSG_BROWSER_BACKEND") == "aside" else 60,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def test_aside_main_world_bridge_preserves_untrusted_json_values_and_errors():
    """Own __proto__ keys, sentinel-like text, undefined and async errors survive real transport."""
    if os.environ.get("NSG_BROWSER_BACKEND") != "aside":
        return
    result = _browser(
        [{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}],
        bridge_control=True,
    )
    assert result == [
        {
            "mainWorld": True,
            "ownProto": {"polluted": True},
            "sentinel": "undefined",
            "text": "</script><script>window.__nsgInjected=true</script>",
        }
    ]


def test_aside_backend_terminates_a_cli_that_ignores_sigterm(tmp_path, monkeypatch):
    """A real stuck external CLI is force-terminated and reports failure rather than hanging cleanup."""
    executable = tmp_path / "aside-stuck-fixture"
    executable.write_text(
        f"#!{sys.executable}\nimport signal, sys\nsignal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "sys.stdin.read()\nprint('stuck CLI control ready', flush=True)\nwhile True: signal.pause()\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", str(executable))
    monkeypatch.setenv("NSG_ASIDE_GUARD_MS", "1000")
    with pytest.raises(AssertionError, match="exceeded fixture CLI deadline") as failure:
        _browser([{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}])
    assert "SIGKILL escalation after ignored SIGTERM" in str(failure.value)


@pytest.mark.parametrize("failure", ("missing-cli", "empty-envelope", "reported-error"))
def test_aside_backend_refuses_missing_or_incomplete_browser_execution(
    tmp_path, monkeypatch, failure
):
    """No unavailable CLI or successful-looking empty response may manufacture rendered geometry."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    executable = tmp_path / "aside-fixture"
    monkeypatch.setenv("ASIDE_BIN", str(executable))
    if failure == "missing-cli":
        expected = "Aside CLI is required"
    else:
        envelope = {
            "run": {
                "content": [],
                "error": None if failure == "empty-envelope" else "fixture backend error",
            }
        }
        executable.write_text(
            f"#!{sys.executable}\nimport sys\nsys.stdin.read()\nprint({json.dumps(json.dumps(envelope))})\n",
            encoding="utf-8",
        )
        executable.chmod(0o700)
        expected = "Aside exited before observation"
    with pytest.raises(AssertionError, match=expected):
        _browser([{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}])


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
        or re.search(r"\\[A-Za-z]+|\$|[qvcG]_[tic]", rendered)
    ):
        problems.append("math glyphs")
    for base, suffix in (("q", "t"), ("v", "i"), ("c", "t"), ("G", "t")):
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
        ("flattened-graph-subscript", ("G_t subscript",)),
        ("raw-graph-subscript", ("math glyphs", "G_t subscript")),
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
    if mutation == "flattened-graph-subscript":
        assert _architecture_notation_violations(figure) == ["G_t subscript"]


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


@pytest.mark.parametrize(
    "leader_exit,guard",
    (
        ("deadline", "Aside call exceeded fixture CLI deadline"),
        ("early-nonzero", "Aside exited before observation"),
    ),
)
def test_aside_backend_kills_a_group_survivor_after_its_leader_exits(
    tmp_path, monkeypatch, leader_exit, guard
):
    """Leader exit cannot hide a pipe-closed TERM survivor or replace the initiating failure."""
    pidfile = tmp_path / "descendant.json"
    leaderfile = tmp_path / "leader.json"
    termfile = tmp_path / "leader-term.json"
    secret = "SYNTHETIC_PRIVATE_PROCESS_OUTPUT_DO_NOT_PUBLISH"
    child_code = (
        "import json, os, signal, sys\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        f"with open({str(pidfile)!r}, 'w') as record: json.dump({{'pid':os.getpid(),'pgid':os.getpgrp()}}, record)\n"
        "print('ready', flush=True)\nos.close(sys.stdout.fileno())\n"
        "while True: signal.pause()\n"
    )
    executable = tmp_path / "aside-descendant-fixture"
    executable.write_text(
        f"#!{sys.executable}\nimport json, os, signal, subprocess, sys\n"
        f"child=subprocess.Popen([sys.executable, '-c', {child_code!r}], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)\n"
        "assert child.stdout.readline() == b'ready\\n'\nchild.stdout.close()\n"
        f"def terminate(signum, frame):\n with open({str(termfile)!r}, 'w') as record: json.dump({{'leader':os.getpid(),'pgid':os.getpgrp()}}, record)\n os._exit(0)\n"
        "signal.signal(signal.SIGTERM, terminate)\n"
        f"with open({str(leaderfile)!r}, 'w') as record: json.dump({{'leader':os.getpid(),'pgid':os.getpgrp()}}, record)\n"
        "sys.stdin.read()\n"
        f"print({secret!r}, flush=True)\nsys.stderr.write({secret!r}+'\\n')\nsys.stderr.flush()\n"
        + ("os._exit(7)\n" if leader_exit == "early-nonzero" else "signal.pause()\n"),
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", str(executable))
    monkeypatch.setenv("NSG_ASIDE_GUARD_MS", "1000")
    try:
        with pytest.raises(AssertionError, match=guard) as failure:
            _browser([{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}])
        message = str(failure.value)
        assert message.splitlines()[-1] == guard
        assert "process-group SIGKILL cleanup; leader closure is not group absence" in message
        assert secret not in message
        descendant = json.loads(pidfile.read_text())
        leader = json.loads(leaderfile.read_text())
        if leader_exit == "deadline":
            assert json.loads(termfile.read_text()) == leader
        else:
            assert not termfile.exists(), "early nonzero exit must precede deadline SIGTERM"
        group = descendant["pgid"]
        assert leader["leader"] == leader["pgid"] == group
        assert descendant["pid"] != leader["leader"]
        with pytest.raises(ProcessLookupError):
            os.kill(descendant["pid"], 0)
        with pytest.raises(ProcessLookupError):
            os.killpg(group, 0)
    finally:
        if pidfile.exists():
            group = json.loads(pidfile.read_text())["pgid"]
            try:
                os.killpg(group, 9)
            except ProcessLookupError:
                pass


@pytest.mark.parametrize("channel", ("stdout", "stderr"))
def test_aside_cli_early_failure_does_not_disclose_external_payload(tmp_path, monkeypatch, channel):
    """An exited external CLI must fail without quoting its private stdout or stderr."""
    secret = "SYNTHETIC_PRIVATE_TAB_METADATA_DO_NOT_PUBLISH"
    executable = tmp_path / "aside-private-payload-fixture"
    envelope = {"run": {"content": [], "error": {"message": secret}}}
    executable.write_text(
        f"#!{sys.executable}\nimport sys\nsys.stdin.read()\n"
        + (
            f"print({json.dumps(envelope)!r})\n"
            if channel == "stdout"
            else f"sys.stderr.write({secret!r})\n"
        ),
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", str(executable))
    with pytest.raises(AssertionError, match="Aside exited before observation") as failure:
        _browser([{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}])
    assert secret not in str(failure.value)


@pytest.mark.parametrize(
    "mutation,guard",
    (
        ("malformed-json", "Aside CLI execution envelope invalid"),
        ("envelope-error", "Aside CLI reported an error"),
        ("receipt-extra", "Aside CLI completion receipt invalid"),
        ("receipt-value", "Aside CLI completion receipt invalid"),
        ("nonzero-exit", "Aside CLI failed"),
    ),
)
def test_aside_completed_cli_envelope_is_checked_without_echoing_opaque_values(
    tmp_path, monkeypatch, mutation, guard
):
    """Real execution cannot legitimize opaque CLI errors, malformed JSON or forged receipt fields."""
    real_cli = shutil.which(os.environ.get("ASIDE_BIN", "aside"))
    assert real_cli, "Aside CLI is required"
    secret = "SYNTHETIC_PRIVATE_TAB_METADATA_DO_NOT_PUBLISH"
    executable = tmp_path / "aside-envelope-mutation-fixture"
    executable.write_text(
        f"#!{sys.executable}\nimport json, subprocess, sys\n"
        f"result=subprocess.run([{real_cli!r},*sys.argv[1:]],input=sys.stdin.read(),text=True,capture_output=True)\n"
        f"mutation={mutation!r}\nsecret={secret!r}\n"
        "if mutation=='malformed-json':\n result.stdout=secret\n"
        "elif mutation=='nonzero-exit':\n result.stderr=secret\n result.returncode=7\n"
        "else:\n envelope=json.loads(result.stdout)\n"
        " if mutation=='envelope-error':\n  envelope['run']['error']={'message':secret}\n"
        " else:\n"
        "  for item in envelope['run']['content']:\n"
        "   if item.get('type')!='text': continue\n"
        "   lines=[]\n"
        "   for line in item.get('text','').splitlines():\n"
        "    try: receipt=json.loads(line)\n"
        "    except (ValueError,TypeError): receipt=None\n"
        "    if isinstance(receipt,dict) and receipt.get('nsgAsideReceipt') is True:\n"
        "     receipt['private_tab_metadata' if mutation=='receipt-extra' else 'commands']=secret\n"
        "     line=json.dumps(receipt)\n"
        "    lines.append(line)\n"
        "   item['text']='\\n'.join(lines)\n"
        " result.stdout=json.dumps(envelope)\n"
        "sys.stdout.write(result.stdout)\nsys.stderr.write(result.stderr)\nsys.exit(result.returncode)\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", str(executable))
    with pytest.raises(AssertionError, match=guard) as failure:
        _browser([{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}])
    assert secret not in str(failure.value)


def test_aside_publication_rejects_malformed_input_without_disclosing_parser_payload(monkeypatch):
    """Malformed stdin fails category-only before any browser operation can start."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", "/nonexistent-aside-entry-control")
    result = subprocess.run(
        ["node", str(ROOT / "tests/publication_presentation_driver.cjs")],
        input='{"private":"SYNTHETIC_PRIVATE_PARSER_PAYLOAD",',
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Aside fixture operation failed\n"


@pytest.mark.parametrize("boundary", ("missing-opt-in", "native-profile"))
def test_cloud_sdk_contract_transport_rejects_implicit_or_native_profile_execution(
    monkeypatch, boundary
):
    """The test facade cannot silently replace native Aside or open a native profile."""
    if boundary == "missing-opt-in":
        monkeypatch.delenv("NSG_ASIDE_TEST_TRANSPORT", raising=False)
    else:
        monkeypatch.setenv("NSG_ASIDE_TEST_TRANSPORT", "playwright")
        monkeypatch.setenv("NSG_ASIDE_PROFILE", "SYNTHETIC_PRIVATE_PROFILE_DO_NOT_PUBLISH")
    result = subprocess.run(
        ["node", str(ROOT / "tests/aside_playwright_contract_cli.cjs")],
        input="console.log('SYNTHETIC_WORKER_MUST_NOT_RUN');",
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Cloud SDK contract transport failed\n"


def test_explicit_aside_missing_cli_fails_in_driver_without_playwright_fallback(
    tmp_path, monkeypatch
):
    """A real failed spawn remains an error even when the cloud transport is available."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", str(tmp_path / "missing-aside-cli"))
    result = subprocess.run(
        ["node", str(ROOT / "tests/publication_presentation_driver.cjs")],
        input=json.dumps(
            {"figures": [{"svg": '<svg xmlns="http://www.w3.org/2000/svg"/>', "width": FULL_WIDTH}]}
        ),
        cwd=ROOT,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Aside fixture operation failed\n"


@pytest.mark.parametrize("inherited_cli", (None, "/nonexistent-aside-session-control"))
def test_cloud_transport_precedes_module_rendering_and_restores_session_environment(inherited_cli):
    """Real module renders precede function fixtures; negative overrides cannot poison later renders."""
    if os.environ.get("NSG_ASIDE_TEST_TRANSPORT") != "playwright":
        return
    _transport_fixture_session(
        inherited_cli,
        transport="playwright",
        tests=[
            "test_disclosure_matrix_has_single_column_readability_and_cell_clearance",
            "test_signal_figures_have_paper_scale_padding_and_no_text_collisions",
            "test_architecture_has_paper_scale_card_and_rotated_shield_clearance",
            "test_aside_backend_refuses_missing_or_incomplete_browser_execution[missing-cli]",
            "test_explicit_aside_missing_cli_fails_in_driver_without_playwright_fallback",
            "test_aside_main_world_bridge_preserves_untrusted_json_values_and_errors",
        ],
    )


@pytest.mark.parametrize("inherited_cli", (None, "/nonexistent-aside-session-control"))
def test_without_cloud_opt_in_fixture_preserves_native_cli_environment(inherited_cli):
    """Loading the suite without opt-in never installs a facade or changes a caller's CLI choice."""
    _transport_fixture_session(
        inherited_cli,
        transport=None,
        tests=["test_explicit_aside_missing_cli_fails_in_driver_without_playwright_fallback"],
    )


def _transport_fixture_session(inherited_cli, *, transport, tests):
    env = os.environ.copy()
    env["NSG_BROWSER_BACKEND"] = "aside"
    env["PYTEST_ADDOPTS"] = ""
    env.pop("ASIDE_BIN", None)
    env.pop("NSG_ASIDE_TEST_TRANSPORT", None)
    if inherited_cli is not None:
        env["ASIDE_BIN"] = inherited_cli
    if transport is not None:
        env["NSG_ASIDE_TEST_TRANSPORT"] = transport
    # A separate interpreter gives module fixtures a genuinely cold pytest session,
    # and exposes environment leaks after session teardown rather than hiding them at exit.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os, sys, pytest\n"
                "before = os.environ.get('ASIDE_BIN')\n"
                "class NativeEnvironment:\n"
                "    def pytest_runtest_call(self, item):\n"
                "        if 'NSG_ASIDE_TEST_TRANSPORT' not in os.environ:\n"
                "            assert os.environ.get('ASIDE_BIN') == before\n"
                "status = pytest.main(sys.argv[1:], plugins=[NativeEnvironment()])\n"
                "assert os.environ.get('ASIDE_BIN') == before, 'ASIDE_BIN leaked after session teardown'\n"
                "sys.exit(status)\n"
            ),
            "-q",
            *(f"tests/test_publication_presentation.py::{name}" for name in tests),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
