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

![Current-source ending still captured on 2026-11-03: the investigator's contribution and validator receipt; engineering presentation, not a model result](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-ending.png)

- **The gate.** Every generated event is treated as an untrusted transaction proposal. A type-strict parser, an external action policy, and seven deterministic checks in six state-relative families decide whether it commits; a rejected candidate gets bounded, counterexample-guided repair, and everything else falls back to the unchanged prior state.
- **The game.** *The Sealed Lighthouse* is a turn-based investigation micro-RPG in Godot 4.7.1 whose in-world ledger shows the gate diegetically: a hold names the family that held it and teaches the rule; a commit posts a contribution, unlocks the next lead, and extends a SHA-256 receipt chain.
- **The evidence — and its limits.** Four lanes (E1 offline fixtures, E2 live screening, E3 KG simulation, ENG1 engine conformance) report exact counts only: 13/13 gate agreement, ρ 5/5 on the guided-repairable class, 52/52 core playable checks plus the 4/4 D-073 extension, one shared terminal state hash. One authored world, one hosted proposer, no participants, no efficacy claim.

<!-- prospective-pilot:start -->
## Prospective comparison — 2026-11-03

Study: `prospective-pilot-20261103`. Status: **NOT_RUN/BLOCKED**; conclusion: `NOT_MET`.

| Track | Planned | Blocked | Assigned | Attempted | Executed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Runtime | 60 | 60 | 0 | 0 | 0 |
| Development | 120 | 120 | 0 | 0 | 0 |

The requested panel is Codex `gpt-5.6-sol`, Codex `gpt-6.1-sol`, and Antigravity `gemini-3.8-flash-medium`, with nominal medium effort. Runtime compares identical-information general rules and ontology over ten fresh resets; bounded development crosses those representations with minimal input/public-repository exploration, five tasks and two fresh runs. These are planned assignments, not completed model runs. Served identity, enforceable no-credit operation, isolation and a new activation remain unproved; no inference was launched. Success rates, effects, costs and intervals are unmeasured, not zero.
<!-- prospective-pilot:end -->

[Frozen protocol](neuro-symbolic-interactive-game-research-2026/research/prospective-pilot-20261103/protocol-v1.json) · [Retained counts](neuro-symbolic-interactive-game-research-2026/research/prospective-pilot-20261103/results-v1/summary.json) · [Independent offline task controls](neuro-symbolic-interactive-game-research-2026/research/prospective-pilot-20261103/task-freeze-v1.json). Five task oracles each accepted two correct variants and rejected two defective/wrong variants; leakage checking covered 9,303 files. This is fixture evidence, not model efficacy. The historical eight-row 5/8 pilot, stopped identity extension, local Ollama observations and single development case remain separate. Exhaustive search by newer agents is an untested hypothesis, not an assumed capability.

## Paper at a glance

![Figure 1: the transaction pipeline — propose, parse, policy, seven checks in six families, bounded repair or unchanged fallback, commit, record, replay — with the ledger grammar band the player reads](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_architecture.png)

**TRACE-RPG: Source-Bound Ontology Evidence and a Bounded Codex-Assisted Integration Case in an Interactive Game.** The current local PDFs measure **17 pages in English and 17 in Korean** (2026-11-10), with the existing manuscript organization and font sizes retained. Figures 5 and 6 appear on pages 10 and 11 in both languages. This is an anonymous-review working draft, not a claim of meeting a ten-page venue limit, journal submission or acceptance. Citation-identity, context and preprint-status checks for its 58 references remain recorded separately.

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

[![Contact sheet of all 17 English manuscript pages, rendered from the current 2026-11-10 PDF](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/paper-en-pages.png)](neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.pdf)

## Evidence

The four historical lanes below retain their original counts and ceilings; they are not pooled with the separate v5 development collection. Every number is a raw count from a deterministic runner or a hash-bound receipt; no inferential statistics are reported.

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

### Separate v5 paired-selector development collection — 2026-11-10

Five synthetic development fixtures × two feedback conditions × two requested selectors produced **20 received responses: 10 schema failures, 10 strictly parsed candidates, 8 gate acceptances and 7 independently specified goals reached**. Every row below retains all five assignments in its denominator; receipt is not task success, and an accepted commit can miss the goal.

| Requested selector | Feedback | Received | Schema failure | Strictly parsed | Gate accepted | Goal reached |
|---|---|---:|---:|---:|---:|---:|
| `gpt-5.6-luna` | Detailed | 5/5 | 1/5 | 4/5 | 4/5 | 3/5 |
| `gpt-5.6-luna` | Generic | 5/5 | 0/5 | 5/5 | 3/5 | 3/5 |
| `gpt-5.6-terra` | Detailed | 5/5 | 5/5 | 0/5 | 0/5 | 0/5 |
| `gpt-5.6-terra` | Generic | 5/5 | 4/5 | 1/5 | 1/5 | 1/5 |

Luna reached 6/10 goals and Terra 1/10, descriptively. These are requested selectors, not attested served identities; actual identity, provider request count and cost are unknown. The small synthetic set is not held out, feedback information is unequal, and the nominal serial order was Luna then Terra. This is neither a human nor causal study and supports no model-superiority, ontology-efficacy or user-benefit claim. Earlier incomplete/diagnostic cohorts, the exploratory single case, the prospective pilot and NPC validated-v5 remain separate.

Public inputs: [Luna results](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-v5/paired-model-comparison-20261110-v5-gpt-5.6-luna/results.json) · [Terra results](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-v5/paired-model-comparison-20261110-v5-gpt-5.6-terra/results.json) · [20 copied prompts](neuro-symbolic-interactive-game-research-2026/research/codex_feedback_pilot/public-v5/). The projections null only `metadata.codex_executable` and add the raw-file SHA-256 and omission receipt; outcomes, prompt hashes and executable hash/version remain. Raw cohorts and approvals remain local and unchanged. The common seven-file source ZIP establishes parent provenance only, not a standalone reproducer.

![Figure 5: source-derived v5 state-signal diagram showing detailed typed errors versus generic rejection, followed by strict parsing, candidate-ID checking, seven-predicate revalidation, commit or unchanged fallback, and a separate goal check](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_state_signal.png)

The signal explains rejection; it grants no mutation authority and estimates no affect. This authored diagram uses the frozen collector and recorded signal fields. After the single response, the v5 collector allows no further repair call; only revalidation can authorize commit.

![Figure 6: frozen v5 collection flow from 20 assignments and responses to 10 parsed candidates, 8 accepted commits and 7 goals, with all 20 per-fixture outcomes and dispatch-to-terminal seconds including schema failures](neuro-symbolic-interactive-game-research-2026/paper/latex/figures/fig_paired_feedback_flow.png)

The flow and matrix preserve all ten schema failures and the one accepted commit that missed its goal. Seconds include failed responses and measure dispatch to terminal, not model-only latency.

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
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-arrival.png" alt="2026-11-03 current-source arrival before any proposal"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-refusal.png" alt="Current-source HOLD: the gate names its family and preserves the prior state"></td>
  </tr>
  <tr>
    <td align="center"><sub>Arrival — fresh disposable engine capture</sub></td>
    <td align="center"><sub>HOLD — unchanged prior state</sub></td>
  </tr>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-authorized_hint.png" alt="Current-source authorized COMMIT with contribution and next affordance"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/native-ending.png" alt="Current-source ending and validator receipt"></td>
  </tr>
  <tr>
    <td align="center"><sub>COMMIT — authorized progression</sub></td>
    <td align="center"><sub>Ending — validator receipt</sub></td>
  </tr>
</table>

**Historical production captures below:** retained as dated deployment evidence, not recaptured current-source or newly deployed bytes.

<p align="center">
  <img width="32%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-start.png" alt="Production deployment on a mobile viewport: start screen">
  <img width="32%" src="neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-in-game.png" alt="Production deployment on a mobile viewport: in-game ledger">
</p>

The fresh still sequence above replaces the active historical gameplay GIF. Its four 1280×720 captures came from a disposable current-source Godot build (4/4 fixtures, 52/52 core checks and 4/4 captured states); they are not usability or model-efficacy evidence. [Capture manifest](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/manifest.json) records source, UTC, dimensions, bytes, SHA-256 and available state/event bindings. Historical originals and hash-bound receipts remain preserved. UI art is curated Higgsfield imagery with per-file provenance and procedural fallback; the player rig is a curated Higgsfield GLB (Idle / Casual_Walk), and Mixamo raw files are never tracked. Movement, camera, VFX, audio and UI do not mutate canonical state; only the proposal router and validator do, with no live Python round trip in the engine slice.

## Live commit-gate dashboard

**2026-11-03 current-source local capture:** real browser input completed arrival → HOLD → three COMMITs → ending, with one hold and state-bound dashboard readouts. This is an operator-driven presentation route, not a model assignment. Capture attempt 1 completed with **five pointer-lock page errors**; two bounded yaw/lock retries also remain in the diagnostic record. The clean-browser gate is **NOT_PASS**, not silently promoted by readable screenshots. No deployment, usability, immersion or model-benefit claim follows.

The current still sequence below replaces the old dashboard GIF and earlier-renderer display copies. Immutable historical captures and failure receipts are retained.

![Current-source dashboard arrival on 2026-11-03: stage 0, no commits and no holds](neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-arrival.png)

<table>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-hold.png" alt="Current local stage-gated disclosure HOLD: initial state hash unchanged"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-commit.png" alt="Current local lens acquisition: stage 0 to 1, one commit and one hold"></td>
  </tr>
  <tr>
    <td align="center"><sub>Hold</sub></td>
    <td align="center"><sub>Commit</sub></td>
  </tr>
  <tr>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-complete.png" alt="Current local ending: three commits and one hold"></td>
    <td><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-last-action.png" alt="Current local last-action and verdict-history readout"></td>
  </tr>
  <tr>
    <td align="center"><sub>Current-source ending · 3 commits / 1 hold</sub></td>
    <td align="center"><sub>Current-source read-only verdict history</sub></td>
  </tr>
</table>

**Historical production endpoint:** [sealed-lighthouse-trace-rpg.vercel.app](https://sealed-lighthouse-trace-rpg.vercel.app). The recorded 2026-09-03 deployment redirected the site root to `/dashboard/` and served the embedded game at `/public/`; its recorded desktop/390×844 checks are historical. This refresh neither redeploys nor establishes that production bytes match the new local captures.

<p align="center"><img width="100%" src="neuro-symbolic-interactive-game-research-2026/docs/readme/prospective-20261103/browser-dashboard-signals.png" alt="2026-11-03 current-source local read-only disclosure signals"></p>

To run it locally, the dashboard embeds the local Web build:

```bash
cd neuro-symbolic-interactive-game-research-2026
./scripts/build_godot_web.sh                                   # disposable-copy Web export -> game-track/web/public/ (ignored)
python3 -m http.server 4173 --bind 127.0.0.1 --directory game-track/web
open http://127.0.0.1:4173/dashboard/                          # game at /public/, dashboard at /dashboard/
```

The boundary is one-directional: the embedded game mirrors typed events through `window.parent.postMessage`; the page has no command channel back into the game and receives no sealed fact IDs. The fresh route recorded 3 commits and 1 hold. Its `STAGE_GATED_DISCLOSURE` hold preserved the initial state hash; the capture manifest retains the actual state/event bindings. These observations concern the current local route, not a newly deployed service or model performance.

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
uv run python scripts/generate_paired_feedback_figures.py --check  # frozen public inputs -> SVG drift check; no model call
ARCHIVED_NPC_SOURCE="$(mktemp -d)"                    # explicit empty directory for historical source
git archive --format=tar fa9fb8a2c2249e35eddc7d4e0951c15a7b4bea09:neuro-symbolic-interactive-game-research-2026 | tar -xf - -C "$ARCHIVED_NPC_SOURCE"
make -C paper/latex check NPC_PAPER_EVIDENCE_ROOT="$ARCHIVED_NPC_SOURCE"
```

- `uv sync` — installs the locked Python 3.11+ environment.
- `pytest` — parser, validator, repair, replay, integrity, and accounting contracts.
- `validate_project.py` — repository structure, JSON schemas and the game bridge, SVG sources, source manifests, and the evidence/analysis contracts.
- `validate_contribution_crosswalk.py` — C1–C5, the 58 references, and the four evidence lanes stay mutually consistent in both manuscripts.
- `validate_visual_assets.py` — every figure and table in the paper resolves to its editable source and data.
- `validate_game_track.sh` — Godot fixtures, the 3D smoke, and the archetype balance probe.
- `run_playable_evaluation.py` — SL-PLAY-EVAL-001 (52 checks) on a disposable copy of the project.
- `verify_like_ci.sh` — the same gate the `validate` workflow runs.
- `generate_paired_feedback_figures.py --check` — checks the two generated SVG sources against the frozen public v5 projections without rewriting or making model calls; PNG/PDF derivatives are built by the paper pipeline.
- `make -C paper/latex check NPC_PAPER_EVIDENCE_ROOT="$ARCHIVED_NPC_SOURCE"` — rebuilds both PDFs and checks source-bound evidence, positive page counts and Type 3 fonts. The archived project at the explicit revision supplies the historical NPC006 source, not current-runtime authority. This archived-source check passed; the default check without an archive remains **FIX** because NPC006 does not match current source. No current-source full-CI pass is claimed.

Packets: offline pilot (frozen, hash-bound) in [`research/academic-pipeline/stage-04-pilot/`](neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/stage-04-pilot/); live screening in [`research/academic-pipeline/rq2-live-pilot/`](neuro-symbolic-interactive-game-research-2026/research/academic-pipeline/rq2-live-pilot/); KG simulation in [`research/simulation/kg-ontology/`](neuro-symbolic-interactive-game-research-2026/research/simulation/kg-ontology/); playable evaluation in [`game-track/godot/docs/latest/`](neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/).

## Fixed-goal NPC operator lane (protocol 1.1)

The current NPC integration is a fixed-goal `sealed-lighthouse-v1` controller. Godot is the sole canonical-state writer; Python interprets typed intent and runs bounded BFS over the six-field public observation only. It never reads hidden world state or performs novel planning. `acquire_object` and `install_lens` are explicit player requests; only Captain Mira may issue `reveal_hint` after signal restoration, tide-lead authorization, and open dialogue.

The wire contract is `npc-goal-recovery/1.1.0`. P invokes the official authenticated Codex OAuth CLI adapter with no rule fallback. R is the authored rule/grammar control; O is a same-model-family, public-input-only auxiliary arm, not independent gold. The loopback service binds to `127.0.0.1:8768` and accepts exactly `http://127.0.0.1:8877` and `http://localhost:8877`; `TRACE_RPG_NPC_CAPABILITY` is transient and the capability is sent only in `X-NPC-Capability`. Episode budgets are cumulative across utterance epochs: 30,000 ms intent, 900,000 ms episode, 8 intent calls, 32 action attempts, 16 replans, 32 plan expansions, and one in-flight request. The allocation is 16 engineering R observations plus 72 screening observations (P/R/O × 2, 24 each), 88 total; arm totals are R=40, P=24, O=24. Input/output tokens, cost, and returned model revision are unavailable and remain `null`.

**Validated-v5 evidence.** The corpus has 28 cases (16 engineering + 12 screening). The immutable canonical packet at `research/academic-pipeline/npc-goal-recovery/verified-run-006/` contains all 88 assigned rows and passes strict validation. 24 authenticated CLI executions: all 24 requested and returned model IDs are null, alongside provider revision, provider seed, token accounting, and cost all null. Each screening arm retains 20 completed executions and 4 assigned stale-control ACK rejections; 4/24 observed goal counts are not recovery-rate or efficacy estimates. O's same-family designation is a protocol source label, not a verified match to P. Unknown-model `verified-run-001/` with failed diagnostics, historical batch `verified-run-002/` and `verified-run-003/`, and source-bound native demonstrations remain separate, immutable evidence; none are pooled with this cohort. No efficacy, superiority, generalization, human benefit, or independent labels are claimed.

From the project root, confirm OAuth and run the explicit Codex service arm (no hidden rule fallback):

```bash
codex login status
uv run python scripts/run_npc_service.py \
  --backend codex --model gpt-5.6-sol --host 127.0.0.1 --port 8768 \
  --allow-origin http://127.0.0.1:8877 \
  --allow-origin http://localhost:8877
```

Canonical packets are immutable. For a new model-pinned cohort, replace `NEW-ID` below with an unused identifier; do not overwrite or pool either historical cohort. Preflight/dry-run output must also use a fresh noncanonical directory. Revalidate the saved canonical packet by passing `research/academic-pipeline/npc-goal-recovery/verified-run-006` to the validator only.

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

**Provenance exceptions.** Three historical QA presentation copies intentionally omit private rig/cache payloads, so their old whole-tree manifests are not byte-complete public reconstructions. Two historical unit-test RED receipts were overwritten; their original byte identities were not recovered, and the labelled reconstruction is not original evidence. The [dated provenance disclosure](llm-wiki/wiki/reports/2026-10-15-npc-goal-operation-implementation.md#historical-unit-test-receipt-losses-and-explicit-corrections) identifies the affected receipts and separately documents the public-copy omissions. These QA exceptions must not be conflated with the retained, separately hash-verified canonical experiment packets.

**AI disclosure.** Large language models assisted prose, code, and test drafting and citation checks; a hosted model produced the labelled live-screening candidates. Every reported count comes from a deterministic runner or a hash-bound receipt. UI art in the playable is curated AI-generated imagery (Higgsfield) with per-file provenance and a procedural fallback; the player rig is a curated Higgsfield GLB; Mixamo raw files are never tracked.

License: to be announced.

## Cite

```bibtex
@misc{tracerpg2026,
  title = {TRACE-RPG: Auditable Neuro-Symbolic Commit Gates for Interactive Game Worlds},
  year  = {2026},
  note  = {Draft prepared for anonymous review; no submission or acceptance claimed},
  url   = {https://github.com/akillness/neural_symbolic_in_game}
}
```
