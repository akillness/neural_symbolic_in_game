class_name NpcAgentClient
extends Node

## Loopback-only asynchronous client for the fixed-goal NPC service.
## Python can interpret and plan, but this node never writes canonical state.
## Godot remains the sole authority for proposal validation and world commits.

const CanonicalState = preload("res://scripts/canonical_state.gd")

signal decision_received(envelope: Dictionary, context: Dictionary)
signal result_recorded(envelope: Dictionary, context: Dictionary)
signal directive_received(code: String, payload: Dictionary)
signal status_changed(text: String)
signal protocol_error(reason: String)

const SCHEMA_VERSION := "npc-goal-recovery/1.1.0"
const SCENARIO_ID := "sealed-lighthouse-v1"
const NPC_ID := "captain_mira"
const GOAL_ID := "harbor-signal-restored-authorized-tide-lead-v1"
const GOAL_VERSION := "1"
const ENDPOINT := "http://127.0.0.1:8768"
const BODY_LIMIT_BYTES := 65536
const INTENT_DEADLINE_MS := 30000
const EPISODE_DEADLINE_MS := 900000
const MAX_INTENT_CALLS := 8
const MAX_ACTION_ATTEMPTS := 32
const MAX_REPLANS := 16
const MAX_PLAN_EXPANSIONS := 32
const MAX_INFLIGHT := 1
const MAX_UTTERANCE_CHARS := 1000

var _http: HTTPRequest
var _game: Node
var _ui: Node
var _session_id := ""
var _episode_id := ""
var _session_epoch := 0
var _sequence := 0
var _delivery_index := 0
var _request_generation := 0
var _intent_calls := 0
var _episode_started_ms := 0
var _pending: Dictionary = {}
var _last_decision_context: Dictionary = {}
var _issued_actions: Dictionary = {}
var _policy_hash := ""
var _config_hash := ""
var _capability := ""
var _closed := false
var _engineering_mode := false
var _interpretation_accepted := false


func _ready() -> void:
	_http = HTTPRequest.new()
	_http.timeout = float(INTENT_DEADLINE_MS) / 1000.0
	_http.body_size_limit = BODY_LIMIT_BYTES
	_http.max_redirects = 0
	_http.request_completed.connect(_on_request_completed)
	add_child(_http)
	_set_status("BACKEND CODEX | MODE LIVE | READY")


func setup(game: Node, ui: Node) -> void:
	_game = game
	_ui = ui
	_capability = OS.get_environment("TRACE_RPG_NPC_CAPABILITY").strip_edges()
	_policy_hash = str(_game.npc_policy_hash())
	_config_hash = str(_game.npc_config_hash())
	_start_session()


func set_capability(value: String) -> void:
	_capability = value.strip_edges()

func bind_engineering_context(context: Dictionary, current_state_ref: Dictionary, deadline_ms: int = INTENT_DEADLINE_MS) -> Dictionary:
	var args := OS.get_cmdline_user_args()
	if "--npc-experiment" not in args and "--npc-bootstrap" not in args:
		return {"accepted": false, "codes": ["ENGINEERING_MODE_REQUIRED"]}
	if _game == null or context.is_empty():
		return {"accepted": false, "codes": ["ENGINEERING_CONTEXT_INVALID"]}
	for key in ["session_id", "episode_id", "session_epoch", "request_id", "goal_id", "goal_version"]:
		if not context.has(key) or str(context.get(key, "")).is_empty():
			return {"accepted": false, "codes": ["MISSING_CONTEXT_" + key.to_upper()]}
	if str(context.get("goal_id", "")) != GOAL_ID or str(context.get("goal_version", "")) != GOAL_VERSION:
		return {"accepted": false, "codes": ["GOAL_MISMATCH"]}
	if context.has("policy_hash") and not str(context.get("policy_hash", "")).is_empty() \
		and str(context.get("policy_hash", "")) != _policy_hash:
		return {"accepted": false, "codes": ["POLICY_HASH_MISMATCH"]}
	if context.has("config_hash") and not str(context.get("config_hash", "")).is_empty() \
		and str(context.get("config_hash", "")) != _config_hash:
		return {"accepted": false, "codes": ["CONFIG_IDENTITY_MISMATCH"]}
	_session_id = str(context.get("session_id", ""))
	_episode_id = str(context.get("episode_id", ""))
	_session_epoch = int(context.get("session_epoch", -1))
	_request_generation += 1
	_sequence = 0
	_delivery_index = 0
	_last_decision_context.clear()
	_issued_actions.clear()
	_interpretation_accepted = false
	_closed = false
	_engineering_mode = true
	var bound := context.duplicate(true)
	bound["generation"] = _request_generation
	bound["policy_hash"] = _policy_hash
	bound["config_hash"] = _config_hash
	bound["deadline_ms"] = Time.get_ticks_msec() + (deadline_ms if deadline_ms > 0 else -1)
	bound["expected_revision"] = int(current_state_ref.get("revision", -1))
	bound["expected_sha256"] = str(current_state_ref.get("sha256", ""))
	bound["state_ref"] = {"revision": bound["expected_revision"], "sha256": bound["expected_sha256"]}
	return {"accepted": true, "context": bound}


