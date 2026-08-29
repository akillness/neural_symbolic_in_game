class_name HarborLedgerUI
extends CanvasLayer

## Harbor Ledger presentation surface (SL-PRESENT-001 layout: scene-forward,
## responsive ledger/action dock). Every semantic color carries a text/icon
## redundancy; refusals show a neutral reason plus the next valid affordance
## and never expose hidden oracle labels.

signal choice_selected(choice_id: String)
signal start_requested
signal audio_toggle_requested
signal tutorial_closed

const PALETTE := SealedLighthouseWorldBuilder.PALETTE
const NARROW_WIDTH := 900.0
const NARROW_LEDGER_TOP := 0.38
const WIDE_LEDGER_TOP := 0.66
const UI_FONT := preload("res://assets/fonts/NanumGothic-Regular.ttf")
# Start-gate key-art drift: one shared 12 s sine drives a ±0.5% scale breathe
# and a ±4 px lateral drift (mouse-independent). The 1.5% base overscan keeps
# the art covering the gate through both extremes; reduced motion rests at the
# base pose and absent art bytes disable the effect entirely.
const GATE_DRIFT_PERIOD_S := 12.0
const GATE_DRIFT_PIXELS := 4.0
const GATE_SCALE_BREATHE := 0.005
const GATE_ART_BASE_SCALE := 1.015

var reduce_motion: bool = false
var _root: Control
var _ledger_log: RichTextLabel
var _ledger_title: Label
var _ledger_box: VBoxContainer
var _choice_box: VBoxContainer
var _choice_scroll: ScrollContainer
var _action_box: VBoxContainer
var _columns: BoxContainer
var _prompt_panel: PanelContainer
var _prompt_label: Label
var _status_label: Label
var _objective_label: Label
var _portrait_box: VBoxContainer
var _portrait: TextureRect
var _portrait_frame: PanelContainer
var _speaker_label: Label
var _flash: ColorRect
var _feedback_label: Label
var _letterbox_top: ColorRect
var _letterbox_bottom: ColorRect
var _toast: Label
var _end_card: PanelContainer
var _end_text: RichTextLabel
var _end_icon: TextureRect
var _ledger_stamp: TextureRect
var _stamp_commit_texture: Texture2D
var _stamp_refusal_texture: Texture2D
var _stamp_tween: Tween
var _bottom_panel: PanelContainer
var _controls_panel: PanelContainer
var _controls_label: Label
var _cursor_label: Label
var _audio_button: Button
var _progress_label: Label
var _progress_bar: ProgressBar
var _start_gate: ColorRect
var _start_card: PanelContainer
var _start_button: Button
var _tutorial_panel: PanelContainer
var _tutorial_title: Label
var _tutorial_body: Label
var _tutorial_image: TextureRect
var _tutorial_columns: BoxContainer
var _tutorial_progress: Label
var _tutorial_prev: Button
var _tutorial_next: Button
var _tutorial_pages: Array = []
var _tutorial_index: int = 0
var _inventory_row: HBoxContainer
var _inventory_icon: TextureRect
var _layout_narrow: bool = false
var _play_started: bool = false
var _portrait_requested: bool = false
var _speaker_name: String = ""
var _progress_stage: int = 0
var _progress_total: int = 3
var _progress_phase: String = "ARRIVAL"
var _toast_tween: Tween
var _flash_tween: Tween
var _feedback_tween: Tween
var _start_key_art: TextureRect
var _start_key_art_landscape: Texture2D = null
var _start_key_art_portrait: Texture2D = null
var _gate_time: float = 0.0


func _ready() -> void:
	layer = 10
	_build()
	get_viewport().size_changed.connect(_apply_responsive_layout)
	_apply_responsive_layout()
	# The only per-frame UI work is the start-gate drift; it runs solely while
	# the gate is visible with key art present (desktop skips it entirely).
	_update_gate_motion_state()


func _process(delta: float) -> void:
	if _start_key_art == null:
		return
	if reduce_motion:
		_start_key_art.position = Vector2.ZERO
		_start_key_art.scale = Vector2.ONE * GATE_ART_BASE_SCALE
		return
	_gate_time = fmod(_gate_time + delta, GATE_DRIFT_PERIOD_S)
	var phase := _gate_time * (TAU / GATE_DRIFT_PERIOD_S)
	_start_key_art.scale = Vector2.ONE * (GATE_ART_BASE_SCALE + sin(phase) * GATE_SCALE_BREATHE)
	_start_key_art.position = Vector2(sin(phase) * GATE_DRIFT_PIXELS, 0.0)


