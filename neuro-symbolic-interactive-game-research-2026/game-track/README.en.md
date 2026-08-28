# Game-development track — The Sealed Lighthouse

The game track does not embed research code directly inside the engine. The target architecture has
the engine emit stable bridge observations and the research runtime return authorization events.
The current Godot fixture instead runs an engine-local authored policy mirror; its supported event
types are projected into `schemas/game-bridge.schema.json` and schema-tested, but no live
Python↔Godot transport has executed.

Current implementation adds a Godot 4.x headless experimental slice plus a separate non-headless
render-capture pass to the event/experiment schemas, deterministic validation, unchanged-state
fallback, integrity checks, operation/state-hash replay, and frozen-response adapter. The authored
Godot path loads a harbor state, acquires a
reachable signal lens, rejects an early forbidden/stage-gated disclosure without mutation, installs
the lens, permits the later tide-marks hint, saves/loads, replays, and injects duplicate, timeout,
and corrupt-save cases. Persistent cross-process idempotency and live model transport remain planned.

Acceptance requirements for a live adapter:

- Canonical engine state changes only through a valid `commit` event.
- Every event records `run_id`, `episode_id`, `step`, `schema_version`, and `world_state_hash`.
- Persistent `event_id` idempotency must remove retries and network duplicates.
- Timeout, model failure, or high affect uncertainty must invoke a deterministic safe policy.
- The research track runs against a mock bridge; the game track runs without a model by replaying recorded traces.

The selected engine is Godot 4.x headless-first. Engine choice is not the paper contribution; protocol compatibility and reproducible state equality are.

Start here:

- [`design/gdd.en.md`](design/gdd.en.md) — authoritative experimental GDD
- [`design/paper-crosswalk.en.md`](design/paper-crosswalk.en.md) — RQ1--RQ5 and Stage 6 map
- [`godot/README.en.md`](godot/README.en.md) — headless run and evidence boundary
- [`assets/README.md`](assets/README.md) — public-safe exclusion manifest for rights-pending generated candidates
- [`../_workspace/current/production/task-manifest.md`](../_workspace/current/production/task-manifest.md) — current studio cycle

The primary planned experiment uses structured state/text. Generated images are excluded from it;
they may enter only a separately frozen secondary VLM/UI track. No participant or model-efficacy
result is produced by the design or headless slice.

## Cycle 3 public-safe playable and evaluation

The current playable `godot/scenes/main_3d.tscn` adds third-person dock exploration, readable
interaction focus, responsive ledger UI, reduced motion, pooled procedural VFX, and gesture-gated
locally generated audio. A 2026-08-21 presentation/feel pass deepened all of it: a tension-driven
weather arc (fog color grading, wind-sheared rain, sea agitation, sky darkening toward the refusal
apex), offshore distant lightning with delayed procedural thunder, buoy/lamp/mist harbor
micro-motion, a slow-FOV intro hold on the dark tower, an ending beat where the harbor-side lamp
sweeps its beam toward the tide channel (the offshore lighthouse stays dark), snappier movement
with stride-locked view bob, stronger focus/confirm affordances, escalating commit feedback, and
seven distinct procedural audio stingers over a wind/water ambience layer. All world-changing
intents still pass through the authored proposal and validation router. The player restores the
harbor-side signal and earns the tide route while the offshore lighthouse remains sealed.

A second 2026-08-21 pass made the paper's transaction diegetic: proposals are weighed in a
3-phase verdict ritual (amber inspection ring → brass-flash 기록 or slate seal-line 보류 → settle),
the harbor ledger logs numbered entries in a bureaucratic-poetic voice with stamp iconography,
Mira gained a 3-beat 서사 (storm night, guarded hope, quiet epilogue), the tutorial's second page
maps 제안·검증·보류·기록 onto the propose/validate/refuse/commit loop, and the end card carries an
episode receipt (entries, deferrals, state hash) under the tide-route seal. Curated D-036 world
textures (wet planks, oxidized brass, sail canvas) and stamp/seal icons ship with full provenance
and a proven procedural fallback.

![Golden-path opening: start gate, intro cinematic, tutorial folio, first steps](godot/docs/latest/golden-path.gif)

*32-second engineering capture from the deployed alias (start gate → intro → tutorial → dock).
Working artifact only — not usability, immersion, or performance evidence.*

| `SL-PLAY-EVAL-001` row | Checks | Result |
|---|---:|---|
| Canonical fixture | `10/10` | PASS |
| Duplicate-event fixture | `10/10` | PASS |
| Timeout fixture | `10/10` | PASS |
| Corrupt-save fixture | `10/10` | PASS |
| Presentation invariants | `9/9` | PASS |
| **Combined** | **`49/49`** | **PASS** |
| Archetype balance probe | `SL-BALANCE-PROBE-001` 5/5 | PASS |

