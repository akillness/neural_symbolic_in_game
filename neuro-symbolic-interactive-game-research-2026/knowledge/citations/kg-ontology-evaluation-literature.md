---
type: Citation Set
title: KG·온톨로지 제안 평가 1차 출처

description: Typed graph constraint, ranking, precision-recall, calibration, competency question, keep/discard 규율의 1차·공식 출처.
tags: [citations, kg, ontology, evaluation, verified]
timestamp: 2026-08-30T00:00:00Z
---

# Verified sources

- W3C, *Shapes Constraint Language (SHACL)*, Recommendation, 2017:
  <https://www.w3.org/TR/shacl/>.
- W3C, *OWL 2 Web Ontology Language Profiles*, Recommendation, 2012:
  <https://www.w3.org/TR/owl2-profiles/>.
- Davis and Goadrich, *The Relationship Between Precision-Recall and ROC Curves*, ICML 2006,
  DOI `10.1145/1143844.1143874`.
- Brier, *Verification of Forecasts Expressed in Terms of Probability*, 1950,
  DOI `10.1175/1520-0493(1950)078<0001:VOFEIT>2.0.CO;2`.
- Bordes et al., *Translating Embeddings for Modeling Multi-relational Data*, NeurIPS 2013,
  HAL `hal-00920777`.
- Karpathy, *autoresearch/program.md*, official repository contract:
  <https://github.com/karpathy/autoresearch/blob/master/program.md>.

# Use boundary

현재 구현은 SHACL processor나 OWL reasoner가 아니다. SHACL/OWL 문헌은 향후 interchange와
constraint vocabulary의 경계를 정할 뿐 적합성 주장을 허용하지 않는다. MRR은 realistic tie
rank를 명시하고, Brier score는 bounded score의 진단값으로만 쓴다. 작성형 closed-world
negative로 얻은 precision/recall은 다른 prevalence나 open-world 데이터에 일반화하지 않는다.
Autoresearch의 고정 evaluator, baseline-first, keep/discard 원칙만 오프라인 전략 검색에
이식하며 5분 GPU 학습 계약을 이 시뮬레이터가 수행한다고 주장하지 않는다.

# Relations

- 평가 지표: [KG 링크 제안 품질](/metrics/kg-proposal-quality.md)
- 실행 규율: [KG 온톨로지 제안 시뮬레이션](/protocols/kg-ontology-simulation.md)
- 타입 계약: [TRACE-RPG application ontology](/concepts/trace-rpg-application-ontology.md)
