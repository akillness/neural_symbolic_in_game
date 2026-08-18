---
type: Engine Evidence
title: Codex OAuth 소프트 제안 채널 (엔지니어링)
description: 엔진 밖 Python CLI로 실행되는 소프트 제안 채널 — 봉투 계약 검증에 공개-정책 렉시컬 스크린을 더한 논문 외 구성요소.
tags: [llm, soft-proposal, not-paper-evidence]
timestamp: 2026-08-18T00:00:00Z
---

# Overview

채널은 Godot 런타임 밖에 산다. `scripts/codex_oauth_llm.py`가 `codex` CLI를 격리 실행해
`game-track/schemas/codex-oauth-soft-proposal.schema.json` 봉투를 받고,
`validate_proposal`이 그 봉투가 권한 없는 후보임을 확인한다
(`status=candidate`, `authorization_effect=none`, `canonical_state_mutated=false`,
`hard_validation_required=true`).

`scripts/soft_proposal_policy.py`는 봉투가 아니라 *내용*을 본다.
`model_visible_projection`이 프롬프트에 노출 가능한
사실 집합을 만들어 봉인 fact ID가 요청에 아예 실리지 않게 하고, `screen_response`가 회신에
봉인·단계 미달 식별자가 표면화됐는지 표시한다. [OBSERVED — 9개 계약 테스트]

경계: 스크린은 렉시컬이므로 값싼 사전 필터일 뿐 의미 오라클이 아니다. 식별자를 부르지 않고
비밀을 흘리는 의역은 잡지 못하며, 그 판정은 SL-ORACLE-001의 블라인드 의미 annotation 몫이다.
깨끗한 스크린은 "금지 식별자가 표면화되지 않았다"는 뜻이지 "의미상 안전하다"가 아니다.

엔진 쪽 금지: `tests/test_godot_web_release.py`가 `scripts/game3d/llm/`, 백엔드 문자열,
컨트롤러·UI의 채널 훅을 거부한다. 사설 백엔드는 게임 런타임 의존이 될 수 없다.

# Relations

- arm 대응: [A4 structured_repair](/experiments/controller-arms.md) ·
  격리 원칙: [골드 격리](/oracles/gold-isolation.md)
- 의미 판정은 별도 계층: [의미 오라클](/oracles/semantic-oracle.md)
- 논문 증거 아님: [claim boundary](/concepts/claim-boundary.md)
