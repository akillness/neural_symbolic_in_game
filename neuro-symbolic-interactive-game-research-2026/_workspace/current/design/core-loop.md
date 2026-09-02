# The Sealed Lighthouse / 봉인된 등대 — core loop

```yaml
artifact_id: SL-LOOP-001
run_id: 20260813-sealed-lighthouse-cycle-1
owner: game-designer
version: 0.2.0
gate: G7
target_period_s: [60, 120]
target_actions_per_loop: [3, 5]
target_reward_events_per_loop: [1, 2]
target_repeat_proxy_min: 0.70
status: modeled-not-playtested
```

## Loop grammar / 루프 문법

```text
READ STATE → OBSERVE → SELECT EVIDENCE/ACTION → PROPOSE
          → VALIDATE → {COMMIT → REWARD + CONTRIBUTION | REPAIR/FALLBACK → LEGIBLE REASON + RULE}
          → READ NEW OR UNCHANGED STATE
```

**[TARGET]** Each loop takes `60–120 s`, contains `3–5` explicit player actions, and emits `1–2`
reward events. A reward is information, access, or relationship feedback—not currency. The player
can voluntarily enter a new loop after reading the resulting state. **[OBSERVED]** No repeat-rate
measurement exists; G7 remains **FIX**.

## Atomic interaction / 원자 상호작용

| Step | Player view / 플레이어 화면 | Research event | Required trace fields |
|---:|---|---|---|
| 1 | Current location, Mira state, evidence ledger | `observation` | event/build/state IDs, visible facts, image-pack ID or `none` |
| 2 | Choose inspect, collect, ask, present, or travel | `proposal_request` | prompt/policy versions, seed, budget, track |
| 3 | Candidate appears as intended action, not canonical truth | `candidate` | model/revision, structured fields, tokens, latency |
| 4 | Ledger shows accepted link or safe reason | `validation` + optional `repair` | validator/oracle separation, errors, attempt index |
| 5 | World changes only on authorization | `commit` or `fallback` | pre/post state hashes, evidence, quest stage |
| 6 | Clue/access/tone feedback | next `observation` | reward type, presentation latency, prior event link |

## Four episode loops / 네 개 에피소드 루프

| Loop | Actions (minimum sequence) | Reward event | Hard test |
|---|---|---|---|
| CL-01 Survey the harbor / 항구 조사 | observe dark lighthouse → visit lamp store → collect signal lens | inventory fact and quest stage `1` | reachability, evidence provenance |
| CL-02 Test the boundary / 경계 시험 | question Mira → request forbidden/stage-gated facts → inspect fallback | safe refusal and next affordance | disclosure rejection, unchanged hash |
| CL-03 Earn the hint / 단서 획득 | install signal lens → authorize hint → ask Mira again | `tide_marks_hint` and quest stage `2` | object precondition, knowledge, disclosure order |
| CL-04 Close and reproduce / 종료·재현 | read next-route affordance → save/reload → replay trace | terminal state and replay receipt | persistence and terminal hash equality |

## Player-facing failure contract / 플레이어 실패 계약

1. A rejected proposal cannot consume evidence, change inventory, alter trust, or advance quest
   stage. [OBSERVED in the authored early-disclosure fixture; TARGET universally]
2. The fallback explains the next valid affordance but cannot quote a hidden oracle label or reveal
   the correct secret. [OBSERVED fixed fallback; TARGET for generated text]
3. A timeout, parse error, or exhausted `K=3` repair path returns the same canonical state plus a
   typed failure receipt. [TARGET]
4. Duplicate event IDs are process-local idempotent in the authored fixture; persistent
   cross-process idempotency remains a live-adapter target. [OBSERVED + TARGET]

## Canonical M6 execution path / 정식 M6 실행 경로

| Step | Fixture ID | Expected evidence | Current status |
|---:|---|---|---|
| 1 | `SL-M6-LOAD` | frozen initial-state hash | [OBSERVED authored policy mirror] |
| 2 | `SL-M6-OBSERVE` | harbor observation event | [OBSERVED authored policy mirror] |
| 3 | `SL-M6-ACQUIRE` | reachable evidence/object commit | [OBSERVED authored policy mirror] |
| 4 | `SL-M6-REJECT` | forbidden-secret rejection and pre/post hash equality | [OBSERVED authored policy mirror] |
| 5 | `SL-M6-STAGE` | valid quest-stage commit | [OBSERVED authored policy mirror] |
| 6 | `SL-M6-HINT` | authorized Mira hint | [OBSERVED authored policy mirror] |
| 7 | `SL-M6-SAVELOAD` | valid save equality and corrupt-save pre-mutation rejection | [OBSERVED authored policy mirror] |
| 8 | `SL-M6-REPLAY` | JSONL terminal hash equality | [OBSERVED authored policy mirror] |
| 9 | `SL-M6-FAULTS` | duplicate, timeout, corrupt-save, and fallback receipts | [OBSERVED authored policy mirror] |

The engine-local path is observed under
the set selected by `engineering/tech-verification/current.json`; the corrupt-save run is a fresh test artifact.
This demonstrates an authored Godot policy mirror and stable-envelope compatibility, not a live
Python authorization integration path or RQ1–RQ5 model efficacy.

## QA rotations / QA 플레이 유형

| Archetype | Distinct strategy | Adversarial focus |
|---|---|---|
| A-01 Evidence-first investigator | collect every reachable clue before dialogue | omission and reachability |
| A-02 Dialogue-first negotiator | question Mira as early as possible | premature disclosure |
| A-03 Boundary-probing skeptic | repeat invalid and duplicate requests | idempotency and safe fallback |
| A-04 Shortest-path optimizer | minimize commits and revisits | skipped prerequisite |
| A-05 Completionist explorer | revisit every observation after state change | stale state and memory |

These five rotations satisfy the *planned* G3 test breadth but do not establish independent
viability or dominance. Those require executed sessions and measurements.

## Contribution legibility / 기여 가독성

After each commit the ledger appends a **CONTRIBUTION clause** (`CONTRIBUTION #N | <fact labels> | STAGE a>b | CHAIN k/3`, `STAGE n` when unchanged, then `UNLOCKED | <next valid entry>`). After each hold, a **RULE LEARNED** line names the predicate gate that held the entry and states one testable rule (`RULE RECALLED (n)` on repeats). A persistent **CASE CHAIN** HUD line tracks three investigation links (LENS, MOUNT, LEAD) by fill state plus `RULES LEARNED n`. At episode end the **two-part receipt** lists the investigator's contributions and rules learned before the technical snapshot.

Labels come from the `FACT_LABEL` table, rule sentences from the `RULE_BY_CODE` table (grouped by `GATE_BY_CODE` gate), and the chain is a live projection of committed facts onto three checkpoints; `contribution_delta` is a pure diff of the two snapshots the hard writer returned. Source: `_workspace/current/intake/aside-feedback-2026-09-02-game-ui-fun-contribution.md` (patterns 1, 2, E; recommendations 1–4, 9).

This augmentation does not change mechanics, logic, or quest flow. It reads committed snapshots and hold history, never mutating state or exposing oracle labels (keeper_betrayal, omitted_object_hazard, unknown_field_hazard). The surfaces are designed to increase perceived agency and reduce frustration around hold rejection—a causal hypothesis documented in `game-design-hypothesis.json` (H-CONTRIB-01, H-RULE-02, H-CHAIN-03, H-RECEIPT-04).

Status: `implemented-engineering-structure-human-impact-unverified`.
