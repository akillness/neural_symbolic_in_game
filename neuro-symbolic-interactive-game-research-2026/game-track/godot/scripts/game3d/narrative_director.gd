class_name NarrativeDirector
extends Node

## Presentation director for the Sealed Lighthouse 3D slice.
## Drives the GDD B-011 tension curve (0.35 → 0.72 → 0.50), the SL-PRESENT-001
## beats P-B01..P-B06, the staged weather arc (fog grade, sky darkening,
## wind-driven rain, sea agitation, offshore lightning), harbor-life
## micro-motion, cinematic camera moves, and the verdict ritual — the paper's
## validate→repair→commit transaction staged diegetically at the acting prop
## as ritual sub-beats of P-B03/P-B04/P-B05:
##   inspect  (~0.25 s) amber ring sweep while the proposal is being weighed;
##   verdict  commit → warm brass flash + rising motes + light bloom envelope
##            (P-B03/P-B05 face), refusal → cold slate dip + one horizontal
##            seal-line shutter stroke (~0.3 s, P-B04 face);
##   settle   the ring releases; the lasting record lives in the ledger.
## Reads committed snapshots only; never proposes or mutates canonical state.
##
## D-030 hard boundary: the offshore lighthouse stays DARK and SEALED. Lightning
## flashes come from the storm sky (moon/ambient/horizon energy only) and the
## ending beam belongs to the HARBOR-SIDE signal lamp sweeping toward the tide
## channel — no effect here ever brightens the SealedBeacon.

signal beat_played(beat_id: String)
signal cinematic_state_changed(active: bool)
## Distant offshore lightning fired (tension >= LIGHTNING_MIN_TENSION only,
## never under reduce_motion). The audio agent may connect a delayed low rumble;
## this director plays no audio itself.
signal lightning_struck(intensity: float)

const TENSION_CURVE := [0.35, 0.48, 0.72, 0.50]  # arrival, lens found, sealed refusal apex, authorized resolve
const LIGHTNING_MIN_TENSION := 0.6
const LIGHTNING_INTERVAL_MIN_S := 8.0
const LIGHTNING_INTERVAL_MAX_S := 18.0
# Objective-beacon breathing (UI marker, never a lighthouse beam — D-030):
# shader pulse eases 0.55↔0.8 over one 2.5 s sine; reduced motion holds the
# static midpoint.
const BEACON_PULSE_PERIOD_S := 2.5
const BEACON_PULSE_MIN := 0.55
const BEACON_PULSE_MAX := 0.8
# Signal-lens hero idle: one full quiet turn every 6 s, and a brass rim glint
# sweep every ~4 s while the optic is still in the store (both motion-gated).
const LENS_IDLE_TURN_PERIOD_S := 6.0
const LENS_GLINT_INTERVAL_S := 4.0
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
		"duration_s": 7.6, "primary": "tide_to_tower_camera",
		"support": "tide_motes", "reduced": "static_end_card",
	},
}
# Verdict-ritual sub-beat timings (P-B03/P-B04/P-B05 faces). Reduced motion
# replaces the whole sequence with one steady verdict-colored ring state.
const RITUAL_SPEC := {
	"inspect_s": 0.22,
	"verdict_s": 0.30,
	"settle_s": 0.24,
}

# P-B06 geometry: every aim point is harbor-side water. From the mount at
# (7, 3.6, 13.5) the sweep runs W → NW (tide marks → channel buoy) and never
# crosses the tower bearing (≈N at (6, y, 62)) — the lighthouse stays dark.
const BEAM_AIM_TIDE := Vector3(-8.5, 1.2, 15.5)
const BEAM_AIM_CHANNEL := Vector3(-14.0, 1.6, 34.0)
const TOWER_FOCUS := Vector3(6.0, 10.0, 62.0)
const CHANNEL_LOOK := Vector3(-11.0, 1.2, 25.0)

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
var _sky_material: ProceduralSkyMaterial
var _moon: DirectionalLight3D
var _rain: CPUParticles3D
var _sea_material: ShaderMaterial
var _lighthouse_light: OmniLight3D
var _buoy_light: OmniLight3D
var _buoy_root: Node3D
var _buoy_rest: Vector3
var _store_lamp: OmniLight3D
var _mira_lantern: OmniLight3D
var _mist_sheets: Array = []
var _mist_rests: PackedVector3Array = PackedVector3Array()
var _beam_pivot: Node3D
var _beam_mesh: MeshInstance3D
var _beam_material: StandardMaterial3D
var _commit_halo: MeshInstance3D
var _halo_material: StandardMaterial3D
var _mount_light: OmniLight3D
var _inspection_ring: MeshInstance3D
var _ring_material: StandardMaterial3D
var _seal_line: MeshInstance3D
var _seal_material: StandardMaterial3D
var _audio_feedback: Node
var _ritual_light_rest: Dictionary = {}
var _cinematic_camera: Camera3D
var _player: PlayerInvestigator3D
var _tension: float = TENSION_CURVE[0]
var _tension_target: float = TENSION_CURVE[0]
var _time: float = 0.0
var _last_stage: int = 0
var _weather_stage: int = 0
var _stage_weather: Array = []
var _fog_color: Color
var _sky_top: Color
var _sky_horizon: Color
var _ambient_level: float = 0.7
var _moon_level: float = 0.35
var _moon_color: Color
var _wind: float = 0.25
var _agitation: float = 0.85
var _rain_speed: float = 1.05
var _fog_scale: float = 1.0
var _wave_phase: float = 0.0
var _lightning_boost: float = 0.0
var _lightning_timer: float = 0.0
var _refusal_chill: float = 0.0
var _rng := RandomNumberGenerator.new()
var _beat_vfx: Dictionary = {}
var _active_tweens: Dictionary = {}
var _cinematic_finish: Callable
var _cinematic_keep_letterbox: bool = false
var _beacon_material: ShaderMaterial
var _lens_prop: Node3D
var _lens_glint_pivot: Node3D
var _lens_glint_material: StandardMaterial3D
var _lens_glint_timer: float = 0.0


