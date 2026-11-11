from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, ClassVar

import pytest

from nesy_game.npc_goal import _codex_output_schema, _codex_validator
from nesy_game.runtime_model_swap import EpisodeLimits, GodotEpisodeEngine, ModelSpec, run_episode
from nesy_game.runtime_model_swap_ollama import (
    OllamaPromptRunner,
    OllamaTransportError,
    receipt_digest,
    serialize_receipt,
)

MODEL = "ollama-fixture:7b"
REQUEST_ID = "ollama-request-1"


def _schema() -> dict[str, Any]:
    return _codex_output_schema()


def _payload(request_id: str = REQUEST_ID, *, label: str = "ASK_INFORMATION") -> dict[str, Any]:
    return {
        "request_id": request_id,
        "typed_intent": {
            "label": label,
            "claims": [{"code": "NONE", "state": "UNVERIFIED"}],
            "target": None,
        },
    }


def _fixture_files(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    blob_bytes = b"model blob bytes bound to the manifest"
    blob_digest = hashlib.sha256(blob_bytes).hexdigest()
    blob = root / "blobs" / f"sha256-{blob_digest}"
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_bytes(blob_bytes)
    manifest = root / "manifests" / "ollama-fixture" / "7b"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "layers": [
                    {
                        "mediaType": "application/vnd.ollama.image.model",
                        "digest": f"sha256:{blob_digest}",
                    }
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    schema = root / "response-schema.json"
    schema.write_text(json.dumps(_schema(), sort_keys=True), encoding="utf-8")
    return manifest, blob, schema


def _runner(
    root: Path,
    transport: Any,
    *,
    schema: Path | None = None,
    clock: Any | None = None,
    timeout: float = 2.0,
) -> OllamaPromptRunner:
    manifest, blob, schema_path = _fixture_files(root)
    kwargs: dict[str, Any] = {
        "manifest_path": manifest,
        "blob_path": blob,
        "schema_path": schema or schema_path,
        "endpoint": "http://127.0.0.1:11434/api/generate",
        "model": MODEL,
        "timeout": timeout,
        "allowed_root": root,
    }
    if clock is not None:
        kwargs["clock"] = clock
    return OllamaPromptRunner(transport, **kwargs)


def _call(runner: OllamaPromptRunner, **overrides: Any):
    values: dict[str, Any] = {
        "request_id": REQUEST_ID,
        "user_prompt": "Where is the lighthouse lens?",
        "instruction": "Return a typed intent.",
        "model": MODEL,
        "timeout": 2.0,
        "validator": _codex_validator,
    }
    values.update(overrides)
    return runner(**values)


def _tag_digest(root: Path) -> str:
    manifest = root / "manifests" / "ollama-fixture" / "7b"
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def _transport_with_response(
    root: Path,
    calls: list[dict[str, Any]],
    response: Any,
    *,
    tag_model: str = MODEL,
    tag_digest: str | None = None,
    show_response: Any = None,
):
    def transport(request: dict[str, Any], *, endpoint: str, timeout: float) -> Any:
        calls.append({"request": dict(request), "endpoint": endpoint, "timeout": timeout})
        if request.get("operation") == "tags":
            return {
                "models": [
                    {"name": tag_model, "digest": f"sha256:{tag_digest or _tag_digest(root)}"}
                ]
            }
        if request.get("operation") == "show":
            # Real /api/show does not echo the requested model; identity comes from /api/tags.
            return show_response if show_response is not None else {"details": {}, "model_info": {}}
        if isinstance(response, dict) and "response" in response:
            completed = dict(response)
            completed.setdefault("done", True)
            return completed
        return response

    return transport


def _assert_finalized(result: Any) -> None:
    assert result.receipt["duration_seconds"] >= 0
    assert result.receipt["receipt_sha256"] == receipt_digest(result.receipt)


def test_valid_response_binds_canonical_schema_and_manifest_tag_without_pull() -> None:
    """A verified local response must bind to the staged tag/blob and fixed-game validator."""
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []
        response = {"model": MODEL, "response": json.dumps(_payload())}
        runner = _runner(root, _transport_with_response(root, calls, response))
        result = _call(runner)
        manifest, blob, _schema_path = _fixture_files(root)
        manifest_sha256 = hashlib.sha256(manifest.read_bytes()).hexdigest()
        blob_sha256 = hashlib.sha256(blob.read_bytes()).hexdigest()

    assert result.returncode == 0
    assert result.payload == _payload()
    assert result.receipt["status"] == "verified"
    assert result.receipt["scientific_eligible"] is False
    assert result.receipt["response_qualified"] is True
    assert result.receipt["requested_model"] == MODEL
    assert result.receipt["response_model"] == MODEL
    assert result.receipt["model_pre"] == MODEL
    assert result.receipt["model_post"] == MODEL
    assert result.receipt["tag_digest_pre"] == manifest_sha256
    assert result.receipt["tag_digest_post"] == manifest_sha256
    assert result.receipt["manifest_sha256_pre"] == manifest_sha256
    assert result.receipt["manifest_sha256_post"] == manifest_sha256
    assert result.receipt["blob_sha256_pre"] == blob_sha256
    assert result.receipt["blob_sha256_post"] == blob_sha256
    assert result.receipt["manifest_blob_distinct"] is True
    assert result.receipt["residency_policy"] == "keep_alive=0"
    assert result.receipt["residency_released"] is True
    _assert_finalized(result)

    generate_requests = [row for row in calls if "operation" not in row["request"]]
    assert len(generate_requests) == 1
    request = generate_requests[0]["request"]
    assert request["model"] == MODEL
    assert request["stream"] is False
    assert request["format"] == _schema()
    assert request["keep_alive"] == 0
    assert [row["request"]["operation"] for row in calls if "operation" in row["request"]] == [
        "tags",
        "show",
        "tags",
        "show",
    ]
    assert not any(row["request"].get("operation") == "pull" for row in calls)


def test_done_false_response_is_retained_as_incomplete_failure() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        response = {
            "model": MODEL,
            "response": json.dumps(_payload()),
            "done": False,
        }
        result = _call(_runner(root, _transport_with_response(root, [], response)))

    assert result.returncode != 0
    assert result.payload == {}
    assert result.receipt["status"] == "failed"
    assert result.receipt["error"] == "generation_not_complete"
    assert result.receipt["failure_kind"] == "parse"
    assert result.receipt["response_done"] is False
    assert result.receipt["postflight_requested"] is False
    assert result.receipt["response_qualified"] is False
    _assert_finalized(result)


def test_real_show_shape_does_not_erase_tag_identity() -> None:
    """The official show shape is accepted while tags provide the authoritative model identity."""
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []
        response = {"model": MODEL, "response": json.dumps(_payload())}
        runner = _runner(
            root,
            _transport_with_response(
                root,
                calls,
                response,
                show_response={
                    "parameters": "temperature 0",
                    "license": "Apache-2.0",
                    "modified_at": "2026-10-28T00:00:00Z",
                    "details": {"family": "llama"},
                    "template": "{{ .Prompt }}",
                    "capabilities": ["completion"],
                    "model_info": {"general.architecture": "llama"},
                },
            ),
        )
        result = _call(runner)

    assert result.returncode == 0
    assert result.receipt["model_pre"] == MODEL
    assert result.receipt["model_post"] == MODEL
    assert result.receipt["response_qualified"] is True


def test_godot_episode_engine_records_injected_ollama_receipt() -> None:
    """The real engine seam preserves a verified Ollama receipt beside its prompt call."""
    with TemporaryDirectory() as directory:
        root = Path(directory)
        adapter_root = root / "ollama"
        output_root = root / "episode"
        calls: list[dict[str, Any]] = []

        def transport(request: dict[str, Any], *, endpoint: str, timeout: float) -> Any:
            calls.append({"request": dict(request), "endpoint": endpoint, "timeout": timeout})
            if request.get("operation") in {"tags", "show"}:
                return _transport_with_response(adapter_root, [], {"model": MODEL})(
                    request, endpoint=endpoint, timeout=timeout
                )
            return {
                "model": MODEL,
                "response": json.dumps(_payload(request["request_id"])),
                "done": True,
            }

        runner = _runner(adapter_root, transport)

        def engine_transport(**kwargs: Any) -> dict[str, Any]:
            payload = json.loads(Path(kwargs["input_path"]).read_text(encoding="utf-8"))
            assert kwargs["mode"] == "bootstrap"
            assert payload["request_context"]["request_id"] == "runtime-0-request"
            return {
                "status": "completed",
                "trace": {
                    "passed": True,
                    "observation": {
                        "lens_reachable": True,
                        "lens_carried": False,
                        "signal_restored": False,
                        "tide_lead_authorized": False,
                        "goal_reached": False,
                        "in_dialogue": False,
                    },
                    "state_ref": {"revision": 0, "sha256": "0" * 64},
                    "policy_hash": "b" * 64,
                    "actions": [],
                },
            }

        engine = GodotEpisodeEngine(
            project=root / "staged-project",
            output_root=output_root,
            prompt_runner=runner,
            engine_runner=engine_transport,
            godot_binary="godot-fixture",
            fixture_ref="fixture#1",
        )
        engine.configure_runtime(
            limits=EpisodeLimits(),
            clock=lambda: 0.0,
            started=0.0,
            model_id=MODEL,
            prompt="Where is the lighthouse lens?",
        )
        assert engine.state()["observation"]["lens_reachable"] is True
        proposal = engine.propose({"model_input": {"rendering": "public rules"}})

    assert proposal == {"action": "acquire_object"}
    assert len(engine.prompt_calls) == 1
    assert len(engine.prompt_receipts) == 1
    assert engine.prompt_receipts[0]["status"] == "verified"
    assert engine.prompt_receipts[0]["response_qualified"] is True
    assert engine.prompt_calls[0]["receipt"] == engine.prompt_receipts[0]
    assert engine.prompt_calls[0]["returncode"] == 0
    assert not any(row["request"].get("operation") == "pull" for row in calls)


@pytest.mark.parametrize(
    ("model", "config", "admitted", "expected_reason", "expected_denominator"),
    [
        (
            ModelSpec("ollama:7b", "general_rule", provider="ollama", offline=False),
            {"execution_mode": "fixed_game_godot_with_local_ollama"},
            False,
            "provider_not_allowed_offline",
            True,
        ),
        (
            ModelSpec("other:7b", "general_rule", provider="other", offline=False),
            {"execution_mode": "fixed_game_godot_with_local_ollama"},
            True,
            "ollama_admission_mismatch",
            False,
        ),
        (
            ModelSpec("ollama:7b", "general_rule", provider="ollama", offline=False),
            {"execution_mode": "ordinary"},
            True,
            "ollama_execution_mode_required",
            False,
        ),
    ],
)
def test_run_episode_rejects_unadmitted_or_mismatched_ollama(
    model: ModelSpec,
    config: dict[str, Any],
    admitted: bool,
    expected_reason: str,
    expected_denominator: bool,
) -> None:
    result = run_episode(
        engine=object(),
        proposal_source=lambda _context: {"action": "noop"},
        model=model,
        limits=EpisodeLimits(),
        seed=7,
        clock=lambda: 0.0,
        config=config,
        prompt="fixed-game admission",
        ollama_local_admitted=admitted,
    )

    assert result["failure_reason"] == expected_reason
    assert result["accounting"]["denominator_eligible"] is expected_denominator
    assert result["scientific"] == {"assigned": 0, "executed": 0, "eligible": False}
    assert result["evidence"]["provenance"]["mode"] == "rejected"


def test_run_episode_admits_local_ollama_and_derives_execution_from_receipt() -> None:
    class FixtureEngine:
        prompt_receipts: ClassVar[list[dict[str, Any]]] = [
            {
                "generation_dispatched": True,
                "status": "verified",
                "response_qualified": True,
                "scientific_eligible": True,
                "transport_kind": "local_http",
                "provider_request_count_authoritative": True,
                "transport_request_count": 3,
                "transport_response_count": 3,
                "transport_events": [
                    {
                        "kind": "preflight",
                        "operation": "version",
                        "attempted": True,
                        "succeeded": True,
                    },
                    {
                        "kind": "preflight",
                        "operation": "tags",
                        "attempted": True,
                        "succeeded": True,
                    },
                    {
                        "kind": "preflight",
                        "operation": "show",
                        "attempted": True,
                        "succeeded": True,
                    },
                ],
            }
        ]
        raw_model_outputs: ClassVar[list[dict[str, Any]]] = []
        prompt_calls: ClassVar[list[dict[str, Any]]] = []
        engine_evidence: ClassVar[list[dict[str, Any]]] = []
        source_hashes: ClassVar[dict[str, str]] = {}

        def configure_runtime(self, **_kwargs: Any) -> None:
            return None

        def state(self) -> dict[str, Any]:
            return {"fixture": True}

        def objective_reached(self) -> bool:
            return False

        def legal_actions(self) -> list[str]:
            return ["noop"]

        def preconditions(self) -> dict[str, list[str]]:
            return {}

        def constraints(self) -> list[str]:
            return []

        def objective(self) -> str:
            return "fixture"

        def validate(self, _proposal: dict[str, Any]) -> dict[str, Any]:
            return {"valid": True, "code": None, "message": None}

        def commit(self, _proposal: dict[str, Any]) -> dict[str, Any]:
            return {"fixture": True}

    with TemporaryDirectory() as directory:
        root = Path(directory)
        runner = _runner(root, lambda _request, **_kwargs: {})
        engine = FixtureEngine()
        engine.prompt_runner = runner
        result = run_episode(
            engine=engine,
            proposal_source=lambda _context: (_ for _ in ()).throw(
                RuntimeError("stop-after-admission")
            ),
            model=ModelSpec("ollama:7b", "general_rule", provider="ollama", offline=False),
            limits=EpisodeLimits(),
            seed=7,
            clock=lambda: 0.0,
            config={
                "assignment_id": "ollama-assignment",
                "execution_mode": "fixed_game_godot_with_local_ollama",
            },
            prompt="fixed-game admission",
            ollama_local_admitted=True,
        )

        assert result["evidence"]["provenance"]["mode"] == "local_ollama"
        assert result["scientific"] == {"assigned": 1, "executed": 1, "eligible": False}
        assert result["evidence"]["provider_request_count"] == 3
        assert result["evidence"]["response_qualification"]["required"] is True


def test_tag_digest_mismatch_is_retained_as_preflight_integrity_failure() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []
        runner = _runner(
            root,
            _transport_with_response(
                root,
                calls,
                {"model": MODEL, "response": json.dumps(_payload())},
                tag_digest="0" * 64,
            ),
        )
        result = _call(runner)

    assert result.returncode != 0
    assert result.payload == {}
    assert result.receipt["status"] == "failed"
    assert result.receipt["error"] == "tag_manifest_digest_mismatch"
    assert result.receipt["failure_kind"] == "integrity"
    assert result.receipt["attempted"] is True
    assert result.receipt["preflight_requested"] is True
    assert result.receipt["preflight_completed"] is True
    assert result.receipt["generation_dispatched"] is False
    _assert_finalized(result)


def test_response_model_mismatch_is_retained_as_identity_failure() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []
        runner = _runner(
            root,
            _transport_with_response(
                root,
                calls,
                {"model": "different-model", "response": json.dumps(_payload())},
            ),
        )
        result = _call(runner)

    assert result.returncode != 0
    assert result.payload == {}
    assert result.receipt["status"] == "failed"
    assert result.receipt["error"] == "response_model_mismatch"
    assert result.receipt["failure_kind"] == "identity"
    assert result.receipt["attempted"] is True
    assert result.receipt["generation_dispatched"] is True
    assert result.receipt["response_model"] == "different-model"
    assert result.receipt["response_sha256"] is not None
    _assert_finalized(result)


def test_absent_or_incorrect_requested_model_is_rejected_before_transport() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        manifest, blob, schema = _fixture_files(root)
        calls: list[dict[str, Any]] = []
        missing_runner = OllamaPromptRunner(
            _transport_with_response(root, calls, {"model": MODEL}),
            manifest_path=manifest,
            blob_path=blob,
            schema_path=schema,
            model=None,
            allowed_root=root,
        )
        incorrect = _call(
            _runner(root, _transport_with_response(root, calls, {"model": MODEL})),
            model="unapproved-model",
        )
        missing = _call(missing_runner, model=None)

    assert missing.returncode != 0
    assert missing.receipt["error"] == "model_missing"
    assert missing.receipt["failure_kind"] == "logical"
    assert missing.receipt["attempted"] is False
    assert incorrect.returncode != 0
    assert incorrect.receipt["error"] == "requested_model_mismatch"
    assert incorrect.receipt["failure_kind"] == "identity"
    assert incorrect.receipt["attempted"] is False
    assert calls == []
    _assert_finalized(missing)
    _assert_finalized(incorrect)


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        ("not a JSON object", "malformed_response"),
        ({"model": MODEL, "response": "not-json"}, "malformed_response"),
        (
            {"model": MODEL, "response": json.dumps({"request_id": REQUEST_ID})},
            "malformed_response",
        ),
        (
            {"model": MODEL, "response": json.dumps(_payload(label="NOT_A_CANONICAL_LABEL"))},
            "malformed_response",
        ),
    ],
)
def test_malformed_or_noncanonical_response_never_becomes_success(
    response: Any, expected_error: str
) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []
        result = _call(_runner(root, _transport_with_response(root, calls, response)))

    assert result.returncode != 0
    assert result.payload == {}
    assert result.receipt["status"] == "failed"
    assert result.receipt["error"] == expected_error
    assert result.receipt["failure_kind"] == "parse"
    assert result.receipt["attempted"] is True
    assert result.receipt["generation_dispatched"] is True
    if isinstance(response, dict):
        assert result.receipt["response_sha256"] is not None
    else:
        assert result.receipt["response_sha256"] is None
    _assert_finalized(result)


