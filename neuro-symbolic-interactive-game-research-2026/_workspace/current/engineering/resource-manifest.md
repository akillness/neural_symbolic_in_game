# Engineering resource manifest / 엔지니어링 리소스 매니페스트

Run ID: `20260813-sealed-lighthouse-cycle-2`  
Owner: game-programmer

| Resource | Generator/owner | Freshness source | Runtime role | Evidence status |
|---|---|---|---|---|
| `game-track/godot/project.godot` | game-programmer | architecture contract | Godot 4.x project entry | `[OBSERVED]` file exists |
| `game-track/godot/scripts/*.gd` | game-programmer | scenario + hard invariants | deterministic state, events, save/load/replay plus a separate non-headless render pass | `[OBSERVED]` policy-mirror and selected v5 capture runners |
| `game-track/godot/data/sealed_lighthouse.json` | game-programmer from approved concept | design/worldview revisions | frozen canonical scenario | `[OBSERVED]` schema-valid |
| `game-track/schemas/experimental-game-*.json` | game-programmer | bridge contract revision | versioned input/output validation | `[OBSERVED]` schema-valid |
| `data/fixtures/experimental-game-*.json` | game-programmer | fault-plan revision | canonical, duplicate, timeout, and corrupt-save inputs | `[OBSERVED]` schema-valid |
| `engineering/tech-verification/current.json` → immutable evidence set | Godot runners + evidence manifest generator | exact fixture/schema/code/render/validator revision | immutable run and render evidence for review | `[OBSERVED]` selected v5 `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`; v1--v4 retained superseded |
| Capture validation toolchain | capture pipeline + retained validator | selected v5 manifest | provenance and portable retained-evidence verification | `[OBSERVED]` capture pipeline, PNG decoder, schema, retained validator, and `uv.lock` hashes; Python `3.13.9`, jsonschema `4.26.0` recorded |
| `sl-rc-001-arrival` | non-headless Godot capture runner | canonical arrival/observation state + capture metadata | structured-state primary render | `[OBSERVED]` 1280×720, 61,120 bytes, SHA-256 `08642e4b...c298c` |
| `sl-rc-002-rejected-secret` | non-headless Godot capture runner | canonical rejection/fallback state + capture metadata | structured-state primary render | `[OBSERVED]` 1280×720, 67,146 bytes, SHA-256 `b123fc52...22db9` |
| `sl-rc-003-authorized-hint` | non-headless Godot capture runner | canonical post-install authorized-hint state + capture metadata | structured-state primary render | `[OBSERVED]` 1280×720, 59,813 bytes, SHA-256 `79356a0c...c9f7f` |
| Concept image pack | visual-resource owner | image manifest/hash | secondary VLM/presentation track only | outside this lane |

Generated Godot `.godot/` import/cache data are not source resources. Promoted run outputs and PNGs
live only in the engineering evidence lane with hashes; ad hoc output directories are not evidence.
The primary screenshots use no generated concept art. No runtime image generation, network model
call, participant data, or personal telemetry is permitted.
