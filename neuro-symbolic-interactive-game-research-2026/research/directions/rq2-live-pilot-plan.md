# RQ2 라이브 파일럿 실행 계획 — Live Pilot Plan (C-RESULT-003 → pilot-only)

```yaml
plan_id: SL-RQ2-LIVE-001
status: APPROVED-2026-08-28-NOT-EXECUTED
approval: 사용자 인터뷰 응답 "승인, 바로 진행" (2026-08-28); ChatGPT 쿼터 사용 승인 포함
target_claim: C-RESULT-003 (guided repair vs blind retry sample efficiency at matched K)
promotion_ceiling: pilot-only   # verified-empirical 전이는 금지(M2/M3/M5 미충족)
```

## 동결 설계 (실행 전 변경 금지)

- **비교 아암**: `unchanged_retry`(A3, blind) vs `guided_repair`(A4, ρ(a,E)) — 두 아암 모두
  라이브 제안자 1개, 매칭 예산 `1+K=4` (`configs/experiment-matrix.yaml` 준수).
- **케이스**: 기존 동결 12 repair fixtures(guided_repairable 5 / oracle_only 1 / irreparable 6)
  + 시드 `[11, 23, 47, 83, 131]`. 케이스·기대 분류 편집 금지.
- **제안자**: `CodexProposalAdapter` — `scripts/codex_oauth_llm.py` `run_prompt()` 위에
  `ProposalAdapter` 프로토콜(`src/nesy_game/experiment.py:61`) 구현. 실패는 기존
  `AdapterFailure` 분류로만 매핑. `soft_proposal_policy.model_visible_projection()`으로
  금지 사실을 프롬프트에서 사전 차단.
- **모델 표기**: 실제 `model_id`/`model_revision` 문자열을 trace에 기록하고, 호스티드
  리비전 불안정성 때문에 **screening 라벨**로만 보고(M7 정규화 전 promoted-model 금지).
- **출력**: `runs/live-pilot-rq2/` 신규 경로. `runs/conformance-pilot/`과 동결 패킷
  `research/academic-pipeline/stage-04-pilot/`은 바이트 불변 유지.
- **엔드포인트**: repair@K 커밋률, 시도 수, 토큰, 지연, 실패 분류. p-값·모집단 주장 없음.

## 실행 순서 (다음 세션 첫 작업)

1. 선행 정리(감사 권고): `research/claim-ledger.yaml`의 C-PILOT-002 문구를 12-케이스
   기준으로 갱신, S44–S46을 stage-05 인용 게이트에 병합, `pyproject.toml`에
   `testpaths=["tests"]` 추가.
2. `CodexProposalAdapter` + 단위 테스트(모킹) 구현 → 스위트 그린.
3. 라이브 스모크 1회(`codex_oauth_llm.py smoke`) → 성공 시 12×2아암×5시드 실행.
4. trace manifest + sha256 잠금 → `C-RESULT-003`을 `pilot-only`로 승격(전이 요건:
   trace_manifest, schema_pass, pilot_label).
5. 한글 보고 갱신 → 영어 패리티 → push.

## 확인된 전제 (2026-08-28)

- `codex login status` → `oauth_prompt_ready: true` (chatgpt_oauth).
- 스키마 `game-track/schemas/codex-oauth-soft-proposal.schema.json` 존재, 스크린 정책 테스트 그린.
- 금지 전이 `TODO-RESULT → verified-empirical`은 harness 워크플로가 차단.
