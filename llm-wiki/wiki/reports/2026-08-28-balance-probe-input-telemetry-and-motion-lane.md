# 밸런스 프로브·입력 텔레메트리·모션 레인 — 2026-08-28 확장 패스

Status: **ENGINEERING CONFORMANCE ONLY; NO HUMAN OR MODEL RESULT; G2/G3/G4/G6 REMAIN FIX**

2026-08-28 사용자 지시(AI 연구 + 게임이론·밸런스·재미 실험 중심 개발, Mixamo/Blender-MCP
리소스 파이프라인, UI·레이아웃·플레이 개선, 한글 우선 문서화)에 따라 결정 `D-037`–`D-039`로
기록된 확장 패스. 라이브 모델 호출과 이미지 생성 쿼터는 사용하지 않았다.

## D-037 — 입력→표시 텔레메트리와 9-검사 프레젠테이션 계약

- `configs/experimental-game.yaml`이 요구하지만 어떤 GDScript도 방출하지 않던
  `input_to_visible_feedback_ms`를 플레이어블 슬라이스에 배선했다: 상호작용/대화 선택 →
  제안 장부 라인 → 렌더된 프레임 경계(`RenderingServer.frame_post_draw`, headless는
  processed-frame 경계)에서 샘플을 기록하고 `--evaluate` 리포트의 `input_feedback` 블록으로
  내보낸다(공유 p95 규칙). headless 관측 샘플 ≈29 ms는 **배선 증거일 뿐** 브라우저/사용자
  제스처 지연 측정이 아니며 G4·G6의 ≤100 ms 조항은 여전히 실브라우저 측정을 요구한다.
- 데스크톱 와이드 레이아웃의 장부 앵커를 0.58 → 0.66으로 올려 플레이 필드 비중을 확보했고
  (`wide_layout_preserves_playfield` ≥ 0.65 검사), 검사 계약은 7 → 9개로 확장되어
  `SL-PLAY-EVAL-001`이 `47/47` → **`49/49`**가 되었다. 좁은 세로 화면 스택 레이아웃은 유지.

## D-038 — 아키타입 밸런스 프로브 `SL-BALANCE-PROBE-001`

- 새 headless 엔트리 `scenes/balance_probe.tscn` + `scripts/balance_probe_runner.gd`가
  QA 아키타입 5종(A-01 증거 우선, A-02 대화 우선, A-03 경계 시험, A-04 최단 경로,
  A-05 완전 탐사)을 동결된 기대값과 함께 canonical machine 위에서 실행한다.
  레이아웃·다음행동(어포던스) 매핑은 단일 소유자 `game3d/golden_path_layout.gd`로 이동해
  플레이어블과 프로브가 같은 정의를 쓴다.
- 측정(스크립트 적합성): 도달률 5/5(의미 상태 수렴), 금지 공개 커밋 0/3 기회, 보류 시 상태
  해시 불변 10/10, 연산 로그 재생 일치 5/5, 보류→다음 유효 행동 안내의 스크립트 추종 10/10,
  이동 근사 11.9–18.2 s(직선 하한; B-002 루프 60–120 s 대비 이동은 소수 비중).
- 구조적 발견 2건: `QUEST_STAGE_PRECONDITION`은 정상 연산 순서로 도달 불가(획득이 즉시
  스테이지 1로 상승 — 방어적 가드), `OBJECT_NOT_REACHABLE`은 정식 시나리오에 유발 상태 없음.
  기계 속성 2건: 중복 설치/중복 단서 재커밋은 revision만 증가(의미 상태 불변)하며 UI 가드로
  차단됨 — 영속 이벤트 멱등성(EG-I05)이 라이브 어댑터 전제임을 재확인.
- 산출물: `game-track/godot/docs/latest/balance-archetypes.{json,md,svg}`(한글 차트 포함),
  `scripts/run_balance_archetypes.py` 재검증 드라이버, pytest 5건 추가(스위트 45 tests).

## D-039 — 모션/리깅 반입 레인(Mixamo→Blender→Godot)

- `game-track/assets/motion/` 계약 신설: Mixamo 원본 FBX/DAE/BVH는 **git 추적·재배포 금지**
  (.gitignore 가드 + `validate_motion_assets.py` fail-closed, Adobe FAQ의 원본 재배포 금지
  반영), Blender/Blender-MCP 편집은 **스크래치 사본에서만**(무가드 코드 실행 경고), GLB
  산출물은 provenance 필수·`runtime_eligible: false` 기본, 승격은 D-035 큐레이션 방식.
- 조사 확정 사실: Higgsfield 공개 API(OpenAPI 50경로)에는 3D 엔드포인트가 없고 CLI 전용
  `multi_image_to_3d`는 무리깅 GLB만 생성(소품 후보 한정). Mixamo는 자동화 API가 없어 수동
  다운로드가 유일 경로. 공식 Blender MCP(projects.blender.org, 로컬 설치본 v1.0.0)는
  Blender ≥5.1 요구 — 로컬 Blender 5.1.2와 호환. Higgsfield 약관 페이지 404로 생성물의
  상업적 권리 미확인 상태 유지. 슬라이스에 스켈레탈 애니메이션 도입 여부 자체는 인터뷰
  항목으로 남김(현재 리그 0개).

## 정비·정정

- QA 게이트 문서의 캡처 4장 SHA-256과 Web PCK 등록값이 실제 파일과 어긋나 있던 드리프트를
  정정(캡처는 evaluation-matrix.json 값으로, PCK는 5,970,516 B `b97069…56eb`로).
- G2/G3를 `NOT_SCHEDULED`에서 **측정된 엔지니어링 수치 + FIX**로 갱신(스크립트 수치는
  게이트 통과 근거가 아님을 명시).
- 사고 기록: 진단용 비-headless 실행이 canonical `project.godot`를 에디터 서식으로 재작성 →
  증거 해시 검증기가 fail-closed로 차단, `git checkout`으로 원복. 샌드박스 셸은 GUI 창을
  열 수 없어 캡처 4장은 2026-08-21본 유지(0.66 레이아웃 반영 캡처 갱신은 GUI 세션 필요).

## Receipts

- `--smoke --public-safe` 8/8, 종료 해시 `4b2310…8892` 불변.
- `SL-PLAY-EVAL-001` 4/4 fixtures, `49/49` combined; `SL-BALANCE-PROBE-001` 5/5 PASS.
- `./scripts/validate_game_track.sh` 45 tests, 44 subtests(모션 가드·프로브 테스트 포함).

## Boundary

스크립트 아키타입은 사람 플레이어가 아니고, 이동 근사는 하한 프록시이며, headless 입력
샘플은 브라우저 지연이 아니다. `C-RESULT-001`–`005`는 `TODO-RESULT` 그대로이고 어떤 게이트도
PASS로 승격되지 않았다. 다음 실행 후보는 RQ2 라이브 파일럿(`CodexProposalAdapter` 구현,
승인 필요)과 사람 대상 G4/G6 측정이다.

Related: [[wiki/reports/2026-08-21-guided-repair-and-diegetic-ritual]],
[[wiki/reports/2026-08-13-trace-rpg-sealed-lighthouse-game-track]],
[[wiki/concepts/trace-rpg-controller]], [[maintenance-log]].
