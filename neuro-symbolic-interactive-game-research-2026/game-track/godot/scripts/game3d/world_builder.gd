class_name SealedLighthouseWorldBuilder
extends RefCounted

## Builds the 3D presentation of the Brinewake harbor slice procedurally.
## Presentation only: geometry, weather, and lights read committed snapshots and
## never touch canonical state (GDI-01, repository engine rules).
##
## Worldview citations: W-001 dock saved, W-002 dark offshore lighthouse,
## W-003 Captain Mira harbor watch, W-004 lamp store reachable with signal lens.

const PALETTE := {
	"storm_ink": Color("#17232D"),
	"wet_slate": Color("#344956"),
	"paper_fog": Color("#D9D3C4"),
	"brass": Color("#A77A3A"),
	"signal_amber": Color("#F2B84B"),
	"warning_coral": Color("#D9685F"),
}

const PACK_3D_RELATIVE := "../assets/concepts/pack-3d"


static func load_pack_texture(file_name: String) -> Texture2D:
	# Optional presentation-candidate concept texture. The build must remain fully
	# playable when the generated pack is absent (primary track stays programmatic).
	var pack_dir := ProjectSettings.globalize_path("res://").path_join(PACK_3D_RELATIVE)
	var path := pack_dir.path_join(file_name)
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(path)
	if image == null:
		return null
	return ImageTexture.create_from_image(image)


static func flat_material(color: Color, roughness: float = 0.85) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	return material


static func textured_material(file_name: String, fallback: Color, uv_scale: Vector3 = Vector3.ONE) -> StandardMaterial3D:
	var material := flat_material(fallback)
	var texture := load_pack_texture(file_name)
	if texture != null:
		material.albedo_texture = texture
		material.albedo_color = Color(0.82, 0.82, 0.82)
		material.uv1_scale = uv_scale
	return material


static func add_box(parent: Node3D, size: Vector3, position: Vector3, material: Material, with_collision: bool = true) -> MeshInstance3D:
	var mesh_instance := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = size
	mesh_instance.mesh = box
	mesh_instance.material_override = material
	mesh_instance.position = position
	parent.add_child(mesh_instance)
	if with_collision:
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var box_shape := BoxShape3D.new()
		box_shape.size = size
		shape.shape = box_shape
		body.add_child(shape)
		mesh_instance.add_child(body)
	return mesh_instance


static func add_cylinder(parent: Node3D, radius: float, height: float, position: Vector3, material: Material, with_collision: bool = true) -> MeshInstance3D:
	var mesh_instance := MeshInstance3D.new()
	var cylinder := CylinderMesh.new()
	cylinder.top_radius = radius
	cylinder.bottom_radius = radius
	cylinder.height = height
	mesh_instance.mesh = cylinder
	mesh_instance.material_override = material
	mesh_instance.position = position
	parent.add_child(mesh_instance)
	if with_collision:
		var body := StaticBody3D.new()
		var shape := CollisionShape3D.new()
		var cylinder_shape := CylinderShape3D.new()
		cylinder_shape.radius = radius
		cylinder_shape.height = height
		shape.shape = cylinder_shape
		body.add_child(shape)
		mesh_instance.add_child(body)
	return mesh_instance


static func build(root: Node3D) -> Dictionary:
	# Returns named handles the director and root controller use for beats and
	# state-snapshot synchronization.
	var handles := {}
	var world := Node3D.new()
	world.name = "HarborWorld"
	root.add_child(world)

	handles["environment"] = _build_environment(root)
	_build_sea(world)
	_build_dock(world)
	_build_lamp_store(world)
	handles["lighthouse_light"] = _build_lighthouse(world)
	handles["rain"] = _build_rain(world)
	handles["mira"] = _build_mira(world)
	handles["lens_prop"] = _build_lens_prop(world)
	handles["lamp_mount"] = _build_lamp_mount(world)
	handles["tide_marks"] = _build_tide_marks(world)
	handles["buoy_light"] = _build_buoy(world)
	handles["world"] = world
	return handles


