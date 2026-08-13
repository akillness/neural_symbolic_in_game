class_name NarrativeDirector
extends Node

## Presentation director for the Sealed Lighthouse 3D slice.
## Drives the GDD B-011 tension curve (0.35 → 0.72 → 0.50), the SL-PRESENT-001
## beats P-B01..P-B05, weather intensity, and cinematic camera moves.
## Reads committed snapshots only; never proposes or mutates canonical state.

signal beat_played(beat_id: String)
signal cinematic_state_changed(active: bool)

const TENSION_CURVE := [0.35, 0.48, 0.72, 0.50]  # arrival, lens found, sealed refusal apex, authorized resolve

var reduce_motion: bool = false
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


func setup(handles: Dictionary, player: PlayerInvestigator3D) -> void:
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


func _process(delta: float) -> void:
	_time += delta
	_tension = lerpf(_tension, _tension_target, minf(delta * 0.6, 1.0))
	if _environment != null:
		_environment.fog_density = 0.010 + _tension * 0.014
	if _rain != null:
		_rain.speed_scale = 0.75 + _tension * 0.9
	if _sea_material != null:
		_sea_material.set_shader_parameter("agitation", 0.7 + _tension * 0.9)
	if _buoy_light != null:
		_buoy_light.light_energy = 0.35 + absf(sin(_time * 1.4)) * 0.5


func set_tension_stage(stage_index: int) -> void:
	_tension_target = TENSION_CURVE[clampi(stage_index, 0, TENSION_CURVE.size() - 1)]


func play_intro(on_finished: Callable) -> void:
	# P-B01 Arrival: hold on the dark tower beyond the wet quay, then hand the
	# camera to the player. No camera shake by specification.
	beat_played.emit("P-B01")
	if reduce_motion:
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
	var tween := create_tween()
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
		func() -> void:
			_cinematic_camera.current = false
			_player.camera.current = true
			_player.input_locked = false
			cinematic_state_changed.emit(false)
			on_finished.call()
	)


func play_commit_glow(target: Node3D, light_name: String, energy: float) -> void:
	# P-B05 style signal glow: 250 ms rise on an authorized commit only.
	var light := target.get_node_or_null(light_name) as OmniLight3D
	if light == null:
		return
	if reduce_motion:
		light.light_energy = energy
		return
	var tween := create_tween()
	tween.tween_property(light, "light_energy", energy, 0.25)


func play_refusal_pulse() -> void:
	# P-B04: local acknowledgement, no alarm; environment holds, no state change.
	if _buoy_light == null or reduce_motion:
		return
	var tween := create_tween()
	tween.tween_property(_buoy_light, "light_energy", 1.4, 0.08)
	tween.tween_property(_buoy_light, "light_energy", 0.5, 0.35)


func play_ending(on_finished: Callable) -> void:
	# Closing affordance: the tower stays sealed; the tide marks point onward.
	beat_played.emit("P-B06")
	cinematic_state_changed.emit(true)
	_player.input_locked = true
	if reduce_motion:
		on_finished.call()
		return
	_cinematic_camera.current = true
	_cinematic_camera.global_position = _player.global_position + Vector3(-2.0, 2.5, -3.0)
	_cinematic_camera.look_at(Vector3(-8.5, 0.5, 15.5))
	var tween := create_tween()
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
	tween.tween_callback(on_finished)
