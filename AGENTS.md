# Project Research Contract

This repository is an experimental, bilingual neuro-symbolic game research project.

## Read order

1. Read `llm-wiki/index.md`.
2. Read relevant pages under `llm-wiki/wiki/`.
3. Query `llm-wiki/graphify-out/graph.json` with the installed Graphify CLI when relationships matter.
4. Read raw sources only to resolve evidence conflicts.

## Non-negotiable rules

- Treat `drive-download-20260812T074907Z-1-001/` and `llm-wiki/raw/` as immutable source evidence.
- Never turn `TODO-RESULT`, `[uncertain]`, or an unverified citation into a factual result.
- Separate hard symbolic validity from soft narrative, affect, novelty, and style objectives.
- Commit a game action only after deterministic hard constraints pass.
- Preserve proposal, evidence, validation, repair, commit, model revision, seed, cost, and latency in every experiment trace.
- Keep research runtime and game runtime separate; exchange only versioned JSON contracts and deterministic replays.
- Keep Korean and English claim IDs, table IDs, figure IDs, equations, and numbers aligned.

## Evidence and refresh

- Prefer primary sources and official model cards. Record URL, retrieval date, evidence level, license, and unresolved conflicts.
- Use Scrapling's research-harvest gate before harvesting papers or datasets. Prefer metadata APIs over publisher-page scraping.
- Use `.survey/neuro-symbolic-interactive-game-2026/` for bounded landscape artifacts and `neuro-symbolic-interactive-game-research-2026/research/deep-research/` for structured model records.
- File durable findings into `llm-wiki/wiki/queries/` or `llm-wiki/wiki/reports/`, then update `llm-wiki/index.md` and `llm-wiki/log.md`.
- The authoritative project graph is `llm-wiki/graphify-out/graph.json`. The prompt/output structural graph is `llm-wiki/graphify-out/prompts/graph.json`; never overwrite one with the other.
- The installed Graphify command surface is version-sensitive. Run `graphify --help` before refresh and use `neuro-symbolic-interactive-game-research-2026/scripts/refresh_knowledge.sh`, which detects supported commands.

## Verification gates

Before a paper release, pass: source integrity, citation identity, mathematical domain/unit checks, logic positive/negative fixtures, protocol completeness, leakage checks, deterministic replay, bilingual parity, SVG parsing, tests, and reproducibility metadata. A failed gate is `FIX`, not evidence to delete.

Detailed ownership and workflow rules live in `neuro-symbolic-interactive-game-research-2026/harness/`.

## Experimental game studio

For any work under `neuro-symbolic-interactive-game-research-2026/game-track/` or
`neuro-symbolic-interactive-game-research-2026/_workspace/`, also apply the canonical studio
contract in `neuro-symbolic-interactive-game-research-2026/CLAUDE.md`. That file owns studio lanes,
Godot boundaries, generated-asset provenance, game quality gates, and workspace freshness. The
research rules above remain authoritative and are not duplicated in the studio contract.
