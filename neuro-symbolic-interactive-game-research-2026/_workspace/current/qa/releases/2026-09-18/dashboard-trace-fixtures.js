/* D-073 dashboard per-node evaluation trace: synthetic-fixture regression.
 *
 * Runs INSIDE the dashboard page (puppeteer `page.evaluate(source)` or paste into
 * the console) after `/dashboard/` is served from P/game-track/web with
 * `python3 -m http.server`. It replaces the embedded game frame with a blank
 * same-origin `srcdoc` page and posts synthetic envelopes from that frame, so the
 * page's source/origin guard (event.source === game.contentWindow &&
 * event.origin === location.origin) is exercised exactly as the real export
 * exercises it. Nothing here touches canonical state; this is an engineering
 * regression of the renderer, not efficacy or usability evidence.
 *
 * Driver note: run it in an UNPATCHED Chromium (e.g. puppeteer's
 * chrome-headless-shell started with --remote-debugging-port). Stealth-patched
 * browsers proxy HTMLIFrameElement.prototype.contentWindow, so
 * `event.source === game.contentWindow` can never hold there and every envelope
 * is (correctly) rejected by the guard.
 *
 * Returns a Promise resolving to {fixtures:[...], guards:[...], settled, passed}.
 * Console errors are captured by the driver (see dashboard-trace-fixtures.json
 * "console"); fixture (g) is the only one allowed to log a console.error.
 */
