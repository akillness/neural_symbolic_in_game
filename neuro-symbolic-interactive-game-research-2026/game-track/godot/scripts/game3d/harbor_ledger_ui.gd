class_name HarborLedgerUI
extends CanvasLayer

## Harbor Ledger presentation surface (SL-PRESENT-001 layout: scene-forward,
## responsive ledger/action dock). Every semantic color carries a text/icon
## redundancy; refusals show a neutral reason plus the next valid affordance
## and never expose hidden oracle labels.
##
## D-073 composition (Aside deep research 2026-09-18, detective tutorial HUD):
## four anchor-pinned zones inside one safe-area margin — top-left objective +
## opt-in hint ladder, top-centre case chain, top-right handle buttons with an
## unread case-file pip, bottom-centre prompt above the ledger dock. The case
## chain N/3 is the only progress number on screen. Held rows are permanent
## and carry PROPOSAL -> RULE -> WHAT THIS TELLS YOU. Every tween is gated by
## `reduce_motion` (steady state).

signal choice_selected(choice_id: String)
signal start_requested
signal audio_toggle_requested
signal tutorial_closed
signal tutorial_requested
signal case_file_requested
signal hint_requested
signal coach_card_dismissed(card_id: String)
signal npc_capability_submitted(text: String)
signal npc_text_submitted(text: String)
signal npc_cancel_requested

const PALETTE := SealedLighthouseWorldBuilder.PALETTE
const NARROW_WIDTH := 900.0
const NARROW_LEDGER_TOP := 0.58
const WIDE_LEDGER_TOP := 0.78
# D-070: WIDE_LEDGER_TOP is a percentage anchor with no absolute pixel floor.
# On a shrunk canvas (e.g. embedded in the commit-gate dashboard iframe,
# which can render well below the project's authored 1280x720), 34% of a
# short viewport leaves less room than the action/ledger columns need,
# pushing dialogue choice buttons below the visible canvas edge instead of
# reflowing or scrolling. This is the minimum panel height (px) the wide
# layout guarantees regardless of viewport height.
# (D-073: measured against the safe-area inner height; 180 px keeps the
# portrait column's minimum — compact log + status line + panel margins —
# while leaving most of the viewport for direct play. Raised anchors
# (narrow 0.58 / wide 0.78) plus a translucent dock keep the ledger from
# covering the playfield in the embedded web build.)
const MIN_BOTTOM_PANEL_HEIGHT := 180.0
const UI_FONT := preload("res://assets/fonts/NanumGothic-Regular.ttf")
# Start-gate key-art drift: one shared 12 s sine drives a ±0.5% scale breathe
# and a ±4 px lateral drift (mouse-independent). The 1.5% base overscan keeps
# the art covering the gate through both extremes; reduced motion rests at the
# base pose and absent art bytes disable the effect entirely.
const GATE_DRIFT_PERIOD_S := 12.0
const GATE_DRIFT_PIXELS := 4.0
const GATE_SCALE_BREATHE := 0.005
const GATE_ART_BASE_SCALE := 1.015
# Safe-area fallback (design px) when the display reports no inset (desktop
# and the 390x844 browser build both do); DisplayServer insets only ever grow it.
const SAFE_AREA_FALLBACK := {"top": 24, "bottom": 20, "left": 12, "right": 12}
# Type floors (design px at 1280x720; 28 px at 1080p is the GAG minimum, so
# body text is >= 20 and time-pressure text >= 24). Narrow uses the second
# value of each pair.
const TYPE_SCALE := {
	"objective": [24, 18],
	"ledger": [20, 16],
	"dialogue": [22, 18],
	"chain": [18, 16],
	"hash": [18, 16],
}
const TOUCH_TARGET := 44.0
const END_CARD_PAGES := 3

var reduce_motion: bool = false
var _screen_under: Control
var _safe_area: MarginContainer
var _root: Control
var _screen_over: Control
var _ui_theme: Theme
var _ledger_log: RichTextLabel
var _ledger_title: Label
var _ledger_box: VBoxContainer
var _choice_box: VBoxContainer
var _choice_scroll: ScrollContainer
var _choice_caption: Label
var _choice_ids: Array = []
var _action_box: VBoxContainer
var _columns: BoxContainer
var _prompt_panel: PanelContainer
var _prompt_label: Label
var _status_label: Label
var _npc_status_label: Label
var _npc_capability_row: HBoxContainer
var _npc_capability_edit: LineEdit
var _npc_capability_button: Button
var _npc_input_row: HBoxContainer
var _npc_line_edit: LineEdit
var _npc_send_button: Button
var _npc_cancel_button: Button
var _objective_label: Label
var _case_chain_label: Label
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
var _end_hash_row: HBoxContainer
var _end_hash_field: LineEdit
var _end_copy_button: Button
var _end_page_label: Label
var _end_prev: Button
var _end_next: Button
var _end_pages: Array = []
var _end_page_index: int = 0
var _end_hash: String = ""
var _ledger_stamp: TextureRect
var _stamp_commit_texture: Texture2D
var _stamp_refusal_texture: Texture2D
var _stamp_tween: Tween
var _bottom_panel: PanelContainer
var _top_bar: BoxContainer
var _dock_top_base: float = WIDE_LEDGER_TOP
var _zone_objective: VBoxContainer
var _zone_chain: PanelContainer
var _zone_handles: VBoxContainer
var _handles_row: HBoxContainer
var _eyebrow_label: Label
var _controls_label: Label
var _cursor_label: Label
var _audio_button: Button
var _guide_button: Button
var _case_file_button: Button
var _hint_button: Button
var _hint_panel: PanelContainer
var _hint_label: Label
var _hint_rung: int = 0
var _hint_lines: Array = []
var _case_file_unread: int = 0
var _progress_stage: int = 0
var _progress_total: int = 3
var _progress_phase: String = "ARRIVAL"
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
var _tutorial_page_count: int = 1
var _coach_cards: Dictionary = {}
var _coach_panel: PanelContainer
var _coach_title: Label
var _coach_body: Label
var _coach_ok: Button
var _coach_card_id: String = ""
var _evidence_panel: PanelContainer
var _evidence_title: Label
var _evidence_cards_box: GridContainer
var _evidence_chain_label: Label
var _evidence_next_label: Label
var _evidence_hint_label: Label
var _evidence_icons: Dictionary = {}
var _evidence_snapshot: Dictionary = {}
var _inventory_row: HBoxContainer
var _inventory_icon: TextureRect
var _layout_narrow: bool = false
var _play_started: bool = false
var _portrait_requested: bool = false
var _speaker_name: String = ""
var _case_chain_snapshot: Dictionary = {}
var _rules_learned_snapshot: Array = []
var _last_rule_line: String = ""
var _last_inference_line: String = ""
var _contribution_lines: int = 0
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
	_ui_theme = Theme.new()
	var ui_font := FontVariation.new()
	ui_font.base_font = UI_FONT
	var ui_fallbacks: Array[Font] = [ThemeDB.fallback_font]
	ui_font.fallbacks = ui_fallbacks
	_ui_theme.default_font = ui_font

	# Three full-rect layers: `_screen_under` (letterbox bars + verdict flash,
	# below every panel so text is never tinted), the safe-area margin holding
	# `_root` (every HUD zone, dock, overlay and card), and `_screen_over`
	# (the start gate, which must cover the whole display including insets).
	_screen_under = Control.new()
	_screen_under.set_anchors_preset(Control.PRESET_FULL_RECT)
	_screen_under.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_screen_under.theme = _ui_theme
	add_child(_screen_under)
	_letterbox_top = _make_bar(_screen_under, true)
	_letterbox_bottom = _make_bar(_screen_under, false)
	_flash = ColorRect.new()
	_flash.set_anchors_preset(Control.PRESET_FULL_RECT)
	_flash.color = Color(0, 0, 0, 0)
	_flash.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_screen_under.add_child(_flash)

	_safe_area = MarginContainer.new()
	_safe_area.set_anchors_preset(Control.PRESET_FULL_RECT)
	_safe_area.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_safe_area.theme = _ui_theme
	add_child(_safe_area)
	_root = Control.new()
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_safe_area.add_child(_root)

	_screen_over = Control.new()
	_screen_over.set_anchors_preset(Control.PRESET_FULL_RECT)
	_screen_over.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_screen_over.theme = _ui_theme
	add_child(_screen_over)

	_build_top_bar()

	_feedback_label = Label.new()
	_feedback_label.add_theme_font_size_override("font_size", 20)
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
	_prompt_label.add_theme_font_size_override("font_size", 20)
	_prompt_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_prompt_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_prompt_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_prompt_panel.add_child(_prompt_label)

	_build_bottom_panel()
	_build_toast()
	_build_evidence_board()
	_build_coach_card()
	_build_end_card()
	_build_tutorial()
	_build_start_gate()


