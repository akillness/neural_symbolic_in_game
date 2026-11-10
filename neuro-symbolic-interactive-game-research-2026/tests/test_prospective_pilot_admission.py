"""Negative controls never dispatch an inference or mistake local claims for authority."""

from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nesy_game import prospective_pilot as pilot


def forbidden_process(*args, **kwargs):
    raise AssertionError("A blocked prospective study started a process")


@pytest.mark.parametrize(
    "evidence",
    [
        {},
        {"metadata": {"version": "0.164.0", "model": "gpt-6.1-sol", "effort": "medium"}},
        {
            "served_identity_verified": True,
            "subscription_no_additional_charge_verified": True,
            "public_input_egress": True,
            "isolation_verified": True,
        },
        {
            "billing": {
                "mode": "existing_credits_no_new_purchase",
                "automatic_reload": False,
                "available_quota": 1000000,
            }
        },
        {
            "activation": {
                "schema_version": "runtime-model-swap-native-activation/v1",
                "rows": 20,
                "public_input_egress": True,
                "existing_credit_consumption_authorized": True,
            }
        },
        {"identity_registry": {}, "response": {"model": "gpt-6.1-sol", "request_id": "copied"}},
    ],
)
def test_metadata_and_self_asserted_authority_cannot_admit_any_unit(evidence: dict) -> None:
    protocol = pilot.build_protocol()
    admission = pilot.evaluate_admission(protocol, evidence)
    result = pilot.collect(protocol, admission, process_factory=forbidden_process)
    assert result["native_process_starts"] == 0
    assert len(result["rows"]) == 180
    assert {row["unit_id"] for row in result["rows"]} == {
        row["unit_id"] for row in protocol["units"]
    }
    for row in result["rows"]:
        assert row["planned"] is True
        assert row["blocked_reasons"]
        assert row["admitted"] is False
        assert row["dispatch_attempts"] == row["native_process_starts"] == 0
        assert row["executed"] is False
        assert row["identity_qualified"] is False
        assert row["actual_engine"] is row["actual_model"] is None
        assert row["successful"] is None
    assert result["counts"] == {
        "planned": 180,
        "blocked": 180,
        "assigned": 0,
        "attempted": 0,
        "executed": 0,
    }


def test_all_missing_prerequisites_are_retained_not_only_first_failure() -> None:
    admission = pilot.evaluate_admission(pilot.build_protocol(), {})
    for row in admission["rows"]:
        assert {
            "BLOCKED_NO_CREDIT_ENFORCEMENT",
            "BLOCKED_IDENTITY_FORMAT_UNOBSERVED",
            "BLOCKED_ACTIVATION_ABSENT",
            "BLOCKED_PUBLIC_DERIVED_UNAPPROVED",
            "BLOCKED_ISOLATION_UNPROVEN",
            "BLOCKED_SCHEMA_ACCEPTANCE_UNOBSERVED",
            "BLOCKED_TASK_FREEZE_INCOMPLETE",
        } <= set(row["blocked_reasons"])


def test_unexpected_admission_still_cannot_reach_unimplemented_live_runner() -> None:
    protocol = pilot.build_protocol()
    admission = pilot.evaluate_admission(protocol, {})
    # This is an adversarial injected decision, not provider identity evidence.
    for row in admission["rows"]:
        row["admitted"] = True
        row["blocked_reasons"] = []
    result = pilot.collect(protocol, admission, process_factory=forbidden_process)
    assert result["native_process_starts"] == 0
    assert all(
        "BLOCKED_LIVE_PATH_NOT_IMPLEMENTED" in row["blocked_reasons"] for row in result["rows"]
    )
    assert all(not row["admitted"] and not row["executed"] for row in result["rows"])


@pytest.mark.parametrize("fault", ["identity", "authorization", "credit", "isolation", "schema"])
def test_trust_fault_halts_remaining_targets_and_both_tracks(fault: str) -> None:
    protocol = pilot.build_protocol()
    ledger = {
        "rows": [
            dict(unit, admitted=False, blocked_reasons=[], terminal_outcome=None)
            for unit in protocol["units"]
        ]
    }
    first = ledger["rows"][0]
    first["terminal_outcome"] = "failed"
    event = {"unit_id": first["unit_id"], "fault": fault}
    stopped = pilot.apply_stop_rule(copy.deepcopy(ledger), event)
    assert stopped["rows"][0]["terminal_outcome"] == "failed"
    assert stopped["halt"]["unit_id"] == first["unit_id"]
    assert all("BLOCKED_QUEUE_HALTED" in row["blocked_reasons"] for row in stopped["rows"][1:])
    assert {row["track"] for row in stopped["rows"][1:]} == {"runtime", "development"}
    assert pilot.apply_stop_rule(stopped, event) == stopped  # No replacement or activation reset.