static func _build_environment(root: Node3D) -> WorldEnvironment:
	var world_environment := WorldEnvironment.new()
	world_environment.name = "StormEnvironment"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = PALETTE.storm_ink.darkened(0.4)
	sky_material.sky_horizon_color = PALETTE.wet_slate.darkened(0.2)
	sky_material.ground_bottom_color = PALETTE.storm_ink.darkened(0.6)
	sky_material.ground_horizon_color = PALETTE.wet_slate.darkened(0.35)
	sky_material.sun_angle_max = 5.0
	sky.sky_material = sky_material
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = 0.7
	environment.fog_enabled = true
	environment.fog_light_color = PALETTE.wet_slate
	environment.fog_density = 0.015
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world_environment.environment = environment
	root.add_child(world_environment)

	var moon := DirectionalLight3D.new()
	moon.name = "StormMoon"
	moon.light_color = PALETTE.paper_fog
	moon.light_energy = 0.35
	moon.rotation_degrees = Vector3(-38.0, 152.0, 0.0)
	moon.shadow_enabled = true
	root.add_child(moon)
	return world_environment


static func _build_sea(world: Node3D) -> void:
	var sea := MeshInstance3D.new()
	sea.name = "Sea"
	var plane := PlaneMesh.new()
	plane.size = Vector2(400.0, 400.0)
	plane.subdivide_width = 60
	plane.subdivide_depth = 60
	sea.mesh = plane
	var shader := Shader.new()
	shader.code = """
shader_type spatial;
render_mode cull_back;
uniform vec3 deep_color : source_color = vec3(0.05, 0.09, 0.12);
uniform vec3 crest_color : source_color = vec3(0.20, 0.29, 0.34);
uniform float agitation : hint_range(0.0, 2.0) = 1.0;
varying float crest;
void vertex() {
	vec3 world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float wave = sin(world_pos.x * 0.11 + TIME * 0.9) * 0.5
		+ sin(world_pos.z * 0.07 - TIME * 0.6) * 0.5
		+ sin((world_pos.x + world_pos.z) * 0.05 + TIME * 0.35) * 0.6;
	VERTEX.y += wave * 0.35 * agitation;
	crest = clamp(wave * 0.5 + 0.5, 0.0, 1.0);
}
void fragment() {
	ALBEDO = mix(deep_color, crest_color, crest * 0.55);
	ROUGHNESS = 0.32;
	SPECULAR = 0.6;
}
"""
	var material := ShaderMaterial.new()
	material.shader = shader
	sea.material_override = material
	sea.position = Vector3(0.0, -0.9, 60.0)
	world.add_child(sea)
	sea.set_meta("sea_material", material)
	world.set_meta("sea", sea)


static func _build_dock(world: Node3D) -> void:
	var dock := Node3D.new()
	dock.name = "HarborDock"
	world.add_child(dock)
	var plank_material := textured_material(
		"SL3D-T01-wet-slate-planks.png", PALETTE.wet_slate, Vector3(6.0, 6.0, 1.0)
	)
	add_box(dock, Vector3(18.0, 0.5, 20.0), Vector3(0.0, -0.25, 5.0), plank_material)
	var piling_material := flat_material(PALETTE.storm_ink.lightened(0.06))
	for x in [-8.0, -4.0, 0.0, 4.0, 8.0]:
		add_cylinder(dock, 0.28, 2.4, Vector3(x, -1.1, 14.8), piling_material, false)
	var rail_material := flat_material(PALETTE.storm_ink.lightened(0.12))
	add_box(dock, Vector3(18.0, 0.12, 0.12), Vector3(0.0, 0.9, 15.0), rail_material, false)
	for x in [-8.5, -4.25, 0.0, 4.25, 8.5]:
		add_box(dock, Vector3(0.12, 1.0, 0.12), Vector3(x, 0.4, 15.0), rail_material, false)
	# Fire-scarred but saved crates: W-001 dock fire averted.
	var crate_material := flat_material(PALETTE.wet_slate.lightened(0.08))
	add_box(dock, Vector3(1.2, 1.2, 1.2), Vector3(-7.0, 0.6, 10.5), crate_material)
	add_box(dock, Vector3(0.9, 0.9, 0.9), Vector3(-5.8, 0.45, 11.2), crate_material)
	add_box(dock, Vector3(1.0, 0.6, 1.4), Vector3(7.2, 0.3, 3.0), crate_material)