func has_accepted_interpretation() -> bool:
	return _interpretation_accepted


func _start_session() -> void:
	_request_generation += 1
	_cancel_http_if_pending("session_reset")
	var seed := "%s:%s:%s" % [Time.get_ticks_usec(), get_instance_id(), OS.get_process_id()]
	_session_id = "npc-%s" % CanonicalState.sha256(seed).substr(0, 24)
	_episode_id = "episode-%s" % CanonicalState.sha256(_session_id).substr(0, 24)
	_episode_started_ms = Time.get_ticks_msec()
	_session_epoch = 0
	_sequence = 0
	_delivery_index = 0
	_intent_calls = 0
	_pending.clear()
	_last_decision_context.clear()
	_issued_actions.clear()
	_interpretation_accepted = false
	_closed = false


func launch_identity() -> Dictionary:
	return {
		"session_id": _session_id,
		"episode_id": _episode_id,
		"session_epoch": _session_epoch,
		"policy_hash": _policy_hash,
		"config_hash": _config_hash,
	}


func begin_dialogue() -> void:
	_closed = false
	_session_epoch += 1
	_request_generation += 1
	_cancel_http_if_pending("dialogue_open")
	_last_decision_context.clear()
	_issued_actions.clear()
	_set_status("BACKEND CODEX | MODE LIVE | READY")


func invalidate_pending(reason: String = "invalidated") -> void:
	_session_epoch += 1
	_request_generation += 1
	_cancel_http_if_pending(reason)
	_last_decision_context.clear()
	_issued_actions.clear()
	if reason != "dialogue_closed":
		_interpretation_accepted = false
	_closed = reason in ["dialogue_closed", "exit", "close"]
	_set_status("BACKEND CODEX | MODE LIVE | CANCELLED")

func request_utterance(utterance: String, observation: Dictionary) -> bool:
	var text := utterance.strip_edges()
	if text.is_empty():
		_set_status("BACKEND CODEX | MODE LIVE | ENTER TEXT")
		return false
	if text.length() > MAX_UTTERANCE_CHARS:
		_set_status("BACKEND CODEX | MODE LIVE | TEXT TOO LONG")
		return false
	if _intent_calls >= MAX_INTENT_CALLS:
		_set_status("BACKEND CODEX | MODE LIVE | CALL BUDGET REACHED")
		return false
	if Time.get_ticks_msec() - _episode_started_ms > EPISODE_DEADLINE_MS:
		_set_status("BACKEND CODEX | MODE LIVE | EPISODE TIMEOUT")
		return false
	# A newer utterance is an explicit epoch boundary. Cancel before replacing
	# pending state so any late transport callback is tombstoned.
	_session_epoch += 1
	_request_generation += 1
	_cancel_http_if_pending("newer_utterance")
	_last_decision_context.clear()
	_issued_actions.clear()
	_interpretation_accepted = false
	_intent_calls += 1
	return _request_step("utterance", text, observation)


func request_observation(observation: Dictionary) -> bool:
	# Result feedback is observation-only: the service reuses its last typed
	# intent and planner context, so this path never spends another model call.
	if _closed or _game == null or not _interpretation_accepted:
		return false
	if not _pending.is_empty():
		_set_status("BACKEND CODEX | MODE LIVE | BUSY")
		return false
	if Time.get_ticks_msec() - _episode_started_ms > EPISODE_DEADLINE_MS:
		_set_status("BACKEND CODEX | MODE LIVE | EPISODE TIMEOUT")
		return false
	return _request_step("observation", "", observation)


func _request_step(event_kind: String, utterance: String, observation: Dictionary) -> bool:
	if _game == null:
		_set_status("BACKEND CODEX | MODE LIVE | UNAVAILABLE")
		return false
	if not _pending.is_empty():
		_set_status("BACKEND CODEX | MODE LIVE | BUSY")
		return false
	var state_ref: Dictionary = _game.npc_state_ref()
	var request_id := _new_id("request")
	var body := {
		"event_kind": event_kind,
		"utterance": utterance if event_kind == "utterance" else null,
		"observation": _sanitize_observation(observation),
	}
	var envelope := _build_envelope(
		"request",
		request_id,
		body,
		state_ref,
		_sha256_utf8(utterance) if event_kind == "utterance" else "",
	)
	_pending = {
		"kind": "step",
		"event_kind": event_kind,
		"generation": _request_generation,
		"session_epoch": _session_epoch,
		"session_id": _session_id,
		"episode_id": _episode_id,
		"goal_id": GOAL_ID,
		"goal_version": GOAL_VERSION,
		"request_id": request_id,
		"expected_revision": int(state_ref.get("revision", -1)),
		"expected_sha256": str(state_ref.get("sha256", "")),
		"deadline_ms": Time.get_ticks_msec() + INTENT_DEADLINE_MS,
		"policy_hash": _policy_hash,
		"config_hash": _config_hash,
	}
	_set_status("BACKEND CODEX | MODE LIVE | WAITING")
	var sent := _send("/npc/step", envelope)
	if not sent:
		_pending.clear()
		_set_status("BACKEND CODEX | MODE LIVE | UNAVAILABLE")
	return sent


