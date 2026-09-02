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

const SCENARIO_PATH := "res://data/sealed_lighthouse.json"
const SAVE_PATH := "user://sl3d_save.json"
const TUTORIAL_SEEN_PATH := "user://sl3d_tutorial_seen.flag"

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
var _evaluate_mode: bool = false
var _play_started: bool = false
var _evaluation_path: String = ""
var _pending_input_feedback: Dictionary = {}
var _input_feedback_samples: Array = []


func _enter_tree() -> void:
	_register_input_actions()


func _ready() -> void:
	var user_args := OS.get_cmdline_user_args()
	_smoke_mode = "--smoke" in user_args
	var evaluate_index := user_args.find("--evaluate")
	_evaluate_mode = evaluate_index != -1
	if _evaluate_mode:
		_evaluation_path = (
			user_args[evaluate_index + 1]
			if evaluate_index + 1 < user_args.size()
			else "user://sealed-lighthouse-3d-engineering-evaluation.json"
		)
	scenario = _load_scenario()
	machine = SealedLighthouseMachine.new(scenario)

	handles = SealedLighthouseWorldBuilder.build(self)
	_objective_beacon = _build_objective_beacon()
	handles["objective_beacon"] = _objective_beacon
	player = PlayerInvestigator3D.create()
	player.position = Vector3(0.0, 0.2, 2.0)
	add_child(player)

	ui = HarborLedgerUI.new()
	add_child(ui)
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
	if _smoke_mode:
		_run_smoke.call_deferred()
		return
	if _evaluate_mode:
		_run_engineering_evaluation.call_deferred(_evaluation_path)
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
	_start_experience(false)


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
		and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED
	):
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)
	if event.is_action_pressed("sl_save"):
		_save_game()
	elif event.is_action_pressed("sl_load"):
		_load_game()
	elif event.is_action_pressed("sl_tutorial"):
		if not _dialogue_open and not episode_over:
			if ui.is_tutorial_open():
				ui.hide_tutorial()
			else:
				_open_tutorial()
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
	if interactable == null or _dialogue_open:
		ui.hide_prompt()
	else:
		ui.show_prompt(interactable.prompt_text)
		if _play_started:
			audio_feedback.play_cue("focus")


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
	if _dialogue_open or episode_over:
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
			ui.ledger_line("narration", "The tower is silent. Rain-dark glass fills the lantern room. The narrow channel cannot be crossed without a signal.")
			if not _lighthouse_observed:
				_lighthouse_observed = true
				ui.ledger_line("hint", "Captain Mira may know what happened to the tower. What she is allowed to reveal is another matter.")
			_complete_input_feedback_probe("lighthouse-observation-ledger-line")
		"tide_marks":
			if "tide_marks_hint" in machine.state["facts"]:
				_finish_episode()
				_complete_input_feedback_probe("episode-completion-feedback")
			else:
				_pending_input_feedback.clear()


func _open_tutorial() -> void:
	ui.hide_prompt()
	player.input_locked = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.set_cursor_captured(false)
	ui.show_tutorial()


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
	var result: Dictionary = machine.apply_operation(operation, arguments)
	if result["accepted"]:
		commit_count += 1
		ui.flash("commit")
		# Reward cadence escalates with earned trust: the first commit is the
		# explained, gentle one; the second is quicker and brighter; from the
		# third on the stinger is quickest and most confident (P-01 legibility
		# first, ceremony reserved for the finale).
		audio_feedback.play_cue("commit_%d" % mini(commit_count, 3))
		_play_verdict_ritual(verdict_target, true)
		if not _first_commit_explained:
			_first_commit_explained = true
			ui.toast("FIRST COMMIT | Only validated entries change state. Watch the solid amber line.")
		elif commit_count == 2:
			ui.toast("ENTRY %d | The ledger remembers the route." % commit_count)
	else:
		refusal_count += 1
		ui.flash("refusal")
		audio_feedback.play_cue("refusal")
		director.play_refusal_pulse()
		_play_verdict_ritual(verdict_target, false)
		if not _first_refusal_explained:
			_first_refusal_explained = true
			ui.toast("FIRST HOLD | State is unchanged. The coral line names the reason and next valid entry.")
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
}
var _holds_by_gate: Dictionary = {}


func gate_for_code(code: String) -> String:
	return str(GATE_BY_CODE.get(code, "POLICY"))


