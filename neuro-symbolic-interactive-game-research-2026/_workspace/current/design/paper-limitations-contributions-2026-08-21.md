# Paper limitations & contributions deep-research findings / 논문 한계·기여 심층 조사 결과

```yaml
artifact_id: DR-PAPER-LIMCON-001
run_id: 20260821-iteration-1-wave-1
owner: DeepResearch
retrieval_date: 2026-08-21
version: 1.0.0
scope: >
  Bounded web deep-research pass over four preregistered stages: (1) counterexample-guided
  repair precedent, (2) neuro-symbolic game-action validation 2025-2026 state, (3) limitations
  audit, (4) contributions sharpening. Consumers: RepairMethod (paper tex owner this wave),
  future paper agents. This document edits NO paper/tex/wiki/game file.
evidence_levels: >
  Per llm-wiki/wiki/concepts/evidence-and-claim-status.md: verified-primary,
  verified-scope-limited, design-assumption, thin-evidence, TODO-RESULT, verified-empirical.
new_records:
  - research/deep-research/results/method-self-refine-2303-17651.json
  - research/deep-research/results/method-self-debug-2304-05128.json
  - research/deep-research/results/method-autospec-cegis-2606-24245.json
  - research/deep-research/results/method-worldstate-transformations-2605-24719.json
validator: "uv run python scripts/validate_deep_research.py ... -> Deep-research contract: 14/14 records valid (2026-08-21)"
```

Terminology contract (aligned with RepairMethod, 2026-08-21): arm identifiers are
`rejection_only` (budget 0), `unchanged_retry` (blind retry, budget 1), `guided_repair`
(NEW, strategy `counterexample_guided` = ρ(a,E), budget 1), and `structured_repair`
(existing state-reading oracle, strategy `policy_restore`, budget 1). Fixture repairability
classes: **guided-repairable** vs **guided-irreparable** (error payload insufficient without
state knowledge). In prose: guided ρ vs blind unchanged-retry vs state-reading oracle; the
oracle stays the upper bound.

---

## Stage 1 — Counterexample-guided repair precedent / 반례 유도 수리 선행 연구

**[FINDING] S1-F1 — CEGIS is the canonical counterexample-consuming repair loop, and its evidence class is solver-verified synthesis success, not operator-level fixture counts.**
Counterexample-guided inductive synthesis originates in Solar-Lezama et al.'s combinatorial
sketching work (ASPLOS 2006; formalized in the 2008 Berkeley PhD thesis "Program Synthesis by
Sketching"). The loop alternates a learner proposing a candidate against a verifier that
returns a concrete counterexample, which is added to the constraint set for the next
candidate. TRACE-RPG's `guided_repair` arm instantiates exactly this shape — validator as
verifier, structured error set E as the counterexample, proposer callback as learner — but in
a domain (game-action commit gates) and an evidence class (deterministic fixture exact counts
with a frozen oracle upper bound) that the CEGIS literature does not cover.
Source: https://people.csail.mit.edu/asolar/ (author page) and ASPLOS 2006 "Combinatorial
Sketching for Finite Programs"; corroborated via multi-source web search 2026-08-21.
Retrieved: 2026-08-21. Evidence level: verified-primary (concept/venue), verified-scope-limited
(no game-domain coverage claim tested beyond search absence).

**[FINDING] S1-F2 — Self-Refine is the canonical LLM self-repair loop; its feedback is model-generated language and its measures are live-model task gains.**
Madaan et al., "Self-Refine: Iterative Refinement with Self-Feedback" (arXiv:2303.17651,
submitted 2023-03-30, CC BY 4.0): one LLM alternates generator/feedback/refiner roles, no
training, evaluated on 7 tasks with GPT-3.5/ChatGPT/GPT-4, ~20% absolute average improvement
by human/automatic preference. The feedback channel is unstructured natural language produced
by the same untrusted model. TRACE-RPG's repair feedback is instead an externally computed,
typed error set from a deterministic validator — a categorically different trust boundary.
Source: https://arxiv.org/abs/2303.17651. Retrieved: 2026-08-21. Evidence level:
verified-primary.

**[FINDING] S1-F3 — Self-Debugging is the closest structural analogue: it consumes an external execution signal, but over trusted full-program runtimes with benchmark-accuracy evidence.**
Chen et al., "Teaching Large Language Models to Self-Debug" (arXiv:2304.05128, submitted
2023-04-11, CC BY 4.0): the model revises code using execution results and its own code
explanation; +2–3% Spider overall (+9% hardest), up to +12% TransCoder/MBPP, with strong
sample-efficiency claims. The error signal comes from executing the full candidate in a
trusted runtime; a commit gate exposes only a bounded typed error payload before any
execution, and TRACE-RPG measures the operator (not the model) on deterministic fixtures.
Source: https://arxiv.org/abs/2304.05128. Retrieved: 2026-08-21. Evidence level:
verified-primary.

**[FINDING] S1-F4 — The self-correction literature itself argues external structured feedback is necessary: intrinsic self-correction without it can degrade performance.**
Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet" (arXiv:2310.01798,
submitted 2023-10-03): LLMs struggle to correct reasoning without external feedback and
sometimes get worse after self-correction. CRITIC (Gou et al., arXiv:2305.11738) reaches the
complementary positive conclusion: tool-supplied external feedback is what makes LLM
self-correction work. Both directly motivate TRACE-RPG's design choice that ρ consumes the
validator's error set rather than the model's own judgment, and motivate the blind
`unchanged_retry` arm as the honest no-information baseline.
Sources: https://arxiv.org/abs/2310.01798 ; https://arxiv.org/abs/2305.11738.
Retrieved: 2026-08-21. Evidence level: verified-primary.

