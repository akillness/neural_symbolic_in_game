# Wiki Schema

This vault is the project-scoped persistent wiki for TRACE-RPG. It is the single
llm-wiki and Graphify root for this repository.

## Invariants

1. Treat `raw/` as immutable source of truth.
2. Treat `wiki/`, `index.md`, and `log.md` as LLM-maintained working artifacts.
3. On ingest, update the raw source capture, a source summary page, affected synthesis pages, `index.md`, and `log.md`.
4. On query, read `index.md` first, then relevant wiki pages, then raw sources only if grounding is needed.
5. File durable answers back into `wiki/queries/` or `wiki/reports/`.
6. During lint passes, look for broken links, orphan pages, stale claims, contradictions, and missing page candidates.
7. Classify statements as `verified-primary`, `verified-scope-limited`, `design-assumption`, `thin-evidence`, or `TODO-RESULT`; never silently promote status.
8. Keep tension, engagement, stress, arousal, and flow as separate constructs.
9. Learned model output, retrieval, memory, and affect estimates are non-authoritative; only a validated commit changes canonical game state.
10. Durable project reports must link the source ledger and claim ledger in `../neuro-symbolic-interactive-game-research-2026/research/`.

## Graphify layers

- Detect `graphify --help` before every refresh because the installed command surface may differ from the skill documentation.
- Authoritative full extraction: `graphify-out/graph.json`, refreshed with the supported `update`/`extract` and `cluster-only` commands.
- Structural prompt/output graph: `graphify-out/prompts/graph.json`, rebuilt only by ingest hooks or an explicit migration.
- Never overwrite or merge the authoritative graph with the prompt/output graph.
- Do not create `.graphify/` as a second authoritative layout. A future layout migration requires a recorded versioned plan and successful portability check.
- On any failed refresh, preserve the last authoritative graph and append the failure to `maintenance-log.md`.

## Style

- Prefer markdown with wiki links to real pages in the vault.
- Use kebab-case file names and a single H1 matching the page title.
- Distinguish grounded source notes from higher-level synthesis.
- Preserve citations to page paths, raw source paths, or source URLs.
- Keep the schema short and revise it when repeated drift appears.

## Validation order

1. Read `index.md`.
2. Read the relevant concept/source/report pages.
3. Query or explain the authoritative Graphify graph.
4. Drill into immutable raw sources when a claim needs grounding.
5. File durable answers under `wiki/queries/` or `wiki/reports/` and append `log.md`.
