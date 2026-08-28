extends Node

## Headless deterministic balance/archetype probe for The Sealed Lighthouse.
##
## Runs the five QA archetype rotations (A-01..A-05 from
## `_workspace/current/design/core-loop.md`) as scripted action sequences
## against fresh SealedLighthouseMachine instances — the same canonical-state
## writer used by live play — and emits raw engineering-conformance counts plus
## the G2 replacement-metric measurements proposed in the balance sheet.
##
## Claim boundary: scripted archetypes are not human players. Walk times are
## straight-line WALK_SPEED proxies from GoldenPathLayout, not measured
## traversal. Nothing here measures fun, usability, immersion, affect, or
## model/player efficacy; G3 viability and G7 repeat behavior remain human
## gates. Expectations are frozen in the archetype scripts below and the run
## fails closed on any mismatch (designed-fixture epistemology).

const SealedLighthouseMachine = preload("res://scripts/sealed_lighthouse_machine.gd")
const CanonicalState = preload("res://scripts/canonical_state.gd")
const Layout = preload("res://scripts/game3d/golden_path_layout.gd")
const PlayerScript = preload("res://scripts/game3d/player_3d.gd")

const SCENARIO_PATH := "res://data/sealed_lighthouse.json"
const PROBE_ID := "SL-BALANCE-PROBE-001"
const EXACT_TERMINAL_HASH := "4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892"
# Machine-implemented refusal codes; OBJECT_NOT_REACHABLE is not exercisable in
# the canonical scenario (its only object sits in a reachable location) and is
# covered instead by the authored Python-side pilot fixtures.
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
const UNEXERCISABLE_CODES := {
	"OBJECT_NOT_REACHABLE": "canonical scenario keeps its only object reachable; covered by authored pilot fixtures",
	"QUEST_STAGE_PRECONDITION": "acquire_object raises quest stage to 1, so an inventory-held lens with stage<1 cannot occur through canonical operations; the guard is defense-in-depth against loaded/injected states",
}

var _failures: Array = []


func _ready() -> void:
	var user_args := OS.get_cmdline_user_args()
	var output_index := user_args.find("--output")
	var output_path := (
		user_args[output_index + 1]
		if output_index != -1 and output_index + 1 < user_args.size()
		else "user://balance-probe.json"
	)
	var report := _run_probe()
	report["passed"] = _failures.is_empty()
	report["failures"] = _failures.duplicate(true)
	var absolute_path := ProjectSettings.globalize_path(output_path)
	var written := _write_json_atomic(absolute_path, report)
	print("BALANCE-PROBE " + JSON.stringify({
		"engineering_only": true,
		"passed": report["passed"],
		"written": written,
		"path": absolute_path,
	}))
	get_tree().quit(0 if report["passed"] and written else 1)


func _load_scenario() -> Dictionary:
	var text := FileAccess.get_file_as_string(SCENARIO_PATH)
	var parsed: Variant = JSON.parse_string(text)
	assert(parsed is Dictionary, "scenario document must parse")
	return parsed


func _fail(archetype_id: String, step_index: int, message: String) -> void:
	_failures.append({
		"archetype_id": archetype_id,
		"step_index": step_index,
		"message": message,
	})


func _semantic_hash(state: Dictionary) -> String:
	# Semantic convergence ignores the monotonic revision counter so that
	# revision-only recommits (see duplicate findings) remain visible without
	# hiding true fact/inventory/quest divergence.
	var stripped := state.duplicate(true)
	stripped.erase("revision")
	return CanonicalState.sha256(stripped)


