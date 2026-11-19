"""Run Phase-6 P20 Large-Scale 1,200-Case 6-Domain Bilingual Escape Benchmark.

Evaluates 5 zero-network deterministic baselines on 1,200 compositional and adversarial
bilingual cases, computes Cochran's Q, pairwise McNemar exact tests, Wilson 95% CIs, and
writes research/green-supplements/phase6_large_bilingual_escape_results.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure scripts/ is in python path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import venue_phase6_benchmark_lib as p6
from venue_phase2_lib import mcnemar_exact_two_sided
from venue_phase3_lib import cochrans_q


def run_benchmark() -> dict[str, any]:
    print("Generating canonical Phase-6 1,200-case escape corpus...")
    corpus = p6.build_phase6_large_escape_corpus()
    corpus_sha = p6.compute_corpus_sha256(corpus)
    print(f"Corpus generated: {len(corpus)} items (SHA-256: {corpus_sha})")

    truth = [bool(it["expected_violation"]) for it in corpus]

    print("Evaluating Baseline 1: stage1_id_only...")
    p1 = [p6.baseline_stage1_id_only(it) for it in corpus]
    m1 = p6.score_predictions_comprehensive(corpus, p1)

    print("Evaluating Baseline 2: keyword_rule_naive...")
    p2 = [p6.baseline_keyword_rule_naive(it) for it in corpus]
    m2 = p6.score_predictions_comprehensive(corpus, p2)

    print("Evaluating Baseline 3: bm25_lexical_lodo (Leave-One-Domain-Out)...")
    p3 = p6.evaluate_bm25_lodo(corpus)
    m3 = p6.score_predictions_comprehensive(corpus, p3)

    print("Evaluating Baseline 4: tfidf_char_word_lodo (Leave-One-Domain-Out)...")
    p4 = p6.evaluate_tfidf_char_word_lodo(corpus)
    m4 = p6.score_predictions_comprehensive(corpus, p4)

    print("Evaluating Baseline 5: stage1_plus_negation_rule_hybrid...")
    p5 = [p6.baseline_stage1_plus_negation_rule_hybrid(it) for it in corpus]
    m5 = p6.score_predictions_comprehensive(corpus, p5)

    baselines = {
        "stage1_id_only": {"predictions": p1, "metrics": m1},
        "keyword_rule_naive": {"predictions": p2, "metrics": m2},
        "bm25_lexical_lodo": {"predictions": p3, "metrics": m3},
        "tfidf_char_word_lodo": {"predictions": p4, "metrics": m4},
        "stage1_plus_negation_rule_hybrid": {"predictions": p5, "metrics": m5},
    }

    names = list(baselines.keys())
    print("Computing Cochran's Q across all 5 baselines...")
    matrix = [
        [int(baselines[m]["predictions"][i] == truth[i]) for m in names] for i in range(len(corpus))
    ]
    cochran_result = cochrans_q(matrix)
    print(f"Cochran's Q: stat={cochran_result['q_stat']}, p={cochran_result['p_value']}")

    print("Computing pairwise McNemar exact tests...")
    pairwise_mcnemar: dict[str, any] = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pair_key = f"{names[i]}__vs__{names[j]}"
            res = mcnemar_exact_two_sided(
                truth, baselines[names[i]]["predictions"], baselines[names[j]]["predictions"]
            )
            pairwise_mcnemar[pair_key] = res

    print("Computing dataset shortcut diagnostics...")
    diagnostics = p6.compute_dataset_shortcut_diagnostics(corpus)

    # Sample cases: 1 sample per domain x stratum x language = 60 items
    sample_cases: list[dict[str, any]] = []
    seen_cells: set[tuple[str, str, str]] = set()
    for it in corpus:
        cell = (it["domain"], it["stratum"], it["language"])
        if cell not in seen_cells:
            seen_cells.add(cell)
            sample_cases.append(
                {
                    "case_id": it["case_id"],
                    "domain": it["domain"],
                    "stratum": it["stratum"],
                    "language": it["language"],
                    "expected_violation": it["expected_violation"],
                    "narrative_text": it["narrative_text"],
                }
            )

    results: dict[str, any] = {
        "benchmark_name": "Phase-6 P20 Large-Scale 6-Domain Compositional & Adversarial Bilingual Escape Benchmark",
        "phase": "Phase-6",
        "protocol": "6-Domain x 2-Language x 5-Stratum Compositional & Adversarial Verification",
        "ground_truth_provenance": "programmatic_compositional_construction",
        "human_evaluation_status": "AWAITING_HUMAN_RATERS",
        "human_raters_completed": 0,
        "corpus_sha256": corpus_sha,
        "corpus_summary": {
            "total_cases": len(corpus),
            "domains": p6.DOMAINS,
            "strata": p6.STRATA,
            "languages": p6.LANGUAGES,
            "items_per_cell": p6.ITEMS_PER_CELL,
            "by_stratum_counts": {
                s: sum(1 for it in corpus if it["stratum"] == s) for s in p6.STRATA
            },
            "by_language_counts": {
                lang: sum(1 for it in corpus if it["language"] == lang) for lang in p6.LANGUAGES
            },
            "by_domain_counts": {
                d: sum(1 for it in corpus if it["domain"] == d) for d in p6.DOMAINS
            },
        },
        "deterministic_baselines": {name: baselines[name]["metrics"] for name in names},
        "statistical_tests": {
            "cochrans_q": cochran_result,
            "pairwise_mcnemar": pairwise_mcnemar,
        },
        "shortcut_diagnostics": diagnostics,
        "sample_cases": sample_cases,
    }

    output_path = (
        REPO_ROOT / "research" / "green-supplements" / "phase6_large_bilingual_escape_results.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    size_kb = output_path.stat().st_size / 1024
    print(f"Results written to {output_path} ({size_kb:.1f} KB)")
    if size_kb >= 150:
        raise ValueError(f"Output JSON size ({size_kb:.1f} KB) exceeds 150 KB limit!")

    return results


if __name__ == "__main__":
    run_benchmark()
