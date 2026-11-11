from __future__ import annotations

"""Local-only Ollama transport for the prospective fixed-game arm.

The adapter never pulls models or starts a daemon. It admits only loopback HTTP,
binds the selected tag to the exact staged Ollama manifest/model blob, and
returns a finalized receipt for every assigned outcome.
"""

import hashlib
import inspect
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

OLLAMA_RECEIPT_SCHEMA = "runtime-ollama-receipt/3"
OLLAMA_REQUEST_SCHEMA = "runtime-ollama-request/2"


class OllamaTransportError(RuntimeError):
    """A local transport or HTTP failure, retained in the receipt."""


class OllamaTransport(Protocol):
    def __call__(self, request: Mapping[str, Any], *, endpoint: str, timeout: float) -> Any: ...


@dataclass(frozen=True)
class OllamaPromptResult:
    returncode: int
    payload: Mapping[str, Any]
    receipt: Mapping[str, Any]


@dataclass(frozen=True)
class OllamaReceipt:
    data: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return _plain(self.data)

    def serialize(self) -> str:
        return serialize_receipt(self.data)


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def serialize_receipt(receipt: Mapping[str, Any]) -> str:
    return json.dumps(_plain(receipt), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def receipt_digest(receipt: Mapping[str, Any]) -> str:
    normalized = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    return hashlib.sha256(serialize_receipt(normalized).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _load_schema(path: str | Path) -> tuple[dict[str, Any] | None, str | None, str | None]:
    candidate = Path(path)
    try:
        raw = candidate.read_bytes()
    except (OSError, ValueError):
        return None, None, "schema_unreadable"
    digest = hashlib.sha256(raw).hexdigest()
    try:
        schema = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, digest, "schema_malformed"
    if not isinstance(schema, Mapping):
        return None, digest, "schema_object_required"
    return dict(schema), digest, None


def _loopback_endpoint(endpoint: str) -> urllib.parse.ParseResult:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("loopback_endpoint_required")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.params:
        raise ValueError("endpoint_credentials_or_fragment_forbidden")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("ollama_port_required") from exc
    if port != 11434:
        raise ValueError("ollama_port_required")
    if parsed.path.rstrip("/") != "/api/generate":
        raise ValueError("generate_endpoint_required")
    return parsed


def _model_aliases(model: Any) -> set[str]:
    if not isinstance(model, str) or not model:
        return set()
    value = model.strip().casefold()
    aliases = {value}
    for prefix in ("registry.ollama.ai/", "localhost/", "127.0.0.1/"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            aliases.add(value)
    if value.startswith("library/"):
        aliases.add(value[len("library/") :])
    return aliases


def _same_model_tag(left: Any, right: Any) -> bool:
    return bool(_model_aliases(left) & _model_aliases(right))


def _digest_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("tag_digest_missing")  # noqa: TRY004
    digest = value.removeprefix("sha256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.casefold()):
        raise ValueError("tag_digest_missing")
    return digest.casefold()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self, request: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> Any:
        raise OllamaTransportError("redirect_forbidden")


def _operation_url(endpoint: str, operation: str) -> str:
    parsed = _loopback_endpoint(endpoint)
    path = {
        "generate": "/api/generate",
        "show": "/api/show",
        "tags": "/api/tags",
        "version": "/api/version",
    }[operation]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _http_transport(request: Mapping[str, Any], *, endpoint: str, timeout: float) -> Any:
    operation = str(request.get("operation") or "generate")
    target = _operation_url(endpoint, operation)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if operation in {"tags", "version"}:
        http_request = urllib.request.Request(target, headers=headers, method="GET")
    else:
        body = {key: value for key, value in request.items() if key != "operation"}
        http_request = urllib.request.Request(
            target, data=_json_bytes(body), headers=headers, method="POST"
        )
    try:
        # The local-only boundary must not inherit HTTP(S)_PROXY or follow redirects.
        opener = urllib.request.build_opener(_NoRedirect(), urllib.request.ProxyHandler({}))
        with opener.open(http_request, timeout=max(0.001, timeout)) as response:
            return json.loads(response.read().decode("utf-8"))
    except TimeoutError:
        raise
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        OSError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, TimeoutError) or "timed out" in str(exc).casefold():
            raise TimeoutError("transport_timeout") from exc
        if isinstance(exc, urllib.error.HTTPError) and exc.code in {401, 403}:
            raise PermissionError("provider_refused") from exc
        raise OllamaTransportError("transport_error") from exc


def _invoke_transport(
    transport: Callable[..., Any], request: Mapping[str, Any], endpoint: str, timeout: float
) -> Any:
    try:
        signature = inspect.signature(transport)
    except (TypeError, ValueError):
        return transport(request, endpoint=endpoint, timeout=timeout)
    parameters = signature.parameters
    kwargs: dict[str, Any] = {}
    if "endpoint" in parameters or any(p.kind == p.VAR_KEYWORD for p in parameters.values()):
        kwargs["endpoint"] = endpoint
    if "timeout" in parameters or any(p.kind == p.VAR_KEYWORD for p in parameters.values()):
        kwargs["timeout"] = timeout
    request_parameter = parameters.get("request")
    if request_parameter is not None and request_parameter.kind == request_parameter.KEYWORD_ONLY:
        return transport(request=request, **kwargs)
    return transport(request, **kwargs)


def _tag_from_manifest_path(path: Path) -> str:
    parts = path.parts
    try:
        index = parts.index("manifests")
    except ValueError as exc:
        raise ValueError("manifest_path_not_in_ollama_store") from exc
    relative = list(parts[index + 1 :])
    if len(relative) < 2:
        raise ValueError("manifest_tag_missing")
    if relative[0] in {"registry.ollama.ai", "localhost", "127.0.0.1"}:
        relative.pop(0)
    if relative and relative[0] == "library":
        relative.pop(0)
    if len(relative) < 2:
        raise ValueError("manifest_tag_missing")
    return "/".join(relative[:-1]) + ":" + relative[-1]


def _manifest_binding(
    manifest_path: Path,
    blob_path: Path,
    *,
    known_blob_sha256: str | None = None,
) -> dict[str, str]:
    try:
        raw = manifest_path.read_bytes()
        manifest = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OllamaTransportError("manifest_unreadable") from exc
    if not isinstance(manifest, Mapping) or not isinstance(manifest.get("layers"), list):
        raise ValueError("manifest_invalid")  # noqa: TRY004
    model_layers = [
        layer
        for layer in manifest["layers"]
        if isinstance(layer, Mapping)
        and layer.get("mediaType") == "application/vnd.ollama.image.model"
    ]
    if len(model_layers) != 1 or not isinstance(model_layers[0].get("digest"), str):
        raise ValueError("manifest_model_layer_missing")
    digest = model_layers[0]["digest"]
    if not digest.startswith("sha256:"):
        raise ValueError("manifest_blob_binding_mismatch")
    digest_hex = _digest_text(digest)
    if blob_path.name != "sha256-" + digest_hex:
        raise ValueError("manifest_blob_binding_mismatch")
    blob_hash = known_blob_sha256 or _sha256(blob_path)
    if blob_hash != digest_hex:
        raise ValueError("blob_digest_mismatch")
    return {
        "tag": _tag_from_manifest_path(manifest_path),
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "blob_sha256": blob_hash,
        "model_layer_digest": "sha256:" + digest_hex,
    }


def _tag_identity(data: Any, model: str) -> dict[str, Any]:
    if not isinstance(data, Mapping) or not isinstance(data.get("models"), list):
        raise ValueError("tags_response_malformed")  # noqa: TRY004
    for entry in data["models"]:
        if not isinstance(entry, Mapping):
            continue
        observed_model = entry.get("model") or entry.get("name")
        if _same_model_tag(observed_model, model):
            return {"model": observed_model, "tag_digest": _digest_text(entry.get("digest"))}
    raise ValueError("model_tag_not_present")


class OllamaPromptRunner:
    """Bounded local Ollama caller for a fresh exploratory cohort only."""

    def __init__(
        self,
        transport: OllamaTransport | Callable[..., Any] | None = None,
        *,
        manifest_path: str | Path,
        blob_path: str | Path,
        schema_path: str | Path,
        endpoint: str = "http://127.0.0.1:11434/api/generate",
        model: str | None = None,
        timeout: float = 30.0,
        allowed_root: str | Path | None = None,
        options: Mapping[str, Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.transport = transport or _http_transport
        parsed_endpoint = _loopback_endpoint(endpoint)
        self.endpoint = endpoint
        self.endpoint_peer = f"{parsed_endpoint.hostname}:{parsed_endpoint.port}"
        self.model = model
        self.timeout = float(timeout)
        if self.timeout <= 0:
            raise ValueError("timeout_must_be_positive")
        self.clock = clock
        self.options = dict(options or {})
        _json_bytes(self.options)
        root = Path(allowed_root).resolve() if allowed_root is not None else None
        self.manifest_path = self._bound_path(manifest_path, root, "manifest")
        self.blob_path = self._bound_path(blob_path, root, "blob")
        self.schema_path = self._bound_path(schema_path, None, "schema")

    @staticmethod
    def _bound_path(value: str | Path, root: Path | None, label: str) -> Path:
        candidate = Path(value).resolve()
        if root is not None:
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError(f"{label}_path_escape") from exc
        return candidate

    def _artifact_identity(self) -> dict[str, str]:
        # Re-hash on every identity check so a same-size/same-mtime replacement
        # cannot reuse a stale cached digest. _sha256 streams the artifact.
        binding = _manifest_binding(self.manifest_path, self.blob_path)
        return binding

    def _receipt(
        self, request_id: str, requested_model: str | None, **fields: Any
    ) -> dict[str, Any]:
        receipt: dict[str, Any] = {
            "schema_version": OLLAMA_RECEIPT_SCHEMA,
            "request_id": request_id,
            "requested_model": requested_model,
            "assignment_id": None,
            "row_id": None,
            "config_hash": None,
            "assignment_id_pre": None,
            "assignment_id_post": None,
            "row_id_pre": None,
            "row_id_post": None,
            "config_hash_pre": None,
            "config_hash_post": None,
            "response_model": None,
            "manifest_sha256": None,
            "blob_sha256": None,
            "model_layer_digest": None,
            "model_pre": None,
            "model_post": None,
            "tag_digest_pre": None,
            "tag_digest_post": None,
            "model_layer_digest_pre": None,
            "model_layer_digest_post": None,
            "ollama_version_pre": None,
            "ollama_version_post": None,
            "manifest_sha256_pre": None,
            "manifest_sha256_post": None,
            "blob_sha256_pre": None,
            "blob_sha256_post": None,
            "manifest_blob_distinct": False,
            "status": "unavailable",
            "error": None,
            "failure_kind": None,
            "timed_out": False,
            "attempted": False,
            "preflight_requested": False,
            "preflight_completed": False,
            "generation_dispatched": False,
            "postflight_requested": False,
            "postflight_completed": False,
            "transport_kind": "injected_fixture"
            if self.transport is not _http_transport
            else "local_http",
            "runner_injected": self.transport is not _http_transport,
            "endpoint": self.endpoint,
            "endpoint_peer": self.endpoint_peer,
            "transport_events": [],
            "transport_request_count": 0,
            "transport_response_count": 0,
            "provider_request_count_authoritative": self.transport is _http_transport,
            "request_sha256": None,
            "schema_sha256": None,
            "schema_sha256_pre": None,
            "schema_sha256_post": None,
            "canonical_schema_sha256": None,
            "canonical_schema_sha256_pre": None,
            "canonical_schema_sha256_post": None,
            "response_sha256": None,
            "response_done": None,
            "done_reason": None,
            "response_metadata": {},
            "response_qualified": False,
            "scientific_eligible": False,
            "residency_policy": "keep_alive=0",
            "residency_release_requested": False,
            "residency_released": False,
            "duration_seconds": None,
            "receipt_sha256": None,
        }
        receipt.update(fields)
        return receipt

    def _remaining(self, deadline: float) -> float:
        remaining = deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError("transport_timeout")
        return remaining

    def _transport_call(
        self, request: Mapping[str, Any], deadline: float, receipt: dict[str, Any]
    ) -> Any:
        remaining = self._remaining(deadline)
        operation = request.get("operation")
        event: dict[str, Any] = {
            "kind": "generation" if operation is None else "preflight",
            "operation": "generate" if operation is None else str(operation),
            "attempted": True,
            "succeeded": False,
            "timeout": remaining,
            "error": None,
        }
        receipt["transport_events"].append(event)
        receipt["attempted"] = True
        receipt["transport_request_count"] += 1
        try:
            result = _invoke_transport(self.transport, request, self.endpoint, remaining)
        except TimeoutError:
            event["error"] = "transport_timeout"
            event["timed_out"] = True
            raise
        except Exception as exc:
            event["error"] = str(exc) or exc.__class__.__name__
            event["timed_out"] = False
            raise
        receipt["transport_response_count"] += 1
        event["succeeded"] = True
        return result

    def _inspect(self, model: str, deadline: float, receipt: dict[str, Any]) -> dict[str, Any]:
        if self.transport is _http_transport:
            version = self._transport_call(
                {"operation": "version", "schema_version": OLLAMA_REQUEST_SCHEMA},
                deadline,
                receipt,
            )
            if not isinstance(version, Mapping) or not isinstance(version.get("version"), str):
                raise ValueError("version_response_malformed")
            ollama_version = version["version"]
        else:
            ollama_version = None
        tags = self._transport_call(
            {"operation": "tags", "schema_version": OLLAMA_REQUEST_SCHEMA}, deadline, receipt
        )
        identity = _tag_identity(tags, model)
        show = self._transport_call(
            {"operation": "show", "model": model, "schema_version": OLLAMA_REQUEST_SCHEMA},
            deadline,
            receipt,
        )
        if not isinstance(show, Mapping):
            raise ValueError("show_response_malformed")  # noqa: TRY004
        identity["show_observed"] = True
        identity["ollama_version"] = ollama_version
        return identity

    def __call__(self, **kwargs: Any) -> OllamaPromptResult:
        started = self.clock()
        request_id = str(kwargs.get("request_id") or "")
        requested_model = kwargs.get("model") or self.model
        requested_model = str(requested_model) if requested_model is not None else None
        receipt = self._receipt(
            request_id,
            requested_model,
            assignment_id=kwargs.get("assignment_id"),
            row_id=kwargs.get("row_id") or kwargs.get("assignment_id"),
            config_hash=kwargs.get("config_hash"),
        )
        receipt["started_monotonic"] = started
        empty: dict[str, Any] = {}
        try:
            requested_timeout = float(kwargs.get("timeout", self.timeout))
            if requested_timeout <= 0:
                raise ValueError("timeout_must_be_positive")
            deadline = started + min(self.timeout, requested_timeout)
            if not request_id:
                receipt.update(
                    status="failed", error="request_id_missing", failure_kind="authorization"
                )
                return OllamaPromptResult(2, empty, receipt)
            if not requested_model:
                receipt.update(status="failed", error="model_missing", failure_kind="logical")
                return OllamaPromptResult(2, empty, receipt)
            if self.model is not None and not _same_model_tag(requested_model, self.model):
                receipt.update(
                    status="failed", error="requested_model_mismatch", failure_kind="identity"
                )
                return OllamaPromptResult(2, empty, receipt)
            schema_path = kwargs.get("output_schema") or self.schema_path
            schema, schema_sha256, schema_error = _load_schema(schema_path)
            if schema_error or schema is None:
                receipt.update(status="failed", error=schema_error, failure_kind="authorization")
                return OllamaPromptResult(2, empty, receipt)
            from nesy_game.npc_goal import (
                _canonical_validate,
                _codex_output_schema,
                _validate_typed_intent,
            )

            canonical_schema = _codex_output_schema()
            canonical_schema_sha256 = hashlib.sha256(_json_bytes(canonical_schema)).hexdigest()
            receipt.update(
                schema_sha256_pre=schema_sha256,
                canonical_schema_sha256_pre=canonical_schema_sha256,
            )
            if schema != canonical_schema:
                receipt.update(
                    status="failed", error="canonical_schema_mismatch", failure_kind="authorization"
                )
                return OllamaPromptResult(2, empty, receipt)
            binding = self._artifact_identity()
            receipt["manifest_blob_distinct"] = binding["manifest_sha256"] != binding["blob_sha256"]
            if not receipt["manifest_blob_distinct"]:
                raise ValueError("manifest_blob_identity_conflated")
            if not _same_model_tag(binding["tag"], requested_model):
                raise ValueError("manifest_tag_mismatch")
            receipt.update(
                assignment_id_pre=receipt["assignment_id"],
                row_id_pre=receipt["row_id"],
                config_hash_pre=receipt["config_hash"],
            )
            receipt["preflight_requested"] = True
            pre = self._inspect(requested_model, deadline, receipt)
            receipt.update(
                model_pre=pre["model"],
                tag_digest_pre=pre["tag_digest"],
                model_layer_digest_pre=binding["model_layer_digest"],
                ollama_version_pre=pre.get("ollama_version"),
                manifest_sha256_pre=binding["manifest_sha256"],
                blob_sha256_pre=binding["blob_sha256"],
                preflight_completed=True,
            )
            if pre["tag_digest"] != binding["manifest_sha256"]:
                raise ValueError("tag_manifest_digest_mismatch")

            prompt = str(kwargs.get("instruction") or kwargs.get("user_prompt") or "")
            request: dict[str, Any] = {
                "schema_version": OLLAMA_REQUEST_SCHEMA,
                "request_id": request_id,
                "model": requested_model,
                "prompt": prompt,
                "user_prompt": str(kwargs.get("user_prompt", "")),
                "stream": False,
                "format": schema,
                "keep_alive": 0,
            }
            if self.options:
                request["options"] = dict(self.options)
            receipt["request_sha256"] = hashlib.sha256(_json_bytes(request)).hexdigest()
            receipt["generation_dispatched"] = True
            receipt["residency_release_requested"] = True
            response = self._transport_call(request, deadline, receipt)
            if not isinstance(response, Mapping):
                raise ValueError("malformed_response")  # noqa: TRY004
            receipt["response_sha256"] = hashlib.sha256(_json_bytes(response)).hexdigest()
            receipt["response_done"] = response.get("done")
            receipt["done_reason"] = response.get("done_reason")
            receipt["response_metadata"] = {
                key: response[key]
                for key in (
                    "total_duration",
                    "load_duration",
                    "prompt_eval_count",
                    "prompt_eval_duration",
                    "eval_count",
                    "eval_duration",
                    "done_reason",
                )
                if key in response
            }
            response_model = response.get("model")
            receipt["response_model"] = response_model
            if not _same_model_tag(response_model, requested_model):
                raise ValueError("response_model_mismatch")
            status = str(response.get("status", "completed")).casefold()
            if status in {"refused", "error", "failed"} or response.get("done_reason") in {
                "refused",
                "error",
            }:
                raise PermissionError("provider_refused")
            raw_payload = response.get("response", response.get("structured_output"))
            if isinstance(raw_payload, str):
                try:
                    payload = json.loads(raw_payload)
                except json.JSONDecodeError as exc:
                    raise ValueError("malformed_response") from exc
            else:
                payload = raw_payload
            if not isinstance(payload, Mapping) or payload.get("request_id") != request_id:
                raise ValueError("malformed_response")
            payload = dict(payload)
            try:
                _canonical_validate(payload, canonical_schema)
                _validate_typed_intent(payload["typed_intent"])
            except Exception as exc:
                raise ValueError("malformed_response") from exc
            validator = kwargs.get("validator")
            if not callable(validator) or not validator(payload, request_id):
                raise ValueError("fixed_game_validator_rejected")
            if response.get("done") is not True:
                raise ValueError("generation_not_complete")
            receipt["residency_released"] = True

            receipt["postflight_requested"] = True
            post = self._inspect(requested_model, deadline, receipt)
            post_binding = self._artifact_identity()
            post_schema, post_schema_sha256, post_schema_error = _load_schema(schema_path)
            if post_schema_error or post_schema is None or post_schema != canonical_schema:
                raise ValueError("schema_digest_drift")
            receipt.update(
                model_post=post["model"],
                tag_digest_post=post["tag_digest"],
                model_layer_digest_post=post_binding["model_layer_digest"],
                ollama_version_post=post.get("ollama_version"),
                manifest_sha256_post=post_binding["manifest_sha256"],
                blob_sha256_post=post_binding["blob_sha256"],
                assignment_id_post=receipt["assignment_id"],
                row_id_post=receipt["row_id"],
                config_hash_post=receipt["config_hash"],
                schema_sha256_post=post_schema_sha256,
                canonical_schema_sha256_post=hashlib.sha256(
                    _json_bytes(canonical_schema)
                ).hexdigest(),
                postflight_completed=True,
            )
            if (
                post["tag_digest"] != post_binding["manifest_sha256"]
                or post["tag_digest"] != pre["tag_digest"]
            ):
                raise ValueError("tag_manifest_digest_drift")
            if binding != post_binding:
                raise ValueError("artifact_identity_drift")
            if any(
                receipt.get(key + "_pre") != receipt.get(key + "_post")
                for key in (
                    "assignment_id",
                    "row_id",
                    "config_hash",
                    "schema_sha256",
                    "canonical_schema_sha256",
                )
            ):
                raise ValueError("receipt_identity_drift")
            receipt.update(
                manifest_sha256=post_binding["manifest_sha256"],
                blob_sha256=post_binding["blob_sha256"],
                model_layer_digest=post_binding["model_layer_digest"],
                schema_sha256=post_schema_sha256,
                canonical_schema_sha256=receipt["canonical_schema_sha256_post"],
                status="verified",
                response_qualified=True,
            )
            receipt["scientific_eligible"] = receipt["transport_kind"] == "local_http" and all(
                isinstance(receipt.get(key), str) and bool(receipt.get(key))
                for key in (
                    "assignment_id",
                    "row_id",
                    "config_hash",
                    "manifest_sha256",
                    "blob_sha256",
                    "model_layer_digest",
                    "schema_sha256",
                    "canonical_schema_sha256",
                )
            )
            return OllamaPromptResult(0, payload, receipt)
        except PermissionError as exc:
            receipt.update(
                status="failed",
                error=str(exc),
                failure_kind="refusal",
                response_qualified=False,
                scientific_eligible=False,
            )
            return OllamaPromptResult(2, empty, receipt)
        except TimeoutError:
            receipt.update(
                status="timeout",
                error="transport_timeout",
                failure_kind="transport",
                timed_out=True,
                response_qualified=False,
                scientific_eligible=False,
            )
            return OllamaPromptResult(124, empty, receipt)
        except OllamaTransportError:
            receipt.update(
                status="unavailable",
                error="transport_error",
                failure_kind="transport",
                response_qualified=False,
                scientific_eligible=False,
            )
            return OllamaPromptResult(125, empty, receipt)
        except (OSError, TypeError, KeyError, ValueError, json.JSONDecodeError) as exc:
            message = str(exc)
            kind = (
                "integrity"
                if any(token in message for token in ("artifact", "digest", "blob", "manifest"))
                else "parse"
            )
            if message in {
                "response_model_mismatch",
                "manifest_tag_mismatch",
                "model_tag_not_present",
            }:
                kind = "identity"
            receipt.update(
                status="failed",
                error=message,
                failure_kind=kind,
                response_qualified=False,
                scientific_eligible=False,
            )
            return OllamaPromptResult(2, empty, receipt)
        except Exception as exc:  # noqa: BLE001 -- preserve unexpected local failures.
            receipt.update(
                status="unavailable",
                error=str(exc),
                failure_kind="transport",
                response_qualified=False,
                scientific_eligible=False,
            )
            return OllamaPromptResult(125, empty, receipt)
        finally:
            receipt.pop("started_monotonic", None)
            receipt["duration_seconds"] = max(0.0, self.clock() - started)
            receipt["receipt_sha256"] = receipt_digest(receipt)


__all__ = [
    "OLLAMA_RECEIPT_SCHEMA",
    "OLLAMA_REQUEST_SCHEMA",
    "OllamaPromptResult",
    "OllamaPromptRunner",
    "OllamaReceipt",
    "OllamaTransport",
    "OllamaTransportError",
    "receipt_digest",
    "serialize_receipt",
]
