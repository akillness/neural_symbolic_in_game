# The Sealed Lighthouse — Web release lane

Status: **production deployment `dpl_2mcMB3qomEKPyUj2oBtXVLzLXraN` is `READY` and live at
[sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app)**.
Its deployment-scoped URL is
[`sealed-lighthouse-trace-bqbsk7j00-akillness-projects.vercel.app`](https://sealed-lighthouse-trace-bqbsk7j00-akillness-projects.vercel.app).

This directory holds the reproducible *configuration* for a public-safe Godot Web build with a
procedural world and separately curated UI/player assets. The
generated `public/` directory is intentionally ignored and is deployed as a static artifact after
local browser verification.

**The exported `index.pck` is not byte-reproducible.** A prior four-export check on an earlier build
from the same clean clone, on one machine with one Godot build, produced four distinct digests and two distinct
sizes (1,573,408 and 1,573,424 bytes; a 16-byte swing). The `index.html` shipped alongside embeds
the observed pck size, so it varies with it, while `index.wasm` and the bundled font stay stable.
Godot's packer is the source of the variance, not the tracked tree or the build script.

Two consequences worth stating plainly. A pck digest recorded below is a **receipt for one specific
deployed artifact**, not a target a rebuild can be expected to hit; do not treat a mismatch as
evidence of tampering or drift. And release verification for this bundle rests on browser smoke
evidence plus the deterministic research artifacts, not on byte-equality of the pck.

The builder copies `game-track/godot/` to a disposable directory and selects `main_3d.tscn` only in
that copy. The canonical research project continues to launch `headless.tscn`, so the immutable
render-evidence binding to `project.godot` does not drift.

```bash
./scripts/build_godot_web.sh
```

The Web preset is single-threaded and has extension support disabled. It therefore does not require
cross-origin isolation. It includes the authored scenario JSON explicitly. Pending-review generated
concept images live outside `res://` and are not shipped. The build ships the separately curated,
provenance-bound Higgsfield UI lane from `godot/assets/ui/` and, since D-050, the validated tracked
`godot/assets/player/higgsfield-player.glb` with `Idle`/`Casual_Walk`. AI use is disclosed on the
start gate. Deleting optional UI PNGs leaves the programmatic world/UI fallback playable; player
visuals and clip state stay outside canonical state and saves.

The current ignored 2026-08-30 `public/` artifact contains 11 top-level files / 50,745,203 bytes,
including `index.html`, JavaScript/audio worklets, `index.pck` (10,892,428 bytes, SHA-256
`de670404769bf86c8eac0e8f4aa57957e1bef4fde6dc9d7fc4daa605376c31ba`), `index.wasm`, and the
directly readable `NanumGothic-OFL.txt`. It includes the tracked player and is deployed. All 10
runtime files fetched from the production alias returned `200` and were byte-identical to the local
artifact; `vercel.json` is deployment configuration and correctly returns `404` as a public route.
The live response retained `nosniff`, strict referrer, and camera/microphone/geolocation-denial
headers. Local deploy metadata written by `vercel link` (`.env.local`, `.vercel/`, a generated
`.gitignore`) is not part of the shipped artifact and is excluded from that count. Local browser QA
completed the English start and three-page ASCII-safe tutorial, the full authored ending path,
refresh-persistent save/load, and state-isolated fall recovery. Production desktop smoke completed
start → in-game → Field Guide with zero console/page errors. The latest engine receipt reports the
tracked rig active with `Idle` and `Casual_Walk` available.

Prior 2026-08-21 deployment `dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW` (ritual + texture build): alias
html/pck/wasm fetched back byte-identical (`index.pck` SHA-256
`b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb`); start gate, intro cinematic,
tutorial folio, diegetic ledger voice with stamps, and objective flow verified at 1280×720 with
zero unexpected console/page errors; a 32 s golden-path screencast was retained as
`godot/docs/latest/golden-path.gif` (engineering working artifact only).

Historical browser smoke confirmed on 2026-08-21 for deployment
`dpl_J9STdbrWdiXyZakGuUWR7aD8jip9`:

- at that time, the alias served the curated-art public-safe artifact; `index.html`, `index.pck`, and
  `index.wasm` fetched from the alias were byte-identical to the locally verified build
  (`index.pck` SHA-256 `e875df7c75c17b98a1372b72418129c6aa3124a0c7a1fe127da25fd6a46d4344`);
- all shipped files returned `200`; WASM used `application/wasm`, the JS entry plus both audio
  worklets used `application/javascript`, and the OFL notice `text/plain`;
- the Higgsfield key-art start gate rendered with its storm-ink scrim, readable Korean/English
  card text, and the AI-use disclosure footer at 1280×720 and 390×844;
- entering from the start gate played the intro cinematic and advanced the HUD to `시점 잠김 ·
  LOOK ACTIVE` with `AUDIO ON`;
- the first-session tutorial folio opened with the curated vignette; the 390×844 narrow layout
  stacks the vignette above full-width text (fixed this cycle after the first deploy showed a
  squeezed text column);
- the ledger updated to the concrete Mira objective with beacon hint; the brass-framed Mira
  portrait rendered in dialogue;
- unexpected console and page errors were zero on both viewports; the single logged
  `WrongDocumentError` on synthetic entry is the known automation-only pointer-lock artifact.
- Korean glyphs rendered from the bundled OFL Nanum Gothic font;
  [`NanumGothic-OFL.txt`](https://sealed-lighthouse-trace-rpg.vercel.app/NanumGothic-OFL.txt)
  returned `200 text/plain`.

Pointer lock is **not verified** for the current deployment. Retained 2026-08-21 automation raised
`pointerlockerror` on a synthetic click, while a Playwriter-driven click produced no pointer-lock
request. The 2026-08-30 desktop smoke did not assert pointer lock. `LOOK ACTIVE` in the HUD is the
game's own state label, not `document.pointerLockElement`, so it cannot stand in for the browser-level
check. Automation denial is not by itself evidence of a production defect; a human-gesture check is
the open item. Local refresh-persistent save/reload passes on the current artifact. Production
desktop re-verification passed, but production save/reload, current 390×844 mobile verification,
pointer lock, representative warmed-frame/input measurements, a 30-minute soak, and a rollback
drill remain open, so G6 stays `FIX`. G4, usability, immersion, affect, player efficacy, and model
efficacy remain unassessed.

| Retained desktop entry | Retained narrow in-game layout |
| --- | --- |
| ![Retained desktop start gate](../godot/docs/latest/vercel-start.png) | ![Retained 390 by 844 in-game layout](../godot/docs/latest/vercel-mobile-in-game.png) |
