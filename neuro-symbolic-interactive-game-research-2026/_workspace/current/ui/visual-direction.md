# Visual Direction — The Sealed Lighthouse

Status: `[TARGET]` with generated concept references  
Primary style anchor: `game-track/assets/concepts/SL-C01-environment-key-art.png`

## Art pillars

1. **Auditable mystery.** Brass geometry communicates evidence, policy, and committed state without
   exposing hidden oracle or treatment-arm metadata.
2. **Weathered authority.** Navy, teal, oxidized copper, parchment, and warm amber distinguish the
   harbor's durable records from volatile storm conditions.
3. **Readable restraint.** No combat spectacle; scene silhouette, evidence availability, and action
   consequences must remain legible in grayscale and at compact UI sizes.

## Player/research separation

- Player mode: scene, NPC dialogue, evidence ledger, three structured choices, quest-stage feedback.
- Research inspector: arm, proposal, validation, repair, hashes, cost, and latency. It is physically
  separated and hidden during blinded evaluation.
- The player must never infer assignment arm from color, animation, timing, validator wording, or
  debug affordances.

## Concept references

| ID | Reference | Use | Excluded inference |
|---|---|---|---|
| SL-C01 | environment key art | palette, composition, landmark hierarchy | no engine-performance evidence |
| SL-C02 | Captain Mira sheet | silhouette, expression range, props | no believability or demographic-quality claim |
| SL-C03 | investigation UI | layout hypothesis | no accessibility/usability claim |
| SL-C04 | icon sheet | semantic motif exploration | no comprehension claim |

All production implementation must be authored from these references and must not silently ship the
concept sheets as final runtime art.
