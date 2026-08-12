# Maintenance Log

- 2026-08-12: Bootstrapped the project-scoped llm-wiki, preserved the five source plans and Scrapling captures, and defined non-mixed Graphify layers. Authoritative graph build pending post-lint refresh.
- 2026-08-12: Migrated hook-generated `.graphify/` prompt/output structure into `graphify-out/prompts/`; removed the obsolete layout so it cannot compete with the authoritative graph.
- 2026-08-12: Wiki lint reached zero broken links; legacy Graphify `update --no-cluster` plus `cluster-only --no-viz` built an authoritative graph with 217 nodes, 186 edges, and 33 communities. A TRACE-RPG query resolved the project/controller nodes.
- 2026-08-12: After the complete web-source ingest, rebuilt to 449 nodes and 44 communities. Renamed the generated Markdown graph report to `.generated.txt` because legacy Graphify emits unresolved Obsidian community links that the wiki linter correctly flags; `graph.json` remains authoritative.
- 2026-08-12: Added policy-oracle, non-authoritative affect, full repair-trace, and primary-paper capture corrections; lint passed and the authoritative graph rebuilt to 454 nodes, 410 edges, and 44 communities. The separate prompt/output graph was not overwritten.
- 2026-08-12: Improvement cycle 1 added semantic JSONL replay, deterministic state-transition recomputation, and episode continuity checks. Wiki lint now excludes Graphify rendering caches while resolving immutable raw-source wikilinks; a hook-created legacy `.graphify/` cache was moved out of the vault to preserve the single authoritative layout.
