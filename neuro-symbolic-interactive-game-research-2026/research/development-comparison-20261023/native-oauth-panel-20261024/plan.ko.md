# Native OAuth 패널 계획 v3

**연구 라벨:** `development-comparison-20261023/native-oauth-panel-20261024`  
**상태:** `FROZEN_NOT_EXECUTED`  
**동결일:** 2026-10-24  
**소유 역할:** native-study contract 및 불변 근거 controller

## 1. 결정과 경계

사용자 결정을 그대로 보존한다: `oauth 인증받은 codex, claude, agy --dangerously-skip-permissions 이용한 cli 로 실험`. 이 결정은 새 단계의 strict API-only 경로를 인증된 native Codex·Claude·agy CLI 경로로 수정한다. 이 문서는 소유자에 의한 provider 호출, API fallback, 새 API key 또는 결과 주장을 승인하지 않는다.

비교 요인은 **system/agent-mediated permission mode**다. 순수 모델 요인이나 ontology 인과효과 요인이 아니다. requested label, runtime-reported model, provider-returned model, weights/revision, seed, usage, latency, billed USD는 분리 기록하고 모르는 값은 `null`로 둔다.

기존 API 경로는 호출된 적이 없으며 review block과 함께 폐기됐다. `native-argon-probe-20261024-01` 및 `native-argon-probe-20261024-02-b1only`의 기존 Argon 4회 시도는 불변 역사/feasibility 근거로만 보존하며 새 결과나 독립 반복이 아니다.

## 2. 동결 artifact

이 단계의 source of truth는 다음 파일이다.

1. `authorization-v3.json` — permission amendment, CLI 경계, billing 및 safety gate.
2. `protocol.json` — 요인, 근거 계약, 상태 원장 및 중지 규칙.
3. `schedule.json` — 결정론적 seed와 단계 순서.
4. `frozen-inputs.json` — C1/B1 task-local 입력, source hash, prompt hash, B1 file manifest.
5. `assignment-manifest.json` — 36개 assignment ID와 assignment별 hash 참조.

동결 입력 digest는 `72f29c460e657e1d70f770f353d01274182a1a68ab15c27e70eb809a194d52c1`이다. 새 stage call 전에 이 파일들을 동결한다. C2, H1 또는 다른 held-out payload는 포함하거나 재구성하지 않는다.

## 3. 정확한 후보와 matched 요인

계약 후보 라벨은 대소문자를 포함해 정확히 보존한다.

| Provider family | 후보 라벨 | 요청 CLI selector |
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

표시/selector 매핑은 요청 경로이지 provider attestation이 아니다. `GeminiArgon`은 registry selector와 native agy catalog selector를 분리 기록한다. 라벨을 조용히 정규화하거나 대체하지 않는다.

각 후보에는 두 task arm(`C1` content generation, `B1` coding)이 있고, 각 arm은 두 representation(`general_rule`, `ontology`)으로 동결된다. 한 후보의 상대 arm은 다른 arm의 raw validity, failure 또는 timeout 때문에 삭제되지 않는다.

## 4. 동결 입력

`C1` source task는 `panel-c1-001`을 유지한다. 위치는 `dock`, `tower`, `lens`는 `dock`, `sealed_scroll`은 `tower`, 사실은 `met_keeper`, `lens_in_hand`이며 `vault_code`를 공개하지 않고 `INSTALL_LENS -> signal_restored`를 만든다. task hash는 `abc8ff7349ee0229870b1d017e0732e77cd47d4e001305e2ece07aa759eee5f3`, representation inventory hash는 `ebc31f1535d694eb71c023ebf782231e5cb5978f12a6bf3987998c03988020e`이다.

`B1`은 task-local harbor/lighthouse 계약이다. 동결된 10개 acceptance ID는 `AC-SCENES`, `AC-MOVEMENT`, `AC-GAME-GOAL`, `AC-ONTOLOGY-GATE`, `AC-REPAIR`, `AC-REPLAY`, `AC-READONLY-SIGNALS`, `AC-SAVE-LOAD`, `AC-BUILD`, `AC-DETERMINISTIC-QA`이다. task-local API는 `project.godot`와 `main.gd`이며, 새 상대 파일은 `game/*.gd`, `game/*.tscn` 아래만 허용하고 symlink·기존 파일 교체·download는 금지한다. 권위 있는 scene은 `harbor`, `lighthouse`이고 root shared `game_api`는 사용하지 않는다.

