# TRACE-RPG 1차 진척 보고 / First Progress Report

기준 시각 / As of: 2026-08-29 KST
범위 / Scope: `neural_symbolic_in_game`의 논문, 동결 실험, Godot/Web 플레이어블
버전 / Baseline: `main` = `origin/main` = `24e994d764a63b2468093f81dcfe01655c359086`

## 한국어 보고

### 판정 요약

| 영역 | 현재 판정 | 직접 근거 |
|---|---|---|
| 결정론적 게임 적합성 | PASS, 엔지니어링 한정 | public-safe smoke `8/8`; terminal SHA-256 `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892` |
| 플레이어블 평가 | PASS, 엔지니어링 한정 | fixture `4/4`, 합계 `49/49`, 작업 캡처 `4/4` |
| 밸런스 프로브 | PASS, 스크립트 한정 | 아키타입 `5/5`, 구현 operation `3/3`, 거부 상태 격리 `10/10`, 거부 코드 `7/9` |
| 전체 회귀 | PASS | `pytest`: `161 passed, 2 skipped`; CI형 unittest: `121 tests`, `2 skipped`; Ruff·구조·위키·survey/deep-research 검증 PASS |
| 로컬 Web 브라우저 QA | PASS-BOUNDED | 전체 결말, 페이지 새로고침을 통과한 저장/불러오기, symbolic-state 비변경 추락 복구 |
| RQ2 라이브 근거 | PILOT-ONLY | 단일 hosted revision, 셀당 5회, `K=1`, 14개 해시 결속 영수증 |
| 논문 | SOURCE PASS / PDF BLOCKED | KO/EN 각각 section `9`, subsection `12`, label `11`; 정적 parity PASS; 로컬 LaTeX 도구 없음 |
| G4 | UNASSESSED | 인간 몰입·사용성·가독성 측정 0건 |
| G6 | FIX | 포인터 잠금, 음향 focus/unlock, warmed 성능, 30분 soak, rollback 미측정 |
| Git | 미실행 | commit/push하지 않았으며 사용자 검토 대기 |

### 이번에 완성한 최소 슬라이스

1. macOS 샌드박스의 정확한 font/CA 진단만 빼고 나머지 `ERROR`/`SCRIPT ERROR`는 계속 실패시키도록 평가기와 Web builder를 보강했다.
2. 밸런스 분모를 실제 구현 operation으로 고정해 `polish_lens`가 실행 가능 항목으로 잘못 집계되던 문제를 제거했다.
3. `y < -3.0` 추락 시 플레이어만 `(0.0, 0.2, 2.0)`으로 복구하고 velocity를 초기화했다. 기존 8번째 smoke check를 확장해 symbolic hash 불변을 증명했다.
4. 로컬 Web에서 Mira 거부 → lens → mount → 승인 단서 → tide marks → 결말까지 실제 입력 경로를 완료했다.
5. lens 획득 후 `F5`, 6.5초 동기화, 전체 페이지 refresh, start, `F9` 순서로 IndexedDB `/userfs` 저장 복구를 확인했다.
6. 라이브 스크리닝을 동결 offline 분모와 분리한 채 KO/EN 논문 fragment로 생성했다. 생성기는 14개 파일의 byte/SHA-256, pilot ID, 근거 tier, `K=1`, arm, seed, 셀별 count를 fail-closed로 검사한다.
7. 해시 결속 셀 summary의 과거 `C-RESULT-003` 승격 의도 문구는 바이트 그대로 보존했다. 바깥 promotion manifest에 현재 경계를 명시해 `C-PILOT-007/008`만 허용하고 `C-RESULT-003`은 `TODO-RESULT`로 고정했다.

### RQ2 라이브 스크리닝 원시 집계