def test_fixed_game_validator_rejection_remains_visible() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []
        result = _call(
            _runner(
                root,
                _transport_with_response(
                    root, calls, {"model": MODEL, "response": json.dumps(_payload())}
                ),
            ),
            validator=lambda _payload, _request_id: False,
        )

    assert result.returncode != 0
    assert result.receipt["error"] == "fixed_game_validator_rejected"
    assert result.receipt["failure_kind"] == "parse"
    assert result.receipt["postflight_requested"] is False
    _assert_finalized(result)


@pytest.mark.parametrize(
    ("field", "expected_error"),
    [("manifest", "tag_manifest_digest_drift"), ("blob", "blob_digest_mismatch")],
)
def test_artifact_digest_drift_is_retained_and_disqualifies_result(
    field: str, expected_error: str
) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        manifest, blob, _schema_path = _fixture_files(root)
        calls: list[dict[str, Any]] = []

        def transport(request: dict[str, Any], *, endpoint: str, timeout: float) -> Any:
            calls.append(dict(request))
            if request.get("operation") in {"tags", "show"}:
                return _transport_with_response(
                    root, [], {"model": MODEL, "response": json.dumps(_payload())}
                )(request, endpoint=endpoint, timeout=timeout)
            if field == "manifest":
                data = json.loads(manifest.read_text(encoding="utf-8"))
                data["extra"] = "drift"
                manifest.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            else:
                blob.write_bytes(b"drifted bytes")
            return {"model": MODEL, "response": json.dumps(_payload()), "done": True}

        result = _call(_runner(root, transport))

    assert result.returncode != 0
    assert result.payload == {}
    assert result.receipt["status"] == "failed"
    assert result.receipt["error"] == expected_error
    assert result.receipt["failure_kind"] == "integrity"
    assert result.receipt["attempted"] is True
    assert result.receipt["response_qualified"] is False
    _assert_finalized(result)


