#!/usr/bin/env python3
"""Deterministic TR01-TR05 traceability scoring and seeded-control audit (0 LLM calls).

Evaluates frozen TRACE-RPG trace artifacts strictly under
`research/traceability-scoring-20261023/rubric.json` without modifying any frozen
evidence, denominators, or `TODO-RESULT` placeholders.

Outputs:
- `results.json`
- `summary.md`
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.contracts import ActionPolicy, CandidateAction, WorldState, parse_candidate_mapping
from nesy_game.repair import counterexample_guided_repair
from nesy_game.runtime import (
    _apply_valid,
    replay_trace_record,
    to_jsonable,
    verify_trace_record,
)
from nesy_game.validator import VALIDATOR_CHECKS, validate_candidate

RUBRIC_PATH = ROOT / "research/traceability-scoring-20261023/rubric.json"
V2_DIR = ROOT / "research/academic-pipeline/gemini-review-20261113/results-v2"
PILOT_DIR = ROOT / "research/academic-pipeline/stage-04-pilot"
DEFAULT_OUTPUT_DIR = ROOT / "research/traceability-scoring-20261023/seeded-control-audit-v1"

ALLOWED_MISSINGNESS = frozenset({"missing", "stale", "contradicted", "inaccessible", "unverified"})

TR01_LINKS = (
    "task_run_attempt",
    "artifact_revision_or_digest",
    "producing_or_using_activity",
    "responsible_actor",
    "source_locator",
)
TR02_LINKS = (
    "input_or_request",
    "applicable_rule_or_requirement_version",
    "actual_evaluated_check_and_result",
    "emitted_decision",
    "source_locator",
)
TR03_LINKS = (
    "decision",
    "observed_state_or_artifact_outcome",
    "before_after_evidence",
    "denied_or_noop_outcome_when_applicable",
    "source_locator",
)
TR04_LINKS = (
    "triggering_failure_or_unmet_requirement",
    "corrective_change_package",
    "exact_revalidation_execution",
    "observed_result_or_unresolved_state",
    "source_locator",
)
TR05_F_LINKS = (
    "predeclared_requirement",
    "implementing_artifact",
    "relevant_verification_evidence",
    "source_locator",
)
TR05_R_LINKS = (
    "in_scope_change",
    "justified_requirement",
    "source_locator",
)

CORE_RULE_SOURCE_KEYS = (
    "src/nesy_game/validator.py",
    "src/nesy_game/contracts.py",
    "src/nesy_game/runtime.py",
    "research/academic-pipeline/gemini-review-20261113/protocol-v2.json",
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        to_jsonable(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recompute_trace_hash(outcome: Mapping[str, Any]) -> str:
    payload = {
        "status": outcome["status"],
        "state": outcome["state"],
        "candidate": outcome["candidate"],
        "validation": outcome["validation"],
        "attempts": outcome["attempts"],
        "prior_state": outcome["prior_state"],
        "trace": outcome["trace"],
        "trace_context": outcome["trace_context"],
    }
    return _sha256_json(payload)


def _world_state_from_dict(data: Mapping[str, Any]) -> WorldState:
    policies = {
        action_type: ActionPolicy(
            frozenset(policy["required_preconditions"]),
            frozenset(policy["allowed_effects"]),
            frozenset(policy.get("required_effects", [])),
            frozenset(policy.get("allowed_quest_stage_effects", [])),
        )
        for action_type, policy in data["action_policies"].items()
    }
    return WorldState(
        state_id=data["state_id"],
        locations=frozenset(data["locations"]),
        reachable_locations=frozenset(data["reachable_locations"]),
        object_locations=data["object_locations"],
        inventory=frozenset(data["inventory"]),
        facts=frozenset(data["facts"]),
        action_policies=policies,
        npc_knowledge={k: frozenset(v) for k, v in data["npc_knowledge"].items()},
        forbidden_disclosures={k: frozenset(v) for k, v in data["forbidden_disclosures"].items()},
        quest_stage=data["quest_stage"],
    )


def _link_pass() -> dict[str, Any]:
    return {"score": 1, "reason": None}


def _link_fail(reason: str, detail: str) -> dict[str, Any]:
    if reason not in ALLOWED_MISSINGNESS:
        raise ValueError(f"invalid missingness reason: {reason}")
    return {"score": 0, "reason": reason, "detail": detail}


def _summarize_dimension(
    unit_scores: Sequence[Mapping[str, Any]],
    link_names: Sequence[str],
    *,
    inventory_complete: bool = True,
    zero_verified_na_reason: str | None = None,
) -> dict[str, Any]:
    applicable_units = [u for u in unit_scores if u["applicable"]]
    n_d = sum(1 for u in applicable_units if u["complete_chain"] == 1)
    cap_n_d = len(applicable_units)
    l_d = sum(
        u["links"][link]["score"]
        for u in applicable_units
        for link in link_names
    )
    m_d = cap_n_d * len(link_names)

    reason_counts: Counter[str] = Counter()
    link_pass_counts: Counter[str] = Counter()
    for u in applicable_units:
        for link in link_names:
            info = u["links"][link]
            if info["score"] == 1:
                link_pass_counts[link] += 1
            elif info["reason"] is not None:
                reason_counts[info["reason"]] += 1

    if not inventory_complete:
        coverage_status = "INDETERMINATE"
        complete_chain_rate = None
        per_link_rate = None
    elif cap_n_d == 0:
        coverage_status = "N/A" if zero_verified_na_reason else "ZERO_APPLICABLE"
        complete_chain_rate = None
        per_link_rate = None
    else:
        coverage_status = "MEASURED"
        complete_chain_rate = n_d / cap_n_d
        per_link_rate = l_d / m_d if m_d else None

    return {
        "inventory_complete": inventory_complete,
        "coverage_status": coverage_status,
        "zero_na_reason": zero_verified_na_reason if cap_n_d == 0 else None,
        "complete_chain_numerator": n_d,
        "complete_chain_denominator": cap_n_d,
        "complete_chain_rate": complete_chain_rate,
        "per_link_note": "Per-link l_d/m_d is optional and never interchangeable with complete-chain coverage.",
        "per_link_numerator": l_d,
        "per_link_denominator": m_d,
        "per_link_rate": per_link_rate,
        "per_link_verified_counts": {k: link_pass_counts[k] for k in link_names},
        "missingness_reason_counts": dict(sorted(reason_counts.items())),
        "total_units_inspected": len(unit_scores),
        "non_applicable_units": len(unit_scores) - cap_n_d,
    }


def score_v2_row(
    row: Mapping[str, Any],
    *,
    row_locator: str,
    frozen_cases_by_id: Mapping[str, Mapping[str, Any]],
    frozen_case_hashes: Mapping[str, str],
    frozen_inventory_keys: frozenset[tuple[str, str, str]],
    frozen_source_hashes: Mapping[str, str],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    """Deterministically score TR01-TR04 for one frozen results-v2 trace row."""

    case_id = row.get("case_id")
    arm = row.get("arm")
    cohort = row.get("cohort")
    frozen_case = frozen_cases_by_id.get(case_id) if isinstance(case_id, str) else None
    arm_spec = next((a for a in protocol["arms"] if a["id"] == arm), None)

    native_outcome = row.get("native_outcome")
    attempts = row.get("attempts")
    repair_budget = row.get("repair_budget")
    repair_attempt_count = row.get("repair_attempt_count")
    status = row.get("status")
    validation = row.get("validation")
    initial_validation = row.get("initial_validation")

    # ------------------------------------------------------------------
    # TR01: Identity and activity binding
    # ------------------------------------------------------------------
    tr01_links: dict[str, Any] = {}

    # 1. task_run_attempt
    inv_key = (case_id, arm, cohort)
    attempt_seq_ok = (
        isinstance(attempts, list)
        and len(attempts) >= 1
        and all(isinstance(a, Mapping) and a.get("attempt") == idx for idx, a in enumerate(attempts))
        and repair_attempt_count == len(attempts) - 1
    )
    if (case_id, arm, cohort) not in frozen_inventory_keys:
        tr01_links["task_run_attempt"] = _link_fail("missing", "assignment not in frozen inventory")
    elif not attempt_seq_ok:
        tr01_links["task_run_attempt"] = _link_fail(
            "contradicted", "non-contiguous or mismatched attempt sequence"
        )
    elif native_outcome is not None:
        tc = native_outcome.get("trace_context") if isinstance(native_outcome, Mapping) else None
        native_trace = native_outcome.get("trace") if isinstance(native_outcome, Mapping) else None
        if (
            not isinstance(tc, Mapping)
            or tc.get("case_id") != case_id
            or tc.get("arm") != arm
            or tc.get("study_id") != protocol["study_id"]
            or native_outcome.get("attempts") != (len(native_trace) - 1 if isinstance(native_trace, list) else -1)
            or not isinstance(native_trace, list)
            or any(
                not isinstance(entry, Mapping) or entry.get("attempt") != idx
                for idx, entry in enumerate(native_trace)
            )
        ):
            tr01_links["task_run_attempt"] = _link_fail(
                "contradicted", "native_outcome trace_context or attempt index contradicts assignment"
            )
        else:
            tr01_links["task_run_attempt"] = _link_pass()
    else:
        tr01_links["task_run_attempt"] = _link_pass()

    # 2. artifact_revision_or_digest
    row_source_hashes = row.get("source_hashes")
    expected_input_hash = frozen_case_hashes.get(case_id) if isinstance(case_id, str) else None
    if expected_input_hash is None or row.get("input_hash") != expected_input_hash:
        tr01_links["artifact_revision_or_digest"] = _link_fail(
            "stale" if row.get("input_hash") else "missing",
            "input_hash does not match frozen case digest",
        )
    elif not isinstance(row_source_hashes, Mapping) or set(row_source_hashes) != set(frozen_source_hashes):
        tr01_links["artifact_revision_or_digest"] = _link_fail(
            "missing" if not row_source_hashes else "stale",
            "source_hashes key set differs from frozen source_hashes.json",
        )
    elif any(row_source_hashes.get(k) != v for k, v in frozen_source_hashes.items()):
        tr01_links["artifact_revision_or_digest"] = _link_fail(
            "stale",
            "source_hashes contains stale or mismatched artifact digest",
        )
    elif native_outcome is None:
        tr01_links["artifact_revision_or_digest"] = _link_fail(
            "missing",
            "native_outcome checksum receipt is absent",
        )
    elif not isinstance(native_outcome, Mapping) or not verify_trace_record(native_outcome):
        reason = (
            "missing"
            if not isinstance(native_outcome, Mapping) or "trace_hash" not in native_outcome
            else "contradicted"
        )
        tr01_links["artifact_revision_or_digest"] = _link_fail(
            reason,
            "native_outcome failed verify_trace_record",
        )
    else:
        tr01_links["artifact_revision_or_digest"] = _link_pass()

    # 3. producing_or_using_activity
    schema_val = row.get("schema_validation")
    if (
        arm_spec is None
        or repair_budget != arm_spec["repair_budget"]
        or not isinstance(schema_val, Mapping)
        or schema_val.get("valid") is not True
    ):
        tr01_links["producing_or_using_activity"] = _link_fail(
            "contradicted", "arm/repair_budget/schema_validation disagrees with frozen protocol"
        )
    else:
        tr01_links["producing_or_using_activity"] = _link_pass()

    # 4. responsible_actor
    expected_actor = frozen_case["candidate"]["actor_id"] if frozen_case else None
    parsed_cand = row.get("parsed_candidate")
    if (
        not isinstance(parsed_cand, Mapping)
        or not parsed_cand.get("actor_id")
        or parsed_cand.get("actor_id") != expected_actor
        or row.get("model_called") is not False
    ):
        tr01_links["responsible_actor"] = _link_fail(
            "contradicted" if parsed_cand else "missing",
            "actor_id or deterministic model_called flag disagrees with frozen case",
        )
    else:
        tr01_links["responsible_actor"] = _link_pass()

    # 5. source_locator
    if not row_locator:
        tr01_links["source_locator"] = _link_fail("missing", "row locator absent")
    elif native_outcome is None or not isinstance(native_outcome, Mapping) or not native_outcome.get("trace_hash"):
        tr01_links["source_locator"] = _link_fail(
            "missing", "native_outcome trace_hash locator absent"
        )
    else:
        tr01_links["source_locator"] = _link_pass()

    tr01_complete = int(all(v["score"] == 1 for v in tr01_links.values()))

    # ------------------------------------------------------------------
    # TR02: Decision evidence chain (game-action decision unit)
    # ------------------------------------------------------------------
    tr02_links: dict[str, Any] = {}

    # 1. input_or_request
    init_state = row.get("initial_state")
    input_match = False
    if (
        frozen_case is not None
        and isinstance(init_state, Mapping)
        and row.get("before_state_hash") == _sha256_json(init_state)
        and isinstance(attempts, list)
        and len(attempts) >= 1
        and isinstance(row.get("initial_candidate"), Mapping)
        and isinstance(attempts[0].get("candidate"), Mapping)
    ):
        try:
            frozen_cand = parse_candidate_mapping(frozen_case["candidate"], allow_defaults=False)
            init_cand = parse_candidate_mapping(row["initial_candidate"], allow_defaults=False)
            att0_cand = parse_candidate_mapping(attempts[0]["candidate"], allow_defaults=False)
            input_match = init_cand == frozen_cand and att0_cand == frozen_cand
        except Exception:
            input_match = False
    if not input_match:
        tr02_links["input_or_request"] = _link_fail(
            "contradicted" if init_state else "missing",
            "initial candidate or initial state disagrees with frozen input",
        )
    else:
        tr02_links["input_or_request"] = _link_pass()

    # 2. applicable_rule_or_requirement_version
    if (
        not isinstance(row_source_hashes, Mapping)
        or any(row_source_hashes.get(k) != frozen_source_hashes.get(k) for k in CORE_RULE_SOURCE_KEYS)
        or frozen_case is None
        or init_state.get("action_policies") != frozen_case["state"]["action_policies"]
    ):
        tr02_links["applicable_rule_or_requirement_version"] = _link_fail(
            "stale",
            "rule/validator/protocol digest or action_policies version mismatch",
        )
    else:
        tr02_links["applicable_rule_or_requirement_version"] = _link_pass()

    # 3. actual_evaluated_check_and_result
    sem_executed = row.get("semantic_gate_executed") is True
    if not sem_executed:
        tr02_links["actual_evaluated_check_and_result"] = _link_fail(
            "unverified",
            "semantic_validation=NOT_EXECUTED (schema-only bypass)",
        )
    elif not isinstance(validation, Mapping) or tuple(validation.get("checks_run", ())) != VALIDATOR_CHECKS:
        tr02_links["actual_evaluated_check_and_result"] = _link_fail(
            "missing" if not isinstance(validation, Mapping) else "contradicted",
            "checks_run does not match full VALIDATOR_CHECKS",
        )
    else:
        try:
            ws = _world_state_from_dict(init_state)
            all_attempts_match = isinstance(attempts, list) and len(attempts) >= 1
            if all_attempts_match:
                for idx, entry in enumerate(attempts):
                    cand_obj = parse_candidate_mapping(entry["candidate"], allow_defaults=False)
                    expected_val = to_jsonable(validate_candidate(ws, cand_obj))
                    if expected_val != entry.get("validation"):
                        all_attempts_match = False
                        break
                    if idx < len(attempts) - 1 and expected_val["valid"]:
                        all_attempts_match = False
                        break
                if all_attempts_match and attempts[-1].get("validation") != validation:
                    all_attempts_match = False
            if all_attempts_match:
                tr02_links["actual_evaluated_check_and_result"] = _link_pass()
            else:
                tr02_links["actual_evaluated_check_and_result"] = _link_fail(
                    "contradicted",
                    "attempt validation disagrees with deterministic validate_candidate",
                )
        except Exception as exc:
            tr02_links["actual_evaluated_check_and_result"] = _link_fail(
                "contradicted", f"validation verification raised {type(exc).__name__}: {exc}"
            )

    # 4. emitted_decision
    val_valid = validation.get("valid") if isinstance(validation, Mapping) else None
    if not sem_executed:
        # schema_only emits COMMITTED without semantic validation
        tr02_links["emitted_decision"] = _link_fail(
            "unverified", "decision emitted without semantic gate execution"
        )
    elif status not in ("COMMITTED", "HOLD") or not isinstance(val_valid, bool):
        tr02_links["emitted_decision"] = _link_fail("missing", "missing valid decision or validation flag")
    elif (status == "COMMITTED" and not val_valid) or (status == "HOLD" and val_valid):
        tr02_links["emitted_decision"] = _link_fail(
            "contradicted", f"status={status} contradicts validation.valid={val_valid}"
        )
    elif isinstance(native_outcome, Mapping):
        expected_native_status = "commit" if status == "COMMITTED" else "fallback"
        if native_outcome.get("status") != expected_native_status:
            tr02_links["emitted_decision"] = _link_fail(
                "contradicted",
                f"status={status} disagrees with native_outcome.status={native_outcome.get('status')}",
            )
        else:
            tr02_links["emitted_decision"] = _link_pass()
    else:
        tr02_links["emitted_decision"] = _link_fail(
            "missing", "native_outcome receipt missing for emitted decision"
        )

    # 5. source_locator
    if tr01_links["source_locator"]["score"] == 1 and isinstance(validation, Mapping):
        tr02_links["source_locator"] = _link_pass()
    else:
        tr02_links["source_locator"] = _link_fail(
            "missing", "decision evidence locator incomplete without native_outcome"
        )

    tr02_complete = int(all(v["score"] == 1 for v in tr02_links.values()))

    # ------------------------------------------------------------------
    # TR03: Decision-to-effect correspondence
    # ------------------------------------------------------------------
    tr03_links: dict[str, Any] = {}

    # 1. decision
    if tr02_links["emitted_decision"]["score"] == 1:
        tr03_links["decision"] = _link_pass()
    else:
        tr03_links["decision"] = _link_fail(
            tr02_links["emitted_decision"]["reason"] or "unverified",
            "decision link unresolved or contradicted",
        )

    # 2. observed_state_or_artifact_outcome
    final_state = row.get("final_state")
    if native_outcome is None or not isinstance(native_outcome, Mapping):
        tr03_links["observed_state_or_artifact_outcome"] = _link_fail(
            "missing", "native_outcome absent; semantic replay unavailable"
        )
    else:
        try:
            replayed_state = replay_trace_record(native_outcome)
            if to_jsonable(replayed_state) != final_state:
                tr03_links["observed_state_or_artifact_outcome"] = _link_fail(
                    "contradicted", "replay_trace_record state differs from row.final_state"
                )
            elif row.get("after_state_hash") != _sha256_json(final_state):
                tr03_links["observed_state_or_artifact_outcome"] = _link_fail(
                    "contradicted", "after_state_hash differs from final_state digest"
                )
            else:
                tr03_links["observed_state_or_artifact_outcome"] = _link_pass()
        except Exception as exc:
            tr03_links["observed_state_or_artifact_outcome"] = _link_fail(
                "contradicted", f"replay_trace_record failed: {exc}"
            )

    # 3. before_after_evidence
    if (
        isinstance(init_state, Mapping)
        and isinstance(final_state, Mapping)
        and row.get("before_state_hash") == _sha256_json(init_state)
        and row.get("after_state_hash") == _sha256_json(final_state)
        and isinstance(native_outcome, Mapping)
        and native_outcome.get("prior_state") == init_state
        and native_outcome.get("state") == final_state
    ):
        tr03_links["before_after_evidence"] = _link_pass()
    else:
        tr03_links["before_after_evidence"] = _link_fail(
            "missing" if not isinstance(native_outcome, Mapping) else "contradicted",
            "before/after state evidence incomplete or mismatched",
        )

    # 4. denied_or_noop_outcome_when_applicable
    if not isinstance(init_state, Mapping) or not isinstance(final_state, Mapping):
        tr03_links["denied_or_noop_outcome_when_applicable"] = _link_fail(
            "missing", "missing initial or final state"
        )
    elif status == "HOLD":
        if final_state == init_state and row.get("after_state_hash") == row.get("before_state_hash"):
            tr03_links["denied_or_noop_outcome_when_applicable"] = _link_pass()
        else:
            tr03_links["denied_or_noop_outcome_when_applicable"] = _link_fail(
                "contradicted", "HOLD decision mutated world state"
            )
    elif status == "COMMITTED":
        if not sem_executed:
            tr03_links["denied_or_noop_outcome_when_applicable"] = _link_fail(
                "unverified", "COMMITTED without semantic validation gate"
            )
        else:
            try:
                ws = _world_state_from_dict(init_state)
                fc = parse_candidate_mapping(row["final_candidate"], allow_defaults=False)
                expected_ws = to_jsonable(_apply_valid(ws, fc))
                if expected_ws == final_state:
                    tr03_links["denied_or_noop_outcome_when_applicable"] = _link_pass()
                else:
                    tr03_links["denied_or_noop_outcome_when_applicable"] = _link_fail(
                        "contradicted", "COMMITTED state does not equal _apply_valid(prior, final)"
                    )
            except Exception as exc:
                tr03_links["denied_or_noop_outcome_when_applicable"] = _link_fail(
                    "contradicted", f"commit state check failed: {exc}"
                )
    else:
        tr03_links["denied_or_noop_outcome_when_applicable"] = _link_fail(
            "contradicted", f"unexpected status={status}"
        )

    # 5. source_locator
    if tr03_links["before_after_evidence"]["score"] == 1 and tr01_links["source_locator"]["score"] == 1:
        tr03_links["source_locator"] = _link_pass()
    else:
        tr03_links["source_locator"] = _link_fail(
            "missing", "before/after state or native receipt locator incomplete"
        )

    tr03_complete = int(all(v["score"] == 1 for v in tr03_links.values()))

    # ------------------------------------------------------------------
    # TR04: Repair chain
    # Reconciled applicability: actual multi-attempt repair OR protocol
    # requires repair (repair_budget > 0 and initial_validation invalid).
    # ------------------------------------------------------------------
    init_valid = initial_validation.get("valid") if isinstance(initial_validation, Mapping) else None
    has_multiple_attempts = isinstance(attempts, list) and len(attempts) > 1
    has_positive_repair_count = isinstance(repair_attempt_count, int) and repair_attempt_count > 0
    protocol_expects_repair = (
        isinstance(repair_budget, int)
        and repair_budget > 0
        and init_valid is False
        and sem_executed
    )
    tr04_applicable = has_multiple_attempts or has_positive_repair_count or protocol_expects_repair

    tr04_links: dict[str, Any] = {}
    if tr04_applicable:
        # 1. triggering_failure_or_unmet_requirement
        if (
            isinstance(attempts, list)
            and len(attempts) >= 1
            and isinstance(attempts[0].get("validation"), Mapping)
            and attempts[0]["validation"].get("valid") is False
            and len(attempts[0]["validation"].get("errors", [])) >= 1
        ):
            tr04_links["triggering_failure_or_unmet_requirement"] = _link_pass()
        else:
            tr04_links["triggering_failure_or_unmet_requirement"] = _link_fail(
                "contradicted", "missing or passing attempt[0] failure trigger"
            )

        # 2. corrective_change_package
        if not isinstance(attempts, list) or len(attempts) < 2 or not isinstance(repair_attempt_count, int) or repair_attempt_count < 1:
            tr04_links["corrective_change_package"] = _link_fail(
                "missing", "repair attempt omitted from trace log despite repair_budget>0 and initial failure"
            )
        elif not isinstance(native_outcome, Mapping) or len(native_outcome.get("trace", [])) < 2:
            tr04_links["corrective_change_package"] = _link_fail(
                "missing", "native_outcome.trace missing repair attempt"
            )
        else:
            try:
                ws = _world_state_from_dict(init_state)
                c0 = parse_candidate_mapping(attempts[0]["candidate"], allow_defaults=False)
                v0 = validate_candidate(ws, c0)
                if arm == "guided_repair":
                    expected_c1 = to_jsonable(counterexample_guided_repair(ws, c0, v0, 1))
                elif arm == "unchanged_retry":
                    expected_c1 = to_jsonable(c0)
                else:
                    expected_c1 = None
                if expected_c1 is not None and attempts[1].get("candidate") == expected_c1:
                    tr04_links["corrective_change_package"] = _link_pass()
                else:
                    tr04_links["corrective_change_package"] = _link_fail(
                        "contradicted", f"repair delta disagrees with arm={arm} repair operator"
                    )
            except Exception as exc:
                tr04_links["corrective_change_package"] = _link_fail(
                    "contradicted", f"repair delta verification failed: {exc}"
                )

        # 3. exact_revalidation_execution
        if not isinstance(attempts, list) or len(attempts) < 2:
            tr04_links["exact_revalidation_execution"] = _link_fail(
                "missing", "revalidation attempt missing from trace"
            )
        else:
            try:
                ws = _world_state_from_dict(init_state)
                c1 = parse_candidate_mapping(attempts[1]["candidate"], allow_defaults=False)
                v1 = to_jsonable(validate_candidate(ws, c1))
                if attempts[1].get("validation") == v1 and attempts[1].get("attempt") == 1:
                    tr04_links["exact_revalidation_execution"] = _link_pass()
                else:
                    tr04_links["exact_revalidation_execution"] = _link_fail(
                        "contradicted", "revalidation result or attempt index mismatch"
                    )
            except Exception as exc:
                tr04_links["exact_revalidation_execution"] = _link_fail(
                    "contradicted", f"revalidation check failed: {exc}"
                )

        # 4. observed_result_or_unresolved_state
        if not isinstance(attempts, list) or len(attempts) < 2:
            tr04_links["observed_result_or_unresolved_state"] = _link_fail(
                "missing", "post-repair outcome missing due to omitted repair attempt"
            )
        elif tr03_links["observed_state_or_artifact_outcome"]["score"] == 1 and tr02_links["emitted_decision"]["score"] == 1:
            tr04_links["observed_result_or_unresolved_state"] = _link_pass()
        else:
            tr04_links["observed_result_or_unresolved_state"] = _link_fail(
                "contradicted", "post-repair outcome disagrees with revalidation"
            )

        # 5. source_locator
        if (
            tr01_links["source_locator"]["score"] == 1
            and isinstance(row_source_hashes, Mapping)
            and row_source_hashes.get("src/nesy_game/repair.py") == frozen_source_hashes.get("src/nesy_game/repair.py")
        ):
            tr04_links["source_locator"] = _link_pass()
        else:
            tr04_links["source_locator"] = _link_fail(
                "missing" if tr01_links["source_locator"]["score"] == 0 else "stale",
                "repair source locator or repair.py digest unverified",
            )

        tr04_complete = int(all(v["score"] == 1 for v in tr04_links.values()))
    else:
        tr04_complete = None

    return {
        "case_id": case_id,
        "arm": arm,
        "cohort": cohort,
        "outcome_status": "PASS" if status == "COMMITTED" else ("FAIL" if status == "HOLD" else "MISSING"),
        "raw_status": status,
        "repair_attempt_count": repair_attempt_count,
        "TR01": {"applicable": True, "complete_chain": tr01_complete, "links": tr01_links},
        "TR02": {"applicable": True, "complete_chain": tr02_complete, "links": tr02_links},
        "TR03": {"applicable": True, "complete_chain": tr03_complete, "links": tr03_links},
        "TR04": {"applicable": tr04_applicable, "complete_chain": tr04_complete, "links": tr04_links},
    }


def score_tr05_v2(
    protocol: Mapping[str, Any],
    summary: Mapping[str, Any],
    source_hashes: Mapping[str, str],
    input_hashes: Mapping[str, str],
    core_rows: Sequence[Mapping[str, Any]],
    surface_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Score TR05 forward and reverse views separately for results-v2."""

    # Predeclared requirements anchored directly in protocol.json
    forward_specs: list[dict[str, Any]] = [
        {
            "req_id": "Q1_schema_only_bypass",
            "predeclared": protocol["questions"][0],
            "artifacts": ["scripts/run_gemini_review_evaluation.py", "src/nesy_game/validator.py"],
            "verified": summary["core"]["schema_only"]["unsafe_commits"] > 0
            and summary["core"]["semantic_rejection"]["unsafe_commits"] == 0,
            "locator": "protocol.json:questions[0]; summary.json:core.schema_only.unsafe_commits",
        },
        {
            "req_id": "Q2_bounded_repair_and_rates",
            "predeclared": protocol["questions"][1],
            "artifacts": ["src/nesy_game/runtime.py", "src/nesy_game/repair.py", "scripts/review_reference.py"],
            "verified": all(
                summary["core"][arm]["assigned"] == 416
                and summary["core"][arm]["initial_reference_unknown"] == 0
                for arm in ("semantic_rejection", "unchanged_retry", "guided_repair")
            ),
            "locator": "protocol.json:questions[1]; summary.json:core",
        },
        {
            "req_id": "Q3_graph_reachability_crosscheck",
            "predeclared": protocol["questions"][2],
            "artifacts": ["scripts/run_gemini_review_evaluation.py", "scripts/review_reference.py"],
            "verified": summary["graph_agreement"]["assigned"] == 32
            and summary["graph_agreement"]["agreements"] == 32,
            "locator": "protocol.json:questions[2]; summary.json:graph_agreement",
        },
        {
            "req_id": "Q4_structural_signature_retention",
            "predeclared": protocol["questions"][3],
            "artifacts": ["scripts/run_gemini_review_evaluation.py"],
            "verified": summary["core"]["guided_repair"]["valid_retained_signature_count"] == 11
            and summary["core"]["guided_repair"]["repaired_signature_count"] == 2,
            "locator": "protocol.json:questions[3]; summary.json:core.*.valid_retained_signature_count",
        },
        {
            "req_id": "Q5_surface_sentinels_boundary",
            "predeclared": protocol["questions"][4],
            "artifacts": ["scripts/run_gemini_review_evaluation.py", "src/nesy_game/validator.py"],
            "verified": len(surface_rows) == 48
            and summary["surface_pairs"]["guided_repair"]["declared_held"] == 6
            and summary["surface_pairs"]["guided_repair"]["undeclared_committed"] == 6,
            "locator": "protocol.json:questions[4]; summary.json:surface_pairs; surface_rows.jsonl",
        },
        {
            "req_id": "ARM_schema_only",
            "predeclared": protocol["arms"][0]["decision"],
            "artifacts": ["scripts/run_gemini_review_evaluation.py"],
            "verified": sum(1 for r in core_rows if r["arm"] == "schema_only" and r["semantic_gate_executed"] is False) == 416,
            "locator": "protocol.json:arms[0]; rows.jsonl[arm=schema_only]",
        },
        {
            "req_id": "ARM_semantic_rejection",
            "predeclared": protocol["arms"][1]["decision"],
            "artifacts": ["src/nesy_game/runtime.py", "src/nesy_game/validator.py"],
            "verified": sum(1 for r in core_rows if r["arm"] == "semantic_rejection" and r["native_replay_equal"] is True) == 416,
            "locator": "protocol.json:arms[1]; rows.jsonl[arm=semantic_rejection]",
        },
        {
            "req_id": "ARM_unchanged_retry",
            "predeclared": protocol["arms"][2]["decision"],
            "artifacts": ["src/nesy_game/runtime.py"],
            "verified": sum(1 for r in core_rows if r["arm"] == "unchanged_retry" and r["repair_attempt_count"] == 1) == 260
            and summary["core"]["unchanged_retry"]["repair_successes"] == 0,
            "locator": "protocol.json:arms[2]; rows.jsonl[arm=unchanged_retry]",
        },
        {
            "req_id": "ARM_guided_repair",
            "predeclared": protocol["arms"][3]["decision"],
            "artifacts": ["src/nesy_game/runtime.py", "src/nesy_game/repair.py"],
            "verified": sum(1 for r in core_rows if r["arm"] == "guided_repair" and r["repair_attempt_count"] == 1) == 260
            and summary["core"]["guided_repair"]["repair_successes"] == 128,
            "locator": "protocol.json:arms[3]; rows.jsonl[arm=guided_repair]",
        },
        {
            "req_id": "POLICY_disclosure_stage_gate",
            "predeclared": protocol["state_and_policy"]["disclosure"],
            "artifacts": ["src/nesy_game/validator.py", "src/nesy_game/contracts.py"],
            "verified": any(
                r["variant"] == "declared_secret" and r["arm"] == "semantic_rejection" and r["status"] == "HOLD"
                for r in core_rows
            )
            and any(
                r["variant"] == "valid_public_fact" and r["arm"] == "semantic_rejection" and r["status"] == "COMMITTED"
                for r in core_rows
            ),
            "locator": "protocol.json:state_and_policy.disclosure; rows.jsonl",
        },
        {
            "req_id": "REPRO_freeze_input_and_source_hashes",
            "predeclared": protocol["reproducibility"]["freeze"],
            "artifacts": ["research/academic-pipeline/gemini-review-20261113/protocol-v2.json"],
            "verified": all(
                (V2_DIR / fname).exists() and _sha256_file(V2_DIR / fname) == digest
                for fname, digest in input_hashes.items()
            ),
            "locator": "protocol.json:reproducibility.freeze; input_hashes.json",
        },
        {
            "req_id": "REPRO_trace_retention",
            "predeclared": protocol["reproducibility"]["trace"],
            "artifacts": ["src/nesy_game/runtime.py", "scripts/run_gemini_review_evaluation.py"],
            "verified": len(core_rows) == 1664
            and all(r.get("model_called") is False and r.get("seed") is None and r.get("cost_usd") is None for r in core_rows),
            "locator": "protocol.json:reproducibility.trace; rows.jsonl",
        },
    ]

    forward_units: list[dict[str, Any]] = []
    for spec in forward_specs:
        art_ok = all(
            art in source_hashes and (ROOT / art).exists() and _sha256_file(ROOT / art) == source_hashes[art]
            for art in spec["artifacts"]
        )
        links = {
            "predeclared_requirement": _link_pass() if spec["predeclared"] else _link_fail("missing", "missing requirement text"),
            "implementing_artifact": _link_pass() if art_ok else _link_fail("stale", "implementing artifact missing or hash mismatch"),
            "relevant_verification_evidence": _link_pass() if spec["verified"] else _link_fail("contradicted", "verification check failed"),
            "source_locator": _link_pass() if spec["locator"] else _link_fail("missing", "locator missing"),
        }
        forward_units.append(
            {
                "req_id": spec["req_id"],
                "applicable": True,
                "complete_chain": int(all(v["score"] == 1 for v in links.values())),
                "links": links,
            }
        )

    # Reverse view: in-scope artifacts hashed in source_hashes.json directly supporting gemini-review-20261113
    in_scope_artifact_justifications = {
        "research/academic-pipeline/gemini-review-20261113/protocol-v2.json": "REPRO_freeze / study protocol",
        "research/academic-pipeline/gemini-review-20261113/reviewer-source.json": "Frozen review-source provenance",
        "research/academic-pipeline/gemini-review-20261113/review-response.json": "Frozen reviewer response record",
        "scripts/run_gemini_review_evaluation.py": "Q1-Q5 study runner & simulator",
        "scripts/review_reference.py": "Q2-Q3 implementation-separate reference BFS & oracle",
        "src/nesy_game/__init__.py": "Package export surface for nesy_game",
        "src/nesy_game/contracts.py": "WorldState / CandidateAction / ActionPolicy contracts",
        "src/nesy_game/validator.py": "Hard semantic gate (VALIDATOR_CHECKS)",
        "src/nesy_game/repair.py": "State-blind counterexample_guided_repair operator",
        "src/nesy_game/runtime.py": "Bounded execute_with_repair, verify_trace_record, replay_trace_record",
    }
    co_hashed_sibling_modules = sorted(set(source_hashes) - set(in_scope_artifact_justifications))

    reverse_units: list[dict[str, Any]] = []
    for path_str, justification in in_scope_artifact_justifications.items():
        disk_path = ROOT / path_str
        hash_ok = path_str in source_hashes and disk_path.exists() and _sha256_file(disk_path) == source_hashes[path_str]
        links = {
            "in_scope_change": _link_pass() if hash_ok else _link_fail("stale", f"hash mismatch for {path_str}"),
            "justified_requirement": _link_pass() if justification else _link_fail("missing", "missing requirement mapping"),
            "source_locator": _link_pass() if path_str in source_hashes else _link_fail("missing", "absent from source_hashes.json"),
        }
        reverse_units.append(
            {
                "artifact": path_str,
                "applicable": True,
                "complete_chain": int(all(v["score"] == 1 for v in links.values())),
                "links": links,
            }
        )

    return {
        "TR05_forward": _summarize_dimension(forward_units, TR05_F_LINKS, inventory_complete=True),
        "TR05_reverse": _summarize_dimension(reverse_units, TR05_R_LINKS, inventory_complete=True),
        "aggregation_note": "Forward and reverse TR05 rates are reported separately and never averaged.",
        "co_hashed_sibling_modules_disclosed_separately": {
            "count": len(co_hashed_sibling_modules),
            "note": "Hashed automatically via src/nesy_game/*.py glob in run_gemini_review_evaluation.py; belong to sibling studies, not directly invoked by gemini-review-20261113.",
            "paths": co_hashed_sibling_modules,
        },
        "forward_units": forward_units,
        "reverse_units": reverse_units,
    }


