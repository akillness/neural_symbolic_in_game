# Index

## Project

- [[wiki/projects/trace-rpg-paper-2026]] — SCI/SCIE-oriented paper; strict-admitted006 `READY_FOR_SELECTED_COMMIT` is the dated 2026-10-17 selected-source baseline, not approval for changed disclosure sources. Source-bound historical revision: [[wiki/reports/2026-10-22-ontology-signals-interview#11. 승인된 한정 구현과 현재 증거 상태 (2026-10-23)]].

## Concepts

- [[wiki/concepts/trace-rpg-controller]] — event-sourced proposal, validation, repair, and commit boundary
- [[wiki/concepts/hard-validity-soft-adaptation]] — hard safety precedence and affect uncertainty boundary
- [[wiki/concepts/evidence-and-claim-status]] — provenance and result-promotion states
- [[wiki/concepts/journal-grade-experimental-design]] — two-stage model panel, statistics, human evaluation, reproducibility

## Sources and reports

- [[wiki/reports/2026-10-23-current-model-contribution-and-comparison-plan]] — **검증·Git 전달·순차 실험 준비**: `c08ed75` 원격 전달과 전체 pre-push 통과를 확인했다. 기존 사례는 `n=1`, CLI 6회, 독립 반복 0회이며 논문은 각 10쪽이다. 출판 테스트 97개·subtest 23개와 시각자료 검사가 통과했고, 이전 푸시 2회 차단은 보존했다. 후속 검토는 승인하되 공개 경로·할당량 메타데이터 문제 1건을 발견했다. 작업본 가림과 19개 검사는 완료했으나 후속 전달·과거 Git 노출은 별개다. Jev는 미검증 `proposal_only`; 이 체크포인트의 새 비교 36셀은 호출 0회다. 실험은 단일 큐로 수행하며 과거 Argon 관측·제안 채점표를 새 완료 결과로 쓰지 않는다.
  - [[wiki/reports/2026-10-23-current-model-contribution-and-comparison-plan#Ontology consistency interview / 온톨로지 일관성 인터뷰 — 2026-10-24]] — **새 인터뷰 진행 중**: 매 질의 Jev 라우팅 규칙 반영·실제 API 라우팅 확인. 형식 일관성/실행 안전/개발 편익을 분리하고, 동일 정보의 일반규칙 대조군과 새 Sol 기준선 필요성을 제안했다. 이번 후보명은 기존 패널로 자동 대체하지 않으며 새 비교 실험·동결계약 변경은 없다.
    - 사용자 선택: **A 실행 일관성 + C 비최상위 후보의 실용성**. B 중심 권고는 미채택이다. 다음 인터뷰는 고정 게임 내부의 실행 모델 비교와 게임 제작 에이전트 비교를 구분한다. 기존 동결 계약 변경·실험 실행은 없다.
    - **실행 비교·지표 개정 승인:** 같은 게임 내부의 모델 교체와 A+C가 주 목표다. 새 런타임 연구의 **1차는 예산 내 목표 달성률(사전 한도 내 수정 허용)**로 확정했고, 최초 제안 위반율·수정 횟수·완료 시간·비용은 2차, 커밋 안전은 별도 필수 게이트다. 내러티브→온톨로지→워크플로우는 별도 산출물 검증이며 모델별 게임 제작은 탐색 제안이다. **C 허용차·예산·전체 프로토콜은 아직 미확정**이며 기존 동결계약 변경·실험 실행은 없다.
    - **지표 개정 JSON 동결 완료 / 전체 프로토콜 미동결:** [새 런타임 연구의 지표 원본](../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/endpoint-amendment-v1.json)과 SHA-256을 생성·검증했다. [일괄 결정안](../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/pre-run-decision-proposal-v1.json)은 `PENDING_USER_APPROVAL`; 하니스 감사는 `IMPLEMENTATION_REQUIRED`다. 파일럿 조건당24회·최대288회는 미승인 탐색 제안이며 C 비열등성 결과가 아니다. 검토 최초FIX→교정후APPROVE·JSON4개 파싱·해시2개 일치만 검증했고 모델 실험 실행은 없다.
    - **오프라인 구현·실제 엔진 검증 완료:** [최종 영수증](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-24-runtime-model-swap-offline/verification-final.json). 일반규칙/온톨로지 표현 각각 실제 Godot 4판단·3커밋·목표 달성·안전 PASS·새 프로세스 재실행 PASS, 회귀53개와 subtest32개·Ruff·형식 검사 통과, 보호46파일 바이트 불변. 전용 Python 검토기429는 실패로 남기고 독립 Python 기준 대체 검토로 결함을 닫았다. **주입 응답을 쓴 QA이며 실모델 비교0·A/C 미입증·전체 프로토콜/실행 승인 미완료**다. 앞선 정적 감사와 실패 영수증은 이력으로 보존한다.
      - **전체 위키 구조 검사는 FIX:** 이번 인계 추가 영역 밖의 자동수집 이력 링크180개가 끊어져 exit1이었다. 이 실패를 보존했으며 원본·과거 링크를 삭제해 통과시키지 않았다. 런타임 검증 PASS와 전체 위키 건강 상태는 별개다.
    - [[wiki/reports/2026-10-23-current-model-contribution-and-comparison-plan#Independent manuscript review / 독립 논문 검토 — 2026-10-24]] — **논거·임팩트·구성 독립 검토 3개 완료**: [원문 대조 통합판](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-24-paper-review/meta-review.json). 중심 기여는 source-bound 제안→승인→변경의 감사 경계로 정리하며, A/C·온톨로지 인과 효과는 미입증 그대로다. NPC 한영 한계 누락 지적은 원문 전체 대조로 비채택했다. native preflight 현재 부재와 과거 언급의 충돌은 `[uncertain]`으로 보존한다. 논문 개정·실험·Git 전달을 완료했다는 뜻이 아니다.
    - [[wiki/reports/2026-10-23-current-model-contribution-and-comparison-plan#Revised publication checkpoint / 개정 출판 체크포인트 — 2026-10-24]] — **개정 소스 `13b5c77` 원격 전달·read-back 완료**: 한영 각10쪽·F1--F6 한정 과학 검토 승인, 기여5·참조58 교차검증 PASS. 전체 pre-push의 unittest412개·game78개/subtest48개 및 위키 구조 검사 PASS, 공개 집합 링크116개 확인. 원본 미확보 표시는 source recovery가 아니고 개인 경로 원본은 수정하지 않았다. 실모델 비교는0회·A/C 미입증이며 전체 연구/실행 승인과 재배포는 별개다.

- [[wiki/reports/2026-10-23-signal-notation-review]] — **새 표기·시각화 감사 / 추가 live QA 전체 NOT_PASS**: 관련 테스트104개 통과, 검토한 한영 PDF 영역의 잘림·겹침 없음. E/R은 사례 수, C는 검사 기록 수, NR은 미보고 사례 수이며 재생 일치는 안전성이 아니다. Python 검사 ID·퀘스트 조건 연결에 보완점이 남는다. 새 Jev API는 미검증 `proposal_only`; headed yaw guard와 headless pointer-lock 오류4건을 보존한다. 후자는 행동·맵7개 항목이 통과했지만 전체 승인이 아니다. 아래 과거 배포 PASS·동결 실험 수치와 구분하며 새 개발 표본·논문/게임 수정·재배포는 없다.
  - 인터뷰 지표 추가: **검증 완료 시간(1차) + 판단·수정 추적 가능성(핵심 2차)**. 근거·규칙·검사·결정 및 오류·수정·재검증 연결을 별도로 평가한다. 실패한 수정도 추적 가능할 수 있으며, 기록 누락은 통과가 아니다. 세부 측정법은 제안 단계이고 새 결과·실험·논문/게임 수정은 아니다.

- [[wiki/reports/2026-10-23-ontology-map-development-case]] — **현재 온톨로지·실제 개발 사례·표현 개선 검증 (2026-10-23)**: 8역할과 Python7/Godot6/DISC7은 별개다. Codex `gpt-6.1-sol` 사례는 `n=1`·CLI6·독립 반복0 그대로이며, 검사171개 = 동결 사례62 + 출판 소스43 + 표현 회귀44 + 시각 검증기22, 별도 subtest23개 통과다([049](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/049-frozen-affected-regressions.json), [한·영 논문050](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-evidence/050-frozen-paired-papers.json)). 제공자 정체성·리비전·비용은 `null`; Jev는 부정적·미검증 `proposal_only` 조언이다.
  - 배포 `dpl_75HRZ3UGnVtADdvZnFUJaG9espYY` READY: [HTTP 근거](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-http-assets.json) 자산18/18 HTTP200·바이트/해시 일치·루트307 → `/dashboard/`; [실제 입력 근거](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-browser/actual-game-acceptance.json) 8게이트 PASS·모든 진단 오류0. Headed Chromium DPR2의 390 px는 데스크톱 줄바꿈·키보드 검사이지 물리 모바일 gameplay가 아니다.
  - 한영 PDF는 각각10쪽·EN675846/KO631282바이트·Type3 각각0개다. SVG4개·표 여백과 정식 LaTeX 수식을 개선했으며 표 패딩4 pt·`arraystretch=1.20`·표준 IEEE10 pt를 유지한다. 최종 선택 소스 CI 상태는 [표현 개선 영수증](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-ontology-map/presentation-final-verification.json)에서 확인한다. Git 전달은 별도 저장소 커밋·원격 이력으로 확인하며 배포에서 추론하지 않는다. **G4/full G6는 `FIX`; 효능·우월성·인간 편익은 미입증**이며 동결 실험과 아래 과거 기록은 보존한다.

- [[wiki/queries/2026-10-23-signal-data-types-interview#2026-10-23 승인된 한정 release 종료]] — **과거 R3: 승인된 signal-explainer 구현·빌드·배포 PASS** (`2026-10-23T07:34:34.105503+00:00`), [당시 최종 receipt](../neuro-symbolic-interactive-game-research-2026/_workspace/current/qa/releases/2026-10-23-signal-explainer/production-r3-final-verification.json) · [승인 Seed](../.ouroboros/seeds/seed-20261023-signal-explainer-b35b22f4227d.yaml). 당시 배포 `dpl_BvpyBPiSouiyoyzN3wG9WQN16YNM` READY; EN/KO 각10쪽·Type3 없음, 배포9/9 byte 일치. 390px은 dashboard reflow만 검증했으며 G4/full G6는 FIX였다. 현재 프로덕션은 위 표현 개선 기록을 따른다; 효능·우월성 주장은 없다.
  - [[wiki/queries/2026-10-23-signal-data-types-interview#2026-10-23 온톨로지 구조별 증거 배치와 실제 개발 실측 방향]] — 사용자 후속 방향: 온톨로지 구성·관계에 해당 근거 패킷을 부착하고, 실제 Codex 게임 개발 과정과 게임 환경을 전향적으로 실측한다. 구조별 대응·측정 설계 제안 기록; 새 개발/수집/한영 PDF 재편집/재배포 완료가 아니다.

- [[wiki/reports/2026-10-22-ontology-signals-interview]] — **동결 이력: 2026-10-23T01:24:31.965Z 한정 구현·여섯 산출물 PASS / 투고 페이지 gate FIX.** [당시 receipt](../neuro-symbolic-interactive-game-research-2026/research/npc-disclosure/final-verification-20261023.json): focused36/7.26s, authentic Godot7 semantic cases PASS, 일반/온톨로지60/60 일치·unsafe0, 무검사 unsafe51=무권한44+재공개변경7. 정상48/경계4/malformed8 및 규칙변경2/짝비교4를 분리한다. 당시 EN/KO는 각12쪽으로 ≤10쪽 기준 미충족이며 배포 미검증이었다. 이 실패와 source-bound §11은 그대로 보존하며, 현재 각10쪽·배포 완료 상태는 위 signal-explainer 최종 receipt가 갱신한다. 인간 효능은 여전히 미검증이다.

- [[wiki/reports/2026-10-15-npc-goal-operation-implementation]] — **historical strict-admitted006; READY_FOR_SELECTED_COMMIT, 2026-10-17**: composed actual source/artifact reviews closed with all 82 final byte identities matching; actual guide/2-JPEG review APPROVE, 4/4. Selected-tree full CI exited0: 333 unit tests plus78 game tests/48 subtests. Selected006 strict validation admitted16 ENG +72 SCR with zero missing/errors/replay model calls; ENG remained engineering-only and SCR bounded descriptive. EN/KO PDFs were each10 pages. The earlier176/178 exit-1 and two lost-original unit RED receipts remain dated history; experiment packets were not corrupted by those QA losses. At this dated baseline, commit/push, clean Godot release build and production/browser verification were not done; it is not the current signal-explainer release receipt. G4/full G6 and efficacy/model-family/independent-gold/human-benefit/superiority/generalization/`C-RESULT` ceilings are not promoted by the new bounded release.
- [[wiki/reports/2026-10-14-npc-goal-recovery-design]] — **독립 검토 완료된 NPC 운영 시스템 설계**: PASS_FOR_USER_REVIEW; 게임 고정 목표, 자연어 의도 해석 + 기호 재계획, 실제 Godot 이벤트 폐루프, 권한·상태 신선도·claim/fact 분리, 대조군/지표/발언 출처 동결 기준; 프로토콜·구현·새 효능 결과는 미완료
- [[wiki/reports/2026-10-15-npc-goal-operation-implementation]] — **historical D-082 unpublished follow-up**: corrected bilingual claim/authority/navigation scope; its EN/KO 10-page make, strict NPC002, focused tests and visual passes are dated history, not current006 release approval. Actual OpenCode review did not execute; the later user-required actual Codex review replaces that route, with current selected-commit readiness recorded above. Jev remains advisory `proposal_only`; no efficacy/independent-gold/human-benefit promotion.
  - 설명용 단일 HTML: `neuro-symbolic-interactive-game-research-2026/_workspace/current/ui/npc-operating-system-brief/index.html` — 기존/제안 구조, 단계 예시, Codex 그림 2장 내장; 새 NPC 구현·효능 결과 아님
- [[wiki/reports/2026-10-14-paper-experiment-optimization]] — **current paper/game revision (D-075)**: bounded 2025–2026 primary-source refresh (58 records), EN/KO evidence-scoped methods paper, frozen E1 reproduction (121 = 85 + 36; 11/11 CSVs), non-pooled regime SVG, fresh r2 game crops, opt-in bounded local receipts, and explicit remaining author/submission boundaries
- [[wiki/reports/2026-09-18-d073-detective-loop-trace-mirror-and-release]] — **current game track (D-073)**: Aside deep research ×2 filed as intake; hash-bound `EvaluationTrace` mirror + per-node commit-gate dashboard (explicit pass/fail/skipped/out-of-scope, no default state); case-file board, hint ladder, coach cards, slot-assembly deduction, paged end card, four-zone HUD; world stations/VFX/gesture clips; Higgsfield case-v1 pack + evidence-desk GLB; `SL-PLAY-EVAL-001` 52/52 core + 4/4 extension; production `dpl_BkguPJPErtawmhjxU5cvg97PBsiq`
- [[wiki/reports/2026-09-06-paper-game-factcheck-and-release]] — bounded primary-source fact-check, bilingual claim-scope corrections, dashboard predicate accounting, and combined paper/game release

- [[wiki/sources/original-drive-research-plans]] — synthesis of all five supplied Markdown sources
- [[wiki/sources/2026-model-and-method-evidence]] — Scrapling and primary-source model/method snapshot
- [[wiki/reports/2026-08-12-research-synthesis]] — unified research direction and remaining risks
- [[wiki/reports/2026-08-12-trace-rpg-academic-stage-02]] — journal target, 36-source shortlist, and empirical claim boundary
- [[wiki/reports/2026-08-12-trace-rpg-academic-stage-03]] — fail-closed claim audit and IEEE ToG IMRaD outline
- [[wiki/reports/2026-08-12-trace-rpg-academic-stage-04]] — bilingual IEEE draft, deterministic pilot, and evidence boundary
- [[wiki/reports/2026-08-13-trace-rpg-academic-stage-04.5-and-05]] — superseded Stage 4.5 pass/correction trail and still-valid Stage 5 citation-identity gate
- [[wiki/reports/2026-08-13-trace-rpg-academic-stage-06]] — ToG peer-review simulation; user accepted the Full Paper revise-and-resubmit game-track direction
- [[wiki/reports/2026-08-13-trace-rpg-sealed-lighthouse-game-track]] — game track baseline: Godot 4.7.1 authored fixtures, immutable v5 render evidence, Cycle-3 public-safe presentation/Web release, and bounded G4/G6 status
- [[wiki/reports/2026-08-21-sealed-lighthouse-feel-and-higgsfield-ui]] — feel/연출 deepening baseline: D-034/D-035 Higgsfield curated UI art lane, narrow-tutorial fix, first 2026-08-21 Vercel redeploy
- [[wiki/reports/2026-08-21-guided-repair-and-diegetic-ritual]] — guided repair operator ρ(a,E) with per-arm×class designed-fixture results, diegetic verdict ritual/ledger voice, D-036 texture lane, L1–L9 limitations, 45 verified references, second 2026-08-21 deploy + clean tagged re-lock
- [[wiki/reports/2026-08-28-balance-probe-input-telemetry-and-motion-lane]] — **current game + academic track**: D-037 input→visible telemetry + 9-check contract (49/49), D-038 archetype balance probe `SL-BALANCE-PROBE-001` (5 rotations, G2 replacement measurements, structural guard findings), D-039 Mixamo/Blender motion intake lane with raw-source guard; QA hash-drift corrections; G2–G8 remain FIX
- [[wiki/reports/2026-09-02-aside-feedback-fun-contribution-legibility-and-page-recomposition]] — **current game + academic track (D-061/D-062/D-063)**: Aside search-grounded feedback filed as intake; presentation-only contribution readout (CASE CHAIN, `CONTRIBUTION #N`, `RULE LEARNED`, two-part receipt) with fail-closed fact-label allowlist, `SL-PLAY-EVAL-001` 12/12 → 52/52, and refreshed captures; threshold-free `SL-HYP-001` study-owner protocol + GDD §11 (B-014–B-017); contribution-first paper recomposition (EN/KO 8pp, deterministic single-column Fig. 1 + ledger band, causal Godot sequence, S52–S56); concurrent-session collisions resolved
- [[wiki/reports/2026-08-13-trace-rpg-academic-stage-06-to-10]] — academic stage history: bilingual revision, 42-source identity gate, 42/42 claim re-audit, and 2026-08-14 clean tagged recapture
- [[wiki/reports/2026-09-03-paper-game-readout-figure-readme-and-reference-recheck]] — **current game + academic track (D-066–D-069)**: Fig. 3 playable-readout panels with frozen shot receipts, corrected KO spacing, presentation-flow prose, 55-entry reference cross-check (48 VERIFIED / 7 PREPRINT / 22 rate-limited) with entry-derived fail-closed totals and the S53 source conflict preserved, the image-first root README, and the production dashboard at the site root
 insert after
- [[wiki/reports/2026-09-18-aside-evidence-review-game-paper]] — Aside 기반 근거 리뷰: engineering conformance와 player/model efficacy를 분리하고, trace semantics·human study·confirmatory repair의 두 사이클 개선안 제시
- [[maintenance-log]] — wiki and Graphify maintenance decisions

## Prompt/output ingest

- [[wiki/sources/2026-08-12-075859-drive-download-20260812t074907z-1-001-ai-researc]] - drive-download-20260812T074907Z-1-001 의 파일내용을 모두 파악하고 $ai-research-skills 이용해서…

- [[wiki/queries/2026-08-12-075859-drive-download-20260812t074907z-1-001-ai-researc]] - drive-download-20260812T074907Z-1-001 의 파일내용을 모두 파악하고 $ai-research-skills 이용해서…

- [[wiki/sources/2026-08-12-081137-sci-sci-e]] - 중요한점은 논문의 타깃은 sci, sci-e 급 저널을 타깃으로할꺼야

- [[wiki/queries/2026-08-12-081137-sci-sci-e]] - 중요한점은 논문의 타깃은 sci, sci-e 급 저널을 타깃으로할꺼야

- [[wiki/sources/2026-08-12-093240-prompt]] - 깃로그확인하고 오류없도록 푸시. 그리고 개선작업 두번 진행해서 푸시해

- [[wiki/queries/2026-08-12-093240-prompt]] - 깃로그확인하고 오류없도록 푸시. 그리고 개선작업 두번 진행해서 푸시해

- [[wiki/sources/2026-08-12-112804-academic-research-pdf]] - 논문내용 강화하고 포맷도 개선하자. 연구내용을 $academic-research 작성하고 pdf 생성까지 실험결과 포함해서 작성해 결론까지

- [[wiki/queries/2026-08-12-112804-academic-research-pdf]] - 논문내용 강화하고 포맷도 개선하자. 연구내용을 $academic-research 작성하고 pdf 생성까지 실험결과 포함해서 작성해 결론까지

- [[wiki/sources/2026-08-12-113016-prompt]] - 확정

- [[wiki/queries/2026-08-12-113016-prompt]] - 확정

- [[wiki/sources/2026-08-12-114820-prompt]] - 승인

- [[wiki/queries/2026-08-12-114820-prompt]] - 승인

- [[wiki/sources/2026-08-12-151131-prompt]] - ㄱㄱ

- [[wiki/queries/2026-08-12-151131-prompt]] - ㄱㄱ

- [[wiki/sources/2026-08-13-024518-continue]] - continue

- [[wiki/queries/2026-08-13-024518-continue]] - continue

- [[wiki/sources/2026-08-13-081610-interview-game-studio-harness]] - interview 게임트랙에 실험용 게임을 $game-studio-harness 기반으로 구성하고, 규칙파일에 워스프세이스 최신화하도록 추가하…

- [[wiki/queries/2026-08-13-081610-interview-game-studio-harness]] - interview 게임트랙에 실험용 게임을 $game-studio-harness 기반으로 구성하고, 규칙파일에 워스프세이스 최신화하도록 추가하…

- [[wiki/sources/2026-08-13-081911-god-tibo-imagen]] - 컨셉과 리소스도 $god-tibo-imagen 이용해서 컨셉등을 다 설정할수있도록해

- [[wiki/queries/2026-08-13-081911-god-tibo-imagen]] - 컨셉과 리소스도 $god-tibo-imagen 이용해서 컨셉등을 다 설정할수있도록해

- [[wiki/sources/2026-08-13-085617-prompt]] - 비 플랜

- [[wiki/queries/2026-08-13-085617-prompt]] - 비 플랜

- [[wiki/sources/2026-08-13-085724-prompt]] - 권장대로 진행하자

- [[wiki/queries/2026-08-13-085724-prompt]] - 권장대로 진행하자

- [[wiki/sources/2026-08-13-085828-prompt]] - 이중 트랙으로 진행

- [[wiki/queries/2026-08-13-085828-prompt]] - 이중 트랙으로 진행

- [[wiki/sources/2026-08-13-093342-prompt]] - 비 권장대로 진행

- [[wiki/queries/2026-08-13-093342-prompt]] - 비 권장대로 진행

- [[wiki/sources/2026-08-13-113058-prompt]] - 실험 동작하고 캡쳐이미지 추가

- [[wiki/queries/2026-08-13-113058-prompt]] - 실험 동작하고 캡쳐이미지 추가

- [[wiki/sources/2026-08-13-125906-godot]] - godot 게임과 클로드세션으로 완료한 게임을 리소스와 몰입 연출중심으로 디밸롭하고 리소스를 풍요롭고 집중할수있는 형태로 가공해. 웹으로 빌드…

- [[wiki/queries/2026-08-13-125906-godot]] - godot 게임과 클로드세션으로 완료한 게임을 리소스와 몰입 연출중심으로 디밸롭하고 리소스를 풍요롭고 집중할수있는 형태로 가공해. 웹으로 빌드…

- [[wiki/sources/2026-08-13-130053-prompt]] - 게임 플레이 씬의 주요 실험내용과 평가매트릭도 수행하고, 리드미에 업데이트후 깃푸시까지. 이미지와 표도 모두 첨부해서 푸시하자. 최신버전으로만…

- [[wiki/queries/2026-08-13-130053-prompt]] - 게임 플레이 씬의 주요 실험내용과 평가매트릭도 수행하고, 리드미에 업데이트후 깃푸시까지. 이미지와 표도 모두 첨부해서 푸시하자. 최신버전으로만…

- [[wiki/sources/2026-08-13-131159-finally-you-must-try-to-research-for-research-pa]] - finally you must try to research for $research-paper-writing both english and k…

- [[wiki/queries/2026-08-13-131159-finally-you-must-try-to-research-for-research-pa]] - finally you must try to research for $research-paper-writing both english and k…

- [[wiki/sources/2026-08-13-141311-oauth-llm-codex]] - oauth 로 llm 사용가능하게 codex 디바이스 코드 입력으로 로그인할수있도록 기능도 추가

- [[wiki/queries/2026-08-13-141311-oauth-llm-codex]] - oauth 로 llm 사용가능하게 codex 디바이스 코드 입력으로 로그인할수있도록 기능도 추가

- [[wiki/sources/2026-09-05-142539-yolo]] - —yolo

- [[wiki/queries/2026-09-05-142539-yolo]] - —yolo

- [[wiki/sources/2026-09-05-144752-prompt]] - 논문과 게임의 근서와 페이퍼내용에 대해 팩트체크와 개선사항 개선해서 업데이트 적용후 배포까지

- [[wiki/queries/2026-09-05-144752-prompt]] - 논문과 게임의 근서와 페이퍼내용에 대해 팩트체크와 개선사항 개선해서 업데이트 적용후 배포까지

- [[wiki/sources/2026-09-05-145340-prompt]] - 진행해

- [[wiki/queries/2026-09-05-145340-prompt]] - 진행해

- [[wiki/sources/2026-09-06-003827-prompt]] - 이어서 진행해

- [[wiki/queries/2026-09-06-003827-prompt]] - 이어서 진행해

- (capture unavailable in checkout: `wiki/sources/2026-10-22-222444-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-222444-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-224103-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-224103-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-224434-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-224434-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-225244-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-225244-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-225321-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-225321-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-230028-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-230028-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-232633-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-232633-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-233038-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-233038-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-22-235602-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-22-235602-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-000436-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-000436-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-000538-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-000538-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-000623-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-000623-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-000638-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-000638-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-001018-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-001018-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-001141-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-001141-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-004316-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-004316-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-004444-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-004444-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-004445-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-004445-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-004449-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-004449-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-050222-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-050222-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-051127-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-051127-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085003-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085003-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085044-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085044-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085129-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085129-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085204-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085204-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085238-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085238-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085323-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085323-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085407-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085407-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-085644-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-085644-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-223131-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-223131-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-224506-model-deasdfas`) - /model deasdfas

- (capture unavailable in checkout: `wiki/queries/2026-10-23-224506-model-deasdfas`) - /model deasdfas

- (capture unavailable in checkout: `wiki/sources/2026-10-23-225314-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-225314-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-225428-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-225428-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-225538-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-225538-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-225623-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-225623-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/sources/2026-10-23-225814-system-instructions`) - ## System Instructions

- (capture unavailable in checkout: `wiki/queries/2026-10-23-225814-system-instructions`) - ## System Instructions

- (Private source note retained locally; excluded from publication: `wiki/sources/2026-10-24-154756-system-instructions`) - ## System Instructions

- (Private query note retained locally; excluded from publication: `wiki/queries/2026-10-24-154756-system-instructions`) - ## System Instructions

## Native runtime comparison — 2026-10-26

- [[wiki/reports/2026-10-26-fixed-game-native-runtime-comparison]] — **PUBLICATION_CHECKS_PASS / SELECTED_TREE_CI_PASS**: 고정 퀘스트1개·원래 배정8행·native 관측7행, system-goal5/8·host 호출23·관측 repair0·unsafe commit0/16. Fresh-engine는 VALID6/INVALID0/NOT_RUN1(row4)/NOT_OBSERVED1(row1), semantic link replay는 valid7/invalid0/unobserved1이다. 첫 직렬화 실패의 null·미재실행과 이후 소스 개정 교란을 보존한다.
- [공개 출판 검증](../neuro-symbolic-interactive-game-research-2026/research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/publication-verification.json)은 working-tree185 tests+326 subtests·한영 본문 각10쪽/보충 각1쪽·visual134 receipts/10 SVG/22 double-regeneration·crosswalk5 contributions/58 references/9 topics/3 experiment+1 engineering·PDF/AUX label/인용번호 일치를 기록한다. 공개66파일 선택본의 격리 CI도 전 항목 PASS: 단위528 tests·game-track83 tests+48 subtests, source commit `b4a4abd`/tree `820833702716ca57cc3b1d0684de6a568b75d59a`. 원격 전송은 Git ref로 별도 확인하며 hosted CI 통과를 뜻하지 않는다. 초기 보충 FIX4건은 한정 fallback PASS로 닫았고 실패 gate·증거·글자 크기를 보존했다. 현재 실측과 과거 native=0 계획·단일 개발 사례·E1/E2/E3/NPC·주입 QA·미실행 whole-game 패널은 합산하지 않는다. 동결 prelaunch pending은 현재 admission 판정이 아니며 일반 재배포 license는 미확인이다. A/C 확증·효능·모델 순위·player benefit은 미입증이다. 새 보고서에 공개 근거와 그림·표·본문/보충 PDF·TeX 경로를 연결했다.
