from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import run_runtime_model_swap_codex_exploratory as exploratory
import test_runtime_model_swap_native as native_tests

from nesy_game import runtime_model_swap_native as native_runtime
from nesy_game.npc_goal import GoalController, IntentInterpreter
from nesy_game.runtime_model_swap import EpisodeLimits, GodotEpisodeEngine, ModelSpec, run_episode
from nesy_game.runtime_model_swap_native import EXTENSION_ACTIVATION_SCHEMA, NativeActivationTrust


def _activation(representation: str = "general_rule", seed: int = 31) -> NativeActivationTrust:
    assignment_id = f"sealed-lighthouse-v1:gpt-6-luna:{representation}:repeat-1"
    return NativeActivationTrust(
        activation_sha256="a" * 64,
        plan_sha256="b" * 64,
        row_id=assignment_id,
        row_sha256="c" * 64,
        activation={
            "schema_version": EXTENSION_ACTIVATION_SCHEMA,
            "permissions": {"account": "read_only", "billing": "existing_credits_only"},
            "billing_policy": "existing_credits_no_new_purchase",
        },
        row={"assignment_id": assignment_id, "seed": seed, "representation": representation},
        purpose="test_simulation",
        origin="test_only",
    )


def _real_shaped_activation(
    representation: str = "general_rule",
    seed: int = 31,
    *,
    generated_assignment: bool = False,
    source_root: Path | None = None,
) -> NativeActivationTrust:
    assignment_id = (
        f"codex-selector-exploratory-{seed}-{representation}"
        if generated_assignment
        else f"sealed-lighthouse-v1:gpt-6-luna:{representation}:repeat-1"
    )
    return NativeActivationTrust(
        activation_sha256="a" * 64,
        plan_sha256="b" * 64,
        row_id=assignment_id,
        row_sha256="c" * 64,
        activation={
            "schema_version": EXTENSION_ACTIVATION_SCHEMA,
            "study_id": exploratory.STUDY_ID,
            "permissions": {
                "account": "read_only",
                "billing": "existing_credits_only",
                "existing_credit_consumption_authorized": True,
                "automatic_reload_off_verified": True,
                "native_account_match_verified": True,
                "new_credit_purchase_authorized": False,
                "api_key_fallback_authorized": False,
            },
            "billing_policy": "existing_credits_no_new_purchase",
            "artifact_bindings": {"allowed_requests": []},
        },
        row={
            "assignment_id": assignment_id,
            "seed": seed,
            "representation": representation,
            "target": {
                "family_label": "GPT-6-LUNA",
                "host": "codex",
                "selector": "gpt-6-luna",
                "effort": "medium",
            },
        },
        purpose="production_native",
        origin="trusted_bootstrap",
        source_root=str(source_root) if source_root is not None else None,
    )


