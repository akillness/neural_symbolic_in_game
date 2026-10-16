extends Node3D

## Root controller of the Sealed Lighthouse 3D presentation slice.
##
## Authority model (GDI-01..GDI-05): the authored SealedLighthouseMachine mirror
## is the only writer of canonical state. Every player intent becomes a proposal;
## refusals leave the prior state (and hash) untouched and surface a neutral
## reason plus the next valid affordance. Presentation reads committed snapshots.
##
## Player-visible strings cite worldview IDs (W-*, SL-GDD-T1) in comments.
## Headless verification: run with `--headless -- --smoke` to execute the scripted
## M6-shaped sequence through the same proposal router used by live play.

const SealedLighthouseMachine = preload("res://scripts/sealed_lighthouse_machine.gd")
const CanonicalState = preload("res://scripts/canonical_state.gd")
const ProceduralAudioFeedbackScript = preload("res://scripts/game3d/procedural_audio.gd")
const EvaluationTraceScript = preload("res://scripts/game3d/evaluation_trace.gd")
const NpcAgentClientScript = preload("res://scripts/game3d/npc_agent_client.gd")

const SCENARIO_PATH := "res://data/sealed_lighthouse.json"
const NPC_CONFIG_PATH := "res://data/npc-goal-recovery.json"
const SAVE_PATH := "user://sl3d_save.json"
const TUTORIAL_SEEN_PATH := "user://sl3d_tutorial_seen.flag"
const RECEIPT_SCHEMA_VERSION := "1.0.0"
const RECEIPT_BUILD_ID := "sealed-lighthouse-presentation-telemetry-v1"
const RECEIPT_SCENE_ID := "main_3d"
const RECEIPT_SOURCE_PATHS := [
	"res://project.godot",
	"res://scenes/main_3d.tscn",
	"res://data/sealed_lighthouse.json",
	"res://scripts/canonical_state.gd",
	"res://scripts/sealed_lighthouse_machine.gd",
	"res://scripts/game3d/game_3d.gd",
	"res://scripts/game3d/golden_path_layout.gd",
	"res://scripts/game3d/evaluation_trace.gd",
	"res://scripts/game3d/harbor_ledger_ui.gd",
]
const RECEIPT_FORBIDDEN_PAYLOAD_TOKENS := [
	"fact_id", "fact_ids", "hidden_fact", "oracle", "save_path", "user_text",
]

var machine: SealedLighthouseMachine
var scenario: Dictionary
var handles: Dictionary
var player: PlayerInvestigator3D
var ui: HarborLedgerUI
var director: NarrativeDirector
var audio_feedback: ProceduralAudioFeedback
var _objective_beacon: Node3D
var commit_count: int = 0
var refusal_count: int = 0
var episode_over: bool = false
var _first_commit_explained: bool = false
var _first_refusal_explained: bool = false
var _dialogue_open: bool = false
var _met_mira: bool = false
var _lighthouse_observed: bool = false
var _smoke_mode: bool = false
var npc_client: NpcAgentClient
var _npc_waiting_action: Dictionary = {}
var _npc_action_results: Dictionary = {}
var _npc_evaluate_mode: bool = false
var _npc_replay_mode: bool = false
var _npc_bootstrap_mode: bool = false
var _npc_experiment_mode: bool = false
var _npc_engineering_path: String = ""
var _npc_bootstrap_path: String = ""
var _npc_experiment_path: String = ""
var _npc_engineering_events: Array = []
var _npc_engineering_errors: Array = []
var _evaluate_mode: bool = false
var _autoplay_mode: bool = false
## Presentation-only dashboard bridge (D-065): when the Web build is embedded
## in a page, typed events are mirrored to the parent via postMessage. It reads
## only the snapshots the hard writer returns plus presentation counters and
## never carries sealed fact IDs, hidden oracle labels, or rig identity. The
## page has no authority over canonical state.
const DASHBOARD_CHANNEL := "trace-rpg-dashboard"
const DASHBOARD_TICK_SECONDS := 0.25
var _dashboard_enabled: bool = false
var _receipt_export_failed: bool = false
const RECEIPT_MAX_ROWS := 4096
var _receipt_recording_enabled: bool = false
var _receipt_overflowed: bool = false
var _dashboard_seq: int = 0
var _dashboard_tick_elapsed: float = 0.0
var _dashboard_focus: String = ""
var _play_started: bool = false
var _evaluation_path: String = ""
var _receipt_output_path: String = ""
var _telemetry_initial_state_hash: String = ""
var _pending_input_feedback: Dictionary = {}
var _telemetry_started_us: int = 0
var _telemetry_session_id: String = ""
var _build_fingerprint: Dictionary = {}
var _receipt_sequence: int = 0
var _observation_receipts: Array[Dictionary] = []
var _case_revisit_sequence: int = 0
var _last_objective_receipt_code: String = ""
var _input_feedback_samples: Array = []
## D-073 detective-loop presentation state (view-local; never saved, hashed
## or replayed): hint-ladder rung, case-file pip, coach cards shown, first-focus
## toasts, held-proposal texts (deduction distractors) and the slot-assembly
## deduction in progress. None of it is a second game-state model.
var _hint_rung: int = 0
var _hint_timer: Timer
var _presentation_hooks_ready: bool = false
var _coach_cards_shown: Array = []
var _coach_cards_pending: Array = []
var _focus_toasts_shown: Array = []
var _held_texts: Array = []
var _inference_by_gate: Dictionary = {}
var _deduction_open: bool = false
var _deduction_picks: Array = []
var _deduction_attempts: int = 0
var _deduction_confirmed: bool = false


func _enter_tree() -> void:
	_register_input_actions()


func _ready() -> void:
	_telemetry_started_us = Time.get_ticks_usec()
	var user_args := OS.get_cmdline_user_args()
	_smoke_mode = "--smoke" in user_args
	_autoplay_mode = "--autoplay" in user_args
	var evaluate_index := user_args.find("--evaluate")
	_evaluate_mode = evaluate_index != -1
	if _evaluate_mode:
		_evaluation_path = (
			user_args[evaluate_index + 1]
			if evaluate_index + 1 < user_args.size()
			else "user://sealed-lighthouse-3d-engineering-evaluation.json"
		)
	var npc_evaluate_index := user_args.find("--npc-evaluate")
	_npc_evaluate_mode = npc_evaluate_index != -1
	if _npc_evaluate_mode:
		_npc_engineering_path = (
			user_args[npc_evaluate_index + 1]
			if npc_evaluate_index + 1 < user_args.size()
			else "user://npc-engineering-evaluate.json"
		)
	var npc_replay_index := user_args.find("--npc-replay")
	_npc_replay_mode = npc_replay_index != -1
	if _npc_replay_mode:
		_npc_engineering_path = (
			user_args[npc_replay_index + 1]
			if npc_replay_index + 1 < user_args.size()
			else "user://npc-engineering-replay.json"
		)
	var npc_bootstrap_index := user_args.find("--npc-bootstrap")
	_npc_bootstrap_mode = npc_bootstrap_index != -1
	if _npc_bootstrap_mode:
		_npc_bootstrap_path = user_args[npc_bootstrap_index + 1] if npc_bootstrap_index + 1 < user_args.size() else "user://npc-bootstrap.json"
	var npc_experiment_index := user_args.find("--npc-experiment")
	_npc_experiment_mode = npc_experiment_index != -1
	if _npc_experiment_mode:
		_npc_experiment_path = user_args[npc_experiment_index + 1] if npc_experiment_index + 1 < user_args.size() else "user://npc-experiment.json"

	var receipt_output_index := user_args.find("--receipt-output")
	if receipt_output_index != -1:
		if receipt_output_index + 1 >= user_args.size() or str(user_args[receipt_output_index + 1]).begins_with("--"):
			_receipt_export_failed = true
			push_error("--receipt-output requires a file path")
		else:
			_receipt_output_path = user_args[receipt_output_index + 1]
	_receipt_recording_enabled = _evaluate_mode or not _receipt_output_path.is_empty()
	scenario = _load_scenario()
	machine = SealedLighthouseMachine.new(scenario)
	if _receipt_recording_enabled:
		_build_fingerprint = _compute_build_fingerprint()
		_telemetry_session_id = "local-" + CanonicalState.sha256({
			"started_us": _telemetry_started_us,
			"initial_state_sha256": machine.state_hash(),
		}).substr(0, 16)
	_telemetry_initial_state_hash = machine.state_hash()

	handles = SealedLighthouseWorldBuilder.build(self)
	_objective_beacon = _build_objective_beacon()
	handles["objective_beacon"] = _objective_beacon
	player = PlayerInvestigator3D.create()
	player.position = Vector3(0.0, 0.2, 2.0)
	add_child(player)

	ui = HarborLedgerUI.new()
	add_child(ui)
	npc_client = NpcAgentClientScript.new()
	add_child(npc_client)
	npc_client.setup(self, ui)

	audio_feedback = ProceduralAudioFeedbackScript.new()
	add_child(audio_feedback)
	director = NarrativeDirector.new()
	add_child(director)
	director.setup(handles, player)
	director.cinematic_state_changed.connect(ui.set_letterbox)

	_spawn_interactables()
	player.interact_requested.connect(_on_interact)
	player.focus_changed.connect(_on_focus_changed)
	player.footstep_requested.connect(_on_footstep_requested)
	player.fall_recovered.connect(_on_player_fall_recovered)
	ui.choice_selected.connect(_on_choice)
	ui.npc_text_submitted.connect(_on_npc_text_submitted)
	ui.npc_capability_submitted.connect(_on_npc_capability_submitted)
	npc_client.result_recorded.connect(_on_npc_result_recorded)
	ui.npc_cancel_requested.connect(_on_npc_cancel_requested)
	npc_client.decision_received.connect(_on_npc_decision)
	npc_client.directive_received.connect(_on_npc_directive)
	npc_client.protocol_error.connect(_on_npc_protocol_error)

	ui.start_requested.connect(_on_start_requested)
	ui.audio_toggle_requested.connect(_on_audio_toggle_requested)
	ui.tutorial_closed.connect(_on_tutorial_closed)
	audio_feedback.audio_unlocked.connect(_sync_audio_state)
	audio_feedback.mute_changed.connect(func(_muted: bool) -> void: _sync_audio_state())
	if director.has_signal("lightning_struck"):
		# WorldFeel contract: distant offshore lightning (tension-gated, motion-
		# gated on the director side). Thunder trails the flash like real storm
		# sound: farther/weaker strikes arrive later and quieter.
		director.lightning_struck.connect(_on_lightning_struck)

	_sync_presentation()
	_dashboard_setup()
	if _smoke_mode:
		_run_smoke.call_deferred()
		return
	if _evaluate_mode:
		_run_engineering_evaluation.call_deferred(_evaluation_path)
		return
	if _npc_evaluate_mode:
		_run_npc_engineering_evaluation.call_deferred(_npc_engineering_path)
		return
	if _npc_bootstrap_mode:
		_run_npc_bootstrap.call_deferred(_npc_bootstrap_path)
		return
	if _npc_experiment_mode:
		_run_npc_experiment.call_deferred(_npc_experiment_path)
		return
	if _npc_replay_mode:
		_run_npc_replay.call_deferred(_npc_engineering_path)
		return
	var shot_index := user_args.find("--shot")
	if shot_index != -1 and shot_index + 1 < user_args.size():
		var shot_stage := "arrival"
		var shot_stage_index := user_args.find("--shot-stage")
		if shot_stage_index != -1 and shot_stage_index + 1 < user_args.size():
			shot_stage = user_args[shot_stage_index + 1]
		_run_screenshot.call_deferred(user_args[shot_index + 1], shot_stage)
		return

	if OS.has_feature("web"):
		player.input_locked = true
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.show_start_gate(true)
		ui.set_cursor_captured(false)
		return
	if _autoplay_mode:
		_run_autoplay.call_deferred()
		return
	_start_experience(false)


## ------------------------------------------------------------ dashboard bridge

func _dashboard_setup() -> void:
	if not OS.has_feature("web") or _smoke_mode or _evaluate_mode:
		return
	var embedded = JavaScriptBridge.eval("(window.parent && window.parent !== window) ? 1 : 0")
	_dashboard_enabled = int(embedded) == 1


func _emit_dashboard(kind: String, payload: Dictionary) -> void:
	if not _dashboard_enabled:
		return
	_dashboard_seq += 1
	var envelope := {
		"channel": DASHBOARD_CHANNEL,
		"seq": _dashboard_seq,
		"kind": kind,
		"t_ms": Time.get_ticks_msec(),
		"engineering_only": true,
		"payload": payload,
	}
	JavaScriptBridge.eval("window.parent.postMessage(%s, '*')" % JSON.stringify(envelope))


func _dashboard_state_summary() -> Dictionary:
	# Reads only the committed snapshot the machine exposes plus presentation
	# counters; fact IDs are deliberately not listed (sealed facts stay sealed).
	return {
		"state_sha256": machine.state_hash(),
		"revision": int(machine.state.get("revision", 0)),
		"stage": int(machine.state["quest"]["stage"]),
		"fact_count": (machine.state["facts"] as Array).size(),
		"commit_count": commit_count,
		"refusal_count": refusal_count,
	}


func _dashboard_sites() -> Array:
	var sites: Array = []
	for spec in GoldenPathLayout.interactable_specs():
		var position: Vector3 = spec["position"]
		sites.append({"id": str(spec["id"]), "x": position.x, "z": position.z})
	return sites


func _process(delta: float) -> void:
	if not _dashboard_enabled or player == null:
		return
	_dashboard_tick_elapsed += delta
	if _dashboard_tick_elapsed < DASHBOARD_TICK_SECONDS:
		return
	_dashboard_tick_elapsed = 0.0
	_emit_dashboard("tick", {
		"x": snappedf(player.global_position.x, 0.01),
		"z": snappedf(player.global_position.z, 0.01),
		"yaw": snappedf(player.rotation.y, 0.001),
		"focus": _dashboard_focus,
		"play_started": _play_started,
		"dialogue_open": _dialogue_open,
		"tutorial_open": ui.is_tutorial_open(),
		"episode_over": episode_over,
		"stage": int(machine.state["quest"]["stage"]),
		"state_sha256": machine.state_hash(),
	})


## ------------------------------------------------------------------ autoplay

## Development-only scripted golden-path route for Movie Maker capture
## (`--write-movie`). Every beat goes through the same interaction and choice
## handlers a player would trigger, so canonical state changes only via the
## proposal router; the autopilot only substitutes for keyboard and mouse input.
## Not evidence of usability, fun, latency, or G4/G6.
func _run_autoplay() -> void:
	_start_experience(false)
	await _autoplay_wait(5.2)
	if ui.is_tutorial_open():
		ui.hide_tutorial()
		_on_tutorial_closed()
		await _autoplay_wait(0.6)
	await _autoplay_walk_to("mira")
	_toggle_case_file()
	await _autoplay_wait(0.4)
	_toggle_case_file()
	await _autoplay_wait(0.4)
	_on_interact("mira")
	await _autoplay_wait(1.8)
	_on_choice("ask_lighthouse")
	await _autoplay_wait(2.6)
	_on_choice("ask_secret")
	await _autoplay_wait(3.4)
	await _autoplay_read_coach_cards()
	_on_choice("leave")
	await _autoplay_wait(0.8)
	await _autoplay_walk_to("lens_pickup")
	_on_interact("lens_pickup")
	await _autoplay_wait(2.6)
	await _autoplay_read_coach_cards()
	await _autoplay_walk_to("lamp_mount")
	_on_interact("lamp_mount")
	await _autoplay_wait(3.0)
	await _autoplay_read_coach_cards()
	await _autoplay_walk_to("mira")
	_on_interact("mira")
	await _autoplay_wait(1.6)
	_on_choice("ask_tide")
	await _autoplay_wait(3.0)
	_on_choice("leave")
	await _autoplay_wait(0.8)
	await _autoplay_walk_to("tide_marks")
	_on_interact("tide_marks")
	await _autoplay_wait(1.6)
	# D-073 slot assembly through the same choice handler a player uses: the
	# three chain entries in order, then SUBMIT CHAIN (whole-chain check).
	for link_id in DEDUCTION_CHAIN:
		_on_choice("pick:" + str(link_id))
		await _autoplay_wait(1.0)
	_on_choice("deduction_submit")
	await _autoplay_wait(11.0)
	print("AUTOPLAY-DONE " + JSON.stringify({
		"engineering_only": true,
		"commits": commit_count,
		"holds": refusal_count,
		"episode_over": episode_over,
		"state_sha256": machine.state_hash(),
	}))
	get_tree().quit(0 if episode_over and not _receipt_export_failed else 1)


func _autoplay_read_coach_cards() -> void:
	# The autopilot "reads" each just-in-time coach card for a beat and then
	# dismisses it through the same [OK] path a player uses (a pending card
	# surfaces after the dismissal, so loop until none is open).
	var guard := 4
	while ui.is_coach_card_open() and guard > 0:
		guard -= 1
		await _autoplay_wait(2.4)
		ui.dismiss_coach_card()
		await _autoplay_wait(0.5)


func _autoplay_wait(seconds: float) -> void:
	await get_tree().create_timer(seconds).timeout


func _autoplay_walk_to(site_id: String) -> void:
	var target: Vector3 = GoldenPathLayout.site_position(site_id)
	player.autopilot_target = target
	player.autopilot_active = true
	var remaining := 14.0
	while remaining > 0.0:
		var planar := Vector2(player.global_position.x - target.x, player.global_position.z - target.z)
		if planar.length() <= 1.7:
			break
		await get_tree().physics_frame
		remaining -= get_physics_process_delta_time()
	player.autopilot_active = false
	await _autoplay_wait(0.6)


func _start_experience(unlock_audio: bool) -> void:
	if _play_started:
		return
	_play_started = true
	if unlock_audio:
		audio_feedback.unlock_from_gesture()
		audio_feedback.play_cue("start")
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	ui.set_play_started(true)
	ui.set_cursor_captured(true)
	_sync_audio_state()
	_emit_dashboard("session", {
		"scenario_id": str(scenario.get("scenario_id", scenario.get("id", "sealed-lighthouse"))),
		"sites": _dashboard_sites(),
		"spawn": {"x": 0.0, "z": 2.0},
	}.merged(_dashboard_state_summary()))
	# W-001/W-002: the saved dock, the dark tower.
	ui.ledger_line("narration", "Brinewake Dock survived. Offshore, the lighthouse stands dark in the storm.")
	director.play_intro(func() -> void:
		ui.ledger_line("narration", "Captain Mira watches the dark tower from the end of the dock.")
		# First-session clarity: the concrete first objective lands the moment
		# control returns (intro ≈4.6 s, instant under reduced motion), inside
		# the ~6 s onboarding window. The amber beacon marks the same target.
		ui.ledger_line("hint", "Speak with Captain Mira first. The amber beacon marks your current lead.")
		# First session only: the onboarding folio opens itself, then [T] reopens it.
		if not FileAccess.file_exists(TUTORIAL_SEEN_PATH):
			var flag := FileAccess.open(TUTORIAL_SEEN_PATH, FileAccess.WRITE)
			if flag != null:
				flag.store_string("seen")
				flag.close()
			_open_tutorial()
		else:
			ui.toast("CURRENT LEAD | Follow the amber beacon to Captain Mira.")
	)


func _on_start_requested() -> void:
	# On web this callback is reached directly from the button press, keeping
	# pointer lock and audio resume inside the browser's user-gesture boundary.
	_start_experience(true)


func _load_scenario() -> Dictionary:
	var text := FileAccess.get_file_as_string(SCENARIO_PATH)
	var parsed: Variant = JSON.parse_string(text)
	assert(parsed is Dictionary, "scenario document must parse")
	return parsed

func npc_state_ref() -> Dictionary:
	return {"revision": int(machine.state.get("revision", 0)), "sha256": machine.state_hash()}


func _npc_policy_hash_projection() -> Variant:
	var policy: Variant = scenario.get("disclosure_policy", {})
	if not policy is Dictionary:
		return policy
	var normalized: Dictionary = policy.duplicate(true)
	var stage_gates: Variant = normalized.get("stage_gates", null)
	if not stage_gates is Array:
		return normalized
	var normalized_gates: Array = []
	for gate in stage_gates:
		if gate is Dictionary:
			var normalized_gate: Dictionary = gate.duplicate(true)
			var minimum_stage: Variant = normalized_gate.get("minimum_stage", null)
			if minimum_stage is float and is_equal_approx(minimum_stage, round(minimum_stage)):
				normalized_gate["minimum_stage"] = int(minimum_stage)
			normalized_gates.append(normalized_gate)
		else:
			normalized_gates.append(gate)
	normalized["stage_gates"] = normalized_gates
	return normalized


func npc_policy_hash() -> String:
	return CanonicalState.sha256(_npc_policy_hash_projection())


func npc_config_hash() -> String:
	return _npc_input_hash(NPC_CONFIG_PATH)


func npc_public_observation() -> Dictionary:
	var state: Dictionary = machine.state
	var locations: Dictionary = state["world"]["object_locations"]
	var reachable: Array = state["world"]["reachable_locations"]
	var inventory: Array = state["player"]["inventory"]
	var mira: Dictionary = state["npcs"]["captain_mira"]
	var installed: bool = "signal_lens_installed" in state["facts"]
	var stage: int = int(state["quest"]["stage"])
	var authorized: bool = "lighthouse_hint_authorized" in state["facts"]
	var mira_knows: bool = "tide_marks_hint" in mira.get("knowledge", [])
	var disclosed: bool = "tide_marks_hint" in mira.get("disclosed", [])
	var lighthouse_dark: bool = "lighthouse_dark" in state["facts"]
	return {
		"lens_reachable": locations.has("signal_lens") and str(locations["signal_lens"]) in reachable,
		"lens_carried": "signal_lens" in inventory,
		"signal_restored": installed,
		"tide_lead_authorized": stage >= 2 and mira_knows and authorized,
		"goal_reached": installed and authorized and "tide_marks_hint" in state["facts"] \
			and disclosed and stage >= 2 and lighthouse_dark,
		"in_dialogue": _dialogue_open,
	}


func _register_input_actions() -> void:
	var bindings := {
		"sl_move_forward": KEY_W,
		"sl_move_back": KEY_S,
		"sl_move_left": KEY_A,
		"sl_move_right": KEY_D,
		"sl_interact": KEY_E,
		"sl_save": KEY_F5,
		"sl_load": KEY_F9,
		"sl_motion": KEY_M,
		"sl_tutorial": KEY_T,
		"sl_audio": KEY_V,
		"sl_case_file": KEY_C,
		"sl_hint": KEY_H,
	}
	for action in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			var event := InputEventKey.new()
			event.physical_keycode = bindings[action]
			InputMap.action_add_event(action, event)


