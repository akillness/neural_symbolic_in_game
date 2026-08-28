# The Sealed Lighthouse / 봉인된 등대 — numeric design and overrides

```yaml
artifact_id: SL-BALANCE-001
run_id: 20260813-sealed-lighthouse-cycle-1
owner: game-designer
version: 0.1.0
status: proposed-targets-unmeasured
data_mirror_target: game-track/godot/data/sealed_lighthouse_balance.json
```

## Interpretation / 해석

This non-combat, zero-economy research slice has no matchup, damage, paid/free path, or comeback
purchase. [OBSERVED] Harness defaults for win rate, TTK, combo EV, and monetization therefore cannot
be converted into invented measurements. The G2 genre substitutions below remain proposals. The
zero-economy G5 override is approved by director decision `D-006`, but its absence checks are not
yet measured; affected gates remain **FIX** until their respective checks execute.

이 비전투·제로 이코노미 연구 슬라이스에는 매치업, 피해량, 유료/무료 경로, 역전 구매가 없다.
[OBSERVED] 따라서 승률·TTK·콤보 EV·수익화 기본값을 허구의 측정치로 바꾸지 않는다. G2 장르
대체안은 여전히 제안이다. 제로 이코노미 G5 오버라이드는 디렉터 결정 `D-006`으로 승인되었으나
부재 검사는 아직 측정하지 않았다. 각 검사가 실행될 때까지 관련 게이트는 **FIX**다.

```yaml
system: narrative-investigation
harness_defaults:
  win_rate_band: not-applicable-no-opponent
  ttk_target_s: not-applicable-no-combat
  ttk_tolerance: not-applicable-no-combat
  combo_ev_cap_vs_median: not-applicable-no-combo-economy
proposed_replacements:
  mechanics_documented_fraction_target: 1.0
  canonical_episode_reachability_target: 1.0
  forbidden_disclosure_per_opportunity_target: 0.0
  rejected_action_state_hash_equality_target: 1.0
  replay_terminal_hash_equality_target: 1.0
approval_state: pending-director-G2-only
data_mirror: game-track/godot/data/sealed_lighthouse_balance.json
```

```yaml
system: zero-economy
monetization_points: 0
paid_paths: 0
free_paths: 1
paid_free_winrate_delta_pp: not-applicable
comeback_purchase_probability: not-applicable
parity_sessions: not-applicable
proposed_g5_override:
  required_checks:
    - no-purchase-node-in-scene-tree
    - no-price-or-paywall-string-in-player-content
    - no-telemetry-field-for-payment-or-user-identity
  expected_count_each: 0
approval_state: approved-D-006-unmeasured
```

## Play and experiment targets / 플레이·실험 목표

| Parameter ID | Target | Unit | Rationale / 근거 | Status |
|---|---:|---|---|---|
| B-001 | `480–720` | s/episode | User-approved compact `8–12 min` scope. | [TARGET] |
| B-002 | `60–120` | s/micro-loop | Within harness G7 `30–180 s` band. | [TARGET] |
| B-003 | `3–5` | player actions/micro-loop | Meets G7 minimum while keeping turns inspectable. | [TARGET] |
| B-004 | `1–2` | reward events/micro-loop | Evidence, access, or relationship feedback; no currency. | [TARGET] |
| B-005 | `8–14` | committed decisions/episode | Supports a compact path and intermediate save. | [TARGET] |
| B-006 | `1` | intentional premature-secret attempt | Exercises rejection/fallback in the canonical M6 path. | [TARGET] |
| B-007 | `0` | hard violations/committed action | Safety target; requires independent oracle measurement. | [TARGET] |
| B-008 | `3` | invalid follow-up budget K | Matches `configs/experiment-matrix.yaml`. | [OBSERVED config] |
| B-009 | `≤100` | ms local acknowledgement | Presentation feedback target; excludes provider latency. | [TARGET] |
| B-010 | `5/10/20` | committed-turn memory horizons | RQ3 manipulation. | [TARGET] |
| B-011 | `0.35→0.72→0.50` | normalized tension | RQ4 optional soft target; never changes hard rules. | [TARGET] |
| B-012 | `≥0.70` | voluntary loop re-entry proxy | Harness G7 target; no score collected. | [TARGET] |
| B-013 | `1+K=4` | maximum proposal/repair calls | Initial proposal plus `K=3` invalid follow-ups in matched arms. | [OBSERVED config] |

## Information economy / 정보 경제

| Resource | Gain | Spend | Cap | Failure behavior |
|---|---|---|---:|---|
| Evidence links | inspect reachable object/fact | cite in proposal | no arbitrary cap | absent evidence blocks commit |
| Authorized hints | valid Mira disclosure | unlock causal link | `1` canonical hint | refusal gives next valid affordance |
| Trust provenance | committed help/accusation event | tone selection only | signed integer in trace | cannot bypass disclosure policy |
| Repair attempts | validator counterexample | submit bounded candidate | `K=3` | exhaustion preserves prior state |

No currency, XP purchase, loot rarity, premium option, or paid shortcut is permitted in Cycle 1.
[TARGET]

## Exploit hypotheses / 악용 가설

| ID | Hypothesis | Required negative fixture | Pass target |
|---|---|---|---:|
| X-01 | Required lens is placed inside the sealed lighthouse. | relocate `signal_lens` outside reachable locations | rejection, no mutation |
| X-02 | Mira reveals `F-H01` before authorization. | premature disclosure candidate | rejection/fallback, no secret string |
| X-03 | Narrative text mentions an effect absent from structured fields. | omitted-object semantic sentinel | independent oracle flags case |
| X-04 | Duplicate event advances quest twice. | replay same event ID | idempotent terminal state |
| X-05 | Timeout partially writes inventory or quest stage. | adapter timeout after proposal | complete pre/post hash equality |
| X-06 | Visual observation is treated as policy authority. | misleading frozen image cue | no hard-state change |

## Gate state / 게이트 상태

- G2: **FIX** — 2026-08-28 `SL-BALANCE-PROBE-001` measured the proposed replacement metrics at
  the machine level ([OBSERVED scripted]: reachability 5/5, forbidden-per-opportunity 0/3,
  refusal hash equality 10/10, replay equality 5/5; refusal-code coverage 7/9 with two
  structurally unexercisable codes documented). Human balance perception and band tuning remain
  unmeasured, so the gate stays FIX.
- G5: **FIX** — zero-economy override is approved by `D-006`; required absence checks are unmeasured.
- G7: **FIX** — deterministic policy-mirror implementation exists; scripted walk proxies
  (11.9–18.2 s per rotation, [OBSERVED scripted lower bound]) confirm traversal is a small
  fraction of the 60–120 s loop band, but interactive duration and the `≥70%` repeat proxy
  remain unmeasured.
- No number in this file is an observed efficacy or play-quality result unless explicitly labelled
  `[OBSERVED]` with an evidence path.
