# Stage 5 Citation Verification / 5단계 인용 검증

Status: **PASS_NO_HALLUCINATED_CITATIONS**

Audit date: 2026-09-03 (current machine record; original audit 2026-08-13; top-venue and related-work refresh on 2026-09-02; independent primary-record and browser cross-check on 2026-09-03)

Machine-readable record: `stage-05-citation-verification.json`

Current topical/claim-use crosscheck: `reference-topic-crosswalk.csv`. Intermediate totals in the
Stage-8, game-comparator, repair-lineage, and top-venue addenda below are time-stamped historical
snapshots superseded by the current 55-entry summary.

Gate semantics: a `HALLUCINATED` citation must be removed or replaced before Stage 6. None was
found, so Stage 6 is unblocked. Preprint citations are flagged advisory and do not block.

게이트 기준상 `HALLUCINATED` 인용은 Stage 6 이전에 제거하거나 교체해야 한다. 해당 항목이
없으므로 Stage 6이 차단 해제된다. Preprint 인용은 자문 표시이며 진행을 막지 않는다.

## Method / 방법

Verification used metadata APIs plus named official primary records. Broad publisher-page scraping
was not used. The 2026-09-03 second pass opened the official ICCC proceedings and the current
OpenReview forum/PDF where those records resolved metadata that the indices or frozen venue lists
could not settle.

| Index | Role | Endpoint |
| --- | --- | --- |
| Semantic Scholar | primary | `api.semanticscholar.org/graph/v1` |
| OpenAlex | advisory | `api.openalex.org` |
| Crossref | advisory | `api.crossref.org` |
| arXiv | preprint confirmation | `export.arxiv.org/api/query` |
| NeurIPS virtual program / GenProCC workshop list | venue-list confirmation and conflict record (S53 only) | `neurips.cc/virtual`, `genprocc.github.io` |
| OpenReview | official paper record (S46, S53) | `openreview.net` |
| ICCC proceedings | archival proceedings record (S01) | `computationalcreativity.net/iccc26/proceedings/` |

Each entry was resolved by DOI when the bibliography supplied one and by bibliographic title search
otherwise. A title match counted as a hit only at a normalized similarity of at least 0.85, so a
low-scoring near-neighbour is recorded as a miss rather than a match. Recorded years were compared
only against indices that actually matched, because a non-matching title search can otherwise
return an unrelated record's year.

## Results / 결과

| Status | Count |
| --- | --- |
| `VERIFIED` | 48 |
| `PREPRINT` | 7 |
| `UNMATCHED` | 0 |
| `HALLUCINATED` | 0 |
| Total | 55 |

Every one of the 55 entries was matched by at least one answering independent index. The bibliography
is closed against the manuscripts: S52–S56 are present in both sources, there are 55 unique cite keys
and 55 bibliography entries, no cited-but-absent key and no present-but-uncited entry, and the English
and Korean sources have identical key sets.

55개 항목 모두 응답한 독립 색인 중 최소 하나에서 확인됐다. S52–S56은 두 원고에 이미 반영됐고,
인용 키 55개와 참고문헌 55건이 정확히 일치하며, 인용했지만 빠진 항목과 인용되지 않은 항목이 없다.
영문·국문 원고의 키 집합도 동일하다. `S43`은 의도적 결번이다.

## Preprints (advisory) / 프리프린트

| Key | Work | arXiv | Confirmation |
| --- | --- | --- | --- |
| S02 | Symbolically Scaffolded Play | 2510.25820 | arXiv |
| S26 | VLM engagement understanding in games | 2603.18480 | OpenAlex, Semantic Scholar, arXiv |
| S44 | World-State Transformations for Neuro-symbolic Interactive Storytelling | 2605.24719 | OpenAlex, arXiv; Semantic Scholar rate-limited in frozen audit |
| S52 | AgentSpec: customizable runtime enforcement for LLM agents | 2503.18666 | arXiv, OpenAlex (arXiv-DOI lookup); Semantic Scholar rate-limited; ICSE 2026 acceptance stated on arXiv, no proceedings DOI |
| S54 | STORY2GAME: generating (almost) everything in an IF game | 2505.03547 | arXiv, OpenAlex; Semantic Scholar rate-limited |
| S55 | Beyond State Consistency: behavior consistency in text-based world models | 2604.13824 | arXiv, OpenAlex (arXiv-DOI lookup); Semantic Scholar rate-limited |
| S56 | Get Experience from Practice: LLM agents with record & replay (AgentRR) | 2505.17716 | arXiv, OpenAlex (arXiv-DOI lookup); Semantic Scholar rate-limited |

