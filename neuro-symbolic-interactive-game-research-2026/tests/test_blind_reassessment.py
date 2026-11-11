"""Offline CLI contracts using synthetic, test-only reassessment inputs."""

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "blind_reassessment.py"


class BlindReassessmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "public").mkdir()
        (self.root / "private").mkdir()
        self.source = self.root / "source.json"
        # Deliberately unrelated to research cohorts or their author judgments.
        cases = []
        for index in range(6):
            cases.append(
                {
                    "id": f"synthetic-source-{index}",
                    "rationale": f"synthetic-private-rationale-{index}",
                    "expected": "valid" if index % 2 == 0 else "invalid",
                    "WorldState": {
                        "state_id": f"synthetic-state-{index}",
                        "locations": ["harbor", "tower"],
                        "reachable_locations": ["harbor"],
                        "object_locations": {"lens": "tower"},
                        "inventory": [],
                        "facts": [f"synthetic-fact-{index}"],
                        "action_policies": {
                            "signal": {
                                "required_preconditions": ["authorized"],
                                "allowed_effects": ["signal_restored"],
                                "required_effects": ["signal_restored"],
                            }
                        },
                        "npc_knowledge": {"captain": ["tide_marks"]},
                        "forbidden_disclosures": {"captain": ["keeper_secret"]},
                        "quest_stage": index,
                    },
                    "CandidateAction": {
                        "action_id": f"synthetic-action-{index}",
                        "actor_id": "captain",
                        "action_type": "signal",
                        "preconditions": ["authorized"],
                        "effects": ["signal_restored"],
                        "required_objects": ["lens"],
                        "used_facts": [],
                        "disclosed_facts": [],
                        "required_quest_stage": index,
                        "quest_stage_effect": index + 1,
                        "narrative_text": "",
                        "metadata": {},
                    },
                }
            )
        self.source.write_text(
            json.dumps(
                {
                    "artifact_type": "independent_agent_cases",
                    "author": "synthetic-test-author",
                    "cases": cases,
                }
            ),
            encoding="utf-8",
        )
        self.source_sha256 = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.packet = self.root / "public" / "packet.json"
        self.private = self.root / "private" / "mapping.json"
        self.responses = self.root / "responses.json"
        self.output = self.root / "private" / "reconciled.json"

    def run_cli(self, *args):
        # Pin synthetic bytes only inside the child, not production's reviewed cohort.
        # A drifted source must still fail against this precomputed trust anchor.
        bootstrap = (
            "import runpy,sys; "
            "namespace=runpy.run_path(sys.argv.pop(1)); "
            "namespace['export'].__globals__['SOURCE_SHA256']=sys.argv.pop(1); "
            "raise SystemExit(namespace['main']())"
        )
        return subprocess.run(
            [sys.executable, "-c", bootstrap, str(SCRIPT), self.source_sha256, *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def export(self, seed=42, packet=None, private=None):
        return self.run_cli(
            "export",
            "--source",
            self.source,
            "--packet",
            packet or self.packet,
            "--private",
            private or self.private,
            "--seed",
            seed,
        )

    def reconcile(self, packet=None, private=None, output=None):
        return self.run_cli(
            "reconcile",
            "--source",
            self.source,
            "--packet",
            packet or self.packet,
            "--private",
            private or self.private,
            "--responses",
            self.responses,
            "--output",
            output or self.output,
        )

    def write_responses(self, responses, evaluator=None, packet=None):
        packet_bytes = (packet or self.packet).read_bytes()
        self.responses.write_text(
            json.dumps(
                {
                    "packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
                    "evaluator": evaluator or {"type": "human", "model": None},
                    "responses": responses,
                }
            ),
            encoding="utf-8",
        )

    def test_blind_packet_preserves_inputs_without_identity_or_expectations(self):
        self.assertEqual(self.export().returncode, 0)
        packet = json.loads(self.packet.read_text())
        private = json.loads(self.private.read_text())
        source = json.loads(self.source.read_text())
        by_id = {case["id"]: case for case in source["cases"]}
        assignments = {entry["blind_id"]: entry["source_id"] for entry in private["mapping"]}
        self.assertEqual(len(assignments), 6)
        self.assertEqual(set(assignments.values()), set(by_id))
        for case in packet["cases"]:
            original = by_id[assignments[case["id"]]]
            self.assertEqual(set(case), {"id", "WorldState", "CandidateAction"})
            for key, id_key in (("WorldState", "state_id"), ("CandidateAction", "action_id")):
                expected = dict(original[key])
                self.assertNotEqual(case[key][id_key], expected[id_key])
                expected[id_key] = case[key][id_key]
                self.assertEqual(case[key], expected)
            text = self.packet.read_text()
            for forbidden in (
                original["id"],
                original["WorldState"]["state_id"],
                original["CandidateAction"]["action_id"],
                original["rationale"],
            ):
                self.assertNotIn(forbidden, text)
        self.assertNotIn('"expected"', text)
        self.assertNotIn('"rationale"', text)
        self.assertNotIn('"mapping"', text)
        self.assertEqual(
            private["source_sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest()
        )
        self.assertEqual(
            private["packet_sha256"], hashlib.sha256(self.packet.read_bytes()).hexdigest()
        )

    def test_seed_is_deterministic_and_output_files_are_never_overwritten(self):
        self.assertEqual(self.export().returncode, 0)
        packet_bytes, private_bytes = self.packet.read_bytes(), self.private.read_bytes()
        p2, m2 = self.root / "public" / "p2.json", self.root / "private" / "m2.json"
        self.assertEqual(self.export(packet=p2, private=m2).returncode, 0)
        self.assertEqual(p2.read_bytes(), packet_bytes)
        self.assertEqual(m2.read_bytes(), private_bytes)
        self.assertNotEqual(self.export().returncode, 0)
        self.assertEqual(self.packet.read_bytes(), packet_bytes)
        self.assertEqual(self.private.read_bytes(), private_bytes)
        self.write_responses([])
        self.assertEqual(self.reconcile().returncode, 0)
        output_bytes = self.output.read_bytes()
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual(self.output.read_bytes(), output_bytes)

    def test_incomplete_responses_preserve_denominator_and_evaluator_kind(self):
        self.assertEqual(self.export().returncode, 0)
        ids = [case["id"] for case in json.loads(self.packet.read_text())["cases"]]
        responses = [
            {"id": ids[0], "label": "valid"},
            {"id": ids[1], "label": "unknown"},
            {"id": ids[2], "label": None},
            {"id": ids[3], "label": ""},
        ]
        for index, evaluator in enumerate(
            (
                {"type": "human", "model": None},
                {"type": "model_agent", "model": "test-model"},
                {"type": "unknown", "model": None},
            )
        ):
            with self.subTest(evaluator=evaluator):
                self.write_responses(responses, evaluator)
                output = self.root / "private" / f"result-{index}.json"
                result = self.reconcile(output=output)
                self.assertEqual(result.returncode, 0, result.stderr)
                data = json.loads(output.read_text())
                self.assertEqual(data["evaluator"], evaluator)
                self.assertEqual(
                    (data["total"], data["answered"], data["unknown"], data["missing"]),
                    (6, 1, 1, 4),
                )
                self.assertFalse(data["complete"])
                self.assertEqual(len(data["cases"]), 6)
                self.assertTrue(
                    all(
                        row["matches_author_expectation"] is None
                        for row in data["cases"]
                        if row["label"] in ("unknown", "missing")
                    )
                )

    def test_duplicate_and_unknown_response_ids_fail_without_output(self):
        self.assertEqual(self.export().returncode, 0)
        first = json.loads(self.packet.read_text())["cases"][0]["id"]
        for entries in (
            [{"id": first, "label": "valid"}, {"id": first, "label": "invalid"}],
            [{"id": "unknown-case", "label": "valid"}],
        ):
            with self.subTest(entries=entries):
                self.write_responses(entries)
                self.assertNotEqual(self.reconcile().returncode, 0)
                self.assertFalse(self.output.exists())

    def test_reconciliation_is_confined_to_private_directory(self):
        self.assertEqual(self.export().returncode, 0)
        self.write_responses([])
        for output in (self.root / "public" / "result.json", self.root / "result.json"):
            with self.subTest(output=output):
                self.assertNotEqual(self.reconcile(output=output).returncode, 0)
                self.assertFalse(output.exists())
        self.assertEqual(self.reconcile().returncode, 0)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o600)

    def test_unreviewed_source_is_rejected_before_export_writes(self):
        self.source.write_bytes(self.source.read_bytes() + b" ")
        result = self.export()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source does not match the reviewed v2 SHA-256", result.stderr)
        self.assertFalse(self.packet.exists())
        self.assertFalse(self.private.exists())

    def test_source_or_packet_drift_rejected_before_reconciliation(self):
        self.assertEqual(self.export().returncode, 0)
        self.write_responses([])
        original_source = self.source.read_bytes()
        self.source.write_bytes(original_source + b" ")
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertFalse(self.output.exists())
        self.source.write_bytes(original_source)
        self.packet.write_bytes(self.packet.read_bytes() + b" ")
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_responses_are_bound_to_packet_bytes_not_reused_across_seeds(self):
        self.assertEqual(self.export(seed=1).returncode, 0)
        ids = [c["id"] for c in json.loads(self.packet.read_text())["cases"]]
        self.write_responses([{"id": ids[0], "label": "valid"}])
        other_packet = self.root / "public" / "other.json"
        other_private = self.root / "private" / "other.json"
        self.assertEqual(
            self.export(seed=2, packet=other_packet, private=other_private).returncode, 0
        )
        self.assertNotEqual(self.packet.read_bytes(), other_packet.read_bytes())
        result = self.reconcile(packet=other_packet, private=other_private)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(self.reconcile().returncode, 0)


if __name__ == "__main__":
    unittest.main()
