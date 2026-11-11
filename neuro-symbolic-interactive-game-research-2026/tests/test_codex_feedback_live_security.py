from __future__ import annotations

import hashlib
import io
import json
import multiprocessing
import socket
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import codex_feedback_live_adapter as adapter
import codex_feedback_pilot as pilot


def forbidden(*args, **kwargs):
    pytest.fail("unapproved request reached process or network")


@pytest.fixture
def fake_codex_output(monkeypatch):
    def install(events_for_home):
        class Proxy:
            server_address = ("127.0.0.1", 41001)

            def __init__(self, *args):
                pass

            def serve_forever(self):
                pass

            def shutdown(self):
                pass

            def server_close(self):
                pass

        class Process:
            returncode = 0

            def __init__(self, *args, **kwargs):
                events = events_for_home(Path(kwargs["env"]["CODEX_HOME"]))
                self.stdin = io.BytesIO()
                self.stdout = io.BytesIO(
                    b"".join(
                        (json.dumps(row, ensure_ascii=False) + "\n").encode() for row in events
                    )
                )
                self.stderr = io.BytesIO(b"")

            def poll(self):
                return self.returncode

        monkeypatch.setattr(adapter, "_Proxy", Proxy)
        monkeypatch.setattr(adapter.subprocess, "Popen", Process)
        monkeypatch.setattr(adapter.socket, "create_connection", forbidden)

    return install


def startup_warning_messages(codex_home):
    return {
        "config": (
            "Under-development features enabled: omit_skill_descriptions, skip_host_skill_discovery. "
            "Under-development features are incomplete and may behave unpredictably. "
            "To suppress this warning, set `suppress_unstable_features_warning = true` in "
            f"{codex_home / 'config.toml'}."
        ),
        "disabled-feature": (
            "Code Mode is unavailable because code-mode host is disabled. "
            "Code mode will fail closed; enable `features.code_mode_host` "
            "and install `codex-code-mode-host`."
        ),
    }


def test_forged_approval_without_reviewed_results_never_starts_process(
    prepared_request, monkeypatch, tmp_path
):
    prepared_request["approval"]["results_sha256"] = "0" * 64
    prepared_request["approval"]["results_path"] = str(tmp_path / "missing-reviewed-results.json")
    monkeypatch.setattr(adapter.subprocess, "Popen", forbidden)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        adapter.dispatch(**prepared_request)


@pytest.mark.parametrize(
    "change", ["model", "case", "condition", "prompt", "digest", "binary", "missing-approval"]
)
def test_cross_bound_approval_and_fixture_reject_before_any_process(
    prepared_request, monkeypatch, change
):
    request = prepared_request
    monkeypatch.setattr(adapter.subprocess, "Popen", forbidden)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    if change == "model":
        request["model"] = "gpt-5.6-terra"
    elif change == "case":
        request["case_id"] = pilot.pilot_cases()[1][0]
    elif change == "condition":
        request["condition"] = "generic"
    elif change == "prompt":
        request["prompt"] += b" synthetic-private-secret"
        request["prompt_sha256"] = hashlib.sha256(request["prompt"]).hexdigest()
        request["approval"]["prompt_sha256"] = request["prompt_sha256"]
    elif change == "digest":
        request["prompt_sha256"] = "0" * 64
        request["approval"]["prompt_sha256"] = "0" * 64
    elif change == "binary":
        Path(request["identity"]["codex_executable"]).write_bytes(b"replaced executable")
    else:
        request["approval"] = {}
    with pytest.raises((ValueError, RuntimeError)):
        adapter.dispatch(**request)


def test_dispatch_excludes_parent_credentials_and_returns_only_completed_response(
    prepared_request, monkeypatch
):
    request = prepared_request
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-parent-secret")
    monkeypatch.setenv("HTTPS_PROXY", "http://attacker.invalid:1234")
    observed = {}

    class Proxy:
        server_address = ("127.0.0.1", 41001)

        def __init__(self, *args):
            pass

        def serve_forever(self):
            pass

        def shutdown(self):
            pass

        def server_close(self):
            pass

    class Process:
        returncode = 0

        def __init__(self, args, **kwargs):
            observed.update(kwargs)
            observed["args"] = args
            observed["auth"] = (Path(kwargs["env"]["CODEX_HOME"]) / "auth.json").resolve()
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(
                (
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"type": "agent_message", "text": "synthetic response"},
                        }
                    )
                    + "\n"
                    + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 7}})
                    + "\n"
                ).encode()
            )
            self.stderr = io.BytesIO(b"")

        def poll(self):
            return self.returncode

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    result = adapter.dispatch(**request)
    assert result["response_text"] == "synthetic response"
    assert result["tokens"] == {"input_tokens": 7}
    assert result["actual_model_identity"] is None and result["cost_usd"] is None
    assert observed["auth"] == request["auth_file"]
    assert "OPENAI_API_KEY" not in observed["env"]
    assert observed["env"]["HTTPS_PROXY"] == "http://127.0.0.1:41001"
    assert "synthetic-parent-secret" not in json.dumps(result)


