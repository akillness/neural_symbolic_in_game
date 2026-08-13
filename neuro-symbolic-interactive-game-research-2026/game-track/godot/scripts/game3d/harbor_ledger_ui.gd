class_name HarborLedgerUI
extends CanvasLayer

## Harbor Ledger presentation surface (SL-PRESENT-001 layout: scene-forward,
## responsive ledger/action dock). Every semantic color carries a text/icon
## redundancy; refusals show a neutral reason plus the next valid affordance
## and never expose hidden oracle labels.

signal choice_selected(choice_id: String)
signal start_requested
signal audio_toggle_requested
signal free_question_submitted(text: String)
signal tutorial_closed

const PALETTE := SealedLighthouseWorldBuilder.PALETTE
const NARROW_WIDTH := 900.0
const UI_FONT := preload("res://assets/fonts/NanumGothic-Regular.ttf")

var reduce_motion: bool = false
var _root: Control
var _ledger_log: RichTextLabel
var _ledger_title: Label
var _ledger_box: VBoxContainer
var _choice_box: VBoxContainer
var _choice_scroll: ScrollContainer
var _action_box: VBoxContainer
var _columns: BoxContainer
var _prompt_label: Label
var _status_label: Label
var _objective_label: Label
var _portrait_box: VBoxContainer
var _portrait: TextureRect
var _speaker_label: Label
var _flash: ColorRect
var _feedback_label: Label
var _letterbox_top: ColorRect
var _letterbox_bottom: ColorRect
var _toast: Label
var _end_card: PanelContainer
var _end_text: RichTextLabel
var _bottom_panel: PanelContainer
var _controls_panel: PanelContainer
var _controls_label: Label
var _cursor_label: Label
var _audio_button: Button
var _llm_label: Label
var _question_row: HBoxContainer
var _question_edit: LineEdit
var _tutorial_panel: PanelContainer
var _tutorial_title: Label
var _tutorial_body: Label
var _tutorial_image: TextureRect
var _tutorial_progress: Label
var _tutorial_prev: Button
var _tutorial_next: Button
var _tutorial_pages: Array = []
var _tutorial_index: int = 0
var _inventory_row: HBoxContainer
var _inventory_icon: TextureRect
var _progress_label: Label
var _progress_bar: ProgressBar
var _start_gate: ColorRect
var _start_card: PanelContainer
var _start_button: Button
var _layout_narrow: bool = false
var _play_started: bool = false
var _portrait_requested: bool = false
var _speaker_name: String = ""
var _progress_stage: int = 0
var _progress_total: int = 3
var _progress_phase: String = "도착 · ARRIVAL"
var _toast_tween: Tween
var _flash_tween: Tween
var _feedback_tween: Tween


func _ready() -> void:
	layer = 10
	_build()
	get_viewport().size_changed.connect(_apply_responsive_layout)
	_apply_responsive_layout()


func _build() -> void:
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var ui_theme := Theme.new()
	var ui_font := FontVariation.new()
	ui_font.base_font = UI_FONT
	var ui_fallbacks: Array[Font] = [ThemeDB.fallback_font]
	ui_font.fallbacks = ui_fallbacks
	ui_theme.default_font = ui_font
	_root.theme = ui_theme
	add_child(_root)

	_letterbox_top = _make_bar(_root, true)
	_letterbox_bottom = _make_bar(_root, false)

	_flash = ColorRect.new()
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.color = Color(0, 0, 0, 0)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_flash)

	_build_controls_panel()

	_feedback_label = Label.new()
	_feedback_label.add_theme_font_size_override("font_size", 18)
	_feedback_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_feedback_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	_feedback_label.add_theme_constant_override("shadow_offset_x", 2)
	_feedback_label.add_theme_constant_override("shadow_offset_y", 2)
	_feedback_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_feedback_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_feedback_label.visible = false
	_root.add_child(_feedback_label)

	_prompt_label = Label.new()
	_prompt_label.add_theme_font_size_override("font_size", 20)
	_prompt_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_prompt_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.92))
	_prompt_label.add_theme_constant_override("shadow_offset_x", 2)
	_prompt_label.add_theme_constant_override("shadow_offset_y", 2)
	_prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt_label.visible = false
	_root.add_child(_prompt_label)

	_build_bottom_panel()
	_build_toast()
	_build_end_card()
	_build_start_gate()
	_build_tutorial()


