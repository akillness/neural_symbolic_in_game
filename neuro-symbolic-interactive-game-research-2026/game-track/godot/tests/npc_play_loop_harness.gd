extends SceneTree

const MAIN_SCENE := "res://scenes/main_3d.tscn"
const TRANSPORT_SCRIPT := preload("res://tests/npc_play_loop_transport.gd")
const RESULT_PREFIX := "NPC_PLAY_LOOP_RESULT "
const REAL_WAIT_TIMEOUT_MS := 35000

var failures: Array[String] = []
var errors: Array[String] = []
var frames: int = 0
var decision_count: int = 0
var ack_count: int = 0
var directive_codes: Array[String] = []
var request_events: Array = []
var decision_provenance: Array = []
var completed_phases: Array[String] = []
var report_path := ""
var real_service := false
var contract_regression := false
var contract_controls: Array = []

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	real_service = "--real-service" in args
	var report_index := args.find("--report-path")
	if report_index >= 0 and report_index + 1 < args.size():
		report_path = str(args[report_index + 1])
	contract_regression = "--contract-regression" in args
	call_deferred("_run")

func _run() -> void:
	var game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(game)
	await _tick(3)
	var client: NpcAgentClient = await _replace_client(game)
	client.connect("request_sent", Callable(self, "_on_request_sent"))
	_connect_observers(client, game)

	var initial_ref: Dictionary = game.npc_state_ref()
	if real_service and str((client as Node).get("transport_mode")) != "production_super_send":
		_abort_run("real_transport_override", game, client, initial_ref)
		return
	game._open_mira_dialogue()
	await _tick(1)
	_check(request_events.is_empty(), "initial_open_must_not_request_without_prior_intent")
	_check(not bool(game.npc_public_observation().get("goal_reached", false)), "initial_goal_must_be_false")
	completed_phases.append("initial_open")

	game._on_npc_text_submitted("Please help me restore the harbor signal and then reveal the tide marks hint.")
	var utterance_request_ready := await _wait_for_requests_deadline(request_events, 1, REAL_WAIT_TIMEOUT_MS) if real_service else await _wait_for_requests(request_events, 1)
	_check(utterance_request_ready, "utterance_request_must_complete")
	if not utterance_request_ready:
		_abort_run("utterance_request", game, client, initial_ref)
		return
	var acquire_directive_ready := await _wait_for_waiting_action(game, "acquire_object")
	_check(acquire_directive_ready, "utterance_must_issue_acquire_directive")
	if not acquire_directive_ready:
		_abort_run("acquire_directive", game, client, initial_ref)
		return
	_check(request_events.size() >= 1 and str(request_events[0].get("event_kind", "")) == "utterance", "first_request_must_be_utterance")
	completed_phases.append("utterance")

	game._on_choice("leave")
	await _tick(1)
	var after_close_ref: Dictionary = game.npc_state_ref()
	_check(after_close_ref == initial_ref, "ordinary_dialogue_close_must_not_mutate_world")
	completed_phases.append("close")
	game._propose_acquire()
	await _tick(1)
	var acquired_ref: Dictionary = game.npc_state_ref()
	_check(int(acquired_ref["revision"]) == int(initial_ref["revision"]) + 1, "explicit_acquire_must_increment_revision_once")
	_check(str(acquired_ref["sha256"]) != str(initial_ref["sha256"]), "explicit_acquire_must_change_state_hash")
	completed_phases.append("acquire")

	game._open_mira_dialogue()
	var install_request_ready := await _wait_for_requests(request_events, 2)
	_check(install_request_ready, "first_resume_observation_must_complete")
	if not install_request_ready:
		_abort_run("install_observation", game, client, initial_ref)
		return
	var install_directive_ready := await _wait_for_waiting_action(game, "install_lens")
	_check(install_directive_ready, "first_resume_must_issue_install_directive")
	if not install_directive_ready:
		_abort_run("install_directive", game, client, initial_ref)
		return
	_check(str(request_events[1].get("event_kind", "")) == "observation", "first_resume_must_be_observation_only")
	completed_phases.append("resume_install")
	game._on_choice("leave")
	await _tick(1)
	completed_phases.append("close")
	game._propose_install()
	await _tick(1)
	var installed_ref: Dictionary = game.npc_state_ref()
	_check(int(installed_ref["revision"]) == int(acquired_ref["revision"]) + 1, "explicit_install_must_increment_revision_once")
	_check(str(installed_ref["sha256"]) != str(acquired_ref["sha256"]), "explicit_install_must_change_state_hash")
	_check(bool(game.npc_public_observation().get("signal_restored", false)), "explicit_install_must_restore_signal")
	_check(bool(game.npc_public_observation().get("tide_lead_authorized", false)), "install_must_authorize_mira_lead")
	completed_phases.append("install")

	game._open_mira_dialogue()
	var reveal_requests_ready := await _wait_for_requests(request_events, 4)
	_check(reveal_requests_ready, "second_resume_and_result_observations_must_complete")
	if not reveal_requests_ready:
		_abort_run("reveal_observations", game, client, initial_ref)
		return
	var goal_ready := await _wait_for_goal(game)
	_check(goal_ready, "authorized_reveal_must_reach_goal")
	if not goal_ready:
		_abort_run("goal_reached", game, client, initial_ref)
		return
	var ack_ready := await _wait_for_acks(ack_count, 1)
	_check(ack_ready, "reveal_result_ack_must_be_received")
	if not ack_ready:
		_abort_run("result_ack", game, client, initial_ref)
		return
	var terminal_decision_ready := await _wait_for_decisions(4)
	_check(terminal_decision_ready, "post_ack_observation_decision_must_complete")
	if not terminal_decision_ready:
		_abort_run("terminal_observation", game, client, initial_ref)
		return
	_check(str(request_events[2].get("event_kind", "")) == "observation", "second_resume_must_be_observation_only")
	_check(str(request_events[3].get("event_kind", "")) == "observation", "post_ack_replan_must_be_observation_only")
	completed_phases.append("resume_reveal")
	var final_observation: Dictionary = game.npc_public_observation()
	var final_ref: Dictionary = game.npc_state_ref()
	_check(int(final_ref["revision"]) == int(installed_ref["revision"]) + 1, "reveal_must_increment_revision_once")
	_check(str(final_ref["sha256"]) != str(installed_ref["sha256"]), "reveal_must_change_state_hash")
	_check(bool(final_observation.get("goal_reached", false)), "final_observation_must_report_goal_reached")
	_check("tide_marks_hint" in game.machine.state["facts"], "authorized_hint_must_be_committed_to_world")
	completed_phases.append("goal")

	if contract_regression:
		await _run_contract_controls()
	await _run_stale_and_cancel_controls()
	var frame_limit := "12000" if real_service else "1200"
	var command_contract := "godot --headless --path <staged_project> --script res://tests/npc_play_loop_harness.gd --quit-after %s -- %s--report-path <path>" % [frame_limit, "--real-service " if real_service else ""]
	var report := {
		"mode": "real_service" if real_service else "fake_p_interpreter",
		"transport_mode": str((client as Node).get("transport_mode")),
		"real_wait_timeout_ms": REAL_WAIT_TIMEOUT_MS,
		"passed": failures.is_empty() and errors.is_empty(),
		"phases": completed_phases.duplicate(),
		"frames": frames,
		"report_path": report_path,
		"report_path_arg": "--report-path <path>",
		"command_contract": command_contract,
		"events": {
			"request_count": request_events.size(),
			"event_kinds": _request_kinds(),
			"session_epochs": _request_epochs(),
			"decision_count": decision_count,
			"result_ack_count": ack_count,
			"directive_codes": directive_codes.duplicate(),
		},
		"decision_provenance": decision_provenance.duplicate(true),
		"request_events": request_events.duplicate(true),
		"initial_state_ref": initial_ref,
		"installed_state_ref": installed_ref,
		"final_state_ref": final_ref,
		"final_observation": final_observation,
		"session_id": client.launch_identity().get("session_id", "") if client != null else "",
		"contract_controls": contract_controls.duplicate(true),
		"errors": failures + errors,
	}
	_write_report(report)
	quit(0 if bool(report["passed"]) else 1)

