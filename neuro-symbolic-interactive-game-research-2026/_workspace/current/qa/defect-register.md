# Defect Register

| id | severity | surface | evidence | status | owner |
|---|---|---|---|---|---|
| DEF-001 | S2 | local engine environment | Godot 4.7.1 installed and executable/version receipt recorded | resolved-2026-08-13 | game-programmer |
| DEF-002 | S2 | bridge schema | generic payload lacks event-specific experiment provenance | open | game-programmer |
| DEF-003 | S2 | state model | existing runtime cannot yet express all rich inventory/relationship mutations except as facts | open | game-programmer + logic-auditor |
| DEF-004 | S2 | performance | retained five-sample headless frame p95 exceeds 16.7 ms; soak/input metrics absent | open | game-programmer + QA |
| DEF-005 | S1 | save/load | candidate save used to replace live state before checksum verification | resolved-2026-08-13; corrupt-save fixture added | game-programmer + QA |
| DEF-006 | S2 | cross-runtime transport | policy mirror and stable-envelope projection exist, but no live Python authorization round-trip | open | game-programmer + game-integrator |
| DEF-007 | S2 | concept provenance | SL-C04 v1 violated its prompt with key/seal motifs | resolved-2026-08-13; v1 rejected and v2 regenerated | art pipeline + QA |
| DEF-008 | S1 | retained evidence | capture script could overwrite the fixed retained Godot evidence path | resolved-2026-08-13; unique ID, staging, fail-closed promotion, and overwrite/traversal regressions added | game-programmer + reproducibility-verifier |

An environment blocker may be closed only with an executable/version receipt or explicitly accepted
static-only verification; it cannot be relabelled as a passing engine run.