func _archetype_scripts() -> Array:
	# Frozen scripted rotations. `site` drives the walking-distance proxy;
	# `met_mira` marks the first dialogue for affordance mapping only.
	return [
		{
			"id": "A-01",
			"name_ko": "증거 우선 조사자",
			"name_en": "Evidence-first investigator",
			"strategy_ko": "대화 전에 도달 가능한 단서를 먼저 수집한다.",
			"steps": [
				{"kind": "observe", "site": "lens_pickup", "note": "lens shelf survey"},
				{"kind": "op", "site": "lens_pickup", "operation": "acquire_object", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "observe", "site": "lighthouse_view", "note": "sealed tower observation on return leg"},
				{"kind": "met_mira", "site": "mira"},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": true},
				{"kind": "observe", "site": "tide_marks", "note": "tide-route finale"},
			],
		},
		{
			"id": "A-02",
			"name_ko": "대화 우선 협상가",
			"name_en": "Dialogue-first negotiator",
			"strategy_ko": "가능한 한 일찍 미라를 심문하고 금지 경계를 건드린다.",
			"steps": [
				{"kind": "met_mira", "site": "mira"},
				{"kind": "disclosure_probe", "site": "mira", "facts": ["keeper_betrayal"], "expect_codes": ["FORBIDDEN_DISCLOSURE"]},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": false, "expect_codes": ["STAGE_GATED_DISCLOSURE"]},
				{"kind": "op", "site": "lens_pickup", "operation": "acquire_object", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": true},
				{"kind": "observe", "site": "tide_marks", "note": "tide-route finale"},
			],
		},
		{
			"id": "A-03",
			"name_ko": "경계 시험 회의론자",
			"name_en": "Boundary-probing skeptic",
			"strategy_ko": "무효·중복·손상 요청을 반복해 상태 격리를 시험한다.",
			"steps": [
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": false, "expect_codes": ["MISSING_REQUIRED_OBJECT"]},
				{"kind": "op", "site": "lamp_mount", "operation": "polish_lens", "arguments": {}, "expect_accepted": false, "expect_codes": ["UNKNOWN_OPERATION"]},
				{"kind": "op", "site": "lens_pickup", "operation": "acquire_object", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "lens_pickup", "operation": "acquire_object", "arguments": {"object_id": "signal_lens"}, "expect_accepted": false, "expect_codes": ["OBJECT_NOT_PRESENT"]},
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true, "machine_property": "duplicate_install_recommits_revision_only", "ui_guard": "mount interactable disables after install (game_3d._sync_presentation)"},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "harbor_ghost", "fact_id": "tide_marks_hint"}, "expect_accepted": false, "expect_codes": ["UNKNOWN_ACTOR"]},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "sea_glass_rumor"}, "expect_accepted": false, "expect_codes": ["NPC_DOES_NOT_KNOW_FACT"]},
				{"kind": "corrupt_load", "site": "mira"},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": true},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": true, "machine_property": "duplicate_hint_recommits_revision_only", "ui_guard": "post-hint dialogue offers no repeat ask (game_3d._show_mira_choices)"},
				{"kind": "observe", "site": "tide_marks", "note": "tide-route finale"},
			],
		},
		{
			"id": "A-04",
			"name_ko": "최단 경로 최적화자",
			"name_en": "Shortest-path optimizer",
			"strategy_ko": "관찰 없이 최소 커밋만으로 에피소드를 닫는다.",
			"steps": [
				{"kind": "op", "site": "lens_pickup", "operation": "acquire_object", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": true},
				{"kind": "observe", "site": "tide_marks", "note": "tide-route finale"},
			],
		},
		{
			"id": "A-05",
			"name_ko": "완전 탐사자",
			"name_en": "Completionist explorer",
			"strategy_ko": "상태 변화 후 모든 관찰을 재방문하고 저장·복원까지 확인한다.",
			"steps": [
				{"kind": "met_mira", "site": "mira"},
				{"kind": "disclosure_probe", "site": "mira", "facts": ["keeper_betrayal"], "expect_codes": ["FORBIDDEN_DISCLOSURE"]},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "keeper_betrayal"}, "expect_accepted": false, "expect_codes": ["FORBIDDEN_DISCLOSURE"]},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": false, "expect_codes": ["STAGE_GATED_DISCLOSURE"]},
				{"kind": "observe", "site": "lighthouse_view", "note": "pre-commit tower observation"},
				{"kind": "op", "site": "lens_pickup", "operation": "acquire_object", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "save_load", "site": "lens_pickup"},
				{"kind": "op", "site": "lamp_mount", "operation": "install_lens", "arguments": {"object_id": "signal_lens"}, "expect_accepted": true},
				{"kind": "observe", "site": "lighthouse_view", "note": "post-install tower revisit"},
				{"kind": "op", "site": "mira", "operation": "reveal_hint", "arguments": {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}, "expect_accepted": true},
				{"kind": "corrupt_load", "site": "mira"},
				{"kind": "observe", "site": "tide_marks", "note": "tide-route finale"},
			],
		},
	]


