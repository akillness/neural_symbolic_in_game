#!/usr/bin/env python3
"""Verify reached paper table claims from retained evidence, without recollection.

Layer A checks receipts, typed accounting and local source materialization. It
neither executes an engine/browser nor certifies PDF layout or provider output.
Only the CLI's explicitly reported historical-source preparation writes files:
a local Git archive is unpacked into an owned, automatically removed directory.
The verify() API is strictly read-only and requires that historical source tree.
"""

from __future__ import annotations

import sys

_IMPORT_BYTECODE_SETTING = sys.dont_write_bytecode
sys.dont_write_bytecode = True

import argparse
import contextlib
import csv
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import io
import json
import math
import os
import re
import tarfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = _IMPORT_BYTECODE_SETTING

SURFACES = {
    "paper-en": "paper/latex/en/main.tex",
    "paper-ko": "paper/latex/ko/main.tex",
    "paper-en-traceability-supplement": "paper/latex/en/traceability-supplement.tex",
    "paper-ko-traceability-supplement": "paper/latex/ko/traceability-supplement.tex",
}
AUDIT = "research/academic-pipeline/gemini-review-20261113/results-v2"
AUDIT_INPUT_SHA256 = "6e6db5fd76e2f30acee88deb8d2b4cfc0eabbc7415c9d2718427f989d777525a"
NPC_REVISION = "fa9fb8a2c2249e35eddc7d4e0951c15a7b4bea09"
TABLE_PATTERN = re.compile(r"\\begin\s*\{(table\*?)\}(.*?)\\end\s*\{\1\}", re.DOTALL)
LABEL_PATTERN = re.compile(r"\\label\s*\{(tab:[^{}]+)\}")


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _plain(value: str) -> str:
    """Only presentation whitespace/commands; numbers, signs and order survive."""
    value = re.sub(r"\\(?:texttt|textbf|path)\{([^{}]*)\}", r"\1", value)
    value = value.replace(r"\_", "_").replace(r"\allowbreak", "").replace("{}", "")
    return " ".join(value.split())


def _rows(block: str) -> list[list[str]]:
    _require(block.count(r"\midrule") == 1, "manual table needs one explicit header/body boundary")
    body = block.split(r"\midrule", 1)[1].split(r"\bottomrule", 1)[0]
    rows = [row.strip() for row in re.split(r"\\\\(?:\[[^\]]*\])?", body) if row.strip()]
    return [[_plain(cell) for cell in row.split(" & ")] for row in rows]


