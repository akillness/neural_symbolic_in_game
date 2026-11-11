from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import codex_feedback_live_adapter as adapter
import codex_feedback_pilot as pilot


@pytest.fixture
def synthetic_sandbox(monkeypatch):
    """Model sandbox presence only where both process and proxy are replaced."""
    real_is_file = Path.is_file

    def is_file(path):
        return path == Path("/usr/bin/sandbox-exec") or real_is_file(path)

    def forbidden(*args, **kwargs):
        pytest.fail("unapproved request reached process or network")

    monkeypatch.setattr(Path, "is_file", is_file)
    monkeypatch.setattr(adapter.subprocess, "Popen", forbidden)
    monkeypatch.setattr(adapter, "_Proxy", forbidden)


@pytest.fixture
def prepared_request(tmp_path, monkeypatch):
    case, state, action = pilot.pilot_cases()[0]
    proposal = pilot.to_jsonable(action)
    signal = pilot.to_jsonable(pilot.validate_candidate(state, action))
    prompt = pilot.build_prompt(case, proposal, signal, state).encode()
    binary = tmp_path / "codex"
    binary.write_bytes(b"synthetic-native-binary")
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    monkeypatch.setattr(adapter.isolation, "EXPECTED_SHA256", digest)
    identity = {
        "codex_executable": str(binary),
        "codex_executable_sha256": digest,
        "codex_version": "synthetic 1",
    }
    auth = tmp_path / "auth.json"
    auth.write_text('{"token":"synthetic-secret"}')
    args = {
        "prompt": prompt,
        "prompt_sha256": hashlib.sha256(prompt).hexdigest(),
        "model": "gpt-5.6-luna",
        "identity": identity,
        "auth_file": auth,
        "case_id": case,
        "condition": "detailed",
        "timeout": 10,
    }
    args["approval"] = {
        key: args[key] for key in ("model", "case_id", "condition", "prompt_sha256", "identity")
    }
    reviewed = tmp_path / "approved_results.json"
    reviewed.write_text(
        json.dumps(
            {
                "metadata": {
                    "pilot_protocol": "model-separated-v2",
                    "model_selector": args["model"],
                    **identity,
                },
                "cases": [
                    {
                        "case_id": case,
                        "condition": "detailed",
                        "prompt_sha256": args["prompt_sha256"],
                        "status": "PENDING",
                    }
                ],
            }
        )
    )
    args["approval"]["results_path"] = reviewed
    args["approval"]["results_sha256"] = hashlib.sha256(reviewed.read_bytes()).hexdigest()
    return args


@pytest.fixture
def cohort(tmp_path, monkeypatch, prepared_request):
    run = tmp_path / "cohort"
    monkeypatch.setattr(pilot, "RUN", run)
    monkeypatch.setattr(pilot, "MODEL", prepared_request["model"])
    monkeypatch.setattr(pilot, "AUTH_FILE", prepared_request["auth_file"])
    monkeypatch.setattr(pilot, "codex_identity", lambda: prepared_request["identity"])
    pilot.prepare()
    monkeypatch.setattr(
        pilot, "APPROVAL_SHA256", hashlib.sha256((run / "results.json").read_bytes()).hexdigest()
    )
    return run


@pytest.fixture(scope="session")
def aside_playwright_contract_cli(tmp_path_factory):
    """Explicit cloud SDK contract transport; absence keeps native Aside untouched."""
    if os.environ.get("NSG_ASIDE_TEST_TRANSPORT") != "playwright":
        return None
    node = shutil.which("node")
    assert node, "Node is required for the explicit Playwright contract transport"
    executable = tmp_path_factory.mktemp("aside-sdk-contract") / "aside-contract"
    executable.write_text(
        f"#!{sys.executable}\nimport os, sys\n"
        f"os.execv({node!r}, [{node!r}, {str(ROOT / 'tests/aside_playwright_contract_cli.cjs')!r}, *sys.argv[1:]])\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    return executable


@pytest.fixture(scope="session", autouse=True)
def explicit_aside_contract_transport(aside_playwright_contract_cli):
    with pytest.MonkeyPatch.context() as monkeypatch:
        if aside_playwright_contract_cli is not None:
            monkeypatch.setenv("ASIDE_BIN", str(aside_playwright_contract_cli))
        yield
