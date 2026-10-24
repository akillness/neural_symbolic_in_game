# 전향적 개발 비교 계획

**연구 라벨:** `development-comparison-20261023`  
**상태:** `PROPOSED_NOT_EXECUTED`  
**계획일:** 2026-10-23  
**소유 역할:** 전향적 비교 계획 소유자. 실행에는 별도 승인과 launch receipt가 필요하다.

## 1. 이 계획의 이유

현재 근거는 전체 게임 제작 근거가 아니다. `research/development-cases/ontology-map-20261023-01/`에는 운영자 보조의 읽기 전용 이중언어 대시보드 확장 한 건만 있다: `development_runs=1`, `native_cli_invocations=6`, `independent_repeats=0`. 개발 비교군도, 독립 반복도 없다. 관측된 `5942.665 s` 벽시계 시간은 그 사례의 서술적 사실로만 보존한다. 새 endpoint baseline, 순수 추론 지연, 생산성 측정값 또는 비교군 결과가 아니다.

따라서 이 계획은 새롭고 자체 완결적인 Godot 마이크로게임 제작의 전향적 연구를 제안한다. 기존 사례를 재해석하거나 모델 결과를 만들거나 유료/제공자 작업을 승인하지 않는다. 불변 raw 자료, archive, 동결 결과와 private intake는 이 계획의 범위 밖에 둔다.

동반 프로토콜은 `protocol.json`, 영문 계획은 `plan.en.md`이다. 세 파일은 같은 ID, 상태, 요인, 분모와 중지 규칙을 유지해야 한다.

## 2. 양보할 수 없는 경계

- 이 계획으로 모델 호출, 빌드, 배포, Git 작업, credential 사용, 유료 생성 또는 외부 제공자 호출을 시작하지 않았다.
- 승인된 launch receipt가 생기기 전까지 모든 향후 assignment와 artifact의 상태는 `PROPOSED_NOT_EXECUTED`이다.
- 요청된 모델명은 제공자 identity, 불변 revision, seed, 비용 또는 이용 가능성의 증명이 아니다. requested, runtime-reported, provider-returned 필드를 분리해 기록하고 모르는 값은 `null`로 둔다.
- UI 자문은 coding comparison이 아니다. Gemini App Argon은 실제 tool-capable이고 독립 관측 가능할 때만 coding arm에 들어갈 수 있다. Pro 또는 Flash를 Argon으로 이름 바꾸지 않는다.
- 실패, 미완료, blocked, timeout assignment는 각각 실패/미완료/blocked/timeout 관측값으로 남긴다. 중지 시각은 성공 시각이 아니다.
- tool call, repair attempt와 재개한 session은 독립 sample이 아니다. 각 독립 run에는 새 workspace와 새 thread가 필요하다.
- 기존 `5942.665 s`는 서술적 역사 맥락으로 유지하며 새 endpoint 분모에 넣지 않는다.

## 3. 단계별 실행 계획

### S1 — credential-free replay, observer, rubric, adaptor 사전 점검

**상태:** `PROPOSED_NOT_EXECUTED`.

credential, provider 호출, 유료 지출, 배포 또는 모델 생성 없이 수행한다.

1. 기존 사례의 보존 receipt만 replay한다. hash, event 순서, 상태 의미와 읽기 전용 동작을 확인한다. 이것은 새 run이 아니라 replay임을 표시한다.
2. coding assignment 전에 arm-neutral observer inventory를 동결한다. brief/evidence receipt, rule version과 representation, 새 workspace/thread, 시작 checkout과 asset, requested/runtime/provider identity, adaptor/tool capability, 모든 command/tool call, 파일 diff, build/test/QA, repair 경계와 rerun, save/load, read-only signal, intervention, stop reason, 최종 acceptance와 독립 평가를 포함해야 한다.
3. 이중언어 rubric을 결정론적 fixture에서 `PASS`, `FAIL`, `NOT_REACHED`, `TIMEOUT`, `SAFETY_STOP`, `BLOCKED_UNAVAILABLE`, `MISSING_EVIDENCE`, `N/A`, `COVERAGE_INDETERMINATE`에 대해 dry-check한다.
4. 필요한 근거가 없으면 `PASS`로 바뀌지 않는지 확인한다. `N/A`는 구조적 사유와 분모 항목이 있을 때만 허용한다. Repair는 실제 repair가 0회임을 독립적으로 확인한 경우에만 `N/A`다.
5. Adaptor capability 선언을 현재 로컬 runner 근거와 대조한다. 알려지지 않은 새 model runner는 `IMPLEMENTATION_REQUIRED`이며 working runner가 아니다.

**S1 종료 gate:** schema가 parse되고, replay가 읽기 전용이며, 모든 observer field에 소유자가 있고, rubric fixture가 fail-closed를 보존하며, credential/provider/유료 경계를 넘지 않는다.

