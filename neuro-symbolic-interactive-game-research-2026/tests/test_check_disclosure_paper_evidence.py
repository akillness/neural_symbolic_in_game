from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

from nesy_game.disclosure import PUBLIC_MANIFEST, PUBLIC_REPORT, public_source_binding
from scripts import check_disclosure_paper_evidence as checker

ROOT = Path(__file__).parents[1]
EXPECTED_PACKET_SHA256 = "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028"
ARMS = ("unchecked_isolated", "general_rule", "ontology_gate")
LABELS = ("", "tab:disclosure-contract", "tab:disclosure-arms", "tab:disclosure-fixtures")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _tmp_results(tmp_path: Path) -> Path:
    return tmp_path / "research/npc-disclosure" / checker.RESULTS.name


def _receipt_metadata() -> dict:
    metadata = json.loads((checker.RESULTS / "metadata.json").read_text(encoding="utf-8"))
    metadata["source_hashes"] = {
        relative: checker._sha(ROOT / relative) for relative in checker.CHANGED_SCRIPTS
    }
    return metadata


def _minimal_manifest_repo(tmp_path: Path) -> tuple[Path, dict]:
    """Build the smallest complete checker input tree, excluding the Godot receipt."""
    packet = tmp_path / "research/npc-disclosure/reveal-hint-expectations-v1.json"
    sidecar = tmp_path / "research/npc-disclosure/reveal-hint-expectations-v1.sha256"
    packet.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checker.PACKET, packet)
    sidecar.write_text(f"{EXPECTED_PACKET_SHA256}  {packet.name}\n", encoding="utf-8")

    results = _tmp_results(tmp_path)
    result_payloads = {
        "disclosure-trace.jsonl": '{"case_id":"N-001"}\n',
        "comparison-summary.json": {
            "arms": list(ARMS),
            "case_counts": {"normal": 48, "boundary": 4, "malformed": 8, "total": 60},
        },
        "factual-summary.json": {"status": "PASS", "general_ontology_equal": True},
    }
    for name, payload in result_payloads.items():
        path = results / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            _write_json(path, payload)

    public_binding = public_source_binding(ROOT)
    seed = public_binding["seed_materialization"]
    for relative in (
        *checker.EXECUTION_SOURCES,
        PUBLIC_MANIFEST,
        public_binding["public_source"],
        seed["public_source"],
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    packet_data = json.loads(packet.read_text(encoding="utf-8"))
    source_hashes = {
        relative: (
            public_binding["public_source_sha256"]
            if relative == PUBLIC_REPORT
            else checker._sha(
                tmp_path
                / (seed["public_source"] if relative == seed["logical_source"] else relative)
            )
        )
        for relative in packet_data["source_hashes"]
    }
    metadata = {
        "packet_sha256": EXPECTED_PACKET_SHA256,
        "current_source_bindings_observed": True,
        "public_source_bindings": public_binding,
        "observation_scope": "new deterministic Python evaluation; no new Godot or model observation",
        "source_hashes": source_hashes,
    }
    metadata_path = results / "metadata.json"
    _write_json(metadata_path, metadata)

    outputs = {
        "results_en": "paper/latex/generated/disclosure_results_en.tex",
        "results_ko": "paper/latex/generated/disclosure_results_ko.tex",
        "tables_en": "paper/latex/generated/disclosure_tables_en.tex",
        "tables_ko": "paper/latex/generated/disclosure_tables_ko.tex",
        "figure_svg": "paper/latex/figures/fig_disclosure_signals.svg",
        "figure_png": "paper/latex/figures/fig_disclosure_signals.png",
        "figure_pdf": "paper/latex/figures/fig_disclosure_signals.pdf",
    }
    labels = "\n".join(LABELS[1:])
    for key in ("results_en", "results_ko", "tables_en", "tables_ko"):
        path = tmp_path / outputs[key]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{labels}\nnormal=48 boundary=4 malformed=8 total=60\n", encoding="utf-8")
    svg = tmp_path / outputs["figure_svg"]
    svg.parent.mkdir(parents=True, exist_ok=True)
    svg.write_text(
        'data-paper-label="fig:disclosure-signals" disclosure-trace.jsonl PASS FAIL NR unreported_cases not model latent state',
        encoding="utf-8",
    )
    for key in ("figure_png", "figure_pdf"):
        path = tmp_path / outputs[key]
        path.write_bytes(b"fixture")

    for language in ("en", "ko"):
        latex = tmp_path / f"paper/latex/{language}"
        latex.mkdir(parents=True, exist_ok=True)
        (latex / "main.pdf").write_bytes(b"fixture pdf")
        (latex / "main.log").write_text("Output written on main.pdf.\n", encoding="utf-8")

    manifest = {
        "public_source_substitution": public_binding,
        "observation_scope": "publication materialization from current r5 deterministic Python and Godot artifacts; no new model observation",
        "inputs": {
            "packet": str(packet.relative_to(tmp_path)),
            "packet_sidecar": str(sidecar.relative_to(tmp_path)),
            "trace": str((results / "disclosure-trace.jsonl").relative_to(tmp_path)),
            "comparison": str((results / "comparison-summary.json").relative_to(tmp_path)),
            "factual": str((results / "factual-summary.json").relative_to(tmp_path)),
            "metadata": str((results / "metadata.json").relative_to(tmp_path)),
        },
        "input_sha256": {
            "packet": hashlib.sha256(packet.read_bytes()).hexdigest(),
            "packet_sidecar": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
            "trace": hashlib.sha256((results / "disclosure-trace.jsonl").read_bytes()).hexdigest(),
            "comparison": hashlib.sha256(
                (results / "comparison-summary.json").read_bytes()
            ).hexdigest(),
            "factual": hashlib.sha256((results / "factual-summary.json").read_bytes()).hexdigest(),
            "metadata": hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
        },
        "six_deliverables": {
            key: {}
            for key in (
                "ontology_contract",
                "python_godot_boundary",
                "raw_backed_signals",
                "three_arm_comparison",
                "paired_manuscripts",
                "game_fixture_mapping",
            )
        },
        "outputs": outputs,
    }
    manifest_path = tmp_path / "paper/latex/generated/disclosure_producer_manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path, metadata


def _detailed_receipt(metadata: dict, *, root: Path = ROOT, case_id: str = "N-047") -> dict:
    """Build one receipt from the frozen packet and hashes of the current files."""
    packet = json.loads(checker.PACKET.read_text(encoding="utf-8"))
    frozen_cases = [*packet["normal_cases"], *packet["boundary_cases"], *packet["malformed_cases"]]
    frozen = next(case for case in frozen_cases if case["case_id"] == case_id)
    expected = frozen["expected"]
    allowed = bool(expected["allowed"])
    codes = sorted(set(expected.get("codes", [])))
    template_id = expected.get("template_id")
    state_effect = expected.get("state_effect", "denied_no_mutation")
    template = next(
        template
        for template in packet["approved_templates"]
        if template["template_id"] == template_id
    )
    prior_state_hash = "0" * 64
    next_state_hash = "1" * 64
    case = {
        "case_id": frozen["case_id"],
        "operation": packet["scope"]["operation"],
        "actor_id": frozen["actor_id"],
        "fact_id": frozen["fact_id"],
        "stage": frozen["stage"],
        "prior_disclosed": frozen["prior_disclosed"],
        "expected": expected,
        "observed": {
            "accepted": allowed,
            "codes": codes,
            "template_id": template_id,
            "state_effect": state_effect,
        },
        "accepted": allowed,
        "codes": codes,
        "template_id": template_id,
        "rule_ids": list(expected["rule_ids"]),
        "state_effect": state_effect,
        "prior_state_hash": prior_state_hash,
        "next_state_hash": next_state_hash,
        "display": {"template_id": template_id, "source": template["source"]},
        "disclosure_trace": {
            "contract_id": packet["packet_id"],
            "contract_version": packet["packet_version"],
            "check_ids": [],
            "error_ids": codes,
            "prior_state_hash": prior_state_hash,
            "next_state_hash": next_state_hash,
        },
    }
    case["disclosure_trace"]["check_ids"] = checker._expected_trace_check_ids(case)
    return {
        "marker": "NPC_DISCLOSURE_RESULT",
        "passed": True,
        "failures": [],
        "packet_sha256": EXPECTED_PACKET_SHA256,
        "scenario_source": "game-track/godot/data/sealed_lighthouse.json",
        "source_hashes": {
            relative: checker._sha(root / relative) for relative in checker.EXECUTION_SOURCES
        },
        "cases": [case],
    }


def test_main_rejects_missing_explicit_godot_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(checker, "ARMS", ARMS, raising=False)
    manifest_path, _metadata = _minimal_manifest_repo(tmp_path)
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(
        checker, "PACKET", tmp_path / "research/npc-disclosure/reveal-hint-expectations-v1.json"
    )
    monkeypatch.setattr(
        checker, "SIDECAR", tmp_path / "research/npc-disclosure/reveal-hint-expectations-v1.sha256"
    )
    monkeypatch.setattr(checker, "RESULTS", _tmp_results(tmp_path))
    monkeypatch.setattr(checker, "MANIFEST", manifest_path)
    monkeypatch.setattr(sys, "argv", ["check_disclosure_paper_evidence.py"])

    assert checker.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAIL"
    assert "explicit Godot receipt missing" in result["error"]


def test_rebinding_results_after_source_change_does_not_promote_old_godot_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path, metadata = _minimal_manifest_repo(tmp_path)
    receipt_path = _tmp_results(tmp_path) / "godot-receipt.json"
    receipt = _detailed_receipt(metadata, root=tmp_path)
    _write_json(receipt_path, receipt)
    receipt_before = receipt_path.read_bytes()
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(
        checker, "PACKET", tmp_path / "research/npc-disclosure/reveal-hint-expectations-v1.json"
    )
    monkeypatch.setattr(checker, "SIDECAR", checker.PACKET.with_suffix(".sha256"))
    monkeypatch.setattr(checker, "RESULTS", _tmp_results(tmp_path))
    monkeypatch.setattr(checker, "MANIFEST", manifest_path)
    monkeypatch.setattr(sys, "argv", ["check_disclosure_paper_evidence.py"])

    assert checker.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PASS"

    relative = checker.EXECUTION_SOURCES[0]
    (tmp_path / relative).write_text("changed execution source\n", encoding="utf-8")
    metadata["source_hashes"][relative] = hashlib.sha256(
        (tmp_path / relative).read_bytes()
    ).hexdigest()
    metadata_path = checker.RESULTS / "metadata.json"
    _write_json(metadata_path, metadata)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["input_sha256"]["metadata"] = hashlib.sha256(metadata_path.read_bytes()).hexdigest()
    _write_json(manifest_path, manifest)

    assert checker.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "FAIL"
    assert f"Godot receipt source hash mismatch: {relative}" in result["error"]
    assert receipt_path.read_bytes() == receipt_before


def test_manifest_selected_input_path_drift_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest_path, _metadata = _minimal_manifest_repo(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["inputs"]["trace"] = (
        "research/npc-disclosure/results-signal-explainer-20261023-r3/disclosure-trace.jsonl"
    )
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    monkeypatch.setattr(
        checker, "PACKET", tmp_path / "research/npc-disclosure/reveal-hint-expectations-v1.json"
    )
    monkeypatch.setattr(checker, "SIDECAR", checker.PACKET.with_suffix(".sha256"))
    monkeypatch.setattr(checker, "RESULTS", _tmp_results(tmp_path))

    with pytest.raises(ValueError, match="manifest selected input path drift"):
        checker._check_current_results(manifest)


def test_marker_only_receipt_is_rejected(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    path = tmp_path / "marker-only-test.json"
    _write_json(path, {"marker": "NPC_DISCLOSURE_RESULT", "passed": True, "failures": []})

    with pytest.raises(ValueError):
        checker._check_godot_receipt(path, metadata)


@pytest.mark.parametrize(
    ("field", "mutate", "expected_error"),
    [
        (
            "packet_sha256",
            lambda receipt: receipt.update(packet_sha256="wrong-packet"),
            "packet binding",
        ),
        (
            "source_hashes",
            lambda receipt: receipt["source_hashes"].update(
                {checker.EXECUTION_SOURCES[0]: "0" * 64}
            ),
            "source hash mismatch",
        ),
    ],
    ids=["wrong-packet-hash", "wrong-source-hash"],
)
def test_receipt_rejects_packet_or_execution_source_hash_drift(
    tmp_path: Path, field: str, mutate, expected_error: str
) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    mutate(receipt)
    path = tmp_path / f"{field}-test.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match=expected_error):
        checker._check_godot_receipt(path, metadata)


def test_receipt_rejects_missing_execution_source_hash(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    del receipt["source_hashes"][checker.EXECUTION_SOURCES[-1]]
    path = tmp_path / "missing-source-hash.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="source hash malformed"):
        checker._check_godot_receipt(path, metadata)


def test_receipt_rejects_expected_object_drift_from_frozen_packet(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    receipt["cases"][0]["expected"] = {**receipt["cases"][0]["expected"], "allowed": False}
    path = tmp_path / "expected-drift.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="expected value is not frozen-packet bound"):
        checker._check_godot_receipt(path, metadata)


def test_receipt_rejects_operation_drift(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    receipt["cases"][0]["operation"] = "other_operation"
    path = tmp_path / "operation-drift.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="operation drift"):
        checker._check_godot_receipt(path, metadata)


def test_receipt_rejects_rule_id_not_frozen_packet_bound(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    receipt["cases"][0]["rule_ids"] = ["DISC-FAKE"]
    path = tmp_path / "fake-rule-id.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="rule IDs are not frozen-packet bound"):
        checker._check_godot_receipt(path, metadata)


def test_receipt_rejects_fabricated_nonempty_disclosure_trace(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    receipt["cases"][0]["disclosure_trace"] = {"event": "fabricated-stale-trace"}
    path = tmp_path / "fabricated-trace.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="disclosure contract binding mismatch"):
        checker._check_godot_receipt(path, metadata)


@pytest.mark.parametrize("case_id", ["M-007", "M-008"])
def test_receipt_rejects_malformed_case_actor_drift(tmp_path: Path, case_id: str) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata, case_id=case_id)
    receipt["cases"][0]["actor_id"] = "captain_mira"
    path = tmp_path / f"{case_id}-actor-drift.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="actor_id drift"):
        checker._check_godot_receipt(path, metadata)


def test_receipt_rejects_observed_top_level_mismatch(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    receipt["cases"][0]["observed"]["accepted"] = False
    path = tmp_path / "observed-mismatch.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match="observed accepted mismatch"):
        checker._check_godot_receipt(path, metadata)


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        ("prior_state_hash", "not-a-hash", "state hashes malformed"),
        ("disclosure_trace", {}, "display/trace malformed"),
    ],
    ids=["malformed-state-hash", "empty-disclosure-trace"],
)
def test_receipt_rejects_malformed_state_hash_or_empty_trace(
    tmp_path: Path, field: str, value: object, expected_error: str
) -> None:
    metadata = _receipt_metadata()
    receipt = _detailed_receipt(metadata)
    receipt["cases"][0][field] = value
    path = tmp_path / f"{field}-invalid.json"
    _write_json(path, receipt)

    with pytest.raises(ValueError, match=expected_error):
        checker._check_godot_receipt(path, metadata)


def test_detailed_receipt_passes_godot_validation_path(tmp_path: Path) -> None:
    metadata = _receipt_metadata()
    path = tmp_path / "godot-receipt.json"
    _write_json(path, _detailed_receipt(metadata))

    checker._check_godot_receipt(path, metadata)


def test_outputs_require_bilingual_label_and_numeric_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checker, "LABELS", LABELS, raising=False)
    manifest_path, _metadata = _minimal_manifest_repo(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    receipt = _tmp_results(tmp_path) / "godot-receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("{}", encoding="utf-8")

    checker._check_outputs(manifest, receipt)

    ko_results = tmp_path / manifest["outputs"]["results_ko"]
    ko_results.write_text(
        ko_results.read_text(encoding="utf-8").replace("total=60", "total=61"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="numeric parity"):
        checker._check_outputs(manifest, receipt)

    ko_results.write_text(
        ko_results.read_text(encoding="utf-8").replace("total=61", "total=60"), encoding="utf-8"
    )
    ko_tables = tmp_path / manifest["outputs"]["tables_ko"]
    ko_results.write_text(
        ko_results.read_text(encoding="utf-8").replace("tab:disclosure-arms", "missing-label"),
        encoding="utf-8",
    )
    ko_tables.write_text(
        ko_tables.read_text(encoding="utf-8").replace("tab:disclosure-arms", "missing-label"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="bilingual label"):
        checker._check_outputs(manifest, receipt)


def test_outputs_reject_legacy_skipped_check_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checker, "LABELS", LABELS, raising=False)
    manifest_path, _metadata = _minimal_manifest_repo(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    receipt = _tmp_results(tmp_path) / "godot-receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("{}", encoding="utf-8")

    svg = tmp_path / manifest["outputs"]["figure_svg"]
    svg.write_text(
        svg.read_text(encoding="utf-8").replace("NR unreported_cases", "SKIPPED"), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="figure provenance/legend token missing"):
        checker._check_outputs(manifest, receipt)


@pytest.mark.parametrize(
    "mutation, message",
    [("missing_pdf", "paper PDF missing"), ("failed_log", "paper build receipt failed")],
)
def test_outputs_require_successful_en_ko_build_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str, message: str
) -> None:
    manifest_path, _metadata = _minimal_manifest_repo(tmp_path)
    monkeypatch.setattr(checker, "LABELS", LABELS, raising=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    receipt = _tmp_results(tmp_path) / "godot-receipt.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("{}", encoding="utf-8")

    if mutation == "missing_pdf":
        (tmp_path / "paper/latex/en/main.pdf").unlink()
    else:
        (tmp_path / "paper/latex/en/main.log").write_text("Fatal error\n", encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        checker._check_outputs(manifest, receipt)
