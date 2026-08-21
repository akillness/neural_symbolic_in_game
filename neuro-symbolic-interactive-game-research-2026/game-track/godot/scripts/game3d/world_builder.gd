class_name SealedLighthouseWorldBuilder
extends RefCounted

## Builds the 3D presentation of the Brinewake harbor slice procedurally.
## Presentation only: geometry, weather, and lights read committed snapshots and
## never touch canonical state (GDI-01, repository engine rules).
##
## Worldview citations: W-001 dock saved, W-002 dark offshore lighthouse,
## W-003 Captain Mira harbor watch, W-004 lamp store reachable with signal lens.
## D-030: the offshore tower stays dark and sealed; every warm payoff element
## built here (mount light, tide glow, ending signal beam) is harbor-side only.

const PALETTE := {
	"storm_ink": Color("#17232D"),
	"wet_slate": Color("#344956"),
	"paper_fog": Color("#D9D3C4"),
	"brass": Color("#A77A3A"),
	"signal_amber": Color("#F2B84B"),
	"warning_coral": Color("#D9685F"),
}

const PACK_3D_RELATIVE := "../assets/concepts/pack-3d"

# Presentation budget (Web/Compatibility renderer): five preallocated CPU burst
# emitters, at most 18 live particles per beat, no new VFX-only lights (the
# ending signal beam, waterline mist, commit halo, and verdict-ritual meshes
# are unshaded static meshes, not lights), and instanced repetition for dock
# dressing. These are starting caps, not a measured frame-performance claim.
const PUBLIC_SAFE_ARG := "--public-safe"
const PRESENTATION_VFX_BUDGET := {
	"target_fps": 60,
	"pooled_burst_emitters": 5,
	"max_simultaneous_burst_particles": 18,
	"max_simultaneous_burst_draw_calls": 1,
	"web_continuous_rain_particles": 360,
	"desktop_continuous_rain_particles": 480,
	"waterline_mist_quads": 3,
	"verdict_ritual_meshes": 2,
	"vfx_only_lights": 0,
	"blur_passes": 0,
	"raymarch_samples": 0,
}


static func load_pack_texture(file_name: String) -> Texture2D:
	# HARD BOUNDARY: optional presentation-candidate textures are never loaded by
	# Web exports or public-safe runs. The primary/public surface stays procedural
	# and fully playable without generated PNGs.
	if OS.has_feature("web") or PUBLIC_SAFE_ARG in OS.get_cmdline_user_args():
		return null
	var pack_dir := ProjectSettings.globalize_path("res://").path_join(PACK_3D_RELATIVE)
	var path := pack_dir.path_join(file_name)
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(path)
	if image == null:
		return null
	return ImageTexture.create_from_image(image)


static func load_concept_texture(file_name: String) -> Texture2D:
	# Same boundary as load_pack_texture, for the reviewed SL-C0x concept set one
	# directory up: start-gate key art and tutorial illustrations. Absent bytes
	# simply leave the image slot hidden.
	if OS.has_feature("web") or PUBLIC_SAFE_ARG in OS.get_cmdline_user_args():
		return null
	var concepts_dir := ProjectSettings.globalize_path("res://").path_join("../assets/concepts")
	var path := concepts_dir.path_join(file_name)
	if not FileAccess.file_exists(path):
		return null
	var image := Image.load_from_file(path)
	if image == null:
		return null
	return ImageTexture.create_from_image(image)


static func load_curated_ui_texture(file_name: String) -> Texture2D:
	# D-034/D-035 curated UI art lane (assets/ui/, user-reviewed Higgsfield pack).
	# Unlike the candidate pack/concept lanes above, these bytes are runtime- and
	# Web-eligible: they live inside res:// and ship in the PCK. Contract: when a
	# curated file is absent the caller keeps its procedural look — return null,
	# never error.
	var path := "res://assets/ui/".path_join(file_name)
	if not ResourceLoader.exists(path, "Texture2D"):
		return null
	return load(path) as Texture2D


