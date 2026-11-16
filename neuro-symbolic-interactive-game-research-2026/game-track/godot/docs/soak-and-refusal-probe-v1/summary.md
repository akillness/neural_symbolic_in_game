# Sealed Lighthouse — Refusal Coverage & Headless Soak Probe

- **Probe ID**: `SL-SOAK-REFUSAL-PROBE-001`
- **Status**: **PASS** (`OBSERVED_ENGINE_RUN`)
- **Engine**: Godot `4.7.1-stable (official)` (`display_server=headless`, `os=macOS`)
- **Canonical Terminal SHA-256**: `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`

> Claim boundary: Headless Godot engine conformance, refusal-code coverage, and deterministic step/commit timing + memory stability soak only. Not evidence for human gameplay, G3/G4/G7, usability, immersion, or LLM efficacy.

## 1. Refusal-Code Coverage (Previously Unexercised + Full Matrix)

- **Implemented / Exercised**: `9/9` (`100%` of `IMPLEMENTED_CODES`)
- **Newly Exercised Codes**: `OBJECT_NOT_REACHABLE`, `QUEST_STAGE_PRECONDITION`
- **State-Hash Isolation**: `11/11` (`all_cases_state_isolated=True`)
- **EvaluationTrace Mirror Consistency**: `11/11` (`all_cases_trace_consistent=True`)

| Case ID | Expected Code | Observed Codes | Mechanism | Isolated | Trace Consistent | Latency (ms) |
| --- | --- | --- | --- | --- | --- | ---: |
| `unexercised-01a-object-not-reachable-world-event` | `OBJECT_NOT_REACHABLE` | `OBJECT_NOT_REACHABLE` | canonical apply_world_event('LENS_UNREACHABLE') removes lamp_store from reachable_locations | PASS | PASS | 0.018 |
| `unexercised-01b-object-not-reachable-snapshot` | `OBJECT_NOT_REACHABLE` | `OBJECT_NOT_REACHABLE` | hash-verified load_state_if_hash_matches with object at unreachable 'blocked_tower_room' | PASS | PASS | 0.013 |
| `unexercised-02a-quest-stage-precondition-stage0` | `QUEST_STAGE_PRECONDITION` | `QUEST_STAGE_PRECONDITION` | hash-verified load_state_if_hash_matches with carried signal_lens and quest.stage=0 | PASS | PASS | 0.016 |
| `unexercised-02b-quest-stage-precondition-stage-neg1` | `QUEST_STAGE_PRECONDITION` | `QUEST_STAGE_PRECONDITION` | hash-verified load_state_if_hash_matches with carried signal_lens and quest.stage=-1 | PASS | PASS | 0.011 |
| `core-03-missing-required-object` | `MISSING_REQUIRED_OBJECT` | `MISSING_REQUIRED_OBJECT` | install_lens before acquire_object | PASS | PASS | 0.017 |
| `core-04-unknown-operation` | `UNKNOWN_OPERATION` | `UNKNOWN_OPERATION` | unsupported operation name | PASS | PASS | 0.010 |
| `core-05-forbidden-disclosure` | `FORBIDDEN_DISCLOSURE` | `FORBIDDEN_DISCLOSURE` | permanently_forbidden fact requested | PASS | PASS | 0.076 |
| `core-06-stage-gated-disclosure` | `STAGE_GATED_DISCLOSURE` | `STAGE_GATED_DISCLOSURE` | stage-gated fact requested before quest.stage >= 2 | PASS | PASS | 0.072 |
| `core-07-unknown-actor` | `UNKNOWN_ACTOR` | `UNKNOWN_ACTOR` | undeclared actor_id | PASS | PASS | 0.072 |
| `core-08-npc-does-not-know-fact` | `NPC_DOES_NOT_KNOW_FACT` | `NPC_DOES_NOT_KNOW_FACT` | fact absent from captain_mira knowledge list | PASS | PASS | 0.072 |
| `core-09-object-not-present` | `OBJECT_NOT_PRESENT` | `OBJECT_NOT_PRESENT` | acquire_object after signal_lens already acquired | PASS | PASS | 0.011 |

Supplementary note: `DISCLOSURE_TEMPLATE_UNAVAILABLE` is a defensive guard in `_reveal_hint` triggered only if `EvidenceCaptureRunner.CAPTURE_SPECS` lacks `sl-rc-003-authorized-hint`; it remains structurally unreachable under intact source assets.

## 2. Deterministic Headless Soak Loop

- **Ticks Executed**: `1600` (`warmup_ticks=64`, `steady_state_ticks=1536`, `cycle_length=8`)
- **Episodes Completed**: `200` (`terminal_hash_matches=200/200`)
- **Commits / Refusals / World Events / Save-Loads**: `600` / `800` (`800` isolated) / `200` / `400`
- **EvaluationTrace Checks Consistent**: `1600/1600`
- **Total Soak Wall Time**: `11020.559 ms`

### Step/Commit & Headless Frame Timing (ms, `Time.get_ticks_usec`)

| Metric | Count | Min | Mean | p50 | p95 | p99 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `step_commit_all_ticks` | 1600 | 0.081 | 0.474 | 0.379 | 1.099 | 1.507 | 8.019 |
| `step_commit_steady_state` (post-warmup) | 1536 | 0.081 | 0.486 | 0.406 | 1.108 | 1.512 | 8.019 |
| `commit_only_operations` | 600 | 0.082 | 0.433 | 0.337 | 0.986 | 1.507 | 7.671 |
| `frame_wall_all_ticks` (incl. tick-1 startup) | 1600 | 0.341 | 6.888 | 6.869 | 8.174 | 8.522 | 12.314 |
| `frame_wall_steady_state` (post-warmup) | 1536 | 3.896 | 6.899 | 6.868 | 8.176 | 8.539 | 12.314 |
| `headless_frame_delta_all_ticks` | 1600 | 0.117 | 6.974 | 6.944 | 6.944 | 7.344 | 133.333 |
| `headless_frame_delta_steady_state` | 1536 | 6.343 | 6.904 | 6.944 | 6.944 | 7.080 | 7.854 |

### Memory & Object Stability

- **OS Resident Set Size (`ps -o rss=`)**: pre-refusal `117808 KiB` -> pre-soak `118288 KiB` -> post-soak `76064 KiB` (`soak_delta=-42224 KiB` / `-41.234 MiB`)
- **Godot Static Memory (all ticks)**: initial `25,208,997 B`, min `25,208,745 B`, max `25,209,245 B`, final `25,208,977 B`, peak `29,887,262 B`
- **Godot Static Memory (steady-state post-warmup)**: initial `25,209,245 B` -> final `25,208,977 B` (`delta=-268 B`)
- **Godot Object / Node / Orphan Monitors**: objects steady-state `1488` -> `1488` (`delta=+0`), nodes `2..2`, orphan nodes `0..0`

| Tick | Static Memory (B) | Object Count | Node Count | Orphan Nodes |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 25,208,997 | 1488 | 2 | 0 |
| 64 | 25,208,977 | 1488 | 2 | 0 |
| 400 | 25,208,977 | 1488 | 2 | 0 |
| 800 | 25,208,977 | 1488 | 2 | 0 |
| 1200 | 25,208,977 | 1488 | 2 | 0 |
| 1600 | 25,208,977 | 1488 | 2 | 0 |

Generated by `scripts/run_soak_and_refusal_probe.py` against `game-track/godot/scenes/soak_and_refusal_probe.tscn` on a disposable staged project copy.
