# Paper Draft: Knowledge-Graph-Grounded LLM Dialogue for Consistent RPG NPCs 2026-06-28

Status: Draft v0.1 for research planning. Empirical result claims are intentionally marked `TODO-RESULT` until experiments are run.

## Working title

**Knowledge-Graph-Grounded LLM Dialogue for Consistent RPG NPCs**

## Target article type

SCI-E-oriented full research article in game AI, interactive narrative, computational creativity, or applied neuro-symbolic AI.

## Abstract

Role-playing game NPCs require dialogue that is natural, characterful, and responsive, while staying consistent with lore, relationships, quest state, faction politics, and what each character is allowed to know or reveal. LLMs can produce fluent NPC dialogue, but unconstrained generation often contradicts world facts, leaks future quest information, ignores relationship state, or breaks character voice. This paper proposes a neuro-symbolic dialogue framework that combines retrieval-augmented LLM generation with a game-lore knowledge graph and a symbolic dialogue-state controller. The knowledge graph stores entities, relationships, events, locations, secrets, and faction constraints; the symbolic controller enforces NPC knowledge boundaries, disclosure permissions, quest-state conditions, and relationship-dependent tone. Candidate responses are validated before display, with rejected responses repaired or regenerated. We propose experiments comparing LLM-only, RAG-only, knowledge-graph-only, and full neuro-symbolic variants across lore consistency, forbidden disclosure, multi-turn memory, believability, naturalness, latency, and cost. The expected contribution is an auditable architecture for high-quality RPG dialogue that balances expressive generation with explicit narrative and gameplay constraints.

## Keywords

Neuro-symbolic AI; RPG dialogue; NPCs; knowledge graphs; large language models; interactive narrative; game AI; dialogue state tracking; lore consistency; retrieval-augmented generation.

## 1. Introduction

NPC dialogue is one of the most visible places where generative AI can improve game development. Designers want characters who respond to player choices, remember past events, express personality, and improvise within a living world. But RPG dialogue is not free-form conversation: an NPC must not reveal a secret before the quest unlocks it, must not claim friendship with an enemy faction, must not forget a death or betrayal that already occurred, and must speak with a voice appropriate to their role and relationship state.

LLMs are strong at natural language but weak at guaranteed consistency. Retrieval-augmented generation improves grounding, yet retrieved lore alone does not enforce hard disclosure rules or dialogue policies. This paper proposes a knowledge-graph-grounded neuro-symbolic approach: an LLM generates candidate dialogue, while a symbolic policy layer and graph validator control what the NPC knows, may say, must avoid, and how the response should reflect game state.

## 2. Research questions

- **RQ1:** Does knowledge-graph grounding reduce lore contradictions versus LLM-only and RAG-only generation?
- **RQ2:** Does a symbolic dialogue policy reduce forbidden disclosures and quest-state violations?
- **RQ3:** Can the system improve consistency without reducing perceived naturalness or believability?
- **RQ4:** How does the approach scale across multi-turn conversations and evolving player history?
- **RQ5:** Which component contributes most: retrieval, graph facts, symbolic policy, response validation, or repair?

## 3. Related work outline

- **NPC dialogue and interactive narrative.** Authored trees, planner-based dialogue, and state machines preserve authorial control but scale poorly when players expect open-ended conversation.
- **LLM-driven game characters.** LLMs produce flexible responses but introduce contradiction, hallucination, tone drift, and unsafe disclosure; prompt-only methods are insufficient for strict game-state control.
- **Knowledge graphs and symbolic control.** Graphs structure entities, relations, and events; symbolic policies encode rules such as `npc_knows`, `can_reveal`, `relationship_threshold`, `quest_stage_required`, and `faction_alignment`.
- **Neuro-symbolic reasoning.** *Large Language Models Are Neurosymbolic Reasoners* (AAAI 2024) supports coupling LLMs with symbolic structures, treating the LLM as a surface realizer and candidate generator rather than the final authority over world facts.

## 4. Proposed method

### 4.1 System overview