func _replace_client(game: Node) -> NpcAgentClient:
	var old_client: Node = game.npc_client
	old_client.queue_free()
	await process_frame
	var replacement: NpcAgentClient = TRANSPORT_SCRIPT.new()
	game.add_child(replacement)
	await process_frame
	game.npc_client = replacement
	replacement.setup(game, game.ui)
	return replacement

func _connect_observers(client: NpcAgentClient, game: Node) -> void:
	client.decision_received.connect(Callable(game, "_on_npc_decision"))
	client.result_recorded.connect(Callable(game, "_on_npc_result_recorded"))
	client.directive_received.connect(Callable(game, "_on_npc_directive"))
	client.protocol_error.connect(Callable(game, "_on_npc_protocol_error"))
	client.decision_received.connect(Callable(self, "_on_decision"))
	client.result_recorded.connect(Callable(self, "_on_ack"))
	client.directive_received.connect(Callable(self, "_on_directive"))
	client.protocol_error.connect(Callable(self, "_on_protocol_error"))

func _on_request_sent(path: String, envelope: Dictionary) -> void:
	if path != "/npc/step":
		return
	request_events.append({
		"path": path,
		"event_kind": str(envelope.get("body", {}).get("event_kind", "")),
		"session_epoch": int(envelope.get("session_epoch", -1)),
		"request_id": str(envelope.get("request_id", "")),
		"raw_utterance_sha256": str(envelope.get("provenance", {}).get("raw_utterance_sha256", "")),
	})

