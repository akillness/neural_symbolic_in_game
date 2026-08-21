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
	ui.ledger_line("narration", "브라인웨이크 부두는 살아남았다. 그러나 앞바다의 등대는 폭풍 속에서 어둡다.")
	director.play_intro(func() -> void:
		ui.ledger_line("narration", "미라 선장이 부두 끝에서 어두운 탑을 지켜보고 있다.")
		# First-session clarity: the concrete first objective lands the moment
		# control returns (intro ≈4.6 s, instant under reduced motion), inside
		# the ~6 s onboarding window. The amber beacon marks the same target.
		ui.ledger_line("hint", "먼저 부두 끝의 미라 선장에게 말을 걸자 — 황색 빛기둥이 목표를 가리킨다.")
		# First session only: the onboarding folio opens itself, then [T] reopens it.
		if not FileAccess.file_exists(TUTORIAL_SEEN_PATH):
			var flag := FileAccess.open(TUTORIAL_SEEN_PATH, FileAccess.WRITE)
			if flag != null:
				flag.store_string("seen")
				flag.close()
			_open_tutorial()
		else:
			ui.toast("목표: 미라 선장에게 말 걸기 — 황색 빛기둥을 따라가라.")
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
	ui.toast("모션 감소: " + ("켜짐" if reduced else "꺼짐"))


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
		ui.toast("음향: 켜짐")
		return
	_toggle_audio()


func _toggle_audio() -> void:
	var muted := audio_feedback.toggle_muted()
	_sync_audio_state()
	if not muted:
		audio_feedback.play_cue("start")
	ui.toast("음향: " + ("꺼짐" if muted else "켜짐"))


func _sync_audio_state() -> void:
	ui.set_audio_state(audio_feedback.is_unlocked(), audio_feedback.is_muted())


func _on_footstep_requested(step_index: int) -> void:
	# Steady-walk path: pick between the two literal cue names instead of
	# formatting a String per stride.
	audio_feedback.play_cue("step_0" if step_index % 2 == 0 else "step_1")


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
	# Golden-path pacing at WALK_SPEED 4.2 m/s (straight-line, trigger-zone edge
	# to trigger-zone edge; real times run slightly longer around props):
	#   spawn(0,2) → Mira(3,11)        ≈  6.9 m ≈ 1.6 s
	#   Mira → lens(-11,1)             ≈ 11.8 m ≈ 2.8 s
	#   lens → mount(7,13.5)           ≈ 16.5 m ≈ 3.9 s   (longest leg, < 6 s)
	#   mount → Mira                   overlap  ≈ 0.5 s   (zones adjoin)
	#   Mira → tide marks(-8.5,15.5)   ≈  7.2 m ≈ 1.7 s
	# Total pure walking ≈ 10–12 s across the 8–12 min episode target.
	# Loop shape: S-center → NE → SW → NE → NW; no leg exceeds ~3.9 s and no
	# revisit happens without a new commit in between (no dead backtracking).
	# The sealed lighthouse_view sits at the NE rail on the mount→Mira return:
	# the mount zone masks it while installing (nearest-wins focus), then the
	# mount interactable disables after the install commit and the view ring
	# becomes the nearest focus on the walk back — the player meets the sealed
	# tower (and its nudge toward Mira's forbidden question) mid-loop, before
	# the tide-marks finale (W-002: observed, never entered).
	var world: Node3D = handles["world"]
	var specs := [
		{
			"id": "mira",
			"name": "미라 선장",
			"prompt": "미라 선장에게 말 걸기",
			"position": Vector3(3.0, 1.0, 11.0),
			"radius": 2.6,
		},
		{
			"id": "lens_pickup",
			"name": "신호 렌즈",
			"prompt": "신호 렌즈 조사하기",
			# Prop sits past the dock edge (x=-11 vs planks ending at x=-9):
			# radius 2.8 leaves ≈0.6 m of standable trigger band on the planks
			# instead of the ≈5 cm sliver the old 2.2 radius allowed.
			"position": Vector3(-11.0, 1.0, 1.0),
			"radius": 2.8,
		},
		{
			"id": "lamp_mount",
			"name": "부두 신호등 거치대",
			"prompt": "거치대에 렌즈 설치 제안하기",
			"position": Vector3(7.0, 1.5, 13.5),
			"radius": 2.6,
		},
		{
			"id": "lighthouse_view",
			"name": "봉인된 등대",
			"prompt": "앞바다의 등대 관찰하기",
			# Moved from mid-rail (0, 15.2) onto the NE rail so it lies on the
			# mount→Mira return leg; radius 2.6 keeps it inside the rail band.
			"position": Vector3(5.4, 1.0, 14.8),
			"radius": 2.6,
		},
		{
			"id": "tide_marks",
			"name": "조수 표식",
			"prompt": "조수 표식 살펴보기",
			"position": Vector3(-8.5, 0.6, 15.5),
			"radius": 2.6,
		},
	]
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


func _on_interact(interaction_id: String) -> void:
	if _dialogue_open or episode_over:
		return
	match interaction_id:
		"mira":
			_open_mira_dialogue()
		"lens_pickup":
			_propose_acquire()
		"lamp_mount":
			_propose_install()
		"lighthouse_view":
			# W-002 observation only: the slice never enters the tower. The tower
			# stays dark and sealed; the first look nudges the player toward the
			# forbidden question at Mira — the intended refusal teaching moment.
			ui.ledger_line("narration", "탑은 침묵한다. 등불이 있어야 할 곳에는 비에 젖은 유리뿐이다. 좁은 물길은 신호 없이는 지날 수 없다.")
			if not _lighthouse_observed:
				_lighthouse_observed = true
				ui.ledger_line("hint", "미라 선장이라면 저 탑의 사정을 알지도 모른다 — 무엇을 물어도 되는지는 별개의 문제다.")
		"tide_marks":
			if "tide_marks_hint" in machine.state["facts"]:
				_finish_episode()


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
			ui.toast("목표: 미라 선장에게 말 걸기 — 황색 빛기둥을 따라가라.")


## ---------------------------------------------------------------- proposals

func _propose(
	operation: String,
	arguments: Dictionary,
	proposal_text: String,
	verdict_target: Node3D = null,
) -> Dictionary:
	ui.ledger_line("proposal", proposal_text)
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
			ui.toast("첫 기록 — 검증을 통과한 항목만 상태를 바꾼다. 장부의 황색 실선을 보라.")
		elif commit_count == 2:
			ui.toast("기록 %d — 장부가 경로를 기억한다." % commit_count)
	else:
		refusal_count += 1
		ui.flash("refusal")
		audio_feedback.play_cue("refusal")
		director.play_refusal_pulse()
		_play_verdict_ritual(verdict_target, false)
		if not _first_refusal_explained:
			_first_refusal_explained = true
			ui.toast("첫 보류 — 상태는 그대로다. 산호선이 이유와 다음 유효 항목을 알려준다.")
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
	# Mirrors _next_affordance_text ordering exactly — one honest mapping from
	# the committed snapshot to the node the repair-hint blink should mark.
	var state: Dictionary = machine.state
	var has_lens: bool = "signal_lens" in state["player"]["inventory"]
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	if hint_known:
		return handles.get("tide_marks") as Node3D
	if installed:
		return _interactable("mira")
	if has_lens:
		return handles.get("lamp_mount") as Node3D
	if not _met_mira:
		return _interactable("mira")
	return handles.get("lens_prop") as Node3D


func _next_affordance_text() -> String:
	# Single source for "다음:" strings — every refusal path routes through
	# _refusal_feedback, so this is the one ordering to keep honest. Mirrors
	# the committed snapshot plus the presentation-only met-Mira flag.
	var state: Dictionary = machine.state
	var has_lens: bool = "signal_lens" in state["player"]["inventory"]
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	if hint_known:
		return "서쪽 방파제의 조수 표식을 살펴보자."
	if installed:
		return "미라 선장에게 허가된 단서를 묻자."
	if has_lens:
		return "부두 신호등 거치대에 렌즈를 설치하자."
	if not _met_mira:
		return "부두 끝의 미라 선장에게 말을 걸자."
	return "램프 상점에서 신호 렌즈를 회수하자."


func _refusal_feedback(codes: Array) -> void:
	# Neutral reason + one world-flavor clause + the concrete next valid entry.
	# Hidden oracle labels never surface; the flavor stays non-alarming (P-02) —
	# the ledger defers, it never punishes.
	var next_affordance := _next_affordance_text()
	for code in codes:
		match code:
			"FORBIDDEN_DISCLOSURE":
				# Canonical early-secret fallback (safe_fallback.text_ko).
				ui.ledger_line("dialogue", scenario["safe_fallback"]["text_ko"])
				ui.ledger_refusal("이 요청은 지금 답할 수 없다 — 장부가 답을 미룬다.", next_affordance)
			"STAGE_GATED_DISCLOSURE":
				ui.ledger_line("dialogue", "「아직 그 이야기를 할 때가 아니야. 순서가 있어.」")
				ui.ledger_refusal("공개 조건이 충족되지 않았다 — 장부는 순서를 지킨다.", next_affordance)
			"MISSING_REQUIRED_OBJECT":
				ui.ledger_refusal("설치할 렌즈가 손에 없다 — 장부는 빈손을 기록하지 않는다.", next_affordance)
			"QUEST_STAGE_PRECONDITION":
				ui.ledger_refusal("아직 준비가 되지 않았다 — 물때가 오지 않은 항목이다.", next_affordance)
			"OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE":
				ui.ledger_refusal("지금 여기서는 가져올 수 없다 — 닿지 않는 것은 장부 밖이다.", next_affordance)
			_:
				ui.ledger_refusal("항목이 보류되었다 — 장부가 답을 미룬다.", next_affordance)
	# RitualVfx repair-hint blink marks the same next-valid target in-world.
	_play_repair_hint(_next_affordance_target())


func _propose_acquire() -> void:
	# SL-GDD-T1 Q1: collect the reachable signal lens.
	var result := _propose(
		"acquire_object",
		{"object_id": "signal_lens"},
		"신호 렌즈를 회수한다",
		handles.get("lens_prop") as Node3D,
	)
	if result["accepted"]:
		# P-B02: brass-outlined acquisition after the commit. The bright pickup
		# chime rides above the commit rise so "got the object" reads distinctly
		# from "the ledger accepted it".
		audio_feedback.play_cue("pickup")
		ui.ledger_commit(commit_count, "신호 렌즈 확보. 회수 항목, 검증 통과.")
		ui.ledger_line("narration", "황동 테두리가 손끝에서 차갑게 빛난다. 부두의 거치대가 떠오른다.")
		director.set_tension_stage(1)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()


func _propose_install() -> void:
	# SL-GDD-T1 Q2: install requires the lens and quest stage >= 1.
	var result := _propose(
		"install_lens",
		{"object_id": "signal_lens"},
		"거치대에 렌즈를 설치한다",
		handles.get("lamp_mount") as Node3D,
	)
	if result["accepted"]:
		ui.ledger_commit(commit_count, "신호 렌즈 설치. 허가된 단서 항목이 열렸다.")
		ui.ledger_line("narration", "거치대의 등불이 낮고 따뜻하게 살아난다. 탑은 여전히 어둡지만, 물길의 이야기가 열렸다.")
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
	ui.set_portrait_visible(true, "미라 선장 · 항만 감시")
	# W-003: duty-bounded operational knowledge, no keeper authority. Greeting
	# beats are presentation-only and branch on the committed snapshot; every
	# choice id and flow below stays untouched.
	var state: Dictionary = machine.state
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	if first_meeting:
		# Beat (a) — her account of the storm night and the sealing (W-001/W-002):
		# operational facts only; the WHY stays outside her authority (F-H01).
		ui.ledger_line("dialogue", "「부두를 구해줘서 고맙다. 그 불이 번졌으면 장부째 바다에 가라앉을 뻔했지.」")
		ui.ledger_line("dialogue", "「탑은 사흘째 어둡다. 폭풍 한가운데서 등불이 죽었고, 신호를 두 번 보냈지만 두 번 다 어둠뿐이었다. 장부에는 한 줄만 남았지 — 봉인.」")
		ui.ledger_line("dialogue", "「그래서 오늘 밤은 아무도 물길에 못 들어간다. 항만 감시는 확인된 것만 말한다. 이 항구가 살아남은 방식이다.」")
	elif hint_known:
		# Beat (c) — quiet epilogue: the harbor survives on valid entries only.
		ui.ledger_line("dialogue", "「장부를 봐라. 오늘 밤 남은 건 전부 유효한 항목뿐이다. 이 항구는 그런 밤들을 쌓아서 버텨 왔어.」")
	elif installed:
		# Beat (b) — guarded hope after the lens install: she almost writes hope
		# into the ledger, but the ledger only takes what is verified.
		ui.ledger_line("dialogue", "「거치대 불빛이 물길 입구까지 닿더군. …희망이라고 적을 뻔했다. 장부는 확인된 것만 받으니, 아직은 적지 않겠다.」")
	else:
		ui.ledger_line("dialogue", "「아직 물때는 기다려주지 않는다. 저 탑이 저러고 있으니, 오늘 밤은 아무도 물길에 못 들어간다.」")
	_show_mira_choices()


func _show_mira_choices() -> void:
	var state: Dictionary = machine.state
	var installed: bool = "signal_lens_installed" in state["facts"]
	var hint_known: bool = "tide_marks_hint" in state["facts"]
	var choices: Array = []
	if not hint_known:
		choices.append({"id": "ask_lighthouse", "text": "등대에 무슨 일이 있었죠?"})
		choices.append({"id": "ask_secret", "text": "등대지기가 숨기는 게 있죠? 말해줘요."})
		choices.append({"id": "ask_tide", "text": "조수 표식에 대해 알려줘요."})
	else:
		choices.append({"id": "ask_after", "text": "이제 어디로 가야 하죠?"})
	choices.append({"id": "leave", "text": "물러난다"})
	ui.show_choices(choices)


func _on_choice(choice_id: String) -> void:
	if not _dialogue_open:
		return
	match choice_id:
		"ask_lighthouse":
			# W-002: operational fact, already disclosed.
			ui.ledger_line("dialogue", "「사흘 전부터 등불이 죽었다. 안에서 문을 걸어 잠갔는지, 응답이 없어. 물길 표지는 그게 전부다.」")
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
			_show_mira_choices()
		"ask_tide":
			_propose_tide_hint()
		"ask_after":
			ui.ledger_line("dialogue", "「썰물 표식을 따라가라. 다음 물때가 길을 열 거다. 탑은… 그때 다시 이야기하지.」")
			_show_mira_choices()
		"leave":
			_close_dialogue()


func _propose_tide_hint() -> void:
	# SL-GDD-T1 Q2-HINT: stage >= 2 and Mira knows the fact.
	var result := _propose(
		"reveal_hint",
		{"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
		"미라에게 조수 표식 단서를 요청한다",
		_interactable("mira"),
	)
	if result["accepted"]:
		# P-B05: one ledger link turns solid; restrained bell, signal glow.
		ui.ledger_line("dialogue", "「좋아. 렌즈를 달았으니 말해주지. 서쪽 방파제의 조수 표식 — 썰물이 세 번째 표식 아래로 내려가면, 바위 사이로 길이 드러난다.」")
		ui.ledger_commit(commit_count, "조수 표식 단서 공개. 허가 확인, 항목 유효.")
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
	ui.toast("저장됨 — 상태 해시 " + machine.state_hash().substr(0, 12) + "…")


func _load_game() -> void:
	if not FileAccess.file_exists(SAVE_PATH):
		ui.toast("저장 파일이 없다.")
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(SAVE_PATH))
	if not (parsed is Dictionary) or not parsed.has("state") or not parsed.has("state_sha256"):
		ui.toast("저장 파일을 읽을 수 없다 — 불러오기 거절.")
		return
	if machine.load_state_if_hash_matches(parsed["state"], parsed["state_sha256"]):
		ui.toast("불러옴 — 손상 검사 통과.")
		_sync_presentation()
	else:
		# GDI-02: a corrupt save must never become authoritative.
		ui.toast("저장 해시 불일치 — 불러오기 거절, 현재 상태 유지.")


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
	var objective := "부두 끝의 미라 선장에게 말을 건다 — 물길이 닫힌 이유를 아는 사람"
	var phase := "도착 · ARRIVAL"
	if _met_mira:
		objective = "램프 상점에서 신호 렌즈를 회수한다 — 신호 없이는 물길이 열리지 않는다"
	if hint_known:
		objective = "서쪽 방파제의 조수 표식을 살핀다 — 썰물이 길을 여는 시각을 읽는다"
		phase = "단서 기록 · TRACE"
	elif installed:
		objective = "미라 선장에게 돌아가 허가된 단서를 묻는다 — 신호가 살았으니 말할 수 있다"
		phase = "신호 복구 · SIGNAL"
	elif not lens_in_store:
		objective = "부두 북동쪽 거치대에 렌즈를 설치한다 — 항구 신호부터 살린다"
		phase = "렌즈 확보 · LENS"
	var inventory: Array = state["player"]["inventory"]
	var exploration_progress := 3 if hint_known else int(state["quest"]["stage"])
	var status := "상태 단계 %d · 소지품: %s\n기록 %d · 보류 %d\n장부는 검증을 통과한 항목만 받아들인다." % [
		int(state["quest"]["stage"]),
		"신호 렌즈" if "signal_lens" in inventory else "없음",
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
	ui.ledger_line("commit", "기록 완결 — 조수 항로 확보. 세 번째 표식 아래, 썰물이 길을 연다.")
	ui.ledger_line("narration", "장부의 마지막 줄이 황금빛으로 마른다. 부두의 불빛이 물길 끝까지 이어진다.")
	ui.toast("획득: 썰물 항로 — 이번 밤의 가장 큰 기록.")
	ui.set_progress(3, 3, "항로 확보 · ROUTE")
	director.play_ending(func() -> void:
		var summary := "\n[color=#F2B84B]봉인된 등대 — 에피소드 종료[/color]\n\n"
		summary += "등대는 오늘 밤도 봉인된 채로 남는다. 그러나 장부에는 유효한 항목만 남았고,\n"
		summary += "썰물의 표식이 다음 경로를 가리킨다.\n"
		summary += _episode_receipt_text()
		summary += "\n[color=#D9D3C4]— 다음 물때에 계속 —[/color]"
		# The 'ledger closes' beat: brief dim + 기록 완결 toast, then the end
		# card slides in (reduced motion: immediate card). UI owns the staging.
		ui.play_ledger_close(summary)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
		ui.set_cursor_captured(false)
	)


func _episode_receipt_text() -> String:
	# Compact episode receipt: 기록 N · 보류 N · 상태 해시 <short>. One shared
	# rendering for the live end card and the ending screenshot stage — the
	# counts and hash come straight from the committed snapshot, never invented.
	var receipt := "\n[color=#F2B84B]기록 %d[/color] · [color=#D9685F]보류 %d[/color] · 최종 단계 %d\n" % [
		commit_count, refusal_count, int(machine.state["quest"]["stage"])
	]
	receipt += "[color=#8FA3B2]검사기 영수증 — 상태 해시 %s…[/color]\n" % machine.state_hash().substr(0, 16)
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
	var ui_snapshot := ui.get_engineering_snapshot()
	var audio_snapshot := audio_feedback.get_engineering_snapshot()
	var player_snapshot := player.get_engineering_snapshot()
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
			"check": "player_world_changes_route_through_proposals",
			"pass": player_snapshot["world_change_boundary"].begins_with("interact_requested"),
		},
	]
	var passed := true
	for check in checks:
		if not check["pass"]:
			passed = false
	var report := {
		"schema_version": "1.0.0",
		"evaluation": "sealed-lighthouse-3d-presentation-engineering",
		"engineering_only": true,
		"not_evidence_for": ["G4", "usability", "immersion", "affect", "efficacy"],
		"claim_boundary": "Automated presentation invariants only; no participant, neural-model, or gameplay efficacy measurement.",
		"passed": passed,
		"state_sha256_before": state_hash_before,
		"state_sha256_after": machine.state_hash(),
		"supported_screenshot_stages": ["arrival", "refusal", "authorized_hint", "ending"],
		"ui": ui_snapshot,
		"audio": audio_snapshot,
		"player": player_snapshot,
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
	ui.ledger_line("narration", "브라인웨이크 부두는 살아남았다. 그러나 앞바다의 등대는 폭풍 속에서 어둡다.")
	match stage:
		"arrival":
			ui.ledger_line("narration", "미라 선장이 부두 끝에서 어두운 탑을 지켜보고 있다.")
		"refusal":
			ui.set_portrait_visible(true, "미라 선장 · 항만 감시")
			ui.ledger_line("proposal", "봉인된 사실을 지금 공개해 달라고 요청한다")
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
				var summary := "\n[color=#F2B84B]봉인된 등대 — 에피소드 종료[/color]\n\n"
				summary += "장부에는 유효한 항목만 남았고, 썰물의 표식이 다음 경로를 가리킨다.\n"
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
	checks.append({
		"check": "presentation_sync_reads_snapshot",
		"pass": (handles["tide_marks"] as Node3D).visible
			and not (handles["lens_prop"] as Node3D).visible,
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