@pytest.mark.parametrize(
    "kind,message,classification",
    [
        pytest.param("item", "synthetic error 비밀", "unknown", id="item-text"),
        pytest.param("top", "synthetic error 비밀", "unknown", id="top-text"),
        pytest.param("item", None, "unknown", id="item-missing"),
        pytest.param("top", None, "unknown", id="top-missing"),
        pytest.param("item", 42, "unknown", id="item-nonstring"),
        pytest.param("top", 42, "unknown", id="top-nonstring"),
        pytest.param("nested", "synthetic error 비밀", "unknown", id="nested-text"),
        pytest.param("nested", None, "unknown", id="nested-missing"),
        pytest.param("nested", 42, "unknown", id="nested-nonstring"),
        pytest.param("top-priority", "synthetic error 비밀", "unknown", id="top-over-nested"),
        pytest.param("top-priority", 42, "unknown", id="nonstring-top-over-nested"),
        pytest.param("item-nested", "synthetic error 비밀", "unknown", id="item-nested-text"),
        pytest.param("item-nested", None, "unknown", id="item-nested-missing"),
        pytest.param("item-nested", 42, "unknown", id="item-nested-nonstring"),
        pytest.param("item-priority", "synthetic error 비밀", "unknown", id="item-over-nested"),
        pytest.param("item-priority", 42, "unknown", id="nonstring-item-over-nested"),
        pytest.param(
            "top",
            "The 'gpt-5.6-luna' model is not supported when using Codex with a ChatGPT account.",
            "unsupported_model",
            id="luna-account-unsupported",
        ),
        pytest.param(
            "item-nested",
            "The 'gpt-5.6-luna' model is not supported when using Codex with a ChatGPT account.",
            "unsupported_model",
            id="unsupported-nested-item",
        ),
        pytest.param(
            "nested",
            "The 'gpt-5.6-terra' model is not supported when using Codex with a ChatGPT account.",
            "unknown",
            id="other-model-does-not-diagnose-requested-model",
        ),
        pytest.param(
            "nested",
            "Your access token has expired. Please sign in again.",
            "auth",
            id="expired-token",
        ),
        pytest.param(
            "item",
            "Your authentication token has been invalidated. Please try signing in again.",
            "auth",
            id="invalidated-token",
        ),
        pytest.param(
            "top", "Authentication required. Please run 'codex login'.", "auth", id="login-required"
        ),
        pytest.param("nested", "Rate limit reached.", "rate_limit", id="rate-limit"),
        pytest.param("item-nested", "Too many requests.", "rate_limit", id="too-many-requests"),
        pytest.param(
            "top",
            "You exceeded your current quota, please check your plan and billing details.",
            "quota",
            id="quota-exhausted",
        ),
        pytest.param("nested", "You've hit your usage limit.", "quota", id="usage-limit"),
        pytest.param(
            "top",
            " \nThe 'gpt-5.6-luna' model is not supported when using Codex with a ChatGPT account.\t",
            "unsupported_model",
            id="unsupported-surrounding-whitespace",
        ),
        pytest.param(
            "top", "rate limit reached.", "unknown", id="message-signature-is-case-sensitive"
        ),
        pytest.param(
            "item",
            "The '비밀🔑' model is not supported when using Codex with a ChatGPT account.",
            "unknown",
            id="unicode-model-not-allowlisted",
        ),
        pytest.param(
            "top",
            "Bearer synthetic-access-token: Rate limit reached.",
            "unknown",
            id="recognized-message-with-secret-prefix",
        ),
        pytest.param(
            "nested",
            "Your access token has expired. Please sign in again. synthetic-secret=비밀🔑",
            "unknown",
            id="recognized-message-with-secret-suffix",
        ),
        pytest.param(
            "item",
            "The 'gpt-5.6-luna' model is not supported when using Codex with a ChatGPT account. synthetic-secret",
            "unknown",
            id="unsupported-with-extra-server-text",
        ),
        pytest.param(
            "top",
            "sk-synthetic-secret-비밀🔑 rate_limit authentication_error unsupported_model",
            "unknown",
            id="secret-like-keywords-are-not-diagnosis",
        ),
    ],
)
def test_error_events_fail_closed_and_keep_only_message_hash(
    prepared_request, fake_codex_output, capsys, kind, message, classification
):
    event = (
        {"type": "item.completed", "item": {"type": "error"}}
        if kind.startswith("item")
        else {"type": "error"}
    )
    if kind == "item-nested":
        event["item"]["error"] = {} if message is None else {"message": message}
    elif kind == "item-priority":
        event["item"]["error"] = {"message": "synthetic nested secret"}
        event["item"]["message"] = message
    elif kind == "nested":
        event["error"] = {} if message is None else {"message": message}
    elif kind == "top-priority":
        event["error"] = {"message": "synthetic nested secret"}
        event["message"] = message
    elif message is not None:
        (event["item"] if kind == "item" else event)["message"] = message
    output = [
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "synthetic-private-response"},
        },
        {"type": "turn.completed", "usage": {"input_tokens": 7}},
        event,
    ]

    fake_codex_output(lambda home: output)
    with pytest.raises(adapter.DispatchError) as exc:
        adapter.dispatch(**prepared_request)
    assert exc.value.code == "provider_error"
    evidence = exc.value.evidence
    assert evidence["events"][-1]["error_classification"] == classification
    expected = (
        hashlib.sha256(message.encode("utf-8")).hexdigest() if isinstance(message, str) else None
    )
    assert evidence["events"][-1]["error_message_sha256"] == expected
    serialized = json.dumps(evidence, ensure_ascii=False) + str(exc.value)
    assert "synthetic-private-response" not in serialized
    assert "synthetic error 비밀" not in serialized
    assert "synthetic nested secret" not in serialized
    captured = capsys.readouterr()
    if isinstance(message, str):
        assert message not in serialized + captured.out + captured.err
    assert "synthetic-private-response" not in captured.out + captured.err


