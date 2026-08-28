# Maintenance Log

- 2026-08-28 (second pass, ooo seed `seed-20260828-knowledge-layer-refresh`): closed two of the
  three deferred drift items. `wiki/projects/trace-rpg-paper-2026.md` now carries the rho(a,E)
  method, the 45-reference Stage-5 state, the executed live pilot with its regime dependence, and
  the unresolved C-RESULT-003 promotion contradiction; `wiki/concepts/trace-rpg-controller.md` now
  formalizes rho and the guided/oracle/irreparable taxonomy. `claim-ledger.yaml` C-PILOT-002 was
  corrected in the earlier pass. Wiki lint passes at 59 pages.
- 2026-08-28 (correction, supersedes the BLOCKED note below): the authoritative graph IS
  refreshed. The earlier failure was diagnosed to its root cause rather than accepted: Python's
  `ProcessPoolExecutor` probes `os.sysconf("SC_SEM_NSEMS_MAX")` before starting, this sandbox
  denies that call with EPERM, and graphify's AST extraction defaults to a process pool — so the
  rebuild died while `graphify-out/` was writable the whole time. `GRAPHIFY_MAX_WORKERS=1` is
  graphify's own supported single-worker path (it returns before constructing the pool), and
  `scripts/refresh_knowledge.sh` now probes for pool availability and sets it only when the pool
  is genuinely unavailable, so normal machines keep parallel extraction.
  Rebuild result: 627 nodes, 739 edges, 57 communities. Audit of the 654 -> 627 delta: +84 nodes
  across 17 newly indexed files (including the 2026-08-21 and 2026-08-28 reports, which were the
  drift being closed), -4 from dropping `.state/ingest-prompt.json` (agent runtime state that does
  not belong in the authoritative graph), and -107 across 42 shared files concentrated in
  `raw/sources/web/*.md` model cards. That last term is an extractor-version granularity change,
  not content loss: graphify 0.9.51 emits typed nodes (104 `page` + 523 `heading`) where the
  0.8.x-era graph emitted 654 untyped nodes. The separate prompt/output graph under
  `graphify-out/prompts/` was not touched, per llm-wiki/AGENTS.md.
- 2026-08-12: Bootstrapped the project-scoped llm-wiki, preserved the five source plans and Scrapling captures, and defined non-mixed Graphify layers. Authoritative graph build pending post-lint refresh.
- 2026-08-12: Migrated hook-generated `.graphify/` prompt/output structure into `graphify-out/prompts/`; removed the obsolete layout so it cannot compete with the authoritative graph.
- 2026-08-12: Wiki lint reached zero broken links; legacy Graphify `update --no-cluster` plus `cluster-only --no-viz` built an authoritative graph with 217 nodes, 186 edges, and 33 communities. A TRACE-RPG query resolved the project/controller nodes.
- 2026-08-12: After the complete web-source ingest, rebuilt to 449 nodes and 44 communities. Renamed the generated Markdown graph report to `.generated.txt` because legacy Graphify emits unresolved Obsidian community links that the wiki linter correctly flags; `graph.json` remains authoritative.
- 2026-08-12: Added policy-oracle, non-authoritative affect, full repair-trace, and primary-paper capture corrections; lint passed and the authoritative graph rebuilt to 454 nodes, 410 edges, and 44 communities. The separate prompt/output graph was not overwritten.
- 2026-08-12: Improvement cycle 1 added semantic JSONL replay, deterministic state-transition recomputation, and episode continuity checks. Wiki lint now excludes Graphify rendering caches while resolving immutable raw-source wikilinks; a hook-created legacy `.graphify/` cache was moved out of the vault to preserve the single authoritative layout.
- 2026-08-12: Improvement cycle 2 added strict frozen-proposal and assigned-case JSON schemas, a no-coercion recorded-response adapter, classified adapter failures, checksum-required record loading, semantic result/trace cross-link checks, rollback-tested dual-file writes, and manifest-gated treatment-policy summaries. Overall, symbolic-validation, and adapter failures are separate; response-observed latency is explicitly conditional and accompanied by its observed-case count.
