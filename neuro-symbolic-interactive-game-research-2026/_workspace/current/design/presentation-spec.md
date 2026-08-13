# The Sealed Lighthouse / 봉인된 등대 — presentation and concept-resource specification

```yaml
artifact_id: SL-PRESENT-001
run_id: 20260813-sealed-lighthouse-cycle-1
owner: game-designer
version: 0.1.0
gate: G4
style_anchor: SL-C01
status: target-assets-and-immersion-unverified
```

## Art direction / 아트 디렉션

**[TARGET]** “Maritime evidence folio”: engraved coastal-chart linework, restrained gouache weather
wash, oxidized brass instruments, wet slate, and a single warm signal-light accent. The direction
must not name or imitate a living artist, studio house style, or surveyed game's exact interface.

**[TARGET]** “해양 증거철”: 해도 판화 선, 절제된 구아슈 날씨층, 산화된 황동 계기, 젖은 점판암,
단일한 따뜻한 신호등 강조색을 사용한다. 생존 작가·스튜디오 고유 화풍·비교작 UI를 지명하거나
모사하지 않는다.

### Palette / 색상

| Token | Hex | Use |
|---|---|---|
| `storm-ink` | `#17232D` | background and unobserved space |
| `wet-slate` | `#344956` | reachable environment |
| `paper-fog` | `#D9D3C4` | text and evidence paper |
| `brass` | `#A77A3A` | selected evidence and valid causal link |
| `signal-amber` | `#F2B84B` | committed reward or authorized hint only |
| `warning-coral` | `#D9685F` | blocked proposal; never secret correctness |

All semantic states require text/icon redundancy; color alone cannot encode validity. [TARGET]

## Layout / 화면 구조

At `1280×720`, reserve `55%` for the scene, `30%` for the Harbor Ledger/dialogue, and `15%` for
actions and status. [TARGET] At narrower widths, stack scene above ledger and preserve a minimum
`44×44 px` control target. Body text target is `18 px` at `1×`; subtitles and motion reduction are
available from the first playable build. [TARGET]

## Scene and feedback beats / 장면·피드백 비트

| Beat | Visual state | Motion/effect | Audio intent | Hard boundary |
|---|---|---|---|---|
| P-B01 Arrival | dark lighthouse silhouette beyond wet quay | slow rain layer, no camera shake | wind + distant buoy | image is observation only |
| P-B02 Lens found | signal lens outlined in `brass` | `120–180 ms` line-draw | glass/metal cue | effect follows committed acquisition |
| P-B03 Proposal pending | dotted ledger link | subtle pulse, motion-reduction alternative | low pencil loop | no state change |
| P-B04 Rejected secret | link stops before sealed node | local acknowledgement target `≤100 ms`; `warning-coral` + text | soft page stop, no alarm | prior canonical hash retained |
| P-B05 Authorized hint | one Harbor Ledger link becomes solid | signal-light glow `250 ms` | restrained bell harmonic | only after valid lens-install commit |
| P-B06 Replay verified | inspector-only hash receipt | none in primary player view | optional neutral click | not a quality reward |

Effect feedback latency is a target to be measured from input receipt to local acknowledgement. It
is not the provider/model response latency and no measurement exists yet.

## `god-tibo-imagen` concept pack / 콘셉트 팩

Generation is an offline authoring activity. Run a dry-run before generation; preserve exact prompt,
negative constraints, reference list, tool/package/provider/model, UTC time, dimensions, bytes,
SHA-256, curation state, rights review, intended track, and `runtime_eligible: false` beside each
output. [TARGET]

| Asset ID | Output class | Frozen prompt intent / 동결 프롬프트 의도 | Required negative constraints |
|---|---|---|---|
| SL-C01 | Environment key art | Wide storm harbor and sealed offshore lighthouse; maritime evidence-folio linework and one amber light. | no logo, watermark, readable text, franchise imitation, photorealism, UI, modern vehicle |
| SL-C02 | Captain Mira exploration sheet | Original harbor watch captain with consistent facial structure, expressions, and practical storm clothing. | no celebrity likeness, named-artist style, weapons focus, pin-up pose, logo, readable text |
| SL-C03 | Investigation UI concept | Harbor Ledger, three structured action choices, commit/fallback feedback, and separate inspector mode. | no hidden secret, correct oracle label, tiny-text dependency, or commercial-game UI copy |
| SL-C04 | Evidence icon sheet | Strict `4×3` canonical-visible set: lighthouse, Harbor Watch badge, lantern, tide marks, Mira logbook, signal lens, dock knot, dark-lighthouse token, trust token, quest beacon, commit, fallback. | no key, seal animal, letter, betrayal/secret-document motif, readable text, trademark, currency, or watermark |

The current pack and adjacent provenance exist under `game-track/assets/concepts/`; its manifest
records `SL-C01` as the style anchor and all four files as secondary-track concept artifacts.
[OBSERVED artifact] Tool invocation and hashes are owned by that manifest, not duplicated here.
Human publication-rights/style review remains pending, and the undocumented backend must never be
imported by Godot or research runtime.

## Dual-track presentation / 이중 트랙 연출

| Track | Visual input | Randomization role | Authority | Claim scope |
|---|---|---|---|---|
| Primary structured | text, icons, canonical fields; concept scene may be disabled | fixed across arms | structured state/policy only | RQ1–RQ5 confirmatory target |
| Secondary VLM/UI | reviewed and SHA-256-frozen image pack | image-pack version is explicit blocking factor | image observation is soft context only | exploratory until separately preregistered |

Primary and secondary manifests must be disjoint and versioned. Regeneration during an episode is
forbidden. [TARGET]

## G4 status / G4 상태

G4 requires median immersion `≥4.0/5`, local effect feedback `≤100 ms`, and zero unresolved S1/S2
readability complaints. [TARGET] No playtest or latency evidence exists, so G4 is **FIX**.
