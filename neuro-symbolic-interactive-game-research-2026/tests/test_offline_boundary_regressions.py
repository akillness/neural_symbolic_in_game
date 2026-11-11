import hashlib
import io
import json

import codex_feedback_live_adapter as adapter
import codex_feedback_pilot as pilot
import pytest
import run_equal_information_feedback as feedback
import run_fixed_oracle_comparison as comparison

from nesy_game.runtime import to_jsonable


def forbidden(*args, **kwargs):
    pytest.fail("unapproved request reached process or network")


@pytest.mark.parametrize(
    "event,returncode,expected",
    [
        (
            {"type": "error", "error": {"code": "rate_limit_exceeded", "message": "private"}},
            1,
            "provider_error",
        ),
        (
            {"type": "item.completed", "item": {"type": "error", "message": "private"}},
            0,
            "provider_error",
        ),
        ({"type": "thread.started"}, 7, "process_error"),
        ({"type": "unexpected"}, 0, "protocol_error"),
    ],
)
def test_dispatch_classifies_failures_without_releasing_response(
    prepared_request, monkeypatch, event, returncode, expected
):
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
        def __init__(self, *args, **kwargs):
            self.returncode = returncode
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO((json.dumps(event) + "\n").encode())
            self.stderr = io.BytesIO(b"private stderr")

        def poll(self):
            return self.returncode

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with pytest.raises(adapter.DispatchError) as failure:
        adapter.dispatch(**prepared_request)
    assert failure.value.code == expected
    assert failure.value.evidence["request_count"] is None
    assert failure.value.evidence["tls_payload_observed"] is False
    assert "private" not in json.dumps(failure.value.evidence)


@pytest.mark.parametrize("item_error", [False, True])
def test_unencodable_provider_message_is_unknown_but_keeps_structured_classification(
    prepared_request, monkeypatch, item_error
):
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
        returncode = 1

        def __init__(self, *args, **kwargs):
            self.stdin = io.BytesIO()
            error = {"type": "error", "code": "rate_limit_exceeded", "message": "\ud800"}
            event = {"type": "item.completed", "item": error} if item_error else error
            self.stdout = io.BytesIO((json.dumps(event) + "\n").encode())
            self.stderr = io.BytesIO()

        def poll(self):
            return self.returncode

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with pytest.raises(adapter.DispatchError) as failure:
        adapter.dispatch(**prepared_request)
    assert failure.value.code == "provider_error"
    event = failure.value.evidence["events"][0]
    assert event["error_message_sha256"] is None
    assert event["error_classification"] == "rate_limit"
    assert failure.value.evidence["request_count"] is None


@pytest.mark.parametrize(
    "usage,expected",
    [
        (
            {
                "input_tokens": 0,
                "cached_input_tokens": 12,
                "output_tokens": 2**63 - 1,
                "total_tokens": 42,
                "private": {"nested": "synthetic-secret"},
            },
            {
                "input_tokens": 0,
                "cached_input_tokens": 12,
                "output_tokens": 2**63 - 1,
                "total_tokens": 42,
            },
        ),
        (
            {
                "input_tokens": -1,
                "cached_input_tokens": True,
                "output_tokens": 2**63,
                "total_tokens": "synthetic-secret",
            },
            {},
        ),
        ({"input_tokens": 1.5, "output_tokens": ["synthetic-secret"], "total_tokens": None}, {}),
        (None, None),
        ("synthetic-secret", None),
    ],
)
def test_usage_preserves_only_bounded_integer_token_counts(
    prepared_request, monkeypatch, usage, expected
):
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
            self.stdin = io.BytesIO()
            events = [
                {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}},
                {"type": "turn.completed", "usage": usage},
            ]
            self.stdout = io.BytesIO(
                b"".join((json.dumps(event) + "\n").encode() for event in events)
            )
            self.stderr = io.BytesIO()

        def poll(self):
            return self.returncode

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", Process)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    result = adapter.dispatch(**prepared_request)
    assert result["tokens"] == expected
    assert "synthetic-secret" not in json.dumps(result)


def test_process_launch_failure_is_sanitized_and_unknown(prepared_request, monkeypatch):
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

    def fail(*args, **kwargs):
        raise OSError("private launch failure")

    monkeypatch.setattr(adapter, "_Proxy", Proxy)
    monkeypatch.setattr(adapter.subprocess, "Popen", fail)
    monkeypatch.setattr(adapter.socket, "create_connection", forbidden)
    with pytest.raises(adapter.DispatchError) as failure:
        adapter.dispatch(**prepared_request)
    assert failure.value.code == "process_error"
    assert failure.value.evidence is None
    assert "private" not in str(failure.value)
    assert failure.value.__cause__ is None


