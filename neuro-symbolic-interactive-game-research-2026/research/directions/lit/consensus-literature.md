# 컨센서스·앙상블 검증 문헌 (검증 완료, 2026-08-14)

13편 전부 arXiv 1차 소스 + DBLP/프로시딩 교차 확인. UNVERIFIED 0, 학회 미확정 플래그 3.

## 자기일관성·다수결

1. Wang et al. **"Self-Consistency Improves Chain of Thought Reasoning."** ICLR 2023
   (arXiv:2203.11171). GSM8K +17.9%p 등 — 단, 본 실험은 **경로 40개 표본**, 실용 무릎은
   5–10경로에서 포화. 소프트 검증의 정준 기준선이자 비용 배수의 출처.

## 다중 에이전트 토론

2. Du et al. **"Improving Factuality and Reasoning through Multiagent Debate."** ICML 2024
   (arXiv:2305.14325). 3에이전트×2라운드: 산술 67.0→81.8%, **체스 수 유효성 29.3→45.2%** —
   토론 후에도 **54.8%가 하드 무효**. 기호 게이트가 제거하는 바로 그 상한.
3. Smit et al. **"Should we be going MAD?"** ICML 2024 (PMLR v235, arXiv:2311.17371).
   토론은 자기일관성·다중 경로 앙상블을 **신뢰성 있게 능가하지 못함**; 프로토콜은 하이퍼파라미터
   취약(동의 강도 튜닝만으로 USMLE ~±15%p). 토론 예산이 자기정당화되지 않는다는 최강 근거.

## 앙상블·저지 패널

4. Wang et al. **"Mixture-of-Agents."** ICLR 2025 (arXiv:2406.04692). AlpacaEval 2.0에서
   오픈소스 앙상블 65.1% > GPT-4o 57.5% — 단 최적화 대상은 선호 승률이지 하드 유효성이 아님.
5. Verga et al. **"Replacing Judges with Juries (PoLL)."** arXiv:2404.18796 [venue 미확정 —
   COLM 오인용 주의]. 소형 모델 패널이 단일 대형 저지보다 우수하며 **7× 저렴** — "컨센서스가
   항상 비싸다"의 반례. 게이트 논거는 가격이 아니라 **보장 유형**에 서야 한다.
6. Zheng et al. **"Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena."** NeurIPS 2023
   D&B (arXiv:2306.05685). GPT-4 저지 인간 일치 ~80%가 상한; 위치·장황·자기강화 편향은
   패널 평균으로 상쇄되지 않는 계통 오차.

## 테스트타임 컴퓨트·검증기

7. Snell et al. ICLR 2025 Oral (arXiv:2408.03314) — FLOPs 매칭에서 14× 소형 모델 역전은
   기저 성공률이 있는 구간에서만: **테스트타임 컴퓨트는 범주적 하드 무효를 수리하지 못한다**.
8. Chen et al. **"Are More LLM Calls All You Need?"** NeurIPS 2024 (arXiv:2403.02419;
   카메라레디 제목 "…Compound AI Systems"). Vote/Filter-Vote **비단조**, 최적 호출 1–30 구간.
9. Cobbe et al. **"Training Verifiers."** arXiv:2110.14168 [venue 없음]. 6B+검증기+100표본 ≈
   30× 파라미터 — 게이트는 이 교환에서 표본 항을 1로 접는다.
10. Lightman et al. **"Let's Verify Step by Step."** ICLR 2024 (arXiv:2305.20050). PRM 78%
    (MATH 부분집합); 비용은 호출이 아니라 **사전 감독 80만 레이블** — 기호 규칙 저작과 가장
    공정한 비용 비교 대상.
11. Brown et al. **"Large Language Monkeys."** arXiv:2407.21787 [DBLP상 CoRR only].
    coverage 로그선형 — 단 자동 검증기 없는 도메인에서 다수결·RM은 수백 표본에서 정체.

## 기호 검증 직접 비교

12. Pan et al. **"Logic-LM."** Findings of EMNLP 2023 (arXiv:2305.12295). 5데이터셋 평균
    표준 프롬프트 대비 +39.2%p, CoT 대비 +18.4%p — **표본 배수 없이** LLM 1회 번역 +
    결정론 솔버 + 오류 메시지 수리. 우리 아키텍처의 최근접 출판 유사체.
13. Ye et al. **"SatLM."** NeurIPS 2023 (arXiv:2305.09656). 선언적 명세 + 정리증명기 —
    "파싱된 명세에 대한 정답 보장". 컨센서스의 확률적 일치와 **범주적으로 다른 조건부 보장**;
    잔여 오차는 NL→기호 번역 단계로 국소화.

## 두 갈래 핵심 논지

- **비용 상한은 구조적**: 다수결 정확도는 호출 수에 비단조(Chen)이고, 자동 검증기 부재 시
  선택 정확도는 정체(Brown) — 컨센서스는 어떤 가격에도 임의의 하드 유효성까지 구매 불가.
- **정확도 축은 보장 유형으로 갈라짐**: 최고 소프트 검증 ~80% 인간 일치(Zheng), 토론 후에도
  체스 무효 54.8%(Du) vs SatLM의 명세 상대 보장 — 게이트는 오차를 번역 단계로 모은다.