func _record_hold(gate: String) -> void:
	_holds_by_gate[gate] = int(_holds_by_gate.get(gate, 0)) + 1


func _refusal_feedback(codes: Array) -> void:
	# Neutral reason + one world-flavor clause + the concrete next valid entry.
	# Hidden oracle labels never surface; the flavor stays non-alarming (P-02) —
	# the ledger defers, it never punishes. Each hold also names the predicate
	# family that held it so the in-game ledger mirrors the paper's commit gate.
	var next_affordance := _next_affordance_text()
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


func _propose_acquire() -> void:
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
		ui.ledger_commit(commit_count, "Signal lens secured. Retrieval entry validated.")
		ui.ledger_line("narration", "The brass rim gleams cold against your fingers. The harbor signal mount comes to mind.")
		director.set_tension_stage(1)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()


func _propose_install() -> void:
	# SL-GDD-T1 Q2: install requires the lens and quest stage >= 1.
	var result := _propose(
		"install_lens",
		{"object_id": "signal_lens"},
		"Install the lens in the harbor signal mount",
		handles.get("lamp_mount") as Node3D,
	)
	if result["accepted"]:
		ui.ledger_commit(commit_count, "Signal lens installed. An authorized lead is now available.")
		ui.ledger_line("narration", "A low, warm light wakes in the mount. The tower remains dark, but the channel's story opens.")
		director.set_tension_stage(2)
		director.play_commit_glow(handles["lamp_mount"], "MountLight", 2.4)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()


## ----------------------------------------------------------------- dialogue

func _open_mira_dialogue() -> void:
	_dialogue_open = true
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
	_begin_input_feedback_probe("dialogue-choice:" + choice_id)
	match choice_id:
		"ask_lighthouse":
			# W-002: operational fact, already disclosed.
			ui.ledger_line("dialogue", "The light died three days ago. The door may be barred from inside. There has been no answer. That is all we know.")
			_complete_input_feedback_probe("mira-dialogue-ledger-line")
			_show_mira_choices()
		"ask_secret":
			# B-006: the one intended early secret request (keeper_betrayal stays sealed).
			var codes: Array = machine.validate_disclosure(["keeper_betrayal"])
			refusal_count += 1
			ui.flash("refusal")
			audio_feedback.play_cue("refusal")
			director.play_refusal_pulse()
			_play_verdict_ritual(_interactable("mira"), false)
			director.set_tension_stage(2)
			_refusal_feedback(codes)
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


func _propose_tide_hint() -> void:
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
		audio_feedback.play_cue("hint")
		director.set_tension_stage(3)
		var world: Node3D = handles["world"]
		director.play_commit_glow(world.get_node("TideMarks"), "TideGlow", 1.6)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()
	_show_mira_choices()


func _close_dialogue() -> void:
	_dialogue_open = false
	ui.clear_choices()
	ui.set_portrait_visible(false)
	if not _smoke_mode and not _evaluate_mode:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
		ui.set_cursor_captured(true)

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


func _load_game() -> void:
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

	# Objective copy audit: bureaucratic-poetic but concrete — each line names
	# WHO/WHERE and WHY NOW; the beacon marks the same target in-world.
	var objective := "Speak with Captain Mira at the end of the dock | She knows why the channel is closed"
	var phase := "ARRIVAL"
	if _met_mira:
		objective = "Recover the signal lens from the lamp store | The channel cannot open without a signal"
	if hint_known:
		objective = "Inspect the tide marks on the west breakwater | Read when low tide opens the path"
		phase = "TRACE LOGGED"
	elif installed:
		objective = "Return to Captain Mira for the authorized lead | The harbor signal is restored"
		phase = "SIGNAL RESTORED"
	elif not lens_in_store:
		objective = "Install the lens at the northeast harbor mount | Restore the harbor signal"
		phase = "LENS SECURED"
	var inventory: Array = state["player"]["inventory"]
	var exploration_progress := 3 if hint_known else int(state["quest"]["stage"])
	var status := "STAGE %d | INVENTORY: %s\nENTRIES %d | HOLDS %d" % [
		int(state["quest"]["stage"]),
		"SIGNAL LENS" if "signal_lens" in inventory else "EMPTY",
		commit_count,
		refusal_count,
	]
	ui.set_status(objective, status)
	ui.set_progress(exploration_progress, 3, phase)


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


