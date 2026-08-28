# Task Manifest — Cycle 3 (+ 2026-08-28 밸런스·텔레메트리 확장 패스)

Run ID: `20260813-sealed-lighthouse-cycle-3`
Current stage: Stage 1 re-entry — playable presentation/Web release engineering; 2026-08-28
balance/telemetry/motion-lane extension recorded as D-037–D-039
Operating mode: public-safe procedural runtime; immutable research evidence remains separate
Next beat: browser save/reload, representative warmed frame/input measurements, 30-minute soak,
non-headless capture refresh (GUI session), and final aggregate regression

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
| Build staged Web artifact | release engineer | 1.release | ignored `game-track/web/public/` | release engineering | done-11-files-41426182-bytes | rebuild for future releases |
| Verify deployed Web in browser | QA + release | 1.verify | six `docs/latest/*web*`/`*vercel*` captures | G1/G6/release | done-bounded-desktop-mobile-zero-errors | pointer lock + save/reload + performance |
| Measure Web performance and 30-minute soak | QA | 1.verify | browser performance report | G6 | pending | warmed p95, long frames, input, memory |
| Conduct approved human presentation study | independent evaluator | later study | participant packet | G4 | not-started | immersion/readability/usability data |
| Deploy public-safe static artifact | release engineer | 1.release | `https://sealed-lighthouse-trace-rpg.vercel.app` | release | done-production-http-browser-smoke | monitor/rollback drill |
| Deepen weather/cinematic 연출 (tension weather arc, lightning, harbor micro-motion, intro FOV, ending beam) | visual lane (subagent WorldFeel) | 1.presentation | `world_builder.gd`, `narrative_director.gd` | G1/G4 | done-2026-08-21-smoke-and-eval-green | human presentation study |
| Deepen core-loop feel/balance (movement accel, focus affordance, golden-path retune, escalating commits, 7 stingers + ambience) | programmer + audio lane (subagent LoopFeel) | 1.systems | `player_3d.gd`, `interactable_3d.gd`, `game_3d.gd`, `procedural_audio.gd` | G1/G7 | done-2026-08-21-smoke-and-eval-green | human presentation study |
| Generate Higgsfield UI art pack (6 assets + provenance) | asset lane (subagent HiggsfieldGen) | 1.resources | `game-track/assets/generated/higgsfield-ui-v1/` | provenance (D-034) | done-6-of-6-accepted-2-retries | keep staging immutable |
| Curate + integrate UI art lane | UI lane (subagent UIIntegrate) + release | 1.resources | `game-track/godot/assets/ui/` (6 PNGs, provenance, curation.json), `harbor_ledger_ui.gd`, `world_builder.gd` | provenance/G1 (D-035) | done-fallback-proven-smoke-green | human rights/style re-review if repurposed |
| Fix narrow-viewport tutorial layout (vignette squeezed text at 390px) | orchestrator | 1.verify | `harbor_ledger_ui.gd` responsive tutorial stack | G1/G6 | done-verified-on-prod-390x844 | none |
| Verdict ritual VFX + repair hint + curated world textures (D-036) | visual lane (subagent RitualVfx) | 1.presentation | `narrative_director.gd` (`play_verdict_ritual`, `play_repair_hint`), `world_builder.gd` (`curated_material`), `interactable_3d.gd`, `procedural_audio.gd` (4 cues), `player_3d.gd` | G1/G4 | done-2026-08-21-it1-smoke-eval-fallback-green | human presentation study |
| Diegetic ledger voice + Mira 서사 3-beat + tutorial rule page + episode receipt | narrative lane (subagent NarrativeLoop) | 1.design | `game_3d.gd`, `harbor_ledger_ui.gd` (기록/보류 voice, stamps, end-card receipt) | G1/G7 | done-2026-08-21-it1-router-probe-green | human presentation study |
| Generate + curate texture/stamp pack (3 tileable textures, 2 stamps, 1 seal) | asset lane (subagent TexturePack) | 1.resources | `game-track/assets/generated/higgsfield-tex-v1/`, 6 curated files in `assets/ui/`, curation.json 12 assets | provenance (D-036) | done-1.49MB-smoke-green | rights re-review if repurposed |
| Deep research: limitations/contributions + 4 method records | research lane (subagent DeepResearch) | paper.revision | `_workspace/current/design/paper-limitations-contributions-2026-08-21.md`, `research/deep-research/results/` (14/14 valid) | citation identity | done-2026-08-21 | integrate remaining text in iteration 2 |
| Guided repair operator ρ(a,E) + fixture battery + bilingual paper update | research engineer (subagent RepairMethod) | paper.method | `src/nesy_game/repair.py`, pilot manifest +10 fixtures, `run_conformance_pilot.py` guided arm, regenerated stage-04 packet (38 artifacts/22 inputs), EN 8pp / KO 7pp PDFs | methods drift + page band | done-120-tests-drift-OK-make-check-pass | clean-tag re-lock at push 2 |
| Iteration-2 game polish (beacon shader, lens hero glint, start-gate parallax, ledger-close beat, perf allocation audit, stamp/contrast fixes) | polish lane (subagent GamePolish) | 1.presentation | all seven `game3d/*.gd` | G1/G4/G6 | done-2026-08-21-it2-smoke-eval-fallback-green | human presentation study |
| Iteration-2 paper polish (5-bullet contributions, +3 verified refs S44–S46 → 45 total, L1–L9 limitations, IMRaD parity audit, figure rubric ≥4/5 rework) | paper lane (subagent PaperPolish) | paper.revision | `paper/latex/en+ko/main.tex`, `references.bib`, `generate_paper_figures.py`, rebuilt PDFs EN 8pp/KO 7pp | page band + drift + parity | done-2026-08-21-make-check-pass | clean-tag re-lock |
| Deploy iteration-2 artifact + golden-path capture | release engineer (orchestrator) | 1.release | deploy `dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW`, `docs/latest/golden-path.gif` (3.2 MB, 32 s) | release engineering | done-byte-identical-alias-zero-errors | monitor/rollback drill |
| Instrument input→visible feedback telemetry + 9-check presentation contract + playfield-first wide layout (0.66) | programmer + UI lane (D-037) | 1.systems | `game_3d.gd` probe/`_input_feedback_snapshot`, `harbor_ledger_ui.gd` layout metrics, `run_playable_evaluation.py` 9/9, `SL-PLAY-EVAL-001` `49/49` | G4/G6 wiring | done-2026-08-28-headless-wiring-only | browser/user-gesture latency measurement |
| Execute deterministic archetype balance probe `SL-BALANCE-PROBE-001` (5 rotations, G2 replacement measurements, chart + md + json) | QA + designer (D-038) | 1.verify | `scenes/balance_probe.tscn`, `scripts/balance_probe_runner.gd`, `scripts/game3d/golden_path_layout.gd`, `scripts/run_balance_archetypes.py`, `docs/latest/balance-archetypes.{json,md,svg}` | G2/G3 engineering | done-2026-08-28-5-of-5-pass | human playtest for G2 perception/G3 viability |
| Open motion/rig intake lane with raw-source guard (Mixamo/Blender/Godot retarget contract) | asset lane + release (D-039) | 1.resources | `game-track/assets/motion/README.md`, `scripts/validate_motion_assets.py`, root `.gitignore` guards | provenance | done-contract-zero-assets | first curated GLB + rig adoption interview |
| Refresh stale QA registrations (capture SHA-256 ×4, PCK bytes/hash) against current artifacts | QA (bookkeeping) | 1.verify | `qa/gate-measurements.md` | evidence hygiene | done-2026-08-28 | keep in sync at each artifact refresh |
| Close Cycle 3 | director + independent reviewers | 1.review | `retrospectives/cycle-3-retrospective.md` | release | blocked-on-pending-evidence | final verdict |

