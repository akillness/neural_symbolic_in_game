# Stage 4 Replication Receipt / 4단계 재현 영수증

Date: 2026-09-02  
Command: `uv run python scripts/run_conformance_pilot.py --output-dir <scratch>/runs --release-dir <scratch>/release`  
Purpose: confirm that the frozen `stage-04-pilot` packet reproduces from the tracked manifest without touching the release directory. This is a reproducibility receipt for E1, not new evidence and not a promotion of any `C-RESULT-*` claim.

- `pilot-results.json`: identical after removing volatile keys (none): **True**
- Every generated CSV below was compared byte-for-byte against the frozen release.

| CSV | Byte-identical | Frozen SHA-256 (prefix) |
|---|---|---|
| `accounting-guards.csv` | yes | `17918e03e8971bd2` |
| `adapter-accounting.csv` | yes | `720abffe93b605ad` |
| `boundary-sentinels.csv` | yes | `2142c6ea6a9c3437` |
| `closed-boundary-regressions.csv` | yes | `54bc10d5a6b00259` |
| `gate-conformance.csv` | yes | `552cd2939b8fa6ad` |
| `integrity-boundaries.csv` | yes | `b9e16ea9d6777c89` |
| `integrity-faults.csv` | yes | `9cd903ad799cf413` |
| `pilot-summary.csv` | yes | `e983674f5a09e3fb` |
| `repair-arm-summary.csv` | yes | `464ba51d694d31e3` |
| `repair-arms.csv` | yes | `66a791fcd441127a` |
| `repair-class-summary.csv` | yes | `44fd6d612ae4be78` |

동결 패킷은 격리된 출력 디렉터리에서 CSV 전부 바이트 동일하게 재현됐다. 이는 E1의 재현성 영수증이며 새 근거나 효능 주장이 아니다.
