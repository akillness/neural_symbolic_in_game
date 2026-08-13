# 봉인된 등대 — 시나리오·홀드아웃·독립 오라클 계획

```yaml
pair_id: SL-ORACLE-001
language: ko
version: 0.1.0
run_id: 20260813-sealed-lighthouse-cycle-1
confirmatory_status: PLANNED-NOT-EXECUTED
development_fixture_status: OBSERVED-AUTHORED-GODOT-POLICY-MIRROR
primary_track: structured-state-text
secondary_track: secondary-vlm-ui
```

## 1. 목적 분리

`SL-DEV-001`(*봉인된 등대*)은 공개 개발 fixture이자 Stage 6 M6 엔진 fixture다. 스키마,
저장/불러오기, 재생, 텔레메트리, 연출 디버깅에 사용할 수 있다. 사실과 실패가 개발자에게 공개되어
있으므로 확증 효과 추정에서는 제외한다. [TARGET]

확증 RQ1–RQ5 모집단은 별도로 작성·동결한 세계/퀘스트 템플릿을 쓴다. 의미 골드 레이블은 사전등록된
unblinding 전까지 생성 시스템, 컨트롤러 작성자, 제작 세계관 QA, 시각 생성 프롬프트로부터 숨긴다.
[TARGET]

## 2. 시나리오 계층

| 표 SL-ORACLE-T1 계층 | 목적 | 템플릿과 반복 | 추론 상태 |
|---|---|---|---|
| 개발 | Godot M6, 스키마와 음성 fixture 디버깅 | `SL-DEV-001`; 필요 시 결정론 seed | 엔지니어링 전용 |
| Stage 1 스크리닝 | 등록 모델 10개 전체 Pareto 선별 | 트랙당 `30` 시나리오 × `3`회; 현재 설정 | 논문 수준 인과 결론 없음 |
| Stage 2 확증 | 승격 3개 모델의 사전등록 RQ1–RQ5 추정 | 트랙당 `120` 시나리오 × `5` seed (`11,23,47,83,131`); 현재 설정 | 동결·실행 뒤에만 확증 |
| 2차 시각 | 동결 이미지 팩을 사용한 모달리티/UI 민감도 | 별도 검정력/사전등록 블록 | 별도 등록 전 탐색적 |

`30/3`, `120/5`, 모델 수, seed는 `../../configs/experiment-matrix.yaml`에서 관찰된 설정값이며
완료 표본 수가 아니다. [OBSERVED config]

## 3. 시나리오 패밀리

| 표 SL-ORACLE-T2 패밀리 | 등록 앵커 | 필수 위험 | 1차 종점 |
|---|---|---|---|
| 세계 접근성 | `IF-LOCK-001` | 필수 객체 접근 불가 또는 자기 잠금 뒤 배치 | 유효 에피소드율 |
| 세계 인과 | `IF-CAUSAL-001` | 전제조건 전 효과 | 유효 에피소드율 |
| NPC 공개 | `NPC-SECRET-001` | 허가 전 미래 배신 요청 | 하드 대화 위반율 |
| 시간 기억 | `NPC-MEMORY-020` | 관계 변화 사건을 `5/10/20` 턴에 회상 | 유효성 매칭 모순율 |
| 인물 기만 | `NPC-DECEPTION-001` | 캐릭터 내 거짓말이 사적 정식 상태와 모순되면 안 됨 | 의미 하드 위반 |
| 감정 상승 | `AFF-RISE-001` | 퀘스트 안전을 지키는 상승 목표 | 유효성 게이트 뒤 긴장 RMSE |
| 감정 불확실 | `AFF-UNCERTAIN-001` | 높은 추정 불확실성에서 적응 비활성화 | 폴백 정확성 |

각 확증 항목은 개발 발화의 의역이 아니라 템플릿으로 인스턴스화한다. [TARGET]

## 4. 홀드아웃과 누출 방지 프로토콜

1. 모델 배정 전에 템플릿 패밀리 ID를 동결한다. 발화 단위가 아니라 결합
   `(world_template_id, quest_motif_id, npc_identity_id, relation_motif_id)` 단위로 분할한다.
   [TARGET]
2. `SL-DEV-001`, Brinewake, Captain Mira, 신호 렌즈, 가까운 어휘 의역은 개발 전용이며 Stage 2에서
   제외한다. [TARGET]
3. 정규화 그래프와 퀘스트 오토마타를 fingerprint한다. 분할을 가로지르는 근접 중복 구조는
   unblinding 전에 한쪽으로 전부 이동한다. [TARGET]