def test_build_plan_is_deterministic_and_keeps_unknown_identity_out_of_science() -> None:
    first = exploratory.build_plan(
        model="gpt-6-luna", seed=17, max_dispatches=12, episode_timeout=180, response_timeout=60
    )
    second = exploratory.build_plan(
        model="gpt-6-luna", seed=17, max_dispatches=12, episode_timeout=180, response_timeout=60
    )

    assert first == second
    assert (
        first["config_hash"]
        == hashlib.sha256(
            json.dumps(
                {key: value for key, value in first.items() if key != "config_hash"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
    )
    assert [cell["representation"] for cell in first["cells"]] == ["general_rule", "ontology"]
    assert len({cell["assignment_id"] for cell in first["cells"]}) == 2
    assert all(cell["scientific_assignment"] is False for cell in first["cells"])
    assert first["target"]["requested_selector"] == "gpt-6-luna"
    assert first["provenance"]["provider_identity"] is None
    assert first["provenance"]["provider_revision"] is None
    assert first["provenance"]["identity_status"] == "unknown_until_provider_response"
    assert "not a strict native identity cohort" in first["claim_boundary"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_dispatches", 13, "max_dispatches_must_be_between_1_and_12"),
        ("max_dispatches", 0, "max_dispatches_must_be_between_1_and_12"),
        ("episode_timeout", 181, "episode_timeout_must_be_between_0_and_180_seconds"),
        ("episode_timeout", 0, "episode_timeout_must_be_between_0_and_180_seconds"),
        ("response_timeout", 61, "response_timeout_must_be_between_0_and_60_seconds"),
        ("response_timeout", 0, "response_timeout_must_be_between_0_and_60_seconds"),
    ],
)
def test_build_plan_rejects_limits_outside_frozen_bounds(
    field: str, value: int, message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        exploratory.build_plan(**{field: value})


def test_prelaunch_is_offline_and_fail_closed_when_codex_gate_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exploratory.shutil, "which", lambda _name: None)
    # Exercise the missing Codex gate, not an untracked operator approval packet.
    packet = tmp_path / "synthetic-frozen-packet"
    packet.mkdir()
    expected = {}
    for name, filename in (
        ("assignment_plan", "assignment-plan.json"),
        ("approved_scope", "approved-scope.json"),
    ):
        content = native_tests._canonical_bytes(
            {"artifact": name, "test_only": True, "live_dispatch_authorized": False}
        )
        (packet / filename).write_bytes(content)
        expected[name] = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr(exploratory, "FROZEN_PACKET", packet)
    monkeypatch.setattr(exploratory, "FROZEN_PACKET_EXPECTED", expected)
    result = exploratory.prelaunch_check(
        output_dir=tmp_path / "prelaunch", model="gpt-6-luna", seed=23
    )
    check = result["check"]

    assert check["status"] == "blocked"
    assert check["live_calls"] == 0
    assert check["subprocesses_started"] == 0
    assert check["credentials_read"] is False
    assert check["provider_identity"] is None
    assert check["provider_revision"] is None
    assert check["frozen_packet_drift"] == []
    assert check["missing_source_artifacts"] == []
    assert check["codex_binary_available"] is False
    assert (tmp_path / "prelaunch" / "admission-plan.json").is_file()
    assert (tmp_path / "prelaunch" / "prelaunch-check.json").is_file()


def test_execute_cli_fails_closed_before_output_or_subprocess_without_activation_inputs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "execute"
    code = exploratory.main(["--execute", "--admit-exploratory", "--output-dir", str(output)])
    payload = json.loads(capsys.readouterr().out)

    assert code == 2
    assert payload["status"] == "blocked"
    assert payload["live_calls"] == 0
    assert "fresh_activation_plan_account_gate_inputs_required" in payload["failure_reason"]
    assert not output.exists()


def test_prelaunch_fails_closed_on_frozen_packet_drift_even_when_codex_is_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(exploratory.shutil, "which", lambda _name: "/usr/bin/codex")
    monkeypatch.setattr(exploratory, "FROZEN_PACKET_EXPECTED", {"assignment_plan": "0" * 64})

    result = exploratory.prelaunch_check(output_dir=tmp_path / "drift", model="gpt-6-luna", seed=24)

    assert result["check"]["status"] == "blocked"
    assert result["check"]["live_calls"] == 0
    assert "assignment_plan" in result["check"]["frozen_packet_drift"]


def test_cell_rejects_missing_or_mismatched_activation_before_creating_output(
    tmp_path: Path,
) -> None:
    output = tmp_path / "cell"
    with pytest.raises(
        exploratory.ExploratoryActivationRequired, match="fresh_activation_row_mismatch"
    ):
        exploratory.run_exploratory_cell(
            output_dir=output,
            representation="ontology",
            seed=31,
            trusted_activation=_activation("general_rule"),
        )
    assert not output.exists()


def test_codex_runner_uses_exec_path_zero_retries_and_observed_process_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, production_boundary: dict[str, Any]
) -> None:
    activation = production_boundary["capability"]
    home = tmp_path / "transport-home"
    auth = home / ".codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("synthetic-secret", encoding="utf-8")
    captured: dict[str, Any] = {}

    monkeypatch.setattr(exploratory, "_sanitized_environment", lambda: {"HOME": str(home)})

    def fake_host(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        kwargs["on_started"]()
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_last = Path(command[command.index("--output-last-message") + 1])
        output_last.write_text(json.dumps({"request_id": "req-1"}), encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(exploratory, "run_host_process", fake_host)
    runner = exploratory.CodexSelectorPromptRunner(
        selector="gpt-6-luna",
        trusted_activation=activation,
        native_context=production_boundary["context"],
        expected_assignment_id=activation.row["assignment_id"],
        expected_config_hash="config-hash",
        expected_representation="general_rule",
        expected_seed=activation.row["seed"],
        expected_fixture_ref=activation.row["fixture_id"],
    )
    result = runner(**_bound_transport_request(production_boundary, "req-1"))

    receipt = result.receipt
    command = captured["command"]
    assert result.returncode == 0
    assert command[:4] == ["codex", "exec", "--json", "--strict-config"]
    assert command[command.index("--model") + 1] == "gpt-6-luna"
    assert receipt["requested_selector"] == "gpt-6-luna"
    assert receipt["provider_identity"] is None
    assert receipt["identity_status"] == "unknown"
    assert receipt["provider_retries"] == 0
    assert receipt["dispatch_started"] is True
    assert receipt["local_process_started"] is True
    assert receipt["provider_request_count"] is None
    assert receipt["provider_request_count_authoritative"] is False
    assert receipt["provider_request_count_ambiguous"] is True
    assert (
        receipt["provider_request_count_basis"]
        == "transport_process_only_no_authoritative_provider_evidence"
    )
    assert receipt["cost_usd"] is None
    assert "synthetic-secret" not in json.dumps(receipt, sort_keys=True)
    assert all(str(home) not in value for value in receipt["command"])
    assert all(str(ROOT) not in value for value in receipt["command"])


def test_codex_runner_missing_account_gate_is_authorization_failure_without_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, production_boundary: dict[str, Any]
) -> None:
    activation = production_boundary["capability"]
    monkeypatch.setattr(
        exploratory, "_sanitized_environment", lambda: {"HOME": str(tmp_path / "no-home")}
    )
    host_calls: list[Any] = []
    monkeypatch.setattr(
        exploratory, "run_host_process", lambda *args, **kwargs: host_calls.append(args) or None
    )
    runner = exploratory.CodexSelectorPromptRunner(
        selector="gpt-6-luna",
        trusted_activation=activation,
        native_context=production_boundary["context"],
        expected_assignment_id=activation.row["assignment_id"],
        expected_config_hash="config-hash",
        expected_representation="general_rule",
        expected_seed=activation.row["seed"],
        expected_fixture_ref=activation.row["fixture_id"],
    )

    result = runner(**_bound_transport_request(production_boundary, "req-2"))

    assert result.returncode == 2
    assert result.receipt["failure_kind"] == "authorization"
    assert result.receipt["error"] == "codex_auth_unavailable"
    assert result.receipt["local_process_started"] is False
    assert result.receipt["provider_retries"] == 0
    assert host_calls == []


def test_codex_runner_retains_failed_process_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, production_boundary: dict[str, Any]
) -> None:
    activation = production_boundary["capability"]
    home = tmp_path / "transport-home"
    auth = home / ".codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("synthetic-secret", encoding="utf-8")
    monkeypatch.setattr(exploratory, "_sanitized_environment", lambda: {"HOME": str(home)})

    def failed_host(command: list[str], **_kwargs: Any) -> subprocess.CompletedProcess[str]:
        _kwargs["on_started"]()
        return subprocess.CompletedProcess(command, 7, "", "synthetic host failure")

    monkeypatch.setattr(exploratory, "run_host_process", failed_host)
    runner = exploratory.CodexSelectorPromptRunner(
        selector="gpt-6-luna",
        trusted_activation=activation,
        native_context=production_boundary["context"],
        expected_assignment_id=activation.row["assignment_id"],
        expected_config_hash="config-hash",
        expected_representation="general_rule",
        expected_seed=activation.row["seed"],
        expected_fixture_ref=activation.row["fixture_id"],
    )
    result = runner(**_bound_transport_request(production_boundary, "failed-request"))

    assert result.returncode == 7
    assert result.receipt["failure_kind"] == "logical"
    assert result.receipt["provider_request_count"] is None
    assert result.receipt["provider_request_count_authoritative"] is False
    assert result.receipt["local_process_started"] is True
    assert runner.prompt_receipts[-1]["returncode"] == 7
    assert result.receipt["provider_request_count_ambiguous"] is True
    assert (
        result.receipt["provider_request_count_basis"]
        == "transport_process_only_no_authoritative_provider_evidence"
    )


def test_codex_runner_retains_timeout_receipt_without_retry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, production_boundary: dict[str, Any]
) -> None:
    activation = production_boundary["capability"]
    home = tmp_path / "transport-home"
    auth = home / ".codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("synthetic-secret", encoding="utf-8")
    monkeypatch.setattr(exploratory, "_sanitized_environment", lambda: {"HOME": str(home)})

    def timeout_host(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        kwargs["on_started"]()
        raise subprocess.TimeoutExpired(
            command, kwargs["timeout"], output="partial", stderr="timed out"
        )

    monkeypatch.setattr(exploratory, "run_host_process", timeout_host)
    runner = exploratory.CodexSelectorPromptRunner(
        selector="gpt-6-luna",
        trusted_activation=activation,
        native_context=production_boundary["context"],
        expected_assignment_id=activation.row["assignment_id"],
        expected_config_hash="config-hash",
        expected_representation="general_rule",
        expected_seed=activation.row["seed"],
        expected_fixture_ref=activation.row["fixture_id"],
    )
    result = runner(**_bound_transport_request(production_boundary, "timeout-request"))

    assert result.returncode == 124
    assert result.receipt["failure_kind"] == "timeout"
    assert result.receipt["timed_out"] is True
    assert result.receipt["provider_retries"] == 0
    assert runner.prompt_receipts[-1]["timed_out"] is True


def test_real_activation_family_label_accepts_and_preserves_distinct_exploratory_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, simulation_boundary: dict[str, Any]
) -> None:
    activation = simulation_boundary["capability"]
    monkeypatch.setattr(exploratory, "PROMPT", "fixture prompt")
    monkeypatch.setattr(exploratory, "FIXTURE_REF", activation.row["fixture_id"])
    monkeypatch.setattr(
        exploratory, "stage_project", lambda _source, destination: destination.mkdir()
    )

    class FakeEngine:
        def __init__(self, **_kwargs: Any) -> None:
            self.propose = lambda _state: {}
            self.repair = lambda _state, _proposal, _error, _attempt: {}

    monkeypatch.setattr(exploratory, "GodotEpisodeEngine", FakeEngine)

    def fake_run_episode(**kwargs: Any) -> dict[str, Any]:
        return {
            "model": {"model_id": "gpt-6-luna", "representation": "general_rule"},
            "status": "failure",
            "success": False,
            "goal_reached": False,
            "failure_reason": "synthetic_engine_failure",
            "evidence": {"prompt_receipts": []},
            "config": kwargs["config"],
        }

    monkeypatch.setattr(exploratory, "run_episode", fake_run_episode)
    result = exploratory.run_exploratory_cell(
        output_dir=tmp_path / "cell",
        representation="general_rule",
        seed=activation.row["seed"],
        trusted_activation=activation,
        process_runner=lambda *_args, **_kwargs: pytest.fail("unexpected host dispatch"),
        native_context=simulation_boundary["context"],
        exploratory_plan_hash="d" * 64,
    )

    assert result["config"]["assignment_id"] == (
        f"codex-selector-exploratory-{activation.row['seed']}-general_rule"
    )
    assert result["config"]["authorization_row_id"] == activation.row_id
    assert result["config"]["assignment_id"] != result["config"]["authorization_row_id"]
    assert (tmp_path / "cell" / "episode.json").is_file()


