# 논문 게임 판독 그림 · 발표 흐름 정리 · 레퍼런스 교차검증 · 이미지 중심 README — 2026-09-03 (D-066)

Status: **ENGINEERING/EDITORIAL PASS ONLY; NO HUMAN OR MODEL RESULT; C-RESULT-001–005 REMAIN UNESTABLISHED; G4/G6 REMAIN FIX**

2026-09-03 사용자 지시(발표자료 캡처를 논문에 첨부, 배지·이미지 중심 README를 영어 기본/한글 전환으로
작성, 논문 EN/KO를 발표 흐름 위주로 정리하며 에이전트 작업용 스펙·파일·지시 문구 제거, 레퍼런스
팩트체크는 Aside 리서치를 더 신뢰하는 교차검증으로, 깃 푸시)에 따라 결정 `D-066`으로 기록한 패스.
직전에 동시 세션(Aside `BOZW50yOGZJCIJso`)이 `dfa627a`로 서술형 README·레거시 원고·README 시각
생성기를 제거하고 푸시한 상태에서 시작했으며, 해당 세션은 이 패스 동안 편집을 보류했다.

## 1. 논문 그림 3 `fig:playable-readout` (EN/KO 동일)

- 소스: 추적 중인 작업 캡처 `game-track/godot/docs/latest/{refusal,authorized_hint,ending}.png`
  (HEAD 바이트 그대로; 2026-09-02 Web stage 캡처). 논문은 LaTeX `trim`/`clip`으로만 잘라 쓰고
  픽셀은 손대지 않는다. 생성형 UI 아트(초상·인장)는 크롭 밖에 둔다.
- 패널: (a) 보류 — `[P] PROPOSAL → [H] HELD → [V] GATE DISCLOSURE | state unchanged →
  [N] NEXT VALID ENTRY → [V] RULE LEARNED`; (b) 커밋 — `[C] ENTRY #2 | COMMITTED → [C] CONTRIBUTION #2
  | STAGE 1>2 | CHAIN 2/3 → [N] UNLOCKED`; (c) 엔드카드 — INVESTIGATOR'S CONTRIBUTION #1–#3, RULES
  LEARNED, ENTRIES/HOLDS/FINAL STAGE, VALIDATOR RECEIPT `4b2310…`, HOLDS BY GATE.
- 바인딩: `scripts/update_visual_source_manifest.py`에 두 번째 `noneditable_evidence` 항목
  `sealed-lighthouse-playable-readout-panels`(재현 소스: evaluation-matrix.json,
  presentation-evaluation.json, game_3d.gd, harbor_ledger_ui.gd, run_playable_evaluation.py).
- ENG1 문단이 그림 3을 가리키며, 캡션과 본문 모두 "presentation-only readout of committed snapshots;
  engineering conformance, not usability/efficacy evidence"를 유지한다.

## 2. 원고 흐름 정리 (EN/KO 병렬)

- 제거·치환: `C-PILOT-007/008`, `C-RESULT-*`, `TODO-RESULT`, 매트릭스 CSV 파일명, git 태그, 매니페스트
  개수, `Codex CLI`, `screening-pilot-only`, `signal-repair-v2`, `S2-typed-lexical-loose`, `OKF`,
  Stage 번호, AI 사용 고지의 오케스트레이션 문구. 생성기(`generate_paper_results.py`,
  `run_kg_ontology_simulation.py`) 문자열도 같은 규칙으로 갱신.
- 검증기 완화 1건: `validate_contribution_crosswalk.py`의 데이터 가용성 검사가 CSV 파일명 대신
  "machine-checked … matrices" 구문(EN/KO)을 요구한다. 그 밖의 마커(일곱 검사/여섯 계열, C1–C5,
  E1–E3, ENG1, 인용 집합 = bib 집합)는 그대로.

## 3. 레퍼런스 교차검증

- 1차: 세 개의 병렬 read-only 에이전트가 Crossref JSON, arXiv, OpenReview, 출판사 랜딩 페이지에서
  해석 가능성·메타데이터·인용 문맥 적합성을 확인(55 KEEP, 메타데이터 수정 0, 삭제 0). ACM DOI
  `10.1145/3742413.3789221`은 비브라우저 클라이언트에 403이지만 Crossref가 확인.
- 2차(사용자 지시로 더 신뢰): Aside 브라우저 리서치 세 세션이 같은 55개 항목을 1차 기록과 독립적으로
  열어 검토. 불일치 항목은 1차보다 Aside 판정을 우선하되, 메타데이터 변경은 1차 소스 URL을 직접 다시
  열어 확정한 뒤에만 `references.bib`·crosswalk CSV에 반영한다. 결과는 아래 "Receipts"에 기록.