def score_stage04_pilot() -> dict[str, Any]:
    """Score TR01-TR05 on stage-04-pilot outcome_record rows separately from results-v2."""

    pilot = json.loads((PILOT_DIR / "pilot-results.json").read_text(encoding="utf-8"))
    manifest = json.loads((PILOT_DIR / "pilot-assignment-manifest.json").read_text(encoding="utf-8"))
    expected_prov = manifest["expected_provenance_by_key"]

    section_results: dict[str, Any] = {}
    for section in ("gate_conformance", "boundary_sentinels", "repair_arms"):
        rows = pilot[section]["rows"]
        by_arm: dict[str, list[dict[str, Any]]] = {}
        for idx, row in enumerate(rows):
            arm_id = row["arm_id"]
            row_id = row.get("fixture_id") or row.get("sentinel_id") or row.get("case_id")
            manifest_key = f"{section}/{row_id}/{arm_id}"
            prov = expected_prov.get(manifest_key)
            rec = row.get("outcome_record")

            # TR01
            tr01_links = {
                "task_run_attempt": _link_pass() if prov is not None else _link_fail("missing", "absent from pilot-assignment-manifest"),
                "artifact_revision_or_digest": (
                    _link_pass()
                    if prov is not None
                    and row.get("config_hash") == prov["config_hash"]
                    and row.get("input_hash") == prov["input_hash"]
                    and isinstance(rec, Mapping)
                    and verify_trace_record(rec)
                    else _link_fail("contradicted", "manifest provenance or trace_hash mismatch")
                ),
                "producing_or_using_activity": (
                    _link_pass() if prov is not None and prov.get("row_class") == "executed" else _link_fail("unverified", "not marked executed")
                ),
                "responsible_actor": (
                    _link_pass()
                    if isinstance(rec, Mapping) and bool(rec.get("candidate", {}).get("actor_id"))
                    else _link_fail("missing", "actor_id missing")
                ),
                "source_locator": _link_pass() if isinstance(rec, Mapping) and bool(rec.get("trace_hash")) else _link_fail("missing", "trace_hash locator missing"),
            }

            # TR02
            tr02_ok_val = False
            if isinstance(rec, Mapping):
                try:
                    ws = _world_state_from_dict(rec["prior_state"])
                    tr02_ok_val = all(
                        to_jsonable(validate_candidate(ws, parse_candidate_mapping(entry["candidate"], allow_defaults=False)))
                        == entry["validation"]
                        for entry in rec["trace"]
                    )
                except Exception:
                    tr02_ok_val = False
            expected_status = "commit" if isinstance(rec, Mapping) and rec["validation"]["valid"] else "fallback"
            tr02_links = {
                "input_or_request": _link_pass() if isinstance(rec, Mapping) and prov is not None and row.get("input_hash") == prov["input_hash"] else _link_fail("contradicted", "input mismatch"),
                "applicable_rule_or_requirement_version": _link_pass() if prov is not None and row.get("config_hash") == prov["config_hash"] else _link_fail("stale", "config_hash mismatch"),
                "actual_evaluated_check_and_result": _link_pass() if tr02_ok_val else _link_fail("contradicted", "validate_candidate mismatch"),
                "emitted_decision": _link_pass() if isinstance(rec, Mapping) and rec.get("status") == expected_status else _link_fail("contradicted", "status vs validation mismatch"),
                "source_locator": _link_pass() if isinstance(rec, Mapping) and bool(rec.get("trace_hash")) else _link_fail("missing", "trace_hash missing"),
            }

            # TR03
            replay_ok = False
            if isinstance(rec, Mapping):
                try:
                    replayed = replay_trace_record(rec)
                    replay_ok = (
                        to_jsonable(replayed) == rec["state"]
                        and _sha256_json(rec["state"]) == row.get("final_state_hash")
                        and _sha256_json(rec["prior_state"]) == row.get("prior_state_hash")
                    )
                except Exception:
                    replay_ok = False
            noop_ok = isinstance(rec, Mapping) and (
                (rec["status"] == "fallback" and rec["state"] == rec["prior_state"])
                or (rec["status"] == "commit" and replay_ok)
            )
            tr03_links = {
                "decision": tr02_links["emitted_decision"],
                "observed_state_or_artifact_outcome": _link_pass() if replay_ok else _link_fail("contradicted", "replay mismatch"),
                "before_after_evidence": _link_pass() if replay_ok else _link_fail("contradicted", "before/after state hash mismatch"),
                "denied_or_noop_outcome_when_applicable": _link_pass() if noop_ok else _link_fail("contradicted", "fallback/commit polarity mismatch"),
                "source_locator": _link_pass() if replay_ok else _link_fail("missing", "replay locator incomplete"),
            }

            # TR04
            budget = row.get("repair_budget", 0)
            init_valid = isinstance(rec, Mapping) and rec["trace"][0]["validation"]["valid"]
            tr04_applicable = (isinstance(rec, Mapping) and rec["attempts"] > 0) or (budget > 0 and not init_valid)
            tr04_links: dict[str, Any] = {}
            if tr04_applicable:
                has_two = isinstance(rec, Mapping) and len(rec["trace"]) >= 2 and rec["attempts"] >= 1
                tr04_links = {
                    "triggering_failure_or_unmet_requirement": _link_pass() if not init_valid else _link_fail("contradicted", "initial valid"),
                    "corrective_change_package": _link_pass() if has_two else _link_fail("missing", "missing repair attempt"),
                    "exact_revalidation_execution": _link_pass() if (has_two and tr02_ok_val) else _link_fail("contradicted", "revalidation mismatch"),
                    "observed_result_or_unresolved_state": _link_pass() if (has_two and replay_ok) else _link_fail("contradicted", "post-repair state mismatch"),
                    "source_locator": _link_pass() if (has_two and bool(rec.get("trace_hash"))) else _link_fail("missing", "repair locator missing"),
                }

            unit = {
                "unit_id": manifest_key,
                "arm_id": arm_id,
                "outcome_status": "PASS" if row.get("final_status") == "commit" else "FAIL",
                "TR01": {"applicable": True, "complete_chain": int(all(v["score"] == 1 for v in tr01_links.values())), "links": tr01_links},
                "TR02": {"applicable": True, "complete_chain": int(all(v["score"] == 1 for v in tr02_links.values())), "links": tr02_links},
                "TR03": {"applicable": True, "complete_chain": int(all(v["score"] == 1 for v in tr03_links.values())), "links": tr03_links},
                "TR04": {
                    "applicable": tr04_applicable,
                    "complete_chain": int(all(v["score"] == 1 for v in tr04_links.values())) if tr04_applicable else None,
                    "links": tr04_links,
                },
            }
            by_arm.setdefault(arm_id, []).append(unit)

        arm_summaries = {}
        for arm_id, units in by_arm.items():
            arm_summaries[arm_id] = {
                "unit_count": len(units),
                "outcomes": dict(Counter(u["outcome_status"] for u in units)),
                "TR01": _summarize_dimension([u["TR01"] for u in units], TR01_LINKS),
                "TR02": _summarize_dimension([u["TR02"] for u in units], TR02_LINKS),
                "TR03": _summarize_dimension([u["TR03"] for u in units], TR03_LINKS),
                "TR04": _summarize_dimension(
                    [u["TR04"] for u in units],
                    TR04_LINKS,
                    zero_verified_na_reason=(
                        "Verified zero repair attempts (repair_budget=0, single attempt in trace)."
                        if all(not u["TR04"]["applicable"] for u in units)
                        else None
                    ),
                ),
            }
        section_results[section] = {
            "row_count": len(rows),
            "by_arm": arm_summaries,
        }

    return {
        "pilot_id": pilot["pilot_id"],
        "schema_version": pilot["schema_version"],
        "assignment_set_hash": manifest["assignment_set_hash"],
        "sections_scored": section_results,
    }


