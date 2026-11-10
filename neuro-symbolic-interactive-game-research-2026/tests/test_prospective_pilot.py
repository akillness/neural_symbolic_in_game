"""Frozen prospective engineering contracts; no native host or model is invoked."""

from __future__ import annotations

import copy
import itertools
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game import prospective_pilot as pilot
from nesy_game.runtime_model_swap import _render

TARGETS = {
    "c56sol": ("codex", "gpt-5.6-sol", "medium"),
    "c61sol": ("codex", "gpt-6.1-sol", "medium"),
    "agy38f": ("antigravity", "gemini-3.8-flash-medium", "medium"),
}


def expected_ids() -> set[str]:
    runtime = {
        f"pp1103:rt:{target}:{rep}:r{repeat:02d}"
        for target, rep, repeat in itertools.product(TARGETS, ("gr", "onto"), range(1, 11))
    }
    development = {
        f"pp1103:dev:{target}:{exploration}:{rep}:t{task}:r{repeat}"
        for target, exploration, rep, task, repeat in itertools.product(
            TARGETS, ("min", "exp"), ("gr", "onto"), range(1, 6), (1, 2)
        )
    }
    return runtime | development


def test_planned_units_cover_exact_frozen_cross_product_and_paired_resets() -> None:
    protocol = pilot.build_protocol()
    units = protocol["units"]
    assert Counter(row["unit_id"] for row in units) == Counter(expected_ids())
    assert Counter(row["track"] for row in units) == {"runtime": 60, "development": 120}
    assert {
        key: (item["host"], item["selector"], item["effort"])
        for key, item in protocol["targets"].items()
    } == TARGETS
    paired = defaultdict(set)
    resets = []
    for row in units:
        parts = row["unit_id"].split(":")
        if row["track"] == "runtime":
            repeat = int(parts[-1][1:])
            expected_seed = 2026110300 + repeat
            pairing = ("runtime", repeat)
        else:
            task, repeat = int(parts[-2][1:]), int(parts[-1][1:])
            expected_seed = 2026111000 + 10 * task + repeat
            pairing = ("development", task, repeat)
        assert row["seed"] == expected_seed
        paired[pairing].add(row["seed"])
        resets.append(row["reset_id"])
    assert all(len(seeds) == 1 for seeds in paired.values())
    assert len(set(resets)) == 180  # No assignment can inherit another assignment's state.


def test_counterbalance_is_reproducible_target_rotation_not_grouped_by_condition() -> None:
    units = pilot.build_protocol()["units"]
    assert units == pilot.build_protocol()["units"]
    keys = list(TARGETS)
    expected = []
    for block in range(1, 11):
        rotated = keys[block % 3 :] + keys[: block % 3]
        reps = ("gr", "onto") if block % 2 else ("onto", "gr")
        expected.extend(f"pp1103:rt:{key}:{rep}:r{block:02d}" for key in rotated for rep in reps)
    cells = [("min", "gr"), ("min", "onto"), ("exp", "gr"), ("exp", "onto")]
    for block, (task, repeat) in enumerate(itertools.product(range(1, 6), (1, 2)), 1):
        rotated = keys[block % 3 :] + keys[: block % 3]
        order = cells[block % 4 :] + cells[: block % 4]
        expected.extend(
            f"pp1103:dev:{key}:{exp}:{rep}:t{task}:r{repeat}"
            for key in rotated
            for exp, rep in order
        )
    assert [row["unit_id"] for row in units] == expected
    assert [row["order"] for row in units] == list(range(1, 181))


@pytest.mark.parametrize(
    "mutation", ["duplicate", "missing", "condition", "target", "seed", "reset", "order"]
)
def test_protocol_rejects_wrong_membership_even_when_count_is_preserved(mutation: str) -> None:
    protocol = copy.deepcopy(pilot.build_protocol())
    units = protocol["units"]
    if mutation == "duplicate":
        units[-1] = copy.deepcopy(units[0])
    elif mutation == "missing":
        units.pop()
    elif mutation == "condition":
        units[0]["unit_id"] = units[0]["unit_id"].replace(":gr:", ":invented:")
    elif mutation == "target":
        protocol["targets"]["c61sol"]["selector"] = "gpt-6.1"
    elif mutation == "seed":
        units[0]["seed"] += 1
    elif mutation == "reset":
        units[0]["reset_id"] = units[1]["reset_id"]
    else:
        units[0]["order"], units[1]["order"] = units[1]["order"], units[0]["order"]
    with pytest.raises(ValueError):
        pilot.validate_protocol(protocol)


@pytest.mark.parametrize(
    "track,field,value",
    [
        ("runtime", "wall_seconds", 181),
        ("runtime", "response_seconds", 61),
        ("runtime", "host_dispatches", 13),
        ("runtime", "repairs_per_decision", 3),
        ("development", "wall_seconds", 901),
        ("development", "tool_executions", 65),
        ("development", "submissions", 4),
        ("development", "host_dispatches", 73),
        ("development", "non_yielding_dispatches", 6),
    ],
)
def test_protocol_rejects_relaxed_scientific_resource_caps(
    track: str, field: str, value: int
) -> None:
    protocol = copy.deepcopy(pilot.build_protocol())
    protocol[f"{track}_limits"][field] = value
    with pytest.raises(ValueError):
        pilot.validate_protocol(protocol)


@pytest.mark.parametrize("representation", ["general_rule", "ontology"])
def test_existing_renderer_round_trips_embedded_delimiters_and_unicode(representation: str) -> None:
    semantic = {
        "requirement_ids": ["TASK-1", "a;b=c"],
        "public_facts": {"label": '한글; x=y; quote=";"', "nested": [False, None, 3]},
        "preconditions": "key=value; another=not a new field",
        "allowed_effects": [],
        "rejection_semantics": {"code": "bad;field=value"},
        "unchanged_invariants": ["no canonical writes"],
    }
    assert pilot.decode_context(_render(semantic, representation), representation) == semantic


@pytest.mark.parametrize(
    "text,representation",
    [
        ("rules:a=1;a=2", "general_rule"),
        ("rules:a=1;trailing", "general_rule"),
        ("rules:a=NaN", "general_rule"),
        ('ontology:{"a":1,"a":2}', "ontology"),
        ('ontology:{"a":1}garbage', "ontology"),
        ("ontology:[]", "ontology"),
    ],
)
def test_context_decoder_rejects_ambiguous_or_malformed_facts(
    text: str, representation: str
) -> None:
    with pytest.raises(ValueError):
        pilot.decode_context(text, representation)


def test_unknown_protocol_fields_are_not_silently_accepted() -> None:
    protocol = copy.deepcopy(pilot.build_protocol())
    protocol["native_authorization_bypass"] = True
    with pytest.raises(ValueError):
        pilot.validate_protocol(protocol)