def test_strict_activation_row_cannot_masquerade_as_fresh_exploratory_assignment(
    tmp_path: Path,
) -> None:
    activation = _real_shaped_activation(seed=41, generated_assignment=True)

    with pytest.raises(
        exploratory.ExploratoryActivationRequired, match="exploratory_assignment_must_be_distinct"
    ):
        exploratory.run_exploratory_cell(
            output_dir=tmp_path / "cell",
            representation="general_rule",
            seed=41,
            trusted_activation=activation,
            exploratory_plan_hash="d" * 64,
        )
    assert not (tmp_path / "cell").exists()


def test_real_activation_rejects_non_string_family_label_before_output(tmp_path: Path) -> None:
    activation = _real_shaped_activation(seed=41)
    activation.row["target"]["family_label"] = 6

    with pytest.raises(
        exploratory.ExploratoryActivationRequired, match="fresh_activation_family_label_invalid"
    ):
        exploratory.run_exploratory_cell(
            output_dir=tmp_path / "cell",
            representation="general_rule",
            seed=41,
            trusted_activation=activation,
            exploratory_plan_hash="d" * 64,
        )
    assert not (tmp_path / "cell").exists()


def _execute_args(tmp_path: Path) -> SimpleNamespace:
    contexts = [tmp_path / "context-general.json", tmp_path / "context-ontology.json"]
    for path in contexts:
        path.write_text("{}", encoding="utf-8")
    return SimpleNamespace(
        model="gpt-6-luna",
        seed=41,
        max_dispatches=12,
        episode_timeout=180.0,
        response_timeout=60.0,
        activation_path=[Path("activation-general.json"), Path("activation-ontology.json")],
        activation_sha256=["a" * 64, "b" * 64],
        native_context=contexts,
        plan_path=Path("plan.json"),
        plan_sha256="b" * 64,
        row_id=["strict-row-general", "strict-row-ontology"],
        trust_root=Path("trust-root"),
        source_root=Path("source-root"),
    )


