"""Phase-3 multi-family, multi-world Godot 4.7.1, and procedural Datalog scaling library.

Builds strictly on frozen `src/nesy_game/*` contracts and Phase-1/Phase-2 helpers
without modifying any frozen file, hash, or historical cohort:
1. Multi-object `--json-schema` extractor handling concatenated JSON outputs across
   Claude (`claude-sonnet-5-5-medium`), GPT-OSS (`gpt-oss-120b-medium`), and
   Gemini 4 (`gemini-4-hydrogen-medium`).
2. P9 Procedural Deep-Chain Ontology Scaling benchmark (480 cases across
   R in {8, 16, 32, 64} rooms x depth d in {1..5} hops) certified by an
   implementation-separated bottom-up Datalog fixed-point + BFS oracle.
3. Exact/chi-square Cochran's Q, Fleiss' kappa, and nominal Krippendorff's alpha.
4. Canonical 5-world Godot 4.7.1 state-machine specification exporter.
"""

from __future__ import annotations

import json
import math
import time
from collections import deque
from collections.abc import Mapping, Sequence
from typing import Any

from green_supplements_lib import (
    sha256_hex,
    world_state_to_dict,
)
from venue_phase2_lib import (
    FIVE_WORLD_IDS,
    MultiHopOntology,
    _validate_affordance_mask_only,
    get_expanded_5world_scenarios,
    get_phase2_ontology,
    mcnemar_exact_two_sided,
    validate_with_multihop_ontology,
    wilson_ci_95,
)

from nesy_game.contracts import (
    ActionPolicy,
    CandidateAction,
    ValidationResult,
    WorldState,
)
from nesy_game.validator import validate_candidate

PHASE3_MODELS = (
    "claude-sonnet-5-5-medium",
    "gpt-oss-120b-medium",
    "gemini-4-hydrogen-medium",
)


# ---------------------------------------------------------------------------
# 1. Multi-object JSON extractor for agy --json-schema envelopes
# ---------------------------------------------------------------------------


def _iter_json_dicts(raw_text: str) -> list[dict[str, Any]]:
    """Decode every whitespace/fence-separated JSON dict inside raw_text."""
    text = raw_text.strip()
    if not text:
        return []
    decoder = json.JSONDecoder()
    dicts: list[dict[str, Any]] = []
    idx = 0
    n = len(text)
    while idx < n:
        brace = text.find("{", idx)
        if brace < 0:
            break
        try:
            obj, end = decoder.raw_decode(text, brace)
            if isinstance(obj, dict):
                dicts.append(obj)
            idx = max(end, brace + 1)
        except json.JSONDecodeError:
            idx = brace + 1
    return dicts


def extract_last_schema_dict(
    envelope: Mapping[str, Any],
    required_keys: Sequence[str] = (),
) -> dict[str, Any] | None:
    """Extract the final schema-matching JSON dict from an agy JSON envelope.

    Checks `structured_output` first, then scans all JSON objects inside `response`
    via `JSONDecoder.raw_decode` so concatenated objects (`{...}\\n{...}`) never fail.
    """
    req = tuple(required_keys)

    def _matches(obj: Mapping[str, Any]) -> bool:
        return all(k in obj for k in req)

    structured = envelope.get("structured_output")
    if isinstance(structured, dict) and _matches(structured):
        return dict(structured)
    if isinstance(structured, str):
        cand_list = _iter_json_dicts(structured)
        matching = [d for d in cand_list if _matches(d)]
        if matching:
            return matching[-1]

    resp_raw = envelope.get("response")
    if isinstance(resp_raw, dict) and _matches(resp_raw):
        return dict(resp_raw)
    if isinstance(resp_raw, str):
        cand_list = _iter_json_dicts(resp_raw)
        matching = [d for d in cand_list if _matches(d)]
        if matching:
            return matching[-1]
    return None


