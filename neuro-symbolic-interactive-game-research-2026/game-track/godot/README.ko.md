# 봉인된 등대 — Godot 적합성·플레이어블·캡처·Web pass

상태: **Cycle 2 불변 v5를 유지하고 Cycle 3 public-safe 평가는 fixture `4/4`, 합계 `49/49`
검사를 통과했다. 아키타입 밸런스 프로브 `SL-BALANCE-PROBE-001`은 5/5 통과했고, 프로덕션
배포 `dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y`에 영문 추적 플레이어 산출물이 공개됐다.**

이 Godot 4.x 프로젝트는 논문에서 인용할 수 있도록 설계한 결정론적 마이크로 RPG
fixture다. 연구 런타임을 엔진에 내장하지 않고 엔진 로컬 저자 정책 미러를 실행한다. 지원
이벤트는 안정 브리지 envelope projection 검사를 통과하지만 라이브 Python 권한 왕복은
실행하지 않았다.

render-capture 진입점은 headless 적합성 runner와 의도적으로 분리된다. presentation 근거를
위해 동결된 정식 시점을 재생하고 실제 렌더 프레임을 기다린 뒤, 등록 PNG 3개와 source/render
메타데이터를 쓴다. action을 승인하거나 canonical state를 변경하지 않는다.

## 시나리오 경로

| 턴 | 플레이어/시스템 행동 | 하드 정책 결과 | 정규 상태 |
|---:|---|---|---|
| 0 | 꺼진 등대와 접근 가능한 등구점을 관찰 | 관찰 전용 | 불변 |
| 1 | 접근 가능한 신호 렌즈 획득 | 유효 commit | 인벤토리 변경, 퀘스트 1단계 |
| 2 | Captain Mira에게 미래의 배신 비밀과 잠긴 힌트 요청 | `FORBIDDEN_DISCLOSURE` + `STAGE_GATED_DISCLOSURE` | 안전 fallback, 불변 |
| 3 | 신호 렌즈 설치 | 유효 commit | 퀘스트 2단계, 힌트 승인 |
| 4 | 선택적 중복 ID 또는 timeout 주입 | 멱등 무시 또는 안전 fallback | 불변 |
| 5 | 승인된 조수 흔적 힌트 요청 | 유효 commit | 힌트 공개, 관계 기억 추가 |
| 6–8 | 저장, 불러오기, replay | 해시 비교 | 종료 해시 일치 필요 |

동결된 예상 종료 상태 해시는
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`다.
이는 정규 JSON의 비밀키 없는 SHA-256 무결성 checksum이며 인증 수단이 아니다.
fixture는 이를 `python-independent-sealed-lighthouse-v1` oracle로 명시한다. Python 테스트는
GDScript와 독립적으로 같은 종료 상태 projection을 계산한다. 관측된 Godot fixture 실행 4종은 모두
그 해시와 일치했다.

## Godot 4.x에서 실행

저장소 프로젝트 루트에서 다음을 실행한다.

```bash
PROJECT_ROOT="$(pwd)"
GODOT_BIN="/absolute/path/to/godot4"
OUTPUT_DIR="/tmp/trace-rpg-godot-canonical"
"$GODOT_BIN" --headless --path "$PROJECT_ROOT/game-track/godot" --quit-after 120 -- \
  --fixture="$PROJECT_ROOT/data/fixtures/experimental-game-canonical.json" \
  --output="$OUTPUT_DIR"
