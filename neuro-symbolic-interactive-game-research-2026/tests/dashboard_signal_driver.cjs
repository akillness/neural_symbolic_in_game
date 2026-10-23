"use strict";

const { chromium } = require("playwright");

const baseUrl = process.env.SIGNAL_DASHBOARD_BASE_URL;
if (!baseUrl) throw new Error("SIGNAL_DASHBOARD_BASE_URL is required");

const HASH_A = "a".repeat(64);
const HASH_B = "b".repeat(64);

const explanation = (overrides = {}) => ({
  schema_id: "trace-rpg-semantic-explanation",
  schema_version: "1.0.0",
  input: { operation: "reveal_hint", actor_role: "captain", subject_type: "lead" },
  ontology: { relation: "captain_to_lead_disclosure", rule_ids: ["DISC-005"] },
  checks: {
    evaluated: [{ code: "NPC_DOES_NOT_KNOW_FACT", gate: "DISCLOSURE", outcome: "pass" }],
    skipped: [], out_of_scope: [], consistent: true,
  },
  decision: { outcome: "authorized_fresh", accepted: true, result_codes: [] },
  state_effect: { kind: "fresh_disclosure", mutated: true, prior_state_hash: HASH_A, next_state_hash: HASH_B },
  engine: { seq: 1, t_ms: 100 },
  ...overrides,
});

