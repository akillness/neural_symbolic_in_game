# 봉인된 등대 — 논문 및 Stage 6 연결표

```yaml
pair_id: SL-XWALK-001
language: ko
version: 0.2.0
run_id: 20260813-sealed-lighthouse-cycle-2
paper_target: SCI-or-SCIE-game-journal
status: DESIGN-CROSSWALK-NO-EFFICACY-RESULT
```

## 1. 범위

이 문서는 게임 메커니즘을 계획된 논문 근거와 연결한다. `TODO-RESULT` 주장을 승격하지 않는다.
제출 원고의 권위 소스는 `../../paper/latex/en/main.tex`와 `../../paper/latex/ko/main.tex`이며,
Markdown 파일은 대체된 프로토콜 청사진이다. [OBSERVED]

## 2. RQ1–RQ5 연결

| 표 SL-XWALK-T1 | 논문 주장 | 게임 조작 | 독립 단위 | 계획 종점 | 승격 전 필수 근거 | 현재 상태 |
|---|---|---|---|---|---|---|
| RQ1 / H1 | `C-RESULT-001` | 접근 불가 객체 홀드아웃, 미라 조기 공개, 인과 단계 생략; A5 대 A0와 등록 baseline | 홀드아웃 세계/퀘스트 템플릿, seed 중첩 | 유효 에피소드율, 하드 대화 위반율, 금지 공개 | 라이브 승격 모델 + 독립 인코딩/의미 오라클 + 혼합효과 분석 | `TODO-RESULT` [OBSERVED] |
| RQ2 / H2 | `C-RESULT-003` | 동일 거절 후보에 일반 맹목 재시도(A3) 또는 타입 반례(A4), `K=3` | 홀드아웃 시나리오/템플릿 | repair@K, 토큰, 비용, 지연, 실패 분류 | 호출/토큰 예산 매칭과 완전한 treatment-policy 회계 | `TODO-RESULT` [OBSERVED] |
| RQ3 / H3 | `C-RESULT-004` | 관계/사실 사건을 그래프+시간 provenance 유무로 `5/10/20` 턴에 질문 | NPC/관계 motif 템플릿 | 모순율, 유효성 매칭 다양성 | 분리 NPC/motif 홀드아웃 + 독립 의미 레이블 + provenance 추적 | `TODO-RESULT` [OBSERVED] |
| RQ4 / H4 | `C-RESULT-002` | A5 `trace_rpg_full`에 affect `off` 대 `uncertainty_calibrated_soft_adaptation` 교차, 높은 불확실성에서 비활성화 | 감정 템플릿 | 유효성 비열등 후 목표 긴장 RMSE | `2 pp`, 단측 `α=.025` 유효성 게이트 후 양측 `α=.05` RMSE 검정 | `TODO-RESULT` [OBSERVED] |
| RQ5 / H5 | `C-RESULT-005` | 승격 모델에 같은 동결 시나리오와 arm, 확증 전 10개 모델 스크린 | 모델 층을 가로지른 시나리오/템플릿 | 시스템-모델 상호작용과 방향 | 정확한 모델 리비전, 접근/규모 층, 민감도 분석 | `TODO-RESULT` [OBSERVED], 2차 추정량 |

## 3. 메트릭 정의

| 표 SL-XWALK-T2 메트릭 | 수식 | 권한 경계 |
|---|---|---|
| 유효 에피소드율 | `valid_completed_episodes / attempted_episodes` | 컨트롤러 자기채점이 아닌 독립 오라클 |
| 커밋당 하드 위반 | `hard_violations_on_committed_actions / committed_actions` | 인코딩 + 의미 감사 |
| 금지 공개율 | `forbidden_facts_disclosed / disclosure_opportunities` | 숨은 공개 오라클 |
| Repair@K | `invalid_candidates_repaired_within_K / invalid_candidates` | 매칭 A3/A4 배정, `K=3` |
| 기억 모순율 | `semantic_memory_contradictions / scored_memory_queries` | 독립 `5/10/20` 턴 레이블 |
| 목표 긴장 RMSE | `sqrt(mean((predicted_tension - target_tension)^2))` | 하드 유효성 비열등 뒤에만 검정 |
| 재생 동일성 | `I(engine_terminal_hash = research_terminal_hash)` | 엔진 정확성만, RQ 효과 아님 |
| 거절 불변성 | 거절/timeout/실패에서 `I(pre_state_hash = post_state_hash)` | 엔진/컨트롤러 경계 정확성 |
| 작성형 typed-link 제안 정밀도/재현율 | `P=TP/(TP+FP)`, `R=TP/(TP+FN)` | `SL-KG-ONTOLOGY-SIM-001` closed-world 방법론 링크만, RQ3 효능 아님 |
| K에서 온톨로지 적합도 | `Sem@K = conforming_top_K / (K × queries)` | 인코딩된 domain/range 구성 검사, 의미 완전성 아님 |

## 4. Stage 6 C1 해소 연결

