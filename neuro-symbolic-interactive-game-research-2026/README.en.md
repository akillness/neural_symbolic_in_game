# TRACE-RPG Research Package 2026

> Status: experimental design and implementation draft. No numeric result has been produced; empirical claims remain locked as `TODO-RESULT`.

TRACE-RPG never writes an LLM proposal directly into canonical game state. Each proposal becomes a typed event and is committed only after an authoritative action-policy oracle, knowledge-graph, quest-policy, reachability, and forbidden-disclosure checks. A failed proposal receives a structured counterexample and a bounded repair opportunity. The research and game-development tracks build independently but interoperate through a versioned, replayable event contract.

## Journal target and evidence bar

The primary candidate is **IEEE Transactions on Games**, whose scope directly covers game AI, player modelling, and game evaluation. **Knowledge-Based Systems** is the method-first alternative; **IEEE Transactions on Affective Computing** becomes relevant only if affect inference is an independently strong contribution; **Entertainment Computing** is an application and user-study alternative. Indexing changes, so SCIE coverage must be rechecked in the Clarivate Master Journal List immediately before submission.

Journal-level claims require a preregistered primary endpoint, pilot-informed prospective power analysis, world- and quest-template holdouts, mixed-effects models, effect sizes with 95% confidence intervals, multiplicity correction, independent human evaluation, failure analysis, and trace-complete reproducibility artifacts.

Detailed venue gate: [`research/journal-targets.md`](research/journal-targets.md)

## Research questions

- RQ1: Does a symbolic commit gate reduce impossible world states and forbidden disclosures across model scales?
- RQ2: Is counterexample/unsat-core repair more sample-efficient than blind retry?
- RQ3: Do graph retrieval and temporal memory improve long-horizon consistency without collapsing narrative diversity?
- RQ4: Can uncertainty-calibrated affect adaptation improve target-curve tracking without regressing hard validity?
- RQ5: Do controller gains replicate across a ten-model screen and a three-model confirmatory stage?

## Quick start

```bash
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
uv run python scripts/validate_harness.py
uv run python examples/headless_demo.py
uv run python examples/recorded_experiment.py
```

This repository currently runs the local policy validator, bounded repair/fallback, full-history trace hash, semantic JSONL replay, and a network-free recorded-response experiment adapter. The offline runner preserves model revision, seed, token counts, provider/runner latency, failures, and commit status in schema-validated JSONL. Real ten-model API/local-serving adapters, MLflow/energy telemetry, Godot/Unity transport, and the human study are specified but not implemented.

## Layout

| Path | Purpose |
|---|---|
| `paper/ko`, `paper/en` | Korean and English drafts sharing claim identifiers |
| `configs/` | SSOT for ten models, treatments, scenarios, and metrics |
| `src/nesy_game/` | Deterministic contracts and minimal validator |
| `game-track/` | Engine-neutral bridge and replay contract |
| `research/` | Immutable sources, Scrapling captures, evidence and claim ledgers |
| `harness/` | Agent roles, workflows, and validation gates |
| `../llm-wiki/` | Project wiki and Graphify knowledge graph |
| `visuals/` | Source SVGs for the manuscript and README |

## Reproducibility boundary

- LLMs/VLMs propose candidates or soft signals; they never constitute canonical world state.
- SMT/rule checking guarantees only encoded constraints. Semantic false negatives are measured separately.
- Synthetic players are stress-test instruments, not evidence of human experience.
- Raw sources and execution traces are immutable, and paper tables must be generated from trace IDs.
- “Open weight” is not treated as a synonym for “open source”; every model retains an explicit license and policy record.

## Execution order

1. Pilot scenario difficulty, validator omission rates, and human-rating variance.
2. Freeze the analysis plan and primary endpoints; determine sample size through power analysis.
3. Screen ten models cheaply and promote three through a preregistered Pareto rule.
4. Run the confirmatory 3-model × 6-system × 3-track experiment and ablations.
5. Admit only independently audited, trace-complete runs into paper results.
