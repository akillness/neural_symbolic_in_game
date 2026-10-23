import json
import shutil
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from npc_historical_fixture import archive_historical_npc_sources

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_npc_paper_results as generator


class GenerateNpcPaperResultsModelCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._historical_tempdir = TemporaryDirectory(dir=ROOT)
        cls.historical_root = Path(cls._historical_tempdir.name) / "historical-source-root"
        cls.historical_root.mkdir()
        archive_historical_npc_sources(ROOT, cls.historical_root)

    @classmethod
    def tearDownClass(cls):
        cls._historical_tempdir.cleanup()

    def _load_packet_with_model_mutation(self, mutate):
        original_rows = generator._rows

        def rows(path):
            records = original_rows(path)
            if path.name == "screening-results.jsonl":
                p_rows = [row for row in records if row.get("arm") == "P"]
                mutate(p_rows)
            return records

        with patch.object(generator, "_rows", side_effect=rows):
            return generator._load_packet(self.historical_root)

    def _load_packet_with_screening_mutation(self, mutate):
        original_rows = generator._rows

        def rows(path):
            records = original_rows(path)
            if path.name == "screening-results.jsonl":
                mutate(records)
            return records

        with patch.object(generator, "_rows", side_effect=rows):
            return generator._load_packet(self.historical_root)

    @staticmethod
    def _set_model_cohort(rows, requested, returned):
        for row in rows:
            row["model"].update(requested=requested, returned=returned)

    def test_default_current_root_rejects_verified_run_source_drift(self):
        with self.assertRaisesRegex(
            ValueError,
            r"NPC-ENG1: source manifest runtime_source_hashes_before mismatch: .*; source manifest runtime_source_hashes_after mismatch:",
        ):
            generator._load_packet()

    def test_nonexistent_explicit_root_fails_without_current_root_fallback(self):
        with TemporaryDirectory(dir=ROOT) as temporary_directory:
            temporary_root = Path(temporary_directory)
            missing_root = temporary_root / "does-not-exist"
            output_dir = temporary_root / "generated"
            figures_dir = temporary_root / "figures"
            with (
                patch.object(generator, "OUT", output_dir),
                patch.object(generator, "FIGURES", figures_dir),
                self.assertRaisesRegex(
                    ValueError, rf"missing NPC evidence root: {missing_root.resolve()}"
                ),
            ):
                generator.main(missing_root)
            self.assertFalse(output_dir.exists())
            self.assertFalse(figures_dir.exists())

    def test_historical_main_preserves_numeric_outcomes_and_portable_scope_metadata(self):
        expected_outcomes = {
            "NPC-ENG1": {"valid": True, "publishable": False, "errors": []},
            "NPC-SCR1": {"valid": True, "publishable": True, "errors": []},
        }
        with TemporaryDirectory(dir=ROOT) as temporary_directory:
            output_root = Path(temporary_directory)
            output_dir = output_root / "generated"
            figures_dir = output_root / "figures"
            with (
                patch.object(generator, "OUT", output_dir),
                patch.object(generator, "FIGURES", figures_dir),
            ):
                generator.main(self.historical_root)

            reports = json.loads(
                (output_dir / "npc_validation_reports.json").read_text(encoding="utf-8")
            )

        for packet_id, outcome in expected_outcomes.items():
            with self.subTest(packet_id=packet_id):
                report = reports[packet_id]
                self.assertEqual(
                    {key: report[key] for key in ("valid", "publishable", "errors")},
                    outcome,
                )
                self.assertEqual(
                    report["validation_context"],
                    {
                        "mode": "historical-evidence-root",
                        "source_root": "explicit-archived-root",
                        "packet_scope": "dated-historical-only",
                        "current_release_authority": False,
                        "historical_reference": {"revision": "fa9fb8a", "date": "2026-10-17"},
                    },
                )
                self.assertEqual(
                    report["packet_dir"],
                    "research/academic-pipeline/npc-goal-recovery/verified-run-006",
                )
                self.assertFalse(Path(report["packet_dir"]).is_absolute())
                self.assertNotIn(str(self.historical_root), json.dumps(report))

    def test_relocated_clean_source_tree_reproduces_historical_reports_without_promotion(self):
        before = {
            path.relative_to(generator.PACKET): path.read_bytes()
            for path in generator.PACKET.rglob("*")
            if path.is_file()
        }
        with (
            TemporaryDirectory() as relocated_directory,
            TemporaryDirectory(dir=ROOT) as output_directory,
        ):
            relocated_root = Path(relocated_directory) / "clean-checkout"
            shutil.copytree(self.historical_root, relocated_root)
            output_root = Path(output_directory)
            reports = []
            fragments = []
            for index, source_root in enumerate((self.historical_root, relocated_root)):
                with (
                    patch.object(generator, "OUT", output_root / str(index) / "generated"),
                    patch.object(generator, "FIGURES", output_root / str(index) / "figures"),
                ):
                    generator.main(source_root)
                    reports.append(
                        json.loads(
                            (generator.OUT / "npc_validation_reports.json").read_text(
                                encoding="utf-8"
                            )
                        )
                    )
                    fragments.append(
                        {path.name: path.read_bytes() for path in generator.OUT.glob("*.tex")}
                    )

            self.assertEqual(reports[0], reports[1])
            self.assertEqual(fragments[0], fragments[1])
            for packet_id in ("NPC-ENG1", "NPC-SCR1"):
                self.assertTrue(reports[1][packet_id]["valid"])
                self.assertEqual(
                    reports[1][packet_id]["validation_context"]["packet_scope"],
                    "dated-historical-only",
                )
                self.assertFalse(
                    reports[1][packet_id]["validation_context"]["current_release_authority"]
                )
            self.assertNotIn(str(relocated_root), json.dumps(reports[1]))
        self.assertEqual(
            {
                path.relative_to(generator.PACKET): path.read_bytes()
                for path in generator.PACKET.rglob("*")
                if path.is_file()
            },
            before,
        )

    def test_relocated_historical_source_tampering_fails_before_writing_outputs(self):
        for relative in (
            "game-track/godot/scripts/game3d/game_3d.gd",
            "configs/npc-goal-recovery.json",
            "game-track/schemas/npc-goal-recovery.schema.json",
        ):
            with (
                self.subTest(source=relative),
                TemporaryDirectory() as relocated_directory,
                TemporaryDirectory(dir=ROOT) as output_directory,
            ):
                relocated_root = Path(relocated_directory) / "clean-checkout"
                shutil.copytree(self.historical_root, relocated_root)
                source = relocated_root / relative
                source.write_bytes(source.read_bytes() + b"\n")
                output_root = Path(output_directory)
                with (
                    patch.object(generator, "OUT", output_root / "generated"),
                    patch.object(generator, "FIGURES", output_root / "figures"),
                    self.assertRaisesRegex(ValueError, "(?i)(hash|sha|mismatch|drift)"),
                ):
                    generator.main(relocated_root)
                self.assertFalse((output_root / "generated").exists())
                self.assertFalse((output_root / "figures").exists())

    def test_explicit_historical_load_exposes_historical_context(self):
        packet = generator._load_packet(self.historical_root)
        self.assertEqual(
            packet["validation_context"],
            {
                "mode": "historical-evidence-root",
                "source_root": "explicit-archived-root",
                "packet_scope": "dated-historical-only",
                "current_release_authority": False,
                "historical_reference": {"revision": "fa9fb8a", "date": "2026-10-17"},
            },
        )
        expected_arms = {
            arm: {
                "n": 24,
                "completed_n": 20,
                "assigned_failure_n": 4,
                "goal_reached_n": 4,
                "recovery_eligible_n": 24,
                "recovery_unreachable_n": 0,
                "source_independent_n": 0,
                "terminal_status_counts": {"assigned_failure": 4, "completed": 20},
            }
            for arm in ("P", "R", "O")
        }
        self.assertEqual(
            {
                arm: {key: packet["aggregate"]["arms"][arm][key] for key in expected}
                for arm, expected in expected_arms.items()
            },
            expected_arms,
        )

    def test_uniform_null_cohort_is_accepted_and_disclosed_in_both_languages(self):
        packet = self._load_packet_with_model_mutation(
            lambda rows: self._set_model_cohort(rows, requested=None, returned=None)
        )
        metadata = packet["model_metadata"]

        self.assertIsNone(metadata["requested"])
        self.assertIsNone(metadata["returned"])
        self.assertEqual(metadata["returned_unknown_count"], metadata["cohort_size"])
        english = generator._results(packet, korean=False)
        korean = generator._results(packet, korean=True)

        self.assertIn("Requested model: unknown (null)", english)
        self.assertIn("recorded decision-model identifier: unknown (null)", english)
        self.assertIn("Actual model-family matching is unverified", english)
        self.assertIn("요청 모델: 알 수 없음 (null)", korean)
        self.assertIn("decision에 기록된 모델 식별자: 알 수 없음 (null)", korean)
        self.assertIn("실제 모델 계열 일치는 unverified(검증되지 않음)", korean)

    def test_returned_named_and_null_rows_are_disclosed_as_partial_unknown(self):
        def mutate(rows):
            self._set_model_cohort(rows, requested=None, returned=None)
            rows[0]["model"].update(returned="rev-test")

        packet = self._load_packet_with_model_mutation(mutate)
        metadata = packet["model_metadata"]
        unknown_count = metadata["cohort_size"] - 1
        self.assertEqual(metadata["returned"], "rev-test")
        self.assertEqual(metadata["returned_unknown_count"], unknown_count)

        english = generator._results(packet, korean=False)
        korean = generator._results(packet, korean=True)
        self.assertIn(
            f"recorded decision-model identifier: rev-test (partial; unknown {unknown_count}/{metadata['cohort_size']})",
            english,
        )
        self.assertIn(
            f"decision에 기록된 모델 식별자: rev-test (부분; 알 수 없음 {unknown_count}/{metadata['cohort_size']})",
            korean,
        )

    def test_mixed_or_differing_requested_cohorts_are_rejected(self):
        def mixed_requested(rows):
            self._set_model_cohort(rows, requested=None, returned=None)
            rows[0]["model"].update(requested="codex-test")

        def differing_requested(rows):
            self._set_model_cohort(rows, requested=None, returned=None)
            rows[0]["model"].update(requested="codex-a")
            rows[1]["model"].update(requested="codex-b")

        cases = {
            "mixed requested null and named": mixed_requested,
            "differing requested names": differing_requested,
        }
        for name, mutate in cases.items():
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, r"requested model cohort is mixed"),
            ):
                self._load_packet_with_model_mutation(mutate)

    def test_differing_returned_model_names_are_rejected(self):
        def mutate(rows):
            self._set_model_cohort(rows, requested=None, returned=None)
            rows[0]["model"].update(returned="rev-a")
            rows[1]["model"].update(returned="rev-b")

        with self.assertRaisesRegex(
            ValueError, r"returned model cohort has multiple named revisions"
        ):
            self._load_packet_with_model_mutation(mutate)

    def test_missing_or_malformed_model_metadata_is_rejected(self):
        cases = {
            "missing model object": lambda rows: rows[0].pop("model"),
            "missing requested field": lambda rows: rows[0]["model"].pop("requested"),
            "missing returned field": lambda rows: rows[0]["model"].pop("returned"),
            "model object is not mapping": lambda rows: rows[0].update(model="codex-test"),
            "requested name has surrounding whitespace": lambda rows: rows[0]["model"].update(
                requested=" codex-test "
            ),
            "returned metadata has wrong type": lambda rows: rows[0]["model"].update(returned=7),
        }
        for name, mutate in cases.items():
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(
                    ValueError, r"model metadata|model (?:requested|returned) malformed"
                ),
            ):
                self._load_packet_with_model_mutation(mutate)

    def test_explicit_model_names_are_latex_escaped_in_bilingual_results(self):
        def mutate(rows):
            self._set_model_cohort(rows, requested="Model_v1%safe&#", returned="rev_1")

        packet = self._load_packet_with_model_mutation(mutate)
        self.assertEqual(packet["model_metadata"]["requested"], "Model_v1%safe&#")
        self.assertEqual(packet["model_metadata"]["returned"], "rev_1")

        english = generator._results(packet, korean=False)
        korean = generator._results(packet, korean=True)
        escaped_name = r"Model\_v1\%safe\&\#"

        self.assertIn(escaped_name, english)
        self.assertIn(escaped_name, korean)
        self.assertIn(r"recorded decision-model identifier: rev\_1", english)
        self.assertIn(r"decision에 기록된 모델 식별자: rev\_1", korean)
        self.assertNotIn("provider revision: rev_1", english)
        self.assertNotIn("provider revision: rev_1", korean)
        self.assertNotIn("Model_v1%safe&#", english)
        self.assertNotIn("Model_v1%safe&#", korean)

    def test_explicit_requested_model_name_renders_without_attributing_null_return(self):
        def mutate(rows):
            self._set_model_cohort(rows, requested="gpt-5.6-sol", returned=None)

        packet = self._load_packet_with_model_mutation(mutate)
        self.assertEqual(packet["model_metadata"]["requested"], "gpt-5.6-sol")
        self.assertIsNone(packet["model_metadata"]["returned"])

        english = generator._results(packet, korean=False)
        korean = generator._results(packet, korean=True)
        self.assertIn("Requested model: gpt-5.6-sol", english)
        self.assertIn("recorded decision-model identifier: unknown (null)", english)
        self.assertIn("요청 모델: gpt-5.6-sol", korean)
        self.assertIn("decision에 기록된 모델 식별자: 알 수 없음 (null)", korean)

    def test_recorded_selector_is_not_provider_revision_and_null_revision_is_disclosed(self):
        packet = self._load_packet_with_model_mutation(
            lambda rows: self._set_model_cohort(
                rows, requested="gpt-5.6-sol", returned="gpt-5.6-sol"
            )
        )
        english = generator._results(packet, korean=False)
        korean = generator._results(packet, korean=True)

        self.assertIn("Requested model: gpt-5.6-sol", english)
        self.assertIn("recorded decision-model identifier: gpt-5.6-sol", english)
        self.assertIn("provider revision is unavailable", english)
        self.assertNotIn("provider revision: gpt-5.6-sol", english)
        self.assertIn("요청 모델: gpt-5.6-sol", korean)
        self.assertIn("decision에 기록된 모델 식별자: gpt-5.6-sol", korean)
        self.assertIn("provider revision은 사용할 수 없고 null 식별자는 미상으로 남긴다", korean)
        self.assertNotIn("provider revision: gpt-5.6-sol", korean)

    def test_stale_control_disclosure_retains_all_failures_and_counts_verified_controls(self):
        packet = generator._load_packet(self.historical_root)
        disclosure = packet["stale_disclosure"]

        self.assertEqual(disclosure["assigned_failure_rows"], 12)
        self.assertEqual(disclosure["verified_rows"], 12)
        self.assertEqual(disclosure["unclassified_rows"], 0)
        self.assertEqual(disclosure["by_arm"], {"P": 4, "R": 4, "O": 4})
        self.assertEqual(disclosure["by_control"], {"stale_revision": 6, "stale_policy": 6})
        self.assertEqual(
            disclosure["by_case"],
            {"SCR-T01": ["stale_revision"], "SCR-T02": ["stale_policy"]},
        )

        english = generator._results(packet, korean=False)
        korean = generator._results(packet, korean=True)
        self.assertIn(
            "Verified pre-authored stale-control ACK rejections are P=4, R=4, O=4 per arm", english
        )
        self.assertIn("SCR-T01 (stale\\_revision), SCR-T02 (stale\\_policy)", english)
        self.assertIn("12 instances had all corresponding negative-control gates passed", english)
        self.assertIn("negative-control gates", english)
        self.assertNotIn("expected_negative_gates", english)
        self.assertIn("not method-performance outcomes", english)
        self.assertIn("검증된 사전 작성 stale-control ACK 거부는 arm별 P=4, R=4, O=4건", korean)
        self.assertIn("SCR-T01 (stale\\_revision), SCR-T02 (stale\\_policy)", korean)
        self.assertIn("12개 인스턴스 모두 대응하는 음성 대조 gate가 모두 통과했다", korean)
        self.assertNotIn("expected_negative_gates", korean)
        self.assertIn("method-performance 결과로 해석하지 않으며", korean)

    def test_changed_ack_or_negative_gate_cannot_gain_controlled_failure_label(self):
        def mutate_ack(rows):
            row = next(
                row for row in rows if row.get("case_id") == "SCR-T01" and row.get("arm") == "P"
            )
            row["acks"][0]["body"]["error"] = "not_stale_result"

        def mutate_gate(rows):
            row = next(
                row for row in rows if row.get("case_id") == "SCR-T01" and row.get("arm") == "P"
            )
            row["engine"]["experiment"]["trace"]["expected_negative_gates"][0]["passed"] = False

        for name, mutate in (("changed ACK", mutate_ack), ("failed negative gate", mutate_gate)):
            with self.subTest(name=name):
                packet = self._load_packet_with_screening_mutation(mutate)
                disclosure = packet["stale_disclosure"]
                self.assertEqual(disclosure["assigned_failure_rows"], 12)
                self.assertEqual(disclosure["verified_rows"], 11)
                self.assertEqual(disclosure["unclassified_rows"], 1)
                self.assertEqual(disclosure["by_arm"], {"P": 3, "R": 4, "O": 4})
                english = generator._results(packet, korean=False)
                self.assertIn(
                    "11 instances had all corresponding negative-control gates passed", english
                )
                self.assertIn("other assigned failures (1) remain unclassified", english)
                self.assertNotIn("expected_negative_gates", english)

    def test_portable_report_only_normalizes_exact_packet_and_preserves_payload(self):
        expected_packet_dir = "research/academic-pipeline/npc-goal-recovery/verified-run-006"
        source_report = generator._load_packet(self.historical_root)["validation_reports"][
            "NPC-SCR1"
        ]
        same_basename_elsewhere = ROOT / "tests" / "not-the-npc-packet" / generator.PACKET.name
        cases = {
            "canonical packet": (str(generator.PACKET), expected_packet_dir),
            "same basename elsewhere": (str(same_basename_elsewhere), str(same_basename_elsewhere)),
            "missing packet_dir": (None, None),
            "non-string packet_dir": (7, 7),
        }

        for name, (packet_dir, expected) in cases.items():
            with self.subTest(name=name):
                report = deepcopy(source_report)
                if name == "missing packet_dir":
                    report.pop("packet_dir")
                else:
                    report["packet_dir"] = packet_dir
                before = deepcopy(report)

                portable = generator._portable_validation_report(report)

                self.assertEqual(report, before)
                self.assertEqual(portable["valid"], True)
                self.assertEqual(portable["publishable"], True)
                self.assertEqual(portable["errors"], [])
                if name == "missing packet_dir":
                    self.assertNotIn("packet_dir", portable)
                else:
                    self.assertEqual(portable["packet_dir"], expected)
                if name == "canonical packet":
                    self.assertFalse(Path(portable["packet_dir"]).is_absolute())
                elif name == "same basename elsewhere":
                    self.assertTrue(Path(portable["packet_dir"]).is_absolute())
                self.assertEqual(portable["source"], before["source"])
                self.assertEqual(portable["counts"], before["counts"])


if __name__ == "__main__":
    unittest.main()