func setup(handles: Dictionary, player: PlayerInvestigator3D) -> void:
	# HARD BOUNDARY: all handles are presentation nodes built from committed-state
	# projections. This director never calls the state machine or authorizes input.
	add_to_group("sl_presentation_director")
	var world_environment := handles["environment"] as WorldEnvironment
	_environment = world_environment.environment
	_sky_material = world_environment.get_meta("sky_material", null) as ProceduralSkyMaterial
	_moon = world_environment.get_meta("storm_moon", null) as DirectionalLight3D
	_rain = handles["rain"]
	_lighthouse_light = handles["lighthouse_light"]
	_buoy_light = handles["buoy_light"]
	_player = player
	var world: Node3D = handles["world"]
	var sea: MeshInstance3D = world.get_meta("sea")
	_sea_material = sea.get_meta("sea_material")
	_buoy_root = world.get_meta("buoy_root", null) as Node3D
	if _buoy_root != null:
		_buoy_rest = _buoy_root.position
	_store_lamp = world.get_meta("store_lamp", null) as OmniLight3D
	_mira_lantern = world.get_meta("mira_lantern", null) as OmniLight3D
	_mist_sheets = world.get_meta("waterline_mist_sheets", [])
	# Per-frame drift reads from this packed cache, not get_meta — the metas
	# stay for the reduced-motion rest snap.
	_mist_rests.resize(_mist_sheets.size())
	for index in _mist_sheets.size():
		var sheet := _mist_sheets[index] as MeshInstance3D
		if sheet != null:
			_mist_rests[index] = sheet.get_meta("rest_position", sheet.position)
	var objective_beacon := handles.get("objective_beacon") as Node3D
	if objective_beacon != null:
		_beacon_material = objective_beacon.get_meta(&"beacon_material", null) as ShaderMaterial
	_lens_prop = handles.get("lens_prop") as Node3D
	if _lens_prop != null:
		_lens_glint_pivot = _lens_prop.get_meta(&"glint_pivot", null) as Node3D
		_lens_glint_material = _lens_prop.get_meta(&"glint_material", null) as StandardMaterial3D
	_beam_pivot = world.get_meta("signal_beam_pivot", null) as Node3D
	if _beam_pivot != null:
		_beam_mesh = _beam_pivot.get_meta("beam_mesh", null) as MeshInstance3D
		_beam_material = _beam_pivot.get_meta("beam_material", null) as StandardMaterial3D
	_commit_halo = world.get_meta("commit_halo", null) as MeshInstance3D
	if _commit_halo != null:
		_halo_material = _commit_halo.get_meta("halo_material", null) as StandardMaterial3D
	_inspection_ring = world.get_meta("inspection_ring", null) as MeshInstance3D
	if _inspection_ring != null:
		_ring_material = _inspection_ring.get_meta("ring_material", null) as StandardMaterial3D
	_seal_line = world.get_meta("seal_line", null) as MeshInstance3D
	if _seal_line != null:
		_seal_material = _seal_line.get_meta("seal_material", null) as StandardMaterial3D
	# Ritual audio rides the pooled, gesture/mute-gated cue voices owned by the
	# audio node; the director requests cues, it never owns playback policy.
	# Resolved lazily too (_request_cue) — setup may run before tree entry.
	if is_inside_tree():
		_audio_feedback = get_tree().get_first_node_in_group("sl_audio_feedback")
	var lamp_mount := handles.get("lamp_mount") as Node3D
	if lamp_mount != null:
		_mount_light = lamp_mount.get_node_or_null("MountLight") as OmniLight3D
	_cinematic_camera = Camera3D.new()
	_cinematic_camera.name = "CinematicCamera"
	_cinematic_camera.fov = 55.0
	add_child(_cinematic_camera)
	for key in BEAT_VFX_KEYS:
		var particles := handles.get(key) as CPUParticles3D
		if particles != null:
			particles.set_meta("rest_position", particles.position)
			_beat_vfx[key] = particles
	assert(BEAT_SPEC.size() == 6 and _beat_vfx.size() == BEAT_VFX_KEYS.size())
	for spec in BEAT_SPEC.values():
		assert(float(spec["duration_s"]) > 0.0 and not String(spec["reduced"]).is_empty())
	# Fixed seed: lightning cadence stays deterministic per run, like the pooled
	# beat VFX seeds.
	_rng.seed = 6606
	_lightning_timer = _rng.randf_range(LIGHTNING_INTERVAL_MIN_S, LIGHTNING_INTERVAL_MAX_S)
	_stage_weather = _build_stage_weather()
	_snap_weather_to_stage(0)
	_apply_motion_policy()


