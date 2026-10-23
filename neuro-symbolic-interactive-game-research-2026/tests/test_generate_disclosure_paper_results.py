from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_disclosure_paper_results as producer

from scripts import check_disclosure_paper_evidence as checker


def _row(
    *,
    case_id: str,
    stratum: str,
    expected_allowed: bool,
    state_effect: str,
    observed_allowed: bool,
    mismatch: bool,
    mutated: bool,
    unsafe_violations: list[str] | None = None,
    arm: str = "unchecked_isolated",
) -> dict:
    return {
        "arm": arm,
        "case_id": case_id,
        "stratum": stratum,
        "expected": {"allowed": expected_allowed, "state_effect": state_effect},
        "observed": {"allowed": observed_allowed},
        "mismatch": mismatch,
        "mutated": mutated,
        "replay_equal": True,
        "state_assertion_failures": [],
        "display_assertion_failures": [],
        "unsafe_violations": unsafe_violations or [],
    }


def test_actual_generated_bilingual_outputs_preserve_numeric_evidence_parity() -> None:
    data = producer._load()
    english = (
        producer._narrative(data, korean=False)
        + producer._contract_table(data, korean=False)
        + producer._arms_table(data, korean=False)
        + producer._fixtures_table(data, korean=False)
    )
    korean = (
        producer._narrative(data, korean=True)
        + producer._contract_table(data, korean=True)
        + producer._arms_table(data, korean=True)
        + producer._fixtures_table(data, korean=True)
    )

    numeric_tokens = checker._numeric_tokens(english)
    assert numeric_tokens == checker._numeric_tokens(korean)
    assert all(numeric_tokens[value] > 0 for value in ("48", "4", "8", "60", "0"))


def _svg_text(element: ElementTree.Element) -> str:
    return " ".join(" ".join(element.itertext()).split())


def _svg_text_items(svg: str) -> tuple[float, list[tuple[ElementTree.Element, str, float | None]]]:
    root = ElementTree.fromstring(svg)
    width_match = re.fullmatch(r"([0-9.]+)(?:px|pt)?", root.attrib["width"])
    assert width_match is not None
    width = float(width_match.group(1))
    css_sizes: dict[str, tuple[float, str]] = {}
    for element in root.iter():
        if not element.tag.endswith("style") or not element.text:
            continue
        for selector, body in re.findall(r"\.([A-Za-z_][\w-]*)\s*\{([^}]*)\}", element.text):
            match = re.search(r"font-size\s*:\s*([0-9.]+)\s*(px|pt)?", body)
            if match:
                css_sizes[selector] = (float(match.group(1)), match.group(2) or "px")

    def font_size_px(element: ElementTree.Element) -> float | None:
        inline = re.search(
            r"font-size\s*:\s*([0-9.]+)\s*(px|pt)?",
            element.attrib.get("style", ""),
        )
        if inline:
            value, unit = float(inline.group(1)), inline.group(2) or "px"
            return value * (96 / 72 if unit == "pt" else 1)
        for class_name in element.attrib.get("class", "").split():
            if class_name in css_sizes:
                value, unit = css_sizes[class_name]
                return value * (96 / 72 if unit == "pt" else 1)
        return None

    publication_scale = 252.0 / width
    return width, [
        (
            element,
            _svg_text(element),
            None if (size := font_size_px(element)) is None else size * publication_scale,
        )
        for element in root.iter()
        if element.tag.endswith("text")
    ]