async function main() {
  const browser = await chromium.launch({ headless: true, executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || undefined });
  try {
    const page = await browser.newPage();
    await page.goto(`${baseUrl}/dashboard/index.html`, { waitUntil: "domcontentloaded" });
    await page.waitForFunction(() => document.querySelector("#comparison-status")?.textContent.includes("frozen independent lane"));

    const initial = await page.evaluate(() => ({
      status: document.querySelector("#disclosure-live-status").textContent,
      clock: document.querySelector("#timeline-clock").textContent,
      events: document.querySelector("#disclosure-events").textContent,
      comparison: document.querySelector("#comparison-status").textContent,
      comparisonPanel: document.querySelector(".frozen-comparison").textContent,
      matrix: document.querySelector("#comparison-matrix").textContent,
      body: document.body.textContent,
      geometry: Array.from(document.querySelectorAll("#comparison-graph rect"), (node) => ({
        x: Number(node.getAttribute("x")),
        width: Number(node.getAttribute("width")),
      })),
      metricLabels: Array.from(document.querySelectorAll("#comparison-graph text"), (node) => ({
        x: Number(node.getAttribute("x")),
        text: node.textContent,
      })),
    }));
    if (!initial.body.includes("engineering demonstration") || !initial.body.includes("not evidence")) throw new Error("synthetic renderer is not labelled engineering-only");
    if (!initial.status.includes("waiting for disclosure events")) throw new Error(`unexpected initial status: ${initial.status}`);
    if (!initial.clock.includes("engine clock: waiting")) throw new Error(`unexpected initial clock: ${initial.clock}`);
    if (!initial.events.includes("Waiting for disclosure_outcome")) throw new Error("empty live timeline did not remain explicit");
    if (!initial.comparison.includes("N=48") || !initial.comparison.includes("B=4") || !initial.comparison.includes("M=8")) throw new Error(`denominators missing: ${initial.comparison}`);
    if (!initial.comparisonPanel.includes("engineering-only fixture agreement") || !initial.comparisonPanel.includes("not ontology superiority") || !initial.comparisonPanel.includes("not a live trend or game result")) throw new Error("comparison claim boundary is not scoped to frozen panel");
    if (!initial.matrix.includes("reported") || !initial.matrix.includes("unreported")) throw new Error(`frozen matrix missing report-status distinctions: ${initial.matrix}`);
    if (!initial.geometry.length || initial.geometry.some(({ x, width }) => x !== 245 || !Number.isFinite(width) || width < 0 || width > 640 - 245)) throw new Error(`comparison geometry is off-canvas: ${JSON.stringify(initial.geometry)}`);
    if (!initial.geometry.some(({ width }) => width === 0)) throw new Error(`true-zero metric was given a minimum width: ${JSON.stringify(initial.geometry)}`);
    if (!initial.metricLabels.some(({ x, text }) => x === 130 && text.includes("unsafe"))) throw new Error(`metric labels are not anchored at x=130: ${JSON.stringify(initial.metricLabels)}`);

    const frame = page.frames().find((candidate) => candidate.url().includes("/public/index.html"));
    if (!frame) throw new Error("embedded game frame did not load");
    const send = async (message) => frame.evaluate((value) => window.parent.postMessage(value, location.origin), message);
    const rejectedEnvelope = { channel: "trace-rpg-dashboard", kind: "disclosure_outcome", seq: 5, t_ms: 500, payload: { explanation: explanation() } };
    await page.evaluate((data) => new Promise((resolve) => {
      const handler = () => { window.removeEventListener("message", handler); queueMicrotask(resolve); };
      window.addEventListener("message", handler);
      window.postMessage(data, location.origin);
    }), rejectedEnvelope);
    await page.evaluate((data) => {
      const frameWindow = document.querySelector("iframe")?.contentWindow || window;
      window.dispatchEvent(new MessageEvent("message", { data, origin: "https://foreign.invalid", source: frameWindow }));
    }, rejectedEnvelope);
    const rejectedCount = await page.evaluate(() => document.querySelectorAll("#disclosure-events .disclosure-event").length);
    if (rejectedCount !== 0) throw new Error(`foreign/source-mismatched event was accepted: ${rejectedCount}`);

    await send({ channel: "trace-rpg-dashboard", kind: "disclosure_outcome", seq: 20, t_ms: 2000, payload: { explanation: explanation({ engine: { seq: 20, t_ms: 2000 } }) } });
    await send({ channel: "trace-rpg-dashboard", kind: "disclosure_replay", seq: 10, t_ms: 1000, payload: { explanation: explanation({ engine: { seq: 10, t_ms: 1000 }, decision: { outcome: "authorized_redisplay", accepted: true, result_codes: [] }, state_effect: { kind: "redisplay_no_mutation", mutated: false, prior_state_hash: HASH_A, next_state_hash: HASH_A } }) } });
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 2);

    const known = await page.evaluate(() => ({
      status: document.querySelector("#disclosure-live-status").textContent,
      clock: document.querySelector("#timeline-clock").textContent,
      events: Array.from(document.querySelectorAll("#disclosure-events .disclosure-event"), (node) => node.textContent),
      semantic: document.querySelector("#semantic-explanation").textContent,
      comparisonPanel: document.querySelector(".frozen-comparison").textContent,
      body: document.body.textContent,
    }));
    if (!known.status.includes("2 disclosure signals")) throw new Error(`event count missing: ${known.status}`);
    if (!known.clock.includes("1000–2000")) throw new Error(`engine chronology missing: ${known.clock}`);
    if (!known.events[0].includes("seq 10") || !known.events[1].includes("seq 20")) throw new Error(`events not engine-ordered: ${JSON.stringify(known.events)}`);
    if (!known.semantic.includes("authorized_redisplay")) throw new Error("latest semantic event was not rendered");
    if (known.comparisonPanel.includes("authorized_redisplay") || !known.comparisonPanel.includes("not a live trend")) throw new Error("live event leaked into frozen comparison claim scope");
    if (known.body.includes("captain_mira") || known.body.includes("dock_saved")) throw new Error("hidden actor/fact ID leaked into dashboard text");
    await send({
      channel: "trace-rpg-dashboard", kind: "disclosure_outcome", seq: 30, t_ms: 3000,
      payload: { explanation: explanation({
        actor_id: "captain_mira", fact_id: "dock_saved",
        input: { operation: "reveal_hint", actor_role: { secret: "captain_mira" }, subject_type: null },
        ontology: { relation: "ontology_superior", rule_ids: ["ontology_superior"] },
        checks: { evaluated: [{ code: "ontology_superior", gate: "disclosure", outcome: "maybe" }], skipped: "bad", out_of_scope: [{}], consistent: "yes" },
        decision: { outcome: "ontology_superior", accepted: "yes", result_codes: ["ontology_superior"] },
        state_effect: { kind: "???", mutated: "yes", prior_state_hash: "raw-state", next_state_hash: "raw-state" },
        engine: { seq: "not-a-number", t_ms: Infinity },
      }) } });
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 3);
    const malformed = await page.evaluate(() => ({ semantic: document.querySelector("#semantic-explanation").textContent, body: document.body.textContent }));
    if (!malformed.semantic.includes("unknown")) throw new Error("malformed explanation was not fail-closed as unknown");
    if (malformed.body.includes("ontology_superior") || malformed.body.includes("captain_mira") || malformed.body.includes("dock_saved") || malformed.body.includes("raw_hidden_rule") || malformed.body.includes("raw-state") || malformed.body.includes("raw_fact_id")) throw new Error("malformed or malicious semantic values leaked");
    await send({
      channel: "trace-rpg-dashboard", kind: "disclosure_outcome", seq: 40,
      payload: { explanation: explanation({
        checks: {
          evaluated: [{ code: "DISC-CHECK-001-POLICY", gate: "disclosure", outcome: "pass" }],
          skipped: null, out_of_scope: null,
          unreported: [{ code: "DISC-007", gate: "disclosure", outcome: "pass" }],
          consistent: false,
        },
        engine: { seq: 40 },
      }) },
    });
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 4);
    const partial = await page.evaluate(() => ({
      semantic: document.querySelector("#semantic-explanation").textContent,
      checks: document.querySelector("#semantic-explanation article:nth-child(3)").textContent,
      event: document.querySelector("#disclosure-events .disclosure-event:last-child").textContent,
      state: document.querySelector("#semantic-explanation article:nth-child(3)").dataset.state,
      svg: Array.from(document.querySelectorAll("#disclosure-timeline [x], #disclosure-timeline [y], #disclosure-timeline [x1], #disclosure-timeline [y1], #disclosure-timeline [x2], #disclosure-timeline [y2], #disclosure-timeline [cx], #disclosure-timeline [cy]")).map((node) => ({
        x: ["x", "x1", "x2", "cx"].map((name) => node.getAttribute(name)).filter((value) => value !== null),
        y: ["y", "y1", "y2", "cy"].map((name) => node.getAttribute(name)).filter((value) => value !== null),
      })),
    }));
    if (partial.state !== "unknown" || !partial.semantic.includes("consistent: false")) throw new Error(`unreported consistency was not unknown: ${JSON.stringify(partial)}`);
    if (!partial.checks.includes("1 unreported") || !partial.checks.includes("unknown")) throw new Error(`missing arrays were treated as zero: ${partial.checks}`);
    if (!partial.event.includes("t_ms unknown") || !partial.event.includes("1 unreported")) throw new Error(`partial engine clock or unreported count missing: ${partial.event}`);
    for (const point of partial.svg) {
      for (const value of [...point.x, ...point.y]) {
        const number = Number(value);
        if (!Number.isFinite(number)) throw new Error(`timeline geometry is non-finite: ${value}`);
      }
      for (const value of point.x) if (Number(value) < 0 || Number(value) > 1000) throw new Error(`timeline x is off-canvas: ${value}`);
      for (const value of point.y) if (Number(value) < 0 || Number(value) > 200) throw new Error(`timeline y is off-canvas: ${value}`);
    }
    await send({
      channel: "trace-rpg-dashboard", kind: "disclosure_outcome", seq: 50, t_ms: 4000,
      payload: { explanation: explanation({ schema_id: "wrong-schema", schema_version: "9.9.9" }) },
    });
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 5);
    const wrongSchema = await page.evaluate(() => document.querySelector("#semantic-explanation").textContent);
    if (!wrongSchema.includes("unknown") || wrongSchema.includes("authorized_fresh") || wrongSchema.includes("captain_to_lead_disclosure")) throw new Error("schema mismatch did not fail closed");

    await send({ channel: "trace-rpg-dashboard", kind: "session", seq: 99, payload: { scenario_id: "sealed_lighthouse", sites: [], state_sha256: HASH_A, revision: 0, stage: 0, commit_count: 0, refusal_count: 0, fact_count: 0 } });
    await page.waitForFunction(() => document.querySelectorAll("#disclosure-events .disclosure-event").length === 0);
    const reset = await page.evaluate(() => ({ status: document.querySelector("#disclosure-live-status").textContent, events: document.querySelector("#disclosure-events").textContent, comparison: document.querySelector("#comparison-status").textContent }));
    if (!reset.status.includes("waiting for disclosure events") || !reset.events.includes("Waiting for disclosure_outcome")) throw new Error("session reset did not clear live disclosure state");
    if (!reset.comparison.includes("frozen independent lane")) throw new Error("session reset erased frozen denominator lane");
  } finally {
    await browser.close();
  }
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
