extends SceneTree

const Machine = preload("res://scripts/sealed_lighthouse_machine.gd")
const CanonicalState = preload("res://scripts/canonical_state.gd")

var failures: Array[String] = []
var receipt_cases: Array = []
var semantic_outcomes_ok := true
var state_hash_binding_ok := true
var display_safety_ok := true
var canonical_recomputation_ok := true

func _init() -> void:
	var scenario: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/sealed_lighthouse.json"))
	if not scenario is Dictionary:
		_fail("scenario did not load as a dictionary")
	else:
		_test_denial_preserves_state_and_safe_display(scenario)
		_test_fresh_generic_disclosure_has_no_memory(scenario)
		_test_fresh_hint_disclosure_commits_memory_and_hash(scenario)
		_test_allowed_redisplay_is_unchanged(scenario)
		_test_malformed_precedence(scenario)
	_run_game3d_integration.call_deferred()

func _run_game3d_integration() -> void:
	var scene_resource: PackedScene = load("res://scenes/main_3d.tscn")
	if scene_resource == null:
		_fail("main_3d scene could not load")
		_finish()
		return
	var game: Variant = scene_resource.instantiate()
	get_root().add_child(game)
	await process_frame
	if game.machine == null:
		_fail("game3d did not initialize canonical machine")
		_finish()
		return
	game._smoke_mode = true
	game._dialogue_open = true
	var denied_before: Dictionary = game.machine.state.duplicate(true)
	var denied_hash: String = game.machine.state_hash()
	var denied: Dictionary = game._propose_tide_hint()
	_assert_safe_fallback(denied, "game3d dialogue denied hint")
	_assert(game.machine.state == denied_before, "game3d denied dialogue mutated state")
	_assert(game.machine.state_hash() == denied_hash, "game3d denied dialogue changed hash")

	var authorized: Dictionary = game.machine.state.duplicate(true)
	authorized["quest"]["stage"] = 2
	authorized["npcs"]["captain_mira"]["disclosed"].erase("tide_marks_hint")
	authorized["facts"].erase("tide_marks_hint")
	game.machine.load_state(authorized)
	var fresh: Dictionary = game._propose_tide_hint()
	_assert(fresh["accepted"] == true, "game3d dialogue fresh hint rejected")
	_assert(fresh["display"]["template_id"] == "sl-rc-003-authorized-hint", "game3d fresh display mismatch")
	_assert(fresh["state_effect"] == "fresh_disclosure", "game3d fresh state effect mismatch")
	_assert_hash_binding(game.machine, fresh)
	var redisplay_before: Dictionary = game.machine.state.duplicate(true)
	var redisplay_hash: String = game.machine.state_hash()
	var redisplay: Dictionary = game._propose_tide_hint()
	_assert(redisplay["accepted"] == true, "game3d dialogue redisplay rejected")
	_assert(redisplay["state_effect"] == "redisplay_no_mutation", "game3d redisplay state effect mismatch")
	_assert(redisplay["state"] == redisplay_before, "game3d redisplay mutated state")
	_assert(game.machine.state_hash() == redisplay_hash, "game3d redisplay changed hash")
	_assert_hash_binding(game.machine, redisplay)
	_finish()

