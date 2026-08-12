# SCI/SCIE Journal Target Gate

As-of date: 2026-08-12. Indexing, metrics, and editorial scope can change; this file is a planning record, not a permanent indexing claim.

| Priority | Candidate | Fit to TRACE-RPG | Manuscript emphasis | Gate before submission |
|---:|---|---|---|---|
| 1 | IEEE Transactions on Games | Direct fit: game AI, simulated worlds, player modelling, affective computing in games, game evaluation | Controller novelty + multi-game empirical evidence + player study | Recheck SCIE in Clarivate MJL; inspect the latest 24 months of accepted papers and author instructions |
| 2 | Knowledge-Based Systems | Strong fit when typed knowledge, symbolic reasoning, and hybrid AI are the main contribution | Formal method, semantic audit, cross-model generalization | Recheck SCIE and article type; demonstrate knowledge-based novelty beyond orchestration |
| 3 | IEEE Transactions on Affective Computing | Conditional fit if affect estimation/adaptation is independently validated | Uncertainty calibration, temporal affect model, human ground truth | Do not submit a game-controller paper with affect as a thin add-on |
| 4 | Entertainment Computing | Strong application and empirical/user-study fit | Playability, player experience, system architecture, evaluation | Recheck WoS collection in MJL; expand human study and deployment detail |

## Non-negotiable journal gates

1. **Novelty map:** compare against IVIE, KNUDGE, role-sensitive symbolic prompting, GraphRAG, temporal memory, and game-affect VLM work at the level of mechanism and evaluation—not keywords.
2. **Construct validity:** world validity, NPC consistency, tension, engagement, stress, and flow remain distinct constructs with separate operationalizations.
3. **Confirmatory statistics:** one primary endpoint per track; prospective power/simulation; model/world/participant random effects; effect size, 95% CI, and Holm adjustment.
4. **Human evidence:** preregistered inclusion/exclusion, blinded presentation order, attention checks, inter-rater reliability, ethics/consent record, and no substitution of synthetic players for people.
5. **External validity:** held-out worlds and quest motifs, at least two engine/mock environments, exact model revisions, and sensitivity to prompt and decoding choices.
6. **Semantic audit:** expert review of validator false accepts and false rejects, because formal guarantees cover only encoded predicates.
7. **Reproducibility:** immutable source and trace hashes, deterministic replay, configuration snapshots, hardware/energy reporting, artifact checklist, and negative results.
8. **Claim lock:** result prose cannot move from `TODO-RESULT` to `verified-empirical` until trace, analysis, and independent-review gates all pass.

## Submission decision

```text
game-specific controller contribution + strong player/game evaluation -> IEEE Transactions on Games
knowledge-representation/reasoning contribution dominates          -> Knowledge-Based Systems
affect inference is independently novel and human-validated        -> IEEE Transactions on Affective Computing
deployed application and user experience dominate                  -> Entertainment Computing
```

The final selection is made only after results exist. Journal rank or impact factor must not determine the method post hoc.

Official scope/index checks:

- IEEE Transactions on Games: https://transactions.games/
- Knowledge-Based Systems: https://www.sciencedirect.com/journal/knowledge-based-systems/about/aims-and-scope
- IEEE Transactions on Affective Computing: https://www.computer.org/csdl/journal/ta
- Entertainment Computing: https://www.sciencedirect.com/journal/entertainment-computing/about/aims-and-scope
- Clarivate Master Journal List: https://mjl.clarivate.com/
