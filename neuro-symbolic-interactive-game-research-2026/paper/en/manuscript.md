# TRACE-RPG: An Event-Sourced Neuro-Symbolic Harness for Auditable and Affect-Adaptive Interactive Game Worlds

> **Superseded protocol blueprint — not the current empirical manuscript.** The authoritative Stage 4
> draft is [`../latex/en/main.tex`](../latex/en/main.tex), with machine-generated designed-fixture
> results and explicit evidence boundaries. This file is retained only as a future confirmatory-study
> plan; none of its ten-model, memory, affect, human, or engine statements are completed results.

**Target manuscript:** IEEE Transactions on Games first; method-first redirection to Knowledge-Based Systems is decided after results.  
**Status:** protocol-complete draft; all empirical values are `TODO-RESULT`.  
**Claim namespace:** `C-*` identifiers are shared with the Korean draft and `research/claim-ledger.yaml`.

## Abstract

Large language models can produce expressive game worlds and dialogue, but unconstrained generations may create impossible transitions, leak quest information, or contradict long-term character knowledge. We propose TRACE-RPG, an engine-neutral controller that separates stochastic proposal from canonical state mutation. A typed event log, knowledge graph, quest/disclosure policy, and deterministic validator form a hard commit gate; failed candidates receive structured counterexamples for bounded repair. Temporal memory and uncertainty-calibrated affect adaptation operate only as soft context and cannot override validity. The evaluation protocol screens ten open-weight and hosted models, promotes three using a preregistered Pareto rule, and then compares six system configurations over world generation, NPC dialogue, and affect adaptation with held-out worlds and quest motifs. Primary outcomes, mixed-effects analyses, semantic validator audits, human evaluation, latency, energy, and reproducibility are specified before execution. Results are intentionally omitted until trace-backed confirmatory runs are complete (`TODO-RESULT`).

## 1. Introduction

Interactive games require more than plausible text. A proposed action must be executable in the current world; a non-player character (NPC) may reveal only what it knows and is permitted to disclose; quest progress must remain reachable; and adaptation should not trade safety for short-term engagement. Prompting and retrieval improve conditioning but do not make these properties invariant.

TRACE-RPG treats a model as a fallible proposer. The research contribution is a model-agnostic, event-sourced commit protocol and an evaluation design that separates formal validity, semantic omissions, narrative quality, and affective adaptation.

The planned contributions are:

1. a typed, engine-neutral state/event contract with deterministic replay;
2. a hard validation and bounded counterexample-repair protocol;
3. a temporal knowledge and affect layer whose outputs remain non-authoritative;
4. a two-stage, ten-model evaluation with matched-validity diversity and systems measurements; and
5. a trace-to-claim workflow designed for SCI/SCIE journal reproducibility.

No contribution is stated as empirically superior until its registered test passes.

## 2. Related work and research gap

Neuro-symbolic interactive-fiction systems such as IVIE demonstrate incremental validated construction [1], while symbolic scaffolding for NPC dialogue shows that effects can vary by character role [2]. KNUDGE conditions branching dialogue on quest and entity specifications [3]. TextWorld provides an executable symbolic reference for text-game states [4]. Graph retrieval [5], temporal memory [6], generative simulations, RL play-style agents [7], and game-agent benchmarks [8] offer complementary context and stress tests. Recent game-affect evaluation further warns that visible cues do not imply robust inference of latent engagement [9].

| Prior line | Executable state | Policy/disclosure gate | Temporal evidence | Affect under safety constraint | Cross-model systems cost |
|---|---:|---:|---:|---:|---:|
| IVIE / TextWorld | yes | partial | no | no | no |
| KNUDGE / scaffolded dialogue | partial | partial | no | no | no |
| G-Retriever / Mem0 | no game commit | no | yes | no | partial |
| BALROG / RL play styles | environment-dependent | no | episode-dependent | no | partial |
| TRACE-RPG protocol | yes | yes, for encoded policy | yes | yes, gated | yes |