func _on_decision(envelope: Dictionary, context: Dictionary) -> void:
	decision_count += 1
	decision_provenance.append({
		"event_kind": str(context.get("event_kind", "")),
		"session_epoch": int(context.get("session_epoch", -1)),
		"request_id": str(envelope.get("request_id", "")),
		"raw_utterance_sha256": str(envelope.get("provenance", {}).get("raw_utterance_sha256", "")),
	})
func _on_ack(_envelope: Dictionary, _context: Dictionary) -> void:
	ack_count += 1

func _on_directive(code: String, _payload: Dictionary) -> void:
	directive_codes.append(code)

func _on_protocol_error(reason: String) -> void:
	errors.append(reason)

func _abort_run(phase: String, game: Node, client: NpcAgentClient, initial_ref: Dictionary) -> void:
	failures.append("HARNESS_ABORTED_%s" % phase)
	var frame_limit := "12000" if real_service else "1200"
	var command_contract := "godot --headless --path <staged_project> --script res://tests/npc_play_loop_harness.gd --quit-after %s -- %s--report-path <path>" % [frame_limit, "--real-service " if real_service else ""]
	var report := {
		"mode": "real_service" if real_service else "fake_p_interpreter",
		"transport_mode": str((client as Node).get("transport_mode")),
		"real_wait_timeout_ms": REAL_WAIT_TIMEOUT_MS,
		"passed": false,
		"fatal_phase": phase,
		"phases": completed_phases.duplicate(),
		"frames": frames,
		"report_path": report_path,
		"report_path_arg": "--report-path <path>",
		"command_contract": command_contract,
		"events": {
			"request_count": request_events.size(),
			"event_kinds": _request_kinds(),
			"session_epochs": _request_epochs(),
			"decision_count": decision_count,
			"result_ack_count": ack_count,
			"directive_codes": directive_codes.duplicate(),
		},
		"decision_provenance": decision_provenance.duplicate(true),
		"request_events": request_events.duplicate(true),
		"initial_state_ref": initial_ref,
		"final_state_ref": game.npc_state_ref(),
		"final_observation": game.npc_public_observation(),
		"session_id": client.launch_identity().get("session_id", ""),
		"errors": failures + errors,
	}
	_write_report(report)
	quit(1)

func _wait_for_requests_deadline(events: Array, expected: int, timeout_ms: int) -> bool:
	var deadline := Time.get_ticks_msec() + timeout_ms
	while events.size() < expected and Time.get_ticks_msec() < deadline:
		await process_frame
		frames += 1
	return events.size() >= expected

func _wait_for_waiting_action_deadline(game: Node, operation: String, timeout_ms: int) -> bool:
	var deadline := Time.get_ticks_msec() + timeout_ms
	while str(game._npc_waiting_action.get("operation", "")) != operation and Time.get_ticks_msec() < deadline:
		await process_frame
		frames += 1
	return str(game._npc_waiting_action.get("operation", "")) == operation