These seven works have no resolved archival proceedings record in the current audit. S01 (IVIE) left
this list when the ICCC 2026 proceedings were published. S46 (Self-Debug) is not claimed as a proceedings
publication; it left the preprint status when the official OpenReview record established its accepted
ICLR 2024 poster identity. S45 (Self-Refine) had already left the list
when its NeurIPS 36 proceedings DOI `10.52202/075280-2019` resolved. The manuscripts describe the
remaining preprints' status or use them only as bounded motivation/comparators. Claim `C-AFFECT-001` remains
`verified-scope-limited-preprint`, and no conclusion depends on treating a preprint as an archival
record.

## Publisher-assignment record / 출판사 배정 레코드

`S23_yin2026contextualized` was re-checked because Stage 2 had flagged a future-dated issue assignment.

- DOI `10.1016/j.entcom.2026.101194` resolves in all three indices at title similarity 1.0.
- The publisher record now assigns *Entertainment Computing*, volume 58 (September 2026), article
  101194; the bibliography note records the 2026-09-03 verification.

The citation remains `VERIFIED` by identity. The earlier submission-time issue-metadata recheck is
closed by the publisher assignment; no issue number is invented.

## Year differences / 연도 차이

Seven entries show a year difference against at least one matched index. Each was inspected
individually, and all seven are the same benign pattern: the index matched the preprint or workshop
version while the bibliography cites the archival version.

| Key | Bib year | Differing index | Explanation |
| --- | --- | --- | --- |
| S10 | 2023 | Semantic Scholar 2022 | PACMPL article year vs earlier record |
| S11 | 2019 | Semantic Scholar 2018 | Springer *Computer Games* chapter vs CGW@IJCAI workshop |
| S14 | 2019 | Semantic Scholar 2018 | IEEE ToG issue year vs early access |
| S15 | 2024 | OpenAlex 2023, Semantic Scholar 2023 | ICLR 2024 vs arXiv submitted version |
| S17 | 2024 | OpenAlex 2023, Semantic Scholar 2023 | ICLR 2024 vs arXiv submitted version |
| S18 | 2025 | OpenAlex 2024 | ICLR 2025 vs arXiv submitted version |
| S33 | 2021 | OpenAlex 2020 | JMLR 2021 vs arXiv submitted version |

For S15, S17, S18, and S33 the OpenAlex record was confirmed to be `type: preprint`,
`source: arXiv`, `version: submittedVersion`, so the bibliography's archival year is the correct
citation year and no edit is required.

S15, S17, S18, S33은 OpenAlex 레코드가 arXiv preprint 판본으로 확인됐으므로 참고문헌의
archival 연도가 옳다. 수정이 필요하지 않다.

## Coverage limitation / 검증 범위 한계

The frozen 45-entry audit recorded Semantic Scholar HTTP 429 for S02, S03, S04, S05, S08,
S12, S18, S33, S34, S44, S45, and S46. The 2026-09-02 refresh then received HTTP 429 for all ten
new lookups, S47--S56, bringing the explicit coverage gap to **22 of 55**. The ten additions were
matched through Crossref/OpenAlex, PMLR plus OpenAlex, arXiv plus OpenAlex, or, for S53, the official
NeurIPS program and GenProCC accepted-paper list.

This is an access limitation of the third index, not citation-mismatch evidence. All 22 affected
records are matched by at least one other named source. A 2026-08-30 spot-check observed Semantic
Scholar title records for S02 and S44--S46 before later calls returned 429 again; those observations
do not replace a reproducible complete re-audit. No entry is reported as verified on the strength of
an index that did not answer.