### S2 — shared-tool-interface feasibility

**상태:** `PROPOSED_NOT_EXECUTED`.

Coding comparison에는 다음 능력의 parity가 필요하다.

- 새 workspace와 새 thread;
- 동일한 완전한 brief와 evidence receipt;
- 파일 read/write와 허용 command 실행;
- build/test/readback과 diff capture;
- command `argv`, 구조화된 tool argument, stdout, stderr, exit code, elapsed;
- tool call, intervention, repair 경계와 rerun;
- identity field와 capability receipt;
- save/load, 결정론적 replay와 fallback 없이 중지.
- 공통 prompt, tool permission, compute 환경, clock source와 동일한 starting checkout;

후보 system:

1. **Native Codex runtime, runtime-reported `gpt-6.1-sol`.** 실제 native turn receipt가 그 선택을 보고할 때만 launch한다. Provider-returned model, immutable revision, seed, cost가 없으면 `null`로 둔다. Self-report는 provider attestation이 아니다.
2. **명시적으로 발견·검증된 Claude model 하나.** 정확한 model identifier는 승인된 runtime에서 얻고 protocol freeze 전에 검증한다. ID를 발명하거나 UI label에서 이용 가능성을 추정하지 않는다.
3. **Gemini App Argon.** 실제 file edit, command/build, readback, observer 지원을 시험한다. 자문 전용 UI 동작은 coding evidence가 아니다. Argon이라는 이름을 그대로 보존하고 Pro/Flash를 대체·재명명하지 않는다.
   현재 UI 관측에서 Argon option/selection(`4 Argon complex tasks`)이 보일 수 있지만 response나 coding-tool parity는 확립되지 않았다. 이는 consultation UI availability로만 기록하며 coding availability로 기록하지 않는다.

동등한 coding/tool/observer parity가 없으면 whole-game assignment 전에 다음 중 하나를 동결한다.

- `SPLIT_STACK_COMPARISON`: stack 차이를 공개하고 coding endpoint를 합치지 않는다.
- `BLOCK_ARGON_CODING_ARM`: Argon 계획 cell을 blocked/unavailable로 보존하고 분모에 기록한다.

Fallback model을 조용히 사용하거나 UI 자문을 coding arm으로 바꾸지 않는다.

**S2 종료 gate:** 최소 두 system이 비교 가능한 capability를 검증받거나, blocked/split-stack 결정을 동결하고 unavailable system을 launched coding run에서 제외하되 계획 분모에서 지우지 않는다.

### S3 — 새 whole-game microgame task

**상태:** `PROPOSED_NOT_EXECUTED`.

각 assignment에는 같은 frozen checkout, 완전한 brief, asset, evidence와 acceptance suite를 준다. 새 workspace와 새 thread에서 시작한다. Resume은 repeat가 아니다. Licensed 또는 procedural asset만 사용하고 provenance/license receipt를 기록한다. 승인 없는 다운로드나 유료 생성은 허용하지 않는다.

자체 완결 Godot microgame은 다음 열 가지를 모두 통과해야 한다.

| ID | 동결된 acceptance 요구사항 |
|---|---|
| `AC-SCENES` | 최소 두 개 named scene이 clean checkout에서 로드되고, 숨은 수동 설정 없이 선언된 경로로 전환된다. |
| `AC-MOVEMENT` | 선언된 player movement/input이 허용 fixture에서 결정론적으로 작동하고 동결 근거를 변경하지 않는다. |
| `AC-GAME-GOAL` | 선언된 goal에 재현 가능한 성공 조건과 보이는/읽을 수 있는 완료 receipt가 있다. |
| `AC-ONTOLOGY-GATE` | 선언된 ontology/policy gate가 무권한 action을 거부하고 frozen rule ID를 사용해 권한 action을 허용한다. |
| `AC-REPAIR` | 제한된 repair가 원래 candidate, error, change, rerun을 기록한다. 실패한 repair도 추적 가능하고 조용히 commit하지 않는다. |
| `AC-REPLAY` | 같은 receipt에서 replay하면 선언된 decision, acceptance 상태와 관련 state/hash 출력이 재현된다. |
| `AC-READONLY-SIGNALS` | read-only signal이 선언 상태와 관측 상태, missing/unreported evidence를 보여주며 game state나 frozen input을 변경하지 않는다. |
| `AC-SAVE-LOAD` | save/load가 canonical state, version/hash와 goal 관련 fact를 보존하고 round-trip receipt를 남긴다. |
| `AC-BUILD` | 승인된 기존 build path 또는 별도 승인된 새 runner가 clean checkout에서 실행 가능한 artifact를 만든다. 모르는 runner를 working이라고 주장하지 않는다. |
| `AC-DETERMINISTIC-QA` | 격리 copy에서 반복한 결정론적 QA가 같은 선언 결과를 만들고, seeded valid corruption을 검출하며, false clean 결과를 수용하지 않는다. |