func _update_gate_motion_state() -> void:
	set_process(
		_start_key_art != null and _start_gate != null and _start_gate.visible
	)


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

	_prompt_panel = PanelContainer.new()
	_prompt_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.94), PALETTE.signal_amber, 2, 10)
	)
	_prompt_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt_panel.visible = false
	_root.add_child(_prompt_panel)
	_prompt_label = Label.new()
	_prompt_label.add_theme_font_size_override("font_size", 18)
	_prompt_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt_panel.add_child(_prompt_label)

	_build_bottom_panel()
	_build_toast()
	_build_end_card()
	_build_start_gate()
	_build_tutorial()


func _build_controls_panel() -> void:
	_controls_panel = PanelContainer.new()
	_controls_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.92), Color(PALETTE.brass, 0.78), 1, 8)
	)
	_root.add_child(_controls_panel)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 4)
	_controls_panel.add_child(stack)

	var case_label := Label.new()
	case_label.text = "TRACE-RPG | CASE 01"
	case_label.add_theme_font_size_override("font_size", 11)
	case_label.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.68))
	stack.add_child(case_label)

	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)
	stack.add_child(header)
	_cursor_label = Label.new()
	_cursor_label.text = "[READY] CASE READY"
	_cursor_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_cursor_label.add_theme_font_size_override("font_size", 14)
	_cursor_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	header.add_child(_cursor_label)
	_audio_button = Button.new()
	_audio_button.text = "AUDIO LOCKED | V"
	_audio_button.custom_minimum_size = Vector2(132.0, 28.0)
	_audio_button.add_theme_font_size_override("font_size", 12)
	_style_button(_audio_button)
	_audio_button.pressed.connect(func() -> void: audio_toggle_requested.emit())
	header.add_child(_audio_button)

	_controls_label = Label.new()
	_controls_label.text = "WASD MOVE | MOUSE LOOK | [E] INSPECT | [Esc] CURSOR\n[F5] SAVE | [F9] LOAD | [M] REDUCE MOTION | [V] AUDIO | [T] GUIDE"
	_controls_label.add_theme_font_size_override("font_size", 12)
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
	_add_parchment_grain(_bottom_panel)

	_columns = BoxContainer.new()
	_columns.vertical = false
	_columns.add_theme_constant_override("separation", 12)
	_bottom_panel.add_child(_columns)

	_portrait_box = VBoxContainer.new()
	_portrait_box.custom_minimum_size = Vector2(180.0, 0.0)
	_columns.add_child(_portrait_box)
	# D-034/D-035: curated Higgsfield portrait first (Web-eligible), candidate
	# pack art as desktop fallback; both absent leaves the slot hidden.
	_portrait_frame = PanelContainer.new()
	_portrait_frame.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.65), Color(PALETTE.brass, 0.9), 2, 4)
	)
	_portrait_frame.visible = false
	_portrait_box.add_child(_portrait_frame)
	_portrait = TextureRect.new()
	_portrait.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_portrait.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_portrait.custom_minimum_size = Vector2(180.0, 180.0)
	var portrait_texture := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-mira-portrait.png")
	if portrait_texture == null:
		portrait_texture = SealedLighthouseWorldBuilder.load_pack_texture(
			"SL3D-P01-mira-dialogue-portrait.png"
		)
	_portrait.texture = portrait_texture
	_portrait.visible = false
	_portrait_frame.add_child(_portrait)
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
	_ledger_title.text = "HARBOR LEDGER | CASE FILE"
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
	# Curated ledger stamps (D-034/D-035): a brief diegetic ink stamp lands next
	# to the newest verdict line — commit uses ui-stamp-commit.png, refusal uses
	# ui-stamp-refusal.png. Absent bytes leave today's text-only ledger intact.
	_stamp_commit_texture = SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-stamp-commit.png")
	_stamp_refusal_texture = SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-stamp-refusal.png")
	_ledger_stamp = TextureRect.new()
	_ledger_stamp.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_ledger_stamp.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	# Capture review: at 52 px the stamp covered the tail of wrapped verdict
	# lines in the bottom-right of the log. 44 px + slight translucency lets
	# the newest line stay readable while the ink stamp still lands.
	_ledger_stamp.custom_minimum_size = Vector2(44.0, 44.0)
	_ledger_stamp.anchor_left = 1.0
	_ledger_stamp.anchor_right = 1.0
	_ledger_stamp.anchor_top = 1.0
	_ledger_stamp.anchor_bottom = 1.0
	_ledger_stamp.offset_left = -52.0
	_ledger_stamp.offset_right = -8.0
	_ledger_stamp.offset_top = -52.0
	_ledger_stamp.offset_bottom = -8.0
	_ledger_stamp.self_modulate = Color(1, 1, 1, 0.88)
	_ledger_stamp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_ledger_stamp.visible = false
	_ledger_log.add_child(_ledger_stamp)

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
	# D-034/D-035 curated-first icon; candidate pack art as desktop fallback.
	var lens_icon := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-icon-signal-lens.png")
	if lens_icon == null:
		lens_icon = SealedLighthouseWorldBuilder.load_pack_texture("SL3D-U01-signal-lens-icon.png")
	_inventory_icon.texture = lens_icon
	_inventory_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_inventory_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_inventory_icon.custom_minimum_size = Vector2(44.0, 44.0)
	_inventory_row.add_child(_inventory_icon)
	var inventory_label := Label.new()
	inventory_label.text = "SIGNAL LENS SECURED | GO TO THE MOUNT"
	inventory_label.add_theme_font_size_override("font_size", 16)
	inventory_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	inventory_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	inventory_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_inventory_row.add_child(inventory_label)

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
	_add_parchment_grain(_end_card)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 10)
	_end_card.add_child(stack)
	_end_text = RichTextLabel.new()
	_end_text.bbcode_enabled = true
	_end_text.add_theme_font_size_override("normal_font_size", 19)
	_end_text.add_theme_color_override("default_color", PALETTE.paper_fog)
	_end_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	stack.add_child(_end_text)
	# D-034/D-035: decorative tide-route emblem on the episode end card. The
	# ledger text stays the payoff; absent bytes simply hide the emblem.
	_end_icon = TextureRect.new()
	# The tide-route SEAL is the earned emblem (frozen curated contract name);
	# the older route icon remains a fallback so existing bytes keep working.
	var seal_texture := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-seal-tide-route.png")
	if seal_texture == null:
		seal_texture = SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-icon-tide-route.png")
	_end_icon.texture = seal_texture
	_end_icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_end_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_end_icon.custom_minimum_size = Vector2(96.0, 96.0)
	_end_icon.visible = _end_icon.texture != null
	stack.add_child(_end_icon)


