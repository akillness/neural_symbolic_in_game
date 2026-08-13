# Stage 6 Revision Track — The Sealed Lighthouse Experimental Game

Status: `ENGINE_LOCAL_CONFORMANCE_AND_RENDER_OBSERVED_CROSS_RUNTIME_INTEGRATION_PENDING`
Date: 2026-08-13
Upstream review: `stage-06-peer-review-simulation.md`
Requirements: `../../../.omx/specs/deep-interview-experimental-game-track.md`

## Accepted direction

The user accepted the Full Paper revise-and-resubmit direction and selected a planning-plus-headless
game-track revision. A five-round deep interview fixed the following decisions:

1. turn-based narrative investigation micro-RPG;
2. precise design plus a minimal executable headless slice;
3. Godot 4.x headless-first;
4. structured-state/text primary track plus frozen-image VLM/UI secondary track;
5. human-study protocol/tooling without participant recruitment or data collection.

## C1 contribution

The new design makes Stage 6 C1 executable rather than satisfied. It specifies six explicit
controller arms, matched repair budgets, grouped template holdouts, physically separated encoded
and semantic oracles, treatment-policy failure accounting, per-attempt token/latency/cost fields,
and a ten-model/three-model path. No live model, held-out oracle label, human outcome, effect size,
or confidence interval has been produced. `C-RESULT-001`--`005` therefore remain `TODO-RESULT`.

Authoritative planning surfaces:

- `game-track/design/gdd.en.md` and `gdd.ko.md`;
- `game-track/design/scenario-oracle-plan.en.md` and `.ko.md`;
- `game-track/design/paper-crosswalk.en.md` and `.ko.md`;
- `configs/experimental-game.yaml`, `experiment-matrix.yaml`, `scenario-catalog.yaml`, and
  `metric-catalog.yaml`.

## M6 contribution

The Godot development fixture implements the required sequence: load, observation, reachable signal
lens acquisition, early forbidden/stage-gated disclosure rejection with unchanged state, valid
quest progression, later permitted hint, save/load, JSONL replay, and duplicate/timeout injection.
Four Godot 4.7.1 fixtures now provide engine-local policy-mirror evidence: canonical, duplicate-ID,
timeout, and corrupt-save rejection. The retained canonical/duplicate/timeout packet and the fresh
corrupt-save negative run passed their authored checks. A stable-envelope projection is tested for
supported event types, but no live Python authorization transport has executed. This therefore
supports engine-local conformance and contract compatibility, not a cross-runtime integration path,
game generality, model efficacy, or player benefit.

A separate non-headless Godot 4.7.1 render replay now records three 1280x720 primary-track views:
`sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, and `sl-rc-003-authorized-hint`. The promoted
packet `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5` binds each PNG checksum to its
canonical scripted-fixture event ID, delivery index, validation outcome, and before/after
world-state hashes. The rejected-disclosure panel retains equal before/after hashes, whereas the
authorized-hint panel binds a valid commit to distinct before/after hashes. This evidence supports
`C-GAME-DESIGN-003`: authored engine render/state correspondence only. It is not live transport,
model inference, sampled player interaction, usability, immersion, G4, or G6 evidence.
The earlier immutable v1--v4 packets are retained but superseded after visual and provenance
audits; v5 is the selected publication capture evidence.

## Generated visual content

Four concept surfaces were generated offline with `god-tibo-imagen` after dry-run validation. Every
image has exact prompt, reference list, provider/model request, response ID, dimensions, bytes,
SHA-256, curation state, intended track, rights-review state, and limitations. The backend is
undocumented, so reproducibility means preserving the frozen bytes and manifest rather than
assuming pixel-identical regeneration.

The images are excluded from the primary structured-state experiment. They may enter only a
separately labelled, preregistered secondary VLM/UI track. Image quality is not an empirical game or
model result. Publication requires a venue-compatible AI-generated-content disclosure and human
rights/style review.

The three retained Godot screenshots are different artifacts: they are authored vector/text engine
renders in the primary track, contain no generated concept asset, and replay the frozen canonical
trace. Their inclusion documents a trace-linked presentation boundary; it does not evaluate visual
quality or player experience.

## Human-study boundary

Cycle 1 may create a blinded player/annotation surface, independent label/adjudication schema, and
consent/retention/deletion/opt-out protocol. Recruitment, personal identifiers, participant
telemetry, and human-experience results are prohibited until a later ethics and data-governance
gate.

## Evidence state

| Surface | Current permitted interpretation |
|---|---|
| Design/GDD | approved experimental protocol |
| Concept images | AI-generated design and secondary-track inputs |
| Static Godot/schema tests | implementation conformance |
| Executed Godot policy-mirror traces | authored engine-local state/replay conformance |
| Retained Godot render replay | authored engine render/state correspondence for three trace-bound 1280x720 views |
| Stable bridge projection test | schema compatibility only; no live Python transport |
| Live model/holdout/human results | absent; `TODO-RESULT` |
