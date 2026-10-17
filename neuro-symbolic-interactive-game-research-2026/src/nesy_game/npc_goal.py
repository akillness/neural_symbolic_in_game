"""Fixed-goal NPC interpretation, bounded planning, and replay-safe tracing.

Python is deliberately non-authoritative: it interprets bounded utterances, plans from the
public observation projection, and joins Godot results.  Godot remains the only canonical
world-state writer.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import tempfile
import threading
import time
import uuid
from collections import OrderedDict, deque
from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - runtime dependency is installed by the project
    Draft202012Validator = None  # type: ignore[assignment]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "game-track" / "schemas" / "npc-goal-recovery.schema.json"
CONFIG_PATH = PROJECT_ROOT / "configs" / "npc-goal-recovery.json"
SCHEMA_VERSION = "npc-goal-recovery/1.1.0"
REPLAY_INTENT_LINEAGE_SCOPE = "epoch_local_only"
REPLAY_CROSS_EPOCH_INTENT_CONTINUITY_PROVEN = False
SCENARIO_ID = "sealed-lighthouse-v1"
NPC_ID = "captain_mira"
GOAL_ID = "harbor-signal-restored-authorized-tide-lead-v1"
GOAL_VERSION = "1"
PUBLIC_FLAGS = ("lens_reachable", "lens_carried", "signal_restored", "tide_lead_authorized")
OBSERVATION_METADATA = ("goal_reached", "in_dialogue")
INTENT_LABELS = (
    "ASK_INFORMATION",
    "REQUEST_DISCLOSURE",
    "REPORT_FACT",
    "REFUSE_HELP",
    "AMBIGUOUS",
    "UNKNOWN",
)
CLAIM_STATES = ("UNVERIFIED", "SUPPORTED", "CONTRADICTED", "INDETERMINATE", "NOT_VISIBLE")
OPERATIONS = ("acquire_object", "install_lens", "reveal_hint", "clarify", "negotiate")
EXECUTION_MODES = ("player_request", "commit_world", "dialogue")
FORBIDDEN_FACT_TERMS = (
    "tide_marks_hint",
    "sealed_lighthouse",
    "lighthouse_dark",
    "offshore_lighthouse",
    "canonical_state",
    "worldstate",
)
REQUEST_KEYS = frozenset(
    (
        "schema_version",
        "message_type",
        "session_id",
        "session_epoch",
        "episode_id",
        "request_id",
        "event_id",
        "sequence",
        "delivery_index",
        "scenario_id",
        "npc_id",
        "goal_id",
        "config_hash",
        "goal_version",
        "policy_hash",
        "state_ref",
        "body",
        "budget",
        "provenance",
        "content_sha256",
    )
)
IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _require_enum(name: str, value: Any, allowed: set[str] | tuple[str, ...]) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ProtocolError(f"invalid_{name}")


def _canonical_validate(payload: Any, schema: Mapping[str, Any] | None = None) -> None:
    if Draft202012Validator is None:
        raise ControllerFailure("jsonschema_unavailable")
    document = dict(schema) if schema is not None else _load_schema()
    try:
        errors = sorted(
            Draft202012Validator(document).iter_errors(payload), key=lambda error: list(error.path)
        )
    except Exception as exc:
        raise ControllerFailure("canonical_schema_unavailable") from exc
    if errors:
        raise ProtocolError("canonical_schema_validation_failed")


DEFAULT_BUDGET: dict[str, Any] = {
    "intent_deadline_ms": 30_000,
    "episode_deadline_ms": 900_000,
    "max_intent_calls": 8,
    "max_action_attempts": 32,
    "max_replans": 16,
    "max_plan_expansions": 32,
    "max_inflight_per_session": 1,
    "input_tokens": None,
    "output_tokens": None,
    "cost": None,
}


class ProtocolError(ValueError):
    """Input does not satisfy the strict frozen protocol."""


class ControllerFailure(RuntimeError):
    """A bounded controller operation failed closed."""


class BudgetExceeded(ControllerFailure):
    """A configured budget was exhausted."""


def canonical_json(value: Any) -> bytes:
    """Return deterministic UTF-8 JSON used for all protocol hashes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def canonical_config_hash() -> str:
    try:
        return hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest()
    except (OSError, UnicodeError) as exc:
        raise ControllerFailure("canonical_config_unavailable") from exc


def content_hash(envelope: Mapping[str, Any]) -> str:
    material = {key: value for key, value in envelope.items() if key != "content_sha256"}
    return sha256_json(material)


def _trace_snapshot_id(session_id: str, session_epoch: int, rows: list[Mapping[str, Any]]) -> str:
    """Stable identity for one complete epoch trace snapshot."""
    return sha256_json({"session_id": session_id, "session_epoch": session_epoch, "rows": rows})


def _result_transition_error(
    operation: str, status: str, source_ref: Mapping[str, Any], result_ref: Mapping[str, Any]
) -> str | None:
    """Return a transition error when a result status disagrees with canonical state movement."""
    if status == "STALE":
        return "stale_result"
    if status == "APPLIED":
        if operation in {"acquire_object", "install_lens", "reveal_hint"}:
            if result_ref["revision"] != source_ref["revision"] + 1:
                return "applied_revision_mismatch"
            if result_ref["sha256"] == source_ref["sha256"]:
                return "applied_state_unchanged"
            return None
        if result_ref != source_ref:
            return "dialogue_state_changed"
        return None
    if result_ref != source_ref:
        return "non_applied_state_changed"
    return None


def _require_identifier(name: str, value: Any) -> None:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ProtocolError(f"invalid_{name}")


def _require_sha(name: str, value: Any) -> None:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise ProtocolError(f"invalid_{name}")


def _validate_state_ref(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"revision", "sha256"}:
        raise ProtocolError("invalid_state_ref")
    if not _is_int(value["revision"]) or value["revision"] < 0:
        raise ProtocolError("invalid_state_revision")
    _require_sha("state_hash", value["sha256"])


def validate_observation(observation: Any) -> dict[str, bool]:
    if not isinstance(observation, dict) or set(observation) != set(
        PUBLIC_FLAGS + OBSERVATION_METADATA
    ):
        raise ProtocolError("invalid_public_observation")
    if any(not isinstance(observation[key], bool) for key in observation):
        raise ProtocolError("observation_flags_must_be_boolean")
    return {key: observation[key] for key in PUBLIC_FLAGS + OBSERVATION_METADATA}


