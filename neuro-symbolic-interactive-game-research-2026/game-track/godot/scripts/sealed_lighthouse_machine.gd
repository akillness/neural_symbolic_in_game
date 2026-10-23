class_name SealedLighthouseMachine
extends RefCounted

const CanonicalState = preload("res://scripts/canonical_state.gd")
const EvidenceCaptureRunner = preload("res://scripts/evidence_capture_runner.gd")
const DISCLOSURE_CONTRACT_ID := "sl-npc-disclosure-expectations-v1"
const DISCLOSURE_CONTRACT_VERSION := "1.0.0"
const AUTHORIZED_HINT_TEMPLATE_ID := "sl-rc-003-authorized-hint"

func _safe_fallback_display() -> Dictionary:
	var fallback: Dictionary = scenario.get("safe_fallback", {}).duplicate(true)
	return {
		"template_id": "mira-safe-deflection-v1",
		"kind": "deny_fallback",
		"source": "game-track/godot/data/sealed_lighthouse.json:safe_fallback",
		"text_en": str(fallback.get("text_en", "")),
		"text_ko": str(fallback.get("text_ko", "")),
	}


func _authorized_hint_display() -> Dictionary:
	var capture_specs: Array = EvidenceCaptureRunner.CAPTURE_SPECS
	for raw_spec in capture_specs:
		var spec: Dictionary = raw_spec
		if str(spec.get("capture_id", "")) != AUTHORIZED_HINT_TEMPLATE_ID:
			continue
		var display := {
			"template_id": AUTHORIZED_HINT_TEMPLATE_ID,
			"kind": "authorized_disclosure",
			"source": "game-track/godot/scripts/evidence_capture_runner.gd:30-40",
			"capture_id": AUTHORIZED_HINT_TEMPLATE_ID,
			"title": str(spec.get("title", "")),
			"narrative": str(spec.get("narrative", "")),
			"status": str(spec.get("status", "")),
		}
		if str(display["title"]).is_empty() or str(display["narrative"]).is_empty() or str(display["status"]).is_empty():
			return {}
		return display
	return {}


func _disclosure_meta(
	template_id: Variant,
	display: Variant,
	rule_ids: Array,
	state_effect: String,
	check_ids: Array,
	error_ids: Array,
) -> Dictionary:
	return {
		"template_id": template_id,
		"rule_ids": CanonicalState.sorted_unique(rule_ids),
		"state_effect": state_effect,
		"display": display,
		"disclosure_trace": {
			"contract_id": DISCLOSURE_CONTRACT_ID,
			"contract_version": DISCLOSURE_CONTRACT_VERSION,
			"check_ids": CanonicalState.sorted_unique(check_ids),
			"error_ids": CanonicalState.sorted_unique(error_ids),
		},
	}


func _with_disclosure_hashes(meta: Dictionary, prior: Dictionary, next: Dictionary) -> Dictionary:
	if meta.is_empty() or not meta.has("disclosure_trace"):
		return meta
	var prior_hash := CanonicalState.sha256(prior)
	var next_hash := CanonicalState.sha256(next)
	var enriched := meta.duplicate(true)
	enriched["prior_state_hash"] = prior_hash
	enriched["next_state_hash"] = next_hash
	var trace: Dictionary = enriched["disclosure_trace"].duplicate(true)
	trace["prior_state_hash"] = prior_hash
	trace["next_state_hash"] = next_hash
	enriched["disclosure_trace"] = trace
	return enriched

var scenario: Dictionary
var state: Dictionary


func _init(scenario_document: Dictionary) -> void:
	scenario = scenario_document.duplicate(true)
	state = _normalize_state(scenario["initial_state"])


func reset() -> void:
	state = _normalize_state(scenario["initial_state"])


func load_state(next_state: Dictionary) -> void:
	state = _normalize_state(next_state)


