# 확장 모델 패널 — 한국어 근거

**연구:** `development-comparison-20261023`  
**근거 기준일:** 초기 근거 기준일 2026-10-23; 2026-10-24 검색 관측으로 업데이트
**레지스트리:** [`model-registry.json`](./model-registry.json)  
**패널 상태:** `PROPOSED_NOT_EXECUTED`  
**측정 run:** `0`  
**근거 수:** 56개 — 공개 source 47개, native 안전 명령 receipt 6개, 제공된 Jev advisory receipt 1개, plain user-decision receipt 2개.

이 패널은 identity/access 사전 점검 근거이며 생성 콘텐츠 근거나 coding 실험 결과가 아니다. `raw_user_label`은 Main이 제공한 사용자 문자열을 그대로 보존한다. `protocol_label`은 현재 계획/프로토콜 표기이고 `display_alias`는 표시 전용이다. `canonical_id`는 명시적 사용자 확인 또는 공식 문서가 뒷받침하는 editorial normalization으로 선택된 문서화 후보를 기록한다. Editorial normalization은 provider attestation이 아니며 runtime/provider identity는 별도 필드다.

## 1. 아홉 후보 비교

| 번호 | `raw_user_label` | `protocol_label` | `protocol_candidate_id` | `canonical_id` (검증된 후보 또는 `null`) | 제공자 / 매핑 신뢰도 | Source ID | 실험 / launch 상태 |
|---:|---|---|---|---|---|---|---|
| 1 | `gpt 6.1 sol` | `gpt-6.1-sol` | `gpt_6_1_sol` | `gpt-6.1-sol` | OpenAI; 공개 ID와 bundled catalog 항목이 정확히 일치 | O1,O3,O4,O5,N-OAI-1..3 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 2 | `gpt 6 sol` | `gpt-6-sol` | `gpt_6_sol` | `gpt-6-sol` | OpenAI; 공개 ID와 bundled catalog 항목이 정확히 일치 | O2,O3,O4,O5,N-OAI-1..3 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 3 | `astra` | `Astra` | `astra` | `gpt-6-astra` | OpenAI; 사용자 확인 GPT-6 Astra 및 공식/catalog 근거; Project Astra는 제외 | A1,A2,A3,O4,O5,C1,C2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 4 | `luna` | `Luna` | `luna` | `gpt-6-luna` | OpenAI; 사용자 확인 GPT-6 Luna 및 공식/catalog 근거; 다른 generation/product는 제외 | L1,L2,L3,L4,O4,O5,C2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 5 | `opus 5.5` | `Opus5.5` | `opus_5_5` | `claude-opus-5-5` | Anthropic; 공식 model ID이나 provider deployment는 미결속 | P1,P3,P4,P5,P6,P7,P8,N-CLAUDE-1..2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 6 | `sonnect 5.5` | `ClaudeSonnet5.5` | `literal_sonnect_5_5` | `claude-sonnet-5-5` | Anthropic; 명백한 오탈자의 editorial normalization, 공식 ID 문서화, provider attestation은 미검증 | P2,P3,P4,P6,P7,N-CLAUDE-1..2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 7 | `fable 5.1` | `Fable5.1` | `fable_5_1` | `claude-fable-5-1` | Anthropic; 공식 model ID이나 runtime/provider identity는 미검증 | F1,F2,F3,F4,F5,F6,P7,N-CLAUDE-1..2 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_FALLBACK_PARITY_AND_CAPS` |
| 8 | `gemin 3.8flash` | `Gemini3.8Flash` | `literal_gemin3_8_flash` | `gemini-3.8-flash` | Google; 명백한 오탈자의 editorial normalization, 공식 ID 문서화, provider attestation은 미검증 | G1,G2,G4,G5,G7,G8,G9,G10,G11,G13,G14,G15,G16,G19 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |
| 9 | `gemini argon` | `GeminiArgon` | `gemini_argon` | `gemini-4-argon` | Google 공개 후보; App backing identity는 증명되지 않음 | G1,G3,G5,G6,G7,G8,G9,G10,G11,G12,G13,G14,G15,G16,G19,G21 | `PROPOSED_NOT_EXECUTED` / `BLOCKED_PENDING_ACCESS_IDENTITY_PARITY_AND_CAPS` |

모든 행의 `measured_runs`는 `0`이다. 2026-10-23 plain user decision receipt가 두 track에 대한 aggregate additional API budget cap USD 100을 승인했다. Per-run, token, wall-time, tool-call, repair, intervention cap은 `null`이므로 launch는 계속 fail-closed다. Protocol-conforming API panel inference는 관측되지 않았고, 별도 native C1 feasibility launch 2회가 관측되었지만 comparative result가 아니다. Account entitlement, provider-returned identity, serving revision, seed, 실제 비용, 유효 tool manifest와 실험 효능은 미검증 또는 `null`이다.

## 2. 후보별 근거와 interface 경계

### 2.1 OpenAI 후보

1. **`gpt 6.1 sol` → `gpt-6.1-sol`.** 공식 card가 정확한 ID와 Responses/Chat Completions surface를 제시한다 [O1]. 설치된 Codex CLI는 `0.163.0`이었고 bundled catalog에 별도 `gpt-6.1-sol` 항목이 있었다 [N-OAI-1,N-OAI-3]. Model-only arm은 tool을 제외한 Responses 요청으로 제안한다. Coding arm은 `-m/--model`을 쓰는 별도 Codex CLI arm이며, 문서화된 native tool은 unified execution, freeform patch, web search다 [O5]. Catalog 기본 reasoning은 `low`, API 기본값은 `medium`이며 native 항목에는 관측된 기본 service tier가 없다. Provider response나 불변 backend revision은 얻지 못했다. `comp_hash=3000`은 catalog metadata이지 model revision이 아니다 [O1,N-OAI-3].

2. **`gpt 6 sol` → `gpt-6-sol`.** 공식 card가 별도의 정확한 ID를 제시한다 [O2]. 같은 설치 bundled catalog에도 별도 항목으로 기록됐다 [N-OAI-3]. Model-only와 Codex coding arm은 분리한다. API 기본 reasoning은 `medium`, native 기본 reasoning은 `medium`, native 기본 service tier는 `priority/Fast`다. 반면 `gpt-6.1-sol`에는 해당 tier field가 없다. API `none`은 이 model에는 문서화됐지만 `gpt-6.1-sol`에는 문서화되지 않았으므로 기본값을 합치면 안 된다. Provider response, serving revision, seed, account access는 관측되지 않았다.

3. **OpenAI control 경고.** 두 card는 API와 CLI의 context limit와 기본값을 다르게 노출한다. Matched run은 공통 surface, reasoning effort, service tier, context/truncation 규칙, tool manifest와 reroute 정책을 명시적으로 선택하고 receipt해야 한다. Codex JSONL 및 app-server 문서는 usage/reroute field를 노출하지만 launch receipt는 없다 [O6,O7,O8].

### 2.2 확인된 Astra와 Luna binding

4. **`astra` → `gpt-6-astra`.** 2026-10-23 Main의 plain user decision이 요청 label을 GPT-6 Astra로 결속했다. 공식 OpenAI source가 `gpt-6-astra`와 Codex/API 지원을 식별한다 [A1,A2,C1,C2,O4,O5]. Google Project Astra는 별도의 trusted-tester research prototype이며 대체 후보가 아니라 제외 alternative로만 보존한다 [A3]. 이 binding은 user-confirmed/catalog-supported이지 provider-returned runtime receipt가 아니다. Account access, tool, fallback, revision과 operational cap은 미검증이다.

5. **`luna` → `gpt-6-luna`.** 2026-10-23 Main의 plain user decision이 Luna를 GPT-6 Luna로 결속했다. 공식 card와 Codex model documentation이 `gpt-6-luna`를 식별한다 [L1,C2]. GPT-5.6 Luna는 제외 alternative이며 Luna Code와 Luna Studio는 model이 아닌 설정 가능한 product로 제외한다 [L2,L3,L4]. Account access, provider-returned identity, tool, fallback, revision과 operational cap은 미검증이다.

### 2.3 Anthropic 후보

6. **`opus 5.5` → `claude-opus-5-5`.** Anthropic은 정확한 model ID와 pinned-ID 의미를 문서화한다 [P1,P3,P4]. 직접 model-only arm은 tool을 끈 provider API를 사용해야 하고, Claude Code arm은 별도 agent loop다. Opus adaptive thinking은 항상 켜져 있으며 API 기본 effort는 `medium`이다. Forced `any`/named-tool은 거부되고 `auto`와 `none`은 문서화돼 있다 [P1,P5]. Claude Code `2.1.302`는 관측했지만 model 선택이나 response는 실행하지 않았다 [N-CLAUDE-1,N-CLAUDE-2]. Availability fallback, content fallback, managed policy replacement, subagent model 변경은 미검증이다.

7. **`sonnect 5.5` → editorial `ClaudeSonnet5.5` → `claude-sonnet-5-5`.** Raw literal은 보존하되 Main이 명백한 오탈자의 editorial normalization을 Claude Sonnet 5.5로 승인했다. Anthropic은 정확한 ID와 기본 effort `high`를 문서화한다 [P2,P3,P4]. 이 editorial mapping은 provider attestation이 아니며 exact account/provider launch, `modelUsage`, fallback containment과 tool-parity 근거가 필요하다.

8. **`fable 5.1` → `claude-fable-5-1`.** Anthropic은 정확한 ID를 문서화하고 Fable과 Mythos를 구분한다 [F1,F2]. Claude Code support는 v2.1.257부터 문서화돼 있다. `fable` 또는 `best` alias 대신 full ID를 써야 하는데, Claude Apps gateway alias가 Fable 5로 해석될 수 있어 Fable 5.1과 다르기 때문이다 [F3]. 직접 model-only와 Claude Code Read/Edit/Bash arm은 분리한다 [F4]. Automatic safety fallback이 문서화돼 있으며 `CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK=1`, `switchModelsOnFlag=false`가 control로 문서화됐지만 어느 것도 설정·시험하지 않았다 [F5,F6]. Forced tool choice는 지원되지 않는다. 실제 result에는 `modelUsage`와 cost field가 필요하지만 result 자체가 없다.

### 2.4 Gemini 후보와 interface 분리

8. **`gemin 3.8flash` → editorial `Gemini3.8Flash` → `gemini-3.8-flash`.** Raw literal은 보존하되 Main이 명백한 오탈자의 editorial normalization을 Gemini 3.8 Flash로 승인했다. Google이 public candidate를 문서화한다 [G1,G2,G4]. Gemini API model-only lane은 text를 생성하고 caller가 실행하는 function 또는 Python-only code execution을 선택적으로 호출할 수 있다 [G5,G7,G8]. 이는 repository file/build 권한이 아니다. 문서화된 Antigravity preview agent `antigravity-preview-09-2026`는 `gemini-3.8-flash`를 선택하고 sandbox file 및 Bash/Python/Node/build/test tool을 제공하지만 [G9], 실행 또는 parity receipt는 없다. App selector `3.8 Flash`가 보이더라도 display-only evidence다 [G13]. Editorial normalization은 provider attestation이 아니다.

9. **`gemini argon`.** Google은 공개 후보 ID `gemini-4-argon`을 문서화한다 [G1,G3,G6]. Registry에는 공개 후보로 기록하되 App selector `4 Argon`이 이 ID로 backend 된다는 증명으로 사용하지 않는다. API thinking 기본값은 `medium`이고 latest-model 문서는 temperature/top-p/top-k가 무시된다고 한다 [G6]. Antigravity preview agent는 `agent_config.model=gemini-4-argon`과 sandbox file/Bash/Python/Node/build/test tool을 지원하지만 `max_total_tokens`는 best-effort이며 agent는 별도 interface다 [G9,G12]. Gemini CLI는 Argon에 최적화되지 않았다고 경고하며 fallback/subagent routing을 문서화한다 [G10,G11]. Native B1-only report [G21]에는 agent-mediated one-shot feasibility 시도 2회가 기록되어 있다(General-rule wall time 180.043초, ontology 180.038초). 둘 다 `TIMEOUT`/`print_timeout`이며 runtime/provider identity, usage, checker invocation은 `null`이다. 이는 비순응 feasibility 근거이며 measured panel run이나 comparative result가 아니다. `modelVersion`, environment ID, tool receipt, cost는 관측되지 않았다.

## 3. 후보 공통 control hazard

- **Codex 기본값이 다르다.** 두 OpenAI 후보의 API reasoning 기본값은 `medium`이다. Native Codex 기본값은 `gpt 6.1 sol`이 `low`, `gpt 6 sol`이 `medium`이며, native `priority/Fast` 기본 service tier는 후자에만 있다. 명시적인 공통 control이 필요하다.
- **Claude routing과 fallback은 추정하지 말고 관측해야 한다.** Provider selector 형식은 API, Bedrock, Foundry, Google Cloud마다 다르다. Claude alias도 provider에 따라 다르게 해석될 수 있다. Availability fallback, content-based safety fallback, managed policy replacement, subagent 변경은 실제 응답 model을 바꿀 수 있다. 가능할 때 `modelUsage`가 필수 runtime accounting field다.
- **Claude 비용 cap은 estimate-only다.** `total_cost_usd`/`costUSD`와 `--max-budget-usd`는 client estimate이며 authoritative billing이 아니고 초과할 수 있다. 실제 청구 비용은 `null`이다.
- **Gemini App은 Antigravity가 아니다.** Canvas/App 문서는 editing, preview, console, export를 설명하지만 local repository 권한이나 provider model attestation을 확립하지 않는다 [G13]. Antigravity는 interaction/environment ID와 별도 tool 제약을 가진 tool-capable managed-agent interface다 [G9,G12]. Gemini CLI도 fallback 및 subagent routing이 있는 별도 surface다 [G10,G11,G14,G15]. 이 surface들을 같은 tool parity처럼 합치면 안 된다.
- **모르는 숫자 control은 계속 null이다.** 2026-10-23 plain user decision receipt가 aggregate additional API budget USD 100을 승인했다. Per-run token, wall-time, tool-call, repair, intervention cap은 `null`이며 null operational cap은 launch를 차단한다.
- **Jev는 advisory일 뿐이다.** 제공된 `jev-1.14.0` receipt는 `unvalidated`, `proposal_only`이며 `addresses_task=no (p_yes=0.45)`, `evidence_supports=no (p_yes=0.10)`, `needs_clarification=yes (p_yes=0.66)`, request 1, input 966, output 80, elapsed 368 ms, `scientific_study_launched=0`이다. Gold label, independent human truth 또는 commit authority가 될 수 없다.

## 4. Native 안전 명령 receipt

아래 명령은 private account data가 없는 read-only preflight check다.

| Receipt | 명령 | 관측 결과 |
|---|---|---|
| N-OAI-1 | `codex --version` | `codex-cli 0.163.0` |
| N-OAI-2 | `codex --help` | Model/exec/sandbox control 표시; inference 미실행 |
| N-OAI-3 | `codex debug models --bundled` | 11개 bundled JSON catalog; `gpt-6.1-sol`과 `gpt-6-sol` 별도 항목; raw `artifact://3382` |
| N-CLAUDE-1 | `claude --version` | `2.1.302 (Claude Code)` |
| N-CLAUDE-2 | `claude --help` | Model/effort/tools/MCP/permission/JSON/budget control; catalog 또는 seed option은 표시되지 않음 |
| N-GEMINI-1 | `agy --print /usage --output-format json --print-timeout 15s --sandbox` | `num_turns=0`, 전체 token `0`; Argon/Gemini quota group `100%`; plan field 없음; inference 미실행. 공식 headless 문서 [G20]는 `num_turns`를 세션 누적 사용자 턴으로 정의하며 provider request/inference 수가 아니다. `conversation_id`도 관찰 가능하다. |
### 4.1 Native C1 feasibility 관측 (비순응, API-panel 측정 아님)

