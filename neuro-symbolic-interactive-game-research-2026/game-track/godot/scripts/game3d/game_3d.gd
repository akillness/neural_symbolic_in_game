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

const SCENARIO_PATH := "res://data/sealed_lighthouse.json"
const SAVE_PATH := "user://sl3d_save.json"

var machine: SealedLighthouseMachine
var scenario: Dictionary
var handles: Dictionary
var player: PlayerInvestigator3D
var ui: HarborLedgerUI
var director: NarrativeDirector
var commit_count: int = 0
var refusal_count: int = 0
var episode_over: bool = false
var _dialogue_open: bool = false
var _smoke_mode: bool = false


func _enter_tree() -> void:
	_register_input_actions()


func _ready() -> void:
	_smoke_mode = "--smoke" in OS.get_cmdline_user_args()
	scenario = _load_scenario()
	machine = SealedLighthouseMachine.new(scenario)

	handles = SealedLighthouseWorldBuilder.build(self)
	player = PlayerInvestigator3D.create()
	player.position = Vector3(0.0, 0.2, 2.0)
	add_child(player)

	ui = HarborLedgerUI.new()
	add_child(ui)
	director = NarrativeDirector.new()
	add_child(director)
	director.setup(handles, player)
	director.cinematic_state_changed.connect(ui.set_letterbox)

	_spawn_interactables()
	player.interact_requested.connect(_on_interact)
	player.focus_changed.connect(_on_focus_changed)
	ui.choice_selected.connect(_on_choice)

	_sync_presentation()
	if _smoke_mode:
		_run_smoke.call_deferred()
		return
	var user_args := OS.get_cmdline_user_args()
	var shot_index := user_args.find("--shot")
	if shot_index != -1 and shot_index + 1 < user_args.size():
		_run_screenshot.call_deferred(user_args[shot_index + 1])
		return

	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	# W-001/W-002: the saved dock, the dark tower.
	ui.ledger_line("narration", "브라인웨이크 부두는 살아남았다. 그러나 앞바다의 등대는 폭풍 속에서 어둡다.")
	director.play_intro(func() -> void:
		ui.ledger_line("narration", "미라 선장이 부두 끝에서 어두운 탑을 지켜보고 있다.")
	)


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
	}
	for action in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
			var event := InputEventKey.new()
			event.physical_keycode = bindings[action]
			InputMap.action_add_event(action, event)


func _unhandled_input(event: InputEvent) -> void:
	if _smoke_mode or episode_over:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		if event.physical_keycode == KEY_ESCAPE:
			Input.mouse_mode = (
				Input.MOUSE_MODE_VISIBLE
				if Input.mouse_mode == Input.MOUSE_MODE_CAPTURED
				else Input.MOUSE_MODE_CAPTURED
			)
	if event.is_action_pressed("sl_save"):
		_save_game()
	elif event.is_action_pressed("sl_load"):
		_load_game()
	elif event.is_action_pressed("sl_motion"):
		var reduced := not director.reduce_motion
		director.reduce_motion = reduced
		ui.reduce_motion = reduced
		ui.toast("모션 감소: " + ("켜짐" if reduced else "꺼짐"))


