# Experimental playable/Web release readiness / 실험 플레이어블·웹 릴리스 준비도

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game-programmer + release engineer
Current verdict input: `FIX`

| Check | State | Evidence / blocker |
|---|---|---|
| Canonical deterministic state machine and schemas | DONE-CARRIED | selected v5 and contract tests |
| Explicit playable `main_3d.tscn` | DONE-ENGINEERING | public-safe smoke `8/8`; correct terminal hash |
| Procedural harbor, focus, VFX, UI, reduced motion | DONE-STRUCTURE | presentation sources; human impact unmeasured |
| Gesture-gated procedural audio | DONE-BROWSER-SMOKE | start gesture completed without console/page error; impact unassessed |
| Candidate generated-asset exclusion | DONE-STRUCTURE | `web`/`--public-safe` guard; candidate rights/style review remains open |
| Disposable Web staging | DONE-STRUCTURE | builder changes only a temporary project copy |
| Single-threaded Web preset | DONE-STRUCTURE | thread/extensions disabled; scenario JSON included |
| Static-host configuration | DONE-STRUCTURE | content/referrer/permissions headers declared |
| Aggregate engineering regression | PASS-CURRENT-SESSION | `40 tests, 44 subtests`; final rerun pending |
| Presentation evaluation JSON | DONE-ENGINEERING | `SL-PLAY-EVAL-001`: `4/4`, `40/40` + `7/7` = `47/47` |
| Latest public-safe screenshots | DONE-WORKING-CAPTURES | four 1280×720 PNGs, SHA-256 registered; not immutable evidence |
| Bundled Korean font | DONE-PROVENANCE | unmodified Nanum Gothic Regular, SIL OFL 1.1, 2,054,744 bytes, pinned SHA-256/source; public 4,534-byte OFL notice hash-matched |
| Staged Web artifact | DONE-ARTIFACT | 11 top-level files, 41,425,846 bytes; latest PCK 1,573,072 bytes after `docs/latest/**` exclusion |
| Production HTTP/MIME | DONE | HTML/JS/WASM/PCK/OFL returned 200; WASM `application/wasm`; OFL `text/plain` |
| Deployed browser layout/glyph smoke | DONE-BOUNDED | Playwriter 1280×720 and 390×844 start/in-game captures; Korean rendering clean |
| Trusted headless pointer lock | DONE | Playwriter click entered pointer lock; console/page-error counts stayed zero |
| Browser save/reload | FIX | not exercised in the retained deployment smoke |
| Warmed performance/input/soak | FIX | no warmed p95, long-frame rate, input latency, or 30-minute memory trace |
| Deployment/response verification | DONE-BOUNDED | production `https://sealed-lighthouse-trace-rpg.vercel.app`; retained desktop/mobile captures and HTTP checks |
| Live Python authorization transport | FIX | stable projection only |
| G4 or RQ1–RQ5 efficacy promotion | PROHIBITED | no human/model efficacy evidence |

Release means a reviewable public-safe experimental playable, not a production service or proof of
immersion. The procedural artifact is live at `https://sealed-lighthouse-trace-rpg.vercel.app` and
passed the bounded browser smoke above; pending generated candidates are excluded. The extension
tab's `WrongDocumentError` was automation-only, while dedicated trusted headless sessions passed.
G4 remains **UNASSESSED** and G6 remains `FIX` because save/reload, representative warmed
frame/input measurement, and a 30-minute soak are still missing.
