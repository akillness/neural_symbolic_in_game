# Experimental slice release readiness / 실험 슬라이스 릴리스 준비도

Run ID: `20260813-sealed-lighthouse-cycle-2`  
Owner: game-programmer  
Current verdict input: `FIX`

| Check | State | Evidence / blocker |
|---|---|---|
| Godot project skeleton and deterministic state machine | DONE | `game-track/godot/` |
| Versioned scenario/fixture/event/save/summary schemas | DONE | static schema test |
| Canonical, duplicate-ID, timeout, corrupt-save fixtures | DONE | `data/fixtures/experimental-game-*.json` |
| Independent Python target-state oracle | DONE | `tests/test_godot_experimental_game.py` |
| Static + conditional engine tests | DONE | current count recorded in `qa/regression-matrix.md` |
| Godot 4.x parsing and execution | DONE | 4.7.1, four retained headless runs |
| Separate non-headless canonical render pass | DONE-PROMOTED-V5 | selected `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`; manifest records macOS display server and `headless: false`; v1--v4 retained superseded |
| Capture source-state, digest, and toolchain binding | DONE-VERIFIED | `sl-rc-001-arrival`--`sl-rc-003-authorized-hint`; source event/state hashes, source file hashes, dimensions, bytes, PNG SHA-256, pixel statistics, capture/validator/schema/lock hashes, and tool versions recorded |
| Primary-track generated-asset exclusion | DONE-MANIFEST | all three capture rows record `generated_assets_in_frame: false`; structured state/text and programmatic engine graphics only |
| Save/load/replay engine evidence | DONE | four matching terminal/load/replay/oracle hashes; corrupt-save load rejected before mutation |
| Duplicate and timeout state-isolation drill | DONE | authored fault summaries, all hard checks true |
| Corrupt-save pre-mutation rejection | DONE | fresh Godot negative fixture and regression assertion |
| Stable bridge-envelope projection | DONE-SCHEMA-ONLY | no live Python authorization transport |
| Frame/request measurements | FIX | observed, but frame p95 failed and sample is tiny |
| 30-minute memory soak and input feedback | OUT OF SCOPE | later interactive cycle |
| Independent game-integrator review | APPROVED-BOUNDED | save, bridge, concepts, event order, ownership, and immutable-capture findings fixed and reverified |
| Paper engine-path promotion | LIMITED | engine-local policy-mirror wording only |
| RQ1–RQ5 efficacy promotion | PROHIBITED | no live-model, participant, or independent-oracle result |
| G4/G6 promotion from screenshots | PROHIBITED | static render evidence does not measure immersion, input latency, frame p95, long-frame rate, or memory soak |

Release here means a reviewable experimental artifact, not a polished game or production service.
The deterministic headless slice executed and retained reproducible artifacts. Cycle 2 adds only a
separately executed non-headless presentation packet tied to that authored fixture; it does not
replace the conformance trace. Independent review identified and drove save-integrity,
bridge-projection, asset-provenance, and documentation fixes. Live cross-runtime authorization,
G4, G6, and every efficacy claim remain unready.
