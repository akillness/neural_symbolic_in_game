class_name Interactable3D
extends Area3D

## Proximity interaction marker. Purely presentational: it proposes intents to the
## root controller and never mutates canonical state itself (GDI-01).

signal focus_changed(interactable: Interactable3D, focused: bool)

const FOCUS_FONT := preload("res://assets/fonts/NanumGothic-Regular.ttf")

@export var interaction_id: String = ""
@export var display_name: String = ""
@export var prompt_text: String = ""
var enabled: bool = true
var _focused: bool = false
var _focus_weight: float = 0.0
var _confirm_weight: float = 0.0
var _settle_weight: float = 0.0
var _phase: float = 0.0
var _idle_spin: float = 0.0
var _marker_anchor: Node3D
var _marker_ring: MeshInstance3D
var _marker_label: Label3D
var _marker_material: StandardMaterial3D
var _director: Node
var _player: PlayerInvestigator3D


static func create(id: String, name_text: String, prompt: String, radius: float = 2.2) -> Interactable3D:
	var area := Interactable3D.new()
	area.interaction_id = id
	area.display_name = name_text
	area.prompt_text = prompt
	area.name = "Interact_%s" % id
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = radius
	shape.shape = sphere
	area.add_child(shape)
	area.collision_layer = 4
	area.collision_mask = 0
	area._build_focus_marker()
	return area


func _ready() -> void:
	# A stable per-ID offset avoids synchronized marker motion without runtime RNG.
	_phase = float(abs(interaction_id.hash()) % 628) * 0.01
	_director = get_tree().get_first_node_in_group("sl_presentation_director")
	_bind_player.call_deferred()


func _build_focus_marker() -> void:
	# HARD BOUNDARY: this is a text/shape affordance only. It can mirror focus and
	# availability, but cannot commit an action or mutate canonical state.
	_marker_anchor = Node3D.new()
	_marker_anchor.name = "FocusMarker"
	_marker_anchor.position = Vector3(0.0, 0.22, 0.0)
	add_child(_marker_anchor)

	_marker_ring = MeshInstance3D.new()
	_marker_ring.name = "FocusRing"
	var ring_mesh := TorusMesh.new()
	ring_mesh.inner_radius = 0.28
	ring_mesh.outer_radius = 0.36
	ring_mesh.rings = 12
	ring_mesh.ring_segments = 8
	_marker_material = SealedLighthouseWorldBuilder.emissive_material(
		SealedLighthouseWorldBuilder.PALETTE.signal_amber, 0.45, 0.58
	)
	ring_mesh.material = _marker_material
	_marker_ring.mesh = ring_mesh
	# A slight fixed tilt makes the slow idle Y-spin below readable (a flat
	# torus is rotationally symmetric — untilted it would spin invisibly).
	_marker_ring.rotation_degrees.x = 12.0
	_marker_anchor.add_child(_marker_ring)

	_marker_label = Label3D.new()
	_marker_label.name = "FocusLabel"
	_marker_label.text = "[E] %s" % display_name
	var focus_font := FontVariation.new()
	focus_font.base_font = FOCUS_FONT
	var focus_fallbacks: Array[Font] = [ThemeDB.fallback_font]
	focus_font.fallbacks = focus_fallbacks
	_marker_label.font = focus_font
	_marker_label.font_size = 30
	_marker_label.pixel_size = 0.0065
	_marker_label.modulate = SealedLighthouseWorldBuilder.PALETTE.paper_fog
	_marker_label.outline_modulate = SealedLighthouseWorldBuilder.PALETTE.storm_ink
	_marker_label.outline_size = 10
	_marker_label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	_marker_label.no_depth_test = true
	_marker_label.position = Vector3(0.0, 0.78, 0.0)
	_marker_label.visible = false
	_marker_anchor.add_child(_marker_label)


func _bind_player() -> void:
	var scene := get_tree().current_scene
	if scene == null:
		return
	_player = scene.find_child("PlayerInvestigator", true, false) as PlayerInvestigator3D
	if _player == null:
		return
	var callback := Callable(self, "_on_player_focus_changed")
	if not _player.focus_changed.is_connected(callback):
		_player.focus_changed.connect(callback)
	var confirm_callback := Callable(self, "_on_player_interact_requested")
	if not _player.interact_requested.is_connected(confirm_callback):
		_player.interact_requested.connect(confirm_callback)


