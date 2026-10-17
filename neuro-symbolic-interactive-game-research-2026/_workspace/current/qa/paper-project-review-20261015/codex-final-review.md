**Verdict: FIX.** All 47 required artifacts were inspected completely across this Codex review and three bounded Codex review slices. Every file matches its manifest byte count and SHA-256. The bundle also matches **949,812 bytes** and SHA-256 `0c8da99ba60917dfc2c6b4d5d87f22a209753312c9a37f55f28947eb28d2b06a`.

The three original findings are addressed, but the broader review found a remaining semantic-replay defect and incomplete regression coverage. No files were changed; no suites, experiments, model calls, Git operations, builds, deployments, or credential/configuration access were performed.

**Findings, ordered by severity**

1. **Medium — Replay still accepts duplicate or causally impossible result records.**  
   [npc_goal.py:1885](/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/src/nesy_game/npc_goal.py:1885) checks each result independently against a decision collected into a lookup table at lines 1812–1813. It neither tracks consumed action IDs nor requires the decision to precede its result.

   Static counterexamples, after recomputing checksums and contiguous sequence/delivery fields:

   - `request → decision → APPLIED result → duplicate APPLIED result`
   - `request → APPLIED result → decision`

   Both satisfy the inspected replay checks. Request/decision uniqueness at lines 1808–1811 does not cover results. The live controller instead requires an issued action at lines 1312–1319, deduplicates results at 1352–1359, and appends accepted results at 1424.

   Replay therefore accepts histories the controller cannot produce. Add causal ordering and consumed-action checks, with matching positive and rehashed negative fixtures. This is a **static source finding**, not an executed reproduction or evidence of duplicate world mutation.

2. **Medium — A replay-report rejection test performs no verification.**  
   [test_npc_evidence_contract.py:317](/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/tests/test_npc_evidence_contract.py:317) defines mutations for arbitrary counts, omitted/duplicated rows, and lane swaps through line 336, but never invokes the callback or asserts rejection. The test passes without exercising those controls.

   The validator contains corresponding rejection logic at `scripts/validate_npc_goal_evidence.py:1313–1358`; this finding does **not** establish that current004 is malformed. Restore the mutation loop and assertions against a valid baseline. Also correct the screening baseline construction at test lines 223–242: `zip(cases, assignments)` produces only 12 records for 72 assignments, weakening the publication-negative tests at lines 373–400.

**Recheck of the original findings**

- **Evidence identity corrected.** EN `main.tex:201–205`, KO `main.tex:252–257`, NPC crosswalk lines 2–3, and generator line 18 consistently designate `verified-run-004`. Its admission report records **16 engineering + 72 screening records**, zero missing records, and no errors. All ten recorded runtime-source digests independently match the current files and both collection-time vectors. Generator lines 72–75 invoke strict validation; `aggregate.validation` remains explicitly separate generation-time placeholders. This review inspected that logic and the stored receipts; it did not rerun validation.
- **Request/decision state binding corrected.** [npc_goal.py:1838](/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/src/nesy_game/npc_goal.py:1838) compares the complete references. `tests/test_npc_goal_contract.py:252–317` supplies matching positive replay and revision/hash negatives that recompute the checksum and assert `replay_state_ref_mismatch`.
- **Godot status/target rejection corrected.** [npc_agent_client.gd:478](/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/game-track/godot/scripts/game3d/npc_agent_client.gd:478) enforces the status enum; lines 506–508 enforce typed targets; 567–568 reject executable steps under terminal/failure statuses. Lines 253–256 reject before directive emission. Fixtures at `npc_play_loop_harness.gd:336–415` require zero directives and unchanged state references; ordinary player, dialogue, and terminal controls remain. The existing copy/validate/commit writer remains intact at `sealed_lighthouse_machine.gd:58–89`.

**Provenance and scientific boundaries**

The inspected artifacts consistently retain:

