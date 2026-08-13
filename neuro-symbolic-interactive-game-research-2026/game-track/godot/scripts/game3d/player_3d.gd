class_name PlayerInvestigator3D
extends CharacterBody3D

## Third-person investigator controller. Movement and focus are presentation;
## every world-changing intent is proposed to the root controller (GDI-01).

signal interact_requested(interaction_id: String)
signal focus_changed(interactable: Interactable3D)

const WALK_SPEED := 4.2
const ACCELERATION := 10.0
const GRAVITY := 18.0
const MOUSE_SENSITIVITY := 0.0028

var camera: Camera3D
var input_locked: bool = false
var _spring_arm: SpringArm3D
var _yaw: float = 0.0
var _pitch: float = -0.32
var _focused: Interactable3D = null


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
	player._spring_arm.position = Vector3(0.0, 1.7, 0.0)
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
		_yaw -= event.relative.x * MOUSE_SENSITIVITY
		_pitch = clampf(_pitch - event.relative.y * MOUSE_SENSITIVITY, -1.1, 0.25)
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
	velocity.x = move_toward(velocity.x, target.x, ACCELERATION * delta)
	velocity.z = move_toward(velocity.z, target.z, ACCELERATION * delta)
	move_and_slide()
	_update_focus()


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