func _unhandled_input(event: InputEvent) -> void:
	if _smoke_mode or _evaluate_mode or episode_over:
		return
	if not _play_started:
		if event.is_action_pressed("sl_motion"):
			_toggle_reduced_motion()
		elif event.is_action_pressed("sl_audio"):
			_on_audio_toggle_requested()
		return
	if event.is_action_pressed("sl_audio") and not audio_feedback.is_unlocked():
		_on_audio_toggle_requested()
		return
	_unlock_audio_from_event(event)
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_ESCAPE and ui.is_tutorial_open():
			ui.hide_tutorial()
			return
		if event.physical_keycode == KEY_ESCAPE and ui.is_coach_card_open():
			ui.dismiss_coach_card()
			return
		if event.physical_keycode == KEY_ESCAPE and ui.is_evidence_board_open():
			_toggle_case_file()
			return
		if event.physical_keycode == KEY_ESCAPE and _deduction_open:
			_close_deduction()
			return
		if event.physical_keycode == KEY_ESCAPE and _dialogue_open:
			_close_dialogue()
			return
		if event.physical_keycode == KEY_ESCAPE:
			Input.mouse_mode = (
				Input.MOUSE_MODE_VISIBLE
				if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
				else Input.MOUSE_MODE_CAPTURED
			)
			ui.set_cursor_captured(Input.mouse_mode == Input.MOUSE_MODE_CAPTURED)
	elif (
		event is InputEventMouseButton
		and event.button_index == MOUSE_BUTTON_LEFT
		and event.pressed
		and not _dialogue_open
		and not ui.is_coach_card_open()
		and not ui.is_evidence_board_open()
		and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED
	):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)
	if event is InputEventKey and event.pressed and not event.echo:
		# Number-key choice shortcut (1..9 in visible order): the same
		# _on_choice path as a button press, so a clipped/scrolled list on a
		# narrow embed stays completable by keyboard. Presentation-only input;
		# canonical state still changes only through the proposal router.
		if _dialogue_open and not _smoke_mode and not _evaluate_mode and not episode_over:
			var focus_owner := get_viewport().gui_get_focus_owner()
			var typing_in_field := focus_owner is LineEdit
			if not typing_in_field and not ui.is_tutorial_open() and not ui.is_coach_card_open() and not ui.is_evidence_board_open():
				var digit := -1
				match event.physical_keycode:
					KEY_1: digit = 1
					KEY_2: digit = 2
					KEY_3: digit = 3
					KEY_4: digit = 4
					KEY_5: digit = 5
					KEY_6: digit = 6
					KEY_7: digit = 7
					KEY_8: digit = 8
					KEY_9: digit = 9
				if digit > 0:
					var ids: Array = ui.choice_ids()
					if digit <= ids.size():
						_on_choice(str(ids[digit - 1]))
						return
	if event.is_action_pressed("sl_save"):
		_save_game()
	elif event.is_action_pressed("sl_load"):
		_load_game()
	elif event.is_action_pressed("sl_tutorial"):
		if not _dialogue_open and not episode_over:
			if ui.is_tutorial_open():
				ui.hide_tutorial()
			else:
				_open_tutorial(true)
	elif event.is_action_pressed("sl_case_file"):
		_toggle_case_file()
	elif event.is_action_pressed("sl_hint"):
		_advance_hint_ladder()
	elif event.is_action_pressed("sl_motion"):
		_toggle_reduced_motion()
	elif event.is_action_pressed("sl_audio"):
		_toggle_audio()


func _toggle_reduced_motion() -> void:
	var reduced := not director.reduce_motion
	director.reduce_motion = reduced
	ui.reduce_motion = reduced
	ui.toast("REDUCED MOTION | " + ("ON" if reduced else "OFF"))


func _unlock_audio_from_event(event: InputEvent) -> void:
	if audio_feedback.is_unlocked():
		return
	var is_gesture: bool = (
		(event is InputEventKey and event.pressed and not event.echo)
		or (event is InputEventMouseButton and event.pressed)
	)
	if is_gesture:
		audio_feedback.unlock_from_gesture()
		audio_feedback.play_cue("start")
		_sync_audio_state()


func _on_audio_toggle_requested() -> void:
	if not audio_feedback.is_unlocked():
		audio_feedback.unlock_from_gesture()
		audio_feedback.play_cue("start")
		_sync_audio_state()
		ui.toast("AUDIO | ON")
		return
	_toggle_audio()


func _toggle_audio() -> void:
	var muted := audio_feedback.toggle_muted()
	_sync_audio_state()
	if not muted:
		audio_feedback.play_cue("start")
	ui.toast("AUDIO | " + ("OFF" if muted else "ON"))


func _sync_audio_state() -> void:
	ui.set_audio_state(audio_feedback.is_unlocked(), audio_feedback.is_muted())


func _on_footstep_requested(step_index: int) -> void:
	# Steady-walk path: pick between the two literal cue names instead of
	# formatting a String per stride.
	audio_feedback.play_cue("step_0" if step_index % 2 == 0 else "step_1")


func _on_player_fall_recovered() -> void:
	ui.toast("FALL RECOVERY | Returned to the dock entrance.")


func _on_lightning_struck(intensity: float) -> void:
	# Flash-to-thunder gap: strong (near) strikes rumble sooner and louder.
	# 1.4–3.2 s of delay keeps the pair readable as one storm event without a
	# startle. play_cue itself stays mute/unlock gated.
	if episode_over:
		return
	var strength := clampf(intensity, 0.0, 1.0)
	var delay := lerpf(3.2, 1.4, strength)
	get_tree().create_timer(delay).timeout.connect(func() -> void:
		audio_feedback.play_cue("thunder", lerpf(-6.0, 0.0, strength))
	)


func _spawn_interactables() -> void:
	# Layout, pacing math, and the loop-shape rationale live in
	# GoldenPathLayout (single owner shared with the headless balance probe).
	# The mount zone masks lighthouse_view while installing (nearest-wins
	# focus), then the mount interactable disables after the install commit and
	# the view ring becomes the nearest focus on the walk back — the player
	# meets the sealed tower (and its nudge toward Mira's forbidden question)
	# mid-loop, before the tide-marks finale (W-002: observed, never entered).
	var world: Node3D = handles["world"]
	var specs: Array = GoldenPathLayout.interactable_specs()
	for spec in specs:
		var interactable := Interactable3D.create(
			spec["id"], spec["name"], spec["prompt"], spec["radius"]
		)
		interactable.position = spec["position"]
		world.add_child(interactable)
		interactable.add_to_group("sl_interactables")


func _interactable(id: String) -> Interactable3D:
	var world: Node3D = handles["world"]
	return world.get_node_or_null("Interact_%s" % id) as Interactable3D


func _on_focus_changed(interactable: Interactable3D) -> void:
	_dashboard_focus = "" if interactable == null else str(interactable.interaction_id)
	_emit_dashboard("focus", {"interaction_id": _dashboard_focus})
	if interactable == null or _dialogue_open:
		ui.hide_prompt()
	else:
		ui.show_prompt(interactable.prompt_text)
		if _play_started:
			audio_feedback.play_cue("focus")
			_first_focus_toast(str(interactable.interaction_id))


func _begin_input_feedback_probe(source: String) -> void:
	# Presentation-only clock. The sample never enters canonical state or hashes.
	_pending_input_feedback = {
		"source": source,
		"started_us": Time.get_ticks_usec(),
	}


func _complete_input_feedback_probe(visible_feedback: String) -> void:
	if _pending_input_feedback.is_empty():
		return
	var pending := _pending_input_feedback.duplicate(true)
	_pending_input_feedback.clear()
	_record_input_feedback_after_draw(pending, visible_feedback)


func _record_input_feedback_after_draw(pending: Dictionary, visible_feedback: String) -> void:
	# Acknowledgement is counted only after the frame containing the UI mutation
	# reaches the renderer. Headless runs stop at the processed-frame boundary
	# (dummy renderer; wiring evidence only); browser/user-gesture latency still
	# requires a retained Web measurement.
	await get_tree().process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
	var elapsed_ms := maxf(
		float(Time.get_ticks_usec() - int(pending["started_us"])) / 1000.0,
		0.0,
	)
	if _input_feedback_samples.size() >= 512:
		_input_feedback_samples.pop_front()
	_input_feedback_samples.append({
		"source": pending["source"],
		"visible_feedback": visible_feedback,
		"elapsed_ms": elapsed_ms,
	})


func _percentile_95(values: Array) -> float:
	if values.is_empty():
		return 0.0
	var ordered := values.duplicate()
	ordered.sort()
	var index := mini(int(ceil(0.95 * ordered.size())) - 1, ordered.size() - 1)
	return float(ordered[maxi(index, 0)])


func _input_feedback_snapshot() -> Dictionary:
	var elapsed: Array = []
	for sample in _input_feedback_samples:
		elapsed.append(float(sample["elapsed_ms"]))
	return {
		"clock": "Time.get_ticks_usec",
		"visibility_boundary": "RenderingServer.frame_post_draw",
		"measurement_context": "engine-local; headless samples are wiring evidence, not browser latency",
		"sample_count": elapsed.size(),
		"input_to_visible_feedback_ms": elapsed,
		"p95_input_to_visible_feedback_ms": _percentile_95(elapsed),
		"samples": _input_feedback_samples.duplicate(true),
	}


func _on_interact(interaction_id: String) -> void:
	if episode_over:
		return
	if _dialogue_open:
		var waiting_operation := str(_npc_waiting_action.get("operation", ""))
		if not waiting_operation.is_empty():
			var expected_interaction := "lens_pickup" if waiting_operation == "acquire_object" else "lamp_mount"
			if interaction_id != expected_interaction:
				return
	_begin_input_feedback_probe("interact:" + interaction_id)
	match interaction_id:
		"mira":
			_open_mira_dialogue()
			_complete_input_feedback_probe("mira-dialogue-open")
		"lens_pickup":
			_propose_acquire()
		"lamp_mount":
			_propose_install()
		"lighthouse_view":
			# W-002 observation only: the slice never enters the tower. The tower
			# stays dark and sealed; the first look nudges the player toward the
			# forbidden question at Mira — the intended refusal teaching moment.
			player.play_gesture(&"Observe")
			director.play_inspect_sparkle(_interactable("lighthouse_view"))
			ui.ledger_line("narration", "The tower is silent. Rain-dark glass fills the lantern room. The narrow channel cannot be crossed without a signal.")
			if not _lighthouse_observed:
				_lighthouse_observed = true
				ui.ledger_line("hint", "Captain Mira may know what happened to the tower. What she is allowed to reveal is another matter.")
			_complete_input_feedback_probe("lighthouse-observation-ledger-line")
		"tide_marks":
			player.play_gesture(&"Observe")
			director.play_inspect_sparkle(handles["tide_marks"])
			if "tide_marks_hint" in machine.state["facts"]:
				_open_deduction()
				_complete_input_feedback_probe("deduction-open")
			else:
				# Completion guidance: silent no-op left players unsure why the
				# marks do nothing before Mira authorizes the lead. Point at the
				# next valid entry without revealing the sealed lead itself.
				ui.ledger_line("hint", "The marks mean nothing yet. Ask Captain Mira for the authorized lead first.")
				ui.toast("NEXT | Ask Captain Mira for the authorized lead.")
				_complete_input_feedback_probe("tide-marks-locked-hint")


func _open_tutorial(full_guide: bool = false) -> void:
	# Boot shows the folio's page 1 only (D-073: reference card, not "the
	# tutorial"); [T] / the GUIDE handle open all four pages.
	ui.hide_prompt()
	player.input_locked = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.set_cursor_captured(false)
	ui.show_tutorial(full_guide)
	# The full folio covers what the queued coach cards would say.
	_coach_cards_pending.clear()
	ui.dismiss_coach_card()


func _on_tutorial_closed() -> void:
	if _smoke_mode or _evaluate_mode or episode_over or _dialogue_open:
		return
	player.input_locked = false
	if _play_started:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)
		if commit_count == 0 and not _met_mira:
			# The folio covered the intro hint on first sessions; re-anchor the
			# first objective the instant real control begins.
			ui.toast("CURRENT LEAD | Follow the amber beacon to Captain Mira.")


## ---------------------------------------------------------------- proposals

func _propose(
	operation: String,
	arguments: Dictionary,
	proposal_text: String,
	verdict_target: Node3D = null,
) -> Dictionary:
	ui.ledger_line("proposal", proposal_text)
	_complete_input_feedback_probe("proposal-ledger-line")
	_emit_dashboard("proposal", {"operation": operation, "text": proposal_text})
	# D-073: reconstruct the machine's check order against the committed
	# PRE-state, then let the hash-bound machine decide. The mirror only becomes
	# dashboard evidence when its failures equal the codes the machine returned.
	var mirror: Dictionary = EvaluationTraceScript.reconstruct(
		scenario, machine.state, operation, arguments
	)
	var result: Dictionary = machine.apply_operation(operation, arguments)
	_last_dashboard_trace = dashboard_trace(
		mirror["checks"], mirror["plan"],
		EvaluationTraceScript.consistent(mirror["checks"], result["codes"])
	)
	if result["accepted"]:
		commit_count += 1
		ui.flash("commit")
		# Reward cadence escalates with earned trust: the first commit is the
		# explained, gentle one; the second is quicker and brighter; from the
		# third on the stinger is quickest and most confident (P-01 legibility
		# first, ceremony reserved for the finale).
		audio_feedback.play_cue("commit_%d" % mini(commit_count, 3))
		_play_verdict_ritual(verdict_target, true)
		# Contribution clause per commit (Aside search-feedback 2026-09-02
		# pattern 2): a pure diff of the two committed snapshots names what
		# this entry actually established. Never reads canonical state beyond
		# the snapshots the machine already returned.
		var delta := contribution_delta(result["prior_state"], result["state"])
		var contribution_labels := player_visible_fact_labels(delta["facts_added"])
		_contribution_log.append({
			"entry": commit_count,
			"labels": contribution_labels,
			"stage_from": delta["stage_from"],
			"stage_to": delta["stage_to"],
		})
		_emit_dashboard("commit", {
			"operation": operation,
			"labels": contribution_labels,
			"stage_from": delta["stage_from"],
			"stage_to": delta["stage_to"],
			"state_sha256_before": CanonicalState.sha256(result["prior_state"]),
			"mutated": bool(result["mutated"]),
			"trace": _last_dashboard_trace,
		}.merged(_dashboard_state_summary()))
		var committed_chain := _case_chain_from_state(machine.state)
		var next_after_commit := str(GoldenPathLayout.next_affordance(machine.state, _met_mira).get("target_id", ""))
		_record_observation_receipt(
			"commit_emitted",
			"COMMIT",
			CanonicalState.sha256(result["prior_state"]),
			machine.state_hash(),
			{
				"operation_code": operation,
				"commit_index": commit_count,
				"stage_from": int(delta["stage_from"]),
				"stage_to": int(delta["stage_to"]),
				"chain_filled": int(committed_chain["filled"]),
				"chain_total": int(committed_chain["total"]),
				"next_affordance_target": next_after_commit,
			},
		)
		if not _first_commit_explained:
			_first_commit_explained = true
			ui.toast("FIRST COMMIT | Only validated entries change state. Watch the solid amber line.")
		elif commit_count == 2:
			ui.toast("ENTRY %d | The ledger remembers the route." % commit_count)
		_on_commit_presentation(proposal_text)
	else:
		refusal_count += 1
		ui.flash("refusal")
		audio_feedback.play_cue("refusal")
		director.play_refusal_pulse()
		_play_verdict_ritual(verdict_target, false)
		if not _first_refusal_explained:
			_first_refusal_explained = true
			ui.toast("FIRST HOLD | State is unchanged. The coral line names the reason and next valid entry.")
		_remember_held_text(proposal_text)
	return result


func _play_verdict_ritual(target: Node3D, committed: bool) -> void:
	# RitualVfx additive surface: the 3-phase inspection→verdict→settle ritual
	# layers ON TOP of the existing glow/pulse (never replaces them). Guarded so
	# the slice runs unchanged while the director surface is absent.
	if director != null and director.has_method("play_verdict_ritual"):
		director.play_verdict_ritual(target, committed)


func _play_repair_hint(target: Node3D) -> void:
	# RitualVfx additive surface: double amber blink marking the next valid
	# affordance after a refusal. Null target is allowed by the contract.
	if director != null and director.has_method("play_repair_hint"):
		director.play_repair_hint(target)
		audio_feedback.play_cue("repair_hint")


func _next_affordance_target() -> Node3D:
	# Delegates the ordering to GoldenPathLayout (single owner, shared with the
	# balance probe) and maps the target id onto the scene node the repair-hint
	# blink should mark.
	match str(GoldenPathLayout.next_affordance(machine.state, _met_mira)["target_id"]):
		"tide_marks":
			return handles.get("tide_marks") as Node3D
		"lamp_mount":
			return handles.get("lamp_mount") as Node3D
		"lens_pickup":
			return handles.get("lens_prop") as Node3D
		_:
			return _interactable("mira")


func _next_affordance_text() -> String:
	# Single source for "Next valid entry" strings — every refusal path routes through
	# _refusal_feedback; the ordering itself lives in GoldenPathLayout.
	return str(GoldenPathLayout.next_affordance(machine.state, _met_mira)["text"])


## Engine-mirror validator code -> the manuscript's state-relative predicate
## family (Table II: policy, precondition, reachability, knowledge, disclosure,
## quest stage). Surfaced diegetically so a hold names the gate that held it.
const GATE_BY_CODE := {
	"FORBIDDEN_DISCLOSURE": "DISCLOSURE",
	"STAGE_GATED_DISCLOSURE": "DISCLOSURE/QUEST STAGE",
	"MISSING_REQUIRED_OBJECT": "PRECONDITION",
	"QUEST_STAGE_PRECONDITION": "QUEST STAGE",
	"OBJECT_NOT_PRESENT": "REACHABILITY",
	"OBJECT_NOT_REACHABLE": "REACHABILITY",
	"NPC_DOES_NOT_KNOW_FACT": "KNOWLEDGE",
	"UNKNOWN_ACTOR": "POLICY",
	"UNKNOWN_OPERATION": "POLICY",
	"LENS_UNREACHABLE": "REACHABILITY",
	"WORLD_EVENT_ARGUMENTS_INVALID": "PRECONDITION",
	"WORLD_EVENT_LENS_MISSING": "PRECONDITION",
	"WORLD_EVENT_LENS_ALREADY_CARRIED": "PRECONDITION",
	"WORLD_EVENT_ALREADY_APPLIED": "PRECONDITION",
	"WORLD_EVENT_STAGE_PRECONDITION": "QUEST STAGE",
	"UNSUPPORTED_WORLD_EVENT": "POLICY",
}
var _holds_by_gate: Dictionary = {}


func gate_for_code(code: String) -> String:
	return str(GATE_BY_CODE.get(code, "POLICY"))


## The manuscript's six predicate families in Table II order. Every dashboard
## trace assigns each family exactly one explicit state; there is no default.
const GATE_FAMILIES := [
	"POLICY", "PRECONDITION", "REACHABILITY", "KNOWLEDGE", "DISCLOSURE", "QUEST STAGE"
]


static func gate_families_of(gate: String) -> Array:
	# A composite gate such as "DISCLOSURE/QUEST STAGE" names two families.
	var families: Array = []
	for part in gate.split("/"):
		var family := str(part).strip_edges()
		if family in GATE_FAMILIES and family not in families:
			families.append(family)
	return families


## D-073 per-node evaluation evidence for the observer dashboard (Aside deep
## research 2026-09-18: PROV plan-vs-activity split, JSON Schema "evaluated"
## semantics, no default state). `trace` is the EvaluationTrace mirror of the
## machine's ordered checks with each check mapped onto its predicate family;
## `skipped` lists the in-scope checks the engine never reached because an
## earlier check held the entry (`held_at`); `family_states` gives every one of
## the six families exactly one explicit state: "pass", "fail", "skipped", or
## "out_of_scope" (never consulted for this operation type). `consistent` is
## the mirror-vs-machine agreement flag: when false, no family state is
## reported at all (the dashboard renders "state missing", never a pass).
## Presentation-only; it never adds a check the machine did not run.
func dashboard_trace(trace: Array, plan: Array = [], consistent: bool = true) -> Dictionary:
	if not consistent:
		return {
			"checks": [],
			"evaluated_gates": [],
			"held_at": "",
			"short_circuit": false,
			"skipped": [],
			"out_of_scope": [],
			"family_states": {},
			"consistent": false,
		}
	var checks: Array = []
	var evaluated_gates: Array = []
	var evaluated_codes: Array = []
	var held_at := ""
	var family_states := {}
	for entry in trace:
		var code := str(entry["code"])
		var gate := gate_for_code(code)
		var outcome := str(entry["outcome"])
		checks.append({"code": code, "gate": gate, "outcome": outcome})
		evaluated_codes.append(code)
		if gate not in evaluated_gates:
			evaluated_gates.append(gate)
		if outcome == "fail" and held_at == "":
			held_at = code
		for family in gate_families_of(gate):
			# A family that both passed and failed a check in one call (only
			# the composite disclosure pair can) reports the failure.
			if outcome == "fail" or not family_states.has(family):
				family_states[family] = outcome
	var skipped: Array = []
	for code in plan:
		if str(code) in evaluated_codes:
			continue
		var gate := gate_for_code(str(code))
		skipped.append({"code": str(code), "gate": gate})
		for family in gate_families_of(gate):
			if not family_states.has(family):
				family_states[family] = "skipped"
	var out_of_scope: Array = []
	for family in GATE_FAMILIES:
		if not family_states.has(family):
			family_states[family] = "out_of_scope"
			out_of_scope.append(family)
	return {
		"checks": checks,
		"evaluated_gates": evaluated_gates,
		"held_at": held_at,
		"short_circuit": held_at != "",
		"skipped": skipped,
		"out_of_scope": out_of_scope,
		"family_states": family_states,
		"consistent": true,
	}


## Human-readable allowlist for newly established facts (contribution_delta's
## facts_added), keyed by canonical fact id. Unknown facts stay internal and
## collapse to the UI's generic "State recorded" copy, never a raw identifier.
const FACT_LABEL := {
	"signal_lens_acquired": "Signal lens secured",
	"signal_lens_installed": "Harbor signal restored",
	"lighthouse_hint_authorized": "Lead authorized",
	"tide_marks_hint": "Tide-marks lead recorded",
}

## Rule text a hold teaches, keyed by validator code (Table II predicate
## family). Neutral, non-alarming, and never names the hidden oracle (P-02);
## the gate label groups codes, this const gives each one its own testable
## sentence so repeated holds on one gate can still recall distinct rules.
const RULE_BY_CODE := {
	"FORBIDDEN_DISCLOSURE": "Some facts stay sealed for good; the ledger never records them.",
	"STAGE_GATED_DISCLOSURE": "A lead is disclosed only after its stage is reached.",
	"MISSING_REQUIRED_OBJECT": "Installation requires a carried signal lens.",
	"QUEST_STAGE_PRECONDITION": "This entry needs an earlier stage first.",
	"OBJECT_NOT_PRESENT": "Only a reachable object can be taken.",
	"OBJECT_NOT_REACHABLE": "Only a reachable object can be taken.",
	"NPC_DOES_NOT_KNOW_FACT": "A speaker can only disclose what they know.",
	"UNKNOWN_ACTOR": "The policy names who may act and how.",
	"UNKNOWN_OPERATION": "The policy names who may act and how.",
}

