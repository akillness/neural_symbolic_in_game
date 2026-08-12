# Evidence and Claim Status

TRACE-RPG uses explicit epistemic states:

- `verified-primary`: directly supported by a primary paper, official repository/model card, publisher, or regulator.
- `verified-scope-limited`: source supports a narrower setting than the planned paper.
- `design-assumption`: chosen architecture or protocol awaiting empirical test.
- `thin-evidence`: lead, snippet, inaccessible page, or unresolved source conflict.
- `TODO-RESULT`: planned empirical conclusion with no eligible trace-backed result.
- `verified-empirical`: confirmatory trace, analysis, semantic audit, reproducibility review, and bilingual parity all pass.

Pilot and screening data cannot transition directly to `verified-empirical`. A verified result is revoked if an upstream trace or analysis hash changes.

Related: [[wiki/concepts/journal-grade-experimental-design]], [[wiki/projects/trace-rpg-paper-2026]].

