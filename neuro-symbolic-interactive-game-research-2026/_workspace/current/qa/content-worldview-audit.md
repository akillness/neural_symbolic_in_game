# Player-visible content to worldview audit / 플레이어 노출 콘텐츠–세계관 감사

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Timestamp: 2026-08-13 Asia/Seoul  
Method: repository enumeration plus manual semantic review  
Verdict: `FIX` for a playable release; `PASS` for the enumerated headless fixture surface only

| Surface | Runtime/content anchor | Worldview IDs | Review |
|---|---|---|---|
| Scenario title | `sealed_lighthouse.json:title_en/title_ko` | `W-002`, `L-003` | aligned |
| Initial observation | `experimental_game_runner.gd:observation_en/ko` | `W-002`, `W-004`, `L-001`, `L-002` | aligned |
| Captain Mira fallback | `sealed_lighthouse.json:safe_fallback` | `E-002`, `E-003`, `M-FALLBACK-01` | aligned; no forbidden payload |
| Reachable signal lens | `initial_state.world.object_locations.signal_lens` | `W-004`, `E-003`, `F-003` | aligned |
| Authorized tide hint | `tide_marks_hint` event path | `F-005`, `F-006`, `M-DISC-01` | aligned after Q2 |
| Concept environment | `SL-C01` | `W-002`, `L-001`, `L-003` | concept-only; rights review pending |
| Captain Mira sheet | `SL-C02` | `E-002`, `M-VOICE-01` | concept-only; representation review pending |
| Investigation UI | `SL-C03` | `W-005` | layout-only; blinding/accessibility untested |
| Evidence icon sheet v2 | `SL-C04` | `E-003`, `F-002`–`F-006`, `W-005` | v1 rejected; v2 requires labelled icon-semantic test |

The enumerated headless strings and canonical visible concepts have `0` unwaived lore conflicts in
this audit. This is not a complete playable-build G1 pass: no localized content export, interactive
UI copy, accessibility state, or future generated/model text was audited. Hidden oracle labels are
not treated as player-visible lore.