- 기록: `references.bib` note 날짜 `2026-09-03`, `stage-05-citation-verification.json` `audit_date`
  및 addendum 갱신. S46이 ICLR 2024 채택작으로 확인되어 상태 합계는 47 VERIFIED / 8 PREPRINT / 22 rate-limited로 갱신(검증기 계약도 함께 갱신).

## 4. README (루트 `README.md` EN 기본 + `README.ko.md` 전환)

- 배지(validate 워크플로, EN/KO PDF, Vercel 플레이, Godot 4.7.1, Python 3.11+, 증거 52/52·8/8·5/5,
  last-commit, 슬라이드), 골든패스 GIF, 그림 1, 논문 페이지 시트(`docs/readme/paper-*-pages.jpg`),
  캡처 4장, 모바일 2장, 대시보드 GIF + 스틸 4장(`docs/readme/dashboard/`), 밸런스 SVG, KG SVG,
  한국어 덱 16장(`docs/readme/slides/ko-*.jpg`, `docs/slides/trace-rpg-overview.ko.html` 추적).
- 라이선스 파일이 없어 라이선스 배지는 넣지 않았다("to be announced").

## Receipts

- Aside 교차검증 결과(`_workspace/current/intake/aside-reference-crosscheck-2026-09-03.md`): 55/55 해석 가능;
  적용된 수정 — S01 IVIE → ICCC'26 아카이벌 proceedings(ACC 2026, ISBN 978-989-54160-8-0), S06 Mem0 volume 413 /
  pages 2993–3000, S12·S19 제목 표기(Anthology/OJS), S25 FDG '20 proceedings 전체 제목 + article 60, S46 Self-Debug →
  ICLR 2024 채택작(OpenReview), S53 저자 순서(Zeng 우선), S23/S26/S44/S52 note 재기록; 본문 문장 축소 — S15는
  확증 연구 문장의 인용에서 제외, S38·S55·S56 표현을 원 논문 주장 범위로 좁힘. 1차 에이전트가 놓친 항목을
  Aside가 잡았다.
- `make -C paper/latex check` EN 8쪽 / KO 8쪽, Overfull·undefined 0; `validate_contribution_crosswalk.py` 5 contributions /
  55 references / 9 topics PASS; `validate_visual_assets.py --require-pdf-tools --check-regeneration` PASS(16 sources
  double-regenerated, 2 engine-evidence exceptions); `validate_project.py` PASS; `./scripts/verify_like_ci.sh` 전 단계
  PASS.

## 5. D-067 후속 정정 (같은 날 두 번째 푸시)

- 독립 검토 지적: 그림 3이 갱신 가능한 `docs/latest` Web-stage 캡처를 가리켰고 매니페스트 소스로는 그 바이트를
  재생성할 수 없었으며, KO PDF는 한글 어절 사이 공백이 전부 붙은 채 출력됐고(xeCJK 기본 `CJKspace=false`),
  AI 사용 고지가 그림에 포함된 생성 이미지를 언급하지 않았다.
- 조치: `run_playable_evaluation.py --capture`가 `SHOT-SAVED` 페이로드를 `<stage>.shot.json`(캡처 방법, 스테이지
  전후 canonical state hash)으로 남기고 매트릭스 영수증에 병합; `docs/latest`를 네이티브 경로로 갱신하고 QA 핀
  갱신; 그림 3 소스를 `paper/latex/captures/playable-readout-20260903/`(PNG + shot.json + receipt.json, trim 박스
  기록)에 동결하고 매니페스트에 `engine-working-capture`(illustration only) 예외로 바인딩; 캡션·ENG1에 "예시일 뿐
  근거가 아니다" 명시; `\xeCJKsetup{CJKspace=true}`로 한글 공백 복원(8쪽 유지); 두 언어 고지에 curated 생성 UI
  아트 문장 추가; E2 문구를 "hosted proposer"로 도구 중립화; CLAUDE.md의 캡처 갱신 규칙 두 항목을 일치시킴.

## Boundary

그림 3의 캡처는 엔지니어링 작업 캡처이며 사용성·몰입·감정·효능 근거가 아니다. README와 원고 어디에도
새 결과 주장은 없다. `C-RESULT-001`–`005`는 미확립 그대로이고 G4/G6도 `FIX` 그대로다.

Related: [[wiki/reports/2026-09-02-aside-feedback-fun-contribution-legibility-and-page-recomposition]],
[[wiki/concepts/evidence-and-claim-status]], [[wiki/concepts/trace-rpg-controller]], [[maintenance-log]].