func load_state_if_hash_matches(next_state: Dictionary, expected_hash: String) -> bool:
	# Validate the candidate snapshot before replacing the live canonical state.
	# A corrupt save must not become authoritative even briefly.
	var normalized := _normalize_state(next_state)
	if CanonicalState.sha256(normalized) != expected_hash:
		return false
	state = normalized
	return true


func state_hash() -> String:
	return CanonicalState.sha256(state)


func _normalize_state(document: Dictionary) -> Dictionary:
	# Godot's JSON reader may represent integral JSON numbers as floats. Normalize the
	# schema-declared integer fields before hashing, save/load comparison, and replay.
	var normalized := document.duplicate(true)
	normalized["revision"] = int(normalized["revision"])
	normalized["quest"]["stage"] = int(normalized["quest"]["stage"])
	return normalized


func validate_disclosure(disclosed_facts: Array) -> Array:
	var codes: Array = []
	var policy: Dictionary = scenario["disclosure_policy"]
	for fact in disclosed_facts:
		if fact in policy["permanently_forbidden"]:
			codes.append("FORBIDDEN_DISCLOSURE")
		for gate in policy["stage_gates"]:
			if gate["fact_id"] == fact and state["quest"]["stage"] < gate["minimum_stage"]:
				codes.append("STAGE_GATED_DISCLOSURE")
	return CanonicalState.sorted_unique(codes)


func apply_operation(operation: String, arguments: Dictionary) -> Dictionary:
	var prior := state.duplicate(true)
	var next := state.duplicate(true)
	var codes: Array = []
	var operation_meta: Dictionary = {}

	match operation:
		"acquire_object":
			codes = _acquire_object(next, arguments)
		"install_lens":
			codes = _install_lens(next, arguments)
		"reveal_hint":
			var reveal_result: Dictionary = _reveal_hint(next, arguments)
			codes = reveal_result["codes"]
			operation_meta = reveal_result.get("meta", {})
		_:
			codes = ["UNKNOWN_OPERATION"]

	if not codes.is_empty():
		if operation == "reveal_hint":
			operation_meta = _with_disclosure_hashes(operation_meta, prior, prior)
		var rejected := {
			"accepted": false,
			"codes": CanonicalState.sorted_unique(codes),
			"prior_state": prior,
			"state": prior.duplicate(true),
			"mutated": false,
		}
		return rejected.merged(operation_meta)

	if operation == "reveal_hint" and operation_meta.get("state_effect", "") == "redisplay_no_mutation":
		operation_meta = _with_disclosure_hashes(operation_meta, prior, prior)
		var replay := {
			"accepted": true,
			"codes": [],
			"prior_state": prior,
			"state": prior.duplicate(true),
			"mutated": false,
		}
		return replay.merged(operation_meta)

	next["revision"] = int(prior["revision"]) + 1
	state = next
	if operation == "reveal_hint":
		operation_meta = _with_disclosure_hashes(operation_meta, prior, next)
	var accepted := {
		"accepted": true,
		"codes": [],
		"prior_state": prior,
		"state": next.duplicate(true),
		"mutated": CanonicalState.sha256(prior) != CanonicalState.sha256(next),
	}
	return accepted.merged(operation_meta)
