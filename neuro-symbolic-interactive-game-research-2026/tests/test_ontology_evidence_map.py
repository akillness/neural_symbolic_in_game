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


def _assert_mobile_caption_width(layout, tolerance=1):
    """A blockified mobile table must not collapse its caption into a letter-wide column."""
    assert layout["caption"]["width"] >= layout["table"]["width"] - tolerance, (
        "Mobile ontology caption collapsed",
        layout["caption"],
        layout["table"],
    )


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
    env = os.environ.copy()
    if env.get("NSG_BROWSER_BACKEND") == "aside":
        assert shutil.which(env.get("ASIDE_BIN", "aside")), "Aside CLI is required"
    else:
        playwright = os.environ.get("PLAYWRIGHT_BIN") or shutil.which("playwright")
        assert playwright, "Playwright is required to verify the frozen browser contract"
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
        timeout=140 if env.get("NSG_BROWSER_BACKEND") == "aside" else 60,
    )
    if result.returncode != 0:
        raise AssertionError(result.stdout + result.stderr)
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
            _assert_mobile_caption_width(layout, tolerance)
            require_fit(f"{stage}:caption", layout["caption"], container)
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


@pytest.mark.parametrize(
    "control,guard",
    [
        ("error", "final fixture pageErrors guard rejected"),
        ("outgoing", "final fixture outgoing guard rejected"),
        ("post", "final fixture GET-only guard rejected"),
    ],
)
def test_aside_final_drain_rejects_violations_after_original_assertions(
    component_dashboard_url, monkeypatch, control, guard
):
    """Late real exceptions, parent commands and POST501 cannot arrive after the last oracle."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("NSG_ASIDE_CLOSE_CONTROL", control)
    with pytest.raises(AssertionError, match=guard):
        test_isolated_component_map_and_existing_observer_contracts(
            component_dashboard_url, "valid", 1440
        )


@pytest.mark.parametrize(
    "control,guard",
    [
        ("error", "final fixture pageErrors guard rejected"),
        ("rejection", "final fixture pageErrors guard rejected"),
        ("outgoing", "final fixture outgoing guard rejected"),
        ("csp", "controlled fixture CSP violation"),
        ("post", "final fixture GET-only guard rejected"),
    ],
)
def test_aside_rejected_source_does_not_discard_concurrent_observations(
    component_dashboard_url, monkeypatch, control, guard
):
    """A caught trusted-function TypeError cannot erase a real independently delivered violation."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("NSG_ASIDE_REJECT_CONTROL", control)
    with pytest.raises(AssertionError, match=guard):
        test_isolated_component_map_and_existing_observer_contracts(
            component_dashboard_url, "valid", 1440
        )


def test_aside_partial_collector_failure_cannot_be_laundered_as_a_source_error(
    component_dashboard_url, monkeypatch
):
    """An iframe collector failure retains already-drained top errors and blocks attempted recovery."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("NSG_ASIDE_REJECT_CONTROL", "collector-loss")
    with pytest.raises(AssertionError, match="Aside fixture collector failed:") as failure:
        test_isolated_component_map_and_existing_observer_contracts(
            component_dashboard_url, "valid", 1440
        )
    observations = [
        json.loads(line)
        for line in str(failure.value).splitlines()
        if line.startswith('{"fixtureControl":"collector-loss"')
    ]
    assert observations == [
        {"fixtureControl": "collector-loss", "partialTopErrors": 1, "sticky": True}
    ]


@pytest.mark.parametrize(
    "projection",
    (
        "delayed-main",
        "auxiliary-before-ready",
        "auxiliary-after-ready",
        "auxiliary-during-close",
        "stale-closed-main",
        "probe-private-metadata",
    ),
)
def test_aside_tab_ownership_rejects_auxiliaries_without_miscounting_its_main(
    component_dashboard_url, tmp_path, monkeypatch, projection
):
    """Real fixture targets and observations stay contained without publishing opaque SDK metadata."""
    import sys

    real_cli = shutil.which(os.environ.get("ASIDE_BIN", "aside"))
    assert real_cli, "Aside CLI is required"
    receipt = tmp_path / "projection.json"
    driver_receipts = tmp_path / "driver-receipts.jsonl"
    wrapper = r"""
