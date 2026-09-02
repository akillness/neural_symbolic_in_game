# Stage 5 Link Audit / 5단계 링크 감사 — 2026-09-02

Method: every `doi`/`url` in `paper/latex/references.bib` was (1) resolved with `curl -L` for HTTP status and final host, then fact-checked in the Aside browser: DOI entries against the Crossref work record (title must contain the cited title's distinctive token; container title and year read back), non-DOI entries against the landing page's `citation_title`/`document.title`. No publisher page was scraped beyond its title metadata.

| Key | Resolver | Final host / status | Title check | Note |
|---|---|---|---|---|
| S01 | URL | `arxiv.org` 200 | landing-page title match |  |
| S02 | URL | `arxiv.org` 200 | landing-page title match |  |
| S03 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S04 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S05 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S06 | DOI | `ebooks.iospress.nl` 302 | Crossref title match | IOS Press 302 to ebooks.iospress.nl; Crossref record confirms |
| S07 | DOI | `dl.acm.org` 403 | Crossref title match | dl.acm.org returns 403 to non-browser clients; Crossref record confirms |
| S08 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S09 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S10 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S11 | DOI | `link.springer.com` 200 | Crossref title match |  |
| S12 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S13 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S14 | DOI | `ieeexplore.ieee.org` 202 | Crossref title match | 202 = IEEE Xplore challenge page (DOI resolves); Crossref record confirms |
| S15 | URL | `proceedings.iclr.cc` 200 | landing-page title match |  |
| S16 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S17 | URL | `proceedings.iclr.cc` 200 | landing-page title match |  |
| S18 | URL | `proceedings.iclr.cc` 200 | landing-page title match |  |
| S19 | DOI | `ojs.aaai.org` 200 | Crossref title match |  |
| S20 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S21 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S22 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S23 | DOI | `linkinghub.elsevier.com` 200 | Crossref title match |  |
| S24 | DOI | `ieeexplore.ieee.org` 202 | Crossref title match | 202 = IEEE Xplore challenge page (DOI resolves); Crossref record confirms |
| S25 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S26 | URL | `arxiv.org` 200 | landing-page title match |  |
| S27 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S28 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S29 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S30 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S31 | URL | `proceedings.neurips.cc` 200 | landing-page title match |  |
| S32 | DOI | `journals.sagepub.com` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S33 | URL | `jmlr.org` 200 | landing-page title match |  |
| S34 | URL | `jmlr.org` 200 | landing-page title match |  |
| S35 | DOI | `linkinghub.elsevier.com` 200 | Crossref title match |  |
| S36 | DOI | `aclanthology.org` 200 | Crossref title match |  |
| S37 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S38 | DOI | `ieeexplore.ieee.org` 202 | Crossref title match | 202 = IEEE Xplore challenge page (DOI resolves); Crossref record confirms |
| S39 | DOI | `linkinghub.elsevier.com` 200 | Crossref title match |  |
| S40 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S41 | DOI | `ojs.aaai.org` 200 | Crossref title match |  |
| S42 | DOI | `ojs.aaai.org` 200 | Crossref title match |  |
| S44 | URL | `arxiv.org` 200 | landing-page title match |  |
| S45 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S46 | URL | `arxiv.org` 200 | landing-page title match |  |
| S47 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S48 | DOI | `www.proceedings.com` 200 | Crossref title match |  |
| S49 | DOI | `dl.acm.org` 403 | Crossref title match | 403 = publisher bot wall (DOI resolves); Crossref record confirms |
| S50 | URL | `proceedings.mlr.press` 200 | landing-page title match |  |
| S51 | URL | `proceedings.mlr.press` 200 | landing-page title match |  |
| S52 | URL | `arxiv.org` 200 | landing-page title match |  |
| S53 | URL | `openreview.net` 200 | manual only | OpenReview serves a browser-verification wall to automation; venue string (NeurIPS 2025 GenProCC workshop) verified by hand only |
| S54 | URL | `arxiv.org` 200 | landing-page title match |  |
| S55 | URL | `arxiv.org` 200 | landing-page title match |  |
| S56 | URL | `arxiv.org` 200 | landing-page title match |  |

Result: 55/55 entries resolve; 37 DOI titles match Crossref, 17 landing-page titles match, 1 (S53) is human-verifiable only. No link was changed; no `HALLUCINATED` or `UNMATCHED` entry exists.

결과: 55개 항목 모두 해석되며, DOI 37건은 Crossref 제목과, 비-DOI 17건은 랜딩 페이지 제목과 일치한다. S53은 자동화 차단으로 수동 확인만 가능하다. 수정이 필요한 링크는 없다.
