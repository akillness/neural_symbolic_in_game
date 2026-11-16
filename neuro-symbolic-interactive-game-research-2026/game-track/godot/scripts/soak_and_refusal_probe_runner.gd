extends Node

## Separate headless deterministic refusal-coverage and soak probe for
## The Sealed Lighthouse (`SL-SOAK-REFUSAL-PROBE-001`).
##
## Purpose:
## 1. Exercise all 9 refusal codes in `IMPLEMENTED_CODES`, explicitly including
##    the 2 codes left structurally unexercised by `SL-BALANCE-PROBE-001`:
##    - `OBJECT_NOT_REACHABLE` (via canonical `apply_world_event("LENS_UNREACHABLE")`
##      and via hash-verified snapshot injection).
##    - `QUEST_STAGE_PRECONDITION` (via hash-verified `load_state_if_hash_matches`
##      snapshot injection where `signal_lens` is carried with `quest.stage < 1`).
## 2. Run a bounded deterministic headless soak loop (default 1600 ticks = 200
##    complete 8-step cycles) measuring step/commit duration p95, frame time p95
##    (both full-run including startup transients and post-warmup steady state),
##    Godot static memory, object/orphan counts, and OS resident set size (RSS).
##
## Does not modify any frozen artifact, `SL-PLAY-EVAL-001`, or `SL-BALANCE-PROBE-001`.

const SealedLighthouseMachine = preload("res://scripts/sealed_lighthouse_machine.gd")
const CanonicalState = preload("res://scripts/canonical_state.gd")
const EvaluationTraceScript = preload("res://scripts/game3d/evaluation_trace.gd")

const SCENARIO_PATH := "res://data/sealed_lighthouse.json"
const PROBE_ID := "SL-SOAK-REFUSAL-PROBE-001"
const EXACT_TERMINAL_HASH := "4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892"
const DEFAULT_SOAK_TICKS := 1600
const WARMUP_TICKS := 64
const IMPLEMENTED_CODES := [
	"FORBIDDEN_DISCLOSURE",
	"STAGE_GATED_DISCLOSURE",
	"MISSING_REQUIRED_OBJECT",
	"OBJECT_NOT_PRESENT",
	"OBJECT_NOT_REACHABLE",
	"QUEST_STAGE_PRECONDITION",
	"UNKNOWN_OPERATION",
	"UNKNOWN_ACTOR",
	"NPC_DOES_NOT_KNOW_FACT",
]

var _scenario: Dictionary = {}
var _output_path: String = "user://soak-and-refusal-probe.json"
var _soak_ticks: int = DEFAULT_SOAK_TICKS
var _warmup_ticks: int = WARMUP_TICKS

var _failures: Array = []
var _refusal_battery: Dictionary = {}
var _pre_refusal_rss_kib: int = -1
var _pre_soak_rss_kib: int = -1
var _post_soak_rss_kib: int = -1

var _soak_machine: SealedLighthouseMachine
var _terminal_snapshot: Dictionary = {}
var _stage0_lens_snapshot: Dictionary = {}
var _stage0_lens_hash: String = ""

var _tick_index: int = 0
var _soak_active: bool = false
var _prev_frame_us: int = 0
var _soak_started_us: int = 0

var _frame_delta_ms: Array[float] = []
var _frame_wall_ms: Array[float] = []
var _step_commit_ms: Array[float] = []
var _commit_only_ms: Array[float] = []
var _commit_only_index: int = 0
var _static_mem_bytes: Array[int] = []
var _object_counts: Array[int] = []
var _node_counts: Array[int] = []
var _orphan_counts: Array[int] = []

var _soak_commits: int = 0
var _soak_refusals: int = 0
var _soak_refusals_isolated: int = 0
var _soak_world_events: int = 0
var _soak_save_loads: int = 0
var _soak_trace_checks: int = 0
var _soak_trace_consistent: int = 0
var _soak_episodes_completed: int = 0
var _soak_terminal_hash_matches: int = 0
var _soak_exercised_codes: Dictionary = {}