다음은 native prelaunch 재검증의 공개 receipt 관측이다(`offline-revalidation-main-01.json`, source-snapshot erratum `source-snapshot-erratum-main-01.json`, scope correction `parent-amendment-scope-correction-02.json`). Native old-B1 disposition은 `NOT_LAUNCHED_SUPERSEDED_BY_V2_FOLDER`이며, 이는 contract mismatch 주장이 아니다. 각 task의 `n=1` 관측이며 새 repeat가 아니다. 아홉 후보 패널, `measured_runs: 0`, superiority·efficacy·통계 주장에는 영향을 주지 않는다.

| 관측 | Wall time (s) | Input tokens | Output tokens | Thinking | Cache-read | Total (native-reported; counter inclusion unverified) | Raw check |
|---|---:|---:|---:|---:|---:|---:|---|
| General-rule task | 26.182 | 26,028 | 763 | 614 | 0 | 26,791 | `PASS` |
| Ontology task | 59.792 | 17,829 | 143 | 0 | 8,192 | 17,972 | `PASS` |

Prompt byte size는 각각 **2,318** 및 **2,265**이며, prompt bytes는 token count와 다르다. 다섯 raw counter는 이중 계산 없이 보존했다. `total`은 native-reported 값을 그대로 기록했으며, native output schema는 `output`이 `thinking`을 포함하는지 아직 확립하지 않았다. 공식 headless 예시는 [G20] input/output/thinking/total 필드를 보이지만 thinking 포함 여부나 cache-read subset 의미를 정의하지 않는다. Cache-read 차이(`0` 대 `8,192`)는 추가 comparison confound이며 latency를 representation에 인과적으로 귀속할 수 없다. 전체 native context, 유효 tool, provider-returned identity/model revision과 tool parity는 여전히 미검증이고, 이 지표는 descriptive only다. Raw CLI zero-turn usage receipt는 quota/status만 가져왔고 이 task 통계가 아니다. Original wrapper prelaunch SHA가 캡처되지 않아 executor provenance는 수정 필요 상태이며, 보정된 secondary snapshot-bank hash는 64-hex erratum으로 보존된다. Subscription/quota와 billed USD는 `null`이다.