func _build_top_bar() -> void:
	# D-073 zones: one anchor-pinned bar across the top of the safe area.
	# Wide: [objective + hint ladder | case chain | handles] side by side.
	# Narrow: the three zones stack (objective, chain, handles). No offsets are
	# hand-placed; every zone is a container child.
	_top_bar = BoxContainer.new()
	_top_bar.vertical = false
	_top_bar.add_theme_constant_override("separation", 10)
	_top_bar.anchor_left = 0.0
	_top_bar.anchor_right = 1.0
	_top_bar.anchor_top = 0.0
	_top_bar.anchor_bottom = 0.0
	_top_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(_top_bar)
	_top_bar.resized.connect(_place_transients)
	_root.resized.connect(_place_transients)

	# Zone 1 — objective + opt-in hint ladder (top-left).
	_zone_objective = VBoxContainer.new()
	_zone_objective.add_theme_constant_override("separation", 6)
	_zone_objective.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_zone_objective.size_flags_stretch_ratio = 1.45
	_zone_objective.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top_bar.add_child(_zone_objective)
	var objective_panel := PanelContainer.new()
	objective_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.92), Color(PALETTE.brass, 0.78), 1, 10)
	)
	objective_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_zone_objective.add_child(objective_panel)
	var objective_stack := VBoxContainer.new()
	objective_stack.add_theme_constant_override("separation", 6)
	objective_panel.add_child(objective_stack)
	_objective_label = Label.new()
	_objective_label.add_theme_font_size_override("font_size", 24)
	_objective_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	_objective_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_objective_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	objective_stack.add_child(_objective_label)
	var hint_row := HBoxContainer.new()
	hint_row.add_theme_constant_override("separation", 8)
	objective_stack.add_child(hint_row)
	_hint_button = Button.new()
	_hint_button.custom_minimum_size = Vector2(124.0, 30.0)
	_hint_button.add_theme_font_size_override("font_size", 13)
	_hint_button.focus_mode = Control.FOCUS_NONE
	_style_button(_hint_button)
	_hint_button.pressed.connect(func() -> void: hint_requested.emit())
	hint_row.add_child(_hint_button)
	_hint_panel = PanelContainer.new()
	_hint_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.35), Color(PALETTE.brass, 0.55), 1, 6)
	)
	_hint_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_hint_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hint_panel.visible = false
	hint_row.add_child(_hint_panel)
	_hint_label = Label.new()
	_hint_label.add_theme_font_size_override("font_size", 14)
	_hint_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_hint_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hint_panel.add_child(_hint_label)
	_update_hint_button()

	# Zone 2 — case chain (top-centre). Filled/hollow ASCII markers carry the
	# state; the brass connectors are drawn at >= 3:1 against storm ink.
	_zone_chain = PanelContainer.new()
	_zone_chain.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.92), Color(PALETTE.brass, 0.78), 1, 10)
	)
	_zone_chain.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_zone_chain.size_flags_stretch_ratio = 1.0
	_zone_chain.size_flags_vertical = Control.SIZE_SHRINK_BEGIN
	_zone_chain.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top_bar.add_child(_zone_chain)
	var chain_stack := VBoxContainer.new()
	chain_stack.add_theme_constant_override("separation", 2)
	_zone_chain.add_child(chain_stack)
	var chain_eyebrow := Label.new()
	chain_eyebrow.text = "CASE CHAIN"
	chain_eyebrow.add_theme_font_size_override("font_size", 11)
	chain_eyebrow.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.72))
	chain_eyebrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	chain_stack.add_child(chain_eyebrow)
	_case_chain_label = Label.new()
	_case_chain_label.add_theme_font_size_override("font_size", 18)
	_case_chain_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_case_chain_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_case_chain_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_case_chain_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	chain_stack.add_child(_case_chain_label)
	_render_case_chain()

	# Zone 3 — handles (top-right): field guide, case file with unread pip,
	# audio; then a one-line pointer/controls eyebrow.
	_zone_handles = VBoxContainer.new()
	_zone_handles.add_theme_constant_override("separation", 4)
	_zone_handles.size_flags_horizontal = Control.SIZE_SHRINK_END
	_zone_handles.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_top_bar.add_child(_zone_handles)
	_handles_row = HBoxContainer.new()
	_handles_row.add_theme_constant_override("separation", 6)
	_handles_row.alignment = BoxContainer.ALIGNMENT_END
	_zone_handles.add_child(_handles_row)
	_guide_button = Button.new()
	_guide_button.text = "[T] GUIDE"
	_guide_button.custom_minimum_size = Vector2(96.0, 32.0)
	_guide_button.add_theme_font_size_override("font_size", 13)
	_guide_button.focus_mode = Control.FOCUS_NONE
	_style_button(_guide_button)
	_guide_button.pressed.connect(func() -> void: tutorial_requested.emit())
	_handles_row.add_child(_guide_button)
	_case_file_button = Button.new()
	_case_file_button.custom_minimum_size = Vector2(150.0, 32.0)
	_case_file_button.add_theme_font_size_override("font_size", 13)
	_case_file_button.focus_mode = Control.FOCUS_NONE
	_style_button(_case_file_button)
	_case_file_button.pressed.connect(func() -> void: case_file_requested.emit())
	_handles_row.add_child(_case_file_button)
	_update_case_file_button()
	_audio_button = Button.new()
	_audio_button.text = "[V] AUDIO LOCKED"
	_audio_button.custom_minimum_size = Vector2(150.0, 32.0)
	_audio_button.add_theme_font_size_override("font_size", 13)
	_audio_button.focus_mode = Control.FOCUS_NONE
	_style_button(_audio_button)
	_audio_button.pressed.connect(func() -> void: audio_toggle_requested.emit())
	_handles_row.add_child(_audio_button)
	_eyebrow_label = Label.new()
	_eyebrow_label.add_theme_font_size_override("font_size", 12)
	_eyebrow_label.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.78))
	_eyebrow_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	_eyebrow_label.add_theme_constant_override("shadow_offset_x", 1)
	_eyebrow_label.add_theme_constant_override("shadow_offset_y", 1)
	_eyebrow_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_eyebrow_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_eyebrow_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_zone_handles.add_child(_eyebrow_label)
	# `_cursor_label` / `_controls_label` keep their historic roles (pointer
	# state text; controls reference) and are folded into the one eyebrow line.
	_cursor_label = Label.new()
	_cursor_label.text = "[READY] CASE READY"
	_cursor_label.visible = false
	_zone_handles.add_child(_cursor_label)
	_controls_label = Label.new()
	_controls_label.text = "WASD MOVE | MOUSE LOOK | [E] INSPECT | [Esc] CURSOR | [F5]/[F9] SAVE/LOAD | [M] MOTION | [H] HINT"
	_controls_label.visible = false
	_zone_handles.add_child(_controls_label)
	_update_eyebrow()


func _update_eyebrow() -> void:
	if _eyebrow_label == null:
		return
	_eyebrow_label.text = "TRACE-RPG | CASE 01 | %s\n%s" % [_cursor_label.text, _controls_label.text]


