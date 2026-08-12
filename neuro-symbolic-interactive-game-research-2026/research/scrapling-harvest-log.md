# Scrapling Harvest Log

As of 2026-08-12, static HTTP extraction was the default. Scientific URLs were checked by the research-harvest gate before retrieval; source site terms, robots rules, crawl delay, and authorization remain authoritative.

| Target class | Mode | Outcome | Use |
|---|---|---|---|
| arXiv paper pages | HTTP after harvest gate | Twelve direct captures; arXiv 15-second crawl delay respected | Primary paper metadata/abstract evidence |
| Official model cards/repositories | HTTP `--ai-targeted` | Qwen, Phi, DeepSeek, OLMo, Mistral, Qwen-VL, gpt-oss captures | Exact IDs, capabilities, access, and license leads |
| OpenAI/Google model docs | HTTP `--ai-targeted` | Direct captures | Hosted snapshot/service evidence, recheck at run time |
| IEEE Transactions on Games | HTTP `--ai-targeted` | Direct scope capture | Venue-scope evidence only |
| ScienceDirect journal scope | HTTP `--ai-targeted` | HTTP 403 challenge page captured | Not admissible as scope evidence; official page/browser result and submission-time recheck required |
| Google Drive folder | Static probe unsuitable | Not harvested; authentication/JS boundary | Local extracted files are the only authoritative supplied content |
| AAAI/AIIDE DOI targets | HTTP via DOI redirect | Two direct official proceedings captures | Primary paper metadata and abstract evidence |
| ACM DOI targets | Plain HTTP only | HTTP 403 pages; no stealth escalation | Metadata lead only; use author preprint/API for evidence |
| ICML 2026 posters | Plain HTTP | Two direct official conference captures | Analogy-only evidence, not game-playstyle evidence |
| IEEE/Kaggle MultiPENG | Plain HTTP probe after gate | Pages fetched without bypass; IEEE remains subscription-domain evidence | Dataset metadata lead; verify licensed data access separately |

Scrapling captures are snapshots, not proof that a model remains available or a journal remains indexed. `research/source-ledger.yaml` records admissibility; `research/sources/scraped/` preserves the retrieved bytes.

The exhaustive mapping from every URL in the supplied five documents to its capture/status is `original-link-audit.yaml`.
