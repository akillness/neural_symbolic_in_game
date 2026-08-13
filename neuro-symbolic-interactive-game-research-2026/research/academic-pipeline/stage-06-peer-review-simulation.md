# Stage 6 Peer-Review Simulation / 6단계 동료심사 시뮬레이션

Status: **REVISE_AND_RESUBMIT — USER DECISION REQUIRED**

Review date: 2026-08-13

Target: IEEE Transactions on Games, Full Paper

Review ensemble: EIC, R1 methodology, R2 related work, R3 clarity/reproducibility, and adversarial
Devil's Advocate

Evidence baseline: Stage 4 bilingual six-page manuscripts, Stage 4 deterministic conformance
packet, Stage 4.5 claim-faithfulness audit, and Stage 5 citation-identity audit

> **Post-review resolution note (2026-08-13):** this review's unknown-field and assignment-count
> findings describe its pre-Stage-8 baseline. The current rerun has 2 open semantic/policy
> sentinels, a separate 1/1 closed unknown-key regression, and 64 bound provenance rows (43
> executed + 21 aggregate). Statements below are retained as historical reviewer evidence.

## Editorial decision / 편집 판정

The simulated decision is **revise and resubmit for the declared Full Paper track**. The topic is
within the journal's game-AI and game-software scope, and the implemented authorization, replay, and
assignment-accounting boundary is coherent. The present evidence nevertheless remains a
purposively authored deterministic conformance suite. It does not yet establish scientific efficacy,
comparative advantage, game-world generality, or interactive-system value at the level expected of
a mature Full Paper.

현재 판정은 선언된 Full Paper 트랙에 대한 **대폭 수정 후 재투고**다. 주제와 구현된 경계는
저널 범위에 부합하지만, 현재 근거는 저자가 설계한 결정론적 적합성 파일럿에 한정된다.
과학적 효능, 비교 우위, 게임 세계 일반화, 상호작용 시스템 가치를 입증하려면 별도의
확증 실험이 필요하다.

The same six-page packet could be reframed as a Short Paper after major revision, but that would be a
change in contribution contract. This review retains the user-approved Full Paper objective. The
official journal guidance lists Full Papers as 10--14 pages and Short Papers as 6--8 pages, with the
detailed limits described as 10 and 6 pages before over-length charges, respectively.

Official policy checks used in this review:

- ToG submission guidance: <https://transactions.games/submit/submission-guidelines>
- IEEE AI-generated-content disclosure policy:
  <https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/>

## Reviewer scorecard / 심사 점수표

| Role | Focus | Score | Recommendation |
| --- | --- | ---: | --- |
| EIC | fit, significance, maturity | 5.0/10 | Revise and resubmit as Full Paper; Major Revision if reframed as Short Paper |
| R1 | method and experimental design | 5.0/10 | Major evidence-generating revision |
| R2 | related work and positioning | 5.5/10 | Major Revision |
| R3 | clarity, reproducibility, presentation | 7.0/10 | Major Revision |
| Devil's Advocate | strongest rejection case | n/a | Reject the present Full Paper evidence package |

These scores are reasoned reviewer judgements, not calibrated probabilities or empirical
measurements.

## Shared strengths / 공통 강점

1. The manuscripts maintain an unusually disciplined boundary between encoded conformance and
   semantic safety, model efficacy, player benefit, retrieval, affect, and engine performance.
2. The proposal/commit separation, defensive revalidation, bounded repair, state-semantic replay,
   and assignment-complete terminal accounting form a coherent systems design.
3. Negative guarantees and known gaps are visible: unknown proposal fields, omitted semantics,
   unkeyed checksums, unauthenticated repair provenance, and single-writer assumptions.
4. Stage 4.5 mechanically verified bilingual numeric, equation, figure, label, citation-key, and
   claim parity. Stage 5 found 33 verified records, 3 preprints, and no unmatched or hallucinated
   citation identity.
5. The six-page PDFs are readable, anonymous, and mechanically clean; the English abstract is
   within the journal's 150--200-word requirement.

## Critical findings / 필수 수정 사항

### C1. Full-paper efficacy and external validity are absent

The current denominators are authored fixtures, not sampled model/game/player observations. There
is no live model, independently labelled semantic oracle, held-out world or quest template, genuine
blind-retry baseline, actual engine loop, or participant result. The controller validator also
cannot serve as the sole independent outcome oracle for a claim that the controller improves
validity.

**Acceptance criterion:** preregister and execute assignment-complete model/controller experiments
with held-out templates and an independently authored encoded-and-semantic oracle. At minimum,
compare direct commit, structural constraint only, validator-only rejection, matched-budget blind
retry, structured repair, and the complete TRACE-RPG path. Preserve timeout/parse/controller
failures in the estimand and report effect sizes, uncertainty, multiplicity handling, tokens,
latency, and cost. Treat scenario or held-out template as the independent unit and repeated seeds as
nested generations, rather than counting rows or seeds as independent scenarios; report variance
components and model/domain sensitivity. The hidden oracle must include disclosure, omitted-object,
and unknown-field hazards that the current boundary sentinels intentionally accept.

### C2. The reproducibility packet is internally frozen but not release-locked

The Stage 4 SHA manifest records base commit `3958c09`, `dirty: true`, and a local interpreter path.
This is adequate evidence for the recorded dirty snapshot but not a final anonymous release lock.
No clean tag, clean-environment reproduction record, archival identifier, or code/data availability
statement exists.

**Acceptance criterion:** after revision, generate the pilot and paper packet from a clean tagged
source commit, independently reproduce it in a fresh environment, remove user-specific paths from
the anonymous supplement, publish an anonymous review artifact, and later archive the accepted
artifact with a persistent identifier.

