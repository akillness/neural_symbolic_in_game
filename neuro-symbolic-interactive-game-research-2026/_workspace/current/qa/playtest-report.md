# Playtest Report — Cycle 3

Run ID: `20260813-sealed-lighthouse-cycle-3`
Status: `NO_HUMAN_PLAYTEST_DATA — AUTOMATED ENGINEERING CONFORMANCE ONLY`

No participant, independent informal play session, or human rating was run. Therefore the project
has no observation for immersion, usability, comprehension, agency, readability preference,
naturalness, repeat intent, or player benefit.

## Automated playable-path receipt

| Item | Current result | Permitted interpretation |
|---|---|---|
| Public-safe 3D smoke | `8/8` checks pass | authored proposal/state/presentation-sync conformance |
| Terminal state | `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892` | content integrity against frozen oracle |
| Aggregate regression | full Pytest `181 passed, 81 subtests`; unittest `138 passed`; game selection `50 passed, 48 subtests`; Ruff check/format clean | current engineering regression |
| Local Web golden path | English start/tutorial and ending reached; tracked rig loaded; refresh-persistent save/load passed; zero console/page errors | browser engineering QA only |
| Fall recovery | below-world return observed; smoke proves symbolic hash unchanged | physical recovery, not a state mutation |
| Pointer lock | unverified; DOM lock remained null in automation | human-gesture check still required |
| Human observations | `0` sessions, `0` participants | no G4/G7/player claim |

`--evaluate` and `--shot-stage` outputs remain automated presentation artifacts, not playtest data.
The 2026-08-29/30 local Web receipt is `_workspace/current/qa/browser-qa.md`; it records the complete
route, refresh-persistent save/load, fall recovery, pointer-lock non-verification, and the narrow
signal-lens approach.

## Required future human packet

An approved study must record build/content-pack IDs, viewport/device, language, task completion,
input-to-visible acknowledgement, readability defects, immersion scale, comprehension, adverse
events, and anonymized consent-compliant provenance. Until then G4 and the human portion of G7
remain `FIX`.
