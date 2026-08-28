# Maintenance Log

- 2026-08-28 (second pass, ooo seed `seed-20260828-knowledge-layer-refresh`): closed two of the
  three deferred drift items. `wiki/projects/trace-rpg-paper-2026.md` now carries the rho(a,E)
  method, the 45-reference Stage-5 state, the executed live pilot with its regime dependence, and
  the unresolved C-RESULT-003 promotion contradiction; `wiki/concepts/trace-rpg-controller.md` now
  formalizes rho and the guided/oracle/irreparable taxonomy. `claim-ledger.yaml` C-PILOT-002 was
  corrected in the earlier pass. Wiki lint passes at 59 pages.
- 2026-08-28: authoritative graph refresh attempted and BLOCKED, recorded rather than skipped.
  `scripts/refresh_knowledge.sh` passes its command-surface gate (installed graphifyy 0.9.51 has
  both `update` and `cluster-only`) but `graphify update .` fails with
  `[graphify watch] Rebuild failed: [Errno 1] Operation not permitted` in this sandbox. Probes:
  `graphify-out/` is writable, and `graphify extract . --code-only --max-workers 1` runs cleanly,
  which points at the default multi-worker extraction path rather than at file permissions.
  `--code-only` yields 0 nodes because this vault is markdown (124 doc files skipped), and full
  doc extraction needs an LLM backend plus an API key, which was not authorized for this run.
  `graphify-out/graph.json` therefore stays at its 2026-08-13 build (654 nodes) and still omits the
  2026-08-21 and 2026-08-28 reports. Anyone quoting the graph must treat it as stale until a run
  with a permitted extraction path or an authorized backend refreshes it.

- 2026-08-28: Filed the D-037–D-039 report page, promoted it to the current-track pointer in
  `index.md`, and logged the session in `log.md`. Known deferred drift (not fixed this pass):
  the authoritative `graphify-out/graph.json` still predates the 2026-08-21 and 2026-08-28
  reports, `wiki/projects/trace-rpg-paper-2026.md` still describes the pre-ρ(a,E) 42-reference
  state, and `research/claim-ledger.yaml` C-PILOT-002 still uses the 2-case wording — queued for
  the next research-lane session so the wiki refresh and the claim-ledger rewrite land together.

- 2026-08-12: Bootstrapped the project-scoped llm-wiki, preserved the five source plans and Scrapling captures, and defined non-mixed Graphify layers. Authoritative graph build pending post-lint refresh.
- 2026-08-12: Migrated hook-generated `.graphify/` prompt/output structure into `graphify-out/prompts/`; removed the obsolete layout so it cannot compete with the authoritative graph.
- 2026-08-12: Wiki lint reached zero broken links; legacy Graphify `update --no-cluster` plus `cluster-only --no-viz` built an authoritative graph with 217 nodes, 186 edges, and 33 communities. A TRACE-RPG query resolved the project/controller nodes.
- 2026-08-12: After the complete web-source ingest, rebuilt to 449 nodes and 44 communities. Renamed the generated Markdown graph report to `.generated.txt` because legacy Graphify emits unresolved Obsidian community links that the wiki linter correctly flags; `graph.json` remains authoritative.
- 2026-08-12: Added policy-oracle, non-authoritative affect, full repair-trace, and primary-paper capture corrections; lint passed and the authoritative graph rebuilt to 454 nodes, 410 edges, and 44 communities. The separate prompt/output graph was not overwritten.
- 2026-08-12: Improvement cycle 1 added semantic JSONL replay, deterministic state-transition recomputation, and episode continuity checks. Wiki lint now excludes Graphify rendering caches while resolving immutable raw-source wikilinks; a hook-created legacy `.graphify/` cache was moved out of the vault to preserve the single authoritative layout.
- 2026-08-12: Improvement cycle 2 added strict frozen-proposal and assigned-case JSON schemas, a no-coercion recorded-response adapter, classified adapter failures, checksum-required record loading, semantic result/trace cross-link checks, rollback-tested dual-file writes, and manifest-gated treatment-policy summaries. Overall, symbolic-validation, and adapter failures are separate; response-observed latency is explicitly conditional and accompanied by its observed-case count.
