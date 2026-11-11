#!/usr/bin/env python3
"""Admission-gated fixed-game runner for the prospective local Ollama arm.

Without ``--execute`` this command performs only local artifact/schema checks and
prints the immutable execution plan. A live run requires both ``--execute`` and
``--admit-exploratory``; no model pull, daemon start, or remote endpoint is ever
performed by this entrypoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_npc_goal_experiment import run_godot
from run_playable_evaluation import stage_project

from nesy_game.npc_goal import SCHEMA_PATH, _codex_output_schema
from nesy_game.runtime_model_swap import EpisodeLimits, GodotEpisodeEngine, ModelSpec, run_episode
from nesy_game.runtime_model_swap_ollama import OllamaPromptRunner, _manifest_binding

PROMPT = "Restore the lighthouse signal and reveal the authorized tide lead."
FIXTURE_REF = "data/fixtures/npc-goal-recovery/validated-v2/engineering.json#ENG-S01"
DEFAULT_OPTIONS = {"temperature": 0.0, "num_ctx": 4096, "num_predict": 512}


def _hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _assignment_id(seed: int, model: str, representation: str, model_layer_digest: str) -> str:
    model_slug = "".join(char if char.isalnum() else "_" for char in model).strip("_").lower()
    digest_slug = model_layer_digest.removeprefix("sha256:")[:16]
    return f"ollama-exploratory-{seed}-{model_slug}-{representation}-{digest_slug}"


def _store_root(path: Path, marker: str) -> Path:
    resolved = path.resolve()
    try:
        index = resolved.parts.index(marker)
    except ValueError as exc:
        raise ValueError(f"{marker}_path_not_in_ollama_store") from exc
    root = Path(*resolved.parts[:index])
    if not root.is_absolute():
        raise ValueError("ollama_store_root_invalid")
    return root


def _artifact_binding(manifest: Path, blob: Path) -> tuple[Path, dict[str, str]]:
    manifest_root = _store_root(manifest, "manifests")
    blob_root = _store_root(blob, "blobs")
    if manifest_root != blob_root:
        raise ValueError("manifest_blob_store_root_mismatch")
    binding = _manifest_binding(manifest.resolve(), blob.resolve())
    return manifest_root, binding


def _write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def _safe_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}".encode("utf-8", errors="backslashreplace").decode("utf-8")


def _pre_run_failure_record(
    *,
    config: Mapping[str, Any],
    model: ModelSpec,
    limits: EpisodeLimits,
    seed: int,
    prompt: str,
    assigned_ids: list[str],
    started: float,
    error: BaseException,
) -> dict[str, Any]:
    ended = time.monotonic()
    duration = max(0.0, ended - started)
    error_text = _safe_error(error)
    rows = [
        {
            "assignment_id": assignment_id,
            "status": "assigned_failure",
            "assigned_failure": True,
            "failure_reason": "pre_run_failure",
            "error": error_text,
            "duration_seconds": duration,
        }
        for assignment_id in assigned_ids
    ]
    evidence = {
        "provenance": {"mode": "local_ollama", "synthetic": False, "scientific_eligible": False},
        "seed": seed,
        "provider_identity": None,
        "provider_revision": None,
        "cost_usd": None,
        "provider_request_count": 0,
        "provider_request_count_authoritative": False,
        "provider_process_launch_count": 0,
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "config_hash": _hash(dict(config)),
        "prompt_receipts": [],
        "transport_events": [],
        "time": {
            "preparation_started": started,
            "preparation_ended": ended,
            "started": None,
            "ended": ended,
            "boundary": "first_host_dispatch_to_terminal_observation",
        },
    }
    record: dict[str, Any] = {
        "schema_version": "runtime-model-swap/1",
        "assignment_id": config.get("assignment_id"),
        "assigned_ids": list(assigned_ids),
        "assigned_rows": rows,
        "scope": "bookkeeping",
        "model": asdict(model),
        "limits": asdict(limits),
        "seed": seed,
        "config": dict(config),
        "prompt": prompt,
        "initial_state": {},
        "final_state": {},
        "decisions": [],
        "evidence": evidence,
        "accounting": {
            "assigned": len(assigned_ids),
            "host_calls": 0,
            "source_attempts": 0,
            "failed_calls": 0,
            "timeout_calls": 0,
            "transport_retries": 0,
            "repair_calls": 0,
            "successful_repairs": 0,
            "initial_proposal_failures": 0,
            "wall_expired": False,
            "denominator_eligible": True,
        },
        "scientific": {"assigned": len(assigned_ids), "executed": 0, "eligible": False},
        "safety": {"status": "NOT_PASS", "committed_transitions": 0, "errors": [error_text]},
        "failure_reason": "pre_run_failure",
        "last_error": error_text,
        "status": "failure",
        "success": False,
        "goal_reached": False,
        "duration_seconds": duration,
        "primary_success": False,
        "semantic_replay": {"valid": False, "checks": [], "scope": "pre_run_failure"},
        "engineering_status": "FIX",
        "accepted_for_engineering_verification": False,
    }
    record["record_hash"] = _hash(record)
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Admission-gated local Ollama fixed-game exploratory arm"
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--blob", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--representation", choices=("ontology", "general_rule"), default="general_rule"
    )
    parser.add_argument("--seed", type=int, default=20261028)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434/api/generate")
    parser.add_argument("--execute", action="store_true", help="allow fixed-game and Ollama calls")
    parser.add_argument(
        "--admit-exploratory", action="store_true", help="explicitly admit the new local cohort"
    )
    args = parser.parse_args(argv)

    if args.timeout <= 0:
        raise ValueError("timeout_must_be_positive")
    manifest = args.manifest.resolve()
    blob = args.blob.resolve()
    store_root, binding = _artifact_binding(manifest, blob)
    canonical_schema = _codex_output_schema()
    schema_digest = hashlib.sha256(
        json.dumps(
            canonical_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    options = {**DEFAULT_OPTIONS, "seed": args.seed}
    config: dict[str, Any] = {
        "cohort": "ollama-exploratory",
        "scenario": "sealed-lighthouse-v1",
        "goal": "harbor-signal-restored-authorized-tide-lead-v1",
        "assignment_id": _assignment_id(
            args.seed, args.model, args.representation, binding["model_layer_digest"]
        ),
        "execution_mode": "fixed_game_godot_with_local_ollama",
        "model": args.model,
        "endpoint": args.endpoint,
        "manifest_path": str(manifest),
        "blob_path": str(blob),
        "ollama_store_root": str(store_root),
        "manifest_sha256": binding["manifest_sha256"],
        "blob_sha256": binding["blob_sha256"],
        "model_layer_digest": binding["model_layer_digest"],
        "representation": args.representation,
        "seed": args.seed,
        "options": options,
        "prompt_hash": hashlib.sha256(PROMPT.encode("utf-8")).hexdigest(),
        "canonical_schema_path": str(SCHEMA_PATH),
        "canonical_output_schema_sha256": schema_digest,
    }
    assigned_ids = [str(config["assignment_id"])]
    if len(set(assigned_ids)) != len(assigned_ids):
        raise ValueError("duplicate_assigned_id")
    config_hash = _hash(config)
    plan = {
        "status": "admitted" if args.execute and args.admit_exploratory else "plan_only",
        "cohort": config["cohort"],
        "assignment_id": config["assignment_id"],
        "assigned_ids": assigned_ids,
        "assigned_rows": [{"assignment_id": assignment_id} for assignment_id in assigned_ids],
        "execution_mode": config["execution_mode"] if args.execute else "no_execution",
        "config_hash": config_hash,
        "manifest_path": str(manifest),
        "blob_path": str(blob),
        "manifest_sha256": binding["manifest_sha256"],
        "blob_sha256": binding["blob_sha256"],
        "model_layer_digest": binding["model_layer_digest"],
        "representation": args.representation,
        "seed": args.seed,
        "options": options,
        "model": args.model,
        "no_claims": ["not_native_codex", "not_causal_ontology_efficacy", "not_frozen_cohort"],
    }
    if not args.execute or not args.admit_exploratory:
        print(json.dumps(plan, ensure_ascii=False, sort_keys=True))
        return 0
    if args.output_root.exists():
        raise FileExistsError(f"output already exists: {args.output_root}")
    args.output_root.mkdir(parents=True)
    _write_json(args.output_root / "admission-plan.json", plan)

    model_spec = ModelSpec(
        args.model, args.representation, provider="ollama", revision=None, offline=False
    )
    limits = EpisodeLimits(response_seconds=args.timeout)
    episode_path = args.output_root / "episode.json"
    run_started = time.monotonic()
    setup_complete = False
    try:
        with tempfile.TemporaryDirectory(prefix="runtime-ollama-fixed-game-") as working:
            project = Path(working) / "project"
            schema_file = Path(working) / "canonical-output-schema.json"
            schema_file.write_text(
                json.dumps(
                    canonical_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ),
                encoding="utf-8",
            )
            stage_project(ROOT / "game-track" / "godot", project)
            runner = OllamaPromptRunner(
                manifest_path=manifest,
                blob_path=blob,
                schema_path=schema_file,
                model=args.model,
                endpoint=args.endpoint,
                timeout=args.timeout,
                options=options,
                allowed_root=store_root,
            )
            engine = GodotEpisodeEngine(
                project=project,
                output_root=args.output_root,
                seed=args.seed,
                assignment_id=str(config["assignment_id"]),
                prompt_runner=runner,
                engine_runner=run_godot,
                godot_binary=shutil.which("godot4") or shutil.which("godot") or "godot",
                fixture_ref=FIXTURE_REF,
            )
            setup_complete = True
            record = run_episode(
                engine=engine,
                proposal_source=engine.propose,
                repair_source=engine.repair,
                model=model_spec,
                limits=limits,
                seed=args.seed,
                clock=time.monotonic,
                config=config,
                prompt=PROMPT,
                ollama_local_admitted=True,
                output_path=episode_path,
            )
    except Exception as exc:
        if setup_complete:
            raise
        record = _pre_run_failure_record(
            config=config,
            model=model_spec,
            limits=limits,
            seed=args.seed,
            prompt=PROMPT,
            assigned_ids=assigned_ids,
            started=run_started,
            error=exc,
        )
        _write_json(episode_path, record)
    print(
        json.dumps(
            {
                "status": record["status"],
                "success": record["success"],
                "failure_reason": record["failure_reason"],
                "scientific": record.get("scientific"),
                "record_hash": record.get("record_hash"),
                "output_root": str(args.output_root),
            },
            sort_keys=True,
        )
    )
    return 0 if record["success"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