func _spawn_interactables() -> void:
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
			"position": Vector3(-11.0, 1.0, 1.0),
			"radius": 2.2,
		},
		{
			"id": "lamp_mount",
			"name": "부두 신호등 거치대",
			"prompt": "거치대에 렌즈 설치 제안하기",
			"position": Vector3(7.0, 1.5, 13.5),
			"radius": 2.4,
		},
		{
			"id": "lighthouse_view",
			"name": "봉인된 등대",
			"prompt": "앞바다의 등대 관찰하기",
			"position": Vector3(0.0, 1.0, 15.2),
			"radius": 3.0,
		},
		{
			"id": "tide_marks",
			"name": "조수 표식",
			"prompt": "조수 표식 살펴보기",
			"position": Vector3(-8.5, 0.6, 15.5),
			"radius": 2.4,
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
			# W-002 observation only: the slice never enters the tower.
			ui.ledger_line("narration", "탑은 침묵한다. 등불이 있어야 할 곳에는 비에 젖은 유리뿐이다. 좁은 물길은 신호 없이는 지날 수 없다.")
		"tide_marks":
			if "tide_marks_hint" in machine.state["facts"]:
				_finish_episode()


## ---------------------------------------------------------------- proposals

func _propose(operation: String, arguments: Dictionary, proposal_text: String) -> Dictionary:
	ui.ledger_line("proposal", proposal_text)
	var result: Dictionary = machine.apply_operation(operation, arguments)
	if result["accepted"]:
		commit_count += 1
		ui.flash("commit")
	else:
		refusal_count += 1
		ui.flash("refusal")
		director.play_refusal_pulse()
	return result


func _refusal_feedback(codes: Array) -> void:
	# Neutral reason + next valid affordance; hidden oracle labels never surface.
	var state: Dictionary = machine.state
	var has_lens: bool = "signal_lens" in state["player"]["inventory"]
	var installed: bool = "signal_lens_installed" in state["facts"]
	var next_affordance := "램프 상점에서 신호 렌즈를 회수하자."
	if has_lens and not installed:
		next_affordance = "부두 신호등 거치대에 렌즈를 설치하자."
	elif installed:
		next_affordance = "미라 선장에게 허가된 단서를 묻자."
	for code in codes:
		match code:
			"FORBIDDEN_DISCLOSURE":
				# Canonical early-secret fallback (safe_fallback.text_ko).
				ui.ledger_line("dialogue", scenario["safe_fallback"]["text_ko"])
				ui.ledger_line("refusal", "이 요청은 지금 답할 수 없다. 다음: " + next_affordance)
			"STAGE_GATED_DISCLOSURE":
				ui.ledger_line("dialogue", "「아직 그 이야기를 할 때가 아니야. 순서가 있어.」")
				ui.ledger_line("refusal", "공개 조건이 충족되지 않았다. 다음: " + next_affordance)
			"MISSING_REQUIRED_OBJECT":
				ui.ledger_line("refusal", "설치할 렌즈가 손에 없다. 다음: " + next_affordance)
			"QUEST_STAGE_PRECONDITION":
				ui.ledger_line("refusal", "아직 준비가 되지 않았다. 다음: " + next_affordance)
			"OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE":
				ui.ledger_line("refusal", "지금 여기서는 가져올 수 없다. 다음: " + next_affordance)
			_:
				ui.ledger_line("refusal", "행동이 보류되었다. 다음: " + next_affordance)


func _propose_acquire() -> void:
	# SL-GDD-T1 Q1: collect the reachable signal lens.
	var result := _propose(
		"acquire_object", {"object_id": "signal_lens"}, "신호 렌즈를 회수한다"
	)
	if result["accepted"]:
		# P-B02: brass-outlined acquisition after the commit.
		ui.ledger_line("commit", "신호 렌즈 확보 — 회수 기록이 장부에 남는다.")
		ui.ledger_line("narration", "황동 테두리가 손끝에서 차갑게 빛난다. 부두의 거치대가 떠오른다.")
		director.set_tension_stage(1)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()


func _propose_install() -> void:
	# SL-GDD-T1 Q2: install requires the lens and quest stage >= 1.
	var result := _propose(
		"install_lens", {"object_id": "signal_lens"}, "거치대에 렌즈를 설치한다"
	)
	if result["accepted"]:
		ui.ledger_line("commit", "렌즈 설치 완료 — 허가된 단서가 열렸다.")
		ui.ledger_line("narration", "거치대의 등불이 낮고 따뜻하게 살아난다. 탑은 여전히 어둡지만, 물길의 이야기가 열렸다.")
		director.set_tension_stage(2)
		director.play_commit_glow(handles["lamp_mount"], "MountLight", 2.4)
	else:
		_refusal_feedback(result["codes"])
	_sync_presentation()


## ----------------------------------------------------------------- dialogue

func _open_mira_dialogue() -> void:
	_dialogue_open = true
	ui.hide_prompt()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	ui.set_portrait_visible(true, "미라 선장 — 항만 감시선장")
	# W-003: duty-bounded operational knowledge, no keeper authority.
	ui.ledger_line("dialogue", "「부두를 구해줘서 고맙다. 저 탑이 저러고 있으니, 오늘 밤은 아무도 물길에 못 들어간다.」")
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
			director.play_refusal_pulse()
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
		"미라에게 조수 표식 단서를 요청한다"
	)
	if result["accepted"]:
		# P-B05: one ledger link turns solid; restrained bell, signal glow.
		ui.ledger_line("dialogue", "「좋아. 렌즈를 달았으니 말해주지. 서쪽 방파제의 조수 표식 — 썰물이 세 번째 표식 아래로 내려가면, 바위 사이로 길이 드러난다.」")
		ui.ledger_line("hint", "조수 표식 단서가 장부에 기록되었다.")
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
	if not _smoke_mode:
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


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

	var objective := "꺼진 등대의 사정을 조사한다"
	if hint_known:
		objective = "조수 표식을 살펴 다음 경로를 확인한다"
	elif installed:
		objective = "미라 선장에게 허가된 단서를 묻는다"
	elif not lens_in_store:
		objective = "부두 거치대에 신호 렌즈를 설치한다"
	var inventory: Array = state["player"]["inventory"]
	var status := "단계 %d · 소지품: %s\n커밋 %d · 보류 %d\n[F5] 저장 · [F9] 불러오기 · [M] 모션 감소" % [
		int(state["quest"]["stage"]),
		"신호 렌즈" if "signal_lens" in inventory else "없음",
		commit_count,
		refusal_count,
	]
	ui.set_status(objective, status)


