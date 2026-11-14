"""Reviewer verification contracts over genuine, isolated publication inputs.

The copied observations are never represented as a new scientific run. Mutations
exist only in pytest's temporary tree; every victim is restored before reuse.
"""

from __future__ import annotations

import builtins
import hashlib
import importlib.util
import io
import json
import re
import shutil
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest
from npc_historical_fixture import archive_historical_npc_sources

ROOT = Path(__file__).resolve().parents[1]
SURFACES = {
    "paper-en": "paper/latex/en/main.tex",
    "paper-ko": "paper/latex/ko/main.tex",
    "paper-en-traceability-supplement": "paper/latex/en/traceability-supplement.tex",
    "paper-ko-traceability-supplement": "paper/latex/ko/traceability-supplement.tex",
}
REVIEW = "research/academic-pipeline/gemini-review-20261113/results-v2"
REVIEW_ROOT = "research/academic-pipeline/gemini-review-20261113"
PRIVATE_REVIEW_IDENTITIES = (
    f"{REVIEW_ROOT}/reviewer-source.json",
    f"{REVIEW_ROOT}/results-v2/reviewer-source.json",
)
PUBLIC_REVIEW_SOURCE = f"{REVIEW_ROOT}/reviewer-source.public.json"
PUBLIC_REVIEW_RECEIPT = f"{REVIEW_ROOT}/public-source-projection-v1.json"
PUBLIC_REVIEW_RECEIPT_SHA256 = "7c2c4acd22bd811729fcd2645039bae5ebf99313a74ff2de28338a7458475232"
PUBLIC_REVIEW_SOURCE_SHA256 = "278182062607a58b6d55e6d4c062f9651469d14001345710335fc2bc25a3079e"
ORIGINAL_REVIEW_SHA256 = "09e18301e2fc537af0666b444ac3aadee6a0c6f3dc8e2e0f1c5b3bd8b3ac4ea6"
TABLE = r"""
\begin{table*}
\caption{Unregistered fixture, not a scientific observation}
\label{tab:reviewer-unbound}
\begin{tabular}{lr}Fixture & 1/2 \\
\end{tabular}
\end{table*}
"""


@pytest.fixture(scope="module")
def verifier():
    # Delay loading until test execution: absent implementation is a real RED,
    # not an import-time skip or a fabricated successful checker.
    path = ROOT / "scripts/verify_paper_claims.py"
    assert path.is_file(), "reviewer entrypoint scripts/verify_paper_claims.py is unimplemented"
    spec = importlib.util.spec_from_file_location("paper_claims_contract_subject", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def publication(verifier, tmp_path_factory):
    """Copy genuine PUBLIC inputs once; never reconstruct withheld original bytes."""
    parent = tmp_path_factory.mktemp("paper-claims")
    project = parent / ROOT.name
    shutil.copytree(
        ROOT,
        project,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "node_modules",
            ".godot",
        ),
    )
    for relative in PRIVATE_REVIEW_IDENTITIES:
        (project / relative).unlink(missing_ok=True)
    historical = parent / "historical-npc-fa9"
    historical.mkdir()
    archive_historical_npc_sources(ROOT, historical)
    return project, historical


@pytest.fixture
def change(publication):
    project, _ = publication
    originals = {}

    def replace(relative, transform):
        path = project / relative
        if path not in originals:
            originals[path] = path.read_bytes() if path.exists() else None
        old = path.read_text(encoding="utf-8") if path.exists() else ""
        new = transform(old)
        assert new != old, f"mutation did not change {relative}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new, encoding="utf-8")
        return path

    yield replace
    for path, payload in originals.items():
        if payload is None:
            path.unlink(missing_ok=True)
        else:
            path.write_bytes(payload)


def _replace_once(text, old, new):
    assert text.count(old) == 1, f"expected one mutation anchor: {old!r}"
    return text.replace(old, new, 1)


def _refresh_manifest(project, change, monkeypatch):
    """A mutable receipt refresh must not authorize altered scientific claims."""
    import update_visual_source_manifest as manifest

    with monkeypatch.context() as context:
        context.setattr(manifest, "ROOT", project)
        payload = manifest.build_manifest()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    # Some protected inputs (including claim-ledger status) are intentionally
    # outside this visual receipt. An idempotent refresh is not a failed attack;
    # change() still requires the actual source mutation to alter its bytes.
    if (project / "visuals/source-manifest.json").read_text(encoding="utf-8") != serialized:
        change("visuals/source-manifest.json", lambda _: serialized)


def _verify(verifier, publication):
    project, historical = publication
    return verifier.verify(project, npc_evidence_root=historical, public_source_projection=True)


