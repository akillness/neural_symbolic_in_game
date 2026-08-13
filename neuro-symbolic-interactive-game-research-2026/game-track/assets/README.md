# The Sealed Lighthouse Concept Resource Pack / 봉인된 등대 컨셉 리소스 팩

This folder contains four AI-generated concept surfaces for the experimental game. They were
created offline with `god-tibo-imagen` after dry-run validation. They are not production-ready game
assets and are never generated during an experiment.

이 폴더에는 실험 게임용 AI 생성 컨셉 리소스 4종이 있다. 모든 이미지는 dry-run 검증 후
`god-tibo-imagen`으로 오프라인 생성되었다. 프로덕션 완성 자산이 아니며 실험 런타임에서는
생성하지 않는다.

| ID | Surface | Role | Current status |
|---|---|---|---|
| SL-C01 | Harbor/lighthouse environment | visual style anchor | accepted concept |
| SL-C02 | Captain Mira exploration sheet | character direction | accepted concept |
| SL-C03 | Investigation UI | layout and separation direction | accepted concept, untested UI |
| SL-C04 | Evidence icons | icon-language direction | accepted v2 concept; requires cropping/semantic testing |

The first SL-C04 generation failed independent prompt-compliance review because it rendered a key
and a seal-animal motif. That byte stream is retained under `concepts/rejected/` with a rejection
reason; the active v2 sheet was regenerated from a canonical-visible-only prompt and visually
inspected again. This is a curation decision, not evidence of semantic usability.

## Experimental boundary / 실험 경계

- The primary confirmatory track uses only structured text and canonical state.
- A frozen checksum-locked derivative pack may be used by the separately labelled secondary VLM/UI
  track.
- Visual assets cannot change policy, oracle, action availability, or canonical state.
- Every input pack must cite `concepts/asset-manifest.json` and the selected files' SHA-256 values.
- Image generation quality, visual inspection, or a checksum is not evidence of originality,
  accessibility, player benefit, or experimental efficacy.

1차 확증 트랙은 구조화 텍스트와 정식 상태만 사용한다. 별도 2차 VLM/UI 트랙만 동결된 파생
이미지 팩을 사용할 수 있다. 시각 자산은 정책·oracle·행동 가능성·정식 상태를 변경할 수 없다.

## Reproducibility and disclosure / 재현성과 공개

Exact prompts are under `concepts/prompts/`; each image has adjacent `.provenance.json`. The backend
is undocumented and may change, so reproduction means preserving the actual image bytes and hashes,
not assuming a future regeneration will be pixel-identical. Publication requires an explicit
AI-generated-content statement and human rights/style review.

정확한 프롬프트는 `concepts/prompts/`, 개별 생성 기록은 인접 `.provenance.json`에 있다. 비공개
백엔드 계약은 변경될 수 있으므로 재현성 기준은 재생성의 픽셀 동일성이 아니라 현재 파일과
해시의 보존이다.
