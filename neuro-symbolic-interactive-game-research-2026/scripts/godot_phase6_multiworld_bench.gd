extends SceneTree

# Phase-6 P19 Authentic Multi-World & Large-Scale Godot 4.7.1 Runtime Engine Benchmark
# Executes P19A (120 multi-hop cases + 5 multi-turn world episodes) and
# P19B (5 procedural RPG scale tiers x 1000 ticks = 5,000 authentic ticks).

func _init() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() < 2:
		push_error("Usage: godot --headless -s res://godot_phase6_multiworld_bench.gd -- <in.json> <out.json>")
		quit(1)
		return

	var in_path: String = args[0]
	var out_path: String = args[1]

	var file := FileAccess.open(in_path, FileAccess.READ)
	if file == null:
		push_error("Failed to open input JSON: " + in_path)
		quit(2)
		return

	var text: String = file.get_as_text()
	file.close()

	var parse_res = JSON.parse_string(text)
	if parse_res == null or typeof(parse_res) != TYPE_DICTIONARY:
		push_error("Failed to parse JSON input payload from: " + in_path)
		quit(3)
		return

	var payload: Dictionary = parse_res
	var results: Dictionary = {}

	# Record Godot version info
	var v_info := Engine.get_version_info()
	results["godot_version"] = "%d.%d.%d" % [v_info.get("major", 4), v_info.get("minor", 0), v_info.get("patch", 0)]
	results["godot_version_string"] = Engine.get_version_info().get("string", "4.x")
	results["engine_name"] = "godot"

	# Execute P19A
	var p19a_res := _run_p19a(payload)
	results["p19a"] = p19a_res

	# Execute P19B
	var p19b_res := _run_p19b(payload)
	results["p19b"] = p19b_res

	# Save output JSON
	var out_file := FileAccess.open(out_path, FileAccess.WRITE)
	if out_file == null:
		push_error("Failed to open output JSON for writing: " + out_path)
		quit(4)
		return

	out_file.store_string(JSON.stringify(results, "  "))
	out_file.close()
	quit(0)


# ==============================================================================
# Runtime Logic: Transitive Closure, Multi-hop Eval, 7-Predicate Step & Rho
# ==============================================================================

# Semi-naive fixpoint transitive closure
func _transitive_closure(seeds: Array, adj: Dictionary) -> Dictionary:
	var visited: Dictionary = {}
	var frontier: Array = []
	for s in seeds:
		var k := str(s)
		visited[k] = true
		frontier.append(k)

	while frontier.size() > 0:
		var curr = frontier.pop_back()
		if adj.has(curr):
			var neighbors: Array = adj[curr]
			for n in neighbors:
				var n_str := str(n)
				if not visited.has(n_str):
					visited[n_str] = true
					frontier.append(n_str)
	return visited


func _eval_multihop_case(spec: Dictionary, actor: String, fact: String, quest_stage: int) -> Dictionary:
	var role_parents: Dictionary = spec.get("role_parents", {})
	var fact_implications: Dictionary = spec.get("fact_implications", {})
	var forbidden_by_role: Dictionary = spec.get("forbidden_by_role", {})
	var min_stage_by_fact: Dictionary = spec.get("min_stage_by_fact", {})

	# Transitive role closure: role_closure = {actor} U ancestors(actor)
	var role_closure: Dictionary = _transitive_closure([actor], role_parents)

	# Transitive fact closure: derived_facts = {fact} U implied(fact)
	var derived_facts: Dictionary = _transitive_closure([fact], fact_implications)

	# Effective forbidden facts across all inherited roles
	var effective_forbidden: Dictionary = {}
	for r in role_closure.keys():
		var f_list: Array = forbidden_by_role.get(str(r), [])
		for f_item in f_list:
			effective_forbidden[str(f_item)] = true

	var leaked_roots: Array = []
	var required_min_stage := 0
	for df in derived_facts.keys():
		var df_str := str(df)
		if effective_forbidden.has(df_str):
			leaked_roots.append(df_str)
		var st := int(min_stage_by_fact.get(df_str, 0))
		if st > required_min_stage:
			required_min_stage = st

	leaked_roots.sort()
	var deny := (leaked_roots.size() > 0) or (required_min_stage > quest_stage)

	return {
		"deny": deny,
		"leaked_roots": leaked_roots,
		"required_min_stage": required_min_stage
	}



# Sort an Array of strings deterministically
func _sort_array(arr: Array) -> Array:
	var sorted := arr.duplicate()
	sorted.sort()
	return sorted