@contextlib.contextmanager
def _project_imports(root: Path):
    """Resolve every project import inside the selected tree before execution."""
    old_path = sys.path[:]
    old_bytecode = sys.dont_write_bytecode
    names = {
        path.stem
        for base in (root, Path(__file__).resolve().parents[1])
        for path in (base / "scripts").glob("*.py")
    }

    def local(name: str) -> bool:
        return name.split(".", 1)[0] in names | {"nesy_game", "scripts"}

    class SelectedRootImports(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if not local(fullname):
                return None
            search_path = path
            if "." not in fullname:
                search_path = (
                    [str(root / "src")]
                    if fullname == "nesy_game"
                    else [str(root)]
                    if fullname == "scripts"
                    else [str(root / "scripts")]
                )
            spec = importlib.machinery.PathFinder.find_spec(fullname, search_path)
            if spec is None:
                raise ModuleNotFoundError(f"required selected-root module missing: {fullname}")
            origins = (
                [spec.origin]
                if spec.origin not in (None, "namespace")
                else list(spec.submodule_search_locations or [])
            )
            if not origins or any(
                not Path(origin).resolve().is_relative_to(root) for origin in origins
            ):
                raise ModuleNotFoundError(
                    f"required module is not supplied by selected project: {fullname}"
                )
            return spec

    saved = {name: module for name, module in list(sys.modules.items()) if local(name)}
    for name in saved:
        del sys.modules[name]
    sys.path[:0] = [str(root / "scripts"), str(root / "src"), str(root)]
    finder = SelectedRootImports()
    sys.meta_path.insert(0, finder)
    sys.dont_write_bytecode = True
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        for name in list(sys.modules):
            if local(name):
                del sys.modules[name]
        sys.modules.update(saved)
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode


class _Verifier:
    def __init__(
        self, root: Path, npc_root: Path | None, *, public_source_projection: bool = False
    ):
        self.root = root
        self.npc_root = npc_root
        self.public_source_projection = public_source_projection
        self.expected: dict[str, bytes] = {}
        self.family: dict[str, str] = {}
        self.values: dict[str, Any] = {}
        self.report: dict[str, Any] = {
            "schema_version": "paper-claims-verification/v1",
            "status": "ERROR",
            "scope": "Layer A: registered reached-table/source claims; offline receipt and local source materialization only",
            "source_verification_mode": "EXPLICIT_PUBLIC_SOURCE_PROJECTION"
            if public_source_projection
            else "STRICT_ORIGINAL_SOURCE",
            "surfaces": [],
            "tables": [],
            "checks": [],
            "registered_unreachable": [],
            "derivative_only": [],
            "preserved_statuses": {},
            "claim_sites": [],
            "withdrawn_evidence": [],
            "external_layers": [
                {"id": name, "status": "NOT_EXECUTED_BY_THIS_COMMAND"}
                for name in (
                    "fresh-engine-and-web-integration",
                    "pdf-build-layout-and-render",
                    "provider-recollection",
                )
            ],
            "protected_snapshot": {"status": "NOT_CHECKED"},
            "limitations": [
                "Exact equality concerns specified local source bytes, not cross-platform PDF/engine/provider bitwise identity.",
                "Unkeyed hashes do not authenticate origins or resist coordinated rewriting of all trust anchors.",
                "Narrative coverage is limited to explicitly listed claim sites, not every assertion in arbitrary prose.",
            ],
        }
        if public_source_projection:
            self.report["scope"] += (
                "; explicit public reviewer-source derivative and original commitments only; private originals not reverified"
            )
            self.report["limitations"].append(
                "Public reviewer-source projection verification cannot recompute the SHA-256 of the two withheld original files or independently establish the hidden /url removal from private bytes."
            )

    def check(self, name: str, operation):
        try:
            detail = operation()
        except (ImportError, FileNotFoundError) as exc:
            result = {"id": name, "status": "BLOCKED", "detail": str(exc)}
        except (
            OSError,
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            AttributeError,
            AssertionError,
            RuntimeError,
        ) as exc:
            result = {"id": name, "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"}
        else:
            result = {"id": name, "status": "PASS", "detail": detail or "validated"}
        self.report["checks"].append(result)
        self.family[name] = result["status"]
        return result

    def module(self, name: str):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        _require(path.is_relative_to(self.root), f"dependency outside selected project: {name}")
        return module

    def exact(self, relative: str, expected: str | bytes) -> None:
        payload = expected.encode("utf-8") if isinstance(expected, str) else expected
        actual = (self.root / relative).read_bytes()
        self.expected[relative] = payload
        _require(
            actual == payload,
            f"source materialization mismatch: {relative}; expected SHA256 {_sha(payload)}, observed {_sha(actual)}",
        )
        self.report["claim_sites"].append(
            {"source": relative, "binding": "exact source materialization", "sha256": _sha(payload)}
        )

    def inventory(self, visual, manifest):
        validator = visual.Validator(require_pdf_tools=False, check_regeneration=False)
        self.closures = {}
        for surface, relative in SURFACES.items():
            sources = validator._publication_sources(self.root / relative)
            self.closures[surface] = sources
            entry = {
                "id": surface,
                "source": relative,
                "anchors": [],
                "table_count": 0,
                "binding_count": 0,
                "errors": [],
            }
            for source, text in sources.items():
                original = re.sub(
                    r"(?<!\\)%[^\n]*", "", (self.root / source).read_text(encoding="utf-8")
                )
                document = re.split(r"\\begin\s*\{document\}", original, maxsplit=1)
                body = document[-1]
                if re.search(r"\\(?:if[A-Za-z]*|else|fi|def|let|csname|endinput)\b", body):
                    entry["errors"].append(f"unsupported structural TeX control: {source}")
                if re.search(
                    r"\\(?:gdef|edef|xdef|futurelet|includeonly|newenvironment|renewenvironment|scantokens|catcode)\b",
                    original,
                ):
                    entry["errors"].append(
                        f"unsupported structural TeX definition/filter: {source}"
                    )
                ending = re.split(r"\\end\s*\{document\}", original, maxsplit=1)
                if len(ending) == 2 and ending[1].strip():
                    entry["errors"].append(f"unreachable content after end of document: {source}")
                # Font-selection conditionals in the existing Korean preamble do
                # not hide content; table/input-bearing conditionals are rejected.
                if len(document) == 2:
                    prefix = document[0]
                    if re.search(r"\\if[A-Za-z]*\b", prefix) and re.search(
                        r"\\(?:input|include)\s*\{|\\begin\s*\{table", prefix
                    ):
                        entry["errors"].append(
                            f"structural content inside preamble conditional: {source}"
                        )
                matches = list(TABLE_PATTERN.finditer(text))
                remaining = TABLE_PATTERN.sub("", text)
                if LABEL_PATTERN.search(remaining):
                    entry["errors"].append(f"orphan table label outside table: {source}")
                if any(
                    len(re.findall(rf"\\{command}\s*\{{table\*?\}}", text)) != len(matches)
                    for command in ("begin", "end")
                ):
                    entry["errors"].append(f"unbalanced or nested table environments: {source}")
                for index, match in enumerate(matches, 1):
                    block = match.group(2)
                    labels = LABEL_PATTERN.findall(block)
                    anchor = labels[0] if labels else f"<unlabeled:{source}:{index}>"
                    entry["anchors"].append(anchor)
                    owners = [
                        owner
                        for owner in manifest.get("table_sources", [])
                        if anchor in owner.get("anchors", [])
                        and surface in owner.get("rendered_in", [])
                        and source in {r["path"] for r in owner.get("layout_sources", [])}
                    ]
                    errors = []
                    if len(labels) != 1 or not re.search(r"\\begin\s*\{tabular(?:x|\*)?\}", block):
                        errors.append("table needs exactly one tab: label and a tabular body")
                    if len(owners) != 1:
                        errors.append(f"expected one reached manifest owner, found {len(owners)}")
                    record = {
                        "surface_id": surface,
                        "anchor": anchor,
                        "source": source,
                        "block_index": index,
                        "table_source_id": owners[0]["id"] if len(owners) == 1 else None,
                        "binding_kind": None,
                        "adapter_id": None,
                        "source_receipts": owners[0].get("data_sources", [])
                        if len(owners) == 1
                        else [],
                        "status": "FAIL" if errors else "PENDING",
                        "detail": "; ".join(errors),
                    }
                    record["_block"] = block
                    self.report["tables"].append(record)
            duplicate = [
                anchor for anchor, count in Counter(entry["anchors"]).items() if count != 1
            ]
            if duplicate:
                entry["errors"].append(f"duplicate table labels/inclusions: {duplicate}")
            entry["table_count"] = len(entry["anchors"])
            self.report["surfaces"].append(entry)
        for owner in manifest.get("table_sources", []):
            if not owner.get("rendered_in"):
                self.report["derivative_only"].append(
                    {
                        "id": owner["id"],
                        "scope": "receipt/inventory only; not a reached-table numerical validation",
                    }
                )
            for surface in owner.get("rendered_in", []):
                sources = self.closures.get(surface, {})
                for anchor in owner.get("anchors", []):
                    found = any(
                        re.search(r"\\label\s*\{" + re.escape(anchor) + r"\}", text)
                        for text in sources.values()
                    )
                    layout = bool(
                        set(sources) & {r["path"] for r in owner.get("layout_sources", [])}
                    )
                    if not found or not layout:
                        self.report["registered_unreachable"].append(
                            {"id": owner["id"], "surface_id": surface, "anchor": anchor}
                        )
        errors = validator.errors + [
            error for surface in self.report["surfaces"] for error in surface["errors"]
        ]
        if self.report["registered_unreachable"]:
            errors.append(
                f"registered published anchors are unreachable: {self.report['registered_unreachable']}"
            )
        _require(not errors, "; ".join(errors))
        return f"discovered {len(self.report['tables'])} table occurrences across {len(SURFACES)} roots; no fixed count assumption"

    def pilot(self):
        producer = self.module("generate_paper_results")
        runner = self.module("run_conformance_pilot")
        data = _json(producer.RESULTS_PATH)
        _require(
            data["inference"] == "none; raw designed-fixture counts only",
            "E1 inference boundary drift",
        )
        base = producer.RESULTS_PATH.parent
        receipt = _json(base / "sha256-manifest.json")
        for item in receipt["artifacts"]:
            path = base / item["path"]
            payload = path.read_bytes()
            _require(
                len(payload) == item["bytes"] and _sha(payload) == item["sha256"],
                f"frozen E1 artifact drift: {item['path']}",
            )
        specification = runner.load_manifest(self.root / "configs/pilot-manifest.json")
        assignment, _ = runner._build_assignment_manifest(
            specification, runner._world_state(specification["base_state"]), data
        )
        _require(
            assignment == _json(base / "pilot-assignment-manifest.json"),
            "E1 assignment/provenance mismatch",
        )
        runner._assert_complete(data)
        rows = data["repair_arms"]["rows"]
        for summary in data["repair_arms"]["raw_counts_by_arm"]:
            selected = [row for row in rows if row["arm_id"] == summary["arm_id"]]
            _require(
                len(selected) == summary["case_count"],
                f"E1 assigned denominator drift: {summary['arm_id']}",
            )
            _require(
                sum(row["final_status"] == "commit" for row in selected) == summary["commit_count"],
                f"E1 commit aggregate drift: {summary['arm_id']}",
            )
        for language in ("en", "ko"):
            for stem, text in (
                ("pilot_results", producer._result_text(data, language == "ko")),
                ("pilot_tables", producer._tables(data, language == "ko")),
                ("contribution_map", producer._contribution_map(language == "ko")),
                ("evidence_lanes", producer._lane_table(language == "ko")),
            ):
                self.exact(f"paper/latex/generated/{stem}_{language}.tex", text)
        self.values["pilot"] = data
        return "E1 frozen rows, assignment provenance, summaries and bilingual table/prose materialization"

    def public_review_source(self, inputs, sources):
        """Validate the approved publication derivative, never the withheld bytes."""
        base = self.root / "research/academic-pipeline/gemini-review-20261113"
        receipt_path = base / "public-source-projection-v1.json"
        receipt_payload = receipt_path.read_bytes()
        receipt_digest = "7c2c4acd22bd811729fcd2645039bae5ebf99313a74ff2de28338a7458475232"
        _require(
            len(receipt_payload) == 2618 and _sha(receipt_payload) == receipt_digest,
            "approved public reviewer-source projection receipt digest drift",
        )
        receipt = json.loads(receipt_payload)
        _require(
            receipt["schema_version"] == "public-source-projection-v1"
            and receipt["artifact_classification"] == "publication-derivative",
            "public reviewer-source projection classification drift",
        )
        projection = receipt["projection"]
        _require(
            projection["source_format"] == "json"
            and projection["allowed_semantic_operations"] == [{"op": "remove", "path": "/url"}]
            and projection["all_other_json_fields"] == "UNCHANGED",
            "reviewer-source projection exceeds the approved top-level /url removal",
        )
        expected_commitments = {
            "input_manifest": {
                "path": "results-v2/input_hashes.json",
                "sha256": AUDIT_INPUT_SHA256,
                "bytes": 649,
            },
            "source_manifest": {
                "path": "results-v2/source_hashes.json",
                "sha256": "098bc6e3f678b79a8db1a0195efac90ff22ac31a31b7dafe0b12de62bbda135f",
                "bytes": 2204,
            },
        }
        _require(
            receipt["original_commitments"] == expected_commitments,
            "public projection altered an original audit manifest commitment",
        )
        for identity in expected_commitments.values():
            payload = (base / identity["path"]).read_bytes()
            _require(
                len(payload) == identity["bytes"] and _sha(payload) == identity["sha256"],
                "original audit manifest bytes drifted under public projection",
            )
        public_identity = {
            "path": "reviewer-source.public.json",
            "sha256": "278182062607a58b6d55e6d4c062f9651469d14001345710335fc2bc25a3079e",
            "bytes": 20262,
        }
        _require(
            receipt["public_derivative"] == public_identity,
            "approved public reviewer-source identity drift",
        )
        expected_paths = {"reviewer-source.json", "results-v2/reviewer-source.json"}
        mappings = receipt["mappings"]
        _require(
            len(mappings) == len(expected_paths)
            and {mapping["original"]["path"] for mapping in mappings} == expected_paths,
            "public projection must map exactly the two distinct withheld originals",
        )
        original_digest = "09e18301e2fc537af0666b444ac3aadee6a0c6f3dc8e2e0f1c5b3bd8b3ac4ea6"
        for mapping in mappings:
            _require(
                set(mapping) == {"original", "public_path"}
                and mapping["original"]
                == {"path": mapping["original"]["path"], "sha256": original_digest, "bytes": 20336}
                and mapping["public_path"] == public_identity["path"],
                "public projection original-to-derivative mapping drift",
            )
        original_source_key = (
            "research/academic-pipeline/gemini-review-20261113/reviewer-source.json"
        )
        _require(
            inputs["reviewer-source.json"] == sources[original_source_key] == original_digest
            and sources["scripts/run_gemini_review_evaluation.py"]
            == "23619724bc24782e170c620f0bbe256f6cd4c85e4b01a0cad1f6b121536939ff",
            "original reviewer/executed-runner commitments changed under public projection",
        )
        public_path = base / public_identity["path"]
        for path in (receipt_path, public_path):
            _require(
                path.resolve().is_relative_to(base.resolve())
                and not any(
                    parent.is_symlink()
                    for parent in (path, *path.parents)
                    if parent.is_relative_to(self.root)
                ),
                "public reviewer-source dependency escapes its selected project path",
            )
        public_payload = public_path.read_bytes()
        _require(
            len(public_payload) == public_identity["bytes"]
            and _sha(public_payload) == public_identity["sha256"],
            "public reviewer-source bytes drift from the independently pinned derivative",
        )
        public_source = json.loads(public_payload)
        _require(
            isinstance(public_source, dict) and "url" not in public_source,
            "withheld top-level reviewer URL was restored to the public derivative",
        )
        _require(
            receipt["verification_scope"]["private_original_archive_reverification"]
            == "NOT_PERFORMED_BY_PUBLIC_COMMAND",
            "public projection falsely claims original-private-source reverification",
        )
        prefix = str(base.relative_to(self.root)) + "/"
        self.report["public_source_projection"] = {
            "status": "PUBLIC_DERIVATIVE_VERIFIED_ORIGINAL_COMMITMENTS_ONLY",
            "receipt": {
                "path": prefix + receipt_path.name,
                "sha256": receipt_digest,
                "bytes": len(receipt_payload),
            },
            "public_source": {
                "path": prefix + public_path.name,
                "sha256": public_identity["sha256"],
                "bytes": len(public_payload),
            },
            "withheld_originals": [
                {
                    "path": prefix + mapping["original"]["path"],
                    "sha256": original_digest,
                    "bytes": 20336,
                }
                for mapping in mappings
            ],
            "private_original_reverification": "NOT_PERFORMED_BY_THIS_COMMAND",
            "scope": "All nonwithheld original inputs, executed sources, outcomes, accounting, reference checks, replays, CSVs and table materializations remain validated; the two original source byte hashes cannot be recomputed from this public derivative.",
        }
        return "approved public reviewer-source derivative and original manifest commitments verified; exactly two private original identities are not publicly reverified"

    def audit(self):
        runner = self.module("run_gemini_review_evaluation")
        producer = self.module("generate_paper_results")
        base = self.root / AUDIT
        _require(
            _sha((base / "input_hashes.json").read_bytes()) == AUDIT_INPUT_SHA256,
            "frozen audit input-manifest digest mismatch",
        )
        inputs = _json(base / "input_hashes.json")
        sources = _json(base / "source_hashes.json")
        if self.public_source_projection:
            projection = self.check(
                "public-source-projection", lambda: self.public_review_source(inputs, sources)
            )
            _require(
                projection["status"] == "PASS",
                "explicit public reviewer-source projection did not validate",
            )
        for relative, digest in inputs.items():
            if self.public_source_projection and relative == "reviewer-source.json":
                continue
            _require(
                _sha((base / relative).read_bytes()) == digest,
                f"audit frozen input drift: {relative}",
            )
        expected_sources = (
            {"scripts/run_gemini_review_evaluation.py", "scripts/review_reference.py"}
            | {
                str(path.relative_to(self.root))
                for path in (self.root / "src/nesy_game").glob("*.py")
            }
            | {
                f"research/academic-pipeline/gemini-review-20261113/{name}"
                for name in ("protocol-v2.json", "reviewer-source.json", "review-response.json")
            }
        )
        _require(set(sources) == expected_sources, "audit executed-source inventory drift")
        for relative, digest in sources.items():
            if (
                self.public_source_projection
                and relative
                == "research/academic-pipeline/gemini-review-20261113/reviewer-source.json"
            ):
                continue
            _require(
                _sha((self.root / relative).read_bytes()) == digest,
                f"audit executed-source hash mismatch: {relative}",
            )
        protocol = _json(base / "protocol.json")
        summary = _json(base / "summary.json")
        _require(
            summary["input_hashes"] == inputs and summary["source_hashes"] == sources,
            "audit summary provenance drift",
        )
        for frozen, current in (
            ("protocol.json", "protocol-v2.json"),
            ("reviewer-source.json", "reviewer-source.json"),
            ("review-response.json", "review-response.json"),
        ):
            if self.public_source_projection and frozen == current == "reviewer-source.json":
                continue
            _require(
                (base / frozen).read_bytes() == (base.parent / current).read_bytes(),
                f"audit canonical/frozen source mismatch: {frozen}",
            )
        arms = tuple(arm["id"] for arm in protocol["arms"])
        _require(arms == runner.ARMS, "audit arm identity/order mismatch")
        cases = {
            "core": _json(base / "cases.json"),
            "surface": _json(base / "surface_sentinels.json"),
        }
        expected = Counter(
            (cohort, case["case_id"], arm)
            for cohort, records in cases.items()
            for case in records
            for arm in arms
        )
        _require(set(expected.values()) == {1}, "audit duplicate frozen cases")
        inventory = Counter(
            (row["cohort"], row["case_id"], row["arm"])
            for row in _json(base / "assignment_inventory.json")
        )
        _require(inventory == expected, "audit frozen inventory mismatch")
        _require(
            len(cases["core"]) == protocol["assignment_count_per_arm"]
            and len(cases["surface"]) == protocol["surface_sentinels"]["units_per_arm"],
            "audit cohort denominator mismatch",
        )
        rows = {}
        actual = Counter()
        outcome_digests = {
            "core": "bb32a68931016bc0b23fde3210c9f6f9a87768a87fd334ae6fad638fa4705d89",
            "surface": "f25fdb767bd50e67d255be4369fddb6777a3eea51bb89a15aa11d52992f82ab1",
        }
        for cohort, stem in (("core", "rows"), ("surface", "surface_rows")):
            _require(
                _sha((base / f"{stem}.jsonl").read_bytes()) == outcome_digests[cohort],
                f"frozen audit {cohort} outcome receipt digest drift",
            )
            rows[cohort] = [
                json.loads(line)
                for line in (base / f"{stem}.jsonl").read_text().splitlines()
                if line.strip()
            ]
            by_id = {case["case_id"]: case for case in cases[cohort]}
            for row in rows[cohort]:
                case = by_id[row["case_id"]]
                actual[(cohort, row["case_id"], row["arm"])] += 1
                _require(
                    row["cohort"] == cohort and row["source_hashes"] == sources,
                    "audit row cohort/source binding mismatch",
                )
                _require(
                    row["input_hash"] == _sha(_canonical(case).encode())
                    and row["initial_state"] == case["state"]
                    and row["initial_candidate"] == case["candidate"],
                    f"audit raw input mismatch: {row['case_id']}",
                )
                _require(
                    row["status"] in {"COMMITTED", "HOLD", "FAILED"}
                    and (row["error"] is not None) == (row["status"] == "FAILED"),
                    "audit terminal/failure accounting mismatch",
                )
                _require(
                    type(row["latency_ms"]) in (int, float)
                    and math.isfinite(row["latency_ms"])
                    and row["latency_ms"] >= 0,
                    "audit recorded latency malformed",
                )
                _require(
                    row["model_called"] is False
                    and all(row[key] is None for key in ("model_id", "model_revision", "cost_usd")),
                    "audit non-model scope drift",
                )
                if row["status"] != "FAILED":
                    parsed = runner.parse_candidate_mapping(case["candidate"], allow_defaults=False)
                    reference = {}
                    reference_state = runner._reference_inputs(case, reference, parsed)
                    _require(
                        all(row.get(key) == value for key, value in reference.items()),
                        f"audit reference input/signature mismatch: {row['case_id']}/{row['arm']}",
                    )
                    final = runner.parse_candidate_mapping(
                        row["final_candidate"], allow_defaults=False
                    )
                    _require(
                        row["reference_final_valid"]
                        == runner.generic_accepts(reference_state, final),
                        f"audit final reference result mismatch: {row['case_id']}/{row['arm']}",
                    )
                    _require(
                        row["final_signature"]
                        == runner.structural_signature(row["final_candidate"]),
                        "audit final structural signature mismatch",
                    )
                    _require(
                        row["goal_reached"]
                        == (
                            row["status"] == "COMMITTED"
                            and "signal_restored" in row["final_state"]["facts"]
                        ),
                        "audit goal/state mismatch",
                    )
                    _require(
                        row["before_state_hash"] == runner._hash(runner._world_state(case["state"]))
                        and row["after_state_hash"]
                        == runner._hash(runner._world_state(row["final_state"])),
                        "audit state hash mismatch",
                    )
                    if row["arm"] == "schema_only":
                        _require(
                            row["native_outcome"] is None
                            and row["native_replay_equal"] is None
                            and row["semantic_gate_executed"] is False,
                            "schema-only arm invented native/semantic execution",
                        )
                    else:
                        native = row["native_outcome"]
                        replayed = runner.to_jsonable(runner.replay_trace_record(native))
                        _require(
                            replayed == row["final_state"] and row["native_replay_equal"] is True,
                            "audit native receipt replay/state mismatch",
                        )
                        _require(
                            native["candidate"] == row["final_candidate"]
                            and native["trace"] == row["attempts"]
                            and native["validation"] == row["validation"],
                            "audit native receipt/outcome projection mismatch",
                        )
                        _require(
                            row["status"]
                            == ("COMMITTED" if native["status"] == "commit" else "HOLD")
                            and row["semantic_gate_executed"] is True,
                            "audit terminal/gate receipt mismatch",
                        )
                        _require(
                            row["repair_attempt_count"] == native["attempts"]
                            and row["repair_budget"] == runner.REPAIR_BUDGETS[row["arm"]],
                            "audit repair count/budget mismatch",
                        )
            recomputed = runner.summarize_rows(rows[cohort])
            _require(summary[cohort] == recomputed, f"audit {cohort} raw-row/aggregate mismatch")
            with (base / f"{stem}.csv").open(encoding="utf-8", newline="") as handle:
                exported = list(csv.DictReader(handle))
            expected_export = [
                {
                    key: _canonical(value)
                    if isinstance(value, (dict, list))
                    else ""
                    if value is None
                    else str(value)
                    for key, value in row.items()
                }
                for row in rows[cohort]
            ]
            _require(exported == expected_export, f"audit {cohort} CSV/raw row mismatch")
        _require(actual == expected, "audit missing/duplicate/unexpected raw assignments")
        _require(
            summary["graph_agreement"] == runner._graph_agreement(cases["core"]),
            "audit frozen graph agreement mismatch",
        )
        for arm in arms:
            selected = [row for row in rows["surface"] if row["arm"] == arm]
            declared = [row for row in selected if row["variant"] == "surface_declared"]
            undeclared = [row for row in selected if row["variant"] == "surface_undeclared"]
            pairs = {
                "undeclared_assigned": len(undeclared),
                "declared_assigned": len(declared),
                "undeclared_committed": sum(row["status"] == "COMMITTED" for row in undeclared),
                "declared_held": sum(row["status"] == "HOLD" for row in declared),
                "narrative_state_mutation_checks": sum(
                    row["final_state"] is not None for row in selected
                ),
                "narrative_state_mutation_mismatches": [
                    row["case_id"]
                    for row in selected
                    if row["final_state"] is not None
                    and (
                        set(row["final_state"]["facts"])
                        != set(row["initial_state"]["facts"])
                        | (
                            set(row["final_candidate"]["effects"])
                            if row["status"] == "COMMITTED"
                            else set()
                        )
                        or row["final_state"]["quest_stage"] != row["initial_state"]["quest_stage"]
                    )
                ],
            }
            _require(
                summary["surface_pairs"][arm] == pairs,
                f"audit paired surface denominator/state mismatch: {arm}",
            )
        render_summary = {
            **summary,
            "core": {arm: summary["core"][arm] for arm in arms},
            "surface": {arm: summary["surface"][arm] for arm in arms},
        }
        for language in ("en", "ko"):
            frozen = runner._table_fragment(render_summary, language)
            self.exact(f"{AUDIT}/review_boundary_audit_{language}.tex", frozen)
            self.exact(
                f"paper/latex/generated/review_boundary_audit_{language}.tex",
                producer._review_boundary_publication(frozen, language == "ko"),
            )
        self.values["audit"] = summary
        detail = f"{len(rows['core'])} core and {len(rows['surface'])} separate surface retained assignments; no execution/re-timing"
        return detail + (
            "; explicit public reviewer-source derivative and original commitments only; two private original source files NOT_PERFORMED_BY_THIS_COMMAND"
            if self.public_source_projection
            else ""
        )

    def runtime(self):
        producer = self.module("generate_runtime_comparison_publication")
        data = producer.load_public_results(producer.RESULTS_PATH)
        identity = producer.load_identity_results(producer.IDENTITY_RESULTS_PATH)
        for language in ("en", "ko"):
            for stem, text in (
                (
                    "runtime_comparison_results",
                    producer.render_results_fragment(data, korean=language == "ko"),
                ),
                (
                    "runtime_comparison_tables",
                    producer.render_tables_fragment(data, korean=language == "ko"),
                ),
                (
                    "runtime_identity_extension",
                    producer.render_identity_fragment(identity, korean=language == "ko"),
                ),
            ):
                self.exact(f"paper/latex/generated/{stem}_{language}.tex", text)
        self.values["runtime"] = producer.compute_aggregates(data)
        self.values["runtime_rows"] = data["rows"]
        self.values["runtime_identity"] = identity
        return "original eight assigned rows and stopped identity extension remain separate, with null/NR and engine dispositions preserved"

    def disclosure(self):
        producer = self.module("generate_disclosure_paper_results")
        checker = self.module("check_disclosure_paper_evidence")
        data = producer._load()
        checker._check_packet()
        manifest = _json(checker.MANIFEST)
        metadata = checker._check_current_results(manifest)
        receipt = manifest.get("godot_receipt")
        if isinstance(receipt, dict):
            receipt = receipt.get("path")
        if not receipt:
            public = (
                self.root
                / "research/npc-disclosure/results-signal-explainer-20261023-r5/godot-disclosure-receipt.json"
            )
            candidates = sorted(producer.RESULTS.glob("*godot*receipt*.json"))
            receipt_path = candidates[0] if len(candidates) == 1 else public
        else:
            receipt_path = self.root / receipt
        checker._check_godot_receipt(receipt_path, metadata)
        semantics = self.module("nesy_game.disclosure")
        contract = semantics.load_frozen_contract(producer.PACKET, self.root, public_sources=True)
        retained_cases = list(producer._cases(data["packet"]).values())
        reproduced_rows = semantics._case_records(contract, retained_cases)
        _require(
            data["rows"] == reproduced_rows,
            "disclosure complete deterministic trace/state/replay/assertion source parity mismatch",
        )
        for language in ("en", "ko"):
            korean = language == "ko"
            self.exact(
                f"paper/latex/generated/disclosure_results_{language}.tex",
                producer._narrative(data, korean),
            )
            self.exact(
                f"paper/latex/generated/disclosure_tables_{language}.tex",
                producer._contract_table(data, korean)
                + producer._arms_table(data, korean)
                + producer._fixtures_table(data, korean),
            )
        self.values["disclosure"] = data
        return "NPC-DISC-1 retained traces, stored Godot receipt and exact source materialization; no fresh engine execution"

    def npc(self):
        if self.npc_root is None or not self.npc_root.is_dir():
            raise FileNotFoundError(
                "required NPC006 source tree at revision "
                + NPC_REVISION
                + "; supply npc_evidence_root (CLI can prepare local Git objects)"
            )
        producer = self.module("generate_npc_paper_results")
        data = producer._load_packet(self.npc_root)
        for language in ("en", "ko"):
            self.exact(
                f"paper/latex/generated/npc_results_{language}.tex",
                producer._results(data, language == "ko"),
            )
            self.exact(
                f"paper/latex/generated/npc_tables_{language}.tex",
                producer._tables(data, language == "ko"),
            )
        self.values["npc"] = data
        return "NPC006 historical source validation: 16 engineering and 72 screening rows; no current-source fallback"

    def kg(self):
        module = self.module("nesy_game.kg_ontology_simulation")
        payloads, matrix, _ = module.build_artifact_payloads(self.root)
        _require(
            not module.check_artifacts(self.root, payloads),
            "; ".join(module.check_artifacts(self.root, payloads)),
        )
        self.expected.update({str(path): payload for path, payload in payloads.items()})
        self.values["kg"] = matrix
        return (
            "complete KG authored closed-world payloads reproduced in memory; no artifact refresh"
        )

    def v5(self):
        producer = self.module("generate_paired_feedback_figures")
        data = producer.load_cohorts()
        import zipfile

        archive_path = (
            self.root
            / "research/codex_feedback_pilot/paired-model-comparison-20261110-v5-source.zip"
        )
        _require(
            _sha(archive_path.read_bytes())
            == "22bdfebbb40d55f7a2ff951aab1b18789c495a8fc388f0624ef5ef6658b34b60",
            "frozen v5 executed-source ZIP digest mismatch",
        )
        public_digests = {
            "gpt-5.6-luna": "96265fe867e84f752615e4a807c2389b887f7adac82c8e7c66de8d30f3326a0e",
            "gpt-5.6-terra": "64651e9035d494a1b3ce09e7d6632b28fe2098b52a4990f34234853b5c48db4d",
        }
        with zipfile.ZipFile(archive_path) as archive:
            members = {
                item.filename: _sha(archive.read(item))
                for item in archive.infolist()
                if not item.is_dir()
            }
        for selector, digest in public_digests.items():
            source = producer.COHORT_ROOT / f"{producer.COHORT_PREFIX}{selector}" / "results.json"
            _require(
                _sha(source.read_bytes()) == digest,
                f"frozen v5 public outcome projection drift: {selector}",
            )
            metadata = data["metadata"][selector]
            _require(
                metadata["source_sha256"] == members,
                f"v5 executed ZIP/cohort source bindings disagree: {selector}",
            )
        for row in data["rows"]:
            prompt = self.root / row["source"]
            prompt = prompt.parent / row["prompt_file"]
            _require(
                _sha(prompt.read_bytes()) == row["prompt_sha256"],
                f"v5 retained prompt hash drift: {row['selector']}/{row['case_id']}/{row['condition']}",
            )
        self.values["v5"] = data
        for source, digest in data["sources"].items():
            _require(
                _sha((self.root / source).read_bytes()) == digest,
                f"v5 source binding mismatch: {source}",
            )
        strata = producer.describe_v5_strata(data)
        self.values["strata"] = strata
        for language in ("en", "ko"):
            self.exact(
                f"paper/latex/generated/paired_feedback_strata_{language}.tex",
                producer.render_v5_strata_tex(strata, language=language),
            )
        return "all 20 assigned v5 outcomes validated; post-hoc strata are descriptive, never a replacement for five-case denominators"

    def captures(self, visual, manifest):
        reached = [
            surface
            for surface, sources in self.closures.items()
            if any(
                re.search(r"\\label\s*\{fig:engine-cutscenes\}", text) for text in sources.values()
            )
        ]
        if not reached:
            return "no reached engine-cutscenes figure; no capture claim made"
        assets = [
            asset
            for asset in manifest.get("visual_assets", [])
            if asset.get("id") == "paper-engine-cutscenes"
        ]
        _require(
            len(assets) == 1, "reached engine capture montage needs one registered source binding"
        )
        asset = assets[0]
        records = [
            record
            for record in asset["data_sources"]
            if record["path"].endswith("/provenance.json")
        ]
        _require(len(records) == 1, "engine capture provenance binding is missing/ambiguous")
        provenance_path = self.root / records[0]["path"]
        provenance_payload = provenance_path.read_bytes()
        provenance_digest = _sha(provenance_payload)
        original_digest = "83a5fb90765f071c6baccaea651640398f8118991f550c261b0810135942811c"
        _require(
            provenance_path.resolve().is_relative_to(self.root)
            and len(provenance_payload) == records[0]["bytes"]
            and provenance_digest == records[0]["sha256"],
            "current engine provenance/registered receipt mismatch",
        )
        provenance = json.loads(provenance_payload)
        base = provenance_path.parent
        projection_path = base / "public-path-projection-v1.json"
        projected_files = None
        if projection_path.exists():
            projection_payload = projection_path.read_bytes()
            _require(
                _sha(projection_payload)
                == "b30b13c760a047a4d9840ed0f35adc4543e61058f374bf948fe38f825d66cff5",
                "approved public capture projection receipt digest drift",
            )
            projection = json.loads(projection_payload)
            _require(
                projection["schema_version"] == "1.0.0"
                and projection["status"] == "PUBLIC_PREFIX_RELOCATED_PUBLICATION_DERIVATIVE"
                and projection["evidence_set_id"] == base.name,
                "public capture projection identity/classification drift",
            )
            entries = projection["files"]
            projected_files = {entry["file"]: entry for entry in entries}
            _require(
                len(projected_files)
                == len(entries)
                == projection["counts"]["original_files"]
                == projection["originals"]["file_count"]
                == 21,
                "public capture projection has duplicate/missing original file identities",
            )
            classes = Counter()
            for entry in entries:
                relative = Path(entry["file"])
                _require(
                    not relative.is_absolute()
                    and relative.as_posix() == entry["file"]
                    and not {".", ".."}.intersection(relative.parts),
                    "public capture projection contains an unsafe relative path",
                )
                path = base / relative
                _require(
                    path.is_file()
                    and path.resolve().is_relative_to(base.resolve())
                    and not any(
                        parent.is_symlink()
                        for parent in (path, *path.parents)
                        if parent.is_relative_to(base)
                    ),
                    "public capture projection file is missing or escapes its evidence set",
                )
                for identity in (entry["original"], entry["public"]):
                    _require(
                        type(identity["bytes"]) is int
                        and identity["bytes"] >= 0
                        and isinstance(identity["sha256"], str)
                        and re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) is not None,
                        "malformed public/original capture file identity",
                    )
                payload = path.read_bytes()
                _require(
                    len(payload) == entry["public"]["bytes"]
                    and _sha(payload) == entry["public"]["sha256"],
                    f"public capture projection byte/hash mismatch: {entry['file']}",
                )
                classification = entry["classification"]
                _require(
                    classification
                    in {"unchanged-original-bytes", "public-path-relocated-derivative"}
                    and (entry["original"] == entry["public"])
                    == (classification == "unchanged-original-bytes"),
                    "capture original/derivative file classification mismatch",
                )
                classes[classification] += 1
            _require(
                classes["unchanged-original-bytes"]
                == projection["counts"]["unchanged_original_files"]
                == 14
                and classes["public-path-relocated-derivative"]
                == projection["counts"]["transformed_existing_files"]
                == 7
                and projection["counts"]["new_projection_receipts"] == 1,
                "public capture original/derivative accounting drift",
            )
            actual_files = {
                str(path.relative_to(base)) for path in base.rglob("*") if path.is_file()
            }
            _require(
                actual_files == set(projected_files) | {projection_path.name},
                "public capture projection file inventory does not match its declared closure",
            )
            provenance_entry = projected_files["provenance.json"]
            _require(
                provenance_entry["original"] == {"bytes": 23410, "sha256": original_digest}
                and provenance_entry["public"]
                == {"bytes": len(provenance_payload), "sha256": provenance_digest}
                and provenance_digest
                == "0e3057ef1ac368a44ba08cc25b780f8c87b11a131b149dea68f8c574d9014cf3",
                "trusted original/current public provenance mapping mismatch",
            )
            metadata = provenance["publication_projection"]
            _require(
                metadata["classification"]
                == "PUBLIC_PATH_RELOCATED_DERIVATIVE_NOT_RAW_CAPTURE_PROVENANCE"
                and metadata["original"] == provenance_entry["original"]
                and metadata["projection_id"] == projection["projection_id"]
                and metadata["receipt"] == projection_path.name,
                "current provenance does not identify its explicit publication derivative receipt",
            )
            self.report["capture_projection"] = {
                "status": projection["status"],
                "source": str(projection_path.relative_to(self.root)),
                "sha256": _sha(projection_payload),
                "original_provenance_sha256": original_digest,
                "public_provenance_sha256": provenance_digest,
                "validated_public_files": len(entries),
                "classification": metadata["classification"],
                "private_original_archive_reverification": "NOT_PERFORMED_BY_THIS_COMMAND",
            }
        else:
            _require(
                provenance_digest == original_digest,
                "stored original engine capture provenance digest drift; a public derivative requires its explicit projection receipt",
            )
        _require(
            provenance["claim_scope"]
            == "authored_native_3d_game_scene_render_and_state_correspondence_only",
            "engine capture claim scope drift",
        )
        packet_entries = provenance["packet_files_before_provenance"]
        _require(
            len({entry["file"] for entry in packet_entries}) == len(packet_entries),
            "duplicate engine packet receipt identity",
        )
        for record in provenance["packet_files_before_provenance"]:
            path = base / record["file"]
            _require(
                path.resolve().is_relative_to(base.resolve()),
                "engine capture receipt path escapes evidence set",
            )
            if projected_files is not None:
                projected = projected_files.get(record["file"])
                _require(
                    projected is not None
                    and projected["public"]
                    == {"bytes": record["bytes"], "sha256": record["sha256"]},
                    "current provenance packet receipt differs from declared public projection",
                )
            payload = path.read_bytes()
            _require(
                len(payload) == record["bytes"] and _sha(payload) == record["sha256"],
                f"engine capture packet receipt drift: {record['file']}",
            )
        png = self.module("png_contract")
        _require(
            all(
                len({capture[key] for capture in provenance["captures"]})
                == len(provenance["captures"])
                for key in ("stage", "file", "sidecar")
            ),
            "duplicate engine capture stage/file/sidecar identity",
        )
        for capture in provenance["captures"]:
            path = base / capture["file"]
            payload = path.read_bytes()
            _require(
                len(payload) == capture["bytes"] and _sha(payload) == capture["sha256"],
                f"engine PNG receipt drift: {capture['stage']}",
            )
            png.validate_render_png(path, width=capture["width"], height=capture["height"])
            sidecar = _json(base / capture["sidecar"])
            event = capture["observed_render_event"]
            _require(
                event["event_type"] == "SHOT-SAVED", "stored capture is not a SHOT-SAVED event"
            )
            for key in ("stage", "width", "height", "state_sha256_before", "state_sha256_after"):
                _require(
                    sidecar[key] == capture[key] == event["payload"][key],
                    f"engine sidecar/event field drift: {capture['stage']}/{key}",
                )
            _require(
                sidecar["sha256"] == capture["sha256"] and sidecar["engineering_only"] is True,
                "engine capture classification/hash drift",
            )
            related = capture["related_fixture_event"]
            matches = related["world_state_hash"] == capture["state_sha256_after"]
            _require(
                matches == capture["related_fixture_state_matches_captured_after_state"],
                "engine related fixture/state correspondence was relabelled",
            )
        validator = visual.Validator(require_pdf_tools=False, check_regeneration=False)
        _require(
            validator._validate_capture_montage(
                self.root / "paper/latex/figures/fig_engine_cutscenes.svg", asset
            ),
            "; ".join(validator.errors),
        )
        return "stored four authored native images, SHOT-SAVED state bindings and unretouched montage checked; refusal mapping is not exact fixture replay; no performance/player/efficacy PASS"

    def statuses(self):
        import yaml

        try:
            ledger = yaml.safe_load((self.root / "research/claim-ledger.yaml").read_text())
        except yaml.YAMLError as exc:
            raise ValueError("claim ledger YAML is invalid") from exc
        claims = ledger["claims"] if isinstance(ledger, dict) else ledger
        by_id = {claim["id"]: claim for claim in claims}
        statuses = self.report["preserved_statuses"]
        for number in range(1, 6):
            key = f"C-RESULT-{number:03}"
            statuses[key] = by_id[key]["status"]
            _require(statuses[key] == "TODO-RESULT", f"unmeasured result status promoted: {key}")
        summary = _json(self.root / "research/prospective-pilot-20261103/results-v1/summary.json")
        counts = summary["counts"]
        _require(
            summary["status"] == "NOT_RUN/BLOCKED"
            and counts["executed"] == counts["attempted"] == 0
            and counts["blocked"] == 180,
            "prospective unexecuted/blocked scope drift",
        )
        prospective = self.root / "research/prospective-pilot-20261103"
        planned = _json(prospective / "planned-units-v1.json")
        collection = _json(prospective / "results-v1/collection-status.json")
        prospective_api = self.module("nesy_game.prospective_pilot")
        protocol = _json(prospective / "protocol-v1.json")
        prospective_api.validate_protocol(protocol)
        protocol_digest = prospective_api.protocol_sha256(protocol)
        _require(
            planned["protocol_sha256"] == collection["protocol_sha256"] == protocol_digest,
            "prospective protocol/inventory source binding drift",
        )
        _require(
            planned["units"] == protocol["units"],
            "prospective planned unit inventory differs from frozen protocol",
        )
        planned_ids = [row["unit_id"] for row in planned["units"]]
        actual_ids = [row["unit_id"] for row in collection["rows"]]
        _require(
            len(set(planned_ids))
            == len(planned_ids)
            == counts["planned"]
            == collection["counts"]["planned"]
            and actual_ids == planned_ids,
            "prospective planned/blocked assignment identity drift",
        )
        _require(
            all(
                row["admitted"] is False
                and row["executed"] is False
                and row["native_process_starts"] == row["dispatch_attempts"] == 0
                and row["terminal_outcome"] is None
                and row["successful"] is None
                and bool(row["blocked_reasons"])
                for row in collection["rows"]
            ),
            "prospective unexecuted row was promoted or loses blockers",
        )
        _require(
            all(collection["counts"][key] == counts[key] for key in collection["counts"]),
            "prospective collection/summary totals drift",
        )
        statuses.update(
            prospective_completed=counts["executed"],
            prospective_assigned=counts["blocked"],
            prospective_status="BLOCKED",
        )
        rubric = _json(self.root / "research/traceability-scoring-20261023/rubric.json")
        _require(
            rubric["status"] == "PROPOSED_NOT_VALIDATED"
            and rubric["measurement_status"]["proposal_not_measured"] is True,
            "traceability rubric was promoted to measured",
        )
        _require(
            [dimension["id"] for dimension in rubric["dimensions"]]
            == [f"TR{n:02}" for n in range(1, 7)],
            "traceability dimension identities changed",
        )
        statuses["traceability_rubric"] = "PROPOSED_UNMEASURED"
        statuses["traceability_source_status"] = rubric["status"]
        return "source-derived TODO-RESULT, prospective blocked 0/180 and unmeasured six-dimension rubric preserved"

    def narratives(self):
        _require(
            self.family.get("audit") == self.family.get("v5") == "PASS",
            "bounded narrative checks need complete audit and v5 source adapters",
        )
        audit = self.values["audit"]
        guided, schema = audit["core"]["guided_repair"], audit["core"]["schema_only"]
        ratio = lambda row, num, den: f"{row[num]}/{row[den]}"
        invalid = ratio(guided, "initial_invalid", "assigned")
        safe = ratio(guided, "unsafe_commits", "assigned")
        recovered = ratio(guided, "repair_successes", "initial_invalid")
        held = ratio(guided, "held", "assigned")
        goal = ratio(guided, "goals", "assigned")
        valid_cases = ratio(guided, "initial_valid", "initial_valid")
        signatures = ratio(guided, "valid_retained_signature_count", "valid_signature_denominator")
        false_rejections = ratio(guided, "false_rejections", "initial_valid")
        graph = f"{audit['graph_agreement']['agreements']}/{audit['graph_agreement']['assigned']}"
        data = self.values["v5"]
        cells = data["cells"]
        luna = [
            cells[("gpt-5.6-luna", condition)]["counts"] for condition in ("detailed", "generic")
        ]
        terra = [
            cells[("gpt-5.6-terra", condition)]["counts"] for condition in ("detailed", "generic")
        ]
        parse_counts = [
            f"{sum(cell['schema'] for cell in model)}/{sum(cell['assigned'] for cell in model)}"
            for model in (luna, terra)
        ]
        semantic = (
            [f"{data['totals']['gate']}/{data['totals']['parsed']}"]
            + [f"{cell['gate']}/{cell['parsed']}" for cell in (luna[0], luna[1], terra[1])]
            + [f"{data['totals']['goal']}/{data['totals']['assigned']}"]
        )
        for language in ("en", "ko"):
            source = f"paper/latex/{language}/main.tex"
            text = (self.root / source).read_text(encoding="utf-8")
            paragraphs = re.split(r"\n\s*\n", text)
            sites = (
                [
                    (
                        "audit-funnel",
                        r"\label{sec:review-boundary-results}",
                        [invalid, safe, recovered, held, goal],
                    ),
                    (
                        "audit-preservation",
                        r"\input{../generated/review_boundary_audit_en.tex}",
                        [valid_cases, signatures, false_rejections, graph],
                    ),
                    (
                        "v5-parser",
                        r"\textbf{Stage 1",
                        [f"{data['totals']['schema']}/{data['totals']['assigned']}", *parse_counts],
                    ),
                    ("v5-semantic", r"\textbf{Stage 2", semantic),
                ]
                if language == "en"
                else [
                    (
                        "audit-funnel",
                        r"\label{sec:review-boundary-results}",
                        [
                            invalid,
                            ratio(guided, "initial_valid", "assigned"),
                            invalid,
                            invalid,
                            safe,
                            recovered,
                            held,
                            safe,
                        ],
                    ),
                    (
                        "audit-preservation",
                        "유도 수리의 유효 커밋",
                        [
                            goal,
                            ratio(schema, "goals", "assigned"),
                            false_rejections,
                            valid_cases,
                            signatures,
                            graph,
                        ],
                    ),
                    (
                        "audit-surface",
                        "본 배정과 구분한",
                        [
                            f"{audit['surface_pairs']['guided_repair']['undeclared_committed']}/{audit['surface_pairs']['guided_repair']['undeclared_assigned']}",
                            f"{audit['surface_pairs']['guided_repair']['declared_held']}/{audit['surface_pairs']['guided_repair']['declared_assigned']}",
                        ],
                    ),
                    ("v5-two-stages", r"\textbf{1단계", [*parse_counts, *semantic[1:]]),
                ]
            )
            for site_id, anchor, expected in sites:
                matches = [paragraph for paragraph in paragraphs if anchor in paragraph]
                if language == "en" and site_id == "audit-preservation":
                    adjacent = text.split(anchor)
                    _require(
                        len(adjacent) == 2,
                        "audit preservation source-materialization boundary is missing/ambiguous",
                    )
                    section = adjacent[0].rsplit(r"\label{sec:review-boundary-results}", 1)
                    _require(len(section) == 2, "audit preservation section anchor is missing")
                    matches = [re.split(r"\n\s*\n", section[1].rstrip())[-1]]
                _require(
                    len(matches) == 1,
                    f"bounded narrative claim site missing/ambiguous: {source}/{site_id}",
                )
                observed = re.findall(r"\d+/\d+", matches[0])
                if site_id == "v5-two-stages":
                    counts = re.search(r"파싱된 후보 (\d+)개 중 (\d+)개", matches[0])
                    _require(
                        counts is not None
                        and tuple(map(int, counts.groups()))
                        == (data["totals"]["parsed"], data["totals"]["gate"]),
                        "Korean v5 parsed/gate count binding drift",
                    )
                self.report["claim_sites"].append(
                    {
                        "source": source,
                        "site": site_id,
                        "binding": "ordered context-keyed numerator/denominator fields",
                        "expected": expected,
                        "observed": observed,
                    }
                )
                _require(
                    observed == expected,
                    f"bounded narrative numerator/denominator drift: {source}/{site_id}: expected {expected}, observed {observed}",
                )
        return "registered EN/KO audit funnel, preservation, surface and v5 two-stage numerator/denominator claim sites bound; arbitrary prose is outside this check"

    def withdrawal(self):
        relative = "research/maintenance/ollama-unverified-history-20261113.json"
        payload = (self.root / relative).read_bytes()
        _require(
            _sha(payload) == "053cc214e3fa5b38f5444ab56205b70dc97230ce668af2e3bc4d3ba36ab7821b",
            "withdrawn Ollama attribution archive digest drift",
        )
        archive = json.loads(payload)
        _require(
            archive["schema_version"] == "withdrawn-historical-attribution/1",
            "withdrawal archive schema drift",
        )
        _require(
            archive["status"] == "UNVERIFIED_HISTORICAL_ATTRIBUTION"
            and archive["disposition"] == "WITHDRAWN_FROM_CURRENT_QUANTITATIVE_EVIDENCE",
            "unverified historical attribution was promoted to current evidence",
        )
        _require(
            archive["original_raw_data_deleted_by_this_change"] is False
            and archive["substitute_receipts_created"] is False
            and archive["model_recollection_performed"] is False,
            "withdrawal must neither delete originals nor manufacture replacement evidence",
        )
        fragments = archive["source_fragments"]
        _require(
            [fragment["language"] for fragment in fragments] == ["en", "ko"],
            "withdrawal archive needs both verbatim manuscript fragments",
        )
        for fragment in fragments:
            language = fragment["language"]
            source = f"paper/latex/{language}/main.tex"
            _require(
                fragment["path"] == source
                and _sha(fragment["text"].encode("utf-8")) == fragment["sha256"],
                "withdrawn verbatim fragment/source digest mismatch",
            )
            _require(
                r"\label{tab:ollama-feasibility}" in fragment["text"],
                "archive lost the withdrawn quantitative table",
            )
            current = "\n".join(self.closures[f"paper-{language}"].values())
            _require(
                "tab:ollama-feasibility" not in current,
                "withdrawn Ollama quantitative table is still reached or referenced",
            )
            _require(
                relative in current,
                "current manuscript omits the inspectable historical withdrawal archive",
            )
            section = current.split(r"\label{app:runtime-ollama-feasibility}", 1)
            _require(len(section) == 2, "Ollama withdrawal limitation section is missing")
            limitation = re.split(r"\\section(?:\*?)\{", section[1], maxsplit=1)[0]
            if language == "en":
                missing = re.search(
                    r"original.{0,100}(?:unavailable|missing|not.{0,25}(?:locat|recover)|could not.{0,25}(?:locat|recover))",
                    limitation,
                    re.IGNORECASE | re.DOTALL,
                )
            else:
                missing = re.search(
                    r"원본.{0,180}(?:없|찾지|복구.{0,20}못|확보.{0,20}못)", limitation, re.DOTALL
                )
            _require(
                missing is not None, f"clear missing-original-receipt limitation absent: {source}"
            )
        self.report["withdrawn_evidence"].append(
            {
                "id": "ollama-feasibility",
                "path": relative,
                "sha256": _sha(payload),
                "status": archive["status"],
                "disposition": archive["disposition"],
                "binding_kind": "historical_attribution_only",
                "quantitative_evidence": False,
            }
        )
        return "verbatim historical attribution integrity and actual current-table withdrawal checked; no original receipt or quantitative result is credited"

    def artifact_sources(self):
        required = (
            "pilot",
            "audit",
            "runtime",
            "disclosure",
            "npc",
            "kg",
            "v5",
            "preserved-statuses",
            "contribution-crosswalk",
            "withdrawn-ollama-attribution",
        )
        _require(
            all(self.family.get(name) == "PASS" for name in required),
            "artifact map requires all named source families and the actual withdrawal to validate",
        )
        facts = {}
        pilot = self.values["pilot"]
        facts.update(
            {
                "validators": len(self.module("nesy_game.validator").VALIDATOR_CHECKS),
                **pilot["gate_conformance"]["raw_counts"],
            }
        )
        arms = {row["arm_id"]: row for row in pilot["repair_arms"]["raw_counts_by_arm"]}
        facts.update(
            arm_count=len(arms),
            repair_cases=arms["guided_repair"]["case_count"],
            reject=arms["rejection_only"]["commit_count"],
            guided=arms["guided_repair"]["commit_count"],
            oracle=arms["structured_repair"]["commit_count"],
        )
        _require(
            arms["unchanged_retry"]["commit_count"] == facts["reject"]
            and all(row["case_count"] == facts["repair_cases"] for row in arms.values()),
            "artifact E1 shared denominator/reject-blind correspondence drift",
        )
        facts.update(
            integrity=pilot["integrity_faults"]["raw_counts"]["fault_count"],
            adapter_records=len(pilot["adapter_accounting"]["records"]),
            guards=pilot["accounting_guards"]["raw_counts"]["guard_count"],
            sentinels=pilot["boundary_sentinels"]["raw_counts"]["sentinel_count"],
        )
        audit = self.values["audit"]
        facts.update(
            audit_main=sum(row["assigned"] for row in audit["core"].values()),
            audit_surface=sum(row["assigned"] for row in audit["surface"].values()),
        )
        live_base = self.root / "research/academic-pipeline/rq2-live-pilot"
        promotion = _json(live_base / "promotion-manifest.json")
        summaries = [
            "frozen-pilot-base/policy_visible/summary.json",
            "frozen-pilot-base/policy_blind/summary.json",
            "frozen-pilot-base/goal_directed_blind/summary.json",
            "signal-repair-v2/policy_visible/summary.json",
            "signal-repair-v2/policy_blind/summary.json",
        ]
        live = [_json(live_base / path) for path in summaries]
        facts.update(
            e2_receipts=len(promotion["files"]),
            seeds=live[0]["counts"]["seeds"],
            repair_budget=live[0]["repair_budget"],
            isolated=sum(
                arm["non_commit_state_isolated"]
                for summary in live
                for arm in summary["per_arm"].values()
            ),
            noncommits=sum(
                arm["non_commits"] for summary in live for arm in summary["per_arm"].values()
            ),
        )
        kg = self.values["kg"]
        facts.update(kg["graph"])
        facts.update(
            queries=kg["budget"]["queries_per_trial"],
            strategies=len(kg["trials"]),
            scores=kg["budget"]["candidate_scores_total"],
            ranking_k=kg["budget"]["ranking_k"],
            winner=kg["winner"]["strategy_id"].split("-", 1)[0],
            violations=kg["ontology_violations"],
        )
        facts.update(
            {
                key: f"{kg['winner']['metrics'][source]:.3f}"
                for key, source in (
                    ("precision", "precision"),
                    ("recall", "recall"),
                    ("mrr", "mrr_realistic"),
                    ("semantic", "semantic_at_k"),
                )
            }
        )
        _require(
            facts["precision"] == facts["recall"], "artifact map P=R shorthand no longer applies"
        )
        game = _json(self.root / "game-track/godot/docs/latest/evaluation-matrix.json")
        totals, presentation = game["totals"], game["presentation"]
        _require(
            len({row["fixture_id"] for row in game["authored_fixtures"]})
            == len(game["authored_fixtures"])
            == totals["fixtures_total"]
            == totals["fixtures_passed"],
            "engine matrix fixture identity/count mismatch",
        )
        _require(
            sum(row["counts"]["checks_total"] for row in game["authored_fixtures"])
            + presentation["counts"]["checks_total"]
            == totals["combined_checks_total"],
            "engine core/presentation check denominator mismatch",
        )
        for counts in [row["counts"] for row in game["authored_fixtures"]] + [
            presentation[key] for key in ("counts", "extension_counts", "all_counts")
        ]:
            _require(
                all(
                    type(counts[key]) is int and counts[key] >= 0
                    for key in ("checks_passed", "checks_total")
                )
                and counts["checks_passed"] <= counts["checks_total"],
                "engine leaf check counts must be bounded nonnegative integers",
            )
        _require(
            all(type(value) is int and value >= 0 for value in totals.values()),
            "engine aggregate counts must be nonnegative integers",
        )
        for key in totals:
            if key.endswith("_passed"):
                _require(
                    totals[key] <= totals[key.removesuffix("_passed") + "_total"],
                    "engine aggregate pass count exceeds denominator",
                )
        for row in game["authored_fixtures"]:
            _require(
                row["passed"] is (row["counts"]["checks_passed"] == row["counts"]["checks_total"]),
                "engine fixture disposition/count mismatch",
            )
            isolation = row["state_isolation"]
            _require(
                isolation["all_required_passed"] is True
                and all(
                    value["passed"] is True
                    for value in isolation.values()
                    if isinstance(value, dict)
                ),
                "engine fixture state-isolation result mismatch",
            )
        _require(
            sum(row["passed"] is True for row in game["authored_fixtures"])
            == totals["fixtures_passed"],
            "engine passed fixture aggregate mismatch",
        )
        for suffix in ("passed", "total"):
            _require(
                sum(row["counts"]["checks_" + suffix] for row in game["authored_fixtures"])
                == totals["fixture_checks_" + suffix],
                "engine fixture check aggregate mismatch",
            )
            _require(
                presentation["counts"]["checks_" + suffix]
                == totals["presentation_checks_" + suffix],
                "engine presentation check aggregate mismatch",
            )
            _require(
                totals["fixture_checks_" + suffix] + totals["presentation_checks_" + suffix]
                == totals["combined_checks_" + suffix],
                "engine core passed/total aggregate mismatch",
            )
            _require(
                presentation["all_counts"]["checks_" + suffix]
                == presentation["counts"]["checks_" + suffix]
                + presentation["extension_counts"]["checks_" + suffix],
                "engine presentation/extension accounting mismatch",
            )
        _require(
            presentation["passed"]
            is (
                presentation["all_counts"]["checks_passed"]
                == presentation["all_counts"]["checks_total"]
            )
            and presentation["state_isolation"]["unchanged"] is True,
            "engine presentation disposition/isolation mismatch",
        )
        extension_ids = presentation["extension_check_ids"]
        _require(
            len(set(extension_ids))
            == len(extension_ids)
            == presentation["extension_counts"]["checks_total"]
            == totals["extension_checks_total"],
            "engine extension inventory/count mismatch",
        )
        _require(
            totals["extension_checks_passed"] == presentation["extension_counts"]["checks_passed"]
            and totals["all_checks_total"]
            == totals["combined_checks_total"] + totals["extension_checks_total"]
            and totals["all_checks_passed"]
            == totals["combined_checks_passed"] + totals["extension_checks_passed"],
            "engine 52 core plus four extension accounting drift",
        )
        balance = _json(self.root / "game-track/godot/docs/latest/balance-archetypes.json")
        facts.update(
            fixtures=totals["fixtures_total"],
            core_pass=totals["combined_checks_passed"],
            core_total=totals["combined_checks_total"],
            extension_pass=totals["extension_checks_passed"],
            extension_total=totals["extension_checks_total"],
            archetypes=balance["aggregates"]["archetype_count"],
            godot_version=game["execution"]["godot_version"].split(".stable", 1)[0],
        )
        smoke_source = (self.root / "game-track/godot/scripts/game3d/game_3d.gd").read_text(
            encoding="utf-8"
        )
        smoke = smoke_source.split("func _run_smoke() -> void:", 1)[1].split("\nfunc ", 1)[0]
        smoke_ids = re.findall(r'"check"\s*:\s*"([^"]+)"', smoke)
        _require(
            smoke_ids
            == [
                "early_secret_refused_without_mutation",
                "early_hint_stage_gated",
                "install_without_lens_refused",
                "lens_acquired",
                "lens_installed_stage_2",
                "authorized_hint_disclosed",
                "presentation_sync_and_fall_recovery",
                "corrupt_save_rejected",
            ],
            "defined smoke predicate inventory drift; definitions are not a retained run",
        )
        facts["smoke_defined"] = len(smoke_ids)
        dev_base = self.root / "research/development-cases/ontology-map-20261023-01"
        dev = _json(dev_base / "contract.json")
        result_path = dev_base / "result.json"
        _require(
            _sha(result_path.read_bytes())
            == "79a104eed9c8433180bb36183003e7a5d3c43afc5d4018bc6cd1e6527309344d",
            "dated development result digest drift",
        )
        result = _json(result_path)
        _require(
            _sha((dev_base / "contract.json").read_bytes()) == result["frozen_contract_sha256"],
            "development result/frozen contract binding drift",
        )
        ontology = _json(self.root / "game-track/web/dashboard/ontology-map.json")
        roles = ontology["roles"]
        _require(
            sorted(role["id"] for role in roles) == sorted(dev["ontology_role_ids"])
            and len({role["id"] for role in roles}) == len(roles),
            "development bilingual map role identity drift",
        )
        for role in roles:
            _require(
                set(role["labels"]) == {"en", "ko"} and all(role["labels"].values()),
                "map role lost its bilingual labels",
            )
        for relative in (
            "research/npc-disclosure/reveal-hint-expectations-v1.json",
            "game-track/godot/data/sealed_lighthouse.json",
        ):
            _require(
                _sha((self.root / relative).read_bytes()) == dev["input_sha256"][relative],
                "development map input source digest mismatch",
            )
        receipt_path = dev_base / result["verification"]["combined_receipt"]
        _require(
            receipt_path.resolve().is_relative_to(dev_base)
            and _sha(receipt_path.read_bytes())
            == "b204e5d676998c4bdc7ec69b18ba625d45422d8cddf93170d323c34cee9812ec",
            "dated development command receipt path/digest drift",
        )
        receipt = _json(receipt_path)
        _require(
            receipt["argv"]
            == result["verification"]["combined_command"]
            == [
                "uv",
                "run",
                "--extra",
                "dev",
                "python",
                "-m",
                "pytest",
                "tests/test_ontology_evidence_map.py",
                "tests/test_signal_explainer.py",
                "tests/test_godot_web_release.py",
                "-q",
            ]
            and receipt["exit_code"] == 0
            and receipt["timed_out"] is False,
            "dated development command/result outcome drift",
        )
        for stream in ("stdout", "stderr"):
            path = receipt_path.parent / receipt[f"{stream}_file"]
            _require(
                path.resolve().is_relative_to(receipt_path.parent)
                and _sha(path.read_bytes()) == receipt[f"{stream}_sha256"],
                "dated development retained stream digest drift",
            )
        stdout = (receipt_path.parent / receipt["stdout_file"]).read_text(encoding="utf-8")
        passed = re.fullmatch(r"\.+\s+\[100%\]\s+(\d+) passed in [0-9.]+s\s*", stdout)
        _require(
            passed is not None
            and int(passed.group(1)) == result["verification"]["observed_tests_passed"]
            and result["verification"]["observed_tests_failed"] == 0,
            "dated development stdout/test accounting drift",
        )
        facts.update(
            roles=len(roles),
            dev_runs=dev["run_count"],
            dev_pass=int(passed.group(1)),
            dev_total=int(passed.group(1)) + result["verification"]["observed_tests_failed"],
            dev_date=receipt["started_at"].split("T", 1)[0],
        )
        npc = self.values["npc"]
        screening_arms = Counter(row["arm"] for row in npc["screening"])
        _require(
            set(screening_arms) == {"P", "R", "O"} and len(set(screening_arms.values())) == 1,
            "NPC screening arm denominators differ",
        )
        facts.update(
            engineering=len(npc["engineering"]),
            screening=len(npc["screening"]),
            screening_arm=screening_arms["P"],
            stale=npc["stale_disclosure"]["verified_rows"],
            npc_pin=NPC_REVISION[:7],
        )
        disclosure = self.values["disclosure"]
        packet = disclosure["packet"]
        disclosure_api = self.module("generate_disclosure_paper_results")
        metrics = disclosure_api._arm_metrics(disclosure["rows"])
        by_arm = {
            arm: {
                row["case_id"]: row["observed"] for row in disclosure["rows"] if row["arm"] == arm
            }
            for arm in ("general_rule", "ontology_gate")
        }
        _require(
            set(by_arm["general_rule"]) == set(by_arm["ontology_gate"]),
            "disclosure paired case identity drift",
        )
        agreement = sum(
            by_arm["general_rule"][key] == by_arm["ontology_gate"][key]
            for key in by_arm["general_rule"]
        )
        facts.update(
            disclosure_cases=len(by_arm["general_rule"]),
            normal=len(packet["normal_cases"]),
            boundary=len(packet["boundary_cases"]),
            malformed=len(packet["malformed_cases"]),
            disclosure_arms=len(metrics),
            agreement=agreement,
            unsafe=metrics["unchecked_isolated"]["unique_unsafe_case_count"],
            rule_fixtures=len(packet["rule_change_fixtures"]),
        )
        runtime = self.values["runtime"]["overall"]
        identity = _json(
            self.root
            / "research/runtime-model-swap-20261024/codex-identity-20261026/public-results-v1/results.json"
        )
        facts.update(
            native_assigned=runtime["assigned"],
            goals=runtime["system_successes"],
            harness=runtime["status_counts"]["technical_failure"],
            timeouts=sum(
                row["failure_reason"] == "response_timeout" for row in self.values["runtime_rows"]
            ),
            host_calls=runtime["host_invocations"],
            native_unsafe=runtime["transitions"]["unsafe_committed"],
            commits=runtime["transitions"]["committed"],
            replays=runtime["replay_valid"]["true"],
            engine_statuses="/".join(
                str(runtime["engine_reexecution_status"][key])
                for key in ("VALID", "INVALID", "NOT_RUN", "NOT_OBSERVED")
            ),
            identity_plan=identity["counters"]["planned"],
            identity_assigned=identity["counters"]["assigned"],
        )
        history_path = (
            self.root
            / "research/codex_feedback_pilot/public-history-20261111/cohort-inventory.json"
        )
        _require(
            _sha(history_path.read_bytes())
            == "88d77a8c20887f2cf18df5fb4de9cfcc24ce193d78d4d7e9cb0b179e333990e2",
            "frozen historical cohort inventory digest drift",
        )
        history = _json(history_path)["rows"]
        _require(
            len({row["cohort"] for row in history}) == len(history),
            "duplicate historical cohort identity",
        )
        for row in history:
            for key in (
                "assigned",
                "completed",
                "failed",
                "IN_PROGRESS",
                "PENDING",
                "gate_accepted",
                "objective_reached",
                "evaluated_candidate_count",
            ):
                _require(
                    type(row[key]) is int and row[key] >= 0,
                    f"malformed historical accounting: {row['cohort']}/{key}",
                )
            _require(
                row["assigned"]
                == sum(row[key] for key in ("completed", "failed", "IN_PROGRESS", "PENDING"))
                and row["gate_accepted"] <= row["evaluated_candidate_count"] <= row["assigned"]
                and row["objective_reached"] <= row["evaluated_candidate_count"],
                "historical accounting invariant drift",
            )
        v5 = self.values["v5"]
        v5_history = [
            row
            for row in history
            if row["cohort"]
            in {"paired-model-comparison-20261110-v5-" + selector for selector in v5["metadata"]}
        ]
        _require(len(v5_history) == len(v5["metadata"]), "v5/history membership mismatch")
        for row in v5_history:
            counts = [
                cell["counts"]
                for (selector, _), cell in v5["cells"].items()
                if selector == row["requested_selector"]
            ]
            _require(
                row["assigned"] == sum(cell["assigned"] for cell in counts)
                and row["gate_accepted"] == sum(cell["gate"] for cell in counts)
                and row["objective_reached"] == sum(cell["goal"] for cell in counts),
                "v5/historical projected outcome mismatch",
            )
        facts.update(
            v5_assigned=v5["totals"]["assigned"],
            v5_fixtures=len({row["case_id"] for row in v5["rows"]}),
            selectors=len(v5["metadata"]),
            v5_gate=v5["totals"]["gate"],
            v5_goals=v5["totals"]["goal"],
            v5_schema=v5["totals"]["schema"],
            source_files=len(next(iter(v5["metadata"].values()))["source_sha256"]),
            history_entries=len(history),
            historical_only=len(history) - len(v5_history),
            v5_entries=len(v5_history),
        )
        prospective_base = self.root / "research/prospective-pilot-20261103"
        summary = _json(prospective_base / "results-v1/summary.json")
        collection = _json(prospective_base / "results-v1/collection-status.json")
        blockers = {reason for row in collection["rows"] for reason in row["blocked_reasons"]}
        facts.update(
            planned=summary["counts"]["planned"],
            completed=summary["counts"]["executed"],
            runtime_plan=summary["tracks"]["runtime"]["planned"],
            development_plan=summary["tracks"]["development"]["planned"],
            blockers=len(blockers),
        )
        crosswalk = self.module("validate_contribution_crosswalk")
        audit = _json(self.root / "research/academic-pipeline/stage-05-citation-verification.json")
        status_counts, _ = crosswalk._validate_citation_audit_totals(audit)
        bibliography = crosswalk._bib_entries(
            (self.root / "paper/latex/references.bib").read_text(encoding="utf-8")
        )
        topic_rows = crosswalk._read_csv(
            self.root / "research/academic-pipeline/reference-topic-crosswalk.csv"
        )
        _require(
            set(bibliography)
            == {row["key"] for row in audit["entries"]}
            == {row["bib_key"] for row in topic_rows},
            "citation audit/bibliography/topic identity drift",
        )
        facts.update(
            references=len(bibliography),
            verified=status_counts["VERIFIED"],
            preprint=status_counts["PREPRINT"],
            dimensions=len(
                _json(self.root / "research/traceability-scoring-20261023/rubric.json")[
                    "dimensions"
                ]
            ),
        )
        schemas = sorted((self.root / "game-track/schemas").glob("*.schema.json"))
        _require(
            bool(schemas)
            and all(
                _json(path)["$schema"].rstrip("#") == "https://json-schema.org/draft/2020-12/schema"
                for path in schemas
            ),
            "bridge schema dialect is not Draft 2020-12",
        )
        facts["audit_main_comma"] = f"{facts['audit_main']:,}"
        facts.update(
            {
                "engine_" + key.lower(): value
                for key, value in runtime["engine_reexecution_status"].items()
            }
        )
        facts.update(zip(("dev_year", "dev_month", "dev_day"), facts["dev_date"].split("-")))
        self.values["artifact_map"] = facts
        return "keyed artifact-map fields derived from validated source families, dated DEV receipt, engine matrix, historical inventory and blocked protocol; static smoke definitions are not executed results"

    def artifact_map(self, table):
        _require(
            self.family.get("artifact-map-sources") == "PASS",
            "artifact map lacks validated typed source facts",
        )
        facts = self.values["artifact_map"]
        language = "ko" if "/ko/" in table["source"] else "en"
        specs = {
            "en": {
                "core": {
                    "label": "C1--C5 Core \\newline Contracts \\& $\\rho$",
                    "paths": [
                        ("src/nesy_game/contracts.py", "src/nesy_game/contracts.py"),
                        ("validator.py", "src/nesy_game/validator.py"),
                        ("repair.py", "src/nesy_game/repair.py"),
                        ("runtime.py", "src/nesy_game/runtime.py"),
                        ("experiment.py", "src/nesy_game/experiment.py"),
                        ("game-track/schemas/*.schema.json", "game-track/schemas/*.schema.json"),
                    ],
                    "cell": "WorldState, ActionPolicy, @validators@ predicate checks "
                    "(VALIDATOR_CHECKS), guided repair $\\rho(a,E)$, state-reading oracle, "
                    "semantic replay \\& SHA-256 chain verifier, Draft 2020-12 bridge/record "
                    "schemas.",
                    "verifier": "scripts/validate_project.py \\newline Sec.~\\ref{sec:arch}, "
                    "Tables~\\ref{tab:validators}--\\ref{tab:rho-rules}, "
                    "Fig.~\\ref{alg:commit}",
                    "verifier_paths": ["scripts/validate_project.py"],
                },
                "e1": {
                    "label": "E1 Offline \\newline Conformance",
                    "paths": [
                        (
                            "research/academic-pipeline/stage-04-pilot/pilot-results.json",
                            "research/academic-pipeline/stage-04-pilot/pilot-results.json",
                        ),
                        (
                            "pilot-assignment-manifest.json",
                            "research/academic-pipeline/stage-04-pilot/pilot-assignment-manifest.json",
                        ),
                        (
                            "sha256-manifest.json",
                            "research/academic-pipeline/stage-04-pilot/sha256-manifest.json",
                        ),
                        ("*.csv", "research/academic-pipeline/stage-04-pilot/*.csv"),
                    ],
                    "cell": "@fixture_count@ gate fixtures (@valid_control_count@ valid, "
                    "@negative_fixture_count@ negative), @repair_cases@ repair cases across "
                    "@arm_count@ arms ($@reject@/@repair_cases@$ reject/blind, "
                    "$@guided@/@repair_cases@$ $\\rho$, $@oracle@/@repair_cases@$ oracle), "
                    "@integrity@ integrity-fault checks, @adapter_records@ adapter terminal "
                    "records, @guards@ manifest guards, @sentinels@ open sentinels.",
                    "verifier": "scripts/run_conformance_pilot.py \\newline Sec.~\\ref{sec:lanes}, "
                    "\\ref{sec:results}, "
                    "Tables~\\ref{tab:pilot-repair}--\\ref{tab:pilot-accounting}",
                    "verifier_paths": ["scripts/run_conformance_pilot.py"],
                },
                "boundary_audit": {
                    "label": "Boundary \\newline Audit",
                    "paths": [
                        (
                            "research/academic-pipeline/gemini-review-20261113/results-v2/",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/",
                        ),
                        (
                            "summary.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/summary.json",
                        ),
                        (
                            "rows.jsonl",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/rows.jsonl",
                        ),
                        (
                            "surface_rows.jsonl",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/surface_rows.jsonl",
                        ),
                        (
                            "assignment_inventory.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/assignment_inventory.json",
                        ),
                        (
                            "input_hashes.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/input_hashes.json",
                        ),
                        (
                            "source_hashes.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/source_hashes.json",
                        ),
                    ],
                    "cell": "@audit_main_comma@ main assignments and @audit_surface@ "
                    "separately denominated surface assignments; bounded authored "
                    "finite-graph audit, frozen inventory, and input/source hashes.",
                    "verifier": "scripts/run_gemini_review_evaluation.py \\newline "
                    "tests/test_gemini_review_publication.py \\newline "
                    "Secs.~\\ref{sec:review-boundary-audit}, "
                    "\\ref{sec:review-boundary-results}",
                    "verifier_paths": [
                        "scripts/run_gemini_review_evaluation.py",
                        "tests/test_gemini_review_publication.py",
                    ],
                },
                "historical_e2": {
                    "label": "E2 Archived \\newline Live Screening",
                    "paths": [
                        (
                            "research/academic-pipeline/rq2-live-pilot/promotion-manifest.json",
                            "research/academic-pipeline/rq2-live-pilot/promotion-manifest.json",
                        ),
                        (
                            "frozen-pilot-base/",
                            "research/academic-pipeline/rq2-live-pilot/frozen-pilot-base/",
                        ),
                        (
                            "signal-repair-v2/",
                            "research/academic-pipeline/rq2-live-pilot/signal-repair-v2/",
                        ),
                    ],
                    "cell": "@e2_receipts@ hash-pinned historical JSON/JSONL receipts "
                    "($@seeds@\\text{ seeds}\\times K{=}@repair_budget@$ paired "
                    "$\\rho$ vs.\\ blind retry, $@isolated@/@noncommits@$ non-commit "
                    "state isolation); excluded from active claims.",
                    "verifier": "scripts/validate_contribution_crosswalk.py \\newline "
                    "Sec.~\\ref{sec:lanes} (Historical only)",
                    "verifier_paths": ["scripts/validate_contribution_crosswalk.py"],
                },
                "e3": {
                    "label": "E3 KG/Ontology \\newline Simulation",
                    "paths": [
                        (
                            "knowledge/ontology/trace-rpg-ontology.json",
                            "knowledge/ontology/trace-rpg-ontology.json",
                        ),
                        ("curated-relations.json", "knowledge/ontology/curated-relations.json"),
                        (
                            "research/simulation/kg-ontology/latest/evaluation-matrix.json",
                            "research/simulation/kg-ontology/latest/evaluation-matrix.json",
                        ),
                    ],
                    "cell": "@nodes@ OKF nodes, @reference_edges@ reference edges, "
                    "@curated_typed_edges@ curated typed edges; @queries@ edge-withheld queries "
                    "$\\times$ @strategies@ fixed strategies (@scores@ scores; S2 "
                    "$P{=}R{=}@precision@$, $\\text{MRR}{=}@mrr@$, "
                    "$\\text{Sem@@ranking_k@}{=}@semantic@$).",
                    "verifier": "scripts/run_kg_ontology_simulation.py \\newline Sec.~\\ref{sec:lanes}, "
                    "Table~\\ref{tab:kg-ontology-simulation}",
                    "verifier_paths": ["scripts/run_kg_ontology_simulation.py"],
                },
                "engine_dev": {
                    "label": "ENG1 \\& \\newline DEV-CASE",
                    "paths": [
                        ("game-track/godot/project.godot", "game-track/godot/project.godot"),
                        (
                            "game-track/godot/docs/latest/evaluation-matrix.json",
                            "game-track/godot/docs/latest/evaluation-matrix.json",
                        ),
                        (
                            "game-track/godot/docs/latest/balance-archetypes.json",
                            "game-track/godot/docs/latest/balance-archetypes.json",
                        ),
                        (
                            "game-track/web/dashboard/ontology-map.json",
                            "game-track/web/dashboard/ontology-map.json",
                        ),
                        (
                            "research/development-cases/ontology-map-20261023-01/",
                            "research/development-cases/ontology-map-20261023-01/",
                        ),
                        (
                            "contract.json",
                            "research/development-cases/ontology-map-20261023-01/contract.json",
                        ),
                        (
                            "result.json",
                            "research/development-cases/ontology-map-20261023-01/result.json",
                        ),
                        (
                            "evidence/verification-009-mobile-complete-tests.json",
                            "research/development-cases/ontology-map-20261023-01/evidence/verification-009-mobile-complete-tests.json",
                        ),
                    ],
                    "cell": "Retained matrix: @fixtures@ fixtures, @core_pass@/@core_total@ "
                    "core and separate @extension_pass@/@extension_total@ extension "
                    "checks; @archetypes@ archetypes. Eight defined smoke predicates "
                    "are a contract, not a stored run-pass result. Bilingual "
                    "@roles@-role map; $n{=}@dev_runs@$ development case with dated "
                    "@dev_pass@/@dev_total@ test receipt.",
                    "verifier": "scripts/validate_game_track.sh; "
                    "tests/test_godot_experimental_game.py \\newline "
                    "Sec.~\\ref{sec:results}--\\ref{sec:development-case}, "
                    "Table~\\ref{tab:ontology-roles}",
                    "verifier_paths": [
                        "scripts/validate_game_track.sh",
                        "tests/test_godot_experimental_game.py",
                    ],
                },
                "npc": {
                    "label": "NPC-ENG1 \\& \\newline NPC-SCR1",
                    "paths": [
                        (
                            "configs/npc-goal-recovery.json",
                            "npc-source:configs/npc-goal-recovery.json",
                        ),
                        (
                            "research/academic-pipeline/npc-goal-recovery/verified-run-006/aggregate.json",
                            "research/academic-pipeline/npc-goal-recovery/verified-run-006/aggregate.json",
                        ),
                        (
                            "*-results.jsonl",
                            "research/academic-pipeline/npc-goal-recovery/verified-run-006/*-results.jsonl",
                        ),
                    ],
                    "cell": "@engineering@ deterministic NPC-ENG1 cases and @screening@ NPC-SCR1 rows "
                    "($P/R/O{=}@screening_arm@$ each), @stale@ stale-control ACK rejections "
                    "(SCR-T01/T02), epoch-local replay, and pinned fa9fb8a provenance hashes.",
                    "verifier": "scripts/validate_npc_goal_evidence.py \\newline "
                    "Sec.~\\ref{sec:lanes}, \\ref{sec:results}, "
                    "Table~\\ref{tab:npc-screening}",
                    "verifier_paths": ["scripts/validate_npc_goal_evidence.py"],
                },
                "disclosure": {
                    "label": "NPC-DISC-1 \\newline Disclosure Gate",
                    "paths": [
                        ("src/nesy_game/disclosure.py", "src/nesy_game/disclosure.py"),
                        (
                            "research/npc-disclosure/reveal-hint-expectations-v1.json",
                            "research/npc-disclosure/reveal-hint-expectations-v1.json",
                        ),
                        (
                            "results-signal-explainer-20261023-r5/",
                            "research/npc-disclosure/results-signal-explainer-20261023-r5/",
                        ),
                    ],
                    "cell": "@disclosure_cases@ declaration-derived reveal_hint cases "
                    "($@normal@\\text{ normal}/@boundary@\\text{ "
                    "boundary}/@malformed@\\text{ malformed}$) across @disclosure_arms@ "
                    "arms ($@agreement@/@disclosure_cases@$ general_rule vs.\\ "
                    "ontology_gate parity; @unsafe@ unsafe in unchecked arm) and "
                    "@rule_fixtures@ rule-change fixtures.",
                    "verifier": "scripts/generate_disclosure_paper_results.py \\newline "
                    "Sec.~\\ref{sec:disclosure-contract}, \\ref{sec:results}, "
                    "Tables~\\ref{tab:disclosure-contract}--\\ref{tab:disclosure-fixtures}, "
                    "Fig.~\\ref{fig:disclosure-signals}",
                    "verifier_paths": ["scripts/generate_disclosure_paper_results.py"],
                },
                "native_identity": {
                    "label": "Native Pilot \\& \\newline ID Extension",
                    "paths": [
                        (
                            "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                            "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                        ),
                        (
                            "codex-identity-20261026/public-results-v1/results.json",
                            "research/runtime-model-swap-20261024/codex-identity-20261026/public-results-v1/results.json",
                        ),
                    ],
                    "cell": "@native_assigned@ assigned fixed-game rows "
                    "(@goals@/@native_assigned@ goals, @harness@ harness fault, "
                    "@timeouts@ timeouts, @host_calls@ host calls, "
                    "@native_unsafe@/@commits@ unsafe, @replays@ semantic replays, "
                    "$@engine_valid@/@engine_invalid@/@engine_not_run@/@engine_not_observed@$ "
                    "fresh-engine); plus planned @identity_plan@-row identity "
                    "extension stopped at Row @identity_assigned@ "
                    "(IDENTITY_UNVERIFIED).",
                    "verifier": "scripts/generate_runtime_comparison_publication.py "
                    "\\newline Sec.~\\ref{sec:results}, "
                    "Table~\\ref{tab:runtime-comparison-aggregate}, "
                    "App.~\\ref{app:runtime-evidence}--\\ref{app:runtime-identity}",
                    "verifier_paths": ["scripts/generate_runtime_comparison_publication.py"],
                },
                "v5_history": {
                    "label": "v5 Feedback \\& \\newline Cohort History",
                    "paths": [
                        (
                            "research/codex_feedback_pilot/public-v5/",
                            "research/codex_feedback_pilot/public-v5/",
                        ),
                        (
                            "paired-model-comparison-20261110-v5-source.zip",
                            "research/codex_feedback_pilot/paired-model-comparison-20261110-v5-source.zip",
                        ),
                        (
                            "public-history-20261111/cohort-inventory.json",
                            "research/codex_feedback_pilot/public-history-20261111/cohort-inventory.json",
                        ),
                    ],
                    "cell": "@v5_assigned@ v5 assignments (@v5_fixtures@ fixtures $\\times$ "
                    "@selectors@ selectors $\\times$ Detailed/Generic; @v5_gate@ gate "
                    "pass, @v5_goals@ goal, @v5_schema@ schema fail), prompt/response "
                    "SHA-256 digests, @source_files@ frozen source files, and "
                    "@history_entries@-cohort historical inventory.",
                    "verifier": "tests/test_codex_feedback_publication.py \\newline "
                    "Sec.~\\ref{sec:results}, Table~\\ref{tab:paired-feedback-v5}, "
                    "Figs.~\\ref{fig:state-signal}--\\ref{fig:paired-feedback-flow}, "
                    "App.~\\ref{app:diagnostic-blocked}",
                    "verifier_paths": ["tests/test_codex_feedback_publication.py"],
                },
                "withdrawn_prospective": {
                    "label": "Withdrawn History \\& \\newline Blocked Pilot",
                    "paths": [
                        (
                            "research/maintenance/ollama-unverified-history-20261113.json",
                            "research/maintenance/ollama-unverified-history-20261113.json",
                        ),
                        (
                            "research/prospective-pilot-20261103/protocol-v1.json",
                            "research/prospective-pilot-20261103/protocol-v1.json",
                        ),
                        (
                            "research/prospective-pilot-20261103/results-v1/collection-status.json",
                            "research/prospective-pilot-20261103/results-v1/collection-status.json",
                        ),
                        (
                            "summary.json",
                            "research/prospective-pilot-20261103/results-v1/summary.json",
                        ),
                    ],
                    "cell": "Ollama attribution withdrawn: original receipts "
                    "unavailable; historical JSON is not validated "
                    "experimental data. Separate prospective plan: "
                    "@completed@/@planned@ completed ($@runtime_plan@\\text{ "
                    "runtime}/@development_plan@\\text{ dev}$ planned), "
                    "@blockers@ fail-closed blockers (NOT_RUN/BLOCKED).",
                    "verifier": "scripts/run_prospective_pilot.py \\newline "
                    "App.~\\ref{app:runtime-ollama-feasibility}--\\ref{app:diagnostic-blocked}",
                    "verifier_paths": ["scripts/run_prospective_pilot.py"],
                },
                "crosswalk": {
                    "label": "Crosswalk \\& \\newline Manifests",
                    "paths": [
                        (
                            "research/academic-pipeline/*-matrix.csv",
                            "research/academic-pipeline/*-matrix.csv",
                        ),
                        (
                            "stage-05-citation-verification.json",
                            "research/academic-pipeline/stage-05-citation-verification.json",
                        ),
                        ("visuals/source-manifest.json", "visuals/source-manifest.json"),
                        (
                            "research/traceability-scoring-20261023/rubric.json",
                            "research/traceability-scoring-20261023/rubric.json",
                        ),
                    ],
                    "cell": "@references@-reference topic/status crosswalk (@verified@ verified, "
                    "@preprint@ preprint), C1--C5 \\& E1--ENG1 claim-boundary matrices, "
                    "visual/table SHA-256 source manifest, and @dimensions@-dimension "
                    "traceability rubric (TR01--TR06).",
                    "verifier": "scripts/validate_visual_assets.py \\newline "
                    "Table~\\ref{tab:contribution-map}, "
                    "Table~\\ref{tab:evidence-lanes}, Supplement",
                    "verifier_paths": ["scripts/validate_visual_assets.py"],
                },
            },
            "ko": {
                "core": {
                    "label": "C1--C5 핵심 \\newline 계약 및 $\\rho$",
                    "paths": [
                        ("src/nesy_game/contracts.py", "src/nesy_game/contracts.py"),
                        ("validator.py", "src/nesy_game/validator.py"),
                        ("repair.py", "src/nesy_game/repair.py"),
                        ("runtime.py", "src/nesy_game/runtime.py"),
                        ("experiment.py", "src/nesy_game/experiment.py"),
                        ("game-track/schemas/*.schema.json", "game-track/schemas/*.schema.json"),
                    ],
                    "cell": "WorldState, ActionPolicy, @validators@개 결정론적 검사(VALIDATOR_CHECKS), 반례 유도 "
                    "수리 $\\rho(a,E)$, 상태 판독 oracle, 의미적 리플레이·SHA-256 체인 검증기, Draft 2020-12 "
                    "브리지·레코드 스키마.",
                    "verifier": "scripts/validate_project.py \\newline 4장, "
                    "표~\\ref{tab:validators}--\\ref{tab:rho-rules}, 그림~\\ref{alg:commit}",
                    "verifier_paths": ["scripts/validate_project.py"],
                },
                "e1": {
                    "label": "E1 오프라인 \\newline 적합성 설계",
                    "paths": [
                        (
                            "research/academic-pipeline/stage-04-pilot/pilot-results.json",
                            "research/academic-pipeline/stage-04-pilot/pilot-results.json",
                        ),
                        (
                            "pilot-assignment-manifest.json",
                            "research/academic-pipeline/stage-04-pilot/pilot-assignment-manifest.json",
                        ),
                        (
                            "sha256-manifest.json",
                            "research/academic-pipeline/stage-04-pilot/sha256-manifest.json",
                        ),
                        ("*.csv", "research/academic-pipeline/stage-04-pilot/*.csv"),
                    ],
                    "cell": "게이트 픽스처 @fixture_count@개(유효 @valid_control_count@, 음성 "
                    "@negative_fixture_count@), @arm_count@개 수리 arm별 @repair_cases@개 "
                    "사례($@reject@/@repair_cases@$ 거부/블라인드, $@guided@/@repair_cases@$ $\\rho$, "
                    "$@oracle@/@repair_cases@$ oracle), 무결성 결함 @integrity@개, 어댑터 종단 기록 "
                    "@adapter_records@개, 매니페스트 가드 @guards@개, 경계 센티널 @sentinels@개.",
                    "verifier": "scripts/run_conformance_pilot.py \\newline 5--6장, "
                    "표~\\ref{tab:pilot-repair}--\\ref{tab:pilot-accounting}",
                    "verifier_paths": ["scripts/run_conformance_pilot.py"],
                },
                "boundary_audit": {
                    "label": "신규 한정 \\newline 오프라인 감사",
                    "paths": [
                        (
                            "research/academic-pipeline/gemini-review-20261113/results-v2/",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/",
                        ),
                        (
                            "summary.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/summary.json",
                        ),
                        (
                            "rows.jsonl",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/rows.jsonl",
                        ),
                        (
                            "surface_rows.jsonl",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/surface_rows.jsonl",
                        ),
                        (
                            "assignment_inventory.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/assignment_inventory.json",
                        ),
                        (
                            "input_hashes.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/input_hashes.json",
                        ),
                        (
                            "source_hashes.json",
                            "research/academic-pipeline/gemini-review-20261113/results-v2/source_hashes.json",
                        ),
                    ],
                    "cell": "본 배정 @audit_main_comma@개와 별도 표면 배정 @audit_surface@개를 구분한 저작된 "
                    "유한 감사. 동결 입력·배정 목록·입력/소스 해시와 행별 결과를 보존하며 모델·사람 효능 자료가 아니다.",
                    "verifier": "scripts/run_gemini_review_evaluation.py \\newline "
                    "tests/test_gemini_review_publication.py \\newline "
                    "\\ref{sec:review-boundary-audit}--\\ref{sec:review-boundary-results}절",
                    "verifier_paths": [
                        "scripts/run_gemini_review_evaluation.py",
                        "tests/test_gemini_review_publication.py",
                    ],
                },
                "historical_e2": {
                    "label": "E2 보관된 \\newline 라이브 스크리닝",
                    "paths": [
                        (
                            "research/academic-pipeline/rq2-live-pilot/promotion-manifest.json",
                            "research/academic-pipeline/rq2-live-pilot/promotion-manifest.json",
                        ),
                        (
                            "frozen-pilot-base/",
                            "research/academic-pipeline/rq2-live-pilot/frozen-pilot-base/",
                        ),
                        (
                            "signal-repair-v2/",
                            "research/academic-pipeline/rq2-live-pilot/signal-repair-v2/",
                        ),
                    ],
                    "cell": "해시 결속된 과거 JSON/JSONL 영수증 @e2_receipts@개($@seeds@\\text{ "
                    "seed}\\times K{=}@repair_budget@$ 대응 $\\rho$ vs.\\ 블라인드 재시도, "
                    "비커밋 상태 격리 $@isolated@/@noncommits@$); 활성 주장 및 집계에서 제외된 "
                    "provenance 자료.",
                    "verifier": "scripts/validate_contribution_crosswalk.py \\newline 5장 "
                    "(Historical 전용)",
                    "verifier_paths": ["scripts/validate_contribution_crosswalk.py"],
                },
                "e3": {
                    "label": "E3 KG/온톨로지 \\newline 링크 시뮬레이션",
                    "paths": [
                        (
                            "knowledge/ontology/trace-rpg-ontology.json",
                            "knowledge/ontology/trace-rpg-ontology.json",
                        ),
                        ("curated-relations.json", "knowledge/ontology/curated-relations.json"),
                        (
                            "research/simulation/kg-ontology/latest/evaluation-matrix.json",
                            "research/simulation/kg-ontology/latest/evaluation-matrix.json",
                        ),
                    ],
                    "cell": "OKF 노드 @nodes@개, 참조 엣지 @reference_edges@개, 큐레이션 타입 엣지 "
                    "@curated_typed_edges@개; 엣지 은닉 질의 @queries@개 $\\times$ 고정 전략 "
                    "@strategies@종(@scores@개 점수; S2 $P{=}R{=}@precision@$, "
                    "$\\text{MRR}{=}@mrr@$, $\\text{Sem@@ranking_k@}{=}@semantic@$, 온톨로지 위반 "
                    "@violations@건).",
                    "verifier": "scripts/run_kg_ontology_simulation.py \\newline 5장, "
                    "표~\\ref{tab:kg-ontology-simulation}",
                    "verifier_paths": ["scripts/run_kg_ontology_simulation.py"],
                },
                "engine_dev": {
                    "label": "ENG1 및 \\newline DEV-CASE",
                    "paths": [
                        ("game-track/godot/project.godot", "game-track/godot/project.godot"),
                        (
                            "game-track/godot/docs/latest/evaluation-matrix.json",
                            "game-track/godot/docs/latest/evaluation-matrix.json",
                        ),
                        (
                            "game-track/godot/docs/latest/balance-archetypes.json",
                            "game-track/godot/docs/latest/balance-archetypes.json",
                        ),
                        (
                            "game-track/web/dashboard/ontology-map.json",
                            "game-track/web/dashboard/ontology-map.json",
                        ),
                        (
                            "research/development-cases/ontology-map-20261023-01/contract.json",
                            "research/development-cases/ontology-map-20261023-01/contract.json",
                        ),
                        (
                            "research/development-cases/ontology-map-20261023-01/evidence/verification-009-mobile-complete-tests.json",
                            "research/development-cases/ontology-map-20261023-01/evidence/verification-009-mobile-complete-tests.json",
                        ),
                    ],
                    "cell": "저장된 Godot @godot_version@ 슬라이스(sealed_lighthouse.json) 행렬의 픽스처 "
                    "@fixtures@/@fixtures@, 코어 @core_pass@/@core_total@와 별도 확장 "
                    "@extension_pass@/@extension_total@, 아키타입 @archetypes@종; 한·영 "
                    "@roles@역할 온톨로지 맵 및 $n{=}@dev_runs@$ Codex 대시보드 계약과 보관된 "
                    "@dev_year@-@dev_month@-@dev_day@ 명령의 @dev_pass@/@dev_total@ 결과. "
                    "Smoke 검사는 정의된 계약이며 보존 실행 영수증에 결속되지 않은 통과율은 주장하지 않는다.",
                    "verifier": "scripts/validate_game_track.sh \\newline 6장, "
                    "표~\\ref{tab:ontology-roles}",
                    "verifier_paths": ["scripts/validate_game_track.sh"],
                },
                "npc": {
                    "label": "NPC-ENG1 및 \\newline NPC-SCR1",
                    "paths": [
                        (
                            "configs/npc-goal-recovery.json",
                            "npc-source:configs/npc-goal-recovery.json",
                        ),
                        (
                            "research/academic-pipeline/npc-goal-recovery/verified-run-006/aggregate.json",
                            "research/academic-pipeline/npc-goal-recovery/verified-run-006/aggregate.json",
                        ),
                        (
                            "*-results.jsonl",
                            "research/academic-pipeline/npc-goal-recovery/verified-run-006/*-results.jsonl",
                        ),
                    ],
                    "cell": "결정론적 NPC-ENG1 @engineering@례 및 NPC-SCR1 @screening@행($P/R/O$ 각 "
                    "@screening_arm@행), 사전 작성 stale-control ACK 거부 @stale@건(SCR-T01/T02), "
                    "epoch 내부 리플레이, 고정 커밋(fa9fb8a) 해시 매니페스트.",
                    "verifier": "scripts/validate_npc_goal_evidence.py \\newline 5--6장, "
                    "표~\\ref{tab:npc-screening}",
                    "verifier_paths": ["scripts/validate_npc_goal_evidence.py"],
                },
                "disclosure": {
                    "label": "NPC-DISC-1 \\newline 공개 계약 게이트",
                    "paths": [
                        ("src/nesy_game/disclosure.py", "src/nesy_game/disclosure.py"),
                        (
                            "research/npc-disclosure/reveal-hint-expectations-v1.json",
                            "research/npc-disclosure/reveal-hint-expectations-v1.json",
                        ),
                        (
                            "results-signal-explainer-20261023-r5/",
                            "research/npc-disclosure/results-signal-explainer-20261023-r5/",
                        ),
                    ],
                    "cell": "선언 유도형 reveal_hint @disclosure_cases@례(정상 @normal@/경계 "
                    "@boundary@/오류 @malformed@)의 @disclosure_arms@개 arm 비교(general_rule "
                    "vs.\\ ontology_gate $@agreement@/@disclosure_cases@$ 일치, 무검사군 위험 "
                    "사례 @unsafe@건) 및 규칙 변경 픽스처 @rule_fixtures@종(RC-001/002).",
                    "verifier": "scripts/generate_disclosure_paper_results.py \\newline 4.2.1절, "
                    "6장, "
                    "표~\\ref{tab:disclosure-contract}--\\ref{tab:disclosure-fixtures}, "
                    "그림~\\ref{fig:disclosure-signals}",
                    "verifier_paths": ["scripts/generate_disclosure_paper_results.py"],
                },
                "native_identity": {
                    "label": "Native 비교 및 \\newline 신원 확장",
                    "paths": [
                        (
                            "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                            "research/runtime-model-swap-20261024/codex-live-20261026/public-results-v1/results.json",
                        ),
                        (
                            "codex-identity-20261026/public-results-v1/results.json",
                            "research/runtime-model-swap-20261024/codex-identity-20261026/public-results-v1/results.json",
                        ),
                    ],
                    "cell": "고정 게임 @native_assigned@행(목표 @goals@/@native_assigned@, 직렬화 실패 "
                    "@harness@, timeout @timeouts@, host 호출 @host_calls@, unsafe "
                    "@native_unsafe@/@commits@, 의미 리플레이 @replays@, 새 엔진 "
                    "$@engine_valid@/@engine_invalid@/@engine_not_run@/@engine_not_observed@$); "
                    "@identity_plan@행 계획 신원 확장 @identity_assigned@행 "
                    "중단(IDENTITY_UNVERIFIED).",
                    "verifier": "scripts/generate_runtime_comparison_publication.py "
                    "\\newline 6장, 표~\\ref{tab:runtime-comparison-aggregate}, "
                    "부록~\\ref{app:runtime-evidence}--\\ref{app:runtime-identity}",
                    "verifier_paths": ["scripts/generate_runtime_comparison_publication.py"],
                },
                "v5_history": {
                    "label": "v5 피드백 수집 \\newline 및 코호트 이력",
                    "paths": [
                        (
                            "research/codex_feedback_pilot/public-v5/",
                            "research/codex_feedback_pilot/public-v5/",
                        ),
                        (
                            "paired-model-comparison-20261110-v5-source.zip",
                            "research/codex_feedback_pilot/paired-model-comparison-20261110-v5-source.zip",
                        ),
                        (
                            "public-history-20261111/cohort-inventory.json",
                            "research/codex_feedback_pilot/public-history-20261111/cohort-inventory.json",
                        ),
                    ],
                    "cell": "합성 픽스처 @v5_fixtures@종 $\\times$ @selectors@ selector $\\times$ "
                    "상세/일반 신호 @v5_assigned@행(게이트 통과 @v5_gate@, 목표 달성 @v5_goals@, 스키마 실패 "
                    "@v5_schema@), 프롬프트/응답 SHA-256, 실행 소스 @source_files@개 압축본 및 총 "
                    "@history_entries@개 코호트 인벤토리(과거 @historical_only@개, v5 "
                    "@v5_entries@개).",
                    "verifier": "tests/test_codex_feedback_publication.py \\newline 6장, "
                    "표~\\ref{tab:paired-feedback-v5}, "
                    "그림~\\ref{fig:state-signal}--\\ref{fig:paired-feedback-flow}, "
                    "부록~\\ref{app:diagnostic-blocked}",
                    "verifier_paths": ["tests/test_codex_feedback_publication.py"],
                },
                "withdrawn_prospective": {
                    "label": "철회된 Ollama 귀속 및 \\newline 차단 전향 파일럿",
                    "paths": [
                        (
                            "research/maintenance/ollama-unverified-history-20261113.json",
                            "research/maintenance/ollama-unverified-history-20261113.json",
                        ),
                        (
                            "research/prospective-pilot-20261103/protocol-v1.json",
                            "research/prospective-pilot-20261103/protocol-v1.json",
                        ),
                        (
                            "research/prospective-pilot-20261103/results-v1/collection-status.json",
                            "research/prospective-pilot-20261103/results-v1/collection-status.json",
                        ),
                        (
                            "research/prospective-pilot-20261103/results-v1/summary.json",
                            "research/prospective-pilot-20261103/results-v1/summary.json",
                        ),
                    ],
                    "cell": "Ollama 정량 주장은 원본 부재로 철회한 미검증 역사 귀속이며 원자료·검증 결과가 아니다. "
                    "별도의 실제 전향 기록은 @planned@단위 계획(런타임 @runtime_plan@/개발 "
                    "@development_plan@), 실행 @completed@/@planned@ 및 "
                    "@blockers@개 선결 차단 게이트(NOT_RUN/BLOCKED)를 보존한다.",
                    "verifier": "scripts/run_prospective_pilot.py \\newline "
                    "부록~\\ref{app:runtime-ollama-feasibility}--\\ref{app:diagnostic-blocked}",
                    "verifier_paths": ["scripts/run_prospective_pilot.py"],
                },
                "crosswalk": {
                    "label": "교차검증 및 \\newline 시각 매니페스트",
                    "paths": [
                        (
                            "research/academic-pipeline/*-matrix.csv",
                            "research/academic-pipeline/*-matrix.csv",
                        ),
                        (
                            "stage-05-citation-verification.json",
                            "research/academic-pipeline/stage-05-citation-verification.json",
                        ),
                        ("visuals/source-manifest.json", "visuals/source-manifest.json"),
                        (
                            "research/traceability-scoring-20261023/rubric.json",
                            "research/traceability-scoring-20261023/rubric.json",
                        ),
                    ],
                    "cell": "참고문헌 @references@편 주제·상태 교차표(검증 @verified@, 프리프린트 @preprint@), "
                    "기여·실험 주장 경계 매트릭스, 시각·표 산출물의 SHA-256 매니페스트, 미측정 @dimensions@차원 추적성 "
                    "루브릭(TR01--TR06).",
                    "verifier": "scripts/validate_visual_assets.py \\newline "
                    "표~\\ref{tab:contribution-map}, 표~\\ref{tab:evidence-lanes}, "
                    "보충자료",
                    "verifier_paths": ["scripts/validate_visual_assets.py"],
                },
            },
        }[language]
        body = table["_block"].split(r"\midrule", 1)[1].split(r"\bottomrule", 1)[0]
        rows = [
            row.strip().split(" & ")
            for row in re.split(r"\\\\(?:\[[^\]]*\])?", body)
            if row.strip()
        ]
        _require(
            all(len(row) == 4 for row in rows), "artifact map needs four typed columns per lane"
        )
        labels = {spec["label"]: key for key, spec in specs.items()}
        observed = [_plain(row[0]) for row in rows]
        _require(
            len(set(observed)) == len(observed) and set(observed) == set(labels),
            "artifact map has a duplicate, missing or unbound lane",
        )
        closure = "\n".join(self.closures[table["surface_id"]].values())
        anchors = set(re.findall(r"\\label\s*\{([^{}]+)\}", closure))
        bindings, receipts = [], {}
        for row in rows:
            key = labels[_plain(row[0])]
            spec = specs[key]
            tokens = re.findall(r"\\path\{([^{}]+)\}", row[1])
            _require(
                tokens == [token for token, _ in spec["paths"]],
                f"artifact lane/source-path correspondence drift: {key}",
            )
            resolved_paths = []
            for token, relative in spec["paths"]:
                historical = relative.startswith("npc-source:")
                base = self.npc_root if historical else self.root
                _require(base is not None, "artifact historical source base is unavailable")
                relative = relative.removeprefix("npc-source:")
                matches = sorted(base.glob(relative)) if "*" in relative else [base / relative]
                _require(bool(matches), f"artifact wildcard has no source matches: {key}/{token}")
                for path in matches:
                    _require(
                        path.exists() and path.resolve().is_relative_to(base),
                        f"artifact source missing/outside selected root: {key}/{relative}",
                    )
                    _require(
                        not any(
                            parent.is_symlink()
                            for parent in (path, *path.parents)
                            if parent.is_relative_to(base)
                        ),
                        f"artifact source symlink is not accepted: {relative}",
                    )
                    resolved = (f"npc-source@{NPC_REVISION}:" if historical else "") + str(
                        path.relative_to(base)
                    )
                    resolved_paths.append(resolved)
                    if path.is_file():
                        receipts[resolved] = {"path": resolved, "sha256": _sha(path.read_bytes())}
            expected = re.sub(
                r"@([a-z][a-z0-9_]*?)@", lambda match: str(facts[match[1]]), spec["cell"]
            )
            _require(
                _plain(row[2]) == expected,
                f"artifact keyed quantitative/scope cell drift: {key}; expected {expected!r}, observed {_plain(row[2])!r}",
            )
            _require(
                _plain(row[3]) == spec["verifier"]
                and re.findall(r"\\path\{([^{}]+)\}", row[3]) == spec["verifier_paths"],
                f"artifact verifier/reference cell drift: {key}",
            )
            for relative in spec["verifier_paths"]:
                path = self.root / relative
                _require(
                    path.is_file() and path.resolve().is_relative_to(self.root),
                    f"artifact verifier is not supplied by selected root: {relative}",
                )
                receipts[relative] = {"path": relative, "sha256": _sha(path.read_bytes())}
            _require(
                set(re.findall(r"\\ref\{([^{}]+)\}", row[3])).issubset(anchors),
                f"artifact reference does not target reached publication closure: {key}",
            )
            fields = set(re.findall(r"@([a-z][a-z0-9_]*?)@", spec["cell"]))
            bindings.append(
                {
                    "lane": key,
                    "column": 3,
                    "fields": {field: facts[field] for field in sorted(fields)},
                    "resolved_sources": resolved_paths,
                    "expected_cell": expected,
                }
            )
        table["source_receipts"] = list(receipts.values())
        return "artifact-map-sources", "typed_source_cells", bindings

    def manual(self, table):
        anchor = table["anchor"]
        rows = _rows(table["_block"])
        korean = "/ko/" in table["source"]
        if anchor == "tab:paired-feedback-v5":
            data = self.values["v5"]
            expected = []
            for selector in ("gpt-5.6-luna", "gpt-5.6-terra"):
                for condition in ("detailed", "generic"):
                    counts = data["cells"][(selector, condition)]["counts"]
                    label = (
                        {"detailed": "상세", "generic": "일반"}[condition]
                        if korean
                        else condition.title()
                    )
                    expected.append(
                        [selector, label]
                        + [
                            f"{counts[key]}/{counts['assigned']}"
                            for key in ("received", "gate", "goal", "schema")
                        ]
                    )
            _require(
                rows == expected,
                f"v5 keyed model/condition/metric cells mismatch: expected {expected}, observed {rows}",
            )
            return "v5", "empirical_source", expected
        if anchor == "tab:validators":
            checks = self.module("nesy_game.validator").VALIDATOR_CHECKS
            names = [
                "Action policy",
                "Precondition",
                "Reachability",
                "NPC knowledge",
                "Disclosure",
                "Quest stage (quest_stage)",
                "Quest-stage monotonicity (quest_stage_monotonicity)",
            ]
            _require(
                tuple(checks)
                == (
                    "action_policy",
                    "precondition",
                    "object_reachability",
                    "npc_knowledge",
                    "forbidden_disclosure",
                    "quest_stage",
                    "quest_stage_monotonicity",
                ),
                "validator source predicate inventory drift",
            )
            expected_rejects = (
                [
                    "알 수 없는 action/type; policy-required preconditions/effects 누락; 비허용 effects 또는 비인가 quest-stage effects",
                    "누락/거짓 requirement",
                    "접근 불가 object",
                    "사용·공개 사실이 행위자의 지식 집합에 없음",
                    "forbidden fact",
                    "required stage가 current stage보다 높음",
                    "regressive stage",
                ]
                if korean
                else [
                    "unknown action/type; omitted required preconditions/effects; disallowed effects or unauthorized quest-stage effects",
                    "absent/false requirement",
                    "inaccessible object",
                    "used/disclosed fact absent from actor knowledge",
                    "forbidden fact",
                    "required stage above current",
                    "regressive stage",
                ]
            )
            _require(
                all(len(row) == 3 for row in rows) and [row[1] for row in rows] == expected_rejects,
                "validator predicate/rejection correspondence drift",
            )
            _require(
                [row[0] for row in rows] == names
                and all(
                    len(row) == 3 and row[2] == ("변경 없음" if korean else "unchanged")
                    for row in rows
                ),
                "validator keyed predicate/failure-state design contract mismatch",
            )
            _require(
                not any(re.search(r"\d", row[1]) for row in rows),
                "unbound quantitative validator cell",
            )
            return (
                "design-contracts",
                "design_contract",
                {"validator_ids": list(checks), "failure_state": "unchanged"},
            )
        if anchor == "tab:rho-rules":
            repair = self.module("nesy_game.repair")
            expected_codes = {
                "POLICY_PRECONDITION_OMISSION",
                "POLICY_EFFECT_OMISSION",
                "POLICY_EFFECT_VIOLATION",
                "UNSATISFIED_PRECONDITION",
                "POLICY_QUEST_STAGE_EFFECT_VIOLATION",
            }
            _require(
                repair.GUIDED_REPAIRABLE_CODES == expected_codes,
                "guided repair source classes drift",
            )
            expected = (
                [
                    ["정책 precondition 누락", "명명된 predicate 삽입"],
                    ["정책 effect 누락", "명명된 effect 삽입"],
                    ["정책 effect 위반", "명명된 effect 제거"],
                    ["불충족 precondition", "명명된 predicate 제거"],
                    ["비인가 stage 변이", "quest_stage_effect 초기화"],
                    ["알 수 없는 action type", "no-op (등록된 대안 없음)"],
                    [
                        "도달 불가 object; knowledge, disclosure, stage class",
                        "no-op (후보 국소 edit은 세탁이거나 상태 지식 필요)",
                    ],
                ]
                if korean
                else [
                    ["Policy precondition omission", "insert the named predicate"],
                    ["Policy effect omission", "insert the named effect"],
                    ["Policy effect violation", "drop the named effect"],
                    ["Unsatisfied precondition", "drop the named predicate"],
                    ["Unauthorized stage mutation", "clear quest_stage_effect"],
                    ["Unknown action type", "no-op (no registered alternative)"],
                    [
                        "Unreachable object; knowledge, disclosure, and stage classes",
                        "no-op (candidate edit would launder or needs state)",
                    ],
                ]
            )
            _require(rows == expected, "rho keyed error/edit contract mismatch")
            return (
                "design-contracts",
                "design_contract",
                {"repairable_codes": sorted(expected_codes), "rows": expected},
            )
        if anchor == "tab:ontology-roles":
            scenario = _json(self.root / "game-track/godot/data/sealed_lighthouse.json")
            state, policy = scenario["initial_state"], scenario["disclosure_policy"]
            _require(
                state["world"]["object_locations"]["signal_lens"] == "lamp_store"
                and set(state["npcs"]) == {"captain_mira"},
                "ontology world/actor source binding mismatch",
            )
            _require(
                set(state["facts"]) == {"dock_saved", "lighthouse_dark"}
                and state["quest"] == {"stage": 0, "flags": ["dock_saved"]},
                "ontology fact/quest source binding mismatch",
            )
            _require(
                policy["permanently_forbidden"] == ["keeper_betrayal"]
                and policy["stage_gates"] == [{"fact_id": "tide_marks_hint", "minimum_stage": 2}],
                "ontology policy declaration mismatch",
            )
            _require(
                [row[0] for row in rows]
                == ["World", "Actor", "Knowledge", "Fact", "Policy", "Quest", "Action", "Trace"]
                and all(len(row) == 2 for row in rows),
                "ontology role/column identity mismatch",
            )
            keyed_numbers = {row[0]: re.findall(r"[+-]?\d+", row[1]) for row in rows}
            _require(
                keyed_numbers
                == {
                    "World": [],
                    "Actor": [],
                    "Knowledge": [],
                    "Fact": [],
                    "Policy": ["2"],
                    "Quest": ["0"],
                    "Action": ["+1"],
                    "Trace": [],
                },
                "ontology keyed quantitative declaration drift",
            )
            _require(
                "keeper_betrayal" in rows[4][1]
                and "tide_marks_hint" in rows[4][1]
                and "dock_saved" in rows[5][1]
                and "reveal_hint" in rows[6][1],
                "ontology source field/row mapping mismatch",
            )
            descriptions = (
                [
                    "초기 객체 위치는 신호 렌즈를 등대 램프 보관소에 둔다.",
                    "미라 선장이 허용된 유일한 actor다.",
                    "Actor의 지식이 canonical Fact ID를 가리킴; 지식은 허가가 아니다.",
                    "초기 사실에는 dock_saved, lighthouse_dark가 포함되며 keeper_betrayal은 ID이지 비밀 payload가 아니다.",
                    "공개 정책은 keeper_betrayal을 금지하고 tide_marks_hint에 최소 quest stage $2$를 요구한다.",
                    "초기 quest는 stage $0$, flag dock_saved; 공개는 stage 불변.",
                    "reveal_hint(actor_id,fact_id)는 Fact/disclosed ID를 추가하며 조석 단서만 relationship memory를 추가한다. 최초 공개는 revision $+1$; 재표시는 불변이다.",
                    "이전·다음 상태 hash, 규칙·template·case ID가 packet과 version을 근거에 결속하며 누락은 PASS가 아니다.",
                ]
                if korean
                else [
                    "Initial object locations place the signal lens in the lamp store.",
                    "Captain Mira is the sole eligible actor.",
                    "Actor knowledge refers to canonical Fact IDs, not permission.",
                    "Initial facts include dock_saved and lighthouse_dark; keeper_betrayal is an ID, not payload.",
                    "Disclosure policy forbids keeper_betrayal; tide_marks_hint needs minimum quest stage $2$.",
                    "The initial quest is at stage $0$ with flag dock_saved; disclosure preserves stage.",
                    "reveal_hint(actor_id,fact_id) adds Fact/disclosed ID; only tide hint adds relationship memory. Fresh revision $+1$; redisplay unchanged.",
                    "Prior and next state hashes, rule and template identifiers, and case ID bind packet/version to evidence; absent fields cannot establish PASS.",
                ]
            )
            _require(
                [row[1] for row in rows] == descriptions,
                "ontology keyed role/source correspondence drift",
            )
            _require(
                self.family.get("disclosure") == "PASS",
                "ontology action/trace source semantics require complete disclosure receipt validation",
            )
            return (
                "design-contracts",
                "design_contract",
                {"roles": [row[0] for row in rows], "source_declarations": scenario},
            )
        if anchor == "tab:traceability-rubric":
            _require(
                [row[0] for row in rows] == [f"TR{n:02}" for n in range(1, 7)]
                and all(len(row) == 3 for row in rows),
                "rubric dimension/column identity mismatch",
            )
            _require(
                not any(re.search(r"\d", cell) for row in rows for cell in row[1:]),
                "unbound quantitative rubric score",
            )
            _require(
                self.family.get("preserved-statuses") == "PASS",
                "rubric must remain proposed/unmeasured",
            )
            expected_cells = (
                [
                    [
                        "task, 정확한 artifact revision/digest, activity, actor의 identity/activity binding",
                        "complete slot / required slot",
                    ],
                    [
                        r"request/input $\rightarrow$ rule version $\rightarrow$ evaluated check/result $\rightarrow$ decision",
                        "complete chain / inventoried decision",
                    ],
                    [
                        r"decision $\rightarrow$ 관측 state/artifact effect와 before/after 근거",
                        "complete correspondence / outcome-required decision",
                    ],
                    [
                        r"triggering failure $\rightarrow$ corrective package $\rightarrow$ exact revalidation $\rightarrow$ result",
                        "complete repair chain / actual repair attempt",
                    ],
                    [
                        r"forward requirement $\rightarrow$ artifact $\rightarrow$ verification 및 reverse in-scope change mapping",
                        "forward/reverse를 별도 보고",
                    ],
                    [
                        "non-author가 선언된 audit/replay target을 독립 실행",
                        "exercised target / declared target",
                    ],
                ]
                if korean
                else [
                    [
                        "identity/activity binding to task, exact artifact revision/digest, activity, and actor",
                        "complete slots / required slots",
                    ],
                    [
                        r"request/input $\rightarrow$ rule version $\rightarrow$ evaluated check/result $\rightarrow$ decision",
                        "complete chains / inventoried decisions",
                    ],
                    [
                        r"decision $\rightarrow$ observed state or artifact effect with before/after evidence",
                        "complete correspondences / decisions requiring outcome",
                    ],
                    [
                        r"triggering failure $\rightarrow$ corrective package $\rightarrow$ exact revalidation $\rightarrow$ result",
                        "complete repair chains / actual repair attempts",
                    ],
                    [
                        r"forward requirement $\rightarrow$ artifact $\rightarrow$ verification and reverse in-scope change mapping",
                        "report forward and reverse separately",
                    ],
                    [
                        "non-author independent exercise of declared audit/replay target",
                        "exercised targets / declared targets",
                    ],
                ]
            )
            _require(
                [row[1:] for row in rows] == expected_cells,
                "rubric keyed dimension/link/denominator correspondence drift",
            )
            return (
                "preserved-statuses",
                "design_contract",
                {"dimensions": [row[0] for row in rows], "measured": False},
            )
        if anchor == "tab:artifact-directory-map":
            return self.artifact_map(table)
        raise ValueError(f"no semantic adapter for reached manual table {anchor}")

    def bind(self, manifest):
        generated = {
            "tab:pilot-repair": "pilot",
            "tab:pilot-accounting": "pilot",
            "tab:contribution-map": "pilot",
            "tab:evidence-lanes": "pilot",
            "tab:review-boundary-funnel": "audit",
            "tab:review-structural-retention": "audit",
            "tab:review-surface-sentinels": "audit",
            "tab:runtime-comparison-aggregate": "runtime",
            "tab:runtime-identity-admission": "runtime",
            "tab:npc-screening": "npc",
            "tab:kg-ontology-simulation": "kg",
            "tab:disclosure-contract": "disclosure",
            "tab:disclosure-arms": "disclosure",
            "tab:disclosure-fixtures": "disclosure",
            "tab:paired-feedback-strata": "v5",
        }
        for table in self.report["tables"]:
            if table["status"] == "FAIL":
                self.report["checks"].append(
                    {
                        "id": "table-coverage",
                        "status": "FAIL",
                        "detail": f"{table['surface_id']}/{table['anchor']}: {table['detail']}",
                    }
                )
                continue
            anchor, source = table["anchor"], table["source"]
            family = generated.get(anchor)
            if family:
                table["adapter_id"] = family
                table["binding_kind"] = "source_materialization"
                valid = self.family.get(family) == "PASS" and source in self.expected
                table["status"] = (
                    "PASS"
                    if valid
                    else "FAIL"
                    if self.family.get(family) == "PASS"
                    else self.family.get(family, "FAIL")
                )
                table["detail"] = (
                    "exact source regenerated from validated retained inputs"
                    if valid
                    else f"missing validated {family} materialization for reached source {source}; family status {self.family.get(family)}"
                )
                if family == "audit" and self.public_source_projection:
                    table["binding_kind"] = "source_materialization_public_source_projection"
                    table["source_verification_mode"] = self.report["source_verification_mode"]
                    table["private_original_reverification"] = "NOT_PERFORMED_BY_THIS_COMMAND"
                    table["detail"] += (
                        "; explicit public reviewer-source derivative and original commitments only; private original bytes not reverified"
                    )
                if source in self.expected:
                    table["expected_sha256"] = _sha(self.expected[source])
                    table["observed_sha256"] = _sha((self.root / source).read_bytes())
                if table["status"] != "PASS":
                    self.report["checks"].append(
                        {
                            "id": f"table-materialization:{table['surface_id']}:{anchor}",
                            "status": table["status"],
                            "detail": table["detail"],
                        }
                    )
            else:
                result = self.check(
                    f"manual:{table['surface_id']}:{anchor}",
                    lambda table=table: self._bind_manual(table),
                )
                table["status"] = result["status"]
                table["detail"] = result["detail"]
            if not table["source_receipts"]:
                dependencies = [
                    "src/nesy_game/validator.py",
                    "src/nesy_game/repair.py",
                    "game-track/godot/data/sealed_lighthouse.json",
                    "research/traceability-scoring-20261023/rubric.json",
                ]
                table["source_receipts"] = [
                    {"path": path, "sha256": _sha((self.root / path).read_bytes())}
                    for path in dependencies
                ]
        for table in self.report["tables"]:
            table.pop("_block", None)
        for surface in self.report["surfaces"]:
            surface["binding_count"] = sum(
                table["status"] == "PASS"
                for table in self.report["tables"]
                if table["surface_id"] == surface["id"]
            )
            for table in self.report["tables"]:
                if table["surface_id"] == surface["id"] and table["status"] != "PASS":
                    surface["errors"].append(f"{table['anchor']}: {table['detail']}")

    def _bind_manual(self, table):
        family, kind, expected = self.manual(table)
        table.update(adapter_id=family, binding_kind=kind, expected=expected)
        if table["anchor"] == "tab:artifact-directory-map" and self.public_source_projection:
            table["source_verification_mode"] = self.report["source_verification_mode"]
            table["private_original_reverification"] = "NOT_PERFORMED_BY_THIS_COMMAND"
            return "typed source fields; audit reviewer-source is an explicit public derivative with original commitments only, not private-original reverification"
        return "typed row/column contract bound to declared source facts"


