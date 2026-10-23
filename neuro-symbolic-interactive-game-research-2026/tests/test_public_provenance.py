from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from nesy_game.disclosure import (
    PUBLIC_MANIFEST,
    PUBLIC_REPORT,
    DisclosureContractError,
    load_frozen_contract,
    public_source_binding,
    verify_publication_sources,
)
from scripts import check_disclosure_paper_evidence as checker
from scripts import generate_disclosure_paper_results as paper_producer
from scripts import generate_signal_explainer as signal_generator

ROOT = Path(__file__).parents[1]
PACKET = ROOT / "research/npc-disclosure/reveal-hint-expectations-v1.json"
PUBLIC_MANIFEST_PATH = ROOT / PUBLIC_MANIFEST
PUBLIC_DERIVATIVE = ROOT / "research/npc-disclosure/public/ontology-signals-interview.public.txt"
RUNNER = ROOT / "scripts/run_disclosure_evaluation.py"
SIGNAL_GENERATOR = ROOT / "scripts/generate_signal_explainer.py"
CHECKER = ROOT / "scripts/check_disclosure_paper_evidence.py"
SOURCE_RELS = tuple(json.loads(PACKET.read_text(encoding="utf-8"))["source_hashes"])
EXPECTED_OUTPUTS = {
    "disclosure-trace.jsonl",
    "comparison-summary.json",
    "factual-summary.json",
    "metadata.json",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(*paths: Path) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for path in paths:
        if path.is_file():
            files[path] = path.read_bytes()
        elif path.is_dir():
            files.update(
                {child: child.read_bytes() for child in path.rglob("*") if child.is_file()}
            )
    return files


def _copy_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """Build a selected project tree with the private report intentionally absent."""
    project = tmp_path / "selected-project"
    packet = project / "research/npc-disclosure/reveal-hint-expectations-v1.json"
    packet.parent.mkdir(parents=True)
    shutil.copy2(PACKET, packet)
    shutil.copy2(PACKET.with_suffix(".sha256"), packet.with_suffix(".sha256"))

    for relative in SOURCE_RELS:
        if relative == PUBLIC_REPORT or relative.startswith(".ouroboros/"):
            continue
        source = ROOT / relative
        if not source.is_file() and relative.startswith((".ouroboros/", "llm-wiki/")):
            source = ROOT.parent / relative
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    for source in PUBLIC_MANIFEST_PATH.parent.iterdir():
        if source.is_file():
            destination = project / "research/npc-disclosure/public" / source.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return project, packet


def _copy_current_results_without_public_binding(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path]:
    project, packet = _copy_fixture(tmp_path)
    results_relative = Path("research/npc-disclosure/results-signal-explainer-20261023-r5")
    results = project / results_relative
    shutil.copytree(ROOT / results_relative, results)

    metadata_path = results / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.pop("public_source_bindings", None)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )

    manifest_path = project / "paper/latex/generated/disclosure_producer_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checker.MANIFEST, manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_sha256"]["metadata"] = _sha(metadata_path)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    return project, packet, results, manifest_path


