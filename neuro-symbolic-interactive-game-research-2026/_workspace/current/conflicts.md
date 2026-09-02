# Shared-Worktree Conflict Register

No unresolved file-ownership collision is recorded at Cycle 1 intake. Auto-ingested wiki prompt
artifacts predate studio execution and must be preserved.

## 2026-08-14 — divergent `main` and concurrent editing session

- Session `a0097d91` observed `origin/main` **4 commits ahead** of local `main`, while local `main`
  held **13 unpushed commits** from other sessions. `git push origin main` was rejected
  (non-fast-forward). No force-push, rebase, or merge was performed.
- The work was committed as `2f1db87` and pushed to branch
  `okf-methods-graph-and-consensus-direction` instead, so no other session's history was rewritten.
  Reconciling `main` with the four remote release commits (`c4752df`, `6a5fcb7`, `5f2af6d`,
  `0ab55b4`) remains an open owner decision.
- Shared files `game-track/godot/scripts/game3d/{game_3d,harbor_ledger_ui,world_builder}.gd` and
  both `game-track/godot/README.*` carry edits from a concurrent session as well as this one. The
  committed snapshot preserves both; `./scripts/validate_game_track.sh` passed on that snapshot.
- Not committed by this session: another session's in-flight changes under `paper/`, `research/`,
  `_workspace/`, `llm-wiki/`, and the `addons/RodinBridge/` install (now git-ignored upstream).

### Resolution (same day)

- `origin/main` proved to be the authoritative line: it already carries the reviewer response
  letter and decision-log entries up to `D-033` (local `main` stopped at `D-026`), so the 13
  unpushed local commits are a superseded parallel expression of the same work. Local `main` was
  left untouched rather than reset.
- The additive work was rebuilt directly on `origin/main` as branch `okf-methods-graph-clean`,
  which passes `./scripts/validate_game_track.sh` (`40 passed, 44 subtests`), the OKF structure
  lint, and the methods drift check.
- Two items were withheld from that branch because the authoritative line forbids them:
  the generated `pack-3d` PNG bytes (`validate_concept_assets.py` public-safe exclusion — prompts,
  provenance, and the generator script are retained) and the in-engine Codex OAuth LLM channel
  (`tests/test_godot_web_release.py` forbids `scripts/game3d/llm/`, backend strings, and the
  `MiraLLM`/`sl_llm`/`free_question` hooks in the controller and UI). The Godot-side tutorial
  wiring that depended on those hooks is withheld with them, pending an owner decision on whether
  to route the channel through `scripts/codex_oauth_llm.py` instead.

## 2026-08-28 — C-RESULT-003 promotion: two contracts disagree

- `harness/workflows/result-promotion.yaml` permits `TODO-RESULT -> pilot-only` when
  `trace_manifest`, `schema_pass`, and `pilot_label` exist. After the D-040 second live run
  all three exist for `C-RESULT-003`.
- `scripts/validate_game_studio.py::check_claim_boundary` hard-fails if any `C-RESULT-00N`
  leaves `TODO-RESULT`, enforcing the Cycle-1 boundary in
  `.omx/specs/deep-interview-experimental-game-track.md` ("leaves C-RESULT-001--005 TODO").
- Action taken: the promotion was **reverted**, not forced. The guard was not weakened and
  the spec was not edited. Live evidence stays recorded under `C-PILOT-007` and
  `C-PILOT-008`, which are pilot claims and therefore outside the guarded range.
- Owner decision required: either (a) keep the Cycle-1 boundary and leave every `C-RESULT-*`
  at `TODO-RESULT` until a confirmatory cycle opens, or (b) explicitly amend the Cycle-1
  boundary to admit `pilot-only` for planned efficacy claims, updating the spec, the guard,
  and the crosswalk in the same change set.

### 2026-08-28 follow-up — the guard file cannot carry the explanation

Attempting to document the contradiction *inside*
`scripts/validate_game_studio.py` broke the build: the selected immutable render
packet binds that file's SHA-256 as `retained_validator_sha256`, so a docstring-only
edit invalidated the sealed evidence and failed both the unit tests and the
game-track contract check. The edit was reverted; the evidence-integrity contract
behaved exactly as intended.

Consequence for whoever resolves this: `scripts/validate_game_studio.py` is
hash-bound by the retained evidence packet and cannot be edited without promoting a
new evidence set under the capture contract, which currently also needs a
non-headless capture (GUI-blocked in the agent sandbox). Any resolution that changes
the guard is therefore a two-part job: lift the Cycle-1 boundary in
`.omx/specs/deep-interview-experimental-game-track.md` first, then re-promote
evidence in the same change set. The explanation lives here and in
`harness/workflows/result-promotion.yaml`, which is not hash-bound.

## 2026-09-02 — two live sessions in one worktree (Aside `BOZW50yOGZJCIJso` + Claude Code)

- Aside session `BOZW50yOGZJCIJso` (lock scope `d061-independent-review-and-strengthening`,
  started 08:43Z) holds `.git/game-studio.lock` and is editing `game_3d.gd` (`GATE_BY_CODE`
  additions), `paper/latex/Makefile` (SOURCE_DATE_EPOCH reproducibility; `check` now builds),
  `scripts/generate_paper_results.py`, `scripts/validate_visual_assets.py` (new 28 px paper-label
  floor, text-overlap, and single-column `width=\columnwidth` checks), `visuals/*.svg`,
  `tests/test_generate_paper_results.py`, and `tests/test_godot_experimental_game.py`.