@pytest.mark.parametrize("kind", ["top", "item"])
@pytest.mark.parametrize("placement", ["direct", "nested"])
@pytest.mark.parametrize(
    "code,message,classification",
    [
        pytest.param(
            "authentication_error", "synthetic-private-error", "auth", id="authentication"
        ),
        pytest.param(
            "rate_limit_exceeded", "synthetic-private-error", "rate_limit", id="rate-limit"
        ),
        pytest.param(
            "invalid_request_error",
            "synthetic-private-error",
            "invalid_request",
            id="invalid-request",
        ),
        pytest.param("server_error", "synthetic-private-error", "server", id="server"),
        pytest.param(
            "context_length_exceeded",
            "synthetic-private-error",
            "context_length",
            id="context-length",
        ),
        pytest.param("synthetic-unknown-code", "synthetic-private-error", "unknown", id="unknown"),
        pytest.param(42, "synthetic-private-error", "unknown", id="number"),
        pytest.param({"unexpected": "code"}, "synthetic-private-error", "unknown", id="object"),
        pytest.param(None, "synthetic-private-error", "unknown", id="null"),
        pytest.param(
            "unsupported_model",
            "synthetic-private-error",
            "unsupported_model",
            id="unsupported-code",
        ),
        pytest.param(
            "model_not_supported",
            "synthetic-private-error",
            "unsupported_model",
            id="model-not-supported-code",
        ),
        pytest.param(
            "model_not_found",
            "synthetic-private-error",
            "model_unavailable",
            id="missing-model-is-not-unsupported",
        ),
        pytest.param("invalid_api_key", "synthetic-private-error", "auth", id="invalid-api-key"),
        pytest.param("token_expired", "synthetic-private-error", "auth", id="expired-token-code"),
        pytest.param(
            "authentication_error",
            "The 'gpt-5.6-luna' model is not supported when using Codex with a ChatGPT account.",
            "auth",
            id="auth-code-over-unsupported-message",
        ),
        pytest.param(
            "model_not_supported",
            "Your access token has expired. Please sign in again.",
            "unsupported_model",
            id="unsupported-code-over-auth-message",
        ),
    ],
)
def test_error_code_classification_remains_fail_closed(
    prepared_request, fake_codex_output, kind, placement, code, message, classification
):
    container = {"type": "error", "message": message}
    if placement == "direct":
        container["code"] = code
        container["error"] = {"code": "rate_limit_exceeded"}
    else:
        container["error"] = {"code": code}
    event = {"type": "item.completed", "item": container} if kind == "item" else container
    output = [
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": "synthetic-private-response"},
        },
        {"type": "turn.completed", "usage": {"input_tokens": 7}},
        event,
    ]

    fake_codex_output(lambda home: output)
    with pytest.raises(adapter.DispatchError) as exc:
        adapter.dispatch(**prepared_request)
    assert exc.value.code == "provider_error"
    evidence = exc.value.evidence
    assert evidence["events"][-1]["error_classification"] == classification
    assert (
        evidence["events"][-1]["error_message_sha256"]
        == hashlib.sha256(message.encode("utf-8")).hexdigest()
    )
    serialized = json.dumps(evidence) + str(exc.value)
    assert "synthetic-private-error" not in serialized
    assert "synthetic-private-response" not in serialized
    assert "synthetic-unknown-code" not in serialized
    assert message not in serialized


