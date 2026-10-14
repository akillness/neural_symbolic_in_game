# TRACE-RPG submission optimization / 논문·실험 최적화 (D-075)

Date / 기준일: 2026-10-14. Scope: evidence-bounded methods and instrumentation revision, not a new efficacy study or a journal acceptance decision.

## Current paper contract / 현재 원고 계약

The synchronized English and Korean manuscripts are **TRACE-RPG: Auditable Neuro-Symbolic Commit Gates for Interactive Game Worlds**. The contribution is an implemented authorization/repair/replay/accounting contract under authored policies. It is not a first-ever transaction protocol, a full event-sourcing guarantee, semantic completeness, authenticated provenance, model ranking, or player benefit.

한·영 원고는 문제 → 신뢰 경계 → 일곱 검증 조건 → 오류 기반 수리 → 실험 lane → 관찰 결과 → 한계의 흐름으로 정리했다. 수리 연산자 ρ는 이전 candidate와 typed validator error만 읽으며, 이 error가 유일한 state-derived 입력이다. 직접 `WorldState`를 읽는 `policy_restore` oracle과 구분한다. 동일 error에 대한 고정점은 수리 루프 수렴을 뜻하지 않으며, K는 시도 수의 상한이지 callback 시간 제한이 아니다.

The target remains IEEE Transactions on Games, Full Paper / instrumentation-and-methods. Removing legacy 7pt/6.5pt typography overrides produced 9-page EN/KO PDFs under standard IEEE typography; the provisional 6-page Short Paper gate failed and was explicitly superseded, not hidden by shrinking fonts or deleting evidence. The build enforces the detailed official Full Paper ceiling of 10 pages including references. Korean reference columns use the native IEEEtran trigger for this 58-reference snapshot.

Official guidance: <https://transactions.games/submit/submission-guidelines>, retrieved 2026-10-14. Its summary lists Full 10–14 / Short 6–8 while the detailed sections specify ceilings of 10 / 6; the top notice adopts double-anonymous review from 2025 while a later paragraph still says single-blind. The manuscript follows the newer anonymity notice and detailed 10-page ceiling. **The author must confirm the current category/format in the submission system; an editor decision, anonymous reviewer archive, DOI deposit, and originality declaration are not claimed.**

## Verified recent literature / 최신 문헌 대조

The current bibliography has **58 entries: 48 VERIFIED identity records and 10 PREPRINT records**. The 22 prior Semantic Scholar rate-limited lookups remain disclosed. This is a bounded primary-record refresh, not an assertion that every old source was newly fetched or that every preprint is archival.

| ID | Primary source, year | Defensible use / 허용되는 근거 |
|---|---|---|
| S57 | Geng et al., *JSONSchemaBench*, 2025, <https://arxiv.org/abs/2501.10868> | Structural schema compliance, constraint coverage and generation quality are distinct from game-state semantic authorization. |
| S58 | Ma et al., *Can LLM Agents Stick to the Script?*, 2026, <https://arxiv.org/abs/2608.08160> | Long-horizon narrative commitment/fact consistency motivates the problem; its results are not TRACE-RPG or player outcomes. |
| S59 | Sun et al., *The Emperor's New Clothes in Benchmarking?*, 2025, <https://arxiv.org/abs/2503.16402> | Benchmark rewriting does not establish contamination resistance; question-level leakage reporting remains necessary. |

All three were checked against primary arXiv records and corroborating identity metadata on 2026-10-14. Revision, retrieval date, unresolved venue conflicts and license limits are recorded in `research/sources/scraped/arxiv-*.md` and `research/source-ledger.yaml`. Missing paper licenses are not inferred from code/dataset licenses. S58's acceptance comment is not promoted without an established proceedings record.

## Experiment-to-evidence map / 실험과 근거 연결

| Lane | Evidence actually available | Allowed conclusion / 해석 상한 |
|---|---|---|
| E1 offline | 13 authored gate expectations; 12 invalid repair cases per arm; rejection-only 0/12, blind unchanged retry 0/12, error-guided ρ 5/12, state-reading oracle 6/12; 121 provenance rows = 85 executed + 36 aggregate | Encoded conformance in authored fixtures, not validator accuracy or independent population samples. |
| E2 live | Frozen screening packet, 5 cells × 5 calls; 3 cells initially valid; constructed policy-blind Signal-v2 ρ 5/5 vs blind 0/5; goal-blind null regime 0/5 vs 0/5 | `screening-pilot-only`, regime-dependent mechanism transfer; no general sample-efficiency/model superiority. |
| E3 methods graph | Existing closed-world simulation; source-input hashes refreshed after citation/ledger changes | Simulation-only; not retrieval/memory runtime efficacy and not a new simulation result. |
| ENG1 game | Authored Godot fixture/replay/presentation conformance; fixed 52/52 core, separate 4-check extension, fixed 8/8 smoke; new local receipt integrity lane | Engine-local engineering evidence; no live Python round-trip, attention, comprehension, latency, enjoyment, immersion or agency claim. |

