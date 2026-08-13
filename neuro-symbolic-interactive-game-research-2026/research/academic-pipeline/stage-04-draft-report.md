# Stage 4 Draft Report / Stage 4 초안 보고서

Status: **SUPERSEDED HISTORICAL STAGE-4 SNAPSHOT — APPROVAL RECORDED 2026-08-13**

Snapshot date: 2026-08-12

Evidence class: deterministic local offline pilot engineering evidence

Amendment: **post-Stage-8 rerun**. The current packet preserves the Stage-4 study scope while
moving `candidate_contract_strictness` from an accepted open sentinel to a closed negative
regression after both proposal and replay parsers began rejecting unknown top-level keys.

Current downstream status: **Stage 4.5's original pass was superseded; Stage 5 passed; Stage 6 was
accepted and actioned; Stages 8 and 9 executed; Stage 10 remains pending.** Statements below about
awaiting approval, six-page parity, absent engine execution, and unexecuted downstream gates describe
the original Stage-4 snapshot, not the current manuscript or game evidence.

## Original Stage-4 decision / 원래 Stage-4 판정 (historical)

Stage 4 produced a complete bilingual IEEE-format draft, machine-generated pilot result fragments,
and a shared 36-record reference database. The English and Korean PDFs are each six pages. The
empirical center remains a deterministic conformance pilot over authored offline fixtures; it is not
a live-model evaluation or a user study. The stage therefore remains
**AWAITING_USER_APPROVAL** and no Stage 4.5 or Stage 5 review result may be inferred from this packet.

Stage 4에서는 영문·국문 IEEE 형식 초안, 기계 생성 파일럿 결과 조각, 36개 레코드의 공유
참고문헌 데이터베이스를 완성했다. 영문과 국문 PDF는 각각 6쪽이다. 실증의 중심은 작성된
오프라인 fixture에 대한 결정론적 적합성 파일럿이며, 라이브 모델 평가나 사용자 연구가
아니다. 따라서 현재 상태는 **AWAITING_USER_APPROVAL**이고, 이 패킷으로부터 Stage 4.5 또는
Stage 5 검토 결과를 추론해서는 안 된다.

## Delivered artifacts / 산출물

| Artifact | Location | Verified snapshot |
| --- | --- | --- |
| English IEEE manuscript and PDF | `paper/latex/en/main.tex`, `paper/latex/en/main.pdf` | 6-page PDF |
| Korean IEEE companion and PDF | `paper/latex/ko/main.tex`, `paper/latex/ko/main.pdf` | 6-page PDF |
| Shared bibliography | `paper/latex/references.bib` | 36 reference records |
| Reproducible PDF build | `paper/latex/Makefile` | Regenerates SVG/PNG figures, both PDFs, and page/font/log gates |
| Machine-generated bilingual result inputs | `paper/latex/generated/pilot_results_{en,ko}.tex`, `pilot_tables_{en,ko}.tex` | Generated from the frozen pilot artifacts |
| Pilot evidence bundle | `research/academic-pipeline/stage-04-pilot/` | JSON, CSV, Markdown, and TeX views plus SHA-256 manifest |
| Published-row provenance manifest | `research/academic-pipeline/stage-04-pilot/pilot-assignment-manifest.json` | 64 exact row keys and provenance records |

The PDFs, result inputs, source code, and pilot artifacts are reported here as existing evidence; this
report does not modify them.

## Exact pilot observations / 정확한 파일럿 관찰값

| Evaluation slice | Exact observation | Admissible interpretation | Prohibited extrapolation |
| --- | --- | --- | --- |
| Gate conformance | 13/13 fixture expectations matched; all 12 implemented validator codes were observed | The tested gate returned the expected outcome for one valid control and the isolated authored code fixtures | Exhaustive semantic validity, population error rate, or general game safety |
| Rejection-only arm | 0/2 repair successes and 0/2 commits among two initially invalid designed cases | With repair budget 0, neither case committed | Comparative model efficacy or a population failure probability |
| Unchanged-retry arm | 0/2 repair successes and 0/2 commits | Repeating the unchanged invalid candidate did not produce a commit in these two fixtures | A general claim that retry cannot work |
| Structured-repair arm | 1/2 repair successes and 1/2 commits | One authored case committed after the repaired candidate passed the same deterministic validator; the other did not | Superiority, sample efficiency, or stability across models and tasks |
| Open boundary sentinels | 2/2 were accepted at the encoded layer; 0/2 were labelled safety passes | The fixtures expose unparsed narrative disclosure and an omitted candidate-and-policy object requirement | Semantic safety or complete policy coverage |
| Closed candidate-contract regression | 1/1 passed: both parsers specifically rejected a complete 12-field candidate carrying one unknown key | The Stage-8 shared key contract stayed closed in this authored negative fixture | Semantic safety, exhaustive schema robustness, or a population error rate |
| Detectable integrity faults | 10/10 named injected faults were rejected by their designated operations | Rejection is supported only for the frozen checksum, replay, type, control-flow, linkage, continuity, and rollback mutations represented in the bundle; stable detector-layer attribution was not tested | Tamper-proofing, authentication, adversarial completeness, exact detector attribution, or detection of unspecified faults |
| Known repair-provenance boundary | 1/1 designed boundary remained replay-accepted, as expected | State-semantic replay accepted a rehashed substitution of one invalid precursor for another before the same recorded valid repair because it does not authenticate or re-execute the repair generator | Provenance verification for repair generation |
| Adapter accounting | 1 commit, 1 symbolic fallback, and 5 adapter failures across 7 assigned cases | Every designed adapter case entered one of the three reported terminal accounting categories | Live provider reliability, model quality, or latency distribution |
| Assignment-accounting guards | 3/3 injected manifest faults detected | Duplicate observed record, duplicate expected assignment, and missing assignment were rejected in the authored guards | Concurrency safety or exhaustive accounting correctness |
| Frozen published-row set | 64 row keys: 43 executed fixture rows and 21 aggregate rows | The manifest fixes the expected provenance of every released pilot row, including the closed-boundary regression and fault-specific input specifications | 64 independent stochastic trials, 64 model calls, or a statistical sample |

