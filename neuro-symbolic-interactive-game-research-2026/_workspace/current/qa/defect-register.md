# Defect Register — Cycle 3

| id | severity | surface | evidence | status | owner |
|---|---|---|---|---|---|
| DEF-001 | S2 | local engine environment | Godot 4.7.1 installed and executable/version receipt recorded | resolved-2026-08-13 | game-programmer |
| DEF-002 | S2 | bridge schema | generic payload lacks event-specific experiment provenance | open | game-programmer |
| DEF-003 | S2 | state model | current runtime cannot yet express all rich inventory/relationship mutations except as facts | open | game-programmer + logic-auditor |
| DEF-004 | S2 | performance | retained startup-heavy frame p95 exceeds 16.7 ms; warmed Web, long-frame, input, and soak metrics absent | open | game-programmer + QA |
| DEF-005 | S1 | save/load | candidate save once replaced live state before checksum verification | resolved-2026-08-13; corrupt-save regression retained | game-programmer + QA |
| DEF-006 | S2 | cross-runtime transport | policy mirror and stable-envelope projection exist, but no live Python authorization round-trip | open | game-programmer + game-integrator |
| DEF-007 | S2 | concept provenance | SL-C04 v1 violated its prompt with key/seal motifs | resolved-2026-08-13; v1 rejected, v2 retained as candidate | art pipeline + QA |
| DEF-008 | S1 | retained evidence | capture script could overwrite fixed evidence path | resolved-2026-08-13; unique fail-closed promotion | game-programmer + reproducibility verifier |
| DEF-009 | S2 | Web export | playable scene previously had no reproducible Web preset/staged release path | resolved: 11-file artifact deployed; latest PCK 1,573,408 bytes after `docs/latest/**` exclusion; HTML/JS/WASM/PCK/OFL 200, correct WASM/OFL MIME | release engineer |
| DEF-010 | S2 | browser input/audio | pointer capture and autoplay require a real user gesture and recovery path | reopened 2026-08-17, not closed: the prior-session observation of a trusted headless Playwriter click entering pointer lock is retained as history but did not reproduce — the headless synthetic click raised `pointerlockerror` and the real-Chrome Playwriter click issued no pointer-lock request, with `document.pointerLockElement` null both times, so pointer lock is unverified and the `LOOK ACTIVE` / `시점 잠김` HUD label is not pointer-lock evidence; still true: zero console/page errors and the real-user-gesture boundary for pointer capture and autoplay; automation denial alone is not a production defect, so a human-gesture check is open; input latency still DEF-014 | UI/audio lane + QA |
| DEF-011 | S2 | responsive UI | fixed desktop ledger risked narrow-viewport clipping and undersized controls | resolved for sampled states: clean 1280×720 and 390×844 start/in-game rendering | UI lane + QA |
| DEF-012 | S1 | rights/track separation | generated candidate images remain pending human rights/style review | public-release risk mitigated by Web/`--public-safe` exclusion; candidate review remains open | release + art owner |
| DEF-013 | S2 | Korean browser text | no clean-browser evidence confirmed Korean glyphs and fallback font behavior | resolved for sampled states: bundled OFL Nanum Gothic and clean Korean at both retained viewports | QA + UI lane |
| DEF-014 | S2 | Web performance | no warmed p95, long-frame rate, input latency, audio focus, or 30-minute memory trace | open | QA + release engineer |
| DEF-015 | S2 | worldview/candidate art | SL-C01 “one amber light” can contradict the dark sealed lighthouse | runtime-resolved by exclusion and corrected copy; regeneration/curation pending | designer + art owner |
| DEF-016 | S2 | release validation | deployment URL, asset responses, console, save/reload, and artifact inventory were absent | partially resolved: production URL, responses/MIME, exact inventory, captures, and zero errors recorded; save/reload remains open | release engineer + QA |
| DEF-017 | S3 | Playwriter extension inspection | extension-connected tab raised `WrongDocumentError` because it did not own the root document for pointer lock | closed-automation-only; scoped to the extension-tab automation artifact and not evidence that pointer lock works (see DEF-010); page/console error counts stayed zero | QA automation |

An implementation-only resolution does not close the corresponding gate. Browser, performance, or
human-impact defects close only with the exact required execution evidence.
