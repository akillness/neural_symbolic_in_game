#!/usr/bin/env python3
"""Run a network-free experiment smoke test from frozen proposal records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game import (
    ActionPolicy,
    RecordedProposalAdapter,
    WorldState,
    run_experiment_case,
    summarize_experiment,
    to_jsonable,
    write_experiment_jsonl,
)


def main() -> None:
    state = WorldState(
        state_id="harbor-0",
        locations=frozenset({"harbor", "lighthouse"}),
        reachable_locations=frozenset({"harbor"}),
        object_locations={},
        inventory=frozenset(),
        facts=frozenset({"player_saved_dock"}),
        action_policies={
            "NPC_REPLY": ActionPolicy(
                frozenset({"player_saved_dock"}),
                frozenset({"lighthouse_hint_given"}),
                frozenset({"lighthouse_hint_given"}),
            )
        },
        npc_knowledge={"captain_mira": frozenset({"player_saved_dock"})},
        quest_stage=1,
    )
    adapter = RecordedProposalAdapter.from_json(ROOT / "data/fixtures/recorded-proposals.json")
    result_path = ROOT / "runs/recorded-experiment/results.jsonl"
    trace_path = ROOT / "runs/recorded-experiment/traces.jsonl"
    result_path.unlink(missing_ok=True)
    trace_path.unlink(missing_ok=True)
    cases = [
        run_experiment_case(
            adapter,
            state,
            run_id="offline-smoke",
            scenario_id="NPC-HARBOR-001",
            seed=seed,
        )
        for seed in (23, 47)
    ]
    for case in cases:
        write_experiment_jsonl(
            result_path,
            trace_path,
            case,
        )
    payload = {
        "records": [to_jsonable(case.record) for case in cases],
        "summary": summarize_experiment(
            (case.record for case in cases),
            (
                ("offline-smoke", "NPC-HARBOR-001", seed, adapter.model_id, adapter.model_revision)
                for seed in (23, 47)
            ),
        ),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
