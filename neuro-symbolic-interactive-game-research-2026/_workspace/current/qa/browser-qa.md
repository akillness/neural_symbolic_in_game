# Browser QA Receipt — local and production Web build

Date: 2026-08-30 KST
Surfaces: predecessor disposable local Web export at `http://127.0.0.1:18941/`; current production
`dpl_Auzz4gjVUcgDcL45EjcRG2HVyoCW` at `https://sealed-lighthouse-trace-rpg.vercel.app`
Bundle receipt: 11 manifest files / 50,746,755 bytes; 10 public runtime files / 50,746,242 bytes;
`index.pck` 10,893,980 bytes, SHA-256 `654c1f136de9e15b37be4d697daf863dccf20d1a59287ae86f635d0d7e1a58e7`
Claim boundary: engineering QA only. Not G4, G6, usability, immersion, affect, fun, or efficacy evidence.

## Verified

- Production reached `READY`; all 10 public runtime files returned anonymous `200` responses and
  matched local bytes. `vercel.json` returned `404`; WASM used `application/wasm`, the OFL notice
  used `text/plain`, and `nosniff`, strict referrer, plus camera/microphone/geolocation-denial
  headers were present.
- Production desktop smoke completed the start gate, all three tutorial pages, and the in-game
  transition with zero console errors and zero page errors. The current deployment was not verified
  at 390×844, and pointer lock was not asserted.

- In the predecessor local Web build, the English start gate and all three tutorial pages completed
  in the browser. The final tutorial page rendered
  `Observe -> inspect -> propose -> validate -> repair -> commit.` without missing glyphs.
- That predecessor local build completed the full authored route: Mira dialogue and
  forbidden-disclosure refusal → signal-lens pickup → lamp-mount install → authorized tide hint →
  tide marks → ending panel. The retained 69.067 s
  `game-track/godot/docs/latest/trace-rpg-gameplay.mp4` records the predecessor local artifact
  deployed as `dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y` before the lens-approach-deck change and was
  verified as H.264 High, 1280×720, 30 fps, 5,662,128 bytes, fast-start enabled, SHA-256
  `aa374c5aa9d03e0ab2822b83638e4c6645c7c9fda6c07e858051254c244b7044`.
- Because the sandbox's dummy renderer cannot produce `--shot` textures and a windowed Godot capture aborts, the four latest working PNGs were regenerated from a disposable Web build with an untracked `?shot-stage=` hook, captured at 2× device pixel ratio, then downsampled to exact 1280×720. The tracked runtime has no capture-only hook.
- Falling below `y=-3.0` returned the player to `(0.0, 0.2, 2.0)`. The extended public-safe smoke independently asserts that the symbolic state hash is unchanged by recovery and still reports `8/8`.
- DEF-021 is implementation-closed in the current deployment: collision-bearing `LensApproachDeck`
  contains the unchanged `GoldenPathLayout` anchor, overlaps the quay, and wraps the lamp-store
  wall. The disposable-copy 8/8 smoke verifies its enabled matching `BoxShape3D`; owner navigation
  remains unmeasured and does not close G4/G6.
- Save/reload survived a full page refresh. After lens pickup, `F5` displayed state hash prefix `19b474dcc12a…`; the browser exposed IndexedDB `/userfs`. After a 6.5 s sync wait, reload, start, and `F9`, the game displayed `LOADED · Integrity check passed.`, restored the lens inventory, and restored the lamp-mount objective.
- The tracked 9,677,324-byte Higgsfield player GLB loaded in the public-safe Web build; `--evaluate` reported `player_rig_active: true`, source `higgsfield-tracked`, and active animation `Idle`, with `Idle` and `Casual_Walk` present.
- The local build completed with the exact macOS font/certificate diagnostics filtered before the unchanged fail-closed `SCRIPT ERROR|ERROR:` gate. A synthetic real error still fails the gate.
- The final bundle reload and tutorial check produced zero browser console errors and zero page errors.

## Open findings

- Pointer lock did not engage in automation. After start and after `Esc` followed by a canvas click, `document.pointerLockElement` remained `null` while the active element was `CANVAS`. Horizontal mouse moves changed only about `0.10–0.15%` of sampled pixels, consistent with rain motion rather than a camera turn. This remains an unverified human-gesture item, not proof of a production defect.
- Audio unlock/focus behavior, warmed frame p95, long-frame rate, browser input latency, 30-minute soak, and rollback drill were not measured. The single `3.53 ms` engine-local input-feedback sample is wiring evidence only.