# ----------------------------------------------------------------------
# Seeded corruptions (5) & Invariance controls (3)
# ------------------------------------------------------------------

def _reverse_dict_keys(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _reverse_dict_keys(obj[k]) for k in reversed(list(obj.keys()))}
    if isinstance(obj, list):
        return [_reverse_dict_keys(x) for x in obj]
    return obj


def _apply_seeded_corruption(
    row: Mapping[str, Any],
    corruption_kind: str,
) -> tuple[str, dict[str, Any] | None, str]:
    """Return (applicability_status, mutated_row_or_none, note).

    `applicability_status` is one of `valid`, `inapplicable`, `malformed`.
    """
    mutated = deepcopy(dict(row))

    if corruption_kind == "remove_receipt":
        if mutated.get("native_outcome") is None:
            return "inapplicable", None, "row already lacks native_outcome receipt"
        mutated["native_outcome"] = None
        mutated["native_replay_equal"] = None
        return "valid", mutated, "removed native_outcome checksummed receipt"

    if corruption_kind == "swap_attempt_id":
        no = mutated.get("native_outcome")
        attempts = mutated.get("attempts")
        if not isinstance(no, dict) or not isinstance(no.get("trace"), list) or len(no["trace"]) < 2:
            return "inapplicable", None, "single-attempt row has no pair of attempt IDs to swap"
        # Swap attempt 0 and 1 identifiers in both trace and attempts, AND recompute trace_hash
        # to prove detection does not rely solely on checksum mismatch.
        no["trace"][0]["attempt"], no["trace"][1]["attempt"] = (
            no["trace"][1]["attempt"],
            no["trace"][0]["attempt"],
        )
        if isinstance(attempts, list) and len(attempts) >= 2:
            attempts[0]["attempt"], attempts[1]["attempt"] = (
                attempts[1]["attempt"],
                attempts[0]["attempt"],
            )
        no["trace_hash"] = _recompute_trace_hash(no)
        return "valid", mutated, "swapped attempt IDs 0<->1 and recomputed trace_hash"

    if corruption_kind == "bind_old_artifact_revision":
        sh = mutated.get("source_hashes")
        if not isinstance(sh, dict) or "src/nesy_game/validator.py" not in sh:
            return "malformed", None, "missing source_hashes validator entry"
        sh["src/nesy_game/validator.py"] = hashlib.sha256(b"stale-validator-revision-v0").hexdigest()
        return "valid", mutated, "bound stale validator.py digest in source_hashes"

    if corruption_kind == "reverse_decision_or_status":
        no = mutated.get("native_outcome")
        if not isinstance(no, dict):
            return "inapplicable", None, "native_outcome absent"
        if mutated.get("status") == "COMMITTED":
            mutated["status"] = "HOLD"
            no["status"] = "fallback"
        elif mutated.get("status") == "HOLD":
            mutated["status"] = "COMMITTED"
            no["status"] = "commit"
        else:
            return "malformed", None, f"unexpected status {mutated.get('status')!r}"
        # Recompute trace_hash so detection proves semantic/replay checking, not mere hash drift.
        no["trace_hash"] = _recompute_trace_hash(no)
        return "valid", mutated, "reversed status & native_outcome.status with recomputed trace_hash"

    if corruption_kind == "omit_failed_repair":
        no = mutated.get("native_outcome")
        attempts = mutated.get("attempts")
        if (
            not isinstance(no, dict)
            or not isinstance(attempts, list)
            or len(attempts) < 2
            or mutated.get("status") != "HOLD"
            or mutated.get("repair_attempt_count", 0) < 1
        ):
            return "inapplicable", None, "unit does not contain a failed repair attempt"
        # Omit the failed repair attempt and recompute trace_hash on the truncated trace.
        mutated["attempts"] = attempts[:1]
        mutated["repair_attempt_count"] = 0
        no["trace"] = no["trace"][:1]
        no["attempts"] = 0
        no["trace_hash"] = _recompute_trace_hash(no)
        return "valid", mutated, "omitted failed repair attempt[1] and recomputed trace_hash"

    raise ValueError(f"unknown corruption_kind: {corruption_kind}")


