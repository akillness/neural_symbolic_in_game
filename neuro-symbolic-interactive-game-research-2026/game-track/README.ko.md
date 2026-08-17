# 게임 개발 트랙 — 봉인된 등대

게임 트랙은 연구 코드를 엔진 내부에 직접 결합하지 않는다. 목표 아키텍처는 엔진이 안정 브리지
관찰을 보내고 연구 런타임이 권한 이벤트를 반환하는 구조다. 현재 Godot fixture는 엔진 로컬 저자
정책 미러를 실행한다. 지원 이벤트는 `schemas/game-bridge.schema.json`으로 projection되어 스키마
검증되지만 라이브 Python↔Godot transport는 아직 실행하지 않았다.

현재 구현은 이벤트/실험 스키마, 결정론적 검증, 상태 불변 fallback, 무결성 검사, operation/상태
해시 replay, frozen-response 어댑터에 Godot 4.x headless 실험 슬라이스와 별도 non-headless
render-capture pass를 추가한다. 저자 설계
Godot 경로는 항구 상태 로드, 접근 가능한 신호 렌즈 획득, 조기 금지/단계 제한 공개의 상태 불변
거절, 렌즈 설치, 이후 허용되는 조수 흔적 힌트, 저장/불러오기, 재생, duplicate/timeout/손상 저장
주입을 다룬다. 프로세스 간 영속 멱등성과 라이브 모델 transport는 계획 상태다.

라이브 어댑터 승인 조건:

- 엔진의 canonical state 변경은 유효한 `commit` 이벤트를 통해서만 일어난다.
- 모든 이벤트는 `run_id`, `episode_id`, `step`, `schema_version`, `world_state_hash`를 가진다.
- 재시도와 네트워크 중복은 영속 `event_id` 멱등성으로 제거해야 한다.
- 시간 초과, 모델 장애, 높은 감정 불확실성에서는 결정론적 안전 정책으로 fallback해야 한다.
- 연구 트랙은 실제 엔진 없이 mock bridge로 실행할 수 있고, 게임 트랙은 모델 없이 recorded trace를 재생할 수 있다.

선택 엔진은 Godot 4.x headless-first다. 엔진 선택 자체는 논문 기여가 아니며 프로토콜 호환성과 재현 가능한 상태 동일성이 기준이다.

시작 경로:

- [`design/gdd.ko.md`](design/gdd.ko.md) — 정식 실험 GDD
- [`design/paper-crosswalk.ko.md`](design/paper-crosswalk.ko.md) — RQ1--RQ5 및 Stage 6 연결표
- [`godot/README.ko.md`](godot/README.ko.md) — headless 실행과 근거 경계
- [`assets/README.md`](assets/README.md) — 권리 검토 전 생성 후보의 공개 안전 제외 매니페스트
- [`../_workspace/current/production/task-manifest.md`](../_workspace/current/production/task-manifest.md) — 현재 스튜디오 사이클

1차 계획 실험은 구조화 상태/텍스트를 사용한다. 생성 이미지는 제외되며 별도 동결 2차
VLM/UI 트랙에만 들어갈 수 있다. 설계나 headless 슬라이스는 참가자·모델 효능 결과를 만들지
않는다.

## Cycle 3 public-safe 플레이어블과 평가

현재 플레이어블 `godot/scenes/main_3d.tscn`은 3인칭 부두 탐색, 읽기 쉬운 상호작용 포커스,
반응형 장부 UI, 모션 감소, 풀링된 절차 VFX, 사용자 제스처 뒤 활성화되는 로컬 생성 음향을
추가한다. 세계를 바꾸는 모든 의도는 계속 저자 설계 제안·검증 라우터를 거친다. 플레이어는
항구 측 신호를 복구하고 썰물 항로를 얻으며 앞바다 등대는 봉인된 채로 남는다.

| `SL-PLAY-EVAL-001` 행 | 검사 | 결과 |
|---|---:|---|
| 정식 fixture | `10/10` | PASS |
| 중복 이벤트 fixture | `10/10` | PASS |
| timeout fixture | `10/10` | PASS |
| 손상 저장 fixture | `10/10` | PASS |
| 프레젠테이션 불변조건 | `7/7` | PASS |
| **합계** | **`47/47`** | **PASS** |

