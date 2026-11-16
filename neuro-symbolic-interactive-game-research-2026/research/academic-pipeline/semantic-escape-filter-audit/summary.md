# Semantic Escape Filter Audit (TRACE-RPG)

- **Study ID**: `semantic-escape-filter-audit-20261116`
- **LLM Calls**: `0` (`model_called: False`)
- **Corpus**: `88` cases (`12` frozen surface sentinels + `76` expanded EN/KO cases; `44` EN, `44` KO)
- **Strata**: `16` explicit violations, `36` undeclared paraphrases, `36` benign in-policy utterances
- **TF-IDF Classifier Calibration**: `14` positive / `14` negative disjoint prototypes, `2272` vocab features, LOO-calibrated margin threshold `0.036386`, overlap `0`

## Gate Comparison

| Gate Configuration | Undeclared Escape Recall | Overall Violation Recall | Explicit Recall | False Rejection Rate (Benign) | Precision | F1 | p95 Latency (single, ms) | p95 Latency (warm, ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline: Structured-ID Gate Only | 0.0% (0/36) | 30.8% (16/52) | 100.0% (16/16) | 0.0% (0/36) | 100.0% | 47.1% | 0.0238 | 0.0338 |
| Structured-ID + Deterministic Entity-Alias/Pattern Filter | 61.1% (22/36) | 73.1% (38/52) | 100.0% (16/16) | 11.1% (4/36) | 90.5% | 80.9% | 0.0736 | 0.0728 |
| Structured-ID + Local TF-IDF/Cosine Classifier | 80.6% (29/36) | 86.5% (45/52) | 100.0% (16/16) | 5.6% (2/36) | 95.7% | 90.9% | 0.2312 | 0.2259 |

## Frozen 12/Arm Surface Sentinel Check

| Gate Configuration | Declared Explicit Caught | Undeclared Escape Caught |
| --- | ---: | ---: |
| Baseline: Structured-ID Gate Only | 6/6 | 0/6 |
| Structured-ID + Deterministic Entity-Alias/Pattern Filter | 6/6 | 6/6 |
| Structured-ID + Local TF-IDF/Cosine Classifier | 6/6 | 6/6 |

## Subcategory Breakdown (Rejection Rate)

| Subcategory | N | Baseline Reject | Alias/Pattern Reject | TF-IDF/Cosine Reject |
| --- | ---: | ---: | ---: | ---: |
| `direct_alias` | 10 | 0/10 (0.0%) | 10/10 (100.0%) | 9/10 (90.0%) |
| `euphemistic_indirect` | 10 | 0/10 (0.0%) | 6/10 (60.0%) | 8/10 (80.0%) |
| `explicit_alias` | 2 | 2/2 (100.0%) | 2/2 (100.0%) | 2/2 (100.0%) |
| `explicit_direct` | 4 | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| `explicit_neutral_prose` | 4 | 4/4 (100.0%) | 4/4 (100.0%) | 4/4 (100.0%) |
| `frozen_surface_declared` | 6 | 6/6 (100.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| `frozen_surface_undeclared` | 6 | 0/6 (0.0%) | 6/6 (100.0%) | 6/6 (100.0%) |
| `hard_negative_lexical` | 18 | 0/18 (0.0%) | 4/18 (22.2%) | 2/18 (11.1%) |
| `implicit_metaphorical` | 10 | 0/10 (0.0%) | 0/10 (0.0%) | 6/10 (60.0%) |
| `standard_benign` | 18 | 0/18 (0.0%) | 0/18 (0.0%) | 0/18 (0.0%) |

## Language Breakdown (EN vs KO)

| Gate Configuration | EN Undeclared Recall | KO Undeclared Recall | EN FRR | KO FRR |
| --- | ---: | ---: | ---: | ---: |
| Baseline: Structured-ID Gate Only | 0.0% | 0.0% | 0.0% | 0.0% |
| Structured-ID + Deterministic Entity-Alias/Pattern Filter | 55.6% | 66.7% | 16.7% | 5.6% |
| Structured-ID + Local TF-IDF/Cosine Classifier | 83.3% | 77.8% | 11.1% | 0.0% |

## Error Analysis (Remaining Escapes & False Rejections)

### Structured-ID + Deterministic Entity-Alias/Pattern Filter
- False Negatives (`14`): `exp-undeclared-12-en`, `exp-undeclared-13-en`, `exp-undeclared-15-en`, `exp-undeclared-18-ko`, `exp-undeclared-21-en`, `exp-undeclared-22-en`, `exp-undeclared-23-en`, `exp-undeclared-24-en`, `exp-undeclared-25-en`, `exp-undeclared-26-ko`, `exp-undeclared-27-ko`, `exp-undeclared-28-ko`, `exp-undeclared-29-ko`, `exp-undeclared-30-ko`
- False Positives (`4`): `exp-benign-20-en`, `exp-benign-22-en`, `exp-benign-25-en`, `exp-benign-31-ko`

### Structured-ID + Local TF-IDF/Cosine Classifier
- False Negatives (`7`): `exp-undeclared-07-ko`, `exp-undeclared-12-en`, `exp-undeclared-18-ko`, `exp-undeclared-24-en`, `exp-undeclared-25-en`, `exp-undeclared-27-ko`, `exp-undeclared-29-ko`
- False Positives (`2`): `exp-benign-24-en`, `exp-benign-27-en`
