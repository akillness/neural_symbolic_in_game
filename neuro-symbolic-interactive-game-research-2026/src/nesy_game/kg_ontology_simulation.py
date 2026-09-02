"""Deterministic, claim-bounded evaluation for typed OKF link proposals.

This module builds a repository-local methods graph. It never participates in
runtime authorization and never reads or writes the Godot project.
"""

from __future__ import annotations

import hashlib
import html
import json
import math
import os
import re
import sqlite3
import tempfile
from collections import deque
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"
SIMULATION_ID = "SL-KG-ONTOLOGY-SIM-001"
EXCLUDED_RESULT_CLAIMS = tuple(f"C-RESULT-{index:03d}" for index in range(1, 6))
TRACKED_OUTPUTS = {
    "graph": Path("knowledge/graphify-out/okf-links.json"),
    "matrix_json": Path("research/simulation/kg-ontology/latest/evaluation-matrix.json"),
    "matrix_md": Path("research/simulation/kg-ontology/latest/evaluation-matrix.md"),
    "trials_tsv": Path("research/simulation/kg-ontology/latest/strategy-trials.tsv"),
    "recommendations": Path("research/simulation/kg-ontology/latest/recommendations.json"),
    "svg": Path("research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg"),
    "paper_en": Path("paper/latex/generated/kg_ontology_simulation_en.tex"),
    "paper_ko": Path("paper/latex/generated/kg_ontology_simulation_ko.tex"),
    "manifest": Path("research/simulation/kg-ontology/latest/sha256-manifest.json"),
}
DEFAULT_DATABASE = Path("research/simulation/kg-ontology/latest/trace-rpg-knowledge.sqlite")

_LINK_RE = re.compile(r"\[([^\]]+)\]\((/[^)#]+\.md)(?:#[^)]+)?\)")
_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)
_STOPWORDS = {
    "a",
    "an",
    "and",
    "at",
    "before",
    "by",
    "each",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "which",
    "with",
    "각",
    "어떤",
    "무엇인가",
    "측정하는",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        os.fchmod(handle.fileno(), 0o644)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def _parse_frontmatter(path: Path, text: str) -> tuple[dict[str, Any], str]:
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0].strip():
        raise ValueError(f"missing OKF frontmatter: {path}")
    fields: dict[str, Any] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if key == "tags":
            if not (raw_value.startswith("[") and raw_value.endswith("]")):
                raise ValueError(f"tags must be an inline list: {path}")
            fields[key] = sorted(
                item.strip() for item in raw_value[1:-1].split(",") if item.strip()
            )
        else:
            fields[key] = raw_value
    required = {"type", "title", "description", "tags", "timestamp"}
    missing = sorted(required - fields.keys())
    if missing:
        raise ValueError(f"missing OKF fields in {path}: {missing}")
    return fields, parts[2]


def build_okf_graph(knowledge_root: Path, project_root: Path) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for path in sorted(knowledge_root.rglob("*.md")):
        if "graphify-out" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter, body = _parse_frontmatter(path, text)
        relative = path.relative_to(knowledge_root).as_posix()
        node_id = f"/{relative}"
        nodes.append(
            {
                "id": node_id,
                "type": frontmatter["type"],
                "title": frontmatter["title"],
                "description": frontmatter["description"],
                "tags": frontmatter["tags"],
                "timestamp": frontmatter["timestamp"],
                "source_path": path.relative_to(project_root).as_posix(),
                "sha256": sha256_path(path),
            }
        )
        for label, target in _LINK_RE.findall(body):
            digest = sha256_bytes(f"{node_id}\0references\0{target}".encode())[:20]
            edges.append(
                {
                    "id": f"REF-{digest}",
                    "source": node_id,
                    "relation": "references",
                    "target": target,
                    "label": " ".join(label.split()),
                    "evidence": path.relative_to(project_root).as_posix(),
                    "curated": False,
                }
            )
    nodes.sort(key=lambda row: row["id"])
    edges.sort(key=lambda row: (row["source"], row["target"], row["label"]))
    return {
        "schema_version": "2.0.0",
        "graph_id": "TRACE-RPG-OKF-METHODS-001",
        "directed": True,
        "multigraph": False,
        "claim_boundary": (
            "Documentation graph only; never an authorization source or C-RESULT evidence."
        ),
        "summary": {"nodes": len(nodes), "reference_edges": len(edges)},
        "nodes": nodes,
        "edges": edges,
    }


def _type_allowed(actual: str, allowed: list[str]) -> bool:
    return "*" in allowed or actual in allowed


