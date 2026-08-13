# QA Test Plan — Cycle 3 Stage 1

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game QA
Status: `IN_PROGRESS`

## Test strata

1. **Hard contract:** schema versions, event order, hash domains, duplicate rejection, timeout,
   corrupt save, exact replay, and terminal oracle hash.
2. **Playable authority:** movement/focus emit intent only; valid proposals commit; rejected actions
   preserve the complete prior state.
3. **Public-safe assets:** Web and `--public-safe` load no pending generated candidates; procedural
   fallbacks remain complete.
4. **Presentation invariants:** start gate, gesture-locked audio, color/icon/text redundancy,
   responsive profiles, reduced motion, and evaluation non-mutation.
5. **Latest captures:** arrival, refusal, authorized hint, and ending working shots have explicit
   state hashes and engineering-only labels; no implicit immutable promotion.
6. **Browser behavior:** click start, pointer capture/recovery, Korean glyphs, wide/narrow layout,
   audio unlock/mute/focus, console, save/reload, and tab focus.
7. **Performance:** warmed frame p95, long-frame rate, input-to-visible latency, and 30-minute memory
   trace.
8. **Provenance:** selected v5 remains immutable; Web build comes from a disposable copy; deployed
   artifact inventory and headers are recorded.
9. **Human impact:** only an approved independent protocol may measure immersion, readability,
   usability, affect, or repeat behavior.

## Automated engineering matrix

| Scenario | Expected hard result | Expected presentation result |
|---|---|---|
| Early secret request | refusal; identical state hash | coral + stop icon/text/ledger; restrained VFX/audio only |
| Early tide-hint request | stage-gated; identical state hash | neutral next-affordance feedback |
| Install without lens | refusal | mount remains uncommitted |
| Acquire lens | one commit | brass/glint/focus acknowledgement after commit |
| Install harbor signal lens | quest stage 2 | harbor-side amber signal; lighthouse remains dark |
| Authorized hint | one commit; fact recorded | tide marks and hint feedback become available |
| Corrupt save | reject; live state unchanged | readable rejection toast |
| Evaluation mode | no state mutation | JSON invariants only, explicitly not G4/efficacy |

## Browser viewport set

- Wide desktop: `1280×720`.
- Narrow portrait proxy: `720×900`.
- At both sizes: verify controls, ledger, objective/status, choice buttons, start gate, Korean/English
  glyphs, pointer state, and no overlap/clipping.

## Exit rule

No S1 defect, exact state-hash replay, exported public-safe asset separation, clean browser startup,
complete Korean/English visible-content audit, and director verdict backed by gate measurements.
Even if all automation passes, G4 remains `FIX` without human data and G6 remains `FIX` without the
required warmed/input/soak measurements.
