# Stage 9 Final Formatting and AI Disclosure / 9단계 최종 서식 및 AI 고지

Date: 2026-08-13

## Article type and format / 논문 유형과 서식

| Item | Value |
| --- | --- |
| Venue | IEEE Transactions on Games |
| Article type | Short Paper |
| Template | `IEEEtran`, `journal` option, two-column |
| Page count | EN 7 pp, KO 6 pp |
| Band | 6--8 pp, overlength charges above 6, references counted (transactions.games, retrieved 2026-08-13) |
| Review model | double-anonymous since 2025-01-01 |
| Bibliography | 41 entries, `IEEEtran` style |

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
| Self-identifying repository URL | none; the availability statement promises an anonymized archive for review and a DOI deposit at camera-ready |

## Build gate / 빌드 게이트

`make all` exits 0 with:

- page count inside the 6--8 band for both languages, asserted as a band rather than a fixed number
  so a legibility or content fix cannot silently change the article type;
- zero Type-3 fonts in either PDF and in all figure PDFs;
- no overfull boxes, undefined references, undefined citations, or missing characters.

Remaining log warnings are underfull horizontal boxes and, in the Korean build, `TU/ptm` font-shape
substitutions under XeLaTeX. Both are pre-existing and cosmetic.

## Sections added at this stage / 이번 단계에서 추가한 절

**Data and Code Availability** (added at Stage 8 under finding F7) states the bundle contents, the
SHA-256 manifest coverage, and the provenance-regeneration caveat.

**Disclosure of AI Usage** is added here in both languages. It states that large language models
were used to draft and revise prose, to simulate the reviewer panel whose findings drove the
revision, and to run citation-identity checks; and that they were not used to generate, alter, or
interpret any experimental result. Every reported number is emitted by the deterministic pilot
runner from frozen fixtures and reaches the manuscript only through machine-generated fragments.

The disclosure is accurate for this project rather than boilerplate: the reviewer simulation is a
real part of how this manuscript reached its current form, and saying so is more honest than
omitting it.

## Carried open items / 이월된 미해결 항목

Stage 9 originally carried the items below. The current manuscript subsequently resolves F13 and
F14; F17 and F18 remain camera-ready items.

| ID | Item | Status |
| --- | --- | --- |
| F13 | I1--I4 are explicitly asserted implementation invariants, not theorems; no callback deadline is claimed | resolved in current manuscript |
| F14 | 64 provenance rows are split as 43 executed fixture rows plus 21 aggregate rows | resolved in current manuscript |
| F17 | `\IfFileExists` and `\pendingartifact` scaffolding still present, latent | open |
| F18 | one of four figure floats uncited in each language | open |

F13과 F14는 현재 원고에서 해결됐다. F17과 F18은 camera-ready 이전 교정 항목이다.
