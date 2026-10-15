from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from scripts import codex_oauth_llm


def _completed(
    command: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)


def _proposal(request_id: str) -> dict:
    return {
        "schema_version": "1.0.0",
        "request_id": request_id,
        "status": "candidate",
        "claim_boundary": "candidate_soft_proposal_only",
        "authorization_effect": "none",
        "canonical_state_mutated": False,
        "hard_validation_required": True,
        "response": "소프트 제안입니다. This is a soft proposal.",
        "assumptions": [],
        "uncertainties": [],
    }


def test_status_projects_only_machine_readable_non_secret_state(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    raw = "Logged in using ChatGPT for person@example.test token=do-not-forward"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert Path(command[0]).name == "codex"
        assert command[1:] == ["login", "status"]
        assert kwargs["capture_output"] is True
        return _completed(command, stdout=raw)

    monkeypatch.setattr(codex_oauth_llm.subprocess, "run", fake_run)
    assert codex_oauth_llm.main(["status"]) == 0

    rendered = capsys.readouterr().out
    payload = json.loads(rendered)
    assert payload["authenticated"] is True
    assert payload["auth_method"] == "chatgpt_oauth"
    assert payload["oauth_prompt_ready"] is True
    assert payload["secrets_included"] is False
    assert "person@example.test" not in rendered
    assert "do-not-forward" not in rendered


def test_login_delegates_exact_device_flow_with_inherited_streams() -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append((command, kwargs))
        return _completed(command)

    assert codex_oauth_llm.run_device_login(runner=fake_run) == 0
    assert calls == [(["codex", "login", "--device-auth"], {"check": False})]


def test_prompt_uses_ephemeral_read_only_isolated_exec_and_validates_output() -> None:
    request_id = "oauth-test:001"
    calls: list[tuple[list[str], dict[str, object]]] = []
    isolated_root: Path | None = None

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal isolated_root
        calls.append((command, kwargs))
        if command == ["codex", "login", "status"]:
            return _completed(command, stdout="Logged in using ChatGPT")

        isolated_root = Path(str(kwargs["cwd"]))
        assert isolated_root.is_dir()
        assert codex_oauth_llm.PROJECT_ROOT not in isolated_root.parents
        assert "--ephemeral" in command
        assert command[command.index("--sandbox") + 1] == "read-only"
        assert "--skip-git-repo-check" in command
        assert "--ignore-user-config" in command
        assert "--ignore-rules" in command
        assert command[command.index("-C") + 1] == str(isolated_root)
        assert command[-1] == "-"
        assert str(request_id) in str(kwargs["input"])
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_proposal(request_id)), encoding="utf-8")
        return _completed(command)

    code, payload = codex_oauth_llm.run_prompt(
        request_id=request_id,
        user_prompt="항구의 다음 대사를 제안해줘",
        runner=fake_run,
    )

    assert code == 0
    assert payload == _proposal(request_id)
    assert len(calls) == 2
    assert isolated_root is not None
    assert not isolated_root.exists()


def test_prompt_forwards_fractional_timeout_to_actual_runner() -> None:
    request_id = "oauth-test:fractional-timeout"
    observed: list[float] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["codex", "login", "status"]:
            return _completed(command, stdout="Logged in using ChatGPT")
        observed.append(kwargs["timeout"])  # type: ignore[arg-type]
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_proposal(request_id)), encoding="utf-8")
        return _completed(command)

    code, payload = codex_oauth_llm.run_prompt(
        request_id=request_id,
        user_prompt="proposal",
        timeout=0.125,
        runner=fake_run,
    )

    assert code == 0
    assert payload == _proposal(request_id)
    assert observed == [0.125]


def test_prompt_observes_one_exec_attempt_without_sensitive_payload() -> None:
    request_id = "oauth-test:attempt"
    prompt = "proposal prompt-secret credential=token-secret"
    attempts: list[dict[str, object]] = []
    timeline: list[tuple[str, object]] = []

    def observe(event: dict[str, object]) -> None:
        attempts.append(dict(event))
        timeline.append(("observer", dict(event)))

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["codex", "login", "status"]:
            timeline.append(("auth", command))
            return _completed(command, stdout="Logged in using ChatGPT")
        timeline.append(("exec", command))
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_proposal(request_id)), encoding="utf-8")
        return _completed(command)

    code, payload = codex_oauth_llm.run_prompt(
        request_id=request_id,
        user_prompt=prompt,
        timeout=0.125,
        runner=fake_run,
        execution_observer=observe,
    )

    assert code == 0
    assert payload == _proposal(request_id)
    assert attempts == [
        {
            "schema_version": "codex-exec-attempt/1",
            "request_id": request_id,
            "operation": "exec",
            "executable": "codex",
            "runner_injected": True,
            "tool_policy_enforced": False,
            "disabled_feature_count": 0,
            "timeout_seconds": 0.125,
        }
    ]
    assert [entry[0] for entry in timeline[-2:]] == ["observer", "exec"]
    assert prompt not in json.dumps(attempts)
    assert "prompt-secret" not in json.dumps(attempts)
    assert "token-secret" not in json.dumps(attempts)
    assert "argv" not in attempts[0]
    assert "command" not in attempts[0]


