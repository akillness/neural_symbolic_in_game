/* TRACE-RPG live commit-gate dashboard.
 *
 * Presentation-only consumer of the game's postMessage mirror (D-065). It draws an
 * AgentSight-style weighted pipeline ("commit nebula") as a per-proposal
 * evaluation trace (D-073), a `top`-like metrics panel bound to the paper's
 * predicate families, an event timeline, and a harbor mini-map. Nothing here can
 * propose, repair, or commit; it renders what the hard writer already returned.
 * Exposed as window.__traceDashboard for browser automation.
 *
 * Trace contract (engine `game_3d.gd::dashboard_trace`, attached as `payload.trace`
 * on `commit` and `hold` envelopes):
 *   checks:          [{code, gate, outcome: "pass"|"fail"}...]  in execution order
 *   evaluated_gates: [gate...]                                   families consulted
 *   held_at:         <code> or ""                                first failing check
 *   short_circuit:   bool                                        engine stopped early
 *   skipped:         [{code, gate}...]   in-scope checks never reached after the hold
 *   out_of_scope:    [family...]         families never consulted for this operation
 *   family_states:   {FAMILY: "pass"|"fail"|"skipped"|"out_of_scope"}  every family,
 *                    exactly one explicit state, no default
 * Rules (Aside deep research 2026-09-18, P/_workspace/current/intake/
 * aside-research-2026-09-18-commit-gate-trace-encoding.md):
 *   - node state follows explicit `family_states`, unless a check outcome is
 *     unreported. Missing/unknown evidence renders "state missing" and logs
 *     console.error, never a neutral or a pass;
 *   - only edges the engine actually traversed animate; the settled stroke, not the
 *     motion, carries the evidence; prefers-reduced-motion substitutes weight for
 *     motion instead of deleting the evidence;
 *   - green/coral are verdict colours reserved for COMMIT/HOLD and the timeline;
 *     pass is blue, fail is coral + ring, skipped is dashed/no fill, out of scope
 *     is hatched;
 *   - legend rows are generated from the states present in the current event with
 *     pytest-style separate counts, never a ratio over the six families.
 * Envelopes without `payload.trace` (builds older than D-073) fall back to the
 * schema-only pulse of D-065 and are tagged `legacy: schema-only` in the feed.
 */