func _build_controls_panel() -> void:
	_controls_panel = PanelContainer.new()
	_controls_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.88), Color(PALETTE.brass, 0.72), 1, 8)
	)
	_root.add_child(_controls_panel)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 2)
	_controls_panel.add_child(stack)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)
	stack.add_child(header)
	_cursor_label = Label.new()
	_cursor_label.text = "● 시작 대기 · READY"
	_cursor_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_cursor_label.add_theme_font_size_override("font_size", 14)
	_cursor_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	header.add_child(_cursor_label)
	_audio_button = Button.new()
	_audio_button.text = "AUDIO LOCKED · [V]"
	_audio_button.custom_minimum_size = Vector2(142.0, 26.0)
	_audio_button.add_theme_font_size_override("font_size", 13)
	_audio_button.pressed.connect(func() -> void: audio_toggle_requested.emit())
	header.add_child(_audio_button)

	_llm_label = Label.new()
	_llm_label.text = "LLM 확인 중…"
	_llm_label.add_theme_font_size_override("font_size", 13)
	_llm_label.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.25))
	_llm_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_llm_label)

	_controls_label = Label.new()
	_controls_label.text = "WASD 이동 · 마우스 시점 · [E] 조사 · [Esc] 커서\n[F5] 저장 · [F9] 불러오기 · [M] 모션 · [V] 음향 · [L] LLM 재확인"
	_controls_label.add_theme_font_size_override("font_size", 13)
	_controls_label.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.08))
	_controls_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_controls_label)

	var progress_row := HBoxContainer.new()
	progress_row.add_theme_constant_override("separation", 8)
	stack.add_child(progress_row)
	_progress_label = Label.new()
	_progress_label.custom_minimum_size = Vector2(180.0, 0.0)
	_progress_label.add_theme_font_size_override("font_size", 13)
	_progress_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	progress_row.add_child(_progress_label)
	_progress_bar = ProgressBar.new()
	_progress_bar.min_value = 0.0
	_progress_bar.max_value = float(_progress_total)
	_progress_bar.value = 0.0
	_progress_bar.show_percentage = false
	_progress_bar.custom_minimum_size = Vector2(120.0, 8.0)
	_progress_bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	progress_row.add_child(_progress_bar)
	_update_progress_text()


