"""The D-073 evaluation-trace mirror must track the byte-bound hard-policy machine.

`game-track/godot/scripts/sealed_lighthouse_machine.gd` is bound by SHA-256 into the
retained engine evidence, so the dashboard trace is reconstructed by a separate
mirror (`evaluation_trace.gd`) that is authored against one exact machine source.
These checks fail closed on drift: if the machine changes, the mirror's pinned hash
and its check plan must be re-audited in the same change.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACHINE = ROOT / "game-track/godot/scripts/sealed_lighthouse_machine.gd"
MIRROR = ROOT / "game-track/godot/scripts/game3d/evaluation_trace.gd"
CONTROLLER = ROOT / "game-track/godot/scripts/game3d/game_3d.gd"
EVIDENCE_MANIFEST = (
    ROOT
    / "_workspace/current/engineering/tech-verification/evidence/godot-4.7.1/evidence-manifest.json"
)

MACHINE_CHECK_ORDER = {
    "acquire_object": ["OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE"],
    "install_lens": ["MISSING_REQUIRED_OBJECT", "QUEST_STAGE_PRECONDITION"],
    "reveal_hint": [
        "FORBIDDEN_DISCLOSURE",
        "STAGE_GATED_DISCLOSURE",
        "UNKNOWN_ACTOR",
        "NPC_DOES_NOT_KNOW_FACT",
    ],
}


def _pinned_hash() -> str:
    match = re.search(r'MACHINE_SOURCE_SHA256 := "([0-9a-f]{64})"', MIRROR.read_text("utf-8"))
    assert match, "evaluation_trace.gd must pin MACHINE_SOURCE_SHA256"
    return match.group(1)


def test_mirror_is_pinned_to_the_current_machine_bytes() -> None:
    assert _pinned_hash() == hashlib.sha256(MACHINE.read_bytes()).hexdigest()


def test_mirror_pin_equals_the_retained_engine_evidence_binding() -> None:
    manifest = EVIDENCE_MANIFEST.read_text("utf-8")
    bound = set(re.findall(r'"machine_sha256":\s*"([0-9a-f]{64})"', manifest))
    assert bound == {_pinned_hash()}


def test_mirror_check_plan_matches_the_machine_source_order() -> None:
    """The mirror's CHECK_PLAN must list each refusal code in the order the machine's
    source raises it, so `skipped` can only name checks the engine really has."""
    source = MACHINE.read_text("utf-8")
    mirror = MIRROR.read_text("utf-8")
    for operation, codes in MACHINE_CHECK_ORDER.items():
        positions = [source.index(f'"{code}"') for code in codes]
        assert positions == sorted(positions), operation
        plan_block = re.search(rf'"{operation}":\s*\[(.*?)\]', mirror, re.DOTALL)
        assert plan_block, operation
        assert re.findall(r'"([A-Z_]+)"', plan_block.group(1)) == codes, operation


def test_controller_reports_only_mirror_traces_with_a_consistency_flag() -> None:
    controller = CONTROLLER.read_text("utf-8")
    assert "EvaluationTraceScript.reconstruct(" in controller
    assert "EvaluationTraceScript.consistent(" in controller
    assert '"consistent": false' in controller and '"consistent": true' in controller
    # The machine records nothing; the controller must never read a trace off it.
    assert "machine.last_trace" not in controller
    assert 'result["trace"]' not in controller