# Computes deterministic SHA-256 string for canonical state dict
func _hash_state(state: Dictionary) -> String:
	# Convert state to a normalized JSON string with sorted keys
	var canonical_keys := state.keys()
	canonical_keys.sort()
	var normalized: Dictionary = {}
	for k in canonical_keys:
		var v = state[k]
		if typeof(v) == TYPE_ARRAY:
			var sorted_v = v.duplicate()
			sorted_v.sort()
			normalized[k] = sorted_v
		elif typeof(v) == TYPE_DICTIONARY:
			var sub_keys = v.keys()
			sub_keys.sort()
			var sub_norm: Dictionary = {}
			for sk in sub_keys:
				sub_norm[sk] = v[sk]
			normalized[k] = sub_norm
		else:
			normalized[k] = v

	var json_str := JSON.stringify(normalized)
	var ctx := HashingContext.new()
	ctx.start(HashingContext.HASH_SHA256)
	ctx.update(json_str.to_utf8_buffer())
	var digest := ctx.finish()
	return digest.hex_encode()


# 7 Predicates validation + bounded state-blind repair rho
# Returns:
# {
#   "valid": bool,
#   "rho_repaired": bool,
#   "blocked_leak": bool,
#   "reasons": Array,
#   "committed_action": Dictionary,
#   "new_state": Dictionary
# }
func _validate_and_step(state: Dictionary, spec: Dictionary, action: Dictionary) -> Dictionary:
	var act := action.duplicate(true)
	var reasons: Array = []
	var rho_repaired := false
	var blocked_leak := false

	var action_type: String = act.get("type", "unknown")
	var actor: String = act.get("actor", "")
	var quest_stage: int = int(state.get("quest_stage", 0))

	# 1. Policy check: action_type must be supported
	var allowed_actions: Array = spec.get("allowed_actions", ["move", "examine", "talk", "disclose", "unlock", "take", "cast"])
	if not allowed_actions.has(action_type):
		return {
			"valid": false,
			"rho_repaired": false,
			"blocked_leak": false,
			"reasons": ["unsupported_action_type: " + action_type],
			"committed_action": {},
			"new_state": state
		}

	# 2. Preconditions check
	var actor_loc: String = state.get("actor_locations", {}).get(actor, "")
	var target_loc: String = act.get("target_location", "")
	if action_type == "move":
		if target_loc == "":
			reasons.append("missing_target_location")
		else:
			var adj_locs: Array = spec.get("location_adjacency", {}).get(actor_loc, [])
			if not adj_locs.has(target_loc):
				reasons.append("unreachable_location: " + target_loc + " from " + actor_loc)

	# 3. Object reachability check
	var target_obj: String = act.get("target_object", "")
	if target_obj != "":
		var obj_loc: String = state.get("object_locations", {}).get(target_obj, "")
		var held_by: String = actor if state.get("inventory", {}).get(actor, []).has(target_obj) else ""

		if obj_loc != actor_loc and held_by != actor:
			reasons.append("unreachable_object: " + target_obj)

	# 4. NPC knowledge check
	var target_npc: String = act.get("target_npc", "")
	if target_npc != "":
		var npc_loc: String = state.get("npc_locations", {}).get(target_npc, "")
		if npc_loc != actor_loc:
			reasons.append("npc_not_in_room: " + target_npc)

	# 5. Transitive forbidden_disclosure via multihop check
	var disclosed: Array = act.get("disclosed_facts", [])
	var filtered_disclosed: Array = []
	for fact in disclosed:
		var f_str := str(fact)
		var eval_res := _eval_multihop_case(spec, actor, f_str, quest_stage)
		if eval_res["deny"]:
			blocked_leak = true
			reasons.append("forbidden_disclosure_leak: " + f_str)
		else:
			filtered_disclosed.append(f_str)

	# Bounded state-blind repair rho: if disclosure failed, rho strips forbidden facts
	if blocked_leak:
		if filtered_disclosed.size() > 0 or action_type != "disclose":
			# rho repair succeeds by dropping forbidden facts
			act["disclosed_facts"] = filtered_disclosed
			rho_repaired = true
			reasons.clear()
		else:
			# If disclose has 0 valid facts remaining, it is blocked completely
			return {
				"valid": false,
				"rho_repaired": false,
				"blocked_leak": true,
				"reasons": reasons,
				"committed_action": {},
				"new_state": state
			}

	# Clamp unauthorized extra effects (rho repair on effect fields)
	var effects: Dictionary = act.get("effects", {})
	if effects.size() > 0:
		var valid_effects: Dictionary = {}
		var allowed_effect_keys: Array = spec.get("allowed_effect_keys", ["add_inventory", "set_flag", "advance_stage"])
		for ek in effects.keys():
			if allowed_effect_keys.has(ek):
				valid_effects[ek] = effects[ek]
			else:
				rho_repaired = true
		act["effects"] = valid_effects

	# 6. Quest stage requirement check on action
	var req_stage: int = int(act.get("required_min_stage", 0))
	if quest_stage < req_stage:
		reasons.append("quest_stage_insufficient: " + str(quest_stage) + " < " + str(req_stage))

	# 7. Monotonicity check: cannot revoke immutable facts or decrement quest_stage
	var advance: int = int(act.get("effects", {}).get("advance_stage", 0))
	if advance < 0:
		reasons.append("monotonicity_violation_negative_advance")

	if reasons.size() > 0:
		return {
			"valid": false,
			"rho_repaired": rho_repaired,
			"blocked_leak": blocked_leak,
			"reasons": reasons,
			"committed_action": {},
			"new_state": state
		}

	# Re-validation passed: apply committed step to canonical state
	var next_state := state.duplicate(true)

	if action_type == "move" and target_loc != "":
		var locs: Dictionary = next_state.get("actor_locations", {}).duplicate()
		locs[actor] = target_loc
		next_state["actor_locations"] = locs

	if act.get("disclosed_facts", []).size() > 0:
		var current_disc: Array = next_state.get("known_disclosed_facts", []).duplicate()
		for f in act["disclosed_facts"]:
			if not current_disc.has(f):
				current_disc.append(f)
		next_state["known_disclosed_facts"] = current_disc

	var effs: Dictionary = act.get("effects", {})
	if effs.has("advance_stage"):
		next_state["quest_stage"] = quest_stage + int(effs["advance_stage"])

	if effs.has("set_flag"):
		var flags: Dictionary = next_state.get("flags", {}).duplicate()
		flags[str(effs["set_flag"])] = true
		next_state["flags"] = flags

	if effs.has("add_inventory"):
		var inv: Dictionary = next_state.get("inventory", {}).duplicate()
		var actor_inv: Array = inv.get(actor, []).duplicate()
		actor_inv.append(str(effs["add_inventory"]))
		inv[actor] = actor_inv
		next_state["inventory"] = inv

	return {
		"valid": true,
		"rho_repaired": rho_repaired,
		"blocked_leak": blocked_leak,
		"reasons": [],
		"committed_action": act,
		"new_state": next_state
	}


