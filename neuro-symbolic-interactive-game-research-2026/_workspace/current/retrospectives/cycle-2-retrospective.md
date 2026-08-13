# Cycle 2 retrospective — non-headless authored render evidence

Run ID: `20260813-sealed-lighthouse-cycle-2`
Closed: 2026-08-13
Director decision: bounded final selection under `D-026`
Next-cycle entry: Stage 1 engine-integration hardening

## Outcome

Cycle 2 added one separate non-headless Godot presentation pass without changing the headless
conformance authority. The selected immutable v5 packet binds three 1280×720 primary structured-
state panels to canonical event/state beats, source hashes, file hashes, render metadata, pixel
integrity statistics, and the validation-toolchain provenance. All capture rows declare
`generated_assets_in_frame: false`.

The first promoted render packet was not overwritten or deleted. Visual QA found a clipped header
in its rejection panel, so v1 remained immutable and v2 corrected it under `D-020`. A subsequent
independent audit requested safer top margins and stronger state-status contrast, so v2 also remains
retained and v3 corrected presentation under `D-022`. A deep audit then required hashes for the
capture pipeline, PNG decoder, schema, retained validator, and `uv.lock`, plus Python/jsonschema
versions; v4 added them. The CI-portability repair selected v5 without requiring the verifier host
Python to equal the recorded capture host. v1--v4 remain immutable and superseded.

## Verification

| Check | Evidence | Result |
|---|---|---|
| Selected evidence pointer | `engineering/tech-verification/current.json` | `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5` + manifest SHA-256 bound |
| Non-headless execution | selected render manifest | macOS display server; `headless: false`; OpenGL compatibility renderer |
| Dimensions and content | three capture rows | 1280×720, opacity `1.0`, 1,308--1,356 unique colors |
| Source correspondence | capture event IDs and before/after world hashes | arrival observation, state-preserving rejection, authorized hint commit bound |
| Aggregate regression | `./scripts/validate_game_track.sh` on 2026-08-13 | PASS: 19 tests, 44 subtests; asset/studio/Ruff and six-document current-pointer parity gates pass |
| Full Python suite | `uv run python -m pytest -q` on 2026-08-13 after Stage-8 parser-contract regression migration | PASS: 96 tests, 70 subtests |
| Toolchain provenance | selected v5 manifest | capture pipeline, PNG decoder, schema, retained validator, `uv.lock`, Python `3.13.9`, and jsonschema `4.26.0` recorded |
| Bilingual paper/PDF integration | authoritative EN/KO LaTeX + `make check` | PASS: registered readable three-panel figure before Discussion, bounded `C-GAME-DESIGN-003`, both PDFs within the 6--8-page short-paper band |
| Visual review | direct inspection of selected image bytes | PASS: readable, non-blank, safe top margins, high-contrast statuses |

## Gate effect

No G1--G8 gate is upgraded by screenshot existence. G1 remains `FIX` until a complete visible-string
export is audited. G4 remains without participant immersion/readability/latency data. G6 remains
`FIX` because frame p95, long-frame rate, 30-minute memory soak, and interactive input evidence are
not supplied by static capture. G2, G3, G5, G7, and G8 retain their prior bounded states.

`SL-CAPTURE-001` is only a paper-crosswalk label, not an engine-manifest field. It may support
`C-GAME-DESIGN-003` as authored engine-render/state correspondence. It may not support a live
Python authorization, model efficacy, visual efficacy, usability, immersion, participant outcome,
semantic-oracle completeness, G4, or G6 claim.

## Next cycle

Re-enter Stage 1 for the live Python authorization adapter and the missing warmup/soak/input
performance evidence. Preserve all render packets; resolve paper-facing evidence through selected
v5 only.
