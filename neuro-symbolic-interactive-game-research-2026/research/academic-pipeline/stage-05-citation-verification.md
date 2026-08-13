# Stage 5 Citation Verification / 5단계 인용 검증

Status: **PASS_NO_HALLUCINATED_CITATIONS**

Audit date: 2026-08-13

Machine-readable record: `stage-05-citation-verification.json`

Gate semantics: a `HALLUCINATED` citation must be removed or replaced before Stage 6. None was
found, so Stage 6 is unblocked. Preprint citations are flagged advisory and do not block.

게이트 기준상 `HALLUCINATED` 인용은 Stage 6 이전에 제거하거나 교체해야 한다. 해당 항목이
없으므로 Stage 6이 차단 해제된다. Preprint 인용은 자문 표시이며 진행을 막지 않는다.

## Method / 방법

Verification used metadata APIs only. No publisher page was scraped, which follows both the
repository evidence rule and the `scrapling` research-harvesting guidance to prefer
Crossref/OpenAlex/Semantic Scholar over rendered abstract pages.

| Index | Role | Endpoint |
| --- | --- | --- |
| Semantic Scholar | primary | `api.semanticscholar.org/graph/v1` |
| OpenAlex | advisory | `api.openalex.org` |
| Crossref | advisory | `api.crossref.org` |
| arXiv | preprint confirmation | `export.arxiv.org/api/query` |

Each entry was resolved by DOI when the bibliography supplied one and by bibliographic title search
otherwise. A title match counted as a hit only at a normalized similarity of at least 0.85, so a
low-scoring near-neighbour is recorded as a miss rather than a match. Recorded years were compared
only against indices that actually matched, because a non-matching title search can otherwise
return an unrelated record's year.

## Results / 결과

| Status | Count |
| --- | --- |
| `VERIFIED` | 33 |
| `PREPRINT` | 3 |
| `UNMATCHED` | 0 |
| `HALLUCINATED` | 0 |
| Total | 36 |

Every one of the 36 entries was matched by at least one independent index. The bibliography is
closed against the manuscripts: 36 unique cite keys, 36 bibliography entries, no cited-but-absent
key and no present-but-uncited entry, and an identical key set in the English and Korean sources.

36개 항목 모두 최소 하나 이상의 독립 색인에서 확인됐다. 인용 키 36개와 참고문헌 36건이
정확히 일치하며, 영문·국문 원고의 키 집합도 동일하다.

## Preprints (advisory) / 프리프린트

| Key | Work | arXiv | Confirmation |
| --- | --- | --- | --- |
| S01 | IVIE: neuro-symbolic incremental IF world generation | 2606.13348 | OpenAlex, Semantic Scholar, arXiv |
| S02 | Symbolically Scaffolded Play | 2510.25820 | arXiv |
| S26 | VLM engagement understanding in games | 2603.18480 | OpenAlex, Semantic Scholar, arXiv |

These three carry no publisher DOI and remain preprints. The manuscripts already describe S01 as a
preprint comparator and S26 as a preprint reporting VLM engagement limitations, and claim
`C-AFFECT-001` was independently downgraded to `verified-scope-limited-preprint` in the claim
ledger. No conclusion in the manuscripts depends on treating a preprint as an archival record.

## Conditional record / 조건부 레코드

`S23_yin2026contextualized` was re-checked because Stage 2 flagged a future-dated issue assignment.

- DOI `10.1016/j.entcom.2026.101194` resolves in all three indices at title similarity 1.0.
- Crossref reports *Entertainment Computing*, volume 58, article 101194, type `journal-article`.
- The issued date is 2026-09, which is still in the future relative to this audit, and no issue
  number is assigned.

The citation is therefore `VERIFIED` by identity, and the existing manuscript note requiring an
issue-metadata recheck at submission stays in force. This is a metadata-freshness caveat, not a
citation-integrity failure.

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

Semantic Scholar returned HTTP 429 for 9 of 36 entries even after three backoff rounds, which
repeats the rate-limit condition already recorded at Stage 2. Those 9 entries are:
S02, S03, S04, S05, S08, S12, S18, S33, S34.

This is an access limitation of the primary index, not evidence about the citations. Each of the 9
is still matched by at least one other index, and S02 is confirmed directly on arXiv. No entry is
reported as verified on the strength of an index that did not answer.

Semantic Scholar가 36건 중 9건에서 HTTP 429를 반환했다. 이는 색인 접근 제한이며 인용에 관한
근거가 아니다. 9건 모두 다른 색인에서 확인됐고, 응답하지 않은 색인을 근거로 검증됐다고
표시한 항목은 없다.

## Gate decision / 게이트 판정

| Field | Value |
| --- | --- |
| Entries audited | 36 |
| Hallucinated | 0 |
| Unmatched | 0 |
| Removals or replacements required | 0 |
| Blocking findings | 0 |
| Stage 6 | unblocked |
| Carried caveats | S23 issue metadata recheck at submission; 3 preprints remain advisory; Semantic Scholar coverage incomplete for 9 entries |

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
