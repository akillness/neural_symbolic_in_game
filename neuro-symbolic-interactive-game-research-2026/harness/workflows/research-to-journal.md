# Research-to-journal workflow

```text
P0 preflight
  -> P1 evidence harvest (parallel)
  -> G1 provenance and license gate
  -> P2 ontology + formal claims
  -> G2 math/logic and semantic-completeness gate
  -> P3 pilot + power simulation
  -> G3 preregistration/experimental-design gate
  -> P4 ten-model screen
  -> G4 frozen Pareto promotion
  -> P5 three-model confirmatory experiment + human study
  -> G5 statistics/reproducibility gate
  -> P6 bilingual manuscript
  -> G6 independent claim and journal-scope audit
```

## Phase contracts

- P0 records tool versions, command surfaces, hardware, model availability, and secrets-free environment metadata.
- P1 uses primary sources first and Scrapling only when robots/terms permit. Search snippets are leads, not evidence.
- P2 defines each state variable and predicate, generates counterexamples, and labels unencoded semantic assumptions.
- P3 freezes estimands, primary endpoints, exclusion/missing-data rules, seed allocation, power simulation, and stopping rules.
- P4 is exploratory. It cannot populate confirmatory paper result claims.
- P5 writes append-only JSONL events and a manifest hash before analysis.
- P6 changes a `TODO-RESULT` only through the result-promotion workflow.

## Failure policy

Retry transient retrieval/model failures with bounded backoff. Do not retry a design or logic failure into success; revise the artifact, increment its version, and rerun the gate. Escalate licensing, ethics, scope, or irrecoverable data-integrity failures to the human principal investigator.