func _build_start_gate() -> void:
	_start_gate = ColorRect.new()
	_start_gate.set_anchors_preset(Control.PRESET_FULL_RECT)
	_start_gate.color = Color(PALETTE.storm_ink, 0.91)
	_start_gate.mouse_filter = Control.MOUSE_FILTER_STOP
	_start_gate.visible = false
	_root.add_child(_start_gate)
	# D-034/D-035: curated Higgsfield key art first (ships in the Web PCK), the
	# reviewed concept sheet as desktop fallback. When both are absent the gate
	# keeps today's flat storm-ink look exactly.
	var key_art_texture := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-start-key-art.png")
	if key_art_texture == null:
		key_art_texture = SealedLighthouseWorldBuilder.load_concept_texture(
			"SL-C01-environment-key-art.png"
		)
	_start_key_art_landscape = key_art_texture
	# D-042: the 16:9 gate art loses ~74% of its width to STRETCH_KEEP_ASPECT_COVERED
	# on a 390x844 phone viewport, so a 9:16 companion is selected on portrait
	# layouts. Absent bytes fall back to the landscape art and, absent that too,
	# to the flat storm-ink gate — the procedural surface stays fully playable.
	_start_key_art_portrait = SealedLighthouseWorldBuilder.load_curated_ui_texture(
		"ui-start-key-art-portrait.png"
	)
	if key_art_texture != null:
		_start_key_art = TextureRect.new()
		_start_key_art.texture = key_art_texture
		_start_key_art.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		_start_key_art.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		_start_key_art.set_anchors_preset(Control.PRESET_FULL_RECT)
		_start_key_art.mouse_filter = Control.MOUSE_FILTER_IGNORE
		# Base overscan + centered pivot: the drift breathes around the middle
		# of the gate and never exposes a bare edge.
		_start_key_art.scale = Vector2.ONE * GATE_ART_BASE_SCALE
		_start_key_art.resized.connect(func() -> void:
			_start_key_art.pivot_offset = _start_key_art.size * 0.5
		)
		_start_gate.add_child(_start_key_art)
		# Storm-ink gradient scrim: >=0.45 alpha at every text band (0.50 at the
		# very top, 0.86 at the footer) so card text and the disclosure keep
		# >=4.5:1 contrast over the art at 1280x720 and 390x844.
		var scrim := TextureRect.new()
		var scrim_gradient := Gradient.new()
		scrim_gradient.set_color(0, Color(PALETTE.storm_ink, 0.50))
		scrim_gradient.set_color(1, Color(PALETTE.storm_ink, 0.86))
		var scrim_texture := GradientTexture2D.new()
		scrim_texture.gradient = scrim_gradient
		scrim_texture.fill_from = Vector2(0.0, 0.0)
		scrim_texture.fill_to = Vector2(0.0, 1.0)
		scrim.texture = scrim_texture
		scrim.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		scrim.set_anchors_preset(Control.PRESET_FULL_RECT)
		scrim.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_start_gate.add_child(scrim)
	else:
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
	var eyebrow := Label.new()
	eyebrow.text = "TRACE-RPG | CASE 01"
	eyebrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	eyebrow.add_theme_font_size_override("font_size", 13)
	eyebrow.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.72))
	stack.add_child(eyebrow)
	var title := Label.new()
	title.text = "THE SEALED LIGHTHOUSE"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_font_size_override("font_size", 27)
	title.add_theme_color_override("font_color", PALETTE.signal_amber)
	stack.add_child(title)
	var premise := Label.new()
	premise.text = "Recover the harbor signal. Earn the tide route.\nOnly validated actions enter the ledger."
	premise.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	premise.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	premise.add_theme_font_size_override("font_size", 17)
	premise.add_theme_color_override("font_color", PALETTE.paper_fog)
	stack.add_child(premise)
	_start_button = Button.new()
	_start_button.text = "BEGIN INVESTIGATION"
	_start_button.custom_minimum_size = Vector2(0.0, 58.0)
	_start_button.add_theme_font_size_override("font_size", 18)
	_style_button(_start_button, true)
	_start_button.pressed.connect(func() -> void: start_requested.emit())
	stack.add_child(_start_button)
	var note := Label.new()
	note.text = "WASD Move | [E] Inspect | [T] Field Guide | [M] Reduce Motion"
	note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_font_size_override("font_size", 14)
	note.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.2))
	stack.add_child(note)
	if key_art_texture != null:
		var disclosure := Label.new()
		disclosure.text = "AI-generated art | Higgsfield"
		disclosure.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		disclosure.add_theme_font_size_override("font_size", 12)
		disclosure.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.72))
		disclosure.anchor_left = 0.0
		disclosure.anchor_right = 1.0
		disclosure.anchor_top = 1.0
		disclosure.anchor_bottom = 1.0
		disclosure.offset_top = -30.0
		disclosure.offset_bottom = -10.0
		disclosure.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_start_gate.add_child(disclosure)


