extends SceneTree

const MAIN_SCENE := "res://scenes/main_3d.tscn"
const TRANSPORT_SCRIPT := preload("res://tests/npc_play_loop_transport.gd")
const RESULT_PREFIX := "NPC_PLAY_LOOP_RESULT "

var failures: Array[String] = []
var errors: Array[String] = []
var frames: int = 0
var decision_count: int = 0
var ack_count: int = 0
var directive_codes: Array[String] = []
var request_events: Array = []
var report_path := ""
var real_service := false

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	real_service = "--real-service" in args
	var report_index := args.find("--report-path")
	if report_index >= 0 and report_index + 1 < args.size():
		report_path = str(args[report_index + 1])
	call_deferred("_run")

func _run() -> void:
	var game: Node = load(MAIN_SCENE).instantiate()
	root.add_child(game)
	await _tick(3)
	var client: NpcAgentClient = game.npc_client
	if not real_service:
		client = await _replace_client(game)
	_connect_observers(client, game)
	if not real_service:
		request_events = (client as Node).get("requests")

	var initial_ref: Dictionary = game.npc_state_ref()
	game._open_mira_dialogue()
	await _tick(1)
	_check(request_events.is_empty(), "initial_open_must_not_request_without_prior_intent")
	_check(not bool(game.npc_public_observation().get("goal_reached", false)), "initial_goal_must_be_false")

	game._on_npc_text_submitted("Please help me restore the harbor signal and then reveal the tide marks hint.")
	_check(await _wait_for_requests(request_events, 1), "utterance_request_must_complete")
	_check(await _wait_for_waiting_action(game, "acquire_object"), "utterance_must_issue_acquire_directive")
	_check(request_events.size() >= 1 and str(request_events[0].get("event_kind", "")) == "utterance", "first_request_must_be_utterance")

	game._on_choice("leave")
	await _tick(1)
	var after_close_ref: Dictionary = game.npc_state_ref()
	_check(after_close_ref == initial_ref, "ordinary_dialogue_close_must_not_mutate_world")
	game._propose_acquire()
	await _tick(1)
	var acquired_ref: Dictionary = game.npc_state_ref()
	_check(int(acquired_ref["revision"]) == int(initial_ref["revision"]) + 1, "explicit_acquire_must_increment_revision_once")
	_check(str(acquired_ref["sha256"]) != str(initial_ref["sha256"]), "explicit_acquire_must_change_state_hash")
	_check(bool(game.npc_public_observation().get("lens_carried", false)), "explicit_acquire_must_change_public_observation")

	game._open_mira_dialogue()
	_check(await _wait_for_requests(request_events, 2), "first_resume_observation_must_complete")
	_check(await _wait_for_waiting_action(game, "install_lens"), "first_resume_must_issue_install_directive")
	_check(str(request_events[1].get("event_kind", "")) == "observation", "first_resume_must_be_observation_only")
	game._on_choice("leave")
	await _tick(1)
	game._propose_install()
	await _tick(1)
	var installed_ref: Dictionary = game.npc_state_ref()
	_check(int(installed_ref["revision"]) == int(acquired_ref["revision"]) + 1, "explicit_install_must_increment_revision_once")
	_check(str(installed_ref["sha256"]) != str(acquired_ref["sha256"]), "explicit_install_must_change_state_hash")
	_check(bool(game.npc_public_observation().get("signal_restored", false)), "explicit_install_must_restore_signal")
	_check(bool(game.npc_public_observation().get("tide_lead_authorized", false)), "install_must_authorize_mira_lead")

	game._open_mira_dialogue()
	_check(await _wait_for_requests(request_events, 4), "second_resume_and_result_observations_must_complete")
	_check(await _wait_for_goal(game), "authorized_reveal_must_reach_goal")
	_check(await _wait_for_acks(ack_count, 1), "reveal_result_ack_must_be_received")
	_check(await _wait_for_decisions(4), "post_ack_observation_decision_must_complete")
	_check(str(request_events[2].get("event_kind", "")) == "observation", "second_resume_must_be_observation_only")
	_check(str(request_events[3].get("event_kind", "")) == "observation", "post_ack_replan_must_be_observation_only")
	var final_observation: Dictionary = game.npc_public_observation()
	var final_ref: Dictionary = game.npc_state_ref()
	_check(int(final_ref["revision"]) == int(installed_ref["revision"]) + 1, "reveal_must_increment_revision_once")
	_check(str(final_ref["sha256"]) != str(installed_ref["sha256"]), "reveal_must_change_state_hash")
	_check(bool(final_observation.get("goal_reached", false)), "final_observation_must_report_goal_reached")
	_check("tide_marks_hint" in game.machine.state["facts"], "authorized_hint_must_be_committed_to_world")

	await _run_stale_and_cancel_controls()
	var frame_limit := "12000" if real_service else "1200"
	var command_contract := "godot --headless --path <staged_project> --script res://tests/npc_play_loop_harness.gd --quit-after %s -- %s--report-path <path>" % [frame_limit, "--real-service " if real_service else ""]
	var report := {
		"mode": "real_service" if real_service else "fake_p_interpreter",
		"passed": failures.is_empty() and errors.is_empty(),
		"phases": ["initial_open", "utterance", "close", "acquire", "resume_install", "close", "install", "resume_reveal", "goal"],
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
		"initial_state_ref": initial_ref,
		"installed_state_ref": installed_ref,
		"final_state_ref": final_ref,
		"final_observation": final_observation,
		"session_id": client.launch_identity().get("session_id", "") if client != null else "",
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
	var game_decision := Callable(game, "_on_npc_decision")
	if not client.decision_received.is_connected(game_decision):
		client.decision_received.connect(game_decision)
	var game_result := Callable(game, "_on_npc_result_recorded")
	if not client.result_recorded.is_connected(game_result):
		client.result_recorded.connect(game_result)
	var game_directive := Callable(game, "_on_npc_directive")
	if not client.directive_received.is_connected(game_directive):
		client.directive_received.connect(game_directive)
	var game_error := Callable(game, "_on_npc_protocol_error")
	if not client.protocol_error.is_connected(game_error):
		client.protocol_error.connect(game_error)
	client.decision_received.connect(Callable(self, "_on_decision"))
	client.result_recorded.connect(Callable(self, "_on_ack"))
	client.directive_received.connect(Callable(self, "_on_directive"))
	client.protocol_error.connect(Callable(self, "_on_protocol_error"))

func _on_decision(envelope: Dictionary, context: Dictionary) -> void:
	decision_count += 1
	if real_service:
		request_events.append({
			"event_kind": str(context.get("event_kind", "")),
			"session_epoch": int(context.get("session_epoch", -1)),
			"request_id": str(envelope.get("request_id", "")),
		})
func _on_ack(_envelope: Dictionary, _context: Dictionary) -> void:
	ack_count += 1

func _on_directive(code: String, _payload: Dictionary) -> void:
	directive_codes.append(code)

func _on_protocol_error(reason: String) -> void:
	errors.append(reason)

func _wait_for_requests(events: Array, expected: int, max_frames: int = 600) -> bool:
	for _index in range(max_frames):
		if events.size() >= expected:
			return true
		await process_frame
		frames += 1
	return events.size() >= expected

func _wait_for_waiting_action(game: Node, operation: String, max_frames: int = 600) -> bool:
	for _index in range(max_frames):
		if str(game._npc_waiting_action.get("operation", "")) == operation:
			return true
		await process_frame
		frames += 1
	return str(game._npc_waiting_action.get("operation", "")) == operation

func _wait_for_goal(game: Node, max_frames: int = 600) -> bool:
	for _index in range(max_frames):
		if bool(game.npc_public_observation().get("goal_reached", false)):
			return true
		await process_frame
		frames += 1
	return bool(game.npc_public_observation().get("goal_reached", false))

func _wait_for_acks(current: int, expected: int, max_frames: int = 600) -> bool:
	for _index in range(max_frames):
		if ack_count >= expected:
			return true
		await process_frame
		frames += 1
	return ack_count >= expected and ack_count >= current

func _wait_for_decisions(expected: int, max_frames: int = 600) -> bool:
	for _index in range(max_frames):
		if decision_count >= expected:
			return true
		await process_frame
		frames += 1
	return decision_count >= expected

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