static func _build_lamp_store(world: Node3D) -> void:
	var store := Node3D.new()
	store.name = "LampStore"
	store.position = Vector3(-6.0, 0.0, 1.0)
	world.add_child(store)
	var wall_material := flat_material(PALETTE.storm_ink.lightened(0.1))
	var roof_material := flat_material(PALETTE.storm_ink.darkened(0.15))
	# Hut with a door gap on the +z face toward the dock walkway.
	add_box(store, Vector3(6.0, 3.0, 0.25), Vector3(0.0, 1.5, -2.5), wall_material)
	add_box(store, Vector3(0.25, 3.0, 5.0), Vector3(-3.0, 1.5, 0.0), wall_material)
	add_box(store, Vector3(0.25, 3.0, 5.0), Vector3(3.0, 1.5, 0.0), wall_material)
	add_box(store, Vector3(2.0, 3.0, 0.25), Vector3(-2.0, 1.5, 2.5), wall_material)
	add_box(store, Vector3(2.0, 3.0, 0.25), Vector3(2.0, 1.5, 2.5), wall_material)
	add_box(store, Vector3(2.0, 0.8, 0.25), Vector3(0.0, 2.6, 2.5), wall_material)
	add_box(store, Vector3(6.6, 0.25, 5.6), Vector3(0.0, 3.1, 0.0), roof_material)
	# Interior counter and shelf, brass instruments.
	var brass_material := textured_material("SL3D-T02-oxidized-brass.png", PALETTE.brass)
	add_box(store, Vector3(2.4, 1.0, 0.8), Vector3(-1.2, 0.5, -1.6), flat_material(PALETTE.wet_slate))
	add_box(store, Vector3(0.5, 0.3, 0.5), Vector3(-1.2, 1.15, -1.6), brass_material, false)
	var lamp := OmniLight3D.new()
	lamp.light_color = PALETTE.paper_fog
	lamp.light_energy = 1.1
	lamp.omni_range = 7.0
	lamp.position = Vector3(0.0, 2.4, 0.0)
	store.add_child(lamp)


static func _build_lighthouse(world: Node3D) -> OmniLight3D:
	# W-002: offshore, dark, observed but never entered in this slice.
	var island := Node3D.new()
	island.name = "OffshoreLighthouse"
	island.position = Vector3(6.0, 0.0, 62.0)
	world.add_child(island)
	var rock_material := flat_material(PALETTE.storm_ink.lightened(0.04))
	add_cylinder(island, 6.0, 3.0, Vector3(0.0, -0.5, 0.0), rock_material, false)
	var tower_material := flat_material(PALETTE.storm_ink.lightened(0.16))
	add_cylinder(island, 1.6, 14.0, Vector3(0.0, 7.0, 0.0), tower_material, false)
	add_cylinder(island, 2.0, 1.0, Vector3(0.0, 14.5, 0.0), flat_material(PALETTE.storm_ink), false)
	var lantern_material := flat_material(PALETTE.storm_ink.lightened(0.25), 0.4)
	add_cylinder(island, 1.2, 1.8, Vector3(0.0, 15.6, 0.0), lantern_material, false)
	add_cylinder(island, 1.5, 0.6, Vector3(0.0, 16.8, 0.0), flat_material(PALETTE.storm_ink.darkened(0.2)), false)
	var beacon := OmniLight3D.new()
	beacon.name = "SealedBeacon"
	beacon.light_color = PALETTE.signal_amber
	beacon.light_energy = 0.0
	beacon.omni_range = 40.0
	beacon.position = Vector3(0.0, 15.6, 0.0)
	island.add_child(beacon)
	return beacon


