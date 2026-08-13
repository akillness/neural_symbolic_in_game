# Stage 2.5 Pre-Write Integrity Gate / 사전 집필 무결성 게이트

Status: **PASS WITH FAIL-CLOSED CLAIM BOUNDARIES**  
Audit date: 2026-08-12  
Repository revision audited: `3958c092d4e01d9091c2206ba3ae4719656d2eb4`  
Runtime snapshot: Python 3.13.9, uv 0.9.10

> **Historical gate snapshot.** Counts and replay behavior below describe the audited pre-pilot
> revision. Stage 4 supersedes the current implementation evidence with 63 passing tests plus three
> subtests and deterministic validation of every recorded attempt; see
> `stage-04-draft-report.md` and `stage-04-pilot/pilot-results.json`.

## Gate decision / 게이트 판정

The manuscript may advance to outlining only after its empirical center is narrowed to a deterministic
offline conformance pilot. Unsupported efficacy statements are retained solely as explicitly future,
preregistered hypotheses. No positive claim about ten-model performance, player preference, temporal
memory, retrieval, affect adaptation, or commercial-engine behavior may enter the abstract, results, or
conclusion.

원고의 실증 중심을 결정론적 오프라인 적합성 파일럿으로 제한하는 조건에서 다음 단계로
진행한다. 근거가 없는 효능 문장은 명시적인 미래 사전등록 가설로만 유지한다. 10개 모델
성능, 플레이어 선호, 장기 메모리, 검색, 감정 적응, 상용 엔진 동작에 대한 긍정적 주장은
초록·결과·결론에 들어갈 수 없다.

## Declared provenance / 선언된 provenance

| Evidence object | Fresh observation | What it can support | What it cannot support |
| --- | --- | --- | --- |
| Unit/integration suite | 41/41 authored tests passed on the audited revision | Conformance of the tested validator, repair, replay, schema, adapter, and accounting paths | Population error rates, semantic completeness, model quality, or player outcomes |
| Frozen-response smoke | Two assigned rows: one commit and one recorded timeout | End-to-end record/trace generation and assignment-complete descriptive accounting | A model comparison, current live latency, confidence interval, or causal estimate |
| Smoke summary | commit `1/2`; overall failure `1/2`; adapter failure `1/2`; symbolic fallback `0/2`; response-observed `n=1`; recorded provider latency 842.5 ms; 318 input and 41 output tokens | Exact sanity values for the hand-authored fixture | General failure probability, p95 latency, efficiency, or reliability |
| Repair unit case | One invalid proposal repaired and committed with `K=1` | Existence of a functioning bounded repair path | `repair@K` performance or superiority to blind retry |
| Mutation tests | Authored checksum, replay, continuity, linkage, and rollback counterexamples | Detection behavior for the named mutations | Authentication, adversarial security, or exhaustive corruption detection |
| Ten-model and human-study files | Configuration and protocol only | Future evaluation plan | Any completed empirical result |

The fresh validation command also passed Ruff lint/format, project integrity, harness structure,
deep-research contracts (10/10), survey contracts (3/3), and wiki structural lint. These are build and
artifact checks, not research outcomes.

## Claim audit / 주장 감사

Classification follows the `academic-research` contract:
`ALIGNED`, `OVERSTATED`, `NOT_SUPPORTED_BY_PROVENANCE`, or `PROVENANCE_INSUFFICIENT`.