이 관측은 read-only native feasibility evidence일 뿐이며, 순응 API 실행이나 comparative result를 확립하지 않는다.

Receipt는 설치된 CLI/catalog 관측만 확립한다. Account entitlement, active tool, provider-returned identity, serving revision, seed, cost, experiment execution은 확립하지 않는다.

## 5. Fail-closed launch checklist

현재 모든 항목은 `REQUIRED_NOT_SATISFIED`이며, 하나라도 false 또는 null이면 launch를 차단한다.

| ID | 모든 arm 실행 전 필요한 근거 | 현재 상태 |
|---|---|---|
| L01 | 정확한 raw label을 silent substitution 없이 공식 selector에 결속 | `REQUIRED_NOT_SATISFIED` |
| L02 | Receipt로 확인한 account/provider entitlement와 exact launch | `REQUIRED_NOT_SATISFIED` |
| L03 | Runtime-reported identity와 provider-returned identity/modelVersion 분리 | `REQUIRED_NOT_SATISFIED` |
| L04 | Snapshot 의미와 serving revision 분리; catalog hash/UI label을 revision으로 사용하지 않음 | `REQUIRED_NOT_SATISFIED` |
| L05 | 명시된 tool manifest를 가진 model-only arm과 coding-agent arm 분리 | `REQUIRED_NOT_SATISFIED` |
| L06 | Fallback/reroute/subagent/policy replacement를 끄거나 부재를 receipt로 증명 | `REQUIRED_NOT_SATISFIED` |
| L07 | 공통 effort/tier/context/sampling 제한, fresh workspace/thread, observer schema 동결 | `REQUIRED_NOT_SATISFIED` |
| L08 | Receipt로 승인된 non-null cap과 consent 설정 | `REQUIRED_NOT_SATISFIED` |
| L09 | Jev는 advisory로만 취급하고 independent human/neutral grading 유지 | `REQUIRED_NOT_SATISFIED` |
| L10 | 승인 launch 전 measured runs 0 유지; legacy n1/CLI6 사례 제외 | `REQUIRED_NOT_SATISFIED` |