func _finish() -> void:
	var passed := failures.is_empty()
	var result := {"passed": passed, "failures": failures}
	print("NPC_DISCLOSURE_RESULT " + JSON.stringify(result))
	var receipt_path := OS.get_environment("NPC_DISCLOSURE_RECEIPT_PATH")
	if not receipt_path.is_empty():
		var source_hashes := {
			"game-track/godot/scripts/game3d/game_3d.gd": _sha256_file("res://scripts/game3d/game_3d.gd"),
			"game-track/godot/scripts/sealed_lighthouse_machine.gd": _sha256_file("res://scripts/sealed_lighthouse_machine.gd"),
			"game-track/godot/data/sealed_lighthouse.json": _sha256_file("res://data/sealed_lighthouse.json"),
			"game-track/godot/scripts/evidence_capture_runner.gd": _sha256_file("res://scripts/evidence_capture_runner.gd"),
			"game-track/godot/scripts/canonical_state.gd": _sha256_file("res://scripts/canonical_state.gd"),
			"tests/npc_disclosure_harness.gd": _sha256_file("res://tests/npc_disclosure_harness.gd"),
		}
		var receipt := {
			"marker": "NPC_DISCLOSURE_RESULT",
			"passed": passed,
			"failures": failures,
			"packet_sha256": "9920aa834910a3ee35ed4446de4fdba42bb67dda71b07a93bccfc7a0b2e09028",
			"scenario_source": "game-track/godot/data/sealed_lighthouse.json",
			"source_hashes": source_hashes,
			"cases": receipt_cases,
			"semantic_assertions": {
				"semantic_outcomes": semantic_outcomes_ok,
				"state_hash_binding": state_hash_binding_ok,
				"display_safety": display_safety_ok,
				"canonical_recomputation": canonical_recomputation_ok,
			},
			"marker_payload": result,
		}
		var file := FileAccess.open(receipt_path, FileAccess.WRITE)
		if file == null:
			push_error("cannot open NPC_DISCLOSURE_RECEIPT_PATH")
		else:
			file.store_string(JSON.stringify(receipt, "  "))
			file.close()
	quit(0 if passed else 1)

func _sha256_file(path: String) -> String:
	var bytes := FileAccess.get_file_as_bytes(path)
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	if context.update(bytes) != OK:
		return ""
	return context.finish().hex_encode()

func _record_case(case_id: String, fact_id: String, stage: int, prior_disclosed: bool, expected: Dictionary, payload: Dictionary, actor_id: String = "captain_mira") -> void:
	var observed := {
		"allowed": payload.get("accepted", false),
		"accepted": payload.get("accepted", false),
		"codes": payload.get("codes", []),
		"template_id": payload.get("template_id"),
		"state_effect": payload.get("state_effect"),
		"rule_ids": payload.get("rule_ids", []),
	}
	var display_value: Variant = payload.get("display", {})
	var display: Dictionary = display_value if display_value is Dictionary else {}
	var trace_value: Variant = payload.get("disclosure_trace", {})
	var trace: Dictionary = trace_value if trace_value is Dictionary else {}
	for key in expected:
		if observed.get(key) != expected[key]:
			semantic_outcomes_ok = false
	receipt_cases.append({
		"case_id": case_id,
		"operation": "reveal_hint",
		"actor_id": actor_id,
		"fact_id": fact_id,
		"stage": stage,
		"prior_disclosed": prior_disclosed,
		"expected": expected,
		"observed": observed,
		"accepted": payload.get("accepted", false),
		"codes": payload.get("codes", []),
		"template_id": payload.get("template_id"),
		"rule_ids": payload.get("rule_ids", []),
		"state_effect": payload.get("state_effect"),
		"prior_state_hash": payload.get("prior_state_hash", ""),
		"next_state_hash": payload.get("next_state_hash", ""),
		"display": display,
		"mutated": payload.get("mutated", false),
		"source": payload.get("source", display.get("source", "")),
		"disclosure_outcome": payload.get("disclosure_outcome", payload.get("state_effect", "")),
		"contract_id": trace.get("contract_id", ""),
		"contract_version": trace.get("contract_version", ""),
		"disclosure_trace": trace,
	})

func _fail(message: String) -> void:
	failures.append(message)

func _assert(condition: bool, message: String) -> void:
	if not condition:
		_fail(message)

func _new_machine(scenario: Dictionary, stage: int, fact_id: String, prior_disclosed: bool) -> Object:
	var machine := Machine.new(scenario)
	var state: Dictionary = machine.state.duplicate(true)
	state["quest"]["stage"] = stage
	var actor: Dictionary = state["npcs"]["captain_mira"]
	if fact_id not in actor["knowledge"]:
		actor["knowledge"].append(fact_id)
	if prior_disclosed:
		if fact_id not in actor["disclosed"]:
			actor["disclosed"].append(fact_id)
	else:
		actor["disclosed"].erase(fact_id)
		state["facts"].erase(fact_id)
	machine.load_state(state)
	return machine

