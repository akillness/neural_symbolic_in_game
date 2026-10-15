from __future__ import annotations

import json
import os
import select
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

P = Path(
    "/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026"
)
sys.path.insert(0, str(P))
sys.path.insert(0, str(P / "src"))

from nesy_game.npc_goal import (
    ControllerFailure,
    GoalController,
    IntentInterpreter,
    canonical_config_hash,
    content_hash,
    default_envelope,
)
from scripts.run_npc_service import (
    CAPABILITY_HEADER,
    DEFAULT_ALLOWED_ORIGINS,
    NpcServer,
    ServiceState,
)

POLICY_HASH = "af0a1075294b11630d0828960c8eff6dbeccce5e6f2b414c2b5c1b0a1e405c36"
CAPABILITY = "test-capability"


def observation(**overrides: bool) -> dict[str, bool]:
    result = {
        "lens_reachable": False,
        "lens_carried": False,
        "signal_restored": False,
        "tide_lead_authorized": False,
        "goal_reached": False,
        "in_dialogue": False,
    }
    result.update(overrides)
    return result


def request_envelope(
    request_id: str = "service-request",
    *,
    session_id: str = "service-session",
    session_epoch: int = 0,
    utterance: str = "Where is the lens?",
    event_kind: str = "utterance",
    observation_value: dict[str, bool] | None = None,
    arm: str = "R",
    backend: str = "rule",
) -> dict:
    return default_envelope(
        message_type="request",
        session_id=session_id,
        session_epoch=session_epoch,
        request_id=request_id,
        sequence=-1,
        delivery_index=-1,
        body={
            "event_kind": event_kind,
            "utterance": utterance if event_kind == "utterance" else None,
            "observation": observation_value or observation(lens_reachable=True),
        },
        policy_hash=POLICY_HASH,
        arm=arm,
        backend=backend,
    )


def result_envelope_for(
    source: dict,
    decision: dict,
    *,
    status: str = "APPLIED",
    revision: int | None = None,
    state_hash: str | None = None,
    feedback: str = "applied",
) -> dict:
    step = decision["body"]["steps"][0]
    source_ref = source["state_ref"]
    world_operation = step["operation"] in {"acquire_object", "install_lens", "reveal_hint"}
    result_revision = (
        (
            source_ref["revision"] + 1
            if world_operation and status == "APPLIED"
            else source_ref["revision"]
        )
        if revision is None
        else revision
    )
    result_state = {"revision": result_revision, "sha256": state_hash or ("1" * 64)}
    payload = default_envelope(
        message_type="result",
        session_id=source["session_id"],
        session_epoch=source["session_epoch"],
        request_id=source["request_id"],
        sequence=0,
        delivery_index=0,
        state_ref=result_state,
        body={
            "action_id": step["action_id"],
            "operation": step["operation"],
            "status": status,
            "engine_revision": result_revision,
            "state_ref": result_state,
            "feedback": feedback,
            "observation": observation(lens_reachable=True),
        },
        policy_hash=source["policy_hash"],
        arm="R",
        backend="rule",
    )
    payload["content_sha256"] = content_hash(payload)
    return payload


class CountingInterpreter:
    arm = "R"
    model = None

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.timeouts: list[int | None] = []
        self._rule = IntentInterpreter(arm="R")

    def interpret(self, *, request_id: str, utterance: str, timeout_ms: int | None = None):
        self.calls.append((request_id, utterance))
        self.timeouts.append(timeout_ms)
        return self._rule.interpret(
            request_id=request_id, utterance=utterance, timeout_ms=timeout_ms
        )


class FailingInterpreter:
    arm = "R"
    model = None

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def interpret(self, *, request_id: str, utterance: str, timeout_ms: int | None = None):
        self.calls.append((request_id, utterance))
        raise ControllerFailure("interpreter_failed")


