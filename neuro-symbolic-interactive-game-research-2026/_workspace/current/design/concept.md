# The Sealed Lighthouse / 봉인된 등대 — concept

```yaml
artifact_id: SL-CONCEPT-001
run_id: 20260813-sealed-lighthouse-cycle-3
owner: game-designer
version: 0.2.0
authority: cycle-concept
status: target-not-playtest-result
```

## High concept / 한 줄 콘셉트

**[TARGET] EN.** An `8–12 min` turn-based narrative investigation micro-RPG in which the player
restores a harbor-side signal and earns a tide route by collecting authorized evidence and
questioning Captain Mira, while the offshore lighthouse remains sealed. A visible
proposal/validation boundary prevents impossible actions and premature secrets from mutating the
world.

**[TARGET] KO.** 플레이어가 허가된 증거를 수집하고 미라 선장에게 질문해 항구 측 신호를
복구하고 썰물 항로를 획득하는 `8–12분` 턴 기반 내러티브 수사 마이크로 RPG다. 앞바다의
등대는 끝까지 봉인된 채로 남는다. 플레이어가 이해할 수 있는 제안/검증 경계는 불가능한
행동과 시기상조 비밀이 세계를 변경하지 못하게 한다.

## Product role / 제품 역할

- **[TARGET] Paper instrument:** expose TRACE-RPG's proposal, evidence, validation, repair,
  commit/fallback, replay, cost, and latency fields through a compact playable episode.
- **[TARGET] Game prototype:** make constraint feedback feel like investigative deduction rather
  than a developer error message.
- **[TARGET] Public-safe presentation:** enrich the harbor with procedural geometry, VFX, audio,
  focus, and responsive UI while keeping those systems outside canonical state.
- **[TARGET] Dual-track fixture:** primary experiments use structured state/text; a separately frozen
  image pack supports a secondary VLM/UI study only.
- **[OBSERVED] Evidence boundary:** no live model, independent human label, participant result,
  browser performance result, or immersion result is established by this design document.

## Design pillars / 설계 원칙

| ID | Pillar / 원칙 | Player promise / 플레이어 약속 | Research obligation / 연구 의무 |
|---|---|---|---|
| P-01 | Legible causality / 읽히는 인과 | Every consequential option shows what evidence it relies on after resolution. | Log evidence IDs without leaking the hidden oracle. |
| P-02 | Safe failure / 안전한 실패 | A blocked action produces an in-world fallback and never destroys progress. | Prove pre/post canonical-state hash equality on rejection/timeout. |
| P-03 | Earned disclosure / 획득한 공개 | Mira reveals only what the current quest state authorizes. | Separate NPC knowledge, allowed disclosure, and hidden semantic labels. |
| P-04 | Compact consequence / 압축된 결과 | A small action changes accessibility, trust, or clue interpretation within minutes. | Preserve ordered event provenance and test `5/10/20`-turn memory variants. |
| P-05 | Reproducible atmosphere / 재현 가능한 분위기 | Storm, harbor signal, and ledger feedback support tension without changing rules. | Procedural presentation and frozen visual inputs remain soft context; hard validity wins. |

## Audience and play posture / 대상과 플레이 태도

The primary player is comfortable reading short dialogue and comparing clues. [TARGET] The episode
supports five test postures without assigning player-quality labels: evidence-first investigator,
dialogue-first negotiator, boundary-probing skeptic, shortest-path optimizer, and completionist
explorer. These are QA rotations, not psychometric categories.

## Canonical cadence / 정식 진행 리듬

`observe → inspect or ask → propose → validate → repair/fallback → commit → feedback/reward`

One micro-loop lasts `60–120 s`, contains at least `3` player actions, and ends in at least `1`
information or access reward. [TARGET] Four linked micro-loops form the `8–12 min` episode target.

## Minimum episode / 최소 에피소드

| Beat | Player-facing event / 플레이 사건 | Hard-system purpose / 하드 시스템 목적 |
|---:|---|---|
| 1 | The rescued harbor is reachable; the offshore lighthouse is dark and sealed. | Load frozen initial state. |
| 2 | Visit the reachable lamp store and recover the signal lens. | Acquire a reachable object with provenance. |
| 3 | Ask Mira for `keeper_betrayal` and `tide_marks_hint` too early. | Reject forbidden and stage-gated disclosure with no mutation. |
| 4 | Install the recovered lens in the harbor-side signal mount. | Advance quest stage through a valid object-dependent commit. |
| 5 | Receive the now-authorized `tide_marks_hint`. | Exercise knowledge and disclosure policy. |
| 6 | Read the earned tide-route affordance while the lighthouse remains sealed. | End the research slice without inventing a downstream chapter. |
| 7 | Save and reload the terminal canonical state. | Exercise save/load continuity. |
| 8 | Replay JSONL and compare terminal hashes. | Produce engine evidence independently of model quality. |

## Explicit non-goals / 명시적 비목표

- Entering, lighting, or reopening the offshore lighthouse in this episode.
- Real-time combat, procedural combat balance, open-world volume, monetization, or a polished
  commercial release.
- Runtime image generation or dependence on `god-tibo-imagen` during a game or experiment.
- Participant recruitment, personal telemetry, or any human-efficacy claim.
- Treating a production lore check or controller validator as the independent semantic oracle.
- Promoting `C-RESULT-001`–`C-RESULT-005` before the preregistered evidence exists.

## Success language / 성공 표현 규칙

Before execution, use “designed to,” “target,” or “planned.” After execution, a claim may become
`[OBSERVED]` only when it cites the exact command/session, frozen inputs, trace, reviewer, and
measurement. Automated UI, VFX, audio, screenshot, or browser checks remain engineering
conformance; they do not establish that the episode is fun, immersive, usable, or effective.
