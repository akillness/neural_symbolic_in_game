#!/usr/bin/env python3
"""Synthetic-only Codex sandbox and CONNECT proxy probe; never uses real credentials."""

import base64
import datetime
import hashlib
import http.server
import json
import os
import re
import secrets
import select
import shutil
import socket
import socketserver
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

SYNTHETIC_PROMPT = b"Reply with exactly: synthetic-ok"
EXPECTED_SHA256 = "030316ecfbb41f4e7946e584b0063ef333b7a36cd312ba349f2f6869e39b62cc"
DISABLED = (
    "shell_tool",
    "shell_snapshot",
    "unified_exec",
    "browser_use",
    "browser_use_external",
    "browser_use_full_cdp_access",
    "computer_use",
    "apps",
    "enable_mcp_apps",
    "mcp_2026_07_28",
    "tool_call_mcp_elicitation",
    "tool_suggest",
    "skill_search",
    "skill_mcp_dependency_install",
    "image_generation",
    "view_image",
    "in_app_browser",
    "code_mode_host",
    "plugins",
    "hooks",
    "multi_agent",
    "code_mode",
)

# Captured twice from the pinned binary using this exact synthetic profile.
DEVELOPER_SHA256 = (
    "d57793bc3719706a807d7adb21db20cce80e7984d7c1263b788b0c82c443f78c",
    "9143ec699df6d6308a8f7f430a1bb94d85da02ba9788ba6eac80bbe9c7cfbefa",
    "810438cc2dac75dcbca3286e1f362e4ea60e62089bd31093dc889a3f8b889514",
)
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def is_uuid(value):
    return isinstance(value, str) and UUID_RE.fullmatch(value) is not None


def valid_metadata(metadata, cache_key, now=None, model="gpt-5.6-luna", oauth=False):
    expected_keys = {
        "x-codex-window-id",
        "x-codex-turn-metadata",
        "root_turn_id",
        "thread_id",
        "session_id",
        "x-codex-installation-id",
        "turn_id",
    }
    if oauth:
        expected_keys |= {"guardian_credits_requested", "mcp_attribution"}
    if not isinstance(metadata, dict) or set(metadata) != expected_keys or not is_uuid(cache_key):
        return False
    serialized = metadata["x-codex-turn-metadata"]
    if not isinstance(serialized, str) or len(serialized) > 2048:
        return False
    info = json.loads(serialized, object_pairs_hook=unique_pairs)
    if not isinstance(info, dict):
        return False
    ids = (
        "installation_id",
        "session_id",
        "thread_id",
        "turn_id",
        "root_turn_id",
        "context_window_id",
    )
    if any(not is_uuid(info.get(key)) for key in ids):
        return False
    expected = {
        **{key: info[key] for key in ids},
        "agent_name": "/root",
        "window_id": cache_key + ":0",
        "window_number": 0,
        "request_kind": "turn",
        "history_initialization": "new",
        "thread_source": "user",
        "turn_trigger": "exec",
        "sandbox": "seatbelt",
        "sandbox_mode": "read-only",
        "auto_review_enabled": False,
        "node_repl_auto_review_required": False,
        "node_repl_disabled": False,
        "turn_started_at_unix_ms": info.get("turn_started_at_unix_ms"),
        "analytics_enabled": False,
        "model": model,
        "reasoning_effort": "medium",
    }
    timestamp = info.get("turn_started_at_unix_ms")
    if (
        type(timestamp) is not int
        or abs(timestamp - int((time.time() if now is None else now) * 1000)) > 120000
    ):
        return False
    return (
        json.dumps(info, sort_keys=True) == json.dumps(expected, sort_keys=True)
        and info["session_id"] == info["thread_id"] == cache_key
        and info["root_turn_id"] == info["turn_id"]
        and metadata
        == {
            "x-codex-window-id": cache_key + ":0",
            "x-codex-turn-metadata": serialized,
            "root_turn_id": info["root_turn_id"],
            "thread_id": info["thread_id"],
            "session_id": info["session_id"],
            "x-codex-installation-id": info["installation_id"],
            "turn_id": info["turn_id"],
            **(
                {"guardian_credits_requested": "true", "mcp_attribution": '{"status":"none"}'}
                if oauth
                else {}
            ),
        }
    )


def checked_prompt(prompt: bytes) -> bytes:
    if prompt != SYNTHETIC_PROMPT:
        raise ValueError("unaudited prompt")
    return prompt


def connect_authority(line: bytes, expected: str) -> bool:
    return line == ("CONNECT " + expected + " HTTP/1.1").encode("ascii")