| 기저 / 조건 | 최초 유효 | guided commit | blind commit | 해석 |
|---|---:|---:|---:|---|
| Frozen / policy-visible | `5/5` | `5/5` | `5/5` | 수리 미발동 |
| Frozen / policy-blind | `5/5` | `5/5` | `5/5` | 수리 미발동 |
| Frozen / goal-directed blind | `0/5` | `0/5` | `0/5` | 수리 불가 `QUEST_STAGE_REGRESSION` |
| Signal-v2 / policy-visible | `5/5` | `5/5` | `5/5` | 수리 미발동 |
| Signal-v2 / policy-blind | `0/5` | `5/5` | `0/5` | 의도적으로 만든 guided-repairable regime |

현재 셀의 noncommit `15/15`는 prior-state hash를 보존했다. 폐기된 v1 진단은 동반 오류를 최대 3개에서 수리 불가 오류 1개로 줄였지만 commit하지 못했다. 이 결과는 해당 오류 regime의 mechanism transfer만 지지한다. 모집단 효능, 모델 순위, 일반 표본효율, `C-RESULT-003` 확증을 지지하지 않는다.

### 남은 결함과 다음 게이트

- `DEF-021`: lens anchor `(-11, 1, 1)`, radius `2.8`가 부두 가장자리 밖에 있어 정상 접근 중 추락이 반복됐다. 앞문 경로로 완료 가능하고 추락 복구가 hard lock을 제거하므로 이번에는 S3로 보류했다. 다음 layout 또는 인간 navigation pass에서만 radius/anchor를 조정한다.
- 자동화에서 start 후와 `Esc`→canvas click 후 모두 `document.pointerLockElement == null`이었다. 이는 사람 환경의 제품 결함 증거가 아니라 포인터 잠금 미검증이다.
- production alias는 이전 빌드다. 현재 로컬 save/reload와 추락 복구는 다음 배포 뒤 production에서 다시 확인해야 한다.
- warmed frame p95, long-frame rate, 실제 browser input latency, audio focus/unlock, 30분 memory soak, rollback drill이 없다.
- 인간 평가가 없어 G4는 계속 `UNASSESSED`다.
- LaTeX toolchain이 없어 변경된 live-addendum PDF는 로컬에서 재빌드하지 못했다.
- Python 연구 runtime과 Godot runtime의 live authorization round-trip은 아직 없다.

### 근거 위치

- 브라우저 QA: `_workspace/current/qa/browser-qa.md`
- 게이트 수치: `_workspace/current/qa/gate-measurements.md`
- 결함: `_workspace/current/qa/defect-register.md`
- 라이브 packet: `research/academic-pipeline/rq2-live-pilot/`
- claim 상태: `research/claim-ledger.yaml`
- KO/EN 원고: `paper/latex/ko/main.tex`, `paper/latex/en/main.tex`
- 논문 생성기: `scripts/generate_paper_results.py`
- 현재 `project.godot` SHA-256: `2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd`, HEAD와 byte-identical

## English parity report

### Verdict summary

| Area | Current verdict | Direct evidence |
|---|---|---|
| Deterministic game conformance | PASS, engineering only | public-safe smoke `8/8`; terminal SHA-256 `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892` |
| Playable evaluation | PASS, engineering only | fixtures `4/4`, combined `49/49`, working captures `4/4` |
| Balance probe | PASS, scripted only | archetypes `5/5`, implemented operations `3/3`, refusal isolation `10/10`, refusal codes `7/9` |
| Full regression | PASS | `pytest`: `161 passed, 2 skipped`; CI-shaped unittest: `121 tests`, `2 skipped`; Ruff, structure, wiki, survey, and deep-research gates PASS |
| Local Web browser QA | PASS-BOUNDED | full ending, refresh-persistent save/load, symbolic-state-isolated fall recovery |
| RQ2 live evidence | PILOT-ONLY | one hosted revision, five calls per cell, `K=1`, 14 hash-bound receipts |
| Paper | SOURCE PASS / PDF BLOCKED | KO/EN each have `9` sections, `12` subsections, and `11` labels; static parity PASS; no local LaTeX toolchain |
| G4 | UNASSESSED | zero human immersion, usability, or readability measurements |
| G6 | FIX | pointer lock, audio focus/unlock, warmed performance, 30-minute soak, and rollback unmeasured |
| Git | NOT RUN | no commit or push; awaiting user review |