## Case-chain link order: HUD id -> the fact that fills it. Presentation
## only; the single source of truth stays the committed snapshot's facts.
const CASE_LINKS := [
	["LENS", "signal_lens_acquired"],
	["MOUNT", "signal_lens_installed"],
	["LEAD", "tide_marks_hint"],
]

## D-073 held-row third line, keyed by validator code: the inference the hold
## licenses (what the refusal tells the investigator about the world's rules).
## One ASCII sentence each; never names the hidden oracle or the sealed fact.
const INFERENCE_BY_CODE := {
	"FORBIDDEN_DISCLOSURE": "The keeper's secret is not an entry you can earn; the route is.",
	"STAGE_GATED_DISCLOSURE": "Mira can disclose the lead once the harbor signal is restored.",
	"MISSING_REQUIRED_OBJECT": "The mount takes a carried lens; recover it first.",
	"QUEST_STAGE_PRECONDITION": "This entry has a place in the chain; the chain is written in order.",
	"OBJECT_NOT_PRESENT": "Look for the lens where the harbor keeps its optics.",
	"OBJECT_NOT_REACHABLE": "Stand where the object can be reached before proposing to take it.",
	"NPC_DOES_NOT_KNOW_FACT": "Ask the person whose duty covers the fact.",
	"UNKNOWN_ACTOR": "Only named harbor roles may write to the ledger.",
	"UNKNOWN_OPERATION": "Only the ledger's known entry kinds can be proposed.",
}

## Case-file card copy per chain link: what the entry proves and why it
## matters for the open question (WHAT OPENED THE TIDE ROUTE?). The SEALED
## card is fixed copy and never names its fact.
const EVIDENCE_WHY := {
	"LENS": "Without the optic there is no signal to restore.",
	"MOUNT": "The restored signal is what lets the harbor authorize a lead.",
	"LEAD": "The authorized lead names where the tide opens the path.",
}
const SEALED_CARD_LABEL := "Sealed record"
const SEALED_CARD_WHY := "no answer can open it"

## Slot-assembly deduction (D-073): the chain the tide route rests on, in
## order. Options offered per slot are the committed contribution labels (the
## FACT_LABEL text) plus one distractor; validation compares the assembled
## sequence against this order and the committed facts, whole chain at once.
const DEDUCTION_CHAIN := ["LENS", "MOUNT", "LEAD"]
const DEDUCTION_RED_HERRING := "The keeper's silence"
const DEDUCTION_MAX_BUTTONS := 5

## Opt-in hint ladder copy per chain node (rung 1 = the open question, rung 2
## = place/person + compass, rung 3 = the next valid entry from
## GoldenPathLayout). View-local; text is static and keyed by node id.
const HINT_QUESTION_BY_NODE := {
	"ARRIVAL": "Who in this harbor can say why the channel is closed?",
	"LENS": "What does the harbor signal need before it can shine again?",
	"MOUNT": "Where does a signal lens belong so the harbor can see it?",
	"AUTHORIZE": "Now that the signal is restored, who is allowed to disclose the lead?",
	"LEAD": "Where does the authorized lead say the tide opens the path?",
}
const HINT_PLACE_BY_TARGET := {
	"mira": "Captain Mira at the end of the dock",
	"lens_pickup": "the lamp store past the west end of the dock",
	"lamp_mount": "the harbor signal mount on the northeast rail",
	"tide_marks": "the tide marks on the west breakwater",
}
const HINT_COMPASS := ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

var _contribution_log: Array[Dictionary] = []
var _rules_learned_by_gate: Dictionary = {}
## The EvaluationTrace mirror of the most recent machine call, already mapped by
## `dashboard_trace` (presentation-only; refreshed at every call site).
var _last_dashboard_trace: Dictionary = {}


## Fail-closed presentation boundary: only explicitly authored public labels
## may leave the canonical snapshot. Unknown or future fact ids stay internal.
static func player_visible_fact_labels(facts: Array) -> Array:
	var labels: Array = []
	for fact in facts:
		var fact_id := str(fact)
		if FACT_LABEL.has(fact_id):
			labels.append(str(FACT_LABEL[fact_id]))
	return labels


## Pure, presentation-only diff between two committed snapshots. Never reads
## or mutates `machine` — callers always pass result["prior_state"]/
## result["state"] (or hand-built probes in the engineering evaluation).
static func contribution_delta(prior: Dictionary, next: Dictionary) -> Dictionary:
	var prior_facts: Array = prior.get("facts", [])
	var next_facts: Array = next.get("facts", [])
	var facts_added: Array = []
	for fact in next_facts:
		if fact not in prior_facts:
			facts_added.append(fact)
	var prior_inventory: Array = prior.get("player", {}).get("inventory", [])
	var next_inventory: Array = next.get("player", {}).get("inventory", [])
	var inventory_added: Array = []
	for item in next_inventory:
		if item not in prior_inventory:
			inventory_added.append(item)
	var inventory_removed: Array = []
	for item in prior_inventory:
		if item not in next_inventory:
			inventory_removed.append(item)
	var disclosed_added: Array = []
	var next_npcs: Dictionary = next.get("npcs", {})
	var prior_npcs: Dictionary = prior.get("npcs", {})
	for actor_id in next_npcs.keys():
		var next_disclosed: Array = next_npcs[actor_id].get("disclosed", [])
		var prior_disclosed: Array = prior_npcs.get(actor_id, {}).get("disclosed", [])
		for fact in next_disclosed:
			if fact not in prior_disclosed:
				disclosed_added.append(fact)
	return {
		"stage_from": int(prior.get("quest", {}).get("stage", 0)),
		"stage_to": int(next.get("quest", {}).get("stage", 0)),
		"facts_added": CanonicalState.sorted_unique(facts_added),
		"inventory_added": CanonicalState.sorted_unique(inventory_added),
		"inventory_removed": CanonicalState.sorted_unique(inventory_removed),
		"disclosed_added": CanonicalState.sorted_unique(disclosed_added),
	}


func _case_chain_from_state(state: Dictionary) -> Dictionary:
	# Mirrors CASE_LINKS against the committed snapshot's facts. Presentation
	# only; called fresh every time so it can never drift from machine.state.
	var facts: Array = state.get("facts", [])
	var links: Array = []
	var filled := 0
	for link in CASE_LINKS:
		var is_filled: bool = str(link[1]) in facts
		if is_filled:
			filled += 1
		links.append({"id": str(link[0]), "filled": is_filled})
	return {"links": links, "filled": filled, "total": CASE_LINKS.size()}


func _ledger_last_contribution() -> void:
	# Shared by every accepted proposal right after its ledger_commit line:
	# the CONTRIBUTION clause reads the entry _propose just appended, the
	# chain reads the snapshot the commit produced, and UNLOCKED names the
	# affordance the commit opened (computed after the commit on purpose).
	var chain := _case_chain_from_state(machine.state)
	var entry: Dictionary = _contribution_log[-1]
	ui.ledger_contribution(
		commit_count, entry["labels"], entry["stage_from"], entry["stage_to"],
		chain["filled"], chain["total"]
	)
	ui.ledger_unlocked(_next_affordance_text())


func _record_hold(gate: String) -> void:
	_holds_by_gate[gate] = int(_holds_by_gate.get(gate, 0)) + 1


func _correction_code_for_hold(codes: Array) -> String:
	for code in codes:
		match str(code):
			"FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE":
				return "ASK_AUTHORIZED_LEAD"
			"MISSING_REQUIRED_OBJECT":
				return "RECOVER_SIGNAL_LENS"
			"QUEST_STAGE_PRECONDITION":
				return "FOLLOW_COMMITTED_SEQUENCE"
			"OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE":
				return "MOVE_TO_REACHABLE_AFFORDANCE"
	return "FOLLOW_NEXT_AFFORDANCE"


func _refusal_feedback(codes: Array) -> void:
	# Neutral reason + one world-flavor clause + the concrete next valid entry.
	# Hidden oracle labels never surface; the flavor stays non-alarming (P-02) —
	# the ledger defers, it never punishes. Each hold also names the predicate
	# family that held it so the in-game ledger mirrors the paper's commit gate.
	var next_affordance := _next_affordance_text()
	var held_hash := machine.state_hash()
	var next_affordance_target := str(GoldenPathLayout.next_affordance(machine.state, _met_mira).get("target_id", ""))
	var hold_gates: Array = []
	for code in codes:
		hold_gates.append(gate_for_code(str(code)))
	_emit_dashboard("hold", {
		"codes": codes.duplicate(),
		"gates": hold_gates,
		"next_affordance": next_affordance,
		# Every call site refreshes `_last_dashboard_trace` right after the
		# machine call that produced these codes, so it is the evaluation
		# evidence for this hold (fail-closed when the mirror disagrees).
		"trace": _last_dashboard_trace,
	}.merged(_dashboard_state_summary()))
	_record_observation_receipt(
		"hold_emitted",
		"HOLD",
		held_hash,
		held_hash,
		{
			"reason_codes": CanonicalState.sorted_unique(codes),
			"gate_codes": CanonicalState.sorted_unique(hold_gates),
			"correction_code": _correction_code_for_hold(codes),
			"next_affordance_target": next_affordance_target,
		},
	)
	for code in codes:
		var gate := gate_for_code(str(code))
		_record_hold(gate)
		match code:
			"FORBIDDEN_DISCLOSURE":
				# Canonical early-secret fallback (safe_fallback.text_en).
				ui.ledger_line("dialogue", scenario["safe_fallback"]["text_en"])
				ui.ledger_refusal("This request cannot be answered yet. The ledger defers it.", next_affordance, gate)
			"STAGE_GATED_DISCLOSURE":
				ui.ledger_line("dialogue", "Not yet. There is an order to these things.")
				ui.ledger_refusal("Disclosure conditions are not met. The ledger keeps the sequence.", next_affordance, gate)
			"MISSING_REQUIRED_OBJECT":
				ui.ledger_refusal("There is no lens to install. The ledger will not record empty hands.", next_affordance, gate)
			"QUEST_STAGE_PRECONDITION":
				ui.ledger_refusal("The entry is not ready. Its tide has not come in.", next_affordance, gate)
			"OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE":
				ui.ledger_refusal("It cannot be taken from here. What cannot be reached stays outside the ledger.", next_affordance, gate)
			_:
				ui.ledger_refusal("The entry was held. The ledger defers it.", next_affordance, gate)
		# W-005 rule-teaching companion (Aside search-feedback 2026-09-02
		# patterns 2/E): the first hold on a gate teaches one testable rule;
		# later holds on the same gate recall it instead of repeating verbatim.
		var rule_text := str(RULE_BY_CODE.get(str(code), "The policy held this entry."))
		var first_time := not _rules_learned_by_gate.has(gate)
		if first_time:
			_rules_learned_by_gate[gate] = rule_text
		ui.ledger_rule(gate, rule_text, first_time, int(_holds_by_gate.get(gate, 0)) - 1)
		# D-073 third line of the held row: PROPOSAL -> RULE -> WHAT THIS TELLS
		# YOU. The inference a hold licenses (XAG 115: the error AND the method
		# to correct it). Authored per code; remembered per gate for the receipt.
		var inference_text := str(INFERENCE_BY_CODE.get(str(code), "The ledger keeps its order; the next valid entry names the way."))
		if not _inference_by_gate.has(gate):
			_inference_by_gate[gate] = inference_text
		ui.ledger_inference(inference_text)
	var rules_learned_sorted: Array = _rules_learned_by_gate.keys()
	rules_learned_sorted.sort()
	ui.set_case_chain(_case_chain_from_state(machine.state), rules_learned_sorted)
	_on_hold_presentation()
	# RitualVfx repair-hint blink marks the same next-valid target in-world.
	_play_repair_hint(_next_affordance_target())


func _holds_by_gate_text() -> String:
	# Deterministic order so the end card and any capture stay stable.
	var keys: Array = _holds_by_gate.keys()
	keys.sort()
	var parts: Array = []
	for key in keys:
		parts.append("%s %d" % [key, int(_holds_by_gate[key])])
	return " | ".join(parts) if not parts.is_empty() else "none"


func _npc_gate_player_action(operation: String) -> bool:
	if npc_client == null:
		return true
	if _npc_waiting_action.is_empty() or str(_npc_waiting_action.get("operation", "")) != operation:
		return true
	var waiting := _npc_waiting_action.duplicate(true)
	var action_id := str(waiting.get("action_id", ""))
	var context: Dictionary = waiting.get("context", {}) if waiting.get("context", {}) is Dictionary else {}
	var binding_errors: Array = npc_client.validate_action_context(context, action_id, operation, npc_state_ref())
	if binding_errors.is_empty():
		return true
	# This is the last check before _propose's synchronous canonical writer. A
	# stale directive is tombstoned; it must never be re-correlated to a later
	# ordinary player interaction.
	var feedback := "Player action held: %s" % ",".join(binding_errors)
	if npc_client != null:
		npc_client.submit_action_result(context, action_id, operation, "STALE", feedback)
	_npc_waiting_action.clear()
	ui.set_npc_status("NPC DIRECTIVE EXPIRED | No state changed.")
	ui.toast("NPC DIRECTIVE EXPIRED | No state changed.")
	return false


func _propose_acquire() -> void:
	if not _npc_gate_player_action("acquire_object"):
		return
	# SL-GDD-T1 Q1: collect the reachable signal lens.
	var result := _propose(
		"acquire_object",
		{"object_id": "signal_lens"},
		"Recover the signal lens",
		handles.get("lens_prop") as Node3D,
	)
	if result["accepted"]:
		# P-B02: brass-outlined acquisition after the commit. The bright pickup
		# chime rides above the commit rise so "got the object" reads distinctly
		# from "the ledger accepted it".
		audio_feedback.play_cue("pickup")
		player.play_gesture(&"Collect")
		ui.ledger_commit(commit_count, "Signal lens secured. Retrieval entry validated.")
		_ledger_last_contribution()
		ui.ledger_line("narration", "The brass rim gleams cold against your fingers. The harbor signal mount comes to mind.")
		director.set_tension_stage(1)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()
	_npc_record_player_action("acquire_object", result)


func _propose_install() -> void:
	if not _npc_gate_player_action("install_lens"):
		return
	# SL-GDD-T1 Q2: install requires the lens and quest stage >= 1.
	var result := _propose(
		"install_lens",
		{"object_id": "signal_lens"},
		"Install the lens in the harbor signal mount",
		handles.get("lamp_mount") as Node3D,
	)
	if result["accepted"]:
		ui.ledger_commit(commit_count, "Signal lens installed. An authorized lead is now available.")
		_ledger_last_contribution()
		ui.ledger_line("narration", "A low, warm light wakes in the mount. The tower remains dark, but the channel's story opens.")
		director.set_tension_stage(2)
		director.play_commit_glow(handles["lamp_mount"], "MountLight", 2.4)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()
	_npc_record_player_action("install_lens", result)


## ----------------------------------------------------------------- dialogue

func _open_mira_dialogue() -> void:
	_dialogue_open = true
	_npc_waiting_action.clear()
	var resume_interpretation := npc_client.has_accepted_interpretation()
	npc_client.begin_dialogue()
	if resume_interpretation:
		npc_client.request_observation(npc_public_observation())
	ui.show_npc_input(true)
	_emit_dashboard("dialogue", {"phase": "open", "npc": "captain_mira"})
	var first_meeting := not _met_mira
	if not _met_mira:
		# Presentation-only pacing flag: after the first meeting the objective
		# beacon stops pointing at Mira and follows the committed snapshot.
		_met_mira = true
		_sync_presentation()
	ui.hide_prompt()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.set_cursor_captured(false)
	audio_feedback.play_cue("dialogue")
	player.play_gesture(&"Speak")
	director.set_guide_trail_suppressed(true)
	ui.set_portrait_visible(true, "CAPTAIN MIRA | HARBOR WATCH")
	# W-003: duty-bounded operational knowledge, no keeper authority. Greeting
	# beats are presentation-only and branch on the committed snapshot; every
	# choice id and flow below stays untouched.
	var state: Dictionary = machine.state
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	if first_meeting:
		# Beat (a) — her account of the storm night and the sealing (W-001/W-002):
		# operational facts only; the WHY stays outside her authority (F-H01).
		ui.ledger_line("dialogue", "Thank you for saving the dock. If that fire had spread, the ledger would have gone under with it.")
		ui.ledger_line("dialogue", "The tower has been dark for three days. Its light died in the heart of the storm. We signaled twice and received only darkness. The ledger has one word left: sealed.")
		ui.ledger_line("dialogue", "No one enters the channel tonight. Harbor watch reports only what it can verify. That is how this harbor survived.")
	elif hint_known:
		# Beat (c) — quiet epilogue: the harbor survives on valid entries only.
		ui.ledger_line("dialogue", "Read the ledger. Every entry that remains tonight is valid. This harbor survived by stacking nights like this one.")
	elif installed:
		# Beat (b) — guarded hope after the lens install: she almost writes hope
		# into the ledger, but the ledger only takes what is verified.
		ui.ledger_line("dialogue", "The mount's light reaches the channel entrance now. I nearly wrote hope. The ledger accepts only what we can verify, so not yet.")
	else:
		ui.ledger_line("dialogue", "The tide will not wait for us. With that tower dark, no one enters the channel tonight.")
	_show_mira_choices()


func _show_mira_choices() -> void:
	var state: Dictionary = machine.state
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	var choices: Array = []
	if not hint_known:
		choices.append({"id": "ask_lighthouse", "text": "What happened to the lighthouse?"})
		choices.append({"id": "ask_secret", "text": "The keeper is hiding something. Tell me."})
		choices.append({"id": "ask_tide", "text": "What do the tide marks mean?"})
	else:
		choices.append({"id": "ask_after", "text": "Where do I go now?"})
	choices.append({"id": "leave", "text": "Step away"})
	ui.show_choices(choices)


func _on_choice(choice_id: String) -> void:
	if not _dialogue_open:
		return
	if _deduction_open:
		# D-073 slot assembly: not a Mira choice and never a machine proposal.
		_on_deduction_choice(choice_id)
		return
	_begin_input_feedback_probe("dialogue-choice:" + choice_id)
	_emit_dashboard("dialogue", {"phase": "choice", "npc": "captain_mira", "choice_id": choice_id})
	match choice_id:
		"ask_lighthouse":
			# W-002: operational fact, already disclosed.
			ui.ledger_line("dialogue", "The light died three days ago. The door may be barred from inside. There has been no answer. That is all we know.")
			_complete_input_feedback_probe("mira-dialogue-ledger-line")
			_show_mira_choices()
		"ask_secret":
			# B-006: the one intended early secret request (keeper_betrayal stays sealed).
			_remember_held_text("Request disclosure of what the keeper hides")
			var mirror_checks: Array = EvaluationTraceScript.disclosure_checks(
				scenario, machine.state, ["keeper_betrayal"]
			)
			var codes: Array = machine.validate_disclosure(["keeper_betrayal"])
			_last_dashboard_trace = dashboard_trace(
				mirror_checks, EvaluationTraceScript.plan_for("validate_disclosure"),
				EvaluationTraceScript.consistent(mirror_checks, codes)
			)
			refusal_count += 1
			ui.flash("refusal")
			audio_feedback.play_cue("refusal")
			director.play_refusal_pulse()
			_play_verdict_ritual(_interactable("mira"), false)
			director.set_tension_stage(2)
			_refusal_feedback(codes)
			# Keep the compact status line's HOLDS count current after a
			# dialogue-path hold (the proposal paths already resync).
			_sync_presentation()
			_complete_input_feedback_probe("refusal-ledger-line")
			_show_mira_choices()
		"ask_tide":
			_propose_tide_hint()
		"ask_after":
			ui.ledger_line("dialogue", "Follow the low-tide marks. The next tide will open the path. The tower can wait until then.")
			_complete_input_feedback_probe("mira-dialogue-ledger-line")
			_show_mira_choices()
		"leave":
			_close_dialogue()
			_complete_input_feedback_probe("dialogue-close")
		_:
			_pending_input_feedback.clear()


func _propose_tide_hint() -> Dictionary:
	# SL-GDD-T1 Q2-HINT: stage >= 2 and Mira knows the fact.
	var result := _propose(
		"reveal_hint",
		{"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
		"Request the tide-marks lead from Captain Mira",
		_interactable("mira"),
	)
	if result["accepted"]:
		# P-B05: one ledger link turns solid; restrained bell, signal glow.
		ui.ledger_line("dialogue", "Good. The lens is in place, so I can tell you. At the tide marks on the west breakwater, the path appears when the water falls below the third mark.")
		ui.ledger_commit(commit_count, "Tide-marks lead disclosed. Authorization confirmed; entry valid.")
		_ledger_last_contribution()
		audio_feedback.play_cue("hint")
		director.set_tension_stage(3)
		var world: Node3D = handles["world"]
		director.play_commit_glow(world.get_node("TideMarks"), "TideGlow", 1.6)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()
	_show_mira_choices()
	return result


func _close_dialogue() -> void:
	_emit_dashboard("dialogue", {"phase": "close", "npc": "captain_mira"})
	_dialogue_open = false
	_npc_waiting_action.clear()
	if npc_client != null:
		npc_client.invalidate_pending("dialogue_closed")
	ui.show_npc_input(false)
	director.set_guide_trail_suppressed(false)
	ui.clear_choices()
	ui.set_portrait_visible(false)
	ui.set_contextual_panel_visible(false)
	if not _smoke_mode and not _evaluate_mode:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)
func _on_npc_capability_submitted(value: String) -> void:
	var capability := value.strip_edges()
	if capability.is_empty() or capability.length() > 512 or capability.find("\r") != -1 or capability.find("\n") != -1:
		ui.set_npc_status("NPC BACKEND | CAPABILITY INVALID")
		return
	npc_client.set_capability(capability)
	ui.set_npc_status("NPC BACKEND | CAPABILITY READY | MEMORY ONLY")


func _on_npc_text_submitted(text: String) -> void:
	if not _dialogue_open or npc_client == null:
		return
	_npc_waiting_action.clear()
	ui.set_npc_busy(true)
	if not npc_client.request_utterance(text, npc_public_observation()):
		ui.set_npc_busy(false)


func _on_npc_cancel_requested() -> void:
	_npc_waiting_action.clear()
	if npc_client != null:
		npc_client.invalidate_pending("cancelled")
	ui.set_npc_busy(false)
	ui.toast("NPC REQUEST CANCELLED | No state changed.")