@contextmanager
def running_server(
    *,
    capability: str = CAPABILITY,
    max_workers: int = 1,
    max_inference_calls: int = 8,
    trace_output: Path | None = None,
    interpreter: Any | None = None,
    allowed_origins: frozenset[str] | None = None,
) -> Iterator[tuple[str, ServiceState, Any]]:
    interpreter = CountingInterpreter() if interpreter is None else interpreter
    controller = GoalController(interpreter=interpreter)
    state = ServiceState(
        controller,
        allowed_origins=DEFAULT_ALLOWED_ORIGINS if allowed_origins is None else allowed_origins,
        max_workers=max_workers,
        trace_output=trace_output,
        capability=capability,
        max_inference_calls=max_inference_calls,
        header_timeout=0.25,
        body_timeout=0.25,
    )
    server = NpcServer("127.0.0.1", 0, state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state, interpreter
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def http_request(
    base: str,
    method: str,
    path: str,
    *,
    payload: Any = None,
    headers: dict[str, str] | None = None,
    timeout: float = 2.0,
) -> tuple[int, dict[str, str], Any]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(base + path, data=data, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            return response.status, dict(response.headers), json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        try:
            body = error.read()
        finally:
            error.close()
        return error.code, dict(error.headers), json.loads(body) if body else None


class NpcServiceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        state = ServiceState(
            controller,
            allowed_origins=DEFAULT_ALLOWED_ORIGINS,
            max_workers=1,
            trace_output=None,
            capability=CAPABILITY,
        )
        cls.server = NpcServer("127.0.0.1", 0, state)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)

    def _request(
        self, method: str, path: str, *, payload: dict | None = None, headers: dict | None = None
    ):
        request_headers = dict(headers or {})
        if path in {"/npc/step", "/npc/result"} and CAPABILITY_HEADER not in request_headers:
            request_headers[CAPABILITY_HEADER] = f"Bearer {CAPABILITY}"
        return http_request(self.base, method, path, payload=payload, headers=request_headers)

    def test_health_and_loopback_origin_contract(self) -> None:
        status, headers, payload = self._request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["schema_version"], "npc-goal-recovery/1.1.0")
        self.assertEqual(payload["config_hash"], canonical_config_hash())
        status, _headers, payload = self._request(
            "GET", "/health", headers={"Origin": "https://evil.example"}
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "origin_not_allowed")
        self.assertNotIn("Access-Control-Allow-Origin", headers)

    def test_valid_step_is_typed_decision_with_fixed_goal(self) -> None:
        status, headers, payload = self._request(
            "POST",
            "/npc/step",
            payload=request_envelope(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["message_type"], "decision")
        self.assertEqual(payload["goal_id"], "harbor-signal-restored-authorized-tide-lead-v1")
        self.assertEqual(payload["body"]["steps"][0]["operation"], "acquire_object")
        self.assertEqual(headers["Content-Type"], "application/json")

    def test_service_rejects_wrong_content_type_and_tampered_hash(self) -> None:
        status, _headers, payload = self._request(
            "POST",
            "/npc/step",
            payload=request_envelope("wrong-content"),
            headers={"Content-Type": "text/plain"},
        )
        self.assertEqual(status, 415)
        self.assertEqual(payload["error"], "content_type_must_be_application_json")

        tampered = request_envelope("tampered")
        tampered["content_sha256"] = "0" * 64
        status, _headers, payload = self._request(
            "POST", "/npc/step", payload=tampered, headers={"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "content_hash_mismatch")

    def test_replay_route_validates_order_and_hash_without_model_call(self) -> None:
        record = request_envelope("replay")
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        decision = controller.handle_request(record)
        status, _headers, payload = self._request(
            "POST",
            "/npc/replay",
            payload={"records": [record, decision], "expected_session_id": "service-session"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["valid"], True)
        self.assertEqual(payload["rows"], 2)

        tampered = dict(decision)
        tampered["body"] = dict(decision["body"], status="FAILED")
        tampered["content_sha256"] = content_hash(tampered)
        status, _headers, payload = self._request(
            "POST",
            "/npc/replay",
            payload={"records": [record, tampered], "expected_session_id": "service-session"},
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "replay_plan_semantics_mismatch")


class NpcServiceSecurityIntegrationTests(unittest.TestCase):
    def _headers(
        self,
        *,
        capability: str | None = CAPABILITY,
        origin: str | None = None,
        host: str | None = None,
    ) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if capability is not None:
            headers[CAPABILITY_HEADER] = f"Bearer {capability}"
        if origin is not None:
            headers["Origin"] = origin
        if host is not None:
            headers["Host"] = host
        return headers

    def test_mutating_routes_reject_missing_wrong_capability_host_and_origin_before_inference(
        self,
    ) -> None:
        cases = (
            ("missing capability", self._headers(capability=None), 401, "capability_required"),
            ("wrong capability", self._headers(capability="wrong"), 401, "capability_required"),
            ("wrong host", self._headers(host="attacker.invalid"), 403, "host_not_allowed"),
            (
                "wrong origin",
                self._headers(origin="https://evil.example"),
                403,
                "origin_not_allowed",
            ),
        )
        with running_server() as (base, _state, interpreter):
            for name, headers, expected_status, error_code in cases:
                with self.subTest(name=name):
                    status, _response_headers, payload = http_request(
                        base,
                        "POST",
                        "/npc/step",
                        payload=request_envelope(name.replace(" ", "-")),
                        headers=headers,
                    )
                    self.assertEqual(status, expected_status)
                    self.assertEqual(payload["error"], error_code)
                    self.assertEqual(interpreter.calls, [])

    def test_nonloopback_origin_is_rejected_before_inference(self) -> None:
        with running_server() as (base, _state, interpreter):
            status, _headers, payload = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("nonloopback-origin"),
                headers=self._headers(origin="https://evil.example"),
            )
            self.assertEqual(status, 403)
            self.assertEqual(payload["error"], "origin_not_allowed")
            self.assertEqual(interpreter.calls, [])

    def test_idle_header_deadline_keeps_accepts_bounded(self) -> None:
        with running_server(max_workers=1) as (base, _state, _interpreter):
            parsed = urlsplit(base)
            idle = socket.create_connection((parsed.hostname, parsed.port), timeout=1)
            try:
                rejected = socket.create_connection((parsed.hostname, parsed.port), timeout=1)
                try:
                    rejected.sendall(
                        f"GET /health HTTP/1.1\r\nHost: {parsed.hostname}:{parsed.port}\r\nConnection: close\r\n\r\n".encode()
                    )
                    rejected.settimeout(1)
                    try:
                        self.assertEqual(rejected.recv(1), b"")
                    except (ConnectionResetError, OSError):
                        pass
                finally:
                    rejected.close()

                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline:
                    readable, _writable, _exceptional = select.select([idle], [], [], 0.05)
                    if readable:
                        try:
                            if not idle.recv(1):
                                break
                        except OSError:
                            break
                status, _headers, payload = http_request(base, "GET", "/health", timeout=1)
                self.assertEqual(status, 200)
                self.assertEqual(payload["status"], "ok")
            finally:
                idle.close()

    def test_aggregate_quota_survives_fresh_session_and_epoch(self) -> None:
        with running_server(max_inference_calls=2) as (base, _state, interpreter):
            for index in range(2):
                envelope = request_envelope(
                    f"quota-{index}", session_id=f"session-{index}", session_epoch=index
                )
                envelope["budget"]["intent_deadline_ms"] = 1234
                envelope["content_sha256"] = content_hash(envelope)
                status, _headers, payload = http_request(
                    base,
                    "POST",
                    "/npc/step",
                    payload=envelope,
                    headers=self._headers(),
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["message_type"], "decision")
            status, _headers, payload = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope(
                    "quota-exhausted", session_id="fresh-session", session_epoch=99
                ),
                headers=self._headers(),
            )
            self.assertEqual(payload["body"]["error"], "aggregate_inference_quota_exceeded")
            self.assertEqual(payload["body"]["status"], "REJECTED")
            self.assertEqual(len(interpreter.calls), 2)
            self.assertEqual(interpreter.timeouts, [1234, 1234])

    def test_rejected_validation_stale_conflict_and_cached_requests_do_not_consume_quota(
        self,
    ) -> None:
        with running_server(max_inference_calls=2) as (base, _state, interpreter):
            source = request_envelope("quota-first", session_id="quota-session", session_epoch=0)
            status, _headers, decision = http_request(
                base, "POST", "/npc/step", payload=source, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(interpreter.calls), 1)

            status, _headers, cached = http_request(
                base, "POST", "/npc/step", payload=source, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(cached["content_sha256"], decision["content_sha256"])
            self.assertEqual(len(interpreter.calls), 1)

            newer = request_envelope("quota-new", session_id="quota-session", session_epoch=1)
            status, _headers, _new_decision = http_request(
                base, "POST", "/npc/step", payload=newer, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(len(interpreter.calls), 2)

            status, _headers, payload = http_request(
                base, "POST", "/npc/step", payload=source, headers=self._headers()
            )
            self.assertEqual(status, 400)
            self.assertEqual(payload["error"], "stale_session_epoch")
            self.assertEqual(len(interpreter.calls), 2)

            conflict = result_envelope_for(newer, _new_decision, revision=1, state_hash="1" * 64)
            status, _headers, payload = http_request(
                base, "POST", "/npc/result", payload=conflict, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(payload["body"]["status"], "ACCEPTED")
            conflict["body"] = dict(conflict["body"], status="ERROR")
            conflict["content_sha256"] = content_hash(conflict)
            status, _headers, payload = http_request(
                base, "POST", "/npc/result", payload=conflict, headers=self._headers()
            )
            self.assertEqual(status, 400)
            self.assertEqual(payload["error"], "conflicting_duplicate")
            self.assertEqual(len(interpreter.calls), 2)

    def test_config_and_provenance_rejections_happen_before_interpretation(self) -> None:
        with running_server(max_inference_calls=1) as (base, _state, interpreter):
            cases = (
                (
                    "missing-config",
                    lambda payload: payload.pop("config_hash"),
                    "envelope_keys_must_match_schema",
                ),
                (
                    "config-mismatch",
                    lambda payload: payload.update(
                        {
                            "config_hash": "0" * 64,
                            "content_sha256": content_hash({**payload, "config_hash": "0" * 64}),
                        }
                    ),
                    "config_hash_mismatch",
                ),
                (
                    "provenance-mismatch",
                    lambda payload: payload.update(
                        {
                            "provenance": {**payload["provenance"], "arm": "P", "backend": "codex"},
                            "content_sha256": content_hash(
                                {
                                    **payload,
                                    "provenance": {
                                        **payload["provenance"],
                                        "arm": "P",
                                        "backend": "codex",
                                    },
                                }
                            ),
                        }
                    ),
                    "interpreter_provenance_mismatch",
                ),
            )
            for request_id, mutate, expected_error in cases:
                with self.subTest(request_id=request_id):
                    payload = request_envelope(request_id)
                    mutate(payload)
                    status, _headers, response = http_request(
                        base, "POST", "/npc/step", payload=payload, headers=self._headers()
                    )
                    self.assertEqual(status, 400)
                    self.assertEqual(response["error"], expected_error)
                    self.assertEqual(interpreter.calls, [])

            valid = request_envelope("after-validation")
            status, _headers, response = http_request(
                base, "POST", "/npc/step", payload=valid, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(response["message_type"], "decision")
            status, _headers, response = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("quota-after-valid", session_id="fresh-session"),
                headers=self._headers(),
            )
            self.assertEqual(status, 429)
            self.assertEqual(response["body"]["error"], "aggregate_inference_quota_exceeded")

    def test_failed_interpreter_attempt_consumes_process_quota(self) -> None:
        interpreter = FailingInterpreter()
        with running_server(max_inference_calls=1, interpreter=interpreter) as (
            base,
            _state,
            _interpreter,
        ):
            status, _headers, payload = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("failed-call"),
                headers=self._headers(),
            )
            self.assertEqual(status, 409)
            self.assertEqual(payload["body"]["error"], "interpreter_failed")
            self.assertEqual(len(interpreter.calls), 1)
            status, _headers, payload = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("after-failed-call", session_id="fresh"),
                headers=self._headers(),
            )
            self.assertEqual(status, 429)
            self.assertEqual(payload["body"]["error"], "aggregate_inference_quota_exceeded")

    def test_observation_only_replan_does_not_consume_inference_quota(self) -> None:
        with running_server(max_inference_calls=1) as (base, _state, interpreter):
            source = request_envelope("utterance", session_id="observe-session")
            status, _headers, first = http_request(
                base, "POST", "/npc/step", payload=source, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(first["body"]["steps"][0]["operation"], "acquire_object")
            observation_request = request_envelope(
                "observation",
                session_id="observe-session",
                event_kind="observation",
                observation_value=observation(lens_carried=True),
            )
            status, _headers, replanned = http_request(
                base, "POST", "/npc/step", payload=observation_request, headers=self._headers()
            )
            self.assertEqual(status, 200)
            self.assertEqual(replanned["body"]["steps"][0]["operation"], "install_lens")
            self.assertEqual(len(interpreter.calls), 1)

    def test_canonical_default_origin_8877_accepts_options_and_post_8767_rejects(self) -> None:
        with running_server() as (base, _state, interpreter):
            accepted_origin = "http://127.0.0.1:8877"
            rejected_origin = "http://127.0.0.1:8767"
            status, headers, payload = http_request(
                base, "OPTIONS", "/npc/step", headers={"Origin": accepted_origin}
            )
            self.assertEqual(status, 204)
            self.assertIsNone(payload)
            self.assertEqual(headers["Access-Control-Allow-Origin"], accepted_origin)

            status, headers, payload = http_request(
                base, "OPTIONS", "/npc/step", headers={"Origin": rejected_origin}
            )
            self.assertEqual(status, 403)
            self.assertEqual(payload["error"], "origin_not_allowed")
            self.assertNotIn("Access-Control-Allow-Origin", headers)

            status, headers, payload = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("origin-accepted"),
                headers=self._headers(origin=accepted_origin),
            )
            self.assertEqual(status, 200)
            self.assertEqual(payload["message_type"], "decision")
            self.assertEqual(headers["Access-Control-Allow-Origin"], accepted_origin)

            status, _headers, payload = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("origin-rejected"),
                headers=self._headers(origin=rejected_origin),
            )
            self.assertEqual(status, 403)
            self.assertEqual(payload["error"], "origin_not_allowed")
            self.assertEqual(len(interpreter.calls), 1)

    def test_partial_body_deadline_releases_bounded_worker_slot(self) -> None:
        with running_server(max_workers=1) as (base, _state, _interpreter):
            parsed = urlsplit(base)
            partial = socket.create_connection((parsed.hostname, parsed.port), timeout=1)
            try:
                partial.sendall(
                    b"POST /npc/step HTTP/1.1\r\n"
                    + f"Host: {parsed.hostname}:{parsed.port}\r\n".encode()
                    + f"Content-Type: application/json\r\n{CAPABILITY_HEADER}: Bearer {CAPABILITY}\r\n".encode()
                    + b"Content-Length: 100\r\nConnection: close\r\n\r\n{}"
                )
                try:
                    status, _headers, payload = http_request(
                        base,
                        "POST",
                        "/npc/step",
                        payload=request_envelope("blocked"),
                        headers=self._headers(),
                        timeout=1,
                    )
                except (ConnectionResetError, TimeoutError, urllib.error.URLError):
                    status, payload = 0, {}
                self.assertIn(status, {0, 429})
                if status == 429:
                    self.assertEqual(payload["error"], "worker_limit_exceeded")

                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline:
                    readable, _writable, _exceptional = select.select([partial], [], [], 0.05)
                    if readable:
                        try:
                            if not partial.recv(1):
                                break
                        except OSError:
                            break
                status, _headers, payload = http_request(
                    base,
                    "POST",
                    "/npc/step",
                    payload=request_envelope("after-timeout"),
                    headers=self._headers(),
                    timeout=1,
                )
                self.assertEqual(status, 200)
                self.assertEqual(payload["message_type"], "decision")
            finally:
                partial.close()

    def test_malformed_payloads_are_controlled_and_health_survives(self) -> None:
        malformed: list[tuple[str, dict, str]] = []
        message_type = request_envelope("array-message-type")
        message_type["message_type"] = []
        message_type["content_sha256"] = content_hash(message_type)
        malformed.append(("message type array", message_type, "invalid_payload"))

        nested = request_envelope("deep-json")
        value: Any = "x"
        for _ in range(35):
            value = [value]
        nested["body"]["utterance"] = value
        nested["content_sha256"] = content_hash(nested)
        malformed.append(("deep nesting", nested, "json_nesting_too_deep"))

        boolean_revision = request_envelope("bool-revision")
        boolean_revision["state_ref"]["revision"] = True
        boolean_revision["content_sha256"] = content_hash(boolean_revision)
        malformed.append(("boolean revision", boolean_revision, "invalid_state_revision"))

        with running_server() as (base, _state, interpreter):
            for name, payload, expected_error in malformed:
                with self.subTest(name=name):
                    status, _headers, response = http_request(
                        base, "POST", "/npc/step", payload=payload, headers=self._headers()
                    )
                    self.assertEqual(status, 400)
                    self.assertEqual(response["error"], expected_error)
                    self.assertEqual(interpreter.calls, [])
                    health_status, _health_headers, health = http_request(base, "GET", "/health")
                    self.assertEqual(health_status, 200)
                    self.assertEqual(health["status"], "ok")

            status, _headers, response = http_request(
                base,
                "POST",
                "/npc/replay",
                payload={"records": [1], "expected_session_id": "service-session"},
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(status, 400)
            self.assertEqual(response["error"], "invalid_replay_payload")
            health_status, _health_headers, health = http_request(base, "GET", "/health")
            self.assertEqual(health_status, 200)
            self.assertEqual(health["status"], "ok")
            self.assertEqual(interpreter.calls, [])

    def test_model_target_array_is_rejected_without_health_loss(self) -> None:
        def bad_runner(**kwargs: Any) -> tuple[int, dict[str, Any]]:
            return 0, {
                "request_id": kwargs["request_id"],
                "typed_intent": {"label": "REQUEST_DISCLOSURE", "claims": [], "target": []},
            }

        interpreter = IntentInterpreter(arm="P", prompt_runner=bad_runner)
        with running_server(interpreter=interpreter) as (base, _state, _interpreter):
            status, _headers, response = http_request(
                base,
                "POST",
                "/npc/step",
                payload=request_envelope("bad-target", arm="P", backend="codex"),
                headers=self._headers(),
            )
            self.assertEqual(status, 400)
            self.assertEqual(response["error"], "invalid_intent_target")
            health_status, _health_headers, health = http_request(base, "GET", "/health")
            self.assertEqual(health_status, 200)
            self.assertEqual(health["status"], "ok")

    def test_cli_rule_backend_starts_health_and_shuts_down(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        environment = os.environ.copy()
        environment["TRACE_RPG_NPC_CAPABILITY"] = CAPABILITY
        process = subprocess.Popen(
            [
                sys.executable,
                str(P / "scripts" / "run_npc_service.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--backend",
                "rule",
            ],
            cwd=P,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            deadline = time.monotonic() + 5
            while True:
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    self.fail(
                        f"service exited before health: rc={process.returncode}, stdout={stdout!r}, stderr={stderr!r}"
                    )
                try:
                    status, _headers, payload = http_request(
                        f"http://127.0.0.1:{port}", "GET", "/health", timeout=0.5
                    )
                except (urllib.error.URLError, TimeoutError, ConnectionError):
                    if time.monotonic() >= deadline:
                        self.fail("rule backend CLI did not become healthy within 5 seconds")
                    time.sleep(0.05)
                    continue
                self.assertEqual(status, 200)
                self.assertEqual(payload["status"], "ok")
                break
            process.terminate()
            return_code = process.wait(timeout=3)
            process.communicate(timeout=1)
            self.assertEqual(return_code, 0)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)
            process.communicate(timeout=1)

    def test_client_accounting_is_null_and_raw_utterance_is_not_exposed(self) -> None:
        utterance = "raw utterance canary 8f0f7a"
        with tempfile.TemporaryDirectory() as directory:
            trace_path = Path(directory) / "trace.jsonl"
            with running_server(trace_output=trace_path) as (base, _state, _interpreter):
                payload = request_envelope("redaction", utterance=utterance)
                payload["budget"].update({"input_tokens": 123, "output_tokens": 456, "cost": 7.89})
                payload["content_sha256"] = content_hash(payload)
                status, _headers, response = http_request(
                    base, "POST", "/npc/step", payload=payload, headers=self._headers()
                )
                self.assertEqual(status, 200)
                self.assertIsNone(response["budget"]["input_tokens"])
                self.assertIsNone(response["budget"]["output_tokens"])
                self.assertIsNone(response["budget"]["cost"])
                self.assertNotIn(utterance, json.dumps(response, ensure_ascii=False))
            trace_text = trace_path.read_text(encoding="utf-8")
            self.assertNotIn(utterance, trace_text)


if __name__ == "__main__":
    unittest.main()
