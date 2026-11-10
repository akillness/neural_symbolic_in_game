"""Task freeze/leakage contracts. Hidden task answers never live in this repository."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from nesy_game import prospective_pilot as pilot


def test_task_freeze_without_independent_oracles_is_explicitly_blocked(tmp_path: Path) -> None:
    public = tmp_path / "public"
    private = tmp_path / "evaluator-only"
    public.mkdir()
    private.mkdir(mode=0o700)
    report = pilot.verify_task_oracles(public, private)
    assert report["status"] == "BLOCKED_TASK_FREEZE_INCOMPLETE"
    assert {row["task_id"] for row in report["tasks"]} == {"t1", "t2", "t3", "t4", "t5"}
    for row in report["tasks"]:
        assert row["status"] == "BLOCKED_TASK_FREEZE_INCOMPLETE"
        assert row["known_good"] is None and row["alternative_correct"] is None
        assert row["baseline"] is None and row["plausible_wrong"] is None


def test_task_semantics_are_equal_across_representations_not_just_equal_lengths() -> None:
    protocol = pilot.build_protocol()
    assert {task["task_id"] for task in protocol["tasks"]} == {"t1", "t2", "t3", "t4", "t5"}
    for task in protocol["tasks"]:
        semantic = task["semantic"]
        assert set(semantic) == {
            "requirement_ids",
            "public_facts",
            "preconditions",
            "allowed_effects",
            "rejection_semantics",
            "unchanged_invariants",
        }
        general = pilot.decode_context(task["contexts"]["general_rule"], "general_rule")
        ontology = pilot.decode_context(task["contexts"]["ontology"], "ontology")
        assert general == ontology == semantic


def test_freeze_rejects_representation_that_adds_a_hidden_advantage() -> None:
    protocol = pilot.build_protocol()
    protocol["tasks"][0]["contexts"]["ontology"] = 'ontology:{"extra_answer":"invented"}'
    with pytest.raises(ValueError):
        pilot.validate_protocol(protocol)


@pytest.mark.parametrize("leak_kind", ["whole_file", "added_line", "tokens", "hidden_literal"])
def test_leakage_checker_detects_solution_retrieval_despite_reformatting(
    tmp_path: Path, leak_kind: str
) -> None:
    public = tmp_path / "public"
    private = tmp_path / "evaluator-only"
    public.mkdir()
    private.mkdir(mode=0o700)
    correct = "def accept(record):\n    return record.kind == 'approved' and record.stage >= 2 and record.actor == 'captain'\n"
    hidden = "oracle-only-case-791-distinctive"
    (private / "known_good.py").write_text(correct, encoding="utf-8")
    (private / "hidden-cases.txt").write_text(hidden, encoding="utf-8")
    leaked = {
        "whole_file": correct,
        "added_line": "prefix\n    return record.kind == 'approved' and record.stage >= 2 and record.actor == 'captain'\nsuffix\n",
        "tokens": "def accept ( record ) : # comment\n return (record.kind == 'approved'\n and record.stage >= 2 and record.actor == 'captain')\n",
        "hidden_literal": "copied " + hidden,
    }[leak_kind]
    (public / "visible.txt").write_text(leaked, encoding="utf-8")
    oracle_manifest = {
        "known_good_files": [str(private / "known_good.py")],
        "added_lines": [correct.splitlines()[1]],
        "hidden_literals": [hidden],
        "hidden_case_ids": [],
        "disclosures": [],
    }
    with pytest.raises(ValueError):
        pilot.audit_task_leakage(public, private, oracle_manifest)


def test_mirror_disclosure_is_path_and_hash_bound_not_a_blanket_exemption(tmp_path: Path) -> None:
    public = tmp_path / "public"
    private = tmp_path / "evaluator-only"
    (public / "tests").mkdir(parents=True)
    private.mkdir(mode=0o700)
    mirror = public / "tests/public-check.txt"
    line = "return accepted if stage >= required_stage else denied"
    mirror.write_text(line, encoding="utf-8")
    manifest = {
        "known_good_files": [],
        "added_lines": [line],
        "hidden_literals": [],
        "hidden_case_ids": [],
        "disclosures": [
            {
                "path": "tests/public-check.txt",
                "sha256": hashlib.sha256(mirror.read_bytes()).hexdigest(),
                "kind": "public-test",
            }
        ],
    }
    assert pilot.audit_task_leakage(public, private, manifest)["status"] == "PASS"
    # A disclosure cannot authorize all later test files or a changed mirror.
    (public / "tests/undisclosed-copy.txt").write_text(line, encoding="utf-8")
    with pytest.raises(ValueError):
        pilot.audit_task_leakage(public, private, manifest)


def test_baseline_and_exploration_overlay_must_have_the_same_defect(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.py"
    corpus = tmp_path / "corpus.py"
    baseline.write_text("def gate(stage): return True\n", encoding="utf-8")
    corpus.write_text("def gate(stage): return stage >= 2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        pilot.validate_task_source_binding(
            baseline,
            corpus,
            {
                "source_commit": "13b5c77401aefc0cb8ff3f10534d8944564e957b",
                "baseline_sha256": hashlib.sha256(baseline.read_bytes()).hexdigest(),
            },
        )


@pytest.mark.parametrize(
    "relative",
    [
        ".git/objects/answer",
        "research/development-cases/old/candidate-final.json",
        "_workspace/archive/old-answer.txt",
        "notes/source-snapshot-v1/answer.py",
        "notes/frozen-packet-v1/answer.json",
        "answer.patch",
        "answer.diff",
        "nested/candidate-final-copy.py",
    ],
)
def test_corpus_forbidden_history_and_answer_paths_reject_even_without_literal_match(
    tmp_path: Path,
    relative: str,
) -> None:
    public, private = tmp_path / "public", tmp_path / "evaluator-only"
    private.mkdir(mode=0o700)
    forbidden = public / relative
    forbidden.parent.mkdir(parents=True, exist_ok=True)
    forbidden.write_text(
        "benign bytes cannot authorize a forbidden history surface", encoding="utf-8"
    )
    manifest = {
        "known_good_files": [],
        "added_lines": [],
        "hidden_literals": [],
        "hidden_case_ids": [],
        "disclosures": [],
    }
    with pytest.raises(ValueError):
        pilot.audit_task_leakage(public, private, manifest)


@pytest.fixture
def baseline_context_case(tmp_path: Path) -> tuple[Path, Path, str, dict]:
    public, private = tmp_path / "public", tmp_path / "evaluator-only"
    public.mkdir()
    private.mkdir(mode=0o700)
    baseline = (
        "def project(records):\n"
        '    return [record["value"] for record in records if record["active"] '
        'and record["stage"] >= 2 and record["enabled"]]\n'
        "\ndef eligible(record):\n"
        "    return True\n"
    )
    fixed_line = (
        '    return record["active"] and record["stage"] >= 2 and record["enabled"] '
        'and record["actor"] == "captain" and record["quota"] > 0'
    )
    correct = baseline.replace("    return True", fixed_line)
    known_good = private / "known_good.py"
    known_good.write_text(correct, encoding="utf-8")
    manifest = {
        "known_good_files": [str(known_good)],
        "added_lines": [fixed_line],
        "hidden_literals": ["oracle-only-context-case-791"],
        "hidden_case_ids": ["private-context-case-382"],
        "disclosures": [],
    }
    return public, private, baseline, manifest


def test_defective_baseline_context_is_not_a_solution_window(
    baseline_context_case: tuple[Path, Path, str, dict],
) -> None:
    public, private, baseline, manifest = baseline_context_case
    (public / "baseline.py").write_text(baseline, encoding="utf-8")
    # The unchanged comprehension shares >12 tokens with the new return line,
    # but neither its full line nor its actual actor/quota fix is in the baseline.
    # Without independently supplied baseline evidence, keep the existing check.
    with pytest.raises(ValueError, match="token_window"):
        pilot.audit_task_leakage(public, private, manifest)
    report = pilot.audit_task_leakage(public, private, manifest, baseline_texts=(baseline,))
    assert report["status"] == "PASS"
    assert report["disclosed_matches"] == []


@pytest.mark.parametrize(
    "leak_kind,match",
    [
        ("added_line", "added_line"),
        ("distinctive_fix_tokens", "token_window"),
        ("whole_file", "whole_file"),
        ("hidden_literal", "hidden literal or case id"),
        ("hidden_case_id", "hidden literal or case id"),
    ],
)
def test_baseline_context_does_not_exempt_actual_solution_or_hidden_material(
    baseline_context_case: tuple[Path, Path, str, dict],
    leak_kind: str,
    match: str,
) -> None:
    public, private, baseline, manifest = baseline_context_case
    leaked = {
        "added_line": "unrelated prefix\n" + manifest["added_lines"][0] + "\nunrelated suffix\n",
        # Only the distinctive fix suffix: no shared comprehension/predicate prefix.
        # Comments and whitespace differ, so only token matching can catch this.
        "distinctive_fix_tokens": 'record [ "actor" ] == # moved comment\n "captain" and record [ "quota" ] > 0\n',
        "whole_file": Path(manifest["known_good_files"][0]).read_text(encoding="utf-8"),
        "hidden_literal": manifest["hidden_literals"][0],
        "hidden_case_id": manifest["hidden_case_ids"][0],
    }[leak_kind]
    visible = public / "visible.txt"
    visible.write_text(leaked, encoding="utf-8")
    if leak_kind in ("hidden_literal", "hidden_case_id"):
        # Baseline-window subtraction and even a hash-bound mirror disclosure
        # must never authorize a literal that is explicitly evaluator-only.
        baseline += "\n# " + leaked + "\n"
        manifest["disclosures"] = [
            {
                "path": "visible.txt",
                "sha256": hashlib.sha256(visible.read_bytes()).hexdigest(),
                "kind": "semantic-mirror",
            }
        ]
    with pytest.raises(ValueError, match=match):
        pilot.audit_task_leakage(public, private, manifest, baseline_texts=(baseline,))


def test_baseline_context_preserves_path_and_hash_bound_mirror_disclosure(
    baseline_context_case: tuple[Path, Path, str, dict],
) -> None:
    public, private, baseline, manifest = baseline_context_case
    (public / "tests").mkdir()
    mirror = public / "tests/public-check.txt"
    fixed_line = manifest["added_lines"][0]
    mirror.write_text(fixed_line, encoding="utf-8")
    manifest["disclosures"] = [
        {
            "path": "tests/public-check.txt",
            "sha256": hashlib.sha256(mirror.read_bytes()).hexdigest(),
            "kind": "public-test",
        }
    ]
    report = pilot.audit_task_leakage(public, private, manifest, baseline_texts=(baseline,))
    assert report["status"] == "PASS"
    assert report["disclosed_matches"] == [
        {
            "path": "tests/public-check.txt",
            "kinds": ["added_line", "token_window"],
        }
    ]
    mirror.write_text(fixed_line + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="public-check.txt: undisclosed known-good match"):
        pilot.audit_task_leakage(public, private, manifest, baseline_texts=(baseline,))
    mirror.write_text(fixed_line, encoding="utf-8")
    (public / "tests/undisclosed-copy.txt").write_text(fixed_line, encoding="utf-8")
    with pytest.raises(ValueError, match="undisclosed-copy.txt: undisclosed known-good match"):
        pilot.audit_task_leakage(public, private, manifest, baseline_texts=(baseline,))


@pytest.mark.parametrize("link_kind", ["directory", "file"])
def test_leakage_audit_rejects_symlinks_exposing_evaluator_only_material(
    tmp_path: Path,
    link_kind: str,
) -> None:
    public, private = tmp_path / "public", tmp_path / "evaluator-only"
    public.mkdir()
    private.mkdir(mode=0o700)
    hidden = "synthetic-private-case-641-not-a-real-task-answer"
    (private / "case.txt").write_text(hidden, encoding="utf-8")
    link = public / "readable-notes"
    target = private if link_kind == "directory" else private / "case.txt"
    link.symlink_to(target, target_is_directory=link_kind == "directory")
    manifest = {
        "known_good_files": [],
        "added_lines": [],
        "hidden_literals": [hidden],
        "hidden_case_ids": [],
        "disclosures": [],
    }
    with pytest.raises(ValueError, match=r"readable-notes:.*symlink"):
        pilot.audit_task_leakage(public, private, manifest)


@pytest.mark.parametrize("variant", ["known_good", "alternative_correct"])
def test_oracle_verification_rejects_reformatted_short_multiline_fix_in_source_order(
    tmp_path: Path,
    variant: str,
) -> None:
    # These arithmetic fixtures are synthetic, not the hidden game-task answers.
    # Exercise manifest generation through the public verifier: a hand-ordered
    # manifest would miss the sorting defect in the generator entirely.
    bundle, private, corpus = (tmp_path / name for name in ("bundle", "evaluator-only", "corpus"))
    private.mkdir(mode=0o700)
    corpus.mkdir()
    baseline = "def calculate(x, y):\n    return 0\n"
    fixes = {
        "known_good": ("z = x + y + 1", "a = z * 2 + 3"),
        "alternative_correct": ("v = x + y + 1", "b = 3 + v * 2"),
    }
    bodies = {
        name: "def calculate(x, y):\n    "
        + "\n    ".join(lines)
        + f"\n    return {'a' if name == 'known_good' else 'b'}\n"
        for name, lines in fixes.items()
    }
    entries, rows = [], []
    for task_id in pilot.TASK_IDS:
        task = bundle / task_id
        spec = {
            "task_id": task_id,
            "source_commit": pilot.SOURCE_COMMIT,
            "target_file": "calculate.py",
            "baseline_sha256": pilot.sha256_hex(baseline.encode()),
        }
        task.mkdir(parents=True)
        spec_path = task / "task-spec.json"
        spec_path.write_text(json.dumps(spec), encoding="utf-8")
        for directory in ("baseline", "corpus-overlay"):
            (task / directory).mkdir()
            (task / directory / "calculate.py").write_text(baseline, encoding="utf-8")
        evaluator = private / "tasks" / task_id
        for name, body in bodies.items():
            directory = evaluator / "variants" / name
            directory.mkdir(parents=True)
            (directory / "calculate.py").write_text(body, encoding="utf-8")
        determinacy = evaluator / "determinacy.md"
        determinacy.write_text(
            "Synthetic arithmetic fixture: return twice (x + y + 1) plus three.\n", encoding="utf-8"
        )
        digest = pilot.sha256_hex(determinacy.read_bytes())
        entries.append(
            {
                "task_id": task_id,
                "source_commit": pilot.SOURCE_COMMIT,
                "baseline_sha256": spec["baseline_sha256"],
                "source_sha256": pilot.sha256_hex(bodies["known_good"].encode()),
                "determinacy_sha256": digest,
                "logic_auditor": "synthetic-fixture-auditor",
            }
        )
        row = {
            "task_id": task_id,
            "known_good": True,
            "alternative_correct": True,
            "baseline": False,
            "plausible_wrong": False,
            "task_spec_sha256": pilot.sha256_hex(spec_path.read_bytes()),
            "determinacy_sha256": digest,
            "logic_auditor": "synthetic-fixture-auditor",
            "logic_verdict": "PASS",
        }
        row["receipt_sha256"] = pilot.sha256_hex(pilot.canonical_json(row))
        rows.append(row)
    (bundle / "task-manifest.json").write_text(json.dumps({"tasks": entries}), encoding="utf-8")
    (private / pilot.HIDDEN_LITERALS_NAME).write_text(
        json.dumps({"hidden_literals": [], "hidden_case_ids": []}), encoding="utf-8"
    )
    observations = {
        "source_commit": pilot.SOURCE_COMMIT,
        "tasks": rows,
        "oracle_sha256": pilot.oracle_commitments(private)["oracle_sha256"],
    }
    (private / pilot.VARIANT_RESULTS_NAME).write_text(json.dumps(observations), encoding="utf-8")

    clean = pilot.verify_task_oracles(bundle, private, corpus_roots=(corpus,))
    assert clean["status"] == "PASS", clean
    assert clean["leakage"]["status"] == "PASS"

    # Each fix line is below the line-match threshold; the unrelated prefix and
    # omitted function wrapper prevent whole-file equality. Only the contiguous
    # added-hunk token window can detect this whitespace-reformatted retrieval.
    leak = (
        "# unrelated public prefix\n"
        + "\n".join(line.replace(" ", "") for line in fixes[variant])
        + "\n"
    )
    (corpus / "notes.py").write_text(leak, encoding="utf-8")
    report = pilot.verify_task_oracles(bundle, private, corpus_roots=(corpus,))
    assert report["status"] == "FAIL", report
    assert report["leakage"]["status"] == "FAIL", report
    assert "notes.py: undisclosed known-good match (token_window)" in report["leakage"]["error"]