동결된 45건 감사에서는 Semantic Scholar 조회 12건이 HTTP 429였고, 2026-09-02에 추가한
S47--S56 조회 10건도 모두 429를 반환했다. 따라서 현재 coverage gap은 **55건 중 22건**이다.
이는 인용 불일치가 아니라 세 번째 색인의 접근 제한이다. 영향받은 22건은 모두 명시된 다른
출처에서 확인했으며, 응답하지 않은 색인을 근거로 검증됐다고 표시한 항목은 없다.

## Gate decision / 게이트 판정

| Field | Value |
| --- | --- |
| Entries audited | 55 |
| Hallucinated | 0 |
| Unmatched | 0 |
| Removals or replacements required | 0 |
| Blocking findings | 0 |
| Stage 6 | unblocked |
| Carried caveats | 7 preprints remain advisory; Semantic Scholar coverage incomplete for 22 entries; S53 official records retain a documented author-order display conflict |

This gate verifies citation identity only. It does not assess whether each cited work supports the
sentence that cites it; that judgement belongs to Stage 6 peer-review simulation.

이 게이트는 인용의 동일성만 검증한다. 각 문헌이 인용 문장을 실제로 뒷받침하는지에 대한
판단은 Stage 6 동료심사 시뮬레이션의 몫이다.

## Stage 8 addendum / 8단계 추가분

Five prior-work citations were added at Stage 8 to close Stage 6 finding F10 (missing action-
interposition lineage). Each was verified through the same three-index process before being cited:

| Key | Work | Indices | Note |
| --- | --- | --- | --- |
| S37 | Riedl, Saretto & Young, narrative mediation, AAMAS 2003 | Crossref, OpenAlex, Semantic Scholar | DOI `10.1145/860575.860694` resolves; pages 741--748 confirmed |
| S38 | Evans & Short, Versu, IEEE TCIAIG | Crossref, OpenAlex, Semantic Scholar | archival year corrected 2013 -> 2014; OpenAlex reported the early-access year, Crossref the issue year |
| S39 | Fikes & Nilsson, STRIPS, Artificial Intelligence 1971 | Crossref, OpenAlex, Semantic Scholar | volume, issue, and pages confirmed |
| S40 | Schneider, Enforceable Security Policies, ACM TISSEC 2000 | Crossref, OpenAlex, Semantic Scholar | volume, issue, and pages confirmed |
| S41 | Ware & Siler, Sabre, AIIDE 2021 | Crossref, OpenAlex, Semantic Scholar | title similarity 1.0 |

Revised totals: **41 entries, 38 verified, 3 preprint, 0 unmatched, 0 hallucinated.** The three
preprints are unchanged (S01, S02, S26). Bibliography closure was re-checked after the addition:
41 unique cite keys, 41 bibliography entries, no cited-but-absent key, no present-but-uncited entry.

S38의 연도는 archival issue 기준 2014로 정정했다. OpenAlex는 early-access 연도를, Crossref는
issue 연도를 보고했으며 Stage 5에서 확립한 archival 우선 원칙을 동일하게 적용했다.

## 2026-08-13 game-comparator addendum / 게임 비교군 추가

`S42_buongiorno2024pangea` was added during the final literature refresh. The responsible-harvest
gate returned no disallow finding but could not verify several robots files, so absence of a finding
was not treated as authorization. Verification used the official AAAI/OJS record and PDF plus
metadata APIs. Crossref, OpenAlex, and Semantic Scholar all resolve DOI
`10.1609/aiide.v20i1.31876` to the same title, five authors, 2024 publication, and AIIDE venue;
Crossref and the official record agree on volume 20, issue 1, pages 156--166.

Revised totals: **42 entries, 39 verified, 3 preprint, 0 unmatched, 0 hallucinated.** English and
Korean LaTeX cite identical 42-key sets, and the bibliography contains exactly those 42 entries.
Identity verification does not transfer PANGeA's reported accuracy to TRACE-RPG and does not make
its LLM self-reflection validator a deterministic authorization oracle.


## 2026-08-28 repair-lineage addendum / 수리 계보 추가

