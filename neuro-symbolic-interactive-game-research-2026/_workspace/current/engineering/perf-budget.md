# Performance budget / 성능 예산

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game-programmer
Gate: G6 draft
Verdict input: `FIX — structural Web budgets exist; warmed browser/input/soak measurements do not`

```yaml
performance_budget:
  warmed_frame_p95_ms_max: 16.7
  long_frame_rate_max: 0.005
  request_p95_ms_max: 100.0
  input_feedback_ms_max: 100.0
  memory_soak_minutes: 30
  web_continuous_rain_particles_max: 360
  presentation_burst_particles_max: 18
  procedural_audio_mix_rate_hz: 22050
measurement_clock: Time.get_ticks_usec
engine_result_required: true
```

## Carried Cycle 2 measurements

| Measure | Target | Carried observed value | Evidence |
|---|---:|---:|---|
| Startup-heavy headless frame delta p95 | ≤16.7 ms | canonical `116.667`; duplicate `100.000`; timeout `98.760`; corrupt-save `112.907 ms` — `FIX` | selected v5 summaries |
| Request validation p95 | <100 ms with zero unintended timeouts | canonical `0.107`; duplicate `0.084`; corrupt-save `0.077 ms`; designed timeout `100.0 ms` | selected v5 summaries |
| Total engine elapsed | report only | canonical `18.317`; duplicate `16.130`; timeout `17.295`; corrupt-save `16.766 ms` | selected v5 summaries |

The five-frame headless samples are exact observations but not a warmed performance estimate.

## Cycle 3 implementation budgets

| Surface | Implemented budget | Evidence kind |
|---|---|---|
| Renderer/export | Godot Compatibility Web; thread and extension support disabled | static configuration |
| Continuous rain | Web `360`, desktop `480` CPU particles | static cap |
| One-shot VFX | five pooled emitters; at most `18` particles per burst; no VFX-only lights | static cap |
| Repeated dressing | `MultiMeshInstance3D`, decorative instances without collision | static structure |
| Expensive post effects | blur `0`, raymarch `0` | static cap |
| Procedural audio | mono `22,050 Hz`, four pooled cue voices, generated once per scene | static structure |
| Reduced motion | player-toggleable; VFX/camera motion policy is suppressed or shortened | static structure |

These caps define a starting performance envelope; they are not measured FPS, memory, or input
results.

## Current missing measurements

| Measure | Target | Current state | Required method |
|---|---:|---|---|
| Warmed Web frame p95 | ≤16.7 ms | `[NOT OBSERVED]` | browser profiler after warmup |
| Long-frame rate | <0.5% | `[NOT OBSERVED]` | retained session sample |
| Input-to-visible feedback | ≤100 ms | `[NOT OBSERVED]` | browser input/visual timestamps |
| Memory stability | stable over 30 min | `[NOT OBSERVED]` | 30-minute browser/OS memory trace |
| Audio unlock/resume | gesture-safe and stable | `[NOT OBSERVED IN CLEAN BROWSER]` | start, focus-out/in, mute/unmute test |

The public-safe 3D smoke `8/8` and aggregate `40 tests, 44 subtests` validate authored engineering
behavior only. G6 remains `FIX` until the missing browser and soak measurements are recorded with
exact commands, timestamps, and retained outputs.
