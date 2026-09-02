# Aside 검색 피드백 기반 재미·기여도 가독성 패스와 논문 페이지 재구성 — 2026-09-02

Status: **ENGINEERING CONFORMANCE ONLY; NO HUMAN OR MODEL RESULT; G2/G4/G6 REMAIN FIX; INTEGRATED REVIEW RECORDED AS D-061/D-062/D-063**

2026-09-02 사용자 지시(서브에이전트로 게임 UI·타입·기획·시스템을 Aside 검색 피드백에 비추어
개선하고 재미와 기여도가 도드라지게 적용, 논문 재리뷰와 페이지 구성 레이아웃 개선)에 따라
수행한 확장 패스. 라이브 모델 호출·이미지 생성 쿼터는 사용하지 않았다. Aside 세션은
`aside exec --effort high` 두 건으로 외부 공개 웹만 조사했고, 그 결과는
`_workspace/current/intake/aside-feedback-2026-09-02-{game-ui-fun-contribution,paper-framing-layout}.md`에
Aside 내부 인용 태그만 제거해 원문 그대로 보관했다. 두 보고서는 조언(`[INFERENCE]`)이며 근거가
아니다.

## 1. Aside 피드백 요지 (외부 검색 기반)

- 게임(50개 출처): 진행을 관계(케이스 체인)로 보이기, 커밋마다 "무엇이 바뀌었나"를 인과 delta로
  쓰기, 보류(HOLD)를 규칙 학습으로 바꾸기(Struggle-is-Spiel), 관찰 동사는 항상 유효하게 두기,
  끝 영수증을 "수사관의 기여 → 규칙 → 기술 영수증" 2부 구성으로, XAG 101/102 텍스트·대비 기준,
  1001 Nights(CHI EA 2025)처럼 검증기를 디제시스 역할로 두고 3층(결과/술어 설명/연구 노트)으로
  설명하기.
- 논문(105개 출처): IEEE ToG 단문 6–8쪽(6쪽 초과는 유료), 초록 150–200단어, 1쪽에 굵은 명제 한
  문장, 기여를 절/레인 포인터가 붙은 반증 가능 문장으로, IEEEtran은 1쪽 float를 두지 않으므로
  개요 그림은 2쪽 상단, 하나의 `figure*`는 정의 페이지에 놓이지 않음, 같은 파이프라인의 중복 표현
  제거, Godot 캡처는 "제안→보류→커밋"의 번호 붙은 인과 시퀀스로, 2025–2026 필독 이웃 문헌
  (AgentSpec, Setting the DC, STORY2GAME, Beyond State Consistency, AgentRR 등)과 교집합
  주장으로 위치 짓기.

## 2. 게임 시스템·UI (D-062, presentation-only)

- `game_3d.gd`: 순수 함수 `contribution_delta(prior, next)`(하드 writer가 반환한 두 스냅샷의
  facts/stage/inventory/disclosed diff), fail-closed public-label allowlist `FACT_LABEL`, `RULE_BY_CODE`,
  `CASE_LINKS`(LENS/MOUNT/LEAD ↔ `signal_lens_acquired`/`signal_lens_installed`/`tide_marks_hint`),
  `_ledger_last_contribution()`
  (세 `_propose_*` 호출자가 공유), 2부 구성 `_episode_receipt_text()`
  (`INVESTIGATOR'S CONTRIBUTION` → `RULES LEARNED n` → 기존 기술 영수증).
- `harbor_ledger_ui.gd`: `set_case_chain`(`CASE CHAIN | LENS [x] > MOUNT [ ] > LEAD [ ] | RULES
  LEARNED n | <gates>`), `ledger_contribution`(`CONTRIBUTION #N | <labels> | STAGE a>b | CHAIN k/3`),
  `ledger_unlocked`, `ledger_rule`(`RULE LEARNED | GATE: …` / `RULE RECALLED (n)`), 공유 `stage_clause`
  (단계 불변 시 `STAGE 2`), 엔지니어링 스냅샷 키 `case_chain`/`rules_learned`/`contribution_lines`/
  `last_rule_line`. 모든 문자열 ASCII, 색 외 텍스트 중복 유지, 캔버스 앵커 불변.
