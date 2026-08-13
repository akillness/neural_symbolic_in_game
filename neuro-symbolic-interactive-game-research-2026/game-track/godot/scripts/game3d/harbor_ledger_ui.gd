class_name HarborLedgerUI
extends CanvasLayer

## Harbor Ledger presentation surface (SL-PRESENT-001 layout: ~55% scene,
## ~30% ledger, ~15% actions). Every semantic color carries a text/icon
## redundancy; refusals show a neutral reason plus the next valid affordance
## and never expose hidden oracle labels.

signal choice_selected(choice_id: String)

const PALETTE := SealedLighthouseWorldBuilder.PALETTE

var reduce_motion: bool = false
var _ledger_log: RichTextLabel
var _choice_box: VBoxContainer
var _prompt_label: Label
var _status_label: Label
var _objective_label: Label
var _portrait: TextureRect
var _speaker_label: Label
var _flash: ColorRect
var _letterbox_top: ColorRect
var _letterbox_bottom: ColorRect
var _toast: Label
var _end_card: PanelContainer
var _end_text: RichTextLabel
var _bottom_panel: Control


func _ready() -> void:
	layer = 10
	_build()


func _build() -> void:
	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(root)

	_letterbox_top = _make_bar(root, true)
	_letterbox_bottom = _make_bar(root, false)

	_flash = ColorRect.new()
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.color = Color(0, 0, 0, 0)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(_flash)

	_prompt_label = Label.new()
	_prompt_label.add_theme_font_size_override("font_size", 20)
	_prompt_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_prompt_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	_prompt_label.position = Vector2(-220.0, -320.0)
	_prompt_label.size = Vector2(440.0, 32.0)
	_prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt_label.visible = false
	root.add_child(_prompt_label)

	_bottom_panel = PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(PALETTE.storm_ink, 0.92)
	style.border_color = PALETTE.brass
	style.set_border_width_all(2)
	style.set_content_margin_all(10)
	_bottom_panel.add_theme_stylebox_override("panel", style)
	_bottom_panel.anchor_left = 0.0
	_bottom_panel.anchor_right = 1.0
	_bottom_panel.anchor_top = 0.62
	_bottom_panel.anchor_bottom = 1.0
	root.add_child(_bottom_panel)

	var columns := HBoxContainer.new()
	columns.add_theme_constant_override("separation", 12)
	_bottom_panel.add_child(columns)

	var portrait_box := VBoxContainer.new()
	portrait_box.custom_minimum_size = Vector2(180.0, 0.0)
	columns.add_child(portrait_box)
	_portrait = TextureRect.new()
	_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_portrait.custom_minimum_size = Vector2(180.0, 180.0)
	_portrait.texture = SealedLighthouseWorldBuilder.load_pack_texture("SL3D-P01-mira-dialogue-portrait.png")
	_portrait.visible = false
	portrait_box.add_child(_portrait)
	_speaker_label = Label.new()
	_speaker_label.add_theme_font_size_override("font_size", 18)
	_speaker_label.add_theme_color_override("font_color", PALETTE.brass)
	_speaker_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	portrait_box.add_child(_speaker_label)

	var ledger_box := VBoxContainer.new()
	ledger_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ledger_box.size_flags_stretch_ratio = 2.2
	columns.add_child(ledger_box)
	var ledger_title := Label.new()
	ledger_title.text = "항구 장부 — Harbor Ledger"
	ledger_title.add_theme_font_size_override("font_size", 18)
	ledger_title.add_theme_color_override("font_color", PALETTE.brass)
	ledger_box.add_child(ledger_title)
	_ledger_log = RichTextLabel.new()
	_ledger_log.bbcode_enabled = true
	_ledger_log.scroll_following = true
	_ledger_log.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_ledger_log.add_theme_font_size_override("normal_font_size", 18)
	_ledger_log.add_theme_color_override("default_color", PALETTE.paper_fog)
	ledger_box.add_child(_ledger_log)

	var action_box := VBoxContainer.new()
	action_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	action_box.size_flags_stretch_ratio = 1.0
	action_box.add_theme_constant_override("separation", 6)
	columns.add_child(action_box)
	_objective_label = Label.new()
	_objective_label.add_theme_font_size_override("font_size", 18)
	_objective_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	_objective_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	action_box.add_child(_objective_label)
	_status_label = Label.new()
	_status_label.add_theme_font_size_override("font_size", 18)
	_status_label.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.1))
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	action_box.add_child(_status_label)
	_choice_box = VBoxContainer.new()
	_choice_box.add_theme_constant_override("separation", 6)
	_choice_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	action_box.add_child(_choice_box)

	_toast = Label.new()
	_toast.add_theme_font_size_override("font_size", 18)
	_toast.add_theme_color_override("font_color", PALETTE.paper_fog)
	_toast.set_anchors_preset(Control.PRESET_CENTER_TOP)
	_toast.position = Vector2(-260.0, 24.0)
	_toast.size = Vector2(520.0, 30.0)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.visible = false
	root.add_child(_toast)

	_end_card = PanelContainer.new()
	var end_style := StyleBoxFlat.new()
	end_style.bg_color = Color(PALETTE.storm_ink, 0.97)
	end_style.border_color = PALETTE.signal_amber
	end_style.set_border_width_all(2)
	end_style.set_content_margin_all(28)
	_end_card.add_theme_stylebox_override("panel", end_style)
	_end_card.anchor_left = 0.18
	_end_card.anchor_right = 0.82
	_end_card.anchor_top = 0.16
	_end_card.anchor_bottom = 0.84
	_end_card.visible = false
	root.add_child(_end_card)
	_end_text = RichTextLabel.new()
	_end_text.bbcode_enabled = true
	_end_text.add_theme_font_size_override("normal_font_size", 19)
	_end_text.add_theme_color_override("default_color", PALETTE.paper_fog)
	_end_card.add_child(_end_text)