Stage 6 C1은 전체 논문 효과와 외적 타당성이 없다고 판정한다. [OBSERVED] 게임 트랙은 특정
전제조건만 해소할 수 있으며 설계만으로 이 지적을 닫을 수 없다.

| 표 SL-XWALK-T3 C1 요구 | 설계/구현 표면 | 완료 근거 | 상태 |
|---|---|---|---|
| 라이브 모델/컨트롤러 비교 | `SL-ORACLE-T3`의 A0–A5 + 설정된 grounding/affect variant | 배정 완전 experiment record | [PLANNED] |
| 독립 의미 오라클 | `SL-ORACLE-001`의 인코딩+의미 계층 | 동결 숨은 레이블, 일치/조정, 매니페스트 해시 | [PLANNED], 레이블 미수집 |
| 홀드아웃 세계/퀘스트 | 결합 템플릿/motif 분할 | 분할 매니페스트 + 중복 감사 | [PLANNED] |
| 진짜 맹목 재시도 | A3 일반 재시도, 타입 피드백 없음 | A4 대비 프롬프트/호출/토큰 감사 | [PLANNED] |
| direct, constraint, reject, blind, repair, full arm | A0–A5 | 정확한 6-arm 설정 존재, 사전등록과 실행 레코드 필요 | [OBSERVED config] + [PLANNED execution] |
| 실패 유지 | treatment-policy 추정량 | timeout/parse/소진 행과 분모 | [TARGET] |
| 올바른 독립 단위 | 템플릿 클러스터, seed 중첩 | 원시 N, 클러스터 수, 분산 성분 | [TARGET] |
| 토큰, 지연, 비용 | 추적 계약 | 배정별 회계 + 요약 | [TARGET] |

현재 `configs/experiment-matrix.yaml`은 C1의 6개 arm을 명시하고 매칭 최대 호출을 `1+K=4`로
설정한다. [OBSERVED config] 이는 이름/설계 간극만 닫으며 실행, 오라클, 홀드아웃, 분석 요구는
닫지 않는다.

## 5. Stage 6 M6 해소 연결

| 표 SL-XWALK-T4 M6 요구 | Fixture | 필수 artifact | 해석 한계 | 상태 |
|---|---|---|---|---|
| 다단계 엔진 시나리오 | `SL-M6-LOAD`–`SL-M6-FAULTS` | Godot JSONL 추적 + 명령/빌드 메타데이터 | 엔진 로컬 정책 미러, 런타임 간/외적 타당성 아님 | [OBSERVED 저자 fixture] |
| 퀘스트 진행 | Q0→Q2 + 허가 단서 | 수집/설치 커밋과 단계 snapshot | 엔진 로컬 정확성, 이후 등대 진입은 범위 밖 | [OBSERVED 저자 fixture] |
| NPC 지식/공개 | 조기 거절 후 허가 단서 | `evt-002-validation-secret`, 폴백, `evt-005-commit-hint` | 라이브 arm/오라클 없이는 모델 품질 주장 금지 | [OBSERVED 저자 fixture] |
| 저장/불러오기 또는 재생 | 유효 저장/불러오기, 손상 저장 거절, operation 재생 | `evt-006-save`, `evt-007-load`, `evt-008-replay-check` | 지속성/재현성만 | [OBSERVED 저자 fixture] |
| 프레임/요청 예산 | 프레임과 요청 지연만 | 원시 텔레메트리 + 표본 수 포함 p95 | 프레임 목표 실패, 로컬 입력/제공자 지연 없음 | [OBSERVED 불완전, FIX] |
| Non-headless 엔진 렌더 | 정식 도착, 비밀 거절, 승인 힌트 | manifest ID `sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, `sl-rc-003-authorized-hint`를 묶는 `SL-CAPTURE-001` 논문 bundle | 저자 fixture render/state 대응만 | [OBSERVED 불변 승격] |

관찰 행은 엔진 로컬 정책 미러 근거다. 런타임 간 M6 통합 주장에는 라이브 Python 권한 transport가
필요하다. 어떤 행도 `C-RESULT-*` 상태를 바꾸지 않는다.
선택 render 패킷은 `godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`다. 불변 v1--v4는
보존하며 visual QA, validation-toolchain provenance 결속, CI portability 수정을 거쳐
superseded 처리했다. v5 evidence chain은 capture/decoder/schema/validator/lock hash와 tool
version을 기록하되 verifier host가 capture host를 가장하도록 요구하지 않는다.

## 6. 게임 artifact → 논문 사용

| 표 SL-XWALK-T5 artifact | 안정 ID | 지금 허용되는 논문 사용 | 지금 금지되는 사용 |
|---|---|---|---|
| GDD 쌍 | `SL-GDD-001` | 실험 게임과 권한 경계 설명 | 재미, 유효성, 이식성, 성능 주장 |
| 시나리오/오라클 쌍 | `SL-ORACLE-001` | 계획된 홀드아웃, arm, 독립 레이블 설명 | 완료 N, 일치도, 효과 보고 |
| 콘셉트와 세계관 | `SL-CONCEPT-001`, `SL-WORLD-001` | 공개 fixture 의미 정의 | 제작 세계관 QA를 골드 오라클로 사용 |
| 수치/코어 루프 계획 | `SL-BALANCE-001`, `SL-LOOP-001` | `[TARGET]` 설계 목표 보고 | 목표를 관찰 측정으로 보고 |
| 참신성 조사 | `SL-SURVEY-001`, `SL-NOVELTY-001` | 한계를 포함한 공식 설명 범위 비교 | 보편적 참신성 또는 플레이어 인상 주장 |
| 동결 콘셉트 팩 | `SL-C01`–`SL-C04` | AI 보조 콘셉트 제작과 시각 조건 공개 | 이미지 품질로 게임 품질/RQ 결과 추론 |
| Non-headless render bundle | `SL-CAPTURE-001`(manifest 필드가 아닌 논문 label), `C-GAME-DESIGN-003` | 정확한 manifest capture ID와 source 결속을 포함한 결정론적 구조화 상태 Godot render 표면 3개 제시 | 라이브 Python 통합, 모델/시각 효능, 사용성, 몰입, 인간 결과, G4 또는 G6 주장 |
| Typed methods-graph 시뮬레이션 | `SL-KG-ONTOLOGY-SIM-001` | simulation-only label 아래 작성형 6질의 링크 holdout 방법, 정확한 수식, 구성 검사를 보고 | 런타임 검색, 시간 메모리 효익, 의미 완전성, 플레이어 유용성, 어떤 `C-RESULT-*` 승격도 추론 금지 |
| 기여 판독 표면(`CONTRIBUTION #N`, `RULE LEARNED`, `CASE CHAIN`, 2부 구성 엔드카드 영수증) | `SL-GDD-T4`, `SL-HYP-001`, `SL-PLAY-EVAL-001` 검사 `contribution_delta_is_pure_and_names_facts`, `hold_teaches_rule_for_its_gate`, `case_chain_mirrors_committed_snapshot` | 플레이어블 장부가 원고의 predicate family(표 II)를 어떻게 반영하고 모든 commit을 snapshot delta에 연결하는지를 엔지니어링 적합성(ENG1, C2/C3 표면)으로 기술 | 재미, 지각된 주체성, 유능감, 좌절 감소, G4 또는 어떤 플레이어 결과 주장; `SL-GDD-T4`의 `[TARGET]` 질문에는 데이터가 없음 |