## Latest observed engineering receipts

- `godot --headless --path game-track/godot res://scenes/main_3d.tscn -- --smoke --public-safe`
  → `8/8`, terminal state SHA-256
  `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`.
- `./scripts/validate_game_track.sh` → `40 tests, 44 subtests` in the current Cycle 3 session.
- `scripts/run_playable_evaluation.py` → `SL-PLAY-EVAL-001` (2026-08-28): fixtures `4/4`, fixture
  checks `40/40`, presentation checks `9/9` (adds `wide_layout_preserves_playfield` and
  `input_feedback_latency_probe_emits_sample`), combined `49/49`; terminal SHA-256 unchanged.
  The evaluation now also emits `input_feedback` telemetry (engine-local wiring evidence only).
- `scripts/run_balance_archetypes.py` → `SL-BALANCE-PROBE-001` (2026-08-28): archetypes `5/5`,
  refusal state isolation `10/10`, forbidden-disclosure commits `0/3` opportunities, replay hash
  equality `5/5`, refusal-code coverage `7/9` with two structurally unexercisable codes documented;
  artifacts `docs/latest/balance-archetypes.{json,md,svg}`.
- Four `docs/latest/*.png` working captures are 1280×720 and SHA-256 registered in the matrix;
  they are carried from 2026-08-21 — the 2026-08-28 session could not open a GUI window from its
  sandbox, so a non-headless capture refresh with the new 0.66 wide layout is pending.