후보 pilot task block은 `B1`(exploratory signal-hunt microgame)과 `B2`(exploratory gate-and-escape microgame)이다. 이름이 열 가지 suite를 완화하지 않는다. 이후 held-out block `H1`, `H2`는 보류하며 pilot을 조정하는 데 쓰지 않는다.

### S4 — matched-information factorial block

**상태:** `PROPOSED_NOT_EXECUTED`.

요인은 다음과 같다.

- representation: `general_rule` × `ontology_representation`;
- system: S2를 통과한 각 system;
- task block: pilot에서는 `B1`, `B2`, 이후 별도 동결 후 held-out block;
- independent run: 새 workspace + 새 thread이며 resume은 금지.

두 representation에는 같은 완전한 fact, policy, example, 허용 tool, asset과 acceptance suite를 넣는다. 계획된 정보 요인은 표현 encoding이며 불균등한 evidence가 아니다. representation/system/task 순서를 frozen seed로 randomize 또는 counterbalance하고 launch 전에 기록한다. 편의 순서를 쓰지 않는다.

Composite quality-time-traceability score를 만들지 않으며 ontology나 model 우월성을 전제하지 않는다. 각 결과를 따로 보고한 다음 task-block nesting을 보존하는 matched/clustered 분석을 한다.

### S5 — feasibility pilot 이후 larger repetition과 held-out task

**상태:** `PROPOSED_NOT_EXECUTED`.

먼저 아래의 작은 pilot만 실행한다. 이는 명시적으로 **exploratory이며 powered 또는 confirmatory가 아니다**. Sample-size benefit, significance, model ranking, ontology superiority, developer productivity 또는 player-benefit 주장을 지지할 수 없다.

Pilot은 interface, acceptance suite, observer inventory, repair 경계, timing과 결정론적 replay가 실제로 운용 가능한지 묻는다. Gate가 통과하면 larger repetition count와 held-out task block을 더 큰 실행 전에 동결한다. Gate가 실패하면 해당 arm/study를 중지하고 구체적 blocker를 보존한다. 실패를 버리거나 분모를 바꿔 missing evidence를 고치지 않는다.

## 4. 후보 pilot matrix (exploratory 전용)

각 cell은 새 workspace/thread를 사용하는 `I=2`개의 독립 run을 배정한다. Argon cell은 S2가 실제 coding/tool/observer capability를 검증하기 전까지 계획상 존재하지만 blocked다.

| Representation | System | B1 | B2 | Cell 상태 |
|---|---|---:|---:|---|
| `general_rule` | native Codex runtime-reported `gpt-6.1-sol` | 2 | 2 | S2 조건부 |
| `ontology_representation` | native Codex runtime-reported `gpt-6.1-sol` | 2 | 2 | S2 조건부 |
| `general_rule` | 검증된 Claude model | 2 | 2 | S2 및 정확한 model ID 조건부 |
| `ontology_representation` | 검증된 Claude model | 2 | 2 | S2 및 정확한 model ID 조건부 |
| `general_rule` | Gemini App Argon | 2 | 2 | tool-capable일 때만 가능 |
| `ontology_representation` | Gemini App Argon | 2 | 2 | tool-capable일 때만 가능 |

세 system 모두인 경우 계획 count는 24 assignments이며, 두 system feasibility 경우는 16이다. 이는 배정 계획이지 관측치, power calculation 또는 sample benefit가 아니다. System이 blocked이면 계획 cell은 `N_planned_cells`에 남고 `N_launched=0`이 되며 조용히 제거하지 않는다.

**Factorial 공식:**

- `N_planned_cells = R × S × T`: `R=2` representation, `S`는 S2를 통과한 system 수, `T=2` pilot task block.
- `N_assigned = R × S × T × I`: cell당 `I=2`개의 새 독립 repeat.
- planned, assigned, launched, completed, all-pass, failed, timeout, blocked, missing-evidence 분모를 분리한다.

## 5. Endpoint, quality와 traceability

### Primary endpoint

`time_to_first_all_predeclared_validation_pass`는 완전한 frozen brief/evidence receipt를 전달한 시각부터 마지막 applicable acceptance check가 처음 독립적으로 `PASS`를 검증한 시각까지의 연속 초다.

Waiting, planning, tool call, coding, build/test, repair, rerun과 승인된 operator intervention을 포함한다. 미완료, 실패, timeout, safety-stop, blocked, missing-evidence run은 성공이 아닌 관측값으로 남긴다. Stop time을 성공 시간으로 대체하지 않는다.

### 분리된 secondary output

