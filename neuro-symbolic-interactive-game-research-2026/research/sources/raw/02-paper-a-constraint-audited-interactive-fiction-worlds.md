# Paper Draft: Constraint-Audited LLM Generation for Playable Interactive Fiction Worlds 2026-06-28

Status: Draft v0.1 for research planning. Empirical result claims are intentionally marked `TODO-RESULT` until experiments are run.

## Working title

**Constraint-Audited LLM Generation for Playable Interactive Fiction Worlds**

## Target article type

SCI-E-oriented full research article in AI for games, computational creativity, interactive narrative, or applied neuro-symbolic AI.

## Abstract

Large language models can generate fluent and diverse interactive-fiction content, but unconstrained generation frequently violates game-world logic, producing unreachable objects, inconsistent puzzle chains, invalid preconditions, or contradictions with prior story state. This paper proposes a neuro-symbolic generation framework that separates creative proposal from validity enforcement. An LLM incrementally proposes rooms, objects, characters, quest steps, puzzles, and narration, while a symbolic world-state validator checks map topology, object reachability, inventory constraints, preconditions, effects, and narrative invariants before any content is committed. Invalid candidates are repaired through a structured feedback loop or deterministic transformation. We design a reproducible evaluation protocol comparing LLM-only, symbolic-only, retrieval-augmented, and neuro-symbolic variants across validity, playability, expressiveness, repair efficiency, and cost. The expected contribution is an auditable pipeline for playable interactive-fiction worlds that preserves LLM expressiveness while reducing hard game-logic failures.

## Keywords

Neuro-symbolic AI; interactive fiction; game AI; large language models; procedural content generation; narrative generation; symbolic validation; world-state modeling; RAG; quest generation.

## 1. Introduction

Interactive fiction and narrative games require both expressive language and strict state consistency. A generated world may sound plausible while being impossible to play: a key may appear behind the locked door it opens, a quest-giver may refer to an event that has not occurred, or a puzzle may require an unreachable object. These failures break player progression and undermine trust in AI-assisted authoring tools.

LLMs have improved the surface quality of generated narrative, yet they do not naturally maintain exact world-state invariants over long generation chains. Symbolic AI can encode preconditions, effects, constraints, and graph reachability, but is weak at varied prose. This paper investigates a neuro-symbolic middle path: use LLMs as candidate generators and symbolic systems as validators, repair guides, and commit authorities. It is inspired by 2026 work on incremental validated interactive-fiction generation (IVIE), and by earlier work such as *Bringing Stories Alive* and arguments that LLMs can act as neuro-symbolic reasoners when connected to symbolic structures.

## 2. Research questions

- **RQ1:** Does symbolic validation reduce invalid world-state transitions versus LLM-only generation?
- **RQ2:** Does a repair loop preserve or improve playability without collapsing narrative diversity?
- **RQ3:** Which components contribute most: retrieval grounding, symbolic validation, graph memory, or structured repair?
- **RQ4:** What is the cost and latency overhead of neuro-symbolic validation relative to LLM-only generation?
- **RQ5:** Can the framework generalize across genres (fantasy, mystery, science fiction, educational puzzle worlds)?

## 3. Related work outline

- **Interactive fiction generation.** Narrative generation must be evaluated not only as text but as a playable state space (*Bringing Stories Alive: Generating Interactive Fiction Worlds*, AIIDE 2020).
- **Neuro-symbolic narrative systems.** Recent work frames LLMs as creative but fallible proposal engines, with symbolic modules handling formal constraints and state updates (IVIE, 2026).
- **LLMs as neuro-symbolic reasoners.** *Large Language Models Are Neurosymbolic Reasoners* (AAAI 2024) supports coupling LLMs with external symbolic structures and tool calls.
- **Procedural content and quest constraints.** Quest and puzzle generation require causal ordering, object placement, precondition/effect modeling, and reachability analysis — motivating explicit validators over pure prompt engineering.

## 4. Proposed method

### 4.1 System overview

1. **Seed interpreter** — converts a high-level story seed into an initial symbolic schema.
2. **RAG context retriever** — retrieves relevant lore, prior state, genre rules, design constraints.
3. **LLM proposal engine** — generates candidate additions or transformations.
4. **Symbolic validator** — checks formal consistency and playability invariants.
5. **Repair controller** — converts validation errors into structured revision requests or deterministic corrections.
6. **Commit and narration layer** — commits only validated transformations and generates player-facing prose from the accepted state.

### 4.2 Symbolic world representation

A world state is a typed graph:

```text
WorldState = {
  locations: Location[],
  exits: Edge<Location, Location>[],
  objects: Object[],
  characters: Character[],
  inventoryRules: Rule[],
  questGoals: Goal[],
  preconditions: Predicate[],
  effects: Effect[],
  invariants: Invariant[],
  narrativeFacts: Fact[]
}
```


Key invariants:

- Every required object must be reachable before it is needed.
- A locked location cannot contain the only key needed to unlock itself unless an alternate route exists.
- A quest step cannot depend on an unachievable prior state.
- Character knowledge cannot include future events unless explicitly justified.
- A committed effect must have a satisfied precondition.

### 4.3 LLM proposal format

The LLM cannot mutate the world directly; it outputs a candidate transformation:


