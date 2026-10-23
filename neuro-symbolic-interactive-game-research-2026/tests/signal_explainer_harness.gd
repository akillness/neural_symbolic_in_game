extends SceneTree

const CanonicalState = preload("res://scripts/canonical_state.gd")
const EvidenceCaptureRunner = preload("res://scripts/evidence_capture_runner.gd")

var failures: Array[String] = []
var cases: Array[String] = []

func _init() -> void:
	call_deferred("_run")

func _run() -> void:
	var scene_resource: PackedScene = load("res://scenes/main_3d.tscn")
	if scene_resource == null:
		_fail("main_3d scene could not load")
		_finish()
		return
	var game: Variant = scene_resource.instantiate()
	root.add_child(game)
	await process_frame
	if game.machine == null:
		_fail("game3d did not initialize canonical machine")
		_finish()
		return
	game._smoke_mode = false
	game._evaluate_mode = false
	_test_startup_and_waiting(game)
	game._play_started = true
	game._dialogue_open = true
	game._receipt_recording_enabled = true
	game._observation_receipts.clear()
	game._receipt_sequence = 0
	_test_denied(game)
	if _authorized_template_available():
		_test_authorized_routes(game)
		_test_panel_lifecycle(game)
	else:
		_test_template_unavailable(game)
		_test_panel_lifecycle(game)
	_finish()

func _test_startup_and_waiting(game: Object) -> void:
	cases.append("startup_and_waiting")
	game.call("_on_start_requested")
	await process_frame
	game.call("_on_tutorial_closed")
	await process_frame
	_assert(game._play_started == true, "actual startup did not start play")
	_assert(game._explainer_button != null, "startup explainer button missing")
	_assert(game._explainer_button.name == "SemanticExplainerButton", "startup explainer button name drift")
	_assert(game._explainer_button.text == "[X] EXPLAIN", "startup explainer button text drift")
	_assert(game._explainer_button.visible == true, "explainer button not visible after start dismissal")
	_assert(game._explain_open == false, "explainer opened during startup dismissal")
	_assert(game._explainer_panel.visible == false, "explainer panel visible before opt-in")
	game.call("_toggle_explainer")
	await process_frame
	_assert(game._explain_open == true, "waiting explainer did not open")
	_assert(game._explainer_panel.visible == true, "waiting explainer panel not visible")
	var waiting_text := str(game._explainer_body.text)
	_assert("WAITING | No result/check/state/hash reported." in waiting_text, "waiting body lacks no-result state")
	_assert("accepted=false" not in waiting_text, "waiting body fabricated accepted=false")
	_assert("mutated=false" not in waiting_text, "waiting body fabricated mutated=false")
	_assert("consistent=false" not in waiting_text, "waiting body fabricated consistent=false")
	var waiting_snapshot := _snapshot(game)
	_assert(waiting_snapshot.get("decision", {}).get("outcome") == "waiting_for_disclosure_event", "waiting decision outcome drift")
	_assert(waiting_snapshot.get("decision", {}).get("accepted") == "unknown", "waiting accepted value drift")
	_assert(waiting_snapshot.get("checks", {}).get("consistent") == "unknown", "waiting consistency value drift")
	_assert(waiting_snapshot.get("state_effect", {}).get("mutated") == "unknown", "waiting mutation value drift")
	_assert(waiting_snapshot.get("state_effect", {}).get("prior_state_hash") == "not_reported", "waiting prior hash fabricated")
	_assert(waiting_snapshot.get("state_effect", {}).get("next_state_hash") == "not_reported", "waiting next hash fabricated")
	game.call("_close_explainer")
	await process_frame
	_assert(game._explain_open == false, "startup waiting panel did not close")
	_assert(game._explainer_button.visible == true, "explainer affordance did not return after close")

func _authorized_template_available() -> bool:
	for raw_spec in EvidenceCaptureRunner.CAPTURE_SPECS:
		var spec: Dictionary = raw_spec
		if str(spec.get("capture_id", "")) == "sl-rc-003-authorized-hint":
			return true
	return false

