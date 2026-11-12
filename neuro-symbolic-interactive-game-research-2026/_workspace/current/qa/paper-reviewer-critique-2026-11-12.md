# TRACE-RPG 논문 리뷰어 관점 개선사항 및 수정 계획

- **작성일**: 2026-11-12
- **대상 원고**:
  - 영문: `paper/latex/en/main.tex`
  - 국문: `paper/latex/ko/main.tex`
  - 보충자료: `paper/latex/en/traceability-supplement.tex`, `paper/latex/ko/traceability-supplement.tex`
- **전제 조건**: `scripts/validate_contribution_crosswalk.py`, `scripts/validate_visual_assets.py`, `tests/test_*.py` 등 저장소의 CI/출판 검증 계약을 유지하면서 학술 논문으로서의 가독성, 논리적 완결성, 한·영 정합성 및 조판 품질을 개선한다.

---

## 1. 핵심 구조적 개선사항 (Major Revisions)

### M1. 초록 및 본문의 과도한 면책 조항(Over-Disclaiming) 압축
- **지적 사항**:
  - 초록(Abstract)과 본문 각 절마다 *"does not establish efficacy, superiority, A or C, player benefit..."* 및 *"provider identity, revision, cost, request count unknown"* 등의 방어적 문구가 10회 이상 반복되어, 논문의 핵심 기여(C1~C5: 외부 결정론적 게이트, 반례 유도 수리 $\rho$, 리플레이 무결성, 배정 완결성 회계)가 묻힌다.
- **개선 방향**:
  - 초록을 **연구 문제 $\rightarrow$ 핵심 아키텍처(C1~C5) $\rightarrow$ 주요 실증 관측치(대시보드 사례, 고정 게임 파일럿 5/8, v5 수집 8/20·7/20) $\rightarrow$ 단일화된 범위 경계 문장** 순으로 압축하여 가독성을 높인다.
  - 반복되는 추론 상한(Inference Ceiling) 및 미상 메타데이터 고지는 Table I(`contribution_map`), Table IV(`evidence_lanes`), 그리고 **Threats and Boundaries(타당성 위협 및 경계)** 절에 집중 배치한다.

### M2. 실험 섹션(Section V)의 코호트 파편화 해소
- **지적 사항**:
  - 본문 Section V(Pilot Results) 내에 유효 응답이 0건인 중단 코호트(`v2 evidence/diagnostic`), 과거 파일 계수(`Historical bookkeeping`: v1~v4), 실행이 0/180건 차단된 `Prospective two-track pilot`(`NOT_RUN/BLOCKED`), 단일 탐색 사례(`Separate exploratory signal example`)가 혼재되어 미완성 보고서처럼 보인다.
- **개선 방향**:
  - 본문 Section V는 **완료·관측된 핵심 실증 레인**(E1 오프라인 적합성, NPC-ENG1/SCR1 및 NPC-DISC-1, ENG1 및 단일 Codex 사례, 고정 게임 native 비교, v5 paired-selector 수집) 중심으로 정리한다.
  - 중단·미완료·차단된 파일럿 기록(`v2` 중단 코호트, `v1~v4` 과거 파일 계수, `prospective-pilot` 차단 상태, 단일 탐색 영수증)은 **부록(Appendix: Diagnostic, Historical, and Blocked Cohorts)**으로 분리 배치하여 본문의 서사 흐름을 정돈한다(단, CI 계약상 `\input{../generated/prospective-pilot/status_*.tex}`는 `main.tex` 클로저 내에 유지).

### M3. 수식 (1)과 실제 Python 구현 계약 간의 자기 부정 해소
- **지적 사항**:
  - Section III에서 개념적 검증기 $V(c_t,a_t)=(\boldsymbol{v}, E_t)\in\{0,1\}^7$을 정의한 직후, 본문에서 *"실제 Python 반환 타입은 7개 불리언이 아니라 `ValidationResult(valid, errors, checks_run)`이다"*라고 수식을 스스로 부정한다.
- **개선 방향**:
  - 수식 (1)을 실제 구현 계약(`ValidationResult(valid, errors, checks_run)`)과 일관되도록 $V(c_t,a_t)=(\mathrm{valid}, E_t, C_{\mathrm{run}})$로 정식화하고, 일곱 개 결정론적 검사 비트 $\boldsymbol{v}\in\{0,1\}^7$와 $\mathrm{valid} \iff \bigwedge_{i=1}^{7}(v_i=1)$의 관계를 명확히 연결해 개념과 코드 간 괴리를 제거한다.