### C3. Required AI-use disclosure is missing

IEEE requires disclosure when AI-generated content contributes text, figures, images, or code. The
current manuscript has no such statement. ToG's current double-anonymous notice also prohibits
identity-revealing acknowledgments during review.

**Acceptance criterion:** add an anonymous, venue-compatible disclosure that identifies the AI
systems, affected manuscript/code/figure surfaces, assistance level, and authors' verification and
responsibility. Restore identifying acknowledgments only in the camera-ready version.

## Major findings / 주요 수정 사항

### M1. Direct scholarly lineage and comparators are incomplete

The related-work section begins mainly with recent LLM work. It needs the game-research lineage from
interactive narrative and computational story generation through hybrid neuro-symbolic design,
action shielding/agent guardrails, and event-log/replay architectures. The current claim that IVIE
is the "closest" comparator is not supported by a systematic comparative search and should be
reduced to "a direct recent game-specific comparator."

Recommended candidates must enter the normal source and Stage 5 verification gates before use:
Kybartas and Bidarra's computational-narrative survey, Riedl and Young/Bulitko on narrative planning
and interactive narrative, Alshiekh et al. on shielding, recent agent guardrails, modular
neuro-symbolic taxonomies, and event-sourcing literature. The comparison should distinguish proposer,
policy source, enforcement time, state-relative semantics, failure handling, evidence linkage, and
guarantee boundary.

### M2. Terminology currently exceeds the demonstrated mechanism

The pilot executes a modular proposal-to-symbolic-authorization architecture without live neural
inference. "Neuro-symbolic" therefore names the intended modular composition, not a trained hybrid
learner. Likewise, the implementation records and replays event traces but has not established that
canonical state is authoritatively reconstructed from a complete event store. "Transactional" does
not imply ACID or concurrent-writer safety.

**Acceptance criterion:** define these terms narrowly and cite their architectural lineages, or
retitle the system as an event-logged/audit-trailed staged authorization gate. Do not infer neural
efficacy, authoritative event sourcing, ACID behavior, or cryptographic auditability.

### M3. P1--P4 need proof status rather than proposition styling

The four statements agree with the present implementation boundary but are not formal theorems over
all executions. P1 and P2 are conditional on terminal exception handling and callback deadlines; P3
covers declared effects under an authored policy; P4 covers fixed schemas and deterministic replay,
not repair provenance.

**Acceptance criterion:** either provide proof/model-check/property-based evidence over the stated
transition system or rename them implementation invariants and give each invariant an assumption,
test family, and counter-scope.

### M4. The central algorithm omits experimentally important terminal paths

The pseudocode does not show adapter failure, controller exception, deadline enforcement,
assignment-row emission, result/trace pair persistence, or rollback. These paths are central to the
artifact's accounting contribution.

**Acceptance criterion:** expand the algorithm or add a companion state machine that maps every
terminal class to state mutation, trace availability, record emission, and aggregation treatment.

### M5. Artifact licensing and availability are unresolved

`pyproject.toml` uses `LicenseRef-Unspecified`. This prevents reviewers from treating the repository
as a reusable open-source artifact even though open-source components and model licenses are
catalogued elsewhere.

**Acceptance criterion:** select an explicit repository license with author approval, retain
third-party notices and per-model/data license records, and add code/data availability text. This
decision is intentionally not inferred by the review agent.

### M6. Game relevance needs an executed interactive path

The versioned bridge is an interface contract, not engine evidence.

**Acceptance criterion:** execute at least one multi-step headless or real engine scenario covering
quest progression, NPC knowledge/disclosure, save/load or replay, and frame/request budget
measurement. Keep engine-specific correctness separate from model-quality claims.

## Minor findings / 경미한 수정 사항

- Reduce the keyword list from six to the journal's required two to five.
- Recheck S23's future-dated issue metadata immediately before submission.
- Perform a professional Korean academic-language pass, reducing unnecessary code-switching and
  correcting particles such as `TRACE-RPG을`.
- Use "실제 모델 기반 우월성" rather than "실시간 모델 우월성" for live-model superiority.
- Clarify that AgentBoard motivates process-level measurement; immutable retention is TRACE-RPG's
  protocol choice.
- Prefer vector PDF/EPS figure inclusion where the final toolchain preserves font requirements.
- Remove user-specific paths and repository identity from the anonymous release packet.

## Devil's Advocate / 최강 반대 논거

The strongest rejection case is that the submission presents an excellent research artifact and
integration-test discipline as a mature Full Paper without independent evidence that the mechanism
helps a generative game system. The same authored validator defines the intervention and much of the
observed success criterion; all cases are purposive and tiny; no neural proposer, player, engine, or
held-out semantic judgement is present; and the claimed novelty is a combination whose nearest
lineages are not yet compared. Under this reading, the work is a promising protocol specification,
not yet a validated game-AI research result.

## Meta-review and revision order / 메타리뷰와 수정 순서

The findings are accepted into two revision classes, pending the mandatory user checkpoint:

1. **Immediate manuscript/artifact repair:** terminology, direct comparator matrix, invariant
   status, complete algorithm paths, five keywords, Korean language pass, AI disclosure template,
   availability statement, and clean-release instructions.
2. **Evidence-generating Full Paper work:** independent semantic oracle, held-out scenarios, live
   model/controller baselines, headless/engine integration, and confirmatory analysis.

Stage 7 cross-model verification remains optional and has not run. Stage 8 revision is blocked until
the user accepts, partially accepts, or rebuts this Stage 6 report. No finding in this review promotes
`C-RESULT-001` through `C-RESULT-005`; all five remain `TODO-RESULT`.
