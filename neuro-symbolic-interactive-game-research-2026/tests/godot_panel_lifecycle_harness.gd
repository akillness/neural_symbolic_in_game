extends SceneTree

const HarborLedgerUI = preload("res://scripts/game3d/harbor_ledger_ui.gd")
const Game3D = preload("res://scripts/game3d/game_3d.gd")
const NarrativeDirector = preload("res://scripts/game3d/narrative_director.gd")
const SealedLighthouseMachine = preload("res://scripts/sealed_lighthouse_machine.gd")

var _failures: Array[String] = []
var _selected_choice := ""
var _selected_count := 0
var _ui: HarborLedgerUI

func _set_viewport_size(size: Vector2) -> void:
	_ui.get_viewport().size = size
	await process_frame
	await process_frame


func _expect_rect_inside(rect: Rect2, container: Rect2, message: String) -> void:
	_expect(rect.size.x > 0.0 and rect.size.y > 0.0, message + " has no area")
	_expect(container.encloses(rect), message + " rect=%s container=%s" % [rect, container])


func _open_authored_mira_choices() -> Game3D:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string("res://data/sealed_lighthouse.json"))
	var scenario: Dictionary = parsed as Dictionary
	var controller := Game3D.new()
	controller.scenario = scenario
	controller.machine = SealedLighthouseMachine.new(scenario)
	controller.ui = _ui
	controller._dialogue_open = true
	controller.call("_show_mira_choices")
	return controller


func _click_button(button: Button) -> void:
	# Godot headless has no browser pointer queue; geometry proves the hit target,
	# then the public Button press path proves the authored signal contract.
	button.pressed.emit()
	await process_frame


func _assert_case_file_guard(viewport_size: Vector2) -> void:
	await _set_viewport_size(viewport_size)
	_ui.show_evidence_board(
		[
			{"id": "LENS", "filled": false, "sealed": false, "label": "Not yet in the ledger", "why": ""},
			{"id": "MOUNT", "filled": false, "sealed": false, "label": "Not yet in the ledger", "why": ""},
			{"id": "LEAD", "filled": false, "sealed": false, "label": "Not yet in the ledger", "why": ""},
			{"id": "SEALED", "filled": false, "sealed": true, "label": "A sealed entry", "why": ""},
		],
		{"filled": 0, "total": 3}, [], "Recover the signal lens"
	)
	await process_frame
	_expect(_ui.is_evidence_board_open(), "case-file guard did not open")
	_expect(_ui._evidence_cards_box.get_child_count() == 4, "case-file guard lost one of four cards")
	_expect(_ui._evidence_hint_label.visible, "case-file guard hid the close/footer instruction")
	_expect_rect_inside(
		_ui._evidence_panel.get_global_rect(),
		Rect2(Vector2.ZERO, viewport_size),
		"case-file guard panel",
	)
	_ui.hide_evidence_board()


