# The Sealed Lighthouse — comparable-game survey / 비교 게임 조사

```yaml
artifact_id: SL-SURVEY-001
run_id: 20260813-sealed-lighthouse-cycle-1
owner: game-designer
version: 0.1.0
retrieved_on: 2026-08-13
status: planning-evidence
claim_policy: "Official descriptions establish advertised features only; they do not prove implementation absence or quality."
```

## Epistemic legend / 인식론 표기

- **[OBSERVED]**: stated on the linked developer, publisher, or official store page.
- **[INFERENCE]**: a design interpretation drawn from the observed descriptions.
- **[TARGET]**: a requirement for *The Sealed Lighthouse*; not a measured result.
- `E1`: developer/publisher primary page. `E2`: official storefront or publisher-authored store
  announcement. All comparison material is link/reference-only; no art, text, or trademarks are
  licensed for reuse.

## Source register / 출처 목록

| ID | Comparable | Official evidence and observed feature / 공식 근거와 관찰 기능 | Level |
|---|---|---|---|
| GS-01 | *Disco Elysium* | [Official active-skill-check design note](https://discoelysium.com/devblog/2016/10/06/active-skill-checks): dialogue is treated as a game system, uses dice, and records world changes as modifiers. [OBSERVED] | E1 |
| GS-02 | *Pentiment* | [Xbox release article](https://news.xbox.com/en-us/2022/11/15/pentiment-available-now/): limited investigation time, conversational inquiry, chosen leads, deductions, and consequences extending across 25 years. [OBSERVED] | E1 |
| GS-03 | *The Case of the Golden Idol* | [Publisher-authored Steam announcement](https://store.steampowered.com/news/posts/?enddate=1665651593&feed=steam_community_announcements): freely searched frozen scenes and an interactive theory notebook that reports whether a theory is correct. [OBSERVED] | E2 |
| GS-04 | *Return of the Obra Dinn* | [Developer page](https://www.dukope.com/): first-person mystery adventure based on exploration and logical deduction. [OBSERVED] | E1 |
| GS-05 | *Roadwarden* | [Developer press kit](https://moralanxietystudio.com/presskit/roadwarden): illustrated text RPG combining inventory puzzles, dialogue choices, abilities, survival resources, and time-limited quests. [OBSERVED] | E1 |
| GS-06 | *Citizen Sleeper* | [Official Steam page](https://store.steampowered.com/app/1578650/Citizen_Sleeper/): cycles, assignable dice, clocks, friendships, and actions that shape other characters and the station. [OBSERVED] | E2 |
| GS-07 | *Heaven's Vault* | [Developer page](https://www.inklestudios.com/heavensvault/): investigation, translation with consequential wrong answers, characters that remember choices, and an adaptive narrative. [OBSERVED] | E1 |

## Advertised-feature matrix / 공식 설명 기반 기능 행렬

`Y` means the cited page explicitly evidences the feature. `NE` means *not evidenced on the cited
page* and must not be read as proof that the game lacks it.

| ID | Investigation / 조사 | Dialogue-choice system / 대화 선택 | Persistent consequence or memory / 지속 결과·기억 | Explicit cycle or time budget / 주기·시간 | Visible answer/check feedback / 판정 피드백 | Pre-commit symbolic counterexample / 커밋 전 기호 반례 | Deterministic research trace / 결정론 연구 추적 |
|---|---:|---:|---:|---:|---:|---:|---:|
| GS-01 | Y | Y | Y | NE | Y | NE | NE |
| GS-02 | Y | Y | Y | Y | NE | NE | NE |
| GS-03 | Y | NE | NE | NE | Y | NE | NE |
| GS-04 | Y | NE | NE | NE | NE | NE | NE |
| GS-05 | Y | Y | NE | Y | NE | NE | NE |
| GS-06 | Y | NE | Y | Y | Y | NE | NE |
| GS-07 | Y | Y | Y | NE | Y | NE | NE |
| **Explicit-frequency / 명시 빈도** | **7/7** | **4/7** | **4/7** | **3/7** | **4/7** | **0/7** | **0/7** |

## Design reading / 설계 해석

1. **[INFERENCE]** Investigation, consequential choice, and state-responsive characters are genre
   expectations; they are not novelty claims.
2. **[INFERENCE]** None of the seven cited public descriptions advertises the combined player-facing
   pattern `proposal → deterministic rejection reason → bounded repair/fallback → traceable commit`.
   This is a *public-description frequency of 0/7*, not a reverse-engineering claim.
3. **[TARGET]** The game's novelty candidate is an optional diegetic “Harbor Ledger” view that makes
   the commit boundary legible without exposing hidden oracle labels.
4. **[TARGET]** The primary paper track remains structured state/text; frozen images are isolated in
   a secondary VLM/UI track. This dual-track protocol is research infrastructure, not a claim of
   superior play quality.

## Survey limits / 조사 한계

- No comparative game was reverse engineered or playtested in this pass. [OBSERVED]
- Official marketing pages under-report internal architecture; `NE` cannot support an absence
  claim. [OBSERVED]
- G8 also requires a QA impression median of at least `4.0/5`; no player or QA score exists.
  Current G8 status is therefore **FIX**, regardless of the `0/7` advertised-frequency count.
- The comparison set is purposive, not a statistical sample of narrative games. Any paper use must
  describe it as a bounded design benchmark, not a market-wide prevalence estimate.

