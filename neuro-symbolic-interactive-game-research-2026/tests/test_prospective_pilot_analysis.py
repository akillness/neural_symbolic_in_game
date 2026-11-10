"""Reporting contracts keep blocked observations, unknowns, and historical lanes honest."""

from __future__ import annotations

import copy
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import generate_prospective_pilot_results as generator

from nesy_game import prospective_pilot as pilot


def blocked_collection() -> tuple[dict, dict]:
    protocol = pilot.build_protocol()

    def forbid(*args, **kwargs):
        raise AssertionError("Analysis fixture attempted process creation")

    result = pilot.collect(protocol, pilot.evaluate_admission(protocol, {}), process_factory=forbid)
    return protocol, result


def test_empty_admission_is_not_zero_success_or_zero_measured_cost() -> None:
    protocol, collection = blocked_collection()
    summary = pilot.reconcile_results(protocol, collection["rows"])
    assert summary["counts"] == {
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
    assert summary["tracks"]["runtime"]["planned"] == 60
    assert summary["tracks"]["development"]["planned"] == 120
    assert summary["success_rate"] is None
    assert summary["observed_cost"] is None
    assert summary["effect_estimate"] is None
    assert summary["status"] == "NOT_RUN/BLOCKED"
    assert summary["conclusion"] == "NOT_MET"


def test_independent_raw_accounting_retains_failure_and_admitted_missingness() -> None:
    protocol, collection = blocked_collection()
    rows = collection["rows"]
    for index in range(3):
        rows[index].update(admitted=True, blocked_reasons=[])
    rows[0].update(
        dispatch_attempts=1,
        native_process_starts=1,
        executed=True,
        identity_qualified=True,
        terminal_outcome="success",
        successful=True,
        safety_gate="PASS",
        actual_model="gpt-5.6-sol",
        actual_engine="synthetic-fixture",
        cost=None,
        replayed=True,
    )
    rows[1].update(
        dispatch_attempts=1,
        native_process_starts=1,
        executed=False,
        terminal_outcome="timeout",
        successful=False,
        cost=0.25,
    )
    # Third admitted assignment has no terminal record: it is missing, never dropped.
    rows[2].update(terminal_outcome=None, successful=None)
    summary = pilot.reconcile_results(protocol, rows)
    assert summary["counts"] == {
        "planned": 180,
        "blocked": 177,
        "assigned": 3,
        "attempted": 2,
        "executed": 1,
        "failed": 1,
        "missing": 1,
        "successful": 1,
        "identity_qualified": 1,
        "replayed": 1,
    }
    assert summary["success_rate"] == pytest.approx(1 / 3)
    assert summary["observed_cost"] is None  # Partial cost observations cannot imply a total.
    assert summary["known_cost_subtotal"] == 0.25
    assert summary["unknown_cost_units"] == 2
    assert summary["tracks"]["development"]["attempted"] == 0


@pytest.mark.parametrize("mutation", ["duplicate", "drop", "unknown", "track", "blocked_success"])
def test_raw_reconciliation_rejects_membership_drift_and_impossible_results(mutation: str) -> None:
    protocol, collection = blocked_collection()
    rows = collection["rows"]
    if mutation == "duplicate":
        rows[-1] = copy.deepcopy(rows[0])
    elif mutation == "drop":
        rows.pop()
    elif mutation == "unknown":
        rows[0]["unit_id"] = "historical:pilot:row-1"
    elif mutation == "track":
        rows[0]["track"] = "development"
    else:
        rows[0]["successful"] = True
    with pytest.raises(ValueError):
        pilot.reconcile_results(protocol, rows)


@pytest.mark.parametrize(
    "field,value",
    [("success_rate", 0), ("observed_cost", 0), ("effect_estimate", 0), ("conclusion", "MET")],
)
def test_analysis_verifier_rejects_invented_measurements(field: str, value) -> None:
    protocol, collection = blocked_collection()
    summary = pilot.reconcile_results(protocol, collection["rows"])
    summary[field] = value
    with pytest.raises(ValueError):
        pilot.validate_analysis(protocol, collection["rows"], summary)


def test_generation_is_nested_text_only_bilingual_and_preserves_historical_matrices(
    tmp_path: Path,
) -> None:
    protocol, collection = blocked_collection()
    protected = [
        ROOT / "research/academic-pipeline/experiment-evidence-matrix.csv",
        ROOT / "research/academic-pipeline/contribution-evidence-matrix.csv",
        ROOT / "scripts/validate_contribution_crosswalk.py",
    ]
    before = {path: path.read_bytes() for path in protected}
    out = tmp_path / "results-v1"
    tex = tmp_path / "generated/prospective-pilot"
    summary = generator.generate_results(protocol, collection, out, tex)
    assert {path.name for path in tex.iterdir()} == {"status_en.tex", "status_ko.tex"}
    assert json.loads((out / "summary.json").read_text(encoding="utf-8")) == summary
    assert {path: path.read_bytes() for path in protected} == before
    for language in ("en", "ko"):
        fragment = (tex / f"status_{language}.tex").read_text(encoding="utf-8")
        assert summary["study_id"] in fragment
        assert "NOT_RUN/BLOCKED" in fragment and "NOT_MET" in fragment
        for count in ("180", "60", "120"):
            assert re.search(rf"(?<!\d){count}(?!\d)", fragment)
        assert not re.search(
            r"\\(?:begin\{(?:tabular\*?|equation\*?|figure\*?)\}|includegraphics)", fragment
        )
    assert not list(out.rglob("*.svg")) and not list(out.rglob("*.png"))


@pytest.mark.parametrize(
    "destination",
    [
        "summary-file",
        "en-file",
        "ko-file",
        "summary-parent",
        "tex-parent",
    ],
)
def test_generation_rejects_symlink_destinations_before_any_overwrite(
    tmp_path: Path,
    destination: str,
) -> None:
    protocol, collection = blocked_collection()
    # Use genuine output bytes so the existing different-content guard cannot
    # accidentally stand in for rejecting a summary symlink.
    generator.generate_results(protocol, collection, tmp_path / "fresh", tmp_path / "fresh-tex")
    summary_bytes = (tmp_path / "fresh/summary.json").read_bytes()
    protected = tmp_path / "protected-evidence"
    protected.mkdir()
    out, tex = tmp_path / "results-v1", tmp_path / "generated/prospective-pilot"
    if destination.endswith("parent"):
        link = tmp_path / "redirected-parent"
        link.symlink_to(protected, target_is_directory=True)
        if destination == "summary-parent":
            out = link / "nested/results-v1"
        else:
            tex = link / "nested/prospective-pilot"
    out.mkdir(parents=True, exist_ok=True)
    tex.mkdir(parents=True, exist_ok=True)
    sentinels = {
        out / "summary.json": summary_bytes,
        tex / "status_en.tex": b"protected English evidence must remain byte-identical\n",
        tex / "status_ko.tex": b"protected Korean evidence must remain byte-identical\n",
    }
    for path, data in sentinels.items():
        path.write_bytes(data)
    if destination.endswith("file"):
        target = {
            "summary-file": out / "summary.json",
            "en-file": tex / "status_en.tex",
            "ko-file": tex / "status_ko.tex",
        }[destination]
        evidence = protected / "retained-record"
        evidence.write_bytes(sentinels[target])
        target.unlink()
        target.symlink_to(evidence)
        sentinels[evidence] = sentinels[target]
    try:
        with pytest.raises(ValueError, match="symlink"):
            generator.generate_results(protocol, collection, out, tex)
    finally:
        # A later destination must not be rejected after earlier writes landed.
        assert {path: path.read_bytes() for path in sentinels} == sentinels


def test_bilingual_manuscripts_include_exactly_one_separate_prospective_fragment() -> None:
    # TeX is the publication artifact consumed by LaTeX, not Python source to grep.
    for language in ("en", "ko"):
        source = (ROOT / f"paper/latex/{language}/main.tex").read_text(encoding="utf-8")
        includes = re.findall(r"\\input\{([^}]+)\}", re.sub(r"(?m)(?<!\\)%.*$", "", source))
        assert includes.count(f"../generated/prospective-pilot/status_{language}.tex") == 1
        assert not any(
            "prospective" in item
            and item != f"../generated/prospective-pilot/status_{language}.tex"
            for item in includes
        )
        assert (ROOT / f"paper/latex/generated/prospective-pilot/status_{language}.tex").is_file()
    # Existing exact top-level inventory, legacy-input, identity-appendix and three-equation
    # assertions remain owned by their existing tests; this adds no replacement allowlist.
