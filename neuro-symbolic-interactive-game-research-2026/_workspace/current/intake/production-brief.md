# Production Brief — The Sealed Lighthouse

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Cycle: 1, Stage 1  
Status: `IN_PROGRESS — design packet, concept pack, and engine-local headless scenario complete`  
Next public beat: live Python authorization adapter plus warmup/soak/input performance evidence  
Requirements: `../../../../.omx/specs/deep-interview-experimental-game-track.md` (repository root)

## Outcome

[TARGET] Deliver an 8--12 minute turn-based narrative investigation micro-RPG testbed in which the
player investigates a sealed lighthouse with Captain Mira. The slice must operationalize quest
reachability, knowledge/disclosure, bounded repair, state-isolating fallback, save/load, and replay
without making efficacy claims.

## Player promise

[TARGET] Every consequential choice changes only a transparent committed world state; mystery comes
from what the player has not yet proven, not from rules changing behind the scenes.

## Research promise

[TARGET] The same frozen episode can be executed through structured state/text and, separately,
through a frozen-image VLM observation track. Both tracks preserve assignment, model, policy,
oracle, build, content-pack, seed, latency, cost, and terminal-state provenance.

## Scope

Included:

- precise bilingual GDD and RQ1--RQ5 experiment crosswalk;
- one Godot 4.x headless deterministic slice;
- bridge/replay/save-load/telemetry contracts and fault fixtures;
- four `god-tibo-imagen` concept/resource surfaces with complete provenance;
- blinded annotation UI and ethics/data-governance protocol design.

Excluded:

- real-time combat, monetization, polished desktop release, runtime image generation;
- participant recruitment or personal-data collection;
- promotion of `C-RESULT-001`--`005` or any model/player/engine efficacy claim.

## Authority boundary

[OBSERVED] The Python research runtime owns the separate encoded validator used by the research
scaffold. The current Godot fixture does not call it; it executes a reviewed engine-local authored
policy mirror. [TARGET] A live adapter makes Python the cross-runtime commit authority while Godot
owns presentation, input, save/load integration, and engine telemetry. Timeout, invalid candidate,
or exhausted repair must leave complete canonical state unchanged.

## Required evidence before Cycle 1 closes

1. All workspace artifacts exist with `[OBSERVED]`/`[TARGET]`/`[INFERENCE]` boundaries.
2. Godot 4.7.1 execution receipt and retained engine-local traces exist. [OBSERVED]
3. Operation replay reconstructs the same terminal state hash. [OBSERVED]
4. Concept assets pass image parsing and manifest hash checks. [OBSERVED]
5. Paper crosswalk contains no result promotion. [OBSERVED]
6. Independent QA and game-integrator review findings are recorded and fixed. [OBSERVED]

Cycle 1 still remains `FIX` at the studio-gate level because live authorization, G6, and player-loop
measurements are absent.
