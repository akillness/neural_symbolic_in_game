"""Preparation source binding without native commands, models, or private task oracles."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nesy_game import prospective_pilot as pilot

TARGET = "game-track/web/dashboard/ontology-map.json"
INTERFACE = "game-track/web/dashboard/public-types.json"
TREE_PREFIX = "public-project/"


def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture
def prepare_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[ModuleType, dict, dict]:
    module_spec = importlib.util.spec_from_file_location(
        "prospective_prepare_cli_under_test",
        ROOT / "scripts/run_prospective_pilot.py",
    )
    assert module_spec is not None and module_spec.loader is not None
    cli = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(cli)

    bundle, source = tmp_path / "bundle", tmp_path / "source"
    git_root = tmp_path / "git-metadata"
    git_root.mkdir()
    source_bytes, baselines, pinned_blobs, entries = {}, {}, {}, []
    for task_id in pilot.TASK_IDS:
        target = TARGET if task_id == "t1" else f"tasks/{task_id}/target.json"
        good = json.dumps({"task": task_id, "accept": "verified-source-only"}).encode()
        defective = json.dumps({"task": task_id, "accept": "injected-defect"}).encode()
        source_bytes[target], baselines[target] = good, defective
        _write(source / target, good)
        _write(bundle / task_id / "baseline" / target, defective)
        _write(bundle / task_id / "corpus-overlay" / target, defective)
        baseline_sha = hashlib.sha256(defective).hexdigest()
        interfaces = [TARGET, {"path": INTERFACE}] if task_id == "t1" else [INTERFACE]
        spec = {
            "task_id": task_id,
            "source_commit": pilot.SOURCE_COMMIT,
            "title": f"Repair {task_id}",
            "requirement": "Reject invalid records",
            "target_file": target,
            "interface_files": interfaces,
            "public_check": {"kind": "json-parse"},
            "max_changed_lines": 8,
            "endpoint": "aggregate pass/fail",
            "baseline_sha256": baseline_sha,
        }
        _write(bundle / task_id / "task-spec.json", json.dumps(spec).encode())
        _write(bundle / task_id / "interfaces" / INTERFACE, b'{"record_kind":"public"}\n')
        entries.append(
            {
                "task_id": task_id,
                "source_commit": pilot.SOURCE_COMMIT,
                "source_sha256": hashlib.sha256(good).hexdigest(),
                "baseline_sha256": baseline_sha,
            }
        )
    source_bytes[INTERFACE] = b'{"record_kind":"public"}\n'
    _write(bundle / "task-manifest.json", json.dumps({"tasks": entries}).encode())
    for relative, data in source_bytes.items():
        pinned_blobs[relative] = hashlib.sha1(
            f"blob {len(data)}\0".encode() + data,
        ).hexdigest()

    def git_metadata(root: Path, *argv: str) -> subprocess.CompletedProcess[bytes]:
        if root != git_root or argv[:2] != ("rev-parse", "--verify") or len(argv) != 3:
            raise AssertionError(f"unexpected git metadata request: {root}, {argv}")
        revision = argv[2]
        if revision == f"{pilot.SOURCE_COMMIT}^{{commit}}":
            result = pilot.SOURCE_COMMIT
        elif revision.startswith(f"{pilot.SOURCE_COMMIT}:{TREE_PREFIX}"):
            relative = revision.removeprefix(f"{pilot.SOURCE_COMMIT}:{TREE_PREFIX}")
            result = pinned_blobs.get(relative)
        else:
            raise AssertionError(f"unexpected pinned revision: {revision}")
        return subprocess.CompletedProcess(
            argv, 0 if result else 1, stdout=(result + "\n").encode() if result else b"", stderr=b""
        )

    monkeypatch.setattr(cli, "_git", git_metadata)
    return cli, source_bytes, baselines


def _prepare(
    cli: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, dict]:
    code = cli.main(
        [
            "prepare",
            "--task-root",
            str(tmp_path / "bundle"),
            "--source-root",
            str(tmp_path / "source"),
            "--git-root",
            str(tmp_path / "git-metadata"),
            "--study-root",
            str(tmp_path / "study"),
            "--tree-prefix",
            TREE_PREFIX,
        ]
    )
    return code, json.loads(capsys.readouterr().out)


def test_prepare_target_interface_overlap_preserves_defect_without_solution_copy(
    tmp_path: Path,
    prepare_bundle: tuple,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli, source_bytes, baselines = prepare_bundle
    code, receipt = _prepare(cli, tmp_path, capsys)
    assert code == 0, receipt
    assert receipt["status"] == "PASS"
    study = tmp_path / "study"
    protocol = json.loads((study / cli.PROTOCOL).read_text(encoding="utf-8"))
    assert pilot.validate_protocol(protocol)["status"] == "PASS"
    assert protocol["tasks"][0]["semantic"]["public_facts"]["interface_files"] == [
        TARGET,
        INTERFACE,
    ]
    sources = json.loads((study / cli.SOURCES).read_text(encoding="utf-8"))
    target_row = next(row for row in sources["tasks"] if row["task_id"] == "t1")
    assert target_row["source_sha256"] == hashlib.sha256(source_bytes[TARGET]).hexdigest()
    assert target_row["baseline_sha256"] == hashlib.sha256(baselines[TARGET]).hexdigest()
    interface_row = next(row for row in target_row["interfaces"] if row["path"] == INTERFACE)
    assert interface_row["sha256"] == hashlib.sha256(source_bytes[INTERFACE]).hexdigest()
    assert interface_row["matches_pinned_blob"] is True
    for directory in ("baseline", "corpus-overlay"):
        assert (study / "tasks" / "t1" / directory / TARGET).read_bytes() == baselines[TARGET]
    assert (study / "tasks" / "t1" / "interfaces" / INTERFACE).read_bytes() == source_bytes[
        INTERFACE
    ]
    assert not (study / "tasks" / "t1" / "interfaces" / TARGET).exists()
    for path in study.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            assert all(
                good not in data for relative, good in source_bytes.items() if relative != INTERFACE
            ), path


@pytest.mark.parametrize("damage", ["tampered", "missing"])
def test_prepare_rejects_unbound_true_interface_before_writing_study(
    tmp_path: Path,
    prepare_bundle: tuple,
    capsys: pytest.CaptureFixture[str],
    damage: str,
) -> None:
    cli, _, _ = prepare_bundle
    interface = tmp_path / "bundle" / "t1" / "interfaces" / INTERFACE
    if damage == "tampered":
        interface.write_bytes(b'{"record_kind":"unverified-change"}\n')
    else:
        interface.unlink()
    code, receipt = _prepare(cli, tmp_path, capsys)
    assert code != 0, receipt
    assert receipt["status"] in {"FAIL", "BLOCKED"}
    assert any(INTERFACE in error for error in receipt["errors"]), receipt
    assert receipt["outputs"] == {}
    study = tmp_path / "study"
    assert not study.exists() or not any(study.iterdir())


@pytest.mark.parametrize("link_kind", ["directory", "file"])
def test_prepare_rejects_symlinks_before_copying_evaluator_only_bytes(
    tmp_path: Path,
    prepare_bundle: tuple,
    capsys: pytest.CaptureFixture[str],
    link_kind: str,
) -> None:
    cli, _, _ = prepare_bundle
    private = tmp_path / "evaluator-only"
    private.mkdir(mode=0o700)
    hidden = b"synthetic-evaluator-only-sentinel-582: never publish these bytes\n"
    (private / "retained-case.txt").write_bytes(hidden)
    link = tmp_path / "bundle/t1/readable-notes"
    target = private if link_kind == "directory" else private / "retained-case.txt"
    link.symlink_to(target, target_is_directory=link_kind == "directory")

    code, receipt = _prepare(cli, tmp_path, capsys)

    study = tmp_path / "study"
    copied = [path for path in study.rglob("*") if path.is_file()]
    assert all(hidden not in path.read_bytes() for path in copied), copied
    assert (private / "retained-case.txt").read_bytes() == hidden
    assert code != 0, receipt
    assert receipt["status"] == "FAIL", receipt
    assert any("symlink" in error and "readable-notes" in error for error in receipt["errors"]), (
        receipt
    )
    assert receipt["outputs"] == {}
    assert not study.exists() or not any(study.iterdir())
