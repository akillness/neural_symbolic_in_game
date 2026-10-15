---
type: report
date: 2026-10-15
ai-first: true
proof_status: source-bound-engineering-and-descriptive-screening-verified
---

# NPC Goal Operation — Implementation and Evidence

Updated 2026-10-15. This repository report is authoritative for the current implementation; an external vault copy is not a substitute for updating this file. Earlier pending collection notes are superseded by the completed receipts below.

## Current result and boundary

The fixed-goal `sealed-lighthouse-v1` prototype is implemented. Godot is the sole canonical-state writer. Python interprets typed intent against six public-observation fields, performs bounded BFS, and replans from fresh observations without reinterpreting the original intent. Player requests perform acquisition/installation; only Captain Mira can commit an authorized `reveal_hint`.

This is engineering and descriptive fixed-case evidence, not recovery efficacy, model superiority, generalization, human benefit, semantic gold, or an independent-oracle comparison. `C-RESULT-001`–`005` and the human G4/G6 boundaries are not promoted.

## Canonical screening packet

Current packet: `neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/npc-goal-recovery/verified-run-002/`.

- Collection command: `uv run python scripts/run_npc_goal_experiment.py --packet all --model gpt-5.6-sol --output-dir research/academic-pipeline/npc-goal-recovery/verified-run-002 --godot-timeout 120`; exit 0, 88 records, 631.33 seconds.
- Strict validation: `uv run python scripts/validate_npc_goal_evidence.py --packet all --packet-dir research/academic-pipeline/npc-goal-recovery/verified-run-002`; valid with zero errors. NPC-ENG1 has all 16 engineering assignments and is not empirical-publishable by design. NPC-SCR1 has all 72 screening assignments and passes its descriptive publication gate.
- P has 24 observed authenticated CLI execution attempts explicitly requesting `gpt-5.6-sol`. These are not remote billing-call counts.
- Each P/R/O screening arm retains 20 completed executions and 4 assigned failures. The 12 failures are the pre-authored stale-revision/stale-policy ACK controls, not relabelled successes. Observed goal counts are 4/24 per arm, not recovery-rate estimates.
- The source-independent row count is zero. O's same-family designation is a protocol source classification, not evidence of actual model-family matching.
- Ten runtime source hashes match before/after collection. The UI-only choice-layout fix is outside this packet's ten-path source set; the 17-path native proof and render evidence were separately recollected.

### Model identity is not model revision

The historical field `model.returned` contains `gpt-5.6-sol` in all 24 P records, but its producer copies `decision.provenance.model`, which originates from `Interpretation(..., self.model)`. It propagates the configured selector, not provider-returned revision metadata. `usage.model_revision_available` is false and `usage.model_revision` is null. Provider seed, token accounting, cost, and immutable provider revision remain unavailable. Neither global CLI configuration nor a configured selector identifies the actual provider revision. The original unknown-selector `verified-run-001/` remains immutable and is not pooled with 002.

## Current native closed-loop proof

Current proof: `neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/npc-real-play-loop-v5-012/`.

- Real Godot → HTTP → authenticated Codex → Godot test: `uv run pytest tests/test_npc_play_loop.py::test_optional_real_service_mode_uses_existing_endpoint_and_report_contract -q --basetemp _workspace/current/qa/npc-real-play-loop-v5-012/pytest`, with the explicit real-service environment and transient capability. Result: **1 passed in 24.99s**, `artifact://3299`.
- All 17 runtime/config/UI/harness source hashes match before and after execution. UI source SHA-256 is `7dc4cf70084f1a2c7380f35b8bd262f55a088d91862d8fd866ebed2e53e3b487`; Game3D source SHA-256 begins `2a273cf3`. These are file hashes, not Git commit names.
- Nine trace rows contain one utterance request, three observation requests, four decisions, and one reused typed-intent ID across epochs 2, 4, and 6.
- Each epoch's snapshot identity and HTTP semantic replay validate. Replay adds zero model calls; this does **not** mean the live runtime used zero model calls.
- Final canonical state: revision 3, SHA-256 `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`.
- Exact command/result, source maps, trace, and replay receipts are in `provenance.json`, `service-trace.jsonl`, `replay-evidence.json`, and the referenced pytest report. This proof does not record a contemporaneous Git base-commit/dirty flag; old proof context must not be copied into it.

