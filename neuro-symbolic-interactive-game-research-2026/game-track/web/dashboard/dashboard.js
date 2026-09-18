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
 *   - node state is rendered from `family_states` only; a family missing from the
 *     payload renders a loud "state missing" node and logs console.error, never a
 *     neutral or a pass;
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
      code: String(c.code || ""), gate: String(c.gate || ""), outcome: c.outcome === "fail" ? "fail" : "pass", families: gateFamilies(c.gate),
    }));
    const familyStates = raw.family_states && typeof raw.family_states === "object" ? raw.family_states : {};
    const states = {};
    const missing = [];
    for (const f of FAMILIES) {
      const s = familyStates[f];
      if (s === "pass" || s === "fail" || s === "skipped" || s === "out_of_scope") states[f] = s;
      else { states[f] = "missing"; missing.push(f); }
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
      console.error(`dashboard trace: family_states missing ${trace.missing.join(", ")} for ${operation} (seq ${envelope.seq}); rendering "state missing", not a pass`);
    }
    const codesByFamily = Object.fromEntries(FAMILIES.map((f) => [f, []]));
    const touched = new Set();
    const STEP = 260;
    let step = 0;
    for (const check of trace.checks) {
      const color = check.outcome === "pass" ? COLORS.blue : COLORS.coral;
      for (const f of check.families) {
        touched.add(f);
        state.familyEval[f].evaluated += 1;
        state.familyEval[f][check.outcome === "pass" ? "passed" : "failed"] += 1;
        weigh(f, 1, "evaluated");
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
      lines.push(`${String(i + 1).padEnd(2)} ${familyLabel(c.families).padEnd(15)} ${c.code.padEnd(25)} ${c.outcome === "pass" ? "v passed" : "x failed"}`);
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
    const ref = state.reference ? state.reference.paper_predicates : [];
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
    $("kpi-stage").textContent = summary.stage ?? "0";
    $("kpi-revision").textContent = summary.revision ?? "0";
    $("kpi-facts").textContent = summary.fact_count ?? "0";
    $("kpi-episode").textContent = state.episodeOver ? "complete" : "open";
    $("session-hash").textContent = `state ${short(summary.state_sha256)}`;
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
    log.scrollTop = log.scrollHeight;
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

  // ------------------------------------------------------------------ handler
  function handle(msg) {
    const { kind, payload } = msg;
    if (!state.connected) {
      state.connected = true;
      const pill = $("link-state");
      pill.textContent = "live · receiving game events";
      pill.className = "pill live";
    }
    const record = { kind, at: performance.now(), seq: msg.seq, payload };
    if (kind === "tick") {
      state.player = { x: payload.x, z: payload.z, yaw: payload.yaw };
      state.trail.push({ x: payload.x, z: payload.z });
      if (state.trail.length > 400) state.trail.shift();
      state.focus = payload.focus || "";
      state.episodeOver = !!payload.episode_over;
      state.lastTick = payload;
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
        showTraceFlow("commit", payload, msg); flash("flash-commit");
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
        showTraceFlow("hold", payload, msg); flash("flash-hold");
        renderKpis(payload); renderGateTable(); renderReference();
        logLine("hold", `${payload.codes.join(", ")} · gate ${payload.gates.join(", ")} · state unchanged ${short(payload.state_sha256)} · next: ${payload.next_affordance}${traceLogTag()}`);
        break;
      case "dialogue":
        state.counts.dialogues += 1;
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
        state.lastSummary = payload;
        renderKpis(payload);
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

  fetch("paper-reference.json")
    .then((r) => r.json())
    .then((ref) => { state.reference = ref; renderGateTable(); renderReference(); })
    .catch(() => { renderGateTable(); renderReference(); });
  renderChain();
  renderMinimap();
  renderTimeline();
  renderLegend();
  renderLastTrace();
})();
