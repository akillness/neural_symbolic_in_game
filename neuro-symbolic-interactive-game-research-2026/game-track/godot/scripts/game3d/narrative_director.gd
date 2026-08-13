class_name NarrativeDirector
extends Node

## Presentation director for the Sealed Lighthouse 3D slice.
## Drives the GDD B-011 tension curve (0.35 → 0.72 → 0.50), the SL-PRESENT-001
## beats P-B01..P-B06, weather intensity, and cinematic camera moves.
## Reads committed snapshots only; never proposes or mutates canonical state.

signal beat_played(beat_id: String)
signal cinematic_state_changed(active: bool)

const TENSION_CURVE := [0.35, 0.48, 0.72, 0.50]  # arrival, lens found, sealed refusal apex, authorized resolve
const BEAT_VFX_KEYS := [
	"arrival_mist", "lens_glints", "mount_sparks", "refusal_motes", "tide_motes"
]
const BEAT_SPEC := {
	"P-B01": {
		"duration_s": 4.6, "primary": "camera_handoff",
		"support": "arrival_mist", "reduced": "instant_handoff",
	},
	"P-B02": {
		"duration_s": 0.75, "primary": "lens_glint",
		"support": "ledger_commit", "reduced": "ledger_commit",
	},
	"P-B03": {
		"duration_s": 0.62, "primary": "mount_light",
		"support": "mount_sparks", "reduced": "steady_mount_light",
	},
	"P-B04": {
		"duration_s": 0.48, "primary": "local_refusal_text",
		"support": "refusal_motes", "reduced": "local_refusal_text",
	},
	"P-B05": {
		"duration_s": 1.25, "primary": "tide_mark_light",
		"support": "tide_motes", "reduced": "steady_tide_light",
	},
	"P-B06": {
		"duration_s": 5.0, "primary": "tide_to_tower_camera",
		"support": "tide_motes", "reduced": "static_end_card",
	},
}

var reduce_motion: bool:
	get:
		return _reduce_motion
	set(value):
		if _reduce_motion == value:
			return
		_reduce_motion = value
		_apply_motion_policy()

var _reduce_motion: bool = false
var _environment: Environment
var _rain: CPUParticles3D
var _sea_material: ShaderMaterial
var _lighthouse_light: OmniLight3D
var _buoy_light: OmniLight3D
var _cinematic_camera: Camera3D
var _player: PlayerInvestigator3D
var _tension: float = TENSION_CURVE[0]
var _tension_target: float = TENSION_CURVE[0]
var _time: float = 0.0
var _last_stage: int = 0
var _beat_vfx: Dictionary = {}
var _active_tweens: Dictionary = {}
var _cinematic_finish: Callable
var _cinematic_keep_letterbox: bool = false


func setup(handles: Dictionary, player: PlayerInvestigator3D) -> void:
	# HARD BOUNDARY: all handles are presentation nodes built from committed-state
	# projections. This director never calls the state machine or authorizes input.
	add_to_group("sl_presentation_director")
	_environment = (handles["environment"] as WorldEnvironment).environment
	_rain = handles["rain"]
	_lighthouse_light = handles["lighthouse_light"]
	_buoy_light = handles["buoy_light"]
	_player = player
	var world: Node3D = handles["world"]
	var sea: MeshInstance3D = world.get_meta("sea")
	_sea_material = sea.get_meta("sea_material")
	_cinematic_camera = Camera3D.new()
	_cinematic_camera.name = "CinematicCamera"
	_cinematic_camera.fov = 55.0
	add_child(_cinematic_camera)
	for key in BEAT_VFX_KEYS:
		var particles := handles.get(key) as CPUParticles3D
		if particles != null:
			_beat_vfx[key] = particles
	assert(BEAT_SPEC.size() == 6 and _beat_vfx.size() == BEAT_VFX_KEYS.size())
	for spec in BEAT_SPEC.values():
		assert(float(spec["duration_s"]) > 0.0 and not String(spec["reduced"]).is_empty())
	_apply_motion_policy()


func _process(delta: float) -> void:
	_time += delta
	_tension = lerpf(_tension, _tension_target, minf(delta * 0.6, 1.0))
	if _reduce_motion:
		if _environment != null:
			_environment.fog_density = 0.012 + _tension * 0.004
		if _rain != null:
			_rain.emitting = false
		if _sea_material != null:
			_sea_material.set_shader_parameter("agitation", 0.18)
		if _buoy_light != null:
			_buoy_light.light_energy = 0.58
		return
	if _environment != null:
		_environment.fog_density = 0.010 + _tension * 0.014
	if _rain != null:
		_rain.emitting = true
		_rain.speed_scale = 0.75 + _tension * 0.9
	if _sea_material != null:
		_sea_material.set_shader_parameter("agitation", 0.7 + _tension * 0.9)
	if _buoy_light != null:
		_buoy_light.light_energy = 0.35 + absf(sin(_time * 1.4)) * 0.5


func set_tension_stage(stage_index: int) -> void:
	var clamped_stage := clampi(stage_index, 0, TENSION_CURVE.size() - 1)
	_tension_target = TENSION_CURVE[clamped_stage]
	if clamped_stage == 1 and _last_stage < 1:
		# P-B02 Lens recovery: one bright core supported by a short glint burst.
		beat_played.emit("P-B02")
		_emit_vfx("lens_glints")
	_last_stage = maxi(_last_stage, clamped_stage)