def _snapshot(
    root: Path, npc_root: Path | None, *, public_source_projection: bool = False
) -> dict[str, tuple[int, str]]:
    """Protect dependency membership and bytes, including failure paths."""
    result = {}
    folders = (
        "scripts",
        "src",
        "configs",
        "data",
        "paper/latex",
        "visuals",
        "research/academic-pipeline",
        "research/npc-disclosure",
        "research/simulation",
        "research/codex_feedback_pilot/public-v5",
        "research/traceability-scoring-20261023",
        "research/prospective-pilot-20261103",
        "knowledge/ontology",
        "game-track/godot/scripts",
        "game-track/godot/data",
        "game-track/schemas",
    )
    folders += (
        "_workspace/current/engineering/tech-verification/evidence/godot-4.7.1-20261113t151426z-paper-native3d-v1",
    )
    folders += (
        "research/maintenance",
        "research/development-cases/ontology-map-20261023-01",
        "research/codex_feedback_pilot/public-history-20261111",
        "game-track/godot/docs/latest",
        "game-track/web/dashboard",
    )
    folders += ("tests",)
    paths = {root / "research/claim-ledger.yaml"}
    for folder in folders:
        base = root / folder
        _require(not base.is_symlink(), f"protected dependency directory is a symlink: {folder}")
        for path in base.rglob("*"):
            _require(
                not path.is_symlink(),
                f"protected dependency symlink is not accepted: {path.relative_to(root)}",
            )
            if path.is_file() and "__pycache__" not in path.parts:
                paths.add(path)
    paths.update((root / "research/runtime-model-swap-20261024").glob("*/public-results-v1/*.json"))
    paths.add(root / "research/codex_feedback_pilot/paired-model-comparison-20261110-v5-source.zip")

    def receipt_paths(node):
        if isinstance(node, dict):
            if {"path", "sha256", "bytes"}.issubset(node):
                yield root / node["path"]
            else:
                for value in node.values():
                    yield from receipt_paths(value)
        elif isinstance(node, list):
            for value in node:
                yield from receipt_paths(value)

    paths.update(
        path
        for path in receipt_paths(_json(root / "visuals/source-manifest.json"))
        if path.is_file()
    )
    for path in sorted(paths):
        if public_source_projection and str(path.relative_to(root)) in {
            "research/academic-pipeline/gemini-review-20261113/reviewer-source.json",
            "research/academic-pipeline/gemini-review-20261113/results-v2/reviewer-source.json",
        }:
            continue
        _require(
            not any(
                parent.is_symlink()
                for parent in (path, *path.parents)
                if parent.is_relative_to(root)
            ),
            f"protected dependency symlink is not accepted: {path.relative_to(root)}",
        )
        _require(
            path.resolve().is_relative_to(root),
            f"protected source escapes selected root: {path.relative_to(root)}",
        )
        payload = path.read_bytes()
        result["project:" + str(path.relative_to(root))] = (len(payload), _sha(payload))
    if npc_root is not None and npc_root.is_dir():
        for path in sorted(npc_root.rglob("*")):
            _require(not path.is_symlink(), "historical dependency symlink is not accepted")
            if path.is_file() and "__pycache__" not in path.parts:
                _require(
                    path.resolve().is_relative_to(npc_root),
                    "historical source symlink escapes its root",
                )
                payload = path.read_bytes()
                result["npc-source:" + str(path.relative_to(npc_root))] = (
                    len(payload),
                    _sha(payload),
                )
    return result