1. **Quality:** acceptance ID마다 상태와 run-level all-pass indicator; time/quality composite score는 만들지 않는다.
2. **Time:** run별 endpoint, censoring/stop reason과 cap; 성공 시간이 없으면 대체값을 넣지 않는다.
3. **Traceability:** 여섯 개의 binary verified-link dimension을 따로 보고한다.

여섯 traceability dimension은 다음과 같다.

- `D1` exact artifact/activity binding;
- `D2` request → rule version → actual check/result → decision;
- `D3` decision → observed state/diff/no-op outcome;
- `D4` trigger → repair change → rerun → actual result;
- `D5` requirements → implementation → verification 및 reverse change → requirement coverage;
- `D6` independently exercised audit/replay targets.

Canonical rubric cross-reference: `research/traceability-scoring-20261023/rubric.json`를 계획된 rubric source로 사용한다. `D1→TR01` identity/activity binding, `D2→TR02` decision evidence chain, `D3→TR03` decision-to-effect, `D4→TR04` repair chain, `D5→TR05` bidirectional requirement coverage(전진/역방향 별도), `D6→TR06` independent evidence exercisability로 매핑한다. 이 cross-reference는 제안이며 검증·실행되지 않았다.


각 dimension `d`에 대해 `n_d`는 **모든** 사전 선언 link가 독립적으로 검증된 applicable unit 수이고, `N_d`는 완전한 arm-neutral observer inventory에 있는 모든 applicable opportunity 수다. `n_d/N_d`와 link별 count를 분리 보고한다. 필요한 link가 없으면 0이며 PASS가 아니다. Inventory가 불완전하면 coverage는 `INDETERMINATE`이고 complete percentage가 아니다. 실제 repair가 0회임을 독립적으로 검증한 경우에만 repair를 `N/A`로 둔다. 실패한 repair도 완전히 traceable할 수 있다.

### 모든 assigned denominator

- `N_planned_cells`: launch 전에 선언한 모든 representation × system × task-block cell, 조건부 blocked cell 포함.
- `N_assigned`: 배정된 모든 새 독립 run.
- `N_launched`: launch receipt 경계를 통과한 assignment.
- `N_completed`: 모든 applicable acceptance가 해소되고 observer inventory가 완전한 launched run.
- `N_all_acceptance`: acceptance ID별 모든 applicable launched run; pass/fail/not-reached를 분리.
- `N_all_pass`: 모든 applicable acceptance ID가 독립적으로 pass인 run.
- `N_failed`: acceptance 또는 validity/safety check가 실패한 launched run.
- `N_timeout`: first all-pass 전에 frozen time cap에서 중지한 launched run.
- `N_blocked_unavailable`: model/tool/consent/capability prerequisite가 없어 launch하지 않은 계획 cell.
- `N_missing_evidence`: 필요한 observer evidence가 없는 launched run; 보존하고 invalid/indeterminate로 표시.
- `N_d`: traceability dimension `d`의 모든 applicable observer opportunity; 성공 run만 세지 않는다.
- `N_link`: 각 `N_d` 내부 link별 opportunity 분모.

Task block을 cluster/pair key로 쓴다. 새 독립 run은 task block 안에 중첩되며 task-level 독립 population으로 취급하지 않는다. Paired/clustered 분석 전에 cell별 분포를 먼저 보고한다.

## 6. Observer inventory와 독립 평가

Validity claim 전에 observer inventory가 완전해야 한다. 필요한 event type은 다음과 같다.

- complete brief/evidence receipt;
- rule version과 representation receipt;
- 새 workspace/thread identity;
- 시작 checkout과 asset-license hash;
- requested/runtime/provider model identity, immutable revision, seed, cost;
- tool/adaptor capability receipt;
- 모든 tool call과 command(`argv` 또는 구조화 argument, stdout, stderr, exit, elapsed);
- file read/write/diff와 commit boundary;
- build/test/QA/replay command와 output;
- repair-attempt 시작, change, rerun, result와 boundary;
- save/load state hash 또는 명시적 failure;
- read-only signal 관측과 missing field;
- operator intervention과 authorization;
- stop reason/timestamp;
- final acceptance vector와 independent assessor receipt.

Runner/author, arm-neutral observer, independent assessor를 분리한다. Blinded-as-feasible한 두 coder가 adjudication 전에 raw acceptance/traceability rating을 lock한다. Adjudication은 raw observation을 다시 쓰면 안 된다.

Replay control에는 seed receipt deletion, swapped attempt/revision, polarity inversion, omitted failed repair, format-only/irrelevant decorative change, clean control copy를 포함한다. Detected valid corruption, seeded valid corruption, false alarm을 분리 기록한다. 형식만 바꾼 변경 또는 무관한 장식 변경은 grade를 바꾸지 않아야 한다.