func _new_key(physical_keycode: Key) -> InputEventKey:
	var event := InputEventKey.new()
	event.pressed = true
	event.physical_keycode = physical_keycode
	return event

func _press(game: Object, physical_keycode: Key) -> void:
	game.call("_unhandled_input", _new_key(physical_keycode))

func _authorized_state(game: Object) -> Dictionary:
	var state: Dictionary = game.machine.state.duplicate(true)
	state["quest"]["stage"] = 2
	state["npcs"]["captain_mira"]["disclosed"].erase("tide_marks_hint")
	state["facts"].erase("tide_marks_hint")
	return state

func _snapshot(game: Object) -> Dictionary:
	var value: Variant = game._last_explanation
	return value if value is Dictionary else {}

func _assert(condition: bool, message: String) -> void:
	if not condition:
		_fail(message)

func _fail(message: String) -> void:
	failures.append(message)

func _assert_hash(value: Variant, message: String) -> void:
	var hash_value := str(value)
	_assert(hash_value.length() == 64, message + " length")
	for character in hash_value:
		_assert(character in "0123456789abcdef", message + " is not lowercase sha256")

func _assert_receipts(game: Object, start: int, required_kinds: Array, case_name: String) -> void:
	var actual_kinds: Array = []
	var previous_seq := -1
	for index in range(start, game._observation_receipts.size()):
		var receipt: Dictionary = game._observation_receipts[index]
		var kind := str(receipt.get("receipt_kind", ""))
		actual_kinds.append(kind)
		var sequence := int(receipt.get("receipt_seq", -1))
		_assert(sequence > previous_seq, case_name + " receipt sequence not increasing")
		previous_seq = sequence
		_assert(int(receipt.get("monotonic_us", -1)) >= 0, case_name + " receipt time missing")
		_assert(bool(game.call("_receipt_payload_safe", receipt)), case_name + " unsafe receipt payload")
	_assert(actual_kinds.count("disclosure_outcome") == 1, case_name + " semantic event count drift: " + JSON.stringify(actual_kinds))
	_assert("disclosure_replay" not in actual_kinds, case_name + " emitted duplicate replay event")
	for required_kind in required_kinds:
		_assert(actual_kinds.count(str(required_kind)) == 1, case_name + " receipt kind drift: " + JSON.stringify(actual_kinds))
	var allowed_kinds := {"disclosure_outcome": true, "objective_rendered": true}
	for required_kind in required_kinds:
		allowed_kinds[str(required_kind)] = true
	for actual_kind in actual_kinds:
		_assert(allowed_kinds.has(str(actual_kind)), case_name + " unexpected receipt kind: " + JSON.stringify(actual_kinds))
	_assert(actual_kinds.count("objective_rendered") <= 1, case_name + " duplicate presentation receipt")

func _assert_no_hidden_payload(snapshot: Dictionary, case_name: String) -> void:
	var rendered := JSON.stringify(snapshot)
	for token in [
		"fact_id", "fact_ids", "tide_marks_hint", "keeper_betrayal", "hidden_fact",
		"oracle", "python", "res://", "game-track/", "sealed_lighthouse",
	]:
		_assert(token not in rendered, case_name + " leaked " + token)