func _build_bottom_panel() -> void:
	_bottom_panel = PanelContainer.new()
	_bottom_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.70), PALETTE.brass, 2, 10)
	)
	_bottom_panel.anchor_left = 0.0
	_bottom_panel.anchor_right = 1.0
	_bottom_panel.anchor_bottom = 1.0
	_root.add_child(_bottom_panel)
	_bottom_panel.visible = false
	_add_parchment_grain(_bottom_panel)

	_columns = BoxContainer.new()
	_columns.vertical = false
	_columns.add_theme_constant_override("separation", 12)
	_bottom_panel.add_child(_columns)

	_portrait_box = VBoxContainer.new()
	_portrait_box.custom_minimum_size = Vector2(160.0, 0.0)
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
	_portrait.custom_minimum_size = Vector2(160.0, 160.0)
	var portrait_texture := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-mira-portrait.png")
	if portrait_texture == null:
		portrait_texture = SealedLighthouseWorldBuilder.load_pack_texture(
			"SL3D-P01-mira-dialogue-portrait.png"
		)
	_portrait.texture = portrait_texture
	_portrait.visible = false
	_portrait_frame.add_child(_portrait)
	_speaker_label = Label.new()
	_speaker_label.add_theme_font_size_override("font_size", 16)
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
	_ledger_log.add_theme_font_size_override("normal_font_size", 20)
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
	# One compact status line (stage / phase / inventory / entries / holds).
	# The case chain N/3 stays the only progress number; these are receipts.
	_status_label = Label.new()
	_status_label.add_theme_font_size_override("font_size", 16)
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
	# Choice-list caption: names what the list is asking for (e.g. the
	# deduction slot being filled). Empty and hidden outside such prompts.
	_choice_caption = Label.new()
	_choice_caption.add_theme_font_size_override("font_size", 16)
	_choice_caption.add_theme_color_override("font_color", PALETTE.brass)
	_choice_caption.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_choice_caption.visible = false
	_action_box.add_child(_choice_caption)

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
	# D-074: the scroll container reports almost no minimum size of its own
	# (that is the point of a scroll view), so on a short, narrow canvas the
	# narrow dock ratio in _apply_dock_ratios() can hand it less height than
	# a single authored choice button needs once its label wraps (R4 mobile
	# dashboard embed measured 344x720 -- half the tuned 713x720 reference --
	# squeezed the scripted Mira choice list to a sliver no scroll offset
	# could bring a button fully into). Reacting to the container's own
	# sort_children signal (fired by Godot after autowrap settles each
	# button's real height) and mirroring that as the scroll's floor lets
	# Control's normal combined-minimum-size growth lift _bottom_panel just
	# enough, with zero touch to the dock anchors/ratios above. Clearing the
	# list drops the floor back to 0 so the compact no-choice dock is
	# unaffected.
	_choice_box.sort_children.connect(_on_choice_box_sorted)
	_npc_status_label = Label.new()
	_npc_status_label.text = "NPC BACKEND | CODEX | NOT CONNECTED"
	_npc_status_label.add_theme_font_size_override("font_size", 14)
	_npc_status_label.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.1))
	_npc_capability_row = HBoxContainer.new()
	_npc_capability_row.add_theme_constant_override("separation", 6)
	_npc_capability_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_npc_capability_row.visible = false
	_action_box.add_child(_npc_capability_row)
	_npc_capability_edit = LineEdit.new()
	_npc_capability_edit.placeholder_text = "NPC capability (memory only)"
	_npc_capability_edit.secret = true
	_npc_capability_edit.max_length = 512
	_npc_capability_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_npc_capability_edit.custom_minimum_size = Vector2(0.0, TOUCH_TARGET)
	_npc_capability_edit.add_theme_font_size_override("font_size", 14)
	_npc_capability_edit.add_theme_stylebox_override("normal", _panel_style(Color(PALETTE.storm_ink, 0.96), Color(PALETTE.wet_slate, 0.95), 1, 8))
	_npc_capability_edit.add_theme_stylebox_override("focus", _panel_style(Color(PALETTE.storm_ink, 0.98), PALETTE.signal_amber, 2, 8))
	_npc_capability_edit.text_submitted.connect(func(text: String) -> void: npc_capability_submitted.emit(text))
	_npc_capability_row.add_child(_npc_capability_edit)
	_npc_capability_button = Button.new()
	_npc_capability_button.text = "CONNECT"
	_npc_capability_button.custom_minimum_size = Vector2(96.0, TOUCH_TARGET)
	_style_button(_npc_capability_button, true)
	_npc_capability_button.pressed.connect(func() -> void: npc_capability_submitted.emit(_npc_capability_edit.text))
	_npc_capability_row.add_child(_npc_capability_button)
	_npc_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_npc_status_label.visible = false
	_action_box.add_child(_npc_status_label)
	_npc_input_row = HBoxContainer.new()
	_npc_input_row.add_theme_constant_override("separation", 6)
	_npc_input_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_npc_input_row.visible = false
	_action_box.add_child(_npc_input_row)
	_npc_line_edit = LineEdit.new()
	_npc_line_edit.placeholder_text = "Ask Captain Mira"
	_npc_line_edit.max_length = 1000
	_npc_line_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_npc_line_edit.custom_minimum_size = Vector2(0.0, TOUCH_TARGET)
	_npc_line_edit.add_theme_font_size_override("font_size", 16)
	_npc_line_edit.add_theme_stylebox_override("normal", _panel_style(Color(PALETTE.storm_ink, 0.96), Color(PALETTE.wet_slate, 0.95), 1, 8))
	_npc_line_edit.add_theme_stylebox_override("focus", _panel_style(Color(PALETTE.storm_ink, 0.98), PALETTE.signal_amber, 2, 8))
	_npc_line_edit.text_submitted.connect(func(text: String) -> void: npc_text_submitted.emit(text))
	_npc_input_row.add_child(_npc_line_edit)
	_npc_send_button = Button.new()
	_npc_send_button.text = "SEND"
	_npc_send_button.custom_minimum_size = Vector2(72.0, TOUCH_TARGET)
	_style_button(_npc_send_button, true)
	_npc_send_button.pressed.connect(func() -> void: npc_text_submitted.emit(_npc_line_edit.text))
	_npc_input_row.add_child(_npc_send_button)
	_npc_cancel_button = Button.new()
	_npc_cancel_button.text = "CANCEL"
	_npc_cancel_button.custom_minimum_size = Vector2(84.0, TOUCH_TARGET)
	_style_button(_npc_cancel_button)
	_npc_cancel_button.pressed.connect(func() -> void: npc_cancel_requested.emit())
	_npc_input_row.add_child(_npc_cancel_button)


func _build_evidence_board() -> void:
	# D-073 case file: a modal board ([C] / CASE FILE handle) whose title is
	# the open question the case answers. Its three chain slots are present and
	# unfilled from the first frame; a fourth card records the sealed entry
	# without ever naming it. Fill states and labels are handed in by the
	# controller from the committed snapshot through the fail-closed FACT_LABEL
	# allowlist. Curated parchment board + card icons are optional: absent bytes
	# leave the flat storm-ink panel and the ASCII [x]/[ ]/[S] markers, which
	# carry the same meaning on their own.
	_evidence_panel = PanelContainer.new()
	_evidence_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.97), PALETTE.brass, 2, 16)
	)
	_evidence_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	_evidence_panel.visible = false
	_root.add_child(_evidence_panel)
	var board_texture := SealedLighthouseWorldBuilder.load_curated_ui_texture("ui-evidence-board.png")
	if board_texture != null:
		var board := TextureRect.new()
		board.texture = board_texture
		board.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		board.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
		# Darken-modulated toward storm ink so amber/paper-fog text keeps its
		# contrast on the parchment (same discipline as the ledger grain).
		board.modulate = Color(0.40, 0.40, 0.42, 0.9)
		board.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_evidence_panel.add_child(board)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 10)
	_evidence_panel.add_child(stack)
	_evidence_title = Label.new()
	_evidence_title.text = "WHAT OPENED THE TIDE ROUTE?"
	_evidence_title.add_theme_font_size_override("font_size", 22)
	_evidence_title.add_theme_color_override("font_color", PALETTE.signal_amber)
	_evidence_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_evidence_title)
	var subtitle := Label.new()
	subtitle.text = "CASE FILE | Three entries answer it. The ledger fills a card only when it commits the entry."
	subtitle.add_theme_font_size_override("font_size", 14)
	subtitle.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.8))
	subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(subtitle)
# Four cards in one row on wide layouts; a 2x2 grid on narrow portrait
# viewports. The card grid gets its own vertical scroll surface so the modal
# footer remains inside the viewport when narrow cards wrap to multiple lines.
	var cards_scroll := ScrollContainer.new()
	cards_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	cards_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	cards_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	cards_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	stack.add_child(cards_scroll)
	_evidence_cards_box = GridContainer.new()
	_evidence_cards_box.columns = 4
	_evidence_cards_box.add_theme_constant_override("h_separation", 10)
	_evidence_cards_box.add_theme_constant_override("v_separation", 10)
	_evidence_cards_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_evidence_cards_box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	cards_scroll.add_child(_evidence_cards_box)
	for card_id in ["LENS", "MOUNT", "LEAD", "SEALED"]:
		var icon_name := "ui-evidence-%s.png" % str(card_id).to_lower()
		_evidence_icons[card_id] = SealedLighthouseWorldBuilder.load_curated_ui_texture(icon_name)
	_evidence_chain_label = Label.new()
	_evidence_chain_label.add_theme_font_size_override("font_size", 16)
	_evidence_chain_label.add_theme_color_override("font_color", PALETTE.paper_fog)
	_evidence_chain_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_evidence_chain_label)
	_evidence_next_label = Label.new()
	_evidence_next_label.add_theme_font_size_override("font_size", 16)
	_evidence_next_label.add_theme_color_override("font_color", PALETTE.signal_amber)
	_evidence_next_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_evidence_next_label)
	_evidence_hint_label = Label.new()
	_evidence_hint_label.text = "[C] or [Esc] CLOSE CASE FILE"
	_evidence_hint_label.add_theme_font_size_override("font_size", 13)
	_evidence_hint_label.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.74))
	_evidence_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_evidence_hint_label)


