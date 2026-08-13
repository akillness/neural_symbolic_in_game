class_name SealedLighthouseMachine
extends RefCounted

const CanonicalState = preload("res://scripts/canonical_state.gd")

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

	match operation:
		"acquire_object":
			codes = _acquire_object(next, arguments)
		"install_lens":
			codes = _install_lens(next, arguments)
		"reveal_hint":
			codes = _reveal_hint(next, arguments)
		_:
			codes = ["UNKNOWN_OPERATION"]

	if not codes.is_empty():
		return {
			"accepted": false,
			"codes": CanonicalState.sorted_unique(codes),
			"prior_state": prior,
			"state": prior.duplicate(true),
			"mutated": false,
		}

	next["revision"] = int(prior["revision"]) + 1
	state = next
	return {
		"accepted": true,
		"codes": [],
		"prior_state": prior,
		"state": next.duplicate(true),
		"mutated": CanonicalState.sha256(prior) != CanonicalState.sha256(next),
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


func _reveal_hint(next: Dictionary, arguments: Dictionary) -> Array:
	var actor_id: String = arguments.get("actor_id", "")
	var fact_id: String = arguments.get("fact_id", "")
	var disclosure_codes := validate_disclosure([fact_id])
	if not disclosure_codes.is_empty():
		return disclosure_codes
	if actor_id != "captain_mira":
		return ["UNKNOWN_ACTOR"]
	if fact_id not in next["npcs"][actor_id]["knowledge"]:
		return ["NPC_DOES_NOT_KNOW_FACT"]
	next["facts"].append(fact_id)
	next["facts"] = CanonicalState.sorted_unique(next["facts"])
	next["npcs"][actor_id]["disclosed"].append(fact_id)
	next["npcs"][actor_id]["disclosed"] = CanonicalState.sorted_unique(
		next["npcs"][actor_id]["disclosed"]
	)
	next["npcs"][actor_id]["relationship_memory"].append(
		"turn-05:mira-shared-tide-marks-hint"
	)
	next["npcs"][actor_id]["relationship_memory"] = CanonicalState.sorted_unique(
		next["npcs"][actor_id]["relationship_memory"]
	)
	return []