@pytest.mark.parametrize(
    "consumer", ["signal", "paper", "checker"], ids=["signal", "paper", "checker"]
)
def test_current_consumers_reject_missing_explicit_public_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str
) -> None:
    project, packet, results, manifest_path = _copy_current_results_without_public_binding(tmp_path)
    packet_sidecar = packet.with_suffix(".sha256")

    if consumer == "signal":
        monkeypatch.setattr(signal_generator, "ROOT", project)
        monkeypatch.setattr(signal_generator, "PACKET", packet)
        monkeypatch.setattr(signal_generator, "PACKET_SIDECAR", packet_sidecar)
        monkeypatch.setattr(signal_generator, "RESULTS", results)
        monkeypatch.setattr(signal_generator, "TRACE", results / "disclosure-trace.jsonl")
        monkeypatch.setattr(signal_generator, "COMPARISON", results / "comparison-summary.json")
        monkeypatch.setattr(signal_generator, "FACTUAL", results / "factual-summary.json")
        monkeypatch.setattr(signal_generator, "METADATA", results / "metadata.json")
        operation = signal_generator.load_inputs
    elif consumer == "paper":
        monkeypatch.setattr(paper_producer, "ROOT", project)
        monkeypatch.setattr(paper_producer, "PACKET", packet)
        monkeypatch.setattr(paper_producer, "PACKET_SIDECAR", packet_sidecar)
        monkeypatch.setattr(paper_producer, "RESULTS", results)
        operation = paper_producer._load
    else:
        monkeypatch.setattr(checker, "ROOT", project)
        monkeypatch.setattr(checker, "PACKET", packet)
        monkeypatch.setattr(checker, "SIDECAR", packet_sidecar)
        monkeypatch.setattr(checker, "RESULTS", results)
        monkeypatch.setattr(checker, "MANIFEST", manifest_path)
        manifest = checker._read_json(manifest_path)
        operation = lambda: checker._check_current_results(manifest)

    with pytest.raises(ValueError, match="current public-source evaluation metadata missing"):
        operation()


