"""Behavioral tests for the public-safe TRACE-RPG signal projection."""

from __future__ import annotations

import copy
import functools
import hashlib
import http.server
import importlib.util
import json
import os
import shutil
import socketserver
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_signal_explainer.py"
REFERENCE = ROOT / "game-track/web/dashboard/disclosure-reference.json"
FIGURES = ROOT / "paper/latex/figures"


def _producer():
    spec = importlib.util.spec_from_file_location("generate_signal_explainer", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _walk_strings(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)
    elif isinstance(value, str):
        yield value


def _walk_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _walk_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_keys(item)


def _isolated_inputs(tmp_path, producer):
    names = ("PACKET", "PACKET_SIDECAR", "TRACE", "COMPARISON", "FACTUAL", "METADATA", "SCENARIO")
    if hasattr(producer, "RECEIPT"):
        names = (*names, "RECEIPT")
    paths = {name: tmp_path / Path(getattr(producer, name)).name for name in names}
    for name, path in paths.items():
        shutil.copyfile(getattr(producer, name), path)
        setattr(producer, name, path)
    packet_sha = hashlib.sha256(paths["PACKET"].read_bytes()).hexdigest()
    producer.EXPECTED_PACKET_SHA = packet_sha
    paths["PACKET_SIDECAR"].write_text(f"{packet_sha}  packet.json\n", encoding="utf-8")
    return paths


def _sync_packet_binding(paths, producer):
    packet_sha = hashlib.sha256(paths["PACKET"].read_bytes()).hexdigest()
    producer.EXPECTED_PACKET_SHA = packet_sha
    paths["PACKET_SIDECAR"].write_text(f"{packet_sha}  packet.json\n", encoding="utf-8")
    metadata = json.loads(paths["METADATA"].read_text(encoding="utf-8"))
    metadata["packet_sha256"] = packet_sha
    paths["METADATA"].write_text(json.dumps(metadata), encoding="utf-8")


def _rewrite_json(path: Path, mutate) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    mutate(payload)
    path.write_text(json.dumps(payload, allow_nan=True), encoding="utf-8")


def _rewrite_jsonl(path: Path, mutate) -> None:
    rows = [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    mutate(rows)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_reference_is_public_safe_and_preserves_the_input_projection():
    producer = _producer()
    data = producer.load_inputs()
    before = copy.deepcopy(data)
    reference = producer.build_reference(data)

    assert data == before
    assert reference["schema_version"] == "trace-rpg-signal-explainer/v1"
    assert reference["live"]["status"] == "awaiting_runtime"
    assert reference["live"]["events"] == []
    assert reference["live"]["counts"]["runtime_events"] == 0
    assert "fixture_examples" not in reference["live"]
    hidden_values = {
        str(case.get(key))
        for case in [
            *data["packet"]["normal_cases"],
            *data["packet"]["boundary_cases"],
            *data["packet"]["malformed_cases"],
        ]
        for key in ("actor_id", "fact_id")
        if case.get(key)
    }
    public_strings = set(_walk_strings(reference))
    assert hidden_values.isdisjoint(public_strings)
    assert {
        "actor_id",
        "fact_id",
        "raw_state",
        "raw_actor_id",
        "raw_fact_id",
        "hidden_fact",
    }.isdisjoint(set(_walk_keys(reference)))


def test_frozen_counts_keep_denominators_and_unsafe_mismatch_distinct():
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    comparison = reference["frozen_comparison"]
    assert comparison["independent_inputs"] == 60
    assert comparison["case_counts"] == {"normal": 48, "boundary": 4, "malformed": 8, "total": 60}
    assert comparison["counts"]["general_ontology_equal"] == 60
    assert comparison["counts"]["unsafe_by_arm"] == {
        "unchecked_isolated": 51,
        "general_rule": 0,
        "ontology_gate": 0,
    }
    assert comparison["counts"]["mismatch_by_arm"] == {
        "unchecked_isolated": 60,
        "general_rule": 0,
        "ontology_gate": 0,
    }
    assert comparison["counts"]["unsafe_by_arm"] != comparison["counts"]["mismatch_by_arm"]

    for arm in comparison["arms"]:
        for stratum in ("normal", "boundary", "malformed"):
            cell = comparison["cells"][arm][stratum]
            assert cell["n"] == comparison["case_counts"][stratum]
            assert cell["report_status"] == "reported"
            assert cell["checks"]["report_status"] in {"reported", "unreported"}
    sparse = comparison["cells"]["unchecked_isolated"]
    for stratum in sparse:
        assert sparse[stratum]["checks"] == {"pass": 0, "fail": 0, "report_status": "unreported"}


def test_generated_figures_are_parseable_and_nonempty():
    for stem in ("fig_signal_mechanism", "fig_signal_comparison"):
        svg = FIGURES / f"{stem}.svg"
        ET.parse(svg)
        assert svg.stat().st_size > 0
        assert (FIGURES / f"{stem}.png").stat().st_size > 0
        assert (FIGURES / f"{stem}.pdf").stat().st_size > 0


def test_check_mode_is_deterministic_and_read_only():
    before = {path: path.read_bytes() for path in [REFERENCE, *FIGURES.glob("fig_signal_*.svg")]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary == {
        "general_ontology_equal": 60,
        "mismatch": [0, 0, 60],
        "mode": "check",
        "normal_boundary_malformed_per_arm": [48, 4, 8],
        "status": "PASS",
        "unsafe": [0, 0, 51],
    }
    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize(
    ("name", "mutate", "error_pattern"),
    [
        (
            "duplicate-case-id",
            lambda packet: packet["normal_cases"][1].__setitem__(
                "case_id", packet["normal_cases"][0]["case_id"]
            ),
            "frozen case ids duplicate or missing",
        ),
        (
            "missing-required-field",
            lambda packet: packet["normal_cases"][0].pop("fact_id"),
            "fact_id",
        ),
    ],
)
def test_load_inputs_rejects_invalid_case_contract(tmp_path, name, mutate, error_pattern):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)
    _rewrite_json(paths["PACKET"], mutate)
    _sync_packet_binding(paths, producer)
    with pytest.raises(ValueError, match=error_pattern):
        producer.load_inputs()


def test_load_inputs_rejects_nonfinite_numeric_data(tmp_path):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)
    _rewrite_json(
        paths["COMPARISON"],
        lambda comparison: comparison.__setitem__(
            "case_counts", {"normal": float("nan"), "boundary": 4, "malformed": 8, "total": 60}
        ),
    )
    with pytest.raises(ValueError):
        producer.load_inputs()


@pytest.mark.parametrize(
    "mutation", ["duplicate", "missing"], ids=["duplicate-trace-pair", "missing-trace-pair"]
)
def test_load_inputs_rejects_duplicate_or_missing_trace_case_arm_pair(tmp_path, mutation):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)
    rows = [
        json.loads(line)
        for line in paths["TRACE"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if mutation == "duplicate":
        rows[1] = copy.deepcopy(rows[0])
    else:
        rows[0]["case_id"] = rows[3]["case_id"]
    paths["TRACE"].write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    with pytest.raises(ValueError):
        producer.load_inputs()


def test_load_inputs_rejects_packet_stratum_swap_preserving_denominators(tmp_path):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)

    def swap_strata(packet):
        normal = packet["normal_cases"].pop()
        boundary = packet["boundary_cases"].pop()
        packet["normal_cases"].append(boundary)
        packet["boundary_cases"].append(normal)

    _rewrite_json(paths["PACKET"], swap_strata)
    _sync_packet_binding(paths, producer)
    with pytest.raises(ValueError, match="stratum"):
        producer.load_inputs()


def test_load_inputs_rejects_trace_expected_drift(tmp_path):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)
    _rewrite_jsonl(
        paths["TRACE"],
        lambda rows: rows[0]["expected"].__setitem__("allowed", not rows[0]["expected"]["allowed"]),
    )
    with pytest.raises(ValueError, match="trace expected"):
        producer.load_inputs()