def test_execute_cells_preserves_partial_failure_and_writes_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = _execute_args(tmp_path)
    monkeypatch.setattr(
        exploratory,
        "load_pinned_native_activation",
        lambda **_kwargs: _real_shaped_activation(source_root=tmp_path),
    )

    def synthetic_cell(**kwargs: Any) -> dict[str, Any]:
        if kwargs["representation"] == "general_rule":
            raise RuntimeError("synthetic cell failure")
        return {
            "assignment_id": f"codex-selector-exploratory-{args.seed}-ontology",
            "authorization_row_id": args.row_id[1],
            "model": {"representation": "ontology"},
            "status": "failure",
            "failure_reason": "second synthetic failure",
            "evidence": {"provider_request_count": None},
        }

    monkeypatch.setattr(exploratory, "run_exploratory_cell", synthetic_cell)
    summary = exploratory._execute_cells(args, tmp_path / "execution")

    assert summary["records"][0]["status"] == "failure"
    assert summary["records"][0]["failure_reason"].startswith(
        "RuntimeError: synthetic cell failure"
    )
    assert summary["records"][1]["status"] == "failure"
    assert summary["live_calls"] is None
    assert summary["live_calls_ambiguous"] is True
    assert (tmp_path / "execution" / "general_rule" / "episode.json").is_file()
    assert (tmp_path / "execution" / "execution-summary.json").is_file()


def test_execute_cells_total_cap_one_never_dispatches_second_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = _execute_args(tmp_path)
    args.max_dispatches = 1
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(
        exploratory,
        "load_pinned_native_activation",
        lambda **_kwargs: _real_shaped_activation(source_root=tmp_path),
    )

    def synthetic_cell(**kwargs: Any) -> dict[str, Any]:
        calls.append((kwargs["representation"], kwargs["max_dispatches"]))
        return {
            "assignment_id": f"codex-selector-exploratory-{args.seed}-{kwargs['representation']}",
            "authorization_row_id": args.row_id[0],
            "model": {"representation": kwargs["representation"]},
            "status": "failure",
            "failure_reason": "synthetic failure",
            "evidence": {"provider_request_count": None},
        }

    monkeypatch.setattr(exploratory, "run_exploratory_cell", synthetic_cell)
    summary = exploratory._execute_cells(args, tmp_path / "execution")

    assert summary["cell_dispatch_caps"] == [1, 0]
    assert calls == [("general_rule", 1)]
    assert summary["records"][1]["failure_reason"] == "host_dispatch_budget_exhausted"
    assert summary["live_calls"] is None
    assert summary["live_calls_ambiguous"] is True