def test_svg_text_items_decodes_nested_tspans_and_tails_in_rendered_order() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="480">
      <text>normal <tspan>expected <tspan>E 47/1</tspan> n=48</tspan>
        <tspan>R 48/0</tspan><tspan>C 60/4</tspan><tspan>NR 8</tspan> end</text>
      <text>boundary</text>
    </svg>"""

    _width, text_items = _svg_text_items(svg)

    assert [text for _element, text, _size in text_items] == [
        "normal expected E 47/1 n=48 R 48/0 C 60/4 NR 8 end",
        "boundary",
    ]


def test_actual_svg_reports_fixture_cells_and_publication_legible_metrics() -> None:
    data = producer._load()
    svg = producer._svg(data)
    width, text_items = _svg_text_items(svg)
    assert width > 0
    root = ElementTree.fromstring(svg)
    texts = [text for _element, text, _size in text_items]
    texts.extend(
        _svg_text(element) for element in root.iter() if element.tag.endswith(("desc", "title"))
    )
    joined = " ".join(texts).lower()

    for label in producer.ARMS + ("normal", "boundary", "malformed"):
        assert label in joined
    for label in ("expected", "replay", "check", "pass", "fail", "nr"):
        assert label in joined
    assert "not pass" in joined and "skipped" in joined
    assert "out-of-scope" in joined or "out of scope" in joined
    assert "efficacy" in joined

    groups = {
        (group.attrib.get("data-arm"), group.attrib.get("data-stratum")): group
        for group in root.iter()
        if "data-arm" in group.attrib and "data-stratum" in group.attrib
    }
    assert len(groups) == 9
    cells = producer._signal_cells(data["rows"])
    arm_aliases = {"U": "unchecked_isolated", "G": "general_rule", "O": "ontology_gate"}
    stratum_aliases = {"N": "normal", "B": "boundary", "M": "malformed"}
    for (arm_value, stratum_value), group in groups.items():
        arm = arm_aliases.get(arm_value, arm_value)
        stratum = stratum_aliases.get(stratum_value, stratum_value)
        assert arm in producer.ARMS and stratum in {name for _prefix, name in producer.STRATA}
        cell = cells[arm][stratum]
        group_text = " ".join(_svg_text(node) for node in group.iter() if node.tag.endswith("text"))
        assert (
            f"E {cell['expected']['pass']}/{cell['expected']['fail']} n={cell['n']}" in group_text
        )
        assert f"R {cell['replay']['pass']}/{cell['replay']['fail']}" in group_text
        stratum_prefix = next(prefix for prefix, name in producer.STRATA if name == stratum)
        selected = [
            row for row in data["rows"] if row["arm"] == arm and row["stratum"] == stratum_prefix
        ]
        check_pass = sum(
            check["outcome"] == "pass" for row in selected for check in row.get("checks", [])
        )
        check_fail = sum(
            check["outcome"] == "fail" for row in selected for check in row.get("checks", [])
        )
        unreported_cases = sum(not row.get("checks") for row in selected)
        assert f"C {check_pass}/{check_fail} NR {unreported_cases}" in group_text

    numeric_text = re.compile(r"(?:^|\s)(?:E|R|C)\s+[0-9]+(?:/[0-9]+){1,2}")
    explanatory_text = re.compile(
        r"expected|replay|check|pass|fail|nr|normal|boundary|malformed|missing|unreported|efficacy|latent",
        re.IGNORECASE,
    )
    for _element, text, size in text_items:
        if numeric_text.search(text):
            assert size is not None and size >= 8, (text, size)
        if explanatory_text.search(text):
            assert size is not None and size >= 7, (text, size)


def test_arm_metrics_separates_semantic_mismatch_from_unique_unsafe_cases() -> None:
    rows = [
        # A denied case that is allowed is unsafe. Duplicate tags must not double-count it.
        _row(
            case_id="N-denied-but-allowed",
            stratum="N",
            expected_allowed=False,
            state_effect="denied_no_mutation",
            observed_allowed=True,
            mismatch=True,
            mutated=False,
            unsafe_violations=["unchecked_unauthorized_allow", "unchecked_unauthorized_allow"],
        ),
        # A permitted redisplay mutation is unsafe and also has a duplicate tag.
        _row(
            case_id="B-redisplay-mutated",
            stratum="B",
            expected_allowed=True,
            state_effect="redisplay_no_mutation",
            observed_allowed=True,
            mismatch=False,
            mutated=True,
            unsafe_violations=["unchecked_redisplay_mutation", "unchecked_redisplay_mutation"],
        ),
        # A permitted fresh representation mismatch is semantic, but explicitly not unsafe.
        _row(
            case_id="M-fresh-representation-mismatch",
            stratum="M",
            expected_allowed=True,
            state_effect="fresh_disclosure",
            observed_allowed=True,
            mismatch=True,
            mutated=False,
            unsafe_violations=["stale-unsafe-tag-must-be-ignored"],
        ),
        # Clean permitted and denied rows establish the non-failure denominators.
        _row(
            case_id="N-clean-permitted",
            stratum="N",
            expected_allowed=True,
            state_effect="fresh_disclosure",
            observed_allowed=True,
            mismatch=False,
            mutated=False,
        ),
        _row(
            case_id="B-clean-denied",
            stratum="B",
            expected_allowed=False,
            state_effect="denied_no_mutation",
            observed_allowed=False,
            mismatch=False,
            mutated=False,
        ),
    ]

    metrics = producer._arm_metrics(rows)
    unchecked = metrics["unchecked_isolated"]

    assert unchecked["case_count"] == 5
    assert unchecked["normal_case_count"] == 2
    assert unchecked["allowed_count"] == 4
    assert unchecked["denied_count"] == 1
    assert unchecked["expected_mismatch_count"] == 2
    assert unchecked["semantic_mismatch_by_stratum"] == {"N": 1, "B": 0, "M": 1}
    assert unchecked["state_assertion_failure_count"] == 0
    assert unchecked["display_assertion_failure_count"] == 0
    assert unchecked["replay_mismatch_count"] == 0

    assert unchecked["unsafe_violation_count"] == 2
    assert unchecked["unique_unsafe_case_count"] == 2
    assert unchecked["unsafe_by_stratum"] == {"N": 1, "B": 1, "M": 0}
    assert unchecked["unauthorized_allow_count"] == 1
    assert unchecked["unauthorized_allow_by_stratum"] == {"N": 1, "B": 0, "M": 0}
    assert unchecked["redisplay_mutation_count"] == 1
    assert unchecked["redisplay_mutation_by_stratum"] == {"N": 0, "B": 1, "M": 0}
    assert unchecked["permitted_fresh_representation_mismatch_count"] == 1
    assert unchecked["permitted_fresh_representation_mismatch_by_stratum"] == {
        "N": 0,
        "B": 0,
        "M": 1,
    }


def test_arms_table_labels_semantic_mismatches_and_unique_unsafe_cases_separately() -> None:
    metrics = {
        "case_count": 60,
        "normal_case_count": 48,
        "allowed_count": 60,
        "denied_count": 0,
        "expected_mismatch_count": 60,
        "semantic_mismatch_by_stratum": {"N": 48, "B": 4, "M": 8},
        "state_assertion_failure_count": 0,
        "display_assertion_failure_count": 0,
        "replay_mismatch_count": 0,
        "unsafe_violation_count": 51,
        "unique_unsafe_case_count": 51,
        "unsafe_by_stratum": {"N": 41, "B": 2, "M": 8},
        "unauthorized_allow_count": 44,
        "unauthorized_allow_by_stratum": {"N": 34, "B": 2, "M": 8},
        "redisplay_mutation_count": 7,
        "redisplay_mutation_by_stratum": {"N": 7, "B": 0, "M": 0},
        "permitted_fresh_representation_mismatch_count": 9,
        "permitted_fresh_representation_mismatch_by_stratum": {"N": 7, "B": 2, "M": 0},
    }
    zero_metrics = {key: 0 for key in metrics if key.endswith("_count")}
    zero_metrics.update(
        {
            "case_count": 60,
            "normal_case_count": 48,
            "semantic_mismatch_by_stratum": {"N": 0, "B": 0, "M": 0},
            "unsafe_by_stratum": {"N": 0, "B": 0, "M": 0},
            "unauthorized_allow_by_stratum": {"N": 0, "B": 0, "M": 0},
            "redisplay_mutation_by_stratum": {"N": 0, "B": 0, "M": 0},
            "permitted_fresh_representation_mismatch_by_stratum": {"N": 0, "B": 0, "M": 0},
        }
    )
    data = {
        "comparison": {
            "case_counts": {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
            "arms": {
                "unchecked_isolated": metrics,
                "general_rule": zero_metrics,
                "ontology_gate": zero_metrics,
            },
        }
    }

    for language in (False, True):
        table = producer._arms_table(data, korean=language)
        header = next(line for line in table.splitlines() if "Arm" in line and "n (N/B/M)" in line)
        row = next(line for line in table.splitlines() if line.startswith(r"unchecked\_isolated"))
        cells = [cell.strip() for cell in row.removesuffix(r"\\").split("&")]
        assert len(cells) == 7
        assert cells[3] == "60"
        assert cells[6] == "51"
        assert "Semantic mismatch" in header
        assert "Unique unsafe" in header
        assert cells[3] != cells[6]
