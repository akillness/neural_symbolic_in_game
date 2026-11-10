from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import generate_runtime_comparison_publication as publication

_DIGEST = "a" * 64


def _row(
    row_id: int,
    selector: str,
    representation: str,
    repeat: int,
    *,
    executed: bool | None,
    status: str,
    failure_reason: str | None,
    primary_success: bool,
    goal_reached: bool | None,
    host_invocations_observed: int,
    repair_calls: int | None,
    initial_proposal_failures: int | None,
    timeout_calls: int | None,
    committed_transitions: int | None,
    unsafe_committed_transitions: int | None,
    safety_status: str,
    replay_valid: bool | None,
    engine_reexecution_valid: bool | None,
    elapsed_seconds: float | None,
    preparation_seconds: float | None,
    outgoing_requests_bound: bool | None,
    episode_sha256: str | None,
) -> dict[str, object]:
    engine_status = (
        "VALID"
        if engine_reexecution_valid is True
        else ("INVALID" if engine_reexecution_valid is False else "NOT_OBSERVED")
    )
    return {
        "row_id": row_id,
        "planned_id": f"{publication.QUEST_ID}:{selector}:{representation}:repeat-{repeat}",
        "requested_selector": selector,
        "representation": representation,
        "repeat": repeat,
        "assigned": True,
        "executed": executed,
        "status": status,
        "failure_reason": failure_reason,
        "primary_success": primary_success,
        "goal_reached": goal_reached,
        "host_invocations_observed": host_invocations_observed,
        "provider_request_count": None,
        "repair_calls": repair_calls,
        "initial_proposal_failures": initial_proposal_failures,
        "timeout_calls": timeout_calls,
        "committed_transitions": committed_transitions,
        "unsafe_committed_transitions": unsafe_committed_transitions,
        "safety_status": safety_status,
        "replay_valid": replay_valid,
        "engine_reexecution_valid": engine_reexecution_valid,
        "engine_reexecution_status": engine_status,
        "elapsed_seconds": elapsed_seconds,
        "preparation_seconds": preparation_seconds,
        "outgoing_requests_bound": outgoing_requests_bound,
        "provider_identity": None,
        "provider_revision": None,
        "cost_usd": None,
        "source_manifest_sha256": _DIGEST,
        "episode_sha256": episode_sha256,
        "result_sha256": _DIGEST,
    }


