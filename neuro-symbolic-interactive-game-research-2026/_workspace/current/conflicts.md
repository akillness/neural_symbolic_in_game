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
