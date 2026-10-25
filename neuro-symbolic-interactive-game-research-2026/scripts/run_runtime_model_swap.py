from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.runtime_model_swap import EpisodeLimits, GodotEpisodeEngine, ModelSpec, run_episode


def _hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline engineering-only runtime model-swap harness"
    )
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--representation", choices=("ontology", "general_rule"), default="general_rule"
    )
    parser.add_argument("--seed", type=int, default=20261024)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.offline or args.live:
        print(
            json.dumps(
                {
                    "status": "rejected",
                    "failure_reason": "provider_not_allowed_offline",
                    "provider_process_launch_count": 0,
                },
                sort_keys=True,
            )
        )
        return 2
    args.output_root.mkdir(parents=True, exist_ok=False)
    from run_npc_goal_experiment import run_godot
    from run_playable_evaluation import stage_project

    prompt = "Restore the lighthouse signal and reveal the authorized tide lead."
    config = {
        "scenario": "sealed-lighthouse-v1",
        "goal": "harbor-signal-restored-authorized-tide-lead-v1",
        "assignment_id": "runtime-model-swap-offline",
    }
    manifest = {
        "schema_version": "runtime-model-swap/assignment-manifest-1",
        "engineering_only": True,
        "assignment_id": config["assignment_id"],
        "assigned_ids": [config["assignment_id"]],
        "seed": args.seed,
        "representation": args.representation,
        "scenario": config["scenario"],
        "goal_witness": "engine_observed_goal_reached",
        "source": "synthetic_offline_callback",
        "config_hash": _hash(config),
        "prompt_hash": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
    }
    with (args.output_root / "assignment-manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    def scripted_prompt(**kwargs: object) -> tuple[int, dict[str, object]]:
        payload = {
            "request_id": kwargs["request_id"],
            "typed_intent": {"label": "ASK_INFORMATION", "claims": [], "target": None},
        }
        validator = kwargs["validator"]
        if not validator(payload, str(kwargs["request_id"])):
            raise ValueError("offline_scripted_payload_invalid")
        return 0, payload

    with tempfile.TemporaryDirectory(prefix="runtime-model-swap-") as working:
        project = Path(working) / "project"
        stage_project(ROOT / "game-track" / "godot", project)
        engine = GodotEpisodeEngine(
            project=project,
            output_root=args.output_root,
            seed=args.seed,
            assignment_id=str(config["assignment_id"]),
            prompt_runner=scripted_prompt,
            engine_runner=run_godot,
            godot_binary=shutil.which("godot4") or shutil.which("godot") or "godot",
            fixture_ref="data/fixtures/npc-goal-recovery/validated-v2/engineering.json#ENG-S01",
        )
        record = run_episode(
            engine=engine,
            proposal_source=engine.propose,
            repair_source=engine.repair,
            model=ModelSpec("offline-synthetic-model", args.representation),
            limits=EpisodeLimits(),
            seed=args.seed,
            clock=time.monotonic,
            config=config,
            prompt=prompt,
            output_path=args.output_root / "episode.json",
        )
    print(
        json.dumps(
            {
                "status": record["status"],
                "success": record["success"],
                "primary_success": record["primary_success"],
                "engineering_status": record["engineering_status"],
                "accepted_for_engineering_verification": record[
                    "accepted_for_engineering_verification"
                ],
                "failure_reason": record["failure_reason"],
                "goal_reached": record["goal_reached"],
                "decisions": len(record["decisions"]),
                "semantic_replay": record["semantic_replay"],
                "output_root": str(args.output_root),
            },
            sort_keys=True,
        )
    )
    return 0 if record["primary_success"] and record["accepted_for_engineering_verification"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
