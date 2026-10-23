"use strict";

// ISOLATED COMPONENT FIXTURE ONLY. No real game or gameplay outcomes are exercised.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const { chromium } = require("playwright");
const config = JSON.parse(fs.readFileSync(0, "utf8"));
const map = JSON.parse(fs.readFileSync(config.mapPath, "utf8"));
const roles = config.roles;
const HASH_A = "a".repeat(64);
const HASH_B = "b".repeat(64);
const attack = '<img src=x onerror="window.__ontologyInjected=true"><script>window.__ontologyInjected=true</script>';
// Independent test oracle for the public projection policy. The source map remains
// canonical; this fixture only describes the neutral aliases that a public DOM may expose.
const PUBLIC_ALIAS_BY_TERM = Object.freeze({
  "turn-05:mira-shared-tide-marks-hint": "[memory-A]",
  "sl-rc-003-authorized-hint": "[authorized-template]",
  "mira-safe-deflection-v1": "[fallback-template]",
  "sealed-lighthouse-disclosure-v1": "[policy-A]",
  "sealed-lighthouse-v1": "[world-A]",
  captain_mira: "[actor-A]",
  dock_saved: "[fact-A]",
  keeper_betrayal: "[fact-B]",
  lighthouse_dark: "[fact-C]",
  tide_marks_hint: "[fact-D]",
  harbor_dock: "[location-A]",
  lamp_store: "[location-B]",
  signal_lens: "[object-A]",
  Mira: "[actor-A]",
  미라: "[행위자-A]",
});
const PROTECTED_TERMS = Object.keys(PUBLIC_ALIAS_BY_TERM).sort((a, b) => b.length - a.length);
const expectedPublicText = (value) => PROTECTED_TERMS.reduce(
  (projected, term) => projected.split(term).join(PUBLIC_ALIAS_BY_TERM[term]),
  String(value),
);
const semanticFragments = (value) => {
  let remaining = String(value);
  for (const term of PROTECTED_TERMS) remaining = remaining.split(term).join("\u0000");
  return remaining.split("\u0000").map((part) => part.trim()).filter((part) => part.length > 2);
};

