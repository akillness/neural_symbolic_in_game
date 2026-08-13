# Performance budget / 성능 예산

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Owner: game-programmer  
Gate: G6 draft  
Verdict input: `FIX` — engine measurements exist, but frame budget and soak requirements do not pass

```yaml
performance_budget:
  headless_frame_p95_ms_max: 16.7
  long_frame_rate_max: 0.005
  request_p95_ms_max: 100.0
  input_feedback_ms_max: 100.0
  memory_soak_minutes: 30
measurement_clock: Time.get_ticks_usec
engine_result_required: true
```

| Measure | Target | Current observed value | Method | Evidence |
|---|---:|---:|---|---|
| Headless frame delta p95 | ≤16.7 ms | canonical `116.667`; duplicate `100.000`; timeout `98.760`; corrupt-save `112.907 ms` — `FIX` | 5 Godot process-frame samples/run, including startup | selected v5 summaries |
| Request validation p95 | <100 ms with zero timeouts | canonical `0.107`; duplicate `0.084`; corrupt-save `0.077 ms` pass; designed timeout `100.0 ms` fails as expected | monotonic `Time.get_ticks_usec` | selected v5 summaries |
| Total engine elapsed | report only | canonical `18.317`; duplicate `16.130`; timeout `17.295`; corrupt-save `16.766 ms` | monotonic runner wall time | selected v5 summaries |
| Long-frame rate | <0.5% | `[NOT OBSERVED]` | ≥30-minute run | Not implemented this cycle |
| Input feedback | ≤100 ms | `[NOT OBSERVED]` | interactive debug surface | Explicit non-goal this cycle |
| Memory stability | stable over 30 min | `[NOT OBSERVED]` | engine profiler/OS RSS | Not implemented this cycle |

Evidence: the set selected by `engineering/tech-verification/current.json`. The timeout fixture's `100 ms` is
a designed deadline, not an empirical service-latency draw. Frame p95 uses only five samples and is
dominated by startup/warmup, so it is an exact engineering observation but not a stable performance
estimate. G6 remains `FIX` until a warmup-controlled sample, long-frame rate, 30-minute memory soak,
and interactive input-feedback measurement exist.
