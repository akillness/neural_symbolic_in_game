---
type: Runbook
title: OKF 번들 구조 린트
description: type·title·description 필수 필드와 frontmatter 닫힘을 검사한다.
tags: [okf, lint]
timestamp: 2026-08-14T00:00:00Z
---

# Steps

1. `python3 scripts/validate_okf_bundle.py knowledge/` — frontmatter와 링크 오류 0.
2. `python3 scripts/export_okf_graph.py --check` — source hash를 포함한 typed OKF export가 최신.
3. `python3 scripts/run_kg_ontology_simulation.py --check` — ontology/domain/range/CQ/claim boundary와
   JSON·Markdown·TSV·SVG·TeX byte가 최신이고 임시 SQLite integrity/FK가 통과.

세 단계가 모두 통과해야 배포 가능하다.
