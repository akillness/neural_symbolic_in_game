# 뉴로심볼릭·KG 내러티브 검증 문헌 (검증 완료, 2026-08-14)

전 항목 ACL Anthology·arXiv·AAAI OJS·NeurIPS 프로시딩 1차 레코드 대조. UNVERIFIED 0,
프리프린트 플래그 2 (GraphRAG, GraphCheck).

## KG 근거 내러티브·대화

1. Weir et al. **"Ontologically Faithful Generation of NPC Dialogues" (KNUDGE).** EMNLP 2024
   (arXiv:2212.10618). Outer Worlds 45퀘스트 159대화트리; 최고 ICL 모델 non-violation 3.97/4
   (골드 동급) — **비위반을 유창성과 분리 채점**하는 우리 분리의 선례.
2. Buongiorno et al. **"PANGeA."** AIIDE 2024 (DOI 10.1609/aiide.v20i1.31876). 검증 계층
   활성화로 Llama-3 8B **28%→98%**, GPT-4 71%→99% — **검증 계층이 모델 스케일을 이긴다**는
   최강 단일 수치.
3. Ashby et al. **"Personalized Quest and Dialogue Generation in RPGs."** CHI 2023
   (DOI 10.1145/3544548.3581441; arXiv 없음). Neo4j 타입 트리플 순회가 콘텐츠 승인 경로;
   응답성은 KG 승(169:159), 만족도는 수제 승(197:125) — 근거는 참조 유효성을 사고 서사
   품질은 별도.

## 뉴로심볼릭 솔버·검증기

4. Pan et al. **Logic-LM.** Findings EMNLP 2023 — CoT 대비 +18.4%p (consensus 문헌과 공유).
5. Olausson et al. **"LINC."** EMNLP 2023 (arXiv:2310.15164). ProofWriter 98.3%(GPT-4);
   단 FOLIO/GPT-4에서 CoT에 밀림(72.5 vs 75.3, 비유의) — **상보적 실패 모드**가 하이브리드
   (H5b/H5c) 설계의 직접 근거.
6. Xu et al. **"SymbCoT."** ACL 2024 (arXiv:2405.18357). GPT-4 CoT 대비 +8.85~+17.75%p;
   검증기가 번역 충실성과 단계 적법성을 **양면 검사** — 내러티브 게이트의 이중 의무와 동형.

## 그래프 검색·기억

7. Edge et al. **"GraphRAG."** arXiv:2404.16130 [프리프린트]. 커뮤니티 요약으로 토큰 >97% 절감.
8. He et al. **"G-Retriever."** NeurIPS 2024 (arXiv:2402.07630). **유효 엣지 12%→76%**,
   완전 유효 그래프 8%→62%, 환각 54% 감소 — 그래프 구조 자체를 유효성 지표로 측정한
   최고 계측 결과. "타입 관계 = 검사 가능한 술어"의 실증형.
9. Gutiérrez et al. **"HippoRAG."** NeurIPS 2024. 반복 검색 대비 **10–20× 저렴, 6–13× 고속**
   — 인터랙티브 지연에서 영속 KG 기억의 비용 논거.

## 제약 디코딩

10. Scholak et al. **"PICARD."** EMNLP 2021. 실행 실패 **12%→2%** — 사후 필터가 아닌
    디코딩 중 거부의 가치.
11. Geng et al. **"Grammar-Constrained Decoding."** EMNLP 2023 (arXiv:2305.13971).
    입력 의존 문법으로 유효 파스 트리 64.2%→**100%** — 현재 세계 상태에서 술어를 끌어오는
    validator의 형식적 유사체.

## 내러티브 계획·중재·승인

12. Ware & Siler. **"Sabre."** AIIDE 2021 (DOI 10.1609/aiide.v17i1.18896; IEEE ToG 아님 —
    ToG는 Siler & Ware 2022 탐색 전략 논문). 신념 전용 절제가 **무효 플랜 110개를 수용하며
    유효 해 0개 회복** — 제약 계층은 사후 필터가 아니라 해공간의 구성 요소.
13. Robertson & Young 내러티브 중재 — intervention/accommodation 2분기 수리 정책 어휘.

## 인터랙티브 픽션 세계 생성

14. Vaucher et al. **"IVIE."** ICCC'26 (arXiv:2606.13348). 목표 완주 Generate 100% vs
    Inspiration 50%; 파라미터 일치 81.25%. **정직한 반례**: 검증 전 단계를 통과하고도
    구조적으로 불가능한 목표 2건(아이템에 Location 미배정) — *validator는 인코딩한 술어만
    강제한다*, 스키마 커버리지 공백 = 조용한 정확성 공백. 우리 의미 오라클·H5b의 존재 이유.
15. TextWorld (IJCAI 2018 워크숍) · ScienceWorld (EMNLP 2022) — 엔진이 곧 validator인
    평가 기질, 정답 적법성 계산 가능.

## 정량 척추 4수

PANGeA 28→98% · G-Retriever 유효 엣지 12→76% · PICARD 무효 12→2% · Sabre 절제의
무효 110 수용/유효 0 회복 — 그리고 IVIE의 스키마 공백 반례가 주장의 정직한 경계.
