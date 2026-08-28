"""Live proposal adapter over the authenticated Codex CLI (D-040).

This is the first non-recorded :class:`~nesy_game.experiment.ProposalAdapter`. It
turns one authoritative :class:`WorldState` into a *soft* candidate action and
returns it for deterministic hard validation. It never authorizes anything.

Boundaries this module keeps:

* **No authority.** The adapter returns a candidate. Only the deterministic
  validator/commit path may mutate canonical state.
* **No forbidden identifier in the prompt.** The state projection sent to the
  model is built from the same disclosure policy the validator enforces, so a
  permanently forbidden fact ID is never named in the request. A model cannot
  leak what it was never shown, which is a prompt-side mitigation and not a
  semantic-safety guarantee.
* **Classified failures only.** Transport, schema, and contract problems raise
  :class:`AdapterFailure` so the runner records them under the existing failure
  taxonomy instead of crashing an assignment.
* **Screening, not promoted evidence.** The hosted revision string is recorded
  verbatim; hosted model revisions are unstable, so any result produced with this
  adapter is screening-tier and may not be promoted past ``pilot-only``.
"""

from __future__ import annotations

import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .contracts import WorldState
from .experiment import AdapterFailure, ProposalResponse, candidate_from_mapping
from .runtime import to_jsonable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LIVE_CANDIDATE_SCHEMA = PROJECT_ROOT / "game-track/schemas/codex-live-candidate.schema.json"
_SCRIPTS = PROJECT_ROOT / "scripts"

ENVELOPE_KEYS = {
    "schema_version",
    "request_id",
    "status",
    "claim_boundary",
    "authorization_effect",
    "canonical_state_mutated",
    "hard_validation_required",
    "candidate",
    "assumptions",
    "uncertainties",
}
CANDIDATE_KEYS = {
    "action_id",
    "actor_id",
    "action_type",
    "preconditions",
    "effects",
    "required_objects",
    "used_facts",
    "disclosed_facts",
    "required_quest_stage",
    "quest_stage_effect",
    "narrative_text",
}
_REQUEST_ID_SAFE = re.compile(r"[^A-Za-z0-9._:-]")


def _load_codex_module() -> Any:
    """Import the Codex CLI wrapper without making `scripts/` a package import."""

    if str(_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS))
    try:
        import codex_oauth_llm  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - environment boundary
        raise AdapterFailure(
            "adapter_contract:codex_wrapper_missing", f"cannot import codex wrapper: {exc}"
        ) from exc
    return codex_oauth_llm


def validate_live_candidate(payload: Any, request_id: str) -> bool:
    """Re-check the critical envelope contract locally after model-side schema use."""

    if not isinstance(payload, dict) or set(payload) != ENVELOPE_KEYS:
        return False
    if payload.get("schema_version") != "1.0.0":
        return False
    if payload.get("request_id") != request_id:
        return False
    if payload.get("status") != "candidate":
        return False
    if payload.get("claim_boundary") != "candidate_soft_proposal_only":
        return False
    if payload.get("authorization_effect") != "none":
        return False
    if payload.get("canonical_state_mutated") is not False:
        return False
    if payload.get("hard_validation_required") is not True:
        return False
    candidate = payload.get("candidate")
    if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_KEYS:
        return False
    for field in ("assumptions", "uncertainties"):
        items = payload.get(field)
        if not isinstance(items, list) or len(items) > 16:
            return False
        if any(not isinstance(item, str) for item in items):
            return False
    return True


def visible_state_projection(
    state: WorldState,
    scenario: Mapping[str, Any],
    *,
    include_action_policies: bool = True,
    condition_label: str | None = None,
) -> dict[str, Any]:
    """Build the model-visible view, excluding permanently forbidden fact IDs.

    The exclusion mirrors the validator's own disclosure policy, so the prompt and
    the gate cannot drift apart. Stage-gated IDs stay visible as *names* because the
    validator, not the prompt, decides whether disclosing them is allowed yet.

    ``include_action_policies`` selects the difficulty condition. The
    ``policy_visible`` condition hands the model the full precondition/effect table,
    which makes a valid action nearly transcribable. The ``policy_blind`` condition
    withholds that table and lists only the action-type names, which is the realistic
    generative setting where a proposer must infer the constraint surface.
    """

    if condition_label is None:
        condition_label = "policy_visible" if include_action_policies else "policy_blind"
    payload = to_jsonable(state)
    forbidden: set[str] = set()
    policy = scenario.get("disclosure_policy", {})
    for fact_id in policy.get("permanently_forbidden", []):
        forbidden.add(str(fact_id))
    for actor, facts in (payload.get("forbidden_disclosures") or {}).items():
        del actor
        forbidden.update(str(fact) for fact in facts)

    def strip(values: Any) -> Any:
        if isinstance(values, list):
            return [value for value in values if value not in forbidden]
        return values

    policies = payload.get("action_policies") or {}
    projected = {
        "state_id": payload.get("state_id"),
        "locations": strip(payload.get("locations")),
        "reachable_locations": strip(payload.get("reachable_locations")),
        "object_locations": payload.get("object_locations"),
        "inventory": strip(payload.get("inventory")),
        "facts": strip(payload.get("facts")),
        "quest_stage": payload.get("quest_stage"),
        "npc_knowledge": {
            actor: strip(facts) for actor, facts in (payload.get("npc_knowledge") or {}).items()
        },
    }
    if include_action_policies:
        projected["action_policies"] = policies
    else:
        projected["action_types"] = sorted(policies)
    return {
        "state": projected,
        "condition": condition_label,
        "withheld_fact_count": len(forbidden),
        "withholding_note": (
            "Permanently forbidden fact identifiers are removed from this projection. "
            "Do not invent, guess, or reference any fact that is not listed."
        ),
    }