## 7. 논문 문구 통제

현재 허용:

> [TARGET] 봉인된 등대 프로토콜은 퀘스트 접근성, 게이트된 NPC 공개, 제한 수리, 시간 기억을
> 조작화한다. 저자 작성 Godot fixture가 실행한 범위는 퀘스트/공개/저장-불러오기/operation replay
> 하위 집합뿐이며, 모델·플레이어·시각 효과는 아직 시험하지 않았다.

라이브 Python 권한 부여를 포함해 실행되고 독립 검토된 M6 추적 뒤에만 허용:

> [OBSERVED] 동결 개발 에피소드는 사전 명시된 엔진 경로를 완료하고 종단 상태 해시를 재현했다.
> 이는 런타임 간 통합 경로 근거이며 모델 효과 근거가 아니다.

현재 엔진 로컬 근거는 안정 브리지 envelope 스키마 projection을 동반한 저자 작성 Godot 정책
미러 실행으로만 기술할 수 있다. 라이브 Python 권한 부여 왕복은 성립하지 않는다.

불변 승격과 새 검증 뒤 `C-GAME-DESIGN-003`은 다음 범위만 진술할 수 있다.

> [OBSERVED] 별도 non-headless Godot pass가 정식 저자 도착, 공개 거절, 승인 힌트 상태를
> `sl-rc-001-arrival`, `sl-rc-002-rejected-secret`, `sl-rc-003-authorized-hint`로 렌더링했으며,
> 선택 근거 세트에 source/file digest를 기록했다. 이는 render/state 대응이며 효능 또는 런타임 간
> 결과가 아니다.

C1 실행과 독립 검토 전 금지:

- “TRACE-RPG가 하드 위반을 줄인다”, “구조화 수리가 더 효율적이다”, “기억이 일관성을 높인다”,
  “감정 적응이 긴장을 개선한다”, “효과가 모델 전반에 일반화된다.”
- `C-RESULT-001`–`C-RESULT-005` 승격.
- 생성 이미지, 제작 QA, 결정론 fixture, M6 실행 1회를 독립 의미 또는 플레이어 품질 결과로 암시.

## 8. 릴리스 게이트

논문 인용 전 한·영 ID/수치, 링크 대상, 출처 정체성, 시나리오 분할, 오라클 독립성, 프로토콜 완결성,
누출 방지, 스키마 적합성, 결정론 재생, claim-ledger 상태를 검증한다. 누락 artifact는 `FIX`로 남기며,
삭제하거나 주장 경계를 약화할 이유로 쓰지 않는다.