func _build_bottom_panel() -> void:
	_bottom_panel = PanelContainer.new()
	_bottom_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.94), PALETTE.brass, 2, 10)
	)
	_bottom_panel.anchor_left = 0.0
	_bottom_panel.anchor_right = 1.0
	_bottom_panel.anchor_bottom = 1.0
	_root.add_child(_bottom_panel)

	_columns = BoxContainer.new()
	_columns.vertical = false
	_columns.add_theme_constant_override("separation", 12)
	_bottom_panel.add_child(_columns)

	_portrait_box = VBoxContainer.new()
	_portrait_box.custom_minimum_size = Vector2(180.0, 0.0)
	_columns.add_child(_portrait_box)
	_portrait = TextureRect.new()
	_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_portrait.custom_minimum_size = Vector2(180.0, 180.0)
	_portrait.texture = SealedLighthouseWorldBuilder.load_pack_texture("SL3D-P01-mira-dialogue-portrait.png")
	_portrait.visible = false
	_portrait_box.add_child(_portrait)
	_speaker_label = Label.new()
	_speaker_label.add_theme_font_size_override("font_size", 18)
	_speaker_label.add_theme_color_override("font_color", PALETTE.brass)
	_speaker_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_speaker_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_portrait_box.add_child(_speaker_label)

	_ledger_box = VBoxContainer.new()
	_ledger_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ledger_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_ledger_box.size_flags_stretch_ratio = 2.2
	_columns.add_child(_ledger_box)
	_ledger_title = Label.new()
	_ledger_title.text = "항구 장부 — Harbor Ledger"
	_ledger_title.add_theme_font_size_override("font_size", 18)
	_ledger_title.add_theme_color_override("font_color", PALETTE.brass)
	_ledger_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_ledger_box.add_child(_ledger_title)
	_ledger_log = RichTextLabel.new()
	_ledger_log.bbcode_enabled = true
	_ledger_log.scroll_following = true
	_ledger_log.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_ledger_log.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_ledger_log.add_theme_font_size_override("normal_font_size", 18)
	_ledger_log.add_theme_color_override("default_color", PALETTE.paper_fog)
	_ledger_box.add_child(_ledger_log)

	_action_box = VBoxContainer.new()
	_action_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_action_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_action_box.size_flags_stretch_ratio = 1.0
	_action_box.add_theme_constant_override("separation", 6)
	_columns.add_child(_action_box)
	_objective_label = Label.new()
	_objective_label.add_theme_font_size_override("font_size", 18)
	_objective_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	_objective_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_action_box.add_child(_objective_label)
	_status_label = Label.new()
	_status_label.add_theme_font_size_override("font_size", 17)
	_status_label.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.1))
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_action_box.add_child(_status_label)
	_inventory_row = HBoxContainer.new()
	_inventory_row.add_theme_constant_override("separation", 8)
	_inventory_row.visible = false
	_action_box.add_child(_inventory_row)
	_inventory_icon = TextureRect.new()
	_inventory_icon.texture = SealedLighthouseWorldBuilder.load_pack_texture("SL3D-U01-signal-lens-icon.png")
	_inventory_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_inventory_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_inventory_icon.custom_minimum_size = Vector2(44.0, 44.0)
	_inventory_row.add_child(_inventory_icon)
	var inventory_label := Label.new()
	inventory_label.text = "신호 렌즈 확보 — 거치대로"
	inventory_label.add_theme_font_size_override("font_size", 16)
	inventory_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	inventory_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	inventory_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_inventory_row.add_child(inventory_label)
	_question_row = HBoxContainer.new()
	_question_row.add_theme_constant_override("separation", 6)
	_question_row.visible = false
	_action_box.add_child(_question_row)
	_question_edit = LineEdit.new()
	_question_edit.placeholder_text = "미라에게 자유롭게 묻는다…"
	_question_edit.custom_minimum_size = Vector2(0.0, 44.0)
	_question_edit.max_length = 300
	_question_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_question_edit.add_theme_font_size_override("font_size", 17)
	_question_edit.text_submitted.connect(_submit_question)
	_question_row.add_child(_question_edit)
	var ask_button := Button.new()
	ask_button.text = "묻는다"
	ask_button.custom_minimum_size = Vector2(76.0, 44.0)
	ask_button.add_theme_font_size_override("font_size", 17)
	ask_button.pressed.connect(func() -> void: _submit_question(_question_edit.text))
	_question_row.add_child(ask_button)

	_choice_scroll = ScrollContainer.new()
	_choice_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	_choice_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_choice_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_action_box.add_child(_choice_scroll)
	_choice_box = VBoxContainer.new()
	_choice_box.add_theme_constant_override("separation", 6)
	_choice_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_choice_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_choice_scroll.add_child(_choice_box)


func _build_toast() -> void:
	_toast = Label.new()
	_toast.add_theme_font_size_override("font_size", 18)
	_toast.add_theme_color_override("font_color", PALETTE.paper_fog)
	_toast.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.92))
	_toast.add_theme_constant_override("shadow_offset_x", 2)
	_toast.add_theme_constant_override("shadow_offset_y", 2)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_toast.visible = false
	_root.add_child(_toast)


func _build_end_card() -> void:
	_end_card = PanelContainer.new()
	_end_card.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.97), PALETTE.signal_amber, 2, 28)
	)
	_end_card.visible = false
	_root.add_child(_end_card)
	_end_text = RichTextLabel.new()
	_end_text.bbcode_enabled = true
	_end_text.add_theme_font_size_override("normal_font_size", 19)
	_end_text.add_theme_color_override("default_color", PALETTE.paper_fog)
	_end_card.add_child(_end_text)