func accept_decision(envelope: Dictionary, context: Dictionary, current_state_ref: Dictionary) -> Dictionary:
	var errors := _validate_decision(envelope, context, current_state_ref)
	if not errors.is_empty():
		return {"accepted": false, "codes": errors}
	var body: Dictionary = envelope["body"]
	var steps: Array = body.get("steps", [])
	if steps.is_empty():
		var terminal_status := str(body.get("status", "ERROR"))
		if terminal_status not in ["NO_ROUTE", "GOAL_REACHED"]:
			return {"accepted": false, "codes": ["MISSING_PLAN_STEP"]}
		if terminal_status == "GOAL_REACHED" and not bool(_game.npc_public_observation().get("goal_reached", false)):
			return {"accepted": false, "kind": "none", "status": "GOAL_NOT_REACHED", "codes": ["GOAL_NOT_REACHED"]}
		directive_received.emit("NPC_" + terminal_status, {"status": terminal_status})
		_interpretation_accepted = true
		return {"accepted": true, "kind": "none", "status": terminal_status}
	var step: Dictionary = steps[0]
	var operation := str(step.get("operation", ""))
	var execution_mode := str(step.get("execution_mode", ""))
	var action_id := str(step.get("action_id", ""))
	if action_id.is_empty() or _issued_actions.has(action_id):
		return {"accepted": false, "codes": ["DUPLICATE_ACTION"]}
	var arguments: Dictionary = step.get("arguments", {})
	var observation := _sanitize_observation(_game.npc_public_observation())
	if operation == "reveal_hint":
		if execution_mode != "commit_world":
			return {"accepted": false, "codes": ["EXECUTION_MODE_MISMATCH"]}
		if arguments != {"actor_id": NPC_ID, "fact_id": "tide_marks_hint"}:
			return {"accepted": false, "codes": ["REVEAL_BINDING_MISMATCH"]}
		# Mira may reveal only the authorized, known tide lead. The existing hard
		# writer remains the final synchronous authority after this gate.
		if not bool(observation.get("signal_restored", false)) \
			or not bool(observation.get("tide_lead_authorized", false)) \
			or not bool(observation.get("in_dialogue", false)) \
			or bool(observation.get("goal_reached", false)):
			return {"accepted": false, "codes": ["REVEAL_PRECONDITION_MISMATCH"]}
	elif operation in ["acquire_object", "install_lens"]:
		if execution_mode != "player_request":
			return {"accepted": false, "codes": ["EXECUTION_MODE_MISMATCH"]}
		if arguments != {"object_id": "signal_lens"}:
			return {"accepted": false, "codes": ["PLAYER_ACTION_BINDING_MISMATCH"]}
		if operation == "acquire_object" and (not bool(observation.get("lens_reachable", false)) or bool(observation.get("lens_carried", false))):
			return {"accepted": false, "codes": ["PLAYER_ACTION_PRECONDITION_MISMATCH"]}
		if operation == "install_lens" and (not bool(observation.get("lens_carried", false)) or bool(observation.get("signal_restored", false))):
			return {"accepted": false, "codes": ["PLAYER_ACTION_PRECONDITION_MISMATCH"]}
	else:
		if operation not in ["clarify", "negotiate"] or execution_mode != "dialogue":
			return {"accepted": false, "codes": ["UNSUPPORTED_STEP"]}
		return _accept_dialogue_step(operation)
	var issued := context.duplicate(true)
	issued["action_id"] = action_id
	issued["operation"] = operation
	issued["prior_state_ref"] = {"revision": int(current_state_ref.get("revision", -1)), "sha256": str(current_state_ref.get("sha256", ""))}
	issued["result_submitted"] = false
	issued["intent_id"] = str(body.get("intent_id", ""))
	_issued_actions[action_id] = issued
	var directive_context := issued.duplicate(true)
	if operation == "reveal_hint":
		directive_received.emit("NPC_REVEAL_HINT", {"action_id": action_id, "context": directive_context})
		_interpretation_accepted = true
		return {"accepted": true, "kind": "reveal_hint", "action_id": action_id, "context": directive_context}
	directive_received.emit("NPC_PLAYER_ACTION", {"operation": operation, "action_id": action_id, "context": directive_context})
	_interpretation_accepted = true
	return {"accepted": true, "kind": "player_request", "operation": operation, "action_id": action_id, "context": directive_context}


