# Engineering resource manifest / 엔지니어링 리소스 매니페스트

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game-programmer
Status: public-safe playable deployed and browser-smoke verified; performance/soak evidence pending

| Resource | Generator/owner | Runtime role | Current evidence status |
|---|---|---|---|
| `game-track/godot/project.godot` | game-programmer | canonical research project; default remains `res://scenes/headless.tscn` | `[OBSERVED]` preserved for immutable evidence/hash binding |
| `game-track/godot/scenes/main_3d.tscn` | game-programmer | explicit playable 3D entry | `[OBSERVED structure]` public-safe smoke `8/8`, terminal hash `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892` |
| `scripts/game3d/game_3d.gd` | game-programmer | proposal router, save/load, presentation sync, Web start gate, `--smoke`, `--evaluate`, `--shot` | `[OBSERVED]` `SL-PLAY-EVAL-001` `47/47` and latest working captures |
| `scripts/game3d/player_3d.gd` | game-programmer | third-person movement, mouse look, focus, interaction signal, distance-paced footsteps | `[OBSERVED structure]`; input latency/feel unmeasured |
| `scripts/game3d/world_builder.gd` | game-programmer + visual lane | procedural harbor, instanced dressing, rain, public-safe asset guard, five pooled beat VFX emitters | `[OBSERVED structure]`; frame performance unmeasured |
| `scripts/game3d/narrative_director.gd` | visual lane | six authored presentation beats, tension, cinematics, reduced-motion policy, pooled VFX triggering | `[OBSERVED structure]`; no affect/immersion result |
| `scripts/game3d/interactable_3d.gd` | visual lane | text/icon/color-redundant focus marker | `[OBSERVED structure]`; readability unmeasured |
| `scripts/game3d/harbor_ledger_ui.gd` | UI lane | wide-column/narrow-stacked layouts, 44 px choice targets, progress, start gate, pointer/audio status | `[OBSERVED]` Korean rendering clean at 1280×720 and 390×844 in Playwriter |
| `scripts/game3d/procedural_audio.gd` | audio lane | deterministic 22,050 Hz ambient/cues, four cue voices, gesture lock, mute and focus-out policy | `[OBSERVED structure]`; no external audio assets; browser playback pending |
| `game-track/godot/assets/models/*.glb` | Blender procedural authoring | five byte-locked harbor prop/landmark meshes, with procedural fallback | `[OBSERVED artifact]` 5/5 size/SHA-256 receipts in `models-manifest.json`; AI generation false; no third-party mesh/texture inputs recorded; source generator was not retained, so exact regeneration is not claimed |
| `game-track/godot/assets/fonts/NanumGothic-Regular.ttf` | upstream Google Fonts/Nanum; Sandoll Communication | bundled Korean/Latin UI and focus-label glyph coverage | `[OBSERVED provenance]` unmodified upstream binary, 2,054,744 bytes, SHA-256 `76f45ef4a6bcff344c837c95a7dcc26e017e38b5846d5ae0cdcb5b86be2e2d31`, SIL OFL 1.1 in adjacent `OFL.txt`, retrieved 2026-08-13 |
| `game-track/godot/data/sealed_lighthouse.json` | game-programmer from approved concept | frozen canonical scenario | `[OBSERVED]` schema-valid carried fixture |
| `game-track/schemas/experimental-game-*.json` | game-programmer | versioned bridge/input/output validation | `[OBSERVED]` schema-valid carried contracts |
| `data/fixtures/experimental-game-*.json` | game-programmer | canonical, duplicate, timeout, and corrupt-save inputs | `[OBSERVED]` schema-valid carried fixtures |
| `engineering/tech-verification/current.json` → selected v5 | immutable evidence pipeline | selected headless and non-headless Cycle 2 evidence | `[OBSERVED carried]` `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`; unchanged |
| `game-track/web/export_presets.cfg` | Web release lane | single-threaded Web preset, extension support disabled, scenario JSON included, `docs/latest/**` excluded | `[OBSERVED]` deployed artifact built from staged copy |
| `scripts/build_godot_web.sh` | Web release lane | copy to `mktemp`, select `main_3d.tscn` only in staged copy, fail on Godot script/import errors, copy the OFL notice to the artifact root, sync deploy artifact | `[OBSERVED structure]`; canonical project is not rewritten |
| `game-track/web/vercel.json` | Web release lane | static security headers without unnecessary cross-origin isolation | `[OBSERVED]` production deployment at `https://sealed-lighthouse-trace-rpg.vercel.app` |
| `game-track/web/public/` | builder output | ignored disposable static artifact for browser validation/deploy | `[OBSERVED latest]` 11 top-level files, 41,425,846 bytes; PCK 1,573,072 bytes after excluding `docs/latest/**`; public OFL notice 4,534 bytes; HTML/JS/WASM/PCK/OFL returned 200 and WASM `application/wasm`; non-authoritative |
| Deployed browser captures | Playwriter | start/in-game presentation receipts | `[OBSERVED]` `docs/latest/vercel-start.png`, `vercel-in-game.png`, `vercel-mobile-start.png`, `vercel-mobile-in-game.png`; local Web inspection retained as `web-start.png`, `web-in-game.png` |

## Public-safe asset boundary

The public snapshot retains only `game-track/assets/concepts/public-exclusion.json`, which binds the
omitted generated candidates by ID and SHA-256. The original bytes remain pending human
rights/style review with `runtime_eligible: false`. `world_builder.gd` returns no candidate texture when the engine has the
`web` feature or receives `--public-safe`; the Web project also packages only `res://` resources.
Therefore the public release lane uses procedural geometry, materials, icons, VFX, UI, and audio.
This exclusion does not complete the candidate pack's human rights/style review; it prevents that
unreviewed pack from entering the public playable artifact.

## Evidence boundary

Generated Godot `.godot/` cache data and `game-track/web/public/` are not source resources. Latest
working screenshots and `--evaluate` JSON are engineering-only until separately promoted under a
new immutable evidence ID. The selected Cycle 2 v5 packet and its hashes must not be overwritten or
relabelled by Cycle 3 presentation work.

The bundled OFL font and deployment receipts are release resources, not research evidence. The
Playwriter production smoke reported zero console/page errors and trusted headless pointer lock.
One extension-connected tab produced `WrongDocumentError` because it did not own the root document;
that is an automation-only limitation, not a deployed-page failure.