def test_real_run_episode_accepts_family_label_and_bridges_auth_row_to_prompt(
    tmp_path: Path,
) -> None:
    activation = _real_shaped_activation(seed=41)
    assignment_id = "codex-selector-exploratory-41-general_rule"
    config = {
        "assignment_id": assignment_id,
        "authorization_row_id": activation.row_id,
        "exploratory_plan_hash": "d" * 64,
        "execution_mode": "configured_selector_exploratory",
        "model_selector": "gpt-6-luna",
        "effort": "medium",
    }
    config_hash = hashlib.sha256(
        json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    limits = EpisodeLimits(wall_seconds=180.0, response_seconds=60.0, max_host_calls=1)
    prompt_calls: list[dict[str, Any]] = []

    def prompt_runner(**kwargs: Any) -> tuple[int, dict[str, Any]]:
        prompt_calls.append(dict(kwargs))
        return 0, {
            "request_id": kwargs["request_id"],
            "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
        }

    engine = GodotEpisodeEngine(
        project=tmp_path / "project",
        output_root=tmp_path / "output",
        prompt_runner=prompt_runner,
        engine_runner=lambda **_kwargs: {"status": "completed"},
        godot_binary="synthetic-godot",
        fixture_ref=exploratory.FIXTURE_REF,
        seed=41,
        assignment_id=assignment_id,
    )
    engine._prepared = True
    engine._snapshot = {
        "state_ref": {"revision": 0, "sha256": "0" * 64},
        "observation": {
            "lens_reachable": True,
            "lens_carried": False,
            "signal_restored": False,
            "tide_lead_authorized": False,
            "goal_reached": False,
            "in_dialogue": False,
        },
    }
    engine._policy_hash = "b" * 64
    engine._controller = GoalController(
        interpreter=IntentInterpreter(arm="P", prompt_runner=engine._observed_prompt),
        budget=engine._budget(),
        session_ttl_seconds=180.0,
    )
    gate = {
        "mode": "configured_selector_exploratory",
        "ready": True,
        "requested_selector": "gpt-6-luna",
        "assignment_id": assignment_id,
        "authorization_row_id": activation.row_id,
        "exploratory_plan_hash": config["exploratory_plan_hash"],
        "config_hash": config_hash,
        "prompt_hash": hashlib.sha256(exploratory.PROMPT.encode("utf-8")).hexdigest(),
        "max_host_dispatches": 1,
        "response_seconds": 60.0,
        "provider_retries": 0,
        "raw_credentials_persisted": False,
        "activation_sha256": activation.activation_sha256,
        "plan_sha256": activation.plan_sha256,
        "row_sha256": activation.row_sha256,
        "row_id": activation.row_id,
        "activation_study_id": exploratory.STUDY_ID,
        "account_gate": activation.activation["permissions"],
        "billing_policy": activation.activation["billing_policy"],
    }

    record = run_episode(
        engine=engine,
        proposal_source=engine.propose,
        repair_source=engine.repair,
        model=ModelSpec(
            "gpt-6-luna", "general_rule", provider="codex", revision=None, offline=False
        ),
        limits=limits,
        seed=41,
        clock=lambda: 0.0,
        config=config,
        prompt=exploratory.PROMPT,
        trusted_activation=activation,
        exploratory_context=gate,
    )

    assert record["failure_reason"] == "commit_failure"
    assert prompt_calls, record
    assert prompt_calls[0]["assignment_id"] == assignment_id
    assert prompt_calls[0]["row_id"] == activation.row_id
    assert record["config"]["assignment_id"] == assignment_id
    assert record["config"]["authorization_row_id"] == activation.row_id
    assert record["evidence"]["exploratory_admission"]["authorization_row_id"] == activation.row_id


def test_real_run_episode_rejects_mismatched_family_target_before_prompt(tmp_path: Path) -> None:
    activation = _real_shaped_activation(seed=41)
    activation.row["target"]["selector"] = "wrong-selector"
    assignment_id = "codex-selector-exploratory-41-general_rule"
    config = {
        "assignment_id": assignment_id,
        "authorization_row_id": activation.row_id,
        "exploratory_plan_hash": "d" * 64,
        "execution_mode": "configured_selector_exploratory",
        "model_selector": "gpt-6-luna",
        "effort": "medium",
    }
    config_hash = hashlib.sha256(
        json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()
    prompt_calls: list[dict[str, Any]] = []

    def prompt_runner(**kwargs: Any) -> tuple[int, dict[str, Any]]:
        prompt_calls.append(dict(kwargs))
        return 0, {}

    limits = EpisodeLimits(wall_seconds=180.0, response_seconds=60.0, max_host_calls=1)
    engine = GodotEpisodeEngine(
        project=tmp_path / "project",
        output_root=tmp_path / "output",
        prompt_runner=prompt_runner,
        engine_runner=lambda **_kwargs: {"status": "completed"},
        godot_binary="synthetic-godot",
        fixture_ref=exploratory.FIXTURE_REF,
        seed=41,
        assignment_id=assignment_id,
    )
    record = run_episode(
        engine=engine,
        proposal_source=engine.propose,
        repair_source=engine.repair,
        model=ModelSpec(
            "gpt-6-luna", "general_rule", provider="codex", revision=None, offline=False
        ),
        limits=limits,
        seed=41,
        clock=lambda: 0.0,
        config=config,
        prompt=exploratory.PROMPT,
        trusted_activation=activation,
        exploratory_context={
            "mode": "configured_selector_exploratory",
            "ready": True,
            "requested_selector": "gpt-6-luna",
            "assignment_id": assignment_id,
            "authorization_row_id": activation.row_id,
            "exploratory_plan_hash": config["exploratory_plan_hash"],
            "config_hash": config_hash,
            "prompt_hash": hashlib.sha256(exploratory.PROMPT.encode("utf-8")).hexdigest(),
            "max_host_dispatches": 1,
            "response_seconds": 60.0,
            "provider_retries": 0,
            "raw_credentials_persisted": False,
            "activation_sha256": activation.activation_sha256,
            "plan_sha256": activation.plan_sha256,
            "row_sha256": activation.row_sha256,
            "row_id": activation.row_id,
            "activation_study_id": exploratory.STUDY_ID,
            "account_gate": activation.activation["permissions"],
            "billing_policy": activation.activation["billing_policy"],
        },
    )

    assert record["failure_reason"] == "exploratory_activation_target_mismatch"
    assert not prompt_calls


def test_execute_cells_rejects_missing_activation_pair_before_output(tmp_path: Path) -> None:
    args = _execute_args(tmp_path)
    args.activation_path = [Path("activation-general.json")]
    args.activation_sha256 = ["a" * 64]

    with pytest.raises(
        exploratory.ExploratoryActivationRequired,
        match="fresh_activation_plan_account_gate_inputs_required",
    ):
        exploratory._execute_cells(args, tmp_path / "execution")
    assert not (tmp_path / "execution").exists()


def test_execute_cells_misordered_activation_pairs_fail_closed_per_cell(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = _execute_args(tmp_path)
    general = _real_shaped_activation("general_rule", seed=args.seed, source_root=tmp_path)
    ontology = _real_shaped_activation("ontology", seed=args.seed, source_root=tmp_path)
    ontology.row["representation"] = "general_rule"
    general.row["representation"] = "ontology"
    args.row_id = [general.row_id, ontology.row_id]
    args.activation_path = [Path("activation-ontology.json"), Path("activation-general.json")]
    args.activation_sha256 = [ontology.activation_sha256, general.activation_sha256]
    loader_calls: list[tuple[Path, str]] = []

    def swapped_loader(**kwargs: Any) -> NativeActivationTrust:
        path = Path(kwargs["activation_path"])
        loader_calls.append((path, kwargs["row_id"]))
        return ontology if path.name == "activation-ontology.json" else general

    monkeypatch.setattr(exploratory, "load_pinned_native_activation", swapped_loader)
    summary = exploratory._execute_cells(args, tmp_path / "execution")

    assert loader_calls == [
        (Path("activation-ontology.json"), general.row_id),
        (Path("activation-general.json"), ontology.row_id),
    ]
    assert [row["failure_reason"] for row in summary["records"]] == [
        "ExploratoryActivationRequired: fresh_activation_cell_mismatch",
        "ExploratoryActivationRequired: fresh_activation_cell_mismatch",
    ]
    assert summary["records"][0]["authorization_row_id"] == general.row_id
    assert summary["records"][1]["authorization_row_id"] == ontology.row_id


def _bind_exploratory_entrypoint(bundle: dict[str, Any], content: bytes) -> None:
    """Re-pin the whole approval chain, not just a synthetic manifest hash."""
    relative = "scripts/run_runtime_model_swap_codex_exploratory.py"
    path = bundle["source_root"] / relative
    path.parent.mkdir(parents=True)
    path.write_bytes(content)
    manifest_path = bundle["source_root"] / "bound/source_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"].append(
        {"path": relative, "sha256": hashlib.sha256(content).hexdigest(), "role": "controller"}
    )
    manifest_bytes = native_tests._canonical_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    digest = hashlib.sha256(manifest_bytes).hexdigest()
    context = bundle["context"]
    context["hashes"]["source_manifest_sha256"] = digest
    context["bound_files"]["source_manifest"]["sha256"] = digest
    native_tests._rebind_native_evidence(
        bundle["source_root"], context, source_manifest_sha256=digest
    )
    for row in bundle["plan"]["rows"]:
        row["source_manifest_sha256"] = digest
    plan_bytes = native_tests._canonical_bytes(bundle["plan"])
    bundle["plan_path"].write_bytes(plan_bytes)
    bundle["plan_sha256"] = hashlib.sha256(plan_bytes).hexdigest()
    activation = bundle["activation"]
    activation["plan"]["sha256"] = bundle["plan_sha256"]
    activation["plan"]["row_sha256"] = hashlib.sha256(
        native_tests._canonical_bytes(bundle["row"])
    ).hexdigest()
    activation["artifact_bindings"]["source_manifest_sha256"] = digest
    for name in ("public_input", "identity_setting", "context_isolation", "subscription"):
        activation["evidence_digests"][f"{name}_receipt_sha256"] = context["evidence"][name][
            "receipt_artifact"
        ]["sha256"]


@pytest.fixture
def production_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> dict[str, Any]:
    """Pin real authorization artifacts while replacing only the host and wall clock."""
    now = [datetime(2026, 10, 25, 12, tzinfo=UTC)]
    monkeypatch.setattr(native_runtime, "_now_value", lambda _value=None: now[0])
    bundle = native_tests._apply_existing_credit_policy(
        native_tests._production_bundle(tmp_path / "fixture", extension=True)
    )
    entrypoint = getattr(request, "param", "current")
    if entrypoint != "missing":
        content = (
            Path(exploratory.__file__).read_bytes()
            if entrypoint == "current"
            else b"different approved exploratory implementation\n"
        )
        _bind_exploratory_entrypoint(bundle, content)
    bundle["activation_path"].write_bytes(native_tests._canonical_bytes(bundle["activation"]))
    bundle["activation_sha256"] = hashlib.sha256(bundle["activation_path"].read_bytes()).hexdigest()
    bundle["context_path"].write_bytes(native_tests._canonical_bytes(bundle["context"]))
    bundle["capability"] = native_runtime.load_pinned_native_activation(
        activation_path=bundle["activation_path"],
        activation_sha256=bundle["activation_sha256"],
        plan_path=bundle["plan_path"],
        plan_sha256=bundle["plan_sha256"],
        row_id=bundle["row"]["planned_id"],
        purpose="production_native",
        origin="trusted_bootstrap",
        trust_root=bundle["trust_root"],
        source_root=bundle["source_root"],
    )
    home = tmp_path / "home"
    auth = home / ".codex" / "auth.json"
    auth.parent.mkdir(parents=True)
    auth.write_text("{}", encoding="utf-8")
    for module in (exploratory, native_runtime):
        monkeypatch.setattr(module, "_sanitized_environment", lambda: {"HOME": str(home)})
    calls: list[dict[str, Any]] = []

    def fake_host(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append({"command": command, **kwargs})
        if kwargs.get("on_started") is not None:
            kwargs["on_started"]()
        payload = {"request_id": f"request-{len(calls)}", "action": "finish"}
        Path(command[command.index("--output-last-message") + 1]).write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": json.dumps(payload)},
                }
            ),
            native_tests.ProviderIdentityAdmissionTests._MATCH + "\n",
        )

    for module in (exploratory, native_runtime):
        monkeypatch.setattr(module, "run_host_process", fake_host)
    return {**bundle, "now": now, "host_calls": calls, "tmp_path": tmp_path}


