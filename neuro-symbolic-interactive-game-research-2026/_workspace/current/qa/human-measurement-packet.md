# G4/G6 사람 측정 패킷 — Human Measurement Packet

```yaml
artifact_id: SL-HUMAN-MEASURE-001
status: READY-NOT-EXECUTED
prepared: 2026-08-28 (user request: "지금 준비해줘")
participant: 프로젝트 소유자 1인 (자기 측정; G4의 독립 참가자 연구를 대체하지 않음)
target_url: https://sealed-lighthouse-trace-rpg.vercel.app
build: dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW (index.pck 5,970,516 B, b97069…56eb)
```

이 패킷은 자동화가 대신할 수 없는 **사람 제스처 항목**을 소유자 1회 플레이로 닫기 위한
체크리스트다. 결과는 아래 보고 양식으로 남기면 되고, 기록되면 DEF-010(포인터록)과
G6의 save/reload 항목을 닫고 G6 성능 항목의 1차 실측이 된다.
(G4 몰입·가독성 게이트는 독립 참가자 프로토콜이 따로 필요하므로 이 패킷으로 닫히지 않는다.)

## A. 포인터록 사람 제스처 확인 (DEF-010, 약 2분)

1. 데스크톱 Chrome 일반 창(시크릿 아님)에서 위 URL 접속.
2. `조사 시작 — BEGIN` 버튼을 **마우스로 직접 클릭**.
3. 확인: 커서가 사라지고 마우스로 시점이 도는가? HUD 좌상단이 `시점 잠김 · LOOK ACTIVE`인가?
4. `Esc` → 커서 복귀 확인 → 화면 클릭 → 재잠김 확인.
5. (선택) DevTools 콘솔에 `document.pointerLockElement` 입력 — canvas 요소가 나오면 확정.

보고: 잠김 성공 여부 / 재잠김 성공 여부 / 콘솔 값.

## B. 저장·복원 왕복 (G6 save/reload, 약 2분)

1. 렌즈 획득(기록 #1) 후 `F5` 저장 — "저장됨 — 상태 해시 …" 토스트 확인.
2. 렌즈 설치(기록 #2)까지 진행 후 `F9` 복원 — "불러옴 — 손상 검사 통과." 확인.
3. 확인: 상태가 기록 #1 직후로 돌아갔는가(목표 문구·소지품·기록 수)?
4. 페이지 새로고침 후 `F9` — 브라우저 재시작 간 저장이 유지되는가?

보고: 각 단계 토스트 문구 / 복원 후 기록·보류 카운트.

## C. 입력→화면 반응 체감 + 실측 (G4/G6 ≤100 ms, 약 5분)

1. 에피소드를 처음부터 끝까지 1회 플레이(8–12분 목표 대비 실제 소요를 메모).
2. 상호작용 `E` 를 누를 때 장부 반응이 즉각적인지 체감 메모(지연·끊김 있으면 위치 기록).
3. 실측(선택, 권장): DevTools → Performance → Record 상태에서 `E` 상호작용 3회 →
   기록 중지 → `keydown` 이벤트에서 다음 화면 페인트까지 간격을 3건 읽어 적기.
   (초고속 카메라 방식보다 이 방법이 간단하고 충분하다.)

보고: 체감 평가(즉각/보통/지연) / 실측 3건 ms / 에피소드 소요 시간 / 기록·보류 최종 수.

## D. 30분 메모리 소크 (G6 soak, 백그라운드 30분)

1. 게임을 켠 채 30분 방치(중간에 2–3회만 이동/상호작용).
2. 시작 직후와 30분 후에 DevTools → Memory 또는 작업관리자(Shift+Esc)에서
   탭 메모리 값을 각각 기록.
3. 확인: 지속 상승 추세인가, 안정인가.

보고: 시작 MB / 30분 후 MB / 프레임 끊김 체감 여부.

## 보고 양식 (이 파일 하단에 추가하거나 채팅으로)

```yaml
executed_utc: 
browser_and_version: 
A_pointer_lock: {locked: , relocked: , pointerLockElement: }
B_save_reload: {save_toast: , load_toast: , state_rolled_back: , survives_refresh: }
C_input: {feel: , measured_ms: [ , , ], episode_minutes: , commits: , refusals: }
D_soak: {start_mb: , end_mb: , stutter: }
```

기록이 도착하면: DEF-010 종결, G6의 save/reload·입력 항목 갱신, gate-measurements에
사람 제스처 실측으로 반영한다. 남는 G6 항목은 warmed frame p95/long-frame(브라우저
프로파일 세션)과 rollback drill이다.