@pytest.mark.parametrize("kind", ["top", "item"])
@pytest.mark.parametrize(
    "warning,mutation,classification",
    [
        pytest.param("config", "exact", "startup_config_warning", id="bound-config-warning"),
        pytest.param(
            "disabled-feature",
            "exact",
            "startup_disabled_feature_warning",
            id="disabled-feature-warning",
        ),
        pytest.param("config", "wrong-path", "unknown", id="other-config-path"),
        pytest.param("config", "reordered-features", "unknown", id="other-feature-order"),
        pytest.param("config", "prefix", "unknown", id="config-warning-secret-prefix"),
        pytest.param("config", "suffix", "unknown", id="config-warning-secret-suffix"),
        pytest.param("disabled-feature", "prefix", "unknown", id="disabled-feature-secret-prefix"),
        pytest.param("disabled-feature", "suffix", "unknown", id="disabled-feature-secret-suffix"),
    ],
)
def test_incomplete_startup_warning_never_succeeds(
    prepared_request, fake_codex_output, capsys, kind, warning, mutation, classification
):
    observed = {}

    def startup_events(codex_home):
        config_path = codex_home / "config.toml"
        message = startup_warning_messages(codex_home)[warning]
        if mutation == "wrong-path":
            message = message.replace(
                str(config_path), str(codex_home / "synthetic-private-config.toml")
            )
        elif mutation == "reordered-features":
            message = message.replace(
                "omit_skill_descriptions, skip_host_skill_discovery",
                "skip_host_skill_discovery, omit_skill_descriptions",
            )
        elif mutation == "prefix":
            message = "synthetic-secret=비밀🔑 " + message
        elif mutation == "suffix":
            message += " synthetic-secret=비밀🔑"
        observed.update(message=message, config_path=str(config_path))
        container = {"type": "error", "message": message}
        event = {"type": "item.completed", "item": container} if kind == "item" else container
        return [{"type": "thread.started"}, event]

    fake_codex_output(startup_events)
    with pytest.raises(adapter.DispatchError) as exc:
        adapter.dispatch(**prepared_request)
    assert exc.value.code == "provider_error"
    assert exc.value.transmission == "unknown"
    evidence = exc.value.evidence
    assert evidence["returncode"] == 0
    assert [event["type"] for event in evidence["events"]] == [
        "thread.started",
        "item.completed" if kind == "item" else "error",
    ]
    assert evidence["events"][-1]["error_classification"] == classification
    assert (
        evidence["events"][-1]["error_message_sha256"]
        == hashlib.sha256(observed["message"].encode("utf-8")).hexdigest()
    )
    captured = capsys.readouterr()
    serialized = (
        json.dumps(evidence, ensure_ascii=False) + str(exc.value) + captured.out + captured.err
    )
    assert observed["message"] not in serialized
    assert observed["config_path"] not in serialized
    assert "synthetic-secret" not in serialized
    assert "synthetic-private-config" not in serialized