- `--evaluate` 계약 9 → **12** 검사(`contribution_delta_is_pure_and_names_facts`,
  `hold_teaches_rule_for_its_gate`, `case_chain_mirrors_committed_snapshot`; `schema_version` 1.2.0,
  `contribution` 블록). `SL-PLAY-EVAL-001` `49/49` → **`52/52`**, fixture `40/40` 불변, smoke `8/8`
  불변, 종료 해시 `4b2310…8892` 불변, 실제 `project.godot` 해시 `2e7966…9edd` 전후 동일.
  D-063은 공개 레이블 1개와 봉인/미등록 ID 2개를 함께 넣어 공개 레이블만 남는 probe를 같은
  12개 검사 안에 추가했다. 미등록 ID는 UI에서 원시 문자열이 아니라 `State recorded`로 접힌다.
- 검증: disposable copy headless smoke/evaluate, `run_playable_evaluation.py` PASS(`fixtures 4/4,
  checks 52/52, screenshots 4/4`), 추적되지 않는 `?shot-stage=` 훅을 단 disposable Web stage를
  headless Chromium으로 구동해 1280×720(2× DPR 다운샘플)과 390×844에서 새 장부 줄·HUD 체인·엔드카드
  렌더 확인(콘솔/페이지 오류 0). 네 작업 캡처를 갱신하고 해시를 `qa/gate-measurements.md`,
  `qa/browser-qa.md`에 등록. 이는 렌더 근거일 뿐 사용성·재미·G4 근거가 아니다.

## 3. 기획·타입 문서 (D-062)

- 신규 `game-track/design/game-design-hypothesis.json`(`SL-HYP-001`, H-CONTRIB-01/H-RULE-02/
  H-CHAIN-03/H-RECEIPT-04, 학습/숙달 렌즈, 반증 조건, control=기존 장부 vs variant=기여 판독,
  evidence decision `inconclusive`) — game-design-theory validator PASS. 독립 리뷰에서 근거 없이
  고정한 arm당 4–6명 및 70%/40% 판정선을 제거했고, 모집 전에 연구 책임자가 의사결정 위험과
  근거 강도에 맞춘 충분성 규칙을 동결하도록 수정했다.
- `game-ui-contract.json` v2 표면(hud-case-chain, ledger-contribution, ledger-rule-learned,
  end-card-receipt; 데이터 바인딩·검증 매트릭스·결정) — game-ui-ux validator PASS.
- GDD EN/KO §11 "Contribution legibility / 기여 가독성" + 표 `SL-GDD-T4`(`B-014`–`B-017`, 전부
  `[TARGET]`; 구현 구조는 `[OBSERVED structure]`), `core-loop.md` 루프 문법에 `+ CONTRIBUTION` /
  `+ RULE`, `presentation-spec.md` 비트 `P-B07`/`P-B08`, `paper-crosswalk.{en,ko}.md` 표
  `SL-XWALK-T5` 행 추가. `B-016`은 실수 유도를 목표로 삼지 않도록 hold 없는 황금 경로의 0도
  유효한 기술통계로 정정했다. DesignDocs 서브에이전트가 crosswalk/presentation-spec를 통째로
  덮어쓴 사고는 HEAD에서 원복 후 의도한 행만 재적용했다(`conflicts.md`).

## 4. 논문 재구성 (D-062)

- 참고문헌 5건 추가·검증(S52 AgentSpec arXiv 2503.18666, S53 Setting the DC NeurIPS 2025 GenProCC,
  S54 STORY2GAME 2505.03547, S55 Beyond State Consistency 2604.13824, S56 AgentRR 2505.17716; arXiv
  API·OpenAlex·공식 venue 페이지로 신원 확인, Semantic Scholar 429는 rate-limited로 기록) → 총 55건,
  crosswalk/기여 매트릭스 양방향 폐쇄, `validate_contribution_crosswalk.py` PASS.