func _ready() -> void:
	var user_args := OS.get_cmdline_user_args()
	var output_index := user_args.find("--output")
	if output_index != -1 and output_index + 1 < user_args.size():
		_output_path = user_args[output_index + 1]
	var ticks_index := user_args.find("--ticks")
	if ticks_index != -1 and ticks_index + 1 < user_args.size():
		_soak_ticks = maxi(int(user_args[ticks_index + 1]), 16)
	_warmup_ticks = mini(WARMUP_TICKS, maxi(_soak_ticks / 10, 1))

	_scenario = _load_scenario()
	_pre_refusal_rss_kib = _sample_rss_kib()
	_refusal_battery = _run_refusal_battery(_scenario)
	_prepare_soak_state()
	_frame_delta_ms.resize(_soak_ticks)
	_frame_wall_ms.resize(_soak_ticks)
	_step_commit_ms.resize(_soak_ticks)
	_commit_only_ms.resize((_soak_ticks / 8) * 3 + 3)
	_static_mem_bytes.resize(_soak_ticks)
	_object_counts.resize(_soak_ticks)
	_node_counts.resize(_soak_ticks)
	_orphan_counts.resize(_soak_ticks)
	_pre_soak_rss_kib = _sample_rss_kib()

	_soak_started_us = Time.get_ticks_usec()
	_prev_frame_us = _soak_started_us
	_soak_active = true


func _process(delta: float) -> void:
	if not _soak_active:
		return

	var frame_now_us := Time.get_ticks_usec()
	var wall_ms := maxf(float(frame_now_us - _prev_frame_us) / 1000.0, 0.0)
	_prev_frame_us = frame_now_us
	var delta_ms := maxf(delta * 1000.0, 0.0)

	var step_started_us := Time.get_ticks_usec()
	var step_kind := _tick_index % 8
	_execute_soak_step(_tick_index, step_kind)
	var step_ms := maxf(float(Time.get_ticks_usec() - step_started_us) / 1000.0, 0.0)

	_frame_delta_ms[_tick_index] = delta_ms
	_frame_wall_ms[_tick_index] = wall_ms
	_step_commit_ms[_tick_index] = step_ms
	if step_kind in [1, 2, 3]:
		_commit_only_ms[_commit_only_index] = step_ms
		_commit_only_index += 1

	_static_mem_bytes[_tick_index] = int(OS.get_static_memory_usage())
	_object_counts[_tick_index] = int(Performance.get_monitor(Performance.OBJECT_COUNT))
	_node_counts[_tick_index] = int(Performance.get_monitor(Performance.OBJECT_NODE_COUNT))
	_orphan_counts[_tick_index] = int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))

	_tick_index += 1
	if _tick_index >= _soak_ticks:
		_soak_active = false
		_commit_only_ms.resize(_commit_only_index)
		var soak_elapsed_ms := maxf(float(Time.get_ticks_usec() - _soak_started_us) / 1000.0, 0.0)
		_post_soak_rss_kib = _sample_rss_kib()
		_finalize_and_quit(soak_elapsed_ms)


func _load_scenario() -> Dictionary:
	var text := FileAccess.get_file_as_string(SCENARIO_PATH)
	var parsed: Variant = JSON.parse_string(text)
	assert(parsed is Dictionary, "scenario document must parse")
	return parsed


func _sample_rss_kib() -> int:
	var out: Array = []
	var rc := OS.execute("ps", ["-o", "rss=", "-p", str(OS.get_process_id())], out, true)
	if rc != 0 or out.is_empty():
		return -1
	var raw := str(out[0]).strip_edges()
	if raw.is_empty() or not raw.is_valid_int():
		return -1
	return int(raw)


func _fail(section: String, step_label: String, message: String) -> void:
	_failures.append({
		"section": section,
		"step": step_label,
		"message": message,
	})