B1 task hash는 `70d8a14a219b99f4823318ad57dbe3bfb6a61d5d5a9c57c3f8b75403e162dabd`, representation inventory hash는 `b34022f80d779541ca056275e3992d62d257297c13e3e3c99d52b3afab39280e`이다.

Prompt는 `src/nesy_game/model_panel.py::build_prompt`만 사용해 `proposition_views`로 생성한다. C1 hard content check는 `content_grade`를 사용한다. prompt hash는 `frozen-inputs.json`에 있고 `assignment-manifest.json`에서 assignment별로 참조한다.

## 5. 일정과 launch cap

- `F0`: read-only OAuth status, source/hash, observer 및 transport preflight; provider call 0회.
- `F1`: `general_rule` 18개 사전 선언 assignment: 후보마다 C1 1개와 B1 1개.
- `F2`: `ontology` matched assignment 18개: 후보마다 C1 1개와 B1 1개.
- 합계: 정확히 36개를 사전 선언하며 모두 fresh disposable workspace와 fresh session을 사용한다.
- Seed: `20261023`; 순서는 `schedule.json`에 동결한다.
- launch별 cap: 180초; retry·resume·fallback 없음; 추가 G1 credit 없음.

USD 100 hard 값은 native CLI가 강제할 수 없으므로 gate는 `UNVERIFIED_NOT_ENFORCEABLE_BY_NATIVE_CLI`이고 통과가 아니다. Billing은 native subscription quota로 기록하고 `billed_usd`는 `null`이다. 신뢰할 수 있는 native receipt가 spend를 보고할 때만 USD 80에서 중지하며, 이는 price reserve가 아니다.

## 6. 정확한 native CLI 경계

Transport owner가 제공한 source-supported 명령 형태는 다음과 같다.

- Codex: `codex exec --json --ephemeral --skip-git-repo-check --ignore-user-config --ignore-rules -s read-only --config approval_policy=never --model <exact-selector> -C <fresh-cwd>`; prompt는 stdin. `--dangerously-bypass-approvals-and-sandbox`는 사용하지 않는다.
- Claude: `claude -p --model <exact-selector> --dangerously-skip-permissions --disable-slash-commands --no-session-persistence --output-format stream-json --tools ''`; `--bare`는 사용하지 않는다.
- agy: `agy --print <prompt> --sandbox --dangerously-skip-permissions --disable-slash-commands --model <exact-selector> --effort medium --output-format stream-json --print-timeout 180s`. B1 plan-mode flag는 기존 exact help/probe receipt가 증명할 때만 사용한다. agy global tool availability는 `UNVERIFIED`이며 “없음”으로 주장하지 않는다.

OAuth status preflight는 read-only이고 auth file이나 email을 읽지 않는다. 환경 projection은 `PATH`, `HOME`, `TMPDIR`, locale/terminal identity 변수만 허용하며 제거한 secret/provider-routing 변수는 값 없이 이름/개수만 기록한다.

## 7. 근거·안전·주장

모든 assignment는 source hash, task/prompt/inventory hash, selector, fresh workspace/session ID, context/session hash, stdout/stderr/partial stream, usage, latency, runtime/provider identity, revision, seed, billed USD, failure, stop reason을 도착 순서대로 보존해야 한다. 동결 시점에는 모든 runtime field가 `null`, `launched=0`, attempt artifact 0개다.

생성된 Godot code를 실행하지 않는다. B1 host QA는 별도 sandbox-gate repair와 fresh checker/profile proof 전까지 blocked다. 모델 self-report는 AC pass가 아니다. C1 hard validity는 quality/novelty와 분리하고 composite score를 만들지 않으며, 별도 승인 없는 repair를 하지 않는다.

이 artifact는 model superiority, ontology superiority, causal efficacy, productivity, player benefit, API price, provider identity/revision 또는 Argon 역사에서 상속한 새 결과를 주장하지 않는다. Failure, blocked, timeout, missing evidence는 원래 상태와 분모를 유지한다.

**다음 행동:** transport owner는 이 동결 manifest에 대해서만 read-only OAuth status/preflight를 수행하고 receipt를 첨부할 수 있다. 이 파일들은 변경하지 않는다.
