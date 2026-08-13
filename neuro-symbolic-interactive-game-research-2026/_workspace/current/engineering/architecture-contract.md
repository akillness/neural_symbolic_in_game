# Engineering architecture contract / 엔지니어링 아키텍처 계약

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game-programmer
Status: `[OBSERVED] carried v5 conformance evidence plus Cycle 3 playable/Web structure`

## Authority boundary / 권한 경계

| Concern | Authoritative owner | Exchange |
|---|---|---|
| Canonical world, quest, NPC disclosure, relationship memory | Target: research-side policy/validator; current fixture: Godot policy mirror | versioned candidate, validation, commit/reject events |
| Player movement, focus, camera, UI, VFX, local audio | Godot presentation | reads committed snapshot; emits interaction intent only |
| Engine observation, save/load, local telemetry | Godot game track | `experimental-game-event.schema.json` JSONL |
| State mutation | deterministic commit operation only | before/after canonical SHA-256 |
| Proposal text or future live model | untrusted, non-authoritative | cannot mutate state before validation |
| Generated candidate images | secondary authoring/VLM track | never loaded by Web or `--public-safe`; no runtime generation |
| Static Web hosting | disposable export artifact | no research authority and no canonical-state mutation |

The Python and Godot runtimes remain separate. The current playable fixture does not execute a live
Python authorization round-trip. Stable bridge projection proves schema compatibility only.

## Entry points and freshness boundary / 진입점·최신성 경계

- Canonical project: `game-track/godot/project.godot`, default
  `res://scenes/headless.tscn`; its evidence-bound bytes remain unchanged.
- Playable scene: `game-track/godot/scenes/main_3d.tscn`, launched explicitly for desktop,
  public-safe smoke, evaluation, and working screenshots.
- Web release: `scripts/build_godot_web.sh` copies the project to `mktemp`, installs the Web preset,
  changes only the staged copy to `main_3d.tscn`, checks logs for errors, and emits ignored
  `game-track/web/public/`.
- Immutable evidence: `engineering/tech-verification/current.json` still selects v5. Cycle 3
  working screenshots/evaluation outputs are not inserted into or substituted for that packet.

## Implemented deterministic path / 구현된 결정론적 경로

`observe → acquire_object → rejected disclosure → safe fallback → install_lens → authorized hint → tide route → save → load → replay`

The offshore lighthouse stays dark and sealed. Exactly three valid commits reach the canonical
terminal state. The Python-side independent fixture oracle and Godot state machine bind that state
to `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`.

## Hard invariants / 하드 불변조건

| ID | Invariant | Enforcement/evidence state |
|---|---|---|
| EG-I01 | Only a valid commit changes canonical state | carried v5: three commits/run; `apply_operation` is sole writer |
| EG-I02 | Early betrayal/gated hint cannot mutate state | carried v5 hash equality plus current public-safe smoke |
| EG-I03 | `keeper_betrayal` is never disclosed | permanent forbidden set; terminal fixture excludes fact |
| EG-I04 | `tide_marks_hint` requires quest stage ≥2 | stage gate plus post-install commit |
| EG-I05 | Duplicate IDs apply at most once per process | carried duplicate fixture |
| EG-I06 | Timeout leaves full state unchanged | carried timeout fixture |
| EG-I07 | Save/load and replay reproduce terminal hash | carried canonical/corrupt-save fixtures |
| EG-I08 | Timing, VFX, audio, movement, and UI do not enter canonical hash | presentation data kept outside state |
| EG-I09 | Supported events project into stable bridge envelope | schema compatibility only; no live transport claim |
| EG-I10 | Public-safe/Web presentation cannot load pending generated assets | `web`/`--public-safe` guard plus staged `res://` export |
| EG-I11 | Browser pointer/audio activation starts from a user gesture | start gate callback; browser execution still required |

## Cycle 3 engineering modes / Cycle 3 엔지니어링 모드

| Mode | Purpose | Claim boundary |
|---|---|---|
| `--smoke --public-safe` | execute eight authored state/presentation checks without candidate assets | conformance only |
| `--evaluate <path>` | atomically write UI/audio/input presentation invariants | not G4, usability, affect, immersion, or efficacy |
| `--shot <path> --shot-stage <beat> --public-safe` | create latest working presentation capture | not immutable/promotable without a new evidence packet |
| staged Web export | build public artifact without mutating canonical project | not deployed/browser-verified until fresh receipts exist |

## Paper-use boundary / 논문 사용 경계

Carried v5 data may support the already-bounded authored engine-render/state correspondence claim.
Cycle 3 automated presentation checks may describe instrument construction or engineering
conformance only. They cannot promote cross-runtime integration, model quality, human benefit,
immersion, usability, G4, or G6.
