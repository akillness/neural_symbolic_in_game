# Player-visible content to worldview audit / 플레이어 노출 콘텐츠–세계관 감사

Run ID: `20260813-sealed-lighthouse-cycle-3`
Timestamp: 2026-08-13 Asia/Seoul
Method: source enumeration plus manual semantic review; clean exported-browser review pending
Verdict: `FIX` for G1; `0` known conflicts in reviewed public-safe runtime source, `1` candidate-art
conflict quarantined from runtime

| Surface | Runtime/content anchor | Worldview IDs | Review |
|---|---|---|---|
| Scenario title | `sealed_lighthouse.json:title_en/title_ko` | `W-002`, `L-003` | aligned |
| Arrival narration | `game_3d.gd` intro | `W-001`, `W-002`, `W-004`, `L-001`, `L-002` | harbor survived; offshore lighthouse explicitly dark |
| Captain Mira dialogue/fallback | `game_3d.gd`, `sealed_lighthouse.json:safe_fallback` | `W-003`, `E-002`, `E-003`, `M-FALLBACK-01` | aligned; no forbidden payload |
| Reachable signal lens | initial object state + lens pickup | `W-004`, `E-003`, `F-003` | aligned |
| Harbor signal mount | lens-install interaction and narration | `W-004`, `F-004`, `F-005` | aligned only when described as harbor-side signal; it does not light the lighthouse |
| Authorized tide hint | `tide_marks_hint` event path | `F-005`, `F-006`, `M-DISC-01` | aligned after quest stage 2 |
| Episode ending | `game_3d.gd:_finish_episode` | `W-002`, `L-003`, `F-006` | aligned: lighthouse remains sealed; tide marks reveal the next route |
| Browser start gate and controls | `harbor_ledger_ui.gd` | `W-005` | copy does not claim hidden truth; Korean glyph/browser rendering unverified |
| Commit/refusal feedback | ledger + focus/VFX/audio cues | `W-005`, `E-003` | semantic color has text/icon redundancy; human readability unverified |
| `SL-C01` environment candidate | generated concept pack | `W-002`, `L-001`, `L-003` | **conflict/quarantine:** “one amber light” can depict a lit offshore lighthouse; excluded from runtime/Web and must be regenerated or curated before use |
| `SL-C02` Mira candidate | generated concept pack | `E-002`, `M-VOICE-01` | concept-only; representation/rights review pending; public-safe excluded |
| `SL-C03` UI candidate | generated concept pack | `W-005` | layout-only; blinding/accessibility untested; public-safe excluded |
| `SL-C04` v2 icon candidate | generated concept pack | `E-003`, `F-002`–`F-006`, `W-005` | v1 rejected; v2 still requires labelled icon-semantic and rights review; public-safe excluded |
| `pack-3d` candidates | generated 3D presentation pack | presentation only | `runtime_eligible: false`; Web/`--public-safe` guard prevents loading |

## Corrective ruling

The prior phrase “reopens a dark lighthouse” and any runtime interpretation of a lit `SL-C01` are
not canonical. The slice restores a **harbor-side signal**, authorizes the tide-marks clue, and earns
the next route while the **offshore lighthouse remains dark and sealed**. Decision `D-030` binds
future copy, captures, and candidate curation to this reading.

## Remaining G1 gap

Static review of the current source does not replace an exported player-visible string inventory.
G1 remains `FIX` until a clean Web build is reviewed at wide/narrow sizes for Korean/English glyphs,
clipping, controls, dialogue, ending text, save/load messages, and accessibility states. Hidden
oracle labels are never treated as player-visible lore.
