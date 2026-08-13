# Stage 3 IEEE ToG Outline and Evidence Map / IEEE ToG 아웃라인과 근거 맵

Status: **AWAITING USER APPROVAL**  
Target: IEEE Transactions on Games, full research article  
Main-paper ceiling: 10 typeset pages including references  
Abstract: 150--200 words, one self-contained paragraph

## Recommended scope change / 권고 범위 변경

### Working title

**TRACE-RPG: Event-Sourced Neuro-Symbolic Commit Gates for Auditable Interactive Game Worlds**

**TRACE-RPG: 감사 가능한 인터랙티브 게임 세계를 위한 이벤트 소싱 신경-기호 커밋 게이트**

“Affect-adaptive” is removed from the title because neither an affect estimator nor an adaptation
controller has produced evidence. Affect remains an explicitly future, non-authoritative extension.

### Central thesis

TRACE-RPG isolates stochastic game proposals from canonical mutation through an externally supplied
action policy, deterministic state-relative validation, bounded repair, and semantic replay. A designed
offline conformance pilot evaluates the implemented mechanism and measurement boundary; it does not
estimate live-model superiority or player benefit.

### Contribution set

| ID | Contribution | Evidence required in this paper | Status before Stage 4 |
| --- | --- | --- | --- |
| C1 | Versioned canonical-state, action-policy, candidate-event, and bridge contracts | Schema audit, valid/invalid fixtures, state-transition replay | implemented; pilot table needed |
| C2 | State-relative neuro-symbolic commit gate with bounded counterexample repair | Validator-domain matrix, repair ablation, termination argument | implemented core; comparative pilot needed |
| C3 | Content-linked repair history, semantic replay, and episode-continuity checks | Frozen mutation manifest and generated detection table | implemented core; mutation table needed |
| C4 | Assignment-complete offline harness with strict adapter boundaries and separated failure classes | Frozen assignments, result/trace linkage, generated accounting table | implemented core; pilot table needed |
| C5 | Preregisterable ten-model, human, retrieval/memory, and affect extension | Protocol/configuration only | future blueprint; not an empirical contribution |

## Page budget / 페이지 예산

| Component | Pages |
| --- | ---: |
| Title, abstract, index terms | 0.35 |
| I. Introduction | 0.70 |
| II. Related Work and Gap | 0.85 |
| III. Problem Definition and Guarantee Boundary | 0.65 |
| IV. TRACE-RPG Architecture and Algorithms | 1.75 |
| V. Deterministic Offline Pilot Method | 0.90 |
| VI. Pilot Results | 0.95 |
| VII. Discussion | 0.65 |
| VIII. Confirmatory Extension | 0.55 |
| IX. Threats, Ethics, and Artifact Scope | 0.35 |
| X. Conclusion | 0.15 |
| References | 1.50 |
| Layout contingency | 0.65 |
| **Maximum** | **10.00** |

The model matrix, complete schemas, full fixture catalog, human instrument, power analysis, and extended
statistics move to supplementary material.

## Detailed IMRaD plan / 상세 IMRaD 계획

### Abstract

Use five moves within 150--200 words: problem; bounded literature gap; method; exact offline pilot
result; scope-limited conclusion. The final sentence must exclude live ten-model, human, affect, and
engine-performance inference.

`[NEEDS EVIDENCE: frozen pilot manifest hash, generated result-table hash, exact fault denominator]`

Index terms: game artificial intelligence, interactive narrative, neuro-symbolic systems, constrained
generation, reproducibility.

### I. Introduction

#### A. Fluent content is not an executable transition

Use S03, S11--S13, S15, S18, and S20--S22 to distinguish language plausibility from interactive state,
quest, and disclosure constraints. Avoid any unmeasured prevalence claim about present systems.

#### B. Authorization is distinct from structure, retrieval, and role play

- Structure/schema admissibility: S09, S10, S36.
- Retrieval and memory as evidence, not authority: S04--S07.
- Believability versus knowledge/disclosure correctness: S02, S03, S07, S08, S17, S21, S22.

#### C. Contributions and scope

Present C1--C4 as the current contributions and C5 as a reproducible extension blueprint. End with:

> This paper reports deterministic offline conformance evidence for the controller and research
> harness; ten-model, human-participant, retrieval/memory, affect-adaptation, and commercial-engine
> studies are future confirmatory evaluations and are not part of the present empirical claims.

### II. Related Work and Research Gap