func _make_evidence_card(card: Dictionary) -> PanelContainer:
	var filled := bool(card.get("filled", false))
	var sealed := bool(card.get("sealed", false))
	var accent: Color = PALETTE.signal_amber if filled else Color(PALETTE.brass, 0.85)
	if sealed:
		accent = Color(0.62, 0.70, 0.76, 1.0)  # slate: neutral, never a verdict color
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(PALETTE.storm_ink, 0.74), accent, 2 if filled else 1, 8)
	)
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 4)
	panel.add_child(stack)
	var icon_texture: Texture2D = _evidence_icons.get(str(card["id"]), null)
	if icon_texture != null:
		var icon := TextureRect.new()
		icon.texture = icon_texture
		icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.custom_minimum_size = Vector2(0.0, 48.0 if _layout_narrow else 72.0)
		# Unfilled cards keep the icon dim so fill state never depends on the
		# border color alone (the [x]/[ ] marker carries it too).
		icon.modulate = Color(1, 1, 1, 1.0 if (filled or sealed) else 0.42)
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		stack.add_child(icon)
	var head := Label.new()
	var marker := "[S]" if sealed else ("[x]" if filled else "[ ]")
	head.text = "%s %s" % [marker, str(card["id"])]
	head.add_theme_font_size_override("font_size", 18)
	head.add_theme_color_override("font_color", accent)
	stack.add_child(head)
	var body := Label.new()
	body.text = str(card.get("label", ""))
	body.add_theme_font_size_override("font_size", 15)
	body.add_theme_color_override("font_color", PALETTE.paper_fog)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(body)
	var why := Label.new()
	why.text = str(card.get("why", ""))
	why.add_theme_font_size_override("font_size", 13)
	why.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.78))
	why.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(why)
	return panel


func show_evidence_board(
	cards: Array, chain: Dictionary, rules_learned: Array, next_entry: String = ""
) -> void:
	# Renders exactly the cards it is given; never derives a fill state or a
	# label itself. `next_entry` is GoldenPathLayout.next_affordance text.
	# Opening clears the unread pip on the handle button.
	_evidence_snapshot = {
		"cards": cards.duplicate(true),
		"chain": chain.duplicate(true),
		"rules_learned": rules_learned.duplicate(),
		"next_entry": next_entry,
	}
	if _evidence_panel == null:
		return
	for child in _evidence_cards_box.get_children():
		_evidence_cards_box.remove_child(child)
		child.queue_free()
	for card in cards:
		_evidence_cards_box.add_child(_make_evidence_card(card))
	var rules_text := ", ".join(rules_learned) if not rules_learned.is_empty() else "none"
	_evidence_chain_label.text = "CHAIN %d/%d PROVEN | RULES LEARNED | %s" % [
		int(chain.get("filled", 0)), int(chain.get("total", 0)), rules_text
	]
	_evidence_next_label.text = "[N] NEXT VALID ENTRY | %s" % next_entry
	_evidence_next_label.visible = next_entry != ""
	_evidence_panel.visible = true
	_case_file_unread = 0
	_update_case_file_button()


func hide_evidence_board() -> void:
	if _evidence_panel != null:
		_evidence_panel.visible = false


func is_evidence_board_open() -> bool:
	return _evidence_panel != null and _evidence_panel.visible


func mark_case_file_unread() -> void:
	# One pip per commit until the board is opened (D-073: no timed auto-open).
	_case_file_unread += 1
	_update_case_file_button()


func clear_case_file_unread() -> void:
	_case_file_unread = 0
	_update_case_file_button()


func _update_case_file_button() -> void:
	if _case_file_button == null:
		return
	_case_file_button.text = (
		"[C] CASE FILE (%d new)" % _case_file_unread if _case_file_unread > 0 else "[C] CASE FILE"
	)


func set_hint_ladder(rung: int, lines: Array) -> void:
	# Opt-in, non-spoiling hint ladder: rung 0 shows nothing; rungs 1..3 stack
	# the lines the controller authored for the current chain node. View-local
	# state only (the controller resets it on scene enter and after commits).
	_hint_rung = clampi(rung, 0, 3)
	_hint_lines = lines.duplicate()
	if _hint_panel == null:
		return
	_hint_panel.visible = _hint_rung > 0 and not _hint_lines.is_empty()
	var rendered: Array = []
	for line in _hint_lines:
		rendered.append(str(line))
	_hint_label.text = "\n".join(rendered)
	_update_hint_button()


func hint_ladder_text() -> String:
	return _hint_label.text if _hint_label != null else ""


func _update_hint_button() -> void:
	if _hint_button != null:
		_hint_button.text = "[H] HINT %d/3" % _hint_rung


func _build_coach_card() -> void:
	# Just-in-time coach cards (D-073): one interaction, <= 3 ideas, dismissed
	# on player action only ([OK] or Esc, never a timer), styled so they cannot
	# be mistaken for the HUD: lighter parchment stock, italic title.
	_coach_cards = {
		"ledger_intro": {
			"title": "How the ledger works",
			"body": "That amber [C] COMMITTED line means validation passed and the state advanced.\nEvery entry is checked before it is written.\nOnly committed entries change the case.",
		},
		"hold_intro": {
			"title": "What a hold means",
			"body": "A coral [H] HELD line means the ledger kept the sequence; nothing changed.\nEach hold names the gate, the rule, and what that tells you.\nA hold is guidance, not a penalty.",
		},
		"investigate": {
			"title": "How to investigate",
			"body": "Every committed entry becomes a card in the case file [C].\nThe chain LENS -> MOUNT -> LEAD is the spine of the case.\nAt the tide marks you will assemble that chain yourself.",
		},
	}
	_coach_panel = PanelContainer.new()
	_coach_panel.add_theme_stylebox_override(
		"panel", _panel_style(Color(0.86, 0.80, 0.66, 0.97), Color(PALETTE.brass, 0.95), 2, 14)
	)
	_coach_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	_coach_panel.visible = false
	_coach_panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	# The card is a child of the top-right handles zone: the bar grows while
	# the card is open, so every transient (toast, verdict text) is placed
	# below it by measurement — no overlap by construction.
	_zone_handles.add_child(_coach_panel)
	var stack := VBoxContainer.new()
	stack.add_theme_constant_override("separation", 8)
	_coach_panel.add_child(stack)
	var italic := FontVariation.new()
	italic.base_font = UI_FONT
	italic.variation_transform = Transform2D(Vector2(1.0, 0.0), Vector2(0.22, 1.0), Vector2.ZERO)
	_coach_title = Label.new()
	_coach_title.add_theme_font_override("font", italic)
	_coach_title.add_theme_font_size_override("font_size", 20)
	_coach_title.add_theme_color_override("font_color", Color(0.18, 0.15, 0.10))
	_coach_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_coach_title)
	_coach_body = Label.new()
	_coach_body.add_theme_font_size_override("font_size", 16)
	_coach_body.add_theme_color_override("font_color", Color(0.14, 0.12, 0.09))
	_coach_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	stack.add_child(_coach_body)
	var row := HBoxContainer.new()
	row.alignment = BoxContainer.ALIGNMENT_END
	stack.add_child(row)
	_coach_ok = Button.new()
	_coach_ok.text = "[OK] GOT IT"
	_coach_ok.custom_minimum_size = Vector2(120.0, 36.0)
	_coach_ok.add_theme_font_size_override("font_size", 14)
	_style_button(_coach_ok, true)
	_coach_ok.pressed.connect(dismiss_coach_card)
	row.add_child(_coach_ok)


func show_coach_card(card_id: String) -> void:
	if _coach_panel == null or not _coach_cards.has(card_id):
		return
	var card: Dictionary = _coach_cards[card_id]
	_coach_card_id = card_id
	_coach_title.text = str(card["title"])
	_coach_body.text = str(card["body"])
	_coach_panel.visible = true
	_coach_ok.grab_focus()


func dismiss_coach_card() -> void:
	if _coach_panel == null or not _coach_panel.visible:
		return
	_coach_panel.visible = false
	var dismissed := _coach_card_id
	_coach_card_id = ""
	coach_card_dismissed.emit(dismissed)


func is_coach_card_open() -> bool:
	return _coach_panel != null and _coach_panel.visible


func coach_card_ids() -> Array:
	var ids: Array = _coach_cards.keys()
	ids.sort()
	return ids


func _build_toast() -> void:
	_toast = Label.new()
	_toast.add_theme_font_size_override("font_size", 20)
	_toast.add_theme_color_override("font_color", PALETTE.paper_fog)
	_toast.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.92))
	_toast.add_theme_constant_override("shadow_offset_x", 2)
	_toast.add_theme_constant_override("shadow_offset_y", 2)
	_toast.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_toast.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_toast.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_toast.visible = false
	_root.add_child(_toast)


