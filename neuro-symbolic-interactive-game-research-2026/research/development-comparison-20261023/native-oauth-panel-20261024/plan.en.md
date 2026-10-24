# Native OAuth panel plan v3

**Study label:** `development-comparison-20261023/native-oauth-panel-20261024`  
**Status:** `FROZEN_NOT_EXECUTED`  
**Freeze date:** 2026-10-24  
**Owner:** Native-study contract and immutable evidence controller

## 1. Decision and boundary

The user decision is preserved verbatim: `oauth 인증받은 codex, claude, agy --dangerously-skip-permissions 이용한 cli 로 실험`. It amends the new stage from strict API-only to authenticated native Codex, Claude and agy CLI operation. It does not authorize a provider call by this owner, an API fallback, a new API key, or a result claim.

The factor is **system/agent-mediated permission mode**, not a pure-model or ontology causal-efficacy factor. Requested label, runtime-reported model, provider-returned model, weights/revision, seed, usage, latency and billed USD remain separate; unknown values stay `null`.

The old API route was never called and is retired with a review block. The four old Argon attempts under `native-argon-probe-20261024-01` and `native-argon-probe-20261024-02-b1only` remain immutable historical/feasibility evidence, not new results or independent repeats.

## 2. Frozen artifacts

Read these artifacts together; they are the source of truth for this stage:

1. `authorization-v3.json` — permission amendment, CLI boundary, billing and safety gate.
2. `protocol.json` — factors, evidence contract, status ledger and stop rules.
3. `schedule.json` — deterministic seed and stage order.
4. `frozen-inputs.json` — C1/B1 task-local inputs, source hashes, prompt hashes and B1 file manifest.
5. `assignment-manifest.json` — all 36 assignment IDs and per-assignment hash references.

The frozen-input digest is `72f29c460e657e1d70f770f353d01274182a1a68ab15c27e70eb809a194d52c1`. These files are frozen before any new stage call. No C2, H1 or other held-out payload is included or reconstructed here.

## 3. Exact candidates and matched factors

The nine contractual labels are exact and case-sensitive:

| Provider family | Candidate label | Requested CLI selector |
|---|---|---|
| OpenAI | `gpt-6.1-sol` | `gpt-6.1-sol` |
| OpenAI | `gpt-6-sol` | `gpt-6-sol` |
| OpenAI | `Astra` | `gpt-6-astra` |
| OpenAI | `Luna` | `gpt-6-luna` |
| Anthropic | `Opus5.5` | `claude-opus-5-5` |
| Anthropic | `literal 'sonnect5.5'` | `claude-sonnet-5-5` |
| Anthropic | `Fable5.1` | `claude-fable-5-1` |
| Google | `literal 'gemin3.8flash'` | `gemini-3.8-flash` |
| Google | `GeminiArgon` | `gemini-4-argon-medium` |

The display/selector mapping is a requested route, not provider attestation. `GeminiArgon`'s native agy catalog selector is recorded separately from its registry selector. No label is silently normalized or replaced.

Each candidate receives both independent task arms (`C1` content generation and `B1` coding) under both representations (`general_rule` and `ontology`). Within a candidate, the counterpart arm stays scheduled regardless of the other arm's raw validity, failure or timeout.

## 4. Frozen inputs

`C1` keeps the source task at `panel-c1-001`, with `dock` and `tower` locations, `lens` at `dock`, `sealed_scroll` at `tower`, `met_keeper` and `lens_in_hand`, and the `INSTALL_LENS -> signal_restored` policy while withholding `vault_code`. Its source/task hash is `abc8ff7349ee0229870b1d017e0732e77cd47d4e001305e2ece07aa759eee5f3`; representation inventory hash is `ebc31f1535d694eb71c023ebf782231e5cb5978f12a6bf3987998c03988020e0`.

