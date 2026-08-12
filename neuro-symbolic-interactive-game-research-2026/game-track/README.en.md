# Game-development track

The game track does not embed research code directly inside the engine. The engine emits observations conforming to `schemas/game-bridge.schema.json`; the research runtime returns `candidate`, `validation`, and `commit/reject` events.

Current implementation: event schema, fixture, deterministic candidate validation, unchanged-state fallback, and headless replay example. Network transport, cross-process idempotency storage, and timeout fault injection are planned adapter work and are not claimed as implemented.

Acceptance requirements for a live adapter:

- Canonical engine state changes only through a valid `commit` event.
- Every event records `run_id`, `episode_id`, `step`, `schema_version`, and `world_state_hash`.
- Persistent `event_id` idempotency must remove retries and network duplicates.
- Timeout, model failure, or high affect uncertainty must invoke a deterministic safe policy.
- The research track runs against a mock bridge; the game track runs without a model by replaying recorded traces.

A Godot 4.x or Unity LTS adapter needs only WebSocket/JSONL transport. Engine choice is not the paper contribution; protocol compatibility is.