def _run_runner(output_dir: Path, project_root: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--packet",
            str(project_root / "research/npc-disclosure/reveal-hint-expectations-v1.json"),
            "--project-root",
            str(project_root),
            "--public-sources",
            "--output-dir",
            str(output_dir),
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_public_contract_loads_without_private_report_and_emits_explicit_public_binding(
    tmp_path: Path,
) -> None:
    project, packet = _copy_fixture(tmp_path)
    assert not (project.parent / "llm-wiki").exists()
    assert not (project / PUBLIC_REPORT).exists()
    assert not (project / ".ouroboros").exists()
    assert not (project.parent / ".ouroboros").exists()

    contract = load_frozen_contract(packet, project, public_sources=True)

    binding = contract.public_source_bindings
    assert binding is not None
    assert binding["logical_source"] == PUBLIC_REPORT
    assert (
        binding["public_source"]
        == "research/npc-disclosure/public/ontology-signals-interview.public.txt"
    )
    assert binding["public_source_sha256"] == _sha(project / binding["public_source"])
    assert binding["manifest"] == PUBLIC_MANIFEST
    assert binding["manifest_sha256"] == _sha(project / PUBLIC_MANIFEST)
    assert contract.source_hashes_observed[PUBLIC_REPORT] == binding["public_source_sha256"]
    assert (
        contract.source_hashes_observed[PUBLIC_REPORT]
        != binding["historical_observed_source_sha256"]
    )


def test_explicit_public_binding_accepts_pinned_derivative(tmp_path: Path) -> None:
    project, packet = _copy_fixture(tmp_path)
    contract = load_frozen_contract(packet, project, public_sources=True)
    packet_data = json.loads(packet.read_text(encoding="utf-8"))
    binding = dict(contract.public_source_bindings or {})

    verified = verify_publication_sources(
        project,
        dict(contract.source_hashes_observed),
        packet_data,
        public_source_bindings=binding,
    )

    assert verified == binding
    assert verified["public_source_sha256"] == _sha(project / verified["public_source"])


def test_explicit_public_binding_rejects_wrong_observed_derivative_digest(tmp_path: Path) -> None:
    project, packet = _copy_fixture(tmp_path)
    contract = load_frozen_contract(packet, project, public_sources=True)
    packet_data = json.loads(packet.read_text(encoding="utf-8"))
    binding = dict(contract.public_source_bindings or {})
    observed = dict(contract.source_hashes_observed)
    observed[PUBLIC_REPORT] = "0" * 64

    with pytest.raises(
        DisclosureContractError,
        match="public substitution current source binding mismatch",
    ):
        verify_publication_sources(
            project,
            observed,
            packet_data,
            public_source_bindings=binding,
        )


def test_explicit_public_binding_rejects_forged_binding_metadata(tmp_path: Path) -> None:
    project, packet = _copy_fixture(tmp_path)
    contract = load_frozen_contract(packet, project, public_sources=True)
    packet_data = json.loads(packet.read_text(encoding="utf-8"))
    observed = dict(contract.source_hashes_observed)
    forged = dict(contract.public_source_bindings or {})
    forged["public_source_sha256"] = "f" * 64

    with pytest.raises(
        DisclosureContractError,
        match="public substitution current binding metadata mismatch",
    ):
        verify_publication_sources(
            project,
            observed,
            packet_data,
            public_source_bindings=forged,
        )


def test_pinned_manifest_and_derivative_tampering_are_rejected(tmp_path: Path) -> None:
    project, _ = _copy_fixture(tmp_path)
    manifest = project / PUBLIC_MANIFEST
    derivative = project / "research/npc-disclosure/public/ontology-signals-interview.public.txt"

    manifest.write_bytes(manifest.read_bytes() + b"\n")
    with pytest.raises(DisclosureContractError, match="manifest hash mismatch"):
        public_source_binding(project)

    shutil.copy2(PUBLIC_MANIFEST_PATH, manifest)
    derivative.write_bytes(derivative.read_bytes() + b"tampered")
    with pytest.raises(DisclosureContractError, match="public source derivative hash mismatch"):
        public_source_binding(project)
    shutil.copy2(PUBLIC_DERIVATIVE, derivative)
    seed = project / "research/npc-disclosure/public/disclosure-seed.yaml"
    seed.write_bytes(seed.read_bytes() + b"tampered")
    with pytest.raises(DisclosureContractError, match="public seed materialization hash mismatch"):
        public_source_binding(project)


def test_public_source_set_and_historical_digest_drift_are_rejected(tmp_path: Path) -> None:
    project, packet = _copy_fixture(tmp_path)
    contract = load_frozen_contract(packet, project, public_sources=True)
    observed = dict(contract.source_hashes_observed)
    packet_data = json.loads(packet.read_text(encoding="utf-8"))

    with pytest.raises(
        DisclosureContractError,
        match="public substitution historical source binding mismatch",
    ):
        verify_publication_sources(project, observed, packet_data)

    with pytest.raises(DisclosureContractError, match="binding set drift"):
        verify_publication_sources(project, {**observed, "unexpected.txt": "0" * 64}, packet_data)

    historical_drift = dict(observed)
    historical_drift[PUBLIC_REPORT] = "f" * 64
    with pytest.raises(
        DisclosureContractError,
        match="public substitution historical source binding mismatch",
    ):
        verify_publication_sources(project, historical_drift, packet_data)

    historical_observed = dict(observed)
    public_manifest = json.loads((project / PUBLIC_MANIFEST).read_text(encoding="utf-8"))
    historical_observed[PUBLIC_REPORT] = public_manifest["historical_observed_source_sha256"]
    changed_source = project / "game-track/godot/data/sealed_lighthouse.json"
    changed_source.write_bytes(changed_source.read_bytes() + b"\n")
    with pytest.raises(DisclosureContractError, match="publication source hash drift"):
        verify_publication_sources(project, historical_observed, packet_data)


def test_public_runner_preserves_historical_inputs_and_baseline_denominators(
    tmp_path: Path,
) -> None:
    historical_report = (
        ROOT.parent / "llm-wiki/wiki/reports/2026-10-22-ontology-signals-interview.md"
    )
    old_results = tuple(sorted((ROOT / "research/npc-disclosure").glob("results-*")))
    before = _snapshot(
        PACKET,
        PACKET.with_suffix(".sha256"),
        PUBLIC_MANIFEST_PATH,
        PUBLIC_DERIVATIVE,
        historical_report,
        *old_results,
    )
    output = tmp_path / "public-results"

    result = _run_runner(output)

    assert result.returncode == 0, result.stdout + result.stderr
    assert {path.name for path in output.iterdir()} == EXPECTED_OUTPUTS
    factual = json.loads(result.stdout)
    assert factual["status"] == "PASS"
    assert factual["case_counts"] == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60}
    assert factual["general_ontology_equal"] is True

    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    binding = metadata["public_source_bindings"]
    assert binding["logical_source"] == PUBLIC_REPORT
    assert (
        metadata["observation_scope"]
        == "new deterministic Python evaluation; no new Godot or model observation"
    )
    assert metadata["source_hashes"][PUBLIC_REPORT] == binding["public_source_sha256"]
    assert (
        metadata["source_hashes"][PUBLIC_REPORT]
        != json.loads(PACKET.read_text(encoding="utf-8"))["source_hashes"][PUBLIC_REPORT]
    )
    assert (
        _snapshot(
            PACKET,
            PACKET.with_suffix(".sha256"),
            PUBLIC_MANIFEST_PATH,
            PUBLIC_DERIVATIVE,
            historical_report,
            *old_results,
        )
        == before
    )