This table states protocol coverage, not measured superiority. The present bibliography is a seed set rather than a systematic review; venue-ready work still requires database search strings, screening counts, DOI-normalized metadata, and a PRISMA-style exclusion record.

The unresolved gap is not a lack of generation methods. It is the absence of one auditable protocol that evaluates world transition safety, NPC disclosure, temporal memory, narrative diversity conditioned on validity, affect adaptation, and runtime cost across heterogeneous models without allowing any learned component to become canonical state.

## 3. Problem formulation

At step \(t\), canonical state is

\[
c_t = (G_t, q_t, m_t),
\]

where \(G_t\) is the typed world/knowledge graph, \(q_t\) is authoritative action, quest, and disclosure policy, and \(m_t\) is the immutable event prefix. The learned affect estimate \(z_t\) is explicitly non-authoritative. The proposer observes context \(s_t=(c_t,z_t)\) and samples candidate event \(a_t\):

\[
a_t \sim p_\theta(a\mid c_t,z_t,R_k(c_t),h_t),
\]

where \(R_k\) is bounded graph retrieval and \(h_t\) is the visible interaction history. The deterministic validator returns a vector of predicate outcomes and counterexamples:

\[
V(c_t,a_t)=(v_{policy},v_{pre},v_{reach},v_{know},v_{disc},v_{quest},E_t).
\]

The commit transition is

\[
c_{t+1}=\begin{cases}
T(c_t,a_t), & \bigwedge_i v_i=1,\\
c_t, & \text{otherwise.}
\end{cases}
\]

Only the first branch mutates canonical state. Repair samples \(a_t^{(j+1)}\) from the prior candidate and structured error set \(E_t^{(j)}\), with \(j<K\). Exhaustion invokes a deterministic fallback rather than an unchecked generation.

Hard validity is lexicographically prior to soft quality. For valid candidates, selection may maximize

\[
J(a)=\lambda_n N(a)+\lambda_g Q_g(a)+\lambda_a A(a)-\lambda_c C(a),
\]

where \(N\) is narrative quality, \(Q_g\) is groundedness, \(A\) is affect-curve utility, and \(C\) is latency/token/energy cost. No value of \(J\) can authorize an invalid commit.

## 4. System architecture

The controller has five separable layers:

1. **Evidence and state:** typed graph, policy state, immutable events, and content-addressed assets.
2. **Retrieval:** current subgraph extraction with evidence identifiers and a fixed context budget.
3. **Proposal/formalization:** text or multimodal model produces a schema-constrained candidate; its declared preconditions and effects remain untrusted.
4. **Validation/repair:** an independently authored action-policy oracle rejects omitted requirements and non-allowed effects; precondition, reachability, NPC knowledge, disclosure, quest, and schema checks then produce counterexamples. Narrative-to-fact semantic extraction remains a separately audited learned check and is not claimed as a formal guarantee.
5. **Commit/observe:** valid events are committed, replayed into the engine, and logged with exact revisions and timing.

The game engine and research runtime compile independently. Their only shared mutable boundary is the versioned bridge event; traces can therefore be replayed against a mock engine or a recorded model response.

## 5. Research questions and hypotheses

- **RQ1 / H1 (`C-RESULT-001`):** The full commit gate lowers hard violation probability relative to LLM-only and retrieval-only systems across promoted models.
- **RQ2 / H2 (`C-RESULT-003`):** Structured counterexample repair yields higher repair@K and fewer generated tokens than blind retry at the same K.
- **RQ3 / H3 (`C-RESULT-004`):** Graph retrieval plus event-sourced temporal memory reduces long-horizon contradictions while preserving matched-validity narrative diversity.
- **RQ4 / H4 (`C-RESULT-002`):** Affect adaptation lowers target-curve error without a non-inferior hard-validity margin violation.
- **RQ5 / H5 (`C-RESULT-005`):** The controller effect remains directionally consistent across model-access and scale strata.

