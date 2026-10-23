from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
import unittest
from collections import Counter
from copy import deepcopy
from pathlib import Path

from npc_historical_fixture import archive_historical_npc_sources

P = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(P / "src"))
sys.path.insert(0, str(P / "scripts"))

from run_npc_goal_experiment import (
    DEFAULT_BUDGET,
    aggregate,
    canonical_config_hash,
    execute_assignment,
    load_cases,
    make_assignments,
    protocol_budget,
    replay_report,
    sha256_file,
    write_jsonl_preserving,
    write_sha256_manifest,
)
from validate_npc_goal_evidence import (
    EXPECTED_CLAIMS,
    _engine_reexecution_comparison,
    _replay_classes,
    digest,
    policy_hash,
    runtime_source_hashes,
    source_project_config_hash,
    validate_packet,
)

from nesy_game.npc_goal import ReplayValidator, _trace_snapshot_id

SHA256 = re.compile(r"^[0-9a-f]{64}$")
POLICY_HASH = "2e7966bf2ac6b54bfaf2db84b3f446686436bd3a1f8efea592ffa82e91249edd"


class NpcEvidenceFixtureTests(unittest.TestCase):
    def _load(self, name: str) -> dict:
        path = P / "data/fixtures/npc-goal-recovery" / name
        return json.loads(path.read_text(encoding="utf-8"))

    def test_frozen_packets_have_exact_assignments_and_regime_coverage(self) -> None:
        engineering = self._load("engineering.json")
        screening = self._load("screening.json")
        self.assertEqual(engineering["schema_version"], "npc-goal-recovery/1.0.0")
        self.assertEqual(screening["schema_version"], "npc-goal-recovery/1.0.0")
        self.assertEqual(engineering["packet_id"], "NPC-ENG1")
        self.assertEqual(screening["packet_id"], "NPC-SCR1")
        self.assertEqual(len(engineering["cases"]), 16)
        self.assertEqual(len(screening["cases"]), 12)
        self.assertEqual(
            Counter(row["regime"] for row in screening["cases"]),
            Counter(
                {
                    "static": 2,
                    "language_claim": 2,
                    "world_change": 2,
                    "stale": 2,
                    "deadline_cancel": 2,
                    "duplicate_no_route": 2,
                }
            ),
        )
        self.assertEqual(engineering["provenance"]["source_kind"], "same_model_family_auxiliary")
        self.assertEqual(screening["provenance"]["source_kind"], "same_model_family_auxiliary")
        self.assertEqual(engineering["provenance"]["independent_source_fraction"], 0)
        self.assertEqual(screening["provenance"]["independent_source_fraction"], 0)

    def test_each_case_is_public_input_bound_and_hashable_before_assignment(self) -> None:
        for packet_name in ("engineering.json", "screening.json"):
            packet = self._load(packet_name)
            self.assertEqual(packet["policy_hash"], POLICY_HASH)
            ids = set()
            seeds = set()
            for case in packet["cases"]:
                with self.subTest(packet=packet_name, case=case["id"]):
                    self.assertNotIn(case["id"], ids)
                    ids.add(case["id"])
                    self.assertNotIn(case["seed"], seeds)
                    seeds.add(case["seed"])
                    self.assertIsInstance(case["utterance"], str)
                    self.assertIn("observation", case)
                    self.assertEqual(
                        set(case["observation"]),
                        {
                            "lens_reachable",
                            "lens_carried",
                            "signal_restored",
                            "tide_lead_authorized",
                            "goal_reached",
                            "in_dialogue",
                        },
                    )
                    self.assertTrue(SHA256.fullmatch(case["state_ref"]["sha256"]))
                    self.assertEqual(case["source_kind"], "same_model_family_auxiliary")
                    reference = case["reference_intent"]
                    self.assertIn(
                        reference["label"],
                        {
                            "ASK_INFORMATION",
                            "REQUEST_DISCLOSURE",
                            "REPORT_FACT",
                            "REFUSE_HELP",
                            "AMBIGUOUS",
                            "UNKNOWN",
                        },
                    )
                    for claim in reference["claims"]:
                        self.assertIn(
                            claim["code"],
                            {
                                "LENS_REACHABLE",
                                "LENS_CARRIED",
                                "SIGNAL_RESTORED",
                                "TIDE_LEAD_AUTHORIZED",
                                "GOAL_REACHED",
                                "IN_DIALOGUE",
                                "NONE",
                            },
                        )
                        self.assertEqual(claim["state"], "UNVERIFIED")

    def test_assignment_rows_do_not_persist_raw_transient_hash_as_text(self) -> None:
        for packet_name in ("engineering.json", "screening.json"):
            packet = self._load(packet_name)
            for case in packet["cases"]:
                self.assertNotIn("raw_utterance", case)
                self.assertNotIn("user_text", case.get("trace", {}))
                self.assertNotIn("private", json.dumps(case, ensure_ascii=False).lower())

    def _verified_dir(self) -> Path:
        return P / "research/academic-pipeline/npc-goal-recovery/verified-run-006"

    def _copy_verified(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        source = self._verified_dir()
        self.assertTrue(source.is_dir(), f"missing canonical final evidence directory: {source}")
        holder = tempfile.TemporaryDirectory()
        destination = Path(holder.name) / "verified-run-006"
        shutil.copytree(source, destination)
        return holder, destination

    def _copy_portable_project(
        self, source_root: Path
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name) / "relocated-project"
        shutil.copytree(source_root, root)
        packet = root / "research/academic-pipeline/npc-goal-recovery/verified-run-006"
        shutil.copytree(self._verified_dir(), packet)
        return holder, root, packet

    def _copy_immutable_native_positive(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        """Create a private native-positive fixture from immutable005; never publication evidence."""
        immutable_root = P / "research/academic-pipeline/npc-goal-recovery/verified-run-005"
        source_manifest_path = immutable_root / "source-manifest.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        old_root = str(source_manifest["artifact_root"])
        holder = tempfile.TemporaryDirectory(dir=P)
        packet = Path(holder.name) / "native-positive-synthetic"
        shutil.copytree(immutable_root, packet)
        for result_name in ("engineering-results.jsonl", "screening-results.jsonl"):
            result_path = packet / result_name
            records = self._read_jsonl(result_path)

            def rebind(value):
                if isinstance(value, str):
                    return value.replace(old_root, str(packet))
                if isinstance(value, list):
                    return [rebind(item) for item in value]
                if isinstance(value, dict):
                    return {key: rebind(item) for key, item in value.items()}
                return value

            records = [rebind(record) for record in records]
            for record in records:
                record["record_sha256"] = digest(
                    {key: value for key, value in record.items() if key != "record_sha256"}
                )
            self._write_jsonl(result_path, records)
        replay_path = packet / "replay-results.json"
        replay_payload = rebind(json.loads(replay_path.read_text(encoding="utf-8")))
        replay_path.write_text(json.dumps(replay_payload), encoding="utf-8")
        source_manifest_path = packet / "source-manifest.json"
        source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
        current_runtime = runtime_source_hashes(P)
        source_manifest["artifact_root"] = str(packet)
        source_manifest["test_only"] = True
        source_manifest["runtime_source_hashes_before"] = current_runtime
        source_manifest["runtime_source_hashes_after"] = current_runtime
        source_manifest_path.write_text(json.dumps(source_manifest), encoding="utf-8")
        write_sha256_manifest(packet)
        for packet_id in ("NPC-ENG1", "NPC-SCR1"):
            report, errors = validate_packet(packet_id, P, packet)
            self.assertFalse(errors, errors)
            self.assertTrue(report["valid"], errors)
        return holder, packet

    def _refresh_native_packet(self, packet: Path, packet_id: str = "NPC-ENG1") -> None:
        result_name = (
            "engineering-results.jsonl" if packet_id == "NPC-ENG1" else "screening-results.jsonl"
        )
        aggregate_name = (
            "engineering-aggregate.json" if packet_id == "NPC-ENG1" else "aggregate.json"
        )
        manifest_name = (
            "engineering-assignment-manifest.json"
            if packet_id == "NPC-ENG1"
            else "screening-assignment-manifest.json"
        )
        records = self._read_jsonl(packet / result_name)
        manifest = json.loads((packet / manifest_name).read_text(encoding="utf-8"))
        existing = json.loads((packet / aggregate_name).read_text(encoding="utf-8"))
        refreshed = aggregate(
            records,
            manifest["assignments"],
            packet_id=packet_id,
            config_hash=manifest["config_hash"],
            npc_protocol_config_sha256=manifest["npc_protocol_config_sha256"],
            source_schema_sha256=manifest["source_schema_sha256"],
            source_project_config_sha256=manifest["source_project_config_sha256"],
            policy_hash=manifest["policy_hash"],
        )
        existing.update(refreshed)
        (packet / aggregate_name).write_text(json.dumps(existing), encoding="utf-8")
        replay_path = packet / "replay-results.json"
        replay_path.write_text(json.dumps(replay_report(records, packet_id)), encoding="utf-8")
        write_sha256_manifest(packet)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict]:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]

    @staticmethod
    def _write_jsonl(path: Path, rows: list[dict]) -> None:
        path.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows
            ),
            encoding="utf-8",
        )

    def _synthetic_packet(
        self, packet_id: str = "NPC-ENG1"
    ) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        holder = tempfile.TemporaryDirectory(dir=P)
        packet_dir = Path(holder.name) / "packet"
        packet_dir.mkdir()
        is_engineering = packet_id == "NPC-ENG1"
        packet_name = "engineering" if is_engineering else "screening"
        expected_count = 16 if is_engineering else 72
        cases = load_cases(
            P / f"data/fixtures/npc-goal-recovery/validated-v5/{packet_name}.json",
            packet_id,
            16 if is_engineering else 12,
        )
        config_digest = canonical_config_hash(P / "configs/npc-goal-recovery.json")
        project_digest = source_project_config_hash(P)
        schema_digest = sha256_file(P / "game-track/schemas/npc-goal-recovery.schema.json")
        frozen_policy = policy_hash(P)
        budget = protocol_budget(
            json.loads((P / "configs/npc-goal-recovery.json").read_text(encoding="utf-8"))
        )
        assignments = make_assignments(
            cases,
            packet_id=packet_id,
            config_hash=config_digest,
            npc_protocol_config_sha256=config_digest,
            source_schema_sha256=schema_digest,
            source_project_config_sha256=project_digest,
            policy_hash=frozen_policy,
            budget=budget,
        )
        cases_by_id = {case["id"]: case for case in cases}
        assignments_by_id = {assignment["assignment_id"]: assignment for assignment in assignments}
        records = [
            execute_assignment(
                cases_by_id[assignment["case_id"]],
                assignment,
                budget=DEFAULT_BUDGET,
                model=None,
                service_url=None,
                godot_binary=None,
                godot_project=P / "game-track" / "godot",
                output_dir=packet_dir,
                godot_timeout=1,
                skip_model=False,
                admission_failure={
                    "category": "engine_gate_failure",
                    "code": "synthetic_admission",
                    "error": "synthetic",
                },
            )
            for assignment in assignments
        ]
        self.assertEqual(
            [(row["assignment_id"], row["case_id"]) for row in records],
            [(assignment["assignment_id"], assignment["case_id"]) for assignment in assignments],
        )
        expected_hashes = {
            "config_hash": config_digest,
            "npc_protocol_config_sha256": config_digest,
            "source_project_config_sha256": project_digest,
            "source_schema_sha256": schema_digest,
            "policy_hash": frozen_policy,
        }
        for record in records:
            assignment = assignments_by_id[record["assignment_id"]]
            case = cases_by_id[assignment["case_id"]]
            stem = assignment["assignment_id"].replace(":", "_")
            input_ref = f"godot-input/{stem}.bootstrap.json"
            input_path = packet_dir / input_ref
            bootstrap_input = {
                "schema_version": "npc-engineering/input-1",
                "assignment_id": assignment["assignment_id"],
                "fixture_ref": case["fixture_ref"],
                "fixture_input_sha256": assignment["fixture_input_sha256"],
                "config_hash": config_digest,
                "source_hashes": expected_hashes,
                "setup_operations": case["setup_operations"],
                "seed_world_events": case["seed_world_events"],
                "in_dialogue": case.get("in_dialogue", False),
                "request_context": {},
                "decision": None,
                "mutations": case["mutations"],
            }
            input_path.parent.mkdir(parents=True, exist_ok=True)
            input_path.write_text(json.dumps(bootstrap_input), encoding="utf-8")
            input_sha = sha256_file(input_path)
            bootstrap_trace = {
                "passed": True,
                "policy_hash": frozen_policy,
                "source_hashes": expected_hashes,
                "state_ref": dict(case["state_ref"]),
            }
            sidecar_ref = input_ref + ".bootstrap.json"
            (packet_dir / sidecar_ref).write_text(json.dumps(bootstrap_trace), encoding="utf-8")
            record["engine"] = {
                "available": False,
                "status": "not_run",
                "bootstrap": {
                    "available": True,
                    "status": "completed",
                    "mode": "bootstrap",
                    "command": ["godot", "--npc-bootstrap", input_ref],
                    "input_path": input_ref,
                    "sidecar_path": sidecar_ref,
                    "input_sha256_before": input_sha,
                    "input_sha256_after": input_sha,
                    "input_bytes_preserved": True,
                    "artifact_root": str(packet_dir),
                    "trace": bootstrap_trace,
                },
                "experiment": {"available": False, "status": "not_run"},
                "replay": {
                    "available": False,
                    "status": "not_run",
                    "valid": False,
                    "rows": 0,
                    "model_calls": 0,
                },
            }
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
        manifest = {
            "schema_version": "npc-goal-recovery/evidence-1",
            "packet_id": packet_id,
            "config_hash": config_digest,
            "source_project_config_sha256": project_digest,
            "source_schema_sha256": schema_digest,
            "npc_protocol_config_sha256": config_digest,
            "policy_hash": frozen_policy,
            "budget": budget,
            "claim_boundary": dict(EXPECTED_CLAIMS),
            "assignment_count": len(assignments),
            "assignments": assignments,
        }
        manifest_name = (
            "engineering-assignment-manifest.json"
            if is_engineering
            else "screening-assignment-manifest.json"
        )
        result_name = "engineering-results.jsonl" if is_engineering else "screening-results.jsonl"
        aggregate_name = "engineering-aggregate.json" if is_engineering else "aggregate.json"
        (packet_dir / manifest_name).write_text(json.dumps(manifest), encoding="utf-8")
        write_jsonl_preserving(packet_dir / result_name, records)
        packet_aggregate = aggregate(
            records,
            assignments,
            packet_id=packet_id,
            config_hash=config_digest,
            npc_protocol_config_sha256=config_digest,
            source_schema_sha256=schema_digest,
            source_project_config_sha256=project_digest,
            policy_hash=frozen_policy,
        )
        packet_aggregate["run_mode"] = "preflight"
        packet_aggregate["cli_exec_attempt_count"] = 0
        (packet_dir / aggregate_name).write_text(json.dumps(packet_aggregate), encoding="utf-8")
        source_manifest = {
            "schema_version": "npc-goal-recovery/evidence-1",
            "config_hash": config_digest,
            "source_project_config_sha256": project_digest,
            "source_project_config_sha256_after": project_digest,
            "source_project_unchanged": True,
            "npc_protocol_config_sha256": config_digest,
            "source_schema_sha256": schema_digest,
            "policy_hash": frozen_policy,
            "test_only": True,
            "packets": [packet_id],
            "counts": {packet_id: len(assignments)},
            "run_mode": "preflight",
            "cli_exec_attempt_count": 0,
            "artifact_root": str(packet_dir),
            "runtime_source_hashes_before": runtime_source_hashes(P),
            "runtime_source_hashes_after": runtime_source_hashes(P),
            "runtime_sources_unchanged": True,
        }
        (packet_dir / "source-manifest.json").write_text(
            json.dumps(source_manifest), encoding="utf-8"
        )
        (packet_dir / "replay-results.json").write_text(
            json.dumps(replay_report(records, packet_id)), encoding="utf-8"
        )
        write_sha256_manifest(packet_dir)
        self._synthetic_result_name = result_name
        self._synthetic_aggregate_name = aggregate_name
        self._synthetic_packet_id = packet_id
        self.assertEqual(len(assignments), expected_count)
        return holder, packet_dir

    def _validate_synthetic_mutation(
        self, mutate, packet_id: str = "NPC-ENG1"
    ) -> tuple[dict, list[str]]:
        holder, packet_dir = self._synthetic_packet(packet_id)
        with holder:
            baseline_report, baseline_errors = validate_packet(packet_id, P, packet_dir)
            self.assertTrue(baseline_report["valid"], baseline_errors)
            mutate(packet_dir)
            return validate_packet(packet_id, P, packet_dir)

    def test_test_only_native_fixture_is_not_publishable(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            report, errors = validate_packet("NPC-SCR1", P, packet)
        self.assertTrue(report["valid"], errors)
        self.assertTrue(report["source"]["test_only"])
        self.assertFalse(report["publishable"], report)
        holder, packet = self._synthetic_packet("NPC-ENG1")
        with holder:
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertTrue(report["valid"], errors)
        self.assertTrue(report["source"]["test_only"])
        self.assertFalse(report["publishable"], report)

    def test_assignment_fixture_ref_cannot_rebind_case_after_rehash(self) -> None:
        def mutate(packet_dir: Path) -> None:
            manifest_path = packet_dir / "engineering-assignment-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assignment = manifest["assignments"][0]
            replacement = load_cases(
                P / "data/fixtures/npc-goal-recovery/validated-v5/engineering.json",
                "NPC-ENG1",
                16,
            )[1]
            assignment.update(
                {
                    "fixture_ref": replacement["fixture_ref"],
                    "fixture_input_sha256": digest(replacement),
                    "seed": replacement["seed"],
                    "source_kind": replacement["source_kind"],
                    "utterance_source_kind": replacement["source_kind"],
                }
            )
            assignment["assignment_key"] = digest(
                {key: value for key, value in assignment.items() if key != "assignment_key"}
            )
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            result_path = packet_dir / "engineering-results.jsonl"
            records = self._read_jsonl(result_path)
            record = records[0]
            record["fixture_ref"] = replacement["fixture_ref"]
            record["seed"] = replacement["seed"]
            record["fixture_input_sha256"] = assignment["fixture_input_sha256"]
            record["raw_utterance_sha256"] = replacement["raw_utterance_sha256"]
            bootstrap = record["engine"]["bootstrap"]
            bootstrap_input_path = packet_dir / bootstrap["input_path"]
            bootstrap_input = json.loads(bootstrap_input_path.read_text(encoding="utf-8"))
            bootstrap_input.update(
                {
                    "fixture_ref": replacement["fixture_ref"],
                    "fixture_input_sha256": assignment["fixture_input_sha256"],
                    "setup_operations": replacement["setup_operations"],
                    "seed_world_events": replacement["seed_world_events"],
                    "mutations": replacement["mutations"],
                }
            )
            bootstrap_input_path.write_text(json.dumps(bootstrap_input), encoding="utf-8")
            bootstrap["input_sha256_before"] = sha256_file(bootstrap_input_path)
            bootstrap["input_sha256_after"] = bootstrap["input_sha256_before"]
            bootstrap["trace"]["state_ref"] = deepcopy(replacement["state_ref"])
            sidecar_path = packet_dir / bootstrap["sidecar_path"]
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            sidecar["state_ref"] = deepcopy(replacement["state_ref"])
            sidecar_path.write_text(json.dumps(sidecar), encoding="utf-8")
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, records)
            write_sha256_manifest(packet_dir)

        report, errors = self._validate_synthetic_mutation(mutate)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("case_id" in error and "fixture" in error for error in errors),
            errors,
        )

    def test_completed_record_rejects_false_tamper_evidence_after_rehash(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            tamper = record["engine"]["tamper_reexecution"]
            tamper_trace = deepcopy(tamper["trace"])
            tamper_trace["errors"] = ["ACTION_NOT_APPLIED"]
            for action in tamper_trace["actions"]:
                action["codes"] = []
                action["result"]["codes"] = []
            tamper["trace"] = tamper_trace
            (packet / tamper["sidecar_path"]).write_text(json.dumps(tamper_trace), encoding="utf-8")
            record["replay"]["godot_tamper_rejected"] = False
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "completed tamper replay did not prove canonical rejection" in error
                for error in errors
            ),
            errors,
        )
        self.assertFalse(any("record schema/hash mismatch" in error for error in errors), errors)

    def test_completed_record_rejects_goal_observation_not_bound_to_native_final(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            native_trace = record["engine"]["experiment"]["trace"]
            native_final = deepcopy(native_trace["observations"][-1])
            native_final["goal_reached"] = not native_final["goal_reached"]
            record["observation_after"] = native_final
            record["goal_reached"] = native_final["goal_reached"]
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "observation_after does not bind native final observation" in error
                or "goal_reached does not bind native final observation" in error
                for error in errors
            ),
            errors,
        )
        self.assertFalse(any("record schema/hash mismatch" in error for error in errors), errors)

    def test_completed_exit_zero_tamper_without_canonical_codes_is_rejected(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            tamper = record["engine"]["tamper_reexecution"]
            tamper_trace = deepcopy(tamper["trace"])
            tamper_trace["errors"] = ["ACTION_NOT_APPLIED"]
            tamper_trace["status"] = "COMPLETED"
            tamper_trace["terminal_status"] = "COMPLETED"
            for action in tamper_trace["actions"]:
                action["codes"] = []
                action["result"]["codes"] = []
            tamper["status"] = "completed"
            tamper["returncode"] = 0
            tamper["trace"] = tamper_trace
            (packet / tamper["sidecar_path"]).write_text(json.dumps(tamper_trace), encoding="utf-8")
            record["replay"]["godot_tamper_rejected"] = True
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            write_sha256_manifest(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "completed tamper replay did not prove canonical rejection" in error
                for error in errors
            ),
            errors,
        )

    def test_completed_record_requires_native_terminal_observation(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            experiment = record["engine"]["experiment"]
            experiment_trace = deepcopy(experiment["trace"])
            experiment_trace.pop("observations", None)
            experiment_trace.pop("final_public_snapshot", None)
            for action in experiment_trace.get("actions", []):
                if isinstance(action, dict):
                    action.pop("observation_after", None)
                    action.pop("observation", None)
            experiment_trace["actions"] = []
            experiment_trace["rows"] = []
            sidecar_path = packet / experiment["sidecar_path"]
            sidecar_path.write_text(json.dumps(experiment_trace), encoding="utf-8")
            experiment["trace"] = json.loads(sidecar_path.read_text(encoding="utf-8"))
            replay = record["engine"]["replay"]
            replay_trace = deepcopy(replay["trace"])
            replay_trace.pop("observations", None)
            replay_trace.pop("final_public_snapshot", None)
            replay_trace["actions"] = []
            replay_trace["rows"] = []
            replay_sidecar_path = packet / replay["sidecar_path"]
            replay_sidecar_path.write_text(json.dumps(replay_trace), encoding="utf-8")
            replay["trace"] = json.loads(replay_sidecar_path.read_text(encoding="utf-8"))
            record["observation_after"] = deepcopy(record["observation"])
            record["goal_reached"] = record["observation_after"]["goal_reached"]
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            write_sha256_manifest(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("completed record requires native final observation" in error for error in errors),
            errors,
        )
        self.assertFalse(any("record schema/hash mismatch" in error for error in errors), errors)

    def test_malformed_native_replay_action_is_reported_not_raised(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            replay = record["engine"]["replay"]
            replay_trace = deepcopy(replay["trace"])
            replay_trace["actions"] = [None]
            replay["trace"] = replay_trace
            replay_sidecar = packet / replay["sidecar_path"]
            replay_sidecar.write_text(json.dumps(replay_trace), encoding="utf-8")
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            write_sha256_manifest(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("reexecution comparison" in error.lower() for error in errors),
            errors,
        )

    def test_native_action_requires_canonical_state_ref_after(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            for stage_name in ("experiment", "replay"):
                stage = record["engine"][stage_name]
                trace = deepcopy(stage["trace"])
                for collection_name in ("actions", "rows"):
                    for action in trace.get(collection_name, []):
                        if isinstance(action, dict) and "state_ref_after" in action:
                            action["state_ref"] = action.pop("state_ref_after")
                stage["trace"] = trace
                sidecar = packet / stage["sidecar_path"]
                sidecar.write_text(json.dumps(trace), encoding="utf-8")
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            write_sha256_manifest(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("state_ref_after" in error and "missing" in error for error in errors),
            errors,
        )

    def test_native_replay_requires_zero_returncode(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            replay = record["engine"]["replay"]
            replay["returncode"] = 1
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            write_sha256_manifest(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "native replay completion signals incomplete" in error and "returncode" in error
                for error in errors
            ),
            errors,
        )

    def test_native_replay_requires_passed_trace(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            rows = self._read_jsonl(result_path)
            record = next(row for row in rows if row.get("status") == "completed")
            replay = record["engine"]["replay"]
            replay_trace = deepcopy(replay["trace"])
            replay_trace["passed"] = False
            replay["trace"] = replay_trace
            replay_sidecar = packet / replay["sidecar_path"]
            replay_sidecar.write_text(json.dumps(replay_trace), encoding="utf-8")
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, rows)
            self._refresh_native_packet(packet)
            write_sha256_manifest(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "native replay completion signals incomplete" in error and "trace.passed" in error
                for error in errors
            ),
            errors,
        )

    def test_reexecution_comparison_rejects_non_list_action_containers(self) -> None:
        for field, malformed in (("actions", {}), ("rows", "bad")):
            with self.subTest(field=field):
                original = {"actions": [], "rows": []}
                replayed = {"actions": [], "rows": []}
                replayed[field] = malformed
                with self.assertRaisesRegex(TypeError, "engine_reexecution_actions_must_be_list"):
                    _engine_reexecution_comparison(original, replayed)

    def test_replay_classes_rejects_invalid_native_completion_metadata(self) -> None:
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            records = self._read_jsonl(packet / "engineering-results.jsonl")
            record = next(
                item
                for item in records
                if item.get("status") == "completed"
                and item.get("engine", {}).get("replay", {}).get("status") == "completed"
            )
            self.assertEqual(_replay_classes(record), ("python_eligible", "godot_eligible"))
            mutations = {
                "status_failed": lambda replay: replay.update(status="failed"),
                "returncode_nonzero": lambda replay: replay.update(returncode=7),
                "trace_not_passed": lambda replay: replay["trace"].update(passed=False),
                "input_not_preserved": lambda replay: replay.update(input_bytes_preserved=False),
            }
            for name, mutate in mutations.items():
                with self.subTest(mutation=name):
                    mutated = deepcopy(record)
                    replay = mutated["engine"]["replay"]
                    mutate(replay)
                    self.assertEqual(
                        _replay_classes(mutated),
                        ("python_eligible", "godot_failed"),
                    )

    def test_completed_action_requires_result_ack_completion_chain(self) -> None:
        """A completed native action cannot erase result/ACK rows and canonical replay rows."""
        holder, packet = self._copy_immutable_native_positive()
        with holder:
            result_path = packet / "engineering-results.jsonl"
            records = self._read_jsonl(result_path)
            index = next(
                index
                for index, item in enumerate(records)
                if item.get("status") == "completed"
                and item.get("results")
                and item.get("acks")
                and item.get("replay", {}).get("snapshot", {}).get("rows")
            )
            record = records[index]
            replay = record["replay"]
            snapshot = deepcopy(replay["snapshot"])
            snapshot["rows"] = snapshot["rows"][:2]
            snapshot["snapshot_id"] = _trace_snapshot_id(
                snapshot["session_id"], snapshot["session_epoch"], snapshot["rows"]
            )
            snapshot["cursor"] = {
                "session_id": snapshot["session_id"],
                "session_epoch": snapshot["session_epoch"],
                "row_count": len(snapshot["rows"]),
                "head_hash": snapshot["rows"][-1]["hash"],
            }
            checked = ReplayValidator.validate(
                snapshot,
                expected_session_id=str(record["request"]["session_id"]),
            )
            record["results"] = []
            record["acks"] = []
            replay["snapshot"] = snapshot
            replay["records"] = snapshot["rows"]
            replay["rows"] = checked["rows"]
            replay["python"] = {
                "content_hashes": checked["content_hashes"],
                "model_calls": 0,
                "rows": checked["rows"],
                "source": "controller.export_trace",
                "valid": True,
            }
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(result_path, records)
            self._refresh_native_packet(packet)
            report, errors = validate_packet("NPC-ENG1", P, packet)
            self.assertFalse(report["valid"])
            self.assertTrue(
                any(
                    "completed action result/ACK completion chain missing" in error
                    for error in errors
                ),
                errors,
            )

    def test_completed_stage_requires_zero_returncode(self) -> None:
        for stage in ("bootstrap", "experiment"):
            with self.subTest(stage=stage):
                holder, packet = self._copy_immutable_native_positive()
                with holder:
                    result_path = packet / "engineering-results.jsonl"
                    records = self._read_jsonl(result_path)
                    index = next(
                        index
                        for index, item in enumerate(records)
                        if item.get("status") == "completed"
                        and item.get("results")
                        and item.get("acks")
                    )
                    record = records[index]
                    self.assertEqual(record["engine"][stage]["status"], "completed")
                    self.assertEqual(record["engine"][stage]["returncode"], 0)
                    record["engine"][stage]["returncode"] = 7
                    record["record_sha256"] = digest(
                        {key: value for key, value in record.items() if key != "record_sha256"}
                    )
                    self._write_jsonl(result_path, records)
                    self._refresh_native_packet(packet)
                    report, errors = validate_packet("NPC-ENG1", P, packet)
                    self.assertFalse(report["valid"])
                    self.assertTrue(any(f"{stage} returncode" in error for error in errors), errors)

    def test_replay_report_rejects_arbitrary_counts_omitted_duplicates_and_lane_swaps(self) -> None:
        def mutate(packet_dir: Path) -> None:
            replay_path = packet_dir / "replay-results.json"
            payload = json.loads(replay_path.read_text(encoding="utf-8"))
            rows = payload["rows"]
            if self._replay_mutation == "arbitrary-count":
                payload["rows"] = rows[:-1]
            elif self._replay_mutation == "omitted-duplicate":
                payload["rows"] = rows[:-1] + [deepcopy(rows[0])]
            elif self._replay_mutation == "lane-swap":
                swapped = deepcopy(rows)
                swapped[0]["assignment_id"], swapped[1]["assignment_id"] = (
                    swapped[1]["assignment_id"],
                    swapped[0]["assignment_id"],
                )
                swapped[0]["status"] = "completed"
                swapped[0]["assigned_failure"] = False
                payload["rows"] = swapped
            else:
                raise AssertionError(f"unknown replay mutation: {self._replay_mutation}")
            replay_path.write_text(json.dumps(payload), encoding="utf-8")
            write_sha256_manifest(packet_dir)

        for variant in ("arbitrary-count", "omitted-duplicate", "lane-swap"):
            with self.subTest(variant=variant):
                self._replay_mutation = variant
                report, errors = self._validate_synthetic_mutation(mutate)
                self.assertFalse(report["valid"])
                self.assertTrue(any("replay" in error.lower() for error in errors), errors)

    def test_receipt_rejects_empty_missing_duplicate_and_relocated_entries(self) -> None:
        def mutate(packet_dir: Path) -> None:
            receipt_path = packet_dir / "sha256-manifest.json"
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            entries = receipt["files"]
            if self._receipt_mutation == "empty":
                receipt["files"] = []
            elif self._receipt_mutation == "missing":
                receipt["files"] = entries[:-1]
            elif self._receipt_mutation == "duplicate":
                receipt["files"] = entries + [deepcopy(entries[0])]
            else:
                receipt["files"] = entries + [
                    {"path": "../relocated-packet.json", "sha256": "a" * 64}
                ]
            receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

        for variant in ("empty", "missing", "duplicate", "relocated"):
            with self.subTest(variant=variant):
                self._receipt_mutation = variant
                report, errors = self._validate_synthetic_mutation(mutate)
                self.assertFalse(report["valid"])
                self.assertTrue(any("receipt" in error or "sha256" in error for error in errors))

    def test_relocated_packet_file_corruption_is_not_hidden_by_receipt(self) -> None:
        def mutate(packet_dir: Path) -> None:
            source = packet_dir / "engineering-results.jsonl"
            relocated = packet_dir / "relocated" / source.name
            relocated.parent.mkdir()
            source.replace(relocated)

        report, errors = self._validate_synthetic_mutation(mutate)
        self.assertFalse(report["valid"])
        self.assertTrue(any("receipt" in error or "missing" in error for error in errors))

    def test_publication_requires_publish_mode(self) -> None:
        def mutate(packet_dir: Path) -> None:
            for name in ("source-manifest.json", "aggregate.json"):
                path = packet_dir / name
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["run_mode"] = "dry_run"
                path.write_text(json.dumps(payload), encoding="utf-8")
            write_sha256_manifest(packet_dir)

        report, errors = self._validate_synthetic_mutation(mutate, "NPC-SCR1")
        self.assertEqual(report["run_mode"], "dry_run")
        self.assertFalse(report["publishable"])
        self.assertFalse(any("run_mode" in error for error in errors))

    def test_publication_requires_injected_execution_attempt(self) -> None:
        def mutate(packet_dir: Path) -> None:
            for name in ("source-manifest.json", "aggregate.json"):
                path = packet_dir / name
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["run_mode"] = "publish"
                payload["cli_exec_attempt_count"] = 0
                path.write_text(json.dumps(payload), encoding="utf-8")
            write_sha256_manifest(packet_dir)

        report, errors = self._validate_synthetic_mutation(mutate, "NPC-SCR1")
        self.assertEqual(report["run_mode"], "publish")
        self.assertFalse(report["publishable"])
        self.assertTrue(any("exec" in error.lower() for error in errors))

    def test_canonical_final_manifests_have_exact_arm_denominators(self) -> None:
        root = self._verified_dir()
        expected = {
            "engineering-assignment-manifest.json": ("NPC-ENG1", Counter({"R": 16})),
            "screening-assignment-manifest.json": (
                "NPC-SCR1",
                Counter({"P": 24, "R": 24, "O": 24}),
            ),
        }
        for filename, (packet_id, arms) in expected.items():
            with self.subTest(packet=packet_id):
                manifest = json.loads((root / filename).read_text(encoding="utf-8"))
                assignments = manifest["assignments"]
                self.assertEqual(manifest["packet_id"], packet_id)
                self.assertEqual(len(assignments), sum(arms.values()))
                self.assertEqual(Counter(row["arm"] for row in assignments), arms)
                self.assertTrue(
                    all(
                        str(row["fixture_ref"]).startswith(
                            "data/fixtures/npc-goal-recovery/validated-v5/"
                        )
                        for row in assignments
                    )
                )

    def test_canonical_packet_survives_relocation_and_rejects_input_substitution(self) -> None:
        canonical = self._verified_dir()
        historical_root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        archive_historical_npc_sources(P, historical_root)
        for packet_id in ("NPC-ENG1", "NPC-SCR1"):
            with self.subTest(location="canonical", packet=packet_id):
                report, errors = validate_packet(packet_id, historical_root, canonical)
                self.assertTrue(report["valid"], errors)

        holder, root, packet = self._copy_portable_project(historical_root)
        with holder:
            for packet_id in ("NPC-ENG1", "NPC-SCR1"):
                with self.subTest(location="relocated", packet=packet_id):
                    report, errors = validate_packet(packet_id, root, packet)
                    self.assertTrue(report["valid"], errors)

        negative_cases = ("actual_input", "outside_packet", "same_basename", "input_tamper")
        for variant in negative_cases:
            holder, root, packet = self._copy_portable_project(historical_root)
            with holder, self.subTest(location="relocated", variant=variant):
                if variant == "input_tamper":
                    rows = self._read_jsonl(packet / "engineering-results.jsonl")
                    record = next(
                        row
                        for row in rows
                        if row.get("status") == "completed"
                        and row.get("engine", {}).get("experiment")
                    )
                    input_path = packet / record["engine"]["experiment"]["input_path"]
                    receipt_before = (packet / "sha256-manifest.json").read_bytes()
                    input_path.write_bytes(input_path.read_bytes() + b"\n")
                    report, errors = validate_packet("NPC-ENG1", root, packet)
                    self.assertFalse(report["valid"])
                    self.assertEqual(receipt_before, (packet / "sha256-manifest.json").read_bytes())
                    self.assertTrue(
                        any(
                            "native input SHA does not match actual immutable file" in error
                            for error in errors
                        ),
                        errors,
                    )
                    continue

                rows = self._read_jsonl(packet / "engineering-results.jsonl")
                record = next(
                    row
                    for row in rows
                    if row.get("status") == "completed" and row.get("engine", {}).get("experiment")
                )
                experiment = record["engine"]["experiment"]
                input_name = Path(experiment["input_path"]).name
                command = experiment["command"]
                command_index = command.index("--npc-experiment") + 1
                if variant == "actual_input":
                    replacement = next(
                        path
                        for path in (packet / "godot-input").glob("*.experiment.json")
                        if path.name != input_name
                        and ".tamper." not in path.name
                        and "engine_fixture_reexecution" not in path.name
                    )
                elif variant == "outside_packet":
                    replacement = root / "outside-input.json"
                    replacement.write_text("{}\n", encoding="utf-8")
                else:
                    replacement = packet / "alternate" / input_name
                    replacement.parent.mkdir()
                    shutil.copy2(packet / experiment["input_path"], replacement)
                command[command_index] = str(replacement)
                record["record_sha256"] = digest(
                    {key: value for key, value in record.items() if key != "record_sha256"}
                )
                self._write_jsonl(packet / "engineering-results.jsonl", rows)
                write_sha256_manifest(packet)
                report, errors = validate_packet("NPC-ENG1", root, packet)
                self.assertFalse(report["valid"])
                self.assertTrue(
                    any(
                        "command input does not match metadata.input_path" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_dry_run_or_skip_directory_cannot_publish(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            report, errors = validate_packet("NPC-ENG1", P, Path(empty))
        self.assertFalse(report["valid"])
        self.assertTrue(any(error.startswith("missing manifest:") for error in errors))

    def test_missing_p_execution_rows_reject_publication(self) -> None:
        holder, packet_dir = self._copy_verified()
        with holder:
            path = packet_dir / "screening-results.jsonl"
            rows = self._read_jsonl(path)
            self.assertEqual(sum(row.get("arm") == "P" for row in rows), 24)
            self._write_jsonl(path, [row for row in rows if row.get("arm") != "P"])
            report, errors = validate_packet("NPC-SCR1", P, packet_dir)
        self.assertFalse(report["valid"])
        self.assertTrue(any("missing assignment results" in error for error in errors))

    def test_record_cannot_rebind_p_assignment_to_rule_arm(self) -> None:
        holder, packet_dir = self._copy_verified()
        with holder:
            path = packet_dir / "screening-results.jsonl"
            rows = self._read_jsonl(path)
            record = next(row for row in rows if row.get("arm") == "P")
            record["arm"] = "R"
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(path, rows)
            report, errors = validate_packet("NPC-SCR1", P, packet_dir)
        self.assertFalse(report["valid"])
        self.assertTrue(any("assignment identity mismatch for arm" in error for error in errors))

    def test_rehashed_aggregate_counters_cannot_fake_valid_counts(self) -> None:
        holder, packet_dir = self._copy_verified()
        with holder:
            path = packet_dir / "aggregate.json"
            aggregate = json.loads(path.read_text(encoding="utf-8"))
            aggregate["arms"]["R"]["n"] += 1
            path.write_text(json.dumps(aggregate, ensure_ascii=False), encoding="utf-8")
            report, errors = validate_packet("NPC-SCR1", P, packet_dir)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("aggregate arm R counts/statuses mismatch" in error for error in errors)
        )

    def test_embedded_native_trace_must_match_packet_scoped_sidecar(self) -> None:
        holder, packet_dir = self._copy_verified()
        with holder:
            path = packet_dir / "screening-results.jsonl"
            rows = self._read_jsonl(path)
            record = next(
                row
                for row in rows
                if row.get("status") == "completed"
                and row.get("engine", {}).get("experiment", {}).get("trace")
            )
            record["engine"]["experiment"]["trace"]["passed"] = False
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(path, rows)
            report, errors = validate_packet("NPC-SCR1", P, packet_dir)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any("experiment sidecar stage/hash gate failed" in error for error in errors)
        )

    def test_native_input_path_must_stay_inside_packet_and_bind_record(self) -> None:
        holder, packet_dir = self._copy_verified()
        with holder:
            path = packet_dir / "screening-results.jsonl"
            rows = self._read_jsonl(path)
            record = next(
                row
                for row in rows
                if row.get("status") == "completed" and row.get("engine", {}).get("experiment")
            )
            record["engine"]["experiment"]["input_path"] = "../../outside.json"
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(path, rows)
            report, errors = validate_packet("NPC-SCR1", P, packet_dir)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "experiment: native input artifact missing or outside packet" in error
                for error in errors
            )
        )

    def test_completed_record_cannot_rebind_request_id(self) -> None:
        holder, packet_dir = self._copy_verified()
        with holder:
            path = packet_dir / "screening-results.jsonl"
            rows = self._read_jsonl(path)
            record = next(
                row
                for row in rows
                if row.get("status") == "completed" and isinstance(row.get("request"), dict)
            )
            record["request"]["request_id"] = "request-mismatch"
            record["record_sha256"] = digest(
                {key: value for key, value in record.items() if key != "record_sha256"}
            )
            self._write_jsonl(path, rows)
            write_sha256_manifest(packet_dir)
            report, errors = validate_packet("NPC-SCR1", P, packet_dir)
        self.assertFalse(report["valid"])
        self.assertTrue(
            any(
                "request" in error.lower()
                and ("identity" in error.lower() or "bind" in error.lower())
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