```

결함 주입에는 fixture를 `experimental-game-duplicate-event.json`,
`experimental-game-timeout.json`, `experimental-game-corrupt-save.json` 중 하나로 교체한다.
정상 종료한 엔진 실행은 다음을 쓴다.

- `events.jsonl`: 모든 이벤트의 제안·근거·검증·수리·commit, 모델 revision, seed, 비용,
  지연시간, 변경 전후 상태 해시
- `save.json`: 버전 지정 저장 문서와 상태 해시
- `summary.json`: 엔진 버전, replay/저장 검사, 결함 수, 시간 표본

`OBSERVED_ENGINE_RUN` 표시는 실제 Godot 프로세스가 summary를 만들 때만 기록된다. 정적
테스트는 엔진 결과를 대신 만들지 않는다.

## 계약 검증

```bash
.venv/bin/python -m pytest -q tests/test_godot_experimental_game.py
ruff check tests/test_godot_experimental_game.py
```

Godot 4.x가 없으면 정적 계약 테스트가 통과하고 엔진 테스트는 명시적 사유와 함께
skip된다. Godot이 있으면 동일 테스트가 네 fixture를 모두 실행하고 이벤트·저장·요약을
JSON Schema로 검증한다.

2026-08-13 권위 보존 근거 세트는
`../../_workspace/current/engineering/tech-verification/current.json`이 지정하며 현재
`evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/`로 해석된다. 정식,
중복 ID, timeout, 손상 저장 실행은 각각 commit 3회를 수행하고 동결 종료/oracle 해시에
도달했으며, 손상 저장 probe는 live state mutation 전에 거절됐다. 선택된 보존 Cycle 2
packet은 `40 tests, 44 subtests`를 기록하고, 현재 game-track gate는 `46 passed, 2 skipped`를
기록한다. 성능 budget은 모두 통과하지 않았다. 시작 transient를
포함한 5개 표본의 헤드리스 frame p95는 선택 보존 패킷에서 각각 `116.667`, `100.000`,
`98.760`, `112.907 ms`다.

## Non-headless capture 패킷

Cycle 2는 선택 불변 근거 세트
`godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5`의 논문 label을
`SL-CAPTURE-001`로 기록한다. 불변 v1--v4 패킷은 보존하며 clipping, top margin, status
contrast, toolchain provenance, CI portability 검토를 거쳐 superseded 처리했다. v5 primary
구조화 상태 패널은 다음과 같다.

| 패널 | source 시점 | 파일 |
|---|---|---|
| `sl-rc-001-arrival` | 도착 관찰 | `sl-rc-001-arrival.png` |
| `sl-rc-002-rejected-secret` | 조기 공개 거절과 fallback | `sl-rc-002-rejected-secret.png` |
| `sl-rc-003-authorized-hint` | 렌즈 설치 뒤 승인된 힌트 | `sl-rc-003-authorized-hint.png` |

승격에는 non-headless display driver, 렌더 프레임 동기화, 정확한 1280×720 크기,
non-blank/opacity 검사, 파일 byte/SHA-256, source fixture·run·event/state 시점·source hash 결속이
필요하다. primary 패킷에는 생성 콘셉트 asset이 없다.
v5 manifest는 capture pipeline, PNG decoder, capture schema, retained validator, `uv.lock`의
hash와 Python `3.13.9`, jsonschema `4.26.0`, JSON Schema Draft 2020-12를 추가로 기록한다.
verifier는 지원되는 다른 Python 버전에서도 실행할 수 있으며, 기록된 capture 환경을 검증하되
동일 host라고 가장하지 않는다.

![도착 관찰](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-001-arrival.png)

![공개 거절](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-002-rejected-secret.png)

![승인 힌트](../../_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20260813t115916z-sealed-lighthouse-render-v5/rendered-canonical-v1/sl-rc-003-authorized-hint.png)

## 3D 연출 슬라이스 (`scenes/main_3d.tscn`)

`scripts/game3d/`는 동일한 저자 정책 미러(`sealed_lighthouse_machine.gd`)를 유일한 정식 상태
저자[OBSERVED]로 사용하는 플레이 가능한 3D 연출 슬라이스다. 부두·램프 상점·해상 등대
실루엣·폭풍 날씨를 절차적으로 구성하고, SL-PRESENT-001 비트(P-B01~P-B06)와 B-011 긴장 곡선
`0.35→0.72→0.50`을 프레젠테이션 계층에서만 구동한다. 제안→커밋/보류 라우팅은 라이브 플레이와
스모크 스윕이 같은 코드 경로를 쓴다.

```bash
# 아래 모든 Godot 명령은 game-track/godot이 아닌 임시 import 복사본만 대상으로 한다.
STAGED_GODOT_PROJECT=/tmp/sl3d-disposable-project

# 플레이 (WASD, 마우스 시점, E, F5/F9, M 모션 감소, V 음향, T 안내)
godot --path "$STAGED_GODOT_PROJECT" res://scenes/main_3d.tscn

# Public-safe 헤드리스 스모크 (거절 불변·단계 게이트·손상 저장 거절 8종)
godot --headless --path "$STAGED_GODOT_PROJECT" res://scenes/main_3d.tscn -- --smoke --public-safe

# 임시 fixture + 프레젠테이션 매트릭스 (엔지니어링 전용)
python3 scripts/run_playable_evaluation.py --godot /path/to/Godot