def verify(
    root: Path, *, npc_evidence_root: Path | None = None, public_source_projection: bool = False
) -> dict[str, Any]:
    """Read-only Layer-A verification; no process, listener, or output writes."""
    checker = _Verifier(
        Path(root),
        Path(npc_evidence_root) if npc_evidence_root is not None else None,
        public_source_projection=public_source_projection,
    )
    npc_root = None
    before = None
    try:
        _require(
            type(public_source_projection) is bool,
            "public_source_projection must be an explicit boolean",
        )
        root = Path(root).expanduser().resolve()
        npc_root = (
            Path(npc_evidence_root).expanduser().resolve()
            if npc_evidence_root is not None
            else None
        )
        checker.root, checker.npc_root = root, npc_root
        if not root.is_dir():
            raise FileNotFoundError(f"project root is not a directory: {root}")
        required = [
            *SURFACES.values(),
            "visuals/source-manifest.json",
            "scripts/validate_visual_assets.py",
        ]
        review_base = "research/academic-pipeline/gemini-review-20261113"
        required.extend(
            [
                review_base + "/reviewer-source.public.json",
                review_base + "/public-source-projection-v1.json",
            ]
            if public_source_projection
            else [
                review_base + "/reviewer-source.json",
                review_base + "/results-v2/reviewer-source.json",
            ]
        )
        missing = [path for path in required if not (root / path).is_file()]
        if missing:
            raise FileNotFoundError(f"required project inputs missing: {missing}")
        if npc_root is None or not npc_root.exists():
            raise FileNotFoundError(
                "required NPC006 historical source root unavailable at revision " + NPC_REVISION
            )
        _require(npc_root.is_dir(), "present NPC006 historical source root is not a directory")
        before = _snapshot(root, npc_root, public_source_projection=public_source_projection)
        with _project_imports(root):
            visual = checker.module("validate_visual_assets")
            manifest = _json(root / "visuals/source-manifest.json")
            _require(
                manifest.get("schema_version") == 1, "source manifest schema_version must be 1"
            )
            checker.check("table-inventory", lambda: checker.inventory(visual, manifest))
            checker.check("stored-engine-captures", lambda: checker.captures(visual, manifest))
            validator = visual.Validator(require_pdf_tools=False, check_regeneration=False)
            for name in (
                "_validate_manifest_freshness",
                "_validate_receipts",
                "_validate_asset_inventory",
                "_validate_tables",
            ):

                def validate(name=name):
                    previous = len(validator.errors)
                    getattr(validator, name)(manifest)
                    _require(
                        len(validator.errors) == previous, "; ".join(validator.errors[previous:])
                    )
                    return "; ".join(validator.notes) or name

                checker.check(name.removeprefix("_"), validate)
            checker.check("preserved-statuses", checker.statuses)
            checker.check("withdrawn-ollama-attribution", checker.withdrawal)
            for name in ("pilot", "audit", "runtime", "disclosure", "npc", "kg", "v5"):
                checker.check(name, getattr(checker, name))
            crosswalk = checker.module("validate_contribution_crosswalk")

            def check_crosswalk():
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    crosswalk.main()
                return output.getvalue().strip()

            checker.check("contribution-crosswalk", check_crosswalk)
            checker.check("artifact-map-sources", checker.artifact_sources)
            checker.check("bounded-narrative-claims", checker.narratives)
            checker.bind(manifest)
    except FileNotFoundError as exc:
        checker.report["checks"].append(
            {"id": "prerequisites", "status": "BLOCKED", "detail": str(exc)}
        )
    except (OSError, ValueError, TypeError, KeyError) as exc:
        checker.report["checks"].append(
            {"id": "integrity", "status": "FAIL", "detail": f"{type(exc).__name__}: {exc}"}
        )
    except (
        ImportError,
        IndexError,
        AttributeError,
        AssertionError,
        RuntimeError,
        ArithmeticError,
        SyntaxError,
        NameError,
        csv.Error,
        tarfile.TarError,
    ) as exc:
        checker.report["checks"].append(
            {"id": "internal-checker", "status": "ERROR", "detail": f"{type(exc).__name__}: {exc}"}
        )
    finally:
        if before is not None:
            try:
                after = _snapshot(root, npc_root, public_source_projection=public_source_projection)
                changed = sorted(
                    key for key in before.keys() | after.keys() if before.get(key) != after.get(key)
                )
                checker.report["protected_snapshot"] = {
                    "status": "PASS" if not changed else "FAIL",
                    "path_count": len(before),
                    "changed": changed,
                    "before_sha256": _sha(_canonical(before).encode()),
                    "after_sha256": _sha(_canonical(after).encode()),
                }
                if changed:
                    checker.report["checks"].append(
                        {
                            "id": "protected-input-mutation",
                            "status": "FAIL",
                            "detail": f"protected input membership/bytes changed during verification: {changed}",
                        }
                    )
            except (OSError, ValueError) as exc:
                checker.report["protected_snapshot"] = {"status": "FAIL", "detail": str(exc)}
                checker.report["checks"].append(
                    {"id": "protected-input-mutation", "status": "FAIL", "detail": str(exc)}
                )
        for table in checker.report["tables"]:
            table.pop("_block", None)
    statuses = {check["status"] for check in checker.report["checks"]}
    statuses.update(table["status"] for table in checker.report["tables"])
    checker.report["status"] = next(
        (status for status in ("ERROR", "FAIL", "BLOCKED") if status in statuses), "PASS"
    )
    if not checker.report["tables"] and checker.report["status"] == "PASS":
        checker.report["status"] = "FAIL"
        checker.report["checks"].append(
            {"id": "table-coverage", "status": "FAIL", "detail": "no reached table was verified"}
        )
    return checker.report