# ==============================================================================
# P19A: 120 Multi-Hop Cases + 5 World Episodes
# ==============================================================================

func _run_p19a(payload: Dictionary) -> Dictionary:
	var cases: Array = payload.get("p19a_cases", [])
	var ontology: Dictionary = payload.get("p19a_ontology", {})
	var episodes: Dictionary = payload.get("p19a_world_episodes", {})

	var evaluated_cases: Array = []
	var t_start_all := Time.get_ticks_usec()

	for c in cases:
		var actor: String = c.get("actor", "guest")
		var fact: String = c.get("fact", "")
		var stage: int = int(c.get("quest_stage", 0))

		var t0 := Time.get_ticks_usec()
		var res := _eval_multihop_case(ontology, actor, fact, stage)
		var t1 := Time.get_ticks_usec()

		evaluated_cases.append({
			"id": c.get("id", ""),
			"world": c.get("world", ""),
			"actor": actor,
			"fact": fact,
			"quest_stage": stage,
			"deny": res["deny"],
			"leaked_roots": res["leaked_roots"],
			"required_min_stage": res["required_min_stage"],
			"ticks_usec": (t1 - t0)
		})

	var t_cases_total := Time.get_ticks_usec() - t_start_all

	# Run 5 world multi-turn episodes
	var world_episode_results: Dictionary = {}
	for world_id in episodes.keys():
		var ep_data: Dictionary = episodes[world_id]
		var initial_state: Dictionary = ep_data.get("initial_state", {})
		var spec: Dictionary = ep_data.get("spec", {})
		var actions: Array = ep_data.get("actions", [])

		var curr_state := initial_state.duplicate(true)
		var commits := 0
		var rho_repairs := 0
		var blocked_leaks := 0
		var unsafe_commits := 0
		var leaks_committed := 0

		for a in actions:
			var step_res := _validate_and_step(curr_state, spec, a)
			if step_res["rho_repaired"]:
				rho_repairs += 1
			if step_res["blocked_leak"]:
				blocked_leaks += 1

			if step_res["valid"]:
				commits += 1
				curr_state = step_res["new_state"]
				# Verify safety invariant post-commit
				var disclosed: Array = step_res["committed_action"].get("disclosed_facts", [])
				for df in disclosed:
					var chk := _eval_multihop_case(spec, step_res["committed_action"].get("actor", ""), df, curr_state.get("quest_stage", 0))
					if chk["deny"]:
						unsafe_commits += 1
						leaks_committed += 1
			else:
				# Blocked action
				pass

		var term_sha := _hash_state(curr_state)
		world_episode_results[world_id] = {
			"actions_count": actions.size(),
			"commits": commits,
			"rho_repairs": rho_repairs,
			"blocked_leaks": blocked_leaks,
			"unsafe_commits": unsafe_commits,
			"leaks_committed": leaks_committed,
			"terminal_state_sha256": term_sha,
			"terminal_state": curr_state
		}

	return {
		"cases_count": evaluated_cases.size(),
		"cases_total_usec": t_cases_total,
		"cases": evaluated_cases,
		"world_episodes": world_episode_results
	}