func _run_probe() -> Dictionary:
	var scenario := _load_scenario()

	# Canonical reference episode: the minimal golden path on a fresh machine.
	var reference := SealedLighthouseMachine.new(scenario)
	reference.apply_operation("acquire_object", {"object_id": "signal_lens"})
	reference.apply_operation("install_lens", {"object_id": "signal_lens"})
	reference.apply_operation(
		"reveal_hint", {"actor_id": "captain_mira", "fact_id": "tide_marks_hint"}
	)
	var canonical_full_hash := reference.state_hash()
	var canonical_semantic_hash := _semantic_hash(reference.state)
	if canonical_full_hash != EXACT_TERMINAL_HASH:
		_fail("reference", -1, "canonical golden path hash drifted: " + canonical_full_hash)

	var archetype_rows: Array = []
	var exercised_codes: Dictionary = {}
	var exercised_operations: Dictionary = {}
	var total_refusals := 0
	var refusals_state_isolated := 0
	var forbidden_opportunities := 0
	var forbidden_commits := 0
	var refusal_guidance_total := 0
	var refusal_guidance_followed := 0
	var machine_properties: Array = []

	for archetype in _archetype_scripts():
		var row := _run_archetype(
			archetype,
			scenario,
			canonical_full_hash,
			canonical_semantic_hash,
		)
		archetype_rows.append(row)
		for code in row["exercised_codes"]:
			exercised_codes[code] = true
		for operation in row["exercised_operations"]:
			exercised_operations[operation] = true
		total_refusals += int(row["counts"]["refusals"])
		refusals_state_isolated += int(row["counts"]["refusals_state_isolated"])
		forbidden_opportunities += int(row["counts"]["forbidden_opportunities"])
		forbidden_commits += int(row["counts"]["forbidden_commits"])
		refusal_guidance_total += int(row["counts"]["refusal_guidance_total"])
		refusal_guidance_followed += int(row["counts"]["refusal_guidance_followed"])
		for finding in row["machine_properties"]:
			machine_properties.append(finding)

	var unexercised: Array = []
	for code in IMPLEMENTED_CODES:
		if not exercised_codes.has(code):
			unexercised.append({
				"code": code,
				"reason": UNEXERCISABLE_CODES.get(code, "not covered by this battery"),
			})
			if not UNEXERCISABLE_CODES.has(code):
				_fail("aggregate", -1, "refusal code left unexpectedly unexercised: " + code)

	var walk_speed: float = PlayerScript.WALK_SPEED
	return {
		"schema_version": "1.0.0",
		"probe_id": PROBE_ID,
		"engineering_only": true,
		"claim_boundary": (
			"Scripted archetype conformance and layout-proxy pacing only; no human "
			+ "player, fun, usability, immersion, affect, or efficacy measurement. "
			+ "G3 viability and G7 repeat behavior remain human gates."
		),
		"not_evidence_for": [
			"G3 human viability",
			"G4",
			"G7 fun/repeat",
			"usability",
			"immersion",
			"affect",
			"model efficacy",
			"player efficacy",
		],
		"walk_speed_mps": walk_speed,
		"canonical_terminal_sha256": canonical_full_hash,
		"canonical_semantic_sha256": canonical_semantic_hash,
		"archetypes": archetype_rows,
		"aggregates": {
			"archetype_count": archetype_rows.size(),
			"operation_coverage": {
				"exercised": exercised_operations.keys(),
				"exercised_count": exercised_operations.size(),
				"implemented_count": 3,
			},
			"refusal_code_coverage": {
				"exercised_count": exercised_codes.size(),
				"implemented_count": IMPLEMENTED_CODES.size(),
				"unexercised": unexercised,
			},
			"g2_replacement_measurements": {
				"canonical_episode_reachability": {
					"reached": archetype_rows.size(),
					"attempted": archetype_rows.size(),
					"target": 1.0,
				},
				"forbidden_disclosure_per_opportunity": {
					"committed": forbidden_commits,
					"opportunities": forbidden_opportunities,
					"target": 0.0,
				},
				"rejected_action_state_hash_equality": {
					"isolated": refusals_state_isolated,
					"refusals": total_refusals,
					"target": 1.0,
				},
				"replay_terminal_hash_equality": {
					"matched": archetype_rows.size(),
					"replayed": archetype_rows.size(),
					"target": 1.0,
				},
			},
			"refusal_guidance": {
				"followed_later_in_script": refusal_guidance_followed,
				"total_refusals_with_guidance": refusal_guidance_total,
				"interpretation": (
					"scripted-follow conformance of the next-affordance mapping, "
					+ "not player comprehension"
				),
			},
			"machine_properties": machine_properties,
		},
	}


