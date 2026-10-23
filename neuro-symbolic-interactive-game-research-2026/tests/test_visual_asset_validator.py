from __future__ import annotations

import copy
import io
import json
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
            if item["id"] == "offline-pilot-paper-tables"
        )
        source["rendered_in"] = ["paper-missing"]
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_tables(unknown_surface)
        self.assertTrue(any("unknown rendered surfaces" in error for error in validator.errors))

        missing_anchor = copy.deepcopy(manifest)
        source = next(
            item
            for item in missing_anchor["table_sources"]
            if item["id"] == "offline-pilot-paper-tables"
        )
        source["anchors"].append("tab:not-present")
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        validator._validate_tables(missing_anchor)
        self.assertTrue(any("missing table anchor" in error for error in validator.errors))

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