func _run_refusal_case(
	case_id: String,
	machine: SealedLighthouseMachine,
	operation: String,
	arguments: Dictionary,
	expected_code: String,
	mechanism: String
) -> Dictionary:
	var pre_hash := machine.state_hash()
	var pre_snapshot: Dictionary = machine.state.duplicate(true)
	var started_us := Time.get_ticks_usec()
	var result: Dictionary = machine.apply_operation(operation, arguments)
	var latency_ms := maxf(float(Time.get_ticks_usec() - started_us) / 1000.0, 0.0)
	var post_hash := machine.state_hash()
	var trace: Dictionary = EvaluationTraceScript.reconstruct(_scenario, pre_snapshot, operation, arguments)
	var trace_matches := EvaluationTraceScript.consistent(trace["checks"], result["codes"])
	var isolated := (post_hash == pre_hash) and (not bool(result["mutated"]))
	var passed: bool = (
		(not bool(result["accepted"]))
		and (result["codes"] == [expected_code])
		and isolated
		and trace_matches
	)
	if not passed:
		_fail(
			"refusal_battery",
			case_id,
			"expected [%s] isolated+trace_consistent; got accepted=%s codes=%s isolated=%s trace=%s" % [
				expected_code, result["accepted"], result["codes"], isolated, trace_matches
			]
		)
	return {
		"case_id": case_id,
		"expected_code": expected_code,
		"observed_codes": result["codes"],
		"mechanism": mechanism,
		"operation": operation,
		"arguments": arguments,
		"accepted": bool(result["accepted"]),
		"mutated": bool(result["mutated"]),
		"state_isolated": isolated,
		"trace_consistent": trace_matches,
		"pre_state_sha256": pre_hash,
		"post_state_sha256": post_hash,
		"latency_ms": snappedf(latency_ms, 0.001),
		"passed": passed,
	}


func _make_stage0_lens_snapshot() -> Dictionary:
	var snap: Dictionary = _scenario["initial_state"].duplicate(true)
	snap["revision"] = 0
	snap["quest"]["stage"] = 0
	snap["player"]["inventory"] = ["signal_lens"]
	snap["world"]["object_locations"] = {}
	return snap