## 6. Experimental design

### 6.1 Models and stages

Stage 1 screens the ten exact entries in `configs/model-matrix.yaml` over 30 scenarios per track and three repetitions. It is exploratory and cannot support final causal claims. A frozen Pareto rule promotes the best hosted control, feasible open-weight model, and at-most-32-GB profile on hard validity, human quality, p95 latency, and cost.

Stage 2 evaluates the promoted three over 120 scenarios per track and five seeds in six systems: LLM-only, RAG, KG, KG+policy, full validator+repair, and full+affect. Ablations remove retrieval, policy, validation, repair, memory, or affect. World, quest-template, NPC identity, and relation-motif splits prevent near-duplicate leakage.

### 6.2 Scenarios

World-generation families cover fantasy, mystery, science fiction, and educational puzzles. Dialogue families cover hints, bargaining, deception, memory, and relationship change. Affect families include rising, relief, oscillating, and uncertain-observation curves. Adversarial cases include unreachable objects, contradictory observations, premature secret requests, stale memories, unsatisfiable repair cores, and misleading visual affect cues.

### 6.3 Outcomes

One primary endpoint is registered per track: valid episode rate, hard dialogue violation rate, and tension target RMSE subject to a hard-validity non-inferiority constraint. Secondary outcomes include violations per candidate, solvability, forbidden disclosure, repair@K, temporal contradictions, KG precision/recall, matched-validity semantic diversity, blinded naturalness, p50/p95 latency, tokens, VRAM, energy, and validator false-positive/false-negative rates.

### 6.4 Human evaluation

A pilot estimates variance and task duration; confirmatory sample size is chosen prospectively through simulation/power analysis rather than an arbitrary participant count. Presentation order is randomized and blinded. Participants evaluate matched-validity outputs only, preventing an invalid but fluent response from winning on style. Inclusion/exclusion, attention checks, consent, compensation, demographics, inter-rater reliability, and adverse events are reported. Synthetic players never replace the human study.

### 6.5 Statistical analysis

The episode is the analysis unit; candidate events are nested observations, not independent samples. Each `(model, scenario, seed)` is a paired block. The five seeds are repeated stochastic draws and never inflate the scenario count. Binary endpoints use mixed-effects logistic regression with system, promoted-model stratum, their interaction, and seed block as fixed terms, plus world and scenario-template random intercepts. Ordinal ratings use cumulative-link mixed models. Continuous endpoints use transformed hierarchical models or scenario-clustered hierarchical bootstrap intervals.

The confirmatory family is frozen before unblinding. H1 contains two primary contrasts (world and dialogue, Holm-adjusted at two-sided \(\alpha=.05\)); H2 and H3 each contain one two-sided \(\alpha=.05\) contrast. H4 uses hierarchical gatekeeping: validity must first be non-inferior at a 2-percentage-point absolute margin with one-sided \(\alpha=.025\), chosen as an engineering tolerance before confirmatory unblinding, before affect-RMSE superiority is tested at two-sided \(\alpha=.05\). RQ5's system-by-model interaction is secondary. API timeout, parse failure, and exhausted retry remain in the treatment-policy estimand as hard-invalid outcomes; a pre-response infrastructure failure is rerun once at the same seed with an audited reason, then scored as failure. Human-rating missingness is reported without single imputation and receives MAR plus delta-MNAR sensitivity analysis; missing energy telemetry is excluded only from the energy estimand. We report raw N, cluster and failure counts, exclusions, effect sizes, 95% intervals, and diagnostics.

## 7. Validation and falsification loops

### 7.1 Fact verification

Every factual statement maps to `research/source-ledger.yaml` and every planned result to `research/claim-ledger.yaml`. Primary sources are captured by Scrapling when permitted; inaccessible or robots-restricted pages retain only metadata and are not upgraded to verified evidence. The deep-research report and browser survey must agree on exact model IDs, release state, license, and scope.

### 7.2 Mathematical and logical audit

