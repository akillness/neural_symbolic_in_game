**Verdict: FIX.** All 26 listed artifacts were inspected completely; their SHA-256 hashes match the review manifest. Three material findings remain.

1. **High — Publication evidence points to an invalid packet.**  
   `research/academic-pipeline/npc-goal-recovery/verified-run-002/validation-report.json:1` marks both NPC-ENG1 and NPC-SCR1 `valid:false`, `publishable:false`, with runtime-source hash mismatches. Nevertheless, `paper/latex/en/main.tex:201` and `paper/latex/ko/main.tex:252` identify NPC002 as validated reproduction evidence; `research/academic-pipeline/npc-goal-recovery/npc-contribution-evidence-matrix.csv:3` calls it strict-validated screening. Meanwhile, `scripts/generate_npc_paper_results.py:18` selects NPC003. This breaks manuscript–generator–evidence identity. Align the publication pointers with the intended admissible packet and fresh strict validation, preserving NPC002 unchanged. NPC003’s stored report is not a fresh validation performed by this review.

2. **Medium — NPC semantic replay omits request/decision state binding.**  
   In `src/nesy_game/npc_goal.py:1834–1882`, replay reconstructs planning context using the **request’s** state reference but never requires the decision’s state reference to equal it. Result transition validation then uses the **decision’s** reference at `src/nesy_game/npc_goal.py:1899–1905`. Consequently, an internally checksummed record can contain inconsistent planning and transition origins without this semantic check rejecting the inconsistency. Require matching request/decision state references before accepting the decision. This is a static source finding; no mutation fixture was executed.

3. **Medium — Godot accepts decisions outside the canonical status/target contract.**  
   `game-track/godot/scripts/game3d/npc_agent_client.gd:467–564` does not validate the decision-status enum and accepts arbitrary string targets up to 128 characters (`:503–505`). The canonical schema restricts targets to null/lens/signal/tide_marks (`game-track/schemas/npc-goal-recovery.schema.json:74`) and defines explicit statuses (`:111`). With nonempty steps, `npc_agent_client.gd:253–315` routes the operation without checking status, permitting a cancelled/failed-status decision to issue a directive if its other gates pass. Empty-step `ERROR` is also accepted at `:260–267`, although absent from the schema. Enforce canonical enums and status/step consistency. The inspected hard gates still constrain physical operations; this finding does not establish arbitrary canonical mutation.

Observed evidence boundaries:

- EN/KO sources agree on **16 + 72 = 88 assignments over 28 definitions**, with **R/P/O = 40/24/24**. Screening tables retain 20 completed and four failed assignments per arm. These are descriptive counts, not efficacy estimates or independent gold.
- O is explicitly auxiliary; actual model-family matching remains unverified. Unavailable provider revision, seed, tokens, cost, and latency remain null where reported.
- The generator invokes strict validation before loading results (`scripts/generate_npc_paper_results.py:67–75`); aggregate validity placeholders are not its authority. Portable normalization compares resolved full paths (`:53–64`), not basenames.
- Legacy ENG1, additive Godot-authoritative NPC integration, and native012 transport/replay remain separate provenance boundaries. Native012 records one utterance, three observations, and zero-model-call replay; it establishes neither efficacy nor shipped Web live-LLM deployment.
- Both manuscripts disclose KG strategy-selection reuse and unkeyed integrity hashes. No promotion to measured G4/G6, human benefit, recovery efficacy, or cross-model superiority was found.
- EN/KO reference labels resolve through their included fragments, and referenced figure files exist. Rendered layout, citation identity, and figure contents were not independently verified here.

No files were changed; no Git operations, builds, tests, linters, network calls, integrations, or subagents were used. Findings are source-review conclusions. Previous failed OpenCode attempts remain failed; this is a separate Codex reviewer process, not an independent-model claim, journal acceptance, or completed release.

All paths below are relative to `/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026`. Ranges are inclusive; **all rows represent complete inspection**, including rereads of initially truncated output.

| # | Actual inspected source | Inspected lines |
|---|---|---|
| 1 | `paper/latex/en/main.tex` | 1–240; 241–285 |
| 2 | `paper/latex/ko/main.tex` | 1–180; 181–306; 307–341 |
| 3 | `paper/latex/generated/npc_results_en.tex` | 1–5 |
| 4 | `paper/latex/generated/npc_results_ko.tex` | 1–5 |
| 5 | `paper/latex/generated/npc_tables_en.tex` | 1–17 |
| 6 | `paper/latex/generated/npc_tables_ko.tex` | 1–17 |
| 7 | `research/academic-pipeline/contribution-evidence-matrix.csv` | 1–6 |
| 8 | `research/academic-pipeline/experiment-evidence-matrix.csv` | 1–5 |
| 9 | `research/academic-pipeline/npc-goal-recovery/npc-contribution-evidence-matrix.csv` | 1–3 |
| 10 | `research/academic-pipeline/npc-goal-recovery/verified-run-002/validation-report.json` | 1, complete JSON |
| 11 | `research/academic-pipeline/npc-goal-recovery/verified-run-002/aggregate.json` | 1, complete JSON |
| 12 | `configs/npc-goal-recovery.json` | 1–78 |
| 13 | `game-track/schemas/npc-goal-recovery.schema.json` | 1–170 |
| 14 | `src/nesy_game/npc_goal.py` | 1–300; 301–600; 601–920; 921–1220; 1221–1520; 1521–1770; 1771–1970 |
| 15 | `scripts/generate_npc_paper_results.py` | 1–220; 221–390; 391–527 |
| 16 | `game-track/godot/scripts/canonical_state.gd` | 1–47 |
| 17 | `game-track/godot/scripts/game3d/npc_agent_client.gd` | 1–270; 271–530; 531–778 |
| 18 | `_workspace/current/qa/npc-real-play-loop-v5-012/provenance.json` | 1–253 |
| 19 | `_workspace/current/qa/npc-real-play-loop-v5-012/replay-evidence.json` | 1–240; 241–460; 461–660 |
| 20 | `src/nesy_game/runtime.py` | 1–250; 251–484 |
| 21 | `src/nesy_game/validator.py` | 1–146 |
| 22 | `src/nesy_game/repair.py` | 1–121 |
| 23 | `src/nesy_game/contracts.py` | 1–200; 201–364 |
| 24 | `game-track/godot/scripts/sealed_lighthouse_machine.gd` | 1–206 |
| 25 | `scripts/run_npc_service.py` | 1–260; 261–520; 521–755 |
| 26 | `scripts/codex_oauth_llm.py` | 1–245; 246–477 |