func _build_tutorial() -> void:
	# Evidence-folio onboarding: controls, then the ledger grammar, then how a
	# session maps onto the experiment loop. Illustrations are optional reviewed
	# concept candidates, so the pages stay readable when those bytes are absent.
	_tutorial_pages = [
		{
			"title": "OPEN THE FIELD GUIDE | CONTROLS",
			"body": "Move with WASD | Look with the mouse | Inspect with [E]\nRelease or close with [Esc] | Save [F5] | Load [F9]\nReduce motion [M] | Audio [V] | Reopen this guide [T]\n\nThe amber beacon marks your current lead.\nWhen a focus ring glows, press [E] to inspect.",
			"curated": "ui-tutorial-vignette.png",
			"image": "SL3D-U01-signal-lens-icon.png",
			"pack": true,
		},
		{
			"title": "HOW THE HARBOR LEDGER WORKS",
			"body": "The ledger accepts only entries that pass validation.\nThat is how this harbor survived the storm.\n\n[P] Brass dotted line = PROPOSAL. The world has not changed.\n[V] VALIDATION = the ledger checks every entry.\n[H] Coral line = HELD. State stays unchanged, with a neutral reason\n    and one concrete next valid entry.\n[C] Amber line = COMMITTED. Validation passed and the state advanced.\n\nA hold is guidance, not punishment.\nColor always appears with text and symbols.",
			"image": "SL-C03-investigation-ui.png",
			"pack": false,
		},
		{
			"title": "THIS HARBOR IS AN EXPERIMENT",
			"body": "This slice is a TRACE-RPG research probe.\nObserve -> inspect -> propose -> validate -> repair -> commit.\n\nOnly committed entries change canonical state.\nHeld or timed-out proposals keep the prior state hash.\nNo answer can unlock a permanently sealed fact.",
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
	_add_parchment_grain(_tutorial_panel)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 12)
	_tutorial_panel.add_child(stack)
	_tutorial_title = Label.new()
	_tutorial_title.add_theme_font_size_override("font_size", 24)
	_tutorial_title.add_theme_color_override("font_color", PALETTE.signal_amber)
	_tutorial_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_tutorial_title)
	_tutorial_columns = BoxContainer.new()
	_tutorial_columns.vertical = false
	_tutorial_columns.add_theme_constant_override("separation", 16)
	_tutorial_columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	stack.add_child(_tutorial_columns)
	_tutorial_image = TextureRect.new()
	_tutorial_image.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_tutorial_image.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_tutorial_image.custom_minimum_size = Vector2(340.0, 240.0)
	_tutorial_image.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_tutorial_columns.add_child(_tutorial_image)
	_tutorial_body = Label.new()
	_tutorial_body.add_theme_font_size_override("font_size", 18)
	_tutorial_body.add_theme_color_override("font_color", PALETTE.paper_fog)
	_tutorial_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_tutorial_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_tutorial_body.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_tutorial_columns.add_child(_tutorial_body)
	var nav := HBoxContainer.new()
	nav.add_theme_constant_override("separation", 10)
	stack.add_child(nav)
	_tutorial_prev = Button.new()
	_tutorial_prev.text = "< BACK"
	_tutorial_prev.custom_minimum_size = Vector2(96.0, 44.0)
	_tutorial_prev.add_theme_font_size_override("font_size", 16)
	_style_button(_tutorial_prev)
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
	_tutorial_next.add_theme_font_size_override("font_size", 16)
	_style_button(_tutorial_next, true)
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
	# D-034/D-035 curated-first tutorial art; candidate pack/concept fallback.
	var texture: Texture2D = null
	if page.has("curated"):
		texture = SealedLighthouseWorldBuilder.load_curated_ui_texture(page["curated"])
	if texture == null:
		texture = (
			SealedLighthouseWorldBuilder.load_pack_texture(page["image"])
			if page["pack"]
			else SealedLighthouseWorldBuilder.load_concept_texture(page["image"])
		)
	_tutorial_image.texture = texture
	_tutorial_image.visible = texture != null
	_tutorial_progress.text = "%d / %d" % [_tutorial_index + 1, _tutorial_pages.size()]
	_tutorial_prev.disabled = _tutorial_index == 0
	_tutorial_next.text = (
		"START CASE >" if _tutorial_index == _tutorial_pages.size() - 1 else "NEXT >"
	)
	_tutorial_next.grab_focus()