func _run_refusal_battery(scenario: Dictionary) -> Dictionary:
	var cases: Array = []

	# 1. Previously unexercised #1 (Path A): canonical world event LENS_UNREACHABLE -> OBJECT_NOT_REACHABLE.
	var m_world := SealedLighthouseMachine.new(scenario)
	var before_world_hash := m_world.state_hash()
	var world_event_res: Dictionary = m_world.apply_world_event("LENS_UNREACHABLE", {})
	var world_event_ok: bool = (
		bool(world_event_res["accepted"])
		and bool(world_event_res["mutated"])
		and (m_world.state_hash() != before_world_hash)
		and ("lamp_store" not in m_world.state["world"]["reachable_locations"])
	)
	if not world_event_ok:
		_fail("refusal_battery", "world-event-lens-unreachable", "LENS_UNREACHABLE world event did not apply cleanly")
	cases.append(_run_refusal_case(
		"unexercised-01a-object-not-reachable-world-event",
		m_world,
		"acquire_object",
		{"object_id": "signal_lens"},
		"OBJECT_NOT_REACHABLE",
		"canonical apply_world_event('LENS_UNREACHABLE') removes lamp_store from reachable_locations"
	))

	# 2. Previously unexercised #1 (Path B): hash-verified snapshot with unreachable location -> OBJECT_NOT_REACHABLE.
	var m_unreach_snap := SealedLighthouseMachine.new(scenario)
	var unreach_snap: Dictionary = scenario["initial_state"].duplicate(true)
	unreach_snap["revision"] = int(unreach_snap["revision"])
	unreach_snap["quest"]["stage"] = int(unreach_snap["quest"]["stage"])
	unreach_snap["world"]["object_locations"]["signal_lens"] = "blocked_tower_room"
	var unreach_hash := CanonicalState.sha256(unreach_snap)
	if not m_unreach_snap.load_state_if_hash_matches(unreach_snap, unreach_hash):
		_fail("refusal_battery", "unreach-snapshot-load", "failed hash-verified load for unreachable-object snapshot")
	cases.append(_run_refusal_case(
		"unexercised-01b-object-not-reachable-snapshot",
		m_unreach_snap,
		"acquire_object",
		{"object_id": "signal_lens"},
		"OBJECT_NOT_REACHABLE",
		"hash-verified load_state_if_hash_matches with object at unreachable 'blocked_tower_room'"
	))

	# 3. Previously unexercised #2 (Path A): hash-verified snapshot with carried lens and stage=0 -> QUEST_STAGE_PRECONDITION.
	var m_stage0 := SealedLighthouseMachine.new(scenario)
	var stage0_snap := _make_stage0_lens_snapshot()
	var stage0_hash := CanonicalState.sha256(stage0_snap)
	if not m_stage0.load_state_if_hash_matches(stage0_snap, stage0_hash):
		_fail("refusal_battery", "stage0-snapshot-load", "failed hash-verified load for stage=0 carried-lens snapshot")
	cases.append(_run_refusal_case(
		"unexercised-02a-quest-stage-precondition-stage0",
		m_stage0,
		"install_lens",
		{"object_id": "signal_lens"},
		"QUEST_STAGE_PRECONDITION",
		"hash-verified load_state_if_hash_matches with carried signal_lens and quest.stage=0"
	))

	# 4. Previously unexercised #2 (Path B): negative quest.stage=-1 boundary -> QUEST_STAGE_PRECONDITION.
	var m_stage_neg := SealedLighthouseMachine.new(scenario)
	var stage_neg_snap := _make_stage0_lens_snapshot()
	stage_neg_snap["quest"]["stage"] = -1
	var stage_neg_hash := CanonicalState.sha256(stage_neg_snap)
	if not m_stage_neg.load_state_if_hash_matches(stage_neg_snap, stage_neg_hash):
		_fail("refusal_battery", "stage-neg-snapshot-load", "failed hash-verified load for stage=-1 carried-lens snapshot")
	cases.append(_run_refusal_case(
		"unexercised-02b-quest-stage-precondition-stage-neg1",
		m_stage_neg,
		"install_lens",
		{"object_id": "signal_lens"},
		"QUEST_STAGE_PRECONDITION",
		"hash-verified load_state_if_hash_matches with carried signal_lens and quest.stage=-1"
	))

	# 5-11. Exercise the remaining 7 codes in IMPLEMENTED_CODES on a fresh machine for full 9/9 verification.
	var m_all := SealedLighthouseMachine.new(scenario)
	cases.append(_run_refusal_case(
		"core-03-missing-required-object",
		m_all,
		"install_lens",
		{"object_id": "signal_lens"},
		"MISSING_REQUIRED_OBJECT",
		"install_lens before acquire_object"
	))
	cases.append(_run_refusal_case(
		"core-04-unknown-operation",
		m_all,
		"polish_lens",
		{},
		"UNKNOWN_OPERATION",
		"unsupported operation name"
	))
	cases.append(_run_refusal_case(
		"core-05-forbidden-disclosure",
		m_all,
		"reveal_hint",
		{"actor_id": "captain_mira", "fact_id": "keeper_betrayal"},
		"FORBIDDEN_DISCLOSURE",
		"permanently_forbidden fact requested"
	))
	cases.append(_run_refusal_case(
		"core-06-stage-gated-disclosure",
		m_all,
		"reveal_hint",
		{"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
		"STAGE_GATED_DISCLOSURE",
		"stage-gated fact requested before quest.stage >= 2"
	))
	cases.append(_run_refusal_case(
		"core-07-unknown-actor",
		m_all,
		"reveal_hint",
		{"actor_id": "harbor_ghost", "fact_id": "lighthouse_dark"},
		"UNKNOWN_ACTOR",
		"undeclared actor_id"
	))
	cases.append(_run_refusal_case(
		"core-08-npc-does-not-know-fact",
		m_all,
		"reveal_hint",
		{"actor_id": "captain_mira", "fact_id": "sea_glass_rumor"},
		"NPC_DOES_NOT_KNOW_FACT",
		"fact absent from captain_mira knowledge list"
	))
	var acq := m_all.apply_operation("acquire_object", {"object_id": "signal_lens"})
	if not bool(acq["accepted"]):
		_fail("refusal_battery", "acquire-for-not-present", "setup acquire_object failed")
	cases.append(_run_refusal_case(
		"core-09-object-not-present",
		m_all,
		"acquire_object",
		{"object_id": "signal_lens"},
		"OBJECT_NOT_PRESENT",
		"acquire_object after signal_lens already acquired"
	))

	var exercised_set: Dictionary = {}
	var isolated_count := 0
	var trace_consistent_count := 0
	for row in cases:
		for code in row["observed_codes"]:
			exercised_set[str(code)] = true
		if bool(row["state_isolated"]):
			isolated_count += 1
		if bool(row["trace_consistent"]):
			trace_consistent_count += 1

	var missing_codes: Array = []
	for code in IMPLEMENTED_CODES:
		if not exercised_set.has(code):
			missing_codes.append(code)
			_fail("refusal_battery", "coverage", "implemented code not exercised: " + code)

	var exercised_list: Array = exercised_set.keys()
	exercised_list.sort()
	return {
		"cases": cases,
		"total_cases": cases.size(),
		"newly_exercised_from_balance_probe": [
			"OBJECT_NOT_REACHABLE",
			"QUEST_STAGE_PRECONDITION",
		],
		"implemented_codes": IMPLEMENTED_CODES,
		"implemented_count": IMPLEMENTED_CODES.size(),
		"exercised_codes": exercised_list,
		"exercised_count": exercised_list.size(),
		"missing_codes": missing_codes,
		"all_cases_state_isolated": isolated_count == cases.size(),
		"isolated_cases": isolated_count,
		"all_cases_trace_consistent": trace_consistent_count == cases.size(),
		"trace_consistent_cases": trace_consistent_count,
		"supplementary_machine_guards": {
			"DISCLOSURE_TEMPLATE_UNAVAILABLE": "defensive guard in _reveal_hint when EvidenceCaptureRunner.CAPTURE_SPECS lacks sl-rc-003-authorized-hint; structurally unreachable under intact source assets",
		},
	}


func _prepare_soak_state() -> void:
	_soak_machine = SealedLighthouseMachine.new(_scenario)
	var ref := SealedLighthouseMachine.new(_scenario)
	ref.apply_operation("acquire_object", {"object_id": "signal_lens"})
	ref.apply_operation("install_lens", {"object_id": "signal_lens"})
	ref.apply_operation("reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"})
	if ref.state_hash() != EXACT_TERMINAL_HASH:
		_fail("soak_setup", "reference", "canonical terminal hash mismatch: " + ref.state_hash())
	_terminal_snapshot = ref.state.duplicate(true)
	_stage0_lens_snapshot = _make_stage0_lens_snapshot()
	_stage0_lens_hash = CanonicalState.sha256(_stage0_lens_snapshot)