## 7. Cap, runner contract와 fail-closed launch

두 experimental track 전체에 공유되는 **추가 API spend aggregate ceiling USD 100**은 2026-10-23 user ask로 명시적으로 승인되었다. 이는 pooled ceiling일 뿐 operational per-run guard가 아니다. Per-run budget, input/output token, wall-time, repair-attempt, tool-call, operator-intervention, price guard는 계속 `null`/미승인이고 execution consent/launch receipt도 별도다. Operational guard가 null이거나 launch receipt가 없으면 checklist를 실패한다. 모든 launch gate가 통과했거나 72-assignment grid가 funded라고 주장하지 않는다. 새 study run은 실행되지 않았다.

### 모든 assignment 전 prerequisite

S2/S3 전에 승인된 study brief, 정확한 starting checkout, 동일한 prompt/evidence와 tool permission, 선언된 compute 환경과 monotonic clock source, licensed/procedural asset receipt, neutral acceptance author와 independent assessor, capability/adaptor receipt, observer schema, randomization seed, null이 아닌 승인된 cap/consent가 준비되고 동결되어야 한다. 하나라도 없으면 preflight에 머물고 launch하지 않는다.


현재 관측된 정확한 기존 runner command는 이전 dashboard 사례의 다음 명령뿐이다.

```text
uv run --extra dev python -m pytest tests/test_ontology_evidence_map.py tests/test_signal_explainer.py tests/test_godot_web_release.py -q
bash scripts/build_godot_web.sh
```

이 명령은 기존 project evidence로만 보존하며 whole-game microgame runner가 아니다. 새 microgame runner/config entrypoint는 승인된 credential-free 구현/preflight가 정확한 `argv`와 config를 제공하기 전까지 `IMPLEMENTATION_REQUIRED`다. 명령을 발명하거나 모르는 runner를 기존 working runner처럼 쓰지 않는다.

### Fail-closed launch checklist

다음이 모두 true이고 receipt로 확인될 때만 launch한다.

1. 명시적 실행 승인, consent와 cap이 있다.
2. 정확한 starting checkout, brief, representation packet, asset/license, acceptance ID와 observer schema가 동결됐다.
3. randomization/counterbalance seed가 동결됐다.
4. Codex runtime identity가 native runtime에서 보고되고, Claude identity가 발견·검증됐으며, Argon이 독립적으로 tool-capable이거나 coding arm이 blocked/split-stack이다.
5. Shared tool/observer parity가 검증됐다.
6. 승인 없는 credential, 유료 provider, network, deployment, Git 작업 또는 download가 필요하지 않다.
7. Repair 경계, no-fallback 정책과 stop reason이 동결됐다.
8. Replay, mutation control, clean control과 independent assessor access가 준비됐다.

항목 하나라도 false 또는 null이면 launch하지 않는다.

## 8. 역할과 cold-start 인계

**역할:**

- plan owner: 이중언어 contract와 claim boundary 유지;
- adapter/runner engineer: shared interface와 runner receipt만 구현·검증;
- neutral acceptance author: 실행 전에 rule, acceptance와 expected outcome 동결;
- arm-neutral observer: complete inventory와 immutable raw receipt 수집;
- independent assessor A/B: adjudication 전 raw coding lock;
- safety/release gate: consent, cap, license, no-network/no-spend/no-deploy와 rollback 확인;
- adjudicator: raw evidence를 고치지 않고 locked rating 조정.

**인계 순서:**

1. `protocol.json`, `plan.en.md`, `plan.ko.md`를 읽고 모든 상태가 `PROPOSED_NOT_EXECUTED`인지 확인한다.
2. Protocol에 적힌 public current contract/result와 interview note만 읽는다. Raw/archive/frozen output을 보존하고 private intake는 읽지 않는다.
3. Model call 없이 credential-free S1 replay/observer/rubric/adaptor preflight를 구현하고 receipt를 만든다.
4. S2 capability discovery를 수행한다. Claude model ID는 검증된 runtime receipt에서만 채운다. Argon이 tool-capable인지 결정하고 아니면 block 또는 split-stack을 동결한다.
5. Complete microgame brief, B1/B2 block, representation packet, asset/license, acceptance ID, observer schema, order seed와 모든 cap/approval을 동결한다.
6. 승인된 경우에만 모르는 microgame runner를 구현한다. 구현되고 preflight를 통과한 뒤 정확한 argv/config를 기록한다.
7. 새 workspace/thread와 독립 repeat로 exploratory matrix를 실행하고 모든 분모와 stop reason을 보존한다.
8. 두 independent coder가 raw rating을 lock한 뒤 replay mutation과 clean-control 검사를 실행한다.
9. Feasibility decision을 내린다. 명시적 승인 전에는 larger repeat와 H1/H2를 동결하지 않는다. 실패하면 구체적 blocker와 비교 주장 없음으로 중지한다.

