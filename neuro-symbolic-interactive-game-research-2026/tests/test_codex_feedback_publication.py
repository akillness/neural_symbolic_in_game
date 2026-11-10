from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "research" / "codex_feedback_pilot"
COHORT = "paired-model-comparison-20261110-v5"
PUBLIC = PILOT / "public-v5"
SELECTORS = ("gpt-5.6-luna", "gpt-5.6-terra")
CONDITIONS = {
    "en": {"Detailed": "detailed", "Generic": "generic"},
    "ko": {"상세": "detailed", "일반": "generic"},
}
FIXTURES = {
    "missing_precondition",
    "missing_effect",
    "unauthorized_objective",
    "forbidden_disclosure",
    "unsatisfied_dependency",
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def cohorts():
    return {
        selector: _load(PUBLIC / f"{COHORT}-{selector}" / "results.json") for selector in SELECTORS
    }


def _receipt_counts(result):
    # Match all frozen assignments, not a pooled cohort or only successful rows.
    assigned = {
        (case_id, condition) for case_id in FIXTURES for condition in ("detailed", "generic")
    }
    assert Counter((row["case_id"], row["condition"]) for row in result["cases"]) == Counter(
        assigned
    )
    selector = result["metadata"]["model_selector"]
    assert selector in SELECTORS
    assert result["metadata"]["codex_executable"] is None
    assert result["public_projection"]["schema"] == "paired-feedback-public-projection/1"
    assert result["public_projection"]["omitted_fields"] == ["metadata.codex_executable"]

    counts = {condition: Counter() for condition in ("detailed", "generic")}
    for row in result["cases"]:
        prompt_path = PUBLIC / f"{COHORT}-{selector}" / row["prompt_file"]
        prompt_bytes = prompt_path.read_bytes()
        assert hashlib.sha256(prompt_bytes).hexdigest() == row["prompt_sha256"]
        prompt = json.loads(prompt_bytes.decode("utf-8").splitlines()[1])
        for field, prompt_field in (
            ("initial_state", "state"),
            ("shared_proposal", "candidate"),
            ("input_signal", "validator_feedback"),
        ):
            assert row[field] == prompt[prompt_field]
        count = counts[row["condition"]]
        count["assigned"] += 1
        count["pending"] += row["status"] == "PENDING"
        assert row["status"] in {"COMPLETED", "FAILED"}
        count["completed"] += row["status"] == "COMPLETED"
        count["failed"] += row["status"] == "FAILED"

        # A schema failure still has a completed adapter response, not a transport failure.
        evidence = row["evidence"]
        assert evidence["returncode"] == 0
        assert evidence["stdout"]["complete"] is True
        events = evidence["events"]
        assert any(
            event["type"] == "item.completed" and event["item_type"] == "agent_message"
            for event in events
        )
        assert any(event["type"] == "turn.completed" for event in events)
        if row["status"] == "FAILED":
            assert row["failure"]["code"] == "evaluation_error"
            assert row["failure"]["type"] in {"JSONDecodeError", "CandidateParseError"}
            assert row["evaluation"] is None
            assert row["response_bytes"] > 0
            assert re.fullmatch(r"[0-9a-f]{64}", row["response_sha256"])
            count["schema_failed"] += 1
        else:
            assert row["failure"] is None
            # Parse the retained output; an empty/missing receipt cannot count as received.
            assert json.loads(row["response_text"]) == row["evaluation"]["final_candidate"]
            evaluation = row["evaluation"]
            count["gate_accepted"] += evaluation["final_gate_accepted"] is True
            count["objective_reached"] += evaluation["objective_reached"] is True
        count["received"] += 1
    return counts


@pytest.mark.parametrize("selector", SELECTORS)
def test_v5_receipts_keep_failed_assignments_in_complete_cohort(cohorts, selector):
    result = cohorts[selector]
    counts = _receipt_counts(result)
    for condition, count in counts.items():
        assert count["assigned"] == count["received"] == 5
        assert count["pending"] == 0
        assert count["schema_failed"] == count["failed"]
        assert result["summary"][condition] == {
            key: count[key]
            for key in (
                "assigned",
                "completed",
                "failed",
                "pending",
                "gate_accepted",
                "objective_reached",
            )
        }


@pytest.mark.parametrize("language", ("en", "ko"))
def test_published_v5_numeric_rows_match_receipts_in_each_language(cohorts, language):
    expected = {}
    for selector, result in cohorts.items():
        for condition, count in _receipt_counts(result).items():
            expected[(selector, condition)] = tuple(
                (count[key], count["assigned"])
                for key in ("received", "gate_accepted", "objective_reached", "schema_failed")
            )

    # TeX is the published data artifact here, not implementation-source text.
    text = (ROOT / "paper" / "latex" / language / "main.tex").read_text(encoding="utf-8")
    tables = [
        table
        for table in re.findall(r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", text, re.DOTALL)
        if r"\label{tab:paired-feedback-v5}" in table
    ]
    assert len(tables) == 1
    body = tables[0].split(r"\midrule", 1)[1].split(r"\bottomrule", 1)[0]
    actual = {}
    for row in body.split(r"\\"):
        if not row.strip():
            continue
        selector_cell, signal, *values = [cell.strip() for cell in row.split("&")]
        selector = re.fullmatch(r"\\texttt\{([^{}]+)\}", selector_cell).group(1)
        key = selector, CONDITIONS[language][signal]
        assert key not in actual
        assert len(values) == 4
        assert all(re.fullmatch(r"\d+\s*/\s*\d+", value) for value in values)
        actual[key] = tuple(tuple(map(int, value.split("/"))) for value in values)
    assert actual == expected


@pytest.mark.parametrize("selector", SELECTORS)
def test_frozen_v5_source_zip_matches_public_receipt_hashes(cohorts, selector):
    hashes = cohorts[selector]["metadata"]["source_sha256"]
    # Live source may be cleaned up after collection; the frozen ZIP is authoritative.
    with ZipFile(PILOT / f"{COHORT}-source.zip") as archive:
        members = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
        assert Counter(members) == Counter(hashes.keys())
        for name, digest in hashes.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest, name


def test_v5_visual_manifest_links_bilingual_papers_to_actual_evidence_bytes():
    manifest = _load(ROOT / "visuals" / "source-manifest.json")
    entries = [entry for entry in manifest["table_sources"] if entry["id"] == "paired-feedback-v5"]
    assert len(entries) == 1
    table = entries[0]
    assert table["anchors"] == ["tab:paired-feedback-v5"]
    assert Counter(table["rendered_in"]) == Counter(("paper-en", "paper-ko"))
    layouts = [f"paper/latex/{language}/main.tex" for language in ("en", "ko")]
    data = [
        f"research/codex_feedback_pilot/public-v5/{COHORT}-{selector}/results.json"
        for selector in SELECTORS
    ] + [f"research/codex_feedback_pilot/{COHORT}-source.zip"]

    def verify_receipts(receipts, paths):
        assert Counter(receipt["path"] for receipt in receipts) == Counter(paths)
        for receipt in receipts:
            payload = (ROOT / receipt["path"]).read_bytes()
            assert receipt["bytes"] == len(payload), receipt["path"]
            assert receipt["sha256"] == hashlib.sha256(payload).hexdigest(), receipt["path"]

    verify_receipts(table["layout_sources"], layouts)
    verify_receipts(table["data_sources"], data)
    surfaces = [
        surface
        for surface in manifest["rendered_surfaces"]
        if surface["id"] in table["rendered_in"]
    ]
    assert Counter(surface["id"] for surface in surfaces) == Counter(table["rendered_in"])
    for surface in surfaces:
        language = surface["id"].removeprefix("paper-")
        verify_receipts([surface["editable_source"]], [f"paper/latex/{language}/main.tex"])
        verify_receipts([surface["artifact"]], [f"paper/latex/{language}/main.pdf"])