func set_lens_held(held: bool) -> void:
	if _inventory_row != null:
		_inventory_row.visible = held and _inventory_icon.texture != null


func _style_button(button: Button, primary: bool = false) -> void:
	# One shared focus/hover language keeps every actionable surface readable.
	# The 2 px amber focus ring is independent of pointer hover and survives the
	# English copy pass without adding a second component system.
	var normal_bg := Color(PALETTE.brass, 0.88) if primary else Color(PALETTE.storm_ink, 0.92)
	var hover_bg := PALETTE.signal_amber if primary else Color(PALETTE.wet_slate, 0.98)
	var text_color := PALETTE.storm_ink if primary else PALETTE.paper_fog
	button.add_theme_stylebox_override(
		"normal", _panel_style(normal_bg, Color(PALETTE.brass, 0.78), 1, 8)
	)
	button.add_theme_stylebox_override(
		"hover", _panel_style(hover_bg, PALETTE.signal_amber, 2, 8)
	)
	button.add_theme_stylebox_override(
		"pressed", _panel_style(PALETTE.brass.darkened(0.12), PALETTE.signal_amber, 2, 8)
	)
	button.add_theme_stylebox_override(
		"focus", _panel_style(Color(0, 0, 0, 0), PALETTE.signal_amber, 2, 8)
	)
	button.add_theme_color_override("font_color", text_color)
	button.add_theme_color_override("font_hover_color", PALETTE.storm_ink)
	button.add_theme_color_override("font_pressed_color", PALETTE.paper_fog)
	button.add_theme_color_override("font_focus_color", text_color)
	button.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND


func _panel_style(background: Color, border: Color, width: int, margin: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = background
	style.border_color = border
	style.set_border_width_all(width)
	style.set_corner_radius_all(8)
	style.set_content_margin_all(margin)
	return style


func _add_parchment_grain(panel: PanelContainer) -> void:
	# D-034/D-035 curated parchment grain, darken-modulated toward storm ink so
	# paper-fog/amber text keeps its contrast on the dark panels. Absent bytes
	# leave the flat panel style untouched.
	var texture := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-ledger-parchment.png")
	if texture == null:
		return
	var grain := TextureRect.new()
	grain.texture = texture
	grain.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	grain.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	grain.modulate = Color(0.28, 0.30, 0.33, 0.55)
	grain.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_child(grain)


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
	if _tutorial_columns != null:
		# 390px-class portrait viewports: the vignette + text row cannot share the
		# width, so stack the folio vertically and widen the panel instead.
		_tutorial_columns.vertical = _layout_narrow
		_tutorial_image.custom_minimum_size = (
			Vector2(0.0, 150.0) if _layout_narrow else Vector2(340.0, 240.0)
		)
		_tutorial_image.size_flags_vertical = (
			Control.SIZE_SHRINK_CENTER if _layout_narrow else Control.SIZE_SHRINK_BEGIN
		)
		_tutorial_body.add_theme_font_size_override("font_size", 15 if _layout_narrow else 18)
		_tutorial_panel.anchor_left = 0.04 if _layout_narrow else 0.14
		_tutorial_panel.anchor_right = 0.96 if _layout_narrow else 0.86
		_tutorial_panel.anchor_top = 0.10 if _layout_narrow else 0.12
		_tutorial_panel.anchor_bottom = 0.90 if _layout_narrow else 0.88
	# Focus-first desktop layout: keep at least 66% of the viewport for direct
	# play while retaining the full ledger as a scrollable diegetic record.
	# Narrow portrait screens keep the existing stacked reading surface.
	_bottom_panel.anchor_top = NARROW_LEDGER_TOP if _layout_narrow else WIDE_LEDGER_TOP
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
	_controls_panel.offset_bottom = 128.0 if _layout_narrow else 124.0
	_prompt_panel.anchor_left = 0.08 if _layout_narrow else 0.24
	_prompt_panel.anchor_right = 0.92 if _layout_narrow else 0.76
	_prompt_panel.anchor_top = _bottom_panel.anchor_top
	_prompt_panel.anchor_bottom = _bottom_panel.anchor_top
	_prompt_panel.offset_left = 0.0
	_prompt_panel.offset_right = 0.0
	_prompt_panel.offset_top = -56.0
	_prompt_panel.offset_bottom = -8.0
	_feedback_label.anchor_left = 0.20
	_feedback_label.anchor_right = 0.80
	_feedback_label.anchor_top = 0.0
	_feedback_label.anchor_bottom = 0.0
	_feedback_label.offset_left = 0.0
	_feedback_label.offset_right = 0.0
	_feedback_label.offset_top = 136.0
	_feedback_label.offset_bottom = 168.0
	_toast.anchor_left = 0.12
	_toast.anchor_right = 0.88
	_toast.anchor_top = 0.0
	_toast.anchor_bottom = 0.0
	_toast.offset_left = 0.0
	_toast.offset_right = 0.0
	_toast.offset_top = 174.0
	_toast.offset_bottom = 206.0
	_end_card.anchor_left = 0.04 if _layout_narrow else 0.18
	_end_card.anchor_right = 0.96 if _layout_narrow else 0.82
	_end_card.anchor_top = 0.13 if _layout_narrow else 0.16
	_end_card.anchor_bottom = 0.88 if _layout_narrow else 0.84
	_apply_start_key_art()
	_start_card.anchor_left = 0.05 if _layout_narrow else 0.21
	_start_card.anchor_right = 0.95 if _layout_narrow else 0.79
	_start_card.anchor_top = 0.19 if _layout_narrow else 0.22
	_start_card.anchor_bottom = 0.82 if _layout_narrow else 0.78
	_controls_label.add_theme_font_size_override("font_size", 12 if _layout_narrow else 13)
	_ledger_log.add_theme_font_size_override("normal_font_size", 16 if _layout_narrow else 18)
	_objective_label.add_theme_font_size_override("font_size", 16 if _layout_narrow else 18)
	_status_label.add_theme_font_size_override("font_size", 15 if _layout_narrow else 17)
	_update_portrait_visibility()


func _apply_start_key_art() -> void:
	# Orientation-matched gate art (D-042). Falls back to whichever texture exists.
	if _start_key_art == null:
		return
	var chosen: Texture2D = null
	if _layout_narrow and _start_key_art_portrait != null:
		chosen = _start_key_art_portrait
	elif _start_key_art_landscape != null:
		chosen = _start_key_art_landscape
	else:
		chosen = _start_key_art_portrait
	if chosen != null and _start_key_art.texture != chosen:
		_start_key_art.texture = chosen


func start_key_art_orientation() -> String:
	# Engineering-snapshot helper; reports which gate art the layout selected.
	if _start_key_art == null or _start_key_art.texture == null:
		return "none"
	if _start_key_art.texture == _start_key_art_portrait:
		return "portrait"
	if _start_key_art.texture == _start_key_art_landscape:
		return "landscape"
	return "unknown"


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
		_cursor_label.text = "[READY] CASE READY"
		_start_button.grab_focus()
	_update_gate_motion_state()


func set_play_started(started: bool) -> void:
	_play_started = started
	_start_gate.visible = not started
	set_cursor_captured(started)
	_update_gate_motion_state()


func set_cursor_captured(captured: bool) -> void:
	if not _play_started:
		_cursor_label.text = "[READY] CASE READY"
	elif captured:
		_cursor_label.text = "[LOOK] LOOK ACTIVE"
	else:
		_cursor_label.text = "[CURSOR] CURSOR FREE | CLICK TO RETURN"


func set_audio_state(unlocked: bool, muted: bool) -> void:
	if not unlocked:
		_audio_button.text = "AUDIO LOCKED | V"
	elif muted:
		_audio_button.text = "AUDIO OFF | V"
	else:
		_audio_button.text = "AUDIO ON | V"


func set_progress(stage: int, total: int, phase: String) -> void:
	_progress_total = maxi(1, total)
	_progress_stage = clampi(stage, 0, _progress_total)
	_progress_phase = phase
	_progress_bar.max_value = float(_progress_total)
	_progress_bar.value = float(_progress_stage)
	_update_progress_text()


func _update_progress_text() -> void:
	if _progress_label != null:
		_progress_label.text = "CASE %d/%d | %s" % [_progress_stage, _progress_total, _progress_phase]


func show_prompt(text: String) -> void:
	_prompt_label.text = "[E]  |  " + text
	_prompt_panel.visible = text != ""


func hide_prompt() -> void:
	_prompt_panel.visible = false


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
	_portrait_frame.visible = _portrait.visible
	_ledger_title.text = "HARBOR LEDGER | CASE FILE"
	if _portrait_requested and _layout_narrow and _speaker_name != "":
		_ledger_title.text += " | " + _speaker_name


func ledger_line(kind: String, text: String) -> void:
	# Bureaucratic-poetic ledger voice (W-005): the ledger is a diegetic record
	# of accepted evidence. Commits stamp "COMMITTED", refusals stamp "HELD" — the
	# words of a harbor that survives on valid entries only.
	var line := ""
	match kind:
		"narration":
			line = "[color=#D9D3C4]%s[/color]" % text
		"dialogue":
			line = "[color=#D9D3C4][i]'%s'[/i][/color]" % text
		"proposal":
			line = "[color=#A77A3A][P] PROPOSAL ... %s[/color]" % text
		"commit":
			line = "[color=#F2B84B][C] COMMITTED -- %s[/color]" % text
			_show_ledger_stamp(true)
		"refusal":
			line = "[color=#D9685F][H] HELD -| %s[/color]" % text
		"hint":
			line = "[color=#F2B84B][L] LEAD - %s[/color]" % text
		_:
			line = text
	_ledger_log.append_text(line + "\n")


func ledger_commit(entry_number: int, text: String) -> void:
	# Numbered commit entry: 'ENTRY #N | COMMITTED — <entry>'. The entry number is the
	# caller's validated commit count — presentation mirrors it, never invents it.
	_ledger_log.append_text(
		"[color=#F2B84B][C] ENTRY #%d | COMMITTED - %s[/color]\n" % [entry_number, text]
	)
	_show_ledger_stamp(true)


func ledger_refusal(reason: String, next_affordance: String) -> void:
	# 'HELD — <neutral reason>' then 'NEXT VALID ENTRY: <affordance>'. The reason
	# stays neutral/non-alarming (P-02) and never exposes hidden oracle labels;
	# the next valid entry is always concrete and always present.
	_ledger_log.append_text("[color=#D9685F][H] HELD - %s[/color]\n" % reason)
	_ledger_log.append_text(
		"[color=#A77A3A][N] NEXT VALID ENTRY: %s[/color]\n" % next_affordance
	)
	_show_ledger_stamp(false)


func _show_ledger_stamp(committed: bool) -> void:
	# Tiny diegetic ink stamp beside the newest verdict line. Curated bytes are
	# optional: a missing texture keeps today's text-only ledger exactly.
	if _ledger_stamp == null:
		return
	var texture := _stamp_commit_texture if committed else _stamp_refusal_texture
	if texture == null:
		_ledger_stamp.visible = false
		return
	_ledger_stamp.texture = texture
	_ledger_stamp.visible = true
	_ledger_stamp.modulate = Color(1, 1, 1, 1)
	if _stamp_tween != null and _stamp_tween.is_valid():
		_stamp_tween.kill()
	if reduce_motion:
		# Steady state: appear, hold, hide — no press/scale motion.
		_ledger_stamp.scale = Vector2.ONE
		_stamp_tween = create_tween()
		_stamp_tween.tween_interval(1.6)
		_stamp_tween.tween_callback(func() -> void: _ledger_stamp.visible = false)
		return
	_ledger_stamp.pivot_offset = _ledger_stamp.size * 0.5
	_ledger_stamp.scale = Vector2(1.3, 1.3)
	_stamp_tween = create_tween()
	_stamp_tween.tween_property(_ledger_stamp, "scale", Vector2.ONE, 0.18)\
		.set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_BACK)
	_stamp_tween.tween_interval(1.1)
	_stamp_tween.tween_property(_ledger_stamp, "modulate:a", 0.0, 0.35)
	_stamp_tween.tween_callback(func() -> void: _ledger_stamp.visible = false)


