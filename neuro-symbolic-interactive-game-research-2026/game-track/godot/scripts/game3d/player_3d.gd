class_name PlayerInvestigator3D
extends CharacterBody3D

## Third-person investigator controller. Movement and focus are presentation;
## every world-changing intent is proposed to the root controller (GDI-01).

signal interact_requested(interaction_id: String)
signal focus_changed(interactable: Interactable3D)
signal footstep_requested(step_index: int)
signal movement_state_changed(active: bool)

const WALK_SPEED := 4.2  # Full dock diagonal ≈ 26.9 m → ≈ 6.4 s; longest golden-path leg ≈ 3.9 s (< 8 s target) — base speed kept.
const ACCELERATION := 28.0  # 4.2 / 28 ≈ 0.15 s to reach max speed — snappy start without skating.
const DECELERATION := 42.0  # 4.2 / 42 ≈ 0.10 s to stop — plants the character for focus/interact.
const GRAVITY := 18.0
const MOUSE_SENSITIVITY := 0.0028
const SPRING_ARM_HEIGHT := 1.7
const STEP_STRIDE := 1.65  # metres per footstep signal; the view bob shares this cadence.
const VIEW_BOB_AMPLITUDE := 0.032  # ≤ 3.2 cm on a 5.2 m boom — subtle by design.
const VIEW_ROLL_MAX_DEG := 0.35  # ≤ 0.4° camera roll sway, stride-synced with the bob.

var camera: Camera3D
var input_locked: bool = false
var _spring_arm: SpringArm3D
var _yaw: float = 0.0
var _pitch: float = -0.32
var _focused: Interactable3D = null
var _movement_active: bool = false
var _step_distance: float = 0.0
var _step_index: int = 0
var _bob_offset: float = 0.0
var _roll_offset: float = 0.0
var _director: Node = null


static func create() -> PlayerInvestigator3D:
	var player := PlayerInvestigator3D.new()
	player.name = "PlayerInvestigator"
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.35
	capsule.height = 1.7
	shape.shape = capsule
	shape.position = Vector3(0.0, 0.85, 0.0)
	player.add_child(shape)

	var visual := MeshInstance3D.new()
	var body_mesh := CapsuleMesh.new()
	body_mesh.radius = 0.32
	body_mesh.height = 1.6
	visual.mesh = body_mesh
	visual.position = Vector3(0.0, 0.8, 0.0)
	var coat := StandardMaterial3D.new()
	coat.albedo_color = SealedLighthouseWorldBuilder.PALETTE.paper_fog.darkened(0.45)
	visual.material_override = coat
	player.add_child(visual)

	var lantern := OmniLight3D.new()
	lantern.light_color = SealedLighthouseWorldBuilder.PALETTE.signal_amber
	lantern.light_energy = 0.35
	lantern.omni_range = 3.5
	lantern.position = Vector3(0.25, 1.1, 0.0)
	player.add_child(lantern)

	player._spring_arm = SpringArm3D.new()
	player._spring_arm.spring_length = 5.2
	player._spring_arm.position = Vector3(0.0, SPRING_ARM_HEIGHT, 0.0)
	player._spring_arm.collision_mask = 1
	player.add_child(player._spring_arm)
	player.camera = Camera3D.new()
	player.camera.name = "PlayerCamera"
	player.camera.fov = 62.0
	player._spring_arm.add_child(player.camera)
	return player


func _ready() -> void:
	_apply_camera_rotation()


func _unhandled_input(event: InputEvent) -> void:
	if input_locked:
		return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		# `screen_relative` keeps look sensitivity stable when the web canvas or
		# browser zoom changes the effective viewport resolution.
		_yaw -= event.screen_relative.x * MOUSE_SENSITIVITY
		_pitch = clampf(_pitch - event.screen_relative.y * MOUSE_SENSITIVITY, -1.1, 0.25)
		_apply_camera_rotation()
	elif event.is_action_pressed("sl_interact") and _focused != null and _focused.enabled:
		interact_requested.emit(_focused.interaction_id)


func _apply_camera_rotation() -> void:
	rotation.y = _yaw
	if _spring_arm != null:
		_spring_arm.rotation.x = _pitch


