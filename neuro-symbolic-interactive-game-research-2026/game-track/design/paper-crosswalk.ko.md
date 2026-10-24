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

## 검증된 현재 프로덕션 (2026-10-23)

[프로덕션 별칭](https://sealed-lighthouse-trace-rpg.vercel.app)과
[생성 배포 주소](https://sealed-lighthouse-trace-fflmsgady-akillness-projects.vercel.app)의
`dpl_75HRZ3UGnVtADdvZnFUJaG9espYY`는 관측 상태 `READY`다.
[HTTP 영수증](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-http-assets.json):
스테이징 게임·대시보드·PDF 18/18개 HTTP 200, 바이트 수·SHA-256 동일, 루트 307 → `/dashboard/`.
[native 키보드·마우스 프로덕션 QA](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-browser/actual-game-acceptance.json)는
stage-zero 거절, 렌즈, 설치/2단계, 최초 공개, 승인된 재표시, map 1440, map 390, 연속 진단의
8/8게이트를 통과했고 console/page/request/HTTP 오류는 각각 0건이다. DPR 2 headed 데스크톱 Chromium
세션 1개의 390 px 줄바꿈·키보드 검사이지 물리 모바일 기기의 gameplay는 아니다.

[표현 개선 릴리스 영수증](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-final-verification.json)은
집중 검사 171개 + subtest 23개 통과를 기록한다: 동결 사례 62개 + 출판 소스 43개 + 표현 회귀 44개
및 시각 검증기 22개([집중 검사 영수증 049](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/049-frozen-affected-regressions.json),
[한·영 논문 영수증 050](../../_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/050-frozen-paired-papers.json)). [출처 정체성 음성
사례와 승인된 한·영 절 오라클](../../tests/test_ontology_publication_sources.py)은 동결 출판 선언을
검사하며 런타임 권한, 독립 인간 골드 및 효능 검증과 구별한다. SVG 4개와 표의 여백을 넓히고
LaTeX 수식을 정식 조판했다. 표는 패딩 4 pt·`arraystretch=1.20`·표준 IEEE 10 pt 글꼴을 유지한다.
현재 [영문](../../paper/latex/en/main.pdf) / [한국어](../../paper/latex/ko/main.pdf) PDF는 각각
10쪽, 675846 / 631282바이트이며 Type3 글꼴은 각각 0개다. 최종 선택 소스 CI는 표현 개선
영수증에서 확인한다. Git 전달은 별도의 저장소 커밋·원격 이력으로 확인하며 프로덕션
PASS로 추론하지 않는다. [봉인 사례](../../research/development-cases/ontology-map-20261023-01/result.json)는
`n=1`, native CLI 6회, 반복 0회, 런타임 선택 `gpt-6.1-sol`, 제공자 정체성·리비전·비용 `null`
그대로다. Jev는 승인 권한 없는 부정적·미검증 `proposal_only` 조언이다. [소스 맵](../web/dashboard/ontology-map.json),
Godot writer 권한, 정식 R5 캡처, fixture60과 NPC88은 변경하지 않는다. **G4/전체 G6는 `FIX`이며
효능·우월성·인간 편익은 입증하지 않는다.** R3/D-087의 현재 프로덕션 상태만 대체하며 비공개·raw
원본과 과거 메트릭은 보존한다.

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
선택된 현재 machine-bound render 패킷은
`godot-4.7.1-20261023-publication-r5`이며
[`current.json`](../../_workspace/current/engineering/tech-verification/current.json)이 선택한다.
[매니페스트](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20261023-publication-r5/evidence-manifest.json)는
실제 Godot 실행 4종과 `2026-10-23 11:00:42` UTC의 macOS non-headless 스크립트 fixture-trace
재생 패널 3개를 기록하며 라이브 Python 권한 transport나 neural inference를 사용하지 않았다.
source/toolchain hash와 tool version을 기록한 저자 작성 render/state 대응이지 실제 플레이어 상호작용이 아니다. R4(`godot-4.7.1-20261023-publication-r4`)와 이전
`godot-4.7.1-20261023-signal-explainer-r1`, `godot-4.7.1-20261015t083849z-sealed-lighthouse-current-v3`과 더 오래된 불변 패킷은 당시 근거로
보존하며 현재 런타임 인증으로 취급하지 않는다.

과거 [R3 프로덕션 영수증](../../_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-final-verification.json)은
`dpl_BvpyBPiSouiyoyzN3wG9WQN16YNM`의 `PASS_FOR_APPROVED_BOUNDED_RELEASE`, Godot 정식
사례 7개, public-safe 검사 8개, 배포 자산 바이트 일치 9개를 기록한다. 고정 60사례에서
general-rule과 ontology-gate는 각각 허용 16개, 거절 44개, 기대 불일치 0개로 일치한다.
이는 선언 유래의 한정된 공학적 적합성이며 온톨로지 우월성이나 효능이 아니다.
**G4와 전체 G6는 `FIX`다.** 이번 문서 갱신은 새 배포나 push를 주장하지 않는다.

[논문 producer 매니페스트](../../paper/latex/generated/disclosure_producer_manifest.json)는 별도로
현재 `results-signal-explainer-20261023-r5` 결정론적 Python/Godot artifact의 출판 전용 materialization을 기록하며 새 모델 관측은 없다. 공개 인터뷰
파생본은 과거 비공개 원문과 바이트 동일하지 않고 원래 동결 패킷과 과거 런타임 영수증은 유지한다.
출판 materialization과 공개 파생본 모두 선택 렌더를 대체하지 않는다.
[실제 브라우저 입력 gameplay 영수증](../../_workspace/current/qa/releases/2026-10-23-signal-explainer/receipt.json)은
commit 3회와 hold 1회 뒤 미라의 승인 힌트에서 멈췄고 조수위 표식 추리는 시도하지 않았다.
스크립트 재생, 출판 provenance, 실제 gameplay는 다른 근거 종류다. 이후 공개 전용 관측도
소유자의 `current.json` 갱신 없이는 렌더 선택을 바꾸지 않는다.

과거 trace/receipt 수정 체크포인트에서 Main은 대상 8파일의 테스트 53개와 subtest 48개
통과를 보고했다. 이후 근거와 별도 CI/Git 증명은 위 현재 프로덕션 절을 따른다.

### 5.1. 온톨로지 구조·근거 개발 사례

2026-10-23 갱신. 읽기 전용 한·영 **Ontology structure → evidence / 온톨로지 구조 → 근거**는
[대시보드](../web/dashboard/index.html)의 **Engineering detail** 안에 있다. `Tab`/`Enter`로
details를 열 수 있고 표는 모바일 폭에서 줄바꿈된다. 저자 작성 8역할은 **World, Actor,
Knowledge, Fact, Policy, Quest, Action, Trace**다. [Source map JSON](../web/dashboard/ontology-map.json)은
정규 식별자·동결 출처 참조·규칙 ID를 유지하며 UI에만 공개 별칭을 쓴다. 선언 구조와 최신
관측 공개 이벤트는 별도 열이며 전체 정규 상태에 접근하지 않는다. 누락·미보고·건너뜀을
통과로 바꾸지 않는다. 8역할, Python predicate 7개, Godot 표시 family 6개, 공개 규칙 7개는
일대일 대응이 아니다.

봉인된 [결과](../../research/development-cases/ontology-map-20261023-01/result.json)는 `ACCEPTED`다.
실제 Codex 개발 사례 1개(`n=1`, 독립 반복 0회)에서 native 런타임이 `gpt-6.1-sol`을 선택했고
CLI 호출은 6회(편집 턴 5회, 읽기 전용/no-edit resume 1회)다. 제공자 반환 모델 정체성·불변
리비전·비용은 미상(`null`)이며 런타임 선택은 제공자 가중치 인증이 아니다. 과거 `gpt-5.6-sol`과
NPC88을 재명명하지 않는다. 영수증은 검사 62개 통과, Godot Web 빌드 exit 0, 실제 입력의
stage-zero 거절·최초 공개·승인된 재표시를 기록한다. 읽기 전용 열람은 상태와 동결 비교를 보존한다.
1440×900과 390×900 모두 8역할을 표시하고 키보드 Enter를 확인했으며 탐색 전부터 수집한
연속 진단에서 console/page/request/HTTP 오류와 warning은 각각 0건이다.

- [공개 근거 manifest](../../research/development-cases/ontology-map-20261023-01/public-evidence-manifest.json)는 원본/공개 해시를 구별한다. 실패 시도와 동일 사례 수리는 보존되며 추가 표본이 아니다.
- 실제 브라우저 PNG: [거절](../../research/development-cases/ontology-map-20261023-01/browser/010-stage_zero_denial.png), [최초 공개](../../research/development-cases/ontology-map-20261023-01/browser/036-fresh_disclosure.png), [승인된 재표시](../../research/development-cases/ontology-map-20261023-01/browser/038-authorized_redisplay.png), [1440 px map](../../research/development-cases/ontology-map-20261023-01/browser/map-1440-action.png), [390 px map](../../research/development-cases/ontology-map-20261023-01/browser/map-390-action.png).
- [메커니즘 도식](../../paper/latex/figures/fig_signal_mechanism.pdf) `fig:signal-mechanism`은 저자 작성 그림이지 브라우저 캡처가 아니다. 현재 각 10쪽 [영문](../../paper/latex/en/main.pdf)·[한국어](../../paper/latex/ko/main.pdf) 원고의 `sec:development-case`를 함께 본다.

이 추가 개발 공학 사례는 동결 공개 코호트 60사례나 NPC88을 늘리지 않으며 인간 편익·재미·
효능·생산성·온톨로지 우월성을 입증하지 않는다. Godot 소스·쓰기 권한과 정식 R5 엔진 캡처는
그대로다. **G4/전체 G6는 `FIX`다.** 현재 프로덕션과 별도 CI/Git 증명은 위 절을 따른다.
보존된 retired hosted-model 코호트(과거 표기, fixture60, NPC88 포함)는 provenance 전용이며 활성 논문 표·계수·런타임 모델 주장에서는 제외한다. 어떤 label/result도 런타임이 보고한 `gpt-6.1-sol` 개발 사례로 이전하지 않는다. 출처 기반 traceability instrument는 제안일 뿐 score를 측정하지 않았다: [`codebook.ko.md`](../../research/traceability-scoring-20261023/codebook.ko.md), [`sources.json`](../../research/traceability-scoring-20261023/sources.json). Whole-game matched-information 및 repeated-cross-model 비교는 `PROPOSED_NOT_EXECUTED` 계획이다: [`plan.ko.md`](../../research/development-comparison-20261023/plan.ko.md).

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
