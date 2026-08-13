# Academic Research Pipeline / 학술 연구 파이프라인

This directory is the controlled evidence and writing packet for the TRACE-RPG journal manuscript.
It follows the local `academic-research` full pipeline and records every mandatory user checkpoint.

이 디렉터리는 TRACE-RPG 저널 원고의 통제된 근거·집필 패킷이다. 로컬
`academic-research` 전체 파이프라인을 따르며 필수 사용자 체크포인트를 기록한다.

## Current state / 현재 상태

| Stage | Deliverable | State |
| --- | --- | --- |
| 1 | Research packet and venue contract | Approved 2026-08-12 |
| 2 | Source shortlist and claim boundaries | Approved 2026-08-12 |
| 2.5 | Pre-write claim/provenance integrity gate | Passed with fail-closed scope boundaries |
| 3 | IEEE ToG IMRaD outline and evidence map | Approved 2026-08-12 |
| 4 | Deterministic offline pilot and bilingual IEEE drafts | Approved 2026-08-13; post-Stage-8 packet regenerated |
| 4.5 | Claim-faithfulness integrity gate (L3) | Expanded final re-audit passed 2026-08-13 after correcting six additional claim defects and completing all figure/table references; clean release lock is separate |
| 5 | Citation verification | Passed 2026-08-13; current closure after addenda: 42 entries, 39 verified, 3 preprint, 0 unmatched/hallucinated |
| 6 | EIC + R1/R2/R3 + Devil's Advocate peer-review simulation | Revise-and-resubmit direction accepted and revision findings actioned |
| 7 | Optional cross-model verification | Not activated; no live cross-model evidence |
| 8 | Author revision | Executed; Class A/B findings closed, explicitly listed residual findings retained |
| 9 | Final formatting and AI-use disclosure | Executed; EN 7 pages, KO 6 pages, IEEE Short Paper band |
| 10 | Reproducibility passport and release lock | Passport compiled and final claim-faithfulness re-audit passed; clean committed/tagged recapture remains pending |

No hosted ten-model or human-study result is represented as completed evidence. Until those studies
are run, generated numerical results are limited to deterministic, local, offline harness experiments
and must be labelled **pilot engineering evidence**.

The current SHA packet recomputes all 55 declared worktree hashes. All 20 input paths exist at its
recorded commit, but only 19 exact digests match: the commit contains an earlier runner revision,
while the frozen runner revision is represented only by the dirty-tree hash. Both manuscripts now
disclose that exact gap. The L3 gate therefore passes, while archival release remains blocked until
a clean commit and tag are used for recapture.

호스팅 10개 모델 실험과 인간 대상 연구는 완료된 결과로 표현하지 않는다. 해당 연구가
실행되기 전까지 수치 결과는 결정론적 로컬·오프라인 하니스 실험에 한하며 반드시
**파일럿 엔지니어링 근거**로 표시한다.