(async () => {
  const FAMILIES = ["POLICY", "PRECONDITION", "REACHABILITY", "KNOWLEDGE", "DISCLOSURE", "QUEST STAGE"];
  const GATE = {
    FORBIDDEN_DISCLOSURE: "DISCLOSURE",
    STAGE_GATED_DISCLOSURE: "DISCLOSURE/QUEST STAGE",
    MISSING_REQUIRED_OBJECT: "PRECONDITION",
    QUEST_STAGE_PRECONDITION: "QUEST STAGE",
    OBJECT_NOT_PRESENT: "REACHABILITY",
    OBJECT_NOT_REACHABLE: "REACHABILITY",
    NPC_DOES_NOT_KNOW_FACT: "KNOWLEDGE",
    UNKNOWN_ACTOR: "POLICY",
    UNKNOWN_OPERATION: "POLICY",
  };
  const SHA = (n) => `${String(n).padStart(2, "0")}`.repeat(32);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const dash = window.__traceDashboard;
  const eventsBefore = dash.events.length;

  // Mirror of game_3d.gd::dashboard_trace so fixtures carry the exact engine shape.
  function engineTrace(trace, plan, overrides = {}) {
    const checks = [], evaluatedGates = [], evaluatedCodes = [];
    let heldAt = "";
    const fs = {};
    const fam = (gate) => gate.split("/").map((s) => s.trim()).filter((f) => FAMILIES.includes(f));
    for (const [code, outcome] of trace) {
      const gate = GATE[code];
      checks.push({ code, gate, outcome });
      evaluatedCodes.push(code);
      if (!evaluatedGates.includes(gate)) evaluatedGates.push(gate);
      if (outcome === "fail" && !heldAt) heldAt = code;
      for (const f of fam(gate)) if (outcome === "fail" || !(f in fs)) fs[f] = outcome;
    }
    const skipped = [];
    for (const code of plan) {
      if (evaluatedCodes.includes(code)) continue;
      const gate = GATE[code];
      skipped.push({ code, gate });
      for (const f of fam(gate)) if (!(f in fs)) fs[f] = "skipped";
    }
    const outOfScope = [];
    for (const f of FAMILIES) if (!(f in fs)) { fs[f] = "out_of_scope"; outOfScope.push(f); }
    const family_states = { ...fs };
    for (const f of overrides.drop || []) delete family_states[f];
    return { checks, evaluated_gates: evaluatedGates, held_at: heldAt, short_circuit: heldAt !== "", skipped, out_of_scope: outOfScope, family_states };
  }

  // --- swap the game frame for a blank same-origin emitter -------------------
  const frame = document.getElementById("game");
  const loaded = new Promise((r) => frame.addEventListener("load", r, { once: true }));
  frame.srcdoc = `<!doctype html><script>window.emit = function (e) { window.parent.postMessage(e, "*"); };</script><body>fixture emitter</body>`;
  await loaded;
  const emit = frame.contentWindow.emit;
  let seq = 100;
  // postMessage is asynchronous: wait until the dashboard has actually consumed
  // the envelope (its event list grew) before reading the DOM.
  const send = async (kind, payload) => {
    seq += 1;
    const e = { channel: "trace-rpg-dashboard", seq, kind, t_ms: 1000 + seq * 7, engineering_only: true, payload };
    const before = dash.events.length;
    emit(e);
    for (let i = 0; i < 100 && dash.events.length === before; i += 1) await sleep(10);
    if (dash.events.length === before) throw new Error(`envelope ${kind} seq ${seq} was not accepted by the dashboard guard`);
    return e;
  };
  const summary = (n, extra = {}) => ({ state_sha256: SHA(n), revision: n, stage: extra.stage ?? 1, fact_count: extra.facts ?? 1, commit_count: extra.commits ?? 0, refusal_count: extra.holds ?? 0 });

  // --- DOM readers -------------------------------------------------------------
  const nodeState = (id) => document.querySelector(`#nodes .node[data-id="${CSS.escape(id)}"]`).getAttribute("data-state");
  const nodeWord = (id) => document.querySelector(`#nodes .node[data-id="${CSS.escape(id)}"] text.word`).textContent;
  const nodeWeight = (id) => document.querySelector(`#nodes .node[data-id="${CSS.escape(id)}"] text.weight`).textContent;
  const nodeCircle = (id) => document.querySelector(`#nodes .node[data-id="${CSS.escape(id)}"] circle:nth-of-type(2)`);
  const edge = (a, b) => document.querySelector(`#edges path[data-edge="${CSS.escape(`${a}>${b}`)}"]`);
  const edgeKind = (a, b) => edge(a, b).getAttribute("data-kind");
  const legendRows = () => [...document.querySelectorAll("#legend-rows li[data-state]")].map((li) => li.getAttribute("data-state"));
  const renderedStates = () => {
    const s = new Set(FAMILIES.map(nodeState));
    for (const t of ["commit", "hold"]) { const v = nodeState(t); if (v) s.add(v); }
    return [...s];
  };
  const snapshot = () => ({
    states: Object.fromEntries(FAMILIES.map((f) => [f, nodeState(f)])),
    words: Object.fromEntries(FAMILIES.map((f) => [f, nodeWord(f)])),
    weights: Object.fromEntries(Object.keys(dash.nodeWeight).map((id) => [id, nodeWeight(id)])),
    familyEval: JSON.parse(JSON.stringify(dash.familyEval)),
    terminals: { commit: nodeState("commit"), hold: nodeState("hold") },
    edges: Object.fromEntries([...document.querySelectorAll("#edges path")].map((p) => [p.getAttribute("data-edge"), p.getAttribute("data-kind")])),
    legendRows: legendRows(),
    legendCounts: document.getElementById("legend-counts").textContent,
    strip: document.getElementById("last-trace").textContent,
    stamp: document.getElementById("trace-stamp").textContent,
    log: [...document.querySelectorAll("#log div")].slice(-1).map((d) => d.textContent)[0] || "",
    pulses: document.querySelectorAll("#pulses circle").length,
    gateTable: [...document.querySelectorAll("#gate-table tr")].slice(1).map((tr) => [...tr.children].map((td) => td.textContent.trim()).slice(0, 5)),
  });

  const results = [];
  function run(name, checks) {
    const failures = [];
    for (const [label, ok, detail] of checks) if (!ok) failures.push(`${label}${detail === undefined ? "" : `: ${JSON.stringify(detail)}`}`);
    const snap = snapshot();
    const legendOk = renderedStates().every((s) => snap.legendRows.includes(s));
    if (!legendOk) failures.push(`rendered states ${JSON.stringify(renderedStates())} not subset of legend rows ${JSON.stringify(snap.legendRows)}`);
    results.push({ fixture: name, passed: failures.length === 0, failures, rendered_states: renderedStates(), snapshot: snap });
    return failures.length === 0;
  }
  const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
  const statesEq = (expected) => eq(Object.fromEntries(FAMILIES.map((f) => [f, nodeState(f)])), expected);
  const oos = (...evaluated) => Object.fromEntries(FAMILIES.map((f) => [f, evaluated[f] || "out_of_scope"]));
  const S = (obj) => ({ ...oos(), ...obj });

  await send("session", { scenario_id: "sealed_lighthouse", sites: [{ id: "mira", x: 3, z: 11 }], ...summary(0, { stage: 0, facts: 0 }) });

  // (a) acquire_object commit: OBJECT_NOT_PRESENT pass -> OBJECT_NOT_REACHABLE pass
  await send("proposal", { operation: "acquire_object", text: "Take the signal lens" });
  await send("commit", { operation: "acquire_object", labels: ["Signal lens secured"], stage_from: 0, stage_to: 1, state_sha256_before: SHA(0), mutated: true,
    trace: engineTrace([["OBJECT_NOT_PRESENT", "pass"], ["OBJECT_NOT_REACHABLE", "pass"]], ["OBJECT_NOT_PRESENT", "OBJECT_NOT_REACHABLE"]), ...summary(1, { commits: 1 }) });
  run("a_acquire_commit", [
    ["family states", statesEq(S({ REACHABILITY: "pass" })), snapshot().states],
    ["REACHABILITY weight = 2 evaluated checks", nodeWeight("REACHABILITY") === "evaluated x2", nodeWeight("REACHABILITY")],
    ["no other family gained weight", FAMILIES.filter((f) => f !== "REACHABILITY").every((f) => nodeWeight(f) === ""), snapshot().weights],
    ["out-of-scope word", nodeWord("POLICY") === "not evaluated", nodeWord("POLICY")],
    ["out-of-scope hatch fill", nodeCircle("POLICY").getAttribute("fill") === "url(#hatch-oos)"],
    ["pass fill/stroke blue", nodeCircle("REACHABILITY").getAttribute("fill") === "#1d3a55" && nodeCircle("REACHABILITY").getAttribute("stroke") === "#6db3f2"],
    ["commit terminal word", nodeState("commit") === "committed" && nodeState("hold") === ""],
    ["edges: parser>REACHABILITY traversed, REACHABILITY>commit commit, commit>trace commit", edgeKind("parser", "REACHABILITY") === "traversed" && edgeKind("REACHABILITY", "commit") === "commit" && edgeKind("commit", "trace") === "commit"],
    ["edges into out-of-scope families dotted, not animated", edgeKind("parser", "POLICY") === "out_of_scope" && edgeKind("POLICY", "commit") === "schema"],
    ["strip rows", document.getElementById("last-trace").textContent.includes("1  v_reach         OBJECT_NOT_PRESENT        v passed") && document.getElementById("last-trace").textContent.includes("2  v_reach         OBJECT_NOT_REACHABLE      v passed") && document.getElementById("last-trace").textContent.includes("-> COMMIT"), document.getElementById("last-trace").textContent],
    ["strip not-evaluated block", document.getElementById("last-trace").textContent.includes("Not evaluated for acquire_object (out of scope): POLICY, PRECONDITION, KNOWLEDGE, DISCLOSURE, QUEST STAGE")],
    ["strip has no short-circuit rule", !document.getElementById("last-trace").textContent.includes("short-circuit")],
    ["strip stamped with seq/t_ms", document.getElementById("last-trace").textContent.includes(`seq ${seq}  t_ms ${1000 + seq * 7}`)],
    ["legend counts pytest-style", document.getElementById("legend-counts").textContent === "2 passed, 0 failed, 0 skipped (checks), 5 not evaluated (families)", document.getElementById("legend-counts").textContent],
    ["legend rows", eq(legendRows(), ["pass", "out_of_scope", "committed"]), legendRows()],
    ["gate table REACHABILITY evaluated/passed/failed", eq(snapshot().gateTable[2].slice(2), ["2", "2", "0"]), snapshot().gateTable],
  ]);

  // (b) install_lens hold: MISSING_REQUIRED_OBJECT fail; QUEST_STAGE_PRECONDITION skipped
  await send("proposal", { operation: "install_lens", text: "Mount the lens" });
  await send("hold", { codes: ["MISSING_REQUIRED_OBJECT"], gates: ["PRECONDITION"], next_affordance: "Find the signal lens.",
    trace: engineTrace([["MISSING_REQUIRED_OBJECT", "fail"]], ["MISSING_REQUIRED_OBJECT", "QUEST_STAGE_PRECONDITION"]), ...summary(1, { commits: 1, holds: 1 }) });
  run("b_install_hold", [
    ["family states", statesEq(S({ PRECONDITION: "fail", "QUEST STAGE": "skipped" })), snapshot().states],
    ["REACHABILITY reset to out_of_scope for this event", nodeState("REACHABILITY") === "out_of_scope"],
    ["REACHABILITY keeps its earned weight", nodeWeight("REACHABILITY") === "evaluated x2"],
    ["PRECONDITION weight 1", nodeWeight("PRECONDITION") === "evaluated x1"],
    ["QUEST STAGE skipped gained no weight", nodeWeight("QUEST STAGE") === ""],
    ["fail word carries code", nodeWord("PRECONDITION") === "failed MISSING_REQUIRED_OBJECT", nodeWord("PRECONDITION")],
    ["fail stroke coral 3px + ring", nodeCircle("PRECONDITION").getAttribute("stroke") === "#d9685f" && nodeCircle("PRECONDITION").getAttribute("stroke-width") === "3"],
    ["skipped: no fill, dashed 6 3", nodeCircle("QUEST STAGE").getAttribute("fill") === "none" && nodeCircle("QUEST STAGE").getAttribute("stroke-dasharray") === "6 3"],
    ["skipped word", nodeWord("QUEST STAGE") === "skipped"],
    ["hold terminal word", nodeState("hold") === "held" && nodeState("commit") === ""],
    ["edge into failing check settles coral with stop cap", edgeKind("parser", "PRECONDITION") === "fail" && edge("parser", "PRECONDITION").getAttribute("marker-end") === "url(#stop-coral)"],
    ["failing family routes to hold; nothing routes to commit", edgeKind("PRECONDITION", "hold") === "hold" && FAMILIES.every((f) => edgeKind(f, "commit") === "schema")],
    ["edge into skipped family dotted", edgeKind("parser", "QUEST STAGE") === "skipped"],
    ["strip: held at + rule + skipped row", ["-> HELD at MISSING_REQUIRED_OBJECT", "1  v_pre           MISSING_REQUIRED_OBJECT   x failed", "== short-circuit here: remaining in-scope checks were not run ==", "2  v_quest         QUEST_STAGE_PRECONDITION  ->| skipped", "Not evaluated for install_lens (out of scope): POLICY, REACHABILITY, KNOWLEDGE, DISCLOSURE"].every((s) => document.getElementById("last-trace").textContent.includes(s)), document.getElementById("last-trace").textContent],
    ["legend counts", document.getElementById("legend-counts").textContent === "0 passed, 1 failed, 1 skipped (checks), 4 not evaluated (families)", document.getElementById("legend-counts").textContent],
    ["legend rows", eq(legendRows(), ["fail", "skipped", "out_of_scope", "held"]), legendRows()],
    ["holds by gate PRECONDITION = 1", dash.holdsByGate.PRECONDITION === 1],
    ["log line carries trace summary", snapshot().log.includes("trace MISSING_REQUIRED_OBJECT:fail > short-circuit at MISSING_REQUIRED_OBJECT"), snapshot().log],
  ]);

  // (c) reveal_hint hold: FORBIDDEN_DISCLOSURE pass, STAGE_GATED_DISCLOSURE fail; actor/knowledge skipped
  await send("proposal", { operation: "reveal_hint", text: "Ask Mira about the tide marks" });
  await send("hold", { codes: ["STAGE_GATED_DISCLOSURE"], gates: ["DISCLOSURE/QUEST STAGE"], next_affordance: "Mount the lens first.",
    trace: engineTrace([["FORBIDDEN_DISCLOSURE", "pass"], ["STAGE_GATED_DISCLOSURE", "fail"]], ["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE", "UNKNOWN_ACTOR", "NPC_DOES_NOT_KNOW_FACT"]), ...summary(1, { commits: 1, holds: 2 }) });
  run("c_reveal_hint_hold", [
    ["family states", statesEq(S({ DISCLOSURE: "fail", "QUEST STAGE": "fail", POLICY: "skipped", KNOWLEDGE: "skipped" })), snapshot().states],
    ["DISCLOSURE weight 2 (both disclosure checks), QUEST STAGE 1", nodeWeight("DISCLOSURE") === "evaluated x2" && nodeWeight("QUEST STAGE") === "evaluated x1", snapshot().weights],
    ["composite gate fails both families to hold", edgeKind("DISCLOSURE", "hold") === "hold" && edgeKind("QUEST STAGE", "hold") === "hold"],
    ["skipped families not routed", edgeKind("parser", "POLICY") === "skipped" && edgeKind("parser", "KNOWLEDGE") === "skipped" && edgeKind("POLICY", "hold") === "schema"],
    ["strip", ["1  v_disc          FORBIDDEN_DISCLOSURE      v passed", "2  v_disc/v_quest  STAGE_GATED_DISCLOSURE    x failed", "== short-circuit here", "3  v_policy        UNKNOWN_ACTOR             ->| skipped", "4  v_know          NPC_DOES_NOT_KNOW_FACT    ->| skipped", "-> HELD at STAGE_GATED_DISCLOSURE", "Not evaluated for reveal_hint (out of scope): PRECONDITION, REACHABILITY"].every((s) => document.getElementById("last-trace").textContent.includes(s)), document.getElementById("last-trace").textContent],
    ["legend counts", document.getElementById("legend-counts").textContent === "1 passed, 1 failed, 2 skipped (checks), 2 not evaluated (families)", document.getElementById("legend-counts").textContent],
    ["fail word names the composite code", nodeWord("DISCLOSURE") === "failed STAGE_GATED_DISCLOSURE" && nodeWord("QUEST STAGE") === "failed STAGE_GATED_DISCLOSURE"],
  ]);

  // (d) early-secret hold (top-level validate_disclosure after a dialogue choice, no proposal envelope)
  await send("dialogue", { phase: "choice", npc: "captain_mira", choice_id: "ask_secret" });
  await send("hold", { codes: ["FORBIDDEN_DISCLOSURE"], gates: ["DISCLOSURE"], next_affordance: "Find the signal lens.",
    trace: engineTrace([["FORBIDDEN_DISCLOSURE", "fail"], ["STAGE_GATED_DISCLOSURE", "pass"]], ["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE"]), ...summary(1, { commits: 1, holds: 3 }) });
  run("d_early_secret_hold", [
    ["family states (fail wins over a later pass in the same family)", statesEq(S({ DISCLOSURE: "fail", "QUEST STAGE": "pass" })), snapshot().states],
    ["weights DISCLOSURE 4, QUEST STAGE 2", nodeWeight("DISCLOSURE") === "evaluated x4" && nodeWeight("QUEST STAGE") === "evaluated x2", snapshot().weights],
    ["strip names the dialogue choice as the operation", document.getElementById("last-trace").textContent.includes("last proposal: ask_secret"), document.getElementById("last-trace").textContent],
    ["strip: rule after last executed check, held-at note", ["1  v_disc          FORBIDDEN_DISCLOSURE      x failed", "2  v_disc/v_quest  STAGE_GATED_DISCLOSURE    v passed", "== short-circuit here", "(held at #1 FORBIDDEN_DISCLOSURE; the disclosure pair is always evaluated together)", "-> HELD at FORBIDDEN_DISCLOSURE"].every((s) => document.getElementById("last-trace").textContent.includes(s))],
    ["rule comes after row 2, not between rows", document.getElementById("last-trace").textContent.indexOf("== short-circuit") > document.getElementById("last-trace").textContent.indexOf("STAGE_GATED_DISCLOSURE    v passed")],
    ["passing QUEST STAGE does not route anywhere on a hold", edgeKind("parser", "QUEST STAGE") === "traversed" && edgeKind("QUEST STAGE", "commit") === "schema" && edgeKind("QUEST STAGE", "hold") === "schema"],
    ["DISCLOSURE routes to hold", edgeKind("DISCLOSURE", "hold") === "hold" && edgeKind("parser", "DISCLOSURE") === "fail"],
    ["legend counts", document.getElementById("legend-counts").textContent === "1 passed, 1 failed, 0 skipped (checks), 4 not evaluated (families)", document.getElementById("legend-counts").textContent],
    ["legend rows", eq(legendRows(), ["pass", "fail", "out_of_scope", "held"]), legendRows()],
  ]);

  // (e) reveal_hint commit with all four checks passing
  await send("proposal", { operation: "reveal_hint", text: "Ask Mira about the tide marks" });
  await send("commit", { operation: "reveal_hint", labels: ["Tide-marks lead recorded"], stage_from: 2, stage_to: 3, state_sha256_before: SHA(1), mutated: true,
    trace: engineTrace([["FORBIDDEN_DISCLOSURE", "pass"], ["STAGE_GATED_DISCLOSURE", "pass"], ["UNKNOWN_ACTOR", "pass"], ["NPC_DOES_NOT_KNOW_FACT", "pass"]], ["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE", "UNKNOWN_ACTOR", "NPC_DOES_NOT_KNOW_FACT"]), ...summary(2, { stage: 3, facts: 3, commits: 2, holds: 3 }) });
  run("e_reveal_hint_commit", [
    ["family states", statesEq(S({ DISCLOSURE: "pass", "QUEST STAGE": "pass", POLICY: "pass", KNOWLEDGE: "pass" })), snapshot().states],
    ["weights", eq([nodeWeight("DISCLOSURE"), nodeWeight("QUEST STAGE"), nodeWeight("POLICY"), nodeWeight("KNOWLEDGE"), nodeWeight("PRECONDITION"), nodeWeight("REACHABILITY")], ["evaluated x6", "evaluated x3", "evaluated x1", "evaluated x1", "evaluated x1", "evaluated x2"]), snapshot().weights],
    ["all four passing families route to commit; PRECONDITION/REACHABILITY do not", ["POLICY", "KNOWLEDGE", "DISCLOSURE", "QUEST STAGE"].every((f) => edgeKind(f, "commit") === "commit") && edgeKind("PRECONDITION", "commit") === "schema" && edgeKind("REACHABILITY", "commit") === "schema"],
    ["previous hold cleared", nodeState("hold") === "" && nodeState("commit") === "committed" && edgeKind("DISCLOSURE", "hold") === "schema"],
    ["strip", ["-> COMMIT", "3  v_policy        UNKNOWN_ACTOR             v passed", "4  v_know          NPC_DOES_NOT_KNOW_FACT    v passed", "Not evaluated for reveal_hint (out of scope): PRECONDITION, REACHABILITY"].every((s) => document.getElementById("last-trace").textContent.includes(s)) && !document.getElementById("last-trace").textContent.includes("short-circuit")],
    ["legend counts", document.getElementById("legend-counts").textContent === "4 passed, 0 failed, 0 skipped (checks), 2 not evaluated (families)", document.getElementById("legend-counts").textContent],
    ["stamp carries seq and verdict", document.getElementById("trace-stamp").textContent.includes(`seq ${seq}`) && document.getElementById("trace-stamp").textContent.includes("reveal_hint -> committed"), document.getElementById("trace-stamp").textContent],
    ["gate table DISCLOSURE evaluated/passed/failed 6/4/2", eq(snapshot().gateTable[4].slice(2), ["6", "4", "2"]), snapshot().gateTable],
  ]);

  // (f) legacy commit without trace (pre-D-073 build)
  const weightsBefore = Object.fromEntries(FAMILIES.map((f) => [f, nodeWeight(f)]));
  await send("proposal", { operation: "acquire_object", text: "Take the signal lens (legacy build)" });
  await send("commit", { operation: "acquire_object", labels: [], stage_from: 3, stage_to: 3, state_sha256_before: SHA(2), mutated: true, ...summary(3, { stage: 3, facts: 3, commits: 3, holds: 3 }) });
  run("f_legacy_commit_no_trace", [
    ["every family in legacy state, never pass", FAMILIES.every((f) => nodeState(f) === "legacy"), snapshot().states],
    ["family weights unchanged by a schema-only envelope", eq(Object.fromEntries(FAMILIES.map((f) => [f, nodeWeight(f)])), weightsBefore)],
    ["legacy word", nodeWord("POLICY") === "no trace (legacy)"],
    ["log tagged legacy: schema-only", snapshot().log.includes("legacy: schema-only"), snapshot().log],
    ["strip says legacy", document.getElementById("last-trace").textContent.includes("legacy: schema-only envelope (no trace)") && document.getElementById("last-trace").textContent.includes("not evaluated for acquire_object: unknown (no trace)")],
    ["legend rows legacy + committed", eq(legendRows(), ["legacy", "committed"]), legendRows()],
    ["legend counts say no per-check counts", document.getElementById("legend-counts").textContent.startsWith("legacy: schema-only envelope, no per-check counts")],
    ["legacy edges amber-dashed, not traversed/commit", edgeKind("parser", "POLICY") === "legacy" && edgeKind("POLICY", "commit") === "legacy" && edgeKind("commit", "trace") === "commit"],
    ["legacyEvents = 1, no trace errors", dash.legacyEvents === 1 && dash.traceErrors === 0],
  ]);

  // (g) install hold with family_states missing KNOWLEDGE -> "state missing" + one console.error
  await send("proposal", { operation: "install_lens", text: "Mount the lens (malformed trace)" });
  await send("hold", { codes: ["MISSING_REQUIRED_OBJECT"], gates: ["PRECONDITION"], next_affordance: "Find the signal lens.",
    trace: engineTrace([["MISSING_REQUIRED_OBJECT", "fail"]], ["MISSING_REQUIRED_OBJECT", "QUEST_STAGE_PRECONDITION"], { drop: ["KNOWLEDGE"] }), ...summary(3, { stage: 3, facts: 3, commits: 3, holds: 4 }) });
  run("g_hold_missing_family_state", [
    ["KNOWLEDGE renders state missing, others from payload", statesEq(S({ PRECONDITION: "fail", "QUEST STAGE": "skipped", KNOWLEDGE: "missing" })), snapshot().states],
    ["missing word + amber stroke + ring", nodeWord("KNOWLEDGE") === "state missing" && nodeCircle("KNOWLEDGE").getAttribute("stroke") === "#f2b84b"],
    ["traceErrors incremented exactly once", dash.traceErrors === 1],
    ["strip flags the missing state", document.getElementById("last-trace").textContent.includes('! state missing from payload: KNOWLEDGE (rendered "state missing", not a pass)')],
    ["legend counts flag the missing state", document.getElementById("legend-counts").textContent === "0 passed, 1 failed, 1 skipped (checks), 3 not evaluated (families), 1 state missing", document.getElementById("legend-counts").textContent],
    ["legend rows include missing", eq(legendRows(), ["fail", "skipped", "out_of_scope", "missing", "held"]), legendRows()],
    ["missing family edge left as schema (no evidence either way)", edgeKind("parser", "KNOWLEDGE") === "schema"],
  ]);

  // --- reduced motion: evidence must survive without motion -----------------------
  // Only meaningful when the driver reloaded the page under
  // prefers-reduced-motion: reduce; otherwise recorded as not applicable.
  const reduced = dash.reducedMotion;
  results.push({ fixture: "h_reduced_motion_substitutes_weight", applicable: reduced, passed: !reduced || (document.querySelectorAll("#pulses circle").length === 0 && edge("parser", "PRECONDITION").getAttribute("stroke-width") === "4" && edgeKind("parser", "PRECONDITION") === "fail"), failures: [], rendered_states: renderedStates(), snapshot: { reducedMotion: reduced, pulses: document.querySelectorAll("#pulses circle").length, failEdgeWidth: edge("parser", "PRECONDITION").getAttribute("stroke-width") } });

  // --- guards --------------------------------------------------------------------
  const guards = [];
  const before = dash.events.length;
  window.postMessage({ channel: "trace-rpg-dashboard", seq: 999, kind: "commit", t_ms: 0, engineering_only: true, payload: { operation: "acquire_object", labels: [], stage_from: 0, stage_to: 1, state_sha256_before: SHA(9), trace: engineTrace([["OBJECT_NOT_PRESENT", "pass"]], []), ...summary(9) } }, "*");
  await sleep(50);
  guards.push({ guard: "parent-window source rejected", passed: dash.events.length === before && nodeState("REACHABILITY") !== "pass" });
  emit({ channel: "not-the-dashboard", seq: 998, kind: "commit", payload: {} });
  await sleep(50);
  guards.push({ guard: "foreign channel from the game frame rejected", passed: dash.events.length === before });

  await sleep(2600);
  const settled = { pulses_remaining: document.querySelectorAll("#pulses circle").length, events_total: dash.events.length, events_before: eventsBefore, counts: dash.counts, holdsByGate: dash.holdsByGate, reducedMotion: dash.reducedMotion };
  return { fixtures: results, guards, settled, passed: results.every((r) => r.passed) && guards.every((g) => g.passed) };
})();
