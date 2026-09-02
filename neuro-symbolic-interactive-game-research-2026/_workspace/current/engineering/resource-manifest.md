# Engineering resource manifest / 엔지니어링 리소스 매니페스트

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game-programmer
Status: 2026-08-30 English/curated-player artifact deployed and desktop-verified; current mobile, performance, soak, and rollback evidence pending

| Resource | Generator/owner | Runtime role | Current evidence status |
|---|---|---|---|
| `game-track/godot/project.godot` | game-programmer | canonical research project; default remains `res://scenes/headless.tscn` | `[OBSERVED]` preserved for immutable evidence/hash binding |
| `game-track/godot/scenes/main_3d.tscn` | game-programmer | explicit playable 3D entry | `[OBSERVED structure]` public-safe smoke `8/8`, terminal hash `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892` |
| `scripts/game3d/game_3d.gd` | game-programmer | proposal router, save/load, presentation sync, Web start gate, `--smoke`, `--evaluate`, `--shot` | `[OBSERVED 2026-09-02]` `SL-PLAY-EVAL-001` `52/52` (presentation `12/12` incl. `contribution_delta_is_pure_and_names_facts`, `hold_teaches_rule_for_its_gate`, `case_chain_mirrors_committed_snapshot`); public-safe smoke `8/8` includes fall-recovery/state-hash parity |
| `scripts/game3d/player_3d.gd` | game-programmer | third-person movement, mouse look, focus, interaction signal, distance-paced footsteps, below-world physical recovery, presentation-only Idle/Walk blend | `[OBSERVED]` local Web recovery and tracked rig animation; symbolic state unchanged in smoke; browser latency/feel unmeasured |
| `scripts/game3d/golden_path_layout.gd` | game-designer + programmer | single owner of interactable layout, walking-distance proxy, refusal next-affordance mapping | `[OBSERVED]` shared by playable slice and balance probe |
| `scripts/balance_probe_runner.gd` + `scenes/balance_probe.tscn` | QA | deterministic 5-archetype battery over the canonical machine (`SL-BALANCE-PROBE-001`) | `[OBSERVED]` 5/5 rotations pass; scripted engineering only |
| `scripts/run_balance_archetypes.py` | QA + tooling | staged headless probe driver; revalidation; md/svg/json working artifacts | `[OBSERVED]` outputs under `docs/latest/` |
| `game-track/godot/assets/ui/ui-start-key-art-portrait.png` | asset lane (D-043) | 9:16 gate art selected when the layout is narrow-stacked; landscape and flat-gate fallbacks retained | `[OBSERVED]` evaluate reports `start_key_art_orientation: portrait` at narrow, `landscape` at wide; delete-test smoke unchanged |
| `game-track/godot/assets/player/higgsfield-player.glb` + provenance/curation | asset lane (D-050) | tracked public-safe player mesh and presentation-only `Idle`/`Casual_Walk` animation | `[OBSERVED]` 9,677,324 bytes, SHA-256 `d575f8c580fbf0ee7207fbe6c09150c34a93cffc4e69b53b7210c971482ff1dd`; extracted texture 8,311,199 bytes / `37c939772e57d381c77e419b836632bf107b5301bde63f041b40e3094669f739`, byte-identical to the GLB-embedded image; 26 nodes, 15,463 triangles, 24 joints; `--evaluate` reports `higgsfield-tracked`, active `Idle` |
| `scripts/validate_player_asset.py` | asset lane + release | fail-closed GLB/provenance/curation/mesh/skin/clip/root-scale validator | `[OBSERVED]` PASS; Web release regression binds the tracked path and movement-state hook |
| `game-track/godot/assets/rig/` (untracked) + local Mixamo recipe | asset lane (D-046) | optional owner-local fallback only; raw Adobe bytes never redistributed | `[OBSERVED history]` superseded for public runtime by D-050; directory remains excluded from Web staging and Git |
| `game-track/assets/motion/` + `scripts/validate_motion_assets.py` | asset lane + release | motion/rig intake contract (D-039); raw-source redistribution guard | `[OBSERVED]` 0 staged assets; guard PASS |
| `scripts/game3d/world_builder.gd` | game-programmer + visual lane | procedural harbor, instanced dressing, rain, public-safe asset guard, five pooled beat VFX emitters | `[OBSERVED structure]`; frame performance unmeasured |
| `scripts/game3d/narrative_director.gd` | visual lane | six authored presentation beats, tension, cinematics, reduced-motion policy, pooled VFX triggering | `[OBSERVED structure]`; no affect/immersion result |
| `scripts/game3d/interactable_3d.gd` | visual lane | text/icon/color-redundant focus marker | `[OBSERVED structure]`; readability unmeasured |
| `scripts/game3d/harbor_ledger_ui.gd` | UI lane | English wide-column/narrow-stacked layouts, 44 px choice targets, progress, start gate, pointer/audio status, ASCII bracket markers | `[OBSERVED]` current start/tutorial/full route rendered with zero console/page errors; responsive profile invariants pass; current narrow human readability unassessed |
| `scripts/game3d/procedural_audio.gd` | audio lane | deterministic 22,050 Hz ambient/cues, 18 generated streams, max five cue voices, gesture lock, mute and focus-out policy | `[OBSERVED structure]`; no external audio assets; browser playback pending |
| `game-track/godot/assets/models/*.glb` | Blender procedural authoring | five byte-locked harbor prop/landmark meshes, with procedural fallback | `[OBSERVED artifact]` 5/5 size/SHA-256 receipts in `models-manifest.json`; AI generation false; no third-party mesh/texture inputs recorded; source generator was not retained, so exact regeneration is not claimed |
| `game-track/godot/assets/fonts/NanumGothic-Regular.ttf` | upstream Google Fonts/Nanum; Sandoll Communication | bundled Korean/Latin UI and focus-label glyph coverage | `[OBSERVED provenance]` unmodified upstream binary, 2,054,744 bytes, SHA-256 `76f45ef4a6bcff344c837c95a7dcc26e017e38b5846d5ae0cdcb5b86be2e2d31`, SIL OFL 1.1 in adjacent `OFL.txt`, retrieved 2026-08-13 |
| `game-track/godot/data/sealed_lighthouse.json` | game-programmer from approved concept | frozen canonical scenario | `[OBSERVED]` schema-valid carried fixture |
| `game-track/schemas/experimental-game-*.json` | game-programmer | versioned bridge/input/output validation | `[OBSERVED]` schema-valid carried contracts |
| `data/fixtures/experimental-game-*.json` | game-programmer | canonical, duplicate, timeout, and corrupt-save inputs | `[OBSERVED]` schema-valid carried fixtures |
| `engineering/tech-verification/current.json` → selected v5 | immutable evidence pipeline | selected headless and non-headless Cycle 2 evidence | `[OBSERVED carried]` `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`; unchanged |
| `game-track/web/export_presets.cfg` | Web release lane | single-threaded Web preset, extension support disabled, scenario JSON included, `docs/latest/**` excluded | `[OBSERVED]` deployed artifact built from staged copy |
| `scripts/build_godot_web.sh` | Web release lane | copy to `mktemp`, select `main_3d.tscn` only in staged copy, subtract exact sandboxed macOS font/certificate diagnostics, fail on every remaining Godot script/import error, copy OFL, sync artifact | `[OBSERVED]` deployed build passed; player validator and synthetic real-error gate passed; canonical project unchanged |
| `game-track/web/vercel.json` | Web release lane | static security headers without unnecessary cross-origin isolation | `[OBSERVED]` production deployment at `https://sealed-lighthouse-trace-rpg.vercel.app` |
| `game-track/web/public/` | builder output | ignored disposable static artifact for browser validation/deploy | `[OBSERVED production 2026-08-30]` deploy `dpl_Auzz4gjVUcgDcL45EjcRG2HVyoCW`; 11 manifest files / 50,746,755 bytes, 10 runtime files / 50,746,242 bytes; PCK 10,893,980 bytes, SHA-256 `654c1f136de9e15b37be4d697daf863dccf20d1a59287ae86f635d0d7e1a58e7`; includes tracked player; all runtime files returned anonymous 200 and matched local bytes; WASM/OFL MIME correct, configured headers present, `vercel.json` 404. `[OBSERVED history]` 2026-08-21 deploy `dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW`: PCK 5,970,516 bytes / `b9706912…56eb`; non-authoritative |
| `game-track/godot/docs/latest/trace-rpg-gameplay.mp4` | release engineer | retained pre-lens-deck full-route gameplay recording linked from README surfaces | `[OBSERVED]` Compresso-compressed H.264 High, 1280×720, 30 fps, 69.067 s, 5,662,128 bytes, fast-start enabled, SHA-256 `aa374c5aa9d03e0ab2822b83638e4c6645c7c9fda6c07e858051254c244b7044`; exact local build source is byte-identical to predecessor production `dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y`; engineering demonstration only |
| Deployed browser captures | Playwriter | start/in-game presentation receipts | `[OBSERVED]` `docs/latest/vercel-start.png`, `vercel-in-game.png`, `vercel-mobile-start.png`, `vercel-mobile-in-game.png`; local Web inspection retained as `web-start.png`, `web-in-game.png` |
| `_workspace/current/qa/browser-qa.md` | browser QA | current local Web golden-path, save/refresh/load, fall-recovery, and pointer-lock receipt | `[OBSERVED]` full ending reached; local save continuity/recovery pass; pointer lock still unverified |