def test_timeout_and_transport_exception_keep_failure_accounting() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        calls: list[dict[str, Any]] = []

        def timeout_transport(request: dict[str, Any], **kwargs: Any) -> Any:
            calls.append(dict(request))
            if request.get("operation") in {"tags", "show"}:
                return _transport_with_response(
                    root, [], {"model": MODEL, "response": json.dumps(_payload())}
                )(request, endpoint=kwargs.get("endpoint", ""), timeout=kwargs.get("timeout", 0.0))
            raise TimeoutError("transport timed out")

        timed_out = _call(_runner(root, timeout_transport))
        assert timed_out.returncode == 124
        assert timed_out.receipt["status"] == "timeout"
        assert timed_out.receipt["error"] == "transport_timeout"
        assert timed_out.receipt["failure_kind"] == "transport"
        assert timed_out.receipt["timed_out"] is True
        assert timed_out.receipt["attempted"] is True
        _assert_finalized(timed_out)

        def failed_transport(request: dict[str, Any], **kwargs: Any) -> Any:
            if request.get("operation") in {"tags", "show"}:
                return _transport_with_response(
                    root, [], {"model": MODEL, "response": json.dumps(_payload())}
                )(request, endpoint=kwargs.get("endpoint", ""), timeout=kwargs.get("timeout", 0.0))
            raise OllamaTransportError("transport_error")

        unavailable = _call(_runner(root, failed_transport))

    assert unavailable.returncode == 125
    assert unavailable.receipt["status"] == "unavailable"
    assert unavailable.receipt["error"] == "transport_error"
    assert unavailable.receipt["failure_kind"] == "transport"
    assert unavailable.receipt["attempted"] is True
    assert unavailable.receipt["timed_out"] is False
    _assert_finalized(unavailable)