func _assert_common_snapshot(
	game: Object,
	result: Dictionary,
	expected_outcome: String,
	expected_effect: String,
	case_name: String,
) -> Dictionary:
	var snapshot := _snapshot(game)
	_assert(not snapshot.is_empty(), case_name + " did not publish an explanation snapshot")
	_assert(snapshot.get("schema_id") == "trace-rpg-semantic-explanation", case_name + " schema id")
	_assert(snapshot.get("schema_version") == "1.0.0", case_name + " schema version")
	var input_value: Variant = snapshot.get("input", {})
	var input: Dictionary = input_value if input_value is Dictionary else {}
	_assert(input == {
		"operation": "reveal_hint",
		"actor_role": "captain",
		"subject_type": "lead",
	}, case_name + " input semantics")
	var ontology_value: Variant = snapshot.get("ontology", {})
	var ontology: Dictionary = ontology_value if ontology_value is Dictionary else {}
	_assert(ontology.get("relation") == "captain_to_lead_disclosure", case_name + " ontology relation")
	_assert(ontology.get("rule_ids", []) == result.get("rule_ids", []), case_name + " ontology rule ids")
	var checks_value: Variant = snapshot.get("checks", {})
	var checks: Dictionary = checks_value if checks_value is Dictionary else {}
	_assert(checks.has("evaluated"), case_name + " missing evaluated checks")
	_assert(checks.has("skipped"), case_name + " missing skipped checks")
	_assert(checks.has("out_of_scope"), case_name + " missing out-of-scope families")
	_assert(checks.has("consistent"), case_name + " missing consistency flag")
	var decision_value: Variant = snapshot.get("decision", {})
	var decision: Dictionary = decision_value if decision_value is Dictionary else {}
	_assert(decision.get("outcome") == expected_outcome, case_name + " decision outcome")
	_assert(decision.get("accepted") == bool(result.get("accepted", false)), case_name + " decision acceptance")
	_assert(decision.get("result_codes", []) == result.get("codes", []), case_name + " result codes")
	var effect_value: Variant = snapshot.get("state_effect", {})
	var effect: Dictionary = effect_value if effect_value is Dictionary else {}
	_assert(effect.get("kind") == expected_effect, case_name + " state effect")
	_assert(effect.get("mutated") == bool(result.get("mutated", false)), case_name + " mutation flag")
	_assert(effect.get("prior_state_hash") == result.get("prior_state_hash", ""), case_name + " prior hash")
	_assert(effect.get("next_state_hash") == result.get("next_state_hash", ""), case_name + " next hash")
	_assert_hash(effect.get("prior_state_hash", ""), case_name + " prior hash")
	_assert_hash(effect.get("next_state_hash", ""), case_name + " next hash")
	_assert_no_hidden_payload(snapshot, case_name)
	return snapshot

func _test_denied(game: Object) -> void:
	cases.append("denied")
	var before_hash: String = str(game.machine.state_hash())
	var receipt_start: int = game._observation_receipts.size()
	var result: Dictionary = game.call("_propose_tide_hint")
	_assert_receipts(game, receipt_start, ["disclosure_outcome", "hold_emitted"], "denied")
	_assert(result.get("accepted") == false, "denied route unexpectedly accepted")
	_assert(result.get("codes", []) == ["STAGE_GATED_DISCLOSURE"], "denied route code drift")
	_assert(result.get("state_effect") == "denied_no_mutation", "denied route effect drift")
	_assert(game.machine.state_hash() == before_hash, "denied route mutated canonical hash")
	var snapshot := _assert_common_snapshot(game, result, "denied", "denied_no_mutation", "denied")
	var checks: Dictionary = snapshot["checks"]
	_assert(checks["consistent"] == true, "denied trace was not consistent")
	_assert(checks["short_circuit"] == true, "denied trace lost short-circuit")
	_assert(checks["held_at"] == "STAGE_GATED_DISCLOSURE", "denied trace held-at drift")
	_assert(checks["evaluated"] == [
		{"code": "FORBIDDEN_DISCLOSURE", "gate": "DISCLOSURE", "outcome": "pass"},
		{"code": "STAGE_GATED_DISCLOSURE", "gate": "DISCLOSURE/QUEST STAGE", "outcome": "fail"},
	], "denied evaluated checks drift")
	_assert(checks["skipped"] == [
		{"code": "UNKNOWN_ACTOR", "gate": "POLICY"},
		{"code": "NPC_DOES_NOT_KNOW_FACT", "gate": "KNOWLEDGE"},
	], "denied skipped checks drift")
	_assert(checks["out_of_scope"] == ["PRECONDITION", "REACHABILITY"], "denied out-of-scope drift")
	_assert(checks["unreported"] == [{"code": "DISCLOSURE_TEMPLATE_UNAVAILABLE", "gate": "DISCLOSURE"}], "denied conditional check was not explicitly unreported")
	var accounted: Dictionary = {}
	for entry in checks["evaluated"]:
		var evaluated_code := str(entry.get("code", ""))
		_assert(not accounted.has(evaluated_code), "denied trace duplicated evaluated code")
		accounted[evaluated_code] = true
	for entry in checks["skipped"]:
		var skipped_code := str(entry.get("code", ""))
		_assert(not accounted.has(skipped_code), "denied trace duplicated skipped code")
		accounted[skipped_code] = true
	for entry in checks["unreported"]:
		var unreported_code := str(entry.get("code", ""))
		_assert(not accounted.has(unreported_code), "denied trace duplicated unreported code")
		accounted[unreported_code] = true
	_assert(accounted == {
		"FORBIDDEN_DISCLOSURE": true,
		"STAGE_GATED_DISCLOSURE": true,
		"UNKNOWN_ACTOR": true,
		"NPC_DOES_NOT_KNOW_FACT": true,
		"DISCLOSURE_TEMPLATE_UNAVAILABLE": true,
	}, "denied trace did not account for each planned check exactly once")
	_assert(checks["family_states"]["POLICY"] == "skipped", "denied policy state drift")
	_assert(checks["family_states"]["KNOWLEDGE"] == "skipped", "denied knowledge state drift")

