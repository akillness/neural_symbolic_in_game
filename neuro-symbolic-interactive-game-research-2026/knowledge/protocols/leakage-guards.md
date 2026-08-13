---
type: Protocol
title: 누출 방지 가드
description: 템플릿 결합 단위 분할·개발 fixture 제외·fingerprint 이동·단독 판정 금지·전면 해시의 5중 가드.
tags: [leakage, holdout]
timestamp: 2026-08-14T00:00:00Z
---

# Schema

1. (world_template, quest_motif, npc_identity, relation_motif) 단위 동결 분할
2. SL-DEV-001(Brinewake·Mira·신호 렌즈·근접 의역) Stage 2 제외
3. 정규화 그래프·퀘스트 오토마타 fingerprint — 근접 중복은 unblinding 전 한쪽으로 이동
4. 생성 모델 계열 단독 판정 금지 · 생성 이미지가 정답 제공 금지
5. 프롬프트·fixture·오라클·모델 revision·이미지 팩·컨트롤러/게임 빌드 해시

# Relations

- [Stage 2](/experiments/stage-2-confirmatory.md) · [골드 격리](/oracles/gold-isolation.md)