def _apply_invariance_control(row: Mapping[str, Any], control_kind: str) -> dict[str, Any]:
    if control_kind == "clean_duplicate":
        return deepcopy(dict(row))

    if control_kind == "irrelevant_decorative_addition":
        mutated = deepcopy(dict(row))
        mutated["decorative_ui_badge"] = "gold-star-verified"
        mutated["ontology_visual_theme"] = {
            "layout": "hierarchical",
            "color": "#22aa88",
            "rdf_hint": "prov:Activity",
        }
        mutated["explanatory_prose"] = "Irrelevant decorative annotation excluded from rubric links."
        return mutated

    if control_kind == "semantics_preserving_format_change":
        # Reverse key order recursively, serialize with indent=2 & ensure_ascii=True,
        # simulate CSV-stringified nested columns round-trip, and parse back.
        reversed_obj = _reverse_dict_keys(deepcopy(dict(row)))
        pretty_ascii = json.dumps(reversed_obj, ensure_ascii=True, indent=2)
        parsed = json.loads(pretty_ascii)
        csv_like = {
            k: (json.dumps(v, ensure_ascii=True) if isinstance(v, (dict, list)) else v)
            for k, v in parsed.items()
        }
        round_tripped = {
            k: (json.loads(v) if isinstance(parsed[k], (dict, list)) else v)
            for k, v in csv_like.items()
        }
        return round_tripped

    raise ValueError(f"unknown invariance control_kind: {control_kind}")