func _build_stage_weather() -> Array:
	# One grade per tension stage. Stages 1 (0.48) and 3 (0.50) sit at similar
	# tension but read differently on purpose: 1 is the storm tightening, 3 is
	# the amber-tinted resolve after the authorized hint (harbor signal restored;
	# the tower itself stays dark, D-030).
	var palette: Dictionary = SealedLighthouseWorldBuilder.PALETTE
	var storm_ink: Color = palette.storm_ink
	var wet_slate: Color = palette.wet_slate
	var paper_fog: Color = palette.paper_fog
	var signal_amber: Color = palette.signal_amber
	return [
		{  # Stage 0 — arrival: heavy but breathable harbor rain.
			"fog": wet_slate,
			"sky_top": storm_ink.darkened(0.40),
			"sky_horizon": wet_slate.darkened(0.20),
			"ambient": 0.70, "moon": 0.35, "moon_color": paper_fog,
			"wind": 0.25, "agitation": 0.85, "rain_speed": 1.05, "fog_scale": 1.0,
		},
		{  # Stage 1 — lens recovered: the storm tightens, wind picks up.
			"fog": wet_slate.darkened(0.10),
			"sky_top": storm_ink.darkened(0.50),
			"sky_horizon": wet_slate.darkened(0.30),
			"ambient": 0.62, "moon": 0.30, "moon_color": paper_fog,
			"wind": 0.45, "agitation": 1.05, "rain_speed": 1.25, "fog_scale": 1.12,
		},
		{  # Stage 2 — sealed refusal apex (0.72): darkest sky, thickest fog,
			# hardest wind; offshore lightning becomes eligible.
			"fog": storm_ink.lightened(0.06),
			"sky_top": storm_ink.darkened(0.62),
			"sky_horizon": storm_ink.lightened(0.10),
			"ambient": 0.50, "moon": 0.22, "moon_color": paper_fog.darkened(0.10),
			"wind": 0.85, "agitation": 1.35, "rain_speed": 1.65, "fog_scale": 1.30,
		},
		{  # Stage 3 — authorized resolve (0.50): the fog thins and warms toward
			# amber. The warmth belongs to the harbor signal, never the tower.
			"fog": wet_slate.lerp(signal_amber, 0.30),
			"sky_top": storm_ink.darkened(0.30),
			"sky_horizon": wet_slate.lerp(signal_amber, 0.34).darkened(0.06),
			"ambient": 0.80, "moon": 0.42, "moon_color": paper_fog.lerp(signal_amber, 0.32),
			"wind": 0.30, "agitation": 0.70, "rain_speed": 0.90, "fog_scale": 0.78,
		},
	]


func _snap_weather_to_stage(stage_index: int) -> void:
	var grade: Dictionary = _stage_weather[stage_index]
	_fog_color = grade["fog"]
	_sky_top = grade["sky_top"]
	_sky_horizon = grade["sky_horizon"]
	_ambient_level = grade["ambient"]
	_moon_level = grade["moon"]
	_moon_color = grade["moon_color"]
	_wind = grade["wind"]
	_agitation = grade["agitation"]
	_rain_speed = grade["rain_speed"]
	_fog_scale = grade["fog_scale"]


func _process(delta: float) -> void:
	_time += delta
	_tension = lerpf(_tension, _tension_target, minf(delta * 0.6, 1.0))
	_blend_weather(delta)
	if _reduce_motion:
		# Complete steady state: no camera travel, particles, pulsing, wave
		# motion, flicker, bob, drift, or lightning — semantic values hold.
		if _environment != null:
			_environment.fog_density = 0.012 + _tension * 0.004
		if _rain != null:
			_rain.emitting = false
		if _sea_material != null:
			_sea_material.set_shader_parameter(&"agitation", 0.18)
		if _buoy_light != null:
			_buoy_light.light_energy = 0.58
		return
	if _environment != null:
		_environment.fog_density = (0.010 + _tension * 0.014) * _fog_scale
	if _rain != null:
		_rain.emitting = true
		_rain.speed_scale = (0.75 + _tension * 0.9) * _rain_speed
		# Wind-driven rain angle: harder stages shear the fall line sideways.
		_rain.direction = Vector3(-0.15 - _wind * 0.55, -1.0, 0.05 + _wind * 0.18)
		_rain.gravity = Vector3(-_wind * 10.0, -22.0, 0.0)
	if _sea_material != null:
		_wave_phase += delta * (0.55 + _wind * 0.9 + _tension * 0.35)
		_sea_material.set_shader_parameter(&"agitation", _agitation * (0.85 + _tension * 0.35))
		_sea_material.set_shader_parameter(&"wave_phase", _wave_phase)
	if _buoy_light != null:
		_buoy_light.light_energy = 0.35 + absf(sin(_time * 1.4)) * 0.5
	if _beacon_material != null:
		# Objective-beacon breathing: 0.55↔0.8 alpha over one 2.5 s sine.
		var breath := 0.5 + 0.5 * sin(_time * (TAU / BEACON_PULSE_PERIOD_S))
		_beacon_material.set_shader_parameter(
			&"pulse", lerpf(BEACON_PULSE_MIN, BEACON_PULSE_MAX, breath)
		)
	if _lens_prop != null and _lens_prop.visible:
		# Hero-item idle: one quiet turn per 6 s while the optic waits in store,
		# plus a brass rim glint sweep every ~4 s.
		_lens_prop.rotation.y = fmod(_lens_prop.rotation.y + delta * (TAU / LENS_IDLE_TURN_PERIOD_S), TAU)
		_lens_glint_timer += delta
		if _lens_glint_timer >= LENS_GLINT_INTERVAL_S:
			_lens_glint_timer = fmod(_lens_glint_timer, LENS_GLINT_INTERVAL_S)
			_play_lens_glint()
	_update_harbor_life()
	_update_lightning(delta)


