from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P))
sys.path.insert(0, str(P / "src"))

from nesy_game.npc_goal import (
    GoalController,
    IntentInterpreter,
    ReplayValidator,
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
OBSERVATION_KEYS = (
    "lens_reachable",
    "lens_carried",
    "signal_restored",
    "tide_lead_authorized",
    "goal_reached",
    "in_dialogue",
)


def observation(**overrides: bool) -> dict[str, bool]:
    value = {key: False for key in OBSERVATION_KEYS}
    value.update(overrides)
    return value


def request(
    request_id: str,
    *,
    session_id: str = "epoch-session",
    session_epoch: int = 0,
    revision: int = 0,
    obs: dict[str, bool] | None = None,
    state_ref: dict[str, object] | None = None,
) -> dict:
    return default_envelope(
        message_type="request",
        session_id=session_id,
        session_epoch=session_epoch,
        request_id=request_id,
        sequence=-1,
        delivery_index=-1,
        state_ref=state_ref
        if state_ref is not None
        else {
            "revision": revision,
            "sha256": hashlib.sha256(f"state-{revision}".encode()).hexdigest(),
        },
        body={
            "event_kind": "utterance",
            "utterance": "Where is the lens?",
            "observation": obs or observation(lens_reachable=True),
        },
        policy_hash=POLICY_HASH,
        arm="R",
        backend="rule",
    )


def result_for(source: dict, decision: dict) -> dict:
    step = decision["body"]["steps"][0]
    result_revision = source["state_ref"]["revision"] + 1
    result_state = {
        "revision": result_revision,
        "sha256": hashlib.sha256(f"result-{result_revision}".encode()).hexdigest(),
    }
    return default_envelope(
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
            "status": "APPLIED",
            "engine_revision": result_revision,
            "state_ref": result_state,
            "feedback": "applied",
            "observation": observation(lens_carried=True),
        },
        policy_hash=POLICY_HASH,
        arm="R",
        backend="rule",
    )


class CountingInterpreter:
    arm = "R"
    model = None

    def __init__(self) -> None:
        self.calls = 0
        self._rule = IntentInterpreter(arm="R")

    def interpret(self, *, request_id: str, utterance: str, timeout_ms: int | None = None):
        self.calls += 1
        return self._rule.interpret(
            request_id=request_id, utterance=utterance, timeout_ms=timeout_ms
        )