await (async (api) => {
 const mode=MODE, auxiliaryUrl=AUXILIARY_URL;
 let main,auxiliary,reads=0,omitted=0,auxiliaryEnumerated=false,closedMainTarget,stalePublished=false,mainOpens=0,auxiliaryCreatedAtOpen;
 let auxiliaryPresentBeforeCleanup=false,auxiliaryAbsentAfterCleanup=false,mainAbsentBeforeCleanup=false;
 const actualPages=new WeakMap();
 const snapshot=(tab,...args)=>api.snapshot(actualPages.get(tab)||tab,...args);
 const closeOwned=async(tab)=>{const actual=actualPages.get(tab)||tab;await api.closeTab(actual);const deadline=Date.now()+15000;while((await api.listBrowserTabs()).some(candidate=>candidate.targetId===actual.targetId)){if(Date.now()>=deadline)throw new Error("projection owned-tab cleanup unconfirmed");}};
 const privateSentinel="SYNTHETIC_PRIVATE_PROBE_METADATA_DO_NOT_PUBLISH";
 let nativeGuardFailures=0,taintedErrors=0,taintedViolations=0;
 const decode=([kind,value])=>kind==="object"?Object.fromEntries(value.map(([key,child])=>[key,decode(child)])):kind==="array"?value.map(decode):kind==="value"?value:undefined;
 const encode=value=>value===undefined?["undefined"]:value===null||typeof value!=="object"?["value",value]:Array.isArray(value)?["array",value.map(encode)]:["object",Object.entries(value).map(([key,child])=>[key,encode(child)])];
 const openTab=async(url)=>{
  main=await api.openTab(url);mainOpens++;
  if(mode==="probe-private-metadata"){
   const actual=main;const evaluate=(...args)=>actual.evaluate(...args);
   const projected=async(...args)=>{const value=await evaluate(...args);let packet;try{packet=typeof value==="string"?decode(JSON.parse(value)):undefined;}catch{}if(packet?.error?.includes("fixture observer readiness missing")){nativeGuardFailures++;throw new Error(packet.error+" "+privateSentinel);}let changed=false;if(Array.isArray(packet?.value?.errors)){packet.value.errors=packet.value.errors.map(error=>{if(/NSG_(top|iframe)_/.test(error)){taintedErrors++;changed=true;return error+" "+privateSentinel;}return error;});}if(Array.isArray(packet?.value?.violations)){for(const violation of packet.value.violations){violation.blocked+="/"+privateSentinel;violation.privateMetadata=privateSentinel;taintedViolations++;changed=true;}}return changed?JSON.stringify(encode(packet)):value;};
   main={get targetId(){return actual.targetId;},evaluate:projected,goto:(...args)=>actual.goto(...args),waitForFunction:(...args)=>actual.waitForFunction(...args),setViewportSize:(...args)=>actual.setViewportSize(...args),emulateMedia:(...args)=>actual.emulateMedia(...args),locator:(...args)=>actual.locator(...args),keyboard:actual.keyboard};
   actualPages.set(main,actual);
  }
  return main;
 };
 const closeTab=async(tab)=>{await api.closeTab(actualPages.get(tab)||tab);closedMainTarget=tab.targetId;if(mode==="auxiliary-during-close"&&mainOpens>=2&&!auxiliary){auxiliaryCreatedAtOpen=mainOpens;auxiliary=await api.openTab(auxiliaryUrl);auxiliaryEnumerated=(await api.listBrowserTabs()).some(candidate=>candidate.targetId===auxiliary.targetId);if(!auxiliaryEnumerated)throw new Error("auxiliary control not ready in inventory");}};
 const listBrowserTabs=async()=>{
  let listed=await api.listBrowserTabs();
  if(!main)return listed;
  reads++;
  if(mode==="delayed-main"&&omitted===0){omitted++;return listed.filter(tab=>tab.targetId!==main.targetId);}
  if(mode==="stale-closed-main"&&closedMainTarget&&main.targetId!==closedMainTarget&&!stalePublished){stalePublished=true;return [...listed,{targetId:closedMainTarget}];}
  if(!auxiliary&&((mode==="auxiliary-before-ready"&&reads===1)||(mode==="auxiliary-after-ready"&&reads===2))){
   auxiliary=await api.openTab(auxiliaryUrl);
   if(auxiliary.targetId===main.targetId)throw new Error("auxiliary control reused main target");
   listed=await api.listBrowserTabs();
   auxiliaryEnumerated=listed.some(tab=>tab.targetId===auxiliary.targetId);
   if(!auxiliaryEnumerated)throw new Error("auxiliary control not ready in inventory");
  }
  return listed;
 };
 try {
 WORKER
 } finally {
  mainAbsentBeforeCleanup=!(await api.listBrowserTabs()).some(tab=>tab.targetId===main?.targetId);
  if(main&&!mainAbsentBeforeCleanup)await closeOwned(main);
  if(auxiliary){
   auxiliaryPresentBeforeCleanup=(await api.listBrowserTabs()).some(tab=>tab.targetId===auxiliary.targetId);
   await closeOwned(auxiliary);
   auxiliaryAbsentAfterCleanup=!(await api.listBrowserTabs()).some(tab=>tab.targetId===auxiliary.targetId);
  }
  console.log(JSON.stringify({fixtureOwnershipProjection:{mode,reads,omitted,stalePublished,mainAbsentBeforeCleanup,auxiliaryCreatedAtOpen,auxiliaryEnumerated,auxiliaryPresentBeforeCleanup,auxiliaryAbsentAfterCleanup,nativeGuardFailures,taintedErrors,taintedViolations}}));
 }
})({listBrowserTabs,openTab,closeTab,snapshot});
""".replace("MODE", json.dumps(projection)).replace(
        "AUXILIARY_URL", json.dumps(component_dashboard_url + "/public/index.html")
    )
    executable = tmp_path / "aside-projection-fixture"
    executable.write_text(
        f"#!{sys.executable}\nimport json, subprocess, sys\nfrom pathlib import Path\n"
        f"source={wrapper!r}.replace('WORKER',sys.stdin.read())\n"
        f"result=subprocess.run([{real_cli!r},*sys.argv[1:]],input=source,text=True,capture_output=True)\n"
        "try:\n"
        " envelope=json.loads(result.stdout)\n"
        " observations=[json.loads(line)['fixtureOwnershipProjection'] for item in envelope['run']['content'] if item.get('type')=='text' for line in item.get('text','').splitlines() if line.startswith('{\"fixtureOwnershipProjection\":')]\n"
        f" Path({str(receipt)!r}).write_text(json.dumps(observations))\n"
        "finally:\n sys.stdout.write(result.stdout)\n sys.stderr.write(result.stderr)\n"
        "sys.exit(result.returncode)\n",
        encoding="utf-8",
    )
    executable.chmod(0o700)
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", str(executable))
    if projection == "probe-private-metadata":
        monkeypatch.setenv("NSG_ASIDE_RECEIPT_PATH", str(driver_receipts))
    if projection in {"delayed-main", "stale-closed-main", "probe-private-metadata"}:
        test_isolated_component_map_and_existing_observer_contracts(
            component_dashboard_url, "valid", 1440
        )
    else:
        with pytest.raises(AssertionError, match="unexpected fixture auxiliary tab"):
            test_isolated_component_map_and_existing_observer_contracts(
                component_dashboard_url, "valid", 1440
            )
    observations = json.loads(receipt.read_text())
    assert len(observations) == 1
    observed = observations[0]
    if projection == "delayed-main":
        assert observed["mainAbsentBeforeCleanup"] is True
        assert observed["omitted"] == 1
        assert observed["reads"] >= 2
    elif projection == "stale-closed-main":
        assert observed["stalePublished"] is True
        assert observed["mainAbsentBeforeCleanup"] is True
    elif projection == "probe-private-metadata":
        assert observed["nativeGuardFailures"] >= 1
        assert observed["taintedErrors"] >= 4
        assert observed["taintedViolations"] >= 4
        assert observed["mainAbsentBeforeCleanup"] is True
        assert "SYNTHETIC_PRIVATE_PROBE_METADATA_DO_NOT_PUBLISH" not in driver_receipts.read_text()
    else:
        assert observed["auxiliaryEnumerated"] is True
        assert observed["mainAbsentBeforeCleanup"] is True
        assert observed["auxiliaryPresentBeforeCleanup"] is True
        assert observed["auxiliaryAbsentAfterCleanup"] is True
        if projection == "auxiliary-during-close":
            assert observed["auxiliaryCreatedAtOpen"] == 2


@pytest.mark.parametrize("failure", ("malformed-input", "malformed-map", "missing-map"))
def test_aside_ontology_rejects_input_failures_without_disclosing_payload_or_path(
    tmp_path, monkeypatch, failure
):
    """Parser and filesystem failures stay category-only before browser launch."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("ASIDE_BIN", "/nonexistent-aside-entry-control")
    private_map = tmp_path / "SYNTHETIC_PRIVATE_MAP_PATH.json"
    if failure == "malformed-map":
        private_map.write_text('{"private":"SYNTHETIC_PRIVATE_MAP_PAYLOAD",', encoding="utf-8")
    payload = (
        '{"private":"SYNTHETIC_PRIVATE_INPUT_PAYLOAD",'
        if failure == "malformed-input"
        else json.dumps({"mapPath": str(private_map)})
    )
    result = subprocess.run(
        ["node", str(ROOT / "tests/ontology_evidence_map_driver.cjs")],
        input=payload,
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr == "Aside fixture operation failed\n"


def test_aside_rejects_prefixed_map_get_without_publishing_path_or_receipt(
    component_dashboard_url, tmp_path, monkeypatch
):
    """A real GET cannot use a suffix route to escape the fixture resource boundary."""
    monkeypatch.setenv("NSG_BROWSER_BACKEND", "aside")
    monkeypatch.setenv("NSG_ASIDE_GET_CONTROL", "prefixed-map")
    receipt = tmp_path / "completion.jsonl"
    monkeypatch.setenv("NSG_ASIDE_RECEIPT_PATH", str(receipt))
    failure = None
    try:
        test_isolated_component_map_and_existing_observer_contracts(
            component_dashboard_url, "valid", 1440
        )
    except AssertionError as error:
        failure = error
    public_output = str(failure or "") + (receipt.read_text() if receipt.exists() else "")
    assert "SYNTHETIC_PRIVATE_SEGMENT" not in public_output
    assert failure is not None, "A prefixed map GET was accepted as a fixture resource"
    assert "unexpected fixture resource" in str(failure)
    assert not receipt.exists(), "A rejected resource produced a successful completion receipt"