func _run_mira_responsive_regression() -> void:
	_ui.choice_selected.connect(func(choice_id: String) -> void:
		_selected_choice = choice_id
		_selected_count += 1
	)
	for viewport_size in [Vector2(1400.0, 900.0), Vector2(344.0, 720.0), Vector2(390.0, 844.0)]:
		await _set_viewport_size(viewport_size)
		_ui.set_play_started(true)
		_ui.set_portrait_visible(true, "CAPTAIN MIRA | HARBOR WATCH")
		# Native headless exercises the authored Ask-Captain-Mira row; the browser
		# adds the capability row under the same source condition.
		_ui.show_npc_input(true)
		_expect(_ui._npc_input_row.visible, "Mira operator form is not present")
		if OS.has_feature("web"):
			_expect(_ui._npc_capability_row.visible, "Web Mira capability row is not present")
		_expect(_ui._npc_status_label.visible, "Mira operator status is not present")
		var controller := _open_authored_mira_choices()
		await process_frame
		_expect(_ui.choice_count() == 4, "actual Mira authored choice list was not opened")
		var first := _ui._choice_box.get_child(0) as Button
		_expect(first.text == "What happened to the lighthouse?", "first authored Mira choice drifted")
		_expect(first.visible and not first.disabled, "first authored Mira choice is not actionable")
		var viewport_rect := Rect2(Vector2.ZERO, viewport_size)
		_expect_rect_inside(first.get_global_rect(), viewport_rect, "first authored Mira choice")
		for child in _ui._choice_box.get_children():
			var choice_button := child as Button
			_ui._choice_scroll.ensure_control_visible(choice_button)
			await process_frame
			_expect_rect_inside(
				choice_button.get_global_rect(),
				_ui._choice_scroll.get_global_rect(),
				"scroll-to-view authored Mira choice '%s'" % choice_button.text,
			)
			_expect_rect_inside(choice_button.get_global_rect(), viewport_rect, "viewport authored Mira choice")
		_ui._choice_scroll.ensure_control_visible(first)
		await process_frame
		_selected_choice = ""
		_selected_count = 0
		var state_before := controller.machine.state_hash()
		await _click_button(first)
		_expect(_selected_count == 1, "real click did not emit exactly one choice signal")
		_expect(_selected_choice == "ask_lighthouse", "real click emitted the wrong authored choice id")
		_expect(controller.machine.state_hash() == state_before, "ordinary choice click mutated canonical state")
		controller.free()
		_ui.clear_choices()
		_ui.show_npc_input(false)
		_ui.set_portrait_visible(false)
		_ui.set_contextual_panel_visible(false)
		if viewport_size.x > 1000.0:
			await _assert_case_file_guard(viewport_size)

func _init() -> void:
	call_deferred("_run")


func _expect(condition: bool, message: String) -> void:
	if not condition:
		_failures.append(message)


