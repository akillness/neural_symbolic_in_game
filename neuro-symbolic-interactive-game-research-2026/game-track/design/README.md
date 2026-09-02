# The Sealed Lighthouse design packet / 봉인된 등대 설계 패킷

This directory is the stable, paper-citable companion to the live studio material in
`../../_workspace/current/design/`. It contains no empirical efficacy claim.

이 디렉터리는 `../../_workspace/current/design/`의 실시간 스튜디오 문서를 논문에서 안정적으로
참조하기 위한 동반 패킷이다. 경험적 효과 주장은 포함하지 않는다.

| Pair / 쌍 | English | 한국어 | Authority / 권한 |
|---|---|---|---|
| `SL-GDD-001` | [gdd.en.md](gdd.en.md) | [gdd.ko.md](gdd.ko.md) | Product and interaction specification / 제품·상호작용 명세 |
| `SL-ORACLE-001` | [scenario-oracle-plan.en.md](scenario-oracle-plan.en.md) | [scenario-oracle-plan.ko.md](scenario-oracle-plan.ko.md) | Scenario split, holdout, and independent oracle protocol / 시나리오 분할·홀드아웃·독립 오라클 |
| `SL-XWALK-001` | [paper-crosswalk.en.md](paper-crosswalk.en.md) | [paper-crosswalk.ko.md](paper-crosswalk.ko.md) | RQ1–RQ5 and Stage 6 C1/M6 mapping / RQ1–RQ5 및 Stage 6 C1/M6 연결 |
| `SL-HYP-001` | [game-design-hypothesis.json](game-design-hypothesis.json) | (language-neutral JSON) | Design hypothesis H-CONTRIB-01 through H-RECEIPT-04 with falsifier and evidence plan / 설계 가설 H-CONTRIB-01~H-RECEIPT-04 위조자·증거 계획 |
| `SL-UI-01` | [game-ui-contract.json](game-ui-contract.json) | (language-neutral JSON) | UI/UX contract v1 with CONTRIBUTION/RULE LEARNED/CASE CHAIN/end-card surfaces / UI/UX 계약 v1 CONTRIBUTION/RULE LEARNED/CASE CHAIN/end-card 표면 |

## Status vocabulary / 상태 어휘

- `[OBSERVED]`: supported by an existing cited artifact or executed record.
- `[TARGET]`: required value, behavior, or artifact; not yet measured.
- `[INFERENCE]`: reasoned interpretation that needs review or execution.
- `[PLANNED]`: scheduled method or output that does not yet exist.

English and Korean documents share pair IDs, table IDs, scenario IDs, claim IDs, equations, and
numbers. Any numeric or semantic change must update both files in the same commit.

영문과 국문 문서는 쌍 ID, 표 ID, 시나리오 ID, 주장 ID, 수식, 수치를 공유한다. 수치나 의미 변경은
동일 커밋에서 두 파일에 함께 반영한다.