def _assert_fail(report, anchor=None):
    assert report["status"] == "FAIL", report
    failures = [check for check in report["checks"] if check["status"] == "FAIL"]
    assert failures and all(check["detail"] for check in failures), report
    if anchor is not None:
        assert any(
            table["anchor"] == anchor and table["status"] == "FAIL" for table in report["tables"]
        ), report


def _snapshot(root):
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in root.rglob("*")
        if path.is_file()
    }


def _inventory(project, monkeypatch):
    """Resolve the existing TeX grammar, independently enumerate effective blocks."""
    import validate_visual_assets as visual

    inventory = {}
    with monkeypatch.context() as context:
        context.setattr(visual, "ROOT", project)
        for surface, relative in SURFACES.items():
            validator = visual.Validator(require_pdf_tools=False, check_regeneration=False)
            sources = validator._publication_sources(project / relative)
            assert validator.errors == []
            anchors = []
            for text in sources.values():
                for block in re.findall(
                    r"\\begin\{table\*?\}(.*?)\\end\{table\*?\}", text, re.DOTALL
                ):
                    labels = re.findall(r"\\label\{(tab:[^}]+)\}", block)
                    assert len(labels) == 1
                    anchors.extend(labels)
            inventory[surface] = anchors
    return inventory


def test_every_reached_table_has_an_individual_source_binding(verifier, publication, monkeypatch):
    project, _ = publication
    expected = _inventory(project, monkeypatch)
    report = _verify(verifier, publication)
    assert report["status"] == "PASS", report
    assert report["schema_version"] == "paper-claims-verification/v1"
    actual_surfaces = {surface["id"]: surface for surface in report["surfaces"]}
    assert set(actual_surfaces) == set(SURFACES)
    expected_pairs = set()
    for surface, anchors in expected.items():
        entry = actual_surfaces[surface]
        assert entry["source"] == SURFACES[surface]
        assert entry["anchors"] == anchors
        assert entry["table_count"] == entry["binding_count"] == len(anchors)
        assert entry["errors"] == []
        expected_pairs.update((surface, anchor) for anchor in anchors)
    actual_pairs = [(table["surface_id"], table["anchor"]) for table in report["tables"]]
    assert len(actual_pairs) == len(set(actual_pairs))
    assert set(actual_pairs) == expected_pairs
    for table in report["tables"]:
        assert table["status"] == "PASS", table
        assert table["table_source_id"] and table["adapter_id"] and table["source_receipts"]
    for surface in SURFACES:
        if "supplement" in surface:
            assert (surface, "tab:traceability-rubric") in expected_pairs
    assert all(anchor != "alg:commit" for _, anchor in actual_pairs)
    assert report["registered_unreachable"] == []
    assert report["external_layers"]
    assert all(
        layer["status"] == "NOT_EXECUTED_BY_THIS_COMMAND" for layer in report["external_layers"]
    )


@pytest.mark.parametrize("surface", SURFACES)
def test_new_table_star_cannot_disappear_from_any_root(
    verifier, publication, change, monkeypatch, surface
):
    project, _ = publication
    change(
        SURFACES[surface], lambda text: text.replace(r"\end{document}", TABLE + r"\end{document}")
    )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), "tab:reviewer-unbound")


@pytest.mark.parametrize(
    "invocation",
    [
        r"\input{reviewer-nested}",
        r"\newcommand{\reviewerinput}{\input{reviewer-nested}}\reviewerinput",
    ],
)
def test_nested_input_and_zero_argument_macro_cannot_hide_unbound_tables(
    verifier, publication, change, monkeypatch, invocation
):
    project, _ = publication
    change("paper/latex/en/reviewer-nested.tex", lambda _: TABLE)
    change(
        SURFACES["paper-en"],
        lambda text: text.replace(r"\end{document}", invocation + "\n" + r"\end{document}"),
    )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), "tab:reviewer-unbound")


@pytest.mark.parametrize("language,signal", [("en", "Detailed"), ("ko", "상세")])
@pytest.mark.parametrize(
    "replacement",
    ["5/5 & 5/5 & 3/5 & 1/5", "5/5 & 3/5 & 4/5 & 1/5", "5/5 & 4/4 & 3/4 & 1/4"],
    ids=["gate-numerator-drift", "same-digits-wrong-columns", "schema-failures-excluded"],
)
def test_manual_v5_cells_are_bound_to_source_keys_and_assigned_denominators(
    verifier, publication, change, monkeypatch, language, signal, replacement
):
    project, _ = publication
    old = rf"\texttt{{gpt-5.6-luna}} & {signal} & 5/5 & 4/5 & 3/5 & 1/5"
    new = rf"\texttt{{gpt-5.6-luna}} & {signal} & {replacement}"
    change(f"paper/latex/{language}/main.tex", lambda text: _replace_once(text, old, new))
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), "tab:paired-feedback-v5")