func _accept_dialogue_step(operation: String) -> Dictionary:
	_interpretation_accepted = true
	directive_received.emit("NPC_DIALOGUE", {"operation": operation})
	return {"accepted": true, "kind": "dialogue", "operation": operation}


func validate_action_context(context: Dictionary, action_id: String, operation: String, current_state_ref: Dictionary, require_original_state: bool = true) -> Array:
	var errors: Array = []
	if context.is_empty() or not _issued_actions.has(action_id):
		errors.append("ISSUED_ACTION_UNKNOWN")
	else:
		var issued: Dictionary = _issued_actions[action_id]
		if str(issued.get("action_id", "")) != action_id or str(issued.get("operation", "")) != operation:
			errors.append("ISSUED_ACTION_BINDING_MISMATCH")
		if str(context.get("operation", operation)) != operation or str(context.get("action_id", action_id)) != action_id:
			errors.append("ISSUED_ACTION_BINDING_MISMATCH")
		if str(issued.get("request_id", "")) != str(context.get("request_id", "")):
			errors.append("ISSUED_ACTION_BINDING_MISMATCH")
		for key in ["session_id", "episode_id", "session_epoch", "generation", "policy_hash", "config_hash", "deadline_ms"]:
			if str(issued.get(key, "")) != str(context.get(key, "")):
				errors.append("ISSUED_ACTION_BINDING_MISMATCH")
		if require_original_state:
			if int(issued.get("expected_revision", -1)) != int(context.get("expected_revision", -2)) \
				or str(issued.get("expected_sha256", "")) != str(context.get("expected_sha256", "")):
				errors.append("ISSUED_ACTION_BINDING_MISMATCH")
		if bool(issued.get("result_submitted", false)):
			errors.append("DUPLICATE_ACTION")
	if int(context.get("session_epoch", -1)) != _session_epoch or int(context.get("generation", -1)) != _request_generation:
		errors.append("EPOCH_OR_GENERATION_MISMATCH")
	if str(context.get("session_id", _session_id)) != _session_id or str(context.get("episode_id", _episode_id)) != _episode_id:
		errors.append("SESSION_BINDING_MISMATCH")
	if str(context.get("policy_hash", "")) != _policy_hash or str(context.get("config_hash", "")) != _config_hash:
		errors.append("CONFIG_IDENTITY_MISMATCH")
	if Time.get_ticks_msec() > int(context.get("deadline_ms", 0)):
		errors.append("DEADLINE_EXPIRED")
	if int(current_state_ref.get("revision", -1)) != int(context.get("expected_revision", -2)):
		errors.append("CURRENT_REVISION_CHANGED")
	if str(current_state_ref.get("sha256", "")) != str(context.get("expected_sha256", "")):
		errors.append("CURRENT_STATE_CHANGED")
	return CanonicalState.sorted_unique(errors)


func submit_action_result(context: Dictionary, action_id: String, operation: String, status: String, feedback: String, next_state_ref: Dictionary = {}) -> bool:
	if _closed or context.is_empty() or _game == null or not _pending.is_empty():
		return false
	var current_ref: Dictionary = _game.npc_state_ref()
	var check_context := context.duplicate(true)
	# The result is emitted after the synchronous hard writer. Validate all
	# session/action identity against the post-write reference while retaining
	# the original prior_state_ref in the issued action context.
	check_context["expected_revision"] = int(current_ref.get("revision", -1))
	check_context["expected_sha256"] = str(current_ref.get("sha256", ""))
	var binding_errors := validate_action_context(check_context, action_id, operation, current_ref, false)
	if not binding_errors.is_empty():
		protocol_error.emit("RESULT_BINDING_REJECTED|" + "|".join(binding_errors))
		return false
	if status not in ["APPLIED", "REJECTED", "STALE", "DUPLICATE", "CANCELLED", "ERROR"]:
		protocol_error.emit("RESULT_STATUS_INVALID")
		return false
	var observation: Dictionary = _sanitize_observation(_game.npc_public_observation())
	var body := {
		"action_id": action_id,
		"operation": operation,
		"status": status,
		"engine_revision": int(current_ref.get("revision", 0)),
		"state_ref": current_ref,
		"feedback": feedback.substr(0, 512),
		"observation": observation,
	}
	var envelope := _build_envelope("result", str(context.get("request_id", "")), body, current_ref, "")
	var issued: Dictionary = _issued_actions.get(action_id, {})
	issued["result_submitted"] = true
	issued["next_state_ref"] = current_ref.duplicate(true)
	_issued_actions[action_id] = issued
	if _engineering_mode:
		return true
	_pending = {
		"kind": "result",
		"generation": _request_generation,
		"session_epoch": _session_epoch,
		"session_id": _session_id,
		"episode_id": _episode_id,
		"request_id": str(context.get("request_id", "")),
		"expected_revision": int(current_ref.get("revision", -1)),
		"expected_sha256": str(current_ref.get("sha256", "")),
		"deadline_ms": Time.get_ticks_msec() + INTENT_DEADLINE_MS,
		"policy_hash": _policy_hash,
		"config_hash": _config_hash,
		"action_id": action_id,
		"operation": operation,
		"prior_state_ref": context.get("prior_state_ref", {}).duplicate(true) if context.get("prior_state_ref", {}) is Dictionary else {},
		"next_state_ref": current_ref.duplicate(true),
	}
	_set_status("BACKEND CODEX | MODE LIVE | CONFIRMING")
	var sent := _send("/npc/result", envelope)
	if not sent:
		_pending.clear()
		issued["result_submitted"] = false
		_issued_actions[action_id] = issued
		_set_status("BACKEND CODEX | MODE LIVE | UNAVAILABLE")
	return sent


