import csv
import hashlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import run_conformance_pilot as pilot

from nesy_game import replay_trace_record


class ConformancePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_path = ROOT / "configs/pilot-manifest.json"
        self.manifest = pilot.load_manifest(self.manifest_path)

    def run_in_temp(self, root: Path):
        output = root / "runs"
        release = root / "release"
        result = pilot.run_pilot(self.manifest_path, output, release)
        return result, output, release

    def test_manifest_is_strict_and_covers_codes_and_boundaries(self) -> None:
        expected_codes = set(self.manifest["implemented_validator_codes"])
        fixture_codes = [
            code for fixture in self.manifest["gate_fixtures"] for code in fixture["expected_codes"]
        ]
        self.assertEqual(set(fixture_codes), expected_codes)
        self.assertEqual(len(fixture_codes), len(expected_codes))
        self.assertEqual(
            sum(not fixture["expected_codes"] for fixture in self.manifest["gate_fixtures"]),
            1,
        )

        sentinels = {item["boundary_type"]: item for item in self.manifest["boundary_sentinels"]}
        semantic = sentinels["semantic_extraction"]["candidate"]
        self.assertIn("sealed_secret", semantic["narrative_text"])
        self.assertEqual(semantic["disclosed_facts"], [])
        omitted_object = sentinels["policy_completeness"]["candidate"]
        self.assertNotIn("required_objects", omitted_object)
        extra_field = sentinels["candidate_contract_strictness"]["candidate"]
        self.assertIn("unexpected_top_level_metadata", extra_field)
        self.assertEqual(
            self.manifest["integrity_boundaries"],
            [
                {
                    "id": "repair_transition_substitution",
                    "expected_detected": False,
                    "interpretation": self.manifest["integrity_boundaries"][0]["interpretation"],
                }
            ],
        )
        for policy in self.manifest["base_state"]["action_policies"].values():
            self.assertIn("allowed_quest_stage_effects", policy)

        mutated = deepcopy(self.manifest)
        mutated["unexpected_manifest_field"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "pilot manifest fields mismatch"):
                pilot.load_manifest(path)

    def test_raw_counts_traces_and_provenance_are_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result, output, _ = self.run_in_temp(Path(directory))

            self.assertEqual(result["gate_conformance"]["raw_counts"]["fixture_count"], 13)
            self.assertEqual(result["gate_conformance"]["raw_counts"]["passed_fixture_count"], 13)
            self.assertEqual(
                result["gate_conformance"]["raw_counts"]["observed_unique_code_count"],
                12,
            )
            self.assertEqual(
                result["boundary_sentinels"]["raw_counts"],
                {
                    "sentinel_count": 3,
                    "encoded_acceptance_count": 3,
                    "passed_sentinel_count": 3,
                    "safety_pass_count": 0,
                },
            )
            repair = {
                row["arm_id"]: (row["commit_count"], row["fallback_count"])
                for row in result["repair_arms"]["raw_counts_by_arm"]
            }
            self.assertEqual(
                repair,
                {
                    "rejection_only": (0, 2),
                    "unchanged_retry": (0, 2),
                    "structured_repair": (1, 1),
                },
            )
            self.assertEqual(
                result["integrity_faults"]["raw_counts"],
                {"fault_count": 10, "detected_fault_count": 10},
            )
            integrity_by_id = {row["fault_id"]: row for row in result["integrity_faults"]["rows"]}
            intermediate = integrity_by_id["intermediate_validation_mutation"]
            self.assertEqual(intermediate["mutated_attempt_index"], 0)
            self.assertEqual(intermediate["source_trace_attempt_count"], 2)
            self.assertTrue(intermediate["source_attempt_was_nonfinal"])
            self.assertEqual(
                intermediate["fault_specification"]["source_kind"],
                "repairable_candidate_k1",
            )
            self.assertEqual(
                result["integrity_boundaries"]["raw_counts"],
                {
                    "boundary_count": 1,
                    "expected_undetected_count": 1,
                    "observed_undetected_count": 1,
                    "passed_boundary_count": 1,
                },
            )
            adapter = result["adapter_accounting"]["raw_counts"]
            self.assertEqual(adapter["assigned_case_count"], 7)
            self.assertEqual(adapter["commit_count"], 1)
            self.assertEqual(adapter["fallback_count"], 1)
            self.assertEqual(adapter["adapter_failure_count"], 5)
            self.assertEqual(adapter["input_token_count"], 210)
            self.assertEqual(adapter["output_token_count"], 42)
            self.assertEqual(
                result["accounting_guards"]["raw_counts"],
                {"guard_count": 3, "detected_guard_count": 3},
            )

            row_groups = (
                result["gate_conformance"]["rows"],
                result["boundary_sentinels"]["rows"],
                result["repair_arms"]["rows"],
                result["repair_arms"]["raw_counts_by_arm"],
                result["integrity_faults"]["rows"],
                result["integrity_boundaries"]["rows"],
                result["adapter_accounting"]["rows"],
                result["accounting_guards"]["rows"],
                result["summary_rows"],
            )
            for rows in row_groups:
                for row in rows:
                    for field in (*pilot.PROVENANCE_COLUMNS, "final_state_hash"):
                        self.assertIn(field, row)
                    for field in (
                        "config_hash",
                        "input_hash",
                        "state_hash",
                        "prior_state_hash",
                        "final_state_hash",
                    ):
                        self.assertRegex(row[field], r"^[a-f0-9]{64}$")

            for section in ("gate_conformance", "boundary_sentinels", "repair_arms"):
                for row in result[section]["rows"]:
                    replayed = replay_trace_record(row["outcome_record"])
                    replayed_hash = pilot._canonical_hash(pilot.to_jsonable(replayed))
                    self.assertTrue(row["replay_passed"])
                    self.assertEqual(replayed_hash, row["final_state_hash"])

            for row in result["boundary_sentinels"]["rows"]:
                self.assertTrue(row["observed_valid"])
                self.assertFalse(row["safety_pass"])
            integrity_boundary = result["integrity_boundaries"]["rows"][0]
            self.assertFalse(integrity_boundary["expected_detected"])
            self.assertFalse(integrity_boundary["observed_detected"])
            self.assertTrue(integrity_boundary["replay_accepted"])
            replay_trace_record(integrity_boundary["substituted_outcome_record"])
            self.assertNotIn("p_value", json.dumps(result).lower())
            self.assertNotIn("p-value", json.dumps(result).lower())

            assignments = json.loads(
                (output / "pilot-assignment-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(assignments["assignment_count"], 62)
            self.assertEqual(
                assignments["assignment_set_hash"],
                pilot._canonical_hash(assignments["expected_provenance_by_key"]),
            )

    def test_generated_artifacts_schemas_hashes_and_release_mirror(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            returned_result, output, release = self.run_in_temp(Path(directory))
            table_stems = {
                "gate-conformance": 13,
                "boundary-sentinels": 3,
                "repair-arms": 6,
                "repair-arm-summary": 3,
                "integrity-faults": 10,
                "integrity-boundaries": 1,
                "adapter-accounting": 7,
                "accounting-guards": 3,
                "pilot-summary": 16,
            }
            for stem, denominator in table_stems.items():
                for suffix in ("csv", "md", "tex"):
                    self.assertTrue((output / f"{stem}.{suffix}").is_file())
                with (output / f"{stem}.csv").open(encoding="utf-8", newline="") as handle:
                    rows = list(csv.DictReader(handle))
                self.assertEqual(len(rows), denominator)

            hash_manifest = json.loads(
                (output / "sha256-manifest.json").read_text(encoding="utf-8")
            )
            for entry in hash_manifest["artifacts"]:
                path = output / entry["path"]
                self.assertEqual(path.stat().st_size, entry["bytes"])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), entry["sha256"])
            input_paths = {entry["path"] for entry in hash_manifest["inputs"]}
            for required in (
                "uv.lock",
                "src/nesy_game/contracts.py",
                "src/nesy_game/validator.py",
                "src/nesy_game/runtime.py",
                "src/nesy_game/experiment.py",
                "game-track/schemas/experiment-record.schema.json",
            ):
                self.assertIn(required, input_paths)
            reproducibility = hash_manifest["reproducibility"]
            self.assertRegex(reproducibility["git"]["commit"], r"^[a-f0-9]{40}$")
            self.assertRegex(reproducibility["git"]["dirty_diff_hash"], r"^[a-f0-9]{64}$")
            self.assertRegex(reproducibility["runner_hash"], r"^[a-f0-9]{64}$")
            self.assertRegex(reproducibility["source_tree_hash"], r"^[a-f0-9]{64}$")
            self.assertTrue(reproducibility["environment"]["python_version"])
            self.assertTrue(reproducibility["environment"]["platform"])
            self.assertTrue(reproducibility["environment"]["uv_version"])

            for schema_name, instance_name in (
                ("pilot-input-manifest.schema.json", None),
                ("pilot-results.schema.json", "pilot-results.json"),
                ("pilot-assignment-manifest.schema.json", "pilot-assignment-manifest.json"),
            ):
                schema = json.loads((output / schema_name).read_text(encoding="utf-8"))
                self.assertFalse(schema["additionalProperties"])
                Draft202012Validator.check_schema(schema)
                if instance_name:
                    instance = json.loads((output / instance_name).read_text(encoding="utf-8"))
                    self.assertEqual(list(Draft202012Validator(schema).iter_errors(instance)), [])

            output_files = {path.name for path in output.iterdir() if path.is_file()}
            release_files = {path.name for path in release.iterdir() if path.is_file()}
            self.assertEqual(output_files, release_files)
            for name in output_files:
                self.assertEqual((output / name).read_bytes(), (release / name).read_bytes())
            results_schema = json.loads(
                (output / "pilot-results.schema.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                list(Draft202012Validator(results_schema).iter_errors(returned_result)), []
            )

            stale = release / "obsolete-table.csv"
            stale.write_text("obsolete\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unexpected stale files"):
                pilot.run_pilot(self.manifest_path, output, release)

    def test_repeated_runs_are_byte_identical_and_binding_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first, first_output, _ = self.run_in_temp(root / "first")
            _, second_output, _ = self.run_in_temp(root / "second")
            first_files = {path.name: path.read_bytes() for path in first_output.iterdir()}
            second_files = {path.name: path.read_bytes() for path in second_output.iterdir()}
            self.assertEqual(set(first_files), set(second_files))
            for name in first_files.keys() - {"sha256-manifest.json"}:
                self.assertEqual(first_files[name], second_files[name], name)
            first_hashes = json.loads(first_files["sha256-manifest.json"])
            second_hashes = json.loads(second_files["sha256-manifest.json"])
            stable_inputs = first_hashes["inputs"] == second_hashes["inputs"]
            stable_dirty_tree = (
                first_hashes["reproducibility"]["git"]["dirty_diff_hash"]
                == second_hashes["reproducibility"]["git"]["dirty_diff_hash"]
            )
            if stable_inputs and stable_dirty_tree:
                self.assertEqual(
                    first_files["sha256-manifest.json"], second_files["sha256-manifest.json"]
                )
            else:
                self.assertTrue(
                    first_hashes["reproducibility"]["source_tree_hash"]
                    != second_hashes["reproducibility"]["source_tree_hash"]
                    or not stable_dirty_tree
                )

            mutated = deepcopy(first)
            mutated["gate_conformance"]["rows"][0]["config_hash"] = "0" * 64
            state = pilot._world_state(self.manifest["base_state"])
            with self.assertRaisesRegex(ValueError, "provenance binding mismatch"):
                pilot._build_assignment_manifest(self.manifest, state, mutated)

    def test_integrity_input_hash_binds_the_concrete_repair_fixture(self) -> None:
        state = pilot._world_state(self.manifest["base_state"])
        original_rows, _ = pilot.run_integrity_faults(self.manifest, state)
        changed_manifest = deepcopy(self.manifest)
        changed_manifest["repair"]["cases"][0]["candidate"]["narrative_text"] = (
            "changed frozen repair precursor"
        )
        changed_rows, _ = pilot.run_integrity_faults(changed_manifest, state)
        original = {row["fault_id"]: row for row in original_rows}
        changed = {row["fault_id"]: row for row in changed_rows}

        for fault_id in (
            "intermediate_validation_mutation",
            "early_valid_attempt_followed_by_repair",
        ):
            self.assertNotEqual(original[fault_id]["input_hash"], changed[fault_id]["input_hash"])
            self.assertEqual(
                changed[fault_id]["fault_specification"]["source_candidate"]["narrative_text"],
                "changed frozen repair precursor",
            )
        self.assertEqual(
            original["checksum_drift"]["input_hash"], changed["checksum_drift"]["input_hash"]
        )


if __name__ == "__main__":
    unittest.main()
