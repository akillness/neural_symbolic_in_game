# Neuro-symbolic Game Story Research Plan 2026-06-28

This report defines a two-paper research program for applying LLM-linked neuro-symbolic methods to game story generation, interactive narrative, and RPG dialogue, using `saas-of-funqa` as the planned RAG/evaluation platform.

## Executive goal

Create two SCI-E-oriented manuscript drafts and one project plan package around neuro-symbolic game storytelling:

1. **Paper A:** validated interactive-fiction / quest-world generation using LLM proposals plus symbolic consistency gates.
2. **Paper B:** knowledge-graph-grounded RPG NPC dialogue using lore retrieval, relationship graphs, and symbolic dialogue-state constraints.
3. **Project package:** a schedule, experimental protocol, bibliography verification list, and Google Docs/Drive handoff plan.

## Why this is publishable

The research gap is practical and timely: LLMs can generate attractive story text, but game content must obey hard constraints such as quest solvability, map topology, object reachability, NPC memory, faction logic, and lore continuity. Neuro-symbolic systems provide a rigorous way to combine creative language generation with auditable validity enforcement.

## Graphify-style knowledge packet

### Entities

- **LLM proposer:** generates candidate quests, world-state transitions, scenes, or dialogue.
- **Symbolic validator:** checks state preconditions/effects, puzzle reachability, inventory logic, and narrative invariants.
- **Knowledge graph memory:** stores world lore, NPC identities, relationships, events, factions, locations, and facts.
- **FunQA RAG layer:** retrieves grounding evidence and records traceable citations from design documents and generated histories.
- **Experiment runner:** executes batch generation, validation, repair, and evaluation.
- **Human evaluator:** rates coherence, believability, engagement, and character voice.
- **Player simulator:** tests solvability, dead-end rates, and dialogue-policy consequences.

### Relations

- LLM proposer **creates** candidate content.
- RAG layer **grounds** generation in lore and prior state.
- Symbolic validator **filters or repairs** invalid candidates.
- Knowledge graph **constrains** facts, relations, and state transitions.
- Experiment runner **measures** validity, quality, and cost.
- Human evaluator and player simulator **validate** subjective and objective outcomes.

### Decisions

- Treat unverified paper titles as leads, not citations.
- Use deterministic baselines before live hosted model branches.
- Separate narrative surface quality from game-state validity in the metric suite.
- Preserve all generated traces, rejected candidates, repairs, and final accepted states.

### Constraints

- SCI-E-level drafts need precise baselines, reproducible datasets, ablation studies, statistical tests, and threat-to-validity analysis.
- Generated story content may contain sensitive themes, bias, or age-inappropriate material; human-review and content-safety gates are required.
- Google Drive/Docs creation needs authenticated Workspace access outside this local tool session; this page is the local handoff source.

## Literature grounding status

Verified anchors (resolvable links):

- IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds, 2026 — https://doi.org/10.48550/arXiv.2606.13348
- Large Language Models Are Neurosymbolic Reasoners, AAAI 2024 — https://doi.org/10.1609/aaai.v38i16.29754
- Bringing Stories Alive: Generating Interactive Fiction Worlds, AIIDE 2020 — https://doi.org/10.1609/aiide.v16i1.7400

Unverified leads requiring follow-up (`TODO-BIB`, no resolvable DOI yet):

- World-State Transformations for Neuro-symbolic Interactive Storytelling, 2026 — OpenAlex adjacent lead.
- Interleaving a Symbolic Story Generator with a Neural Network-Based Large Language Model.
- Neuro-Symbolic Synergy for Interactive World Modeling (NeSyS).

## Paper A: validated interactive-fiction generation

### Working title

**Constraint-Audited LLM Generation for Playable Interactive Fiction Worlds**

### Research question

Can an LLM-plus-symbolic-validator pipeline generate richer interactive-fiction worlds while reducing invalid world states, unreachable puzzles, and narrative contradictions compared with LLM-only and symbolic-only baselines?

### Core method

1. Convert a story seed into a symbolic world schema: locations, objects, characters, locks, keys, goals, preconditions, effects, and invariants.
2. Ask the LLM to propose incremental content: rooms, objects, quest steps, puzzle chains, and narrative descriptions.
3. Run symbolic validation for reachability, solvability, object placement, causal consistency, and progression.
4. Use a repair loop: invalid content is returned to the LLM with structured error messages or repaired by deterministic transformations.
5. Commit only validated transformations to the world-state graph.
6. Generate player-facing narration from the committed graph, not from unvalidated free text.

### Main experiments

- **E1 Validity:** compare LLM-only, symbolic-only, and neuro-symbolic systems on invalid transition rate, unreachable-object rate, unsolvable-puzzle rate, and contradiction count.
- **E2 Expressiveness:** human-rate story coherence, novelty, engagement, and world believability.
- **E3 Repair efficiency:** measure repair-loop success rate, number of iterations, token cost, and latency.
- **E4 Generalization:** run across fantasy, sci-fi, mystery, and educational puzzle domains.
- **E5 Ablation:** remove retrieval, remove symbolic validator, remove repair loop, remove graph memory.

## Paper B: KG-grounded RPG NPC dialogue

### Working title

**Knowledge-Graph-Grounded LLM Dialogue for Consistent RPG NPCs**