static func load_model_scene(file_name: String) -> Node3D:
	# Runtime load of the Blender-authored GLB prop kit (assets/models/). Uses
	# GLTFDocument so no editor import pass is required; returns null when the
	# kit is absent, in which case the procedural geometry below remains the
	# complete primary build.
	var path := ProjectSettings.globalize_path("res://assets/models").path_join(file_name)
	if not FileAccess.file_exists(path):
		return null
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	if document.append_from_file(path, state) != OK:
		return null
	return document.generate_scene(state) as Node3D


static func attach_model(
	parent: Node3D,
	file_name: String,
	position: Vector3,
	scale: float = 1.0,
	y_rotation_deg: float = 0.0
) -> Node3D:
	var model := load_model_scene(file_name)
	if model == null:
		return null
	model.position = position
	model.scale = Vector3.ONE * scale
	model.rotation_degrees.y = y_rotation_deg
	parent.add_child(model)
	return model


static func add_box_collider(parent: Node3D, size: Vector3, position: Vector3) -> void:
	var body := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	body.position = position
	body.add_child(shape)
	parent.add_child(body)


static func flat_material(color: Color, roughness: float = 0.85) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	return material


static func emissive_material(
	color: Color, energy: float = 1.0, alpha: float = 1.0
) -> StandardMaterial3D:
	var material := flat_material(Color(color, alpha), 0.35)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = energy
	if alpha < 1.0:
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return material


static func textured_material(file_name: String, fallback: Color, uv_scale: Vector3 = Vector3.ONE) -> StandardMaterial3D:
	var material := flat_material(fallback)
	var texture := load_pack_texture(file_name)
	if texture != null:
		material.albedo_texture = texture
		material.albedo_color = Color(0.82, 0.82, 0.82)
		material.uv1_scale = uv_scale
	return material


static func curated_material(file_name: String, fallback: Color, uv_scale: Vector3 = Vector3.ONE) -> StandardMaterial3D:
	# D-036 curated world-texture lane: reviewed grain PNGs from assets/ui/ are
	# runtime- and Web-eligible (unlike the pack/concept candidate lanes). The
	# texture is grain, not a new color — albedo modulation keeps the fallback
	# palette hue reading through it. Contract: when the curated file is absent
	# (TexturePack may still be generating), this IS flat_material(fallback);
	# the world must look correct on pure fallback.
	var material := flat_material(fallback)
	var texture := load_curated_ui_texture(file_name)
	if texture != null:
		material.albedo_texture = texture
		# Modulate toward the palette color so grain never overrides hue.
		material.albedo_color = fallback.lightened(0.35)
		material.uv1_scale = uv_scale
	return material


static func brass_fitting_material() -> StandardMaterial3D:
	# Shared oxidized-brass grain for fittings and lamp housings: curated lane
	# first (Web-eligible), desktop candidate pack second, flat brass last.
	var material := curated_material("ui-tex-oxidized-brass.png", PALETTE.brass)
	if material.albedo_texture == null:
		material = textured_material("SL3D-T02-oxidized-brass.png", PALETTE.brass)
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


static func add_multimesh_boxes(
	parent: Node3D,
	name_text: String,
	size: Vector3,
	transforms: Array[Transform3D],
	material: Material
) -> MultiMeshInstance3D:
	# Decorative repetition stays in one instanced draw surface and has no physics.
	var box := BoxMesh.new()
	box.size = size
	box.material = material
	var instances := MultiMesh.new()
	instances.transform_format = MultiMesh.TRANSFORM_3D
	instances.mesh = box
	instances.instance_count = transforms.size()
	for index in transforms.size():
		instances.set_instance_transform(index, transforms[index])
	var multimesh := MultiMeshInstance3D.new()
	multimesh.name = name_text
	multimesh.multimesh = instances
	parent.add_child(multimesh)
	return multimesh