static func _build_rain(world: Node3D) -> CPUParticles3D:
	var rain := CPUParticles3D.new()
	rain.name = "RainLayer"
	rain.amount = 900
	rain.lifetime = 1.1
	rain.emission_shape = CPUParticles3D.EMISSION_SHAPE_BOX
	rain.emission_box_extents = Vector3(22.0, 0.5, 22.0)
	rain.direction = Vector3(-0.15, -1.0, 0.05)
	rain.spread = 4.0
	rain.gravity = Vector3(0.0, -22.0, 0.0)
	rain.initial_velocity_min = 14.0
	rain.initial_velocity_max = 18.0
	var streak := BoxMesh.new()
	streak.size = Vector3(0.015, 0.5, 0.015)
	rain.mesh = streak
	var rain_material := StandardMaterial3D.new()
	rain_material.albedo_color = Color(0.75, 0.8, 0.85, 0.28)
	rain_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	rain_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	streak.material = rain_material
	rain.position = Vector3(0.0, 10.0, 6.0)
	world.add_child(rain)
	return rain


static func _build_mira(world: Node3D) -> Node3D:
	# W-003: harbor watch captain posted near the dock edge, watching the tower.
	var mira := Node3D.new()
	mira.name = "CaptainMira"
	mira.position = Vector3(3.0, 0.0, 11.0)
	world.add_child(mira)
	var coat := flat_material(PALETTE.wet_slate.darkened(0.1))
	add_cylinder(mira, 0.34, 1.25, Vector3(0.0, 0.65, 0.0), coat, false)
	add_cylinder(mira, 0.30, 0.5, Vector3(0.0, 1.45, 0.0), coat, false)
	var head := MeshInstance3D.new()
	var head_mesh := SphereMesh.new()
	head_mesh.radius = 0.22
	head_mesh.height = 0.44
	head.mesh = head_mesh
	head.material_override = flat_material(PALETTE.paper_fog.darkened(0.25))
	head.position = Vector3(0.0, 1.85, 0.0)
	mira.add_child(head)
	var cap := add_cylinder(mira, 0.24, 0.12, Vector3(0.0, 2.02, 0.0), flat_material(PALETTE.storm_ink), false)
	cap.rotation_degrees.x = 4.0
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.4
	capsule.height = 1.9
	shape.shape = capsule
	shape.position = Vector3(0.0, 1.0, 0.0)
	body.add_child(shape)
	mira.add_child(body)
	var lantern_glow := OmniLight3D.new()
	lantern_glow.light_color = PALETTE.signal_amber
	lantern_glow.light_energy = 0.5
	lantern_glow.omni_range = 3.0
	lantern_glow.position = Vector3(0.35, 1.0, 0.2)
	mira.add_child(lantern_glow)
	mira.look_at_from_position(mira.position, Vector3(6.0, 0.0, 62.0), Vector3.UP)
	mira.rotation.x = 0.0
	return mira