4. 모델 프롬프트는 인코딩된 런타임 가시 사실·정책을 포함할 수 있지만 숨은 의미 레이블,
   adjudication 기록, 오라클 전용 누락 필드는 포함하지 않는다. [TARGET]
5. 생성 모델 계열이 유일한 판정자가 될 수 없다. 생성 콘셉트 이미지는 정답을 제공하지 않는다.
   [TARGET]
6. 프롬프트, fixture, 오라클 스키마/버전, 모델 리비전, 이미지 팩 매니페스트, 컨트롤러 빌드,
   게임 빌드를 해시한다. [TARGET]
7. 시나리오/템플릿을 독립 단위로, seed를 중첩 생성으로 취급한다. 행을 독립 시나리오로 세지 않고
   클러스터 수와 분산 성분을 보고한다. [TARGET]

## 5. C1 컨트롤러 arm과 예산 매칭

Stage 6 C1은 다음 최소 진단 블록을 요구한다. [OBSERVED requirement] 정확한 6개 컨트롤러 ID와
예산 계약이 `../../configs/experiment-matrix.yaml`에 반영되어 있다. [OBSERVED config] 아직
실행하지 않았으며 확증 실행 전에 사전등록으로 동결해야 한다. [PLANNED]

| 표 SL-ORACLE-T3 arm | 검색 | 구조 제약 | 결정론 검증기 | 재시도/수리 피드백 | 호출 |
|---|---:|---:|---:|---|---|
| A0 `direct_commit` | 없음 | 없음 | 사후 채점만 | 없음 | `1` |
| A1 `structural_constraint_only` | 없음 | 스키마/문법만 | 사후 채점만 | 없음 | `1` |
| A2 `validator_rejection_only` | 매칭 맥락 | 없음 | 거절, 재제출 없음 | 없음 | `1` |
| A3 `matched_budget_blind_retry` | 매칭 맥락 | 없음 | 거절 | 일반 재시도, 최대 `K=3` 후속 | 총 최대 `4` |
| A4 `structured_repair` | 매칭 맥락 | 없음 | 거절 | 타입 반례, 최대 `K=3` 후속 | 총 최대 `4` |
| A5 `trace_rpg_full` | KG + 시간 provenance | 인코딩 정책 | 거절/커밋 | 타입 반례, 최대 `K=3` 후속 | 총 최대 `4` |

RQ4는 일곱 번째 컨트롤러 arm이 아니다. A5에 설정된 affect variant `off`와
`uncertainty_calibrated_soft_adaptation`을 교차한다. [OBSERVED config]

RQ2는 동일 모델, 시나리오, seed, 프롬프트 가시 사실, 최대 호출 `4회`, 최대 출력 토큰, temperature
`0.7`, top-p `0.95`, timeout `60 s`, cold-cache 1차 정책에서 A3와 A4를 비교한다. [TARGET]
실제 호출, 토큰, 지연, timeout, 파싱 실패, 수리 소진은 treatment-policy 추정량에 남긴다. A2를
맹목 재시도로 잘못 부르지 않는다.

## 6. 독립 오라클 계약

컨트롤러 검증기와 제작 G1 세계관 감사는 유일한 결과 오라클이 될 수 없다. [OBSERVED requirement]
동결 오라클은 합치지 않는 두 계층을 가진다.

### 6.1 인코딩 오라클

- 독립 작성한 전이 그래프, 객체 접근성, 퀘스트 전제조건, NPC 지식, 공개 allow-list. [TARGET]
- `encoded_valid`, 타입 위반 코드, 예상 상태 delta를 출력한다. [TARGET]
- 별도 구현 또는 선언형 골드 artifact를 쓰며 treatment 검증기를 레이블 함수로 호출하지 않는다.
  [TARGET]

### 6.2 의미 오라클

- 서사 텍스트가 불가능 행동, 금지 공개, 미지 사실, 필수 객체/효과 누락, 모순, 근거 없는 상태
  변경을 주장하는지 판정하는 블라인드 annotation 스키마. [TARGET]
- 인코딩 경계가 의도적으로 수용하는 `disclosure_hazard`, `omitted_object_hazard`,
  `unknown_field_hazard` sentinel을 포함한다. [TARGET]
- 향후 독립 레이블 2개와 adjudication을 계획한다. 일치도, 원시 불일치, 결측, adjudication 변경을
  보고해야 한다. Cycle 1에는 레이블을 수집하지 않는다. [PLANNED]