def _score_signature(score: Mapping[str, Any]) -> tuple[Any, ...]:
    return tuple(
        (
            dim,
            score[dim]["applicable"],
            score[dim]["complete_chain"],
            tuple(
                (link, score[dim]["links"][link]["score"], score[dim]["links"][link]["reason"])
                for link in sorted(score[dim]["links"])
            ),
        )
        for dim in ("TR01", "TR02", "TR03", "TR04")
    )


def run_audit(output_dir: Path) -> dict[str, Any]:
    t_start = time.perf_counter()

    rubric = json.loads(RUBRIC_PATH.read_text(encoding="utf-8"))
    protocol = json.loads((V2_DIR / "protocol.json").read_text(encoding="utf-8"))
    summary_v2 = json.loads((V2_DIR / "summary.json").read_text(encoding="utf-8"))
    cases = json.loads((V2_DIR / "cases.json").read_text(encoding="utf-8"))
    surface_cases = json.loads((V2_DIR / "surface_sentinels.json").read_text(encoding="utf-8"))
    inventory = json.loads((V2_DIR / "assignment_inventory.json").read_text(encoding="utf-8"))
    source_hashes = json.loads((V2_DIR / "source_hashes.json").read_text(encoding="utf-8"))
    input_hashes = json.loads((V2_DIR / "input_hashes.json").read_text(encoding="utf-8"))

    core_rows = [
        json.loads(line)
        for line in (V2_DIR / "rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    surface_rows = [
        json.loads(line)
        for line in (V2_DIR / "surface_rows.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    # Verify inventory completeness against frozen assignment_inventory.json
    observed_keys = {(r["case_id"], r["arm"], r["cohort"]) for r in core_rows + surface_rows}
    frozen_inventory_keys = frozenset((x["case_id"], x["arm"], x["cohort"]) for x in inventory)
    inventory_complete = (
        len(core_rows) + len(surface_rows) == len(inventory)
        and observed_keys == frozen_inventory_keys
    )

    frozen_cases_by_id: dict[str, Mapping[str, Any]] = {
        c["case_id"]: c for c in cases + surface_cases
    }
    frozen_case_hashes: dict[str, str] = {
        cid: _sha256_json(c) for cid, c in frozen_cases_by_id.items()
    }

    # Verify disk hashes of frozen inputs & sources
    input_hash_checks = {
        fname: ((V2_DIR / fname).exists() and _sha256_file(V2_DIR / fname) == digest)
        for fname, digest in input_hashes.items()
    }
    source_hash_checks = {
        rel: ((ROOT / rel).exists() and _sha256_file(ROOT / rel) == digest)
        for rel, digest in source_hashes.items()
    }

    # ------------------------------------------------------------------
    # 1. Baseline TR01-TR05 scoring on frozen results-v2 (by cohort & arm)
    # ------------------------------------------------------------------
    scored_core_by_arm: dict[str, list[dict[str, Any]]] = {}
    baseline_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for idx, row in enumerate(core_rows, start=1):
        sc = score_v2_row(
            row,
            row_locator=f"research/academic-pipeline/gemini-review-20261113/results-v2/rows.jsonl:{idx}",
            frozen_cases_by_id=frozen_cases_by_id,
            frozen_case_hashes=frozen_case_hashes,
            frozen_inventory_keys=frozen_inventory_keys,
            frozen_source_hashes=source_hashes,
            protocol=protocol,
        )
        scored_core_by_arm.setdefault(row["arm"], []).append(sc)
        baseline_by_key[(row["case_id"], row["arm"], row["cohort"])] = sc

    scored_surface_by_arm: dict[str, list[dict[str, Any]]] = {}
    for idx, row in enumerate(surface_rows, start=1):
        sc = score_v2_row(
            row,
            row_locator=f"research/academic-pipeline/gemini-review-20261113/results-v2/surface_rows.jsonl:{idx}",
            frozen_cases_by_id=frozen_cases_by_id,
            frozen_case_hashes=frozen_case_hashes,
            frozen_inventory_keys=frozen_inventory_keys,
            frozen_source_hashes=source_hashes,
            protocol=protocol,
        )
        scored_surface_by_arm.setdefault(row["arm"], []).append(sc)

    def _arm_summary(units: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return {
            "unit_count": len(units),
            "decision_scope": "game_action_decisions_only (coding_decisions=0)",
            "outcomes_independent_of_traceability": dict(Counter(u["outcome_status"] for u in units)),
            "TR01": _summarize_dimension([u["TR01"] for u in units], TR01_LINKS, inventory_complete=inventory_complete),
            "TR02": _summarize_dimension([u["TR02"] for u in units], TR02_LINKS, inventory_complete=inventory_complete),
            "TR03": _summarize_dimension([u["TR03"] for u in units], TR03_LINKS, inventory_complete=inventory_complete),
            "TR04": _summarize_dimension(
                [u["TR04"] for u in units],
                TR04_LINKS,
                inventory_complete=inventory_complete,
                zero_verified_na_reason=(
                    "Verified zero repair attempts (repair_budget=0 or all initial attempts valid)."
                    if all(not u["TR04"]["applicable"] for u in units)
                    else None
                ),
            ),
        }

    v2_core_summary = {arm: _arm_summary(units) for arm, units in scored_core_by_arm.items()}
    v2_surface_summary = {arm: _arm_summary(units) for arm, units in scored_surface_by_arm.items()}
    v2_tr05 = score_tr05_v2(protocol, summary_v2, source_hashes, input_hashes, core_rows, surface_rows)

    # ------------------------------------------------------------------
    # 2. Secondary frozen cohort: stage-04-pilot/pilot-results.json
    # ------------------------------------------------------------------
    pilot_scores = score_stage04_pilot()

    # ------------------------------------------------------------------
    # 3. Seeded corruptions & Invariance controls on all 1,248 clean native units
    # ------------------------------------------------------------------
    clean_native_rows = [r for r in core_rows if r["arm"] != "schema_only"]
    # Verify every clean native unit passes baseline TR01-TR04 (when applicable)
    clean_baseline_failures = 0
    for r in clean_native_rows:
        base = baseline_by_key[(r["case_id"], r["arm"], r["cohort"])]
        if base["TR01"]["complete_chain"] != 1 or base["TR02"]["complete_chain"] != 1 or base["TR03"]["complete_chain"] != 1:
            clean_baseline_failures += 1
        if base["TR04"]["applicable"] and base["TR04"]["complete_chain"] != 1:
            clean_baseline_failures += 1
    if clean_baseline_failures != 0:
        raise RuntimeError(f"Expected 0 clean baseline failures, observed {clean_baseline_failures}")

    corruption_kinds = tuple(rubric["controls"]["seeded_corruptions"])
    invariance_kinds = tuple(rubric["controls"]["invariance_controls"])

    corruption_results: dict[str, Any] = {}
    total_seeded_valid = 0
    total_detected_valid = 0
    total_inapplicable = 0
    total_malformed = 0

    for c_kind in corruption_kinds:
        valid_count = 0
        detected_count = 0
        inapplicable_count = 0
        malformed_count = 0
        triggered_dims: Counter[str] = Counter()
        triggered_reasons: Counter[str] = Counter()
        by_arm_counts: dict[str, dict[str, int]] = {}

        for idx, row in enumerate(clean_native_rows, start=1):
            arm = row["arm"]
            arm_bucket = by_arm_counts.setdefault(
                arm, {"valid": 0, "detected": 0, "inapplicable": 0, "malformed": 0}
            )
            app_status, mutated_row, _ = _apply_seeded_corruption(row, c_kind)
            if app_status == "inapplicable":
                inapplicable_count += 1
                arm_bucket["inapplicable"] += 1
                continue
            if app_status == "malformed" or mutated_row is None:
                malformed_count += 1
                arm_bucket["malformed"] += 1
                continue

            valid_count += 1
            arm_bucket["valid"] += 1
            base = baseline_by_key[(row["case_id"], row["arm"], row["cohort"])]
            scored = score_v2_row(
                mutated_row,
                row_locator=f"seeded-control:{c_kind}:{row['case_id']}:{row['arm']}",
                frozen_cases_by_id=frozen_cases_by_id,
                frozen_case_hashes=frozen_case_hashes,
                frozen_inventory_keys=frozen_inventory_keys,
                frozen_source_hashes=source_hashes,
                protocol=protocol,
            )

            degraded = False
            for dim in ("TR01", "TR02", "TR03", "TR04"):
                if base[dim]["applicable"] and base[dim]["complete_chain"] == 1:
                    if not scored[dim]["applicable"] or scored[dim]["complete_chain"] != 1:
                        degraded = True
                        triggered_dims[dim] += 1
                        for link_info in scored[dim]["links"].values():
                            if link_info["score"] == 0 and link_info["reason"] is not None:
                                triggered_reasons[link_info["reason"]] += 1
            if degraded:
                detected_count += 1
                arm_bucket["detected"] += 1

        total_seeded_valid += valid_count
        total_detected_valid += detected_count
        total_inapplicable += inapplicable_count
        total_malformed += malformed_count
        corruption_results[c_kind] = {
            "seeded_valid_corruptions": valid_count,
            "detected_valid_corruptions": detected_count,
            "detection_rate_sensitivity": (detected_count / valid_count) if valid_count else None,
            "inapplicable_controls_retained_separately": inapplicable_count,
            "malformed_controls_retained_separately": malformed_count,
            "triggered_dimensions": dict(sorted(triggered_dims.items())),
            "triggered_missingness_reasons": dict(sorted(triggered_reasons.items())),
            "by_arm": by_arm_counts,
        }

    invariance_results: dict[str, Any] = {}
    total_clean_controls = 0
    total_false_alarms = 0

    for inv_kind in invariance_kinds:
        unit_count = 0
        false_alarms = 0
        by_arm_counts_inv: dict[str, dict[str, int]] = {}

        for row in clean_native_rows:
            arm = row["arm"]
            arm_bucket = by_arm_counts_inv.setdefault(arm, {"clean_units": 0, "false_alarms": 0})
            unit_count += 1
            arm_bucket["clean_units"] += 1

            transformed = _apply_invariance_control(row, inv_kind)
            base = baseline_by_key[(row["case_id"], row["arm"], row["cohort"])]
            scored = score_v2_row(
                transformed,
                row_locator=f"invariance-control:{inv_kind}:{row['case_id']}:{row['arm']}",
                frozen_cases_by_id=frozen_cases_by_id,
                frozen_case_hashes=frozen_case_hashes,
                frozen_inventory_keys=frozen_inventory_keys,
                frozen_source_hashes=source_hashes,
                protocol=protocol,
            )
            if _score_signature(scored) != _score_signature(base):
                false_alarms += 1
                arm_bucket["false_alarms"] += 1

        total_clean_controls += unit_count
        total_false_alarms += false_alarms
        invariance_results[inv_kind] = {
            "clean_control_units": unit_count,
            "false_alarms": false_alarms,
            "false_alarm_rate": (false_alarms / unit_count) if unit_count else None,
            "invariance_preservation_rate": ((unit_count - false_alarms) / unit_count) if unit_count else None,
            "by_arm": by_arm_counts_inv,
        }

    elapsed_seconds = time.perf_counter() - t_start
    total_units_evaluated = (
        len(core_rows)
        + len(surface_rows)
        + sum(s["row_count"] for s in pilot_scores["sections_scored"].values())
        + total_seeded_valid
        + total_clean_controls
    )

    results = {
        "schema_version": "1.0",
        "audit_id": "traceability-seeded-control-audit-v1",
        "rubric_id": rubric["id"],
        "rubric_status": rubric["status"],
        "llm_calls": 0,
        "model_called": False,
        "reliability": {
            "human_assessors": 0,
            "krippendorff_alpha": "UNDEFINED",
            "status": "NOT_ESTIMABLE",
            "note": (
                "Deterministic automated scoring over frozen trace records and seeded controls; "
                "no two independent human assessors were run, so human inter-rater reliability "
                "remains UNDEFINED per rubric.json."
            ),
        },
        "frozen_integrity_preflight": {
            "v2_inventory_complete": inventory_complete,
            "v2_inventory_expected": len(inventory),
            "v2_core_rows": len(core_rows),
            "v2_surface_rows": len(surface_rows),
            "v2_input_hashes_matched": sum(input_hash_checks.values()),
            "v2_input_hashes_total": len(input_hash_checks),
            "v2_source_hashes_matched": sum(source_hash_checks.values()),
            "v2_source_hashes_total": len(source_hash_checks),
        },
        "seeded_control_summary": {
            "clean_native_pool_size": len(clean_native_rows),
            "clean_baseline_failures": clean_baseline_failures,
            "seeded_valid_corruptions": total_seeded_valid,
            "detected_valid_corruptions": total_detected_valid,
            "overall_detector_sensitivity": (
                total_detected_valid / total_seeded_valid if total_seeded_valid else None
            ),
            "inapplicable_controls_retained_separately": total_inapplicable,
            "malformed_controls_retained_separately": total_malformed,
            "clean_control_units": total_clean_controls,
            "false_alarms": total_false_alarms,
            "overall_false_alarm_rate": (
                total_false_alarms / total_clean_controls if total_clean_controls else None
            ),
            "overall_invariance_preservation_rate": (
                (total_clean_controls - total_false_alarms) / total_clean_controls
                if total_clean_controls
                else None
            ),
            "by_corruption_type": corruption_results,
            "by_invariance_type": invariance_results,
        },
        "baseline_frozen_trace_scores": {
            "aggregation_rule": "Never average TR01-TR05, forward/reverse TR05, outcomes, or distinct cohorts.",
            "cohort_1_gemini_review_v2": {
                "source_dir": "research/academic-pipeline/gemini-review-20261113/results-v2",
                "core_by_arm": v2_core_summary,
                "surface_by_arm": v2_surface_summary,
                "TR05": v2_tr05,
            },
            "cohort_2_stage_04_pilot": {
                "source_dir": "research/academic-pipeline/stage-04-pilot",
                "pilot_scores": pilot_scores,
            },
        },
        "audit_burden": {
            "note": "Burden is a reporting quantity, not a traceability score.",
            "total_runtime_seconds": round(elapsed_seconds, 4),
            "total_units_evaluated": total_units_evaluated,
            "ms_per_unit": round((elapsed_seconds * 1000.0) / total_units_evaluated, 4),
            "human_assessor_minutes_per_unit": None,
            "access_failures": 0,
        },
        "nonclaims": [
            "Human inter-rater reliability (Krippendorff alpha) is UNDEFINED; this script executes deterministic rubric checks and seeded controls only.",
            "Frozen denominators (SL-PLAY-EVAL-001 52/52, SL-BALANCE-PROBE-001 5/5, C-RESULT-* TODO-RESULT) and frozen artifacts were not modified.",
            "Seeded control sensitivity verifies deterministic rubric-detector behavior on known synthetic fault injections, not prospective human assessor agreement or development-comparison-20261023 execution.",
            "Traceability completeness (TR01-TR05) does not imply task success, semantic correctness, or safety (e.g., failed repairs in unchanged_retry score 1 on TR04 while remaining HOLD/FAIL).",
        ],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "summary.md").write_text(
        render_summary_md(results),
        encoding="utf-8",
    )
    return results


def _fmt_ratio(dim: Mapping[str, Any]) -> str:
    if dim["coverage_status"] == "N/A":
        return "N/A (0/0)"
    if dim["coverage_status"] == "INDETERMINATE":
        return f"INDETERMINATE ({dim['complete_chain_numerator']}/{dim['complete_chain_denominator']})"
    pct = 100.0 * dim["complete_chain_rate"]
    return f"{dim['complete_chain_numerator']}/{dim['complete_chain_denominator']} ({pct:.1f}%)"


def render_summary_md(results: Mapping[str, Any]) -> str:
    sc = results["seeded_control_summary"]
    pre = results["frozen_integrity_preflight"]
    v2 = results["baseline_frozen_trace_scores"]["cohort_1_gemini_review_v2"]
    pilot = results["baseline_frozen_trace_scores"]["cohort_2_stage_04_pilot"]["pilot_scores"]
    burden = results["audit_burden"]

    lines: list[str] = [
        "# Traceability Seeded Control Audit (`seeded-control-audit-v1`)",
        "",
        f"- **Rubric:** `{results['rubric_id']}` (`status={results['rubric_status']}`)",
        f"- **LLM Calls:** `{results['llm_calls']}` (`model_called={results['model_called']}`)",
        f"- **Human Inter-Rater Reliability (`krippendorff_alpha`):** **`{results['reliability']['krippendorff_alpha']}`** (`{results['reliability']['status']}` — zero human assessors; automated deterministic scorer only)",
        f"- **Frozen Input/Source Preflight:** inventory `{pre['v2_core_rows']}+{pre['v2_surface_rows']}/{pre['v2_inventory_expected']}` (`complete={pre['v2_inventory_complete']}`), `input_hashes` `{pre['v2_input_hashes_matched']}/{pre['v2_input_hashes_total']}`, `source_hashes` `{pre['v2_source_hashes_matched']}/{pre['v2_source_hashes_total']}`",
        "",
        "## 1. Seeded Corruption Sensitivity & Invariance False-Alarm Rates",
        "",
        f"- **Clean native baseline pool:** `{sc['clean_native_pool_size']}` units (`semantic_rejection` + `unchanged_retry` + `guided_repair`, baseline failures=`{sc['clean_baseline_failures']}`)",
        f"- **Overall detector sensitivity (`detected_valid_corruptions / seeded_valid_corruptions`):** **`{sc['detected_valid_corruptions']}/{sc['seeded_valid_corruptions']}`** (`{100.0 * sc['overall_detector_sensitivity']:.2f}%`)",
        f"- **Inapplicable controls retained separately:** `{sc['inapplicable_controls_retained_separately']}` (`malformed={sc['malformed_controls_retained_separately']}`)",
        f"- **Overall invariance false-alarm rate (`false_alarms / clean_control_units`):** **`{sc['false_alarms']}/{sc['clean_control_units']}`** (`{100.0 * sc['overall_false_alarm_rate']:.2f}%`, invariance preservation=`{100.0 * sc['overall_invariance_preservation_rate']:.2f}%`)",
        "",
        "### Seeded Corruption Controls (5 types)",
        "",
        "| Corruption Control | Detected / Valid | Sensitivity | Inapplicable (Separate) | Triggered Dimensions | Primary Missingness Reasons |",
        "|---|---:|---:|---:|---|---|",
    ]
    for c_kind, info in sc["by_corruption_type"].items():
        sens = f"{100.0 * info['detection_rate_sensitivity']:.1f}%" if info["detection_rate_sensitivity"] is not None else "N/A"
        dims = ", ".join(f"{k}:{v}" for k, v in info["triggered_dimensions"].items())
        reasons = ", ".join(f"{k}:{v}" for k, v in info["triggered_missingness_reasons"].items())
        lines.append(
            f"| `{c_kind}` | {info['detected_valid_corruptions']}/{info['seeded_valid_corruptions']} | {sens} | {info['inapplicable_controls_retained_separately']} | {dims} | {reasons} |"
        )

    lines.extend([
        "",
        "### Invariance Controls (3 types)",
        "",
        "| Invariance Control | False Alarms / Clean Units | False-Alarm Rate | Invariance Preserved |",
        "|---|---:|---:|---:|",
    ])
    for inv_kind, info in sc["by_invariance_type"].items():
        far = f"{100.0 * info['false_alarm_rate']:.1f}%"
        pres = f"{100.0 * info['invariance_preservation_rate']:.1f}%"
        lines.append(
            f"| `{inv_kind}` | {info['false_alarms']}/{info['clean_control_units']} | {far} | {pres} |"
        )

    lines.extend([
        "",
        "## 2. Baseline `TR01-TR05` Complete-Chain Scores (Frozen Artifacts)",
        "",
        "> Per `rubric.json`: `TR01-TR05`, forward/reverse `TR05`, outcomes, and cohorts are never averaged or collapsed.",
        "",
        "### Cohort 1: `gemini-review-20261113/results-v2` — Core (`n=1,664` across 4 arms)",
        "",
        "| Arm | Units | Outcomes (`PASS/FAIL`) | TR01 | TR02 | TR03 | TR04 |",
        "|---|---:|---|---|---|---|---|",
    ])
    for arm, info in v2["core_by_arm"].items():
        out_str = f"{info['outcomes_independent_of_traceability'].get('PASS', 0)}/{info['outcomes_independent_of_traceability'].get('FAIL', 0)}"
        lines.append(
            f"| `{arm}` | {info['unit_count']} | {out_str} | {_fmt_ratio(info['TR01'])} | {_fmt_ratio(info['TR02'])} | {_fmt_ratio(info['TR03'])} | {_fmt_ratio(info['TR04'])} |"
        )

    lines.extend([
        "",
        "### Cohort 1: `gemini-review-20261113/results-v2` — Surface Sentinels (`n=48` across 4 arms)",
        "",
        "| Arm | Units | Outcomes (`PASS/FAIL`) | TR01 | TR02 | TR03 | TR04 |",
        "|---|---:|---|---|---|---|---|",
    ])
    for arm, info in v2["surface_by_arm"].items():
        out_str = f"{info['outcomes_independent_of_traceability'].get('PASS', 0)}/{info['outcomes_independent_of_traceability'].get('FAIL', 0)}"
        lines.append(
            f"| `{arm}` | {info['unit_count']} | {out_str} | {_fmt_ratio(info['TR01'])} | {_fmt_ratio(info['TR02'])} | {_fmt_ratio(info['TR03'])} | {_fmt_ratio(info['TR04'])} |"
        )

    tr05_f = v2["TR05"]["TR05_forward"]
    tr05_r = v2["TR05"]["TR05_reverse"]
    lines.extend([
        "",
        "### Cohort 1: `TR05` Bidirectional Requirement Coverage (Separate Views)",
        "",
        f"- **`TR05_forward` (`n_05F / N_05F`):** `{_fmt_ratio(tr05_f)}` (predeclared `protocol.json` requirements -> implementing artifacts -> verified evidence)",
        f"- **`TR05_reverse` (`n_05R / N_05R`):** `{_fmt_ratio(tr05_r)}` (in-scope hashed artifacts -> justified `gemini-review-20261113` requirements; `{v2['TR05']['co_hashed_sibling_modules_disclosed_separately']['count']}` co-hashed sibling modules in `source_hashes.json` disclosed separately)",
        "",
        "### Cohort 2: `stage-04-pilot/pilot-results.json` (`n=63` `outcome_record` rows)",
        "",
        "| Section | Arm | Units | TR01 | TR02 | TR03 | TR04 |",
        "|---|---|---:|---|---|---|---|",
    ])
    for sec, sec_info in pilot["sections_scored"].items():
        for arm, info in sec_info["by_arm"].items():
            lines.append(
                f"| `{sec}` | `{arm}` | {info['unit_count']} | {_fmt_ratio(info['TR01'])} | {_fmt_ratio(info['TR02'])} | {_fmt_ratio(info['TR03'])} | {_fmt_ratio(info['TR04'])} |"
            )

    lines.extend([
        "",
        "## 3. Audit Burden & Non-Claims",
        "",
        f"- **Runtime wall-clock:** `{burden['total_runtime_seconds']}s` across `{burden['total_units_evaluated']}` total unit evaluations (`{burden['ms_per_unit']} ms/unit`, `access_failures={burden['access_failures']}`).",
        "- **Non-claims:**",
    ])
    for nc in results["nonclaims"]:
        lines.append(f"  - {nc}")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Destination directory for results.json and summary.md",
    )
    args = parser.parse_args()
    results = run_audit(args.output_dir)
    sc = results["seeded_control_summary"]
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "llm_calls": results["llm_calls"],
                "krippendorff_alpha": results["reliability"]["krippendorff_alpha"],
                "seeded_valid_corruptions": sc["seeded_valid_corruptions"],
                "detected_valid_corruptions": sc["detected_valid_corruptions"],
                "overall_detector_sensitivity": sc["overall_detector_sensitivity"],
                "inapplicable_controls_retained_separately": sc["inapplicable_controls_retained_separately"],
                "clean_control_units": sc["clean_control_units"],
                "false_alarms": sc["false_alarms"],
                "overall_false_alarm_rate": sc["overall_false_alarm_rate"],
                "runtime_seconds": results["audit_burden"]["total_runtime_seconds"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
