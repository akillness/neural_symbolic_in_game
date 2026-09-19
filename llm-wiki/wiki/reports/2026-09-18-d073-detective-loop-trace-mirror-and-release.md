# D-073 — 탐정 루프 심화, 해시 고정 평가-트레이스 미러, Higgsfield case-v1 팩, 프로덕션 배포 — 2026-09-18

Status: **ENGINEERING PASS ONLY; NO HUMAN OR MODEL RESULT; C-RESULT-001–005 REMAIN UNESTABLISHED; G4/G6 REMAIN FIX**

2026-09-18 사용자 지시(힉스필드로 리소스·모션·프리팹·맵 구성·VFX를 업데이트해 적용하고 빌드·배포까지; 그래프의
흐름 근거가 정확히 동작하도록 Aside 딥리서치로 개선; 추리 게임 요소를 디벨롭해 튜토리얼식 안내를 강화하고
화면 구성이 잘 보이도록 UI/UX 개선; 깃 푸시)에 따라 결정 `D-073`으로 기록한 패스. 세 개의 동시 세션이
같은 worktree에 있었고(`_workspace/current/conflicts.md` 2026-09-18 항목), 2026-09-03의 stale D-069 lock은
기록 후 인수했다.

## 1. Aside 딥리서치 (intake, [INFERENCE])

- `_workspace/current/intake/aside-research-2026-09-18-commit-gate-trace-encoding.md`: W3C PROV-DM의
  plan/activity 분리, JSON Schema 2020-12의 "evaluated" 의미론, OpenTelemetry `Unset` 함정, SMT-LIB/xclingo/
  NeMo Guardrails의 부분 평가 표기, WCAG 1.4.1/1.4.11, Datawrapper 해칭 패턴. 결론: 여섯 계열 모두에
  명시적 상태(pass/fail/skipped/out_of_scope)를 부여하고 기본값을 두지 않으며, 통과는 파랑, 실패는 코랄,
  미도달은 점선, 범위 밖은 해칭으로 단어·기호와 함께 인코딩; 단락 규칙은 명시 필드로 렌더링.
- `_workspace/current/intake/aside-research-2026-09-18-detective-tutorial-hud.md`: Obra Dinn/Golden Idol/
  Shadows of Doubt 개발 기록, CHI PLAY 2024·IUI 2025·arXiv 2403.10272(4E 모델), NN/g 온보딩, Xbox
  Accessibility Guideline 115, WCAG 2.2, Godot 다중 해상도 문서. 결론: 객관식 결론은 안티패턴이므로
  슬롯 조립 추리; 보류 행은 `PROPOSAL → RULE → WHAT THAT TELLS YOU`; 시작 folio는 1페이지만, 나머지는
  적시 코치 카드; 네 개의 고정 HUD 존; 24/20/22 px 타입 하한.

## 2. 그래프 흐름 근거: 해시 고정 평가-트레이스 미러

- `sealed_lighthouse_machine.gd`는 불변 엔진 증거(`software.machine_sha256 = cc531b6b…`)에 바이트
  고정되어 있어 수정하지 않았다. 대신 `game3d/evaluation_trace.gd`(`EvaluationTrace`)가 같은 시나리오와
  커밋 전 상태로 기계의 검사 순서·결과를 재구성하고, 재구성한 실패 집합이 기계가 반환한 코드와 같을 때만
  `consistent: true`로 보고한다(다르면 family state를 비우고 대시보드가 "state missing"으로 그린다).
  `tests/test_evaluation_trace_mirror.py`가 미러의 pin 해시·검사 순서·컨트롤러 배선을 고정한다.
- `game_3d.gd::dashboard_trace(trace, plan, consistent)`는 여섯 계열 각각에 한 상태만 부여하고
  `held_at`/`short_circuit`/`skipped`/`out_of_scope`를 명시한다. 복합 게이트(`DISCLOSURE/QUEST STAGE`)
  실패는 두 계열 모두 `fail`(D-072의 holds-by-gate 집계와 동일 규칙).
- `web/dashboard/dashboard.js`는 `family_states`만으로 노드를 그리고(파랑 pass·코랄 fail·점선 skipped·
  해칭 not evaluated·앰버 state missing), 실제 통과한 엣지만 애니메이션하며, 이벤트마다 범례를 생성하고
  순서대로 검사 행과 단락 규칙을 출력한다. 경계 문구는 SVG 안에 있다. `trace`가 없는 구형 봉투는
  `legacy: schema-only`로 표기된다. 고정 fixture 8종 + 가드 2종이 일반/reduced-motion 두 패스에서 통과
  (`qa/releases/2026-09-18/dashboard-trace-fixtures.json`).

## 3. 탐정 루프·안내·화면 구성

- 증거판 `[C]`(LENS/MOUNT/LEAD/SEALED, `FACT_LABEL`만 통과; SEALED 카드는 사실을 이름하지 않음; 커밋마다
  unread pip), `INFERENCE_BY_CODE` 세 번째 줄, `[H]` 3단 힌트 사다리(3단 = `next_affordance`, 안내 궤적
  토글), 시작 folio 1페이지 + 첫 커밋/첫 보류/첫 렌즈 소지 시 코치 카드, 조수위 표식에서의 슬롯 조립
  추리(`deduction_is_supported`는 커밋 사실의 순수 읽기; 제안이 아니며 hold/commit 이벤트를 내지 않음),
  3페이지 엔드카드(복사 가능한 해시), 네 개의 고정 HUD 존. 임베드(713×720) 검증에서 코치 카드가 독에
  가려지는 결함과 선택지 2/4만 보이던 결함, 대화 경로 보류 후 HOLDS 카운트가 멈추던 결함을 배포 전에
  수정했다.
