# 봉인된 등대 — 권위 있는 실험 게임 기획서

```yaml
pair_id: SL-GDD-001
language: ko
version: 0.1.0
run_id: 20260813-sealed-lighthouse-cycle-1
engine: Godot 4.x headless-first
episode_target_minutes: [8, 12]
evidence_state: TARGET-DESIGN-PLUS-OBSERVED-AUTHORED-ENGINE-FIXTURE
```

## 1. 목적과 권한

이 GDD는 *봉인된 등대*의 안정적인 제품·상호작용·논문 참조 표면을 정의한다. 실시간 G1 세계관
권한은 `../../_workspace/current/design/worldview.md`, 수치 제안은
`../../_workspace/current/design/balance-sheet.md`가 가진다. 현재 사이클에서 ID나 불변식이
바뀌면 인용 전에 이 동반 문서도 갱신해야 한다. [TARGET]

게임은 턴 기반 내러티브 수사 마이크로 RPG이자 TRACE-RPG 시스템 탐침이다. 상용 게임,
인간 효과 연구, 모델 품질 결과가 아니다. [OBSERVED scope]

## 2. 플레이어 제안

브라인웨이크 부두를 구한 플레이어는 폭풍 속에서 꺼진 등대를 조사한다. 접근 가능한 등구점에서
신호 렌즈를 회수하고, 미라 선장에게 질문하며, 의도된 금지/단계 게이트 공개 거절을 한 번 경험한
뒤 렌즈를 설치하고 허가된 `tide_marks_hint`를 얻는다. 연구 슬라이스는 등대가 봉인된 상태에서
다음 경로 affordance를 보여주며 끝난다. [TARGET]

의도된 리듬은 다음과 같다.

`관찰 → 조사/질문 → 제안 → 검증 → 수리/폴백 → 커밋 → 피드백`

`60–120초` 마이크로 루프 네 개가 `8–12분` 목표 에피소드를 구성한다. 각 루프에는 플레이어
행동 `3–5회`와 정보·접근·관계 보상 `1–2회`가 있다. [TARGET]

## 3. 설계 불변식

| ID | 불변식 | 강제 방식 |
|---|---|---|
| GDI-01 | 유효한 `commit`만 정식 상태를 변경한다. | 현재 fixture는 Godot 저자 정책 미러, 목표는 연구 런타임 권한 부여이며 모두 전/후 상태 해시를 쓴다. [OBSERVED fixture + TARGET transport] |
| GDI-02 | 거절, timeout, 파싱 실패, 수리 소진, 중복 전달은 부분 상태 변경을 만들 수 없다. | 전체 상태 동일성과 멱등성 fixture. [TARGET] |
| GDI-03 | NPC 지식과 공개 허가는 분리한다. | `captain_mira` 지식 투영과 퀘스트 단계 공개 정책. [TARGET] |
| GDI-04 | 소프트 감정, 시각 해석, 참신성, 스타일은 하드 유효성을 덮어쓸 수 없다. | 권한 경계 테스트. [TARGET] |
| GDI-05 | 연구와 Godot 런타임은 버전 JSON/JSONL 레코드만 교환한다. | 스키마 검증과 결정론적 재생. [TARGET] |
| GDI-06 | 1차 구조 트랙과 2차 동결 이미지 트랙은 분리된 매니페스트를 쓴다. | 매니페스트 ID와 SHA-256 확인. [TARGET] |

## 4. 세계와 퀘스트 모델

정식 런타임 장소는 `harbor_dock`과 `lamp_store`이며 `lighthouse_offshore`는 이 슬라이스에서
관찰하지만 진입하지 않는 표지다. 정식 개체는 `player_investigator`, `captain_mira`,
`signal_lens`다. 렌즈는 접근 가능한 등구점에서 시작하며 봉인된 등대 안에 놓이지 않는다.
[OBSERVED fixture]

| 표 SL-GDD-T1 단계 | 전제조건 | 허가된 결과 | 필수 음성 사례 |
|---|---|---|---|
| Q0 `arrival` | `dock_saved`, `lighthouse_dark` | 관찰과 공개 질문 | 없는 렌즈 설치 금지 |
| Q1 `lens_acquired` | 접근 가능한 `signal_lens` 수집 | `signal_lens_acquired` | 접근 불가 수집 거절 |
| Q2 `lens_installed` | 렌즈 인벤토리 + 단계 `≥1` | `signal_lens_installed`, `lighthouse_hint_authorized` | 객체/단계 전제 생략 거절 |
| Q2-HINT `terminal_disclosure` | 단계 `≥2`, 미라가 `tide_marks_hint`를 앎 | `tide_marks_hint` 공개, 단계 유지 | `keeper_betrayal`과 과거 소급 변경 거절 |

`keeper_betrayal`은 미라가 알지만 영구 공개 금지이며 fixture 배선에는 테스트 ID만, 골드 서사
페이로드는 노출하지 않는다. `omitted_object_hazard`와 `unknown_field_hazard`는 평가자 전용
레이블이다. 골드 페이로드는 프롬프트, 플레이어 UI, 이미지 프롬프트, 제작 세계관 QA에 들어갈 수
없다. [TARGET]

## 5. 플레이어 행동과 피드백

개념 행동 집합은 `OBSERVE`, `INSPECT`, `COLLECT`, `ASK`, `PRESENT`, `TRAVEL`, `SAVE`,
`LOAD`이며, `REPLAY`는 검사기 표면에 속한다. [TARGET] 정확한 wire enum은 버전 브리지 스키마가
소유한다.

