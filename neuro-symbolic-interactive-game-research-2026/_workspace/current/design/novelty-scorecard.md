# The Sealed Lighthouse / 봉인된 등대 — novelty scorecard

```yaml
artifact_id: SL-NOVELTY-001
run_id: 20260813-sealed-lighthouse-cycle-1
owner: game-designer
version: 0.1.0
gate: G8
survey_size: 7
frequency_threshold_max: 2
impression_target_median: 4.0
status: FIX-no-impression-data
```

## Measurement rule / 측정 규칙

The comparison evidence is the official-description audit in
`../intake/game-survey.md`. `Y` counts only an explicitly described feature; `NE` means not
evidenced and is not proof of absence. The frequency screen is therefore a bounded marketing/design
description audit, not a population estimate or code-level comparison.

비교 근거는 `../intake/game-survey.md`의 공식 설명 감사다. `Y`는 명시된 기능만 세며, `NE`는
근거가 없다는 뜻이지 부재 증명이 아니다. 빈도 선별은 제한된 제품 설명 조사이며 모집단 추정이나
코드 수준 비교가 아니다.

## Candidate elements / 후보 요소

| ID | Candidate / 후보 | Operational definition / 조작적 정의 | Explicit frequency | Threshold | State |
|---|---|---|---:|---:|---|
| N-01 | Diegetic auditable commit / 세계관 내 감사 가능 커밋 | A player-visible Harbor Ledger distinguishes proposed action, accepted evidence, typed rejection reason, bounded repair/fallback, and committed state without exposing the hidden oracle. | `0/7` | `≤2/7` | [INFERENCE] candidate passes frequency screen only |
| N-02 | Dual-track frozen perception / 이중 트랙 동결 지각 | The same structured episode is primary; a hashed, pre-generated image pack is enabled only in a secondary VLM/UI arm and never changes hard authority. | `0/7` | `≤2/7` | [INFERENCE] research-design candidate |
| N-03 | Investigation with persistent consequence | Clues and dialogue alter later access or character response. | `≥4/7` | `≤2/7` | [OBSERVED] not novel by this screen |
| N-04 | Visible answer/check feedback | The game makes a check or theory outcome legible. | `4/7` | `≤2/7` | [OBSERVED] not novel by this screen |

`N-01` is the single player-facing novelty candidate. `N-02` is a research protocol contribution
and must not be marketed as a fun mechanic without player evidence.

## Impression instrument / 인상도 도구

After the headless slice has a minimal debug UI, QA should present two counterbalanced versions:
`Ledger ON` and `Ledger MINIMAL`. [TARGET] Each anonymous evaluator answers:

1. “The game made cause and consequence unusually clear.” (`1–5`)
2. “The blocked action felt like part of the investigation rather than a system error.” (`1–5`)
3. “I could distinguish a proposed event from a committed event.” (`1–5`)

Primary G8 impression item: item 2, median target `≥4.0/5`. [TARGET] Report raw distribution, N,
order, missingness, and version hash; do not average the three items unless that composite is
preregistered. No participant collection is authorized in Cycle 1.

## Gate verdict boundary / 게이트 판정 경계

- Frequency component: **candidate evidence available**, subject to reviewer acceptance of the
  bounded official-description method. [INFERENCE]
- Impression component: **missing**. [OBSERVED]
- Overall G8: **FIX**. [OBSERVED]
- Allowed paper phrasing now: “We identify a low-frequency design candidate for future evaluation.”
- Forbidden phrasing now: “The Harbor Ledger is novel,” “players found it striking,” or any numeric
  quality claim.
