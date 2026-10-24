# 시그널 데이터 타입·온톨로지 단계·게임 배포 후속 인터뷰

## 사용자 요구와 현재 상태

2026-10-23 사용자는 subagent와 Jev 사용, 합의한 게임 변경의 반영·빌드·배포, 시그널 데이터 부재 이유와 추이/그래프 인터뷰를 요청했다. 추가 요구 원문: “파일명과 자료 데이터를 폴더 단위로 기제하지않고, 그 내용을 정리해서 어떤 데이터 타입으로 실험을 전개했고, 온톨로지로 구성하여 단계가 진행되었는지 이해할수있도록 구성해야해.”

설명은 **의미·자료형 → 개체/관계/규칙 → 행동 제안 → 실제 검사 → 허용/거절 → 정규 상태 전이 → 신호/비교 해석** 순서로 구성한다. 파일 경로는 내부 출처 추적용이며 사용자 설명의 주 구조가 아니다. 원래 인터뷰·구현 전 감사는 아래에 날짜가 있는 이력으로 보존하고, 현재 승인된 구현·빌드·배포 완료는 마지막 release 종료 절과 최종 receipt로 구분한다.

Ouroboros interview: `interview_20261023_050206`. 사용자는 첫 질문에서 **작동 과정과 비교 함께**를 선택했다. 한 사건의 데이터·관계·규칙·판정을 주 설명으로 두고 독립 사례 비교를 별도 검증 그래프로 연결한다. 파일/폴더 대신 의미 타입과 온톨로지 단계로 설명한다는 요구도 확정됐다. 인터뷰 시작 당시 git context는 main@fa9fb8a, 0 staged/9 unstaged/104 untracked였으며 현재 작업 트리 상태를 뜻하지 않는다.

**后续批准 / 후속 승인:** 사용자는 두 번째 질문에서 **게임에도 선택형 설명 패널**, 최종 수용 기준 질문에서 **이 기준으로 구현·배포**를 선택했다. 고정 기준은 (1) 내용 중심 선택형 인게임 패널, (2) 실제 사건순 신호와 독립60사례·3조건 비교를 분리한 대시보드, (3) 미기록/건너뜀/범위외의 정직한 표시, (4) 동일 의미·수치·근거의 EN/KO 각10쪽 이하 PDF(본문 글자·여백 축소 없음), (5) 검증한 build의 기존 사이트 배포와 실제 동작 확인이다. 인간 효능 실험·모델 변경·새 외부 서비스는 제외한다.

승인된 불변 [Seed](../../../.ouroboros/seeds/seed-20261023-signal-explainer-b35b22f4227d.yaml)는 보존된다. spec-kit MCP plan은 설치 CLI에 없는 `specify plan`을 호출하여 실패했으므로 성공으로 기록하지 않는다. Seed에서 파생한 계획 `_workspace/current/engineering/signal-explainer.plan`의 Runtime/Dashboard/Data/Papers 구현과 승인된 빌드·배포는 [최종 receipt](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-final-verification.json)의 `PASS_FOR_APPROVED_BOUNDED_RELEASE`로 종료됐다.

## 구현 전 확인 이력 — 2026-10-23 초기 인터뷰