## 9. 중지, rollback과 안전 경계

필요한 cap, approval, consent, license, identity, parity 또는 observer field가 null/unverified일 때, 승인 없는 credential/provider/network/deployment/Git 작업이 필요할 때, acceptance/replay 근거가 없거나 변조됐을 때, repair가 경계를 넘을 때, safety/privacy/data-loss risk가 보일 때 해당 assignment/study를 중지한다.

Immutable raw receipt와 workspace snapshot을 보존한다. Assignment를 해당 사유에 따라 `STOPPED`, `FAILED`, `BLOCKED_UNAVAILABLE`, `TIMEOUT`, `MISSING_EVIDENCE`로 표시한다. 새로 승인된 새 assignment로만 재시작한다. Frozen evidence를 덮어쓰거나, 재개한 repair를 repeat로 세거나, 실패를 버리거나, provider fallback을 사용하거나, model을 재명명하거나, 역사적 pass를 현재 근거로 상속하지 않는다.

## 10. Acceptance artifact와 남은 결정

승인된 실행 후 기대 artifact는 다음과 같다.

- S1 credential-free preflight receipt;
- identity field를 분리한 verified capability/adaptor matrix;
- frozen bilingual brief와 representation packet;
- frozen acceptance/expected-outcome packet;
- fresh workspace/thread assignment와 randomization receipt;
- licensed/procedural asset provenance receipt;
- run별 immutable observer trace와 command receipt;
- run별 acceptance, save/load, replay, stop receipt;
- complete observer inventory와 missingness report;
- 두 개의 locked raw assessor coding과 adjudication log;
- exploratory cell별 descriptive summary와 denominator ledger;
- feasibility decision 및 승인된 경우에만 larger-study/held-out-task freeze packet.

남은 결정은 provider/유료 작업 실행 승인, 정확히 검증된 Claude model/runtime, Argon tool capability, common interface와 새 runner, 모든 cap, B1/B2/H1/H2 brief, representation equivalence wording와 expected-outcome 접근 분리, randomization seed, asset license, larger repetition/holdout와 expansion rule, assessor 접근과 adjudication이다.

이 계획의 어떤 output도 model superiority, ontology superiority, general efficacy, developer productivity, player benefit, 직접 receipt가 없는 provider weight/revision/cost 사실, pilot significance/power 또는 기존 dashboard-extension 사례의 whole-game evidence를 주장해서는 안 된다.

## 11. 확장 후보 cohort와 두 track 설계 (새 요청)

이 절은 기존 세 arm subset이나 whole-game acceptance contract를 폐기하지 않는다. 더 큰 전향적 cohort와 별도의 ontology-content-generation track을 추가한다. **상태는 계속 `PROPOSED_NOT_EXECUTED`이며 model call, build, deployment 또는 결과는 없다.**

### 11.1 정확한 후보 label과 identity 경계

다음 아홉 user label을 정확히 보존한다. Alias를 정규화하거나 비슷한 이름의 model로 대체하지 않는다.

| Candidate label | 이 계획의 canonical ID | 실행 상태 |
|---|---|---|
| `gpt-6.1-sol` | `null` | Read-only public label 근거가 있을 수 있으나 access, provider-returned identity, backend revision, cost와 coding parity는 미검증이다. |
| `gpt-6-sol` | `null` | Read-only public label 근거가 있을 수 있으나 access, provider-returned identity, backend revision, cost와 coding parity는 미검증이다. |
| `Astra` | `null` | User-approved mapping hint `GPT6Astra` / `gpt-6-astra`; registry join과 adaptor preflight 전까지 canonical ID는 null이다. |
| `Luna` | `null` | User-approved mapping hint `GPT6Luna` / `gpt-6-luna`; registry join과 adaptor preflight 전까지 canonical ID는 null이다. |
| `Opus5.5` | `null` | Public label 근거가 있을 수 있으나 account access, runtime model과 coding parity는 미검증이다. |
| `literal 'sonnect5.5'` | `null` | 이 raw literal label을 보존한다. 문서상 editorial display normalization은 `Sonnet5.5`뿐이며 provider attestation이나 조용한 후보 대체를 뜻하지 않는다. |
| `Fable5.1` | `null` | Public catalog label 근거가 있을 수 있으나 account access, runtime model과 coding parity는 미검증이다. |
| `literal 'gemin3.8flash'` | `null` | 이 raw literal label을 보존한다. 문서상 editorial display normalization은 `Gemini3.8Flash`뿐이며 provider attestation이나 조용한 후보 대체를 뜻하지 않는다. |
| `GeminiArgon` | `null` | Consultation UI availability는 관측됐으나 coding/content tool parity와 backing runtime identity는 미검증이다. |

