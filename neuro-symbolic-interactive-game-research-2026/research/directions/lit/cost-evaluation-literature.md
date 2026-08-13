# 비용 인지·예산 매칭 평가 문헌 (검증 완료, 2026-08-14)

딥리서치 에이전트가 arXiv 초록·공식 프로시딩/저널 레코드 대조로 검증한 14편.
UNVERIFIED 플래그는 학회/저널 미확정(프리프린트)을 뜻하며 인용 시 arXiv로 표기한다.

## 비용 인지 평가 프레임워크

1. Erol, El, Suzgun, Yuksekgonul, Zou. **"Cost-of-Pass: An Economic Framework for Evaluating
   Language Models."** ICLR 2026 (arXiv:2504.13359). cost-of-pass = 정답 1건 획득의 기대 비용;
   frontier cost-of-pass는 수개월마다 절반으로 하락; majority voting·self-refinement 등
   inference-time 기법은 "미미한 이득으로 비용을 정당화하기 어렵다" — 우리 H5의 귀무가설.
   (ICLR 2026 판정은 OpenReview PDF 헤더 기반 — 부분 검증)
2. Chen, Zaharia, Zou. **"FrugalGPT."** TMLR 12/2024 (arXiv:2305.05176). GPT-4 성능을 최대
   98% 비용 절감으로 매칭, 동일 비용에서 +4% 정확도. iso-accuracy와 iso-cost는 별개 비교 축.
3. Ong et al. **"RouteLLM: Learning to Route LLMs from Preference Data."** ICLR 2025
   (arXiv:2406.18665). GPT-4 성능 95% 유지에 비용 >85%(MT-Bench) 절감, 강모델 호출률 14% —
   "품질 x% @ 비용 y% + 에스컬레이션 비율" 보고 관례의 출처.

## 예산 매칭 방법론

4. Snell, Lee, Xu, Kumar. **"Scaling LLM Test-Time Compute Optimally…"** ICLR 2025 Oral
   (arXiv:2408.03314). FLOPs 매칭 비교에서 소형 모델+테스트타임 컴퓨트가 14× 대형 모델을
   능가(일부 난이도 구간). 난이도 적응 배분이 best-of-N 대비 >4× 효율 — 예산 고정 후 배분만
   달리하는 우리 설계의 원형.
5. Chen et al. **"Are More LM Calls All You Need?"** NeurIPS 2024 (arXiv:2403.02419).
   Vote/Filter-Vote 성능은 호출 수에 **비단조** — 상승 후 하락. 혼합 난이도에서 다수결이 쉬운
   항목을 돕고 어려운 항목을 해친다. **호출 4회 상한과 K=3의 가장 강한 단일 근거**이자
   난이도 층화 보고의 근거.
6. Brown et al. **"Large Language Monkeys."** ICLR 2025 (arXiv:2407.21787). coverage는 표본
   수에 로그선형(SWE-bench Lite 15.9%@1 → 56%@250) — 단 선택기(verifier)가 있어야 실현.
   coverage@K 대 post-gate accuracy@K 분해의 출처.
7. Stroebl, Kapoor, Narayanan. **"The Limits of Inference Scaling Through Resampling."**
   arXiv:2411.17501 [UNVERIFIED venue]. 검증기 위양성률이 0이 아니면 재표본으로 넘을 수 없는
   정확도 상한 존재, 최적 시도 수는 대개 10 미만 — **게이트 위양성률을 정확도 옆에 보고해야
   하는 이유**.
8. Hoffmann et al. **"Training Compute-Optimal Large Language Models"** (Chinchilla).
   NeurIPS 2022 (arXiv:2203.15556). 동일 FLOP 예산 비교(isoFLOP)가 인과적 구조 주장을
   허가한다는 분야 표준 선례.

## 평가 엄밀성·다중 지표

9. Kapoor, Stroebl et al. **"AI Agents That Matter."** arXiv:2407.01502 [UNVERIFIED venue].
   HumanEval/GPT-4: 단순 재시도 93.2%@$2.45가 LATS 88.0%@$134.50을 Pareto 지배 —
   "비용 통제 없는 정확도 승리는 방법 우월의 근거가 아니다". Pareto 곡선 보고 관례 채택.
10. Dehghani et al. **"The Efficiency Misnomer."** ICLR 2022 (arXiv:2110.12894). 단일 비용
    지표는 순위를 뒤집을 수 있다 — 비용을 벡터(토큰·호출·지연·$)로 보고할 근거.
11. Liang et al. **"HELM."** TMLR 2023 (arXiv:2211.09110). 효율을 본 벤치마크 표에 포함;
    idealized vs denoised 추론 런타임 구분.
12. Narayanan et al. **"Cheaply Estimating Inference Efficiency Metrics…"** NeurIPS 2023
    (arXiv:2305.02440). 호스티드 API 원시 지연은 공급자 간 비교 불가 — idealized runtime 보정.

## 통계 실무

13. Miller. **"Adding Error Bars to Evals."** arXiv:2411.00640 [UNVERIFIED venue].
    클러스터 표준오차 + 쌍대 분석 + 검정력 계획 — 시나리오 내 다중 이벤트가 중첩된 우리
    설계의 기본 레시피.
14. Agarwal et al. **"Deep RL at the Edge of the Statistical Precipice."** NeurIPS 2021
    (기존 S31). IQM·층화 부트스트랩·performance profile — 소수 실행 예산에서의 정직한 구간.
    보조: Bouthillier et al. "Accounting for Variance in ML Benchmarks," MLSys 2021
    (arXiv:2103.03098) — 모든 무작위 원천을 함께 랜덤화해야 CI가 낙관적이지 않다.

## 설계 결정 ↔ 근거 매핑

| 설계 결정 | 1차 근거 |
|---|---|
| arm 간 예산 고정(최대 4호출) 후 비교 | Hoffmann 2022 · Snell 2025 |
| K 확장 대신 낮은 호출 상한 | Chen 2024(비단조) · Stroebl(최적 <10) |
| 정확도 단독이 아닌 Pareto 보고 | Kapoor 2024 · Cost-of-Pass · FrugalGPT |
| 비용 벡터 보고(토큰/호출/지연/$) | Dehghani 2022 · HELM · Narayanan 2023 |
| 게이트 에스컬레이션 비율 보고 | RouteLLM |
| 게이트 위양성률 = 컨센서스 이득의 상한 | Stroebl · Brown 2025 |
| 쌍대·클러스터·검정력 계획 통계 | Miller 2024 |
| 소수 실행 강건 집계(IQM·부트스트랩) | Agarwal 2021 · Bouthillier 2021 |