All ratios above use authored deterministic cases as descriptive denominators. They are not estimates
of a deployment population, and no confidence interval, significance test, or causal comparison is
claimed. In particular, the repair-arm values are pilot feasibility observations, not evidence that
structured repair is generally better than rejection or unchanged retry.

위 비율의 분모는 모두 작성된 결정론적 사례이다. 배포 모집단의 추정치가 아니며 신뢰구간,
유의성 검정, 인과 비교를 주장하지 않는다. 특히 repair arm 결과는 파일럿 구현 가능성의
관찰값일 뿐, structured repair가 rejection 또는 unchanged retry보다 일반적으로 우월하다는
근거가 아니다.

## Integrity and replay boundary / 무결성 및 재생 경계

The artifact manifest uses unkeyed SHA-256 content checksums. These checksums support accidental or
specified mutation detection when recomputed, but they are not digital signatures, message
authentication codes, writer identities, or adversarial authenticity guarantees. Semantic replay
checks the declared state transition and recorded validation semantics. It does not establish the
provenance of the generator that produced a repair candidate. The replay-accepted 1/1 boundary case
is consequently a documented limitation and a successful boundary sentinel, not a safety pass.

산출물 manifest의 SHA-256은 키가 없는 콘텐츠 checksum이다. 재계산 시 우발적 변경이나
명시된 변이를 탐지할 수 있으나 디지털 서명, MAC, 작성자 신원, 적대적 진본성 보장은
아니다. semantic replay는 선언된 상태 전이와 기록된 validation semantics를 검사하지만,
repair candidate를 만든 generator의 provenance를 증명하지 않는다. 따라서 replay가 수용한
1/1 경계 사례는 문서화된 한계이자 의도대로 작동한 boundary sentinel이며 안전성 통과가
아니다.

## Manuscript evidence boundary / 원고 근거 경계

The present manuscripts may claim only implementation existence and tested behavior for declared
structured fields on the designed offline fixtures. They contain no completed evidence from:

- live language-model calls or a ten-model comparison;
- human participants or player-preference evaluation;
- affect sensing or affect-adaptive control;
- retrieval-augmented generation or knowledge-graph retrieval;
- temporal or long-horizon memory experiments; or
- execution inside a commercial or open-source game engine.

Consequently, model generality, narrative quality, player experience, affect effectiveness, retrieval
benefit, memory consistency, engine portability, and production robustness remain outside the current
results. The bilingual drafts must retain the same denominators and limitations when revised.

현재 원고가 주장할 수 있는 범위는 선언된 structured field와 설계된 offline fixture에서
확인된 구현 존재 및 테스트 동작뿐이다. 라이브 모델, 인간 참가자, affect, RAG/graph
retrieval, temporal memory, game-engine 실행에 관한 완료된 실험 근거는 없다. 따라서 모델
일반화, 서사 품질, 플레이어 경험, affect 효과, retrieval 이득, memory 일관성, engine
portability, production robustness는 현재 결과의 범위 밖이다.

## Checkpoint / 승인 체크포인트

| Stage | State | Meaning |
| --- | --- | --- |
| 4 | **AWAITING_USER_APPROVAL** | Draft, pilot tables, bibliography, and bilingual PDFs are assembled for review |
| 4.5 | **NOT_EXECUTED** | No post-draft review decision is recorded |
| 5 | **NOT_EXECUTED** | No downstream citation-integrity/release decision is recorded |

User approval at this checkpoint would approve the Stage 4 draft packet as the next review baseline;
it would not convert the pilot into live-model, human-study, or engine evidence and would not itself
execute Stage 4.5 or Stage 5.