func _build_start_gate() -> void:
	_start_gate = ColorRect.new()
	_start_gate.set_anchors_preset(Control.PRESET_FULL_RECT)
	_start_gate.color = Color(PALETTE.storm_ink, 0.91)
	_start_gate.mouse_filter = Control.MOUSE_FILTER_STOP
	_start_gate.visible = false
	_root.add_child(_start_gate)
	var key_art := TextureRect.new()
	key_art.texture = SealedLighthouseWorldBuilder.load_concept_texture("SL-C01-environment-key-art.png")
	key_art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	key_art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	key_art.set_anchors_preset(Control.PRESET_FULL_RECT)
	key_art.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_start_gate.add_child(key_art)
	var key_art_veil := ColorRect.new()
	key_art_veil.color = Color(PALETTE.storm_ink, 0.58)
	key_art_veil.set_anchors_preset(Control.PRESET_FULL_RECT)
	key_art_veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_start_gate.add_child(key_art_veil)
	_start_card = PanelContainer.new()
	_start_card.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.98), PALETTE.signal_amber, 2, 24)
	)
	_start_gate.add_child(_start_card)
	var stack := VBoxContainer.new()
	stack.alignment = BoxContainer.ALIGNMENT_CENTER
	stack.add_theme_constant_override("separation", 14)
	_start_card.add_child(stack)
	var title := Label.new()
	title.text = "봉인된 등대 · THE SEALED LIGHTHOUSE"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_font_size_override("font_size", 27)
	title.add_theme_color_override("font_color", PALETTE.signal_amber)
	stack.add_child(title)
	var premise := Label.new()
	premise.text = "폭풍 속 항구에서 유효한 기록만 남기고, 허가된 단서를 찾아라.\nOnly validated actions become part of the harbor ledger."
	premise.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	premise.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	premise.add_theme_font_size_override("font_size", 17)
	premise.add_theme_color_override("font_color", PALETTE.paper_fog)
	stack.add_child(premise)
	_start_button = Button.new()
	_start_button.text = "조사 시작 — 클릭하여 시점과 음향 활성화\nBEGIN — CLICK TO CAPTURE"
	_start_button.custom_minimum_size = Vector2(0.0, 66.0)
	_start_button.add_theme_font_size_override("font_size", 18)
	_start_button.pressed.connect(func() -> void: start_requested.emit())
	stack.add_child(_start_button)
	var note := Label.new()
	note.text = "[Esc] 커서 해제 · [V] 음향 끄기 · [M] 모션 감소"
	note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_font_size_override("font_size", 14)
	note.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.2))
	stack.add_child(note)


