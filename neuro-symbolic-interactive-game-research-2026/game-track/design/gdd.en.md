# The Sealed Lighthouse — Authoritative Experimental Game Design Document

```yaml
pair_id: SL-GDD-001
language: en
version: 0.2.0
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

The public-safe snapshot records the omitted concept IDs `SL-C01`, `SL-C02`, `SL-C03`, and
`SL-C04` under `../assets/concepts/public-exclusion.json`; their generated bytes remain outside the
public tree pending human review. [OBSERVED artifact] Each promoted internal output requires exact prompt, negative constraints, reference-input list, generator/provider
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

## 11. Contribution legibility

The player investigation is operationalized as a sequence of committed decisions (CONTRIBUTION clauses) and rejected attempts (RULE LEARNED). Three surfaces expose these patterns during and after gameplay:

1. **CASE CHAIN line**: persistent HUD element showing three investigation links (`LENS`, `MOUNT`, `LEAD`) whose fill state mirrors the committed facts `signal_lens_acquired`, `signal_lens_installed`, and `tide_marks_hint`; the same line carries `RULES LEARNED n | <gates>`. Re-derived from the committed snapshot on every presentation sync. ASCII-only, display-only, no hidden labels. [OBSERVED structure]

2. **CONTRIBUTION clause**: appended under every `ENTRY #N | COMMITTED` line as `CONTRIBUTION #N | <fact labels> | STAGE a>b | CHAIN k/3` (`STAGE n` when the stage is unchanged) followed by `UNLOCKED | <next valid entry>`. Fact labels are emitted only from the public `FACT_LABEL` allowlist (e.g., "Signal lens secured"); unknown or future fact IDs stay internal and render as generic "State recorded" copy. The delta is the pure function `contribution_delta(prior_state, next_state)` over the two snapshots the hard writer returned, so it can neither invent a fact nor expose a sealed one. [OBSERVED structure]

3. **RULE LEARNED line**: appended after the first hold on a predicate gate as `RULE LEARNED | <GATE>: <rule>` (e.g., `RULE LEARNED | KNOWLEDGE: A speaker can only disclose what they know.`); later holds on the same gate render `RULE RECALLED (n) | ...`. The gate comes from `GATE_BY_CODE` (Table II predicate families) and the sentence from the authored `RULE_BY_CODE` table; neither names an oracle label. [OBSERVED structure]

The end-card receipt contains two new sections before the technical receipt:

- **INVESTIGATOR'S CONTRIBUTION**: lists all CONTRIBUTION lines with commit numbers and fact labels, enabling players to review their decision sequence.
- **RULES LEARNED**: sorted list of unique gates discovered, showing policy boundaries in one place.

These surfaces do not mutate state, expose hidden labels (`keeper_betrayal`, `omitted_object_hazard`, `unknown_field_hazard`), or add new mechanics. They derive from committed snapshots and hold history; `SL-PLAY-EVAL-001` checks `contribution_delta_is_pure_and_names_facts`, `hold_teaches_rule_for_its_gate`, and `case_chain_mirrors_committed_snapshot` guard exactly that. Saves still carry only canonical state: after a load, `CASE CHAIN` is re-derived from the loaded facts, whereas the ledger history, the per-entry contribution list, the rules-learned set, and the ENTRIES/HOLDS counters are session-local presentation memory that restarts with the session. [OBSERVED engineering conformance] Their effect on perceived competence, agency, or frustration is unmeasured. [TARGET]

Evidence of player perception is collected via post-episode questions (see Table SL-GDD-T4) and open-ended written reflection, not automated telemetry. Hypothesis H-CONTRIB-01 through H-RECEIPT-04 in `game-design-hypothesis.json` operationalize the causal links between visibility and perceived competence/rule discovery. [TARGET]

| Table SL-GDD-T4 ID | Metric | Target | State |
|---|---|---|---|
| B-014 | CONTRIBUTION clause appears with the commit stamp | same rendered acknowledgement cycle, assessed under the inherited B-009 local-feedback budget | [TARGET] |
| B-015 | Post-episode comprehension: player explains the causality of ≥2 actions using visible CONTRIBUTION/RULE surfaces | study-owner sufficiency rule frozen before recruitment; open-ended causal explanation required | [TARGET] |
| B-016 | RULE LEARNED distinct gates per episode | descriptive count only; 0 is valid on a hold-free golden path, and >0 requires an encountered distinct hold gate | [TARGET] |
| B-017 | CASE CHAIN links | exactly 3 (LENS, MOUNT, LEAD) matching `CASE n/3` count | [TARGET] |
