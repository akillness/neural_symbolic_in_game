"""Publication gates reconcile visible bilingual claims with real blocked-pilot artifacts."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import generate_prospective_pilot_results as generator

from nesy_game import prospective_pilot as pilot

START = "<!-- prospective-pilot:start -->"
END = "<!-- prospective-pilot:end -->"
RUNTIME = "| Runtime | 60 | 60 | 0 | 0 | 0 |"
DEVELOPMENT = "| Development | 120 | 120 | 0 | 0 | 0 |"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _section() -> str:
    return (
        f"{START}\n"
        f"Study: `{pilot.STUDY_ID}`\n\n"
        "Status: **NOT_RUN/BLOCKED**; conclusion: `NOT_MET`.\n\n"
        "| Track | Planned | Blocked | Assigned | Attempted | Executed |\n"
        "| :--- | ---: | ---: | ---: | ---: | ---: |\n"
        f"{RUNTIME}\n{DEVELOPMENT}\n"
        f"{END}\n"
    )


@pytest.fixture
def publication_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ModuleType, Path, Path, Path]:
    module_spec = importlib.util.spec_from_file_location(
        "prospective_publication_cli_under_test",
        ROOT / "scripts/run_prospective_pilot.py",
    )
    assert module_spec is not None and module_spec.loader is not None
    cli = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cli)
    root = tmp_path / "repository" / "research-root"
    study = root / "research" / pilot.STUDY_ID
    tex = root / "paper/latex/generated/prospective-pilot"
    monkeypatch.setattr(cli, "ROOT", root)

    def forbid_process(*args, **kwargs):
        raise AssertionError("Publication verification must not invoke git, a model, or a process")

    monkeypatch.setattr(cli, "_git", forbid_process)
    protocol = pilot.build_protocol()
    collection = pilot.collect(
        protocol,
        pilot.evaluate_admission(protocol, {}),
        process_factory=forbid_process,
    )
    _write(study / cli.PROTOCOL, json.dumps(protocol, ensure_ascii=False))
    _write(study / "results-v1/collection-status.json", json.dumps(collection, ensure_ascii=False))
    generator.generate_results(protocol, collection, study / "results-v1", tex)
    for language in ("en", "ko"):
        _write(
            root / f"paper/latex/{language}/main.tex",
            "\\documentclass{article}\n\\begin{document}\n"
            f"\\input{{../generated/prospective-pilot/status_{language}.tex}}\n"
            "\\end{document}\n",
        )
    _write(
        root.parent / "README.md",
        "# Independent English title\n\n" + _section() + "\nOther prose.\n",
    )
    _write(
        root.parent / "README.ko.md",
        "# 자유로운 한국어 제목\n\n" + _section() + "\n별도 설명입니다.\n",
    )
    return cli, root, study, tex


def _verify(
    bundle: tuple[ModuleType, Path, Path, Path],
    scope: str,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, dict]:
    cli, _, study, tex = bundle
    # Explicit artifact locations exercise publication behavior, not parser defaults.
    code = cli.main(
        [
            "verify-analysis",
            "--scope",
            scope,
            "--study-root",
            str(study),
            "--collection",
            str(study / "results-v1/collection-status.json"),
            "--summary",
            str(study / "results-v1/summary.json"),
            "--tex-dir",
            str(tex),
        ]
    )
    return code, json.loads(capsys.readouterr().out)


def _assert_failure(code: int, receipt: dict) -> None:
    assert code == 1, receipt
    assert receipt["status"] == "FAIL", receipt
    assert receipt["errors"], receipt


@pytest.mark.parametrize("scope", ["manuscript", "readme"])
def test_publication_cli_accepts_reconciled_bilingual_claims(
    publication_bundle: tuple,
    scope: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, receipt = _verify(publication_bundle, scope, capsys)
    assert code == 0, receipt
    assert receipt["status"] == "PASS", receipt
    assert receipt["result"]["scope"] == scope
    assert receipt["result"]["counts"] == {
        "planned": 180,
        "blocked": 180,
        "assigned": 0,
        "attempted": 0,
        "executed": 0,
        "failed": 0,
        "missing": 0,
        "successful": 0,
        "identity_qualified": 0,
        "replayed": 0,
    }


@pytest.mark.parametrize("language", ["en", "ko"])
@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "other-language", "extra-other-language", "comment-only"]
)
def test_manuscript_cli_rejects_missing_duplicate_or_cross_language_input(
    publication_bundle: tuple,
    language: str,
    mutation: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, root, _, _ = publication_bundle
    path = root / f"paper/latex/{language}/main.tex"
    source = path.read_text(encoding="utf-8")
    own = f"\\input{{../generated/prospective-pilot/status_{language}.tex}}"
    other = (
        f"\\input{{../generated/prospective-pilot/status_{'ko' if language == 'en' else 'en'}.tex}}"
    )
    replacements = {
        "missing": "",
        "duplicate": own + "\n" + own,
        "other-language": other,
        "extra-other-language": own + "\n" + other,
        "comment-only": "% " + own,
    }
    _write(path, source.replace(own, replacements[mutation]))
    _assert_failure(*_verify(publication_bundle, "manuscript", capsys))


@pytest.mark.parametrize("scope", ["manuscript", "readme"])
@pytest.mark.parametrize(
    "mutation", ["summary-total", "summary-track", "collection-count", "raw-row"]
)
def test_publication_cli_rejects_aggregate_claims_not_supported_by_raw_units(
    publication_bundle: tuple,
    scope: str,
    mutation: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, study, _ = publication_bundle
    name = "summary.json" if mutation.startswith("summary-") else "collection-status.json"
    path = study / "results-v1" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "summary-total":
        data["counts"]["blocked"] = 179
    elif mutation == "summary-track":
        # Preserve the grand total while attributing one runtime unit to development.
        data["tracks"]["runtime"]["planned"] = 59
        data["tracks"]["development"]["planned"] = 121
    elif mutation == "collection-count":
        data["counts"]["executed"] = 1
    else:
        data["rows"].pop()
    _write(path, json.dumps(data, ensure_ascii=False))
    _assert_failure(*_verify(publication_bundle, scope, capsys))


@pytest.mark.parametrize("language", ["en", "ko"])
@pytest.mark.parametrize("mutation", ["planned", "blocked", "executed", "other-language"])
def test_manuscript_cli_rejects_false_generated_fragment_even_with_correct_count_decoys(
    publication_bundle: tuple,
    language: str,
    mutation: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, _, _, tex = publication_bundle
    path = tex / f"status_{language}.tex"
    text = path.read_text(encoding="utf-8")
    if mutation == "other-language":
        other = "ko" if language == "en" else "en"
        text = (tex / f"status_{other}.tex").read_text(encoding="utf-8")
    else:
        before, after = {
            "en": {
                "planned": ("plans 180 units", "plans 181 units"),
                "blocked": ("180 are blocked", "179 are blocked"),
                "executed": ("0 executed", "1 executed"),
            },
            "ko": {
                "planned": ("180개 단위", "181개 단위"),
                "blocked": ("180개 차단", "179개 차단"),
                "executed": ("0개 실행", "1개 실행"),
            },
        }[language][mutation]
        assert before in text  # Ensure the mutation actually changes the generated claim.
        text = text.replace(before, after, 1)
        text += "% Historical numbers are not the prospective claim: 180 60 120 0.\n"
    _write(path, text)
    _assert_failure(*_verify(publication_bundle, "manuscript", capsys))


@pytest.mark.parametrize("filename", ["README.md", "README.ko.md"])
@pytest.mark.parametrize(
    "mutation",
    [
        "missing-start",
        "missing-end",
        "duplicate-start",
        "duplicate-end",
        "duplicate-section",
        "reversed",
    ],
)
def test_readme_cli_requires_one_well_bounded_visible_count_section(
    publication_bundle: tuple,
    filename: str,
    mutation: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, root, _, _ = publication_bundle
    path = root.parent / filename
    text = path.read_text(encoding="utf-8")
    if mutation == "duplicate-section":
        text += _section()
    elif mutation == "reversed":
        text = (
            text.replace(START, "SECTION_START").replace(END, START).replace("SECTION_START", END)
        )
    else:
        marker = START if mutation.endswith("start") else END
        text = text.replace(
            marker, "" if mutation.startswith("missing") else marker + "\n" + marker
        )
    _write(path, text)
    _assert_failure(*_verify(publication_bundle, "readme", capsys))


@pytest.mark.parametrize("filename", ["README.md", "README.ko.md"])
@pytest.mark.parametrize("track", ["Runtime", "Development"])
@pytest.mark.parametrize("column", ["Planned", "Blocked", "Assigned", "Attempted", "Executed"])
def test_readme_cli_reconciles_each_visible_track_count_not_hidden_correct_numbers(
    publication_bundle: tuple,
    filename: str,
    track: str,
    column: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, root, _, _ = publication_bundle
    path = root.parent / filename
    row = RUNTIME if track == "Runtime" else DEVELOPMENT
    cells = [cell.strip() for cell in row.strip("|").split("|")]
    index = ["Track", "Planned", "Blocked", "Assigned", "Attempted", "Executed"].index(column)
    cells[index] = str(int(cells[index]) + 1)
    wrong = "| " + " | ".join(cells) + " |"
    # A substring/count-presence checker can still find every correct value in this comment.
    text = path.read_text(encoding="utf-8").replace(row, wrong + f"\n<!-- {row} -->")
    _write(path, text)
    _assert_failure(*_verify(publication_bundle, "readme", capsys))


@pytest.mark.parametrize("filename", ["README.md", "README.ko.md"])
@pytest.mark.parametrize(
    "mutation",
    [
        "missing-study",
        "missing-status",
        "missing-conclusion",
        "mixed-status",
        "mixed-conclusion",
        "hidden-status",
        "hidden-table",
        "missing-track",
        "duplicate-track",
        "extra-track",
    ],
)
def test_readme_cli_rejects_missing_hidden_or_contradictory_publication_claims(
    publication_bundle: tuple,
    filename: str,
    mutation: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _, root, _, _ = publication_bundle
    path = root.parent / filename
    text = path.read_text(encoding="utf-8")
    if mutation == "missing-study":
        text = text.replace(pilot.STUDY_ID, "unrelated-study")
    elif mutation == "missing-status":
        text = text.replace("NOT_RUN/BLOCKED", "UNKNOWN")
    elif mutation == "missing-conclusion":
        text = text.replace("NOT_MET", "UNKNOWN")
    elif mutation == "mixed-status":
        text = text.replace("**NOT_RUN/BLOCKED**", "**NOT_RUN/BLOCKED**; status: **PASS**")
    elif mutation == "mixed-conclusion":
        text = text.replace("`NOT_MET`", "`NOT_MET`; conclusion: `MET`")
    elif mutation == "hidden-status":
        text = text.replace(
            "Status: **NOT_RUN/BLOCKED**; conclusion: `NOT_MET`.",
            "<!-- Status: NOT_RUN/BLOCKED; conclusion: NOT_MET. -->",
        )
    elif mutation == "hidden-table":
        text = text.replace("| Track |", "<!--\n| Track |").replace(
            DEVELOPMENT, DEVELOPMENT + "\n-->"
        )
    elif mutation == "missing-track":
        text = text.replace(DEVELOPMENT, "")
    elif mutation == "duplicate-track":
        text = text.replace(DEVELOPMENT, DEVELOPMENT + "\n" + DEVELOPMENT)
    else:
        text = text.replace(DEVELOPMENT, DEVELOPMENT + "\n| Historical | 8 | 0 | 8 | 8 | 8 |")
    _write(path, text)
    _assert_failure(*_verify(publication_bundle, "readme", capsys))


@pytest.mark.parametrize("language", ["en", "ko"])
@pytest.mark.parametrize(
    "claim",
    [
        "runtime",
        "development",
        "total",
        "success-rate",
        "observed-cost",
        "cost-subtotal",
        "effect",
    ],
)
def test_manuscript_cli_recounts_visible_claims_independently_of_poisoned_renderer(
    publication_bundle: tuple,
    language: str,
    claim: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli, _, study, tex = publication_bundle
    original_fragment = generator._fragment
    replacements = {
        "en": {
            "runtime": ("60 runtime", "120 runtime"),
            "development": ("120 development", "60 development"),
            "total": ("plans 180 units", "plans 181 units"),
            "success-rate": ("Success rate: null", "Success rate: 0"),
            "observed-cost": ("Observed cost: null", "Observed cost: 0"),
            "cost-subtotal": ("known subtotal null", "known subtotal 0"),
            "effect": ("Effect estimate: null", "Effect estimate: 0"),
        },
        "ko": {
            "runtime": ("런타임 60개", "런타임 120개"),
            "development": ("개발 120개", "개발 60개"),
            "total": ("180개 단위", "181개 단위"),
            "success-rate": ("성공률: null", "성공률: 0"),
            "observed-cost": ("관측 비용: null", "관측 비용: 0"),
            "cost-subtotal": ("알려진 부분합 null", "알려진 부분합 0"),
            "effect": ("효과 추정: null", "효과 추정: 0"),
        },
    }
    before, after = replacements[language][claim]

    def poisoned_fragment(summary: dict, collection: dict, rendered_language: str) -> str:
        text = original_fragment(summary, collection, rendered_language)
        if rendered_language == language:
            assert before in text  # The fault must change a real labeled visible claim.
            return text.replace(before, after, 1)
        return text

    monkeypatch.setattr(generator, "_fragment", poisoned_fragment)
    protocol = json.loads((study / cli.PROTOCOL).read_text(encoding="utf-8"))
    collection_path = study / "results-v1/collection-status.json"
    collection_bytes = collection_path.read_bytes()
    collection = json.loads(collection_bytes)
    summary_path = study / "results-v1/summary.json"
    summary_bytes = summary_path.read_bytes()
    generator.generate_results(protocol, collection, study / "results-v1", tex)
    assert summary_path.read_bytes() == summary_bytes
    assert collection_path.read_bytes() == collection_bytes
    published = (tex / f"status_{language}.tex").read_text(encoding="utf-8")
    assert after in published and before not in published

    code, receipt = _verify(publication_bundle, "manuscript", capsys)
    _assert_failure(code, receipt)
    assert any(f"status_{language}.tex" in error for error in receipt["errors"]), receipt