#### A. Neuro-symbolic worlds and grounded NPC dialogue

S01--S03, S11, S12, and S20--S23. Mark S01/S02 as preprints and recheck the future-issue metadata of
S23 before submission.

#### B. Structured and constrained generation

S09, S10, S36. The gap is semantic authorization: omitted prerequisites, unauthorized effects,
quest-stage regression, and disclosure cannot be resolved by syntax alone.

#### C. Graph retrieval, long-term memory, and role simulation

S04--S08. These modules may condition proposals; the method denies them direct commit authority.

#### D. Interactive-agent and game evaluation

S13--S19, with S16 supporting process-level observation rather than terminal score alone.

#### E. Bounded novelty statement

> Among the 36 works in the approved evidence pool, no reported method was found to jointly expose an
> externally supplied action-policy boundary, state-relative hard validation, bounded structured
> repair, repair-history-linked semantic replay, and assignment-complete failure accounting.

This is a scoped evidence-pool finding, not an absolute “first.”

**Table I:** prior-system capability matrix. Caption: method reports were compared; systems were not
reproduced head to head.  
`[NEEDS EVIDENCE: comparator extraction sheets and final submission-date source-status check]`

### III. Problem Definition and Guarantee Boundary

#### A. Canonical and non-authoritative context

Define canonical state

\[
c_t=(G_t,q_t,m_t),
\]

where `G` is typed world state, `q` is the externally supplied action/quest/disclosure policy, and `m`
is the committed event prefix. Retrieval, narrative scores, model rationale, memory summaries, and
future affect estimates are proposal context, not canonical authority.

#### B. Proposal, validation, and atomic transition

Define

\[
V(c_t,a_t)=(v_{schema},v_{policy},v_{pre},v_{reach},v_{know},v_{disc},v_{quest},E_t)
\]

and

\[
c_{t+1}=\begin{cases}
T(c_t,a_t), & \bigwedge_i v_i=1,\\
c_t, & \text{otherwise.}
\end{cases}
\]

#### C. Propositions and assumptions

- **P1 — Exhausted-failure immutability:** if every recorded candidate through budget `K` is invalid,
  or proposal/controller execution fails before a committed outcome, the returned canonical state
  equals the supplied prior state. A failed initial candidate followed by a valid repair is not covered.
- **P2 — Bounded recorded attempts:** provided each proposer/repair callback returns within its
  separately enforced deadline, a repair budget `K>=0` permits at most `K+1` recorded candidate
  attempts. A successful application performs one additional defensive validation before mutation.
- **P3 — Encoded effect authorization:** a committed candidate has no declared fact effect outside
  the canonical action policy's allowed set, and any quest-stage target is explicitly listed in that
  action policy. This proposition remains conditional on complete structured-field extraction.
- **P4 — Replay consistency:** under fixed schemas and deterministic transition functions, accepted
  trace records reconstruct their stated final outcome. The current implementation does not claim to
  re-execute every intermediate repair-generation operation.

State assumptions explicitly: correct policy authorship, complete extraction into candidate fields,
single-process file ownership, deterministic versions, and honest hash recomputation boundary.

`[NEEDS EVIDENCE: independent formal domain/type audit; strict replay parser audit before P4 wording]`

### IV. TRACE-RPG Architecture and Algorithms

#### A. Trust and runtime boundaries

Describe the canonical owner, untrusted adapter, proposal response, schema boundary, validator,
repairer, result record, trace, and versioned game bridge.

**Figure 1:** SVG trust-boundary architecture:
`model/recording -> untrusted candidate -> strict parser -> semantic gate -> repair/fallback -> commit -> bridge`.

#### B. Typed candidate and canonical action policy

Explain required fields, defensive immutability, untrusted candidate declarations, and external policy
comparison.

**Table II:** validator predicate, state input, candidate input, error code, mutation rule, pilot fixture.
Cover unknown action, policy precondition/effect omission, unauthorized effect, false precondition,
unreachable object, NPC knowledge/disclosure, forbidden disclosure, quest-stage eligibility, and
quest-stage monotonicity.

#### C. Validate--repair--commit algorithm

Include compact IEEE algorithm pseudocode: validate; commit when valid; otherwise record structured
errors; repair only for `j<K`; revalidate against the same state; deterministic unchanged fallback.

#### D. Content integrity and semantic replay

Separate unkeyed `record_hash` and `trace_hash` checksums from semantic replay and JSONL state
continuity. Explicitly state that checksums are not signatures or authentication.