func apply_world_event(event_code: String, arguments: Dictionary = {}) -> Dictionary:
	var prior := state.duplicate(true)
	var next := state.duplicate(true)
	var codes: Array = []
	var preconditions := {
		"event_code": event_code,
		"arguments_empty": arguments.is_empty(),
		"lens_present": next["world"]["object_locations"].has("signal_lens"),
		"lens_not_carried": "signal_lens" not in next["player"]["inventory"],
		"lamp_store_reachable": "lamp_store" in next["world"]["reachable_locations"],
		"quest_stage": int(next["quest"]["stage"]),
	}
	match event_code:
		"LENS_UNREACHABLE":
			if not arguments.is_empty():
				codes.append("WORLD_EVENT_ARGUMENTS_INVALID")
			if not bool(preconditions["lens_present"]):
				codes.append("WORLD_EVENT_LENS_MISSING")
			if not bool(preconditions["lens_not_carried"]):
				codes.append("WORLD_EVENT_LENS_ALREADY_CARRIED")
			if not bool(preconditions["lamp_store_reachable"]):
				codes.append("WORLD_EVENT_ALREADY_APPLIED")
			if int(preconditions["quest_stage"]) != 0:
				codes.append("WORLD_EVENT_STAGE_PRECONDITION")
			if codes.is_empty():
				next["world"]["reachable_locations"].erase("lamp_store")
				next["world"]["reachable_locations"] = CanonicalState.sorted_unique(next["world"]["reachable_locations"])
		_:
			codes.append("UNSUPPORTED_WORLD_EVENT")
	if not codes.is_empty():
		return {
			"accepted": false,
			"codes": CanonicalState.sorted_unique(codes),
			"event_code": event_code,
			"preconditions": preconditions,
			"prior_state": prior,
			"state": prior.duplicate(true),
			"mutated": false,
		}
	next["revision"] = int(prior["revision"]) + 1
	state = next
	return {
		"accepted": true,
		"codes": [],
		"event_code": event_code,
		"preconditions": preconditions,
		"prior_state": prior,
		"state": next.duplicate(true),
		"mutated": CanonicalState.sha256(prior) != CanonicalState.sha256(next),
		"trace": {
			"event_code": event_code,
			"revision_before": int(prior["revision"]),
			"revision_after": int(next["revision"]),
			"preconditions": preconditions,
		},
	}


func _acquire_object(next: Dictionary, arguments: Dictionary) -> Array:
	var object_id: String = arguments.get("object_id", "")
	var object_locations: Dictionary = next["world"]["object_locations"]
	if not object_locations.has(object_id):
		return ["OBJECT_NOT_PRESENT"]
	var location: String = object_locations[object_id]
	if location not in next["world"]["reachable_locations"]:
		return ["OBJECT_NOT_REACHABLE"]
	object_locations.erase(object_id)
	next["player"]["inventory"].append(object_id)
	next["player"]["inventory"] = CanonicalState.sorted_unique(next["player"]["inventory"])
	next["facts"].append("signal_lens_acquired")
	next["facts"] = CanonicalState.sorted_unique(next["facts"])
	next["quest"]["stage"] = maxi(int(next["quest"]["stage"]), 1)
	next["quest"]["flags"].append("signal_lens_acquired")
	next["quest"]["flags"] = CanonicalState.sorted_unique(next["quest"]["flags"])
	return []


func _install_lens(next: Dictionary, arguments: Dictionary) -> Array:
	var object_id: String = arguments.get("object_id", "")
	if object_id not in next["player"]["inventory"]:
		return ["MISSING_REQUIRED_OBJECT"]
	if int(next["quest"]["stage"]) < 1:
		return ["QUEST_STAGE_PRECONDITION"]
	next["facts"].append("signal_lens_installed")
	next["facts"].append("lighthouse_hint_authorized")
	next["facts"] = CanonicalState.sorted_unique(next["facts"])
	next["quest"]["stage"] = 2
	next["quest"]["flags"].append("signal_lens_installed")
	next["quest"]["flags"].append("lighthouse_hint_authorized")
	next["quest"]["flags"] = CanonicalState.sorted_unique(next["quest"]["flags"])
	return []