| Claim or planned contribution | Pre-gate class | Resolution required for Stage 3 | Post-resolution state |
| --- | --- | --- | --- |
| `C-METHOD-001`: symbolic validation can incrementally ground interactive-fiction generation | `ALIGNED` to S01, but source status is limited | Attribute to IVIE and label S01 preprint/forthcoming; do not treat it as TRACE-RPG evidence | `ALIGNED` |
| `C-METHOD-002`: role-sensitive scaffolding can trade stability against improvisation | `ALIGNED` to S02, preprint-only | Use as motivation with peer-reviewed NPC/player work S03, S21, S22; never as sole central evidence | `ALIGNED` |
| `C-DATA-001`: KNUDGE grounds branching dialogue in quest/entity specifications | `ALIGNED` | Cite the archival EMNLP 2024 record S03, not the 2022 arXiv year as publication year | `ALIGNED` |
| `C-AFFECT-001`: current VLM engagement inference shows a perception--understanding gap | `PROVENANCE_INSUFFICIENT` for a settled field-wide claim | Say “a recent preprint reports” and use it only to motivate non-authoritative affect; pair with S24--S25 | `ALIGNED`, preprint-scoped |
| `C-SYSTEM-001`: hard validity must be a commit gate while narrative/affect remain soft | `OVERSTATED` as a universal prescription | Recast as the TRACE-RPG design invariant: encoded hard predicates precede optional soft scoring | `ALIGNED` as proposed method |
| “TRACE-RPG is engine-neutral” | `PROVENANCE_INSUFFICIENT` | Say “engine-decoupled versioned bridge contract”; actual portability remains unproven until an engine adapter runs | `ALIGNED`, scope-limited |
| “The policy oracle is independently authored/reviewed” | `PROVENANCE_INSUFFICIENT` | Claim only that model-declared fields are checked against externally supplied canonical `ActionPolicy`; document authorship independence in the pilot manifest | `ALIGNED` after manifest evidence; otherwise `[NEEDS EVIDENCE]` |
| “TRACE-RPG guarantees valid game behavior” | `NOT_SUPPORTED_BY_PROVENANCE` | Replace with “enforces the encoded predicates for the tested transition domain”; state semantic incompleteness and policy-author error explicitly | `ALIGNED`, encoded-domain only |
| “The trace is tamper-proof/authenticated” | `NOT_SUPPORTED_BY_PROVENANCE` | Use “unkeyed content-integrity checksum plus semantic replay”; no signature, MAC, writer identity, or adversarial authenticity claim | `ALIGNED` |
| “Semantic replay detects corruption” | `OVERSTATED` without a mutation domain | Report only detection of each named, frozen mutation class and its exact denominator | `ALIGNED` after Stage 4 pilot |
| “Complete repair traces are semantically replayed” | `OVERSTATED` at this historical gate | Stage 4 now strictly parses and deterministically revalidates every recorded attempt and requires nonfinal attempts to be invalid; it still does not authenticate or re-execute the repair generator | `ALIGNED`, structured state-semantic replay only |
| “The experiment harness preserves every assigned failure” | `OVERSTATED` as a universal implementation claim | Scope to records admitted by the frozen assignment key and tested writer/adapter boundary; note cross-process locking is absent | `ALIGNED` after Stage 4 pilot |
| Temporal graph memory is implemented | `NOT_SUPPORTED_BY_PROVENANCE` | Remove from implemented contribution and place retrieval/memory ablations in future confirmatory work | `ALIGNED` as future protocol only |
| Affect adaptation is implemented/effective | `NOT_SUPPORTED_BY_PROVENANCE` | Remove “affect-adaptive” from the present title; keep affect as a future non-authoritative track | `ALIGNED` as future protocol only |
| A ten-model panel establishes controller generality | `NOT_SUPPORTED_BY_PROVENANCE` | Describe model matrix as a frozen research blueprint; no result language | `ALIGNED` as future protocol only |
| Player preference or naturalness improves | `NOT_SUPPORTED_BY_PROVENANCE` | Retain as future matched-validity human-study question requiring ethics approval and prospective power | `ALIGNED` as future hypothesis only |
| `C-RESULT-001`: gate reduces hard violations | `NOT_SUPPORTED_BY_PROVENANCE` | Keep `TODO-RESULT`; exclude from current empirical conclusion | unresolved hypothesis, non-blocking because no positive claim is made |
| `C-RESULT-002`: affect improves target tracking without validity regression | `NOT_SUPPORTED_BY_PROVENANCE` | Keep `TODO-RESULT`; provisional non-inferiority margin requires an independent rationale | unresolved hypothesis, non-blocking because no positive claim is made |
| `C-RESULT-003`: structured repair is more sample-efficient than blind retry | `NOT_SUPPORTED_BY_PROVENANCE` | Keep `TODO-RESULT`; deterministic repair existence is not comparative efficiency | unresolved hypothesis, non-blocking because no positive claim is made |
| `C-RESULT-004`: graph/event memory reduces contradictions | `NOT_SUPPORTED_BY_PROVENANCE` | Keep `TODO-RESULT`; the components and comparator are not implemented | unresolved hypothesis, non-blocking because no positive claim is made |
| `C-RESULT-005`: controller effect is cross-model consistent | `NOT_SUPPORTED_BY_PROVENANCE` | Keep `TODO-RESULT`; no live/recorded ten-model outcome exists | unresolved hypothesis, non-blocking because no positive claim is made |

