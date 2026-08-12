---
name: research-orchestrator
description: Proactively route any TRACE-RPG evidence update, experiment, model comparison, result promotion, manuscript revision, or journal-preparation task through the correct producer-reviewer gates.
allowed-tools: Read Write Edit Bash Grep Glob Agent
---

# TRACE-RPG Research Orchestrator

Use this skill whenever work can affect a factual claim, experimental result, game-state contract, or manuscript conclusion. The purpose is to prevent fast local progress from bypassing provenance, design, or independent-review constraints.

## Workflow

1. Read `harness/ownership.yaml`, `harness/workflows/research-to-journal.md`, and `research/claim-ledger.yaml`.
2. Classify the task as evidence, ontology, protocol, execution, analysis, result promotion, or manuscript work.
3. Name one writer and a different reviewer from `.claude/agents/`.
4. Create `_workspace/{run-id}/manifest.yaml` with input hashes, planned outputs, and stop conditions.
5. Run the smallest upstream gates that can establish prerequisites.
6. Preserve failed artifacts and decisions under `_workspace/gates/`.
7. Update the claim ledger only after the applicable gate passes.

## Hard rules

- Never turn pilot/screening output into confirmatory evidence.
- Never let a learned component mutate canonical game state directly.
- Never strengthen wording beyond the source/evidence status.
- Never let a writer approve its own artifact.
- Never delete failed traces or overwrite raw sources.

## Output

Return the phase, artifacts changed, fresh validation evidence, failed/waived gates, and the next permitted phase. Do not claim completion while a required gate is pending.