- 2026-08-28 incident note: the canonical `game-track/godot/project.godot` was rewritten twice
  during this session — once by a diagnostic non-headless launch and once during the first cold
  `--import` after new engine files were added (editor-style normalization that also flipped
  `run/main_scene`). The studio validator failed closed on the evidence hash both times and the
  file was restored via `git checkout`; a warm-cache re-run of the same import no longer rewrites
  it. Rule of thumb: after adding engine resources, run the suite once, then re-check
  `git status -- game-track/godot/project.godot` before staging.
- `game-track/web/public/` contains 11 top-level build files (~45.9 MB); the latest 2026-08-21 PCK
  is 5,970,516 bytes (1.57 MB procedural → 4.82 MB with curated UI art → 5.97 MB with the D-036
  texture/stamp lane), SHA-256
  `b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb`. The public 4,534-byte OFL notice
  hash matches the source license. Local `vercel link` metadata (`.env.local`, `.vercel/`, generated
  `.gitignore`) is not a shipped artifact file and is excluded from the count. The artifact remains
  ignored and non-authoritative.
- Vercel production: `https://sealed-lighthouse-trace-rpg.vercel.app`, 2026-08-21 deploy
  `dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW` (ritual+texture build, `index.pck` 5,970,516 bytes, SHA-256
  `b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb`); html/pck/wasm fetched from
  the alias byte-identical to the local artifact. (Prior receipts: same-day
  `dpl_J9STdbrWdiXyZakGuUWR7aD8jip9` — curated-art build, verified desktop+mobile; 2026-08-17
  `dpl_7DN4fLqmGa8DfKeiQamVrkXgpEoe`.)
- 2026-08-21 golden-path screencast from the deployed alias retained as
  `docs/latest/golden-path.gif` (640×360, 10 fps, 32 s, 3,245,101 bytes) — engineering working
  artifact only; not usability, immersion, or performance evidence.
- 2026-08-21 headless browser smoke (local + alias): key-art start gate with AI disclosure footer,
  intro cinematic, tutorial folio (narrow 390×844 stacked layout fixed this session after the first
  deploy showed a squeezed text column), ledger/objective updates, brass-framed Mira portrait;
  zero unexpected console/page errors at 1280×720 and 390×844. The single `WrongDocumentError` on
  synthetic entry is the known automation-only pointer-lock artifact; pointer lock remains `FIX`
  pending a human-gesture check (2026-08-17 evidence unchanged: headless click raised
  `pointerlockerror`; real-Chrome automation issued no pointer-lock request).
  All six retained `docs/latest/*web*`/`*vercel*` captures were refreshed from the 2026-08-21
  artifact/deployment.
- 2026-08-17 browser smoke: clean Korean rendering at 1280×720 and 390×844; zero console and page
  errors. Pointer lock is not verified — a prior session's trusted-headless pointer-lock claim failed
  reproduction on 2026-08-17 (headless Chromium raised `pointerlockerror`; real Chrome via Playwriter
  issued no pointer-lock request; `document.pointerLockElement` stayed null both times), so that item
  is `FIX` pending a human-gesture check. Playwriter was used that day only for the Vercel
  device-approval login and the pointer-lock retest; the layout, glyph, and HTTP checks ran headless.
  Retained paths: `docs/latest/vercel-start.png`, `vercel-in-game.png`,
  `vercel-mobile-start.png`, `vercel-mobile-in-game.png`, `web-start.png`, and `web-in-game.png`.
- Nanum Gothic Regular is bundled under SIL OFL 1.1 with pinned source, license, size, and SHA-256.

These receipts are engineering conformance only and do not modify selected immutable v5 or upgrade
G4/G6. The extension-connected inspection tab's `WrongDocumentError` is automation-only and does not
imply that any session confirmed pointer lock; automation denial is not by itself evidence of a
production defect. G4 is unassessed and G6 remains `FIX` pending save/reload, warmed
performance/input, the 30-minute soak, and the open human-gesture pointer-lock check.

Refresh rule: any lane, generator, authority boundary, entry point, Web export behavior, gate,
regression command, or evidence-promotion boundary change updates this manifest and `CLAUDE.md` in
the same change set.

Latest rule refresh: 2026-08-21, decisions `D-034`–`D-036` (Higgsfield UI generator, curated
runtime art lane, world-texture/stamp extension); prior refresh 2026-08-13, `D-027`–`D-033`.
