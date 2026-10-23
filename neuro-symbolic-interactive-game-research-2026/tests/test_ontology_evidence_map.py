"""Frozen ontology case contracts; browser fixtures are NOT actual gameplay evidence."""

from __future__ import annotations

import functools
import hashlib
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "research/development-cases/ontology-map-20261023-01"
PACKET_PATH = "research/npc-disclosure/reveal-hint-expectations-v1.json"
SCENARIO_PATH = "game-track/godot/data/sealed_lighthouse.json"
MAP = ROOT / "game-track/web/dashboard/ontology-map.json"


def _read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def _role_text(role):
    return " ".join(_strings(role))


def _roles():
    return {role["id"]: role for role in _read(MAP)["roles"]}


def test_frozen_sources_match_case_input_hashes():
    """The test oracle must remain the frozen public packet and scenario, not runtime output."""
    contract = _read(CASE / "contract.json")
    for relative in (PACKET_PATH, SCENARIO_PATH):
        assert (
            hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            == contract["input_sha256"][relative]
        ), relative


def test_map_declares_exactly_eight_distinct_bilingual_roles():
    payload = _read(MAP)
    contract = _read(CASE / "contract.json")
    assert payload["schema_version"] == "ontology-evidence-map/v1"
    ids = [role["id"] for role in payload["roles"]]
    assert sorted(ids) == sorted(contract["ontology_role_ids"])
    for role in payload["roles"]:
        # Contract declares bilingual labels, not merely bilingual explanatory prose.
        labels = {key: value for key, value in role.items() if "label" in key}
        text = " ".join(_strings(labels))
        assert re.search(r"[A-Za-z]", text), role["id"]
        assert re.search(r"[가-힣]", text), role["id"]


def test_map_binds_frozen_packet_not_a_runtime_result():
    packet = _read(ROOT / PACKET_PATH)
    contract = _read(CASE / "contract.json")
    text = _role_text(_read(MAP))
    assert contract["input_sha256"][PACKET_PATH] in text
    assert PACKET_PATH in text
    assert packet["packet_id"] in text
    assert SCENARIO_PATH in text


@pytest.mark.parametrize(
    "role_id,required_ids",
    [
        ("world", ("sealed-lighthouse-v1", "harbor_dock", "lamp_store", "signal_lens")),
        ("actor", ("captain_mira",)),
        ("knowledge", ("captain_mira", "keeper_betrayal", "tide_marks_hint", "DISC-004")),
        ("fact", ("dock_saved", "lighthouse_dark", "keeper_betrayal", "tide_marks_hint")),
        ("policy", ("keeper_betrayal", "tide_marks_hint", "DISC-001", "DISC-002")),
        ("quest", ("tide_marks_hint",)),
        ("action", ("reveal_hint", "DISC-005", "DISC-006", "DISC-007")),
        ("trace", ("prior_state_hash", "next_state_hash", "rule_ids", "template_id", "case_id")),
    ],
    ids=lambda value: value if isinstance(value, str) else None,
)
def test_each_role_explains_its_source_grounded_content(role_id, required_ids):
    """An eight-row vocabulary list cannot substitute for the declared game relationships."""
    text = _role_text(_roles()[role_id])
    for identifier in required_ids:
        assert identifier in text, f"{role_id} omits its declared relationship to {identifier}"


def test_source_map_keeps_canonical_ids_for_private_projection():
    """The source contract keeps exact story IDs; only the public DOM may alias them."""
    source_text = _role_text(_read(MAP))
    canonical_terms = (
        "sealed-lighthouse-v1",
        "sealed-lighthouse-disclosure-v1",
        "harbor_dock",
        "lamp_store",
        "signal_lens",
        "captain_mira",
        "dock_saved",
        "keeper_betrayal",
        "lighthouse_dark",
        "tide_marks_hint",
        "turn-05:mira-shared-tide-marks-hint",
        "sl-rc-003-authorized-hint",
        "mira-safe-deflection-v1",
    )
    public_aliases = ("[world-A]", "[actor-A]", "[fact-A]", "[fact-D]", "[memory-A]")
    for term in canonical_terms:
        assert term in source_text, f"source JSON lost canonical term {term}"
    for alias in public_aliases:
        assert alias not in source_text, (
            f"public alias replaced canonical source grounding: {alias}"
        )


def test_role_rules_resolve_to_frozen_packet_and_cover_disclosure_boundaries():
    packet = _read(ROOT / PACKET_PATH)
    roles = _roles()
    referenced = set()
    for role in roles.values():
        rule_ids = set(re.findall(r"\bDISC-\d{3}\b", _role_text(role)))
        assert rule_ids <= set(packet["rule_ids"]), role["id"]
        referenced.update(rule_ids)
    assert referenced == set(packet["rule_ids"])


def test_policy_and_quest_state_stage_gate_as_declaration_not_observed_progress():
    scenario = _read(ROOT / SCENARIO_PATH)
    gate = scenario["disclosure_policy"]["stage_gates"][0]
    roles = _roles()
    for role_id in ("policy", "quest"):
        text = _role_text(roles[role_id])
        assert gate["fact_id"] in text
        assert re.search(rf"(?<!\d){gate['minimum_stage']}(?!\d)", text), role_id
    assert scenario["disclosure_policy"]["policy_id"] in _role_text(roles["policy"])


