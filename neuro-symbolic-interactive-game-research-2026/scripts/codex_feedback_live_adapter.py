#!/usr/bin/env python3
"""Bounded native Codex transport. TLS payloads cannot be inspected by this proxy."""

from __future__ import annotations

import hashlib
import json
import os
import select
import socket
import socketserver
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import codex_isolation_wrapper as isolation

ALLOWED_AUTHORITIES = frozenset({"chatgpt.com:443", "auth.openai.com:443"})

_ERROR_CLASSIFICATIONS = {
    "authentication_error": "auth",
    "rate_limit_exceeded": "rate_limit",
    "invalid_request_error": "invalid_request",
    "server_error": "server",
    "context_length_exceeded": "context_length",
    "unsupported_model": "unsupported_model",
    "model_not_supported": "unsupported_model",
    "model_not_found": "model_unavailable",
    "invalid_api_key": "auth",
    "token_expired": "auth",
    "insufficient_quota": "quota",
    "usage_limit_reached": "quota",
    "transport_error": "transport",
    "connection_error": "transport",
    "sandbox_error": "sandbox",
}
_ERROR_MESSAGES = {
    "Your access token has expired. Please sign in again.": "auth",
    "Your authentication token has been invalidated. Please try signing in again.": "auth",
    "Authentication required. Please run 'codex login'.": "auth",
    "You exceeded your current quota, please check your plan and billing details.": "quota",
    "You've hit your usage limit.": "quota",
    "Rate limit reached.": "rate_limit",
    "Too many requests.": "rate_limit",
    (
        "Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; "
        "enable `features.code_mode_host` and install `codex-code-mode-host`."
    ): "startup_disabled_feature_warning",
}


def _classify_error(
    code: object,
    message: object,
    status_code: object = None,
    *,
    model: str,
    config_path: Path | None = None,
) -> str:
    """Classify error events only; never return provider text or infer from keywords."""
    if isinstance(code, str) and code in _ERROR_CLASSIFICATIONS:
        return _ERROR_CLASSIFICATIONS[code]
    if type(status_code) is int:
        if status_code == 401:
            return "auth"
        if status_code == 429:
            return "rate_limit"
    if isinstance(message, str):
        message = message.strip()
        # Only the already-validated dispatch selector may match this signature.
        if (
            message
            == f"The '{model}' model is not supported when using Codex with a ChatGPT account."
        ):
            return "unsupported_model"
        if config_path is not None and message == (
            "Under-development features enabled: omit_skill_descriptions, skip_host_skill_discovery. "
            "Under-development features are incomplete and may behave unpredictably. "
            "To suppress this warning, set `suppress_unstable_features_warning = true` in "
            f"{config_path}."
        ):
            return "startup_config_warning"
        return _ERROR_MESSAGES.get(message, "unknown")
    return "unknown"


class DispatchError(RuntimeError):
    def __init__(self, code, evidence=None):
        super().__init__(code)
        self.code = code
        self.transmission = "unknown"
        self.evidence = evidence


def snapshot_executable(binary: bytes, directory: Path) -> Path:
    if hashlib.sha256(binary).hexdigest() != isolation.EXPECTED_SHA256:
        raise RuntimeError("native Codex build is not the audited binary")
    directory = directory.resolve(strict=True)
    os.chmod(directory, 0o700)
    target = directory / "codex"
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o500)
    with os.fdopen(fd, "wb") as stream:
        stream.write(binary)
    if hashlib.sha256(target.read_bytes()).hexdigest() != isolation.EXPECTED_SHA256:
        raise RuntimeError("native Codex snapshot differs from the audited binary")
    return target


class _Proxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True
    allow_reuse_address = False


