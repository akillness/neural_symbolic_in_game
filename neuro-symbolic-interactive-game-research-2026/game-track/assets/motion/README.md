# 모션/리깅 자산 반입 레인 — Motion & Rig Intake Lane (D-039)

이 디렉터리는 캐릭터 리그·모션 자산의 **스테이징 레인**이다. 현재는 계약과 검증기만 존재하며
자산은 0개다. 반입 전 이 문서 전체가 적용된다.

## 소스별 규칙

| 소스 | 허용 형태 | 금지 |
|---|---|---|
| Mixamo (Adobe) | 수동 브라우저 다운로드 → **로컬 보관** → Blender 재처리 → GLB 산출물만 검토 대상 | 원본 `.fbx`/`.dae`의 저장소 커밋·재배포·에셋팩 포함·ML 학습 사용. Adobe FAQ가 원본 파일 재배포를 금지한다 |
| Higgsfield `multi_image_to_3d` | 정적 무리깅 GLB(소품/환경 후보만) | 리깅 캐릭터로 오인 표기, 권리 확인 전 공개 빌드 포함(약관 페이지 404 상태 기록됨) |
| Blender 자체 제작 | GLB + 생성 스크립트 보존 권장 | 스크립트 미보존 시 "정확 재생성 가능" 주장 |

## 처리 파이프라인 (승인된 형태)

1. **원본 보관**: Mixamo FBX는 `game-track/assets/motion/raw/`(gitignore됨)에만 둔다.
2. **Blender 편집**: 반드시 **스크래치 복사본**에서 작업한다. Blender MCP(`execute_blender_code`)는
   LLM 코드를 무가드로 실행하므로 원본·불변 증거 디렉터리를 절대 열지 않는다.
   headless CLI(`Blender --background --python`) 경로도 동일 규칙.
3. **Godot 반입**: GLB로 내보내 Godot 4.x `BoneMap` + `SkeletonProfileHumanoid`로 리타게팅한다.
   루트 모션이 필요하면 임포트 옵션 `Unimportant Positions`를 **꺼야** 한다(기본 ON이면 Hips 외
   위치 트랙이 조용히 제거된다).
4. **provenance**: 산출 GLB마다 인접 `<name>.provenance.json`을 둔다. 필수 필드는
   `validate_motion_assets.py` 참조. 생성 시점 `runtime_eligible`은 항상 `false`.
5. **큐레이션**: 런타임 승격은 D-035와 동일하게 명시적 사용자 지시를 인용하는 `curation.json`
   추가 후에만 가능하며, 공개 빌드는 자산 부재 시에도 완전 동작해야 한다(절차적 폴백).

## 경계

- 이 레인의 어떤 자산도 1차 확증 실험 트랙의 입력이 아니다(구조화 상태/텍스트가 1차).
- 리타게팅 결과물은 연출 자산이며 G4/G6/효능 근거가 아니다.
- 현재 슬라이스에는 스켈레탈 애니메이션이 없다. 도입은 별도 결정(플레이어/미라 리그)과
  인터뷰 확인 후 진행한다.

## 실행 기록 — 2026-08-28 (D-045: 취득 성공, Blender 불필요 확인)

사용자가 Adobe/Google 소셜 로그인으로 Mixamo 세션을 열어 자산 취득 차단이 해소됐고,
실제로 받아서 검증했다. 그 과정에서 **이 레인의 전제 하나가 틀렸음**이 드러났다.

### 정정: 직선 반입에는 Blender가 필요 없다

이 문서는 원래 Mixamo → Blender → GLB → Godot 경로를 전제했다. 실측 결과 **Godot 4.7.1이
FBX를 네이티브(ufbx)로 직접 임포트**하며, Blender를 거치지 않아도 스켈레톤과 애니메이션이
그대로 만들어진다. 측정값(`Peasant Man` + `Breathing Idle`, 4,172,928 B):

- `Skeleton3D` 1개, **본 43개**
- `AnimationPlayer` 1개, 애니메이션 `mixamo_com`
- `MeshInstance3D` 1개

재현: `uv run python scripts/verify_motion_ingest.py <파일>`.
따라서 Blender는 **선택**이며, 다른 스켈레톤으로 리타게팅하거나 메시를 편집할 때만 필요하다.
(이 세션의 샌드박스에서는 Blender가 파이썬 실행 중 `MTLBackend::metal_is_supported()`에서
크래시하고 이 빌드의 `--gpu-backend`는 유효값이 `metal` 뿐이라 우회가 없었다. 다만 기존 GLB
5종은 과거에 Blender로 만들어졌으므로 세션 의존 현상으로 보고 재판정 대상으로 남긴다.)

### 자산 바이트는 의도적으로 커밋하지 않는다

Adobe 약관이 원본 캐릭터·애니메이션 파일의 재배포를 금지하고 이 저장소는 공개이므로,
받은 FBX는 `raw/`(gitignore)에 두고 **바이트 대신 반입 레시피와 프로븐어런스만** 추적한다:
`ingest-verification.json`이 소스 해시·크기·임포트 결과를 담고, `verify_motion_ingest.py`가
누구든 자기가 받은 파일로 같은 검증을 재현하게 한다.

### 남은 단계

런타임 도입(플레이어 캐릭터 교체, 이동 상태와 애니메이션 연결)은 **연출 결정**이라 별도
승인이 필요하다. 현재 슬라이스는 절차적 캐릭터로 동작하며 이 레인은 아직 런타임에 연결되지
않았다.

## Boundary (EN summary)

Staging lane only; zero assets today. Raw Mixamo FBX never enters git (Adobe forbids raw-file
redistribution). Blender MCP/headless edits operate on scratch copies only. Retargeted GLB needs
adjacent provenance with `runtime_eligible: false` until curated under the D-035 pattern. Nothing
here feeds the primary structured-state research track or upgrades any gate.
