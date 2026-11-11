from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import codex_feedback_live_adapter as adapter
import codex_feedback_pilot as pilot


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
