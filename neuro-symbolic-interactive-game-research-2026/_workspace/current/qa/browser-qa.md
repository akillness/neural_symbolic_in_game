# Browser QA Receipt — local and production Web build

Date: 2026-08-30 KST
Surfaces: disposable local Web export at `http://127.0.0.1:18941/`; production deployment
`dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y` at `https://sealed-lighthouse-trace-rpg.vercel.app`
Bundle receipt: 11 manifest files / 50,745,187 bytes; 10 public runtime files / 50,744,674 bytes;
`index.pck` 10,892,412 bytes, SHA-256 `29e3d8b6b898482fb1a7979966cf1acec88caf7578a26398e889fc7af10f8f76`
Claim boundary: engineering QA only. Not G4, G6, usability, immersion, affect, fun, or efficacy evidence.

## Verified

- Production reached `READY`; all 10 public runtime files returned `200` and matched local bytes.
  `vercel.json` was consumed as deployment configuration and correctly returned `404` as a public
  route. WASM used `application/wasm`; `nosniff`, strict referrer, and
  camera/microphone/geolocation-denial headers were present.
- Production desktop smoke completed the start gate, in-game transition, and `[T]` Field Guide with
  zero console errors and zero page errors. The current deployment was not verified at 390×844, and
  pointer lock was not asserted.

- The English start gate and all three tutorial pages completed in the browser. The final tutorial page rendered `Observe -> inspect -> propose -> validate -> repair -> commit.` without missing glyphs.
- The full authored route completed: Mira dialogue and forbidden-disclosure refusal → signal-lens pickup → lamp-mount install → authorized tide hint → tide marks → ending panel. The current 69.067 s
  `game-track/godot/docs/latest/trace-rpg-gameplay.mp4` records that exact local artifact and was
  verified as H.264 High, 1280×720, 30 fps, 5,662,128 bytes, fast-start enabled, SHA-256
  `aa374c5aa9d03e0ab2822b83638e4c6645c7c9fda6c07e858051254c244b7044`.
- Because the sandbox's dummy renderer cannot produce `--shot` textures and a windowed Godot capture aborts, the four latest working PNGs were regenerated from a disposable Web build with an untracked `?shot-stage=` hook, captured at 2× device pixel ratio, then downsampled to exact 1280×720. The tracked runtime has no capture-only hook.
- Falling below `y=-3.0` returned the player to `(0.0, 0.2, 2.0)`. The extended public-safe smoke independently asserts that the symbolic state hash is unchanged by recovery and still reports `8/8`.
- Save/reload survived a full page refresh. After lens pickup, `F5` displayed state hash prefix `19b474dcc12a…`; the browser exposed IndexedDB `/userfs`. After a 6.5 s sync wait, reload, start, and `F9`, the game displayed `LOADED · Integrity check passed.`, restored the lens inventory, and restored the lamp-mount objective.
- The tracked 9,677,324-byte Higgsfield player GLB loaded in the public-safe Web build; `--evaluate` reported `player_rig_active: true`, source `higgsfield-tracked`, and active animation `Idle`, with `Idle` and `Casual_Walk` present.
- The local build completed with the exact macOS font/certificate diagnostics filtered before the unchanged fail-closed `SCRIPT ERROR|ERROR:` gate. A synthetic real error still fails the gate.
- The final bundle reload and tutorial check produced zero browser console errors and zero page errors.

## Open findings

- Pointer lock did not engage in automation. After start and after `Esc` followed by a canvas click, `document.pointerLockElement` remained `null` while the active element was `CANVAS`. Horizontal mouse moves changed only about `0.10–0.15%` of sampled pixels, consistent with rain motion rather than a camera turn. This remains an unverified human-gesture item, not proof of a production defect.
- The signal-lens anchor is at `(-11, 1, 1)` with radius `2.8`, beyond the dock-plank edge near `x=-9`. The route is completable through the lamp-shop front door, but normal approaches repeatedly caused a fall before focus. Fall recovery removes the hard lock; the narrow affordance remains an S3 traversal/usability issue for the next layout pass.
- Audio unlock/focus behavior, warmed frame p95, long-frame rate, browser input latency, 30-minute soak, and rollback drill were not measured. The single `3.53 ms` engine-local input-feedback sample is wiring evidence only.

## Evidence pointers

- Recovery implementation: `game-track/godot/scripts/game3d/player_3d.gd`
- Recovery smoke: `game-track/godot/scripts/game3d/game_3d.gd`
- Recovery regression: `tests/test_godot_web_release.py`
- Web fail-closed filter: `scripts/build_godot_web.sh`
- Player asset validator: `scripts/validate_player_asset.py`
- Current engineering receipts: `game-track/godot/docs/latest/presentation-evaluation.json`, `game-track/godot/docs/latest/evaluation-matrix.json`, `game-track/godot/docs/latest/balance-archetypes.json`, `game-track/godot/docs/latest/trace-rpg-gameplay.mp4`
- Current working PNG hashes: arrival `0516c561fee938e62ae5279f1facdb85d39248cfb9b522c800e74bc953d2f9d8`; refusal `2041fa1e1dd8e5f5d62373cf25c0462530b40e430f649a87c18f8ebfa1ab0b61`; authorized hint `cc5e766adbf0a8eb47e519b61fa2032fd5fac268e3d3be845aa711b6f00f37fe`; ending `4c312110e04ed342c3ab7961120b07873a6d97a39f446f6a99ddb839d4622e9f`.
