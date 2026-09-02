import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_paper_results as generator


class GeneratePaperResultsTests(unittest.TestCase):
    def test_guided_repair_code_count_drift_fails_closed(self) -> None:
        data = json.loads(generator.RESULTS_PATH.read_text(encoding="utf-8"))
        guided_commit = next(
            row
            for row in data["repair_arms"]["rows"]
            if row["arm_id"] == "guided_repair" and row["final_status"] == "commit"
        )
        guided_commit["initial_error_count"] += 1
        with self.assertRaisesRegex(ValueError, "initial validator-code count drift"):
            generator._guided_commit_error_codes(data)

    def test_live_packet_generation_and_claim_boundary_fail_closed(self) -> None:
        packet = generator._load_live_packet()
        self.assertEqual(set(packet["current"]), {key for key, _ in generator.LIVE_CURRENT_CELLS})
        self.assertIn("5/5", generator._live_result_text(packet, korean=False))
        self.assertIn("15/15", generator._live_result_text(packet, korean=True))
        self.assertIn("pilot-only", generator._live_result_text(packet, korean=False))
        self.assertNotIn("C-PILOT", generator._live_result_text(packet, korean=False))
        self.assertIn("0/5", generator._live_tables(packet, korean=False))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "generated"
            with patch.object(generator, "OUT", output):
                generator.main()
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "pilot_results_en.tex",
                    "pilot_results_ko.tex",
                    "pilot_tables_en.tex",
                    "pilot_tables_ko.tex",
                    "live_pilot_results_en.tex",
                    "live_pilot_results_ko.tex",
                    "live_pilot_tables_en.tex",
                    "live_pilot_tables_ko.tex",
                    "contribution_map_en.tex",
                    "contribution_map_ko.tex",
                    "evidence_lanes_en.tex",
                    "evidence_lanes_ko.tex",
                },
            )
            contribution_map = (output / "contribution_map_en.tex").read_text(encoding="utf-8")
            self.assertIn(r"\label{tab:contribution-map}", contribution_map)
            for contribution_id in ("C1", "C2", "C3", "C4", "C5"):
                self.assertIn(f"{contribution_id} & ", contribution_map)
            lanes = (output / "evidence_lanes_ko.tex").read_text(encoding="utf-8")
            self.assertIn(r"\label{tab:evidence-lanes}", lanes)
            for lane_id in ("E1", "E2", "E3", "ENG1"):
                self.assertIn(f"{lane_id} & ", lanes)
            self.assertIn(
                r"\allowbreak{}", (output / "pilot_results_en.tex").read_text(encoding="utf-8")
            )

        with tempfile.TemporaryDirectory() as directory:
            live_root = Path(directory) / "rq2-live-pilot"
            shutil.copytree(generator.LIVE_ROOT, live_root)
            manifest_path = live_root / "promotion-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["supported_claim_ids"] = ["C-RESULT-003"]
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            root_patch = patch.object(generator, "LIVE_ROOT", live_root)
            manifest_patch = patch.object(generator, "LIVE_MANIFEST_PATH", manifest_path)
            with (
                root_patch,
                manifest_patch,
                self.assertRaisesRegex(ValueError, "supported claim drift"),
            ):
                generator._load_live_packet()


if __name__ == "__main__":
    unittest.main()