@pytest.mark.parametrize(
    "variant,failure",
    [
        pytest.param("ordered-pair", None, id="exact-ordered-startup-pair-completes"),
        pytest.param("top-config", "provider_error", id="top-level-config-is-real-error"),
        pytest.param("top-disabled", "provider_error", id="top-level-disabled-is-real-error"),
        pytest.param("reordered", "provider_error", id="warning-order-is-required"),
        pytest.param("duplicate-config", "provider_error", id="duplicate-config-warning"),
        pytest.param("duplicate-disabled", "provider_error", id="duplicate-disabled-warning"),
        pytest.param("after-turn", "provider_error", id="warnings-after-turn-start"),
        pytest.param("post-completion", "provider_error", id="warnings-after-completed-response"),
        pytest.param("before-thread", "provider_error", id="warnings-before-thread-start"),
        pytest.param("no-thread", "provider_error", id="warnings-require-thread-start"),
        pytest.param(
            "missing-config", "provider_error", id="disabled-warning-alone-cannot-complete"
        ),
        pytest.param(
            "missing-disabled", "provider_error", id="config-warning-alone-cannot-complete"
        ),
        pytest.param("missing-turn", "protocol_error", id="ordered-pair-requires-turn-start"),
        pytest.param("missing-response", "protocol_error", id="ordered-pair-requires-response"),
        pytest.param("missing-completion", "protocol_error", id="ordered-pair-requires-completion"),
        pytest.param("pair-only", "protocol_error", id="ordered-pair-without-turn-or-result"),
        pytest.param("duplicate-thread", "protocol_error", id="duplicate-thread-start"),
        pytest.param("duplicate-turn", "protocol_error", id="duplicate-turn-start"),
        pytest.param("unknown", "provider_error", id="unknown-error-is-not-warning"),
        pytest.param("wrong-path", "provider_error", id="config-path-must-match-scratch-home"),
        pytest.param("whitespace", "provider_error", id="warning-exemption-does-not-strip"),
        pytest.param("prefix", "provider_error", id="warning-with-secret-prefix"),
        pytest.param("suffix", "provider_error", id="warning-with-secret-suffix"),
        pytest.param("envelope-code", "provider_error", id="coded-envelope-is-real-error"),
        pytest.param("item-code", "provider_error", id="coded-item-is-real-error"),
        pytest.param("nested-code", "provider_error", id="hidden-nested-code-is-real-error"),
        pytest.param("envelope-status", "provider_error", id="envelope-http-status-is-real-error"),
        pytest.param("item-status", "provider_error", id="item-http-status-is-real-error"),
        pytest.param(
            "nested-status", "provider_error", id="hidden-nested-http-status-is-real-error"
        ),
        pytest.param("nested-message", "provider_error", id="nested-message-is-not-native-warning"),
        pytest.param(
            "envelope-nested-auth", "provider_error", id="envelope-nested-auth-is-real-error"
        ),
        pytest.param("item-nested-auth", "provider_error", id="item-nested-auth-is-real-error"),
    ],
)
def test_only_exact_ordered_startup_warning_pair_can_complete(
    prepared_request, fake_codex_output, capsys, variant, failure
):
    observed = {}
    response_text = "synthetic-startup-response-비밀"
    usage = {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10}

    def startup_events(codex_home):
        messages = startup_warning_messages(codex_home)
        config = {
            "type": "item.completed",
            "item": {"type": "error", "message": messages["config"]},
        }
        disabled = {
            "type": "item.completed",
            "item": {"type": "error", "message": messages["disabled-feature"]},
        }
        thread = {"type": "thread.started"}
        turn = {"type": "turn.started"}
        response = {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": response_text},
        }
        completed = {"type": "turn.completed", "usage": usage}
        events = [thread, config, disabled, turn, response, completed]
        if variant == "top-config":
            events[1] = config["item"]
        elif variant == "top-disabled":
            events[2] = disabled["item"]
        elif variant == "reordered":
            events[1:3] = [disabled, config]
        elif variant == "duplicate-config":
            events.insert(2, config)
        elif variant == "duplicate-disabled":
            events.insert(3, disabled)
        elif variant == "after-turn":
            events = [thread, turn, config, disabled, response, completed]
        elif variant == "post-completion":
            events = [thread, turn, response, completed, config, disabled]
        elif variant == "before-thread":
            events = [config, disabled, thread, turn, response, completed]
        elif variant == "no-thread":
            events = events[1:]
        elif variant.startswith("missing-"):
            events.remove(
                {
                    "missing-config": config,
                    "missing-disabled": disabled,
                    "missing-turn": turn,
                    "missing-response": response,
                    "missing-completion": completed,
                }[variant]
            )
        elif variant == "pair-only":
            events = events[:3]
        elif variant == "duplicate-thread":
            events.insert(1, thread)
        elif variant == "duplicate-turn":
            events.insert(4, turn)
        elif variant == "unknown":
            config["item"]["message"] = "synthetic-secret=비밀🔑 unknown provider error"
        elif variant == "wrong-path":
            config["item"]["message"] = messages["config"].replace(
                str(codex_home), str(codex_home / "synthetic-private-home")
            )
        elif variant == "whitespace":
            config["item"]["message"] = " " + messages["config"]
        elif variant == "prefix":
            config["item"]["message"] = "synthetic-secret=비밀🔑 " + messages["config"]
        elif variant == "suffix":
            disabled["item"]["message"] += " synthetic-secret=비밀🔑"
        elif variant == "nested-message":
            config["item"]["error"] = {"message": config["item"].pop("message")}
        elif variant == "envelope-nested-auth":
            config["error"] = {"code": "authentication_error"}
        elif variant == "item-nested-auth":
            config["item"]["error"] = {"code": "authentication_error"}
        elif variant.endswith(("-code", "-status")):
            placement, field = variant.split("-")
            target = config if placement == "envelope" else config["item"]
            if placement == "nested":
                target = target.setdefault("error", {})
            target["code" if field == "code" else "status_code"] = (
                "synthetic-private-code" if field == "code" else "429"
            )
        observed.update(messages=messages, config_path=str(codex_home / "config.toml"))
        return events

    fake_codex_output(startup_events)
    if failure is None:
        result = adapter.dispatch(**prepared_request)
        assert result["response_text"] == response_text
        assert result["tokens"] == usage
        evidence = result["evidence"]
        warnings = [event for event in evidence["events"] if event.get("item_type") == "error"]
        assert [event["error_classification"] for event in warnings] == [
            "startup_config_warning",
            "startup_disabled_feature_warning",
        ]
        assert [event["error_message_sha256"] for event in warnings] == [
            hashlib.sha256(message.encode("utf-8")).hexdigest()
            for message in observed["messages"].values()
        ]
        exception_text = ""
    else:
        with pytest.raises(adapter.DispatchError) as exc:
            adapter.dispatch(**prepared_request)
        assert exc.value.code == failure
        assert exc.value.transmission == "unknown"
        evidence = exc.value.evidence
        exception_text = str(exc.value)
    captured = capsys.readouterr()
    serialized = (
        json.dumps(evidence, ensure_ascii=False) + exception_text + captured.out + captured.err
    )
    assert response_text not in serialized
    assert observed["config_path"] not in serialized
    assert all(message not in serialized for message in observed["messages"].values())
    assert "synthetic-secret" not in serialized
    assert "synthetic-private" not in serialized


