import unittest
from html import escape
from pathlib import Path

from scripts.generate_readme_visuals import claim_status_svg, read_claims, wrap


class ClaimStatusVisualTests(unittest.TestCase):
    def test_every_claim_and_evidence_name_is_rendered_without_line_truncation(self) -> None:
        svg = claim_status_svg()

        for claim in read_claims():
            self.assertIn(escape(str(claim["id"])), svg)
            for line in wrap(str(claim["claim"]), 64):
                self.assertIn(escape(line), svg)
            for evidence_path in claim.get("evidence") or []:
                self.assertIn(escape(Path(str(evidence_path)).name), svg)

        self.assertNotIn('class="claim-truncated"', svg)


if __name__ == "__main__":
    unittest.main()
