from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import generate_disclosure_paper_results as disclosure_producer
import validate_contribution_crosswalk as crosswalk_validator

from nesy_game.validator import VALIDATOR_CHECKS

E3_METRIC_ROWS = {
    "S0": "S0 degree baseline & 0.000 & 0.000 & 0.282 & 0.315 & 0.556",
    "S2": "S2 typed-lexical & 1.000 & 1.000 & 0.944 & 0.131 & 1.000",
}


def _normalized_latex(text: str) -> str:
    """Normalize only TeX wrappers/escaping, retaining semantic words and IDs."""
    text = text.replace(r"\_", "_")
    text = re.sub(r"\\text(?:tt|bf)\{", "", text)
    text = text.replace("}", "")
    return " ".join(text.split()).casefold()


def _table_rows(main_text: str, label: str) -> list[str]:
    match = re.search(
        rf"\\label\{{{re.escape(label)}\}}(?P<body>.*?)\\end\{{table\}}",
        main_text,
        flags=re.DOTALL,
    )
    assert match is not None, f"missing table {label}"
    return [
        _normalized_latex(line)
        for line in match.group("body").splitlines()
        if "&" in line and r"\\" in line
    ]


def _section(text: str, heading: str, next_heading: str) -> str:
    start = re.search(heading, text, flags=re.MULTILINE)
    assert start is not None, f"missing section matching {heading}"
    tail = text[start.end() :]
    end = re.search(next_heading, tail, flags=re.MULTILINE)
    return tail if end is None else tail[: end.start()]


def _discussion_intro(text: str, heading: str) -> str:
    body = _section(text, heading, r"^\\section\{")
    first_paragraph = body.split("\n\n", 1)[0]
    return first_paragraph.strip()


def test_validator_table_keeps_canonical_predicate_meanings_and_stage_policy_ownership() -> None:
    """The paper table must map each Python ID to its meaning and owner its stage error correctly."""
    ontology = json.loads(
        (ROOT / "game-track/web/dashboard/ontology-map.json").read_text(encoding="utf-8")
    )
    canonical = ontology["rule_sets"]["python7"]
    assert tuple(item["id"] for item in canonical) == VALIDATOR_CHECKS

    for language in ("en", "ko"):
        main = (ROOT / f"paper/latex/{language}/main.tex").read_text(encoding="utf-8")
        rows = _table_rows(main, "tab:validators")
        for predicate in canonical:
            predicate_id = predicate["id"].casefold()
            predicate_label = _normalized_latex(predicate["label"])
            label_aliases = {
                "object_reachability": "reachability",
                "forbidden_disclosure": "disclosure",
            }
            semantic_label = label_aliases.get(predicate_id, predicate_label)
            row = next(
                (
                    candidate
                    for candidate in rows
                    if predicate_id in candidate or semantic_label in candidate
                ),
                None,
            )
            assert row is not None, f"{language}: missing canonical predicate row {predicate['id']}"
            assert semantic_label in row

        policy_row = next(row for row in rows if "action policy" in row or "action_policy" in row)
        monotonicity_row = next(row for row in rows if "quest_stage_monotonicity" in row)
        eligibility_row = next(
            row
            for row in rows
            if ("quest stage" in row or "quest_stage" in row) and "monotonicity" not in row
        )

        assert "stage" in policy_row
        assert any(marker in policy_row for marker in ("unauthorized", "비인가"))
        assert any(marker in monotonicity_row for marker in ("regressive", "regression", "후퇴"))
        assert not any(marker in monotonicity_row for marker in ("unauthorized", "비인가"))
        assert (
            ("required" in eligibility_row and "current" in eligibility_row)
            or ("필요" in eligibility_row and "현재" in eligibility_row)
            or ("상위" in eligibility_row and "현재" in eligibility_row)
        )


