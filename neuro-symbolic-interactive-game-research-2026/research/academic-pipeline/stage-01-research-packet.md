# Stage 1 Research Packet / 연구 패킷

Status: **USER APPROVED — 2026-08-12**  
Pipeline: `academic-pipeline`, full mode, very-high oversight  
As-of date: 2026-08-12

## Target / 투고 목표

- Primary journal: **IEEE Transactions on Games (ToG)**.
- Article type: full research article; systems-and-methods contribution with pilot empirical evidence.
- Submission language: English; project companion manuscript: Korean.
- Source format: IEEE Transactions LaTeX; outputs: English PDF and Korean PDF.
- Review package: double-anonymous manuscript, anonymized repository/artifact references for submission.
- Working length target: at or below ten typeset pages for the main full-paper body and references,
  with optional supplementary material. The live venue rules are rechecked immediately before submission.
- Abstract contract: 150--200 words, one self-contained paragraph; 2--5 index terms.

The venue contract is based on the live [IEEE Transactions on Games submission guidelines](https://transactions.games/submit/submission-guidelines)
and [IEEE journal authoring tools](https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/authoring-tools-and-templates/).

## Working title / 작업 제목

**TRACE-RPG: Trace-Complete Neuro-Symbolic Transaction Gates for Reliable Interactive Game Agents**

**TRACE-RPG: 신뢰 가능한 인터랙티브 게임 에이전트를 위한 추적 완전 신경-기호 트랜잭션 게이트**

## Research problem / 연구 문제

Open-ended language models can propose expressive game actions, dialogue, and adaptations, but their
outputs are not authoritative game state. The central problem is how to retain generative flexibility
while preventing invalid world transitions, unauthorized knowledge disclosure, and irreproducible
evaluation records under interactive latency constraints.

개방형 언어 모델은 표현력 있는 게임 행동·대화·적응을 제안할 수 있지만 그 출력은 권위적
게임 상태가 아니다. 핵심 문제는 생성 유연성을 유지하면서 잘못된 세계 전이, 권한 없는
지식 공개, 재현 불가능한 평가 기록을 인터랙티브 지연 제약 아래에서 방지하는 방법이다.

## Research questions / 연구 질문

- **RQ1 — Validity:** Does a symbolic transaction gate reduce illegal world transitions and NPC
  disclosure violations relative to unguarded and syntax-only constrained generation?
- **RQ2 — Recovery:** How often can bounded repair recover rejected proposals without weakening
  canonical action-policy constraints?
- **RQ3 — Cost:** What latency, token, and availability cost is introduced by retrieval, validation,
  repair, and trace persistence?
- **RQ4 — Experience:** Under matched validity, do players prefer guarded generation to scripted,
  unguarded, and retrieval-only dialogue? This remains a preregistered future human study.
- **RQ5 — Reproducibility:** Can content-addressed records and semantic replay detect corruption and
  reproduce every committed transition under a declared environment?

## Proposed contribution / 제안 기여

1. A proposer--validator--repair--commit architecture that keeps learned affect and language output
   non-authoritative until a canonical policy accepts a transition.
2. An action-policy oracle for preconditions, effects, object permissions, quest monotonicity, and
   NPC knowledge/disclosure boundaries.
3. A semantic, append-only replay format linking assignment, proposal, validation, repair history,
   final state, resource accounting, and content-integrity hashes.
4. A multitrack evaluation harness spanning world state, dialogue, affect, systems performance, and
   reproducibility, with explicit treatment-policy denominators and failure taxonomy.
5. An open, bilingual research scaffold and a staged empirical program that separates deterministic
   engineering evidence from future hosted-model and human-subject conclusions.

## Experiment intake declaration / 실험 인입 선언

The manuscript will include newly executed experiments, but at the present checkpoint only experiments
that run locally and deterministically without hosted-model credentials or human participants are
authorized as completed evidence. They may test validators, repairs, mutation resistance, replay,
failure accounting, latency of the local harness, and synthetic scenario coverage. They cannot support
claims about ten-model comparative quality, player preference, production-scale latency, or affect-model
accuracy. Those claims remain hypotheses and protocol commitments until the corresponding studies run.

## Stop conditions / 중단 조건

- No fabricated model, player, energy, cost, or latency measurement.
- No use of a preprint as the sole support for a central factual claim.
- No causal or superiority claim from deterministic unit/integration tests.
- No submission-ready label until bibliography, anonymous packaging, statistical analysis, PDF checks,
  and independent reviewer loops pass.

