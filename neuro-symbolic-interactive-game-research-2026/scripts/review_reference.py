"""Implementation-separated reference for the bounded reusable-key graph audit.

The ordinary-rule predicate is extracted unchanged from the fixed-input
comparison. Implementation separation is not independent or blinded ground
truth. Reachability exhausts (room, persistent key inventory) states, without
importing the production gate, runtime, repair logic or graph closure.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping


def _identifiers(values, field):
    if not isinstance(values, (list, tuple)) or any(
        not isinstance(value, str) or not value for value in values
    ):
        raise ValueError(f"{field} must be a list of nonempty string identifiers")
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicate identifiers")
    return frozenset(values)


def reference_reachable_locations(graph: Mapping[str, object]) -> frozenset[str]:
    """Enumerate finite undirected room/key states with persistent reusable keys.

    Each edge has source, target and requires_keys fields. Placements map item
    identifiers to rooms; only items referenced by edge requirements are keys.
    Invalid graph structure raises ValueError instead of becoming a false
    unreachable-room observation. This profile has no key consumption, dynamic
    edges, inventory capacity or irreversible transitions.
    """
    if not isinstance(graph, Mapping) or set(graph) != {"rooms", "start", "edges", "placements"}:
        raise ValueError("graph must have exactly rooms, start, edges and placements")
    rooms = _identifiers(graph["rooms"], "rooms")
    if not rooms:
        raise ValueError("rooms must not be empty")
    start = graph["start"]
    if not isinstance(start, str) or start not in rooms:
        raise ValueError("start must identify a declared room")
    placements = graph["placements"]
    if not isinstance(placements, Mapping) or any(
        not isinstance(item, str) or not item or not isinstance(room, str) or room not in rooms
        for item, room in placements.items()
    ):
        raise ValueError("placements must map nonempty item identifiers to declared rooms")
    edges = graph["edges"]
    if not isinstance(edges, (list, tuple)):
        raise TypeError("edges must be a list of edge records")
    adjacency = {room: [] for room in rooms}
    keys = set()
    for edge in edges:
        if not isinstance(edge, Mapping) or set(edge) != {"source", "target", "requires_keys"}:
            raise ValueError("each edge must have exactly source, target and requires_keys")
        source, target = edge["source"], edge["target"]
        if any(not isinstance(room, str) or room not in rooms for room in (source, target)):
            raise ValueError("edge endpoints must identify declared rooms")
        required = _identifiers(edge["requires_keys"], "requires_keys")
        if not required <= placements.keys():
            raise ValueError("every required key must have a placement")
        keys.update(required)
        adjacency[source].append((target, required))
        adjacency[target].append((source, required))

    pickups = {room: set() for room in rooms}
    for key in keys:
        pickups[placements[key]].add(key)
    initial = (start, frozenset(pickups[start]))
    pending = deque([initial])
    seen = {initial}
    reachable = set()
    while pending:
        room, inventory = pending.popleft()
        reachable.add(room)
        for destination, required in adjacency[room]:
            if required <= inventory:
                successor = (destination, inventory | pickups[destination])
                if successor not in seen:
                    seen.add(successor)
                    pending.append(successor)
    return frozenset(reachable)


def generic_accepts(state, candidate):
    """Reused ordinary-rule predicate over duck-typed state and candidate values."""
    policy = state.action_policies.get(candidate.action_type)
    if policy is None:
        return False
    if not policy.required_preconditions <= candidate.preconditions:
        return False
    if not policy.required_effects <= candidate.effects <= policy.allowed_effects:
        return False
    if candidate.quest_stage_effect is not None and (
        candidate.quest_stage_effect not in policy.allowed_quest_stage_effects
        or candidate.quest_stage_effect < state.quest_stage
    ):
        return False
    if not candidate.preconditions <= state.facts:
        return False
    if any(
        obj not in state.inventory
        and state.object_locations.get(obj) not in state.reachable_locations
        for obj in candidate.required_objects
    ):
        return False
    known = state.npc_knowledge.get(candidate.actor_id, frozenset())
    if not candidate.used_facts <= known or not candidate.disclosed_facts <= known:
        return False
    if candidate.disclosed_facts & state.forbidden_disclosures.get(candidate.actor_id, frozenset()):
        return False
    return candidate.required_quest_stage <= state.quest_stage