func _blend_weather(delta: float) -> void:
	# Tension-staged color grading: fog color, sky darkening, ambient level, and
	# moonlight ease toward the committed stage grade. Under reduce_motion this
	# is a one-time state transition, not continuous motion.
	if _stage_weather.is_empty() or _environment == null:
		return
	var grade: Dictionary = _stage_weather[_weather_stage]
	var blend := minf(delta * 0.8, 1.0)
	_fog_color = _fog_color.lerp(grade["fog"], blend)
	_sky_top = _sky_top.lerp(grade["sky_top"], blend)
	_sky_horizon = _sky_horizon.lerp(grade["sky_horizon"], blend)
	_ambient_level = lerpf(_ambient_level, grade["ambient"], blend)
	_moon_level = lerpf(_moon_level, grade["moon"], blend)
	_moon_color = _moon_color.lerp(grade["moon_color"], blend)
	_wind = lerpf(_wind, grade["wind"], blend)
	_agitation = lerpf(_agitation, grade["agitation"], blend)
	_rain_speed = lerpf(_rain_speed, grade["rain_speed"], blend)
	_fog_scale = lerpf(_fog_scale, grade["fog_scale"], blend)
	var cold_fog: Color = SealedLighthouseWorldBuilder.PALETTE.wet_slate.darkened(0.25)
	_environment.fog_light_color = _fog_color.lerp(cold_fog, _refusal_chill * 0.55)
	_environment.ambient_light_energy = clampf(
		_ambient_level * (1.0 + _lightning_boost * 0.9) - _refusal_chill * 0.2, 0.05, 1.6
	)
	if _sky_material != null:
		var flash_horizon: Color = SealedLighthouseWorldBuilder.PALETTE.paper_fog
		_sky_material.sky_top_color = _sky_top.lerp(flash_horizon, _lightning_boost * 0.20)
		# Lightning reads strongest at the seaward horizon — an offshore storm
		# flash, never a glow at the sealed tower lantern.
		_sky_material.sky_horizon_color = _sky_horizon.lerp(flash_horizon, _lightning_boost * 0.45)
		_sky_material.ground_horizon_color = _sky_horizon.darkened(0.35)
	if _moon != null:
		_moon.light_energy = _moon_level * (1.0 + _lightning_boost * 2.4)
		_moon.light_color = _moon_color


func _update_harbor_life() -> void:
	# Harbor-life micro-motion: cheap sine transforms on existing nodes; no new
	# physics, particles, or lights. All of it rests under reduce_motion.
	var sway := 0.6 + _tension * 0.7
	if _buoy_root != null:
		_buoy_root.position = _buoy_rest + Vector3(0.0, sin(_time * 1.1) * 0.06 * sway, 0.0)
		_buoy_root.rotation.z = sin(_time * 0.9) * 0.045 * sway
		_buoy_root.rotation.x = cos(_time * 0.7) * 0.03 * sway
	if _store_lamp != null:
		_store_lamp.light_energy = 1.1 + sin(_time * 13.7) * 0.05 + sin(_time * 7.3) * 0.04
	if _mira_lantern != null:
		_mira_lantern.light_energy = 0.5 + sin(_time * 11.3 + 1.7) * 0.04
	for index in _mist_sheets.size():
		var sheet := _mist_sheets[index] as MeshInstance3D
		if sheet == null:
			continue
		sheet.position = _mist_rests[index] + Vector3(
			sin(_time * 0.11 + index * 2.1) * 1.6,
			sin(_time * 0.23 + index) * 0.05,
			cos(_time * 0.13 + index * 1.3) * 1.2
		)


func _play_lens_glint() -> void:
	# Brass rim glint sweep (~0.7 s): the pooled spark brightens, arcs a third
	# of the way around the rim, and dies out. Rides the optic's own transform,
	# so it inherits the idle turn and disappears with the pickup. Motion-gated
	# by the caller; presentation only.
	if _lens_glint_pivot == null or _lens_glint_material == null:
		return
	_lens_glint_pivot.rotation.y = 0.0
	var tween := _new_tween("lens_glint")
	tween.tween_property(_lens_glint_material, "albedo_color:a", 0.85, 0.16) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(_lens_glint_pivot, "rotation:y", TAU / 3.0, 0.7) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.parallel().tween_property(_lens_glint_material, "albedo_color:a", 0.0, 0.4) \
		.set_delay(0.3).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)