### M4. 수리 루프($\rho$) 검증 공백 및 `unauthorized_objective` 목표 모순 명확화
- **지적 사항**:
  - 핵심 기여가 Validate–Repair–Commit(C2, C5)임에도 고정 게임 파일럿(8행)은 `repair=0`이고, v5 수집(20행)도 추가 수리 호출이 0회다. 또한 v5의 `unauthorized_objective` 픽스처는 정책을 준수해 게이트를 통과하면(Luna 상세 4/5) 공통 목표(`signal_restored`)에는 반드시 실패(3/5)하도록 설계되어 혼동을 준다.
- **개선 방향**:
  - E1의 결정론적 $\rho$ 수리(5/5)가 **다중 시도 수리 루프의 메커니즘 적합성**을, v5 수집(상세 4/5 vs 일반 3/5)이 **단일 패스 피드백 신호의 게이트 통과 차이**를 각각 검증함을 명확히 구분한다.
  - `unauthorized_objective`의 4/5 vs 3/5 차이는 모델 오류가 아니라 *정책 준수(불법 효과 차단)와 목표 달성(`signal_restored`) 간의 의도적 분리 검증*임을 한 문장으로 명료화한다.

### M5. 재현성 및 데이터 가용성(Data and Code Availability) 문구 정돈
- **지적 사항**:
  - 키워드가 `reproducibility`임에도 *"held by the authors, not deposited"*, *"no repository or deposit identifier"*라고 서술해 리뷰어에게 검증 불가 인상을 준다.
- **개선 방향**:
  - 익명 심사 단계의 보존 범위(기계 검증된 매트릭스, 동결 패킷, 검증 스크립트, 공개 투영)와 외부 저장소/DOI 기탁 예정 상태를 구분해 객관적으로 서술한다(CI 마커 문자열 유지).

---

## 2. 세부 편집·조판 및 한·영 정합성 오류 (Minor & Technical Fixes)

1. **부록 및 보충자료 표 번호 점프 오류 수정**:
   - 본문 표는 Table XI(11번)까지 존재하나, 부록 B(`runtime_identity_extension_*.tex`)가 `\setcounter{table}{14}`(Table XV)로 하드코딩되어 Table XII~XIV가 누락된 상태.
   - `scripts/generate_runtime_comparison_publication.py` 및 생성 파일의 하드코딩 카운터 의존성을 점검하고, 본문·부록·보충자료(`traceability-supplement.tex`) 간 표 번호가 자연스럽게 이어지도록 정합성을 맞춘다.
2. **영문·국문 원고 장(Section) 및 하위 절 구조 통일**:
   - **장 번호 불일치**: 영문(`en/main.tex`)은 Section 6이 `Discussion, Threats, Ethics, and Artifact Scope`, Section 7이 `Conclusion`인 반면, 국문(`ko/main.tex`)은 Section 6 `논의`, Section 7 `타당성 위협, 윤리, 산출물 범위`, Section 8 `결론`으로 나뉘어 있음 $\rightarrow$ **국문본도 영문본과 동일하게 7개 장 구조(Section 6 통합, Section 7 결론)로 통일**.
   - **Section 4.1.1 및 Section 5.3/5.4 불일치**: 국문본에만 있는 `4.1.1 여덟 역할 구조와 source binding` 및 `5.3/5.4` 분리 구조를 영문본과 일치시킴.
   - **Section 5 서두 입력 순서 불일치**: 영문(`pilot_tables` $\rightarrow$ `pilot_results`)과 국문(`pilot_results` $\rightarrow$ `pilot_tables`)의 `\input` 순서를 통일.
3. **국문 원고 비문 및 영문 혼용 표기 수정 (`ko/main.tex`)**:
   - **서론 첫 문단 비문**: `권한이 아니며 \cite{...}. 상태 변경은` $\rightarrow$ `권한이 아니며 \cite{...}, 상태 변경은`으로 수정.
   - **표 참조 혼용**: `Table~\ref{tab:contribution-map}은` $\rightarrow$ `표~\ref{tab:contribution-map}은`으로 통일.
   - **문체 정돈**: 국문 본문의 과도한 영문 단어 직역·병기(`~이지 ~가 아니다`)를 자연스러운 학술 국문으로 다듬되, CI 테스트가 검증하는 필수 한국어/영어 키워드(`일곱 개의 결정론적 검사`, `여섯 상태 상대 계열`, `기계 검증 기여·참조 주제·실험 매트릭스` 등)는 정확히 보존.
4. **빌드 및 CI 검증 통과**:
   - `paper/latex`에서 영문/국문 PDF 재빌드(`make check`) 및 `Overfull` / `Missing character` / `Type 3 font` 0건 확인.
   - `visuals/source-manifest.json` 갱신(필요 시) 및 `./scripts/verify_like_ci.sh` 관련 테스트 통과 확인.