S44--S46 were added with the guided-repair revision. arXiv and OpenAlex independently matched each
title and year; Semantic Scholar returned HTTP 429 and is recorded as rate-limited rather than as a
match failure. This raises the current frozen total to **45 entries: 39 verified, 6 preprints,
0 unmatched, 0 hallucinated**. Their topical and contribution roles are recorded in
`reference-topic-crosswalk.csv`; S44 is a game-specific authored-transformation comparator, while
S45--S46 are feedback-repair precedents with different feedback channels and authority boundaries.

## Top-venue refresh addendum (2026-09-02) / 주요 학회 보강

Five references were added so the manuscript's core technique cites its archival lineage directly,
and one existing preprint entry was resolved to its proceedings record. Semantic Scholar was
rate-limited for every call; DBLP was unreachable; Crossref, OpenAlex, and PMLR page metadata answered.

| Key | Venue | Identity | Role |
| --- | --- | --- | --- |
| S45 | NeurIPS 36 (2023), pp. 46534–46594 | DOI `10.52202/075280-2019` (Crossref, OpenAlex) | preprint → `VERIFIED` |
| S47 | ASPLOS 2006, pp. 404–415 | DOI `10.1145/1168857.1168907` (Crossref, OpenAlex) | counterexample-guided synthesis lineage for ρ (T9, C5) |
| S48 | NeurIPS 36 (2023), pp. 8634–8652 | DOI `10.52202/075280-0377` (Crossref, OpenAlex) | feedback-repair comparator (T9, C5) |
| S49 | ACM Computing Surveys 15(4), 1983 | DOI `10.1145/289.291` (Crossref, OpenAlex) | commit/abort transaction lineage (T8, C2/C3) |
| S50 | ICML 2024, PMLR 235:22895–22907 | PMLR citation metadata; OpenAlex indexes arXiv 2402.01817 | generate-and-verify lineage (T8, C2/C5) |
| S51 | CoRL 2022, PMLR 205:287–318 (2023) | PMLR citation metadata; OpenAlex indexes arXiv 2204.01691 | affordance-gated admission (T8, C2) |

주요 학회·저널에 등재된 5편을 추가하고 S45를 proceedings 레코드로 승격했다. 어떤 추가 인용도
효능 주장을 지지하지 않으며, 계보와 비교 대상의 정확한 출처만 강화한다.

## Related-work refresh addendum (2026-09-02) / 관련 연구 보강

Five references named by the paper-framing feedback were added so the related-work section can state
an intersection claim against its closest 2025–2026 neighbours. Verification used metadata APIs and
official venue program pages only; no publisher page was scraped and the OpenReview browser challenge
was not bypassed. Semantic Scholar returned HTTP 429 for every call. Retrieval date: 2026-09-02.

| Key | Identity (arXiv API title / authors) | Indices matched | Role |
| --- | --- | --- | --- |
| S52 | *AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents* — Haoyu Wang; Christopher M. Poskitt; Jun Sun (arXiv 2503.18666v3, published 2025-03-24) | arXiv API; OpenAlex W6947676652 via arXiv-DOI lookup (title search missed it) | general runtime-enforcement precedent (T8, C2); arXiv comment states ICSE 2026 acceptance, no proceedings DOI, so cited as preprint |
| S53 | *Setting the DC: Tool-Grounded D&D Simulations to Test LLM Agents* — Shengqi Li; Ziyi Zeng; Jiajun Xi; Andrew Zhu; Prithviraj Ammanabrolu (NeurIPS 2025 GenProCC workshop, OpenReview `3Op7kJOvaD`) | `neurips.cc/virtual/2025/128312`; `genprocc.github.io` accepted paper 50; OpenReview forum/API HTTP 403 challenge; not indexed by OpenAlex, Crossref, or arXiv | tool-grounded game-state admission comparator (T1, C1/C2); `VERIFIED` by official venue record, non-archival |
| S54 | *STORY2GAME: Generating (Almost) Everything in an Interactive Fiction Game* — Eric Zhou; Shreyas Basavatia; Moontashir Siam; Zexin Chen; Mark O. Riedl (arXiv 2505.03547v1, 2025-05-06) | arXiv API; OpenAlex W4415248313 (title search, type preprint) | generated-precondition comparator (T1, C1/C2) |
| S55 | *Beyond State Consistency: Behavior Consistency in Text-Based World Models* — Youling Huang; Guanqiao Chen; Junchi Yao; Lu Wang; Fangkai Yang; Chao Du; ChenZhuo Zhao; Pu Zhao; Qingwei Lin; Saravan Rajmohan; Dongmei Zhang (arXiv 2604.13824v1, 2026-04-15) | arXiv API; OpenAlex W7154587752 via arXiv-DOI lookup | limitation citation for L1 (T5, `BOUNDARY-FUTURE`) |
| S56 | *Get Experience from Practice: LLM Agents with Record & Replay* — Erhu Feng; Wenbo Zhou; Zibin Liu; Le Chen; Yunpeng Dong; Cheng Zhang; Yisheng Zhao; Dong Du; Zhichao Hua; Yubin Xia; Haibo Chen (arXiv 2505.17716v1, 2025-05-23) | arXiv API; OpenAlex W6910287059 via arXiv-DOI lookup | record-and-replay paradigm precedent (T7, C3) |

