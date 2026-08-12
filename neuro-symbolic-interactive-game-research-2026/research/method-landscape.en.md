# 2026 Method Landscape

| Method | Game application | TRACE-RPG role | Principal failure mode |
|---|---|---|---|
| TextWorld-style symbolic state | Objects, rooms, inventories, action preconditions | Executable reference world and reachability oracle | Cannot encode all natural-language semantics |
| Graph retrieval / PCST GraphRAG | Retrieve lore relevant to the active quest and NPC | Minimize proposer context while preserving evidence IDs | Retrieval cannot guarantee rule compliance |
| KNUDGE-style entity/quest conditioning | Bound dialogue by NPC goals, relations, and quest facts | Candidate utterance generation and evidence comparison | Asset/license constraints and role-dependent effects |
| LLM formalization + Z3/rule checking | Convert natural-language proposals into predicates and events | Hard commit gate with counterexample/unsat-core repair | Cannot prove commonsense properties that were never encoded |
| Event-sourced temporal memory | Order observations, utterances, and state mutations | Deterministic replay and memory conflict resolution | Mistaking retrieved memory for authoritative state |
| Generative-agent simulation | NPC and synthetic-player stress testing | Generate rare, long-horizon scenarios | Not a substitute for human experience evidence |
| Language/visual world models | Predict screen and action consequences | Candidate policy and video-observer auxiliary | Hallucinated state may leak into canonical state |
| RL play-style agents | Explore with diverse behavior policies | Path, difficulty, and deadlock stress testing | Weak representativeness of real player populations |
| BALROG-like multi-environment evaluation | Compare tool use and gameplay across models | External capability and generalization reference | Does not directly test project-specific rule safety |
| Uncertainty-calibrated affect models | Estimate and adapt tension/arousal signals | Soft objective with a safe fallback | Conflating tension, engagement, stress, and flow |

The recommended system ladder is `S0 LLM-only → S1 + graph retrieval → S2 + typing/validation → S3 + counterexample repair → S4 + temporal memory → S5 + affect adaptation`. Every stage shares the same candidate budget and validity audit.