func _test_authorized_routes(game: Object) -> void:
	game.machine.load_state(_authorized_state(game))
	game._dialogue_open = true
	cases.append("fresh")
	var fresh_before: String = str(game.machine.state_hash())
	var fresh_receipt_start: int = game._observation_receipts.size()
	var fresh: Dictionary = game.call("_propose_tide_hint")
	_assert_receipts(game, fresh_receipt_start, ["disclosure_outcome", "commit_emitted"], "fresh")
	_assert(fresh.get("accepted") == true, "fresh route rejected")
	_assert(fresh.get("mutated") == true, "fresh route did not mutate")
	_assert(fresh.get("state_effect") == "fresh_disclosure", "fresh route effect drift")
	_assert(game.machine.state_hash() == fresh.get("next_state_hash"), "fresh next hash not canonical")
	_assert(fresh.get("prior_state_hash") == fresh_before, "fresh prior hash drift")
	var fresh_snapshot := _assert_common_snapshot(game, fresh, "authorized_fresh", "fresh_disclosure", "fresh")
	var fresh_checks: Dictionary = fresh_snapshot["checks"]
	_assert(fresh_checks["consistent"] == true, "fresh trace was not consistent")
	_assert(fresh_checks["short_circuit"] == false, "fresh trace incorrectly short-circuited")
	_assert(fresh_checks["skipped"] == [], "fresh trace fabricated skipped checks")
	_assert(fresh_checks["out_of_scope"] == ["PRECONDITION", "REACHABILITY"], "fresh out-of-scope drift")
	_assert(fresh_checks["evaluated"].size() == 4, "fresh trace did not evaluate all disclosure checks")
	for entry in fresh_checks["evaluated"]:
		_assert(entry["outcome"] == "pass", "fresh trace contains a non-pass check")

	cases.append("redisplay")
	var replay_before: Dictionary = game.machine.state.duplicate(true)
	var replay_hash: String = str(game.machine.state_hash())
	var replay_receipt_start: int = game._observation_receipts.size()
	var replay: Dictionary = game.call("_propose_tide_hint")
	_assert_receipts(game, replay_receipt_start, ["disclosure_outcome"], "redisplay")
	_assert(replay.get("accepted") == true, "redisplay route rejected")
	_assert(replay.get("mutated") == false, "redisplay route mutated")
	_assert(replay.get("state_effect") == "redisplay_no_mutation", "redisplay route effect drift")
	_assert(replay.get("state") == replay_before, "redisplay route changed canonical state")
	_assert(game.machine.state_hash() == replay_hash, "redisplay route changed canonical hash")
	var replay_snapshot := _assert_common_snapshot(game, replay, "authorized_redisplay", "redisplay_no_mutation", "redisplay")
	var replay_checks: Dictionary = replay_snapshot["checks"]
	_assert(replay_checks["consistent"] == true, "redisplay trace was not consistent")
	_assert(replay_checks["short_circuit"] == false, "redisplay trace incorrectly short-circuited")
	_assert(replay_checks["skipped"] == [], "redisplay trace fabricated skipped checks")

