# TRACE-RPG 연구 패키지 2026

> 상태: 구현 및 설계 fixture 논문 초안. 확증 효능 결과는 아직 없으며 `C-RESULT-001`--`005`는 `TODO-RESULT`다. 유일한 수치 근거는 결정론적 오프라인 적합성 파일럿이다.

TRACE-RPG는 LLM이 제안한 세계 변화와 NPC 발화를 곧바로 게임 상태에 기록하지 않는다. Parsing에 성공한 제안은 typed candidate event가 되고, 외부에서 공급된 행동 정책과 precondition·도달 가능성·NPC 지식·정보 공개·quest stage에 대한 결정론적 검사를 통과한 경우에만 커밋된다. 유효하지 않은 후보는 구조화 validation error를 만들고 제한된 repair 기회를 받을 수 있으며, adapter와 controller failure는 분류된 terminal row로 남는다. 지식 그래프 검색과 게임 엔진 연동은 versioned event contract로 연결되는 별도 확증 트랙이며, 현재 파일럿에서 완료된 근거로 표현하지 않는다.

## 시각 자료

여섯 개 SVG는 모두 `scripts/generate_readme_visuals.py`가 생성한다. V2 하단, V3, V4는 동결된 파일럿 CSV와 주장 원장에서 직접 읽으므로 원본 수치와 어긋날 수 없다. 실선은 구현되어 파일럿에서 실행된 요소이고, 점선은 명세만 있고 근거가 없는 미구현 요소다.

### V1 · 신뢰 경계

![신뢰 경계: 학습된 제안, 심볼릭 권위](visuals/system-architecture.svg)

제안자는 감정 추정 `z_t`, 그래프 검색, 시간 메모리를 관찰할 수 있으나 이들 중 어느 것도 커밋 권한을 갖지 않는다. 정식 상태는 게이트를 통과한 `T(c_t, a_t)`로만 바뀐다. 인코딩된 유효성은 인코딩된 술어에 한한 유효성이며, 인식하지 못한 최상위 candidate field는 현재 거부가 아니라 무시된다.

### V2 · 단일 트랜잭션

![파싱, 검증, 제한 수리, 방어 검증, 커밋](visuals/commit-transaction.svg)

예산 안에서 어떤 후보도 검증을 통과하지 못하면 정식 상태는 그대로 유지된다. 최초 후보가 실패해도 수리 후 commit될 수 있으며, 완료된 candidate attempt는 종단 결과 전에 모두 기록된다. 하단 repair arm 수치는 `repair-arm-summary.csv`에서 읽는다.

### V3 · 파일럿 관찰값 전체

![동결된 아티팩트에서 생성한 모든 파일럿 수치](visuals/pilot-evidence.svg)

각 행의 분모는 그 행에 한정된 설계 사례 수이며 행 간 비교는 성립하지 않는다. `0/2`와 `5/7`은 설계된 결과이지 회귀가 아니다. 신뢰구간, 유의성 검정, 인과 비교는 주장하지 않는다.

### V4 · 주장 원장 상태

![주장 원장 상태](visuals/claim-status.svg)

설계 fixture 근거는 효능 주장으로 승격되지 않는다. 상류 trace나 분석 해시가 바뀌면 검증 상태는 취소된다.

### V5 · 학술 파이프라인 진행 상태

![학술 파이프라인 상태](visuals/research-workflow.svg)

### V6 · 계획된 확증 설계 (미실행)

![계획된 확증 실험 설계](visuals/confirmatory-design.svg)

## 목표 저널과 논문 수준

1차 투고 후보는 게임 AI·플레이어 모델링·게임 평가 범위가 직접 맞는 **IEEE Transactions on Games**다. 방법론 기여가 더 강하면 **Knowledge-Based Systems**, 감정 추론의 독립적 기여가 충분하면 **IEEE Transactions on Affective Computing**, 응용·사용자 연구 중심이면 **Entertainment Computing**을 재검토한다. 색인 상태는 변할 수 있으므로 제출 직전 Clarivate Master Journal List에서 SCIE 여부를 다시 확인하는 것을 필수 게이트로 둔다.