# 큐레이션된 공개 플레이어 자산·출처·클립 계약
python3 scripts/validate_player_asset.py

# 개발용 검증 샷 (GUI host 전용, 이 sandbox에서는 불가, 승격 불가)
godot --path "$STAGED_GODOT_PROJECT" res://scenes/main_3d.tscn -- \
  --shot /tmp/sl3d-shot.png --shot-stage arrival --public-safe
```

스모크 스윕 8검사는 2026-08-30 Godot 4.7.1에서 다시 통과했고 종료 상태 해시는 동결 해시
`4b2310…8892`와 일치한다. 기존 프레젠테이션 검사는 활성화된 `BoxShape3D`가 보이는
렌즈 접근 덱과 일치하고 `GoldenPathLayout`의 앵커를 포함하며 부두와 겹치고 램프 상점 벽을
감싸는지도 확인한다. 이는 DEF-021의 공학 결함만 닫으며 사람의 길찾기 성공을 주장하지 않는다.
Godot을 사용할 수 있는 로컬 테스트는 disposable copy에서 이 스모크를 실행한다.
Web과 `--public-safe`는 `../assets/concepts/` 및
`../assets/concepts/pack-3d/`의 검토 대기 후보를 로드하지 않는다. 대신 별도 큐레이션 UI
lane과 추적 대상 `assets/player/higgsfield-player.glb`의 `Idle`/`Casual_Walk`을 절차 월드·VFX·
음향 위에 사용한다. 플레이어 외형과 클립 상태는 정식 상태나 저장 데이터에 들어가지 않는다.
검토 대기 콘셉트 후보의 공개 승격에는 계속 사람 권리·스타일 검토가 필요하다.

## Cycle 3 평가 매트릭스와 최신 작업 캡처

| `SL-PLAY-EVAL-001` 행 | 검사 | 결과 |
|---|---:|---|
| 정식 fixture | `10/10` | PASS |
| 중복 이벤트 fixture | `10/10` | PASS |
| timeout fixture | `10/10` | PASS |
| 손상 저장 fixture | `10/10` | PASS |
| 프레젠테이션 불변조건 | `9/9` | PASS |
| **합계** | **`49/49`** | **PASS** |
| 아키타입 밸런스 프로브 | `SL-BALANCE-PROBE-001` 5/5 | PASS |

fixture `4/4` 모두 정확한 종료 SHA-256
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`에 도달했다.
[전체 매트릭스](docs/latest/evaluation-matrix.md), [JSON 매트릭스](docs/latest/evaluation-matrix.json),
[원시 프레젠테이션 평가](docs/latest/presentation-evaluation.json)를 확인할 수 있다.

| 도착 | 보류 |
|---|---|
| ![Cycle 3 public-safe 도착](docs/latest/arrival.png) | ![Cycle 3 public-safe 보류](docs/latest/refusal.png) |
| 승인 단서 | 항로 획득 결말 |
| ![Cycle 3 public-safe 승인 단서](docs/latest/authorized_hint.png) | ![Cycle 3 public-safe 결말](docs/latest/ending.png) |

네 1280×720 PNG는 이 샌드박스에서 Godot `--shot` 렌더가 불가능해 임시 Web stage와 브라우저로
생성한 최신 엔지니어링 작업 캡처다. 캡처 전용 query hook은 추적 source에 들어가지 않았다.
불변 v5 패킷을 대체하거나 수정하지 않는다.

현재 전체 경로 플레이 영상: **[Compresso 압축 H.264 MP4](docs/latest/trace-rpg-gameplay.mp4)**
(`1280×720`, 30 fps, 69.067초, 5,662,128바이트, SHA-256
`aa374c5aa9d03e0ab2822b83638e4c6645c7c9fda6c07e858051254c244b7044`). 아래 배포와 바이트가
일치하는 로컬 빌드에서 캡처한 엔지니어링 시연이다.

## Public-safe Web 산출물 빌드

저장소 프로젝트 루트에서 실행한다.

```bash
./scripts/build_godot_web.sh
python3 -m http.server 4173 --directory game-track/web/public
```

