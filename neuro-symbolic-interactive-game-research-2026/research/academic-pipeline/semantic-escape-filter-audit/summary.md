# Semantic Escape Filter Audit (TRACE-RPG)

- **Study ID**: `semantic-escape-filter-audit-20261116`
- **LLM Calls**: `0` (`model_called: False`)
- **Environment**: `Darwin/arm64` (Python `3.11`, `4` source hashes bound)
- **Corpus**: `88` cases (`12` frozen surface sentinels + `76` expanded EN/KO cases; `44` EN, `44` KO)
- **Strata**: `16` explicit violations, `36` undeclared paraphrases, `36` benign in-policy utterances
- **TF-IDF Classifier Calibration**: `14` positive / `14` negative prototypes (`loo_idf_isolation=True`, `27` in-fold prototypes/fold), `2272` deployment vocab features, LOO-calibrated margin threshold `-0.035864` (`Youden J=0.0714`), exact eval overlap `0`

## Gate Comparison

| Gate Configuration | Undeclared Escape Recall | Overall Violation Recall | Explicit Recall | False Rejection Rate (Benign) | Precision | F1 | Overall Warm p95 (ms) | Stage-2 Only Warm p95 (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline: Structured-ID Gate Only | 0.0% (0/36) | 30.8% (16/52) | 100.0% (16/16) | 0.0% (0/36) | 100.0% | 47.1% | 0.0319 | N/A |
| Structured-ID + Deterministic Entity-Alias/Pattern Filter | 61.1% (22/36) | 73.1% (38/52) | 100.0% (16/16) | 11.1% (4/36) | 90.5% | 80.9% | 0.0407 | 0.0160 |
| Structured-ID + Local TF-IDF/Cosine Classifier | 97.2% (35/36) | 98.1% (51/52) | 100.0% (16/16) | 58.3% (21/36) | 70.8% | 82.3% | 0.7049 | 0.6761 |

## Frozen 12/Arm Surface Sentinel Check

| Gate Configuration | Declared Explicit Caught | Undeclared Escape Caught |
| --- | ---: | ---: |
| Baseline: Structured-ID Gate Only | 6/6 | 0/6 |
| Structured-ID + Deterministic Entity-Alias/Pattern Filter | 6/6 | 6/6 |
| Structured-ID + Local TF-IDF/Cosine Classifier | 6/6 | 6/6 |

## Subcategory Breakdown (Rejection Rate)

| Subcategory | N | Baseline Reject | Alias/Pattern Reject | TF-IDF/Cosine Reject |
| --- | ---: | ---: | ---: | ---: |
| `direct_alias` | 10 | 0/10 (0.0%) | 10/10 (100.0%) | 10/10 (100.0%) |
| `euphemistic_indirect` | 10 | 0/10 (0.0%) | 6/10 (60.0%) | 10/10 (100.0%) |
| `explicit_alias` | 2 | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) |
| `explicit_direct` | 4 | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| `explicit_neutral_prose` | 4 | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| `frozen_surface_declared` | 6 | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| `frozen_surface_undeclared` | 6 | 0/6 (0.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| `hard_negative_lexical` | 18 | 0/18 (0.0%) | 4/18 (22.2%) | 8/18 (44.4%) |
| `implicit_metaphorical` | 10 | 0/10 (0.0%) | 0/10 (0.0%) | 9/10 (90.0%) |
| `standard_benign` | 18 | 0/18 (0.0%) | 0/18 (0.0%) | 13/18 (72.2%) |

## Language Breakdown (EN vs KO)

| Gate Configuration | EN Undeclared Recall | KO Undeclared Recall | EN FRR | KO FRR |
| --- | ---: | ---: | ---: | ---: |
| Baseline: Structured-ID Gate Only | 0.0% | 0.0% | 0.0% | 0.0% |
| Structured-ID + Deterministic Entity-Alias/Pattern Filter | 55.6% | 66.7% | 16.7% | 5.6% |
| Structured-ID + Local TF-IDF/Cosine Classifier | 94.4% | 100.0% | 72.2% | 44.4% |

## Scope Limitations & Methodological Caveats

- **Single Forbidden Fact ID (`single_secret_id: "keeper_secret"`):** All 88 evaluation cases test surface leakage of a single forbidden fact ID ('keeper_secret') in the Sealed Lighthouse harbor scenario; multi-secret inventories, multi-actor asymmetric disclosure tables, and dynamic cross-turn secret accumulation are not evaluated here.
- **Co-Authored Calibration & Evaluation Utterances:** Although the 28 TF-IDF calibration prototypes (14 positive, 14 negative) have zero exact text overlap with the 88 evaluation cases and vocabulary/IDF weights are computed strictly inside each 27-prototype Leave-One-Out fold before deployment refitting, both the calibration prototypes and the 76 expanded EN/KO evaluation utterances were co-authored within the same study rather than collected from independent external red-teamers or live LLM generations.
- **`implicit_metaphorical` Subcategory Recall (`n=10`):** Alias/Pattern catches `0/10` (`0.0%`) and LOO TF-IDF/Cosine catches `9/10` (`90.0%`), confirming that pragmatic/metaphorical leaks without shared lexical anchors still partially evade surface lexical filters.
- **`hard_negative_lexical` & Benign FRR (`n=18` hard negatives, `n=18` standard benign):** Alias/Pattern false rejections are confined to lexically overlapping hard negatives (`4/18` = `22.2%`; `standard_benign` `0/18` = `0.0%`), whereas strictly leakage-free 27-prototype LOO TF-IDF calibration (`threshold=-0.035864`, `Youden J=0.0714`) yields `8/18` (`44.4%`) on `hard_negative_lexical` and `13/18` (`72.2%`) on `standard_benign` (showing high sensitivity of tiny-prototype bag-of-ngrams LOO thresholds once self-IDF leakage is removed).
- **Stage-2-Only vs Overall Warm Latency (`WARM_REPEATS=25`):** Overall `warm_p95_ms` (`0.0407 ms` Alias/Pattern, `0.7049 ms` TF-IDF) includes `16/88` Stage-1-rejected cases that short-circuit before Stage 2; `stage2_only_warm_p95_ms` across the `1800` Stage-2 invocations is `0.0160 ms` (Alias/Pattern) and `0.6761 ms` (TF-IDF), with end-to-end Stage-2-executed warm p95 `0.0395 ms` and `0.7857 ms`.

## Error Analysis (Remaining Escapes & False Rejections)

### Structured-ID + Deterministic Entity-Alias/Pattern Filter
- False Negatives (`14`): `exp-undeclared-12-en`, `exp-undeclared-13-en`, `exp-undeclared-15-en`, `exp-undeclared-18-ko`, `exp-undeclared-21-en`, `exp-undeclared-22-en`, `exp-undeclared-23-en`, `exp-undeclared-24-en`, `exp-undeclared-25-en`, `exp-undeclared-26-ko`, `exp-undeclared-27-ko`, `exp-undeclared-28-ko`, `exp-undeclared-29-ko`, `exp-undeclared-30-ko`
- False Positives (`4`): `exp-benign-20-en`, `exp-benign-22-en`, `exp-benign-25-en`, `exp-benign-31-ko`

### Structured-ID + Local TF-IDF/Cosine Classifier
- False Negatives (`1`): `exp-undeclared-25-en`
- False Positives (`21`): `exp-benign-02-en`, `exp-benign-03-en`, `exp-benign-04-en`, `exp-benign-05-en`, `exp-benign-06-en`, `exp-benign-08-en`, `exp-benign-09-en`, `exp-benign-11-ko`, `exp-benign-12-ko`, `exp-benign-13-ko`, `exp-benign-14-ko`, `exp-benign-16-ko`, `exp-benign-17-ko`, `exp-benign-20-en`, `exp-benign-21-en`, `exp-benign-24-en`, `exp-benign-25-en`, `exp-benign-26-en`, `exp-benign-27-en`, `exp-benign-30-ko`, `exp-benign-31-ko`
