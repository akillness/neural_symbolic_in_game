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

P = Path(
    "/Users/jangyoung/orca/neural_symbolic_in_game/neuro-symbolic-interactive-game-research-2026"
)
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
    digest,
    policy_hash,
    runtime_source_hashes,
    source_project_config_hash,
    validate_packet,
)

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
        return P / "research/academic-pipeline/npc-goal-recovery/verified-run-003"

    def _copy_verified(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        source = self._verified_dir()
        self.assertTrue(source.is_dir(), f"missing canonical final evidence directory: {source}")
        holder = tempfile.TemporaryDirectory()
        destination = Path(holder.name) / "verified-run-003"
        shutil.copytree(source, destination)
        return holder, destination

    def _copy_portable_project(self) -> tuple[tempfile.TemporaryDirectory[str], Path, Path]:
        holder = tempfile.TemporaryDirectory()
        root = Path(holder.name) / "relocated-project"
        root.mkdir()
        packet = root / "research/academic-pipeline/npc-goal-recovery/verified-run-003"
        shutil.copytree(self._verified_dir(), packet)
        required = (
            "configs/npc-goal-recovery.json",
            "data/fixtures/npc-goal-recovery/validated-v5/engineering.json",
            "data/fixtures/npc-goal-recovery/validated-v5/screening.json",
            "game-track/schemas/npc-goal-recovery.schema.json",
            "game-track/godot/project.godot",
            "game-track/godot/data/npc-goal-recovery.json",
            "game-track/godot/data/sealed_lighthouse.json",
            "src/nesy_game/npc_goal.py",
            "scripts/codex_oauth_llm.py",
            "scripts/run_npc_goal_experiment.py",
            "game-track/godot/scripts/game3d/game_3d.gd",
            "game-track/godot/scripts/game3d/npc_agent_client.gd",
            "game-track/godot/scripts/sealed_lighthouse_machine.gd",
            "game-track/godot/scripts/canonical_state.gd",
            "game-track/godot/scenes/main_3d.tscn",
        )
        for relative in required:
            destination = root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(P / relative, destination)
        return holder, root, packet

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
        records = [
            execute_assignment(
                case,
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
            for case, assignment in zip(cases, assignments)
        ]
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
            mutate(packet_dir)
            return validate_packet(packet_id, P, packet_dir)

    def test_replay_report_rejects_arbitrary_counts_omitted_duplicates_and_lane_swaps(self) -> None:
        def mutate(packet_dir: Path) -> None:
            replay_path = packet_dir / "replay-results.json"
            payload = json.loads(replay_path.read_text(encoding="utf-8"))
            rows = payload["rows"]
            if self._replay_mutation == "arbitrary-count":
                payload["rows"] = rows[:-1]
            elif self._replay_mutation == "omitted-duplicate":
                payload["rows"] = rows[:-1] + [deepcopy(rows[0])]
            else:
                swapped = deepcopy(rows)
                swapped[0]["assignment_id"], swapped[1]["assignment_id"] = (
                    swapped[1]["assignment_id"],
                    swapped[0]["assignment_id"],
                )
                swapped[0]["status"] = "completed"
                swapped[0]["assigned_failure"] = False
                payload["rows"] = swapped
            replay_path.write_text(json.dumps(payload), encoding="utf-8")
            write_sha256_manifest(packet_dir)

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
        for packet_id in ("NPC-ENG1", "NPC-SCR1"):
            with self.subTest(location="canonical", packet=packet_id):
                report, errors = validate_packet(packet_id, P, canonical)
                self.assertTrue(report["valid"], errors)

        negative_cases = ("actual_input", "outside_packet", "same_basename", "input_tamper")
        for variant in negative_cases:
            holder, root, packet = self._copy_portable_project()
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