class _StepClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def test_one_deadline_is_shared_by_preflight_generation_and_postflight() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        clock = _StepClock()
        calls: list[dict[str, Any]] = []

        def transport(request: dict[str, Any], *, endpoint: str, timeout: float) -> Any:
            calls.append({"request": dict(request), "timeout": timeout})
            clock.advance(0.75)
            if request.get("operation") in {"tags", "show"}:
                return _transport_with_response(
                    root, [], {"model": MODEL, "response": json.dumps(_payload())}
                )(request, endpoint=endpoint, timeout=timeout)
            return {"model": MODEL, "response": json.dumps(_payload()), "done": True}

        result = _call(_runner(root, transport, clock=clock, timeout=2.0))

    assert result.returncode == 124
    assert result.receipt["error"] == "transport_timeout"
    assert result.receipt["timed_out"] is True
    assert result.receipt["duration_seconds"] == pytest.approx(2.25)
    assert result.receipt["postflight_requested"] is True
    assert len(calls) == 3
    assert all(call["timeout"] > 0 for call in calls)
    _assert_finalized(result)


@pytest.mark.parametrize("label", ["manifest", "blob"])
def test_bound_artifact_paths_cannot_escape_explicit_allowed_root(label: str) -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory) / "allowed"
        outside = Path(directory) / "outside.bin"
        root.mkdir()
        outside.write_bytes(b"outside")
        manifest, blob, schema = _fixture_files(root)
        paths = {"manifest": manifest, "blob": blob}
        paths[label] = outside

        with pytest.raises(ValueError, match=rf"^{label}_path_escape$"):
            OllamaPromptRunner(
                lambda *_args, **_kwargs: {},
                manifest_path=paths["manifest"],
                blob_path=paths["blob"],
                schema_path=schema,
                model=MODEL,
                allowed_root=root,
            )