func _validate_decision(envelope: Dictionary, context: Dictionary, current_state_ref: Dictionary) -> Array:
	var errors := _validate_common(envelope, "decision")
	if context.is_empty():
		errors.append("MISSING_CONTEXT")
	else:
		if str(envelope.get("request_id", "")) != str(context.get("request_id", "")):
			errors.append("REQUEST_MISMATCH")
		if int(envelope.get("session_epoch", -1)) != int(context.get("session_epoch", -2)):
			errors.append("EPOCH_MISMATCH")
		if int(context.get("generation", -1)) != _request_generation:
			errors.append("GENERATION_MISMATCH")
		if str(context.get("session_id", "")) != _session_id or str(context.get("episode_id", "")) != _episode_id:
			errors.append("SESSION_BINDING_MISMATCH")
		if str(context.get("goal_id", "")) != GOAL_ID or str(context.get("goal_version", "")) != GOAL_VERSION:
			errors.append("GOAL_MISMATCH")
		if Time.get_ticks_msec() > int(context.get("deadline_ms", 0)):
			errors.append("DEADLINE_EXPIRED")
		if str(context.get("policy_hash", "")) != _policy_hash or str(context.get("config_hash", "")) != _config_hash:
			errors.append("CONFIG_IDENTITY_MISMATCH")
	var envelope_ref: Dictionary = envelope.get("state_ref", {})
	if int(envelope_ref.get("revision", -1)) != int(context.get("expected_revision", -2)):
		errors.append("REVISION_MISMATCH")
	if str(envelope_ref.get("sha256", "")) != str(context.get("expected_sha256", "")):
		errors.append("STATE_HASH_MISMATCH")
	var body_value: Variant = envelope.get("body", {})
	if not body_value is Dictionary:
		errors.append("BODY_SCHEMA_INVALID")
		return CanonicalState.sorted_unique(errors)
	var body: Dictionary = body_value as Dictionary
	errors.append_array(_validate_decision_body(body))
	# Structural, hash, session, epoch, request, goal, policy, and deadline
	# binding must all pass before a consumed action can short-circuit freshness.
	if not errors.is_empty():
		return CanonicalState.sorted_unique(errors)
	var steps: Array = body.get("steps", [])
	if not steps.is_empty() and steps[0] is Dictionary:
		var action_id := str((steps[0] as Dictionary).get("action_id", ""))
		if not action_id.is_empty() and _issued_actions.has(action_id):
			return ["DUPLICATE_ACTION"]
	if int(current_state_ref.get("revision", -1)) != int(context.get("expected_revision", -2)):
		errors.append("CURRENT_REVISION_CHANGED")
	if str(current_state_ref.get("sha256", "")) != str(context.get("expected_sha256", "")):
		errors.append("CURRENT_STATE_CHANGED")
	return CanonicalState.sorted_unique(errors)