- The Claude Code session (this entry; decision recorded as `D-062`) added the presentation-only
  contribution readout (`game_3d.gd` outside `GATE_BY_CODE`, `harbor_ledger_ui.gd`), the 12-check
  `SL-PLAY-EVAL-001` contract (`run_playable_evaluation.py`, `tests/test_playable_evaluation.py`,
  refreshed `docs/latest/`), the design/type docs, five verified references (S52–S56) with
  crosswalk rows, and the EN/KO page-composition revision (8/8 pages, Fig. 3 and Fig. 5 removed,
  Fig. 1 redesigned as a single-column pipeline + ledger-grammar band).
- Shared-file discipline used: re-read before every edit, no reverts, explicit pathspecs only, no
  staging or committing while the lock is held. `D-062` was appended at 19:38; `D-061` remains
  reserved by the lock holder, and no validator enforces ID contiguity (`validate_game_studio.py`
  only requires the log file to exist), so the temporary gap is documented, not a defect.
- Observed collisions: (1) `paper/latex/{en,ko}/` builds raced (truncated `main.aux`, corrupted
  `main.pdf`); this session built in an isolated copy (`/tmp/paperbuild`) and re-ran the in-place
  build only in quiet windows. (2) At 19:21 the lock holder rewrote the ledger band of
  `compact_architecture_svg()` in `scripts/generate_paper_figures.py` (one-row variant, canvas
  900×830) after this session's two-row variant (900×928) had passed the visual validator; the
  in-flight variant currently fails its own overlap check and `visuals/source-manifest.json` is
  stale relative to it. This session stopped editing the generator; whoever finalizes must run
  `make figures`, `update_visual_source_manifest.py`, and the validator before committing.
  (3) The stricter validator also flags the untouched `game-track/godot/docs/latest/balance-archetypes.svg`
  (`'보류 refusals' / '5'` overlap); that is the lock holder's rule change, not a regression from this
  session's files.
- DesignDocs lane overwrote `paper-crosswalk.{en,ko}.md` and `presentation-spec.md` wholesale; the
  originals were restored from `HEAD` and only the intended additive rows (SL-XWALK-T5 row, P-B07/P-B08)
  were re-applied.
- Residue at 19:40 local, after this session re-ran `update_visual_source_manifest.py` (everything
  this session owns is green: unit tests, game-track `49 passed / 45 subtests`, crosswalk 55 refs,
  project integrity, offline smoke, harness, studio contracts, wiki lint, design validators):
  (1) `validate_visual_assets.py`: `generated figure/table sources are stale:
  paper/latex/figures/fig_architecture.svg` — the lock holder edited `compact_architecture_svg()`
  again after the last `make figures`; whoever finalizes runs `make figures`, rebuilds EN/KO,
  re-runs the manifest update and validator. (2) `ruff format --check`: `scripts/generate_readme_visuals.py`
  (lock holder's file). (3) `ko/main.pdf` was rebuilt by this session at 19:21 but the lock holder
  edited `ko/main.tex` again at 19:22:57 — KO needs one more rebuild before commit.
- Measured, not fixed (lock holder's `paper/latex/Makefile` hunk): `ps2pdf -dEPSCrop
  -dDeterministicID=true` is not idempotent on Ghostscript 10.06 (`-dDeterministicID` is not a
  pdfwrite parameter; two consecutive `make figures` runs gave `6fe63607…` then `881bf048…` for
  `fig_architecture.pdf`), so `visuals/source-manifest.json` re-drifts on every build.
  `ps2pdf -dEPSCrop -dOmitInfoDate=true -dOmitID=true -dOmitXMP=true` produced byte-identical
  output twice (`c303a8f5…`) on the same EPS; the Makefile owner should adopt that.
- `D-062` was appended at 19:38 (validator has no decision-order rule; the row states that `D-061`
  is reserved by the lock holder so a reader does not mistake the gap for a missing record).

### 2026-09-02 resolution — D-061/D-062 integrated

- The D-062 writer became quiescent before final integration. D-061 retained its reserved ID and was appended after D-062 so neither append-only record was rewritten.
- The final Fig. 1 source is the one-row 900×830 ledger-band variant. `CONTRIBUTION` was shortened to `CONTRIB. #N`; browser geometry measured the label at 178.90 px inside its 205 px card with no global SVG overflow.
- The non-idempotent Ghostscript option was replaced with the already measured `-dOmitInfoDate=true -dOmitID=true -dOmitXMP=true` conversion. Two consecutive figure builds produced identical SVG, PNG, and PDF hashes, and two forced manuscript rebuilds produced identical EN and KO PDF hashes.
- `generate_paper_figures.py`, `generate_readme_visuals.py`, `update_visual_source_manifest.py`, and `validate_visual_assets.py` are settled and Ruff-formatted. The refreshed manifest validates 88 unique receipts, 11 SVG assets, and isolated double-regeneration of 22 sources.
- The final bilingual PDFs are 8 pages each with zero overfull/undefined/missing-character errors and zero Type 3 fonts. The complete CI-equivalent sequence, full Pytest, and all three game design/UI/feel contract validators pass; canonical `project.godot` and balance-receipt hashes are unchanged.
- No unresolved shared-worktree collision remains from this entry. Commit, push, and deployment remain outside the D-061 review scope.
