# FunQA Tension Score Platform Stage Plan 2026-07-06

본 보고서는 강화학습(RL) 에이전트의 플레이스타일 및 비디오 데이터를 활용하여 사용자의 텐션 스코어(Tension Score)를 예측하고, 유사 게임 및 난이도 메타데이터 기반으로 근거 기반 RAG(Retrieval-Augmented Generation) 서비스를 제공하기 위한 `saas-of-funqa` 플랫폼의 8주 단계별 개발 계획을 수립한다.
> **문헌 검증 상태(2026-07-06 갱신):** 최초 초안의 인용을 `web_search`로 재검증한 결과 식별자 오기 1건을 정정하고, 가공된 것으로 판단되는 서지사항 1건을 삭제했으며, 실제 내용과 다르게 서술된 논문 설명 2건을 정정했습니다. 상세 내용은 §2의 각 "(2026-07-06 정정)" 각주 참고.

---

## 1. Executive Goal (실행 목표)

본 프로젝트의 목표는 유니티 게임을 플레이하는 강화학습(RL) 모델의 '타입'에 따라 사용자가 느끼는 레벨디자인 구간별 **Tension Score(텐션 스코어)**를 설문조사 데이터와 멀티모달 비디오 분석을 통해 모델링하고 예측하는 것이다. 
이를 위해 플레이 영상을 멀티모달 데이터로 저장하고, 텐션 스코어·유사 게임·유사 난이도 등의 메타데이터 DB를 구축하여, RAG 파이프라인을 통해 신뢰 가능한 예측 및 추천 근거를 사용자에게 시각적으로 전달하는 플랫폼을 개발한다.

---

## 2. Literature Grounding (문헌 검토 및 기술 분석)

최근 2024~2026년 학계 및 산업계의 연구 성과를 바탕으로 본 플랫폼의 설계 방향을 다음과 같이 설정한다.