# ==============================================================================
# P19B: 5 Procedural RPG Scale Tiers x 1000 Ticks = 5,000 Ticks Benchmark
# ==============================================================================

func _run_p19b(payload: Dictionary) -> Dictionary:
	var tiers: Array = payload.get("p19b_tiers", [])
	var tier_results: Dictionary = {}
	var grand_total_ticks := 0
	var grand_total_usec := 0

	for tier_spec in tiers:
		var name: String = tier_spec.get("name", "tier")
		var num_rooms: int = int(tier_spec.get("rooms", 8))
		var num_actors: int = int(tier_spec.get("actors", 3))
		var depth: int = int(tier_spec.get("depth", 2))
		var num_ticks: int = int(tier_spec.get("ticks", 1000))
		var spec: Dictionary = tier_spec.get("spec", {})
		var initial_state: Dictionary = tier_spec.get("initial_state", {})
		var trace_actions: Array = tier_spec.get("trace_actions", [])

		var curr_state := initial_state.duplicate(true)
		var commits := 0
		var rho_repairs := 0
		var blocked_leaks := 0
		var unsafe_commits := 0
		var leaks_committed := 0

		var latencies_usec: Array = []
		var t_tier_start := Time.get_ticks_usec()

		for i in range(num_ticks):
			var a: Dictionary = trace_actions[i]
			var t0 := Time.get_ticks_usec()
			var step_res := _validate_and_step(curr_state, spec, a)
			var t1 := Time.get_ticks_usec()
			latencies_usec.append(t1 - t0)

			if step_res["rho_repaired"]:
				rho_repairs += 1
			if step_res["blocked_leak"]:
				blocked_leaks += 1

			if step_res["valid"]:
				commits += 1
				curr_state = step_res["new_state"]
				var disc: Array = step_res["committed_action"].get("disclosed_facts", [])
				for df in disc:
					var chk := _eval_multihop_case(spec, step_res["committed_action"].get("actor", ""), df, curr_state.get("quest_stage", 0))
					if chk["deny"]:
						unsafe_commits += 1
						leaks_committed += 1

		var t_tier_end := Time.get_ticks_usec()
		var tier_total_usec: int = t_tier_end - t_tier_start
		grand_total_ticks += num_ticks
		grand_total_usec += tier_total_usec

		# Compute percentiles and budget pass rates
		latencies_usec.sort()
		var n := latencies_usec.size()
		var p50_u: float = float(latencies_usec[int(n * 0.50)])
		var p95_u: float = float(latencies_usec[int(min(n - 1, int(n * 0.95)))])
		var p99_u: float = float(latencies_usec[int(min(n - 1, int(n * 0.99)))])
		var max_u: float = float(latencies_usec[n - 1])

		var sum_u: float = 0.0
		var count_60hz := 0 # <= 16666 usec
		var count_120hz := 0 # <= 8333 usec
		for u in latencies_usec:
			sum_u += float(u)
			if u <= 16666:
				count_60hz += 1
			if u <= 8333:
				count_120hz += 1

		var mean_u: float = sum_u / float(n) if n > 0 else 0.0
		var term_sha := _hash_state(curr_state)

		tier_results[name] = {
			"rooms": num_rooms,
			"actors": num_actors,
			"depth": depth,
			"ticks": num_ticks,
			"total_time_ms": float(tier_total_usec) / 1000.0,
			"mean_ms": mean_u / 1000.0,
			"p50_ms": p50_u / 1000.0,
			"p95_ms": p95_u / 1000.0,
			"p99_ms": p99_u / 1000.0,
			"max_ms": max_u / 1000.0,
			"budget_60hz_pass_rate": float(count_60hz) / float(n),
			"budget_120hz_pass_rate": float(count_120hz) / float(n),
			"commits": commits,
			"rho_repairs": rho_repairs,
			"blocked_leaks": blocked_leaks,
			"unsafe_commits": unsafe_commits,
			"leaks_committed": leaks_committed,
			"terminal_state_sha256": term_sha
		}

	return {
		"total_ticks": grand_total_ticks,
		"total_time_ms": float(grand_total_usec) / 1000.0,
		"tiers": tier_results
	}