**Figure 2:** SVG proposal--validation--repair--fallback/commit--replay state machine.

#### E. Assignment-complete experimental records

Define the nine-part assignment key `(run, arm, scenario, seed, model, revision, controller hash, input
hash, prior-state hash)`, pre-execution freezing, exact set equality, duplicate rejection, result/trace
linkage, rollback behavior, and failure classes. Provider-response latency is conditional on observed
responses; it is not the treatment-policy end-to-end latency estimand.

### V. Deterministic Offline Pilot Method

#### A. Pilot questions

- **PQ1:** Do valid candidates commit while every named invalid-policy fixture falls back unchanged?
- **PQ2:** Under matched repairable/non-repairable fixtures, how do rejection-only, unchanged retry,
  and structured repair differ in commit and attempt outcomes?
- **PQ3:** Which frozen corruption classes are caught by checksum only versus checksum plus semantic
  replay and continuity validation?
- **PQ4:** Do strict adapter/schema and manifest gates preserve exactly one classified row per assigned
  case and reject inconsistent records?

#### B. Designed fixture domains

1. **Gate conformance:** matched valid/invalid authored cases covering every implemented failure code.
2. **Repair ablation:** rejection-only (`K=0`), unchanged retry (`K=1`), structured repair (`K=1`) on
   repairable and deliberately irreparable cases.
3. **Integrity ablation:** ordinary drift, rehashed impossible state, state/attempt/validation/control-flow
   mutation, disconnected episode, result/trace mismatch, and an injected second-file append failure
   with best-effort pair-write rollback.
4. **Adapter/accounting:** valid, symbolic-invalid, timeout/missing, malformed, non-JSON, response
   contract, duplicate assignment, and missing assignment cases.

The Stage 4 generator freezes the exact count and hashes. Unique fixtures, not repeated deterministic
seeds, are the descriptive denominator.

#### C. Metrics and analysis

- expected/observed validator class agreement;
- rejected/adapter-failure state-mutation count;
- repair commit and attempt counts by arm and repairability;
- rejected/planned mutations by designated operation; stable detector-layer attribution requires a
  separate typed detection-code protocol;
- replayed/committed traces;
- admitted/injected manifest violations;
- assignment-complete commit, symbolic-fallback, adapter-failure, and overall non-commit counts.

Report raw counts and exact proportions. Do not use inferential p-values or population confidence
intervals for purposively designed conformance fixtures. A local timing microbenchmark is diagnostic
only and requires machine, warm-up, repetitions, raw observations, and an end-to-end timer.

#### D. Reproducibility package

Freeze input fixtures, assignment-manifest hash, a result JSON artifact with embedded outcome/trace
records, strict schemas, environment/lock/commit snapshot, generated CSV/LaTeX tables, SVG figures,
and a checksum manifest.

### VI. Pilot Results

#### A. Gate and state isolation

**Table III:** generated case-level outcome matrix with expected class, observed class, prior/final state,
commit/fallback, and replay result.  
`[NEEDS EVIDENCE: generated Stage 4 artifact]`

#### B. Repair mechanism

Report exact outcomes for the three arms stratified by repairability. Do not call unchanged deterministic
retry an LLM sampling baseline.  
`[NEEDS EVIDENCE: frozen repair manifest and generated comparison]`

#### C. Integrity and replay fault injection

**Figure 3:** SVG evidence flow from mutation manifest to detector layer and generated result table.
Allowed language: “all/`x` of the implemented fault fixtures were rejected.” Forbidden language:
“tamper-proof” or “secure authentication.”  
`[NEEDS EVIDENCE: generated mutation results and denominator]`

#### D. Failure taxonomy and denominator integrity

**Table IV:** assigned cases, commits, symbolic fallbacks, adapter failures, response-observed count,
and injected manifest violations. The current two-row smoke appears only as a feasibility row, clearly
labelled hand-authored and non-inferential.

#### E. Result boundary

State that the pilot contains no live model call, participant, affect prediction, narrative-quality
comparison, or actual engine loop.

### VII. Discussion

#### A. What the pilot establishes

Mechanism feasibility, encoded-state isolation, replayable audit records, and failure-complete
measurement under the frozen fixtures.

#### B. What it does not establish

Semantic completeness, correct policy authoring, cross-model generalization, player benefit, real-time
engine performance, concurrent-writer safety, or adversarial cryptographic authenticity.

