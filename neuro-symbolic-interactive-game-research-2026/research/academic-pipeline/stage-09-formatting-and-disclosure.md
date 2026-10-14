# Stage 9 Final Formatting and AI Disclosure / 9단계 최종 서식 및 AI 고지

Date: 2026-08-13

Current release update: clean tagged pilot recapture verified 2026-08-14.

## Article type and format / 논문 유형과 서식

| Item | Value |
| --- | --- |
| Venue | IEEE Transactions on Games |
| Article type | Short Paper |
| Template | `IEEEtran`, `journal` option, two-column |
| Page count | EN 7 pp, KO 6 pp |
| Band | 6--8 pp, overlength charges above 6, references counted (transactions.games, retrieved 2026-08-13) |
| Review model | double-anonymous since 2025-01-01 |
| Bibliography | 42 entries, `IEEEtran` style |

The English manuscript at 7 pages is inside the band and one page into the overlength-charge range.
That page buys the two-column mechanism figures that Stage 6 finding F11 required; leaving the
figures illegible to avoid a page charge would be the wrong trade.

영문 원고 7쪽은 밴드 안에 있으며 초과 페이지 요금 구간으로 1쪽 진입한다. 이 1쪽은 Stage 6의
F11이 요구한 2단 폭 그림을 위한 것이며, 요금을 피하려고 그림을 읽을 수 없는 상태로 두는 것은
잘못된 교환이다.

## Anonymization / 익명화

| Check | Result |
| --- | --- |
| Author block | `Anonymous Author(s)` in EN, `익명 저자` in KO |
| Affiliation | none present |
| Funding acknowledgment | none present |
| Author biography | none present |
| Self-identifying repository URL | none; the availability statement does not claim that an anonymized archive or DOI deposit already exists |

## Build gate / 빌드 게이트

`make all` exits 0 with:

- page count inside the 6--8 band for both languages, asserted as a band rather than a fixed number
  so a legibility or content fix cannot silently change the article type;
- zero Type-3 fonts in either PDF and in all figure PDFs;
- no overfull boxes, undefined references, undefined citations, or missing characters.

Remaining log warnings are underfull horizontal boxes and, in the Korean build, `TU/ptm` font-shape
substitutions under XeLaTeX. Both are pre-existing and cosmetic.

## Sections added at this stage / 이번 단계에서 추가한 절

**Data and Code Availability** (added at Stage 8 under finding F7) states the bundle contents and
the current clean tagged provenance: 35/35 artifact hashes, 21/21 input paths and exact digests at
`c4752df`, tag `trace-rpg-stage10-inputs-20260814-v1`, `dirty=false`, 56/56 total hashes, portable
`uv run python`, and no absolute user/clone paths. It does not claim an existing reviewer archive
or DOI deposit.

**Disclosure of AI Usage** is present in both languages. The expanded re-audit corrected it to
cover prose, code, and test drafting; command orchestration; evidence auditing and result
interpretation; the reviewer-panel simulation; and citation-identity checks. It does not claim
that AI was absent from interpretation. Instead it records the enforceable boundary: deterministic
runners and retained artifacts, rather than model-authored values, are the source of reported
numbers. Pilot counts enter through generated fragments and Godot statements are transcribed from
the retained engine-evidence packet.

The disclosure is accurate for this project rather than boilerplate: the reviewer simulation is a
real part of how this manuscript reached its current form, and saying so is more honest than
omitting it.

## Carried item disposition / 이월 항목 처리

Stage 9 originally carried the items below. The current manuscript resolves F13, F14, F17, and F18;
the final copy-edit makes all required figures and generated fragments direct build dependencies.

| ID | Item | Status |
| --- | --- | --- |
| F13 | I1--I4 are explicitly asserted implementation invariants, not theorems; no callback deadline is claimed | resolved in current manuscript |
| F14 | 64 provenance rows are split as 43 executed fixture rows plus 21 aggregate rows | resolved in current manuscript |
| F17 | required figures and language-matched generated fragments are direct inputs; conditional fallbacks removed | resolved in final copy-edit |
| F18 | all five figure/algorithm floats and all three tables explicitly cited in both languages | resolved in expanded final re-audit |

F13, F14, F17, F18은 현재 원고에서 해결됐다. 필수 그림 또는 생성 fragment가 없으면 placeholder로
대체되지 않고 LaTeX build가 실패한다. 확장된 Stage-4.5 최종 재감사는 통과했고 clean
committed/tagged recapture가 F6도 종결했다. 심사 archive/DOI deposit은 주장하지 않으며
`C-RESULT-001`--`005`는 계속 `TODO-RESULT`이고 별도 G4/G6 게임 gate의 상태는 바뀌지 않는다.

## Current revision override (2026-10-14) / 현재 개정판 적용

The historical Stage 9 snapshot above remains unchanged for audit provenance. For the current
revision, the approved `stage_1.article_type` is a full research article and the submission track
is **Full Paper**. Rebuilt standard-IEEE PDFs measure 9 pages in English and 9 pages in Korean;
the current gate is the detailed official Full Papers limit of 10 pages including references.
The official page also presents a summary/header target of 10--14 pages, so the summary-versus-
detailed-limit conflict is recorded rather than silently resolved; the detailed 10-page limit is
the conservative current gate. The earlier Short Paper/6--8-page snapshot is historical and is
not a current cover-note or page target. No padding, font shrinking, or layout trick is used, and
the manuscripts are not expanded merely to fill the 10-page ceiling. Evidence scope and all
instrumentation/methods limitations remain unchanged.

위 Stage 9 역사 스냅샷은 감사 provenance를 위해 변경하지 않는다. 현재 개정판에서 승인된
`stage_1.article_type`은 full research article이며 제출 트랙은 **Full Paper**이다. 표준 IEEE
PDF를 다시 빌드한 결과 영문과 국문은 각각 9쪽이며, 현재 게이트는 참고문헌을 포함한 공식
Full Papers 상세 제한 10쪽이다. 공식 페이지의 요약/헤더에는 10--14쪽 목표가 함께 표시되어
있으므로 요약과 상세 제한의 충돌을 기록하되 임의로 숨기지 않는다. 보수적인 현재 게이트는
상세 제한 10쪽을 따른다. 이전 Short Paper/6--8쪽 스냅샷은 역사 기록이며 현재 cover note나
page target이 아니다. 패딩, 글꼴 축소, 레이아웃 꼼수를 사용하지 않으며 10쪽을 채우기 위해
원고를 늘리지 않는다. 증거 범위와 instrumentation/methods 한계는 그대로 유지된다.