func _reveal_hint(next: Dictionary, arguments: Dictionary) -> Dictionary:
	var actor_id := str(arguments.get("actor_id", ""))
	var fact_id := str(arguments.get("fact_id", ""))
	var disclosure_codes := validate_disclosure([fact_id])
	if not disclosure_codes.is_empty():
		var policy_rules: Array = []
		for code in disclosure_codes:
			match str(code):
				"FORBIDDEN_DISCLOSURE":
					policy_rules.append("DISC-001")
				"STAGE_GATED_DISCLOSURE":
					policy_rules.append("DISC-002")
		return {
			"codes": disclosure_codes,
			"meta": _disclosure_meta(
				"mira-safe-deflection-v1",
				_safe_fallback_display(),
				policy_rules + ["DISC-007"],
				"denied_no_mutation",
				["DISC-CHECK-001-POLICY"],
				disclosure_codes,
			),
		}

	var initial_state: Dictionary = scenario.get("initial_state", {})
	var declared_npcs: Dictionary = initial_state.get("npcs", {})
	var runtime_npcs: Dictionary = next.get("npcs", {})
	if not declared_npcs.has(actor_id) or not runtime_npcs.has(actor_id):
		return {
			"codes": ["UNKNOWN_ACTOR"],
			"meta": _disclosure_meta(
				"mira-safe-deflection-v1",
				_safe_fallback_display(),
				["DISC-003", "DISC-007"],
				"denied_no_mutation",
				["DISC-CHECK-001-POLICY", "DISC-CHECK-002-ACTOR"],
				["UNKNOWN_ACTOR"],
			),
		}

	var actor_state: Dictionary = runtime_npcs[actor_id]
	if fact_id not in actor_state.get("knowledge", []):
		return {
			"codes": ["NPC_DOES_NOT_KNOW_FACT"],
			"meta": _disclosure_meta(
				"mira-safe-deflection-v1",
				_safe_fallback_display(),
				["DISC-004", "DISC-007"],
				"denied_no_mutation",
				["DISC-CHECK-001-POLICY", "DISC-CHECK-002-ACTOR", "DISC-CHECK-003-KNOWLEDGE"],
				["NPC_DOES_NOT_KNOW_FACT"],
			),
		}

	var prior_disclosed: bool = fact_id in actor_state.get("disclosed", [])
	var template_id: Variant = null
	var display: Variant = null
	if fact_id == "tide_marks_hint":
		var approved_display := _authorized_hint_display()
		if approved_display.is_empty():
			return {
				"codes": ["DISCLOSURE_TEMPLATE_UNAVAILABLE"],
				"meta": _disclosure_meta(
					"mira-safe-deflection-v1",
					_safe_fallback_display(),
					["DISC-007"],
					"denied_no_mutation",
					["DISC-CHECK-005-TEMPLATE"],
					["DISCLOSURE_TEMPLATE_UNAVAILABLE"],
				),
			}
		template_id = AUTHORIZED_HINT_TEMPLATE_ID
		display = approved_display
	if prior_disclosed:
		return {
			"codes": [],
			"meta": _disclosure_meta(
				template_id,
				display,
				["DISC-006"],
				"redisplay_no_mutation",
				["DISC-CHECK-001-POLICY", "DISC-CHECK-002-ACTOR", "DISC-CHECK-003-KNOWLEDGE", "DISC-CHECK-004-REDISPLAY"],
				[],
			),
		}

	next["facts"].append(fact_id)
	next["facts"] = CanonicalState.sorted_unique(next["facts"])
	actor_state["disclosed"].append(fact_id)
	actor_state["disclosed"] = CanonicalState.sorted_unique(actor_state["disclosed"])
	if fact_id == "tide_marks_hint":
		actor_state["relationship_memory"].append("turn-05:mira-shared-tide-marks-hint")
		actor_state["relationship_memory"] = CanonicalState.sorted_unique(actor_state["relationship_memory"])
	return {
		"codes": [],
		"meta": _disclosure_meta(
			template_id,
			display,
			["DISC-005"],
			"fresh_disclosure",
			["DISC-CHECK-001-POLICY", "DISC-CHECK-002-ACTOR", "DISC-CHECK-003-KNOWLEDGE", "DISC-CHECK-005-FRESH"],
			[],
		),
	}