- EN/KO 본문: 초록 ≤200단어, 서론 굵은 명제 문장, C1–C5 한 줄+절/레인 포인터, 관련 연구에 S52–S54
  대비 문장과 교집합 주장, 감사 가능성 절에 S56, L1에 S55, ENG1·데이터 가용성 문단에 12 불변조건/
  52 검사 명시(재미·사용성 근거 아님).
- 레이아웃: Fig. 1을 2쪽 상단 단일 컬럼 파이프라인(제안→파서→정책→7개 검사/6개 상태 상대 계열→
  수리/폴백→커밋→기록→리플레이, 레인 태그 E1/E2/E3/ENG1, 하단 플레이어블 장부 문법 띠)으로 재설계, Godot 캡처 그림을
  전폭 3패널 인과 시퀀스 + 바인딩된 상태 필드 표로 재배치(이제 Fig. 3), Fig. 1·표 IV와 중복이던
  `fig_repair_state_machine`(구 Fig. 3)과 `fig_evidence_boundary`(구 Fig. 5)를 제거하고 본문·생성기·
  manifest·validator 목록에서 함께 정리. 결과 EN **8쪽**
  / KO **8쪽**, Overfull 0, Type 3 폰트 0, 참고문헌이 8쪽을 채움.
- 격리 빌드(`/tmp/paperbuild`)로 검증한 뒤 D-061에서 병행 편집이 멈출 때까지 기다려 통합했다.
  최종 Fig. 1은 900×830 한 줄 장부 띠이며 `CONTRIB. #N` 레이블을 205 px 카드 안에서 178.90 px로
  실측했고 전역 SVG overflow는 0이었다. Ghostscript의 비결정적 `-dDeterministicID`를
  `-dOmitInfoDate=true -dOmitID=true -dOmitXMP=true`로 바꿔 그림 2회와 EN/KO PDF 강제 빌드 2회의
  바이트 해시가 각각 동일함을 확인했다. 병행 충돌은 해소됐다(`conflicts.md`).

## Receipts

- `--smoke --public-safe` 8/8, 종료 해시 `4b2310…8892` 불변; `--evaluate` 12/12,
  `state_sha256_before == state_sha256_after`.
- `scripts/run_playable_evaluation.py` → `SL-PLAY-EVAL-001 PASS: fixtures 4/4, checks 52/52,
  screenshots 4/4; Godot 4.7.1.stable.official`.
- 작업 캡처 SHA-256: arrival `a8174d47…cfa9`, refusal `d1c2fb6f…6015`, authorized_hint
  `87ec7d60…70b5`, ending `792aa442…1b8b`.
- 논문: `pdfinfo` EN 8 / KO 8, `Overfull` 0, `pdffonts` Type 3 0, crosswalk 55 refs PASS.
- 편집 가능한 시각 자료: 11 SVG, 경량 생성 출력 22개 2회 재생성, 고유 source/artifact receipt
  88개 PASS. 전체 `verify_like_ci.sh` PASS, full Pytest `181 passed, 81 subtests`, unittest `138 passed`,
  game-track `50 passed, 48 subtests`, Ruff clean.

## Boundary

케이스 체인·기여 절·규칙 학습 줄은 커밋된 스냅샷의 순수 파생물이며 어떤 상태도 바꾸지 않는다.
이들이 지각된 유능감·주체성·좌절에 미치는 효과는 측정되지 않았고(`B-015` 질문 데이터 없음),
`C-RESULT-001`–`005`는 `TODO-RESULT` 그대로이며 어떤 게이트도 PASS로 승격되지 않았다. Aside
보고서의 M-effort 제안(플레이어가 직접 쓰는 최종 추론, 한 사실의 두 맥락 제공)은 골든 패스와
스모크 해시를 바꾸므로 다음 사이클 인터뷰 항목으로 남긴다.

Related: [[wiki/reports/2026-08-28-balance-probe-input-telemetry-and-motion-lane]],
[[wiki/reports/2026-08-21-guided-repair-and-diegetic-ritual]],
[[wiki/concepts/trace-rpg-controller]], [[wiki/concepts/hard-validity-soft-adaptation]],
[[maintenance-log]].