def test_non_loopback_and_unsafe_loopback_endpoints_are_rejected() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        manifest, blob, schema = _fixture_files(root)
        for endpoint, error in (
            ("http://192.0.2.1:11434/api/generate", "loopback_endpoint_required"),
            ("https://127.0.0.1:11434/api/generate", "loopback_endpoint_required"),
            (
                "http://127.0.0.1:11434/api/generate?x=1",
                "endpoint_credentials_or_fragment_forbidden",
            ),
            ("http://127.0.0.1:1234/api/generate", "ollama_port_required"),
        ):
            with pytest.raises(ValueError, match=f"^{error}$"):
                OllamaPromptRunner(
                    lambda *_args, **_kwargs: {},
                    manifest_path=manifest,
                    blob_path=blob,
                    schema_path=schema,
                    model=MODEL,
                    endpoint=endpoint,
                    allowed_root=root,
                )


def test_missing_or_malformed_schema_is_rejected_before_transport() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        manifest, blob, schema = _fixture_files(root)
        calls: list[dict[str, Any]] = []
        missing = root / "missing-schema.json"
        missing_result = _call(
            OllamaPromptRunner(
                _transport_with_response(root, calls, {"model": MODEL}),
                manifest_path=manifest,
                blob_path=blob,
                schema_path=missing,
                model=MODEL,
                allowed_root=root,
            )
        )

        schema.write_text("{not-json", encoding="utf-8")
        malformed_result = _call(
            OllamaPromptRunner(
                _transport_with_response(root, calls, {"model": MODEL}),
                manifest_path=manifest,
                blob_path=blob,
                schema_path=schema,
                model=MODEL,
                allowed_root=root,
            )
        )

    for result, expected_error in (
        (missing_result, "schema_unreadable"),
        (malformed_result, "schema_malformed"),
    ):
        assert result.returncode != 0
        assert result.payload == {}
        assert result.receipt["status"] == "failed"
        assert result.receipt["error"] == expected_error
        assert result.receipt["failure_kind"] == "authorization"
        assert result.receipt["attempted"] is False
        _assert_finalized(result)
    assert calls == []


