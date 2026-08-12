# Neuro-symbolic Game Story Research Plan 2026-07-06

본 보고서는 게임 스토리 생성, 인터랙티브 내러티브 및 RPG 대화 시스템에 대형 언어 모델(LLM)과 기호적 제어(Symbolic Control)를 결합하는 뉴로-심볼릭(Neuro-symbolic) 방법론의 2개 논문 연구 프로그램에 대한 8주 일정을 정의합니다. 이 연구는 `saas-of-funqa` 플랫폼을 RAG 및 평가 백엔드로 활용합니다.
> **문헌 검증 상태(2026-07-06 갱신):** 최초 초안의 인용을 `web_search`로 재검증하여 미확인 서지사항 1건(FDG 2025 관련)을 삭제하고 1건을 2차 출처 확인 수준으로 하향 표기했습니다. 상세 내용은 §2, §3의 "정정 사항" 각주 참고.

## Executive Goal (연구 목표)

2026년 8월 31일까지 뉴로-심볼릭 게임 스토리텔링 분야에서 SCI-E급 저널 또는 탑티어 학회 투고가 가능한 2개의 논문 초안(Manuscript Draft)과 통합 실험 패키지를 구축하는 것을 목표로 합니다.
1. **Paper A:** LLM 제안(Proposal)과 기호적 일관성 검증(Symbolic Validator) 루프를 결합하여 일관되고 플레이 가능한 인터랙티브 픽션(Interactive Fiction) 및 퀘스트 월드를 점진적으로 생성하는 프레임워크 연구.
2. **Paper B:** 지식 그래프(Knowledge Graph)와 기호적 대화 정책(Dialogue Policy)을 활용하여 세계관 규칙(Lore)을 준수하고 NPC의 일관성을 유지하는 RPG 대화 생성 시스템 연구.

---

## Literature Grounding Status (문헌 조사 및 기반 연구)

2025-2026년 최신 연구 동향을 반영하여 뉴로-심볼릭 내러티브 생성, 게임 콘텐츠 검증, 지식 그래프 기반 대화, 감성 컴퓨팅 및 텐션 모델링 분야의 문헌 기반을 확장합니다.

### 1. Neuro-symbolic LLM Narrative/Story Generation
*   **Verified Anchors (검증된 문헌):**
    *   `Large Language Models Are Neurosymbolic Reasoners` — AAAI 2024, DOI `10.1609/aaai.v38i16.29754`.
        *   LLM을 외부 기호 구조와 결합하여 추론적 한계를 극복하는 기저 연구.
*   **Unverified Leads (추가 검토 필요 리드):**
    *   `Interleaving a Symbolic Story Generator with a Neural Network-Based Large Language Model` (2026 adjacent lead).
    *   `Lost in Stories: Consistency Bugs in Long Story Generation` (2026 NLP lead).

### 2. LLM-plus-Symbolic Validation for Interactive Fiction/Game Content
*   **Verified Anchors (검증된 문헌):**
    *   `IVIE: A Neuro-symbolic Approach to Incremental and Validated Generation of Interactive Fiction Worlds` — OpenAlex 2026, arXiv:2606.13348.
        *   LLM의 창의적 내러티브 생성과 기호적 월드 상태 검증(PAYADOR 기반 제약 조건)을 통합하여 일관된 인터랙티브 픽션 월드를 생성하는 4단계 파이프라인 제시.
    *   `Symbolically Scaffolded Play: Designing Role-Sensitive Prompts for Generative NPC Dialogue` — Vanessa Figueiredo and David Elumeze, arXiv:2510.25820, 2025.
        *   LLM NPC 대화에서 일관성 유지와 즉흥적 플레이 간의 균형을 위해 퍼지 기호 스캐폴딩(fuzzy-symbolic scaffolding)을 탐구하며 역할에 따른 제약 효과를 분석.
    *   `Bringing Stories Alive: Generating Interactive Fiction Worlds` — AIIDE 2020, DOI `10.1609/aiide.v16i1.7400`.
        *   인터랙티브 픽션 월드 생성을 플레이 가능한 상태 공간(Playable State Space)의 제약 만족 문제로 정의한 고전적 벤치마크.
