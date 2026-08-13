# The Sealed Lighthouse — Web release lane

Status: **public-safe artifact deployed at
[sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app); browser
smoke passed on 2026-08-14**.

This directory holds the reproducible configuration for a procedural-only Godot Web build. The
generated `public/` directory is intentionally ignored and is deployed as a static artifact after
local browser verification.

The builder copies `game-track/godot/` to a disposable directory and selects `main_3d.tscn` only in
that copy. The canonical research project continues to launch `headless.tscn`, so the immutable
render-evidence binding to `project.godot` does not drift.

```bash
./scripts/build_godot_web.sh
```

The Web preset is single-threaded and has extension support disabled. It therefore does not require
cross-origin isolation. It includes the authored scenario JSON explicitly. Pending-review generated
concept images live outside `res://` and are not shipped; the public build uses the programmatic
presentation fallback.

The current ignored `public/` artifact contains 11 top-level files and 41,426,198 bytes, including
`index.html`, JavaScript/audio worklets, `index.pck`, `index.wasm`, and the directly readable
`NanumGothic-OFL.txt`. Artifact existence is release engineering evidence only.

Playwriter browser smoke confirmed:

- production deployment `dpl_9RFPtxe7iZha8HWEawJzZu8WceED` serves the 2026-08-14 latest-only
  public-safe artifact;
- HTML, JS, WASM, and PCK returned `200`; WASM used `application/wasm`.
- Korean glyphs rendered from the bundled OFL Nanum Gothic font.
- [`NanumGothic-OFL.txt`](https://sealed-lighthouse-trace-rpg.vercel.app/NanumGothic-OFL.txt)
  returned `200 text/plain`, 4,534 bytes, and SHA-256
  `eeacf16032901d0ed0456876ec77b8f0fda6b3fecec7d972f8543eb602e6c30f`.
- the deployed PCK is 1,573,424 bytes, has deployment-receipt SHA-256
  `6e6500e79b48260ae5d6f532133ff664094ccc4e3a98116718a60264aca0b7b1`, and excludes
  `docs/latest/**` plus every pending concept pack;
- the start gate and in-game ledger remained readable at 1280×720 and 390×844;
- a trusted Playwriter click entered pointer lock in headless Chromium;
- console and page-error counts were zero before and after entry.

The extension-connected inspection tab cannot own the root document for pointer lock and produced
one automation-only `WrongDocumentError`; the dedicated headless Playwriter sessions succeeded.
Save/reload, representative warmed-frame/input measurements, and a 30-minute soak remain open, so
G6 stays `FIX`. G4, usability, immersion, affect, player efficacy, and model efficacy remain
unassessed.

| Desktop entry | Narrow in-game layout |
| --- | --- |
| ![Deployed desktop start gate](../godot/docs/latest/vercel-start.png) | ![Deployed 390 by 844 in-game layout](../godot/docs/latest/vercel-mobile-in-game.png) |