- 평가 계약: `--evaluate`는 16개 검사(동결된 core 12 + D-073 확장 4). `SL-PLAY-EVAL-001`은 논문이
  인용하는 core 52/52를 그대로 유지하고 확장 4/4를 별도 집계한다(전체 56/56). 네 장의 작업 캡처를
  네이티브 `--capture` 경로로 갱신했다.

## 4. 월드·VFX·모션·에셋

- 스테이션: 램프 창고 간판+상자, 신호 마운트 플랫폼, 조수위 표식 기둥, 미라의 증거 책상(Higgsfield GLB,
  없으면 절차적 책상). 안내 궤적(힌트 3단 또는 보류 후 6초), 포커스 링 호흡, 관찰 스파클, 책상 정착 광,
  커밋 FOV 넛지, 리그 제스처 클립(Collect/Observe/Speak; 없으면 무시). 예산 내(추가 광원 0).
- Higgsfield case-v1: 이미지 작업 9건(1회 재시도) + `multi_image_to_3d` 1건. 큐레이션 PNG 7장
  3,479,586 B, `evidence_desk.glb` 516,268 B(텍스처 1024 px 재임베드, 기하 바이트 동일; 4,794 삼각형).
  프롬프트·provenance·매니페스트·curation 기록.

## 5. 검증과 배포

- 스모크 8/8, 종단 SHA-256 `4b2310…8892`, canonical `project.godot` `2e7966…9edd` 불변; `--evaluate`
  16/16; 런타임 오류 0; `./scripts/verify_like_ci.sh` 전 단계 PASS(게임 트랙 52 tests / 48 subtests).
- 로컬·프로덕션 브라우저 walk(unpatched chrome-headless-shell 148, SwiftShader WebGL2): 실제
  early-secret 보류·stage-gated 보류·렌즈 커밋 트레이스가 올바른 skipped/out-of-scope 계열로 렌더링되고
  해시 체인 `f488d9c4… → 19b474dc…`가 이어졌다. 알려진 자동화 전용 pointer-lock 진단 1건만 남는다.
- 프로덕션 `dpl_BkguPJPErtawmhjxU5cvg97PBsiq` READY (`https://sealed-lighthouse-trace-rpg.vercel.app`):
  16 파일 56,003,696 B 바이트 일치(PCK 13,312,496 B), `/` → `/dashboard/`, `/paper/{en,ko}.pdf`, 390 px
  가로 넘침 없음. 영수증: `_workspace/current/qa/releases/2026-09-18/`.

## Boundary

이 패스의 모든 수치는 엔지니어링 적합성이다. 사용성·몰입·재미·효능·G4·G6 근거가 아니며, `C-RESULT-001`–
`005`는 `TODO-RESULT` 그대로다. 논문 원고는 수정하지 않았고 ENG1 헤드라인 52/52는 문자 그대로 참이다.

Related: [[wiki/reports/2026-09-06-paper-game-factcheck-and-release]],
[[wiki/reports/2026-09-18-aside-evidence-review-game-paper]], [[wiki/concepts/trace-rpg-controller]],
[[wiki/concepts/evidence-and-claim-status]], [[maintenance-log]].

## 6. D-074 후속 (2026-09-19) — 게임성·논문 내용 검증과 디벨롭

- 게임성 검증: `SL-BALANCE-PROBE-001` 5/5(보류 격리 10/10); headless `--autoplay` 골든 패스가 슬롯 조립
  추리를 거쳐 `episode_over`(commit 3 / hold 1, 종단 `4b2310…8892`); Movie Maker 재녹화(76.3 s MP4,
  1.5× GIF, 일회용 사본); 713×720 임베드 브라우저 walk. 드러난 결함 4건 수정 — 추리 선택지가 HUD 순서를
  베끼는 수준이던 것을 보류 제안·레드 헤링 distractor + 상태 해시 시드 순서로 바꿔 "검증된 항목을
  기억하는" 추리로; 좁은 독에서 미라 선택지 4개가 다 보이도록 선택 목록 열림 시 독 배분 0.55:2.45;
  엔딩 캡처의 영수증이 같은 순수 검사로 추리 확정을 기록; 오토파일럿이 코치 카드를 읽고 닫음.
- 논문 검증: Aside 근거 리뷰 §6의 문장 단위 경계를 EN/KO에 반영 — ENG1이 D-073 표면과 fail-closed
  per-node dashboard mirror, core 52/52 + 확장 4검사 집계를 명시; L5가 comprehension/agency/enjoyment/
  immersion/player benefit 주장 불가를 명시; AI 사용 고지가 case-file 팩과 evidence-desk 메시를 명명.
  두 원고 8쪽 유지, 검증기 마커·인용 게이트(5/55/9, citation 4/4) PASS. 결과 승격 없음.
- 동시 세션의 검증된 플레이어 GLB 갱신(Observe/Collect/Speak, 1024 px)을 별도 귀속 커밋으로 반영해
  추적 바이트 = 배포 바이트. 프로덕션 `dpl_37aBTEYLhDHtDD3Z2mWUXAxUvRkg` 16파일 56,005,886 B 일치,
  PDF 두 개는 저장소 바이트와 동일.