*   **Unverified Leads (추가 검토 필요 리드):**
    *   `Neuro-Symbolic Synergy for Interactive World Modeling (NeSyS)` (2026 adjacent lead).
    *   `NSVIF: Neuro-Symbolic Verification on Instruction Following for Game Agents` (2025 lead).

### 3. Knowledge-Graph-Grounded LLM Dialogue for Game NPCs
*   **Verified Anchors (검증된 문헌):**
    *   `NPC Mind: Knowledge Graph-Augmented Language Models for Game Characters` — P. Ammanabrolu, M. Riedl, and A. Young, Proc. AAAI Conf. Artif. Intell., vol. 39, 2025. (2026-07-06 재검증: 1차 출처 직접 확인 불가, 단 `ijetcsit.org` 게재 논문의 참고문헌 [16]에서 동일 서지사항으로 인용됨을 확인 — 2차 출처 확인 수준.)
        *   지식 그래프를 LLM과 결합하여 NPC의 대화 기억 일관성과 세계관 인식을 유도하는 메모리 모델링 연구.
    *   `Ontologically Faithful Generation of Non-Player Character Dialogues (KNUDGE)` — arXiv:2212.10618.
        *   Obsidian Entertainment `The Outer Worlds`의 실제 퀘스트 대화 데이터로 구축한 KNUDGE 벤치마크. 분기형 대화 트리가 퀘스트/엔티티 명세를 얼마나 충실히 반영하는지 검증하는 과제를 정의 — Paper B의 lore-consistency 평가 축과 직접 연관.
*   **2026-07-06 정정 사항:** 이전 초안에서 `Grounded NPC Dialogue via Retrieval-Augmented Generation (FDG 2025)`를 검증됨으로 표기했으나, 재검색 결과 해당 서지사항의 1차 출처를 확인할 수 없어 **삭제**함 (FDG 2026은 2026-08-10~14 개최 예정으로 accepted-paper 목록조차 아직 공개되지 않음). 향후 실제 FDG 2026 accepted papers 목록 공개 시 재확인 필요.
*   **Unverified Leads (추가 검토 필요 리드):**
    *   `Personalized Non-Player Characters: A Framework for Character-Consistent Dialogue Generation` (MDPI Applied Sciences, 2025).
    *   `Story2Game: Neuro-symbolic Quest and Action Code Generation for RPGs` (2026 lead).

### 4. RL/Affective-Computing Player Tension/Engagement Modeling from Gameplay Video (for FunQA cross-link)
*   **Verified Anchors (검증된 문헌):**
    *   `Do Vision Language Models Understand Human Engagement in Games?` — arXiv:2603.18480, DOI `10.48550/arXiv.2603.18480`, 2026.
        *   VLM이 게임 비디오를 통해 플레이어의 몰입도를 인지할 수 있는지 평가하며 perception-understanding gap과 GameVibe 데이터셋을 소개.
    *   `AffectGPT-R1: Leveraging RL for Open-Vocabulary Multimodal Emotion Recognition` — arXiv:2508.01318, DOI `10.48550/arXiv.2508.01318`, 2025.
        *   강화학습을 통한 감성 수치 최적화 모델로 멀티모달 비디오 피드백 루프 분석에 기여.
*   **Unverified Leads (추가 검토 필요 리드):**
    *   `LLM-Assisted Reinforcement Learning for Affective Game Adaptation` (2026 adjacent lead).

---

## 8-Week Schedule (8주 연구 일정)

마감 시한(2026년 8월 31일)에 맞추어 단일 연구자의 가용 대역폭(Bandwidth) 내에서 두 논문(Paper A & Paper B)의 프로토타이핑, 대규모 배치 실험, 어블레이션 연구, 인간 평가, 통계 분석 및 논문 작성을 소화하기 위한 병렬/교차 압축 계획입니다.

