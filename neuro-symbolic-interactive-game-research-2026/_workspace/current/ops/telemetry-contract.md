# Telemetry contract / 텔레메트리 계약

Run ID: `20260813-sealed-lighthouse-cycle-1`
Owner: game-programmer
Experimental event schema version: `1.1.0`

Canonical analysis mapping version: `configs/experimental-game.yaml#telemetry_required` `1.1.0`.
The engine event field `request_latency_ms` maps to the all-assigned request-latency estimand;
future provider responses use `recorded_provider_latency_ms`, while frame samples map from
`engine_frame_ms` and interactive input samples from `input_to_visible_feedback_ms`. Do not merge
the designed timeout cap with response-observed provider latency.

## Event envelope

Every JSONL record carries scenario/run/episode/event identity, logical `sequence`, unique
`delivery_index`, turn, seed, deterministic scenario timestamp, before/after state hashes, exact
fixture-model ID and revision, policy ID,
proposal, evidence IDs, validation, repair, commit, cost, request latency and payload. Missing fields
fail `experimental-game-event.schema.json`.

`sequence` belongs to a logical event. A deliberately repeated delivery therefore reuses both
`event_id` and `sequence`; `delivery_index` is the contiguous physical JSONL line order. This
prevents a duplicate-delivery fixture from pretending that a second logical event occurred.

```yaml
required_trace_fields:
  - proposal
  - evidence_ids
  - validation
  - repair
  - commit
  - model_id
  - model_revision
  - seed
  - cost_usd
  - request_latency_ms
  - world_state_hash_before
  - world_state_hash
participant_or_personal_data: forbidden
runtime_image_generation: forbidden
```

Deterministic fixture cost is `0.0 USD` because it performs no API/model call. This value describes
the adapter used by the fixture, not future hosted-model cost.

## Summary telemetry

`summary.json` records actual Godot version, display headless status, monotonic engine elapsed time,
process-frame delta samples, request-validation samples, p95 values, configured budgets, and fault
counts. Timing never enters canonical-state hashing. The 100 ms timeout injection is labeled a
designed deadline, not an observed latency distribution.

Observed 2026-08-13 evidence is selected by
`../engineering/tech-verification/current.json`: `21/22/25` events across canonical,
duplicate-ID, and timeout runs; three commits per run; identical terminal/load/replay/oracle hashes;
and exact request/frame samples. `evidence-manifest.json` binds every output by byte count and
SHA-256. The frame budget failed and remains visible.

## Analysis and retention boundaries

- Primary unit: frozen scenario/quest template; seed is a nested generation in future studies.
- Engine timing is engineering evidence only and cannot support model-quality claims.
- Schema-validated raw engine outputs are retained in the engineering evidence lane; unvalidated
  ad hoc outputs remain outside authoritative evidence.
- No participant data is collected. Human-study tooling must export anonymous records under its own
  approved schema in a later cycle.
- Run artifacts are immutable after evidence promotion; corrections create a new run ID.
