# TRACE-RPG Controller

TRACE-RPG is the unified research artifact synthesized from the original world-generation, NPC-dialogue, and affect-adaptation plans.

At step `t`, canonical state is `c_t = (G_t, q_t, m_t)`: a typed world/knowledge graph, authoritative action/quest/disclosure policy, and immutable event prefix. The uncertain affect estimate `z_t` is non-authoritative context, so the proposer observes `s_t = (c_t, z_t)` but cannot commit it. An independently authored action-policy oracle first rejects omitted requirements and non-allowed effects; precondition, reachability, NPC knowledge, disclosure, quest, and schema checks then determine whether a typed event commits. Invalid candidates leave state unchanged and receive bounded counterexample repair; exhaustion invokes a deterministic fallback.

The research contribution is the controller boundary and traceability rather than a claim that one model is a complete NPC or world engine. The game and research tracks compile separately and interoperate through a versioned event schema.

Related: [[wiki/concepts/hard-validity-soft-adaptation]], [[wiki/concepts/journal-grade-experimental-design]], [[wiki/projects/trace-rpg-paper-2026]].