@pytest.mark.parametrize(
    "response,error_type",
    [
        pytest.param("synthetic-private-secret 한글", "JSONDecodeError", id="invalid-json"),
        pytest.param(
            '{"action_id":"synthetic-private-secret"}',
            "CandidateParseError",
            id="invalid-candidate",
        ),
    ],
)
def test_expected_parse_failure_continues_without_retry_and_preserves_evidence(
    cohort, monkeypatch, response, error_type
):
    calls = []
    evidence = {
        "returncode": 0,
        "events": [{"type": "turn.completed"}],
        "request_count": None,
        "tls_payload_observed": False,
    }

    def completed(**kwargs):
        calls.append((kwargs["case_id"], kwargs["condition"]))
        payload = json.loads(kwargs["prompt"].decode().splitlines()[-1])
        return {
            "response_text": response if len(calls) == 1 else json.dumps(payload["candidate"]),
            "tokens": {"input_tokens": 7},
            "tls_payload_observed": False,
            "evidence": evidence,
        }

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", completed)
    assert pilot.run() is True
    raw = (cohort / "results.json").read_text()
    result = json.loads(raw)
    rows = result["cases"]
    expected_pairs = [
        (case, condition) for case, _, _ in pilot.pilot_cases() for condition in pilot.CONDITIONS
    ]
    assert calls == expected_pairs
    assert [(row["case_id"], row["condition"]) for row in rows] == expected_pairs
    assert rows[0]["status"] == "FAILED"
    assert rows[0]["failure"] == {
        "type": error_type,
        "code": "evaluation_error",
        "transmission": "unknown",
    }
    assert "response_text" not in rows[0]
    assert rows[0]["response_sha256"] == hashlib.sha256(response.encode("utf-8")).hexdigest()
    assert rows[0]["response_bytes"] == len(response.encode("utf-8"))
    assert "synthetic-private-secret" not in raw
    assert rows[0]["tokens"] == {"input_tokens": 7}
    assert rows[0]["evidence"] == evidence
    assert rows[0]["evaluation"] is None
    assert all(row["status"] == "COMPLETED" for row in rows[1:])
    assert all(row["evaluation"]["final_gate_accepted"] is False for row in rows[1:])
    assert all(row["evaluation"]["objective_reached"] is False for row in rows[1:])
    assigned = len(pilot.pilot_cases())
    assert result["summary"] == {
        condition: {
            "assigned": assigned,
            "completed": assigned - (condition == rows[0]["condition"]),
            "failed": int(condition == rows[0]["condition"]),
            "pending": 0,
            "gate_accepted": 0,
            "objective_reached": 0,
        }
        for condition in pilot.CONDITIONS
    }
    status = json.loads((cohort / "status.json").read_text())
    assert status["status"] == "COMPLETED_WITH_FAILURES"
    assert (status["planned"], status["completed"], status["failed"], status["pending"]) == (
        len(expected_pairs),
        len(expected_pairs) - 1,
        1,
        0,
    )


@pytest.mark.parametrize(
    "response", [None, {"private": "synthetic-private-secret"}], ids=["null", "object"]
)
def test_unexpected_evaluator_type_error_stops_and_keeps_dispatch_evidence(
    cohort, monkeypatch, response
):
    calls = []
    evidence = {
        "returncode": 0,
        "events": [{"type": "turn.completed"}],
        "request_count": None,
        "tls_payload_observed": False,
    }

    def completed(**kwargs):
        calls.append(kwargs)
        return {
            "response_text": response,
            "tokens": {"input_tokens": 7},
            "tls_payload_observed": False,
            "evidence": evidence,
        }

    monkeypatch.setattr(pilot.codex_feedback_live_adapter, "dispatch", completed)
    assert pilot.run() is False
    raw = (cohort / "results.json").read_text()
    result = json.loads(raw)
    rows = result["cases"]
    assert len(calls) == 1
    assert rows[0]["status"] == "FAILED"
    assert rows[0]["failure"] == {
        "type": "TypeError",
        "code": "evaluation_error",
        "transmission": "unknown",
    }
    assert "response_text" not in rows[0]
    assert rows[0]["response_sha256"] is None
    assert rows[0]["response_bytes"] is None
    assert "synthetic-private-secret" not in raw
    assert rows[0]["tokens"] == {"input_tokens": 7}
    assert rows[0]["evidence"] == evidence
    assert rows[0]["evaluation"] is None
    assert all(row["status"] == "PENDING" for row in rows[1:])
    assigned = len(pilot.pilot_cases())
    assert result["summary"] == {
        condition: {
            "assigned": assigned,
            "completed": 0,
            "failed": int(condition == rows[0]["condition"]),
            "pending": assigned - (condition == rows[0]["condition"]),
            "gate_accepted": 0,
            "objective_reached": 0,
        }
        for condition in pilot.CONDITIONS
    }
    status = json.loads((cohort / "status.json").read_text())
    assert status["status"] == "STOPPED"
    assert (status["planned"], status["completed"], status["failed"], status["pending"]) == (
        len(rows),
        0,
        1,
        len(rows) - 1,
    )