각 상호작용은 연출 목표로 `≤100 ms` 내 로컬 확인을 보여준다. 이는 모델 응답이 아니며 요청 완료를
뜻하지 않는다. 제안 인과 링크는 점선, 커밋 링크는 황색 실선, 거절 링크는 산호색으로 멈추고 중립적
이유와 다음 유효 affordance를 보여준다. 숨은 오라클 레이블은 노출하지 않는다. [TARGET]

미라 선장은 짧고 실용적인 해양 언어를 쓴다. 신뢰도는 말투를 바꿀 수 있지만 비밀을 허가하거나
퀘스트 전제조건을 충족하지 못한다. 정식 조기 요청 폴백은 등대지기 배신을 공개하지 않고 신호
렌즈를 회수하도록 안내한다. [TARGET]

## 6. 이중 트랙 콘텐츠 계약

| 표 SL-GDD-T2 트랙 | 입력 | 권한 | 런타임 생성 | 의도된 근거 |
|---|---|---|---|---|
| 1차 구조 트랙 | 정식 JSON 상태, 텍스트 관찰, 저자 제작 비생성 기호 마커 | 인코딩 정책과 결정론 검증기 | 없음 | 계획된 RQ1–RQ5 확증 평가 |
| 2차 VLM/UI 트랙 | 1차 입력 + 검토·SHA-256 동결 콘셉트 이미지 | 동일한 하드 권한, 이미지는 소프트 관찰 | 금지 | 탐색적 모달리티/UI 평가 |

공개 안전 스냅샷은 `../assets/concepts/public-exclusion.json`에 제외 ID `SL-C01`, `SL-C02`,
`SL-C03`, `SL-C04`를 기록하며, 생성 바이트는 인간 검토 전까지 공개 트리에 포함하지 않는다.
[OBSERVED artifact] 내부에서 승격할 각 출력은 정확한 프롬프트, 음성 제약, 참조 입력 목록, 생성기/제공자 메타데이터, UTC 시각, 크기,
바이트, SHA-256, 큐레이션 상태, 의도 트랙, 권리 검토, AI 사용 공개, `runtime_eligible: false`를
보존해야 한다. [TARGET]

## 7. 수치 명세

| 표 SL-GDD-T3 ID | 값 | 의미 | 상태 |
|---|---:|---|---|
| B-001 | `480–720 s` | 에피소드 길이 | [TARGET] |
| B-002 | `60–120 s` | 마이크로 루프 길이 | [TARGET] |
| B-003 | `3–5` | 마이크로 루프당 행동 | [TARGET] |
| B-004 | `1–2` | 마이크로 루프당 보상 사건 | [TARGET] |
| B-005 | `8–14` | 에피소드당 커밋 결정 | [TARGET] |
| B-006 | `1` | M6 경로의 의도된 조기 비밀 요청 | [TARGET] |
| B-008 | `K=3` | 무효 후속/수리 예산 | [OBSERVED config] |
| B-009 | `≤100 ms` | 로컬 확인 목표 | [TARGET] |
| B-010 | `5/10/20 turns` | 관계/사실 기억 지평 | [TARGET] |
| B-011 | `0.35→0.72→0.50` | 선택적 정규화 긴장 곡선 | [TARGET] |
| B-013 | `1+K=4` | 매칭 재시도/수리/full arm의 최대 호출 | [OBSERVED config] |

전투와 경제는 없다. 매치업 승률, TTK, 콤보 EV, 유료/무료 차이, 역전 구매, 동등 도달 세션은
적용되지 않는다. 디렉터 결정 `D-006`이 제로 이코노미 G5 오버라이드를 승인했지만 대체 부재 검사는
측정하지 않았다. 필요한 검사가 실행될 때까지 G2와 G5는 `FIX`다. [OBSERVED status]

## 8. 추적과 텔레메트리

모든 배정 에피소드는 제안, 근거, 검증, 수리, 커밋/폴백, 모델과 리비전, seed, 비용, 토큰,
요청 지연, 엔진 지연, 빌드 해시, 전/후 상태 해시, 저장 해시, 재생 해시, 실패 분류를 보존해야 한다.
[TARGET]

엔진 정확성과 모델 효과는 서로 다른 추정량이다. Godot 재생 성공은 Stage 6 M6을 뒷받침할 수
있지만 `C-RESULT-001`–`C-RESULT-005`를 뒷받침할 수 없다. [OBSERVED claim boundary]

## 9. 접근성과 연출

시각 방향은 독창적인 “해양 증거철”이다. 해도 판화 선, 절제된 구아슈 날씨, 젖은 점판암,
산화 황동, 단일 황색 신호를 쓴다. [TARGET] 색은 항상 텍스트/아이콘 중복을 가지며, 조작 대상은
최소 `44×44 px`, 본문은 `1×`에서 `18 px`, 모션 감소와 자막은 첫 플레이 가능 디버그 표면부터
포함한다. [TARGET]

## 10. 과장 없는 인수 기준

저자 작성 headless 슬라이스는 로드, 신호 렌즈 수집, 금지/단계 공개의 안전한 거절, 렌즈 설치,
허가된 단서, 저장/불러오기, operation replay, 종단 해시 비교, 중복 전달, timeout/폴백, 손상 저장
거절까지 M6 시퀀스를 실행했다. [OBSERVED authored fixture] 논문 결과 준비
상태는 `SL-ORACLE-001`의 분리 동결된 홀드아웃·독립 오라클·모델 arm·분석·리뷰 게이트가 실행된
뒤에만 가능하다.

현재 결과 상태: **이 GDD는 플레이어, 라이브 모델, 독립 오라클, 시각 모델, 엔진 성능 효과 결과를
주장하지 않는다.** [OBSERVED]
