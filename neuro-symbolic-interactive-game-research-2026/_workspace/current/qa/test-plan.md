# QA Test Plan — Cycle 1

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Owner: game QA  
Status: `IN_PROGRESS`

## Test strata

1. Contract: schema versions, exact fields, hash domains, duplicate rejection.
2. State: invalid/failure paths preserve the entire prior state; valid commits apply only allowed
   effects.
3. Episode: acquire authorized evidence, reject early secret request, progress quest, permit later
   hint, save/load, and deterministic replay.
4. Faults: duplicate event ID, timeout, malformed event, disconnected trace, stale state hash.
5. Presentation: blinded player view must not expose arm, validator, oracle, or repair metadata.
6. Provenance: every concept PNG must match its manifest checksum and remain outside primary input.

## Synthetic adversarial archetypes

| Archetype | Strategy | Primary risk |
|---|---|---|
| Rule follower | follows authored clues | false-positive rejection |
| Shortcut seeker | skips prerequisite | impossible progression |
| Secret fisher | repeatedly requests locked fact | forbidden disclosure |
| Memory challenger | revisits altered relationships after 5/10/20 turns | temporal contradiction |
| Failure inducer | triggers timeout, duplicate, and malformed input | state mutation on failure |

These are scripted QA roles, not human participants or evidence of player diversity.

## Exit rule

No S1 defect, exact state-hash replay, schema validation, primary/visual input separation, and a
director verdict backed by `qa/gate-measurements.md`. Unmeasured gates remain `FIX`.