**[FINDING] S1-F5 — 2026 CEGIS×LLM crossovers exist in hardware repair and agent-safety rules, and neither touches game-state commit gates or operator-level fixture comparison.**
(a) Tran, "Open-Source LLM-Driven Formal Verification: A Multi-Agent Pipeline for RTL Repair"
(arXiv:2607.28877, 2026-07-30) feeds formal-backend counterexamples (Yosys/SymbiYosys/Z3) to
an LLM until k-induction proves the RTL correct — counterexample-guided candidate repair, but
in hardware with proof-based evidence. (b) Ma et al., "AutoSpec: Safety Rule Evolution for LLM
Agents via Inductive Logic Programming" (arXiv:2606.24245, 2026-06-23) runs CEGIS over
annotated agent traces to repair the RULES (F1 0.98/0.93), not the candidate. Bracketing:
repair-the-candidate (RTL, code) and repair-the-rules (AutoSpec) both exist; a deterministic
fixture-level comparison of a candidate-repair operator against blind and oracle arms inside a
game-action commit gate exists in neither.
Sources: https://arxiv.org/abs/2607.28877 ; https://arxiv.org/abs/2606.24245.
Retrieved: 2026-08-21. Evidence level: verified-primary.

**Stage 1 synthesis (2 lines):** Counterexample-consuming repair is well precedented (CEGIS
2006 → LLM self-repair loops 2023 → 2026 hardware/agent-safety crossovers), and the
literature's own conclusion is that external structured feedback is the load-bearing
ingredient. No prior work performs a deterministic, model-free, fixture-level comparison of a
candidate-repair operator ρ(a,E) against blind-retry and state-reading-oracle arms inside a
transactional game-state commit gate — that comparison is a real, defensible novelty slot for
this paper, provided its evidence is framed as operator conformance, not live-model efficacy.

---

## Stage 2 — Neuro-symbolic game-action validation, 2025–2026 state / 신경-기호 게임 행동 검증 최신 동향

**[FINDING] S2-F1 — One genuinely new 2026 system in the IVIE lineage must be added to related work: World-State Transformations (Góngora et al.).**
Góngora, Chiruzzo, Méndez, Gervás, "World-State Transformations for Neuro-symbolic
Interactive Storytelling" (arXiv:2605.24719, submitted 2026-05-23, CC BY-NC-ND 4.0; PAYADOR
lineage, overlapping authorship with IVIE): LLMs (Llama 3 70B, Gemini 1.5 Flash) predict which
pre-programmed world-state transformations to trigger from free-text input; an exploratory
N=8, two-scenario, bilingual (EN/ES) player study suggests transformations preserve
world-state consistency while supporting expressive input. It restricts what an LLM may
trigger; it does not gate, audit, replay, or repair candidate transitions, and it reports no
repair-operator or trace-integrity evidence. Recommended placement: Related Work §II-C beside
IVIE and PANGeA, with the same "validity is only validity for the encoded predicates" framing.
Source: https://arxiv.org/abs/2605.24719. Retrieved: 2026-08-21. Evidence level:
verified-primary (paper identity/claims), verified-scope-limited (N=8 exploratory study).

