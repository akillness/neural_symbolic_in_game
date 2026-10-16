# Gameplay-focus dashboard refresh (2026-10-02)

Status: implementation and engineering verification in progress.
Owner: Aside; delegated write scope limited to `game-track/web/dashboard/{index.html,dashboard.css,dashboard.js}`.
Base revision: `4382f69` (working-tree tracked game sources clean at intake).

## User-authorized scope

User requests a readability improvement that fits the pace of gameplay, preserves gameplay behavior, runs tests, updates README images, and builds/deploys the result. This authorizes the local implementation and Vercel production release for this pass. Git staging, commits and pushes remain `none` because no new push instruction was given. Unrelated untracked generator/tool files remain untouched.

## Source and adaptation

The user supplied `Dashboard _ Gameplay Focus.png`, SHA recorded in the final receipt. It is a visual hierarchy reference, not evidence of actual game state. Use a large real playable iframe, compact progress/readout header, quest/map/recent-action rail, stable last-action readout and collapsed engineering details. Do not import the pictured harbor as a fake live canvas or its invented lamp-room, stairs, tide-log, five-step quest or parser-success values.

The actual game has committed stages 0 to 3 (signal lens, harbor beacon mount, authorized tide route), followed by a presentation-only deduction. The offshore lighthouse remains sealed. All counters, gate outcomes and safe hold advice must come from real mirrored engine events. English-only runtime, hidden-fact allowlist and one-way observer boundary remain unchanged.

## Pace/readability design targets [TARGET]

- Game remains the primary attention surface. Preserve the proven 720px iframe height to avoid clipping the bottom ledger and dialogue choices.
- Show current objective and last complete verdict without forcing the player to read graph prose.
- Keep the last action stable across movement, focus and tick messages. Permit reading a frozen earlier result without pausing or controlling the game; explicitly report newer results and provide Follow latest.
- Show evaluated checks in actual emitted order; keep skipped and not-evaluated separate. Never infer parser pass or future/hidden knowledge.
- Fold full graph, hash chain, paper reference and raw feed into native accessible disclosure controls, not deletion.
- Bounded history, escaped strings, color-independent verdict/state words, keyboard focus visibility, reduced-motion behavior and responsive contained scrolling.

## Verification planned

1. Canonical project and machine hashes unchanged before/after staged Godot runs.
2. Real public-safe smoke, canonical/duplicate/timeout/corrupt-save fixtures and presentation evaluation with distinct pass/fail/skip counts.
3. Existing trace fixture harness in unpatched Chromium (normal and reduced motion), plus rapid updates/history pinning/reload/session reset/source-origin guards.
4. Local and production real Web game boot, input/dialogue/hold/commit/quest progression checks; desktop and 390px/768px page overflow and controls visibility.
5. README screenshots captured from the verified new real runtime, not from synthetic fixtures; provenance notes distinguish current images from historical route recordings.
6. Disposable-copy Web build and anonymous deployed file checks against exact local release bytes, unchanged EN/KO manuscript bytes, and final production visual proof.

All new results are engineering verification only. Human readability, enjoyment, efficacy and G4/G6 remain unestablished; no paper claim, frozen evidence or research-result promotion is authorized.