def _production_selector_runner(bundle: dict[str, Any]) -> exploratory.CodexSelectorPromptRunner:
    row = bundle["row"]
    return exploratory.CodexSelectorPromptRunner(
        selector="gpt-6-luna",
        trusted_activation=bundle["capability"],
        native_context=bundle["context"],
        expected_assignment_id=f"codex-selector-exploratory-{row['seed']}-{row['representation']}",
        expected_config_hash="d" * 64,
        max_dispatches=2,
        expected_representation=row["representation"],
        expected_seed=row["seed"],
        expected_fixture_ref=row["fixture_id"],
    )


def _production_request(
    bundle: dict[str, Any], *, output: str, request_id: str, prompt: str = "fixture prompt"
) -> dict[str, Any]:
    output_dir = bundle["tmp_path"] / output
    output_dir.mkdir()
    schema = output_dir / "output-schema.json"
    schema.write_bytes((bundle["source_root"] / "bound/output-schema.json").read_bytes())
    row = bundle["row"]
    bindings = bundle["activation"]["artifact_bindings"]
    return {
        "request_id": request_id,
        "model": "gpt-6-luna",
        "assignment_id": f"codex-selector-exploratory-{row['seed']}-{row['representation']}",
        "row_id": row["assignment_id"],
        "config_hash": "d" * 64,
        "instruction": prompt,
        "user_prompt": prompt,
        "output_schema": schema,
        "output_schema_sha256": bindings["output_schema_sha256"],
        "allowed_requests_sha256": bindings["allowed_requests_sha256"],
        "quest_id": row["quest_id"],
        "seed": row["seed"],
        "repeat": row["repeat"],
        "reset": row["reset"],
        "fixture_id": row["fixture_id"],
        "fixture_sha256": row["fixture_sha256"],
        "oracle_sha256": row["oracle_sha256"],
        "representation": row["representation"],
        "timeout": 1,
    }