func _update_lightning(delta: float) -> void:
	# Distant offshore lightning: sky/ambient/moon energy spike with a two-step
	# decay. Eligible only above LIGHTNING_MIN_TENSION and never under
	# reduce_motion. D-030: the SealedBeacon is never touched.
	if _tension < LIGHTNING_MIN_TENSION or _environment == null:
		return
	_lightning_timer -= delta
	if _lightning_timer > 0.0:
		return
	_lightning_timer = _rng.randf_range(LIGHTNING_INTERVAL_MIN_S, LIGHTNING_INTERVAL_MAX_S)
	var intensity := _rng.randf_range(0.7, 1.0)
	lightning_struck.emit(intensity)
	var tween := _new_tween("lightning")
	tween.tween_property(self, "_lightning_boost", intensity, 0.06)
	tween.tween_property(self, "_lightning_boost", intensity * 0.35, 0.10)
	tween.tween_property(self, "_lightning_boost", intensity * 0.55, 0.08)
	tween.tween_property(self, "_lightning_boost", 0.0, 0.45) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)


func set_tension_stage(stage_index: int) -> void:
	var clamped_stage := clampi(stage_index, 0, TENSION_CURVE.size() - 1)
	_tension_target = TENSION_CURVE[clamped_stage]
	_weather_stage = clamped_stage
	if clamped_stage == 1 and _last_stage < 1:
		# P-B02 Lens recovery: one bright core supported by a short glint burst.
		beat_played.emit("P-B02")
		_emit_vfx("lens_glints")
	_last_stage = maxi(_last_stage, clamped_stage)


func play_intro(on_finished: Callable) -> void:
	# P-B01 Arrival: hold on the dark tower beyond the wet quay, then pull back
	# with a slow FOV ease (55 → 62) into the player camera's field of view so
	# the handoff cuts seamlessly. No camera shake by specification.
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
	_cinematic_camera.fov = 55.0
	_cinematic_camera.global_position = Vector3(2.0, 4.5, 30.0)
	_cinematic_camera.look_at(lighthouse_focus)
	_cinematic_finish = on_finished
	_cinematic_keep_letterbox = false
	var tween := _new_tween("intro")
	tween.tween_interval(1.4)
	tween.tween_property(_cinematic_camera, "global_position", Vector3(0.0, 3.2, 10.0), 3.2) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.parallel().tween_property(_cinematic_camera, "fov", 62.0, 3.2) \
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
	# P-B03/P-B05: core light + subordinate pooled burst + one pooled radial halo
	# quad (scale/fade ≤0.6 s), authorized commits only.
	var is_tide_hint := target.name == "TideMarks"
	beat_played.emit("P-B05" if is_tide_hint else "P-B03")
	_emit_vfx("tide_motes" if is_tide_hint else "mount_sparks")
	var light := target.get_node_or_null(light_name) as OmniLight3D
	if light == null:
		return
	if _reduce_motion:
		light.light_energy = energy
		return
	if _commit_halo != null and _halo_material != null:
		_commit_halo.global_position = light.global_position
		_commit_halo.scale = Vector3.ONE * 0.4
		_halo_material.albedo_color.a = 0.55
		_commit_halo.visible = true
		var halo_tween := _new_tween("commit_halo")
		halo_tween.tween_property(_commit_halo, "scale", Vector3.ONE * 1.55, 0.42) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
		halo_tween.parallel().tween_property(_halo_material, "albedo_color:a", 0.0, 0.5)
		halo_tween.tween_callback(func() -> void: _commit_halo.visible = false)
	var tween := _new_tween("commit_%s" % target.get_instance_id())
	tween.tween_property(light, "light_energy", energy * 1.18, 0.18) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(light, "light_energy", energy, 0.40) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func play_refusal_pulse() -> void:
	# P-B04: local acknowledgement, no alarm; environment holds, no state change.
	# The punch-up is a brief cold dip — buoy color and ambient shift toward
	# wet_slate (≤0.6 s), then recover fully.
	beat_played.emit("P-B04")
	if _player != null:
		_emit_vfx("refusal_motes", _player.global_position + Vector3(0.0, 1.15, 0.0))
	if _buoy_light == null:
		return
	if _reduce_motion:
		_buoy_light.light_energy = 0.72
		return
	var coral: Color = SealedLighthouseWorldBuilder.PALETTE.warning_coral
	var cold: Color = coral.lerp(SealedLighthouseWorldBuilder.PALETTE.wet_slate, 0.65)
	var tween := _new_tween("refusal")
	tween.tween_property(_buoy_light, "light_energy", 1.25, 0.08)
	tween.parallel().tween_property(_buoy_light, "light_color", cold, 0.08)
	tween.parallel().tween_property(self, "_refusal_chill", 1.0, 0.10)
	tween.tween_property(_buoy_light, "light_energy", 0.5, 0.38)
	tween.parallel().tween_property(_buoy_light, "light_color", coral, 0.38)
	tween.parallel().tween_property(self, "_refusal_chill", 0.0, 0.40)