1. **Dialogue context collector** — gathers player utterance, quest state, NPC identity, relationship state, recent history.
2. **Knowledge graph retriever** — extracts relevant subgraphs from lore, events, locations, factions, secrets, prior interactions.
3. **Symbolic dialogue policy engine** — computes what the NPC knows, can reveal, must conceal, and should emotionally express.
4. **LLM response proposer** — generates candidate replies grounded in the subgraph and policy.
5. **Response validator** — checks contradiction, forbidden disclosure, quest mismatch, relationship mismatch, voice constraints.
6. **Repair / regeneration loop** — revises invalid responses with structured error feedback.
7. **Trace logger** — stores final response, evidence facts, policy checks, validation result, cost/latency metrics.

### 4.2 Knowledge graph schema

The game-lore knowledge graph uses typed triples and event nodes:

```text
Entity types:
  Character, Faction, Location, Item, Quest, Event, Secret, Relationship, DialogueRule

Relation examples:
  member_of(Character, Faction)
  located_in(Entity, Location)
  witnessed(Character, Event)
  knows(Character, Fact)
  trusts(Character, Character, score)
  enemy_of(Faction, Faction)
  unlocks(QuestStage, Secret)
  can_reveal(Character, Secret, Condition)
```
  can_reveal(Character, Secret, Condition)


### 4.3 Symbolic dialogue policy

Before generation, the policy engine produces a compact control packet:

```json
{
  "npcId": "captain_mira",
  "knownFacts": ["player_saved_dock", "faction_red_sails_hostile"],
  "forbiddenFacts": ["prince_is_traitor"],
  "allowedHints": ["ask_about_lighthouse"],
  "relationshipTone": "guarded_respect",
  "questStage": "investigate_smuggler_route",
  "voiceConstraints": ["concise", "naval_metaphors", "no_modern_slang"]
}
```

The LLM receives this packet with retrieved graph evidence and must return a structured candidate with cited facts:

```json
{
  "response": "You kept the dock from burning, so I will give you this much: ships vanish when the lighthouse goes dark.",
  "usedFacts": ["player_saved_dock", "ask_about_lighthouse"],
  "withheldFacts": ["prince_is_traitor"],
  "tone": "guarded_respect"
}
```

### 4.4 Validation checks

- **Lore contradiction** — response conflicts with graph facts.
- **Forbidden disclosure** — reveals a locked secret or future quest fact.
- **NPC knowledge violation** — uses facts not known by the NPC.
- **Relationship mismatch** — tone contradicts trust, fear, faction, or romance state.
- **Quest-stage mismatch** — hint or instruction appears too early or too late.
- **Voice mismatch** — style conflicts with character voice constraints.
- **Safety mismatch** — output violates content or age-rating policy.

## 5. Experimental design

### 5.1 Systems compared

- **B1 LLM-only** — player utterance and NPC description only.
- **B2 Prompted LLM** — adds consistency instruction, no retrieval or validator.
- **B3 RAG-only** — retrieves lore snippets, no explicit graph or policy checks.
- **B4 KG-grounded generation** — uses graph facts in prompt, no symbolic validation.
- **B5 Policy-only template hybrid** — symbolic policies with templated responses.
- **Proposed** — KG retrieval + symbolic policy + LLM proposal + validation + repair.

### 5.2 Dataset and fixtures

Three fictional RPG worlds (fantasy kingdom, cyberpunk city, post-apocalyptic frontier), 20 NPCs per world with factions/secrets/relationship states/voice constraints, and 30 scenarios per world (quest hints, emotional reactions, bargaining, deception, memory references), with 5/10/20-turn variants for memory stress tests. Each scenario specifies ground-truth lore, NPC knowledge set, forbidden facts, allowed hints by quest stage, relationship/tone target, and expected validation constraints.

### 5.3 Metrics

| Dimension | Metric | Measurement |
|---|---|---|
| Lore consistency | Contradiction rate | Human audit + graph validator + sampled LLM judge |
| Disclosure control | Forbidden disclosure rate | Policy violation count |
| NPC knowledge | Unknown-fact usage rate | Response facts not in NPC knowledge set |
| Quest compliance | Premature/late hint rate | Quest-stage rule check |
| Character quality | Believability and voice rating | Blind human Likert ratings |
| Naturalness | Conversational fluency | Blind human Likert ratings |
| Memory | Multi-turn consistency | Contradictions across 5/10/20 turns |
| Efficiency | Cost and latency | Tokens, wall-clock, validation time |