const explanation = (overrides = {}) => ({
  schema_id: "trace-rpg-semantic-explanation", schema_version: "1.0.0",
  input: { operation: "reveal_hint", actor_role: "captain", subject_type: "lead" },
  ontology: { relation: "captain_to_lead_disclosure", rule_ids: ["DISC-005"] },
  checks: { evaluated: [{ code: "NPC_DOES_NOT_KNOW_FACT", gate: "DISCLOSURE", outcome: "pass" }], skipped: [], out_of_scope: [], unreported: [], consistent: true },
  decision: { outcome: "authorized_fresh", accepted: true, result_codes: [] },
  state_effect: { kind: "fresh_disclosure", mutated: true, prior_state_hash: HASH_A, next_state_hash: HASH_B },
  engine: { seq: 1, t_ms: 100 }, ...overrides,
});

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
  try {
    const context = await browser.newContext({ viewport: { width: config.width, height: 1000 }, reducedMotion: "reduce" });
    const page = await context.newPage();
    const pageErrors = [];
    const outgoing = [];
    const requests = [];
    page.on("pageerror", (error) => pageErrors.push(error.message));
    page.on("request", (request) => requests.push({ url: request.url(), method: request.method() }));
    // Stop only the heavy iframe at the network boundary. The real dashboard and
    // its real origin/source-validated event receiver are otherwise unmodified.
    await page.route("**/public/index.html", (route) => route.fulfill({ contentType: "text/html", body: '<!doctype html><title>ISOLATED COMPONENT FIXTURE, NOT GAMEPLAY</title><body>Component transport only</body>' }));
    await page.exposeFunction("captureOutgoing", (value) => outgoing.push(value));
    await page.addInitScript(() => {
      if (window === window.top) return;
      window.addEventListener("message", (event) => window.parent.captureOutgoing(event.data));
    });
    await page.route("**/ontology-map.json", (route) => {
      const fixture = structuredClone(map);
      if (config.mode === "missing") return route.fulfill({ status: 404, body: "missing local map" });
      if (config.mode === "malformed-json") return route.fulfill({ contentType: "application/json", body: "{" });
      if (config.mode === "null") return route.fulfill({ json: null });
      if (config.mode === "duplicate-role") fixture.roles[1] = structuredClone(fixture.roles[0]);
      if (config.mode === "missing-role") fixture.roles.pop();
      if (config.mode === "wrong-hash") fixture.source_packet.sha256 = HASH_A;
      if (config.mode === "unknown-rule") fixture.roles[0].rule_ids.push("DISC-999");
      if (config.mode === "missing-translation") delete fixture.roles[0].labels.ko;
      if (config.mode === "unknown-evidence-ref") fixture.roles[0].evidence_refs = ["not.in.frozen.packet"];
      if (config.mode === "arbitrary-rule-sets") {
        fixture.rule_sets.python7 = fixture.rule_sets.python7.map((rule, index) => ({ ...rule, id: `PY-ARBITRARY-${index}` }));
        fixture.rule_sets.godot6 = fixture.rule_sets.godot6.map((rule, index) => ({ ...rule, id: `GODOT-ARBITRARY-${index}` }));
      }
      if (config.mode === "wrong-packet-path") fixture.source_packet.path = "research/unfrozen/packet.json";
      if (config.mode === "wrong-packet-status") fixture.source_packet.status = "RUNTIME_RESULTS";
      if (config.mode === "wrong-scenario-path") fixture.scenario.path = "game-track/godot/data/other_scenario.json";
      if (config.mode === "wrong-scenario-hash") fixture.scenario.sha256 = HASH_A;
      if (config.mode === "unsafe-text") {
        fixture.roles[0].labels.en = attack;
        fixture.roles[0].content.en = attack;
      }
      if (config.mode === "unsafe-evidence-ref") fixture.roles[0].evidence_refs = [attack];
      if (["truncated-evidence-refs", "duplicate-evidence-refs", "missing-role-rule", "duplicate-role-rule"].includes(config.mode)) {
        const actor = fixture.roles.find((role) => role.id === "actor");
        if (config.mode === "truncated-evidence-refs") actor.evidence_refs = ["scope.eligible_actor_ids"];
        if (config.mode === "duplicate-evidence-refs") actor.evidence_refs = ["scope.eligible_actor_ids", "M-001", "M-001", "M-007"];
        if (config.mode === "missing-role-rule") actor.rule_ids = ["DISC-003"];
        if (config.mode === "duplicate-role-rule") actor.rule_ids = ["DISC-003", "DISC-003", "DISC-007"];
      }
      return route.fulfill({ json: fixture });
    });
    await page.goto(`${config.baseUrl}/dashboard/index.html`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.querySelector("#comparison-status")?.textContent.includes("frozen independent lane"));
    await page.waitForFunction(() => /loaded|unavailable/.test(document.querySelector("#ontology-map-status")?.textContent || ""));
    const valid = ["valid", "unsafe-text"].includes(config.mode);
    const summary = page.locator("details.engineering > summary");
    await summary.focus();
    await page.keyboard.press("Enter");
    assert.equal(await page.locator("details.engineering").getAttribute("open"), "", "Engineering detail must open from keyboard");
    const table = page.locator(".ontology-map table");
    const observed = (id) => page.locator(`[data-observed-role="${id}"]`);
    const mobileLayout = [];
    const measureMobileLayout = async (stage) => {
      if (!valid || config.width !== 390) return;
      mobileLayout.push(await table.evaluate((element, stage) => {
        const bounds = (node) => {
          const rect = node.getBoundingClientRect();
          return { left: rect.left, right: rect.right, width: rect.width };
        };
        const contentBounds = (node) => {
          const rect = node.getBoundingClientRect();
          const style = getComputedStyle(node);
          const left = rect.left + node.clientLeft + parseFloat(style.paddingLeft);
          const right = rect.left + node.clientLeft + node.clientWidth - parseFloat(style.paddingRight);
          return { left, right, width: right - left };
        };
        const container = contentBounds(element.parentElement);
        // Intersect every actual clipping ancestor, not just the document: a
        // hidden/scrollable wrapper must not conceal an oversized mobile table.
        for (let ancestor = element.parentElement; ancestor; ancestor = ancestor.parentElement) {
          if (!/hidden|clip|auto|scroll/.test(getComputedStyle(ancestor).overflowX)) continue;
          const rect = ancestor.getBoundingClientRect();
          container.left = Math.max(container.left, rect.left + ancestor.clientLeft);
          container.right = Math.min(container.right, rect.left + ancestor.clientLeft + ancestor.clientWidth);
        }
        container.left = Math.max(container.left, 0);
        container.right = Math.min(container.right, window.innerWidth);
        container.width = container.right - container.left;
        const displayed = (node) => [...node.getClientRects()].some((rect) => rect.width > 0 && rect.height > 0);
        // Mobile intentionally clips the semantic thead for screen readers;
        // inspect the displayed row headings and content cells, not that label copy.
        const cells = [...element.querySelectorAll("tbody th, tbody td")].filter(displayed).map((cell) => {
          const content = contentBounds(cell);
          const paragraphs = [...cell.querySelectorAll("p")].filter(displayed).map((paragraph) => {
            const range = document.createRange();
            range.selectNodeContents(paragraph);
            return {
              text: paragraph.textContent,
              bounds: bounds(paragraph),
              clientWidth: paragraph.clientWidth,
              scrollWidth: paragraph.scrollWidth,
              textBounds: [...range.getClientRects()].filter((rect) => rect.width > 0 && rect.height > 0)
                .map((rect) => ({ left: rect.left, right: rect.right, width: rect.width })),
            };
          });
          const range = document.createRange();
          range.selectNodeContents(cell);
          return {
            role: cell.closest("tr").querySelector("[data-observed-role]")?.dataset.observedRole || "heading",
            text: cell.textContent,
            bounds: bounds(cell), content,
            clientWidth: cell.clientWidth, scrollWidth: cell.scrollWidth,
            textBounds: [...range.getClientRects()].filter((rect) => rect.width > 0 && rect.height > 0)
              .map((rect) => ({ left: rect.left, right: rect.right, width: rect.width })),
            paragraphs,
          };
        });
        return {
          stage, container,
          table: { ...bounds(element), clientWidth: element.clientWidth, scrollWidth: element.scrollWidth },
          cells,
        };
      }, stage));
    };
    if (valid) {
      assert.equal(await table.locator("tbody tr").count(), roles.length, "all structural roles must render");
      const headings = await table.locator("thead th").allTextContents();
      assert(headings.some((value) => /declared/i.test(value)) && headings.some((value) => /observed/i.test(value)), "declaration and observation must be distinct columns");
      assert.equal(await table.locator('th[scope="row"]').count(), roles.length, "role labels must remain semantic row headings");
      for (const role of map.roles) {
        const row = table.locator("tbody tr").filter({ has: observed(role.id) });
        assert((await row.textContent()).includes(role.labels.ko), `${role.id} Korean label lost`);
        assert((await observed(role.id).textContent()).includes("missing/unreported"), `${role.id} inferred evidence before an event`);
        assert(!/\bpass\b/i.test(await observed(role.id).textContent()), `${role.id} absence incorrectly passed`);
      }
      if (config.mode === "unsafe-text") {
        assert((await table.textContent()).includes(attack), "adversarial declaration was not rendered as literal text");
        assert.equal(await table.locator("img, script, iframe, [onerror]").count(), 0, "declaration became active markup");
        assert.equal(await page.evaluate(() => window.__ontologyInjected), undefined);
      } else {
        for (const role of map.roles) {
          const row = table.locator("tbody tr").filter({ has: observed(role.id) });
          const rowText = await row.textContent();
          const declaration = await row.locator("td").first().textContent();
          assert(rowText.includes(role.labels.en) && rowText.includes(role.labels.ko), `${role.id} bilingual labels lost`);
          assert(declaration.includes(expectedPublicText(role.content.en)), `${role.id} English relationship structure changed`);
          assert(declaration.includes(expectedPublicText(role.content.ko)), `${role.id} Korean relationship structure changed`);
          for (const sourceField of [role.identifiers, role.content.en, role.content.ko]) {
            for (const fragment of semanticFragments(sourceField)) {
              assert(declaration.includes(fragment), `${role.id} lost non-sensitive declared meaning: ${fragment}`);
            }
          }
          const protectedInRole = PROTECTED_TERMS.filter((term) => [role.identifiers, role.content.en, role.content.ko].some((field) => field.includes(term)));
          for (const term of protectedInRole) {
            assert(declaration.includes(PUBLIC_ALIAS_BY_TERM[term]), `${role.id} lost neutral alias for protected term ${term}`);
            assert(!declaration.includes(term), `${role.id} leaked protected term ${term} in declared DOM`);
          }
          for (const reference of role.evidence_refs) assert(rowText.includes(reference), `${role.id} source reference lost from public evidence cell`);
        }
        const ontologyText = await page.locator(".ontology-map").textContent();
        for (const term of PROTECTED_TERMS) assert(!ontologyText.includes(term), `protected story term leaked into ontology DOM: ${term}`);
        for (const alias of new Set(Object.values(PUBLIC_ALIAS_BY_TERM))) {
          if (PROTECTED_TERMS.some((term) => map.roles.some((role) => [role.identifiers, role.content.en, role.content.ko].some((field) => field.includes(term)) && PUBLIC_ALIAS_BY_TERM[term] === alias))) {
            assert(ontologyText.includes(alias), `neutral public alias missing: ${alias}`);
          }
        }
      }
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `document overflow at ${config.width}px`);
    } else {
      assert.match(await page.locator("#ontology-map-status").textContent(), /unavailable.*missing|missing.*unavailable/i);
      assert.equal(await table.locator("tbody tr").count(), 0, "invalid map retained apparently trustworthy declarations");
    }
    await page.evaluate(() => document.fonts.ready);
    await measureMobileLayout("declaration");

    const frame = page.frames().find((candidate) => candidate.url().includes("/public/index.html"));
    assert(frame, "isolated transport frame is unavailable");
    const send = (value) => frame.evaluate((data) => window.parent.postMessage(data, location.origin), value);
    const event = (value, seq = 1) => ({ channel: "trace-rpg-dashboard", kind: "disclosure_outcome", seq, t_ms: seq * 100, payload: { explanation: value } });
    const frozen = await page.locator(".frozen-comparison").textContent();
    const canonical = await page.locator("#session-hash").textContent();
    // A parent-origin spoof cannot supply observation, even with a valid envelope.
    await page.evaluate((data) => window.postMessage(data, location.origin), event(explanation()));
    await send(event(explanation()));
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 1);
    assert((await page.locator("#semantic-explanation").textContent()).includes("authorized_fresh"), "signal consumer stopped rendering real receiver input");
    if (valid) {
      assert((await observed("action").textContent()).includes("authorized_fresh"));
      assert((await observed("policy").textContent()).includes("DISC-005"));
      assert((await observed("trace").textContent()).includes("NPC_DOES_NOT_KNOW_FACT"));
      assert((await observed("trace").textContent()).includes(HASH_A));
      assert((await observed("trace").textContent()).includes(HASH_B));
      for (const role of ["world", "knowledge", "fact", "quest"]) {
        assert((await observed(role).textContent()).includes("unavailable"), `${role} invented full canonical state from public projection`);
      }
      assert(!(await observed("actor").textContent()).includes("captain_mira"), "declared actor ID fabricated as observed");
      assert(!(await observed("fact").textContent()).includes("tide_marks_hint"), "declared fact ID fabricated as observed");
    }
    await measureMobileLayout("observed");
    const beforeInspection = await page.evaluate(() => JSON.stringify(window.__traceDashboard));
    await summary.focus();
    await page.keyboard.press("Enter");
    await page.keyboard.press("Enter");
    assert.equal(await page.evaluate(() => JSON.stringify(window.__traceDashboard)), beforeInspection, "opening map changed observer state");
    assert.equal(await page.locator(".frozen-comparison").textContent(), frozen, "inspection/live signal rewrote frozen comparison");
    assert.equal(await page.locator("#session-hash").textContent(), canonical, "observing map changed canonical state readout");
    assert.deepEqual(outgoing, [], "read-only map sent a command to embedded game");
    assert(requests.every((request) => request.method === "GET"), "read-only map issued a write request");

    await send(event(explanation({ checks: { evaluated: null, skipped: null, out_of_scope: null, unreported: null, consistent: null }, state_effect: {}, engine: { seq: 2 } }), 2));
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 2);
    if (valid) {
      const text = await observed("trace").textContent();
      assert(text.includes("missing/unreported") && !text.includes(HASH_B), "partial event retained previous complete evidence");
      assert(!/\bpass\b/.test(text), "unreported checks became passed");
    }
    await send(event(explanation({ schema_id: "invalid-schema", actor_id: attack, input: { operation: attack, actor_role: attack, subject_type: attack } }), 3));
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 3);
    if (valid) for (const role of roles) assert((await observed(role).textContent()).includes("missing/unreported"), `${role} did not clear malformed live evidence`);
    assert(!(await page.locator("#semantic-explanation").textContent()).includes(attack));
    await send({ channel: "trace-rpg-dashboard", kind: "session", seq: 4, payload: { scenario_id: "sealed_lighthouse", sites: [], state_sha256: HASH_A, revision: 0, stage: 0, commit_count: 0, refusal_count: 0, fact_count: 0 } });
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 0);
    if (valid) for (const role of roles) assert((await observed(role).textContent()).includes("missing/unreported"), `${role} did not reset with session`);
    await measureMobileLayout("reset");
    assert.equal(await page.locator(".frozen-comparison").textContent(), frozen);
    assert.deepEqual(pageErrors, [], "map failure escaped local boundary");
    console.log(JSON.stringify({ fixture: "isolated component transport; NOT actual gameplay", mode: config.mode, width: config.width, roles: valid ? roles.length : 0, result: "pass", mobileLayout }));
  } finally {
    await browser.close();
  }
}
main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