## Evidence pointers

- Recovery implementation: `game-track/godot/scripts/game3d/player_3d.gd`
- Recovery smoke: `game-track/godot/scripts/game3d/game_3d.gd`
- Recovery regression: `tests/test_godot_web_release.py`
- Lens approach geometry: `game-track/godot/scripts/game3d/world_builder.gd`,
  `game-track/godot/scripts/game3d/game_3d.gd`
- Web fail-closed filter: `scripts/build_godot_web.sh`
- Player asset validator: `scripts/validate_player_asset.py`
- Current engineering receipts: `game-track/godot/docs/latest/presentation-evaluation.json`, `game-track/godot/docs/latest/evaluation-matrix.json`, `game-track/godot/docs/latest/balance-archetypes.json`, `game-track/godot/docs/latest/trace-rpg-gameplay.mp4`
- Current working PNG hashes (refreshed 2026-09-03 through `scripts/run_playable_evaluation.py --capture`: native windowed `--shot` on a disposable staged copy, each PNG bound by a `<stage>.shot.json` receipt with the canonical state hash before/after the stage): arrival `1960493fdb2f3da263c1290faef569a1ad6b1d58d33e751f66915597b0a15703`; refusal `41c69c36e1e8913885d48b5aa730909b4eedcb278ce5e0a3d0a3fb31c8dc4105`; authorized hint `f068f274c608d8cf4ab9f4f8c226702b02bf01240c0179e23c4fbe7d76402122`; ending `b61eb311e1040b57eb4e6c52e6348ada725f43489486272d51cfc9937b38adaf`. The 2026-09-02 Web-stage hashes (arrival `a8174d47…`, refusal `d1c2fb6f…`, authorized hint `87ec7d60…`, ending `792aa442…`) and the 2026-08-30 hashes (arrival `0516c561…`, refusal `2041fa1e…`, authorized hint `cc5e766a…`, ending `4c312110…`) are superseded. The manuscripts' Fig. 3 uses a frozen copy of the refusal/authorized-hint/ending captures under `paper/latex/captures/playable-readout-20260903/`, illustration only.
- 2026-09-02 disposable Web stage (D-062): the `refusal` stage rendered `[V] GATE DISCLOSURE | state unchanged`, `[N] NEXT VALID ENTRY: ...`, and `[V] RULE LEARNED | DISCLOSURE: Some facts stay sealed for good; the ledger never records them.` with HUD `CASE CHAIN | LENS [ ] > MOUNT [ ] > LEAD [ ] | RULES LEARNED 1 | DISCLOSURE`; the `authorized_hint` stage rendered `CONTRIBUTION #1..#3` (`STAGE 0>1`, `STAGE 1>2`, `STAGE 2`, `CHAIN 1/3..3/3`) and `UNLOCKED` lines after each `ENTRY #N | COMMITTED`; the `ending` stage rendered the two-part receipt (`INVESTIGATOR'S CONTRIBUTION` block, `RULES LEARNED 0 | none`, then the technical receipt). Rendering evidence only; not usability, fun, or G4 evidence.

## 2026-09-03 production dashboard deployment (D-068)

- `dpl_G58qo7siKGUP2E55RH2Xxj8pPgtF` READY at `https://sealed-lighthouse-trace-rpg.vercel.app`: `/` → 307 → `/dashboard/`; `/index.html` → 307 → `/public/index.html`; `/dashboard/`, `/dashboard/dashboard.js`, `/dashboard/paper-reference.json`, `/public/index.html`, `/public/index.js`, `/public/index.wasm` (`application/wasm`), `/public/index.pck` all anonymous 200 and byte-identical to the staged site (10 runtime files / 50,754,386 bytes; PCK `b92af65d854d921440cd8b748591ce13032de989f3697e6b6648c855b9688075`); `/vercel.json` and the old root `/index.js` 404. Configured headers present (`X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`).
- Headless Chromium 1440×900: dashboard loaded, embedded game reached the start gate, clicking BEGIN INVESTIGATION started the episode and the header pill read `live · receiving game events` with `state f488d9c4…812c`; zero 4xx responses, zero console/page errors after the favicon link was added. 390×844: no horizontal overflow after the KPI cards wrap to three columns. Captures: `docs/latest/vercel-dashboard.png`, `docs/latest/vercel-dashboard-mobile.png`. Engineering demonstration only; not usability, G4, or G6 evidence.
