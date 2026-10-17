import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import generate_npc_paper_results as generator
import validate_npc_goal_evidence as validator

from nesy_game.npc_goal import (
    REPLAY_CROSS_EPOCH_INTENT_CONTINUITY_PROVEN,
    REPLAY_INTENT_LINEAGE_SCOPE,
)


class GenerateNpcPublicationBoundaryTests(unittest.TestCase):
    """Guard the distinction between structural validity and publication admission."""

    def _report(self, packet_id, *, publishable, test_only=False, packet_dir=None):
        return {
            "packet_id": packet_id,
            "valid": True,
            "publishable": publishable,
            "errors": [],
            "source": {"test_only": test_only},
            "packet_dir": str(packet_dir or generator.PACKET),
        }

    def _load_with_reports(self, reports):
        seed = ROOT / "research/academic-pipeline/npc-goal-recovery/verified-run-005"
        with TemporaryDirectory(dir=ROOT) as temporary_directory:
            packet_dir = Path(temporary_directory) / "test-only-publication-boundary-seed"
            shutil.copytree(seed, packet_dir)
            seeded_reports = {
                packet_id: dict(report, packet_dir=str(packet_dir))
                for packet_id, report in reports.items()
            }

            def validate_packet(packet_id, root, *, packet_dir):
                report = dict(seeded_reports[packet_id])
                return report, list(report["errors"])

            with (
                patch.object(generator, "PACKET", packet_dir),
                patch.object(validator, "validate_packet", side_effect=validate_packet),
            ):
                return generator._load_packet()

    def test_screening_report_that_is_valid_but_not_publishable_is_rejected(self):
        reports = {
            "NPC-ENG1": self._report("NPC-ENG1", publishable=False),
            "NPC-SCR1": self._report("NPC-SCR1", publishable=False),
        }

        with self.assertRaisesRegex(ValueError, r"NPC-SCR1 is not publication-admissible"):
            self._load_with_reports(reports)

    def test_explicit_test_only_screening_report_is_rejected(self):
        reports = {
            "NPC-ENG1": self._report("NPC-ENG1", publishable=False),
            "NPC-SCR1": self._report("NPC-SCR1", publishable=True, test_only=True),
        }

        with self.assertRaisesRegex(
            ValueError, r"NPC-SCR1 TESTONLY evidence cannot enter manuscript generation"
        ):
            self._load_with_reports(reports)

    def test_publishable_screening_and_non_publishable_engineering_are_allowed(self):
        reports = {
            "NPC-ENG1": self._report("NPC-ENG1", publishable=False),
            "NPC-SCR1": self._report("NPC-SCR1", publishable=True),
        }

        packet = self._load_with_reports(reports)

        self.assertEqual(packet["validation_reports"]["NPC-ENG1"]["publishable"], False)
        self.assertEqual(packet["validation_reports"]["NPC-SCR1"]["publishable"], True)
        self.assertEqual(packet["aggregate"]["packet_id"], "NPC-SCR1")

    def test_replay_scope_disclosure_is_bilingual_and_names_epoch_boundary_rules(self):
        reports = {
            "NPC-ENG1": self._report("NPC-ENG1", publishable=False),
            "NPC-SCR1": self._report("NPC-SCR1", publishable=True),
        }

        packet = self._load_with_reports(reports)
        outputs = {
            "English": generator._results(packet, korean=False),
            "Korean": generator._results(packet, korean=True),
        }
        escaped_scope = REPLAY_INTENT_LINEAGE_SCOPE.replace("_", r"\_")
        escaped_continuity = str(REPLAY_CROSS_EPOCH_INTENT_CONTINUITY_PROVEN).lower()
        required_flags = (
            rf"intent\_lineage\_scope={escaped_scope}",
            rf"cross\_epoch\_intent\_continuity\_proven={escaped_continuity}",
        )
        language_tokens = {
            "English": (
                "adjacent",
                "leading",
                "positive-epoch",
                "orphan",
                "before intent commitment",
                "later intent mismatches",
            ),
            "Korean": (
                "인접한",
                "선두",
                "양의 epoch",
                "고아",
                "의도 확정 전",
                "후속 의도 불일치",
            ),
        }
        for language, output in outputs.items():
            with self.subTest(language=language):
                for token in required_flags + language_tokens[language]:
                    self.assertIn(token, output)

    def test_staged_generator_imports_staged_npc_source(self):
        with TemporaryDirectory(dir=ROOT) as temporary_directory:
            staging = Path(temporary_directory) / "staged-project"
            (staging / "scripts").mkdir(parents=True)
            (staging / "src").mkdir()
            shutil.copy2(
                ROOT / "scripts/generate_npc_paper_results.py",
                staging / "scripts/generate_npc_paper_results.py",
            )
            shutil.copytree(ROOT / "src/nesy_game", staging / "src/nesy_game")

            import_script = """
import importlib.util
import pathlib
import sys

generator_path = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("staged_generator", generator_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
import nesy_game.npc_goal as npc_goal
print(npc_goal.__file__)
"""
            completed = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    import_script,
                    str(staging / "scripts/generate_npc_paper_results.py"),
                ],
                cwd=ROOT,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            imported_source = Path(completed.stdout.strip())
            self.assertTrue(
                imported_source.is_relative_to(staging / "src"),
                f"staged generator imported editable source: {imported_source}",
            )


if __name__ == "__main__":
    unittest.main()