## Public-safe asset boundary

Within the pending concept lane, the public snapshot retains only
`game-track/assets/concepts/public-exclusion.json`, which binds omitted candidates by ID and
SHA-256. Those original bytes remain pending human rights/style review with
`runtime_eligible: false`. `world_builder.gd` returns no pending candidate texture when the engine
has the `web` feature or receives `--public-safe`; the Web project packages only `res://` resources.
Therefore the public release lane uses the separately curated Higgsfield UI assets and tracked
Higgsfield player GLB over procedural world geometry, materials, VFX, and audio. The player lane is
presentation-only and cannot write save/schema/canonical state. This exclusion does not complete
the pending concept pack's human rights/style review; it prevents that unreviewed pack from entering
the public playable artifact.

## Evidence boundary

Generated Godot `.godot/` cache data and `game-track/web/public/` are not source resources. Latest
working screenshots and `--evaluate` JSON are engineering-only until separately promoted under a
new immutable evidence ID. The selected Cycle 2 v5 packet and its hashes must not be overwritten or
relabelled by Cycle 3 presentation work.

The bundled OFL font and deployment receipts are release resources, not research evidence. The
2026-08-17 production browser smoke reported zero console and page errors; its layout, Korean glyph,
and HTTP/MIME checks ran in a headless browser, and Playwriter was used that day only for the Vercel
device-approval login and one pointer-lock retest.

A prior session recorded that a trusted headless Playwriter click entered pointer lock. That
observation is retained here as prior-session history and failed reproduction on 2026-08-17, so it is
not a current result. Re-tested twice that day: a synthetic click in headless Chromium raised
`pointerlockerror`, and the click in real Chrome via Playwriter produced no pointer-lock request at
all; `document.pointerLockElement` stayed null in both. Pointer lock is therefore `FIX` and not
verified. The HUD label `LOOK ACTIVE` (`시점 잠김`) is the game's own state label and is not evidence of
pointer lock; only `document.pointerLockElement` is. Automation denial is not by itself evidence of a
production defect, so the open item is a human-gesture pointer-lock check on the deployed page.

One extension-connected tab produced `WrongDocumentError` because it did not own the root document;
that is an automation-only limitation, not a deployed-page failure, and it does not imply that any
session confirmed pointer lock.
