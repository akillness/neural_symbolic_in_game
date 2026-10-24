from __future__ import annotations

import copy
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_visual_assets as visual_validator


class VisualAssetValidatorTests(unittest.TestCase):
    def test_rendered_table_surface_and_anchor_drift_fail_closed(self) -> None:
        manifest = json.loads(visual_validator.MANIFEST_PATH.read_text(encoding="utf-8"))
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_tables(manifest)
        self.assertEqual(validator.errors, [])

        unknown_surface = copy.deepcopy(manifest)
        source = next(
            item
            for item in unknown_surface["table_sources"]
            if item["id"] == "current-paper-hand-authored-tables"
        )
        source["rendered_in"] = ["paper-missing"]
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_tables(unknown_surface)
        self.assertTrue(any("unknown rendered surfaces" in error for error in validator.errors))

        missing_anchor = copy.deepcopy(manifest)
        source = next(
            item
            for item in missing_anchor["table_sources"]
            if item["id"] == "current-paper-hand-authored-tables"
        )
        source["anchors"].append("tab:not-present")
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_tables(missing_anchor)
        self.assertTrue(any("missing table anchor" in error for error in validator.errors))

    def test_generated_disclosure_tables_keep_local_120_spacing_before_each_body(self) -> None:
        for language in ("en", "ko"):
            source = (ROOT / f"paper/latex/generated/disclosure_tables_{language}.tex").read_text(
                encoding="utf-8"
            )
            fragments = re.findall(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", source, re.DOTALL)
            self.assertTrue(fragments, language)
            for fragment in fragments:
                body_start = fragment.index(r"\begin{tabular")
                self.assertLess(fragment.index(r"\setlength{\tabcolsep}{4pt}"), body_start)
                self.assertLess(fragment.index(r"\renewcommand{\arraystretch}{1.20}"), body_start)

    def _validate_table_spacing_fixture(self, spacing: str, suffix: str = "") -> list[str]:
        table = (
            "\n".join(
                (
                    r"\begin{table}[t]",
                    r"\centering",
                    spacing.rstrip("\n"),
                    r"\begin{tabular}{ll}",
                    r"\toprule",
                    r"A & B \\",
                    r"\bottomrule",
                    r"\end{tabular}",
                    r"\label{tab:fixture}",
                    r"\end{table}",
                )
            )
            + "\n"
        )
        table += suffix
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / "paper/latex/generated"
            generated.mkdir(parents=True)
            (generated / "fixture.tex").write_text(table, encoding="utf-8")
            for filename, contents in {
                "pilot_tables_en.tex": "Interpretation Rows have different denominators",
                "pilot_tables_ko.tex": "해석 범위 분모와 성공 방향",
                "live_pilot_tables_en.tex": r"$\Delta$ matched candidates",
                "live_pilot_tables_ko.tex": r"$\Delta$ 동일 후보",
            }.items():
                (generated / filename).write_text(contents, encoding="utf-8")
            for language in ("en", "ko"):
                main = root / f"paper/latex/{language}/main.tex"
                main.parent.mkdir(parents=True, exist_ok=True)
                main.write_text(r"\input{../generated/fixture}" + "\n", encoding="utf-8")
            manifest = {
                "rendered_surfaces": [
                    {
                        "id": "paper-en",
                        "editable_source": {"path": "paper/latex/en/main.tex"},
                    },
                    {
                        "id": "paper-ko",
                        "editable_source": {"path": "paper/latex/ko/main.tex"},
                    },
                ],
                "table_sources": [
                    {
                        "id": "fixture-table",
                        "layout_sources": [{"path": "paper/latex/generated/fixture.tex"}],
                        "rendered_in": ["paper-en", "paper-ko"],
                        "anchors": ["tab:fixture"],
                    }
                ],
            }
            validator = visual_validator.Validator(
                require_pdf_tools=False, check_regeneration=False
            )
            with patch.object(visual_validator, "ROOT", root):
                validator._validate_tables(manifest)
            return validator.errors

    def test_table_spacing_mutations_keep_missing_and_110_floor_checks(self) -> None:
        cases = (
            ("missing", "", "no explicit arraystretch"),
            (
                "below-floor",
                r"\renewcommand{\arraystretch}{1.09}" + "\n",
                "row spacing below the 1.10 floor",
            ),
        )
        for name, spacing, message in cases:
            with self.subTest(spacing=name):
                errors = self._validate_table_spacing_fixture(spacing)
                self.assertTrue(any(message in error for error in errors), errors)

    def test_generated_table_spacing_is_checked_per_table_block(self) -> None:
        cases = (
            ("missing-second", "", "table 2 has no explicit arraystretch"),
            (
                "below-floor-second",
                r"\renewcommand{\arraystretch}{1.05}" + "\n",
                "table 2 row spacing below the 1.10 floor",
            ),
        )
        for name, second_spacing, message in cases:
            second = (
                "\n".join(
                    (
                        r"\begin{table}[t]",
                        r"\centering",
                        second_spacing.rstrip("\n"),
                        r"\begin{tabular}{ll}",
                        r"\toprule",
                        r"A & B \\",
                        r"\bottomrule",
                        r"\end{tabular}",
                        r"\label{tab:second}",
                        r"\end{table}",
                    )
                )
                + "\n"
            )
            with self.subTest(spacing=name):
                errors = self._validate_table_spacing_fixture(
                    r"\renewcommand{\arraystretch}{1.20}" + "\n", second
                )
                self.assertTrue(any(message in error for error in errors), errors)

    def test_generated_standalone_tabular_outside_table_block_is_rejected(self) -> None:
        orphan = r"\begin{tabular}{ll}" + "\n" + r"A & B \\" + "\n" + r"\end{tabular}" + "\n"
        errors = self._validate_table_spacing_fixture(
            r"\renewcommand{\arraystretch}{1.20}" + "\n", orphan
        )
        self.assertTrue(
            any(
                "tabular content exists outside rendered table blocks" in error for error in errors
            ),
            errors,
        )

    def test_unsupported_connector_path_is_not_silently_skipped(self) -> None:
        self.assertIsNone(visual_validator.Validator._path_segments("M0 0 C 1 2, 3 4, 5 6"))
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<path class="connector" d="M0 0 C 10 10, 20 20, 30 30"/>'
            "</svg>"
        )
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_svg_geometry(root, Path("synthetic.svg"))
        self.assertTrue(
            any("unsupported connector path syntax" in error for error in validator.errors)
        )

    def test_halo_does_not_hide_text_to_text_or_container_overlap(self) -> None:
        root = ET.fromstring(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
            "<style>.label { font-size: 24px; }</style>"
            '<rect x="10" y="10" width="80" height="60"/>'
            '<text class="label" x="20" y="45" paint-order="stroke">long halo label</text>'
            '<text class="label" x="20" y="45">second label</text>'
            "</svg>"
        )
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_svg_geometry(root, Path("synthetic.svg"))
        self.assertTrue(any("nearest container" in error for error in validator.errors))
        self.assertTrue(any("text boxes overlap" in error for error in validator.errors))

    def _validate_svg_fixture(self, body: str, *, kind: str) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "paper/latex/figures/fixture.svg"
            path.parent.mkdir(parents=True)
            path.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 100 100">'
                "<title>Fixture chart</title><desc>Contract fixture</desc>"
                "<style>.label { font-size: 28px; }</style>"
                f"{body}</svg>",
                encoding="utf-8",
            )
            validator = visual_validator.Validator(
                require_pdf_tools=False, check_regeneration=False
            )
            with patch.object(visual_validator, "ROOT", root):
                validator._validate_svg(path, paper=True, kind=kind)
            return validator.errors

    def test_chart_accepts_visible_colored_data_marks_or_existing_connectors(self) -> None:
        cases = {
            "colored bar": (
                '<rect class="chart-track" x="10" y="10" width="80" height="80" fill="#eeeeee"/>'
                '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="#1f77b4"/>'
            ),
            "connector": '<path class="connector" d="M10 50 L90 50" stroke="#1f77b4"/>',
        }
        for name, body in cases.items():
            with self.subTest(evidence=name):
                self.assertEqual(self._validate_svg_fixture(body, kind="chart"), [])

    def test_chart_rejects_absent_hidden_zero_or_invisible_data_marks(self) -> None:
        cases = {
            "absent": '<rect class="chart-track" x="10" y="10" width="80" height="80" fill="#eeeeee"/>',
            "hidden": '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="#1f77b4" opacity="0"/>',
            "zero": '<rect class="data-mark" x="20" y="40" width="0" height="45" fill="#1f77b4"/>',
            "invisible": '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="none"/>',
            "display-hidden": '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="#1f77b4" display="none"/>',
            "visibility-hidden": '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="#1f77b4" visibility="hidden"/>',
            "nonfinite-width": '<rect class="data-mark" x="20" y="40" width="nan" height="45" fill="#1f77b4"/>',
            "nonfinite-opacity": '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="#1f77b4" opacity="nan"/>',
        }
        for name, body in cases.items():
            with self.subTest(mark=name):
                errors = self._validate_svg_fixture(body, kind="chart")
                self.assertTrue(
                    any(
                        "chart requires visible data marks or connectors" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_diagram_still_requires_a_connector_even_with_data_marks(self) -> None:
        errors = self._validate_svg_fixture(
            '<rect class="data-mark" x="20" y="40" width="18" height="45" fill="#1f77b4"/>',
            kind="diagram",
        )
        self.assertTrue(any("connector paths are not classed" in error for error in errors), errors)


class HistoricalRegenerationTests(unittest.TestCase):
    def test_historical_sources_remain_available_for_both_regenerations_then_are_removed(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            source_relative = "game-track/godot/scripts/sealed_lighthouse_machine.gd"
            output_relative = "paper/latex/generated/historical-test.tex"
            for relative in (
                "scripts/generate_npc_paper_results.py",
                "research/academic-pipeline/stage-04-pilot",
                "research/academic-pipeline/rq2-live-pilot",
                "research/academic-pipeline/contribution-evidence-matrix.csv",
                "research/academic-pipeline/experiment-evidence-matrix.csv",
                "research/claim-ledger.yaml",
                "game-track/godot/docs/latest/balance-archetypes.json",
                *visual_validator.NPC_REGENERATION_SUPPORT,
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"current checkout bytes")
            output = root / output_relative
            output.parent.mkdir(parents=True)
            output.write_bytes(b"historical snapshot bytes")
            archive_bytes = io.BytesIO()
            with zipfile.ZipFile(archive_bytes, "w") as archive:
                archive.writestr(source_relative, b"historical snapshot bytes")
            historical_roots: list[Path] = []
            staged_roots: list[Path] = []

            def run(command, *, cwd, **kwargs):
                if command[:2] == ["git", "rev-parse"]:
                    return subprocess.CompletedProcess(command, 0, stdout=f"{root.parent}\n")
                if command[:2] == ["git", "archive"]:
                    expected_tree = "fa9fb8a2c2249e35eddc7d4e0951c15a7b4bea09:project"
                    if expected_tree not in command:
                        raise subprocess.CalledProcessError(
                            128, command, stderr="unknown historical tree"
                        )
                    return subprocess.CompletedProcess(command, 0, stdout=archive_bytes.getvalue())
                if "scripts/generate_npc_paper_results.py" in command:
                    evidence_root = Path(command[command.index("--evidence-root") + 1])
                    historical_roots.append(evidence_root)
                    staged_roots.append(Path(cwd))
                    generated = Path(cwd) / output_relative
                    generated.parent.mkdir(parents=True, exist_ok=True)
                    generated.write_bytes((evidence_root / source_relative).read_bytes())
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=True)
            with (
                patch.object(visual_validator, "ROOT", root),
                patch.object(visual_validator, "LIGHTWEIGHT_OUTPUTS", (output_relative,)),
                patch.object(visual_validator.subprocess, "run", side_effect=run),
            ):
                validator._validate_lightweight_regeneration({})

            self.assertEqual(validator.errors, [])
            self.assertEqual(len(historical_roots), 2)
            self.assertEqual(historical_roots[0], historical_roots[1])
            self.assertTrue(all(not path.exists() for path in historical_roots + staged_roots))
            self.assertEqual((root / source_relative).read_bytes(), b"current checkout bytes")
            self.assertEqual(output.read_bytes(), b"historical snapshot bytes")

    def test_historical_extraction_ignores_inherited_hook_git_context_for_selected_subtree(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            root = repository / "neuro-symbolic-interactive-game-research-2026"
            source_relative = "game-track/godot/scripts/sealed_lighthouse_machine.gd"
            output_relative = "paper/latex/generated/historical-hook-env-test.tex"
            for relative in (
                "scripts/generate_npc_paper_results.py",
                "research/academic-pipeline/stage-04-pilot",
                "research/academic-pipeline/rq2-live-pilot",
                "research/academic-pipeline/contribution-evidence-matrix.csv",
                "research/academic-pipeline/experiment-evidence-matrix.csv",
                "research/claim-ledger.yaml",
                "game-track/godot/docs/latest/balance-archetypes.json",
                *visual_validator.NPC_REGENERATION_SUPPORT,
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"current checkout bytes")
            output = root / output_relative
            output.parent.mkdir(parents=True)
            output.write_bytes(b"historical snapshot bytes")
            archive_bytes = io.BytesIO()
            with zipfile.ZipFile(archive_bytes, "w") as archive:
                archive.writestr(source_relative, b"historical snapshot bytes")
            archive_commands: list[tuple[list[str], dict[str, str]]] = []
            discovery_environments: list[dict[str, str]] = []
            historical_roots: list[Path] = []
            staged_roots: list[Path] = []
            local_git_context = {
                "GIT_DIR": "relative-hook-worktree/.git",
                "GIT_WORK_TREE": "relative-hook-worktree",
                "GIT_IMPLICIT_WORK_TREE": "true",
                "GIT_COMMON_DIR": "relative-common",
                "GIT_INDEX_FILE": "relative-hook-index",
                "GIT_OBJECT_DIRECTORY": "relative-object",
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": "relative-alternate",
                "GIT_PREFIX": "relative-prefix",
                "GIT_GRAFT_FILE": "relative-graft",
                "GIT_SHALLOW_FILE": "relative-shallow",
                "GIT_REPLACE_REF_BASE": "relative-replace",
            }
            preserved_environment = {
                "TRACE_PARENT_MARKER": "parent-preserved",
                "PYTHONDONTWRITEBYTECODE": "safety-preserved",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "safe.option",
                "GIT_CONFIG_VALUE_0": "preserved",
                "GIT_NO_REPLACE_OBJECTS": "1",
                "GIT_SSH_COMMAND": "ssh-safe-wrapper",
                "GIT_TERMINAL_PROMPT": "0",
            }

            def run(command, *, cwd, **kwargs):
                effective_env = dict(kwargs.get("env", os.environ))
                if command[:3] == ["git", "rev-parse", "--local-env-vars"]:
                    return subprocess.CompletedProcess(
                        command,
                        0,
                        stdout="GIT_DIR\nGIT_WORK_TREE\nGIT_INDEX_FILE\n",
                    )
                if command[:2] == ["git", "rev-parse"]:
                    discovery_environments.append(effective_env)
                    git_root = (
                        root
                        if any(effective_env.get(key) for key in local_git_context)
                        else repository
                    )
                    return subprocess.CompletedProcess(command, 0, stdout=f"{git_root}\n")
                if command[:2] == ["git", "archive"]:
                    archive_commands.append((command, effective_env))
                    expected_tree = (
                        "fa9fb8a2c2249e35eddc7d4e0951c15a7b4bea09:"
                        "neuro-symbolic-interactive-game-research-2026"
                    )
                    if expected_tree not in command:
                        raise subprocess.CalledProcessError(
                            128, command, stderr="wrong historical subtree"
                        )
                    return subprocess.CompletedProcess(command, 0, stdout=archive_bytes.getvalue())
                if "scripts/generate_npc_paper_results.py" in command:
                    evidence_root = Path(command[command.index("--evidence-root") + 1])
                    historical_roots.append(evidence_root)
                    staged_roots.append(Path(cwd))
                    generated = Path(cwd) / output_relative
                    generated.parent.mkdir(parents=True, exist_ok=True)
                    generated.write_bytes((evidence_root / source_relative).read_bytes())
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

            with patch.dict(
                os.environ, {**local_git_context, **preserved_environment}, clear=False
            ):
                parent_environment = dict(os.environ)
                validator = visual_validator.Validator(
                    require_pdf_tools=False, check_regeneration=True
                )
                with (
                    patch.object(visual_validator, "ROOT", root),
                    patch.object(visual_validator, "LIGHTWEIGHT_OUTPUTS", (output_relative,)),
                    patch.object(visual_validator.subprocess, "run", side_effect=run),
                ):
                    validator._validate_lightweight_regeneration({})
                self.assertEqual(dict(os.environ), parent_environment)

            self.assertEqual(validator.errors, [])
            self.assertEqual(len(archive_commands), 1)
            self.assertEqual(len(discovery_environments), 1)
            archive_command, archive_environment = archive_commands[0]
            for child_environment in [discovery_environments[0], archive_environment]:
                for key in local_git_context:
                    self.assertNotIn(key, child_environment)
                for key, value in preserved_environment.items():
                    self.assertEqual(child_environment[key], value)
            self.assertIn(
                "fa9fb8a2c2249e35eddc7d4e0951c15a7b4bea09:"
                "neuro-symbolic-interactive-game-research-2026",
                archive_command,
            )
            self.assertEqual(len(historical_roots), 2)
            self.assertEqual(historical_roots[0], historical_roots[1])
            self.assertTrue(all(not path.exists() for path in historical_roots + staged_roots))
            self.assertEqual((root / source_relative).read_bytes(), b"current checkout bytes")
            self.assertEqual(output.read_bytes(), b"historical snapshot bytes")

    def test_historical_extraction_failures_stop_before_any_generator_or_success_note(self) -> None:
        failures = (
            (
                "git failure",
                subprocess.CalledProcessError(128, ["git", "archive"], stderr="missing commit"),
            ),
            ("archive unreadable", OSError("archive unavailable")),
            ("invalid archive", b"not a zip archive"),
        )
        for name, failure in failures:
            with self.subTest(failure=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "project"
                root.mkdir()
                generator_commands = []

                def run(
                    command,
                    *,
                    root=root,
                    failure=failure,
                    generator_commands=generator_commands,
                    **kwargs,
                ):
                    if command[:2] == ["git", "rev-parse"]:
                        return subprocess.CompletedProcess(command, 0, stdout=f"{root.parent}\n")
                    if command[:2] == ["git", "archive"]:
                        if isinstance(failure, Exception):
                            raise failure
                        return subprocess.CompletedProcess(command, 0, stdout=failure)
                    generator_commands.append(command)
                    return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

                validator = visual_validator.Validator(
                    require_pdf_tools=False, check_regeneration=True
                )
                with (
                    patch.object(visual_validator, "ROOT", root),
                    patch.object(visual_validator.subprocess, "run", side_effect=run),
                ):
                    validator._validate_lightweight_regeneration({})

                self.assertEqual(len(validator.errors), 1)
                self.assertIn("historical NPC source extraction failed", validator.errors[0])
                self.assertEqual(generator_commands, [])
                self.assertEqual(validator.notes, [])


class PublicationLinkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.papers = tuple(
            self.root / f"paper/latex/{language}/main.tex" for language in ("en", "ko")
        )
        for paper in self.papers:
            paper.parent.mkdir(parents=True)
            paper.write_text("\\section{Publication}\n", encoding="utf-8")

    def validate_links(self, manifest: dict) -> list[str]:
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        with (
            patch.object(visual_validator, "ROOT", self.root),
            patch.object(visual_validator, "PAPER_MAIN", self.papers),
        ):
            validator._validate_paper_links(manifest)
        return validator.errors

    def figure_manifest(self, rendered_path: str = "paper/latex/figures/current.pdf") -> dict:
        return {
            "visual_assets": [
                {
                    "id": "current-figure",
                    "publication_role": "current-figure",
                    "used_by": [str(path.relative_to(self.root)) for path in self.papers],
                    "editable_sources": [{"path": "paper/latex/figures/current.svg"}],
                    "rendered": [{"path": rendered_path}],
                }
            ]
        }

    def write_figure_wrapper(self, wrapper: str, target: str = "current.pdf") -> None:
        for paper in self.papers:
            paper.write_text(wrapper.replace("target", f"../figures/{target}"), encoding="utf-8")

    def test_columnwidth_remains_accepted_for_a_single_column_figure(self) -> None:
        self.write_figure_wrapper(
            r"""\begin{figure}[t]
\includegraphics[width=\columnwidth]{target}
\end{figure}
"""
        )
        self.assertEqual(self.validate_links(self.figure_manifest()), [])

    def test_textwidth_is_accepted_only_inside_a_real_full_width_figure(self) -> None:
        self.write_figure_wrapper(
            r"""\begin{figure*}[t]
\includegraphics[width=\textwidth]{target}
\end{figure*}
"""
        )
        self.assertEqual(self.validate_links(self.figure_manifest()), [])

    def test_single_column_textwidth_and_custom_or_narrow_widths_are_rejected(self) -> None:
        cases = {
            "single-column textwidth": r"""\begin{figure}[t]
\includegraphics[width=\textwidth]{target}
\end{figure}
""",
            "narrow columnwidth": r"""\begin{figure}[t]
\includegraphics[width=0.9\columnwidth]{target}
\end{figure}
""",
            "custom textwidth": r"""\begin{figure*}[t]
\includegraphics[width=0.9\textwidth]{target}
\end{figure*}
""",
            "omitted width": r"""\begin{figure}[t]
\includegraphics{target}
\end{figure}
""",
            "full-width height override": r"""\begin{figure*}[t]
\includegraphics[width=\textwidth,height=1pt]{target}
\end{figure*}
""",
            "column scale override": r"""\begin{figure}[t]
\includegraphics[width=\columnwidth,scale=0.1]{target}
\end{figure}
""",
        }
        for name, wrapper in cases.items():
            with self.subTest(width_contract=name):
                self.write_figure_wrapper(wrapper)
                errors = self.validate_links(self.figure_manifest())
                self.assertTrue(
                    any("must use the legible single-column contract" in error for error in errors),
                    errors,
                )

    def test_raw_raster_inclusion_is_rejected_even_when_owned(self) -> None:
        self.write_figure_wrapper(
            r"""\begin{figure}[t]
\includegraphics[width=\columnwidth]{target}
\end{figure}
""",
            target="current.png",
        )
        errors = self.validate_links(self.figure_manifest("paper/latex/figures/current.png"))
        self.assertTrue(any("raster paper figure inclusion" in error for error in errors), errors)

    def test_retained_optional_figure_does_not_require_inclusion_but_current_figure_requires_each_owner(
        self,
    ) -> None:
        manifest = {
            "visual_assets": [
                {
                    "id": "current-signals",
                    "publication_role": "current-figure",
                    "used_by": [str(path.relative_to(self.root)) for path in self.papers],
                    "editable_sources": [{"path": "paper/latex/figures/current.svg"}],
                    "rendered": [{"path": "paper/latex/figures/current.pdf"}],
                },
                {
                    "id": "optional-comparison",
                    "publication_role": "retained-optional",
                    "used_by": [],
                    "editable_sources": [{"path": "paper/latex/figures/comparison.svg"}],
                    "rendered": [{"path": "paper/latex/figures/comparison.pdf"}],
                    "represented_by": {
                        "table_source_id": "disclosure-tables",
                        "anchor": "tab:disclosure-arms",
                    },
                },
            ],
            "table_sources": [
                {
                    "id": "disclosure-tables",
                    "anchors": ["tab:disclosure-arms"],
                    "rendered_in": ["paper-en", "paper-ko"],
                }
            ],
        }
        for paper in self.papers:
            paper.write_text(
                "\\includegraphics[width=\\columnwidth]{../figures/current.pdf}\n", encoding="utf-8"
            )
        self.assertEqual(self.validate_links(manifest), [])

        self.papers[1].write_text("\\section{Missing current figure}\n", encoding="utf-8")
        self.assertEqual(
            self.validate_links(manifest),
            ["paper/latex/ko/main.tex: must include vector for current-signals"],
        )

    def test_nested_input_graphic_not_declared_in_manifest_is_rejected(self) -> None:
        generated = self.root / "paper/latex/generated"
        (generated / "sections").mkdir(parents=True)
        (generated / "tables.tex").write_text("\\input{sections/figure}\n", encoding="utf-8")
        (generated / "sections/figure.tex").write_text(
            "\\includegraphics[width=\\columnwidth]{../../figures/unlisted.pdf}\n", encoding="utf-8"
        )
        self.papers[0].write_text("\\input{../generated/tables}\n", encoding="utf-8")
        self.assertEqual(
            self.validate_links({}),
            ["paper/latex/en/main.tex: unmanifested graphics ['paper/latex/figures/unlisted.pdf']"],
        )

    def test_unused_macro_and_comments_do_not_render_but_invoking_macro_follows_its_input(
        self,
    ) -> None:
        section = self.root / "paper/latex/generated/comparison.tex"
        section.parent.mkdir(parents=True)
        section.write_text(
            "\\includegraphics[width=\\columnwidth]{../figures/comparison.pdf}\n", encoding="utf-8"
        )
        definitions = (
            "\\newcommand{\\comparisonfigure}{\\input{../generated/comparison}}\n"
            "% \\input{missing-commented-input}\n"
            "% \\includegraphics{../figures/commented.pdf}\n"
            "\\section{Results}\n"
        )
        self.papers[0].write_text(definitions, encoding="utf-8")
        self.assertEqual(self.validate_links({}), [])
        self.papers[0].write_text(definitions + "\\comparisonfigure\n", encoding="utf-8")
        self.assertEqual(
            self.validate_links({}),
            [
                "paper/latex/en/main.tex: unmanifested graphics ['paper/latex/figures/comparison.pdf']"
            ],
        )

    def test_nested_current_figure_is_accepted_by_both_visual_and_paper_link_gates(self) -> None:
        generated = self.root / "paper/latex/generated/figure.tex"
        generated.parent.mkdir(parents=True)
        generated.write_text(
            "\\includegraphics[width=\\columnwidth]{../figures/nested.pdf}\n", encoding="utf-8"
        )
        figures = self.root / "paper/latex/figures"
        figures.mkdir()
        (figures / "nested.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 200 100">'
            "<title>Nested diagram</title><desc>Reachable publication fixture</desc>"
            "<style>.label { font-size: 28px; }</style>"
            '<path class="connector" d="M10 20 L100 20"/></svg>',
            encoding="utf-8",
        )
        (figures / "nested.pdf").write_bytes(b"%PDF test fixture")
        for paper in self.papers:
            paper.write_text("\\input{../generated/figure}\n", encoding="utf-8")
        manifest = {
            "visual_assets": [
                {
                    "id": "nested-current",
                    "publication_role": "current-figure",
                    "used_by": [str(path.relative_to(self.root)) for path in self.papers],
                    "editable_sources": [{"path": "paper/latex/figures/nested.svg"}],
                    "rendered": [{"path": "paper/latex/figures/nested.pdf"}],
                    "generator": {"path": "scripts/generate_nested.py"},
                }
            ]
        }
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        with (
            patch.object(visual_validator, "ROOT", self.root),
            patch.object(visual_validator, "PAPER_MAIN", self.papers),
            patch.object(visual_validator.shutil, "which", return_value=None),
        ):
            validator._validate_visual_assets(manifest)
            validator._validate_paper_links(manifest)
        self.assertEqual(validator.errors, [])

    def test_parameterized_graphics_macro_fails_closed_only_when_invoked(self) -> None:
        definition = "\\newcommand{\\customfigure}[1]{\\includegraphics[width=\\columnwidth]{../figures/#1.pdf}}\n"
        self.papers[0].write_text(definition + "\\section{Results}\n", encoding="utf-8")
        self.assertEqual(self.validate_links({}), [])
        self.papers[0].write_text(definition + "\\customfigure{unlisted}\n", encoding="utf-8")
        errors = self.validate_links({})
        self.assertEqual(len(errors), 1)
        self.assertIn("unsupported parameterized macro", errors[0])

    def test_macro_defined_by_prior_input_cannot_hide_unmanifested_graphic(self) -> None:
        definitions = self.root / "paper/latex/generated/definitions.tex"
        definitions.parent.mkdir(parents=True)
        definitions.write_text(
            "\\newcommand{\\latefigure}{\\includegraphics[width=\\columnwidth]{../figures/unlisted.pdf}}\n",
            encoding="utf-8",
        )
        self.papers[0].write_text(
            "\\input{../generated/definitions}\n\\latefigure\n", encoding="utf-8"
        )
        self.assertEqual(
            self.validate_links({}),
            ["paper/latex/en/main.tex: unmanifested graphics ['paper/latex/figures/unlisted.pdf']"],
        )


if __name__ == "__main__":
    unittest.main()