`C-RESULT-001`–`005` remain `TODO-RESULT`; G4/G6 are not promoted. There are **0 human participants**. The 64 = 43 + 21 values in historical narrative/passport snapshots do not replace the current hash-bound 121-row Stage-04 packet.

### Reproduction observed this revision

`uv run python scripts/run_conformance_pilot.py --output-dir <temporary>/runs --release-dir <temporary>/release` exited 0 without writing the frozen bundle. `pilot-results.json` and assignment manifest were identical; **11/11 CSVs were byte-identical**. See `_workspace/current/qa/releases/2026-10-14/conformance-replication.json` for the exact command and hashes. The frozen assignment manifest remains `64308191b933d0ceaad1d15689c48d2a6ea22c0f6b03ee19b9c571defa414d48`.

## Environment, visuals and layout / 환경·시각자료·레이아웃

- The architecture SVG now distinguishes E1, E2 and ENG1 while showing proposal → parser/policy → validate → repair/fallback → commit → record → replay. `fig_evidence_regimes.svg` displays raw, non-pooled regime contrasts from the three registered JSON sources; no generated image supplies measured data.
- All numerical table prose is derived from frozen JSON inputs. The state-reading oracle, typed-error operator and blind unchanged control stay distinguishable in both languages; initial-valid and null live regimes are retained.
- The manuscript's playable readout uses `paper/latex/captures/playable-readout-20261014-r2/`: three fresh native PNG + shot-receipt pairs, measured trim boxes, full source/state hashes, dimensions and bytes. They are illustration-only working captures, never retouched or promoted to efficacy evidence.
- Captures were produced on a disposable project by `python3 scripts/run_playable_evaluation.py --godot <Godot-4.7.1> --capture`: 4/4 screenshots and 52/52 core checks. Canonical `project.godot` remains `2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd`.
- `make -C paper/latex check` builds the two PDFs, checks page counts, rejects Type 3 fonts and layout/reference/glyph errors, and now fails closed if PDF inspection or conversion tools fail. Temporary figure outputs are promoted only after all conversions succeed. The negative-path Makefile tests reject stale-PDF success, missing page metadata, >10 pages, tool failures and an early Type 3 figure.

### Codex environment concept / 코덱스 환경 개념 이미지

`god-tibo-imagen` 0.4.1 generated one 1536×1024 environment style anchor after `gti --dry-run`. Local preview: `_workspace/current/ui/paper-optimization/environment-style-anchor.png`; exact prompt, dry-run receipt and adjacent provenance are retained. It depicts the closed evidence case, harbor-side signal and unlit sealed offshore lighthouse. **It is an AI-generated concept, not a game capture or result.**

The image bytes remain local and gitignored pending **human rights/style review**; `runtime_eligible`, `primary_experiment_eligible` and `manuscript_eligible` are all false. The PNG is deliberately absent from the paper and public repository. Author sign-off is needed before its promotion; no implicit approval is claimed. Generated UI art already curated in previous studio decisions remains disclosed in both manuscripts.

## Experimental game observation contract / 게임 관찰 계약

Ordinary gameplay records **zero new observation receipts**. Explicit `--evaluate` or `--receipt-output <path>` enables the local engineering packet. It records coded objective/hold/commit/case-chain/session events, monotonic event-availability timestamps, a pseudonymous local session ID, source-byte fingerprint and prior/next canonical hashes. It is not the authoritative research trace, save state, model output, participant observation or browser input-latency measurement.

The per-kind payload key set is exact. Default opt-out, malformed empty commit payload and overflow are exercised by disposable Godot probes. A 4096-row cap fails the packet and refuses export rather than silently dropping data; canonical state stays unchanged. The full authored autoplay exports the 12-receipt lifecycle with hash continuity. Tests run only against staged copies; the core 16 presentation checks and 8 smoke checks are not inflated by receipt checks.

## Verification and release record / 검증·전달 기록

Observed focused gates: conformance replication 11/11 CSVs, Godot protocol tests 4/4, citation tests 5/5, Makefile negative-path tests 6/6, independent final code review no P0/P1 blocker. These are local engineering checks, not study outcomes.

Final CI-equivalent verification and push status are recorded in `_workspace/current/qa/releases/2026-10-14/verification.json` after execution. Pending entries must not be read as PASS. The pre-existing dirty UI/README work is excluded from this change: after a prohibited reviewer stash/pop/drop, 12 dirty tracked files and 10 untracked user files matched the recovered snapshot byte-for-byte; see `shared-tree-preservation.json` and `_workspace/current/conflicts.md`.

### Submission boundary / 실제 제출 경계

The deliverable is a defensible, reproducible **methods/instrumentation submission candidate**, not an unconditional claim of journal readiness or acceptance. A reviewer archive and author declarations still need author completion, and official category wording needs confirmation. Confirmatory multi-model/held-out semantic, retrieval/memory and human studies would be required before asserting the corresponding efficacy claims; this revision neither fabricates them nor disguises fixtures as participants.
