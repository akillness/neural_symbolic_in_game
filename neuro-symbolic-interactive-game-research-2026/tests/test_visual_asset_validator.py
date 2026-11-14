from __future__ import annotations

import base64
import copy
import hashlib
import io
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
import zlib
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_visual_assets as visual_validator


class BoundCaptureMontageTests(unittest.TestCase):
    def _fixture(self, root, *, dimensions=(1280, 720), non_png=False):
        def png_chunk(kind, payload):
            checksum = zlib.crc32(kind + payload) & 0xFFFFFFFF
            return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

        def write_receipt(relative, payload):
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            return {
                "path": relative,
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }

        captures = []
        images = []
        width, height = dimensions
        for index in range(4):
            payload = (
                b"\x89PNG\r\n\x1a\n"
                + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                + png_chunk(
                    b"IDAT",
                    zlib.compress((b"\x00" + bytes([index * 60, 0, 0, 255]) * width) * height),
                )
                + png_chunk(b"IEND", b"")
            )
            if non_png:
                payload = f"not a PNG capture {index}".encode()
            captures.append(write_receipt(f"captures/panel-{index}.png", payload))
            encoded = base64.b64encode(payload).decode("ascii")
            images.append(
                f'<image x="{index * 100}" y="0" width="100" height="56.25" '
                f'href="data:image/png;base64,{encoded}"/>'
            )
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" role="img" viewBox="0 0 400 100">'
            "<title>Bound captures</title><desc>Four immutable engine panels</desc>"
            "<style>.label { font-size: 28px; }</style>" + "".join(images) + "</svg>"
        )
        source = write_receipt("paper/latex/figures/fig_engine_cutscenes.svg", svg.encode())
        rendered = write_receipt("paper/latex/figures/fig_engine_cutscenes.pdf", b"%PDF fixture\n")
        generator = write_receipt(
            "scripts/generate_engine_cutscene_figure.py", b"fixture generator\n"
        )
        return {
            "id": "paper-engine-cutscenes",
            "kind": "engine-capture-montage",
            "editable_sources": [source],
            "rendered": [rendered],
            "generator": generator,
            "data_sources": captures,
            "used_by": [],
        }

    def _validate(self, root, asset, *, pdf_mutation=None):
        svg = root / asset["editable_sources"][0]["path"]

        def pdf_tool(command, **kwargs):
            if command[0] == "pdfimages":
                images = [("image", 1280, 720)] * 4
                if pdf_mutation == "flattened":
                    images = [("image", 1600, 400)]
                elif pdf_mutation == "extra-image":
                    images.append(("image", 1280, 720))
                elif pdf_mutation == "missing-image":
                    images.pop()
                elif pdf_mutation == "wrong-pdf-dimensions":
                    images[0] = ("image", 1279, 720)
                elif pdf_mutation in {
                    "alpha-masks",
                    "partial-mask",
                    "wrong-mask-dimensions",
                    "extra-mask",
                }:
                    count = {"partial-mask": 1, "extra-mask": 5}.get(pdf_mutation, 4)
                    images.extend([("smask", 1280, 720)] * count)
                    if pdf_mutation == "wrong-mask-dimensions":
                        images[-1] = ("smask", 1280, 719)
                elif pdf_mutation == "unsupported-image-type":
                    images.append(("mask", 1280, 720))
                output = "".join(
                    f"1 {index} {kind} {width} {height} rgb 3 8 image no {index + 1} 0 72 72 1B 100%\n"
                    for index, (kind, width, height) in enumerate(images)
                )
            elif command[0] == "pdffonts":
                output = "Helvetica Type 3" if pdf_mutation == "font" else "Helvetica Type 1"
            elif command[0] == "pdfinfo":
                digest = (
                    "0" * 64
                    if pdf_mutation == "source"
                    else hashlib.sha256(svg.read_bytes()).hexdigest()
                )
                size = "100 x 100" if pdf_mutation == "aspect" else "400 x 100"
                output = f"Title: source-sha256:{digest}\nPage size: {size} pts\n"
            else:
                raise AssertionError(f"Unexpected external PDF tool: {command}")
            return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

        validator = visual_validator.Validator(require_pdf_tools=True, check_regeneration=False)
        with (
            patch.object(visual_validator, "ROOT", root),
            patch.object(visual_validator.shutil, "which", return_value="/fixture/pdf-tool"),
            patch.object(visual_validator.subprocess, "run", side_effect=pdf_tool),
        ):
            validator._validate_receipts({"visual_assets": [asset]})
            validator._validate_visual_assets({"visual_assets": [asset]})
        return validator

    def test_only_byte_bound_four_panel_capture_montage_admits_pdf_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = self._fixture(root)
            self.assertEqual(self._validate(root, asset).errors, [])
            for kind in ("chart", "diagram"):
                with self.subTest(kind=kind):
                    asset["kind"] = kind
                    errors = self._validate(root, asset).errors
                    self.assertTrue(
                        any(
                            "contains raster image objects instead of vectors" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_capture_missing_digest_and_embedded_image_corruption_fail_closed(self):
        for mutation in (
            "missing-source",
            "changed-source",
            "missing-receipt",
            "duplicate-receipt",
            "changed-image",
            "duplicate-image",
            "missing-image",
            "external-image",
            "invalid-base64",
            "wrong-asset-id",
            "none-data-sources",
            "mapping-data-sources",
            "invalid-data-source-entry",
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                asset = self._fixture(root)
                path = root / asset["data_sources"][0]["path"]
                svg = root / asset["editable_sources"][0]["path"]
                if mutation == "missing-source":
                    path.unlink()
                    expected = "manifest receipt is missing"
                elif mutation == "changed-source":
                    payload = path.read_bytes()
                    path.write_bytes(payload[:-1] + bytes([payload[-1] ^ 1]))
                    expected = "SHA-256 drift"
                else:
                    expected = "capture montage"
                    if mutation == "none-data-sources":
                        asset["data_sources"] = None
                    elif mutation == "mapping-data-sources":
                        asset["data_sources"] = {"unexpected": "container"}
                    elif mutation == "invalid-data-source-entry":
                        asset["data_sources"] = [None]
                    elif mutation == "missing-receipt":
                        asset["data_sources"].pop()
                    elif mutation == "duplicate-receipt":
                        asset["data_sources"][1] = copy.deepcopy(asset["data_sources"][0])
                    elif mutation == "wrong-asset-id":
                        asset["id"] = "unapproved-raster-figure"
                    else:
                        tree = ET.parse(svg)
                        images = tree.getroot().findall("{http://www.w3.org/2000/svg}image")
                        if mutation == "missing-image":
                            tree.getroot().remove(images[0])
                        elif mutation == "duplicate-image":
                            images[1].set("href", images[0].attrib["href"])
                        elif mutation == "external-image":
                            images[0].set("href", "file:///unbound.png")
                        elif mutation == "invalid-base64":
                            images[0].set("href", "data:image/png;base64,%%%")
                        else:
                            payload = path.read_bytes()
                            changed = payload[:-1] + bytes([payload[-1] ^ 1])
                            images[0].set(
                                "href",
                                "data:image/png;base64,"
                                + base64.b64encode(changed).decode("ascii"),
                            )
                        tree.write(svg, encoding="utf-8")
                        payload = svg.read_bytes()
                        asset["editable_sources"][0].update(
                            bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest()
                        )
                validator = self._validate(root, asset)
                self.assertTrue(
                    any(expected in error for error in validator.errors), validator.errors
                )
                self.assertTrue(
                    any(
                        "contains raster image objects instead of vectors" in error
                        for error in validator.errors
                    ),
                    "An unbound capture must not receive the PDF raster exception: "
                    + repr(validator.errors),
                )
                with self.assertRaises(SystemExit):
                    validator._finish()

    def test_capture_rejects_receipted_wrong_source_kind_or_intrinsic_dimensions(self):
        for dimensions, non_png in (
            ((1, 1), False),
            ((1279, 720), False),
            ((1280, 719), False),
            ((1280, 720), True),
        ):
            with (
                self.subTest(dimensions=dimensions, non_png=non_png),
                tempfile.TemporaryDirectory() as directory,
            ):
                root = Path(directory)
                asset = self._fixture(root, dimensions=dimensions, non_png=non_png)
                validator = self._validate(root, asset)
                self.assertTrue(
                    any("capture montage" in error for error in validator.errors), validator.errors
                )
                self.assertTrue(
                    any(
                        "contains raster image objects instead of vectors" in error
                        for error in validator.errors
                    ),
                    validator.errors,
                )
                with self.assertRaises(SystemExit):
                    validator._finish()

    def test_capture_pdf_admits_exact_four_panels_with_or_without_four_alpha_masks(self):
        for mutation in (None, "alpha-masks"):
            with self.subTest(pdf_images=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                validator = self._validate(root, self._fixture(root), pdf_mutation=mutation)
                self.assertEqual(validator.errors, [])

    def test_capture_pdf_rejects_flattened_extra_missing_or_wrong_size_image_objects(self):
        for mutation in (
            "flattened",
            "extra-image",
            "missing-image",
            "wrong-pdf-dimensions",
            "partial-mask",
            "extra-mask",
            "wrong-mask-dimensions",
            "unsupported-image-type",
        ):
            with self.subTest(pdf_images=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                validator = self._validate(root, self._fixture(root), pdf_mutation=mutation)
                self.assertTrue(
                    any("capture montage" in error for error in validator.errors), validator.errors
                )
                with self.assertRaises(SystemExit):
                    validator._finish()

    def test_capture_exception_preserves_pdf_source_font_and_aspect_checks(self):
        for mutation, expected in (
            ("source", "embedded SVG source hash is stale"),
            ("font", "Type 3 fallback font"),
            ("aspect", "PDF/SVG aspect ratios differ"),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                validator = self._validate(root, self._fixture(root), pdf_mutation=mutation)
                self.assertTrue(
                    any(expected in error for error in validator.errors), validator.errors
                )
                with self.assertRaises(SystemExit):
                    validator._finish()


class PublicCaptureProjectionTests(unittest.TestCase):
    def test_public_projection_binds_all_files_without_rewriting_original_capture_pixels(self):
        import update_visual_source_manifest as manifest_builder

        relative_root = (
            "_workspace/current/engineering/tech-verification/evidence/"
            "godot-4.7.1-20261113t151426z-paper-native3d-v1"
        )
        public_root = ROOT / relative_root
        projection_path = public_root / "public-path-projection-v1.json"
        projection = json.loads(projection_path.read_text(encoding="utf-8"))
        records = {record["file"]: record for record in projection["files"]}
        self.assertEqual(len(records), len(projection["files"]), "duplicate projection file paths")
        self.assertEqual(
            set(records),
            {
                str(path.relative_to(public_root))
                for path in public_root.rglob("*")
                if path.is_file() and path != projection_path
            },
        )
        derivative_paths = {
            "process-capture-metadata.json",
            "provenance.json",
            "process-logs/canonical-fixture.log",
            "process-logs/capture-arrival.log",
            "process-logs/capture-authorized_hint.log",
            "process-logs/capture-ending.log",
            "process-logs/capture-refusal.log",
        }
        self.assertEqual(
            {
                name
                for name, record in records.items()
                if record["classification"] == "public-path-relocated-derivative"
            },
            derivative_paths,
        )
        unchanged = set(records) - derivative_paths
        self.assertEqual((len(records), len(derivative_paths), len(unchanged)), (21, 7, 14))
        self.assertEqual(projection["counts"]["original_files"], len(records))
        self.assertEqual(projection["counts"]["transformed_existing_files"], len(derivative_paths))
        self.assertEqual(projection["counts"]["unchanged_original_files"], len(unchanged))
        for name, record in records.items():
            with self.subTest(public_file=name):
                path = (public_root / name).resolve()
                self.assertTrue(
                    path.is_relative_to(public_root.resolve()), "not a public capture path"
                )
                payload = path.read_bytes()
                self.assertEqual(
                    record["public"],
                    {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()},
                )
                if name in unchanged:
                    self.assertEqual(record["classification"], "unchanged-original-bytes")
                    self.assertEqual(record["original"], record["public"])
                else:
                    self.assertNotEqual(record["original"]["sha256"], record["public"]["sha256"])
        png_identities = {
            "arrival": (330730, "381ade4db31d68dd971f2bc1d11adf619d5dd24b94492430c6561aa09f1d91f4"),
            "authorized_hint": (
                375315,
                "ef7b5d2ac230303d77f08c54a784f8261ec1ff82c910dec731fd895ab4124e00",
            ),
            "ending": (406731, "986bb850e064bc615e66262e29c318b103c1547928bc8336a3989aac1ac3e7fc"),
            "refusal": (481240, "34ab2b20eb56222560d917546c71f97d61fa7f3f92b057a4ea3bf7d35253c9f5"),
        }
        for stage, (byte_count, digest) in png_identities.items():
            with self.subTest(original_png=stage):
                expected = {"bytes": byte_count, "sha256": digest}
                self.assertEqual(records[f"native3d/{stage}.png"]["original"], expected)
                self.assertEqual(projection["validation"]["png_identity"][stage], expected)
        asset = next(
            item
            for item in manifest_builder.build_manifest()["visual_assets"]
            if item["id"] == "paper-engine-cutscenes"
        )
        registered = {record["path"]: record for record in asset["data_sources"]}
        for name in (
            "public-path-projection-v1.json",
            *(f"native3d/{stage}.png" for stage in png_identities),
        ):
            with self.subTest(manifest_receipt=name):
                payload = (public_root / name).read_bytes()
                relative = f"{relative_root}/{name}"
                self.assertEqual(
                    registered[relative],
                    {
                        "path": relative,
                        "bytes": len(payload),
                        "sha256": hashlib.sha256(payload).hexdigest(),
                    },
                )


class PaperRetirementManifestTests(unittest.TestCase):
    def test_manifest_keeps_active_figures_tables_and_evidence_without_retired_presentations(self):
        import update_visual_source_manifest as manifest_builder

        manifest = manifest_builder.build_manifest()
        assets = {asset["id"]: asset for asset in manifest["visual_assets"]}
        expected_figures = {
            "paper-architecture": "fig_architecture",
            "paper-signal-mechanism": "fig_signal_mechanism",
            "paper-disclosure-signals": "fig_disclosure_signals",
            "state-signal": "fig_state_signal",
            "paired-feedback-flow": "fig_paired_feedback_flow",
            "paper-runtime-comparison": "fig_runtime_comparison",
            "paper-engine-cutscenes": "fig_engine_cutscenes",
        }
        for asset_id, stem in expected_figures.items():
            with self.subTest(figure=stem):
                asset = assets[asset_id]
                self.assertEqual(asset["publication_role"], "current-figure")
                self.assertEqual(
                    set(asset["used_by"]), {"paper/latex/en/main.tex", "paper/latex/ko/main.tex"}
                )
                self.assertEqual(
                    {record["path"] for record in asset["rendered"] + asset["editable_sources"]},
                    {f"paper/latex/figures/{stem}.{suffix}" for suffix in ("svg", "png", "pdf")},
                )
        self.assertTrue(
            {
                "current-paper-hand-authored-tables",
                "paired-feedback-v5",
                "traceability-supplement-table",
                "disclosure-paper-tables",
                "runtime-comparison-results-en",
                "runtime-comparison-results-ko",
                "runtime-comparison-tables-en",
                "runtime-comparison-tables-ko",
                "runtime-identity-extension-en",
                "runtime-identity-extension-ko",
                "offline-pilot-paper-tables",
                "review-boundary-audit-paper-tables",
                "contribution-and-lane-paper-tables",
                "npc-goal-recovery-paper-tables",
                "kg-ontology-paper-fragments",
                "stage-04-conformance-table-bundle",
            }
            <= {source["id"] for source in manifest["table_sources"]},
        )
        receipts = list(
            visual_validator.Validator(
                require_pdf_tools=False, check_regeneration=False
            )._iter_receipts(manifest)
        )
        paths = {record["path"] for record in receipts}
        npc_root = "research/academic-pipeline/npc-goal-recovery/verified-run-006"
        signal_root = "research/npc-disclosure/results-signal-explainer-20261023-r5"
        required_data = {
            *(
                f"{npc_root}/{name}"
                for name in (
                    "aggregate.json",
                    "screening-assignment-manifest.json",
                    "engineering-results.jsonl",
                    "screening-results.jsonl",
                    "replay-results.json",
                    "sha256-manifest.json",
                )
            ),
            *(
                f"{signal_root}/{name}"
                for name in (
                    "disclosure-trace.jsonl",
                    "comparison-summary.json",
                    "factual-summary.json",
                    "metadata.json",
                )
            ),
            "research/npc-disclosure/reveal-hint-expectations-v1.json",
            "research/npc-disclosure/reveal-hint-expectations-v1.sha256",
            "research/simulation/kg-ontology/latest/evaluation-matrix.json",
            "research/simulation/kg-ontology/latest/strategy-trials.tsv",
            "game-track/godot/docs/latest/balance-archetypes.json",
            "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
            "research/runtime-model-swap-20261024/codex-identity-20261026/public-results-v1/results.json",
            *(
                f"research/codex_feedback_pilot/public-v5/paired-model-comparison-20261110-v5-gpt-5.6-{model}/results.json"
                for model in ("luna", "terra")
            ),
            "research/codex_feedback_pilot/paired-model-comparison-20261110-v5-source.zip",
        }
        self.assertTrue(required_data <= paths, sorted(required_data - paths))
        for record in receipts:
            with self.subTest(receipt=record["path"]):
                payload = (ROOT / record["path"]).read_bytes()
                self.assertEqual(record["bytes"], len(payload))
                self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertEqual(
            set(assets),
            set(expected_figures) | {"kg-ontology-evaluation-matrix", "game-balance-archetypes"},
        )

    def test_active_asset_missing_and_same_size_digest_drift_remain_hard_errors(self):
        import update_visual_source_manifest as manifest_builder

        manifest = manifest_builder.build_manifest()
        record = next(
            asset for asset in manifest["visual_assets"] if asset["id"] == "paper-signal-mechanism"
        )["editable_sources"][0]
        payload = (ROOT / record["path"]).read_bytes()
        for mutation, expected in (
            ("missing", f"manifest receipt is missing: {record['path']}"),
            ("digest", f"SHA-256 drift: {record['path']}"),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                path = root / record["path"]
                if mutation == "digest":
                    path.parent.mkdir(parents=True)
                    path.write_bytes(bytes([payload[0] ^ 1]) + payload[1:])
                validator = visual_validator.Validator(
                    require_pdf_tools=False, check_regeneration=False
                )
                with patch.object(visual_validator, "ROOT", root):
                    validator._validate_receipts(
                        {"visual_assets": [{"editable_sources": [record]}]}
                    )
                self.assertEqual(validator.errors, [expected])
                with self.assertRaisesRegex(SystemExit, "failed with 1 error"):
                    validator._finish()


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
                "scripts/generate_paired_feedback_figures.py",
                "scripts/generate_paper_results.py",
                "research/academic-pipeline/stage-04-pilot",
                "research/academic-pipeline/rq2-live-pilot",
                "research/academic-pipeline/contribution-evidence-matrix.csv",
                "research/academic-pipeline/experiment-evidence-matrix.csv",
                "research/claim-ledger.yaml",
                "game-track/godot/docs/latest/balance-archetypes.json",
                *visual_validator.NPC_REGENERATION_SUPPORT,
                *visual_validator.RUNTIME_COMPARISON_REGENERATION_SUPPORT,
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
                "scripts/generate_paired_feedback_figures.py",
                "scripts/generate_paper_results.py",
                "research/academic-pipeline/stage-04-pilot",
                "research/academic-pipeline/rq2-live-pilot",
                "research/academic-pipeline/contribution-evidence-matrix.csv",
                "research/academic-pipeline/experiment-evidence-matrix.csv",
                "research/claim-ledger.yaml",
                "game-track/godot/docs/latest/balance-archetypes.json",
                *visual_validator.NPC_REGENERATION_SUPPORT,
                *visual_validator.RUNTIME_COMPARISON_REGENERATION_SUPPORT,
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

    def _write_fractional_figure_svg(self, font_size: int) -> None:
        path = self.root / "paper/latex/figures/current.svg"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 500">'
            f"<style>text {{ font-size: {font_size}px; }}</style>"
            '<text x="20" y="40">Runtime comparison</text></svg>',
            encoding="utf-8",
        )

    def test_fractional_textwidth_is_allowed_only_with_an_eight_point_svg_proof(self) -> None:
        self._write_fractional_figure_svg(font_size=28)
        self.write_figure_wrapper(
            r"""\begin{figure*}[t]
\includegraphics[width=0.72\textwidth]{target}
\end{figure*}
"""
        )
        self.assertEqual(self.validate_links(self.figure_manifest()), [])

        cases = {
            "height transform": (
                28,
                r"""\begin{figure*}[t]
\includegraphics[width=0.72\textwidth,height=1pt]{target}
\end{figure*}
""",
            ),
            "too-small print": (
                12,
                r"""\begin{figure*}[t]
\includegraphics[width=0.72\textwidth]{target}
\end{figure*}
""",
            ),
            "fractional columnwidth": (
                28,
                r"""\begin{figure*}[t]
\includegraphics[width=0.72\columnwidth]{target}
\end{figure*}
""",
            ),
            "scale transform": (
                28,
                r"""\begin{figure*}[t]
\includegraphics[width=0.72\textwidth,scale=1]{target}
\end{figure*}
""",
            ),
            "non-full-width figure": (
                28,
                r"""\begin{figure}[t]
\includegraphics[width=0.72\textwidth]{target}
\end{figure}
""",
            ),
        }
        for name, (font_size, wrapper) in cases.items():
            with self.subTest(width_contract=name):
                self._write_fractional_figure_svg(font_size)
                self.write_figure_wrapper(wrapper)
                errors = self.validate_links(self.figure_manifest())
                self.assertTrue(
                    any("must use the legible single-column contract" in error for error in errors),
                    errors,
                )

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

    def test_declared_runtime_figure_anchor_fails_when_label_missing_or_renamed(self) -> None:
        manifest = self.figure_manifest()
        asset = manifest["visual_assets"][0]
        asset["id"] = "paper-runtime-comparison"
        asset["anchors"] = ["fig:runtime-comparison"]

        cases = {
            "correct label": r"\label{fig:runtime-comparison}",
            "missing label": "",
            "renamed label": r"\label{fig:runtime-comparison-renamed}",
        }
        for name, label in cases.items():
            with self.subTest(label=name):
                self.write_figure_wrapper(
                    r"""\begin{figure*}[t]
\includegraphics[width=\textwidth]{target}
"""
                    + (label + "\n" if label else "")
                    + r"""\end{figure*}
"""
                )
                errors = self.validate_links(manifest)
                if name == "correct label":
                    self.assertEqual(errors, [])
                else:
                    self.assertEqual(
                        sorted(errors),
                        sorted(
                            [
                                "paper/latex/en/main.tex: paper-runtime-comparison is missing figure anchor fig:runtime-comparison",
                                "paper/latex/ko/main.tex: paper-runtime-comparison is missing figure anchor fig:runtime-comparison",
                            ]
                        ),
                    )

    def _write_runtime_table_fixture(self) -> None:
        generated = self.root / "paper/latex/generated"
        generated.mkdir(parents=True, exist_ok=True)
        for language, marker in (("en", "Runtime results"), ("ko", "런타임 결과")):
            (generated / f"runtime_comparison_results_{language}.tex").write_text(
                marker + "\n", encoding="utf-8"
            )
            (generated / f"runtime_comparison_tables_{language}.tex").write_text(
                "\\begin{table*}[t]\n"
                "\\centering\n"
                "\\renewcommand{\\arraystretch}{1.20}\n"
                "\\begin{tabularx}{\\textwidth}{ll}\n"
                "\\toprule\n"
                "Runtime & Result \\\\\n"
                "\\bottomrule\n"
                "\\end{tabularx}\n"
                "\\label{tab:runtime-comparison-aggregate}\n"
                "\\end{table*}\n",
                encoding="utf-8",
            )
        for language, marker in (
            ("en", "Interpretation Rows have different denominators"),
            ("ko", "해석 범위 분모와 성공 방향"),
        ):
            (generated / f"pilot_tables_{language}.tex").write_text(marker, encoding="utf-8")
        self.papers[0].write_text(
            "\\input{../generated/runtime_comparison_results_en}\n"
            "\\input{../generated/runtime_comparison_tables_en}\n",
            encoding="utf-8",
        )
        self.papers[1].write_text(
            "\\input{../generated/runtime_comparison_results_ko}\n"
            "\\input{../generated/runtime_comparison_tables_ko}\n",
            encoding="utf-8",
        )

    def runtime_table_manifest(self) -> dict:
        result_data = [
            {
                "path": "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                "bytes": 0,
                "sha256": "0" * 64,
            }
        ]
        return {
            "rendered_surfaces": [
                {"id": "paper-en", "editable_source": {"path": "paper/latex/en/main.tex"}},
                {"id": "paper-ko", "editable_source": {"path": "paper/latex/ko/main.tex"}},
            ],
            "table_sources": [
                {
                    "id": "runtime-comparison-results-en",
                    "layout_sources": [
                        {"path": "paper/latex/generated/runtime_comparison_results_en.tex"}
                    ],
                    "data_sources": result_data,
                    "rendered_in": ["paper-en"],
                    "anchors": [],
                },
                {
                    "id": "runtime-comparison-results-ko",
                    "layout_sources": [
                        {"path": "paper/latex/generated/runtime_comparison_results_ko.tex"}
                    ],
                    "data_sources": result_data,
                    "rendered_in": ["paper-ko"],
                    "anchors": [],
                },
                {
                    "id": "runtime-comparison-tables-en",
                    "layout_sources": [
                        {"path": "paper/latex/generated/runtime_comparison_tables_en.tex"}
                    ],
                    "data_sources": result_data,
                    "rendered_in": ["paper-en"],
                    "anchors": ["tab:runtime-comparison-aggregate"],
                },
                {
                    "id": "runtime-comparison-tables-ko",
                    "layout_sources": [
                        {"path": "paper/latex/generated/runtime_comparison_tables_ko.tex"}
                    ],
                    "data_sources": result_data,
                    "rendered_in": ["paper-ko"],
                    "anchors": ["tab:runtime-comparison-aggregate"],
                },
            ],
        }

    def validate_runtime_tables(self, manifest: dict) -> list[str]:
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        with patch.object(visual_validator, "ROOT", self.root):
            validator._validate_tables(manifest)
        return validator.errors

    def test_runtime_result_and_table_sources_require_their_localized_closures(self) -> None:
        self._write_runtime_table_fixture()
        manifest = self.runtime_table_manifest()
        self.assertEqual(self.validate_runtime_tables(manifest), [])

        cases = {
            "missing KO companion": lambda: (
                self.papers[1].write_text(
                    "\\input{../generated/runtime_comparison_tables_ko}\n", encoding="utf-8"
                ),
                (self.root / "paper/latex/generated/runtime_comparison_results_ko.tex").unlink(),
            ),
            "EN uses KO result fragment": lambda: self.papers[0].write_text(
                "\\input{../generated/runtime_comparison_results_ko}\n"
                "\\input{../generated/runtime_comparison_tables_en}\n",
                encoding="utf-8",
            ),
        }
        for name, mutate in cases.items():
            with self.subTest(closure=name):
                self._write_runtime_table_fixture()
                mutate()
                errors = self.validate_runtime_tables(manifest)
                self.assertTrue(
                    any(
                        "does not include a declared layout source" in error
                        or "paper source traversal failed" in error
                        for error in errors
                    ),
                    errors,
                )

    def _write_traceability_surface_fixture(self) -> None:
        generated = self.root / "paper/latex/generated"
        generated.mkdir(parents=True, exist_ok=True)
        for language, marker in (
            ("en", "Interpretation Rows have different denominators"),
            ("ko", "해석 범위 분모와 성공 방향"),
        ):
            (generated / f"pilot_tables_{language}.tex").write_text(marker, encoding="utf-8")
            paper_dir = self.root / f"paper/latex/{language}"
            paper_dir.mkdir(parents=True, exist_ok=True)
            (paper_dir / "main.tex").write_text(
                "\\begin{table}[t]\n"
                "\\centering\n"
                "\\renewcommand{\\arraystretch}{1.20}\n"
                "\\begin{tabular}{ll}\n"
                "\\toprule\n"
                "Measured & Value \\\\\n"
                "\\bottomrule\n"
                "\\end{tabular}\n"
                "\\label{tab:measured}\n"
                "\\end{table}\n",
                encoding="utf-8",
            )
            (paper_dir / "traceability-supplement.tex").write_text(
                "\\begin{table}[t]\n"
                "\\centering\n"
                "\\renewcommand{\\arraystretch}{1.20}\n"
                "\\begin{tabular}{ll}\n"
                "\\toprule\n"
                "Rubric & Value \\\\\n"
                "\\bottomrule\n"
                "\\end{tabular}\n"
                "\\label{tab:traceability-rubric}\n"
                "\\end{table}\n",
                encoding="utf-8",
            )

    def traceability_surface_manifest(self) -> dict:
        return {
            "rendered_surfaces": [
                {
                    "id": "paper-en",
                    "artifact": {"path": "paper/latex/en/main.pdf"},
                    "editable_source": {"path": "paper/latex/en/main.tex"},
                },
                {
                    "id": "paper-ko",
                    "artifact": {"path": "paper/latex/ko/main.pdf"},
                    "editable_source": {"path": "paper/latex/ko/main.tex"},
                },
                {
                    "id": "paper-en-traceability-supplement",
                    "artifact": {"path": "paper/latex/en/traceability-supplement.pdf"},
                    "editable_source": {"path": "paper/latex/en/traceability-supplement.tex"},
                },
                {
                    "id": "paper-ko-traceability-supplement",
                    "artifact": {"path": "paper/latex/ko/traceability-supplement.pdf"},
                    "editable_source": {"path": "paper/latex/ko/traceability-supplement.tex"},
                },
            ],
            "table_sources": [
                {
                    "id": "current-paper-hand-authored-tables",
                    "layout_sources": [
                        {"path": "paper/latex/en/main.tex"},
                        {"path": "paper/latex/ko/main.tex"},
                    ],
                    "rendered_in": ["paper-en", "paper-ko"],
                    "anchors": ["tab:measured"],
                },
                {
                    "id": "traceability-supplement-table",
                    "layout_sources": [
                        {"path": "paper/latex/en/traceability-supplement.tex"},
                        {"path": "paper/latex/ko/traceability-supplement.tex"},
                    ],
                    "rendered_in": [
                        "paper-en-traceability-supplement",
                        "paper-ko-traceability-supplement",
                    ],
                    "anchors": ["tab:traceability-rubric"],
                },
            ],
        }

    def test_traceability_rubric_anchor_is_owned_only_by_supplement_surfaces(self) -> None:
        self._write_traceability_surface_fixture()
        manifest = self.traceability_surface_manifest()
        self.assertEqual(self.validate_runtime_tables(manifest), [])

        cases = {
            "rubric declared on main": lambda mutated: next(
                source
                for source in mutated["table_sources"]
                if source["id"] == "current-paper-hand-authored-tables"
            )["anchors"].append("tab:traceability-rubric"),
            "KO supplement consumer omitted": lambda mutated: next(
                source
                for source in mutated["table_sources"]
                if source["id"] == "traceability-supplement-table"
            )["rendered_in"].remove("paper-ko-traceability-supplement"),
            "KO supplement source missing": lambda mutated: (
                self.root / "paper/latex/ko/traceability-supplement.tex"
            ).unlink(),
            "EN supplement label only": lambda mutated: (
                self.root / "paper/latex/en/traceability-supplement.tex"
            ).write_text("\\label{tab:traceability-rubric}\n", encoding="utf-8"),
        }
        for name, mutate in cases.items():
            with self.subTest(ownership=name):
                self._write_traceability_surface_fixture()
                mutated = copy.deepcopy(manifest)
                mutate(mutated)
                errors = self.validate_runtime_tables(mutated)
                if name == "rubric declared on main":
                    self.assertTrue(
                        any(
                            "paper-en is missing table anchor tab:traceability-rubric" in error
                            for error in errors
                        ),
                        errors,
                    )
                elif name == "KO supplement consumer omitted":
                    self.assertTrue(
                        any(
                            "anchor tab:traceability-rubric is rendered in undeclared surface paper-ko-traceability-supplement"
                            in error
                            for error in errors
                        ),
                        errors,
                    )
                elif name == "EN supplement label only":
                    semantic_errors = [
                        error
                        for error in errors
                        if "table anchor tab:traceability-rubric is not inside a rendered table block"
                        in error
                    ]
                    self.assertEqual(
                        semantic_errors,
                        [
                            "traceability-supplement-table: paper-en-traceability-supplement table anchor tab:traceability-rubric is not inside a rendered table block"
                        ],
                    )
                else:
                    self.assertTrue(
                        any("paper source traversal failed" in error for error in errors),
                        errors,
                    )

    def test_manifest_builder_owns_traceability_supplement_surfaces_and_table(self) -> None:
        import update_visual_source_manifest as manifest_builder

        manifest = manifest_builder.build_manifest()
        expected_ids = {
            "paper-en-traceability-supplement",
            "paper-ko-traceability-supplement",
        }
        supplements = {
            surface["id"]: surface
            for surface in manifest["rendered_surfaces"]
            if "traceability-supplement" in surface.get("id", "")
        }
        self.assertEqual(set(supplements), expected_ids)
        self.assertEqual(
            {
                (
                    surface_id,
                    surface["artifact"]["path"],
                    surface["editable_source"]["path"],
                )
                for surface_id, surface in supplements.items()
            },
            {
                (
                    "paper-en-traceability-supplement",
                    "paper/latex/en/traceability-supplement.pdf",
                    "paper/latex/en/traceability-supplement.tex",
                ),
                (
                    "paper-ko-traceability-supplement",
                    "paper/latex/ko/traceability-supplement.pdf",
                    "paper/latex/ko/traceability-supplement.tex",
                ),
            },
        )

        source = next(
            source
            for source in manifest["table_sources"]
            if source["id"] == "traceability-supplement-table"
        )
        self.assertEqual(
            [record["path"] for record in source["layout_sources"]],
            [
                "paper/latex/en/traceability-supplement.tex",
                "paper/latex/ko/traceability-supplement.tex",
            ],
        )
        self.assertEqual(source["rendered_in"], sorted(expected_ids))
        self.assertEqual(source["anchors"], ["tab:traceability-rubric"])

    def test_missing_runtime_input_or_output_receipt_fails_closed(self) -> None:
        validator = visual_validator.Validator(require_pdf_tools=False, check_regeneration=False)
        manifest = {
            "table_sources": [
                {
                    "id": "runtime-comparison-results-en",
                    "data_sources": [
                        {
                            "path": "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                            "bytes": 0,
                            "sha256": "0" * 64,
                        }
                    ],
                    "layout_sources": [
                        {
                            "path": "paper/latex/generated/runtime_comparison_results_en.tex",
                            "bytes": 0,
                            "sha256": "0" * 64,
                        }
                    ],
                }
            ]
        }
        with patch.object(visual_validator, "ROOT", self.root):
            validator._validate_receipts(manifest)
        self.assertEqual(
            sorted(validator.errors),
            sorted(
                [
                    "manifest receipt is missing: research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                    "manifest receipt is missing: paper/latex/generated/runtime_comparison_results_en.tex",
                ]
            ),
        )

    def test_current_figure_requires_inclusion_by_each_owner(self) -> None:
        manifest = {
            "visual_assets": [
                {
                    "id": "current-signals",
                    "publication_role": "current-figure",
                    "used_by": [str(path.relative_to(self.root)) for path in self.papers],
                    "editable_sources": [{"path": "paper/latex/figures/current.svg"}],
                    "rendered": [{"path": "paper/latex/figures/current.pdf"}],
                },
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
