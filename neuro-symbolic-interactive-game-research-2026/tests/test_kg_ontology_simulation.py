from __future__ import annotations

import copy
import json
import shutil
import sqlite3
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nesy_game.kg_ontology_simulation import (
    EXCLUDED_RESULT_CLAIMS,
    TRACKED_OUTPUTS,
    build_artifact_payloads,
    build_evaluation,
    build_sqlite,
    candidate_features,
    check_artifacts,
    run_strategy_search,
    validate_benchmark_config,
    validate_claim_boundary,
    validate_graph,
)


class KgOntologySimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix, cls.context = build_evaluation(ROOT)

    def test_graph_and_ontology_conform_without_runtime_authority(self) -> None:
        errors = validate_graph(
            self.context["graph"],
            self.context["ontology"],
            self.context["curated"],
            ROOT,
        )
        self.assertEqual(errors, [])
        self.assertEqual(self.matrix["ontology_violations"], 0)
        self.assertEqual(self.matrix["graph"]["competency_question_coverage"], 1.0)
        self.assertTrue(
            all(
                row["source_coverage"] == 1.0
                for row in self.matrix["graph"]["competency_questions"]
            )
        )
        self.assertIn("not OWL or SHACL", self.matrix["terminology"]["ontology"])

    def test_validator_predicate_mapping_is_exactly_six_of_six(self) -> None:
        coverage = self.matrix["graph"]["encoded_relation_coverage"]
        self.assertEqual(coverage["mapped"], 6)
        self.assertEqual(coverage["eligible"], 6)
        self.assertEqual(coverage["ratio"], 1.0)
        self.assertIn("not semantic completeness", coverage["interpretation"])

    def test_autoresearch_style_search_keeps_only_constrained_improvement(self) -> None:
        decisions = {trial["strategy_id"]: trial["decision"] for trial in self.matrix["trials"]}
        self.assertEqual(decisions["S0-degree-baseline"], "baseline")
        self.assertEqual(decisions["S2-typed-lexical-loose"], "keep")
        self.assertEqual(self.matrix["winner"]["strategy_id"], "S2-typed-lexical-loose")
        self.assertTrue(any(decision == "discard" for decision in decisions.values()))

        node_ids = {row["id"] for row in self.context["graph"]["nodes"]}
        leaked_holdout = copy.deepcopy(self.context["config"])
        leaked_holdout["holdout_relation_ids"] = leaked_holdout["holdout_relation_ids"][:-1]
        with self.assertRaisesRegex(ValueError, "exactly match query holdouts"):
            validate_benchmark_config(leaked_holdout, self.context["curated"], node_ids)

        reordered = copy.deepcopy(self.context["config"])
        reordered["selection_rule"]["strict_improvement_order"] = [
            "negative_nonzero_weight_count",
            "precision",
        ]
        validate_benchmark_config(reordered, self.context["curated"], node_ids)
        features = candidate_features(
            self.context["graph"], self.context["ontology"], reordered, self.context["curated"]
        )
        trials, _ = run_strategy_search(reordered, features)
        for trial in trials:
            self.assertEqual(
                trial["objective"],
                [-float(trial["metrics"]["nonzero_weight_count"]), trial["metrics"]["precision"]],
            )

    def test_winner_metrics_use_explicit_counts_and_realistic_ties(self) -> None:
        metrics = self.matrix["winner"]["metrics"]
        self.assertEqual(
            (metrics["true_positive"], metrics["false_positive"], metrics["false_negative"]),
            (6, 0, 0),
        )
        self.assertEqual((metrics["precision"], metrics["recall"], metrics["f1"]), (1.0, 1.0, 1.0))
        self.assertEqual(metrics["semantic_at_k"], 1.0)
        self.assertEqual(metrics["mrr_realistic"], 0.944444444444)
        self.assertEqual(metrics["hits_at_1"], 1.0)
        self.assertEqual(self.matrix["budget"]["candidate_scores_per_trial"], 30)
        self.assertEqual(self.matrix["budget"]["candidate_scores_total"], 210)

    def test_all_result_claims_are_fail_closed_exclusions(self) -> None:
        exclusions = self.matrix["scope"]["not_evidence_for"]
        self.assertEqual(tuple(exclusions[-5:]), EXCLUDED_RESULT_CLAIMS)
        self.assertTrue(self.matrix["scope"]["engineering_only"])
        self.assertTrue(self.matrix["scope"]["simulation_only"])
        ledger = (ROOT / "research/claim-ledger.yaml").read_text(encoding="utf-8")
        validate_claim_boundary(ledger)
        self.assertIn("non_supporting_artifacts", ledger)
        self.assertIn("research/simulation/kg-ontology/latest/evaluation-matrix.json", ledger)
        promoted = ledger.replace(
            "  - id: C-RESULT-001\n    claim: TRACE-RPG reduces hard violations versus LLM-only baselines.\n"
            "    evidence: []\n    status: TODO-RESULT",
            "  - id: C-RESULT-001\n    claim: TRACE-RPG reduces hard violations versus LLM-only baselines.\n"
            "    evidence: []\n    status: verified",
        )
        with self.assertRaisesRegex(ValueError, "result claim status drift: C-RESULT-001"):
            validate_claim_boundary(promoted)

    def test_generated_payloads_are_byte_deterministic_and_current(self) -> None:
        first, _, _ = build_artifact_payloads(ROOT)
        second, _, _ = build_artifact_payloads(ROOT)
        self.assertEqual(first, second)
        self.assertEqual(check_artifacts(ROOT, first), [])
        self.assertEqual(set(first), set(TRACKED_OUTPUTS.values()))
        for relative in TRACKED_OUTPUTS.values():
            self.assertEqual((ROOT / relative).stat().st_mode & 0o777, 0o644)

    def test_sqlite_graph_store_has_foreign_keys_and_expected_rows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "knowledge.sqlite"
            counts = build_sqlite(ROOT, database, self.matrix, self.context)
            self.assertEqual(counts["node"], self.matrix["graph"]["nodes"])
            self.assertEqual(
                counts["edge"],
                self.matrix["graph"]["reference_edges"]
                + self.matrix["graph"]["curated_typed_edges"],
            )
            self.assertEqual(counts["benchmark_query"], 6)
            self.assertEqual(counts["benchmark_candidate"], 30)
            connection = sqlite3.connect(database)
            try:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(connection.execute("PRAGMA foreign_key_check").fetchall(), [])
                candidate_foreign_keys = connection.execute(
                    "PRAGMA foreign_key_list(benchmark_candidate)"
                ).fetchall()
                self.assertTrue(any(row[2] == "benchmark_query" for row in candidate_foreign_keys))
            finally:
                connection.close()
            self.assertEqual(
                build_sqlite(ROOT, database, self.matrix, self.context)["benchmark_query"], 6
            )
            database_before_failure = database.read_bytes()
            broken_context = copy.deepcopy(self.context)
            broken_context["config"]["inputs"]["sqlite_schema"] = "broken-schema.sql"
            (Path(directory) / "broken-schema.sql").write_text(
                "CREATE TABLE broken(", encoding="utf-8"
            )
            with self.assertRaises(sqlite3.OperationalError):
                build_sqlite(Path(directory), database, self.matrix, broken_context)
            self.assertEqual(database.read_bytes(), database_before_failure)

            protected = Path(directory) / "protected.sqlite"
            protected.write_text("not a database", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to replace non-SQLite file"):
                build_sqlite(ROOT, protected, self.matrix, self.context)
            self.assertEqual(protected.read_text(encoding="utf-8"), "not a database")

    def test_svg_is_valid_and_visibly_claim_bounded(self) -> None:
        svg = ROOT / TRACKED_OUTPUTS["svg"]
        root = ET.parse(svg).getroot()
        self.assertEqual(root.attrib["width"], "1480")
        text = svg.read_text(encoding="utf-8")
        self.assertIn("[SIMULATED]", text)
        self.assertIn("C-RESULT-001…005", text)

    def test_generated_english_and_korean_tex_have_numeric_parity(self) -> None:
        english = (ROOT / TRACKED_OUTPUTS["paper_en"]).read_text(encoding="utf-8")
        korean = (ROOT / TRACKED_OUTPUTS["paper_ko"]).read_text(encoding="utf-8")
        numeric_rows = [
            "0.000 & 0.000 & 0.282 & 0.315 & 0.556",
            "1.000 & 1.000 & 0.944 & 0.131 & 1.000",
        ]
        for row in numeric_rows:
            self.assertIn(row, english)
            self.assertIn(row, korean)
        self.assertIn("or evidence for any efficacy claim.", english)
        self.assertIn("어떤 효능 주장의 근거도 아니다.", korean)
        for claim_id in EXCLUDED_RESULT_CLAIMS:
            self.assertNotIn(claim_id, english)
            self.assertNotIn(claim_id, korean)
        self.assertIn("S2 typed-lexical & ", english)
        self.assertNotIn("OKF", korean)

    def test_claim_boundary_drift_fails_before_evaluation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary_root = Path(directory)
            shutil.copytree(ROOT / "knowledge", temporary_root / "knowledge")
            (temporary_root / "configs").mkdir()
            (temporary_root / "research").mkdir()
            shutil.copy2(
                ROOT / "research/claim-ledger.yaml",
                temporary_root / "research/claim-ledger.yaml",
            )
            shutil.copy2(
                ROOT / "research/source-ledger.yaml",
                temporary_root / "research/source-ledger.yaml",
            )
            config = json.loads(
                (ROOT / "configs/kg-ontology-simulation.json").read_text(encoding="utf-8")
            )
            config["scope"]["not_evidence_for"][-1] = "C-RESULT-999"
            (temporary_root / "configs/kg-ontology-simulation.json").write_text(
                json.dumps(config, ensure_ascii=False), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "C-RESULT exclusion contract drift"):
                build_evaluation(temporary_root)


if __name__ == "__main__":
    unittest.main()
