extends Node

const CanonicalState = preload("res://scripts/canonical_state.gd")
const ScenarioMachine = preload("res://scripts/sealed_lighthouse_machine.gd")

const FRAME_BUDGET_MS := 16.7
const REQUEST_BUDGET_MS := 100.0

var fixture: Dictionary
var scenario: Dictionary
var machine: SealedLighthouseMachine
var events: Array = []
var processed_event_ids := {}
var event_by_id := {}
var frame_delta_ms: Array = []
var request_latency_ms: Array = []
var next_logical_sequence := 0
var duplicate_event_count := 0
var timeout_count := 0
var fallback_count := 0
var commit_count := 0
var committed_operations: Array = []
var observed_fallback_codes: Array = []
var timeout_state_isolation := true


func _ready() -> void:
	call_deferred("_execute")


func _execute() -> void:
	var started_us := Time.get_ticks_usec()
	var options := _parse_options(OS.get_cmdline_user_args())
	var fixture_path: String = options.get("fixture", "")
	if fixture_path.is_empty():
		_fail("missing --fixture=/absolute/path/to/experimental-game-*.json")
		return
	fixture = _read_json(fixture_path)
	if fixture.is_empty():
		return
	scenario = _read_json(str(fixture["scenario_resource"]))
	if scenario.is_empty():
		return
	machine = ScenarioMachine.new(scenario)
	var initial_state := machine.state.duplicate(true)
	var initial_hash := machine.state_hash()
	var output_dir := _resolve_output_path(
		options.get("output", "user://experimental-game/%s" % fixture["fixture_id"])
	)
	var directory_error := DirAccess.make_dir_recursive_absolute(output_dir)
	if directory_error != OK:
		_fail("cannot create output directory: %s" % output_dir)
		return

	await get_tree().process_frame
	_sample_frame()
	_emit(
		"evt-000-observe",
		0,
		"observation",
		initial_hash,
		initial_hash,
		null,
		["dock_saved", "lighthouse_dark"],
		"not_applicable",
		[],
		false,
		0,
		null,
		false,
		null,
		0.0,
		{
			"location": machine.state["player"]["location"],
			"reachable_locations": machine.state["world"]["reachable_locations"],
			"observation_en": "The lighthouse is dark; the lamp store remains reachable.",
			"observation_ko": "등대는 어둡고 등구점은 접근 가능하다."
		}
	)

	_record_valid_operation_proposal(
		1,
		"acquire_object",
		{"object_id": "signal_lens"},
		["reachable:lamp_store", "object_at:signal_lens:lamp_store"]
	)
	_commit_operation(
		"evt-001-commit-acquire",
		1,
		"acquire_object",
		{"object_id": "signal_lens"},
		["reachable:lamp_store", "object_at:signal_lens:lamp_store"]
	)

	await get_tree().process_frame
	_sample_frame()
	var forbidden_before := machine.state_hash()
	var forbidden_proposal := {
		"actor_id": "captain_mira",
		"action": "ask_locked_secret",
		"disclosed_facts": ["keeper_betrayal", "tide_marks_hint"]
	}
	var disclosure_started_us := Time.get_ticks_usec()
	var forbidden_codes := machine.validate_disclosure(forbidden_proposal["disclosed_facts"])
	var disclosure_latency := _elapsed_ms(disclosure_started_us)
	request_latency_ms.append(disclosure_latency)
	_emit_state_event(
		"evt-002-action-secret",
		2,
		"player_action",
		forbidden_proposal,
		["quest_stage:1"],
		"not_applicable",
		[],
		0.0,
		{"intent": "request_locked_secret"}
	)
	_emit_state_event(
		"evt-002-candidate-secret",
		2,
		"candidate",
		forbidden_proposal,
		["captain_mira_knows:keeper_betrayal", "quest_stage:1"],
		"not_applicable",
		[],
		0.0,
		{"source": "deterministic_fault_candidate"}
	)
	_emit_state_event(
		"evt-002-validation-secret",
		2,
		"validation",
		forbidden_proposal,
		["policy:sealed-lighthouse-disclosure-v1", "quest_stage:1"],
		"invalid",
		forbidden_codes,
		disclosure_latency,
		{"hard_gate": true}
	)
	_emit_state_event(
		"evt-002-reject-secret",
		2,
		"reject",
		forbidden_proposal,
		["policy:sealed-lighthouse-disclosure-v1"],
		"invalid",
		forbidden_codes,
		0.0,
		{"canonical_mutation": false}
	)
	_emit(
		"evt-002-fallback-secret",
		2,
		"fallback",
		forbidden_before,
		machine.state_hash(),
		forbidden_proposal,
		["fallback:mira-safe-deflection-v1"],
		"invalid",
		forbidden_codes,
		false,
		0,
		"repair_budget_exhausted",
		false,
		null,
		0.0,
		{
			"fallback_id": scenario["safe_fallback"]["fallback_id"],
			"text_en": scenario["safe_fallback"]["text_en"],
			"text_ko": scenario["safe_fallback"]["text_ko"],
			"canonical_mutation": false
		}
	)
	fallback_count += 1
	observed_fallback_codes.append_array(forbidden_codes)
	var early_forbidden_state_isolation := forbidden_before == machine.state_hash()

	_record_valid_operation_proposal(
		3,
		"install_lens",
		{"object_id": "signal_lens"},
		["inventory:signal_lens", "quest_stage:1"]
	)
	_commit_operation(
		"evt-003-commit-install",
		3,
		"install_lens",
		{"object_id": "signal_lens"},
		["inventory:signal_lens", "quest_stage:1"]
	)

	if fixture["fault_mode"] == "duplicate_event":
		_commit_operation(
			"evt-003-commit-install",
			3,
			"install_lens",
			{"object_id": "signal_lens"},
			["inventory:signal_lens", "quest_stage:1"]
		)

	if fixture["fault_mode"] == "timeout":
		_record_timeout_fixture(4)

	await get_tree().process_frame
	_sample_frame()
	var hint_arguments := {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
	_record_valid_operation_proposal(
		5,
		"reveal_hint",
		hint_arguments,
		["quest_stage:2", "fact_authorized:tide_marks_hint"]
	)
	_commit_operation(
		"evt-005-commit-hint",
		5,
		"reveal_hint",
		hint_arguments,
		["quest_stage:2", "fact_authorized:tide_marks_hint"]
	)
	var permitted_hint_after_authorization: bool = (
		"tide_marks_hint" in machine.state["facts"]
		and "keeper_betrayal" not in machine.state["facts"]
		and int(machine.state["quest"]["stage"]) >= 2
	)

	await get_tree().process_frame
	_sample_frame()
	var terminal_hash := machine.state_hash()
	var save_path := output_dir.path_join("save.json")
	var save_document := {
		"schema_version": "1.0.0",
		"scenario_id": scenario["scenario_id"],
		"run_id": fixture["run_id"],
		"episode_id": fixture["episode_id"],
		"saved_at_event_id": "evt-006-save",
		"state_hash": terminal_hash,
		"state": machine.state.duplicate(true),
	}
	if fixture["fault_mode"] == "corrupt_save":
		# Persist the deliberately corrupted candidate without updating the recorded
		# checksum. The subsequent load must reject it before touching live state.
		save_document["state"]["quest"]["stage"] = 99
	if not _write_json(save_path, save_document):
		return
	_emit_state_event(
		"evt-006-save",
		6,
		"save",
		null,
		["state_hash:%s" % terminal_hash],
		"not_applicable",
		[],
		0.0,
		{"path": "save.json", "state_hash": terminal_hash}
	)
	var loaded_document := _read_json(save_path)
	if loaded_document.is_empty():
		return
	var loaded_state: Dictionary = loaded_document["state"]
	var before_load_hash := machine.state_hash()
	var load_applied := machine.load_state_if_hash_matches(
		loaded_state, str(loaded_document["state_hash"])
	)
	var loaded_hash := machine.state_hash()
	var corrupt_save_state_isolation: bool = (
		fixture["fault_mode"] != "corrupt_save"
		or (not load_applied and loaded_hash == before_load_hash)
	)
	_emit_state_event(
		"evt-007-load",
		7,
		"load",
		null,
		["saved_state_hash:%s" % loaded_document["state_hash"]],
		"valid" if load_applied else "invalid",
		[] if load_applied else ["SAVE_HASH_MISMATCH"],
		0.0,
		{
			"path": "save.json",
			"loaded_state_hash": loaded_hash,
			"preload_state_hash": before_load_hash,
			"load_applied": load_applied,
		}
	)

	# Replay the committed operation trace, not the deliberately corrupted candidate save.
	var replay_result := _replay(initial_state, events)
	var replay_hash: String = replay_result["state_hash"]
	_emit_state_event(
		"evt-008-replay-check",
		8,
		"replay_check",
		null,
		["trace_event_count:%d" % events.size()],
		"valid" if replay_result["valid"] else "invalid",
		replay_result["codes"],
		0.0,
		{
			"replay_state_hash": replay_hash,
			"terminal_state_hash": terminal_hash,
			"duplicate_events_ignored": replay_result["duplicate_events_ignored"]
		}
	)

	await get_tree().process_frame
	_sample_frame()
	# `sequence` identifies the logical event and therefore remains identical for a
	# duplicated delivery. `delivery_index` is the unique JSONL line order.
	for delivery_index in range(events.size()):
		events[delivery_index]["delivery_index"] = delivery_index
	var trace_path := output_dir.path_join("events.jsonl")
	if not _write_jsonl(trace_path, events):
		return
	var engine_elapsed_ms := _elapsed_ms(started_us)
	var p95_frame := _percentile_95(frame_delta_ms)
	var p95_request := _percentile_95(request_latency_ms)
	var expected: Dictionary = fixture["expected"]
	var fixture_expectations_match: bool = (
		CanonicalState.sorted_unique(observed_fallback_codes) == expected["fallback_codes"]
		and committed_operations == expected["committed_operations"]
		and duplicate_event_count == int(expected["duplicate_event_count"])
		and timeout_count == int(expected["timeout_count"])
	)
	var summary := {
		"schema_version": "1.0.0",
		"execution_status": "OBSERVED_ENGINE_RUN",
		"fixture_id": fixture["fixture_id"],
		"scenario_id": scenario["scenario_id"],
		"run_id": fixture["run_id"],
		"episode_id": fixture["episode_id"],
		"seed": int(fixture["seed"]),
		"engine": {
			"name": "Godot",
			"version": str(Engine.get_version_info()["string"]),
			"headless": DisplayServer.get_name() == "headless",
		},
		"hash_algorithm": "sha256-canonical-json-v1",
		"initial_state_hash": initial_hash,
		"research_oracle_state_hash": expected["research_oracle_state_hash"],
		"terminal_state_hash": terminal_hash,
		"loaded_state_hash": loaded_hash,
		"replay_state_hash": replay_hash,
		"checks": {
			"early_forbidden_state_isolation": early_forbidden_state_isolation,
			"permitted_hint_after_authorization": permitted_hint_after_authorization,
			"save_load_hash_match": (
				loaded_hash == terminal_hash
				and load_applied == bool(fixture["expected"]["save_load_matches"])
			),
			"replay_hash_match": replay_result["valid"] and replay_hash == terminal_hash,
			"expected_terminal_hash_match": terminal_hash == fixture["expected"]["terminal_state_hash"],
			"research_oracle_hash_match": (
				terminal_hash == fixture["expected"]["research_oracle_state_hash"]
			),
			"duplicate_idempotent": (
				duplicate_event_count == int(fixture["expected"]["duplicate_event_count"])
				and replay_result["duplicate_events_ignored"] == duplicate_event_count
			),
			"timeout_state_isolation": (
				timeout_state_isolation
				and timeout_count == int(fixture["expected"]["timeout_count"])
			),
			"corrupt_save_state_isolation": corrupt_save_state_isolation,
			"fixture_expectations_match": fixture_expectations_match,
		},
		"counts": {
			"events": events.size(),
			"commits": commit_count,
			"fallbacks": fallback_count,
			"duplicate_events": duplicate_event_count,
			"timeouts": timeout_count,
		},
		"software": {
			"runner_sha256": _resource_sha256("res://scripts/experimental_game_runner.gd"),
			"machine_sha256": _resource_sha256("res://scripts/sealed_lighthouse_machine.gd"),
			"canonicalizer_sha256": _resource_sha256("res://scripts/canonical_state.gd"),
			"scenario_sha256": _resource_sha256(str(fixture["scenario_resource"])),
			"fixture_sha256": _file_sha256(fixture_path),
		},
		"telemetry": {
			"clock": "Time.get_ticks_usec",
			"engine_elapsed_ms": engine_elapsed_ms,
			"headless_frame_delta_ms": frame_delta_ms,
			"request_latency_ms": request_latency_ms,
			"p95_frame_delta_ms": p95_frame,
			"p95_request_latency_ms": p95_request,
			"frame_budget_ms": FRAME_BUDGET_MS,
			"request_budget_ms": REQUEST_BUDGET_MS,
			"frame_budget_passed": p95_frame <= FRAME_BUDGET_MS,
			"request_budget_passed": p95_request < REQUEST_BUDGET_MS and timeout_count == 0,
		},
		"artifacts": {
			"events_jsonl": "events.jsonl",
			"save_json": "save.json",
		},
	}
	var summary_path := output_dir.path_join("summary.json")
	if not _write_json(summary_path, summary):
		return
	var required_checks: Dictionary = summary["checks"]
	var all_checks_passed := true
	for check in required_checks.values():
		all_checks_passed = all_checks_passed and bool(check)
	print(JSON.stringify({
		"summary_path": summary_path,
		"terminal_state_hash": terminal_hash,
		"all_checks_passed": all_checks_passed,
	}))
	get_tree().quit(0 if all_checks_passed else 2)


func _record_valid_operation_proposal(
	turn: int,
	operation: String,
	arguments: Dictionary,
	evidence_ids: Array
) -> void:
	var proposal := {"operation": operation, "arguments": arguments}
	_emit_state_event(
		"evt-%03d-action-%s" % [turn, operation],
		turn,
		"player_action",
		proposal,
		evidence_ids,
		"not_applicable",
		[],
		0.0,
		{"intent": operation}
	)
	_emit_state_event(
		"evt-%03d-candidate-%s" % [turn, operation],
		turn,
		"candidate",
		proposal,
		evidence_ids,
		"not_applicable",
		[],
		0.0,
		{"source": "deterministic_fixture_policy"}
	)
	_emit_state_event(
		"evt-%03d-validation-%s" % [turn, operation],
		turn,
		"validation",
		proposal,
		evidence_ids,
		"valid",
		[],
		0.0,
		{"hard_gate": true}
	)


func _commit_operation(
	event_id: String,
	turn: int,
	operation: String,
	arguments: Dictionary,
	evidence_ids: Array
) -> Dictionary:
	if processed_event_ids.has(event_id):
		duplicate_event_count += 1
		var duplicate: Dictionary = event_by_id[event_id].duplicate(true)
		events.append(duplicate)
		return {"accepted": true, "duplicate": true, "mutated": false}
	var before_hash := machine.state_hash()
	var started_us := Time.get_ticks_usec()
	var result := machine.apply_operation(operation, arguments)
	var latency_ms := _elapsed_ms(started_us)
	request_latency_ms.append(latency_ms)
	var after_hash := machine.state_hash()
	var event := _make_event(
		event_id,
		turn,
		"commit" if result["accepted"] else "reject",
		before_hash,
		after_hash,
		{"operation": operation, "arguments": arguments},
		evidence_ids,
		"valid" if result["accepted"] else "invalid",
		result["codes"],
		false,
		0,
		null,
		bool(result["accepted"]),
		operation if result["accepted"] else null,
		latency_ms,
		{"operation": operation, "arguments": arguments, "mutated": result["mutated"]}
	)
	processed_event_ids[event_id] = true
	event_by_id[event_id] = event.duplicate(true)
	events.append(event)
	if result["accepted"]:
		commit_count += 1
		committed_operations.append(operation)
	return result


func _record_timeout_fixture(turn: int) -> void:
	var before_hash := machine.state_hash()
	var proposal := {
		"operation": "reveal_hint",
		"arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
	}
	_emit_state_event(
		"evt-004-action-timeout",
		turn,
		"player_action",
		proposal,
		["quest_stage:2"],
		"not_applicable",
		[],
		0.0,
		{"intent": "timeout_fault_injection"}
	)
	_emit_state_event(
		"evt-004-candidate-timeout",
		turn,
		"candidate",
		proposal,
		["fixture:timeout"],
		"not_applicable",
		[],
		0.0,
		{"source": "fault_injection"}
	)
	_emit(
		"evt-004-timeout",
		turn,
		"timeout",
		before_hash,
		machine.state_hash(),
		proposal,
		["fixture:timeout"],
		"timeout",
		["ADAPTER_TIMEOUT"],
		false,
		0,
		"adapter_timeout",
		false,
		null,
		REQUEST_BUDGET_MS,
		{"deadline_ms": REQUEST_BUDGET_MS, "canonical_mutation": false}
	)
	_emit(
		"evt-004-fallback-timeout",
		turn,
		"fallback",
		before_hash,
		machine.state_hash(),
		proposal,
		["fallback:mira-safe-deflection-v1"],
		"timeout",
		["ADAPTER_TIMEOUT"],
		false,
		0,
		"adapter_timeout",
		false,
		null,
		0.0,
		{"fallback_id": scenario["safe_fallback"]["fallback_id"], "canonical_mutation": false}
	)
	timeout_count += 1
	fallback_count += 1
	observed_fallback_codes.append("ADAPTER_TIMEOUT")
	timeout_state_isolation = timeout_state_isolation and before_hash == machine.state_hash()
	request_latency_ms.append(REQUEST_BUDGET_MS)


func _replay(initial_state: Dictionary, trace_events: Array) -> Dictionary:
	var replay_machine := ScenarioMachine.new(scenario)
	replay_machine.load_state(initial_state)
	var seen := {}
	var codes: Array = []
	var duplicates_ignored := 0
	for event in trace_events:
		var event_id: String = event["event_id"]
		if seen.has(event_id):
			duplicates_ignored += 1
			continue
		seen[event_id] = true
		if event["event_type"] != "commit" or not event["commit"]["applied"]:
			if replay_machine.state_hash() != event["world_state_hash"]:
				codes.append("NON_COMMIT_STATE_HASH_MISMATCH")
			continue
		if replay_machine.state_hash() != event["world_state_hash_before"]:
			codes.append("COMMIT_PRIOR_HASH_MISMATCH")
			continue
		var replayed := replay_machine.apply_operation(
			event["payload"]["operation"], event["payload"]["arguments"]
		)
		if not replayed["accepted"]:
			codes.append("REPLAY_OPERATION_REJECTED")
		if replay_machine.state_hash() != event["world_state_hash"]:
			codes.append("COMMIT_TERMINAL_HASH_MISMATCH")
	return {
		"valid": codes.is_empty(),
		"codes": CanonicalState.sorted_unique(codes),
		"state_hash": replay_machine.state_hash(),
		"duplicate_events_ignored": duplicates_ignored,
	}


func _emit_state_event(
	event_id: String,
	turn: int,
	event_type: String,
	proposal: Variant,
	evidence_ids: Array,
	validation_status: String,
	validation_codes: Array,
	latency_ms: float,
	payload: Dictionary
) -> void:
	var state_hash := machine.state_hash()
	_emit(
		event_id,
		turn,
		event_type,
		state_hash,
		state_hash,
		proposal,
		evidence_ids,
		validation_status,
		validation_codes,
		false,
		0,
		null,
		false,
		null,
		latency_ms,
		payload
	)


func _emit(
	event_id: String,
	turn: int,
	event_type: String,
	before_hash: String,
	after_hash: String,
	proposal: Variant,
	evidence_ids: Array,
	validation_status: String,
	validation_codes: Array,
	repair_applied: bool,
	repair_attempt: int,
	repair_reason: Variant,
	commit_applied: bool,
	commit_operation: Variant,
	latency_ms: float,
	payload: Dictionary
) -> void:
	events.append(_make_event(
		event_id,
		turn,
		event_type,
		before_hash,
		after_hash,
		proposal,
		evidence_ids,
		validation_status,
		validation_codes,
		repair_applied,
		repair_attempt,
		repair_reason,
		commit_applied,
		commit_operation,
		latency_ms,
		payload
	))


func _make_event(
	event_id: String,
	turn: int,
	event_type: String,
	before_hash: String,
	after_hash: String,
	proposal: Variant,
	evidence_ids: Array,
	validation_status: String,
	validation_codes: Array,
	repair_applied: bool,
	repair_attempt: int,
	repair_reason: Variant,
	commit_applied: bool,
	commit_operation: Variant,
	latency_ms: float,
	payload: Dictionary
) -> Dictionary:
	var logical_sequence := next_logical_sequence
	next_logical_sequence += 1
	return {
		"schema_version": "1.1.0",
		"scenario_id": scenario["scenario_id"],
		"run_id": fixture["run_id"],
		"episode_id": fixture["episode_id"],
		"event_id": event_id,
		"sequence": logical_sequence,
		"turn": turn,
		"event_type": event_type,
		"seed": int(fixture["seed"]),
		"timestamp_ms": logical_sequence * 100,
		"world_state_hash_before": before_hash,
		"world_state_hash": after_hash,
		"model_id": "fixture/deterministic-policy",
		"model_revision": "sealed-lighthouse-fixture-v1",
		"policy_id": scenario["disclosure_policy"]["policy_id"],
		"proposal": proposal,
		"evidence_ids": CanonicalState.sorted_unique(evidence_ids),
		"validation": {
			"status": validation_status,
			"codes": CanonicalState.sorted_unique(validation_codes),
		},
		"repair": {
			"applied": repair_applied,
			"attempt": repair_attempt,
			"reason": repair_reason,
		},
		"commit": {
			"applied": commit_applied,
			"operation": commit_operation,
		},
		"cost_usd": 0.0,
		"request_latency_ms": latency_ms,
		"payload": payload,
	}


func _parse_options(arguments: PackedStringArray) -> Dictionary:
	var options := {}
	for argument in arguments:
		if not argument.begins_with("--") or "=" not in argument:
			continue
		var parts := argument.trim_prefix("--").split("=", true, 1)
		options[parts[0]] = parts[1]
	return options


func _resolve_output_path(path: String) -> String:
	if path.begins_with("user://") or path.begins_with("res://"):
		return ProjectSettings.globalize_path(path)
	if path.is_absolute_path():
		return path
	return ProjectSettings.globalize_path("user://" + path)


func _read_json(path: String) -> Dictionary:
	var resolved := ProjectSettings.globalize_path(path) if path.begins_with("res://") else path
	if not FileAccess.file_exists(resolved):
		_fail("JSON file does not exist: %s" % resolved)
		return {}
	var handle := FileAccess.open(resolved, FileAccess.READ)
	if handle == null:
		_fail("cannot open JSON file: %s" % resolved)
		return {}
	var parsed: Variant = JSON.parse_string(handle.get_as_text())
	if not parsed is Dictionary:
		_fail("JSON root must be an object: %s" % resolved)
		return {}
	return parsed


func _write_json(path: String, document: Dictionary) -> bool:
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		_fail("cannot write JSON file: %s" % path)
		return false
	handle.store_string(JSON.stringify(CanonicalState.canonicalize(document), "  ", false) + "\n")
	return true


func _write_jsonl(path: String, records: Array) -> bool:
	var handle := FileAccess.open(path, FileAccess.WRITE)
	if handle == null:
		_fail("cannot write JSONL file: %s" % path)
		return false
	for record in records:
		handle.store_line(CanonicalState.canonical_json(record))
	return true


func _sample_frame() -> void:
	frame_delta_ms.append(maxf(get_process_delta_time() * 1000.0, 0.0))


func _elapsed_ms(started_us: int) -> float:
	return maxf(float(Time.get_ticks_usec() - started_us) / 1000.0, 0.0)


func _percentile_95(values: Array) -> float:
	if values.is_empty():
		return 0.0
	var ordered := values.duplicate()
	ordered.sort()
	var index := mini(int(ceil(0.95 * ordered.size())) - 1, ordered.size() - 1)
	return float(ordered[maxi(index, 0)])


func _resource_sha256(path: String) -> String:
	return _file_sha256(ProjectSettings.globalize_path(path))


func _file_sha256(path: String) -> String:
	var handle := FileAccess.open(path, FileAccess.READ)
	if handle == null:
		push_error("cannot hash file: %s" % path)
		return ""
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		return ""
	if context.update(handle.get_buffer(handle.get_length())) != OK:
		return ""
	return context.finish().hex_encode()


func _fail(message: String) -> void:
	push_error(message)
	get_tree().quit(1)