def test_evidence_references_resolve_to_packet_and_rule_meanings_are_not_rewritten():
    packet = _read(ROOT / PACKET_PATH)
    payload = _read(MAP)
    assert payload["disclosure_rule_meanings"] == packet["rule_ids"]
    assert payload["source_packet"]["status"] == packet["status"]
    assert payload["source_packet"]["packet_version"] == packet["packet_version"]
    case_ids = {
        item["case_id"]
        for group in ("normal_cases", "boundary_cases", "malformed_cases")
        for item in packet[group]
    }
    for role in payload["roles"]:
        assert role["evidence_refs"], f"{role['id']} has no source grounding"
        for reference in role["evidence_refs"]:
            if reference in case_ids:
                continue
            target = packet
            for segment in reference.split("."):
                assert isinstance(target, dict) and segment in target, reference
                target = target[segment]


@pytest.fixture(scope="module")
def component_dashboard_url():
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(ROOT / "game-track/web")
    )
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.mark.parametrize(
    "mode,width",
    [
        ("valid", 1440),
        ("valid", 390),
        ("unsafe-text", 390),
        ("missing", 1440),
        ("malformed-json", 1440),
        ("null", 1440),
        ("duplicate-role", 1440),
        ("missing-role", 1440),
        ("wrong-hash", 1440),
        ("unknown-rule", 1440),
        ("missing-translation", 1440),
        ("unknown-evidence-ref", 1440),
        ("unsafe-evidence-ref", 1440),
        ("truncated-evidence-refs", 1440),
        ("duplicate-evidence-refs", 1440),
        ("missing-role-rule", 1440),
        ("duplicate-role-rule", 1440),
        ("arbitrary-rule-sets", 1440),
        ("wrong-packet-path", 1440),
        ("wrong-packet-status", 1440),
        ("wrong-scenario-path", 1440),
        ("wrong-scenario-hash", 1440),
    ],
    ids=lambda value: str(value),
)
def test_isolated_component_map_and_existing_observer_contracts(
    component_dashboard_url, mode, width
):
    """Browser-only fixture evidence: no synthetic result is labeled actual gameplay."""
    playwright = os.environ.get("PLAYWRIGHT_BIN") or shutil.which("playwright")
    assert playwright, "Playwright is required to verify the frozen browser contract"
    env = os.environ.copy()
    env["NODE_PATH"] = str(Path(playwright).parent.parent / "lib/node_modules")
    candidates = sorted(
        Path.home().glob(
            "Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/"
            "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
        )
    )
    if candidates and not env.get("PLAYWRIGHT_EXECUTABLE_PATH"):
        env["PLAYWRIGHT_EXECUTABLE_PATH"] = str(candidates[-1])
    result = subprocess.run(
        ["node", str(ROOT / "tests/ontology_evidence_map_driver.cjs")],
        input=json.dumps(
            {
                "baseUrl": component_dashboard_url,
                "mapPath": str(MAP),
                "roles": _read(CASE / "contract.json")["ontology_role_ids"],
                "mode": mode,
                "width": width,
            }
        ),
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    receipt = json.loads(result.stdout.strip())
    assert receipt["result"] == "pass"
    assert receipt["fixture"] == "isolated component transport; NOT actual gameplay"
    if width == 390 and mode in {"valid", "unsafe-text"}:
        layouts = receipt["mobileLayout"]
        assert [layout["stage"] for layout in layouts] == ["declaration", "observed", "reset"]
        violations = []
        tolerance = 1  # CSS subpixel layout versus integer client/scroll widths.

        def require_fit(label, bounds, visible):
            if (
                bounds["left"] < visible["left"] - tolerance
                or bounds["right"] > visible["right"] + tolerance
                or bounds["width"] > visible["width"] + tolerance
            ):
                violations.append({"target": label, "bounds": bounds, "visible": visible})

        def require_no_scroll(label, measured, available):
            if measured["scrollWidth"] > available + tolerance:
                violations.append(
                    {
                        "target": label,
                        "scrollWidth": measured["scrollWidth"],
                        "available": available,
                    }
                )

        for layout in layouts:
            stage = layout["stage"]
            container = layout["container"]
            require_fit(f"{stage}:table", layout["table"], container)
            require_no_scroll(f"{stage}:table", layout["table"], container["width"])
            require_no_scroll(
                f"{stage}:table-internal", layout["table"], layout["table"]["clientWidth"]
            )
            assert set(_read(CASE / "contract.json")["ontology_role_ids"]) <= {
                cell["role"] for cell in layout["cells"]
            }, f"{stage}: mobile table hid structural rows"
            assert any(cell["paragraphs"] for cell in layout["cells"]), (
                f"{stage}: mobile paragraph geometry was not exercised"
            )
            for index, cell in enumerate(layout["cells"]):
                label = f"{stage}:{cell['role']}:cell-{index}"
                require_fit(label, cell["bounds"], container)
                require_no_scroll(label, cell, cell["clientWidth"])
                visible = {
                    "left": max(container["left"], cell["content"]["left"]),
                    "right": min(container["right"], cell["content"]["right"]),
                }
                visible["width"] = visible["right"] - visible["left"]
                for text_bounds in cell["textBounds"]:
                    require_fit(f"{label}:text", text_bounds, visible)
                for paragraph_index, paragraph in enumerate(cell["paragraphs"]):
                    paragraph_label = f"{label}:paragraph-{paragraph_index}"
                    require_fit(paragraph_label, paragraph["bounds"], visible)
                    require_no_scroll(paragraph_label, paragraph, paragraph["clientWidth"])
                    for text_bounds in paragraph["textBounds"]:
                        require_fit(f"{paragraph_label}:text", text_bounds, visible)
        assert not violations, "Mobile ontology content is internally clipped: " + json.dumps(
            {
                "violation_count": len(violations),
                "layouts": [
                    {key: layout[key] for key in ("stage", "container", "table")}
                    for layout in layouts
                ],
                "first_violations": violations[:12],
                "first_paragraph_violation": next(
                    (violation for violation in violations if ":paragraph-" in violation["target"]),
                    None,
                ),
            },
            ensure_ascii=False,
        )
