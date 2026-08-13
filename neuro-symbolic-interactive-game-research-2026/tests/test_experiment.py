import hashlib
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from nesy_game import (
    ActionPolicy,
    AdapterFailure,
    CandidateAction,
    ExperimentCase,
    ProposalResponse,
    RecordedProposalAdapter,
    WorldState,
    experiment_assignment_key,
    experiment_record_from_mapping,
    planned_experiment_assignment,
    run_experiment_case,
    summarize_experiment,
    verify_experiment_record,
    write_experiment_jsonl,
)

REPAIR_TARGET = "door_open"


class ExperimentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.state = WorldState(
            state_id="s0",
            locations=frozenset({"gate"}),
            reachable_locations=frozenset({"gate"}),
            object_locations={},
            inventory=frozenset(),
            facts=frozenset({"met_guard"}),
            action_policies={
                "REPLY": ActionPolicy(
                    frozenset({"met_guard"}),
                    frozenset({"door_open"}),
                    frozenset({"door_open"}),
                )
            },
        )
        self.valid_record = {
            "scenario_id": "S-1",
            "seed": 11,
            "provider_latency_ms": 125.0,
            "input_tokens": 100,
            "output_tokens": 20,
            "candidate": {
                "action_id": "a-1",
                "actor_id": "guard",
                "action_type": "REPLY",
                "preconditions": ["met_guard"],
                "effects": ["door_open"],
            },
        }
        schema = json.loads(
            (
                Path(__file__).parents[1] / "game-track/schemas/experiment-record.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.record_validator = Draft202012Validator(schema)

    def assert_schema_valid(self, record) -> None:
        errors = sorted(self.record_validator.iter_errors(record), key=lambda item: list(item.path))
        self.assertEqual(errors, [])

    @staticmethod
    def rehash(record: dict) -> None:
        payload = dict(record)
        payload.pop("record_hash", None)
        canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        record["record_hash"] = hashlib.sha256(canonical.encode()).hexdigest()

    def test_recorded_case_commits_and_captures_provenance(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        ticks = iter((10.0, 10.005))
        case = run_experiment_case(
            adapter,
            self.state,
            run_id="run-1",
            scenario_id="S-1",
            seed=11,
            clock=lambda: next(ticks),
        )
        self.assertEqual(case.record.status, "commit")
        self.assertAlmostEqual(case.record.runner_latency_ms, 5.0)
        self.assertEqual(case.record.provider_latency_ms, 125.0)
        self.assertEqual(case.record.arm_id, "default")
        self.assertEqual(len(case.record.controller_config_hash), 64)
        self.assertEqual(len(case.record.assignment_input_hash), 64)
        self.assertEqual(len(case.record.prior_state_hash), 64)
        self.assertEqual(len(case.record.proposal_hash), 64)
        self.assertEqual(len(case.record.final_state_hash), 64)
        self.assertIn("door_open", case.state.facts)
        self.assertEqual(case.outcome.trace_context["model_revision"], "revision")

    def test_missing_record_is_counted_and_state_stays_unchanged(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [])
        ticks = iter((3.0, 3.1))
        case = run_experiment_case(
            adapter,
            self.state,
            run_id="run-1",
            scenario_id="missing",
            seed=11,
            clock=lambda: next(ticks),
        )
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "missing_record")
        self.assertIs(case.state, self.state)
        self.assertIsNone(case.outcome)

    def test_treatment_policy_summary_keeps_failures_in_denominator(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        committed = run_experiment_case(
            adapter, self.state, run_id="run", scenario_id="S-1", seed=11
        )
        failed = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=12)
        assignments = [
            experiment_assignment_key(committed.record),
            experiment_assignment_key(failed.record),
        ]
        summary = summarize_experiment([committed.record, failed.record], assignments)
        self.assertEqual(summary["assigned_cases"], 2)
        self.assertEqual(summary["commit_rate"], 0.5)
        self.assertEqual(summary["overall_failure_rate"], 0.5)
        self.assertEqual(summary["hard_validation_failure_rate"], 0.0)
        self.assertEqual(summary["adapter_failure_rate"], 0.5)
        self.assertEqual(summary["latency_observed_cases"], 1)
        self.assertEqual(summary["provider_response_latency_p95_ms"], 125.0)

    def test_summary_rejects_duplicate_and_missing_assignments(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        assignment = experiment_assignment_key(case.record)
        with self.assertRaisesRegex(ValueError, "duplicate assigned-case"):
            summarize_experiment([case.record, case.record], [assignment])
        missing = list(assignment)
        missing[3] = 12
        with self.assertRaisesRegex(ValueError, "manifest mismatch"):
            summarize_experiment([case.record], [assignment, tuple(missing)])

    def test_assignment_key_separates_experimental_arms(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        control = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            arm_id="rejection_only",
            scenario_id="S-1",
            seed=11,
        )
        treatment = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            arm_id="structured_repair",
            scenario_id="S-1",
            seed=11,
        )
        self.assertNotEqual(
            experiment_assignment_key(control.record), experiment_assignment_key(treatment.record)
        )

    def test_assignment_key_binds_config_input_and_prior_state(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        first = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            scenario_id="S-1",
            seed=11,
            controller_config={"policy_revision": "p1"},
            assignment_input={"fixture_id": "fixture-1"},
        )
        second = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            scenario_id="S-1",
            seed=11,
            controller_config={"policy_revision": "p2"},
            assignment_input={"fixture_id": "fixture-1"},
        )
        self.assertNotEqual(
            experiment_assignment_key(first.record), experiment_assignment_key(second.record)
        )

    def test_assignment_can_be_frozen_before_execution(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        expected = planned_experiment_assignment(
            adapter,
            self.state,
            run_id="run",
            arm_id="gate",
            scenario_id="S-1",
            seed=11,
            controller_config={"policy_revision": "p1"},
            assignment_input={"fixture_id": "fixture-1"},
        )
        case = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            arm_id="gate",
            scenario_id="S-1",
            seed=11,
            controller_config={"policy_revision": "p1"},
            assignment_input={"fixture_id": "fixture-1"},
        )
        self.assertEqual(expected, experiment_assignment_key(case.record))

    def test_repairer_closure_values_are_bound_into_controller_provenance(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])

        def make_repairer(effect):
            def repairer(_state, candidate, _validation, _attempt):
                return replace(candidate, effects=frozenset({effect}))

            return repairer

        first = planned_experiment_assignment(
            adapter,
            self.state,
            run_id="run",
            scenario_id="S-1",
            seed=11,
            repairer=make_repairer("door_open"),
            repair_budget=1,
        )
        second = planned_experiment_assignment(
            adapter,
            self.state,
            run_id="run",
            scenario_id="S-1",
            seed=11,
            repairer=make_repairer("other_effect"),
            repair_budget=1,
        )
        self.assertNotEqual(first[6], second[6])

    def test_repairer_referenced_globals_are_bound_into_controller_provenance(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])

        def repairer(_state, candidate, _validation, _attempt):
            return replace(candidate, effects=frozenset({REPAIR_TARGET}))

        global REPAIR_TARGET
        original = REPAIR_TARGET
        try:
            REPAIR_TARGET = "door_open"
            first = planned_experiment_assignment(
                adapter,
                self.state,
                run_id="run",
                scenario_id="S-1",
                seed=11,
                repairer=repairer,
                repair_budget=1,
            )
            REPAIR_TARGET = "other_effect"
            second = planned_experiment_assignment(
                adapter,
                self.state,
                run_id="run",
                scenario_id="S-1",
                seed=11,
                repairer=repairer,
                repair_budget=1,
            )
        finally:
            REPAIR_TARGET = original
        self.assertNotEqual(first[6], second[6])

    def test_controller_provenance_cannot_contradict_actual_arguments(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        with self.assertRaisesRegex(ValueError, "reserved controller field"):
            run_experiment_case(
                adapter,
                self.state,
                run_id="run",
                scenario_id="S-1",
                seed=11,
                repair_budget=1,
                controller_config={"repair_budget": 0},
            )
        with self.assertRaisesRegex(ValueError, "reserved assignment field"):
            run_experiment_case(
                adapter,
                self.state,
                run_id="run",
                scenario_id="S-1",
                seed=11,
                assignment_input={"scenario_id": "other"},
            )

    def test_record_hash_binds_config_input_and_state_provenance(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            arm_id="policy_gate",
            scenario_id="S-1",
            seed=11,
            controller_config={"repair_budget": 0, "policy_revision": "p1"},
            assignment_input={"fixture_id": "fixture-1"},
        )
        record = json.loads(json.dumps(case.record.__dict__))
        for field in (
            "arm_id",
            "controller_config_hash",
            "assignment_input_hash",
            "prior_state_hash",
        ):
            tampered = dict(record)
            tampered[field] = "0" * 64 if field.endswith("_hash") else "other-arm"
            self.assertFalse(verify_experiment_record(tampered), field)

    def test_summary_separates_symbolic_fallback_from_adapter_failure(self) -> None:
        invalid = json.loads(json.dumps(self.valid_record))
        invalid["candidate"]["effects"] = ["policy_bypass"]
        adapter = RecordedProposalAdapter("model", "revision", [invalid])
        fallback = run_experiment_case(
            adapter, self.state, run_id="run", scenario_id="S-1", seed=11
        )
        assignment = experiment_assignment_key(fallback.record)
        summary = summarize_experiment([fallback.record], [assignment])
        self.assertEqual(fallback.record.status, "fallback")
        self.assertEqual(summary["overall_failure_rate"], 1.0)
        self.assertEqual(summary["hard_validation_failure_rate"], 1.0)
        self.assertEqual(summary["adapter_failure_rate"], 0.0)

    def test_repairer_exception_is_a_terminal_controller_failure(self) -> None:
        invalid = json.loads(json.dumps(self.valid_record))
        invalid["candidate"]["effects"] = ["policy_bypass"]
        adapter = RecordedProposalAdapter("model", "revision", [invalid])

        def exploding_repairer(*_args):
            raise RuntimeError("injected repair failure")

        case = run_experiment_case(
            adapter,
            self.state,
            run_id="run",
            arm_id="structured_repair",
            scenario_id="S-1",
            seed=11,
            repairer=exploding_repairer,
            repair_budget=1,
        )
        self.assertEqual(case.record.status, "controller_failure")
        self.assertEqual(case.record.failure_type, "controller_exception:RuntimeError")
        self.assertIsNone(case.outcome)
        self.assertEqual(case.record.prior_state_hash, case.record.final_state_hash)
        self.assertEqual(case.state, self.state)
        self.assert_schema_valid(json.loads(json.dumps(case.record.__dict__)))
        summary = summarize_experiment([case.record], [experiment_assignment_key(case.record)])
        self.assertEqual(summary["controller_failure_rate"], 1.0)

    def test_result_and_trace_jsonl_are_written_separately(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "results.jsonl"
            trace_path = Path(directory) / "traces.jsonl"
            write_experiment_jsonl(result_path, trace_path, case)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertEqual(result["trace_hash"], trace["trace_hash"])
        self.assertTrue(verify_experiment_record(result))

    def test_writer_rejects_same_destination_and_mismatched_case(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        first = run_experiment_case(adapter, self.state, run_id="run-1", scenario_id="S-1", seed=11)
        second = run_experiment_case(
            adapter, self.state, run_id="run-2", scenario_id="S-1", seed=11
        )
        mismatched = ExperimentCase(first.record, second.outcome, second.state)
        with tempfile.TemporaryDirectory() as directory:
            same_path = Path(directory) / "mixed.jsonl"
            with self.assertRaisesRegex(ValueError, "different files"):
                write_experiment_jsonl(same_path, same_path, first)
            with self.assertRaisesRegex(ValueError, "trace context"):
                write_experiment_jsonl(
                    Path(directory) / "results.jsonl",
                    Path(directory) / "traces.jsonl",
                    mismatched,
                )
            self.assertFalse((Path(directory) / "results.jsonl").exists())
            tampered = ExperimentCase(
                first.record,
                replace(first.outcome, attempts=999),
                first.state,
            )
            with self.assertRaisesRegex(ValueError, "hash verification failed"):
                write_experiment_jsonl(
                    Path(directory) / "results.jsonl",
                    Path(directory) / "traces.jsonl",
                    tampered,
                )

    def test_writer_preflight_and_rollback_prevent_orphan_trace(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result_directory = root / "result-directory"
            result_directory.mkdir()
            trace_path = root / "trace.jsonl"
            with self.assertRaisesRegex(ValueError, "not a regular file"):
                write_experiment_jsonl(result_directory, trace_path, case)
            self.assertFalse(trace_path.exists())

            result_path = root / "result.jsonl"
            original_open = Path.open

            def fail_result_open(path, mode="r", *args, **kwargs):
                if path == result_path and mode == "ab":
                    raise OSError("injected result write failure")
                return original_open(path, mode, *args, **kwargs)

            with (
                patch.object(Path, "open", fail_result_open),
                self.assertRaisesRegex(OSError, "injected result write failure"),
            ):
                write_experiment_jsonl(result_path, trace_path, case)
            self.assertFalse(result_path.exists())
            self.assertFalse(trace_path.exists())

    def test_trace_writer_rejects_disconnected_episode_append(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        first = run_experiment_case(adapter, self.state, run_id="run-1", scenario_id="S-1", seed=11)
        disconnected = run_experiment_case(
            adapter, self.state, run_id="run-2", scenario_id="S-1", seed=11
        )
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "results.jsonl"
            trace_path = Path(directory) / "traces.jsonl"
            write_experiment_jsonl(result_path, trace_path, first)
            with self.assertRaisesRegex(ValueError, "disconnected episode"):
                write_experiment_jsonl(result_path, trace_path, disconnected)
            self.assertEqual(len(result_path.read_text(encoding="utf-8").splitlines()), 1)

    def test_trace_writer_verifies_existing_episode_before_append(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "results.jsonl"
            trace_path = Path(directory) / "traces.jsonl"
            write_experiment_jsonl(result_path, trace_path, case)
            trace = json.loads(trace_path.read_text(encoding="utf-8"))
            trace["attempts"] = 999
            trace_path.write_text(json.dumps(trace) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash verification failed"):
                write_experiment_jsonl(result_path, trace_path, case)
            self.assertEqual(len(result_path.read_text(encoding="utf-8").splitlines()), 1)

    def test_experiment_record_hash_rejects_metric_tampering(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        record = json.loads(json.dumps(case.record.__dict__))
        self.assertTrue(verify_experiment_record(record))
        record["output_tokens"] = 9999
        self.assertFalse(verify_experiment_record(record))

    def test_semantic_record_validation_rejects_state_change_on_adapter_failure(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [])
        case = run_experiment_case(
            adapter, self.state, run_id="run", scenario_id="missing", seed=11
        )
        record = json.loads(json.dumps(case.record.__dict__))
        record["final_state_id"] = "forged-state"
        self.rehash(record)
        with self.assertRaisesRegex(ValueError, "leave state unchanged"):
            experiment_record_from_mapping(record)

    def test_external_record_loader_requires_valid_checksum(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        original = json.loads(json.dumps(case.record.__dict__))
        for replacement in (None, "", "0" * 64):
            record = dict(original)
            record["record_hash"] = replacement
            with (
                self.subTest(record_hash=replacement),
                self.assertRaisesRegex(ValueError, "checksum verification failed"),
            ):
                experiment_record_from_mapping(record)
        missing = dict(original)
        missing.pop("record_hash")
        with self.assertRaisesRegex(ValueError, "checksum verification failed"):
            experiment_record_from_mapping(missing)

    def test_recorded_adapter_defensively_copies_records(self) -> None:
        source = self.valid_record.copy()
        source["candidate"] = dict(self.valid_record["candidate"])
        adapter = RecordedProposalAdapter("model", "revision", [source])
        source["candidate"]["effects"] = ["tampered"]
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        self.assertEqual(case.record.status, "commit")

    def test_malformed_record_is_classified_not_raised(self) -> None:
        malformed = {"scenario_id": "S-1", "seed": 11, "candidate": {}}
        adapter = RecordedProposalAdapter("model", "revision", [malformed])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "parse_error")
        self.assert_schema_valid(json.loads(json.dumps(case.record.__dict__)))

    def test_string_set_field_is_parse_error_not_symbolic_failure(self) -> None:
        malformed = json.loads(json.dumps(self.valid_record))
        malformed["candidate"]["preconditions"] = "met_guard"
        adapter = RecordedProposalAdapter("model", "revision", [malformed])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "parse_error")
        assignment = experiment_assignment_key(case.record)
        summary = summarize_experiment([case.record], [assignment])
        self.assertEqual(summary["hard_validation_failure_rate"], 0.0)
        self.assertEqual(summary["adapter_failure_rate"], 1.0)

    def test_recorded_adapter_never_coerces_seed_or_accounting(self) -> None:
        fractional_seed = dict(self.valid_record, seed=11.9)
        with self.assertRaisesRegex(ValueError, "exact integer"):
            RecordedProposalAdapter("model", "revision", [fractional_seed])

        fractional_tokens = dict(self.valid_record, input_tokens=7.9)
        adapter = RecordedProposalAdapter("model", "revision", [fractional_tokens])
        case = run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11)
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "parse_error")
        self.assertEqual(case.record.input_tokens, 0)
        self.assert_schema_valid(json.loads(json.dumps(case.record.__dict__)))

    def test_runner_rejects_non_integer_seed_before_assignment(self) -> None:
        adapter = RecordedProposalAdapter("model", "revision", [self.valid_record])
        with self.assertRaisesRegex(ValueError, "exact integer"):
            run_experiment_case(adapter, self.state, run_id="run", scenario_id="S-1", seed=11.5)

    def test_timeout_from_live_adapter_boundary_is_classified(self) -> None:
        class TimeoutAdapter:
            model_id = "hosted/model"
            model_revision = "snapshot"

            def propose(self, state, scenario_id, seed):
                raise TimeoutError

        case = run_experiment_case(
            TimeoutAdapter(), self.state, run_id="run", scenario_id="S-1", seed=11
        )
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "timeout")
        self.assertEqual(case.record.prior_state_id, case.record.final_state_id)
        self.assert_schema_valid(json.loads(json.dumps(case.record.__dict__)))

    def test_empty_live_failure_code_is_normalized_and_schema_valid(self) -> None:
        class EmptyFailureAdapter:
            model_id = "hosted/model"
            model_revision = "snapshot"

            def propose(self, state, scenario_id, seed):
                raise AdapterFailure("", "provider omitted its failure code")

        case = run_experiment_case(
            EmptyFailureAdapter(), self.state, run_id="run", scenario_id="S-1", seed=11
        )
        self.assertEqual(case.record.failure_type, "adapter_failure:unclassified")
        decoded = json.loads(json.dumps(case.record.__dict__))
        self.assert_schema_valid(decoded)
        self.assertEqual(experiment_record_from_mapping(decoded), case.record)

    def test_non_json_live_candidate_is_classified_and_retained(self) -> None:
        class NonJsonAdapter:
            model_id = "hosted/model"
            model_revision = "snapshot"

            def propose(self, state, scenario_id, seed):
                candidate = CandidateAction(
                    action_id="a-live",
                    actor_id="guard",
                    action_type="REPLY",
                    preconditions=frozenset({"met_guard"}),
                    effects=frozenset({"door_open"}),
                    metadata={"bad": object()},
                )
                return ProposalResponse(candidate, 1.0, 2, 3)

        case = run_experiment_case(
            NonJsonAdapter(), self.state, run_id="run", scenario_id="S-1", seed=11
        )
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "parse_error")
        self.assert_schema_valid(json.loads(json.dumps(case.record.__dict__)))

    def test_none_adapter_response_is_classified_and_retained(self) -> None:
        class NoneAdapter:
            model_id = "hosted/model"
            model_revision = "snapshot"

            def propose(self, state, scenario_id, seed):
                return None

        case = run_experiment_case(
            NoneAdapter(), self.state, run_id="run", scenario_id="S-1", seed=11
        )
        self.assertEqual(case.record.status, "adapter_failure")
        self.assertEqual(case.record.failure_type, "adapter_contract:response_type")
        assignment = experiment_assignment_key(case.record)
        summary = summarize_experiment([case.record], [assignment])
        self.assertEqual(summary["assigned_cases"], 1)
        self.assertEqual(summary["commit_rate"], 0.0)
        self.assertEqual(summary["overall_failure_rate"], 1.0)
        self.assertEqual(summary["hard_validation_failure_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
