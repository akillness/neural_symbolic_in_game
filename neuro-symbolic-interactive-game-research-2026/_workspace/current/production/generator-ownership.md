# Generator Ownership

| Generated surface | Owner | Source of truth | Rebuild/refresh trigger | Promotion gate |
|---|---|---|---|---|
| Concept PNGs | `god-tibo-imagen` authoring lane | adjacent provenance + asset manifest | prompt/model/reference change | rights/style/human review |
| Godot import/cache | Godot editor | engine source assets | engine or source asset change | never committed as evidence |
| Experiment tables | repository Python generators | trace-linked result artifacts | upstream hash change | claim ledger + reviewer |
| Paper figures | `scripts/generate_paper_figures.py` | configs/claim/pilot artifacts | input hash change | PDF build gates |
| Wiki graph | knowledge refresh script | wiki pages + raw sources | durable finding change | graph integrity check |

Generated concept art is never an empirical source. A hash proves content identity, not authorship,
rights, semantic correctness, or game quality.