`B1` is the task-local harbor/lighthouse contract. It uses the ten frozen acceptance IDs `AC-SCENES`, `AC-MOVEMENT`, `AC-GAME-GOAL`, `AC-ONTOLOGY-GATE`, `AC-REPAIR`, `AC-REPLAY`, `AC-READONLY-SIGNALS`, `AC-SAVE-LOAD`, `AC-BUILD`, and `AC-DETERMINISTIC-QA`. Its task-local API is `project.godot` plus `main.gd`, with generated relative files only under `game/*.gd` and `game/*.tscn`; no symlinks, replacements or downloads. The authoritative scenes are `harbor` and `lighthouse`. The root shared `game_api` is unused.

B1 source/task hash is `70d8a14a219b99f4823318ad57dbe3bfb6a61d5d5a9c57c3f8b75403e162dabd`; representation inventory hash is `b34022f80d779541ca056275e3992d62d257297c13e3e3c99d52b3afab39280e`.

Prompts are generated only by `src/nesy_game/model_panel.py::build_prompt`, using `proposition_views`; C1/B1 hard content checks use `content_grade`. Prompt hashes are in `frozen-inputs.json` and repeated per assignment through `assignment-manifest.json` references.

## 5. Schedule and launch caps

- `F0`: read-only OAuth status, source/hash, observer and transport preflight; zero provider calls.
- `F1`: 18 predeclared `general_rule` assignments: one C1 and one B1 for each candidate.
- `F2`: 18 predeclared matched `ontology` assignments: one C1 and one B1 for each candidate.
- Total: exactly 36 predeclared assignments, all with fresh disposable workspaces and fresh sessions.
- Seed: `20261023`; order is frozen in `schedule.json`.
- Per launch cap: 180 seconds; no retry, resume or fallback; no additional G1 credits.

The hard USD 100 value is not enforceable by the native CLIs, so its gate is `UNVERIFIED_NOT_ENFORCEABLE_BY_NATIVE_CLI` and does not pass. Billing is recorded as native subscription quota; `billed_usd` remains `null`. Stop at USD 80 only if a trustworthy native receipt reports spend; this is not a price reserve.

## 6. Exact native CLI boundary

The transport owner supplied these source-supported command shapes:

- Codex: `codex exec --json --ephemeral --skip-git-repo-check --ignore-user-config --ignore-rules -s read-only --config approval_policy=never --model <exact-selector> -C <fresh-cwd>` with prompt on stdin. Do not use `--dangerously-bypass-approvals-and-sandbox`.
- Claude: `claude -p --model <exact-selector> --dangerously-skip-permissions --disable-slash-commands --no-session-persistence --output-format stream-json --tools ''`. Do not use `--bare`.
- agy: `agy --print <prompt> --sandbox --dangerously-skip-permissions --disable-slash-commands --model <exact-selector> --effort medium --output-format stream-json --print-timeout 180s`. The B1 plan-mode flag is used only if an exact existing help/probe receipt proves it. agy global tool availability is `UNVERIFIED`, never “absent.”

OAuth status preflight is read-only and does not read auth files or email. Environment projection allows only `PATH`, `HOME`, `TMPDIR`, locale/terminal identity variables and records removed secret/provider-routing names without values.

## 7. Evidence, safety and claims

Every assignment must persist the source hashes, task/prompt/inventory hashes, selector, fresh workspace/session IDs, context/session hash, all stdout/stderr/partial stream, usage, latency, runtime/provider identities, revision, seed, billed USD, failure and stop reason as data arrives. At freeze all runtime fields are `null`, `launched=0`, and no attempt artifact exists.

Do not execute generated Godot code. B1 host QA remains blocked pending the separate sandbox-gate repair and fresh checker/profile proof; no model self-report is an AC pass. C1 hard validity is separate from quality and novelty, with no composite score and no repair unless separately approved.

No artifact here may claim model superiority, ontology superiority, causal efficacy, productivity, player benefit, API price, provider identity or revision, or a new result inherited from Argon history. Failures, blocked calls, timeouts and missing evidence remain their original statuses and denominators.

**Next action:** the transport owner may run only the read-only OAuth status/preflight against this frozen manifest, then attach a receipt without changing these files.