## 6. Primary source index

아래 공개 source는 모두 **2026-10-23**에 retrieval했다. 전체 `establishes` 내용과 후보 연결은 `model-registry.json`에 있다.

| ID | 공식 URL |
|---|---|
| O1–O3 | [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol); [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol); [OpenAI model catalog](https://developers.openai.com/api/docs/models/) |
| O4–O8 | [ChatGPT model docs](https://learn.chatgpt.com/docs/models); [Codex CLI](https://learn.chatgpt.com/docs/codex/cli); [Codex JSONL](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable); [Codex app-server model list](https://learn.chatgpt.com/docs/app-server#list-models-modellist); [Responses create reference](https://developers.openai.com/api/reference/resources/responses/methods/create/) |
| A1–A3 | [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra); [GPT-6 Astra announcement](https://openai.com/index/gpt-6-astra-next-generation-work/); [Project Astra](https://deepmind.google/models/project-astra/) |
| L1–L4 | [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna); [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna); [Luna Code](https://marketplace.visualstudio.com/items?itemName=derekshreds.lunacode); [Luna Studio](https://marketplace.visualstudio.com/items?itemName=lunabaseai.luna-co-pilot) |
| F1–F6 | [Fable overview](https://platform.claude.com/docs/en/models/fable-5-1/overview); [Fable what's new](https://platform.claude.com/docs/en/models/fable-5-1/whats-new-fable-5-1); [Claude model config](https://code.claude.com/docs/en/model-config); [Claude headless](https://code.claude.com/docs/en/headless); [Claude env vars](https://code.claude.com/docs/en/env-vars); [Claude settings](https://code.claude.com/docs/en/settings-reference) |
| P1–P8 | [Opus overview](https://platform.claude.com/docs/en/models/opus-5-5/overview); [Sonnet overview](https://platform.claude.com/docs/en/models/sonnet-5-5/overview); [Claude model overview](https://platform.claude.com/docs/en/models/overview); [Model IDs/versions](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions); [Opus what's new](https://platform.claude.com/docs/en/models/opus-5-5/whats-new-opus-5-5); [Claude CLI reference](https://code.claude.com/docs/en/cli-reference); [Claude cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking); [Models API list](https://platform.claude.com/docs/en/api/models/list) |
| G1–G8 | [Gemini models](https://ai.google.dev/gemini-api/docs/models); [Gemini 3.8 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash); [Gemini 4 Argon](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon); [Gemini 3.8 updates](https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.8); [GenerateContent response](https://ai.google.dev/api/generate-content#v1beta.GenerateContentResponse); [Latest model](https://ai.google.dev/gemini-api/docs/latest-model); [Function calling](https://ai.google.dev/gemini-api/docs/function-calling); [Code execution](https://ai.google.dev/gemini-api/docs/code-execution) |
| G9–G16,G19 | [Antigravity agent](https://ai.google.dev/gemini-api/docs/antigravity-agent); [Gemini CLI model](https://geminicli.com/docs/cli/model/); [Gemini CLI routing](https://geminicli.com/docs/cli/model-routing/); [Managed agents](https://ai.google.dev/gemini-api/docs/managed-agents-quickstart); [Gemini App Canvas](https://support.google.com/gemini/answer/16047321?hl=en); [CLI transition](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/); [Gemini CLI headless](https://geminicli.com/docs/cli/headless/); [Gemini changelog](https://ai.google.dev/gemini-api/docs/changelog); [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) |
| G20 | [Antigravity headless CLI](https://antigravity.google/docs/cli/headless.md) | 공식 headless JSON usage 의미: `num_turns`는 세션 누적 사용자 턴이며 `conversation_id`가 관찰 가능하다. input/output/thinking/total 예시는 thinking 포함 여부나 cache-read subset 의미를 정의하지 않는다. |
| G21 | Local native Argon B1-only feasibility report (`native-argon-probe-20261024-02-b1only/report.json`) | Agent-mediated one-shot 2회가 180.043초와 180.038초에 timeout; runtime/provider identity, usage, checker invocation은 null이며 measured panel run이 아님. |

## 7. Legacy boundary와 next action

역사 사례 `research/development-cases/ontology-map-20261023-01/`는 `development_runs=1`, `native_cli_invocations=6`, `independent_repeats=0`, 서술용 wall time `5942.665 s`로 보존한다. 이 사례는 확장 패널 바깥에 명시적으로 두며 `measured_runs=0`을 바꾸지 않는다.

다음 단계: 확인된 GPT-6 Astra, GPT-6 Luna, editorial Claude Sonnet 5.5 및 editorial Gemini 3.8 Flash 매핑을 사용하되, 실행 상태를 바꾸기 전에 승인된 exact-model launch, fallback-containment, tool-parity, per-run-cap 및 provider-identity receipt를 확보한다.