def test_load_inputs_rejects_source_digest_mismatch(tmp_path):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)
    _rewrite_json(
        paths["METADATA"], lambda metadata: metadata.__setitem__("packet_sha256", "0" * 64)
    )
    with pytest.raises(ValueError, match="metadata packet binding drift"):
        producer.load_inputs()


def test_load_inputs_rejects_current_source_hash_mutation(tmp_path):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)
    relative = next(
        iter(json.loads(paths["METADATA"].read_text(encoding="utf-8"))["source_hashes"])
    )

    def mutate(metadata):
        metadata["source_hashes"][relative] = "0" * 64

    _rewrite_json(paths["METADATA"], mutate)
    with pytest.raises(ValueError) as exc_info:
        producer.load_inputs()
    assert str(exc_info.value) == f"publication source hash drift: {relative}"


@pytest.mark.parametrize(
    "field_value", ["DISC-999", "maybe"], ids=["invalid-check-id", "invalid-check-outcome"]
)
def test_load_inputs_rejects_invalid_check_identifier_or_outcome(tmp_path, field_value):
    producer = _producer()
    paths = _isolated_inputs(tmp_path, producer)

    def mutate(rows):
        row = next(row for row in rows if row["checks"])
        row["checks"][0]["rule_id" if field_value == "DISC-999" else "outcome"] = field_value

    _rewrite_jsonl(paths["TRACE"], mutate)
    with pytest.raises(ValueError, match="trace check identifier or outcome is invalid"):
        producer.load_inputs()


def test_readers_fail_on_malformed_json_and_non_object_jsonl(tmp_path):
    producer = _producer()
    malformed = tmp_path / "bad.json"
    malformed.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON input"):
        producer.read_json(malformed)
    rows = tmp_path / "bad.jsonl"
    rows.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="JSONL row is not an object"):
        producer.read_jsonl(rows)


def test_dashboard_consumes_real_iframe_events_and_resets_live_clock():
    """Exercise the served DOM, iframe postMessage boundary, chronology, and reset."""
    web_root = ROOT / "game-track/web"
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(web_root))
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        playwright_path = os.environ.get("PLAYWRIGHT_BIN") or shutil.which("playwright")
        if not playwright_path:
            pytest.skip("Playwright CLI is not installed")
        node_root = Path(playwright_path).parent.parent
        env = os.environ.copy()
        env["SIGNAL_DASHBOARD_BASE_URL"] = f"http://127.0.0.1:{server.server_address[1]}"
        env["NODE_PATH"] = str(node_root / "lib/node_modules")
        browser_candidates = sorted(
            Path.home().glob(
                "Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
            )
        )
        if browser_candidates:
            env["PLAYWRIGHT_EXECUTABLE_PATH"] = str(browser_candidates[-1])
        result = subprocess.run(
            ["node", str(ROOT / "tests/dashboard_signal_driver.cjs")],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
        )
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
