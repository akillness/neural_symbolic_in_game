# Gate Measurements — Cycle 2

Timestamp baseline: 2026-08-13  
Rule: no evidence path means `FIX`.

Cycle 1 engine-local conformance measurements are retained below as baseline. Cycle 2 adds a
separate non-headless render-capture packet, `SL-CAPTURE-001`; it does not reclassify a baseline
gate without the gate's own required measurement.

## G1 — Narrative consistency

- Target: 0 unwaived lore violations; 100% visible content traced to worldview.
- Observed: enumerated headless fixture strings and four concept surfaces were mapped to worldview
  IDs with `0` unwaived conflicts. A complete playable-build/localization export does not exist.
- Cycle 2 render evidence: three deterministic primary-track frames were promoted for canonical
  arrival, rejection, and authorized-hint beats. Their player-visible string audit remains `FIX`
  until independent content review is recorded.
- Method/evidence: `qa/content-worldview-audit.md`, `design/worldview.md`, concept provenance.
- State: `FIX`.

## G2 — Rules and balance

- Target: 100% mechanic coverage; applicable values within approved investigation-specific bands.
- Observed: no simulation.
- State: `NOT_SCHEDULED_STAGE_1`.

## G3 — Player-type diversity

- Target: at least five scripted archetypes tested and three distinct viable paths before final use.
- Observed: 0 executed archetypes.
- State: `NOT_SCHEDULED_STAGE_1`.

## G4 — Presentation impact

- Target: median human immersion >=4/5 and feedback <=100 ms in a later approved study.
- Observed: no participant data.
- Render-capture interpretation: even a valid non-headless PNG is not an immersion score, a
  readability complaint audit, or an input-feedback latency probe.
- State: `NOT_SCHEDULED_NO_HUMAN_DATA`.

## G5 — Revenue and fairness

- Target: zero paid mechanics under decision `D-006`.
- Observed: design declares zero economy; no paid/free simulation applies.
- Method/evidence: `pm/revenue-map.md`, `pm/reward-bands.md`.
- State: `SCOPED_OVERRIDE_NOT_EMPIRICAL_PASS`.

## G6 — Operations and performance

- Target: telemetry fields emit; p95 frame <=16.7 ms; long frames <0.5%; stable 30-minute memory;
  input <=100 ms; safe rollback and exact replay.
- Observed: Godot 4.7.1 executed four retained policy-mirror runs, including a corrupt-save negative
  run. All four matched the same terminal/load/replay/oracle hash and all authored correctness
  checks. Frame p95 was `116.667/100.000/98.760/112.907 ms` across five
  startup-heavy samples and failed `16.7 ms`; no long-frame rate, 30-minute soak, or interactive
  input measurement exists. The timeout fixture deliberately reached the `100 ms` deadline.
- Method/evidence: `engineering/tech-verification/godot-headless.md`,
  `engineering/tech-verification/current.json` plus its selected evidence manifest, and
  `tests/test_godot_experimental_game.py`.
- Cycle 2 render evidence: display/render metadata, frame synchronization, PNG integrity, and source
  binding may validate capture provenance only. They do not satisfy p95 frame, long-frame, soak,
  or input-latency thresholds.
- State: `FIX`.

## G7 — Core loop

- Target: 30--180 s, at least three actions, at least one information/progression reward, later human
  repeat proxy >=70%.
- Observed: the authored headless path executed three valid commits plus guarded failure cases in
  each retained run. It is an engine-local deterministic policy mirror, not a timed human loop;
  no 30--180 s interactive duration or repeat proxy was measured.
- Method/evidence: retained event traces and summaries under
  the evidence set selected by `engineering/tech-verification/current.json`.
- State: `FIX`.

## Cycle 2 capture-specific evidence (not a G1--G8 substitute)

- Target: one non-headless, deterministic primary-track render pass with three registered panels,
  exact source-state/event binding, 1280×720 dimensions, file hashes, and non-blank/opacity checks.
- Observed paper bundle: `SL-CAPTURE-001` in
  `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5` with manifest captures
  `sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, and `sl-rc-003-authorized-hint`.
- Observed manifest values: Godot 4.7.1, macOS display server, `headless: false`, OpenGL
  compatibility renderer on Apple M2 Pro, 1280×720, opacity `1.0`, and 1,308--1,356 unique colors.
- Evidence history: v1 was retained after rejection-header clipping; v2 fixed clipping; v3 added
  safe top margins and high-contrast status; v4 bound the full validation-toolchain provenance; v5
  made retained verification portable without erasing the recorded capture-host versions. All five
  remain immutable; v5 is selected (`D-020`, `D-022`, `D-025`, `D-026`).
- Current state: `[OBSERVED]` immutable promotion and visual inspection; fresh aggregate PASS with
  19 tests and 44 subtests. This closes the capture-specific integrity check only.
- Claim boundary: authored fixture render/state correspondence only; no live Python transport,
  model efficacy, visual efficacy, human study, G4, or G6 claim.

## G8 — Novelty

- Target: feature in <=2 of at least five comparable titles and later impression >=4/5.
- Observed: a seven-title official-description audit was completed; `N-01` and `N-02` have bounded
  `0/7` advertised-frequency candidates, but no human impression measurement exists.
- Method/evidence: `intake/game-survey.md`, `design/novelty-scorecard.md`.
- State: `FIX`.