@pytest.mark.parametrize("language", ["en", "ko"])
def test_generated_table_cannot_be_reauthorized_by_refreshing_editable_manifest(
    verifier, publication, change, monkeypatch, language
):
    project, _ = publication
    change(
        f"paper/latex/generated/pilot_tables_{language}.tex",
        lambda text: _replace_once(text, "5/5 & 0/1 & 0/6", "4/5 & 0/1 & 0/6"),
    )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), "tab:pilot-repair")


def test_guided_repair_narrative_cannot_replace_assigned_denominator_with_successes(
    verifier, publication, change, monkeypatch
):
    project, _ = publication
    change(
        "paper/latex/generated/pilot_tables_en.tex",
        lambda text: _replace_once(text, r"$\rho$ 5/12", r"$\rho$ 5/5"),
    )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), "tab:pilot-repair")


@pytest.mark.parametrize("mutation", ["remove-input", "orphan-label", "duplicate-input"])
def test_reachable_registration_cannot_pass_after_its_binding_is_broken(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication
    target = "paper/latex/en/main.tex"
    include = r"\input{../generated/pilot_tables_en.tex}"
    if mutation == "remove-input":
        change(target, lambda text: _replace_once(text, include, "% removed registered input"))
    elif mutation == "duplicate-input":
        change(target, lambda text: _replace_once(text, include, include + "\n" + include))
    else:
        change(
            "paper/latex/generated/pilot_tables_en.tex",
            lambda text: (
                _replace_once(text, r"\label{tab:pilot-repair}", "")
                + "\n"
                + r"\label{tab:pilot-repair}"
                + "\n"
            ),
        )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication))


@pytest.mark.parametrize(
    "mutation", ["wrong-reference-result", "missing-assignment", "wrong-source-sha"]
)
def test_frozen_raw_receipts_and_source_hashes_are_not_replaced_by_derived_tables(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication
    if mutation == "wrong-source-sha":

        def alter_hash(text):
            payload = json.loads(text)
            payload["scripts/review_reference.py"] = "0" * 64
            return json.dumps(payload, indent=2) + "\n"

        change(f"{REVIEW}/source_hashes.json", alter_hash)
    else:

        def alter_row(text):
            rows = text.splitlines()
            if mutation == "missing-assignment":
                return "\n".join(rows[1:]) + "\n"
            first = json.loads(rows[0])
            assert first["reference_final_valid"] is True
            first["reference_final_valid"] = False
            rows[0] = json.dumps(first)
            return "\n".join(rows) + "\n"

        change(f"{REVIEW}/rows.jsonl", alter_row)
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication))


def test_wrong_historical_source_bytes_fail_without_rehash_or_current_source_fallback(
    verifier, publication, tmp_path
):
    project, historical = publication
    wrong = tmp_path / "wrong-fa9"
    shutil.copytree(historical, wrong)
    source = wrong / "src/nesy_game/npc_goal.py"
    source.write_bytes(source.read_bytes() + b"\n# tampered isolated fixture\n")
    before = _snapshot(wrong)
    report = verifier.verify(project, npc_evidence_root=wrong, public_source_projection=True)
    _assert_fail(report)
    assert _snapshot(wrong) == before


def test_missing_explicit_historical_dependency_is_blocked_not_skipped(
    verifier, publication, tmp_path
):
    project, _ = publication
    missing = tmp_path / "missing-genuine-fa9"
    report = verifier.verify(project, npc_evidence_root=missing, public_source_projection=True)
    assert report["status"] == "BLOCKED", report
    assert any(check["status"] == "BLOCKED" and check["detail"] for check in report["checks"])
    assert not missing.exists()


def test_unmeasured_claims_and_prospective_denominators_are_preserved(verifier, publication):
    report = _verify(verifier, publication)
    assert report["status"] == "PASS", report
    preserved = report["preserved_statuses"]
    for number in range(1, 6):
        assert preserved[f"C-RESULT-{number:03}"] == "TODO-RESULT"
    assert preserved["prospective_completed"] == 0
    assert preserved["prospective_assigned"] == 180
    assert preserved["prospective_status"] == "BLOCKED"
    assert preserved["traceability_rubric"] == "PROPOSED_UNMEASURED"