def _validate_budget(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != set(DEFAULT_BUDGET):
        raise ProtocolError("invalid_budget")
    for key in DEFAULT_BUDGET:
        item = value[key]
        if key in {"input_tokens", "output_tokens", "cost"}:
            if item is not None and (
                isinstance(item, bool) or not isinstance(item, (int, float)) or item < 0
            ):
                raise ProtocolError(f"invalid_budget_{key}")
        elif not _is_int(item) or item < 1:
            raise ProtocolError(f"invalid_budget_{key}")
    if value["max_inflight_per_session"] != 1:
        raise ProtocolError("max_inflight_per_session_must_be_one")
    return dict(value)


def _validate_provenance(value: Any) -> dict[str, Any]:
    required = {
        "arm",
        "backend",
        "model",
        "trace_ref",
        "recorded_response_ref",
        "raw_utterance_sha256",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ProtocolError("invalid_provenance")
    _require_enum("provenance_arm", value["arm"], ("P", "R", "O"))
    _require_enum("provenance_backend", value["backend"], ("codex", "rule", "reference"))
    for key in ("model", "trace_ref", "recorded_response_ref"):
        if value[key] is not None and (not isinstance(value[key], str) or len(value[key]) > 256):
            raise ProtocolError(f"invalid_provenance_{key}")
    if value["raw_utterance_sha256"] is not None:
        _require_sha("raw_utterance_sha256", value["raw_utterance_sha256"])
    return dict(value)


def validate_envelope(payload: Any, *, expected_message_type: str | None = None) -> dict[str, Any]:
    """Validate local protocol rules and the canonical JSON Schema."""
    if not isinstance(payload, dict) or set(payload) != REQUEST_KEYS:
        raise ProtocolError("envelope_keys_must_match_schema")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ProtocolError("schema_version_mismatch")
    message_type = payload["message_type"]
    _require_enum("message_type", message_type, ("request", "decision", "result", "ack"))
    if expected_message_type and message_type != expected_message_type:
        raise ProtocolError("unexpected_message_type")
    for key in ("session_id", "episode_id", "request_id", "event_id"):
        _require_identifier(key, payload[key])
    if not _is_int(payload["session_epoch"]) or payload["session_epoch"] < 0:
        raise ProtocolError("invalid_session_epoch")
    for key in ("sequence", "delivery_index"):
        if not _is_int(payload[key]) or payload[key] < 0:
            raise ProtocolError(f"invalid_{key}")
    if payload["scenario_id"] != SCENARIO_ID or payload["npc_id"] != NPC_ID:
        raise ProtocolError("identity_mismatch")
    if payload["goal_id"] != GOAL_ID or payload["goal_version"] != GOAL_VERSION:
        raise ProtocolError("goal_mismatch")
    _require_sha("config_hash", payload["config_hash"])
    if payload["config_hash"] != canonical_config_hash():
        raise ProtocolError("config_hash_mismatch")
    _require_sha("policy_hash", payload["policy_hash"])
    _validate_state_ref(payload["state_ref"])
    _validate_budget(payload["budget"])
    _validate_provenance(payload["provenance"])
    _require_sha("content_sha256", payload["content_sha256"])
    if payload["content_sha256"] != content_hash(payload):
        raise ProtocolError("content_hash_mismatch")
    _validate_body(message_type, payload["body"])
    _canonical_validate(payload)
    return payload


def _validate_body(message_type: str, body: Any) -> None:
    if not isinstance(body, dict):
        raise ProtocolError("body_must_be_object")
    if message_type == "request":
        if set(body) != {"event_kind", "utterance", "observation"}:
            raise ProtocolError("invalid_request_body")
        event_kind = body["event_kind"]
        _require_enum("event_kind", event_kind, ("utterance", "observation"))
        utterance = body["utterance"]
        if event_kind == "utterance":
            if not isinstance(utterance, str) or not utterance.strip() or len(utterance) > 1000:
                raise ProtocolError("invalid_utterance")
        elif utterance is not None:
            raise ProtocolError("observation_utterance_must_be_null")
        validate_observation(body["observation"])
    elif message_type == "decision":
        if set(body) != {
            "intent_id",
            "typed_intent",
            "plan_id",
            "steps",
            "planning_context_digest",
            "status",
            "error",
        }:
            raise ProtocolError("invalid_decision_body")
        _require_identifier("intent_id", body["intent_id"])
        if body["plan_id"] is not None:
            _require_identifier("plan_id", body["plan_id"])
        _require_sha("planning_context_digest", body["planning_context_digest"])
        _require_enum(
            "decision_status",
            body["status"],
            (
                "READY",
                "WAITING_PLAYER",
                "WAITING_DIALOGUE",
                "GOAL_REACHED",
                "NO_ROUTE",
                "FAILED",
                "CANCELLED",
            ),
        )
        if body["error"] is not None and (
            not isinstance(body["error"], str) or len(body["error"]) > 256
        ):
            raise ProtocolError("invalid_decision_error")
        _validate_typed_intent(body["typed_intent"], allow_verified_states=True)
        steps = body["steps"]
        if not isinstance(steps, list) or len(steps) > 32:
            raise ProtocolError("invalid_plan_steps")
        for step in steps:
            _validate_step(step)
    elif message_type == "result":
        expected = {
            "action_id",
            "operation",
            "status",
            "engine_revision",
            "state_ref",
            "feedback",
            "observation",
        }
        if set(body) != expected:
            raise ProtocolError("invalid_result_body")
        _require_identifier("action_id", body["action_id"])
        _require_enum("result_operation", body["operation"], OPERATIONS)
        _require_enum(
            "result_status",
            body["status"],
            ("APPLIED", "REJECTED", "STALE", "DUPLICATE", "CANCELLED", "ERROR"),
        )
        if not _is_int(body["engine_revision"]) or body["engine_revision"] < 0:
            raise ProtocolError("invalid_engine_revision")
        _validate_state_ref(body["state_ref"])
        if not isinstance(body["feedback"], str) or len(body["feedback"]) > 512:
            raise ProtocolError("invalid_feedback")
        validate_observation(body["observation"])
    else:
        if set(body) != {"ack_for", "status", "error"}:
            raise ProtocolError("invalid_ack_body")
        _require_enum("ack_for", body["ack_for"], ("request", "decision", "result"))
        _require_enum(
            "ack_status", body["status"], ("ACCEPTED", "REJECTED", "DUPLICATE", "STALE", "ERROR")
        )
        if body["error"] is not None and (
            not isinstance(body["error"], str) or len(body["error"]) > 256
        ):
            raise ProtocolError("invalid_ack_error")


def _validate_step(step: Any) -> None:
    if not isinstance(step, dict) or set(step) != {
        "action_id",
        "operation",
        "execution_mode",
        "arguments",
    }:
        raise ProtocolError("invalid_plan_step")
    _require_identifier("action_id", step["action_id"])
    _require_enum("plan_operation", step["operation"], OPERATIONS)
    _require_enum("execution_mode", step["execution_mode"], EXECUTION_MODES)
    if not isinstance(step["arguments"], dict):
        raise ProtocolError("invalid_plan_arguments")
    allowed = {
        "acquire_object": {"object_id": "signal_lens"},
        "install_lens": {"object_id": "signal_lens"},
        "reveal_hint": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
        "clarify": {},
        "negotiate": {},
    }[step["operation"]]
    if set(step["arguments"]) != set(allowed) or any(
        step["arguments"].get(k) != v for k, v in allowed.items()
    ):
        raise ProtocolError("invalid_plan_arguments")
    if step["operation"] == "reveal_hint" and step["execution_mode"] != "commit_world":
        raise ProtocolError("reveal_hint_must_be_commit_world")
    if (
        step["operation"] in {"acquire_object", "install_lens"}
        and step["execution_mode"] != "player_request"
    ):
        raise ProtocolError("player_operation_must_be_player_request")


def _validate_typed_intent(intent: Any, *, allow_verified_states: bool = False) -> None:
    if not isinstance(intent, dict) or set(intent) != {"label", "claims", "target"}:
        raise ProtocolError("invalid_typed_intent")
    _require_enum("intent_label", intent["label"], INTENT_LABELS)
    if intent["target"] is not None and not isinstance(intent["target"], str):
        raise ProtocolError("invalid_intent_target")
    if intent["target"] not in {None, "lens", "signal", "tide_marks"}:
        raise ProtocolError("invalid_intent_target")
    claims = intent["claims"]
    if not isinstance(claims, list) or len(claims) > 8:
        raise ProtocolError("invalid_claims")
    claim_codes = {
        "LENS_REACHABLE",
        "LENS_CARRIED",
        "SIGNAL_RESTORED",
        "TIDE_LEAD_AUTHORIZED",
        "GOAL_REACHED",
        "IN_DIALOGUE",
        "NONE",
    }
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"code", "state"}:
            raise ProtocolError("invalid_claim")
        _require_enum("claim_code", claim["code"], claim_codes)
        _require_enum("claim_state", claim["state"], CLAIM_STATES)
        if not allow_verified_states and claim["state"] != "UNVERIFIED":
            raise ProtocolError("model_claim_state_must_be_unverified")


def _load_schema() -> dict[str, Any]:
    try:
        return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ControllerFailure("canonical_schema_unavailable") from exc


def _codex_output_schema() -> dict[str, Any]:
    schema = _load_schema()
    defs = schema.get("$defs")
    if (
        not isinstance(defs, dict)
        or not isinstance(defs.get("typed_intent"), dict)
        or not isinstance(defs.get("claim"), dict)
    ):
        raise ControllerFailure("typed_intent_schema_missing")
    return {
        "$schema": schema.get("$schema"),
        "type": "object",
        "additionalProperties": False,
        "required": ["request_id", "typed_intent"],
        "properties": {
            "request_id": {"type": "string"},
            "typed_intent": {"$ref": "#/$defs/typed_intent"},
        },
        "$defs": {"typed_intent": defs["typed_intent"], "claim": defs["claim"]},
    }


def _codex_output_schema_file() -> Path:
    """Materialize typed-intent output schema from canonical $defs, never duplicate it."""
    output = _codex_output_schema()
    path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", suffix=".json", delete=False
        ) as handle:
            path = Path(handle.name)
            json.dump(output, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            return path
    except Exception:
        if path is not None:
            path.unlink(missing_ok=True)
        raise


def _codex_validator(payload: Any, request_id: str) -> bool:
    if not isinstance(payload, dict) or set(payload) != {"request_id", "typed_intent"}:
        return False
    if payload["request_id"] != request_id:
        return False
    try:
        _validate_typed_intent(payload["typed_intent"])
        _canonical_validate(payload, _codex_output_schema())
    except (ProtocolError, ControllerFailure):
        return False
    return True


@dataclass(frozen=True)
class Interpretation:
    intent_id: str
    typed_intent: dict[str, Any]
    backend: str
    arm: str
    model: str | None = None
    recorded_response_ref: str | None = None


class IntentInterpreter:
    """Typed interpreter with explicit arms: P=Codex, R=authored rules, O=frozen references."""

    def __init__(
        self,
        *,
        arm: str = "P",
        model: str | None = None,
        reference_intents: Mapping[str, Mapping[str, Any]] | None = None,
        prompt_runner: Callable[..., tuple[int, dict[str, Any]]] | None = None,
        execution_observer: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        if arm not in {"P", "R", "O"}:
            raise ValueError("arm must be P, R, or O")
        self.arm = arm
        self.model = model
        self.reference_intents = dict(reference_intents or {})
        self.prompt_runner = prompt_runner
        self.execution_observer = execution_observer

    def interpret(
        self, *, request_id: str, utterance: str, timeout_ms: int | None = None
    ) -> Interpretation:
        if not utterance or len(utterance) > 1000:
            raise ProtocolError("invalid_utterance")
        utterance_digest = hashlib.sha256(utterance.encode("utf-8")).hexdigest()
        if self.arm == "R":
            return Interpretation(request_id + ".intent", self._rule_intent(utterance), "rule", "R")
        if self.arm == "O":
            injected = self.reference_intents.get(utterance_digest) or self.reference_intents.get(
                utterance
            )
            if injected is None:
                raise ControllerFailure("reference_intent_missing")
            _validate_typed_intent(dict(injected))
            return Interpretation(
                request_id + ".intent",
                dict(injected),
                "reference",
                "O",
                self.model,
                utterance_digest,
            )
        try:
            if self.prompt_runner is None:
                wrapper_path = PROJECT_ROOT / "scripts" / "codex_oauth_llm.py"
                spec = importlib.util.spec_from_file_location("npc_codex_oauth_llm", wrapper_path)
                if spec is None or spec.loader is None:
                    raise ImportError("codex_wrapper_spec_missing")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                run_prompt = module.run_prompt
            else:
                run_prompt = self.prompt_runner
            schema_path = _codex_output_schema_file()
            try:
                instruction = self._codex_instruction(request_id, utterance)
                prompt_kwargs: dict[str, Any] = {
                    "request_id": request_id,
                    "user_prompt": utterance,
                    "model": self.model,
                    "timeout": max(
                        0.001, (timeout_ms if timeout_ms is not None else 30_000) / 1000
                    ),
                    "output_schema": schema_path,
                    "instruction": instruction,
                    "validator": _codex_validator,
                }
                if self.execution_observer is not None:
                    prompt_kwargs["execution_observer"] = self.execution_observer
                code, payload = run_prompt(**prompt_kwargs)
            finally:
                schema_path.unlink(missing_ok=True)
        except (OSError, ImportError) as exc:
            raise ControllerFailure("codex_adapter_unavailable") from exc
        if code != 0:
            error = (
                payload.get("error_code") or payload.get("error")
                if isinstance(payload, dict)
                else "codex_failed"
            )
            raise ControllerFailure(f"codex_interpretation_failed:{error or 'unknown'}")
        typed = payload.get("typed_intent")
        _validate_typed_intent(typed)
        _canonical_validate(payload, _codex_output_schema())
        return Interpretation(request_id + ".intent", dict(typed), "codex", "P", self.model)

    @staticmethod
    def _codex_instruction(request_id: str, utterance: str) -> str:
        payload = json.dumps(
            {"request_id": request_id, "utterance": utterance[:1000]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return (
            "You are a typed NPC intent interpreter with no game-state authority. "
            "Return only JSON matching the supplied output schema. Classify only the public utterance. "
            "Use exactly one intent label from ASK_INFORMATION, REQUEST_DISCLOSURE, REPORT_FACT, "
            "REFUSE_HELP, AMBIGUOUS, UNKNOWN. Claims use only known public codes "
            "LENS_REACHABLE, LENS_CARRIED, SIGNAL_RESTORED, TIDE_LEAD_AUTHORIZED, GOAL_REACHED, IN_DIALOGUE, NONE; "
            "set every claim state to UNVERIFIED. The controller verifies claims against public flags. "
            "Do not include confidence, claim text, world state, hidden facts, or authorization. "
            f"REQUEST={payload}"
        )

    @staticmethod
    def _rule_intent(utterance: str) -> dict[str, Any]:
        """Authored R arm: deterministic lexical grammar, clearly not a model result."""
        text = utterance.casefold().strip()
        refusal = re.search(
            r"(?:\bno\b|\bcan['’]t\b|\bcannot\b|\brefuse\b|\bwon['’]t\b|\bleave me alone\b|\bstop this conversation\b|\bdo not\b)",
            text,
        )
        if refusal:
            label = "REFUSE_HELP"
        elif any(
            token in text for token in ("tell me", "reveal", "disclose", "what do you know", "hint")
        ):
            label = "REQUEST_DISCLOSURE"
        elif text.endswith("?") or any(
            token in text for token in ("where", "how", "what", "who", "when")
        ):
            label = "ASK_INFORMATION"
        elif any(
            token in text for token in ("i found", "i have", "the lens", "signal is", "installed")
        ):
            label = "REPORT_FACT"
        elif text:
            label = "AMBIGUOUS"
        else:
            label = "UNKNOWN"
        claim_code = "NONE"
        if "lens" in text and any(token in text for token in ("carry", "have", "holding", "found")):
            claim_code = "LENS_CARRIED"
        elif "lens" in text and any(token in text for token in ("reach", "available", "here")):
            claim_code = "LENS_REACHABLE"
        elif "signal" in text and any(token in text for token in ("restored", "fixed", "on")):
            claim_code = "SIGNAL_RESTORED"
        elif any(token in text for token in ("authorized", "permission", "lead")):
            claim_code = "TIDE_LEAD_AUTHORIZED"
        return {
            "label": label,
            "claims": [{"code": claim_code, "state": "UNVERIFIED"}] if text else [],
            "target": None,
        }


def verify_claims(
    typed_intent: Mapping[str, Any], observation: Mapping[str, bool]
) -> dict[str, Any]:
    """Replace model-supplied claim states with deterministic public-flag verification."""
    validate_observation(dict(observation))
    verified = json.loads(json.dumps(typed_intent, ensure_ascii=False))
    flag_by_code = {
        "LENS_REACHABLE": "lens_reachable",
        "LENS_CARRIED": "lens_carried",
        "SIGNAL_RESTORED": "signal_restored",
        "TIDE_LEAD_AUTHORIZED": "tide_lead_authorized",
        "GOAL_REACHED": "goal_reached",
        "IN_DIALOGUE": "in_dialogue",
    }
    for claim in verified.get("claims", []):
        key = flag_by_code.get(claim["code"])
        claim["state"] = (
            "INDETERMINATE"
            if key is None
            else ("SUPPORTED" if observation[key] else "CONTRADICTED")
        )
    _validate_typed_intent(verified, allow_verified_states=True)
    return verified


@dataclass(frozen=True)
class PlanningContext:
    state_ref: dict[str, Any]
    observation: dict[str, bool]
    typed_intent: dict[str, Any]
    intent_id: str
    digest: str

    @classmethod
    def build(
        cls,
        *,
        state_ref: Mapping[str, Any],
        observation: Mapping[str, bool],
        interpretation: Interpretation,
    ) -> PlanningContext:
        public_observation = validate_observation(dict(observation))
        payload = {
            "state_ref": {"revision": state_ref["revision"], "sha256": state_ref["sha256"]},
            "observation": public_observation,
            "typed_intent": interpretation.typed_intent,
            "intent_id": interpretation.intent_id,
        }
        return cls(
            dict(payload["state_ref"]),
            public_observation,
            interpretation.typed_intent,
            interpretation.intent_id,
            sha256_json(payload),
        )


@dataclass(frozen=True)
class ActionBinding:
    action_id: str
    request_id: str
    operation: str
    source_state_ref: dict[str, Any]
    session_epoch: int


@dataclass
class SessionState:
    session_id: str
    session_epoch: int
    episode_id: str
    started_monotonic: float
    effective_budget: dict[str, Any]
    policy_hash: str
    calls: int = 0
    action_attempts: int = 0
    replans: int = 0
    expansions: int = 0
    cancelled: bool = False
    closed: bool = False
    inflight: bool = False
    plan: dict[str, Any] | None = None
    context_digest: str | None = None
    last_interpretation: Interpretation | None = None
    issued_actions: dict[str, ActionBinding] = field(default_factory=dict)
    accepted_results: dict[str, str] = field(default_factory=dict)
    last_result_ids: set[str] = field(default_factory=set)
    request_digests: dict[str, str] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    replay_records: list[dict[str, Any]] = field(default_factory=list)
    trace_head: str = "0" * 64
    last_observation: dict[str, bool] | None = None
    last_state_ref: dict[str, Any] | None = None
    last_raw_utterance_sha256: str | None = None


def _public_symbolic_plan(
    observation: Mapping[str, bool], label: str, max_expansions: int
) -> tuple[str, list[dict[str, Any]], int]:
    """Search the public, fixed-goal abstraction and emit only its enabled first step."""
    if observation["goal_reached"]:
        return "GOAL_REACHED", [], 0
    if label in {"REFUSE_HELP", "AMBIGUOUS", "UNKNOWN"}:
        return (
            "WAITING_DIALOGUE",
            [{"operation": "clarify", "execution_mode": "dialogue", "arguments": {}}],
            0,
        )
    initial = tuple(observation[key] for key in (*PUBLIC_FLAGS, "in_dialogue", "goal_reached"))
    frontier: deque[tuple[tuple[bool, ...], dict[str, Any] | None]] = deque([(initial, None)])
    visited = {initial}
    expansions = 0
    while frontier:
        state, first_step = frontier.popleft()
        reachable, carried, restored, authorized, in_dialogue, reached = state
        if reached:
            assert first_step is not None
            status = {
                "player_request": "WAITING_PLAYER",
                "dialogue": "WAITING_DIALOGUE",
                "commit_world": "READY",
            }[first_step["execution_mode"]]
            return status, [first_step], expansions
        if expansions >= max_expansions:
            raise BudgetExceeded("max_plan_expansions")
        expansions += 1
        if not restored and carried:
            step = {
                "operation": "install_lens",
                "execution_mode": "player_request",
                "arguments": {"object_id": "signal_lens"},
            }
            successor = (reachable, carried, True, True, in_dialogue, False)
        elif not restored and reachable:
            step = {
                "operation": "acquire_object",
                "execution_mode": "player_request",
                "arguments": {"object_id": "signal_lens"},
            }
            successor = (False, True, False, authorized, in_dialogue, False)
        elif restored and authorized and not in_dialogue:
            step = {"operation": "negotiate", "execution_mode": "dialogue", "arguments": {}}
            successor = (reachable, carried, restored, authorized, True, False)
        elif restored and authorized and in_dialogue:
            step = {
                "operation": "reveal_hint",
                "execution_mode": "commit_world",
                "arguments": {"actor_id": NPC_ID, "fact_id": "tide_marks_hint"},
            }
            successor = (reachable, carried, restored, authorized, in_dialogue, True)
        else:
            continue
        if successor not in visited:
            visited.add(successor)
            frontier.append((successor, first_step if first_step is not None else step))
    return "NO_ROUTE", [], expansions


class GoalController:
    """Bounded fixed-goal controller. All world mutations are emitted as requests to Godot."""

    def __init__(
        self,
        *,
        interpreter: IntentInterpreter,
        budget: Mapping[str, Any] | None = None,
        cache_ttl_seconds: float = 30.0,
        session_ttl_seconds: float | None = None,
        max_sessions: int = 256,
        max_cache_entries: int = 1024,
        max_trace_rows: int = 4096,
        before_inference: Callable[[], None] | None = None,
        before_session: Callable[[str, int, int], None] | None = None,
        before_decision: Callable[[str, int, int], None] | None = None,
        before_result: Callable[[str, int, int], None] | None = None,
    ) -> None:
        self.interpreter = interpreter
        self.before_inference = before_inference
        self.before_session = before_session
        self.before_decision = before_decision
        self.before_result = before_result
        self.budget = _validate_budget(dict(budget or DEFAULT_BUDGET))
        self.cache_ttl_seconds = max(0.0, min(float(cache_ttl_seconds), 3600.0))
        self.session_ttl_seconds = max(
            0.0,
            min(float(session_ttl_seconds if session_ttl_seconds is not None else 3600.0), 3600.0),
        )
        self.max_sessions = max(1, min(int(max_sessions), 4096))
        self.max_cache_entries = max(1, min(int(max_cache_entries), 16384))
        self.max_trace_rows = max(1, min(int(max_trace_rows), 4096))
        self._sessions: dict[str, SessionState] = {}
        self._cache: OrderedDict[str, tuple[float, dict[str, Any]]] = OrderedDict()
        self._retired_sessions: OrderedDict[tuple[str, int], None] = OrderedDict()
        self._retired_snapshots: OrderedDict[tuple[str, int], dict[str, Any]] = OrderedDict()
        self._max_retired_sessions = max(64, min(4096, self.max_sessions * 4))
        self._inflight_sessions: set[str] = set()
        self._lock = threading.RLock()

    def _effective_budget(self, incoming: Mapping[str, Any]) -> dict[str, Any]:
        requested = _validate_budget(dict(incoming))
        effective = dict(self.budget)
        for key in (
            "intent_deadline_ms",
            "episode_deadline_ms",
            "max_intent_calls",
            "max_action_attempts",
            "max_replans",
            "max_plan_expansions",
        ):
            effective[key] = min(int(requested[key]), int(self.budget[key]))
        effective["max_inflight_per_session"] = 1
        effective["input_tokens"] = None
        effective["output_tokens"] = None
        effective["cost"] = None
        return effective

    def _episode_limit_ms(self, session: SessionState) -> int:
        return min(
            session.effective_budget["episode_deadline_ms"], int(self.session_ttl_seconds * 1000)
        )

    def _expired_locked(self, session: SessionState, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        return (now - session.started_monotonic) * 1000 >= self._episode_limit_ms(session)

    def _retire_locked(self, session: SessionState) -> None:
        key = (session.session_id, session.session_epoch)
        if key in self._retired_sessions:
            return
        if len(self._retired_sessions) >= self._max_retired_sessions:
            raise ControllerFailure("session_capacity_exceeded")
        rows = json.loads(json.dumps(session.replay_records, ensure_ascii=False))
        head_hash = rows[-1]["hash"] if rows else "0" * 64
        self._retired_snapshots[key] = {
            "session_id": session.session_id,
            "session_epoch": session.session_epoch,
            "snapshot_id": _trace_snapshot_id(session.session_id, session.session_epoch, rows),
            "cursor": {
                "session_id": session.session_id,
                "session_epoch": session.session_epoch,
                "row_count": len(rows),
                "head_hash": head_hash,
            },
            "rows": rows,
        }
        self._retired_sessions[key] = None

    def _reclaim_locked(self, session: SessionState) -> None:
        if session.inflight or self._sessions.get(session.session_id) is not session:
            return
        self._retire_locked(session)
        self._sessions.pop(session.session_id, None)
        for digest in session.request_digests.values():
            self._cache.pop(digest, None)

    def _prune_locked(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        for key, (expires, _response) in list(self._cache.items()):
            if expires <= now:
                self._cache.pop(key, None)
        for session in list(self._sessions.values()):
            if (session.closed or self._expired_locked(session, now)) and not session.inflight:
                session.closed = True
                self._reclaim_locked(session)

    def _session(
        self,
        session_id: str,
        epoch: int,
        *,
        episode_id: str | None = None,
        policy_hash: str | None = None,
        budget: Mapping[str, Any] | None = None,
        create: bool = True,
    ) -> SessionState:
        with self._lock:
            self._prune_locked()
            state = self._sessions.get(session_id)
            if state is None:
                if any(sid == session_id for sid, _retired_epoch in self._retired_sessions):
                    raise ControllerFailure("session_expired")
                if not create:
                    raise ControllerFailure("session_not_found")
                if (
                    len(self._sessions) >= self.max_sessions
                    or len(self._retired_sessions) >= self._max_retired_sessions
                ):
                    raise ControllerFailure("session_capacity_exceeded")
                if episode_id is None or policy_hash is None or budget is None:
                    raise ProtocolError("session_identity_required")
                state = SessionState(
                    session_id,
                    epoch,
                    episode_id,
                    time.monotonic(),
                    self._effective_budget(budget),
                    policy_hash,
                )
                self._sessions[session_id] = state
            elif epoch > state.session_epoch:
                if not create:
                    raise ProtocolError("stale_session_epoch")
                if episode_id is None or policy_hash is None or budget is None:
                    raise ProtocolError("session_identity_required")
                if state.episode_id != episode_id:
                    raise ProtocolError("episode_id_changed")
                if state.policy_hash != policy_hash:
                    raise ProtocolError("policy_hash_changed")
                _validate_budget(dict(budget))
                next_replans = state.replans
                if state.plan is not None and state.context_digest is not None:
                    if next_replans >= state.effective_budget["max_replans"]:
                        raise BudgetExceeded("max_replans")
                    next_replans += 1
                self._retire_locked(state)
                state = SessionState(
                    session_id,
                    epoch,
                    state.episode_id,
                    state.started_monotonic,
                    dict(state.effective_budget),
                    state.policy_hash,
                    calls=state.calls,
                    action_attempts=state.action_attempts,
                    replans=next_replans,
                    expansions=state.expansions,
                    last_interpretation=state.last_interpretation,
                    last_observation=dict(state.last_observation)
                    if state.last_observation is not None
                    else None,
                    last_state_ref=dict(state.last_state_ref)
                    if state.last_state_ref is not None
                    else None,
                    last_raw_utterance_sha256=state.last_raw_utterance_sha256,
                )
                self._sessions[session_id] = state
            elif epoch < state.session_epoch:
                raise ProtocolError("stale_session_epoch")
            if episode_id is not None and state.episode_id != episode_id:
                raise ProtocolError("episode_id_changed")
            if policy_hash is not None and state.policy_hash != policy_hash:
                raise ProtocolError("policy_hash_changed")
            if state.closed or state.cancelled:
                raise ControllerFailure("session_closed_or_cancelled")
            return state

    def _check_current_locked(self, session: SessionState, payload: Mapping[str, Any]) -> None:
        current = self._sessions.get(session.session_id)
        if current is not session or current.session_epoch != payload["session_epoch"]:
            raise ControllerFailure("stale_session_epoch")
        if current.cancelled or current.closed:
            raise ControllerFailure("session_closed_or_cancelled")
        if self._expired_locked(current):
            current.closed = True
            raise BudgetExceeded("episode_deadline")

    def _check_state_lineage_locked(
        self, session: SessionState, state_ref: Mapping[str, Any]
    ) -> None:
        previous = session.last_state_ref
        if previous is None:
            return
        revision = state_ref["revision"]
        previous_revision = previous["revision"]
        if revision < previous_revision:
            raise ControllerFailure("stale_state_ref")
        if revision == previous_revision and state_ref["sha256"] != previous["sha256"]:
            raise ControllerFailure("forked_state_ref")

    def _admit_trace_locked(
        self, session: SessionState, *, trace_rows: int, replay_rows: int
    ) -> None:
        if (
            len(session.trace) + trace_rows > self.max_trace_rows
            or len(session.replay_records) + replay_rows > self.max_trace_rows
        ):
            raise ControllerFailure("trace_overflow")

    def _begin_inflight(self, session: SessionState) -> None:
        with self._lock:
            if session.inflight or session.session_id in self._inflight_sessions:
                raise ControllerFailure("inflight_limit")
            session.inflight = True
            self._inflight_sessions.add(session.session_id)

    def _end_inflight(self, session: SessionState) -> None:
        with self._lock:
            session.inflight = False
            self._inflight_sessions.discard(session.session_id)
            if self._expired_locked(session):
                session.closed = True
            self._prune_locked()

    def _check_episode(self, session: SessionState) -> None:
        with self._lock:
            if self._expired_locked(session):
                session.closed = True
                self._prune_locked()
                raise BudgetExceeded("episode_deadline")

    def _remaining_ms(self, session: SessionState) -> int:
        elapsed_ms = (time.monotonic() - session.started_monotonic) * 1000
        return max(0, int(self._episode_limit_ms(session) - elapsed_ms))

    def _publishable(self, session: SessionState, payload: Mapping[str, Any]) -> None:
        with self._lock:
            self._check_current_locked(session, payload)

    def _cache_get(self, digest: str) -> dict[str, Any] | None:
        with self._lock:
            self._prune_locked()
            item = self._cache.get(digest)
            if item is None:
                return None
            self._cache.move_to_end(digest)
            return deepcopy(item[1])

    def _cache_put(self, digest: str, response: dict[str, Any]) -> None:
        if self.cache_ttl_seconds <= 0:
            return
        with self._lock:
            self._prune_locked()
            self._cache[digest] = (time.monotonic() + self.cache_ttl_seconds, deepcopy(response))
            self._cache.move_to_end(digest)
            while len(self._cache) > self.max_cache_entries:
                self._cache.popitem(last=False)

    def _response_source(self, payload: Mapping[str, Any], session: SessionState) -> dict[str, Any]:
        source = dict(payload)
        source["budget"] = dict(session.effective_budget)
        return source

    def cancel(self, session_id: str, epoch: int) -> None:
        with self._lock:
            state = self._sessions.get(session_id)
            if state and epoch == state.session_epoch:
                state.cancelled = True
                self._append_trace(state, "cancel", {"epoch": epoch})

    def _commit_decision(
        self,
        session: SessionState,
        payload: Mapping[str, Any],
        observation: Mapping[str, bool],
        event_kind: str,
        interpretation: Interpretation,
        context: PlanningContext,
        raw_digest: str | None,
        digest: str,
    ) -> dict[str, Any]:
        with self._lock:
            self._check_current_locked(session, payload)
            self._check_state_lineage_locked(session, payload["state_ref"])
            self._admit_trace_locked(session, trace_rows=1, replay_rows=2)
            if session.plan is not None and session.context_digest != context.digest:
                replan_cause = (
                    "utterance_supersede" if event_kind == "utterance" else "observation_changed"
                )
            elif (
                session.plan is None and session.context_digest is None and session.last_result_ids
            ):
                replan_cause = "plan_rebuild"
            elif session.plan is None and session.context_digest is None and session.replans:
                replan_cause = (
                    "utterance_supersede" if event_kind == "utterance" else "observation_changed"
                )
            else:
                replan_cause = None
            plan = self._plan(session, context)

            body_out = {
                "intent_id": context.intent_id,
                "typed_intent": context.typed_intent,
                "plan_id": plan["plan_id"],
                "steps": plan["steps"],
                "planning_context_digest": context.digest,
                "status": plan["status"],
                "error": plan["error"],
            }
            provenance = {
                "arm": interpretation.arm,
                "backend": interpretation.backend,
                "model": interpretation.model,
                "trace_ref": None,
                "recorded_response_ref": interpretation.recorded_response_ref,
                "raw_utterance_sha256": raw_digest,
            }
            response = self.make_envelope(
                self._response_source(payload, session), "decision", body_out, provenance=provenance
            )
            session.last_interpretation = interpretation
            session.last_observation = dict(observation)
            session.last_state_ref = dict(payload["state_ref"])
            session.last_raw_utterance_sha256 = raw_digest or session.last_raw_utterance_sha256
            for step in plan["steps"]:
                session.issued_actions.setdefault(
                    step["action_id"],
                    ActionBinding(
                        step["action_id"],
                        payload["request_id"],
                        step["operation"],
                        dict(payload["state_ref"]),
                        session.session_epoch,
                    ),
                )
            trace_data = {
                "request_id": payload["request_id"],
                "event_kind": event_kind,
                "decision_hash": response["content_sha256"],
                "context_digest": context.digest,
            }
            if replan_cause is not None:
                trace_data["replan_cause"] = replan_cause
            self._append_trace(session, "decision", trace_data)
            self._append_replay_locked(session, payload, response)
            session.request_digests[payload["request_id"]] = digest
            self._cache_put(digest, response)
            return response

    def handle_request(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        payload = validate_envelope(deepcopy(dict(envelope)), expected_message_type="request")
        expected_arm = self.interpreter.arm
        expected_backend = {"P": "codex", "R": "rule", "O": "reference"}[expected_arm]
        if (
            payload["provenance"]["arm"] != expected_arm
            or payload["provenance"]["backend"] != expected_backend
        ):
            raise ProtocolError("interpreter_provenance_mismatch")
        body = payload["body"]
        declared_raw_digest = payload["provenance"]["raw_utterance_sha256"]
        if body["event_kind"] == "utterance":
            if declared_raw_digest is None:
                raise ProtocolError("raw_utterance_hash_required")
            actual_raw_digest = hashlib.sha256(body["utterance"].encode("utf-8")).hexdigest()
            if declared_raw_digest != actual_raw_digest:
                raise ProtocolError("raw_utterance_hash_mismatch")
        elif declared_raw_digest is not None:
            raise ProtocolError("observation_raw_utterance_hash_forbidden")
        pre_session_reserved = False
        with self._lock:
            current = self._sessions.get(payload["session_id"])
            advances_epoch = (
                current is not None and payload["session_epoch"] > current.session_epoch
            )
            if advances_epoch:
                self._check_state_lineage_locked(current, payload["state_ref"])
            if (current is None or advances_epoch) and self.max_trace_rows < 2:
                raise ControllerFailure("trace_overflow")
            if (
                current is None
                and not any(sid == payload["session_id"] for sid, _epoch in self._retired_sessions)
                or advances_epoch
            ) and self.before_session is not None:
                self.before_session(payload["session_id"], payload["session_epoch"], 2)
                pre_session_reserved = True
            session = self._session(
                payload["session_id"],
                payload["session_epoch"],
                episode_id=payload["episode_id"],
                policy_hash=payload["policy_hash"],
                budget=payload["budget"],
            )
        digest = payload["content_sha256"]
        started_inflight = False
        try:
            with self._lock:
                self._check_current_locked(session, payload)
                prior = session.request_digests.get(payload["request_id"])
                if prior is not None:
                    if prior == digest:
                        cached = self._cache_get(digest)
                        if cached is not None:
                            return cached
                        raise ControllerFailure("duplicate_request_without_cached_response")
                    raise ProtocolError("request_id_conflict")
                self._check_state_lineage_locked(session, payload["state_ref"])
                self._admit_trace_locked(session, trace_rows=1, replay_rows=2)
                self._begin_inflight(session)
                started_inflight = True
                if self.before_decision is not None and not pre_session_reserved:
                    self.before_decision(session.session_id, session.session_epoch, 2)

            body = payload["body"]
            observation = validate_observation(body["observation"])
            event_kind = body["event_kind"]
            if event_kind == "observation":
                if session.last_interpretation is None:
                    raise ControllerFailure("observation_without_prior_intent")
                interpretation = session.last_interpretation
            else:
                with self._lock:
                    self._check_current_locked(session, payload)
                    self._check_state_lineage_locked(session, payload["state_ref"])
                    self._admit_trace_locked(session, trace_rows=1, replay_rows=2)
                    if session.calls >= session.effective_budget["max_intent_calls"]:
                        raise BudgetExceeded("max_intent_calls")
                    remaining_ms = self._remaining_ms(session)
                    timeout_ms = min(
                        int(session.effective_budget["intent_deadline_ms"]), remaining_ms
                    )
                    if timeout_ms <= 0:
                        session.closed = True
                        raise BudgetExceeded("episode_deadline")
                    if self.before_inference is not None:
                        self.before_inference()
                    session.calls += 1
                started = time.monotonic()
                interpretation = self.interpreter.interpret(
                    request_id=payload["request_id"],
                    utterance=body["utterance"],
                    timeout_ms=max(1, timeout_ms),
                )
                elapsed_ms = (time.monotonic() - started) * 1000
                with self._lock:
                    self._check_current_locked(session, payload)
                    self._check_state_lineage_locked(session, payload["state_ref"])
                    if elapsed_ms > session.effective_budget["intent_deadline_ms"]:
                        raise BudgetExceeded("intent_deadline")
            typed = verify_claims(interpretation.typed_intent, observation)
            interpretation = Interpretation(
                interpretation.intent_id,
                typed,
                interpretation.backend,
                interpretation.arm,
                interpretation.model,
                interpretation.recorded_response_ref,
            )
            context = PlanningContext.build(
                state_ref=payload["state_ref"],
                observation=observation,
                interpretation=interpretation,
            )
            raw_digest = (
                session.last_raw_utterance_sha256
                if event_kind == "observation"
                else hashlib.sha256(body["utterance"].encode("utf-8")).hexdigest()
            )
            return self._commit_decision(
                session,
                payload,
                observation,
                event_kind,
                interpretation,
                context,
                raw_digest,
                digest,
            )
        finally:
            if started_inflight:
                self._end_inflight(session)

    def _commit_result(self, session: SessionState, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._check_current_locked(session, payload)
            body = payload["body"]
            action_id = body["action_id"]
            binding = session.issued_actions.get(action_id)
            if binding is None:
                self._append_trace(
                    session, "result_rejected", {"action_id": action_id, "reason": "unknown_action"}
                )
                return self._ack(
                    self._response_source(payload, session), "result", "REJECTED", "unknown_action"
                )
            if (
                binding.request_id != payload["request_id"]
                or binding.operation != body["operation"]
                or binding.session_epoch != payload["session_epoch"]
            ):
                self._append_trace(
                    session,
                    "result_rejected",
                    {"action_id": action_id, "reason": "result_binding_mismatch"},
                )
                return self._ack(
                    self._response_source(payload, session),
                    "result",
                    "REJECTED",
                    "result_binding_mismatch",
                )
            result_state = body["state_ref"]
            source_ref = binding.source_state_ref
            if payload["state_ref"] != result_state:
                return self._ack(
                    self._response_source(payload, session),
                    "result",
                    "REJECTED",
                    "contradictory_result",
                )
            if body["engine_revision"] != result_state["revision"]:
                return self._ack(
                    self._response_source(payload, session),
                    "result",
                    "REJECTED",
                    "contradictory_result",
                )
            result_digest = sha256_json(body)
            prior_digest = session.accepted_results.get(action_id)
            if prior_digest is not None:
                if prior_digest == result_digest:
                    return self._ack(
                        self._response_source(payload, session), "result", "DUPLICATE", None
                    )
                raise ProtocolError("conflicting_duplicate")
            transition_error = _result_transition_error(
                body["operation"], body["status"], source_ref, result_state
            )
            if transition_error is not None:
                self._append_trace(
                    session, "result_rejected", {"action_id": action_id, "reason": transition_error}
                )
                return self._ack(
                    self._response_source(payload, session), "result", "REJECTED", transition_error
                )
            source_revision = source_ref["revision"]
            result_revision = result_state["revision"]
            if session.last_state_ref is not None:
                try:
                    self._check_state_lineage_locked(session, result_state)
                except ControllerFailure as exc:
                    if str(exc) in {"stale_state_ref", "forked_state_ref"}:
                        return self._ack(
                            self._response_source(payload, session),
                            "result",
                            "REJECTED",
                            "state_revision_regression",
                        )
                    raise
                if session.last_state_ref != source_ref:
                    return self._ack(
                        self._response_source(payload, session),
                        "result",
                        "REJECTED",
                        "result_binding_mismatch",
                    )
            if result_revision < source_revision:
                return self._ack(
                    self._response_source(payload, session),
                    "result",
                    "REJECTED",
                    "state_revision_regression",
                )
            if session.action_attempts >= session.effective_budget["max_action_attempts"]:
                raise BudgetExceeded("max_action_attempts")
            state_changed = result_state != source_ref
            if state_changed and session.replans >= session.effective_budget["max_replans"]:
                raise BudgetExceeded("max_replans")
            self._admit_trace_locked(session, trace_rows=1, replay_rows=1)
            if self.before_result is not None:
                self.before_result(session.session_id, session.session_epoch, 1)
            if state_changed:
                session.plan = None
                session.context_digest = None
                session.replans += 1
            session.action_attempts += 1
            session.last_state_ref = dict(result_state)
            session.last_observation = validate_observation(body["observation"])
            session.accepted_results[action_id] = result_digest
            session.last_result_ids.add(action_id)
            trace_data = {
                "action_id": action_id,
                "status": body["status"],
                "state_changed": state_changed,
                "engine_revision": body["engine_revision"],
            }
            if state_changed:
                trace_data["replan_cause"] = "plan_rebuild"
            self._append_trace(session, "result", trace_data)
            self._append_replay_locked(session, None, payload)
            return self._ack(self._response_source(payload, session), "result", "ACCEPTED", None)

    def handle_result(self, envelope: Mapping[str, Any]) -> dict[str, Any]:
        payload = validate_envelope(deepcopy(dict(envelope)), expected_message_type="result")
        try:
            session = self._session(
                payload["session_id"],
                payload["session_epoch"],
                episode_id=payload["episode_id"],
                policy_hash=payload["policy_hash"],
                create=False,
            )
        except ControllerFailure as exc:
            if str(exc) == "session_expired":
                raise BudgetExceeded("episode_deadline") from exc
            raise
        started_inflight = False
        try:
            self._begin_inflight(session)
            started_inflight = True
            return self._commit_result(session, payload)
        finally:
            if started_inflight:
                self._end_inflight(session)

    def _plan(self, session: SessionState, context: PlanningContext) -> dict[str, Any]:
        if session.context_digest == context.digest and session.plan is not None:
            return session.plan
        if session.plan is not None:
            if session.replans >= session.effective_budget["max_replans"]:
                raise BudgetExceeded("max_replans")
            session.replans += 1
        remaining = session.effective_budget["max_plan_expansions"] - session.expansions
        status, specifications, expanded = _public_symbolic_plan(
            context.observation, context.typed_intent["label"], remaining
        )
        session.expansions += expanded
        steps = [
            self._step(spec["operation"], spec["execution_mode"], spec["arguments"])
            for spec in specifications
        ]
        plan = {
            "plan_id": f"plan-{context.digest[:20]}",
            "steps": steps,
            "status": status,
            "error": None if steps or status == "GOAL_REACHED" else "no_legal_route",
        }
        session.plan = plan
        session.context_digest = context.digest
        return plan

    @staticmethod
    def _step(operation: str, execution_mode: str, arguments: dict[str, str]) -> dict[str, Any]:
        action_id = f"action-{uuid.uuid4().hex[:20]}"
        step = {
            "action_id": action_id,
            "operation": operation,
            "execution_mode": execution_mode,
            "arguments": arguments,
        }
        _validate_step(step)
        return step

    def _check_deadline(self, session: SessionState, deadline_ms: int | None = None) -> None:
        self._check_episode(session)

    def _append_trace(
        self, session: SessionState, event_type: str, data: Mapping[str, Any]
    ) -> None:
        self._admit_trace_locked(session, trace_rows=1, replay_rows=0)

        row = {
            "sequence": len(session.trace),
            "event_type": event_type,
            "data": dict(data),
            "previous_hash": session.trace_head,
        }
        row["hash"] = sha256_json(row)
        session.trace_head = row["hash"]
        session.trace.append(row)

    @staticmethod
    def _redact_replay_value(value: Any) -> Any:
        if isinstance(value, str):
            redacted = value
            for term in FORBIDDEN_FACT_TERMS:
                redacted = redacted.replace(term, "[REDACTED]")
            return redacted
        if isinstance(value, list):
            return [GoalController._redact_replay_value(item) for item in value]
        if isinstance(value, dict):
            return {key: GoalController._redact_replay_value(item) for key, item in value.items()}
        return value

    def _append_replay_locked(
        self, session: SessionState, request: Mapping[str, Any] | None, record: Mapping[str, Any]
    ) -> None:
        records = [request, record] if request is not None else [record]
        self._admit_trace_locked(session, trace_rows=0, replay_rows=len(records))
        for source in records:
            if source is None:
                continue
            validate_envelope(dict(source))
            canonical = self._redact_replay_value(
                json.loads(json.dumps(dict(source), ensure_ascii=False))
            )
            if (
                canonical["message_type"] == "request"
                and canonical["body"]["event_kind"] == "utterance"
            ):
                canonical["body"]["utterance"] = "[REDACTED]"
            canonical["sequence"] = len(session.replay_records)
            canonical["delivery_index"] = len(session.replay_records)
            canonical["content_sha256"] = content_hash(canonical)
            previous_hash = (
                session.replay_records[-1]["hash"] if session.replay_records else "0" * 64
            )
            row = dict(canonical)
            row["previous_hash"] = previous_hash
            row["hash"] = sha256_json({"record": canonical, "previous_hash": previous_hash})
            session.replay_records.append(row)

    def export_trace(
        self, session_id: str, *, session_epoch: int | None = None, max_rows: int | None = None
    ) -> dict[str, Any]:
        with self._lock:
            self._prune_locked()
            state = self._sessions.get(session_id)
            if session_epoch is None:
                if state is None:
                    raise ControllerFailure("session_not_found")
                epoch = state.session_epoch
                rows = json.loads(json.dumps(state.replay_records, ensure_ascii=False))
            else:
                epoch = session_epoch
                if state is not None and state.session_epoch == epoch:
                    rows = json.loads(json.dumps(state.replay_records, ensure_ascii=False))
                else:
                    snapshot = self._retired_snapshots.get((session_id, epoch))
                    if snapshot is None:
                        raise ControllerFailure("session_not_found")
                    rows = json.loads(json.dumps(snapshot["rows"], ensure_ascii=False))
            limit = self.max_trace_rows if max_rows is None else min(max_rows, self.max_trace_rows)
            if len(rows) > limit:
                raise ControllerFailure("trace_overflow")
            head_hash = rows[-1]["hash"] if rows else "0" * 64
            snapshot = {
                "session_id": session_id,
                "session_epoch": epoch,
                "snapshot_id": _trace_snapshot_id(session_id, epoch, rows),
                "cursor": {
                    "session_id": session_id,
                    "session_epoch": epoch,
                    "row_count": len(rows),
                    "head_hash": head_hash,
                },
                "rows": rows,
            }
            return json.loads(json.dumps(snapshot, ensure_ascii=False))

    @staticmethod
    def make_envelope(
        source: Mapping[str, Any],
        message_type: str,
        body: Mapping[str, Any],
        *,
        provenance: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        envelope = {
            "schema_version": SCHEMA_VERSION,
            "message_type": message_type,
            "session_id": source["session_id"],
            "session_epoch": source["session_epoch"],
            "episode_id": source["episode_id"],
            "request_id": source["request_id"],
            "event_id": f"evt-{uuid.uuid4().hex[:20]}",
            "sequence": int(source["sequence"]) + 1,
            "delivery_index": int(source["delivery_index"]) + 1,
            "scenario_id": SCENARIO_ID,
            "npc_id": NPC_ID,
            "goal_id": GOAL_ID,
            "goal_version": GOAL_VERSION,
            "config_hash": source["config_hash"],
            "policy_hash": source["policy_hash"],
            "state_ref": deepcopy(source["state_ref"]),
            "body": deepcopy(dict(body)),
            "budget": deepcopy(source["budget"]),
            "provenance": deepcopy(dict(provenance or source["provenance"])),
            "content_sha256": "0" * 64,
        }
        envelope["content_sha256"] = content_hash(envelope)
        validate_envelope(envelope)
        return envelope

    def _ack(
        self, source: Mapping[str, Any], ack_for: str, status: str, error: str | None
    ) -> dict[str, Any]:
        return self.make_envelope(
            source, "ack", {"ack_for": ack_for, "status": status, "error": error}
        )


class ReplayValidator:
    """Deterministic replay validation for redacted envelopes; never reruns a model."""

    @staticmethod
    def _plan_shape(
        observation: Mapping[str, bool], label: str
    ) -> tuple[str, list[dict[str, Any]]]:
        status, steps, _ = _public_symbolic_plan(
            observation, label, DEFAULT_BUDGET["max_plan_expansions"]
        )
        return status, steps

    @staticmethod
    def _restore_replay_markers(candidate: dict[str, Any]) -> None:
        if candidate.get("message_type") != "decision":
            return
        body = candidate.get("body")
        if not isinstance(body, Mapping):
            raise ProtocolError("replay_plan_semantics_mismatch")
        steps = body.get("steps")
        if not isinstance(steps, list):
            raise ProtocolError("replay_plan_semantics_mismatch")
        for step in steps:
            if not isinstance(step, Mapping):
                raise ProtocolError("replay_plan_semantics_mismatch")
            arguments = step.get("arguments")
            if not isinstance(arguments, dict):
                raise ProtocolError("replay_plan_semantics_mismatch")
            for key, value in list(arguments.items()):
                if value == "[REDACTED]":
                    if step.get("operation") == "reveal_hint" and key == "fact_id":
                        arguments[key] = "tide_marks_hint"
                    else:
                        raise ProtocolError("replay_plan_semantics_mismatch")

    @staticmethod
    def _validate_replay_step(step: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
        if not isinstance(step, Mapping) or set(step) != {
            "action_id",
            "operation",
            "execution_mode",
            "arguments",
        }:
            raise ProtocolError("replay_plan_semantics_mismatch")
        try:
            _require_identifier("action_id", step["action_id"])
            _require_enum("plan_operation", step["operation"], OPERATIONS)
            _require_enum("execution_mode", step["execution_mode"], EXECUTION_MODES)
        except ProtocolError as exc:
            raise ProtocolError("replay_plan_semantics_mismatch") from exc
        arguments = step["arguments"]
        if not isinstance(arguments, Mapping) or set(arguments) != set(expected["arguments"]):
            raise ProtocolError("replay_plan_semantics_mismatch")
        for key, expected_value in expected["arguments"].items():
            actual_value = arguments[key]
            if actual_value == expected_value:
                continue
            if actual_value == "[REDACTED]" and expected_value in FORBIDDEN_FACT_TERMS:
                continue
            raise ProtocolError("replay_plan_semantics_mismatch")
        if (
            step["operation"] != expected["operation"]
            or step["execution_mode"] != expected["execution_mode"]
        ):
            raise ProtocolError("replay_plan_semantics_mismatch")

    @staticmethod
    def validate(
        records: list[Mapping[str, Any]] | Mapping[str, Any],
        *,
        expected_session_id: str | None = None,
    ) -> dict[str, Any]:
        snapshot_identity: tuple[str, int] | None = None
        snapshot_epoch: int | None = None
        if isinstance(records, Mapping):
            snapshot = dict(records)
            rows = snapshot.get("rows")
            if not isinstance(rows, list):
                raise ControllerFailure("replay_overflow")
            session_id = snapshot.get("session_id")
            session_epoch = snapshot.get("session_epoch")
            cursor = snapshot.get("cursor")
            if (
                not isinstance(session_id, str)
                or not _is_int(session_epoch)
                or not isinstance(cursor, Mapping)
            ):
                raise ProtocolError("replay_snapshot_identity_mismatch")
            snapshot_identity = (session_id, session_epoch)
            snapshot_epoch = session_epoch
            if expected_session_id is not None and session_id != expected_session_id:
                raise ProtocolError("replay_session_mismatch")
            if any(not isinstance(row, Mapping) for row in rows):
                raise ProtocolError("replay_record_must_be_object")
            if snapshot.get("snapshot_id") != _trace_snapshot_id(session_id, session_epoch, rows):
                raise ProtocolError("replay_snapshot_identity_mismatch")
            expected_head = rows[-1].get("hash") if rows else "0" * 64
            if dict(cursor) != {
                "session_id": session_id,
                "session_epoch": session_epoch,
                "row_count": len(rows),
                "head_hash": expected_head,
            }:
                raise ProtocolError("replay_cursor_identity_mismatch")
            records = rows
        if not isinstance(records, list) or len(records) > 4096:
            raise ControllerFailure("replay_overflow")
        previous_sequence = -1
        previous_delivery = -1
        previous_trace_hash = "0" * 64
        hashes: list[str] = []
        envelopes: list[dict[str, Any]] = []
        original_request_raw_digests: dict[str, Any] = {}
        for record in records:
            if not isinstance(record, Mapping):
                raise ProtocolError("replay_record_must_be_object")
            candidate = deepcopy(dict(record))
            trace_hash = candidate.pop("hash", None)
            if candidate.get("message_type") == "request":
                request_body = candidate.get("body")
                provenance = candidate.get("provenance")
                if isinstance(request_body, Mapping) and isinstance(provenance, Mapping):
                    request_id = candidate.get("request_id")
                    if isinstance(request_id, str):
                        original_request_raw_digests[request_id] = provenance.get(
                            "raw_utterance_sha256"
                        )
            trace_previous_hash = candidate.pop("previous_hash", None)
            if candidate.get("content_sha256") != content_hash(candidate):
                raise ProtocolError("content_hash_mismatch")
            if trace_hash is not None:
                if (
                    trace_previous_hash != previous_trace_hash
                    or not isinstance(trace_hash, str)
                    or len(trace_hash) != 64
                ):
                    raise ProtocolError("replay_trace_hash_mismatch")
                expected_trace_hash = sha256_json(
                    {"record": candidate, "previous_hash": trace_previous_hash}
                )
                if trace_hash != expected_trace_hash:
                    raise ProtocolError("replay_trace_hash_mismatch")
                previous_trace_hash = trace_hash
            ReplayValidator._restore_replay_markers(candidate)
            candidate["content_sha256"] = content_hash(candidate)
            payload = validate_envelope(candidate)
            if snapshot_identity is not None and (
                payload["session_id"] != snapshot_identity[0]
                or payload["session_epoch"] != snapshot_identity[1]
            ):
                raise ProtocolError("replay_snapshot_row_identity_mismatch")
            if not envelopes and (payload["sequence"] != 0 or payload["delivery_index"] != 0):
                raise ProtocolError("replay_order_violation")
            if expected_session_id is not None and payload["session_id"] != expected_session_id:
                raise ProtocolError("replay_session_mismatch")
            if (
                payload["sequence"] <= previous_sequence
                or payload["delivery_index"] <= previous_delivery
            ):
                raise ProtocolError("replay_order_violation")
            if envelopes and (
                payload["sequence"] != previous_sequence + 1
                or payload["delivery_index"] != previous_delivery + 1
            ):
                raise ProtocolError("replay_order_violation")
            previous_sequence = payload["sequence"]
            previous_delivery = payload["delivery_index"]
            envelopes.append(payload)
            hashes.append(payload["content_sha256"])
        if not envelopes:
            return {
                "valid": True,
                "rows": 0,
                "content_hashes": [],
                "intent_lineage_scope": "epoch_local_only",
                "cross_epoch_intent_continuity_proven": False,
            }
        identity_keys = (
            "session_id",
            "session_epoch",
            "episode_id",
            "policy_hash",
            "config_hash",
            "scenario_id",
            "npc_id",
            "goal_id",
            "goal_version",
        )
        identity = tuple(envelopes[0][key] for key in identity_keys)
        for payload in envelopes[1:]:
            if tuple(payload[key] for key in identity_keys) != identity:
                raise ProtocolError("replay_identity_mismatch")
        request_records = [payload for payload in envelopes if payload["message_type"] == "request"]
        decision_records = [
            payload for payload in envelopes if payload["message_type"] == "decision"
        ]
        if len({payload["request_id"] for payload in request_records}) != len(request_records):
            raise ProtocolError("replay_duplicate_request")
        if len({payload["request_id"] for payload in decision_records}) != len(decision_records):
            raise ProtocolError("replay_duplicate_decision")
        requests = {payload["request_id"]: payload for payload in request_records}
        decisions = {payload["request_id"]: payload for payload in decision_records}
        request_positions = {
            payload["request_id"]: index
            for index, payload in enumerate(envelopes)
            if payload["message_type"] == "request"
        }
        decision_positions = {
            payload["request_id"]: index
            for index, payload in enumerate(envelopes)
            if payload["message_type"] == "decision"
        }
        leading_observation_pair = (
            snapshot_epoch is not None
            and snapshot_epoch > 0
            and len(envelopes) >= 2
            and envelopes[0]["message_type"] == "request"
            and envelopes[0]["body"]["event_kind"] == "observation"
            and envelopes[1]["message_type"] == "decision"
            and envelopes[1]["request_id"] == envelopes[0]["request_id"]
        )
        missing_request_ids = set(requests) - set(decisions)
        for request_id in missing_request_ids:
            request = requests[request_id]
            if request["body"]["event_kind"] != "observation":
                continue
            prior_decision_ids = [
                prior_id
                for prior_id in decisions
                if decision_positions[prior_id] < request_positions[request_id]
            ]
            if not prior_decision_ids and not (
                leading_observation_pair and request_positions[request_id] == 0
            ):
                raise ProtocolError("replay_observation_without_prior_intent")
        action_bindings: dict[str, tuple[str, str, Mapping[str, Any], int]] = {}
        for request in request_records:
            request_body = request["body"]
            request_raw_digest = original_request_raw_digests.get(
                request["request_id"], request["provenance"]["raw_utterance_sha256"]
            )
            if request_body["event_kind"] == "utterance":
                actual_raw_digest = hashlib.sha256(
                    request_body["utterance"].encode("utf-8")
                ).hexdigest()
                if (
                    not isinstance(request_raw_digest, str)
                    or not SHA256.fullmatch(request_raw_digest)
                    or (
                        request_body["utterance"] != "[REDACTED]"
                        and request_raw_digest != actual_raw_digest
                    )
                ):
                    raise ProtocolError("replay_raw_utterance_hash_mismatch")
            elif request_raw_digest is not None:
                raise ProtocolError("observation_raw_utterance_hash_forbidden")
        decision_intents: dict[str, tuple[str, str, tuple[str, ...], str | None]] = {}
        for request_id, decision in decisions.items():
            request = requests.get(request_id)
            if request is None:
                raise ProtocolError("replay_decision_without_request")
            if request_positions[request_id] > decision_positions[request_id]:
                raise ProtocolError("replay_decision_before_request")
            if decision["state_ref"] != request["state_ref"]:
                raise ProtocolError("replay_state_ref_mismatch")
            if request["body"]["event_kind"] == "utterance":
                request_raw_digest = original_request_raw_digests.get(
                    request_id, request["provenance"]["raw_utterance_sha256"]
                )
                expected_raw_digest = request_raw_digest
                if request["body"]["utterance"] != "[REDACTED]":
                    expected_raw_digest = hashlib.sha256(
                        request["body"]["utterance"].encode("utf-8")
                    ).hexdigest()
                decision_raw_digest = decision["provenance"]["raw_utterance_sha256"]
                if decision_raw_digest != expected_raw_digest:
                    raise ProtocolError("replay_raw_utterance_hash_mismatch")
            body = decision["body"]
            event_kind = request["body"]["event_kind"]
            typed = body["typed_intent"]
            _validate_typed_intent(typed, allow_verified_states=True)
            claim_codes = tuple(claim["code"] for claim in typed["claims"])
            current_intent = (body["intent_id"], typed["label"], claim_codes, typed["target"])
            observation = validate_observation(request["body"]["observation"])
            raw_typed = {
                "label": typed["label"],
                "claims": [{"code": c["code"], "state": "UNVERIFIED"} for c in typed["claims"]],
                "target": typed["target"],
            }
            if verify_claims(raw_typed, observation) != typed:
                raise ProtocolError("replay_claim_verification_mismatch")
            if event_kind == "observation":
                prior_decision_ids = [
                    prior_id
                    for prior_id in decisions
                    if decision_positions[prior_id] < request_positions[request_id]
                ]
                if not prior_decision_ids:
                    if not leading_observation_pair or request_positions[request_id] != 0:
                        raise ProtocolError("replay_observation_without_prior_intent")
                else:
                    prior_id = max(prior_decision_ids, key=decision_positions.__getitem__)
                    prior_intent = decision_intents.get(prior_id)
                    if prior_intent is None:
                        raise ProtocolError("replay_observation_without_prior_intent")
                    if current_intent != prior_intent:
                        raise ProtocolError("replay_observation_intent_mismatch")
            interpretation = Interpretation(
                body["intent_id"],
                typed,
                decision["provenance"]["backend"],
                decision["provenance"]["arm"],
            )
            context = PlanningContext.build(
                state_ref=request["state_ref"],
                observation=observation,
                interpretation=interpretation,
            )
            if context.digest != body["planning_context_digest"]:
                raise ProtocolError("replay_planning_context_mismatch")
            status, expected_steps = ReplayValidator._plan_shape(observation, typed["label"])
            if (
                status != body["status"]
                or body["plan_id"] != f"plan-{context.digest[:20]}"
                or len(body["steps"]) != len(expected_steps)
            ):
                raise ProtocolError("replay_plan_semantics_mismatch")
            for step, expected in zip(body["steps"], expected_steps):
                ReplayValidator._validate_replay_step(step, expected)
                action_bindings.setdefault(
                    step["action_id"],
                    (
                        request_id,
                        step["operation"],
                        decision["state_ref"],
                        decision["session_epoch"],
                    ),
                )
            decision_intents[request_id] = current_intent
        consumed_action_ids: set[str] = set()
        latest_state_ref: Mapping[str, Any] | None = None
        for index, payload in enumerate(envelopes):
            if payload["message_type"] in {"request", "decision"}:
                state_ref = payload["state_ref"]
                if latest_state_ref is not None and (
                    state_ref["revision"] < latest_state_ref["revision"]
                    or (
                        state_ref["revision"] == latest_state_ref["revision"]
                        and state_ref["sha256"] != latest_state_ref["sha256"]
                    )
                ):
                    raise ProtocolError("replay_state_revision_regression")
                if payload["message_type"] == "decision":
                    latest_state_ref = state_ref
                continue
            if payload["message_type"] != "result":
                continue
            body = payload["body"]
            decision = decisions.get(payload["request_id"])
            if decision is None:
                raise ProtocolError("replay_result_without_decision")
            if decision_positions[payload["request_id"]] > index:
                raise ProtocolError("replay_result_before_decision")
            binding = action_bindings.get(body["action_id"])
            if (
                binding is None
                or binding[0] != payload["request_id"]
                or binding[1] != body["operation"]
                or binding[3] != payload["session_epoch"]
            ):
                raise ProtocolError("replay_result_binding_mismatch")
            matching = [
                step for step in decision["body"]["steps"] if step["action_id"] == body["action_id"]
            ]
            if payload["state_ref"] != body["state_ref"]:
                raise ProtocolError("replay_result_contradiction")
            if len(matching) != 1 or matching[0]["operation"] != body["operation"]:
                raise ProtocolError("replay_result_binding_mismatch")
            if body["action_id"] in consumed_action_ids:
                raise ProtocolError("replay_duplicate_result")
            if body["engine_revision"] != body["state_ref"]["revision"]:
                raise ProtocolError("replay_result_contradiction")
            transition_error = _result_transition_error(
                body["operation"], body["status"], binding[2], body["state_ref"]
            )
            if transition_error == "stale_result":
                raise ProtocolError("replay_stale_result")
            if transition_error is not None:
                raise ProtocolError("replay_result_transition_mismatch")
            if latest_state_ref is not None:
                if body["state_ref"]["revision"] < latest_state_ref["revision"] or (
                    body["state_ref"]["revision"] == latest_state_ref["revision"]
                    and body["state_ref"]["sha256"] != latest_state_ref["sha256"]
                ):
                    raise ProtocolError("replay_state_revision_regression")
                if latest_state_ref != binding[2]:
                    raise ProtocolError("replay_result_binding_mismatch")
            latest_state_ref = body["state_ref"]
            consumed_action_ids.add(body["action_id"])
        if missing_request_ids:
            raise ProtocolError("replay_request_without_decision")
        return {
            "valid": True,
            "rows": len(envelopes),
            "content_hashes": hashes,
            "intent_lineage_scope": REPLAY_INTENT_LINEAGE_SCOPE,
            "cross_epoch_intent_continuity_proven": REPLAY_CROSS_EPOCH_INTENT_CONTINUITY_PROVEN,
        }


def default_envelope(
    *,
    message_type: str,
    body: Mapping[str, Any],
    session_id: str = "session-1",
    session_epoch: int = 0,
    request_id: str = "request-1",
    sequence: int = 0,
    delivery_index: int = 0,
    state_ref: Mapping[str, Any] | None = None,
    policy_hash: str = "0" * 64,
    arm: str = "P",
    backend: str = "codex",
    model: str | None = None,
) -> dict[str, Any]:
    source = {
        "session_id": session_id,
        "session_epoch": session_epoch,
        "episode_id": "episode-1",
        "request_id": request_id,
        "sequence": sequence,
        "delivery_index": delivery_index,
        "config_hash": canonical_config_hash(),
        "policy_hash": policy_hash,
        "state_ref": dict(state_ref or {"revision": 0, "sha256": "0" * 64}),
        "budget": dict(DEFAULT_BUDGET),
        "provenance": {
            "arm": arm,
            "backend": backend,
            "model": model,
            "trace_ref": None,
            "recorded_response_ref": None,
            "raw_utterance_sha256": None,
        },
    }
    if message_type == "request" and body.get("event_kind") == "utterance":
        utterance = body.get("utterance")
        if not isinstance(utterance, str) or not utterance:
            raise ProtocolError("invalid_utterance")
        source["provenance"]["raw_utterance_sha256"] = hashlib.sha256(
            utterance.encode("utf-8")
        ).hexdigest()
    return GoalController.make_envelope(source, message_type, body)


__all__ = [
    "BudgetExceeded",
    "ControllerFailure",
    "GoalController",
    "IntentInterpreter",
    "PlanningContext",
    "ProtocolError",
    "ReplayValidator",
    "canonical_config_hash",
    "canonical_json",
    "content_hash",
    "default_envelope",
    "sha256_json",
    "validate_envelope",
    "validate_observation",
    "verify_claims",
]