func _wait_for_goal_deadline(game: Node, timeout_ms: int) -> bool:
	var deadline := Time.get_ticks_msec() + timeout_ms
	while not bool(game.npc_public_observation().get("goal_reached", false)) and Time.get_ticks_msec() < deadline:
		await process_frame
		frames += 1
	return bool(game.npc_public_observation().get("goal_reached", false))

func _wait_for_acks_deadline(current: int, expected: int, timeout_ms: int) -> bool:
	var deadline := Time.get_ticks_msec() + timeout_ms
	while ack_count < expected and Time.get_ticks_msec() < deadline:
		await process_frame
		frames += 1
	return ack_count >= expected and ack_count >= current

func _wait_for_decisions_deadline(expected: int, timeout_ms: int) -> bool:
	var deadline := Time.get_ticks_msec() + timeout_ms
	while decision_count < expected and Time.get_ticks_msec() < deadline:
		await process_frame
		frames += 1
	return decision_count >= expected

func _wait_for_requests(events: Array, expected: int, max_frames: int = 600) -> bool:
	if real_service:
		return await _wait_for_requests_deadline(events, expected, REAL_WAIT_TIMEOUT_MS)
	for _index in range(max_frames):
		if events.size() >= expected:
			return true
		await process_frame
		frames += 1
	return events.size() >= expected

func _wait_for_waiting_action(game: Node, operation: String, max_frames: int = 600) -> bool:
	if real_service:
		return await _wait_for_waiting_action_deadline(game, operation, REAL_WAIT_TIMEOUT_MS)
	for _index in range(max_frames):
		if str(game._npc_waiting_action.get("operation", "")) == operation:
			return true
		await process_frame
		frames += 1
	return str(game._npc_waiting_action.get("operation", "")) == operation

func _wait_for_goal(game: Node, max_frames: int = 600) -> bool:
	if real_service:
		return await _wait_for_goal_deadline(game, REAL_WAIT_TIMEOUT_MS)
	for _index in range(max_frames):
		if bool(game.npc_public_observation().get("goal_reached", false)):
			return true
		await process_frame
		frames += 1
	return bool(game.npc_public_observation().get("goal_reached", false))

func _wait_for_acks(current: int, expected: int, max_frames: int = 600) -> bool:
	if real_service:
		return await _wait_for_acks_deadline(current, expected, REAL_WAIT_TIMEOUT_MS)
	for _index in range(max_frames):
		if ack_count >= expected:
			return true
		await process_frame
		frames += 1
	return ack_count >= expected and ack_count >= current

func _wait_for_decisions(expected: int, max_frames: int = 600) -> bool:
	if real_service:
		return await _wait_for_decisions_deadline(expected, REAL_WAIT_TIMEOUT_MS)
	for _index in range(max_frames):
		if decision_count >= expected:
			return true
		await process_frame
		frames += 1
	return decision_count >= expected

