extends Node

const VIEWPORT_SIZE := Vector2i(1280, 720)
const CAPTURE_SPECS := [
	{
		"capture_id": "sl-rc-001-arrival",
		"filename": "sl-rc-001-arrival.png",
		"event_id": "evt-000-observe",
		"beat": "arrival_observation",
		"view_mode": "participant-primary",
		"participant_visible": true,
		"title": "ARRIVAL / DARK LIGHTHOUSE",
		"narrative": "The lighthouse is dark. The lamp store remains reachable.",
		"status": "OBSERVATION",
		"accent": Color("58c7d9"),
	},
	{
		"capture_id": "sl-rc-002-rejected-secret",
		"filename": "sl-rc-002-rejected-secret.png",
		"event_id": "evt-002-fallback-secret",
		"beat": "forbidden_disclosure_rejected",
		"view_mode": "experiment-inspector",
		"participant_visible": false,
		"title": "HARD GATE / DISCLOSURE REJECTED",
		"narrative": "Captain Mira deflects the request. Canonical state remains unchanged.",
		"status": "FALLBACK · NO MUTATION",
		"accent": Color("ff6b73"),
	},
	{
		"capture_id": "sl-rc-003-authorized-hint",
		"filename": "sl-rc-003-authorized-hint.png",
		"event_id": "evt-005-commit-hint",
		"beat": "authorized_hint_committed",
		"view_mode": "experiment-inspector",
		"participant_visible": false,
		"title": "AUTHORIZED HINT / COMMIT",
		"narrative": "The restored lens authorizes Mira's tide-marks hint.",
		"status": "COMMIT · REPLAY-BOUND",
		"accent": Color("f7c95c"),
	},
]

var viewport: SubViewport
var stage: Control
var title_label: Label
var status_label: Label
var narrative_label: Label
var event_label: Label
var state_label: Label
var validation_label: Label
var progress_label: Label
var beam: Polygon2D
var signal_core: Polygon2D


func _ready() -> void:
	call_deferred("_execute")


func _execute() -> void:
	var options := _parse_options(OS.get_cmdline_user_args())
	if DisplayServer.get_name() == "headless":
		_fail("render capture requires a non-headless display server")
		return
	var events_path: String = options.get("events", "")
	var summary_path: String = options.get("summary", "")
	var output_path: String = options.get("output", "")
	var evidence_set_id: String = options.get("evidence-set-id", "")
	if events_path.is_empty() or summary_path.is_empty() or output_path.is_empty():
		_fail("missing --events, --summary, or --output")
		return
	if evidence_set_id.is_empty():
		_fail("missing --evidence-set-id")
		return
	if DirAccess.make_dir_recursive_absolute(output_path) != OK:
		_fail("cannot create capture output: %s" % output_path)
		return

	var events := _read_jsonl(events_path)
	var summary := _read_json(summary_path)
	if events.is_empty() or summary.is_empty():
		return
	var event_by_id := {}
	for event in events:
		event_by_id[str(event["event_id"])] = event
	for spec in CAPTURE_SPECS:
		if not event_by_id.has(spec["event_id"]):
			_fail("source event missing for capture: %s" % spec["event_id"])
			return

	_build_stage()
	var capture_rows: Array = []
	for spec in CAPTURE_SPECS:
		var event: Dictionary = event_by_id[spec["event_id"]]
		_apply_capture(spec, event, summary)
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var image := viewport.get_texture().get_image()
		if image.is_empty() or image.get_width() != VIEWPORT_SIZE.x or image.get_height() != VIEWPORT_SIZE.y:
			_fail("invalid captured viewport for %s" % spec["capture_id"])
			return
		var file_path := output_path.path_join(spec["filename"])
		if image.save_png(file_path) != OK:
			_fail("cannot save PNG: %s" % file_path)
			return
		var validation_codes: Array = event["validation"]["codes"]
		capture_rows.append({
			"capture_id": spec["capture_id"],
			"file": spec["filename"],
			"beat": spec["beat"],
			"event_id": event["event_id"],
			"sequence": int(event["sequence"]),
			"delivery_index": int(event["delivery_index"]),
			"turn": int(event["turn"]),
			"world_state_hash_before": event["world_state_hash_before"],
			"world_state_hash": event["world_state_hash"],
			"validation_status": event["validation"]["status"],
			"validation_codes": validation_codes,
			"view_mode": spec["view_mode"],
			"participant_visible": spec["participant_visible"],
			"generated_assets_in_frame": false,
			"width": image.get_width(),
			"height": image.get_height(),
			"mime_type": "image/png",
			"bytes": FileAccess.get_file_as_bytes(file_path).size(),
			"sha256": FileAccess.get_sha256(file_path),
		})

	var render_manifest := {
		"schema_version": "1.0.0",
		"status": "OBSERVED_GODOT_RENDER_REPLAY",
		"evidence_set_id": evidence_set_id,
		"fixture_id": summary["fixture_id"],
		"scenario_id": summary["scenario_id"],
		"run_id": summary["run_id"],
		"episode_id": summary["episode_id"],
		"seed": int(summary["seed"]),
		"input_mode": "scripted_fixture_trace_replay",
		"track": "primary-structured-state-text",
		"capture_method": "subviewport-frame-post-draw-v1",
		"captured_at_utc": Time.get_datetime_string_from_system(true, true),
		"engine": {
			"name": "Godot",
			"version": str(Engine.get_version_info()["string"]),
			"headless": false,
			"display_server": DisplayServer.get_name(),
			"rendering_method": RenderingServer.get_current_rendering_method(),
			"rendering_device": RenderingServer.get_video_adapter_name(),
		},
		"viewport": {"width": VIEWPORT_SIZE.x, "height": VIEWPORT_SIZE.y},
		"source": {
			"events_jsonl": "../sealed-lighthouse-canonical-v1/events.jsonl",
			"events_sha256": FileAccess.get_sha256(events_path),
			"summary_json": "../sealed-lighthouse-canonical-v1/summary.json",
			"summary_sha256": FileAccess.get_sha256(summary_path),
			"capture_scene_sha256": _resource_sha256("res://scenes/evidence_capture.tscn"),
			"capture_runner_sha256": _resource_sha256("res://scripts/evidence_capture_runner.gd"),
			"project_sha256": _resource_sha256("res://project.godot"),
		},
		"claim_scope": "authored-engine-render-state-correspondence-only",
		"limitations": [
			"No live Python authorization transport or neural model inference was used.",
			"This scripted replay is not participant interaction, usability, immersion, G4, or G6 evidence.",
			"Pixel hashes identify this packet only and are not cross-device visual golden values.",
		],
		"captures": capture_rows,
	}
	var manifest_path := output_path.path_join("capture-manifest.json")
	if not _write_json(manifest_path, render_manifest):
		return
	print(JSON.stringify({
		"capture_manifest": manifest_path,
		"capture_count": capture_rows.size(),
		"display_server": DisplayServer.get_name(),
	}))
	get_tree().quit(0)


