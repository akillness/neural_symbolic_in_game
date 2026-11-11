#!/usr/bin/env python3
"""Export existing synthetic cases for blind reassessment and reconcile judgments offline."""

import argparse
import copy
import hashlib
import json
import os
import random
import sys
from pathlib import Path

NOTICE = (
    "Blind reassessment of six previously authored synthetic cases; not a new "
    "independent holdout or human gold. No live model or human judgment is implied. "
    "Judge each action only against the rules below; unknown is permitted."
)
RULES = [
    "The action type must have a policy. Its preconditions must include the policy's required preconditions, and all action preconditions must be true in the state.",
    "Action effects must include all policy-required effects and be a subset of policy-allowed effects.",
    "Every required object must be in inventory or at a reachable location.",
    "Used and disclosed facts must be known by the actor; disclosed facts must not be forbidden for that actor.",
    "The required quest stage must not exceed the current stage. A non-null stage effect must be policy-authorized and must not reduce the current stage.",
]
STATE_KEYS = {
    "state_id",
    "locations",
    "reachable_locations",
    "object_locations",
    "inventory",
    "facts",
    "action_policies",
    "npc_knowledge",
    "forbidden_disclosures",
    "quest_stage",
}
ACTION_KEYS = {
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
    "metadata",
}
SOURCE_SHA256 = "9f5b6401467a2c9a8329659b9999bb86d5a8231cced62d1e9dbaa6326d174ef7"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    data = Path(path).read_bytes()

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj

    def invalid_constant(value):
        raise ValueError(f"non-finite JSON number: {value}")

    return data, json.loads(data, object_pairs_hook=unique, parse_constant=invalid_constant)


def encoded(value):
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode()


def nonempty(value, description):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{description} must be a nonempty string")
    return value


def prepare(source, seed):
    if not isinstance(source, dict) or source.get("artifact_type") != "independent_agent_cases":
        raise ValueError("source must be independent_agent_cases")
    cases = source.get("cases")
    if not isinstance(cases, list) or len(cases) != 6:
        raise ValueError("source must contain exactly six cases")
    seen = set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")  # noqa: TRY004 - Preserve malformed-input ValueError contract.
        original_id = nonempty(case.get("id"), "source case id")
        if original_id in seen:
            raise ValueError("duplicate source case id")
        seen.add(original_id)
        state, action = case.get("WorldState"), case.get("CandidateAction")
        if (
            not isinstance(state, dict)
            or set(state) != STATE_KEYS
            or not isinstance(action, dict)
            or set(action) != ACTION_KEYS
        ):
            raise ValueError("unexpected state or action fields")
        nonempty(state["state_id"], "state id")
        nonempty(action["action_id"], "action id")
        if action["narrative_text"] != "" or action["metadata"] != {}:
            raise ValueError("nonempty narrative or metadata cannot be exported safely")
        if case.get("expected") not in ("valid", "invalid"):
            raise ValueError("source expectation must be valid or invalid")
    ordered = list(cases)
    random.Random(seed).shuffle(ordered)
    packet_cases, mapping = [], []
    for index, case in enumerate(ordered, 1):
        blind_id = f"case-{index:02d}"
        state, action = copy.deepcopy(case["WorldState"]), copy.deepcopy(case["CandidateAction"])
        state["state_id"], action["action_id"] = f"state-{index:02d}", f"action-{index:02d}"
        packet_cases.append({"id": blind_id, "WorldState": state, "CandidateAction": action})
        mapping.append({"blind_id": blind_id, "source_id": case["id"]})
    packet = {
        "artifact_type": "blind_reassessment_packet",
        "notice": NOTICE,
        "response_instructions": "Return JSON with packet_sha256 (SHA-256 of the exact packet file bytes), evaluator {type: human|model_agent|unknown, model: string|null}, and responses [{id, label: valid|invalid|unknown|null}]. Omitted or empty responses are missing; never guess unknown judgments.",
        "rules": RULES,
        "cases": packet_cases,
    }
    return packet, mapping


def write_new(path, data, mode=0o644):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
    except BaseException:
        Path(path).unlink(missing_ok=True)
        raise


def export(args):
    packet_path, private_path = Path(args.packet).resolve(), Path(args.private).resolve()
    if packet_path.parent == private_path.parent or packet_path.parent in private_path.parents:
        raise ValueError("private artifact must be outside the packet directory")
    source_bytes, source = load(args.source)
    if digest(source_bytes) != SOURCE_SHA256:
        raise ValueError("source does not match the reviewed v2 SHA-256")
    packet, mapping = prepare(source, args.seed)
    packet_bytes = encoded(packet)
    private = {
        "artifact_type": "blind_reassessment_private",
        "source_sha256": digest(source_bytes),
        "packet_sha256": digest(packet_bytes),
        "seed": args.seed,
        "mapping": mapping,
        "author": source.get("author"),
        "human_gold": False,
        "notice": "Private assignment mapping; never give this file to the evaluator.",
    }
    write_new(private_path, encoded(private), 0o600)
    try:
        write_new(packet_path, packet_bytes)
    except BaseException:
        private_path.unlink(missing_ok=True)
        raise