func _on_npc_decision(envelope: Dictionary, context: Dictionary) -> void:
	_npc_engineering_events.append({
		"kind": "decision",
		"request_id": str(envelope.get("request_id", "")),
		"event_id": str(envelope.get("event_id", "")),
		"sequence": int(envelope.get("sequence", 0)),
		"state_ref": envelope.get("state_ref", {}),
		"status": str(envelope.get("body", {}).get("status", "")),
	})

	ui.set_npc_busy(false)
	var accepted := npc_client.accept_decision(envelope, context, npc_state_ref())
	if not bool(accepted.get("accepted", false)):
		_npc_waiting_action.clear()
		ui.set_npc_status("BACKEND CODEX | MODE LIVE | PLAN HELD")
		ui.toast("NPC PLAN HELD | Freshness or binding check failed.")
		return


func _on_npc_directive(code: String, payload: Dictionary) -> void:
	match code:
		"NPC_PLAYER_ACTION":
			_npc_waiting_action = payload.duplicate(true)
			ui.set_npc_status("NPC DIRECTIVE | PLAYER ACTION REQUIRED | %s" % str(payload.get("operation", "")).to_upper())
			ui.toast("PLAYER ACTION REQUIRED | Use the world interaction.")
		"NPC_REVEAL_HINT":
			_npc_commit_reveal(str(payload.get("action_id", "")), payload.get("context", {}))
		"NPC_DIALOGUE":
			_npc_waiting_action.clear()
			ui.set_npc_status("NPC DIRECTIVE | DIALOGUE | %s" % str(payload.get("operation", "")).to_upper())
		"NPC_NO_ROUTE":
			_npc_waiting_action.clear()
			ui.set_npc_status("BACKEND CODEX | MODE LIVE | NO ROUTE")
		"NPC_GOAL_REACHED":
			_npc_waiting_action.clear()
			ui.set_npc_status("NPC FIXED GOAL REACHED | TIDE LEAD")
		"NPC_ERROR":
			_npc_waiting_action.clear()
			ui.set_npc_status("BACKEND CODEX | MODE LIVE | ERROR")


func _on_npc_protocol_error(reason: String) -> void:
	_npc_waiting_action.clear()
	_npc_engineering_errors.append(reason)

	ui.set_npc_busy(false)
	ui.set_npc_status("BACKEND CODEX | MODE LIVE | UNAVAILABLE")
	if not _evaluate_mode and not _npc_evaluate_mode and not _npc_replay_mode:
		ui.toast("NPC SERVICE UNAVAILABLE | %s" % reason)


func _npc_record_player_action(operation: String, result: Dictionary) -> void:
	if _npc_waiting_action.is_empty() or str(_npc_waiting_action.get("operation", "")) != operation:
		return
	var action_id := str(_npc_waiting_action.get("action_id", ""))
	var context: Dictionary = _npc_waiting_action.get("context", {})
	_npc_waiting_action.clear()
	var status := "APPLIED" if bool(result.get("accepted", false)) else "REJECTED"
	var feedback := "Player action committed." if status == "APPLIED" else "Player action held: %s" % ",".join(result.get("codes", []))
	npc_client.submit_action_result(context, action_id, operation, status, feedback)


func _npc_commit_reveal(action_id: String, context: Dictionary) -> void:
	if action_id.is_empty() or context.is_empty():
		return
	if _npc_action_results.has(action_id):
		npc_client.submit_action_result(context, action_id, "reveal_hint", "DUPLICATE", "Duplicate action ignored.")
		return
	_npc_action_results[action_id] = {"accepted": false, "codes": ["IN_FLIGHT"]}
	var expected_revision := int(context.get("expected_revision", -1))
	var expected_hash := str(context.get("expected_sha256", ""))
	var current_ref := npc_state_ref()
	var gate_ok: bool = _dialogue_open \
		and int(current_ref["revision"]) == expected_revision \
		and str(current_ref["sha256"]) == expected_hash \
		and str(context.get("policy_hash", "")) == npc_policy_hash() \
		and str(context.get("config_hash", "")) == npc_config_hash()
	if not gate_ok:
		npc_client.submit_action_result(context, action_id, "reveal_hint", "STALE", "Freshness gate rejected the reveal proposal.")
		return
	# No await is permitted between this gate and the existing hard writer.
	var result := _propose_tide_hint()
	_npc_action_results[action_id] = {"accepted": bool(result.get("accepted", false)), "codes": result.get("codes", []), "mutated": bool(result.get("mutated", false))}
	var status := "APPLIED" if bool(result.get("accepted", false)) else "REJECTED"
	var feedback := "Tide lead committed." if status == "APPLIED" else "Tide lead held: %s" % ",".join(result.get("codes", []))
	npc_client.submit_action_result(context, action_id, "reveal_hint", status, feedback)

func _on_npc_result_recorded(envelope: Dictionary, context: Dictionary) -> void:
	_npc_engineering_events.append({
		"kind": "ack",
		"request_id": str(envelope.get("request_id", "")),
		"event_id": str(envelope.get("event_id", "")),
		"sequence": int(envelope.get("sequence", 0)),
		"status": str(envelope.get("body", {}).get("status", "")),
		"action_id": str(context.get("action_id", "")),
	})
	# The result acknowledgement ends the action request. Ask for the next
	# directive through the observation-only path; the service reuses the prior
	# typed intent and must not invoke the model again.
	if _dialogue_open and npc_client != null:
		npc_client.request_observation(npc_public_observation())

## -------------------------------------------------------------- persistence

func _save_game() -> void:
	var payload := {
		"state": machine.state,
		"state_sha256": machine.state_hash(),
	}
	var handle := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	handle.store_string(JSON.stringify(payload, "  "))
	handle.close()
	ui.toast("SAVED | State hash " + machine.state_hash().substr(0, 12) + "...")


func _exit_tree() -> void:
	if npc_client != null and is_instance_valid(npc_client):
		npc_client.invalidate_pending("exit")


func _load_game() -> void:
	if npc_client != null:
		npc_client.invalidate_pending("load")
	_npc_waiting_action.clear()
	if not FileAccess.file_exists(SAVE_PATH):
		ui.toast("NO SAVE FILE FOUND")
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if not (parsed is Dictionary) or not parsed.has("state") or not parsed.has("state_sha256"):
		ui.toast("LOAD HELD | The save file could not be read.")
		return
	if machine.load_state_if_hash_matches(parsed["state"], parsed["state_sha256"]):
		ui.toast("LOADED | Integrity check passed.")
		_sync_presentation()
	else:
		# GDI-02: a corrupt save must never become authoritative.
		ui.toast("LOAD HELD | Save hash mismatch; current state preserved.")


## ------------------------------------------------------------- presentation

func _sync_presentation() -> void:
	# Presentation reads the committed snapshot; it never writes back.
	var state: Dictionary = machine.state
	var lens_in_store: bool = state["world"]["object_locations"].has("signal_lens")
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	var world: Node3D = handles["world"]

	(handles["lens_prop"] as Node3D).visible = lens_in_store
	# Hero-item continuity: once the optic leaves the store the vacated cradle
	# shows a dim retaining ring, so returning players read the change.
	var cradle_marker := world.get_meta(&"lens_cradle_marker", null) as MeshInstance3D
	if cradle_marker != null:
		cradle_marker.visible = not lens_in_store
	ui.set_lens_held(
		"signal_lens" in state["player"]["inventory"]
		and "signal_lens_installed" not in state["facts"]
	)
	var lens_interact := _interactable("lens_pickup")
	if lens_interact != null:
		lens_interact.enabled = lens_in_store
	var mount_light := (handles["lamp_mount"] as Node3D).get_node("MountLight") as OmniLight3D
	if installed and mount_light.light_energy <= 0.0:
		mount_light.light_energy = 2.4
	(handles["tide_marks"] as Node3D).visible = hint_known
	var tide_interact := _interactable("tide_marks")
	if tide_interact != null:
		tide_interact.enabled = hint_known
	var mount_interact := _interactable("lamp_mount")
	if mount_interact != null:
		mount_interact.enabled = not installed
	_update_objective_beacon(lens_in_store, installed, hint_known)
	director.set_tide_lead_known(hint_known)
	director.refresh_guide_trail()

	# Objective copy audit: bureaucratic-poetic but concrete — each line names
	# WHO/WHERE and WHY NOW; the beacon marks the same target in-world.
	var objective := "Speak with Captain Mira at the end of the dock | She knows why the channel is closed"
	var objective_code := "MIRA_AUTHORIZATION"
	var next_affordance_target := "mira"
	var phase := "ARRIVAL"
	if _met_mira:
		objective = "Recover the signal lens from the lamp store | The channel cannot open without a signal"
		objective_code = "LENS_RECOVERY"
		next_affordance_target = "lens_pickup"
		phase = "LENS_RECOVERY"
	if hint_known:
		objective = "Inspect the tide marks on the west breakwater | Read when low tide opens the path"
		objective_code = "TIDE_MARKS"
		next_affordance_target = "tide_marks"
		phase = "TRACE_LOGGED"
	elif installed:
		objective = "Return to Captain Mira for the authorized lead | The harbor signal is restored"
		objective_code = "RETURN_TO_MIRA"
		next_affordance_target = "mira"
		phase = "SIGNAL_RESTORED"
	elif not lens_in_store:
		objective = "Install the lens at the northeast harbor mount | Restore the harbor signal"
		objective_code = "LENS_MOUNT"
		next_affordance_target = "lamp_mount"
		phase = "LENS_SECURED"
	var objective_hash := machine.state_hash()
	if objective_code != _last_objective_receipt_code:
		_record_observation_receipt(
			"objective_rendered",
			phase,
			objective_hash,
			objective_hash,
			{
				"objective_code": objective_code,
				"next_affordance_target": next_affordance_target,
			},
		)
		_last_objective_receipt_code = objective_code
	var inventory: Array = state["player"]["inventory"]
	var exploration_progress := 3 if hint_known else int(state["quest"]["stage"])
	# One compact status line (D-073: the case chain N/3 is the only progress
	# number on screen; these are receipts, not a second counter).
	var status := "STAGE %d | %s | INVENTORY: %s | ENTRIES %d | HOLDS %d" % [
		int(state["quest"]["stage"]),
		phase,
		"SIGNAL LENS" if "signal_lens" in inventory else "EMPTY",
		commit_count,
		refusal_count,
	]
	ui.set_status(objective, status)
	ui.set_progress(exploration_progress, 3, phase)
	var rules_learned_sorted: Array = _rules_learned_by_gate.keys()
	rules_learned_sorted.sort()
	ui.set_case_chain(_case_chain_from_state(state), rules_learned_sorted)
	# D-073 detective-loop surfaces (presentation-only, derived here so they
	# can never drift from the committed snapshot).
	_ensure_presentation_hooks()
	_refresh_hint_ladder()
	if ui.is_evidence_board_open():
		_show_case_file()
	if (
		"signal_lens" in inventory
		and not installed
		and _play_started
		and not _smoke_mode
		and not _evaluate_mode
	):
		_show_coach_card_once("investigate")