`canonical ID`는 verified candidate evidence registry가 확인할 때까지 null이다. Public model card, product label, UI option, installed CLI version 또는 self-report는 account access, provider-returned identity, immutable revision, spend, coding parity 또는 content-generation parity의 증명이 아니다. Main-owned read-only identity 작업은 registry에 참고될 수 있지만 이 연구를 실행하지 않는다.

이 디렉터리의 계획된 상대 registry 경로는 `model-registry.json`, `model-panel.en.md`, `model-panel.ko.md`다. Registry가 identity evidence의 source of truth이며 exact requested label과 source ID로 join하고 display name이나 중복 identity claim으로 join하지 않는다. Registry/panel record와 S1 preflight evidence는 readiness 근거이지 study result가 아니며 launched run을 의미하지 않는다.


`Astra`와 `Luna`의 identity mapping은 registry join 대기 중인 승인된 hint일 뿐이다: 각각 `GPT6Astra` / `gpt-6-astra`, `GPT6Luna` / `gpt-6-luna`다. Raw requested label은 바꾸지 않으며, `model-registry.json`이 정확한 source-ID mapping을 확인하기 전 canonical ID는 null이고 이 승인을 provider attestation으로 추론하지 않는다. `Fable5.1`의 documented auto-fallback risk는 유지되며, launch에는 요청 후보를 증명하는 runtime/provider-returned identity receipt가 필요하다.


### 11.2 Track A — whole-game coding

Track A는 이 계획의 S3/S4 Godot task다. 새 workspace와 새 thread, 두 scene, movement, goal, ontology gate, 제한된 repair, replay, read-only signal, save/load, build, deterministic QA를 포함하며 licensed/procedural asset만 사용한다. 각 후보에는 별도 capability/adaptor receipt가 필요하다. 실제 coding tool과 observer parity를 검증하기 전까지 `GeminiArgon`은 blocked다. Consultation UI는 coding run이 아니다.

### 11.3 Track B — ontology content generation

Track B는 game-build endpoint의 이름을 바꾼 것이 아닌 별도 task family다. 각 run은 같은 frozen facts, rules, examples, task brief, tool permission, compute 환경, clock source, start checkout과 asset/license packet에서 content를 생성한다. 계획된 정보 요인은 `general_rule` 대 `ontology_representation`뿐이다.

Content task bank는 두 pilot block(`C1`, `C2`)과 두 held-out block(`HC1`, `HC2`)을 사용한다. 실행 전에 exact prompt, fact, rule, expected field, forbidden fact, example, schema version과 held-out 분리를 동결한다. 후보 output을 본 뒤 bank를 조정하지 않는다.

Hard validity는 quality score가 아니라 gate다. Schema completeness/type validity, canonical identifier와 relation/reference integrity, rule/policy consistency와 forbidden-fact exclusion, deterministic replay, read-only evidence binding을 검사한다. Content가 novel하거나 문체가 좋아도 hard-validity failure는 failure다.

Repair는 미승인 `repair_attempt_cap`으로 제한한다. 모든 repair boundary, original candidate, error, change, rerun과 실제 result를 기록한다. 실패한 repair도 traceable하며 조용히 pass할 수 없다. Repair가 없을 때만 독립적으로 zero repairs를 확인한 뒤 `N/A`를 허용한다.

Novelty와 quality는 hard validity와 분리된 exploratory output이다. 실행 전에 novelty unit, duplicate/near-duplicate baseline, seed/control case, blinding instruction과 quality rubric을 동결한다. Quality × novelty × validity composite를 만들지 않고 novelty/quality로 hard validity를 덮지 않는다. Independent human 또는 neutral grader가 adjudication 전에 raw rating을 lock한다. Jev는 advisory일 수 있지만 gold label, independent human truth 또는 commit authority가 아니다.

### 11.4 확장 matrix와 legacy subset 경계

전체 후보 계획은 **아홉 후보 × 두 representation × 두 task block × 두 새 독립 repeat = track당 72개 계획 assignment**다. 이는 exploratory이며 powered 또는 confirmatory가 아니다. 72 launched run, 새 `gpt-6.1-sol` 결과 또는 sample benefit가 아니다. Blocked/unavailable 후보는 계획 분모에 남고 `N_launched=0`이다.

이전 세 arm/24-run과 두 arm/16-run count는 legacy subset example로만 유지한다. 아홉 후보 전체 cohort 또는 새 관측값으로 제시하지 않는다.

### 11.5 두 track 전에 동결할 control

