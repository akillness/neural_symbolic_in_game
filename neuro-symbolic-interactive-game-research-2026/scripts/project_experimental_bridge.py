#!/usr/bin/env python3
"""Project a strict experimental-engine event onto the stable research bridge envelope."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SUPPORTED_TYPES = {
    "observation",
    "player_action",
    "candidate",
    "validation",
    "commit",
    "reject",
    "fallback",
}


def project_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event["event_type"]
    if event_type not in SUPPORTED_TYPES:
        raise ValueError(f"event type has no stable bridge projection: {event_type}")
    return {
        "schema_version": "1.0.0",
        "scenario_id": event["scenario_id"],
        "run_id": event["run_id"],
        "episode_id": event["episode_id"],
        "event_id": event["event_id"],
        "step": event["sequence"],
        "event_type": event_type,
        "model_id": event["model_id"],
        "policy_id": event["policy_id"],
        "seed": event["seed"],
        "world_state_hash": event["world_state_hash"],
        "evidence_ids": event["evidence_ids"],
        "timestamp_ms": event["timestamp_ms"],
        "payload": {
            "experimental_event_schema": event["schema_version"],
            "delivery_index": event["delivery_index"],
            "turn": event["turn"],
            "world_state_hash_before": event["world_state_hash_before"],
            "model_revision": event["model_revision"],
            "proposal": event["proposal"],
            "validation": event["validation"],
            "repair": event["repair"],
            "commit": event["commit"],
            "cost_usd": event["cost_usd"],
            "request_latency_ms": event["request_latency_ms"],
            "engine_payload": event["payload"],
        },
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: project_experimental_bridge.py <experimental-events.jsonl>")
        return 2
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event["event_type"] in SUPPORTED_TYPES:
            print(json.dumps(project_event(event), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
