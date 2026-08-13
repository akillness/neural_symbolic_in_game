# The Sealed Lighthouse / 봉인된 등대 — presentation and resource specification

```yaml
artifact_id: SL-PRESENT-001
run_id: 20260813-sealed-lighthouse-cycle-3
owner: game-designer
version: 0.2.0
gate: G4
runtime_style_anchor: procedural-maritime-evidence-folio
status: implemented-engineering-structure-human-impact-unverified
```

## Art direction / 아트 디렉션

**[TARGET]** “Maritime evidence folio”: engraved coastal-chart linework, restrained gouache weather
wash, oxidized brass instruments, wet slate, and a single warm **harbor-side signal** accent. The
offshore lighthouse remains dark and sealed. The direction does not name or imitate a living
artist, studio house style, or surveyed game's exact interface.

**[TARGET]** “해양 증거철”: 해도 판화 선, 절제된 구아슈 날씨층, 산화된 황동 계기, 젖은
점판암, 단일한 따뜻한 **항구 측 신호** 강조색을 사용한다. 앞바다 등대는 어둡고 봉인된
상태를 유지한다. 생존 작가·스튜디오 고유 화풍·비교작 UI를 지명하거나 모사하지 않는다.

### Palette / 색상

| Token | Hex | Use |
|---|---|---|
| `storm-ink` | `#17232D` | background and unobserved space |
| `wet-slate` | `#344956` | reachable environment |
| `paper-fog` | `#D9D3C4` | text and evidence paper |
| `brass` | `#A77A3A` | selected evidence and valid causal link |
| `signal-amber` | `#F2B84B` | committed harbor signal or authorized hint only |
| `warning-coral` | `#D9685F` | blocked proposal; never secret correctness |

[OBSERVED structure] Commit/refusal feedback uses color plus icon, text, and ledger-line redundancy.
This is not a human accessibility or readability result.

## Layout / 화면 구조

At `1280×720`, the implemented wide layout uses scene, ledger, and action columns. A narrow or
portrait viewport switches to a stacked ledger/action layout. Choice controls have a `44 px`
minimum height; body copy targets `16–18 px` depending on the layout. The controls panel names
`WASD`, mouse look, `[E]`, `[Esc]`, `[F5]`, `[F9]`, `[M]`, and `[V]`.

[OBSERVED structure] Web starts behind an explicit bilingual click gate so pointer capture and
audio resume occur inside a browser user gesture. `[Esc]` releases the pointer; click recaptures
it. Responsive layout declarations and the gate are exercised by `--evaluate`, but clean-browser
and Korean glyph verification is still pending.

## Scene and feedback beats / 장면·피드백 비트

| Beat | Implemented visual state | Motion/effect | Procedural audio intent | Hard boundary |
|---|---|---|---|---|
| P-B01 Arrival | dark sealed lighthouse beyond a dressed wet quay | rain plus pooled arrival mist; reduced-motion alternative | generated wind/harbor/buoy bed after gesture | observation only |
| P-B02 Lens found | signal lens receives brass focus/commit emphasis | fixed lens-glint burst after commit | generated focus/commit cue | effect follows committed acquisition |
| P-B03 Proposal pending | dotted ledger link and readable objective/progress | subtle pulse; reduced-motion alternative | generated dialogue cue | no state change |
| P-B04 Rejected secret | coral stop, icon, text, ledger refusal | fixed refusal motes/pulse | generated restrained refusal cue | prior canonical hash retained |
| P-B05 Authorized hint | harbor mount and tide marks gain amber emphasis | pooled sparks/motes and bounded glow | generated hint harmonic | only after valid lens-install commit |
| P-B06 Route earned | ending card states the tower remains sealed and tide route is next | restrained ending cinematic | no quality-reward sound claim | does not invent lighthouse entry |

The implementation contains a local acknowledgement target of `≤100 ms`, but no timestamped
input-to-visible measurement has run. The target is not provider/model response latency.

## Runtime presentation budget / 런타임 연출 예산

| Budget item | Implemented cap | Interpretation |
|---|---:|---|
| Pooled one-shot beat emitters | 5 | preallocated presentation structure |
| Max particles in one authored burst | 18 | fixed effect cap, not measured GPU cost |
| Web continuous rain | 360 particles | Web starting budget |
| Desktop continuous rain | 480 particles | desktop starting budget |
| VFX-only lights | 0 new | reuse authored scene lights |
| Blur/raymarch | 0 passes / 0 samples | Compatibility/Web constraint |
| Audio cue voices | 4 | fixed local pool |
| Audio mix rate | 22,050 Hz mono | deterministic local generation |

These are implementation caps, not G6 measurements.

## Generated concept and 3D candidate packs / 생성 후보 팩

The offline `god-tibo-imagen` packs remain secondary-track candidates with adjacent provenance,
`runtime_eligible: false`, and pending human publication-rights/style review. The original `SL-C01`
prompt admits “one amber light”; if interpreted as a lit offshore lighthouse, it contradicts the
canonical dark/sealed state. It is therefore excluded from runtime and public-safe/Web builds. A
future regenerated environment candidate must place any amber signal on the harbor side and keep
the lighthouse dark.

`world_builder.gd` loads no generated candidate texture when `OS.has_feature("web")` or
`--public-safe` is present. The public presentation consequently uses only programmatic geometry,
materials, focus markers, VFX, UI, and procedural audio.

## Track separation / 트랙 분리

| Track | Visual/audio input | Authority | Claim scope |
|---|---|---|---|
| Primary structured research | text, icons, canonical fields | structured state/policy | RQ1–RQ5 confirmatory target |
| Public-safe playable | programmatic 3D, UI, VFX, locally generated audio | presentation reads committed snapshots | engineering conformance only |
| Secondary VLM/UI | reviewed and SHA-256-frozen image pack | soft image context only | exploratory after separate preregistration |

Regeneration during an episode is forbidden. Primary, public-safe, and secondary manifests remain
disjoint and versioned.

## G4 status / G4 상태

G4 requires median human immersion `≥4.0/5`, measured local effect feedback `≤100 ms`, and zero
unresolved S1/S2 readability complaints under an approved test. No participant or input-latency
dataset exists. Automated smoke, `--evaluate`, screenshots, and browser checks are engineering
conformance only, so G4 remains **FIX**.