def _synthetic_packet() -> dict[str, object]:
    rows = [
        _row(
            1,
            "gpt-6.1-sol",
            "general_rule",
            1,
            executed=None,
            status="technical_failure",
            failure_reason="harness_json_serialization_failure",
            primary_success=False,
            goal_reached=None,
            host_invocations_observed=0,
            repair_calls=None,
            initial_proposal_failures=None,
            timeout_calls=None,
            committed_transitions=None,
            unsafe_committed_transitions=None,
            safety_status="NOT_OBSERVED",
            replay_valid=None,
            engine_reexecution_valid=None,
            elapsed_seconds=None,
            preparation_seconds=None,
            outgoing_requests_bound=None,
            episode_sha256=None,
        ),
        _row(
            2,
            "gpt-6.1-sol",
            "general_rule",
            2,
            executed=True,
            status="success",
            failure_reason=None,
            primary_success=True,
            goal_reached=True,
            host_invocations_observed=3,
            repair_calls=1,
            initial_proposal_failures=0,
            timeout_calls=0,
            committed_transitions=2,
            unsafe_committed_transitions=1,
            safety_status="FAIL",
            replay_valid=False,
            engine_reexecution_valid=False,
            elapsed_seconds=12.0,
            preparation_seconds=2.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
        _row(
            3,
            "gpt-6.1-sol",
            "ontology",
            1,
            executed=True,
            status="failure",
            failure_reason="goal_not_reached",
            primary_success=False,
            goal_reached=False,
            host_invocations_observed=2,
            repair_calls=0,
            initial_proposal_failures=1,
            timeout_calls=0,
            committed_transitions=1,
            unsafe_committed_transitions=0,
            safety_status="PASS",
            replay_valid=False,
            engine_reexecution_valid=True,
            elapsed_seconds=20.0,
            preparation_seconds=2.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
        _row(
            4,
            "gpt-6.1-sol",
            "ontology",
            2,
            executed=True,
            status="failure",
            failure_reason="response_timeout",
            primary_success=False,
            goal_reached=False,
            host_invocations_observed=12,
            repair_calls=0,
            initial_proposal_failures=0,
            timeout_calls=1,
            committed_transitions=0,
            unsafe_committed_transitions=0,
            safety_status="NO_COMMIT_OBSERVED",
            replay_valid=True,
            engine_reexecution_valid=False,
            elapsed_seconds=60.0,
            preparation_seconds=2.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
        _row(
            5,
            "gpt-5.6-sol",
            "general_rule",
            1,
            executed=True,
            status="success",
            failure_reason=None,
            primary_success=True,
            goal_reached=True,
            host_invocations_observed=4,
            repair_calls=0,
            initial_proposal_failures=0,
            timeout_calls=0,
            committed_transitions=1,
            unsafe_committed_transitions=0,
            safety_status="PASS",
            replay_valid=True,
            engine_reexecution_valid=True,
            elapsed_seconds=30.0,
            preparation_seconds=3.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
        _row(
            6,
            "gpt-5.6-sol",
            "general_rule",
            2,
            executed=True,
            status="failure",
            failure_reason="unsafe_transition",
            primary_success=False,
            goal_reached=False,
            host_invocations_observed=1,
            repair_calls=1,
            initial_proposal_failures=0,
            timeout_calls=0,
            committed_transitions=1,
            unsafe_committed_transitions=1,
            safety_status="FAIL",
            replay_valid=False,
            engine_reexecution_valid=False,
            elapsed_seconds=25.0,
            preparation_seconds=3.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
        _row(
            7,
            "gpt-5.6-sol",
            "ontology",
            1,
            executed=True,
            status="success",
            failure_reason=None,
            primary_success=True,
            goal_reached=True,
            host_invocations_observed=2,
            repair_calls=0,
            initial_proposal_failures=0,
            timeout_calls=0,
            committed_transitions=0,
            unsafe_committed_transitions=0,
            safety_status="PASS",
            replay_valid=True,
            engine_reexecution_valid=False,
            elapsed_seconds=40.0,
            preparation_seconds=4.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
        _row(
            8,
            "gpt-5.6-sol",
            "ontology",
            2,
            executed=True,
            status="success",
            failure_reason=None,
            primary_success=True,
            goal_reached=True,
            host_invocations_observed=1,
            repair_calls=0,
            initial_proposal_failures=0,
            timeout_calls=0,
            committed_transitions=1,
            unsafe_committed_transitions=0,
            safety_status="FAIL",
            replay_valid=False,
            engine_reexecution_valid=True,
            elapsed_seconds=10.0,
            preparation_seconds=1.0,
            outgoing_requests_bound=True,
            episode_sha256=_DIGEST,
        ),
    ]
    return {
        "schema_version": publication.SCHEMA_VERSION,
        "study_id": publication.STUDY_ID,
        "status": publication.REQUIRED_STATUS,
        "scope": {
            "quest_id": publication.QUEST_ID,
            "selectors": list(publication.SELECTORS),
            "representations": list(publication.REPRESENTATIONS),
            "repeats": 2,
            "seed": publication.SEED,
            "concurrency": 1,
            "episode_wall_seconds": 180,
            "response_seconds": 60,
            "maximum_host_invocations": 12,
            "maximum_repairs_per_decision": 2,
        },
        "rows": rows,
    }


class RuntimeComparisonPublicationTests(unittest.TestCase):
    def _write_packet(self, directory: Path, packet: dict[str, object]) -> Path:
        path = directory / "results.json"
        path.write_text(json.dumps(packet, allow_nan=True), encoding="utf-8")
        return path

    def test_complete_eight_row_packet_is_accepted_and_aggregated_from_rows(self) -> None:
        """The public packet admits exactly eight frozen rows and derives denominators from them."""
        packet = _synthetic_packet()
        loaded = publication.validate_public_results(packet)

        aggregate = publication.compute_aggregates(loaded)
        overall = aggregate["overall"]
        self.assertEqual([row["row_id"] for row in loaded["rows"]], list(range(1, 9)))
        self.assertEqual(
            tuple(row["planned_id"] for row in loaded["rows"]), publication.expected_planned_ids()
        )
        self.assertEqual(overall["assigned"], 8)
        self.assertEqual(overall["system_successes"], 4)
        self.assertEqual(overall["observed_executions"], 7)
        self.assertEqual(overall["host_invocations"], 25)
        self.assertEqual(
            overall["status_counts"], {"success": 4, "failure": 3, "technical_failure": 1}
        )
        self.assertEqual(overall["durations"]["elapsed_seconds"]["n"], 7)
        self.assertEqual(overall["repairs"], {"sum": 2, "observed_rows": 7})
        self.assertEqual(
            overall["transitions"], {"committed": 6, "unsafe_committed": 2, "observed_rows": 7}
        )
        self.assertEqual(overall["initial_proposal_failures"], {"sum": 1, "observed_rows": 7})
        self.assertEqual(overall["timeout_calls"], {"sum": 1, "observed_rows": 7})

    def test_retained_failure_timeout_and_null_observations_are_reportable(self) -> None:
        """Technical failure, timeout, unsafe outcome, and replay failures remain separate public observations."""
        packet = _synthetic_packet()
        loaded = publication.validate_public_results(packet)
        first, timeout = loaded["rows"][0], loaded["rows"][3]
        self.assertEqual(first["status"], "technical_failure")
        self.assertEqual(first["failure_reason"], "harness_json_serialization_failure")
        self.assertIsNone(first["executed"])
        self.assertEqual(first["host_invocations_observed"], 0)
        self.assertIsNone(first["goal_reached"])
        self.assertEqual(timeout["failure_reason"], "response_timeout")
        rendered = publication.render_results_fragment(loaded)
        self.assertIn("not attributed to GPT-6.1 capability", rendered)
        self.assertIn("response-timeout failure", rendered)
        self.assertEqual(timeout["timeout_calls"], 1)
        self.assertEqual(timeout["elapsed_seconds"], 60.0)
        self.assertEqual(timeout["host_invocations_observed"], 12)

        aggregate = publication.compute_aggregates(loaded)["overall"]
        self.assertEqual(aggregate["replay_valid"], {"true": 3, "false": 4, "unknown": 1})
        self.assertEqual(
            aggregate["engine_reexecution_status"],
            {"VALID": 3, "INVALID": 4, "NOT_RUN": 0, "NOT_OBSERVED": 1},
        )
        self.assertEqual(aggregate["replay_valid"]["unknown"], 1)
        self.assertIsNone(first["provider_request_count"])
        self.assertIsNone(first["provider_identity"])
        self.assertIsNone(first["provider_revision"])
        self.assertIsNone(first["cost_usd"])

    def test_missing_duplicate_drifted_and_incomplete_packets_fail_closed(self) -> None:
        """Missing, duplicate, schema-drifted, and incomplete public inputs cannot reach rendering."""
        mutations: list[tuple[str, object]] = []
        missing_row = _synthetic_packet()
        missing_row["rows"] = missing_row["rows"][:-1]
        mutations.append(("missing row", missing_row))
        duplicate_row = _synthetic_packet()
        duplicate_row["rows"][1]["row_id"] = 1
        mutations.append(("duplicate row id", duplicate_row))
        drifted_id = _synthetic_packet()
        drifted_id["rows"][1]["planned_id"] = (
            "sealed-lighthouse-v1:gpt-5.6-sol:general_rule:repeat-2"
        )
        mutations.append(("drifted planned id", drifted_id))
        drifted_field = _synthetic_packet()
        drifted_field["rows"][1]["unexpected"] = "drift"
        mutations.append(("drifted row fields", drifted_field))
        incomplete_status = _synthetic_packet()
        incomplete_status["status"] = "running"
        mutations.append(("incomplete status", incomplete_status))

        for name, packet in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_public_results(packet)

    def test_type_time_and_contradiction_boundaries_are_rejected(self) -> None:
        """Booleans are not numbers, times are finite/nonnegative, and contradictory row fields fail validation."""
        mutations: list[tuple[str, object]] = []
        boolean_count = _synthetic_packet()
        boolean_count["rows"][1]["host_invocations_observed"] = True
        mutations.append(("boolean host count", boolean_count))
        boolean_goal = _synthetic_packet()
        boolean_goal["rows"][1]["goal_reached"] = 1
        mutations.append(("numeric goal flag", boolean_goal))
        negative_time = _synthetic_packet()
        negative_time["rows"][1]["elapsed_seconds"] = -0.1
        mutations.append(("negative elapsed", negative_time))
        nan_time = _synthetic_packet()
        nan_time["rows"][1]["elapsed_seconds"] = float("nan")
        mutations.append(("nonfinite elapsed", nan_time))
        negative_preparation = _synthetic_packet()
        negative_preparation["rows"][1]["preparation_seconds"] = -0.1
        mutations.append(("negative preparation", negative_preparation))
        contradictory_status = _synthetic_packet()
        contradictory_status["rows"][1]["primary_success"] = False
        mutations.append(("success marked unsuccessful", contradictory_status))
        contradictory_failure = _synthetic_packet()
        contradictory_failure["rows"][2]["failure_reason"] = None
        mutations.append(("failure without reason", contradictory_failure))
        unsafe_exceeds_committed = _synthetic_packet()
        unsafe_exceeds_committed["rows"][5]["unsafe_committed_transitions"] = 2
        mutations.append(("unsafe exceeds committed", unsafe_exceeds_committed))

        for name, packet in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_public_results(packet)

    def test_primary_success_requires_execution_goal_and_in_budget_elapsed(self) -> None:
        """A successful endpoint requires observed execution, reached goal, and elapsed time within the 180-second episode budget."""
        mutations: list[tuple[str, object]] = []
        no_execution = _synthetic_packet()
        row = no_execution["rows"][1]
        row.update(
            executed=None,
            goal_reached=None,
            host_invocations_observed=0,
            repair_calls=None,
            initial_proposal_failures=None,
            timeout_calls=None,
            committed_transitions=None,
            unsafe_committed_transitions=None,
            safety_status="NOT_OBSERVED",
            replay_valid=None,
            engine_reexecution_valid=None,
            elapsed_seconds=None,
            preparation_seconds=None,
            outgoing_requests_bound=None,
            episode_sha256=None,
        )
        mutations.append(("success without execution", no_execution))
        no_goal = _synthetic_packet()
        no_goal["rows"][1]["goal_reached"] = False
        mutations.append(("success without goal", no_goal))
        over_budget = _synthetic_packet()
        over_budget["rows"][1]["elapsed_seconds"] = 180.01
        mutations.append(("success over episode budget", over_budget))

        for name, packet in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_public_results(packet)

        unsafe_replay = _synthetic_packet()
        loaded = publication.validate_public_results(unsafe_replay)
        self.assertEqual(loaded["rows"][1]["status"], "success")
        self.assertEqual(loaded["rows"][1]["safety_status"], "FAIL")
        self.assertFalse(loaded["rows"][1]["replay_valid"])

    def test_host_call_limit_and_count_bounds_are_enforced(self) -> None:
        """Observed host calls cannot exceed the exact per-episode maximum and counters remain bounded integers."""
        mutations: list[tuple[str, object]] = []
        too_many_hosts = _synthetic_packet()
        too_many_hosts["rows"][1]["host_invocations_observed"] = 13
        mutations.append(("host call maximum", too_many_hosts))
        negative_count = _synthetic_packet()
        negative_count["rows"][1]["repair_calls"] = -1
        mutations.append(("negative repair count", negative_count))
        fractional_count = _synthetic_packet()
        fractional_count["rows"][1]["timeout_calls"] = 1.5
        mutations.append(("fractional timeout count", fractional_count))

        for name, packet in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_public_results(packet)

    def test_bilingual_fragments_preserve_the_same_aggregate_values(self) -> None:
        """English and Korean result/table fragments carry identical aggregate values and replay denominators."""
        packet = _synthetic_packet()
        en_results = publication.render_results_fragment(packet)
        ko_results = publication.render_results_fragment(packet, korean=True)
        en_tables = publication.render_tables_fragment(packet)
        ko_tables = publication.render_tables_fragment(packet, korean=True)
        for value in ("4/8", "7", "25", "2", "6", "n=7"):
            self.assertIn(value, en_results)
            self.assertIn(value, ko_results)
        for label in ("VALID=3", "INVALID=4", "NOT_RUN=0", "NOT_OBSERVED=1"):
            for rendered in (en_results, ko_results):
                self.assertIn(label, rendered.replace(r"\_", "_"))

        def latex_rows(fragment: str) -> list[str]:
            lines = fragment.splitlines()
            start = lines.index("\\midrule") + 1
            end = lines.index("\\bottomrule")
            return [line.strip() for line in lines[start:end] if line.strip()]

        en_rows = latex_rows(en_tables)
        ko_rows = latex_rows(ko_tables)
        self.assertEqual(len(en_rows), 4)
        self.assertEqual(en_rows, ko_rows)
        for rendered in (en_tables, ko_tables):
            self.assertEqual(rendered.count(r"\\"), 5)
            self.assertNotIn(r"\\\\", rendered)
            self.assertEqual(rendered.count(r"\label{tab:runtime-comparison-aggregate}"), 1)
        numeric_rows = [
            tuple(part.strip().rstrip("\\").strip() for part in row.split(" & ")[2:])
            for row in en_rows
        ]
        self.assertEqual(
            numeric_rows,
            [
                ("1/2", "1", "3", "1/2", "12.00 (1)", "0/1/0/1"),
                ("0/2", "2", "14", "0/1", "40.00 (2)", "1/1/0/0"),
                ("1/2", "2", "5", "1/2", "27.50 (2)", "1/1/0/0"),
                ("2/2", "2", "3", "0/1", "25.00 (2)", "1/1/0/0"),
            ],
        )
        self.assertIn("remain NR", en_results)
        self.assertIn("NR이다", ko_results)

    def test_svg_is_valid_explicitly_labelled_and_contains_all_eight_rows(self) -> None:
        """The comparison SVG is parseable, accessible by explicit labels, and renders each assigned row."""
        svg = publication.render_comparison_svg(_synthetic_packet())
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.attrib["role"], "img")
        self.assertEqual(root.attrib["aria-labelledby"], "svg-title svg-desc")
        self.assertIn("FIXED-GAME NATIVE RUNTIME COMPARISON | 8 ASSIGNED ROWS", svg)
        self.assertIn("NR = not reported, not zero", svg)
        self.assertIn("color is supplementary", svg)
        namespace = "{http://www.w3.org/2000/svg}"
        row_groups = {
            node.attrib.get("id"): node
            for node in root.iter(f"{namespace}g")
            if node.attrib.get("id", "").startswith("row-")
        }
        self.assertEqual(set(row_groups), {f"row-{row_id}" for row_id in range(1, 9)})
        actual_rows = []
        for row_id in range(1, 9):
            row_key = f"row-{row_id}"
            group = row_groups[row_key]
            self.assertEqual(group.attrib["aria-labelledby"], f"{row_key}-title {row_key}-desc")
            visible_text = [
                "".join(node.itertext()).strip() for node in group.iter(f"{namespace}text")
            ]
            self.assertGreaterEqual(len(visible_text), 3)
            actual_rows.append(tuple(visible_text[:3]))
        self.assertEqual(
            actual_rows,
            [
                ("1", "gpt-6.1-sol", "general_rule / r1"),
                ("2", "gpt-6.1-sol", "general_rule / r2"),
                ("3", "gpt-6.1-sol", "ontology / r1"),
                ("4", "gpt-6.1-sol", "ontology / r2"),
                ("5", "gpt-5.6-sol", "general_rule / r1"),
                ("6", "gpt-5.6-sol", "general_rule / r2"),
                ("7", "gpt-5.6-sol", "ontology / r1"),
                ("8", "gpt-5.6-sol", "ontology / r2"),
            ],
        )
        for label in (
            "HARNESS",
            "TIMEOUT",
            "SUCCESS",
            "FAIL",
            "failure_reason=harness_json_serialization_failure",
            "failure_reason=response_timeout",
            "NO_COMMIT_OBSERVED",
            "replay=",
            "engine=",
        ):
            self.assertIn(label, svg)

    def test_frozen_actual_packet_preserves_observed_accounting_and_engine_dispositions(
        self,
    ) -> None:
        """The frozen public packet retains its exact assigned, execution, receipt, and status accounting."""
        data = publication.load_public_results(publication.RESULTS_PATH)
        overall = publication.compute_aggregates(data)["overall"]
        self.assertEqual(overall["assigned"], 8)
        self.assertEqual(overall["observed_executions"], 7)
        self.assertEqual(overall["system_successes"], 5)
        self.assertEqual(overall["host_invocations"], 23)
        self.assertEqual(overall["repairs"], {"sum": 0, "observed_rows": 7})
        self.assertEqual(
            overall["transitions"], {"committed": 16, "unsafe_committed": 0, "observed_rows": 7}
        )
        self.assertEqual(overall["durations"]["elapsed_seconds"]["n"], 7)
        self.assertEqual(
            overall["engine_reexecution_status"],
            {"VALID": 6, "INVALID": 0, "NOT_RUN": 1, "NOT_OBSERVED": 1},
        )
        self.assertEqual(data["rows"][0]["engine_reexecution_status"], "NOT_OBSERVED")
        self.assertEqual(data["rows"][3]["engine_reexecution_status"], "NOT_RUN")
        self.assertEqual(overall["replay_valid"], {"true": 7, "false": 0, "unknown": 1})
        self.assertEqual(overall["timeout_calls"]["sum"], 2)

    def test_frozen_digest_rejects_timeout_and_aggregate_mutations(self) -> None:
        """A structurally valid mutation of a frozen result cannot enter publication through its digest gate."""
        payload = json.loads(publication.RESULTS_PATH.read_text(encoding="utf-8"))
        mutations = []
        timeout_mutation = copy.deepcopy(payload)
        timeout_mutation["rows"][3]["timeout_calls"] = 0
        mutations.append(("one-timeout mutation", timeout_mutation))
        aggregate_mutation = copy.deepcopy(payload)
        aggregate_mutation["rows"][1]["host_invocations_observed"] = 5
        mutations.append(("aggregate drift", aggregate_mutation))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for name, mutation in mutations:
                with self.subTest(name=name):
                    publication.validate_public_results(mutation)
                    with self.assertRaises(ValueError):
                        publication.load_public_results(self._write_packet(root, mutation))

    def test_generic_validator_rejects_failure_goal_values_and_observed_provider_requests(
        self,
    ) -> None:
        """Failure rows require a nullable boolean goal, and provider requests remain null at the public boundary."""
        payload = json.loads(publication.RESULTS_PATH.read_text(encoding="utf-8"))
        for value in (0, 1, "false"):
            mutation = copy.deepcopy(payload)
            mutation["rows"][2]["goal_reached"] = value
            with self.subTest(goal_reached=value), self.assertRaises(ValueError):
                publication.validate_public_results(mutation)
        provider_mutation = copy.deepcopy(payload)
        provider_mutation["rows"][1]["provider_request_count"] = 1
        with self.assertRaises(ValueError):
            publication.validate_public_results(provider_mutation)

    def test_engine_disposition_is_four_way_and_bool_consistency_is_enforced(self) -> None:
        """Engine replay disposition is four-valued while its nullable boolean remains a consistent complementary fact."""
        adverse = _synthetic_packet()
        adverse["rows"][3]["engine_reexecution_status"] = "NOT_RUN"
        adverse["rows"][3]["engine_reexecution_valid"] = None
        publication.validate_public_results(adverse)
        aggregate = publication.compute_aggregates(adverse)["overall"]
        self.assertEqual(
            aggregate["engine_reexecution_status"],
            {"VALID": 3, "INVALID": 3, "NOT_RUN": 1, "NOT_OBSERVED": 1},
        )
        inconsistent_valid = copy.deepcopy(adverse)
        inconsistent_valid["rows"][1]["engine_reexecution_status"] = "VALID"
        inconsistent_valid["rows"][1]["engine_reexecution_valid"] = False
        with self.assertRaises(ValueError):
            publication.validate_public_results(inconsistent_valid)
        inconsistent_not_run = copy.deepcopy(adverse)
        inconsistent_not_run["rows"][3]["engine_reexecution_valid"] = True
        with self.assertRaises(ValueError):
            publication.validate_public_results(inconsistent_not_run)

    def test_missing_input_fails_before_creating_any_publication_outputs(self) -> None:
        """A missing input path fails closed without creating result fragments or the SVG."""
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "generated"
            figures_dir = root / "figures"
            missing = root / "missing.json"
            with (
                patch.object(publication, "OUTPUT_DIR", output_dir),
                patch.object(publication, "FIGURES_DIR", figures_dir),
                self.assertRaises(FileNotFoundError),
            ):
                publication.main(missing)
            self.assertFalse(output_dir.exists())
            self.assertFalse(figures_dir.exists())


class IdentityAdmissionPublicationTests(unittest.TestCase):
    @staticmethod
    def _fixture_payload() -> dict[str, object]:
        return json.loads(publication.IDENTITY_RESULTS_PATH.read_text(encoding="utf-8"))

    def test_sanitized_identity_packet_is_validated_without_mutation(self) -> None:
        """The fixed packet preserves its 20-row plan and observed 1/0/19 accounting."""
        payload = self._fixture_payload()
        before = copy.deepcopy(payload)

        validated = publication.validate_identity_results(payload)
        self.assertEqual(publication.load_identity_results(), validated)
        self.assertEqual(
            publication.IDENTITY_RESULTS_SHA256,
            "12fee3535d99930311b71ffa7e56b9aaa8b220353a14533cc25194211bf5554c",
        )

        self.assertEqual(payload, before)
        self.assertEqual(len(validated["rows"]), 20)
        self.assertEqual(
            tuple(row["planned_id"] for row in validated["rows"]),
            tuple(
                f"sealed-lighthouse-v1:{selector}:{representation}:repeat-{repeat}"
                for selector in validated["scope"]["requested_selectors"]
                for representation in validated["scope"]["representations"]
                for repeat in validated["scope"]["repeats"]
            ),
        )
        self.assertEqual(
            validated["counters"],
            {
                "assigned": 1,
                "blocked_repair_requests": 2,
                "committed_transitions": 0,
                "executed": 1,
                "host_invocations": 3,
                "identity_qualified": 0,
                "native_processes": 1,
                "planned": 20,
                "system_goal_successes": 0,
                "unattempted": 19,
                "unsafe_committed_transitions": 0,
            },
        )
        self.assertEqual(validated["rows"][0]["assigned"], 1)
        self.assertEqual(validated["rows"][0]["executed"], 1)
        self.assertEqual(validated["rows"][0]["identity_qualified"], False)
        self.assertEqual(validated["rows"][0]["provider_identity"], None)
        self.assertEqual(validated["rows"][0]["provider_revision"], None)
        self.assertTrue(all(row["status"] == "NOT_RUN" for row in validated["rows"][1:]))
        self.assertTrue(
            all(
                row["assigned"] == 0
                and row["executed"] == 0
                and row["goal_reached"] is None
                and row["identity_qualified"] is False
                for row in validated["rows"][1:]
            )
        )
        self.assertEqual(validated["unknowns"]["provider_identity"], None)
        self.assertEqual(validated["unknowns"]["provider_revision"], None)
        self.assertEqual(validated["unknowns"]["provider_cost_usd"], None)
        self.assertTrue(
            all(
                row["identity_qualified"] is False
                and row["provider_identity"] is None
                and row["provider_revision"] is None
                for row in validated["rows"]
            )
        )
        self.assertTrue(all(value is None for value in validated["unknowns"].values()))
        self.assertFalse(validated["prior_cohort"]["pooled"])
        self.assertEqual(
            validated["prior_cohort"]["results_sha256"],
            "ba369ab2f4e02afaeac643490e13fe6785ac7f8cbd04a5b88507c2cc4691c26e",
        )
        self.assertTrue(validated["failure"]["record_hash_valid"])
        self.assertFalse(validated["failure"]["engineering_record_accepted"])
        self.assertEqual(
            validated["failure"]["raw_bootstrap_stop_reason"], "episode_record_integrity_invalid"
        )

    def test_identity_loader_rejects_discarded_duplicate_and_reordered_planned_rows(self) -> None:
        """The validator requires the complete frozen row sequence, not merely 20 plausible rows."""
        mutations: list[tuple[str, dict[str, object]]] = []

        discarded = self._fixture_payload()
        discarded["rows"] = discarded["rows"][:-1]
        mutations.append(("discarded planned row", discarded))

        duplicated = self._fixture_payload()
        duplicated["rows"][1]["planned_id"] = duplicated["rows"][0]["planned_id"]
        mutations.append(("duplicated planned row", duplicated))

        reordered = self._fixture_payload()
        reordered["rows"][0], reordered["rows"][1] = reordered["rows"][1], reordered["rows"][0]
        mutations.append(("reordered planned rows", reordered))

        for name, mutation in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_identity_results(mutation)

    def test_identity_validation_rejects_counter_and_not_run_state_drift(self) -> None:
        """Counters stay integer/reconciled, and NOT_RUN rows cannot acquire execution or a false goal."""
        mutations: list[tuple[str, dict[str, object]]] = []

        boolean_count = self._fixture_payload()
        boolean_count["counters"]["assigned"] = True
        row_boolean_count = self._fixture_payload()
        row_boolean_count["rows"][0]["host_invocations"] = True
        mutations.append(("boolean row count", row_boolean_count))

        row_fractional_count = self._fixture_payload()
        row_fractional_count["rows"][0]["blocked_repair_requests"] = 1.5
        mutations.append(("fractional row count", row_fractional_count))
        mutations.append(("boolean counter", boolean_count))

        fractional_count = self._fixture_payload()
        fractional_count["counters"]["executed"] = 1.5
        mutations.append(("fractional counter", fractional_count))

        counter_drift = self._fixture_payload()
        counter_drift["counters"]["unattempted"] = 18
        mutations.append(("counter reconciliation drift", counter_drift))

        promoted_execution = self._fixture_payload()
        promoted_execution["rows"][1]["executed"] = 1
        mutations.append(("NOT_RUN promoted to execution", promoted_execution))

        promoted_goal = self._fixture_payload()
        promoted_goal["rows"][1]["goal_reached"] = False
        mutations.append(("NOT_RUN promoted to false goal", promoted_goal))

        for name, mutation in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_identity_results(mutation)

    def test_identity_validation_rejects_unqualified_identity_revision_cost_pooling_and_private_fields(
        self,
    ) -> None:
        """Unqualified selector/catalog claims, invented unknowns, cohort pooling, and private fields stay out."""
        mutations: list[tuple[str, dict[str, object]]] = []

        qualified_without_proof = self._fixture_payload()
        qualified_without_proof["rows"][0]["identity_qualified"] = True
        mutations.append(("unqualified identity promoted", qualified_without_proof))

        selector_claim = self._fixture_payload()
        selector_claim["rows"][0]["provider_identity"] = "gpt-6-luna"
        mutations.append(("requested selector treated as provider identity", selector_claim))

        catalog_claim = self._fixture_payload()
        catalog_claim["rows"][0]["provider_revision"] = "catalog"
        mutations.append(("catalog treated as provider revision", catalog_claim))

        invented_revision = self._fixture_payload()
        invented_revision["unknowns"]["provider_revision"] = "invented-revision"
        mutations.append(("invented unknown revision", invented_revision))

        zero_cost = self._fixture_payload()
        zero_cost["unknowns"]["provider_cost_usd"] = 0
        mutations.append(("zero cost for unknown", zero_cost))

        pooled = self._fixture_payload()
        pooled["prior_cohort"]["pooled"] = True
        mutations.append(("old eight-row cohort pooled", pooled))

        private_top_level = self._fixture_payload()
        private_top_level["_private_trace"] = "must not publish"
        mutations.append(("unexpected private top-level field", private_top_level))

        private_row = self._fixture_payload()
        private_row["rows"][0]["private_header"] = "must not publish"
        mutations.append(("unexpected private row field", private_row))

        for name, mutation in mutations:
            with self.subTest(name=name), self.assertRaises(ValueError):
                publication.validate_identity_results(mutation)

    def test_identity_validation_rejects_private_operator_email_in_diagnosis(self) -> None:
        """Diagnosis cannot smuggle an operator/account field into the public packet."""
        payload = self._fixture_payload()
        payload["diagnosis"]["operator_email"] = "private"

        with self.assertRaises(ValueError):
            publication.validate_identity_results(payload)

    def test_identity_validation_rejects_private_operator_account_fields_in_every_public_mapping(
        self,
    ) -> None:
        """Every public mapping is closed; private/operator/account extras are not publishable."""
        mapping_paths = (
            ("scope", ("scope",)),
            ("counters", ("counters",)),
            ("row", ("rows", 0)),
            ("failure", ("failure",)),
            ("timing", ("timing",)),
            ("unknowns", ("unknowns",)),
            ("provenance", ("provenance",)),
            ("prior_cohort", ("prior_cohort",)),
            ("unsupported_request", ("unsupported_request",)),
            ("diagnosis", ("diagnosis",)),
            ("claims", ("claims",)),
        )
        mapping_paths = mapping_paths + tuple(
            (f"row[{index}]", ("rows", index)) for index in range(1, 20)
        )
        for mapping_name, path in mapping_paths:
            for extra_key, extra_value in (
                ("private_trace", "must not publish"),
                ("operator_email", "private"),
                ("account_id", "private"),
            ):
                payload = self._fixture_payload()
                target = payload
                for component in path:
                    target = target[component]
                target[extra_key] = extra_value
                with (
                    self.subTest(mapping=mapping_name, extra_key=extra_key),
                    self.assertRaises(ValueError),
                ):
                    publication.validate_identity_results(payload)

    def test_identity_validation_rejects_malformed_nested_public_mapping_types(self) -> None:
        """Public metadata objects must remain mappings rather than null, list, or scalar values."""
        metadata_paths = (
            "scope",
            "counters",
            "rows",
            "failure",
            "timing",
            "unknowns",
            "provenance",
            "prior_cohort",
            "unsupported_request",
            "diagnosis",
            "claims",
        )
        for field in metadata_paths:
            for malformed in (None, [], "not-a-mapping"):
                payload = self._fixture_payload()
                payload[field] = malformed
                with (
                    self.subTest(field=field, malformed=repr(malformed)),
                    self.assertRaises(ValueError),
                ):
                    publication.validate_identity_results(payload)

        for malformed in (None, [], "not-a-mapping"):
            payload = self._fixture_payload()
            payload["rows"][0] = malformed
            with (
                self.subTest(field="rows[0]", malformed=repr(malformed)),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

    def test_identity_validation_rejects_missing_keys_from_each_public_metadata_object(
        self,
    ) -> None:
        """Required metadata keys cannot be omitted while leaving the packet otherwise plausible."""
        required_keys = {
            "failure": (
                "engineering_record_accepted",
                "fresh_engine_replay",
                "model_incapability_inferred",
                "primary",
                "proposal_constraint_validity",
                "raw_bootstrap_stop_reason",
                "raw_terminal_failure_reason",
                "record_hash_valid",
                "safety",
                "secondary",
                "semantic_record_links_valid",
            ),
            "timing": (
                "episode_elapsed_seconds",
                "native_process_seconds",
                "orchestration_seconds",
                "preparation_seconds",
                "pure_inference_latency_claimed",
                "successful_completion_seconds",
            ),
            "unknowns": (
                "actual_cash_charge",
                "actual_credit_consumption",
                "effective_effort",
                "provider_cost_usd",
                "provider_identity",
                "provider_request_count",
                "provider_revision",
            ),
            "provenance": (
                "episode_sha256",
                "execution_ended_at",
                "installed_cli_version",
                "operational_closure_sha256",
                "plan_sha256",
                "record_hash",
                "source_manifest_sha256",
                "source_snapshot_file_count",
                "source_snapshot_manifest_sha256",
                "source_snapshot_visibility",
            ),
            "prior_cohort": (
                "assigned",
                "pooled",
                "results_sha256",
                "system_goal_successes",
                "unchanged",
            ),
            "unsupported_request": (
                "assigned",
                "catalog_status",
                "requested_selector",
                "substituted",
            ),
            "diagnosis": (
                "bounded_source_fallback_review",
                "dedicated_tracer_status",
                "identity_state",
                "logging_target_level_correct",
                "missing_or_nonstring_header_unresolved",
                "provider_model_header",
                "source_urls",
            ),
            "claims": (
                "confirmatory_A_C_established",
                "new_verified_model_comparison",
                "no_rerun",
                "ontology_effect_demonstrated",
                "zero_cost_or_zero_credit_claimed",
            ),
        }
        for mapping_name, fields in required_keys.items():
            for field in fields:
                payload = self._fixture_payload()
                del payload[mapping_name][field]
                with self.subTest(mapping=mapping_name, field=field), self.assertRaises(ValueError):
                    publication.validate_identity_results(payload)

    def test_identity_validation_rejects_hash_timestamp_url_boolean_and_count_drift(self) -> None:
        """Public metadata keeps strict hashes, UTC timestamps, source URLs, booleans, and counts."""
        hash_fields = (
            "episode_sha256",
            "operational_closure_sha256",
            "plan_sha256",
            "record_hash",
            "source_manifest_sha256",
            "source_snapshot_manifest_sha256",
        )
        for field in hash_fields:
            for invalid in ("A" * 64, "a" * 63, "not-a-hash"):
                payload = self._fixture_payload()
                payload["provenance"][field] = invalid
                with (
                    self.subTest(kind="provenance hash", field=field, invalid=invalid),
                    self.assertRaises(ValueError),
                ):
                    publication.validate_identity_results(payload)

        for invalid in (
            "2026-10-27T00:07:50.534794",
            "2026-10-27T00:07:50.534794+09:00",
            "not-a-timestamp",
        ):
            payload = self._fixture_payload()
            payload["provenance"]["execution_ended_at"] = invalid
            with self.subTest(kind="UTC timestamp", invalid=invalid), self.assertRaises(ValueError):
                publication.validate_identity_results(payload)

        for invalid in (
            ["file:///private/operator"],
            ["https://example.invalid/not-codex-source"],
            [
                (
                    "https://github.com/openai/codex/blob/rust-v0.163.0/"
                    "codex-rs/core/src/session/turn.rs"
                )
            ],
        ):
            payload = self._fixture_payload()
            payload["diagnosis"]["source_urls"] = invalid
            with (
                self.subTest(kind="public source URLs", invalid=invalid),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)
        for field, invalid in (
            ("installed_cli_version", "0.163.0"),
            ("installed_cli_version", "private-cli"),
            ("source_snapshot_visibility", "public"),
            ("source_snapshot_visibility", None),
        ):
            payload = self._fixture_payload()
            payload["provenance"][field] = invalid
            with (
                self.subTest(kind="provenance bounded value", field=field, invalid=invalid),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

        for field, invalid in (
            ("bounded_source_fallback_review", "private-review"),
            ("dedicated_tracer_status", "operator-only"),
            ("identity_state", "PRIVATE_IDENTITY"),
            ("provider_model_header", None),
            ("provider_model_header", {"operator_email": "private"}),
        ):
            payload = self._fixture_payload()
            payload["diagnosis"][field] = invalid
            with (
                self.subTest(kind="diagnosis bounded value", field=field, invalid=invalid),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

        for invalid in (None, "private-url", [None], ["https://example.invalid/private"]):
            payload = self._fixture_payload()
            payload["diagnosis"]["source_urls"] = invalid
            with (
                self.subTest(kind="diagnosis URL type", invalid=invalid),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

        for field, invalid in (
            ("catalog_status", "private-catalog"),
            ("requested_selector", "operator-model"),
        ):
            payload = self._fixture_payload()
            payload["unsupported_request"][field] = invalid
            with (
                self.subTest(kind="unsupported request bound", field=field, invalid=invalid),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

        for mapping_name, field in (
            ("diagnosis", "logging_target_level_correct"),
            ("diagnosis", "missing_or_nonstring_header_unresolved"),
            ("unsupported_request", "substituted"),
            ("timing", "pure_inference_latency_claimed"),
            ("prior_cohort", "pooled"),
            ("prior_cohort", "unchanged"),
            ("failure", "engineering_record_accepted"),
            ("failure", "record_hash_valid"),
            ("failure", "model_incapability_inferred"),
            ("failure", "semantic_record_links_valid"),
            ("claims", "confirmatory_A_C_established"),
            ("claims", "new_verified_model_comparison"),
            ("claims", "no_rerun"),
            ("claims", "ontology_effect_demonstrated"),
            ("claims", "zero_cost_or_zero_credit_claimed"),
        ):
            payload = self._fixture_payload()
            payload[mapping_name][field] = 1
            with (
                self.subTest(kind="strict boolean", mapping=mapping_name, field=field),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

        for mapping_name, field, invalid in (
            ("provenance", "source_snapshot_file_count", True),
            ("provenance", "source_snapshot_file_count", 23.0),
            ("provenance", "source_snapshot_file_count", -1),
            ("unsupported_request", "assigned", True),
            ("unsupported_request", "assigned", -1),
            ("unsupported_request", "assigned", 0.5),
            ("prior_cohort", "assigned", True),
            ("prior_cohort", "assigned", -1),
            ("prior_cohort", "assigned", 8.0),
            ("prior_cohort", "system_goal_successes", True),
            ("prior_cohort", "system_goal_successes", -1),
            ("prior_cohort", "system_goal_successes", 5.0),
        ):
            payload = self._fixture_payload()
            payload[mapping_name][field] = invalid
            with (
                self.subTest(
                    kind="strict count", mapping=mapping_name, field=field, invalid=invalid
                ),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)
        for invalid in ("A" * 64, "a" * 63, "not-a-hash"):
            payload = self._fixture_payload()
            payload["prior_cohort"]["results_sha256"] = invalid
            with (
                self.subTest(kind="prior cohort hash", invalid=invalid),
                self.assertRaises(ValueError),
            ):
                publication.validate_identity_results(payload)

        for field in (
            "preparation_seconds",
            "episode_elapsed_seconds",
            "native_process_seconds",
            "orchestration_seconds",
        ):
            for invalid in (0, -1, float("inf"), None):
                payload = self._fixture_payload()
                payload["timing"][field] = invalid
                with (
                    self.subTest(kind="positive finite timing", field=field, invalid=invalid),
                    self.assertRaises(ValueError),
                ):
                    publication.validate_identity_results(payload)

    def test_identity_fragments_share_packet_accounting_and_publication_boundaries(self) -> None:
        """Both languages expose 20/1/0/19 and the identity-admission caveats without layout shortcuts."""
        packet = publication.validate_identity_results(self._fixture_payload())
        rendered = [
            publication.render_identity_fragment(packet),
            publication.render_identity_fragment(packet, korean=True),
        ]

        for fragment in rendered:
            lowered = fragment.lower()
            normalized = lowered.replace("_", " ").replace("-", " ")
            for value in ("20", "1", "0", "19"):
                self.assertIn(value, fragment)
            self.assertIn("unknown", lowered)
            self.assertIn("not a model comparison", normalized)
            self.assertIn("record hash valid", normalized)
            self.assertIn("engineering record accepted", normalized)
            self.assertTrue("true" in normalized or "valid" in normalized)
            self.assertTrue(
                "false" in normalized or "rejected" in normalized or "not accepted" in normalized
            )
            self.assertEqual(fragment.count(r"\label{tab:runtime-identity-admission}"), 1)
            for forbidden in (r"\resizebox", r"\tiny", r"\scriptsize"):
                self.assertNotIn(forbidden, fragment)
            self.assertNotIn("reducedfont", lowered)

            def normalize_cell(value: str) -> str:
                cell = value.strip().rstrip("\\").strip()
                prefix = r"\texttt{"
                if cell.startswith(prefix) and cell.endswith("}"):
                    cell = cell[len(prefix) : -1]
                return cell.replace(r"\_", "_")

            table_rows = [
                tuple(normalize_cell(part) for part in line.strip().split(" & "))
                for line in fragment.splitlines()
                if " & " in line and line.strip().endswith(r"\\")
            ]
            body_rows = [
                row
                for row in table_rows
                if len(row) == 6
                and row[0] in packet["scope"]["requested_selectors"]
                and row[1] in packet["scope"]["representations"]
            ]
            expected_cells = {
                (selector, representation)
                for selector in packet["scope"]["requested_selectors"]
                for representation in packet["scope"]["representations"]
            }
            self.assertEqual(len(body_rows), 10)
            self.assertEqual({row[:2] for row in body_rows}, expected_cells)

    def test_identity_loader_digest_gate_and_writer_are_deterministic_and_non_mutating(
        self,
    ) -> None:
        """Exact bytes are digest-pinned; writing uses OUTPUT_DIR and leaves the source unchanged."""
        source = publication.IDENTITY_RESULTS_PATH
        original_bytes = source.read_bytes()

        with TemporaryDirectory() as directory:
            root = Path(directory)
            input_path = root / "identity-results.json"
            input_path.write_bytes(original_bytes)
            altered_path = root / "altered-results.json"
            altered_path.write_bytes(original_bytes.replace(b'"assigned":1', b'"assigned":2', 1))

            with self.assertRaises(ValueError):
                publication.load_identity_results(altered_path)

            output_dir = root / "generated"
            with patch.object(publication, "OUTPUT_DIR", output_dir):
                first_paths = tuple(publication.write_identity_fragments(input_path=input_path))
                first_bytes = tuple(path.read_bytes() for path in first_paths)
                second_paths = tuple(publication.write_identity_fragments(input_path=input_path))
                second_bytes = tuple(path.read_bytes() for path in second_paths)

            self.assertEqual(first_paths, second_paths)
            self.assertEqual(
                tuple(path.name for path in first_paths),
                ("runtime_identity_extension_en.tex", "runtime_identity_extension_ko.tex"),
            )
            self.assertEqual(first_bytes, second_bytes)
            self.assertEqual(
                first_bytes[0].decode("utf-8"),
                publication.render_identity_fragment(publication.load_identity_results(input_path)),
            )
            self.assertEqual(
                first_bytes[1].decode("utf-8"),
                publication.render_identity_fragment(
                    publication.load_identity_results(input_path), korean=True
                ),
            )

        self.assertEqual(source.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