def _prepare_npc_source(root: Path, destination: Path) -> None:
    """The CLI's sole preparation exception: local Git -> owned disposable tree."""
    import subprocess

    relatives = (
        "configs/npc-goal-recovery.json",
        "game-track/godot/project.godot",
        "game-track/schemas/npc-goal-recovery.schema.json",
        "data/fixtures/npc-goal-recovery/validated-v5",
        "src/nesy_game/npc_goal.py",
        "scripts/codex_oauth_llm.py",
        "scripts/run_npc_goal_experiment.py",
        "game-track/godot/scripts/game3d/game_3d.gd",
        "game-track/godot/scripts/game3d/npc_agent_client.gd",
        "game-track/godot/scripts/sealed_lighthouse_machine.gd",
        "game-track/godot/scripts/canonical_state.gd",
        "game-track/godot/data/npc-goal-recovery.json",
        "game-track/godot/data/sealed_lighthouse.json",
        "game-track/godot/scenes/main_3d.tscn",
    )
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(
        GIT_NO_LAZY_FETCH="1",
        GIT_TERMINAL_PROMPT="0",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
    )
    git = ["git", "-c", "protocol.allow=never"]

    def archive_at(base, paths):
        try:
            return subprocess.run(
                [*git, "-C", str(base), "archive", "--format=tar", NPC_REVISION, *paths],
                capture_output=True,
                check=False,
                env=environment,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValueError(
                "local historical-source Git archive exceeded its 30-second bound"
            ) from exc

    completed = archive_at(root, relatives)
    prefixed_archive = bool(completed.returncode)
    if completed.returncode:
        # A subproject in the original enclosing Git repository needs its path
        # prefix. Never search another checkout or substitute current sources.
        completed = archive_at(root.parent, [f"{root.name}/{path}" for path in relatives])
    if completed.returncode:
        raise FileNotFoundError(
            "local Git object/source paths unavailable for required NPC006 revision " + NPC_REVISION
        )
    with tarfile.open(fileobj=io.BytesIO(completed.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            name = Path(member.name)
            if prefixed_archive and name.parts and name.parts[0] == root.name:
                name = Path(*name.parts[1:])
            target = destination / name
            _require(
                not name.is_absolute() and target.resolve().is_relative_to(destination.resolve()),
                "unsafe historical archive path",
            )
            _require(
                member.isdir() or member.isfile(),
                "historical archive links/special files are not accepted",
            )
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                extracted = archive.extractfile(member)
                _require(extracted is not None, "historical archive member missing")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(extracted.read())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--npc-evidence-root", type=Path)
    parser.add_argument(
        "--public-source-projection",
        action="store_true",
        help="explicitly verify the approved public reviewer-source derivative and original commitments, not the withheld original bytes",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit the deterministic structured Layer-A report"
    )
    args = parser.parse_args(argv)
    root = args.root
    resolution_error = None
    try:
        root = root.expanduser().resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        resolution_error = str(exc)
    if resolution_error is not None:
        report = _Verifier(
            root, None, public_source_projection=args.public_source_projection
        ).report
        report.update(
            status="BLOCKED",
            checks=[{"id": "prerequisites", "status": "BLOCKED", "detail": resolution_error}],
        )
    elif args.npc_evidence_root is not None:
        report = verify(
            root,
            npc_evidence_root=args.npc_evidence_root,
            public_source_projection=args.public_source_projection,
        )
    elif not root.is_dir():
        report = _Verifier(
            root, None, public_source_projection=args.public_source_projection
        ).report
        report.update(
            status="BLOCKED",
            checks=[
                {
                    "id": "prerequisites",
                    "status": "BLOCKED",
                    "detail": "selected project root does not exist",
                }
            ],
        )
    else:
        import tempfile

        try:
            with tempfile.TemporaryDirectory(prefix="paper-claims-npc-source-") as temporary:
                historical = Path(temporary)
                _prepare_npc_source(root, historical)
                report = verify(
                    root,
                    npc_evidence_root=historical,
                    public_source_projection=args.public_source_projection,
                )
                report["historical_source_preparation"] = {
                    "status": "PREPARED_FROM_LOCAL_GIT",
                    "revision": NPC_REVISION,
                    "destination": "owned disposable directory; removed after verification",
                    "scope": "source preparation, not new engine/model observation",
                }
        except FileNotFoundError as exc:
            report = _Verifier(
                root, None, public_source_projection=args.public_source_projection
            ).report
            report.update(
                status="BLOCKED",
                checks=[
                    {"id": "historical-source-preparation", "status": "BLOCKED", "detail": str(exc)}
                ],
            )
        except (OSError, ValueError, tarfile.TarError) as exc:
            report = _Verifier(
                root, None, public_source_projection=args.public_source_projection
            ).report
            report.update(
                status="FAIL",
                checks=[
                    {"id": "historical-source-preparation", "status": "FAIL", "detail": str(exc)}
                ],
            )
    code = {"PASS": 0, "FAIL": 1, "BLOCKED": 2, "ERROR": 3}[report["status"]]
    report["exit_code"] = code
    report["command"] = ".venv/bin/python scripts/verify_paper_claims.py" + (
        " --json" if args.json else ""
    )
    if args.public_source_projection:
        report["command"] += " --public-source-projection"
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    else:
        print(f"paper claims Layer A: {report['status']} (exit {code})")
        print(report["scope"])
        for surface in report["surfaces"]:
            print(
                f"{surface['id']}: {surface['binding_count']}/{surface['table_count']} reached table bindings complete"
            )
        for check in report["checks"]:
            if check["status"] != "PASS":
                print(f"{check['status']} {check['id']}: {check['detail']}")
        print(
            "Fresh engine/Web, PDF rendering and provider recollection: NOT_EXECUTED_BY_THIS_COMMAND"
        )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
