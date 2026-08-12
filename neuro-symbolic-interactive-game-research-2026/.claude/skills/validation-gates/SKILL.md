---
name: validation-gates
description: Aggressively validate TRACE-RPG facts, formulas, logic, experimental design, game replay, statistics, and bilingual claims before any result or release is accepted.
allowed-tools: Read Write Edit Bash Grep Glob Agent
---

# TRACE-RPG Validation Gates

Trigger this skill for preregistration, validator changes, experiment launch, result analysis, paper revision, release, or submission. It exists because formal, empirical, and editorial validity fail in different ways.

## Gate selection

- **Evidence:** direct source, retrieval date, hash, access constraint, license.
- **Math/logic:** domains, quantifiers, boundary cases, counterexample, termination, encoded-vs-semantic scope.
- **Experiment:** estimand, primary endpoint, power, randomization, leakage, multiplicity, judge independence, missingness.
- **Runtime:** schema, property tests, replay equality, idempotency, failure fallback, p95 budget.
- **Statistics:** independent reproduction, effect size/interval, diagnostics, robustness, table checksum.
- **Manuscript:** claim-ledger link, `TODO-RESULT` lock, KO/EN parity, journal-scope and artifact checklist.

## Procedure

1. Define the claim that the gate can prove and its pass condition.
2. Run the smallest fresh validation that proves it.
3. Store command, version, inputs, output, and reviewer in `_workspace/gates/`.
4. On failure, return a counterexample or reproducible mismatch; do not edit the producer's artifact as reviewer.
5. Only the research orchestrator may advance the phase.

See `harness/workflows/verification-loops.md` and `harness/workflows/result-promotion.yaml` for transition rules.