func _assert_hash_binding(machine: Object, result: Dictionary) -> void:
	var prior_ok: bool = result["prior_state_hash"] == CanonicalState.sha256(result["prior_state"])
	var next_ok: bool = result["next_state_hash"] == CanonicalState.sha256(result["state"])
	var machine_ok: bool = machine.state_hash() == result["next_state_hash"]
	state_hash_binding_ok = state_hash_binding_ok and prior_ok and next_ok and machine_ok
	canonical_recomputation_ok = canonical_recomputation_ok and prior_ok and next_ok
	_assert(prior_ok, "prior hash is not canonical")
	_assert(next_ok, "next hash is not canonical")
	_assert(machine_ok, "machine hash differs from returned next hash")

func _assert_safe_fallback(result: Dictionary, case_name: String) -> void:
	var safe: bool = result["accepted"] == false and result["state_effect"] == "denied_no_mutation" and result["mutated"] == false
	safe = safe and result["prior_state"] == result["state"] and result["prior_state_hash"] == result["next_state_hash"]
	safe = safe and result["template_id"] == "mira-safe-deflection-v1" and result["display"]["template_id"] == "mira-safe-deflection-v1"
	safe = safe and "tide_marks_hint" not in JSON.stringify(result["display"])
	display_safety_ok = display_safety_ok and safe
	_assert(result["accepted"] == false, case_name + " unexpectedly accepted")
	_assert(result["state_effect"] == "denied_no_mutation", case_name + " state effect")
	_assert(result["mutated"] == false, case_name + " mutated")
	_assert(result["prior_state"] == result["state"], case_name + " changed canonical state")
	_assert(result["prior_state_hash"] == result["next_state_hash"], case_name + " changed state hash")
	_assert(result["template_id"] == "mira-safe-deflection-v1", case_name + " returned unsafe template")
	_assert(result["display"]["template_id"] == "mira-safe-deflection-v1", case_name + " display is not safe fallback")
	_assert("tide_marks_hint" not in JSON.stringify(result["display"]), case_name + " leaked requested dialogue")

func _test_denial_preserves_state_and_safe_display(scenario: Dictionary) -> void:
	var machine := _new_machine(scenario, 0, "keeper_betrayal", false)
	var result: Dictionary = machine.apply_operation("reveal_hint", {"actor_id": "captain_mira", "fact_id": "keeper_betrayal"})
	_assert("FORBIDDEN_DISCLOSURE" in result["codes"], "forbidden denial code missing")
	_assert_safe_fallback(result, "forbidden denial")
	_assert_hash_binding(machine, result)
	_record_case("N-013", "keeper_betrayal", 0, false, {"allowed": false, "codes": ["FORBIDDEN_DISCLOSURE"], "template_id": "mira-safe-deflection-v1", "rule_ids": ["DISC-001", "DISC-007"]}, result)

func _test_fresh_generic_disclosure_has_no_memory(scenario: Dictionary) -> void:
	for fact_id in ["dock_saved", "lighthouse_dark"]:
		var machine := _new_machine(scenario, 0, fact_id, false)
		var before: Dictionary = machine.state.duplicate(true)
		var result: Dictionary = machine.apply_operation("reveal_hint", {"actor_id": "captain_mira", "fact_id": fact_id})
		_assert(result["accepted"] == true, fact_id + " fresh disclosure rejected")
		_assert(result["template_id"] == null, fact_id + " invented dialogue template")
		_assert(result["state_effect"] == "fresh_disclosure", fact_id + " wrong state effect")
		_assert(fact_id in result["state"]["facts"], fact_id + " fact missing")
		_assert(fact_id in result["state"]["npcs"]["captain_mira"]["disclosed"], fact_id + " disclosed ID missing")
		_assert(result["state"]["npcs"]["captain_mira"]["relationship_memory"] == before["npcs"]["captain_mira"]["relationship_memory"], fact_id + " added relationship memory")
		_assert(result["state"]["revision"] == before["revision"] + 1, fact_id + " revision not incremented once")
		_assert(result["mutated"] == true, fact_id + " fresh disclosure did not mutate")
		_assert_hash_binding(machine, result)
		var case_id := "N-003" if fact_id == "dock_saved" else "N-027"
		_record_case(case_id, fact_id, 0, false, {"allowed": true, "codes": [], "template_id": null, "state_effect": "fresh_disclosure", "rule_ids": ["DISC-005"]}, result)