func _build_end_card() -> void:
	# D-073 paged receipt (Obra Dinn's multipage tally): PAGE n/3 with NEXT /
	# BACK, one section per page. Page 3 carries the state hash in a read-only
	# selectable field plus [COPY HASH].
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
	_end_text.add_theme_font_size_override("normal_font_size", 20)
	_end_text.add_theme_color_override("default_color", PALETTE.paper_fog)
	_end_text.size_flags_vertical = Control.SIZE_EXPAND_FILL
	stack.add_child(_end_text)
	_end_hash_row = HBoxContainer.new()
	_end_hash_row.add_theme_constant_override("separation", 8)
	_end_hash_row.visible = false
	stack.add_child(_end_hash_row)
	var hash_caption := Label.new()
	hash_caption.text = "STATE HASH"
	hash_caption.add_theme_font_size_override("font_size", 14)
	hash_caption.add_theme_color_override("font_color", Color(PALETTE.paper_fog, 0.78))
	hash_caption.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_end_hash_row.add_child(hash_caption)
	_end_hash_field = LineEdit.new()
	_end_hash_field.editable = false
	_end_hash_field.selecting_enabled = true
	_end_hash_field.context_menu_enabled = true
	_end_hash_field.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_end_hash_field.custom_minimum_size = Vector2(0.0, 36.0)
	_end_hash_field.add_theme_font_size_override("font_size", 18)
	_end_hash_field.add_theme_color_override("font_color", PALETTE.paper_fog)
	_end_hash_field.add_theme_color_override("font_uneditable_color", PALETTE.paper_fog)
	_end_hash_field.add_theme_stylebox_override(
		"normal", _panel_style(Color(PALETTE.storm_ink, 0.9), Color(PALETTE.brass, 0.78), 1, 6)
	)
	_end_hash_field.add_theme_stylebox_override(
		"read_only", _panel_style(Color(PALETTE.storm_ink, 0.9), Color(PALETTE.brass, 0.78), 1, 6)
	)
	_end_hash_row.add_child(_end_hash_field)
	_end_copy_button = Button.new()
	_end_copy_button.text = "[COPY HASH]"
	_end_copy_button.custom_minimum_size = Vector2(128.0, 36.0)
	_end_copy_button.add_theme_font_size_override("font_size", 14)
	_style_button(_end_copy_button)
	_end_copy_button.pressed.connect(func() -> void:
		DisplayServer.clipboard_set(_end_hash)
		_end_copy_button.text = "[COPIED]"
	)
	_end_hash_row.add_child(_end_copy_button)
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
	_end_icon.custom_minimum_size = Vector2(72.0, 72.0)
	_end_icon.visible = _end_icon.texture != null
	stack.add_child(_end_icon)
	var nav := HBoxContainer.new()
	nav.add_theme_constant_override("separation", 10)
	stack.add_child(nav)
	_end_prev = Button.new()
	_end_prev.text = "< BACK"
	_end_prev.custom_minimum_size = Vector2(96.0, TOUCH_TARGET)
	_end_prev.add_theme_font_size_override("font_size", 16)
	_style_button(_end_prev)
	_end_prev.pressed.connect(func() -> void: _end_go(-1))
	nav.add_child(_end_prev)
	_end_page_label = Label.new()
	_end_page_label.add_theme_font_size_override("font_size", 16)
	_end_page_label.add_theme_color_override("font_color", PALETTE.paper_fog.darkened(0.15))
	_end_page_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_end_page_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	nav.add_child(_end_page_label)
	_end_next = Button.new()
	_end_next.text = "NEXT >"
	_end_next.custom_minimum_size = Vector2(120.0, TOUCH_TARGET)
	_end_next.add_theme_font_size_override("font_size", 16)
	_style_button(_end_next, true)
	_end_next.pressed.connect(func() -> void: _end_go(1))
	nav.add_child(_end_next)


func set_end_card_hash(state_hash: String) -> void:
	_end_hash = state_hash
	if _end_hash_field != null:
		_end_hash_field.text = state_hash
	if _end_copy_button != null:
		_end_copy_button.text = "[COPY HASH]"


func _end_go(step: int) -> void:
	if _end_pages.is_empty():
		return
	_end_page_index = clampi(_end_page_index + step, 0, _end_pages.size() - 1)
	_apply_end_page()


func _apply_end_page() -> void:
	if _end_pages.is_empty():
		return
	_end_text.text = str(_end_pages[_end_page_index])
	var last := _end_page_index == _end_pages.size() - 1
	_end_hash_row.visible = last and _end_hash != ""
	_end_page_label.text = "PAGE %d/%d" % [_end_page_index + 1, _end_pages.size()]
	_end_prev.disabled = _end_page_index == 0
	_end_next.disabled = last
	if last:
		_end_prev.grab_focus()
	else:
		_end_next.grab_focus()


func end_card_page_count() -> int:
	return _end_pages.size()