def sandbox_profile(scratch: Path, executable: Path, proxy_port: int) -> str:
    scratch, executable = scratch.resolve(strict=True), executable.resolve(strict=True)
    if not 1 <= proxy_port <= 65535:
        raise ValueError("invalid port")
    # SBPL strings are quoted by JSON, avoiding profile injection through paths.
    q = lambda path: json.dumps(str(path), ensure_ascii=True)
    ancestors = {Path("/var"), Path("/etc")}
    ancestors.update(
        p for root in (scratch, executable.parent) for p in (root, *root.parents) if str(p) != "/"
    )
    metadata = " ".join("(literal " + q(p) + ")" for p in sorted(ancestors))
    return (
        f"(version 1)(allow default)(deny network-outbound)"
        f'(allow network-outbound (remote ip "localhost:{proxy_port}"))'
        f"(deny file-read*)(deny file-write*)"
        f'(allow file-read* (literal "/") (subpath "/System") (subpath "/usr/lib") '
        f'(subpath "/usr/share") (subpath "/dev") (subpath {q(scratch)}) (literal {q(executable)}))'
        f"(allow file-write* (subpath {q(scratch)}))"
        f"(deny process-exec)(allow process-exec (literal {q(executable)}))"
        f"(allow file-read-metadata {metadata})"
    )


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = False
    daemon_threads = True


