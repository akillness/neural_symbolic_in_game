# The Sealed Lighthouse — Authoritative Experimental Game Design Document

```yaml
pair_id: SL-GDD-001
language: en
version: 0.1.0
run_id: 20260813-sealed-lighthouse-cycle-1
engine: Godot 4.x headless-first
episode_target_minutes: [8, 12]
evidence_state: TARGET-DESIGN-PLUS-OBSERVED-AUTHORED-ENGINE-FIXTURE
```

## 1. Purpose and authority

This GDD defines the stable product, interaction, and paper-reference surface for *The Sealed
Lighthouse*. The live G1 lore authority is
`../../_workspace/current/design/worldview.md`; numeric proposals are in
`../../_workspace/current/design/balance-sheet.md`. When the live cycle changes an ID or invariant,
this companion must be updated before it is cited. [TARGET]

The game is a turn-based narrative investigation micro-RPG and a TRACE-RPG systems probe. It is not
a production game, human-efficacy study, or model-quality result. [OBSERVED scope]

## 2. Player proposition

After helping save Brinewake's dock, the player investigates a dark lighthouse during a storm.
They recover a reachable signal lens from the lamp store, ask Captain Mira for information,
experience one intentional forbidden/stage-gated disclosure rejection, install the lens, and earn
the authorized `tide_marks_hint`. The research slice ends with a next-route affordance while the
lighthouse remains sealed. [TARGET]

The intended cadence is:

`observe → inspect/ask → propose → validate → repair/fallback → commit → feedback`

Four `60–120 s` micro-loops form an `8–12 min` target episode. Each loop contains `3–5` player
actions and `1–2` information/access/relationship rewards. [TARGET]

## 3. Design invariants

| ID | Invariant | Enforcement |
|---|---|---|
| GDI-01 | Only a valid `commit` mutates canonical state. | Current fixture: Godot authored policy mirror; target: research-runtime authorization; both use pre/post state hashes. [OBSERVED fixture + TARGET transport] |
| GDI-02 | Rejection, timeout, parse failure, exhausted repair, and duplicate delivery cannot partially mutate state. | Whole-state equality and idempotency fixtures. [TARGET] |
| GDI-03 | NPC knowledge and disclosure permission are separate. | `captain_mira` knowledge projection plus quest-stage disclosure policy. [TARGET] |
| GDI-04 | Soft affect, visual interpretation, novelty, and style never override hard validity. | Authority-boundary tests. [TARGET] |
| GDI-05 | Research and Godot runtimes exchange only versioned JSON/JSONL records. | Schema validation and deterministic replay. [TARGET] |
| GDI-06 | The primary structured track and secondary frozen-image track use disjoint manifests. | Manifest IDs and SHA-256 checks. [TARGET] |

## 4. World and quest model

Canonical runtime locations are `harbor_dock` and `lamp_store`; `lighthouse_offshore` is an observed,
non-entered landmark in this slice. Canonical entities are `player_investigator`, `captain_mira`,
and `signal_lens`. The lens begins in the reachable lamp store, never inside the sealed lighthouse.
[OBSERVED fixture]

| Table SL-GDD-T1 stage | Preconditions | Authorized outcome | Required negative case |
|---|---|---|---|
| Q0 `arrival` | `dock_saved`, `lighthouse_dark` | observe and ask public questions | no absent-lens install |
| Q1 `lens_acquired` | reachable `signal_lens` collection | `signal_lens_acquired` | reject unreachable acquisition |
| Q2 `lens_installed` | lens inventory + stage `≥1` | `signal_lens_installed`, `lighthouse_hint_authorized` | reject skipped object/stage prerequisite |
| Q2-HINT `terminal_disclosure` | stage `≥2`; Mira knows `tide_marks_hint` | disclose `tide_marks_hint`, preserve stage | reject `keeper_betrayal` and retroactive rewrite |

`keeper_betrayal` is known to Mira but permanently forbidden; only its test ID, not its gold
narrative payload, may be exposed during fixture wiring. `omitted_object_hazard` and
`unknown_field_hazard` are evaluator-only labels. Their gold payloads must not enter prompts,
player UI, image prompts, or production lore QA. [TARGET]

## 5. Player actions and feedback

The conceptual action set is `OBSERVE`, `INSPECT`, `COLLECT`, `ASK`, `PRESENT`, `TRAVEL`, `SAVE`,
and `LOAD`; `REPLAY` belongs to the inspector surface. [TARGET] The exact wire enum is owned by the
versioned bridge schema.