- **Exact task bank:** B1/B2와 C1/C2 prompt, fact, rule, example, acceptance ID, expected output, held-out H1/H2/HC1/HC2를 launch 전에 동결하며 사후 대체하지 않는다.
- **Information equivalence:** Matched arm은 동일한 semantic information, tool, compute, clock, starting checkout, asset와 budget cap을 받으며 representation syntax만 다르다.
- **Tool/budget parity:** 같은 allowed tool surface와 per-run budget/token/wall-time/repair/intervention/price guard를 사용한다. 이 operational 값은 별도 승인 전까지 null이다. Pooled USD 100 ceiling은 두 track에 공유되지만 per-run guard를 대체하지 않는다.
- **Grader independence:** Human/neutral grader는 candidate author/runner와 독립적이고 adjudication 전에 raw rating을 lock하며 Jev를 gold로 사용하지 않는다.
- **Clustering과 censoring:** Track 및 task block 안에서 cluster/pair한다. 새 repeat는 nested run이다. Failure, timeout, safety stop, blocked, missing-evidence는 non-success이며 missing time-to-pass를 stop time으로 대체하지 않는다.
- **Multiplicity:** Larger study 전에 confirmatory contrast, family와 multiplicity procedure를 사전 선언한다. Pilot은 descriptive다.
- **Held-out task:** H1/H2/HC1/HC2에 prompt, representation, rubric, repair 또는 novelty metric을 맞추지 않으며 결과를 별도 보고한다.
- **Novelty control:** Novelty unit, duplicate control, clean control, grader blinding과 false-alarm 처리를 사전 선언하며 novelty를 hard validity와 quality에서 분리 보고한다.

### 11.6 Runnable harness 경계와 추가 pickup

이 계획의 기존 exact command는 이전 dashboard 사례 검사뿐이다. Whole-game coding runner와 ontology-content runner는 승인된 credential-free 구현/preflight가 exact `argv`와 config entrypoint를 만들기 전까지 모두 `IMPLEMENTATION_REQUIRED`다. Harness가 있는 것처럼 쓰지 않는다.

기존 pickup sequence 다음 cold-start 단계는 다음과 같다: (1) 아홉 label을 정규화하지 않고 입력한다; (2) Main-owned identity registry가 준비되면 읽되 verified 전에는 canonical ID를 채우지 않는다; (3) B와 C task bank 및 held-out block을 분리 동결한다; (4) coding/content runner를 각각 구현·preflight한다; (5) 공통 information/tool/compute/clock/budget와 independent grader control을 동결한다; (6) 모든 cap/approval이 non-null이고 fail-closed checklist가 통과하기 전에는 어느 track도 실행하지 않는다.

## 12. 확장된 남은 결정

남은 결정은 exact verified Claude model/runtime, Argon tool capability, 승인된 Astra/Luna mapping hint의 registry 확인, common interface와 new runner, 모든 operational per-run cap과 price guard, B1/B2/H1/H2 brief, representation equivalence wording과 expected-outcome access separation, randomization seed, asset license, larger repetition/holdout 및 expansion rule, assessor access/adjudication이다. Pooled USD 100 ceiling은 planning에만 승인되었고 execution은 여전히 미승인·미실행이다.

## 13. 명시적 승인 revision과 최소 feasibility schedule

**Approval revision `approval-revision-20261023-01` (planning authorization only):** user가 whole-game coding과 ontology-content-generation track에 공유되는 추가 API spend ceiling USD 100을 승인했다. 이는 provider/model call 승인, fail-closed checklist 면제, per-run budget/token/wall-time/repair/tool/intervention/price guard 채움, 특정 assignment의 consent, track당 72 assignment exploratory grid의 funding을 의미하지 않는다. 새 study run은 시작되지 않았다.

모델 call 전에 다음 최소 feasibility schedule을 proposal로 freeze한다: (F0) 모든 candidate/track에 credential-free S1 replay/observer/rubric/adaptor preflight를 수행하되 provider call은 하지 않는다. (F1) identity/tool-capability와 operational guard receipt가 확인된 뒤에만 verified candidate마다 fresh B1 coding assignment 1개와 fresh C1 content assignment 1개를 `general_rule`만으로 최대 18개까지 계획한다. (F2) F1 hard launch/observer check를 통과한 cell에 한해 candidate/track별 fresh matched `ontology_representation` assignment를 최대 18개 추가한다. 이 schedule은 powered confirmation이 아닌 descriptive feasibility evidence다. Failure/block/missing evidence도 denominator와 stop reason을 유지한다. 전체 72-per-track matrix는 별도 proposed이며 funded/executable이라고 가정하지 않는다.

Editorial normalization은 문서 표시만을 위한 것이다. Raw label `literal 'sonnect5.5'`, `literal 'gemin3.8flash'`는 계약 label로 유지하며 `Sonnet5.5`, `Gemini3.8Flash`는 explicit display alias로만 쓸 수 있다. Provider-returned identity나 조용한 substitution이 아니다.
