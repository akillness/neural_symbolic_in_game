# Paper and game fact-check and release — 2026-09-06

Status: editorial/engineering verification and production deployment complete; human/efficacy gates remain unproven.

## Evidence and corrections

- The bounded primary-source refresh rechecked S02, S44, S52, S54, S55, and S56 through arXiv, OpenAlex, and Crossref. It does not represent a fresh verification of all 55 references. The retained Stage-5 classification remains 48 VERIFIED and 7 PREPRINT, with 22 historical Semantic Scholar rate-limited lookups. VERIFIED concerns source identity, not support for TRACE-RPG efficacy.
- S44 supports authored world-state transformations and exploratory consistency observations. Its abstract cannot establish that every transaction, audit, or repair mechanism is absent. Both manuscripts now identify those as separate evidence questions.
- S55 supports the limitation of state consistency as a measure of agent behavior. Both manuscripts now describe narrative quality as a separately unmeasured construct.
- The dashboard reference omitted `UNKNOWN_ACTOR` (POLICY) and `NPC_DOES_NOT_KNOW_FACT` (KNOWLEDGE). Its mappings now match the engine's `GATE_BY_CODE`. Composite `DISCLOSURE/QUEST STAGE` events count once in each affected family; unknown families do not create new counters.
- Deployment previously reused an existing ignored Web export and omitted the manuscripts. The release script now rebuilds the game in a disposable copy, packages EN/KO PDFs at `/paper/en.pdf` and `/paper/ko.pdf`, refuses unknown CLI options, and records file sizes portably. The dashboard links both PDFs.
- The project overview's stale 45-reference and 49-check current-state statements are updated to 55 references and 52 engineering checks. Historical reports retain their dated values.

## Verification and limits

The pre-change full suite passed 183 tests and 81 subtests. The release-staging regression passed 3 tests covering stale exports, missing PDFs, and misspelled dry-run arguments. Both revised manuscripts pass `make -C paper/latex check`, at 8 pages each. Final integrated verification and deployment receipts are recorded below when complete.

No participant study, model-ranking result, general safety rate, narrative benefit, or G4/G6 gate is promoted. `C-RESULT-001`–`C-RESULT-005` remain `TODO-RESULT`. Public deployment is an engineering demonstration, not journal submission or confirmatory evidence.

## Canonical evidence

Production: https://sealed-lighthouse-trace-rpg.vercel.app/ — READY deployment
`dpl_2KYaaLu6PWuwaFZ4RxFrFkA6C4RT`; 16 files (10 game + 4 dashboard + 2 PDFs),
53,567,287 bytes, all matching local SHA-256. Papers: `/paper/en.pdf` and `/paper/ko.pdf`.
Full CI-equivalent sequence passes; Pytest 188 tests / 83 subtests; EN/KO 8 pages each.
Production browser start and observer regression pass. One headless pointer-lock diagnostic
is retained, so no zero-error gesture or human G4/G6 claim is made. Mobile page overflow is
absent, but mobile game readability remains unverified. See the
[release receipt](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/factcheck-release-2026-09-06.md).

- [Source ledger](../../../neuro-symbolic-interactive-game-research-2026/research/source-ledger.yaml)
- [Claim ledger](../../../neuro-symbolic-interactive-game-research-2026/research/claim-ledger.yaml)
- [Citation audit](../../../neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/stage-05-citation-verification.json)
- [Release procedure](../../../neuro-symbolic-interactive-game-research-2026/scripts/deploy_vercel_dashboard.sh)

Related: [[wiki/projects/trace-rpg-paper-2026]], [[wiki/concepts/evidence-and-claim-status]], [[wiki/reports/2026-09-03-paper-game-readout-figure-readme-and-reference-recheck]].
