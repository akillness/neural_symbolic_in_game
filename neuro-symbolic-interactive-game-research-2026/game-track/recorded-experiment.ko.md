# 기록 응답 실험 트랙

Recorded adapter는 평가 전에 제안 payload를 동결한다. 따라서 네트워크 변동과 모델 비용 없이 검증·재생·지표 코드·논문 표 생성 경로를 시험할 수 있다. `schemas/recorded-proposals.schema.json`과 런타임 경계는 묵시적 문자열/숫자 형변환, 잘못된 후보 배열, 집합 필드 중복, JSON이 아닌 metadata를 거부한다.

| 입력 필드 | 의미 |
|---|---|
| `model_id`, `model_revision` | 모든 case에 적용되는 정확한 원본 식별자 |
| `scenario_id`, `seed` | fixture 내부의 고유 조회 키 |
| `candidate` | 신뢰하지 않는 모델 제안이며 권위 있는 `ActionPolicy`가 계속 통제함 |
| `provider_latency_ms` | 응답을 최초 캡처할 때 측정한 지연 |
| `input_tokens`, `output_tokens` | 동결된 provider 사용량 |
| `failure` | 후보가 없는 timeout/API/parse 결과 분류 |

`run_experiment_case`는 배정 case당 하나의 스키마·의미 계약 검증 레코드(schema `1.2.0`)를 만든다. 누락·malformed·timeout·잘못된 adapter 응답과 분류된 repair callback 실패는 전체 정준 상태를 변경하지 않으며 treatment-policy 분모에 남는다. 완료된 제안 결과는 별도로 저장되어 체크섬 검증과 기호 상태 재생을 수행할 수 있다. Repair callback이 예외를 던져도 종단 `controller_failure` 행은 남지만, 현재 형식은 그 부분 실행의 완료 trace를 보존하지 않는다.

모든 배정 case에는 결정론적 `record_hash`가 있고, 완료된 제안 결과는 전체 `trace_hash`에도 연결된다. `proposal_hash`, `prior_state_hash`, `final_state_hash`는 선언된 제안과 전체 정준 상태를 결합한다. 보고된 토큰·지연·실패·seed·상태 또는 결합 해시를 바꾸면 체크섬이 무효가 된다. 이는 키 없는 SHA-256 무결성 검사이며 서명이나 콘텐츠와 체크섬을 함께 바꿀 수 있는 공격자에 대한 방어가 아니다. 재생은 기록된 기호 후보와 상태를 재검증하지만 repairer가 다음 후보를 만든 과정을 인증하거나 재실행하지 않는다.

연속 에피소드마다 별도의 trace JSONL 경로를 사용한다. writer는 결과/trace의 동일 경로, 서로 연결되지 않은 결과–outcome 쌍, 새 case의 이전 상태가 해당 trace의 마지막 상태와 다른 append를 거부한다. 두 파일 쓰기는 flush와 최선 노력 rollback을 적용하지만, 프로세스 간 잠금은 호출자가 담당한다.

Treatment-policy 집계에는 실행 전에 동결한 assignment manifest가 필수다. 9개 필드 키는 `(run_id, arm_id, scenario_id, seed, model_id, model_revision, controller_config_hash, assignment_input_hash, prior_state_hash)`다. `planned_experiment_assignment`가 adapter 호출 없이 키를 계산하며, 비율이나 토큰 합계를 계산하기 전에 중복 관측 행, 중복 manifest 항목, 누락 assignment, 예상하지 않은 assignment를 거부한다.

```bash
uv run python examples/recorded_experiment.py
```

출력은 Git에서 제외된 `runs/recorded-experiment/`에 저장된다. 기록된 provider 지연은 현재 장비의 실시간 지연으로 보고하면 안 되며, `runner_latency_ms`는 adapter 호출·검증·수리를 포함한 단일 실행 로컬 진단값이다. `provider_response_latency_*`는 응답을 받은 case에 조건부인 진단값이며 `latency_observed_cases`를 함께 보고하고 timeout/API 실패는 제외한다. 확증용 전체 지연 지표는 모든 배정 case에 적용할 deadline censoring 또는 timeout cap 정책을 사전등록해야 한다.
