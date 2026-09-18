# Paper/game fact-check release — 2026-09-06

[OBSERVED] Content audit, integrated verification, production deployment and remote byte comparison are complete.

- Bounded source audit: S02/S44/S52/S54/S55/S56, exact primary metadata URLs in `research/academic-pipeline/stage-05-citation-verification.json`; retained full audit baseline 55 references / 48 VERIFIED / 7 PREPRINT / 22 historical rate-limited lookups. This pass does not re-date every source.
- Both manuscripts narrow the S44 mechanism-absence claim and S55 narrative-coherence extrapolation. EN/KO PDFs remain 8 pages. `make -C paper/latex check` passes; forced builds use the Makefile's source-date environment.
- Dashboard mappings include `UNKNOWN_ACTOR` and `NPC_DOES_NOT_KNOW_FACT`; composite gates count each known family once; reported hold counts are no longer shown as a fabricated unchanged-state success fraction. The public observer remains one-directional.
- Release staging always rebuilds current Godot sources on a disposable copy, bundles both PDFs, rejects unknown arguments, and preflights missing PDFs. Three staging tests pass without external writes.
- Full Pytest: 188 passed, 83 subtests passed. Unit discovery: 144 passed. The initial CI-equivalent pass found one unused `noqa` in the new citation test; it was removed and all Ruff checks pass. The final full CI-equivalent run is recorded below.
- Original source `game-track/godot/project.godot` remains SHA-256 `2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd`.

[INFERENCE] These corrections improve claim precision and observer accounting. They do not establish model efficacy, human benefit, general safety, narrative quality, G4, or G6.

[OBSERVED] Another session's `.git/game-studio.lock` remains present. This release session does not stage, commit, push, remove that lock, or overwrite its D-069 changes. Production deployment was explicitly requested and uses the verified working artifacts.

## Deployment and browser receipt

Production deployment `dpl_2KYaaLu6PWuwaFZ4RxFrFkA6C4RT` is READY at
https://sealed-lighthouse-trace-rpg.vercel.app/ (root redirects to `/dashboard/`; the game remains
at `/public/`; manuscripts are `/paper/en.pdf` and `/paper/ko.pdf`). All 16 public files match
the verified local bytes: 10 game files, 4 dashboard files and 2 PDFs, totalling 53,567,287 bytes.
Both PDFs return `application/pdf`; WASM returns `application/wasm`; security headers and old
`/index.html` redirect are present; `/vercel.json` returns 404.

Local and production Chromium load the dashboard and game, start an actual session with a
64-digit state hash, expose both paper links, and have no horizontal page overflow at
390×844. Synthetic observer fixtures verify the source guard, composite gate counting,
deduplication and unknown-family exclusion; these fixtures are not gameplay or research
observations. One headless pointer-lock diagnostic remains recorded on each run, with zero
other console/page errors. The mobile game frame is only 185 px high; this check establishes
page layout, not mobile game readability. Human pointer-lock/audio, mobile game readability,
performance and soak evidence remain FIX.

Final `verify_like_ci.sh`: all steps pass (144 unittest cases, Ruff, project/source integrity,
crosswalk, visual regeneration, offline experiment, harness, 51 game tests / 48 subtests,
deep-research, survey and wiki). Full Pytest: 188 tests / 83 subtests pass. The authoritative
Graphify graph was refreshed with the supported script; the prompt graph remains separate.

Retained receipts and captures: `releases/2026-09-06/production-http.json`,
`production-browser.json`, `local-browser.json`, `production-{desktop,started,mobile}.png`,
`ci-final.log`, and `pytest.log`. These are current engineering receipts, not promoted research
captures or human evaluation results.