- **24 real authenticated P CLI execution attempts and 24 decisions**, using default configuration without an explicit selector. Requested/returned identifiers and provider revision remain null; sampling seeds, tokens, and cost remain unavailable. Seeds **201–212 × two repetitions** are fixture identifiers.
- **P/R/O: 20 completed + four assigned stale-control failures per 24**, with goals reached **4/24** each. Engineering retains **14 completed + two failures per 16**. These are descriptive protocol counts.
- The selector test explicitly constructs known-selector **input** at [model-cohort test:176](/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/tests/test_generate_npc_paper_results_model_cohort.py:176), retaining the named-selector assertions and unavailable-provider-revision assertions through line 192.
- Zero model calls applies to **replay**, not collection. Native012 remains historical and source-bound; its runtime hashes differ from current004. Neither it nor 002/003 revalidates current bytes.
- Core Python controller authority, legacy ENG1’s engine-local mirror, and the separate **Godot-authoritative NPC v1.1** path remain distinguished.
- Both manuscripts disclose that the same authored KG targets select and summarize the retained strategy: EN line 208, KO line 260, experiment matrix line 4.

Supplemental checks verified all 131 visual-manifest receipts. Screening-result metadata was also checked across all rows; that supplemental check was **not** a complete inspection of the separate 4 MB results file.

**Coverage**

Paths are relative to `/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026/`. SHA values are 12-character prefixes. “Complete” includes rereading truncated output; single-line JSON entries were paginated through every byte.