class _Connect(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(5)
        try:
            header = bytearray()
            while not header.endswith(b"\r\n\r\n") and len(header) < 8192:
                data = self.request.recv(1)
                if not data:
                    raise ValueError("incomplete CONNECT")
                header.extend(data)
            lines = bytes(header).split(b"\r\n")
            hosts = [
                line.split(b":", 1)[1].strip()
                for line in lines[1:]
                if b":" in line and line.split(b":", 1)[0].lower() == b"host"
            ]
            target = next(
                (
                    name
                    for name in ALLOWED_AUTHORITIES
                    if isolation.connect_authority(lines[0], name)
                ),
                None,
            )
            if (
                not header.endswith(b"\r\n\r\n")
                or target is None
                or hosts != [target.encode("ascii")]
            ):
                raise ValueError("CONNECT destination rejected")
            with socket.create_connection((target.rsplit(":", 1)[0], 443), timeout=5) as upstream:
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                while not self.server.stop.is_set():
                    readable, _, _ = select.select((self.request, upstream), (), (), 0.2)
                    for source in readable:
                        chunk = source.recv(65536)
                        if not chunk:
                            return
                        (upstream if source is self.request else self.request).sendall(chunk)
        except ValueError:
            self.server.failure = "isolation_violation"
            self.server.violation.set()
        except OSError:
            self.server.failure = "transport_error"
            self.server.violation.set()


def _verify_prompt(prompt, prompt_sha256, model, case_id, condition):
    import codex_feedback_pilot as pilot

    if (
        model not in pilot.MODELS
        or condition not in pilot.CONDITIONS
        or not isinstance(prompt, bytes)
    ):
        raise ValueError("unapproved request assignment")
    cases = {name: (state, action) for name, state, action in pilot.pilot_cases()}
    if case_id not in cases:
        raise ValueError("unapproved fixture")
    state, action = cases[case_id]
    proposal = pilot.to_jsonable(action)
    signal = (
        pilot.to_jsonable(pilot.validate_candidate(state, action))
        if condition == "detailed"
        else {"valid": False, "message": "Action rejected."}
    )
    expected = pilot.build_prompt(case_id, proposal, signal, state).encode("utf-8")
    if prompt != expected or hashlib.sha256(prompt).hexdigest() != prompt_sha256:
        raise ValueError("prompt does not match the approved fixture assignment")


def dispatch(
    *,
    prompt: bytes,
    prompt_sha256: str,
    model: str,
    identity: dict,
    auth_file: Path,
    case_id: str,
    condition: str,
    approval: dict,
    timeout: int = 120,
) -> dict:
    """Dispatch one reviewed fixture under a strict OS profile and CONNECT allowlist.

    The proxy sees only TLS destination, not requests or response contents. Actual
    served model and cost therefore remain unverified. Token refresh may fail
    because the original authentication file is mounted read-only.
    """
    expected_approval = {
        "model": model,
        "case_id": case_id,
        "condition": condition,
        "prompt_sha256": prompt_sha256,
        "identity": identity,
    }
    if (
        not isinstance(approval, dict)
        or {k: approval.get(k) for k in expected_approval} != expected_approval
    ):
        raise ValueError("reviewed assignment does not match dispatch")
    result_hash = approval.get("results_sha256")
    if (
        not isinstance(result_hash, str)
        or len(result_hash) != 64
        or any(c not in "0123456789abcdef" for c in result_hash)
    ):
        raise ValueError("reviewed results digest is missing")
    try:
        path = Path(approval["results_path"]).absolute()
        if path.name != "approved_results.json" or path.resolve(strict=True) != path:
            raise ValueError("invalid reviewed results path")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            reviewed = stream.read(4 * 1024 * 1024 + 1)
        if len(reviewed) > 4 * 1024 * 1024 or hashlib.sha256(reviewed).hexdigest() != result_hash:
            raise ValueError("reviewed results digest mismatch")
        document = json.loads(reviewed, object_pairs_hook=isolation.unique_pairs)
        metadata = document["metadata"]
        matching = [
            row
            for row in document["cases"]
            if row.get("case_id") == case_id and row.get("condition") == condition
        ]
        if (
            metadata.get("pilot_protocol") != "model-separated-v2"
            or metadata.get("model_selector") != model
            or any(metadata.get(key) != value for key, value in identity.items())
            or len(matching) != 1
            or matching[0].get("prompt_sha256") != prompt_sha256
            or matching[0].get("status") != "PENDING"
        ):
            raise ValueError("reviewed results assignment mismatch")
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("reviewed results unavailable or invalid") from exc
    _verify_prompt(prompt, prompt_sha256, model, case_id, condition)
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise ValueError("invalid timeout")
    executable = Path(identity["codex_executable"]).resolve(strict=True)
    binary = executable.read_bytes()
    digest = hashlib.sha256(binary).hexdigest()
    if digest != identity.get("codex_executable_sha256") or digest != isolation.EXPECTED_SHA256:
        raise RuntimeError("native Codex build is not the audited binary")
    if not identity.get("codex_version"):
        raise RuntimeError("native Codex version was not bound")
    auth = Path(auth_file).resolve(strict=True)
    if not auth.is_file():
        raise RuntimeError("authentication file unavailable")
    if not Path("/usr/bin/sandbox-exec").is_file():
        raise RuntimeError("macOS sandbox-exec required")

    with (
        tempfile.TemporaryDirectory(prefix="codex-live-") as directory,
        tempfile.TemporaryDirectory(prefix="codex-native-") as native_dir,
    ):
        executable = snapshot_executable(binary, Path(native_dir))
        root = Path(directory).resolve()
        os.chmod(root, 0o700)
        for name in ("home", "codex", "cwd"):
            (root / name).mkdir(mode=0o700)
        (root / "codex" / "auth.json").symlink_to(auth)
        proxy = _Proxy(("127.0.0.1", 0), _Connect)
        proxy.stop = threading.Event()
        proxy.failure = None
        proxy.violation = threading.Event()
        thread = threading.Thread(target=proxy.serve_forever, daemon=True)
        thread.start()
        proc = None
        try:
            port = proxy.server_address[1]
            profile = isolation.sandbox_profile(root, executable, port)
            profile += (
                "(allow file-read* (literal " + json.dumps(str(auth), ensure_ascii=True) + "))"
            )
            parents = " ".join(
                "(literal " + json.dumps(str(p), ensure_ascii=True) + ")"
                for p in auth.parents
                if str(p) != "/"
            )
            profile += "(allow file-read-metadata " + parents + ")"
            proxy_url = f"http://127.0.0.1:{port}"
            env = {
                "HOME": str(root / "home"),
                "CODEX_HOME": str(root / "codex"),
                "TMPDIR": str(root),
                "PATH": "/usr/bin:/bin",
                "TZ": "UTC",
                "OTEL_SDK_DISABLED": "true",
                "HTTP_PROXY": proxy_url,
                "http_proxy": proxy_url,
                "HTTPS_PROXY": proxy_url,
                "https_proxy": proxy_url,
                "NO_PROXY": "",
                "no_proxy": "",
            }
            args = ["/usr/bin/sandbox-exec", "-p", profile, str(executable), "exec"]
            for feature in isolation.DISABLED:
                args.extend(("--disable", feature))
            args.extend(
                [
                    "--enable",
                    "omit_skill_descriptions",
                    "--enable",
                    "skip_host_skill_discovery",
                    "-c",
                    "skills.bundled.enabled=false",
                    "-c",
                    "analytics.enabled=false",
                    "-c",
                    'otel.metrics_exporter="none"',
                    "-c",
                    'otel.exporter="none"',
                    "-c",
                    'web_search="disabled"',
                    "-c",
                    'cli_auth_credentials_store="file"',
                    "--ephemeral",
                    "--sandbox",
                    "read-only",
                    "--skip-git-repo-check",
                    "--ignore-user-config",
                    "--ignore-rules",
                    "--json",
                    "--color",
                    "never",
                    "--model",
                    model,
                    "-C",
                    str(root / "cwd"),
                    "-",
                ]
            )
            started = time.monotonic()
            try:
                proc = subprocess.Popen(
                    args,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=root / "cwd",
                    env=env,
                    close_fds=True,
                    start_new_session=True,
                )
            except OSError:
                raise DispatchError("process_error") from None
            response, usage, complete, provider_failed, error, events = (
                [],
                [],
                threading.Event(),
                threading.Event(),
                [],
                [],
            )
            streams = {
                name: {"hasher": hashlib.sha256(), "bytes": 0, "complete": False}
                for name in ("stdout", "stderr")
            }

            def record_chunk(name, chunk):
                state = streams[name]
                state["bytes"] += len(chunk)
                if state["bytes"] > 10 * 1024 * 1024:
                    error.append("output limit")
                    return False
                state["hasher"].update(chunk)
                return True

            def consume():
                startup_phase = "awaiting_thread"
                turn_started = False
                try:
                    while True:
                        line = proc.stdout.readline(65537)
                        if not line:
                            streams["stdout"]["complete"] = True
                            break
                        if not record_chunk("stdout", line):
                            break
                        if error:
                            continue
                        if len(line) > 65536 or len(events) >= 1000:
                            raise ValueError("event limit")
                        event = json.loads(line)
                        kind = event.get("type")
                        item = event.get("item")
                        item_type = item.get("type") if isinstance(item, dict) else None
                        container = (
                            item if kind == "item.completed" and item_type == "error" else event
                        )
                        detail = (
                            container.get("error")
                            if isinstance(container.get("error"), dict)
                            else container
                        )
                        status_code = container.get("status_code", detail.get("status_code"))
                        if type(status_code) is not int or not 100 <= status_code <= 599:
                            status_code = None
                        raw_code = container.get("code", detail.get("code"))
                        allowed_codes = (
                            "rate_limit_exceeded",
                            "invalid_request_error",
                            "authentication_error",
                            "server_error",
                            "context_length_exceeded",
                        )
                        code = (
                            raw_code
                            if raw_code in allowed_codes
                            else ("other" if raw_code is not None else None)
                        )
                        events.append(
                            {
                                "type": kind
                                if kind
                                in (
                                    "thread.started",
                                    "turn.started",
                                    "turn.completed",
                                    "item.completed",
                                    "error",
                                )
                                else "other",
                                "item_type": item_type
                                if item_type in ("agent_message", "error")
                                else ("other" if item_type is not None else None),
                                "http_status": status_code,
                                "error_code": code,
                                "elapsed_seconds": round(time.monotonic() - started, 3),
                            }
                        )
                        if kind == "error" or (kind == "item.completed" and item_type == "error"):
                            nested = container.get("error")
                            message = (
                                container.get("message")
                                if "message" in container
                                else (nested.get("message") if isinstance(nested, dict) else None)
                            )
                            try:
                                message_hash = (
                                    hashlib.sha256(message.encode("utf-8")).hexdigest()
                                    if isinstance(message, str)
                                    else None
                                )
                            except UnicodeEncodeError:
                                message_hash = None
                            events[-1]["error_message_sha256"] = message_hash
                            structured_code = (
                                container.get("code")
                                if "code" in container
                                else (nested.get("code") if isinstance(nested, dict) else None)
                            )
                            events[-1]["error_classification"] = _classify_error(
                                structured_code,
                                message,
                                status_code,
                                model=model,
                                config_path=root / "codex" / "config.toml",
                            )
                            expected_warning = (
                                "startup_config_warning"
                                if startup_phase == "awaiting_config_warning"
                                else "startup_disabled_feature_warning"
                                if startup_phase == "awaiting_disabled_warning"
                                else None
                            )
                            # Codex 0.167.0 emits these local warnings as ErrorItem, not ThreadEvent::Error.
                            if (
                                kind == "item.completed"
                                and expected_warning is not None
                                and events[-1]["error_classification"] == expected_warning
                                and isinstance(message, str)
                                and message == message.strip()
                                and event.get("error") is None
                                and container.get("error") is None
                                and all(
                                    part.get(key) is None
                                    for part in (event, container, detail)
                                    for key in ("code", "status_code")
                                )
                            ):
                                startup_phase = (
                                    "awaiting_disabled_warning"
                                    if startup_phase == "awaiting_config_warning"
                                    else "awaiting_turn"
                                )
                                continue
                            provider_failed.set()
                        elif startup_phase == "awaiting_disabled_warning":
                            provider_failed.set()
                            raise ValueError("incomplete startup warnings")
                        if kind == "item.completed" and item_type == "agent_message":
                            if startup_phase == "closed":
                                raise ValueError("response after completed turn")
                            if startup_phase == "awaiting_turn":
                                raise ValueError("missing turn start")
                            startup_phase = "running"
                            text = item.get("text")
                            if not isinstance(text, str) or len(text.encode("utf-8")) > 65536:
                                raise ValueError("invalid response")
                            response.append(text)
                        elif kind == "turn.completed":
                            if startup_phase == "awaiting_turn":
                                raise ValueError("missing turn start")
                            startup_phase = "closed"
                            reported_usage = event.get("usage")
                            usage.append(
                                {
                                    key: reported_usage[key]
                                    for key in (
                                        "input_tokens",
                                        "cached_input_tokens",
                                        "output_tokens",
                                        "total_tokens",
                                    )
                                    if type(reported_usage.get(key)) is int
                                    and 0 <= reported_usage[key] < 2**63
                                }
                                if isinstance(reported_usage, dict)
                                else None
                            )
                            complete.set()
                        elif kind == "error" or (kind == "item.completed" and item_type == "error"):
                            continue
                        elif kind == "thread.started":
                            if startup_phase != "awaiting_thread":
                                raise ValueError("unexpected thread start")
                            startup_phase = "awaiting_config_warning"
                        elif kind == "turn.started":
                            if turn_started or startup_phase in ("running", "closed"):
                                raise ValueError("unexpected turn start")
                            turn_started = True
                            startup_phase = "running"
                        else:
                            raise ValueError("unexpected event")
                except (ValueError, TypeError, AttributeError, OSError):
                    error.append("invalid or unexpected Codex event")
                    try:
                        while True:
                            chunk = proc.stdout.read(65536)
                            if not chunk:
                                streams["stdout"]["complete"] = True
                                break
                            if not record_chunk("stdout", chunk):
                                break
                    except OSError:
                        pass
                if startup_phase == "awaiting_disabled_warning":
                    provider_failed.set()

            def consume_stderr():
                try:
                    while True:
                        chunk = proc.stderr.read(65536)
                        if not chunk:
                            streams["stderr"]["complete"] = True
                            break
                        if not record_chunk("stderr", chunk):
                            break
                except OSError:
                    error.append("stderr read failure")

            reader = threading.Thread(target=consume, daemon=True)
            stderr_reader = threading.Thread(target=consume_stderr, daemon=True)
            reader.start()
            stderr_reader.start()
            stdin_error = False
            try:
                proc.stdin.write(prompt)
                proc.stdin.close()
            except OSError:
                stdin_error = True
                error.append("stdin write failure")
            deadline = started + timeout
            while (
                proc.poll() is None
                and not error
                and not provider_failed.is_set()
                and not proxy.violation.is_set()
                and time.monotonic() < deadline
            ):
                time.sleep(0.02)
            reason = None
            if proc.poll() is None:
                reason = proxy.failure or (
                    "process_error"
                    if stdin_error
                    else "provider_error"
                    if provider_failed.is_set()
                    else "protocol_error"
                    if error
                    else "timeout"
                )
                proc.kill()
                proc.wait(timeout=3)
            reader.join(timeout=3)
            stderr_reader.join(timeout=3)
            evidence = {
                "returncode": proc.returncode,
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "events": events,
                "request_count": None,
                "tls_payload_observed": False,
                "raw_text_retained": False,
                "raw_text_omission_reason": "may contain credentials or sensitive server data",
            }
            for name, state in streams.items():
                evidence[name] = {
                    "sha256": state["hasher"].hexdigest() if state["complete"] else None,
                    "bytes": state["bytes"],
                    "complete": state["complete"],
                }
            if reason:
                raise DispatchError(reason, evidence)
            if proxy.violation.is_set():
                raise DispatchError(proxy.failure or "isolation_violation", evidence)
            if stdin_error:
                raise DispatchError("process_error", evidence)
            if provider_failed.is_set():
                raise DispatchError("provider_error", evidence)
            if reader.is_alive() or stderr_reader.is_alive() or error:
                raise DispatchError("protocol_error", evidence)
            if proc.returncode != 0:
                raise DispatchError("process_error", evidence)
            if not complete.is_set() or len(response) != 1 or len(usage) != 1:
                raise DispatchError("protocol_error", evidence)
            return {
                "response_text": response[0],
                "tokens": usage[0],
                "actual_model_identity": None,
                "cost_usd": None,
                "tls_payload_observed": False,
                "evidence": evidence,
            }
        finally:
            if proc is not None and proc.poll() is None:
                proc.kill()
                proc.wait(timeout=3)
            proxy.stop.set()
            proxy.shutdown()
            proxy.server_close()
            thread.join(timeout=3)