func _build_objective_beacon() -> Node3D:
	# Usability affordance: one soft amber column marks the current objective
	# target so the next valid action is always discoverable without opening a
	# menu. Presentation only; it follows the committed snapshot.
	# Read: a tapered additive column (narrower at top) that dissolves upward
	# well below the tower silhouette line, plus a small ground-contact ring —
	# unmistakably a UI marker, never a lighthouse beam (D-030). The director
	# breathes the shader's pulse 0.55↔0.8 over 2.5 s (static mid-alpha under
	# reduced motion).
	var beacon := Node3D.new()
	beacon.name = "ObjectiveBeacon"
	var column := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = 0.08
	mesh.bottom_radius = 0.34
	mesh.height = 4.6
	mesh.radial_segments = 24
	mesh.rings = 1
	mesh.cap_top = false
	mesh.cap_bottom = false
	column.mesh = mesh
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode blend_add, depth_draw_never, cull_back, unshaded, shadows_disabled;
// Soft additive objective marker: brightest at the ground, dissolving to
// nothing by ~82% height, with a view-facing softness so the silhouette
// edges never read as hard geometry. `pulse` is the director-driven
// breathing alpha (0.55↔0.8, static 0.675 under reduced motion).
// Height comes from the local VERTEX (mesh spans ±half_height), NOT UV.y:
// CylinderMesh packs its side into the V∈[0,0.5] half of the UV atlas, so a
// UV-based gradient would collapse into the faded band and vanish.
uniform vec3 tint : source_color = vec3(0.95, 0.72, 0.29);
uniform float pulse : hint_range(0.0, 1.0) = 0.675;
uniform float half_height = 2.3;
varying float column_height;
void vertex() {
	column_height = clamp(VERTEX.y / (2.0 * half_height) + 0.5, 0.0, 1.0);
}
void fragment() {
	float body = 1.0 - smoothstep(0.10, 0.82, column_height);
	float ground_kiss = 1.0 - smoothstep(0.0, 0.07, column_height);
	float facing = abs(dot(normalize(NORMAL), normalize(VIEW)));
	float softness = mix(0.55, 1.0, facing * facing);
	ALBEDO = tint;
	ALPHA = (body * 0.85 + ground_kiss * 0.35) * softness * pulse;
}
"""
	var material := ShaderMaterial.new()
	material.shader = shader
	material.set_shader_parameter(
		&"tint", SealedLighthouseWorldBuilder.PALETTE.signal_amber
	)
	column.material_override = material
	column.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	column.position = Vector3(0.0, 2.3, 0.0)
	beacon.add_child(column)
	# Ground-contact glow ring: anchors the column to the target's floor so the
	# marker reads "stand here", not "light from the sky". Static by design.
	var contact_ring := MeshInstance3D.new()
	contact_ring.name = "ContactRing"
	var ring_mesh := TorusMesh.new()
	ring_mesh.inner_radius = 0.34
	ring_mesh.outer_radius = 0.5
	ring_mesh.rings = 24
	ring_mesh.ring_segments = 6
	contact_ring.mesh = ring_mesh
	contact_ring.material_override = SealedLighthouseWorldBuilder.emissive_material(
		SealedLighthouseWorldBuilder.PALETTE.signal_amber, 0.55, 0.3
	)
	contact_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	contact_ring.position = Vector3(0.0, 0.05, 0.0)
	beacon.add_child(contact_ring)
	beacon.set_meta(&"beacon_material", material)
	(handles["world"] as Node3D).add_child(beacon)
	return beacon


func _update_objective_beacon(lens_in_store: bool, installed: bool, hint_known: bool) -> void:
	# The beacon always marks the CURRENT golden-path target and advances with
	# each commit (or the met-Mira presentation flag): Mira → lens → mount →
	# Mira → tide marks. Coordinates mirror _spawn_interactables.
	if _objective_beacon == null:
		return
	var target := Vector3(3.0, 0.0, 11.0)  # Mira: first meeting, and post-install question.
	if hint_known:
		target = Vector3(-8.5, 0.0, 15.5)  # tide marks finale
	elif installed:
		target = Vector3(3.0, 0.0, 11.0)  # back to Mira for the authorized hint
	elif not lens_in_store:
		target = Vector3(7.0, 0.0, 13.5)  # lens held → mount
	elif _met_mira:
		target = Vector3(-11.0, 0.0, 1.0)  # lens still in store
	_objective_beacon.position = target


## ------------------------------------------------ D-073 detective loop (view)

func _ensure_presentation_hooks() -> void:
	# Lazily wired on the first _sync_presentation (this controller does not
	# own _ready): the HUD handle buttons, the hint ladder key/button, the
	# coach-card dismissal and the 0.5 s compass refresh for rung 2.
	if _presentation_hooks_ready or ui == null:
		return
	_presentation_hooks_ready = true
	ui.tutorial_requested.connect(func() -> void:
		if not _dialogue_open and not episode_over and _play_started:
			if ui.is_tutorial_open():
				ui.hide_tutorial()
			else:
				_open_tutorial(true)
	)
	ui.case_file_requested.connect(_toggle_case_file)
	ui.hint_requested.connect(_advance_hint_ladder)
	ui.coach_card_dismissed.connect(_on_coach_card_dismissed)
	_hint_timer = Timer.new()
	_hint_timer.wait_time = 0.5
	_hint_timer.one_shot = false
	_hint_timer.autostart = true
	_hint_timer.timeout.connect(func() -> void:
		if _hint_rung >= 2 and not episode_over:
			_refresh_hint_ladder()
	)
	add_child(_hint_timer)
	ui.set_hint_ladder(0, [])


func _on_commit_presentation(_proposal_text: String) -> void:
	# After every accepted proposal: the case-file handle gets an unread pip
	# (no timed auto-open), the hint ladder resets to rung 0, and the first
	# commit surfaces the "how the ledger works" coach card once.
	ui.mark_case_file_unread()
	_set_hint_rung(0)
	if _play_started:
		_show_coach_card_once("ledger_intro")


func _on_hold_presentation() -> void:
	# After every hold: the first one surfaces the "what a hold means" coach
	# card once. The held row itself is permanent (never faded or collapsed).
	if _play_started:
		_show_coach_card_once("hold_intro")


func _remember_held_text(text: String) -> void:
	# Held proposal texts feed the deduction's distractor pool (presentation
	# only; they are the ledger's own words, never a fact id).
	if text != "" and text not in _held_texts:
		_held_texts.append(text)


func _show_coach_card_once(card_id: String) -> void:
	# One card at a time (never stack hints): a card requested while another
	# is open waits in a view-local queue and appears when that one is
	# dismissed by the player. Each card id shows at most once per session.
	if card_id in _coach_cards_shown or ui.is_tutorial_open() or episode_over:
		return
	_coach_cards_shown.append(card_id)
	if ui.is_coach_card_open():
		_coach_cards_pending.append(card_id)
		return
	_present_coach_card(card_id)


func _present_coach_card(card_id: String) -> void:
	ui.show_coach_card(card_id)
	_emit_dashboard("coach_card", {"card_id": card_id, "phase": "shown"})
	if not _dialogue_open:
		# The [OK] button needs a pointer; Esc also dismisses. Dialogue already
		# has the pointer free.
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.set_cursor_captured(false)


func _on_coach_card_dismissed(card_id: String) -> void:
	_emit_dashboard("coach_card", {"card_id": card_id, "phase": "dismissed"})
	if not _coach_cards_pending.is_empty() and not episode_over and not ui.is_tutorial_open():
		_present_coach_card(str(_coach_cards_pending.pop_front()))
		return
	if _play_started and not _dialogue_open and not episode_over and not ui.is_tutorial_open():
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)


func _first_focus_toast(interaction_id: String) -> void:
	# First-time contextual coach toast per interactable (one interaction per
	# card; never repeats). Presentation-only set.
	if interaction_id in _focus_toasts_shown or _dialogue_open or episode_over:
		return
	var hints := {
		"mira": "[E] INSPECT | Speak with Captain Mira. She reports only what harbor watch can verify.",
		"lens_pickup": "[E] INSPECT | Propose recovering the signal lens. The ledger validates the entry.",
		"lamp_mount": "[E] INSPECT | Propose installing the lens. The mount takes a carried lens only.",
		"lighthouse_view": "[E] INSPECT | Observe the sealed tower. It stays dark; nobody enters tonight.",
		"tide_marks": "[E] INSPECT | Read the tide marks, then assemble the chain that opened the route.",
	}
	if not hints.has(interaction_id):
		return
	_focus_toasts_shown.append(interaction_id)
	ui.toast(str(hints[interaction_id]))


## Case file (evidence board) — presentation-only view of the committed
## snapshot through the fail-closed FACT_LABEL allowlist. The SEALED card is
## fixed copy and never names its fact.
static func evidence_cards(state: Dictionary) -> Array:
	var facts: Array = state.get("facts", [])
	var cards: Array = []
	for link in CASE_LINKS:
		var card_id := str(link[0])
		var fact_id := str(link[1])
		var filled: bool = fact_id in facts
		cards.append({
			"id": card_id,
			"filled": filled,
			"sealed": false,
			"label": str(FACT_LABEL.get(fact_id, "State recorded")) if filled else "Not yet in the ledger",
			"why": str(EVIDENCE_WHY.get(card_id, "")),
		})
	cards.append({
		"id": "SEALED",
		"filled": false,
		"sealed": true,
		"label": SEALED_CARD_LABEL,
		"why": SEALED_CARD_WHY,
	})
	return cards


func _show_case_file() -> void:
	var rules_learned_sorted: Array = _rules_learned_by_gate.keys()
	rules_learned_sorted.sort()
	ui.show_evidence_board(
		evidence_cards(machine.state),
		_case_chain_from_state(machine.state),
		rules_learned_sorted,
		_next_affordance_text(),
	)


func _toggle_case_file() -> void:
	if not _play_started or episode_over or ui.is_tutorial_open():
		return
	if ui.is_evidence_board_open():
		ui.hide_evidence_board()
		var closed_chain := _case_chain_from_state(machine.state)
		_case_revisit_sequence += 1
		_record_observation_receipt(
			"case_chain_closed",
			"CASE_FILE_CLOSE",
			machine.state_hash(),
			machine.state_hash(),
			{
				"action_code": "CLOSE_CASE_FILE",
				"revisit_index": _case_revisit_sequence,
				"chain_filled": int(closed_chain["filled"]),
				"chain_total": int(closed_chain["total"]),
			},
		)
		_emit_dashboard("case_file", {"phase": "close"})
		if not _dialogue_open:
			Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
			ui.set_cursor_captured(true)
		return
	_show_case_file()
	var opened_chain := _case_chain_from_state(machine.state)
	_case_revisit_sequence += 1
	_record_observation_receipt(
		"case_chain_opened",
		"CASE_FILE_OPEN",
		machine.state_hash(),
		machine.state_hash(),
		{
			"action_code": "OPEN_CASE_FILE",
			"revisit_index": _case_revisit_sequence,
			"chain_filled": int(opened_chain["filled"]),
			"chain_total": int(opened_chain["total"]),
		},
	)
	_emit_dashboard("case_file", {"phase": "open", "chain_filled": int(_case_chain_from_state(machine.state)["filled"])})
	if not _dialogue_open:
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.set_cursor_captured(false)


## Hint ladder — opt-in, non-spoiling, keyed by the current chain node.
func _hint_node() -> String:
	var state: Dictionary = machine.state
	if "tide_marks_hint" in state["facts"]:
		return "LEAD"
	if "signal_lens_installed" in state["facts"]:
		return "AUTHORIZE"
	if "signal_lens" in state["player"]["inventory"]:
		return "MOUNT"
	if _met_mira:
		return "LENS"
	return "ARRIVAL"


static func compass_hint(from_position: Vector3, to_position: Vector3) -> String:
	# 8-wind bearing from the player to the target, +Z = N (the offshore tower
	# lies north of the dock), +X = E, plus a rounded distance in metres.
	var dx := to_position.x - from_position.x
	var dz := to_position.z - from_position.z
	var distance := Vector2(dx, dz).length()
	if distance < 2.0:
		return "HERE"
	var bearing := fposmod(rad_to_deg(atan2(dx, dz)), 360.0)
	var sector := int(floor((bearing + 22.5) / 45.0)) % 8
	return "%s %d m" % [HINT_COMPASS[sector], int(round(distance))]


func hint_ladder_lines(rung: int) -> Array:
	# Pure over (committed snapshot, met-Mira flag, player position): rung 1
	# restates the open question, rung 2 names the place/person + compass,
	# rung 3 names the next valid entry (GoldenPathLayout.next_affordance).
	var lines: Array = []
	if rung <= 0:
		return lines
	var node := _hint_node()
	var affordance: Dictionary = GoldenPathLayout.next_affordance(machine.state, _met_mira)
	var target_id := str(affordance["target_id"])
	lines.append("1 | %s" % str(HINT_QUESTION_BY_NODE.get(node, "What does the ledger need next?")))
	if rung >= 2:
		var place := str(HINT_PLACE_BY_TARGET.get(target_id, "the next marked place"))
		var compass := "HERE"
		if player != null:
			compass = compass_hint(player.global_position, GoldenPathLayout.site_position(target_id))
		lines.append("2 | Look for %s | %s" % [place, compass])
	if rung >= 3:
		lines.append("3 | NEXT VALID ENTRY: %s" % str(affordance["text"]))
	return lines


func _set_hint_rung(rung: int) -> void:
	var next_rung := clampi(rung, 0, 3)
	var trail_on := next_rung >= 3
	if director != null and director.has_method("set_guide_trail_enabled") and (trail_on or _hint_rung >= 3):
		# Lane C's diegetic guide trail (rung 3 only; default off).
		director.set_guide_trail_enabled(trail_on)
	_hint_rung = next_rung
	_refresh_hint_ladder()


func _refresh_hint_ladder() -> void:
	if ui != null:
		ui.set_hint_ladder(_hint_rung, hint_ladder_lines(_hint_rung))


func _advance_hint_ladder() -> void:
	if not _play_started or episode_over or ui.is_tutorial_open():
		return
	var next_rung := _hint_rung + 1 if _hint_rung < 3 else 0
	_set_hint_rung(next_rung)
	_emit_dashboard("hint", {"rung": _hint_rung, "node": _hint_node()})


## Slot-assembly deduction at the tide marks (D-073). NOT a machine proposal:
## no apply_operation, no commit/hold envelope, no refusal count. The player
## assembles the chain from the ledger's own entries; the whole chain is
## checked at once against the committed facts by the pure static below.
static func deduction_is_supported(state: Dictionary, sequence: Array) -> bool:
	if sequence.size() != DEDUCTION_CHAIN.size():
		return false
	var facts: Array = state.get("facts", [])
	for index in DEDUCTION_CHAIN.size():
		var link_id := str(DEDUCTION_CHAIN[index])
		if str(sequence[index]) != link_id:
			return false
		var fact_id := ""
		for link in CASE_LINKS:
			if str(link[0]) == link_id:
				fact_id = str(link[1])
		if fact_id == "" or fact_id not in facts:
			return false
	return true


func _chain_link_label(link_id: String) -> String:
	for link in CASE_LINKS:
		if str(link[0]) == link_id:
			return str(FACT_LABEL.get(str(link[1]), "State recorded"))
	return "State recorded"


func _deduction_option_label(option_id: String) -> String:
	if option_id.begins_with("distract:"):
		var index := int(option_id.trim_prefix("distract:"))
		var pool := _deduction_distractor_pool()
		return str(pool[index]) if index >= 0 and index < pool.size() else DEDUCTION_RED_HERRING
	return _chain_link_label(option_id)


func _deduction_distractor_pool() -> Array:
	var pool: Array = [DEDUCTION_RED_HERRING]
	for text in _held_texts:
		pool.append(str(text))
	return pool


func deduction_options(slot_index: int) -> Array:
	# Per slot: the three chain labels plus distractors drawn from the ledger's
	# own held proposals and one authored red herring, in a deterministic order
	# seeded by the committed state hash and the slot index (never the HUD's
	# LENS -> MOUNT -> LEAD order), so assembling the chain means recalling
	# which entries the ledger actually validated. Slot 1 keeps Step away;
	# later slots offer CLEAR SLOTS instead. <= DEDUCTION_MAX_BUTTONS buttons.
	var options: Array = []
	for link_id in DEDUCTION_CHAIN:
		options.append({"id": "pick:" + str(link_id), "text": _chain_link_label(str(link_id))})
	var pool := _deduction_distractor_pool()
	var distractor_budget := DEDUCTION_MAX_BUTTONS - 1 - options.size()
	for offset in mini(distractor_budget, pool.size()):
		var pool_index := (slot_index + offset) % pool.size()
		options.append({"id": "pick:distract:%d" % pool_index, "text": str(pool[pool_index])})
	_deterministic_shuffle(options, machine.state_hash() + ":" + str(slot_index))
	if slot_index == 0:
		options.append({"id": "deduction_leave", "text": "Step away"})
	else:
		options.append({"id": "deduction_clear", "text": "CLEAR SLOTS"})
	return options


static func _deterministic_shuffle(items: Array, seed_text: String) -> void:
	# Fisher-Yates over a seeded RNG so the order is stable for a given
	# committed state (captures, autoplay, and evaluation stay reproducible)
	# but not the authored chain order.
	var rng := RandomNumberGenerator.new()
	rng.seed = hash(seed_text)
	for index in range(items.size() - 1, 0, -1):
		var swap_index := rng.randi_range(0, index)
		var held: Variant = items[index]
		items[index] = items[swap_index]
		items[swap_index] = held


func _open_deduction() -> void:
	_dialogue_open = true
	_deduction_open = true
	_deduction_picks = []
	_emit_dashboard("dialogue", {"phase": "deduction", "beat": "open", "attempts": _deduction_attempts})
	ui.hide_prompt()
	ui.dismiss_coach_card()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.set_cursor_captured(false)
	audio_feedback.play_cue("dialogue")
	ui.ledger_line("narration", "The tide marks are dry to the third line. The route is open; the ledger asks how it opened.")
	ui.ledger_line("deduction", "Assemble the chain that opened the tide route.")
	_show_deduction_slot()


func _show_deduction_slot() -> void:
	var slot_index := _deduction_picks.size()
	if slot_index >= DEDUCTION_CHAIN.size():
		var assembled: Array = []
		for option_id in _deduction_picks:
			assembled.append(_deduction_option_label(str(option_id)))
		ui.show_choices([
			{"id": "deduction_submit", "text": "SUBMIT CHAIN"},
			{"id": "deduction_clear", "text": "CLEAR SLOTS"},
			{"id": "deduction_leave", "text": "Step away"},
		], "[D] CHAIN | %s" % " -> ".join(assembled))
		return
	ui.show_choices(
		deduction_options(slot_index),
		"[D] SLOT %d/%d | Which ledger entry comes %s?" % [
			slot_index + 1, DEDUCTION_CHAIN.size(), ["first", "next", "last"][slot_index]
		]
	)


func _on_deduction_choice(choice_id: String) -> void:
	_begin_input_feedback_probe("deduction-choice:" + choice_id)
	if choice_id.begins_with("pick:"):
		_deduction_picks.append(choice_id.trim_prefix("pick:"))
		_emit_dashboard("dialogue", {"phase": "deduction", "beat": "slot", "slot": _deduction_picks.size()})
		_show_deduction_slot()
		_complete_input_feedback_probe("deduction-slot")
		return
	match choice_id:
		"deduction_clear":
			_deduction_picks = []
			_show_deduction_slot()
			_complete_input_feedback_probe("deduction-clear")
		"deduction_submit":
			_deduction_attempts += 1
			var supported := deduction_is_supported(machine.state, _deduction_picks)
			if supported:
				_deduction_confirmed = true
				ui.ledger_line("deduction_confirmed", "Lens secured -> signal restored -> lead authorized")
				_emit_dashboard("dialogue", {"phase": "deduction", "beat": "confirmed", "attempts": _deduction_attempts})
				_complete_input_feedback_probe("deduction-confirmed")
				_finish_episode()
				_close_deduction()
			else:
				ui.ledger_line("deduction_held", "The chain does not match the ledger. Re-read the case file.")
				_emit_dashboard("dialogue", {"phase": "deduction", "beat": "held", "attempts": _deduction_attempts})
				_deduction_picks = []
				_show_deduction_slot()
				_complete_input_feedback_probe("deduction-held")
		"deduction_leave":
			_close_deduction()
			_complete_input_feedback_probe("deduction-close")
		_:
			_pending_input_feedback.clear()


func _close_deduction() -> void:
	if not _deduction_open:
		return
	_emit_dashboard("dialogue", {"phase": "deduction", "beat": "close", "attempts": _deduction_attempts})
	_deduction_open = false
	_dialogue_open = false
	_deduction_picks = []
	ui.clear_choices()
	ui.set_contextual_panel_visible(false)
	ui.hide_evidence_board()
	if not _smoke_mode and not _evaluate_mode and not episode_over:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)


func _finish_episode() -> void:
	if episode_over:
		return
	episode_over = true
	_emit_dashboard("episode_complete", {
		"holds_by_gate": _holds_by_gate.duplicate(),
	}.merged(_dashboard_state_summary()))
	ui.hide_prompt()
	# The tide-route acquisition is the episode's biggest beat: fanfare + commit
	# flash + golden ledger celebration land immediately, then the P-B06 camera
	# (or the reduced-motion static card) carries the close. The tower stays
	# dark and sealed throughout (W-002/D-030) — the payoff is the earned route.
	var ending_chain := _case_chain_from_state(machine.state)
	_record_observation_receipt(
		"session_end_emitted",
		"SESSION_END",
		machine.state_hash(),
		machine.state_hash(),
		{
			"commit_count": commit_count,
			"refusal_count": refusal_count,
			"chain_filled": int(ending_chain["filled"]),
			"chain_total": int(ending_chain["total"]),
		},
	)
	_receipt_export_failed = not _export_receipts_if_requested()
	audio_feedback.play_cue("ending")
	ui.flash("commit")
	ui.ledger_line("commit", "Case complete. Tide route secured; below the third mark, low tide opens the path.")
	ui.ledger_line("narration", "The ledger's final line dries to gold. Harbor light reaches the end of the channel.")
	ui.toast("ACQUIRED | LOW-TIDE ROUTE")
	ui.set_progress(3, 3, "ROUTE SECURED")
	director.play_ending(func() -> void:
		# The 'ledger closes' beat: brief dim + case-complete toast, then the end
		# card slides in (reduced motion: immediate card). UI owns the staging.
		# D-073: the receipt is a three-page document (PAGE n/3) built by one
		# page builder shared with the ending screenshot stage.
		ui.set_end_card_hash(machine.state_hash())
		ui.play_ledger_close(_episode_end_pages())
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.set_cursor_captured(false)
	)


func _episode_receipt_text() -> String:
	# Kept as the single-string receipt entry point (page 1 of the paged end
	# card). Every count comes straight from committed snapshots or
	# presentation counters (_contribution_log, _rules_learned_by_gate,
	# _deduction_attempts), never invented.
	return str(_episode_end_pages()[0])


func _episode_end_pages() -> Array:
	# D-073 paged receipt (Obra Dinn's multipage tally; Aside search-feedback
	# 2026-09-02 pattern 8): page 1 = the investigator's contribution (+ the
	# deduction line), page 2 = rules learned and what each told you, page 3 =
	# the validator receipt with the state hash (copyable field in the UI), one
	# settled statement and the unsettled part phrased as a question. Shared by
	# the live end card and the ending screenshot stage (page 1 by default).
	var page_one := "\n[color=#F2B84B]THE SEALED LIGHTHOUSE | CASE COMPLETE[/color]\n\n"
	page_one += "The lighthouse remains sealed tonight, but every entry in the ledger is valid.\n"
	page_one += "The low-tide marks point to the next route.\n"
	page_one += "\n[color=#F2B84B][font_size=24]INVESTIGATOR'S CONTRIBUTION[/font_size][/color]\n"
	if _contribution_log.is_empty():
		page_one += "[color=#D9D3C4]No entries were committed this session.[/color]\n"
	else:
		for entry in _contribution_log:
			var labels: Array = entry["labels"]
			var label_text := "; ".join(labels) if not labels.is_empty() else "State recorded"
			page_one += "[color=#D9D3C4]#%d %s | %s[/color]\n" % [
				int(entry["entry"]),
				label_text,
				HarborLedgerUI.stage_clause(int(entry["stage_from"]), int(entry["stage_to"])),
			]
	page_one += "[color=#F2B84B]DEDUCTION | %s[/color]\n" % _deduction_receipt_clause()

	var rules_learned_sorted: Array = _rules_learned_by_gate.keys()
	rules_learned_sorted.sort()
	var page_two := "\n[color=#F2B84B][font_size=24]RULES LEARNED %d[/font_size][/color]\n" % rules_learned_sorted.size()
	if rules_learned_sorted.is_empty():
		page_two += "[color=#D9D3C4]No hold taught a rule this session.[/color]\n"
	else:
		for gate in rules_learned_sorted:
			page_two += "[color=#D9D3C4][V] %s | %s[/color]\n" % [str(gate), str(_rules_learned_by_gate[gate])]
			page_two += "[color=#8FA3B2]    WHAT THIS TOLD YOU | %s[/color]\n" % str(
				_inference_by_gate.get(gate, "The ledger keeps its order.")
			)
	page_two += "\n[color=#D9D3C4]Every held row stays in the ledger. The rules are the case.[/color]\n"

	var page_three := "\n[color=#F2B84B][font_size=24]VALIDATOR RECEIPT[/font_size][/color]\n"
	page_three += "[color=#F2B84B]ENTRIES %d[/color] | [color=#D9685F]HOLDS %d[/color] | FINAL STAGE %d\n" % [
		commit_count, refusal_count, int(machine.state["quest"]["stage"])
	]
	page_three += "[color=#8FA3B2]HOLDS BY GATE | %s[/color]\n" % _holds_by_gate_text()
	page_three += "[color=#8FA3B2]STATE HASH %s...[/color] (full hash below)\n" % machine.state_hash().substr(0, 16)
	page_three += "\n[color=#D9D3C4]SETTLED | The tide route was earned on this evidence, under these rules.[/color]\n"
	page_three += "[color=#D9D3C4]OPEN | Why is the lighthouse sealed? Not tonight's entry.[/color]\n"
	page_three += "\n[color=#D9D3C4]CONTINUE AT THE NEXT TIDE[/color]"
	return [page_one, page_two, page_three]


func _deduction_receipt_clause() -> String:
	# 'confirmed in N attempt(s)' once the chain was assembled; the ending
	# screenshot stage never runs the deduction, so it reads 'not recorded'.
	if not _deduction_confirmed:
		return "not recorded"
	return "confirmed in %d attempt%s" % [_deduction_attempts, "" if _deduction_attempts == 1 else "s"]


func _sha256_bytes(bytes: PackedByteArray) -> String:
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	if context.update(bytes) != OK:
		return ""
	return context.finish().hex_encode()


func _compute_build_fingerprint() -> Dictionary:
	var source_hashes := {}
	var missing_paths: Array = []
	for source_path in RECEIPT_SOURCE_PATHS:
		var file := FileAccess.open(str(source_path), FileAccess.READ)
		if file == null:
			missing_paths.append(str(source_path))
			continue
		var digest := _sha256_bytes(file.get_buffer(file.get_length()))
		if digest.is_empty():
			missing_paths.append(str(source_path))
		else:
			source_hashes[str(source_path)] = digest
	var complete := missing_paths.is_empty() and source_hashes.size() == RECEIPT_SOURCE_PATHS.size()
	return {
		"algorithm": "sha256-bytes-v1",
		"source_paths": RECEIPT_SOURCE_PATHS.duplicate(),
		"source_hashes": source_hashes,
		"combined_sha256": CanonicalState.sha256(source_hashes) if complete else "",
		"complete": complete,
		"missing_paths": missing_paths,
	}


func _record_observation_receipt(
	receipt_kind: String,
	phase_code: String,
	prior_hash: String,
	next_hash: String,
	payload: Dictionary,
) -> void:
	if not _receipt_recording_enabled or _receipt_overflowed:
		return
	if _observation_receipts.size() >= RECEIPT_MAX_ROWS:
		_receipt_overflowed = true
		_receipt_export_failed = true
		push_error("Observation receipt capacity exceeded; export refused")
		return
	_receipt_sequence += 1
	var now_us := Time.get_ticks_usec()
	var monotonic_us := maxi(now_us - _telemetry_started_us, 0)
	var receipt := {
		"receipt_schema_version": RECEIPT_SCHEMA_VERSION,
		"receipt_seq": _receipt_sequence,
		"monotonic_us": monotonic_us,
		"telemetry_session_id": _telemetry_session_id,
		"scenario_id": str(scenario.get("scenario_id", "sealed-lighthouse-v1")),
		"build_id": RECEIPT_BUILD_ID,
		"build_fingerprint": _build_fingerprint.duplicate(true),
		"engine_version": str(Engine.get_version_info().get("string", "unknown")),
		"scene_id": RECEIPT_SCENE_ID,
		"receipt_kind": receipt_kind,
		"phase_code": phase_code,
		"prior_state_sha256": prior_hash,
		"next_state_sha256": next_hash,
		"canonical_state_unchanged": prior_hash == next_hash,
		"payload": payload.duplicate(true),
	}
	_observation_receipts.append(receipt)


func _receipt_payload_safe(receipt: Dictionary) -> bool:
	var allowed_keys := {
		"objective_rendered": ["objective_code", "next_affordance_target"],
		"commit_emitted": ["operation_code", "commit_index", "stage_from", "stage_to", "chain_filled", "chain_total", "next_affordance_target"],
		"hold_emitted": ["reason_codes", "gate_codes", "correction_code", "next_affordance_target"],
		"case_chain_opened": ["action_code", "revisit_index", "chain_filled", "chain_total"],
		"case_chain_closed": ["action_code", "revisit_index", "chain_filled", "chain_total"],
		"session_end_emitted": ["commit_count", "refusal_count", "chain_filled", "chain_total"],
	}
	var kind := str(receipt.get("receipt_kind", ""))
	if not allowed_keys.has(kind):
		return false
	var payload: Variant = receipt.get("payload", {})
	if not payload is Dictionary:
		return false
	if payload.size() != allowed_keys[kind].size():
		return false
	for key in payload.keys():
		if str(key) not in allowed_keys[kind]:
			return false
	var serialized := JSON.stringify(payload).to_lower()
	for token in RECEIPT_FORBIDDEN_PAYLOAD_TOKENS:
		if serialized.contains(str(token)):
			return false
	return true


func _is_sha256(value: Variant) -> bool:
	if not value is String or value.length() != 64:
		return false
	for character in value:
		if str(character) not in "0123456789abcdef":
			return false
	return true


func _telemetry_report(state_hash_before: String, state_hash_after: String) -> Dictionary:
	var ordered := true
	var shape_valid := true
	var hashes_valid := true
	var state_flags_valid := true
	var payloads_safe := true
	var holds_unchanged := true
	var sequence_previous := 0
	var monotonic_previous := -1
	var required_fields := [
		"receipt_schema_version", "receipt_seq", "monotonic_us", "telemetry_session_id",
		"scenario_id", "build_id", "build_fingerprint", "engine_version", "scene_id",
		"receipt_kind", "phase_code", "prior_state_sha256", "next_state_sha256",
		"canonical_state_unchanged", "payload",
	]
	for receipt in _observation_receipts:
		for field in required_fields:
			shape_valid = shape_valid and receipt.has(field)
		shape_valid = shape_valid and receipt.get("receipt_schema_version", "") == RECEIPT_SCHEMA_VERSION
		shape_valid = shape_valid and str(receipt.get("receipt_kind", "")) != "" and str(receipt.get("phase_code", "")) != ""
		shape_valid = shape_valid and receipt.get("payload", {}) is Dictionary
		var sequence := int(receipt.get("receipt_seq", 0))
		var monotonic_us := int(receipt.get("monotonic_us", -1))
		ordered = ordered and sequence == sequence_previous + 1 and monotonic_us >= monotonic_previous
		sequence_previous = sequence
		monotonic_previous = monotonic_us
		var prior_hash := str(receipt.get("prior_state_sha256", ""))
		var next_hash := str(receipt.get("next_state_sha256", ""))
		hashes_valid = hashes_valid and _is_sha256(prior_hash) and _is_sha256(next_hash)
		state_flags_valid = state_flags_valid and bool(receipt.get("canonical_state_unchanged", false)) == (prior_hash == next_hash)
		payloads_safe = payloads_safe and _receipt_payload_safe(receipt)
		if str(receipt.get("receipt_kind", "")) == "hold_emitted":
			holds_unchanged = holds_unchanged and bool(receipt.get("canonical_state_unchanged", false)) and prior_hash == next_hash
	var fingerprint_complete := bool(_build_fingerprint.get("complete", false))
	var fingerprint_sources: Variant = _build_fingerprint.get("source_hashes", {})
	var fingerprint_valid := fingerprint_complete and fingerprint_sources is Dictionary
	if fingerprint_valid:
		fingerprint_valid = _is_sha256(_build_fingerprint.get("combined_sha256", "")) and CanonicalState.sha256(fingerprint_sources) == str(_build_fingerprint.get("combined_sha256", ""))
		for source_path in RECEIPT_SOURCE_PATHS:
			fingerprint_valid = fingerprint_valid and _is_sha256(fingerprint_sources.get(str(source_path), ""))
	var canonical_untouched := machine.state_hash() == state_hash_after
	var checks := [
		{"check": "receipts_present", "pass": not _observation_receipts.is_empty()},
		{"check": "receipt_shape_complete", "pass": shape_valid},
		{"check": "receipt_sequence_and_clock_ordered", "pass": ordered},
		{"check": "receipt_state_hashes_valid", "pass": hashes_valid},
		{"check": "receipt_payloads_code_only", "pass": payloads_safe},
		{"check": "receipt_state_flags_consistent", "pass": state_flags_valid},
		{"check": "hold_receipts_preserve_state", "pass": holds_unchanged},
		{"check": "build_fingerprint_is_grounded", "pass": fingerprint_valid},
		{"check": "build_fingerprint_recomputed", "pass": fingerprint_valid},
		{"check": "telemetry_does_not_change_canonical_state", "pass": canonical_untouched and state_hash_before == state_hash_after},
		{"check": "receipt_capacity_not_exceeded", "pass": not _receipt_overflowed},
	]
	var passed := true
	for check in checks:
		passed = passed and bool(check["pass"])
	return {
		"schema_version": RECEIPT_SCHEMA_VERSION,
		"engineering_only": true,
		"claim_boundary": "Local presentation receipts only; no participant, model, efficacy, or browser-latency evidence.",
		"passed": passed,
		"build_fingerprint": _build_fingerprint.duplicate(true),
		"receipts": _observation_receipts.duplicate(true),
		"checks": checks,
	}

func _receipt_export_integrity() -> Dictionary:
	var shape_valid := true
	var ordered := true
	var hashes_valid := true
	var state_flags_valid := true
	var payloads_safe := true
	var holds_unchanged := true
	var chain_linked := true
	var sequence_previous := 0
	var monotonic_previous := -1
	var expected_previous_hash := _telemetry_initial_state_hash
	var required_fields := [
		"receipt_schema_version", "receipt_seq", "monotonic_us", "telemetry_session_id",
		"scenario_id", "build_id", "build_fingerprint", "engine_version", "scene_id",
		"receipt_kind", "phase_code", "prior_state_sha256", "next_state_sha256",
		"canonical_state_unchanged", "payload",
	]
	for receipt in _observation_receipts:
		for field in required_fields:
			shape_valid = shape_valid and receipt.has(field)
		shape_valid = shape_valid and receipt.get("receipt_schema_version", "") == RECEIPT_SCHEMA_VERSION
		shape_valid = shape_valid and str(receipt.get("receipt_kind", "")) != "" and str(receipt.get("phase_code", "")) != ""
		shape_valid = shape_valid and receipt.get("payload", {}) is Dictionary
		var sequence := int(receipt.get("receipt_seq", 0))
		var monotonic_us := int(receipt.get("monotonic_us", -1))
		ordered = ordered and sequence == sequence_previous + 1 and monotonic_us >= monotonic_previous
		sequence_previous = sequence
		monotonic_previous = monotonic_us
		var prior_hash := str(receipt.get("prior_state_sha256", ""))
		var next_hash := str(receipt.get("next_state_sha256", ""))
		hashes_valid = hashes_valid and _is_sha256(prior_hash) and _is_sha256(next_hash)
		state_flags_valid = state_flags_valid and bool(receipt.get("canonical_state_unchanged", false)) == (prior_hash == next_hash)
		chain_linked = chain_linked and prior_hash == expected_previous_hash
		expected_previous_hash = next_hash
		payloads_safe = payloads_safe and _receipt_payload_safe(receipt)
		if str(receipt.get("receipt_kind", "")) == "hold_emitted":
			holds_unchanged = holds_unchanged and bool(receipt.get("canonical_state_unchanged", false)) and prior_hash == next_hash
	var fingerprint_complete := bool(_build_fingerprint.get("complete", false))
	var source_hashes: Variant = _build_fingerprint.get("source_hashes", {})
	var fingerprint_valid := fingerprint_complete and source_hashes is Dictionary and _is_sha256(_build_fingerprint.get("combined_sha256", ""))
	if fingerprint_valid:
		fingerprint_valid = CanonicalState.sha256(source_hashes) == str(_build_fingerprint.get("combined_sha256", ""))
		for source_path in RECEIPT_SOURCE_PATHS:
			fingerprint_valid = fingerprint_valid and _is_sha256(source_hashes.get(str(source_path), ""))
	else:
		fingerprint_valid = false
	chain_linked = chain_linked and not _observation_receipts.is_empty() and expected_previous_hash == machine.state_hash()
	var checks := [
		{"check": "receipts_present", "pass": not _observation_receipts.is_empty()},
		{"check": "receipt_shape_complete", "pass": shape_valid},
		{"check": "receipt_sequence_and_clock_ordered", "pass": ordered},
		{"check": "receipt_state_hashes_valid", "pass": hashes_valid},
		{"check": "receipt_payloads_code_only", "pass": payloads_safe},
		{"check": "receipt_state_flags_consistent", "pass": state_flags_valid},
		{"check": "receipt_state_chain_linked", "pass": chain_linked},
		{"check": "hold_receipts_preserve_state", "pass": holds_unchanged},
		{"check": "build_fingerprint_is_grounded", "pass": fingerprint_valid},
		{"check": "build_fingerprint_recomputed", "pass": fingerprint_valid},
		{"check": "receipt_capacity_not_exceeded", "pass": not _receipt_overflowed},
	]
	var passed := true
	for check in checks:
		passed = passed and bool(check["pass"])
	return {"passed": passed, "checks": checks}


func _export_receipts_if_requested() -> bool:
	if _receipt_export_failed:
		print("RECEIPT-EXPORT " + JSON.stringify({
			"engineering_only": true,
			"written": false,
			"reason": "capacity_exceeded" if _receipt_overflowed else "recording_failed",
		}))
		return false
	if _receipt_output_path.is_empty():
		return true
	var integrity := _receipt_export_integrity()
	if not bool(integrity["passed"]):
		print("RECEIPT-EXPORT " + JSON.stringify({"engineering_only": true, "written": false, "reason": "integrity_failed", "checks": integrity["checks"]}))
		return false
	var export_payload := {
		"schema_version": RECEIPT_SCHEMA_VERSION,
		"engineering_only": true,
		"claim_boundary": "Explicit local presentation receipt export; event availability only, never attention, input latency, participant, model, or efficacy evidence.",
		"scenario_id": str(scenario.get("scenario_id", "sealed-lighthouse-v1")),
		"build_id": RECEIPT_BUILD_ID,
		"build_fingerprint": _build_fingerprint.duplicate(true),
		"telemetry_session_id": _telemetry_session_id,
		"initial_state_sha256": _telemetry_initial_state_hash,
		"final_state_sha256": machine.state_hash(),
		"receipt_count": _observation_receipts.size(),
		"receipts": _observation_receipts.duplicate(true),
		"integrity": integrity,
	}
	var absolute_path := ProjectSettings.globalize_path(_receipt_output_path)
	var written := _write_json_atomic(absolute_path, export_payload)
	print("RECEIPT-EXPORT " + JSON.stringify({
		"engineering_only": true,
		"written": written,
		"path": absolute_path,
		"receipt_count": _observation_receipts.size(),
	}))
	return written




func _run_engineering_evaluation(path: String) -> void:
	# Static/runtime presentation instrumentation only. This mode performs no
	# participant or model trial and is explicitly not a G4/efficacy measurement.
	player.input_locked = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.show_start_gate(true)
	ui.set_audio_state(audio_feedback.is_unlocked(), audio_feedback.is_muted())
	await get_tree().process_frame
	var state_hash_before := machine.state_hash()

	# Exercise the real proposal→ledger acknowledgement path with a synthetic,
	# state-preserving early hint request. This proves telemetry wiring only.
	_begin_input_feedback_probe("synthetic-evaluation:early-hint")
	var probe_result := _propose(
		"reveal_hint",
		{"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
		"Synthetic tide-marks lead request",
		_interactable("mira"),
	)
	if not probe_result["accepted"]:
		_refusal_feedback(probe_result["codes"])
	# D-073 dashboard-trace probe. Computed immediately after the synthetic
	# early-hint proposal: `_last_dashboard_trace` is the mirror of that call,
	# and no other machine call happens before this line.
	var trace_probe := _last_dashboard_trace.duplicate(true)
	await get_tree().process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
	await get_tree().process_frame

	var ui_snapshot := ui.get_engineering_snapshot()
	var audio_snapshot := audio_feedback.get_engineering_snapshot()
	var player_snapshot := player.get_engineering_snapshot()
	var input_feedback_snapshot := _input_feedback_snapshot()

	# Presentation-only contribution_delta probe: hand-built snapshots (never
	# derived from `machine`) exercise the pure diff function without any
	# canonical mutation. Reused for both the check and the report's
	# "contribution" block.
	var contribution_probe_prior: Dictionary = machine.state.duplicate(true)
	var contribution_probe_next: Dictionary = contribution_probe_prior.duplicate(true)
	contribution_probe_next["facts"].append("signal_lens_acquired")
	contribution_probe_next["quest"]["stage"] = 1
	contribution_probe_next["player"]["inventory"].append("signal_lens")
	contribution_probe_next["quest"]["flags"].append("signal_lens_acquired")
	var contribution_probe := contribution_delta(contribution_probe_prior, contribution_probe_next)
	var visible_label_probe := player_visible_fact_labels([
		"signal_lens_acquired", "keeper_betrayal", "future_private_fact"
	])
	var case_chain_link_ids: Array = []
	for link in ui_snapshot["case_chain"]["links"]:
		case_chain_link_ids.append(str(link["id"]))
	var direct_case_chain_filled := 0
	for link in CASE_LINKS:
		if str(link[1]) in machine.state["facts"]:
			direct_case_chain_filled += 1

	# D-073 evidence-board probe: cards from the live committed snapshot (all
	# unfilled here) and from a hand-built snapshot with two chain facts. Fill
	# flags must equal fact membership; the SEALED card must carry no fact id.
	var board_cards_now := evidence_cards(machine.state)
	var board_probe_state: Dictionary = machine.state.duplicate(true)
	board_probe_state["facts"] = ["signal_lens_acquired", "signal_lens_installed", "lighthouse_hint_authorized"]
	var board_cards_probe := evidence_cards(board_probe_state)
	var board_ids_now: Array = []
	var board_fill_matches_now := true
	for card in board_cards_now:
		board_ids_now.append(str(card["id"]))
		for link in CASE_LINKS:
			if str(link[0]) == str(card["id"]):
				board_fill_matches_now = board_fill_matches_now and (
					bool(card["filled"]) == (str(link[1]) in machine.state["facts"])
				)
	var board_fill_matches_probe := true
	var board_probe_filled: Array = []
	for card in board_cards_probe:
		if bool(card["filled"]):
			board_probe_filled.append(str(card["id"]))
		for link in CASE_LINKS:
			if str(link[0]) == str(card["id"]):
				board_fill_matches_probe = board_fill_matches_probe and (
					bool(card["filled"]) == (str(link[1]) in board_probe_state["facts"])
				)
	var sealed_text := ""
	for card in board_cards_now:
		if str(card["id"]) == "SEALED":
			sealed_text = "%s | %s" % [str(card["label"]), str(card["why"])]
	var sealed_text_clean := sealed_text != "" and not sealed_text.contains("keeper_betrayal")
	for fact_id in FACT_LABEL.keys():
		sealed_text_clean = sealed_text_clean and not sealed_text.contains(str(fact_id))
	for link in CASE_LINKS:
		sealed_text_clean = sealed_text_clean and not sealed_text.contains(str(link[1]))

	# D-073 deduction probe: the pure static validator over hand-built
	# snapshots. True only for the exact [LENS, MOUNT, LEAD] sequence with all
	# three chain facts committed; never for a distractor, a reordering, a
	# short chain, or a snapshot missing a chain fact.
	var two_fact_state: Dictionary = machine.state.duplicate(true)
	two_fact_state["facts"] = ["signal_lens_acquired", "signal_lens_installed"]
	var three_fact_state: Dictionary = machine.state.duplicate(true)
	three_fact_state["facts"] = [
		"lighthouse_hint_authorized", "signal_lens_acquired", "signal_lens_installed", "tide_marks_hint"
	]
	var deduction_probes := {
		"empty_state_correct_order": deduction_is_supported(machine.state, ["LENS", "MOUNT", "LEAD"]),
		"two_facts_correct_order": deduction_is_supported(two_fact_state, ["LENS", "MOUNT", "LEAD"]),
		"three_facts_correct_order": deduction_is_supported(three_fact_state, ["LENS", "MOUNT", "LEAD"]),
		"three_facts_wrong_order": deduction_is_supported(three_fact_state, ["MOUNT", "LENS", "LEAD"]),
		"three_facts_distractor": deduction_is_supported(three_fact_state, ["LENS", "MOUNT", "distract:0"]),
		"three_facts_short_chain": deduction_is_supported(three_fact_state, ["LENS", "MOUNT"]),
	}

	# D-073 hint-ladder probe: rung 3 must name the current next valid entry
	# (GoldenPathLayout.next_affordance). View-local rung is restored to 0.
	var next_affordance_probe := _next_affordance_text()
	_set_hint_rung(3)
	var hint_probe_text := ui.hint_ladder_text()
	_set_hint_rung(0)
	var checks := [
		{
			"check": "evaluation_does_not_mutate_canonical_state",
			"pass": machine.state_hash() == state_hash_before,
		},
		{
			"check": "web_start_gate_is_visible_before_play",
			"pass": ui_snapshot["start_gate_visible"] and not ui_snapshot["play_started"],
		},
		{
			"check": "audio_remains_locked_before_user_gesture",
			"pass": not audio_snapshot["unlocked"] and not audio_snapshot["ambient_playing"],
		},
		{
			"check": "procedural_audio_uses_no_external_assets",
			"pass": audio_snapshot["external_audio_assets"].is_empty(),
		},
		{
			"check": "semantic_feedback_has_non_color_redundancy",
			"pass": "text" in ui_snapshot["semantic_feedback_redundancy"]
				and "icon" in ui_snapshot["semantic_feedback_redundancy"],
		},
		{
			"check": "responsive_layout_profiles_declared",
			"pass": ui_snapshot["responsive_profiles"]["narrow"] == "narrow-stacked"
				and ui_snapshot["responsive_profiles"]["wide"] == "wide-columns",
		},
		{
			"check": "wide_layout_preserves_playfield",
			"pass": float(ui_snapshot["layout_metrics"]["wide_playfield_fraction"]) >= 0.65,
		},
		{
			"check": "player_world_changes_route_through_proposals",
			"pass": player_snapshot["world_change_boundary"].begins_with("interact_requested"),
		},
		{
			"check": "input_feedback_latency_probe_emits_sample",
			"pass": int(input_feedback_snapshot["sample_count"]) >= 1
				and float(input_feedback_snapshot["p95_input_to_visible_feedback_ms"]) >= 0.0,
		},
		{
			"check": "contribution_delta_is_pure_and_names_facts",
			"pass": contribution_probe["facts_added"] == ["signal_lens_acquired"]
				and int(contribution_probe["stage_from"]) == 0
				and int(contribution_probe["stage_to"]) == 1
				and contribution_probe["inventory_added"] == ["signal_lens"]
				and visible_label_probe == ["Signal lens secured"]
				and machine.state_hash() == state_hash_before,
		},
		{
			"check": "hold_teaches_rule_for_its_gate",
			"pass": gate_for_code("STAGE_GATED_DISCLOSURE") in ui_snapshot["rules_learned"]
				and str(ui_snapshot["last_rule_line"]).begins_with("RULE LEARNED"),
		},
		{
			"check": "case_chain_mirrors_committed_snapshot",
			"pass": int(ui_snapshot["case_chain"]["total"]) == 3
				and case_chain_link_ids == ["LENS", "MOUNT", "LEAD"]
				and int(ui_snapshot["case_chain"]["filled"]) == direct_case_chain_filled,
		},
		{
			"check": "evidence_board_mirrors_committed_facts",
			"pass": board_ids_now == ["LENS", "MOUNT", "LEAD", "SEALED"]
				and board_fill_matches_now
				and board_fill_matches_probe
				and board_probe_filled == ["LENS", "MOUNT"]
				and sealed_text_clean
				and machine.state_hash() == state_hash_before,
		},
		{
			"check": "deduction_reads_committed_facts_only",
			"pass": deduction_probes["empty_state_correct_order"] == false
				and deduction_probes["two_facts_correct_order"] == false
				and deduction_probes["three_facts_correct_order"] == true
				and deduction_probes["three_facts_wrong_order"] == false
				and deduction_probes["three_facts_distractor"] == false
				and deduction_probes["three_facts_short_chain"] == false
				and machine.state_hash() == state_hash_before,
		},
		{
			"check": "guided_step_matches_next_affordance",
			"pass": next_affordance_probe != ""
				and hint_probe_text.contains(next_affordance_probe)
				and int(ui_snapshot["hint_ladder"]["rung"]) == 0,
		},
		{
			"check": "evaluation_trace_names_only_evaluated_checks",
			"pass": trace_probe["checks"] == [
					{"code": "FORBIDDEN_DISCLOSURE", "gate": "DISCLOSURE", "outcome": "pass"},
					{"code": "STAGE_GATED_DISCLOSURE", "gate": "DISCLOSURE/QUEST STAGE", "outcome": "fail"},
				]
				and trace_probe["evaluated_gates"] == ["DISCLOSURE", "DISCLOSURE/QUEST STAGE"]
				and str(trace_probe["held_at"]) == "STAGE_GATED_DISCLOSURE"
				and bool(trace_probe["short_circuit"]) == true
				and trace_probe["skipped"] == [
					{"code": "UNKNOWN_ACTOR", "gate": "POLICY"},
					{"code": "NPC_DOES_NOT_KNOW_FACT", "gate": "KNOWLEDGE"},
				]
				and trace_probe["out_of_scope"] == ["PRECONDITION", "REACHABILITY"]
				and trace_probe["family_states"] == {
					"POLICY": "skipped",
					"PRECONDITION": "out_of_scope",
					"REACHABILITY": "out_of_scope",
					"KNOWLEDGE": "skipped",
					"DISCLOSURE": "fail",
					"QUEST STAGE": "fail",
				}
				and bool(trace_probe["consistent"]) == true
				and machine.state_hash() == state_hash_before,
		},
	]
	var state_hash_after := machine.state_hash()
	var telemetry := _telemetry_report(state_hash_before, state_hash_after)
	var passed := true
	for check in checks:
		if not check["pass"]:
			passed = false
	passed = passed and bool(telemetry["passed"])
	var report := {
		"schema_version": "1.3.0",
		"evaluation": "sealed-lighthouse-3d-presentation-engineering",
		"engineering_only": true,
		"not_evidence_for": ["G4", "usability", "immersion", "affect", "efficacy", "browser input latency"],
		"claim_boundary": "Automated presentation invariants and engine-local telemetry wiring only; no participant, neural-model, browser-latency, or gameplay-efficacy measurement.",
		"telemetry": telemetry,
		"passed": passed,
		"state_sha256_before": state_hash_before,
		"state_sha256_after": state_hash_after,
		"supported_screenshot_stages": ["arrival", "refusal", "authorized_hint", "ending"],
		"ui": ui_snapshot,
		"audio": audio_snapshot,
		"player": player_snapshot,
		"input_feedback": input_feedback_snapshot,
		"contribution": {
			"probe": contribution_probe,
			"visible_label_probe": visible_label_probe,
			"case_chain": ui_snapshot["case_chain"],
			"rules_learned": ui_snapshot["rules_learned"],
		},
		"dashboard_trace": trace_probe,
		"evidence_board": {
			"cards_from_committed_state": board_cards_now,
			"cards_from_hand_built_snapshot": board_cards_probe,
			"sealed_card_text": sealed_text,
		},
		"deduction": {
			"chain": DEDUCTION_CHAIN.duplicate(),
			"max_buttons_per_slot": DEDUCTION_MAX_BUTTONS,
			"probes": deduction_probes,
			"options_slot_1": deduction_options(0),
		},
		"hint_ladder": {
			"rung_3_text": hint_probe_text,
			"next_affordance_text": next_affordance_probe,
		},
		"checks": checks,
	}
	var absolute_path := ProjectSettings.globalize_path(path)
	var written := _write_json_atomic(absolute_path, report)
	print("ENGINEERING-EVALUATION " + JSON.stringify({
		"engineering_only": true,
		"passed": passed,
		"written": written,
		"path": absolute_path,
	}))
	get_tree().quit(0 if passed and written and not _receipt_export_failed else 1)


func _npc_sha256_bytes(data: PackedByteArray) -> String:
	var hashing := HashingContext.new()
	hashing.start(HashingContext.HASH_SHA256)
	hashing.update(data)
	return hashing.finish().hex_encode()


func _npc_input(path: String) -> Dictionary:
	var absolute := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(absolute):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(absolute))
	return parsed if parsed is Dictionary else {}


func _npc_input_hash(path: String) -> String:
	var absolute := ProjectSettings.globalize_path(path)
	if not FileAccess.file_exists(absolute):
		return ""
	return _npc_sha256_bytes(FileAccess.get_file_as_bytes(absolute))


func _npc_source_hashes(input: Dictionary) -> Dictionary:
	var hashes: Dictionary = input.get("source_hashes", {}).duplicate(true) if input.get("source_hashes", {}) is Dictionary else {}
	if not hashes.has("source_project_config_sha256"):
		hashes["source_project_config_sha256"] = _npc_input_hash("res://project.godot")
	if not hashes.has("npc_protocol_config_sha256"):
		hashes["npc_protocol_config_sha256"] = npc_config_hash()
	if not hashes.has("source_schema_sha256"):
		hashes["source_schema_sha256"] = _npc_input_hash("res://../schemas/npc-goal-recovery.schema.json")
	hashes["policy_hash"] = npc_policy_hash()
	return hashes


func _npc_apply_mutation(mutation: Variant) -> Dictionary:
	var operation := ""
	var arguments: Dictionary = {}
	if mutation is String:
		operation = str(mutation)
	elif mutation is Dictionary:
		operation = str(mutation.get("operation", mutation.get("kind", "")))
		arguments = mutation.get("arguments", {}) if mutation.get("arguments", {}) is Dictionary else {}
	else:
		return {"accepted": false, "codes": ["MUTATION_SCHEMA_INVALID"], "mutated": false}
	match operation:
		"open_dialogue":
			if not arguments.is_empty():
				return {"accepted": false, "codes": ["DIALOGUE_ARGUMENTS_INVALID"], "mutated": false}
			if not _dialogue_open:
				_open_mira_dialogue()
			return {"accepted": true, "codes": [], "mutated": false}
		"close_dialogue":
			if not arguments.is_empty():
				return {"accepted": false, "codes": ["DIALOGUE_ARGUMENTS_INVALID"], "mutated": false}
			if _dialogue_open:
				_close_dialogue()
			return {"accepted": true, "codes": [], "mutated": false}
		"acquire_object":
			if arguments != {"object_id": "signal_lens"}:
				return {"accepted": false, "codes": ["PLAYER_ACTION_BINDING_MISMATCH"], "mutated": false}
			return _propose("acquire_object", arguments, "Bootstrap acquire signal lens", handles.get("lens_prop") as Node3D)
		"install_lens":
			if arguments != {"object_id": "signal_lens"}:
				return {"accepted": false, "codes": ["PLAYER_ACTION_BINDING_MISMATCH"], "mutated": false}
			return _propose("install_lens", arguments, "Bootstrap install signal lens", handles.get("lamp_mount") as Node3D)
		"reveal_hint":
			if arguments != {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}:
				return {"accepted": false, "codes": ["REVEAL_BINDING_MISMATCH"], "mutated": false}
			if not _dialogue_open:
				return {"accepted": false, "codes": ["DIALOGUE_REQUIRED"], "mutated": false}
			return _propose_tide_hint()
		_:
			return {"accepted": false, "codes": ["MUTATION_UNSUPPORTED"], "mutated": false}


func _npc_snapshot() -> Dictionary:
	return {"observation": npc_public_observation(), "state_ref": npc_state_ref()}


func _npc_write_result(path: String, report: Dictionary, marker: String, suffix: String = ".result.json") -> void:
	var output_path := ProjectSettings.globalize_path(path) + suffix
	var written := _write_json_atomic(output_path, report)
	print(marker + " " + JSON.stringify({"passed": report.get("passed", false), "written": written, "path": output_path, "input_path": ProjectSettings.globalize_path(path)}))
	get_tree().quit(0 if bool(report.get("passed", false)) and written else 1)


func _npc_apply_setup(input: Dictionary, events: Array, errors: Array) -> void:
	var operations: Variant = input.get("setup_operations", [])
	if not operations is Array:
		errors.append("SETUP_OPERATIONS_SCHEMA_INVALID")
	else:
		for setup in operations:
			if not setup is Dictionary or not setup.has("operation") or not setup.has("arguments"):
				errors.append("SETUP_OPERATION_SCHEMA_INVALID")
				continue
			var operation := str(setup.get("operation", ""))
			var arguments: Variant = setup.get("arguments", {})
			var expected_arguments: Dictionary = {}
			match operation:
				"open_dialogue", "close_dialogue":
					expected_arguments = {}
				"acquire_object", "install_lens":
					expected_arguments = {"object_id": "signal_lens"}
				"reveal_hint":
					expected_arguments = {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
				_:
					errors.append("SETUP_OPERATION_UNSUPPORTED")
					continue
			if not arguments is Dictionary or arguments != expected_arguments:
				errors.append("SETUP_OPERATION_ARGUMENTS_INVALID")
				continue
			var before := npc_state_ref()
			var result := _npc_apply_mutation(setup)
			var after := npc_state_ref()
			events.append({
				"kind": "setup_operation",
				"operation": operation,
				"arguments": expected_arguments,
				"result": {"accepted": bool(result.get("accepted", false)), "codes": result.get("codes", []), "mutated": bool(result.get("mutated", false))},
				"state_ref_before": before,
				"state_ref_after": after,
				"observation": npc_public_observation(),
			})
			if not bool(result.get("accepted", false)):
				errors.append("SETUP_OPERATION_REJECTED")
	var seed_events: Variant = input.get("seed_world_events", [])
	if not seed_events is Array:
		errors.append("SEED_WORLD_EVENTS_SCHEMA_INVALID")
	else:
		for raw_event in seed_events:
			var event_code := ""
			var arguments: Dictionary = {}
			if raw_event is String:
				event_code = str(raw_event)
			elif raw_event is Dictionary:
				event_code = str(raw_event.get("code", raw_event.get("event_code", "")))
				arguments = raw_event.get("arguments", {}) if raw_event.get("arguments", {}) is Dictionary else {}
			else:
				errors.append("SEED_WORLD_EVENT_SCHEMA_INVALID")
				continue
			if event_code != "LENS_UNREACHABLE":
				errors.append("SEED_WORLD_EVENT_UNSUPPORTED")
				continue
			var before := npc_state_ref()
			var result := machine.apply_world_event(event_code, arguments)
			var after := npc_state_ref()
			events.append({
				"kind": "seed_world_event",
				"code": event_code,
				"arguments": arguments,
				"result": {"accepted": bool(result.get("accepted", false)), "codes": result.get("codes", []), "mutated": bool(result.get("mutated", false)), "preconditions": result.get("preconditions", {}), "trace": result.get("trace", {})},
				"state_ref_before": before,
				"state_ref_after": after,
				"observation": npc_public_observation(),
			})
			if not bool(result.get("accepted", false)):
				errors.append("SEED_WORLD_EVENT_REJECTED")
	var desired_dialogue := bool(input.get("in_dialogue", false))
	if desired_dialogue and not _dialogue_open:
		_open_mira_dialogue()
	elif not desired_dialogue and _dialogue_open:
		_close_dialogue()
	_dialogue_open = desired_dialogue

func _run_npc_bootstrap(path: String) -> void:
	var input_hash_before := _npc_input_hash(path)
	var input := _npc_input(path)
	var initial_ref := npc_state_ref()
	var events: Array = []
	var errors: Array = []
	if input.is_empty():
		errors.append("INPUT_MISSING")
	if str(input.get("schema_version", "")) != "npc-engineering/input-1":
		errors.append("SCHEMA_VERSION_INVALID")
	if str(input.get("assignment_id", "")).is_empty():
		errors.append("ASSIGNMENT_ID_MISSING")
	if input.get("decision", null) != null:
		errors.append("BOOTSTRAP_DECISION_MUST_BE_NULL")
	var request_context: Dictionary = input.get("request_context", {}) if input.get("request_context", {}) is Dictionary else {}
	for key in ["session_id", "episode_id", "session_epoch", "request_id", "goal_id", "goal_version"]:
		if not request_context.has(key):
			errors.append("REQUEST_CONTEXT_MISSING_" + key.to_upper())
	var declared_hashes: Dictionary = input.get("source_hashes", {}) if input.get("source_hashes", {}) is Dictionary else {}
	if declared_hashes.has("policy_hash") and not str(declared_hashes.get("policy_hash", "")).is_empty() \
		and str(declared_hashes.get("policy_hash", "")) != npc_policy_hash():
		errors.append("POLICY_HASH_MISMATCH")
	_npc_apply_setup(input, events, errors)
	var snapshot := _npc_snapshot()
	var context := request_context.duplicate(true)
	context["state_ref"] = snapshot["state_ref"]
	context["observation"] = snapshot["observation"]
	context["policy_hash"] = npc_policy_hash()
	context["config_hash"] = npc_config_hash()
	var final_ref := npc_state_ref()
	var input_hash_after := _npc_input_hash(path)
	var preserved := input_hash_before != "" and input_hash_before == input_hash_after
	var source_hashes := _npc_source_hashes(input)
	var report := {
		"engineering_only": true,
		"claim_boundary": "Engineering-only canonical bootstrap, identity binding, and deterministic world-event evidence; no participant, efficacy, or usability claim.",
		"not_evidence_for": ["G4", "usability", "immersion", "affect", "efficacy", "model superiority"],
		"mode": "bootstrap",
		"schema_version": "npc-engineering/input-1",
		"assignment_id": str(input.get("assignment_id", "")),
		"fixture_ref": str(input.get("fixture_ref", "")),
		"source_hashes": source_hashes,
		"actual_state_ref": snapshot["state_ref"],
		"state_ref": snapshot["state_ref"],
		"policy_hash": npc_policy_hash(),
		"observation": snapshot["observation"],
		"context": context,
		"initial_state_sha256": initial_ref["sha256"],
		"initial_state_ref": initial_ref,
		"final_state_ref": final_ref,
		"input_sha256_before": input_hash_before,
		"input_sha256_after": input_hash_after,
		"input_bytes_preserved": preserved,
		"events": events,
		"actions": [],
		"terminal_status": "BOOTSTRAP_APPLIED" if errors.is_empty() else "BOOTSTRAP_REJECTED",
		"passed": not input.is_empty() and errors.is_empty() and preserved,
		"errors": errors,
	}
	_npc_write_result(path, report, "NPC-BOOTSTRAP", ".bootstrap.json")
func _npc_fixture_player_action(mutations: Array, operation: String) -> bool:
	for mutation in mutations:
		if mutation is String:
			var text := str(mutation).to_lower()
			if text.find("fixture-playeraction") != -1 and text.find(operation.to_lower()) != -1:
				return true
		elif mutation is Dictionary:
			var code := str(mutation.get("code", mutation.get("type", ""))).to_lower()
			if code in ["fixture-playeraction", "fixture_player_action"] and str(mutation.get("operation", "")) == operation:
				return true
	return false


func _npc_state_refs_equal(left: Dictionary, right: Dictionary) -> bool:
	return int(left.get("revision", -1)) == int(right.get("revision", -2)) \
		and str(left.get("sha256", "")) == str(right.get("sha256", ""))


func _npc_context_key_equal(left: Dictionary, right: Dictionary, key: String) -> bool:
	if not left.has(key) or not right.has(key):
		return false
	var left_value: Variant = left[key]
	var right_value: Variant = right[key]
	if key == "session_epoch":
		if not (left_value is int or left_value is float) or not (right_value is int or right_value is float):
			return false
		var left_epoch := float(left_value)
		var right_epoch := float(right_value)
		return is_finite(left_epoch) and is_finite(right_epoch) and left_epoch >= 0.0 and right_epoch >= 0.0 \
			and left_epoch == floor(left_epoch) and right_epoch == floor(right_epoch) and left_epoch == right_epoch
	return left_value is String and right_value is String and left_value == right_value


func _npc_context_matches(input: Dictionary, decision: Dictionary, actual: Dictionary) -> bool:
	var context: Dictionary = input.get("request_context", {}) if input.get("request_context", {}) is Dictionary else {}
	for key in ["session_id", "episode_id", "session_epoch", "request_id", "goal_id", "goal_version"]:
		if not _npc_context_key_equal(decision, context, key):
			return false
	if str(decision.get("policy_hash", "")) != npc_policy_hash():
		return false
	var declared_hashes: Dictionary = input.get("source_hashes", {}) if input.get("source_hashes", {}) is Dictionary else {}
	if declared_hashes.has("policy_hash") and not str(declared_hashes.get("policy_hash", "")).is_empty() \
		and str(declared_hashes.get("policy_hash", "")) != npc_policy_hash():
		return false
	var decision_ref: Dictionary = decision.get("state_ref", {}) if decision.get("state_ref", {}) is Dictionary else {}
	var actual_ref: Dictionary = actual.get("state_ref", {}) if actual.get("state_ref", {}) is Dictionary else {}
	return _npc_state_refs_equal(decision_ref, actual_ref)

func _npc_mutation_codes(input: Dictionary) -> Array:
	var values: Variant = input.get("mutations", [])
	if not values is Array:
		return []
	var codes: Array = []
	for mutation in values:
		if mutation is String:
			codes.append(str(mutation).to_lower())
		elif mutation is Dictionary:
			codes.append(str(mutation.get("code", mutation.get("type", ""))).to_lower())
	return codes


func _npc_normalized_result(result: Dictionary) -> Dictionary:
	var codes: Array = result.get("codes", []) if result.get("codes", []) is Array else []
	return {
		"accepted": bool(result.get("accepted", false)),
		"codes": CanonicalState.sorted_unique(codes),
		"mutated": bool(result.get("mutated", false)),
	}


func _npc_redacted_request(input: Dictionary) -> Dictionary:
	var request: Variant = input.get("request", null)
	if not request is Dictionary:
		return {}
	var envelope: Dictionary = request
	var body: Dictionary = envelope.get("body", {}) if envelope.get("body", {}) is Dictionary else {}
	return {
		"sha256": CanonicalState.sha256(envelope),
		"session_id": str(envelope.get("session_id", "")),
		"episode_id": str(envelope.get("episode_id", "")),
		"session_epoch": int(envelope.get("session_epoch", -1)),
		"request_id": str(envelope.get("request_id", "")),
		"goal_id": str(envelope.get("goal_id", "")),
		"goal_version": str(envelope.get("goal_version", "")),
		"state_ref": envelope.get("state_ref", {}),
		"event_kind": str(body.get("event_kind", "")),
		"observation": body.get("observation", {}),
	}


func _npc_execute_engine_decision(input: Dictionary, decision: Dictionary, bound_context: Dictionary, actual_initial: Dictionary, rows: Array, events: Array) -> Dictionary:
	var body: Dictionary = decision.get("body", {}) if decision.get("body", {}) is Dictionary else {}
	var steps: Variant = body.get("steps", [])
	if not steps is Array:
		return {"accepted": false, "status": "ERROR", "codes": ["STEPS_SCHEMA_INVALID"]}
	if steps.is_empty():
		var terminal := npc_client.accept_decision(decision, bound_context, npc_state_ref())
		var terminal_codes: Array = terminal.get("codes", []) if terminal.get("codes", []) is Array else []
		var terminal_status := str(terminal.get("status", "ERROR"))
		events.append({"kind": "terminal", "status": terminal_status, "result": _npc_normalized_result(terminal), "observation": npc_public_observation(), "state_ref": npc_state_ref()})
		return {"accepted": bool(terminal.get("accepted", false)), "status": terminal_status, "codes": terminal_codes}
	var step: Variant = steps[0]
	var before := npc_state_ref()
	var row := {
		"index": 0,
		"step": step,
		"state_ref_before": before,
		"status": "REJECTED",
		"codes": [],
		"observation_before": actual_initial["observation"],
	}
	if not step is Dictionary:
		row["codes"] = ["PLAN_STEP_SCHEMA_INVALID"]
		row["state_ref_after"] = before
		row["observation_after"] = npc_public_observation()
		rows.append(row)
		return {"accepted": false, "status": "ERROR", "codes": row["codes"]}
	var action: Dictionary = step
	var action_id := str(action.get("action_id", ""))
	var operation := str(action.get("operation", ""))
	var execution_mode := str(action.get("execution_mode", ""))
	var arguments: Dictionary = action.get("arguments", {}) if action.get("arguments", {}) is Dictionary else {}
	row["action_id"] = action_id
	row["operation"] = operation
	row["execution_mode"] = execution_mode
	row["arguments"] = arguments
	var accepted := npc_client.accept_decision(decision, bound_context, before)
	var result: Dictionary = accepted.duplicate(true)
	if bool(accepted.get("accepted", false)) and str(accepted.get("kind", "")) == "player_request":
		var waiting := _npc_waiting_action.duplicate(true)
		var waiting_context: Dictionary = waiting.get("context", {}) if waiting.get("context", {}) is Dictionary else {}
		if not _npc_fixture_player_action(input.get("mutations", []), operation):
			result = {"accepted": false, "codes": ["PLAYER_ACTION_REQUIRED"], "mutated": false}
		else:
			var binding_errors := npc_client.validate_action_context(waiting_context, action_id, operation, before)
			if not binding_errors.is_empty():
				result = {"accepted": false, "codes": binding_errors, "mutated": false}
			else:
				result = _npc_apply_mutation({"operation": operation, "arguments": arguments})
				_npc_record_player_action(operation, result)
	elif bool(accepted.get("accepted", false)) and str(accepted.get("kind", "")) == "reveal_hint":
		result = _npc_action_results.get(action_id, {"accepted": false, "codes": ["REVEAL_RESULT_MISSING"], "mutated": false})
	elif bool(accepted.get("accepted", false)) and str(accepted.get("kind", "")) == "dialogue":
		result = {"accepted": true, "codes": ["DIALOGUE_ONLY"], "mutated": false}
	var after := npc_state_ref()
	var normalized := _npc_normalized_result(result)
	var control_codes := _npc_mutation_codes(input)
	var cancellation_control := "cancelled" in control_codes or "cancellation" in control_codes
	var deadline_control := "deadline" in control_codes or "deadline_expired" in control_codes
	var stale_control := "stale_epoch" in control_codes or "epoch_stale" in control_codes or "stale_policy" in control_codes or "policy_stale" in control_codes or "stale_revision" in control_codes or "stale_revision_hash" in control_codes or "revision_stale" in control_codes or "conflict" in control_codes
	row["status"] = "APPLIED" if normalized["accepted"] else ("CANCELLED" if cancellation_control else ("ERROR" if deadline_control else ("STALE" if stale_control or "EPOCH_OR_GENERATION_MISMATCH" in normalized["codes"] or "CURRENT_STATE_CHANGED" in normalized["codes"] else "REJECTED")))
	row["codes"] = normalized["codes"]
	row["result"] = normalized
	row["state_ref_after"] = after
	row["observation_after"] = npc_public_observation()
	rows.append(row)
	events.append({"kind": "action", "action_id": action_id, "operation": operation, "execution_mode": execution_mode, "arguments": arguments, "status": row["status"], "result": normalized, "state_ref_before": before, "state_ref_after": after, "observation": row["observation_after"]})
	return {"accepted": normalized["accepted"], "status": row["status"], "codes": normalized["codes"], "action_id": action_id}
func _run_npc_experiment(path: String) -> void:
	var input_hash_before := _npc_input_hash(path)
	var input := _npc_input(path)
	var errors: Array = []
	var events: Array = []
	var rows: Array = []
	var expected_negative_gates: Array = []
	var initial_ref := npc_state_ref()
	if input.is_empty():
		errors.append("INPUT_MISSING")
	if str(input.get("schema_version", "")) != "npc-engineering/input-1":
		errors.append("SCHEMA_VERSION_INVALID")
	if str(input.get("assignment_id", "")).is_empty():
		errors.append("ASSIGNMENT_ID_MISSING")
	var declared_hashes: Dictionary = input.get("source_hashes", {}) if input.get("source_hashes", {}) is Dictionary else {}
	if declared_hashes.has("policy_hash") and not str(declared_hashes.get("policy_hash", "")).is_empty() \
		and str(declared_hashes.get("policy_hash", "")) != npc_policy_hash():
		errors.append("POLICY_HASH_MISMATCH")
	_npc_apply_setup(input, events, errors)
	var actual_initial := _npc_snapshot()
	var supplied_initial: Variant = input.get("initial_public_snapshot", null)
	if supplied_initial is Dictionary and not supplied_initial.is_empty():
		if supplied_initial.get("observation", {}) != actual_initial["observation"]:
			errors.append("INITIAL_OBSERVATION_MISMATCH")
		var supplied_ref: Dictionary = supplied_initial.get("state_ref", {}) if supplied_initial.get("state_ref", {}) is Dictionary else {}
		if not supplied_ref.is_empty() and not _npc_state_refs_equal(supplied_ref, actual_initial["state_ref"]):
			errors.append("INITIAL_STATE_REF_MISMATCH")
	var mutations: Variant = input.get("mutations", [])
	if not mutations is Array:
		errors.append("MUTATIONS_SCHEMA_INVALID")
		mutations = []
	var controls := _npc_mutation_codes(input)
	var known_controls := ["stale_epoch", "epoch_stale", "stale_policy", "policy_stale", "stale_revision", "stale_revision_hash", "revision_stale", "conflict", "cancelled", "cancellation", "deadline", "deadline_expired", "duplicate", "no_route", "no-route", "fixture-playeraction", "fixture_player_action", "lens_unreachable"]
	for control in controls:
		if control not in known_controls:
			errors.append("MUTATION_CONTROL_UNSUPPORTED_" + control.to_upper())
	var decision_value: Variant = input.get("decision", null)
	var decision: Dictionary = decision_value if decision_value is Dictionary else {}
	if decision.is_empty():
		errors.append("DECISION_SCHEMA_INVALID")
	var decision_body: Dictionary = decision.get("body", {}) if decision.get("body", {}) is Dictionary else {}
	var steps: Array = decision_body.get("steps", []) if decision_body.get("steps", []) is Array else []
	if not decision_body.has("steps") or not decision_body.get("steps", []) is Array:
		errors.append("STEPS_SCHEMA_INVALID")
	var request_context: Dictionary = input.get("request_context", {}) if input.get("request_context", {}) is Dictionary else {}
	var redacted_request := _npc_redacted_request(input)
	if not redacted_request.is_empty():
		for key in ["session_id", "episode_id", "session_epoch", "request_id", "goal_id", "goal_version"]:
			if not _npc_context_key_equal(redacted_request, request_context, key):
				errors.append("REQUEST_CONTEXT_MISMATCH_" + key.to_upper())
		var request_ref: Dictionary = redacted_request.get("state_ref", {}) if redacted_request.get("state_ref", {}) is Dictionary else {}
		if not request_ref.is_empty() and not _npc_state_refs_equal(request_ref, actual_initial["state_ref"]):
			errors.append("REQUEST_STATE_REF_MISMATCH")
	var bound_context: Dictionary = {}
	var bind_result := npc_client.bind_engineering_context(request_context, actual_initial["state_ref"])
	if bool(bind_result.get("accepted", false)):
		bound_context = bind_result.get("context", {})
	else:
		errors.append_array(bind_result.get("codes", []))
	var context_matches := not decision.is_empty() and _npc_context_matches(input, decision, actual_initial)
	var blocking_control := ""
	for control in controls:
		if control in ["stale_epoch", "epoch_stale", "stale_policy", "policy_stale", "stale_revision", "stale_revision_hash", "revision_stale", "conflict", "cancelled", "cancellation", "deadline", "deadline_expired"]:
			blocking_control = control
			break
	if not context_matches and blocking_control.is_empty():
		errors.append("DECISION_CONTEXT_MISMATCH")
	var action_outcome := {"status": "ERROR", "accepted": false, "codes": ["NOT_EXECUTED"]}
	if not decision.is_empty() and not bound_context.is_empty() and blocking_control in ["stale_epoch", "epoch_stale", "stale_policy", "policy_stale", "stale_revision", "stale_revision_hash", "revision_stale", "conflict"]:
		var gate_before := npc_state_ref()
		var controlled := decision.duplicate(true)
		if blocking_control in ["stale_epoch", "epoch_stale"]:
			controlled["session_epoch"] = int(controlled.get("session_epoch", 0)) + 1
		elif blocking_control in ["stale_policy", "policy_stale"]:
			controlled["policy_hash"] = String("0").repeat(64)
		else:
			var stale_ref: Dictionary = controlled.get("state_ref", {}).duplicate(true) if controlled.get("state_ref", {}) is Dictionary else {}
			stale_ref["sha256"] = String("0").repeat(64)
			controlled["state_ref"] = stale_ref
		action_outcome = _npc_execute_engine_decision(input, controlled, bound_context, actual_initial, rows, events)
		var gate_after := npc_state_ref()
		var expected_code := "EPOCH_MISMATCH" if blocking_control in ["stale_epoch", "epoch_stale"] else ("POLICY_HASH_MISMATCH" if blocking_control in ["stale_policy", "policy_stale"] else "STATE_HASH_MISMATCH")
		var gate_pass: bool = not bool(action_outcome.get("accepted", false)) and str(action_outcome.get("status", "")) in ["STALE", "REJECTED"] and str(gate_before["sha256"]) == str(gate_after["sha256"])
		expected_negative_gates.append({"control": blocking_control, "expected_status": "STALE", "observed_status": action_outcome.get("status", ""), "codes": action_outcome.get("codes", []), "expected_code": expected_code, "state_ref_before": gate_before, "state_ref_after": gate_after, "passed": gate_pass})
	elif not decision.is_empty() and not bound_context.is_empty() and blocking_control in ["cancelled", "cancellation"]:
		npc_client.invalidate_pending("cancelled")
		action_outcome = _npc_execute_engine_decision(input, decision, bound_context, actual_initial, rows, events)
		var gate_ref := npc_state_ref()
		var gate_pass: bool = not bool(action_outcome.get("accepted", false)) and str(gate_ref["sha256"]) == str(actual_initial["state_ref"]["sha256"])
		expected_negative_gates.append({"control": blocking_control, "expected_status": "CANCELLED", "observed_status": action_outcome.get("status", ""), "codes": action_outcome.get("codes", []), "state_ref_before": actual_initial["state_ref"], "state_ref_after": gate_ref, "passed": gate_pass})
		var rebound := npc_client.bind_engineering_context(request_context, npc_state_ref())
		if not bool(rebound.get("accepted", false)):
			errors.append_array(rebound.get("codes", []))
		else:
			bound_context = rebound.get("context", {})
	elif not decision.is_empty() and not bound_context.is_empty() and blocking_control in ["deadline", "deadline_expired"]:
		var expired := npc_client.bind_engineering_context(request_context, actual_initial["state_ref"], -1)
		var expired_context: Dictionary = expired.get("context", {}) if expired.get("context", {}) is Dictionary else {}
		action_outcome = _npc_execute_engine_decision(input, decision, expired_context, actual_initial, rows, events)
		var gate_ref := npc_state_ref()
		var gate_pass: bool = not bool(action_outcome.get("accepted", false)) and "DEADLINE_EXPIRED" in action_outcome.get("codes", []) and str(gate_ref["sha256"]) == str(actual_initial["state_ref"]["sha256"])
		expected_negative_gates.append({"control": blocking_control, "expected_status": "ERROR", "observed_status": action_outcome.get("status", ""), "codes": action_outcome.get("codes", []), "expected_code": "DEADLINE_EXPIRED", "state_ref_before": actual_initial["state_ref"], "state_ref_after": gate_ref, "passed": gate_pass})
		var rebound := npc_client.bind_engineering_context(request_context, npc_state_ref())
		if bool(rebound.get("accepted", false)):
			bound_context = rebound.get("context", {})
		else:
			errors.append_array(rebound.get("codes", []))
	elif not decision.is_empty() and not bound_context.is_empty() and context_matches:
		action_outcome = _npc_execute_engine_decision(input, decision, bound_context, actual_initial, rows, events)
	var duplicate_control := ""
	for control in controls:
		if control == "duplicate":
			duplicate_control = control
			break
	if duplicate_control != "" and not decision.is_empty() and not bound_context.is_empty() and bool(action_outcome.get("accepted", false)):
		var duplicate_before := npc_state_ref()
		var duplicate_result := npc_client.accept_decision(decision, bound_context, npc_state_ref())
		var duplicate_after := npc_state_ref()
		var duplicate_codes: Array = duplicate_result.get("codes", []) if duplicate_result.get("codes", []) is Array else []
		expected_negative_gates.append({"control": "duplicate", "expected_status": "DUPLICATE", "observed_status": "DUPLICATE" if not duplicate_result.get("accepted", false) else "APPLIED", "codes": duplicate_codes, "expected_code": "DUPLICATE_ACTION", "state_ref_before": duplicate_before, "state_ref_after": duplicate_after, "passed": not duplicate_result.get("accepted", false) and "DUPLICATE_ACTION" in duplicate_codes and duplicate_before["sha256"] == duplicate_after["sha256"]})
	var no_route_control := "no_route" in controls or "no-route" in controls
	if no_route_control:
		var route_observation: Dictionary = actual_initial["observation"]
		var unreachable_route := not bool(route_observation.get("lens_reachable", false)) and not bool(route_observation.get("lens_carried", false)) and not bool(route_observation.get("signal_restored", false))
		var no_world_step := steps.is_empty() or (steps.size() == 1 and steps[0] is Dictionary and str(steps[0].get("execution_mode", "")) == "dialogue")
		var route_state_unchanged := _npc_state_refs_equal(actual_initial["state_ref"], npc_state_ref())
		var route_held: bool = unreachable_route and no_world_step and route_state_unchanged and action_outcome.get("status", "") in ["NO_ROUTE", "APPLIED"] and bool(action_outcome.get("accepted", false))
		expected_negative_gates.append({"control": "no_route", "expected_status": "NO_CANONICAL_ROUTE", "observed_status": action_outcome.get("status", ""), "codes": action_outcome.get("codes", []), "physical_route_unreachable": unreachable_route, "no_world_step": no_world_step, "state_ref_before": actual_initial["state_ref"], "state_ref_after": npc_state_ref(), "passed": route_held})
	for gate in expected_negative_gates:
		if not bool(gate.get("passed", false)):
			errors.append("EXPECTED_NEGATIVE_GATE_FAILED")
	if not blocking_control.is_empty() and action_outcome.get("status", "") not in ["STALE", "CANCELLED", "ERROR", "REJECTED"]:
		errors.append("NEGATIVE_CONTROL_NOT_ENFORCED")
	if blocking_control.is_empty() and not steps.is_empty() and action_outcome.get("status", "") != "APPLIED":
		errors.append("ACTION_NOT_APPLIED")
	var final_ref := npc_state_ref()
	var input_hash_after := _npc_input_hash(path)
	var preserved := input_hash_before != "" and input_hash_before == input_hash_after
	var expected: Dictionary = input.get("expected", {}) if input.get("expected", {}) is Dictionary else {}
	var goal_reached := bool(npc_public_observation().get("goal_reached", false))
	if expected.has("goal_reached") and bool(expected["goal_reached"]) != goal_reached:
		errors.append("EXPECTED_GOAL_MISMATCH")
	var passed := not input.is_empty() and errors.is_empty() and preserved
	var report := {
		"engineering_only": true,
		"claim_boundary": "Engineering-only canonical NPC decision binding, first-step transition, negative-gate, and deterministic replay evidence; no participant, efficacy, or usability claim.",
		"not_evidence_for": ["G4", "usability", "immersion", "affect", "efficacy", "model superiority"],
		"mode": "experiment",
		"schema_version": "npc-engineering/input-1",
		"assignment_id": str(input.get("assignment_id", "")),
		"fixture_ref": str(input.get("fixture_ref", "")),
		"source_hashes": _npc_source_hashes(input),
		"policy_hash": npc_policy_hash(),
		"request": redacted_request,
		"request_context": request_context,
		"decision_sha256": CanonicalState.sha256(decision) if not decision.is_empty() else "",
		"decision": decision,
		"initial_public_snapshot": actual_initial,
		"initial_state_ref": actual_initial["state_ref"],
		"final_state_ref": final_ref,
		"rows": rows,
		"actions": rows,
		"events": events,
		"expected_negative_gates": expected_negative_gates,
		"observations": [actual_initial["observation"], npc_public_observation()],
		"status": action_outcome.get("status", "ERROR"),
		"terminal_status": "PASSED" if passed else "FAILED",
		"goal_reached": goal_reached,
		"recovery_eligible": passed,
		"recovery_unreachable": not passed,
		"input_sha256_before": input_hash_before,
		"input_sha256_after": input_hash_after,
		"input_bytes_preserved": preserved,
		"passed": passed,
		"errors": errors,
	}
	_npc_write_result(path, report, "NPC-EXPERIMENT")

func _run_npc_engineering_evaluation(path: String) -> void:
	# This lane is explicitly engineering-only. It sends a real loopback request
	# through HTTPRequest and records only redacted envelope metadata and hashes.
	_npc_engineering_events.clear()
	_npc_engineering_errors.clear()
	var initial_ref := npc_state_ref()
	_open_mira_dialogue()
	var sent := npc_client.request_utterance("Help me restore the harbor signal.", npc_public_observation())
	var started := Time.get_ticks_msec()
	var frames_while_waiting := 0
	while sent and _npc_engineering_events.is_empty() and _npc_engineering_errors.is_empty() \
		and Time.get_ticks_msec() - started < 35000:
		await get_tree().process_frame
		frames_while_waiting += 1
	var final_ref := npc_state_ref()
	var report := {
		"schema_version": "npc-engineering/1",
		"mode": "evaluate",
		"command": "godot --headless --path game-track/godot --scene scenes/main_3d.tscn -- --npc-evaluate <path>",
		"path": ProjectSettings.globalize_path(path),
		"initial_state_sha256": initial_ref["sha256"],
		"final_state_sha256": final_ref["sha256"],
		"frames_while_waiting": frames_while_waiting,
		"request_wait_ms": Time.get_ticks_msec() - started,
		"events": _npc_engineering_events.duplicate(true),
		"errors": _npc_engineering_errors.duplicate(),
		"passed": sent and frames_while_waiting > 0 and not _npc_engineering_events.is_empty() and _npc_engineering_errors.is_empty(),
		"claim_boundary": "Engineering transport and Godot freshness-gate evidence only; not efficacy evidence.",
	}
	var written := _write_json_atomic(ProjectSettings.globalize_path(path), report)
	print("NPC-ENGINEERING-EVALUATION " + JSON.stringify({"passed": report["passed"], "written": written, "path": ProjectSettings.globalize_path(path)}))
	get_tree().quit(0 if bool(report["passed"]) and written else 1)


func _run_npc_replay(path: String) -> void:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(ProjectSettings.globalize_path(path))) \
		if FileAccess.file_exists(ProjectSettings.globalize_path(path)) else null
	var actions: Array = parsed.get("actions", []) if parsed is Dictionary else []
	var initial_ref := npc_state_ref()
	var rows: Array = []
	var seen_action_ids: Dictionary = {}
	var passed := parsed is Dictionary and actions.size() > 0
	for action in actions:
		if not action is Dictionary:
			passed = false
			continue
		var action_id := str(action.get("action_id", ""))
		var operation := str(action.get("operation", ""))
		var before := npc_state_ref()
		var expected_ref: Dictionary = action.get("state_ref", {})
		var stale := str(expected_ref.get("sha256", "")) != "" and str(expected_ref.get("sha256", "")) != str(before["sha256"])
		var duplicate := action_id != "" and seen_action_ids.has(action_id)
		if action_id != "":
			seen_action_ids[action_id] = true
		var result: Dictionary = {"accepted": false, "codes": ["UNKNOWN_OPERATION"]}
		if stale:
			result = {"accepted": false, "codes": ["STALE_SESSION_OR_STATE"]}
		elif duplicate:
			result = {"accepted": false, "codes": ["DUPLICATE_ACTION_ID"]}
		else:
			match operation:
				"acquire_object":
					result = _propose("acquire_object", {"object_id": "signal_lens"}, "Replay acquire", handles.get("lens_prop") as Node3D)
				"install_lens":
					result = _propose("install_lens", {"object_id": "signal_lens"}, "Replay install", handles.get("lamp_mount") as Node3D)
				"reveal_hint":
					var args: Dictionary = action.get("arguments", {})
					if args == {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}:
						result = _propose_tide_hint()
					else:
						result = {"accepted": false, "codes": ["REVEAL_BINDING_MISMATCH"]}
				_:
					result = {"accepted": false, "codes": ["UNKNOWN_OPERATION"]}
		var after := npc_state_ref()
		var status := "APPLIED" if bool(result.get("accepted", false)) else "REJECTED"
		if stale:
			status = "STALE"
		elif duplicate:
			status = "DUPLICATE"
		rows.append({
			"action_id": action_id,
			"operation": operation,
			"status": status,
			"state_ref_before": before,
			"state_ref_after": after,
			"codes": result.get("codes", []),
		})
		if stale and str(action.get("expect_status", "")) != "STALE":
			passed = false
		if duplicate and str(action.get("expect_status", "")) != "DUPLICATE":
			passed = false
		if not stale and not duplicate and str(action.get("state_ref", {}).get("sha256", "")) != "" \
			and str(action["state_ref"]["sha256"]) != str(before["sha256"]):
			passed = false
	var final_ref := npc_state_ref()
	var report := {
		"schema_version": "npc-engineering/1",
		"mode": "replay",
		"command": "godot --headless --path game-track/godot --scene scenes/main_3d.tscn -- --npc-replay <path>",
		"path": ProjectSettings.globalize_path(path),
		"initial_state_sha256": initial_ref["sha256"],
		"final_state_sha256": final_ref["sha256"],
		"actions": rows,
		"passed": passed,
		"claim_boundary": "Deterministic recorded-action replay and state-hash evidence only; model is not rerun.",
	}
	var output_path := ProjectSettings.globalize_path(path) + ".result.json"
	var written := _write_json_atomic(output_path, report)
	print("NPC-ENGINEERING-REPLAY " + JSON.stringify({"passed": passed, "written": written, "path": output_path, "input_path": ProjectSettings.globalize_path(path)}))
	get_tree().quit(0 if passed and written else 1)

func _write_json_atomic(path: String, payload: Dictionary) -> bool:
	var parent := path.get_base_dir()
	if parent != "" and DirAccess.make_dir_recursive_absolute(parent) != OK:
		push_error("Cannot create evaluation directory: " + parent)
		return false
	var temporary_path := path + ".tmp"
	if FileAccess.file_exists(temporary_path):
		DirAccess.remove_absolute(temporary_path)
	var handle := FileAccess.open(temporary_path, FileAccess.WRITE)
	if handle == null:
		push_error("Cannot open temporary evaluation file: " + temporary_path)
		return false
	handle.store_string(JSON.stringify(payload, "  ") + "\n")
	handle.flush()
	handle.close()
	var rename_error := DirAccess.rename_absolute(temporary_path, path)
	if rename_error != OK:
		push_error("Atomic evaluation rename failed: %s -> %s" % [temporary_path, path])
		return false
	return true


func _run_screenshot(path: String, stage: String = "arrival") -> void:
	# Development-only public-safe presentation capture. Requires a non-headless
	# display driver; this working shot is not promotable render/G4 evidence.
	var supported := ["arrival", "refusal", "authorized_hint", "ending"]
	if stage not in supported:
		print("SHOT-ERROR " + JSON.stringify({
			"error": "unsupported_stage",
			"stage": stage,
			"supported": supported,
		}))
		get_tree().quit(2)
		return
	player.input_locked = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.set_play_started(true)
	# Screenshot stages explicitly opt into the contextual dock; normal play
	# starts hidden and reveals it only for active dialogue/choices.
	ui.set_contextual_panel_visible(true)
	ui.set_cursor_captured(false)
	var state_hash_before := machine.state_hash()
	_prepare_screenshot_stage(stage)
	var camera := Camera3D.new()
	camera.fov = 58.0
	add_child(camera)
	if stage == "ending":
		camera.global_position = Vector3(-4.0, 3.5, 8.0)
		camera.look_at(Vector3(-4.0, 4.0, 38.0))
	elif stage == "refusal":
		camera.global_position = Vector3(1.0, 2.4, 6.0)
		camera.look_at(Vector3(3.0, 2.0, 11.0))
	else:
		camera.global_position = Vector3(-5.0, 2.6, 4.5)
		camera.look_at(Vector3(5.0, 4.0, 45.0))
	camera.current = true
	for _frame in range(45):
		await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	var absolute_path := ProjectSettings.globalize_path(path)
	var written := _save_png_atomic(image, absolute_path)
	print("SHOT-SAVED " + JSON.stringify({
		"engineering_only": true,
		"not_evidence_for": ["G4", "usability", "immersion", "affect", "efficacy"],
		"stage": stage,
		"path": absolute_path,
		"written": written,
		"width": image.get_width(),
		"height": image.get_height(),
		"state_sha256_before": state_hash_before,
		"state_sha256_after": machine.state_hash(),
	}))
	get_tree().quit(0 if written else 1)


func _prepare_screenshot_stage(stage: String) -> void:
	ui.ledger_line("narration", "Brinewake Dock survived. Offshore, the lighthouse stands dark in the storm.")
	match stage:
		"arrival":
			ui.ledger_line("narration", "Captain Mira watches the dark tower from the end of the dock.")
		"refusal":
			ui.set_portrait_visible(true, "CAPTAIN MIRA | HARBOR WATCH")
			ui.ledger_line("proposal", "Request disclosure of the sealed fact now")
			var before := machine.state_hash()
			var mirror_checks: Array = EvaluationTraceScript.disclosure_checks(
				scenario, machine.state, ["keeper_betrayal"]
			)
			var codes: Array = machine.validate_disclosure(["keeper_betrayal"])
			_last_dashboard_trace = dashboard_trace(
				mirror_checks, EvaluationTraceScript.plan_for("validate_disclosure"),
				EvaluationTraceScript.consistent(mirror_checks, codes)
			)
			refusal_count += 1
			ui.flash("refusal")
			_refusal_feedback(codes)
			assert(machine.state_hash() == before, "refusal screenshot must preserve state")
		"authorized_hint", "ending":
			_propose_acquire()
			_propose_install()
			_propose_tide_hint()
			if stage == "ending":
				# The route's closing deduction is presentation-only; record the
				# same outcome the autoplay route produces through the pure check
				# so the end card reads the full loop. No canonical mutation.
				if not _deduction_confirmed and deduction_is_supported(machine.state, DEDUCTION_CHAIN):
					_deduction_attempts = 1
					_deduction_confirmed = true
				# Same page builder as the live end card; opens on page 1.
				ui.set_end_card_hash(machine.state_hash())
				ui.show_end_card(_episode_end_pages())
	_sync_presentation()
	# Captures stay deterministic: no unread pip, no coach card, no open case
	# file and the hint ladder at rung 0 regardless of the staged commits.
	ui.dismiss_coach_card()
	ui.hide_evidence_board()
	_set_hint_rung(0)
	ui.clear_case_file_unread()


func _save_png_atomic(image: Image, path: String) -> bool:
	var parent := path.get_base_dir()
	if parent != "" and DirAccess.make_dir_recursive_absolute(parent) != OK:
		push_error("Cannot create screenshot directory: " + parent)
		return false
	var temporary_path := path + ".tmp"
	if FileAccess.file_exists(temporary_path):
		DirAccess.remove_absolute(temporary_path)
	if image.save_png(temporary_path) != OK:
		push_error("Cannot save temporary screenshot: " + temporary_path)
		return false
	if DirAccess.rename_absolute(temporary_path, path) != OK:
		push_error("Atomic screenshot rename failed: %s -> %s" % [temporary_path, path])
		return false
	return true


## -------------------------------------------------------------------- smoke

func _run_smoke() -> void:
	# Headless conformance sweep through the same proposal router as live play.
	var checks: Array = []
	var initial_hash := machine.state_hash()

	var codes: Array = machine.validate_disclosure(["keeper_betrayal"])
	checks.append({
		"check": "early_secret_refused_without_mutation",
		"pass": "FORBIDDEN_DISCLOSURE" in codes and machine.state_hash() == initial_hash,
	})

	var gated := machine.apply_operation(
		"reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
	)
	checks.append({
		"check": "early_hint_stage_gated",
		"pass": not gated["accepted"] and "STAGE_GATED_DISCLOSURE" in gated["codes"]
			and machine.state_hash() == initial_hash,
	})

	var premature := machine.apply_operation("install_lens", {"object_id": "signal_lens"})
	checks.append({
		"check": "install_without_lens_refused",
		"pass": not premature["accepted"] and "MISSING_REQUIRED_OBJECT" in premature["codes"],
	})

	var acquire := machine.apply_operation("acquire_object", {"object_id": "signal_lens"})
	checks.append({"check": "lens_acquired", "pass": acquire["accepted"]})

	var install := machine.apply_operation("install_lens", {"object_id": "signal_lens"})
	checks.append({
		"check": "lens_installed_stage_2",
		"pass": install["accepted"] and int(machine.state["quest"]["stage"]) == 2,
	})

	var hint := machine.apply_operation(
		"reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
	)
	checks.append({
		"check": "authorized_hint_disclosed",
		"pass": hint["accepted"] and "tide_marks_hint" in machine.state["facts"],
	})

	_sync_presentation()
	var state_before_fall := machine.state_hash()
	player.global_position = Vector3(0.0, -4.0, 2.0)
	var fall_recovered := player.recover_from_fall_if_needed()
	# Extend the existing presentation check rather than adding a ninth smoke
	# item: the current movement signal must cross-fade a valid rig to walk and
	# back to idle while leaving the canonical state hash untouched. Procedural
	# fallback remains a valid play-safe result when no curated rig is present.
	player.movement_state_changed.emit(true)
	var walk_snapshot := player.get_engineering_snapshot()
	player.movement_state_changed.emit(false)
	var idle_snapshot := player.get_engineering_snapshot()
	var locomotion_animation_ok := true
	if bool(walk_snapshot["player_rig_active"]):
		locomotion_animation_ok = (
			walk_snapshot["player_rig_active_animation"] == "Casual_Walk"
			and walk_snapshot["player_rig_engine_animation"] == "Casual_Walk"
			and bool(walk_snapshot["player_rig_animation_playing"])
			and idle_snapshot["player_rig_active_animation"] == "Idle"
			and idle_snapshot["player_rig_engine_animation"] == "Idle"
			and bool(idle_snapshot["player_rig_animation_playing"])
		)
	# DEF-021 stays inside the existing presentation check so the published 8/8
	# smoke denominator remains stable. Verify that the enabled collider matches
	# the visible deck, contains the single-owned lens anchor, overlaps the quay's
	# west edge, and wraps the hut wall.
	var lens_approach := (
		(handles["world"] as Node3D).get_node_or_null("LampStore/LensApproachDeck")
		as MeshInstance3D
	)
	var lens_approach_ok := false
	if (
		lens_approach != null
		and lens_approach.mesh is BoxMesh
		and lens_approach.get_child_count() > 0
	):
		var approach_body := lens_approach.get_child(0) as StaticBody3D
		if approach_body != null and approach_body.get_child_count() > 0:
			var approach_shape := approach_body.get_child(0) as CollisionShape3D
			if approach_shape != null and approach_shape.shape is BoxShape3D:
				var approach_size := (lens_approach.mesh as BoxMesh).size
				var collider_size := (approach_shape.shape as BoxShape3D).size
				var approach_center := lens_approach.global_position
				var lens_anchor_local := lens_approach.to_local(
					GoldenPathLayout.site_position("lens_pickup")
				)
				lens_approach_ok = (
					not approach_shape.disabled
					and approach_body.collision_layer != 0
					and approach_body.position.is_equal_approx(Vector3.ZERO)
					and approach_shape.position.is_equal_approx(Vector3.ZERO)
					and collider_size.is_equal_approx(approach_size)
					and absf(lens_anchor_local.x) <= approach_size.x * 0.5
					and absf(lens_anchor_local.z) <= approach_size.z * 0.5
					and approach_center.x + approach_size.x * 0.5 >= -9.0
					and approach_center.z + approach_size.z * 0.5 >= 4.0
				)
	checks.append({
		"check": "presentation_sync_and_fall_recovery",
		"pass": (handles["tide_marks"] as Node3D).visible
			and not (handles["lens_prop"] as Node3D).visible
			and lens_approach_ok
			and fall_recovered
			and player.global_position.distance_to(PlayerInvestigator3D.FALL_RECOVERY_POSITION) < 0.01
			and locomotion_animation_ok
			and machine.state_hash() == state_before_fall,
	})

	var save_hash := machine.state_hash()
	checks.append({
		"check": "corrupt_save_rejected",
		"pass": not machine.load_state_if_hash_matches(
			machine.state, "0000000000000000"
		) and machine.state_hash() == save_hash,
	})

	var all_passed := true
	for check in checks:
		if not check["pass"]:
			all_passed = false
	print(JSON.stringify({
		"smoke": "sealed-lighthouse-3d",
		"passed": all_passed,
		"final_state_sha256": machine.state_hash(),
		"checks": checks,
	}, "  "))
	get_tree().quit(0 if all_passed else 1)
