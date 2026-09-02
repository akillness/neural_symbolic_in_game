# Neural-Symbolic Interactive Game Research 2026

[![validate](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml/badge.svg)](https://github.com/akillness/neural_symbolic_in_game/actions/workflows/validate.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Knowledge](https://img.shields.io/badge/knowledge-llm--wiki%20%2B%20Graphify-6f42c1)](./llm-wiki/index.md)
[![Research status](https://img.shields.io/badge/status-experimental-orange)](./neuro-symbolic-interactive-game-research-2026/README.en.md)

TRACE-RPG는 생성 모델의 제안을 정식 게임 상태와 분리하고, 외부 행동 정책과 결정론적 검증을 통과한 이벤트만 커밋하는 뉴로-심볼릭 연구 하네스입니다. 이 저장소에는 이중언어 IEEE 원고 source, 동결 오프라인 적합성 파일럿, `pilot-only` 단일 모델 RQ2 스크리닝, `simulation-only` KG/온톨로지 레인, Godot 4.7.1 Web 플레이어블이 함께 있습니다. 다중 모델 확증 연구, 인간 연구, 감정·런타임 검색 효능은 아직 미실행입니다.

TRACE-RPG separates generated proposals from canonical game state and commits only events accepted by an external action policy and deterministic validation. The repository contains bilingual IEEE sources, a frozen offline conformance pilot, a `pilot-only` single-model RQ2 screen, a `simulation-only` KG/ontology lane, and a Godot 4.7.1 Web playable. Confirmatory multi-model, human, affect, and runtime-retrieval efficacy studies remain unexecuted.

| Start here | Description |
|---|---|
| [한국어 안내](./neuro-symbolic-interactive-game-research-2026/README.ko.md) | 연구 질문, 구조, 실행 순서 |
| [English guide](./neuro-symbolic-interactive-game-research-2026/README.en.md) | Research questions, architecture, execution |
| [정식 한국어 논문 source](./neuro-symbolic-interactive-game-research-2026/paper/latex/ko/main.tex) | Current TRACE-RPG manuscript source |
| [Authoritative English paper source](./neuro-symbolic-interactive-game-research-2026/paper/latex/en/main.tex) | Current TRACE-RPG manuscript source |
| [Public Web playable](https://sealed-lighthouse-trace-rpg.vercel.app) | Current production alias |
| [Current gameplay recording](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/trace-rpg-gameplay.mp4) | 63.433 s H.264 MP4 of the scripted golden-path route (Godot Movie Maker, 2026-09-02); [GIF](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/golden-path.gif) |
| [Project knowledge index](./llm-wiki/index.md) | Persistent sources, concepts, reports, and graph |

## 완료 상태 / Completion status

| 영역 / Area | 상태 / Status | 근거 / Evidence |
|---|---|---|
| 구현 / Implementation | **현재 적합성 범위 완료 / Done for current conformance scope** | pytest 181 passed, 81 subtests; unittest 138 passed; Godot 4/4 fixtures and 52/52 combined checks; scripted golden-path recording |
| 학술 파이프라인 / Academic pipeline | **저장소 단계 완료 / Repository stages complete** | Stages 1–10, including final bilingual PDF rebuild and format checks, are complete; efficacy studies and submission remain separate |
| 논문 / Paper | **source·PDF 최신 / Sources and PDFs current** | Bilingual IEEE sources and 8-page PDFs, 55 link-audited references (46 VERIFIED + 9 PREPRINT), live-screening and KG-simulation addenda; paper checks pass |
| 재현성 / Reproducibility | **동결 패킷 완료 / Frozen packet complete** | 38/38 artifacts, 22/22 inputs, 121 provenance rows recompute from the guided-repair release packet |
| 라이브 스크리닝 / Live screening | **`pilot-only`** | `C-PILOT-007/008`; guided 5/5 vs blind 0/5 only in one constructed repairable regime |
| **확증 실험 / Confirmatory experiments** | **미완료 / NOT DONE** | `C-RESULT-001`–`005` = `TODO-RESULT`, 5 of 21 claims with no promotion-qualifying evidence |
| 투고 / Submission | **미진행 / Not started** | No journal decision, reviewer archive, or DOI deposit |

현재 적합성 주장을 위한 구현은 완료됐지만 확증 실험은 완료되지 않았습니다. 단일 모델 라이브
스크리닝은 제한된 mechanism evidence일 뿐 `C-RESULT-*`를 승격하지 않습니다. 인간 연구,
감정·런타임 검색·메모리 효능, 대표성 있는 엔진 성능 연구도 미실행입니다.

Implementation for the current conformance claims is complete, but the confirmatory experiments are
not. The single-model live screen is bounded mechanism evidence and promotes no `C-RESULT-*` claim.
Human, affect, runtime-retrieval, memory-efficacy, and representative engine-performance studies
remain unexecuted.

상세 표(실험 설계 · 논문 요약 · 주장 원장) / Detailed tables:
[한국어](./neuro-symbolic-interactive-game-research-2026/README.ko.md#한눈에-보기) ·
[English](./neuro-symbolic-interactive-game-research-2026/README.en.md#at-a-glance)

## System at a glance

![Trust boundary: learned proposal, symbolic authority](./neuro-symbolic-interactive-game-research-2026/visuals/system-architecture.svg)

제안은 학습 모델이, 커밋 권한은 결정론적 게이트가 가집니다. 검색·메모리·감정 추정은 제안 컨텍스트일 뿐 정식 상태를 바꿀 수 없습니다.
A learned model proposes; only the deterministic gate commits. Retrieval, memory, and affect are proposal context and can never mutate canonical state.

![One transaction: parse, validate, bounded repair, defensive check, commit](./neuro-symbolic-interactive-game-research-2026/visuals/commit-transaction.svg)

## What the numbers actually say

첫 그림은 동결된 **Stage 4 오프라인** 파일럿만, 둘째 그림은 전체 주장 원장을 보여 줍니다.
라이브 스크리닝은 별도 패킷이며 첫 그림의 분모에 섞이지 않습니다. 두 SVG는 원본에서 직접
생성되고 CI가 재생성 결과와 커밋된 파일의 일치를 강제합니다.

The first figure covers only the frozen **Stage 4 offline** pilot; the second covers the complete
claim ledger. Live screening remains a separate packet and never enters the first figure's
denominators. Both SVGs are generated from source data, and CI enforces byte-stable regeneration.

![Every Stage 4 offline-pilot number, generated from the frozen artifact](./neuro-symbolic-interactive-game-research-2026/visuals/pilot-evidence.svg)

![Claim ledger status](./neuro-symbolic-interactive-game-research-2026/visuals/claim-status.svg)

첫 그림의 분모는 전부 저자가 설계한 결정론적 사례입니다. 효능 주장 `C-RESULT-001`–`005`는
승격 가능한 확증 근거가 없는 `TODO-RESULT`입니다.
Every denominator in the first figure is an authored deterministic case. The efficacy claims
`C-RESULT-001`–`005` remain `TODO-RESULT` with no promotion-qualifying confirmatory evidence.

![Academic pipeline status](./neuro-symbolic-interactive-game-research-2026/visuals/research-workflow.svg)

The academic pipeline has actioned the user-accepted direction from a simulated IEEE Transactions
on Games Major Revision review. This is an internal review exercise, not a journal decision or
paper acceptance; confirmatory efficacy claims remain blocked.

![Planned confirmatory design — no result in this repository comes from this matrix](./neuro-symbolic-interactive-game-research-2026/visuals/confirmatory-design.svg)

Regenerate all six visuals with `uv run python scripts/generate_readme_visuals.py`.

## Cycle 3 playable engineering snapshot / 플레이어블 엔지니어링 스냅샷

*The Sealed Lighthouse / 봉인된 등대* now has a public-safe Godot 4.7.1 playable presentation:
third-person harbor exploration, proposal-gated interactions, responsive ledger UI, reduced motion,
pooled procedural VFX, and gesture-gated locally generated audio. The player restores the
harbor-side signal and earns the tide route while the offshore lighthouse remains sealed.

| `SL-PLAY-EVAL-001` row | Checks | Result |
|---|---:|---|
| Canonical fixture | `10/10` | PASS |
| Duplicate-event fixture | `10/10` | PASS |
| Timeout fixture | `10/10` | PASS |
| Corrupt-save fixture | `10/10` | PASS |
| Presentation invariants | `9/9` | PASS |
| **Combined** | **`49/49`** | **PASS** |
| Archetype balance probe | `SL-BALANCE-PROBE-001` 5/5 | PASS |

All `4/4` authored fixtures reached the exact terminal SHA-256
`4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892`. See the
[full bilingual-friendly evaluation matrix](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/evaluation-matrix.md)
and [machine-readable JSON](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/evaluation-matrix.json).

| Arrival / 도착 | Refusal / 보류 |
|---|---|
| ![Cycle 3 public-safe arrival](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/arrival.png) | ![Cycle 3 public-safe refusal](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/refusal.png) |
| Authorized hint / 승인 단서 | Ending / 항로 획득 |
| ![Cycle 3 public-safe authorized hint](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/authorized_hint.png) | ![Cycle 3 public-safe ending](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/ending.png) |

These are latest **engineering working captures**, not the immutable Cycle 2 research packet.
Generated candidates listed in `game-track/assets/concepts/public-exclusion.json` are excluded from
Web and `--public-safe`. The public artifact uses the curated UI lane and validated tracked
Higgsfield player with `Idle`/`Casual_Walk` over the procedural world, VFX, and audio fallback.

**Claim boundary / 주장 경계:** fixture and presentation-invariant conformance only. G4,
usability, immersion, affect, player efficacy, and model efficacy are **UNASSESSED**. G6 remains
`FIX` pending production save/reload, current mobile verification, human pointer/audio confirmation,
warmed-frame/input measurements, a 30-minute soak, and rollback evidence.

```bash
cd neuro-symbolic-interactive-game-research-2026
./scripts/build_godot_web.sh
python3 -m http.server 4173 --directory game-track/web/public
```

Deployment / 배포: **[play the public-safe Web build](https://sealed-lighthouse-trace-rpg.vercel.app)**
(Vercel `dpl_Auzz4gjVUcgDcL45EjcRG2HVyoCW`, `READY`). Current gameplay / 현재 플레이 영상:
**[63.433 s H.264 MP4](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/trace-rpg-gameplay.mp4)** · **[GIF](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/golden-path.gif)**
(`1280×720`, 30 fps, 5,662,128 bytes, SHA-256
`aa374c5aa9d03e0ab2822b83638e4c6645c7c9fda6c07e858051254c244b7044`).
The current production artifact serves 10 runtime files with `200`; `vercel.json` is consumed as
deployment configuration and correctly returns `404`. The current desktop smoke completed start →
in-game → Field Guide with zero console or page errors. Current 390×844 mobile verification and
pointer lock remain open; automation denial is not itself proof of a defect. / 현재 모바일과 포인터
잠금은 **미검증**이며 사람 확인이 남아 있다.

Retained 2026-08-21 layout captures below are historical and do not verify the current deployment:

| Historical desktop / 과거 데스크톱 | Historical narrow layout / 과거 협폭 |
|---|---|
| ![Historical Vercel desktop in-game smoke](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-in-game.png) | ![Historical Vercel 390 by 844 in-game smoke](./neuro-symbolic-interactive-game-research-2026/game-track/godot/docs/latest/vercel-mobile-in-game.png) |

## Quick validation

```bash
cd neuro-symbolic-interactive-game-research-2026
uv sync --extra research --extra dev
uv run python -m unittest discover -s tests -v
uv run python scripts/validate_project.py
uv run python scripts/generate_readme_visuals.py
```

The current package is a research scaffold, not a claim that model experiments have already run. Empirical values remain explicitly marked `TODO-RESULT` until trace-backed runs pass the release gates.
