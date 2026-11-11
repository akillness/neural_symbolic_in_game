from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import codex_feedback_pilot as pilot
from run_local_signal_comparison import fixtures

from nesy_game.runtime import to_jsonable


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    run = tmp_path / "pilot"
    monkeypatch.setattr(pilot, "RUN", run)
    monkeypatch.setattr(pilot, "MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(
        pilot,
        "codex_identity",
        lambda: {
            "codex_executable": "fake-codex",
            "codex_executable_sha256": "fake-hash",
            "codex_version": "fake-codex 1.0",
        },
    )

    def version_only(command, **kwargs):
        assert command == ["fake-codex", "--version"]
        return SimpleNamespace(stdout="fake-codex 1.0\n")

    monkeypatch.setattr(pilot.subprocess, "run", version_only)
    pilot.prepare()
    monkeypatch.setattr(pilot, "AUTH_FILE", tmp_path / "synthetic-auth.json")
    monkeypatch.setattr(
        pilot, "APPROVAL_SHA256", hashlib.sha256((run / "results.json").read_bytes()).hexdigest()
    )
    return run


def _valid_dispatch_result(prompt):
    payload = json.loads(prompt.decode().splitlines()[-1])
    candidate = payload["candidate"]
    policy = payload["state"]["action_policies"][candidate["action_type"]]
    candidate["preconditions"] = policy["required_preconditions"]
    candidate["effects"] = policy["allowed_effects"]
    candidate["disclosed_facts"] = []
    return {
        "response_text": json.dumps(candidate),
        "tokens": {"input_tokens": 17, "output_tokens": 11},
        "tls_payload_observed": False,
        "evidence": {"terminal_response_observed": True},
    }