**[FINDING] S2-F2 — Targeted arXiv queries for game-domain action-validation/repair work return nothing beyond the already-cited comparators; the gap statement holds.**
arXiv API queries on 2026-08-21 — `"symbolic validation" AND cat:cs.AI AND game` (0 results),
`"action validation" AND LLM AND game` (0 results), `"interactive fiction" AND repair AND
validation` (0 results), `ti:"interactive storytelling" AND "neuro-symbolic"` (1 result:
2605.24719 above). IVIE (arXiv:2606.13348, ICCC'26, CC BY-NC-ND 4.0) and PANGeA
(S42_buongiorno2024pangea) remain the two direct game-specific comparators already cited.
Absence of results is evidence of search absence, not proof of nonexistence; queries and dates
are recorded here for the submission-time recheck the paper already promises for S23.
Sources: http://export.arxiv.org/api/query (queries above) ;
https://arxiv.org/abs/2606.13348. Retrieved: 2026-08-21. Evidence level:
verified-scope-limited (bounded negative search).

**[FINDING] S2-F3 — Secondary/industry sources describe "commit gate" symbolic validators as an emerging 2026 pattern, but none constitutes citable archival precedent.**
A 2026 web-search pass surfaces industry/aggregator prose (e.g., consultancy whitepapers,
Medium engineering posts) describing LLM-subordinate symbolic validators for game state,
grammar-constrained action formats, and per-step verification as current practice. None of the
surfaced items is a peer-reviewed or archival source that could displace the paper's gap
claim, and none reports audit-linked records, semantic replay, or repair-arm comparison. Treat
as background pressure ("the pattern is in the air") justifying the paper's positioning, not
as citations.
Source: multi-engine web search, queries recorded in run log. Retrieved: 2026-08-21.
Evidence level: thin-evidence (non-archival secondary prose).

**Stage 2 synthesis (2 lines):** Exactly one new citable 2026 system was found — World-State
Transformations (arXiv:2605.24719), same research lineage as IVIE — and it belongs in Related
Work §II-C; it selects among authored transformations but has no transactional gate, audit
evidence, or repair comparison. All targeted searches for game-domain candidate-repair or
commit-gate evidence come back empty, so the paper's research-gap statement survives this pass
unchanged.

---

## Stage 3 — Limitations audit / 한계 감사

Sharpest honest list, drawn from the paper's own Threats/Discussion sections plus Stage 1–2
findings. Each item is written to be pasted (or lightly edited) into the paper; none is
hedging boilerplate. Evidence level for all items: verified-primary against
`paper/latex/en/main.tex` as of 2026-08-21, cross-checked with the abstract and §7–§8.

**[FINDING] S3-F1 — Nine-item limitation list (recommended).**

1. **Semantic incompleteness of encoded fields.** The gate rejects only what its declared
   fields and predicates represent; a natural-language implication omitted from structured
   candidate fields passes untested, so an encoded check can never discover the semantics its
   authors failed to encode.
2. **Single authored world state.** Every fixture count is conditioned on one hand-authored
   world (Sealed Lighthouse) and its policy; nothing here estimates behavior across worlds,
   policies, genres, or scale, and world-count generalization is untested by construction.
3. **Oracle-vs-guided repair evidence boundary.** The prior pilot's reference callback read
   authoritative state and is an upper bound only; the new `guided_repair` arm ρ(a,E) is
   evaluated on deterministic designed fixtures, so its counts certify operator conformance on
   guided-repairable/guided-irreparable classes — not repair quality of any live model, and
   not closure of the oracle gap outside those fixtures.
4. **No live model transport.** All proposer and adapter behavior is recorded or synthetic;
   there are no live model calls, no live Python–Godot authorization round trips, and adapter
   telemetry values are schema-pinned constants, so no latency, cost, or capability claim
   about any provider or engine transport is supported.
5. **No human data.** No participants, playtests, or affect measurements exist; nothing is
   known about player experience, legibility, or fun, and the diegetic ledger framing is a
   design hypothesis, not an evaluated outcome.
6. **Unkeyed hashes are integrity checks, not authentication.** SHA-256 content checksums
   detect accidental or tested corruption only; an actor who can rewrite content can rewrite
   checksums, so no writer-identity, tamper-resistance, or adversarial-security property is
   established.
7. **Single-process writer assumption.** Terminal-record consistency assumes one process owns
   the result files; concurrent-writer safety is neither implemented nor tested, and replay
   guarantees do not survive multi-writer corruption scenarios.
8. **Engine portability is asserted by interface, not demonstrated.** The versioned bridge
   decouples interfaces, but engine evidence is one scripted Godot 4.7.1 fixture whose
   startup-dominated frame samples (98.8–116.7 ms worst deltas) miss the 16.7 ms budget; no
   commercial-engine port or representative real-time performance measurement exists.
9. **Designed fixtures do not generalize.** Fixture cases are purposively authored
   conformance probes, not samples from any model or game population; exact-count agreement
   supports implementation-conformance claims only, and attaching population or safety-rate
   inference to them would be a category error.

Rationale notes: items 1–2, 4–9 restate and sharpen boundaries the paper already
acknowledges (§Abstract, §7, §8); item 3 is updated for this wave's guided-repair work so the
limitation moves from "oracle-only, no deployable method" to the honest post-implementation
boundary "guided operator evidence is fixture-level conformance."
Sources: repo `paper/latex/en/main.tex` (§Abstract, §7 Discussion, §8 Threats) at working-tree
state 2026-08-21; external corroboration for item 3's framing:
https://arxiv.org/abs/2310.01798 (external feedback necessity). Retrieved: 2026-08-21.

---

## Stage 4 — Contributions sharpening / 기여 정제

**[FINDING] S4-F1 — Rewritten contribution bullets (4 existing + 1 new), each naming artifact, mechanism, and evidence class.**
Current bullets (Introduction §I, items 1–4) name artifacts but not mechanisms or evidence
classes. Recommended replacements below; evidence level: verified-primary against
`paper/latex/en/main.tex` §I and §5–§6 structure as of 2026-08-21, with item 5 matching the
RepairMethod arm contract (`guided_repair`, strategy `counterexample_guided`, vs
`unchanged_retry` and `structured_repair`).
Sources: repo `paper/latex/en/main.tex` (§I contributions enumerate) at working-tree state
2026-08-21; novelty-slot support: https://arxiv.org/abs/2606.24245 and
https://arxiv.org/abs/2607.28877 (nearest 2026 CEGIS×LLM work, neither in games).
Retrieved: 2026-08-21.

Recommended EN bullets — see "Recommended paper text" below (kept in one place to avoid
divergent copies).

**Stage 3+4 synthesis (2 lines each):**
Stage 3: The paper's own threat framing is already unusually honest; the audit's main upgrades
are (a) converting the oracle-only repair caveat into the sharper post-guided-repair evidence
boundary and (b) stating the unkeyed-hash and single-writer assumptions as first-class
limitations rather than discussion asides.
Stage 4: Each contribution now names artifact + mechanism + evidence class so a reviewer can
map every claim to a frozen artifact; the new fifth bullet claims exactly what Stage 1 shows
no one else has — a deterministic guided-vs-blind-vs-oracle operator comparison inside a
game-action commit gate — and nothing more.

---

## Recommended paper text / 권장 논문 문안

### (a) EN limitation bullets (drop-in for §Threats/Discussion)

- **L1 (encoded-semantics boundary).** Validation rejects only what declared fields and
  predicates represent; natural-language implications omitted from structured fields pass
  untested. An encoded check cannot discover semantics its authors did not encode.
- **L2 (single world).** All counts are conditioned on one authored world state and policy;
  cross-world, cross-policy, and scale generalization are untested by construction.
- **L3 (repair evidence boundary).** The state-reading reference callback remains an oracle
  upper bound; the counterexample-guided operator ρ(a,E) is evidenced only by deterministic
  fixture counts over guided-repairable and guided-irreparable classes. Neither result
  measures live-model repair quality.
- **L4 (no live transport).** Proposers and adapters are recorded or synthetic; no live model
  calls or live engine authorization round trips exist, and adapter telemetry is schema-pinned
  constants, not measurement.
- **L5 (no human data).** No participants or affect measurements exist; player-facing
  legibility of the commit ritual is a design hypothesis, not an evaluated outcome.
- **L6 (integrity, not authentication).** Unkeyed SHA-256 checksums detect accidental or
  tested corruption; they provide no writer identity or adversarial tamper resistance.
- **L7 (single-process writer).** Record consistency assumes single-process file ownership;
  concurrent-writer safety is neither implemented nor tested.
- **L8 (engine portability undemonstrated).** The versioned bridge decouples interfaces, but
  engine evidence is one scripted Godot fixture with startup-dominated frame samples that miss
  the 16.7 ms budget; no commercial-engine or real-time result exists.
- **L9 (designed fixtures, no population inference).** Fixtures are purposively authored
  conformance probes; exact counts support implementation conformance only and carry no
  population or safety-rate inference.

### (b) EN contribution bullets (drop-in for §I enumerate)

1. **Versioned trust-boundary contracts** — for canonical state, externally supplied action
   policy, candidate event, experiment record, and game bridge — enforced by a type-strict
   parser that rejects ambiguous known-field types and unknown top-level candidate keys;
   evidenced by deterministic parser-contract fixtures, including proposal/replay rejection
   parity on a prespecified unknown-key negative.
2. **A validate–repair–commit controller** whose seven checks across six state-relative families decide every
   admitted transition, with bounded repair budget, unchanged deterministic fallback, and
   defensive pre-commit revalidation; evidenced by exact-count validator/state-isolation and
   repair-control-flow fixtures over a single authored world.
3. **An audit-evidence layer** binding terminal records to unkeyed SHA-256 content checksums,
   state-semantic replay that recomputes the recorded transition, and episode-continuity
   validation; evidenced by prespecified fault-injection fixtures in which every named
   corruption is rejected by its designated check operation.
4. **An offline conformance harness** with type-strict known-field adapter boundaries, frozen
   assignment keys, distinct terminal failure classes, and assignment-complete accounting that
   retains controller-failure rows without proposal traces; evidenced by manifest-violation
   fixtures and a frozen release packet with recomputable hashes.
5. **A counterexample-guided repair operator and fixture battery** — ρ(a,E) consumes only the
   structured error set and the prior candidate, never authoritative state, and is compared
   against a blind unchanged-retry arm and the state-reading oracle upper bound on an expanded
   deterministic fixture set partitioned into guided-repairable and guided-irreparable
   classes; evidenced by exact per-arm commit/fallback counts under frozen manifests.

### (c) KO translations / 한국어 번역

한계 (L1–L9):

- **L1 (인코딩된 의미의 경계).** 검증은 선언된 필드와 술어가 표현하는 것만 거부한다. 구조화
  필드에서 누락된 자연어 함의는 검사 없이 통과하며, 인코딩된 검사는 저자가 인코딩하지 않은
  의미를 발견할 수 없다.
- **L2 (단일 세계).** 모든 수치는 하나의 저작된 세계 상태와 정책에 조건화되어 있다. 세계 간,
  정책 간, 규모 확장 일반화는 구성상 검증되지 않았다.
- **L3 (수리 증거 경계).** 상태를 읽는 참조 콜백은 오라클 상한으로 남는다. 반례 유도 수리
  연산자 ρ(a,E)의 증거는 guided-repairable/guided-irreparable 클래스에 대한 결정론적 픽스처
  수치뿐이며, 어느 결과도 라이브 모델의 수리 품질을 측정하지 않는다.
- **L4 (라이브 전송 없음).** 제안자와 어댑터는 기록되었거나 합성이다. 라이브 모델 호출도,
  라이브 엔진 승인 왕복도 없으며, 어댑터 텔레메트리는 스키마로 고정된 상수이지 측정이 아니다.
- **L5 (인간 데이터 없음).** 참가자나 정서 측정이 없다. 커밋 의식의 플레이어 체감 가독성은
  설계 가설이지 평가된 결과가 아니다.
- **L6 (무결성이지 인증이 아님).** 키 없는 SHA-256 체크섬은 우발적·시험된 손상만 탐지한다.
  작성자 신원이나 적대적 변조 저항성은 제공하지 않는다.
- **L7 (단일 프로세스 기록자).** 기록 일관성은 단일 프로세스의 파일 소유를 가정한다. 동시
  기록자 안전성은 구현되지도 검증되지도 않았다.
- **L8 (엔진 이식성 미입증).** 버전화된 브리지는 인터페이스를 분리할 뿐이며, 엔진 증거는 시작
  구간이 지배하는 프레임 샘플이 16.7 ms 예산을 초과하는 단일 스크립트 Godot 픽스처가 전부다.
  상용 엔진 이식이나 실시간 결과는 없다.
- **L9 (설계된 픽스처, 모집단 추론 없음).** 픽스처는 목적적으로 저작된 적합성 프로브다. 정확
  수치는 구현 적합성만 뒷받침하며 모집단·안전율 추론을 담지 않는다.

기여 (1–5):

1. **버전화된 신뢰 경계 계약** — 정본 상태, 외부 제공 행동 정책, 후보 이벤트, 실험 기록, 게임
   브리지 계약을 타입 엄격 파서가 강제하며, 모호한 기지 필드 타입과 미지의 최상위 후보 키를
   거부한다. 증거: 사전 지정된 미지-키 부정 사례에 대한 제안/재생 거부 동등성을 포함한
   결정론적 파서 계약 픽스처.
2. **검증–수리–커밋 컨트롤러** — 여섯 상태 상대 계열에 걸친 검사 7개가 허용되는 모든 전이를 결정하고,
   유계 수리 예산, 불변 결정론적 폴백, 커밋 직전 방어적 재검증을 갖춘다. 증거: 단일 저작
   세계에 대한 정확 수치의 검증기/상태 격리 및 수리 제어 흐름 픽스처.
3. **감사 증거 계층** — 종단 기록을 키 없는 SHA-256 콘텐츠 체크섬에 결속하고, 기록된 전이를
   재계산하는 상태 의미 재생과 에피소드 연속성 검증을 수행한다. 증거: 명명된 모든 손상이
   지정된 검사 연산에 의해 거부되는 사전 지정 결함 주입 픽스처.
4. **오프라인 적합성 하네스** — 타입 엄격 기지 필드 어댑터 경계, 동결된 할당 키, 구분되는
   종단 실패 클래스, 제안 추적 없는 컨트롤러 실패 행까지 보존하는 할당 완전 회계를 갖춘다.
   증거: 매니페스트 위반 픽스처와 재계산 가능한 해시를 포함한 동결 릴리스 패킷.
5. **반례 유도 수리 연산자와 픽스처 배터리** — ρ(a,E)는 구조화된 오류 집합과 직전 후보만을
   소비하며 정본 상태는 결코 읽지 않는다. guided-repairable/guided-irreparable 클래스로 분할된
   확장 결정론적 픽스처 집합에서 블라인드 unchanged-retry 암과 상태를 읽는 오라클 상한과
   비교된다. 증거: 동결 매니페스트 하의 암별 정확 커밋/폴백 수치.

### (d) New BibTeX entries for `paper/latex/references.bib` (≤3, verified metadata)

Keys follow the existing `SNN_` house pattern; RepairMethod assigns final numbers. All
identities verified 2026-08-21 against the arXiv API abstract pages (arXiv entries) or
multi-source venue corroboration (ASPLOS entry). Author lists are exact.

```bibtex
@inproceedings{S43_solarlezama2006sketching,
  author    = {Solar-Lezama, Armando and Tancau, Liviu and Bod{\'i}k, Rastislav and Seshia, Sanjit and Saraswat, Vijay},
  title     = {Combinatorial Sketching for Finite Programs},
  booktitle = {Proceedings of the 12th International Conference on Architectural Support for Programming Languages and Operating Systems (ASPLOS XII)},
  publisher = {ACM},
  year      = {2006},
  note      = {Origin of counterexample-guided inductive synthesis (CEGIS); page range to be confirmed against the ACM DL at camera-ready}
}

@misc{S44_gongora2026worldstate,
  author        = {G{\'o}ngora, Santiago and Chiruzzo, Luis and M{\'e}ndez, Gonzalo and Gerv{\'a}s, Pablo},
  title         = {World-State Transformations for Neuro-symbolic Interactive Storytelling},
  year          = {2026},
  eprint        = {2605.24719},
  archiveprefix = {arXiv},
  url           = {https://arxiv.org/abs/2605.24719},
  note          = {Preprint; no archival venue or publisher DOI verified as of 2026-08-21}
}

@misc{S45_madaan2023selfrefine,
  author        = {Madaan, Aman and Tandon, Niket and Gupta, Prakhar and Hallinan, Skyler and Gao, Luyu and Wiegreffe, Sarah and Alon, Uri and Dziri, Nouha and Prabhumoye, Shrimai and Yang, Yiming and Gupta, Shashank and Majumder, Bodhisattwa Prasad and Hermann, Katherine and Welleck, Sean and Yazdanbakhsh, Amir and Clark, Peter},
  title         = {Self-Refine: Iterative Refinement with Self-Feedback},
  year          = {2023},
  eprint        = {2303.17651},
  archiveprefix = {arXiv},
  url           = {https://arxiv.org/abs/2303.17651},
  note          = {Preprint; commonly indexed as NeurIPS 2023 but proceedings identity not re-verified as of 2026-08-21}
}
```

Verified alternates (full identity confirmed, use only if the argument needs them; do not
exceed the paper's citation budget): Chen, Lin, Sch{\"a}rli, Zhou, "Teaching Large Language
Models to Self-Debug", arXiv:2304.05128 (2023); Huang, Chen, Mishra, Zheng, Yu, Song, Zhou,
"Large Language Models Cannot Self-Correct Reasoning Yet", arXiv:2310.01798 (2023); Gou,
Shao, Gong, Shen, Yang, Duan, Chen, "CRITIC: Large Language Models Can Self-Correct with
Tool-Interactive Critiquing", arXiv:2305.11738 (2023); Ma, Wang, Ji, Zhou, Xue, Li, Wang,
Zhang, "AutoSpec: Safety Rule Evolution for LLM Agents via Inductive Logic Programming",
arXiv:2606.24245 (2026); Tran, "Open-Source LLM-Driven Formal Verification: A Multi-Agent
Pipeline for RTL Repair", arXiv:2607.28877 (2026).

### Recommended related-work sentence for arXiv:2605.24719 (EN)

> A 2026 system in the same lineage restricts LLMs to selecting authored world-state
> transformations and reports an exploratory eight-participant study of player expression
> \cite{S44_gongora2026worldstate}; it maintains consistency by construction but provides no
> transactional gate, audit-linked records, or repair-operator evidence.

---

## Run log / 실행 기록

- Queries (arXiv API, 2026-08-21): `all:"counterexample-guided" AND all:"language model"`
  (8 hits, 2 relevant 2026); `all:"symbolic validation" AND cat:cs.AI AND all:game` (0);
  `ti:"interactive storytelling" AND all:"neuro-symbolic"` (1); `all:"action validation" AND
  all:LLM AND all:game` (0); `all:"interactive fiction" AND all:repair AND all:validation` (0).
- Web searches: CEGIS provenance, Self-Refine metadata, Self-Debug metadata, 2026
  neuro-symbolic game-action validation landscape (secondary-only results).
- Primary pages read: arXiv abs 2303.17651, 2304.05128, 2310.01798, 2305.11738, 2605.24719,
  2606.24245, 2607.28877; repo captures for 2606.13348 (IVIE), 2510.25820 (scaffolded play).
- New records validated: `uv run python scripts/validate_deep_research.py --fields
  research/deep-research/fields.yaml --dir research/deep-research/results --quiet` →
  `Deep-research contract: 14/14 records valid`.
- Files NOT touched (non-goals): `paper/latex/**` (RepairMethod owns), `llm-wiki/wiki/**`,
  all game files.