- **[OBSERVED] 원자료는 존재한다.** 고정 기대표의 정상48/경계4/형식오류8을 세 조건에 각각 적용하여 60×3=180 기록이 있다. 각 사례의 초기 상태를 별도로 구성하므로 기록 순서는 한 플레이의 시간축이 아니다. 단순 직렬화 순서를 학습/향상 추이로 표시할 수 없다.
- **[OBSERVED] 내용 중심 자료형:** 요청은 행동/행위자/사실 ID를 가진 객체이고, 퀘스트 단계는 정수이며, 지식 보유·기존 공개 여부는 Boolean 조건이다. 지식·공개 이력은 사실 ID의 집합 의미를 정렬된 배열로 저장한다. 정책은 영구 금지 사실 집합과 사실별 최소 단계 관계를 갖는다. 결과에는 허용 Boolean, 구조화된 오류 목록, 기록된 검사 결과, 상태 변화 종류, 전후 상태 식별값, 재생 일치 여부가 있다.
- **[OBSERVED] 세 신호 체계를 구분한다.** 원래 Python 7 Boolean 검사, Godot 6 표시 의미군, 선택 공개 행동의 7 선언 규칙은 같은 7개 채널이 아니다. 공개 행동의 연구 trace는 앞에서 통과한 모든 검사를 기록하지 않는 sparse annotation이다. 비어 있는 칸은 `미기록`이지 통과/건너뜀/범위외가 아니다.
- **[OBSERVED] 화면 소비 연결이 빠져 있다.** Godot은 `disclosure_outcome`/`disclosure_replay`를 내보내지만 dashboard는 전용 처리·그래프 갱신 대신 일반 로그로 처리한다. 기존 연구 참고 패널도 E1/E2만 읽고 새 공개 결과를 읽지 않는다. 기존 미러의 source pin과 현재 hard-writer bytes가 다르므로 전체 새 공개 계약을 완전히 계측한 그림으로 부를 수 없다. 이는 소스 조사 결과이며 현재 production browser 관찰이 아니다.
- **[OBSERVED] 그래프 해석:** 현재 자료로 조건/정상·경계·형식오류별 비교 막대 및 `미기록`을 명시한 사례×규칙 행렬은 가능하다. 실제 사건순 타임라인은 기존 seq/engine time/상태 hash 이벤트를 이용한 새 실행 기록이 필요하다. 개인·잠재 모델 상태·게임 재미/학습 효과 자료가 생기는 것은 아니다.
- **[OBSERVED, 구현 전] 이전 수정의 배포 미수행 경계.** 초기 감사 당시 최신 보관 배포는 10-16 Vercel release였고, 10-23 선행 공개 수정 receipt는 clean build/production deploy/browser 검증 미수행을 명시했다. 초기 인터뷰는 public alias/provider를 재검증하지 않았고 당시 PDF 각12쪽은 publication FIX였다. 기존 dry-run도 실제 build/export를 하므로 read-only 확인용으로 실행하지 않았다. 이 dated 실패는 보존하되 현재 상태는 아래 release 종료의 새 production 증거·각10쪽 PDF가 대체한다.

## 인터뷰 당시 내용 중심 설명안 — 이후 승인·구현 완료

1. 상황: 누가 어떤 사실을 알고 있고 퀘스트가 어느 단계인지 typed state로 설명한다.
2. 온톨로지: NPC–알고 있음–사실, 사실–최소 공개 단계–단계, 사실–영구 금지–정책, 행동–공개 대상–사실 관계를 보여준다. 현재 선언을 해석하는 구체 규칙이지 문서 전체를 자동 OWL 추론기로 바꿨다는 주장이 아니다.
3. 실험 조건: 한 번에 바꾸는 지식/단계/공개 이력과 공통 기대값, 세 실행 조건, 각 분모를 명시한다.
4. 판정: 실제 실행/기록된 검사와 거절 이유, 허용 여부를 보여준다. 거절이 규칙대로라면 기대 일치 측면에서 성공일 수 있다.
5. 상태 전이: 거절은 상태 유지, 새 공개는 허용된 사실 공개 이력/정해진 효과만 반영, 재표시는 현재 권한을 다시 확인하고 상태를 중복 변경하지 않는다. 공개 자체가 퀘스트 단계를 올리는 것은 아니다.
6. 시각화: 시간 흐름(새 실제 실행)과 독립 사례 비교(기존 고정 사례)를 분리한다. 7개 수치의 매끈한 선형 곡선을 임의로 만들지 않는다.

인터뷰 때 ‘단계1 거절 → 합법적 중간 행동 후 단계2 → 새 공개 허용 → 재표시’는 설명용 구성이었다. 기존60개 독립 사례를 그 연속 실행의 관찰로 바꾸지 않는다. 이후 별도로 수집된 실제 입력 기반 production 실행은 아래 release 종료에서 구분한다.

## 보조 검토

