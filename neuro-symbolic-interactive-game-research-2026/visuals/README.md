# 편집 가능한 시각 자료 계약 / Editable Visual Asset Contract

## 한국어 정본

이 디렉터리의 `source-manifest.json`은 논문, README, 연구 방향 문서에 쓰이는 표와 그림을 렌더 결과, 편집 원본, 생성기, 데이터 원천에 연결한다. 새 표나 그림은 이 계약을 통과하기 전까지 인용 가능한 산출물이 아니다.

### 1. 정본 형식

- 다이어그램과 차트의 편집 정본은 UTF-8 SVG와 이를 재생성하는 Python 코드다.
- 데이터 기반 차트는 SVG와 함께 CSV, JSON 또는 TSV 원자료를 보관한다.
- 논문 표의 편집 정본은 UTF-8 LaTeX다. 데이터 기반 표는 생성기와 CSV 또는 JSON을 함께 보관한다.
- 논문 그림의 PDF와 PNG는 같은 stem의 SVG 옆에 둔다. PDF는 논문 삽입용 벡터 렌더이고 PNG는 빠른 미리보기용 파생본이다.
- 파생 PDF, PNG 또는 생성된 TeX를 직접 수정하지 않는다. 생성기 또는 정본 데이터를 수정한 뒤 다시 생성한다.
- 게임 화면 캡처는 예외다. 캡처 픽셀을 손으로 고치면 증거가 무효가 되므로, 장면, 이벤트, 상태 hash, capture manifest와 생성 runner를 재현 원천으로 보관한다.

### 2. 선과 텍스트

- 연결선은 기본적으로 텍스트 영역을 지나지 않는다.
- 선 위에 라벨이 꼭 필요하면 `connector-label` 그룹 안에 불투명 `label-shield`를 두거나 배경색 halo를 사용한다. 선이 글리프 위에 인쇄되는 상태는 허용하지 않는다.
- 카드 설명, 축 라벨, 범례와 긴 부제는 경계선에서 최소 한 글자 높이만큼 떨어뜨린다.
- 표에는 세로선을 사용하지 않는다. `booktabs`의 top, mid, bottom rule과 1.10 이상의 행간을 사용한다.
- 각주와 약어 설명은 이를 사용하는 표 바로 아래에 둔다. 다른 표 아래로 미루지 않는다.

### 3. 비교 설계

- 비교 대상은 같은 기준선과 같은 분모를 공유할 때만 한 묶음으로 배치한다.
- 분모가 다르거나 성공 방향이 다른 행은 `해석 범위`를 함께 적고 비율 순위처럼 보이지 않게 한다.
- matched 비교는 두 값을 같은 셀 또는 인접 열에 두고, 필요한 경우 산술 차이 `Delta`를 함께 표시한다.
- 색만으로 의미를 전달하지 않는다. 라벨, 정확 count, 선 모양 또는 명시적 상태 문구를 함께 사용한다.
- 설계 픽스처 count, screening-pilot-only 결과, 인간 측정 결과를 같은 비교축으로 합치지 않는다.

### 4. 크기와 언어 패리티

- 논문 다이어그램은 벡터 PDF로 삽입하고 최종 인쇄 폭에서 최소 6.5 pt 상당의 본문 라벨을 유지한다.
- README SVG의 핵심 라벨은 12 px 미만으로 내리지 않는다.
- 영어와 한국어 논문의 표 번호, 그림 번호, claim ID, 수치, 비교 방향과 각주 의미를 맞춘다.
- 긴 한국어 또는 영어 라벨은 폭을 실제로 확인하고 줄바꿈한다. 문자 수만으로 잘라서 숨기지 않는다.

### 5. 갱신과 검증

```bash
uv run python scripts/generate_readme_visuals.py
uv run python scripts/generate_direction_figures.py
uv run python scripts/generate_paper_results.py
make -C paper/latex all
uv run python scripts/update_visual_source_manifest.py
uv run python scripts/validate_visual_assets.py --require-pdf-tools --check-regeneration
```

`validate_visual_assets.py`는 manifest freshness, SVG XML과 접근성 metadata, 편집 원본 존재, paper SVG/PDF/PNG 동거, PDF에 포함된 SVG 원본 hash, raster object와 Type 3 font가 없는 벡터 PDF 삽입, line-label shield, 논문 그림·balance chart의 source-level line/text collision, 표의 booktabs/행간/비교 구조를 검사한다. 경량 생성물 22개는 임시 사본에서 두 번 재생성해 byte equality도 검사한다. 최종 판정은 `make check`와 `./scripts/verify_like_ci.sh`까지 포함한다.

## English parity

`source-manifest.json` links every paper/README/research table or figure to its rendered output, editable source, generator, and data inputs. Diagrams and charts use UTF-8 SVG plus Python; data-driven visuals retain CSV, JSON, or TSV; paper tables retain editable LaTeX and their generator/data. Paper figures keep adjacent same-stem SVG, vector PDF, and PNG preview files.

Connectors must not print over text. A necessary inline label uses an opaque `label-shield` or background-colored halo. The validator checks source-level line/text geometry for paper figures and the balance chart, requires the SVG source hash inside each vector PDF, and double-regenerates lightweight sources in an isolated copy. Tables use no vertical rules, use `booktabs`, retain at least 1.10 row spacing, and keep notes under the table that owns them. Comparisons align matched values, show exact counts, expose a descriptive delta only for matched denominators, and label mixed-direction rows so they cannot be read as a ranking.

Engine screenshots are the deliberate exception: their pixels are not editable evidence. Their reproducible source is the bound scene, runner, event/state packet, and hash manifest. Regenerate rather than retouch them.
