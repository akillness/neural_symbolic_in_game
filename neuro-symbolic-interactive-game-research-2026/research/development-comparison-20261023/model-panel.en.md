# Expanded model panel — English evidence

**Study:** `development-comparison-20261023`  
**Evidence date:** Initial evidence date 2026-10-23; updated with observations retrieved 2026-10-24
**Registry:** [`model-registry.json`](./model-registry.json)  
**Panel status:** `PROPOSED_NOT_EXECUTED`  
**Measured runs:** `0`  
**Evidence count:** 56 records — 47 public-source records, 6 native safe-command receipts, 1 supplied Jev advisory receipt, and 2 plain user-decision receipts.

This panel is identity/access preflight evidence, not generated-content evidence and not a coding experiment result. `raw_user_label` preserves the exact user strings supplied by Main. `protocol_label` preserves the current plan/protocol spelling, while `display_alias` is presentation only. `canonical_id` records the documented candidate selected by explicit user confirmation or editorial normalization where supported by official documentation; editorial normalization is not provider attestation, and runtime/provider identity remains separate.

## 1. Nine-candidate comparison

| # | `raw_user_label` | `protocol_label` | `protocol_candidate_id` | `canonical_id` (verified candidate or `null`) | Provider / mapping confidence | Source IDs | Experiment / launch status |
|---:|---|---|---|---|---|---|---|
| 1 | `gpt 6.1 sol` | `gpt-6.1-sol` | `gpt_6_1_sol` | `gpt-6.1-sol` | OpenAI; exact public ID and bundled catalog entry | O1,O3,O4,O5,N-OAI-1..3 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 2 | `gpt 6 sol` | `gpt-6-sol` | `gpt_6_sol` | `gpt-6-sol` | OpenAI; exact public ID and bundled catalog entry | O2,O3,O4,O5,N-OAI-1..3 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 3 | `astra` | `Astra` | `astra` | `gpt-6-astra` | OpenAI; user-confirmed GPT-6 Astra with official/catalog evidence; Project Astra excluded | A1,A2,A3,O4,O5,C1,C2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 4 | `luna` | `Luna` | `luna` | `gpt-6-luna` | OpenAI; user-confirmed GPT-6 Luna with official/catalog evidence; other generations/products excluded | L1,L2,L3,L4,O4,O5,C2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 5 | `opus 5.5` | `Opus5.5` | `opus_5_5` | `claude-opus-5-5` | Anthropic; official model ID, provider deployment still unbound | P1,P3,P4,P5,P6,P7,P8,N-CLAUDE-1..2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 6 | `sonnect 5.5` | `ClaudeSonnet5.5` | `literal_sonnect_5_5` | `claude-sonnet-5-5` | Anthropic; editorial normalization of obvious typo, official ID documented, provider attestation unverified | P2,P3,P4,P6,P7,N-CLAUDE-1..2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 7 | `fable 5.1` | `Fable5.1` | `fable_5_1` | `claude-fable-5-1` | Anthropic; official model ID, runtime/provider identity still unverified | F1,F2,F3,F4,F5,F6,P7,N-CLAUDE-1..2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_FALLBACK_PARITY_AND_CAPS` |
| 8 | `gemin 3.8flash` | `Gemini3.8Flash` | `literal_gemin3_8_flash` | `gemini-3.8-flash` | Google; editorial normalization of obvious typo, official ID documented, provider attestation unverified | G1,G2,G4,G5,G7,G8,G9,G10,G11,G13,G14,G15,G16,G19 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 9 | `gemini argon` | `GeminiArgon` | `gemini_argon` | `gemini-4-argon` | Google public candidate; App backing identity is not attested | G1,G3,G5,G6,G7,G8,G9,G10,G11,G12,G13,G14,G15,G16,G19,G21 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |

All rows have `measured_runs: 0`. A plain user decision receipt dated 2026-10-23 approves an aggregate additional API budget cap of USD 100 for both tracks; per-run, token, wall-time, tool-call, repair and intervention caps remain `null`, so launch remains fail-closed. No protocol-conforming API panel inference was observed; two separate native C1 feasibility launches were observed, not as a comparative result. Account entitlement, provider-returned identity, serving revision, seed, incurred cost, effective tool manifest and experiment efficacy remain unverified or null.

## 2. Candidate evidence and interface boundary

### 2.1 OpenAI candidates

1. **`gpt 6.1 sol` → `gpt-6.1-sol`.** The official card gives the exact ID and Responses/Chat Completions surface [O1]. The installed Codex CLI was `0.163.0`; its bundled catalog listed a separate `gpt-6.1-sol` entry [N-OAI-1,N-OAI-3]. The model-only arm is a proposed Responses request with tools excluded. The coding arm is a separate proposed Codex CLI arm using `-m/--model`; documented native tools include unified execution, freeform patching and web search [O5]. The catalog default reasoning level is `low`, while the API default is `medium`; the native entry has no observed default service tier. No provider response or immutable backend revision was obtained. `comp_hash=3000` is catalog metadata, not a model revision [O1,N-OAI-3].

2. **`gpt 6 sol` → `gpt-6-sol`.** The official card gives a distinct exact ID [O2]. The same installed bundled catalog listed it as a separate entry [N-OAI-3]. The model-only and Codex coding arms remain separate. API default reasoning is `medium`; native default reasoning is `medium` and native default service tier is `priority/Fast`, unlike the missing tier field for `gpt-6.1-sol`. API `none` is documented for this model but not for `gpt-6.1-sol`; defaults cannot be pooled. No provider response, serving revision, seed or account access was observed.

3. **OpenAI control warning.** The two cards expose different API/CLI context limits and defaults. A matched run must choose and receipt an explicit common surface, reasoning effort, service tier, context/truncation rule, tool manifest and reroute policy. Codex JSONL and app-server documentation expose usage/reroute fields, but no launch receipt exists [O6,O7,O8].

### 2.2 Confirmed Astra and Luna bindings

4. **`astra` → `gpt-6-astra`.** Main's plain user decision dated 2026-10-23 binds the requested label to GPT-6 Astra. Official OpenAI sources identify `gpt-6-astra` and Codex/API support [A1,A2,C1,C2,O4,O5]. Google Project Astra remains a separate trusted-tester research prototype and is retained only as an excluded alternative, not a substitute [A3]. The binding is user-confirmed/catalog-supported, not a provider-returned runtime receipt; account access, tools, fallback, revision and operational caps remain unverified.

5. **`luna` → `gpt-6-luna`.** Main's plain user decision dated 2026-10-23 binds Luna to GPT-6 Luna. The official card and Codex model documentation identify `gpt-6-luna` [L1,C2]. GPT-5.6 Luna remains an excluded alternative, while Luna Code and Luna Studio remain excluded configurable products rather than models [L2,L3,L4]. Account access, provider-returned identity, tools, fallback, revision and operational caps remain unverified.

### 2.3 Anthropic candidates

6. **`opus 5.5` → `claude-opus-5-5`.** Anthropic documents the exact model ID and pinned-ID semantics [P1,P3,P4]. A direct model-only arm must use a provider API with tools disabled; a Claude Code arm is a separate agent loop. Opus adaptive thinking is always on and API default effort is `medium`; forced `any`/named-tool choices are rejected, while `auto` and `none` are documented [P1,P5]. Claude Code `2.1.302` was observed, but no model selection or response was run [N-CLAUDE-1,N-CLAUDE-2]. Availability fallback, content fallback, managed policy replacement and subagent model changes remain unverified.

7. **`sonnect 5.5` → editorial `ClaudeSonnet5.5` → `claude-sonnet-5-5`.** The raw literal is preserved, while Main approved an obvious-spelling editorial normalization to Claude Sonnet 5.5. Anthropic documents the exact ID and default effort `high` [P2,P3,P4]. This editorial mapping is not provider attestation; exact account/provider launch, `modelUsage`, fallback containment and tool-parity evidence remain required.

8. **`fable 5.1` → `claude-fable-5-1`.** Anthropic documents the exact ID and separates Fable from Mythos [F1,F2]. Claude Code support is documented from v2.1.257; use the full ID rather than `fable` or `best`, because Claude Apps gateway aliases can resolve to Fable 5 rather than Fable 5.1 [F3]. Direct model-only and Claude Code Read/Edit/Bash arms remain distinct [F4]. Automatic safety fallback is documented; `CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK=1` and `switchModelsOnFlag=false` are documented controls, but neither was configured or tested [F5,F6]. Forced tool choice is unsupported. `modelUsage` and cost fields would be needed from a real result; no result exists.

### 2.4 Gemini candidates and interface separation

8. **`gemin 3.8flash` → editorial `Gemini3.8Flash` → `gemini-3.8-flash`.** The raw literal is preserved, while Main approved an obvious-spelling editorial normalization to Gemini 3.8 Flash. Google documents the public candidate [G1,G2,G4]. The Gemini API model-only lane can generate text and optionally invoke caller-executed functions or Python-only code execution [G5,G7,G8]; these capabilities do not grant repository file/build rights. The documented Antigravity preview agent `antigravity-preview-09-2026` can select `gemini-3.8-flash` and exposes sandbox file plus Bash/Python/Node/build/test tools [G9], but no run or parity receipt exists. The App selector `3.8 Flash`, if shown, is display-only evidence [G13]; editorial normalization is not provider attestation.

9. **`gemini argon`.** Google documents public candidate ID `gemini-4-argon` [G1,G3,G6]. The registry records it as a public candidate, not as proof that the App selector `4 Argon` is backed by that ID. API thinking defaults to `medium`; latest-model docs say temperature/top-p/top-k are ignored [G6]. The Antigravity preview agent supports `agent_config.model=gemini-4-argon` with sandbox file/Bash/Python/Node/build/test tools, but `max_total_tokens` is best-effort and the agent is a distinct interface [G9,G12]. Gemini CLI warns it is not optimized for Argon and documents fallback/subagent routing [G10,G11]. The native B1-only report [G21] records two agent-mediated one-shot feasibility attempts (general-rule wall time 180.043 s; ontology 180.038 s), both `TIMEOUT`/`print_timeout`, with runtime/provider identity, usage, and checker invocation null; this is non-conforming feasibility evidence, not a measured panel run or comparative result. No modelVersion, environment ID, tool receipt or cost was observed.

## 3. Cross-candidate control hazards

- **Codex defaults differ.** API reasoning defaults are `medium` for both OpenAI candidates. Native Codex defaults are `low` for `gpt 6.1 sol` and `medium` for `gpt 6 sol`; only the latter exposes native `priority/Fast` as the default service tier. Explicit common controls are required.
- **Claude routing and fallback must be observed, not inferred.** Provider selector format differs by API, Bedrock, Foundry and Google Cloud. Claude aliases can resolve differently by provider. Availability fallback, content-based safety fallback, managed policy replacement and subagent changes can alter the answering model. `modelUsage` is the required runtime accounting field when available.
- **Claude cost cap is estimate-only.** `total_cost_usd`/`costUSD` and `--max-budget-usd` are client estimates; they are not authoritative billing and may be exceeded. Actual billed cost remains `null`.
- **Gemini App is not Antigravity.** Canvas/App documentation covers editing, previews, console and export, but does not establish arbitrary local repository rights or provider model attestation [G13]. Antigravity is a separate tool-capable managed-agent interface with its own interaction/environment IDs and documented tool limitations [G9,G12]. Gemini CLI is another surface with fallback and subagent routing [G10,G11,G14,G15]. These surfaces cannot be pooled as if they had identical tool parity.
- **Unknown numeric controls stay null.** An aggregate additional API budget of USD 100 is approved by the plain user decision receipt dated 2026-10-23. Per-run token, wall-time, tool-call, repair and intervention caps remain `null`; any null operational cap fails the launch gate.
- **Jev is advisory only.** The supplied `jev-1.14.0` receipt is `unvalidated`, `proposal_only`, with `addresses_task=no (p_yes=0.45)`, `evidence_supports=no (p_yes=0.10)`, `needs_clarification=yes (p_yes=0.66)`, request 1, input 966, output 80, elapsed 368 ms and `scientific_study_launched=0`. It cannot be a gold label, independent human truth or commit authority.

## 4. Native safe-command receipts

These commands were read-only preflight checks and contained no private account data.

| Receipt | Command | Observed result |
|---|---|---|
| N-OAI-1 | `codex --version` | `codex-cli 0.163.0` |
| N-OAI-2 | `codex --help` | Model/exec/sandbox controls shown; no inference run |
| N-OAI-3 | `codex debug models --bundled` | 11-entry bundled JSON catalog; separate `gpt-6.1-sol` and `gpt-6-sol`; raw `artifact://3382` |
| N-CLAUDE-1 | `claude --version` | `2.1.302 (Claude Code)` |
| N-CLAUDE-2 | `claude --help` | Model/effort/tools/MCP/permission/JSON/budget controls; no catalog or seed option shown |
| N-GEMINI-1 | `agy --print /usage --output-format json --print-timeout 15s --sandbox` | `num_turns=0`, all tokens `0`; Argon/Gemini quota groups at `100%`; no plan fields; no inference run. Official headless docs [G20] define `num_turns` as cumulative user turns for the session, not provider requests/inferences; `conversation_id` is observable. |
### 4.1 Native C1 feasibility observations (non-conforming, not API-panel measurements)

