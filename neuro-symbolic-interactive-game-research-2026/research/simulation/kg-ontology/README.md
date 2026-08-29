# SL-KG-ONTOLOGY-SIM-001

A separate, deterministic **simulation-only** lane for the repository-local methods graph.

## What it is

- Input: OKF atoms under `knowledge/`, the closed application ontology, 24 reviewed typed relations,
  and a frozen six-query × five-candidate link holdout.
- Search: seven fixed strategies, degree baseline first, 30 candidate scores per strategy and 210
  total, strict keep/discard ratchet after recall, coverage, and `Sem@3` constraints.
- Output: byte-stable JSON, Markdown, TSV, SVG, bilingual TeX, SHA-256 manifest, plus an ignored
  SQLite property-graph mirror with source-scoped competency questions and query/candidate foreign keys.
  SQLite replacement is atomic and refuses symlinks or non-SQLite targets.

## What it is not

It is not the sibling Graphify authority, a runtime domain KG, OWL/SHACL conformance, an independent
semantic oracle, temporal-memory evidence, player evidence, or support for `C-RESULT-001` through
`C-RESULT-005`. The authored graph supplies both the features and closed-world labels. Therefore the
reported precision is a reproducible construction test, not a population estimate.

## Run

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_kg_ontology_simulation.py
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/run_kg_ontology_simulation.py --check
```

`--check` recomputes every tracked artifact in memory and builds a temporary SQLite database for
integrity and foreign-key verification. It fails on stale bytes, unresolved nodes, undeclared types
or relations, domain/range violations, duplicate/self edges, missing evidence paths, aggregate or
required-source competency-query coverage loss, holdout/budget drift, or claim-boundary drift.

## Inputs and outputs

- Config: `configs/kg-ontology-simulation.json`
- Ontology: `knowledge/ontology/trace-rpg-ontology.json`
- Curated overlay: `knowledge/ontology/curated-relations.json`
- SQLite schema: `knowledge/ontology/knowledge-graph-schema.sql`
- Generated packet: `research/simulation/kg-ontology/latest/`
- Generated paper fragments: `paper/latex/generated/kg_ontology_simulation_{en,ko}.tex`
- Runtime database: `research/simulation/kg-ontology/latest/trace-rpg-knowledge.sqlite` (ignored)