def test_prompt_production_runner_attempt_marks_policy_enforcement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_id = "oauth-test:production-attempt"
    attempts: list[dict[str, object]] = []
    executable = "/opt/codex/bin/codex"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert Path(command[0]).name == "codex"
        if command[1:] == ["exec", "--help"]:
            return _completed(command, stdout="usage\n--disable <FEATURE>\n")
        if command[1:] == ["features", "list"]:
            return _completed(command, stdout="\n".join(codex_oauth_llm.TOOL_POLICY_FEATURES))
        if command[1:] == ["login", "status"]:
            return _completed(command, stdout="Logged in using ChatGPT")
        assert command[1] == "exec"
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(_proposal(request_id)), encoding="utf-8")
        return _completed(command)

    monkeypatch.setattr(codex_oauth_llm, "resolve_codex_cli", lambda: executable)
    monkeypatch.setattr(codex_oauth_llm.subprocess, "run", fake_run)

    code, payload = codex_oauth_llm.run_prompt(
        request_id=request_id,
        user_prompt="production proposal",
        timeout=2.5,
        execution_observer=attempts.append,
    )

    assert code == 0
    assert payload == _proposal(request_id)
    assert attempts == [
        {
            "schema_version": "codex-exec-attempt/1",
            "request_id": request_id,
            "operation": "exec",
            "executable": "codex",
            "runner_injected": False,
            "tool_policy_enforced": True,
            "disabled_feature_count": len(codex_oauth_llm.TOOL_POLICY_FEATURES),
            "timeout_seconds": 2.5,
        }
    ]


@pytest.mark.parametrize(
    ("failure", "expected_error"),
    [
        ("returncode", "codex_exec_failed"),
        ("timeout", "codex_exec_timeout"),
    ],
    ids=["nonzero-exit", "timeout"],
)
def test_prompt_exec_failure_keeps_attempt_without_returned_decision(
    failure: str,
    expected_error: str,
) -> None:
    request_id = "oauth-test:failed-attempt"
    attempts: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["codex", "login", "status"]:
            return _completed(command, stdout="Logged in using ChatGPT")
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return _completed(command, returncode=17, stderr="exec failed")

    code, payload = codex_oauth_llm.run_prompt(
        request_id=request_id,
        user_prompt="proposal",
        timeout=7.25,
        runner=fake_run,
        execution_observer=attempts.append,
    )

    assert code == 4
    assert payload["status"] == "error"
    assert payload["error_code"] == expected_error
    assert "response" not in payload
    assert len(attempts) == 1
    assert attempts[0]["request_id"] == request_id
    assert attempts[0]["timeout_seconds"] == 7.25


