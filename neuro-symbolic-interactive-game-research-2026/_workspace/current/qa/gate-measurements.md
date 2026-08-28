# Gate Measurements — Cycle 3 Stage 1 re-entry

Timestamp baseline: 2026-08-13
Rule: no evidence path/receipt means `FIX`. Automated presentation conformance is not human efficacy.

Cycle 2 selected immutable evidence remains v5. Cycle 3 adds a public-safe playable/Web
engineering lane; it neither rewrites that packet nor upgrades a gate without the gate's required
measurement.

## G1 — Narrative consistency

- Target: `0` unwaived lore violations; `100%` player-visible content traced to worldview.
- Current source audit: `0` known conflicts in reviewed public-safe runtime strings and `1`
  generated environment-candidate conflict (`SL-C01`) quarantined from runtime.
- Correction: payoff is harbor-side signal restoration plus earned tide route; the offshore
  lighthouse remains dark and sealed.
- Browser evidence: bundled OFL Nanum Gothic rendered Korean cleanly in a headless browser at
  desktop 1280×720 and narrow 390×844 start/in-game states, with zero console/page errors.
- Missing: a complete all-dialogue/state accessibility audit beyond the retained start/in-game
  browser samples.
- Evidence: `qa/content-worldview-audit.md`, `design/concept.md`, public-safe guard.
- State: `FIX`.

## G2 — Rules and balance

- Target: 100% mechanic coverage; applicable values within approved investigation bands.
- Observed 2026-08-28 (`SL-BALANCE-PROBE-001`, scripted engineering conformance): operation
  coverage `3/3`; refusal-code coverage `7/9` with `OBJECT_NOT_REACHABLE` and
  `QUEST_STAGE_PRECONDITION` documented as structurally unexercisable through canonical
  operations (the second because `acquire_object` immediately raises quest stage to 1 — the
  guard is defense-in-depth); canonical episode reachability `5/5`; forbidden-disclosure
  commits `0/3` opportunities; refusal state-hash equality `10/10`; op-log replay hash equality
  `5/5`. Machine property recorded: duplicate install/hint re-commits mutate revision only
  (semantic state unchanged) and are UI-guarded; persistent event idempotency remains a live
  adapter precondition (EG-I05).
- Missing: human balance perception, tuned band simulation over B-001–B-013, and any live-model
  arm. Scripted counts cannot pass the gate alone.
- Evidence: `game-track/godot/docs/latest/balance-archetypes.{json,md,svg}`,
  `scripts/run_balance_archetypes.py`, `game-track/godot/scripts/balance_probe_runner.gd`.
- State: `FIX — ENGINEERING MEASUREMENTS ONLY`.

## G3 — Player-type diversity

- Target: at least five scripted archetypes and three viable paths before final use.
- Observed 2026-08-28: five scripted archetype rotations (A-01–A-05) executed deterministically
  through the canonical machine; all five converge to the canonical semantic terminal state;
  walking-distance proxies span 50.03–76.23 m (≈11.9–18.2 s at WALK_SPEED) across three distinct
  route shapes. Scripted execution establishes breadth of the battery, not human viability or
  dominance.
- Missing: human sessions per archetype and viability/dominance measurements.
- Evidence: `game-track/godot/docs/latest/balance-archetypes.json` per-archetype rows.
- State: `FIX — SCRIPTED BREADTH ONLY, NO HUMAN DATA`.

## G4 — Presentation impact

- Target: median human immersion `≥4.0/5`, measured local input-to-visible feedback `≤100 ms`, and
  zero unresolved S1/S2 readability complaints under an approved protocol.
- Implemented engineering structure: procedural harbor/VFX/audio, focus redundancy, responsive
  UI, reduced motion, and browser start gate.
- Fresh automated evidence (2026-08-28): `SL-PLAY-EVAL-001` passed all `9/9` presentation
  invariants (now including `wide_layout_preserves_playfield` ≥ 0.65 and
  `input_feedback_latency_probe_emits_sample`); the evaluation emits engine-local
  `input_to_visible_feedback_ms` samples through the proposal→ledger→rendered-frame boundary
  (headless sample observed at ≈29 ms; wiring evidence only, not a browser/user-gesture
  measurement). Four public-safe 1280×720 working captures remain hash-registered (carried from
  2026-08-21; GUI capture refresh pending).
- Interpretation: smoke, JSON, screenshots, and browser checks cannot measure immersion,
  readability preference, usability, affect, or efficacy.