저자 fixture `4/4` 모두 정확한 종료 상태 SHA-256
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`에 도달했다. 전체 표와
기계 판독 기록은 [`godot/docs/latest/evaluation-matrix.md`](godot/docs/latest/evaluation-matrix.md),
[`evaluation-matrix.json`](godot/docs/latest/evaluation-matrix.json)에 있다.

| 도착 | 보류 |
|---|---|
| ![Cycle 3 public-safe 도착](godot/docs/latest/arrival.png) | ![Cycle 3 public-safe 보류](godot/docs/latest/refusal.png) |
| 승인 단서 | 항로 획득 결말 |
| ![Cycle 3 public-safe 승인 단서](godot/docs/latest/authorized_hint.png) | ![Cycle 3 public-safe 결말](godot/docs/latest/ending.png) |

네 파일은 최신 1280×720 엔지니어링 작업 캡처이며 불변 Cycle 2 패킷이 아니다. Web과
`--public-safe`는 검토 대기 생성 후보를 제외하며 공개 빌드는 절차 지오메트리·VFX·UI·음향만
사용한다.

**주장 경계:** 저자 fixture와 프레젠테이션 불변조건 적합성만 다룬다. G4, 사용성, 몰입,
정서, 플레이어 효능, 모델 효능은 **UNASSESSED**다. G6는 포인터 잠금, save/reload,
warmed frame/input, 30분 soak 측정 전까지 `FIX`다.

프로젝트 루트에서 실행한다.

```bash
./scripts/build_godot_web.sh
python3 -m http.server 4173 --directory game-track/web/public
```

배포 상태: **[public-safe Vercel 빌드 공개](https://sealed-lighthouse-trace-rpg.vercel.app)**.
2026-08-17 headless 브라우저 스모크로 한글 표시, 데스크톱·협폭 반응형 배치, 콘솔·페이지 오류
0건을 확인했다. 포인터 잠금 진입은 **미검증**이다. 2026-08-17 재시험에서 headless 합성 클릭은
`pointerlockerror`를 냈고 실제 Chrome의 Playwriter 클릭은 포인터 잠금 요청 자체를 만들지
않았으며 두 실행 모두 `document.pointerLockElement`가 null이었다. HUD `시점 잠김`은 게임 자체
상태 표시이며 이 브라우저 검사를 대체하지 못한다. 자동화 거부만으로는 운영 결함 근거가 되지
않으며 사람 제스처 확인이 미해결 항목이다. 2026-08-17 Playwriter는 Vercel 기기 승인 로그인과
그 포인터 잠금 재시험에만 사용했다. 빌드·브라우저 스모크 상세: [`web/README.md`](web/README.md).

## 엔진 render-capture 근거

Cycle 2는 정식 저자 fixture를 별도 non-headless Godot pass로 렌더링한 1280×720 primary-track
패널 3개를 `SL-CAPTURE-001`로 등록한다.

| 패널 | 시점 | 파일 | 주장 한계 |
|---|---|---|---|
| `sl-rc-001-arrival` | 도착 관찰 | `sl-rc-001-arrival.png` | 저자 scene/state 대응 |
| `sl-rc-002-rejected-secret` | 공개 거절 | `sl-rc-002-rejected-secret.png` | 거절/fallback presentation 대응 |
| `sl-rc-003-authorized-hint` | 렌즈 설치 뒤 승인된 힌트 | `sl-rc-003-authorized-hint.png` | 승인 공개 presentation 대응 |

`SL-CAPTURE-001`은 엔진 manifest 필드가 아닌 논문 연결표 bundle label이며 manifest는 위
`sl-rc-*` capture ID 3개를 사용한다. 선택 불변 근거 세트 ID는
`godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`이다. v1--v4 패킷은 불변 보존하며
visual QA, toolchain provenance 결속, CI portability 수정을 거쳐 superseded 처리했다. v5
manifest는 capture pipeline, PNG decoder, schema, retained validator, dependency lock, capture
host tool version을 결속한다. 이 패널은 생성 콘셉트
아트가 아니라 구조화 상태/텍스트와 프로그램 방식 엔진 그래픽만 사용한다. 라이브 Python 권한,
모델·시각 효능, 사용성, 몰입, 인간연구 결과, G4 또는 G6를 입증하지 않는다.

![SL-CAPTURE-001 도착 관찰](../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-001-arrival.png)

![SL-CAPTURE-001 공개 거절](../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-002-rejected-secret.png)

![SL-CAPTURE-001 승인 힌트](../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-003-authorized-hint.png)

오프라인 재현 안내: [`recorded-experiment.ko.md`](recorded-experiment.ko.md)