def test_each_controller_receives_identical_complete_fixed_inputs():
    fixtures = comparison.fixtures()
    assert {case[0] for case in fixtures} == {"development", "held_out"}
    assert {case[1].state_id for case in fixtures if case[0] == "development"}.isdisjoint(
        case[1].state_id for case in fixtures if case[0] == "held_out"
    )
    for case in fixtures:
        split, state, candidate, _, _ = case
        initial, proposal = to_jsonable(state), to_jsonable(candidate)
        row = comparison.run_case(*case)
        assert row["split"] == split
        for result in row["conditions"].values():
            assert result["input_state"] == initial
            assert result["input_proposal"] == proposal
        assert to_jsonable(state) == initial
        assert to_jsonable(candidate) == proposal


def test_missing_oracle_does_not_become_a_safety_or_goal_judgment():
    _, state, candidate, _, _ = comparison.fixtures()[0]
    row = comparison.run_case("held_out", state, candidate)
    assert row["expectation"]["valid"] is None
    assert row["expectation"]["objective"] is None
    assert row["expectation"]["source"] is None
    for result in row["conditions"].values():
        assert result["safety_violation"] is None
        assert result["false_refusal"] is None
        assert result["objective_matches_expectation"] is None
    judged = comparison.run_case(*comparison.fixtures()[0])
    assert "scenario designer" in judged["expectation"]["source"]
    assert "not independently validated" in judged["expectation"]["source"]


def test_unsafe_success_and_safe_refusal_are_distinct(monkeypatch):
    _, state, candidate, _, _ = comparison.fixtures()[0]
    monkeypatch.setattr(comparison, "generic_accepts", lambda *_: True)
    result = comparison.run_case("held_out", state, candidate, False, False)["conditions"][
        "generic_rules"
    ]
    assert result["accepted"] is True
    assert result["safety_violation"] is True
    assert result["false_refusal"] is False
    assert isinstance(result["objective_reached"], bool)
    monkeypatch.setattr(comparison, "generic_accepts", lambda *_: False)
    result = comparison.run_case("held_out", state, candidate, True, False)["conditions"][
        "generic_rules"
    ]
    assert result["accepted"] is False
    assert result["safety_violation"] is False
    assert result["false_refusal"] is True
    assert result["objective_reached"] is False


def test_controller_failure_preserves_unknown_and_assigned_denominator(monkeypatch):
    case = comparison.fixtures()[0]

    def broken(*args):
        raise ValueError("fixture error")

    monkeypatch.setattr(comparison, "generic_accepts", broken)
    row = comparison.run_case(*case)
    result = row["conditions"]["generic_rules"]
    assert result["status"] == "FAILED"
    assert result["accepted"] is None
    assert result["safety_violation"] is None
    assert result["objective_reached"] is None
    summary = comparison.summarize([row])[case[0]]["generic_rules"]
    assert (summary["assigned"], summary["completed"], summary["failed"]) == (1, 0, 1)
    assert summary["safety_unknown"] == summary["objective_unknown"] == 1


def test_feedback_encodings_recover_identical_complete_signal_and_outcomes():
    cases = feedback.fixtures()
    assert {case[0] for case in cases} == {"development", "held_out"}
    for case in cases:
        _, state, candidate, _, _ = case
        row = feedback.run_case(*case)
        detailed = row["conditions"]["detailed"]
        generic = row["conditions"]["generic_with_details"]
        assert detailed["status"] == generic["status"] == "COMPLETED"
        assert detailed["input_state"] == generic["input_state"] == to_jsonable(state)
        assert detailed["input_proposal"] == generic["input_proposal"] == to_jsonable(candidate)
        assert detailed["decoded_signal"] == generic["decoded_signal"]
        assert detailed["signal"] == json.loads(generic["signal"]["details_json"])
        for field in ("outcome", "final_candidate", "final_state", "trace", "objective_reached"):
            assert detailed[field] == generic[field]
        for result in (detailed, generic):
            assert result["safety_violation"] is None
            assert result["false_refusal"] is None


def test_feedback_decode_failure_stays_unknown_and_counts_as_failed(monkeypatch):
    original = feedback.decode_feedback

    def broken(name, signal):
        if name == "generic_with_details":
            raise ValueError("invalid feedback")
        return original(name, signal)

    monkeypatch.setattr(feedback, "decode_feedback", broken)
    case = feedback.fixtures()[0]
    row = feedback.run_case(*case)
    result = row["conditions"]["generic_with_details"]
    assert result["status"] == "FAILED"
    assert result["outcome"] is None
    assert result["final_candidate"] is None
    assert result["objective_reached"] is None
    assert result["safety_violation"] is None
    summary = feedback.summarize([row])[case[0]]["generic_with_details"]
    assert (summary["assigned"], summary["completed"], summary["failed"]) == (1, 0, 1)
    assert summary["objective_unknown"] == summary["safety_unknown"] == 1