@pytest.mark.parametrize("first_path", ["exploratory", "native"])
def test_production_activation_cannot_replay_from_fresh_runner_output(
    production_boundary: dict[str, Any], first_path: str
) -> None:
    bundle = production_boundary
    request = _production_request(bundle, output="first-output", request_id="request-1")
    if first_path == "native":
        first = native_runtime.NativePromptRunner(
            host="codex",
            selector="gpt-6-luna",
            effort="medium",
            native_context=bundle["context"],
            trusted_activation=bundle["capability"],
        )
    else:
        first = _production_selector_runner(bundle)
    assert first(**request).returncode == 0
    bundle["capability"] = native_runtime.load_pinned_native_activation(
        activation_path=bundle["activation_path"],
        activation_sha256=bundle["activation_sha256"],
        plan_path=bundle["plan_path"],
        plan_sha256=bundle["plan_sha256"],
        row_id=bundle["row"]["planned_id"],
        purpose="production_native",
        origin="trusted_bootstrap",
        trust_root=bundle["trust_root"],
        source_root=bundle["source_root"],
    )
    second = _production_selector_runner(bundle)
    denied = second(
        **_production_request(bundle, output="fresh-second-output", request_id="request-2")
    )
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert "native_activation_row_already_claimed" in json.dumps(denied.receipt)
    assert len(bundle["host_calls"]) == 1