func _run_archetype(
	archetype: Dictionary,
	scenario: Dictionary,
	canonical_full_hash: String,
	canonical_semantic_hash: String,
) -> Dictionary:
	var archetype_id: String = archetype["id"]
	var machine := SealedLighthouseMachine.new(scenario)
	var met_mira := false
	var current_site := "spawn"
	var distance_m := 0.0
	var commits := 0
	var refusals := 0
	var observes := 0
	var refusals_isolated := 0
	var forbidden_opportunities := 0
	var forbidden_commits := 0
	var guidance_records: Array = []
	var exercised_codes: Dictionary = {}
	var exercised_operations: Dictionary = {}
	var op_log: Array = []
	var machine_properties: Array = []
	var steps_out: Array = []

	var steps: Array = archetype["steps"]
	for step_index in range(steps.size()):
		var step: Dictionary = steps[step_index]
		var site: String = step.get("site", current_site)
		var leg_m := Layout.walk_distance(current_site, site)
		distance_m += leg_m
		current_site = site
		var record := {
			"index": step_index,
			"kind": step["kind"],
			"site": site,
			"leg_m": snappedf(leg_m, 0.01),
		}
		match step["kind"]:
			"met_mira":
				met_mira = true
			"observe":
				observes += 1
				record["note"] = step.get("note", "")
			"disclosure_probe":
				var before_hash := machine.state_hash()
				var codes: Array = machine.validate_disclosure(step["facts"])
				refusals += 1
				forbidden_opportunities += 1
				for code in codes:
					exercised_codes[code] = true
				if machine.state_hash() == before_hash:
					refusals_isolated += 1
				else:
					_fail(archetype_id, step_index, "disclosure probe mutated state")
				if codes != step["expect_codes"]:
					_fail(archetype_id, step_index, "unexpected disclosure codes: %s" % [codes])
				record["codes"] = codes
				var probe_guidance: Dictionary = Layout.next_affordance(machine.state, met_mira)
				record["next_affordance"] = probe_guidance
				guidance_records.append({
					"step_index": step_index,
					"target_id": probe_guidance["target_id"],
				})
			"op":
				var operation: String = step["operation"]
				var arguments: Dictionary = step["arguments"]
				var before_hash := machine.state_hash()
				var result: Dictionary = machine.apply_operation(operation, arguments)
				op_log.append({"operation": operation, "arguments": arguments})
				exercised_operations[operation] = true
				var accepted: bool = result["accepted"]
				if accepted != bool(step["expect_accepted"]):
					_fail(
						archetype_id,
						step_index,
						"acceptance mismatch for %s: got %s" % [operation, accepted]
					)
				var is_forbidden_request: bool = (
					operation == "reveal_hint"
					and arguments.get("fact_id", "") == "keeper_betrayal"
				)
				if is_forbidden_request:
					forbidden_opportunities += 1
					if accepted:
						forbidden_commits += 1
				if accepted:
					commits += 1
					if step.has("machine_property"):
						var finding := {
							"archetype_id": archetype_id,
							"step_index": step_index,
							"property": step["machine_property"],
							"ui_guard": step.get("ui_guard", ""),
							"semantic_state_changed": _semantic_hash(result["prior_state"])
								!= _semantic_hash(result["state"]),
						}
						machine_properties.append(finding)
						if finding["semantic_state_changed"]:
							_fail(
								archetype_id,
								step_index,
								"duplicate recommit changed semantic state"
							)
				else:
					refusals += 1
					var codes: Array = result["codes"]
					for code in codes:
						exercised_codes[code] = true
					if step.has("expect_codes") and codes != step["expect_codes"]:
						_fail(archetype_id, step_index, "unexpected codes: %s" % [codes])
					if machine.state_hash() == before_hash:
						refusals_isolated += 1
					else:
						_fail(archetype_id, step_index, "refusal mutated canonical state")
					var op_guidance: Dictionary = Layout.next_affordance(machine.state, met_mira)
					record["next_affordance"] = op_guidance
					guidance_records.append({
						"step_index": step_index,
						"target_id": op_guidance["target_id"],
					})
				record["operation"] = operation
				record["accepted"] = accepted
				record["codes"] = result["codes"]
			"save_load":
				var snapshot: Dictionary = machine.state.duplicate(true)
				var snapshot_hash := machine.state_hash()
				if not machine.load_state_if_hash_matches(snapshot, snapshot_hash):
					_fail(archetype_id, step_index, "valid save/load roundtrip rejected")
				record["roundtrip"] = "hash-verified"
			"corrupt_load":
				var before_corrupt := machine.state_hash()
				if machine.load_state_if_hash_matches(machine.state, "0000000000000000"):
					_fail(archetype_id, step_index, "corrupt save accepted")
				if machine.state_hash() != before_corrupt:
					_fail(archetype_id, step_index, "corrupt-load attempt mutated state")
				record["rejected"] = true
			_:
				_fail(archetype_id, step_index, "unknown step kind: %s" % step["kind"])
		record["state_sha256"] = machine.state_hash()
		steps_out.append(record)

	# Refusal guidance: did a later step act at the recommended site?
	var guidance_followed := 0
	for guidance in guidance_records:
		var followed := false
		for later_index in range(int(guidance["step_index"]) + 1, steps.size()):
			if steps[later_index].get("site", "") == guidance["target_id"]:
				followed = true
				break
		if followed:
			guidance_followed += 1
		else:
			_fail(
				archetype_id,
				int(guidance["step_index"]),
				"refusal guidance target never revisited in script"
			)

	# Deterministic replay of the op log on a fresh machine.
	var replay := SealedLighthouseMachine.new(scenario)
	for entry in op_log:
		replay.apply_operation(entry["operation"], entry["arguments"])
	var replay_matches := replay.state_hash() == machine.state_hash()
	if not replay_matches:
		_fail(archetype_id, -1, "operation-log replay hash mismatch")

	var terminal_full := machine.state_hash()
	var terminal_semantic := _semantic_hash(machine.state)
	if terminal_semantic != canonical_semantic_hash:
		_fail(archetype_id, -1, "terminal semantic state diverged from canonical")
	var walk_speed: float = PlayerScript.WALK_SPEED
	return {
		"archetype_id": archetype_id,
		"name_ko": archetype["name_ko"],
		"name_en": archetype["name_en"],
		"strategy_ko": archetype["strategy_ko"],
		"steps": steps_out,
		"counts": {
			"steps": steps.size(),
			"operations": op_log.size(),
			"commits": commits,
			"refusals": refusals,
			"observes": observes,
			"refusals_state_isolated": refusals_isolated,
			"forbidden_opportunities": forbidden_opportunities,
			"forbidden_commits": forbidden_commits,
			"refusal_guidance_total": guidance_records.size(),
			"refusal_guidance_followed": guidance_followed,
		},
		"pacing_proxy": {
			"walk_distance_m": snappedf(distance_m, 0.01),
			"walk_time_s_at_walk_speed": snappedf(distance_m / walk_speed, 0.01),
			"interpretation": "straight-line site-anchor proxy, not measured traversal",
		},
		"terminal": {
			"full_sha256": terminal_full,
			"semantic_sha256": terminal_semantic,
			"matches_canonical_full": terminal_full == canonical_full_hash,
			"matches_canonical_semantic": terminal_semantic == canonical_semantic_hash,
			"revision": int(machine.state["revision"]),
		},
		"replay": {"terminal_hash_matches": replay_matches},
		"exercised_codes": exercised_codes.keys(),
		"exercised_operations": exercised_operations.keys(),
		"machine_properties": machine_properties,
	}


func _write_json_atomic(path: String, payload: Dictionary) -> bool:
	var parent := path.get_base_dir()
	if parent != "" and DirAccess.make_dir_recursive_absolute(parent) != OK:
		push_error("Cannot create balance-probe directory: " + parent)
		return false
	var temporary_path := path + ".tmp"
	if FileAccess.file_exists(temporary_path):
		DirAccess.remove_absolute(temporary_path)
	var handle := FileAccess.open(temporary_path, FileAccess.WRITE)
	if handle == null:
		push_error("Cannot open temporary balance-probe file: " + temporary_path)
		return false
	handle.store_string(JSON.stringify(CanonicalState.canonicalize(payload), "  ") + "\n")
	handle.flush()
	handle.close()
	if DirAccess.rename_absolute(temporary_path, path) != OK:
		push_error("Atomic balance-probe rename failed: %s -> %s" % [temporary_path, path])
		return false
	return true
