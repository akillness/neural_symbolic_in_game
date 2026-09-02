/* TRACE-RPG live commit-gate dashboard.
 *
 * Presentation-only consumer of the game's postMessage mirror (D-065). It draws an
 * AgentSight-style weighted pipeline ("commit nebula"), a `top`-like metrics panel
 * bound to the paper's predicate families, an event timeline, and a harbor mini-map.
 * Nothing here can propose, repair, or commit; it renders what the hard writer
 * already returned. Exposed as window.__traceDashboard for browser automation.
 */
(() => {
  "use strict";
  const CHANNEL = "trace-rpg-dashboard";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const FAMILIES = ["POLICY", "PRECONDITION", "REACHABILITY", "KNOWLEDGE", "DISCLOSURE", "QUEST STAGE"];
  const COLORS = { amber: "#f2b84b", coral: "#d9685f", green: "#6fcf8a", blue: "#6db3f2", muted: "#8fa3b2", line: "#22303d", ink: "#d9d3c4" };

  const state = {
    connected: false,
    session: null,
    reference: null,
    counts: { commits: 0, holds: 0, proposals: 0, dialogues: 0 },
    holdsByGate: Object.fromEntries(FAMILIES.map((f) => [f, 0])),
    codeCounts: {},
    nodeWeight: {},
    hashChain: [],
    lastSummary: null,
    lastTick: null,
    events: [],
    trail: [],
    player: null,
    focus: "",
    lastHoldGates: [],
    episodeOver: false,
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

  // ------------------------------------------------------------------ nebula
  // Pipeline geometry mirrors Fig. 2 / Table II of the manuscript: proposer →
  // parser/contract → six state-relative predicates → commit | hold → trace.
  const NODES = {
    proposer: { x: 60, y: 200, label: "PLAYER INTENT", sub: "proposal a_t", r: 26 },
    parser: { x: 180, y: 200, label: "PARSER", sub: "typed contract", r: 22 },
    POLICY: { x: 330, y: 50, label: "v_policy", sub: "POLICY", r: 16 },
    PRECONDITION: { x: 330, y: 110, label: "v_pre", sub: "PRECONDITION", r: 16 },
    REACHABILITY: { x: 330, y: 170, label: "v_reach", sub: "REACHABILITY", r: 16 },
    KNOWLEDGE: { x: 330, y: 230, label: "v_know", sub: "KNOWLEDGE", r: 16 },
    DISCLOSURE: { x: 330, y: 290, label: "v_disc", sub: "DISCLOSURE", r: 16 },
    "QUEST STAGE": { x: 330, y: 350, label: "v_quest", sub: "QUEST STAGE", r: 16 },
    commit: { x: 480, y: 130, label: "COMMIT", sub: "T(c_t, a_t)", r: 24 },
    hold: { x: 480, y: 270, label: "HOLD", sub: "state unchanged", r: 24 },
    trace: { x: 590, y: 200, label: "TRACE", sub: "hash chain", r: 22 },
  };
  const nebula = $("nebula");
  const edgeLayer = el("g", { id: "edges" }, nebula);
  const pulseLayer = el("g", { id: "pulses" }, nebula);
  const nodeLayer = el("g", { id: "nodes" }, nebula);
  const nodeEls = {};

  function edgePath(a, b) {
    const ax = NODES[a].x, ay = NODES[a].y, bx = NODES[b].x, by = NODES[b].y;
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
  const edgeEls = {};
  for (const [a, b] of EDGES) {
    edgeEls[`${a}>${b}`] = el("path", { d: edgePath(a, b), fill: "none", stroke: COLORS.line, "stroke-width": 1.2, opacity: 0.8 }, edgeLayer);
  }
  for (const [id, n] of Object.entries(NODES)) {
    const g = el("g", { class: "node", "data-id": id }, nodeLayer);
    const halo = el("circle", { cx: n.x, cy: n.y, r: n.r + 6, fill: "none", stroke: COLORS.line, "stroke-width": 1, opacity: 0.6 }, g);
    const circle = el("circle", { cx: n.x, cy: n.y, r: n.r, fill: "#0e161f", stroke: COLORS.muted, "stroke-width": 1.5 }, g);
    const label = el("text", { x: n.x, y: n.y + 3, "text-anchor": "middle", "font-size": 9, "font-family": "Menlo, monospace", fill: COLORS.ink }, g);
    label.textContent = n.label;
    const sub = el("text", { x: n.x, y: n.y + n.r + 14, "text-anchor": "middle", "font-size": 8, fill: COLORS.muted }, g);
    sub.textContent = n.sub;
    const weight = el("text", { x: n.x + n.r + 4, y: n.y - n.r + 2, "font-size": 8, "font-family": "Menlo, monospace", fill: COLORS.amber }, g);
    weight.textContent = "";
    nodeEls[id] = { g, halo, circle, label, weight, base: n.r };
    state.nodeWeight[id] = 0;
  }

  function bump(id, color) {
    state.nodeWeight[id] = (state.nodeWeight[id] || 0) + 1;
    const n = nodeEls[id];
    if (!n) return;
    // AgentSight idiom: size encodes effect weight; growth is logarithmic so the
    // graph stays readable across a long session.
    const r = n.base + Math.min(14, 4 * Math.log2(1 + state.nodeWeight[id]));
    n.circle.setAttribute("r", r);
    n.halo.setAttribute("r", r + 6);
    n.weight.textContent = `x${state.nodeWeight[id]}`;
    n.circle.setAttribute("stroke", color);
    n.circle.setAttribute("stroke-width", 2.5);
    setTimeout(() => n.circle.setAttribute("stroke-width", 1.5), 900);
  }

  const pulses = [];
  function pulse(a, b, color, delay = 0) {
    const key = `${a}>${b}`;
    const path = edgeEls[key];
    if (!path) return;
    path.setAttribute("stroke", color);
    path.setAttribute("opacity", 1);
    const dot = el("circle", { r: 4, fill: color }, pulseLayer);
    pulses.push({ path, dot, t0: performance.now() + delay, dur: 550, color });
    setTimeout(() => { path.setAttribute("stroke", COLORS.line); path.setAttribute("opacity", 0.8); }, 1600 + delay);
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

  function showCommitFlow() {
    pulse("proposer", "parser", COLORS.green);
    bump("proposer", COLORS.green);
    setTimeout(() => bump("parser", COLORS.green), 400);
    FAMILIES.forEach((f, i) => {
      pulse("parser", f, COLORS.green, 450 + i * 40);
      setTimeout(() => bump(f, COLORS.green), 900 + i * 40);
      pulse(f, "commit", COLORS.green, 1000 + i * 40);
    });
    setTimeout(() => bump("commit", COLORS.green), 1500);
    pulse("commit", "trace", COLORS.green, 1550);
    setTimeout(() => bump("trace", COLORS.green), 2050);
  }
  function showHoldFlow(gates) {
    pulse("proposer", "parser", COLORS.amber);
    bump("proposer", COLORS.amber);
    setTimeout(() => bump("parser", COLORS.amber), 400);
    const rejected = new Set(gates.map(gateFamily));
    FAMILIES.forEach((f, i) => {
      const bad = rejected.has(f);
      pulse("parser", f, bad ? COLORS.coral : COLORS.line, 450 + i * 40);
      if (bad) {
        setTimeout(() => bump(f, COLORS.coral), 900 + i * 40);
        pulse(f, "hold", COLORS.coral, 1000 + i * 40);
      }
    });
    setTimeout(() => bump("hold", COLORS.coral), 1500);
    pulse("hold", "trace", COLORS.coral, 1550);
    setTimeout(() => bump("trace", COLORS.coral), 2050);
  }
  function gateFamily(gate) {
    // The engine reports "DISCLOSURE/QUEST STAGE" for stage-gated disclosure.
    return gate.includes("/") ? gate.split("/")[0] : gate;
  }

  // ------------------------------------------------------------------ metrics
  function renderGateTable() {
    const table = $("gate-table");
    const max = Math.max(1, ...Object.values(state.holdsByGate));
    const ref = state.reference ? state.reference.paper_predicates : [];
    const rows = FAMILIES.map((f) => {
      const meta = ref.find((r) => r.family === f) || { symbol: "", engine_codes: [] };
      const n = state.holdsByGate[f] || 0;
      const codes = meta.engine_codes.map((c) => `${c}${state.codeCounts[c] ? ` x${state.codeCounts[c]}` : ""}`).join(", ") || "-";
      return `<tr><td><span class="mono">${meta.symbol}</span> ${f}</td><td class="bar-cell"><div class="bar-fill" style="width:${(100 * n) / max}%"></div><span class="mono">${n}</span></td><td class="hint">${codes}</td></tr>`;
    });
    table.innerHTML = `<tr><th>predicate family</th><th>holds</th><th>engine codes seen</th></tr>${rows.join("")}`;
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
      ["live session · hold-path state unchanged", state.counts.holds ? `${state.counts.holds}/${state.counts.holds}` : "-", "I1 exhausted-failure immutability"],
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
        record.label = payload.operation;
        logLine("proposal", `${payload.operation} - ${payload.text}`);
        break;
      case "commit":
        state.counts.commits += 1;
        state.lastSummary = payload;
        state.hashChain.push({ tag: `commit #${payload.commit_count}`, hash: payload.state_sha256, revision: payload.revision, stage: payload.stage });
        record.label = `commit ${payload.stage_from}>${payload.stage_to}`;
        showCommitFlow(); flash("flash-commit");
        renderKpis(payload); renderChain(); renderGateTable(); renderReference();
        logLine("commit", `${payload.operation} · ${payload.labels.join(" | ") || "state recorded"} · stage ${payload.stage_from}>${payload.stage_to} · ${short(payload.state_sha256_before)} > ${short(payload.state_sha256)}`);
        break;
      case "hold":
        state.counts.holds += 1;
        state.lastSummary = payload;
        state.lastHoldGates = payload.gates;
        for (const g of payload.gates) { const f = gateFamily(g); state.holdsByGate[f] = (state.holdsByGate[f] || 0) + 1; }
        for (const c of payload.codes) state.codeCounts[c] = (state.codeCounts[c] || 0) + 1;
        record.label = `hold ${payload.gates.map(gateFamily).join("+")}`;
        showHoldFlow(payload.gates); flash("flash-hold");
        renderKpis(payload); renderGateTable(); renderReference();
        logLine("hold", `${payload.codes.join(", ")} · gate ${payload.gates.join(", ")} · state unchanged ${short(payload.state_sha256)} · next: ${payload.next_affordance}`);
        break;
      case "dialogue":
        state.counts.dialogues += 1;
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
})();