- Read-only subagents: `SignalGapAudit`, `ReleasePathAudit`. 소스/데이터/보관 배포 증거를 조사했으며 새 테스트·빌드·배포를 수행하지 않았다.
- Jev `jeopi` profile, API backend, 1 request, returned model `jev-1.14.0`, unvalidated/proposal_only. `addresses_task=0.85`, `evidence_supports=0.39`, `needs_clarification=0.50`(probabilities), threshold=0.8, 698 input/80 output tokens, reported latency=311ms. Receipt `64651391846510ce5af756619eafc25813d77b8cc80ba88f421dd0bb44cb39d4`. 이는 제안의 보조 검토이며 연구 정답·실험 신호·커밋/배포 승인으로 쓰지 않는다. 점수를 올리기 위한 재시도는 하지 않았다.
- Initial interview call timed out but server event query showed a persisted interview; resume recovered the first question. Local SQLite view was not the server's current store; server query was used instead. No duplicate implementation run was started.

## 내부 근거

연구 루트 `neuro-symbolic-interactive-game-research-2026/` 기준:

- `src/nesy_game/disclosure.py:229-255,322-418,637-690,817-887`: 사례 상태 구성, 별도 정책 선언 선택, sparse 검사/결과 기록, 비교 의미.
- `research/npc-disclosure/results-current/disclosure-trace.jsonl`: 180개 독립 사례/조건 기록; SignalGapAudit가 전체 행을 read-only 파싱.
- `game-track/godot/scripts/game3d/game_3d.gd:958-1016,1054-1123`: 새 공개 이벤트·기존 6군 표시 경계.
- `game-track/web/dashboard/dashboard.js:731-857`: 기존 히스토리/이벤트 처리/참고 데이터 소비 경계.
- `scripts/build_godot_web.sh`, `scripts/deploy_vercel_dashboard.sh`: disposable/public-safe build와 combined site 배포.
- `research/npc-disclosure/final-verification-20261023.json:235-251`: 12쪽 publication FIX 및 빌드/배포 미수행 경계.
- [[wiki/reports/2026-10-22-ontology-signals-interview]]: 이전 source-bound 보고서는 동결 상태로 보존.

## 설명 방향과 구현 수용 기준

단일 사건의 typed input→온톨로지→실제 검사→상태 전이를 주 설명으로 하고 독립60사례 비교를 별도 검증 패널로 연결하는 방향이 선택됐다. 선택형 게임 내 패널과 위 다섯 기준도 승인됐으며, 구현·검증·기존 사이트 배포 완료는 아래 최종 receipt로 확인된다. 실제 사건순 기록은 별도 공학 실행이며 frozen 사례 순서를 시간축으로 바꾸지 않는다.

## 초기 인터뷰 자문과 자체 점검 이력 — 구현 전 평가이며 현재 release 판정 아님

추가 자문 6개 lane(code/web/data/contrarian/simplifier/architecture)을 병렬 실행하고 같은 질문의 보조 결과로 제출·회수했다. 서버 결과 `fanout:4b27135c81c05e3be8075bbadd2b725569f447441fac63e18435907d5f3e88d5`는 missing/contract violations 없이 complete이며 사용자 선택을 대신하지 않는다. data lane의 `not_a_measurement`는 이 우선순위 질문이 선호 결정이라는 뜻이며 원자료가 없다는 뜻이 아니다. 상위 원자료 감사의 독립 상태 구성과180행 집계는 별도로 확인되어 있다. 아래 자체 점검은 제안된 공통 의미 schema/두 화면이 당시 미구현이던 초기 평가다. 이후 구현 완료도 연구 방법론 온톨로지와 실제 runtime 권한 엔진을 하나로 합쳤다는 뜻은 아니다.

| 자체 점검 | 점수 | 근거와 남은 한계 |
|---|---:|---|
| 정확성 | 4/5 | 소스·180행 감사·실제 Jev 응답을 구분했다. 현재 production 브라우저를 실행하지 않아 소스상 연결 누락만 단정한다. |
| 완전성 | 4/5 | 데이터 타입·관계·판정·상태 전이 및 배포 경계를 설명했다. 인터뷰 선택이 아직 없어 구현·배포 완료를 주장하지 않는다. |
| 명확성 | 4/5 | 파일 목록 대신 의미 흐름으로 재구성했다. 전체 연구 방법론 단계와 게임 진행 단계는 후속 설명에서도 구분해야 한다. |
| 실행 가능성 | 4/5 | 기존 이벤트의 소비 경로와 가능한 비교 그래프를 특정했다. 구현 수용 기준은 사용자의 첫 선택 이후 확정한다. |
| 간결성 | 4/5 | 사용자 설명은 내용/사례/질문에 집중하고 경로는 내부 근거로 분리한다. 내부 자문은 상대적으로 길다. |

