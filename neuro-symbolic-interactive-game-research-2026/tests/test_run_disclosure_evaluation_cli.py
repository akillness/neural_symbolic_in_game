from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

from nesy_game.disclosure import PUBLIC_MANIFEST, PUBLIC_REPORT

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/run_disclosure_evaluation.py"
PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"
HISTORICAL_RESULTS = ROOT / "research/npc-disclosure/results-current"
ACTIVE_RESULTS = ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r1"
EXPECTED_FILES = {
    "disclosure-trace.jsonl",
    "comparison-summary.json",
    "factual-summary.json",
    "metadata.json",
}


def _run(*arguments: str, project_root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(project_root / SCRIPT.relative_to(ROOT)), *arguments],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def _snapshot(*directories: Path) -> dict[Path, bytes]:
    snapshot: dict[Path, bytes] = {}
    for directory in directories:
        if directory.is_file():
            snapshot[directory] = directory.read_bytes()
            continue
        if not directory.exists():
            continue
        snapshot.update(
            {path: path.read_bytes() for path in directory.rglob("*") if path.is_file()}
        )
    return snapshot


@pytest.fixture
def public_checkout(tmp_path: Path) -> Path:
    """Copy runnable public inputs without workspace-owned private provenance."""
    project = tmp_path / "public-checkout"
    packet_data = json.loads(PACKET.read_text(encoding="utf-8"))
    binding = json.loads((ROOT / PUBLIC_MANIFEST).read_text(encoding="utf-8"))
    relatives = {
        str(PACKET.relative_to(ROOT)),
        str(PACKET.with_suffix(".sha256").relative_to(ROOT)),
        str(SCRIPT.relative_to(ROOT)),
        PUBLIC_MANIFEST,
        binding["public_source"],
        binding["seed_materialization"]["public_source"],
        *(
            relative
            for relative in packet_data["source_hashes"]
            if relative != PUBLIC_REPORT and not relative.startswith(".ouroboros/")
        ),
    }
    for relative in relatives:
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    shutil.copytree(
        ROOT / "src/nesy_game",
        project / "src/nesy_game",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    assert not (project / PUBLIC_REPORT).exists()
    assert not (project / ".ouroboros").exists()
    assert not (project.parent / "llm-wiki").exists()
    assert not (project.parent / ".ouroboros").exists()
    return project


def test_cli_requires_explicit_output_directory() -> None:
    result = _run("--public-sources")

    assert result.returncode == 2
    assert "--output-dir" in result.stderr
    assert "required" in result.stderr


@pytest.mark.parametrize("destination_kind", ["file", "nonempty-directory"])
def test_cli_refuses_existing_output_without_changing_bytes(
    tmp_path: Path, destination_kind: str
) -> None:
    destination = tmp_path / "recorded-evidence"
    if destination_kind == "file":
        destination.write_bytes(b"immutable recorded evidence")
    else:
        destination.mkdir()
        (destination / "sentinel.json").write_bytes(b"immutable directory evidence")
    before = _snapshot(destination)

    result = _run("--public-sources", "--packet", str(PACKET), "--output-dir", str(destination))

    assert result.returncode == 1
    assert "refusing to overwrite recorded evidence" in result.stderr
    assert _snapshot(destination) == before


def test_cli_fresh_destination_publishes_actual_180_row_evaluation_without_touching_originals(
    tmp_path: Path,
    public_checkout: Path,
) -> None:
    destination = tmp_path / "fresh-results"
    destination.mkdir()
    before = _snapshot(HISTORICAL_RESULTS, ACTIVE_RESULTS)
    selected_packet = public_checkout / PACKET.relative_to(ROOT)
    selected_sources = (
        selected_packet,
        selected_packet.with_suffix(".sha256"),
        public_checkout / Path(PUBLIC_MANIFEST).parent,
    )
    selected_before = _snapshot(*selected_sources)

    result = _run(
        "--public-sources",
        "--packet",
        str(public_checkout / PACKET.relative_to(ROOT)),
        "--project-root",
        str(public_checkout),
        "--output-dir",
        str(destination),
        "--json",
        project_root=public_checkout,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert {path.name for path in destination.iterdir()} == EXPECTED_FILES
    factual = json.loads(result.stdout)
    assert factual["status"] == "PASS"
    assert factual["case_counts"] == {
        "normal": 48,
        "boundary": 4,
        "malformed": 8,
        "total": 60,
    }
    assert factual["general_ontology_equal"] is True

    rows = [
        json.loads(line)
        for line in (destination / "disclosure-trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(rows) == 180
    assert Counter(row["arm"] for row in rows) == {
        "unchecked_isolated": 60,
        "general_rule": 60,
        "ontology_gate": 60,
    }
    comparison = json.loads((destination / "comparison-summary.json").read_text(encoding="utf-8"))
    assert comparison["case_counts"] == factual["case_counts"]
    assert comparison["general_vs_ontology"]["outcome_equal"] is True
    assert (destination / "comparison-summary.json").read_bytes() == (
        ACTIVE_RESULTS / "comparison-summary.json"
    ).read_bytes()
    assert _snapshot(HISTORICAL_RESULTS, ACTIVE_RESULTS) == before
    assert _snapshot(*selected_sources) == selected_before
    assert selected_packet.read_bytes() == PACKET.read_bytes()
    binding = json.loads((public_checkout / PUBLIC_MANIFEST).read_text(encoding="utf-8"))
    metadata = json.loads((destination / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["packet_sha256"] == binding["packet_sha256"]
    assert metadata["source_hashes"][PUBLIC_REPORT] == binding["public_source_sha256"]
    assert metadata["public_source_bindings"]["logical_source"] == PUBLIC_REPORT
    assert metadata["public_source_bindings"]["public_source"] == binding["public_source"]
    assert metadata["source_hashes"][PUBLIC_REPORT] != binding["historical_observed_source_sha256"]


@pytest.mark.parametrize("missing_source", ["hidden-seed", "private-report"])
def test_cli_private_mode_rejects_public_only_checkout_without_publishing(
    tmp_path: Path,
    public_checkout: Path,
    missing_source: str,
) -> None:
    destination = tmp_path / "private-results"
    binding = json.loads((public_checkout / PUBLIC_MANIFEST).read_text(encoding="utf-8"))
    seed = binding["seed_materialization"]
    expected_missing = seed["logical_source"]
    if missing_source == "private-report":
        seed_destination = public_checkout / seed["logical_source"]
        seed_destination.parent.mkdir(parents=True)
        shutil.copy2(public_checkout / seed["public_source"], seed_destination)
        expected_missing = PUBLIC_REPORT

    result = _run(
        "--packet",
        str(public_checkout / PACKET.relative_to(ROOT)),
        "--project-root",
        str(public_checkout),
        "--output-dir",
        str(destination),
        project_root=public_checkout,
    )

    assert result.returncode == 1
    assert f"source binding is missing: {expected_missing}" in result.stderr
    assert not destination.exists()


def test_cli_invalid_packet_publishes_no_partial_artifacts(tmp_path: Path) -> None:
    invalid_packet = tmp_path / "invalid-packet.json"
    invalid_packet.write_text("{}\n", encoding="utf-8")
    destination = tmp_path / "invalid-results"
    before = _snapshot(HISTORICAL_RESULTS, ACTIVE_RESULTS)

    result = _run(
        "--public-sources",
        "--packet",
        str(invalid_packet),
        "--output-dir",
        str(destination),
    )

    assert result.returncode == 1
    assert "FAIL disclosure evaluation:" in result.stderr
    assert not destination.exists() or not any(destination.rglob("*"))
    assert _snapshot(HISTORICAL_RESULTS, ACTIVE_RESULTS) == before