func _on_player_interact_requested(fired_id: String) -> void:
	# Confirm flash: a short, decaying acknowledgement that the press landed.
	# Presentation only — the proposal outcome arrives separately via the ledger.
	if fired_id == interaction_id and enabled:
		_confirm_weight = 1.0


func play_commit_settle() -> void:
	# Verdict-ritual commit settle: the acting prop's marker takes one ~2%
	# dip-and-recover bounce (RitualVfx contract; the director calls this
	# guarded by has_method). Presentation only; skipped under reduced motion.
	_settle_weight = 1.0


func _on_player_focus_changed(current: Interactable3D) -> void:
	_set_focused(current == self)


func _set_focused(value: bool) -> void:
	if _focused == value:
		return
	_focused = value
	focus_changed.emit(self, value)


func _process(delta: float) -> void:
	if _marker_anchor == null:
		return
	_marker_anchor.visible = enabled
	if not enabled:
		_marker_label.visible = false
		return
	if _director == null:
		_director = get_tree().get_first_node_in_group("sl_presentation_director")
	var motion_reduced: bool = (
		_director != null and bool(_director.get("reduce_motion"))
	)
	# Asymmetric focus envelope: fast attack (~0.12 s) so the ring answers the
	# glance immediately; slower release (~0.3 s) so un-focus reads as a decay,
	# not a cut.
	var focus_rate := 8.5 if _focused else 3.4
	_focus_weight = move_toward(_focus_weight, 1.0 if _focused else 0.0, delta * focus_rate)
	# Confirm flash decays over ~0.3 s after the interact press is acknowledged.
	_confirm_weight = move_toward(_confirm_weight, 0.0, delta * 3.3)
	# Commit settle-bounce decays over ~0.36 s: sin(π·w) dips then recovers.
	_settle_weight = move_toward(_settle_weight, 0.0, delta * 2.8)
	var scale_value := lerpf(0.82, 1.16, _focus_weight)
	var emission := lerpf(0.42, 1.45, _focus_weight)
	var ring_alpha := lerpf(0.42, 0.9, _focus_weight)
	if motion_reduced:
		# Reduced motion: steady semantic states only. Focus = brighter, steady
		# ring; confirm = brief linear brightness step-down, no pulse, pop,
		# settle-bounce, or idle spin.
		_marker_anchor.position.y = 0.22
		_marker_anchor.rotation.y = 0.0
		_marker_ring.rotation.y = 0.0
		_settle_weight = 0.0
		emission += _confirm_weight * 0.8
	else:
		_phase += delta * lerpf(1.15, 2.1, _focus_weight)
		_marker_anchor.position.y = 0.22 + sin(_phase) * lerpf(0.018, 0.055, _focus_weight)
		_marker_anchor.rotation.y += delta * lerpf(0.28, 0.8, _focus_weight)
		# Idle precession: the tilted ring turns once every 4 s — a quiet "this
		# is standing by" read that costs one rotation write per frame.
		_idle_spin = fmod(_idle_spin + delta * (TAU / 4.0), TAU)
		_marker_ring.rotation.y = _idle_spin
		# Focused breathe: emissive pulse + ≤3% scale swell on the same slow sine.
		var breathe := sin(_phase * 1.7)
		scale_value += breathe * 0.03 * _focus_weight
		emission += maxf(0.0, breathe) * 0.5 * _focus_weight
		# Confirm flash: bright spike with a small outward pop that decays fast.
		emission += _confirm_weight * 1.6
		scale_value += _confirm_weight * 0.09
		# Commit settle: ~2% dip that eases back to rest (verdict ritual beat).
		scale_value -= sin(_settle_weight * PI) * 0.02
	_marker_anchor.scale = Vector3.ONE * scale_value
	_marker_label.visible = _focused
	_marker_material.emission_energy_multiplier = emission
	_marker_material.albedo_color = Color(
		SealedLighthouseWorldBuilder.PALETTE.signal_amber,
		minf(ring_alpha + _confirm_weight * 0.1, 1.0)
	)