### Research question

Does a knowledge-graph and symbolic dialogue-state controller reduce lore contradictions and improve character consistency in LLM-generated RPG NPC dialogue without reducing perceived naturalness?

### Core method

1. Build or import a game-lore knowledge graph with NPCs, factions, events, locations, secrets, relationships, and dialogue permissions.
2. Retrieve subgraphs relevant to the player’s utterance, quest state, and NPC memory.
3. Use symbolic dialogue policies to enforce what the NPC knows, can reveal, must conceal, or should refuse.
4. Generate response candidates with an LLM grounded in retrieved evidence and policy constraints.
5. Validate responses for contradiction, forbidden disclosure, relationship mismatch, quest-state mismatch, and tone/voice compliance.
6. Log citations and graph facts used in each response.

### Main experiments

- **E1 Lore consistency:** measure contradiction rate against a held-out world bible and event log.
- **E2 Dialogue-state compliance:** measure forbidden disclosure, premature quest hints, and relationship-inconsistent utterances.
- **E3 Player experience:** human-rate naturalness, character believability, responsiveness, and immersion.
- **E4 Multi-turn memory:** test consistency over 5/10/20-turn conversations.
- **E5 Ablation:** no KG, no symbolic policy, no RAG evidence, no validation gate.

## Shared platform plan for saas-of-funqa

### Minimum research stack

- **Contracts:** define schemas for `WorldState`, `StoryAction`, `QuestConstraint`, `NpcProfile`, `DialoguePolicy`, `ValidationResult`, and `ExperimentTrace`.
- **RAG corpus:** store world bibles, quest specs, lore documents, prior generated episodes, and evaluation rubrics.
- **Graph layer:** represent entities and relations from lore and generated state.
- **Validation service:** deterministic checks plus LLM-as-judge only for subjective or semantic contradiction tasks.
- **Evaluation dashboard:** aggregate validity metrics, human ratings, latency, token cost, and accepted/rejected generations.
- **Export:** generate manuscript tables, appendices, examples, and trace bundles.

### Suggested repo mapping

- `packages/contracts`: experiment schemas.
- `packages/ai`: generation, retrieval, validation, reranking, and answer/synthesis steps.
- `packages/db`: trace persistence and experiment result repositories.
- `apps/api`: experiment endpoints and evaluator routes.
- `apps/web`: research dashboard, annotation UI, and reviewer workflows.
- `data/evals`: fixed story/dialogue fixtures.
- `knowledge/wiki`: durable research plan, bibliography notes, and paper drafts.

## Twelve-week schedule

| Week | Milestone | Outputs |
|---|---|---|
| 1 | Bibliography verification and scope freeze | Verified BibTeX, inclusion/exclusion table, final paper titles |
| 2 | Dataset/fixture design | IF world seeds, RPG lore bible, dialogue scenarios, validation schema |
| 3 | Contract and trace schemas | Type/Zod schemas, JSON fixtures, evaluation rubric |
| 4 | Baseline systems | LLM-only, symbolic-only, RAG-only baselines |
| 5 | Paper A prototype | Incremental generation + symbolic validation + repair loop |
| 6 | Paper B prototype | KG retrieval + dialogue policy + response validator |
| 7 | Batch experiments | Initial validity, quality, cost, and latency results |
| 8 | Ablations | Remove major modules and quantify contribution |
| 9 | Human evaluation | Reviewer guide, annotation form, inter-rater agreement |
| 10 | Statistical analysis | Significance tests, effect sizes, tables, error analysis |
| 11 | Manuscript drafting | Paper A and Paper B full drafts with figures/tables |
| 12 | SCI-E polish | Related work, limitations, ethics, formatting, cover letters |

## Google Drive / Docs handoff plan

Target folder supplied by user:

`https://drive.google.com/drive/folders/1eSrudBtoQ-h8QACuEH0_2Hrjx7fYOThR`

Create three Google Docs from the local wiki files when authenticated Workspace access is available:

1. **Neuro-symbolic Game Story Research Plan 2026** — source: this file.
2. **Paper A Draft — Constraint-Audited LLM Generation for Playable Interactive Fiction Worlds** — source: `paper-draft-ivie-style-validated-game-story-generation-2026-06-28.md`.
3. **Paper B Draft — Knowledge-Graph-Grounded LLM Dialogue for Consistent RPG NPCs** — source: `paper-draft-kg-grounded-rpg-dialogue-2026-06-28.md`.

Suggested Docs structure:

- First page: title, target venue/journal class, version, authors, status.
- Body: manuscript draft or plan.
- Appendix: bibliography verification status, experimental fixtures, metrics table.
- Comment markers: `TODO-BIB`, `TODO-DATA`, `TODO-RESULT`, `TODO-FIGURE`, `TODO-ETHICS`.

## Immediate next actions

1. Confirm exact target genre: text adventure, RPG NPC dialogue, quest-generation tool, or mixed platform.
2. Verify full bibliographic records for the two unverified candidate titles.
3. Select 2–3 target SCI-E journals or conference-journal routes.
4. Decide whether experiments will use public text-game datasets, synthetic fixtures, or proprietary game-design documents.
5. Implement minimal schemas and fixtures before writing final claims.

