# Engineering architecture contract / 엔지니어링 아키텍처 계약

Run ID: `20260813-sealed-lighthouse-cycle-1`  
Owner: game-programmer  
Status: `[OBSERVED]` static contract and four retained Godot 4.7.1 runs

## Authority boundary / 권한 경계

| Concern | Authoritative owner | Exchange |
|---|---|---|
| Canonical world, quest, NPC disclosure, relationship memory | Target: research-side policy/validator contract; current fixture: Godot policy mirror | Versioned candidate, validation, commit/reject events |
| Engine observation, input, save/load, local presentation, frame/request telemetry | Godot game track | `experimental-game-event.schema.json` JSONL |
| State mutation | Deterministic commit operation only | Before/after canonical SHA-256 |
| Proposal text or future live model | Untrusted, non-authoritative | Cannot mutate state before validation |
| Frozen concept images | Visual/VLM secondary track | Hash-pinned manifest only; never generated at episode runtime |

연구 런타임과 게임 런타임은 독립적으로 컴파일한다. 현재 실험 이벤트의 지원 타입은 안정 브리지
envelope로 projection해 스키마 검증하지만, 라이브 Python 권한 transport는 실행하지 않았다.
`fallback`, `reject`, `timeout`, 중복 event ID와 해시가 맞지 않는 저장 후보는 정식 상태를
변경하지 않는다.

## Implemented deterministic path / 구현된 결정론적 경로

`observe → acquire_object → rejected disclosure → safe fallback → install_lens → authorized hint → save → load → replay`

The canonical terminal state is reached by exactly three commits. A Python-side independent fixture
oracle and the Godot state machine bind the target to
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`.
This checksum is content integrity only. The frozen oracle ID is
`python-independent-sealed-lighthouse-v1`; the four retained Godot summaries match it.

## Hard invariants / 하드 불변조건

| ID | Invariant | Implemented enforcement | Evidence state |
|---|---|---|---|
| EG-I01 | Only a valid commit changes canonical state | `SealedLighthouseMachine.apply_operation` copies prior state and assigns only on zero codes | `[OBSERVED]` 3 commits/run, four runs |
| EG-I02 | Early betrayal/gated-hint request cannot mutate state | disclosure validator + fallback before/after hash equality | `[OBSERVED]` all four summaries true |
| EG-I03 | `keeper_betrayal` is never disclosed | permanent forbidden set; terminal fixture excludes fact | `[OBSERVED]` terminal saves + schema tests |
| EG-I04 | `tide_marks_hint` requires quest stage ≥2 | stage gate + post-install commit | `[OBSERVED]` all four runs |
| EG-I05 | Duplicate IDs apply at most once within one process | volatile `processed_event_ids` checked before operation | `[OBSERVED]` duplicate run count 1, terminal hash unchanged |
| EG-I06 | Timeout leaves full state unchanged | timeout and fallback share exact before/after hash | `[OBSERVED]` timeout run count 1, check true |
| EG-I07 | Valid save/load and operation replay reproduce terminal state hash | pre-mutation save checksum gate + operation replay comparison | `[OBSERVED]` four retained terminal/load/replay/oracle hashes equal; corrupt-save candidate rejected unchanged |
| EG-I08 | Timing and cost do not enter canonical state hash | telemetry lives in event/summary envelopes | `[OBSERVED]` schema/code audit |
| EG-I09 | Supported engine events project into the stable bridge envelope | `scripts/project_experimental_bridge.py` + Draft 2020-12 test | `[OBSERVED]` schema compatibility only; no live transport |

## Artifact and schema map / 산출물·스키마 맵

- Godot source of truth: `game-track/godot/`
- Frozen scenario: `game-track/godot/data/sealed_lighthouse.json`
- Execution inputs: `data/fixtures/experimental-game-*.json`
- Event/save/summary/scenario/fixture contracts: `game-track/schemas/experimental-game-*.json`
- Static and conditional engine checks: `tests/test_godot_experimental_game.py`
- Retained run outputs and hashes:
  the immutable set selected by `_workspace/current/engineering/tech-verification/current.json`

## Paper-use boundary / 논문 사용 경계

The retained `OBSERVED_ENGINE_RUN` summaries, JSONL traces, saves, exact engine version, command,
and hashes support the authored Godot policy-mirror path toward Stage 6 M6. Independent review and
a live Python authorization round-trip remain promotion gates. This path cannot promote
cross-runtime integration, model-quality, or player-benefit claims.
Process-local duplicate suppression is not a live-adapter guarantee; persistent cross-process
idempotency storage is explicitly future work.
