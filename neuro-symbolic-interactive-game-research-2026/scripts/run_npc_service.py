#!/usr/bin/env python3
"""Run the fixed-goal NPC interpreter/planner over a bounded loopback HTTP service.

Examples:
  python scripts/run_npc_service.py --backend codex --model gpt-5
  python scripts/run_npc_service.py --backend rule --trace-output /tmp/npc-trace.jsonl

The Codex backend is explicit and fail-closed.  Rule/reference arms are research controls,
never hidden fallbacks.  Godot owns all canonical world writes; /npc/result only acknowledges
an engine outcome and invalidates stale Python plans.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import signal
import socket
import sys
import threading
from collections.abc import Mapping
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nesy_game.npc_goal import (
    SCHEMA_VERSION,
    BudgetExceeded,
    ControllerFailure,
    GoalController,
    IntentInterpreter,
    ProtocolError,
    ReplayValidator,
    content_hash,
    validate_envelope,
)

MAX_JSON_DEPTH = 32
MAX_INFERENCE_CALLS = 8
HEADER_TIMEOUT_SECONDS = 5.0
BODY_TIMEOUT_SECONDS = 5.0
CAPABILITY_HEADER = "X-NPC-Capability"
CANONICAL_CONFIG_PATH = PROJECT_ROOT / "configs" / "npc-goal-recovery.json"


def _validate_loopback_origin(origin: Any) -> str:
    if not isinstance(origin, str):
        raise ProtocolError("canonical_origin_must_be_string")
    parsed = urlsplit(origin)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("canonical_origin_invalid_port") from exc
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or port is None
        or not 1 <= port <= 65535
        or origin != f"http://{parsed.hostname}:{port}"
    ):
        raise ValueError("canonical_origin_must_be_exact_loopback_http")
    return origin


def _load_canonical_transport() -> dict[str, Any]:
    try:
        config_bytes = CANONICAL_CONFIG_PATH.read_bytes()
        config = json.loads(config_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("canonical_transport_config_unavailable") from exc
    if not isinstance(config, dict) or config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("canonical_transport_config_schema_mismatch")
    transport = config.get("transport")
    if not isinstance(transport, dict):
        raise ProtocolError("canonical_transport_config_invalid")
    bind = transport.get("bind")
    port = transport.get("port")
    if (
        bind not in {"127.0.0.1", "localhost"}
        or isinstance(port, bool)
        or not isinstance(port, int)
        or not 1 <= port <= 65535
    ):
        raise ValueError("canonical_transport_config_invalid")
    expected_paths = {
        "step_path": "/npc/step",
        "result_path": "/npc/result",
        "health_path": "/health",
    }
    if any(transport.get(key) != value for key, value in expected_paths.items()):
        raise ValueError("canonical_transport_config_route_mismatch")
    body_limit = transport.get("body_limit_bytes")
    if isinstance(body_limit, bool) or not isinstance(body_limit, int) or body_limit < 1:
        raise ValueError("canonical_transport_config_body_limit_invalid")
    raw_origins = transport.get("default_allowed_origins")
    if not isinstance(raw_origins, list) or not raw_origins:
        raise ValueError("canonical_transport_config_origins_invalid")
    origins = frozenset(_validate_loopback_origin(origin) for origin in raw_origins)
    if len(origins) != len(raw_origins):
        raise ValueError("canonical_transport_config_origins_duplicate")
    return {
        "bind": bind,
        "port": port,
        "body_limit": body_limit,
        "origins": origins,
        "config_hash": hashlib.sha256(config_bytes).hexdigest(),
    }


_CANONICAL_TRANSPORT = _load_canonical_transport()
BODY_LIMIT = _CANONICAL_TRANSPORT["body_limit"]
DEFAULT_SERVICE_HOST = _CANONICAL_TRANSPORT["bind"]
DEFAULT_SERVICE_PORT = _CANONICAL_TRANSPORT["port"]
DEFAULT_ALLOWED_ORIGINS = _CANONICAL_TRANSPORT["origins"]
CANONICAL_CONFIG_HASH = _CANONICAL_TRANSPORT["config_hash"]
_INTEGER_FIELDS = ("session_epoch", "sequence", "delivery_index")
_BUDGET_INTEGER_FIELDS = (
    "intent_deadline_ms",
    "episode_deadline_ms",
    "max_intent_calls",
    "max_action_attempts",
    "max_replans",
    "max_plan_expansions",
    "max_inflight_per_session",
)


def _json_depth_within_limit(value: Any, limit: int = MAX_JSON_DEPTH) -> bool:
    pending: list[tuple[Any, int]] = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        if depth > limit:
            return False
        if isinstance(current, dict):
            pending.extend((item, depth + 1) for item in current.values())
        elif isinstance(current, list):
            pending.extend((item, depth + 1) for item in current)
    return True


def _prepare_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProtocolError("payload_must_be_object")
    if "message_type" in payload and not isinstance(payload["message_type"], str):
        raise ProtocolError("invalid_payload")
    for key in _INTEGER_FIELDS:
        if isinstance(payload.get(key), bool):
            raise ProtocolError(f"invalid_{key}")
    state_ref = payload.get("state_ref")
    if isinstance(state_ref, dict) and isinstance(state_ref.get("revision"), bool):
        raise ProtocolError("invalid_state_revision")
    budget = payload.get("budget")
    if isinstance(budget, dict):
        for key in _BUDGET_INTEGER_FIELDS:
            if isinstance(budget.get(key), bool):
                raise ProtocolError(f"invalid_budget_{key}")
        if any(budget.get(key) is not None for key in ("input_tokens", "output_tokens", "cost")):
            safe = dict(payload)
            safe_budget = dict(budget)
            for key in ("input_tokens", "output_tokens", "cost"):
                safe_budget[key] = None
            safe["budget"] = safe_budget
            safe["content_sha256"] = content_hash(safe)
            return safe
    return payload


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"invalid_json_constant:{value}")


class ServiceState:
    def __init__(
        self,
        controller: GoalController,
        *,
        allowed_origins: frozenset[str],
        max_workers: int,
        trace_output: Path | None,
        capability: str,
        allowed_hosts: frozenset[str] | None = None,
        max_inference_calls: int = MAX_INFERENCE_CALLS,
        header_timeout: float = HEADER_TIMEOUT_SECONDS,
        body_timeout: float = BODY_TIMEOUT_SECONDS,
    ) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be positive")
        if max_inference_calls < 1:
            raise ValueError("max_inference_calls must be positive")
        if not capability:
            raise ValueError("capability_required")
        if len(capability) > 256:
            raise ValueError("capability is too long")
        if header_timeout <= 0 or body_timeout <= 0:
            raise ValueError("timeouts must be positive")
        self.controller = controller
        self.allowed_origins = allowed_origins
        self.allowed_hosts = allowed_hosts or frozenset()
        self.capability = capability
        self.max_workers = max_workers
        self.header_timeout = float(header_timeout)
        self.body_timeout = float(body_timeout)
        self.trace_output = trace_output
        self.trace_lock = threading.Lock()
        self.trace_capacity_lock = threading.Lock()
        self.trace_exported_cursors: dict[tuple[str, int], dict[str, Any]] = {}
        self.trace_rows_total = 0
        self.trace_rows_reserved = 0
        self._trace_reservation_seq = 0
        self._trace_reservations: dict[int, tuple[tuple[str, int], int]] = {}
        self._trace_reservations_by_key: dict[tuple[str, int], list[int]] = {}
        self._trace_local = threading.local()
        self.inference_lock = threading.Lock()
        self.inference_calls = 0
        self.max_inference_calls = max_inference_calls
        self.shutdown = threading.Event()
        self.controller.before_inference = self.reserve_inference
        self.controller.before_session = self.reserve_trace
        self.controller.before_decision = self.reserve_trace
        self.controller.before_result = self.reserve_trace

    def set_allowed_hosts(self, hosts: frozenset[str]) -> None:
        self.allowed_hosts = hosts

    def reserve_inference(self) -> None:
        with self.inference_lock:
            if self.inference_calls >= self.max_inference_calls:
                raise BudgetExceeded("aggregate_inference_quota_exceeded")
            self.inference_calls += 1

    def reserve_trace(self, session_id: str, session_epoch: int, rows: int) -> None:
        if self.trace_output is None:
            return
        if rows < 1:
            raise ValueError("trace reservation must be positive")
        key = (session_id, session_epoch)
        with self.trace_capacity_lock:
            if self.trace_rows_total + self.trace_rows_reserved + rows > 4096:
                raise ControllerFailure("trace_overflow")
            self._trace_reservation_seq += 1
            token = self._trace_reservation_seq
            self._trace_reservations[token] = (key, rows)
            self._trace_reservations_by_key.setdefault(key, []).append(token)
            self.trace_rows_reserved += rows
            tokens = list(getattr(self._trace_local, "tokens", []))
            tokens.append(token)
            self._trace_local.tokens = tokens

    def _release_trace_reservation_locked(self, token: int) -> None:
        reservation = self._trace_reservations.pop(token, None)
        if reservation is None:
            return
        key, rows = reservation
        tokens = self._trace_reservations_by_key.get(key)
        if tokens is not None:
            try:
                tokens.remove(token)
            except ValueError:
                pass
            if not tokens:
                self._trace_reservations_by_key.pop(key, None)
        self.trace_rows_reserved -= rows
        local_tokens = [
            value for value in getattr(self._trace_local, "tokens", []) if value != token
        ]
        self._trace_local.tokens = local_tokens

    def release_trace_reservation(self, session_id: str, session_epoch: int) -> None:
        key = (session_id, session_epoch)
        with self.trace_capacity_lock:
            tokens = list(getattr(self._trace_local, "tokens", []))
            token = next(
                (
                    value
                    for value in reversed(tokens)
                    if self._trace_reservations.get(value, (None, 0))[0] == key
                ),
                None,
            )
            if token is not None:
                self._release_trace_reservation_locked(token)

    def _trace_reservation_for_key_locked(self, key: tuple[str, int]) -> int | None:
        tokens = list(getattr(self._trace_local, "tokens", []))
        for token in reversed(tokens):
            if self._trace_reservations.get(token, (None, 0))[0] == key:
                return token
        return None

    def write_trace(self, session_id: str, session_epoch: int) -> None:
        if self.trace_output is None:
            return
        with self.trace_lock:
            snapshot = self.controller.export_trace(session_id, session_epoch=session_epoch)
            if not isinstance(snapshot, Mapping):
                raise ControllerFailure("trace_snapshot_invalid")
            snapshot_id = snapshot.get("snapshot_id")
            snapshot_session_id = snapshot.get("session_id")
            snapshot_epoch = snapshot.get("session_epoch")
            cursor = snapshot.get("cursor")
            rows = snapshot.get("rows")
            if (
                not isinstance(snapshot_id, str)
                or not snapshot_id
                or snapshot_session_id != session_id
                or snapshot_epoch != session_epoch
                or not isinstance(cursor, Mapping)
                or not isinstance(rows, list)
                or any(not isinstance(row, Mapping) for row in rows)
                or cursor.get("session_id") != session_id
                or cursor.get("session_epoch") != session_epoch
                or isinstance(cursor.get("row_count"), bool)
                or not isinstance(cursor.get("row_count"), int)
                or cursor["row_count"] < 0
                or cursor["row_count"] != len(rows)
                or not isinstance(cursor.get("head_hash"), str)
            ):
                raise ControllerFailure("trace_snapshot_invalid")
            if rows and rows[-1].get("hash") != cursor["head_hash"]:
                raise ControllerFailure("trace_cursor_mismatch")
            if len(rows) > 4096:
                raise ControllerFailure("trace_overflow")

            key = (session_id, session_epoch)
            prior = self.trace_exported_cursors.get(key)
            start = 0
            if prior is not None:
                prior_count = prior["row_count"]
                if prior_count > len(rows):
                    raise ControllerFailure("trace_cursor_mismatch")
                if prior_count and rows[prior_count - 1].get("hash") != prior["head_hash"]:
                    raise ControllerFailure("trace_cursor_mismatch")
                if prior["snapshot_id"] == snapshot_id and (
                    cursor["row_count"] != prior_count or cursor["head_hash"] != prior["head_hash"]
                ):
                    raise ControllerFailure("trace_cursor_mismatch")
                if prior_count == len(rows) and prior["snapshot_id"] != snapshot_id:
                    raise ControllerFailure("trace_cursor_mismatch")
                start = prior_count
            new_rows = rows[start:]
            if new_rows:
                with self.trace_capacity_lock:
                    has_reservation = self._trace_reservation_for_key_locked(key) is not None
                if not has_reservation:
                    self.reserve_trace(session_id, session_epoch, len(new_rows))
            with self.trace_capacity_lock:
                token = self._trace_reservation_for_key_locked(key)
                reserved = (
                    self._trace_reservations.get(token, (key, 0))[1] if token is not None else 0
                )
                if token is not None and len(new_rows) > reserved:
                    raise ControllerFailure("trace_overflow")
                if self.trace_rows_total + len(new_rows) > 4096:
                    raise ControllerFailure("trace_overflow")
                if not new_rows:
                    if token is not None:
                        self._release_trace_reservation_locked(token)
                    return
            self.trace_output.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_output.open("a", encoding="utf-8") as handle:
                for row in new_rows:
                    record = {
                        "schema_version": SCHEMA_VERSION,
                        "session_id": session_id,
                        "session_epoch": session_epoch,
                        "snapshot_id": snapshot_id,
                        "row": row,
                    }
                    handle.write(
                        json.dumps(
                            record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                        )
                        + "\n"
                    )
            self.trace_exported_cursors[key] = {
                "session_id": session_id,
                "session_epoch": session_epoch,
                "snapshot_id": snapshot_id,
                "row_count": cursor["row_count"],
                "head_hash": cursor["head_hash"],
            }
            with self.trace_capacity_lock:
                self.trace_rows_total += len(new_rows)
                if token is not None:
                    self._release_trace_reservation_locked(token)


class NpcHandler(BaseHTTPRequestHandler):
    server_version = "npc-goal-service/1.1"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> ServiceState:
        return self.server.service_state  # type: ignore[attr-defined]

    def setup(self) -> None:
        super().setup()
        self.connection.settimeout(self.state.header_timeout)

    def handle(self) -> None:
        try:
            super().handle()
        except TimeoutError:
            self.close_connection = True

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return origin is None or origin in self.state.allowed_origins

    def _host_allowed(self) -> bool:
        hosts = self.headers.get_all("Host", [])
        return len(hosts) == 1 and hosts[0] in self.state.allowed_hosts

    def _capability_allowed(self) -> bool:
        supplied = self.headers.get(CAPABILITY_HEADER)
        expected = f"Bearer {self.state.capability}"
        return supplied is not None and hmac.compare_digest(supplied, expected)

    def _send_json(
        self, status: int, payload: Mapping[str, Any], *, origin: str | None = None
    ) -> None:
        self.close_connection = True
        encoded = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        if origin in self.state.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-NPC-Capability")
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except OSError:
            self.close_connection = True

    def _error(self, status: int, code: str) -> None:
        self._send_json(
            status,
            {"error": code, "schema_version": SCHEMA_VERSION},
            origin=self.headers.get("Origin"),
        )

    def _check_route_access(self, *, capability_required: bool) -> bool:
        if not self._host_allowed():
            self._error(HTTPStatus.FORBIDDEN, "host_not_allowed")
            return False
        if not self._origin_allowed():
            self._error(HTTPStatus.FORBIDDEN, "origin_not_allowed")
            return False
        if capability_required and not self._capability_allowed():
            self._error(HTTPStatus.UNAUTHORIZED, "capability_required")
            return False
        return True

    def do_OPTIONS(self) -> None:
        if not self._check_route_access(capability_required=False):
            return
        self.close_connection = True
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Content-Length", "0")
        self.send_header("Connection", "close")
        origin = self.headers.get("Origin")
        if origin in self.state.allowed_origins:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, X-NPC-Capability")
        self.end_headers()

    def do_GET(self) -> None:
        if not self._check_route_access(capability_required=False):
            return
        path = urlsplit(self.path).path
        if path != "/health":
            self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        self._send_json(
            HTTPStatus.OK,
            {
                "status": "ok",
                "schema_version": SCHEMA_VERSION,
                "config_hash": CANONICAL_CONFIG_HASH,
                "service": "npc-goal",
            },
            origin=self.headers.get("Origin"),
        )

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if path not in {"/npc/step", "/npc/result", "/npc/replay"}:
            self._check_route_access(capability_required=False)
            if not self.close_connection:
                self._error(HTTPStatus.NOT_FOUND, "not_found")
            return
        if not self._check_route_access(capability_required=path != "/npc/replay"):
            return
        if self.headers.get("Transfer-Encoding"):
            self._error(HTTPStatus.LENGTH_REQUIRED, "transfer_encoding_not_allowed")
            return
        if self.headers.get("Content-Type") != "application/json":
            self._error(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content_type_must_be_application_json")
            return
        try:
            content_length = int(self.headers.get("Content-Length", "-1"))
        except (TypeError, ValueError):
            content_length = -1
        if content_length < 0 or content_length > BODY_LIMIT:
            self._error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body_limit_exceeded")
            return
        payload: Any = None
        envelope: Mapping[str, Any] | None = None
        try:
            self.connection.settimeout(self.state.body_timeout)
            raw = self.rfile.read(content_length)
            if len(raw) != content_length:
                self._error(HTTPStatus.BAD_REQUEST, "incomplete_body")
                return
            try:
                payload = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError):
                self._error(HTTPStatus.BAD_REQUEST, "invalid_json")
                return
            if not _json_depth_within_limit(payload):
                self._error(HTTPStatus.BAD_REQUEST, "json_nesting_too_deep")
                return
            if path == "/npc/replay":
                self._handle_replay(payload)
                return
            expected = "request" if path == "/npc/step" else "result"
            envelope = validate_envelope(_prepare_payload(payload), expected_message_type=expected)
            if envelope["config_hash"] != CANONICAL_CONFIG_HASH:
                raise ProtocolError("config_hash_mismatch")
            if expected == "request":
                response = self.state.controller.handle_request(envelope)
            else:
                response = self.state.controller.handle_result(envelope)
            try:
                self.state.write_trace(envelope["session_id"], envelope["session_epoch"])
            except (ControllerFailure, OSError) as exc:
                self._error(HTTPStatus.INTERNAL_SERVER_ERROR, f"trace_write_failed:{exc}")
                return
            self._send_json(HTTPStatus.OK, response, origin=self.headers.get("Origin"))
        except ProtocolError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
        except BudgetExceeded as exc:
            self._send_controller_error(payload, str(exc), HTTPStatus.TOO_MANY_REQUESTS)
        except ControllerFailure as exc:
            self._send_controller_error(payload, str(exc), HTTPStatus.CONFLICT)
        except TypeError:
            self._send_controller_error(payload, "invalid_payload", HTTPStatus.BAD_REQUEST)
        except (ValueError, AttributeError, KeyError, RecursionError):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_payload")
        except TimeoutError:
            self.close_connection = True
        finally:
            if envelope is not None:
                self.state.release_trace_reservation(
                    envelope["session_id"], envelope["session_epoch"]
                )

    def _handle_replay(self, payload: Any) -> None:
        if not isinstance(payload, dict) or set(payload) != {"records", "expected_session_id"}:
            self._error(HTTPStatus.BAD_REQUEST, "replay_payload_keys")
            return
        records = payload["records"]
        expected = payload["expected_session_id"]
        if (
            not isinstance(records, list)
            or any(not isinstance(record, dict) for record in records)
            or (expected is not None and not isinstance(expected, str))
        ):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_replay_payload")
            return
        try:
            result = ReplayValidator.validate(records, expected_session_id=expected)
        except ProtocolError as exc:
            self._error(HTTPStatus.BAD_REQUEST, str(exc))
            return
        except (ControllerFailure, TypeError, ValueError, AttributeError, KeyError):
            self._error(HTTPStatus.BAD_REQUEST, "invalid_replay_payload")
            return
        self._send_json(HTTPStatus.OK, result, origin=self.headers.get("Origin"))

    def _send_controller_error(self, payload: Any, code: str, status: int) -> None:
        if isinstance(payload, dict):
            try:
                valid = validate_envelope(_prepare_payload(payload))
                ack = GoalController.make_envelope(
                    valid,
                    "ack",
                    {"ack_for": valid["message_type"], "status": "REJECTED", "error": code},
                )
                self._send_json(status, ack, origin=self.headers.get("Origin"))
                return
            except (ProtocolError, TypeError, ValueError, AttributeError, KeyError):
                pass
        self._error(status, code)


class NpcServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host: str, port: int, state: ServiceState) -> None:
        super().__init__((host, port), NpcHandler)
        self.service_state = state
        self.connection_slots = threading.BoundedSemaphore(state.max_workers)
        if not state.allowed_hosts:
            state.set_allowed_hosts(frozenset({f"{host}:{self.server_port}"}))

    def process_request(self, request: socket.socket, client_address: Any) -> None:
        if not self.connection_slots.acquire(blocking=False):
            self.close_request(request)
            return
        try:
            thread = threading.Thread(
                target=self.process_request_thread,
                args=(request, client_address),
                daemon=self.daemon_threads,
            )
            thread.start()
        except BaseException:
            self.connection_slots.release()
            self.close_request(request)
            raise

    def process_request_thread(self, request: socket.socket, client_address: Any) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.connection_slots.release()


def validate_replay(
    records: list[Mapping[str, Any]], *, expected_session_id: str | None = None
) -> dict[str, Any]:
    """Evaluator callable: validate recorded envelopes without rerunning Codex."""
    return ReplayValidator.validate(records, expected_session_id=expected_session_id)


def build_parser() -> argparse.ArgumentParser:
    canonical = _load_canonical_transport()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host",
        default=canonical["bind"],
        help=f"loopback bind host (default: {canonical['bind']})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=canonical["port"],
        help=f"loopback bind port (default: {canonical['port']})",
    )
    parser.add_argument(
        "--backend",
        choices=("codex", "rule", "reference"),
        default="codex",
        help="explicit interpreter arm; no hidden fallback",
    )
    parser.add_argument(
        "--model", default=None, help="Codex model identifier; unavailable accounting remains null"
    )
    parser.add_argument(
        "--trace-output",
        type=Path,
        default=None,
        help="opt-in JSONL trace destination; raw utterances are never written",
    )
    parser.add_argument(
        "--cache-ttl", type=float, default=30.0, help="bounded response cache TTL seconds (0-3600)"
    )
    parser.add_argument(
        "--max-workers", type=int, default=4, help="bounded concurrent request workers (1-32)"
    )
    parser.add_argument(
        "--allow-origin",
        action="append",
        dest="origins",
        help="additional exact loopback origin; repeatable",
    )
    return parser


def run_service(args: argparse.Namespace) -> int:
    canonical = _load_canonical_transport()
    global BODY_LIMIT, CANONICAL_CONFIG_HASH
    BODY_LIMIT = canonical["body_limit"]
    CANONICAL_CONFIG_HASH = canonical["config_hash"]
    extra_origins = frozenset(_validate_loopback_origin(origin) for origin in (args.origins or ()))
    origins = canonical["origins"] | extra_origins
    if args.host != canonical["bind"]:
        raise ValueError("service bind must match canonical transport config")
    if not 1 <= args.port <= 65535 or not 1 <= args.max_workers <= 32:
        raise ValueError("port/max-workers out of range")
    if args.cache_ttl < 0 or args.cache_ttl > 3600:
        raise ValueError("cache-ttl out of range")
    capability = os.environ.get("TRACE_RPG_NPC_CAPABILITY")
    if not capability:
        raise ValueError("TRACE_RPG_NPC_CAPABILITY is required")
    arm = {"codex": "P", "rule": "R", "reference": "O"}[args.backend]
    interpreter = IntentInterpreter(arm=arm, model=args.model)
    controller = GoalController(interpreter=interpreter, cache_ttl_seconds=args.cache_ttl)
    state = ServiceState(
        controller,
        allowed_origins=origins,
        max_workers=args.max_workers,
        trace_output=args.trace_output,
        capability=capability,
    )
    server = NpcServer(args.host, args.port, state)

    def stop(_signum: int, _frame: Any) -> None:
        state.shutdown.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    try:
        server.serve_forever(poll_interval=0.25)
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run_service(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