Every interaction shows a local acknowledgement within `≤100 ms` as a presentation target. This
acknowledgement is not a model response and does not imply request completion. Proposed causal
links are dotted, committed links are solid amber, and rejected links stop in coral with a neutral
reason and next valid affordance. Hidden-oracle labels are never shown. [TARGET]

Captain Mira uses short, practical maritime language. Trust may condition tone but cannot grant a
secret or satisfy a quest precondition. Her canonical premature-request fallback directs the
player to recover the signal lens without revealing the keeper betrayal. [TARGET]

## 6. Dual-track content contract

| Table SL-GDD-T2 track | Inputs | Authority | Runtime generation | Intended evidence |
|---|---|---|---|---|
| Primary structured | canonical JSON state, text observation, authored non-generated symbolic markers | encoded policy and deterministic validator | none | planned RQ1–RQ5 confirmatory evaluation |
| Secondary VLM/UI | primary inputs plus reviewed SHA-256-frozen concept images | identical hard authority; images are soft observation | forbidden | exploratory modality/UI evaluation |

The concept set exists under `../assets/concepts/` with IDs `SL-C01`, `SL-C02`, `SL-C03`, and
`SL-C04`. [OBSERVED artifact] Each output requires exact prompt, negative constraints, reference-input list, generator/provider
metadata, UTC timestamp, dimensions, bytes, SHA-256, curation state, intended track, rights review,
AI-use disclosure, and `runtime_eligible: false`. [TARGET]

## 7. Numeric specification

| Table SL-GDD-T3 ID | Value | Meaning | State |
|---|---:|---|---|
| B-001 | `480–720 s` | episode duration | [TARGET] |
| B-002 | `60–120 s` | micro-loop duration | [TARGET] |
| B-003 | `3–5` | actions per micro-loop | [TARGET] |
| B-004 | `1–2` | reward events per micro-loop | [TARGET] |
| B-005 | `8–14` | committed decisions per episode | [TARGET] |
| B-006 | `1` | intentional premature-secret attempt in M6 path | [TARGET] |
| B-008 | `K=3` | invalid follow-up/repair budget | [OBSERVED config] |
| B-009 | `≤100 ms` | local acknowledgement target | [TARGET] |
| B-010 | `5/10/20 turns` | relationship/fact memory horizons | [TARGET] |
| B-011 | `0.35→0.72→0.50` | optional normalized tension curve | [TARGET] |
| B-013 | `1+K=4` | maximum calls in matched retry/repair/full arms | [OBSERVED config] |

There is no combat or economy. Matchup win rate, TTK, combo EV, paid/free delta, comeback purchase,
and parity-session metrics are not applicable. Director decision `D-006` approves the zero-economy
G5 override, but the replacement absence checks are unmeasured. G2 and G5 remain `FIX` until their
required checks execute. [OBSERVED status]

## 8. Trace and telemetry

Every assigned episode must preserve proposal, evidence, validation, repair, commit/fallback,
model and revision, seed, cost, token usage, request latency, engine latency, build hash, pre/post
state hashes, save hash, replay hash, and failure class. [TARGET]

Engine correctness and model efficacy are separate estimands. A successful Godot replay can support
Stage 6 M6 but cannot support `C-RESULT-001`–`C-RESULT-005`. [OBSERVED claim boundary]

## 9. Accessibility and presentation

The visual direction is an original “maritime evidence folio”: engraved chart linework, muted
gouache weather, wet slate, oxidized brass, and one amber signal accent. [TARGET] Color always has
text/icon redundancy; target controls are at least `44×44 px`, body text is `18 px` at `1×`, and
motion reduction/subtitles are included in the first playable debug surface. [TARGET]

## 10. Acceptance without overclaiming

The authored headless slice has executed the M6 sequence through load, signal-lens acquisition,
forbidden/stage-gated disclosure safely, installs the lens, reveals the authorized hint, saves/loads,
operation replay, terminal-hash comparison, duplicate delivery, timeout/fallback, and corrupt-save
rejection. [OBSERVED authored fixture] It is paper-result-ready only after the separately frozen
holdout, independent oracle, model arms, analysis, and review gates in `SL-ORACLE-001` execute.

Current result state: **no player, live-model, independent-oracle, visual-model, or engine-performance
efficacy result is claimed by this GDD.** [OBSERVED]