func _build_stage() -> void:
	viewport = SubViewport.new()
	viewport.name = "EvidenceViewport"
	viewport.size = VIEWPORT_SIZE
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.transparent_bg = false
	add_child(viewport)

	stage = Control.new()
	stage.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	stage.mouse_filter = Control.MOUSE_FILTER_IGNORE
	viewport.add_child(stage)

	_add_rect(stage, Rect2(0, 0, 1280, 720), Color("071018"))
	_add_rect(stage, Rect2(0, 0, 1280, 72), Color("101f2c"))
	_add_rect(stage, Rect2(38, 102, 760, 478), Color("0b2634"))
	_add_rect(stage, Rect2(828, 102, 414, 478), Color("101b27"))
	_add_rect(stage, Rect2(38, 604, 1204, 78), Color("132331"))

	# Authored vector harbor/lighthouse silhouette. Primary-track capture contains no generated art.
	_add_rect(stage, Rect2(38, 420, 760, 160), Color("0b3549"))
	_add_rect(stage, Rect2(220, 225, 124, 282), Color("d9e2df"))
	_add_rect(stage, Rect2(194, 202, 176, 38), Color("253d48"))
	_add_rect(stage, Rect2(248, 152, 68, 54), Color("f7c95c"))
	_add_rect(stage, Rect2(232, 507, 100, 73), Color("09151d"))
	_add_circle(stage, Vector2(282, 178), 17.0, Color("fff2a9"))
	beam = _add_polygon(
		stage,
		PackedVector2Array([Vector2(315, 161), Vector2(735, 108), Vector2(735, 270), Vector2(315, 194)]),
		Color(0.97, 0.79, 0.36, 0.2)
	)
	signal_core = _add_polygon(
		stage,
		PackedVector2Array([Vector2(282, 142), Vector2(300, 178), Vector2(282, 214), Vector2(264, 178)]),
		Color("58c7d9")
	)

	_add_label(stage, Rect2(40, 22, 350, 34), "TRACE-RPG / ENGINE EVIDENCE VIEW", 17, Color("9fb3c4"))
	title_label = _add_label(stage, Rect2(420, 20, 820, 38), "", 22, Color.WHITE, HORIZONTAL_ALIGNMENT_RIGHT)
	title_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	status_label = _add_label(stage, Rect2(860, 126, 350, 44), "", 20, Color("58c7d9"))
	event_label = _add_label(stage, Rect2(860, 190, 350, 335), "", 16, Color("d7e1e9"))
	event_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	state_label = _add_label(stage, Rect2(0, 0, 0, 0), "", 1, Color.TRANSPARENT)
	validation_label = _add_label(stage, Rect2(0, 0, 0, 0), "", 1, Color.TRANSPARENT)
	narrative_label = _add_label(stage, Rect2(66, 616, 820, 52), "", 20, Color("f3f6f7"))
	progress_label = _add_label(stage, Rect2(900, 616, 310, 52), "", 16, Color("8da6b8"), HORIZONTAL_ALIGNMENT_RIGHT)