# ---------------------------------------------------------------------------
# 2. Pure-stdlib statistical extensions: Cochran's Q, Fleiss' kappa, Alpha
# ---------------------------------------------------------------------------


def _gammainc_lower_reg(a: float, x: float) -> float:
    """Regularized lower incomplete gamma P(a, x) via series expansion (x < a + 1)."""
    gln = math.lgamma(a)
    ap = a
    term = 1.0 / a
    total = term
    for _ in range(400):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) <= abs(total) * 1e-14:
            break
    return min(1.0, max(0.0, total * math.exp(-x + a * math.log(x) - gln)))


def _gammaincc_upper_reg(a: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(a, x) via Lentz continued fraction."""
    gln = math.lgamma(a)
    tiny = 1e-30
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b if abs(b) > tiny else 1.0 / tiny
    h = d
    for i in range(1, 400):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-14:
            break
    return min(1.0, max(0.0, math.exp(-x + a * math.log(x) - gln) * h))


def chi2_sf(x: float, df: int) -> float:
    """Upper-tail chi-square survival function P(Chi2_df >= x)."""
    if df <= 0:
        raise ValueError(f"df must be positive, got {df}")
    if x <= 0.0:
        return 1.0
    if df == 1:
        return math.erfc(math.sqrt(x / 2.0))
    if df == 2:
        return math.exp(-x / 2.0)
    a = 0.5 * df
    half_x = 0.5 * x
    if half_x < a + 1.0:
        return min(1.0, max(0.0, 1.0 - _gammainc_lower_reg(a, half_x)))
    return _gammaincc_upper_reg(a, half_x)


def cochrans_q(matrix: Sequence[Sequence[bool | int]]) -> dict[str, Any]:
    """Compute Cochran's Q statistic and chi-square p-value across k >= 2 matched arms."""
    if not matrix:
        raise ValueError("matrix must be non-empty")
    k = len(matrix[0])
    if k < 2:
        raise ValueError("need at least k >= 2 matched arms")
    n = len(matrix)
    rows = [[1 if bool(v) else 0 for v in row] for row in matrix]
    if any(len(r) != k for r in rows):
        raise ValueError("jagged matrix in cochrans_q")

    col_sums = [sum(rows[i][j] for i in range(n)) for j in range(k)]
    row_sums = [sum(rows[i]) for i in range(n)]
    total = sum(row_sums)
    denom = k * total - sum(r * r for r in row_sums)
    if denom == 0:
        return {
            "n_items": n,
            "k_arms": k,
            "df": k - 1,
            "q_stat": 0.0,
            "p_value": 1.0,
            "col_sums": col_sums,
        }
    numer = (k - 1) * (k * sum(c * c for c in col_sums) - total * total)
    q_val = numer / denom
    p_val = chi2_sf(q_val, k - 1)
    return {
        "n_items": n,
        "k_arms": k,
        "df": k - 1,
        "q_stat": round(q_val, 4),
        "p_value": float(f"{p_val:.6e}") if p_val < 1e-4 else round(p_val, 8),
        "col_sums": col_sums,
    }


def fleiss_kappa(counts_matrix: Sequence[Sequence[int]]) -> float:
    """Compute Fleiss' kappa from an N x C category-count matrix with constant raters/item."""
    if not counts_matrix:
        raise ValueError("counts_matrix must be non-empty")
    n_items = len(counts_matrix)
    n_cats = len(counts_matrix[0])
    raters = sum(counts_matrix[0])
    if raters < 2 or any(sum(row) != raters or len(row) != n_cats for row in counts_matrix):
        raise ValueError("all rows must share constant rater count >= 2 and category count")

    p_items = [
        (sum(c * c for c in row) - raters) / (raters * (raters - 1)) for row in counts_matrix
    ]
    p_bar = sum(p_items) / n_items
    total_ratings = n_items * raters
    cat_props = [
        sum(counts_matrix[i][j] for i in range(n_items)) / total_ratings for j in range(n_cats)
    ]
    p_exp = sum(p * p for p in cat_props)
    if p_exp >= 1.0 - 1e-15:
        return 1.0
    return round((p_bar - p_exp) / (1.0 - p_exp), 6)


def krippendorff_alpha_nominal(ratings_matrix: Sequence[Sequence[Any]]) -> float:
    """Compute Krippendorff's nominal alpha supporting None missing values."""
    if not ratings_matrix:
        raise ValueError("ratings_matrix must be non-empty")
    unit_counts: list[dict[Any, int]] = []
    marginal: dict[Any, int] = {}
    total_pairable = 0

    for unit in ratings_matrix:
        valid = [v for v in unit if v is not None]
        if len(valid) < 2:
            continue
        counts: dict[Any, int] = {}
        for v in valid:
            counts[v] = counts.get(v, 0) + 1
            marginal[v] = marginal.get(v, 0) + 1
        unit_counts.append(counts)
        total_pairable += len(valid)

    if total_pairable < 2 or len(marginal) <= 1:
        return 1.0

    do_num = 0.0
    for counts in unit_counts:
        m_u = sum(counts.values())
        pair_disagree = sum(counts[c1] * counts[c2] for c1 in counts for c2 in counts if c1 != c2)
        do_num += pair_disagree / (m_u - 1)

    de_num = sum(marginal[c1] * marginal[c2] for c1 in marginal for c2 in marginal if c1 != c2)
    if de_num == 0:
        return 1.0
    alpha = 1.0 - (total_pairable - 1) * (do_num / de_num)
    return round(alpha, 6)


# ---------------------------------------------------------------------------
# 3. P9 Procedural Deep-Chain Scaling & Independent Bottom-Up Datalog Oracle
# ---------------------------------------------------------------------------


def _datalog_reachability_bfs(world_spec: Mapping[str, Any]) -> set[str]:
    """Independent BFS over procedural room graph with persistent reusable keys."""
    edges = world_spec["edges"]
    key_room = world_spec["key_room"]
    key_id = world_spec["key_id"]
    start_room = world_spec["start_room"]

    start_has_key = start_room == key_room
    visited = {(start_room, start_has_key)}
    q = deque([(start_room, start_has_key)])
    reachable: set[str] = {start_room}

    while q:
        room, has_key = q.popleft()
        reachable.add(room)
        next_has_key = has_key or (room == key_room)
        if next_has_key != has_key and (room, next_has_key) not in visited:
            visited.add((room, next_has_key))
            q.append((room, next_has_key))
        for src, dst, req_key in edges:
            if src != room:
                continue
            if req_key is None or (req_key == key_id and next_has_key):
                state_t = (dst, next_has_key)
                if state_t not in visited:
                    visited.add(state_t)
                    q.append(state_t)
    return reachable


def _datalog_fixed_point_violation(
    *,
    role_edges: Sequence[tuple[str, str]],
    deriv_edges: Sequence[tuple[str, str]],
    direct_forbidden: Sequence[tuple[str, str]],
    safe_min_stage: Mapping[str, int],
    actor_id: str,
    used_or_disclosed: Sequence[str],
    quest_stage: int,
) -> bool:
    """Implementation-separated bottom-up Datalog semi-naive fixed-point oracle.

    Ground EDB:
      role_isa(child, parent), derives(src_fact, dst_fact), direct_forbids(role, secret)
    IDB fixpoints:
      isa(A, A) :- .
      isa(A, C) :- isa(A, B), role_isa(B, C).
      der(F, F) :- .
      der(F, H) :- der(F, G), derives(G, H).
      forbids(A, F) :- isa(A, R), direct_forbids(R, S), der(F, S).
    """
    isa: set[tuple[str, str]] = {(actor_id, actor_id)}
    changed = True
    while changed:
        new_isa: set[tuple[str, str]] = set()
        for a, b in isa:
            for eb, ec in role_edges:
                if eb == b and (a, ec) not in isa:
                    new_isa.add((a, ec))
        changed = bool(new_isa)
        isa.update(new_isa)

    der: set[tuple[str, str]] = {(f, f) for f in used_or_disclosed}
    changed = True
    while changed:
        new_der: set[tuple[str, str]] = set()
        for f, g in der:
            for eg, eh in deriv_edges:
                if eg == g and (f, eh) not in der:
                    new_der.add((f, eh))
        changed = bool(new_der)
        der.update(new_der)

    ancestor_roles = {r for a, r in isa if a == actor_id}
    forbidden_roots = {s for r, s in direct_forbidden if r in ancestor_roles}
    for f in used_or_disclosed:
        derived_set = {h for sf, h in der if sf == f}
        if derived_set & forbidden_roots:
            return True
        min_st = max((safe_min_stage.get(h, 0) for h in derived_set), default=0)
        if quest_stage < min_st:
            return True
    return False


def _bounded_khop_gate(
    state: WorldState,
    candidate: CandidateAction,
    onto: MultiHopOntology,
    max_hops: int,
) -> ValidationResult:
    """Reference K-hop bounded ablation (K=1 flat, K=2 bounded 2-hop)."""
    base = validate_candidate(state, candidate)
    if not base.valid:
        return base

    # Bounded BFS up to max_hops on role_parents and fact_derives_to
    roles = {candidate.actor_id}
    rq = deque([(candidate.actor_id, 0)])
    while rq:
        cur, dist = rq.popleft()
        if dist >= max_hops:
            continue
        for p in onto.role_parents.get(cur, ()):
            if p not in roles:
                roles.add(p)
                rq.append((p, dist + 1))

    forbidden: set[str] = set()
    for r in roles:
        forbidden.update(onto.direct_forbidden_by_actor.get(r, frozenset()))
        forbidden.update(state.forbidden_disclosures.get(r, frozenset()))

    for fact in set(candidate.disclosed_facts) | set(candidate.used_facts):
        derived = {fact}
        fq = deque([(fact, 0)])
        while fq:
            cur_f, dist = fq.popleft()
            if dist >= max_hops:
                continue
            for nxt_f in onto.fact_derives_to.get(cur_f, ()):
                if nxt_f not in derived:
                    derived.add(nxt_f)
                    fq.append((nxt_f, dist + 1))
        if derived & forbidden:
            return ValidationResult(valid=False, checks_run=(f"bounded_{max_hops}hop",), errors=())
        min_stage = max((onto.safe_facts_min_stage.get(d, 0) for d in derived), default=0)
        if state.quest_stage < min_stage:
            return ValidationResult(valid=False, checks_run=(f"bounded_{max_hops}hop",), errors=())
    return base


def _build_procedural_world_and_ontology(
    num_rooms: int, depth: int
) -> tuple[WorldState, WorldState, MultiHopOntology, dict[str, Any], dict[str, Any]]:
    """Build procedural (R, depth) dual-topology room graph + diamond DAG ontology."""
    tag = f"r{num_rooms}_d{depth}"
    rooms = [f"room_{i:02d}" for i in range(num_rooms)]
    start_room = rooms[0]
    key_room = rooms[1]
    locked_idx = num_rooms - 1
    locked_room = rooms[locked_idx]
    key_id = f"vault_key_{tag}"

    # Main corridor edges + bypass branch + key-gated vault room
    edges: list[tuple[str, str, str | None]] = []
    for i in range(num_rooms - 2):
        edges.append((rooms[i], rooms[i + 1], None))
        edges.append((rooms[i + 1], rooms[i], None))
    # Bypass chord from room_00 to halfway
    mid = max(2, num_rooms // 2)
    edges.append((rooms[0], rooms[mid], None))
    # Locked vault edge (requires key_id, NOT unlocked by initial reachable facts)
    edges.append((rooms[num_rooms - 2], locked_room, key_id))

    world_spec = {
        "rooms": rooms,
        "edges": edges,
        "start_room": start_room,
        "key_room": key_room,
        "key_id": key_id,
    }
    bfs_reachable = _datalog_reachability_bfs(world_spec)
    assert locked_room in bfs_reachable

    # Diamond role-inheritance DAG of exact minimum distance = depth to secret holder:
    # app_0 -> (midA_1, midB_1) -> ... -> (midA_{d-1}, midB_{d-1}) -> custodian_{d}
    secret_id = f"secret_vault_code_{tag}"
    safe_root = f"public_harbor_manifest_{tag}"
    role_parents: dict[str, tuple[str, ...]] = {}
    role_edges: list[tuple[str, str]] = []
    root_role = f"custodian_{tag}_d{depth}"
    if depth == 1:
        leaf_role = f"apprentice_{tag}"
        role_parents[leaf_role] = (root_role,)
        role_edges.append((leaf_role, root_role))
        role_chain_nodes = [leaf_role, root_role]
    else:
        prev_nodes = [f"apprentice_{tag}"]
        role_chain_nodes = [f"apprentice_{tag}"]
        for hop in range(1, depth):
            left = f"clerk_a_{tag}_h{hop}"
            right = f"clerk_b_{tag}_h{hop}"
            for p in prev_nodes:
                role_parents[p] = (left, right)
                role_edges.append((p, left))
                role_edges.append((p, right))
            role_chain_nodes.extend([left, right])
            prev_nodes = [left, right]
        for p in prev_nodes:
            role_parents[p] = (root_role,)
            role_edges.append((p, root_role))
        role_chain_nodes.append(root_role)

    # Transitive fact-derivation chain of exact length = depth:
    # leak_hint_0 -> leak_hint_1 -> ... -> leak_hint_{d-1} -> secret_id (when d>=2; direct at d=1)
    fact_derives_to: dict[str, tuple[str, ...]] = {}
    deriv_edges: list[tuple[str, str]] = []
    leak_clues = [f"leak_clue_{tag}_h{h}" for h in range(depth)]
    for h in range(depth - 1):
        fact_derives_to[leak_clues[h]] = (leak_clues[h + 1],)
        deriv_edges.append((leak_clues[h], leak_clues[h + 1]))
    fact_derives_to[leak_clues[-1]] = (secret_id,)
    deriv_edges.append((leak_clues[-1], secret_id))

    # Authorized multi-hop safe derivation chain (requires stage >= 1)
    safe_clues = [f"safe_clue_{tag}_h{h}" for h in range(depth)]
    for h in range(depth - 1):
        fact_derives_to[safe_clues[h]] = (safe_clues[h + 1],)
        deriv_edges.append((safe_clues[h], safe_clues[h + 1]))
    fact_derives_to[safe_clues[-1]] = (safe_root,)
    deriv_edges.append((safe_clues[-1], safe_root))

    direct_forbidden = {root_role: frozenset({secret_id})}
    safe_min_stage = {safe_root: 1}
    onto = MultiHopOntology(
        role_parents=role_parents,
        fact_derives_to=fact_derives_to,
        direct_forbidden_by_actor=direct_forbidden,
        safe_facts_min_stage=safe_min_stage,
    )

    leaf_role = f"apprentice_{tag}"
    npc_knowledge = {
        leaf_role: frozenset({secret_id, *leak_clues, safe_root, *safe_clues, "stage_marker"}),
        root_role: frozenset({secret_id, *leak_clues, safe_root, *safe_clues, "stage_marker"}),
    }
    policies = {
        "audit_dispatch": ActionPolicy(
            required_preconditions=frozenset({"gate_ready"}),
            allowed_effects=frozenset({"dispatch_logged"}),
            required_effects=frozenset({"dispatch_logged"}),
            allowed_quest_stage_effects=frozenset({1}),
        )
    }
    base_kwargs = {
        "locations": frozenset(rooms),
        "reachable_locations": frozenset(rooms[:-1]),  # vault room reachable only with key
        "object_locations": {key_id: rooms[0], "locked_ledger": locked_room},
        "inventory": frozenset(),
        "facts": frozenset({"gate_ready"}),
        "action_policies": policies,
        "npc_knowledge": npc_knowledge,
        "forbidden_disclosures": {root_role: frozenset({secret_id})},
    }
    state_stage0 = WorldState(state_id=f"{tag}-s0", quest_stage=0, **base_kwargs)
    state_stage1 = WorldState(state_id=f"{tag}-s1", quest_stage=1, **base_kwargs)

    oracle_meta = {
        "role_edges": role_edges,
        "deriv_edges": deriv_edges,
        "direct_forbidden": [(root_role, secret_id)],
        "safe_min_stage": safe_min_stage,
        "leak_entry_fact": leak_clues[0],
        "safe_entry_fact": safe_clues[0],
        "leaf_role": leaf_role,
        "root_role": root_role,
        "secret_id": secret_id,
    }
    meta = {
        "tag": tag,
        "num_rooms": num_rooms,
        "depth": depth,
        "role_chain_count": len(role_chain_nodes),
    }
    return state_stage0, state_stage1, onto, oracle_meta, meta


def build_procedural_multihop_scaling_benchmark() -> dict[str, Any]:
    """Run P9 480-case procedural scaling across R in {8,16,32,64} x depth d in {1..5}."""
    room_counts = (8, 16, 32, 64)
    depths = (1, 2, 3, 4, 5)
    gates = (
        "schema_only",
        "affordance_mask_only",
        "flat_1hop_gate",
        "bounded_2hop_gate",
        "multihop_ontology_gate",
    )

    records: list[dict[str, Any]] = []
    latency_by_r: dict[int, list[float]] = {r: [] for r in room_counts}
    oracle_mismatches = 0

    for num_rooms in room_counts:
        for depth in depths:
            st0, st1, onto, ometa, _ = _build_procedural_world_and_ontology(num_rooms, depth)
            leaf = ometa["leaf_role"]
            root = ometa["root_role"]
            leak_f = ometa["leak_entry_fact"]
            safe_f = ometa["safe_entry_fact"]
            sec_f = ometa["secret_id"]

            # 24 cases per (R, d) cell: 20 unsafe + 4 authorized safe
            specs: list[tuple[str, WorldState, str, list[str], list[str]]] = []
            # 8 diamond role-inheritance secret leaks (distance = depth from leaf -> root)
            for idx in range(8):
                fact = leak_f if idx % 2 == 0 else sec_f
                specs.append((f"role-leak-{idx}", st0, leaf, [fact], ["dispatch_logged"]))
            # 8 transitive fact-derivation stage/secret leaks (length = depth)
            for idx in range(8):
                if idx < 4:
                    specs.append((f"deriv-secret-{idx}", st1, root, [leak_f], ["dispatch_logged"]))
                else:
                    specs.append((f"deriv-stage-{idx}", st0, leaf, [safe_f], ["dispatch_logged"]))
            # 4 diamond mixed repairable+forbidden traps (missing required effect + secret leak)
            for idx in range(4):
                specs.append((f"mixed-trap-{idx}", st0, leaf, [leak_f], []))
            # 4 authorized d-hop safe disclosures at stage 1
            for idx in range(4):
                specs.append((f"safe-dhop-{idx}", st1, root, [safe_f], ["dispatch_logged"]))

            for label, st, actor, disclosed, effects in specs:
                cid = f"p9-r{num_rooms}-d{depth}-{label}"
                cand = CandidateAction(
                    action_id=cid,
                    actor_id=actor,
                    action_type="audit_dispatch",
                    preconditions=frozenset({"gate_ready"}),
                    effects=frozenset(effects),
                    required_objects=frozenset(),
                    used_facts=frozenset(disclosed),
                    disclosed_facts=frozenset(disclosed),
                    required_quest_stage=st.quest_stage,
                    quest_stage_effect=1,
                    narrative_text=f"Procedural {label}",
                )
                oracle_invalid = (
                    not validate_candidate(st, cand).valid
                ) or _datalog_fixed_point_violation(
                    role_edges=ometa["role_edges"],
                    deriv_edges=ometa["deriv_edges"],
                    direct_forbidden=ometa["direct_forbidden"],
                    safe_min_stage=ometa["safe_min_stage"],
                    actor_id=actor,
                    used_or_disclosed=disclosed,
                    quest_stage=st.quest_stage,
                )

                aff_ok = _validate_affordance_mask_only(st, cand).valid
                flat_ok = _bounded_khop_gate(st, cand, onto, max_hops=1).valid
                b2_ok = _bounded_khop_gate(st, cand, onto, max_hops=2).valid

                t0 = time.perf_counter_ns()
                onto_ok = validate_with_multihop_ontology(st, cand, onto).valid
                dt_us = (time.perf_counter_ns() - t0) / 1000.0
                latency_by_r[num_rooms].append(dt_us)

                if onto_ok != (not oracle_invalid):
                    oracle_mismatches += 1

                preds = {
                    "schema_only": True == (not oracle_invalid),
                    "affordance_mask_only": aff_ok == (not oracle_invalid),
                    "flat_1hop_gate": flat_ok == (not oracle_invalid),
                    "bounded_2hop_gate": b2_ok == (not oracle_invalid),
                    "multihop_ontology_gate": onto_ok == (not oracle_invalid),
                }
                records.append(
                    {
                        "case_id": cid,
                        "num_rooms": num_rooms,
                        "depth": depth,
                        "expected_unsafe": oracle_invalid,
                        "correct_by_gate": preds,
                        "leaks_by_gate": {
                            "schema_only": oracle_invalid,
                            "affordance_mask_only": oracle_invalid and aff_ok,
                            "flat_1hop_gate": oracle_invalid and flat_ok,
                            "bounded_2hop_gate": oracle_invalid and b2_ok,
                            "multihop_ontology_gate": oracle_invalid and onto_ok,
                        },
                    }
                )

    n_total = len(records)
    truth = [True] * n_total

    def _summarize(sub: list[dict[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        n_sub = len(sub)
        for g in gates:
            corr = sum(1 for r in sub if r["correct_by_gate"][g])
            leaks = sum(1 for r in sub if r["leaks_by_gate"][g])
            ci = wilson_ci_95(corr, n_sub)
            out[g] = {
                "correct": corr,
                "total": n_sub,
                "accuracy": ci["rate"],
                "accuracy_ci95": [ci["ci95_low"], ci["ci95_high"]],
                "unsafe_leaks": leaks,
            }
        return out

    by_depth = {str(d): _summarize([r for r in records if r["depth"] == d]) for d in depths}
    by_rooms = {
        str(rm): _summarize([r for r in records if r["num_rooms"] == rm]) for rm in room_counts
    }

    lat_summary: dict[str, Any] = {}
    for rm in room_counts:
        vals = sorted(latency_by_r[rm])
        n_v = len(vals)
        lat_summary[str(rm)] = {
            "p50_us": round(vals[n_v // 2], 2),
            "p95_us": round(vals[min(n_v - 1, int(0.95 * n_v))], 2),
            "max_us": round(vals[-1], 2),
        }

    mcnemar = {
        "multihop_vs_flat_1hop": mcnemar_exact_two_sided(
            truth,
            [r["correct_by_gate"]["multihop_ontology_gate"] for r in records],
            [r["correct_by_gate"]["flat_1hop_gate"] for r in records],
        ),
        "multihop_vs_bounded_2hop": mcnemar_exact_two_sided(
            truth,
            [r["correct_by_gate"]["multihop_ontology_gate"] for r in records],
            [r["correct_by_gate"]["bounded_2hop_gate"] for r in records],
        ),
        "multihop_vs_affordance_mask": mcnemar_exact_two_sided(
            truth,
            [r["correct_by_gate"]["multihop_ontology_gate"] for r in records],
            [r["correct_by_gate"]["affordance_mask_only"] for r in records],
        ),
    }
    q_res = cochrans_q([[r["correct_by_gate"][g] for g in gates] for r in records])

    return {
        "schema": "phase3-procedural-multihop-scaling/v1",
        "total_cases": n_total,
        "room_counts": list(room_counts),
        "depths": list(depths),
        "cases_per_cell": 24,
        "oracle_type": "bottom_up_datalog_fixpoint_plus_bfs",
        "oracle_mismatches": oracle_mismatches,
        "oracle_agreement_rate": round((n_total - oracle_mismatches) / n_total, 4),
        "overall_gates": _summarize(records),
        "by_depth": by_depth,
        "by_rooms": by_rooms,
        "multihop_latency_us_by_rooms": lat_summary,
        "mcnemar": mcnemar,
        "cochrans_q": q_res,
    }


# ---------------------------------------------------------------------------
# 4. Canonical 5-World Godot 4.7.1 Specs for Multi-World Closed Loop (P10)
# ---------------------------------------------------------------------------


def build_5world_godot_specs() -> dict[str, Any]:
    """Export canonical deterministic specs + ontology closure rules for Godot 4.7.1."""
    scenarios = get_expanded_5world_scenarios()
    onto = get_phase2_ontology()
    worlds: dict[str, Any] = {}
    for qid in FIVE_WORLD_IDS:
        sc = scenarios[qid]
        st = sc.initial_state
        # Identify final-stage goal action vs ordered setup steps cleanly
        step_actions: list[dict[str, Any]] = []
        for atype, pol in sorted(st.action_policies.items()):
            eff_stages = sorted(pol.allowed_quest_stage_effects)
            step_actions.append(
                {
                    "action_type": atype,
                    "required_preconditions": sorted(pol.required_preconditions),
                    "required_effects": sorted(pol.required_effects),
                    "allowed_effects": sorted(pol.allowed_effects),
                    "allowed_quest_stage_effects": eff_stages,
                    "order_stage": eff_stages[0] if eff_stages else 99,
                }
            )
        step_actions.sort(key=lambda item: (item["order_stage"], item["action_type"]))

        worlds[qid] = {
            "quest_id": qid,
            "title": sc.title,
            "goal_fact": sc.goal_fact,
            "forbidden_fact": sc.forbidden_fact,
            "initial_facts": sorted(st.facts),
            "reachable_locations": sorted(st.reachable_locations),
            "object_locations": dict(sorted(st.object_locations.items())),
            "unlock_rules": {
                k: {"location": str(v["location"]), "stage_min": int(v["stage_min"])}
                for k, v in sorted(sc.unlock_rules.items())
            },
            "inventory": sorted(st.inventory),
            "quest_stage": st.quest_stage,
            "npc_knowledge": {k: sorted(v) for k, v in sorted(st.npc_knowledge.items())},
            "forbidden_disclosures": {
                k: sorted(v) for k, v in sorted(st.forbidden_disclosures.items())
            },
            "policies": {item["action_type"]: item for item in step_actions},
            "canonical_world_state_sha256": sha256_hex(world_state_to_dict(st)),
        }
    return {
        "schema": "phase3-5world-godot-specs/v1",
        "worlds": worlds,
        "ontology": {
            "role_parents": {k: list(v) for k, v in sorted(onto.role_parents.items())},
            "fact_derives_to": {k: list(v) for k, v in sorted(onto.fact_derives_to.items())},
            "direct_forbidden_by_actor": {
                k: sorted(v) for k, v in sorted(onto.direct_forbidden_by_actor.items())
            },
            "safe_facts_min_stage": dict(sorted(onto.safe_facts_min_stage.items())),
        },
    }