func _run_contract_controls() -> void:
	var control_game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(control_game)
	await _tick(2)
	var control_client: NpcAgentClient = await _replace_client(control_game)
	_connect_observers(control_client, control_game)

	var player_steps := [{
		"action_id": "contract-valid-player",
		"operation": "acquire_object",
		"execution_mode": "player_request",
		"arguments": {"object_id": "signal_lens"},
	}]
	var player_before := directive_codes.size()
	var player_result := _contract_decision(control_client, control_game, _contract_body("WAITING_PLAYER", "signal", player_steps))
	var player_directive_delta := directive_codes.size() - player_before
	var player_passed := bool(player_result.get("accepted", false)) and player_directive_delta == 1
	contract_controls.append({"name": "valid_player_action", "accepted": bool(player_result.get("accepted", false)), "directive_delta": player_directive_delta, "passed": player_passed})
	_check(player_passed, "valid_player_action_control_must_be_accepted")

	for status in ["CANCELLED", "FAILED", "UNKNOWN"]:
		var action_id := "contract-%s" % str(status).to_lower()
		var steps := [{
			"action_id": action_id,
			"operation": "acquire_object",
			"execution_mode": "player_request",
			"arguments": {"object_id": "signal_lens"},
		}]
		var before_ref: Dictionary = control_game.npc_state_ref()
		var before := directive_codes.size()
		var result := _contract_decision(control_client, control_game, _contract_body(status, "signal", steps))
		var after_ref: Dictionary = control_game.npc_state_ref()
		var delta := directive_codes.size() - before
		var state_unchanged := before_ref == after_ref
		var passed := not bool(result.get("accepted", false)) and delta == 0 and state_unchanged
		contract_controls.append({"name": "status_%s_rejected" % str(status).to_lower(), "accepted": bool(result.get("accepted", false)), "directive_delta": delta, "state_unchanged": state_unchanged, "state_ref_before": before_ref.duplicate(true), "state_ref_after": after_ref.duplicate(true), "codes": result.get("codes", []), "passed": passed})
		_check(passed, "status_%s_must_not_issue_directive" % str(status).to_lower())

	var arbitrary_target_steps := [{
		"action_id": "contract-arbitrary-target",
		"operation": "acquire_object",
		"execution_mode": "player_request",
		"arguments": {"object_id": "signal_lens"},
	}]
	var arbitrary_before_ref: Dictionary = control_game.npc_state_ref()
	var arbitrary_before := directive_codes.size()
	var arbitrary_result := _contract_decision(control_client, control_game, _contract_body("WAITING_PLAYER", "arbitrary_target", arbitrary_target_steps))
	var arbitrary_after_ref: Dictionary = control_game.npc_state_ref()
	var arbitrary_delta := directive_codes.size() - arbitrary_before
	var arbitrary_state_unchanged := arbitrary_before_ref == arbitrary_after_ref
	var arbitrary_passed := not bool(arbitrary_result.get("accepted", false)) and arbitrary_delta == 0 and arbitrary_state_unchanged
	contract_controls.append({"name": "arbitrary_target_rejected", "accepted": bool(arbitrary_result.get("accepted", false)), "directive_delta": arbitrary_delta, "state_unchanged": arbitrary_state_unchanged, "state_ref_before": arbitrary_before_ref.duplicate(true), "state_ref_after": arbitrary_after_ref.duplicate(true), "codes": arbitrary_result.get("codes", []), "passed": arbitrary_passed})
	_check(arbitrary_passed, "arbitrary_target_must_not_issue_directive")

	var empty_before_ref: Dictionary = control_game.npc_state_ref()
	var empty_before := directive_codes.size()
	var empty_result := _contract_decision(control_client, control_game, _contract_body("ERROR", null, []))
	var empty_after_ref: Dictionary = control_game.npc_state_ref()
	var empty_delta := directive_codes.size() - empty_before
	var empty_state_unchanged := empty_before_ref == empty_after_ref
	var empty_passed := not bool(empty_result.get("accepted", false)) and empty_delta == 0 and empty_state_unchanged
	contract_controls.append({"name": "empty_error_rejected", "accepted": bool(empty_result.get("accepted", false)), "directive_delta": empty_delta, "state_unchanged": empty_state_unchanged, "state_ref_before": empty_before_ref.duplicate(true), "state_ref_after": empty_after_ref.duplicate(true), "codes": empty_result.get("codes", []), "passed": empty_passed})
	_check(empty_passed, "empty_error_must_not_be_accepted")

	control_game._on_npc_cancel_requested()
	await _tick(1)
	control_game._open_mira_dialogue()
	await _tick(1)
	var dialogue_steps := [{
		"action_id": "contract-valid-dialogue",
		"operation": "clarify",
		"execution_mode": "dialogue",
		"arguments": {},
	}]
	var dialogue_before := directive_codes.size()
	var dialogue_result := _contract_decision(control_client, control_game, _contract_body("WAITING_DIALOGUE", null, dialogue_steps))
	var dialogue_delta := directive_codes.size() - dialogue_before
	var dialogue_passed := bool(dialogue_result.get("accepted", false)) and dialogue_delta == 1
	contract_controls.append({"name": "valid_dialogue_action", "accepted": bool(dialogue_result.get("accepted", false)), "directive_delta": dialogue_delta, "passed": dialogue_passed})
	_check(dialogue_passed, "valid_dialogue_control_must_be_accepted")
	control_game.queue_free()

