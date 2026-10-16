# TRACE-RPG — The Sealed Lighthouse

**English** | [한국어](README.ko.md)

*A language model may propose what happens next in a game world — but nothing becomes canonical state until a deterministic symbolic commit gate says so, and every outcome leaves a hash-linked receipt.*

[![validate](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml/badge.svg)](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml)
[![Paper · EN PDF](https://img.shields.io/badge/Paper-EN%20PDF-b31b1b)](neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.pdf)
[![Paper · KO PDF](https://img.shields.io/badge/Paper-KO%20PDF-b31b1b)](neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.pdf)
[![Live dashboard](https://img.shields.io/badge/Live-dashboard%20%2B%20game-2ea44f)](https://sealed-lighthouse-trace-rpg.vercel.app)
[![Play in browser](https://img.shields.io/badge/Play-game%20only-1f6feb)](https://sealed-lighthouse-trace-rpg.vercel.app/public/)
[![Godot 4.7.1](https://img.shields.io/badge/Godot-4.7.1-478cbf)](neuro-symbolic-interactive-game-research-2026/game-track/godot/README.en.md)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab)](neuro-symbolic-interactive-game-research-2026/pyproject.toml)
[![Evidence 52/52 + 4/4 · 8/8 · 5/5](https://img.shields.io/badge/Evidence-52%2F52%20%2B%204%2F4%20%C2%B7%208%2F8%20%C2%B7%205%2F5-blue)](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/evaluation-matrix.md)
[![last commit](https://img.shields.io/github/last-commit/akillness/neural_symbolic_in_game)](https://github.com/akillness/neural_symbolic_in_game/commits/main)
[![Slides (KO)](https://img.shields.io/badge/Slides-KO-orange)](neuro-symbolic-interactive-game-research-2026/docs/slides/trace-rpg-overview.ko.html)

![The Sealed Lighthouse golden path, 76 seconds: arrival at the harbor, a HELD request that names the gate, lens recovery, signal restoration, the authorized tide lead, and the case-complete receipt](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/golden-path.gif)

- **The gate.** Every generated event is treated as an untrusted transaction proposal. A type-strict parser, an external action policy, and seven deterministic checks in six state-relative families decide whether it commits; a rejected candidate gets bounded, counterexample-guided repair, and everything else falls back to the unchanged prior state.
- **The game.** *The Sealed Lighthouse* is a turn-based investigation micro-RPG in Godot 4.7.1 whose in-world ledger shows the gate diegetically: a hold names the family that held it and teaches the rule; a commit posts a contribution, unlocks the next lead, and extends a SHA-256 receipt chain.
- **The evidence — and its limits.** Four lanes (E1 offline fixtures, E2 live screening, E3 KG simulation, ENG1 engine conformance) report exact counts only: 13/13 gate agreement, ρ 5/5 on the guided-repairable class, 52/52 core playable checks plus the 4/4 D-073 extension, one shared terminal state hash. One authored world, one hosted proposer, no participants, no efficacy claim.

## Paper at a glance

![Figure 1: the transaction pipeline — propose, parse, policy, seven checks in six families, bounded repair or unchanged fallback, commit, record, replay — with the ledger grammar band the player reads](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_architecture.png)

**TRACE-RPG: A Trace-Linked Symbolic Commit Gate for Generated Events in an Interactive Game World.** Manuscript submitted for anonymous review (IEEE Transactions on Games short-paper band, 6–8 pages; EN and KO manuscripts are 8 pages each and share one structure). 55 references, all re-verified for resolvability and citation-context fit.

**Thesis.** Fluent or schema-valid generated text does not establish that a proposed game event is executable, authorized, or consistent with canonical state. TRACE-RPG therefore treats every generated event as an untrusted transaction proposal and admits it only through a deterministic symbolic commit gate.

| | Contribution | What it guarantees |
|---|---|---|
| **C1** | Trust-boundary contracts and a type-strict parser | Unknown keys and ambiguous types are rejected at both the proposal and the replay boundary |
| **C2** | Validate–repair–commit controller | Seven deterministic checks in six state-relative families, bounded repair (at most K+1 recorded attempts), unchanged fallback, pre-commit revalidation |
| **C3** | Audit-linked evidence layer | SHA-256-linked records, state-semantic replay, assignment-complete accounting |
| **C4** | Assignment-complete harness | Exact designed-case accounting: every designed case is observed and classified |
| **C5** | Counterexample-guided repair operator ρ | Reads only the prior candidate and the validator's typed error set — never authoritative state |

The seven checks, grouped into six state-relative families. Every failure leaves state unchanged.

| Family | Check | Rejects |
|---|---|---|
| Action policy | 1 | Unknown action or type |
| Precondition | 2 | Absent or false requirement |
| Reachability | 3 | Inaccessible object |
| NPC knowledge | 4 | Undeclared known fact |
| Disclosure | 5 | Forbidden fact |
| Quest | 6, 7 | Ineligible stage; stage regression |

[![Contact sheet of the eight English manuscript pages](neuro-symbolic-interactive-game-research-2026/docs/readme/paper-en-pages.jpg)](neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.pdf)

## Evidence

Four lanes, four ceilings. Every number is a raw count from a deterministic runner or a hash-bound receipt; no inferential statistics are reported.

| Lane | Design | Unit | Headline count | Ceiling |
|---|---|---|---|---|
| **E1** Offline conformance | Authored frozen fixtures, one world: 13 gate fixtures, 12 repair fixtures × 4 arms, 10 fault injections, 7 adapter/accounting assignments, 3 guards | Fixture | 13/13 gate agreement; ρ 5/5 on the guided-repairable class | Mechanism conformance on encoded predicates — not efficacy |
| **E2** Live screening | One hosted proposer (`gpt-5.6-sol`), 5 cells × 5 calls, K = 1, matched candidate for both arms | Call | Signal-v2 cell: ρ 5/5 vs. blind retry 0/5 | Pilot-only; no population or model-ranking claim |
| **E3** KG/ontology simulation | Closed-world typed-link simulation: 43 nodes, 106 reference edges, 24 reviewed typed edges, 210 scored proposals; degree baseline vs. 6 fixed strategies | Proposal | 6/6 authored holdouts recovered | Simulation-only; not runtime retrieval or semantic truth |
| **ENG1** Godot/Web engineering | 4 fixtures, 52 core checks + 4 D-073 extension checks, 8-item 3D smoke, 5 archetype rotations | Check | 52/52 (+4/4 extension) · 8/8 · 5/5; terminal hash equals the offline runner's | Conformance, not performance; no participants |

**Results in full.**

- **E1.** 13/13 gate agreement, all 12 implemented error codes observed. On the 12 initially invalid repair cases (5 guided-repairable / 1 oracle-only / 6 irreparable): rejection-only 0/12, blind retry 0/12, ρ 5/5 + 0/1 + 0/6, state-reading oracle callback 5/5 + 1/1 + 0/6. Every failed arm left state unchanged. 10/10 prespecified faults were rejected by their designated checks. 1/1 provenance-boundary fixture passes replay by design — unkeyed hashes give integrity, not authentication.
- **E2.** A guided advantage appeared only in the policy-blind Signal-v2 cell (ρ 5/5 vs. blind 0/5, +5). The other four cells were +0: three candidates were already valid, one was an irreparable quest-stage regression. All 15/15 non-commit outcomes preserved the prior-state hash.
- **E3.** The typed-lexical strategy recovered 6/6 authored holdouts (P = R = F1 = 1.000, MRR 0.944, Brier 0.131, Sem@3 1.000); the degree baseline recovered none.
- **ENG1.** The Godot slice replays the authored trace and its terminal state hash equals the offline runner's: `4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`. Playable evaluation 52/52 core (40 fixture checks + 12 presentation invariants) plus the separately counted 4/4 D-073 detective/guidance/trace extension (56/56 all), 3D smoke 8/8, balance probe 5/5.

![Balance probe: five scripted archetype rotations through the playable, each completing the same commit chain](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/balance-archetypes.svg)

![KG/ontology simulation evaluation matrix: degree baseline versus six fixed typed-link strategies over the authored holdouts](neuro-symbolic-interactive-game-research-2026/research/simulation/kg-ontology/latest/figures/evaluation-matrix.svg)

**What this does not show.**

- That any model is better than another — E2 uses one hosted proposer with an unpinned revision, five calls per cell.
- Player experience, fun, usability, or affect — no participant has been recruited.
- Generalization beyond the one authored world — all fixtures live in a single frozen world state.
- Writer authentication — the hash chain is unkeyed, so it proves integrity only.
- Engine performance — ENG1 is conformance evidence, not latency or throughput.

## The game

*The Sealed Lighthouse* is a turn-based narrative investigation micro-RPG in a 3D harbor scene (Godot 4.7.1, English UI). The payoff is restoring the harbor-side signal and earning the low-tide route; the offshore lighthouse itself stays sealed and dark. Play it in the browser: [sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app) opens the live dashboard with the game embedded; [`/public/`](https://sealed-lighthouse-trace-rpg.vercel.app/public/) is the game alone.

**Golden path** — three commits, optionally one hold:

1. Recover the signal lens from the lamp store → **commit**, stage 0 > 1.
2. Install the lens in the harbor signal mount → **commit**, stage 1 > 2, the lead is authorized.
3. Ask Captain Mira for the tide-marks lead → **commit**; then inspect the tide marks on the west breakwater → episode complete.
4. (Optional) Ask Mira for the sealed keeper secret → **HELD** by the DISCLOSURE family, state unchanged, rule learned.

**The ledger the player reads** — a presentation-only readout of committed snapshots, never oracle labels or sealed facts:

```text
[P] PROPOSAL …
[C] ENTRY #N | COMMITTED
[C] CONTRIBUTION #N | <facts> | STAGE a>b | CHAIN k/3
[N] UNLOCKED | <next affordance>

[H] HELD | [V] GATE <family> | state unchanged
[N] NEXT VALID ENTRY
[V] RULE LEARNED | <family>: <rule>

HUD      CASE CHAIN | LENS [x] > MOUNT [x] > LEAD [x] | RULES LEARNED n
End card INVESTIGATOR'S CONTRIBUTION #1–#3 · RULES LEARNED · ENTRIES/HOLDS/FINAL STAGE
         VALIDATOR RECEIPT <state hash> · HOLDS BY GATE
```

| Key | Action | | Key | Action |
|---|---|---|---|---|
| `W A S D` | Move | | `F5` / `F9` | Save / load (checksum-validated; a corrupt save is rejected) |
| Mouse | Look | | `M` | Reduce motion |
| `E` | Interact / inspect | | `V` | Audio toggle |
| `Esc` | Free cursor | | `T` | Field guide |

<table>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/refusal.png" alt="The HELD moment: the ledger names the DISCLOSURE gate, reports state unchanged, and teaches the rule"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/authorized_hint.png" alt="Commits with CONTRIBUTION and UNLOCKED lines after the lens is installed and the lead is authorized"></td>
  </tr>
  <tr>
    <td align="center"><sub>Hold — the gate names its family</sub></td>
    <td align="center"><sub>Commit — contribution and next affordance</sub></td>
  </tr>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/ending.png" alt="End card: investigator's contribution, rules learned, entries/holds/final stage, validator receipt with the state hash, holds by gate"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/web-in-game.png" alt="The public-safe Web build running in a browser"></td>
  </tr>
  <tr>
    <td align="center"><sub>End card — the two-part receipt</sub></td>
    <td align="center"><sub>Web build in the browser</sub></td>
  </tr>
</table>

<p align="center">
  <img width="32%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-start.png" alt="Production deployment on a mobile viewport: start screen">
  <img width="32%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-in-game.png" alt="Production deployment on a mobile viewport: in-game ledger">
</p>

All captures above are tracked 1280×720 engineering captures, not usability evidence. The UI art in the playable is curated AI-generated imagery (Higgsfield) with per-file provenance and a procedural fallback; the player rig is a curated Higgsfield GLB (Idle / Casual_Walk); Mixamo raw files are never tracked. Movement, camera, VFX, audio, and UI never mutate canonical state — only the proposal router and validator do, and no live Python round trip exists in the engine slice.

## Live commit-gate dashboard

**2026-10-02 local gameplay UI:** the embedded game stays primary, with its reported three-stage quest, live player/site map, recent actions, and a stable last-action readout. Freeze and historical selection affect this readout only; game input and canonical state stay in the game. The new screenshots show real local input: two `ask_secret` holds preserved `f488d9c4…812c`, then lens acquisition committed stage 0 → 1 (`19b474dc…c498`, 1 commit / 2 holds). They are engineering captures, not usability, fun, efficacy, or G4/G6 evidence. The independent browser gate is still pending, so this revision is not yet deployed.

The GIF and episode-complete image below retain the earlier renderer and its separate 3-commit / 1-hold run.

![Earlier dashboard route: three commits and one hold beside the embedded game; commit receipts extend the chain and the hold preserves state](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/dashboard-route.gif)

<table>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/dashboard/dashboard-hold.png" alt="Real local ask_secret hold selected in history: state unchanged, failed disclosure check, passed stage check, other families not evaluated"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/dashboard/dashboard-commit.png" alt="Local gameplay view after lens acquisition: stage 1 of 3, one commit and two holds, install-lens objective"></td>
  </tr>
  <tr>
    <td align="center"><sub>Hold</sub></td>
    <td align="center"><sub>Commit</sub></td>
  </tr>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/dashboard/dashboard-complete.png" alt="Dashboard at episode completion: three commits, one hold, full chain"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/dashboard/dashboard-panels.png" alt="Real acquire_object verdict: stage 0 to 1, two reported reachability checks, other families not evaluated, selectable history"></td>
  </tr>
  <tr>
    <td align="center"><sub>Earlier renderer · episode complete</sub></td>
    <td align="center"><sub>Current last-action readout</sub></td>
  </tr>
</table>

**Live:** [sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app) — the production site root redirects to `/dashboard/`, and the embedded game is served from `/public/` (deployed 2026-09-03 through `scripts/deploy_vercel_dashboard.sh`; zero console/page errors on desktop and a 390×844 viewport).

<p align="center"><img width="100%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-dashboard.png" alt="2026-10-02 local gameplay dashboard after a real lens-acquisition commit: stage 1 of 3, live player position and the next objective"></p>

To run it locally, the dashboard embeds the local Web build:

```bash
cd neuro-symbolic-interactive-game-research-2026
./scripts/build_godot_web.sh                                   # disposable-copy Web export -> game-track/web/public/ (ignored)
python3 -m http.server 4173 --bind 127.0.0.1 --directory game-track/web
open http://127.0.0.1:4173/dashboard/                          # game at /public/, dashboard at /dashboard/
```

The boundary is one-directional: the game mirrors typed events through `window.parent.postMessage` only when embedded; the page has no channel back into the game and never receives sealed fact IDs. The recorded route produced 3 commits and 1 hold (`FORBIDDEN_DISCLOSURE` → DISCLOSURE family) with the hash chain `f488d9c4…812c → 19b474dc…c498 → 93381457…b900 → 4b231017…8892`.

## Slides

A 16-slide overview deck, in Korean, as a self-contained HTML file: [`trace-rpg-overview.ko.html`](neuro-symbolic-interactive-game-research-2026/docs/slides/trace-rpg-overview.ko.html) (arrows or space to navigate, `?` for help). English captions below; the deck follows the same flow as this README.

<table>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-01.jpg" alt="Slide 1"><br><sub>01 · Title</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-02.jpg" alt="Slide 2"><br><sub>02 · The problem: fluent text ≠ valid event (six failure kinds)</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-03.jpg" alt="Slide 3"><br><sub>03 · The bank-counter analogy</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-04.jpg" alt="Slide 4"><br><sub>04 · Pipeline: propose → parse → policy → 7 checks / 6 families → repair or fallback → commit → record → replay</sub></td>
  </tr>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-05.jpg" alt="Slide 5"><br><sub>05 · Six state-relative families, seven checks, with game examples</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-06.jpg" alt="Slide 6"><br><sub>06 · Guided repair: the ρ loop and the four arms</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-07.jpg" alt="Slide 7"><br><sub>07 · SHA-256 receipt chain and semantic replay</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-08.jpg" alt="Slide 8"><br><sub>08 · Contributions C1–C5</sub></td>
  </tr>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-09.jpg" alt="Slide 9"><br><sub>09 · Evidence lanes E1 / E2 / E3 / ENG1 and their ceilings</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-10.jpg" alt="Slide 10"><br><sub>10 · Offline repair-arm bar chart</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-11.jpg" alt="Slide 11"><br><sub>11 · Live screening table and KG numbers</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-12.jpg" alt="Slide 12"><br><sub>12 · Game episode loop and the authority boundary</sub></td>
  </tr>
  <tr>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-13.jpg" alt="Slide 13"><br><sub>13 · The HELD screen as rule learning</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-14.jpg" alt="Slide 14"><br><sub>14 · Contribution readout: CONTRIBUTION / UNLOCKED / CASE CHAIN and the two-part receipt</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-15.jpg" alt="Slide 15"><br><sub>15 · What the evidence says vs. does not say</sub></td>
    <td><img src="neuro-symbolic-interactive-game-research-2026/docs/readme/slides/ko-16.jpg" alt="Slide 16"><br><sub>16 · Next steps and a three-line summary</sub></td>
  </tr>
</table>

## Reproduce

```bash
cd neuro-symbolic-interactive-game-research-2026
uv sync                                              # Python 3.11+
uv run python -m pytest -q                           # unit + contract tests
uv run python scripts/validate_project.py            # structure, schemas/bridge, SVG, evidence contracts
uv run python scripts/validate_contribution_crosswalk.py
uv run python scripts/validate_visual_assets.py --require-pdf-tools
./scripts/validate_game_track.sh                     # Godot 4.7.1 on PATH: fixtures, smoke, balance probe
uv run python scripts/run_playable_evaluation.py     # SL-PLAY-EVAL-001 on a disposable project copy
./scripts/verify_like_ci.sh                          # the CI-equivalent gate
make -C paper/latex check                            # EN (pdflatex) + KO (xelatex) PDFs, page band, Type 3 check
```

- `uv sync` — installs the locked Python 3.11+ environment.
- `pytest` — parser, validator, repair, replay, integrity, and accounting contracts.
- `validate_project.py` — repository structure, JSON schemas and the game bridge, SVG sources, source manifests, and the evidence/analysis contracts.
- `validate_contribution_crosswalk.py` — C1–C5, the 55 references, and the four evidence lanes stay mutually consistent in both manuscripts.
- `validate_visual_assets.py` — every figure and table in the paper resolves to its editable source and data.
- `validate_game_track.sh` — Godot fixtures, the 3D smoke, and the archetype balance probe.
- `run_playable_evaluation.py` — SL-PLAY-EVAL-001 (52 checks) on a disposable copy of the project.
- `verify_like_ci.sh` — the same gate the `validate` workflow runs.
- `make -C paper/latex check` — rebuilds both PDFs and rejects page-band and Type 3 font regressions.

Packets: offline pilot (frozen, hash-bound) in [`research/academic-pipeline/stage-04-pilot/`](neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/stage-04-pilot/); live screening in [`research/academic-pipeline/rq2-live-pilot/`](neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/rq2-live-pilot/); KG simulation in [`research/simulation/kg-ontology/`](neuro-symbolic-interactive-game-research-2026/research/simulation/kg-ontology/); playable evaluation in [`game-track/godot/docs/latest/`](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/).

## Fixed-goal NPC operator lane (protocol 1.1)

The current NPC integration is a fixed-goal `sealed-lighthouse-v1` controller. Godot is the sole canonical-state writer; Python interprets typed intent and runs bounded BFS over the six-field public observation only. It never reads hidden world state or performs novel planning. `acquire_object` and `install_lens` are explicit player requests; only Captain Mira may issue `reveal_hint` after signal restoration, tide-lead authorization, and open dialogue.

The wire contract is `npc-goal-recovery/1.1.0`. P invokes the official authenticated Codex OAuth CLI adapter with no rule fallback. R is the authored rule/grammar control; O is a same-model-family, public-input-only auxiliary arm, not independent gold. The loopback service binds to `127.0.0.1:8768` and accepts exactly `http://127.0.0.1:8877` and `http://localhost:8877`; `TRACE_RPG_NPC_CAPABILITY` is transient and the capability is sent only in `X-NPC-Capability`. Episode budgets are cumulative across utterance epochs: 30,000 ms intent, 900,000 ms episode, 8 intent calls, 32 action attempts, 16 replans, 32 plan expansions, and one in-flight request. The allocation is 16 engineering R observations plus 72 screening observations (P/R/O × 2, 24 each), 88 total; arm totals are R=40, P=24, O=24. Input/output tokens, cost, and returned model revision are unavailable and remain `null`.

**Validated-v5 evidence.** The corpus has 28 cases (16 engineering + 12 screening). The immutable canonical packet at `research/academic-pipeline/npc-goal-recovery/verified-run-002/` contains all 88 assigned rows and passes strict validation, including 24 observed authenticated CLI executions explicitly requesting `gpt-5.6-sol`. The returned model revision, provider seed, token accounting, and cost are unavailable. Each screening arm retains 20 completed executions and 4 assigned stale-control ACK rejections; 4/24 observed goal counts are not recovery-rate or efficacy estimates. O's same-family designation is a protocol source label, not a verified match to P. The unknown-model `verified-run-001/`, failed diagnostics, and source-bound native demonstrations remain separate, immutable evidence; none are pooled with this cohort. No efficacy, superiority, generalization, human benefit, or independent labels are claimed.

From the project root, confirm OAuth and run the explicit Codex service arm (no hidden rule fallback):

```bash
codex login status
uv run python scripts/run_npc_service.py \
  --backend codex --model gpt-5.6-sol --host 127.0.0.1 --port 8768 \
  --allow-origin http://127.0.0.1:8877 \
  --allow-origin http://localhost:8877
```

Canonical packets are immutable. For a new model-pinned cohort, replace `NEW-ID` below with an unused identifier; do not overwrite or pool either historical cohort. Preflight/dry-run output must also use a fresh noncanonical directory. Revalidate the saved canonical packet by passing `research/academic-pipeline/npc-goal-recovery/verified-run-002` to the validator only.

```bash
uv run python scripts/run_npc_goal_experiment.py \
  --packet all --model gpt-5.6-sol \
  --engineering-fixtures data/fixtures/npc-goal-recovery/validated-v5/engineering.json \
  --screening-fixtures data/fixtures/npc-goal-recovery/validated-v5/screening.json \
  --output-dir _workspace/current/qa/npc-rerun-NEW-ID \
  --godot-project game-track/godot

uv run python scripts/validate_npc_goal_evidence.py \
  --packet all \
  --root "$PWD" \
  --packet-dir _workspace/current/qa/npc-rerun-NEW-ID
```

Only a passing validator permits final packet outcomes and bilingual paper-fragment regeneration; preflights and historical packets remain diagnostic.

## Boundaries and disclosure

The paper states these boundaries, and so does this README:

- One authored world; all fixtures and the playable share a single frozen world state.
- One hosted proposer with an unpinned revision; live screening is pilot-only.
- No participants, no affect or usability data, no efficacy claim.
- Unkeyed hashes give integrity, not authentication.
- Engine evidence is conformance, not performance.
- The human gates — G4 (presentation) and G6 (production) — remain open.

**AI disclosure.** Large language models assisted prose, code, and test drafting and citation checks; a hosted model produced the labelled live-screening candidates. Every reported count comes from a deterministic runner or a hash-bound receipt. UI art in the playable is curated AI-generated imagery (Higgsfield) with per-file provenance and a procedural fallback; the player rig is a curated Higgsfield GLB; Mixamo raw files are never tracked.

License: to be announced.

## Cite

```bibtex
@misc{tracerpg2026,
  title = {TRACE-RPG: A Trace-Linked Symbolic Commit Gate for Generated Events in an Interactive Game World},
  year  = {2026},
  note  = {Manuscript under anonymous review},
  url   = {https://github.com/akillness/neural_symbolic_in_game}
}
```