func _physics_process(delta: float) -> void:
	if not is_on_floor():
		velocity.y -= GRAVITY * delta
	var move_input := Vector2.ZERO
	if not input_locked:
		move_input = Input.get_vector("sl_move_left", "sl_move_right", "sl_move_forward", "sl_move_back")
	var direction := (transform.basis * Vector3(move_input.x, 0.0, move_input.y)).normalized()
	var target := direction * WALK_SPEED
	# Asymmetric smoothing: quick arrival (~0.15 s) but a firmer stop (~0.10 s)
	# so releasing input plants the investigator right inside a focus ring.
	var rate := ACCELERATION if direction.length_squared() > 0.01 else DECELERATION
	velocity.x = move_toward(velocity.x, target.x, rate * delta)
	velocity.z = move_toward(velocity.z, target.z, rate * delta)
	move_and_slide()
	_update_movement_feedback(delta, move_input.length_squared() > 0.01)
	_update_view_bob(delta)
	_update_focus()


func _update_movement_feedback(delta: float, has_input: bool) -> void:
	var horizontal_speed := Vector2(velocity.x, velocity.z).length()
	var moving_now := not input_locked and has_input and is_on_floor() and horizontal_speed > 0.35
	if moving_now != _movement_active:
		_movement_active = moving_now
		movement_state_changed.emit(_movement_active)
	if not moving_now:
		_step_distance = 0.0
		return
	_step_distance += horizontal_speed * delta
	if _step_distance >= STEP_STRIDE:
		_step_distance = fmod(_step_distance, STEP_STRIDE)
		_step_index += 1
		footstep_requested.emit(_step_index)


func _update_view_bob(delta: float) -> void:
	# Camera-boom bob phase-locked to the footstep stride: the dip bottoms out
	# exactly when `footstep_requested` fires, so eye and ear agree. A ≤0.4°
	# roll sway rides the same stride phase (left/right alternation), so the
	# camera leans into each step the ear hears. Both skipped entirely (and
	# eased back to rest) under reduced motion or locked input.
	if _spring_arm == null:
		return
	if _director == null:
		_director = get_tree().get_first_node_in_group("sl_presentation_director")
	var motion_reduced: bool = _director != null and bool(_director.get("reduce_motion"))
	var target_offset := 0.0
	var target_roll := 0.0
	if _movement_active and not motion_reduced and not input_locked:
		# cos(TAU·phase) peaks at phase 0/1 (mid-stride) and dips at the step.
		var phase := _step_distance / STEP_STRIDE
		target_offset = -VIEW_BOB_AMPLITUDE * 0.5 * (1.0 - cos(TAU * phase))
		# sin alternates sign each half-stride: lean left, then right.
		var side := -1.0 if _step_index % 2 == 0 else 1.0
		target_roll = deg_to_rad(VIEW_ROLL_MAX_DEG) * sin(TAU * phase * 0.5) * side
	_bob_offset = lerpf(_bob_offset, target_offset, minf(delta * 14.0, 1.0))
	_roll_offset = lerpf(_roll_offset, target_roll, minf(delta * 10.0, 1.0))
	_spring_arm.position.y = SPRING_ARM_HEIGHT + _bob_offset
	camera.rotation.z = _roll_offset


func _update_focus() -> void:
	var best: Interactable3D = null
	var best_distance := INF
	for area in get_tree().get_nodes_in_group("sl_interactables"):
		var interactable := area as Interactable3D
		if interactable == null or not interactable.enabled:
			continue
		var distance := global_position.distance_to(interactable.global_position)
		var radius := 2.2
		var shape := interactable.get_child(0) as CollisionShape3D
		if shape != null and shape.shape is SphereShape3D:
			radius = (shape.shape as SphereShape3D).radius
		if distance <= radius and distance < best_distance:
			best = interactable
			best_distance = distance
	if best != _focused:
		_focused = best
		focus_changed.emit(_focused)


func get_engineering_snapshot() -> Dictionary:
	return {
		"engineering_only": true,
		"claim_boundary": "Player presentation/input instrumentation; not usability, immersion, or efficacy evidence.",
		"input_locked": input_locked,
		"mouse_look_requires_capture": true,
		"resolution_independent_mouse_delta": "screen_relative",
		"movement_feedback": ["movement_state_changed", "distance-paced-footstep-request", "stride-locked-view-bob"],
		"focused_interaction_id": "" if _focused == null else _focused.interaction_id,
		"world_change_boundary": "interact_requested signal only; root proposal router owns machine calls",
	}
