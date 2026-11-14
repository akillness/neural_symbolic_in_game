"""Required-file admission after retiring paper-unused planning documents."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_project

RETAINED_REQUIREMENTS = (
    "configs/model-matrix.yaml",
    "configs/experiment-matrix.yaml",
    "configs/metric-catalog.yaml",
    "configs/scenario-catalog.yaml",
    "configs/experimental-game.yaml",
    "configs/kg-ontology-simulation.json",
    "knowledge/ontology/trace-rpg-ontology.json",
    "knowledge/ontology/curated-relations.json",
    "knowledge/ontology/knowledge-graph-schema.sql",
    "research/simulation/kg-ontology/latest/evaluation-matrix.json",
    "research/simulation/kg-ontology/latest/evaluation-matrix.md",
    "research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg",
    "paper/latex/generated/kg_ontology_simulation_en.tex",
    "paper/latex/generated/kg_ontology_simulation_ko.tex",
    "research/source-ledger.yaml",
    "research/claim-ledger.yaml",
    "research/original-link-audit.yaml",
    "game-track/schemas/game-bridge.schema.json",
    "game-track/schemas/experiment-record.schema.json",
    "game-track/schemas/recorded-proposals.schema.json",
    "game-track/recorded-experiment.en.md",
    "game-track/recorded-experiment.ko.md",
    "game-track/design/gdd.en.md",
    "game-track/design/gdd.ko.md",
    "game-track/design/paper-crosswalk.en.md",
    "game-track/design/paper-crosswalk.ko.md",
    "game-track/godot/project.godot",
    "game-track/assets/concepts/asset-manifest.json",
    "data/fixtures/game-bridge-event.json",
    "data/fixtures/recorded-proposals.json",
    "harness/ownership.yaml",
    "CLAUDE.md",
    "_workspace/current/production/task-manifest.md",
)


@pytest.fixture
def retained_tree(tmp_path, monkeypatch):
    # check_required validates presence only; content validity belongs to its other gates.
    for relative in RETAINED_REQUIREMENTS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"retained requirement fixture\n")
    monkeypatch.setattr(validate_project, "ROOT", tmp_path)
    return tmp_path


def test_check_required_admits_retained_tree_without_obsolete_planning_docs(retained_tree, capsys):
    """A complete active tree is admissible without the three retired planning docs."""
    validate_project.check_required()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("missing", RETAINED_REQUIREMENTS)
def test_check_required_still_rejects_each_retained_requirement(retained_tree, capsys, missing):
    """Retirement must not silently make any other required file optional."""
    (retained_tree / missing).unlink()
    with pytest.raises(SystemExit) as failure:
        validate_project.check_required()
    assert failure.value.code == 1
    assert capsys.readouterr().out == f"FAIL: missing required files: {[missing]}\n"