def reconcile(args):
    packet_path = Path(args.packet).resolve()
    private_path, output_path = Path(args.private).resolve(), Path(args.output).resolve()
    if (
        private_path.parent == packet_path.parent
        or packet_path.parent in private_path.parents
        or output_path.parent != private_path.parent
    ):
        raise ValueError(
            "reconciliation output must be in the private mapping directory outside the packet directory"
        )
    source_bytes, source = load(args.source)
    packet_bytes, packet = load(args.packet)
    _, private = load(args.private)
    _, responses = load(args.responses)
    if (
        not isinstance(private, dict)
        or private.get("artifact_type") != "blind_reassessment_private"
    ):
        raise ValueError("invalid private artifact")
    if digest(source_bytes) != private.get("source_sha256"):
        raise ValueError("source hash mismatch")
    if digest(source_bytes) != SOURCE_SHA256:
        raise ValueError("source does not match the reviewed v2 SHA-256")
    if digest(packet_bytes) != private.get("packet_sha256"):
        raise ValueError("packet hash mismatch")
    seed = private.get("seed")
    if type(seed) is not int:
        raise ValueError("invalid private seed")
    expected_packet, mapping = prepare(source, seed)
    if packet != expected_packet or private.get("mapping") != mapping:
        raise ValueError("packet or mapping inconsistent with source and seed")
    if not isinstance(responses, dict) or set(responses) != {
        "evaluator",
        "responses",
        "packet_sha256",
    }:
        raise ValueError("responses must contain evaluator, responses, and packet_sha256")
    if responses["packet_sha256"] != digest(packet_bytes):
        raise ValueError("response packet hash mismatch")
    evaluator, entries = responses["evaluator"], responses["responses"]
    if (
        not isinstance(evaluator, dict)
        or set(evaluator) != {"type", "model"}
        or evaluator["type"] not in ("human", "model_agent", "unknown")
    ):
        raise ValueError("evaluator must declare type and model")
    if evaluator["model"] is not None:
        nonempty(evaluator["model"], "evaluator model")
    if evaluator["type"] != "model_agent" and evaluator["model"] is not None:
        raise ValueError("model is only allowed for a model_agent")
    if not isinstance(entries, list):
        raise ValueError("responses must be a list")  # noqa: TRY004 - Preserve malformed-input ValueError contract.
    known = {item["blind_id"] for item in mapping}
    labels = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {"id", "label"}:
            raise ValueError("each response must contain only id and label")
        identifier = nonempty(item["id"], "response id")
        if identifier not in known:
            raise ValueError("unknown response id")
        if identifier in labels:
            raise ValueError("duplicate response id")
        label = item["label"]
        if label not in ("valid", "invalid", "unknown", "", None):
            raise ValueError("invalid response label")
        labels[identifier] = label
    source_cases = {case["id"]: case for case in source["cases"]}
    rows = []
    for item in mapping:
        identifier = item["blind_id"]
        label = labels.get(identifier)
        status = "missing" if label in (None, "") else label
        reference = source_cases[item["source_id"]]["expected"]
        rows.append(
            {
                "id": identifier,
                "label": status,
                "matches_author_expectation": label == reference
                if status in ("valid", "invalid")
                else None,
            }
        )
    answered = sum(row["matches_author_expectation"] is not None for row in rows)
    result = {
        "artifact_type": "blind_reassessment_reconciliation",
        "notice": NOTICE,
        "comparison_notice": "Agreement with prior author expectations is not human gold, efficacy, or independent validation.",
        "privacy_notice": "Private result; do not share with evaluators. File permissions cannot prevent a person from redistributing it.",
        "evaluator": evaluator,
        "source_sha256": digest(source_bytes),
        "packet_sha256": digest(packet_bytes),
        "seed": seed,
        "total": len(rows),
        "answered": answered,
        "missing": sum(row["label"] == "missing" for row in rows),
        "unknown": sum(row["label"] == "unknown" for row in rows),
        "matches": sum(row["matches_author_expectation"] is True for row in rows),
        "complete": answered == len(rows),
        "cases": rows,
    }
    write_new(output_path, encoded(result), 0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    out = commands.add_parser("export")
    for name in ("source", "packet", "private"):
        out.add_argument("--" + name, required=True)
    out.add_argument("--seed", type=int, required=True)
    rec = commands.add_parser("reconcile")
    for name in ("source", "packet", "private", "responses", "output"):
        rec.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        (export if args.command == "export" else reconcile)(args)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
