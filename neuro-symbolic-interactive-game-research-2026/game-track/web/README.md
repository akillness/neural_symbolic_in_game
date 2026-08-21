# The Sealed Lighthouse — Web release lane

Status: **public-safe artifact deployed at
[sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app); browser
smoke passed on 2026-08-21 (desktop 1280×720 and mobile 390×844, curated-art build)**.

This directory holds the reproducible *configuration* for a procedural-only Godot Web build. The
generated `public/` directory is intentionally ignored and is deployed as a static artifact after
local browser verification.

**The exported `index.pck` is not byte-reproducible.** Four consecutive Web exports from the same
clean clone, on one machine with one Godot build, produced four distinct digests and two distinct
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
concept images live outside `res://` and are not shipped; since D-034/D-035 the build ships the six
user-curated, provenance-bound Higgsfield UI art PNGs from `godot/assets/ui/` (AI-generated,
disclosed on the start gate), and the programmatic presentation remains the complete fallback when
those files are absent.

The current ignored `public/` artifact contains 11 top-level files (~44.7 MB), including
`index.html`, JavaScript/audio worklets, `index.pck` (4,817,404 bytes — grew from 1.57 MB with the
curated UI art), `index.wasm`, and the directly readable `NanumGothic-OFL.txt`. Artifact existence
is release engineering evidence only. Local deploy metadata written by `vercel link` (`.env.local`,
`.vercel/`, a generated `.gitignore`) is not part of the shipped artifact and is excluded from that
count.

Browser smoke confirmed (2026-08-21, deployment `dpl_J9STdbrWdiXyZakGuUWR7aD8jip9`):

- the alias serves the latest curated-art public-safe artifact; `index.html`, `index.pck`, and
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

Pointer lock is **not verified** for this deployment. Headless Chromium raised `pointerlockerror`
on a synthetic click, and a Playwriter-driven click in real Chrome produced no pointer-lock request
at all, so neither run is admissible evidence. `LOOK ACTIVE` in the HUD is the game's own state
label, not `document.pointerLockElement`, so it cannot stand in for the browser-level check.
Automation denial is not by itself evidence of a production defect; a human-gesture check is the
open item. Pointer lock, save/reload, representative warmed-frame/input measurements, and a
30-minute soak all remain open, so G6 stays `FIX`. G4, usability, immersion, affect, player
efficacy, and model efficacy remain unassessed.

| Desktop entry | Narrow in-game layout |
| --- | --- |
| ![Deployed desktop start gate](../godot/docs/latest/vercel-start.png) | ![Deployed 390 by 844 in-game layout](../godot/docs/latest/vercel-mobile-in-game.png) |