func _apply_capture(spec: Dictionary, event: Dictionary, summary: Dictionary) -> void:
	title_label.text = spec["title"]
	status_label.text = spec["status"]
	status_label.modulate = Color.WHITE
	status_label.add_theme_color_override("font_color", spec["accent"])
	narrative_label.text = spec["narrative"]
	var codes: Array = event["validation"]["codes"]
	event_label.text = (
		"EVENT\n%s\n\nTURN / SEQUENCE / DELIVERY\n%d / %d / %d\n\nWORLD STATE SHA-256\n%s…\n\nBEFORE\n%s…\n\nVALIDATION  %s\n%s"
		% [
			event["event_id"],
			event["turn"],
			event["sequence"],
			event["delivery_index"],
			str(event["world_state_hash"]).substr(0, 20),
			str(event["world_state_hash_before"]).substr(0, 20),
			str(event["validation"]["status"]).to_upper(),
			" · ".join(codes) if not codes.is_empty() else "NO HARD ERROR CODE",
		]
	)
	progress_label.text = "FIXTURE SEED %d\nTERMINAL %s…" % [int(summary["seed"]), str(summary["terminal_state_hash"]).substr(0, 16)]
	beam.color = Color(spec["accent"], 0.24 if spec["capture_id"] != "sl-rc-001-arrival" else 0.08)
	signal_core.color = spec["accent"]


func _add_rect(parent: Node, rect: Rect2, color: Color) -> ColorRect:
	var node := ColorRect.new()
	node.position = rect.position
	node.size = rect.size
	node.color = color
	parent.add_child(node)
	return node


func _add_circle(parent: Node, center: Vector2, radius: float, color: Color) -> Polygon2D:
	var points := PackedVector2Array()
	for index in range(32):
		var angle := TAU * float(index) / 32.0
		points.append(center + Vector2(cos(angle), sin(angle)) * radius)
	return _add_polygon(parent, points, color)


func _add_polygon(parent: Node, points: PackedVector2Array, color: Color) -> Polygon2D:
	var node := Polygon2D.new()
	node.polygon = points
	node.color = color
	parent.add_child(node)
	return node


func _add_label(
	parent: Node,
	rect: Rect2,
	text: String,
	font_size: int,
	color: Color,
	alignment := HORIZONTAL_ALIGNMENT_LEFT
) -> Label:
	var node := Label.new()
	node.position = rect.position
	node.size = rect.size
	node.text = text
	node.add_theme_font_size_override("font_size", font_size)
	node.add_theme_color_override("font_color", color)
	node.horizontal_alignment = alignment
	node.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	node.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	parent.add_child(node)
	return node


func _parse_options(arguments: PackedStringArray) -> Dictionary:
	var result := {}
	for argument in arguments:
		if not argument.begins_with("--") or not "=" in argument:
			continue
		var parts := argument.substr(2).split("=", true, 1)
		result[parts[0]] = parts[1]
	return result


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		_fail("JSON file does not exist: %s" % path)
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not parsed is Dictionary:
		_fail("JSON root must be an object: %s" % path)
		return {}
	return parsed


func _read_jsonl(path: String) -> Array:
	if not FileAccess.file_exists(path):
		_fail("JSONL file does not exist: %s" % path)
		return []
	var result: Array = []
	for line in FileAccess.get_file_as_string(path).split("\n"):
		if line.strip_edges().is_empty():
			continue
		var parsed: Variant = JSON.parse_string(line)
		if not parsed is Dictionary:
			_fail("JSONL row must be an object: %s" % path)
			return []
		result.append(parsed)
	return result


func _write_json(path: String, document: Dictionary) -> bool:
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		_fail("cannot write JSON: %s" % path)
		return false
	handle.store_string(JSON.stringify(document, "  ", false) + "\n")
	return true


func _resource_sha256(path: String) -> String:
	return FileAccess.get_sha256(ProjectSettings.globalize_path(path))


func _fail(message: String) -> void:
	push_error(message)
	get_tree().quit(1)
