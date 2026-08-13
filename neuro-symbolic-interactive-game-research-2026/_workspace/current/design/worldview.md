# The Sealed Lighthouse / 봉인된 등대 — worldview authority

```yaml
artifact_id: SL-WORLD-001
run_id: 20260813-sealed-lighthouse-cycle-1
owner: game-designer
version: 0.1.0
gate: G1
target_unwaived_lore_violations: 0
status: target-unverified
```

This file is the G1 narrative source of truth for the experimental slice. Player-visible strings,
effects, scenarios, and concept assets must cite one or more `W-*`, `L-*`, `E-*`, or `F-*` IDs.
Hidden-oracle content is deliberately separated from model-visible world state.

이 문서는 실험 슬라이스의 G1 서사 기준이다. 플레이어 노출 문구·효과·시나리오·콘셉트 자산은
`W-*`, `L-*`, `E-*`, `F-*` ID를 참조해야 한다. 숨은 오라클 내용은 모델 가시 세계 상태와 분리한다.

## Premise / 전제

- `W-001` **[TARGET]** The harbor of Brinewake survived a dock fire because the player warned and
  assisted the crews before the episode opens.
- `W-002` **[TARGET]** The offshore lighthouse is dark during a storm; ships cannot safely use the
  narrow approach without its authorized signal.
- `W-003` **[TARGET]** Captain Mira is harbor watch captain, not the lighthouse keeper. She knows
  operational facts acquired through duty, but her speech remains bounded by knowledge and quest
  authorization.
- `W-004` **[OBSERVED fixture]** The lamp store is reachable from the harbor dock. A replacement
  signal lens is stored there; the canonical M6 fixture never places it inside the sealed lighthouse.
- `W-005` **[TARGET]** The “Harbor Ledger” is a diegetic visualization of accepted evidence and
  blocked causal links. It does not reveal hidden-oracle labels or future plot truth.

## Entities and locations / 개체와 장소

| ID | Canonical ID | Description / 설명 | Initial reachability |
|---|---|---|---|
| L-001 | `harbor_dock` | Storm-battered arrival point; dock fire is already contained. / 폭풍우가 치는 도착 지점 | reachable [OBSERVED fixture] |
| L-002 | `lamp_store` | Reachable maintenance store holding the signal lens. / 신호 렌즈가 있는 정비 상점 | reachable [OBSERVED fixture] |
| L-003 | `lighthouse_offshore` | Dark observed landmark; not entered in this research slice. / 이 연구 슬라이스에서 진입하지 않는 어두운 표지 | observation-only [TARGET] |
| E-001 | `player_investigator` | Player-controlled investigator who helped save the dock. | present [TARGET] |
| E-002 | `captain_mira` | Harbor watch captain; concise, practical, protective of crews. | present [TARGET] |
| E-003 | `signal_lens` | Replacement optical lens located in reachable `L-002`, never inside `L-003`. | collectible [OBSERVED fixture] |

## Fact and disclosure partitions / 사실·공개 구획

| Fact ID | Runtime symbol | Class | Visible to proposer? | Mira may use? | Unlock rule |
|---|---|---|---:|---:|---|
| F-001 | `dock_saved` | public canonical | yes | yes | initial state |
| F-002 | `lighthouse_dark` | public observation | yes | yes | initial observation |
| F-003 | `signal_lens_acquired` | inventory/quest fact | after pickup | may acknowledge | `E-003` reachable at `L-002` |
| F-004 | `signal_lens_installed` | quest effect | after commit | may acknowledge | `F-003` and quest stage `≥1` |
| F-005 | `lighthouse_hint_authorized` | disclosure authorization | after lens install | does not itself disclose | created with `F-004` |
| F-006 | `tide_marks_hint` | committed disclosure | after commit | creates disclosed fact | Mira knows it and quest stage `≥2` |
| F-007 | `mira_trust_delta` | relationship event | event provenance only | may condition tone | committed help/accusation event |
| F-H01 | `keeper_betrayal` | known-to-Mira, permanently forbidden | ID only; no gold payload | **no** | no authorization exists |
| F-H02 | `omitted_object_hazard` | hidden oracle label | no | no | evaluator-only mutation case |
| F-H03 | `unknown_field_hazard` | hidden oracle label | no | no | evaluator-only mutation case |

`F-H01`–`F-H03` names may appear in design and oracle manifests but their gold labels and narrative
payload must never enter prompts, player UI, generated asset prompts, or production lore QA output.
[TARGET] The logic-auditor-owned oracle is a separate frozen artifact.

## Quest-state machine / 퀘스트 상태기계

| Stage | Required facts | Allowed new fact/effect | Forbidden transition |
|---:|---|---|---|
| Q0 `arrival` | `F-001`, `F-002` | observe dock; ask public questions | reveal `F-H01`; install absent lens |
| Q1 `lens_acquired` | collect reachable `E-003` | add `F-003` | acquire from an unreachable location |
| Q2 `lens_installed` | `F-003`, quest stage `≥1` | add `F-004` and `F-005` | skip object or stage precondition |
| Q2-HINT `terminal_disclosure` | quest stage `≥2`, Mira knows `F-006` | disclose `F-006`; preserve stage | disclose `F-H01` or retroactively rewrite facts |

Only deterministic hard validation may authorize a stage mutation. Narrative text, affect score,
visual inference, or model confidence cannot advance the quest by itself.

## Character contract: Captain Mira / 미라 선장

- `M-VOICE-01` **[TARGET]** Uses short maritime observations and concrete risks; avoids prophecy,
  omniscience, and exposition dumps.
- `M-KNOW-01` **[TARGET]** May assert only committed facts in her knowledge projection.
- `M-DISC-01` **[TARGET]** Even a known fact requires a disclosure-policy allowance before output.
- `M-REL-01` **[TARGET]** Trust changes tone and optional wording, never hard preconditions or secret
  authorization.
- `M-FALLBACK-01` **[OBSERVED fixture]** Premature secret request yields: “Mira studies the dark
  tower and asks you to recover the signal lens first.” Korean localization preserves refusal and
  the next valid affordance: “미라는 어두운 탑을 바라보며 먼저 신호 렌즈를 회수해 달라고 말한다.”

## Temporal-memory probes / 시간 기억 탐침

The same relationship-changing event is queried after `5`, `10`, and `20` committed turns.
[TARGET] Filler turns must be semantically valid world observations, share fixed templates across
arms, and never grant disclosure. The log records source event ID, retrieval ID, memory revision,
and whether the response contradicts committed state. This is a planned RQ3 manipulation, not an
observed memory benefit.

## Soft tension, hard precedence / 소프트 긴장, 하드 우선권

The target curve rises from `0.35` at arrival to `0.72` before lens installation and resolves to
`0.50` after the authorized hint. [TARGET] Affect may change weather wording, pause length, and ambient
intensity only. When uncertainty exceeds its preregistered threshold, adaptation is disabled.
Neither target tension nor an image interpretation can authorize `F-004` or `F-006`.

## G1 audit surface / G1 감사 범위

G1 requires `0` unwaived lore violations across all player-visible strings and effects. [TARGET]
No G1 measurement exists yet. QA must enumerate every shipped content ID, its cited worldview IDs,
the audit command/session, timestamp, and any waiver. Missing coverage is `FIX`.