(() => {
  "use strict";
  const CHANNEL = "trace-rpg-dashboard";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const FAMILIES = ["POLICY", "PRECONDITION", "REACHABILITY", "KNOWLEDGE", "DISCLOSURE", "QUEST STAGE"];
  const COLORS = {
    amber: "#f2b84b", coral: "#d9685f", green: "#6fcf8a", blue: "#6db3f2", blueFill: "#1d3a55",
    muted: "#8fa3b2", gray: "#7d8a95", faint: "#3a4653", line: "#22303d", ink: "#d9d3c4", card: "#0e161f",
  };
  // Node encodings: colour + glyph + word on every node (WCAG 1.4.1 double encoding).
  const STATE_STYLE = {
    pass: { fill: COLORS.blueFill, stroke: COLORS.blue, width: 2, dash: "", glyph: "v", word: "passed", ring: false },
    fail: { fill: "#3a1f1c", stroke: COLORS.coral, width: 3, dash: "", glyph: "x", word: "failed", ring: true },
    skipped: { fill: "none", stroke: COLORS.gray, width: 2, dash: "6 3", glyph: "->|", word: "skipped", ring: false },
    out_of_scope: { fill: "url(#hatch-oos)", stroke: COLORS.gray, width: 1.5, dash: "", glyph: "n/a", word: "not evaluated", ring: false },
    missing: { fill: "#4a3a10", stroke: COLORS.amber, width: 3, dash: "2 2", glyph: "!", word: "state missing", ring: true },
    legacy: { fill: "none", stroke: COLORS.amber, width: 1.5, dash: "3 3", glyph: "?", word: "no trace (legacy)", ring: false },
    idle: { fill: COLORS.card, stroke: COLORS.muted, width: 1.5, dash: "", glyph: "", word: "no trace yet", ring: false },
  };
  const LEGEND_WORD = {
    pass: "evaluated and passed",
    fail: "evaluated and failed (held, state unchanged)",
    skipped: "skipped: in scope, not run after the hold (short-circuit)",
    out_of_scope: "not evaluated: out of scope for this operation type",
    missing: "state missing from payload (renderer refuses to guess)",
    legacy: "legacy envelope without trace: no per-check evidence",
  };
  const VERDICT_STYLE = {
    commit: { fill: "#173a25", stroke: COLORS.green, width: 3, dash: "", glyph: "", word: "committed", ring: false },
    hold: { fill: "#3a1f1c", stroke: COLORS.coral, width: 3, dash: "", glyph: "", word: "held", ring: true },
    terminal_idle: { fill: COLORS.card, stroke: COLORS.muted, width: 1.5, dash: "", glyph: "", word: "", ring: false },
  };
  const REDUCED_MOTION = typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const state = {
    connected: false,
    session: null,
    reference: null,
    counts: { commits: 0, holds: 0, proposals: 0, dialogues: 0 },
    holdsByGate: Object.fromEntries(FAMILIES.map((f) => [f, 0])),
    codeCounts: {},
    nodeWeight: {},
    // Per-family evidence counters fed only by traces: checks the engine evaluated
    // there (pass + fail). Never fed by legacy schema-only envelopes.
    familyEval: Object.fromEntries(FAMILIES.map((f) => [f, { evaluated: 0, passed: 0, failed: 0 }])),
    familyState: Object.fromEntries(FAMILIES.map((f) => [f, "idle"])),
    lastTrace: null,
    legendRows: [],
    legacyEvents: 0,
    traceErrors: 0,
    pendingOperation: "",
    hashChain: [],
    lastSummary: null,
    lastTick: null,
    events: [],
    trail: [],
    player: null,
    focus: "",
    lastHoldGates: [],
    episodeOver: false,
    reducedMotion: REDUCED_MOTION,
    startedAt: performance.now(),
    verdicts: [],
    selectedVerdictId: null,
    verdictSerial: 0,
    readoutFrozen: false,
    pinnedVerdict: null,
    metMira: false,
    lastTickAt: null,
    disclosureEvents: [],
    latestExplanation: null,
    comparison: null,
  };
  window.__traceDashboard = state;

  const $ = (id) => document.getElementById(id);
  const el = (name, attrs = {}, parent = null) => {
    const node = document.createElementNS(SVG_NS, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
    if (parent) parent.appendChild(node);
    return node;
  };
  const short = (hash) => (hash ? `${hash.slice(0, 8)}…${hash.slice(-4)}` : "—");
  const escapeHtml = (text) => String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function gateFamilies(gate) {
    const seen = [];
    for (const part of String(gate).split("/")) {
      const family = part.trim();
      if (FAMILIES.includes(family) && !seen.includes(family)) seen.push(family);
    }
    return seen;
  }

  // ------------------------------------------------------------------ nebula
  // Pipeline geometry mirrors Fig. 2 / Table II of the manuscript: proposer ->
  // parser/contract -> six state-relative predicates -> commit | hold -> trace.
  // The layout is the plan; the node states are the evidence for one proposal.
  const NODES = {
    proposer: { x: 54, y: 200, label: "INTENT", sub: "player proposal a_t", r: 26 },
    parser: { x: 168, y: 200, label: "PARSER", sub: "typed contract", r: 22 },
    POLICY: { x: 320, y: 40, label: "v_policy", sub: "POLICY", r: 18 },
    PRECONDITION: { x: 320, y: 104, label: "v_pre", sub: "PRECONDITION", r: 18 },
    REACHABILITY: { x: 320, y: 168, label: "v_reach", sub: "REACHABILITY", r: 18 },
    KNOWLEDGE: { x: 320, y: 232, label: "v_know", sub: "KNOWLEDGE", r: 18 },
    DISCLOSURE: { x: 320, y: 296, label: "v_disc", sub: "DISCLOSURE", r: 18 },
    "QUEST STAGE": { x: 320, y: 360, label: "v_quest", sub: "QUEST STAGE", r: 18 },
    commit: { x: 486, y: 130, label: "COMMIT", sub: "T(c_t, a_t)", r: 24 },
    hold: { x: 486, y: 270, label: "HOLD", sub: "state unchanged", r: 24 },
    trace: { x: 594, y: 200, label: "TRACE", sub: "hash chain", r: 22 },
  };
  const nebula = $("nebula");
  const defs = el("defs", {}, nebula);
  // One diagonal hatch only (two hatches are hard to tell apart); reserved for
  // out-of-scope families. Dark-theme derivation of the Datawrapper pattern.
  const hatch = el("pattern", { id: "hatch-oos", width: 6, height: 6, patternTransform: "rotate(45)", patternUnits: "userSpaceOnUse" }, defs);
  el("rect", { width: 6, height: 6, fill: COLORS.card }, hatch);
  el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: COLORS.muted, "stroke-width": 2, "stroke-opacity": 0.55 }, hatch);
  for (const [id, color] of [["arrow-blue", COLORS.blue], ["arrow-green", COLORS.green], ["arrow-coral", COLORS.coral], ["arrow-amber", COLORS.amber]]) {
    const marker = el("marker", { id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto-start-reverse", markerUnits: "userSpaceOnUse" }, defs);
    el("path", { d: "M 0 0 L 10 5 L 0 10 z", fill: color }, marker);
  }
  // "Flow stopped here": the edge into the failing check terminates in a square cap.
  const stopMarker = el("marker", { id: "stop-coral", viewBox: "0 0 10 10", refX: 8, refY: 5, markerWidth: 7, markerHeight: 7, orient: "auto", markerUnits: "userSpaceOnUse" }, defs);
  el("rect", { x: 2, y: 1, width: 7, height: 8, fill: COLORS.coral }, stopMarker);
  const edgeLayer = el("g", { id: "edges" }, nebula);
  const pulseLayer = el("g", { id: "pulses" }, nebula);
  const nodeLayer = el("g", { id: "nodes" }, nebula);
  const noteLayer = el("g", { id: "boundary-note" }, nebula);
  const nodeEls = {};

  for (const [id, n] of Object.entries(NODES)) {
    const isFamily = FAMILIES.includes(id);
    const g = el("g", { class: `node${isFamily ? " family" : ""}`, "data-id": id, "data-state": isFamily ? "idle" : "" }, nodeLayer);
    const halo = el("circle", { cx: n.x, cy: n.y, r: n.r + 6, fill: "none", stroke: COLORS.line, "stroke-width": 1, opacity: 0.6 }, g);
    const circle = el("circle", { cx: n.x, cy: n.y, r: n.r, fill: COLORS.card, stroke: COLORS.muted, "stroke-width": 1.5 }, g);
    const glyph = el("text", { class: "glyph", x: n.x, y: n.y - (isFamily ? 4 : 0), "text-anchor": "middle", "font-size": isFamily ? 9 : 0, "font-family": "Menlo, monospace", fill: COLORS.ink }, g);
    const label = el("text", { class: "label", x: n.x, y: n.y + (isFamily ? 7 : 3), "text-anchor": "middle", "font-size": isFamily ? 8 : 9, "font-family": "Menlo, monospace", fill: COLORS.ink }, g);
    label.textContent = n.label;
    const sub = el("text", { class: "sub", x: n.x, y: n.y + n.r + 11, "text-anchor": "middle", "font-size": 8, fill: COLORS.muted }, g);
    sub.textContent = n.sub;
    const word = el("text", { class: "word", x: n.x, y: n.y + n.r + 20, "text-anchor": "middle", "font-size": 7.5, "font-family": "Menlo, monospace", fill: COLORS.muted }, g);
    // The TRACE node sits at the right edge, so its weight goes above it, right-
    // aligned to the viewport, instead of off-canvas to the right.
    const weight = id === "trace"
      ? el("text", { class: "weight", x: 636, y: n.y - n.r - 4, "text-anchor": "end", "font-size": 7.5, "font-family": "Menlo, monospace", fill: COLORS.amber }, g)
      : el("text", { class: "weight", x: n.x + n.r + 3, y: n.y - n.r + 1, "font-size": 7.5, "font-family": "Menlo, monospace", fill: COLORS.amber }, g);
    nodeEls[id] = { g, halo, circle, glyph, label, sub, word, weight, base: n.r, r: n.r };
    state.nodeWeight[id] = 0;
    if (isFamily) setFamilyState(id, "idle");
    else if (id === "commit" || id === "hold") setTerminalState(id, "terminal_idle");
  }

  function paintNode(id, style) {
    const n = nodeEls[id];
    n.circle.setAttribute("fill", style.fill);
    n.circle.setAttribute("stroke", style.stroke);
    n.circle.setAttribute("stroke-width", style.width);
    if (style.dash) n.circle.setAttribute("stroke-dasharray", style.dash); else n.circle.removeAttribute("stroke-dasharray");
    n.halo.setAttribute("stroke", style.ring ? style.stroke : COLORS.line);
    n.halo.setAttribute("stroke-width", style.ring ? 1.5 : 1);
    n.halo.setAttribute("opacity", style.ring ? 0.9 : 0.6);
    n.glyph.textContent = style.glyph;
    n.word.setAttribute("fill", style.stroke === COLORS.muted ? COLORS.muted : style.stroke);
  }
  function setFamilyState(family, name, detail = "") {
    const style = STATE_STYLE[name] || STATE_STYLE.missing;
    state.familyState[family] = name;
    const n = nodeEls[family];
    n.g.setAttribute("data-state", name);
    paintNode(family, style);
    n.word.textContent = detail ? `${style.word} ${detail}` : style.word;
  }
  function setTerminalState(id, name) {
    const style = VERDICT_STYLE[name];
    const n = nodeEls[id];
    n.g.setAttribute("data-state", name === "terminal_idle" ? "" : style.word);
    paintNode(id, style);
    n.word.textContent = style.word;
  }

  // Edges end on the node rim (not the centre) so a persistent arrowhead / stop
  // cap stays visible above the node circle whatever its current weight radius.
  function edgePath(a, b) {
    const A = NODES[a], B = NODES[b];
    const ax = A.x + nodeEls[a].r, ay = A.y, bx = B.x - nodeEls[b].r, by = B.y;
    const mx = (ax + bx) / 2;
    return `M ${ax} ${ay} C ${mx} ${ay}, ${mx} ${by}, ${bx} ${by}`;
  }
  const EDGES = [
    ["proposer", "parser"],
    ...FAMILIES.map((f) => ["parser", f]),
    ...FAMILIES.map((f) => [f, "commit"]),
    ...FAMILIES.map((f) => [f, "hold"]),
    ["commit", "trace"],
    ["hold", "trace"],
  ];
  // The settled stroke is the evidence. `schema` is the plan (untraversed);
  // everything else is set only from what the engine reported for this proposal.
  const EDGE_STYLE = {
    schema: { stroke: COLORS.line, width: 1.2, dash: "", opacity: 0.8, marker: "" },
    traversed: { stroke: COLORS.blue, width: 2, dash: "", opacity: 1, marker: "url(#arrow-blue)" },
    fail: { stroke: COLORS.coral, width: 3, dash: "", opacity: 1, marker: "url(#stop-coral)" },
    commit: { stroke: COLORS.green, width: 2, dash: "", opacity: 1, marker: "url(#arrow-green)" },
    hold: { stroke: COLORS.coral, width: 2, dash: "", opacity: 1, marker: "url(#arrow-coral)" },
    skipped: { stroke: COLORS.gray, width: 1, dash: "1 3", opacity: 0.9, marker: "" },
    out_of_scope: { stroke: COLORS.faint, width: 1, dash: "1 3", opacity: 0.7, marker: "" },
    legacy: { stroke: COLORS.amber, width: 1.2, dash: "3 3", opacity: 0.8, marker: "" },
  };
  const edgeEls = {};
  for (const [a, b] of EDGES) {
    const path = el("path", { class: "edge", "data-edge": `${a}>${b}`, "data-kind": "schema", d: edgePath(a, b), fill: "none" }, edgeLayer);
    edgeEls[`${a}>${b}`] = path;
    styleEdge(a, b, "schema");
  }
  function styleEdge(a, b, kind) {
    const path = edgeEls[`${a}>${b}`];
    if (!path) return;
    const style = EDGE_STYLE[kind];
    path.setAttribute("data-kind", kind);
    path.setAttribute("stroke", style.stroke);
    // Reduced motion: emphasis by weight instead of by pulse (MDN "substitute,
    // never delete"): traversed strokes are one point heavier.
    path.setAttribute("stroke-width", REDUCED_MOTION && style.marker ? style.width + 1 : style.width);
    path.setAttribute("opacity", style.opacity);
    if (style.dash) path.setAttribute("stroke-dasharray", style.dash); else path.removeAttribute("stroke-dasharray");
    if (style.marker) path.setAttribute("marker-end", style.marker); else path.removeAttribute("marker-end");
  }
  function resetEdges() {
    for (const [a, b] of EDGES) styleEdge(a, b, "schema");
  }
  function refreshEdgesTouching(id) {
    for (const [a, b] of EDGES) if (a === id || b === id) edgeEls[`${a}>${b}`].setAttribute("d", edgePath(a, b));
  }

  // AgentSight idiom: node size encodes weight; growth is logarithmic so the
  // graph stays readable across a long session. Family weight = checks the
  // engine evaluated there (pass + fail, from traces); other nodes = envelopes
  // routed through them. Weights are recorded synchronously at event time so the
  // DOM always carries the evidence even while the motion is still playing.
  function weigh(id, delta, tag) {
    state.nodeWeight[id] = (state.nodeWeight[id] || 0) + delta;
    const n = nodeEls[id];
    if (!n) return;
    // Growth is capped so a grown node never runs into the label of the next one.
    n.r = n.base + Math.min(6, 3 * Math.log2(1 + state.nodeWeight[id]));
    n.circle.setAttribute("r", n.r);
    n.halo.setAttribute("r", n.r + 6);
    n.weight.textContent = state.nodeWeight[id] ? `${tag} x${state.nodeWeight[id]}` : "";
    refreshEdgesTouching(id);
  }
  function bump(id) {
    const n = nodeEls[id];
    if (!n || REDUCED_MOTION) return;
    const settled = n.circle.getAttribute("stroke-width");
    n.circle.setAttribute("stroke-width", Number(settled) + 1.5);
    setTimeout(() => n.circle.setAttribute("stroke-width", settled), 700);
  }

  const pulses = [];
  function pulse(a, b, color, delay = 0) {
    if (REDUCED_MOTION) return;
    const path = edgeEls[`${a}>${b}`];
    if (!path) return;
    const dot = el("circle", { class: "edge-pulse", r: 4, fill: color }, pulseLayer);
    pulses.push({ path, dot, t0: performance.now() + delay, dur: 550 });
  }
  function animatePulses(now) {
    for (let i = pulses.length - 1; i >= 0; i -= 1) {
      const p = pulses[i];
      const u = (now - p.t0) / p.dur;
      if (u < 0) continue;
      if (u >= 1) { p.dot.remove(); pulses.splice(i, 1); continue; }
      const len = p.path.getTotalLength();
      const pt = p.path.getPointAtLength(len * u);
      p.dot.setAttribute("cx", pt.x);
      p.dot.setAttribute("cy", pt.y);
      p.dot.setAttribute("opacity", 1 - u * 0.5);
    }
    requestAnimationFrame(animatePulses);
  }
  requestAnimationFrame(animatePulses);

  // Boundary note inside the viewport so exports carry it (research R10);
  // wording: Aside report section 4, Version A, "commit" adapted to "proposal".
  const NOTE_LINES = [
    "This is a per-proposal evaluation trace, not a schematic. Each node shows what the engine actually did for this proposal:",
    "checks that ran and passed, the check that failed, checks skipped after the first failure, and families out of scope for this",
    "operation type. Families marked \"not evaluated\" never ran. That is not a pass, and says nothing about whether they would hold.",
  ];
  NOTE_LINES.forEach((line, i) => {
    const t = el("text", { class: "boundary-line", x: 6, y: 412 + i * 10, "font-size": 8, fill: COLORS.muted }, noteLayer);
    t.textContent = line;
  });
  const stamp = el("text", { id: "trace-stamp", x: 634, y: 12, "text-anchor": "end", "font-size": 7.5, "font-family": "Menlo, monospace", fill: COLORS.amber }, noteLayer);
  stamp.textContent = "engineering demonstration | no proposal yet";

  // ------------------------------------------------------------------ trace
  function normalizeTrace(raw) {
    if (!raw || typeof raw !== "object") return null;
    const checks = (Array.isArray(raw.checks) ? raw.checks : []).map((c) => ({
      code: String(c.code || ""), gate: String(c.gate || ""), outcome: c.outcome === "fail" ? "fail" : c.outcome === "pass" ? "pass" : "missing", families: gateFamilies(c.gate),
    }));
    const familyStates = raw.family_states && typeof raw.family_states === "object" ? raw.family_states : {};
    const states = {};
    const missing = [];
    for (const f of FAMILIES) {
      const s = familyStates[f];
      if (s === "pass" || s === "fail" || s === "skipped" || s === "out_of_scope") states[f] = s;
      else { states[f] = "missing"; missing.push(f); }
    }
    // An unreported check is not evidence of a family pass, even if the
    // supplied aggregate claims one. Keep the graph and readout fail-closed.
    for (const check of checks) {
      if (check.outcome !== "missing") continue;
      for (const f of check.families) {
        states[f] = "missing";
        if (!missing.includes(f)) missing.push(f);
      }
    }
    return {
      checks,
      evaluatedGates: Array.isArray(raw.evaluated_gates) ? raw.evaluated_gates.map(String) : [],
      heldAt: String(raw.held_at || ""),
      shortCircuit: !!raw.short_circuit,
      skipped: (Array.isArray(raw.skipped) ? raw.skipped : []).map((s) => ({ code: String(s.code || ""), gate: String(s.gate || ""), families: gateFamilies(s.gate) })),
      outOfScope: (Array.isArray(raw.out_of_scope) ? raw.out_of_scope : []).map(String),
      states,
      missing,
    };
  }
  function traceSummaryText(t) {
    return `${t.counts.passed} passed, ${t.counts.failed} failed, ${t.counts.skipped} skipped (checks), ${t.counts.not_evaluated} not evaluated (families)`;
  }
  function showTraceFlow(kind, payload, envelope) {
    const trace = normalizeTrace(payload.trace);
    const operation = String(payload.operation || state.pendingOperation || "unknown operation");
    state.pendingOperation = "";
    // Terminal nodes and edges show this proposal only; the previous verdict is
    // not allowed to linger next to a new one.
    resetEdges();
    setTerminalState("commit", "terminal_idle");
    setTerminalState("hold", "terminal_idle");
    weigh("proposer", 1, "routed"); bump("proposer");
    weigh("parser", 1, "routed"); setTimeout(() => bump("parser"), 350);
    styleEdge("proposer", "parser", "traversed");
    pulse("proposer", "parser", COLORS.blue);
    if (!trace) return showLegacyFlow(kind, payload, envelope, operation);

    if (trace.missing.length) {
      state.traceErrors += 1;
      console.error(`dashboard trace: family/check states missing ${trace.missing.join(", ")} for ${operation} (seq ${envelope.seq}); rendering "state missing", not a pass`);
    }
    const codesByFamily = Object.fromEntries(FAMILIES.map((f) => [f, []]));
    const touched = new Set();
    const STEP = 260;
    let step = 0;
    for (const check of trace.checks) {
      const color = check.outcome === "pass" ? COLORS.blue : check.outcome === "fail" ? COLORS.coral : COLORS.amber;
      for (const f of check.families) {
        touched.add(f);
        if (check.outcome === "pass" || check.outcome === "fail") {
          state.familyEval[f].evaluated += 1;
          state.familyEval[f][check.outcome === "pass" ? "passed" : "failed"] += 1;
          weigh(f, 1, "evaluated");
        }
        if (check.outcome === "fail") codesByFamily[f].push(check.code);
        pulse("parser", f, color, 450 + step * STEP);
        setTimeout(() => bump(f), 900 + step * STEP);
      }
      step += 1;
    }
    for (const f of FAMILIES) {
      const s = trace.states[f];
      setFamilyState(f, s, s === "fail" ? codesByFamily[f].join("+") : "");
      if (s === "pass" || s === "fail") styleEdge("parser", f, s === "fail" ? "fail" : "traversed");
      else if (s === "skipped") styleEdge("parser", f, "skipped");
      else if (s === "out_of_scope") styleEdge("parser", f, "out_of_scope");
      // "missing" keeps the schema edge: no evidence either way.
    }
    const routeAt = 450 + step * STEP;
    if (kind === "commit") {
      for (const f of FAMILIES) if (trace.states[f] === "pass") { styleEdge(f, "commit", "commit"); pulse(f, "commit", COLORS.green, routeAt); }
      setTerminalState("commit", "commit");
      weigh("commit", 1, "routed"); setTimeout(() => bump("commit"), routeAt + 450);
      styleEdge("commit", "trace", "commit"); pulse("commit", "trace", COLORS.green, routeAt + 500);
    } else {
      for (const f of FAMILIES) if (trace.states[f] === "fail") { styleEdge(f, "hold", "hold"); pulse(f, "hold", COLORS.coral, routeAt); }
      setTerminalState("hold", "hold");
      weigh("hold", 1, "routed"); setTimeout(() => bump("hold"), routeAt + 450);
      styleEdge("hold", "trace", "hold"); pulse("hold", "trace", COLORS.coral, routeAt + 500);
    }
    weigh("trace", 1, "routed"); setTimeout(() => bump("trace"), routeAt + 950);

    const counts = {
      passed: trace.checks.filter((c) => c.outcome === "pass").length,
      failed: trace.checks.filter((c) => c.outcome === "fail").length,
      skipped: trace.skipped.length,
      not_evaluated: FAMILIES.filter((f) => trace.states[f] === "out_of_scope").length,
      missing: trace.missing.length,
    };
    state.lastTrace = { kind, operation, seq: envelope.seq, t_ms: envelope.t_ms, legacy: false, trace, counts };
    renderLegend(); renderLastTrace();
  }
  // Envelopes from builds older than D-073 carry no per-check evidence. Keep the
  // D-065 schema pulse so an old build still shows life, but paint it amber
  // (verdict-neutral), feed no family weights, and say so in every surface.
  function showLegacyFlow(kind, payload, envelope, operation) {
    state.legacyEvents += 1;
    const heldFamilies = new Set(kind === "hold" ? (payload.gates || []).flatMap(gateFamilies) : []);
    const codes = kind === "hold" ? (payload.codes || []).map(String) : [];
    FAMILIES.forEach((f, i) => {
      const held = heldFamilies.has(f);
      setFamilyState(f, held ? "fail" : "legacy", held ? codes.join("+") : "");
      styleEdge("parser", f, held ? "fail" : "legacy");
      pulse("parser", f, held ? COLORS.coral : COLORS.amber, 450 + i * 40);
      setTimeout(() => bump(f), 900 + i * 40);
      if (kind === "commit") { styleEdge(f, "commit", "legacy"); pulse(f, "commit", COLORS.amber, 1000 + i * 40); }
      else if (held) { styleEdge(f, "hold", "hold"); pulse(f, "hold", COLORS.coral, 1000 + i * 40); }
    });
    const terminal = kind === "commit" ? "commit" : "hold";
    setTerminalState("commit", "terminal_idle");
    setTerminalState("hold", "terminal_idle");
    setTerminalState(terminal, terminal);
    weigh(terminal, 1, "routed"); setTimeout(() => bump(terminal), 1500);
    styleEdge(terminal, "trace", terminal); pulse(terminal, "trace", terminal === "commit" ? COLORS.green : COLORS.coral, 1550);
    weigh("trace", 1, "routed"); setTimeout(() => bump("trace"), 2050);
    state.lastTrace = { kind, operation, seq: envelope.seq, t_ms: envelope.t_ms, legacy: true, trace: null, heldFamilies: [...heldFamilies], codes, counts: null };
    renderLegend(); renderLastTrace();
  }

  // Legend rows are generated from the states on screen for the current event
  // (never authored once and left to drift), reproducing the exact swatch.
  function swatch(name) {
    const s = STATE_STYLE[name];
    const hatched = s.fill === "url(#hatch-oos)";
    const hatchDef = hatched ? `<defs><pattern id="hatch-legend" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="${COLORS.card}"/><line x1="0" y1="0" x2="0" y2="6" stroke="${COLORS.muted}" stroke-width="2" stroke-opacity="0.55"/></pattern></defs>` : "";
    return `<svg class="swatch" viewBox="0 0 22 22" aria-hidden="true">${hatchDef}${s.ring ? `<circle cx="11" cy="11" r="10" fill="none" stroke="${s.stroke}" stroke-width="1.2" opacity="0.9"/>` : ""}<circle cx="11" cy="11" r="7" fill="${hatched ? "url(#hatch-legend)" : s.fill}" stroke="${s.stroke}" stroke-width="${s.width}"${s.dash ? ` stroke-dasharray="${s.dash}"` : ""}/></svg>`;
  }
  function verdictSwatch(name) {
    const s = VERDICT_STYLE[name];
    return `<svg class="swatch" viewBox="0 0 22 22" aria-hidden="true">${s.ring ? `<circle cx="11" cy="11" r="10" fill="none" stroke="${s.stroke}" stroke-width="1.2" opacity="0.9"/>` : ""}<circle cx="11" cy="11" r="7" fill="${s.fill}" stroke="${s.stroke}" stroke-width="${s.width}"/></svg>`;
  }
  function renderLegend() {
    const rows = $("legend-rows");
    const counts = $("legend-counts");
    const t = state.lastTrace;
    if (!t) {
      state.legendRows = [];
      rows.innerHTML = `<li class="hint">legend rows appear per event, generated from the states the engine reported</li>`;
      counts.textContent = "no proposal evaluated yet";
      return;
    }
    const present = [];
    for (const f of FAMILIES) if (!present.includes(state.familyState[f])) present.push(state.familyState[f]);
    const order = ["pass", "fail", "skipped", "out_of_scope", "missing", "legacy"];
    present.sort((a, b) => order.indexOf(a) - order.indexOf(b));
    const items = present.map((name) => `<li data-state="${name}">${swatch(name)}<span class="glyph mono">${escapeHtml(STATE_STYLE[name].glyph)}</span> <b>${STATE_STYLE[name].word}</b> <span class="hint">${LEGEND_WORD[name]}</span></li>`);
    const verdict = t.kind === "commit" ? "commit" : "hold";
    items.push(`<li data-state="${VERDICT_STYLE[verdict].word}">${verdictSwatch(verdict)}<b>${VERDICT_STYLE[verdict].word}</b> <span class="hint">${verdict === "commit" ? "verdict: entry recorded, new snapshot hash" : "verdict: entry held, state unchanged"}</span></li>`);
    state.legendRows = [...present, VERDICT_STYLE[verdict].word];
    rows.innerHTML = items.join("");
    if (t.legacy) counts.textContent = `legacy: schema-only envelope, no per-check counts (${t.kind === "hold" ? `${t.heldFamilies.length} held famil${t.heldFamilies.length === 1 ? "y" : "ies"}` : "no family evidence"})`;
    else counts.textContent = traceSummaryText(t) + (t.counts.missing ? `, ${t.counts.missing} state missing` : "");
  }
  function renderLastTrace() {
    const box = $("last-trace");
    const t = state.lastTrace;
    if (!t) { box.textContent = "no proposal evaluated yet"; return; }
    const familyLabel = (families) => families.map((f) => NODES[f].label).join("/") || "?";
    const lines = [];
    const verdict = t.kind === "commit" ? "COMMIT" : `HELD at ${t.trace ? t.trace.heldAt || "?" : t.codes.join("+")}`;
    lines.push(`last proposal: ${t.operation}  seq ${t.seq}  t_ms ${t.t_ms}  -> ${verdict}`);
    if (t.legacy) {
      lines.push(`legacy: schema-only envelope (no trace); no per-check evidence`);
      if (t.kind === "hold") lines.push(`held family: ${t.heldFamilies.join(", ") || "?"}  codes: ${t.codes.join(", ") || "?"}`);
      lines.push(`not evaluated for ${t.operation}: unknown (no trace)`);
      box.textContent = lines.join("\n");
      stamp.textContent = `engineering demonstration | seq ${t.seq} | t_ms ${t.t_ms} | ${t.operation} -> ${t.kind === "commit" ? "committed" : "held"} | legacy: schema-only`;
      return;
    }
    const tr = t.trace;
    lines.push(`#  FAMILY          CODE                      OUTCOME`);
    tr.checks.forEach((c, i) => {
      lines.push(`${String(i + 1).padEnd(2)} ${familyLabel(c.families).padEnd(15)} ${c.code.padEnd(25)} ${c.outcome === "pass" ? "v passed" : c.outcome === "fail" ? "x failed" : "? state missing"}`);
    });
    // The rule is driven by the engine's explicit short_circuit / held_at, never
    // inferred from list position. It sits after the last executed check: the
    // disclosure pair is always evaluated together, so the check that held the
    // entry is not necessarily the last one that ran.
    if (tr.shortCircuit) {
      lines.push(`   == short-circuit here: remaining in-scope checks were not run ==`);
      const heldIndex = tr.checks.findIndex((c) => c.code === tr.heldAt);
      if (heldIndex >= 0 && heldIndex < tr.checks.length - 1) lines.push(`   (held at #${heldIndex + 1} ${tr.heldAt}; the disclosure pair is always evaluated together)`);
    }
    tr.skipped.forEach((s, i) => {
      lines.push(`${String(tr.checks.length + i + 1).padEnd(2)} ${familyLabel(s.families).padEnd(15)} ${s.code.padEnd(25)} ->| skipped`);
    });
    const oos = FAMILIES.filter((f) => tr.states[f] === "out_of_scope");
    lines.push("");
    lines.push(`Not evaluated for ${t.operation} (out of scope): ${oos.length ? oos.join(", ") : "none"}`);
    if (tr.missing.length) lines.push(`! state missing from payload: ${tr.missing.join(", ")} (rendered "state missing", not a pass)`);
    box.textContent = lines.join("\n");
    stamp.textContent = `engineering demonstration | seq ${t.seq} | t_ms ${t.t_ms} | ${t.operation} -> ${t.kind === "commit" ? "committed" : "held"}`;
  }

  // ------------------------------------------------------------------ metrics
  function renderGateTable() {
    const table = $("gate-table");
    const max = Math.max(1, ...Object.values(state.holdsByGate));
    const ref = Array.isArray(state.reference?.paper_predicates) ? state.reference.paper_predicates : [];
    const rows = FAMILIES.map((f) => {
      const meta = ref.find((r) => r.family === f) || { symbol: "", engine_codes: [] };
      const n = state.holdsByGate[f] || 0;
      const ev = state.familyEval[f];
      const codes = meta.engine_codes.map((c) => `${c}${state.codeCounts[c] ? ` x${state.codeCounts[c]}` : ""}`).join(", ") || "-";
      return `<tr><td><span class="mono">${meta.symbol}</span> ${f}</td><td class="bar-cell"><div class="bar-fill" style="width:${(100 * n) / max}%"></div><span class="mono">${n}</span></td><td class="num" title="checks the engine evaluated at this family (from traces)">${ev.evaluated}</td><td class="num">${ev.passed}</td><td class="num">${ev.failed}</td><td class="hint">${codes}</td></tr>`;
    });
    table.innerHTML = `<tr><th>predicate family</th><th>holds</th><th>checks evaluated</th><th>passed</th><th>failed</th><th>engine codes seen</th></tr>${rows.join("")}`;
  }
  function renderChain() {
    const ol = $("hash-chain");
    ol.innerHTML = state.hashChain
      .slice(-6)
      .map((h, i, arr) => `<li class="${i === arr.length - 1 ? "head" : ""}"><span class="tag">${h.tag}</span> ${short(h.hash)} <span class="hint">rev ${h.revision} · stage ${h.stage}</span></li>`)
      .join("") || `<li class="hint">no snapshot yet</li>`;
  }
  function renderReference() {
    const r = state.reference;
    const table = $("ref-table");
    if (!r) { table.innerHTML = `<tr><td class="hint">paper-reference.json not loaded</td></tr>`; return; }
    if (!r.e1 || !r.e1.repair_arms) { table.innerHTML = `<tr><td class="hint">Legacy paper counts are not present in this semantic reference; live and frozen lanes stay separate.</td></tr>`; return; }
    const ga = r.e1.repair_arms.guided_repair, ua = r.e1.repair_arms.unchanged_retry;
    const blindCommits = ua.guided_repairable.commits + ua.oracle_only.commits + ua.irreparable.commits;
    const blindCases = ua.guided_repairable.cases + ua.oracle_only.cases + ua.irreparable.cases;
    const rows = [
      ["live session · commits / holds", `${state.counts.commits} / ${state.counts.holds}`, "engineering demo only"],
      ["live session · reported hold events", `${state.counts.holds}`, "engine-reported; immutability checked separately"],
      ["E1 gate fixtures agree", `${r.e1.gate_fixtures[0]}/${r.e1.gate_fixtures[1]}`, `${r.e1.implemented_codes} encoded codes`],
      ["E1 guided repair rho (guided-repairable)", `${ga.guided_repairable.commits}/${ga.guided_repairable.cases}`, "C5 · frozen designed fixtures"],
      ["E1 blind unchanged retry", `${blindCommits}/${blindCases}`, "matched budget, no error feedback"],
      ["E1 detectable integrity faults rejected", `${r.e1.integrity_faults[0]}/${r.e1.integrity_faults[1]}`, "C3 designated check operations"],
      [`E2 ${r.e2.cell} (K=${r.e2.K})`, `rho ${r.e2.guided_commits}/${r.e2.initially_invalid} vs blind ${r.e2.blind_commits}/${r.e2.initially_invalid}`, "screening-pilot-only"],
    ];
    table.innerHTML = `<tr><th>row</th><th>count</th><th>boundary</th></tr>${rows.map(([a, b, c]) => `<tr><td>${a}</td><td class="num">${b}</td><td class="hint">${c}</td></tr>`).join("")}`;
  }
  function renderKpis(summary) {
    if (!summary) return;
    $("kpi-commits").textContent = summary.commit_count ?? state.counts.commits;
    $("kpi-holds").textContent = summary.refusal_count ?? state.counts.holds;
    $("kpi-stage").textContent = summary.stage ?? "—";
    $("kpi-revision").textContent = summary.revision ?? "0";
    $("kpi-facts").textContent = summary.fact_count ?? "0";
    $("kpi-episode").textContent = state.episodeOver ? "complete" : "open";
    $("session-hash").textContent = `state ${short(summary.state_sha256)}`;
    renderQuest(summary);
  }
  // ------------------------------------------------------------------ public semantic disclosure lane
  // Only the additive, public-safe explanation contract is consumed here. Unknown
  // or malformed values remain unknown; the dashboard never turns absence into pass.
  const HASH_RE = /^[a-f0-9]{64}$/i;
  const safeToken = (value, fallback = "unknown") => {
    if (typeof value !== "string") return fallback;
    const token = value.trim().slice(0, 120);
    return token && /^[A-Za-z0-9_.:/+ -]+$/.test(token) ? token : fallback;
  };
  const safeHash = (value) => typeof value === "string" && HASH_RE.test(value) ? value.toLowerCase() : null;
  const EXPLANATION_SCHEMA_ID = "trace-rpg-semantic-explanation";
  const EXPLANATION_SCHEMA_VERSION = "1.0.0";
  const PUBLIC_OPERATION_CODES = new Set(["reveal_hint"]);
  const PUBLIC_ACTOR_ROLES = new Set(["captain", "unknown/restricted"]);
  const PUBLIC_SUBJECT_TYPES = new Set(["lead", "unknown/restricted"]);
  const PUBLIC_RELATIONS = new Set(["captain_to_lead_disclosure", "unknown/restricted"]);
  const PUBLIC_DECISIONS = new Set(["authorized_fresh", "authorized_redisplay", "denied"]);
  const PUBLIC_STATE_EFFECTS = new Set(["fresh_disclosure", "redisplay_no_mutation", "denied_no_mutation"]);
  const PUBLIC_CHECK_CODES = new Set(["FORBIDDEN_DISCLOSURE", "STAGE_GATED_DISCLOSURE", "UNKNOWN_ACTOR", "NPC_DOES_NOT_KNOW_FACT", "DISCLOSURE_TEMPLATE_UNAVAILABLE"]);
  const PUBLIC_GATE_LABELS = new Set([...FAMILIES, "DISCLOSURE/QUEST STAGE"]);
  const DISCLOSURE_RULE_IDS = new Set(["DISC-001", "DISC-002", "DISC-003", "DISC-004", "DISC-005", "DISC-006", "DISC-007"]);
  const publicEnum = (value, allowed) => typeof value === "string" && allowed.has(value) ? value : "unknown";
  const safeRuleId = (value) => DISCLOSURE_RULE_IDS.has(value) ? value : "unknown";
  const boolOrUnknown = (value) => typeof value === "boolean" ? value : null;
  const numberOrUnknown = (value) => Number.isSafeInteger(value) && value >= 0 ? value : null;
  function normalizeExplanation(payload, envelope) {
    const raw = payload && typeof payload.explanation === "object" && payload.explanation !== null ? payload.explanation : null;
    if (!raw || raw.schema_id !== EXPLANATION_SCHEMA_ID || raw.schema_version !== EXPLANATION_SCHEMA_VERSION) return null;
    const input = raw.input && typeof raw.input === "object" ? raw.input : {};
    const ontology = raw.ontology && typeof raw.ontology === "object" ? raw.ontology : {};
    const checks = raw.checks && typeof raw.checks === "object" ? raw.checks : {};
    const decision = raw.decision && typeof raw.decision === "object" ? raw.decision : {};
    const effect = raw.state_effect && typeof raw.state_effect === "object" ? raw.state_effect : {};
    const engine = raw.engine && typeof raw.engine === "object" ? raw.engine : {};
    const mapCheck = (item) => item && typeof item === "object" ? { code: publicEnum(item.code, PUBLIC_CHECK_CODES), gate: publicEnum(item.gate, PUBLIC_GATE_LABELS), outcome: item.outcome === "pass" || item.outcome === "fail" ? item.outcome : "unknown" } : { code: "unknown", gate: "unknown", outcome: "unknown" };
    const evaluated = Array.isArray(checks.evaluated) ? checks.evaluated.map(mapCheck) : null;
    const skipped = Array.isArray(checks.skipped) ? checks.skipped.map(mapCheck) : null;
    const outOfScope = Array.isArray(checks.out_of_scope) ? checks.out_of_scope.map((value) => publicEnum(value, PUBLIC_GATE_LABELS)).slice(0, 12) : null;
    const unreported = Array.isArray(checks.unreported) ? checks.unreported.map(mapCheck) : null;
    const priorHash = safeHash(effect.prior_state_hash);
    const nextHash = safeHash(effect.next_state_hash);
    const hashEquality = priorHash && nextHash ? (priorHash === nextHash ? "equal" : "different") : "unknown";
    const seq = numberOrUnknown(engine.seq) ?? numberOrUnknown(envelope.seq);
    const tMs = numberOrUnknown(engine.t_ms) ?? numberOrUnknown(envelope.t_ms);
    return {
      schema: `${EXPLANATION_SCHEMA_ID} ${EXPLANATION_SCHEMA_VERSION}`,
      input: { operation: publicEnum(input.operation, PUBLIC_OPERATION_CODES), actorRole: publicEnum(input.actor_role, PUBLIC_ACTOR_ROLES), subjectType: publicEnum(input.subject_type, PUBLIC_SUBJECT_TYPES) },
      ontology: { relation: publicEnum(ontology.relation, PUBLIC_RELATIONS), ruleIds: Array.isArray(ontology.rule_ids) ? ontology.rule_ids.map(safeRuleId).slice(0, 16) : [] },
      checks: { evaluated, skipped, outOfScope, unreported, consistent: boolOrUnknown(checks.consistent) },
      decision: { outcome: publicEnum(decision.outcome, PUBLIC_DECISIONS), accepted: boolOrUnknown(decision.accepted), resultCodes: Array.isArray(decision.result_codes) ? decision.result_codes.map((value) => publicEnum(value, PUBLIC_CHECK_CODES)).slice(0, 16) : [] },
      effect: { kind: publicEnum(effect.kind, PUBLIC_STATE_EFFECTS), mutated: boolOrUnknown(effect.mutated), priorHash, nextHash, hashEquality },
      engine: { seq, tMs },
    };
  }
  function displayValue(value) { return value === null || value === undefined || value === "" ? "unknown" : String(value); }
  function renderSemanticExplanation(explanation, hasEvent = false) {
    const root = $("semantic-explanation");
    clearChildren(root);
    if (!explanation) {
      const note = document.createElement("p"); note.className = `empty-note ${hasEvent ? "unknown" : "waiting"}`; note.textContent = hasEvent ? "Semantic explanation unknown: malformed or unavailable public-safe payload." : "Waiting for a disclosure outcome or replay from the game."; root.appendChild(note); return;
    }
    const checkCount = (value) => Array.isArray(value) ? value.length : "unknown";
    const checksKnown = [explanation.checks.evaluated, explanation.checks.skipped, explanation.checks.outOfScope, explanation.checks.unreported].every(Array.isArray) && explanation.checks.consistent === true && explanation.checks.unreported.length === 0;
    const unreportedCodes = explanation.checks.unreported === null ? "unknown" : explanation.checks.unreported.map((check) => check.code).join(", ") || "none";
    const steps = [
      ["Typed input", `${explanation.input.operation}`, `actor role: ${displayValue(explanation.input.actorRole)} · subject: ${displayValue(explanation.input.subjectType)}`, "known"],
      ["Ontology relation", explanation.ontology.relation, explanation.ontology.ruleIds.length ? `rules: ${explanation.ontology.ruleIds.join(", ")}` : "rules: unknown", "known"],
      ["Actual checks", `${checkCount(explanation.checks.evaluated)} evaluated · ${checkCount(explanation.checks.skipped)} skipped · ${checkCount(explanation.checks.unreported)} unreported`, `${checkCount(explanation.checks.outOfScope)} out of scope · consistent: ${displayValue(explanation.checks.consistent)} · unreported: ${unreportedCodes}`, checksKnown ? "known" : "unknown"],
      ["Decision", explanation.decision.outcome, `accepted: ${displayValue(explanation.decision.accepted)} · codes: ${explanation.decision.resultCodes.join(", ") || "none reported"}`, explanation.decision.outcome === "unknown" ? "unknown" : "known"],
      ["State transition", explanation.effect.kind, `mutated: ${displayValue(explanation.effect.mutated)} · hashes: ${explanation.effect.hashEquality}`, explanation.effect.hashEquality === "unknown" ? "unknown" : "known"],
      ["Engine record", `seq ${displayValue(explanation.engine.seq)}`, `t_ms ${displayValue(explanation.engine.tMs)} · ${explanation.schema}`, explanation.engine.seq === null || explanation.engine.tMs === null ? "unknown" : "known"],
    ];
    for (const [heading, value, detail, status] of steps) {
      const article = document.createElement("article"); article.className = "semantic-step"; article.dataset.state = status;
      const h = document.createElement("h3"); h.textContent = heading;
      const p = document.createElement("p"); p.textContent = value;
      const small = document.createElement("span"); small.className = "semantic-detail"; small.textContent = detail;
      article.append(h, p, small); root.appendChild(article);
    }
  }
  function renderDisclosureTimeline() {
    const svg = $("disclosure-timeline"), list = $("disclosure-events"), clock = $("timeline-clock"), status = $("disclosure-live-status");
    clearChildren(svg); clearChildren(list);
    const events = [...state.disclosureEvents].sort((a, b) => (a.seq ?? Number.MAX_SAFE_INTEGER) - (b.seq ?? Number.MAX_SAFE_INTEGER) || (a.tMs ?? Number.MAX_SAFE_INTEGER) - (b.tMs ?? Number.MAX_SAFE_INTEGER));
    if (!events.length) {
      status.textContent = "waiting for disclosure events"; clock.textContent = "engine clock: waiting";
      const li = document.createElement("li"); li.className = "empty-note"; li.textContent = "Waiting for disclosure_outcome or disclosure_replay events."; list.appendChild(li); return;
    }
    const knownTimes = events.map((event) => event.tMs).filter((value) => value !== null);
    const minTime = knownTimes.length ? Math.min(...knownTimes) : null;
    const maxTime = knownTimes.length ? Math.max(...knownTimes) : null;
    const completeClock = knownTimes.length === events.length;
    clock.textContent = minTime === null ? "engine clock: unknown (t_ms not reported); positions show event order" : !completeClock ? "engine clock: incomplete (some t_ms unreported); positions show event order" : `engine clock: t_ms milliseconds · ${minTime}–${maxTime}`;
    status.textContent = `${events.length} disclosure signal${events.length === 1 ? "" : "s"} · ordered by engine seq/t_ms`;
    const xFor = (event, index) => !completeClock || maxTime === minTime ? 100 + index * (800 / Math.max(1, events.length - 1)) : 100 + ((event.tMs - minTime) / (maxTime - minTime)) * 800;
    const lanes = [{ label: "outcome", y: 48 }, { label: "state effect", y: 100 }, { label: "hash equality", y: 152 }];
    lanes.forEach((lane) => { el("line", { x1: 88, y1: lane.y, x2: 990, y2: lane.y, stroke: COLORS.line }, svg); const text = el("text", { x: 8, y: lane.y + 4, "font-size": 11, fill: COLORS.muted }, svg); text.textContent = lane.label; });
    events.forEach((event, index) => {
      const eventKnown = Boolean(event.explanation && event.explanation.decision.outcome !== "unknown" && event.explanation.effect.kind !== "unknown");
      const x = xFor(event, index), outcomeColor = event.explanation?.decision.outcome === "denied" ? COLORS.coral : eventKnown ? COLORS.green : COLORS.amber;
      el("line", { x1: x, y1: 30, x2: x, y2: 166, stroke: outcomeColor, "stroke-width": 1, opacity: 0.55 }, svg);
      el("circle", { cx: x, cy: 48, r: 6, fill: outcomeColor }, svg);
      const effect = event.explanation?.effect.kind || "unknown";
      el("rect", { x: x - 5, y: 95, width: 10, height: 10, fill: effect === "unknown" ? COLORS.amber : COLORS.blue, rx: 2 }, svg);
      const equality = event.explanation?.effect.hashEquality || "unknown";
      el("circle", { cx: x, cy: 152, r: 6, fill: equality === "equal" ? COLORS.green : equality === "different" ? COLORS.coral : COLORS.amber }, svg);
      const label = el("text", { x, y: 20, "font-size": 9, "text-anchor": "middle", fill: outcomeColor }, svg); label.textContent = `#${displayValue(event.seq)}`;
      const li = document.createElement("li"); li.className = "disclosure-event"; li.dataset.outcome = event.explanation?.decision.outcome === "denied" ? "denied" : eventKnown ? "known" : "unknown";
      const indexNode = document.createElement("span"); indexNode.className = "event-index"; indexNode.textContent = `#${index + 1}`;
      const main = document.createElement("div"); main.className = "event-main";
      const head = document.createElement("div"); head.className = "event-head"; head.textContent = `${event.kind} · ${event.explanation?.decision.outcome || "unknown outcome"}`;
      const meta = document.createElement("div"); meta.className = "event-meta";
      const e = event.explanation;
      meta.textContent = `seq ${displayValue(event.seq)} · t_ms ${displayValue(event.tMs)} · checks ${e ? `${e.checks.evaluated?.length ?? "unknown"} evaluated, ${e.checks.skipped?.length ?? "unknown"} skipped, ${e.checks.outOfScope?.length ?? "unknown"} out of scope, ${e.checks.unreported?.length ?? "unknown"} unreported` : "unknown"} · errors ${e ? (e.decision.resultCodes.join(", ") || "none reported") : "unknown"} · state ${e?.effect.kind || "unknown"} · hash equality ${e?.effect.hashEquality || "unknown"}`;
      main.append(head, meta); li.append(indexNode, main); list.appendChild(li);
    });
  }
  function comparisonEntries(reference) {
    const comparison = reference?.frozen_comparison;
    if (!comparison || typeof comparison !== "object") return [];
    const labels = { unchecked_isolated: "Unchecked isolated", general_rule: "General rule", ontology_gate: "Ontology gate" };
    const fromArm = (id, arm, index) => {
      const strata = comparison.cells?.[id] && typeof comparison.cells[id] === "object" ? comparison.cells[id] : {};
      const outcome = Object.values(strata).reduce((sum, cell) => sum + (cell?.report_status === "reported" && typeof cell.n === "number" ? cell.n : 0), 0);
      return { id: safeToken(id, `arm-${index + 1}`), label: safeToken(arm?.label, labels[id] || id || `arm ${index + 1}`), counts: arm?.counts && typeof arm.counts === "object" ? arm.counts : { outcome, unsafe: comparison.counts?.unsafe_by_arm?.[id], mismatch: comparison.counts?.mismatch_by_arm?.[id] } };
    };
    if (Array.isArray(comparison.arms)) return comparison.arms.map((arm, index) => fromArm(typeof arm === "string" ? arm : arm?.id, typeof arm === "string" ? null : arm, index));
    return Object.entries(comparison.arms || {}).map(([id, arm], index) => fromArm(id, arm, index));
  }
  function comparisonCells(comparison, entries) {
    if (Array.isArray(comparison?.cells)) return comparison.cells;
    return entries.flatMap((entry) => Object.entries(comparison?.cells?.[entry.id] || {}).map(([caseClass, cell]) => ({ ...cell, arm: entry.label, case_class: caseClass })));
  }
  function metricValue(counts, metric, aliases = []) {
    const candidate = counts?.[metric];
    if (typeof candidate === "number" && Number.isFinite(candidate)) return candidate;
    if (candidate && typeof candidate === "object") {
      if (typeof candidate.count === "number" && Number.isFinite(candidate.count)) return candidate.count;
      for (const alias of aliases) {
        const value = candidate[alias];
        if (typeof value === "number" && Number.isFinite(value)) return value;
        if (value && typeof value.count === "number" && Number.isFinite(value.count)) return value.count;
      }
    }
    return null;
  }
  function metricForEntry(entry, metric, comparison) {
    return metricValue(entry.counts, metric, [entry.id, entry.label]) ?? metricValue(comparison?.counts, metric, [entry.id, entry.label]);
  }
  function renderRuleBoundaries(reference) {
    const root = $("rule-boundaries"); if (!root) return; clearChildren(root);
    const rules = reference?.disclosure_rules;
    const entries = [["python7", "Original Python: seven Boolean checks"], ["godot6", "Godot: six display families"], ["disclosure7", "Disclosure: seven declaration rules"]];
    for (const [key, title] of entries) {
      const item = document.createElement("article"); item.className = "rule-boundary";
      const heading = document.createElement("h3"); heading.textContent = title;
      const body = document.createElement("p"); const value = rules && typeof rules[key] === "object" ? rules[key] : null;
      const count = Array.isArray(value) ? `count ${value.length}` : value && typeof value.count === "number" ? `count ${value.count}` : "count unknown";
      const label = Array.isArray(value) ? "public labels only; no runtime equivalence inferred" : value && typeof value.label === "string" ? safeToken(value.label) : "public rule boundary not reported";
      body.textContent = `${label} · ${count}`; item.append(heading, body); root.appendChild(item);
    }
  }
  function formatCaseCounts(comparison) {
    const cases = comparison?.case_counts;
    if (cases && typeof cases === "object") {
      const normal = cases.normal ?? cases.N ?? cases.n;
      const boundary = cases.boundary ?? cases.B ?? cases.b;
      const malformed = cases.malformed ?? cases.M ?? cases.m;
      if ([normal, boundary, malformed].every((value) => typeof value === "number")) return `N=${normal} · B=${boundary} · M=${malformed}`;
    }
    const strata = comparison?.cells?.general_rule || comparison?.cells?.ontology_gate || comparison?.cells?.unchecked_isolated;
    const normal = strata?.normal?.n, boundary = strata?.boundary?.n, malformed = strata?.malformed?.n;
    if ([normal, boundary, malformed].every((value) => typeof value === "number")) return `N=${normal} · B=${boundary} · M=${malformed}`;
    return typeof comparison?.denominator === "string" ? comparison.denominator : "60 inputs × 3 arms";
  }
  function renderComparison() {
    const graph = $("comparison-graph"), legend = $("comparison-legend"), matrix = $("comparison-matrix"), status = $("comparison-status"), claim = $("comparison-claim-boundary");
    clearChildren(graph); clearChildren(legend); clearChildren(matrix); renderRuleBoundaries(null);
    const reference = state.reference, comparison = reference?.frozen_comparison, claims = comparison?.claim_boundary, cases = comparison?.case_counts;
    const trusted = reference?.schema_version === "trace-rpg-signal-explainer/v1"
      && comparison?.independent_inputs === 60
      && cases?.normal === 48 && cases?.boundary === 4 && cases?.malformed === 8 && cases?.total === 60
      && comparison?.counts?.general_ontology_equal === 60
      && claims?.engineering_only === true && claims?.not_efficacy === true
      && claims?.not_holdout === true && claims?.not_human_gold === true
      && claims?.not_ontology_superiority === true && claims?.not_player_benefit === true;
    const entries = trusted ? comparisonEntries(reference) : [];
    if (!trusted || !entries.length) {
      status.textContent = "frozen comparison unavailable · no live values inferred";
      claim.textContent = "Bounded checker evidence unavailable or invalid. No superiority, holdout, human-gold, player-benefit, efficacy, or latent-state claim is inferred.";
      matrix.innerHTML = `<tr><td class="hint">Frozen comparison is unavailable or malformed. Cells remain unreported.</td></tr>`;
      return;
    }
    renderRuleBoundaries(reference);
    claim.textContent = "Declaration-derived bounded checker evidence: general-rule and ontology-gate outputs agree on 60/60 inputs. This is engineering-only fixture agreement, not ontology superiority, holdout or human-gold, player-benefit, efficacy, or latent-state evidence.";
    const metrics = ["outcome", "unsafe", "mismatch"], colors = { outcome: COLORS.blue, unsafe: COLORS.coral, mismatch: COLORS.amber };
    status.textContent = `${formatCaseCounts(comparison)} · frozen independent lane`;
    const max = Math.max(1, ...entries.flatMap((entry) => metrics.map((metric) => metricForEntry(entry, metric, comparison) ?? 0)));
    entries.forEach((entry, armIndex) => {
      const y = 36 + armIndex * 68; const label = el("text", { x: 8, y, "font-size": 11, fill: COLORS.ink }, graph); label.textContent = entry.label;
      metrics.forEach((metric, metricIndex) => { const value = metricForEntry(entry, metric, comparison); const x = 245, rowY = y + metricIndex * 18; el("rect", { x, y: rowY - 12, width: value === null ? 6 : Math.max(0, (graph.viewBox.baseVal.width - x - 18) * value / max), height: 14, fill: value === null ? "none" : colors[metric], stroke: colors[metric], "stroke-dasharray": value === null ? "3 3" : "", rx: 3 }, graph); const text = el("text", { x: 130, y: rowY + 1, "font-size": 10, fill: COLORS.ink }, graph); text.textContent = `${metric}: ${value === null ? "unknown" : value}`; });
    });
    metrics.forEach((metric) => { const span = document.createElement("span"); const b = document.createElement("b"); b.textContent = metric; span.append(b, document.createTextNode(metric === "outcome" ? " recorded result" : metric === "unsafe" ? " unsafe classification" : " mismatch classification")); legend.appendChild(span); });
    const cells = comparisonCells(comparison, entries);
    const rows = cells.slice(0, 180).map((cell, index) => { const reportStatus = cell?.checks && typeof cell.checks === "object" ? (cell.checks.report_status === "reported" ? "reported" : "unreported") : cell?.report_status === "reported" ? "reported" : "unreported"; const outcomeValue = typeof cell?.outcome === "string" ? safeToken(cell.outcome) : cell?.outcome && typeof cell.outcome === "object" ? Object.entries(cell.outcome).filter(([, value]) => typeof value === "number").map(([key, value]) => `${safeToken(key)} ${value}`).join(" · ") || "unknown" : "unknown"; const outcome = outcomeValue; const unsafe = displayValue(cell.unsafe); const mismatch = displayValue(cell.mismatch); return `<tr><td class="mono">${index + 1}</td><td>${safeToken(cell?.arm, "unknown")}</td><td>${safeToken(cell?.case_class, "unknown")}</td><td>${displayValue(cell?.n)}</td><td data-status="${reportStatus}">${reportStatus}</td><td>${outcome}</td><td>${unsafe}</td><td>${mismatch}</td></tr>`; });
    matrix.innerHTML = `<tr><th>cell slice</th><th>arm</th><th>case class</th><th>n</th><th>check coverage</th><th>outcome</th><th>unsafe</th><th>mismatch</th></tr>${rows.join("") || `<tr><td colspan="8" class="hint">No cells reported; empty cells are unreported, not pass, skipped, or out of scope.</td></tr>`}`;
  }

  // ------------------------------------------------------------------ timeline
  const LANES = ["proposal", "verdict", "dialogue", "focus"];
  const timeline = $("timeline");
  const WINDOW_MS = 90000;
  function renderTimeline() {
    while (timeline.firstChild) timeline.removeChild(timeline.firstChild);
    const now = performance.now();
    LANES.forEach((lane, i) => {
      const y = 25 + i * 32;
      el("line", { x1: 90, y1: y, x2: 990, y2: y, stroke: COLORS.line }, timeline);
      const t = el("text", { x: 8, y: y + 4, "font-size": 11, fill: COLORS.muted }, timeline);
      t.textContent = lane;
    });
    for (const ev of state.events) {
      const age = now - ev.at;
      if (age > WINDOW_MS) continue;
      const x = 990 - (age / WINDOW_MS) * 900;
      const lane = ev.kind === "commit" || ev.kind === "hold" ? "verdict" : ev.kind;
      const i = LANES.indexOf(lane);
      if (i < 0) continue;
      const y = 25 + i * 32;
      const color = ev.kind === "commit" ? COLORS.green : ev.kind === "hold" ? COLORS.coral : ev.kind === "proposal" ? COLORS.amber : COLORS.blue;
      if (lane === "verdict") el("rect", { x: x - 4, y: y - 9, width: 8, height: 18, fill: color, rx: 2 }, timeline);
      else el("circle", { cx: x, cy: y, r: 4, fill: color }, timeline);
      if (ev.label) {
        const t = el("text", { x, y: y - 12, "font-size": 9, "text-anchor": "middle", fill: color }, timeline);
        t.textContent = ev.label;
      }
    }
  }
  setInterval(renderTimeline, 500);

  // ------------------------------------------------------------------ minimap
  const minimap = $("minimap");
  const MAP = { xmin: -16, xmax: 12, zmin: -4, zmax: 20 };
  const mx = (x) => 10 + ((x - MAP.xmin) / (MAP.xmax - MAP.xmin)) * 300;
  const mz = (z) => 250 - ((z - MAP.zmin) / (MAP.zmax - MAP.zmin)) * 240;
  function renderMinimap() {
    while (minimap.firstChild) minimap.removeChild(minimap.firstChild);
    $("map-caption").textContent = state.session ? `${state.session.sites.length} sites · live player trail` : "waiting for game session";
    $("map-focus").textContent = state.focus ? `Focused site: ${state.focus}` : state.player ? `Player position · ${Number(state.player.x).toFixed(1)}, ${Number(state.player.z).toFixed(1)}` : "Player position appears when the game sends a tick.";
    el("rect", { x: 0, y: 0, width: 320, height: 260, fill: "#0e161f", rx: 8 }, minimap);
    for (let gx = MAP.xmin; gx <= MAP.xmax; gx += 4) el("line", { x1: mx(gx), y1: mz(MAP.zmin), x2: mx(gx), y2: mz(MAP.zmax), stroke: COLORS.line, "stroke-width": 0.5 }, minimap);
    for (let gz = MAP.zmin; gz <= MAP.zmax; gz += 4) el("line", { x1: mx(MAP.xmin), y1: mz(gz), x2: mx(MAP.xmax), y2: mz(gz), stroke: COLORS.line, "stroke-width": 0.5 }, minimap);
    const sites = (state.session && state.session.sites) || [];
    for (const s of sites) {
      const focused = state.focus === s.id;
      el("circle", { cx: mx(s.x), cy: mz(s.z), r: focused ? 8 : 6, fill: "none", stroke: focused ? COLORS.amber : COLORS.muted, "stroke-width": focused ? 2 : 1 }, minimap);
      const t = el("text", { x: mx(s.x), y: mz(s.z) - 10, "font-size": 8, "text-anchor": "middle", fill: focused ? COLORS.amber : COLORS.muted }, minimap);
      t.textContent = s.id;
    }
    if (state.trail.length > 1) {
      el("polyline", { points: state.trail.map((p) => `${mx(p.x)},${mz(p.z)}`).join(" "), fill: "none", stroke: COLORS.blue, "stroke-width": 1.2, opacity: 0.8 }, minimap);
    }
    if (state.player) {
      const p = state.player;
      el("circle", { cx: mx(p.x), cy: mz(p.z), r: 4.5, fill: COLORS.blue }, minimap);
      el("line", { x1: mx(p.x), y1: mz(p.z), x2: mx(p.x - Math.sin(p.yaw)), y2: mz(p.z - Math.cos(p.yaw)), stroke: COLORS.blue, "stroke-width": 2 }, minimap);
    }
  }

  // ------------------------------------------------------------------ feed
  const log = $("log");
  function logLine(kind, text) {
    const line = document.createElement("div");
    line.className = kind;
    line.textContent = `${((performance.now() - state.startedAt) / 1000).toFixed(1).padStart(6)}s  ${kind.padEnd(16)} ${text}`;
    log.appendChild(line);
    while (log.childNodes.length > 120) log.removeChild(log.firstChild);
    $("log-count").textContent = `${state.events.length} events`;
  }
  function flash(cls) {
    const card = document.querySelector(".metrics");
    card.classList.remove("flash-commit", "flash-hold");
    void card.offsetWidth;
    card.classList.add(cls);
  }
  function traceLogTag() {
    const t = state.lastTrace;
    if (!t) return "";
    if (t.legacy) return " · legacy: schema-only";
    const checks = t.trace.checks.map((c) => `${c.code}:${c.outcome}`).join(" > ");
    return ` · trace ${checks || "(no checks)"}${t.trace.shortCircuit ? ` > short-circuit at ${t.trace.heldAt}` : ""} · ${traceSummaryText(t)}`;
  }

  // Player-facing panels render only values returned by the game.
  const QUEST_STEPS = ["Collect the signal lens", "Install the lens at the harbor beacon", "Ask Mira for the tide route"];
  const clearChildren = (node) => { while (node.firstChild) node.removeChild(node.firstChild); };
  function renderQuest(summary = state.lastSummary) {
    const objective = $("quest-objective"), steps = $("quest-steps"), label = $("quest-stage-label"), note = $("quest-note");
    clearChildren(steps);
    const stage = summary?.stage ?? state.lastSummary?.stage;
    if (!Number.isInteger(stage) || stage < 0 || stage > 3) { label.textContent = "waiting for session"; objective.textContent = "Waiting for a valid game session summary."; note.textContent = "No valid quest stage has been reported yet."; return; }
    const current = stage, complete = state.episodeOver;
    label.textContent = complete ? "complete · 3 / 3" : `stage ${current} / 3`;
    objective.textContent = complete ? "Episode complete." : current === 0 && !state.metMira ? "Speak with Captain Mira, then recover the signal lens." : current < 3 ? QUEST_STEPS[current] : "Continue with the presentation-only tide-mark deduction and ending.";
    QUEST_STEPS.forEach((textValue, index) => {
      const item = document.createElement("li"), mark = document.createElement("span"), text = document.createElement("span"), status = document.createElement("span");
      const done = complete || current > index, active = !complete && current === index;
      item.className = `quest-step${done ? " done" : active ? " current" : ""}`; mark.className = "step-mark"; mark.textContent = done ? "✓" : active ? "•" : String(index + 1);
      status.className = "step-state"; status.textContent = done ? "Complete" : active ? "Current stage goal" : "Not started"; text.textContent = textValue; text.appendChild(status); item.append(mark, text); steps.appendChild(item);
    });
    note.textContent = complete || current === 3 ? "The remaining deduction and ending are presentation-only." : "Stage progress follows committed session summaries.";
  }
  function addCheckRow(list, status, label, code = "", family = "") {
    const item = document.createElement("li"), heading = document.createElement("div"), glyph = document.createElement("span"), word = document.createElement("span");
    item.className = "check-item"; item.dataset.state = status; heading.className = "check-heading"; glyph.className = "check-glyph";
    glyph.textContent = ({pass:"✓",fail:"×",skipped:"↷","not-evaluated":"—",missing:"?"})[status] || "?"; word.textContent = label; heading.append(glyph, word); item.appendChild(heading);
    if (code) { const detail = document.createElement("span"); detail.className = "check-code"; detail.textContent = code; item.appendChild(detail); }
    if (family) { const detail = document.createElement("span"); detail.className = "check-family"; detail.textContent = family; item.appendChild(detail); }
    list.appendChild(item);
  }
  function renderSelectedVerdict() {
    const action = state.verdicts.find((item) => item.id === state.selectedVerdictId) || state.pinnedVerdict, outcome = $("action-outcome"), meta = $("action-meta"), next = $("action-next"), traceState = $("action-trace-state"), legacy = $("action-legacy"), checks = $("action-checks");
    clearChildren(checks); next.hidden = true; legacy.hidden = true; $("freeze-readout").setAttribute("aria-pressed", String(state.readoutFrozen)); $("freeze-readout").textContent = state.readoutFrozen ? "Unfreeze readout" : "Freeze readout"; $("follow-latest").hidden = !state.readoutFrozen;
    if (!action) { outcome.textContent = "No action verdict yet."; meta.textContent = "Waiting for the first verdict · the game is still live."; traceState.dataset.state = "waiting"; traceState.textContent = "Trace: waiting for verdict"; return; }
    const age = Math.max(0, Math.floor((performance.now() - action.at) / 1000));
    meta.textContent = `verdict #${action.serial} · ${action.operation || "operation not reported"} · ${action.kind} · ${age}s ago${state.readoutFrozen ? " · readout frozen; game continues" : " · latest action"}`;
    outcome.textContent = action.outcomeText;
    if (action.nextAffordance) { next.textContent = `Next affordance: ${action.nextAffordance}`; next.hidden = false; }
    if (action.legacy) { traceState.dataset.state = "legacy"; traceState.textContent = "EvaluationTrace unavailable · legacy schema-only event"; legacy.textContent = "Legacy event: no per-check trace was supplied. No check result is inferred."; legacy.hidden = false; }
    else if (!action.trace) { traceState.dataset.state = "missing"; traceState.textContent = "EvaluationTrace missing · no check results shown"; legacy.textContent = "This verdict did not include an EvaluationTrace. Missing evidence is not a pass."; legacy.hidden = false; }
    else {
      const trace = action.trace; traceState.dataset.state = "available"; traceState.textContent = `EvaluationTrace received · ${trace.checks.length} executed check${trace.checks.length === 1 ? "" : "s"}`;
      for (const check of trace.checks) { const family = check.families.join(" / "); const status = check.outcome === "pass" ? "pass" : check.outcome === "fail" ? "fail" : "missing"; addCheckRow(checks, status, status === "pass" ? "Passed" : status === "fail" ? "Failed" : "State missing", check.code || "check code not reported", family); }
      for (const skipped of trace.skipped) addCheckRow(checks, "skipped", "Skipped", skipped.code || "check code not reported", skipped.families.join(" / "));
      for (const family of FAMILIES.filter((f) => trace.states[f] === "out_of_scope")) addCheckRow(checks, "not-evaluated", "Not evaluated", "", family);
      for (const family of trace.missing) addCheckRow(checks, "missing", "State missing", "family state not supplied", family);
      if (!trace.checks.length && !trace.skipped.length && !trace.missing.length && !FAMILIES.some((f) => trace.states[f] === "out_of_scope")) { const item=document.createElement("li"); item.className="hint"; item.textContent="Trace supplied no check entries."; checks.appendChild(item); }
    }
  }
  function renderVerdictHistory() {
    const list = $("action-history"), recent = $("recent-actions"); clearChildren(list); clearChildren(recent);
    const selected = state.verdicts.find((item) => item.id === state.selectedVerdictId) || state.pinnedVerdict, selectedSerial = selected ? selected.serial : state.verdictSerial;
    const newer = Math.max(0, state.verdictSerial - selectedSerial);
    $("newer-actions").textContent = state.readoutFrozen ? `${newer} newer action${newer === 1 ? "" : "s"} · game continues` : "Following latest action";
    $("recent-count").textContent = `${state.verdicts.length} verdict${state.verdicts.length === 1 ? "" : "s"}`; $("recent-empty").hidden = state.verdicts.length > 0;
    for (const action of state.verdicts) { const li=document.createElement("li"), button=document.createElement("button"), result=document.createElement("span"), op=document.createElement("span"); button.type="button"; button.className="history-select"; button.dataset.verdictId=String(action.id); button.setAttribute("aria-current",String(action.id===state.selectedVerdictId)); result.className="history-result"; result.textContent=action.kind==="commit"?"Commit":"Hold"; op.className="history-operation"; op.textContent=action.operation||"operation not reported"; button.append(result,op); li.appendChild(button); list.appendChild(li); }
    for (const action of state.verdicts.slice(-3).reverse()) { const li=document.createElement("li"),tag=document.createElement("span"),summary=document.createElement("span"); tag.className=`action-tag ${action.kind}`; tag.textContent=action.kind==="commit"?"Commit":"Hold"; summary.className="action-summary"; summary.textContent=`${action.operation||"operation not reported"} · ${action.summaryText}`; li.append(tag,summary); recent.appendChild(li); }
    const latest=state.verdicts[state.verdicts.length-1]; if (latest&&!state.readoutFrozen) state.selectedVerdictId=latest.id;
    renderSelectedVerdict(); $("follow-latest").textContent=`Follow latest${newer?` (${newer} new)`:""}`;
  }
  function addVerdict(kind, payload, envelope) {
    const operation=String(payload.operation||(state.lastTrace&&state.lastTrace.kind===kind?state.lastTrace.operation:"")||state.pendingOperation||""), from=payload.stage_from, to=payload.stage_to;
    const labels=Array.isArray(payload.labels)?payload.labels.map((value)=>String(value)):[];
    const nextAffordance=kind==="hold"&&typeof payload.next_affordance==="string"?payload.next_affordance.trim():"";
    const outcomeText=kind==="hold"?"Held · game state unchanged.":Number.isFinite(from)&&Number.isFinite(to)?`Committed · stage ${from} → ${to}.`:"Committed · game state updated.";
    const summaryText=kind==="hold"?(nextAffordance||"state unchanged"):(labels.length?labels.join(" · "):"state recorded");
    const trace=state.lastTrace&&state.lastTrace.kind===kind?state.lastTrace:null;
    const item={id:++state.verdictSerial,serial:state.verdictSerial,kind,operation,at:performance.now(),seq:envelope.seq,outcomeText,summaryText,nextAffordance,legacy:!!(trace&&trace.legacy),trace:trace&&trace.trace};
    state.verdicts.push(item); if(state.verdicts.length>12) state.verdicts.shift();
    if(!state.readoutFrozen||state.selectedVerdictId===null) state.selectedVerdictId=item.id; renderVerdictHistory();
  }
  function updateLinkState() {
    const pill=$("link-state"); if(!state.session){pill.textContent="waiting for game session";pill.className="pill waiting";return;}
    if(state.lastTickAt===null){pill.textContent="session received · waiting for game tick";pill.className="pill waiting";return;}
    const age=Math.floor((performance.now()-state.lastTickAt)/1000),fresh=age<=5; pill.textContent=`${fresh?"live":"stale"} · last game tick ${age}s ago`;pill.className=`pill ${fresh?"live":"waiting"}`;
  }
  function resetSessionPresentation() {
    state.counts={commits:0,holds:0,proposals:0,dialogues:0}; state.holdsByGate=Object.fromEntries(FAMILIES.map((f)=>[f,0])); state.codeCounts={}; state.nodeWeight={};
    state.familyEval=Object.fromEntries(FAMILIES.map((f)=>[f,{evaluated:0,passed:0,failed:0}])); state.familyState=Object.fromEntries(FAMILIES.map((f)=>[f,"idle"]));
    state.lastTrace=null;state.legendRows=[];state.legacyEvents=0;state.traceErrors=0;state.pendingOperation="";state.hashChain=[];state.lastSummary=null;state.lastTick=null;state.lastTickAt=null;state.events=[];state.disclosureEvents=[];state.latestExplanation=null;state.trail=[];state.player=null;state.focus="";state.lastHoldGates=[];state.episodeOver=false;
    state.verdicts=[];state.selectedVerdictId=null;state.verdictSerial=0;state.readoutFrozen=false;state.pinnedVerdict=null;state.metMira=false;state.startedAt=performance.now(); clearChildren($("log"));$("log-count").textContent="0 events";
    $("kpi-commits").textContent="0";$("kpi-holds").textContent="0";$("kpi-stage").textContent="—";$("kpi-revision").textContent="0";$("kpi-facts").textContent="0";$("kpi-episode").textContent="waiting";
    resetEdges();FAMILIES.forEach((f)=>setFamilyState(f,"idle"));setTerminalState("commit","terminal_idle");setTerminalState("hold","terminal_idle");renderLegend();renderLastTrace();renderGateTable();renderReference();renderChain();renderQuest(null);renderVerdictHistory();renderMinimap();renderTimeline();renderSemanticExplanation(null);renderDisclosureTimeline();updateLinkState();
  }
  $("freeze-readout").addEventListener("click",()=>{if(state.readoutFrozen){state.readoutFrozen=false;state.pinnedVerdict=null;const latest=state.verdicts[state.verdicts.length-1];state.selectedVerdictId=latest?latest.id:null;}else{state.readoutFrozen=true;state.pinnedVerdict=state.verdicts.find((item)=>item.id===state.selectedVerdictId)||null;}renderVerdictHistory();});
  $("follow-latest").addEventListener("click",()=>{state.readoutFrozen=false;state.pinnedVerdict=null;const latest=state.verdicts[state.verdicts.length-1];state.selectedVerdictId=latest?latest.id:null;renderVerdictHistory();});
  $("action-history").addEventListener("click",(event)=>{const button=event.target.closest("button[data-verdict-id]");if(!button)return;const id=Number(button.dataset.verdictId),action=state.verdicts.find((item)=>item.id===id);if(!action)return;state.selectedVerdictId=id;state.pinnedVerdict=action;state.readoutFrozen=true;renderVerdictHistory();});
  setInterval(()=>{updateLinkState();if(state.selectedVerdictId!==null)renderSelectedVerdict();},1000);

  // ------------------------------------------------------------------ handler
  function handle(msg) {
    const { kind, payload } = msg;
    const record = { kind, at: performance.now(), seq: msg.seq, payload };
    if (kind === "session") resetSessionPresentation();
    state.connected = true;
    if (kind === "tick") state.lastTickAt = performance.now();
    updateLinkState();
    if (kind === "tick") {
      state.player = { x: payload.x, z: payload.z, yaw: payload.yaw };
      state.trail.push({ x: payload.x, z: payload.z });
      if (state.trail.length > 400) state.trail.shift();
      state.focus = payload.focus || "";
      if (payload.episode_over === true) state.episodeOver = true;
      state.lastTick = payload;
      if (state.episodeOver && state.lastSummary) renderKpis(state.lastSummary);
      $("map-caption").textContent = state.session ? `${state.session.sites.length} sites · live player trail` : "waiting for game session";
      $("map-focus").textContent = state.focus ? `Focused site: ${state.focus}` : state.player ? `Player position · ${Number(payload.x).toFixed(1)}, ${Number(payload.z).toFixed(1)}` : "Player position appears when the game sends a tick.";
      renderMinimap();
      return;
    }
    state.events.push(record);
    if (state.events.length > 500) state.events.shift();
    switch (kind) {
      case "session":
        state.session = payload;
        state.lastSummary = payload;
        state.hashChain = [{ tag: "session", hash: payload.state_sha256, revision: payload.revision, stage: payload.stage }];
        renderKpis(payload); renderChain(); renderMinimap();
        logLine("session", `${payload.scenario_id} · ${payload.sites.length} sites · state ${short(payload.state_sha256)}`);
        break;
      case "proposal":
        state.counts.proposals += 1;
        state.pendingOperation = String(payload.operation || "");
        record.label = payload.operation;
        logLine("proposal", `${payload.operation} - ${payload.text}`);
        break;
      case "commit":
        state.counts.commits += 1;
        state.lastSummary = payload;
        state.hashChain.push({ tag: `commit #${payload.commit_count}`, hash: payload.state_sha256, revision: payload.revision, stage: payload.stage });
        record.label = `commit ${payload.stage_from}>${payload.stage_to}`;
        showTraceFlow("commit", payload, msg); addVerdict("commit", payload, msg); flash("flash-commit");
        renderKpis(payload); renderChain(); renderGateTable(); renderReference();
        logLine("commit", `${payload.operation} · ${payload.labels.join(" | ") || "state recorded"} · stage ${payload.stage_from}>${payload.stage_to} · ${short(payload.state_sha256_before)} > ${short(payload.state_sha256)}${traceLogTag()}`);
        break;
      case "hold":
        state.counts.holds += 1;
        state.lastSummary = payload;
        state.lastHoldGates = payload.gates;
        for (const f of new Set(payload.gates.flatMap(gateFamilies))) state.holdsByGate[f] += 1;
        for (const c of payload.codes) state.codeCounts[c] = (state.codeCounts[c] || 0) + 1;
        record.label = `hold ${[...new Set(payload.gates.flatMap(gateFamilies))].join("+")}`;
        showTraceFlow("hold", payload, msg); addVerdict("hold", payload, msg); flash("flash-hold");
        renderKpis(payload); renderGateTable(); renderReference();
        logLine("hold", `${payload.codes.join(", ")} · gate ${payload.gates.join(", ")} · state unchanged ${short(payload.state_sha256)} · next: ${payload.next_affordance}${traceLogTag()}`);
        break;
      case "disclosure_outcome":
      case "disclosure_replay": {
        const explanation = normalizeExplanation(payload, msg);
        const event = { kind, seq: explanation?.engine.seq ?? numberOrUnknown(msg.seq), tMs: explanation?.engine.tMs ?? numberOrUnknown(msg.t_ms), explanation, receivedAt: performance.now() };
        state.disclosureEvents.push(event);
        if (state.disclosureEvents.length > 180) state.disclosureEvents.shift();
        state.latestExplanation = explanation;
        renderSemanticExplanation(explanation, true);
        renderDisclosureTimeline();
        record.label = kind;
        logLine(kind, explanation ? `${explanation.decision.outcome} · ${explanation.effect.kind} · hashes ${explanation.effect.hashEquality}` : "unknown semantic explanation (malformed or unavailable)");
        break;
      }
      case "dialogue":
        state.counts.dialogues += 1;
        if (payload.npc === "captain_mira" && payload.phase === "open") { state.metMira = true; renderQuest(); }
        // A dialogue choice may run a top-level validate_disclosure (the early-
        // secret hold) with no proposal envelope; remember it so the strip can
        // name what the hold was evaluated for.
        if (payload.phase === "choice" && payload.choice_id) state.pendingOperation = String(payload.choice_id);
        record.label = payload.phase === "choice" ? payload.choice_id : payload.phase;
        logLine("dialogue", `${payload.npc} · ${payload.phase}${payload.choice_id ? ` · ${payload.choice_id}` : ""}`);
        break;
      case "focus":
        state.focus = payload.interaction_id || "";
        record.label = state.focus || "";
        if (state.focus) logLine("focus", state.focus);
        renderMinimap();
        break;
      case "episode_complete":
        state.episodeOver = true;
        state.lastSummary = { ...(state.lastSummary || {}), ...payload };
        renderKpis(state.lastSummary);
        logLine("episode_complete", `entries ${payload.commit_count} · holds ${payload.refusal_count} · holds by gate ${JSON.stringify(payload.holds_by_gate)} · final ${short(payload.state_sha256)}`);
        break;
      default:
        logLine(kind, JSON.stringify(payload).slice(0, 160));
    }
  }

  window.addEventListener("message", (event) => {
    // Only the embedded game frame on this origin may feed the dashboard; an opener or a
    // foreign frame posting a well-formed envelope must not be able to paint a fake chain.
    const game = document.getElementById("game");
    if (!game || event.source !== game.contentWindow || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.channel !== CHANNEL) return;
    try { handle(data); } catch (error) { console.error("dashboard handler failed", error, data); }
  });

  const referenceSource = fetch("disclosure-reference.json").then((response) => { if (!response.ok) throw new Error("semantic reference unavailable"); return response.json(); }).catch(() => fetch("paper-reference.json").then((response) => { if (!response.ok) throw new Error("legacy reference unavailable"); return response.json(); }));
  referenceSource.then((ref) => { state.reference = ref; renderGateTable(); renderReference(); renderComparison(); }).catch(() => { renderGateTable(); renderReference(); renderComparison(); });
  renderChain();
  renderMinimap();
  renderTimeline();
  renderLegend();
  renderLastTrace();
  renderSemanticExplanation(null);
  renderDisclosureTimeline();
  renderComparison();
})();