func _test_fresh_hint_disclosure_commits_memory_and_hash(scenario: Dictionary) -> void:
	var machine := _new_machine(scenario, 2, "tide_marks_hint", false)
	var before: Dictionary = machine.state.duplicate(true)
	var result: Dictionary = machine.apply_operation("reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"})
	_assert(result["accepted"] == true, "fresh hint disclosure rejected")
	_assert(result["template_id"] == "sl-rc-003-authorized-hint", "fresh hint template mismatch")
	_assert(result["state_effect"] == "fresh_disclosure", "fresh hint state effect mismatch")
	_assert(result["state"]["npcs"]["captain_mira"]["relationship_memory"] == ["turn-05:mira-shared-tide-marks-hint"], "hint memory mismatch")
	_assert(result["state"]["revision"] == before["revision"] + 1, "hint revision not incremented once")
	_assert_hash_binding(machine, result)
	_record_case("N-047", "tide_marks_hint", 2, false, {"allowed": true, "codes": [], "template_id": "sl-rc-003-authorized-hint", "state_effect": "fresh_disclosure", "rule_ids": ["DISC-005"]}, result)

func _test_allowed_redisplay_is_unchanged(scenario: Dictionary) -> void:
	var machine := _new_machine(scenario, 2, "tide_marks_hint", true)
	var before: Dictionary = machine.state.duplicate(true)
	var before_hash: String = machine.state_hash()
	var result: Dictionary = machine.apply_operation("reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"})
	_assert(result["accepted"] == true, "authorized redisplay rejected")
	_assert(result["template_id"] == "sl-rc-003-authorized-hint", "redisplay template mismatch")
	_assert(result["state_effect"] == "redisplay_no_mutation", "redisplay state effect mismatch")
	_assert(result["state"] == before, "redisplay changed canonical state")
	_assert(machine.state_hash() == before_hash, "redisplay changed canonical hash")
	_assert(result["prior_state_hash"] == result["next_state_hash"], "redisplay hashes differ")
	_assert(result["mutated"] == false, "redisplay marked mutated")
	_assert_hash_binding(machine, result)
	_record_case("N-048", "tide_marks_hint", 2, true, {"allowed": true, "codes": [], "template_id": "sl-rc-003-authorized-hint", "state_effect": "redisplay_no_mutation", "rule_ids": ["DISC-006"]}, result)

func _test_malformed_precedence(scenario: Dictionary) -> void:
	var forbidden := _new_machine(scenario, 2, "keeper_betrayal", false)
	var forbidden_result: Dictionary = forbidden.apply_operation("reveal_hint", {"actor_id": "harbor_ghost", "fact_id": "keeper_betrayal"})
	_assert_safe_fallback(forbidden_result, "unknown actor forbidden fact")
	_assert("FORBIDDEN_DISCLOSURE" in forbidden_result["codes"], "policy code did not precede unknown actor")
	_record_case("M-007", "keeper_betrayal", 2, false, {"allowed": false, "codes": ["FORBIDDEN_DISCLOSURE"], "template_id": "mira-safe-deflection-v1", "rule_ids": ["DISC-001", "DISC-007"]}, forbidden_result, "harbor_ghost")
	var gated := _new_machine(scenario, 1, "tide_marks_hint", false)
	var gated_result: Dictionary = gated.apply_operation("reveal_hint", {"actor_id": "harbor_ghost", "fact_id": "tide_marks_hint"})
	_assert_safe_fallback(gated_result, "unknown actor gated fact")
	_assert("STAGE_GATED_DISCLOSURE" in gated_result["codes"], "stage policy code did not precede unknown actor")
	_record_case("M-008", "tide_marks_hint", 1, false, {"allowed": false, "codes": ["STAGE_GATED_DISCLOSURE"], "template_id": "mira-safe-deflection-v1", "rule_ids": ["DISC-002", "DISC-007"]}, gated_result, "harbor_ghost")
