class_name EvaluationTrace
extends RefCounted

## D-073 per-proposal evaluation trace for the observer dashboard.
##
## `sealed_lighthouse_machine.gd` is byte-bound by the immutable engine evidence
## (`_workspace/current/engineering/tech-verification/**/summary.json:
## software.machine_sha256`), so the machine itself records nothing. This mirror
## reconstructs, from the same scenario document and the committed PRE-state, the
## ordered checks the machine executes for one call and their outcomes, using the
## machine's own predicates and its first-failure short-circuit. It is authored
## against one exact machine source (`MACHINE_SOURCE_SHA256`, pinned by
## `tests/test_evaluation_trace_mirror.py`) and it fails closed at runtime: a
## trace is only reported as evidence when the failures it reconstructs equal the
## refusal codes the real machine returned (`consistent`). Recording never adds
## an evaluation; nothing here reads or writes canonical state.

const MACHINE_SOURCE_SHA256 := "cc531b6b93c066807eb628c0616d060a275a71d7f65c118983d2e8a90cc6b962"

## Authored check order per operation (execution order inside the machine).
const CHECK_PLAN := {
	"acquire_object": ["OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE"],
	"install_lens": ["MISSING_REQUIRED_OBJECT", "QUEST_STAGE_PRECONDITION"],
	"reveal_hint": [
		"FORBIDDEN_DISCLOSURE",
		"STAGE_GATED_DISCLOSURE",
		"UNKNOWN_ACTOR",
		"NPC_DOES_NOT_KNOW_FACT",
	],
	"validate_disclosure": ["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE"],
}


static func plan_for(operation: String) -> Array:
	return (CHECK_PLAN.get(operation, ["UNKNOWN_OPERATION"]) as Array).duplicate()


static func _entry(code: String, failed: bool) -> Dictionary:
	return {"code": code, "outcome": "fail" if failed else "pass"}


## Mirror of `SealedLighthouseMachine.validate_disclosure` for one fact list.
## Both disclosure checks are always evaluated per fact (the machine collects
## codes instead of short-circuiting there).
static func disclosure_checks(scenario: Dictionary, state: Dictionary, facts: Array) -> Array:
	var checks: Array = []
	var policy: Dictionary = scenario["disclosure_policy"]
	for fact in facts:
		checks.append(_entry("FORBIDDEN_DISCLOSURE", fact in policy["permanently_forbidden"]))
		var stage_gated := false
		for gate in policy["stage_gates"]:
			if gate["fact_id"] == fact and int(state["quest"]["stage"]) < int(gate["minimum_stage"]):
				stage_gated = true
		checks.append(_entry("STAGE_GATED_DISCLOSURE", stage_gated))
	return checks


## Mirror of `SealedLighthouseMachine.apply_operation` check execution against
## the PRE-state (the machine evaluates every predicate on a copy of the state it
## holds before mutating). Returns {"plan": [...], "checks": [...]}.
static func reconstruct(
	scenario: Dictionary, state: Dictionary, operation: String, arguments: Dictionary
) -> Dictionary:
	var checks: Array = []
	match operation:
		"acquire_object":
			var object_id: String = str(arguments.get("object_id", ""))
			var object_locations: Dictionary = state["world"]["object_locations"]
			var not_present: bool = not object_locations.has(object_id)
			checks.append(_entry("OBJECT_NOT_PRESENT", not_present))
			if not not_present:
				var location: String = str(object_locations[object_id])
				var reachable: bool = location in state["world"]["reachable_locations"]
				checks.append(_entry("OBJECT_NOT_REACHABLE", not reachable))
		"install_lens":
			var object_id: String = str(arguments.get("object_id", ""))
			var missing: bool = object_id not in state["player"]["inventory"]
			checks.append(_entry("MISSING_REQUIRED_OBJECT", missing))
			if not missing:
				checks.append(_entry("QUEST_STAGE_PRECONDITION", int(state["quest"]["stage"]) < 1))
		"reveal_hint":
			var actor_id: String = str(arguments.get("actor_id", ""))
			var fact_id: String = str(arguments.get("fact_id", ""))
			checks = disclosure_checks(scenario, state, [fact_id])
			if not _any_failed(checks):
				var unknown_actor: bool = actor_id != "captain_mira"
				checks.append(_entry("UNKNOWN_ACTOR", unknown_actor))
				if not unknown_actor:
					var known: bool = fact_id in state["npcs"][actor_id]["knowledge"]
					checks.append(_entry("NPC_DOES_NOT_KNOW_FACT", not known))
		_:
			checks.append(_entry("UNKNOWN_OPERATION", true))
	return {"plan": plan_for(operation), "checks": checks}


static func _any_failed(checks: Array) -> bool:
	for entry in checks:
		if str(entry["outcome"]) == "fail":
			return true
	return false


static func failed_codes(checks: Array) -> Array:
	var codes: Array = []
	for entry in checks:
		if str(entry["outcome"]) == "fail" and str(entry["code"]) not in codes:
			codes.append(str(entry["code"]))
	codes.sort()
	return codes


## The mirror is evidence only when its reconstructed failures equal the refusal
## codes the real machine returned for the same call.
static func consistent(checks: Array, machine_codes: Array) -> bool:
	var observed: Array = []
	for code in machine_codes:
		if str(code) not in observed:
			observed.append(str(code))
	observed.sort()
	return failed_codes(checks) == observed
