# 플레이어 리그 레인 (D-046) — 로컬 전용, 추적 안 함

이 디렉터리의 **모델 바이트는 git에 절대 들어가지 않는다.** Mixamo(Adobe) 약관이 원본
캐릭터·애니메이션 파일의 재배포를 금지하고 이 저장소는 공개이기 때문이다. 이 README만 추적된다.

## 쓰는 법

1. 본인 Adobe 계정으로 Mixamo에서 리그된 캐릭터(+애니메이션)를 FBX로 받는다.
2. 이 디렉터리에 넣는다: `game-track/godot/assets/rig/<이름>.fbx`
3. Godot가 임포트하면(`--import`) 플레이어가 절차적 캡슐 대신 그 리그를 쓴다.
4. 검증: `uv run python scripts/verify_motion_ingest.py game-track/godot/assets/rig/<이름>.fbx`

## 경계

- **웹/`--public-safe` 실행은 이 레인을 로드하지 않는다**(`load_player_rig()` 가드).
  `build_godot_web.sh`도 스테이징에서 이 디렉터리를 제외하므로 PCK에 들어가지 않는다.
- 리그는 **연출 전용**이다. 이동·포커스·모든 세계 변경은 여전히 같은 제안 경로를 지나며,
  정식 상태(canonical state)는 리그를 보지 않는다. 종료 상태 해시는 리그 유무와 무관하게
  동일해야 한다.
- 레인이 비어 있으면 현재 공개 빌드는 별도 D-050 큐레이션 플레이어를 우선 사용한다.
  해당 자산이 없거나 검증에 실패할 때 절차적 캡슐이 fail-safe fallback으로 쓰인다.