def validate_ontology(ontology: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    node_types = ontology.get("node_types")
    relations = ontology.get("relation_types")
    if not isinstance(node_types, list) or not node_types:
        errors.append("ontology.node_types must be a non-empty list")
        node_types = []
    if len(node_types) != len(set(node_types)):
        errors.append("ontology.node_types contains duplicates")
    if not isinstance(relations, dict) or not relations:
        errors.append("ontology.relation_types must be a non-empty object")
        relations = {}
    declared = set(node_types)
    validator_mappings: list[str] = []
    for relation, spec in sorted(relations.items()):
        if not isinstance(spec, dict):
            errors.append(f"relation {relation} must be an object")
            continue
        for side in ("domain", "range"):
            values = spec.get(side)
            if not isinstance(values, list) or not values:
                errors.append(f"relation {relation}.{side} must be a non-empty list")
                continue
            unknown = sorted(set(values) - declared - {"*"})
            if unknown:
                errors.append(f"relation {relation}.{side} has unknown types: {unknown}")
        predicate = spec.get("validator_predicate")
        if spec.get("layer") == "game-state" and predicate:
            validator_mappings.append(predicate)
    expected_predicates = {
        "v_policy",
        "v_pre",
        "v_reach",
        "v_know",
        "v_disc",
        "v_quest",
    }
    if set(validator_mappings) != expected_predicates:
        errors.append(
            "game-state validator mapping drift: "
            f"{sorted(set(validator_mappings))} != {sorted(expected_predicates)}"
        )
    questions = ontology.get("competency_questions")
    if not isinstance(questions, list) or not questions:
        errors.append("ontology.competency_questions must be a non-empty list")
        questions = []
    question_ids = [row.get("id") for row in questions if isinstance(row, dict)]
    if len(question_ids) != len(set(question_ids)):
        errors.append("ontology.competency_questions contains duplicate IDs")
    for question in questions:
        if not isinstance(question, dict):
            errors.append("competency question must be an object")
            continue
        question_id = question.get("id")
        relation = question.get("relation")
        source_type = question.get("source_type")
        target_type = question.get("target_type")
        if relation not in relations:
            errors.append(f"competency question {question_id} has unknown relation: {relation}")
        elif source_type in declared and target_type in declared:
            relation_spec = relations[relation]
            if not _type_allowed(source_type, relation_spec["domain"]) or not _type_allowed(
                target_type, relation_spec["range"]
            ):
                errors.append(f"competency question {question_id} violates relation domain/range")
        if source_type not in declared or target_type not in declared:
            errors.append(f"competency question {question_id} has unknown endpoint type")
        required_sources = question.get("required_sources")
        if not isinstance(required_sources, dict) or not required_sources:
            errors.append(f"competency question {question_id} requires explicit sources")
            continue
        if any(not isinstance(value, int) or value < 1 for value in required_sources.values()):
            errors.append(f"competency question {question_id} has invalid source minimum")
        minimum_answers = question.get("minimum_answers")
        if not isinstance(minimum_answers, int) or minimum_answers < sum(required_sources.values()):
            errors.append(f"competency question {question_id} has an invalid aggregate minimum")
    return errors


def validate_graph(
    graph: dict[str, Any], ontology: dict[str, Any], curated: dict[str, Any], project_root: Path
) -> list[str]:
    errors = validate_ontology(ontology)
    node_types = set(ontology.get("node_types", []))
    relations = ontology.get("relation_types", {})
    nodes = graph.get("nodes", [])
    node_by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        node_id = node.get("id")
        if node_id in node_by_id:
            errors.append(f"duplicate node: {node_id}")
        node_by_id[node_id] = node
        if node.get("type") not in node_types:
            errors.append(f"undeclared node type: {node_id}:{node.get('type')}")
        source_path = project_root / str(node.get("source_path", ""))
        if not source_path.is_file():
            errors.append(f"node source missing: {node_id}:{source_path}")
        elif sha256_path(source_path) != node.get("sha256"):
            errors.append(f"node source hash mismatch: {node_id}")
    seen_edge_ids: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()
    all_edges = list(graph.get("edges", [])) + [
        {**row, "curated": True, "label": row["relation"]} for row in curated.get("edges", [])
    ]
    for edge in all_edges:
        edge_id = str(edge.get("id"))
        if edge_id in seen_edge_ids:
            errors.append(f"duplicate edge ID: {edge_id}")
        seen_edge_ids.add(edge_id)
        source = edge.get("source")
        target = edge.get("target")
        relation = edge.get("relation")
        signature = (str(source), str(relation), str(target))
        if signature in seen_edges:
            errors.append(f"duplicate edge: {signature}")
        seen_edges.add(signature)
        if source == target:
            errors.append(f"self edge: {signature}")
        if source not in node_by_id:
            errors.append(f"unresolved source: {source}")
        if target not in node_by_id:
            errors.append(f"unresolved target: {target}")
        if relation not in relations:
            errors.append(f"undeclared relation: {relation}")
            continue
        if source not in node_by_id or target not in node_by_id:
            continue
        spec = relations[relation]
        if not _type_allowed(node_by_id[source]["type"], spec["domain"]):
            errors.append(f"domain violation: {signature}")
        if not _type_allowed(node_by_id[target]["type"], spec["range"]):
            errors.append(f"range violation: {signature}")
        evidence = project_root / str(edge.get("evidence", ""))
        if not evidence.is_file():
            errors.append(f"edge evidence missing: {signature}:{evidence}")
    for question in ontology.get("competency_questions", []):
        for source_id in question.get("required_sources", {}):
            source = node_by_id.get(source_id)
            if source is None:
                errors.append(
                    f"competency question {question.get('id')} source missing: {source_id}"
                )
            elif source["type"] != question.get("source_type"):
                errors.append(
                    f"competency question {question.get('id')} source type mismatch: {source_id}"
                )
    return errors


def competency_question_results(
    graph: dict[str, Any], ontology: dict[str, Any], curated: dict[str, Any]
) -> list[dict[str, Any]]:
    node_by_id = {row["id"]: row for row in graph["nodes"]}
    edges = curated["edges"]
    results = []
    for question in ontology["competency_questions"]:
        answers = [
            edge
            for edge in edges
            if edge["relation"] == question["relation"]
            and node_by_id[edge["source"]]["type"] == question["source_type"]
            and node_by_id[edge["target"]]["type"] == question["target_type"]
        ]
        counts_by_source = {
            source_id: sum(edge["source"] == source_id for edge in answers)
            for source_id in sorted(question["required_sources"])
        }
        satisfied_sources = sum(
            counts_by_source[source_id] >= minimum
            for source_id, minimum in question["required_sources"].items()
        )
        source_count = len(question["required_sources"])
        results.append(
            {
                "id": question["id"],
                "answers": len(answers),
                "minimum_answers": question["minimum_answers"],
                "required_sources": question["required_sources"],
                "answers_by_source": counts_by_source,
                "source_coverage": round(_safe_ratio(satisfied_sources, source_count), 12),
                "pass": len(answers) >= question["minimum_answers"]
                and satisfied_sources == source_count,
            }
        )
    return results


def _tokens(*values: Any) -> set[str]:
    result: set[str] = set()
    for value in values:
        if isinstance(value, list):
            value = " ".join(str(item) for item in value)
        for token in _TOKEN_RE.findall(str(value).casefold()):
            if token not in _STOPWORDS:
                result.add(token)
    return result


def _jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def validate_benchmark_config(
    config: dict[str, Any], curated: dict[str, Any], node_ids: set[str]
) -> None:
    budget = config["budget"]
    strategies = config["strategies"]
    queries = config["queries"]
    if budget["strategy_trials"] != len(strategies):
        raise ValueError("strategy budget does not match configured trials")
    if budget["queries_per_trial"] != len(queries):
        raise ValueError("query budget does not match configured queries")
    expected_scores = budget["queries_per_trial"] * budget["candidates_per_query"]
    if budget["candidate_scores_per_trial"] != expected_scores:
        raise ValueError("candidate-score budget drift")
    if budget["candidate_scores_total"] != expected_scores * budget["strategy_trials"]:
        raise ValueError("total candidate-score budget drift")
    if not 1 <= budget["decision_k"] <= budget["ranking_k"] <= budget["candidates_per_query"]:
        raise ValueError("ranking/decision budget drift")

    strategy_ids = [row["id"] for row in strategies]
    if len(strategy_ids) != len(set(strategy_ids)):
        raise ValueError("duplicate strategy ID")
    feature_names = {"degree", "lexical", "path", "type_fit"}
    for strategy in strategies:
        if set(strategy["weights"]) != feature_names:
            raise ValueError(f"strategy feature drift: {strategy['id']}")
        if not 0.0 <= float(strategy["threshold"]) <= 1.0:
            raise ValueError(f"strategy threshold out of range: {strategy['id']}")

    order = config["selection_rule"]["strict_improvement_order"]
    objective_names = {
        "precision",
        "mrr_realistic",
        "ndcg_at_k",
        "negative_brier_score",
        "negative_nonzero_weight_count",
    }
    if not order or len(order) != len(set(order)) or set(order) - objective_names:
        raise ValueError("strict-improvement objective order drift")
    for floor_name in ("recall_floor", "coverage_floor", "semantic_at_k_floor"):
        floor = float(config["selection_rule"][floor_name])
        if not 0.0 <= floor <= 1.0:
            raise ValueError(f"selection floor out of range: {floor_name}")

    curated_ids = [row["id"] for row in curated["edges"]]
    if len(curated_ids) != len(set(curated_ids)):
        raise ValueError("duplicate curated relation ID")
    relation_by_id = {row["id"]: row for row in curated["edges"]}
    configured_holdouts = config["holdout_relation_ids"]
    query_holdouts = [query["holdout_relation_id"] for query in queries]
    if len(configured_holdouts) != len(set(configured_holdouts)):
        raise ValueError("duplicate configured holdout relation ID")
    if len(query_holdouts) != len(set(query_holdouts)):
        raise ValueError("duplicate query holdout relation ID")
    if configured_holdouts != query_holdouts:
        raise ValueError("configured holdouts must exactly match query holdouts in order")
    if set(configured_holdouts) - relation_by_id.keys():
        raise ValueError("holdout relation ID is missing from curated relations")

    query_ids = [query["id"] for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("duplicate benchmark query ID")
    for query in queries:
        relation = relation_by_id[query["holdout_relation_id"]]
        if (query["source"], query["relation"]) != (
            relation["source"],
            relation["relation"],
        ):
            raise ValueError(f"query/holdout mismatch: {query['id']}")
        candidates = query["candidates"]
        relevant = [candidate for candidate in candidates if candidate["relevant"]]
        if len(relevant) != 1 or relevant[0]["target"] != relation["target"]:
            raise ValueError(f"query gold relation mismatch: {query['id']}")
        if len(candidates) != budget["candidates_per_query"]:
            raise ValueError(f"candidate budget mismatch: {query['id']}")
        candidate_ids = [candidate["id"] for candidate in candidates]
        candidate_targets = [candidate["target"] for candidate in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError(f"duplicate candidate ID: {query['id']}")
        if len(candidate_targets) != len(set(candidate_targets)):
            raise ValueError(f"duplicate candidate target: {query['id']}")
        if {query["source"], *candidate_targets} - node_ids:
            raise ValueError(f"query has unresolved endpoint: {query['id']}")


def _adjacency(
    graph: dict[str, Any], curated: dict[str, Any], holdout_edges: list[dict[str, Any]]
) -> dict[str, set[str]]:
    removed_pairs = {frozenset((edge["source"], edge["target"])) for edge in holdout_edges}
    adjacency: dict[str, set[str]] = {row["id"]: set() for row in graph["nodes"]}
    training_edges = list(graph["edges"]) + curated["edges"]
    for edge in training_edges:
        source, target = edge["source"], edge["target"]
        if frozenset((source, target)) in removed_pairs:
            continue
        adjacency[source].add(target)
        adjacency[target].add(source)
    return adjacency


def _shortest_path(adjacency: dict[str, set[str]], source: str, target: str) -> int | None:
    if source == target:
        return 0
    queue = deque([(source, 0)])
    visited = {source}
    while queue:
        current, distance = queue.popleft()
        for neighbor in sorted(adjacency[current]):
            if neighbor == target:
                return distance + 1
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, distance + 1))
    return None


def candidate_features(
    graph: dict[str, Any],
    ontology: dict[str, Any],
    config: dict[str, Any],
    curated: dict[str, Any],
) -> dict[str, dict[str, dict[str, float]]]:
    node_by_id = {row["id"]: row for row in graph["nodes"]}
    relation_by_id = {row["id"]: row for row in curated["edges"]}
    holdout_edges = [relation_by_id[item] for item in config["holdout_relation_ids"]]
    adjacency = _adjacency(graph, curated, holdout_edges)
    maximum_degree = max((len(neighbors) for neighbors in adjacency.values()), default=1)
    features: dict[str, dict[str, dict[str, float]]] = {}
    for query in config["queries"]:
        source = node_by_id[query["source"]]
        source_tokens = _tokens(
            source["title"],
            source["description"],
            source["tags"],
            query["relation"].replace("_", " "),
            query["question_en"],
            query["question_ko"],
        )
        relation_spec = ontology["relation_types"][query["relation"]]
        query_features: dict[str, dict[str, float]] = {}
        for candidate in query["candidates"]:
            target = node_by_id[candidate["target"]]
            target_tokens = _tokens(target["title"], target["description"], target["tags"])
            distance = _shortest_path(adjacency, query["source"], candidate["target"])
            type_fit = float(
                _type_allowed(source["type"], relation_spec["domain"])
                and _type_allowed(target["type"], relation_spec["range"])
            )
            query_features[candidate["id"]] = {
                "degree": round(len(adjacency[candidate["target"]]) / maximum_degree, 12),
                "lexical": round(_jaccard(source_tokens, target_tokens), 12),
                "path": round(0.0 if distance is None else 1.0 / (1.0 + distance), 12),
                "type_fit": type_fit,
            }
        features[query["id"]] = query_features
    return features


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _strategy_objective(metrics: dict[str, Any], order: list[str]) -> tuple[float, ...]:
    values = {
        "precision": float(metrics["precision"]),
        "mrr_realistic": float(metrics["mrr_realistic"]),
        "ndcg_at_k": float(metrics["ndcg_at_k"]),
        "negative_brier_score": -float(metrics["brier_score"]),
        "negative_nonzero_weight_count": -float(metrics["nonzero_weight_count"]),
    }
    try:
        return tuple(values[name] for name in order)
    except KeyError as error:
        raise ValueError(f"unsupported strategy objective: {error.args[0]}") from error


def evaluate_strategy(
    strategy: dict[str, Any],
    config: dict[str, Any],
    features: dict[str, dict[str, dict[str, float]]],
) -> dict[str, Any]:
    top_k = int(config["budget"]["ranking_k"])
    decision_k = int(config["budget"]["decision_k"])
    threshold = float(strategy["threshold"])
    weights = strategy["weights"]
    query_rows: list[dict[str, Any]] = []
    true_positive = false_positive = false_negative = 0
    covered_queries = 0
    reciprocal_ranks: list[float] = []
    hits_at_1 = hits_at_k = 0
    ndcg_values: list[float] = []
    semantic_numerator = 0
    brier_total = 0.0
    brier_count = 0
    for query in config["queries"]:
        ranked = []
        for candidate in query["candidates"]:
            feature_row = features[query["id"]][candidate["id"]]
            score = sum(float(weights[name]) * feature_row[name] for name in weights)
            score = round(min(1.0, max(0.0, score)), 12)
            relevant = bool(candidate["relevant"])
            brier_total += (score - float(relevant)) ** 2
            brier_count += 1
            ranked.append(
                {
                    "candidate_id": candidate["id"],
                    "target": candidate["target"],
                    "relevant": relevant,
                    "score": score,
                    "features": feature_row,
                }
            )
        ranked.sort(key=lambda row: (-row["score"], row["candidate_id"]))
        selected = [row for row in ranked[:decision_k] if row["score"] >= threshold]
        selected_ids = {row["candidate_id"] for row in selected}
        relevant_rows = [row for row in ranked if row["relevant"]]
        relevant_ids = {row["candidate_id"] for row in relevant_rows}
        true_positive += len(selected_ids & relevant_ids)
        false_positive += len(selected_ids - relevant_ids)
        false_negative += len(relevant_ids - selected_ids)
        covered_queries += int(bool(selected))
        relevant_score = relevant_rows[0]["score"]
        optimistic_rank = 1 + sum(row["score"] > relevant_score for row in ranked)
        pessimistic_rank = sum(row["score"] >= relevant_score for row in ranked)
        realistic_rank = (optimistic_rank + pessimistic_rank) / 2.0
        reciprocal_ranks.append(1.0 / realistic_rank)
        rank_position = ranked.index(relevant_rows[0]) + 1
        hits_at_1 += int(rank_position <= 1)
        hits_at_k += int(rank_position <= top_k)
        ndcg_values.append(1.0 / math.log2(rank_position + 1) if rank_position <= top_k else 0.0)
        semantic_numerator += sum(int(row["features"]["type_fit"] == 1.0) for row in ranked[:top_k])
        query_rows.append(
            {
                "id": query["id"],
                "selected": sorted(selected_ids),
                "realistic_gold_rank": round(realistic_rank, 12),
                "ranking": ranked,
            }
        )
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    f1 = _safe_ratio(2.0 * precision * recall, precision + recall)
    query_count = len(config["queries"])
    metrics = {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "selected": true_positive + false_positive,
        "precision": round(precision, 12),
        "recall": round(recall, 12),
        "f1": round(f1, 12),
        "coverage": round(_safe_ratio(covered_queries, query_count), 12),
        "mrr_realistic": round(sum(reciprocal_ranks) / query_count, 12),
        "hits_at_1": round(_safe_ratio(hits_at_1, query_count), 12),
        "hits_at_k": round(_safe_ratio(hits_at_k, query_count), 12),
        "ndcg_at_k": round(sum(ndcg_values) / query_count, 12),
        "brier_score": round(_safe_ratio(brier_total, brier_count), 12),
        "semantic_at_k": round(_safe_ratio(semantic_numerator, top_k * query_count), 12),
        "nonzero_weight_count": sum(float(value) != 0.0 for value in weights.values()),
    }
    return {
        "strategy_id": strategy["id"],
        "description": strategy["description"],
        "threshold": threshold,
        "weights": weights,
        "metrics": metrics,
        "queries": query_rows,
    }


def run_strategy_search(
    config: dict[str, Any], features: dict[str, dict[str, dict[str, float]]]
) -> tuple[list[dict[str, Any]], str]:
    floors = config["selection_rule"]
    objective_order = floors["strict_improvement_order"]
    trials: list[dict[str, Any]] = []
    best: dict[str, Any] | None = None
    for index, strategy in enumerate(config["strategies"]):
        trial = evaluate_strategy(strategy, config, features)
        metrics = trial["metrics"]
        eligible = (
            metrics["recall"] >= floors["recall_floor"]
            and metrics["coverage"] >= floors["coverage_floor"]
            and metrics["semantic_at_k"] >= floors["semantic_at_k_floor"]
        )
        objective = _strategy_objective(metrics, objective_order)
        if index == 0:
            decision = "baseline"
            reason = "Baseline recorded before any mutation."
            if eligible:
                best = trial
        elif not eligible:
            decision = "discard"
            reason = "Failed one or more frozen recall, coverage, or Sem@K constraints."
        elif best is None or objective > _strategy_objective(best["metrics"], objective_order):
            decision = "keep"
            reason = "Strict lexicographic improvement under all frozen constraints."
            best = trial
        else:
            decision = "discard"
            reason = "Tie or regression against the current kept strategy."
        trial["eligible"] = eligible
        trial["decision"] = decision
        trial["decision_reason"] = reason
        trial["objective"] = [round(value, 12) for value in objective]
        trials.append(trial)
    if best is None:
        raise ValueError("no strategy satisfied the frozen selection constraints")
    return trials, best["strategy_id"]


def _graph_summary(
    graph: dict[str, Any], ontology: dict[str, Any], curated: dict[str, Any]
) -> dict[str, Any]:
    method_relations = [
        spec for spec in ontology["relation_types"].values() if spec["layer"] == "methods"
    ]
    game_relations = [
        spec for spec in ontology["relation_types"].values() if spec["layer"] == "game-state"
    ]
    mapped_game_relations = [row for row in game_relations if row["validator_predicate"]]
    cq_rows = competency_question_results(graph, ontology, curated)
    return {
        "nodes": len(graph["nodes"]),
        "reference_edges": len(graph["edges"]),
        "curated_typed_edges": len(curated["edges"]),
        "declared_node_types": len(ontology["node_types"]),
        "method_relation_types": len(method_relations),
        "game_state_relation_types": len(game_relations),
        "encoded_relation_coverage": {
            "mapped": len(mapped_game_relations),
            "eligible": len(game_relations),
            "ratio": round(_safe_ratio(len(mapped_game_relations), len(game_relations)), 12),
            "interpretation": "construction invariant, not semantic completeness",
        },
        "competency_questions": cq_rows,
        "competency_question_coverage": round(
            _safe_ratio(sum(row["pass"] for row in cq_rows), len(cq_rows)), 12
        ),
    }


def _input_receipts(root: Path, config: dict[str, Any]) -> dict[str, str]:
    paths = {
        "claim_ledger": root / "research/claim-ledger.yaml",
        "config": root / "configs/kg-ontology-simulation.json",
        "ontology": root / config["inputs"]["ontology"],
        "curated_relations": root / config["inputs"]["curated_relations"],
        "sqlite_schema": root / config["inputs"]["sqlite_schema"],
        "simulator": Path(__file__),
        "source_ledger": root / "research/source-ledger.yaml",
    }
    return {name: sha256_path(path) for name, path in sorted(paths.items())}


def _claim_ledger_records(text: str) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    current_id: str | None = None
    for line in text.replace("\r\n", "\n").splitlines():
        if line.startswith("  - id: "):
            current_id = line.removeprefix("  - id: ").strip()
            if current_id in records:
                raise ValueError(f"duplicate claim ledger ID: {current_id}")
            records[current_id] = []
        elif current_id is not None:
            records[current_id].append(line)
    return records


def _claim_field(lines: list[str], key: str) -> str | list[str] | None:
    prefix = f"    {key}:"
    for index, line in enumerate(lines):
        if not line.startswith(prefix):
            continue
        inline = line.removeprefix(prefix).strip()
        if inline == "[]":
            return []
        if inline and inline not in {">", ">-", "|", "|-"}:
            return inline
        values = []
        for following in lines[index + 1 :]:
            if following.startswith("      - "):
                values.append(following.removeprefix("      - ").strip())
            elif following.startswith("    ") and not following.startswith("      "):
                break
        return values
    return None


def validate_claim_boundary(claim_ledger: str) -> None:
    records = _claim_ledger_records(claim_ledger)
    artifact = "research/simulation/kg-ontology/latest/evaluation-matrix.json"
    for claim_id in EXCLUDED_RESULT_CLAIMS:
        if claim_id not in records:
            raise ValueError(f"claim ledger result missing: {claim_id}")
        record = records[claim_id]
        if _claim_field(record, "status") != "TODO-RESULT":
            raise ValueError(f"result claim status drift: {claim_id}")
        evidence = _claim_field(record, "evidence")
        if not isinstance(evidence, list):
            raise TypeError(f"result claim evidence is not a list: {claim_id}")
        if artifact in evidence:
            raise ValueError(f"simulation promoted as result evidence: {claim_id}")
    c4 = records["C-RESULT-004"]
    non_supporting = _claim_field(c4, "non_supporting_artifacts")
    if not isinstance(non_supporting, list) or artifact not in non_supporting:
        raise ValueError("C-RESULT-004 non-supporting-artifact boundary drift")
    c4_text = "\n".join(c4)
    for phrase in ("does not execute", "cannot", "promote this claim"):
        if phrase not in c4_text:
            raise ValueError("C-RESULT-004 exclusion reason drift")


def build_evaluation(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_json(root / "configs/kg-ontology-simulation.json")
    ontology = load_json(root / config["inputs"]["ontology"])
    curated = load_json(root / config["inputs"]["curated_relations"])
    claim_ledger = (root / "research/claim-ledger.yaml").read_text(encoding="utf-8")
    validate_claim_boundary(claim_ledger)
    graph = build_okf_graph(root / config["inputs"]["knowledge_root"], root)
    errors = validate_graph(graph, ontology, curated, root)
    if errors:
        raise ValueError("ontology/graph conformance failed: " + "; ".join(errors))
    if tuple(config["scope"]["not_evidence_for"][-5:]) != EXCLUDED_RESULT_CLAIMS:
        raise ValueError("C-RESULT exclusion contract drift")
    node_ids = {row["id"] for row in graph["nodes"]}
    validate_benchmark_config(config, curated, node_ids)
    features = candidate_features(graph, ontology, config, curated)
    trials, winner_id = run_strategy_search(config, features)
    winner = next(row for row in trials if row["strategy_id"] == winner_id)
    graph_summary = _graph_summary(graph, ontology, curated)
    if graph_summary["competency_question_coverage"] != 1.0:
        raise ValueError("competency-question coverage is incomplete")
    matrix = {
        "schema_version": SCHEMA_VERSION,
        "simulation_id": SIMULATION_ID,
        "status": "PASS",
        "scope": config["scope"],
        "terminology": {
            "graph_store": "SQLite property-graph mirror of repository-local OKF method atoms",
            "ontology": "closed application ontology registry; not OWL or SHACL",
            "proposal": "candidate typed link in an authored closed-world holdout",
            "precision": "TP / (TP + FP) over selected heldout-link candidates",
            "recall": "TP / (TP + FN) over one frozen relevant link per query",
            "semantic_at_k": "domain/range-conforming candidates among the top K",
            "keep": "offline strategy retained after strict constrained improvement; no Git reset",
        },
        "zero_denominator_policy": "return 0.0 and retain the explicit count",
        "input_receipts": _input_receipts(root, config),
        "graph": graph_summary,
        "ontology_violations": 0,
        "budget": config["budget"],
        "selection_rule": config["selection_rule"],
        "trials": trials,
        "winner": {
            "strategy_id": winner_id,
            "metrics": winner["metrics"],
            "top_proposals": [
                {
                    "query_id": query["id"],
                    "candidate_id": query["ranking"][0]["candidate_id"],
                    "target": query["ranking"][0]["target"],
                    "score": query["ranking"][0]["score"],
                    "relevant": query["ranking"][0]["relevant"],
                }
                for query in winner["queries"]
            ],
        },
        "database": {
            "schema": config["inputs"]["sqlite_schema"],
            "default_artifact": DEFAULT_DATABASE.as_posix(),
            "tracked": False,
            "reason": "SQLite bytes are runtime output; deterministic JSON/SVG/TeX receipts are tracked.",
        },
    }
    context = {
        "config": config,
        "ontology": ontology,
        "curated": curated,
        "graph": graph,
        "features": features,
    }
    return matrix, context


def render_markdown(matrix: dict[str, Any]) -> str:
    graph = matrix["graph"]
    winner = matrix["winner"]
    lines = [
        f"# {matrix['simulation_id']} — KG/ontology proposal evaluation",
        "",
        "> **[SIMULATED · ENGINEERING ONLY]** This is an authored closed-world link-holdout",
        "> benchmark. It is not runtime retrieval, semantic completeness, player evidence, or a",
        "> result for C-RESULT-001 through C-RESULT-005.",
        "",
        "## Exact terms and equations",
        "",
        "For query set $Q$, selected links $S_q$, and frozen relevant links $G_q$:",
        "",
        "$$TP=\\sum_q|S_q\\cap G_q|,\\quad FP=\\sum_q|S_q\\setminus G_q|,\\quad FN=\\sum_q|G_q\\setminus S_q|.$$",
        "",
        "$$P=\\frac{TP}{TP+FP},\\quad R=\\frac{TP}{TP+FN},\\quad F_1=\\frac{2PR}{P+R}.$$",
        "",
        "With realistic tie rank $r_q=(r_q^{opt}+r_q^{pess})/2$:",
        "",
        "$$\\mathrm{MRR}=|Q|^{-1}\\sum_q r_q^{-1},\\qquad \\mathrm{BS}=N^{-1}\\sum_i(s_i-y_i)^2.$$",
        "",
        (
            "$$\\mathrm{Sem}@K=(K|Q|)^{-1}\\sum_q\\sum_{i=1}^{K}"
            "I[\\mathrm{domain/range\\ valid}_{qi}].$$"
        ),
        "",
        (
            "A zero denominator returns `0.0` while the raw count remains present. MRR uses the "
            "average of optimistic and pessimistic ranks for ties. The Brier score treats the "
            "bounded strategy score as a diagnostic confidence, not a calibrated probability claim."
        ),
        "",
        "## Graph and ontology conformance",
        "",
        "| Item | Value | Interpretation |",
        "|---|---:|---|",
        f"| OKF nodes | {graph['nodes']} | repository-local method atoms |",
        f"| Reference edges | {graph['reference_edges']} | Markdown links |",
        f"| Curated typed edges | {graph['curated_typed_edges']} | reviewed relation overlay |",
        f"| Declared node types | {graph['declared_node_types']} | methods + game-state vocabulary |",
        f"| Ontology violations | {matrix['ontology_violations']} | exact structural/domain/range checks |",
        f"| Competency-query coverage | {graph['competency_question_coverage']:.3f} | construction check |",
        (
            "| Encoded relation coverage | "
            f"{graph['encoded_relation_coverage']['mapped']}/"
            f"{graph['encoded_relation_coverage']['eligible']} | construction invariant; "
            "not semantic completeness |"
        ),
        "",
        "## Frozen strategy trials",
        "",
        (
            "| Strategy | Decision | Eligible | Precision | Recall | F1 | Coverage | MRR | Hits@1 | "
            "nDCG@3 | Brier | Sem@3 |"
        ),
        "|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for trial in matrix["trials"]:
        metrics = trial["metrics"]
        lines.append(
            f"| `{trial['strategy_id']}` | {trial['decision']} | "
            f"{'yes' if trial['eligible'] else 'no'} | {metrics['precision']:.3f} | "
            f"{metrics['recall']:.3f} | {metrics['f1']:.3f} | "
            f"{metrics['coverage']:.3f} | {metrics['mrr_realistic']:.3f} | "
            f"{metrics['hits_at_1']:.3f} | {metrics['ndcg_at_k']:.3f} | "
            f"{metrics['brier_score']:.3f} | {metrics['semantic_at_k']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Selected strategy",
            "",
            f"Winner: `{winner['strategy_id']}`.",
            "",
            "| Query | Top proposed target | Score | Frozen relevance |",
            "|---|---|---:|:---:|",
        ]
    )
    for proposal in winner["top_proposals"]:
        lines.append(
            f"| `{proposal['query_id']}` | `{proposal['target']}` | "
            f"{proposal['score']:.3f} | {'yes' if proposal['relevant'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            (
                "The benchmark has six authored queries, five candidates per query, and exactly one "
                "held-out relevant relation per query. Unregistered candidates are closed-world "
                "negatives only for this engineering battery. The same authored graph supplies "
                "features and labels, so this evaluates reproducible link recovery under the encoded "
                "ontology, not independent semantic truth or user usefulness."
            ),
            "",
            (
                "The SQLite file is a generated property-graph mirror for inspection. It does not "
                "replace the sibling Graphify navigation graph, the Python `WorldState`, the hard "
                "validator, or any Godot authority boundary."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def render_trials_tsv(matrix: dict[str, Any]) -> str:
    columns = [
        "strategy_id",
        "decision",
        "eligible",
        "precision",
        "recall",
        "f1",
        "coverage",
        "mrr_realistic",
        "hits_at_1",
        "hits_at_k",
        "ndcg_at_k",
        "brier_score",
        "semantic_at_k",
        "nonzero_weight_count",
    ]
    lines = ["\t".join(columns)]
    for trial in matrix["trials"]:
        metrics = trial["metrics"]
        row: dict[str, Any] = {
            "strategy_id": trial["strategy_id"],
            "decision": trial["decision"],
            "eligible": str(trial["eligible"]).lower(),
            **metrics,
        }
        lines.append("\t".join(str(row[column]) for column in columns))
    return "\n".join(lines) + "\n"


def build_recommendations(matrix: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "simulation_id": SIMULATION_ID,
        "scope": "engineering-only typed-link proposals",
        "winner": matrix["winner"],
        "implemented_improvements": [
            {
                "priority": 1,
                "proposal": "Keep Graphify navigation and the typed OKF method graph as separate layers.",
                "receipt": "knowledge/graphify-out/okf-links.json",
            },
            {
                "priority": 2,
                "proposal": "Validate node types, relation vocabulary, endpoints, domain/range, duplicates, and self-edges before export.",
                "receipt": "knowledge/ontology/trace-rpg-ontology.json",
            },
            {
                "priority": 3,
                "proposal": "Materialize a normalized SQLite property-graph mirror with source hashes and foreign keys.",
                "receipt": "knowledge/ontology/knowledge-graph-schema.sql",
            },
            {
                "priority": 4,
                "proposal": "Gate link-proposal strategies with recall, coverage, and Sem@K floors before precision ratcheting.",
                "receipt": "configs/kg-ontology-simulation.json",
            },
            {
                "priority": 5,
                "proposal": "Track exact formulas and deterministic JSON, Markdown, TSV, SVG, and TeX outputs.",
                "receipt": "research/simulation/kg-ontology/latest/evaluation-matrix.json",
            },
        ],
        "deferred_improvements": [
            {
                "priority": 1,
                "proposal": "Add a separately generated claim/evidence overlay from research/claim-ledger.yaml.",
                "reason": "Keep epistemic status separate from document links and require an explicit promotion design.",
            },
            {
                "priority": 2,
                "proposal": "Compile a versioned runtime domain graph into existing WorldState inputs.",
                "reason": "Runtime retrieval is not implemented and must remain non-authoritative until independently evaluated.",
            },
            {
                "priority": 3,
                "proposal": "Add RDF/SHACL interchange only after the closed ontology stabilizes.",
                "reason": "The current stdlib validator is dependency-light and does not claim SHACL conformance.",
            },
            {
                "priority": 4,
                "proposal": "Evaluate novel-link usefulness with independent annotators and open-world negatives.",
                "reason": "The authored closed-world holdout cannot establish semantic truth or human usefulness.",
            },
        ],
        "excluded_claims": list(EXCLUDED_RESULT_CLAIMS),
    }


def render_svg(matrix: dict[str, Any]) -> str:
    width = 1480
    row_height = 74
    height = 390 + row_height * len(matrix["trials"])
    graph = matrix["graph"]
    winner_id = matrix["winner"]["strategy_id"]
    colors = {
        "background": "#F6F2E8",
        "ink": "#18231D",
        "muted": "#5D6B63",
        "line": "#C9C5B8",
        "baseline": "#A78BFA",
        "keep": "#2E8B57",
        "discard": "#B8B5AA",
        "winner": "#F0A43A",
    }
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" '
            'aria-labelledby="title description">'
        ),
        '<title id="title">TRACE-RPG KG ontology simulation evaluation matrix</title>',
        '<desc id="description">Deterministic engineering-only comparison of seven typed-link proposal strategies.</desc>',
        f'<rect width="{width}" height="{height}" fill="{colors["background"]}"/>',
        (
            "<style>text{font-family:Arial,sans-serif;fill:#18231D}.title{font-size:34px;font-weight:700}"
            ".sub{font-size:17px;fill:#5D6B63}.head{font-size:15px;font-weight:700}"
            ".cell{font-size:15px}.small{font-size:13px;fill:#5D6B63}</style>"
        ),
        '<text id="heading" x="56" y="66" class="title">[SIMULATED] Typed-link proposal ratchet</text>',
        '<text x="56" y="98" class="sub">Authored closed-world holdout · engineering only · excludes C-RESULT-001…005</text>',
        f'<rect x="56" y="126" width="1368" height="112" rx="12" fill="#FFFFFF" stroke="{colors["line"]}"/>',
        f'<text x="84" y="164" class="head">{graph["nodes"]} OKF nodes</text>',
        f'<text x="314" y="164" class="head">{graph["reference_edges"]} reference edges</text>',
        f'<text x="586" y="164" class="head">{graph["curated_typed_edges"]} typed edges</text>',
        f'<text x="814" y="164" class="head">CQ {graph["competency_question_coverage"]:.0%}</text>',
        f'<text x="1002" y="164" class="head">ontology violations {matrix["ontology_violations"]}</text>',
        '<text x="84" y="204" class="small">Precision is optimized only after recall, coverage, and Sem@3 constraints pass.</text>',
        '<text x="56" y="282" class="head">Strategy</text>',
        '<text x="590" y="282" class="head">Decision</text>',
        '<text x="742" y="282" class="head">Precision</text>',
        '<text x="882" y="282" class="head">Recall</text>',
        '<text x="1002" y="282" class="head">MRR</text>',
        '<text x="1118" y="282" class="head">Brier ↓</text>',
        '<text x="1254" y="282" class="head">Sem@3</text>',
    ]
    y = 306
    for trial in matrix["trials"]:
        metrics = trial["metrics"]
        decision = trial["decision"]
        fill = colors[decision]
        if trial["strategy_id"] == winner_id:
            fill = colors["winner"]
        parts.extend(
            [
                f'<rect x="56" y="{y}" width="1368" height="58" rx="9" fill="#FFFFFF" stroke="{colors["line"]}"/>',
                f'<rect x="56" y="{y}" width="10" height="58" rx="5" fill="{fill}"/>',
                f'<text x="84" y="{y + 25}" class="cell">{html.escape(trial["strategy_id"])}</text>',
                f'<text x="84" y="{y + 45}" class="small">{html.escape(trial["description"])}</text>',
                f'<text x="590" y="{y + 35}" class="cell">{decision}{" · winner" if trial["strategy_id"] == winner_id else ""}</text>',
                f'<text x="742" y="{y + 35}" class="cell">{metrics["precision"]:.3f}</text>',
                f'<text x="882" y="{y + 35}" class="cell">{metrics["recall"]:.3f}</text>',
                f'<text x="1002" y="{y + 35}" class="cell">{metrics["mrr_realistic"]:.3f}</text>',
                f'<text x="1118" y="{y + 35}" class="cell">{metrics["brier_score"]:.3f}</text>',
                f'<text x="1254" y="{y + 35}" class="cell">{metrics["semantic_at_k"]:.3f}</text>',
            ]
        )
        y += row_height
    parts.extend(
        [
            f'<line x1="56" y1="{height - 66}" x2="1424" y2="{height - 66}" stroke="{colors["line"]}"/>',
            f'<text x="56" y="{height - 34}" class="small">Closed application ontology, not OWL/SHACL · link recovery, not runtime KG efficacy</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts) + "\n"


STRATEGY_TEX_LABELS = {"S2-typed-lexical-loose": "S2 typed-lexical"}


def _strategy_tex_label(strategy_id: str) -> str:
    """Plain table label for a strategy id; unknown ids fall back to the escaped id."""
    return STRATEGY_TEX_LABELS.get(strategy_id, strategy_id.replace("_", "\\_"))


def render_paper_tex(matrix: dict[str, Any], *, korean: bool) -> str:
    baseline = matrix["trials"][0]["metrics"]
    winner = matrix["winner"]["metrics"]
    graph = matrix["graph"]
    winner_name = _strategy_tex_label(matrix["winner"]["strategy_id"])
    if korean:
        caption = "동결된 타입 링크 holdout에서의 시뮬레이션 전용 제안 전략 평가"
        boundary = (
            "\\noindent\\textbf{범위.} 이 표는 설계된 closed-world 링크 복원 결과이며 "
            "런타임 KG 검색, 의미 완전성, 장기 모순 감소 또는 어떤 효능 주장의 근거도 아니다."
        )
        labels = ("전략", "정밀도", "재현율", "MRR", "Brier", "Sem@3")
    else:
        caption = "Simulation-only proposal-strategy evaluation on a frozen typed-link holdout"
        boundary = (
            "\\noindent\\textbf{Scope.} This table reports authored closed-world link recovery, "
            "not runtime KG retrieval, semantic completeness, long-horizon contradiction reduction, "
            "or evidence for any efficacy claim."
        )
        labels = ("Strategy", "Precision", "Recall", "MRR", "Brier", "Sem@3")
    return "\n".join(
        [
            "% Generated by scripts/run_kg_ontology_simulation.py; do not hand-edit.",
            "\\begin{table}[t]",
            "\\centering",
            "\\small",
            f"\\caption{{{caption}}}",
            "\\label{tab:kg-ontology-simulation}",
            "\\begin{tabular}{lrrrrr}",
            "\\toprule",
            " & ".join(labels) + " \\\\",
            "\\midrule",
            (
                f"S0 degree baseline & {baseline['precision']:.3f} & {baseline['recall']:.3f} & "
                f"{baseline['mrr_realistic']:.3f} & {baseline['brier_score']:.3f} & "
                f"{baseline['semantic_at_k']:.3f} \\\\"
            ),
            (
                f"{winner_name} & "
                f"{winner['precision']:.3f} & {winner['recall']:.3f} & "
                f"{winner['mrr_realistic']:.3f} & {winner['brier_score']:.3f} & "
                f"{winner['semantic_at_k']:.3f} \\\\"
            ),
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
            boundary,
            (
                f"\\noindent The deterministic methods graph contains {graph['nodes']} graph nodes, "
                f"{graph['reference_edges']} reference edges, and "
                f"{graph['curated_typed_edges']} curated typed edges; all ontology checks pass."
                if not korean
                else f"\\noindent 결정론적 방법론 그래프는 graph node {graph['nodes']}개, "
                f"reference edge {graph['reference_edges']}개, curated typed edge "
                f"{graph['curated_typed_edges']}개를 포함하며 온톨로지 검사를 모두 통과한다."
            ),
            "",
        ]
    )


def _build_sqlite_file(
    root: Path,
    database_path: Path,
    matrix: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, int]:
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        schema_path = root / context["config"]["inputs"]["sqlite_schema"]
        connection.executescript(schema_path.read_text(encoding="utf-8"))
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "simulation_id": SIMULATION_ID,
            "graph_id": context["graph"]["graph_id"],
            "ontology_id": context["ontology"]["ontology_id"],
            "winner_strategy_id": matrix["winner"]["strategy_id"],
            **{f"sha256_{key}": value for key, value in matrix["input_receipts"].items()},
        }
        connection.executemany(
            "INSERT INTO metadata(key, value) VALUES (?, ?)", sorted(metadata.items())
        )
        connection.executemany(
            "INSERT INTO node_type(id) VALUES (?)",
            [(item,) for item in sorted(context["ontology"]["node_types"])],
        )
        relation_rows = []
        for relation, spec in sorted(context["ontology"]["relation_types"].items()):
            relation_rows.append(
                (
                    relation,
                    spec["layer"],
                    json.dumps(spec["domain"], ensure_ascii=False, separators=(",", ":")),
                    json.dumps(spec["range"], ensure_ascii=False, separators=(",", ":")),
                    spec["validator_predicate"],
                )
            )
        connection.executemany(
            "INSERT INTO relation_type(id, layer, domain_json, range_json, validator_predicate) "
            "VALUES (?, ?, ?, ?, ?)",
            relation_rows,
        )
        connection.executemany(
            "INSERT INTO node(id, type, title, description, tags_json, source_path, sha256) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["id"],
                    row["type"],
                    row["title"],
                    row["description"],
                    json.dumps(row["tags"], ensure_ascii=False, separators=(",", ":")),
                    row["source_path"],
                    row["sha256"],
                )
                for row in context["graph"]["nodes"]
            ],
        )
        edge_rows = [
            (
                row["id"],
                row["source"],
                row["relation"],
                row["target"],
                0,
                row["label"],
                row["evidence"],
            )
            for row in context["graph"]["edges"]
        ] + [
            (
                row["id"],
                row["source"],
                row["relation"],
                row["target"],
                1,
                row["relation"],
                row["evidence"],
            )
            for row in context["curated"]["edges"]
        ]
        connection.executemany(
            "INSERT INTO edge(id, source, relation, target, curated, label, evidence) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            sorted(edge_rows),
        )
        connection.executemany(
            "INSERT INTO competency_question(id, question_en, question_ko, source_type, relation, "
            "target_type, required_sources_json, minimum_answers) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["id"],
                    row["question_en"],
                    row["question_ko"],
                    row["source_type"],
                    row["relation"],
                    row["target_type"],
                    json.dumps(
                        row["required_sources"],
                        ensure_ascii=False,
                        separators=(",", ":"),
                        sort_keys=True,
                    ),
                    row["minimum_answers"],
                )
                for row in context["ontology"]["competency_questions"]
            ],
        )
        connection.executemany(
            "INSERT INTO benchmark_query(id, question_en, question_ko, source, relation, "
            "holdout_relation_id) VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    query["id"],
                    query["question_en"],
                    query["question_ko"],
                    query["source"],
                    query["relation"],
                    query["holdout_relation_id"],
                )
                for query in context["config"]["queries"]
            ],
        )
        candidate_rows = []
        for query in context["config"]["queries"]:
            for candidate in query["candidates"]:
                candidate_rows.append(
                    (
                        query["id"],
                        candidate["id"],
                        candidate["target"],
                        int(candidate["relevant"]),
                    )
                )
        connection.executemany(
            "INSERT INTO benchmark_candidate(query_id, candidate_id, target, relevant) "
            "VALUES (?, ?, ?, ?)",
            sorted(candidate_rows),
        )
        connection.executemany(
            "INSERT INTO strategy_run(strategy_id, decision, precision, recall, f1, coverage, "
            "mrr_realistic, hits_at_1, hits_at_k, ndcg_at_k, brier_score, semantic_at_k, "
            "nonzero_weight_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    trial["strategy_id"],
                    trial["decision"],
                    trial["metrics"]["precision"],
                    trial["metrics"]["recall"],
                    trial["metrics"]["f1"],
                    trial["metrics"]["coverage"],
                    trial["metrics"]["mrr_realistic"],
                    trial["metrics"]["hits_at_1"],
                    trial["metrics"]["hits_at_k"],
                    trial["metrics"]["ndcg_at_k"],
                    trial["metrics"]["brier_score"],
                    trial["metrics"]["semantic_at_k"],
                    trial["metrics"]["nonzero_weight_count"],
                )
                for trial in matrix["trials"]
            ],
        )
        connection.commit()
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_key_errors:
            raise ValueError(
                f"SQLite integrity failure: integrity={integrity}, foreign_keys={foreign_key_errors}"
            )
        tables = (
            "node_type",
            "relation_type",
            "node",
            "edge",
            "competency_question",
            "benchmark_query",
            "benchmark_candidate",
            "strategy_run",
        )
        counts = {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in tables
        }
    finally:
        connection.close()
    return counts