#### C. Relationship to prior work

Position state-relative authorization beyond syntax-only constraints S09/S10/S36; deny commit authority
to retrieval/memory S04--S07; complement rather than replace game environments/benchmarks S11--S18;
connect process traces to S16.

#### D. Game-engine implications

Discuss authoring-time validation, CI regression, recorded-adapter testing, and replay-based integration.
Avoid a portability claim until an actual engine bridge smoke runs.

### VIII. Confirmatory Extension — Future Work

#### A. Ten-model controller study

Preserve the 10-model exploratory screen, 3-model promotion, and registered failure-inclusive analysis
using S14--S18 and S31. H1 must use an independently labelled/audited semantic oracle rather than the
intervention validator as its sole outcome judge. H2 requires an implemented blind-retry arm and
per-attempt token/latency accounting. With one promoted model per profile, RQ5 is instance-level and
exploratory; it cannot identify access/scale-stratum effects. `C-RESULT-001`, `003`, and `005` remain
`TODO-RESULT`.

#### B. Retrieval and memory ablations

Compare RAG, KG, policy, HippoRAG/Mem0-like memory, and event sourcing at matched validity with S04--S07.
`C-RESULT-004` remains `TODO-RESULT`.

#### C. Matched-validity human dialogue study

Use S02, S17, S20--S23, S27--S30, and S35. Require player-qualified raters, blinding, randomized order,
attention checks, reliability, mixed effects, ethics review, consent, and prospective power.

#### D. Non-authoritative affect track

Use S08 and S23--S26. Affect cannot authorize state. The provisional 2-percentage-point validity margin
requires an independent engineering/participant rationale before preregistration. `C-RESULT-002`
remains `TODO-RESULT`.

### IX. Threats, Ethics, and Artifact Scope

Organize threats as construct, internal, external, conclusion, reproducibility, and security validity.
The offline pilot uses no human/personal data. Future human and affect tracks require applicable ethics
review, consent, retention/deletion rules, compensation disclosure, and opt-out. Anchor reporting and
analysis with S27--S35.  
`[NEEDS EVIDENCE: artifact/fixture license audit and release identifier]`

### X. Conclusion

Target wording:

> In a deterministic offline pilot, TRACE-RPG isolates tested generative game proposals from canonical
> mutation through an encoded neuro-symbolic commit gate and audits their outcomes through linked
> records and semantic replay. The evidence verifies the implemented mechanism for the frozen fixture
> domain; it does not establish cross-model superiority, player-experience benefit, affect efficacy, or
> commercial-engine performance. Those questions remain explicit confirmatory extensions.

## Contribution-to-evidence map / 기여-근거 맵

| Contribution | Sections | Pilot evidence | Literature anchors |
| --- | --- | --- | --- |
| C1 transaction contract | III-A/B, IV-A/B | schema/conformance and unchanged-state cases | S03, S11, S12, S20 |
| C2 hard gate and repair | III-B/C, IV-C, V/VI-A/B | predicate matrix, repair/fallback, bounded termination | S01, S03, S09, S10, S36 |
| C3 trace and replay | IV-D, V/VI-C | checksum, semantic, linkage, continuity mutations | S11, S16, S33 |
| C4 offline experiment harness | IV-E, V/VI-D | adapter boundaries, assignments, rollback, failure taxonomy | S14--S19, S31, S33, S34 |
| C5 confirmatory blueprint | VIII | no current empirical result | S04--S08, S21--S32, S35 |

## Main-paper visual plan / 본문 시각화 계획

1. **Figure 1:** architecture and trust boundary, SVG source plus embedded-font PDF.
2. **Figure 2:** validate--repair--commit--replay state machine, SVG source plus PDF.
3. **Figure 3:** pilot fault-injection and evidence flow, generated SVG plus PDF.
4. **Table I:** prior-work capability matrix.
5. **Table II:** validator predicate and failure-code contract.
6. **Table III:** generated pilot outcome matrix.
7. **Table IV:** accounting and fault-detection summary.

## Stage 3 approval decisions / 승인 대상

Approval accepts all four decisions:

1. remove “affect-adaptive” from the current title and empirical contribution;
2. center the present paper on the commit gate, repair, semantic replay, and experiment accounting;
3. report deterministic designed fixtures as a bounded conformance pilot without inferential claims;
4. retain the ten-model, retrieval/memory, human, affect, and engine studies as future confirmatory work.