@pytest.mark.parametrize("outcome", ["invalid_proposal", "timeout", "repairs_exhausted"])
def test_ordinary_task_failure_does_not_erase_or_halt_other_units(outcome: str) -> None:
    ledger = {
        "rows": [
            dict(unit, admitted=False, blocked_reasons=[], terminal_outcome=None)
            for unit in pilot.build_protocol()["units"]
        ]
    }
    ledger["rows"][0]["terminal_outcome"] = outcome
    assert (
        pilot.apply_stop_rule(
            copy.deepcopy(ledger), {"unit_id": ledger["rows"][0]["unit_id"], "fault": outcome}
        )
        == ledger
    )


def test_dynamic_public_closure_admits_own_history_without_preapproving_future_hashes(
    tmp_path: Path,
) -> None:
    public = tmp_path / "public.txt"
    public.write_text("public observation: gate held", encoding="utf-8")
    trust = tmp_path / "evaluator-only"
    trust.mkdir()
    manifest = {
        "files": [
            {
                "path": str(public),
                "classification": "PUBLIC_BLOB",
                "sha256": hashlib.sha256(public.read_bytes()).hexdigest(),
            }
        ]
    }
    ledger = {"programs": {"controller-v1": "a" * 64}, "approved": True}
    turn = {
        "program_id": "controller-v1",
        "program_sha256": "a" * 64,
        "inputs": [
            {"kind": "static", "path": str(public)},
            {"kind": "public_engine_observation", "value": {"gate": "held"}},
            {"kind": "remaining_budget", "value": {"tools": 62}},
            {"kind": "own_prior_output", "provider": "codex", "value": "read task; x=y"},
        ],
        "provider": "codex",
    }
    assert pilot.validate_turn(turn, manifest, ledger, trust)["status"] == "PASS"
    for bad in (
        dict(turn, program_sha256="b" * 64),
        dict(turn, inputs=[{"kind": "static", "path": str(trust / "answers.json")}]),
        dict(turn, inputs=[{"kind": "hidden_case", "value": "private oracle sentinel"}]),
        dict(
            turn,
            inputs=[{"kind": "own_prior_output", "provider": "antigravity", "value": "answer"}],
        ),
        dict(turn, inputs=[{"kind": "unclassified", "value": "extra facts"}]),
    ):
        with pytest.raises(ValueError):
            pilot.validate_turn(bad, manifest, ledger, trust)
    public.write_text("mutated protected source", encoding="utf-8")
    with pytest.raises(ValueError):
        pilot.validate_turn(turn, manifest, ledger, trust)


@pytest.mark.parametrize(
    "argv",
    [
        ["codex", "exec", "generate"],
        ["agy", "--print", "hello"],
        ["codex", "--version", "--model", "gpt-6.1-sol"],
    ],
)
def test_metadata_allowlist_refuses_generation_before_process_creation(argv: list[str]) -> None:
    with pytest.raises(ValueError):
        pilot.metadata_preflight(argv, process_factory=forbidden_process)


def test_host_neutral_identity_binding_is_attempt_bound_not_payload_bound() -> None:
    attempt = {
        "attempt_id": "controller-17",
        "pid": 123,
        "started": 10,
        "ended": 11,
        "stream_sha256": "c" * 64,
        "selector": "gpt-6.1-sol",
    }
    observation = {
        "channel": "provider",
        "attempt_id": "controller-17",
        "pid": 123,
        "started": 10,
        "ended": 11,
        "stream_sha256": "c" * 64,
        "identities": ["gpt-6.1-sol"],
        "markers": [],
    }
    # Engineering observation type only: this is NOT a real host adapter positive.
    assert pilot.bind_identity(observation, attempt) is True
    mutations = [
        {"channel": "model"},
        {"attempt_id": "controller-16"},
        {"pid": 124},
        {"started": 9},
        {"stream_sha256": "d" * 64},
        {"identities": []},
        {"identities": ["gpt-5.6-sol"]},
        {"identities": ["gpt-6.1-sol", "gpt-6.1-sol"]},
        {"identities": [None]},
        {"markers": ["reroute"]},
        {"markers": ["retry"]},
        {"markers": ["conflicting identity"]},
    ]
    for mutation in mutations:
        assert pilot.bind_identity(dict(observation, **mutation), attempt) is False
    assert (
        pilot.bind_identity(
            {
                "model": "gpt-6.1-sol",
                "identity_request_hash": "e" * 64,
                "outgoing_request_sha256": "e" * 64,
            },
            attempt,
        )
        is False
    )