func _build_tutorial() -> void:
	# Evidence-folio tutorial: three pages that teach controls, the ledger
	# grammar, and how play maps onto the experiment loop. Reviewed concept
	# images (SL-C02/C03) and the SL3D-U01 icon illustrate each page.
	_tutorial_pages = [
		{
			"title": "증거철을 펴다 — 조작",
			"body": "이동 WASD · 시점 마우스 · 조사 [E]\n커서 해제/닫기 [Esc] · 저장 [F5] · 불러오기 [F9]\n모션 감소 [M] · 음향 [V] · LLM 재확인 [L] · 이 안내 [T]\n\n황색 빛기둥이 지금 목표를 가리킨다.\n표식 링이 반짝이는 곳에서 [E]를 눌러 조사한다.",
			"image": "SL3D-U01-signal-lens-icon.png",
			"pack": true,
		},
		{
			"title": "장부의 문법 — 제안·커밋·보류",
			"body": "▸ 황동 점선 = 제안. 아직 아무 일도 일어나지 않았다.\n✔ 황색 실선 = 커밋. 검증을 통과했고 상태 해시가 전진했다.\n✖ 산호색 = 보류. 상태는 그대로이며, 중립적 이유와\n   다음 유효 행동이 함께 온다.\n\n보류는 벌이 아니라 이 항구의 문법이다.\n색은 언제나 문자·기호와 함께 온다.",
			"image": "SL-C03-investigation-ui.png",
			"pack": false,
		},
		{
			"title": "이 항구는 실험실이다",
			"body": "이 게임은 TRACE-RPG 연구의 탐침이다.\n관찰 → 조사 → 제안 → 검증 → 수리 → 커밋의 리듬이\n60–120초 루프를 이룬다.\n\n미라에게 자유롭게 물으면(LLM), 형식이 어긋난 답은\n최대 3회 수리된다 — 논문의 structured repair와 같은 예산.\n봉인된 사실은 어떤 대답으로도 열리지 않는다.",
			"image": "SL-C02-captain-mira-sheet.png",
			"pack": false,
		},
	]
	_tutorial_panel = PanelContainer.new()
	_tutorial_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.97), PALETTE.brass, 2, 24)
	)
	_tutorial_panel.anchor_left = 0.14
	_tutorial_panel.anchor_right = 0.86
	_tutorial_panel.anchor_top = 0.12
	_tutorial_panel.anchor_bottom = 0.88
	_tutorial_panel.visible = false
	_root.add_child(_tutorial_panel)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 12)
	_tutorial_panel.add_child(stack)
	_tutorial_title = Label.new()
	_tutorial_title.add_theme_font_size_override("font_size", 24)
	_tutorial_title.add_theme_color_override("font_color", PALETTE.signal_amber)
	_tutorial_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_tutorial_title)
	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 16)
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	stack.add_child(columns)
	_tutorial_image = TextureRect.new()
	_tutorial_image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_tutorial_image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_tutorial_image.custom_minimum_size = Vector2(250.0, 200.0)
	_tutorial_image.size_flags_vertical = Control.SIZE_EXPAND_FILL
	columns.add_child(_tutorial_image)
	_tutorial_body = Label.new()
	_tutorial_body.add_theme_font_size_override("font_size", 18)
	_tutorial_body.add_theme_color_override("font_color", PALETTE.paper_fog)
	_tutorial_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_tutorial_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_tutorial_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	columns.add_child(_tutorial_body)
	var nav := HBoxContainer.new()
	nav.add_theme_constant_override("separation", 10)
	stack.add_child(nav)
	_tutorial_prev = Button.new()
	_tutorial_prev.text = "◂ 이전"
	_tutorial_prev.custom_minimum_size = Vector2(96.0, 44.0)
	_tutorial_prev.add_theme_font_size_override("font_size", 17)
	_tutorial_prev.pressed.connect(func() -> void: _tutorial_go(-1))
	nav.add_child(_tutorial_prev)
	_tutorial_progress = Label.new()
	_tutorial_progress.add_theme_font_size_override("font_size", 16)
	_tutorial_progress.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.15))
	_tutorial_progress.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_tutorial_progress.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav.add_child(_tutorial_progress)
	_tutorial_next = Button.new()
	_tutorial_next.custom_minimum_size = Vector2(150.0, 44.0)
	_tutorial_next.add_theme_font_size_override("font_size", 17)
	_tutorial_next.pressed.connect(func() -> void: _tutorial_go(1))
	nav.add_child(_tutorial_next)


func show_tutorial() -> void:
	_tutorial_index = 0
	_tutorial_panel.visible = true
	_apply_tutorial_page()


func hide_tutorial() -> void:
	_tutorial_panel.visible = false
	tutorial_closed.emit()


func is_tutorial_open() -> bool:
	return _tutorial_panel != null and _tutorial_panel.visible


func _tutorial_go(step: int) -> void:
	if _tutorial_index + step >= _tutorial_pages.size():
		hide_tutorial()
		return
	_tutorial_index = clampi(_tutorial_index + step, 0, _tutorial_pages.size() - 1)
	_apply_tutorial_page()


func _apply_tutorial_page() -> void:
	var page: Dictionary = _tutorial_pages[_tutorial_index]
	_tutorial_title.text = page["title"]
	_tutorial_body.text = page["body"]
	var texture := (
		SealedLighthouseWorldBuilder.load_pack_texture(page["image"])
		if page["pack"]
		else SealedLighthouseWorldBuilder.load_concept_texture(page["image"])
	)
	_tutorial_image.texture = texture
	_tutorial_image.visible = texture != null
	_tutorial_progress.text = "%d / %d" % [_tutorial_index + 1, _tutorial_pages.size()]
	_tutorial_prev.disabled = _tutorial_index == 0
	_tutorial_next.text = "조사 시작 ▸" if _tutorial_index == _tutorial_pages.size() - 1 else "다음 ▸"
	_tutorial_next.grab_focus()