def build_sqlite(
    root: Path,
    database_path: Path,
    matrix: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, int]:
    sqlite_header = b"SQLite format 3\x00"
    if database_path.is_symlink():
        raise ValueError(f"refusing to replace SQLite symlink: {database_path}")
    if database_path.exists():
        if not database_path.is_file():
            raise ValueError(f"SQLite output is not a regular file: {database_path}")
        with database_path.open("rb") as handle:
            header = handle.read(len(sqlite_header))
        if header and header != sqlite_header:
            raise ValueError(f"refusing to replace non-SQLite file: {database_path}")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=database_path.parent,
        prefix=f".{database_path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        os.fchmod(handle.fileno(), 0o644)
    try:
        counts = _build_sqlite_file(root, temporary, matrix, context)
        os.replace(temporary, database_path)
    finally:
        temporary.unlink(missing_ok=True)
    return counts


def build_artifact_payloads(root: Path) -> tuple[dict[Path, bytes], dict[str, Any], dict[str, Any]]:
    matrix, context = build_evaluation(root)
    recommendations = build_recommendations(matrix)
    payloads = {
        TRACKED_OUTPUTS["graph"]: canonical_json(context["graph"]).encode(),
        TRACKED_OUTPUTS["matrix_json"]: canonical_json(matrix).encode(),
        TRACKED_OUTPUTS["matrix_md"]: render_markdown(matrix).encode(),
        TRACKED_OUTPUTS["trials_tsv"]: render_trials_tsv(matrix).encode(),
        TRACKED_OUTPUTS["recommendations"]: canonical_json(recommendations).encode(),
        TRACKED_OUTPUTS["svg"]: render_svg(matrix).encode(),
        TRACKED_OUTPUTS["paper_en"]: render_paper_tex(matrix, korean=False).encode(),
        TRACKED_OUTPUTS["paper_ko"]: render_paper_tex(matrix, korean=True).encode(),
    }
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "simulation_id": SIMULATION_ID,
        "files": [
            {
                "path": path.as_posix(),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
            }
            for path, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix())
        ],
    }
    payloads[TRACKED_OUTPUTS["manifest"]] = canonical_json(manifest).encode()
    return payloads, matrix, context


def write_artifacts(root: Path, payloads: dict[Path, bytes]) -> None:
    for relative, payload in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        atomic_write(root / relative, payload)


def check_artifacts(root: Path, payloads: dict[Path, bytes]) -> list[str]:
    mismatches = []
    for relative, expected in sorted(payloads.items(), key=lambda item: item[0].as_posix()):
        path = root / relative
        if not path.is_file():
            mismatches.append(f"missing: {relative}")
        elif path.read_bytes() != expected:
            mismatches.append(f"stale: {relative}")
    return mismatches
