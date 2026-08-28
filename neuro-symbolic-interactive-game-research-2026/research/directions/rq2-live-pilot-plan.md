# RQ2 라이브 파일럿 실행 계획 — Live Pilot Plan (C-RESULT-003 → pilot-only)

```yaml
plan_id: SL-RQ2-LIVE-001
status: EXECUTED-2026-08-28 (null result; see C-PILOT-007)
approval: 사용자 인터뷰 응답 "승인, 바로 진행" (2026-08-28); ChatGPT 쿼터 사용 승인 포함
target_claim: C-RESULT-003 (guided repair vs blind retry sample efficiency at matched K)
promotion_ceiling: pilot-only   # verified-empirical 전이는 금지(M2/M3/M5 미충족)
```

## 동결 설계 (실행 전 변경 금지)

- **비교 아암**: `unchanged_retry`(A3, blind) vs `guided_repair`(A4, ρ(a,E)) — 두 아암 모두
  라이브 제안자 1개, 매칭 예산 `1+K=4` (`configs/experiment-matrix.yaml` 준수).
- **케이스(실행 시 정정)**: 동결 12 fixtures는 *이미 무효인 후보*이므로 라이브 제안자와
  결합할 수 없다. 실행 설계는 **시드당 라이브 제안 1회 → 동일 후보를 두 아암이 공유**로
  고정했다(샘플링 잡음 배제). 시드 `[11, 23, 47, 83, 131]`.
- **조건 3종(사전 등록)**: `policy_visible`(제약표 공개), `policy_blind`(제약표 비공개),
  `goal_directed_blind`(효과 0 행동 금지 — 자명한 통과 경로 제거).
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


## 실행 결과 (2026-08-28) — 귀무 결과

| 조건 | 최초 유효 | 최초 무효 | guided 커밋 | blind 커밋 | 관측 오류 코드 |
|---|---:|---:|---:|---:|---|
| `policy_visible` | 5/5 | 0/5 | 5/5 | 5/5 | — (수리 미발생) |
| `policy_blind` | 5/5 | 0/5 | 5/5 | 5/5 | — (수리 미발생) |
| `goal_directed_blind` | 0/5 | 5/5 | 0/5 | 0/5 | `QUEST_STAGE_REGRESSION` |

- 두 무제약 조건에서 모델은 매번 `SAY`를 골랐다. 기저 상태의 `SAY` 정책은 필수 효과가
  없어 **효과 0의 자명한 유효 행동**이 상존하므로, 최초 유효율이 아암을 판별하지 못한다.
- 자명 경로를 막자 모델은 5/5 `ROLLBACK_STAGE`(스테이지 1→0)를 냈고, 이는 동결 분류상
  **guided-irreparable**이다. ρ는 상태를 읽지 않으므로 수리 불가이고, blind도 불가다.
- 따라서 오프라인에서 관측된 guided 우위(5/12)는 **이 제안자·이 기저 상태에서는 재현되지
  않았다**. 라이브 오류 분포가 guided-repairable 클래스와 겹치지 않았기 때문이다.
- 모든 폴백에서 이전 상태 해시가 보존됐다(안전 경계는 라이브에서도 유지).

## 다음 설계 수정 (다음 세션)

1. 기저 상태를 **자명 통과 행동이 없는 상태**로 확장하거나, `SAY`에 필수 효과를 부여한
   변형 시나리오를 추가한다(동결 패킷은 불변 유지, 새 시나리오 ID로).
2. guided-repairable 오류를 실제로 유발하는 프롬프트 조건(예: 효과 목록 일부만 제시)을
   사전 등록한다.
3. 시드가 호스티드 샘플러를 제어하지 못한다는 점을 명시한다 — 제안 해시는 5/5 서로 달랐지만
   구조적 선택(행동 유형·오류 클래스)은 동일했다. 시드는 독립 표본이 아니라 준복제다.
4. 토큰 회계는 CLI 래퍼가 노출하지 않아 0으로 기록된다(`token_accounting_available: false`).