def test_signal_generator_check_accepts_pinned_public_derivative_without_rewriting_outputs() -> (
    None
):
    generated = (
        ROOT / "game-track/web/dashboard/disclosure-reference.json",
        *tuple(sorted((ROOT / "paper/latex/figures").glob("fig_signal_*.svg"))),
    )
    before = _snapshot(PACKET, PUBLIC_MANIFEST_PATH, PUBLIC_DERIVATIVE, *generated)

    result = subprocess.run(
        [sys.executable, str(SIGNAL_GENERATOR), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["mode"] == "check"
    assert payload["normal_boundary_malformed_per_arm"] == [48, 4, 8]
    assert _snapshot(PACKET, PUBLIC_MANIFEST_PATH, PUBLIC_DERIVATIVE, *generated) == before


def test_checker_writes_new_public_receipt_with_current_r5_boundary(tmp_path: Path) -> None:
    receipt = tmp_path / "publication-only-receipt.json"
    historical = tuple(
        sorted((ROOT / "research/npc-disclosure").glob("results-*/godot-receipt.json"))
    )
    before = _snapshot(PACKET, PUBLIC_MANIFEST_PATH, PUBLIC_DERIVATIVE, *historical)

    result = subprocess.run(
        [sys.executable, str(CHECKER), "--public-receipt", str(receipt)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "disclosure-public-materialization/v1"
    assert payload["status"] == "PASS"
    assert (
        payload["observation_scope"]
        == "publication materialization from current r5 deterministic Python and Godot artifacts; no new model observation"
    )
    assert payload["case_counts"] == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60}
    assert payload["public_source_substitution"]["logical_source"] == PUBLIC_REPORT
    current_receipt = payload["current_godot_receipt"]
    assert current_receipt.endswith("results-signal-explainer-20261023-r5/godot-receipt.json")
    assert payload["current_godot_receipt_sha256"] == _sha(ROOT / current_receipt)
    expected_inputs = {
        "comparison": _sha(
            ROOT
            / "research/npc-disclosure/results-signal-explainer-20261023-r5/comparison-summary.json"
        ),
        "factual": _sha(
            ROOT
            / "research/npc-disclosure/results-signal-explainer-20261023-r5/factual-summary.json"
        ),
        "metadata": _sha(
            ROOT / "research/npc-disclosure/results-signal-explainer-20261023-r5/metadata.json"
        ),
        "packet": _sha(PACKET),
        "packet_sidecar": _sha(PACKET.with_suffix(".sha256")),
        "trace": _sha(
            ROOT
            / "research/npc-disclosure/results-signal-explainer-20261023-r5/disclosure-trace.jsonl"
        ),
    }
    assert payload["current_inputs_sha256"] == expected_inputs
    assert "historical_godot_receipt" not in payload
    assert "historical_godot_receipt_sha256" not in payload
    assert "historical_inputs_sha256" not in payload
    assert _snapshot(PACKET, PUBLIC_MANIFEST_PATH, PUBLIC_DERIVATIVE, *historical) == before
