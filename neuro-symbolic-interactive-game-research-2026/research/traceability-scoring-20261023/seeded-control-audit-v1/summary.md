# Traceability Seeded Control Audit (`seeded-control-audit-v1`)

- **Rubric:** `traceability-scoring-rubric-20261023` (`status=PROPOSED_NOT_VALIDATED`)
- **LLM Calls:** `0` (`model_called=False`)
- **Human Inter-Rater Reliability (`krippendorff_alpha`):** **`UNDEFINED`** (`NOT_ESTIMABLE` — zero human assessors; automated deterministic scorer only)
- **Frozen Input/Source Preflight:** inventory `1664+48/1712` (`complete=True`), `input_hashes` `7/7`, `source_hashes` `20/20`

## 1. Seeded Corruption Sensitivity & Invariance False-Alarm Rates

- **Clean native baseline pool:** `1248` units (`semantic_rejection` + `unchanged_retry` + `guided_repair`, baseline failures=`0`)
- **Overall detector sensitivity (`detected_valid_corruptions / seeded_valid_corruptions`):** **`4656/4656`** (`100.00%`)
- **Inapplicable controls retained separately:** `1584` (`malformed=0`)
- **Overall invariance false-alarm rate (`false_alarms / clean_control_units`):** **`0/3744`** (`0.00%`, invariance preservation=`100.00%`)

### Seeded Corruption Controls (5 types)

| Corruption Control | Detected / Valid | Sensitivity | Inapplicable (Separate) | Triggered Dimensions | Primary Missingness Reasons |
|---|---:|---:|---:|---|---|
| `remove_receipt` | 1248/1248 | 100.0% | 0 | TR01:1248, TR02:1248, TR03:1248, TR04:520 | contradicted:520, missing:11024 |
| `swap_attempt_id` | 520/520 | 100.0% | 728 | TR01:520, TR03:520, TR04:520 | contradicted:2080 |
| `bind_old_artifact_revision` | 1248/1248 | 100.0% | 0 | TR01:1248, TR02:1248 | stale:2496 |
| `reverse_decision_or_status` | 1248/1248 | 100.0% | 0 | TR02:1248, TR03:1248, TR04:520 | contradicted:5512 |
| `omit_failed_repair` | 392/392 | 100.0% | 856 | TR04:392 | missing:1176 |

### Invariance Controls (3 types)

| Invariance Control | False Alarms / Clean Units | False-Alarm Rate | Invariance Preserved |
|---|---:|---:|---:|
| `clean_duplicate` | 0/1248 | 0.0% | 100.0% |
| `irrelevant_decorative_addition` | 0/1248 | 0.0% | 100.0% |
| `semantics_preserving_format_change` | 0/1248 | 0.0% | 100.0% |

## 2. Baseline `TR01-TR05` Complete-Chain Scores (Frozen Artifacts)

> Per `rubric.json`: `TR01-TR05`, forward/reverse `TR05`, outcomes, and cohorts are never averaged or collapsed.

### Cohort 1: `gemini-review-20261113/results-v2` — Core (`n=1,664` across 4 arms)

| Arm | Units | Outcomes (`PASS/FAIL`) | TR01 | TR02 | TR03 | TR04 |
|---|---:|---|---|---|---|---|
| `schema_only` | 416 | 416/0 | 0/416 (0.0%) | 0/416 (0.0%) | 0/416 (0.0%) | N/A (0/0) |
| `semantic_rejection` | 416 | 156/260 | 416/416 (100.0%) | 416/416 (100.0%) | 416/416 (100.0%) | N/A (0/0) |
| `unchanged_retry` | 416 | 156/260 | 416/416 (100.0%) | 416/416 (100.0%) | 416/416 (100.0%) | 260/260 (100.0%) |
| `guided_repair` | 416 | 284/132 | 416/416 (100.0%) | 416/416 (100.0%) | 416/416 (100.0%) | 260/260 (100.0%) |

### Cohort 1: `gemini-review-20261113/results-v2` — Surface Sentinels (`n=48` across 4 arms)

| Arm | Units | Outcomes (`PASS/FAIL`) | TR01 | TR02 | TR03 | TR04 |
|---|---:|---|---|---|---|---|
| `schema_only` | 12 | 12/0 | 0/12 (0.0%) | 0/12 (0.0%) | 0/12 (0.0%) | N/A (0/0) |
| `semantic_rejection` | 12 | 6/6 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | N/A (0/0) |
| `unchanged_retry` | 12 | 6/6 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | 6/6 (100.0%) |
| `guided_repair` | 12 | 6/6 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | 6/6 (100.0%) |

### Cohort 1: `TR05` Bidirectional Requirement Coverage (Separate Views)

- **`TR05_forward` (`n_05F / N_05F`):** `12/12 (100.0%)` (predeclared `protocol.json` requirements -> implementing artifacts -> verified evidence)
- **`TR05_reverse` (`n_05R / N_05R`):** `10/10 (100.0%)` (in-scope hashed artifacts -> justified `gemini-review-20261113` requirements; `10` co-hashed sibling modules in `source_hashes.json` disclosed separately)

### Cohort 2: `stage-04-pilot/pilot-results.json` (`n=63` `outcome_record` rows)

| Section | Arm | Units | TR01 | TR02 | TR03 | TR04 |
|---|---|---:|---|---|---|---|
| `gate_conformance` | `gate_validation_k0` | 13 | 13/13 (100.0%) | 13/13 (100.0%) | 13/13 (100.0%) | N/A (0/0) |
| `boundary_sentinels` | `boundary_sentinel_k0` | 2 | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) | N/A (0/0) |
| `repair_arms` | `rejection_only` | 12 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | N/A (0/0) |
| `repair_arms` | `unchanged_retry` | 12 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) |
| `repair_arms` | `guided_repair` | 12 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) |
| `repair_arms` | `structured_repair` | 12 | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) | 12/12 (100.0%) |

## 3. Audit Burden & Non-Claims

- **Runtime wall-clock:** `8.7328s` across `10175` total unit evaluations (`0.8583 ms/unit`, `access_failures=0`).
- **Non-claims:**
  - Human inter-rater reliability (Krippendorff alpha) is UNDEFINED; this script executes deterministic rubric checks and seeded controls only.
  - Frozen denominators (SL-PLAY-EVAL-001 52/52, SL-BALANCE-PROBE-001 5/5, C-RESULT-* TODO-RESULT) and frozen artifacts were not modified.
  - Seeded control sensitivity verifies deterministic rubric-detector behavior on known synthetic fault injections, not prospective human assessor agreement or development-comparison-20261023 execution.
  - Traceability completeness (TR01-TR05) does not imply task success, semantic correctness, or safety (e.g., failed repairs in unchanged_retry score 1 on TR04 while remaining HOLD/FAIL).