func _build_start_gate() -> void:
	_start_gate = ColorRect.new()
	_start_gate.set_anchors_preset(Control.PRESET_FULL_RECT)
	_start_gate.color = Color(PALETTE.storm_ink, 0.91)
	_start_gate.mouse_filter = Control.MOUSE_FILTER_STOP
	_start_gate.visible = false
	_screen_over.add_child(_start_gate)
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
	note.text = "WASD Move | [E] Inspect | [T] Field Guide | [C] Case File | [M] Reduce Motion"
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
	# Field guide (D-073: a reference card, not "the tutorial"). At boot only
	# page 1 is shown — why Mira needs the signal, what the ledger is for, the
	# controls in one line. [T] / the GUIDE handle reopen all four pages any
	# time. Pages 2 and 3 also exist as just-in-time coach cards; page 4 is the
	# investigation method. Illustrations are optional (curated first, reviewed
	# concept candidates as desktop fallback) so every page reads without them.
	_tutorial_pages = [
		{
			"title": "WHY THE HARBOR NEEDS YOU",
			"body": "The lighthouse went dark in the storm. Captain Mira cannot open the channel until the harbor signal is restored.\n\nThe Harbor Ledger records only entries that pass validation. That is how this harbor survived.\n\nThe amber beacon marks your current lead.\n\nWASD move | mouse look | [E] inspect | [T] guide | [C] case file | [H] hint | [Esc] cursor",
			"curated": "ui-tutorial-vignette.png",
			"image": "SL3D-U01-signal-lens-icon.png",
			"pack": true,
		},
		{
			"title": "HOW THE HARBOR LEDGER WORKS",
			"body": "[P] Brass dotted line = PROPOSAL. The world has not changed yet.\n[C] Amber line = COMMITTED. Validation passed and the state advanced.\n[H] Coral line = HELD. State stays unchanged, with a neutral reason and the next valid entry.\n\nColor always appears with text and symbols.",
			"image": "SL-C03-investigation-ui.png",
			"pack": false,
		},
		{
			"title": "WHAT A HOLD MEANS",
			"body": "A hold is guidance, not punishment.\n\nEvery held row stays in the ledger and reads PROPOSAL -> RULE -> WHAT THIS TELLS YOU.\n\nThe rules you learn from holds are the case: they say which entries can ever be written.",
			"image": "SL-C02-captain-mira-sheet.png",
			"pack": false,
		},
		{
			"title": "HOW TO INVESTIGATE",
			"body": "Every committed entry becomes a card in the case file [C]. The chain LENS -> MOUNT -> LEAD is the spine of the case; the board asks what opened the tide route.\n\nAt the tide marks you assemble that chain yourself, one slot at a time, from the ledger's own entries. The whole chain is checked at once.\n\nStuck? [H] HINT climbs three rungs: the open question, the place or person, then the next valid entry.",
			"curated": "ui-tutorial-investigate.png",
			"image": "SL-C03-investigation-ui.png",
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
	_tutorial_body.add_theme_font_size_override("font_size", 20)
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
	_tutorial_prev.custom_minimum_size = Vector2(96.0, TOUCH_TARGET)
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
	_tutorial_next.custom_minimum_size = Vector2(150.0, TOUCH_TARGET)
	_tutorial_next.add_theme_font_size_override("font_size", 16)
	_style_button(_tutorial_next, true)
	_tutorial_next.pressed.connect(func() -> void: _tutorial_go(1))
	nav.add_child(_tutorial_next)


func show_tutorial(full_guide: bool = false) -> void:
	# Boot shows page 1 only; `full_guide` (the [T] key / GUIDE handle) opens
	# the whole four-page reference card.
	_tutorial_index = 0
	_tutorial_page_count = _tutorial_pages.size() if full_guide else 1
	_tutorial_panel.visible = true
	_apply_tutorial_page()


func hide_tutorial() -> void:
	_tutorial_panel.visible = false
	tutorial_closed.emit()


func is_tutorial_open() -> bool:
	return _tutorial_panel != null and _tutorial_panel.visible


func tutorial_page_count() -> int:
	return _tutorial_pages.size()


func _tutorial_go(step: int) -> void:
	if _tutorial_index + step >= _tutorial_page_count:
		hide_tutorial()
		return
	_tutorial_index = clampi(_tutorial_index + step, 0, _tutorial_page_count - 1)
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
	_tutorial_progress.text = "%d / %d" % [_tutorial_index + 1, _tutorial_page_count]
	_tutorial_prev.disabled = _tutorial_index == 0
	_tutorial_next.text = (
		"START CASE >" if _tutorial_index == _tutorial_page_count - 1 else "NEXT >"
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
	button.add_theme_stylebox_override(
		"disabled", _panel_style(Color(PALETTE.storm_ink, 0.6), Color(PALETTE.brass, 0.4), 1, 8)
	)
	button.add_theme_color_override("font_color", text_color)
	button.add_theme_color_override("font_hover_color", PALETTE.storm_ink)
	button.add_theme_color_override("font_pressed_color", PALETTE.paper_fog)
	button.add_theme_color_override("font_focus_color", text_color)
	button.add_theme_color_override("font_disabled_color", Color(PALETTE.paper_fog, 0.55))
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


func _apply_safe_area(viewport_size: Vector2) -> Dictionary:
	# Safe-area margin with a fixed fallback: DisplayServer insets (Android
	# cutouts) only ever grow the fallback; desktop and browser report none.
	var margins := SAFE_AREA_FALLBACK.duplicate()
	var safe := DisplayServer.get_display_safe_area()
	var window_size := Vector2(DisplayServer.window_get_size())
	if safe.size.x > 0 and safe.size.y > 0 and window_size.x > 0.0 and window_size.y > 0.0:
		var scale_x := viewport_size.x / window_size.x
		var scale_y := viewport_size.y / window_size.y
		margins["left"] = maxi(int(safe.position.x * scale_x), int(margins["left"]))
		margins["top"] = maxi(int(safe.position.y * scale_y), int(margins["top"]))
		margins["right"] = maxi(
			int((window_size.x - safe.end.x) * scale_x), int(margins["right"])
		)
		margins["bottom"] = maxi(
			int((window_size.y - safe.end.y) * scale_y), int(margins["bottom"])
		)
	_safe_area.add_theme_constant_override("margin_left", int(margins["left"]))
	_safe_area.add_theme_constant_override("margin_top", int(margins["top"]))
	_safe_area.add_theme_constant_override("margin_right", int(margins["right"]))
	_safe_area.add_theme_constant_override("margin_bottom", int(margins["bottom"]))
	return margins


func _apply_responsive_layout() -> void:
	if _bottom_panel == null:
		return
	var viewport_size := get_viewport().get_visible_rect().size
	_layout_narrow = viewport_size.x < NARROW_WIDTH or viewport_size.x < viewport_size.y * 1.25
	var margins := _apply_safe_area(viewport_size)
	var narrow_index := 1 if _layout_narrow else 0
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
		_tutorial_body.add_theme_font_size_override("font_size", 16 if _layout_narrow else 20)
		_tutorial_panel.anchor_left = 0.04 if _layout_narrow else 0.14
		_tutorial_panel.anchor_right = 0.96 if _layout_narrow else 0.86
		_tutorial_panel.anchor_top = 0.10 if _layout_narrow else 0.12
		_tutorial_panel.anchor_bottom = 0.90 if _layout_narrow else 0.88
	# Focus-first desktop layout: keep at least 78% of the viewport for direct
	# play while retaining the ledger as a compact translucent scrollable record.
	# Narrow portrait screens keep the existing stacked reading surface.
	# D-070: clamp the wide-layout anchor so the bottom panel never gets less
	# than MIN_BOTTOM_PANEL_HEIGHT px, even when a host page (e.g. the
	# dashboard iframe) hands this scene a canvas shorter than 1280x720.
	var wide_ledger_top := WIDE_LEDGER_TOP
	var inner_height := viewport_size.y - float(margins["top"]) - float(margins["bottom"])
	if inner_height > 0.0:
		var min_top_for_floor: float = 1.0 - (MIN_BOTTOM_PANEL_HEIGHT / inner_height)
		wide_ledger_top = clampf(min(WIDE_LEDGER_TOP, min_top_for_floor), 0.0, WIDE_LEDGER_TOP)
	_dock_top_base = NARROW_LEDGER_TOP if _layout_narrow else wide_ledger_top
	_bottom_panel.anchor_top = _dock_top_base
	_bottom_panel.offset_left = 0.0
	_bottom_panel.offset_right = 0.0
	_bottom_panel.offset_top = 0.0
	_bottom_panel.offset_bottom = 0.0
	_portrait_box.custom_minimum_size = Vector2(0.0, 0.0) if _layout_narrow else Vector2(160.0, 0.0)
	_ledger_log.custom_minimum_size = Vector2(0.0, 56.0) if _layout_narrow else Vector2.ZERO
	_apply_dock_ratios()

	# Top bar zones: side by side on wide, stacked on narrow. Touch targets
	# grow to 44 px on narrow (SC 2.5.8 / GAG touch guidance).
	_top_bar.vertical = _layout_narrow
	_top_bar.offset_left = 0.0
	_top_bar.offset_right = 0.0
	_top_bar.offset_top = 0.0
	_top_bar.offset_bottom = 0.0
	_zone_handles.size_flags_horizontal = (
		Control.SIZE_EXPAND_FILL if _layout_narrow else Control.SIZE_SHRINK_END
	)
	_handles_row.alignment = BoxContainer.ALIGNMENT_CENTER if _layout_narrow else BoxContainer.ALIGNMENT_END
	var handle_height := TOUCH_TARGET if _layout_narrow else 32.0
	_guide_button.custom_minimum_size = Vector2(88.0 if _layout_narrow else 96.0, handle_height)
	_case_file_button.custom_minimum_size = Vector2(120.0 if _layout_narrow else 150.0, handle_height)
	_audio_button.custom_minimum_size = Vector2(128.0 if _layout_narrow else 150.0, handle_height)
	_hint_button.custom_minimum_size = Vector2(124.0, TOUCH_TARGET if _layout_narrow else 30.0)
	_eyebrow_label.visible = not _layout_narrow
	_objective_label.add_theme_font_size_override("font_size", TYPE_SCALE["objective"][narrow_index])
	_case_chain_label.add_theme_font_size_override("font_size", TYPE_SCALE["chain"][narrow_index])
	_ledger_log.add_theme_font_size_override("normal_font_size", TYPE_SCALE["ledger"][narrow_index])
	_prompt_label.add_theme_font_size_override("font_size", TYPE_SCALE["dialogue"][narrow_index])
	_end_text.add_theme_font_size_override("normal_font_size", TYPE_SCALE["ledger"][narrow_index])
	_end_hash_field.add_theme_font_size_override("font_size", TYPE_SCALE["hash"][narrow_index])
	_status_label.add_theme_font_size_override("font_size", 14 if _layout_narrow else 16)
	if _npc_status_label != null:
		_npc_status_label.add_theme_font_size_override("font_size", 13 if _layout_narrow else 14)
	if _npc_line_edit != null:
		_npc_line_edit.add_theme_font_size_override("font_size", 15 if _layout_narrow else 16)
	_hint_label.add_theme_font_size_override("font_size", 13 if _layout_narrow else 14)
	for child in _choice_box.get_children():
		if child is Button:
			(child as Button).add_theme_font_size_override(
				"font_size", TYPE_SCALE["dialogue"][narrow_index]
			)

	_prompt_panel.anchor_left = 0.06 if _layout_narrow else 0.24
	_prompt_panel.anchor_right = 0.94 if _layout_narrow else 0.76
	_prompt_panel.anchor_top = _bottom_panel.anchor_top
	_prompt_panel.anchor_bottom = _bottom_panel.anchor_top
	_prompt_panel.offset_left = 0.0
	_prompt_panel.offset_right = 0.0
	_prompt_panel.offset_top = -60.0
	_prompt_panel.offset_bottom = -8.0
	_end_card.anchor_left = 0.02 if _layout_narrow else 0.18
	_end_card.anchor_right = 0.98 if _layout_narrow else 0.82
	_end_card.anchor_top = 0.08 if _layout_narrow else 0.12
	_end_card.anchor_bottom = 0.94 if _layout_narrow else 0.90
	# Case file board: modal over the middle of the screen (wide) / most of the
	# height on narrow where the four cards fall into a 2x2 grid.
	_evidence_panel.anchor_left = 0.02 if _layout_narrow else 0.16
	_evidence_panel.anchor_right = 0.98 if _layout_narrow else 0.84
	_evidence_panel.anchor_top = 0.16 if _layout_narrow else 0.14
	_evidence_panel.anchor_bottom = 0.90 if _layout_narrow else 0.86
	_evidence_cards_box.columns = 2 if _layout_narrow else 4
	if _evidence_panel.visible and not _evidence_snapshot.is_empty():
		show_evidence_board(
			_evidence_snapshot["cards"], _evidence_snapshot["chain"],
			_evidence_snapshot["rules_learned"], str(_evidence_snapshot["next_entry"])
		)
	_apply_start_key_art()
	_start_card.anchor_left = 0.05 if _layout_narrow else 0.21
	_start_card.anchor_right = 0.95 if _layout_narrow else 0.79
	_start_card.anchor_top = 0.19 if _layout_narrow else 0.22
	_start_card.anchor_bottom = 0.82 if _layout_narrow else 0.78
	_place_transients()
	_update_portrait_visibility()


func _place_transients() -> void:
	# Toast / verdict feedback / coach card sit directly under the measured
	# top bar (never over a zone) and above the prompt + dock. On narrow the
	# stacked bar can grow past the fixed 38% dock anchor, so the dock is
	# nudged down just enough to keep one 72 px transient band clear.
	if _top_bar == null or _bottom_panel == null or _root == null:
		return
	var bar_bottom := _top_bar.size.y + 8.0
	var root_height := _root.size.y
	var dock_top := _dock_top_base
	if _layout_narrow and root_height > 0.0:
		# While a coach card is open the bar is transiently taller; let the
		# dock drop to 72% so the card is never covered (2026-09-18 embedded
		# 713x720 check showed the 50% cap clipping "What a hold means").
		# The resting cap (0.62) stays below the compact narrow anchor (0.58).
		var dock_cap := 0.72 if is_coach_card_open() else 0.62
		dock_top = clampf(maxf(_dock_top_base, (bar_bottom + 72.0) / root_height), 0.0, dock_cap)
	_bottom_panel.anchor_top = dock_top
	_prompt_panel.anchor_top = dock_top
	_prompt_panel.anchor_bottom = dock_top
	_feedback_label.anchor_left = 0.20
	_feedback_label.anchor_right = 0.80
	_feedback_label.anchor_top = 0.0
	_feedback_label.anchor_bottom = 0.0
	_feedback_label.offset_left = 0.0
	_feedback_label.offset_right = 0.0
	_feedback_label.offset_top = bar_bottom
	_feedback_label.offset_bottom = bar_bottom + 32.0
	_toast.anchor_left = 0.10
	_toast.anchor_right = 0.90
	_toast.anchor_top = 0.0
	_toast.anchor_bottom = 0.0
	_toast.offset_left = 0.0
	_toast.offset_right = 0.0
	_toast.offset_top = bar_bottom + 36.0
	_toast.offset_bottom = bar_bottom + 68.0


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
	if active:
		set_contextual_panel_visible(false)
	_top_bar.visible = not active
	if active:
		hide_evidence_board()


func show_start_gate(visible_now: bool) -> void:
	_start_gate.visible = visible_now
	if visible_now:
		_play_started = false
		_cursor_label.text = "[READY] CASE READY"
		_update_eyebrow()
		_start_button.grab_focus()
	_update_gate_motion_state()


func set_play_started(started: bool) -> void:
	_play_started = started
	_start_gate.visible = not started
	if started:
		set_contextual_panel_visible(false)
	set_cursor_captured(started)
	_update_gate_motion_state()

func set_contextual_panel_visible(visible_now: bool) -> void:
	# The ledger/action dock is contextual: exploration keeps the authored
	# ledger text in memory, while dialogue/choices and explicit capture beats
	# opt into the large panel. This never mutates canonical state.
	if _bottom_panel != null:
		_bottom_panel.visible = visible_now


func set_cursor_captured(captured: bool) -> void:
	if not _play_started:
		_cursor_label.text = "[READY] CASE READY"
	elif captured:
		_cursor_label.text = "[LOOK] LOOK ACTIVE"
	else:
		_cursor_label.text = "[CURSOR] CURSOR FREE | CLICK TO RETURN"
	_update_eyebrow()


func set_audio_state(unlocked: bool, muted: bool) -> void:
	if not unlocked:
		_audio_button.text = "[V] AUDIO LOCKED"
	elif muted:
		_audio_button.text = "[V] AUDIO OFF"
	else:
		_audio_button.text = "[V] AUDIO ON"


func set_progress(stage: int, total: int, phase: String) -> void:
	# Kept as the controller-facing progress API; the HUD no longer renders a
	# second progress number for it (the case chain N/3 is the one), so the
	# phase word is surfaced through the compact status line instead.
	_progress_total = maxi(1, total)
	_progress_stage = clampi(stage, 0, _progress_total)
	_progress_phase = phase


func progress_phase() -> String:
	return _progress_phase


func set_case_chain(chain: Dictionary, rules_learned: Array) -> void:
	# Case-chain HUD zone (Aside search-feedback 2026-09-02 pattern 1): named
	# relationship links, not a bare fraction, so a filled link explains what
	# the last commit contributed. Text-only; presentation reads the committed
	# snapshot and never invents a link state. Rules learned are kept for the
	# case file and the end card (D-073: one progress number on the HUD).
	_case_chain_snapshot = chain.duplicate(true)
	_rules_learned_snapshot = rules_learned.duplicate()
	_render_case_chain()


func _render_case_chain() -> void:
	if _case_chain_label == null:
		return
	var parts: Array = []
	for link in _case_chain_snapshot.get("links", []):
		var mark := "[x]" if bool(link["filled"]) else "[ ]"
		parts.append("%s %s" % [mark, str(link["id"])])
	if parts.is_empty():
		parts = ["[ ] LENS", "[ ] MOUNT", "[ ] LEAD"]
	_case_chain_label.text = " -> ".join(parts)


func case_chain_text() -> String:
	return _case_chain_label.text if _case_chain_label != null else ""


func show_prompt(text: String) -> void:
	_prompt_label.text = "[E]  |  " + text
	_prompt_panel.visible = text != ""


func hide_prompt() -> void:
	_prompt_panel.visible = false


func set_portrait_visible(visible_now: bool, speaker: String = "") -> void:
	_portrait_requested = visible_now
	_speaker_name = speaker
	_speaker_label.text = speaker
	set_contextual_panel_visible(visible_now)
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
	# words of a harbor that survives on valid entries only. Deduction lines
	# (D-073 slot assembly) are the player's own reasoning being checked
	# against the ledger; they are never machine proposals.
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
		"deduction":
			line = "[color=#F2B84B][D] DEDUCTION | %s[/color]" % text
		"deduction_held":
			line = "[color=#8FA3B2][H] DEDUCTION HELD | %s[/color]" % text
		"deduction_confirmed":
			line = "[color=#F2B84B][C] DEDUCTION CONFIRMED | %s[/color]" % text
			_show_ledger_stamp(true)
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


func ledger_refusal(reason: String, next_affordance: String, gate: String = "") -> void:
	# 'HELD — <neutral reason>' then 'NEXT VALID ENTRY: <affordance>'. The reason
	# stays neutral/non-alarming (P-02) and never exposes hidden oracle labels;
	# the next valid entry is always concrete and always present. Held rows are
	# permanent: nothing here fades or collapses them later.
	_ledger_log.append_text("[color=#D9685F][H] HELD - %s[/color]\n" % reason)
	if gate != "":
		# Diegetic mirror of the paper's state-relative predicate that held the
		# entry (Table II of the manuscript). Names the gate, never the hidden
		# oracle, and restates the invariant every hold shares: state unchanged.
		_ledger_log.append_text(
			"[color=#8FA3B2][V] GATE %s | state unchanged[/color]\n" % gate
		)
	_ledger_log.append_text(
		"[color=#A77A3A][N] NEXT VALID ENTRY: %s[/color]\n" % next_affordance
	)
	_show_ledger_stamp(false)


func ledger_contribution(
	entry_number: int, labels: Array, stage_from: int, stage_to: int, filled: int, total: int
) -> void:
	# Causal delta per commit (Aside search-feedback 2026-09-02 pattern 2):
	# names what the entry actually established, not just that it validated.
	# Counts and labels come straight from the caller's committed-snapshot
	# diff (contribution_delta); this function only renders them.
	var label_text := "; ".join(labels) if not labels.is_empty() else "State recorded"
	_ledger_log.append_text(
		"[color=#F2B84B][C] CONTRIBUTION #%d | %s | %s | CHAIN %d/%d[/color]\n" % [
			entry_number, label_text, stage_clause(stage_from, stage_to), filled, total
		]
	)
	_contribution_lines += 1


static func stage_clause(stage_from: int, stage_to: int) -> String:
	# 'STAGE 0>1' when a commit advanced the quest, plain 'STAGE 2' when it did
	# not: an unchanged stage is still a fact worth stating, but '2>2' reads as
	# a failed transition. Shared by the ledger line and the end-card receipt.
	if stage_from == stage_to:
		return "STAGE %d" % stage_to
	return "STAGE %d>%d" % [stage_from, stage_to]


func ledger_unlocked(text: String) -> void:
	# Names the newly available action (Aside search-feedback 2026-09-02
	# pattern 2/3), computed by the caller AFTER the commit so it reflects
	# the state the entry just unlocked, not the state before it.
	_ledger_log.append_text("[color=#A77A3A][N] UNLOCKED | %s[/color]\n" % text)


func ledger_rule(gate: String, rule_text: String, first_time: bool, recall_count: int) -> void:
	# Struggle-is-Spiel companion (Aside search-feedback 2026-09-02 patterns
	# 2 and E): a hold teaches exactly one testable rule the first time it
	# holds a gate, then recalls the same rule on repeat holds of that gate.
	# Neutral paper-fog voice -- a rule is information, never a penalty.
	var plain_line := (
		"RULE LEARNED | %s: %s" % [gate, rule_text]
		if first_time
		else "RULE RECALLED (%d) | %s: %s" % [recall_count, gate, rule_text]
	)
	_ledger_log.append_text("[color=#D9D3C4][V] %s[/color]\n" % plain_line)
	_last_rule_line = plain_line


func ledger_inference(text: String) -> void:
	# D-073 third line of every held row (PROPOSAL -> RULE -> WHAT THIS TELLS
	# YOU): the inference the hold licenses, authored per refusal code by the
	# controller (INFERENCE_BY_CODE). Same paper-fog voice as the rule line.
	var plain_line := "WHAT THIS TELLS YOU | %s" % text
	_ledger_log.append_text("[color=#D9D3C4][V] %s[/color]\n" % plain_line)
	_last_inference_line = plain_line


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


func show_choices(choices: Array, caption: String = "") -> void:
	# `caption` names what the list is asking for (deduction slot prompts);
	# empty hides it so Mira's dialogue keeps its bare choice list.
	set_contextual_panel_visible(true)
	clear_choices()
	_choice_caption.text = caption
	_choice_caption.visible = caption != ""
	var font_size: int = TYPE_SCALE["dialogue"][1 if _layout_narrow else 0]
	for choice in choices:
		var button := Button.new()
		# Number-key shortcut prefix: visible order maps to keys 1..9, so a
		# clipped/scrolled list on a narrow embed stays completable by keyboard.
		# While a coach card is open the list still renders underneath, but
		# focus stays on the card's [OK] so Enter/Space dismisses it first;
		# digits stay inert until then (game_3d.gd skips them while the card
		# is open) instead of firing behind the helper.
		var shortcut_index := _choice_ids.size() + 1
		if shortcut_index <= 9:
			button.text = "[%d] %s" % [shortcut_index, choice["text"]]
		else:
			button.text = choice["text"]
		button.custom_minimum_size = Vector2(0.0, TOUCH_TARGET)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.add_theme_font_size_override("font_size", font_size)
		_style_button(button)
		var choice_id: String = choice["id"]
		_choice_ids.append(choice_id)
		button.pressed.connect(func() -> void: choice_selected.emit(choice_id))
		_choice_box.add_child(button)
	if _choice_box.get_child_count() > 0 and not is_coach_card_open():
		(_choice_box.get_child(0) as Button).grab_focus()
	_apply_dock_ratios()


func _apply_dock_ratios() -> void:
	# Narrow: the objective moved to the top bar, so the ledger normally takes
	# the larger share of the dock. While a choice list is open the action box
	# takes it instead, so all four dialogue choices (or the five deduction
	# options) fit without scrolling in the 713x720 dashboard embed; the list
	# keeps its own scroll as a fallback. Wide keeps the 2.2 : 1 split.
	if _ledger_box == null or _action_box == null:
		return
	var choices_open := _choice_box != null and _choice_box.get_child_count() > 0
	if _layout_narrow and choices_open:
		# Production embed check (713x720, 2026-09-18): 0.9:1.9 still hid the
		# fourth Mira choice; the log keeps a 4-line minimum and the list takes
		# the rest.
		_ledger_box.size_flags_stretch_ratio = 0.55
		_action_box.size_flags_stretch_ratio = 2.45
		_ledger_log.custom_minimum_size = Vector2(0.0, 48.0)
	else:
		_ledger_box.size_flags_stretch_ratio = 1.6 if _layout_narrow else 2.2
		_action_box.size_flags_stretch_ratio = 1.0
		_ledger_log.custom_minimum_size = Vector2(0.0, 56.0) if _layout_narrow else Vector2.ZERO


func clear_choices() -> void:
	_choice_ids = []
	for child in _choice_box.get_children():
		_choice_box.remove_child(child)
		child.queue_free()
	if _choice_caption != null:
		_choice_caption.text = ""
		_choice_caption.visible = false
	_apply_dock_ratios()


func _on_choice_box_sorted() -> void:
	# D-074: mirror the tallest visible choice button's real (post-autowrap)
	# height as the scroll view's floor, so _action_box's combined minimum
	# size can never settle below "at least one authored choice fully
	# readable" regardless of how narrow/short the host canvas is. Governed
	# entirely by the container's own layout pass -- no viewport-size or
	# font-metric guesswork, and it collapses back to 0 the moment the list
	# is cleared (clear_choices() above removes every child, which still
	# fires this same sort_children signal).
	var tallest := 0.0
	for child in _choice_box.get_children():
		if child is Control and (child as Control).visible:
			tallest = maxf(tallest, (child as Control).size.y)
	if _choice_scroll.custom_minimum_size.y != tallest:
		_choice_scroll.custom_minimum_size = Vector2(0.0, tallest)


func choice_count() -> int:
	return _choice_box.get_child_count() if _choice_box != null else 0


func choice_ids() -> Array:
	# Display-order choice ids for the number-key shortcut path in game_3d.gd.
	return _choice_ids.duplicate()

func show_npc_input(visible_now: bool) -> void:
	if _npc_input_row == null:
		return
	_npc_input_row.visible = visible_now
	_npc_capability_row.visible = visible_now and OS.has_feature("web")
	_npc_status_label.visible = visible_now
	if visible_now:
		set_contextual_panel_visible(true)
		if _npc_capability_row.visible and _npc_capability_edit.text.is_empty():
			_npc_capability_edit.grab_focus()
		else:
			_npc_line_edit.grab_focus()
	else:
		_npc_line_edit.clear()
		_npc_capability_edit.clear()


func set_npc_status(text: String) -> void:
	if _npc_status_label != null:
		_npc_status_label.text = text


func set_npc_busy(busy: bool) -> void:
	if _npc_line_edit == null:
		return
	_npc_line_edit.editable = not busy
	_npc_send_button.disabled = busy
	_npc_cancel_button.disabled = false
	_npc_capability_button.disabled = busy
	if not busy:
		_npc_line_edit.grab_focus()


func clear_npc_input() -> void:
	if _npc_line_edit != null:
		_npc_line_edit.clear()


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


func show_end_card(pages: Variant) -> void:
	# Accepts the paged receipt (Array of bbcode strings) or a single string
	# (rendered as one page). Opens on page 1; the hash row shows on the last.
	_end_pages = pages.duplicate() if pages is Array else [str(pages)]
	_end_page_index = 0
	_apply_end_page()
	_end_card.visible = true
	_bottom_panel.visible = false
	_top_bar.visible = false
	hide_evidence_board()


func play_ledger_close(pages: Variant) -> void:
	# Ending 'ledger closes' beat: the ledger panel returns dimmed for one last
	# look, a final case-complete toast lands, and after ~0.6 s the end card slides
	# in. Reduced motion: the card appears immediately (steady semantic state).
	# Purely additive presentation — the canonical receipt lives in the card.
	if reduce_motion:
		show_end_card(pages)
		return
	set_contextual_panel_visible(true)
	_bottom_panel.modulate = Color(1, 1, 1, 1)
	toast("CASE COMPLETE | The ledger is closing.")
	var beat := create_tween()
	beat.tween_property(_bottom_panel, "modulate:a", 0.55, 0.30) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	beat.tween_interval(0.30)
	beat.tween_callback(func() -> void:
		_bottom_panel.modulate = Color(1, 1, 1, 1)
		show_end_card(pages)
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
		"hud_zones": ["objective+hint-ladder:top-left", "case-chain:top-centre", "handles:top-right", "prompt:bottom-centre"],
		"safe_area_fallback": SAFE_AREA_FALLBACK.duplicate(),
		"type_scale": TYPE_SCALE.duplicate(true),
		"controls_visible": _top_bar.visible,
		"control_affordances": ["WASD", "mouse-look", "E", "Escape", "F5", "F9", "M", "V", "T", "C", "H"],
		"start_gate_visible": _start_gate.visible,
		"play_started": _play_started,
		"progress": {"stage": _progress_stage, "total": _progress_total, "phase": _progress_phase},
		"reduced_motion": reduce_motion,
		"semantic_feedback_redundancy": ["color", "icon", "text", "ledger-line"],
		"case_chain": _case_chain_snapshot,
		"case_chain_text": case_chain_text(),
		"rules_learned": _rules_learned_snapshot,
		"contribution_lines": _contribution_lines,
		"last_rule_line": _last_rule_line,
		"last_inference_line": _last_inference_line,
		"hint_ladder": {"rung": _hint_rung, "text": hint_ladder_text()},
		"evidence_board": _evidence_snapshot.duplicate(true),
		"case_file_unread": _case_file_unread,
		"coach_cards": coach_card_ids(),
		"tutorial_pages": tutorial_page_count(),
		"end_card_pages": END_CARD_PAGES,
	}