@pytest.mark.parametrize("corrupt", [False, True], ids=["valid", "numeric-drift"])
def test_pure_verification_needs_no_writes_processes_sockets_or_provider_calls(
    verifier, publication, change, monkeypatch, corrupt
):
    project, historical = publication
    if corrupt:
        change(
            "paper/latex/generated/pilot_tables_en.tex",
            lambda text: _replace_once(text, "5/5 & 0/1 & 0/6", "4/5 & 0/1 & 0/6"),
        )
        _refresh_manifest(project, change, monkeypatch)
    before = _snapshot(project), _snapshot(historical)

    def forbidden(*args, **kwargs):
        pytest.fail("pure verification attempted a write, process, socket, or provider request")

    def guard_open(original):
        def read_only(file, mode="r", *args, **kwargs):
            if any(flag in mode for flag in "wax+"):
                forbidden(file, mode)
            return original(file, mode, *args, **kwargs)

        return read_only

    with monkeypatch.context() as context:
        context.setattr(sys, "dont_write_bytecode", True)
        context.setattr(socket, "socket", forbidden)
        context.setattr(socket, "create_connection", forbidden)
        context.setattr(subprocess, "Popen", forbidden)
        context.setattr(urllib.request, "urlopen", forbidden)
        context.setattr(Path, "write_bytes", forbidden)
        context.setattr(Path, "write_text", forbidden)
        context.setattr(builtins, "open", guard_open(builtins.open))
        context.setattr(io, "open", guard_open(io.open))
        report = verifier.verify(
            project, npc_evidence_root=historical, public_source_projection=True
        )
    assert report["status"] == ("FAIL" if corrupt else "PASS"), report
    assert (_snapshot(project), _snapshot(historical)) == before


def _cli(project, *args, cwd, public_source_projection):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(project / "scripts/verify_paper_claims.py"),
            *args,
            *(["--public-source-projection"] if public_source_projection else []),
            "--json",
        ],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def test_json_cli_is_deterministic_relocated_and_independent_of_cwd(publication, tmp_path):
    project, historical = publication
    args = ("--root", str(project), "--npc-evidence-root", str(historical))
    first = _cli(project, *args, cwd=tmp_path, public_source_projection=True)
    second = _cli(project, *args, cwd=project / "paper", public_source_projection=True)
    assert first.returncode == second.returncode == 0, (first.stderr, second.stderr)
    assert first.stdout == second.stdout
    assert json.loads(first.stdout)["status"] == "PASS"


@pytest.mark.parametrize("dependency", ["root", "historical-source"])
def test_json_cli_maps_missing_prerequisites_to_blocked_exit_two(publication, tmp_path, dependency):
    project, historical = publication
    root = project if dependency != "root" else tmp_path / "missing-project"
    npc = historical if dependency != "historical-source" else tmp_path / "missing-fa9"
    result = _cli(
        project,
        "--root",
        str(root),
        "--npc-evidence-root",
        str(npc),
        cwd=tmp_path,
        public_source_projection=True,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["status"] == "BLOCKED"


def test_json_cli_numeric_failure_is_nonzero_not_a_successful_inventory(
    publication, change, monkeypatch, tmp_path
):
    project, historical = publication
    change(
        "paper/latex/generated/pilot_tables_en.tex",
        lambda text: _replace_once(text, "5/5 & 0/1 & 0/6", "4/5 & 0/1 & 0/6"),
    )
    _refresh_manifest(project, change, monkeypatch)
    result = _cli(
        project,
        "--root",
        str(project),
        "--npc-evidence-root",
        str(historical),
        cwd=tmp_path,
        public_source_projection=True,
    )
    assert result.returncode == 1, (result.stdout, result.stderr)
    _assert_fail(json.loads(result.stdout), "tab:pilot-repair")


def test_cli_materializes_local_pinned_source_without_manual_dependency_path(verifier, tmp_path):
    # Genuine local Git objects, not a fabricated packet, make the advertised
    # one-command reviewer path executable. No engine/provider reproduction.
    before = {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in ROOT.rglob("*.tex")
    }
    result = _cli(ROOT, cwd=tmp_path, public_source_projection=True)
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["status"] == "PASS"
    assert {
        str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in ROOT.rglob("*.tex")
    } == before


def test_cli_missing_local_git_object_fails_closed_without_fallback(publication, tmp_path):
    project, _ = publication
    # Relocation deliberately leaves .git behind. It must not borrow the live
    # checkout's current sources or turn unavailable historical evidence into SKIP.
    result = _cli(project, cwd=tmp_path, public_source_projection=True)
    assert result.returncode == 2, (result.stdout, result.stderr)
    assert json.loads(result.stdout)["status"] == "BLOCKED"


@pytest.mark.parametrize("number", range(1, 6))
def test_unmeasured_result_claim_cannot_be_promoted_by_editing_its_ledger(
    verifier, publication, change, monkeypatch, number
):
    import yaml

    project, _ = publication
    claim_id = f"C-RESULT-{number:03}"

    def promote(text):
        payload = yaml.safe_load(text)
        claim = next(row for row in payload["claims"] if row["id"] == claim_id)
        assert claim["status"] == "TODO-RESULT"
        claim["status"] = "verified"
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    change("research/claim-ledger.yaml", promote)
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication))


