# SL-KG-ONTOLOGY-SIM-001 — KG/ontology proposal evaluation

> **[SIMULATED · ENGINEERING ONLY]** This is an authored closed-world link-holdout
> benchmark. It is not runtime retrieval, semantic completeness, player evidence, or a
> result for C-RESULT-001 through C-RESULT-005.

## Exact terms and equations

For query set $Q$, selected links $S_q$, and frozen relevant links $G_q$:

$$TP=\sum_q|S_q\cap G_q|,\quad FP=\sum_q|S_q\setminus G_q|,\quad FN=\sum_q|G_q\setminus S_q|.$$

$$P=\frac{TP}{TP+FP},\quad R=\frac{TP}{TP+FN},\quad F_1=\frac{2PR}{P+R}.$$

With realistic tie rank $r_q=(r_q^{opt}+r_q^{pess})/2$:

$$\mathrm{MRR}=|Q|^{-1}\sum_q r_q^{-1},\qquad \mathrm{BS}=N^{-1}\sum_i(s_i-y_i)^2.$$

$$\mathrm{Sem}@K=(K|Q|)^{-1}\sum_q\sum_{i=1}^{K}I[\mathrm{domain/range\ valid}_{qi}].$$

A zero denominator returns `0.0` while the raw count remains present. MRR uses the average of optimistic and pessimistic ranks for ties. The Brier score treats the bounded strategy score as a diagnostic confidence, not a calibrated probability claim.

## Graph and ontology conformance

| Item | Value | Interpretation |
|---|---:|---|
| OKF nodes | 43 | repository-local method atoms |
| Reference edges | 106 | Markdown links |
| Curated typed edges | 24 | reviewed relation overlay |
| Declared node types | 21 | methods + game-state vocabulary |
| Ontology violations | 0 | exact structural/domain/range checks |
| Competency-query coverage | 1.000 | construction check |
| Encoded relation coverage | 6/6 | construction invariant; not semantic completeness |

## Frozen strategy trials

| Strategy | Decision | Eligible | Precision | Recall | F1 | Coverage | MRR | Hits@1 | nDCG@3 | Brier | Sem@3 |
|---|---|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `S0-degree-baseline` | baseline | no | 0.000 | 0.000 | 0.000 | 0.667 | 0.282 | 0.000 | 0.377 | 0.315 | 0.556 |
| `S1-lexical` | discard | no | 1.000 | 1.000 | 1.000 | 1.000 | 0.944 | 1.000 | 1.000 | 0.156 | 0.778 |
| `S2-typed-lexical-loose` | keep | yes | 1.000 | 1.000 | 1.000 | 1.000 | 0.944 | 1.000 | 1.000 | 0.131 | 1.000 |
| `S3-typed-lexical-strict` | discard | no | 1.000 | 0.500 | 0.667 | 0.500 | 0.944 | 1.000 | 1.000 | 0.131 | 1.000 |
| `S4-typed-lexical-path` | discard | yes | 0.833 | 0.833 | 0.833 | 1.000 | 0.861 | 0.833 | 0.938 | 0.137 | 1.000 |
| `S5-path-heavy` | discard | no | 0.500 | 0.500 | 0.500 | 1.000 | 0.625 | 0.500 | 0.688 | 0.174 | 1.000 |
| `S6-degree-mix` | discard | no | 0.500 | 0.500 | 0.500 | 1.000 | 0.639 | 0.500 | 0.772 | 0.141 | 1.000 |

## Selected strategy

Winner: `S2-typed-lexical-loose`.

| Query | Top proposed target | Score | Frozen relevance |
|---|---|---:|:---:|
| `Q-REPAIR-METRIC` | `/metrics/repair-at-k.md` | 0.478 | yes |
| `Q-MEMORY-METRIC` | `/metrics/long-horizon-contradiction-rate.md` | 0.517 | yes |
| `Q-AFFECT-METRIC` | `/metrics/tension-rmse.md` | 0.512 | yes |
| `Q-COST-METRIC` | `/metrics/cost-of-valid-episode.md` | 0.482 | yes |
| `Q-CONFIRMATORY-CONTRAST` | `/contrasts/h3-memory.md` | 0.435 | yes |
| `Q-ENGINE-PROTOCOL` | `/protocols/validate-repair-commit.md` | 0.420 | yes |

## Interpretation boundary

The benchmark has six authored queries, five candidates per query, and exactly one held-out relevant relation per query. Unregistered candidates are closed-world negatives only for this engineering battery. The same authored graph supplies features and labels, so this evaluates reproducible link recovery under the encoded ontology, not independent semantic truth or user usefulness.

The SQLite file is a generated property-graph mirror for inspection. It does not replace the sibling Graphify navigation graph, the Python `WorldState`, the hard validator, or any Godot authority boundary.
