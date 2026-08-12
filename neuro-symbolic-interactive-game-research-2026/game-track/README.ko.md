# 게임 개발 트랙

게임 트랙은 연구 코드를 엔진 내부에 직접 결합하지 않는다. 엔진은 `schemas/game-bridge.schema.json`을 따르는 관찰 이벤트를 보내고, 연구 런타임은 `candidate`, `validation`, `commit/reject` 이벤트를 반환한다.

현재 구현 범위는 이벤트/실험 레코드 스키마·결정론적 후보 검증·상태 불변 fallback·키 없는 콘텐츠 무결성 체크섬·semantic JSONL 재생·네트워크 없이 실험을 재현하는 frozen recorded-response 어댑터다. runner는 응답 누락과 실패도 배정 case 분모에 포함한다. 라이브 네트워크 transport, 프로세스 간 멱등 저장소, timeout fault injection은 계획된 작업이다.

라이브 어댑터 승인 조건:

- 엔진의 canonical state 변경은 유효한 `commit` 이벤트를 통해서만 일어난다.
- 모든 이벤트는 `run_id`, `episode_id`, `step`, `schema_version`, `world_state_hash`를 가진다.
- 재시도와 네트워크 중복은 영속 `event_id` 멱등성으로 제거해야 한다.
- 시간 초과, 모델 장애, 높은 감정 불확실성에서는 결정론적 안전 정책으로 fallback해야 한다.
- 연구 트랙은 실제 엔진 없이 mock bridge로 실행할 수 있고, 게임 트랙은 모델 없이 recorded trace를 재생할 수 있다.

권장 엔진 어댑터는 Godot 4.x 또는 Unity LTS에서 WebSocket/JSONL transport만 구현한다. 특정 엔진 선택은 논문 기여가 아니며 프로토콜 호환성이 기준이다.

오프라인 재현 안내: [`recorded-experiment.ko.md`](recorded-experiment.ko.md)