def test_missing_selected_root_helper_cannot_borrow_cached_checkout_module(verifier, publication):
    import importlib

    project, _ = publication
    importlib.import_module("validate_npc_goal_evidence")
    helper = project / "scripts/validate_npc_goal_evidence.py"
    original = helper.read_bytes()
    helper.unlink()
    try:
        report = _verify(verifier, publication)
    finally:
        helper.write_bytes(original)
    assert report["status"] in {"FAIL", "BLOCKED"}, report
    npc = next(check for check in report["checks"] if check["id"] == "npc")
    assert npc["status"] == "BLOCKED", npc
    assert "validate_npc_goal_evidence" in npc["detail"]
    assert all(
        table["status"] != "PASS"
        for table in report["tables"]
        if table["anchor"] == "tab:npc-screening"
    )


def test_historical_directory_symlink_is_rejected_even_with_correct_target_bytes(
    verifier, publication, tmp_path
):
    project, historical = publication
    escaped = tmp_path / "outside-historical-root"
    shutil.copytree(historical / "configs", escaped)
    wrong = tmp_path / "historical-with-symlink"
    shutil.copytree(historical, wrong)
    shutil.rmtree(wrong / "configs")
    (wrong / "configs").symlink_to(escaped, target_is_directory=True)
    before = _snapshot(escaped)
    report = verifier.verify(project, npc_evidence_root=wrong, public_source_projection=True)
    _assert_fail(report)
    assert any(
        check["status"] == "FAIL" and "symlink" in check["detail"] for check in report["checks"]
    ), report
    assert _snapshot(escaped) == before


def test_verifier_restores_callers_bytecode_policy_without_writing_pycache(
    verifier, publication, monkeypatch
):
    project, historical = publication
    before = _snapshot(project), _snapshot(historical)
    with monkeypatch.context() as context:
        context.setattr(sys, "dont_write_bytecode", False)
        report = verifier.verify(
            project, npc_evidence_root=historical, public_source_projection=True
        )
        assert sys.dont_write_bytecode is False
    assert report["status"] == "PASS", report
    assert (_snapshot(project), _snapshot(historical)) == before


def test_known_anchor_cannot_borrow_materialization_from_an_unreached_source(
    verifier, publication, change
):
    project, _ = publication
    relative = "paper/latex/en/main.tex"
    fragment = (project / "paper/latex/generated/pilot_tables_en.tex").read_text(encoding="utf-8")
    change(
        relative,
        lambda text: _replace_once(text, r"\input{../generated/pilot_tables_en.tex}", fragment),
    )

    def relocate_registration(text):
        payload = json.loads(text)
        owner = next(
            row for row in payload["table_sources"] if row["id"] == "offline-pilot-paper-tables"
        )
        receipt = next(
            row
            for row in owner["layout_sources"]
            if row["path"] == "paper/latex/generated/pilot_tables_en.tex"
        )
        content = (project / relative).read_bytes()
        receipt.update(
            path=relative, bytes=len(content), sha256=hashlib.sha256(content).hexdigest()
        )
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    change("visuals/source-manifest.json", relocate_registration)
    report = _verify(verifier, publication)
    # An independent manifest-freshness failure is not enough: the pilot family
    # itself still reproduces, yet its source binding must reject the relocated
    # reached table rather than borrowing validation of an unused generated file.
    pilot = next(check for check in report["checks"] if check["id"] == "pilot")
    assert pilot["status"] == "PASS", pilot
    table = next(
        row
        for row in report["tables"]
        if row["surface_id"] == "paper-en" and row["anchor"] == "tab:pilot-repair"
    )
    assert table["source"] == relative
    assert table["table_source_id"] == "offline-pilot-paper-tables"
    assert table["status"] == "FAIL", table
    _assert_fail(report)


WITHDRAWN_OLLAMA = "research/maintenance/ollama-unverified-history-20261113.json"


def test_unverified_ollama_archive_is_not_current_quantitative_evidence(verifier, publication):
    project, _ = publication
    payload = (project / WITHDRAWN_OLLAMA).read_bytes()
    archive = json.loads(payload)
    report = _verify(verifier, publication)
    records = report["withdrawn_evidence"]
    record = next(row for row in records if row["id"] == "ollama-feasibility")
    assert record["path"] == WITHDRAWN_OLLAMA
    assert record["sha256"] == hashlib.sha256(payload).hexdigest()
    assert record["status"] == archive["status"] == "UNVERIFIED_HISTORICAL_ATTRIBUTION"
    assert (
        record["disposition"]
        == archive["disposition"]
        == ("WITHDRAWN_FROM_CURRENT_QUANTITATIVE_EVIDENCE")
    )
    assert record["binding_kind"] == "historical_attribution_only"
    assert record["quantitative_evidence"] is False
    assert all(
        table["anchor"] != archive["historical_table_label"] for table in report["tables"]
    ), report
    check = next(row for row in report["checks"] if row["id"] == "withdrawn-ollama-attribution")
    assert check["status"] == "PASS", check
    assert report["status"] == "PASS", report