### 6.3 골드 격리

저장소에는 오라클 스키마, 레이블 어휘, 동결 ID, 암호학 매니페스트를 둘 수 있다. 항목별 골드값은
unblinding 전까지 접근 통제 저장소에 남긴다. 생성/컨트롤러 로그에는 항목 ID만 전달한다. 제작 QA는
합성 레이블로 프로토콜 배선을 시험할 수 있지만 의미 효과를 인증할 수 없다. [TARGET]

## 7. 레이블과 adjudication 레코드

| 표 SL-ORACLE-T4 필드 | 타입 | 의미 |
|---|---|---|
| `scenario_id`, `template_id` | string | 동결 배정과 독립 클러스터 |
| `oracle_version`, `gold_manifest_sha256` | string | 숨은 판정 세트의 정체성 |
| `encoded_valid` | boolean | 독립 인코딩 세계 유효성 |
| `semantic_valid` | boolean/undetermined | 독립 서사 유효성 |
| `hazard_codes` | set | 공개, 객체/효과 누락, 미지 필드, 모순, 불가능 전이 |
| `evidence_spans` | offsets + hashes | 의미 레이블을 지지하는 최소 텍스트 |
| `annotator_id` | pseudonymous code | 저장소에 직접 개인식별자 금지 |
| `confidence` | ordinal | annotation 불확실성, 모델 신뢰도 아님 |
| `adjudication_status` | enum | none, pending, resolved, excluded-with-reason |

## 8. 1차·2차 트랙 무작위화

1차 구조 배정은 모델, 시나리오/템플릿, seed, 컨트롤러 arm, grounding variant, RQ4의 affect
variant로 블록화한다. [TARGET] 2차 시각 배정은 `image_pack_id`와 제시 순서를 추가 블록으로 둔다.
모든 이미지는 무작위화 전에 생성, 검토,
동결, 해시한다. [TARGET] 시각 트랙은 행동 정책, 골드 레이블, 퀘스트 그래프, 커밋 권한을 바꾸지 않는다.

오도하는 시각 감정 단서는 사전등록된 2차 탐침에서만 허용하며, VLM 또는 감정 불확실성이 높으면
적응을 비활성화해야 한다. [TARGET] 사전 명시된 계층 모델 없이는 시각 결과를 1차 결과와 합치지 않는다.

## 9. M6 엔진 프로토콜

엔진 로컬 저자 정책 미러는 동결 로드, 항구 관찰, 접근 가능 수집, 변경 없는 해시를 동반한 조기
비밀 거절, 유효 퀘스트 단계 커밋, 허가된 단서, 저장/불러오기 동일성, JSONL operation replay 종단
동일성, 중복/timeout 폴백, 손상 저장 거절을 실행했다. [OBSERVED authored fixture] 정식·중복·timeout
세 실행은 정확한 명령 형식, Godot 버전, 플랫폼, 소스/fixture 해시, 이벤트 로그, 저장 파일,
전/후/종단 해시, 요청 지연, 5표본 프레임 시간과 함께 보존됐다. [OBSERVED incomplete]

로컬 입력 피드백 지연, soak 실행, 라이브 Python 권한 왕복은 아직 없다. [TARGET] headless 성공은
저자 설계 엔진 경로 정확성만 뒷받침하며 라이브 모델, 독립 오라클, 플레이어, VLM 결과로 셀 수 없다.

## 10. 분석 계획 정렬

- RQ1: 하드 유효성 혼합효과 로지스틱 모델, 템플릿 임의 절편, 모델 고정 층; H1 세계/대화 대조 Holm
  보정. [TARGET]
- RQ2: A4 대 A3, repair@K와 토큰/비용/지연, 단일 양측 `α=.05`. [TARGET]
- RQ3: `5/10/20` 턴 기억 대 무기억, 매칭 하드 유효성 대역 조건부 모순 결과. [TARGET]
- RQ4: affect `off` 대 `uncertainty_calibrated_soft_adaptation`의 A5, 단측 `α=.025`에서 유효성
  비열등 한계 `2 percentage points`, 이후 양측 `α=.05` 긴장 RMSE 우월성. [TARGET]
- RQ5: 시스템-모델 상호작용은 2차이며 확증이 아니다. [TARGET]

이 계획에는 효과 결과, 효과크기, 신뢰구간, 일치도 값, 완료 N이 없다. [OBSERVED]
