# TRACE-RPG submission optimization / 논문·실험 최적화 (D-075; maintained revision note)

Date / 기준일: 2026-10-23 update to the 2026-10-14 record. Scope: evidence-bounded methods, artifact, and single-development-case revision; not a new efficacy study or a journal acceptance decision.

## Current paper contract / 현재 원고 계약

The synchronized English and Korean manuscripts are **TRACE-RPG: Source-Bound Ontology Evidence and a Bounded Codex-Assisted Integration Case in an Interactive Game**. The contribution is an implemented authorization/repair/replay/accounting contract, a read-only bilingual ontology-to-evidence view, and one runtime-reported Codex development case ($n{=}1$, independent repeats $0$). It is not a model-performance comparison, full-game efficacy result, authenticated provenance claim, semantic completeness claim, or player-benefit study.

한·영 원고는 문제 → 신뢰 경계 → 일곱 검증 조건 → 오류 기반 수리 → typed evidence lane → 단일 개발 사례 → 한계의 흐름으로 정리했다. 수리 연산자 $\rho$는 이전 candidate와 typed validator error만 읽으며, `policy_restore` oracle과 구분한다. 현재 본문은 과거 live-screening/E2 코호트를 active table·count·outcome에서 제외하고 immutable historical provenance로만 남긴다. 과거 label/outcome은 runtime-reported `gpt-6.1-sol` 사례로 이전하지 않는다.

현재 모델 표기는 native runtime context의 `gpt-6.1-sol` 선택 보고일 뿐 provider attestation이 아니다. Provider identity, immutable revision, seed, cost는 `null`; model-only latency도 없다. 실제 사례는 six native CLI calls, zero independent repeats, dashboard observer extension, named failures, 62 frozen checks와 Godot Web build를 기록하지만 full-game creation이나 model efficacy를 주장하지 않는다. 표준 IEEE type과 ≤10-page intent를 유지하며, 결과물 재생성·빌드·Git 검증은 Main 소유다.

공식 guidance: <https://transactions.games/submit/submission-guidelines> (2026-10-14 확인). 원고는 최신 anonymity notice와 detailed Full Paper ceiling을 따르며, author가 제출 category/format을 확인해야 한다. editor decision, reviewer archive, DOI deposit, originality declaration은 주장하지 않는다.

## Verified recent literature / 최신 문헌 대조

The current bibliography has **58 entries: 48 VERIFIED identity records and 10 PREPRINT records**. The 22 prior Semantic Scholar rate-limited lookups remain disclosed. This is a bounded primary-record refresh, not an assertion that every old source was newly fetched or that every preprint is archival.

| ID | Primary source, year | Defensible use / 허용되는 근거 |
|---|---|---|
| S57 | Geng et al., *JSONSchemaBench*, 2025, <https://arxiv.org/abs/2501.10868> | Structural schema compliance, constraint coverage and generation quality are distinct from game-state semantic authorization. |
| S58 | Ma et al., *Can LLM Agents Stick to the Script?*, 2026, <https://arxiv.org/abs/2608.08160> | Long-horizon narrative commitment/fact consistency motivates the problem; its results are not TRACE-RPG or player outcomes. |
| S59 | Sun et al., *The Emperor's New Clothes in Benchmarking?*, 2025, <https://arxiv.org/abs/2503.16402> | Benchmark rewriting does not establish contamination resistance; question-level leakage reporting remains necessary. |

All three were checked against primary arXiv records and corroborating identity metadata on 2026-10-14. Revision, retrieval date, unresolved venue conflicts and license limits are recorded in `research/sources/scraped/arxiv-*.md` and `research/source-ledger.yaml`. Missing paper licenses are not inferred from code/dataset licenses. S58's acceptance comment is not promoted without an established proceedings record.

## Current experiment-to-evidence map / 현재 실험과 근거 연결

| Lane | Evidence actually available | Allowed conclusion / 해석 상한 |
|---|---|---|
| E1 offline | Authored gate/repair fixtures, frozen classes, integrity and assignment accounting | Encoded conformance in authored fixtures; not validator accuracy or population evidence. |
| E3 methods graph | Existing closed-world typed-link simulation and authored holdout construction | Simulation/construction only; not retrieval or memory efficacy. |
| ENG1 game | Authored Godot fixture/replay/presentation conformance with no live Python transport | Engine-local evidence; no live authorization round trip, player, latency, or efficacy claim. |
| NPC-DISC-1 | Frozen declaration-derived disclosure strata and public-safe trace records | Bounded engineering counts; E/R/C/NR remain typed and non-pooled. |
| DEV-CASE | One read-only bilingual dashboard integration case: 6 native CLI calls, $n{=}1$, repeats 0, runtime-reported `gpt-6.1-sol` | Descriptive integration evidence only; provider metadata unavailable and no model comparison. |
| E2 / old live screening | Immutable historical packet retained for provenance/hash validation | **HISTORICAL_ARCHIVE_ONLY**; excluded from active tables, counts, and runtime-model outcomes. |

`C1`–`C5` remain bounded design/conformance descriptions; no C6 or full-game round-trip is promoted. The proposed source-derived traceability rubric is unmeasured and is documented in `research/traceability-scoring-20261023/`. Whole-game matched-information and repeated-cross-model comparison are `PROPOSED_NOT_EXECUTED` in `research/development-comparison-20261023/`.
### Reproduction observed this revision

`uv run python scripts/run_conformance_pilot.py --output-dir <temporary>/runs --release-dir <temporary>/release` exited 0 without writing the frozen bundle. `pilot-results.json` and assignment manifest were identical; **11/11 CSVs were byte-identical**. See `_workspace/current/qa/releases/2026-10-14/conformance-replication.json` for the exact command and hashes. The frozen assignment manifest remains `64308191b933d0ceaad1d15689c48d2a6ea22c0f6b03ee19b9c571defa414d48`.

## Environment, visuals and layout / 환경·시각자료·레이아웃

- Any older architecture/evidence-regime figure that names E2 is historical context only; active manuscript figures and tables show E1/E3/ENG1/NPC-DISC-1/DEV-CASE as typed, separate lanes, with no E2 result or old model label as a current outcome.
- Current traceability proposal uses source-derived TR01--TR06 dimensions with explicit denominator, missingness, independence, and outcome-status rules; no score was collected in this revision.
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

The deliverable is a defensible, reproducible **methods/instrumentation submission candidate with one bounded development case**, not an unconditional claim of journal readiness or acceptance. A reviewer archive and author declarations still need author completion, and official category wording needs confirmation. Confirmatory whole-game, repeated-cross-model, held-out semantic, retrieval/memory, and human studies would be required before asserting corresponding efficacy claims; this revision neither fabricates them nor disguises fixtures as participants.