```json
{
  "actionType": "ADD_PUZZLE_CHAIN",
  "rationale": "Creates a two-step lock-and-key puzzle for the lighthouse.",
  "preconditions": ["player_has_map"],
  "effects": ["lighthouse_unlocked"],
  "newEntities": ["rusted_key", "tide_cave"],
  "narrativeText": "The tide cave exhales a briny wind..."
}
```


### 4.4 Validation and repair

The validator returns structured errors:


```json
{
  "valid": false,
  "errors": [
    {
      "code": "UNREACHABLE_REQUIRED_OBJECT",
      "entity": "rusted_key",
      "reason": "rusted_key is placed in lighthouse, but lighthouse requires rusted_key to enter.",
      "repairHint": "Move rusted_key to an accessible pre-lighthouse location or add an alternate entry path."
    }
  ]
}
```


The repair controller either requests a constrained LLM revision or applies a deterministic repair when the transformation is simple and safe.

## 5. Experimental design

### 5.1 Systems compared

- **B1 LLM-only** — direct generation without symbolic validation.
- **B2 Prompted LLM** — explicit consistency instructions, no validator.
- **B3 Symbolic-only** — rule-based generation with template narration.
- **B4 RAG-only** — LLM grounded in retrieved lore, no formal validation.
- **Proposed** — RAG + LLM proposal + symbolic validation + repair + committed graph.

### 5.2 Dataset and fixtures

40 seeds each for fantasy quests, mystery investigations, science-fiction exploration, and educational puzzles. Each seed defines minimal genre constraints, required plot beats, and permitted object classes. Public IF corpora may be used if licensing and reproducibility allow; otherwise synthetic fixtures are released with the paper.

### 5.3 Metrics

| Dimension | Metric | Measurement |
|---|---|---|
| Validity | Invalid transition rate | Validator-detected hard failures per world |
| Reachability | Unreachable required object rate | Graph traversal and dependency analysis |
| Playability | Solvability rate | Automated planner or player simulator |
| Consistency | Contradiction count | Rule checks plus human/LLM-assisted audit |
| Expressiveness | Human-rated engagement | Likert scale with blind raters |
| Diversity | Distinct entity/quest pattern ratio | Structural and lexical diversity metrics |
| Repair | Repair success rate | Percent invalid candidates fixed within N iterations |
| Efficiency | Cost and latency | Tokens, wall-clock time, validation time |

### 5.4 Hypotheses

- **H1:** The neuro-symbolic system reduces hard invalid-state failures versus LLM-only and prompted baselines.
- **H2:** Retrieval alone improves lore consistency but does not eliminate formal playability failures.
- **H3:** The repair loop recovers a large fraction of invalid proposals with lower diversity loss than rejection-only filtering.
- **H4:** Symbolic-only generation has high validity but lower human-rated expressiveness than LLM-based systems.

### 5.5 Statistical analysis

Non-parametric tests for ordinal human ratings; chi-square or Fisher tests for validity proportions; effect sizes and confidence intervals for all major comparisons; correction for multiple comparisons where appropriate.

## 6. Planned implementation on saas-of-funqa

- `packages/contracts` — `WorldStateSchema`, `StoryTransformationSchema`, `ValidationResultSchema`, `RepairAttemptSchema`, `GeneratedWorldTraceSchema`, `InteractiveFictionEvalDatasetSchema`.
- `packages/ai` — generation, retrieval, validation, repair, evaluation functions.
- `packages/db` — persistence for generated states and traces.
- `apps/api` — batch generation and evaluation endpoints.
- `apps/web` — reviewer dashboard and trace explorer.
- `data/evals` — reproducible story seeds and expected constraint profiles.

## 7. Expected contributions

1. A neuro-symbolic architecture for incremental generation of playable interactive-fiction worlds.
2. A validation-and-repair protocol that separates creative proposal from state mutation.
3. A reproducible evaluation matrix for playability, consistency, expressiveness, and efficiency.
4. An open trace format connecting narrative text, symbolic checks, and committed world-state transformations.

## 8. Threats to validity

Synthetic seeds may not represent professional game-design complexity; human ratings are subjective; LLM behavior changes across model versions; symbolic validators may miss semantic contradictions not encoded as rules; repair loops may overfit to validator feedback and reduce creative diversity.

## 9. Ethics and safety

Generated narrative systems can produce biased, violent, sexual, or culturally insensitive content. Experiments require content filters, age-rating constraints, human review, and clear disclosure that text is AI-generated. Player-facing deployment should log model decisions and provide developer override controls.

## 10. Result placeholders

`TODO-RESULT`: validity table · human evaluation table · ablation table · cost/latency table. `TODO-FIGURE`: system architecture diagram · repair-loop flowchart. `TODO-BIB`: verified BibTeX entries.

## References

- IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds, 2026 — https://doi.org/10.48550/arXiv.2606.13348
- Bringing Stories Alive: Generating Interactive Fiction Worlds, AIIDE 2020 — https://doi.org/10.1609/aiide.v16i1.7400
- Large Language Models Are Neurosymbolic Reasoners, AAAI 2024 — https://doi.org/10.1609/aaai.v38i16.29754
- World-State Transformations for Neuro-symbolic Interactive Storytelling, 2026 — OpenAlex lead, `TODO-BIB` (no resolvable DOI yet)