The author order for S53 follows the two official venue records (Li first); the feedback report listed
Zeng first, and the OpenReview record could not be read to arbitrate, so the venue order is used and
the discrepancy is recorded here. Revised totals: **55 entries, 46 verified, 9 preprints, 0 unmatched,
0 hallucinated; Semantic Scholar rate-limited for 22.** None of the five additions supports an
efficacy, fun, or usability claim; they bound the intersection claim and the L1 threat only.

관련 연구 5편(S52–S56)을 메타데이터 API와 공식 학회 프로그램 페이지로만 확인해 추가했다.
OpenReview는 브라우저 챌린지를 반환했고 우회하지 않았다. S53의 저자 순서는 공식 NeurIPS 기록을
따른다. 어떤 추가 인용도 효능·재미·사용성 주장을 지지하지 않으며, 교집합 주장과 L1 위협의
경계만 규정한다.

## 2026-09-03 independent browser correction / 독립 브라우저 정정

A second pass opened the current primary records after the metadata-only pass. It supersedes the
current summary, but not the dated historical snapshots above:

- S01 is archival in the ICCC 2026 proceedings; S46 is an ICLR 2024 accepted poster. The current
  total is therefore **55 entries, 48 verified, 7 preprints, 0 unmatched, 0 hallucinated**, with
  Semantic Scholar rate-limited for 22 entries.
- S06 gained ECAI volume 413 and pages 2993--3000; S12 and S19 use their official title forms; S25
  carries the full FDG '20 proceedings title and article 60; S23 now carries its publisher-assigned
  volume 58 (September 2026).
- For S53, the current OpenReview heading, BibTeX, and PDF list **Ziyi Zeng first**, followed by
  Shengqi Li, and mark the two as equal contributors. The NeurIPS virtual page and GenProCC accepted
  list retain a conflicting Li-first display. The bibliography follows the paper-owned OpenReview
  record while the audit preserves both displays and keeps the workshop status non-archival.

이 정정은 인용 동일성과 메타데이터만 갱신한다. TRACE-RPG의 효능·재미·사용성 주장이나
`C-RESULT-*` 상태를 승격하지 않는다.

## 2026-09-06 bounded primary refresh / 제한된 1차 출처 재확인

This is a targeted recheck, not a new 55-entry audit. The arXiv API re-confirmed title, authors,
and submission year for S02, S44, S52, S54, S55, and S56. OpenAlex continued to classify S44 and
S52 through their arXiv identifiers as preprints; a bounded Crossref title query did not establish
an AgentSpec proceedings identity. S55 is now arXiv v2 (updated 2026-09-02). Therefore the current
total remains **55 entries, 48 verified, 7 preprints, 0 unmatched, 0 hallucinated**, and 22
Semantic Scholar lookups remain rate-limited.

The check also narrows claim use rather than promoting any source: S44's available primary abstract
supports pre-programmed world-state transformations and exploratory consistency observations, but
does not establish the absence of every transactional, trace, or repair mechanism. S55 supports the
behavioral-consistency limitation; it is not direct evidence about narrative coherence. The machine
record contains the exact API URLs, retrieval date, and bounded scope.