class ProxyHandler(socketserver.BaseRequestHandler):
    def handle(self):
        self.request.settimeout(3)
        try:
            header = b""
            while b"\r\n\r\n" not in header and len(header) < 8192:
                chunk = self.request.recv(1)
                if not chunk:
                    return
                header += chunk
            lines = header.split(b"\r\n")
            first = lines[0]
            hosts = [
                line.split(b":", 1)[1].strip()
                for line in lines[1:]
                if b":" in line and line.split(b":", 1)[0].lower() == b"host"
            ]
            authorities = getattr(self.server, "authorities", (self.server.authority,))
            target = next(
                (authority for authority in authorities if connect_authority(first, authority)),
                None,
            )
            if (
                not header.endswith(b"\r\n\r\n")
                or target is None
                or len(hosts) != 1
                or hosts[0] != target.encode("ascii")
            ):
                target_ok = target is not None
                host_ok = (
                    target is not None and len(hosts) == 1 and hosts[0] == target.encode("ascii")
                )
                known = next(
                    (
                        host
                        for host in ("ab.chatgpt.com:443", "chatgpt.com:443", "api.openai.com:443")
                        if connect_authority(first, host)
                    ),
                    "other",
                )
                self.server.failure = f"CONNECT rejected: destination={known}, target_ok={target_ok}, host_ok={host_ok}"
                self.server.violation.set()
                self.request.sendall(b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n")
                return
            with socket.create_connection(
                ("127.0.0.1", self.server.fixture_port), timeout=3
            ) as upstream:
                self.request.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                sockets = (self.request, upstream)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    readable, _, _ = select.select(sockets, [], [], 0.2)
                    for source in readable:
                        data = source.recv(65536)
                        if not data:
                            return
                        (upstream if source is self.request else self.request).sendall(data)
                self.server.failure = "proxy tunnel timed out"
                self.server.violation.set()
        except ConnectionResetError:
            # The client may close a rejected WebSocket tunnel before HTTP fallback.
            return
        except (OSError, ValueError) as exc:
            self.server.failure = (
                f"proxy I/O failure: {type(exc).__name__}, errno={getattr(exc, 'errno', None)}"
            )
            self.server.violation.set()


class FixtureHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    @staticmethod
    def validate_request(
        body: bytes,
        sentinel: str,
        cwd: str,
        developer_hashes: tuple,
        now=None,
        model="gpt-5.6-luna",
        prompt=SYNTHETIC_PROMPT,
        oauth=False,
    ) -> bool:
        try:
            data = json.loads(body, object_pairs_hook=unique_pairs)
            if (
                not isinstance(data, dict)
                or not sentinel
                or sentinel in json.dumps(data, ensure_ascii=False)
            ):
                return False
            expected = {
                "model": model,
                "stream": True,
                "tool_choice": "auto",
                "parallel_tool_calls": False,
                "reasoning": {"effort": "medium", "context": "all_turns"},
                "store": False,
                "include": ["reasoning.encrypted_content"],
                "text": {"verbosity": "low"},
            }
            if set(data) != set(expected) | {"input", "prompt_cache_key", "client_metadata"}:
                return False
            if any(
                data[key] != value or type(data[key]) is not type(value)
                for key, value in expected.items()
            ):
                return False
            if not valid_metadata(
                data["client_metadata"], data["prompt_cache_key"], now, model, oauth
            ):
                return False
            items = data["input"]
            if not isinstance(items, list) or len(items) != len(developer_hashes) + 2 or not cwd:
                return False
            turn_info = (
                json.loads(
                    data["client_metadata"]["x-codex-turn-metadata"], object_pairs_hook=unique_pairs
                )
                if oauth
                else None
            )
            for index, item in enumerate(items):
                if not isinstance(item, dict):
                    return False
                prefix = "at_" if index == 0 else "msg_"
                item_id = item.get("id")
                if (
                    not isinstance(item_id, str)
                    or not item_id.startswith(prefix)
                    or not is_uuid(item_id[len(prefix) :])
                ):
                    return False
                if oauth and index > 0:
                    meta = item.get("internal_chat_message_metadata_passthrough")
                    if (
                        not isinstance(meta, dict)
                        or set(meta)
                        != {"content_item_kinds", "content_item_metadata", "turn_id", "create_time"}
                        or meta["turn_id"] != data["client_metadata"]["turn_id"]
                        or type(meta["create_time"]) not in (int, float)
                        or not abs(
                            meta["create_time"] - turn_info["turn_started_at_unix_ms"] / 1000
                        )
                        <= 60
                    ):
                        return False
                    if index >= len(developer_hashes):
                        kind = (
                            "environments.environment_context"
                            if index == len(developer_hashes)
                            else "user.text"
                        )
                        source = (
                            {"type": "harness", "hook": False}
                            if index == len(developer_hashes)
                            else {"type": "user"}
                        )
                        if meta["content_item_kinds"] != [kind] or meta[
                            "content_item_metadata"
                        ] != [{"provenance": source}]:
                            return False
                if index < len(developer_hashes):
                    fixed = {key: value for key, value in item.items() if key != "id"}
                    if oauth and index > 0:
                        fixed["internal_chat_message_metadata_passthrough"] = {
                            **fixed["internal_chat_message_metadata_passthrough"],
                            "turn_id": "<DYNAMIC>",
                            "create_time": "<DYNAMIC>",
                        }
                    encoded = json.dumps(
                        fixed, sort_keys=True, separators=(",", ":"), ensure_ascii=True
                    )
                    if oauth:
                        encoded = encoded.replace(cwd, "<CWD>").replace(
                            str(Path(cwd).parent), "<SCRATCH>"
                        )
                    encoded = encoded.encode()
                    if hashlib.sha256(encoded).hexdigest() != developer_hashes[index]:
                        return False
            date = (
                datetime.datetime.fromtimestamp(time.time() if now is None else now, datetime.UTC)
                .date()
                .isoformat()
            )
            environment = (
                "<environment_context>\n  <cwd>" + cwd + "</cwd>\n  <shell>sh</shell>\n"
                "  <current_date>" + date + "</current_date>\n  <timezone>GMT</timezone>\n"
                "  <filesystem><workspace_roots><root>" + cwd + "</root></workspace_roots>"
                '<permission_profile type="managed"><file_system type="restricted">'
                '<entry access="read"><special>:root</special></entry></file_system>'
                "</permission_profile></filesystem>\n</environment_context>"
            )
            expected_users = (
                {
                    "type": "message",
                    "id": items[-2]["id"],
                    "role": "user",
                    "content": [{"type": "input_text", "text": environment}],
                },
                {
                    "type": "message",
                    "id": items[-1]["id"],
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt.decode()}],
                },
            )
            return all(
                {
                    k: v
                    for k, v in item.items()
                    if not (oauth and k == "internal_chat_message_metadata_passthrough")
                }
                == expected
                for item, expected in zip(items[-2:], expected_users)
            )
        except (ValueError, TypeError, UnicodeError, KeyError, IndexError):
            return False

    @staticmethod
    def audited_request(body: bytes, sentinel: str, cwd: str = "") -> bool:
        return FixtureHandler.validate_request(body, sentinel, cwd, DEVELOPER_SHA256)

    @staticmethod
    def mutation_controls(body: bytes, cwd: str) -> bool:
        # Operate only on the in-memory, local synthetic request; never persist it.
        original = json.loads(body, object_pairs_hook=unique_pairs)
        variants = []
        for index in range(5):
            changed = json.loads(body, object_pairs_hook=unique_pairs)
            if index == 0:
                changed["input"][0]["tools"][0]["description"] += " injected"
            else:
                changed["input"][index]["content"][0]["text"] += " injected"
            variants.append(json.dumps(changed).encode())
        changed = json.loads(body, object_pairs_hook=unique_pairs)
        changed["client_metadata"]["unexpected"] = "injected"
        variants.append(json.dumps(changed).encode())
        variants.append(b'{"model":"gpt-5.6-luna",' + body.lstrip()[1:])
        if not all(
            not FixtureHandler.audited_request(item, "absent-control", cwd) for item in variants
        ):
            return False
        # The positive-control string exists only through JSON escape sequences.
        escaped = body.replace(b"synthetic-ok", b"\\u0073ynthetic-ok")
        return (
            escaped != body
            and b"synthetic-ok" not in escaped
            and not FixtureHandler.audited_request(escaped, "synthetic-ok", cwd)
            and original["input"][4]["content"][0]["text"] == SYNTHETIC_PROMPT.decode()
        )

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.path != "/v1/responses" or not 0 < length <= 1024 * 1024:
                raise ValueError("unexpected request")
            body = self.rfile.read(length)
            if not self.audited_request(body, self.server.sentinel, self.server.cwd):
                raise ValueError("request contract rejected")
            if not self.mutation_controls(body, self.server.cwd):
                raise ValueError("request mutation controls failed")
            with self.server.post_lock:
                if self.server.posts:
                    raise ValueError("duplicate request")
                self.server.posts += 1
                self.server.sentinel_controls_passed = True
            response = {
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "gpt-5.6-luna",
                "output": [
                    {
                        "id": "msg_synthetic",
                        "type": "message",
                        "role": "assistant",
                        "status": "completed",
                        "content": [
                            {"type": "output_text", "text": "synthetic-ok", "annotations": []}
                        ],
                    }
                ],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }
            events = [
                (
                    "response.created",
                    {"response": {**response, "status": "in_progress", "output": []}},
                ),
                ("response.output_item.done", {"output_index": 0, "item": response["output"][0]}),
                ("response.completed", {"response": response}),
            ]
            payload = b"".join(
                (
                    "event: " + name + "\ndata: " + json.dumps({"type": name, **value}) + "\n\n"
                ).encode()
                for name, value in events
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (ValueError, OSError) as exc:
            self.server.failure = str(exc) if isinstance(exc, ValueError) else "fixture I/O failure"
            self.server.violation.set()
            self.close_connection = True


def run_synthetic() -> dict:
    if sys.platform != "darwin":
        raise RuntimeError("macOS sandbox-exec required")
    found = shutil.which("codex")
    if not found:
        raise RuntimeError("Codex executable unavailable")
    executable = Path(found).resolve(strict=True)
    if hashlib.sha256(executable.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Codex executable differs from audited build")
    sandbox = Path("/usr/bin/sandbox-exec")
    openssl = shutil.which("openssl")
    if not sandbox.is_file() or not openssl:
        raise RuntimeError("sandbox-exec or openssl unavailable")
    with (
        tempfile.TemporaryDirectory(prefix="codex-isolation-") as tmp,
        tempfile.TemporaryDirectory(prefix="codex-canary-") as private,
    ):
        root = Path(tmp).resolve()
        os.chmod(root, 0o700)
        sentinel = secrets.token_hex(32)
        (Path(private) / "sentinel").write_text(sentinel, encoding="ascii")
        for name in ("home", "codex", "cwd"):
            (root / name).mkdir(mode=0o700)
        cert, key = root / "cert.pem", root / "key.pem"
        subprocess.run(
            [
                openssl,
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost",
                "-addext",
                "basicConstraints=critical,CA:FALSE",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            check=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
        violation = threading.Event()
        fixture = ThreadedServer(("127.0.0.1", 0), FixtureHandler)
        fixture.posts, fixture.violation = 0, violation
        fixture.sentinel = sentinel
        fixture.cwd = str(root / "cwd")
        fixture.post_lock = threading.Lock()
        fixture.sentinel_controls_passed = False
        fixture.failure = None
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        fixture.socket = context.wrap_socket(fixture.socket, server_side=True)
        proxy = ThreadedServer(("127.0.0.1", 0), ProxyHandler)
        proxy.fixture_port = fixture.server_address[1]
        proxy.authority = f"localhost:{proxy.fixture_port}"
        proxy.violation = violation
        threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (fixture, proxy)]
        for thread in threads:
            thread.start()
        try:
            proxy_url = f"http://127.0.0.1:{proxy.server_address[1]}"
            env = {
                "HOME": str(root / "home"),
                "CODEX_HOME": str(root / "codex"),
                "PATH": "/usr/bin:/bin",
                "TMPDIR": str(root),
                "FAKE_API_KEY": "synthetic-key",
                "HTTP_PROXY": proxy_url,
                "http_proxy": proxy_url,
                "HTTPS_PROXY": proxy_url,
                "https_proxy": proxy_url,
                "NO_PROXY": "",
                "no_proxy": "",
                "SSL_CERT_FILE": str(cert),
                "OTEL_SDK_DISABLED": "true",
                "TZ": "UTC",
            }
            args = [
                str(sandbox),
                "-p",
                sandbox_profile(root, executable, proxy.server_address[1]),
                str(executable),
                "exec",
                "--strict-config",
                "-c",
                "skills.bundled.enabled=false",
            ]
            args += ["-c", "suppress_unstable_features_warning=true"]
            args += [
                "-c",
                "analytics.enabled=false",
                "-c",
                'otel.exporter="none"',
                "-c",
                'otel.metrics_exporter="none"',
            ]
            for feature in DISABLED:
                args += ["--disable", feature]
            args += [
                "--enable",
                "omit_skill_descriptions",
                "--enable",
                "skip_host_skill_discovery",
                "-c",
                'web_search="disabled"',
                "-c",
                'model_provider="fake"',
                "-c",
                'model_providers.fake.name="Synthetic"',
                "-c",
                f'model_providers.fake.base_url="https://localhost:{proxy.fixture_port}/v1"',
                "-c",
                'model_providers.fake.env_key="FAKE_API_KEY"',
                "-c",
                'model_providers.fake.wire_api="responses"',
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
                "gpt-5.6-luna",
                "-C",
                str(root / "cwd"),
                "-",
            ]
            proc = subprocess.Popen(
                args,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            proc.stdin.write(checked_prompt(SYNTHETIC_PROMPT))
            proc.stdin.close()
            done = threading.Event()
            events = []

            def consume():
                try:
                    for line in proc.stdout:
                        if len(line) > 65536 or len(events) >= 100:
                            violation.set()
                            break
                        event = json.loads(line)
                        events.append(event)
                        item = event.get("item", {})
                        if (
                            event.get("type") == "item.completed"
                            and item.get("type") == "error"
                            and item.get("message")
                            == "Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`."
                            and fixture.posts == 0
                        ):
                            continue
                        if event.get("type") not in {
                            "thread.started",
                            "turn.started",
                            "item.completed",
                            "turn.completed",
                        }:
                            violation.set()
                            break
                        if (
                            event.get("type") == "item.completed"
                            and event.get("item", {}).get("type") != "agent_message"
                        ):
                            violation.set()
                            break
                except (ValueError, OSError):
                    violation.set()
                finally:
                    done.set()

            reader = threading.Thread(target=consume, daemon=True)
            reader.start()
            deadline = time.monotonic() + 20
            while proc.poll() is None and not violation.is_set() and time.monotonic() < deadline:
                time.sleep(0.02)
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=3)
            reader.join(timeout=3)
            if (
                violation.is_set()
                or not done.is_set()
                or proc.returncode != 0
                or fixture.posts != 1
                or not fixture.sentinel_controls_passed
                or not any(e.get("type") == "turn.completed" for e in events)
                or [
                    e.get("item", {}).get("text")
                    for e in events
                    if e.get("type") == "item.completed"
                    and e.get("item", {}).get("type") == "agent_message"
                ]
                != ["synthetic-ok"]
            ):
                raise RuntimeError(
                    "synthetic sandbox request failed: "
                    f"returncode={proc.returncode}, posts={fixture.posts}, "
                    f"violation={violation.is_set()}, fixture={fixture.failure or 'none'}"
                )
            return {
                "synthetic_transport_only": True,
                "posts": fixture.posts,
                "sentinel_absent_and_positive_control_rejected": True,
            }
        finally:
            for server in (proxy, fixture):
                server.shutdown()
                server.server_close()


OAUTH_SYNTHETIC_HASHES = {
    "gpt-5.6-luna": (
        "d57793bc3719706a807d7adb21db20cce80e7984d7c1263b788b0c82c443f78c",
        "d317a29aa89f8858ff31389a29e39e4478b03afb1aff51bde825bb3a4de393fe",
        "2a2199d9724699cb8f78d5a85a89e64ba62ec7a93307e47272657a969aaa4140",
    ),
    "gpt-5.6-terra": (
        "8ded5df1a03ad8b15b9e6bc394d022929453fdead3dc5f7d30b5039d91a8aa84",
        "d317a29aa89f8858ff31389a29e39e4478b03afb1aff51bde825bb3a4de393fe",
        "aae997748533edb2de7163f6e7da9bc7ab5a323225af54b3851d4946e83f0f22",
        "3d0a3917e4b0f766f9df1d894bb16b41d85f9976d24388d13416a273e17489aa",
        "ca75f5252edd56ca5bacc130307f2b3838160088ca3b090a82ceecb5c6bc97e5",
    ),
}


class OAuthFixtureHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_args):
        pass

    def respond(self, code, payload, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def admitted_path(self):
        path = self.path.split("?", 1)[0]
        allowed = {
            "/api/codex/accounts/check",
            "/api/codex/settings/user",
            "/backend-api/codex/responses",
            "/backend-api/codex/models",
        }
        expected_target = (
            path + "?client_version=0.167.0" if path == "/backend-api/codex/models" else path
        )
        method_ok = self.command == "GET" or (
            self.command == "POST" and path == "/backend-api/codex/responses"
        )
        leaked = self.server.sentinel in self.path or any(
            self.server.sentinel in value for _, value in self.headers.items()
        )
        if (
            self.server.violation.is_set()
            or leaked
            or path not in allowed
            or self.path != expected_target
            or not method_ok
            or self.headers.get("Authorization") != "Bearer synthetic-access"
        ):
            if not self.server.violation.is_set():
                self.server.failure = (
                    "fixture rejected: path="
                    + (path if path in allowed else "other")
                    + ", synthetic_auth="
                    + str(self.headers.get("Authorization") == "Bearer synthetic-access")
                )
            self.server.violation.set()
            return None
        with self.server.lock:
            key = self.command + " " + path
            self.server.counts[key] = self.server.counts.get(key, 0) + 1
        return path

    def do_GET(self):
        path = self.admitted_path()
        if path is None:
            self.respond(403, b"", "text/plain")
            return
        if path == "/backend-api/codex/models":
            self.respond(200, b'{"models":[]}', "application/json")
            return
        payload = json.dumps(
            {
                "accounts": [
                    {
                        "id": "synthetic-account",
                        "workspace_backend_origin": "NO_CONSTRAINT",
                        "account_routing_override": "NO_CONSTRAINT",
                    }
                ]
            }
        ).encode()
        self.respond(200, payload, "application/json")

    def mutation_controls(self, body):
        variants = []
        for control in ("sentinel", "settings", "tools", "developer", "metadata"):
            data = json.loads(body, object_pairs_hook=unique_pairs)
            if control == "sentinel":
                data["input"][-1]["content"][0]["text"] = self.server.sentinel
            elif control == "settings":
                data["store"] = True
            elif control == "tools":
                data["tools"] = [{"type": "function", "name": "synthetic"}]
            elif control == "developer":
                data["input"][1]["content"][0]["text"] += " injected"
            else:
                data["input"][-1]["internal_chat_message_metadata_passthrough"]["turn_id"] = (
                    "invalid"
                )
            variants.append(json.dumps(data).encode())
        return all(
            not FixtureHandler.validate_request(
                variant,
                self.server.sentinel,
                self.server.cwd,
                OAUTH_SYNTHETIC_HASHES[self.server.model],
                model=self.server.model,
                prompt=self.server.prompt,
                oauth=True,
            )
            for variant in variants
        )

    def do_POST(self):
        try:
            if self.admitted_path() != "/backend-api/codex/responses":
                raise ValueError("unexpected path or synthetic authorization")
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 1048576 or self.headers.get("Content-Encoding") != "zstd":
                raise ValueError("unexpected compressed payload")
            compressed = self.rfile.read(length)
            decoded = subprocess.run(
                [self.server.zstd, "-d", "-c"],
                input=compressed,
                capture_output=True,
                check=True,
                timeout=10,
            ).stdout
            if (
                len(decoded) > 1048576
                or any(s in decoded for s in (b"synthetic-access", b"synthetic-refresh"))
                or not FixtureHandler.validate_request(
                    decoded,
                    self.server.sentinel,
                    self.server.cwd,
                    OAUTH_SYNTHETIC_HASHES[self.server.model],
                    model=self.server.model,
                    prompt=self.server.prompt,
                    oauth=True,
                )
            ):
                raise ValueError("OAuth request contract rejected")
            if not self.mutation_controls(decoded):
                raise ValueError("OAuth mutation controls failed")
            with self.server.lock:
                if self.server.posts:
                    raise ValueError("duplicate responses request")
                self.server.posts += 1
                self.server.mutation_controls_passed = True
            response = {
                "id": "resp_synthetic",
                "created_at": 1,
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2},
            }
            item = {
                "id": "msg_synthetic",
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": "synthetic-ok", "annotations": []}],
            }
            events = [
                ("response.created", {"response": {**response, "status": "in_progress"}}),
                ("response.output_item.done", {"item": item}),
                ("response.completed", {"response": response}),
            ]
            payload = b"".join(
                (
                    "event: " + name + "\ndata: " + json.dumps({"type": name, **value}) + "\n\n"
                ).encode()
                for name, value in events
            )
            self.respond(200, payload, "text/event-stream")
        except (ValueError, OSError, subprocess.SubprocessError):
            self.server.failure = "synthetic OAuth request rejected"
            self.server.violation.set()
            self.close_connection = True


def run_oauth_synthetic(prompt: bytes, prompt_sha256: str, model: str, timeout: int = 45) -> dict:
    """Exercise reviewed synthetic input against localhost only; never use real credentials."""
    if (
        prompt != b"Return OK."
        or hashlib.sha256(prompt).hexdigest() != prompt_sha256
        or model not in OAUTH_SYNTHETIC_HASHES
        or type(timeout) is not int
        or not 1 <= timeout <= 120
    ):
        raise ValueError("invalid synthetic input")
    prompt.decode("utf-8")
    found, openssl, zstd = shutil.which("codex"), shutil.which("openssl"), shutil.which("zstd")
    if sys.platform != "darwin" or not found or not openssl or not zstd:
        raise RuntimeError("synthetic OAuth prerequisites unavailable")
    executable = Path(found).resolve(strict=True)
    if hashlib.sha256(executable.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Codex executable differs from audited build")
    with (
        tempfile.TemporaryDirectory(prefix="codex-oauth-") as tmp,
        tempfile.TemporaryDirectory(prefix="codex-canary-") as private,
    ):
        root = Path(tmp).resolve()
        os.chmod(root, 0o700)
        sentinel = secrets.token_hex(32)
        (Path(private) / "sentinel").write_text(sentinel, encoding="ascii")
        for name in ("home", "codex", "cwd"):
            (root / name).mkdir(mode=0o700)
        piece = lambda value: (
            base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )
        jwt = (
            piece({"alg": "none", "typ": "JWT"})
            + "."
            + piece(
                {
                    "sub": "synthetic-user",
                    "exp": 4102444800,
                    "https://api.openai.com/auth": {
                        "chatgpt_account_id": "synthetic-account",
                        "chatgpt_plan_type": "plus",
                    },
                }
            )
            + ".synthetic"
        )
        (root / "codex" / "auth.json").write_text(
            json.dumps(
                {
                    "OPENAI_API_KEY": None,
                    "tokens": {
                        "id_token": jwt,
                        "access_token": "synthetic-access",
                        "refresh_token": "synthetic-refresh",
                        "account_id": "synthetic-account",
                    },
                    "last_refresh": datetime.datetime.now(datetime.UTC).isoformat(),
                }
            ),
            encoding="utf-8",
        )
        cert, key = root / "cert.pem", root / "key.pem"
        subprocess.run(
            [
                openssl,
                "req",
                "-x509",
                "-newkey",
                "rsa:2048",
                "-nodes",
                "-days",
                "1",
                "-subj",
                "/CN=localhost",
                "-addext",
                "subjectAltName=DNS:localhost,DNS:chatgpt.com",
                "-addext",
                "basicConstraints=critical,CA:FALSE",
                "-keyout",
                str(key),
                "-out",
                str(cert),
            ],
            check=True,
            timeout=10,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        violation = threading.Event()
        fixture = ThreadedServer(("127.0.0.1", 0), OAuthFixtureHandler)
        fixture.lock, fixture.counts, fixture.posts, fixture.failure = threading.Lock(), {}, 0, None
        fixture.mutation_controls_passed = False
        fixture.zstd, fixture.sentinel, fixture.cwd, fixture.model, fixture.prompt = (
            zstd,
            sentinel,
            str(root / "cwd"),
            model,
            prompt,
        )
        fixture.violation = violation
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        fixture.socket = tls.wrap_socket(fixture.socket, server_side=True)
        proxy = ThreadedServer(("127.0.0.1", 0), ProxyHandler)
        proxy.fixture_port, proxy.authority, proxy.violation = (
            fixture.server_address[1],
            f"localhost:{fixture.server_address[1]}",
            violation,
        )
        # Both names terminate at the local fixture, never at a remote host.
        proxy.authorities = (proxy.authority, "chatgpt.com:443")
        proxy.failure = None
        for server in (fixture, proxy):
            threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            proxy_url = f"http://127.0.0.1:{proxy.server_address[1]}"
            env = {
                "HOME": str(root / "home"),
                "CODEX_HOME": str(root / "codex"),
                "TMPDIR": str(root),
                "PATH": "/usr/bin:/bin",
                "SSL_CERT_FILE": str(cert),
                "OTEL_SDK_DISABLED": "true",
                "TZ": "UTC",
                "HTTP_PROXY": proxy_url,
                "http_proxy": proxy_url,
                "HTTPS_PROXY": proxy_url,
                "https_proxy": proxy_url,
                "NO_PROXY": "",
                "no_proxy": "",
            }
            profile = sandbox_profile(root, executable, proxy.server_address[1])
            cat_profile = (
                profile
                + '(allow file-read* (literal "/bin/cat"))(allow process-exec (literal "/bin/cat"))'
            )
            canary_check = subprocess.run(
                [
                    "/usr/bin/sandbox-exec",
                    "-p",
                    cat_profile,
                    "/bin/cat",
                    str(Path(private) / "sentinel"),
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            cat_allowed = subprocess.run(
                ["/usr/bin/sandbox-exec", "-p", cat_profile, "/bin/cat", "/dev/null"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            exec_profile = profile + '(allow file-read* (literal "/usr/bin/true"))'
            exec_check = subprocess.run(
                ["/usr/bin/sandbox-exec", "-p", exec_profile, "/usr/bin/true"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            exec_allowed = subprocess.run(
                [
                    "/usr/bin/sandbox-exec",
                    "-p",
                    exec_profile + '(allow process-exec (literal "/usr/bin/true"))',
                    "/usr/bin/true",
                ],
                capture_output=True,
                timeout=5,
                check=False,
            )
            canary_read_denied = (
                cat_allowed.returncode == 0
                and canary_check.returncode != 0
                and not canary_check.stdout
            )
            process_exec_denied = exec_allowed.returncode == 0 and exec_check.returncode != 0
            if not canary_read_denied or not process_exec_denied:
                raise RuntimeError("synthetic sandbox control failed")
            args = ["/usr/bin/sandbox-exec", "-p", profile, str(executable), "exec"]
            for feature in DISABLED:
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
                    f'chatgpt_base_url="https://localhost:{fixture.server_address[1]}"',
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
            started = time.time()
            proc = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=root / "cwd",
                close_fds=True,
            )
            proc.stdin.write(prompt)
            proc.stdin.close()
            events = []
            reader_failure = []
            categories = []
            error_signatures = []
            responses = []

            def consume():
                try:
                    for line in proc.stdout:
                        if len(line) > 65536 or len(events) >= 100:
                            reader_failure.append("event limit exceeded")
                            violation.set()
                            break
                        event = json.loads(line)
                        events.append(event.get("type", "unknown"))
                        kind = event.get("type")
                        item = event.get("item", {})
                        if kind == "error" or (
                            kind == "item.completed" and item.get("type") == "error"
                        ):
                            message = (
                                event.get("message", "")
                                if kind == "error"
                                else item.get("message", "")
                            )
                            if not isinstance(message, str):
                                raise ValueError("invalid error event")
                            normalized = re.sub(
                                r"(?<![A-Za-z0-9])(?:/private)?/var/folders/[^\s,;\)]+",
                                "<SCRATCH>",
                                message,
                            )
                            normalized = re.sub(r"localhost:\d+", "localhost:<PORT>", normalized)
                            normalized = re.sub(
                                r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b",
                                "<UUID>",
                                normalized,
                            )
                            error_signatures.append(
                                (kind, hashlib.sha256(normalized.encode()).hexdigest())
                            )
                            categories.append("classified_synthetic_warning")
                        elif kind == "item.completed" and item.get("type") == "agent_message":
                            responses.append(item.get("text") == "synthetic-ok")
                        elif kind == "item.completed":
                            categories.append("unexpected_item")
                except (ValueError, OSError, AttributeError) as exc:
                    reader_failure.append("event read failure: " + type(exc).__name__)
                    violation.set()

            reader = threading.Thread(target=consume, daemon=True)
            reader.start()
            deadline = time.monotonic() + timeout
            while proc.poll() is None and not violation.is_set() and time.monotonic() < deadline:
                time.sleep(0.02)
            timed_out = proc.poll() is None and not violation.is_set()
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=3)
            reader.join(timeout=3)
            expected_errors = [
                (
                    "item.completed",
                    "f81dc692c1f8f292887098fbf7061cd77f7c481714c4230f131c98a423bed2d5",
                ),
                (
                    "item.completed",
                    "098e801ebc95c9c7312a945849442846324dcf639365a297313248993822711b",
                ),
                ("error", "0b4ff975d144bf7cfebc3637e8d9e540109ab64fa1569950a176dc932c986f2c"),
                ("error", "4d8533b3a8e0a5fd71efe35f26a7b1a45bcb9240bd0cd82da31e0fcc4c3dc806"),
                ("error", "19de350ca02937269c9d61da0ce47313277a092a88ac4623d6724ff3ec968c21"),
                ("error", "a9672c70c738169d464238d19e0fc5f7600ea43e70a063de0972ef1c96658191"),
                (
                    "item.completed",
                    "bf956822fae6d027a7bf2743543c6b2701c4bfb6b7f1ed8cbe20c4a7fcedb4b6",
                ),
            ]
            succeeded = (
                proc.returncode == 0
                and not timed_out
                and not violation.is_set()
                and not reader.is_alive()
                and not reader_failure
                and fixture.posts == 1
                and fixture.mutation_controls_passed
                and responses == [True]
                and events.count("turn.completed") == 1
                and error_signatures == expected_errors
                and "unexpected_item" not in categories
            )
            return {
                "synthetic_only": True,
                "provider_request": False,
                "selector": model,
                "passed": succeeded,
                "started_at": started,
                "ended_at": time.time(),
                "returncode": proc.returncode,
                "timed_out": timed_out,
                "event_types": events,
                "request_counts": dict(fixture.counts),
                "posts_accepted": fixture.posts,
                "canary_read_denied": canary_read_denied,
                "process_exec_denied": process_exec_denied,
                "mutation_controls_passed": fixture.mutation_controls_passed,
                "assistant_output_matched": responses == [True],
                "error_categories": (
                    ["startup_config_warning", "startup_disabled_feature_warning"]
                    + ["websocket_http_200_fallback"] * 5
                    if error_signatures == expected_errors
                    else ["unclassified_or_incomplete"]
                ),
                "violation": violation.is_set(),
                "failure": fixture.failure
                or proxy.failure
                or (reader_failure[0] if reader_failure else None),
            }
        finally:
            for server in (proxy, fixture):
                server.shutdown()
                server.server_close()


def main() -> int:
    if sys.argv[1:] != ["--self-test"]:
        print("Only --self-test is supported; real provider access is disabled.", file=sys.stderr)
        return 2
    try:
        print(json.dumps(run_synthetic()))
        return 0
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"Synthetic isolation self-test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