| 주차 (Week) | 일정 (Dates) | Paper A (Constraint-Audited IF) 업무 | Paper B (KG-Grounded RPG NPC Dialogue) 업무 | 공통 플랫폼 및 인프라 통합 업무 |
| :--- | :--- | :--- | :--- | :--- |
| **W1** | 2026-07-06<br>~ 07-12 | - 문헌 연구 범위 확정 및 초안 구조화<br>- IF 월드 씨드(Quest Seed) 정의 및 규칙 확정 | - NPC 프로필 및 세계관 Lore 지식 그래프 스키마 확정<br>- 대화 시나리오 정의 | - `packages/contracts` 공통 스키마 및 Zod 타입 정의<br>- `data/evals` 기본 데이터셋 패키징 |
| **W2** | 2026-07-13<br>~ 07-19 | - **[주요 포커스]** Paper A 프로토타입 개발<br>- Seed Interpreter 및 Symbolic Validator 구현<br>- Repair Loop 로직 작성 | - Paper B 지식 그래프 DB 세팅 및 초기 로딩<br>- Baseline 시스템 (LLM-only, RAG-only) 구축 | - `packages/ai` 및 `packages/db` 공통 모듈 연동<br>- 공통 평가 지표(Metric) 설계 및 로깅 파이프라인 연계 |
| **W3** | 2026-07-20<br>~ 07-26 | - Paper A Baseline 성능 테스트<br>- E1(Validity) 및 E3(Repair) 측정 준비 | - **[주요 포커스]** Paper B 프로토타입 개발<br>- Dialogue Policy Engine 및 KG Retriever 구현<br>- Response Validator 연동 | - `apps/api`에 두 실험 평가용 배치 엔드포인트 연동 |
| **W4** | 2026-07-27<br>~ 08-02 | - Paper A 자동화 배치 실험 진행<br>- Ablation (제약 조건, 리페어 루프 제거 시의 효과) 수행 | - Paper B 자동화 배치 대화 실험 진행<br>- Ablation (KG, 정책 필터 제거 시의 효과) 수행 | - 두 실험의 실행 결과 Traces 데이터베이스(`packages/db`) 영속화 및 비용/지연 시간(Cost/Latency) 분석 |
| **W5** | 2026-08-03<br>~ 08-09 | - Paper A 생성 결과물의 내러티브 다양성 및 표현력에 대한 인간 평가 수행 | - Paper B NPC 대화 자연스러움 및 캐릭터성 유지에 대한 인간 평가 수행 | - 블라인드 인간 평가 양식 설계 및 평가단 투입<br>- 평가자 간 일치도(Inter-rater agreement) 지표 분석 |
| **W6** | 2026-08-10<br>~ 08-16 | - Paper A 통계 분석 및 논문 초안 작성 시작 (Introduction, Related Work, Method) | - Paper B 통계 분석 및 논문 초안 작성 시작 (Introduction, Related Work, Method) | - 비모수 통계 검정, 카이제곱 검정, 혼합 효과 모델 적용 |
| **W7** | 2026-08-17<br>~ 08-23 | - Paper A 초안 작성 완료 (Experiments, Results, Discussion, Threats, Ethics) | - Paper B 초안 작성 완료 (Experiments, Results, Discussion, Threats, Ethics) | - 연구 다이어그램 및 실험 결과 테이블/그래프 생성<br>- LaTeX 포맷팅 및 피어 리뷰 피드백 반영 |
| **W8** | 2026-08-24<br>~ 08-31 | - Paper A 논문 최종 퇴고 및 최종 포맷팅 검증 | - Paper B 논문 최종 퇴고 및 최종 포맷팅 검증 | - 투고 타겟 저널 커버 레터 작성<br>- 실험 소스코드, 데이터셋 패키징 및 Google Drive 업로드 |

---

## By 2026-08-31 실현 가능한 것 / 아닌 것 (Feasibility Assessment)

단일 연구원의 물리적 자원과 8주의 시간 제약을 감안할 때 실현 가능한 범위와 아닌 범위를 솔직하게 분리합니다.

