# Regression Matrix

| Surface | Command | Expected | Current evidence |
|---|---|---|---|
| Python contracts | `uv run python -m pytest -q` | all pass | PASS 2026-08-13 after Stage-8 parser-contract regression migration: 96 tests, 70 subtests |
| Project integrity | `uv run python scripts/validate_project.py` | pass | PASS 2026-08-13 after Graphify refresh |
| Research harness | `uv run python scripts/validate_harness.py` | pass | PASS 2026-08-13: 15 agents, 3 skills, artifact paths and reviewer separation |
| Game track aggregate | `./scripts/validate_game_track.sh` | pass | PASS 2026-08-13: 19 tests, 44 subtests, asset/studio/Ruff gates |
| Immutable Godot evidence bundle | `uv run python scripts/capture_godot_evidence.py --evidence-set-id <unique-id>` | new immutable set: 4 headless fixture runs + separate non-headless canonical render pass | PASS selected `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`; v1--v4 retained superseded; existing set overwrite prohibited |
| Non-headless render captures | selected manifest + aggregate capture/validator tests + visual inspection | `sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, `sl-rc-003-authorized-hint`; 1280×720 PNGs, non-blank/opaque, hash-bound to canonical source beats | PASS selected v5: macOS non-headless, opacity `1.0`, 1,308--1,356 unique colors; safe top margins and high-contrast statuses |
| Capture toolchain provenance | selected v5 manifest + retained validator | exact toolchain hashes and versions recorded; verifier remains portable across supported Python hosts | PASS manifest binds capture pipeline, PNG decoder, schema, retained validator, `uv.lock`, Python, and jsonschema provenance |
| Corrupt-save rejection | aggregate Godot test | no pre-validation mutation | PASS: load rejected, same pre/post live hash |
| Stable bridge projection | aggregate Godot test | all supported events validate | PASS schema compatibility; no live transport claim |
| Concept assets | `uv run python scripts/validate_concept_assets.py` | PNG/prompt/reference/provenance pass | PASS: 4 active concepts; SL-C04 v1 explicitly rejected |
| Bilingual documents | studio parity validator + manual crosswalk audit | pair/claim/stable IDs align automatically; numeric targets align manually | PASS: automatic ID parity plus recorded manual numeric audit |

Cycle 1 PASS rows above are carried baseline evidence. Update the Cycle 2 capture rows only from
fresh commands; never carry an old PASS across a generator, scene, capture method, or schema change.