## Metric and estimand corrections required / 필수 지표 수정

1. `valid_commit_rate` in `src/nesy_game/metrics.py` is not the registered episode-level
   `valid_episode_rate`; the paper must not treat them as synonyms.
2. `commit_rate`, symbolic fallback, and adapter failure are assigned-action-case measures, not quest
   completion or episode solvability.
3. `hard_violation_per_commit` becomes structurally zero under a sound gate. Proposed-candidate
   violations, symbolic rejections, unsafe committed actions, and valid completed episodes require
   separate denominators.
4. Provider-response latency is conditional on receipt of a response. The frozen 842.5 ms value is
   metadata for one historical record, not current p95 system latency.
5. The runner currently stops its local timer before validation/repair, so it is not an end-to-end
   latency measure.
6. Zero-denominator outcomes must render as `NA (n=0)` in paper tables, never as observed zero
   performance.
7. `tension_ccc`, live retrieval/memory, affect control, engine execution, energy, and human measures
   are protocol fields without executable measurements.
8. H1 requires an independent semantic outcome oracle. Using the intervention validator as the sole
   judge of its own validity effect would make the comparison partly tautological.
9. H2 currently lacks an explicit blind-retry implementation and per-repair-call token/latency
   accounting; one handcrafted repair path cannot support efficiency.
10. H5 promotes one model instance per access/scale profile, confounding model identity with stratum;
    the three instances can support exploratory instance-level directions, not stratum generalization.

## Allowed present-tense empirical claims / 현재 허용되는 실증 문장

- On revision `3958c09`, all 41 authored software tests passed in the declared local environment.
- The two-row frozen smoke fixture produced one valid commit and retained one recorded timeout as an
  adapter failure in the assigned-case denominator.
- The tested invalid, adapter-failure, and injected write-failure paths left the tested canonical state
  unchanged.
- The tested structured repair path terminated within `K=1` and committed after the repaired candidate
  passed the same validator.
- The named checksum, semantic-replay, linkage, and continuity counterexamples were rejected by their
  corresponding tested checks.

Every sentence must retain “tested,” “authored fixture,” or an equivalent domain boundary.

## Stage 4 pilot required before result promotion / 결과 승격 전 필수 파일럿

The final manuscript will not rely on the test count alone. Stage 4 must generate an immutable pilot
manifest and machine-derived tables for four designed experiments:

1. validator and state-isolation conformance across every implemented failure code;
2. rejection-only, unchanged blind retry, and structured repair on repairable/non-repairable fixtures;
3. checksum-only versus checksum-plus-semantic-replay fault injection;
4. adapter/schema/failure-accounting and exact assignment-manifest conformance.

Unique authored cases—not repeated deterministic seeds—form the descriptive denominators. The paper
will report raw counts and exact proportions without p-values or population confidence claims.

## Fail-closed conditions / fail-closed 조건

Stage 4 is blocked from promoting a pilot claim if any of the following occurs:

- the result table is manually transcribed rather than generated from frozen artifacts;
- an assignment lacks exactly one terminal record;
- a claimed invariant lacks a positive and/or counterexample fixture appropriate to its domain;
- a rehashed impossible transition passes semantic replay;
- an invalid or adapter-failure outcome mutates canonical state;
- English and Korean result statements differ in numerator, denominator, or scope;
- any `C-RESULT-001`--`005` marker is replaced by a number without the corresponding external study.
