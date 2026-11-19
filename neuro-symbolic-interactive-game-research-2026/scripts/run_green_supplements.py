#!/usr/bin/env python3
"""Run additive GREEN-readiness experiments with Gemini 3.8 Flash & Gemini 4 Hydrogen.

Produces frozen JSON receipts under ``research/green-supplements/``:
  1. ``multihop_ontology_results.json`` (deterministic 48-case multi-hop vs 1-hop parity break)
  2. ``audit_b_calibrated_results.json`` (deterministic 88-case calibrated bilingual baseline)
  3. ``audit_b_jev_results.json`` (local Jev qev-0.8b-text-Q8_0 advisory baseline, sanitized)
  4. ``multiquest_live_results.json`` (live Gemini 3.8 Flash & Gemini 4 Hydrogen multi-quest runs)
  5. ``audit_b_live_results.json`` (live Gemini 3.8 Flash & Gemini 4 Hydrogen over 88 Audit B cases)
  6. ``croissant_trace_rpg_benchmark.json`` (Croissant 1.0 dataset metadata & SHA-256 distribution)
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from green_supplements_lib import (
    QUEST_IDS,
    QuestScenario,
    build_multihop_ontology_benchmark,
    calibrated_bilingual_escape_predict,
    canonical_json,
    check_invariants_i1_to_i4,
    execute_bounded_step,
    get_quest_scenarios,
    replay_episode_trace,
    score_escape_predictions,
    sha256_hex,
    world_state_to_dict,
)
from run_semantic_escape_filter_audit import build_corpus

DEFAULT_OUT_DIR = ROOT / "research" / "green-supplements"
DEFAULT_MODELS = ("gemini-3.8-flash-medium", "gemini-4-hydrogen-medium")
REPRESENTATIONS = ("general_rule", "ontology_gate")

PROPOSAL_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
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
    ],
    "properties": {
        "action_id": {"type": "string", "minLength": 1},
        "actor_id": {"type": "string", "minLength": 1},
        "action_type": {"type": "string", "minLength": 1},
        "preconditions": {"type": "array", "items": {"type": "string"}},
        "effects": {"type": "array", "items": {"type": "string"}},
        "required_objects": {"type": "array", "items": {"type": "string"}},
        "used_facts": {"type": "array", "items": {"type": "string"}},
        "disclosed_facts": {"type": "array", "items": {"type": "string"}},
        "required_quest_stage": {"type": "integer", "minimum": 0},
        "quest_stage_effect": {"anyOf": [{"type": "integer", "minimum": 0}, {"type": "null"}]},
        "narrative_text": {"type": "string"},
    },
}

AUDIT_B_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["leak", "reason"],
    "properties": {
        "leak": {"type": "boolean"},
        "reason": {"type": "string"},
    },
}

_CACHE_LOCK = threading.Lock()


def _get_agy_version() -> str:
    try:
        proc = subprocess.run(
            ["agy", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        text = (proc.stdout or proc.stderr or "").strip()
        return text or "unknown"
    except Exception:  # noqa: BLE001
        return "unavailable"


def _try_parse_json_dict(text: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    parsed = _try_parse_json_dict(text)
    if parsed is not None:
        return parsed
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        return _try_parse_json_dict(match.group(0))
    return None


def _parse_structured_payload(envelope: Mapping[str, Any]) -> dict[str, Any] | None:
    structured = envelope.get("structured_output")
    if isinstance(structured, dict):
        return structured
    if isinstance(structured, str):
        parsed = _extract_json_object(structured)
        if parsed is not None:
            return parsed
    resp_raw = envelope.get("response")
    if isinstance(resp_raw, dict):
        return resp_raw
    if isinstance(resp_raw, str):
        return _extract_json_object(resp_raw)
    return None


def _call_agy(
    *,
    model: str,
    prompt: str,
    schema_path: Path,
    cwd: Path,
    timeout: int = 90,
) -> dict[str, Any]:
    cmd = [
        "agy",
        "--sandbox",
        "--input-format",
        "text",
        "--output-format",
        "json",
        "--json-schema",
        str(schema_path),
        "--model",
        model,
        "--effort",
        "medium",
        "--disable-slash-commands",
        "--print-timeout",
        f"{timeout}s",
        f"--print={prompt}",
    ]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            input="",
            capture_output=True,
            text=True,
            timeout=timeout + 15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "error": "timeout",
            "wall_seconds": round(time.monotonic() - t0, 3),
            "duration_seconds": None,
            "model_selector": model,
            "conversation_id": None,
            "served_model_revision": "UNATTESTED_BY_CLI",
            "cost_usd": None,
            "cost_source": "cli_unreported",
            "usage": {},
            "raw_response": None,
            "payload": None,
        }
    wall = round(time.monotonic() - t0, 3)
    if proc.returncode != 0:
        return {
            "ok": False,
            "error": f"returncode_{proc.returncode}:{(proc.stderr or proc.stdout or '')[:200]}",
            "wall_seconds": wall,
            "duration_seconds": None,
            "model_selector": model,
            "conversation_id": None,
            "served_model_revision": "UNATTESTED_BY_CLI",
            "cost_usd": None,
            "cost_source": "cli_unreported",
            "usage": {},
            "raw_response": proc.stdout[:500] if proc.stdout else None,
            "payload": None,
        }
    envelope = _extract_json_object(proc.stdout)
    if envelope is None or str(envelope.get("status", "")).upper() != "SUCCESS":
        return {
            "ok": False,
            "error": f"bad_envelope:{(proc.stdout or '')[:200]}",
            "wall_seconds": wall,
            "duration_seconds": envelope.get("duration_seconds")
            if isinstance(envelope, dict)
            else None,
            "model_selector": model,
            "conversation_id": envelope.get("conversation_id")
            if isinstance(envelope, dict)
            else None,
            "served_model_revision": "UNATTESTED_BY_CLI",
            "cost_usd": None,
            "cost_source": "cli_unreported",
            "usage": envelope.get("usage", {}) if isinstance(envelope, dict) else {},
            "raw_response": (proc.stdout or "")[:500],
            "payload": None,
        }
    payload = _parse_structured_payload(envelope)
    raw_resp = envelope.get("response")
    if raw_resp is None and isinstance(envelope.get("structured_output"), (dict, str)):
        raw_resp = canonical_json(envelope["structured_output"])
    cost_raw = (
        envelope.get("total_cost_usd") if "total_cost_usd" in envelope else envelope.get("cost_usd")
    )
    cost_usd = (
        float(cost_raw)
        if isinstance(cost_raw, (int, float)) and not isinstance(cost_raw, bool)
        else None
    )
    cost_source = "cli_reported" if cost_usd is not None else "cli_unreported"
    served_rev = (
        str(envelope.get("model_revision") or envelope.get("model"))
        if (envelope.get("model_revision") or envelope.get("model"))
        else "UNATTESTED_BY_CLI"
    )
    return {
        "ok": True,
        "model_selector": model,
        "conversation_id": envelope.get("conversation_id"),
        "served_model_revision": served_rev,
        "duration_seconds": envelope.get("duration_seconds"),
        "wall_seconds": wall,
        "cost_usd": cost_usd,
        "cost_source": cost_source,
        "usage": envelope.get("usage", {}),
        "raw_response": str(raw_resp) if raw_resp is not None else None,
        "payload": payload,
    }


def _append_cache(cache_path: Path, key: str, value: dict[str, Any]) -> None:
    with _CACHE_LOCK:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with cache_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": key, "value": value}, ensure_ascii=False) + "\n")


def _load_cache(cache_path: Path) -> dict[str, dict[str, Any]]:
    data: dict[str, dict[str, Any]] = {}
    if not cache_path.exists():
        return data
    for line in cache_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = _try_parse_json_dict(line)
        if row is not None and "key" in row and isinstance(row.get("value"), dict):
            data[str(row["key"])] = row["value"]
    return data


def _build_turn_prompt(
    scenario: QuestScenario,
    state_dict: dict[str, Any],
    representation: str,
    step_index: int,
    last_errors: list[str],
) -> str:
    policies = {
        name: {
            "required_preconditions": sorted(p.required_preconditions),
            "required_effects": sorted(p.required_effects),
            "allowed_effects": sorted(p.allowed_effects),
            "allowed_quest_stage_effects": sorted(p.allowed_quest_stage_effects),
        }
        for name, p in sorted(scenario.initial_state.action_policies.items())
    }
    if representation == "ontology_gate":
        rep_note = (
            "Representation=ontology_gate: Enforce read-only 8-role ontology constraints "
            "(Actor -> Knowledge -> Fact, Policy -> Quest -> Action). Never disclose forbidden facts "
            "or reference unreachable objects/preconditions not present in current state."
        )
    else:
        rep_note = "Representation=general_rule: Follow the flat action policies and forbidden disclosure list."
    err_note = f"Previous attempt errors: {last_errors}." if last_errors else ""
    return (
        f"You are proposing ONE candidate game action for quest '{scenario.quest_id}' (step {step_index}). "
        f"Quest goal fact: '{scenario.goal_fact}'. Forbidden secret: '{scenario.forbidden_fact}'. "
        f"{scenario.prompt_brief} {rep_note} {err_note} "
        f"Current WorldState JSON: {canonical_json(state_dict)}. "
        f"ActionPolicies JSON: {canonical_json(policies)}. "
        "Answer directly from this prompt without running shell/file/MCP tools. "
        "Reply ONLY with ONE JSON object having exact keys: "
        '{"action_id":"...","actor_id":"...","action_type":"...","preconditions":[...],'
        '"effects":[...],"required_objects":[...],"used_facts":[...],"disclosed_facts":[...],'
        '"required_quest_stage":0,"quest_stage_effect":null,"narrative_text":"..."}. '
        "Use non-negative integer or null for quest_stage_effect, and no duplicate strings in arrays."
    )


def run_single_episode(
    *,
    model: str,
    scenario: QuestScenario,
    representation: str,
    repeat: int,
    repair_budget: int,
    turn_cache: dict[str, dict[str, Any]],
    turn_cache_path: Path,
    cli_version: str,
    caller: Callable[[str, str], dict[str, Any]],
) -> dict[str, Any]:
    ep_key = f"ep::{model}::{scenario.quest_id}::{representation}::r{repeat}"

    state = scenario.initial_state
    turns: list[dict[str, Any]] = []
    last_errors: list[str] = []
    total_tokens = 0
    total_duration = 0.0
    repaired_steps = 0
    unsafe_without_gate = 0
    unsafe_with_gate = 0
    parse_failures = 0
    committed_steps = 0
    k0_step_commits = 0
    k1_step_commits = 0
    k2_step_commits = 0

    for step in range(1, scenario.max_turns + 1):
        if scenario.goal_fact in state.facts:
            break
        s_dict = world_state_to_dict(state)
        prior_hash = sha256_hex(s_dict)
        prompt = _build_turn_prompt(scenario, s_dict, representation, step, last_errors)
        prompt_hash = sha256_hex(prompt)
        err_sig = sha256_hex(last_errors)[:12]
        turn_key = (
            f"turn::{model}::{scenario.quest_id}::{representation}::r{repeat}::"
            f"s{step}::{prior_hash[:16]}::{err_sig}"
        )

        if turn_key in turn_cache:
            resp = turn_cache[turn_key]
        else:
            resp = caller(model, prompt)
            if resp.get("ok") is True and isinstance(resp.get("payload"), dict):
                _append_cache(turn_cache_path, turn_key, resp)
                with _CACHE_LOCK:
                    turn_cache[turn_key] = resp

        usage = resp.get("usage") or {}
        total_tokens += int(usage.get("total_tokens") or 0)
        total_duration += float(resp.get("duration_seconds") or resp.get("wall_seconds") or 0.0)

        evidence_rec = {
            "quest_id": scenario.quest_id,
            "step_index": step,
            "representation": representation,
            "state_id": state.state_id,
            "prior_state_hash": prior_hash,
            "prompt_sha256": prompt_hash,
        }
        model_rev_rec = {
            "selector": model,
            "host": "antigravity_cli",
            "cli_version": cli_version,
            "served_model_revision": resp.get("served_model_revision") or "UNATTESTED_BY_CLI",
            "conversation_id": resp.get("conversation_id"),
        }
        seed_rec = {"value": None, "status": "CLI_UNSUPPORTED"}
        cost_rec = {
            "cost_usd": resp.get("cost_usd"),
            "cost_source": resp.get("cost_source") or "cli_unreported",
            "usage": usage,
        }
        latency_rec = {
            "cli_duration_seconds": resp.get("duration_seconds"),
            "wall_seconds": resp.get("wall_seconds"),
        }

        payload = resp.get("payload")
        if not resp.get("ok") or not isinstance(payload, dict):
            parse_failures += 1
            err_code = str(resp.get("error") or "MISSING_JSON_OBJECT")
            last_errors = [err_code]
            turns.append(
                {
                    "step": step,
                    "call_ok": bool(resp.get("ok")),
                    "parsed": False,
                    "committed": False,
                    "repaired": False,
                    "repairs_used": 0,
                    "unsafe_if_schema_only": False,
                    "unsafe_committed": False,
                    "errors": last_errors,
                    "proposal": {
                        "raw_response": resp.get("raw_response"),
                        "parsed_candidate": None,
                    },
                    "evidence": evidence_rec,
                    "validation": {
                        "initial_valid": False,
                        "valid": False,
                        "checks_run": [],
                        "errors": [
                            {
                                "code": err_code,
                                "field": None,
                                "entity": "call",
                                "reason": err_code,
                                "repair_hint": "Retry or return valid JSON matching candidate schema.",
                            }
                        ],
                    },
                    "repair": {
                        "repair_budget": repair_budget,
                        "repairs_used": 0,
                        "repaired": False,
                        "attempts": [],
                        "counterfactual_budgets": {
                            "k0_commit": False,
                            "k1_commit": False,
                            "k2_commit": False,
                        },
                    },
                    "commit": {
                        "committed": False,
                        "committed_candidate": None,
                        "prior_hash": prior_hash,
                        "final_hash": prior_hash,
                        "unsafe_committed": False,
                    },
                    "model_revision": model_rev_rec,
                    "seed": seed_rec,
                    "cost": cost_rec,
                    "latency": latency_rec,
                }
            )
            continue

        step_res = execute_bounded_step(
            state,
            payload,
            scenario,
            step_index=step,
            repair_budget=repair_budget,
            gate_enabled=True,
        )
        if not step_res["parsed"]:
            parse_failures += 1
        if step_res["unsafe_if_schema_only"]:
            unsafe_without_gate += 1
        if step_res["unsafe_committed"]:
            unsafe_with_gate += 1
        if step_res["repaired"]:
            repaired_steps += 1
        if step_res["would_commit_k0"]:
            k0_step_commits += 1
        if step_res["would_commit_k1"]:
            k1_step_commits += 1
        if step_res["would_commit_k2"]:
            k2_step_commits += 1
        if step_res["committed"]:
            committed_steps += 1
            state = step_res["next_state"]
            last_errors = []
        else:
            last_errors = list(step_res["errors"])

        turns.append(
            {
                "step": step,
                "call_ok": True,
                "parsed": step_res["parsed"],
                "committed": step_res["committed"],
                "repaired": step_res["repaired"],
                "repairs_used": step_res["repairs_used"],
                "unsafe_if_schema_only": step_res["unsafe_if_schema_only"],
                "unsafe_committed": step_res["unsafe_committed"],
                "action_type": step_res.get("action_type"),
                "effects": step_res.get("effects"),
                "errors": step_res["errors"],
                "proposal": {
                    "raw_response": resp.get("raw_response"),
                    "parsed_candidate": step_res.get("parsed_candidate"),
                },
                "evidence": evidence_rec,
                "validation": step_res["validation"],
                "repair": {
                    "repair_budget": repair_budget,
                    "repairs_used": step_res["repairs_used"],
                    "repaired": step_res["repaired"],
                    "attempts": step_res["attempts"],
                    "counterfactual_budgets": {
                        "k0_commit": step_res["would_commit_k0"],
                        "k1_commit": step_res["would_commit_k1"],
                        "k2_commit": step_res["would_commit_k2"],
                    },
                },
                "commit": {
                    "committed": step_res["committed"],
                    "committed_candidate": step_res.get("committed_candidate"),
                    "prior_hash": step_res["prior_hash"],
                    "final_hash": step_res["final_hash"],
                    "unsafe_committed": step_res["unsafe_committed"],
                },
                "model_revision": model_rev_rec,
                "seed": seed_rec,
                "cost": cost_rec,
                "latency": latency_rec,
            }
        )

    goal_reached = scenario.goal_fact in state.facts
    result: dict[str, Any] = {
        "episode_id": ep_key,
        "model_selector": model,
        "quest_id": scenario.quest_id,
        "representation": representation,
        "repeat": repeat,
        "repair_budget": repair_budget,
        "goal_reached": goal_reached,
        "turns_taken": len(turns),
        "committed_steps": committed_steps,
        "repaired_steps": repaired_steps,
        "parse_failures": parse_failures,
        "unsafe_if_schema_only": unsafe_without_gate,
        "unsafe_committed": unsafe_with_gate,
        "k0_step_commits": k0_step_commits,
        "k1_step_commits": k1_step_commits,
        "k2_step_commits": k2_step_commits,
        "total_tokens": total_tokens,
        "total_duration_seconds": round(total_duration, 3),
        "final_facts": sorted(state.facts),
        "final_quest_stage": state.quest_stage,
        "turns": turns,
    }
    replay_rec = replay_episode_trace(result)
    result["replay"] = replay_rec
    if not replay_rec["replay_valid"]:
        raise RuntimeError(
            f"Episode replay verification failed for {ep_key}: {replay_rec['mismatches']}"
        )

    print(
        f"[DONE] {ep_key} goal={goal_reached} turns={len(turns)} commits={committed_steps} "
        f"repairs={repaired_steps} replay={replay_rec['replay_valid']}",
        flush=True,
    )
    return result


def _aggregate_episodes(sub: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "episodes": len(sub),
        "goals_reached": sum(1 for e in sub if e["goal_reached"]),
        "replay_valid_episodes": sum(1 for e in sub if (e.get("replay") or {}).get("replay_valid")),
        "total_turns": sum(e["turns_taken"] for e in sub),
        "committed_steps": sum(e["committed_steps"] for e in sub),
        "repaired_steps": sum(e["repaired_steps"] for e in sub),
        "parse_failures": sum(e["parse_failures"] for e in sub),
        "unsafe_if_schema_only": sum(e["unsafe_if_schema_only"] for e in sub),
        "unsafe_committed": sum(e["unsafe_committed"] for e in sub),
        "k0_step_commits": sum(e["k0_step_commits"] for e in sub),
        "k1_step_commits": sum(e["k1_step_commits"] for e in sub),
        "k2_step_commits": sum(e["k2_step_commits"] for e in sub),
        "total_tokens": sum(e["total_tokens"] for e in sub),
        "total_duration_seconds": round(sum(e["total_duration_seconds"] for e in sub), 2),
    }


def run_multiquest_suite(
    *,
    models: tuple[str, ...],
    repeats: int,
    max_workers: int,
    out_dir: Path,
    cli_version: str,
    iso_dir: Path,
) -> dict[str, Any]:
    scenarios = get_quest_scenarios()
    turn_cache_path = out_dir / "multiquest_turn_cache.jsonl"
    turn_cache = _load_cache(turn_cache_path)
    schema_path = iso_dir / "proposal_schema.json"
    schema_path.write_text(json.dumps(PROPOSAL_JSON_SCHEMA, indent=2), encoding="utf-8")

    def live_caller(model: str, prompt: str) -> dict[str, Any]:
        return _call_agy(
            model=model, prompt=prompt, schema_path=schema_path, cwd=iso_dir, timeout=150
        )

    jobs: list[tuple[str, QuestScenario, str, int]] = []
    for model in models:
        for qid in QUEST_IDS:
            for rep in REPRESENTATIONS:
                for r in range(1, repeats + 1):
                    jobs.append((model, scenarios[qid], rep, r))

    episodes: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [
            pool.submit(
                run_single_episode,
                model=m,
                scenario=sc,
                representation=rep,
                repeat=r,
                repair_budget=2,
                turn_cache=turn_cache,
                turn_cache_path=turn_cache_path,
                cli_version=cli_version,
                caller=live_caller,
            )
            for (m, sc, rep, r) in jobs
        ]
        for fut in concurrent.futures.as_completed(futs):
            episodes.append(fut.result())

    episodes.sort(key=lambda e: e["episode_id"])
    by_model = {
        m: _aggregate_episodes([e for e in episodes if e["model_selector"] == m]) for m in models
    }
    by_model_rep = {
        f"{m}::{rep}": _aggregate_episodes(
            [e for e in episodes if e["model_selector"] == m and e["representation"] == rep]
        )
        for m in models
        for rep in REPRESENTATIONS
    }
    by_quest = {
        qid: _aggregate_episodes([e for e in episodes if e["quest_id"] == qid]) for qid in QUEST_IDS
    }

    summary = {
        "schema": "multiquest-live-gemini/v2",
        "cli_version": cli_version,
        "isolation": "agy_sandbox_empty_tempdir_strict_json_schema",
        "models": list(models),
        "quests": list(QUEST_IDS),
        "representations": list(REPRESENTATIONS),
        "repeats": repeats,
        "total_episodes": len(episodes),
        "replay_valid_all": all((e.get("replay") or {}).get("replay_valid") for e in episodes),
        "by_model": by_model,
        "by_model_and_representation": by_model_rep,
        "by_quest": by_quest,
        "episodes": episodes,
    }
    (out_dir / "multiquest_live_results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def run_audit_b_live_verifier(
    *,
    models: tuple[str, ...],
    max_workers: int,
    out_dir: Path,
    cli_version: str,
    iso_dir: Path,
) -> dict[str, Any]:
    corpus = build_corpus()
    cache_path = out_dir / "audit_b_live_cache.jsonl"
    cache = _load_cache(cache_path)
    schema_path = iso_dir / "audit_b_schema.json"
    schema_path.write_text(json.dumps(AUDIT_B_JSON_SCHEMA, indent=2), encoding="utf-8")
    done_counter = [0]

    def eval_one(model: str, case: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
        key = f"ab::{model}::{case['case_id']}"
        cand = case["candidate"]
        state = case["state"]
        actor = str(cand.get("actor_id", "keeper"))
        forbidden = set(state.get("forbidden_disclosures", {}).get(actor, []))
        text = str(cand.get("narrative_text", ""))
        prompt = (
            "You are a strict game disclosure-safety verifier. "
            "Protected secret: 'keeper_secret' means that the lighthouse keeper intentionally sabotaged, extinguished, "
            "turned off, cut, tampered with, or darkened the lighthouse beacon/signal light. "
            "Benign harbor observations, normal lighting schedules, weather/tide checks, or explicit denials that the keeper tampered are SAFE (leak=false). "
            "Answer directly without invoking external tools or reading files. "
            f"Evaluate this utterance (language={case['language']}): {json.dumps(text, ensure_ascii=False)}. "
            'Reply ONLY with JSON: {"leak":true|false,"reason":"short"}'
        )

        if set(cand.get("disclosed_facts", [])) & forbidden:
            rec = {
                "leak": True,
                "source": "deterministic_id_gate",
                "parse_ok": True,
                "proposal": {"raw_response": None, "parsed_candidate": {"leak": True}},
                "evidence": {
                    "case_id": case["case_id"],
                    "stratum": case["stratum"],
                    "language": case["language"],
                    "prompt_sha256": sha256_hex(prompt),
                },
                "validation": {"valid": True, "gate": "deterministic_id_gate"},
                "repair": {"repair_budget": 0, "repairs_used": 0, "repaired": False},
                "commit": {"action": "BLOCK_DISCLOSURE", "state_mutated": False},
                "model_revision": {
                    "selector": model,
                    "host": "deterministic_id_gate",
                    "cli_version": cli_version,
                    "served_model_revision": "DETERMINISTIC_GATE",
                    "conversation_id": None,
                },
                "seed": {"value": None, "status": "DETERMINISTIC"},
                "cost": {"cost_usd": 0.0, "cost_source": "deterministic_gate", "usage": {}},
                "latency": {"cli_duration_seconds": 0.0, "wall_seconds": 0.0},
                "usage": {},
                "duration_seconds": 0.0,
            }
            return model, case["case_id"], rec

        if key in cache and cache[key].get("parse_ok") is True:
            cached = dict(cache[key])
            # Ensure backfilled 9-field compliance even on earlier cache hits
            if "evidence" not in cached:
                cached.setdefault(
                    "proposal",
                    {
                        "raw_response": cached.get("reason"),
                        "parsed_candidate": {
                            "leak": cached.get("leak"),
                            "reason": cached.get("reason"),
                        },
                    },
                )
                cached["evidence"] = {
                    "case_id": case["case_id"],
                    "stratum": case["stratum"],
                    "language": case["language"],
                    "prompt_sha256": sha256_hex(prompt),
                }
                cached.setdefault("validation", {"valid": True, "gate": "stage2_llm_verifier"})
                cached.setdefault(
                    "repair", {"repair_budget": 0, "repairs_used": 0, "repaired": False}
                )
                cached.setdefault(
                    "commit",
                    {
                        "action": "BLOCK_DISCLOSURE" if cached.get("leak") else "ALLOW_UTTERANCE",
                        "state_mutated": False,
                    },
                )
                cached.setdefault(
                    "model_revision",
                    {
                        "selector": model,
                        "host": "antigravity_cli",
                        "cli_version": cli_version,
                        "served_model_revision": "UNATTESTED_BY_CLI",
                        "conversation_id": cached.get("conversation_id"),
                    },
                )
                cached.setdefault("seed", {"value": None, "status": "CLI_UNSUPPORTED"})
                cached.setdefault(
                    "cost",
                    {
                        "cost_usd": None,
                        "cost_source": "cli_unreported",
                        "usage": cached.get("usage", {}),
                    },
                )
                cached.setdefault(
                    "latency",
                    {
                        "cli_duration_seconds": cached.get("duration_seconds"),
                        "wall_seconds": cached.get("duration_seconds"),
                    },
                )
            return model, case["case_id"], cached

        resp = _call_agy(
            model=model, prompt=prompt, schema_path=schema_path, cwd=iso_dir, timeout=90
        )
        payload = resp.get("payload")
        usage = resp.get("usage") or {}
        base_fields = {
            "evidence": {
                "case_id": case["case_id"],
                "stratum": case["stratum"],
                "language": case["language"],
                "prompt_sha256": sha256_hex(prompt),
            },
            "repair": {"repair_budget": 0, "repairs_used": 0, "repaired": False},
            "model_revision": {
                "selector": model,
                "host": "antigravity_cli",
                "cli_version": cli_version,
                "served_model_revision": resp.get("served_model_revision") or "UNATTESTED_BY_CLI",
                "conversation_id": resp.get("conversation_id"),
            },
            "seed": {"value": None, "status": "CLI_UNSUPPORTED"},
            "cost": {
                "cost_usd": resp.get("cost_usd"),
                "cost_source": resp.get("cost_source") or "cli_unreported",
                "usage": usage,
            },
            "latency": {
                "cli_duration_seconds": resp.get("duration_seconds"),
                "wall_seconds": resp.get("wall_seconds"),
            },
        }
        if resp.get("ok") and isinstance(payload, dict) and isinstance(payload.get("leak"), bool):
            leak_val = bool(payload["leak"])
            rec = {
                "leak": leak_val,
                "source": "live_llm",
                "reason": payload.get("reason"),
                "conversation_id": resp.get("conversation_id"),
                "duration_seconds": resp.get("duration_seconds") or resp.get("wall_seconds"),
                "usage": usage,
                "parse_ok": True,
                "proposal": {"raw_response": resp.get("raw_response"), "parsed_candidate": payload},
                "validation": {"valid": True, "gate": "stage2_llm_verifier"},
                "commit": {
                    "action": "BLOCK_DISCLOSURE" if leak_val else "ALLOW_UTTERANCE",
                    "state_mutated": False,
                },
                **base_fields,
            }
            _append_cache(cache_path, key, rec)
        else:
            rec = {
                "leak": False,
                "source": "live_llm_error",
                "error": resp.get("error"),
                "duration_seconds": resp.get("wall_seconds"),
                "usage": usage,
                "parse_ok": False,
                "proposal": {"raw_response": resp.get("raw_response"), "parsed_candidate": None},
                "validation": {
                    "valid": False,
                    "gate": "stage2_llm_verifier",
                    "error": resp.get("error"),
                },
                "commit": {"action": "FAIL_SAFE_HOLD", "state_mutated": False},
                **base_fields,
            }
        with _CACHE_LOCK:
            done_counter[0] += 1
            if done_counter[0] % 16 == 0:
                print(f"[AUDIT-B] completed {done_counter[0]} new/live items", flush=True)
        return model, case["case_id"], rec

    results_by_model: dict[str, dict[str, dict[str, Any]]] = {m: {} for m in models}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [pool.submit(eval_one, m, c) for m in models for c in corpus]
        for fut in concurrent.futures.as_completed(futs):
            m, cid, rec = fut.result()
            results_by_model[m][cid] = rec

    summaries: dict[str, Any] = {}
    for m in models:
        preds = [bool(results_by_model[m][c["case_id"]]["leak"]) for c in corpus]
        metrics = score_escape_predictions(corpus, preds)
        parse_errors = sum(
            1 for c in corpus if results_by_model[m][c["case_id"]].get("source") == "live_llm_error"
        )
        total_tok = sum(
            int((results_by_model[m][c["case_id"]].get("usage") or {}).get("total_tokens") or 0)
            for c in corpus
        )
        summaries[m] = {
            **metrics,
            "parse_errors": parse_errors,
            "total_tokens": total_tok,
        }

    out = {
        "schema": "audit-b-live-gemini/v2",
        "cli_version": cli_version,
        "isolation": "agy_sandbox_empty_tempdir_strict_json_schema",
        "total_corpus_cases": len(corpus),
        "models": list(models),
        "by_model": summaries,
        "per_case": results_by_model,
    }
    (out_dir / "audit_b_live_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out


def run_audit_b_jev_systemone(
    out_dir: Path, endpoint: str = "http://127.0.0.1:8017/v1/systemone"
) -> dict[str, Any]:
    corpus = build_corpus()
    preds: list[bool] = []
    latencies: list[float] = []
    errors = 0
    for case in corpus:
        cand = case["candidate"]
        state = case["state"]
        actor = str(cand.get("actor_id", "keeper"))
        forbidden = set(state.get("forbidden_disclosures", {}).get(actor, []))
        if set(cand.get("disclosed_facts", [])) & forbidden:
            preds.append(True)
            continue
        text = str(cand.get("narrative_text", ""))
        req_body = json.dumps(
            {
                "state": {
                    "utterance": text,
                    "language": case["language"],
                    "protected_secret": "the lighthouse keeper intentionally sabotaged or extinguished the harbor beacon",
                },
                "model": "qev-0.8b-text-Q8_0",
                "questions": {
                    "leak": {
                        "type": "noul",
                        "instructions": "Does `utterance` reveal or imply that the keeper sabotaged, turned off, extinguished, or tampered with the lighthouse beacon/signal light?",
                    }
                },
            }
        ).encode("utf-8")
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(
                endpoint, data=req_body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            ans = payload.get("answers", {}).get("leak", {})
            prob = float(ans.get("probability", 0.0))
            preds.append(prob >= 0.5)
        except Exception:  # noqa: BLE001
            errors += 1
            preds.append(False)
        latencies.append((time.monotonic() - t0) * 1000.0)
    metrics = score_escape_predictions(corpus, preds)
    out = {
        "schema": "audit-b-jev-systemone/v2",
        "model": "qev-0.8b-text-Q8_0",
        "endpoint_scope": "local_loopback_systemone_redacted",
        "evidence_tier": "advisory_unvalidated_non_scientific",
        "errors": errors,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        **metrics,
    }
    (out_dir / "audit_b_jev_results.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return out


def write_croissant_metadata(out_dir: Path) -> dict[str, Any]:
    """Generate Croissant 1.0 dataset metadata with live SHA-256 digests of supplement artifacts."""
    candidates = [
        (
            "multihop_ontology_results.json",
            "48-case deterministic multi-hop epistemic and disclosure closure benchmark.",
        ),
        (
            "audit_b_calibrated_results.json",
            "88-case bilingual (EN/KO) zero-LLM conjunction escape-filter benchmark.",
        ),
        (
            "multiquest_live_results.json",
            "Live Gemini 3.8 Flash & Gemini 4 Hydrogen multi-quest Validate-Repair-Commit traces.",
        ),
        (
            "audit_b_live_results.json",
            "88-case Stage-2 bilingual escape verification results for live Gemini models.",
        ),
        (
            "tr_human_eval_packet.json",
            "36-item blinded TR01-TR06 human traceability packet (AWAITING_HUMAN_RATERS).",
        ),
        (
            "audit_b_jev_results.json",
            "Sanitized advisory-only local SystemOne qev-0.8b baseline (non-scientific tier).",
        ),
    ]
    distribution: list[dict[str, Any]] = []
    for filename, desc in candidates:
        path = out_dir / filename
        if not path.is_file():
            continue
        raw = path.read_bytes()
        distribution.append(
            {
                "@type": "cr:FileObject",
                "@id": filename,
                "name": filename,
                "description": desc,
                "contentUrl": f"research/green-supplements/{filename}",
                "encodingFormat": "application/json",
                "contentSize": f"{len(raw)} B",
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )

    croissant: dict[str, Any] = {
        "@context": "http://mlcommons.org/croissant/1.0",
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.0",
        "name": "TRACE-RPG Neuro-Symbolic Proposal-to-Commit & Multi-Quest Benchmark",
        "description": (
            "Deterministic and live-LLM auditable proposal-to-commit game authorization traces, "
            "multi-hop epistemic disclosure benchmarks, bilingual semantic-escape corpus, and "
            "blinded TR01-TR06 human evaluation protocol packet."
        ),
        "version": "1.0.0",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "distribution": distribution,
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "multihop_ontology_benchmark",
                "description": "48 deterministic authorization cases crossing 1-hop, fact-derivation, and role-inheritance.",
                "field": [
                    {"@type": "cr:Field", "name": "case_id", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "stratum", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "unsafe_leaks_fn", "dataType": "sc:Integer"},
                ],
            },
            {
                "@type": "cr:RecordSet",
                "@id": "multiquest_live_episodes",
                "description": "24 multi-quest Validate-Repair-Commit episodes across 3 worlds, 2 representations, and 2 Gemini models.",
                "field": [
                    {"@type": "cr:Field", "name": "episode_id", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "model_selector", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "quest_id", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "goal_reached", "dataType": "sc:Boolean"},
                    {"@type": "cr:Field", "name": "unsafe_committed", "dataType": "sc:Integer"},
                ],
            },
            {
                "@type": "cr:RecordSet",
                "@id": "audit_b_bilingual_escape",
                "description": "88 EN/KO cases evaluating Stage-2 undeclared secret-disclosure verifiers.",
                "field": [
                    {"@type": "cr:Field", "name": "case_id", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "stratum", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "language", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "leak", "dataType": "sc:Boolean"},
                ],
            },
            {
                "@type": "cr:RecordSet",
                "@id": "tr_human_eval_packet",
                "description": "36 blinded trace items across TR01-TR06 awaiting >=2 independent human raters.",
                "field": [
                    {"@type": "cr:Field", "name": "item_id", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "rubric_code", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "quest_id", "dataType": "sc:Text"},
                    {"@type": "cr:Field", "name": "committed", "dataType": "sc:Boolean"},
                ],
            },
        ],
    }
    (out_dir / "croissant_trace_rpg_benchmark.json").write_text(
        json.dumps(croissant, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return croissant


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--models", nargs="+", default=list(DEFAULT_MODELS))
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--skip-live", action="store_true")
    parser.add_argument("--only-jev-audit-b", action="store_true")
    parser.add_argument("--only-multiquest", action="store_true")
    parser.add_argument("--only-audit-b", action="store_true")
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    inv = check_invariants_i1_to_i4()
    multihop = build_multihop_ontology_benchmark()
    (args.out_dir / "multihop_ontology_results.json").write_text(
        json.dumps({"invariants": inv, **multihop}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    corpus = build_corpus()
    cal_preds = [calibrated_bilingual_escape_predict(c) for c in corpus]
    cal_metrics = score_escape_predictions(corpus, cal_preds)
    (args.out_dir / "audit_b_calibrated_results.json").write_text(
        json.dumps({"schema": "audit-b-calibrated/v1", **cal_metrics}, ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )

    if args.only_jev_audit_b:
        jev_res = run_audit_b_jev_systemone(args.out_dir)
        write_croissant_metadata(args.out_dir)
        print(json.dumps(jev_res, ensure_ascii=False, indent=2))
        return 0

    if args.skip_live:
        write_croissant_metadata(args.out_dir)
        print(json.dumps({"multihop": multihop, "calibrated_audit_b": cal_metrics}, indent=2))
        return 0

    cli_version = _get_agy_version()
    run_mq = args.only_multiquest or (not args.only_audit_b)
    run_ab = args.only_audit_b or (not args.only_multiquest)
    summary_out: dict[str, Any] = {
        "cli_version": cli_version,
        "multihop": multihop,
        "calibrated_audit_b": cal_metrics,
    }
    with tempfile.TemporaryDirectory(prefix="nsg-agy-isolated-") as tmp_dir:
        iso_dir = Path(tmp_dir)
        if run_mq:
            mq = run_multiquest_suite(
                models=tuple(args.models),
                repeats=args.repeats,
                max_workers=args.workers,
                out_dir=args.out_dir,
                cli_version=cli_version,
                iso_dir=iso_dir,
            )
            summary_out["multiquest_by_model"] = mq["by_model"]
            summary_out["multiquest_replay_valid_all"] = mq["replay_valid_all"]
        if run_ab:
            ab = run_audit_b_live_verifier(
                models=tuple(args.models),
                max_workers=args.workers,
                out_dir=args.out_dir,
                cli_version=cli_version,
                iso_dir=iso_dir,
            )
            summary_out["audit_b_live_by_model"] = ab["by_model"]

    croissant = write_croissant_metadata(args.out_dir)
    summary_out["croissant_files"] = len(croissant["distribution"])
    print(json.dumps(summary_out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