## Immutable proof history

| Artifact | Observed outcome | Current interpretation |
|---|---|---|
| Native 007 | Passed at its recorded 16 source hashes; 21.34s | Historical execution-bound proof; not current after service changes. |
| Native 008 | Failed with the explicit unsupported-model Codex execution error | Retained failure. Availability is established from actual redacted CLI error evidence, not global configuration/cache. |
| Native 009 | Passed in 26.90s at its 17 source hashes | Historical. Only replay is zero-call; do not describe the live run as zero-model-call. |
| Native 010 | Passed in 57.95s at its source bytes | Historical after the seven-code Game3D presentation mapping change. |
| Native 011 | Passed in 22.86s, 17 matching source hashes | Historical after the Mira UI source change; hashes were not rebound. |
| Native 012 | Passed in 24.99s, 17 matching source hashes | Current closed-loop engineering demonstration, separate from screening. |
| verified-run-001 | 88 rows, 24 CLI attempts; unknown requested selector | Historical cohort, never retrospectively assigned the later selector. |
| verified-run-002 | 88 rows, 24 explicitly configured P CLI attempts | Current descriptive packet; all assigned failures remain. |

## Render evidence

Current immutable set: `godot-4.7.1-20261015t083849z-sealed-lighthouse-current-v3` under `_workspace/current/engineering/tech-verification/evidence/`.

Its manifest SHA-256 is `387d6404d28930cc423d612f37ba1f1782381f749f4a4395f252f88a7c4a44e8`. The capture pipeline is `90ef696dfbc86015ea3f5560d4b093f2528eac16944c59ab8005cc98cc857461`, and the UI source is the same `7dc4cf7…` as native012. Four headless fixture runs pass their checks; three non-headless 1280×720 captures validate. Core presentation accounting remains 52/52 plus 4/4 extension checks; smoke accounting remains 8/8. Earlier v1/v2 sets and the legacy v5 set remain untouched execution history. `validate_game_studio.py` passes with the v3 pointer.

## Actual responsive UI defect and final Web proof

R4 reproduced the Mira defect in a fresh isolated browser session. The outer 390×844 page gives Godot a **344×720** canvas. The choice ScrollContainer had a 44px allocation while wrapped authored buttons needed 54px, so scrolling could not fully reveal them. The fix derives the scroll floor from the tallest post-layout visible button via `sort_children`; it preserves the user's 0.58/0.78 anchors, 180px resting floor, and 0.70 panel alpha. Clearing choices restores the compact resting layout.

The preserved pre-fix snapshot still fails the geometry control. The staged lifecycle suite passes 4 tests; its signal test is not represented as browser pointer E2E. Independent Godot code review approves with zero findings.

Final build command: `./scripts/build_godot_web.sh`, exit 0, `artifact://3385`. Actual final-binary desktop and mobile browser verification is recorded in `_workspace/current/qa/npc-web-current-20261015-r5/final-build-full-flow.json`: all four authored choices are visible/scroll-reachable before the first real pointer click; the click appends Mira's scripted line without canonical mutation; all four Case File cards and its footer remain reachable. Console/page/request/HTTP errors are zero. Capability/free-text controls are untouched and no NPC/model calls are made by browser QA. The original R4/R5 reports and the intermediate coordinate-calibration mistake remain recorded.

The final PCK hash begins `d9b280b5`, versus `37bfe94b` in the earlier R5 package, with a 16-byte size difference. Old raw PCK bytes were not retained, so the differing entry/cause is **not established** and byte-identical Web-export reproducibility is not claimed. Final HTML/JS/PCK/WASM bytes were independently fetched and matched to the final local build, and the full flow was rerun on that actual binary rather than inferred from its predecessor.

## Publication and verification gates

