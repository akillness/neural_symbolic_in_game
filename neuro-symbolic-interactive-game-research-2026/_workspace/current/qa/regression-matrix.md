# Regression Matrix — Cycle 3

| Surface | Command/method | Expected | Current evidence |
|---|---|---|---|
| Full Python contracts | `uv run python -m pytest -q` | all pass | carried Cycle 2 PASS: 96 tests, 70 subtests; fresh integrated rerun pending |
| Project integrity | `uv run python scripts/validate_project.py` | pass | carried PASS after Graphify refresh; fresh integrated rerun pending |
| Research harness | `uv run python scripts/validate_harness.py` | pass | carried PASS: 15 agents, 3 skills, reviewer separation |
| Game track aggregate | `./scripts/validate_game_track.sh` | studio, concepts, Godot contracts, Ruff pass | Cycle 3 current-session PASS: 40 tests, 44 subtests; rerun after final integration |
| Public-safe 3D smoke | `godot --headless --path game-track/godot res://scenes/main_3d.tscn -- --smoke --public-safe` | eight checks pass; terminal hash equals oracle | PASS `8/8`; hash `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892` |
| Presentation engineering evaluation | `scripts/run_playable_evaluation.py` plus `--evaluate` | no state mutation; start/audio lock, semantic redundancy, responsive profiles, proposal boundary pass | PASS `7/7`; matrix `SL-PLAY-EVAL-001` |
| Latest public-safe screenshots | non-headless `--shot <png> --shot-stage <beat> --public-safe` | valid 1280×720 PNG; hashes registered; candidate assets excluded | PASS `4/4`; engineering working captures, not immutable evidence |
| Staged Web release | `./scripts/build_godot_web.sh` | canonical project unchanged; no import/script errors; static files emitted | artifact built: 11 top-level files, 41,425,846 bytes; PCK 1,573,072 bytes after `docs/latest/**` exclusion |
| Web artifact asset boundary | staged copy plus `web`/`--public-safe` guard | no pending generated concept/pack-3d images | PASS by source/PCK inspection and public-safe runtime guard |
| Clean browser startup | local/production HTTP + clean browser | start gate; trusted click pointer/audio; console/page errors clean | bounded PASS; save/reload remains separate |
| Responsive/Korean browser UI | wide and narrow viewport snapshots | no clipping; 44 px choices; Korean/English glyphs visible | bounded PASS at 1280×720 and 390×844; human readability unassessed |
| Browser save/load | interact, F5/F9 or equivalent browser path | checksum-validated continuity | pending |
| Browser performance | warmed profiler + 30-minute soak | p95 ≤16.7 ms; long frames <0.5%; input ≤100 ms; stable memory | pending; G6 `FIX` |
| Immutable Godot evidence bundle | retained validator/current pointer | selected v5 remains hash-valid and unchanged | carried PASS; v1–v4 retained superseded, v5 selected |
| Candidate concept assets | `uv run python scripts/validate_concept_assets.py` | public exclusion IDs/hashes parse; every listed PNG remains absent | PASS public-safe profile; rights/style review still pending |
| Bilingual studio documents | studio validator + manual numeric/claim audit | stable IDs and numerical targets align | current document update; validator and manual diff check pending |

The fresh Cycle 3 PASS rows are engineering-only. They do not establish human presentation impact,
browser performance, a live Python transport, or a broader paper result.
