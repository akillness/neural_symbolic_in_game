# Experimental playable/Web release readiness / 실험 플레이어블·웹 릴리스 준비도

Run ID: `20260813-sealed-lighthouse-cycle-3`
Owner: game-programmer + release engineer
Current verdict input: `FIX`

| Check | State | Evidence / blocker |
|---|---|---|
| Canonical deterministic state machine and schemas | DONE-CARRIED | selected v5 and contract tests |
| Explicit playable `main_3d.tscn` | DONE-ENGINEERING | public-safe smoke `8/8`; correct terminal hash |
| Procedural harbor, focus, VFX, English UI, reduced motion | DONE-STRUCTURE | presentation sources; human impact unmeasured |
| Curated tracked Higgsfield player | DONE-PRODUCTION | validator PASS: 9,677,324-byte GLB, 15,463 triangles, 24 joints, `Idle`/`Casual_Walk`; presentation-only; deployed in `dpl_Auzz4gjVUcgDcL45EjcRG2HVyoCW` |
| Gesture-gated procedural audio | DONE-BROWSER-SMOKE | start gesture completed without console/page error; impact unassessed |
| Candidate generated-asset exclusion | DONE-STRUCTURE | `web`/`--public-safe` guard; candidate rights/style review remains open |
| Disposable Web staging | DONE-STRUCTURE | builder changes only a temporary project copy |
| Single-threaded Web preset | DONE-STRUCTURE | thread/extensions disabled; scenario JSON included |
| Static-host configuration | DONE-STRUCTURE | content/referrer/permissions headers declared |
| Aggregate engineering regression | PASS-CURRENT-SESSION | full Pytest `181 passed, 81 subtests`; unittest `138 passed`; game selection `50 passed, 48 subtests`; Ruff check/format clean |
| Presentation evaluation JSON | DONE-ENGINEERING | `SL-PLAY-EVAL-001`: `4/4`, `40/40` + `12/12` = `52/52`; `[OBSERVED 2026-09-02]` three added checks (`contribution_delta_is_pure_and_names_facts`, `hold_teaches_rule_for_its_gate`, `case_chain_mirrors_committed_snapshot`) are contribution-legibility conformance, not fun/usability/G4 evidence |
| Latest public-safe screenshots | DONE-WORKING-CAPTURES | four fresh 1280×720 PNGs from disposable browser stage, SHA-256 registered; not immutable evidence |
| Bundled Korean font | DONE-PROVENANCE | unmodified Nanum Gothic Regular, SIL OFL 1.1, 2,054,744 bytes, pinned SHA-256/source; public 4,534-byte OFL notice hash-matched |
| Staged Web artifact | DONE-PRODUCTION | current 11 manifest files / 50,746,755 bytes; 10 runtime files / 50,746,242 bytes; PCK 10,893,980 bytes, SHA-256 `654c1f13…a58e7`; includes curated player; deployed production is byte-identical |
| Retained gameplay recording | DONE-WORKING-CAPTURE-PREDECESSOR | `trace-rpg-gameplay.mp4`: Compresso H.264 High, 1280×720, 30 fps, 69.067 s, 5,662,128 bytes, SHA-256 `aa374c5a…7044`; full authored route from predecessor `dpl_GpRiuFSFGPrbbVMmFsPdPq731f9Y` before the lens-deck change; engineering demonstration only |
| Production HTTP/MIME | DONE | HTML/JS/WASM/PCK/OFL returned anonymous 200; WASM `application/wasm`; OFL `text/plain`; configured headers present; `vercel.json` 404 |
| Deployed browser layout/glyph smoke | DONE-BOUNDED | current 2026-08-30 desktop start gate/tutorial/in-game smoke, zero console/page errors; retained 2026-08-17 1280×720 and 390×844 captures are historical; current mobile recheck open |
| Trusted headless pointer lock | FIX | not reproduced 2026-08-17: headless synthetic click raised `pointerlockerror`, and the real-Chrome Playwriter click issued no pointer-lock request at all; `document.pointerLockElement` stayed null both times; earlier prior-session pass retained as history only; console/page-error counts stayed zero, and the `LOOK ACTIVE` HUD label is not pointer-lock evidence; human-gesture check open |
| Browser save/reload | DONE-LOCAL-CURRENT | `F5` after lens pickup, full refresh, then `F9` restored lens inventory/objective and passed the corruption check; current production save/reload recheck remains open |
| Below-world recovery | DONE-LOCAL-CURRENT | local Web fall returned to spawn; public-safe smoke remains `8/8` and asserts unchanged symbolic hash |
| Warmed performance/input/soak | FIX | no warmed p95, long-frame rate, input latency, or 30-minute memory trace |
| Deployment/response verification | DONE-BOUNDED | production `dpl_Auzz4gjVUcgDcL45EjcRG2HVyoCW` READY at `https://sealed-lighthouse-trace-rpg.vercel.app`; 10 runtime files anonymous 200 and byte-identical; `vercel.json` 404 |
| Live Python authorization transport | FIX | stable projection only |
| G4 or RQ1–RQ5 confirmatory efficacy promotion | PROHIBITED | RQ2 has screening-pilot-only evidence under `C-PILOT-007/008`; all `C-RESULT-*` remain `TODO-RESULT` |

Release means a reviewable public-safe experimental playable, not a production service or proof of
immersion. The 2026-08-30 English UI + tracked-player artifact is live at
`https://sealed-lighthouse-trace-rpg.vercel.app` as deployment
`dpl_Auzz4gjVUcgDcL45EjcRG2HVyoCW`; bounded production desktop start gate → three-page tutorial →
in-game smoke and exact runtime-byte checks passed. Pending-review concept candidates remain excluded. The extension tab's `WrongDocumentError`
stays automation-only and is not evidence that pointer lock works; the 2026-08-17 retests did not
reproduce the earlier trusted headless pointer-lock pass, and automation denial is not by itself
evidence of a production defect.
G4 remains **UNASSESSED** and G6 remains `FIX`. Local refresh-persistent save/reload passes, but
production save/reload, current mobile verification, a human-gesture pointer/audio check,
representative warmed frame/input measurement, the 30-minute soak, and a rollback drill are still
missing. Full browser details are in `_workspace/current/qa/browser-qa.md`.