func _test_template_unavailable(game: Object) -> void:
	cases.append("template_unavailable")
	game.machine.load_state(_authorized_state(game))
	game._dialogue_open = true
	var before_hash: String = str(game.machine.state_hash())
	var receipt_start: int = game._observation_receipts.size()
	var result: Dictionary = game.call("_propose_tide_hint")
	_assert_receipts(game, receipt_start, ["disclosure_outcome", "hold_emitted"], "template unavailable")
	_assert(result.get("accepted") == false, "missing template unexpectedly accepted")
	_assert(result.get("codes", []) == ["DISCLOSURE_TEMPLATE_UNAVAILABLE"], "missing template code drift")
	_assert(result.get("state_effect") == "denied_no_mutation", "missing template effect drift")
	_assert(game.machine.state_hash() == before_hash, "missing template mutated canonical hash")
	var snapshot := _assert_common_snapshot(game, result, "denied", "denied_no_mutation", "template unavailable")
	var checks: Dictionary = snapshot["checks"]
	_assert(checks["consistent"] == true, "missing template trace was not consistent")
	_assert(checks["short_circuit"] == true, "missing template trace lost short-circuit")
	_assert(checks["held_at"] == "DISCLOSURE_TEMPLATE_UNAVAILABLE", "missing template held-at drift")
	_assert(checks["skipped"] == [], "missing template fabricated skipped checks")
	var evaluated: Array = checks["evaluated"]
	_assert(evaluated.size() == 5, "missing template did not evaluate the template check")
	var last_check: Dictionary = evaluated.back()
	_assert(last_check.get("code") == "DISCLOSURE_TEMPLATE_UNAVAILABLE", "missing template evaluated check code drift")
	_assert(last_check.get("outcome") == "fail", "missing template evaluated check outcome drift")
	_assert(not str(last_check.get("gate", "")).is_empty(), "missing template evaluated check gate missing")
	_assert("DISCLOSURE" not in checks["out_of_scope"], "missing template marked disclosure out-of-scope")

func _test_panel_lifecycle(game: Object) -> void:
	cases.append("panel_lifecycle")
	game._explain_open = false
	var before_hash: String = str(game.machine.state_hash())
	game._dialogue_open = true
	_press(game, KEY_X)
	_assert(game._explain_open == false, "explainer opened during dialogue")
	_assert(game.machine.state_hash() == before_hash, "dialogue explainer attempt changed hash")
	game.call("_close_dialogue")
	game.ui.dismiss_coach_card()
	game.ui.hide_tutorial()
	game.ui.hide_evidence_board()
	_press(game, KEY_X)
	_assert(game._explain_open == true, "explainer did not open from opt-in key")
	_assert(game.machine.state_hash() == before_hash, "opening explainer changed canonical hash")
	_press(game, KEY_ESCAPE)
	_assert(game._explain_open == false, "escape did not close explainer")
	_assert(game.machine.state_hash() == before_hash, "closing explainer changed canonical hash")
	game._smoke_mode = true
	_press(game, KEY_X)
	_assert(game._explain_open == false, "explainer opened in smoke mode")
	_assert(game.machine.state_hash() == before_hash, "smoke-mode explainer attempt changed hash")
	game._smoke_mode = false

func _finish() -> void:
	var result := {"passed": failures.is_empty(), "failures": failures, "cases": cases}
	print("SIGNAL_EXPLAINER_RESULT " + JSON.stringify(result))
	quit(0 if failures.is_empty() else 1)