All `4/4` authored fixtures reached the exact terminal state SHA-256
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`. The complete table and
machine record are [`godot/docs/latest/evaluation-matrix.md`](godot/docs/latest/evaluation-matrix.md)
and [`evaluation-matrix.json`](godot/docs/latest/evaluation-matrix.json).

Archetype balance probe (scripted conformance, not human data):
[`balance-archetypes.md`](godot/docs/latest/balance-archetypes.md) ·
[JSON](godot/docs/latest/balance-archetypes.json)

![Archetype balance probe chart](godot/docs/latest/balance-archetypes.svg)

| Arrival | Refusal |
|---|---|
| ![Cycle 3 public-safe arrival](godot/docs/latest/arrival.png) | ![Cycle 3 public-safe refusal](godot/docs/latest/refusal.png) |
| Authorized hint | Ending |
| ![Cycle 3 public-safe authorized hint](godot/docs/latest/authorized_hint.png) | ![Cycle 3 public-safe ending](godot/docs/latest/ending.png) |

These are four latest 1280×720 engineering working captures, not the immutable Cycle 2 packet.
Web and `--public-safe` still exclude every pending-review candidate under `assets/concepts/`.
Since D-034/D-035 the build additionally ships six user-curated, provenance-bound Higgsfield UI
art assets from `godot/assets/ui/` (start key art, Mira dialogue portrait, ledger parchment grain,
two item icons, tutorial vignette — AI-generated, disclosed on the start gate and here). Deleting
those PNGs leaves the fully playable procedural surface; the smoke receipt is identical with the
directory absent.

**Claim boundary:** authored-fixture and presentation-invariant conformance only. G4, usability,
immersion, affect, player efficacy, and model efficacy are **UNASSESSED**. G6 remains `FIX` until
pointer-lock, save/reload, warmed-frame/input, and 30-minute soak measurements exist.

From the project root:

```bash
./scripts/build_godot_web.sh
python3 -m http.server 4173 --directory game-track/web/public
```

Deployment status: **[public-safe Vercel build live](https://sealed-lighthouse-trace-rpg.vercel.app)**.
2026-08-21 production deployment `dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW` serves the ritual+texture build:
11 files, `index.pck` 5,970,516 bytes, SHA-256
`b9706912530248c271979d1146537ab20ea4fff124e812c6195c7caf8d1c56eb`; served html/pck/wasm fetched
back byte-identical to the local artifact. Headless browser smoke on the alias verified the
key-art start gate with AI disclosure footer, intro cinematic, tutorial folio, diegetic ledger
voice with stamps, and objective flow at 1280×720 with zero unexpected console/page errors
(earlier same-day deployment `dpl_J9STdbrWdiXyZakGuUWR7aD8jip9` verified the same at 390×844).
A human-gesture pointer-lock check remains the open item (as on 2026-08-17, when a headless click
raised `pointerlockerror` and real-Chrome automation issued no pointer-lock request at all).
Build and browser-smoke details: [`web/README.md`](web/README.md).

## Engine render-capture evidence

Cycle 2 registers `SL-CAPTURE-001` as three 1280×720 primary-track panels rendered by a separate
non-headless Godot pass over the canonical authored fixture:

| Panel | Beat | File | Claim limit |
|---|---|---|---|
| `sl-rc-001-arrival` | arrival observation | `sl-rc-001-arrival.png` | authored scene/state correspondence |
| `sl-rc-002-rejected-secret` | rejected disclosure | `sl-rc-002-rejected-secret.png` | rejection/fallback presentation correspondence |
| `sl-rc-003-authorized-hint` | authorized hint after lens installation | `sl-rc-003-authorized-hint.png` | authorized disclosure presentation correspondence |

`SL-CAPTURE-001` is the paper-crosswalk bundle label, not an engine-manifest field; the manifest
uses the three `sl-rc-*` capture IDs above. The selected immutable evidence set is
`godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`. The v1--v4 packets remain immutable and
superseded through visual QA, toolchain-provenance binding, and CI-portability repair. The v5
manifest binds the capture pipeline, PNG decoder, schema, retained validator, dependency lock, and
capture-host tool versions.
These panels use structured state/text and programmatic engine graphics, not generated concept art.
They do not demonstrate live Python authorization, model or visual efficacy, usability, immersion,
human-study outcomes, G4, or G6.

![SL-CAPTURE-001 arrival observation](../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-001-arrival.png)

![SL-CAPTURE-001 rejected disclosure](../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-002-rejected-secret.png)

![SL-CAPTURE-001 authorized hint](../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-003-authorized-hint.png)

Offline reproduction guide: [`recorded-experiment.en.md`](recorded-experiment.en.md)
