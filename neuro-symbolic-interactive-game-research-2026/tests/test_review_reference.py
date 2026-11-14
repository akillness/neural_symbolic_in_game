from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.review_reference import generic_accepts, reference_reachable_locations


def _graph():
    return {
        "rooms": ["start", "junction", "vault"],
        "start": "start",
        "edges": [
            {"source": "start", "target": "junction", "requires_keys": []},
            {"source": "junction", "target": "vault", "requires_keys": ["key"]},
        ],
        "placements": {"key": "vault", "relic": "vault"},
    }


def test_key_behind_its_own_lock_does_not_unlock_itself():
    graph = _graph()
    before = deepcopy(graph)
    assert reference_reachable_locations(graph) == frozenset({"start", "junction"})
    assert graph == before


def test_unlocked_bypass_collects_key_and_makes_locked_route_traversable():
    graph = _graph()
    graph["edges"].append({"source": "start", "target": "vault", "requires_keys": []})
    assert reference_reachable_locations(graph) == frozenset(graph["rooms"])


def test_keys_persist_when_returning_from_branches_and_are_not_consumed():
    graph = {
        "rooms": ["hub", "left", "right", "gate", "goal"],
        "start": "hub",
        "edges": [
            {"source": "hub", "target": "left", "requires_keys": []},
            {"source": "hub", "target": "right", "requires_keys": ["bronze"]},
            {"source": "hub", "target": "gate", "requires_keys": ["bronze", "silver"]},
            {"source": "gate", "target": "goal", "requires_keys": ["bronze", "silver"]},
        ],
        "placements": {"bronze": "left", "silver": "right"},
    }
    assert reference_reachable_locations(graph) == frozenset(graph["rooms"])
    # Records are bidirectional, even when the start is their target.
    graph["start"] = "left"
    assert reference_reachable_locations(graph) == frozenset(graph["rooms"])


@pytest.mark.parametrize(
    "field,value",
    [
        ("start", "missing"),
        ("rooms", ["start", "junction", "junction"]),
        ("edges", [{"source": "start", "target": "missing", "requires_keys": []}]),
        ("edges", [{"source": "missing", "target": "vault", "requires_keys": []}]),
        ("placements", {"key": "missing"}),
        ("placements", {"relic": "vault"}),
        ("edges", [{"source": "start", "target": "vault", "requires_keys": "key"}]),
    ],
    ids=[
        "unknown-start",
        "duplicate-room",
        "unknown-target",
        "unknown-source",
        "unknown-placement",
        "unplaced-required-key",
        "string-key-list",
    ],
)
def test_malformed_graphs_are_rejected_not_silently_treated_as_unreachable(field, value):
    graph = _graph()
    graph[field] = value
    with pytest.raises(ValueError):
        reference_reachable_locations(graph)


@pytest.mark.parametrize(
    "edges", [None, {}, "start -> vault"], ids=["null-edges", "mapping-edges", "string-edges"]
)
def test_reference_rejects_wrong_edges_container_type_with_type_error(edges):
    graph = _graph()
    graph["edges"] = edges
    with pytest.raises(TypeError):
        reference_reachable_locations(graph)


def _ordinary_inputs():
    state = SimpleNamespace(
        facts=frozenset({"ready"}),
        inventory=frozenset(),
        object_locations={"relic": "vault"},
        reachable_locations=frozenset({"start"}),
        npc_knowledge={"keeper": frozenset({"secret"})},
        forbidden_disclosures={"keeper": frozenset({"secret"})},
        quest_stage=0,
        action_policies={
            "signal": SimpleNamespace(
                required_preconditions=frozenset({"ready"}),
                required_effects=frozenset({"restored"}),
                allowed_effects=frozenset({"restored", "lit"}),
                allowed_quest_stage_effects=frozenset({0, 1}),
            )
        },
    )
    candidate = SimpleNamespace(
        action_type="signal",
        actor_id="keeper",
        preconditions=frozenset({"ready"}),
        effects=frozenset({"restored"}),
        required_objects=frozenset(),
        used_facts=frozenset(),
        disclosed_facts=frozenset(),
        required_quest_stage=0,
        quest_stage_effect=1,
    )
    return state, candidate


@pytest.mark.parametrize(
    "changes",
    [
        {"preconditions": frozenset()},
        {"effects": frozenset()},
        {"effects": frozenset({"restored", "unauthorized"})},
        {"preconditions": frozenset({"ready", "missing"})},
        {"required_objects": frozenset({"relic"})},
        {"used_facts": frozenset({"unknown"})},
        {"disclosed_facts": frozenset({"secret"})},
        {"required_quest_stage": 1},
        {"quest_stage_effect": 2},
        {"action_type": "unknown"},
    ],
)
def test_ordinary_reference_rejects_each_encoded_rule_violation(changes):
    state, candidate = _ordinary_inputs()
    assert generic_accepts(state, candidate) is True
    candidate = SimpleNamespace(**{**vars(candidate), **changes})
    assert generic_accepts(state, candidate) is False


def test_inventory_satisfies_object_requirement_without_reachable_placement():
    state, candidate = _ordinary_inputs()
    candidate.required_objects = frozenset({"relic"})
    assert generic_accepts(state, candidate) is False
    state.inventory = frozenset({"relic"})
    assert generic_accepts(state, candidate) is True


def test_reference_executes_with_only_standard_library_available(tmp_path):
    # A real isolated interpreter cannot import the project's validator/runtime/repair.
    source = Path(__file__).resolve().parents[1] / "scripts" / "review_reference.py"
    isolated = tmp_path / "reference.py"
    isolated.write_bytes(source.read_bytes())
    program = """
import json
import runpy
import sys
from types import SimpleNamespace as NS

m = runpy.run_path(sys.argv[1])
graph = json.loads(sys.argv[2])
policy = NS(required_preconditions=frozenset({'ready'}),
            required_effects=frozenset({'restored'}),
            allowed_effects=frozenset({'restored'}),
            allowed_quest_stage_effects=frozenset({1}))
state = NS(action_policies={'signal': policy}, facts=frozenset({'ready'}),
           inventory=frozenset(), object_locations={}, reachable_locations=frozenset(),
           npc_knowledge={}, forbidden_disclosures={}, quest_stage=0)
candidate = NS(action_type='signal', actor_id='keeper', preconditions=frozenset({'ready'}),
               effects=frozenset({'restored'}), required_objects=frozenset(),
               used_facts=frozenset(), disclosed_facts=frozenset(),
               required_quest_stage=0, quest_stage_effect=1)
print(json.dumps({'reachable': sorted(m['reference_reachable_locations'](graph)),
                  'valid': m['generic_accepts'](state, candidate)}))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-c", program, str(isolated), json.dumps(_graph())],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"reachable": ["junction", "start"], "valid": True}