func _execute_soak_step(tick: int, step_kind: int) -> void:
	match step_kind:
		0:
			_soak_machine.reset()
			_soak_check_refusal(
				tick,
				"reveal_hint",
				{"actor_id": "captain_mira", "fact_id": "tide_marks_hint"},
				"STAGE_GATED_DISCLOSURE"
			)
		1:
			_soak_check_commit(tick, "acquire_object", {"object_id": "signal_lens"}, 1)
		2:
			_soak_check_commit(tick, "install_lens", {"object_id": "signal_lens"}, 2)
		3:
			_soak_check_commit(tick, "reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, 3)
			if _soak_machine.state_hash() == EXACT_TERMINAL_HASH:
				_soak_terminal_hash_matches += 1
			else:
				_fail("soak", "tick-%d" % tick, "terminal hash drifted: " + _soak_machine.state_hash())
		4:
			_soak_check_refusal(
				tick,
				"reveal_hint",
				{"actor_id": "captain_mira", "fact_id": "keeper_betrayal"},
				"FORBIDDEN_DISCLOSURE"
			)
		5:
			var loaded := _soak_machine.load_state_if_hash_matches(_terminal_snapshot, EXACT_TERMINAL_HASH)
			_soak_save_loads += 1
			if not loaded or _soak_machine.state_hash() != EXACT_TERMINAL_HASH:
				_fail("soak", "tick-%d" % tick, "save/load roundtrip hash mismatch")
			var pre_snap: Dictionary = _soak_machine.state.duplicate(true)
			var trace: Dictionary = EvaluationTraceScript.reconstruct(
				_scenario,
				pre_snap,
				"reveal_hint",
				{"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
			)
			_soak_trace_checks += 1
			if EvaluationTraceScript.consistent(trace["checks"], []):
				_soak_trace_consistent += 1
			else:
				_fail("soak", "tick-%d" % tick, "trace mirror mismatch on redisplay check")
		6:
			_soak_machine.reset()
			var ev := _soak_machine.apply_world_event("LENS_UNREACHABLE", {})
			_soak_world_events += 1
			if not bool(ev["accepted"]):
				_fail("soak", "tick-%d" % tick, "LENS_UNREACHABLE world event rejected")
			_soak_check_refusal(
				tick,
				"acquire_object",
				{"object_id": "signal_lens"},
				"OBJECT_NOT_REACHABLE"
			)
		7:
			var loaded_stage0 := _soak_machine.load_state_if_hash_matches(_stage0_lens_snapshot, _stage0_lens_hash)
			_soak_save_loads += 1
			if not loaded_stage0 or _soak_machine.state_hash() != _stage0_lens_hash:
				_fail("soak", "tick-%d" % tick, "stage0 snapshot load failed")
			_soak_check_refusal(
				tick,
				"install_lens",
				{"object_id": "signal_lens"},
				"QUEST_STAGE_PRECONDITION"
			)
			_soak_episodes_completed += 1


func _soak_check_commit(tick: int, operation: String, arguments: Dictionary, expected_rev: int) -> void:
	var pre_snap: Dictionary = _soak_machine.state.duplicate(true)
	var result := _soak_machine.apply_operation(operation, arguments)
	_soak_commits += 1
	if not bool(result["accepted"]) or int(_soak_machine.state["revision"]) != expected_rev:
		_fail("soak", "tick-%d" % tick, "commit failed for %s rev=%s" % [operation, _soak_machine.state["revision"]])
	var trace: Dictionary = EvaluationTraceScript.reconstruct(_scenario, pre_snap, operation, arguments)
	_soak_trace_checks += 1
	if EvaluationTraceScript.consistent(trace["checks"], result["codes"]):
		_soak_trace_consistent += 1
	else:
		_fail("soak", "tick-%d" % tick, "trace mirror mismatch on commit %s" % operation)


func _soak_check_refusal(tick: int, operation: String, arguments: Dictionary, expected_code: String) -> void:
	var pre_hash := _soak_machine.state_hash()
	var pre_snap: Dictionary = _soak_machine.state.duplicate(true)
	var result := _soak_machine.apply_operation(operation, arguments)
	_soak_refusals += 1
	if not bool(result["accepted"]) and _soak_machine.state_hash() == pre_hash and not bool(result["mutated"]):
		_soak_refusals_isolated += 1
	else:
		_fail("soak", "tick-%d" % tick, "refusal isolation failed for %s" % operation)
	if result["codes"] != [expected_code]:
		_fail("soak", "tick-%d" % tick, "expected [%s], got %s" % [expected_code, result["codes"]])
	for code in result["codes"]:
		_soak_exercised_codes[str(code)] = true
	var trace: Dictionary = EvaluationTraceScript.reconstruct(_scenario, pre_snap, operation, arguments)
	_soak_trace_checks += 1
	if EvaluationTraceScript.consistent(trace["checks"], result["codes"]):
		_soak_trace_consistent += 1
	else:
		_fail("soak", "tick-%d" % tick, "trace mirror mismatch on refusal %s" % expected_code)


func _percentile(values: Array[float], q: float) -> float:
	if values.is_empty():
		return 0.0
	var ordered := values.duplicate()
	ordered.sort()
	var idx := mini(maxi(int(ceil(q * ordered.size())) - 1, 0), ordered.size() - 1)
	return float(ordered[idx])


func _summarize_floats(values: Array[float]) -> Dictionary:
	if values.is_empty():
		return {"count": 0, "min": 0.0, "mean": 0.0, "p50": 0.0, "p95": 0.0, "p99": 0.0, "max": 0.0}
	var total := 0.0
	var lo := INF
	var hi := -INF
	for v in values:
		total += v
		if v < lo:
			lo = v
		if v > hi:
			hi = v
	return {
		"count": values.size(),
		"min": snappedf(lo, 0.001),
		"mean": snappedf(total / float(values.size()), 0.001),
		"p50": snappedf(_percentile(values, 0.50), 0.001),
		"p95": snappedf(_percentile(values, 0.95), 0.001),
		"p99": snappedf(_percentile(values, 0.99), 0.001),
		"max": snappedf(hi, 0.001),
	}


func _summarize_ints(values: Array[int]) -> Dictionary:
	if values.is_empty():
		return {"count": 0, "initial": 0, "min": 0, "max": 0, "final": 0}
	var lo := values[0]
	var hi := values[0]
	for v in values:
		if v < lo:
			lo = v
		if v > hi:
			hi = v
	return {
		"count": values.size(),
		"initial": values[0],
		"min": lo,
		"max": hi,
		"final": values[values.size() - 1],
	}


func _slice_floats(values: Array[float], start_idx: int) -> Array[float]:
	var out: Array[float] = []
	for i in range(maxi(start_idx, 0), values.size()):
		out.append(values[i])
	return out


func _slice_ints(values: Array[int], start_idx: int) -> Array[int]:
	var out: Array[int] = []
	for i in range(maxi(start_idx, 0), values.size()):
		out.append(values[i])
	return out


func _memory_checkpoints() -> Array:
	var indices: Array[int] = [0]
	if _warmup_ticks > 0 and _warmup_ticks < _soak_ticks:
		indices.append(_warmup_ticks - 1)
	var step := maxi(_soak_ticks / 4, 1)
	var cur := step - 1
	while cur < _soak_ticks - 1:
		if cur not in indices:
			indices.append(cur)
		cur += step
	if (_soak_ticks - 1) not in indices:
		indices.append(_soak_ticks - 1)
	indices.sort()
	var rows: Array = []
	for idx in indices:
		rows.append({
			"tick": idx + 1,
			"static_memory_bytes": _static_mem_bytes[idx],
			"object_count": _object_counts[idx],
			"node_count": _node_counts[idx],
			"orphan_node_count": _orphan_counts[idx],
		})
	return rows


func _finalize_and_quit(soak_elapsed_ms: float) -> void:
	var static_all := _summarize_ints(_static_mem_bytes)
	var static_steady := _summarize_ints(_slice_ints(_static_mem_bytes, _warmup_ticks))
	var obj_steady := _summarize_ints(_slice_ints(_object_counts, _warmup_ticks))
	var orphan_all := _summarize_ints(_orphan_counts)
	var node_all := _summarize_ints(_node_counts)

	var rss_delta_kib: Variant = (
		_post_soak_rss_kib - _pre_soak_rss_kib
		if (_pre_soak_rss_kib >= 0 and _post_soak_rss_kib >= 0)
		else null
	)
	var static_steady_delta := int(static_steady["final"]) - int(static_steady["initial"])
	var obj_steady_delta := int(obj_steady["final"]) - int(obj_steady["initial"])

	var soak_exercised_list: Array = _soak_exercised_codes.keys()
	soak_exercised_list.sort()

	var report := {
		"schema_version": "1.0.0",
		"probe_id": PROBE_ID,
		"engineering_only": true,
		"execution_status": "OBSERVED_ENGINE_RUN",
		"claim_boundary": (
			"Headless Godot engine conformance, refusal-code coverage, and deterministic "
			+ "step/commit timing + memory stability soak only. Not evidence for human "
			+ "gameplay, G3/G4/G7, usability, immersion, or LLM efficacy."
		),
		"engine": {
			"name": "Godot",
			"version": Engine.get_version_info()["string"],
			"headless": DisplayServer.get_name() == "headless",
			"display_server": DisplayServer.get_name(),
			"os": OS.get_name(),
		},
		"canonical_terminal_sha256": EXACT_TERMINAL_HASH,
		"refusal_code_coverage": _refusal_battery,
		"soak": {
			"clock": "Time.get_ticks_usec",
			"ticks_executed": _tick_index,
			"warmup_ticks": _warmup_ticks,
			"steady_state_ticks": maxi(_tick_index - _warmup_ticks, 0),
			"cycle_length": 8,
			"episodes_completed": _soak_episodes_completed,
			"total_soak_elapsed_ms": snappedf(soak_elapsed_ms, 0.001),
			"counts": {
				"commits": _soak_commits,
				"refusals": _soak_refusals,
				"refusals_state_isolated": _soak_refusals_isolated,
				"world_events": _soak_world_events,
				"save_loads": _soak_save_loads,
				"trace_checks": _soak_trace_checks,
				"trace_consistent": _soak_trace_consistent,
				"terminal_hash_matches": _soak_terminal_hash_matches,
				"exercised_refusal_codes": soak_exercised_list,
			},
			"timing_ms": {
				"step_commit_all_ticks": _summarize_floats(_step_commit_ms),
				"step_commit_steady_state": _summarize_floats(_slice_floats(_step_commit_ms, _warmup_ticks)),
				"commit_only_operations": _summarize_floats(_commit_only_ms),
				"frame_wall_all_ticks": _summarize_floats(_frame_wall_ms),
				"frame_wall_steady_state": _summarize_floats(_slice_floats(_frame_wall_ms, _warmup_ticks)),
				"headless_frame_delta_all_ticks": _summarize_floats(_frame_delta_ms),
				"headless_frame_delta_steady_state": _summarize_floats(_slice_floats(_frame_delta_ms, _warmup_ticks)),
			},
			"memory": {
				"resident_rss_kib": {
					"pre_refusal_battery": _pre_refusal_rss_kib,
					"pre_soak": _pre_soak_rss_kib,
					"post_soak": _post_soak_rss_kib,
					"soak_delta_kib": rss_delta_kib,
					"soak_delta_mib": (
						snappedf(float(rss_delta_kib) / 1024.0, 0.001)
						if rss_delta_kib != null
						else null
					),
				},
				"godot_static_memory_bytes": {
					"all_ticks": static_all,
					"steady_state": static_steady,
					"steady_state_delta_bytes": static_steady_delta,
					"peak_reported_bytes": int(OS.get_static_memory_peak_usage()),
				},
				"godot_monitors": {
					"object_count_all_ticks": _summarize_ints(_object_counts),
					"object_count_steady_state": obj_steady,
					"object_count_steady_state_delta": obj_steady_delta,
					"node_count": node_all,
					"orphan_node_count": orphan_all,
				},
				"checkpoints": _memory_checkpoints(),
			},
		},
		"passed": _failures.is_empty(),
		"failures": _failures.duplicate(true),
	}

	var absolute_path := ProjectSettings.globalize_path(_output_path)
	var written := _write_json_atomic(absolute_path, report)
	print("SOAK-REFUSAL-PROBE " + JSON.stringify({
		"probe_id": PROBE_ID,
		"engineering_only": true,
		"passed": report["passed"],
		"written": written,
		"path": absolute_path,
		"refusal_exercised": _refusal_battery["exercised_count"],
		"refusal_implemented": _refusal_battery["implemented_count"],
		"soak_ticks": _tick_index,
		"step_commit_p95_ms": report["soak"]["timing_ms"]["step_commit_steady_state"]["p95"],
		"frame_wall_p95_ms": report["soak"]["timing_ms"]["frame_wall_steady_state"]["p95"],
		"rss_delta_kib": rss_delta_kib,
	}))
	get_tree().quit(0 if report["passed"] and written else 1)


func _write_json_atomic(path: String, payload: Dictionary) -> bool:
	var parent := path.get_base_dir()
	if parent != "" and DirAccess.make_dir_recursive_absolute(parent) != OK:
		push_error("Cannot create probe directory: " + parent)
		return false
	var temporary_path := path + ".tmp"
	if FileAccess.file_exists(temporary_path):
		DirAccess.remove_absolute(temporary_path)
	var handle := FileAccess.open(temporary_path, FileAccess.WRITE)
	if handle == null:
		push_error("Cannot open temporary probe file: " + temporary_path)
		return false
	handle.store_string(JSON.stringify(CanonicalState.canonicalize(payload), "  ") + "\n")
	handle.flush()
	handle.close()
	if DirAccess.rename_absolute(temporary_path, path) != OK:
		push_error("Atomic probe rename failed: %s -> %s" % [temporary_path, path])
		return false
	return true
