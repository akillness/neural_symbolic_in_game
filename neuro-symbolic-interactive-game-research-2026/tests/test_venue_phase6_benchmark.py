"""Tests for Phase-6 Large-Scale 1,200-Case Bilingual Escape Benchmark.

Verifies corpus composition, zero overlap with Phase-2 corpus, deterministic SHA-256 stability,
baseline invariants (stage1_id_only, keyword_rule_naive, LODO zero leakage), and saved JSON integrity.
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import venue_phase6_benchmark_lib as p6
from venue_phase2_lib import build_multisecret_escape_corpus

JSON_PATH = ROOT / "research" / "green-supplements" / "phase6_large_bilingual_escape_results.json"

EXPECTED_DOMAINS = (
    "keeper_secret",
    "council_forgery",
    "eclipse_sabotage",
    "treaty_betrayal",
    "vault_cipher",
    "guild_smuggling",
)

EXPECTED_STRATA = (
    "S1_explicit_id_leak",
    "S2_indirect_paraphrase_leak",
    "S3_crosslingual_compositional_leak",
    "S4_lexical_hard_negative_benign",
    "S5_neutral_role_benign",
)


def test_phase6_corpus_structure_and_balance() -> None:
    """Assert 1,200 unique items, 240 per stratum, 200 per domain, 600 EN + 600 KO."""
    corpus = p6.build_phase6_large_escape_corpus()
    assert len(corpus) == 1200

    # Unique case IDs and narrative texts
    case_ids = [it["case_id"] for it in corpus]
    narratives = [it["narrative_text"] for it in corpus]
    assert len(set(case_ids)) == 1200
    assert len(set(narratives)) == 1200

    # Stratum distribution: 240 each across S1..S5
    stratum_counts = collections.Counter(it["stratum"] for it in corpus)
    assert set(stratum_counts.keys()) == set(EXPECTED_STRATA)
    for stratum in EXPECTED_STRATA:
        assert stratum_counts[stratum] == 240

    # Domain distribution: 200 each across 6 domains
    domain_counts = collections.Counter(it["domain"] for it in corpus)
    assert set(domain_counts.keys()) == set(EXPECTED_DOMAINS)
    for domain in EXPECTED_DOMAINS:
        assert domain_counts[domain] == 200

    # Language distribution: 600 EN + 600 KO
    lang_counts = collections.Counter(it["language"] for it in corpus)
    assert lang_counts["en"] == 600
    assert lang_counts["ko"] == 600

    # Balanced design: 20 items per (domain, stratum, language) cell
    cell_counts = collections.Counter(
        (it["domain"], it["stratum"], it["language"]) for it in corpus
    )
    assert len(cell_counts) == 6 * 5 * 2  # 60 cells
    for cell, count in cell_counts.items():
        assert count == 20, f"Cell {cell} has count {count} != 20"


def test_zero_text_overlap_with_phase2_corpus() -> None:
    """Assert 0 text overlap between Phase-6 (1,200 items) and Phase-2 (180 items) corpora."""
    phase2_corpus = build_multisecret_escape_corpus()
    assert len(phase2_corpus) == 180

    phase2_texts = {
        it["candidate"]["narrative_text"].strip()
        for it in phase2_corpus
        if "candidate" in it and "narrative_text" in it["candidate"]
    }
    assert len(phase2_texts) == 180

    phase6_corpus = p6.build_phase6_large_escape_corpus()
    phase6_texts = {it["narrative_text"].strip() for it in phase6_corpus}
    assert len(phase6_texts) == 1200

    overlap = phase2_texts.intersection(phase6_texts)
    assert len(overlap) == 0, (
        f"Found {len(overlap)} overlapping narrative texts with Phase-2 corpus: {overlap}"
    )


def test_deterministic_corpus_sha256_stability() -> None:
    """Assert deterministic corpus SHA-256 stability across repeated generations and matches artifact."""
    corpus1 = p6.build_phase6_large_escape_corpus()
    corpus2 = p6.build_phase6_large_escape_corpus()

    sha1 = p6.compute_corpus_sha256(corpus1)
    sha2 = p6.compute_corpus_sha256(corpus2)

    assert sha1 == sha2
    assert len(sha1) == 64
    assert all(c in "0123456789abcdef" for c in sha1)

    # Cross-check against the saved artifact
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["corpus_sha256"] == sha1


def test_baseline_invariants_and_lodo_zero_leakage() -> None:
    """Assert correct baseline invariants and zero domain leakage in Leave-One-Domain-Out."""
    corpus = p6.build_phase6_large_escape_corpus()

    s1_items = [it for it in corpus if it["stratum"] == "S1_explicit_id_leak"]
    s2_items = [it for it in corpus if it["stratum"] == "S2_indirect_paraphrase_leak"]
    s3_items = [it for it in corpus if it["stratum"] == "S3_crosslingual_compositional_leak"]
    s4_items = [it for it in corpus if it["stratum"] == "S4_lexical_hard_negative_benign"]
    s5_items = [it for it in corpus if it["stratum"] == "S5_neutral_role_benign"]

    # Invariant 1: stage1_id_only catches S1=100%, misses S2/S3=0%, FRR=0% on benign
    s1_preds = [p6.baseline_stage1_id_only(it) for it in s1_items]
    s2_preds = [p6.baseline_stage1_id_only(it) for it in s2_items]
    s3_preds = [p6.baseline_stage1_id_only(it) for it in s3_items]
    s4_preds = [p6.baseline_stage1_id_only(it) for it in s4_items]
    s5_preds = [p6.baseline_stage1_id_only(it) for it in s5_items]

    assert sum(s1_preds) == 240  # 100% detection on S1
    assert sum(s2_preds) == 0  # 0% detection on S2 (complete bypass)
    assert sum(s3_preds) == 0  # 0% detection on S3 (complete bypass)
    assert sum(s4_preds) == 0  # 0% false rejections on S4 hard negatives
    assert sum(s5_preds) == 0  # 0% false rejections on S5 neutral controls

    # Invariant 2: keyword_rule_naive has high S4 FRR (> 90%)
    keyword_s4_preds = [p6.baseline_keyword_rule_naive(it) for it in s4_items]
    s4_frr = sum(keyword_s4_preds) / len(s4_items)
    assert s4_frr > 0.90, f"Expected S4 false rejection rate > 90%, got {s4_frr:.2%}"

    # Invariant 3: LODO zero domain leakage verification
    domain_to_indices: dict[str, list[int]] = collections.defaultdict(list)
    for idx, item in enumerate(corpus):
        domain_to_indices[item["domain"]].append(idx)

    for test_domain in EXPECTED_DOMAINS:
        test_indices = set(domain_to_indices[test_domain])
        train_indices: set[int] = set()
        for d in EXPECTED_DOMAINS:
            if d != test_domain:
                train_indices.update(domain_to_indices[d])

        # Ensure complete partition: exactly 200 test items, 1,000 train items
        assert len(test_indices) == 200
        assert len(train_indices) == 1000
        assert test_indices.isdisjoint(train_indices), (
            f"Train and test index sets overlap for domain {test_domain}"
        )

        # Assert no domain leakage: train items contain strictly non-test domains
        test_domains = {corpus[i]["domain"] for i in test_indices}
        train_domains = {corpus[i]["domain"] for i in train_indices}
        assert test_domains == {test_domain}
        assert test_domain not in train_domains


def test_saved_json_integrity_and_zero_pii_leaks() -> None:
    """Assert saved JSON artifact integrity, provenance, size constraints, and zero PII leaks."""
    assert JSON_PATH.is_file(), f"Expected results file at {JSON_PATH}"

    # File size constraint: < 150 KB
    file_size_bytes = JSON_PATH.stat().st_size
    assert file_size_bytes < 150 * 1024, (
        f"JSON file size {file_size_bytes / 1024:.2f} KB exceeds 150 KB"
    )

    raw_text = JSON_PATH.read_text(encoding="utf-8")
    data = json.loads(raw_text)

    # Required provenance and human evaluation metadata
    assert data.get("ground_truth_provenance") == "programmatic_compositional_construction"
    assert data.get("human_raters_completed") == 0
    assert data.get("human_evaluation_status") == "AWAITING_HUMAN_RATERS"

    # Required top-level sections
    for key in (
        "benchmark_name",
        "phase",
        "protocol",
        "corpus_sha256",
        "corpus_summary",
        "deterministic_baselines",
        "statistical_tests",
        "shortcut_diagnostics",
    ):
        assert key in data, f"Missing required top-level key: {key}"

    # Baseline coverage
    expected_baselines = {
        "stage1_id_only",
        "keyword_rule_naive",
        "bm25_lexical_lodo",
        "tfidf_char_word_lodo",
        "stage1_plus_negation_rule_hybrid",
    }
    assert set(data["deterministic_baselines"].keys()) == expected_baselines

    # Statistical test consistency
    cochrans_q = data["statistical_tests"]["cochrans_q"]
    assert cochrans_q["n_items"] == 1200
    assert cochrans_q["k_arms"] == 5
    assert cochrans_q["q_stat"] > 800.0
    assert cochrans_q["p_value"] < 1e-100

    # PII and path leak audit
    forbidden_terms = [
        "/Users/",
        "/home/",
        "jangyoung",
        "Young Jang",
        "author",
        "@gmail",
        "email",
        "orcid",
        "sk-ant-",
        "Bearer ",
    ]
    detected_leaks: list[str] = []
    lower_raw = raw_text.lower()
    for term in forbidden_terms:
        if term.lower() in lower_raw:
            detected_leaks.append(term)
    assert not detected_leaks, f"Detected forbidden PII/path leaks: {detected_leaks}"