func play_verdict_ritual(target: Node3D, committed: bool) -> void:
	# The paper's validate→repair→commit transaction, staged diegetically at the
	# acting prop (ritual sub-beats of P-B03/P-B04/P-B05). Three phases:
	#   (i)  inspect — amber ring sweep (~0.22 s) while the proposal is weighed;
	#   (ii) verdict — commit: warm brass flash + rising motes + light bloom;
	#        refusal: cold slate dip + one horizontal seal-line stroke (~0.3 s);
	#   (iii) settle — the ring releases; the record lives in the ledger.
	# Additive layering over play_commit_glow/play_refusal_pulse — never a second
	# state authority: refusals leave every canonical value untouched.
	# Reduced motion: one steady verdict-colored ring state, no sweep/burst/travel.
	var anchor := _ritual_anchor(target)
	var palette: Dictionary = SealedLighthouseWorldBuilder.PALETTE
	var amber: Color = palette.signal_amber
	var brass: Color = palette.brass
	var cold: Color = (palette.warning_coral as Color).lerp(palette.wet_slate, 0.6)
	_request_cue("verdict_inspect")
	if _inspection_ring == null or _ring_material == null:
		# Pool absent (defensive): verdict audio + existing glow/pulse still land.
		_finish_verdict(target, committed, anchor)
		return
	_inspection_ring.global_position = anchor
	_inspection_ring.rotation = Vector3.ZERO
	# A re-trigger can interrupt a commit flash mid-tween; start from rest.
	_ring_material.emission_energy_multiplier = 1.0
	if _reduce_motion:
		# Steady semantic state only: verdict-colored ring, no motion, timed release.
		_ring_material.emission = brass if committed else cold
		_ring_material.albedo_color = Color(_ring_material.emission, 0.55)
		_inspection_ring.scale = Vector3.ONE
		_inspection_ring.visible = true
		_finish_verdict(target, committed, anchor)
		var hold := _new_tween("verdict_ring")
		hold.tween_interval(0.9)
		hold.tween_callback(func() -> void: _inspection_ring.visible = false)
		return
	_ring_material.emission = amber
	_ring_material.albedo_color = Color(amber, 0.0)
	_inspection_ring.scale = Vector3.ONE * 0.55
	_inspection_ring.visible = true
	var inspect_s: float = RITUAL_SPEC["inspect_s"]
	var tween := _new_tween("verdict_ring")
	# (i) inspect: the ring sweeps open and lifts slightly — evidence weighed.
	tween.tween_property(_ring_material, "albedo_color:a", 0.85, inspect_s * 0.45) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(_inspection_ring, "scale", Vector3.ONE * 1.05, inspect_s) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	tween.parallel().tween_property(
		_inspection_ring, "global_position:y", anchor.y + 0.14, inspect_s
	).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	# (ii) verdict.
	tween.tween_callback(func() -> void: _finish_verdict(target, committed, anchor))
	if committed:
		# Warm brass flash + a confident outward pop. Albedo follows emission —
		# the ring is unshaded, so its visible color = albedo tint + emission.
		tween.tween_property(_ring_material, "emission", brass.lightened(0.25), 0.06)
		tween.parallel().tween_property(
			_ring_material, "albedo_color", Color(brass.lightened(0.2), 0.9), 0.06
		)
		tween.parallel().tween_property(_ring_material, "emission_energy_multiplier", 2.2, 0.06)
		tween.parallel().tween_property(_inspection_ring, "scale", Vector3.ONE * 1.28, 0.10) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		tween.tween_property(_ring_material, "emission_energy_multiplier", 1.0, 0.20) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	else:
		# Cold slate dip: the ring chills and sinks a touch — proposal held.
		tween.tween_property(_ring_material, "emission", cold, 0.10)
		tween.parallel().tween_property(_ring_material, "albedo_color", Color(cold, 0.8), 0.10)
		tween.parallel().tween_property(_inspection_ring, "scale", Vector3.ONE * 0.9, 0.16) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
		tween.parallel().tween_property(
			_inspection_ring, "global_position:y", anchor.y - 0.05, 0.16
		).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN_OUT)
	# (iii) settle: release the ring; the lasting record is the ledger line.
	var settle_s: float = RITUAL_SPEC["settle_s"]
	tween.tween_property(_ring_material, "albedo_color:a", 0.0, settle_s) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	tween.tween_callback(func() -> void: _inspection_ring.visible = false)


func play_repair_hint(target: Node3D) -> void:
	# Repair visualization: a short double amber blink on the acting prop's own
	# lamp — "the proposal is being revised toward the next affordance". Light
	# energy envelope only (no particles, meshes, or new lights). Reduced motion
	# skips the pulse; the refusal text already names the next affordance.
	if _reduce_motion:
		return
	var light := _find_target_light(target)
	if light == null:
		return
	var key := "repair_%s" % light.get_instance_id()
	var rest: float = _ritual_light_rest.get(key, light.light_energy)
	_ritual_light_rest[key] = rest
	var amber: Color = SealedLighthouseWorldBuilder.PALETTE.signal_amber
	var peak: float = maxf(rest * 1.6, 0.55)
	var tween := _new_tween(key)
	for _blink in range(2):
		tween.tween_property(light, "light_energy", peak, 0.06) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.parallel().tween_property(light, "light_color", amber, 0.06)
		tween.tween_property(light, "light_energy", rest, 0.10) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	tween.tween_callback(func() -> void: _ritual_light_rest.erase(key))


func _finish_verdict(target: Node3D, committed: bool, anchor: Vector3) -> void:
	# Verdict-phase support layers shared by motion and reduced-motion paths.
	if committed:
		_request_cue("verdict_commit_deep")
		if not _reduce_motion:
			_emit_vfx("mount_sparks", anchor)
			_bloom_target_light(target)
			_settle_nearest_interactable(anchor)
	else:
		_request_cue("verdict_refusal_seal")
		if not _reduce_motion:
			_play_seal_stroke(anchor)