@pytest.mark.parametrize("language", ("en", "ko"))
def test_e3_generated_table_is_in_effective_paper_closure_with_baseline(language: str) -> None:
    """Both editions must consume the generated E3 table, including its comparator row."""
    main_path = (ROOT / f"paper/latex/{language}/main.tex").resolve()
    closure = crosswalk_validator._tex_input_closure(main_path)
    generated_path = (
        ROOT / f"paper/latex/generated/kg_ontology_simulation_{language}.tex"
    ).resolve()
    assert generated_path in closure

    generated = generated_path.read_text(encoding="utf-8")
    closure_text = "\n".join(path.read_text(encoding="utf-8") for path in closure if path.is_file())
    for row in E3_METRIC_ROWS.values():
        assert row.casefold() in generated.casefold()
        assert row.casefold() in closure_text.casefold()
    assert "runtime" in generated.casefold() or "런타임" in generated or "실행" in generated
    assert "efficacy" in generated.casefold() or "효능" in generated

    e3 = _section(
        main_path.read_text(encoding="utf-8"),
        r"^\\subsection\{[^\n]*E3",
        r"^\\section\{",
    )
    assert rf"\input{{../generated/kg_ontology_simulation_{language}.tex}}" in e3
    # The manuscript section delegates the metrics to the generated input rather than
    # retaining a second, stale hand-transcribed metric block.
    e3_without_input = e3.replace(
        rf"\input{{../generated/kg_ontology_simulation_{language}.tex}}", ""
    )
    assert not any(
        metric in e3_without_input for metric in ("0.282", "0.315", "0.556", "0.944", "0.131")
    )


def test_bilingual_discussion_restores_repair_positioning_and_citation_parity() -> None:
    """The restored discussion must carry the same evidence boundary and S46--S48 citations."""
    intros = {}
    for language, heading in (("en", r"^\\section\{Discussion"), ("ko", r"^\\section\{논의\}")):
        text = (ROOT / f"paper/latex/{language}/main.tex").read_text(encoding="utf-8")
        intro = _discussion_intro(text, heading)
        intros[language] = intro
        citations = {
            key.strip()
            for group in re.findall(r"\\cite\{([^}]+)\}", intro)
            for key in group.split(",")
        }
        assert {
            "S45_madaan2023selfrefine",
            "S46_chen2023selfdebug",
            "S47_solarlezama2006sketching",
            "S48_shinn2023reflexion",
        } <= citations
        assert any(
            marker in intro.casefold()
            for marker in ("deterministic pre-execution", "deterministic pre-execution 오류")
        )
        assert "oracle-only" in intro.casefold()
        assert "capability" in intro.casefold()
        assert ("ontology" in intro.casefold() and "superiority" in intro.casefold()) or (
            "ontology" in intro.casefold() and "우월성" in intro
        )

    def citation_keys(value: str) -> set[str]:
        return {
            key.strip()
            for group in re.findall(r"\\cite\{([^}]+)\}", value)
            for key in group.split(",")
        }

    assert citation_keys(intros["en"]) == citation_keys(intros["ko"])


def test_disclosure_narrative_derives_actual_equality_counts_and_scopes_claim() -> None:
    """Generated bilingual prose must print comparison counts from the summary, not hardcoded 60/60."""
    data = disclosure_producer._load()
    for korean in (False, True):
        rendered = disclosure_producer._narrative(data, korean=korean)
        if korean:
            assert re.search(r"결과가 동일(?:하다|하지 않다)\(60/60\)", rendered)
        else:
            assert re.search(
                r"(?:identical outcomes|not identical)[^.\n]*60 (?:of|across) 60", rendered
            )
        assert "discriminating case" in rendered
        assert "authorization-conformance limit" in rendered
        assert "ontology superiority" in rendered

    mutated = copy.deepcopy(data)
    mutated["comparison"]["general_vs_ontology"]["equal_case_count"] = 7
    mutated["comparison"]["general_vs_ontology"]["case_count"] = 11
    for korean in (False, True):
        rendered = disclosure_producer._narrative(mutated, korean=korean)
        if korean:
            assert re.search(r"결과가 동일(?:하다|하지 않다)\(7/11\)", rendered)
        else:
            assert re.search(
                r"(?:identical outcomes|not identical)[^.\n]*7 (?:of|across) 11", rendered
            )
        assert "60/60" not in rendered and "60 of 60" not in rendered