- Final `make check` passes: English and Korean are each 10 pages, standard IEEE typography, no overfull/undefined-reference/missing-character errors. The bounded citation crosswalk is 5 contributions, 58 references, 9 topics, 3 experiment lanes plus 1 engineering lane.
- Visual verification passes: 110 unique receipts, 7 SVG assets, and 22 sources double-regenerated in an isolated copy. NPC labels meet the 28px source floor; SVG/PDF aspect and real table anchors agree.
- The path validator maps recorded absolute command inputs to the same contained packet member after relocation. Original and relocated packets validate; different-member, outside-path, same-basename, and input-byte substitutions remain rejected. No immutable packet bytes were edited to obtain that result.
- Full `./scripts/verify_like_ci.sh` passes after the final builds were frozen: 293 unittest cases; 78 game-track tests and 48 subtests; lint/format; project integrity; visual/citation/crosswalk; offline smoke; harness; 14/14 research records; survey; wiki lint. Exit 0, 292.95s. The earlier concurrent-build run's stale-receipt failure is retained as FIX→repaired, not deleted.
- Independent Python capture/regeneration/portable-identity/model-wording review and Godot UI review pass. Human efficacy, G4/G6, participant/affect evidence, cross-world generalization, provider revision/cost, and actual journal acceptance are not claimed.

## Public asset boundary

The final publication inspection caught local-only D-046 rig payloads in diagnostic project copies before any commit or push. Selection removed 96 raw/sidecar files and 1,020 generated Godot-cache files from the index across 12 candidate QA copies; their local bytes remain untouched. Project-scoped `.gitignore` rules now protect every copied `assets/rig/` payload (with the README exception) and `.godot/` cache, including future copies. `git check-ignore --no-index --stdin -z` confirms all 1,129 private/cache probes are ignored, covering all 22 existing local QA FBX copies, both local canonical-packet project copies, and the original rig; 15 public README/GLB/packet controls remain unignored. Both index and HEAD contain no private rig/cache payload. `git log --all --oneline -- ':(glob)**/assets/rig/player-rig*'` and `git lfs ls-files --name-only` return no entries in the available repository refs.

Three immutable historical QA manifests (`npc-preflight-v4-cli-evidence-001`, `npc-runner-v4-staged-eng`, and `npc-runner-v4-staged-screen`) retain whole-tree receipts naming omitted rig/cache members. Those historical copied presentation environments are intentionally not byte-complete public reconstructions; their old receipts are not rewritten or presented as clean-clone proof. In contrast, canonical002 has 1,333 receipts with zero `godot-project/`, rig, or cache members, and native012 binds only its 17 named runtime/config/UI/harness sources. Independent provenance and asset-boundary reviews pass.

A fresh export of the selected Git index, with no private rig/cache payload, passes `uv run --extra research --extra dev python scripts/validate_npc_goal_evidence.py --packet all --root <public-project-root> --packet-dir research/academic-pipeline/npc-goal-recovery/verified-run-002` (exit 0, 1.94s): 16 valid engineering assignments and 72 valid descriptive-screening assignments, zero errors, zero replay model calls. The complete output is retained at `neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/npc-public-release-20261015/canonical-validation.json`. The first isolated attempt without the declared `research` extra correctly failed with `jsonschema_unavailable`; installing the declared research/dev extras resolved that prerequisite, not a validator relaxation.

The complete public-snapshot `./scripts/verify_like_ci.sh` gate then passes in 232.26s: 293 unittest cases, 78 game tests plus 48 subtests, and every remaining named gate. Its observed output excerpt is retained in `_workspace/current/qa/npc-public-release-20261015/ci-public-snapshot.txt`, with the combined receipt in `asset-boundary.json`. The first full attempt is retained as `ci-unborn-head.txt` and remains a failed/FIX attempt: three conformance-pilot tests could not execute `git diff HEAD` in the initially unborn temporary repository. Fetching the actual existing `f3b1eed` base and initializing only that temporary repo's Git index repaired the verification fixture; no source/test assertion was changed, and the entire gate was rerun. The private-rig-free focused Godot loop also passes (1 passed, 1 opt-in test deselected in 6.04s); all 17 public-source hashes match native012.

Git commit/push is performed only after these repository records and the selected source snapshot are fixed; its actual result belongs to the release history, not a guessed future status in this report.

## Reusable lessons

Freeze formatting and every hash-bound source before capture. Presentation-only code changes still require a new source-bound proof; never rewrite an old SHA receipt. Distinguish configured identifiers from provider metadata, runtime calls from replay calls, protocol validity from efficacy, logical sequence from physical delivery order, and unkeyed integrity hashes from authentication. Test the embedded canvas dimensions, not only the outer page viewport. Validate a relocated packet before calling the artifact portable. Update the repository's actual knowledge files: a successful write to a separate global vault does not update this project.
