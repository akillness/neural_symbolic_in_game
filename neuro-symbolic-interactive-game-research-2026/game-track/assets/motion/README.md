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

## Boundary (EN summary)

Staging lane only; zero assets today. Raw Mixamo FBX never enters git (Adobe forbids raw-file
redistribution). Blender MCP/headless edits operate on scratch copies only. Retargeted GLB needs
adjacent provenance with `runtime_eligible: false` until curated under the D-035 pattern. Nothing
here feeds the primary structured-state research track or upgrades any gate.