평균4.0/5. 우선 보완: 단일 사건의 단계별 설명을 앞에 두고, 독립 사례 비교와 실제 사건순 그래프를 분리하며, 마지막에는 한 가지 목적 질문만 제시한다. 사용자가 이 평가에 동의할지는 확인하지 않았다.

## 2026-10-23 승인된 한정 release 종료

**현재 상태: `PASS_FOR_APPROVED_BOUNDED_RELEASE`.** [승인 Seed](../../../.ouroboros/seeds/seed-20261023-signal-explainer-b35b22f4227d.yaml)의 다섯 기준은 [최종 closure receipt](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-final-verification.json), 관찰 시각 `2026-10-23T07:34:34.105503+00:00`에 따라 완료됐다. 선택형 인게임 설명, 실제 사건순 신호와 독립 사례 비교를 분리한 대시보드, 미기록/건너뜀/범위외 표시, 한영 PDF, 검증 build의 기존 사이트 배포를 닫는다. 초기 planning 실패·미배포·12쪽 기록과 [[wiki/reports/2026-10-22-ontology-signals-interview]]의 source-bound 보고서는 동결 이력으로 보존한다.

- **배포와 최신 정확한 provider 확인 명령:** 연구 루트에서 기록된 `vercel inspect https://sealed-lighthouse-trace-rpg.vercel.app --scope akillness-projects --json` → `READY`, deployment `dpl_BvpyBPiSouiyoyzN3wG9WQN16YNM`, [production](https://sealed-lighthouse-trace-rpg.vercel.app). 위 최종 receipt의 배포 명령은 `bash scripts/deploy_vercel_dashboard.sh`이다. 이 문서 정리에서 재실행한 명령이 아니다.
- **별도 focused 회귀:** [focused-tests-r3.json](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/focused-tests-r3.json), `2026-10-23T06:55:51.524307+00:00`: `uv run pytest -q tests/test_signal_explainer.py tests/test_godot_signal_explainer.py tests/test_evaluation_trace_mirror.py tests/test_generate_npc_paper_results_model_cohort.py tests/test_check_disclosure_paper_evidence.py tests/test_generate_disclosure_paper_results.py tests/test_run_disclosure_evaluation_cli.py` → exit0, **66 passed +16 subtests passed in44.03s**. 이는 production browser 검증 명령이 아니다.
- **분리된 엔진 분모:** 최종 receipt의 canonical Godot **7 semantic cases PASS**와 [public-safe-smoke-r3-verified.json](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/public-safe-smoke-r3-verified.json)의 **8/8 authored public-safe smoke**는 별도다. smoke 종료는 `2026-10-23T07:06:18.720450+00:00`, exit0이며 frozen Python60사례 전체나 인간 연구를 뜻하지 않는다.
- **실제 입력 production 동작:** [production-r3-browser-proof.json](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-browser-proof.json), `2026-10-23T07:32:07.896Z`: 실제 mouse/keyboard로 `denied → legal progress → authorized_fresh → authorized_redisplay`를 관찰했다. 정규 commit은 총3회뿐이며 거절·재표시는 상태를 바꾸지 않는다. 재표시와 설명 패널 조작에서 추가 commit/정규 상태 변경이 없고 **관찰된 browser diagnostics는0**이다. 상태 주입·가짜 engine event·teleport를 사용한 증거가 아니다.
- **배포 동일성과 PDF:** [production-r3-asset-identity.json](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-asset-identity.json), `2026-10-23T07:27:52.760394+00:00`의 실제 배포9/9 asset bytes/SHA-256이 local과 일치한다. 최종 receipt의 `pdfinfo`/`pdffonts` 관찰에서 **EN/KO 각10쪽, Type3 없음**이며 선행 각12쪽 FIX를 해소했다. 이 판정은 전 문장 번역 동등성·모든 페이지 시각 감사·투고/게재 승인을 뜻하지 않는다.
- **이벤트 발행 시점:** 같은 browser proof에서 fresh `disclosure_outcome` **seq899는 commit 직전 count2**를 담고, 바로 다음 **commit seq900이 count3**으로 올린다. `authorized_redisplay` **seq1097은 count3을 유지**한다. fresh 이벤트의 count2를 최종 총 commit 수로 읽거나 재표시가 네 번째 commit을 만든 것으로 읽지 않는다.
- **비교 해석은 그대로:** general-rule과 ontology-gate는 각각 **60사례, allowed16/denied44/unsafe0**, 두 gate의 결과60/60 일치다. isolated unchecked **unsafe51=무권한 허용44+재표시 변경7**이며 semantic mismatch60과 다른 지표다. 정상48/경계4/malformed8, 별도 규칙변경2/짝비교4는 frozen 분모로 유지한다. 독립 사례 순서를 학습 추이나 ontology-superiority로 해석하지 않는다.
- **남은 제외 범위:** [production-r3-mobile-comparison.json](../../../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-mobile-comparison.json), `2026-10-23T07:33:13.743Z`는 **390px dashboard reflow만** 확인한다(page width390, label11px, 그래프 wrapper 내부 scroll). 실제 기기 mobile gameplay·touch·G6 성능 인증이 아니다. **G4/full G6는 FIX**이며 human-gold, access-separated holdout, 인간 효능/플레이어 이익, 잠재 모델 상태, 일반화·우월성, 새 인간/장시간 soak 연구로 승격하지 않는다. 이 정리는 다섯 기존 상태 문서만 갱신하며 code/paper sources/raw/frozen reports·결과·이전 receipts를 변경하거나 테스트·포매터·린터를 실행하지 않는다.

## 2026-10-23 온톨로지 구조별 증거 배치와 실제 개발 실측 방향

**사용자가 확정한 방향:** 패킷명을 먼저 나열하지 않고 온톨로지의 구성·관계·구조를 보여준 뒤 해당 부분의 근거 패킷을 표시한다. 후속 연구는 제안 방법을 실제 Codex 내러티브 게임 개발에 적용하면서 개발 과정과 게임 환경의 데이터를 실측하는 것이다. 이번 기록은 방향·설명 구조의 확정이며 새 개발 실행, 데이터 수집, 모델/API 호출, 참여자 연구 또는 재배포 완료가 아니다. 기존 승인 release와 frozen 결과는 그대로 보존한다.

**Bilingual framing / 한영 공통 연구 문장:** “온톨로지 기반 명세와 결정적 검증을 실제 Codex 내러티브 게임 개발에 적용하고, 개발 작업의 결과·수정 과정과 게임 실행의 상태·서사 제약 준수를 전향적으로 측정한다.” / “We will prospectively apply ontology-based specifications and deterministic validation during actual Codex narrative-game development, measuring development-task outcomes and revision processes separately from runtime state transitions and narrative-constraint conformance.” 이 문장은 후속 연구 계획이지 현재 실증 결과가 아니다.

### 구조와 식별자의 역할

아래는 설명용 역할 구조다. 하나의 공통 그래프가 모든 런타임에 구현되어 있다는 뜻이 아니다. 연구용 methods ontology, 개발에 제공할 명세, 게임의 authoritative state/policy는 역할과 권한을 분리한다.

```text
온톨로지 기반 명세: 개체·관계·조건·허용 전이
├ 개발 시 적용 → Codex의 코드·퀘스트·대화·게임 산출물 → 개발 작업/run 실측 [후속 대상]
└ 실행 시 적용 → 세계/NPC/사실/퀘스트 상태
   ├ NPC의 의도·행동 제안 [기존 NPC-SCR1: 역사적 screening]
   ├ 지식·공개 권한·단계 검사 [NPC-DISC-1: reveal_hint 한정]
   ├ 계획/승인/상태 기록 [NPC-ENG1: Godot-authoritative 통합]
   └ 판정·상태 변화·재생 기록 [각 레인의 분모와 버전별 증거]

별도 core Python 검사·수정·재생 근거: E1 / E2
별도 methods KG 링크 제안 시뮬레이션: E3 [게임 runtime ontology와 동일시하지 않음]
```

`NPC-DISC-1` 등은 실험 레인명이다. 개별 패킷 ID·계약 버전·규칙 ID와 구분한다. 공개 계약의 실제 frozen expectation packet은 `sl-npc-disclosure-expectations-v1` v`1.0.0`이며 상태는 `FROZEN_EXPECTATIONS_NOT_RUNTIME_RESULTS`다. 기대 패킷은 관측값이 아니다. 현재 관측 결과는 `results-signal-explainer-20261023-r3` 수집본 및 앞 절 release receipt에 별도로 결속된다. NPC 통합 프로토콜 `npc-goal-recovery/1.1.0`과 역사적 `verified-run-006`도 서로 다른 식별자다. E2의 `gpt-5.6-sol` 모델명을 모델 정보 미상인 NPC-SCR1 또는 후속 개발 실행에 이식하지 않는다.

| 온톨로지 구조 요소 | 선언에서 확인한 구체 내용 | 관련 근거 |
|---|---|---|
| 개체와 자료형 | `captain_mira`, 네 canonical fact ID, 정수 stage, Boolean knows/prior_disclosed | NPC-DISC-1 expectation packet의 scope |
| 지식 관계와 공개 권한 | 행위자 적격성, 사실 보유, 영구 금지 여부는 별개 조건 | `DISC-001/003/004` |
| 퀘스트 단계와 공개 가능 관계 | `tide_marks_hint`의 최소 공개 stage는 2 | `DISC-002`; NPC-DISC-1 |
| 새 공개 전이 | 요청 사실과 disclosed ID만 추가; 조석 단서의 선언된 memory 효과; stage 유지 | `DISC-005` |
| 재표시와 거절 전이 | 재표시는 현재 권한을 재검사하고 정규 상태 불변; 거절도 상태 불변과 안전한 표시만 허용 | `DISC-006/007` |
| 목표·행동·상태 소유권 | Codex typed intent, Python 공개 주장 검증/제한된 계획, Godot 최종 승인·기록 | NPC-ENG1/NPC-SCR1; `npc-goal-recovery/1.1.0` |
| 일반 검사·수정·재생 메커니즘 | core Python 계약 적합성과 hosted repair screening은 별도 | E1/E2; Godot 전체 통합으로 읽지 않음 |
| 연구 방법론 관계 그래프 | 타입·관계 링크 제안의 closed-world simulation | E3; runtime 권한 엔진이나 개발 생산성 증거 아님 |

Python 7 Boolean 검사, Godot 6 표시군, `DISC-001`–`DISC-007`의 7개 규칙은 계속 구분한다. 개발 시 Codex가 이 구조를 활용해 게임 산출물을 만드는 효과는 기존 runtime packet만으로 입증되지 않는다.

### 후속 실측의 제안 계약 — 표본수·실행 승인은 아직 동결하지 않음

- **관측 단위:** 개발 작업/run과 그 결과 게임 버전. prompt/tool/check/repair/게임 event는 해당 run 안의 반복 관측이며 독립 표본 수로 부풀리지 않는다. 연속 개발 작업의 부모 산출물·상태 의존성도 남긴다.
- **실험 조건 동결:** 동일 작업 목표·수용 기준·시작 코드/데이터/게임 상태, 온톨로지 버전, 실제 요청/반환 모델 정보, prompt/config hash, 도구 권한, Godot·OS·하드웨어·의존성, 중단/재시도 정책과 사람 개입을 기록한다. 얻을 수 없는 model revision/token/cost는 missing이지 추정 실측값이 아니다.
- **구조 효과 비교 제안:** 같은 사실·관계·제약을 일반 문서로 제공한 조건과 구조화된 온톨로지로 제공한 조건을 비교하되 도구·정보 접근·결정적 게이트를 동일하게 둔다. 정보량·컨텍스트 길이 등 남은 차이를 기록한다. 이는 구조화 효과를 묻는 설계이며 게이트 제거 효과나 온톨로지의 모든 구성요소 효과와 혼동하지 않는다.
- **주 지표 제안:** 시작한 적격 run 전체 중 동결된 hard requirements와 실행 가능한 build/요구된 게임 진행을 모두 충족한 run의 비율. 모든 행동을 거절하는 게임은 성공이 아니다. 보조 지표는 실제 검증 완료까지의 시간, 검사 실패–수정 반복, 회귀 결함, 사람 개입 횟수/시간, 토큰·비용의 관측 가능 부분이다. API latency와 end-to-end 개발 시간은 분리하고 중단·실패 시간을 성공 완료 시간으로 바꾸지 않는다.
- **서사 측정 분리:** 선언된 지식/인물/세계/퀘스트 제약의 위반은 hard 결과로 기록한다. 자연어 서사 일관성·선택의 의미·재미는 별도의 사전 정의된 평가가 필요하며 gate 통과율로 대체하지 않는다. 참여자 평가를 시작한다는 승인은 아니다.
- **증거 연결:** 온톨로지 버전 → 개발 작업/run → 실제 prompt/tool/patch/build → 게임 artifact → 실행 session/event → 검사/수정/정규 전이/replay → 논문 claim/table/figure를 추적한다. 성공뿐 아니라 오류, timeout, 거절, fallback, 제외 사유를 보존한다. 새 cohort를 추가하고 현재 선택 포인터를 갱신하며 기존 frozen expectation/관측 결과를 덮어쓰지 않는다.
- **해석 경계:** 기존 60사례 적합성, 후속 개발 과정 실측, 실제 게임 환경 관측, scripted probe와 authored fixture를 분리한다. 반복 수·조건 순서·표본 독립성·사람 지원을 사전 명시하기 전 유의성·일반화·개발 생산성 또는 서사 품질 향상을 확정하지 않는다. 과거 10-model/6-system 장기 계획을 이번 범위에 자동 추가하지 않는다.

### 근거와 이번 기록의 검증

- 직접 확인: 연구 루트 `paper/latex/en/main.tex:70-126,187-205`, `paper/latex/generated/disclosure_tables_en.tex:1-21`, `research/npc-disclosure/reveal-hint-expectations-v1.json:1-80`. 현재 원고·선언의 식별자와 관계에 근거한다.
- 독립 read-only 구조/실측 설계 검토: `OntologyPacketArchitectureReviewer`, `ActualDevelopmentMeasurementReviewer`. 새 실험이나 코드 변경을 수행하지 않았다.
- Workspace semantic lookup은 timeout이었고, installed `graphify query "ontology" --graph llm-wiki/graphify-out/graph.json --budget 1200`은 old node-ID 경고와 no matching nodes(exit4)를 반환했다. 이를 개념 부재의 근거로 쓰지 않고 위 원고·선언을 사용했다. 그래프·인덱스를 재생성하지 않았다.
- 이번에는 이 노트·index·log의 방향 기록만 갱신한다. 한영 PDF 본문/그림 재편집, 새 구현/실측, 논문 수치 변경 및 배포는 아직 실행하지 않았다.

### 수용 판정과 관측 단위의 구체화 — 후속 설계 제안

- **측정 단위는 개발 run:** 사전 정의된 작업과 시작 snapshot에서 시작해 수용·실패·중단으로 끝나는 실행 한 번이다. 같은 작업의 반복 run과 연속 개발 작업은 작업/부모 산출물에 묶고 독립 표본으로 자동 간주하지 않는다. tool call·수정·게임 event는 run 내부 관측이다.
- **주 지표의 run별 판정:** 사전에 정한 (1) build 실행 가능, (2) 요구된 퀘스트/상호작용의 실제 도달·완료, (3) 해당 작업의 필수 권한/지식/단계/상태 불변 조건, (4) 기록된 입력·전이의 결정적 replay 일치를 모두 충족해야 accepted=1, 하나라도 불충족하면 0이다. 성공률의 분모는 사전 적격 기준으로 시작한 모든 run이며 실패·timeout을 성공 run으로 대체하거나 사후 제외하지 않는다. 구체 작업·반복 수·배정/중단 정책은 후속 실행 전에 동결할 대상이다.