@pytest.mark.parametrize("drift", ["manifest", "listed-source"])
def test_production_source_drift_after_loading_blocks_exploratory_process(
    production_boundary: dict[str, Any], drift: str
) -> None:
    bundle = production_boundary
    runner = _production_selector_runner(bundle)
    source = "source_manifest.json" if drift == "manifest" else "public-controller.gd"
    (bundle["source_root"] / "bound" / source).write_text("changed after pinning\n")
    denied = runner(**_production_request(bundle, output="drift-output", request_id="request-1"))
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert bundle["host_calls"] == []


@pytest.mark.parametrize("prior_dispatch", [False, True], ids=["after-load", "between-dispatches"])
def test_production_expiry_after_loading_blocks_exploratory_process(
    production_boundary: dict[str, Any], prior_dispatch: bool
) -> None:
    bundle = production_boundary
    runner = _production_selector_runner(bundle)
    if prior_dispatch:
        assert (
            runner(
                **_production_request(bundle, output="before-expiry", request_id="request-1")
            ).returncode
            == 0
        )
    bundle["now"][0] = datetime(2026, 10, 26, tzinfo=UTC)
    denied = runner(
        **_production_request(
            bundle, output="at-expiry", request_id="request-2" if prior_dispatch else "request-1"
        )
    )
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert "expir" in json.dumps(denied.receipt)
    assert len(bundle["host_calls"]) == int(prior_dispatch)


def test_production_claim_allows_multiple_exact_bound_requests_in_one_runner(
    production_boundary: dict[str, Any],
) -> None:
    bundle = production_boundary
    runner = _production_selector_runner(bundle)
    for index, prompt in enumerate(("fixture prompt", "fixture prompt second"), start=1):
        result = runner(
            **_production_request(
                bundle, output=f"allowed-{index}", request_id=f"request-{index}", prompt=prompt
            )
        )
        assert result.returncode == 0, result.receipt
        assert result.payload == {"request_id": f"request-{index}", "action": "finish"}
        assert result.receipt["identity_status"] == "unknown"
        assert result.receipt["scientific_eligible"] is False
    denied = runner(**_production_request(bundle, output="over-budget", request_id="request-3"))
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert denied.receipt["error"] == "native_extension_dispatch_limit"
    assert len(bundle["host_calls"]) == 2


def test_production_exploratory_rejects_crossed_allowed_request_tuple(
    production_boundary: dict[str, Any],
) -> None:
    bundle = production_boundary
    runner = _production_selector_runner(bundle)
    request = _production_request(bundle, output="crossed-tuple", request_id="request-1")
    request["user_prompt"] = "fixture prompt second"
    denied = runner(**request)
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert denied.receipt["error"] == "outgoing_request_tuple_not_bound"
    assert bundle["host_calls"] == []


@pytest.fixture
def simulation_boundary(production_boundary: dict[str, Any]) -> dict[str, Any]:
    bundle = production_boundary
    bundle["capability"] = native_runtime.load_pinned_native_activation(
        activation_path=bundle["activation_path"],
        activation_sha256=bundle["activation_sha256"],
        plan_path=bundle["plan_path"],
        plan_sha256=bundle["plan_sha256"],
        row_id=bundle["row"]["planned_id"],
        purpose="test_simulation",
        origin="test_only",
        trust_root=bundle["trust_root"],
        source_root=bundle["source_root"],
    )
    return bundle


def _bound_transport_request(bundle: dict[str, Any], request_id: str) -> dict[str, Any]:
    request = _production_request(bundle, output="transport-output", request_id=request_id)
    request.update(assignment_id=bundle["capability"].row_id, config_hash="config-hash")
    return request


def test_production_exploratory_requires_source_bound_native_context(
    production_boundary: dict[str, Any],
) -> None:
    bundle = production_boundary
    runner = _production_selector_runner({**bundle, "context": None})
    denied = runner(**_production_request(bundle, output="missing-context", request_id="request-1"))
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert denied.receipt["error"] == "native_context_rejected"
    assert bundle["host_calls"] == []


@pytest.mark.parametrize("production_boundary", ["missing", "different"], indirect=True)
def test_production_exploratory_requires_approved_executing_entrypoint(
    production_boundary: dict[str, Any],
) -> None:
    bundle = production_boundary
    runner = _production_selector_runner(bundle)
    denied = runner(
        **_production_request(bundle, output="entrypoint-check", request_id="request-1")
    )
    assert denied.returncode != 0
    assert denied.receipt["failure_kind"] == "authorization"
    assert bundle["host_calls"] == []
