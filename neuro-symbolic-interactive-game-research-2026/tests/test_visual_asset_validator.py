from __future__ import annotations

import copy
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