func set_lens_held(held: bool) -> void:
	if _inventory_row != null:
		_inventory_row.visible = held and _inventory_icon.texture != null


func _panel_style(background: Color, border: Color, width: int, margin: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background
	style.border_color = border
	style.set_border_width_all(width)
	style.set_corner_radius_all(4)
	style.set_content_margin_all(margin)
	return style


func _make_bar(parent: Control, top: bool) -> ColorRect:
	var bar := ColorRect.new()
	bar.color = Color.BLACK
	bar.anchor_left = 0.0
	bar.anchor_right = 1.0
	if top:
		bar.anchor_top = 0.0
		bar.anchor_bottom = 0.0
	else:
		bar.anchor_top = 1.0
		bar.anchor_bottom = 1.0
	bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(bar)
	return bar


func _apply_responsive_layout() -> void:
	if _bottom_panel == null:
		return
	var viewport_size := get_viewport().get_visible_rect().size
	_layout_narrow = viewport_size.x < NARROW_WIDTH or viewport_size.x < viewport_size.y * 1.25
	_columns.vertical = _layout_narrow
	_bottom_panel.anchor_top = 0.38 if _layout_narrow else 0.58
	_bottom_panel.offset_left = 6.0
	_bottom_panel.offset_right = -6.0
	_bottom_panel.offset_top = 0.0
	_bottom_panel.offset_bottom = -6.0
	_portrait_box.custom_minimum_size = Vector2(0.0, 0.0) if _layout_narrow else Vector2(180.0, 0.0)
	_ledger_log.custom_minimum_size = Vector2(0.0, 92.0) if _layout_narrow else Vector2.ZERO
	_ledger_box.size_flags_stretch_ratio = 1.05 if _layout_narrow else 2.2
	_action_box.size_flags_stretch_ratio = 1.35 if _layout_narrow else 1.0
	_controls_panel.anchor_left = 0.02
	_controls_panel.anchor_right = 0.98 if _layout_narrow else 0.42
	_controls_panel.anchor_top = 0.02
	_controls_panel.anchor_bottom = 0.02
	_controls_panel.offset_left = 0.0
	_controls_panel.offset_right = 0.0
	_controls_panel.offset_top = 0.0
	_controls_panel.offset_bottom = 106.0 if _layout_narrow else 102.0
	_prompt_label.anchor_left = 0.08
	_prompt_label.anchor_right = 0.92
	_prompt_label.anchor_top = _bottom_panel.anchor_top
	_prompt_label.anchor_bottom = _bottom_panel.anchor_top
	_prompt_label.offset_left = 0.0
	_prompt_label.offset_right = 0.0
	_prompt_label.offset_top = -42.0
	_prompt_label.offset_bottom = -8.0
	_feedback_label.anchor_left = 0.20
	_feedback_label.anchor_right = 0.80
	_feedback_label.anchor_top = 0.0
	_feedback_label.anchor_bottom = 0.0
	_feedback_label.offset_left = 0.0
	_feedback_label.offset_right = 0.0
	_feedback_label.offset_top = 116.0
	_feedback_label.offset_bottom = 148.0
	_toast.anchor_left = 0.12
	_toast.anchor_right = 0.88
	_toast.anchor_top = 0.0
	_toast.anchor_bottom = 0.0
	_toast.offset_left = 0.0
	_toast.offset_right = 0.0
	_toast.offset_top = 152.0
	_toast.offset_bottom = 184.0
	_end_card.anchor_left = 0.04 if _layout_narrow else 0.18
	_end_card.anchor_right = 0.96 if _layout_narrow else 0.82
	_end_card.anchor_top = 0.13 if _layout_narrow else 0.16
	_end_card.anchor_bottom = 0.88 if _layout_narrow else 0.84
	_start_card.anchor_left = 0.05 if _layout_narrow else 0.21
	_start_card.anchor_right = 0.95 if _layout_narrow else 0.79
	_start_card.anchor_top = 0.19 if _layout_narrow else 0.22
	_start_card.anchor_bottom = 0.82 if _layout_narrow else 0.78
	_controls_label.add_theme_font_size_override("font_size", 12 if _layout_narrow else 13)
	_ledger_log.add_theme_font_size_override("normal_font_size", 16 if _layout_narrow else 18)
	_objective_label.add_theme_font_size_override("font_size", 16 if _layout_narrow else 18)
	_status_label.add_theme_font_size_override("font_size", 15 if _layout_narrow else 17)
	_update_portrait_visibility()


func layout_name_for_size(viewport_size: Vector2) -> String:
	return (
		"narrow-stacked"
		if viewport_size.x < NARROW_WIDTH or viewport_size.x < viewport_size.y * 1.25
		else "wide-columns"
	)


func set_letterbox(active: bool) -> void:
	var height := 56.0 if active else 0.0
	_letterbox_top.offset_bottom = height
	_letterbox_bottom.offset_top = -height
	_bottom_panel.visible = not active


func show_start_gate(visible_now: bool) -> void:
	_start_gate.visible = visible_now
	if visible_now:
		_play_started = false
		_cursor_label.text = "● 시작 대기 · READY"
		_start_button.grab_focus()


func set_play_started(started: bool) -> void:
	_play_started = started
	_start_gate.visible = not started
	set_cursor_captured(started)


func set_cursor_captured(captured: bool) -> void:
	if not _play_started:
		_cursor_label.text = "● 시작 대기 · READY"
	elif captured:
		_cursor_label.text = "● 시점 잠김 · LOOK ACTIVE"
	else:
		_cursor_label.text = "○ 커서 자유 · 클릭하여 복귀"


func set_audio_state(unlocked: bool, muted: bool) -> void:
	if not unlocked:
		_audio_button.text = "AUDIO LOCKED · [V]"
	elif muted:
		_audio_button.text = "AUDIO OFF · [V]"
	else:
		_audio_button.text = "AUDIO ON · [V]"


func set_progress(stage: int, total: int, phase: String) -> void:
	_progress_total = maxi(1, total)
	_progress_stage = clampi(stage, 0, _progress_total)
	_progress_phase = phase
	_progress_bar.max_value = float(_progress_total)
	_progress_bar.value = float(_progress_stage)
	_update_progress_text()


func _update_progress_text() -> void:
	if _progress_label != null:
		_progress_label.text = "탐사 %d/%d · %s" % [_progress_stage, _progress_total, _progress_phase]


func show_prompt(text: String) -> void:
	_prompt_label.text = "[E] " + text
	_prompt_label.visible = text != ""


func hide_prompt() -> void:
	_prompt_label.visible = false


func set_portrait_visible(visible_now: bool, speaker: String = "") -> void:
	_portrait_requested = visible_now
	_speaker_name = speaker
	_speaker_label.text = speaker
	_update_portrait_visibility()


func _update_portrait_visibility() -> void:
	if _portrait == null:
		return
	_portrait_box.visible = _portrait_requested and not _layout_narrow
	_portrait.visible = _portrait_requested and not _layout_narrow and _portrait.texture != null
	_ledger_title.text = "항구 장부 — Harbor Ledger"
	if _portrait_requested and _layout_narrow and _speaker_name != "":
		_ledger_title.text += " · " + _speaker_name


func ledger_line(kind: String, text: String) -> void:
	var line := ""
	match kind:
		"narration":
			line = "[color=#D9D3C4]%s[/color]" % text
		"dialogue":
			line = "[color=#D9D3C4][i]“%s”[/i][/color]" % text
		"proposal":
			line = "[color=#A77A3A]▸ 제안 ┄┄ %s[/color]" % text
		"commit":
			line = "[color=#F2B84B]✔ 커밋 ── %s[/color]" % text
		"refusal":
			line = "[color=#D9685F]✖ 보류 ─┤ %s[/color]" % text
		"hint":
			line = "[color=#F2B84B]☀ 허가된 단서 — %s[/color]" % text
		_:
			line = text
	_ledger_log.append_text(line + "\n")


func show_choices(choices: Array) -> void:
	clear_choices()
	for choice in choices:
		var button := Button.new()
		button.text = choice["text"]
		button.custom_minimum_size = Vector2(0.0, 44.0)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.add_theme_font_size_override("font_size", 16 if _layout_narrow else 18)
		var choice_id: String = choice["id"]
		button.pressed.connect(func() -> void: choice_selected.emit(choice_id))
		_choice_box.add_child(button)
	if _choice_box.get_child_count() > 0:
		(_choice_box.get_child(0) as Button).grab_focus()


func clear_choices() -> void:
	for child in _choice_box.get_children():
		child.queue_free()


func set_llm_status(text: String, connected: bool) -> void:
	if _llm_label == null:
		return
	_llm_label.text = ("◆ " if connected else "◇ ") + text
	_llm_label.add_theme_color_override(
		"font_color", PALETTE.signal_amber if connected else PALETTE.paper_fog.darkened(0.25)
	)


func show_question_input() -> void:
	_question_row.visible = true
	_question_edit.text = ""
	_question_edit.grab_focus()


func hide_question_input() -> void:
	_question_row.visible = false


func _submit_question(text: String) -> void:
	var question := text.strip_edges()
	if question == "":
		return
	hide_question_input()
	free_question_submitted.emit(question)


func set_status(objective: String, status: String) -> void:
	_objective_label.text = "◈ 목표: " + objective
	_status_label.text = status


func flash(kind: String) -> void:
	# <=100 ms local acknowledgement target: color and redundant text land on
	# the next frame. This is presentation feedback, never action authorization.
	var is_commit := kind == "commit"
	var color := Color(PALETTE.signal_amber, 0.22) if is_commit else Color(PALETTE.warning_coral, 0.24)
	_feedback_label.text = "✔ VALIDATED · 커밋됨" if is_commit else "✖ HELD · 상태 유지"
	_feedback_label.add_theme_color_override(
		"font_color", PALETTE.signal_amber if is_commit else PALETTE.warning_coral
	)
	_feedback_label.visible = true
	if _flash_tween != null and _flash_tween.is_valid():
		_flash_tween.kill()
	_flash.color = Color(0, 0, 0, 0) if reduce_motion else color
	if not reduce_motion:
		_flash_tween = create_tween()
		_flash_tween.tween_property(_flash, "color", Color(color, 0.0), 0.45)
	if _feedback_tween != null and _feedback_tween.is_valid():
		_feedback_tween.kill()
	_feedback_tween = create_tween()
	_feedback_tween.tween_interval(1.15)
	_feedback_tween.tween_callback(func() -> void: _feedback_label.visible = false)


func toast(text: String) -> void:
	_toast.text = text
	_toast.visible = true
	if _toast_tween != null and _toast_tween.is_valid():
		_toast_tween.kill()
	_toast_tween = create_tween()
	_toast_tween.tween_interval(2.2)
	_toast_tween.tween_callback(func() -> void: _toast.visible = false)


func show_end_card(text: String) -> void:
	_end_text.text = text
	_end_card.visible = true
	_bottom_panel.visible = false


func get_engineering_snapshot() -> Dictionary:
	var viewport_size := get_viewport().get_visible_rect().size
	return {
		"engineering_only": true,
		"claim_boundary": "UI instrumentation snapshot; not G4, usability, immersion, affect, or efficacy evidence.",
		"viewport": {"width": int(viewport_size.x), "height": int(viewport_size.y)},
		"layout": "narrow-stacked" if _layout_narrow else "wide-columns",
		"responsive_profiles": {
			"narrow": layout_name_for_size(Vector2(720.0, 900.0)),
			"wide": layout_name_for_size(Vector2(1280.0, 720.0)),
		},
		"controls_visible": _controls_panel.visible,
		"control_affordances": ["WASD", "mouse-look", "E", "Escape", "F5", "F9", "M", "V"],
		"start_gate_visible": _start_gate.visible,
		"play_started": _play_started,
		"progress": {"stage": _progress_stage, "total": _progress_total, "phase": _progress_phase},
		"reduced_motion": reduce_motion,
		"semantic_feedback_redundancy": ["color", "icon", "text", "ledger-line"],
	}