- State: `FIX — NO HUMAN DATA`.

## G5 — Revenue and fairness

- Target: zero paid mechanics under `D-006`.
- Observed: design remains zero economy; no paid/free simulation applies.
- State: `SCOPED_OVERRIDE_NOT_EMPIRICAL_PASS`.

## G6 — Operations and performance

- Target: telemetry fields emit; warmed frame p95 `≤16.7 ms`; long frames `<0.5%`; stable
  30-minute memory; input `≤100 ms`; safe rollback and exact replay.
- Carried evidence: four v5 policy-mirror runs match terminal/load/replay/oracle hash. Startup-heavy
  frame p95 remains `116.667/100.000/98.760/112.907 ms`, so it does not pass.
- Cycle 3 engineering receipts (refreshed 2026-08-28): aggregate `45 tests, 44 subtests`;
  `SL-PLAY-EVAL-001` passed `4/4` authored fixtures (`40/40`) plus `9/9` presentation checks
  (`49/49` combined); four working PNGs passed size/hash registration. Engine-local input-feedback
  telemetry wiring now exists (D-037) but browser/user-gesture latency remains unmeasured. The
  latest staged artifact has 11 top-level files and 45,823,290 bytes; its PCK is 5,970,516 bytes,
  SHA-256 `b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb` (2026-08-21 D-036
  build, deployed and alias byte-identical). Production
  `https://sealed-lighthouse-trace-rpg.vercel.app` returned 200 for
  HTML/JS/WASM/PCK/OFL, served WASM as `application/wasm`, and exposed the hash-matched 4,534-byte
  OFL notice as `text/plain`. A headless browser verified clean Korean rendering at 1280×720 and
  390×844 with zero console/page errors; Playwriter was used on 2026-08-17 only for the Vercel
  device-approval login and one pointer-lock retest. Pointer lock is NOT verified: the prior
  trusted-headless-pointer-lock observation failed to reproduce twice on 2026-08-17 — a synthetic
  headless Chromium click raised `pointerlockerror`, and a real-Chrome Playwriter click issued no
  pointer-lock request at all — with `document.pointerLockElement` null in both retests. The HUD
  `LOOK ACTIVE` (`시점 잠김`) label is the game's own state label, not pointer-lock evidence, and
  automation denial alone is not evidence of a production defect.
- Missing: browser save/reload, human-gesture pointer-lock confirmation, representative warmed
  frames, long-frame rate, measured input latency, 30-minute memory soak, and rollback drill.
- Evidence: selected v5, `engineering/perf-budget.md`, current source, current-session aggregate
  receipt. No new immutable performance packet exists.
- State: `FIX`.

## G7 — Core loop

- Target: `30–180 s`, at least three actions, at least one information/progression reward, later
  human repeat proxy `≥70%`.
- Cycle 3 engineering receipt (refreshed 2026-08-28): the canonical, duplicate-event, timeout, and
  corrupt-save fixtures passed `10/10` checks each (`4/4`, `40/40`) and all reached terminal hash
  `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`. The presentation evaluation
  added `9/9` non-mutating checks for `49/49` combined, and the archetype probe recorded scripted
  loop-shape counts (commits 3–5, refusals 0–5, walk proxy 11.9–18.2 s per rotation).
- Interpretation: this confirms the state path and public-safe presentation sync; it does not
  measure human duration, comprehension, agency, or repeat behavior.
- State: `FIX`.

## G8 — Novelty

- Target: feature in `≤2` of at least five comparable titles and later impression `≥4/5`.
- Carried observation: seven-title official-description audit with bounded `0/7` advertised-
  frequency candidates for `N-01` and `N-02`; no human impression data.
- State: `FIX`.

## Cycle 3 engineering-conformance matrix (not a G1–G8 substitute)