### (a) Predicting Player Tension/Engagement from Gameplay Video
*   **Descriptor: Multimodal Dataset for Player Engagement Analysis in Video Games (MultiPENG)**
    *   **Venue/Year:** IEEE Xplore (document 10934747), 2025.
    *   **Description:** EEG·아이트래킹·심박수·유저 입력·웹캠 영상·게임플레이 프레임 6종 데이터를 39명 참가자로부터 동기화 수집한 데이터셋. 게임 자연 정지 구간에 몰입도 설문을 삽입해 recall bias와 플레이 방해를 최소화한 시간 정밀도가 특징이며, engagement/interest/stress/excitement 4개 심리 지표로 라벨링된 900개 세션을 포함. 웹캠만으로 몰입도를 판단한 사람 평가자는 F1 0.48에 그친 반면 flow-theory 기반 모델은 F1 0.60을 기록 — 텐션 스코어를 순수 인간 판단이 아닌 모델 기반 신호로 보강해야 하는 근거로 활용 가능.
    *   **Link:** [IEEE Xplore 10934747](https://ieeexplore.ieee.org/abstract/document/10934747/) · [Kaggle 미러](https://www.kaggle.com/datasets/ammarrashed23/multimodal-player-engagement) (Verified — 2026-07-06 재검증: 최초 초안의 `arXiv:2604.14820` 식별자는 오기였음을 확인, IEEE Xplore 1차 출처로 정정)

### (b) RL Agent Playstyle Type Conditioning for Automated Playtesting
*   **RLAnything: Forge Environment, Policy, and Reward Model in Completely Dynamic RL System / AutoTool: Dynamic Tool Selection and Integration for Agentic Reasoning**
    *   **Venue/Year:** ICML 2026 (실제 accepted poster 확인됨).
    *   **Description (2026-07-06 정정):** 최초 초안은 이 두 논문을 "플레이스타일 조건부 다양한 정책 생성" 연구로 서술했으나, 재검증 결과 실제 내용은 에이전틱 LLM의 폐루프 강화학습 트레이닝(RLAnything: 정책·보상모델·환경을 동시 최적화)과 동적 툴 선택(AutoTool)에 관한 연구로, 게임 플레이스타일 조건화나 난이도 테스트 로그 생성과는 직접 관련이 없다. 여기서는 "폐루프 자기개선 RL 트레이닝 루프" 설계 패턴만 유사 사례로 참고하며, FunQA의 RL 플레이스타일 타입 조건화 자체는 별도의 실증 근거가 필요한 자체 설계 항목임을 명시한다.
    *   **Link:** [ICML 2026 RLAnything](https://icml.cc/virtual/2026/poster/64832) · [ICML 2026 AutoTool](https://icml.cc/virtual/2026/poster/65574) (Verified, but analogy only — not a playtesting/playstyle paper)
*   **Automated Play-Testing Through RL Based Human-Like Play-Styles Generation**
    *   **Venue/Year:** arXiv:2211.17188, 2022.
    *   **Description:** 실제로 "RL 기반 플레이스타일 다양화 플레이테스팅"을 다루는 확인된 선행 연구. 인간과 유사한 다양한 플레이스타일(공격적/신중함 등)의 RL 에이전트를 생성해 자동 플레이테스팅에 활용하는 방법론을 제시 — FunQA의 RL 모델 타입 조건화 설계의 직접적 선행 근거로 채택.
    *   **Link:** [arXiv:2211.17188](https://arxiv.org/abs/2211.17188) (Verified)
*   **Automatic Generation of High-Performance RL Environments**
    *   **Venue/Year:** arXiv:2603.12145, 2026.
    *   **Description (2026-07-06 정정):** 최초 초안은 이를 "샌드박스 플레이테스팅 환경 자동 생성"으로 서술했으나, 실제 내용은 LLM을 이용해 저성능 RL 환경 구현체를 고성능(Rust/JAX 등) 구현체로 자동 번역·검증하는 기법(PokeJAX 22,320배 가속 등)이다. FunQA와의 관련성은 "다수의 게임 환경/시뮬레이터를 저비용으로 자동 이식·검증"하는 패턴 참고 수준으로 한정한다.
    *   **Link:** [arXiv:2603.12145](https://arxiv.org/abs/2603.12145) (Verified, description corrected)

### (c) Game Similarity / Difficulty-Similarity Retrieval for Recommendation
*   **2026-07-06 정정 사항:** 최초 초안은 `Agentic GraphRAG and GATs for Difficulty-Aware Recommendation (Journal of KIISE, 2026)`을 검증됨으로 표기했으나, 재검색 결과 이 조합 서지사항의 1차 출처를 확인할 수 없어 **삭제**함(가공된 인용으로 판단). 대신 실제로 확인된 개별 구성요소를 아래와 같이 분리 표기한다.
*   **Large-scale Personalized Video Game Recommendation via Social-aware Contextualized Graph Neural Network**
    *   **Venue/Year:** arXiv:2202.03392.
    *   **Description:** 소셜 그래프와 컨텍스트 정보를 결합한 GNN 기반 대규모 게임 추천 시스템 — 유사 게임 추천의 그래프 기반 접근 선례.
    *   **Link:** [arXiv:2202.03392](https://arxiv.org/pdf/2202.03392) (Verified)
*   **GraphRAG-IRL: Personalized Recommendation with Graph-Grounded Inverse Reinforcement Learning and LLM Re-ranking**
    *   **Venue/Year:** arXiv:2604.19128, 2026.
    *   **Description:** 그래프 기반 검색과 LLM 재순위화(re-ranking)를 결합한 개인화 추천 — FunQA의 유사 게임/난이도 하이브리드 검색 설계에 참고할 GraphRAG+LLM reranker 조합 패턴.
    *   **Link:** [arXiv:2604.19128](https://arxiv.org/pdf/2604.19128) (Verified Lead, 직접적인 게임 난이도 도메인 적용 사례는 아님)
*   **Dynamic Difficulty Adjustment for Maximized Engagement in Digital Games**
    *   **Venue/Year:** WWW 2017 Companion, DOI `10.1145/3041021.3054170`.
    *   **Description:** 플레이어의 지루함/좌절 상태를 관측해 게임 난이도를 실시간 조정하는 DDA 프레임워크 — 텐션 스코어를 난이도 조정 신호로 연결할 때의 고전적 기준선.
    *   **Link:** [DOI 10.1145/3041021.3054170](https://dl.acm.org/doi/10.1145/3041021.3054170) (Verified)

---

## 3. 8-Week Phased Plan (8주 단계별 계획)

개발 일정은 엔드 오브 어거스트(2026-08-31) 마감 기한에 맞추어 아래와 같이 8개 주차로 세분화하며, 모노레포 구조(`packages/`, `apps/`)에 콘크리트하게 매핑된다.

| 주차 (Week) | 마일스톤 및 주요 개발 작업 | 레포지토리 모듈 매핑 (Repo Module Mapping) |
| :--- | :--- | :--- |
| **W1**<br>(2026-07-06 ~ 07-12) | **스키마 요구사항 및 Zod 계약 정의**<br>- 텐션 데이터와 RL 플레이 영상 정보를 정의하는 공통 타입 계약 수립. | `packages/contracts`:<br>- `RlPolicyType`: 플레이스타일 속성 Zod 스키마 정의.<br>- `PlaySession`: 비디오 URL, 플레이어 로그, 세션 메타데이터.<br>- `TensionScoreLabel`: 타임스탬프, 설문 평균 점수, 표준 편차.<br>- `SimilarGameLink`: 유사도, 공유 난이도 지표, 매커니즘 태그. |
| **W2**<br>(2026-07-13 ~ 07-19) | **데이터 저장소 및 레포지토리 구축**<br>- Firestore 스키마 구현 및 데이터 파싱 유틸리티 작성.<br>- 설문조사 원시 CSV 데이터 적재 스크립트 설계. | `packages/db`:<br>- `PlaySessionRepository`: 비디오 세션 메타 적재.<br>- `TensionScoreLabelRepository`: 설문조사 평점 DB.<br>- `SimilarGameRepository`: 유사도 그래프 연결 요소 저장.<br>- `scripts/`: CSV -> Firestore 마이그레이션 도구. |
| **W3**<br>(2026-07-20 ~ 07-26) | **데이터 라벨링 마일스톤 (Survey Synthesis)**<br>- 설문 응답자들의 실시간 긴장도 추이 취합 및 전처리.<br>- 가우시안 스무딩을 적용하여 프레임별 텐션 실측값 획득. | `packages/db` & `scripts/`:<br>- 여러 평가자의 지연(latency) 및 편향을 제거하는 Normalization 공식 구현.<br>- 특정 플레이 영상의 타임라인(1초 단위)에 최종 텐션 점수 동기화 및 DB 기록. |
| **W4**<br>(2026-07-27 ~ 08-02) | **멀티모달 비디오 적재 및 청킹 파이프라인**<br>- 비디오 세그먼트를 시각 경계 기준으로 분할하고 Gemini 임베딩 모델과 매핑. | `packages/ai`:<br>- `normalize.ts` / `extract.ts`: 비디오 메타데이터 및 행동 로그 파싱.<br>- `chunk.ts`: 비디오의 레벨디자인 변화 구간 단위 시맨틱 청킹 엔진 구축. |
| **W5**<br>(2026-08-03 ~ 08-09) | **하이브리드 난이도/유사도 검색 엔진 설계**<br>- RAG 벡터 검색과 난이도 매커니즘 KG 구조적 매칭 및 가중치 병합. | `packages/ai`:<br>- `retrieve.ts`: 장르/플레이 스타일 기반 Vector Similarity + Graph Traversal retrieval.<br>- `rerank.ts`: RRF (Reciprocal Rank Fusion) + Cohere Cross-Encoder Reranker 커스텀 튜닝. |
| **W6**<br>(2026-08-10 ~ 08-16) | **Express API 엔드포인트 구현**<br>- 텐션 점수 예측 및 RAG 근거 조회를 위한 서버 라우팅 개발. | `apps/api` (Express + Genkit):<br>- `/v1/tension/predict` (비디오 입력 시 텐션 곡선 및 근거 리턴).<br>- `/v1/tension/sessions` (RL 스타일별 비디오 검색).<br>- `/v1/games/recommend` (난이도 기반 유사 게임 목록 RAG). |
| **W7**<br>(2026-08-17 ~ 08-23) | **Next.js 검색/예측 워크스페이스 통합**<br>- 텐션 곡선 시각화 및 RAG 시테이션 패널 연동. | `apps/web` (Next.js App Router):<br>- `/search` 확장: 텐션 스코어 분석 뷰 탭 추가.<br>- `/rag-lab` 확장: 실측 텐션(human survey) vs 예측 텐션(model) 곡선 시각화 블록, 비디오 citation inspector rail 설계. |
| **W8**<br>(2026-08-24 ~ 08-31) | **통합 검증 및 릴리즈 게이트 리포트 발행**<br>- 샌드박스 픽스처 셋(10-15개 세션) 기반 RAG 컨센서스 평가 및 최종 보고. | `data/evals/fixtures` & `apps/web`:<br>- 통합 예측 오차(MAE) 검증 데이터 빌드.<br>- RAG Consensus Release-Gate 최종 리포트 발행 및 제출 준비. |

---

## 4. Data/Labeling Milestone: Turning Survey Responses to Ground Truth

설문조사의 주관적 응답을 예측 가능한 **정량적 텐션 스코어 기준(Ground Truth)**으로 변환하기 위한 데이터 파이프라인 마일스톤을 다음과 같이 구체화한다.

1.  **동기화 및 보정 (Temporal Alignment & Delay Compensation):** 
    *   사용자가 영상을 시청하며 평가 장치를 조작할 때 발생하는 인지·행동적 시간 지연(약 1.5~2.5초)을 감안하여, 설문 텐션 타임스탬프를 일정 부분 앞으로 당겨 보정한다.
2.  **정규화 (Normalization):** 
    *   개인마다 기준 긴장도 범위가 다르므로, 개별 설문자의 평가 점수를 Z-score 정규화 혹은 Min-Max Scaling [0, 1] 범위로 일괄 매핑하여 이상치(outliers)의 영향을 최소화한다.
3.  **가우시안 스무딩 (Gaussian Smoothing):** 
    *   조작 시 발생하는 미세한 진동이나 급격한 단절을 방지하고 완만한 텐션의 변화 흐름을 묘사하기 위해 $1D$ Gaussian Kernel (윈도우 크기 5초 내외)을 적용해 부드러운 곡선 데이터를 산출한다.
4.  **대표값 추출 및 DB 영속화:** 
    *   정규화되고 스무딩된 개별 평가 곡선의 중앙값(Median) 혹은 평균값(Mean)을 대표 Tension Curve로 결정하고, `TensionScoreLabel` 스키마 형태로 가공해 Firestore의 `tensionLabels` 하위 컬렉션에 적재한다.

---

## 5. By 2026-08-31 실현 가능한 것 / 아닌 것 (Feasibility Assessment)

프로젝트 종료 시점인 **2026-08-31**까지 완료 가능한 범위와 불가능한 연구적/엔지니어링 경계를 솔직하게 정의한다.

### 실현 가능한 것 (Realistic)
*   **Zod 스키마 및 DB 모델 완성:** `packages/contracts` 및 `packages/db` 내부의 모든 텐션 및 플레이 메타데이터 설계.
*   **소규모 데이터 적재 및 변환 파이프라인:** 10~15개 플레이 세션에 대한 설문조사 결과 CSV 파서 및 가우시안 스무딩 파이프라인.
*   **Gemini 기반 멀티모달 비디오 청킹 및 RAG 검색 프로토타입:** 비디오 하이라이트 구간을 시각 정보로 청킹하고, 유사 레벨디자인 텍스트 가이드를 RRF와 rerank를 거쳐 추출하는 백엔드 API.
*   **예측 데모 UI:** Next.js `/search` 및 `/rag-lab` 화면 상에 저장된 mock 플레이 영상을 토대로 시간대별 텐션 변화 예측 곡선을 렌더링하고, 이 곡선의 특정 시간대를 클릭하면 RAG 근거 자료(유사 게임 유사 난이도 분석 등)를 보여주는 Citation Inspector 프로토타입 연동.

### 실현 불가능한 것 (Unrealistic)
*   **대규모 RL 플레이 영상 데이터셋 구축:** 수천 편 단위의 고용량 멀티모달 비디오 임베딩 및 인덱싱 처리(App Hosting 에뮬레이터 및 로컬 스토리지 비용/성능 한계로 인해 프로토타입 범위로 제한).
*   **실시간 웹캠 기반 생체 신호 추정 탑재:** 브라우저 웹캠을 사용해 실시간으로 유저의 텐션을 추론하고 이를 API 서버와 양방향 소켓으로 추적하는 정교한 온디바이스 생체인식 기능(8주라는 물리적 기한 내에 상용화 수준 구축 불가능).
*   **SCI-E 논문의 완전한 게재 승인:** 8주 기간 내 학술지 피어 리뷰(Peer Review) 일정상 게재 확정은 불가함. 이에 따라 최종 제출용 완성도 높은 매뉴스크립트(Manuscript Draft) 마련 및 서브미션 패키지 구성을 현실적인 최종 마일스톤으로 삼음.

---

## 6. Related pages (관련 페이지)

*   [[wiki/reports/neuro-symbolic-game-story-research-plan-2026-07-06]]
*   [[wiki/reports/funqa-rag-platform]]
*   [[wiki/concepts/neuro-symbolic-game-storytelling]]
