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


# Approved frozen inventory: assigned, completed, failed, IN_PROGRESS, PENDING,
# gate accepted, objective reached, evaluated candidates. No private originals
# are needed to defend these public snapshot counts in CI.
HISTORY_COUNTS = {
    "codex-feedback-pilot-20261110": (10, 0, 7, 0, 3, 0, 0, 0),
    "codex-feedback-pilot-v2-20261110-luna": (10, 0, 0, 0, 10, 0, 0, 0),
    "codex-feedback-pilot-v2-20261110-terra": (10, 0, 0, 0, 10, 0, 0, 0),
    "codex-feedback-pilot-v2-diagnostic-20261110-luna": (10, 0, 0, 1, 9, 0, 0, 0),
    "codex-feedback-pilot-v2-diagnostic-20261110-terra": (10, 0, 1, 0, 9, 0, 0, 0),
    "codex-feedback-pilot-v2-evidence-20261110-luna": (10, 0, 1, 0, 9, 0, 0, 0),
    "codex-feedback-pilot-v2-evidence-20261110-terra": (10, 0, 1, 0, 9, 0, 0, 0),
    "gpt-5.6-luna": (10, 0, 0, 0, 10, 0, 0, 0),
    "gpt-5.6-luna-native-0.167.0": (10, 0, 0, 0, 10, 0, 0, 0),
    "gpt-5.6-terra": (10, 0, 0, 0, 10, 0, 0, 0),
    "gpt-5.6-terra-native-0.167.0": (10, 0, 0, 0, 10, 0, 0, 0),
    "paired-model-comparison-20261110-v3-gpt-5.6-luna": (10, 0, 0, 0, 10, 0, 0, 0),
    "paired-model-comparison-20261110-v3-gpt-5.6-terra": (10, 0, 0, 0, 10, 0, 0, 0),
    "paired-model-comparison-20261110-v4-gpt-5.6-luna": (10, 10, 0, 0, 0, 9, 8, 10),
    "paired-model-comparison-20261110-v4-gpt-5.6-terra": (10, 0, 1, 0, 9, 0, 0, 0),
    "paired-model-comparison-20261110-v5-gpt-5.6-luna": (10, 9, 1, 0, 0, 7, 6, 9),
    "paired-model-comparison-20261110-v5-gpt-5.6-terra": (10, 1, 9, 0, 0, 1, 1, 1),
    "startup-diagnostic-20261110-1794306144015386000-gpt-5.6-luna": (10, 0, 1, 0, 9, 0, 0, 0),
    "startup-diagnostic-20261110-1794306144015386000-gpt-5.6-terra": (10, 0, 1, 0, 9, 0, 0, 0),
}
HISTORY_COUNT_FIELDS = (
    "assigned",
    "completed",
    "failed",
    "IN_PROGRESS",
    "PENDING",
    "gate_accepted",
    "objective_reached",
    "evaluated_candidate_count",
)


@pytest.fixture(scope="module")
def history_inventory():
    return _load(PILOT / "public-history-20261111" / "cohort-inventory.json")


def test_public_history_represents_each_frozen_cohort_once(history_inventory):
    assert Counter(row["cohort"] for row in history_inventory["rows"]) == Counter(
        HISTORY_COUNTS.keys()
    )


@pytest.mark.parametrize("cohort", HISTORY_COUNTS)
def test_public_history_preserves_per_cohort_status_and_success_accounting(
    history_inventory, cohort
):
    rows = [row for row in history_inventory["rows"] if row["cohort"] == cohort]
    assert len(rows) == 1
    row = rows[0]
    counts = tuple(row[field] for field in HISTORY_COUNT_FIELDS)
    assert all(type(value) is int and value >= 0 for value in counts)
    assert counts == HISTORY_COUNTS[cohort]
    assert row["assigned"] == sum(
        row[field] for field in ("completed", "failed", "IN_PROGRESS", "PENDING")
    )
    assert 0 <= row["gate_accepted"] <= row["evaluated_candidate_count"] <= row["assigned"]
    assert 0 <= row["objective_reached"] <= row["evaluated_candidate_count"]
    expected_selector = (
        "gpt-6-luna"
        if cohort == "codex-feedback-pilot-20261110"
        else ("gpt-5.6-luna" if "luna" in cohort else "gpt-5.6-terra")
    )
    assert row["requested_selector"] == expected_selector


@pytest.mark.parametrize("selector", SELECTORS)
def test_public_history_v5_counts_and_digest_match_public_receipts(
    history_inventory, cohorts, selector
):
    row = next(row for row in history_inventory["rows"] if row["cohort"] == f"{COHORT}-{selector}")
    result = cohorts[selector]
    cases = result["cases"]
    statuses = Counter(case["status"] for case in cases)
    assert row["assigned"] == len(cases)
    for field, status in (
        ("completed", "COMPLETED"),
        ("failed", "FAILED"),
        ("IN_PROGRESS", "IN_PROGRESS"),
        ("PENDING", "PENDING"),
    ):
        assert row[field] == statuses[status]
    evaluations = [case["evaluation"] for case in cases if case["evaluation"] is not None]
    assert row["evaluated_candidate_count"] == len(evaluations)
    assert row["gate_accepted"] == sum(
        evaluation["final_gate_accepted"] is True for evaluation in evaluations
    )
    assert row["objective_reached"] == sum(
        evaluation["objective_reached"] is True for evaluation in evaluations
    )
    assert row["received_response_count"] == sum(
        case["evidence"]["returncode"] == 0
        and any(event["type"] == "turn.completed" for event in case["evidence"]["events"])
        for case in cases
    )
    assert row["raw_source_sha256"] == result["public_projection"]["raw_source_sha256"]


def test_public_history_retains_only_safe_aggregate_fields_and_unknowns(history_inventory):
    assert set(history_inventory) == {
        "schema_version",
        "counting_unit",
        "source_digest_scope",
        "source_reproducibility_limitation",
        "rows",
        "caveats",
    }
    allowed_row_fields = {
        "cohort",
        "requested_selector",
        "raw_source_sha256",
        "scope",
        "actual_model_identity",
        "cost_usd",
        "provider_request_count",
        *HISTORY_COUNT_FIELDS,
    }
    for row in history_inventory["rows"]:
        expected_fields = allowed_row_fields | (
            {"received_response_count"} if row["cohort"].startswith(f"{COHORT}-") else set()
        )
        assert set(row) == expected_fields, row["cohort"]
        for field in ("actual_model_identity", "cost_usd", "provider_request_count"):
            assert row[field] is None, (row["cohort"], field)
        assert re.fullmatch(r"[0-9a-f]{64}", row["raw_source_sha256"])
        assert isinstance(row["scope"], str)

    def assert_no_local_paths(value):
        if isinstance(value, dict):
            for item in value.values():
                assert_no_local_paths(item)
        elif isinstance(value, list):
            for item in value:
                assert_no_local_paths(item)
        elif isinstance(value, str):
            assert not re.search(r"/(?:Users|home|tmp|private|var)/|~/|[A-Za-z]:\\", value)

    assert_no_local_paths(history_inventory)