### Smallest complete slice delivered

1. The evaluator and Web builder now subtract only the exact sandboxed macOS font/CA diagnostics while every remaining `ERROR` or `SCRIPT ERROR` still fails closed.
2. The balance denominator is fixed to implemented operations, removing the false executable count for `polish_lens`.
3. Falling below `y=-3.0` recovers only the player to `(0.0, 0.2, 2.0)` and clears velocity. The existing eighth smoke check now proves symbolic-hash equality.
4. The real local Web input path completed Mira refusal → lens → mount → authorized hint → tide marks → ending.
5. After lens pickup, `F5`, a 6.5-second sync wait, full page refresh, start, and `F9` restored state from IndexedDB `/userfs`.
6. Live screening is generated into KO/EN paper fragments without entering the frozen offline denominators. The generator fails closed on the 14 files' byte/SHA-256 values, pilot ID, evidence tier, `K=1`, arms, seeds, and cell counts.
7. The old intended `C-RESULT-003` promotion wording remains byte-preserved in the hash-bound cell summaries. The outer promotion manifest now records the current boundary: only `C-PILOT-007/008` are supported and `C-RESULT-003` remains `TODO-RESULT`.

### RQ2 live-screening raw counts

| Base / condition | Initial valid | Guided commits | Blind commits | Interpretation |
|---|---:|---:|---:|---|
| Frozen / policy-visible | `5/5` | `5/5` | `5/5` | repair not exercised |
| Frozen / policy-blind | `5/5` | `5/5` | `5/5` | repair not exercised |
| Frozen / goal-directed blind | `0/5` | `0/5` | `0/5` | irreparable `QUEST_STAGE_REGRESSION` |
| Signal-v2 / policy-visible | `5/5` | `5/5` | `5/5` | repair not exercised |
| Signal-v2 / policy-blind | `0/5` | `5/5` | `0/5` | deliberately constructed guided-repairable regime |

All `15/15` noncommit outcomes in the current cells preserved the prior-state hash. The superseded v1 diagnostic reduced up to three co-occurring errors to one irreparable error but did not commit. This supports mechanism transfer only in that error regime, not population efficacy, model ranking, general sample efficiency, or confirmatory `C-RESULT-003`.

### Open defects and next gates

- `DEF-021`: the lens anchor `(-11, 1, 1)` with radius `2.8` lies beyond the dock edge and normal approaches repeatedly fell. The front-door route is completable and recovery removes the hard lock, so it is deferred as S3 until the next layout or human navigation pass.
- Automation left `document.pointerLockElement == null` after start and after `Esc`→canvas click. This is non-verification, not evidence of a human-environment production defect.
- The production alias is an older build. Current local save/load and recovery require production re-verification after deployment.
- Warmed frame p95, long-frame rate, real browser input latency, audio focus/unlock, 30-minute memory soak, and rollback drill are absent.
- G4 stays `UNASSESSED` because there is no human evaluation.
- The live-addendum PDFs could not be rebuilt locally because the LaTeX toolchain is absent.
- No live authorization round-trip exists between the Python research runtime and Godot runtime.

### Evidence paths

- Browser QA: `_workspace/current/qa/browser-qa.md`
- Gate measurements: `_workspace/current/qa/gate-measurements.md`
- Defects: `_workspace/current/qa/defect-register.md`
- Live packet: `research/academic-pipeline/rq2-live-pilot/`
- Claim states: `research/claim-ledger.yaml`
- KO/EN manuscripts: `paper/latex/ko/main.tex`, `paper/latex/en/main.tex`
- Paper generator: `scripts/generate_paper_results.py`
- Current `project.godot` SHA-256: `2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd`, byte-identical to HEAD