| Check | Current result | Claim boundary |
|---|---|---|
| Fresh authored fixtures | `4/4`, `40/40`, correct shared terminal hash | hard-path conformance only |
| Presentation evaluation | `9/9`, canonical state unchanged | instrumentation only |
| Combined `SL-PLAY-EVAL-001` | `49/49` | engineering only |
| Archetype balance probe | `SL-BALANCE-PROBE-001` 5/5 rotations; isolation 10/10; replay 5/5 | scripted engineering only |
| Aggregate studio/game tests | `45 tests, 44 subtests` | regression only |
| Candidate asset exclusion | Web/`--public-safe` guard present | static track separation; rights review still open |
| Responsive profiles | wide-column and narrow-stacked declaration check PASS | no visual/human readability result |
| Browser gesture policy | pointer lock NOT verified — 2026-08-17 retests failed to reproduce the prior claim (headless synthetic click raised `pointerlockerror`; real-Chrome Playwriter click issued no pointer-lock request; `document.pointerLockElement` null in both); zero console/page errors confirmed | `FIX`; human-gesture pointer-lock check and measured input latency pending |
| Procedural audio | external asset check PASS; nine generated streams, 22,050 Hz, four voices | playback/impact unmeasured |
| Bundled Korean font | Nanum Gothic Regular, unmodified, SIL OFL 1.1, 2,054,744 bytes, pinned SHA-256; public notice 4,534 bytes, SHA-256 `eeacf16032901d0ed0456876ec77b8f0fda6b3fecec7d972f8543eb602e6c30f` | release resource, not research evidence |
| Web artifact/deployment | 11 files, 45,823,290 bytes; latest production PCK 5,970,516 bytes, SHA-256 `b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb`, after excluding `docs/latest/**`; HTML/JS/WASM/PCK/OFL 200; WASM and OFL MIME correct | pointer lock, save/reload, performance, and soak pending |
| Deployed responsive rendering | clean Korean at 1280×720 and 390×844; zero console/page errors | bounded browser smoke, not G4 |
| Latest working captures | `4/4` 1280×720 PNGs with SHA-256 registration | never G4/efficacy evidence |

## Cycle 3 fresh working artifacts

| Artifact | Size/dimensions | SHA-256 / status |
|---|---:|---|
| `game-track/godot/docs/latest/arrival.png` | 1280×720, 343,547 B | `640558b81b60cb54a739c2e58773f17cfb07c7b16c4302683779194f14e1b8fc` |
| `game-track/godot/docs/latest/refusal.png` | 1280×720, 442,979 B | `9dbd699cb5f047e8cdc6c575daefd1912d9f63191c73f7f9ec3895c0ce3f796c` |
| `game-track/godot/docs/latest/authorized_hint.png` | 1280×720, 397,346 B | `5ab6ff1edbd8aaff2f3bde325b90d131dcafa0fdea25cfa3fc094473bf414901` |
| `game-track/godot/docs/latest/ending.png` | 1280×720, 397,478 B | `2cc3b95318f7aec3e25e8ab7d78ad1b7ba6d4d337414dbf438118e68c03e0d9b` |
| `game-track/godot/docs/latest/evaluation-matrix.json` | `4/4`, `49/49` | PASS; engineering-only |
| `game-track/godot/docs/latest/balance-archetypes.json` | 5/5 rotations, isolation 10/10 | PASS; scripted engineering-only |
| `game-track/web/public/` | 11 top-level files, 45,823,290 bytes; PCK 5,970,516 bytes | PCK SHA-256 `b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb`; deployed 2026-08-21 static artifact after `docs/latest/**` exclusion with public OFL notice; ignored/non-authoritative |
| `docs/latest/vercel-start.png`, `vercel-in-game.png` | 1280×720 | production desktop start/in-game receipts |
| `docs/latest/vercel-mobile-start.png`, `vercel-mobile-in-game.png` | 390×844 | production narrow start/in-game receipts |
| `docs/latest/web-start.png`, `web-in-game.png` | 3294×1908 | local/extension-connected Web inspection receipts |

The public-safe working PNGs, font, and Web/deployment artifacts are not promoted immutable research
evidence. The extension-connected tab produced one automation-only `WrongDocumentError` because it
did not own the root document; that note stays automation-only and does not imply pointer lock was
confirmed working. Pointer lock did not reproduce on 2026-08-17 in either a headless synthetic click
or a real-Chrome Playwriter click, so it remains open pending a human-gesture check. G4, usability,
immersion, affect, player efficacy, and model efficacy remain **UNASSESSED**. G6 remains `FIX`
because save/reload, pointer-lock confirmation, warmed performance/input, and the 30-minute soak are
absent.

## Selected Cycle 2 immutable capture evidence (carried unchanged)

`engineering/tech-verification/current.json` continues to select
`godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`. Its three 1280×720 panels and toolchain
provenance support authored fixture render/state correspondence only. Cycle 3 does not overwrite,
amend, or broaden that claim.