def build_instruction(request_id: str, projection: Mapping[str, Any], seed: int) -> str:
    """Compose the deterministic instruction text for one proposal request."""

    payload = json.dumps(
        {"request_id": request_id, "seed": seed, "world": projection},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    goal_clause = ""
    if projection.get("condition") == "goal_directed_blind":
        goal_clause = (
            "\nGoal constraint: the action MUST change the world. Either emit at least one "
            "entry in effects, or set quest_stage_effect to a new stage. A do-nothing action "
            "with empty effects and null quest_stage_effect does not satisfy this request."
        )
    if projection.get("condition") in {"policy_blind", "goal_directed_blind"}:
        constraint_rules = (
            "- Use only action_type values listed in world.state.action_types.\n"
            "- The precondition and effect rules for each action type are NOT provided. "
            "Infer a plausible, internally consistent action from the world state.\n"
            "- preconditions should be facts that already hold in world.state.facts.\n"
            "- required_objects should be reachable; disclosed_facts should be facts the "
            "actor knows."
        )
    else:
        constraint_rules = (
            "- Use only action_type values that appear in world.state.action_policies.\n"
            "- preconditions must be facts that already hold in world.state.facts.\n"
            "- effects must be allowed by the chosen action policy, and must include its "
            "required effects.\n"
            "- required_objects must be reachable; disclosed_facts must be facts the actor "
            "knows."
        )
    return f"""You propose ONE candidate game action for a symbolic interactive-fiction world.
You have no authority: a deterministic validator decides whether the action commits.
Do not inspect files, run commands, use tools, or claim that state changed.

Rules for the candidate:
{constraint_rules}
- Never invent identifiers that are absent from the projection.
- Set quest_stage_effect to null unless you intend that exact stage effect.
- Return only one JSON object satisfying the supplied output schema, copying request_id exactly.
{goal_clause}

REQUEST_PAYLOAD={payload}
"""


class CodexProposalAdapter:
    """Propose candidate actions through the authenticated Codex CLI.

    The adapter satisfies the ``ProposalAdapter`` protocol (``model_id``,
    ``model_revision``, ``propose``). ``model_revision`` records the exact hosted
    revision string supplied by the caller, because hosted revisions drift and a
    result may not be attributed to an unpinned model.
    """

    def __init__(
        self,
        *,
        model_id: str,
        model_revision: str,
        scenario: Mapping[str, Any],
        run_label: str = "rq2",
        timeout: int = 300,
        condition: str = "policy_visible",
        codex_module: Any | None = None,
        clock: Any = time.perf_counter,
    ) -> None:
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must be a non-empty string")
        if not isinstance(model_revision, str) or not model_revision.strip():
            raise ValueError("model_revision must be a non-empty string")
        if condition not in {"policy_visible", "policy_blind", "goal_directed_blind"}:
            raise ValueError(
                "condition must be policy_visible, policy_blind, or goal_directed_blind"
            )
        self.model_id = model_id
        self.model_revision = model_revision
        self.condition = condition
        self._scenario = dict(scenario)
        self._run_label = _REQUEST_ID_SAFE.sub("-", run_label) or "run"
        self._timeout = timeout
        self._codex = codex_module
        self._clock = clock
        self.calls: list[dict[str, Any]] = []

    def _module(self) -> Any:
        if self._codex is None:
            self._codex = _load_codex_module()
        return self._codex

    def _request_id(self, scenario_id: str, seed: int) -> str:
        safe_scenario = _REQUEST_ID_SAFE.sub("-", scenario_id)
        return f"{self._run_label}-{safe_scenario}-{seed}"[:128]

    def propose(self, state: WorldState, scenario_id: str, seed: int) -> ProposalResponse:
        codex = self._module()
        request_id = self._request_id(scenario_id, seed)
        projection = visible_state_projection(
            state,
            self._scenario,
            include_action_policies=self.condition == "policy_visible",
            condition_label=self.condition,
        )
        instruction = build_instruction(request_id, projection, seed)

        started = self._clock()
        code, payload = codex.run_prompt(
            request_id=request_id,
            user_prompt=instruction,
            model=self.model_id,
            timeout=self._timeout,
            output_schema=LIVE_CANDIDATE_SCHEMA,
            instruction=instruction,
            validator=validate_live_candidate,
        )
        elapsed_ms = max(0.0, (self._clock() - started) * 1000.0)
        self.calls.append(
            {
                "request_id": request_id,
                "scenario_id": scenario_id,
                "seed": seed,
                "exit_code": code,
                "latency_ms": elapsed_ms,
            }
        )
        if code != 0:
            raise AdapterFailure(
                f"live_transport:{payload.get('error_code', 'unknown')}",
                f"codex request failed with exit code {code}",
            )

        candidate_payload = dict(payload["candidate"])
        if candidate_payload.get("quest_stage_effect") is None:
            candidate_payload.pop("quest_stage_effect")
        candidate = candidate_from_mapping(candidate_payload)
        # Token counts are not exposed by the CLI wrapper; recording zero keeps the
        # accounting schema satisfied while making the missing measurement explicit
        # in `token_accounting_available`.
        return ProposalResponse(
            candidate=candidate,
            provider_latency_ms=elapsed_ms,
            input_tokens=0,
            output_tokens=0,
        )