저널 수준 주장은 사전등록된 1차 평가지표, 파일럿 분산에 근거한 검정력 분석, 세계·퀘스트 템플릿 단위 홀드아웃, 혼합효과모형, 효과크기와 95% 신뢰구간, 다중비교 보정, 독립 인간평가, assignment-complete outcome record, proposal outcome이 존재할 때의 완전한 trace를 요구한다.

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
uv run python examples/recorded_experiment.py
uv run python scripts/generate_readme_visuals.py
```

현재 실행 범위는 로컬 정책 검증기, 제한 수리/fallback, 전체 수리 이력 해시, semantic JSONL replay, 네트워크 없는 recorded-response 실험 어댑터다. 오프라인 runner는 모델 revision·seed·토큰·provider/runner 지연·실패·commit 상태를 스키마 검증 JSONL에 보존한다. 마지막 명령은 위 여섯 개 SVG를 동결된 파일럿 아티팩트와 주장 원장에서 다시 생성하므로, 수치가 바뀌면 그림도 함께 갱신된다. 실제 10개 모델 API/로컬 서빙 어댑터, MLflow/에너지 텔레메트리, Godot/Unity transport, 인간 연구는 아직 명세 단계다.

## 디렉터리

| 경로 | 역할 |
|---|---|
| `paper/latex/en`, `paper/latex/ko` | 정식 영문·국문 IEEE Stage 4 원고와 PDF |
| `paper/en`, `paper/ko` | 대체된 미래 확증 연구 프로토콜 청사진 |
| `configs/` | 10개 모델, 실험군, 시나리오, 평가 지표 SSOT |
| `src/nesy_game/` | 결정론적 계약과 최소 검증기 |
| `game-track/` | 엔진 독립 게임 브리지와 재생 계약 |
| `research/` | 원본 보존, Scrapling 캡처, 근거·주장 원장, 심층연구 |
| `harness/` | 에이전트 역할, 워크플로우, 검증 게이트 |
| `../llm-wiki/` | 프로젝트 지식 위키와 Graphify 그래프 |
| `visuals/` | README·논문용 SVG 원본 (`scripts/generate_readme_visuals.py`가 생성) |
| `scripts/` | 검증기, 파일럿 runner, 논문 그림·표·README 시각 자료 생성기 |

## Stage 4 원고와 범위가 제한된 파일럿

정식 IEEE 6쪽 원고는 `paper/latex/en/main.pdf`와 `paper/latex/ko/main.pdf`다.
표는 `research/academic-pipeline/stage-04-pilot/pilot-results.json`에서 생성된다.
인코딩 오류 코드 12종에 대한 게이트 일치 `13/13`, 수리 arm 커밋 `0/2`, `0/2`,
`1/2`, 사전 지정한 탐지 가능 무결성 결함 `10/10`, 별도로 선언한 repair-provenance
경계의 replay 허용 `1/1`, adapter 결과 7건 중 commit 1건·기호 fallback 1건·분류된
failure 5건, 배정 guard `3/3`이다. 이는 저자가 설계한 fixture의 원시 count이며 live
model, player 또는 모집단 효능 추정치가 아니다.

두 PDF는 `make -C paper/latex all`로 재생성·검증한다. 빌드는 SVG 원본을 보존하면서
Type 3 font를 피하기 위한 고해상도 PNG를 포함하고, 쪽수·Type 3 font·누락 glyph·정의되지
않은 reference/citation·overfull box 회귀를 거부한다.

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
5. 독립 평가를 통과하고 assignment-complete하며 outcome이 분류된 실행만 논문 결과에 반영한다. Proposal outcome이 존재하면 완전한 trace를 요구하되, proposal trace가 생성될 수 없는 분류된 terminal failure도 denominator에 유지한다.