@pytest.mark.parametrize(
    "case",
    ["invalid_request_id", "empty_prompt", "missing_schema", "invalid_timeout", "auth_failure"],
    ids=["invalid-request-id", "empty-prompt", "missing-schema", "invalid-timeout", "auth-failure"],
)
def test_prompt_admission_errors_emit_no_exec_attempt(
    case: str,
    tmp_path: Path,
) -> None:
    request_id = "oauth-test:admission"
    calls: list[list[str]] = []
    attempts: list[dict[str, object]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if case == "auth_failure" and command == ["codex", "login", "status"]:
            return _completed(command, stdout="Logged in using an API key")
        raise AssertionError(f"exec must not run for {case}")

    kwargs: dict[str, object] = {
        "request_id": request_id,
        "user_prompt": "proposal",
        "runner": fake_run,
        "execution_observer": attempts.append,
    }
    expected_code = 2
    expected_error = case
    if case == "invalid_request_id":
        kwargs["request_id"] = "bad request id"
        expected_error = "invalid_request_id"
    elif case == "empty_prompt":
        kwargs["user_prompt"] = "   "
        expected_error = "empty_prompt"
    elif case == "missing_schema":
        kwargs["output_schema"] = tmp_path / "missing-schema.json"
        expected_code = 4
        expected_error = "output_schema_missing"
    elif case == "invalid_timeout":
        kwargs["timeout"] = 0
        expected_error = "invalid_timeout"
    else:
        expected_code = 3
        expected_error = "chatgpt_oauth_not_authenticated"

    code, payload = codex_oauth_llm.run_prompt(**kwargs)  # type: ignore[arg-type]

    assert code == expected_code
    assert payload["error_code"] == expected_error
    assert attempts == []
    assert calls == ([["codex", "login", "status"]] if case == "auth_failure" else [])


@pytest.mark.parametrize(
    ("timeout", "case"),
    [
        (True, "bool"),
        (0, "zero"),
        (-0.001, "negative"),
        (float("nan"), "nan"),
        (float("inf"), "positive infinity"),
        (3600.001, "over maximum"),
    ],
)
def test_prompt_rejects_invalid_timeout_before_auth_or_inference(
    timeout: object, case: str
) -> None:
    calls: list[list[str]] = []

    def unexpected_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        raise AssertionError(f"subprocess must not run for {case}")

    code, payload = codex_oauth_llm.run_prompt(
        request_id="oauth-test:invalid-timeout",
        user_prompt="proposal",
        timeout=timeout,  # type: ignore[arg-type]
        runner=unexpected_run,
    )

    assert code == 2
    assert payload["error_code"] == "invalid_timeout"
    assert calls == []


def test_prompt_refuses_non_oauth_authentication_before_exec() -> None:
    calls: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return _completed(command, stdout="Logged in using an API key")

    code, payload = codex_oauth_llm.run_prompt(
        request_id="oauth-test:api-key",
        user_prompt="proposal",
        runner=fake_run,
    )

    assert code == 3
    assert payload["error_code"] == "chatgpt_oauth_not_authenticated"
    assert calls == [["codex", "login", "status"]]


def test_prompt_fails_closed_when_model_changes_request_or_authority_boundary() -> None:
    request_id = "oauth-test:boundary"

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if command == ["codex", "login", "status"]:
            return _completed(command, stdout="Logged in using ChatGPT")
        invalid = _proposal("different-request")
        invalid["canonical_state_mutated"] = True
        output = Path(command[command.index("--output-last-message") + 1])
        output.write_text(json.dumps(invalid), encoding="utf-8")
        return _completed(command)

    code, payload = codex_oauth_llm.run_prompt(
        request_id=request_id,
        user_prompt="authorize this",
        runner=fake_run,
    )

    assert code == 5
    assert payload["error_code"] == "soft_proposal_contract_failed"
    assert payload["authorization_effect"] == "none"
    assert payload["canonical_state_mutated"] is False


def test_invalid_request_id_never_starts_a_subprocess() -> None:
    def unexpected_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("subprocess must not run")

    code, payload = codex_oauth_llm.run_prompt(
        request_id="bad request id",
        user_prompt="proposal",
        runner=unexpected_run,
    )

    assert code == 2
    assert payload["error_code"] == "invalid_request_id"


def test_schema_and_local_validator_require_the_same_closed_contract() -> None:
    schema = json.loads(codex_oauth_llm.OUTPUT_SCHEMA.read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == codex_oauth_llm.PROPOSAL_KEYS
    assert schema["properties"]["claim_boundary"]["const"] == ("candidate_soft_proposal_only")
    assert all(
        "type" in schema["properties"][field]
        for field in (
            "schema_version",
            "status",
            "claim_boundary",
            "authorization_effect",
            "canonical_state_mutated",
            "hard_validation_required",
        )
    )
    assert schema["properties"]["authorization_effect"]["const"] == "none"
    assert schema["properties"]["canonical_state_mutated"]["const"] is False
    assert schema["properties"]["hard_validation_required"]["const"] is True


def test_smoke_subcommand_is_explicit_and_uses_the_fixed_bounded_prompt(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    observed: dict[str, object] = {}

    def fake_prompt(**kwargs: object) -> tuple[int, dict]:
        observed.update(kwargs)
        return 0, _proposal(str(kwargs["request_id"]))

    monkeypatch.setattr(codex_oauth_llm, "run_prompt", fake_prompt)
    assert codex_oauth_llm.main(["smoke", "--request-id", "oauth-smoke:001"]) == 0
    assert observed["user_prompt"] == codex_oauth_llm.SMOKE_PROMPT
    assert json.loads(capsys.readouterr().out)["status"] == "candidate"