func play_intro(on_finished: Callable) -> void:
	# P-B01 Arrival: hold on the dark tower beyond the wet quay, then hand the
	# camera to the player. No camera shake by specification.
	beat_played.emit("P-B01")
	_emit_vfx("arrival_mist")
	if _reduce_motion:
		_cinematic_camera.current = false
		_player.camera.current = true
		on_finished.call()
		return
	cinematic_state_changed.emit(true)
	_player.input_locked = true
	var lighthouse_focus := Vector3(6.0, 12.0, 62.0)
	_cinematic_camera.current = true
	_cinematic_camera.global_position = Vector3(2.0, 4.5, 30.0)
	_cinematic_camera.look_at(lighthouse_focus)
	_cinematic_finish = on_finished
	_cinematic_keep_letterbox = false
	var tween := _new_tween("intro")
	tween.tween_interval(1.4)
	tween.tween_property(_cinematic_camera, "global_position", Vector3(0.0, 3.2, 10.0), 3.2) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.parallel().tween_method(
		func(weight: float) -> void:
			var target := lighthouse_focus.lerp(_player.global_position + Vector3(0.0, 1.5, 0.0), weight)
			_cinematic_camera.look_at(target),
		0.0, 1.0, 3.2
	)
	tween.tween_callback(
		func() -> void: _finish_active_cinematic()
	)


func play_commit_glow(target: Node3D, light_name: String, energy: float) -> void:
	# P-B03/P-B05: core light + subordinate pooled burst, authorized commits only.
	var is_tide_hint := target.name == "TideMarks"
	beat_played.emit("P-B05" if is_tide_hint else "P-B03")
	_emit_vfx("tide_motes" if is_tide_hint else "mount_sparks")
	var light := target.get_node_or_null(light_name) as OmniLight3D
	if light == null:
		return
	if _reduce_motion:
		light.light_energy = energy
		return
	var tween := _new_tween("commit_%s" % target.get_instance_id())
	tween.tween_property(light, "light_energy", energy * 1.18, 0.18) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(light, "light_energy", energy, 0.34) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func play_refusal_pulse() -> void:
	# P-B04: local acknowledgement, no alarm; environment holds, no state change.
	beat_played.emit("P-B04")
	if _player != null:
		_emit_vfx("refusal_motes", _player.global_position + Vector3(0.0, 1.15, 0.0))
	if _buoy_light == null:
		return
	if _reduce_motion:
		_buoy_light.light_energy = 0.72
		return
	var tween := _new_tween("refusal")
	tween.tween_property(_buoy_light, "light_energy", 1.4, 0.08)
	tween.tween_property(_buoy_light, "light_energy", 0.5, 0.35)


func play_ending(on_finished: Callable) -> void:
	# Closing affordance: the tower stays sealed; the tide marks point onward.
	beat_played.emit("P-B06")
	_emit_vfx("tide_motes")
	cinematic_state_changed.emit(true)
	_player.input_locked = true
	if _reduce_motion:
		on_finished.call()
		return
	_cinematic_camera.current = true
	_cinematic_camera.global_position = _player.global_position + Vector3(-2.0, 2.5, -3.0)
	_cinematic_camera.look_at(Vector3(-8.5, 0.5, 15.5))
	_cinematic_finish = on_finished
	_cinematic_keep_letterbox = true
	var tween := _new_tween("ending")
	tween.tween_interval(1.2)
	tween.tween_property(_cinematic_camera, "global_position", Vector3(-4.0, 3.5, 8.0), 2.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.parallel().tween_method(
		func(weight: float) -> void:
			var target := Vector3(-8.5, 0.5, 15.5).lerp(Vector3(6.0, 10.0, 62.0), weight)
			_cinematic_camera.look_at(target),
		0.0, 1.0, 2.8
	)
	tween.tween_interval(1.0)
	tween.tween_callback(func() -> void: _finish_active_cinematic())


func _emit_vfx(key: String, position_override: Variant = null) -> void:
	if _reduce_motion:
		return
	var particles := _beat_vfx.get(key) as CPUParticles3D
	if particles == null:
		return
	if position_override is Vector3:
		particles.global_position = position_override
	particles.emitting = false
	particles.restart()


func _new_tween(key: String) -> Tween:
	var previous := _active_tweens.get(key) as Tween
	if previous != null and previous.is_valid():
		previous.kill()
	var tween := create_tween()
	_active_tweens[key] = tween
	return tween


func _apply_motion_policy() -> void:
	# Reduced motion keeps steady semantic light/color states while removing camera
	# travel, rain, wave motion, pulsing, and particle bursts.
	if _rain != null:
		_rain.emitting = not _reduce_motion
	if _reduce_motion:
		_stop_all_vfx()
		for key in ["intro", "ending"]:
			var tween := _active_tweens.get(key) as Tween
			if tween != null and tween.is_valid():
				tween.kill()
		if _cinematic_finish.is_valid():
			_finish_active_cinematic()


func _finish_active_cinematic() -> void:
	if _cinematic_camera != null:
		_cinematic_camera.current = false
	if _player != null:
		_player.camera.current = true
		if not _cinematic_keep_letterbox:
			_player.input_locked = false
	if not _cinematic_keep_letterbox:
		cinematic_state_changed.emit(false)
	var finished := _cinematic_finish
	_cinematic_finish = Callable()
	_cinematic_keep_letterbox = false
	if finished.is_valid():
		finished.call()


func _stop_all_vfx() -> void:
	for particles in _beat_vfx.values():
		(particles as CPUParticles3D).emitting = false


func _exit_tree() -> void:
	_stop_all_vfx()
	for tween_value in _active_tweens.values():
		var tween := tween_value as Tween
		if tween != null and tween.is_valid():
			tween.kill()