def test_preparation_pairs_same_proposal_and_preserves_replay_artifacts(prepared):
    result = _load(prepared / "results.json")
    rows = result["cases"]
    assert len(rows) == 2 * len(fixtures())
    for case_id, state, original in pilot.pilot_cases():
        pair = [row for row in rows if row["case_id"] == case_id]
        assert {row["condition"] for row in pair} == {"detailed", "generic"}
        assert all(row["shared_proposal"] == to_jsonable(original) for row in pair)
        signals = {row["condition"]: row["input_signal"] for row in pair}
        assert signals["detailed"] != signals["generic"]
        for row in pair:
            raw = (prepared / row["prompt_file"]).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == row["prompt_sha256"]
            payload = json.loads(raw.decode().splitlines()[-1])
            assert payload == {
                "state": to_jsonable(state),
                "candidate": to_jsonable(original),
                "validator_feedback": signals[row["condition"]],
                "objective": "commit with signal_restored in final facts",
            }
    assert result["metadata"]["actual_model_identity"] is None
    assert result["metadata"]["cost_usd"] is None
    assert result["metadata"]["seed"] is None
    fixture_payload = [
        {"state": to_jsonable(state), "proposal": to_jsonable(action)}
        for _, state, action in pilot.pilot_cases()
    ]
    expected = hashlib.sha256(
        json.dumps(fixture_payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert result["metadata"]["fixture_sha256"] == expected
    for name, digest in result["metadata"]["source_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest


def test_response_is_parsed_and_independently_revalidated():
    state, original = fixtures()[1]  # missing required effect
    rejected = pilot.evaluate_response(state, original, json.dumps(to_jsonable(original)))
    assert rejected["final_gate_accepted"] is False
    assert rejected["objective_reached"] is False
    assert rejected["final_state"] == to_jsonable(state)

    corrected = to_jsonable(original)
    corrected["effects"] = ["signal_restored"]
    accepted = pilot.evaluate_response(state, original, json.dumps(corrected))
    assert accepted["final_gate_accepted"] is True
    assert accepted["objective_reached"] is True
    assert "signal_restored" in accepted["final_state"]["facts"]
    assert accepted["initial_state_unchanged"] is True

    corrected["actor_id"] = "other"
    changed_identity = pilot.evaluate_response(state, original, json.dumps(corrected))
    assert changed_identity["outcome"] == "identity_rejected"
    assert changed_identity["final_gate_accepted"] is False
    assert changed_identity["final_state"] == to_jsonable(state)


@pytest.mark.parametrize("response", ["not json", "[]", '{"action_id":"x"}'])
def test_malformed_or_incomplete_response_cannot_become_a_commit(response):
    state, original = fixtures()[1]
    with pytest.raises((ValueError, TypeError, KeyError)):
        pilot.evaluate_response(state, original, response)


@pytest.mark.parametrize("limit", [0, -1, 2, True, "1"])
def test_max_attempts_api_rejects_invalid_without_touching_cohort(prepared, monkeypatch, limit):
    before = {
        name: (prepared / name).read_bytes()
        for name in ("results.json", "approved_results.json", "status.json")
    }
    calls = []
    monkeypatch.setattr(
        pilot.codex_feedback_live_adapter, "dispatch", lambda **kwargs: calls.append(kwargs)
    )
    with pytest.raises(ValueError):
        pilot.run(max_attempts=limit)
    assert not calls
    assert {name: (prepared / name).read_bytes() for name in before} == before


def test_max_attempts_cli_dispatches_only_one(prepared, monkeypatch):
    monkeypatch.setattr(pilot, "RUN_ROOT", prepared.parent)
    monkeypatch.setattr(pilot, "LEGACY_RUN", prepared.parent / "legacy")
    calls = []

    def fake_dispatch(**kwargs):
        calls.append(kwargs)
        payload = json.loads(kwargs["prompt"].decode().splitlines()[-1])
        return {
            "response_text": json.dumps(payload["candidate"]),
            "tokens": {},
            "tls_payload_observed": False,
            "evidence": {},
        }

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "run",
            "--model",
            "gpt-5.6-luna",
            "--codex-bin",
            "fake-codex",
            "--run-dir",
            str(prepared),
            "--auth-file",
            str(prepared.parent / "synthetic-auth.json"),
            "--approval-sha256",
            pilot.APPROVAL_SHA256,
            "--max-attempts",
            "1",
        ],
    )
    pilot.main()
    assert len(calls) == 1
    assert all(row["status"] == "PENDING" for row in _load(prepared / "results.json")["cases"][1:])


def test_max_attempts_success_preserves_other_assignments_and_review(prepared, monkeypatch):
    before = _load(prepared / "results.json")
    approved = (prepared / "approved_results.json").read_bytes()
    calls = []

    def fake_dispatch(**kwargs):
        calls.append(kwargs)
        payload = json.loads(kwargs["prompt"].decode().splitlines()[-1])
        return {
            "response_text": json.dumps(payload["candidate"]),
            "tokens": {},
            "tls_payload_observed": False,
            "evidence": {},
        }

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run(max_attempts=1) is True
    after = _load(prepared / "results.json")
    assert len(calls) == 1
    assert after["cases"][0]["status"] == "COMPLETED"
    assert after["cases"][1:] == before["cases"][1:]
    assert all(row["status"] == "PENDING" for row in after["cases"][1:])
    assert (prepared / "approved_results.json").read_bytes() == approved
    assert _load(prepared / "status.json")["status"] == "STOPPED"


@pytest.mark.parametrize("failure", ["timeout", "process_error", "unexpected"])
def test_max_attempts_failure_stops_without_retry(prepared, monkeypatch, failure):
    before = _load(prepared / "results.json")
    approved = (prepared / "approved_results.json").read_bytes()
    calls = []

    def fake_dispatch(**kwargs):
        calls.append(kwargs)
        if failure == "unexpected":
            raise RuntimeError("synthetic failure")
        raise pilot.codex_feedback_live_adapter.DispatchError(failure)

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run(max_attempts=1) is False
    after = _load(prepared / "results.json")
    assert len(calls) == 1
    assert after["cases"][0]["status"] == "FAILED"
    assert after["cases"][0]["failure"]["transmission"] == "unknown"
    assert after["cases"][1:] == before["cases"][1:]
    assert (prepared / "approved_results.json").read_bytes() == approved
    assert _load(prepared / "status.json")["status"] == "STOPPED"


def test_max_attempts_interrupt_cannot_retry_or_overwrite(prepared, monkeypatch):
    before = _load(prepared / "results.json")
    calls = []

    def interrupted(**kwargs):
        calls.append(kwargs)
        raise KeyboardInterrupt()

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", interrupted)
    with pytest.raises(KeyboardInterrupt):
        pilot.run(max_attempts=1)
    after = _load(prepared / "results.json")
    assert len(calls) == 1
    assert after["cases"][1:] == before["cases"][1:]
    persisted = (prepared / "results.json").read_bytes()
    with pytest.raises(RuntimeError):
        pilot.run(max_attempts=1)
    assert len(calls) == 1
    assert (prepared / "results.json").read_bytes() == persisted


@pytest.mark.parametrize("limit", ["0", "-1", "2", "invalid"])
def test_max_attempts_cli_rejects_invalid_without_touching_cohort(prepared, monkeypatch, limit):
    before = {
        name: (prepared / name).read_bytes()
        for name in ("results.json", "approved_results.json", "status.json")
    }
    calls = []
    monkeypatch.setattr(
        pilot.codex_feedback_live_adapter, "dispatch", lambda **kwargs: calls.append(kwargs)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "run",
            "--model",
            "gpt-5.6-luna",
            "--codex-bin",
            "fake-codex",
            "--max-attempts",
            limit,
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code != 0
    assert not calls
    assert {name: (prepared / name).read_bytes() for name in before} == before


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_process_failure_stops_dispatch_and_preserves_assigned_rows(prepared, monkeypatch, failure):
    adapter = pilot.codex_feedback_live_adapter
    calls = []

    def fake_process(**kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise adapter.DispatchError("timeout" if failure == "timeout" else "process_error")
        payload = json.loads(kwargs["prompt"].decode().splitlines()[-1])
        return {
            "response_text": json.dumps(payload["candidate"]),
            "tokens": {"input_tokens": 12},
            "tls_payload_observed": False,
            "evidence": {},
        }

    monkeypatch.setattr(adapter, "dispatch", fake_process)
    pilot.run()
    result = _load(prepared / "results.json")
    rows = result["cases"]
    assert len(calls) == 2
    assert rows[0]["status"] == "COMPLETED"
    assert rows[1]["status"] == "FAILED"
    assert rows[1]["failure"]["code"] == ("timeout" if failure == "timeout" else "process_error")
    assert rows[1]["failure"]["transmission"] == "unknown"
    assert all(row["status"] == "PENDING" for row in rows[2:])
    assert _load(prepared / "status.json")["status"] == "STOPPED"
    assert result["summary"]["detailed"]["assigned"] == len(fixtures())
    assert result["summary"]["generic"]["assigned"] == len(fixtures())
    assert result["summary"]["detailed"]["completed"] == 1
    assert result["summary"]["generic"]["failed"] == 1
    assert result["summary"]["detailed"]["pending"] == len(fixtures()) - 1
    assert result["summary"]["generic"]["pending"] == len(fixtures()) - 1
    assert result["summary"]["detailed"]["gate_accepted"] == 0
    assert result["summary"]["generic"]["objective_reached"] == 0
    completed = rows[0]
    assert completed["tokens"] == {"input_tokens": 12}
    assert completed["response_text"]
    assert completed["evaluation"]["trace_hash"]
    assert completed["attempt"] == 1


@pytest.mark.parametrize("invalid_index", [0, 1], ids=["first-response", "after-success"])
@pytest.mark.parametrize(
    "response,error_type",
    [
        ("synthetic-private-output-비밀", "JSONDecodeError"),
        ('{"action_id":"synthetic-private-output-비밀"}', "CandidateParseError"),
    ],
    ids=["invalid-json", "invalid-schema"],
)
def test_invalid_response_finishes_collection_without_becoming_success(
    prepared, monkeypatch, response, error_type, invalid_index
):
    approved = (prepared / "approved_results.json").read_bytes()
    calls = []

    def fake_dispatch(**kwargs):
        index = len(calls)
        calls.append((kwargs["case_id"], kwargs["condition"]))
        result = _valid_dispatch_result(kwargs["prompt"])
        if index == invalid_index:
            result["response_text"] = response
        return result

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run() is True
    result = _load(prepared / "results.json")
    rows = result["cases"]
    assert len(calls) == len(set(calls)) == len(rows) == 10
    assert [row["status"] for row in rows] == [
        "FAILED" if index == invalid_index else "COMPLETED" for index in range(10)
    ]
    failed = rows[invalid_index]
    assert failed["failure"] == {
        "type": error_type,
        "code": "evaluation_error",
        "transmission": "unknown",
    }
    assert failed["evaluation"] is None
    assert "response_text" not in failed
    assert failed["response_sha256"] == hashlib.sha256(response.encode()).hexdigest()
    assert failed["response_bytes"] == len(response.encode())
    assert failed["tokens"] == {"input_tokens": 17, "output_tokens": 11}
    assert failed["evidence"] == {"terminal_response_observed": True}
    assert all(row["attempt"] == 1 for row in rows)
    status = _load(prepared / "status.json")
    assert (
        status["status"],
        status["planned"],
        status["completed"],
        status["failed"],
        status["pending"],
    ) == ("COMPLETED_WITH_FAILURES", 10, 9, 1, 0)
    for condition in ("detailed", "generic"):
        is_failed_arm = condition == failed["condition"]
        assert result["summary"][condition] == {
            "assigned": 5,
            "completed": 4 if is_failed_arm else 5,
            "failed": 1 if is_failed_arm else 0,
            "pending": 0,
            "gate_accepted": 4 if is_failed_arm else 5,
            "objective_reached": 3 if is_failed_arm else 4,
        }
    amendment = json.loads(approved)["metadata"]["collector_protocol_amendment"]
    assert failed["failure"]["type"] in amendment["expected_output_errors"]
    assert result["metadata"]["collector_protocol_amendment"] == amendment
    assert "stop_reason" not in result["metadata"]
    assert (prepared / "approved_results.json").read_bytes() == approved
    for artifact in prepared.rglob("*"):
        if artifact.is_file():
            assert "synthetic-private-output-비밀".encode() not in artifact.read_bytes()


@pytest.mark.parametrize(
    "response", ["not json", '{"action_id":"x"}'], ids=["invalid-json", "invalid-schema"]
)
def test_max_attempts_parse_failure_stops_after_single_dispatch(prepared, monkeypatch, response):
    before = _load(prepared / "results.json")
    approved = (prepared / "approved_results.json").read_bytes()
    calls = []

    def fake_dispatch(**kwargs):
        calls.append(kwargs["case_id"])
        result = _valid_dispatch_result(kwargs["prompt"])
        result["response_text"] = response
        return result

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run(max_attempts=1) is True
    after = _load(prepared / "results.json")
    assert len(calls) == 1
    assert after["cases"][0]["status"] == "FAILED"
    assert after["cases"][0]["failure"]["code"] == "evaluation_error"
    assert after["cases"][1:] == before["cases"][1:]
    assert _load(prepared / "status.json")["pending"] == 9
    assert _load(prepared / "status.json")["status"] == "STOPPED"
    assert (
        after["metadata"]["stop_reason"]
        == "Dispatcher attempt limit reached; remaining pairs were not attempted."
    )
    assert (prepared / "approved_results.json").read_bytes() == approved


@pytest.mark.parametrize(
    "failure",
    [
        "provider_error",
        "dispatch-json",
        "dispatch-schema",
        "evaluator-bug",
        "evaluator-value-error",
    ],
)
def test_non_model_output_failure_stops_before_second_dispatch(prepared, monkeypatch, failure):
    before = _load(prepared / "results.json")
    calls = []

    def fake_dispatch(**kwargs):
        calls.append(kwargs["case_id"])
        if failure == "provider_error":
            raise pilot.codex_feedback_live_adapter.DispatchError("provider_error")
        if failure == "dispatch-json":
            json.loads("not json")
        if failure == "dispatch-schema":
            state, original = fixtures()[0]
            pilot.evaluate_response(state, original, '{"action_id":"x"}')
        return _valid_dispatch_result(kwargs["prompt"])

    if failure.startswith("evaluator-"):

        def broken_evaluator(*args):
            if failure == "evaluator-value-error":
                raise ValueError("synthetic evaluator value error")
            raise RuntimeError("synthetic evaluator bug")

        monkeypatch.setattr(pilot, "evaluate_response", broken_evaluator)
    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run() is False
    result = _load(prepared / "results.json")
    assert len(calls) == 1
    failed = result["cases"][0]
    assert failed["status"] == "FAILED"
    assert failed["evaluation"] is None
    assert failed["failure"]["code"] == (
        "provider_error"
        if failure == "provider_error"
        else "evaluation_error"
        if failure.startswith("evaluator-")
        else "unclassified"
    )
    assert result["cases"][1:] == before["cases"][1:]
    status = _load(prepared / "status.json")
    assert (status["status"], status["failed"], status["pending"]) == ("STOPPED", 1, 9)
    assert result["summary"]["detailed"]["gate_accepted"] == 0
    assert result["summary"]["detailed"]["objective_reached"] == 0


def test_models_use_separate_cohorts_and_dispatch_the_assigned_selector(tmp_path, monkeypatch):
    root = tmp_path / "cohorts"
    monkeypatch.setattr(pilot, "RUN_ROOT", root)
    monkeypatch.setattr(pilot, "LEGACY_RUN", root / "legacy")
    monkeypatch.setattr(pilot, "RUN", root / "unused")
    monkeypatch.setattr(pilot, "MODEL", None)
    monkeypatch.setattr(pilot, "CODEX_BIN", None)
    monkeypatch.setattr(
        pilot,
        "codex_identity",
        lambda: {
            "codex_executable": "fake-codex",
            "codex_executable_sha256": "fake-hash",
            "codex_version": "fake-codex 1.0",
        },
    )
    adapter = pilot.codex_feedback_live_adapter
    dispatched = []

    def fake_process(**kwargs):
        dispatched.append(kwargs["model"])
        raise adapter.DispatchError("process_error")

    monkeypatch.setattr(adapter, "dispatch", fake_process)
    for model in ("gpt-5.6-luna", "gpt-5.6-terra"):
        monkeypatch.setattr(
            sys, "argv", ["pilot", "prepare", "--model", model, "--codex-bin", "fake-codex"]
        )
        pilot.main()
        result = _load(root / model / "results.json")
        assert result["metadata"]["model_selector"] == model
        digest = hashlib.sha256((root / model / "results.json").read_bytes()).hexdigest()
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "pilot",
                "run",
                "--model",
                model,
                "--codex-bin",
                "fake-codex",
                "--auth-file",
                str(tmp_path / "auth"),
                "--approval-sha256",
                digest,
            ],
        )
        with pytest.raises(SystemExit) as exc:
            pilot.main()
        assert exc.value.code == 1
        assert _load(root / model / "status.json")["status"] == "STOPPED"
    assert dispatched == ["gpt-5.6-luna", "gpt-5.6-terra"]
    assert (
        _load(root / "gpt-5.6-luna" / "results.json")["metadata"]["model_selector"]
        == "gpt-5.6-luna"
    )


@pytest.mark.parametrize("failure", ["missing", "nonzero"], ids=str)
def test_version_preflight_failure_leaves_no_cohort_directory(tmp_path, monkeypatch, failure):
    run = tmp_path / "cohort"
    monkeypatch.setattr(pilot, "RUN", run)
    monkeypatch.setattr(pilot, "MODEL", "gpt-5.6-luna")
    executable = tmp_path / "fake-codex"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"fake executable")
    monkeypatch.setattr(
        pilot.codex_feedback_live_adapter.isolation,
        "EXPECTED_SHA256",
        hashlib.sha256(executable.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(pilot, "CODEX_BIN", executable)

    def failed_version(command, **kwargs):
        if failure == "missing":
            raise FileNotFoundError("fake-codex")
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(pilot.subprocess, "run", failed_version)
    with pytest.raises((FileNotFoundError, subprocess.CalledProcessError)):
        pilot.prepare()
    assert not run.exists()


@pytest.mark.parametrize(
    "model", [None, "gpt-6-luna", "gpt-5.6-mars"], ids=["missing", "wrong-version", "unknown"]
)
def test_invalid_model_rejected_before_preparation(tmp_path, monkeypatch, model):
    root = tmp_path / "cohorts"
    monkeypatch.setattr(pilot, "RUN_ROOT", root)
    monkeypatch.setattr(pilot, "LEGACY_RUN", root / "legacy")
    monkeypatch.setattr(pilot, "RUN", root / "unused")
    monkeypatch.setattr(pilot, "MODEL", None)
    monkeypatch.setattr(pilot, "CODEX_BIN", None)
    args = ["pilot", "prepare", "--codex-bin", "fake-codex"] + (
        [] if model is None else ["--model", model]
    )
    monkeypatch.setattr(sys, "argv", args)
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code == 2
    assert not root.exists()


def test_cli_requires_explicit_native_binary(tmp_path, monkeypatch):
    root = tmp_path / "cohorts"
    monkeypatch.setattr(pilot, "RUN_ROOT", root)
    monkeypatch.setattr(sys, "argv", ["pilot", "prepare", "--model", "gpt-5.6-luna"])
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code == 2
    assert not root.exists()


def test_script_launcher_rejected_before_version_or_cohort_creation(tmp_path, monkeypatch):
    run = tmp_path / "cohort"
    launcher = tmp_path / "codex"
    launcher.write_bytes(b"#!/usr/bin/env node\n")
    monkeypatch.setattr(pilot, "RUN", run)
    monkeypatch.setattr(pilot, "MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(pilot, "CODEX_BIN", launcher)

    def forbidden(*args, **kwargs):
        pytest.fail("a launcher must not execute even for version probing")

    monkeypatch.setattr(pilot.subprocess, "run", forbidden)
    with pytest.raises((ValueError, RuntimeError), match="(?i)native|mach-o"):
        pilot.prepare()
    assert not run.exists()


@pytest.mark.parametrize("change", ["path", "contents", "version"], ids=str)
def test_changed_executable_identity_blocks_run_without_modifying_cohort(
    tmp_path, monkeypatch, change
):
    run = tmp_path / "cohort"
    executable = tmp_path / "codex-a"
    replacement = tmp_path / "codex-b"
    executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"original executable")
    replacement.write_bytes(b"\xcf\xfa\xed\xfe" + b"original executable")
    monkeypatch.setattr(
        pilot.codex_feedback_live_adapter.isolation,
        "EXPECTED_SHA256",
        hashlib.sha256(executable.read_bytes()).hexdigest(),
    )
    version = ["codex 0.147.0"]
    monkeypatch.setattr(pilot, "RUN", run)
    monkeypatch.setattr(pilot, "MODEL", "gpt-5.6-luna")
    monkeypatch.setattr(pilot, "CODEX_BIN", executable)

    def fake_process(command, **kwargs):
        assert command[-1] == "--version", "model execution must not start"
        return SimpleNamespace(stdout=version[0] + "\n")

    monkeypatch.setattr(pilot.subprocess, "run", fake_process)
    pilot.prepare()
    monkeypatch.setattr(pilot, "AUTH_FILE", tmp_path / "synthetic-auth")
    monkeypatch.setattr(
        pilot, "APPROVAL_SHA256", hashlib.sha256((run / "results.json").read_bytes()).hexdigest()
    )
    before_results = (run / "results.json").read_bytes()
    before_status = (run / "status.json").read_bytes()
    if change == "path":
        monkeypatch.setattr(pilot, "CODEX_BIN", replacement)
    elif change == "contents":
        executable.write_bytes(b"\xcf\xfa\xed\xfe" + b"changed executable")
    else:
        version[0] = "codex 0.167.0"
    with pytest.raises(RuntimeError, match="(?i)codex|executable|identity"):
        pilot.run()
    assert (run / "results.json").read_bytes() == before_results
    assert (run / "status.json").read_bytes() == before_status
    assert all(row["status"] == "PENDING" for row in _load(run / "results.json")["cases"])


def test_dispatch_uses_verified_executable_if_resolution_changes_after_preflight(
    prepared, monkeypatch
):
    original_identity = pilot.codex_identity()

    def changing_identity():
        monkeypatch.setattr(pilot, "CODEX_BIN", Path("replacement"))
        return original_identity

    monkeypatch.setattr(pilot, "codex_identity", changing_identity)
    dispatched = []

    def fake_dispatch(**kwargs):
        dispatched.append(kwargs["identity"]["codex_executable"])
        raise pilot.codex_feedback_live_adapter.DispatchError("process_error")

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run() is False
    assert dispatched == [original_identity["codex_executable"]]


@pytest.mark.parametrize("destination", ["root", "outside", "legacy", "legacy-child"], ids=str)
def test_unsafe_output_paths_are_rejected_without_writes(tmp_path, monkeypatch, destination):
    root = tmp_path / "cohorts"
    legacy = root / "legacy"
    path = {
        "root": root,
        "outside": tmp_path / "outside",
        "legacy": legacy,
        "legacy-child": legacy / "child",
    }[destination]
    monkeypatch.setattr(pilot, "RUN_ROOT", root)
    monkeypatch.setattr(pilot, "LEGACY_RUN", legacy)
    monkeypatch.setattr(pilot, "RUN", root / "unused")
    monkeypatch.setattr(pilot, "MODEL", None)
    monkeypatch.setattr(pilot, "CODEX_BIN", None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "prepare",
            "--model",
            "gpt-5.6-luna",
            "--codex-bin",
            "fake-codex",
            "--run-dir",
            str(path),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pilot.main()
    assert exc.value.code == 2
    assert not path.exists()


def test_existing_output_directory_is_not_overwritten(tmp_path, monkeypatch):
    root = tmp_path / "cohorts"
    existing = root / "custom"
    existing.mkdir(parents=True)
    marker = existing / "results.json"
    marker.write_text(' {"evidence":"preserve"} ', encoding="utf-8")
    monkeypatch.setattr(pilot, "RUN_ROOT", root)
    monkeypatch.setattr(pilot, "LEGACY_RUN", root / "legacy")
    monkeypatch.setattr(pilot, "RUN", root / "unused")
    monkeypatch.setattr(pilot, "MODEL", None)
    monkeypatch.setattr(pilot, "CODEX_BIN", None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "pilot",
            "prepare",
            "--model",
            "gpt-5.6-terra",
            "--codex-bin",
            "fake-codex",
            "--run-dir",
            str(existing),
        ],
    )
    with pytest.raises(FileExistsError):
        pilot.main()
    assert marker.read_text(encoding="utf-8") == ' {"evidence":"preserve"} '


def test_model_mismatch_rejects_prepared_cohort_before_dispatch(prepared, monkeypatch):
    monkeypatch.setattr(pilot, "MODEL", "gpt-5.6-terra")

    def forbidden(*args, **kwargs):
        pytest.fail("a different model must not run a prepared cohort")

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", forbidden)
    with pytest.raises(RuntimeError, match="model|selector"):
        pilot.run()
    result = _load(prepared / "results.json")
    assert result["metadata"]["model_selector"] == "gpt-5.6-luna"
    assert all(row["status"] == "PENDING" for row in result["cases"])


def test_modified_prompt_fails_before_any_model_dispatch(prepared, monkeypatch):
    row = _load(prepared / "results.json")["cases"][0]
    (prepared / row["prompt_file"]).write_text("tampered", encoding="utf-8")

    def forbidden(*args, **kwargs):
        pytest.fail("a model process must not start after prompt drift")

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", forbidden)
    with pytest.raises(RuntimeError, match="prompt does not match"):
        pilot.run()


def test_isolation_violation_stops_all_remaining_dispatch(prepared, monkeypatch):
    def denied(**kwargs):
        raise pilot.codex_feedback_live_adapter.DispatchError("isolation_violation")

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", denied)
    assert pilot.run() is False
    rows = _load(prepared / "results.json")["cases"]
    assert rows[0]["failure"]["code"] == "isolation_violation"
    assert all(row["status"] == "PENDING" for row in rows[1:])


@pytest.mark.parametrize(
    "change", ["case", "condition", "state", "proposal", "signal", "prompt_and_hash"]
)
def test_assignment_or_reviewed_payload_tampering_blocks_dispatch(prepared, monkeypatch, change):
    path = prepared / "results.json"
    data = _load(path)
    row = data["cases"][0]
    if change == "case":
        row["case_id"] = "other"
    elif change == "condition":
        row["condition"] = "generic"
    elif change == "state":
        row["initial_state"]["state_id"] = "other"
    elif change == "proposal":
        row["shared_proposal"]["actor_id"] = "other"
    elif change == "signal":
        row["input_signal"] = {"valid": True}
    else:
        content = b"tampered but rehashed"
        (prepared / row["prompt_file"]).write_bytes(content)
        row["prompt_sha256"] = hashlib.sha256(content).hexdigest()
    path.write_text(json.dumps(data), encoding="utf-8")
    (prepared / "approved_results.json").write_bytes(path.read_bytes())
    monkeypatch.setattr(pilot, "APPROVAL_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())

    def forbidden(*args, **kwargs):
        pytest.fail("tampered assignment must not dispatch")

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", forbidden)
    with pytest.raises(RuntimeError, match="changed after preparation|does not match"):
        pilot.run()


@pytest.mark.parametrize("field,other_index", [("condition", 1), ("case_id", 2)])
def test_swapping_labels_without_changing_prompt_hashes_blocks_dispatch(
    prepared, monkeypatch, field, other_index
):
    path = prepared / "results.json"
    data = _load(path)
    first, other = data["cases"][0], data["cases"][other_index]
    first[field], other[field] = other[field], first[field]
    path.write_text(json.dumps(data), encoding="utf-8")
    (prepared / "approved_results.json").write_bytes(path.read_bytes())
    monkeypatch.setattr(pilot, "APPROVAL_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())

    def forbidden(*args, **kwargs):
        pytest.fail("mismatched labels must not dispatch")

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", forbidden)
    with pytest.raises(RuntimeError, match="changed after preparation|does not match"):
        pilot.run()


def test_dispatch_uses_reviewed_prompt_if_file_changes_after_preflight(prepared, monkeypatch):
    adapter = pilot.codex_feedback_live_adapter
    rows = _load(prepared / "results.json")["cases"]
    second = prepared / rows[1]["prompt_file"]
    reviewed = second.read_bytes()
    observed = []

    def fake_process(**kwargs):
        observed.append(kwargs["prompt"])
        if len(observed) == 1:
            second.write_text("changed after preflight", encoding="utf-8")
            payload = json.loads(kwargs["prompt"].decode().splitlines()[-1])
            return {
                "response_text": json.dumps(payload["candidate"]),
                "tokens": {},
                "tls_payload_observed": False,
                "evidence": {},
            }
        raise adapter.DispatchError("timeout")

    monkeypatch.setattr(adapter, "dispatch", fake_process)
    pilot.run()
    assert len(observed) == 2
    assert observed[1] == reviewed


def test_missing_approval_blocks_every_request(prepared, monkeypatch):
    monkeypatch.setattr(pilot, "APPROVAL_SHA256", None)
    monkeypatch.setattr(
        pilot.codex_feedback_live_adapter,
        "dispatch",
        lambda **kwargs: pytest.fail("unapproved dispatch"),
    )
    before = (prepared / "results.json").read_bytes()
    with pytest.raises(RuntimeError, match="reviewed results SHA-256 are required"):
        pilot.run()
    assert (prepared / "results.json").read_bytes() == before