func _make_bar(root: Control, top: bool) -> ColorRect:
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
	root.add_child(bar)
	return bar


func set_letterbox(active: bool) -> void:
	var height := 56.0 if active else 0.0
	_letterbox_top.offset_bottom = height
	_letterbox_bottom.offset_top = -height
	_bottom_panel.visible = not active


func show_prompt(text: String) -> void:
	_prompt_label.text = "[E] " + text
	_prompt_label.visible = text != ""


func hide_prompt() -> void:
	_prompt_label.visible = false


func set_portrait_visible(visible_now: bool, speaker: String = "") -> void:
	_portrait.visible = visible_now and _portrait.texture != null
	_speaker_label.text = speaker


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
		button.add_theme_font_size_override("font_size", 18)
		var choice_id: String = choice["id"]
		button.pressed.connect(func() -> void: choice_selected.emit(choice_id))
		_choice_box.add_child(button)


func clear_choices() -> void:
	for child in _choice_box.get_children():
		child.queue_free()


func set_status(objective: String, status: String) -> void:
	_objective_label.text = "◈ 목표: " + objective
	_status_label.text = status


func flash(kind: String) -> void:
	# ≤100 ms local acknowledgement target: the color lands on the next frame.
	var color := Color(PALETTE.signal_amber, 0.22) if kind == "commit" else Color(PALETTE.warning_coral, 0.24)
	_flash.color = color
	if reduce_motion:
		_flash.color = Color(0, 0, 0, 0)
		return
	var tween := create_tween()
	tween.tween_property(_flash, "color", Color(color, 0.0), 0.45)


func toast(text: String) -> void:
	_toast.text = text
	_toast.visible = true
	var tween := create_tween()
	tween.tween_interval(2.2)
	tween.tween_callback(func() -> void: _toast.visible = false)


func show_end_card(text: String) -> void:
	_end_text.text = text
	_end_card.visible = true
	_bottom_panel.visible = false