def test_noncanonical_schema_is_rejected_before_transport() -> None:
    with TemporaryDirectory() as directory:
        root = Path(directory)
        manifest, blob, schema = _fixture_files(root)
        schema.write_text(json.dumps({"type": "object"}), encoding="utf-8")
        calls: list[dict[str, Any]] = []
        result = _call(
            OllamaPromptRunner(
                _transport_with_response(root, calls, {"model": MODEL}),
                manifest_path=manifest,
                blob_path=blob,
                schema_path=schema,
                model=MODEL,
                allowed_root=root,
            )
        )

    assert result.returncode != 0
    assert result.receipt["error"] == "canonical_schema_mismatch"
    assert result.receipt["failure_kind"] == "authorization"
    assert result.receipt["attempted"] is False
    assert calls == []
    _assert_finalized(result)


def test_receipt_serialization_and_digest_are_order_independent() -> None:
    first = {"z": [2, 1], "a": {"b": "灯台", "a": 1}}
    second = {"a": {"a": 1, "b": "灯台"}, "z": [2, 1]}

    serialized = serialize_receipt(first)
    assert serialized == serialize_receipt(second)
    assert receipt_digest(first) == hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def test_script_main_keeps_staged_project_and_schema_alive_through_episode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The admitted script must retain its disposable inputs for the full episode call."""
    from scripts import run_runtime_model_swap_ollama as script

    store_root = tmp_path / "ollama-store"
    manifest = store_root / "manifests" / "fixture"
    blob = store_root / "blobs" / "fixture"
    manifest.parent.mkdir(parents=True)
    blob.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    blob.write_bytes(b"fixture")
    output_root = tmp_path / "episode"
    observed: dict[str, Any] = {}

    monkeypatch.setattr(
        script,
        "_artifact_binding",
        lambda _manifest, _blob: (
            store_root,
            {
                "manifest_sha256": "m" * 64,
                "blob_sha256": "b" * 64,
                "model_layer_digest": "layer-fixture",
            },
        ),
    )

    def stage_project(_source: Path, destination: Path) -> None:
        destination.mkdir(parents=True)
        (destination / "project.godot").write_text("[application]\n", encoding="utf-8")
        observed["staged_project"] = destination

    class FakeRunner:
        def __init__(self, **kwargs: Any) -> None:
            observed["schema_path"] = Path(kwargs["schema_path"])
            observed["runner_endpoint"] = kwargs["endpoint"]

    class FakeEngine:
        def __init__(self, **kwargs: Any) -> None:
            self.project = Path(kwargs["project"])
            self.prompt_runner = kwargs["prompt_runner"]
            self.propose = lambda _context: {"action": "noop"}
            self.repair = lambda _context, _error, _attempt: {"action": "noop"}
            observed["engine_project"] = self.project

    def fake_run_episode(**kwargs: Any) -> dict[str, Any]:
        project = kwargs["engine"].project
        schema_path = observed["schema_path"]
        assert project.is_dir()
        assert (project / "project.godot").is_file()
        assert schema_path.is_file()
        assert kwargs["ollama_local_admitted"] is True
        assert kwargs["model"].provider == "ollama"
        assert kwargs["model"].offline is False
        assert kwargs["engine"].prompt_runner.__class__ is FakeRunner
        observed["episode_saw_inputs"] = True
        output_path = Path(kwargs["output_path"])
        output_path.write_text('{"status": "success"}\n', encoding="utf-8")
        return {
            "status": "success",
            "success": True,
            "failure_reason": None,
            "scientific": {"assigned": 1, "executed": 1, "eligible": False},
            "record_hash": "record-fixture",
        }

    monkeypatch.setattr(script, "stage_project", stage_project)
    monkeypatch.setattr(script, "OllamaPromptRunner", FakeRunner)
    monkeypatch.setattr(script, "GodotEpisodeEngine", FakeEngine)
    monkeypatch.setattr(script, "run_episode", fake_run_episode)

    exit_code = script.main(
        [
            "--model",
            MODEL,
            "--manifest",
            str(manifest),
            "--blob",
            str(blob),
            "--output-root",
            str(output_root),
            "--endpoint",
            "http://127.0.0.1:11434/api/generate",
            "--execute",
            "--admit-exploratory",
        ]
    )

    assert exit_code == 0
    assert observed["episode_saw_inputs"] is True
    assert observed["runner_endpoint"].startswith("http://127.0.0.1:")
    assert not observed["staged_project"].exists()
    assert not observed["schema_path"].exists()
    assert (output_root / "episode.json").is_file()
    assert json.loads(capsys.readouterr().out)["status"] == "success"