func _validate_decision_body(body: Dictionary) -> Array:
	var errors: Array = []
	var required := ["intent_id", "typed_intent", "plan_id", "steps", "planning_context_digest", "status", "error"]
	for key in required:
		if not body.has(key):
			errors.append("MISSING_BODY_" + str(key).to_upper())
	for key in body.keys():
		if key not in required:
			errors.append("EXTRA_BODY_" + str(key).to_upper())
	var intent_id := str(body.get("intent_id", ""))
	var status := str(body.get("status", ""))
	if status not in ["READY", "WAITING_PLAYER", "WAITING_DIALOGUE", "GOAL_REACHED", "NO_ROUTE", "FAILED", "CANCELLED"]:
		errors.append("STATUS_INVALID")
	if not _valid_identifier(intent_id):
		errors.append("INTENT_ID_INVALID")
	var plan_id_value: Variant = body.get("plan_id", null)
	if plan_id_value != null and not _valid_identifier(str(plan_id_value)):
		errors.append("PLAN_ID_INVALID")
	var error_value: Variant = body.get("error", null)
	if error_value != null and (not error_value is String or str(error_value).length() > 256):
		errors.append("ERROR_FIELD_INVALID")
	var typed_value: Variant = body.get("typed_intent", {})
	var typed: Dictionary = {}
	if typed_value is Dictionary:
		typed = typed_value
	else:
		errors.append("TYPED_INTENT_SCHEMA_INVALID")
	if typed.is_empty():
		errors.append("TYPED_INTENT_SCHEMA_INVALID")
	else:
		var typed_required := ["label", "claims", "target"]
		for key in typed_required:
			if not typed.has(key):
				errors.append("MISSING_TYPED_INTENT_" + str(key).to_upper())
		for key in typed.keys():
			if key not in typed_required:
				errors.append("EXTRA_TYPED_INTENT_" + str(key).to_upper())
		if str(typed.get("label", "")) not in ["ASK_INFORMATION", "REQUEST_DISCLOSURE", "REPORT_FACT", "REFUSE_HELP", "AMBIGUOUS", "UNKNOWN"]:
			errors.append("TYPED_INTENT_LABEL_INVALID")
		var target_value: Variant = typed.get("target", null)
		if target_value != null and (not target_value is String or str(target_value) not in ["lens", "signal", "tide_marks"]):
			errors.append("TYPED_INTENT_TARGET_INVALID")
		var claims_value: Variant = typed.get("claims", [])
		if not claims_value is Array:
			errors.append("CLAIMS_SCHEMA_INVALID")
		else:
			var claims: Array = claims_value
			if claims.size() > 8:
				errors.append("CLAIMS_LIMIT_EXCEEDED")
			for claim in claims:
				if not claim is Dictionary or claim.keys().size() != 2 or not claim.has("code") or not claim.has("state"):
					errors.append("CLAIM_SCHEMA_INVALID")
					continue
				if str(claim.get("code", "")) not in ["LENS_REACHABLE", "LENS_CARRIED", "SIGNAL_RESTORED", "TIDE_LEAD_AUTHORIZED", "GOAL_REACHED", "IN_DIALOGUE", "NONE"]:
					errors.append("CLAIM_CODE_INVALID")
				if str(claim.get("state", "")) not in ["UNVERIFIED", "SUPPORTED", "CONTRADICTED", "INDETERMINATE", "NOT_VISIBLE"]:
					errors.append("CLAIM_STATE_INVALID")
	var digest := str(body.get("planning_context_digest", ""))
	if not _is_hex64(digest):
		errors.append("PLANNING_DIGEST_INVALID")
	var steps_value: Variant = body.get("steps", [])
	if not steps_value is Array:
		errors.append("STEPS_SCHEMA_INVALID")
		return CanonicalState.sorted_unique(errors)
	var steps: Array = steps_value
	if steps.size() > MAX_PLAN_EXPANSIONS:
		errors.append("PLAN_STEPS_LIMIT_EXCEEDED")
	for step in steps:
		if not step is Dictionary:
			errors.append("PLAN_STEP_SCHEMA_INVALID")
			continue
		var step_required := ["action_id", "operation", "execution_mode", "arguments"]
		for key in step_required:
			if not step.has(key):
				errors.append("MISSING_STEP_" + str(key).to_upper())
		for key in step.keys():

			if key not in step_required:
				errors.append("EXTRA_STEP_" + str(key).to_upper())
		var operation := str(step.get("operation", ""))
		var expected_mode: String = str({"acquire_object": "player_request", "install_lens": "player_request", "reveal_hint": "commit_world", "clarify": "dialogue", "negotiate": "dialogue"}.get(operation, ""))
		if expected_mode.is_empty() or str(step.get("execution_mode", "")) != expected_mode:
			errors.append("STEP_BINDING_INVALID")
		var arguments_value: Variant = step.get("arguments", {})
		if not arguments_value is Dictionary:
			errors.append("STEP_ARGUMENTS_SCHEMA_INVALID")
			continue
		var arguments: Dictionary = arguments_value
		var expected_arguments: Dictionary = {}
		match operation:
			"acquire_object", "install_lens":
				expected_arguments = {"object_id": "signal_lens"}
			"reveal_hint":
				expected_arguments = {"actor_id": NPC_ID, "fact_id": "tide_marks_hint"}
			"clarify", "negotiate":
				expected_arguments = {}
		if arguments != expected_arguments:
			errors.append("STEP_ARGUMENTS_INVALID")
		if not _valid_identifier(str(step.get("action_id", ""))):
			errors.append("STEP_ACTION_ID_INVALID")
	if not steps.is_empty() and status in ["GOAL_REACHED", "NO_ROUTE", "FAILED", "CANCELLED"]:
		errors.append("NON_EXECUTABLE_STATUS_WITH_STEPS")
	return CanonicalState.sorted_unique(errors)

