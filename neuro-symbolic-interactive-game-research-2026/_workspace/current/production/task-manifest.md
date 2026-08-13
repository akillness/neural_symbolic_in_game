# Task Manifest — Cycle 3

Run ID: `20260813-sealed-lighthouse-cycle-3`
Current stage: Stage 1 re-entry — playable presentation/Web release engineering
Operating mode: public-safe procedural runtime; immutable research evidence remains separate
Next beat: browser save/reload, representative warmed frame/input measurements, 30-minute soak, and
final aggregate regression

| task | owner | stage.phase | artifact | gate | status | next evidence |
|---|---|---|---|---|---|---|
| Re-enter Stage 1 and freeze Cycle 3 boundary | director | 1.intake | `intake/production-brief.md`, this manifest | governance | done | director review |
| Correct episode promise | designer | 1.design | `design/concept.md` | G1/G7 | done | audit public strings |
| Preserve sealed lighthouse; restore harbor signal/earn tide route | designer + lore QA | 1.design | concept, presentation, content-worldview audit | G1 | done-in-docs | browser-visible content audit |
| Build public-safe procedural harbor and pooled VFX | visual lane | 1.presentation | `world_builder.gd`, `narrative_director.gd`, `interactable_3d.gd` | G4/G6 | implemented-structure | screenshots + frame measurements |
| Build playable movement/focus boundary | programmer | 1.systems | `player_3d.gd`, `game_3d.gd` | G6/G7 | implemented-structure | browser input probe |
| Build responsive ledger and browser start gate | UI lane | 1.presentation | `harbor_ledger_ui.gd`, `game_3d.gd` | G1/G4/G6 | verified-1280x720-and-390x844 | human G4 study |
| Build gesture-gated procedural audio | audio lane | 1.presentation | `procedural_audio.gd` | G4/G6 | implemented-structure | clean-browser unlock/mute/focus test |
| Enforce generated-asset public exclusion | programmer + release | 1.resources | public-safe guard, Web staging | provenance | implemented-structure | inspect exported artifact |
| Add disposable single-threaded Web export | release engineer | 1.release | `game-track/web/**`, `scripts/build_godot_web.sh` | G6/release | implemented-structure | clean build receipt |
| Add presentation evaluation and latest shot modes | programmer + QA | 1.verify | `docs/latest/evaluation-matrix.*`, four PNGs | engineering | done-4-fixtures-47-of-47-four-shots | README/browser review |
| Execute public-safe 3D smoke | QA | 1.verify | same proposal router as play | G7 engineering | observed-8-of-8 | preserve final command receipt |
| Execute aggregate regression | QA | 1.verify | `./scripts/validate_game_track.sh` | regression | observed-40-tests-44-subtests | rerun after integration |
| Bundle Korean Web font with license | release engineer | 1.resources | `assets/fonts/NanumGothic-Regular.ttf`, `OFL.txt`, provenance README, public `NanumGothic-OFL.txt` | provenance | done-OFL-pinned-and-public-hash | retain license with releases |
| Build staged Web artifact | release engineer | 1.release | ignored `game-track/web/public/` | release engineering | done-11-files-41425846-bytes | rebuild for future releases |
| Verify deployed Web in Playwriter | QA + release | 1.verify | six `docs/latest/*web*`/`*vercel*` captures | G1/G6/release | done-bounded-desktop-mobile-zero-errors | save/reload + performance |
| Measure Web performance and 30-minute soak | QA | 1.verify | browser performance report | G6 | pending | warmed p95, long frames, input, memory |
| Conduct approved human presentation study | independent evaluator | later study | participant packet | G4 | not-started | immersion/readability/usability data |
| Deploy public-safe static artifact | release engineer | 1.release | `https://sealed-lighthouse-trace-rpg.vercel.app` | release | done-production-http-browser-smoke | monitor/rollback drill |
| Close Cycle 3 | director + independent reviewers | 1.review | `retrospectives/cycle-3-retrospective.md` | release | blocked-on-pending-evidence | final verdict |

## Latest observed engineering receipts

- `godot --headless --path game-track/godot res://scenes/main_3d.tscn -- --smoke --public-safe`
  → `8/8`, terminal state SHA-256
  `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`.
- `./scripts/validate_game_track.sh` → `40 tests, 44 subtests` in the current Cycle 3 session.
- `scripts/run_playable_evaluation.py` → `SL-PLAY-EVAL-001`: fixtures `4/4`, fixture checks
  `40/40`, presentation checks `7/7`, combined `47/47`; terminal SHA-256 unchanged.
- Four `docs/latest/*.png` working captures are 1280×720 and SHA-256 registered in the matrix.
- `game-track/web/public/` contains 11 top-level build files and 41,426,198 bytes; the latest PCK is
  1,573,424 bytes after `docs/latest/**` exclusion. The public 4,534-byte OFL notice hash matches the
  source license. The artifact remains ignored and non-authoritative.
- Vercel production: `https://sealed-lighthouse-trace-rpg.vercel.app`; HTML/JS/WASM/PCK/OFL returned
  200, with WASM served as `application/wasm` and OFL as `text/plain`.
- Playwriter: clean Korean rendering at 1280×720 and 390×844; trusted headless pointer lock; zero
  console and page errors. Retained paths: `docs/latest/vercel-start.png`, `vercel-in-game.png`,
  `vercel-mobile-start.png`, `vercel-mobile-in-game.png`, `web-start.png`, and `web-in-game.png`.
- Nanum Gothic Regular is bundled under SIL OFL 1.1 with pinned source, license, size, and SHA-256.

These receipts are engineering conformance only and do not modify selected immutable v5 or upgrade
G4/G6. The extension-connected inspection tab's `WrongDocumentError` is automation-only; dedicated
trusted headless Playwriter sessions passed. G4 is unassessed and G6 remains `FIX` pending
save/reload, warmed performance/input, and the 30-minute soak.

Refresh rule: any lane, generator, authority boundary, entry point, Web export behavior, gate,
regression command, or evidence-promotion boundary change updates this manifest and `CLAUDE.md` in
the same change set.

Latest rule refresh: 2026-08-13, decisions `D-027`–`D-033`.
