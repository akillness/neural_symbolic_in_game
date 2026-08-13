import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator

from scripts.capture_godot_evidence import (
    CANONICAL_FIXTURE_ID,
    RENDER_FILES,
    RENDER_ROOT_NAME,
    fixture_output_path,
    prepare_capture_paths,
    promote_capture,
    write_current_pointer,
)
from scripts.png_contract import validate_render_png
from scripts.project_experimental_bridge import SUPPORTED_TYPES, project_event

ROOT = Path(__file__).parents[1]
GODOT_PROJECT = ROOT / "game-track" / "godot"
SCHEMA_DIR = ROOT / "game-track" / "schemas"
FIXTURE_DIR = ROOT / "data" / "fixtures"
SCENARIO_PATH = GODOT_PROJECT / "data" / "sealed_lighthouse.json"
FIXTURE_PATHS = sorted(FIXTURE_DIR.glob("experimental-game-*.json"))


def current_evidence_root() -> Path:
    tech_root = ROOT / "_workspace/current/engineering/tech-verification"
    pointer = load_json(tech_root / "current.json")
    return tech_root / "evidence" / pointer["evidence_set_id"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def apply_expected_path(initial_state: dict) -> dict:
    """Independent, deliberately small oracle for the three authorized commits."""
    state = deepcopy(initial_state)

    lens_location = state["world"]["object_locations"].pop("signal_lens")
    if lens_location not in state["world"]["reachable_locations"]:
        raise AssertionError("designed fixture made the signal lens unreachable")
    state["player"]["inventory"] = sorted({*state["player"]["inventory"], "signal_lens"})
    state["facts"] = sorted({*state["facts"], "signal_lens_acquired"})
    state["quest"]["stage"] = max(state["quest"]["stage"], 1)
    state["quest"]["flags"] = sorted({*state["quest"]["flags"], "signal_lens_acquired"})
    state["revision"] += 1

    if "signal_lens" not in state["player"]["inventory"]:
        raise AssertionError("designed fixture lost the acquired lens")
    state["facts"] = sorted(
        {*state["facts"], "signal_lens_installed", "lighthouse_hint_authorized"}
    )
    state["quest"]["stage"] = 2
    state["quest"]["flags"] = sorted(
        {
            *state["quest"]["flags"],
            "signal_lens_installed",
            "lighthouse_hint_authorized",
        }
    )
    state["revision"] += 1

    mira = state["npcs"]["captain_mira"]
    if "tide_marks_hint" not in mira["knowledge"]:
        raise AssertionError("Captain Mira lacks the designed authorized hint")
    state["facts"] = sorted({*state["facts"], "tide_marks_hint"})
    mira["disclosed"] = sorted({*mira["disclosed"], "tide_marks_hint"})
    mira["relationship_memory"] = sorted(
        {*mira["relationship_memory"], "turn-05:mira-shared-tide-marks-hint"}
    )
    state["revision"] += 1
    return state


def find_godot_4() -> str | None:
    executable = shutil.which("godot4") or shutil.which("godot")
    if executable is None:
        return None
    probe = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if probe.returncode != 0 or not probe.stdout.strip().startswith("4."):
        return None
    return executable


class GodotExperimentalGameContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario = load_json(SCENARIO_PATH)
        cls.scenario_schema = load_json(SCHEMA_DIR / "experimental-game-scenario.schema.json")
        cls.fixture_schema = load_json(SCHEMA_DIR / "experimental-game-fixture.schema.json")

    def test_schemas_and_all_authored_inputs_validate(self) -> None:
        schema_paths = sorted(SCHEMA_DIR.glob("experimental-game-*.schema.json"))
        self.assertEqual(len(schema_paths), 6)
        for schema_path in schema_paths:
            with self.subTest(schema=schema_path.name):
                Draft202012Validator.check_schema(load_json(schema_path))

        Draft202012Validator(self.scenario_schema).validate(self.scenario)
        self.assertEqual(len(FIXTURE_PATHS), 4)
        fixture_validator = Draft202012Validator(self.fixture_schema)
        for fixture_path in FIXTURE_PATHS:
            with self.subTest(fixture=fixture_path.name):
                fixture_validator.validate(load_json(fixture_path))

    def test_fixture_hashes_bind_the_same_authorized_terminal_state(self) -> None:
        terminal = apply_expected_path(self.scenario["initial_state"])
        expected_hash = canonical_hash(terminal)
        self.assertEqual(
            expected_hash,
            "4b2310173dc059071fdc98e7705608d383dda81559706c3dd33bc96983108892",
        )
        self.assertNotIn("keeper_betrayal", terminal["facts"])
        self.assertIn("tide_marks_hint", terminal["facts"])
        self.assertEqual(terminal["quest"]["stage"], 2)
        self.assertEqual(terminal["revision"], 3)
        for fixture_path in FIXTURE_PATHS:
            fixture = load_json(fixture_path)
            with self.subTest(fixture=fixture["fixture_id"]):
                self.assertEqual(fixture["expected"]["terminal_state_hash"], expected_hash)
                self.assertEqual(fixture["expected"]["research_oracle_state_hash"], expected_hash)
                self.assertEqual(
                    fixture["expected"]["oracle_id"],
                    "python-independent-sealed-lighthouse-v1",
                )
                self.assertEqual(
                    fixture["expected"]["committed_operations"],
                    ["acquire_object", "install_lens", "reveal_hint"],
                )

    def test_disclosure_fixture_has_permanent_and_stage_gates(self) -> None:
        policy = self.scenario["disclosure_policy"]
        self.assertIn("keeper_betrayal", policy["permanently_forbidden"])
        gate = next(item for item in policy["stage_gates"] if item["fact_id"] == "tide_marks_hint")
        self.assertEqual(gate["minimum_stage"], 2)
        self.assertLess(self.scenario["initial_state"]["quest"]["stage"], gate["minimum_stage"])
        self.assertIn(
            "keeper_betrayal",
            self.scenario["initial_state"]["npcs"]["captain_mira"]["knowledge"],
        )
        self.assertNotIn("keeper_betrayal", self.scenario["initial_state"]["facts"])

    def test_fault_fixtures_are_disjoint_and_keep_the_same_terminal_target(self) -> None:
        fixtures = {load_json(path)["fault_mode"]: load_json(path) for path in FIXTURE_PATHS}
        self.assertEqual(set(fixtures), {"none", "duplicate_event", "timeout", "corrupt_save"})
        self.assertEqual(fixtures["none"]["expected"]["duplicate_event_count"], 0)
        self.assertEqual(fixtures["duplicate_event"]["expected"]["duplicate_event_count"], 1)
        self.assertEqual(fixtures["timeout"]["expected"]["timeout_count"], 1)
        self.assertIn("ADAPTER_TIMEOUT", fixtures["timeout"]["expected"]["fallback_codes"])

    def test_experimental_event_projects_to_stable_bridge_contract(self) -> None:
        event_schema = load_json(SCHEMA_DIR / "experimental-game-event.schema.json")
        bridge_schema = load_json(SCHEMA_DIR / "game-bridge.schema.json")
        event_validator = Draft202012Validator(event_schema)
        bridge_validator = Draft202012Validator(bridge_schema)
        evidence_root = current_evidence_root()
        for path in sorted(evidence_root.glob("*/events.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                event = json.loads(line)
                event_validator.validate(event)
                if event["event_type"] not in SUPPORTED_TYPES:
                    continue
                projected = project_event(event)
                bridge_validator.validate(projected)
                self.assertEqual(projected["step"], event["sequence"])
                self.assertEqual(projected["payload"]["delivery_index"], event["delivery_index"])
                self.assertEqual(projected["world_state_hash"], event["world_state_hash"])
                self.assertEqual(
                    projected["payload"]["world_state_hash_before"],
                    event["world_state_hash_before"],
                )

    def test_runner_contains_required_authority_and_replay_boundaries(self) -> None:
        runner = (GODOT_PROJECT / "scripts" / "experimental_game_runner.gd").read_text(
            encoding="utf-8"
        )
        machine = (GODOT_PROJECT / "scripts" / "sealed_lighthouse_machine.gd").read_text(
            encoding="utf-8"
        )
        required_runner_fragments = {
            "processed_event_ids": "duplicate-event idempotency",
            "ADAPTER_TIMEOUT": "timeout fault path",
            "world_state_hash_before": "transaction boundary",
            "_replay(initial_state": "deterministic replay",
            "Time.get_ticks_usec": "observed timing clock",
            "OBSERVED_ENGINE_RUN": "engine-only result status",
        }
        for fragment, purpose in required_runner_fragments.items():
            with self.subTest(purpose=purpose):
                self.assertIn(fragment, runner)
        self.assertIn("FORBIDDEN_DISCLOSURE", machine)
        self.assertIn("STAGE_GATED_DISCLOSURE", machine)
        self.assertIn("load_state_if_hash_matches", machine)
        self.assertLess(
            machine.index("CanonicalState.sha256(normalized) != expected_hash"),
            machine.index("state = normalized", machine.index("load_state_if_hash_matches")),
        )
        for operation in ("acquire_object", "install_lens", "reveal_hint"):
            with self.subTest(operation=operation):
                self.assertIn(f'"{operation}"', machine)

    def test_render_capture_scene_is_non_headless_and_trace_bound(self) -> None:
        runner = (GODOT_PROJECT / "scripts" / "evidence_capture_runner.gd").read_text(
            encoding="utf-8"
        )
        for fragment in (
            'DisplayServer.get_name() == "headless"',
            "RenderingServer.frame_post_draw",
            "viewport.get_texture().get_image()",
            "save_png",
            '"generated_assets_in_frame": false',
            '"authored-engine-render-state-correspondence-only"',
        ):
            self.assertIn(fragment, runner)

    def test_render_capture_scene_rejects_headless_execution(self) -> None:
        godot = find_godot_4()
        if godot is None:
            self.skipTest("Godot 4.x is not installed; capture boundary cannot execute")
        result = subprocess.run(
            [
                godot,
                "--headless",
                "--path",
                str(GODOT_PROJECT),
                "--scene",
                "res://scenes/evidence_capture.tscn",
                "--quit-after",
                "5",
                "--",
                "--events=/missing/events.jsonl",
                "--summary=/missing/summary.json",
                "--output=/missing/output",
                "--evidence-set-id=headless-negative-v1",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "render capture requires a non-headless display server",
            result.stdout + result.stderr,
        )

    def test_retained_render_captures_bind_canonical_events_and_pixels(self) -> None:
        evidence_root = current_evidence_root()
        top_manifest = load_json(evidence_root / "evidence-manifest.json")
        render_manifest = top_manifest["render_capture"]
        schema = load_json(SCHEMA_DIR / "experimental-game-render-capture.schema.json")
        Draft202012Validator(schema).validate(render_manifest)
        self.assertEqual(render_manifest["evidence_set_id"], evidence_root.name)
        self.assertFalse(render_manifest["engine"]["headless"])
        self.assertNotEqual(render_manifest["engine"]["display_server"], "headless")
        self.assertEqual(render_manifest["fixture_id"], CANONICAL_FIXTURE_ID)
        render_root = evidence_root / RENDER_ROOT_NAME
        self.assertEqual(
            load_json(render_root / "capture-manifest.json"),
            render_manifest,
        )
        events_path = evidence_root / CANONICAL_FIXTURE_ID / "events.jsonl"
        summary_path = evidence_root / CANONICAL_FIXTURE_ID / "summary.json"
        self.assertEqual(
            render_manifest["source"]["events_sha256"],
            hashlib.sha256(events_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            render_manifest["source"]["summary_sha256"],
            hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        )
        for field, path in {
            "capture_scene_sha256": GODOT_PROJECT / "scenes/evidence_capture.tscn",
            "capture_runner_sha256": GODOT_PROJECT / "scripts/evidence_capture_runner.gd",
            "project_sha256": GODOT_PROJECT / "project.godot",
            "capture_pipeline_sha256": ROOT / "scripts/capture_godot_evidence.py",
            "png_contract_sha256": ROOT / "scripts/png_contract.py",
            "capture_schema_sha256": (SCHEMA_DIR / "experimental-game-render-capture.schema.json"),
            "retained_validator_sha256": ROOT / "scripts/validate_game_studio.py",
            "uv_lock_sha256": ROOT / "uv.lock",
        }.items():
            self.assertEqual(
                render_manifest["source"][field],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        events = {
            event["event_id"]: event
            for event in (
                json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()
            )
        }
        expected_events = {
            "sl-rc-001-arrival": "evt-000-observe",
            "sl-rc-002-rejected-secret": "evt-002-fallback-secret",
            "sl-rc-003-authorized-hint": "evt-005-commit-hint",
        }
        self.assertEqual(
            {row["file"] for row in render_manifest["captures"]},
            set(RENDER_FILES),
        )
        for row in render_manifest["captures"]:
            with self.subTest(capture=row["capture_id"]):
                self.assertEqual(row["event_id"], expected_events[row["capture_id"]])
                event = events[row["event_id"]]
                self.assertEqual(row["world_state_hash"], event["world_state_hash"])
                self.assertEqual(row["delivery_index"], event["delivery_index"])
                self.assertFalse(row["generated_assets_in_frame"])
                image = render_root / row["file"]
                self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), row["sha256"])
                self.assertEqual(image.stat().st_size, row["bytes"])
                self.assertEqual(validate_render_png(image).to_jsonable(), row["pixel_stats"])
        rejected = next(
            row
            for row in render_manifest["captures"]
            if row["capture_id"] == "sl-rc-002-rejected-secret"
        )
        self.assertEqual(rejected["world_state_hash_before"], rejected["world_state_hash"])
        authorized = events["evt-005-commit-hint"]
        self.assertTrue(authorized["commit"]["applied"])
        self.assertEqual(authorized["commit"]["operation"], "reveal_hint")

    def test_render_schema_rejects_cross_capture_and_summary_identity_swaps(self) -> None:
        evidence_root = current_evidence_root()
        manifest = load_json(evidence_root / RENDER_ROOT_NAME / "capture-manifest.json")
        schema = load_json(SCHEMA_DIR / "experimental-game-render-capture.schema.json")
        validator = Draft202012Validator(schema)

        swapped_file = deepcopy(manifest)
        swapped_file["captures"][0]["file"] = swapped_file["captures"][1]["file"]
        self.assertTrue(list(validator.iter_errors(swapped_file)))

        swapped_view = deepcopy(manifest)
        swapped_view["captures"][0]["view_mode"] = "experiment-inspector"
        swapped_view["captures"][0]["participant_visible"] = False
        self.assertTrue(list(validator.iter_errors(swapped_view)))

        unrelated_identity = deepcopy(manifest)
        unrelated_identity["run_id"] = "unrelated-run"
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            canonical = staging / CANONICAL_FIXTURE_ID
            render = staging / RENDER_ROOT_NAME
            shutil.copytree(evidence_root / CANONICAL_FIXTURE_ID, canonical)
            shutil.copytree(evidence_root / RENDER_ROOT_NAME, render)
            (render / "capture-manifest.json").write_text(
                json.dumps(unrelated_identity, indent=2) + "\n",
                encoding="utf-8",
            )
            from scripts.capture_godot_evidence import enrich_and_validate_render_capture

            with self.assertRaisesRegex(ValueError, "summary identity mismatch: run_id"):
                enrich_and_validate_render_capture(staging, manifest["evidence_set_id"])

    def test_retained_validator_detects_render_toolchain_source_mutation(self) -> None:
        evidence_root = current_evidence_root()
        manifest = load_json(evidence_root / RENDER_ROOT_NAME / "capture-manifest.json")
        expected_paths = {
            "capture_pipeline_sha256": ROOT / "scripts/capture_godot_evidence.py",
            "png_contract_sha256": ROOT / "scripts/png_contract.py",
            "capture_schema_sha256": SCHEMA_DIR / "experimental-game-render-capture.schema.json",
            "retained_validator_sha256": ROOT / "scripts/validate_game_studio.py",
            "uv_lock_sha256": ROOT / "uv.lock",
        }
        for field, path in expected_paths.items():
            with self.subTest(field=field):
                self.assertEqual(
                    manifest["source"][field],
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                )

        mutated = deepcopy(manifest)
        mutated["source"]["png_contract_sha256"] = "0" * 64
        schema = load_json(SCHEMA_DIR / "experimental-game-render-capture.schema.json")
        Draft202012Validator(schema).validate(mutated)
        self.assertNotEqual(
            mutated["source"]["png_contract_sha256"],
            hashlib.sha256((ROOT / "scripts/png_contract.py").read_bytes()).hexdigest(),
        )

    def test_retained_toolchain_provenance_is_verifier_runtime_independent(self) -> None:
        manifest = load_json(current_evidence_root() / RENDER_ROOT_NAME / "capture-manifest.json")
        self.assertRegex(manifest["validation_toolchain"]["python_version"], r"^\d+\.\d+\.\d+")
        self.assertTrue(manifest["validation_toolchain"]["jsonschema_version"])

        validator_source = (ROOT / "scripts/validate_game_studio.py").read_text(encoding="utf-8")
        self.assertNotIn("platform.python_version()", validator_source)
        self.assertNotIn('importlib.metadata.version("jsonschema")', validator_source)

    def test_current_facing_docs_reference_selected_render_evidence(self) -> None:
        selected = current_evidence_root().name
        for path in (
            ROOT / "game-track/README.en.md",
            ROOT / "game-track/README.ko.md",
            GODOT_PROJECT / "README.en.md",
            GODOT_PROJECT / "README.ko.md",
            ROOT / "game-track/design/paper-crosswalk.en.md",
            ROOT / "game-track/design/paper-crosswalk.ko.md",
        ):
            with self.subTest(path=path):
                self.assertIn(selected, path.read_text(encoding="utf-8"))

    def test_evidence_capture_is_unique_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_parent = root / "evidence"
            staging_parent = root / "staging"
            staging, target = prepare_capture_paths(
                "godot-4.7.1-test-set",
                evidence_parent=evidence_parent,
                staging_parent=staging_parent,
            )
            (staging / "fixture").mkdir()
            (staging / "fixture" / "summary.json").write_text("{}\n", encoding="utf-8")
            (staging / "evidence-manifest.json").write_text("{}\n", encoding="utf-8")
            promote_capture(staging, target)
            marker = target / "fixture" / "summary.json"
            before = marker.read_bytes()
            self.assertTrue((target / "evidence-manifest.json").is_file())
            self.assertFalse((staging / "evidence-manifest.json").exists())

            with self.assertRaises(FileExistsError):
                prepare_capture_paths(
                    "godot-4.7.1-test-set",
                    evidence_parent=evidence_parent,
                    staging_parent=staging_parent,
                )
            self.assertEqual(marker.read_bytes(), before)
            self.assertFalse(staging.exists())

    def test_staging_id_collision_and_current_pointer_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence_parent = root / "evidence"
            staging_parent = root / "staging"
            staging_parent.mkdir()
            (staging_parent / "godot-test-staging-v1").mkdir()
            with self.assertRaises(FileExistsError):
                prepare_capture_paths(
                    "godot-test-staging-v1",
                    evidence_parent=evidence_parent,
                    staging_parent=staging_parent,
                )

            manifest = root / "evidence-manifest.json"
            manifest.write_text('{"complete":true}\n', encoding="utf-8")
            import scripts.capture_godot_evidence as capture

            original_pointer = capture.CURRENT_POINTER
            capture.CURRENT_POINTER = root / "current.json"
            try:
                write_current_pointer("godot-test-current-v1", manifest)
            finally:
                capture.CURRENT_POINTER = original_pointer
            pointer = load_json(root / "current.json")
            self.assertEqual(pointer["evidence_set_id"], "godot-test-current-v1")
            self.assertEqual(
                pointer["manifest_sha256"], hashlib.sha256(manifest.read_bytes()).hexdigest()
            )

    def test_capture_main_removes_failed_staging_without_touching_current_pointer(self) -> None:
        import scripts.capture_godot_evidence as capture

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original_evidence = capture.EVIDENCE_PARENT
            original_staging = capture.STAGING_PARENT
            original_pointer = capture.CURRENT_POINTER
            original_which = capture.shutil.which
            original_run = capture.subprocess.run
            capture.EVIDENCE_PARENT = root / "evidence"
            capture.STAGING_PARENT = root / "staging"
            capture.CURRENT_POINTER = root / "current.json"
            capture.CURRENT_POINTER.write_text('{"stable":true}\n', encoding="utf-8")
            capture.shutil.which = lambda _: "/mock/godot"

            def fake_run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
                if command == ["/mock/godot", "--version"]:
                    return subprocess.CompletedProcess(command, 0, "4.7.1.mock\n", "")
                raise subprocess.CalledProcessError(9, command)

            capture.subprocess.run = fake_run
            try:
                with self.assertRaises(subprocess.CalledProcessError):
                    capture.main(["--evidence-set-id", "failed-capture-test-v1"])
            finally:
                capture.EVIDENCE_PARENT = original_evidence
                capture.STAGING_PARENT = original_staging
                capture.CURRENT_POINTER = original_pointer
                capture.shutil.which = original_which
                capture.subprocess.run = original_run
            self.assertFalse((root / "staging/failed-capture-test-v1").exists())
            self.assertFalse((root / "evidence/failed-capture-test-v1").exists())
            self.assertEqual(
                (root / "current.json").read_text(encoding="utf-8"),
                '{"stable":true}\n',
            )

    def test_evidence_set_id_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                prepare_capture_paths(
                    "../overwrite",
                    evidence_parent=root / "evidence",
                    staging_parent=root / "staging",
                )

    def test_fixture_output_rejects_escape_duplicate_and_existing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "staging"
            staging.mkdir()
            seen: set[str] = set()
            for unsafe in ("../escape", "/tmp/escape", "Uppercase"):
                with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                    fixture_output_path(staging, unsafe, seen)

            output = fixture_output_path(staging, "fixture-safe-v1", seen)
            self.assertEqual(output.parent, staging)
            with self.assertRaises(ValueError):
                fixture_output_path(staging, "fixture-safe-v1", seen)

            existing = staging / "fixture-existing-v1"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                fixture_output_path(staging, "fixture-existing-v1", set())


class GodotExperimentalGameRuntimeTests(unittest.TestCase):
    @staticmethod
    def _ensure_project_imported(godot: str) -> None:
        """Import the Godot project once if its asset cache is absent.

        `.godot/` is a build artifact and is gitignored, so a fresh clone has no import
        cache. Godot then spends its first invocation importing instead of running the
        fixture, which produces no summary and fails the test for an environment reason
        rather than a real one. Importing explicitly makes the run deterministic from a
        pristine checkout.
        """

        if (GODOT_PROJECT / ".godot").is_dir():
            return
        subprocess.run(
            [godot, "--headless", "--path", str(GODOT_PROJECT), "--import"],
            check=False,
            capture_output=True,
            text=True,
            timeout=300,
        )

    def test_all_headless_fixtures_when_godot_4_is_available(self) -> None:
        godot = find_godot_4()
        if godot is None:
            self.skipTest("Godot 4.x is not installed; no engine execution is claimed")
        self._ensure_project_imported(godot)

        event_schema = load_json(SCHEMA_DIR / "experimental-game-event.schema.json")
        save_schema = load_json(SCHEMA_DIR / "experimental-game-save.schema.json")
        summary_schema = load_json(SCHEMA_DIR / "experimental-game-summary.schema.json")
        event_validator = Draft202012Validator(event_schema)
        save_validator = Draft202012Validator(save_schema)
        summary_validator = Draft202012Validator(summary_schema)

        with tempfile.TemporaryDirectory() as directory:
            output_root = Path(directory)
            for fixture_path in FIXTURE_PATHS:
                fixture = load_json(fixture_path)
                output = output_root / fixture["fixture_id"]
                command = [
                    godot,
                    "--headless",
                    "--path",
                    str(GODOT_PROJECT),
                    "--quit-after",
                    "120",
                    "--",
                    f"--fixture={fixture_path.resolve()}",
                    f"--output={output}",
                ]
                result = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                with self.subTest(fixture=fixture["fixture_id"]):
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    summary = load_json(output / "summary.json")
                    saved = load_json(output / "save.json")
                    events = [
                        json.loads(line)
                        for line in (output / "events.jsonl")
                        .read_text(encoding="utf-8")
                        .splitlines()
                        if line.strip()
                    ]
                    summary_validator.validate(summary)
                    save_validator.validate(saved)
                    for event in events:
                        event_validator.validate(event)
                    self.assertEqual(
                        [event["delivery_index"] for event in events],
                        list(range(len(events))),
                    )
                    self.assertTrue(all(summary["checks"].values()))
                    self.assertEqual(
                        summary["terminal_state_hash"], fixture["expected"]["terminal_state_hash"]
                    )
                    if fixture["fault_mode"] != "corrupt_save":
                        self.assertEqual(
                            summary["terminal_state_hash"], canonical_hash(saved["state"])
                        )
                    self.assertEqual(
                        summary["counts"]["duplicate_events"],
                        fixture["expected"]["duplicate_event_count"],
                    )
                    self.assertEqual(
                        summary["counts"]["timeouts"], fixture["expected"]["timeout_count"]
                    )
                    if fixture["fault_mode"] == "duplicate_event":
                        duplicate_groups: dict[str, list[dict]] = {}
                        for event in events:
                            duplicate_groups.setdefault(event["event_id"], []).append(event)
                        repeated = [group for group in duplicate_groups.values() if len(group) > 1]
                        self.assertEqual(len(repeated), 1)
                        self.assertEqual(
                            {event["sequence"] for event in repeated[0]},
                            {repeated[0][0]["sequence"]},
                        )
                        self.assertEqual(
                            len({event["delivery_index"] for event in repeated[0]}),
                            2,
                        )
                        unique_logical_sequences = sorted({event["sequence"] for event in events})
                        self.assertEqual(
                            unique_logical_sequences,
                            list(range(len(unique_logical_sequences))),
                        )
                    self.assertEqual(
                        summary["software"]["fixture_sha256"],
                        hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
                    )
                    self.assertEqual(
                        summary["software"]["scenario_sha256"],
                        hashlib.sha256(SCENARIO_PATH.read_bytes()).hexdigest(),
                    )
                    fallback_events = [
                        event for event in events if event["event_type"] == "fallback"
                    ]
                    self.assertTrue(fallback_events)
                    for event in fallback_events:
                        self.assertEqual(
                            event["world_state_hash_before"], event["world_state_hash"]
                        )
                    load_event = next(
                        event for event in events if event["event_id"] == "evt-007-load"
                    )
                    if fixture["fault_mode"] == "corrupt_save":
                        self.assertEqual(load_event["validation"]["codes"], ["SAVE_HASH_MISMATCH"])
                        self.assertFalse(load_event["payload"]["load_applied"])
                        self.assertEqual(
                            load_event["payload"]["preload_state_hash"],
                            load_event["payload"]["loaded_state_hash"],
                        )
                    else:
                        self.assertTrue(load_event["payload"]["load_applied"])


if __name__ == "__main__":
    unittest.main()
