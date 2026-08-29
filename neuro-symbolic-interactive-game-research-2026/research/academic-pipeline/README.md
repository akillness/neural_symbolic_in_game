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
| 4 | Deterministic offline pilot and bilingual IEEE drafts | Approved 2026-08-13; guided-repair packet regenerated 2026-08-21 |
| 4.5 | Claim-faithfulness integrity gate (L3) | Expanded final re-audit passed; clean guided-repair input tag verified 2026-08-21 |
| 5 | Citation verification | Current closure: 45 entries, 0 unmatched/hallucinated |
| 6 | EIC + R1/R2/R3 + Devil's Advocate peer-review simulation | Revise-and-resubmit direction accepted and revision findings actioned |
| 7 | Optional cross-model verification | Single-model RQ2 live screening executed 2026-08-28; no cross-model or confirmatory evidence |
| 8 | Author revision | Executed; live screening addendum now separated from offline denominators |
| 9 | Final formatting and AI-use disclosure | Last built PDFs: EN 8 pages, KO 7 pages; live-addendum sources require rebuild |
| 10 | Reproducibility passport and release lock | Guided-repair release: 38 artifacts, 22 inputs, 121 provenance rows |

No hosted ten-model, confirmatory multi-model, or human-study result is represented as completed
evidence. A separate single-model RQ2 screening pilot is reported only through `C-PILOT-007/008` at
**screening-pilot-only**; `C-RESULT-003` remains `TODO-RESULT` under the unchanged promotion guard.

The current offline SHA packet records `dirty=false` at the tagged guided-repair input commit
`trace-rpg-guided-repair-inputs-20260821-v1`. All 22 declared inputs and 38 artifact hashes
recompute, and 121 provenance rows remain partitioned as 85 executed fixture rows plus 36 aggregate
rows. The manifest carries no absolute user/clone paths and records the portable `uv run python`
invocation. The separate `rq2-live-pilot/promotion-manifest.json` binds 14 JSON/JSONL receipt files
and retains the superseded v1 diagnostic apart from the corrected current cells. The hash-bound cell
summaries keep their earlier intended-promotion wording byte-for-byte; the outer manifest now
records the stricter current interpretation, allowing only `C-PILOT-007/008` and explicitly
excluding `C-RESULT-003`. No reviewer archive or DOI deposit is claimed, `C-RESULT-001`--`005`
remain `TODO-RESULT`, and G4/G6 remain separate game gates.

호스팅 10개 모델 확증 실험과 인간 대상 연구는 완료된 결과로 표현하지 않는다. 별도의 단일
모델 RQ2 스크리닝 파일럿만 `C-PILOT-007/008`의 **screening-pilot-only** 근거로 보고하며,
`C-RESULT-003`은 기존 승격 가드에 따라 `TODO-RESULT`로 유지한다. 해시로 묶인 셀 summary의
이전 승격 의도 문구는 바이트 단위로 보존하고, 바깥 promotion manifest가 현재의 더 엄격한
해석을 명시적으로 우선한다.