These are public-receipt observations from the native prelaunch revalidation (`offline-revalidation-main-01.json`, with the source-snapshot erratum `source-snapshot-erratum-main-01.json` and scope correction `parent-amendment-scope-correction-02.json`). The native old-B1 disposition is `NOT_LAUNCHED_SUPERSEDED_BY_V2_FOLDER`; this is not a contract-mismatch claim. They are `n=1` observations per task, not a new repeat, and have no effect on the nine-candidate panel, `measured_runs: 0`, superiority, efficacy or statistical claims.

| Observation | Wall time (s) | Input tokens | Output tokens | Thinking | Cache-read | Total (native-reported; counter inclusion unverified) | Raw check |
|---|---:|---:|---:|---:|---:|---:|---|
| General-rule task | 26.182 | 26,028 | 763 | 614 | 0 | 26,791 | `PASS` |
| Ontology task | 59.792 | 17,829 | 143 | 0 | 8,192 | 17,972 | `PASS` |

Prompt byte sizes were **2,318** and **2,265** respectively; prompt bytes are distinct from token counts. The five raw counters are retained without double-counting: `total` is copied as native-reported, while the native output schema has not established whether `output` includes `thinking`. Official headless examples [G20] expose input/output/thinking/total fields but do not define thinking inclusion or cache-read subset semantics. The cache-read difference (`0` versus `8,192`) is an additional comparison confound; latency cannot be causally attributed to representation. Full native context, effective tools, provider-returned identity/model revision and tool parity remain unverified; these metrics are descriptive only. The raw CLI zero-turn usage receipt fetched quota/status only, not these task statistics. The original wrapper prelaunch SHA was not captured, so executor provenance remains a fix; the corrected secondary snapshot-bank hash is retained as a 64-hex erratum. Subscription/quota and billed USD are `null`.