def test_response_after_turn_completion_cannot_become_success(
    prepared_request, fake_codex_output, capsys
):
    response_text = "synthetic-private-late-response-비밀"
    output = [
        {"type": "thread.started"},
        {"type": "turn.started"},
        {"type": "turn.completed", "usage": {"input_tokens": 7}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": response_text}},
    ]
    fake_codex_output(lambda home: output)

    with pytest.raises(adapter.DispatchError) as exc:
        adapter.dispatch(**prepared_request)

    assert exc.value.code == "protocol_error"
    assert exc.value.transmission == "unknown"
    assert exc.value.evidence["returncode"] == 0
    captured = capsys.readouterr()
    assert (
        response_text
        not in json.dumps(exc.value.evidence, ensure_ascii=False)
        + str(exc.value)
        + captured.out
        + captured.err
    )


@pytest.mark.parametrize(
    "line,host",
    [
        ("attacker.invalid:443", "attacker.invalid:443"),
        ("chatgpt.com:443@attacker.invalid:443", "chatgpt.com:443"),
        ("chatgpt.com:443", "attacker.invalid:443"),
        ("chatgpt.com:444", "chatgpt.com:444"),
    ],
)
def test_proxy_rejects_destination_bypass_without_upstream_connection(monkeypatch, line, host):
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with adapter._Proxy(("127.0.0.1", 0), adapter._Connect) as proxy:
        proxy.stop = threading.Event()
        proxy.violation = threading.Event()
        thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        try:
            with socket.socket() as client:
                client.settimeout(3)
                client.connect(proxy.server_address)
                client.sendall(f"CONNECT {line} HTTP/1.1\r\nHost: {host}\r\n\r\n".encode())
                assert client.recv(1024) == b""
            assert proxy.violation.wait(3)
        finally:
            proxy.shutdown()
            thread.join()


@pytest.mark.parametrize(
    "failure",
    [
        "timeout",
        "isolation_violation",
        "transport_error",
        "process_error",
        "protocol_error",
        "unclassified",
    ],
)
def test_runner_stops_after_failure_preserving_completed_and_pending_denominators(
    cohort, monkeypatch, failure
):
    calls = []

    def fake_dispatch(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            payload = json.loads(kwargs["prompt"].decode().splitlines()[-1])
            return {
                "response_text": json.dumps(payload["candidate"]),
                "tokens": {"input_tokens": 7},
                "tls_payload_observed": False,
                "evidence": {},
            }
        if failure == "unclassified":
            raise RuntimeError("synthetic-secret-do-not-persist")
        raise adapter.DispatchError(failure)

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fake_dispatch)
    assert pilot.run() is False
    raw = (cohort / "results.json").read_text()
    result = json.loads(raw)
    rows = result["cases"]
    assert len(calls) == 2
    assert [row["status"] for row in rows[:2]] == ["COMPLETED", "FAILED"]
    assert all(row["status"] == "PENDING" for row in rows[2:])
    assert rows[1]["failure"]["code"] == failure
    assert rows[1]["failure"]["transmission"] == "unknown"
    assert result["summary"]["detailed"]["assigned"] == len(pilot.pilot_cases())
    assert result["summary"]["generic"]["assigned"] == len(pilot.pilot_cases())
    assert result["summary"]["detailed"]["completed"] == 1
    assert result["summary"]["generic"]["failed"] == 1
    assert result["summary"]["generic"]["pending"] == len(pilot.pilot_cases()) - 1
    assert "synthetic-secret-do-not-persist" not in raw
    assert json.loads((cohort / "status.json").read_text())["status"] == "STOPPED"


def test_unapproved_cohort_digest_preserves_evidence_and_never_dispatches(cohort, monkeypatch):
    before = {name: (cohort / name).read_bytes() for name in ("results.json", "status.json")}
    monkeypatch.setattr(pilot, "APPROVAL_SHA256", "0" * 64)
    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", forbidden)
    with pytest.raises(RuntimeError, match="reviewed results SHA-256"):
        pilot.run()
    assert {name: (cohort / name).read_bytes() for name in before} == before


def test_concurrent_process_cannot_claim_or_overwrite_same_cohort(
    cohort, prepared_request, monkeypatch
):
    context = multiprocessing.get_context("fork")
    first_entered = context.Event()
    release_first = context.Event()
    output = context.Queue()

    def worker(first):
        def identity():
            if first:
                first_entered.set()
                if not release_first.wait(10):
                    raise RuntimeError("test synchronization failed")
            return prepared_request["identity"]

        def no_dispatch(**kwargs):
            output.put(("dispatch", first))
            raise adapter.DispatchError("transport_error")

        pilot.codex_identity = identity
        pilot.codex_feedback_live_adapter.dispatch = no_dispatch
        try:
            output.put(("result", first, pilot.run()))
        # Relay child-process termination to the parent instead of losing the failure.
        except BaseException as exc:  # noqa: BLE001
            output.put(("error", first, type(exc).__name__, str(exc)))

    first = context.Process(target=worker, args=(True,))
    second = context.Process(target=worker, args=(False,))
    first.start()
    try:
        assert first_entered.wait(10), "first process did not acquire the claim"
        before = {name: (cohort / name).read_bytes() for name in ("results.json", "status.json")}
        second.start()
        second.join(10)
        assert not second.is_alive(), "second process blocked instead of rejecting the claim"
        event = output.get(timeout=3)
        assert event == ("error", False, "RuntimeError", "cohort is already running")
        assert {name: (cohort / name).read_bytes() for name in before} == before
    finally:
        release_first.set()
        first.join(10)
        if first.is_alive():
            first.terminate()
            first.join()
        if second.is_alive():
            second.terminate()
            second.join()
        output.close()
    assert first.exitcode == 0
    assert second.exitcode == 0
    rows = json.loads((cohort / "results.json").read_text())["cases"]
    assert rows[0]["status"] == "FAILED"
    assert all(row["status"] == "PENDING" for row in rows[1:])


@pytest.mark.parametrize(
    "event,returncode,expected",
    [
        ({"type": "thread.started", "secret": "synthetic-event-secret"}, 7, "process_error"),
        (
            {
                "type": "error",
                "error": {
                    "status_code": 429,
                    "code": "rate_limit_exceeded",
                    "message": "synthetic-event-secret",
                },
            },
            1,
            "provider_error",
        ),
        (
            {
                "type": "synthetic-event-secret",
                "status_code": "429",
                "code": "synthetic-secret-code",
            },
            1,
            "protocol_error",
        ),
    ],
)
def test_failed_dispatch_preserves_bounded_evidence_without_raw_secrets(
    prepared_request, monkeypatch, event, returncode, expected
):
    stderr = b"synthetic-stderr-secret"
    stdout = (json.dumps(event) + "\n").encode()

    class Proxy:
        server_address = ("127.0.0.1", 41001)

        def __init__(self, *args):
            pass

        def serve_forever(self):
            pass

        def shutdown(self):
            pass

        def server_close(self):
            pass

    class Process:
        def __init__(self, args, **kwargs):
            self.returncode = returncode
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO(stdout)
            self.stderr = io.BytesIO(stderr)

        def poll(self):
            return self.returncode

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with pytest.raises(adapter.DispatchError) as exc:
        adapter.dispatch(**prepared_request)
    assert exc.value.code == expected
    evidence = exc.value.evidence
    assert evidence["returncode"] == returncode
    assert evidence["stderr"] == {
        "sha256": hashlib.sha256(stderr).hexdigest(),
        "bytes": len(stderr),
        "complete": True,
    }
    assert evidence["stdout"] == {
        "sha256": hashlib.sha256(stdout).hexdigest(),
        "bytes": len(stdout),
        "complete": True,
    }
    assert evidence["request_count"] is None
    assert evidence["tls_payload_observed"] is False
    assert evidence["raw_text_retained"] is False
    assert "synthetic-" not in json.dumps(evidence)
    recorded = evidence["events"][0]
    if event["type"] == "error":
        assert (recorded["type"], recorded["http_status"], recorded["error_code"]) == (
            "error",
            429,
            "rate_limit_exceeded",
        )
    elif event["type"] == "synthetic-event-secret":
        assert (recorded["type"], recorded["http_status"], recorded["error_code"]) == (
            "other",
            None,
            "other",
        )


def test_runner_records_sanitized_dispatch_failure_evidence(cohort, monkeypatch):
    evidence = {
        "returncode": 9,
        "stderr": {
            "sha256": hashlib.sha256(b"synthetic-secret").hexdigest(),
            "bytes": 16,
            "complete": True,
        },
        "events": [{"type": "error", "http_status": 429}],
        "request_count": None,
        "tls_payload_observed": False,
    }

    def fail(**kwargs):
        raise adapter.DispatchError("process_error", evidence)

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", fail)
    assert pilot.run() is False
    raw = (cohort / "results.json").read_text()
    rows = json.loads(raw)["cases"]
    assert rows[0]["evidence"] == evidence
    assert rows[0]["failure"]["code"] == "process_error"
    assert rows[0]["failure"]["transmission"] == "unknown"
    assert all(row["status"] == "PENDING" for row in rows[1:])
    assert "synthetic-secret" not in raw


def test_response_evaluation_failure_keeps_completed_dispatch_evidence(cohort, monkeypatch):
    evidence = {
        "returncode": 0,
        "events": [{"type": "turn.completed"}],
        "request_count": None,
        "tls_payload_observed": False,
    }

    def malformed_response(**kwargs):
        return {
            "response_text": "not json",
            "tokens": {"input_tokens": 7},
            "tls_payload_observed": False,
            "evidence": evidence,
        }

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", malformed_response)
    assert pilot.run() is True
    raw = (cohort / "results.json").read_text()
    rows = json.loads(raw)["cases"]
    for row in rows:
        assert row["status"] == "FAILED"
        assert row["failure"] == {
            "type": "JSONDecodeError",
            "code": "evaluation_error",
            "transmission": "unknown",
        }
        assert row["evidence"] == evidence
        assert row["tokens"] == {"input_tokens": 7}
        assert row["response_sha256"] == hashlib.sha256(b"not json").hexdigest()
        assert row["response_bytes"] == len(b"not json")
        assert "response_text" not in row
    assert "not json" not in raw
    assert json.loads((cohort / "status.json").read_text())["status"] == "COMPLETED_WITH_FAILURES"


def test_broken_stdin_keeps_sanitized_stderr_and_process_outcome(prepared_request, monkeypatch):
    class Proxy:
        server_address = ("127.0.0.1", 41001)

        def __init__(self, *args):
            pass

        def serve_forever(self):
            pass

        def shutdown(self):
            pass

        def server_close(self):
            pass

    class BrokenInput:
        def write(self, value):
            raise BrokenPipeError("synthetic-secret")

    class Process:
        returncode = 9

        def __init__(self, args, **kwargs):
            self.stdin = BrokenInput()
            self.stdout = io.BytesIO(b"")
            self.stderr = io.BytesIO(b"synthetic-private-stderr")

        def poll(self):
            return self.returncode

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with pytest.raises(adapter.DispatchError) as exc:
        adapter.dispatch(**prepared_request)
    assert exc.value.code == "process_error"
    assert exc.value.evidence["returncode"] == 9
    assert (
        exc.value.evidence["stderr"]["sha256"]
        == hashlib.sha256(b"synthetic-private-stderr").hexdigest()
    )
    assert exc.value.evidence["stderr"]["complete"] is True
    assert "synthetic" not in json.dumps(exc.value.evidence)
