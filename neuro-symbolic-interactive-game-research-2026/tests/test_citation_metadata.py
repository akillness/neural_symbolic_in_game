from __future__ import annotations

import copy
import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_contribution_crosswalk as crosswalk_validator


class CitationMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pipeline = ROOT / "research/academic-pipeline"
        cls.audit = json.loads(
            (pipeline / "stage-05-citation-verification.json").read_text(encoding="utf-8")
        )
        with (pipeline / "reference-topic-crosswalk.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            cls.crosswalk = {row["bib_key"]: row for row in csv.DictReader(handle)}

    def test_redundant_totals_are_derived_and_fail_closed(self) -> None:
        status_counts, rate_limited = crosswalk_validator._validate_citation_audit_totals(
            self.audit
        )
        self.assertEqual(status_counts, {"VERIFIED": 48, "PREPRINT": 7})
        self.assertEqual(rate_limited, 22)
        self.assertEqual(
            self.audit["totals"],
            {
                "entries": 55,
                "hallucinated": 0,
                "preprint": 7,
                "semantic_scholar_rate_limited": 22,
                "unmatched": 0,
                "verified": 48,
            },
        )

        stale = copy.deepcopy(self.audit)
        stale["totals"]["verified"] = 47
        with self.assertRaisesRegex(ValueError, "redundant totals drift"):
            crosswalk_validator._validate_citation_audit_totals(stale)

        contradictory = copy.deepcopy(self.audit)
        entry = contradictory["entries"][0]
        entry["rate_limited_indices"].append(entry["matched_indices"][0])
        with self.assertRaisesRegex(ValueError, "both matched and rate-limited"):
            crosswalk_validator._validate_citation_audit_totals(contradictory)

        unknown = copy.deepcopy(self.audit)
        unknown["entries"][0]["matched_indices"].append("unregistered_index")
        with self.assertRaisesRegex(ValueError, "unknown indices"):
            crosswalk_validator._validate_citation_audit_totals(unknown)

    def test_archival_promotions_and_source_receipts_are_synchronized(self) -> None:
        entries = {entry["key"]: entry for entry in self.audit["entries"]}
        self.assertIn("iccc_proceedings", entries["S01_vaucher2026ivie"]["matched_indices"])
        self.assertIn(
            "iccc_proceedings",
            self.crosswalk["S01_vaucher2026ivie"]["identity_indices"].split("|"),
        )

        s53 = entries["S53_li2025settingdc"]
        self.assertIn("openreview", s53["matched_indices"])
        self.assertEqual(
            s53["retrieval"]["paper_authors"],
            [
                "Ziyi Zeng",
                "Shengqi Li",
                "Jiajun Xi",
                "Andrew Zhu",
                "Prithviraj Ammanabrolu",
            ],
        )
        self.assertEqual(s53["retrieval"]["venue_list_authors"][:2], ["Shengqi Li", "Ziyi Zeng"])
        self.assertIn("equal contributors", s53["year_note"])
        self.assertIn("conflicting Li-first venue-list display", s53["year_note"])
        self.assertIn(
            "openreview",
            self.crosswalk["S53_li2025settingdc"]["identity_indices"].split("|"),
        )

    def test_human_readable_current_summary_matches_the_machine_record(self) -> None:
        stage_five = (
            ROOT / "research/academic-pipeline/stage-05-citation-verification.md"
        ).read_text(encoding="utf-8")
        current = stage_five.split("## Stage 8 addendum", maxsplit=1)[0]
        preprints = current.split("## Preprints", maxsplit=1)[1].split(
            "## Publisher-assignment record", maxsplit=1
        )[0]
        self.assertIn("| `VERIFIED` | 48 |", current)
        self.assertIn("| `PREPRINT` | 7 |", current)
        self.assertNotIn("| S01 |", preprints)
        self.assertNotIn("| S46 |", preprints)
        self.assertIn("7 preprints remain advisory", current)

        source_ledger = (ROOT / "research/source-ledger.yaml").read_text(encoding="utf-8")
        self.assertTrue(source_ledger.startswith("as_of: 2026-09-06\n"))
        self.assertIn("official-iccc-proceedings-plus-arxiv-and-index-triangulation", source_ledger)
        self.assertIn("official-openreview-record-and-pdf-plus-venue-list-conflict", source_ledger)
        self.assertIn("marked as equal contributors", source_ledger)

    def test_bounded_primary_refresh_preserves_the_release_totals(self) -> None:
        refresh = self.audit["bounded_primary_refresh"]
        self.assertEqual(refresh["date"], "2026-09-06")
        self.assertEqual(
            refresh["scope"],
            [
                "S02_figueiredo2025scaffolded",
                "S44_gongora2026worldstate",
                "S52_wang2025agentspec",
                "S54_zhou2025story2game",
                "S55_huang2026beyond",
                "S56_feng2025agentrr",
            ],
        )
        self.assertIn("totals remain unchanged", refresh["result"])
        self.assertIn("not an inference", refresh["claim_scope"])

        source_ledger = (ROOT / "research/source-ledger.yaml").read_text(encoding="utf-8")
        self.assertTrue(source_ledger.startswith("as_of: 2026-09-06\n"))
        self.assertIn("world-state-transformations-2026", source_ledger)
        self.assertIn("does not establish the absence", source_ledger)


if __name__ == "__main__":
    unittest.main()