An independent reviewer checks state domains, quantifiers, denominators, boundary cases, reachability assumptions, repair termination, and the distinction between encoded soundness and semantic completeness. Property tests generate valid/invalid transitions; mutation tests remove predicates to measure audit sensitivity; manually labelled cases estimate validator false accepts and false rejects.

### 7.3 Experimental-design audit

Before confirmatory execution, a reviewer checks estimand-to-metric alignment, power, randomization, leakage, judge dependence, multiplicity, missing-data rules, stopping criteria, hardware comparability, and preregistration hashes. Failure freezes result promotion until repaired and rerun.

## 8. Planned results

All values are withheld until execution.

| Claim | Endpoint | Estimate | 95% CI | Status |
|---|---|---:|---:|---|
| C-RESULT-001 | Hard violation reduction | TODO-RESULT | TODO-RESULT | unverified |
| C-RESULT-003 | Repair efficiency | TODO-RESULT | TODO-RESULT | unverified |
| C-RESULT-004 | Temporal contradiction reduction | TODO-RESULT | TODO-RESULT | unverified |
| C-RESULT-002 | Affect tracking under validity margin | TODO-RESULT | TODO-RESULT | unverified |
| C-RESULT-005 | Cross-model consistency | TODO-RESULT | TODO-RESULT | unverified |

## 9. Threats to validity

Formal checks may be sound for encoded predicates but incomplete for natural-language meaning. Model APIs can drift despite snapshot identifiers. Open-weight models differ in serving stacks and quantization. Scenario authors may encode benchmark-specific assumptions. Human ratings can be culturally and linguistically sensitive. Affect labels remain noisy and should not be interpreted as clinical state. Results from text/mock environments may not generalize to real-time commercial games. These threats are measured where possible and otherwise bound the claims.

## 10. Ethics and artifact policy

The protocol avoids covert emotion manipulation, exposes adaptation controls, minimizes and pseudonymizes telemetry, and defines deletion/retention periods. Human data collection requires applicable institutional review and consent before recruitment. Licensed self-authored worlds replace proprietary game lore in released artifacts. Raw sources and traces remain immutable; derived tables record generating code and hashes.

## 11. Conclusion

TRACE-RPG makes an experimentally risky proposition testable: expressive learned generation can coexist with a non-negotiable symbolic commit boundary and auditable adaptation. The current contribution is a falsifiable protocol and runnable scaffold, not a positive result. Empirical conclusions will be written only after the registered, independently reviewed pipeline completes.

## References

1. *IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds*, arXiv:2606.13348, 2026. https://arxiv.org/abs/2606.13348
2. *Symbolically Scaffolded Play: Designing Role-Sensitive Prompts for Generative NPC Dialogue*, arXiv:2510.25820, 2025. https://arxiv.org/abs/2510.25820
3. *Ontologically Faithful Generation of Non-Player Character Dialogues*, arXiv:2212.10618, 2022. https://arxiv.org/abs/2212.10618
4. M. Côté et al., *TextWorld: A Learning Environment for Text-based Games*, arXiv:1806.11532, 2018. https://arxiv.org/abs/1806.11532
5. X. He et al., *G-Retriever: Retrieval-Augmented Generation for Textual Graph Understanding and Question Answering*, arXiv:2402.07630, 2024. https://arxiv.org/abs/2402.07630
6. P. Chhikara et al., *Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory*, arXiv:2504.19413, 2025. https://arxiv.org/abs/2504.19413
7. *Automated Play-Testing Through RL Based Human-Like Play-Styles Generation*, arXiv:2211.17188, 2022. https://arxiv.org/abs/2211.17188
8. D. Paglieri et al., *BALROG: Benchmarking Agentic LLM and VLM Reasoning On Games*, arXiv:2411.13543, 2024. https://arxiv.org/abs/2411.13543
9. *Do Vision Language Models Understand Human Engagement in Games?*, arXiv:2603.18480, 2026. https://arxiv.org/abs/2603.18480