| # | Path | SHA-256 prefix | Inspected coverage |
|---:|---|---|---|
| 1 | `paper/latex/en/main.tex` | `81f6a504eb85` | Complete, lines 1–285 |
| 2 | `paper/latex/ko/main.tex` | `400ca5fde436` | Complete, 1–341 |
| 3 | `paper/latex/generated/npc_results_en.tex` | `c08ac293f7b2` | Complete, 1–5 |
| 4 | `paper/latex/generated/npc_results_ko.tex` | `39cae23833e1` | Complete, 1–5 |
| 5 | `paper/latex/generated/npc_tables_en.tex` | `a9489eec2840` | Complete, 1–17 |
| 6 | `paper/latex/generated/npc_tables_ko.tex` | `cbab9bef43ff` | Complete, 1–17 |
| 7 | `research/academic-pipeline/contribution-evidence-matrix.csv` | `a41776fefe9f` | Complete, 1–6 |
| 8 | `research/academic-pipeline/experiment-evidence-matrix.csv` | `c79c4d41c1be` | Complete, 1–5 |
| 9 | `research/academic-pipeline/npc-goal-recovery/npc-contribution-evidence-matrix.csv` | `abae7c265e2f` | Complete, 1–3 |
| 10 | `research/academic-pipeline/npc-goal-recovery/verified-run-004/validation-report.json` | `2a440d2f96b1` | Complete, line 1; 2,379 bytes |
| 11 | `research/academic-pipeline/npc-goal-recovery/verified-run-004/aggregate.json` | `ac711f935c55` | Complete, line 1; 2,550 bytes |
| 12 | `configs/npc-goal-recovery.json` | `d63f5679f360` | Complete, 1–78 |
| 13 | `game-track/schemas/npc-goal-recovery.schema.json` | `649ccc5dfef6` | Complete, 1–170 |
| 14 | `src/nesy_game/npc_goal.py` | `53e501fbed6f` | Complete, 1–1972 |
| 15 | `scripts/generate_npc_paper_results.py` | `a43c9a20f993` | Complete, 1–527 |
| 16 | `game-track/godot/scripts/canonical_state.gd` | `6a4eb4693e0c` | Complete, 1–47 |
| 17 | `game-track/godot/scripts/game3d/npc_agent_client.gd` | `61d94f02c33d` | Complete, 1–783 |
| 18 | `_workspace/current/qa/npc-real-play-loop-v5-012/provenance.json` | `10fd713a4ba9` | Complete, 1–253 |
| 19 | `_workspace/current/qa/npc-real-play-loop-v5-012/replay-evidence.json` | `4991b13ffbc3` | Complete, 1–660 |
| 20 | `src/nesy_game/runtime.py` | `c620dee17655` | Complete, 1–484 |
| 21 | `src/nesy_game/validator.py` | `1039783e0695` | Complete, 1–146 |
| 22 | `src/nesy_game/repair.py` | `2f711ee9e3f1` | Complete, 1–121 |
| 23 | `src/nesy_game/contracts.py` | `80e2b8c1c3c1` | Complete, 1–364 |
| 24 | `game-track/godot/scripts/sealed_lighthouse_machine.gd` | `48da35d48547` | Complete, 1–206 |
| 25 | `scripts/run_npc_service.py` | `421b475a2fd1` | Complete, 1–755 |
| 26 | `scripts/codex_oauth_llm.py` | `608e3640df42` | Complete, 1–477 |
| 27 | `scripts/validate_npc_goal_evidence.py` | `21ec5410e9c7` | Complete, 1–2090 |
| 28 | `scripts/run_npc_goal_experiment.py` | `55ed019c4688` | Complete, 1–2230 |
| 29 | `scripts/update_visual_source_manifest.py` | `92edb75498c1` | Complete, 1–389 |
| 30 | `tests/test_npc_goal_contract.py` | `8b0a186183e9` | Complete, 1–500 |
| 31 | `tests/test_npc_play_loop.py` | `45965a220ffd` | Complete, 1–300 |
| 32 | `game-track/godot/tests/npc_play_loop_harness.gd` | `bf130a8a5760` | Complete, 1–520 |
| 33 | `tests/test_generate_npc_paper_results_model_cohort.py` | `9385bdc5c0f8` | Complete, 1–330 |
| 34 | `tests/test_npc_evidence_contract.py` | `8ce074d8a065` | Complete, 1–621 |
| 35 | `tests/test_npc_evidence_v5.py` | `392fe3700c2d` | Complete, 1–871 |
| 36 | `visuals/source-manifest.json` | `ff3eba627788` | Complete, 1–892 |
| 37 | `paper/latex/generated/npc_validation_reports.json` | `a8130e595276` | Complete, 1–68 |
| 38 | `paper/latex/figures/fig_npc_screening.svg` | `3ad9cf77180f` | Complete, 1–30 |
| 39 | `research/academic-pipeline/npc-goal-recovery/verified-run-004/source-manifest.json` | `1c99c5b549e9` | Complete, line 1; 7,833 bytes |
| 40 | `research/academic-pipeline/npc-goal-recovery/verified-run-004/engineering-aggregate.json` | `27a5271c3dc5` | Complete, line 1; 2,449 bytes |
| 41 | `research/academic-pipeline/npc-goal-recovery/verified-run-004/screening-assignment-manifest.json` | `bfeaea97629c` | Complete, line 1; 86,687 bytes |
| 42 | `research/academic-pipeline/npc-goal-recovery/verified-run-004/engineering-assignment-manifest.json` | `b8f577971306` | Complete, line 1; 20,135 bytes |
| 43 | `_workspace/current/qa/paper-project-review-20261015/codex-npc004-collection-trace.json` | `f99c5e5f61f3` | Complete, 1–197 |
| 44 | `_workspace/current/qa/paper-project-review-20261015/codex-precollection-smoke.json` | `fb3495a0eeef` | Complete, 1–39 |
| 45 | `_workspace/current/qa/paper-project-review-20261015/codex-replay-red.json` | `4ec3d81d6bab` | Complete, 1–33 |
| 46 | `_workspace/current/qa/paper-project-review-20261015/codex-godot-contract-red.json` | `780ade751558` | Complete, 1–259 |
| 47 | `_workspace/current/qa/paper-project-review-20261015/codex-review.md` | `59129e35017f` | Complete, 1–52 |

Remaining scientific limits include one authored world, constructed screening cases, no independent semantic gold, unverified actual model-family matching, unavailable provider revision/accounting, and no executed human, efficacy, generalization, or commercial-performance study. Unkeyed hashes establish content integrity, not writer authentication.

This verdict covers the inspected source/scientific scope. It does not establish CI completion, deployment approval, or journal acceptance.