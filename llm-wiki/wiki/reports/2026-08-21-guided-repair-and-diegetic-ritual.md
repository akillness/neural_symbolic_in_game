# Guided Repair Method and the Diegetic Commit Ritual — Two-Iteration Pass

Status: **ENGINEERING + DESIGNED-FIXTURE CONFORMANCE ONLY; NO EFFICACY RESULT; G4/G6 REMAIN FIX**

On 2026-08-21 the user directed a two-iteration, subagent-driven pass: focus the playable slice's
연출 (VFX, motion, 3D resources, UI, textures) on making the paper's experimental core loop fun and
legible, improve 영상/서사, upgrade the paper with a novel concrete method producing meaningful
results within its stated experimental conditions, sharpen limitations/contributions via deep
research, keep the overall structure plain, push twice, and deploy. Seven subagents executed
(RitualVfx, NarrativeLoop, TexturePack, DeepResearch, RepairMethod; then GamePolish, PaperPolish).

## Method upgrade (paper lane)

- New counterexample-guided repair operator ρ(a,E) in `src/nesy_game/repair.py`: consumes ONLY the
  prior candidate and the validator's structured error set — never authoritative WorldState
  (enforced by a poisoned-state sentinel test). Deterministic minimal edits per error class;
  no-op on state-requiring classes (declared guided-irreparable).
- Pilot manifest gained a guided-repairable / guided-irreparable fixture taxonomy (+10 repair
  cases, all pre-frozen expectations). The pilot now compares four arms — rejection-only, blind
  unchanged-retry, guided ρ, and the state-reading oracle upper bound — with exact per-arm ×
  repairability-class counts and a changed-field edit-distance minimality proxy. No p-values, no
  population claims: designed-fixture epistemology preserved.
- Bilingual paper updates in parity: ρ equation + per-error-class edit table, repairability
  taxonomy, per-arm results text, one new contribution bullet, guided-vs-oracle discussion.
- Deep research (10 findings, 4 validated method records — Self-Refine, Self-Debug, AutoSpec
  CEGIS, World-State Transformations): the gap statement survives 2026 (no prior deterministic,
  model-free, fixture-level repair-operator comparison inside a game commit gate); L1–L9
  limitation list and 5-bullet artifact+mechanism+evidence contributions integrated by PaperPolish.
- References 42 → 45 (S44 arXiv:2605.24719, S45 Self-Refine, S46 Self-Debug; all identity-verified).
- Figure rework via the PaperBanana rubric (Faithfulness/Readability/Conciseness/Aesthetics) on
  the deterministic SVG generators: repair state machine now shows the guided arm distinct from
  the oracle plus the frozen repairability classes; architecture shows ρ consuming only E_t and
  the corrected c_t=(G_t,q_t) tuple; evidence boundary lists all four arms. All ≥4/5 post-rework.

## 연출/서사 (game lane)

- Verdict ritual: 3-phase VFX at the acting prop (amber inspection ring → brass-flash 기록 or
  slate seal-line 보류 → settle) + repair-hint double blink; 4 new procedural audio cues.
- Diegetic ledger voice: numbered 기록 #N entries, 보류 with code-specific flavor clauses plus the
  concrete next valid affordance; commit/refusal stamp icons; tutorial page 2 maps
  제안·검증·보류·기록 onto propose/validate/refuse/commit; end card carries an episode receipt
  (기록·보류·상태 해시) under the tide-route seal.
- Mira 3-beat 서사 (storm night account, guarded hope, valid-entries epilogue), W-* consistent,
  sealed-lighthouse promise untouched.
- D-036 curated textures/stamps: 6 Higgsfield assets (wet planks, oxidized brass, sail canvas,
  commit/refusal stamps, tide-route seal), 1.49 MB curated, provenance-bound, fallback-proven.
- Iteration-2 polish: tapered beacon shader (fixed a real CylinderMesh UV packing bug), lens hero
  glint, start-gate parallax, ledger-close beat, stamp/contrast readability fixes, and a
  performance audit that removed five per-frame allocation patterns from `_process` loops.

## Receipts

- Push 1 `02cf434` (97 files): smoke 8/8 SHA `4b2310…8892`; eval 47/47; 120/120 tests; drift OK;
  make check EN 8pp/KO 7pp; deep-research 14/14; CI replay green.
- Push 2 (this commit + clean re-lock): deploy `dpl_EbgGYuzM2E6gUuFcKFk26RHFpCWW`,
  `index.pck` 5,970,516 B `b97069…56eb`, alias byte-identical, zero unexpected browser errors;
  golden-path GIF retained as a working artifact; pilot packet re-locked at tag
  `trace-rpg-guided-repair-inputs-20260821-v1` with `dirty=false`.

## Boundary

Designed-fixture counts establish mechanism conformance only. The guided-vs-oracle separation is
an implementation result on frozen cases, not live-model repair quality. G4 (human presentation)
and G6 (pointer lock, save/reload, warmed frames, soak) remain FIX. Curated art remains
AI-disclosed; staging packs stay `runtime_eligible: false`.

Related: [[wiki/reports/2026-08-21-sealed-lighthouse-feel-and-higgsfield-ui]],
[[wiki/reports/2026-08-13-trace-rpg-academic-stage-06-to-10]],
[[wiki/concepts/trace-rpg-controller]], [[maintenance-log]].