func _run() -> void:
	_ui = HarborLedgerUI.new()
	root.add_child(_ui)
	await process_frame
	await _run_mira_responsive_regression()

	_ui.set_status(
		"Speak with Captain Mira at the end of the dock | She knows why the channel is closed",
		"STAGE 0 | ARRIVAL | INVENTORY: EMPTY | ENTRIES 0 | HOLDS 0",
	)
	_ui.set_case_chain({
		"links": [
			{"id": "LENS", "filled": false},
			{"id": "MOUNT", "filled": false},
			{"id": "LEAD", "filled": false},
		],
	}, [])
	var objective_before := _ui._objective_label.text
	var chain_before := _ui.case_chain_text()

	# BEGIN INVESTIGATION -> START CASE: the contextual ledger dock must close,
	# while the always-on objective and case-chain HUD remain readable.
	_ui.set_play_started(true)
	await process_frame
	_expect(not _ui._bottom_panel.visible, "start case leaves contextual ledger dock open")
	_expect(_ui._top_bar.visible, "start case hides objective/case-chain HUD")
	_expect(_ui._objective_label.text == objective_before, "start case rewrites objective HUD")
	_expect(_ui.case_chain_text() == chain_before, "start case rewrites case-chain HUD")

	# A valid dialogue choice is an explicit exception: it reopens the contextual
	# surface and remains available until the dialogue is dismissed.
	_ui.choice_selected.connect(func(choice_id: String) -> void: _selected_choice = choice_id)
	_ui.set_portrait_visible(true, "CAPTAIN MIRA | HARBOR WATCH")
	_ui.show_choices([
		{"id": "ask_lighthouse", "text": "What happened to the lighthouse?"},
		{"id": "leave", "text": "Step away"},
	])
	await process_frame
	_expect(_ui._bottom_panel.visible, "active dialogue choices do not reopen contextual ledger dock")
	_expect(_ui.choice_count() == 2, "active dialogue choices were not preserved")
	(_ui._choice_box.get_child(0) as Button).pressed.emit()
	await process_frame
	_expect(_selected_choice == "ask_lighthouse", "valid dialogue choice was not emitted")
	_expect(_ui.choice_count() == 2, "valid dialogue choice removed remaining choices")

	# Invoke the real controller dismissal path rather than only restating its
	# individual UI calls; no world node or canonical machine is created here.
	var controller := Game3D.new()
	controller.ui = _ui
	controller.director = NarrativeDirector.new()
	controller._dialogue_open = true
	controller.call("_close_dialogue")
	await process_frame
	_expect(_ui.choice_count() == 0, "dialogue dismissal left choices active")
	_expect(not _ui._bottom_panel.visible, "dialogue dismissal left contextual ledger dock open")
	_expect(not _ui._portrait_requested, "dialogue dismissal left portrait active")
	controller.director.free()
	controller.free()
	_ui.set_status(
		"Speak with Captain Mira at the end of the dock | She knows why the channel is closed",
		"STAGE 0 | ARRIVAL | INVENTORY: EMPTY | ENTRIES 0 | HOLDS 0",
	)
	_ui.set_case_chain({
		"links": [
			{"id": "LENS", "filled": false},
			{"id": "MOUNT", "filled": false},
			{"id": "LEAD", "filled": false},
		],
	}, [])
	await process_frame
	_expect(not _ui._bottom_panel.visible, "HUD refresh reopened dismissed contextual ledger dock")
	_expect(_ui._top_bar.visible, "HUD refresh hid objective/case-chain HUD")

	# Returning from cinematic letterbox must restore the HUD, not a closed dock.
	_ui.set_letterbox(true)
	await process_frame
	_expect(not _ui._bottom_panel.visible, "letterbox entry reopened dismissed contextual ledger dock")
	_ui.set_letterbox(false)
	await process_frame
	_expect(not _ui._bottom_panel.visible, "letterbox return reopened dismissed contextual ledger dock")
	_expect(_ui._top_bar.visible, "letterbox return did not restore objective/case-chain HUD")
	_expect(_ui._objective_label.text == objective_before, "letterbox return rewrote objective HUD")
	_expect(_ui.case_chain_text() == chain_before, "letterbox return rewrote case-chain HUD")

	# Representative overlays retain their own priority without reviving the
	# contextual dock or consuming dialogue state.
	_ui.show_tutorial(true)
	await process_frame
	_expect(_ui.is_tutorial_open(), "tutorial overlay did not open")
	_expect(not _ui._bottom_panel.visible, "tutorial overlay reopened contextual ledger dock")
	_ui.hide_tutorial()
	_ui.show_evidence_board(
		[
			{"id": "LENS", "filled": false, "sealed": false, "label": "Not yet in the ledger", "why": ""},
			{"id": "MOUNT", "filled": false, "sealed": false, "label": "Not yet in the ledger", "why": ""},
			{"id": "LEAD", "filled": false, "sealed": false, "label": "Not yet in the ledger", "why": ""},
			{"id": "SEALED", "filled": false, "sealed": true, "label": "A sealed entry", "why": ""},
		],
		{"filled": 0, "total": 3},
		[],
		"Recover the signal lens",
	)
	await process_frame
	_expect(_ui.is_evidence_board_open(), "case-file overlay did not open")
	_expect(not _ui._bottom_panel.visible, "case-file overlay reopened contextual ledger dock")
	_ui.hide_evidence_board()
	_ui.flash("commit")
	_expect(_ui._feedback_label.visible, "feedback overlay disappeared while dock was dismissed")
	_ui.show_end_card(["CASE COMPLETE"])
	await process_frame
	_expect(not _ui._bottom_panel.visible, "ending overlay reopened contextual ledger dock")
	_expect(not _ui._top_bar.visible, "ending overlay did not retain ending priority")

	var result := {"passed": _failures.is_empty(), "failures": _failures}
	print("PANEL_LIFECYCLE_RESULT " + JSON.stringify(result))
	quit(0 if _failures.is_empty() else 1)
