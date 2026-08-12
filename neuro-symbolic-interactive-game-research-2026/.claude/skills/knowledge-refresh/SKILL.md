---
name: knowledge-refresh
description: Refresh and query the TRACE-RPG project llm-wiki and Graphify graph after any durable source, claim, protocol, experiment, or result change; detect tool-version differences before touching graph state.
allowed-tools: Read Write Edit Bash Grep Glob
---

# TRACE-RPG Knowledge Refresh

Use after any durable research change or before answering a project-history question. The project wiki is `../../llm-wiki/` relative to this research package and is distinct from the user's global vault.

## Procedure

1. Read `../../llm-wiki/index.md`, then relevant `wiki/` pages and graph queries.
2. Copy new verbatim sources to `raw/sources/` without mutation and record a checksum.
3. Write compressed atomic concepts, then a dated query/report; update `maintenance-log.md`.
4. Run wiki lint.
5. Inspect `graphify --help` before selecting a command.
6. For the installed legacy surface, refresh authoritative `graphify-out/graph.json` using `graphify update`/`extract` and `cluster-only`. Never write it from prompt/output structural ingestion.
7. Preserve prompt/output structure only in `graphify-out/prompts/graph.json`.
8. Smoke-test a query/path. If refresh fails, retain the prior authoritative graph and log the error.

Do not create both `.graphify/` and `graphify-out/` as competing authoritative stores. A future migration requires a versioned migration record and portable validation before switching layouts.