func _valid_identifier(value: String) -> bool:
	if value.is_empty() or value.length() > 128:
		return false
	var regex := RegEx.new()
	regex.compile("^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
	return regex.search(value) != null


func _is_hex64(value: String) -> bool:
	if value.length() != 64:
		return false
	for character in value:
		if "0123456789abcdef".find(character) == -1:
			return false
	return true

func _normalize_wire_for_hash(envelope: Dictionary) -> Dictionary:
	var normalized := envelope.duplicate(true)
	for key in ["session_epoch", "sequence", "delivery_index"]:
		if normalized.has(key):
			normalized[key] = int(normalized.get(key, 0))
	var state_ref: Variant = normalized.get("state_ref", null)
	if state_ref is Dictionary and state_ref.has("revision"):
		state_ref["revision"] = int(state_ref.get("revision", 0))
	var budget: Variant = normalized.get("budget", null)
	if budget is Dictionary:
		for key in ["intent_deadline_ms", "episode_deadline_ms", "max_intent_calls", "max_action_attempts", "max_replans", "max_plan_expansions", "max_inflight_per_session"]:
			if budget.has(key):
				budget[key] = int(budget.get(key, 0))
	return normalized

func _validate_common(envelope: Dictionary, expected_type: String) -> Array:
	var errors: Array = []
	var required := [
		"schema_version", "message_type", "session_id", "session_epoch", "episode_id",
		"request_id", "event_id", "sequence", "delivery_index", "scenario_id", "npc_id",
		"goal_id", "goal_version", "policy_hash", "config_hash", "state_ref", "body", "budget", "provenance", "content_sha256",
	]
	for key in required:
		if not envelope.has(key):
			errors.append("MISSING_" + str(key).to_upper())
	for key in envelope.keys():
		if key not in required:
			errors.append("EXTRA_" + str(key).to_upper())
	if str(envelope.get("schema_version", "")) != SCHEMA_VERSION:
		errors.append("SCHEMA_VERSION_MISMATCH")
	if str(envelope.get("message_type", "")) != expected_type:
		errors.append("MESSAGE_TYPE_MISMATCH")
	if str(envelope.get("session_id", "")) != _session_id:
		errors.append("SESSION_MISMATCH")
	if int(envelope.get("session_epoch", -1)) != _session_epoch:
		errors.append("EPOCH_MISMATCH")
	if str(envelope.get("episode_id", "")) != _episode_id:
		errors.append("EPISODE_MISMATCH")
	if str(envelope.get("scenario_id", "")) != SCENARIO_ID:
		errors.append("SCENARIO_MISMATCH")
	if str(envelope.get("npc_id", "")) != NPC_ID:
		errors.append("NPC_MISMATCH")
	if str(envelope.get("goal_id", "")) != GOAL_ID or str(envelope.get("goal_version", "")) != GOAL_VERSION:
		errors.append("GOAL_MISMATCH")
	if str(envelope.get("policy_hash", "")) != _policy_hash:
		errors.append("POLICY_HASH_MISMATCH")
	if str(envelope.get("config_hash", "")) != _config_hash:
		errors.append("CONFIG_HASH_MISMATCH")
	var content := envelope.duplicate(true)
	content.erase("content_sha256")
	if str(envelope.get("content_sha256", "")) != CanonicalState.sha256(_normalize_wire_for_hash(content)):
		errors.append("CONTENT_HASH_MISMATCH")
	return CanonicalState.sorted_unique(errors)


func _sha256_utf8(value: String) -> String:
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	if context.update(value.to_utf8_buffer()) != OK:
		return ""
	return context.finish().hex_encode()

func _build_envelope(message_type: String, request_id: String, body: Dictionary, state_ref: Dictionary, raw_hash: String) -> Dictionary:
	_sequence += 1
	_delivery_index += 1
	var envelope := {
		"schema_version": SCHEMA_VERSION,
		"message_type": message_type,
		"session_id": _session_id,
		"session_epoch": _session_epoch,
		"episode_id": _episode_id,
		"request_id": request_id,
		"event_id": _new_id("event"),
		"sequence": _sequence,
		"delivery_index": _delivery_index,
		"scenario_id": SCENARIO_ID,
		"npc_id": NPC_ID,
		"goal_id": GOAL_ID,
		"goal_version": GOAL_VERSION,
		"policy_hash": _policy_hash,
		"config_hash": _config_hash,
		"state_ref": {"revision": int(state_ref.get("revision", 0)), "sha256": str(state_ref.get("sha256", ""))},
		"body": body,
		"budget": {
			"intent_deadline_ms": INTENT_DEADLINE_MS,
			"episode_deadline_ms": EPISODE_DEADLINE_MS,
			"max_intent_calls": MAX_INTENT_CALLS,
			"max_action_attempts": MAX_ACTION_ATTEMPTS,
			"max_replans": MAX_REPLANS,
			"max_plan_expansions": MAX_PLAN_EXPANSIONS,
			"max_inflight_per_session": MAX_INFLIGHT,
			"input_tokens": null,
			"output_tokens": null,
			"cost": null,
		},
		"provenance": {
			"arm": "P",
			"backend": "codex",
			"model": null,
			"trace_ref": null,
			"recorded_response_ref": null,
			"raw_utterance_sha256": raw_hash if raw_hash != "" else null,
		},
	}
	envelope["content_sha256"] = CanonicalState.sha256(envelope)
	return envelope


func _send(path: String, envelope: Dictionary) -> bool:
	if _capability.is_empty() or _capability.length() > 512 or _capability.find("\r") != -1 or _capability.find("\n") != -1:
		protocol_error.emit("CAPABILITY_UNAVAILABLE")
		return false
	var payload := JSON.stringify(envelope)
	var headers := PackedStringArray(["Content-Type: application/json", "X-NPC-Capability: Bearer " + _capability])
	var error := _http.request(ENDPOINT + path, headers, HTTPClient.METHOD_POST, payload)
	if error != OK:
		protocol_error.emit("REQUEST_ERROR_%s" % error)
		return false
	return true


func _on_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	var context := _pending.duplicate(true)
	_pending.clear()
	if context.is_empty():
		return
	if int(context.get("generation", -1)) != _request_generation or int(context.get("session_epoch", -1)) != _session_epoch:
		return
	if result == HTTPRequest.RESULT_TIMEOUT:
		_set_status("BACKEND CODEX | MODE LIVE | TIMEOUT")
		protocol_error.emit("TIMEOUT")
		return
	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_set_status("BACKEND CODEX | MODE LIVE | UNAVAILABLE")
		var detail := ""
		if not body.is_empty():
			var failure: Variant = JSON.parse_string(body.get_string_from_utf8())
			if failure is Dictionary:
				detail = str(failure.get("error", ""))
				if failure.get("body") is Dictionary:
					detail = str(failure["body"].get("error", detail))
			detail = detail.substr(0, 128).replace("\r", " ").replace("\n", " ")
		protocol_error.emit("HTTP_%s_%s%s" % [result, response_code, "" if detail.is_empty() else ":" + detail])
		return
	var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
	if not (parsed is Dictionary):
		_set_status("BACKEND CODEX | MODE LIVE | INVALID RESPONSE")
		protocol_error.emit("INVALID_JSON")
		return
	var envelope: Dictionary = parsed
	var expected := "decision" if str(context.get("kind", "")) == "step" else "ack"
	var errors := _validate_common(envelope, expected)
	if not errors.is_empty():
		_set_status("BACKEND CODEX | MODE LIVE | PROTOCOL ERROR")
		protocol_error.emit("|".join(errors))
		return
	if str(envelope.get("request_id", "")) != str(context.get("request_id", "")):
		_set_status("BACKEND CODEX | MODE LIVE | PROTOCOL ERROR")
		protocol_error.emit("REQUEST_MISMATCH")
		return
	if str(context.get("kind", "")) == "step":
		_last_decision_context = context.duplicate(true)
		_set_status("BACKEND CODEX | MODE LIVE | PLAN RECEIVED")
		decision_received.emit(envelope, context)
	else:
		_set_status("BACKEND CODEX | MODE LIVE | RESULT ACKNOWLEDGED")
		result_recorded.emit(envelope, context)


func _cancel_http_if_pending(_reason: String) -> void:
	if _pending.is_empty() or _http == null:
		return
	_http.cancel_request()
	_pending.clear()


func _sanitize_observation(observation: Dictionary) -> Dictionary:
	return {
		"lens_reachable": bool(observation.get("lens_reachable", false)),
		"lens_carried": bool(observation.get("lens_carried", false)),
		"signal_restored": bool(observation.get("signal_restored", false)),
		"tide_lead_authorized": bool(observation.get("tide_lead_authorized", false)),
		"goal_reached": bool(observation.get("goal_reached", false)),
		"in_dialogue": bool(observation.get("in_dialogue", false)),
	}


func _new_id(prefix: String) -> String:
	_sequence += 1
	return "%s-%s" % [prefix, CanonicalState.sha256("%s:%s:%s" % [prefix, Time.get_ticks_usec(), _sequence]).substr(0, 24)]


func _set_status(text: String) -> void:
	status_changed.emit(text)
	if _ui != null and is_instance_valid(_ui):
		_ui.set_npc_status(text)