@pytest.mark.parametrize("language", ["en", "ko"])
def test_archived_unverified_table_cannot_be_reinserted_as_current_numeric_evidence(
    verifier, publication, change, monkeypatch, language
):
    project, _ = publication
    archive = json.loads((project / WITHDRAWN_OLLAMA).read_text(encoding="utf-8"))
    fragment = next(
        row["text"] for row in archive["source_fragments"] if row["language"] == language
    )
    blocks = [
        match.group(0)
        for match in re.finditer(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", fragment, re.DOTALL)
        if rf"\label{{{archive['historical_table_label']}}}" in match.group(0)
    ]
    assert len(blocks) == 1, "archival fixture must contain its verbatim historical table"
    change(
        f"paper/latex/{language}/main.tex",
        lambda text: _replace_once(text, r"\end{document}", blocks[0] + "\n" + r"\end{document}"),
    )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), archive["historical_table_label"])


@pytest.mark.parametrize(
    "mutation", ["promote-status", "promote-disposition", "fragment-bytes", "fragment-sha"]
)
def test_archived_attribution_cannot_be_promoted_or_rewritten_as_verified_evidence(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication

    def alter_archive(text):
        payload = json.loads(text)
        if mutation == "promote-status":
            payload["status"] = "VERIFIED_EXPERIMENT"
        elif mutation == "promote-disposition":
            payload["disposition"] = "CURRENT_QUANTITATIVE_EVIDENCE"
        elif mutation == "fragment-bytes":
            payload["source_fragments"][0]["text"] += "\nAltered historical attribution.\n"
        else:
            payload["source_fragments"][0]["sha256"] = "0" * 64
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    change(WITHDRAWN_OLLAMA, alter_archive)
    _refresh_manifest(project, change, monkeypatch)
    report = _verify(verifier, publication)
    _assert_fail(report)
    check = next(row for row in report["checks"] if row["id"] == "withdrawn-ollama-attribution")
    assert check["status"] == "FAIL", check


@pytest.mark.parametrize(
    "mutation",
    [
        "fixture-leaf-failed",
        "fixture-pass-flag",
        "presentation-leaf-failed",
        "negative-count",
        "boolean-count",
        "fractional-count",
        "extension-overflow",
    ],
)
def test_engine_leaf_outcomes_cannot_borrow_unchanged_passing_aggregate(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication

    def alter_leaf(text):
        payload = json.loads(text)
        fixture = payload["authored_fixtures"][0]
        if mutation == "fixture-leaf-failed":
            fixture["counts"]["checks_passed"] = 0
            fixture["passed"] = False
        elif mutation == "fixture-pass-flag":
            fixture["passed"] = False
        elif mutation == "presentation-leaf-failed":
            payload["presentation"]["counts"]["checks_passed"] -= 1
            payload["presentation"]["passed"] = False
        elif mutation == "negative-count":
            fixture["counts"]["checks_passed"] = -1
        elif mutation == "boolean-count":
            fixture["counts"]["checks_passed"] = True
        elif mutation == "fractional-count":
            fixture["counts"]["checks_passed"] = 0.5
        else:
            extension = payload["presentation"]["extension_counts"]
            extension["checks_passed"] = extension["checks_total"] + 1
            payload["totals"]["extension_checks_passed"] = extension["checks_passed"]
            payload["totals"]["all_checks_passed"] = (
                payload["totals"]["combined_checks_passed"] + extension["checks_passed"]
            )
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    change("game-track/godot/docs/latest/evaluation-matrix.json", alter_leaf)
    _refresh_manifest(project, change, monkeypatch)
    report = _verify(verifier, publication)
    _assert_fail(report)
    check = next(row for row in report["checks"] if row["id"] == "artifact-map-sources")
    assert check["status"] == "FAIL", check


def test_in_flight_change_to_linked_test_source_fails_protected_snapshot(
    verifier, publication, change, monkeypatch
):
    project, _ = publication
    relative = "tests/test_gemini_review_publication.py"
    victim = project / relative
    original = victim.read_bytes()
    trigger = project / "paper/latex/en/main.tex"
    read_text = Path.read_text
    injected = False

    def read_with_external_mutation(path, *args, **kwargs):
        nonlocal injected
        result = read_text(path, *args, **kwargs)
        if path == trigger and not injected:
            injected = True
            change(relative, lambda text: text + "\n# isolated in-flight source change\n")
        return result

    # The filesystem boundary simulates a concurrent external editor. No checker
    # result or adapter is mocked; final verification must notice changed bytes
    # even if a later table binding hashes the newly modified source normally.
    with monkeypatch.context() as context:
        context.setattr(Path, "read_text", read_with_external_mutation)
        report = _verify(verifier, publication)
    assert injected, "the actual publication source read must trigger the concurrent mutation"
    _assert_fail(report)
    assert report["protected_snapshot"]["status"] == "FAIL", report
    assert any(relative in path for path in report["protected_snapshot"]["changed"])
    assert victim.read_bytes() == original + b"\n# isolated in-flight source change\n"


@pytest.mark.parametrize(
    "relative",
    [
        "research/codex_feedback_pilot/paired-model-comparison-20261110-v5-source.zip",
        "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
    ],
    ids=["frozen-source-archive", "runtime-direct-receipt"],
)
def test_direct_snapshot_dependency_symlink_is_rejected_with_identical_bytes(
    verifier, publication, tmp_path, relative
):
    project, _ = publication
    path = project / relative
    original = path.read_bytes()
    outside = tmp_path / "identical-external-input"
    outside.write_bytes(original)
    path.unlink()
    path.symlink_to(outside)
    try:
        report = _verify(verifier, publication)
    finally:
        path.unlink()
        path.write_bytes(original)
    _assert_fail(report)
    assert any(
        row["status"] == "FAIL" and "symlink" in row["detail"] for row in report["checks"]
    ), report
    assert outside.read_bytes() == original


def test_valid_tex_command_whitespace_cannot_hide_an_unbound_table(
    verifier, publication, change, monkeypatch
):
    project, _ = publication
    table = r"""
\begin {table}
\caption{Whitespace-spelled unregistered fixture, not scientific evidence}
\label {tab:reviewer-whitespace-unbound}
\begin{tabular}{lr}Fixture & 1/2 \\
\end{tabular}
\end {table}
"""
    change(
        "paper/latex/en/main.tex",
        lambda text: _replace_once(text, r"\end{document}", table + r"\end{document}"),
    )
    _refresh_manifest(project, change, monkeypatch)
    _assert_fail(_verify(verifier, publication), "tab:reviewer-whitespace-unbound")


@pytest.mark.parametrize("mutation", ["original-provenance-sha", "duplicate-projection-record"])
def test_public_capture_projection_cannot_rebind_original_provenance_or_duplicate_records(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication
    relative = (
        "_workspace/current/engineering/tech-verification/evidence/"
        "godot-4.7.1-20261113t151426z-paper-native3d-v1/"
        "public-path-projection-v1.json"
    )

    def alter_projection(text):
        payload = json.loads(text)
        provenance = next(row for row in payload["files"] if row["file"] == "provenance.json")
        if mutation == "original-provenance-sha":
            assert provenance["original"]["sha256"] != "0" * 64
            provenance["original"]["sha256"] = "0" * 64
        else:
            payload["files"].append(provenance.copy())
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    change(relative, alter_projection)
    _refresh_manifest(project, change, monkeypatch)
    report = _verify(verifier, publication)
    _assert_fail(report)
    check = next(row for row in report["checks"] if row["id"] == "stored-engine-captures")
    assert check["status"] == "FAIL", check


def test_explicit_public_review_mode_qualifies_provenance_and_all_audit_bindings(
    verifier, publication
):
    project, _ = publication
    assert all(not (project / relative).exists() for relative in PRIVATE_REVIEW_IDENTITIES)
    report = _verify(verifier, publication)
    assert report["status"] == "PASS", report
    assert report["source_verification_mode"] == "EXPLICIT_PUBLIC_SOURCE_PROJECTION"
    projection = report["public_source_projection"]
    assert projection["status"] == "PUBLIC_DERIVATIVE_VERIFIED_ORIGINAL_COMMITMENTS_ONLY"
    assert projection["receipt"] == {
        "path": PUBLIC_REVIEW_RECEIPT,
        "sha256": PUBLIC_REVIEW_RECEIPT_SHA256,
        "bytes": 2618,
    }
    assert projection["public_source"] == {
        "path": PUBLIC_REVIEW_SOURCE,
        "sha256": PUBLIC_REVIEW_SOURCE_SHA256,
        "bytes": 20262,
    }
    assert projection["withheld_originals"] == [
        {"path": relative, "sha256": ORIGINAL_REVIEW_SHA256, "bytes": 20336}
        for relative in PRIVATE_REVIEW_IDENTITIES
    ]
    assert projection["private_original_reverification"] == "NOT_PERFORMED_BY_THIS_COMMAND"
    check = next(row for row in report["checks"] if row["id"] == "public-source-projection")
    assert check["status"] == "PASS", check
    anchors = {
        "tab:review-boundary-funnel",
        "tab:review-structural-retention",
        "tab:review-surface-sentinels",
    }
    tables = [row for row in report["tables"] if row["anchor"] in anchors]
    assert {(row["surface_id"], row["anchor"]) for row in tables} == {
        (surface, anchor) for surface in ("paper-en", "paper-ko") for anchor in anchors
    }
    for table in tables:
        assert table["status"] == "PASS", table
        assert table["binding_kind"] == "source_materialization_public_source_projection"
        assert table["source_verification_mode"] == "EXPLICIT_PUBLIC_SOURCE_PROJECTION"
        assert table["private_original_reverification"] == "NOT_PERFORMED_BY_THIS_COMMAND"
    for table in report["tables"]:
        if table["anchor"] == "tab:artifact-directory-map":
            assert table["source_verification_mode"] == "EXPLICIT_PUBLIC_SOURCE_PROJECTION"
            assert table["private_original_reverification"] == "NOT_PERFORMED_BY_THIS_COMMAND"


def test_strict_review_api_blocks_withheld_originals_instead_of_using_public_projection(
    verifier, publication
):
    project, historical = publication
    report = verifier.verify(project, npc_evidence_root=historical)
    assert report["status"] == "BLOCKED", report
    assert report["source_verification_mode"] == "STRICT_ORIGINAL_SOURCE"
    assert "public_source_projection" not in report
    blocked = [row for row in report["checks"] if row["status"] == "BLOCKED"]
    assert blocked, report
    assert all(
        any(relative in row["detail"] for row in blocked) for relative in PRIVATE_REVIEW_IDENTITIES
    )
    assert not any(table["status"] == "PASS" for table in report["tables"])


def test_strict_review_cli_requires_explicit_public_opt_in(publication, tmp_path):
    project, historical = publication
    result = _cli(
        project,
        "--root",
        str(project),
        "--npc-evidence-root",
        str(historical),
        cwd=tmp_path,
        public_source_projection=False,
    )
    assert result.returncode == 2, (result.stdout, result.stderr)
    report = json.loads(result.stdout)
    assert report["status"] == "BLOCKED", report
    assert report["source_verification_mode"] == "STRICT_ORIGINAL_SOURCE"
    assert "public_source_projection" not in report


@pytest.mark.parametrize(
    "mutation",
    [
        "original-commitment",
        "input-manifest-commitment",
        "source-manifest-commitment",
        "duplicate-mapping",
        "extra-mapping",
        "escaped-original-path",
        "extra-operation",
    ],
)
def test_public_review_projection_cannot_reauthorize_wrong_or_expanded_commitments(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication

    def alter_receipt(text):
        payload = json.loads(text)
        if mutation == "original-commitment":
            payload["mappings"][0]["original"]["sha256"] = "0" * 64
        elif mutation == "input-manifest-commitment":
            payload["original_commitments"]["input_manifest"]["sha256"] = "0" * 64
        elif mutation == "source-manifest-commitment":
            payload["original_commitments"]["source_manifest"]["sha256"] = "0" * 64
        elif mutation == "duplicate-mapping":
            payload["mappings"][1] = json.loads(json.dumps(payload["mappings"][0]))
        elif mutation == "extra-mapping":
            extra = json.loads(json.dumps(payload["mappings"][0]))
            extra["original"]["path"] = "review-response.json"
            payload["mappings"].append(extra)
        elif mutation == "escaped-original-path":
            payload["mappings"][0]["original"]["path"] = "../../outside-reviewer-source.json"
        else:
            payload["projection"]["allowed_semantic_operations"].append(
                {"op": "remove", "path": "/name"}
            )
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    change(PUBLIC_REVIEW_RECEIPT, alter_receipt)
    _refresh_manifest(project, change, monkeypatch)
    report = _verify(verifier, publication)
    _assert_fail(report)
    check = next(row for row in report["checks"] if row["id"] == "public-source-projection")
    assert check["status"] == "FAIL", check


@pytest.mark.parametrize(
    "mutation", ["restore-private-field", "alter-other-field", "duplicate-json-member"]
)
def test_public_review_derivative_tampering_is_rejected_after_manifest_refresh(
    verifier, publication, change, monkeypatch, mutation
):
    project, _ = publication

    def alter_source(text):
        payload = json.loads(text)
        assert "url" not in payload
        if mutation == "duplicate-json-member":
            key = next(iter(payload))
            # The repeated member preserves the parsed object while changing the
            # public byte identity; semantic equality must not bypass the pin.
            return (
                "{"
                + json.dumps(key)
                + ":"
                + json.dumps(payload[key], ensure_ascii=False)
                + ","
                + text.lstrip()[1:]
            )
        if mutation == "restore-private-field":
            payload["url"] = "https://example.invalid/synthetic-forbidden-private-field"
        else:
            payload["synthetic_unapproved_field"] = "not part of the approved projection"
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    change(PUBLIC_REVIEW_SOURCE, alter_source)
    _refresh_manifest(project, change, monkeypatch)
    report = _verify(verifier, publication)
    _assert_fail(report)
    check = next(row for row in report["checks"] if row["id"] == "public-source-projection")
    assert check["status"] == "FAIL", check