@contextmanager
def running_service(
    controller: GoalController, trace_output: Path, *, max_workers: int = 2
) -> Iterator[tuple[str, ServiceState]]:
    state = ServiceState(
        controller,
        allowed_origins=DEFAULT_ALLOWED_ORIGINS,
        max_workers=max_workers,
        trace_output=trace_output,
        capability="test-capability",
        header_timeout=0.5,
        body_timeout=0.5,
    )
    server = NpcServer("127.0.0.1", 0, state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def http_post(base: str, path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | None]:
    request_data = json.dumps(payload, separators=(",", ":")).encode()
    request = urllib.request.Request(
        base + path,
        data=request_data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            CAPABILITY_HEADER: "Bearer test-capability",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            body = response.read()
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as error:
        try:
            body = error.read()
        finally:
            error.close()
        return error.code, json.loads(body) if body else None


class NpcServiceEpochContractTests(unittest.TestCase):
    def _complete_two_epoch_controller(self) -> tuple[GoalController, dict, dict]:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        old = request("old-commit")
        old_decision = controller.handle_request(old)
        old_result = result_for(old, old_decision)
        self.assertEqual(controller.handle_result(old_result)["body"]["status"], "ACCEPTED")
        new = request("new-epoch", session_epoch=1, revision=1, obs=observation(lens_carried=True))
        new["state_ref"] = dict(old_result["body"]["state_ref"])
        new["content_sha256"] = content_hash(new)
        controller.handle_request(new)
        return controller, old, new

    def test_each_epoch_exports_complete_row_zero_snapshot_replay_validates_independently(
        self,
    ) -> None:
        controller, old, _new = self._complete_two_epoch_controller()
        snapshots = {
            epoch: controller.export_trace(old["session_id"], session_epoch=epoch)
            for epoch in (0, 1)
        }
        self.assertEqual(snapshots[0]["session_epoch"], 0)
        self.assertEqual(snapshots[1]["session_epoch"], 1)
        for epoch, snapshot in snapshots.items():
            with self.subTest(epoch=epoch):
                self.assertGreaterEqual(snapshot["cursor"]["row_count"], 2)
                self.assertEqual(snapshot["cursor"]["row_count"], len(snapshot["rows"]))
                self.assertEqual(snapshot["rows"][0]["sequence"], 0)
                self.assertEqual(
                    ReplayValidator.validate(snapshot, expected_session_id=old["session_id"]),
                    {
                        "valid": True,
                        "rows": len(snapshot["rows"]),
                        "content_hashes": [row["content_sha256"] for row in snapshot["rows"]],
                        "intent_lineage_scope": "epoch_local_only",
                        "cross_epoch_intent_continuity_proven": False,
                    },
                )
        self.assertNotEqual(snapshots[0]["snapshot_id"], snapshots[1]["snapshot_id"])

    def test_old_complete_snapshot_survives_epoch_replacement_before_first_trace_write(
        self,
    ) -> None:
        controller = GoalController(interpreter=IntentInterpreter(arm="R"))
        old = request("race-old")
        old_decision = controller.handle_request(old)
        old_result = result_for(old, old_decision)
        self.assertEqual(controller.handle_result(old_result)["body"]["status"], "ACCEPTED")
        new = request(
            "race-new",
            session_epoch=1,
            revision=1,
            obs=observation(lens_carried=True),
            state_ref=old_result["body"]["state_ref"],
        )
        controller.handle_request(new)

        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            state = ServiceState(
                controller,
                allowed_origins=DEFAULT_ALLOWED_ORIGINS,
                max_workers=1,
                trace_output=trace_output,
                capability="test-capability",
            )
            state.write_trace(old["session_id"], 0)
            state.write_trace(old["session_id"], 1)
            persisted = [
                json.loads(line) for line in trace_output.read_text(encoding="utf-8").splitlines()
            ]

        by_epoch = {
            epoch: [record for record in persisted if record["session_epoch"] == epoch]
            for epoch in (0, 1)
        }
        old_snapshot = controller.export_trace(old["session_id"], session_epoch=0)
        new_snapshot = controller.export_trace(old["session_id"], session_epoch=1)
        self.assertEqual(len(by_epoch[0]), len(old_snapshot["rows"]))
        self.assertEqual(len(by_epoch[1]), len(new_snapshot["rows"]))
        self.assertEqual(by_epoch[0][0]["row"]["sequence"], 0)
        self.assertEqual(by_epoch[1][0]["row"]["sequence"], 0)
        self.assertEqual([record["row"] for record in by_epoch[0]], old_snapshot["rows"])
        self.assertEqual([record["row"] for record in by_epoch[1]], new_snapshot["rows"])
        self.assertTrue(
            ReplayValidator.validate(old_snapshot, expected_session_id=old["session_id"])["valid"]
        )
        self.assertTrue(
            ReplayValidator.validate(new_snapshot, expected_session_id=old["session_id"])["valid"]
        )

    def test_request_export_capacity_is_reserved_before_controller_commit(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                state.trace_rows_total = 4095
                payload = request("service-capacity-request", session_id="service-capacity-session")
                status, response = http_post(base, "/npc/step", payload)
                self.assertEqual(status, 409)
                self.assertIsNotNone(response)
                self.assertEqual(response["body"]["status"], "REJECTED")
                self.assertEqual(response["body"]["error"], "trace_overflow")
                self.assertEqual(interpreter.calls, 0)
                self.assertNotIn(payload["session_id"], controller._sessions)
                self.assertEqual(state.trace_rows_total, 4095)
                self.assertFalse(trace_output.exists())

    def test_fresh_request_exact_fit_export_capacity_is_accepted(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                state.trace_rows_total = 4094
                payload = request("service-exact-fit", session_id="service-exact-fit-session")
                status, response = http_post(base, "/npc/step", payload)
                self.assertEqual(status, 200)
                self.assertIsNotNone(response)
                self.assertEqual(response["body"]["status"], "WAITING_PLAYER")
                self.assertEqual(interpreter.calls, 1)
                self.assertEqual(state.trace_rows_total, 4096)
                self.assertEqual(state.trace_rows_reserved, 0)

    def test_higher_epoch_global_overflow_preserves_current_session_before_retirement(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                state.trace_rows_total = 4094
                old_payload = request("epoch-overflow-old", session_id="epoch-overflow-session")
                status, old_response = http_post(base, "/npc/step", old_payload)
                self.assertEqual(status, 200)
                self.assertEqual(old_response["body"]["status"], "WAITING_PLAYER")
                old_state = controller._sessions[old_payload["session_id"]]
                state.trace_rows_total = 4096
                replacement = request(
                    "epoch-overflow-new",
                    session_id=old_payload["session_id"],
                    session_epoch=1,
                    state_ref=old_payload["state_ref"],
                )
                status, response = http_post(base, "/npc/step", replacement)
                self.assertEqual(status, 409)
                self.assertEqual(response["body"]["status"], "REJECTED")
                self.assertEqual(response["body"]["error"], "trace_overflow")
                self.assertIs(controller._sessions[old_payload["session_id"]], old_state)
                self.assertEqual(old_state.session_epoch, 0)
                self.assertEqual(controller._retired_sessions, {})
                self.assertEqual(interpreter.calls, 1)
                self.assertEqual(state.trace_rows_reserved, 0)

    def test_trace_write_oserror_returns_500_without_false_rejected_ack(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                payload = request("trace-write-oserror", session_id="trace-write-oserror-session")

                def fail_write(_session_id: str, _session_epoch: int) -> None:
                    raise OSError("disk-full")

                state.write_trace = fail_write  # type: ignore[method-assign]
                status, response = http_post(base, "/npc/step", payload)
                self.assertEqual(status, 500)
                self.assertEqual(response["error"], "trace_write_failed:disk-full")
                session = controller._sessions[payload["session_id"]]
                self.assertEqual(session.calls, 1)
                self.assertEqual(len(session.trace), 1)
                self.assertEqual(len(session.replay_records), 2)
                self.assertEqual(state.trace_rows_reserved, 0)
                self.assertFalse(trace_output.exists())

    def test_cached_retry_exports_pending_rows_without_new_interpretation(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                payload = request("cached-pending-trace", session_id="cached-pending-session")
                original_write_trace = state.write_trace

                def fail_write(_session_id: str, _session_epoch: int) -> None:
                    raise OSError("transient-disk-error")

                state.write_trace = fail_write  # type: ignore[method-assign]
                status, response = http_post(base, "/npc/step", payload)
                self.assertEqual(status, 500)
                self.assertEqual(response["error"], "trace_write_failed:transient-disk-error")
                state.write_trace = original_write_trace  # type: ignore[method-assign]
                status, cached = http_post(base, "/npc/step", payload)
                self.assertEqual(status, 200)
                self.assertEqual(cached["body"]["status"], "WAITING_PLAYER")
                self.assertEqual(interpreter.calls, 1)
                self.assertEqual(state.trace_rows_total, 2)
                self.assertEqual(state.trace_rows_reserved, 0)

    def test_foreign_thread_reservation_survives_cached_and_rejected_requests(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                state.trace_rows_total = 4094
                cached_payload = request(
                    "foreign-thread-cached", session_id="foreign-thread-session"
                )
                status, first = http_post(base, "/npc/step", cached_payload)
                self.assertEqual(status, 200)
                self.assertEqual(first["body"]["status"], "WAITING_PLAYER")
                state.trace_rows_total = 4095
                state.reserve_trace(cached_payload["session_id"], 0, 1)
                status, cached = http_post(base, "/npc/step", cached_payload)
                self.assertEqual(status, 200)
                self.assertEqual(cached, first)
                self.assertEqual(state.trace_rows_reserved, 1)

                rejected_payload = request(
                    "foreign-thread-rejected", session_id="foreign-thread-rejected-session"
                )
                status, rejected = http_post(base, "/npc/step", rejected_payload)
                self.assertEqual(status, 409)
                self.assertEqual(rejected["body"]["error"], "trace_overflow")
                self.assertEqual(state.trace_rows_reserved, 1)
                self.assertEqual(interpreter.calls, 1)
                state.release_trace_reservation(cached_payload["session_id"], 0)
                self.assertEqual(state.trace_rows_reserved, 0)

    def test_service_trace_reservations_release_for_cached_and_rejected_requests(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                state.trace_rows_total = 4094
                cached_payload = request("service-cached", session_id="service-cached-session")
                status, first = http_post(base, "/npc/step", cached_payload)
                self.assertEqual(status, 200)
                self.assertEqual(first["body"]["status"], "WAITING_PLAYER")
                self.assertEqual(state.trace_rows_total, 4096)
                self.assertEqual(state.trace_rows_reserved, 0)

                status, cached = http_post(base, "/npc/step", cached_payload)
                self.assertEqual(status, 200)
                self.assertEqual(cached, first)
                self.assertEqual(interpreter.calls, 1)
                self.assertEqual(state.trace_rows_total, 4096)
                self.assertEqual(state.trace_rows_reserved, 0)

                retry_payload = request(
                    "service-rejected-retry", session_id="service-rejected-session"
                )
                status, rejected = http_post(base, "/npc/step", retry_payload)
                self.assertEqual(status, 409)
                self.assertEqual(rejected["body"]["error"], "trace_overflow")
                self.assertEqual(interpreter.calls, 1)
                self.assertNotIn(retry_payload["session_id"], controller._sessions)
                self.assertEqual(state.trace_rows_reserved, 0)

                state.trace_rows_total = 4094
                status, retried = http_post(base, "/npc/step", retry_payload)
                self.assertEqual(status, 200)
                self.assertEqual(retried["body"]["status"], "WAITING_PLAYER")
                self.assertEqual(interpreter.calls, 2)
                self.assertEqual(state.trace_rows_reserved, 0)

    def test_concurrent_trace_reservation_rejects_before_second_inference(self) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output, max_workers=2) as (base, state):
                state.trace_rows_total = 4094
                export_started = threading.Event()
                release_export = threading.Event()
                original_export = controller.export_trace

                def gated_export(*args: Any, **kwargs: Any) -> dict[str, Any]:
                    export_started.set()
                    if not release_export.wait(2):
                        raise AssertionError("trace export barrier was not released")
                    return original_export(*args, **kwargs)

                controller.export_trace = gated_export  # type: ignore[method-assign]
                first_payload = request(
                    "service-concurrent-first", session_id="service-concurrent-first"
                )
                second_payload = request(
                    "service-concurrent-second", session_id="service-concurrent-second"
                )
                first_outcome: dict[str, Any] = {}

                def send_first() -> None:
                    first_outcome["response"] = http_post(base, "/npc/step", first_payload)

                thread = threading.Thread(target=send_first)
                thread.start()
                self.assertTrue(export_started.wait(1))
                second_status, second_response = http_post(base, "/npc/step", second_payload)
                self.assertEqual(second_status, 409)
                self.assertEqual(second_response["body"]["error"], "trace_overflow")
                self.assertEqual(interpreter.calls, 1)
                self.assertNotIn(second_payload["session_id"], controller._sessions)
                release_export.set()
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertEqual(first_outcome["response"][0], 200)
                self.assertEqual(first_outcome["response"][1]["body"]["status"], "WAITING_PLAYER")

                self.assertEqual(state.trace_rows_reserved, 0)

    def test_result_export_capacity_is_reserved_before_state_adoption_and_exact_fit_is_accepted(
        self,
    ) -> None:
        interpreter = CountingInterpreter()
        controller = GoalController(interpreter=interpreter)
        with tempfile.TemporaryDirectory() as directory:
            trace_output = Path(directory) / "trace.jsonl"
            with running_service(controller, trace_output) as (base, state):
                source = request("service-result-capacity", session_id="service-result-session")
                status, decision = http_post(base, "/npc/step", source)
                self.assertEqual(status, 200)
                result = result_for(source, decision)
                session = controller._sessions[source["session_id"]]
                state.trace_rows_total = 4096
                status, rejected = http_post(base, "/npc/result", result)
                self.assertEqual(status, 409)
                self.assertEqual(rejected["body"]["status"], "REJECTED")
                self.assertEqual(rejected["body"]["error"], "trace_overflow")
                self.assertEqual(state.trace_rows_reserved, 0)
                self.assertEqual(session.action_attempts, 0)
                self.assertEqual(session.accepted_results, {})
                self.assertEqual(session.last_result_ids, set())
                self.assertEqual(len(session.trace), 1)
                self.assertEqual(len(session.replay_records), 2)

                state.trace_rows_total = 4095
                status, accepted = http_post(base, "/npc/result", result)
                self.assertEqual(status, 200)
                self.assertEqual(accepted["body"]["status"], "ACCEPTED")
                self.assertEqual(session.action_attempts, 1)
                self.assertEqual(len(session.trace), 2)
                self.assertEqual(len(session.replay_records), 3)
                self.assertEqual(state.trace_rows_reserved, 0)


if __name__ == "__main__":
    unittest.main()
