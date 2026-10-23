"""Deterministic three-arm evaluator for the frozen ``reveal_hint`` contract.

This module is intentionally independent of Godot.  It consumes the frozen
expectation packet and the declared scenario, then evaluates the same materialized
state/candidate/template through three isolated arms:

* ``unchecked_isolated`` is an intentionally unsafe no-check baseline;
* ``general_rule`` is an explicit policy implementation;
* ``ontology_gate`` uses a versioned declaration derived only from the frozen
  packet (never the repository graph).

The packet remains the source of expected values.  No gate output is used to
construct expectations.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ARM_NAMES = ("unchecked_isolated", "general_rule", "ontology_gate")
DENY_TEMPLATE = "mira-safe-deflection-v1"
HINT_TEMPLATE = "sl-rc-003-authorized-hint"
HINT_MEMORY = "turn-05:mira-shared-tide-marks-hint"
PUBLIC_REPORT = "llm-wiki/wiki/reports/2026-10-22-ontology-signals-interview.md"
PUBLIC_MANIFEST = "research/npc-disclosure/public/source-substitution-v1.json"
PUBLIC_MANIFEST_SHA256 = "fd08736902f0f542c311b367125a71f47ee20930e9294402b9c70c3481b37d05"


class DisclosureContractError(ValueError):
    """Raised when a frozen contract or source binding is invalid."""


@dataclass(frozen=True)
class DisclosureContract:
    """Validated frozen packet plus its declared runtime inputs."""

    packet_path: Path
    packet_sha256: str
    sidecar_sha256: str
    packet: Mapping[str, Any]
    scenario: Mapping[str, Any]
    runtime_ontology: Mapping[str, Any]
    source_hashes_observed: Mapping[str, str]
    source_hash_mismatches: Mapping[str, Mapping[str, str]]
    public_source_bindings: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class ArmResult:
    """One deterministic arm evaluation result."""

    payload: Mapping[str, Any]


@dataclass(frozen=True)
class EvaluationBundle:
    """Raw outcomes and generated summaries for one evaluator run."""

    trace_records: tuple[Mapping[str, Any], ...]
    comparison_summary: Mapping[str, Any]
    factual_summary: Mapping[str, Any]
    metadata: Mapping[str, Any]


def _canonical_json(value: Any) -> str:
    """Match Godot's sorted-key compact JSON for hash-bound state records."""

    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any) -> str:
    return sha256_bytes(_canonical_json(value).encode("utf-8"))


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DisclosureContractError(f"missing {label}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DisclosureContractError(f"invalid {label}: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DisclosureContractError(f"{label} must be a JSON object: {path}")
    return value


def _resolve_source(root: Path, packet_path: Path, relative: str) -> Path:
    """Resolve project-owned and workspace-owned source bindings."""

    candidates = [root / relative]
    # The seed and llm-wiki are workspace-level sources while the project data is
    # nested one directory below the workspace root.
    if relative.startswith((".ouroboros/", "llm-wiki/")):
        candidates.insert(0, root.parent / relative)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise DisclosureContractError(f"source binding is missing: {relative}")


def public_source_binding(root: Path) -> dict[str, Any]:
    """Validate the one approved privacy derivative, never the private account data."""
    manifest_path = root / PUBLIC_MANIFEST
    if sha256_bytes(manifest_path.read_bytes()) != PUBLIC_MANIFEST_SHA256:
        raise DisclosureContractError("public source substitution manifest hash mismatch")
    binding = _read_json(manifest_path, "public source substitution")
    public_path = root / binding["public_source"]
    if sha256_bytes(public_path.read_bytes()) != binding["public_source_sha256"]:
        raise DisclosureContractError("public source derivative hash mismatch")
    seed = binding["seed_materialization"]
    if sha256_bytes((root / seed["public_source"]).read_bytes()) != seed["sha256"]:
        raise DisclosureContractError("public seed materialization hash mismatch")
    return {"manifest": PUBLIC_MANIFEST, "manifest_sha256": PUBLIC_MANIFEST_SHA256, **binding}


def verify_publication_sources(
    root: Path,
    observed: Mapping[str, str],
    packet: Mapping[str, Any],
    *,
    public_source_bindings: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Check historical sources or explicitly bound current public derivatives."""
    if not isinstance(observed, dict) or set(observed) != set(packet["source_hashes"]):
        raise DisclosureContractError("publication source binding set drift")
    binding = public_source_binding(root)
    if (
        sha256_bytes(
            (root / "research/npc-disclosure/reveal-hint-expectations-v1.json").read_bytes()
        )
        != binding["packet_sha256"]
    ):
        raise DisclosureContractError("public substitution packet binding mismatch")
    if packet["source_hashes"].get(PUBLIC_REPORT) != binding["frozen_source_sha256"]:
        raise DisclosureContractError("public substitution frozen source binding mismatch")
    if public_source_bindings is not None:
        if public_source_bindings != binding:
            raise DisclosureContractError("public substitution current binding metadata mismatch")
        if observed.get(PUBLIC_REPORT) != binding["public_source_sha256"]:
            raise DisclosureContractError("public substitution current source binding mismatch")
    elif observed.get(PUBLIC_REPORT) != binding["historical_observed_source_sha256"]:
        raise DisclosureContractError("public substitution historical source binding mismatch")
    for relative, digest in observed.items():
        if relative == PUBLIC_REPORT:
            continue
        seed = binding["seed_materialization"]
        source = (
            root / seed["public_source"]
            if relative == seed["logical_source"]
            else _resolve_source(root, root, relative)
        )
        if sha256_bytes(source.read_bytes()) != digest:
            raise DisclosureContractError(f"publication source hash drift: {relative}")
    return binding


def _validate_shape(packet: Mapping[str, Any]) -> None:
    required = {
        "packet_id",
        "packet_version",
        "status",
        "authorship",
        "scope",
        "source_hashes",
        "approved_templates",
        "rule_ids",
        "normal_cases",
        "boundary_cases",
        "malformed_cases",
        "rule_change_fixtures",
        "integration_contract",
    }
    missing = sorted(required - packet.keys())
    if missing:
        raise DisclosureContractError(f"frozen packet fields missing: {missing}")
    if packet["status"] != "FROZEN_EXPECTATIONS_NOT_RUNTIME_RESULTS":
        raise DisclosureContractError("packet is not a frozen expectations packet")
    authorship = packet["authorship"]
    if (
        not isinstance(authorship, Mapping)
        or authorship.get("not_derived_from_gate_output") is not True
    ):
        raise DisclosureContractError("expectations must be explicitly independent of gate output")
    if authorship.get("shared_cases_and_expectations") is not True:
        raise DisclosureContractError("three arms must share frozen cases and expectations")
    if tuple(authorship.get("arms", ())) != ARM_NAMES:
        raise DisclosureContractError("frozen arm order does not match evaluator")
    scope = packet["scope"]
    if not isinstance(scope, Mapping) or scope.get("operation") != "reveal_hint":
        raise DisclosureContractError("only the frozen reveal_hint scope is supported")
    if int(scope.get("normal_denominator", -1)) != 48:
        raise DisclosureContractError("normal denominator is not the frozen 48-case domain")
    if len(packet["normal_cases"]) != 48:
        raise DisclosureContractError("normal case list is not frozen at 48 cases")
    if len(packet["boundary_cases"]) != 4 or len(packet["malformed_cases"]) != 8:
        raise DisclosureContractError("boundary/malformed case counts do not match frozen packet")
    if len(packet["rule_change_fixtures"]) != 2:
        raise DisclosureContractError("rule-change fixture count does not match frozen packet")


def _build_runtime_ontology(
    packet: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the versioned runtime declaration from frozen packet fields only."""

    scope = packet["scope"]
    policy = scenario.get("disclosure_policy")
    if not isinstance(policy, Mapping):
        raise DisclosureContractError("scenario disclosure_policy is missing")
    gates = policy.get("stage_gates", [])
    if not isinstance(gates, list):
        raise DisclosureContractError("scenario stage_gates must be a list")
    # This declaration is deliberately serializable and carries its provenance.
    return {
        "ontology_id": f"{packet['packet_id']}:runtime-disclosure",
        "ontology_version": str(packet["packet_version"]),
        "provenance": "frozen_expectation_packet",
        "operation": scope["operation"],
        "scenario_id": scope["scenario_id"],
        "canonical_fact_ids": list(scope["canonical_fact_ids"]),
        "eligible_actor_ids": list(scope["eligible_actor_ids"]),
        "permanently_forbidden": list(policy.get("permanently_forbidden", [])),
        "stage_gates": copy.deepcopy(gates),
        "rule_ids": copy.deepcopy(packet["rule_ids"]),
        "approved_templates": copy.deepcopy(packet["approved_templates"]),
    }


def load_frozen_contract(
    packet_path: str | Path,
    project_root: str | Path | None = None,
    *,
    public_sources: bool = False,
) -> DisclosureContract:
    """Load the packet and bind every source hash, reporting drift explicitly."""

    packet_file = Path(packet_path).resolve()
    root = Path(project_root).resolve() if project_root is not None else packet_file.parents[2]
    packet_bytes = packet_file.read_bytes()
    packet_sha = sha256_bytes(packet_bytes)
    sidecar = packet_file.with_suffix(".sha256")
    sidecar_text = sidecar.read_text(encoding="utf-8").strip().split()
    if not sidecar_text or sidecar_text[0] != packet_sha:
        raise DisclosureContractError(
            f"packet sidecar hash mismatch: expected {packet_sha}, sidecar={sidecar}"
        )
    packet = _read_json(packet_file, "frozen packet")
    _validate_shape(packet)
    scenario_path = root / str(packet["scope"]["scenario_resource"])
    scenario = _read_json(scenario_path, "scenario resource")
    if scenario.get("scenario_id") != packet["scope"]["scenario_id"]:
        raise DisclosureContractError("scenario ID does not match frozen scope")
    observed: dict[str, str] = {}
    public_binding = public_source_binding(root) if public_sources else None
    mismatches: dict[str, dict[str, str]] = {}
    for relative, expected in packet["source_hashes"].items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise DisclosureContractError("source_hashes must map strings to SHA-256 strings")
        if public_binding is not None and relative == PUBLIC_REPORT:
            if (
                expected != public_binding["frozen_source_sha256"]
                or packet_sha != public_binding["packet_sha256"]
            ):
                raise DisclosureContractError("public substitution frozen packet binding mismatch")
            actual = public_binding["public_source_sha256"]
        elif (
            public_binding is not None
            and relative == public_binding["seed_materialization"]["logical_source"]
        ):
            actual = public_binding["seed_materialization"]["sha256"]
        else:
            source = _resolve_source(root, packet_file, relative)
            actual = sha256_bytes(source.read_bytes())
        observed[relative] = actual
        if actual != expected:
            mismatches[relative] = {"expected": expected, "observed": actual}
    protected = {
        str(packet["scope"]["scenario_resource"]),
        ".ouroboros/seeds/seed-20261023-npc-disclosure-37ffdf78a47d.yaml",
    }
    protected_mismatches = sorted(set(mismatches).intersection(protected))
    if protected_mismatches:
        raise DisclosureContractError(f"protected source hash mismatches: {protected_mismatches}")
    ontology = _build_runtime_ontology(packet, scenario)
    return DisclosureContract(
        packet_path=packet_file,
        packet_sha256=packet_sha,
        sidecar_sha256=sidecar_text[0],
        packet=packet,
        scenario=scenario,
        runtime_ontology=ontology,
        source_hashes_observed=observed,
        source_hash_mismatches=mismatches,
        public_source_bindings=public_binding,
    )


# Compatibility aliases make the contract loader easy to discover without adding
# a second implementation surface.
load_contract = load_frozen_contract


def _case_request(case: Mapping[str, Any]) -> dict[str, Any]:
    request = {"operation": "reveal_hint"}
    if "actor_id" in case:
        request["actor_id"] = case["actor_id"]
    if "fact_id" in case:
        request["fact_id"] = case["fact_id"]
    return request


def _materialize_state(contract: DisclosureContract, case: Mapping[str, Any]) -> dict[str, Any]:
    """Materialize exactly the frozen case axes without consulting a gate."""

    state = copy.deepcopy(contract.scenario["initial_state"])
    state["quest"]["stage"] = case["stage"]
    actor_id = case.get("actor_id")
    fact_id = case.get("fact_id")
    if actor_id in state.get("npcs", {}):
        actor = state["npcs"][actor_id]
        knowledge = set(actor.get("knowledge", []))
        disclosed = set(actor.get("disclosed", []))
        if fact_id:
            (knowledge.add(fact_id) if case.get("knows") else knowledge.discard(fact_id))
            (disclosed.add(fact_id) if case.get("prior_disclosed") else disclosed.discard(fact_id))
        actor["knowledge"] = sorted(knowledge)
        actor["disclosed"] = sorted(disclosed)
    return state


def _template_for(case: Mapping[str, Any], allowed: bool) -> str | None:
    if not allowed:
        return DENY_TEMPLATE
    if case.get("fact_id") == "tide_marks_hint":
        return HINT_TEMPLATE
    return None


def _display_for(template_id: str | None, packet: Mapping[str, Any]) -> dict[str, Any] | None:
    if template_id is None:
        return None
    for template in packet["approved_templates"]:
        if template.get("template_id") == template_id:
            return copy.deepcopy(template)
    raise DisclosureContractError(f"template is not approved by frozen packet: {template_id}")


def _policy_codes(
    fact_id: Any,
    stage: Any,
    forbidden: set[str],
    stage_gates: list[Mapping[str, Any]],
) -> list[str]:
    codes: list[str] = []
    if fact_id in forbidden:
        codes.append("FORBIDDEN_DISCLOSURE")
    for gate in stage_gates:
        if gate.get("fact_id") == fact_id and stage < gate.get("minimum_stage"):
            codes.append("STAGE_GATED_DISCLOSURE")
    return sorted(set(codes))


def _error(code: str, rule_id: str, fact_id: Any) -> dict[str, Any]:
    messages = {
        "FORBIDDEN_DISCLOSURE": "requested fact is permanently forbidden",
        "STAGE_GATED_DISCLOSURE": "requested fact is below its minimum stage",
        "UNKNOWN_ACTOR": "actor is not eligible for reveal_hint",
        "NPC_DOES_NOT_KNOW_FACT": "eligible actor does not know the requested fact",
    }
    return {"code": code, "rule_id": rule_id, "fact_id": fact_id, "message": messages[code]}


def _check_result(rule_id: str, outcome: str) -> dict[str, str]:
    return {"rule_id": rule_id, "outcome": outcome}


def _apply_allowed_state(
    state: dict[str, Any], actor_id: str, fact_id: str, fresh: bool
) -> dict[str, Any]:
    next_state = copy.deepcopy(state)
    if not fresh:
        return next_state
    facts = set(next_state.get("facts", []))
    facts.add(fact_id)
    next_state["facts"] = sorted(facts)
    actor = next_state["npcs"][actor_id]
    disclosed = set(actor.get("disclosed", []))
    disclosed.add(fact_id)
    actor["disclosed"] = sorted(disclosed)
    if fact_id == "tide_marks_hint":
        memory = set(actor.get("relationship_memory", []))
        memory.add(HINT_MEMORY)
        actor["relationship_memory"] = sorted(memory)
    next_state["revision"] = int(state.get("revision", 0)) + 1
    return next_state


def _validated_gate(
    state: dict[str, Any],
    case: Mapping[str, Any],
    contract: DisclosureContract,
    *,
    ontology: bool,
    policy_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate one explicit gate; ``ontology`` selects only its declaration source."""

    declaration = contract.runtime_ontology if ontology else None
    if ontology:
        scenario_policy = copy.deepcopy(contract.runtime_ontology)
        if policy_override is not None:
            scenario_policy["permanently_forbidden"] = copy.deepcopy(
                policy_override.get(
                    "permanently_forbidden", scenario_policy["permanently_forbidden"]
                )
            )
            scenario_policy["stage_gates"] = copy.deepcopy(
                policy_override.get("stage_gates", scenario_policy["stage_gates"])
            )
    elif policy_override is not None:
        scenario_policy = policy_override
    else:
        scenario_policy = contract.scenario["disclosure_policy"]
    forbidden = set(scenario_policy.get("permanently_forbidden", []))
    stage_gates = scenario_policy.get("stage_gates", [])
    request = _case_request(case)
    actor_id = request.get("actor_id")
    fact_id = request.get("fact_id")
    checks: list[dict[str, str]] = []
    errors: list[dict[str, Any]] = []
    codes = _policy_codes(fact_id, state["quest"]["stage"], forbidden, stage_gates)
    if codes:
        for code in codes:
            rule_id = "DISC-001" if code == "FORBIDDEN_DISCLOSURE" else "DISC-002"
            checks.append(_check_result(rule_id, "fail"))
            errors.append(_error(code, rule_id, fact_id))
        checks.append(_check_result("DISC-007", "fail"))
        return _result_payload(
            state,
            case,
            contract,
            allowed=False,
            codes=codes,
            checks=checks,
            errors=errors,
            rule_ids=[item["rule_id"] for item in checks],
            state_effect="denied_no_mutation",
        )
    eligible = set(
        (declaration or {"eligible_actor_ids": ["captain_mira"]}).get(
            "eligible_actor_ids", ["captain_mira"]
        )
    )
    if actor_id not in eligible:
        checks.append(_check_result("DISC-003", "fail"))
        checks.append(_check_result("DISC-007", "fail"))
        errors.append(_error("UNKNOWN_ACTOR", "DISC-003", fact_id))
        return _result_payload(
            state,
            case,
            contract,
            allowed=False,
            codes=["UNKNOWN_ACTOR"],
            checks=checks,
            errors=errors,
            rule_ids=[item["rule_id"] for item in checks],
            state_effect="denied_no_mutation",
        )
    actor = state["npcs"].get(actor_id, {})
    if fact_id not in set(actor.get("knowledge", [])):
        checks.append(_check_result("DISC-004", "fail"))
        checks.append(_check_result("DISC-007", "fail"))
        errors.append(_error("NPC_DOES_NOT_KNOW_FACT", "DISC-004", fact_id))
        return _result_payload(
            state,
            case,
            contract,
            allowed=False,
            codes=["NPC_DOES_NOT_KNOW_FACT"],
            checks=checks,
            errors=errors,
            rule_ids=[item["rule_id"] for item in checks],
            state_effect="denied_no_mutation",
        )
    fresh = not bool(case.get("prior_disclosed", False))
    rule_id = "DISC-005" if fresh else "DISC-006"
    checks.append(_check_result(rule_id, "pass"))
    next_state = _apply_allowed_state(state, actor_id, fact_id, fresh)
    return _result_payload(
        state,
        case,
        contract,
        allowed=True,
        codes=[],
        checks=checks,
        errors=[],
        rule_ids=[rule_id],
        state_effect="fresh_disclosure" if fresh else "redisplay_no_mutation",
        next_state=next_state,
    )


def _unchecked_gate(
    state: dict[str, Any], case: Mapping[str, Any], contract: DisclosureContract
) -> dict[str, Any]:
    """Intentional no-check baseline, isolated from the two authoritative gates."""

    actor_id = case.get("actor_id")
    fact_id = case.get("fact_id")
    next_state = copy.deepcopy(state)
    errors: list[dict[str, Any]] = []
    mutated = False
    if isinstance(fact_id, str) and fact_id:
        facts = set(next_state.get("facts", []))
        facts.add(fact_id)
        next_state["facts"] = sorted(facts)
        if actor_id in next_state.get("npcs", {}):
            actor = next_state["npcs"][actor_id]
            disclosed = set(actor.get("disclosed", []))
            disclosed.add(fact_id)
            actor["disclosed"] = sorted(disclosed)
            if fact_id == "tide_marks_hint":
                memory = set(actor.get("relationship_memory", []))
                memory.add(HINT_MEMORY)
                actor["relationship_memory"] = sorted(memory)
        next_state["revision"] = int(state.get("revision", 0)) + 1
        mutated = canonical_hash(state) != canonical_hash(next_state)
    else:
        errors.append(
            {
                "code": "MALFORMED_CANDIDATE",
                "rule_id": None,
                "fact_id": fact_id,
                "message": "no-check arm could not materialize a missing fact",
            }
        )
    return _result_payload(
        state,
        case,
        contract,
        allowed=True,
        codes=[],
        checks=[],
        errors=errors,
        rule_ids=[],
        state_effect="unchecked_mutation" if mutated else "unchecked_no_mutation",
        next_state=next_state,
        unsafe=True,
    )


def _result_payload(
    prior_state: dict[str, Any],
    case: Mapping[str, Any],
    contract: DisclosureContract,
    *,
    allowed: bool,
    codes: list[str],
    checks: list[dict[str, str]],
    errors: list[dict[str, Any]],
    rule_ids: list[str],
    state_effect: str,
    next_state: dict[str, Any] | None = None,
    unsafe: bool = False,
) -> dict[str, Any]:
    after = copy.deepcopy(prior_state if next_state is None else next_state)
    template_id = _template_for(case, allowed)
    return {
        "accepted": allowed,
        "allowed": allowed,
        "codes": sorted(set(codes)),
        "checks": checks,
        "errors": errors,
        "rule_ids": rule_ids,
        "state_effect": state_effect,
        "template_id": template_id,
        "display": _display_for(template_id, contract.packet),
        "prior_state": copy.deepcopy(prior_state),
        "state": after,
        "prior_state_hash": canonical_hash(prior_state),
        "next_state_hash": canonical_hash(after),
        "mutated": canonical_hash(prior_state) != canonical_hash(after),
        "unsafe": unsafe,
    }


def evaluate_case(
    contract: DisclosureContract,
    case: Mapping[str, Any],
    arm: str,
    *,
    policy_override: Mapping[str, Any] | None = None,
) -> ArmResult:
    """Evaluate one frozen case for one arm with a fresh materialized state."""

    if arm not in ARM_NAMES:
        raise ValueError(f"unknown disclosure arm: {arm}")
    state = _materialize_state(contract, case)
    if arm == "unchecked_isolated":
        payload = _unchecked_gate(state, case, contract)
    else:
        payload = _validated_gate(
            state,
            case,
            contract,
            ontology=arm == "ontology_gate",
            policy_override=policy_override,
        )
    payload = dict(payload)
    payload.update(
        {
            "case_id": case["case_id"],
            "arm": arm,
            "request": _case_request(case),
            "contract_version": contract.packet["packet_version"],
            "ontology_declaration": copy.deepcopy(contract.runtime_ontology)
            if arm == "ontology_gate"
            else None,
        }
    )
    return ArmResult(payload)


def _semantic_view(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "allowed": bool(payload.get("allowed")),
        "codes": sorted(set(payload.get("codes", []))),
        "template_id": payload.get("template_id"),
        "state_effect": payload.get("state_effect"),
    }


def _expected_view(case: Mapping[str, Any]) -> dict[str, Any]:
    expected = case["expected"]
    return {
        "allowed": bool(expected["allowed"]),
        "codes": sorted(set(expected.get("codes", []))),
        "template_id": expected.get("template_id"),
        "state_effect": expected.get("state_effect", "denied_no_mutation"),
    }


def _unsafe_expected_invariants(case: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
    """Identify only unauthorized allows and forbidden redisplay mutations."""

    expected = case["expected"]
    failures: list[str] = []
    if not expected["allowed"] and payload["allowed"]:
        failures.append("unchecked_unauthorized_allow")
    if expected.get("state_effect") == "redisplay_no_mutation" and payload["mutated"]:
        failures.append("unchecked_redisplay_mutation")
    return failures


def _state_assertions(case: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    before = payload["prior_state"]
    after = payload["state"]
    before_hash = payload["prior_state_hash"]
    after_hash = payload["next_state_hash"]
    if not payload["allowed"]:
        if before != after or before_hash != after_hash or payload["mutated"]:
            failures.append("denied_state_changed")
    elif payload["state_effect"] == "redisplay_no_mutation":
        if before != after or before_hash != after_hash or payload["mutated"]:
            failures.append("redisplay_state_changed")
    elif payload["state_effect"] == "fresh_disclosure":
        fact_id = case.get("fact_id")
        actor_id = case.get("actor_id")
        if fact_id not in after.get("facts", []):
            failures.append("fresh_fact_not_disclosed")
        if actor_id in after.get("npcs", {}) and fact_id not in after["npcs"][actor_id].get(
            "disclosed", []
        ):
            failures.append("fresh_actor_disclosure_missing")
        if after.get("quest", {}).get("stage") != before.get("quest", {}).get("stage"):
            failures.append("fresh_stage_changed")
        if after.get("revision") != before.get("revision") + 1:
            failures.append("fresh_revision_not_incremented_once")
        if before_hash == after_hash or not payload["mutated"]:
            failures.append("fresh_hash_did_not_change")
        if fact_id == "tide_marks_hint":
            memory = after.get("npcs", {}).get(actor_id, {}).get("relationship_memory", [])
            if HINT_MEMORY not in memory:
                failures.append("hint_relationship_memory_missing")
    return failures


def _display_assertions(case: Mapping[str, Any], payload: Mapping[str, Any]) -> list[str]:
    failures: list[str] = []
    template_id = payload.get("template_id")
    expected = case["expected"]
    if not payload["allowed"] and template_id != DENY_TEMPLATE:
        failures.append("denial_template_not_safe_fallback")
    if payload["allowed"] and case.get("fact_id") != "tide_marks_hint" and template_id is not None:
        failures.append("generic_allowed_fact_invented_template")
    if (
        payload["allowed"]
        and case.get("fact_id") == "tide_marks_hint"
        and template_id != HINT_TEMPLATE
    ):
        failures.append("hint_allowed_template_missing")
    if expected.get("template_id") != template_id and payload.get("arm") != "unchecked_isolated":
        failures.append("template_mismatch")
    return failures


def _replay_signature(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Exclude provenance-only fields while retaining all deterministic evidence."""

    return {
        key: payload[key]
        for key in (
            "allowed",
            "codes",
            "checks",
            "errors",
            "rule_ids",
            "state_effect",
            "template_id",
            "prior_state_hash",
            "next_state_hash",
            "mutated",
            "prior_state",
            "state",
        )
    }


def _matches_expected_observed(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    """Compare only frozen fields present in each rule-change delta."""

    return all(observed.get(key) == expected[key] for key in expected)


def _case_records(
    contract: DisclosureContract, cases: list[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for case in cases:
        for arm in ARM_NAMES:
            first = evaluate_case(contract, case, arm)
            second = evaluate_case(contract, case, arm)
            payload = dict(first.payload)
            expected_view = _expected_view(case)
            semantic = _semantic_view(payload)
            mismatch = semantic != expected_view
            state_failures = _state_assertions(case, payload)
            display_failures = _display_assertions(case, payload)
            replay_equal = _replay_signature(first.payload) == _replay_signature(second.payload)
            unsafe_violations: list[str] = []
            if arm == "unchecked_isolated":
                unsafe_violations.extend(_unsafe_expected_invariants(case, payload))
            violations = state_failures + display_failures
            records.append(
                {
                    "case_id": case["case_id"],
                    "stratum": case["case_id"][0],
                    "arm": arm,
                    "contract_binding": {
                        "packet_id": contract.packet["packet_id"],
                        "packet_version": contract.packet["packet_version"],
                        "packet_sha256": contract.packet_sha256,
                        "sidecar_sha256": contract.sidecar_sha256,
                        "source_hashes": dict(contract.source_hashes_observed),
                        "source_hash_mismatches": copy.deepcopy(contract.source_hash_mismatches),
                        "runtime_ontology": copy.deepcopy(contract.runtime_ontology),
                    },
                    "expected": expected_view,
                    "observed": semantic,
                    "mismatch": mismatch,
                    "rule_ids": payload["rule_ids"],
                    "checks": payload["checks"],
                    "errors": payload["errors"],
                    "request": payload["request"],
                    "prior_state_hash": payload["prior_state_hash"],
                    "next_state_hash": payload["next_state_hash"],
                    "mutated": payload["mutated"],
                    "template_id": payload["template_id"],
                    "display": payload["display"],
                    "state_effect": payload["state_effect"],
                    "prior_state": payload["prior_state"],
                    "state": payload["state"],
                    "replay_equal": replay_equal,
                    "state_assertion_failures": state_failures,
                    "display_assertion_failures": display_failures,
                    "violations": violations,
                    "unsafe_violations": unsafe_violations,
                }
            )
    return records


def _changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    """Return deterministic leaf paths changed by an in-memory policy fixture."""

    if isinstance(before, Mapping) and isinstance(after, Mapping):
        paths: list[str] = []
        for key in sorted(set(before) | set(after)):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                paths.append(child)
            else:
                paths.extend(_changed_paths(before[key], after[key], child))
        return paths
    if isinstance(before, list) and isinstance(after, list):
        paths: list[str] = []
        for index in range(max(len(before), len(after))):
            child = f"{prefix}[{index}]"
            if index >= len(before) or index >= len(after):
                paths.append(child)
            else:
                paths.extend(_changed_paths(before[index], after[index], child))
        return paths
    return [prefix] if before != after else []


def _rule_change_records(
    contract: DisclosureContract, normal_cases: list[Mapping[str, Any]]
) -> dict[str, Any]:
    by_id = {case["case_id"]: case for case in normal_cases}
    fixture_records: list[dict[str, Any]] = []
    for fixture in contract.packet["rule_change_fixtures"]:
        mutation = fixture["mutation"]
        baseline_policy = copy.deepcopy(contract.scenario["disclosure_policy"])
        mutated_policy = copy.deepcopy(baseline_policy)
        path = mutation["path"]
        if path == "disclosure_policy.stage_gates[0].minimum_stage":
            mutated_policy["stage_gates"][0]["minimum_stage"] = mutation["to"]
        elif path == "disclosure_policy.permanently_forbidden":
            mutated_policy["permanently_forbidden"] = copy.deepcopy(mutation["to"])
        else:
            raise DisclosureContractError(f"unsupported frozen rule-change path: {path}")
        pair_records: list[dict[str, Any]] = []
        for case_id in fixture["paired_case_ids"]:
            case = by_id[case_id]
            expected_delta = next(
                item for item in fixture["expected_deltas"] if item["case_id"] == case_id
            )
            arms: dict[str, Any] = {}
            for arm in ("general_rule", "ontology_gate"):
                baseline = evaluate_case(contract, case, arm)
                mutated = evaluate_case(contract, case, arm, policy_override=mutated_policy)
                arms[arm] = {
                    "baseline": _semantic_view(baseline.payload),
                    "mutated": _semantic_view(mutated.payload),
                    "baseline_hashes": {
                        "prior": baseline.payload["prior_state_hash"],
                        "next": baseline.payload["next_state_hash"],
                    },
                    "mutated_hashes": {
                        "prior": mutated.payload["prior_state_hash"],
                        "next": mutated.payload["next_state_hash"],
                    },
                    "matches_expected": (
                        _matches_expected_observed(
                            _semantic_view(baseline.payload), expected_delta["baseline"]
                        )
                        and _matches_expected_observed(
                            _semantic_view(mutated.payload), expected_delta["mutated"]
                        )
                    ),
                }
            pair_records.append(
                {
                    "case_id": case_id,
                    "expected": expected_delta,
                    "arms": arms,
                    "general_ontology_equal": arms["general_rule"]["mutated"]
                    == arms["ontology_gate"]["mutated"],
                }
            )
        observed_changed_paths = [
            f"disclosure_policy.{value}"
            for value in _changed_paths(baseline_policy, mutated_policy)
        ]
        expected_pairs = {item["case_id"] for item in fixture["expected_deltas"]}
        observed_pairs = {row["case_id"] for row in pair_records}
        fixture_records.append(
            {
                "fixture_id": fixture["fixture_id"],
                "mutation": copy.deepcopy(mutation),
                "paired_case_ids": list(fixture["paired_case_ids"]),
                "expected_general_code_edit": fixture["expected_general_code_edit"],
                "expected_ontology_declaration_edit": fixture["expected_ontology_declaration_edit"],
                "observed_changed_paths": observed_changed_paths,
                "edit_scope_matches_expected": all(
                    value == path or value.startswith(f"{path}[")
                    for value in observed_changed_paths
                ),
                "expected_pair_count": len(expected_pairs),
                "observed_pair_count": len(observed_pairs),
                "omitted_case_ids": sorted(expected_pairs - observed_pairs),
                "missed_case_ids": [
                    row["case_id"]
                    for row in pair_records
                    if not all(
                        row["arms"][arm]["matches_expected"]
                        for arm in ("general_rule", "ontology_gate")
                    )
                ],
                "pairs": pair_records,
                "general_rule_change_applied": bool(observed_changed_paths),
                "ontology_gate_change_applied": bool(observed_changed_paths),
                "all_pairs_match": all(
                    all(
                        row["arms"][arm]["matches_expected"]
                        for arm in ("general_rule", "ontology_gate")
                    )
                    for row in pair_records
                ),
                "mutation_scope_preserved": baseline_policy != mutated_policy
                and contract.scenario["disclosure_policy"] == baseline_policy,
            }
        )
    return {
        "fixtures": fixture_records,
        "all_fixtures_match": all(row["all_pairs_match"] for row in fixture_records),
        "general_ontology_equal_under_rule_changes": all(
            pair["general_ontology_equal"]
            for fixture in fixture_records
            for pair in fixture["pairs"]
        ),
        "superiority_claim": None,
    }


def evaluate_contract(contract: DisclosureContract) -> EvaluationBundle:
    """Run all frozen strata and build raw trace plus factual summaries."""

    packet = contract.packet
    cases = [*packet["normal_cases"], *packet["boundary_cases"], *packet["malformed_cases"]]
    records = _case_records(contract, cases)
    normal_cases = list(packet["normal_cases"])
    rule_changes = _rule_change_records(contract, normal_cases)
    by_arm: dict[str, dict[str, Any]] = {}
    for arm in ARM_NAMES:
        arm_records = [row for row in records if row["arm"] == arm]
        normal = [row for row in arm_records if row["stratum"] == "N"]
        unsafe_rows = [row for row in arm_records if row["unsafe_violations"]]
        unauthorized_rows = [
            row for row in arm_records if "unchecked_unauthorized_allow" in row["unsafe_violations"]
        ]
        redisplay_rows = [
            row for row in arm_records if "unchecked_redisplay_mutation" in row["unsafe_violations"]
        ]
        fresh_mismatch_rows = [
            row
            for row in arm_records
            if row["mismatch"]
            and row["expected"]["allowed"]
            and row["expected"]["state_effect"] == "fresh_disclosure"
        ]
        by_stratum = lambda rows: {
            stratum: sum(row["stratum"] == stratum for row in rows) for stratum in ("N", "B", "M")
        }
        by_arm[arm] = {
            "case_count": len(arm_records),
            "normal_case_count": len(normal),
            "allowed_count": sum(row["observed"]["allowed"] for row in arm_records),
            "denied_count": sum(not row["observed"]["allowed"] for row in arm_records),
            "expected_mismatch_count": sum(row["mismatch"] for row in arm_records),
            "semantic_mismatch_by_stratum": by_stratum(
                [row for row in arm_records if row["mismatch"]]
            ),
            "state_assertion_failure_count": sum(
                bool(row["state_assertion_failures"]) for row in arm_records
            ),
            "display_assertion_failure_count": sum(
                bool(row["display_assertion_failures"]) for row in arm_records
            ),
            "replay_mismatch_count": sum(not row["replay_equal"] for row in arm_records),
            "unsafe_violation_count": len({row["case_id"] for row in unsafe_rows}),
            "unique_unsafe_case_count": len({row["case_id"] for row in unsafe_rows}),
            "unsafe_by_stratum": by_stratum(unsafe_rows),
            "unauthorized_allow_count": len({row["case_id"] for row in unauthorized_rows}),
            "unauthorized_allow_by_stratum": by_stratum(unauthorized_rows),
            "redisplay_mutation_count": len({row["case_id"] for row in redisplay_rows}),
            "redisplay_mutation_by_stratum": by_stratum(redisplay_rows),
            "permitted_fresh_representation_mismatch_count": len(
                {row["case_id"] for row in fresh_mismatch_rows}
            ),
            "permitted_fresh_representation_mismatch_by_stratum": by_stratum(fresh_mismatch_rows),
        }
    general = {row["case_id"]: row for row in records if row["arm"] == "general_rule"}
    ontology = {row["case_id"]: row for row in records if row["arm"] == "ontology_gate"}
    arm_equal = [
        case_id
        for case_id in general
        if _semantic_view(general[case_id]["observed"])
        == _semantic_view(ontology[case_id]["observed"])
    ]
    comparison = {
        "packet_id": packet["packet_id"],
        "packet_version": packet["packet_version"],
        "case_counts": {"normal": 48, "boundary": 4, "malformed": 8, "total": len(cases)},
        "arms": by_arm,
        "general_vs_ontology": {
            "case_count": len(general),
            "equal_case_count": len(arm_equal),
            "mismatch_case_ids": sorted(set(general) - set(arm_equal)),
            "outcome_equal": len(arm_equal) == len(general),
            "interpretation": "same frozen rules; no ontology superiority claim",
        },
        "rule_change_comparison": rule_changes,
        "claim_boundary": {
            "engineering_only": True,
            "not_human_gold": True,
            "not_holdout": True,
            "not_efficacy": True,
            "not_player_benefit": True,
            "not_ontology_superiority": True,
        },
    }
    factual = {
        "status": "PASS"
        if by_arm["general_rule"]["expected_mismatch_count"] == 0
        and by_arm["ontology_gate"]["expected_mismatch_count"] == 0
        and rule_changes["all_fixtures_match"]
        else "FAIL",
        "packet_id": packet["packet_id"],
        "packet_version": packet["packet_version"],
        "case_counts": comparison["case_counts"],
        "arm_observations": by_arm,
        "general_ontology_equal": comparison["general_vs_ontology"]["outcome_equal"],
        "rule_change_fixtures_match": rule_changes["all_fixtures_match"],
        "replay_invariance_failures": sum(row["replay_mismatch_count"] for row in by_arm.values()),
        "unsafe_arm_violations": by_arm["unchecked_isolated"]["unsafe_violation_count"],
        "unchecked_unsafe_case_count": by_arm["unchecked_isolated"]["unique_unsafe_case_count"],
        "unchecked_unsafe_by_stratum": by_arm["unchecked_isolated"]["unsafe_by_stratum"],
        "unchecked_unauthorized_allow_count": by_arm["unchecked_isolated"][
            "unauthorized_allow_count"
        ],
        "unchecked_unauthorized_allow_by_stratum": by_arm["unchecked_isolated"][
            "unauthorized_allow_by_stratum"
        ],
        "unchecked_redisplay_mutation_count": by_arm["unchecked_isolated"][
            "redisplay_mutation_count"
        ],
        "unchecked_redisplay_mutation_by_stratum": by_arm["unchecked_isolated"][
            "redisplay_mutation_by_stratum"
        ],
        "unchecked_semantic_mismatch_count": by_arm["unchecked_isolated"][
            "expected_mismatch_count"
        ],
        "unchecked_semantic_mismatch_by_stratum": by_arm["unchecked_isolated"][
            "semantic_mismatch_by_stratum"
        ],
        "unchecked_permitted_fresh_representation_mismatch_count": by_arm["unchecked_isolated"][
            "permitted_fresh_representation_mismatch_count"
        ],
        "unchecked_permitted_fresh_representation_mismatch_by_stratum": by_arm[
            "unchecked_isolated"
        ]["permitted_fresh_representation_mismatch_by_stratum"],
        "summary_scope": "closed declaration-derived engineering cases only",
        "excluded_claims": [
            "human efficacy",
            "ontology superiority",
            "generalization",
            "free natural-language leakage",
        ],
    }
    metadata = {
        "packet_path": str(contract.packet_path),
        "packet_sha256": contract.packet_sha256,
        "sidecar_sha256": contract.sidecar_sha256,
        "source_hashes": dict(contract.source_hashes_observed),
        "source_hash_mismatches": copy.deepcopy(contract.source_hash_mismatches),
        "baseline_source_integrity": "not_reverified"
        if contract.source_hash_mismatches
        else "verified",
        "current_source_bindings_observed": True,
        **(
            {
                "public_source_bindings": dict(contract.public_source_bindings),
                "observation_scope": "new deterministic Python evaluation; no new Godot or model observation",
            }
            if contract.public_source_bindings is not None
            else {}
        ),
        "contract_version": packet["packet_version"],
        "runtime_ontology": copy.deepcopy(contract.runtime_ontology),
        "arms": list(ARM_NAMES),
        "case_ids": [case["case_id"] for case in cases],
    }
    return EvaluationBundle(tuple(records), comparison, factual, metadata)


def write_evaluation(bundle: EvaluationBundle, output_dir: str | Path) -> dict[str, Path]:
    """Write the agreed raw trace, comparison, factual summary, and metadata files."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "trace": directory / "disclosure-trace.jsonl",
        "comparison": directory / "comparison-summary.json",
        "factual": directory / "factual-summary.json",
        "metadata": directory / "metadata.json",
    }
    with paths["trace"].open("w", encoding="utf-8", newline="\n") as handle:
        for record in bundle.trace_records:
            handle.write(_canonical_json(record) + "\n")
    for key, payload in (
        ("comparison", bundle.comparison_summary),
        ("factual", bundle.factual_summary),
        ("metadata", bundle.metadata),
    ):
        paths[key].write_text(_canonical_json(payload) + "\n", encoding="utf-8")
    return paths


def run_evaluation(
    packet_path: str | Path, output_dir: str | Path, project_root: str | Path | None = None
) -> EvaluationBundle:
    """Load, evaluate, and write a complete source-bound packet."""

    contract = load_frozen_contract(packet_path, project_root)
    bundle = evaluate_contract(contract)
    write_evaluation(bundle, output_dir)
    return bundle


__all__ = [
    "ARM_NAMES",
    "ArmResult",
    "DisclosureContract",
    "DisclosureContractError",
    "EvaluationBundle",
    "canonical_hash",
    "evaluate_case",
    "evaluate_contract",
    "load_contract",
    "load_frozen_contract",
    "run_evaluation",
    "sha256_bytes",
    "write_evaluation",
]
