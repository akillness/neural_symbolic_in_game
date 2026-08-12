# TRACE-RPG 연구 패키지 2026

> 상태: 실험 설계 및 구현 초안. 수치 결과는 아직 생성되지 않았으며 모든 실증 주장은 `TODO-RESULT`로 잠겨 있다.

TRACE-RPG는 LLM이 제안한 세계 변화와 NPC 발화를 곧바로 게임 상태에 기록하지 않는다. 모든 제안은 타입화된 이벤트로 변환되고, 권위 있는 행동 정책 오라클·지식 그래프·퀘스트 정책·도달 가능성·금지 정보 규칙을 통과한 경우에만 커밋된다. 실패하면 구조화된 반례를 이용해 제한 횟수만 수리한다. 연구 트랙과 게임 개발 트랙은 독립적으로 빌드되지만 동일한 버전 계약과 재생 가능한 이벤트 로그로 연결된다.

## 목표 저널과 논문 수준

1차 투고 후보는 게임 AI·플레이어 모델링·게임 평가 범위가 직접 맞는 **IEEE Transactions on Games**다. 방법론 기여가 더 강하면 **Knowledge-Based Systems**, 감정 추론의 독립적 기여가 충분하면 **IEEE Transactions on Affective Computing**, 응용·사용자 연구 중심이면 **Entertainment Computing**을 재검토한다. 색인 상태는 변할 수 있으므로 제출 직전 Clarivate Master Journal List에서 SCIE 여부를 다시 확인하는 것을 필수 게이트로 둔다.

저널 수준 주장은 사전등록된 1차 평가지표, 파일럿 분산에 근거한 검정력 분석, 세계·퀘스트 템플릿 단위 홀드아웃, 혼합효과모형, 효과크기와 95% 신뢰구간, 다중비교 보정, 독립 인간평가, 실패 사례와 전체 추적 아티팩트를 요구한다.

상세 투고 게이트: [`research/journal-targets.ko.md`](research/journal-targets.ko.md)

## 핵심 연구 질문

- RQ1: 심볼릭 커밋 게이트가 모델 크기와 무관하게 불가능한 세계 상태와 정보 누설을 줄이는가?
- RQ2: 반례/unsat-core 기반 수리가 단순 재시도보다 유효 상태를 더 효율적으로 복구하는가?
- RQ3: 지식 그래프 검색과 시간 메모리가 장기 대화 일관성을 높이면서 서사 다양성을 보존하는가?
- RQ4: 불확실성 보정된 감정 신호가 하드 유효성을 악화시키지 않고 목표 긴장 곡선 추종을 개선하는가?
- RQ5: 동일 컨트롤러의 이득이 10개 모델 스크리닝과 3개 모델 확증 단계에서 재현되는가?

## 빠른 시작

```bash
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
uv run python scripts/validate_harness.py
uv run python examples/headless_demo.py
```

현재 실행 범위는 로컬 정책 검증기, 제한 수리/fallback, 전체 수리 이력 해시와 JSONL writer, 스키마 fixture, headless 예제다. 실제 10개 모델 추론 어댑터, MLflow/에너지 텔레메트리, Godot/Unity transport, 인간 연구는 명세만 있으며 아직 구현되지 않았다. 실제 추론 환경은 `game-track/README.ko.md` 계약을 구현한 뒤 연결한다.

## 디렉터리

| 경로 | 역할 |
|---|---|
| `paper/ko`, `paper/en` | 동일 주장 ID를 공유하는 한·영 논문 초안 |
| `configs/` | 10개 모델, 실험군, 시나리오, 평가 지표 SSOT |
| `src/nesy_game/` | 결정론적 계약과 최소 검증기 |
| `game-track/` | 엔진 독립 게임 브리지와 재생 계약 |
| `research/` | 원본 보존, Scrapling 캡처, 근거·주장 원장, 심층연구 |
| `harness/` | 에이전트 역할, 워크플로우, 검증 게이트 |
| `../llm-wiki/` | 프로젝트 지식 위키와 Graphify 그래프 |
| `visuals/` | 논문/README용 SVG 원본 |

## 재현성 경계

- LLM/VLM은 후보를 만들거나 소프트 신호를 제안할 뿐, 권위 있는 세계 상태가 아니다.
- SMT/규칙 검증은 **인코딩된 제약**만 보증한다. 의미 검증 누락은 별도 false-negative 감사로 측정한다.
- 합성 플레이어는 스트레스 테스트 도구이며 인간 경험의 증거가 아니다.
- `raw/`와 실행 추적은 불변이며, 논문 표는 추적 ID에서만 생성한다.
- 공개 가중치와 오픈소스를 같은 뜻으로 쓰지 않는다. 라이선스와 사용 정책을 모델별로 기록한다.

## 다음 실행 순서

1. 파일럿으로 시나리오 난이도, 검증기 누락률, 인간평가 분산을 추정한다.
2. 분석계획과 1차 지표를 동결하고 검정력 분석 후 표본 수를 확정한다.
3. 10개 모델을 저비용으로 스크리닝하고 사전 정의된 Pareto 규칙으로 3개를 승격한다.
4. 3개 모델 × 6개 시스템군 × 3개 트랙의 확증 실험과 절제 실험을 수행한다.
5. 독립 평가와 재현성 감사를 통과한 실행만 논문 결과에 반영한다.