func _play_seal_stroke(anchor: Vector3) -> void:
	# Refusal seal: one thin horizontal bar strikes down and holds a beat — the
	# ledger stamp made physical (~0.3 s). Coral→cold slate, then gone.
	if _seal_line == null or _seal_material == null:
		return
	var palette: Dictionary = SealedLighthouseWorldBuilder.PALETTE
	var coral: Color = palette.warning_coral
	var cold: Color = coral.lerp(palette.wet_slate, 0.55)
	_seal_line.global_position = anchor + Vector3(0.0, 0.42, 0.0)
	_seal_material.emission = coral
	# Snap in at full alpha — a stamp lands, it does not fade in.
	_seal_material.albedo_color = Color(coral, 0.9)
	_seal_line.visible = true
	var tween := _new_tween("verdict_seal")
	tween.tween_property(
		_seal_line, "global_position:y", anchor.y + 0.06, 0.12
	).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	tween.parallel().tween_property(_seal_material, "emission", cold, 0.12)
	# Unshaded bar: cool the albedo hue with the emission so the stroke visibly
	# chills from coral to slate as it seals.
	tween.parallel().tween_property(_seal_material, "albedo_color", Color(cold, 0.9), 0.12)
	tween.tween_interval(0.08)
	tween.tween_property(_seal_material, "albedo_color:a", 0.0, 0.10) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	tween.tween_callback(func() -> void: _seal_line.visible = false)


func _bloom_target_light(target: Node3D) -> void:
	# Commit bloom envelope on the prop's own authored lamp (never a new light):
	# +18% for ~0.12 s, easing home over ~0.35 s. Skipped while a commit-glow
	# tween is still driving the same light, so envelopes never fight.
	var light := _find_target_light(target)
	if light == null:
		return
	var glow_key := "commit_%s" % (light.get_parent().get_instance_id() if light.get_parent() != null else 0)
	var glow_tween := _active_tweens.get(glow_key) as Tween
	if glow_tween != null and glow_tween.is_valid() and glow_tween.is_running():
		return
	var key := "bloom_%s" % light.get_instance_id()
	var rest: float = _ritual_light_rest.get(key, light.light_energy)
	if rest <= 0.0:
		return
	_ritual_light_rest[key] = rest
	var tween := _new_tween(key)
	tween.tween_property(light, "light_energy", rest * 1.18, 0.12) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	tween.tween_property(light, "light_energy", rest, 0.35) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.tween_callback(func() -> void: _ritual_light_rest.erase(key))


func _settle_nearest_interactable(anchor: Vector3) -> void:
	# Commit settle-bounce: the acting prop's focus marker takes a 2% settle
	# (guarded — interactables own the envelope; absent method is a no-op).
	var best: Node = null
	var best_distance := 3.2
	for node in get_tree().get_nodes_in_group("sl_interactables"):
		var interactable := node as Node3D
		if interactable == null:
			continue
		var distance := anchor.distance_to(interactable.global_position)
		if distance < best_distance:
			best = interactable
			best_distance = distance
	if best != null and best.has_method("play_commit_settle"):
		best.call("play_commit_settle")


func _ritual_anchor(target: Node3D) -> Vector3:
	# Anchor the ritual at the prop's own lamp when it has one (mount light sits
	# 3.6 m up the post; the lens glow at 1.3 m), else just above the prop, else
	# at the investigator — the proposal always visibly belongs to its actor.
	if target != null:
		var light := _find_target_light(target)
		if light != null:
			return light.global_position
		return target.global_position + Vector3(0.0, 0.9, 0.0)
	if _player != null:
		return _player.global_position + Vector3(0.0, 1.15, 0.0)
	return Vector3.ZERO


func _find_target_light(target: Node3D) -> OmniLight3D:
	if target == null:
		return null
	if target is OmniLight3D:
		return target as OmniLight3D
	for child in target.get_children():
		if child is OmniLight3D:
			return child as OmniLight3D
	return null


func _request_cue(cue_id: String) -> void:
	# Pooled, gesture/mute-gated cue request — playback policy stays with the
	# audio node; the director never bypasses its gating.
	if _audio_feedback == null and is_inside_tree():
		_audio_feedback = get_tree().get_first_node_in_group("sl_audio_feedback")
	if _audio_feedback != null and _audio_feedback.has_method("play_cue"):
		_audio_feedback.call("play_cue", cue_id)


