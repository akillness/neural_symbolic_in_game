#!/usr/bin/env python3
"""Validate editable figure/table sources, rendered linkage, and layout contracts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "visuals" / "source-manifest.json"
SVG_NS = "http://www.w3.org/2000/svg"
PAPER_MAIN = (ROOT / "paper/latex/en/main.tex", ROOT / "paper/latex/ko/main.tex")
PAPER_FIGURE_DIR = ROOT / "paper/latex/figures"

SVG_INVENTORY_ROOTS = (
    ROOT / "paper/latex/figures",
    ROOT / "visuals",
    ROOT / "research/directions/figures",
    ROOT / "research/simulation/kg-ontology/latest/figures",
    ROOT / "game-track/godot/docs/latest",
)

LIGHTWEIGHT_OUTPUTS = (
    "paper/latex/figures/fig_architecture.svg",
    "research/directions/figures/fig_consensus_gate_lanes.svg",
    "research/directions/figures/fig_cost_validity_pareto_concept.svg",
    "paper/latex/generated/pilot_results_en.tex",
    "paper/latex/generated/pilot_results_ko.tex",
    "paper/latex/generated/pilot_tables_en.tex",
    "paper/latex/generated/pilot_tables_ko.tex",
    "paper/latex/generated/live_pilot_results_en.tex",
    "paper/latex/generated/live_pilot_results_ko.tex",
    "paper/latex/generated/live_pilot_tables_en.tex",
    "paper/latex/generated/live_pilot_tables_ko.tex",
    "paper/latex/generated/contribution_map_en.tex",
    "paper/latex/generated/contribution_map_ko.tex",
    "paper/latex/generated/evidence_lanes_en.tex",
    "paper/latex/generated/evidence_lanes_ko.tex",
    "game-track/godot/docs/latest/balance-archetypes.svg",
)


class Validator:
    def __init__(self, *, require_pdf_tools: bool, check_regeneration: bool) -> None:
        self.require_pdf_tools = require_pdf_tools
        self.check_regeneration = check_regeneration
        self.errors: list[str] = []
        self.notes: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        if not condition:
            self.errors.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def run(self) -> None:
        manifest = self._load_manifest()
        if manifest is None:
            self._finish()
            return
        self._validate_manifest_freshness(manifest)
        self._validate_receipts(manifest)
        self._validate_asset_inventory(manifest)
        self._validate_visual_assets(manifest)
        self._validate_tables(manifest)
        self._validate_paper_links(manifest)
        self._validate_engine_evidence(manifest)
        if self.check_regeneration:
            self._validate_lightweight_regeneration()
        self._finish()

    def _finish(self) -> None:
        for note in self.notes:
            print(f"NOTE: {note}")
        if self.errors:
            for error in self.errors:
                print(f"ERROR: {error}", file=sys.stderr)
            raise SystemExit(f"visual-asset validation failed with {len(self.errors)} error(s)")
        print("visual-asset validation: PASS")

    def _load_manifest(self) -> dict[str, Any] | None:
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            self.errors.append(f"cannot read {MANIFEST_PATH.relative_to(ROOT)}: {exc}")
            return None
        self.check(data.get("schema_version") == 1, "source manifest schema_version must be 1")
        return data

    def _load_manifest_builder(self):
        module_path = ROOT / "scripts/update_visual_source_manifest.py"
        spec = importlib.util.spec_from_file_location("visual_source_manifest_builder", module_path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot import {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.build_manifest

    def _validate_manifest_freshness(self, manifest: dict[str, Any]) -> None:
        try:
            expected = self._load_manifest_builder()()
        except (OSError, ImportError, AttributeError, TypeError, ValueError) as exc:
            self.errors.append(f"cannot rebuild source manifest in memory: {exc}")
            return
        self.check(
            manifest == expected,
            "visuals/source-manifest.json is stale; run scripts/update_visual_source_manifest.py",
        )

    def _iter_receipts(self, node: Any) -> Iterator[dict[str, Any]]:
        if isinstance(node, dict):
            if {"path", "bytes", "sha256"}.issubset(node):
                yield node
                return
            for value in node.values():
                yield from self._iter_receipts(value)
        elif isinstance(node, list):
            for value in node:
                yield from self._iter_receipts(value)

    def _validate_receipts(self, manifest: dict[str, Any]) -> None:
        seen: set[tuple[str, str]] = set()
        for item in self._iter_receipts(manifest):
            relative = item["path"]
            key = (relative, item["sha256"])
            if key in seen:
                continue
            seen.add(key)
            path = ROOT / relative
            if not path.is_file():
                self.errors.append(f"manifest receipt is missing: {relative}")
                continue
            payload = path.read_bytes()
            self.check(len(payload) == item["bytes"], f"byte count drift: {relative}")
            digest = hashlib.sha256(payload).hexdigest()
            self.check(digest == item["sha256"], f"SHA-256 drift: {relative}")
        self.note(f"checked {len(seen)} unique source/artifact receipts")

    def _validate_asset_inventory(self, manifest: dict[str, Any]) -> None:
        assets = manifest.get("visual_assets", [])
        ids = [asset.get("id") for asset in assets]
        self.check(len(ids) == len(set(ids)), "visual asset ids must be unique")
        manifest_svgs = {
            record["path"]
            for asset in assets
            for key in ("rendered", "editable_sources")
            for record in asset.get(key, [])
            if record["path"].endswith(".svg")
        }
        disk_svgs: set[str] = set()
        for inventory_root in SVG_INVENTORY_ROOTS:
            if inventory_root.is_dir():
                disk_svgs.update(
                    str(path.relative_to(ROOT)) for path in inventory_root.rglob("*.svg")
                )
        missing = disk_svgs - manifest_svgs
        extra = manifest_svgs - disk_svgs
        self.check(not missing, f"SVG assets missing from manifest: {sorted(missing)}")
        self.check(not extra, f"manifest SVG paths missing on disk: {sorted(extra)}")
        self.note(f"manifest covers {len(disk_svgs)} SVG assets")

        table_ids = [source.get("id") for source in manifest.get("table_sources", [])]
        self.check(len(table_ids) == len(set(table_ids)), "table source ids must be unique")

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def _validate_visual_assets(self, manifest: dict[str, Any]) -> None:
        pdfinfo = shutil.which("pdfinfo")
        pdfimages = shutil.which("pdfimages")
        pdffonts = shutil.which("pdffonts")
        if self.require_pdf_tools:
            self.check(pdfinfo is not None, "pdfinfo is required for source-linked PDF checks")
            self.check(pdfimages is not None, "pdfimages is required for vector PDF checks")
            self.check(pdffonts is not None, "pdffonts is required for Type 3 checks")

        for asset in manifest.get("visual_assets", []):
            asset_id = asset.get("id", "<missing-id>")
            self.check(bool(asset.get("editable_sources")), f"{asset_id}: no editable source")
            self.check(bool(asset.get("generator")), f"{asset_id}: no generator receipt")
            self.check(bool(asset.get("rendered")), f"{asset_id}: no rendered artifact")
            rendered_paths = [record["path"] for record in asset.get("rendered", [])]
            editable_paths = [record["path"] for record in asset.get("editable_sources", [])]
            for relative in editable_paths:
                if relative.endswith(".svg"):
                    self._validate_svg(ROOT / relative, paper=relative.startswith("paper/latex/"))
            for relative in rendered_paths:
                path = ROOT / relative
                if relative.endswith(".pdf"):
                    self.check(path.read_bytes().startswith(b"%PDF"), f"{relative}: invalid PDF")
                    sibling = str(Path(relative).with_suffix(".svg"))
                    self.check(sibling in editable_paths, f"{relative}: no adjacent SVG source")
                    if pdfinfo and pdfimages and pdffonts:
                        self._validate_vector_pdf(ROOT / sibling, path)
                elif relative.endswith(".png"):
                    self.check(
                        path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"),
                        f"{relative}: invalid PNG",
                    )
                    sibling = str(Path(relative).with_suffix(".svg"))
                    self.check(sibling in editable_paths, f"{relative}: no adjacent SVG source")
            for used_by in asset.get("used_by", []):
                owner = ROOT / used_by
                self.check(owner.is_file(), f"{asset_id}: missing owner {used_by}")
                if owner.is_file():
                    text = owner.read_text(encoding="utf-8")
                    referenced = any(Path(item).name in text for item in rendered_paths)
                    self.check(referenced, f"{asset_id}: {used_by} does not reference its artifact")

    def _validate_svg(self, path: Path, *, paper: bool) -> None:
        relative = path.relative_to(ROOT)
        try:
            root = ET.parse(path).getroot()
        except ET.ParseError as exc:
            self.errors.append(f"{relative}: invalid XML: {exc}")
            return
        self.check(self._local_name(root.tag) == "svg", f"{relative}: root is not SVG")
        self.check(root.attrib.get("role") == "img", f"{relative}: missing role=img")
        child_names = {self._local_name(child.tag) for child in root}
        self.check("title" in child_names, f"{relative}: missing <title>")
        self.check("desc" in child_names, f"{relative}: missing <desc>")
        self.check("viewBox" in root.attrib, f"{relative}: missing viewBox")

        style = "\n".join(
            "".join(element.itertext())
            for element in root.iter()
            if self._local_name(element.tag) == "style"
        )
        sizes = [float(value) for value in re.findall(r"font-size:\s*([0-9.]+)px", style)]
        sizes.extend(
            float(value)
            for element in root.iter()
            if (value := element.attrib.get("font-size", ""))
            .removesuffix("px")
            .replace(".", "", 1)
            .isdigit()
        )
        if paper:
            self.check(bool(sizes), f"{relative}: no SVG font sizes found")
            if sizes:
                self.check(min(sizes) >= 28.0, f"{relative}: paper label below 28 SVG px")
            groups = [
                element
                for element in root.iter()
                if self._local_name(element.tag) == "g"
                and "connector-label" in element.attrib.get("class", "").split()
            ]
            for group in groups:
                has_shield = any(
                    self._local_name(child.tag) == "rect"
                    and "label-shield" in child.attrib.get("class", "").split()
                    for child in group
                )
                self.check(has_shield, f"{relative}: connector label lacks an opaque shield")
            arrow_labels = [
                element
                for element in root.iter()
                if self._local_name(element.tag) == "text"
                and "arrow-label" in element.attrib.get("class", "").split()
            ]
            self.check(
                len(groups) >= len(arrow_labels),
                f"{relative}: an arrow label is not grouped with a shield",
            )
            connectors = [
                element
                for element in root.iter()
                if "connector" in element.attrib.get("class", "").split()
            ]
            self.check(bool(connectors), f"{relative}: connector paths are not classed")

        if path.name == "balance-archetypes.svg":
            grid_lines = [
                element
                for element in root.iter()
                if "grid-line" in element.attrib.get("class", "").split()
            ]
            values = [
                element
                for element in root.iter()
                if "bar-value" in element.attrib.get("class", "").split()
            ]
            self.check(bool(grid_lines), f"{relative}: grid lines lack semantic classes")
            self.check(bool(values), f"{relative}: value labels lack semantic classes")
            self.check(
                all(
                    "paint-order" in element.attrib
                    or "paint-order" in element.attrib.get("style", "")
                    for element in values
                ),
                f"{relative}: value labels need stroke halos over grid lines",
            )

        if paper or path.name == "balance-archetypes.svg":
            self._validate_svg_geometry(root, relative)

    @staticmethod
    def _estimated_text_width(value: str, font_size: float) -> float:
        """Conservative Helvetica-like width estimate for source-level collision gates."""

        factors = []
        for char in value:
            if char.isspace() or char in "ilI.,'`|!:;":
                factors.append(0.28)
            elif char in "MW@%":
                factors.append(0.88)
            elif char.isupper():
                factors.append(0.64)
            elif char.isdigit():
                factors.append(0.56)
            else:
                factors.append(0.52)
        return sum(factors) * font_size

    @staticmethod
    def _path_segments(
        path_data: str,
    ) -> list[tuple[float, float, float, float]] | None:
        """Return line segments, or None when the gated path syntax is unsupported."""

        if re.search(r"[CQASTZcqastz]", path_data):
            return None
        tokens = re.findall(r"[MLHVmlhv]|-?(?:\d+(?:\.\d*)?|\.\d+)", path_data)
        segments: list[tuple[float, float, float, float]] = []
        command = ""
        x = y = 0.0
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token.isalpha():
                command = token
                index += 1
                continue
            if command in {"M", "L"} and index + 1 < len(tokens):
                next_x, next_y = float(tokens[index]), float(tokens[index + 1])
                if command == "L":
                    segments.append((x, y, next_x, next_y))
                x, y = next_x, next_y
                command = "L" if command == "M" else command
                index += 2
            elif command == "H":
                next_x = float(token)
                segments.append((x, y, next_x, y))
                x = next_x
                index += 1
            elif command == "V":
                next_y = float(token)
                segments.append((x, y, x, next_y))
                y = next_y
                index += 1
            else:
                return []
        return segments

    @staticmethod
    def _segment_hits_rect(
        segment: tuple[float, float, float, float],
        rectangle: tuple[float, float, float, float],
    ) -> bool:
        x1, y1, x2, y2 = segment
        left, top, right, bottom = rectangle
        length = max(abs(x2 - x1), abs(y2 - y1))
        steps = max(1, int(length) + 1)
        for step in range(steps + 1):
            ratio = step / steps
            x = x1 + ((x2 - x1) * ratio)
            y = y1 + ((y2 - y1) * ratio)
            if left < x < right and top < y < bottom:
                return True
        return False

    def _validate_svg_geometry(self, root: ET.Element, relative: Path) -> None:
        """Catch unshielded text/rule intersections in source SVG coordinates."""

        parent = {child: owner for owner in root.iter() for child in owner}
        style_text = "\n".join(
            "".join(element.itertext())
            for element in root.iter()
            if self._local_name(element.tag) == "style"
        )
        class_sizes: dict[str, float] = {}
        for match in re.finditer(r"\.([\w-]+)\s*\{([^}]*)\}", style_text):
            size = re.search(r"font-size:\s*([0-9.]+)px", match.group(2))
            if size:
                class_sizes[match.group(1)] = float(size.group(1))

        def has_protected_ancestor(element: ET.Element) -> bool:
            current: ET.Element | None = element
            while current is not None:
                classes = current.attrib.get("class", "").split()
                if "connector-label" in classes:
                    return True
                current = parent.get(current)
            return False

        def font_size(element: ET.Element, owner: ET.Element) -> float:
            raw = element.attrib.get("font-size") or owner.attrib.get("font-size")
            if raw:
                return float(raw.removesuffix("px"))
            for class_name in owner.attrib.get("class", "").split():
                if class_name in class_sizes:
                    return class_sizes[class_name]
            return 16.0

        view_x, view_y, view_width, view_height = (
            float(value) for value in root.attrib["viewBox"].split()
        )
        view_box = (view_x, view_y, view_x + view_width, view_y + view_height)
        rectangles = []
        for element in root.iter():
            if self._local_name(element.tag) != "rect":
                continue
            try:
                rectangle = (
                    float(element.attrib.get("x", "0")),
                    float(element.attrib.get("y", "0")),
                    float(element.attrib["width"]),
                    float(element.attrib["height"]),
                )
            except (KeyError, ValueError):
                continue
            if rectangle[2] >= view_width - 1 and rectangle[3] >= view_height - 1:
                continue
            rectangles.append(rectangle)

        text_boxes: list[tuple[str, tuple[float, float, float, float], bool]] = []
        for text in root.iter(f"{{{SVG_NS}}}text"):
            if "transform" in text.attrib:
                continue
            connector_protected = has_protected_ancestor(text) or (
                "paint-order" in text.attrib or "paint-order" in text.attrib.get("style", "")
            )
            spans = [child for child in text if self._local_name(child.tag) == "tspan"] or [text]
            anchor = text.attrib.get("text-anchor", "start")
            try:
                current_x = float(text.attrib.get("x", "0"))
                current_y = float(text.attrib.get("y", "0"))
            except ValueError:
                continue
            for span in spans:
                value = " ".join((span.text or "").split())
                if not value:
                    continue
                try:
                    if "x" in span.attrib:
                        current_x = float(span.attrib["x"])
                    if "y" in span.attrib:
                        current_y = float(span.attrib["y"])
                    elif "dy" in span.attrib:
                        current_y += float(span.attrib["dy"])
                except ValueError:
                    continue
                x, y = current_x, current_y
                size = font_size(span, text)
                width = self._estimated_text_width(value, size)
                if anchor == "middle":
                    left, right = x - (width / 2), x + (width / 2)
                elif anchor == "end":
                    left, right = x - width, x
                else:
                    left, right = x, x + width
                box = (left, y - (0.82 * size), right, y + (0.22 * size))
                text_boxes.append((value, box, connector_protected))
                if (
                    box[0] < view_box[0] - 1
                    or box[1] < view_box[1] - 1
                    or box[2] > view_box[2] + 1
                    or box[3] > view_box[3] + 1
                ):
                    self.errors.append(f"{relative}: text leaves SVG viewBox: {value!r}")
                candidates = [
                    rectangle
                    for rectangle in rectangles
                    if rectangle[0] <= (box[0] + box[2]) / 2 <= rectangle[0] + rectangle[2]
                    and rectangle[1] <= (box[1] + box[3]) / 2 <= rectangle[1] + rectangle[3]
                ]
                if candidates:
                    container = min(candidates, key=lambda item: item[2] * item[3])
                    c_left, c_top, c_width, c_height = container
                    if (
                        box[0] < c_left - 1
                        or box[1] < c_top - 1
                        or box[2] > c_left + c_width + 1
                        or box[3] > c_top + c_height + 1
                    ):
                        self.errors.append(
                            f"{relative}: text exceeds its nearest container: {value!r}"
                        )

        connectors: list[tuple[str, list[tuple[float, float, float, float]]]] = []
        for element in root.iter():
            classes = element.attrib.get("class", "").split()
            if not ({"connector", "grid-line"} & set(classes)):
                continue
            local_name = self._local_name(element.tag)
            if local_name == "line":
                segments = [
                    (
                        float(element.attrib["x1"]),
                        float(element.attrib["y1"]),
                        float(element.attrib["x2"]),
                        float(element.attrib["y2"]),
                    )
                ]
            elif local_name == "path":
                segments = self._path_segments(element.attrib.get("d", ""))
                if segments is None:
                    self.errors.append(
                        f"{relative}: unsupported connector path syntax cannot be geometry-checked: "
                        f"{element.attrib.get('d', '')}"
                    )
                    continue
            else:
                segments = []
            if segments:
                connectors.append((element.attrib.get("d", "line"), segments))

        for value, box, connector_protected in text_boxes:
            if connector_protected:
                continue
            for connector_name, segments in connectors:
                if any(self._segment_hits_rect(segment, box) for segment in segments):
                    self.errors.append(
                        f"{relative}: unshielded connector overlaps text {value!r} ({connector_name})"
                    )

        for index, (left_value, left_box, _) in enumerate(text_boxes):
            for right_value, right_box, _ in text_boxes[index + 1 :]:
                overlap_width = min(left_box[2], right_box[2]) - max(left_box[0], right_box[0])
                overlap_height = min(left_box[3], right_box[3]) - max(left_box[1], right_box[1])
                if overlap_width > 1 and overlap_height > 1:
                    self.errors.append(
                        f"{relative}: text boxes overlap: {left_value!r} / {right_value!r}"
                    )

    def _validate_vector_pdf(self, svg: Path, pdf: Path) -> None:
        relative = pdf.relative_to(ROOT)
        image_listing = subprocess.run(
            ["pdfimages", "-list", str(pdf)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        image_rows = [
            line for line in image_listing.splitlines() if re.match(r"^\s*\d+\s+\d+\s+", line)
        ]
        self.check(not image_rows, f"{relative}: contains raster image objects instead of vectors")

        font_listing = subprocess.run(
            ["pdffonts", str(pdf)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        self.check("Type 3" not in font_listing, f"{relative}: contains a Type 3 fallback font")

        info = subprocess.run(
            ["pdfinfo", str(pdf)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        expected_hash = hashlib.sha256(svg.read_bytes()).hexdigest()
        title_match = re.search(r"^Title:\s+source-sha256:([0-9a-f]{64})$", info, re.MULTILINE)
        self.check(bool(title_match), f"{relative}: missing embedded SVG source hash")
        if title_match:
            self.check(
                title_match.group(1) == expected_hash,
                f"{relative}: embedded SVG source hash is stale",
            )

        root = ET.parse(svg).getroot()
        viewbox = [float(value) for value in root.attrib["viewBox"].split()]
        size_match = re.search(r"^Page size:\s+([0-9.]+) x ([0-9.]+) pts", info, re.MULTILINE)
        self.check(bool(size_match), f"{relative}: cannot read PDF page dimensions")
        if size_match:
            pdf_width, pdf_height = (float(size_match.group(1)), float(size_match.group(2)))
            svg_ratio = viewbox[2] / viewbox[3]
            self.check(
                abs((pdf_width / pdf_height) - svg_ratio) < 0.002,
                f"{relative}: PDF/SVG aspect ratios differ",
            )

    def _validate_tables(self, manifest: dict[str, Any]) -> None:
        table_sources = manifest.get("table_sources", [])
        surfaces = manifest.get("rendered_surfaces", [])
        surface_ids = [surface.get("id") for surface in surfaces]
        self.check(len(surface_ids) == len(set(surface_ids)), "rendered surface ids must be unique")

        input_pattern = re.compile(r"\\input\{([^}]+)\}")

        def source_closure(entry: Path) -> tuple[set[str], str]:
            pending = [entry]
            paths: set[str] = set()
            texts: list[str] = []
            while pending:
                current = pending.pop()
                try:
                    relative = str(current.resolve().relative_to(ROOT))
                except ValueError:
                    self.errors.append(f"paper source escapes project: {current}")
                    continue
                if relative in paths:
                    continue
                if not current.is_file():
                    self.errors.append(f"paper source is missing: {relative}")
                    continue
                paths.add(relative)
                text = current.read_text(encoding="utf-8")
                texts.append(text)
                for target in input_pattern.findall(text):
                    child = current.parent / target
                    if child.suffix == "":
                        child = child.with_suffix(".tex")
                    pending.append(child)
            return paths, "\n".join(texts)

        surface_closures: dict[str, tuple[set[str], str]] = {}
        for surface in surfaces:
            surface_id = surface.get("id")
            source = surface.get("editable_source", {}).get("path")
            if not isinstance(surface_id, str) or not isinstance(source, str):
                self.errors.append("rendered surface needs string id and editable_source.path")
                continue
            surface_closures[surface_id] = source_closure(ROOT / source)

        covered_layouts = {
            record["path"]
            for source in table_sources
            for record in source.get("layout_sources", [])
        }
        generated_table_fragments = {
            str(path.relative_to(ROOT))
            for path in (ROOT / "paper/latex/generated").glob("*.tex")
            if "\\begin{tabular" in path.read_text(encoding="utf-8")
        }
        self.check(
            generated_table_fragments <= covered_layouts,
            "generated paper table fragment missing from source manifest: "
            f"{sorted(generated_table_fragments - covered_layouts)}",
        )

        for source in table_sources:
            source_id = source.get("id", "<missing-id>")
            rendered_in = source.get("rendered_in", [])
            self.check(isinstance(rendered_in, list), f"{source_id}: rendered_in must be a list")
            if not isinstance(rendered_in, list):
                rendered_in = []
            unknown_surfaces = sorted(set(rendered_in) - set(surface_closures))
            self.check(
                not unknown_surfaces,
                f"{source_id}: unknown rendered surfaces {unknown_surfaces}",
            )
            anchors = source.get("anchors", [])
            self.check(isinstance(anchors, list), f"{source_id}: anchors must be a list")
            if not isinstance(anchors, list):
                anchors = []
            layout_paths = {record["path"] for record in source.get("layout_sources", [])}
            for surface_id in rendered_in:
                if surface_id not in surface_closures:
                    continue
                closure_paths, closure_text = surface_closures[surface_id]
                self.check(
                    bool(layout_paths & closure_paths),
                    f"{source_id}: {surface_id} does not include a declared layout source",
                )
                for anchor in anchors:
                    self.check(
                        rf"\label{{{anchor}}}" in closure_text,
                        f"{source_id}: {surface_id} is missing table anchor {anchor}",
                    )
            for surface_id, (_, closure_text) in surface_closures.items():
                if surface_id in rendered_in:
                    continue
                for anchor in anchors:
                    self.check(
                        rf"\label{{{anchor}}}" not in closure_text,
                        f"{source_id}: anchor {anchor} is rendered in undeclared surface {surface_id}",
                    )

            rendered = bool(rendered_in)
            for record in source.get("layout_sources", []):
                relative = record["path"]
                path = ROOT / relative
                text = path.read_text(encoding="utf-8")
                if not rendered or "\\begin{tabular" not in text:
                    continue
                self.check("\\toprule" in text, f"{relative}: rendered table lacks \\toprule")
                self.check("\\bottomrule" in text, f"{relative}: rendered table lacks \\bottomrule")
                tabular_starts = [line for line in text.splitlines() if "\\begin{tabular" in line]
                self.check(
                    all("|" not in line for line in tabular_starts),
                    f"{relative}: vertical table rules are forbidden",
                )
                spacings = [
                    float(value) for value in re.findall(r"arraystretch\}\{([0-9.]+)\}", text)
                ]
                self.check(bool(spacings), f"{relative}: no explicit arraystretch")
                if spacings:
                    self.check(
                        min(spacings) >= 1.10,
                        f"{relative}: row spacing below the 1.10 floor",
                    )

        offline_en = (ROOT / "paper/latex/generated/pilot_tables_en.tex").read_text(
            encoding="utf-8"
        )
        offline_ko = (ROOT / "paper/latex/generated/pilot_tables_ko.tex").read_text(
            encoding="utf-8"
        )
        live_en = (ROOT / "paper/latex/generated/live_pilot_tables_en.tex").read_text(
            encoding="utf-8"
        )
        live_ko = (ROOT / "paper/latex/generated/live_pilot_tables_ko.tex").read_text(
            encoding="utf-8"
        )
        self.check("Interpretation" in offline_en, "offline EN accounting table needs scope column")
        self.check("해석 범위" in offline_ko, "offline KO accounting table needs scope column")
        self.check(
            "Rows have different denominators" in offline_en, "offline EN scope note missing"
        )
        self.check("분모와 성공 방향" in offline_ko, "offline KO scope note missing")
        self.check(
            "$\\Delta$" in live_en and "matched candidates" in live_en,
            "live EN matched delta missing",
        )
        self.check(
            "$\\Delta$" in live_ko and "동일 후보" in live_ko, "live KO matched delta missing"
        )

    def _validate_paper_links(self, manifest: dict[str, Any]) -> None:
        covered = {
            record["path"]
            for asset in manifest.get("visual_assets", [])
            for record in asset.get("rendered", [])
        }
        covered.update(
            record["path"]
            for exception in manifest.get("noneditable_evidence", [])
            for record in exception.get("rendered", [])
        )
        paper_stems = {path.stem for path in PAPER_FIGURE_DIR.glob("*.svg")}
        include_pattern = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
        for main in PAPER_MAIN:
            text = main.read_text(encoding="utf-8")
            included: set[str] = set()
            for target in include_pattern.findall(text):
                resolved = (main.parent / target).resolve()
                try:
                    included.add(str(resolved.relative_to(ROOT)))
                except ValueError:
                    self.errors.append(
                        f"{main.relative_to(ROOT)}: include escapes project: {target}"
                    )
            missing = included - covered
            self.check(
                not missing, f"{main.relative_to(ROOT)}: unmanifested graphics {sorted(missing)}"
            )
            for stem in paper_stems:
                expected = f"../figures/{stem}.pdf"
                self.check(
                    expected in text, f"{main.relative_to(ROOT)}: must include vector {expected}"
                )
                self.check(
                    f"../figures/{stem}.png" not in text,
                    f"{main.relative_to(ROOT)}: raster paper figure inclusion is forbidden",
                )
                include_line = next((line for line in text.splitlines() if expected in line), "")
                self.check(
                    "width=\\columnwidth" in include_line,
                    f"{main.relative_to(ROOT)}: {stem} must use the legible single-column contract",
                )

    def _validate_engine_evidence(self, manifest: dict[str, Any]) -> None:
        exceptions = manifest.get("noneditable_evidence", [])
        self.check(bool(exceptions), "engine-render evidence exception is missing")
        for item in exceptions:
            self.check(
                item.get("editable") is False, f"{item.get('id')}: exception must be explicit"
            )
            self.check(
                bool(item.get("reproducible_sources")), f"{item.get('id')}: no replay sources"
            )
            self.check(bool(item.get("reason")), f"{item.get('id')}: no non-editable rationale")

    @staticmethod
    def _copy_path(source_root: Path, target_root: Path, relative: str) -> None:
        source = source_root / relative
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=True)
        else:
            shutil.copy2(source, target)

    @staticmethod
    def _digest_paths(root: Path, paths: Iterable[str]) -> dict[str, str]:
        return {
            relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in paths
        }

    def _run_lightweight_generators(self, staged_root: Path) -> None:
        commands = (
            [sys.executable, "scripts/generate_paper_figures.py"],
            [sys.executable, "scripts/generate_direction_figures.py"],
            [sys.executable, "scripts/generate_paper_results.py"],
            [
                sys.executable,
                "-c",
                (
                    "import json; from pathlib import Path; "
                    "from scripts.run_balance_archetypes import render_chart; "
                    "p=Path('game-track/godot/docs/latest/balance-archetypes.json'); "
                    "p.with_suffix('.svg').write_text(render_chart(json.loads(p.read_text("
                    "encoding='utf-8'))), encoding='utf-8', newline='\\n')"
                ),
            ],
        )
        for command in commands:
            subprocess.run(
                command,
                cwd=staged_root,
                check=True,
                capture_output=True,
                text=True,
                env={**dict(__import__("os").environ), "PYTHONDONTWRITEBYTECODE": "1"},
            )

    def _validate_lightweight_regeneration(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-rpg-visual-check-") as tmp:
            staged = Path(tmp) / "project"
            staged.mkdir()
            for relative in (
                "scripts",
                "research/academic-pipeline/stage-04-pilot",
                "research/academic-pipeline/rq2-live-pilot",
                "research/academic-pipeline/contribution-evidence-matrix.csv",
                "research/academic-pipeline/experiment-evidence-matrix.csv",
                "research/claim-ledger.yaml",
                "game-track/godot/docs/latest/balance-archetypes.json",
            ):
                self._copy_path(ROOT, staged, relative)
            self._run_lightweight_generators(staged)
            first = self._digest_paths(staged, LIGHTWEIGHT_OUTPUTS)
            self._run_lightweight_generators(staged)
            second = self._digest_paths(staged, LIGHTWEIGHT_OUTPUTS)
            self.check(
                first == second, "lightweight figure/table generators are not byte deterministic"
            )
            current = self._digest_paths(ROOT, LIGHTWEIGHT_OUTPUTS)
            drift = sorted(path for path in LIGHTWEIGHT_OUTPUTS if first[path] != current[path])
            self.check(not drift, f"generated figure/table sources are stale: {drift}")
            self.note(f"double-regenerated {len(LIGHTWEIGHT_OUTPUTS)} sources in an isolated copy")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-pdf-tools",
        action="store_true",
        help="fail unless pdftotext and pdfimages are available",
    )
    parser.add_argument(
        "--check-regeneration",
        action="store_true",
        help="double-regenerate lightweight sources in a temporary copy",
    )
    args = parser.parse_args()
    Validator(
        require_pdf_tools=args.require_pdf_tools,
        check_regeneration=args.check_regeneration,
    ).run()


if __name__ == "__main__":
    main()