빌더는 Godot 프로젝트를 임시 디렉터리로 복사하고 그 복사본에서만 `main_3d.tscn`을 선택한다.
단일 스레드·확장 비활성 Web preset을 사용하며 정식 `project.godot`은 변경하지 않는다. 근거
결속된 실제 프로젝트에는 Godot editor/import를 실행하지 않는다. 2026-08-30 무시 대상
산출물은 manifest 파일 11개, 50,745,187바이트이며 `index.pck`은 10,892,412바이트, SHA-256
`29e3d8b6b898482fb1a7979966cf1acec88caf7578a26398e889fc7af10f8f76`이다. 이 산출물은
**[Vercel `dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y`](https://sealed-lighthouse-trace-rpg.vercel.app)**에
배포됐다. 공개 런타임 파일 10개는 모두 `200`이며 로컬 바이트와 일치했고 `vercel.json`은
배포 설정으로 소비됐다. 프로덕션 데스크톱 스모크는 시작 → 인게임 → Field Guide 전환과
콘솔·페이지 오류 0건을 확인했다. 2026-08-17의 과거 headless 브라우저 스모크는 한글 표시,
1280×720·390×844 반응형 배치, 콘솔·페이지 오류 0건을 확인했다. 포인터 잠금 진입은 **미검증**이다. 2026-08-17 재시험에서 headless 합성 클릭은
`pointerlockerror`를 냈고 실제 Chrome의 Playwriter 클릭은 포인터 잠금 요청 자체를 만들지
않았으며 두 실행 모두 `document.pointerLockElement`가 null이었다. HUD `시점 잠김`은 게임 자체
상태 표시이며 이 브라우저 검사를 대체하지 못한다. 자동화 거부만으로는 운영 결함 근거가 되지
않으며 사람 제스처 확인이 미해결 항목이다. 2026-08-17 Playwriter는 Vercel 기기 승인 로그인과
그 포인터 잠금 재시험에만 사용했다. 상세 내용은 [`../web/README.md`](../web/README.md)에 있다.

**Cycle 3 주장 경계:** 저자 fixture와 프레젠테이션 불변조건 엔지니어링 적합성만 다룬다.
G4, 사용성, 몰입, 정서, 플레이어 효능, 모델 효능은 **UNASSESSED**다. G6는 프로덕션
save/reload, 현 배포 모바일 검증, 사람 포인터/음향 확인, warmed frame/input, 30분 soak,
rollback 근거가 없어 `FIX`다.

## 온보딩 증거철과 엔진 밖 소프트 제안 채널 (2026-08-18)

- 영문 `[T]` 증거철 안내 3면(조작 -> 장부 문법 -> 실험 연결)이 첫 실행 시 자동으로 열리고
  이후 `[T]`로 재열람, `[Esc]`로 닫힌다. 사용자 큐레이션 Higgsfield 삽화는 `assets/ui/`로
  공개 빌드에 포함된다. 이를 지워도 이미지 슬롯만 숨고 문안과 절차 fallback은 완전하게 남는다.
  검토 대기 콘셉트 팩 바이트는 계속 제외한다.
- 첫 커밋·첫 보류에 일회성 설명 토스트가 붙어 "검증 통과만 상태를 바꾼다 / 보류는 상태를
  보존한다"를 즉시 전달한다. 렌즈를 들면 행동 패널에 아이콘 칩이 뜬다.
- LLM은 엔진 밖에만 있다. `scripts/soft_proposal_policy.py`가 프롬프트용 모델 가시 투영을
  만들고 회신에 봉인·단계 미달 식별자가 표면화됐는지 렉시컬 스크린으로 표시한다
  (`--projection`, `--proposal`). 스크린은 사전 필터이며 의미 오라클이 아니다.

## 증거 경계

보존 산출물은 Stage 6 M6의 설계 fixture 엔진 로컬 정책 미러 근거를 제공한다. 런타임 간 통합
논문 승격 전에는 라이브 Python 권한 왕복이 필요하다.
이 프로젝트는 모델 우월성, 플레이어 효용, 의미 oracle 완전성, 시각 품질, 상용 엔진
이식성을 측정하지 않는다. timeout과 중복 ID fixture는 설계된 결함 경로이며 모집단
오류율 추정치가 아니다.
중복 억제는 이 슬라이스의 단일 프로세스 메모리 안에서만 보장된다. 실제 adapter 승인
전에는 프로세스 간 영속 멱등성 저장소가 추가되어야 한다.
PNG는 저자 엔진 render/state 대응 근거만 추가한다. 시각 품질, 사용성, 몰입, input latency,
성능, 플레이어 효용, 의미 oracle, G4 또는 G6 근거를 추가하지 않는다.