func _finish_episode() -> void:
	if episode_over:
		return
	episode_over = true
	ui.hide_prompt()
	director.play_ending(func() -> void:
		var summary := "\n[color=#F2B84B]봉인된 등대 — 에피소드 종료[/color]\n\n"
		summary += "등대는 오늘 밤도 봉인된 채로 남는다. 그러나 장부에는 유효한 기록만 남았고,\n"
		summary += "썰물의 표식이 다음 경로를 가리킨다.\n\n"
		summary += "커밋 %d · 보류 %d · 최종 단계 %d\n" % [
			commit_count, refusal_count, int(machine.state["quest"]["stage"])
		]
		summary += "[color=#6b7b88]검사기 영수증 — 상태 해시 %s[/color]\n" % machine.state_hash().substr(0, 16)
		summary += "\n[color=#D9D3C4]— 다음 물때에 계속 —[/color]"
		ui.show_end_card(summary)
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	)


func _run_screenshot(path: String) -> void:
	# Development-only presentation verification capture. Requires a non-headless
	# display driver; this is a working shot, not promotable render evidence.
	player.input_locked = true
	ui.ledger_line("narration", "브라인웨이크 부두는 살아남았다. 그러나 앞바다의 등대는 폭풍 속에서 어둡다.")
	ui.ledger_line("proposal", "신호 렌즈를 회수한다")
	ui.ledger_line("commit", "신호 렌즈 확보 — 회수 기록이 장부에 남는다.")
	var camera := Camera3D.new()
	camera.fov = 58.0
	add_child(camera)
	camera.global_position = Vector3(-5.0, 2.6, 4.5)
	camera.look_at(Vector3(5.0, 4.0, 45.0))
	camera.current = true
	for _frame in range(45):
		await get_tree().process_frame
	var image := get_viewport().get_texture().get_image()
	image.save_png(path)
	print("SHOT-SAVED " + path)
	get_tree().quit(0)


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