static func _build_lens_prop(world: Node3D) -> Node3D:
	# W-004: the replacement signal lens rests in the reachable lamp store.
	var lens := Node3D.new()
	lens.name = "SignalLensProp"
	lens.position = Vector3(-5.0, 0.0, 0.0)
	world.add_child(lens)
	var pedestal_material := flat_material(PALETTE.wet_slate)
	add_box(lens, Vector3(0.7, 0.9, 0.7), Vector3(0.0, 0.45, 0.0), pedestal_material, false)
	var brass_material := textured_material("SL3D-T02-oxidized-brass.png", PALETTE.brass)
	var ring := MeshInstance3D.new()
	var torus := TorusMesh.new()
	torus.inner_radius = 0.22
	torus.outer_radius = 0.34
	ring.mesh = torus
	ring.material_override = brass_material
	ring.position = Vector3(0.0, 1.25, 0.0)
	ring.rotation_degrees = Vector3(90.0, 0.0, 0.0)
	lens.add_child(ring)
	var glass := MeshInstance3D.new()
	var glass_mesh := SphereMesh.new()
	glass_mesh.radius = 0.24
	glass_mesh.height = 0.48
	glass.mesh = glass_mesh
	var glass_material := StandardMaterial3D.new()
	glass_material.albedo_color = Color(PALETTE.paper_fog, 0.55)
	glass_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	glass_material.roughness = 0.15
	glass.material_override = glass_material
	glass.position = Vector3(0.0, 1.25, 0.0)
	lens.add_child(glass)
	var glow := OmniLight3D.new()
	glow.name = "LensGlow"
	glow.light_color = PALETTE.paper_fog
	glow.light_energy = 0.4
	glow.omni_range = 2.0
	glow.position = Vector3(0.0, 1.3, 0.0)
	lens.add_child(glow)
	return lens


static func _build_lamp_mount(world: Node3D) -> Node3D:
	var mount := Node3D.new()
	mount.name = "DockLampMount"
	mount.position = Vector3(7.0, 0.0, 13.5)
	world.add_child(mount)
	var post_material := flat_material(PALETTE.storm_ink.lightened(0.1))
	add_cylinder(mount, 0.12, 3.4, Vector3(0.0, 1.7, 0.0), post_material)
	var brass_material := textured_material("SL3D-T02-oxidized-brass.png", PALETTE.brass)
	add_box(mount, Vector3(0.6, 0.6, 0.6), Vector3(0.0, 3.6, 0.0), brass_material, false)
	var mount_light := OmniLight3D.new()
	mount_light.name = "MountLight"
	mount_light.light_color = PALETTE.signal_amber
	mount_light.light_energy = 0.0
	mount_light.omni_range = 14.0
	mount_light.position = Vector3(0.0, 3.6, 0.0)
	mount.add_child(mount_light)
	return mount


static func _build_tide_marks(world: Node3D) -> Node3D:
	# Next-path affordance: revealed only after the authorized hint commit.
	var marks := Node3D.new()
	marks.name = "TideMarks"
	marks.position = Vector3(-8.5, 0.05, 15.5)
	marks.visible = false
	world.add_child(marks)
	var mark_material := flat_material(PALETTE.signal_amber.darkened(0.1), 0.5)
	for index in range(4):
		var stripe := add_box(
			marks,
			Vector3(0.5 - index * 0.08, 0.04, 0.16),
			Vector3(0.0, 0.0, index * 0.5),
			mark_material,
			false
		)
		stripe.rotation_degrees.y = index * 7.0
	var glow := OmniLight3D.new()
	glow.light_color = PALETTE.signal_amber
	glow.light_energy = 0.0
	glow.omni_range = 4.0
	glow.position = Vector3(0.0, 0.6, 0.7)
	glow.name = "TideGlow"
	marks.add_child(glow)
	return marks


static func _build_buoy(world: Node3D) -> OmniLight3D:
	var buoy := Node3D.new()
	buoy.name = "ChannelBuoy"
	buoy.position = Vector3(-14.0, -0.4, 34.0)
	world.add_child(buoy)
	add_cylinder(buoy, 0.5, 1.2, Vector3.ZERO, flat_material(PALETTE.warning_coral.darkened(0.25)), false)
	var light := OmniLight3D.new()
	light.name = "BuoyLight"
	light.light_color = PALETTE.warning_coral
	light.light_energy = 0.6
	light.omni_range = 8.0
	light.position = Vector3(0.0, 1.0, 0.0)
	buoy.add_child(light)
	return light