### 실현 가능한 것 (Realistic Outcomes)
*   **Paper A 및 Paper B 연구 논문 초안(Manuscript Draft) 완성:** 약 8~10 페이지 분량의 학술 포맷(LaTeX) 원고 완성 및 자체 피어 리뷰 완료.
*   **실험용 프로토타입 구현 및 배포:** `saas-of-funqa` 내에 모듈화된 패키지로 코드 작성 완료.
*   **자동화 평가 실험 완료:** 160개 이상의 IF 씨드 및 90개 이상의 RPG NPC 시나리오에 대한 배치 추론, 제약 조건 체크, 리페어 성공률 데이터 수집 완료.
*   **소규모 인간 평가 완료:** 연구 그룹 내부 혹은 소규모 서베이 패널(N <= 10)을 활용하여 Likert 척도로 자연스러움, 표현력 평가 수집 및 통계치 도출.
*   **투고용 패키지 준비:** 저널 투고용 커버 레터 초안 및 타겟 저널 리스트업(IEEE Transactions on Games, Applied Soft Computing 등).

### 실현 불가능한 것 (Unrealistic Outcomes)
*   **SCI-E 저널 최종 게재 승인(Acceptance):** 투고 이후 피어 리뷰 프로세스는 최소 3~9개월 소요되므로 8월 31일 이전 게재는 불가능하며, '투고 완료' 혹은 '투고 준비 상태'가 최종 현실적 목표임.
*   **대규모 대조군 인간 평가(Large-N User Study):** 외부 플레이어 수백 명을 대상으로 하는 대규모 유저 테스트 및 임베디드 실험은 8주 연구 일정 하에 예산 및 모집 기간 상 진행 불가.
*   **완전 자동화된 범용 게임 엔진 연동:** Unity, Unreal 등의 실시간 메이저 게임 엔진과의 완벽한 런타임 양방향 RPC 바인딩은 별도의 엔지니어링 작업이 필요하므로 프로토타입 검증 단계에서는 파이썬/TypeScript RAG 시뮬레이션 환경으로 제한함.

---

## Cross-link to FunQA Tension-Score Track (FunQA 연계 방향)

본 뉴로-심볼릭 연구 트랙은 플레이 영상을 멀티모달로 분석하여 사용자 텐션 스코어를 라벨링하고 예측하는 FunQA의 제품 트랙(`1-FunQAProductStagePlan`)과 다음과 같은 공통 인프라를 공유할 수 있습니다.

1.  **공통 스키마 및 규약 (`packages/contracts`):**
    *   게임플레이 상태(`WorldState`) 및 플레이어 행위(`StoryAction`) 스펙 공유.
    *   텐션 예측 결과를 대화 분기나 퀘스트 난이도 조절에 반영하기 위한 `AffectiveStateSchema` 정의.
2.  **공통 AI 검색 및 검증 모듈 (`packages/ai`):**
    *   대화 생성 RAG와 플레이어 프로필 분석을 위한 지식 검색 라이브러리 공유.
    *   VLM 기반 게임 비디오 몰입도 추론 모델(`arXiv:2603.18480` 참고)을 통해 플레이 도중 실시간 텐션 수준을 수집하고, 이를 대화 컨트롤 패킷(`DialoguePolicy`)의 감정 톤(`relationshipTone`)에 주입하여 NPC가 긴장 상태에 다르게 대응하도록 연동.
3.  **데이터베이스 공통 레이어 (`packages/db`):**
    *   게임플레이 리플레이 기록, NPC 대화 히스토리 및 예측된 플레이어 텐션 타임라인을 동일한 Firestore / RAG 데이터베이스 스토어에 구조적으로 통합하여 추적성 확보.

---

## Related Pages (관련 문서)

*   [[wiki/reports/neuro-symbolic-game-story-research-plan-2026-06-28]] (이전 12주 연구 계획 문서)
*   [[wiki/reports/paper-draft-ivie-style-validated-game-story-generation-2026-06-28]] (Paper A 초안 v0.1)
*   [[wiki/reports/paper-draft-kg-grounded-rpg-dialogue-2026-06-28]] (Paper B 초안 v0.1)
*   [[wiki/concepts/neuro-symbolic-game-storytelling]] (핵심 뉴로-심볼릭 개념 요약)
*   [[wiki/reports/funqa-tension-score-platform-stage-plan-2026-07-06]] (FunQA 텐션 스코어 플랫폼 개발 계획 리포트 - 병렬 태스크 산출물)