func show_choices(choices: Array) -> void:
	clear_choices()
	for choice in choices:
		var button := Button.new()
		button.text = choice["text"]
		button.custom_minimum_size = Vector2(0.0, 44.0)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.add_theme_font_size_override("font_size", 16 if _layout_narrow else 18)
		_style_button(button)
		var choice_id: String = choice["id"]
		button.pressed.connect(func() -> void: choice_selected.emit(choice_id))
		_choice_box.add_child(button)
	if _choice_box.get_child_count() > 0:
		(_choice_box.get_child(0) as Button).grab_focus()


func clear_choices() -> void:
	for child in _choice_box.get_children():
		child.queue_free()


func set_status(objective: String, status: String) -> void:
	_objective_label.text = "[L] CURRENT LEAD | " + objective
	_status_label.text = status


func flash(kind: String) -> void:
	# <=100 ms local acknowledgement target: color and redundant text land on
	# the next frame. This is presentation feedback, never action authorization.
	var is_commit := kind == "commit"
	var color := Color(PALETTE.signal_amber, 0.22) if is_commit else Color(PALETTE.warning_coral, 0.24)
	_feedback_label.text = "[C] COMMITTED | VALIDATED" if is_commit else "[H] HELD | STATE UNCHANGED"
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


func play_ledger_close(text: String) -> void:
	# Ending 'ledger closes' beat: the ledger panel returns dimmed for one last
	# look, a final case-complete toast lands, and after ~0.6 s the end card slides
	# in. Reduced motion: the card appears immediately (steady semantic state).
	# Purely additive presentation — the canonical receipt lives in the card.
	if reduce_motion:
		show_end_card(text)
		return
	_bottom_panel.visible = true
	_bottom_panel.modulate = Color(1, 1, 1, 1)
	toast("CASE COMPLETE | The ledger is closing.")
	var beat := create_tween()
	beat.tween_property(_bottom_panel, "modulate:a", 0.55, 0.30) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	beat.tween_interval(0.30)
	beat.tween_callback(func() -> void:
		_bottom_panel.visible = false
		_bottom_panel.modulate = Color(1, 1, 1, 1)
		_end_text.text = text
		_end_card.visible = true
		_end_card.modulate = Color(1, 1, 1, 0)
		var base_position := _end_card.position
		_end_card.position = base_position + Vector2(0.0, 26.0)
		var slide := create_tween()
		slide.tween_property(_end_card, "position", base_position, 0.34) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		slide.parallel().tween_property(_end_card, "modulate:a", 1.0, 0.30)
	)


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
		"start_key_art_orientation": start_key_art_orientation(),
		"layout_metrics": {
			"active_bottom_panel_top_fraction": _bottom_panel.anchor_top,
			"wide_playfield_fraction": WIDE_LEDGER_TOP,
			"narrow_playfield_fraction": NARROW_LEDGER_TOP,
		},
		"controls_visible": _controls_panel.visible,
		"control_affordances": ["WASD", "mouse-look", "E", "Escape", "F5", "F9", "M", "V"],
		"start_gate_visible": _start_gate.visible,
		"play_started": _play_started,
		"progress": {"stage": _progress_stage, "total": _progress_total, "phase": _progress_phase},
		"reduced_motion": reduce_motion,
		"semantic_feedback_redundancy": ["color", "icon", "text", "ledger-line"],
	}