func play_ending(on_finished: Callable) -> void:
	# P-B06 Route earned: pan from the tide marks up to the sealed tower, hold on
	# it dark (it stays sealed, D-030), then the HARBOR-SIDE signal lamp sweeps
	# its beam from the tide marks toward the channel buoy while the camera
	# follows, and the shot holds. Reduced motion: instant static end card with
	# the beam resting aimed at the channel (steady semantic state).
	beat_played.emit("P-B06")
	_emit_vfx("tide_motes")
	cinematic_state_changed.emit(true)
	_player.input_locked = true
	if _reduce_motion:
		_rest_signal_beam()
		on_finished.call()
		return
	_cinematic_camera.current = true
	_cinematic_camera.fov = 62.0
	_cinematic_camera.global_position = _player.global_position + Vector3(-2.0, 2.5, -3.0)
	_cinematic_camera.look_at(Vector3(-8.5, 0.5, 15.5))
	_cinematic_finish = on_finished
	_cinematic_keep_letterbox = true
	var tween := _new_tween("ending")
	tween.tween_interval(1.2)
	tween.tween_property(_cinematic_camera, "global_position", Vector3(-4.0, 3.5, 8.0), 2.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.parallel().tween_property(_cinematic_camera, "fov", 57.0, 2.8) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	tween.parallel().tween_method(
		func(weight: float) -> void:
			var target := Vector3(-8.5, 0.5, 15.5).lerp(TOWER_FOCUS, weight)
			_cinematic_camera.look_at(target),
		0.0, 1.0, 2.8
	)
	tween.tween_interval(0.6)  # hold on the dark, sealed tower
	tween.tween_callback(func() -> void: _arm_signal_beam())
	tween.tween_method(
		func(weight: float) -> void:
			if _beam_pivot != null:
				_beam_pivot.look_at(BEAM_AIM_TIDE.lerp(BEAM_AIM_CHANNEL, weight))
			_cinematic_camera.look_at(TOWER_FOCUS.lerp(CHANNEL_LOOK, weight)),
		0.0, 1.0, 2.2
	).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if _beam_material != null:
		tween.parallel().tween_property(_beam_material, "albedo_color:a", 0.22, 0.7)
		tween.tween_property(_beam_material, "albedo_color:a", 0.16, 0.8)  # settled hold
	else:
		tween.tween_interval(0.8)
	tween.tween_callback(func() -> void: _finish_active_cinematic())


func _arm_signal_beam() -> void:
	# Harbor lamp only: beam originates at the dock mount and aims at water.
	if _beam_pivot == null or _beam_mesh == null:
		return
	_beam_pivot.look_at(BEAM_AIM_TIDE)
	if _beam_material != null:
		_beam_material.albedo_color.a = 0.0
	_beam_mesh.visible = true
	if _mount_light != null:
		var pulse := _new_tween("beam_fade")
		pulse.tween_property(_mount_light, "light_energy", 3.1, 0.5) \
			.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		pulse.tween_property(_mount_light, "light_energy", 2.6, 1.4) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func _rest_signal_beam() -> void:
	# Reduced-motion / interrupted ending: the restored harbor signal reads as a
	# steady beam resting on the channel — no sweep, no pulsing.
	if _beam_pivot == null or _beam_mesh == null:
		return
	_beam_pivot.look_at(BEAM_AIM_CHANNEL)
	if _beam_material != null:
		_beam_material.albedo_color.a = 0.12
	_beam_mesh.visible = true


func _emit_vfx(key: String, position_override: Variant = null) -> void:
	if _reduce_motion:
		return
	var particles := _beat_vfx.get(key) as CPUParticles3D
	if particles == null:
		return
	if position_override is Vector3:
		particles.global_position = position_override
	else:
		# The verdict ritual re-anchors pooled emitters to acting props; without
		# an override the burst returns to its authored rest position.
		particles.position = particles.get_meta("rest_position", particles.position)
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
	# Reduced motion keeps steady semantic light/color states while removing
	# camera travel, rain, wave motion, buoy bob, lamp flicker, mist drift,
	# lightning, halo scaling, verdict-ritual sweeps, and particle bursts.
	if _rain != null:
		_rain.emitting = not _reduce_motion
	if _reduce_motion:
		_stop_all_vfx()
		for key in [
			"intro", "ending", "lightning", "refusal", "commit_halo", "beam_fade",
			"verdict_ring", "verdict_seal", "lens_glint",
		]:
			var tween := _active_tweens.get(key) as Tween
			if tween != null and tween.is_valid():
				tween.kill()
		# Per-light ritual envelopes (repair blink, commit bloom): kill and
		# restore each captured rest energy so no lamp is left mid-envelope.
		for key in _active_tweens.keys():
			var text_key := String(key)
			if not (text_key.begins_with("repair_") or text_key.begins_with("bloom_")):
				continue
			var envelope := _active_tweens.get(key) as Tween
			if envelope != null and envelope.is_valid():
				envelope.kill()
		for rest_key in _ritual_light_rest.keys():
			var id_text := String(rest_key).get_slice("_", 1)
			var light := instance_from_id(int(id_text)) as OmniLight3D
			if light != null:
				light.light_energy = _ritual_light_rest[rest_key]
		_ritual_light_rest.clear()
		_lightning_boost = 0.0
		_refusal_chill = 0.0
		if _commit_halo != null:
			_commit_halo.visible = false
		if _inspection_ring != null:
			_inspection_ring.visible = false
		if _seal_line != null:
			_seal_line.visible = false
		if _buoy_root != null:
			_buoy_root.position = _buoy_rest
			_buoy_root.rotation = Vector3.ZERO
		if _store_lamp != null:
			_store_lamp.light_energy = 1.1
		if _mira_lantern != null:
			_mira_lantern.light_energy = 0.5
		# Beacon holds its static mid-alpha; the lens rests where it stopped
		# with the glint spark extinguished — steady semantic states only.
		if _beacon_material != null:
			_beacon_material.set_shader_parameter(
				&"pulse", (BEACON_PULSE_MIN + BEACON_PULSE_MAX) * 0.5
			)
		if _lens_glint_material != null:
			_lens_glint_material.albedo_color.a = 0.0
		for sheet_value in _mist_sheets:
			var sheet := sheet_value as MeshInstance3D
			if sheet != null:
				sheet.position = sheet.get_meta("rest_position", sheet.position)
		if _beam_mesh != null and _beam_mesh.visible:
			_rest_signal_beam()
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
