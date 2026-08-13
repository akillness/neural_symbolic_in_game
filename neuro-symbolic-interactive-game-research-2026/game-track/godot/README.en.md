# The Sealed Lighthouse — Godot conformance slice and render-capture pass

Status: **three retained Godot 4.7.1 headless runs plus one fresh corrupt-save negative fixture
observed and schema-verified; separate non-headless capture promotion in progress** (2026-08-13).

This Godot 4.x project is a paper-facing, deterministic micro-RPG fixture. It exercises a compact
quest and disclosure path through an engine-local authored policy mirror without embedding the
research runtime. Supported engine events have a tested projection into the stable bridge envelope;
no live Python authorization round-trip has executed.

The render-capture entry point is deliberately separate from the headless conformance runner. It
replays frozen canonical beats for presentation evidence, waits for an actual rendered frame, and
writes three registered PNGs plus source/render metadata. It does not authorize an action or change
canonical state.

## Scenario path

| Turn | Player/system action | Hard-policy outcome | Canonical state |
|---:|---|---|---|
| 0 | Observe the dark lighthouse and reachable lamp store | Observation only | Unchanged |
| 1 | Acquire the reachable signal lens | Valid commit | Inventory and quest stage 1 |
| 2 | Ask Captain Mira for a future betrayal and a gated hint | `FORBIDDEN_DISCLOSURE` + `STAGE_GATED_DISCLOSURE` | Safe fallback; unchanged |
| 3 | Install the signal lens | Valid commit | Quest stage 2; hint authorized |
| 4 | Optional duplicate-ID or timeout injection | Idempotent skip or safe fallback | Unchanged |
| 5 | Ask for the now-authorized tide-marks hint | Valid commit | Hint disclosed; relationship memory appended |
| 6–8 | Save, load, and replay | Hash comparisons | Terminal hash must match |

Frozen expected terminal state hash:
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`.
This is an unkeyed SHA-256 integrity checksum over canonical JSON, not authentication.
The fixture labels it `python-independent-sealed-lighthouse-v1`: the Python test computes the same
terminal projection independently of GDScript. All three observed Godot runs matched that hash.

## Run with Godot 4.x

From the repository project root:

```bash
PROJECT_ROOT="$(pwd)"
GODOT_BIN="/absolute/path/to/godot4"
OUTPUT_DIR="/tmp/trace-rpg-godot-canonical"
"$GODOT_BIN" --headless --path "$PROJECT_ROOT/game-track/godot" --quit-after 120 -- \
  --fixture="$PROJECT_ROOT/data/fixtures/experimental-game-canonical.json" \
  --output="$OUTPUT_DIR"
```

Replace the fixture with `experimental-game-duplicate-event.json`,
`experimental-game-timeout.json`, or `experimental-game-corrupt-save.json` for fault injection.
Each successful engine invocation writes:

- `events.jsonl`: proposal/evidence/validation/repair/commit, model revision, seed, cost, latency,
  and before/after state hashes for every event;
- `save.json`: the versioned save document and state hash;
- `summary.json`: engine version, replay/save checks, fault counts, and timing samples.

The summary uses `OBSERVED_ENGINE_RUN` only because it is emitted from a running Godot process.
Static tests do not create this marker or an ersatz engine result.

## Verify contracts

```bash
.venv/bin/python -m pytest -q tests/test_godot_experimental_game.py
ruff check tests/test_godot_experimental_game.py
```

When Godot 4.x is unavailable, static contract tests pass and the engine test skips with an explicit
reason. When Godot is available, the same test executes all four fixtures and validates every
event, save, and summary against the JSON Schemas.

The authoritative retained 2026-08-13 evidence set is selected by
`../../_workspace/current/engineering/tech-verification/current.json` and currently resolves to
`evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/`. The canonical,
duplicate-ID, timeout, and corrupt-save runs each made three commits and reached the frozen
terminal/oracle hash; the corrupt-save probe was rejected before live-state mutation. The current
game-track suite reports `19 passed, 44 subtests passed`. Performance budgets did not all pass:
five-sample headless frame p95 values included startup transients and were `116.667`, `100.000`,
`98.760`, and `112.907 ms`, respectively, in the selected retained packet.

## Non-headless capture packet

Cycle 2 records `SL-CAPTURE-001` as the paper label for selected immutable evidence set
`godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`. Immutable v1--v4 remain retained and
superseded through clipping, top-margin, status-contrast, toolchain-provenance, and CI-portability
reviews. The v5 primary structured-state panels are:

| Panel | Source beat | File |
|---|---|---|
| `sl-rc-001-arrival` | arrival observation | `sl-rc-001-arrival.png` |
| `sl-rc-002-rejected-secret` | rejected early disclosure and fallback | `sl-rc-002-rejected-secret.png` |
| `sl-rc-003-authorized-hint` | authorized hint after lens installation | `sl-rc-003-authorized-hint.png` |

Promotion requires a non-headless display driver, rendered-frame synchronization, exact 1280×720
dimensions, non-blank/opacity checks, file bytes and SHA-256, and binding to source fixture, run,
event/state beat, and source hashes. The primary packet contains no generated concept asset.
The v5 manifest additionally binds hashes for the capture pipeline, PNG decoder, capture schema,
retained validator, and `uv.lock`, and records Python `3.13.9`, jsonschema `4.26.0`, and JSON Schema
Draft 2020-12. A verifier may run on another supported Python version; it verifies the recorded
capture environment rather than pretending to reproduce it exactly.

![Arrival observation](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-001-arrival.png)

![Rejected disclosure](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-002-rejected-secret.png)

![Authorized hint](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-003-authorized-hint.png)

## Evidence boundary

The retained artifacts provide authored-fixture engine-local policy-mirror evidence toward Stage 6
M6; a live Python authorization round-trip is still required before
cross-runtime paper promotion. They do not measure model superiority, player benefit,
semantic-oracle completeness, visual quality, or commercial-engine portability. Timeout and
duplicate-ID fixtures are authored fault paths, not population error-rate estimates.
Duplicate suppression is intentionally process-local in this slice; persistent cross-process
idempotency remains required before a live adapter can be approved.
The PNGs add only authored engine-render/state correspondence. They do not add visual-quality,
usability, immersion, input-latency, performance, player-benefit, semantic-oracle, G4, or G6
evidence.