static func build(root: Node3D) -> Dictionary:
	# Returns named handles the director and root controller use for beats and
	# state-snapshot synchronization.
	var handles := {}
	var world := Node3D.new()
	world.name = "HarborWorld"
	root.add_child(world)

	handles["environment"] = _build_environment(root)
	_build_sea(world)
	_build_harbor_backdrop(world)
	_build_dock(world)
	_build_lamp_store(world)
	handles["lighthouse_light"] = _build_lighthouse(world)
	handles["rain"] = _build_rain(world)
	handles["mira"] = _build_mira(world)
	handles["lens_prop"] = _build_lens_prop(world)
	handles["lamp_mount"] = _build_lamp_mount(world)
	handles["tide_marks"] = _build_tide_marks(world)
	handles["buoy_light"] = _build_buoy(world)
	_build_waterline_mist(world)
	_build_commit_halo(world)
	_build_verdict_ritual_pool(world)
	var beat_vfx := _build_presentation_vfx(world)
	for key in beat_vfx:
		handles[key] = beat_vfx[key]
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
	# The director drives the tension-staged weather arc (sky grade, ambient
	# level, moonlight, offshore lightning) through these presentation handles.
	world_environment.set_meta("storm_moon", moon)
	world_environment.set_meta("sky_material", sky_material)
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
// Wave motion is phase-driven by the director so storm-stage speed changes
// stay continuous (no TIME snap) and reduced motion can hold the sea still.
uniform float wave_phase = 0.0;
varying float crest;
void vertex() {
	vec3 world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float wave = sin(world_pos.x * 0.11 + wave_phase * 0.9) * 0.5
		+ sin(world_pos.z * 0.07 - wave_phase * 0.6) * 0.5
		+ sin((world_pos.x + world_pos.z) * 0.05 + wave_phase * 0.35) * 0.6;
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


static func _build_harbor_backdrop(world: Node3D) -> void:
	# Broad, low-detail masses frame the playable quay and keep the lighthouse as
	# the only tall distant silhouette. Repeated forms are instanced for Web.
	var silhouette_material := flat_material(PALETTE.storm_ink.darkened(0.16))
	var breakwater_transforms: Array[Transform3D] = []
	for index in range(11):
		var height := 1.3 + float((index * 7) % 4) * 0.28
		var basis := Basis().scaled(Vector3(1.0, height, 1.0))
		breakwater_transforms.append(
			Transform3D(basis, Vector3(-17.5 + index * 3.5, -0.55, 24.0 + absf(index - 5) * 0.35))
		)
	add_multimesh_boxes(
		world,
		"BreakwaterSilhouette",
		Vector3(3.3, 1.1, 3.6),
		breakwater_transforms,
		silhouette_material
	)

	# Two compact working-harbor silhouettes enrich the mid-ground without adding
	# interactable-looking detail or obscuring the main dock path.
	var hull_material := flat_material(PALETTE.wet_slate.darkened(0.22))
	var skiff := Node3D.new()
	skiff.name = "MooredSkiff"
	skiff.position = Vector3(12.0, -0.35, 10.0)
	skiff.rotation_degrees.y = -8.0
	world.add_child(skiff)
	add_box(skiff, Vector3(5.2, 0.55, 1.7), Vector3.ZERO, hull_material, false)
	add_box(skiff, Vector3(3.7, 0.15, 1.25), Vector3(0.0, 0.37, 0.0), flat_material(PALETTE.storm_ink), false)
	add_box(skiff, Vector3(0.08, 4.8, 0.08), Vector3(0.2, 2.65, 0.0), hull_material, false)
	# Storm-furled canvas: a rolled sail lashed along the boom plus a small deck
	# tarp. Curated sail-canvas grain (D-036) when present, flat weathered
	# paper_fog otherwise — silhouette dressing only, no collision.
	var canvas_material := curated_material(
		"ui-tex-sail-canvas.png", PALETTE.paper_fog.darkened(0.35), Vector3(2.0, 1.0, 1.0)
	)
	var furled_sail := add_box(
		skiff, Vector3(2.6, 0.26, 0.30), Vector3(1.35, 1.05, 0.0), canvas_material, false
	)
	furled_sail.rotation_degrees.z = -3.5
	add_box(skiff, Vector3(1.15, 0.09, 0.95), Vector3(-1.35, 0.47, 0.15), canvas_material, false)

	var shed := Node3D.new()
	shed.name = "HarborShedSilhouette"
	shed.position = Vector3(12.5, 0.0, -2.5)
	world.add_child(shed)
	add_box(shed, Vector3(7.0, 3.4, 5.0), Vector3(0.0, 1.7, 0.0), silhouette_material, false)
	var roof := add_box(
		shed,
		Vector3(7.7, 0.3, 5.7),
		Vector3(0.0, 3.55, 0.0),
		flat_material(PALETTE.storm_ink.darkened(0.3)),
		false
	)
	roof.rotation_degrees.z = -4.0


static func _build_dock(world: Node3D) -> void:
	var dock := Node3D.new()
	dock.name = "HarborDock"
	world.add_child(dock)
	# Curated wet-plank grain (D-036, Web-eligible) wins when present; otherwise
	# the desktop-only candidate pack, then flat wet_slate — never a hard need.
	var plank_material := curated_material(
		"ui-tex-wet-planks.png", PALETTE.wet_slate, Vector3(6.0, 6.0, 1.0)
	)
	if plank_material.albedo_texture == null:
		plank_material = textured_material(
			"SL3D-T01-wet-slate-planks.png", PALETTE.wet_slate, Vector3(6.0, 6.0, 1.0)
		)
	add_box(dock, Vector3(18.0, 0.5, 20.0), Vector3(0.0, -0.25, 5.0), plank_material)
	# One instanced seam surface gives the wet quay scale and direction without a
	# texture dependency or one draw call per plank.
	var seam_transforms: Array[Transform3D] = []
	for index in range(17):
		seam_transforms.append(
			Transform3D(Basis(), Vector3(0.0, 0.015, -4.4 + index * 1.18))
		)
	add_multimesh_boxes(
		dock,
		"DockPlankSeams",
		Vector3(17.7, 0.025, 0.035),
		seam_transforms,
		flat_material(PALETTE.storm_ink.lightened(0.02)),
	)
	# Brass studs establish a low-frequency route from spawn toward the dock end.
	var route_transforms: Array[Transform3D] = []
	for index in range(8):
		var side := -1.0 if index % 2 == 0 else 1.0
		route_transforms.append(
			Transform3D(Basis(), Vector3(side * 1.45, 0.045, 0.4 + index * 1.75))
		)
	add_multimesh_boxes(
		dock,
		"BrassRouteStuds",
		Vector3(0.16, 0.07, 0.16),
		route_transforms,
		emissive_material(PALETTE.brass, 0.45),
	)
	var piling_material := flat_material(PALETTE.storm_ink.lightened(0.06))
	for x in [-8.0, -4.0, 0.0, 4.0, 8.0]:
		add_cylinder(dock, 0.28, 2.4, Vector3(x, -1.1, 14.8), piling_material, false)
	var rail_material := flat_material(PALETTE.storm_ink.lightened(0.12))
	add_box(dock, Vector3(18.0, 0.12, 0.12), Vector3(0.0, 0.9, 15.0), rail_material, false)
	for x in [-8.5, -4.25, 0.0, 4.25, 8.5]:
		add_box(dock, Vector3(0.12, 1.0, 0.12), Vector3(x, 0.4, 15.0), rail_material, false)
	# Fire-scarred but saved crates: W-001 dock fire averted.
	var crate_material := flat_material(PALETTE.wet_slate.lightened(0.08))
	var crate_specs: Array = [
		{"base": Vector3(-7.0, 0.0, 10.5), "scale": 1.2, "rot": 12.0},
		{"base": Vector3(-5.8, 0.0, 11.2), "scale": 0.9, "rot": -9.0},
		{"base": Vector3(7.2, 0.0, 3.0), "scale": 1.0, "rot": 41.0},
	]
	for spec in crate_specs:
		var crate_size: float = spec["scale"]
		var center: Vector3 = spec["base"] + Vector3(0.0, crate_size * 0.55, 0.0)
		if attach_model(dock, "dock_crate.glb", spec["base"], crate_size, spec["rot"]) != null:
			add_box_collider(dock, Vector3.ONE * crate_size * 1.1, center)
		else:
			add_box(dock, Vector3.ONE * crate_size * 1.1, center, crate_material)


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
	# The west-side recovery bench aligns the visible lens with its existing
	# interaction volume at world x=-11, while keeping it reachable from the quay.
	add_box(store, Vector3(4.0, 0.22, 2.2), Vector3(-4.8, 0.55, 0.0), roof_material, false)
	add_box(store, Vector3(0.18, 1.2, 0.18), Vector3(-6.3, -0.05, -0.7), wall_material, false)
	add_box(store, Vector3(0.18, 1.2, 0.18), Vector3(-3.3, -0.05, 0.7), wall_material, false)
	var sign := Label3D.new()
	sign.name = "LampStoreSign"
	sign.text = "LAMP & SIGNAL\n등불 · 신호"
	sign.font_size = 34
	sign.pixel_size = 0.008
	sign.modulate = PALETTE.paper_fog
	sign.outline_modulate = PALETTE.storm_ink
	sign.outline_size = 10
	sign.position = Vector3(0.0, 2.45, 2.67)
	store.add_child(sign)
	# Interior counter and shelf, brass instruments.
	var brass_material := brass_fitting_material()
	add_box(store, Vector3(2.4, 1.0, 0.8), Vector3(-1.2, 0.5, -1.6), flat_material(PALETTE.wet_slate))
	add_box(store, Vector3(0.5, 0.3, 0.5), Vector3(-1.2, 1.15, -1.6), brass_material, false)
	var lamp := OmniLight3D.new()
	lamp.name = "StoreLamp"
	lamp.light_color = PALETTE.paper_fog
	lamp.light_energy = 1.1
	lamp.omni_range = 7.0
	lamp.position = Vector3(0.0, 2.4, 0.0)
	store.add_child(lamp)
	# Harbor-life micro-motion: the director flickers this existing lamp gently;
	# no new light is created for the effect.
	world.set_meta("store_lamp", lamp)


static func _build_lighthouse(world: Node3D) -> OmniLight3D:
	# W-002: offshore, dark, observed but never entered in this slice.
	var island := Node3D.new()
	island.name = "OffshoreLighthouse"
	island.position = Vector3(6.0, 0.0, 62.0)
	world.add_child(island)
	if attach_model(island, "lighthouse_tower.glb", Vector3(0.0, 0.4, 0.0)) == null:
		var rock_material := flat_material(PALETTE.storm_ink.lightened(0.04))
		add_cylinder(island, 6.0, 3.0, Vector3(0.0, -0.5, 0.0), rock_material, false)
		var tower_material := flat_material(PALETTE.storm_ink.lightened(0.16))
		add_cylinder(island, 1.6, 14.0, Vector3(0.0, 7.0, 0.0), tower_material, false)
		# Sparse banding and balcony geometry preserve the tower read in fog without
		# implying that the sealed beacon has lit.
		for y in [3.2, 7.1, 11.0]:
			add_cylinder(island, 1.72, 0.18, Vector3(0.0, y, 0.0), rock_material, false)
		add_cylinder(island, 2.35, 0.16, Vector3(0.0, 14.05, 0.0), rock_material, false)
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
	# Compatibility/Web keeps the continuous layer below the conservative 500-CPU
	# prompt-to-profile threshold; desktop remains modest but must still be measured.
	rain.amount = (
		PRESENTATION_VFX_BUDGET.web_continuous_rain_particles
		if OS.has_feature("web")
		else PRESENTATION_VFX_BUDGET.desktop_continuous_rain_particles
	)
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
	world.set_meta("mira_lantern", lantern_glow)
	mira.look_at_from_position(mira.position, Vector3(6.0, 0.0, 62.0), Vector3.UP)
	mira.rotation.x = 0.0
	return mira


static func _build_lens_prop(world: Node3D) -> Node3D:
	# W-004: the replacement signal lens rests in the reachable lamp store.
	var lens := Node3D.new()
	lens.name = "SignalLensProp"
	lens.position = Vector3(-11.0, 0.0, 1.0)
	world.add_child(lens)
	var pedestal_material := flat_material(PALETTE.wet_slate)
	add_box(lens, Vector3(0.7, 0.9, 0.7), Vector3(0.0, 0.45, 0.0), pedestal_material, false)
	if attach_model(lens, "signal_lens.glb", Vector3(0.0, 1.25, 0.0), 1.35) == null:
		var brass_material := brass_fitting_material()
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
	if attach_model(mount, "lamp_post.glb", Vector3.ZERO) != null:
		add_box_collider(mount, Vector3(0.5, 3.4, 0.5), Vector3(0.0, 1.7, 0.0))
	else:
		var post_material := flat_material(PALETTE.storm_ink.lightened(0.1))
		add_cylinder(mount, 0.12, 3.4, Vector3(0.0, 1.7, 0.0), post_material)
		var brass_material := brass_fitting_material()
		add_box(mount, Vector3(0.6, 0.6, 0.6), Vector3(0.0, 3.6, 0.0), brass_material, false)
	var mount_light := OmniLight3D.new()
	mount_light.name = "MountLight"
	mount_light.light_color = PALETTE.signal_amber
	mount_light.light_energy = 0.0
	mount_light.omni_range = 14.0
	mount_light.position = Vector3(0.0, 3.6, 0.0)
	mount.add_child(mount_light)
	# P-B06 ending payoff: the HARBOR-SIDE signal lamp sweeps a soft volumetric-
	# looking beam toward the tide-marks channel. Unshaded low-alpha mesh, not a
	# light (D-030: the offshore lighthouse never lights; the payoff is here).
	var beam_pivot := Node3D.new()
	beam_pivot.name = "SignalBeamPivot"
	beam_pivot.position = Vector3(0.0, 3.6, 0.0)
	mount.add_child(beam_pivot)
	var beam := MeshInstance3D.new()
	beam.name = "SignalBeam"
	var beam_mesh := BoxMesh.new()
	beam_mesh.size = Vector3(0.34, 0.10, 24.0)
	beam.mesh = beam_mesh
	var beam_material := emissive_material(PALETTE.signal_amber, 1.35, 0.0)
	beam_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	beam.material_override = beam_material
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	beam.position = Vector3(0.0, 0.0, -12.0)
	beam.visible = false
	beam_pivot.add_child(beam)
	beam_pivot.set_meta("beam_mesh", beam)
	beam_pivot.set_meta("beam_material", beam_material)
	world.set_meta("signal_beam_pivot", beam_pivot)
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


static func _build_presentation_vfx(world: Node3D) -> Dictionary:
	# HARD BOUNDARY: these nodes communicate authored presentation beats only.
	# They are pooled at scene construction, have fixed seeds/timings, and never
	# authorize actions, inspect hidden oracle labels, or write canonical state.
	var root := Node3D.new()
	root.name = "PresentationVFXPool"
	world.add_child(root)
	var vfx := {
		"arrival_mist": _make_burst(
			root,
			"ArrivalMist",
			Vector3(0.0, 0.65, 7.0),
			PALETTE.paper_fog.darkened(0.22),
			18,
			3.4,
			Vector3(0.45, 0.08, 0.35),
			38.0,
			0.55,
			0.12,
			1101,
		),
		"lens_glints": _make_burst(
			root,
			"LensGlints",
			Vector3(-11.0, 1.25, 1.0),
			PALETTE.paper_fog,
			12,
			0.75,
			Vector3(0.0, 1.0, 0.0),
			42.0,
			1.2,
			0.045,
			2202,
		),
		"mount_sparks": _make_burst(
			root,
			"MountSparks",
			Vector3(7.0, 3.65, 13.5),
			PALETTE.signal_amber,
			16,
			0.62,
			Vector3(0.0, 1.0, 0.0),
			30.0,
			2.1,
			0.04,
			3303,
		),
		"refusal_motes": _make_burst(
			root,
			"RefusalMotes",
			Vector3.ZERO,
			PALETTE.warning_coral,
			10,
			0.48,
			Vector3(0.0, 1.0, 0.0),
			55.0,
			0.8,
			0.035,
			4404,
		),
		"tide_motes": _make_burst(
			root,
			"TideMotes",
			Vector3(-8.5, 0.5, 16.2),
			PALETTE.signal_amber,
			14,
			1.25,
			Vector3(-0.2, 0.8, 0.45),
			28.0,
			0.95,
			0.045,
			5505,
		),
	}
	(vfx["mount_sparks"] as CPUParticles3D).gravity = Vector3(0.0, -4.5, 0.0)
	(vfx["refusal_motes"] as CPUParticles3D).gravity = Vector3(0.0, 0.2, 0.0)
	(vfx["tide_motes"] as CPUParticles3D).gravity = Vector3(0.0, -0.25, 0.0)
	return vfx


static func _make_burst(
	parent: Node3D,
	name_text: String,
	position: Vector3,
	color: Color,
	amount: int,
	lifetime: float,
	direction: Vector3,
	spread: float,
	velocity: float,
	particle_size: float,
	seed_value: int,
) -> CPUParticles3D:
	var particles := CPUParticles3D.new()
	particles.name = name_text
	particles.amount = amount
	particles.lifetime = lifetime
	particles.one_shot = true
	particles.explosiveness = 0.92
	particles.emitting = false
	particles.direction = direction.normalized()
	particles.spread = spread
	particles.initial_velocity_min = velocity * 0.72
	particles.initial_velocity_max = velocity
	particles.scale_amount_min = 0.55
	particles.scale_amount_max = 1.0
	particles.color = color
	particles.fixed_fps = 30
	particles.fract_delta = false
	particles.seed = seed_value
	particles.position = position
	particles.visibility_aabb = AABB(Vector3(-5.0, -5.0, -5.0), Vector3(10.0, 10.0, 10.0))

	var mote := SphereMesh.new()
	mote.radius = particle_size
	mote.height = particle_size * 2.0
	mote.radial_segments = 6
	mote.rings = 3
	mote.material = emissive_material(color, 1.1, 0.78)
	particles.mesh = mote
	parent.add_child(particles)
	return particles


static func _build_buoy(world: Node3D) -> OmniLight3D:
	var buoy := Node3D.new()
	buoy.name = "ChannelBuoy"
	buoy.position = Vector3(-14.0, -0.4, 34.0)
	world.add_child(buoy)
	if attach_model(buoy, "channel_buoy.glb", Vector3(0.0, -0.45, 0.0)) == null:
		add_cylinder(buoy, 0.5, 1.2, Vector3.ZERO, flat_material(PALETTE.warning_coral.darkened(0.25)), false)
	var light := OmniLight3D.new()
	light.name = "BuoyLight"
	light.light_color = PALETTE.warning_coral
	light.light_energy = 0.6
	light.omni_range = 8.0
	light.position = Vector3(0.0, 1.0, 0.0)
	buoy.add_child(light)
	world.set_meta("buoy_root", buoy)
	return light


static func _build_waterline_mist(world: Node3D) -> void:
	# Harbor-life dressing: three large low-alpha unshaded sheets drift slowly
	# near the waterline under director sine transforms. No particles, no
	# physics, no lights — three static draw surfaces within the budget's
	# `waterline_mist_quads` cap. Reduced motion holds them at rest.
	var sheets: Array = []
	var sheet_specs := [
		{"pos": Vector3(-6.0, 0.18, 20.0), "size": Vector2(26.0, 9.0), "alpha": 0.085},
		{"pos": Vector3(10.0, 0.05, 26.0), "size": Vector2(20.0, 7.0), "alpha": 0.065},
		{"pos": Vector3(-16.0, 0.30, 30.0), "size": Vector2(16.0, 6.0), "alpha": 0.075},
	]
	for index in sheet_specs.size():
		var spec: Dictionary = sheet_specs[index]
		var sheet := MeshInstance3D.new()
		sheet.name = "WaterlineMist%d" % index
		var quad := PlaneMesh.new()
		quad.size = spec["size"]
		sheet.mesh = quad
		var material := StandardMaterial3D.new()
		material.albedo_color = Color(PALETTE.paper_fog.darkened(0.30), spec["alpha"])
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.cull_mode = BaseMaterial3D.CULL_DISABLED
		sheet.material_override = material
		sheet.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		sheet.position = spec["pos"]
		world.add_child(sheet)
		sheet.set_meta("rest_position", spec["pos"])
		sheets.append(sheet)
	world.set_meta("waterline_mist_sheets", sheets)


static func _build_commit_halo(world: Node3D) -> void:
	# P-B03/P-B05 punch-up: one pooled billboard quad the director re-anchors to
	# whichever authorized light just committed, scale/fade tweened ≤0.6 s.
	# Unshaded mesh, hidden at rest — zero standing cost, no new light.
	var halo := MeshInstance3D.new()
	halo.name = "CommitHalo"
	var quad := QuadMesh.new()
	quad.size = Vector2(1.6, 1.6)
	halo.mesh = quad
	var material := emissive_material(PALETTE.signal_amber, 1.2, 0.0)
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	material.no_depth_test = true
	halo.material_override = material
	halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	halo.visible = false
	world.add_child(halo)
	halo.set_meta("halo_material", material)
	world.set_meta("commit_halo", halo)


static func _build_verdict_ritual_pool(world: Node3D) -> void:
	# Validate→repair→commit ritual props (P-B03/P-B04 sub-beats): two pooled
	# unshaded meshes the director re-anchors to the acting interactable —
	#   InspectionRing  flat torus, amber "weighing" sweep before the verdict;
	#   SealLine        thin horizontal bar, the refusal "seal" shutter stroke.
	# Both hidden at rest — zero standing cost, no new lights (budget:
	# verdict_ritual_meshes = 2).
	var ring := MeshInstance3D.new()
	ring.name = "InspectionRing"
	var ring_mesh := TorusMesh.new()
	ring_mesh.inner_radius = 0.46
	ring_mesh.outer_radius = 0.54
	ring_mesh.rings = 24
	ring_mesh.ring_segments = 6
	ring.mesh = ring_mesh
	var ring_material := emissive_material(PALETTE.signal_amber, 1.0, 0.0)
	ring_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	ring.material_override = ring_material
	ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	ring.visible = false
	world.add_child(ring)
	ring.set_meta("ring_material", ring_material)
	world.set_meta("inspection_ring", ring)

	var seal_line := MeshInstance3D.new()
	seal_line.name = "SealLine"
	var bar := BoxMesh.new()
	bar.size = Vector3(1.5, 0.045, 0.045)
	seal_line.mesh = bar
	var seal_material := emissive_material(PALETTE.warning_coral, 1.0, 0.0)
	seal_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	seal_line.material_override = seal_material
	seal_line.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	seal_line.visible = false
	world.add_child(seal_line)
	seal_line.set_meta("seal_material", seal_material)
	world.set_meta("seal_line", seal_line)
