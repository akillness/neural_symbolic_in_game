# Godot headless technical verification / Godot 헤드리스 기술 검증

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Execution date: 2026-08-13 Asia/Seoul  
Owner: game-programmer  
Status: `[OBSERVED]` four retained fixture runs; independent review completed with fixes applied

## Exact environment receipt

Homebrew installed `/opt/homebrew/bin/godot`, a symlink to the exact app bundle executable
`/Applications/Godot.app/Contents/MacOS/Godot`. The newly installed app initially retained this
quarantine value:

```text
0381;6a7d9305;;0F2F01FF-F12C-4641-93F4-27F49DE3AA18
```

The signed bundle was checked first: `spctl -a -vv /Applications/Godot.app` reported `accepted`,
`source=Notarized Developer ID`, and the Godot developer identity. Godot invocations nevertheless
stalled at `_dyld_start`. The quarantine attribute was removed from this app only:

```bash
xattr -d com.apple.quarantine /Applications/Godot.app
godot --headless --version
```

Observed version: `4.7.1.stable.official.a13da4feb`. After removal, `xattr -l` retained only
`com.apple.provenance` on the bundle.

## Retained engine runs

The exact command form for each of the canonical, duplicate-ID, timeout, and corrupt-save fixtures was:

```bash
godot --headless --path game-track/godot --quit-after 120 -- \
  --fixture="<absolute data/fixtures/experimental-game-*.json path>" \
  --output="<absolute evidence/fixture-id path>"
```

Authoritative retained root, selected and manifest-hash-bound by `tech-verification/current.json`:
`_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/`.
`evidence-manifest.json` records the OS/platform, command template, complete summaries, byte counts,
and SHA-256 for every JSONL trace, save, and summary.

The retained directory is immutable. Future captures must use a new ID, for example:

```bash
uv run python scripts/capture_godot_evidence.py \
  --evidence-set-id godot-4.7.1-yyyymmddthhmmssz-sealed-lighthouse-v1
```

The command stages outputs outside the evidence lane, reserves the target without replacement,
moves the completion manifest last, and fails closed when either the staging ID or retained
evidence-set ID already exists.

| Fixture | Events | Commits | Fault count | Fallbacks | Terminal/load/replay/oracle hash | Hard checks |
|---|---:|---:|---:|---:|---|---|
| canonical | 21 | 3 | 0 | 1 | `4b2310…8892` | 10/10 true |
| duplicate ID | 22 | 3 | 1 duplicate | 1 | `4b2310…8892` | 10/10 true |
| timeout | 25 | 3 | 1 timeout | 2 | `4b2310…8892` | 10/10 true |
| corrupt save | 21 | 3 | 1 rejected corrupt load | 1 | `4b2310…8892` | 10/10 true |

The early `keeper_betrayal` plus stage-gated `tide_marks_hint` candidate fell back with unchanged
state in every run. The later hint committed only after stage 2. The duplicate commit event was
ignored once, and the designed timeout/fallback pair preserved the state. Valid saves loaded and all
four operation traces replayed to the independently projected terminal hash; the corrupted candidate
save was rejected before live-state mutation.

## Targeted validation

Commands and fresh result:

```bash
.venv/bin/python -m pytest -q tests/test_godot_experimental_game.py
ruff check tests/test_godot_experimental_game.py
```

- `19 passed, 44 subtests passed`
- `All checks passed!`

The conditional Python test launched all four Godot fixtures, validated every JSONL
event/save/summary with Draft 2020-12 schemas, and checked terminal-state equality or corrupt-save
state isolation. A separate retained evidence run then captured durable traces and hashes for the
canonical, duplicate-ID, timeout, and corrupt-save fixtures.

## Failed-performance boundary

The selected v5 five-frame samples per fixture produced p95 values of `116.667`, `100.000`,
`98.760`, and `112.907 ms`, so
the `16.7 ms` G6 target did not pass. Startup/warmup dominates these tiny samples. Canonical and
duplicate and corrupt-save request-validation p95 were `0.107`, `0.084`, and `0.077 ms`; the timeout fixture deliberately
recorded `100.0 ms` and failed its request budget as intended. No 30-minute memory soak or
interactive input-feedback measurement ran. These limits remain `FIX`, not deleted evidence.

## Paper-use boundary

This receipt supports only the authored Godot multi-step engine path, state isolation, save/load,
operation replay, and the exact recorded timings. It is not an independent semantic oracle, model
comparison, player study, stable frame benchmark, commercial-engine portability result, or
persistent cross-process idempotency test. Independent game-integrator review found and drove the
save pre-validation, bridge-scope, event-delivery, and concept-provenance fixes; live transport and
G6 remain open.
