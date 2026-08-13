# Rollback and safe-fallback runbook / 롤백·안전 fallback 실행서

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Owner: game-programmer  
Test status: `[OBSERVED]` process-local duplicate and timeout safe-fallback drills passed

## Runtime failure response

1. Preserve the incoming canonical state and its hash.
2. On validation failure, timeout, adapter failure, exhausted repair, or unknown operation, emit a
   reject/timeout plus deterministic fallback event.
3. Require identical before/after state hashes for every non-commit outcome.
4. Before applying a commit, check `event_id`; a previously processed ID is logged as a duplicate
   and not applied again.
5. If save hash, replay continuity, or terminal hash differs, exit non-zero and quarantine the run.

## Artifact rollback

- Never edit an archived `_workspace/archive/{run-id}` artifact.
- Revert by selecting the last reviewed fixture/schema revision and creating a new run ID; do not
  overwrite prior run evidence.
- Every Godot capture requires `--evidence-set-id <unique-id>`. The capture script runs in a
  non-authoritative staging directory, reserves a new target without replacement, moves the
  completion manifest last, and fails if the staging or retained target already exists.
- Keep failed JSONL/save/summary files for diagnosis and mark them `FIX`; never delete evidence to
  obtain a passing gate.
- A schema or invariant change requires a rule/workspace re-derivation by the director.

## Drill receipt

Godot `4.7.1.stable.official.a13da4feb` executed the duplicate and timeout fixtures on 2026-08-13.
Both retained the oracle terminal hash. The duplicate path reported one duplicate but only three
commits; replay ignored the repeated ID. The timeout path reported one timeout, two fallbacks, and
true timeout-state-isolation. All ten hard checks were true for both summaries. Evidence:
the set selected by `engineering/tech-verification/current.json`.

This drill proves only in-process idempotency and authored timeout handling. Persistent
cross-process idempotency, artifact rollback from a prior release, 30-minute soak, and interactive
input feedback remain untested, so overall G6 remains `FIX`.