func _finish_episode() -> void:
	if episode_over:
		return
	episode_over = true
	ui.hide_prompt()
	# The tide-route acquisition is the episode's biggest beat: fanfare + commit
	# flash + golden ledger celebration land immediately, then the P-B06 camera
	# (or the reduced-motion static card) carries the close. The tower stays
	# dark and sealed throughout (W-002/D-030) — the payoff is the earned route.
	audio_feedback.play_cue("ending")
	ui.flash("commit")
	ui.ledger_line("commit", "Case complete. Tide route secured; below the third mark, low tide opens the path.")
	ui.ledger_line("narration", "The ledger's final line dries to gold. Harbor light reaches the end of the channel.")
	ui.toast("ACQUIRED | LOW-TIDE ROUTE")
	ui.set_progress(3, 3, "ROUTE SECURED")
	director.play_ending(func() -> void:
		var summary := "\n[color=#F2B84B]THE SEALED LIGHTHOUSE | CASE COMPLETE[/color]\n\n"
		summary += "The lighthouse remains sealed tonight, but every entry in the ledger is valid.\n"
		summary += "The low-tide marks point to the next route.\n"
		summary += _episode_receipt_text()
		summary += "\n[color=#D9D3C4]CONTINUE AT THE NEXT TIDE[/color]"
		# The 'ledger closes' beat: brief dim + case-complete toast, then the end
		# card slides in (reduced motion: immediate card). UI owns the staging.
		ui.play_ledger_close(summary)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.set_cursor_captured(false)
	)


func _episode_receipt_text() -> String:
	# Compact episode receipt: entries N | holds N | state hash <short>. One shared
	# rendering for the live end card and the ending screenshot stage — the
	# counts and hash come straight from the committed snapshot, never invented.
	var receipt := "\n[color=#F2B84B]ENTRIES %d[/color] | [color=#D9685F]HOLDS %d[/color] | FINAL STAGE %d\n" % [
		commit_count, refusal_count, int(machine.state["quest"]["stage"])
	]
	receipt += "[color=#8FA3B2]VALIDATOR RECEIPT | STATE HASH %s...[/color]\n" % machine.state_hash().substr(0, 16)
	receipt += "[color=#8FA3B2]HOLDS BY GATE | %s[/color]\n" % _holds_by_gate_text()
	return receipt


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
	await get_tree().process_frame
	if DisplayServer.get_name() != "headless":
		await RenderingServer.frame_post_draw
	await get_tree().process_frame

	var ui_snapshot := ui.get_engineering_snapshot()
	var audio_snapshot := audio_feedback.get_engineering_snapshot()
	var player_snapshot := player.get_engineering_snapshot()
	var input_feedback_snapshot := _input_feedback_snapshot()
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
	]
	var passed := true
	for check in checks:
		if not check["pass"]:
			passed = false
	var report := {
		"schema_version": "1.1.0",
		"evaluation": "sealed-lighthouse-3d-presentation-engineering",
		"engineering_only": true,
		"not_evidence_for": ["G4", "usability", "immersion", "affect", "efficacy", "browser input latency"],
		"claim_boundary": "Automated presentation invariants and engine-local telemetry wiring only; no participant, neural-model, browser-latency, or gameplay-efficacy measurement.",
		"passed": passed,
		"state_sha256_before": state_hash_before,
		"state_sha256_after": machine.state_hash(),
		"supported_screenshot_stages": ["arrival", "refusal", "authorized_hint", "ending"],
		"ui": ui_snapshot,
		"audio": audio_snapshot,
		"player": player_snapshot,
		"input_feedback": input_feedback_snapshot,
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
			var codes: Array = machine.validate_disclosure(["keeper_betrayal"])
			refusal_count += 1
			ui.flash("refusal")
			_refusal_feedback(codes)
			assert(machine.state_hash() == before, "refusal screenshot must preserve state")
		"authorized_hint", "ending":
			_propose_acquire()
			_propose_install()
			_propose_tide_hint()
			if stage == "ending":
				var summary := "\n[color=#F2B84B]THE SEALED LIGHTHOUSE | CASE COMPLETE[/color]\n\n"
				summary += "Every ledger entry is valid, and the low-tide marks point to the next route.\n"
				summary += _episode_receipt_text()
				ui.show_end_card(summary)
	_sync_presentation()


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