func _contract_body(status: String, target: Variant, steps: Array) -> Dictionary:
	return {
		"intent_id": "contract-%s" % status.to_lower(),
		"typed_intent": {"label": "ASK_INFORMATION", "claims": [{"code": "NONE", "state": "UNVERIFIED"}], "target": target},
		"plan_id": "contract-plan",
		"steps": steps,
		"planning_context_digest": "a".repeat(64),
		"status": status,
		"error": null,
	}

func _contract_context(client: NpcAgentClient, state_ref: Dictionary, request_id: String) -> Dictionary:
	var identity := client.launch_identity()
	return {
		"generation": int(client.get("_request_generation")),
		"session_epoch": int(identity.get("session_epoch", -1)),
		"session_id": str(identity.get("session_id", "")),
		"episode_id": str(identity.get("episode_id", "")),
		"request_id": request_id,
		"event_kind": "observation",
		"goal_id": NpcAgentClient.GOAL_ID,
		"goal_version": NpcAgentClient.GOAL_VERSION,
		"policy_hash": str(identity.get("policy_hash", "")),
		"config_hash": str(identity.get("config_hash", "")),
		"expected_revision": int(state_ref.get("revision", -1)),
		"expected_sha256": str(state_ref.get("sha256", "")),
		"deadline_ms": Time.get_ticks_msec() + 30000,
	}

func _contract_decision(client: NpcAgentClient, game: Node, body: Dictionary) -> Dictionary:
	var state_ref: Dictionary = game.npc_state_ref()
	var request_id := "request-%s" % str(body.get("intent_id", ""))
	var envelope := client._build_envelope("decision", request_id, body, state_ref, "")
	var context := _contract_context(client, state_ref, request_id)
	return client.accept_decision(envelope, context, state_ref)

func _run_stale_and_cancel_controls() -> void:
	var stale_game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(stale_game)
	await _tick(2)
	var stale_initial: Dictionary = stale_game.npc_state_ref()
	stale_game._npc_waiting_action = {
		"operation": "acquire_object",
		"action_id": "stale-play-loop",
		"context": {"expected_revision": int(stale_initial.get("revision", -1))},
	}
	var mutation: Dictionary = stale_game.machine.apply_operation("acquire_object", {"object_id": "signal_lens"})
	var stale_before: Dictionary = stale_game.npc_state_ref()
	stale_game._propose_acquire()
	var stale_after: Dictionary = stale_game.npc_state_ref()
	_check(bool(mutation.get("accepted", false)), "stale-control-setup-mutation_must_apply")
	_check(stale_before == stale_after and stale_game._npc_waiting_action.is_empty(), "stale_directive_must_not_reach_writer")
	stale_game.queue_free()

	var cancel_game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(cancel_game)
	await _tick(2)
	var cancel_initial: Dictionary = cancel_game.npc_state_ref()
	cancel_game._npc_waiting_action = {
		"operation": "acquire_object",
		"action_id": "cancelled-play-loop",
		"context": {"expected_revision": int(cancel_initial.get("revision", -1))},
	}
	cancel_game._on_npc_cancel_requested()
	var ordinary_before: Dictionary = cancel_game.npc_state_ref()
	cancel_game._propose_acquire()
	var ordinary_after: Dictionary = cancel_game.npc_state_ref()
	_check(int(ordinary_after["revision"]) == int(ordinary_before["revision"]) + 1 and bool(cancel_game.npc_public_observation().get("lens_carried", false)), "ordinary_player_action_must_work_after_cancel")
	cancel_game.queue_free()

func _request_kinds() -> Array:
	var values: Array = []
	for event in request_events:
		values.append(str(event.get("event_kind", "")))
	return values

func _request_epochs() -> Array:
	var values: Array = []
	for event in request_events:
		values.append(int(event.get("session_epoch", -1)))
	return values

func _tick(count: int) -> void:
	for _index in range(count):
		await process_frame
		frames += 1

func _check(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)

func _write_report(report: Dictionary) -> void:
	var serialized := JSON.stringify(report, "  ")
	if not report_path.is_empty():
		var absolute := ProjectSettings.globalize_path(report_path)
		var file := FileAccess.open(absolute, FileAccess.WRITE)
		if file == null:
			report["passed"] = false
			report["errors"].append("REPORT_WRITE_FAILED")
		else:
			file.store_string(serialized)
			file.close()
	print(RESULT_PREFIX + JSON.stringify(report))