The observations are read-only native feasibility evidence only; they do not establish a conforming API run or comparative result.

The receipts establish installed CLI/catalog observations only. They do not establish account entitlement, active tools, provider-returned identity, serving revision, seed, cost or experiment execution.

## 5. Fail-closed launch checklist

Every item is currently `REQUIRED_NOT_SATISFIED`; any false or null item blocks launch.

| ID | Required evidence before any arm launches | Current status |
|---|---|---|
| L01 | Bind exact raw label to an official selector without silent substitution | `REQUIRED_NOT_SATISFIED` |
| L02 | Receipt-backed account/provider entitlement and exact launch | `REQUIRED_NOT_SATISFIED` |
| L03 | Separate runtime-reported identity from provider-returned identity/modelVersion | `REQUIRED_NOT_SATISFIED` |
| L04 | Separate snapshot semantics from serving revision; catalog hash/UI label is not revision | `REQUIRED_NOT_SATISFIED` |
| L05 | Separate model-only and coding-agent arms with explicit tool manifests | `REQUIRED_NOT_SATISFIED` |
| L06 | Disable or receipt-prove absence of fallback/reroute/subagent/policy replacement | `REQUIRED_NOT_SATISFIED` |
| L07 | Freeze common effort/tier/context/sampling restrictions, fresh workspace/thread and observer schema | `REQUIRED_NOT_SATISFIED` |
| L08 | Set receipt-backed non-null approved caps and consent | `REQUIRED_NOT_SATISFIED` |
| L09 | Treat Jev only as advisory; independent human/neutral grading remains required | `REQUIRED_NOT_SATISFIED` |
| L10 | Keep measured runs at 0 until approved launch; exclude legacy n1/CLI6 case | `REQUIRED_NOT_SATISFIED` |