### 5.4 Hypotheses

- **H1:** The full neuro-symbolic system reduces lore contradiction and forbidden disclosure versus LLM-only and RAG-only baselines.
- **H2:** RAG-only reduces some hallucinations but does not reliably enforce locked secrets or quest-stage rules.
- **H3:** Symbolic policy plus validation improves gameplay compliance with modest latency overhead.
- **H4:** Naturalness of the full system stays comparable to RAG-only because final surface realization is still LLM-performed.
- **H5:** Knowledge-graph grounding shows larger benefits in longer multi-turn conversations than single-turn prompts.

### 5.5 Statistical analysis

Proportion tests for violation rates; mixed-effects models for repeated NPC/world scenarios; non-parametric tests for ordinal human ratings. Report confidence intervals, effect sizes, and inter-rater reliability.

## 6. Planned implementation on saas-of-funqa

- `packages/contracts` — `NpcProfileSchema`, `LoreGraphFactSchema`, `DialoguePolicySchema`, `DialogueScenarioSchema`, `DialogueCandidateSchema`, `DialogueValidationResultSchema`, `DialogueExperimentTraceSchema`.
- `packages/ai` — graph-grounded retrieval, policy packet building, generation, validation, repair.
- `packages/db` — lore graph, dialogue trace, reviewer annotation repositories.
- `apps/api` — batch dialogue experiment endpoints.
- `apps/web` — reviewer dashboard for rating responses and inspecting evidence.
- `data/evals` — fixed RPG world bibles and dialogue scenarios.

Each generated response preserves a trace:

```json
{
  "scenarioId": "fantasy-guard-questhint-001",
  "npcId": "captain_mira",
  "playerUtterance": "What do you know about the lighthouse?",
  "retrievedFacts": ["f1", "f2"],
  "policyPacket": { "questStage": "investigate_smuggler_route" },
  "candidateResponses": [],
  "validationResults": [],
  "acceptedResponse": "...",
  "metrics": { "latencyMs": 0, "tokens": 0 }
}
```

## 7. Expected contributions

1. A neuro-symbolic architecture for RPG NPC dialogue grounded in explicit lore and dialogue policy.
2. A validation framework for detecting forbidden disclosures, knowledge violations, and quest-state mismatches.
3. A reproducible benchmark design for evaluating consistency and believability in open-ended RPG dialogue.
4. A trace schema linking each NPC response to graph facts, symbolic policy decisions, validation checks, and final text.

## 8. Threats to validity

Fictional test worlds may not capture commercial RPG complexity; believability/immersion ratings are subjective; KG construction requires authoring effort smaller teams may lack; LLM-as-judge components inherit model bias and must not replace human evaluation for final claims; results may depend on the base LLM and retrieval configuration.

## 9. Ethics and safety

NPC dialogue systems can produce offensive, manipulative, or age-inappropriate responses. Experiments require content-safety constraints, age-rating policies, bias review, and player-facing disclosure when AI generation is used. Designers retain override authority over canonical lore and sensitive story content.

## 10. Result placeholders

`TODO-RESULT`: lore contradiction table · forbidden disclosure table · naturalness/believability ratings · multi-turn memory analysis · ablation and cost table. `TODO-FIGURE`: KG-grounded dialogue architecture diagram · policy validation flowchart. `TODO-BIB`: verified BibTeX entries.

## References

- Large Language Models Are Neurosymbolic Reasoners, AAAI 2024 — https://doi.org/10.1609/aaai.v38i16.29754
- Generative Agents: Interactive Simulacra of Human Behavior, UIST 2023 — https://doi.org/10.1145/3586183.3606763
- World-State Transformations for Neuro-symbolic Interactive Storytelling, 2026 — OpenAlex lead, `TODO-BIB` (no resolvable DOI yet)
- Additional RPG dialogue, game narrative, and KG-grounded dialogue papers — `TODO-BIB` (to collect before submission)