## 6. Primary source index

All public sources below were retrieved on **2026-10-23**. The full `establishes` text and candidate linkage are in `model-registry.json`.

| IDs | Official URLs |
|---|---|
| O1–O3 | [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol); [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol); [OpenAI model catalog](https://developers.openai.com/api/docs/models/) |
| O4–O8 | [ChatGPT model docs](https://learn.chatgpt.com/docs/models); [Codex CLI](https://learn.chatgpt.com/docs/codex/cli); [Codex JSONL](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable); [Codex app-server model list](https://learn.chatgpt.com/docs/app-server#list-models-modellist); [Responses create reference](https://developers.openai.com/api/reference/resources/responses/methods/create/) |
| A1–A3 | [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra); [GPT-6 Astra announcement](https://openai.com/index/gpt-6-astra-next-generation-work/); [Project Astra](https://deepmind.google/models/project-astra/) |
| L1–L4 | [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna); [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna); [Luna Code](https://marketplace.visualstudio.com/items?itemName=derekshreds.lunacode); [Luna Studio](https://marketplace.visualstudio.com/items?itemName=lunabaseai.luna-co-pilot) |
| F1–F6 | [Fable overview](https://platform.claude.com/docs/en/models/fable-5-1/overview); [Fable what's new](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1); [Claude model config](https://code.claude.com/docs/en/model-config); [Claude headless](https://code.claude.com/docs/en/headless); [Claude env vars](https://code.claude.com/docs/en/env-vars); [Claude settings](https://code.claude.com/docs/en/settings-reference) |
| P1–P8 | [Opus overview](https://platform.claude.com/docs/en/models/opus-5-5/overview); [Sonnet overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview); [Claude model overview](https://platform.claude.com/docs/en/models/overview); [Model IDs/versions](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions); [Opus what's new](https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5); [Claude CLI reference](https://code.claude.com/docs/en/cli-reference); [Claude cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking); [Models API list](https://platform.claude.com/docs/en/api/models/list) |
| G1–G8 | [Gemini models](https://ai.google.dev/gemini-api/docs/models); [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash); [Gemini 4 Argon](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon); [Gemini 3.8 updates](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.8); [GenerateContent response](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse); [Latest model](https://ai.google.dev/gemini-api/docs/latest-model); [Function calling](https://ai.google.dev/gemini-api/docs/function-calling); [Code execution](https://ai.google.dev/gemini-api/docs/code-execution) |
| G9–G16,G19 | [Antigravity agent](https://ai.google.dev/gemini-api/docs/antigravity-agent); [Gemini CLI model](https://geminicli.com/docs/cli/model/); [Gemini CLI routing](https://geminicli.com/docs/cli/model-routing/); [Managed agents](https://ai.google.dev/gemini-api/docs/managed-agents-quickstart); [Gemini App Canvas](https://support.google.com/gemini/answer/16047321?hl=en); [CLI transition](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/); [Gemini CLI headless](https://geminicli.com/docs/cli/headless/); [Gemini changelog](https://ai.google.dev/gemini-api/docs/changelog); [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| G20 | [Antigravity headless CLI](https://antigravity.google/docs/cli/headless.md) | Official headless JSON usage semantics: `num_turns` is cumulative user turns per session and `conversation_id` is observable; example input/output/thinking/total fields do not define thinking inclusion or cache-read subset semantics. |
| G21 | Local native Argon B1-only feasibility report (`native-argon-probe-20261024-02-b1only/report.json`) | Two one-shot agent-mediated attempts timed out at 180.043 s and 180.038 s; runtime/provider identity, usage and checker invocation remained null; not a measured panel run. |

## 7. Legacy boundary and next action

The historical case `research/development-cases/ontology-map-20261023-01/` remains `development_runs=1`, `native_cli_invocations=6`, `independent_repeats=0`, with descriptive wall time `5942.665 s`. It is visibly outside this expanded panel and does not change `measured_runs=0`.

Next action: use the confirmed GPT-6 Astra, GPT-6 Luna, editorial Claude Sonnet 5.5 and editorial Gemini 3.8 Flash mappings, then obtain approved exact-model launch, fallback-containment, tool-parity, per-run-cap and provider-identity receipts before changing any execution status.
